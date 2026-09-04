"""SHAPE.* —— 圆角规则（E-04 card-root 圆角 / 按钮圆角；B7 同族圆角 / 禁嵌套圆矩）。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from validators.dsl import GenuiCard
from validators.finding import Finding, P1
from validators.rules import register
from validators.rules._common import make
from .icon import (_comp_index, _is_button_like, _parent_map, _resolved_children, _numeric_vp)

CARD_ROOT_RADIUS = 20  # rounded.corner_radius_level10（2026-08-21 规范校准：93/93 落地为 20vp，规范由 level8/16vp 修正为 level10/20vp）
#: 按钮胶囊全圆角下限（2026-08-24 owner 裁决，B-q6/B-q15 驱动）：
#: 金标准语料 39/39 为 17-18、生成侧 system_prompt 为 18，规范口径由
#: 「固定 20vp」改为「胶囊全圆角 ≥18vp」（36vp 高按钮即半高 18 全圆角）。
#: 依据：DESIGN.md《圆角刻度》（corner_radius_level9 = 18vp 按钮全圆角下限）
#: 与《操作 Action》（按钮使用胶囊全圆角：borderRadius ≥ 18vp）。
BUTTON_RADIUS_MIN = 18

#: 高度档位（vp）：同功能同圆角的静态近似分族依据（DESIGN.md §Shapes L1537/L1664）
_SMALL_H = 12
_MEDIUM_H = 48

#: 装饰性嵌套圆矩的内层豁免：图片圆角（level2-4）与进度环/状态环是组件自有契约，
#: 不属于「装饰性嵌套圆矩形」（DESIGN.md §Shapes L1536 / L1545）
_NESTED_INNER_EXEMPT = ("Image", "Progress")


@register("SHAPE.CARD_ROOT_RADIUS")
def check_card_root_radius(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """card-root 圆角必须是 level10=20vp（E-04a；2026-08-21 规范校准后由 16vp 改 20vp）。"""
    root = card.find_component("root")
    if root is None:
        return []
    styles = root.get("styles") or {}
    radius = styles.get("borderRadius")
    if isinstance(radius, (int, float)) and int(radius) != CARD_ROOT_RADIUS:
        return [
            make(
                card, "SHAPE.CARD_ROOT_RADIUS",
                f"card-root 圆角应为 {CARD_ROOT_RADIUS}vp，实际 {radius}",
                "root", severity=P1,
                expected=f"{CARD_ROOT_RADIUS}vp",
                actual=f"{radius}vp",
                fix_hint=f"将 root.borderRadius 改为 {CARD_ROOT_RADIUS}",
            )
        ]
    return []


@register("SHAPE.BUTTON_RADIUS")
def check_button_radius(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """按钮圆角应为胶囊全圆角 ≥18vp（E-04b；2026-08-24 owner 裁决改口径）。

    2026-08-24 裁决（B-q6/B-q15 驱动）：按钮圆角真值由「固定 20vp」改为
    「胶囊全圆角下限 18vp」——金标准语料 39/39 为 17-18、生成侧 system_prompt
    为 18；≥18 一律 pass，<18 报 P1。依据：DESIGN.md《圆角刻度》
    （corner_radius_level9 = 18vp 按钮全圆角下限）与《操作 Action》。
    按钮识别口径与 COLOR.BUTTON_CONTEXT 一致：非卡根 onClick 且 button-like
    （复用 icon._is_button_like；id 不含 button 的按钮同样被查，如 B-q15 parentControl）。
    """
    findings: List[Finding] = []
    index = _comp_index(card)
    parents = _parent_map(index)
    for comp in index.values():
        if not comp.get("onClick") or not _is_button_like(comp, parents):
            continue
        styles = comp.get("styles") or {}
        radius = styles.get("borderRadius")
        if isinstance(radius, (int, float)) and not isinstance(radius, bool) \
                and float(radius) < BUTTON_RADIUS_MIN:
            findings.append(
                make(
                    card, "SHAPE.BUTTON_RADIUS",
                    f"按钮圆角应为胶囊全圆角 ≥{BUTTON_RADIUS_MIN}vp，实际 {radius}",
                    comp.get("id"), severity=P1,
                    expected=f"≥{BUTTON_RADIUS_MIN}vp（胶囊全圆角，DESIGN.md《圆角刻度》《操作 Action》）",
                    actual=f"{radius}vp",
                    fix_hint=f"将 borderRadius 改为 ≥{BUTTON_RADIUS_MIN}（36vp 高按钮即半高 {BUTTON_RADIUS_MIN} 全圆角）",
                )
            )
    return findings


def _height_bucket(comp: Dict[str, Any]) -> str:
    """高度档位：small ≤12vp / medium ≤48vp / large >48vp（无高度时按宽度折算）。"""
    styles = comp.get("styles") or {}
    h = _numeric_vp(styles.get("height"))
    if h is None:
        h = _numeric_vp(styles.get("width"))
    if h is None:
        return "unknown"
    if h <= _SMALL_H:
        return "small"
    if h <= _MEDIUM_H:
        return "medium"
    return "large"


@register("SHAPE.RADIUS_FAMILY")
def check_radius_family(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """同一功能用同一圆角，不做逐实例圆角微调（DESIGN.md §Shapes L1537 明文；L1664）。

    静态口径（2026-08-22 语料校准）：按「组件类型 × 高度档位」分族比对 borderRadius——
    纯按类型会误报（语料 q021/q040 中同类型 surface 底板按尺寸分属不同功能）；
    非卡根可点击控件另按整卡可点击族比对（2026-08-24 裁决后按钮为胶囊全圆角 ≥18vp，
    族内一致性要求不变：同卡可点击控件不混用多种圆角）。
    同族出现 ≥2 种不同圆角 → P1。
    """
    findings: List[Finding] = []
    index = _comp_index(card)
    parents = _parent_map(index)
    root_id = "root" if "root" in index else next((i for i in index if i not in parents), None)

    by_group: Dict[Any, Dict[int, str]] = {}
    click_family: Dict[int, str] = {}
    for comp in index.values():
        styles = comp.get("styles") or {}
        radius = styles.get("borderRadius")
        if not isinstance(radius, (int, float)):
            continue
        r = int(radius)
        if comp.get("id") != root_id and comp.get("onClick"):
            click_family.setdefault(r, comp.get("id"))
            continue
        if comp.get("id") == root_id:
            continue  # card-root 圆角由 SHAPE.CARD_ROOT_RADIUS 独立承接
        group = (comp.get("component"), _height_bucket(comp))
        by_group.setdefault(group, {}).setdefault(r, comp.get("id"))

    for group, radii in by_group.items():
        if len(radii) > 1:
            r_list = sorted(radii)
            findings.append(
                make(
                    card, "SHAPE.RADIUS_FAMILY",
                    f"同功能组件族 {group[0]}（{group[1]} 档）混用 {len(radii)} 种圆角: {r_list}",
                    radii[r_list[1]], severity=P1,
                    expected="同一功能用同一圆角（DESIGN.md §Shapes L1537/L1664）",
                    actual=f"{group[0]} {group[1]} 档: {r_list}vp 混用",
                    fix_hint="收敛为该族统一的 corner_radius_level* token，不做逐实例微调",
                )
            )
    if len(click_family) > 1:
        r_list = sorted(click_family)
        findings.append(
            make(
                card, "SHAPE.RADIUS_FAMILY",
                f"整卡可点击控件族混用 {len(click_family)} 种圆角: {r_list}vp",
                click_family[r_list[1]], severity=P1,
                expected="同卡可点击控件圆角一致（胶囊全圆角 ≥18vp，2026-08-24 裁决）",
                actual=f"可点击族: {r_list}vp 混用",
                fix_hint="可点击控件统一收敛为一个圆角值（≥18vp 胶囊全圆角），其余形态按各自契约",
            )
        )
    return findings


def _subtree_rounded_non_exempt(index: Dict[str, Dict[str, Any]], comp: Dict[str, Any]
                                ) -> Optional[str]:
    """子树中第一个非豁免（非 Image/Progress）且 borderRadius>0 的组件 id。"""
    for child in _resolved_children(index, comp):
        if child.get("component") in _NESTED_INNER_EXEMPT:
            continue
        br = (child.get("styles") or {}).get("borderRadius")
        if isinstance(br, (int, float)) and int(br) > 0:
            return child.get("id")
        hit = _subtree_rounded_non_exempt(index, child)
        if hit is not None:
            return hit
    return None


@register("SHAPE.NESTED_RADIUS")
def check_nested_radius(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """不使用装饰性嵌套圆矩形（DESIGN.md §Shapes L1545 明文）。

    判定：非卡根、非图片/进度环的外层组件 borderRadius>0 时，其子树内不得再有
    非图片/进度环的 borderRadius>0 组件；card-root 是卡片外边界，不算嵌套外层。
    """
    findings: List[Finding] = []
    index = _comp_index(card)
    parents = _parent_map(index)
    root_id = "root" if "root" in index else next((i for i in index if i not in parents), None)
    for comp in index.values():
        cid = comp.get("id")
        if cid == root_id or cid not in parents:
            continue  # 卡根与顶层组件不是嵌套外层
        if comp.get("component") in _NESTED_INNER_EXEMPT:
            continue
        br = (comp.get("styles") or {}).get("borderRadius")
        if not (isinstance(br, (int, float)) and int(br) > 0):
            continue
        inner = _subtree_rounded_non_exempt(index, comp)
        if inner is not None:
            findings.append(
                make(
                    card, "SHAPE.NESTED_RADIUS",
                    f"装饰性嵌套圆矩形：圆角容器 {cid}（{int(br)}vp）内嵌套圆角组件 {inner}",
                    inner, severity=P1,
                    expected="不使用装饰性嵌套圆矩形（DESIGN.md §Shapes L1545）",
                    actual=f"{cid}({int(br)}vp) 内嵌 {inner}",
                    fix_hint="去掉内层或外层的圆角，只保留一层圆角表面；图片/进度环除外",
                )
            )
    return findings
