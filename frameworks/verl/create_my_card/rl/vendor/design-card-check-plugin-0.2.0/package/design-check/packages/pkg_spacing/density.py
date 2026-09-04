"""DENSITY.* —— 展示密度规则（E-07）。

F2 单一主操作依据（DESIGN.md）：
- §Overview L1138-1139：卡片默认单一主操作，仅当次操作有独立且即时的用户目标时才附带；
- §Slot Model L1436：2×2 最多 1 个按钮；2×4 容量上限 2 个按钮，
  次操作只有在具有独立、即时目标且不与主操作竞争时才可出现；
- Do/Don'ts L1649：不要让 2×2 超过 1 个显式操作，或让 2×4 超过 1 个主操作 + 1 个次操作。

两层检查：
- DENSITY.EXPLICIT_ACTIONS：超过尺寸硬上限（2x2=1 / 2x4=2）→ P1（明文硬上限）；
- DENSITY.SINGLE_PRIMARY_ACTION：非卡根可点击元素 >1 → P2，
  标注「多 CTA 待语义豁免」——规范允许例外场景（次操作有独立即时目标），机器不下最终结论。
root 整卡点击豁免：按结构（顶层组件 id == root 或无父节点）判定，不用 id 文本猜测。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from validators.dsl import GenuiCard
from validators.finding import Finding, P1, P2, PROGRAM
from validators.rules import register
from validators.rules._common import make
from validators.core.tree import _comp_index, _parent_map

LIMIT_BY_SIZE = {"2x2": 1, "2x4": 2}


def _root_id(card: GenuiCard) -> Optional[str]:
    index = _comp_index(card)
    if "root" in index:
        return "root"
    parents = _parent_map(index)
    for cid in index:
        if cid not in parents:
            return cid
    return None


def _non_root_actions(card: GenuiCard) -> List[Dict[str, Any]]:
    """带 onClick 且非卡根（结构判定）的组件列表。"""
    root_id = _root_id(card)
    return [c for c in card.iter_components() if c.get("onClick") and c.get("id") != root_id]


@register("DENSITY.EXPLICIT_ACTIONS")
def check_explicit_actions(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """显式操作数量必须 ≤ 该尺寸上限（2x2=1，2x4=2）（E-07；DESIGN.md L1436/L1649）。

    root 整卡点击豁免（结构判定）；超出硬上限属明文违规 → P1。
    """
    size = card.size
    actions = _non_root_actions(card)
    limit = LIMIT_BY_SIZE.get(size, 1)
    if len(actions) > limit:
        return [
            make(
                card, "DENSITY.EXPLICIT_ACTIONS",
                f"{size} 卡出现 {len(actions)} 个非卡根 onClick 操作 > 上限 {limit}",
                actions[limit].get("id"), severity=P1,
                expected=f"显式操作 ≤ {limit}（DESIGN.md §Slot Model L1436）",
                actual=f"{len(actions)}",
                fix_hint="收敛为单一主操作；若确需保留多 CTA，须有独立即时目标并经设计师豁免（L1436）",
            )
        ]
    return []


@register("DENSITY.SINGLE_PRIMARY_ACTION")
def check_single_primary_action(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """非卡根可点击元素 >1 → 违反「默认单一主操作」（DESIGN.md §Overview L1138）。

    P2 + 多 CTA 待语义豁免：规范允许例外（次操作须有独立、即时目标且不与主操作竞争，
    L1436），静态无法证实豁免是否成立，机器只标记偏离默认形态，最终由设计师确认。
    """
    actions = _non_root_actions(card)
    if len(actions) > 1:
        return [
            make(
                card, "DENSITY.SINGLE_PRIMARY_ACTION",
                f"非卡根可点击元素 {len(actions)} 个 > 1，违反「默认单一主操作」（多 CTA 待语义豁免）",
                actions[1].get("id"), severity=P2, evidence_type=PROGRAM,
                expected="默认单一主操作：非卡根可点击 ≤ 1（DESIGN.md §Overview L1138）",
                actual=f"{len(actions)} 个: {', '.join(a.get('id') for a in actions)}",
                fix_hint="收敛为单一主操作；次操作仅在有独立即时目标时保留，需设计师豁免确认",
            )
        ]
    return []


@register("DENSITY.NUMBERS")
def check_number_density(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """可见大数字数量 ≤ 1（非双环/非数字并列场景）（E-07）。"""
    big_numbers = 0
    for comp in card.iter_components():
        if comp.get("component") != "Text":
            continue
        styles = comp.get("styles") or {}
        size = styles.get("fontSize")
        content = comp.get("content") or ""
        if isinstance(size, (int, float)) and size >= 24:
            # 粗略：大字号文本视为主体数字（数据绑定也算一个数字候选）
            big_numbers += 1
    if big_numbers > 1:
        return [
            make(
                card, "DENSITY.NUMBERS",
                f"出现 {big_numbers} 个大数字（fontSize>=24）> 1",
                severity=P1,
                expected="主数字唯一（maxVisibleNumbers=1）",
                actual=f"{big_numbers} 个",
                fix_hint="保留一个主数字，其余转为状态/文字",
            )
        ]
    return []
