# CreateMyCard 当前奖励机制方案

本文说明奖励公式、门禁和证据语义；批量审计、canary 与 L2 操作见
[`../evaluation/README.md`](../evaluation/README.md)。

## 1. 方案状态

当前实现是 **Stage 0 离线奖励审计模块**，用于验证奖励信号是否稳定、可解释、可复现。它可以为模型生成的 Compact DSL 计算候选奖励并输出完整证据，但尚未接入 veRL/GRPO 在线训练。

当前配置固定为：

```json
{
  "status": "candidate_unvalidated",
  "policy_update_enabled": false
}
```

因此，当前输出只能用于离线比较、问题定位和奖励校准，不能直接驱动模型参数更新。

## 2. 设计目标

奖励机制需要同时回答以下问题：

1. 模型输出是否是合法、可转换的 Compact DSL；
2. 卡片是否只使用 TaskSpec 允许的数据、素材和事件；
3. 卡片是否覆盖了任务要求的主要信息；
4. 卡片结构、布局和样式是否符合设计规范；
5. 输出是否完整且不过度冗长；
6. 失败来自模型还是质检环境，避免把环境故障错误归因给模型。

## 3. 整体流程

```text
模型生成 Compact DSL
        │
        ▼
元数据检查
  TaskSpec / size / schema / token
        │
        ▼
Compact DSL 转 A2UI
  语法、组件树、协议结构
        │
        ▼
TaskSpec 上下文校验
  path / asset / event 白名单
        │
        ├──────────────┐
        ▼              ▼
信息覆盖度检查       design-card-check
主要路径/文字/事件    L1 静态质检
合法率/信息预算       可选 L2 dumpLayout
        │              │
        └──────┬───────┘
               ▼
         输出效率检查
               │
               ▼
       加权分数 + 硬门禁
               │
               ▼
 create-my-card.reward-audit.v1
```

主计算入口是 `reward/compute_score.py` 中的 `RewardComputer.compute()`。

## 4. 输入

每个候选至少需要：

```json
{
  "id": "case-001",
  "designCompactDsl": "...",
  "taskSpec": {},
  "finishReason": "stop",
  "completionTokens": 812
}
```

可选输入包括：

- 人工复核后的主要信息标签；
- CardSpec；
- 与样本对应的真实渲染 `dumpLayout`。

## 5. 奖励分量

五个基础分量均归一化到 `[0, 1]`，当前权重如下：

| 分量 | 权重 | 主要来源 | 当前含义 |
|---|---:|---|---|
| `contract` | 0.25 | DSL 转换器、TaskSpec 校验、质检器 | 协议、组件结构和能力合同正确性 |
| `content` | 0.20 | 信息覆盖度程序 | 主要信息召回、白名单合法率和信息数量预算 |
| `static_layout` | 0.45 | design-card-check L1 | 声明式布局、间距、密度、区域和几何规则 |
| `style` | 0.05 | design-card-check L1 | 颜色、字体、形状、图标和视觉规则 |
| `efficiency` | 0.05 | 生成元数据 | 输出是否完整、简洁且没有额外包装 |

当五个分量均可计算时，候选基础分为：

```text
base_score =
    0.25 × contract
  + 0.20 × content
  + 0.45 × static_layout
  + 0.05 × style
  + 0.05 × efficiency
```

缺少任一必要分量时不会重新归一化权重：

- `score = null`；
- 已知分量只写入 `partial_score`，供诊断使用；
- `partial_score` 不能作为正式训练奖励。

## 6. 信息覆盖度

### 6.1 主要信息标签

信息覆盖度采用“预定义标签 + 静态抽取比对”的确定性方案，不调用模型裁判。每个任务的标签示例：

```json
{
  "reviewed": true,
  "required_primary_paths": [
    "/data/weather/current/temperatureText"
  ],
  "required_primary_texts": [
    "上海天气"
  ],
  "required_events": [
    {
      "call": "clickToDeeplink",
      "args": {
        "intentName": "Weather_CityCode",
        "bundleName": "",
        "abilityName": "",
        "uri": "hww://www.huawei.com/totemweather?enterType=share&cityCode="
      }
    }
  ],
  "reference_content_budget": {
    "facts_min": 1,
    "facts_max": 3
  }
}
```

标签含义：

- `required_primary_paths`：必须使用的数据绑定路径；
- `required_primary_texts`：必须出现的固定文字；
- `required_events`：必须提供的完整交互 handler；比较前会统一事件参数中的绑定表示，再精确比较 `call + args`；
- `required_event_calls`：兼容旧标签的粗粒度调用名检查，无法区分同一 `call` 的不同目标；
- `facts_min/facts_max`：允许展示的数据绑定数量范围；
- `reviewed=true`：标签经过人工确认，可以参与计分。

`evaluation/build_content_label_review.py` 可以从 SFT 标准答案提取候选证据，生成待审核模板。程序不会自动把所有 schema 字段都当作主要信息。

### 6.2 从生成结果抽取证据

Compact DSL 转成 A2UI 后，程序从可见组件中抽取：

- `content`、`label`、`value`、`total`、`src`、`select` 中的数据绑定路径；
- `content`、`label` 中的固定文字；
- `Image`、`ActionUnit` 使用的素材；
- `onClick` 中的事件及事件调用名。

当前匹配方式为：

- 数据路径完全匹配；
- 事件调用名完全匹配；
- 必要文字在可见固定文字中进行子串匹配；
- 不做同义词、改写或语义等价判断。

### 6.3 计算公式

主要信息召回率：

```text
primary_recall = 命中的必要路径、文字和事件数 / 必要项总数
```

TaskSpec 白名单合法率：

```text
allowed_precision = 合法的路径、素材和事件数 / 实际使用总数
```

信息数量预算当前只统计去重后的数据绑定路径：

```text
budget_ok = facts_min <= len(used_paths) <= facts_max
```

最终信息覆盖分：

```text
content_score = primary_recall × allowed_precision × budget_ok
```

当前只有 `content_score == 1.0` 才不会触发覆盖失败门禁。即使静态覆盖达到 `1.0`，也只代表信息已经声明，真实渲染中的遮挡、截断和屏外不可见仍需 L2 验证。

### 6.4 标签缺失

以下情况不会猜测主要信息，也不会给模型负分：

- 没有标签；
- `reviewed` 不是 `true`；
- 主要项为空，但内容预算要求至少展示一项。

此时 `content.value=null`，门禁状态为 `audit_only`，样本不能形成完整候选分。

## 7. 设计质检器

核心规则不是本项目重新实现，而是调用 vendored 的 `design-card-check 0.2.0`
最小运行快照：

```text
vendor/design-card-check-plugin-0.2.0/package/design-check/scripts/check_card.py
```

该固定版本已随项目入库，默认不依赖机器上的下载目录。
`DESIGN_CHECK_ROOT` 和 `--checker-root` 只作为显式覆盖入口。

`reward/design_checker_adapter.py` 负责：

1. 创建包含 `query.txt`、`task-spec.json` 和 `card.genui.jsonl` 的临时样本目录；
2. 调用质检器并请求 JSON 输出；
3. 解析规则 findings；
4. 校验退出码和 findings 是否一致；
5. 处理超时、重试和环境故障；
6. L2 时传入 `dumpLayout` 并按需启用 delegated 规则。

质检器退出码语义：

| 退出码 | 含义 | 奖励处理 |
|---:|---|---|
| `0` | 有效检查结果，未发现 P0 | 正常计分 |
| `1` | 有效检查结果，发现 P0 | 正常解析 findings，并触发 P0 门禁 |
| `2` | 输入、质检器或运行环境故障 | 重试；仍失败则 mask 样本 |
| 其他 | 未定义异常 | mask 样本 |

质检 finding 按规则前缀映射到 `contract`、`static_layout` 和 `style`。当前严重度惩罚为：

| 严重度 | 单条惩罚 |
|---|---:|
| P0 | 1.00 |
| P1 | 0.25 |
| P2 | 0.05 |

同一规则、同一元素的重复 finding 只惩罚一次。当前只有质检器标记为“程序已证实”的证据参与加权惩罚，避免把需要设备或人工确认的问题直接计入模型奖励。

## 8. L1 与 L2

### L1：静态检查

L1 直接检查生成后的 A2UI 声明，适合覆盖所有 rollout，主要检查：

- 协议与组件结构；
- 字体、颜色、间距和尺寸；
- 声明式布局、密度和区域规则；
- TaskSpec 场景、素材和尺寸相关规则。

L1 速度快、结果确定，但不能确认真实渲染后的遮挡、截断和最终位置。

### L2：真实渲染检查

L2 使用设备或模拟器产生的 `dumpLayout`，用于检查：

- 真实坐标与尺寸；
- 越界和截断；
- 组件重叠；
- DSL 声明与真实渲染结果的差异。

`evaluation/render_l2_sample.py` 用于生成渲染载荷；配置本地 HTTP 渲染服务后会远程
取得 `dumpLayout` 和截图，未配置服务 URL 时仍可选择调用质检包的
`render_eval_dump.py`。完整联调流程见仓库的
`docs/create_my_card/local-render-service.md`。

基线配置中 L2 诊断分量权重为 `0`，只作为离线证据写入审计结果。候选配置
`reward_visual_candidate.json` 提供一个仍然禁止策略更新的校准入口：存在真实
layout dump 时，将 75% L2 几何分与 25% L1 声明布局分混合成
`static_layout`，并对重叠、文字压扁、安全区越界和底部越界设置
`visual_integrity` 门禁。没有 layout dump 时不启用该混合。

这不是已定稿的训练权重。它只用于真实候选 + L2 + 人评的相关性实验，完成稳定性
验证前不得开启 `policy_update_enabled`。

### 当前视觉覆盖缺口

- 954 条 SFT gold 的 L1 布局 finding 几乎都来自标题字号，L1 不能代表真实几何；
- 横向文字截断没有完整规则，现有 `TEXT_SQUASH` 只覆盖高度压扁；
- 留白主要依赖底部锚点代理，没有全局占用率和左右/顶部留白度量；
- vendored 2×4 规则包含历史人工裁决表和少量样本校准阈值。

奖励适配器会把所有真实 rollout 的 checker case id 强制加上 `rl-` 前缀，避免
模型样本 id 误触发 `A-q8`、`B-q20` 一类历史人工裁决。阈值本身仍需在真实生成
分布上重新校准，不能因为回归测试通过就认为具备泛化性。

## 9. 输出效率

输出效率根据 `finishReason`、`completionTokens` 和输出包装计算：

`completionTokens` 指模型 completion 本文在训练/rollout tokenizer 下、
`add_special_tokens=False` 的 token 数，不包含 prompt 或 chat template 控制 token。
历史数据缺少该字段时，`audit_rewards.py --tokenizer-path` 可按同一口径补算；
缺失的 `finishReason` 只能通过 `--default-finish-reason` 显式补充。

- `completionTokens <= 1400`：`efficiency=1.0`；
- `1400 < completionTokens < 1536`：从 `1.0` 线性下降到 `0.0`；
- `completionTokens >= 1536`：`efficiency=0.0`；
- `finishReason == "length"`：`efficiency=0.0`；
- 输出包含 `<think>` 或以 Markdown 代码块开头：`efficiency=0.0`；
- 缺少 token 数：`efficiency=null`，样本不能形成完整候选分。

## 10. 不可补偿门禁

加权分之外还存在硬门禁，防止其他分量的高分抵消关键错误：

| 条件 | 处理结果 |
|---|---|
| Compact DSL 无法解析或转换 | `score=-1` |
| 使用非法 TaskSpec 路径、素材或事件 | `score` 最高限制为 `-0.5` |
| `content_score < 1.0` | `score` 最高限制为 `-0.5` |
| 质检器发现 P0 | `score` 最高限制为 `0` |
| 质检器超时、exit 2 或输出损坏 | `masked=true`，不惩罚模型 |
| 奖励元数据本身无效 | `masked=true`，不惩罚模型 |

门禁使用上限约束而不是简单扣分。例如基础分为 `0.85`，但信息覆盖失败，最终分数最多为 `-0.5`。

## 11. 审计输出

每个样本输出 `create-my-card.reward-audit.v1` 记录，主要字段包括：

- `score`：完整候选分或门禁结果；
- `partial_score`：缺少分量时的已知贡献，仅用于诊断；
- `components`：各奖励分量、权重、来源和证据；
- `gates`：每个硬门禁的判定和动作；
- `findings`：质检器原始问题列表；
- `masked`：是否因环境或元数据问题屏蔽；
- `retryable`：失败是否适合重试；
- `policy_update_eligible`：当前恒为 `false`。

## 12. 代码对应关系

| 文件 | 职责 |
|---|---|
| `reward/compute_score.py` | 奖励编排、分项计分和硬门禁 |
| `reward/content_coverage.py` | 主要信息覆盖与 TaskSpec 白名单证据 |
| `reward/design_checker_adapter.py` | 调用和解析现有质检器 |
| `reward/schema.py` | 奖励审计数据结构 |
| `configs/reward_stage0.json` | 权重、规则映射和阶段开关 |
| `configs/reward_visual_candidate.json` | 禁止训练的 L2 视觉校准候选配置 |
| `evaluation/audit_rewards.py` | 批量离线审计入口 |
| `evaluation/analyze_reward_groups.py` | greedy + sampled 组内方差与结构审计 |
| `evaluation/build_reward_canary.py` | 构造固定 reviewed 跨领域 canary parquet |
| `evaluation/build_content_label_review.py` | 生成主要信息标签审核模板 |
| `evaluation/render_l2_sample.py` | 准备或执行 L2 渲染样本 |
| `evaluation/run_reward_separation_server.sh` | 真实 SFT 候选生成与双配置审计入口 |
| `tests/test_reward_stage0.py` | 奖励机制回归测试 |

## 13. 当前限制与下一阶段

当前方案已经形成可运行、可审计的离线闭环，但仍存在以下限制：

1. 信息覆盖是精确规则匹配，不理解同义表达；
2. L1 只能检查声明式布局，不能代表真实渲染质量；
3. L2 尚未获得足够样本和人评相关性证据，权重仍为零；
4. `static_layout`、`content`、`style` 和 `efficiency` 尚未全部完成奖励校准；
5. 当前通过 Python 子进程调用质检器，尚未进行在线 rollout 吞吐优化；
6. 尚未接入 veRL/GRPO 的 reward function 入口。

进入在线训练前至少需要完成：

1. 在固定 canary 集上运行 SFT greedy 和 Best-of-N 候选；
2. 对选定样本执行 L2 和盲评；
3. 检查奖励与人评相关性、零方差和规则误判；
4. 检查模型是否通过缩短输出、减少组件或省略信息投机；
5. 确认所有参与训练的分量已经校准；
6. 再启用 `policy_update_enabled` 并接入在线 GRPO。
