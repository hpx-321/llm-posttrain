"""AREA.* —— 槽位归区后的分区针对性规则（L1 声明侧；L2a 实测侧在 validators/geometry.py）。

由 WP-AREA 包填充实现；接线已入 rules/__init__.py 末行 import。
设计依据：docs goal 讨论 + 2026-08-22 B-q4 dump 实证（ringValue×ringState 重叠 16vp、
saveButton 下探 12vp 安全边距 8.0vp）。
"""
from __future__ import annotations

from typing import Any, Dict, List

from validators.dsl import GenuiCard
from validators.finding import Finding, P1
from validators.rules import register
from validators.rules._common import make
from .slot_rule import (
    _comp_index,
    _container_of,
    _find_root,
    _parent_map,
    _resolved_children,
    _title_zone,
)

#: title-text 契约字号（DESIGN.md §Title & Identity L1414：body-s-regular 12vp/400）
TITLE_TEXT_SIZE = 12.0


@register("AREA.TITLE_TEXT_TIER")
def check_title_text_tier(card: GenuiCard, contract: Dict[str, Any], query: str) -> List[Finding]:
    """title-text 字号档位（§L1414 统一 body-s-regular 12vp/400 → P1）。

    title 区定位复用 rules/slot_rule.py 既有识别工具（_container_of /
    _title_zone：容器首子 = title 区），取 title 子树首个 Text 判定。

    判定口径（宁缺毋滥）：
    - 只判 fontSize 偏离 12vp 档位；fontWeight 不单独判——93 条语料
      86/93 标题为 12/500（body-s-medium 档，验收基线），B-q4 12/600
      标题亦通过验收，字重档位差异不臆报，留人工复核；
    - title 区定位不到 / 无 Text → 跳过。
    """
    index = _comp_index(card)
    parents = _parent_map(index)
    root = _find_root(index, parents)
    if root is None:
        return []
    container, _ = _container_of(root, index)
    title = _title_zone(container, index)
    if title is None:
        return []
    # 取 title 子树内第一个 Text（title-text 本体）——DFS 先序（首子树优先）。
    # BFS 会误取兄弟大字：C 模板形态 [Row(真title 12vp), Text 主数值 38vp]（C-Q034 实证，
    # 2026-08-22 修复）；DFS 对 B header / 93 集 Row / 裸 Text 形态取点不变。
    stack = [title]
    while stack:
        comp = stack.pop()
        if comp.get("component") == "Text":
            raw = (comp.get("styles") or {}).get("fontSize")
            if isinstance(raw, (int, float)) and not isinstance(raw, bool) \
                    and float(raw) != TITLE_TEXT_SIZE:
                return [
                    make(
                        card, "AREA.TITLE_TEXT_TIER",
                        f"title-text 字号 {raw:g}vp ≠ body-s-regular 12vp（DESIGN.md §Title & Identity L1414）",
                        comp.get("id"), severity=P1,
                        expected="title-text fontSize = 12vp（body-s-regular 12vp/400）",
                        actual=f"fontSize={raw:g}vp",
                        fix_hint="标题统一使用 body-s-regular(12vp/400)，不再使用 14vp/18vp 的 subtitle 层级",
                    )
                ]
            return []  # 首 Text 已在 12vp 档位 → 合规
        stack.extend(reversed(_resolved_children(index, comp)))
    return []
