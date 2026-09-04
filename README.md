# LLM Post-Training

面向 Ascend 910 的 LLM SFT 与 RL 实验仓库，训练框架以 veRL 为主。当前包含
CreateMyCard 卡片生成和 Qwen3.6 GSM8K 两条实验链路。

## 快速开始

训练机需要已安装 Docker、Ascend 驱动，并能通过 `npu-smi info` 识别 NPU。外部模型和
大规模数据默认分别放在 `/mnt/model`、`/mnt/data`；仓库内生成的 `outputs/` 不提交到 Git。

在宿主机启动容器：

```bash
cd /path/to/llm-posttrain
export WORK_DIR="$PWD"
bash infra/startContainer.sh verl-train
docker exec -it verl-train bash
```

仓库会挂载到容器的 `/workspace`。进入容器后执行：

```bash
cd /workspace
npu-smi info
bash infra/check_ascend_env.sh
```

默认镜像由 `infra/startContainer.sh` 维护，当前为
`quay.io/ascend/verl:v0.8.0-cann9.0.0-torch_npu2.9.0post2-a3-ubuntu22.04-py3.11-vllm`。
指定 NPU 或自定义镜像的方式见[容器与 Ascend 指南](docs/ASCEND_DOCKER_GUIDE.md)。

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `frameworks/verl/create_my_card/` | CreateMyCard 数据转换、SFT、RL 奖励与评测 |
| `A2UI_Render_0716/` | Windows/HarmonyOS L2 渲染工程 |
| `frameworks/verl/qwen36_gsm8k/` | Qwen3.6 GSM8K SFT 与 GRPO 实验 |
| `infra/` | 容器启动、Ascend 检查和离线镜像工具 |
| `docs/` | 跨模块规范、操作手册和验证报告 |

## CreateMyCard

主流程如下：

```text
TaskSpec + A2UI
→ Compact DSL 转换与 round-trip 校验
→ SFT 数据构建、训练和模型合并
→ 候选生成与 Stage 0 奖励审计
→ Windows 设备渲染、截图和 L2 质检
→ RFT / DPO / GRPO
```

接手时先阅读 [CreateMyCard 总览](frameworks/verl/create_my_card/README.md)，然后按任务进入：

- [数据生产与转换](frameworks/verl/create_my_card/data_pipeline/README.md)
- [SFT 数据、训练与评测](frameworks/verl/create_my_card/sft/README.md)
- [RL 奖励与多阶段流水线](frameworks/verl/create_my_card/rl/README.md)
- [Windows 本地渲染服务](docs/create_my_card/local-render-service.md)
- [数据合同与质检规范](docs/create_my_card/data-quality-spec.md)

快速验证 RL 与渲染服务代码：

```bash
python -m pytest frameworks/verl/create_my_card/rl/tests -q
```

当前 RL 奖励仍处于校准阶段，配置中的 `policy_update_enabled=false` 不应在完成
L2/人评相关性、reward hacking 和 holdout 验证前开启。

## GSM8K

- [Qwen3.6-27B SFT 流程](docs/qwen36_gsm8k_sft.md)
- [GRPO 训练入口](frameworks/verl/qwen36_gsm8k/rl/run_grpo.sh)
- [GRPO 21-step 验证报告](docs/qwen36_gsm8k_grpo_validation.md)

## 协作约定

- 从仓库根目录执行文档中的命令，模块文档明确要求切换目录时除外。
- 不提交模型、checkpoint、日志、生成的 Parquet 和 `outputs/` 产物。
- 不手工修改生成的 Parquet；需要版本管理的源数据位于各任务的 `data/source/`。
- 正式训练前先完成环境检查、数据预检和短步数 smoke test。
- 全部文档入口见[文档导航](docs/README.md)。
