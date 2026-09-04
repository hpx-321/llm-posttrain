"""CATALOG.* —— 禁用组件/属性兜底（F4，DESIGN.md component-catalog 镜像）。

背景（F4 缺口）：DSL 出现 DESIGN.md component-catalog 之外的组件名、或组件 styles
里出现该组件契约之外的属性键，此前无任何规则拦截。本模块补齐两条：

- CATALOG.COMPONENT_UNREGISTERED（P1，程序已证实）：组件名不在契约登记集；
- CATALOG.STYLE_KEY_UNREGISTERED（P2，程序已证实）：styles 键不在该组件契约属性集。

契约集来源（本模块内派生常量，不改 design_contract.py）：

1. DESIGN.md front-matter `components:` 契约登记集（L1055-1121）：button-primary /
   button-primary-pressed / button-secondary / button-icon-2x2 / card-root /
   list-row / progress-ring-label；
2. A2UI extended 原始组件命名空间（Text/Column/Row/Stack/Image/Progress/Button/Divider）：
   DESIGN.md 未枚举 genui 组件命名空间，按语料实证放行（93 条语料
   「卡片8-4-v12-93条-…-v18-20260807」+ 第一次评测 299 个 DSL 文件全覆盖），
   待规范补条目；
3. 各组件 styles 键契约 = 上述两个语料的每组件并集（同上实证依据），
   radialGradient 例外按规范放行（见 _GRADIENT_KEYS 注释）；
   语义组件（button-* 等）的属性键按 DESIGN.md 对应契约块（L1056-1121）放行。

判定口径：
- 组件名非字符串、styles 非 dict 时跳过（由其它结构性规则负责）；
- 组件未登记时不再单独判 styles 键（COMPONENT_UNREGISTERED 已覆盖该组件）；
- styles 键只查键名一层，不深入嵌套值（margin/linearGradient 等值的内部结构
  由对应专项规则负责）。
"""
from __future__ import annotations

from typing import Dict, List

from validators.dsl import GenuiCard
from validators.finding import Finding, P1, P2
from validators.rules import register
from validators.rules._common import make

#: DESIGN.md front-matter components 契约登记集（L1055-1121）
DESIGN_COMPONENTS = frozenset((
    "button-primary",          # L1056-1066
    "button-primary-pressed",  # L1067-1077
    "button-secondary",        # L1078-1088
    "button-icon-2x2",         # L1089-1104
    "card-root",               # L1105-1113
    "list-row",                # L1114-1117
    "progress-ring-label",     # L1118-1121
))

#: A2UI extended 原始组件（语料实证：93 条语料 + 第一次评测 299 DSL 全覆盖；
#: DESIGN.md 未枚举 genui 组件命名空间，按语料实证放行，待规范补条目）
CORPUS_COMPONENTS = frozenset((
    "Text", "Column", "Row", "Stack", "Image", "Progress", "Button", "Divider",
))

COMPONENT_LEGAL = DESIGN_COMPONENTS | CORPUS_COMPONENTS

#: 渐变键：linearGradient 语料实证；radialGradient 按规范放行——
#: DESIGN.md weather 预设为径向渐变（L1178），且既有 GRADIENT 规则契约同时读取
#: linearGradient/radialGradient（validators/rules/gradient.py L15-19）；
#: E-24 真实天气卡镜像（root 用 radialGradient）为可渲染实证。
_GRADIENT_KEYS = frozenset(("linearGradient", "radialGradient"))

#: 原始组件 styles 键契约（语料实证并集，依据同上 CORPUS_COMPONENTS 注释；
#: 可承载背景渐变的容器组件并入渐变键）
CORPUS_STYLE_KEYS = {
    "Text": frozenset((
        "width", "height", "margin", "fontSize", "fontWeight", "fontColor",
        "maxLines", "textAlign", "textOverflow", "borderRadius", "alignContent",
        "backgroundColor", "flexShrink", "maxFontSize", "minFontSize", "padding",
        "constraintSize", "layoutWeight",
    )),
    "Column": frozenset((
        "width", "height", "margin", "padding", "borderRadius", "clip",
        "backgroundColor", "alignItems", "justifyContent", "flexShrink",
        "layoutWeight", "borderWidth", "borderColor", "constraintSize", "shadow",
    )) | _GRADIENT_KEYS,
    "Row": frozenset((
        "width", "height", "margin", "alignItems", "justifyContent", "flexShrink",
        "layoutWeight", "borderRadius", "backgroundColor", "padding", "clip",
        "borderWidth", "borderColor", "constraintSize",
    )) | _GRADIENT_KEYS,
    "Stack": frozenset((
        "width", "height", "margin", "alignContent", "borderRadius", "padding",
        "backgroundColor", "flexShrink", "clip", "constraintSize", "layoutWeight",
        "borderWidth", "borderColor",
    )) | _GRADIENT_KEYS,
    "Image": frozenset((
        "width", "height", "margin", "objectFit", "fillColor", "flexShrink",
        "borderRadius", "layoutWeight",
    )),
    "Progress": frozenset((
        "width", "height", "margin", "type", "color", "backgroundColor",
        "strokeWidth", "borderRadius", "flexShrink", "layoutWeight",
    )),
    "Button": frozenset((
        "width", "height", "margin", "padding", "fontSize", "fontWeight",
        "fontColor", "backgroundColor", "borderRadius", "flexShrink",
        "borderWidth", "borderColor", "layoutWeight", "maxFontSize",
        "minFontSize", "maxLines",
    )),
    "Divider": frozenset((
        "width", "height", "strokeWidth", "vertical", "color", "layoutWeight",
    )),
}

#: 语义组件 styles 键契约（DESIGN.md 对应契约块，行号见 DESIGN_COMPONENTS 注释；
#: 这些键在规范中是组件顶层属性，DSL 侧如写入 styles 同样放行）
_SEMANTIC_STYLE_KEYS = {
    "button-primary": frozenset((
        "backgroundColor", "textColor", "gradientBackgroundOverride", "typography",
        "typographyFallback", "fallbackWhen", "rounded", "padding", "gap",
        "contentAlign", "height",
    )),
    "button-primary-pressed": frozenset((
        "backgroundColor", "textColor", "gradientBackgroundOverride", "typography",
        "typographyFallback", "fallbackWhen", "rounded", "padding", "gap",
        "contentAlign", "height",
    )),
    "button-secondary": frozenset((
        "backgroundColor", "textColor", "gradientBackgroundOverride", "typography",
        "typographyFallback", "fallbackWhen", "rounded", "padding", "gap",
        "contentAlign", "height",
    )),
    "button-icon-2x2": frozenset((
        "size", "iconSize", "placement", "contentAlign", "rounded",
        "minimumHotZone", "backgroundColor", "iconColor",
        "gradientBackgroundOverride", "requiredAttribute", "iconSource",
        "visibleText", "accessibleName", "hotZoneExtension",
    )),
    "card-root": frozenset(("background", "rounded", "padding")),
    "list-row": frozenset(("typography", "height", "padding")),
    "progress-ring-label": frozenset(("typography", "textColor")),
}

STYLE_KEYS: Dict[str, frozenset] = {**CORPUS_STYLE_KEYS, **_SEMANTIC_STYLE_KEYS}


@register("CATALOG.COMPONENT_UNREGISTERED")
def check_component_registered(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """F4a：组件名必须在契约登记集内（DESIGN.md components L1055-1121 + 语料实证原始组件）。"""
    findings: List[Finding] = []
    for comp in card.iter_components():
        name = comp.get("component")
        if not isinstance(name, str) or not name:
            continue
        if name in COMPONENT_LEGAL:
            continue
        findings.append(
            make(
                card, "CATALOG.COMPONENT_UNREGISTERED",
                f"组件 {name!r} 不在组件契约登记集内",
                comp.get("id"), severity=P1,
                expected="component ∈ DESIGN.md components 契约登记集（L1055-1121）+ A2UI 语料实证原始组件",
                actual=f"component={name!r}",
                fix_hint="改用契约登记组件（Column/Row/Stack/Text/Image/Progress/Button/Divider），"
                         "或在 DESIGN.md 补登记后放行",
            )
        )
    return findings


@register("CATALOG.STYLE_KEY_UNREGISTERED")
def check_style_key_registered(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """F4b：组件 styles 键必须在对应组件契约属性集内（P2 建议级兜底）。"""
    findings: List[Finding] = []
    for comp in card.iter_components():
        name = comp.get("component")
        if not isinstance(name, str):
            continue
        styles = comp.get("styles")
        if not isinstance(styles, dict):
            continue
        legal = STYLE_KEYS.get(name)
        if legal is None:
            continue  # 组件未登记由 COMPONENT_UNREGISTERED 负责
        for key in styles:
            if not isinstance(key, str) or key in legal:
                continue
            findings.append(
                make(
                    card, "CATALOG.STYLE_KEY_UNREGISTERED",
                    f"{name} styles 出现契约外属性 {key!r}",
                    comp.get("id"), severity=P2,
                    expected=f"styles 键 ∈ {name} 契约属性集",
                    actual=f"styles.{key}",
                    fix_hint=f"删除或改用 {name} 契约内属性键；确需新增时先补 DESIGN.md 契约条目",
                )
            )
    return findings
