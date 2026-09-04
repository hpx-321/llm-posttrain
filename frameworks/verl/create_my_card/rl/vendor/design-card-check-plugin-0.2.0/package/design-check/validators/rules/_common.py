"""L1 规则公共小工具。"""
from __future__ import annotations

from typing import Optional

from ..dsl import GenuiCard
from ..finding import Element, Finding, PROGRAM, P1
from ..colors import hex_rrggbbaa, normalize_aarrggbb


def pointer(card: GenuiCard, dsl_id: str) -> str:
    # 说明：JSON Pointer 只精确到组件 id（组件索引可在打印证据时补齐）。
    return f"/updateComponents/components/{dsl_id}"


def el(card: GenuiCard, dsl_id: Optional[str] = None) -> Element:
    return Element(dsl_id=dsl_id, json_pointer=pointer(card, dsl_id) if dsl_id else "")


def make(
    card: GenuiCard,
    rule_id: str,
    message: str,
    dsl_id: Optional[str] = None,
    *,
    severity: str = P1,
    evidence_type: str = PROGRAM,
    expected: str = "",
    actual: str = "",
    fix_hint: str = "",
    layer: str = "L1",
) -> Finding:
    return Finding(
        qid=card.case_id,
        layer=layer,
        rule_id=rule_id,
        severity=severity,
        evidence_type=evidence_type,
        element=el(card, dsl_id),
        expected=expected,
        actual=actual,
        fix_hint=fix_hint,
        message=message,
    )


def color_value_rgba(value) -> Optional[str]:
    """把 DSL 颜色（ARGB / RGB）归一到规范 #rrggbbaa 形式，用于与 token 集合比对。"""
    if not isinstance(value, str):
        return None
    # DSL 8 位色是 AARRGGBB；先按 ARGB 归一，6 位按不透明 RGB 处理。
    return normalize_aarrggbb(value) or hex_rrggbbaa(value)


def alpha_of_rgba(rrggbbaa: str) -> Optional[int]:
    """从 #rrggbbaa 取 alpha 通道（0-255）。"""
    try:
        return int(rrggbbaa[7:9], 16)
    except Exception:
        return None


def count_components(card: GenuiCard, component: str) -> int:
    return sum(1 for c in card.iter_components() if c.get("component") == component)
