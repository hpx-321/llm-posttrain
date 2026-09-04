"""DESIGN.md（2×2）设计契约加载（vendor 自 harmony-card-dsl-validation 并演化）。

规范金标准（2026-08-22 登记）= 工作区根 ``DESIGN.md``（2×2）+ ``DESIGN-2x4.md``（2×4），
按卡片尺寸选用；本模块归一化 ``DESIGN.md`` front-matter，2×4 侧契约（layout_slots 等）经
``config.design_2x4_spec_path()`` 消费。外层宿主仓库 ``docs/system_prompt.txt`` 不是本检查器真值。

把 DESIGN.md front-matter 归一化成检查器可用的集合/映射：
- allowed_font_sizes / allowed_hex / allowed_spacing / allowed_radius
- density（各尺寸展示密度上限）
- copy_limits（copyLimits）
- gradients（background_gradients 注册预设：stops/type/direction/angle/座标）
- alpha_steps（13 档透明度枚举，取自开发计划 §7 E-01 且与规范一致）

运行期保持「标准库 only」：PyYAML 可选，缺失时退回正则定向抽取。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Set

try:  # 可选依赖
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore

from .config import design_2x4_spec_path, design_spec_path

HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6})")  # 8 位优先：6 位优先会把 #RRGGBBAA 截成 #RRGGBB 丢 alpha

#: 13 档 alpha（开发计划 §7 E-01，DESIGN.md alpha 阶梯）
_ALPHA_STEPS_BASE = (0xFF, 0xE5, 0xCC, 0xB2, 0x99, 0x7F, 0x66, 0x4D, 0x33, 0x26, 0x19, 0x0C, 0x00)

#: owner 裁决（2026-08-22 误报矫正会话，docs/plan.md 当日记录）：13 档中
#: 255×百分比 非整数的「模糊档」（90/70/50/15/10/5%），其进值（四舍五入侧）
#: 与规范登记的去尾值同等合法。背景：MS 分支生成管线把 10% 换算为
#: round(25.5)=0x1A 而规范登记 floor(25.5)=0x19，全量 141 处系统性偏差。
#: 30% 规范本身取进值 0x4D，其去尾值 0x4C 不在裁决范围（裁决仅覆盖进值侧）。
#: DESIGN.md L1251 原文暂未同步修订，规范侧是否补记由 owner 后续定夺。
ALPHA_CEIL_VARIANTS = {
    0xE6: 0xE5,  # 90%: 255×0.9=229.5，进 0xE6 / 登记 0xE5
    0xB3: 0xB2,  # 70%: 178.5，进 0xB3 / 登记 0xB2
    0x80: 0x7F,  # 50%: 127.5，进 0x80 / 登记 0x7F
    0x27: 0x26,  # 15%: 38.25，进 0x27 / 登记 0x26
    0x1A: 0x19,  # 10%: 25.5，进 0x1A / 登记 0x19
    0x0D: 0x0C,  # 5%: 12.75，进 0x0D / 登记 0x0C
}
ALPHA_STEPS = tuple(sorted(set(_ALPHA_STEPS_BASE) | set(ALPHA_CEIL_VARIANTS)))
ALPHA_LABELS = {hex(v) for v in ALPHA_STEPS}
ALPHA_STEPS_SET = set(ALPHA_STEPS)

_CEIL_BY_FLOOR_HEX = {f"{floor:02x}": f"{ceil:02x}" for ceil, floor in ALPHA_CEIL_VARIANTS.items()}


def _expand_ceil_variant_sources(sources: Dict[str, Set[str]]) -> None:
    """登记色的模糊档进值孪生视同登记（owner 裁决 2026-08-22）。

    对每个已登记的 ``#rrggbbaa`` 值，若其 alpha 是某模糊档的去尾值（如 ``19``），
    则同基色的进值形式（``1a``）也进登记集，来源标签追加裁决标记；
    基色未登记的值不因此获得合法性（如 ``#1AE64566`` 仍报 TOKEN_UNREGISTERED）。
    """
    for value in list(sources):
        raw = value.lstrip("#").lower()
        if len(raw) == 8 and raw[6:8] in _CEIL_BY_FLOOR_HEX:
            twin = "#" + raw[:6] + _CEIL_BY_FLOOR_HEX[raw[6:8]]
            sources.setdefault(twin, set()).update(
                f"{tag}·进值孪生(裁决2026-08-22)" for tag in sources[value]
            )

_FONT_SIZE_RE = re.compile(r"fontSize:\s*(\d+)")
_RADIUS_RE = re.compile(r"corner_radius_\w+:\s*(-?\d+)")
_COPY_LIMIT_KEYS = ("titleMaxChars", "primarySentenceMaxChars", "statusLabelMaxChars", "actionLabelMaxChars")
_COPY_LIMIT_RE = re.compile(r"^\s{4}(" + "|".join(_COPY_LIMIT_KEYS) + r"):\s*(\d+)\s*$", re.MULTILINE)


def empty_contract() -> Dict[str, Any]:
    return {
        "loaded": False,
        "source": "",
        "allowed_font_sizes": set(),
        "allowed_hex": set(),
        "allowed_spacing": set(),
        "allowed_radius": set(),
        "density": {},
        "copy_limits": {},
        "gradients": {},
        "alpha_steps": ALPHA_STEPS,
        "hex_sources": {},
    }


def canonical_hex(value: str) -> str:
    """归一为小写 8 位 ``#rrggbbaa``；6 位补 ``ff`` alpha。"""
    text = value.strip().lower()
    if text.startswith("#") and len(text) == 7:
        return text + "ff"
    return text


def _vp_num(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = re.search(r"-?\d+(?:\.\d+)?", value)
        if m:
            return float(m.group(0))
    return None


def _add_hex(contract: Dict[str, Any], value: Any) -> None:
    if isinstance(value, str):
        for h in HEX_RE.findall(value):
            contract["allowed_hex"].add(canonical_hex(h))


def _split_frontmatter(text: str) -> str:
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            start = i
            break
    if start is None:
        return ""
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[start + 1 : i])
    return ""


def _normalize_gradient_stops(stops: Any) -> list:
    out = []
    if isinstance(stops, list):
        for stop in stops:
            if isinstance(stop, dict):
                color = canonical_hex(str(stop.get("color", "")))
                offset = stop.get("offset", "")
                out.append((offset, color))
            elif isinstance(stop, (list, tuple)) and len(stop) == 2:
                color = canonical_hex(str(stop[0]))
                out.append((str(stop[1]), color))
    return out


def _fill_from_yaml(contract: Dict[str, Any], data: Any) -> None:
    if not isinstance(data, dict):
        return
    colors = data.get("colors")
    if isinstance(colors, dict):
        for v in colors.values():
            _add_hex(contract, v)
    themes = data.get("themes")
    if isinstance(themes, dict):
        for theme in themes.values():
            if isinstance(theme, dict):
                for v in theme.values():
                    _add_hex(contract, v)

    typography = data.get("typography")
    if isinstance(typography, dict):
        for role in typography.values():
            if isinstance(role, dict):
                size = _vp_num(role.get("fontSize"))
                if size is not None:
                    contract["allowed_font_sizes"].add(int(size))

    rounded = data.get("rounded")
    if isinstance(rounded, dict):
        for v in rounded.values():
            radius = _vp_num(v)
            if radius is not None:
                contract["allowed_radius"].add(int(radius))

    spacing = data.get("spacing")
    if isinstance(spacing, dict):
        for v in spacing.values():
            space = _vp_num(v)
            if space is not None:
                contract["allowed_spacing"].add(int(space))

    density = data.get("density")
    if isinstance(density, dict):
        contract["density"] = {str(k): v for k, v in density.items() if isinstance(v, dict)}

    content_pruning = data.get("content_pruning")
    if isinstance(content_pruning, dict):
        cl = content_pruning.get("copyLimits")
        if isinstance(cl, dict):
            contract["copy_limits"] = {str(k): v for k, v in cl.items() if isinstance(v, (int, float))}

    gradients = data.get("background_gradients")
    if isinstance(gradients, dict):
        for name, spec in gradients.items():
            if name == "cssVariableNaming" or not isinstance(spec, dict):
                continue
            contract["gradients"][str(name)] = {
                "type": spec.get("type"),
                "direction": spec.get("direction"),
                "angle": spec.get("angle"),
                "center": spec.get("center"),
                "radius": spec.get("radius"),
                "stops": _normalize_gradient_stops(spec.get("stops")),
            }
            # opaqueEquivalent（DESIGN.md 方案 A）：白宿主预合成等效预设，参与匹配与登记集
            opaque = spec.get("opaqueEquivalent")
            if isinstance(opaque, dict) and opaque.get("stops"):
                contract["gradients"][f"{name}#opaque"] = {
                    "type": spec.get("type"),
                    "direction": spec.get("direction"),
                    "angle": spec.get("angle"),
                    "center": spec.get("center"),
                    "radius": spec.get("radius"),
                    "stops": _normalize_gradient_stops(opaque.get("stops")),
                }


def _section_lines(frontmatter: str, header: str) -> list[str]:
    lines = frontmatter.splitlines()
    start = None
    for i, line in enumerate(lines):
        if line == f"{header}:":
            start = i + 1
            break
    if start is None:
        return []
    block: list[str] = []
    for line in lines[start:]:
        if line.strip() == "":
            block.append(line)
            continue
        if line and not line.startswith((" ", "\t")):
            break
        block.append(line)
    return block


def _fill_from_text(contract: Dict[str, Any], frontmatter: str) -> None:
    for h in HEX_RE.findall(frontmatter):
        contract["allowed_hex"].add(canonical_hex(h))
    for size in _FONT_SIZE_RE.findall(frontmatter):
        contract["allowed_font_sizes"].add(int(size))
    for radius in _RADIUS_RE.findall(frontmatter):
        contract["allowed_radius"].add(int(radius))
    for line in _section_lines(frontmatter, "spacing"):
        m = re.match(r"^\s{2}[\w-]+:\s*(-?\d+)(?:vp)?\s*$", line)
        if m:
            contract["allowed_spacing"].add(int(m.group(1)))
    for key, value in _COPY_LIMIT_RE.findall(frontmatter):
        contract["copy_limits"][key] = int(value)


# ---------------------------------------------------------------------------
# allowed 色集构造（goal docs/goal-dsh-design-check-plugin.md §2.1 / Phase 0）
# 依据：DESIGN.md front-matter（colors / themes / background_gradients /
# button_color_rules / card_element_color_recommendations / components）。
# 返回 {归一化 #rrggbbaa -> {来源名}}，供 COLOR.TOKEN_UNREGISTERED 判定与报错建议。
# ---------------------------------------------------------------------------

_GRADIENT_META_KEYS = ("cssVariableNaming",)
_HEX_SOURCE_SECTIONS = (
    "colors",
    "themes",
    "background_gradients",
    "button_color_rules",
    "card_element_color_recommendations",
    "components",
)


def _add_source(sources: Dict[str, Set[str]], hex_key: str, name: str) -> None:
    sources.setdefault(hex_key, set()).add(name)


def _walk_hex_values(node: Any, base: str, sources: Dict[str, Set[str]]) -> None:
    """递归收集 dict/list/str 里的 hex；来源名用点路径（不含数组下标）。"""
    if isinstance(node, dict):
        for k, v in node.items():
            path = f"{base}.{k}" if base else str(k)
            if isinstance(v, str):
                for h in HEX_RE.findall(v):
                    _add_source(sources, canonical_hex(h), path)
            else:
                _walk_hex_values(v, path, sources)
    elif isinstance(node, list):
        for item in node:
            _walk_hex_values(item, base, sources)


def _add_button_pair(sources: Dict[str, Set[str]], primary_hue_hex: str, name: str) -> None:
    """按 button_color_rules 派生「19 背景 + FF 前景」同色相配对（DESIGN.md L172-189）。"""
    base = canonical_hex(primary_hue_hex)[:7]  # 取 #rrggbb
    _add_source(sources, base + "19", f"button_color_rules.{name}(19/FF 配对)")
    _add_source(sources, base + "ff", f"button_color_rules.{name}(19/FF 配对)")


def _hex_sources_from_yaml(data: Any, sources: Dict[str, Set[str]]) -> None:
    if not isinstance(data, dict):
        return
    colors = data.get("colors")
    if isinstance(colors, dict):
        for k, v in colors.items():
            if isinstance(v, str):
                for h in HEX_RE.findall(v):
                    _add_source(sources, canonical_hex(h), f"colors.{k}")
    themes = data.get("themes")
    if isinstance(themes, dict):
        for tname, theme in themes.items():
            if isinstance(theme, dict):
                for k, v in theme.items():
                    if isinstance(v, str):
                        for h in HEX_RE.findall(v):
                            _add_source(sources, canonical_hex(h), f"themes.{tname}.{k}")
    gradients = data.get("background_gradients")
    if isinstance(gradients, dict):
        for name, spec in gradients.items():
            if name in _GRADIENT_META_KEYS or not isinstance(spec, dict):
                continue
            _walk_hex_values(spec.get("stops"), f"background_gradients.{name}.stops", sources)
            opaque = spec.get("opaqueEquivalent")
            if isinstance(opaque, dict):
                _walk_hex_values(opaque, f"background_gradients.{name}.opaqueEquivalent", sources)
            bcc = spec.get("buttonColorContext")
            if isinstance(bcc, dict):
                _walk_hex_values(bcc, f"background_gradients.{name}.buttonColorContext", sources)
                hue = bcc.get("primaryHue")
                if isinstance(hue, str):
                    for h in HEX_RE.findall(hue):
                        _add_button_pair(sources, h, name)
    for section in ("button_color_rules", "card_element_color_recommendations", "components"):
        _walk_hex_values(data.get(section), section, sources)


def _hex_sources_from_text(frontmatter: str, sources: Dict[str, Set[str]]) -> None:
    """无 PyYAML 时的回退：按行跟踪 2/4 级键名，给 hex 标注「section.键路径」来源。"""
    section = ""
    sub2 = ""  # 最近一级子键（theme 名 / 渐变预设名 / 组件名）
    sub4 = ""  # 最近二级子键（theme token / 预设内键）
    for line in frontmatter.splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        m_top = re.match(r"^([A-Za-z_][\w-]*):", line)
        if indent == 0 and m_top:
            section = m_top.group(1)
            sub2 = ""
            sub4 = ""
            continue
        if section not in _HEX_SOURCE_SECTIONS:
            continue
        stripped = line.strip()
        m_key = re.match(r"^([\w-]+):", stripped)
        if m_key and indent == 2:
            sub2 = m_key.group(1)
            sub4 = ""
        elif m_key and indent == 4 and sub2:
            sub4 = m_key.group(1)
        # 键名先更新再判 meta：否则 cssVariableNaming 后的首个预设行会被跳过，sub2 永远卡死
        if section == "background_gradients" and sub2 in _GRADIENT_META_KEYS:
            continue
        sub = f"{sub2}.{sub4}" if (sub2 and sub4) else sub2
        for h in HEX_RE.findall(line):
            key_hex = canonical_hex(h)
            # primaryHue 可能独占一行，也可能出现在流式 buttonColorContext: {...} 行内
            if section == "background_gradients" and "primaryHue" in stripped:
                _add_button_pair(sources, h, sub2 or "preset")
            _add_source(sources, key_hex, f"{section}.{sub}" if sub else section)


def build_allowed_hex_set(path: Any = None) -> Dict[str, Set[str]]:
    """构造 allowed 色集：{归一化 #rrggbbaa -> {来源名集合}}。

    覆盖 DESIGN.md 的 colors（light）、themes.dark 覆盖、11 个渐变预设全部 stops、
    buttonColorContext.primaryHue 及其 19/FF 配对色、场景点缀色、components 字面色。
    """
    path = Path(path) if path is not None else design_spec_path()
    if not path.exists():
        return {}
    frontmatter = _split_frontmatter(path.read_text(encoding="utf-8"))
    if not frontmatter:
        return {}
    sources: Dict[str, Set[str]] = {}
    if yaml is not None:
        try:
            _hex_sources_from_yaml(yaml.safe_load(frontmatter) or {}, sources)
            _expand_ceil_variant_sources(sources)
            return sources
        except Exception:
            pass
    _hex_sources_from_text(frontmatter, sources)
    _expand_ceil_variant_sources(sources)
    return sources


def load_design_contract(path: Any = None) -> Dict[str, Any]:
    """加载归一化设计契约；path 缺省用 ``DESIGN.md``。"""
    path = Path(path) if path is not None else design_spec_path()
    contract = empty_contract()
    contract["source"] = str(path)
    if not path.exists():
        return contract
    frontmatter = _split_frontmatter(path.read_text(encoding="utf-8"))
    if not frontmatter:
        return contract
    hex_sources: Dict[str, Set[str]] = {}
    if yaml is not None:
        try:
            data = yaml.safe_load(frontmatter) or {}
            _fill_from_yaml(contract, data)
            _hex_sources_from_yaml(data, hex_sources)
            _expand_ceil_variant_sources(hex_sources)
            contract["hex_sources"] = hex_sources
            contract["loaded"] = True
            return contract
        except Exception:
            pass
    _fill_from_text(contract, frontmatter)
    _hex_sources_from_text(frontmatter, hex_sources)
    _expand_ceil_variant_sources(hex_sources)
    contract["hex_sources"] = hex_sources
    contract["loaded"] = True
    return contract


def alpha_class(alpha: int) -> int | None:
    """把 alpha 映到最近的 13 档；不在档位的 alpha 用于报警。"""
    if not 0 <= alpha <= 255:
        return None
    return min(ALPHA_STEPS, key=lambda s: abs(s - alpha))


# ---------------------------------------------------------------------------
# 2×4 布局契约（DESIGN-2x4.md front-matter layout_slots 段，2026-08-22 登记）
# ---------------------------------------------------------------------------

#: 4 根结构登记（DESIGN-2x4.md layout_slots.rootStructures）
ROOT_STRUCTURES_2X4 = ("bare", "titledCompact", "titledRegular", "titledAction")
#: 标准变体登记数（DESIGN-2x4.md layout_slots.standardVariants，18 张标准布局卡）
STANDARD_VARIANTS_COUNT_2X4 = 18
#: 2×4 canvas 登记尺寸（width × height，vp）
CANVAS_2X4_SIZE = (320, 160)

#: 回退解析器把行内嵌套 map（"{ 2: 142, 3: 90.67 }"）保留为字符串时，提取 键: 数值 对
_WIDTHS_RE = re.compile(r"([\w-]+)\s*:\s*(\d+(?:\.\d+)?)")


def _normalize_widths(value: Any) -> Any:
    """splitRules 的 widths 归一化为 {int 键: 数值}（yaml 与回退解析器两种形态）。"""
    if isinstance(value, dict):
        return {int(k) if str(k).isdigit() else k: v for k, v in value.items()}
    if isinstance(value, str):
        pairs = [(k, float(v) if "." in v else int(v)) for k, v in _WIDTHS_RE.findall(value)]
        if pairs:
            return {int(k) if k.isdigit() else k: v for k, v in pairs}
    return value


def _normalize_layout_slots_2x4(slots: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """归一化 layout_slots：canvas 尺寸字符串（"320vp"）转数字、splitRules 的 widths 键转 int。

    保证无论走 PyYAML 还是回退解析器，下游（WP-B 布局规则）读到的宽度都是 int。
    """
    canvas = slots.get("canvas") if isinstance(slots.get("canvas"), dict) else {}
    root_structures = slots.get("rootStructures") if isinstance(slots.get("rootStructures"), dict) else {}
    split_rules = slots.get("splitRules") if isinstance(slots.get("splitRules"), dict) else {}
    standard_variants = slots.get("standardVariants") if isinstance(slots.get("standardVariants"), dict) else {}

    canvas_2x4 = canvas.get("2x4")
    if canvas_2x4 is None and isinstance(canvas.get('"2x4"'), dict):
        # 回退解析器（spec.parse_front_matter）保留 YAML 引号键名，归一化去掉引号
        canvas_2x4 = canvas['"2x4"']
        canvas["2x4"] = canvas_2x4
    if isinstance(canvas_2x4, dict):
        width = _vp_num(canvas_2x4.get("width"))
        height = _vp_num(canvas_2x4.get("height"))
        if width is not None:
            canvas_2x4["width"] = int(width)
        if height is not None:
            canvas_2x4["height"] = int(height)

    for rule in split_rules.values():
        if isinstance(rule, dict) and rule.get("widths") is not None:
            rule["widths"] = _normalize_widths(rule["widths"])

    return {
        "canvas": canvas,
        "rootStructures": root_structures,
        "splitRules": split_rules,
        "standardVariants": standard_variants,
        "horizontalClosure": slots.get("horizontalClosure") or {},
        "verticalClosure": slots.get("verticalClosure") or {},
        "titleRow": slots.get("titleRow") or {},
        "fullWidthSingleColumnAllowed": slots.get("fullWidthSingleColumnAllowed") or [],
        "layout_constraints": data.get("layout_constraints") or {},
    }


def _validate_layout_slots_2x4(contract: Dict[str, Any], path: Path) -> None:
    """校验 2×4 布局契约与登记一致；不一致说明规范文件被误改，抛 ValueError（含路径）。"""
    variants = contract["standardVariants"]
    if len(variants) != STANDARD_VARIANTS_COUNT_2X4:
        raise ValueError(
            f"{path}: layout_slots.standardVariants 登记 {STANDARD_VARIANTS_COUNT_2X4} 个标准变体，"
            f"实际 {len(variants)} 个（键: {sorted(variants)})——规范被误改，拒绝静默错检"
        )
    roots = contract["rootStructures"]
    if set(roots) != set(ROOT_STRUCTURES_2X4):
        raise ValueError(
            f"{path}: layout_slots.rootStructures 登记 {list(ROOT_STRUCTURES_2X4)}，"
            f"实际 {sorted(roots)}——规范被误改，拒绝静默错检"
        )
    canvas_2x4 = contract["canvas"].get("2x4")
    if not isinstance(canvas_2x4, dict):
        raise ValueError(f"{path}: layout_slots.canvas 缺少 2x4 条目——规范被误改")
    size = (canvas_2x4.get("width"), canvas_2x4.get("height"))
    if size != CANVAS_2X4_SIZE:
        raise ValueError(
            f"{path}: 2×4 canvas 登记 {CANVAS_2X4_SIZE[0]}×{CANVAS_2X4_SIZE[1]}，"
            f"实际 {size[0]}×{size[1]}——规范被误改，拒绝静默错检"
        )


def load_layout_slots_2x4(path: Any = None) -> Dict[str, Any]:
    """加载归一化 2×4 布局契约（DESIGN-2x4.md front-matter ``layout_slots`` 段）。

    path 缺省用 ``config.design_2x4_spec_path()``。返回 dict 至少含：``canvas`` /
    ``rootStructures`` / ``splitRules`` / ``standardVariants``（18 变体全量，含
    structure 字符串）/ ``horizontalClosure`` / ``verticalClosure`` / ``titleRow`` /
    ``fullWidthSingleColumnAllowed`` / ``layout_constraints``（顶层键）。

    解析优先 PyYAML（复用 ``_split_front_matter``），缺失时回退
    ``validators.spec.parse_front_matter``。规范文件被误改（变体数/根结构/canvas
    尺寸与登记不符）时抛 ValueError，错误信息含文件路径。
    """
    path = Path(path) if path is not None else design_2x4_spec_path()
    if not path.is_file():
        raise ValueError(f"2x4 规范文件不存在: {path}")
    frontmatter = _split_frontmatter(path.read_text(encoding="utf-8"))
    if not frontmatter:
        raise ValueError(f"2x4 规范文件缺少 front-matter（--- 块）: {path}")
    data: Any = None
    if yaml is not None:
        try:
            data = yaml.safe_load(frontmatter)
        except Exception:
            data = None
    if not isinstance(data, dict):
        from .spec import parse_front_matter  # 无 PyYAML 回退：缩进式 YAML 子集

        data = parse_front_matter(frontmatter)
    slots = data.get("layout_slots")
    if not isinstance(slots, dict):
        raise ValueError(f"{path}: front-matter 缺少 layout_slots 段（2×4 布局契约）")
    contract = _normalize_layout_slots_2x4(slots, data)
    _validate_layout_slots_2x4(contract, path)
    return contract


def attach_card_size_contracts(contract: Dict[str, Any], card: Any) -> Dict[str, Any]:
    """双契约接线收口（Idea2-WP-B 2026-08-26）：按卡尺寸挂尺寸专属契约。

    2×4 卡挂 ``contract["layout_slots_2x4"]``（校验失败即抛错，防规范误改后
    静默错检）；其余维持现状不挂。原 check_card.py 内联逻辑上提至此，
    batch / eval / regression / report_html / sample 各入口统一经本函数注入
    ——修复此前仅 check_card 挂接、其余入口 LAYOUT2X4.* 静默跳过的漏挂缺口。
    """
    if getattr(card, "card_size", None) == "2x4":
        contract["layout_slots_2x4"] = load_layout_slots_2x4(design_2x4_spec_path())
    return contract
