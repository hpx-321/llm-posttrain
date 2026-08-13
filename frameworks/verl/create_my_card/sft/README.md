# CreateMyCard veRL SFT

本目录维护 CreateMyCard 的监督微调与评测闭环：构建数据、分析 Token、训练、合并 FSDP 检查点，并导出评测所需的 Compact DSL 和可渲染 A2UI。

## 文件

```text
sft/
├── data/source/
│   ├── system_prompt.md
│   ├── taskspec.json
│   └── design_compact_dsl.jsonl
├── build_parquet.py
├── analyze_tokens.py
├── qwen36_sft_dataset.py
├── sft_dry_run.py
├── best_sft_trainer.py
├── run_sft.sh
├── merge_fsdp_checkpoint.sh
├── validate_merged_model.py
├── build_taskspec_test.py
├── export_renderable_a2ui.py
├── training.env.example
└── requirements.txt
```

核心依赖关系：

```text
source 数据
→ build_parquet.py
→ train.parquet + validation.parquet
→ analyze_tokens.py
→ token_stats.json + oom_probe.parquet
→ run_sft.sh
→ veRL FSDP checkpoints
→ merge_fsdp_checkpoint.sh
→ Hugging Face 模型
→ build_taskspec_test.py + export_renderable_a2ui.py
→ 原始 Compact DSL + 可渲染 A2UI
```

## 1. 构建数据

`taskspec.json` 每条记录包含 `id` 和 `taskSpec`；`design_compact_dsl.jsonl` 每行包含相同 `id` 和 `designCompactDsl`。构建器会检查 ID 唯一性和双向配对关系。

```bash
cd /workspace/hql/llm-posttrain/frameworks/verl/create_my_card/sft
pip install -r requirements.txt
python3 build_parquet.py
```

默认输出：

```text
data/parquet/train.parquet
data/parquet/validation.parquet
```

每行固定为：

```json
{
  "id": "sample-id",
  "messages": [
    {"role": "system", "content": "<system prompt>"},
    {"role": "user", "content": "<TaskSpec JSON>"},
    {"role": "assistant", "content": "<Design Compact DSL>"}
  ],
  "enable_thinking": false
}
```

验证集数量按32条对齐。当前192条数据默认拆分为160条训练、32条验证；扩充数据后仍按相同规则确定验证集，不强制固定比例。

## 2. Token 与 OOM 预检

训练前必须使用实际模型 tokenizer 分析全量数据：

```bash
python3 analyze_tokens.py \
  --model-path /mnt/model/Qwen3.6-27B \
  --probe-output data/parquet/oom_probe.parquet
```

输出：

- `token_stats.json`：训练集和验证集的 prompt、assistant、total Token 分布，最长样本及建议的 `MAX_LENGTH`。
- `oom_probe.parquet`：循环复制最长样本，用于两步显存压力测试。

脚本与训练 Dataset 共用同一套 Qwen3.6 chat template 编码逻辑，固定 `enable_thinking=false`。如果样本超过模型上下文长度，分析直接失败。

数据更新后需要重新运行，并把报告中的 `recommendedMaxLength` 同步到训练环境的 `MAX_LENGTH`。训练使用 `data.truncation=error`，不会静默截断 TaskSpec 或 DSL。

## 3. 配置训练

复制并修改环境文件：

```bash
cp training.env.example /path/to/create_my_card.env
source /path/to/create_my_card.env
```

必须重点确认：

- `MODEL_PATH`：Qwen3.6 基座模型。
- `DATA_DIR`：包含 train、validation 和 oom_probe Parquet。
- `SAVE_PATH`：FSDP 检查点目录。
- `NPROC_PER_NODE`：可用 NPU/GPU 数量。
- `MAX_LENGTH`：不得小于 Token 报告的建议值。
- `MAX_TOKEN_LEN_PER_GPU`：动态 batch 的单卡 Token 预算。
- `TRAIN_BATCH_SIZE`：全局 batch，必须能被数据并行规模整除。

当前配置执行全参数 SFT，使用 FSDP、BF16、gradient checkpointing、dynamic batch、cosine learning-rate scheduler 和 assistant-only loss mask。

`qwen36_sft_dataset.py` 通过 veRL 官方 `data.custom_cls` 扩展点加载。它一次性对完整 `system → user → assistant` 对话应用 Qwen3.6 chat template，避免默认 Dataset 分段套模板造成的不兼容。

## 4. Dry-run

先运行两步最长样本压力测试：

```bash
DRY_RUN=1 bash run_sft.sh
```

dry-run 使用 `oom_probe.parquet`，不会保存检查点或模型权重。若发生 OOM，优先依次尝试降低 `MAX_TOKEN_LEN_PER_GPU`、开启 activation/optimizer/parameter offload；不要降低 `MAX_LENGTH` 截断数据。

## 5. 正式训练

```bash
DRY_RUN=0 bash run_sft.sh
```

临时覆盖默认配置并训练 10 个 epoch：

```bash
TOTAL_EPOCHS=10 DRY_RUN=0 bash run_sft.sh
```

该命令只对本次运行生效；训练仍在每个 epoch 后验证，并且只保留 validation loss 最低的检查点。

默认行为：

- 每个 epoch 后验证；只有 `val/loss` 比历史最佳值降低超过 `BEST_CKPT_MIN_DELTA` 时才保存检查点。默认值 `0` 表示严格降低即可。
- 检查点只包含 FSDP 模型权重、Hugging Face 配置和 FSDP 配置，不保存 optimizer、scheduler/RNG 或 DataLoader 状态。
- `MAX_CKPT_TO_KEEP=1` 只保留全局最佳检查点。
- 最佳 step 和 loss 分别记录在 `best_checkpointed_iteration.txt` 与 `best_validation_metrics.json`。
- 训练固定使用 `trainer.resume_mode=disable`，不支持断点续训；`SAVE_PATH` 中存在旧检查点时会拒绝启动。
- 日志写到 `${LOG_DIR}/run-*.log`，同时输出到终端。

当前160条训练数据、全局 batch 32时，每个 epoch 有5个优化 step。训练中断后需要使用新的 `SAVE_PATH` 从头运行；该模式以降低磁盘占用为优先，不保留恢复训练所需状态。

## 6. 合并检查点

veRL FSDP checkpoint 不能直接作为 Hugging Face 模型加载。训练完成后运行：

```bash
SAVE_PATH=/mnt/data/checkpoints/qwen36-27b-create-my-card-sft-v1 \
CHECKPOINT_STEP=best \
MERGED_MODEL=/mnt/data/models/qwen36-27b-create-my-card-sft-v1 \
bash merge_fsdp_checkpoint.sh
```

`CHECKPOINT_STEP=best` 从 `best_checkpointed_iteration.txt` 读取最低 validation loss 对应的 step，也可以指定正整数。`MERGED_MODEL` 必须是不存在的新目录，脚本不会覆盖已有模型。

合并后 `validate_merged_model.py` 会检查权重、config、tokenizer 和非思考 chat template，避免把不完整目录交给评测推理。

## 7. 评测推理

构建官方2×2 TaskSpec 测试输入：

```bash
python3 build_taskspec_test.py
```

使用合并后的模型推理并转换为可渲染 A2UI：

```bash
python3 export_renderable_a2ui.py \
  --model-path /mnt/data/models/qwen36-27b-create-my-card-sft-v1 \
  --input-file data/parquet/test.parquet \
  --output-dir /mnt/data/outputs/create-my-card/renderable-a2ui \
  --tensor-parallel-size 8
```

输出目录包含：

```text
raw_compact_dsl.jsonl
taskspec-001.card.genui.jsonl
taskspec-002.card.genui.jsonl
...
```

`raw_compact_dsl.jsonl` 在模型推理结束后立即落盘；随后脚本关闭 vLLM engine、释放 NPU/GPU 缓存，再调用正向转换器。若部分转换失败，原始结果和成功生成的卡片仍会保留，失败项写入 `conversion_errors.jsonl`，进程最终以非零状态退出。

修复转换器或中间 DSL 后，可以跳过模型加载重新转换：

```bash
python3 export_renderable_a2ui.py \
  --raw-input-file /path/to/raw_compact_dsl.jsonl \
  --output-dir /path/to/retry-output
```

该入口不计算任何评测指标。

## 训练后 Benchmark

合并后的 Hugging Face 模型可以从两个维度评测，二者应同时保留：

- 业务质量：输入真实 `TaskSpec`，生成 Design Compact DSL，并验证能否转换为可渲染 A2UI。
- 服务性能：启动 vLLM OpenAI 兼容服务后，用 vLLM `v0.8.0` 自带的
  `benchmarks/benchmark_serving.py` 测 TTFT、TPOT、端到端延迟和吞吐。

Qwen3.6-27B 有 24 个 attention heads，因此 tensor parallel size 必须整除 24。
16 张卡不能使用 `TP=16`；先使用 `TP=8` 验证单个副本，再用两个 `TP=8` 副本做线上
并发扩展。

### 业务质量与离线延迟

`benchmark_create_my_card.py` 复用训练时的 system prompt、Qwen3.6 chat template、
`enable_thinking=false` 和 Compact DSL -> A2UI 转换器。每条样本都会记录原始 DSL、
prompt/completion token、生成延迟、成功状态和失败原因。

```bash
cd /workspace/hql/llm-posttrain/frameworks/verl/create_my_card/sft

python3 benchmark_create_my_card.py \
  --model-path /mnt/data/models/qwen36-27b-create-my-card-sft-v1-step15 \
  --input-file data/parquet/test.parquet \
  --output-dir /mnt/data/outputs/create-my-card/benchmark-tp8-b1 \
  --tensor-parallel-size 8 \
  --batch-size 1 \
  --max-model-len 4096 \
  --max-new-tokens 1536
```

`--batch-size 1` 用于观察逐样本离线延迟；吞吐测试可逐次使用 `2`、`4`、`8`、`16`，
并且每次指定一个新的 `--output-dir`。

输出目录包含：

```text
benchmark-tp8-b1/
├── benchmark_report.json   # 机器可读汇总：成功率、失败分类、token/延迟分位数、吞吐、模型加载耗时
├── benchmark_report.md     # 人类可读汇总：带 ms、tokens、req/s、tok/s 单位
├── samples.jsonl           # 每条样本的 token、latency、ok、error 和失败分类
└── raw_compact_dsl.jsonl   # 每条样本的原始模型输出
```

终端会打印业务质量摘要，并输出 JSON 与 Markdown 报告路径；使用 `benchmark_report.md` 看带单位的报告，
使用 `samples.jsonl` 查看具体样本。例如：

```bash
cat /mnt/data/outputs/create-my-card/benchmark-tp8-b1/benchmark_report.md
cat /mnt/data/outputs/create-my-card/benchmark-tp8-b1/samples.jsonl
```

### vLLM 在线服务性能

在模型所在的 vLLM `v0.8.0` 容器中，先启动一个 TP=8 的 OpenAI 兼容服务：

```bash
export MODEL=/mnt/data/models/qwen36-27b-create-my-card-sft-v1-step15

vllm serve "$MODEL" \
  --served-model-name create-my-card-sft \
  --tensor-parallel-size 8 \
  --dtype bfloat16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --trust-remote-code \
  --disable-log-requests
```

另开一个 shell，在 vLLM 源码根目录执行以下命令。该命令用随机长度请求测服务器性能，
不评估 CreateMyCard 的业务正确性：

```bash
mkdir -p /mnt/data/benchmarks

python benchmarks/benchmark_serving.py \
  --backend vllm \
  --model "$MODEL" \
  --served-model-name create-my-card-sft \
  --dataset-name random \
  --random-input-len 2048 \
  --random-output-len 512 \
  --num-prompts 200 \
  --request-rate inf \
  --max-concurrency 32 \
  --percentile-metrics ttft,tpot,itl,e2el \
  --metric-percentiles 50,90,95,99 \
  --trust-remote-code \
  --save-result \
  --save-detailed \
  --result-dir /mnt/data/benchmarks \
  --result-filename tp8-in2048-out512-c32.json \
  --metadata tp=8 input=2048 output=512 concurrency=32
```

终端会打印 successful requests、请求吞吐、输出 token 吞吐、总 token 吞吐，以及
TTFT、TPOT、ITL、E2E latency 的均值、中位数和指定分位数。`--save-detailed` 会将
逐请求的 `input_lens`、`output_lens`、`ttfts`、`itls`、`generated_texts` 和 `errors`
写入指定 JSON 文件。

建议固定输入/输出长度后，依次测试 `--max-concurrency 1,2,4,8,16,32,64`。`--request-rate inf`
测极限吞吐；使用有限值（例如 `--request-rate 2`、`5`、`10`）可模拟稳定到达的线上流量，
并观察 P95/P99 延迟和吞吐的拐点。
