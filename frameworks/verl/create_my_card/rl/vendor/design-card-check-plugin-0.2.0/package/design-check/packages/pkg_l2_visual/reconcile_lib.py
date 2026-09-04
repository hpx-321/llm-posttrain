"""L2b 声明↔真值对账（E-11 类 + goal Phase 2 颜色/透明度对账）。

- DIMENSION_DRIFT：DSL 声明 width/height 与 dump 实测尺寸（vp），容差 ±1px；
  DSL 中 height 可能是 ``matchParent`` 或数值，只对明确数值对账。
- COLOR_DRIFT（goal docs/goal-dsh-design-check-plugin.md Phase 2，E-19/E-21）：
  DSL 声明 backgroundColor vs dump 实测 backgroundColor（两侧同为 #AARRGGBB，归一后比较）。
  dump 值为空或 #00000000 而声明非透明 → 「需端侧确认」（渲染层常不回填背景，不强行判违规）。
  依据：DESIGN.md snapshot 契约 mustMatchRealLayout（约 L1009-1012）。
- OPACITY_DRIFT（E-20）：声明 opacity（缺省 1.0）vs dump opacity，漂移报 P2。
  dump 拿不到 fontColor/fillColor——前景色已在 L1 声明侧校验，本层不推测（报告盲区说明）。
"""
from __future__ import annotations

from typing import List, Optional

from validators.colors import normalize_aarrggbb
from validators.dsl import GenuiCard
from validators.finding import Element, Finding, P1, P2, PROGRAM, DEVICE, L2B
from .geometry import make_finding  # noqa: F401
from .layout import DumpLayout, DumpNode

TOL_PX = 1.0
PX_PER_VP = 3.5
TOL_VP = TOL_PX / PX_PER_VP
OPACITY_TOL = 0.01


def _declared_rgba(raw) -> Optional[str]:
    """DSL 声明色（#AARRGGBB/#RGB6）→ #rrggbbaa；非字符串/非法返回 None。"""
    if not isinstance(raw, str):
        return None
    norm = normalize_aarrggbb(raw)
    return norm.lower() if norm else None


def _dump_rgba(raw) -> Optional[str]:
    """dump 实测色（#AARRGGBB）→ #rrggbbaa；空/非法返回 None。"""
    if not isinstance(raw, str) or not raw.strip():
        return None
    norm = normalize_aarrggbb(raw)
    return norm.lower() if norm else None


def _as_float(raw) -> Optional[float]:
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return None


def reconcile_colors(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """声明 backgroundColor vs dump 实测背景色对账（goal Phase 2 / E-19、E-21）。"""
    findings: List[Finding] = []
    for comp in card.iter_components():
        dsl_id = comp.get("id")
        declared = _declared_rgba((comp.get("styles") or {}).get("backgroundColor"))
        if declared is None:
            continue  # 未声明背景色，无对账义务
        node = layout.find_by_id(dsl_id)
        if node is None:
            continue
        measured = _dump_rgba(node.attributes.get("backgroundColor"))
        if measured in (None, "", "#00000000"):
            if declared != "#00000000":
                findings.append(Finding(
                    qid=card.case_id, layer=L2B, rule_id="RECONCILE.COLOR_DRIFT",
                    severity=P2, evidence_type=DEVICE,
                    element=Element(dsl_id=dsl_id, json_pointer="", dump_id=dsl_id),
                    expected=f"backgroundColor={declared}",
                    actual="dump 未回填背景色（#00000000/空）",
                    fix_hint="端侧确认实际背景（dump 对非容器组件背景常不回填）",
                    message=f"{dsl_id} 声明背景 {declared}，dump 未回填，待端侧确认",
                    evidence_file=layout.source,
                ))
            continue
        if measured != declared:
            findings.append(Finding(
                qid=card.case_id, layer=L2B, rule_id="RECONCILE.COLOR_DRIFT",
                severity=P1, evidence_type=PROGRAM,
                element=Element(dsl_id=dsl_id, json_pointer="", dump_id=dsl_id),
                expected=f"backgroundColor={declared}",
                actual=f"dump 实测 {measured}",
                fix_hint="对齐声明与渲染（检查 token 展开/主题覆盖丢失）",
                message=f"{dsl_id} 声明背景 {declared}，dump 实测 {measured}",
                evidence_file=layout.source,
            ))
    return findings


def reconcile_opacity(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    """声明 opacity（缺省 1.0）vs dump opacity 对账（goal Phase 2 / E-20）。"""
    findings: List[Finding] = []
    for comp in card.iter_components():
        dsl_id = comp.get("id")
        declared = _as_float((comp.get("styles") or {}).get("opacity"))
        if declared is None:
            declared = 1.0
        node = layout.find_by_id(dsl_id)
        if node is None:
            continue
        measured = _as_float(node.attributes.get("opacity"))
        if measured is None:
            continue
        if abs(declared - measured) > OPACITY_TOL:
            findings.append(Finding(
                qid=card.case_id, layer=L2B, rule_id="RECONCILE.OPACITY_DRIFT",
                severity=P2, evidence_type=PROGRAM,
                element=Element(dsl_id=dsl_id, json_pointer="", dump_id=dsl_id),
                expected=f"opacity={declared}",
                actual=f"dump 实测 {measured}",
                fix_hint="对齐声明与渲染透明度",
                message=f"{dsl_id} 声明 opacity={declared}，dump 实测 {measured}",
                evidence_file=layout.source,
            ))
    return findings


def reconcile(card: GenuiCard, layout: DumpLayout) -> List[Finding]:
    findings: List[Finding] = []
    declared = {c.get("id"): c for c in card.iter_components() if c.get("id")}
    for dsl_id, comp in declared.items():
        node = layout.find_by_id(dsl_id)
        if node is None:
            continue
        styles = comp.get("styles") or {}
        bvp = node.bounds_vp()
        if bvp is None:
            continue
        w = bvp[2] - bvp[0]
        h = bvp[3] - bvp[1]
        for prop, measured in (("width", w), ("height", h)):
            declared_val = styles.get(prop)
            if not isinstance(declared_val, (int, float)):
                continue
            if abs(declared_val - measured) > TOL_VP:
                findings.append(Finding(
                    qid=card.case_id, layer=L2B, rule_id="RECONCILE.DIMENSION_DRIFT",
                    severity=P1, evidence_type=PROGRAM,
                    element=Element(dsl_id=dsl_id, json_pointer="", dump_id=dsl_id),
                    expected=f"{prop}={declared_val}vp",
                    actual=f"{prop}={measured:.1f}vp",
                    fix_hint="检查 layoutWeight/约束导致渲染走样",
                    message=f"{dsl_id} {prop} 声明 {declared_val}vp 实测 {measured:.1f}vp",
                    evidence_file=layout.source,
                ))
    findings += reconcile_colors(card, layout)
    findings += reconcile_opacity(card, layout)
    return findings
