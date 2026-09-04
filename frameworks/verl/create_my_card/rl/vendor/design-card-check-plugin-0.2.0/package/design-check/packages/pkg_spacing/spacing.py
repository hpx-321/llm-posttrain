"""SPACING.* —— 间距/安全边距规则（E-05）。"""
from __future__ import annotations

from typing import Dict, List

from validators.dsl import GenuiCard
from validators.finding import Finding, P1
from validators.rules import register
from validators.rules._common import make

SAFE_MARGIN = 12


@register("SPACING.SAFE_MARGIN")
def check_safe_margin(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """card-root padding 必须为 safe-margin=12vp（E-05）。"""
    root = card.find_component("root")
    if root is None:
        return []
    padding = (root.get("styles") or {}).get("padding")
    if padding is not None and int(padding) != SAFE_MARGIN:
        return [
            make(
                card, "SPACING.SAFE_MARGIN",
                f"card-root padding 应为 safe-margin={SAFE_MARGIN}vp，实际 {padding}",
                "root", severity=P1,
                expected=f"{SAFE_MARGIN}vp",
                actual=f"{padding}vp",
                fix_hint="保持 root padding = 12",
            )
        ]
    return []


@register("SPACING.SCALE")
def check_spacing_scale(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """根容器 padding 必须落在 spacing 档位（E-05，组件级微调 margin 不作硬性判断）。"""
    root = card.find_component("root")
    if root is None:
        return []
    padding = (root.get("styles") or {}).get("padding")
    if padding is None:
        return []
    allowed = set(contract.get("allowed_spacing") or [])
    if allowed and int(padding) not in allowed:
        return [
            make(
                card, "SPACING.SCALE",
                f"root padding={padding} 不在 spacing 档位",
                "root", severity=P1,
                expected=" ".join(str(s) for s in sorted(allowed)),
                actual=f"root padding={padding}",
                fix_hint="改用 spacing 档位值",
            )
        ]
    return []
