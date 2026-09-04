# Vendored design-card-check runtime 0.2.0

本目录是 CreateMyCard 奖励与 L2 采集使用的固定、最小离线运行快照，来源于
`design-card-check-plugin-0.2.0-dist`。它不是原插件的完整发布包。

保留范围：

- `package/DESIGN.md`、`package/DESIGN-2x4.md`：2×2 / 2×4 规则真值；
- `package/design-check/packages/`、`validators/`：奖励检查所需规则与运行库；
- `scripts/check_card.py`：L1/L2 检查入口；
- `scripts/render_eval_dump.py`、`render_dump.py`、`device_utils.py`：L2 设备采集入口及依赖；
- `scripts/contrast_calc.py`：质检结果中引用的对比度复算工具。

未保留 npm/dsh 插件壳、提示词、报告生成、批处理、构建发布、SHA 清单及原发布说明。
奖励模块默认从此目录加载质检器；只有替换外部实现时才需要设置
`DESIGN_CHECK_ROOT`。

升级时请创建新的版本目录，并按实际入口重新提取最小运行子集；不要在本目录恢复
与训练奖励无关的发布和审查工具。同时更新 `VENDORED_CHECKER_ROOT`、现有回归测试
与奖励版本说明。
