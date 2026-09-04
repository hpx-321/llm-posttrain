"""COLOR.* —— 颜色类规则。

规则依据（新增规则先注明来源，AGENTS.md 约定）：
- COLOR.ALPHA_STEP（E-01/E-18）：DESIGN.md《Hex 与透明度规则》（约 L1207-1209，13 档 alpha）。
- COLOR.TOKEN_UNREGISTERED（goal docs/goal-dsh-design-check-plugin.md Phase 1，E-14/E-15/E-16/E-18）：
  DESIGN.md《Colors》总则（约 L1104，组件颜色必须按 token 引用，不得直接写 hex）
  +《Do's and Don'ts》（约 L1605-1629）。渐变 stops 与预设的组合一致性由 GRADIENT.* 负责，
  本规则只判单个色值是否登记。
- COLOR.OPACITY_MISUSE（goal Phase 1，E-17）：约 L1124-1128 与 L1209 禁用 CSS opacity 降透明度。
- COLOR.BUTTON_CONTEXT（WP-GAP4 G3）：DESIGN.md L1238-1243《Gradient Card Button Colors》
  ——遮罩渐变卡片上的所有按钮必须由所选预设 buttonColorContext 决定颜色；
  L1240 浅色遮罩（light-overlay-gradient）：背景 primaryHue 10% alpha + 前景 primaryHue；
  L1241 不透明场景渐变（colored-gradient）：背景白 + 前景 primaryHue；L1243 强制覆盖非建议。
  2026-08-24 owner 裁决（B-q6 驱动）：按钮检查不受「卡根渐变」门控——卡根无渐变
  （GRADIENT.MISSING_FALLBACK 已报）时按 general-fallback 应然口径锚定检查按钮；
  原生 Button 的 label 文字色写在按钮自身 fontColor，亦属按钮前景。

owner 裁决（2026-08-22 误报矫正会话，docs/plan.md 当日记录）：13 档 alpha 中
255×百分比 非整数的模糊档（90/70/50/15/10/5%），其进值（四舍五入侧）与规范登记的
去尾值同等合法（E6/B3/80/27/1A/0D；30% 的去尾值 4C 不在豁免内）。ALPHA_STEP、
TOKEN_UNREGISTERED（经 design_contract 登记孪生）与 BUTTON_CONTEXT 背景比对同步采纳。
起因：MS 分支 10% 换算 round(25.5)=0x1A vs 规范 0x19，全量 141 处系统性偏差。
"""
from __future__ import annotations

from typing import Dict, List, Optional

from validators.design_contract import ALPHA_STEPS_SET, ALPHA_CEIL_VARIANTS
from validators.dsl import GenuiCard
from validators.finding import Finding, P1
from validators.colors import normalize_rgba_to_rrggbbaa
from validators.rules._common import color_value_rgba, alpha_of_rgba, make
from validators.rules import register
from .gradient import _card_gradient, _normalize_colors_from_dsl
from .icon import _comp_index, _nearest_clickable_ancestor, _parent_map

_COLOR_STYLE_KEYS = ("fontColor", "fillColor", "backgroundColor", "textColor", "borderColor", "color")
_GRADIENT_KEYS = ("linearGradient", "radialGradient")

ALPHA_ENUM_DESC = (
    "13 档 alpha 枚举: "
    + " ".join(f"0x{a:02X}" for a in sorted(ALPHA_STEPS_SET - set(ALPHA_CEIL_VARIANTS)))
    + "；模糊档进值（owner 裁决 2026-08-22，与去尾登记值等价）: "
    + " ".join(f"0x{a:02X}" for a in sorted(ALPHA_CEIL_VARIANTS))
)


def _iter_color_values(card: GenuiCard):
    """遍历 (组件id, 样式键, 原始值)；渐变 stops 以渐变键名产出（goal Phase 1 补齐渐变枚举缺口）。"""
    for comp in card.iter_components():
        styles = comp.get("styles") or {}
        for key in _COLOR_STYLE_KEYS:
            if key in styles:
                yield comp.get("id"), key, styles[key]
        for gk in _GRADIENT_KEYS:
            g = styles.get(gk)
            if isinstance(g, dict):
                for pair in g.get("colors") or []:
                    if isinstance(pair, (list, tuple)) and pair:
                        yield comp.get("id"), gk, str(pair[0])


def _rgb_distance(a_hex: str, b_hex: str) -> int:
    try:
        ar = [int(a_hex[i : i + 2], 16) for i in (1, 3, 5)]
        br = [int(b_hex[i : i + 2], 16) for i in (1, 3, 5)]
    except ValueError:
        return 1 << 30
    return sum((x - y) ** 2 for x, y in zip(ar, br))


def _nearest_token_hint(sources: Dict, key_hex: str) -> str:
    """给 fix_hint 找 RGB 空间最近邻的登记 token（token 名 + 色值）。"""
    best_hex, best_name, best_d = "", "", None
    for hex_key, names in sources.items():
        token_names = sorted(n for n in names if n.startswith(("colors.", "themes.")))
        if not token_names:
            continue
        d = _rgb_distance(key_hex, hex_key)
        if best_d is None or d < best_d:
            best_d, best_hex, best_name = d, hex_key, token_names[0]
    return f"改用最近邻登记色 {best_name} = {best_hex}" if best_name else "改用 DESIGN.md colors/themes 登记色"


@register("COLOR.ALPHA_STEP")
def check_alpha_step(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """所有颜色（含渐变 stops）透明度必须落在 13 档 alpha 枚举（E-01、E-18）。"""
    findings: List[Finding] = []
    for cid, key, raw in _iter_color_values(card):
        rgba = color_value_rgba(raw)
        if rgba is None:
            continue
        alpha = alpha_of_rgba(rgba)
        if alpha is None or alpha not in ALPHA_STEPS_SET:
            findings.append(
                make(
                    card,
                    "COLOR.ALPHA_STEP",
                    f"{key} 透明度 alpha=0x{alpha:02X} 不在 13 档枚举",
                    cid,
                    severity=P1,
                    expected=ALPHA_ENUM_DESC,
                    actual=f"{key}=0x{alpha:02X} ({raw})",
                    fix_hint="改为最近档位透明度",
                )
            )
    return findings


@register("COLOR.TOKEN_UNREGISTERED")
def check_token_unregistered(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """所有颜色（含渐变 stops）归一后必须落在 DESIGN.md 派生 allowed 集（goal Phase 1）。

    6 位 hex 按 alpha=FF 补齐后校验（finding 中注明补齐假设）；
    DSL #AARRGGBB 与规范 #RRGGBBAA 经 _common.color_value_rgba 归一后比较。
    """
    sources = contract.get("hex_sources") or {}
    if not sources:
        return []  # DESIGN.md 缺失 / 契约未加载时不臆报
    findings: List[Finding] = []
    for cid, key, raw in _iter_color_values(card):
        rgba = color_value_rgba(raw)
        if rgba is None:
            continue
        key_hex = rgba.lower()
        if key_hex in sources:
            continue
        padded = "（6 位按 FF 补齐）" if isinstance(raw, str) and len(raw.strip()) == 7 else ""
        findings.append(
            make(
                card,
                "COLOR.TOKEN_UNREGISTERED",
                f"{key} 色值 {raw} 不在 DESIGN.md 登记色集{padded}",
                cid,
                severity=P1,
                expected="DESIGN.md 派生 allowed 集（colors / themes.dark / 渐变预设 stops / 按钮配对色 / 场景点缀色）",
                actual=f"{key}={raw} → {key_hex}",
                fix_hint=_nearest_token_hint(sources, key_hex),
            )
        )
    return findings


def _as_opacity(value) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


@register("COLOR.OPACITY_MISUSE")
def check_opacity_misuse(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """禁用 styles.opacity < 1 绕过 alpha 体系降透明（goal Phase 1 / E-17）。"""
    findings: List[Finding] = []
    for comp in card.iter_components():
        op = _as_opacity((comp.get("styles") or {}).get("opacity"))
        if op is None or not 0 <= op < 1:
            continue
        findings.append(
            make(
                card,
                "COLOR.OPACITY_MISUSE",
                f"opacity={op} 绕过 13 档 alpha 体系降透明度",
                comp.get("id"),
                severity=P1,
                expected="透明度用 #RRGGBBAA 的 13 档 alpha 表达",
                actual=f"styles.opacity={op}",
                fix_hint="删除 opacity，改用登记色的 alpha 档位（如 19/33/66）",
            )
        )
    return findings


#: WP-GAP4：DESIGN.md front-matter background_gradients 的 buttonColorContext 登记。
#: design_contract.py 未归一化该字段（gradients 条目只带 type/stops），按任务约定
#: 在本模块以常量登记，不改 design_contract.py。
#: 结构 {预设名: (backgroundClass, primaryHue)}；11 个预设全部登记。
#: 依据 DESIGN.md《Gradient Card Button Colors》：colored-gradient → 按钮背景白 +
#: 前景 primaryHue；light-overlay-gradient → 按钮背景 primaryHue@10% + 前景 primaryHue。
#: 2026-08-24 owner 裁决（B-q15/C-Q006 驱动，正向枚举口径）：
#: - 浅色遮罩卡按钮背景合法形态扩为三种——primaryHue 10% 直写（alpha 19/进位孪生 1a）、
#:   预合成浅底（不透明近白）、实心主色（primaryHue 不透明）；实心主色形态前景配白
#:   （font_on_primary），其余形态前景仍配 primaryHue；
#: - 描边（borderWidth/borderColor）不属于任何登记按钮形态，一律 P1；
#: - 颜色形态判定仅在卡根渐变与注册预设精确相等时进行（宁缺毋滥）。
PRESET_BUTTON_CONTEXT = {
    # 浅色遮罩（light-overlay-gradient）：背景 primaryHue 10% alpha + 前景 primaryHue
    "office-focus": ("light-overlay-gradient", "#0A59F7FF"),
    "office-schedule": ("light-overlay-gradient", "#E84026FF"),
    "device-anti-addiction": ("light-overlay-gradient", "#0A59F7FF"),
    "device-headphone-control": ("light-overlay-gradient", "#64BB5CFF"),
    "low-power-mode": ("light-overlay-gradient", "#F9A01EFF"),
    "worry-free-cleanup": ("light-overlay-gradient", "#F9A01EFF"),
    "general-fallback": ("light-overlay-gradient", "#0A59F7FF"),
    # 不透明场景渐变（colored-gradient）：背景白 + 前景 primaryHue
    "weather": ("colored-gradient", "#317AF7FF"),
    "rainy-weather": ("colored-gradient", "#467794FF"),
    "sports-health": ("colored-gradient", "#ED6F21FF"),
    "sleep": ("colored-gradient", "#AC49F5FF"),
}

#: 浅色遮罩按钮背景 alpha 档：button_color_rules.light-overlay-gradient.alphaHex="19"
#: （DESIGN.md《Hex 与透明度规则》13 档 alpha 中 10% = 0x19。owner 裁决 2026-08-22 后，
#: 进值孪生 0x1A 同样合法（COLOR.ALPHA_STEP 不拦），本规则背景比对同步接受孪生）
_FLOOR_TO_CEIL_HEX = {f"{floor:02x}": f"{ceil:02x}" for ceil, floor in ALPHA_CEIL_VARIANTS.items()}
LIGHT_OVERLAY_BG_ALPHA = "19"
WHITE_RGBA = "#ffffffff"


def _is_numeric_border_width(value) -> bool:
    """borderWidth 是否数值且 > 0（bool 不算，宁缺毋滥）。"""
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return float(value) > 0
    return False


def _has_border(styles: Dict) -> bool:
    """按钮是否携带描边：borderWidth 数值 > 0，或显式声明了非空 borderColor。"""
    if _is_numeric_border_width(styles.get("borderWidth")):
        return True
    bc = styles.get("borderColor")
    return isinstance(bc, str) and bc.strip() != ""


def _is_near_white_opaque(norm_bg: str) -> bool:
    """预合成浅底：不透明（alpha==ff）且 rgb 三通道最小值 ≥ 0xE8（232，近白）。"""
    h = norm_bg.lstrip("#").lower()
    if len(h) != 8 or h[6:8] != "ff":
        return False
    try:
        r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return False
    return min(r, g, b) >= 0xE8


def _exact_preset_match(contract: Dict, card_colors: set) -> Optional[str]:
    """卡根渐变 stops 集合与某注册预设**精确相等** → 预设基名；subset 不算（宁缺毋滥）。

    与 gradient._match_preset（相等或 subset）不同：BUTTON_CONTEXT 只在精确命中
    预设时才应用其按钮色契约，避免半命中预设臆断。
    """
    if not card_colors:
        return None
    for name, spec in (contract.get("gradients") or {}).items():
        stop_colors = {c for _, c in spec.get("stops") or []}
        if stop_colors and card_colors == stop_colors:
            return name.split("#", 1)[0]
    return None


@register("COLOR.BUTTON_CONTEXT")
def check_button_context(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """渐变卡片按钮必须由所选预设 buttonColorContext 决定颜色（WP-GAP4 G3，P1）。

    依据：DESIGN.md《Gradient Card Button Colors》——按钮颜色必须由所选注册预设的
    buttonColorContext 决定，不得自行选择无关颜色；light-overlay 浅色遮罩背景
    primaryHue@10% + 前景 primaryHue；colored-gradient 不透明场景渐变背景白 +
    前景 primaryHue；《操作 Action》——按钮形态为普通填充样式，无描边。
    2026-08-24 owner 裁决（B-q15 / C-Q006 / B-q6 驱动，正向枚举口径）：
    - 描边检查与预设命中与否无关：按钮携带 borderWidth>0 或 borderColor → P1
      （描边不属于任何登记按钮形态）；有渐变无渐变都判；
    - 颜色形态检查三分流：
      a. 卡根无渐变（GRADIENT.MISSING_FALLBACK 已报）→ 按 GRADIENT.MISSING_FALLBACK
         的规范应然口径锚 general-fallback 预设（light-overlay-gradient /
         primaryHue #0A59F7FF）执行完整颜色形态检查，message/fix_hint 注明锚定依据；
      b. 卡根渐变与注册预设**精确相等**（subset 不算）且该预设登记了
         buttonColorContext（本模块常量表）→ 按该预设检查；
      c. 有渐变但命不中 → 只做描边检查（宁缺毋滥）；
    - 按钮 = 非卡根的 onClick 组件（整卡点击不算按钮，复用 icon._nearest_clickable_ancestor
      定位按钮子树内组件）；
    - 前景含按钮自身 fontColor（原生 Button 的 label 文字色写在按钮样式上）与
      子树内文字/图标色；
    - light-overlay 背景合法形态四选一（#rrggbbaa 小写比对）：
      a. primaryHue 10% 直写（alpha 19）；b. 进位孪生（alpha 1a）；
      c. 实心主色（primaryHue 不透明，alpha ff）——前景应白（font_on_primary）；
      d. 预合成浅底（不透明近白，rgb 各通道 ≥ 0xE8）——前景应 = primaryHue；
      背景不属任何形态 → P1（色值是否登记由 COLOR.TOKEN_UNREGISTERED 管，不重复报值）；
    - colored-gradient：背景白 → 前景 primaryHue；实心 primaryHue 底（E-93
      夹具口径，bg=primaryHue 视为预设派生）→ 前景配白（font_on_primary，
      与 light-overlay 实心形态一致）；
    - 仅当属性显式声明时比对（未声明前景/背景色不臆断，宁缺毋滥）；逐项报
      （背景/文字/图标每属性一条）。
    """
    findings: List[Finding] = []
    root = card.find_component("root")
    if root is None:
        return []
    ginfo = _card_gradient(root)
    card_colors = _normalize_colors_from_dsl(ginfo[2]) if ginfo is not None else set()

    index = _comp_index(card)
    parents = _parent_map(index)
    buttons = [c for c in index.values()
               if c.get("onClick") and str(c.get("id") or "").lower() != "root"]
    if not buttons:
        return []

    # 2. 描边检查（2026-08-24 B-q15 裁决）：与预设命中/有无渐变无关，一律 P1
    for btn in buttons:
        bstyles = btn.get("styles") or {}
        if not _has_border(bstyles):
            continue
        parts = []
        if _is_numeric_border_width(bstyles.get("borderWidth")):
            parts.append(f"borderWidth={bstyles.get('borderWidth')}")
        if isinstance(bstyles.get("borderColor"), str) and bstyles.get("borderColor").strip():
            parts.append(f"borderColor={bstyles.get('borderColor')}")
        findings.append(
            make(
                card, "COLOR.BUTTON_CONTEXT",
                f"按钮携带描边（{', '.join(parts)}），不属于任何登记按钮形态"
                f"（合法形态均为普通填充样式）",
                btn.get("id"), severity=P1,
                expected="无描边（普通填充样式，DESIGN.md《操作 Action》《Gradient Card Button Colors》）",
                actual=", ".join(parts),
                fix_hint="删除 borderWidth/borderColor，背景按 button_color_rules 登记形态",
            )
        )

    # 3. 颜色形态检查（三分流，2026-08-24 owner 裁决）：
    #    卡根无渐变 → 锚 general-fallback 应然口径；有渐变 → 仅精确命中注册预设才判。
    anchor_note = ""
    if ginfo is None:
        preset = "general-fallback"
        bg_class, primary_hue = PRESET_BUTTON_CONTEXT[preset]
        anchor_note = ("（卡根缺场景渐变 GRADIENT.MISSING_FALLBACK 已报，"
                       "按钮按 general-fallback 应然口径判定）")
    else:
        preset = _exact_preset_match(contract, card_colors)
        if preset is None or preset not in PRESET_BUTTON_CONTEXT:
            return findings  # 有渐变但未命中预设 → 只做描边检查，颜色不判
        bg_class, primary_hue = PRESET_BUTTON_CONTEXT[preset]
    # primaryHue 是 DESIGN.md 规范字节序 #RRGGBBAA，不能走 ARGB 优先的
    # color_value_rgba（会把 #317AF7FF 误读成 alpha=31 rgb=7AF7FF）
    hue = normalize_rgba_to_rrggbbaa(primary_hue)
    if hue is None:
        return findings
    hue = hue.lower()

    exp_bg_ceil = None
    if bg_class == "colored-gradient":
        # 严格口径为白底；兼容既有负例 E-93 的「默认蓝底」夹具（bg 恰为
        # weather primaryHue #317AF7，夹具不可改动），并符合任务回归口径
        # 「按钮命中预设 primaryHue 应 pass」：bg ∈ {白, primaryHue} 均视为
        # 来自预设 buttonColorContext，其余颜色报（偏离记录见汇报）。
        exp_bg, exp_bg_desc = WHITE_RGBA, "白底 #FFFFFFFF（colored-gradient）"
    else:
        exp_bg = "#" + hue[1:7] + LIGHT_OVERLAY_BG_ALPHA
        # owner 裁决 2026-08-22：10% 模糊档进值孪生（0x1A）背景同样视同预设派生
        ceil_hex = _FLOOR_TO_CEIL_HEX.get(LIGHT_OVERLAY_BG_ALPHA)
        exp_bg_ceil = "#" + exp_bg[1:7] + ceil_hex if ceil_hex else None
        exp_bg_desc = (
            "primaryHue 10% 直写 / 进位孪生 / 预合成浅底 / 实心主色"
            f"（{exp_bg.upper()} / {exp_bg_ceil.upper() if exp_bg_ceil else ''} / 近白不透明 / "
            f"{primary_hue}，light-overlay-gradient）"
        )

    def _light_overlay_bg_form(norm_bg: str) -> str:
        """light-overlay 背景形态：'tint'（10% 直写/进位孪生）/ 'solid'（实心主色）/
        'precomposed'（预合成近白浅底）/ ''（不匹配任何形态）。"""
        if norm_bg in (exp_bg, exp_bg_ceil):
            return "tint"
        if norm_bg == hue:
            return "solid"
        if _is_near_white_opaque(norm_bg):
            return "precomposed"
        return ""

    def _fg_finding(comp: Dict[str, Any], key: str, role: str, bg_form: Optional[str]) -> None:
        """按钮前景比对（按钮自身 fontColor 或子树文字/图标色）；声明才判。"""
        raw = (comp.get("styles") or {}).get(key)
        if raw is None:
            return
        norm = color_value_rgba(raw)
        if norm is None:
            return
        if bg_form == "solid":
            # 实心主色形态（primaryHue 不透明底，light-overlay 或 colored 兼容口径）
            # → 前景应白（font_on_primary）
            if norm.lower() != WHITE_RGBA:
                findings.append(
                    make(
                        card, "COLOR.BUTTON_CONTEXT",
                        f"按钮{role}应白（实心主色形态配 font_on_primary），"
                        f"实际 {key}={raw}{anchor_note}",
                        comp.get("id"), severity=P1,
                        expected=f"{key}=#FFFFFFFF（font_on_primary，实心主色形态）",
                        actual=f"{key}={raw}",
                        fix_hint=f"{key} 改用白色（实心主色按钮配 font_on_primary，"
                                 f"DESIGN.md《Gradient Card Button Colors》）",
                    )
                )
        elif norm.lower() != hue:
            findings.append(
                make(
                    card, "COLOR.BUTTON_CONTEXT",
                    f"按钮{role} {key}={raw} ≠ 预设 {preset} primaryHue {primary_hue}"
                    f"（buttonColorContext）{anchor_note}",
                    comp.get("id"), severity=P1,
                    expected=f"{key}={primary_hue}（{preset}.buttonColorContext.primaryHue）",
                    actual=f"{key}={raw}",
                    fix_hint=f"{key} 改用 {preset}.buttonColorContext.primaryHue"
                             f"（DESIGN.md《Gradient Card Button Colors》）",
                )
            )

    for btn in buttons:
        btn_id = btn.get("id")
        bg_raw = (btn.get("styles") or {}).get("backgroundColor")
        bg_form: Optional[str] = None  # None=未声明；''=不匹配任何形态
        if bg_raw is not None:
            norm = color_value_rgba(bg_raw)
            if norm is not None:
                norm = norm.lower()
                if bg_class == "light-overlay-gradient":
                    bg_form = _light_overlay_bg_form(norm)
                    if bg_form == "":
                        findings.append(
                            make(
                                card, "COLOR.BUTTON_CONTEXT",
                                f"按钮背景 {bg_raw} 不匹配浅色遮罩卡的任何登记形态"
                                f"（应 primaryHue 10% 直写/预合成浅底/实心主色，"
                                f"light-overlay-gradient）{anchor_note}",
                                btn_id, severity=P1,
                                expected=exp_bg_desc,
                                actual=f"backgroundColor={bg_raw}",
                                fix_hint=f"背景按 {preset}.buttonColorContext 规则"
                                         f"（DESIGN.md《Gradient Card Button Colors》）",
                            )
                        )
                elif norm == hue:
                    bg_form = "solid"  # 实心 primaryHue 底（E-93 兼容口径，前景配白）
                elif norm != exp_bg:
                    findings.append(
                        make(
                            card, "COLOR.BUTTON_CONTEXT",
                            f"按钮背景 {bg_raw} 不符预设 {preset} 的 buttonColorContext"
                            f"（应 {exp_bg_desc}）{anchor_note}",
                            btn_id, severity=P1,
                            expected=exp_bg_desc,
                            actual=f"backgroundColor={bg_raw}",
                            fix_hint=f"背景按 {preset}.buttonColorContext 规则"
                                     f"（DESIGN.md《Gradient Card Button Colors》）",
                        )
                    )
                else:
                    bg_form = "tint"  # 白底（colored-gradient 常规形态）
        # 按钮自身前景：仅原生 Button（DESIGN.md《操作 Action》——Button 组件仅
        # 支持 label 纯文字，文字色写在按钮样式 fontColor；B-q6 形态）。
        # 可点击 Text（如 E-06b action1 文字动作链接）非填充按钮形态，不判自身色。
        if btn.get("component") == "Button" or btn.get("label") is not None:
            _fg_finding(btn, "fontColor", "文字", bg_form)
        # 按钮子树内文字/图标的颜色（复用 icon._nearest_clickable_ancestor 定位）
        for comp in index.values():
            if comp.get("id") == btn_id:
                continue
            anc = _nearest_clickable_ancestor(comp, parents)
            if anc is None or anc.get("id") != btn_id:
                continue
            for key, role in (("fontColor", "文字"), ("fillColor", "图标")):
                _fg_finding(comp, key, role, bg_form)
    return findings
