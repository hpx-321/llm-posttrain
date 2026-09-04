"""颜色字节序适配（Phase 1 第 1 步）。

DSL 里的颜色是 ``#AARRGGBB``（如 ``#E5000000`` / ``#FFFDECEA``），而 ``DESIGN.md``
front-matter 里的 token 是 ``#RRGGBBAA``（如 ``#000000E5``）。做逐值比对前必须先归一，
否则会全量误报。本模块提供双向归一与模板值比对。
"""
from __future__ import annotations

import re
from typing import Optional

from .design_contract import ALPHA_STEPS as ALPHA_13_STEPS

HEX_RE = re.compile(r"^#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})$")


def _hex_component(value: str, start: int, length: int = 2) -> str:
    return value[start : start + length]


def normalize_aarrggbb(value: str) -> Optional[str]:
    """把 DSL 颜色 ``#AARRGGBB``（或 6 位 ``#RRGGBB``）转成设计规范的 ``#RRGGBBAA``。"""
    value = value.strip()
    m = HEX_RE.match(value)
    if not m:
        return None
    h = m.group(1)
    if len(h) == 6:
        return f"#{h}FF"
    alpha = h[0:2]
    rgb = h[2:8]
    return f"#{rgb}{alpha}"


def normalize_rgba_to_rrggbbaa(value: str) -> Optional[str]:
    """任何规范的 8 位/6 位 hex 都归一到 ``#RRGGBBAA``（非 8 位补 FF 不透明）。"""
    value = value.strip()
    m = HEX_RE.match(value)
    if not m:
        return None
    h = m.group(1)
    if len(h) == 6:
        return f"#{h}FF"
    return f"#{h}"


def hex_rrggbbaa(value: str) -> Optional[str]:
    """对任意输入先按 DSL、再按规范顺序尝试归一，返回规范形式或 None。"""
    return normalize_rgba_to_rrggbbaa(value) or normalize_aarrggbb(value)


def alpha_channel(rrggbbaa: str) -> Optional[int]:
    """返回 alpha 通道（0-255）；非法输入返回 None。"""
    normalized = normalize_rgba_to_rrggbbaa(rrggbbaa)
    if normalized is None:
        return None
    return int(normalized[7:9], 16)


def parse_ar_color(value: str) -> Optional[tuple]:
    """把 DSL（ARGB）颜色解析为 (r,g,b,a) 0..1。

    - 6 位 ``#RRGGBB``：不透明（alpha=1.0）；
    - 8 位 ``#AARRGGBB``：标准 DSL 字节序。
    """
    m = HEX_RE.match(value.strip())
    if not m:
        return None
    h = m.group(1)
    if len(h) == 6:
        a = "FF"
        rgb = h
    else:
        a, rgb = h[0:2], h[2:8]
    try:
        r = int(rgb[0:2], 16) / 255.0
        g = int(rgb[2:4], 16) / 255.0
        b = int(rgb[4:6], 16) / 255.0
        alpha = int(a, 16) / 255.0
    except ValueError:
        return None
    return r, g, b, alpha


#: 13 档 alpha 单一来源（DESIGN.md《Hex 与透明度规则》；goal Phase 0 统一：
#: 历史本地字面量含 0x40/0x59/0x73/0x80 错误档位，已删除，统一导入 design_contract.ALPHA_STEPS）。
#: 兼容别名
alpha_13_steps = ALPHA_13_STEPS
alpha_value = alpha_channel


def alpha_class(alpha: int) -> Optional[int]:
    """把 alpha 映到最近的 13 档；越界返回 None。"""
    if not 0 <= alpha <= 255:
        return None
    return min(ALPHA_13_STEPS, key=lambda step: abs(step - alpha))
