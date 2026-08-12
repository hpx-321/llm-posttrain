# CreateMyCard veRL SFT 数据构建

该目录把一份 system prompt、全量 TaskSpec JSON 和全量 Design Compact DSL JSONL 组装为 veRL SFT 使用的 Parquet。

## 目录

```text
sft/
├── analyze_tokens.py
├── build_parquet.py
├── build_taskspec_test.py
├── export_renderable_a2ui.py
├── merge_fsdp_checkpoint.sh
├── qwen36_sft_dataset.py
├── run_sft.sh
├── sft_dry_run.py
├── training.env.example
├── validate_merged_model.py
├── requirements.txt
├── data/
│   ├── source/
│   │   ├── system_prompt.md
│   │   ├── taskspec.json
│   │   └── design_compact_dsl.jsonl
│   └── parquet/
```

`data/source/` 中的三个文件是唯一生产输入。`data/parquet/` 是生成目录。

上游 A2UI → Design Compact 转换规则见[数据生产与转换流程](../data_pipeline/README.md)；跨批次的数据合同统一见 [`docs/create_my_card/`](../../../../docs/create_my_card/)。

## 输入合同

### system_prompt.md

保存统一 system prompt。文件为空或只有空白时，构建出的 `messages` 不包含空 system 消息；以后填入内容后，每条样本都会使用同一份 system prompt。

### taskspec.json

根节点必须是数组，每条记录包含稳定且唯一的 `id` 和完整 `taskSpec`：

```json
[
  {
    "id": "q001",
    "taskSpec": {
      "size": "2x2",
      "userQuery": "示例"
    }
  }
]
```

`taskSpec` 会以紧凑 JSON 字符串写入 `user.content`，不会把 `id` 写入模型输入。

### design_compact_dsl.jsonl

每行是一条 JSON 记录，通过 `id` 与 TaskSpec 配对：

```json
{"id":"q001","designCompactDsl":"<Design Compact DSL 原文>"}
```

DSL 包含多行时，使用合法 JSON 字符串中的 `\n`。标签必须是原始 DSL，不允许 Markdown 代码围栏或 `<think>`。

构建器按 `id` 配对，不依赖两个文件的记录顺序；重复、缺失或多余的 `id` 都会直接报错。

## 输出格式

每条 Parquet 记录为：

```json
{
  "id": "q001",
  "messages": [
    {"role": "system", "content": "<统一 system prompt>"},
    {"role": "user", "content": "<完整 TaskSpec JSON 字符串>"},
    {"role": "assistant", "content": "<Design Compact DSL 原文>"}
  ],
  "enable_thinking": false
}
```

输出包括：

- `train.parquet`
- `validation.parquet`
- `manifest.json`：输入哈希、切分参数、样本 ID 和输出哈希

## 使用

在 veRL 训练环境安装依赖：

```bash
python -m pip install -r requirements.txt
```

填入源数据后执行：

```bash
cd /workspace/frameworks/verl/create_my_card/sft
python build_parquet.py
```

自定义构建参数示例：

```bash
python build_parquet.py \
  --validation-ratio 0.05 \
  --seed 42 \
  --output-dir /data/create_card_sft
```

`--validation-ratio` 是验证集的目标比例，不要求实际切分严格满足该比例。非零目标会将验证集条数对齐到最接近的 32 倍数，最低为 32 条，并至少保留 32 条训练数据，因此非空切分要求总数据不少于 64 条；`0` 仍表示生成空验证集。`manifest.json` 同时记录目标比例、实际比例和对齐倍数。当前 192 条数据使用默认参数时会切分为 160 条训练数据和 32 条验证数据。

当前源数据包含 192 条唯一配对记录：`cmc-v16-*` 99 条、`card84-v18-*` 93 条。`taskspec.json` 与 `design_compact_dsl.jsonl` 已通过本构建器的加载、唯一 ID 和双向缺失检查；`system_prompt.md` 保存与该批标签闭集对齐的 Qwen3.6-27B Compact DSL 生成约束，构建后作为每条样本统一的 system 消息。

## Token 长度分析

Parquet 构建完成后、启动训练前，用实际训练模型的 tokenizer 和 chat template 分析全量样本，同时生成最长样本 OOM probe：

```bash
python analyze_tokens.py \
  --model-path /mnt/model/Qwen3.6-27B \
  --probe-output data/parquet/oom_probe.parquet
```

默认读取：

```text
data/parquet/train.parquet
data/parquet/validation.parquet
```

完整报告写入 `data/parquet/token_stats.json`，终端打印不含 `perSample` 明细的摘要。统计口径为：

- prompt token：system（如有）+ TaskSpec + assistant 生成前缀
- assistant token：Design Compact DSL + assistant 结束标记
- total token：veRL SFT 实际处理的完整序列

第一批 192 条数据的结果为：

```text
prompt max=2641
assistant max=1380
total max=3875
recommendedMaxLength=4096
violations=[]
```

`recommendedMaxLength` 使用“全量最大 total token 按 256 向上对齐”的值，不使用 P99 截断。当前据此设置 `MAX_LENGTH=4096`；后续数据扩充后必须重新分析，并把新的 `recommendedMaxLength` 同步到实验环境文件。

自定义数据路径时显式传入输入和报告位置：

```bash
python analyze_tokens.py \
  --model-path /mnt/model/Qwen3.6-27B \
  --train-parquet /data/create_card_sft/train.parquet \
  --validation-parquet /data/create_card_sft/validation.parquet \
  --report /data/create_card_sft/token_stats.json
```

压测集循环使用训练集中最长的若干条记录，只用于显存 dry-run，不是正式训练数据。存在超限样本时不会生成该文件。

## 训练

`run_sft.sh` 通过 veRL 0.8.0 官方的 `data.custom_cls` 扩展点加载 `qwen36_sft_dataset.py`。该适配器不会像默认 `MultiTurnSFTDataset` 那样分别处理 system、user 和 assistant，而是：

1. 用 `system + user` 和 `add_generation_prompt=true` 生成完整推理 prompt。
2. 用 `system + user + assistant` 生成完整训练序列。
3. 校验训练序列必须以推理 prompt 为前缀。
4. prompt Token 的 `loss_mask` 设为 0，仅将 assistant 正文及结束标记设为 1。

两次 chat template 调用都固定使用 `enable_thinking=false`。这既适配 Qwen3.6 对完整对话顺序的要求，也与 `analyze_tokens.py` 的 Token 统计口径完全一致。适配器只支持当前文本单轮合同与 `data.pad_mode=no_padding`，遇到异常角色顺序、思考标签或超长样本会立即报错。

训练脚本直接使用 token 报告确定的整数参数。当前配置为：

```text
MAX_LENGTH=4096
MAX_TOKEN_LEN_PER_GPU=8192
SP_SIZE=1
```

这与 veRL 官方 SFT 配置方式一致：`data.max_length` 是单样本上限；启用 `data.use_dynamic_bsz=true` 后，`data.max_token_len_per_gpu` 是每设备 packed micro-batch 的 token 预算。官方性能指南建议从约 `2 × max_length` 的预算开始调优，因此当前使用 8192。4K 序列不需要 Ulysses，先使用 `SP_SIZE=1`。

训练固定使用 `data.truncation=error`。如果实验环境中的 `MAX_LENGTH` 小于真实样本，自定义 Dataset 会报错，不会静默裁掉 TaskSpec 或 DSL。默认 Dataset 的 `data.ignore_input_ids_mismatch` 不再参与当前流程；适配器会直接检查完整训练序列与推理 prompt 的前缀一致性。参考：[veRL SFT 官方配置](https://github.com/verl-project/verl/blob/main/verl/trainer/config/sft_trainer_engine.yaml)、[veRL 性能调优指南](https://github.com/verl-project/verl/blob/main/docs/perf/perf_tuning.rst)。

```bash
cp training.env.example /path/to/experiment.env
source /path/to/experiment.env

# 默认 DRY_RUN=1，使用 analyze_tokens.py 生成的最长样本 probe 跑两步
bash run_sft.sh

# 冒烟通过后再正式训练
DRY_RUN=0 bash run_sft.sh
```

veRL 0.8.0 会在最后一个训练 step 无条件调用检查点保存，`trainer.save_freq=-1` 只能关闭中间保存。两步 dry-run 因此通过 `sft_dry_run.py` 仅在当前训练进程内跳过该最终调用，同时设置 `checkpoint.save_contents=[]`；不会在 `SAVE_PATH` 下写入模型权重、优化器状态、额外状态、tokenizer/config 或 `global_step_2` 检查点目录。正式训练不使用该入口，仍在每个 epoch 结束后正常保存。

默认训练模式为全参数 SFT：

```text
LORA_RANK=0
LEARNING_RATE=1e-6
```

只有人工显式设置 `LORA_RANK>0` 才会切换为 LoRA；脚本不会在 OOM 后自动改变训练目标。Qwen3.6-27B 全参数 AdamW 的模型、梯度和优化器状态显存占用很高，正式训练前必须先让最长样本 dry-run 通过。

### 两个长度参数的区别

`MAX_LENGTH` 是单条 SFT 样本的总长度上限：

```text
prompt token + assistant token <= MAX_LENGTH
```

`MAX_TOKEN_LEN_PER_GPU` 是动态 micro-batch 在单个设备上的 token 预算。启用 Ulysses sequence parallel 后，veRL 的完整 micro-batch 预算为：

```text
MAX_TOKEN_LEN_PER_GPU × SP_SIZE
```

脚本会检查这个有效预算至少等于 `MAX_LENGTH`。当前 `8192 × 1` 可容纳约两个 4K 样本，有利于动态 batch 吞吐；如果 dry-run OOM，可先降为 4096，让每个 packed micro-batch 最多容纳一条最长样本，这不会截断数据。

### OOM 处理顺序

训练默认已经开启 BF16、FSDP、梯度检查点、去 padding、动态 token batch，并将每设备 micro batch 设为 1。如果最长样本 dry-run 仍然 OOM，按以下顺序处理：

1. 将 `MAX_TOKEN_LEN_PER_GPU` 从 8192 降到 4096，减少单次 packed micro-batch 的样本数。
2. 若单条最长样本仍然 OOM，增大 `SP_SIZE`，例如 `1 → 2 → 4`，且必须整除设备数。
3. 保持 `MICRO_BATCH_SIZE_PER_GPU=1`，不要靠截断 DSL 降显存。
4. 开启 `ACTIVATION_OFFLOAD=true`。
5. 再开启 `OPTIMIZER_OFFLOAD=true`，必要时开启 `PARAM_OFFLOAD=true`。
6. 若仍然 OOM，增加设备或回到数据侧处理异常超长样本，不能静默截断。

`data.truncation=error` 和完整序列前缀一致性被固定为硬检查。训练脚本不会捕获 OOM 后偷偷降低长度重试，也不会自动改为 LoRA，因为这两种做法都会改变既定训练目标。

训练和推理必须使用相同 Qwen3.6 tokenizer、chat template、system prompt 与 `enable_thinking=false` 设置。

## 训练后权重合并

正式训练保存的是 16 个 FSDP 分片，`global_step_15/huggingface/` 只包含 config 和 tokenizer 元数据，不能直接作为完整 vLLM 模型目录。先用 veRL 的 `model_merger` 合并为标准 Hugging Face 权重：

```bash
cd /workspace/hql/llm-posttrain/frameworks/verl/create_my_card/sft

export SAVE_PATH=/mnt/data/checkpoints/qwen36-27b-create-my-card-sft-v1
export CHECKPOINT_STEP=15
export MERGED_MODEL=/mnt/data/models/qwen36-27b-create-my-card-sft-v1-step15

bash merge_fsdp_checkpoint.sh
```

`CHECKPOINT_STEP=latest` 会读取 `${SAVE_PATH}/latest_checkpointed_iteration.txt`，当前正式训练对应 step 15。若要比较 step 10 和 step 15，分别设置不同的 `CHECKPOINT_STEP` 与 `MERGED_MODEL` 合并即可。目标目录必须不存在，脚本不会覆盖已有模型。

合并命令等价于：

```bash
python3 -m verl.model_merger merge \
  --backend fsdp \
  --local_dir /mnt/data/checkpoints/qwen36-27b-create-my-card-sft-v1/global_step_15 \
  --target_dir /mnt/data/models/qwen36-27b-create-my-card-sft-v1-step15 \
  --trust-remote-code \
  --use_cpu_initialization
```

合并结束后，`validate_merged_model.py` 会检查权重文件、config、tokenizer、chat template 和非思考空 `<think>` 前缀。通过后，推理程序的 `--model-path` 应指向 `MERGED_MODEL`，而不是原始 `global_step_15`。

## TaskSpec 输入集与可渲染 A2UI 导出

测试输入来自 [CreateMyCard 官方 taskspec_cases.json](https://github.com/InnovationTea/CreateMyCard/tree/main/testdata/taskspec)。构建器直接读取 `main` 分支当前数据，筛选 `size=2x2` 的 TaskSpec，并按训练数据的字段顺序序列化：`userQuery`、`size`、`dataModelSchema`、`eventCandidates`、`assetCandidates`。

```bash
cd /workspace/hql/llm-posttrain/frameworks/verl/create_my_card/sft
python3 build_taskspec_test.py
```

构建器从官方 20 条输入中只选择 15 条 `size="2x2"` 记录，默认生成：

- `data/parquet/test.parquet`：15 条 `2x2` TaskSpec 输入。
- `data/parquet/test_manifest.json`：来源位置、筛选条件、行数和样本 ID。

服务器无法访问 GitHub 时，可提前下载原文件后执行：

```bash
python3 build_taskspec_test.py --source-file /path/to/taskspec_cases.json
```

当前 system prompt 明确只训练 `2x2`、160×160 卡片，因此从 `test.parquet` 生成 Design Compact DSL，再通过仓库内的冻结正向转换器导出可直接渲染的标准 A2UI NDJSON：

```bash
python3 export_renderable_a2ui.py \
  --model-path /mnt/data/models/qwen36-27b-create-my-card-sft-v1-step15 \
  --input-file data/parquet/test.parquet \
  --output-dir /mnt/data/outputs/create-my-card/renderable-a2ui-step15 \
  --tensor-parallel-size 8
```

每个 TaskSpec 对应一个可直接交给渲染端的文件：

```text
/mnt/data/outputs/create-my-card/renderable-a2ui-step15/
├── raw_compact_dsl.jsonl
├── taskspec-001.card.genui.jsonl
├── taskspec-002.card.genui.jsonl
└── ...
```

`raw_compact_dsl.jsonl` 会在模型推理结束后、A2UI 转换开始前写入，包含样本 ID、尺寸、停止原因、completion token 数和模型原始 Compact DSL。中间结果落盘后，脚本会主动关闭 vLLM engine、释放模型引用和 NPU/GPU 缓存，再执行正向转换；因此转换阶段不再持续占用模型显存。每个 `*.card.genui.jsonl` 都是转换器输出的三行标准 A2UI 消息：`createSurface`、`updateComponents` 和 `updateDataModel`。

导出固定使用训练时相同的 system prompt、Qwen3.6 chat template 和 `enable_thinking=false`。若任一结果为空、被截断或无法通过正向转换器，输出目录会保留全部 `raw_compact_dsl.jsonl`，并生成 `conversion_errors.jsonl` 记录失败样本 ID、异常和原始 DSL；为避免误用部分结果，此时不会写出任何 `*.card.genui.jsonl`。

修复 Compact DSL 或转换器后，可以跳过模型推理，直接复用原始结果并写入一个新的输出目录：

```bash
python3 export_renderable_a2ui.py \
  --raw-input-file /mnt/data/outputs/create-my-card/renderable-a2ui-step15/raw_compact_dsl.jsonl \
  --output-dir /mnt/data/outputs/create-my-card/renderable-a2ui-step15-retry
```

该入口不计算任何评测指标。
