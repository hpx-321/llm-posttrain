# SFT 数据目录

本目录区分受版本控制的源数据和本地生成产物。数据字段合同和质检标准以 `docs/create_my_card/` 为准。

## `source/`

| 文件 | 作用 | 是否进入训练标签 |
| --- | --- | --- |
| `system_prompt.md` | 全批次统一系统提示词 | 是 |
| `taskspec.json` | 带稳定 `id` 的 TaskSpec 数组 | 是，作为 user 内容 |
| `design_compact_dsl.jsonl` | 与 TaskSpec 同 ID 的 Compact DSL | 是，作为 assistant 内容 |
| `taskspec_cases.json` | 规范化 TaskSpec 评估案例 | 否，仅用于评测输入 |

当前训练源包含 954 对 TaskSpec/Compact DSL。默认构建结果为 922 条训练数据和 32 条验证数据。

当前评估源包含 98 条案例：62 条 `2x2` 和 36 条 `2x4`。由于当前 SFT 系统提示词只支持 `2x2`，`evaluation/build_taskspec_test.py` 默认从中生成 62 条 `test.parquet` 记录。

源数据更新前应先按[`../../data_pipeline/README.md`](../../data_pipeline/README.md)完成转换和 round-trip；`dataset/build_parquet.py` 只负责训练侧配对与序列化，不替代数据生产质检。

## `parquet/`

该目录保存本地生成文件：

```text
train.parquet
validation.parquet
token_stats.json
oom_probe.parquet
test.parquet
```

这些文件可以从源数据或远端测试数据重新生成，不应手工编辑。目录中的 `.gitignore` 用于避免提交大体积训练产物。
