# 数据集构建与 Token 预检

本目录保存数据构建、Token 预检和 veRL Dataset 入口。以下命令均假设当前目录为 `sft/`。

## 职责

| 实现 | 职责 |
| --- | --- |
| `build_parquet.py` | 校验 TaskSpec/Compact DSL ID、确定性切分并原子写入 Parquet |
| `analyze_tokens.py` | 使用实际模型 tokenizer 统计长度、检查上下文并生成 OOM probe |
| `qwen36_sft_dataset.py` | 应用 Qwen3.6 非思考 chat template 和 assistant-only loss mask |

## 构建 Parquet

```bash
cd /workspace/hql/llm-posttrain/frameworks/verl/create_my_card/sft
python3 dataset/build_parquet.py
```

默认读取：

```text
data/source/system_prompt.md
data/source/taskspec.json
data/source/design_compact_dsl.jsonl
```

默认输出：

```text
data/parquet/train.parquet
data/parquet/validation.parquet
```

每行 schema 保持为：

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

构建器检查 ID 唯一性和双向配对关系。验证集数量按 32 条对齐；当前 954 条源数据默认拆分为 922 条训练和 32 条验证。

## Token 与 OOM 预检

```bash
python3 dataset/analyze_tokens.py \
  --model-path /mnt/model/Qwen3.6-27B \
  --probe-output data/parquet/oom_probe.parquet
```

输出：

- `token_stats.json`：各 split 的 prompt、assistant、total Token 分布、最长样本和建议 `MAX_LENGTH`；
- `oom_probe.parquet`：循环使用最长样本构造的显存压力数据。

分析脚本和训练 Dataset 共用相同 chat template 逻辑并固定 `enable_thinking=false`。样本超过模型上下文时直接失败；训练使用 `data.truncation=error`，不会静默截断 TaskSpec 或 DSL。

数据更新后必须重新生成报告，并把 `recommendedMaxLength` 同步到训练环境的 `MAX_LENGTH`。

## 实现导入

内部代码可直接导入：

```python
from frameworks.verl.create_my_card.sft.dataset.build_parquet import build_dataset
from frameworks.verl.create_my_card.sft.dataset.qwen36_sft_dataset import (
    CreateMyCardSFTDataset,
)
```

veRL 配置使用 `sft/dataset/qwen36_sft_dataset.py`。
