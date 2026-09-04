"""VISUAL.CONTRAST —— 可见性/对比度（goal docs/goal-contrast-operator.md P2 重构）。

依据：DESIGN.md《对比度》（普通阅读文本强制 ≥3:1；2026-08-21 起正文建议 ≥4.5:1，WCAG AA 对齐）。

与旧实现的差异（D4 一并处理）：
- 背景模型：全卡单色近似 → 「文字所在背景栈」（卡片基底 → root 渐变 stop 包络 → 祖先底板），
  由 validators.contrast_calc 算子驱动（规则与 CLI 工具共用同一实现）；
- 判定三态（渐变位置不可知时取两端 stop 包络，不臆断位置）：
  fail（全位置 <3:1）→ P1 程序已证实；
  uncertain（跨 3:1，取决于文字实际位置）→ P2 需端侧确认；
  pass-suggest（过 3:1 但 <4.5:1）→ P2 建议级（规范建议档，非强制）；
  pass（最不利位置 ≥4.5:1）→ 不报。

A2 盲区补法（2026-08-22，WP5，依据 docs/goal-detection-plugin-target.md A2）：
① 未声明 fontColor 的 Text 不再静默跳过：按隐式前景进入算子——
   不透明场景渐变（weather/rainy-weather/sports-health/sleep，DESIGN.md
   《渐变场景》反色文本阶条款）隐式为 #FFFFFFFF；浅色遮罩/基底隐式为 #000000E5
   （colors.font_primary 浅色主题默认）。渐变类别按「卡片命中登记预设」判定：
   浅色遮罩预设的 opaqueEquivalent 烘焙变体（#opaque）仍是浅色底，不按 stops 不透明度误判。
   隐式前景命中时 finding 标注「隐式前景假设」。
② fontColor 为 token 写法（{{colors.font_primary}} 等）时展开为字面 hex 再进算子；
   token→hex 映射来自 validators/data/color_profile.json（DESIGN.md colors/themes.dark，
   不修改 design_contract.py）；展开不了的按 uncertain 三态（P2 需端侧确认），不臆报。
③ content 为空白/空的 Text（装饰性 surface，无字形可读）不参与对比度判定。

2026-08-24 owner 裁决（DESIGN.md《对比度》新增条款）：按钮子树内文字对比度不足
由 P1 降为 P2 提醒——按钮配色由 button_color_rules 登记形态（Gradient Card Button
Colors / 操作 Action 按钮形态配对色）全权管辖，对比度算子不重复判定；
按钮外文字维持 P1。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from validators.contrast_calc import envelope_evaluate, text_background_stack
from validators.dsl import GenuiCard
from validators.finding import Finding, P1, P2, PROGRAM, DEVICE
from validators.rules import register
from validators.rules._common import make
from .gradient import _card_gradient, _normalize_colors_from_dsl, _match_preset
from .icon import _comp_index, _is_button_like, _nearest_clickable_ancestor, _parent_map

_FG_KEYS = ("fontColor", "textColor")

#: A2-① 隐式前景（DESIGN.md L1184 反色文本阶 / L12 colors.font_primary 浅色主题默认）
IMPLICIT_FG_OPAQUE = "#FFFFFFFF"  # 不透明场景渐变反色前景
IMPLICIT_FG_LIGHT = "#000000E5"   # 浅色底深色默认（font_primary，light 主题）

#: token→hex 共享映射（A2-②；validators/data/color_profile.json，DESIGN.md colors/themes.dark）
_COLOR_PROFILE_PATH = Path(__file__).resolve().parent / "data" / "color_profile.json"


def _load_color_profile() -> Dict:
    try:
        data = json.loads(_COLOR_PROFILE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


_COLOR_PROFILE: Dict = _load_color_profile()

#: token 形态：{{colors.font_primary}} / {colors.font_primary} / 裸 colors.*、themes.* 路径
_TOKEN_RE = re.compile(r"^\s*\{\{\s*([\w./-]+)\s*\}\}\s*$")
_TOKEN1_RE = re.compile(r"^\s*\{\s*([\w./-]+)\s*\}\s*$")
_TOKEN_BARE_RE = re.compile(r"^(?:colors|themes)\.[\w./-]+$")


def _looks_like_token(raw: str) -> bool:
    return bool(_TOKEN_RE.match(raw) or _TOKEN1_RE.match(raw) or _TOKEN_BARE_RE.match(raw))


def _expand_token(raw: str, profile: Dict) -> Optional[str]:
    """token 写法 → 字面 hex（#RRGGBBAA，DESIGN.md 字节序）；展开不了返回 None。"""
    m = _TOKEN_RE.match(raw) or _TOKEN1_RE.match(raw)
    path = m.group(1) if m else raw.strip()
    tokens = (profile or {}).get("tokens") or {}
    if path in tokens:
        return tokens[path]
    if "." not in path and f"colors.{path}" in tokens:
        return tokens[f"colors.{path}"]
    return None


def _rrggbbaa_to_argb(hex_rgba: str) -> str:
    """DESIGN.md #RRGGBBAA → DSL #AARRGGBB（算子按 argb 解析背景栈）。"""
    h = hex_rgba.strip().lstrip("#").lower()
    if len(h) == 8:
        return f"#{h[6:8]}{h[0:6]}"
    return f"#{h}ff"  # 6 位 → 不透明


def _is_opaque_rrggbbaa(hex_rgba: str) -> bool:
    h = hex_rgba.strip().lstrip("#").lower()
    return len(h) == 8 and h[6:8] == "ff"


def _preset_is_opaque(contract: Dict, preset_name: str) -> bool:
    """登记预设是否「不透明场景渐变」（L1155-1160：weather/rainy-weather/sports-health/sleep）。"""
    spec = (contract.get("gradients") or {}).get(preset_name) or {}
    stops = spec.get("stops") or []
    return bool(stops) and all(_is_opaque_rrggbbaa(c) for _, c in stops)


def _implicit_foreground(card: GenuiCard, contract: Dict) -> Tuple[str, str]:
    """A2-①：未声明 fontColor 的隐式前景 + 假设说明。"""
    root = card.find_component("root")
    ginfo = _card_gradient(root) if root else None
    if ginfo is None:
        return IMPLICIT_FG_LIGHT, "浅色基底深色默认（colors.font_primary，DESIGN.md L12）"
    card_colors = _normalize_colors_from_dsl(ginfo[2])
    matched = _match_preset(contract, card_colors) if contract.get("gradients") else None
    base = matched.split("#", 1)[0] if matched else None
    if base is not None:
        if _preset_is_opaque(contract, base):
            return IMPLICIT_FG_OPAQUE, "不透明场景渐变反色前景（DESIGN.md L1184）"
        # 浅色遮罩预设（含 opaqueEquivalent 烘焙变体）→ 深色默认
        return IMPLICIT_FG_LIGHT, "浅色遮罩底深色默认（colors.font_primary）"
    # 未命中登记预设：按 stops 不透明度兜底（全不透明 → 反色条款；否则浅色默认）
    if card_colors and all(_is_opaque_rrggbbaa(c) for c in card_colors):
        return IMPLICIT_FG_OPAQUE, "不透明渐变反色前景（DESIGN.md L1184，未注册预设兜底）"
    return IMPLICIT_FG_LIGHT, "浅色底深色默认（colors.font_primary）"


def _fg_subject(fg_note: Optional[str], fg: str) -> str:
    if fg_note is None:
        return "fontColor"
    return f"未声明 fontColor（隐式前景假设 {fg}，{fg_note}）"


@register("VISUAL.CONTRAST")
def check_contrast(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    findings: List[Finding] = []
    index = _comp_index(card)
    parents = _parent_map(index)
    for comp in card.iter_components():
        if comp.get("component") != "Text":
            continue
        cid = comp.get("id")
        if not cid:
            continue
        content = comp.get("content")
        if content is None or str(content).strip() == "":
            continue  # A2-③ 空白内容装饰性 surface 无字形，不判对比度
        styles = comp.get("styles") or {}
        fg: Optional[str] = None
        fg_note: Optional[str] = None
        declared = next((styles[k] for k in _FG_KEYS if k in styles), None)
        if declared is None:
            fg, fg_note = _implicit_foreground(card, contract)  # A2-①
        elif isinstance(declared, str) and _looks_like_token(declared):
            expanded = _expand_token(declared, _COLOR_PROFILE)  # A2-②
            if expanded is None:
                findings.append(
                    make(
                        card, "VISUAL.CONTRAST",
                        f"fontColor 为 token 写法 {declared}，无法展开为登记 hex，对比度无法判定",
                        cid, severity=P2, evidence_type=DEVICE,
                        expected="fontColor 展开为登记色（color_profile）后 ≥3:1（需端侧确认渲染色）",
                        actual=f"{declared}（不在 validators/data/color_profile.json）",
                        fix_hint="改用登记 token（colors./themes.dark. 前缀）或直接写 hex",
                    )
                )
                continue
            fg = _rrggbbaa_to_argb(expanded)
            fg_note = f"token 展开 {declared} → {expanded}"
        elif isinstance(declared, str):
            fg = declared
        else:
            continue  # 非字符串声明无法解析，不臆报
        try:
            info = text_background_stack(card, cid)
            env = envelope_evaluate(fg, info)
        except ValueError:
            continue  # 解析不了的色不臆报
        worst = env["worst_case"]
        subject = _fg_subject(fg_note, fg)
        hint = (
            f"加深前景或换用对比更强的登记色（最不利背景合成色 {worst['blended_bg']}，"
            f"前景合成后 {worst['blended_fg']}；可用 scripts/contrast_calc.py 复算）"
        )
        actual_prefix = f"{fg} on {env['assumption']} 背景"
        if env["verdict"] == "fail":
            anc = _nearest_clickable_ancestor(comp, parents)
            in_button = anc is not None and _is_button_like(anc, parents)
            if in_button:
                # 2026-08-24 裁决：按钮子树内配色由 button_color_rules 登记形态管辖，
                # 对比度不足降为 P2 提醒
                findings.append(
                    make(
                        card, "VISUAL.CONTRAST",
                        f"{subject} 对比度 {env['ratio_min']:.1f}~{env['ratio_max']:.1f}:1，"
                        f"所有渐变位置均 <3:1（按钮子树：配色由 button_color_rules 登记形态管辖，"
                        f"降为提醒）",
                        cid, severity=P2, evidence_type=PROGRAM,
                        expected="按钮形态配对色（button_color_rules）",
                        actual=f"{actual_prefix}，ratio {env['ratio_min']}~{env['ratio_max']}"
                               + (f"；{fg_note}" if fg_note else ""),
                        fix_hint=hint + "；按钮配色以 button_color_rules 登记形态为准",
                    )
                )
            else:
                findings.append(
                    make(
                        card, "VISUAL.CONTRAST",
                        f"{subject} 对比度 {env['ratio_min']:.1f}~{env['ratio_max']:.1f}:1，"
                        f"所有渐变位置均 <3:1",
                        cid, severity=P1, evidence_type=PROGRAM,
                        expected="≥3:1（DESIGN.md《对比度》强制）",
                        actual=f"{actual_prefix}，ratio {env['ratio_min']}~{env['ratio_max']}"
                               + (f"；{fg_note}" if fg_note else ""),
                        fix_hint=hint,
                    )
                )
        elif env["verdict"] == "uncertain":
            findings.append(
                make(
                    card, "VISUAL.CONTRAST",
                    f"{subject} 对比度跨 3:1 门槛（{env['ratio_min']:.1f}~{env['ratio_max']:.1f}:1），"
                    f"取决于文字在渐变上的实际位置",
                    cid, severity=P2, evidence_type=DEVICE,
                    expected="≥3:1（位置相关）",
                    actual=f"{actual_prefix}，ratio {env['ratio_min']}~{env['ratio_max']}"
                           + (f"；{fg_note}" if fg_note else ""),
                    fix_hint=hint + "；或以端侧渲染确认实际位置",
                )
            )
        elif env["verdict"] == "pass-suggest":
            findings.append(
                make(
                    card, "VISUAL.CONTRAST",
                    f"{subject} 对比度 {env['ratio_min']:.1f}:1 过 3:1 强制档，建议 ≥4.5:1",
                    cid, severity=P2, evidence_type=PROGRAM,
                    expected="≥4.5:1（建议级，WCAG AA 对齐）",
                    actual=f"{fg}，ratio {env['ratio_min']}"
                           + (f"；{fg_note}" if fg_note else ""),
                    fix_hint=hint,
                )
            )
    return findings
