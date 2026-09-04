# CreateMyCard 后训练

本目录维护 CreateMyCard 从最终 A2UI 数据生产到 veRL SFT、模型导出、奖励审计和
设备侧 L2 质检的垂直流程。数据协议和质量合同集中放在 `docs/create_my_card/`。

## 接手顺序

1. 阅读本页的流程边界，确认工作属于数据、SFT、奖励还是 L2 渲染。
2. 从仓库根目录运行 `python -m pytest frameworks/verl/create_my_card/rl/tests -q`。
3. 进入下方对应模块文档；需要设备截图时直接使用本地渲染服务手册。

源数据位于 `sft/data/source/`，模型和训练产物不进入 Git。当前 RL 奖励尚未完成
L2/人评校准，不能直接开启策略更新。

## 目录

```text
create_my_card/
├── data_pipeline/                 # 最终 A2UI ↔ Design Compact DSL
│   └── converters/                # 冻结转换器、逆向工具和 round-trip 校验
├── sft/
    ├── data/                      # 受版本控制的源数据与本地生成的 Parquet
    ├── dataset/                   # 数据构建、Token 分析和 veRL Dataset 实现
    ├── training/                  # dry-run、最佳检查点和合并后校验实现
    └── evaluation/                # 测试集、推理导出、benchmark 和模型对比
└── rl/                            # Stage 0 离线奖励审计与 L2 样本准备
```

## 流程边界

```text
TaskSpec + 最终 A2UI
→ data_pipeline：逆向 Compact DSL + 正向 round-trip
→ sft/dataset：ID 配对 + Parquet + Token/OOM 预检
→ sft/training：dry-run + 正式训练 + FSDP 合并
→ sft/evaluation：推理 + 可渲染性检查 + 基座/SFT 对比 + 离线/服务性能评测
→ rl：无梯度奖励审计 + primary 标签复核 + L2 抽样准备
```

- `data_pipeline/` 负责进入 SFT 前的协议转换和单样本 round-trip。
- `sft/data/source/` 保存已经交付给训练侧的成对源数据。
- `sft/dataset/` 不重新设计或修复 A2UI，只构建训练记录并做训练前检查。
- `sft/evaluation/` 当前以 Compact DSL 可转换率和性能为主，不把可转换率等同于完整业务语义正确率。
- `rl/` 当前只实现 Stage 0 候选奖励审计，权重未经 L2/人评校准，不允许策略更新。

## 文档入口

- [数据生产与转换](data_pipeline/README.md)
- [正逆向转换器](data_pipeline/converters/README.md)
- [SFT 总览与执行入口](sft/README.md)
- [数据集构建与 Token 预检](sft/dataset/README.md)
- [训练与检查点](sft/training/README.md)
- [推理导出与评测](sft/evaluation/README.md)
- [Stage 0 奖励审计](rl/README.md)
- [Windows 本地渲染服务](../../../docs/create_my_card/local-render-service.md)
- [RL 布局优化方案](../../../docs/create_my_card/rl-layout-optimization-plan.md)
- [数据生产交接说明](../../../docs/create_my_card/data-production-handoff.md)
- [数据质检规范](../../../docs/create_my_card/data-quality-spec.md)
- [Expression Profile v1](../../../docs/create_my_card/expression-profile-v1.md)
