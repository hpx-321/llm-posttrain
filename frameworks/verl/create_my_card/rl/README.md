# CreateMyCard RL

本目录实现第一个任务 `TaskSpec → 完整 Design Compact DSL` 的候选奖励，以及最小的
`RFT → DPO → GRPO` 多阶段后训练骨架。第二个“一轮图文反馈修改”任务尚未接入。

## 当前状态

- 奖励模块和离线评估工具已经实现，但尚未完成 L2/人评相关性、组内区分度、
  reward hacking 和 holdout 评估；
- `reward_stage0.json` 与视觉候选配置都保持 `policy_update_enabled=false`；
- 三阶段 mock 编排和单元测试已跑通；目标 Ascend 环境上的 RFT、DPO 两阶段
  checkpoint-free smoke 也已各完成 2 个 optimizer step；
- RFT 复用现有 veRL FSDP SFT；DPO 按 veRL 官方离线 DPO RFC 的
  `TrainingWorker`/FSDP 结构做 0.7.1 兼容适配，项目只保留 veRL 实现和外部
  launcher 扩展点；
- 候选生成可直接消费版本内 TaskSpec/system prompt，并记录生成 checkpoint；奖励审计
  与 RFT/DPO builder 已形成项目内文件闭环；
- RFT/DPO smoke 都只跑少量 optimizer step，不保存 checkpoint；
- 5632 极限长序列和 N=8 rollout preflight 尚未完成；奖励未评估，因此尚未开始
  RFT/DPO 正式训练或 GRPO 策略更新。

## 目录导航

| 目录或入口 | 职责 | 文档 |
| --- | --- | --- |
| `reward/` | 单候选奖励计算、内容覆盖、质检适配和 veRL adapter | [`reward/README.md`](reward/README.md) |
| `evaluation/` | 离线 reward audit、canary、组内方差和 L2 渲染准备 | [`evaluation/README.md`](evaluation/README.md) |
| `pipeline/` | RFT/DPO/GRPO 数据构造、阶段编排和 checkpoint 串接 | [`pipeline/README.md`](pipeline/README.md) |
| `training/` | veRL 0.7.1 DPO 数据/loss/Trainer 适配和外部 launcher 边界；RFT 复用 SFT | 见 pipeline 文档 |
| `configs/` | pipeline 配置和两份未校准奖励配置 | — |
| `tests/` | 奖励与流水线回归测试 | — |
| `vendor/` | 固定版本的 design-card-check 最小运行快照 | — |
| `run_pipeline.py` | 多阶段 runner 的顶层入口 | 见 pipeline 文档 |

训练、评估和奖励实现彼此独立：runner 不读取评估结论，也不计算文件 SHA；评估模块
只消费候选和奖励输出；奖励模块不知道 RFT/DPO 的数据选择逻辑。

## 最小流程

```text
TaskSpec
  ├─ candidate generation → reward audit → RFT/DPO 数据
  └─ GRPO prompt → online reward

base SFT → RFT checkpoint → DPO checkpoint → GRPO checkpoint
```

RFT 完成后需要使用 RFT checkpoint 重新采样 DPO 候选；DPO 完成后再以 DPO
checkpoint 作为 GRPO 的 actor/reference 起点。因此 pipeline 支持在 RFT、DPO 后暂停
并恢复，而不把三个阶段包装成一次不可拆分的运行。

## 快速检查

从仓库根目录验证配置和 mock 编排：

```bash
python frameworks/verl/create_my_card/rl/run_pipeline.py validate \
  --config frameworks/verl/create_my_card/rl/configs/pipeline_taskspec_dsl.json

python frameworks/verl/create_my_card/rl/run_pipeline.py run \
  --config frameworks/verl/create_my_card/rl/configs/pipeline_taskspec_dsl.json \
  --run-id local-scaffold \
  --backend mock
```

运行回归测试：

```bash
python -m pytest frameworks/verl/create_my_card/rl/tests -q
```

完整的 TaskSpec → 候选 → 奖励 → RFT/DPO 数据 → 两阶段训练命令见
[`pipeline/README.md`](pipeline/README.md)；真实奖励候选实验、L2 准备和输出解释见
[`evaluation/README.md`](evaluation/README.md)。正式训练前仍需先完成奖励评估；代码
跑通只代表模块合同可用，不代表奖励有效或指标已经达成。
