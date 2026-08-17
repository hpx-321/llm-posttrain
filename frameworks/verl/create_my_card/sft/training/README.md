# 训练与检查点

本目录保存 veRL 训练、环境模板、检查点合并和合并后校验入口。以下命令均假设当前目录为 `sft/`。

## 实现职责

| 实现 | 职责 |
| --- | --- |
| `sft_dry_run.py` | 执行最长样本压力测试并禁止写 checkpoint |
| `best_sft_trainer.py` | 按 `val/loss` 保存全局最佳 FSDP 模型权重 |
| `validate_merged_model.py` | 检查合并目录、权重、config、tokenizer 和非思考模板 |

## 配置

```bash
cd /workspace/hql/llm-posttrain/frameworks/verl/create_my_card/sft
cp training/training.env.example /path/to/create_my_card.env
source /path/to/create_my_card.env
```

重点确认：

- `MODEL_PATH`：Qwen3.6 基座模型；
- `DATA_DIR`：包含 train、validation 和 oom_probe Parquet；
- `SAVE_PATH`：新的 FSDP checkpoint 目录；
- `NPROC_PER_NODE`：可用 NPU/GPU 数量；
- `MAX_LENGTH`：不得小于 Token 报告建议值；
- `MAX_TOKEN_LEN_PER_GPU`：动态 batch 的单卡 Token 预算；
- `TRAIN_BATCH_SIZE`：全局 batch，必须能被数据并行规模整除。

当前配置执行全参数 SFT，使用 FSDP、BF16、gradient checkpointing、dynamic batch、cosine scheduler 和 assistant-only loss mask。

## Dry-run

```bash
DRY_RUN=1 bash training/run_sft.sh
```

dry-run 使用 `oom_probe.parquet` 执行默认两步训练，不保存 checkpoint 或模型权重。若发生 OOM，依次尝试降低 `MAX_TOKEN_LEN_PER_GPU` 或开启 activation/optimizer/parameter offload；不要降低 `MAX_LENGTH` 截断数据。

## TensorBoard

`run_sft.sh` 同时启用 `console` 和 `tensorboard` logger，并启动或复用公共 dashboard。默认事件目录为 `/mnt/data/logs/verl_create_my_card_sft_1`，文本日志仍写入 `${LOG_DIR}/run-*.log`。

```bash
TENSORBOARD_DIR=/mnt/data/logs/my_create_my_card_sft \
TENSORBOARD_HOST=0.0.0.0 \
TENSORBOARD_PORT=6007 \
DRY_RUN=0 \
  bash training/run_sft.sh
```

默认访问地址为 `http://<训练机地址>:6006`。目标端口已有 TensorBoard 时会复用现有进程；不同事件目录应使用不同端口。

## 正式训练

```bash
DRY_RUN=0 bash training/run_sft.sh
```

临时覆盖 epoch：

```bash
TOTAL_EPOCHS=10 DRY_RUN=0 bash training/run_sft.sh
```

当前 checkpoint 策略：

- 每个 epoch 后验证，只有 `val/loss` 改善超过 `BEST_CKPT_MIN_DELTA` 才保存；
- checkpoint 只保留 FSDP 模型权重和模型/FSDP 配置；
- `MAX_CKPT_TO_KEEP=1` 默认只保留全局最佳模型；
- 最佳 step/loss 写入 `best_checkpointed_iteration.txt` 和 `best_validation_metrics.json`；
- 不保存 optimizer、scheduler/RNG 或 DataLoader 状态；
- `trainer.resume_mode=disable`，不支持断点续训；
- `SAVE_PATH` 已含 checkpoint 状态时拒绝启动。

每个 epoch 的优化 step 由当前训练集数量、全局 batch 和 veRL sampler 行为决定，不在文档中固化易漂移的样本数。

## 合并 FSDP checkpoint

```bash
SAVE_PATH=/mnt/model/qwen36-27b-create-my-card-sft-v1 \
CHECKPOINT_STEP=best \
MERGED_MODEL=/mnt/model/qwen36-27b-create-my-card-sft-v1-merged \
bash training/merge_fsdp_checkpoint.sh
```

`CHECKPOINT_STEP=best` 从最佳 tracker 读取 step，也可以指定正整数。`MERGED_MODEL` 必须是不存在的新目录，脚本不会覆盖已有模型；合并后自动运行同目录的 `validate_merged_model.py`。
