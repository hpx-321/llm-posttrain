# TaskSpec → DSL 多阶段后训练骨架

本目录提供一个最小、可暂停和可恢复的 `RFT → DPO → GRPO` 串行训练骨架，当前只
覆盖：

```text
TaskSpec → 完整 Design Compact DSL
```

runner 只负责把 checkpoint 和训练数据交给三个阶段，不负责奖励评估、实验审批或
制品审查。候选生成、奖励计算、数据构造和训练启动彼此独立，方便单独替换或测试。

## 最小流程

```text
base SFT checkpoint
  └─ RFT 数据 → RFT → RFT checkpoint
                    └─ DPO pair → DPO → DPO checkpoint
                                      └─ GRPO prompt + online reward
                                           → GRPO checkpoint
```

RFT 和 DPO 数据依赖前一阶段策略的候选，因此服务器上通常分三次执行：RFT 后暂停，
用 RFT checkpoint 重新采样并构造 DPO pair；DPO 后再准备 GRPO prompt 并继续。

## 模块职责

| 模块 | 只负责什么 |
| --- | --- |
| `contracts.py` | 阶段、命令、checkpoint 的小型数据结构 |
| `config.py` | 读取并校验 JSON 配置 |
| `data.py` / `data_cli.py` | 生成 RFT、DPO、GRPO 各自需要的原生训练文件 |
| `backends.py` | 可替换的 `mock` 与 `command` 执行后端 |
| `runner.py` | 顺序执行、暂停/恢复和 checkpoint 串接 |
| `reward/verl_adapter.py` | 将 veRL custom reward 参数转换为 `RewardComputer` 输入 |
| `training/` | RFT、DPO、GRPO 的启动脚本边界 |

项目不再包含 `assessment.py`、`provenance.py`、文件 SHA 校验或
`dataset-manifest.json`。后续评估可以单独输出报告，但不会反向耦合 runner。

## 运行模式

- `scaffold`：只能搭配 `--backend mock`，验证三阶段顺序、暂停恢复和 checkpoint
  串接，不包含真实模型权重。
- `smoke`：允许 command 后端，用少量 optimizer step 检查训练环境和数据格式；不保存
  或合并 checkpoint，下一阶段继续复用本次输入 checkpoint。
- `train`：执行配置中的真实命令。runner 只检查输入 checkpoint、数据目录、配置中
  声明的训练文件和输出 checkpoint 是否存在。

同一份配置默认保持 `scaffold`，真实运行时用 `--mode smoke` 或 `--mode train`
覆盖；基础模型路径用 `--base-checkpoint` 覆盖。暂停后恢复时必须继续传入相同的两个
值，避免串错 checkpoint。

`train` 不再要求独立 assessment。GRPO 是否允许使用当前奖励，由奖励配置中的
`policy_update_enabled` 和 `validated_for_policy_update` 决定；未验证奖励只能通过
`CMC_ALLOW_UNVALIDATED_REWARD=1` 做 smoke，不能作为正式训练结果。

## 本地验证骨架

从仓库根目录运行：

```bash
python frameworks/verl/create_my_card/rl/run_pipeline.py validate \
  --config frameworks/verl/create_my_card/rl/configs/pipeline_taskspec_dsl.json

python frameworks/verl/create_my_card/rl/run_pipeline.py run \
  --config frameworks/verl/create_my_card/rl/configs/pipeline_taskspec_dsl.json \
  --run-id local-scaffold \
  --backend mock
```

测试分段执行：

```bash
python frameworks/verl/create_my_card/rl/run_pipeline.py run \
  --config frameworks/verl/create_my_card/rl/configs/pipeline_taskspec_dsl.json \
  --run-id staged-scaffold --backend mock --stop-after rft

python frameworks/verl/create_my_card/rl/run_pipeline.py run \
  --config frameworks/verl/create_my_card/rl/configs/pipeline_taskspec_dsl.json \
  --run-id staged-scaffold --backend mock --resume --stop-after dpo

python frameworks/verl/create_my_card/rl/run_pipeline.py run \
  --config frameworks/verl/create_my_card/rl/configs/pipeline_taskspec_dsl.json \
  --run-id staged-scaffold --backend mock --resume
```

恢复时只核对阶段、后端、运行模式、输入 checkpoint、输出 checkpoint 和数据目录。
正式训练确认已有输出 checkpoint 存在；smoke 则确认原输入 checkpoint 仍存在。配置
命令或数据内容发生变化时应使用新的 run id；runner 不再通过哈希推断内容是否变化。

## 数据构造

三个 builder 都拒绝覆盖已有训练文件，执行完成后在终端返回数量和筛选参数摘要，
不落额外数据清单。

### RFT

每个 `groupId` 选择一个达到阈值的最高分候选，输出 `train.parquet`、
`validation.parquet` 和便于排查的 `selection.jsonl`。同时把选中的训练行循环复制为
256 条 `oom_probe.parquet`，只供 checkpoint-free RFT smoke 获得完整 global batch；
`train` 模式仍只读取原始 `train.parquet`，不会使用重复样本。

```bash
python -m frameworks.verl.create_my_card.rl.pipeline.data_cli rft \
  --candidates <base候选.jsonl> \
  --audits <reward-audit.jsonl> \
  --taskspec <taskspec.json> \
  --system-prompt <system_prompt.txt> \
  --output-dir <run_dir>/datasets/rft \
  --expected-producer-checkpoint <base_sft_checkpoint>
```

需要只选择正式可训练奖励时，再显式增加 `--require-policy-update-eligible`；模块测试
和未校准阶段可以不加。

### DPO

chosen/rejected 必须来自同一 prompt，builder 只做分数阈值、最小分差和长度比例
过滤，输出 `train.jsonl` 与 `validation.jsonl`。DPO 模型由与 SFT 相同的 veRL
`TrainingWorker`/FSDP Engine 加载、分片和执行前反向；项目只增加
偏好数据编码、reference log-prob 和标准 sigmoid DPO loss 三层逻辑。

实现依据是 veRL 官方的
[`[RFC] Add trainer for Direct Preference Optimization`](https://github.com/verl-project/verl/discussions/6357)
和 RFC 作者公开的
[`dpo-dataset-pipeline`](https://github.com/zhexjtu/verl/tree/dpo-dataset-pipeline)
分支。veRL 0.7.1 尚未发布可直接调用的 `verl.trainer.dpo_trainer`，因此这里只回移
`TrainingWorker`、pair 保序和 loss scaling 等核心设计，不修改容器的 `site-packages`。

reference 不再常驻第二份 27B 模型。Trainer 在任何参数更新前，用初始 policy 的 FSDP
Engine 遍历 chosen/rejected 并把 completion log-prob 保存在内存中，后续训练期间固定
使用。动态 batching 使用 veRL 的 `force_group_size=2`，保证同一 pair 的 chosen 与
rejected 不会被拆到不同 micro-batch。DPO 数据固定关闭 Qwen thinking 模板，prompt
与完整序列必须通过相同 chat template 得到一致 token 前缀。

上层入口保持不变：仍由 `run_pipeline.py ... --stop-after dpo` 调用
`training/run_dpo_backend.sh`，再进入项目内 veRL 适配。已有候选生成、reward audit、
DPO builder 和 pipeline 命令无需改写。

`train` 模式先保存 veRL FSDP model-only checkpoint，再通过现有 merger 输出供后续
GRPO 使用的 Hugging Face checkpoint；`smoke` 默认跑 2 个 optimizer step，自动把
少量训练 pair 在内存中循环到一个 global batch，不保存或合并 checkpoint。目标环境
只需要现有 veRL SFT 训练依赖。`DPO_LAUNCHER` 可显式替换整个 DPO 启动实现，
但 pipeline 的输入输出合同保持不变。

如果 DPO 使用独立 Python 环境，可令 `DPO_PYTHON_BIN=/path/to/venv/bin/python`；设备
探测、分布式训练和 checkpoint 合并都会使用该解释器，避免与当前 shell 串环境。

veRL DPO 适配层的内部边界如下：

| 文件 | 职责 |
| --- | --- |
| `training/dpo_dataset.py` | JSONL 合同、非 thinking chat template、pair collator |
| `training/dpo_loss.py` | completion log-prob 聚合和标准 sigmoid DPO loss |
| `training/train_dpo_verl.py` | veRL SFTTrainer 适配、reference 预计算和分布式聚合 |
| `training/run_dpo_verl.sh` | veRL 参数、FSDP checkpoint 与 HF 合并 |

```bash
python -m frameworks.verl.create_my_card.rl.pipeline.data_cli dpo \
  --candidates <rft候选.jsonl> \
  --audits <reward-audit.jsonl> \
  --taskspec <taskspec.json> \
  --system-prompt <system_prompt.txt> \
  --output-dir <run_dir>/datasets/dpo \
  --expected-producer-checkpoint <rft_checkpoint>
```

## RFT → DPO 项目内闭环

四份训练文件不是仓库静态资源。它们由项目内现有模块按以下链路生成：

```text
taskspec.json + system_prompt.md
  → export_renderable_a2ui.py（策略采样，写 producerCheckpoint）
  → raw_compact_dsl.jsonl
  → audit_rewards.py
  → reward-audit.jsonl
  → data_cli rft/dpo
  → datasets/rft/{train,validation,oom_probe}.parquet + datasets/dpo/*.jsonl
  → run_pipeline.py
```

候选生成、奖励审计、数据选择和训练仍是四个独立入口；闭环依靠显式文件合同连接，
runner 不内嵌 vLLM 或奖励实现。所有命令均从仓库根目录执行。

### 一次跑通 RFT + DPO smoke

smoke 不保存 RFT checkpoint，因此 RFT 和 DPO 共用 base checkpoint 的同一批候选。
下面先取 16 个 TaskSpec，每个生成 1 条 greedy + 8 条采样候选：

```bash
RUN_ID=taskspec-dsl-smoke
BASE_MODEL=/mnt/model/qwen36-27b-create-my-card-sft-v1-merged
TOKENIZER=/mnt/model/Qwen3.6-27B
RUN_ROOT="outputs/rl-pipeline/${RUN_ID}"
PREP_ROOT="outputs/rl-preparation/${RUN_ID}/base"
GEN_DIR="${PREP_ROOT}/generation"
TASKSPEC="frameworks/verl/create_my_card/sft/data/source/taskspec.json"
SYSTEM_PROMPT="frameworks/verl/create_my_card/sft/data/source/system_prompt.md"
RAW_CANDIDATES="${GEN_DIR}/raw_compact_dsl.jsonl"
AUDITS="${PREP_ROOT}/reward-audit.jsonl"

python frameworks/verl/create_my_card/sft/evaluation/export_renderable_a2ui.py \
  --model-path "${BASE_MODEL}" \
  --producer-checkpoint "${BASE_MODEL}" \
  --tokenizer-path "${TOKENIZER}" \
  --taskspec-file "${TASKSPEC}" \
  --system-prompt "${SYSTEM_PROMPT}" \
  --output-dir "${GEN_DIR}" \
  --raw-only \
  --include-greedy \
  --num-samples 8 \
  --temperature 0.7 \
  --top-p 0.9 \
  --limit 16

python frameworks/verl/create_my_card/rl/evaluation/audit_rewards.py \
  --input "${RAW_CANDIDATES}" \
  --taskspec-file "${TASKSPEC}" \
  --output "${AUDITS}" \
  --fail-on-masked

python -m frameworks.verl.create_my_card.rl.pipeline.data_cli rft \
  --candidates "${RAW_CANDIDATES}" \
  --audits "${AUDITS}" \
  --taskspec "${TASKSPEC}" \
  --system-prompt "${SYSTEM_PROMPT}" \
  --output-dir "${RUN_ROOT}/datasets/rft" \
  --expected-producer-checkpoint "${BASE_MODEL}" \
  --allow-partial-score \
  --min-score -1.0

python -m frameworks.verl.create_my_card.rl.pipeline.data_cli dpo \
  --candidates "${RAW_CANDIDATES}" \
  --audits "${AUDITS}" \
  --taskspec "${TASKSPEC}" \
  --system-prompt "${SYSTEM_PROMPT}" \
  --output-dir "${RUN_ROOT}/datasets/dpo" \
  --expected-producer-checkpoint "${BASE_MODEL}" \
  --allow-partial-score \
  --chosen-min-score -1.0 \
  --min-score-margin 0.05 \
  --max-length-ratio 4.0

python frameworks/verl/create_my_card/rl/run_pipeline.py run \
  --config frameworks/verl/create_my_card/rl/configs/pipeline_taskspec_dsl.json \
  --run-id "${RUN_ID}" \
  --mode smoke \
  --base-checkpoint "${BASE_MODEL}" \
  --stop-after dpo
```

RFT 与 DPO 默认各做 2 个 optimizer step，不保存或合并 checkpoint。这里使用
`partial_score` 和宽松阈值只为验证机械链路；如果采样候选没有可用分差，DPO builder
会明确失败，此时应增加样本数或更换 TaskSpec，不能伪造偏好对。`--raw-only` 会跳过
空输出和因长度上限截断的候选；若某个 group 因此没有足够候选，数据构造同样会明确失败。
RFT smoke 读取 builder 生成的 256 条 `oom_probe.parquet`，因此少量 TaskSpec 不会因
小于分布式 global batch 而得到 `steps_per_epoch=0`。

### 带 checkpoint 的 RFT → 重新采样 → DPO

先从 base checkpoint 生成候选、审计并构造 RFT 数据，再保存 RFT checkpoint：

```bash
RUN_ID=taskspec-dsl-train
BASE_MODEL=/mnt/model/qwen36-27b-create-my-card-sft-v1-merged
TOKENIZER=/mnt/model/Qwen3.6-27B
RUN_ROOT="outputs/rl-pipeline/${RUN_ID}"
RFT_PREP="outputs/rl-preparation/${RUN_ID}/base"
RFT_GEN="${RFT_PREP}/generation"
TASKSPEC="frameworks/verl/create_my_card/sft/data/source/taskspec.json"
SYSTEM_PROMPT="frameworks/verl/create_my_card/sft/data/source/system_prompt.md"
RFT_CANDIDATES="${RFT_GEN}/raw_compact_dsl.jsonl"
RFT_AUDITS="${RFT_PREP}/reward-audit.jsonl"

python frameworks/verl/create_my_card/sft/evaluation/export_renderable_a2ui.py \
  --model-path "${BASE_MODEL}" \
  --producer-checkpoint "${BASE_MODEL}" \
  --tokenizer-path "${TOKENIZER}" \
  --taskspec-file "${TASKSPEC}" \
  --system-prompt "${SYSTEM_PROMPT}" \
  --output-dir "${RFT_GEN}" \
  --raw-only \
  --include-greedy \
  --num-samples 8 \
  --temperature 0.7 \
  --top-p 0.9

python frameworks/verl/create_my_card/rl/evaluation/audit_rewards.py \
  --input "${RFT_CANDIDATES}" \
  --taskspec-file "${TASKSPEC}" \
  --output "${RFT_AUDITS}" \
  --fail-on-masked

python -m frameworks.verl.create_my_card.rl.pipeline.data_cli rft \
  --candidates "${RFT_CANDIDATES}" \
  --audits "${RFT_AUDITS}" \
  --taskspec "${TASKSPEC}" \
  --system-prompt "${SYSTEM_PROMPT}" \
  --output-dir "${RUN_ROOT}/datasets/rft" \
  --expected-producer-checkpoint "${BASE_MODEL}" \
  --allow-partial-score \
  --min-score -1.0

python frameworks/verl/create_my_card/rl/run_pipeline.py run \
  --config frameworks/verl/create_my_card/rl/configs/pipeline_taskspec_dsl.json \
  --run-id "${RUN_ID}" \
  --mode train \
  --base-checkpoint "${BASE_MODEL}" \
  --stop-after rft
```

RFT 完成后，必须使用其合并 checkpoint 重新生成 DPO 候选，不能复用 base 候选：

```bash
RFT_CHECKPOINT="${RUN_ROOT}/stages/rft/merged-checkpoint"
DPO_PREP="outputs/rl-preparation/${RUN_ID}/rft-policy"
DPO_GEN="${DPO_PREP}/generation"
DPO_CANDIDATES="${DPO_GEN}/raw_compact_dsl.jsonl"
DPO_AUDITS="${DPO_PREP}/reward-audit.jsonl"

python frameworks/verl/create_my_card/sft/evaluation/export_renderable_a2ui.py \
  --model-path "${RFT_CHECKPOINT}" \
  --producer-checkpoint "${RFT_CHECKPOINT}" \
  --tokenizer-path "${TOKENIZER}" \
  --taskspec-file "${TASKSPEC}" \
  --system-prompt "${SYSTEM_PROMPT}" \
  --output-dir "${DPO_GEN}" \
  --raw-only \
  --include-greedy \
  --num-samples 8 \
  --temperature 0.7 \
  --top-p 0.9

python frameworks/verl/create_my_card/rl/evaluation/audit_rewards.py \
  --input "${DPO_CANDIDATES}" \
  --taskspec-file "${TASKSPEC}" \
  --output "${DPO_AUDITS}" \
  --fail-on-masked

python -m frameworks.verl.create_my_card.rl.pipeline.data_cli dpo \
  --candidates "${DPO_CANDIDATES}" \
  --audits "${DPO_AUDITS}" \
  --taskspec "${TASKSPEC}" \
  --system-prompt "${SYSTEM_PROMPT}" \
  --output-dir "${RUN_ROOT}/datasets/dpo" \
  --expected-producer-checkpoint "${RFT_CHECKPOINT}" \
  --allow-partial-score \
  --chosen-min-score -1.0 \
  --min-score-margin 0.05 \
  --max-length-ratio 4.0

python frameworks/verl/create_my_card/rl/run_pipeline.py run \
  --config frameworks/verl/create_my_card/rl/configs/pipeline_taskspec_dsl.json \
  --run-id "${RUN_ID}" \
  --mode train \
  --base-checkpoint "${BASE_MODEL}" \
  --resume \
  --stop-after dpo
```

恢复时 `--base-checkpoint` 必须仍是最初的 base SFT checkpoint；runner 从 RFT stage
manifest 恢复实际的 `RFT_CHECKPOINT`。默认训练设备为 NPU；CUDA 环境在启动训练前设置
`TRAIN_DEVICE=cuda`。如目标服务器已有经过验证的 OpenRLHF 或其他 DPO 实现，可设置
`DPO_LAUNCHER` 覆盖内置后端，而无需改 runner 或数据格式。

以上 train 命令仍用 `--allow-partial-score` 和宽松阈值验证机械链路。reward 完成评估并把
配置中的 `policy_update_enabled` 打开后，正式实验必须移除 `--allow-partial-score`，并在
RFT、DPO 两条 `data_cli` 命令中增加 `--require-policy-update-eligible`。候选准备目录故意
放在 `outputs/rl-preparation/`，避免污染 runner 只管理的 `outputs/rl-pipeline/${RUN_ID}`。

### GRPO

输出 veRL 使用的 `train.parquet` 和 `validation.parquet`。TaskSpec 与内容标签以 JSON
字符串放入 `extra_info`，在线 reward adapter 再负责解码。

```bash
python -m frameworks.verl.create_my_card.rl.pipeline.data_cli grpo \
  --taskspec <taskspec.json> \
  --system-prompt <system_prompt.txt> \
  --labels <reviewed-content-labels.json> \
  --output-dir <run_dir>/datasets/grpo
```

内容标签是否必须人工复核由 `--require-reviewed-labels` 单独控制，不与 runner 绑定。

## 保留的必要检查

为了避免把路径错误误认为训练问题，command backend 仍会检查：

- 本阶段输入 checkpoint 存在；
- 数据目录和配置声明的 train/validation 文件存在；
- 训练命令退出码为 0；
- `train` 命令结束后确实产生输出 checkpoint；`smoke` 不要求也不保留 checkpoint。

这些是执行合同，不评价模型质量，也不计算文件指纹。

## 当前未完成

- 奖励相关性、人评、L2、零方差、长度投机和 holdout 评估尚未完成；
- RFT 与 veRL DPO 已在目标 Ascend 环境分别完成 2-step 真实梯度 smoke；smoke 按约定
  不保存 checkpoint，正式训练、checkpoint 合并和能力收益尚未验证；
- 5632 长序列与 N=8 rollout 的 Ascend preflight 尚未完成；
- GRPO 尚未执行 CreateMyCard 的真实梯度 smoke。
