"""GRADIENT.* —— 卡片背景渐变规则（E-02）。"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from validators.core.gradient_util import (  # noqa: F401  渐变共享助手上提 core 后 re-export 保持兼容
    _card_gradient,
    _normalize_colors_from_dsl,
    _match_preset,
)
from validators.dsl import GenuiCard
from validators.finding import Finding, P1
from validators.design_contract import ALPHA_CEIL_VARIANTS
from validators.rules import register
from validators.rules._common import make

def _preset_shape(preset: dict) -> str:
    return str(preset.get("type") or "linear")


def _card_shape_desc(kind: str, direction: str) -> str:
    return f"{kind} {direction}" if direction else kind


@register("GRADIENT.MISSING_FALLBACK")
def check_missing_fallback(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """card-root 必须叠加场景渐变；未命中精确场景时必须用 general-fallback（E-02b）。"""
    root = card.find_component("root")
    if root is None:
        return []
    if _card_gradient(root) is None:
        return [
            make(
                card, "GRADIENT.MISSING_FALLBACK",
                "card-root 只有基底无场景渐变，必须叠加 general-fallback 或精确场景渐变",
                "root", severity=P1,
                expected="base-color + gradient overlay (general-fallback 兜底)",
                actual="仅 backgroundColor，无 linearGradient/radialGradient",
                fix_hint="为 root 增加 general-fallback 渐变遮罩",
            )
        ]
    return []


@register("GRADIENT.UNREGISTERED")
def check_unregistered(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """渐变 stops 必须精确匹配某个注册预设（E-02a，禁止自定义渐变）。"""
    root = card.find_component("root")
    if root is None:
        return []
    ginfo = _card_gradient(root)
    if ginfo is None:
        return []
    card_colors = _normalize_colors_from_dsl(ginfo[2])
    preset = _match_preset(contract, card_colors) if contract.get("gradients") else None
    if preset is None and card_colors:
        return [
            make(
                card, "GRADIENT.UNREGISTERED",
                f"渐变 stops {sorted(card_colors)} 不匹配任何注册预设",
                "root", severity=P1,
                expected="匹配 background_gradients 中的一个预设",
                actual="自定义渐变/未注册 stops",
                fix_hint="改用注册预设（如 general-fallback）或命中精确场景",
            )
        ]
    return []


@register("GRADIENT.PRESET_MISMATCH")
def check_preset_mismatch(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """颜色命中某预设但形状/方向不符（E-02c，q010 weather linear≠radial 真实案例）。"""
    root = card.find_component("root")
    if root is None:
        return []
    ginfo = _card_gradient(root)
    if ginfo is None:
        return []
    kind, direction, pairs = ginfo
    card_colors = _normalize_colors_from_dsl(pairs)
    preset_name = _match_preset(contract, card_colors)
    if preset_name is None:
        return []
    preset = contract["gradients"][preset_name]
    expected_shape = _preset_shape(preset)
    if expected_shape != kind:
        return [
            make(
                card, "GRADIENT.PRESET_MISMATCH",
                f"颜色命中预设 {preset_name}（{expected_shape}），但卡片用 {kind}",
                "root", severity=P1,
                expected=f"{expected_shape} {preset.get('direction') or preset.get('center') or ''}"
                         f" {'→'.join(c for _, c in preset.get('stops') or [])}",
                actual=_card_shape_desc(kind, direction),
                fix_hint=f"将背景改为 {preset_name}（{expected_shape}）",
            )
        ]
    return []
