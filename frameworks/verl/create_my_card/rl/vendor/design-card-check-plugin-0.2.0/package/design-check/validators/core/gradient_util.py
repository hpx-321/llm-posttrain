"""渐变共享助手（自 rules/gradient.py 上提，Idea2-WP-A 2026-08-26）。

scene/contrast/color 三个规则模块共享的渐变解析/预设匹配逻辑；
原私有名经 rules/gradient.py re-export 保持兼容（消费方零改动）。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..design_contract import ALPHA_CEIL_VARIANTS

#: 模糊档进值 → 去尾登记值（owner 裁决 2026-08-22：两者等价，匹配统一归一）
_CEIL_TO_FLOOR_HEX = {f"{ceil:02x}": f"{floor:02x}" for ceil, floor in ALPHA_CEIL_VARIANTS.items()}


def _card_gradient(root) -> Optional[Tuple[str, str, List]]:
    """返回 (kind, direction, colors_list)；kind in {linear, radial} 或 None。"""
    styles = root.get("styles") or {}
    if "linearGradient" in styles:
        g = styles["linearGradient"] or {}
        return "linear", g.get("direction", ""), g.get("colors") or []
    if "radialGradient" in styles:
        g = styles["radialGradient"] or {}
        return "radial", g.get("center", ""), g.get("colors") or []
    return None


def _normalize_colors_from_dsl(pairs) -> set:
    from ..colors import hex_rrggbbaa, normalize_aarrggbb

    out = set()
    if not isinstance(pairs, list):
        return out
    for pair in pairs:
        if isinstance(pair, (list, tuple)) and pair:
            rgba = normalize_aarrggbb(str(pair[0])) or hex_rrggbbaa(str(pair[0]))
            if rgba:
                # owner 裁决 2026-08-22：模糊档进值（如 0x1A）与去尾登记值（0x19）
                # 等价，预设匹配前统一归一到去尾形式（#0A59F71A 卡视为 office-focus）。
                # normalize_aarrggbb 带 # 前缀，先剥前缀取 alpha 字节再重组。
                stripped = rgba.lower().lstrip("#")
                if len(stripped) == 8:
                    stripped = stripped[:6] + _CEIL_TO_FLOOR_HEX.get(stripped[6:8], stripped[6:8])
                out.add("#" + stripped)
    return out


def _match_preset(contract: Dict, card_colors: set) -> Optional[str]:
    if not card_colors:
        return None
    gradients = contract.get("gradients") or {}
    for name, spec in gradients.items():
        stop_colors = {c for _, c in spec.get("stops") or []}
        if stop_colors and card_colors == stop_colors:
            return name
        if stop_colors and card_colors.issubset(stop_colors):
            return name
    return None
