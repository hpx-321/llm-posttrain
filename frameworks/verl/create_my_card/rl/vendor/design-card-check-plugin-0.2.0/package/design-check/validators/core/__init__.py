"""check-core 底座（拆包第一步，2026-08-26 Idea2-WP-A）。

本包是「1+5」拆包方案（docs/idea-check-package-split.md §2）中的公共底座：
**无规则**，只承载供 5 个检测包共享的通用能力——

- 解析 / schema：dsl.py、finding.py（仍在 validators/ 顶层，归包时迁入）
- 契约加载：design_contract.py、config.py、colors.py（同上）
- 树工具：core/tree.py（组件树索引/父子关系/尺寸解析等通用遍历）
- 渐变共享助手：core/gradient_util.py

规则本体（rules/*.py）不属于本包；本包不注册任何 rule_id。
"""
