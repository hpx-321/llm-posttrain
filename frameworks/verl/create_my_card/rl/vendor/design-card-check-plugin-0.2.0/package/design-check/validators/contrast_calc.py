"""对比度算子（goal docs/goal-contrast-operator.md P0）。

纯函数、仅标准库。设计要点：
- ``blend_stack`` 自底向上 alpha 合成（layers[0] 为最底层：卡片基底/宿主）；
- ``contrast_ratio`` WCAG 相对亮度对比度；
- ``evaluate`` 接受 DSL(#AARRGGBB) 或规范(#RRGGBBAA) hex，输出比值/判定/逐层 trace；
- ``text_background_stack`` 从 DSL 求文字的有效背景栈（最近祖先底板 → 卡片基底 → 渐变位置色）。
  渐变位置不可知时用「包络区间」（两端 stop 各算一次取 min/max）三态判定，不臆断位置——
  比 goal 原稿的「中点插值」更保守，偏差已记录 docs/plan.md。

依据：DESIGN.md《对比度》（普通阅读文本强制 ≥3:1；2026-08-21 起正文建议 ≥4.5:1，WCAG AA 对齐）。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .colors import normalize_aarrggbb, normalize_rgba_to_rrggbbaa

#: 档位阈值（DESIGN.md《对比度》：3:1 强制；4.5:1 建议级）
MIN_CONTRAST = 3.0
SUGGEST_CONTRAST = 4.5

RGBA = Tuple[float, float, float, float]


def parse_hex(value: str, byteorder: str = "argb") -> Optional[Tuple[int, int, int, int]]:
    """hex → (r,g,b,a) 0..255。byteorder: 'argb'(DSL, 默认) / 'rgba'(规范)。"""
    if not isinstance(value, str):
        return None
    norm = normalize_aarrggbb(value) if byteorder == "argb" else normalize_rgba_to_rrggbbaa(value)
    if not norm:
        return None
    h = norm[1:]  # rrggbbaa
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16)


def _to_unit(rgba: Tuple[int, int, int, int]) -> RGBA:
    r, g, b, a = rgba
    return r / 255.0, g / 255.0, b / 255.0, a / 255.0


def _to_hex(rgb: Tuple[float, float, float]) -> str:
    return "#" + "".join(f"{max(0, min(255, round(c * 255))):02X}" for c in rgb)


def blend_stack(layers: List[RGBA]) -> Tuple[float, float, float]:
    """自底向上 alpha 合成（layers[0] 最底层），返回不透明等效 RGB（0..1）。"""
    if not layers:
        raise ValueError("blend_stack 需要至少一层")
    r, g, b = layers[0][0], layers[0][1], layers[0][2]
    for lr, lg, lb, la in layers[1:]:
        r = lr * la + r * (1 - la)
        g = lg * la + g * (1 - la)
        b = lb * la + b * (1 - la)
    return r, g, b


def _luminance(rgb) -> float:
    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast_ratio(fg_rgb, bg_rgb) -> float:
    """WCAG 对比度：(L亮+0.05)/(L暗+0.05)。"""
    l1, l2 = _luminance(fg_rgb), _luminance(bg_rgb)
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


def evaluate(fg: str, bg_stack: List[str], byteorder: str = "argb") -> Dict:
    """对任意「前景 × 背景栈」求对比度，返回 {ratio, verdict, blended_bg, blended_fg, trace}。

    背景栈自底向上（bg_stack[0] 最底层）；前景先与合成背景做 alpha 合成再计算。
    """
    fg_rgba = parse_hex(fg, byteorder)
    if fg_rgba is None:
        raise ValueError(f"前景色无法解析: {fg!r}")
    layers: List[RGBA] = []
    trace: List[Dict] = []
    for raw in bg_stack:
        rgba = parse_hex(raw, byteorder)
        if rgba is None:
            raise ValueError(f"背景层无法解析: {raw!r}")
        layers.append(_to_unit(rgba))
    bg_rgb = blend_stack(layers)
    fg_unit = _to_unit(fg_rgba)
    fg_rgb = blend_stack([bg_rgb, fg_unit])  # 前景按自身 alpha 合成到背景上
    ratio = contrast_ratio(fg_rgb, bg_rgb)
    return {
        "ratio": round(ratio, 2),
        "verdict": "≥3:1" if ratio >= MIN_CONTRAST else "不足3:1",
        "ratio_pass_3": ratio >= MIN_CONTRAST,
        "ratio_pass_45": ratio >= SUGGEST_CONTRAST,
        "blended_bg": _to_hex(bg_rgb),
        "blended_fg": _to_hex(fg_rgb),
        "fg_raw": fg,
        "bg_raw": list(bg_stack),
        "trace": [{"layer": raw, "parsed_rgba": list(rgba)}
                  for raw, rgba in zip(bg_stack, [tuple(int(c * 255 + 0.5) for c in layer) for layer in layers])],
    }


def gradient_stops_of(card) -> Optional[Dict]:
    """root 渐变 → {kind, stops:[hex...]}（DSL 原始 #AARRGGBB）；无渐变返回 None。"""
    root = card.find_component("root")
    if root is None:
        return None
    styles = root.get("styles") or {}
    for gk in ("linearGradient", "radialGradient"):
        g = styles.get(gk)
        if isinstance(g, dict) and g.get("colors"):
            return {"kind": gk, "stops": [str(p[0]) for p in g["colors"] if isinstance(p, (list, tuple)) and p]}
    return None


def _parent_map(card) -> Dict[str, Dict]:
    parents: Dict[str, Dict] = {}
    for comp in card.iter_components():
        for child in (comp.get("children") or []):
            if isinstance(child, str):
                parents[child] = comp
    return parents


def text_background_stack(card, comp_id: str) -> Dict:
    """求文字组件的有效背景栈信息（不含渐变 stop 本身，由调用方做包络）。

    返回 {base: hex|None, panels: [hex ... 自外向内], gradient: {kind,stops}|None,
          ancestors: [组件id ... 自内向外], assumption: str}
    """
    comp = card.find_component(comp_id)
    if comp is None:
        raise ValueError(f"组件不存在: {comp_id}")
    parents = _parent_map(card)
    chain: List[Dict] = []
    node = comp
    while True:
        parent = parents.get(node.get("id"))
        if parent is None:
            break
        chain.append(parent)
        node = parent
    root = card.find_component("root")
    panels = []
    for anc in reversed(chain):  # 自外(root 侧)向内
        if anc.get("id") == "root":
            continue
        bg = (anc.get("styles") or {}).get("backgroundColor")
        if isinstance(bg, str) and bg.strip():
            rgba = parse_hex(bg, "argb")
            if rgba and rgba[3] > 0:  # 全透明层跳过
                panels.append(bg)
    base = (root.get("styles") or {}).get("backgroundColor") if root else None
    gradient = gradient_stops_of(card)
    assumption = "no-gradient"
    if gradient:
        assumption = "linear-envelope" if gradient["kind"] == "linearGradient" else "radial-envelope"
    return {
        "base": base if isinstance(base, str) and base.strip() else "#FFFFFFFF",
        "panels": panels,
        "gradient": gradient,
        "ancestors": [a.get("id") for a in chain],
        "assumption": assumption,
    }


def stack_hexes(info: Dict, gradient_stop: Optional[str]) -> List[str]:
    """把背景栈信息展开为 evaluate 可用的 hex 列表（自底向上）。"""
    layers = [info["base"]]
    if gradient_stop:
        layers.append(gradient_stop)
    layers.extend(info["panels"])  # panels 已按自外向内；底层=最外层板
    return layers


def envelope_evaluate(fg: str, info: Dict) -> Dict:
    """包络三态：对渐变各 stop（无渐变则单次）求比值，返回 min/max 与判定。

    verdict ∈ {'pass'(min≥3), 'fail'(max<3), 'uncertain'(跨 3:1), 'pass-suggest'(min<4.5 建议)}
    """
    stops = (info["gradient"]["stops"] if info["gradient"] else [None])
    results = []
    for stop in stops:
        ev = evaluate(fg, stack_hexes(info, stop))
        results.append(ev)
    ratios = [ev["ratio"] for ev in results]
    ratio_min, ratio_max = min(ratios), max(ratios)
    out = {
        "fg": fg,
        "assumption": info["assumption"],
        "ratio_min": round(ratio_min, 2),
        "ratio_max": round(ratio_max, 2),
        "worst_case": results[ratios.index(ratio_min)],
        "trace": [r for r in results],
    }
    if ratio_min >= MIN_CONTRAST:
        out["verdict"] = "pass" if ratio_min >= SUGGEST_CONTRAST else "pass-suggest"
    elif ratio_max < MIN_CONTRAST:
        out["verdict"] = "fail"
    else:
        out["verdict"] = "uncertain"
    return out
