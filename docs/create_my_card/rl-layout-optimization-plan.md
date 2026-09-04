# CreateMyCard：从 SFT 可渲染到 RL 布局质量优化方案

> 状态：方案 v1，面向 Qwen3.6-27B、veRL、HarmonyOS A2UI 2×2 卡片。
> 目标：以当前 SFT checkpoint 为起点，降低重叠、越界、文字截断和异常留白，同时保持 Compact DSL 可转换、内容正确、输出长度稳定。
> 范围：本方案定义数据、奖励、训练、评测、消融和工程接口；不把“训练 reward 上升”直接等同于“布局质量提升”。
> 工程进度：Stage 0 的离线审计闭环已落在 [`frameworks/verl/create_my_card/rl/`](../../frameworks/verl/create_my_card/rl/README.md)；primary 标签复核、L2/人评校准、静态代理和 Ascend preflight 尚未完成，因此当前奖励禁止策略更新。

## 1. 结论摘要

不建议直接把设计质检器的 `P0/P1/P2` 数量相加后启动 PPO。推荐采用三阶段路线：

```text
当前 SFT checkpoint
  → Stage A：Best-of-N + 质检器排序，构建 RFT/偏好数据
  → Stage B：RFT（首选）或 DPO，先吸收现有策略能探索到的好布局
  → Stage C：在线 GRPO，使用可验证的规则奖励继续探索
```

算法首选 GRPO，而不是 PPO，原因是当前任务是单轮 `TaskSpec → Compact DSL`，可以得到终态、确定性、分级的规则奖励，不需要额外训练 critic。训练时从当前 SFT/RFT 模型初始化 actor，并用同一 checkpoint 作为 reference model。

设计质检器不能原样当作完整在线奖励：

- L1 静态检查速度快，适合覆盖所有 rollout；
- 当前 2×2 布局没有完整的 L1 骨架终审，主要目标中的重叠、真实截断和留白依赖 L2 `dumpLayout`；
- `GEOMETRY.OVERLAP` 已被质检器默认静默，RL 专用评测必须显式启用 `include_delegated`；
- L2 需要渲染设备，不能在没有吞吐评估的情况下阻塞每个 rollout。

因此采用双层奖励：

1. 每个 rollout 同步执行转换、TaskSpec 一致性、L1 质检和 Compact DSL 静态布局代理评分；
2. 固定 canary、难例和抽样候选执行真实渲染 + L2，用于离线排序、奖励校准、回归和最终验收；
3. 只有渲染服务吞吐满足训练要求后，才把 L2 作为同步在线奖励的一部分。

## 2. 当前基线与问题定义

### 2.1 已有资产

当前仓库已经具备：

- 954 条 TaskSpec/Compact DSL 成对数据，确定性拆分为 922 条训练、32 条验证；
- 98 条独立 TaskSpec 评估源，其中当前构建器支持 62 条 2×2，另有 36 条 2×4；
- Compact DSL → A2UI 冻结转换器及 round-trip 工具；
- Qwen3.6-27B 全参数 SFT、FSDP checkpoint 合并和离线 benchmark；
- 在 16 个逻辑 Ascend NPU 上跑通的 veRL GRPO 工程模板；
- `design-card-check-plugin 0.2.0`：5 个规则包、69 条登记规则、L1/L2 统一 finding schema。

当前 SFT 的主要成绩是“能生成、能转换、能渲染”。截图暴露的下一层问题是：

- 元素或文字重叠；
- 核心文字/数值越界或截断；
- 内容过少、底部留白过大；
- 对齐、间距和信息密度不稳定；
- 输出虽然语法合法，但布局不一定合理。

### 2.2 成功标准

最终模型必须同时满足以下条件：

| 维度 | 核心指标 | 放行原则 |
| --- | --- | --- |
| 协议 | Compact DSL 解析率、A2UI 转换率、round-trip | 不低于 SFT；正式候选目标 ≥99.5% |
| 内容 | 核心事实/动作覆盖、非法 path/asset/event 数 | 核心事实不得因优化布局而删除；非法引用为 0 |
| 布局 | overlap（P0）、safe-area overflow/text squash（P1）、异常留白（P2） | 各目标规则命中率相对 SFT 至少下降 50%，不能只统计 P0 |
| 设计 | P1/P2、颜色/字号/间距/密度规则 | 各规则族不得以另一规则族退化为代价换分 |
| 长度 | response token P50/P95、截断率、EOS | P95 增长不超过 10%；截断率 <1% |
| 人评 | SFT vs RL 盲评偏好 | RL 胜率 >50%，且配对 bootstrap 95% CI 下界 >50% |
| 稳定性 | KL、entropy、零方差组、3 个随机种子 | 不以单次训练曲线或单个 checkpoint 下结论 |

“目标问题下降 50%”是第一阶段工程门槛，不是最终产品指标。正式阈值应在 SFT 基线全量跑完后冻结，不能训练后再改口径。

## 3. 奖励环境架构

```text
TaskSpec prompt
    │
    ▼
当前策略生成 Compact DSL
    │
    ├─ 解析 / frozen converter / TaskSpec 上下文校验 ──► 协议与内容门禁
    │
    ├─ A2UI + design-check L1 ───────────────────────► 规则 finding
    │
    ├─ Compact DSL 静态布局代理 ─────────────────────► 在线布局分
    │
    └─ 选定样本：渲染 → dumpLayout → L2 ────────────► 真实几何分
                                                        │
                                                        ▼
                                            分维度 reward + GRPO
```

### 3.1 不通过 dsh 壳逐条调用

插件的 JS 入口只是参数分流和 Python 子进程壳。训练奖励应直接调用 Python 核心或部署成独立 reward service，避免每条 rollout 启动 `dsh`、Node 和新的 Python 进程。

质检器 0.2.0 固定在项目内：

```text
frameworks/verl/create_my_card/rl/vendor/
└── design-card-check-plugin-0.2.0/
    └── package/
        ├── DESIGN.md
        ├── DESIGN-2x4.md
        └── design-check/
```

奖励审计默认使用该内置路径。`DESIGN_CHECK_ROOT`、`DESIGN_SPEC` 和
`DESIGN_2X4_SPEC` 只用于显式覆盖，不应作为正常运行的必需配置。

当前训练骨架只保留运行所需的显式路径和配置，不在训练主路径中计算文件 SHA、
绑定 assessment 或维护制品审查清单。后续需要做正式实验复现时，可由独立评估模块
记录 checker、converter、prompt、tokenizer、veRL 与奖励配置版本，但不应成为
RFT、DPO、GRPO runner 的依赖。

### 3.2 质检器退出码契约

奖励适配器必须按真实契约处理：

| 退出码 | 含义 | 训练处理 |
| ---: | --- | --- |
| 0 | 检查完成且无 P0，仍可能有 P1/P2 | 解析 JSON，计算分维度奖励 |
| 1 | 检查完成且存在 P0 | 正常负样本，解析 JSON；不能当环境故障 |
| 2 | 检查器自身故障、输入/环境异常 | mask 或重试该 rollout，不能给模型 0 分 |

如果把 exit 2 当作低奖励，模型会被环境故障错误惩罚；如果只看 exit 0/1，又会完全忽略 P1/P2。

## 4. 奖励设计

### 4.1 先门禁，再加权

奖励不是简单的 findings 计数。先执行不可补偿的硬门禁：

```python
if checker_internal_error_or_timeout:
    return MASK_AND_RETRY

if not compact_parse_ok or not a2ui_conversion_ok:
    return -1.0

if illegal_path_asset_event or missing_primary_fact_or_unfit_primary_text:
    return min(raw_reward, -0.5)

if any_checker_p0:
    return min(raw_reward, 0.0)
```

这样可以防止“颜色和间距很好”抵消“根本不可转换”，也可以防止模型删除内容来获得无重叠、低密度的假高分。

### 4.2 在线同步奖励

所有分量先归一化到 `[0,1]`。下面的权重只是 Stage 0 要验证的候选假设，不能在未校准时直接写入正式 GRPO 配置：

```text
R_online =
    0.25 × R_contract
  + 0.20 × R_content
  + 0.45 × R_static_layout
  + 0.05 × R_style
  + 0.05 × R_efficiency
```

| 分量 | 来源 | 主要内容 |
| --- | --- | --- |
| `R_contract` | converter + `PROTOCOL.*` / `STRUCT.*` | 消息、根、树、ID、数据绑定、事件和素材合法性 |
| `R_content` | TaskSpec + SFT gold 派生标签 | 核心事实/动作 recall、允许集合 precision、无静态值泄漏 |
| `R_static_layout` | `SPACING.*` / `SLOT.*` / `DENSITY.*` / `AREA.*` + 新静态代理 | 尺寸预算、父子容器占用、文字框、间距、对齐、留白和密度 |
| `R_style` | `COLOR.*` / `GRADIENT.*` / `TYPE.*` / `SHAPE.*` 等 | 视觉 token 与元素规范 |
| `R_efficiency` | tokenizer / EOS | 输出长度带、无重复、无截断、正确结束 |

不把 format/长度奖励设成主奖励。协议和长度分量合计不超过 30%，布局与内容才是优化目标。

在静态代理通过校准前，`R_static_layout` 只能用于日志和 Best-of-N 分析，不能以 0.45 权重驱动策略更新。Stage 0 至少比较三组权重，并在冻结的人评/L2 校准集上选择；权重选择完成后写入 reward manifest，训练中不再修改。

### 4.3 静态布局代理

当前质检器 L1 对 2×2 的真实重叠和截断覆盖不足，需要新增一个只读的 Compact DSL 静态代理评分器。它不替代 L2，只负责为在线训练提供密集信号：

1. 按 Column/Row 的 `height/width + margin + itemMargin` 计算父容器预算；
2. 检查所有可见叶子是否落在 136×136 内容区；
3. 检查 `Text.height / fontSize`、`maxLines` 与可用宽高的合理性；
4. 检查 Row 横向预算、Column 纵向预算和跨槽位间距；
5. 计算可见叶子 bbox union 的占用率与底部留白；
6. 留白目标不写死成“越满越好”，而是按人工通过样本、卡片类型和内容数得到的 P10–P90 合理区间；
7. Stack 只在明确叠放语义下评分，不能把 Stack 内所有相交都当重叠。

静态代理的每一项都要在真实 L2 dump 上做相关性校准。进入在线 RL 的建议门槛是：

- 与 `R_l2` 的 Spearman 相关系数 `ρ ≥ 0.5`；
- 对人工布局偏好 pair 的排序准确率 `≥60%`；
- 静态分 top quartile 的 L2 P0 率至少比 bottom quartile 低 50%；
- 长度和组件数控制后，上述关系仍成立。

门槛应在看结果前冻结。未通过时，静态代理必须降权、重写或仅用于诊断；不能因为“看起来合理”保留，更不能启动依赖它的在线 GRPO。

### 4.4 L2 真实渲染奖励

对有 dump 的样本计算：

```text
R_l2 =
    0.30 × no_overlap
  + 0.25 × no_overflow_or_text_squash
  + 0.15 × spacing
  + 0.15 × alignment
  + 0.15 × occupancy_and_bottom_anchor
```

必须显式开启：

```text
--include-delegated
```

因为目标中的元素重叠对应 `GEOMETRY.OVERLAP`，它在当前插件中默认不输出。与三类截图问题直接对应的规则是：

| 问题 | 规则/信号 |
| --- | --- |
| 重叠 | `GEOMETRY.OVERLAP`（L2、P0、需显式启用） |
| 越界 | `GEOMETRY.SAFE_AREA_OVERFLOW` |
| 纵向截断 | `GEOMETRY.TEXT_SQUASH` |
| 过大留白 | `GEOMETRY.CONTENT_ALIGN_ANCHOR` |
| 间距/对齐 | `GEOMETRY.SLOT_GAP`、`LABEL_GAP`、`AREA_*` |
| 声明与实测漂移 | `RECONCILE.DIMENSION_DRIFT` 等 |

离线候选排序采用：

```text
R_rank = 0.60 × R_online + 0.40 × R_l2
```

权重需通过人类偏好校准，不作为未经验证的固定真值。

### 4.5 finding 到分数的映射

按规则族分别计算，不用全局总数：

```text
penalty_dimension = clip(1.00 × n_P0 + 0.25 × n_P1 + 0.05 × n_P2, 0, 1)
score_dimension = 1 - penalty_dimension
```

对于同一根因重复报出的多个 finding，应按 `rule_id + element` 去重或设置单规则上限，避免复杂卡片仅因元素多就天然得分更低。每个 reward 分量必须单独写日志，至少包括 raw value、加权贡献和命中的规则 ID。

### 4.6 内容覆盖防作弊

每条 RL 数据的 `extra_info` 至少携带：

```json
{
  "sample_id": "...",
  "task_spec": {},
  "required_primary_paths": [],
  "allowed_paths": [],
  "allowed_assets": [],
  "allowed_events": [],
  "reference_content_budget": {"facts_min": 1, "facts_max": 3}
}
```

标签生成原则：

- `allowed_*` 来自 TaskSpec 白名单；
- primary path 由用户 Query、TaskSpec 和 SFT gold 共同派生，并抽样人工复核；
- 不要求复制 gold 的组件树、颜色或精确坐标；
- 允许删除次要信息，但不允许删除主事实后用空卡骗分；
- 允许不使用不相关的素材/事件候选，不把“候选全部使用”当成功。

primary fact 通过不能只检查“路径或字符串存在”，还必须检查其可见性：

- 静态 `text_fit` 代理通过；
- 有 L2 的样本未在对应元素上命中 `TEXT_SQUASH`、overflow 或 overlap；
- canary/final test 使用长动态值时，核心文字仍实际可见。

统一口径：

```text
primary_recall = 命中的 primary facts / primary facts 总数
allowed_precision = 合法 path/asset/event / 实际使用的 path/asset/event
content_pass = (primary_recall == 1) and (allowed_precision == 1) and primary_text_fit
content_pass_rate = mean(content_pass)
```

停机条件中的“内容覆盖下降”统一指固定 dev 集上的 `content_pass_rate`；在线 batch 使用 5-step EWMA 告警，不能用单个 noisy batch 直接回滚。

## 5. 数据与课程

### 5.1 冻结数据分层

| 数据层 | 建议规模 | 用途 |
| --- | ---: | --- |
| RL train | 现有 922 条起步 | rollout、RFT、GRPO |
| SFT validation | 现有 32 条，保持不动 | SFT/格式回归，不参与 RL 采样 |
| 2×2 dev | 现有 62 条 | 高频评测与 checkpoint 选择 |
| visual canary | 截图中的 16 条或其原始 case | 每 25–50 step 固定 T=0 渲染 |
| final test | 至少 300 条独立 TaskSpec | 最终统计结论，不参与调参 |
| 2×4 extension | 现有 36 条起步 | 2×2 稳定后单独扩展 |

62 条测试集足够发现大问题，不足以证明几个百分点的提升。最终测试应扩展到至少 300 条；可以从 `query/generation` 的 1,068 条自然 Query 中独立生成 TaskSpec，但生成、去重和人工验收必须与 RL train 隔离。

### 5.2 难例生成

围绕三类目标构造确定性 stress variants：

- 长中文标题、长设备名、长日程名；
- 1/2/3 个事实，数字位数和单位变化；
- 有/无图标、有/无按钮、有/无 Progress；
- 需要 Row、Column、Stack 的不同布局；
- 低信息卡与高信息卡；
- 合法但接近 136×136 容量边界的样本；
- sampleValue 的长字符串、百分比和多位数字极值。

变体只能修改 TaskSpec 允许的 preview/sample 值，不能引入训练时不存在的协议或业务能力。

### 5.3 Learnability 采样

对每个 prompt 维护最近 N 个 rollout 的成功率与 reward std：

- 全部高分：降低采样权重；
- 全部失败：先进入离线修复/RFT 或降难度；
- 成功率在 `[0.1, 0.9]`：优先用于 GRPO；
- reward std 接近 0 的组不进入策略更新，避免浪费 rollout。

## 6. 三阶段训练流程

### Stage 0：无梯度奖励审计

在任何 RL 更新前：

1. 对 SFT checkpoint 执行 T=0 greedy 基线；
2. 对同一 prompt 以训练采样参数生成 N=8；
3. 全量跑在线奖励，选定样本跑 L2；
4. 人工盲评至少 200 对候选；
5. 检查 reward 与人评、L2、长度和组件数的相关性；
6. 主动寻找高 reward 的空卡、删内容卡、超短卡、模板卡。

进入训练的最低条件：

- 静态代理达到 §4.3 的 L2/人评校准门槛；
- reward 选出的候选在人评中显著优于随机候选；
- reward 与长度/组件数不存在单调投机关系；
- checker exit 2 和 timeout 可被可靠 mask/retry；
- 每个 reward 分量有非零方差；
- 以 `group_reward_std < 1e-4` 定义近零方差组，Stage 0 中有用组比例至少达到 50%；
- prompt 的 N=8 成功率主要落在 `[0.1,0.9]`；若大量全对/全错，先调整课程而不是启动 GRPO；
- SFT step-0 与 reference 的 KL 为 0 或数值误差量级。

这里的 200 对人评用于奖励校准，不用于最终显著性结论。

### Stage 0.5：Ascend 长序列与配置 preflight

现有 GRPO 冒烟只验证了 `max_model_len=1536`；CreateMyCard 候选配置是 5632，不能按“rollout 总数仍为 32”直接外推。写正式训练脚本前必须：

1. 用实际 tokenizer 重新生成 `token_stats.json`，获得 prompt/response 的 P50、P95 和 max；
2. 用 P50/P95/max 三个长度桶分别测试 `n=1/4/8`、prompt batch `1/2/4`；
3. 显式验证 `max_model_len`、`max_num_batched_tokens`、`max_num_seqs` 和 KV cache 配置；
4. 检查最长序列无 OOM/NaN、无静默截断，NPU reserved 保留至少 20% 余量；
5. 并发运行 converter/L1 reward worker，确认 CPU 内存、文件句柄和 reward latency 不阻塞 rollout；
6. 通过打印的 Hydra 最终配置和实际日志，确认 `filter_groups`、`entropy_coef`、`loss_agg_mode`、`truncation` 等键确实生效。

若 4 prompts × 8 rollout 无法同时驻留，应降低并发、分批生成同一 group 或调整 offload/调度预算，不能通过截断 TaskSpec/DSL 获得“可运行”结果。

### Stage A：Best-of-N → RFT/DPO

每个训练 prompt 生成 8 个候选：

- chosen：通过协议/内容门禁、无 P0、`R_rank` 最高；
- rejected：同 prompt 下至少一个明确布局问题，但仍可解析，便于模型学习布局差异；
- pair 的长度尽量匹配，防止 DPO 只学会“越短越好”；
- chosen/rejected 分差过小的 pair 丢弃。

首选先做 1 个 epoch RFT：只用通过门禁的高质量候选继续 SFT。原因是这是从当前策略可达区域中做稳定的 rejection sampling，成本低且不引入在线策略漂移。

如果已有足够、清晰的 pair，再增加 DPO 消融。自生成 pair 噪声较大时不要只靠 DPO；优先使用 verifier + 人工复核的 pair。

### Stage B：在线 GRPO

通过 Stage 0.5 后的候选起始配置：

```yaml
model:
  actor: <rft_or_sft_merged_checkpoint>
  reference: <same_checkpoint>

data:
  train_batch_size: 4          # prompt 数
  max_prompt_length: 4096
  max_response_length: 1536
  truncation: error

rollout:
  n: 8                         # 4 prompts × 8 = 32 rollouts/step
  temperature: 0.8
  top_p: 0.95
  enable_thinking: false
  max_model_len: 5632
  max_num_batched_tokens: <由 Stage 0.5 实测确定>
  max_num_seqs: <由 Stage 0.5 实测确定>

actor:
  learning_rate: 5e-7          # 消融 2e-7 / 5e-7 / 1e-6
  use_kl_loss: true
  kl_loss_coef: 0.001
  clip_ratio: 0.2
  loss_agg_mode: token-mean
  entropy_coef: 0.001          # 早期使用，稳定后可降为 0

algorithm:
  adv_estimator: grpo
  norm_adv_by_std_in_grpo: true
  filter_groups:
    enable: true
    metric: score
```

配置键必须在训练镜像锁定的 veRL commit 上做 preflight；不能直接假设最新文档键名与 Ascend 镜像完全一致。缺失或未生效的稳定性键属于 smoke 失败，不能静默回退到框架默认值。

选择依据：

- `n=8` 是待 Stage 0 验证的候选；只有它能显著降低近零方差组、且吞吐可接受时才采用；
- 把 prompt batch 从 8 调为 4，保持每步 32 个 rollout，不直接翻倍 rollout 总量；
- RL 学习率从已验证的 `5e-7` 起步；
- SFT/RFT 模型同时作为 reference，避免向基座模型漂移；
- token-mean、EOS 和 soft overlong shaping 从 smoke 起控制 DSL 长度；长度超过 SFT 合格样本 P95 + 预留 buffer 时逐步扣分，命中 max response length 时硬扣；
- 如果 response length 仍持续增长，消融 `norm_adv_by_std_in_grpo=false`（Dr.GRPO）；
- 如果出现明显长输出偏置，再启用 DAPO 的 overlong shaping 与 clip-higher。

训练节奏：

| 阶段 | 步数 | 目的 |
| --- | ---: | --- |
| smoke | 20 | 验证 reward、KL、反向、NPU 内存和退出码 |
| pilot | 100 | 检查 reward hacking、零方差、长度和 canary |
| main | 300–600 | 只在 pilot 通过后启动 |

现有 GSM8K 验证约 265 秒/step。按相同 32 rollout 机械估算，100/300/600 step 为 7.4/22/44 小时。**这只是未计入 3.7× 最大序列长度、converter 和 reward 计算的理论下界，不能作为排期承诺**；正式排期必须以 Stage 0.5 和 20-step smoke 实测为准。

### Stage C：L2 校准与二次离线优化

初版不把设备渲染强行塞进每个 GRPO rollout：

- 每 25–50 step：固定 16 条 canary，T=0，完整渲染 + L2；
- 每 100 step：从当前策略抽样 128–256 条，执行 L2 与人工抽检；
- 将 L2 高低分候选加入下一轮 RFT/DPO buffer；
- 不把跨多个 checkpoint 的陈旧 L2 reward 混进当前 on-policy batch；
- 如果渲染服务能在训练 update 前返回同批 reward，才试验同步 L2-GRPO。

veRL 当前 Reward Loop 支持自定义同步/异步 reward。异步只用于并发等待同一 rollout 的 verifier，不能演化为不受控的跨版本 stale reward。

## 7. 训练监控与自动停机

### 7.1 每 step 记录

- `reward/total` 与每个 reward component；
- 每条规则族的 finding 数与贡献；
- `group_reward_std`、零方差 group 比例、被过滤 group 比例；
- 解析率、转换率、checker exit 2、timeout 和重试率；
- response length P50/P95/max、EOS、clip ratio；
- KL、entropy、clipfrac、importance ratio、grad norm；
- rollout、转换、L1、L2、actor update 的耗时；
- 每个 checkpoint 的完整 canary 输出和渲染图。

### 7.2 Canary

固定 16 条、T=0、同 tokenizer/chat template/stop tokens：

- 每 25–50 step 生成一次；
- 保存 Compact DSL、A2UI、截图、dump、findings 和 reward breakdown；
- 与 SFT、上一个 checkpoint 和 last-good checkpoint 并排对比；
- canary 永不进入训练集，也不在训练中修改。

Canary 只负责快速报警，不用于选择最佳 checkpoint。最佳/last-good checkpoint 在固定 dev62 上选择：先满足转换率、`content_pass_rate` 和 P0 的硬门禁，再按冻结的 `dev_layout_score` 排序；同分时选择 response P95 更短、KL 更低的 checkpoint。final test 只在配置与 checkpoint 冻结后运行一次。

### 7.3 停机/回滚条件

出现任一情况立即暂停：

- 转换率相对 last-good 下降 >0.5 个百分点；
- 固定 dev 的 `content_pass_rate` 下降 >1 个百分点，或在线 5-step EWMA 持续下降并出现非法 path/asset/event；
- canary P0 增加，或 overlap/截断重新出现；
- response P95 相对 SFT 增长 >10%，或 clip ratio >1%；
- checker exit 2/timeout >0.5%；
- `group_reward_std < 1e-4` 的近零方差 group 连续 5 个窗口 >50%；
- KL、entropy 或 grad norm 相对稳定区间突然异常；
- total reward 上升而 L2/人评下降。

回滚到 last-good checkpoint 后，先审计 reward 和数据，不先换算法。

## 8. 评测设计

### 8.1 必须报告的基线

1. SFT greedy；
2. SFT Best-of-8 + checker rerank（无训练）；
3. RFT/DPO checkpoint；
4. GRPO，只有 L1/静态布局奖励；
5. GRPO + L2 校准；
6. 如长度漂移，再比较 Dr.GRPO/DAPO 稳定化版本。

Best-of-8 rerank 是重要强基线：如果它已经拿到大部分收益，应先评估线上推理成本，再判断 RL 是否值得。

### 8.2 评测口径

- headline：T=0、同一 vLLM/转换器/质检器版本；
- 辅助：T=0.8 的 pass@8、best-of-8；
- 3 个训练随机种子；
- 样本级 paired bootstrap 95% CI；
- 最终至少对 300 对 SFT/RL 渲染图做盲评，随机左右顺序；Stage 0 的 200 对只用于奖励校准；
- 分别报告 2×2、场景、组件数、文本长度和难度分桶；
- 训练 reward、自动指标和人工偏好分开报告。

按二项近似，200 对盲评通常需要约 57% 的观察胜率，95% CI 下界才可能高于 50%；300 对仍需约 56%。正式实验在标注前按期望最小效应做 power analysis，并预注册样本量、tie 处理和 bootstrap 方法。

### 8.3 消融矩阵

| 消融 | 回答的问题 |
| --- | --- |
| 无 RFT warm-up | 离线阶段是否提升稳定性/样本效率 |
| N=4 vs N=8 | 组内差异是否值得额外采样 |
| 无内容覆盖门禁 | 是否出现删内容/空卡 reward hacking |
| 无静态布局代理 | L1 本身是否足够 |
| 无 L2 校准 | 静态分数是否真正转化为渲染质量 |
| 无长度项 | 是否出现输出增长或截断 |
| GRPO vs Dr.GRPO | std normalization 是否造成长度偏置 |
| 固定/自适应难度采样 | 零方差 group 是否下降 |
| KL `1e-4/1e-3/1e-2` | 探索、布局改善与 SFT 能力保持的平衡 |

消融必须保持数据、rollout 数、训练步数和硬件预算一致，不能把更多数据的收益归因于算法。

Reference 始终使用进入当前 RL 阶段的 SFT/RFT checkpoint，不以基座模型作弱 reference；需要更多探索时调低 KL 系数、提高采样多样性或调整课程，避免把格式与可转换能力一起放掉。

## 9. 建议工程目录

```text
frameworks/verl/create_my_card/rl/
├── README.md
├── prepare_rl_dataset.py
├── run_grpo.sh
├── configs/
│   ├── reward_v1.yaml
│   └── grpo_v1.yaml
├── reward/
│   ├── compute_score.py
│   ├── design_checker_adapter.py
│   ├── static_layout_score.py
│   ├── content_coverage.py
│   └── schema.py
├── rollout/
│   └── temp_artifact_store.py
└── evaluation/
    ├── build_canary.py
    ├── evaluate_checkpoint.py
    ├── render_l2_sample.py
    └── paired_bootstrap.py
```

`compute_score.py` 对 veRL 暴露统一入口；内部步骤固定为：

```text
solution_str
  → convert_compact_dsl_to_a2ui(..., task_spec=...)
  → content coverage
  → design-check L1
  → static layout proxy
  → optional render/L2
  → reward schema v1
```

reward 输出不仅返回 scalar，还要保存可审计结构：

```json
{
  "score": 0.73,
  "masked": false,
  "components": {
    "contract": 1.0,
    "content": 0.9,
    "static_layout": 0.55,
    "style": 0.8,
    "efficiency": 1.0
  },
  "findings": [],
  "versions": {}
}
```

## 10. 主要风险与控制

| 风险 | 表现 | 控制 |
| --- | --- | --- |
| 空卡/删内容骗分 | overlap 少但信息缺失 | 内容覆盖硬门禁、占用率区间、人工 pair |
| 质检器误报 | reward 与人评冲突 | 规则族校准、L2/人评相关性、版本 pin |
| 2×2 L1 覆盖不足 | reward 上升但截图不变 | 静态代理 + 固定 L2 canary；不宣称 L1 等于视觉质量 |
| 设备渲染不稳定 | exit 2、桌面 dump、timeout | mask/retry；检查 app bundle；不惩罚策略 |
| 零方差组 | GRPO 无策略梯度 | N=8、learnability 采样、filter_groups |
| 长度膨胀 | DSL 越来越长、截断 | token-mean、长度带、Dr.GRPO/DAPO 消融 |
| SFT 能力遗忘 | 可转换率下降 | SFT/RFT reference、KL、canary、低 LR |
| train/eval 漂移 | reward 高、离线评测低 | 相同模板、stop token、converter、checker 和 engine |
| 奖励版本漂移 | 同 checkpoint 分数变化 | manifest 记录所有 hash，评测冻结版本 |

## 11. 里程碑与 Go/No-Go

### M1：奖励可用

- 产出 reward adapter、静态布局代理、版本 manifest；
- 完成 SFT greedy、N=4/N=8 基线和近零方差统计；
- 静态代理通过 L2/人评相关性门槛，200 对校准人评证明 reward 排序有效；
- 完成 5632 长序列、N=8 和关键 veRL 配置键的 Ascend preflight；
- 无明显空卡、长度或组件数投机。

### M2：离线提升

- 完成 RFT/DPO；
- dev62 和 canary16 的布局指标优于 SFT；
- 转换率、内容覆盖不退化。

### M3：GRPO pilot

- 20-step smoke + 100-step pilot；
- 零方差、KL、entropy、长度均在门槛内；
- canary 实际截图改善，而非只看 reward。

### M4：正式训练与结论

- 300–600 step、3 seeds；
- ≥300 条 final test；
- 自动指标 + 人评 + 配对置信区间；
- 完成消融和失败案例复盘。

任一阶段未过门槛，回到奖励/数据，不继续堆训练步数。

## 12. 参考依据

- [veRL 仓库](https://github.com/verl-project/verl)与[论文](https://arxiv.org/abs/2409.19256)：GRPO、custom reward、group filtering 和 Ascend 现有工程链路的基础。
- [veRL 自定义奖励文档](https://verl.readthedocs.io/en/latest/preparation/reward_function.html)与[Reward Loop](https://verl.readthedocs.io/en/latest/advance/reward_loop.html)：同步/异步规则奖励接口。
- [DAPO](https://arxiv.org/abs/2503.14476)：token-level loss、clip-higher 和 overlong shaping。
- [Dr.GRPO](https://arxiv.org/abs/2503.20783)：移除 group std normalization，作为长度稳定性消融。
- [Search-R1](https://github.com/PeterGriffinJin/Search-R1)：可验证 outcome reward + GRPO 的公开参考。
- [RAGEN](https://github.com/RAGEN-AI/RAGEN)：零方差、训练稳定性和 agentic RL 诊断参考。
- [AgentCPM-GUI](https://github.com/OpenBMB/AgentCPM-GUI)：移动场景 SFT + reinforcement fine-tuning 的邻近案例；其任务是 GUI 操作，不应直接照搬奖励。
- 本仓库 `docs/qwen36_gsm8k_grpo_validation.md`：16 个逻辑 Ascend NPU 上的 veRL GRPO 工程、吞吐、长度和零方差实测。
- 本仓库 `docs/create_my_card/data-quality-spec.md`：TaskSpec、A2UI、布局、round-trip 与 SFT 数据的质量合同。
- `design-card-check-plugin 0.2.0` 的 `README-DIST.md`、`SKILL.md`、五个 package manifest 与 `check_card.py`：规则范围、finding schema 和退出码契约。
