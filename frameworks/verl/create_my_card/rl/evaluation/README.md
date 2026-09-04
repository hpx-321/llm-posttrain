# 奖励评估与 Stage 0 操作

本目录只负责评估当前候选奖励，不执行 RFT、DPO 或 GRPO 参数更新。奖励公式和门禁
定义见 [`../reward/README.md`](../reward/README.md)。

## 文件职责

| 文件 | 职责 |
| --- | --- |
| `audit_rewards.py` | 对保存的 Compact DSL 候选批量计算奖励 |
| `build_content_label_review.py` | 从 SFT gold 生成待人工复核的主要内容标签模板 |
| `build_reward_canary.py` | 用固定 reviewed 标签构造 16 条 canary parquet |
| `analyze_reward_groups.py` | 检查同 prompt 候选的方差、缺分和长度相关性 |
| `render_l2_sample.py` | 生成 L2 渲染载荷，并可调用本地 HTTP 渲染服务或旧设备工具 |
| `run_reward_separation_server.sh` | 生成真实 SFT 候选并完成双配置审计 |
| `fixtures/` | 只供评估使用的固定 canary 标签，不得作为训练数据 |

## 1. 批量审计已有候选

输入 JSONL 至少包含：

```json
{"id":"case-001","designCompactDsl":"...","finishReason":"stop","completionTokens":812}
```

TaskSpec 可以内嵌为 `taskSpec`，也可以通过 `--taskspec-file` 统一提供：

```bash
python frameworks/verl/create_my_card/rl/evaluation/audit_rewards.py \
  --input outputs/raw_compact_dsl.jsonl \
  --taskspec-file frameworks/verl/create_my_card/sft/data/source/taskspec.json \
  --labels-file reward-labels.json \
  --output outputs/reward-audit.jsonl
```

历史 gold 没有 `completionTokens` 时，使用 rollout 相同的 tokenizer 补算。脚本只编码
completion 本文，并固定 `add_special_tokens=False`：

```bash
python frameworks/verl/create_my_card/rl/evaluation/audit_rewards.py \
  --input frameworks/verl/create_my_card/sft/data/source/design_compact_dsl.jsonl \
  --taskspec-file frameworks/verl/create_my_card/sft/data/source/taskspec.json \
  --tokenizer-path /mnt/model/Qwen3.6-27B \
  --default-finish-reason stop \
  --output outputs/reward-audit-full.jsonl
```

标签必须显式设置 `reviewed=true` 才能参与完整内容计分。可先生成审核模板：

```bash
python frameworks/verl/create_my_card/rl/evaluation/build_content_label_review.py \
  --output outputs/content-label-review.json
```

## 2. 真实候选区分度实验

服务器入口使用 16 条跨天气、日程、设备、健康、音乐和设置等领域的固定 canary。
每个 TaskSpec 生成 1 条 greedy 和 8 条 temperature 候选，再分别使用基线配置与
视觉候选配置进行审计：

```bash
SFT_MODEL_PATH=/mnt/model/qwen36-27b-create-my-card-sft-v1-merged \
TOKENIZER_PATH=/mnt/model/Qwen3.6-27B \
bash frameworks/verl/create_my_card/rl/evaluation/run_reward_separation_server.sh
```

默认输出到一个带时间戳的目录：

- `generation/raw_compact_dsl.jsonl`：全部真实候选；
- `reward-baseline-analysis.md`：当前 Stage 0 配置的组内区分度；
- `reward-l1-visual-reweighted-analysis.md`：视觉候选配置的 L1 区分度；
- `run-manifest.json`：模型路径和采样参数。

机械 PASS 只表示 reward 在同 prompt 候选间产生了可测差异，不代表排序符合人类视觉
偏好。固定 canary 来自现有 SFT 数据，只能用于程序和训练分布内校准，不得回流为
训练样本；正式评估仍需单独建立未参与 SFT 的 holdout TaskSpec。

## 3. L2 渲染准备

已有 `dumpLayout` 时，将文件命名为 `<id>.layout.json`，并向 `audit_rewards.py` 传入
`--layout-dir`。指定目录后每个样本都必须存在对应 dump，不会静默降级为 L1。

设备侧样本可以先生成带 `__viewport__` 的载荷：

```bash
python frameworks/verl/create_my_card/rl/evaluation/render_l2_sample.py \
  --input outputs/raw_compact_dsl.jsonl \
  --taskspec-file frameworks/verl/create_my_card/sft/data/source/taskspec.json \
  --output-dir outputs/l2-render-sample \
  --limit 16
```

只有显式增加 `--execute` 才会调用设备或模拟器；准备载荷本身不表示 L2 已完成。
配置 `A2UI_RENDER_SERVICE_URL` 后，`--execute` 自动通过 Windows 本地渲染服务
获取布局和截图；没有配置 URL 时保留旧的本机子进程路径。
完整的 Windows 配置、SSH 反向隧道和容器命令见
[`../../../../../docs/create_my_card/local-render-service.md`](../../../../../docs/create_my_card/local-render-service.md)。

## 4. 奖励输出语义

- `score=-1`：模型输出无法解析或转换；
- `score<=-0.5`：TaskSpec 白名单、主要内容覆盖或内容预算失败；
- `score<=0`：checker 存在 P0；
- `score=null, masked=true`：checker、超时或 L2 环境故障，不惩罚模型；
- `score=null, masked=false`：证据不足且未触发可独立判定的负向门禁；
- `partial_score`：不重新归一化的已知分量贡献，只供诊断。

当前两份奖励配置都不允许正式策略更新。至少完成真实候选排序、L2/人评相关性、
零方差、长度投机、reward hacking 和 holdout 检查后，才能讨论开启
`policy_update_enabled`。
