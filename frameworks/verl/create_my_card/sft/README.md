# CreateMyCard veRL SFT

本目录按数据集、训练和评测三个阶段组织 CreateMyCard SFT。各子目录同时保存实现和执行入口，根目录只保留总览、依赖、数据与测试。

## 目录

```text
sft/
├── data/
│   ├── README.md
│   ├── source/                    # system prompt、TaskSpec、Compact DSL
│   └── parquet/                   # 本地生成的训练与测试数据
├── dataset/
│   ├── README.md
│   ├── build_parquet.py
│   ├── analyze_tokens.py
│   └── qwen36_sft_dataset.py
├── training/
│   ├── README.md
│   ├── training.env.example
│   ├── run_sft.sh
│   ├── sft_dry_run.py
│   ├── best_sft_trainer.py
│   ├── merge_fsdp_checkpoint.sh
│   └── validate_merged_model.py
├── evaluation/
│   ├── README.md
│   ├── import_taskspec_cases.py
│   ├── build_taskspec_test.py
│   ├── export_renderable_a2ui.py
│   ├── benchmark_create_my_card.py
│   └── compare_create_my_card.py
├── requirements.txt
└── README.md
```

## 执行入口

| 阶段 | 命令 | 说明 |
| --- | --- | --- |
| 构建训练集 | `python3 dataset/build_parquet.py` | [数据集构建](dataset/README.md) |
| Token/OOM 预检 | `python3 dataset/analyze_tokens.py ...` | [数据集构建](dataset/README.md) |
| dry-run/训练 | `bash training/run_sft.sh` | [训练与检查点](training/README.md) |
| 合并模型 | `bash training/merge_fsdp_checkpoint.sh` | [训练与检查点](training/README.md) |
| 导入评估源 | `python3 evaluation/import_taskspec_cases.py ...` | [推理与评测](evaluation/README.md) |
| 构建测试集 | `python3 evaluation/build_taskspec_test.py` | [推理与评测](evaluation/README.md) |
| 推理并导出 A2UI | `python3 evaluation/export_renderable_a2ui.py ...` | [推理与评测](evaluation/README.md) |
| 离线 benchmark | `python3 evaluation/benchmark_create_my_card.py ...` | [推理与评测](evaluation/README.md) |
| 基座/SFT 对比 | `python3 evaluation/compare_create_my_card.py ...` | [推理与评测](evaluation/README.md) |

## 核心链路

```text
data/source
→ dataset/build_parquet.py
→ train.parquet + validation.parquet
→ dataset/analyze_tokens.py
→ token_stats.json + oom_probe.parquet
→ training/run_sft.sh
→ veRL FSDP checkpoint
→ training/merge_fsdp_checkpoint.sh
→ Hugging Face 模型
→ evaluation/import_taskspec_cases.py
→ evaluation/build_taskspec_test.py
→ evaluation/export_renderable_a2ui.py / benchmark_create_my_card.py
→ evaluation/compare_create_my_card.py
```

## 最短执行顺序

```bash
cd /workspace/hql/llm-posttrain/frameworks/verl/create_my_card/sft
pip install -r requirements.txt

python3 dataset/build_parquet.py
python3 dataset/analyze_tokens.py \
  --model-path /mnt/model/Qwen3.6-27B \
  --probe-output data/parquet/oom_probe.parquet

cp training/training.env.example /path/to/create_my_card.env
source /path/to/create_my_card.env
DRY_RUN=1 bash training/run_sft.sh
DRY_RUN=0 bash training/run_sft.sh
```

训练完成后按[训练文档](training/README.md)合并模型，再按[评测文档](evaluation/README.md)生成测试输入、导出 A2UI，并自动对比基座与 SFT 模型。

## 脚本语法检查

```bash
bash -n frameworks/verl/create_my_card/sft/training/run_sft.sh
bash -n frameworks/verl/create_my_card/sft/training/merge_fsdp_checkpoint.sh
```
