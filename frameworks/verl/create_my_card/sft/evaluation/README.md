# 推理导出与评测

本目录保存测试数据构建、模型推理、A2UI 导出和 benchmark 入口。以下命令均假设当前目录为 `sft/`。

## 实现职责

| 实现 | 职责 |
| --- | --- |
| `import_taskspec_cases.py` | 将原始 Q*.json 请求转换为项目 TaskSpec 评估源 |
| `build_taskspec_test.py` | 构建官方 2×2 TaskSpec 推理输入 |
| `export_renderable_a2ui.py` | 生成 Compact DSL，并转换为可渲染 A2UI |
| `benchmark_create_my_card.py` | 汇总可转换率、失败分类、Token、离线延迟和吞吐 |
| `compare_create_my_card.py` | 自动运行基座与 SFT benchmark，并生成逐样本配对对比 |

## 构建测试输入

从原始请求重新生成规范化 TaskSpec 源：

```bash
python3 evaluation/import_taskspec_cases.py \
  --input-dir /path/to/813 \
  --reference-file /path/to/taskspec_cases.json \
  --output-file data/source/taskspec_cases.json
```

导入器按 `Q` 编号排序，校验原始顶层字段与 `content` 副本一致；数据字段和素材路径优先从项目训练 TaskSpec 目录解析，目录未覆盖的能力字段与素材使用脚本内显式白名单，遇到未知项直接失败。

构建 Parquet：

```bash
cd /workspace/hql/llm-posttrain/frameworks/verl/create_my_card/sft
python3 evaluation/build_taskspec_test.py
```

默认读取 `data/source/taskspec_cases.json`，输出 `data/parquet/test.parquet`。当前源包含 98 条案例，其中 62 条为 `2x2`、36 条为 `2x4`；现有系统提示词和构建器只面向 `2x2`，因此 Parquet 包含 62 条。也可以用 `--source-file` 或 `--source-url` 显式替换规范化来源。

## 推理并导出 A2UI

```bash
python3 evaluation/export_renderable_a2ui.py \
  --model-path /mnt/model/qwen36-27b-create-my-card-sft-v1-merged \
  --input-file data/parquet/test.parquet \
  --output-dir /mnt/data/outputs/create-my-card/renderable-a2ui \
  --tensor-parallel-size 8
```

输出：

```text
raw_compact_dsl.jsonl
taskspec-001.card.genui.jsonl
taskspec-002.card.genui.jsonl
...
```

模型生成结束后先写入 `raw_compact_dsl.jsonl`，再释放 vLLM engine 并执行 Compact DSL→A2UI 转换。转换成功的样本始终保留为独立的 `*.card.genui.jsonl`；转换失败的样本写入 `conversion_errors.jsonl`，全部样本处理完成后以非零状态退出。

跳过模型加载并重试转换：

```bash
python3 evaluation/export_renderable_a2ui.py \
  --raw-input-file /path/to/raw_compact_dsl.jsonl \
  --output-dir /path/to/retry-output
```

## 离线 benchmark

```bash
python3 evaluation/benchmark_create_my_card.py \
  --model-path /mnt/model/qwen36-27b-create-my-card-sft-v1-merged \
  --input-file data/parquet/test.parquet \
  --output-dir /mnt/data/outputs/create-my-card/benchmark-tp8-b1 \
  --tensor-parallel-size 8 \
  --batch-size 1 \
  --max-model-len 5632 \
  --max-new-tokens 1536
```

输出：

```text
benchmark_report.json
benchmark_report.md
samples.jsonl
raw_compact_dsl.jsonl
```

`--batch-size 1` 用于观察逐样本离线延迟；批量值 `2/4/8/16` 用于观察吞吐，每次必须使用新的输出目录。

导出、单模型 benchmark 和自动对比统一默认 `--max-model-len 5632`，与训练的 `MAX_LENGTH=5632` 一致；训练与评测都会在序列超限时直接失败，不做静默截断。默认 `--max-new-tokens 1536` 时，推理 prompt 最多可使用 4096 Token。

当前业务质量指标表示“模型输出能否通过 Compact DSL→A2UI 转换”，用于发现截断、空输出和协议错误；JSON 尾逗号、未闭合分隔符以及冗余或错配的关闭符号均直接计为转换失败，不做自动修复。该指标不是 TaskSpec 语义正确率，完整业务验收仍需结合数据合同、渲染结果或带参考答案的评测。

## 基座与 SFT 自动对比

```bash
python3 evaluation/compare_create_my_card.py \
  --sft-model-path /mnt/model/qwen36-27b-create-my-card-sft-v1-merged \
  --input-file data/parquet/test.parquet \
  --output-dir /mnt/data/outputs/create-my-card/base-vs-sft \
  --tensor-parallel-size 8 \
  --max-model-len 5632 \
  --max-new-tokens 1536
```

基座模型默认读取 `/mnt/model/Qwen3.6-27B`，默认 `batch-size=16`。可分别用 `--base-model-path` 和 `--batch-size` 覆盖。两个模型共享基座 tokenizer、测试集、随机种子和生成参数，并在独立子进程中顺序运行，前一个模型退出后才加载下一个模型。

输出：

```text
base/
├── benchmark_report.json
├── benchmark_report.md
├── samples.jsonl
└── raw_compact_dsl.jsonl
sft/
├── benchmark_report.json
├── benchmark_report.md
├── samples.jsonl
└── raw_compact_dsl.jsonl
comparison_report.json
comparison_report.md
comparison_samples.jsonl
```

对比报告汇总成功率、失败类型、Token、延迟和吞吐差异，并标记每个样本的 `improved`、`regressed`、`both_success` 或 `both_failed` 状态。默认批量设置面向吞吐比较，报告中的样本延迟是批次耗时的均摊值；如需观察逐样本离线延迟，显式传入 `--batch-size 1`。

## 在线服务性能

Qwen3.6-27B 有 24 个 attention heads，tensor parallel size 必须整除 24。先启动 TP=8 vLLM OpenAI 兼容服务：

```bash
export MODEL=/mnt/model/qwen36-27b-create-my-card-sft-v1-merged

vllm serve "$MODEL" \
  --served-model-name create-my-card-sft \
  --tensor-parallel-size 8 \
  --dtype bfloat16 \
  --max-model-len 5632 \
  --gpu-memory-utilization 0.90 \
  --trust-remote-code \
  --disable-log-requests
```

在 vLLM 源码根目录运行其官方服务 benchmark：

```bash
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
  --result-dir /mnt/data/benchmarks
```

固定输入输出长度后，应逐次测试并发 `1/2/4/8/16/32/64`；`request-rate=inf` 测极限吞吐，有限 request rate 用于观察稳定流量下的 P95/P99 延迟。
