"""ICON.* —— 图标尺寸/位置/素材契约（DESIGN.md §Icons & Resource Assets）。

依据（《Icons & Resource Assets》场景枚举）：资源 SVG 原始尺寸是坐标系不是显示尺寸，
最终尺寸按场景选择：
- 左上标题前置 leading-icon 12vp；右上 leading-icon 20vp；
- button-icon-2x2（纯图标按钮）内部图标 16vp；图文按钮内部图标 20vp；
- display-ring 中心图标 24vp；paired-data-ring 中心 16vp；
- hero 56vp 仅 icon_weather1（由 ASSET.HERO_ICON_CONTRACT 承接，此处不重复）。

2026-08-24 owner 裁决（C-Q006 驱动，front-matter sizes.button-with-icon-content /
button-icon-2x2-content token）：图文按钮（按钮子树内有 Text 或按钮自身带 label 属性）
内部图标按 20vp，纯图标按钮内部图标维持 16vp。

genui 组件表扁平（children 为 id 引用），上下文识别先解析 id 索引再判结构；
能定位的场景才判尺寸，定位不到的图标不报（宁缺毋滥，避免臆断）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from validators.core.tree import (  # noqa: F401  树工具上提 core 后 re-export 保持兼容
    _comp_index,
    _parent_map,
    _resolved_children,
    _numeric_vp,
    _nearest_clickable_ancestor,
    _is_card_root,
    _is_button_like,
)
from validators.dsl import GenuiCard
from validators.finding import Finding, P1, P2
from validators.rules import register
from validators.rules._common import make

#: 各场景契约尺寸（vp）
LEADING_TOP_LEFT = 12
LEADING_TOP_RIGHT = 20
BUTTON_ICON = 16          # 纯图标按钮（button-icon-2x2）内部图标
BUTTON_ICON_WITH_TEXT = 20  # 图文按钮内部图标（2026-08-24 C-Q006 裁决）
DISPLAY_RING_CENTER = 24
PAIRED_RING_CENTER = 16

#: 多色资源集合（§1501：多色资源不得被自动改色；DSL 侧唯一多色插画为天气 hero）
MULTICOLOR_SRCS = {"icon_weather1"}


def _is_title_row(row: Dict[str, Any]) -> bool:
    cid = str(row.get("id") or "").lower()
    return "title" in cid or "header" in cid


def _row_position(comp: Dict[str, Any], children: List[Dict[str, Any]]) -> Optional[str]:
    """图标在标题行中的位置：leading（文字前）/ trailing（文字后）。"""
    ids = [c.get("id") for c in children]
    try:
        idx = ids.index(comp.get("id"))
    except ValueError:
        return None
    texts_after = any(c.get("component") == "Text" for c in children[idx + 1:])
    texts_before = any(c.get("component") == "Text" for c in children[:idx])
    if texts_after and not texts_before:
        return "leading"
    if texts_before and not texts_after:
        return "trailing"
    return None


def _ring_stack_count(index: Dict[str, Dict[str, Any]]) -> int:
    """含 Progress 的 Stack 数量：1 = display-ring，>=2 = paired-data-ring。"""
    count = 0
    for comp in index.values():
        if comp.get("component") != "Stack":
            continue
        if any(c.get("component") == "Progress" for c in _resolved_children(index, comp)):
            count += 1
    return count


def _subtree_has_text(index: Dict[str, Dict[str, Any]], comp: Dict[str, Any]) -> bool:
    """子树（沿 _resolved_children 递归）内是否存在 Text 组件。"""
    for child in _resolved_children(index, comp):
        if child.get("component") == "Text":
            return True
        if _subtree_has_text(index, child):
            return True
    return False


def _classify_icon(index: Dict[str, Dict[str, Any]], parents: Dict[str, Dict[str, Any]],
                   comp: Dict[str, Any]) -> Tuple[Optional[str], Optional[int]]:
    """返回 (场景, 期望尺寸)；识别不了返回 (None, None)。"""
    parent = parents.get(comp.get("id"))
    if parent is None:
        return None, None
    # 按钮内部（最近的 clickable 祖先是按钮样小容器，而非整卡点击的 root）：
    # 图文按钮（子树有 Text 或按钮自身带 label）内部图标 20vp；
    # 纯图标按钮内部图标 16vp（2026-08-24 C-Q006 裁决，front-matter sizes token）。
    clickable = _nearest_clickable_ancestor(comp, parents)
    if clickable is not None and _is_button_like(clickable, parents):
        if _subtree_has_text(index, clickable) or clickable.get("label"):
            return "button-icon-with-text", BUTTON_ICON_WITH_TEXT
        return "button-icon", BUTTON_ICON
    # 环中心（与 Progress 同处一个 Stack）
    if parent.get("component") == "Stack" and any(
        c.get("component") == "Progress" for c in _resolved_children(index, parent)
    ):
        if _ring_stack_count(index) >= 2:
            return "paired-data-ring-center", PAIRED_RING_CENTER
        return "display-ring-center", DISPLAY_RING_CENTER
    # 标题行 leading/trailing
    if parent.get("component") == "Row" and _is_title_row(parent):
        pos = _row_position(comp, _resolved_children(index, parent))
        if pos == "leading":
            return "title-leading-icon", LEADING_TOP_LEFT
        if pos == "trailing":
            return "title-trailing-icon", LEADING_TOP_RIGHT
    return None, None


def _src_basename(src: Any) -> str:
    """去扩展名的 basename（.svg 引用可命中同名 .png，故统一按 stem 比对）。"""
    return Path(str(src or "").rstrip("/")).stem


@register("ICON.SIZE_CONTRACT")
def check_icon_size(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """C1/C2：图标尺寸按场景契约；位置由结构判定（12 在文字前、20 在文字后不颠倒）。"""
    findings: List[Finding] = []
    index = _comp_index(card)
    parents = _parent_map(index)
    for comp in index.values():
        if comp.get("component") != "Image":
            continue
        scene, expected = _classify_icon(index, parents, comp)
        if scene is None or expected is None:
            continue
        styles = comp.get("styles") or {}
        for dim in ("width", "height"):
            actual = _numeric_vp(styles.get(dim))
            if actual is None or abs(actual - expected) < 0.5:
                continue
            findings.append(
                make(
                    card, "ICON.SIZE_CONTRACT",
                    f"{scene} 场景图标 {dim} 应为 {expected}vp，实际 {actual:g}vp",
                    comp.get("id"), severity=P1,
                    expected=f"{scene}: {dim}={expected}vp",
                    actual=f"{dim}={actual:g}vp",
                    fix_hint=f"按 DESIGN.md §Icons 1503 契约改为 {expected}vp",
                )
            )
    return findings


@register("ICON.MULTICOLOR_TINT")
def check_multicolor_tint(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """C4：多色资源（icon_weather1）不得被 fillColor 改色（§1501）。"""
    findings: List[Finding] = []
    for comp in card.iter_components():
        if comp.get("component") != "Image":
            continue
        if _src_basename(comp.get("src")) not in MULTICOLOR_SRCS:
            continue
        styles = comp.get("styles") or {}
        if styles.get("fillColor"):
            findings.append(
                make(
                    card, "ICON.MULTICOLOR_TINT",
                    f"多色资源 {comp.get('src')} 不得被 fillColor 改色",
                    comp.get("id"), severity=P1,
                    expected="多色资源保持原色（不写 fillColor）",
                    actual=f"fillColor={styles.get('fillColor')}",
                    fix_hint="删除 fillColor，按 §Icons 1501 保持多色原样",
                )
            )
    return findings


@register("ICON.DUPLICATE_SRC")
def check_duplicate_src(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """D1：同卡图标不得重复（启发式——DESIGN.md 无明文，按 P2 + 设计师裁决出）。"""
    findings: List[Finding] = []
    seen: Dict[str, List[str]] = {}
    for comp in card.iter_components():
        if comp.get("component") != "Image":
            continue
        src = comp.get("src")
        if not isinstance(src, str):
            continue
        seen.setdefault(src, []).append(comp.get("id") or "?")
    for src, cids in seen.items():
        if len(cids) > 1:
            findings.append(
                make(
                    card, "ICON.DUPLICATE_SRC",
                    f"同卡图标重复使用 {len(cids)} 次: {src}",
                    cids[1], severity=P2,
                    expected="同卡图标不重复",
                    actual=f"{src} × {len(cids)} ({', '.join(cids)})",
                    fix_hint="更换重复实例的语义图标或省略（规范未列明文，需设计师裁决）",
                )
            )
    return findings


def _load_media_basenames() -> set:
    """渲染工程媒体清单（vendored data/media_icons.json）；缺失时返回空集，规则降级跳过。

    匹配按「去扩展名的 basename」——DSL 写 .svg 后缀可命中同名 .png（现网已证实可渲染）。
    """
    data_file = Path(__file__).resolve().parent / "data" / "media_icons.json"
    try:
        data = json.loads(data_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {Path(str(name)).stem for name in data.get("icons") or []}


@register("ICON.SRC_NOT_IN_MEDIA")
def check_src_in_media(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """C3：Image src 必须存在于渲染工程媒体清单（§Icons 1499 只用本地登记 SVG）。

    清单缺失（vendored 文件不存在）时静默跳过——评测集无 task-spec，
    ASSET.UNDECLARED 的 assetCandidates 通道无输入，本规则是评测集的来源校验兜底。
    """
    media = _load_media_basenames()
    if not media:
        return []
    findings: List[Finding] = []
    for comp in card.iter_components():
        if comp.get("component") != "Image":
            continue
        src = comp.get("src")
        if not isinstance(src, str) or not src:
            continue
        if _src_basename(src) not in media:
            findings.append(
                make(
                    card, "ICON.SRC_NOT_IN_MEDIA",
                    f"Image src 不在渲染媒体清单: {src}",
                    comp.get("id"), severity=P1,
                    expected="src ∈ A2UI_Render entry media（validators/data/media_icons.json）",
                    actual=src,
                    fix_hint="改用清单内语义匹配的 SVG，或省略图标（§Icons 1499）",
                )
            )
    return findings


def _load_media_fullnames() -> set:
    """渲染工程媒体清单全名（含扩展名）集合；缺失时返回空集，规则降级跳过。"""
    data_file = Path(__file__).resolve().parent / "data" / "media_icons.json"
    try:
        data = json.loads(data_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    return {str(name) for name in data.get("icons") or []}


@register("ICON.SRC_EXTENSION_MISMATCH")
def check_src_extension_mismatch(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """C3b：src 的 stem 在媒体清单但 stem+同扩展名不在 → 引用扩展名与登记不符（P1）。

    依据：DESIGN.md §Icons 1499 只用本地登记 SVG；渲染工程不回退未登记扩展名
    ——C-Q034 G4 金标准：src=resources/base/media/icon_car.svg，清单仅登记
    "icon_car.png"（vendored media_icons.json，渲染工程同），实测本机渲染器
    不回退 → icon 空白（视觉已核验）。
    判定口径：stem（去扩展名）在清单，但「stem+同扩展名」全名不在清单 → 报；
    stems 均不在清单 → 不报（归 ICON.SRC_NOT_IN_MEDIA 管辖，避免双报）。
    """
    media_full = _load_media_fullnames()
    if not media_full:
        return []
    media_stems = {Path(str(n)).stem for n in media_full}
    findings: List[Finding] = []
    for comp in card.iter_components():
        if comp.get("component") != "Image":
            continue
        src = comp.get("src")
        if not isinstance(src, str) or not src:
            continue
        name = Path(str(src).rstrip("/")).name
        stem, ext = Path(name).stem, Path(name).suffix
        if not ext or stem not in media_stems:
            continue  # 无扩展名或 stem 不在清单 → SRC_NOT_IN_MEDIA 管辖
        if name in media_full:
            continue  # stem+同扩展名登记在案 → 合规
        registered = sorted(n for n in media_full if Path(str(n)).stem == stem)
        findings.append(
            make(
                card, "ICON.SRC_EXTENSION_MISMATCH",
                f"引用 {src}，登记资源仅有 {', '.join(registered)}——引用扩展名与登记不符，"
                f"部分渲染器不回退将渲染空白",
                comp.get("id"), severity=P1,
                expected=f"src 扩展名与登记一致（{stem} + 登记扩展名）",
                actual=f"{name}（登记 {', '.join(registered)}）",
                fix_hint=f"把 src 改为登记资源 {registered[0]}，或改用清单内同语义 SVG（§Icons 1499）",
            )
        )
    return findings
