# -*- coding: utf-8 -*-
"""Convert validated A2UI documents into deterministic Compact DSL."""

from __future__ import annotations

import copy
import json
import re
from typing import Any

try:
    from . import compact_dsl_a2ui_converter as forward
    from .check_a2ui import parse_a2ui
    from .common import A2uiReverseConversionError, ParsedA2ui
except ImportError:
    import compact_dsl_a2ui_converter as forward
    from check_a2ui import parse_a2ui
    from common import A2uiReverseConversionError, ParsedA2ui


_BINDING_RE = re.compile(r"^\{\{ \$\{(/[^{}]+)\} \}\}$", re.DOTALL)
_EXPRESSION_BINDING_RE = re.compile(r"^\{\{ (.+) \}\}$", re.DOTALL)
_GENERATED_TEXT_MAX_LINES = 1
_GENERATED_ICON_STYLES = {
    "width": 16,
    "height": 16,
    "objectFit": "contain",
    "flexShrink": 0,
}


def convert_a2ui_to_compact_dsl(
    a2ui: str,
    *,
    size: str | None = None,
    collapse_design_tokens: bool = True,
    collapse_color_tokens: bool = False,
    collapse_action_units: bool = True,
) -> str:
    """Convert one final A2UI document into deterministic Compact DSL.

    ``size`` may be omitted only when the Surface dimensions select exactly one
    forward-converter size.  The current 2x4 and 4x2 dimensions are identical,
    so callers must disambiguate those two sizes explicitly.
    """

    parsed = parse_a2ui(a2ui)
    return _convert_parsed_a2ui_to_compact_dsl(
        parsed,
        size=size,
        collapse_design_tokens=collapse_design_tokens,
        collapse_color_tokens=collapse_color_tokens,
        collapse_action_units=collapse_action_units,
    )


def _convert_parsed_a2ui_to_compact_dsl(
    parsed: ParsedA2ui,
    *,
    size: str | None,
    collapse_design_tokens: bool,
    collapse_color_tokens: bool,
    collapse_action_units: bool,
) -> str:
    """Convert an already validated A2UI document without reparsing it."""

    resolved_size = _resolve_size(parsed, size)
    rows = _reverse_component_rows(
        parsed,
        resolved_size,
        collapse_design_tokens=collapse_design_tokens,
        collapse_color_tokens=collapse_color_tokens,
        collapse_action_units=collapse_action_units,
    )
    rows.append(["/", copy.deepcopy(parsed.update_data_model["value"])])
    compact_dsl = _serialize_rows(rows)
    _validate_compact_output(compact_dsl, resolved_size)
    return compact_dsl


def _resolve_size(parsed: ParsedA2ui, requested: str | None) -> str:
    supported = tuple(forward._COMPACT_ROOT_DIMENSIONS)
    if requested is not None:
        if requested not in supported:
            raise A2uiReverseConversionError(f'Unsupported Form size "{requested}".')
        _validate_surface_dimensions(parsed, requested)
        return requested
    if "width" not in parsed.create_surface:
        raise A2uiReverseConversionError(
            "Surface has no dimensions; pass size explicitly or provide it via TaskSpec."
        )
    width = parsed.create_surface["width"]
    height = parsed.create_surface["height"]
    matches = [
        name
        for name in supported
        if forward._surface_dimensions(name, {}) == {"width": width, "height": height}
    ]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise A2uiReverseConversionError(
            f"Surface {width}x{height} does not match a supported Form size."
        )
    raise A2uiReverseConversionError(
        f"Surface {width}x{height} is ambiguous ({', '.join(matches)}); pass size explicitly."
    )


def _validate_surface_dimensions(parsed: ParsedA2ui, size: str) -> None:
    if "width" not in parsed.create_surface:
        return
    expected = forward._surface_dimensions(size, {})
    actual = {
        "width": parsed.create_surface["width"],
        "height": parsed.create_surface["height"],
    }
    if actual != expected:
        raise A2uiReverseConversionError(
            f"Surface dimensions {actual['width']}x{actual['height']} do not match "
            f"size {size} ({expected['width']}x{expected['height']})."
        )


def _reverse_component_rows(
    parsed: ParsedA2ui,
    size: str,
    *,
    collapse_design_tokens: bool,
    collapse_color_tokens: bool,
    collapse_action_units: bool,
) -> list[list[Any]]:
    rows: list[list[Any]] = []
    skipped: set[str] = set()
    for component_id in parsed.component_order:
        if component_id in skipped:
            continue
        component = parsed.components_by_id[component_id]
        if collapse_action_units:
            icon_action = _match_icon_round_action_unit(component, parsed.components_by_id)
            if icon_action is not None:
                props, icon_id = icon_action
                rows.append([component_id, "ActionUnit", props])
                skipped.add(icon_id)
                continue
            capsule_action = _match_capsule_action_unit(component)
            if capsule_action is not None:
                rows.append([component_id, "ActionUnit", capsule_action])
                continue
        row = _reverse_regular_component(
            component,
            size,
            collapse_design_tokens=collapse_design_tokens,
            collapse_color_tokens=collapse_color_tokens,
        )
        rows.append(row)
    return rows


def _match_icon_round_action_unit(
    component: dict[str, Any],
    components: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], str] | None:
    component_id = component["id"]
    icon_id = f"{component_id}_icon"
    if set(component) != {"id", "component", "children", "onClick", "styles"}:
        return None
    if component["component"] != "Stack" or component["children"] != [icon_id]:
        return None
    expected_styles = forward._resolved_design_styles(
        component_id, forward._BUTTON_DESIGNS["icon-round"]
    )
    forward._normalize_icon_button_stack(expected_styles)
    if component["styles"] != expected_styles:
        return None
    icon = components.get(icon_id)
    if icon is None or set(icon) != {"id", "component", "src", "styles"}:
        return None
    if icon["component"] != "Image" or icon["styles"] != _GENERATED_ICON_STYLES:
        return None
    source = icon["src"]
    if not isinstance(source, str) or not source.startswith("resources/base/media/"):
        return None
    return (
        {
            "state": "icon-round",
            "icon": source,
            "onClick": _reverse_bindings(component["onClick"], component_id),
        },
        icon_id,
    )


def _match_capsule_action_unit(component: dict[str, Any]) -> dict[str, Any] | None:
    allowed = {"id", "component", "label", "onClick", "styles", "enabled"}
    if set(component) - allowed:
        return None
    required = {"id", "component", "label", "onClick", "styles"}
    if not required.issubset(component) or component["component"] != "Button":
        return None
    label = component["label"]
    if not isinstance(label, str) or not label.strip():
        return None
    styles = component["styles"]
    expected = forward._resolved_design_styles(
        component["id"], forward._BUTTON_DESIGNS["capsule"]
    )
    if not isinstance(styles, dict) or set(styles) != set(expected):
        return None
    if any(
        styles[name] != value
        for name, value in expected.items()
        if name != "fontColor"
    ):
        return None
    props: dict[str, Any] = {
        "state": "capsule",
        "label": label,
        "onClick": _reverse_bindings(component["onClick"], component["id"]),
    }
    if styles.get("fontColor") != expected.get("fontColor"):
        props["actionInk"] = copy.deepcopy(styles["fontColor"])
    if "enabled" in component:
        props["enabled"] = _reverse_bindings(component["enabled"], component["id"])
    return props


def _reverse_regular_component(
    component: dict[str, Any],
    size: str,
    *,
    collapse_design_tokens: bool,
    collapse_color_tokens: bool,
) -> list[Any]:
    component_id = component["id"]
    component_type = component["component"]
    props: dict[str, Any] = {}
    semantic = forward._SEMANTIC_FIELDS.get(component_type, frozenset())
    for name in semantic:
        if name in component:
            props[name] = _reverse_bindings(component[name], component_id)
    if "onClick" in component:
        props["onClick"] = _reverse_bindings(component["onClick"], component_id)
    if component_type in {"Row", "Column"} and "itemMargin" in component:
        props["itemMargin"] = _reverse_bindings(component["itemMargin"], component_id)
    if component_type == "List" and "space" in component:
        props["space"] = _reverse_bindings(component["space"], component_id)
    for name, value in component.get("styles", {}).items():
        if name in props:
            raise A2uiReverseConversionError(
                f"{component_id}: property {name} appears both as field and style."
            )
        props[name] = _reverse_bindings(value, component_id)

    if component_id == "root":
        _reverse_root_defaults(props, size)
    if component_type == "Text":
        _reverse_text_defaults(props, component_id)
    if collapse_design_tokens:
        _collapse_design(component_type, component_id, props)
    if collapse_color_tokens:
        props = _collapse_colors(props)

    row: list[Any] = [component_id, component_type, props]
    children = component.get("children", [])
    if component_type in forward._CONTAINER_TYPES or children:
        row.append(list(children))
    return row


def _reverse_root_defaults(props: dict[str, Any], size: str) -> None:
    for name in ("width", "height"):
        if props.get(name) != "matchParent":
            raise A2uiReverseConversionError(
                f"root: generated styles.{name} must be matchParent."
            )
        props.pop(name)
    dimensions = forward._COMPACT_ROOT_DIMENSIONS[size]
    props["width"] = dimensions["width"]
    props["height"] = dimensions["height"]
    if not any(
        name in props for name in ("linearGradient", "backgroundColor", "backgroundImage")
    ):
        raise A2uiReverseConversionError(
            "root: forward conversion always emits a background; source has none."
        )
    if size != "2x2":
        return
    generated = {
        "padding": 12,
        "borderRadius": 20,
        "clip": True,
        "itemMargin": 8,
    }
    for name, expected in generated.items():
        if props.get(name) != expected:
            raise A2uiReverseConversionError(
                f"root: generated {name} must equal {expected!r}."
            )
        props.pop(name)
    if props.get("justifyContent") == "spaceBetween":
        props.pop("justifyContent")


def _reverse_text_defaults(props: dict[str, Any], component_id: str) -> None:
    if "textOverflow" in props:
        raise A2uiReverseConversionError(
            f"{component_id}: Text.textOverflow is forbidden."
        )
    if "maxLines" not in props:
        raise A2uiReverseConversionError(
            f"{component_id}: generated Text.maxLines is missing."
        )
    max_lines = props["maxLines"]
    if not isinstance(max_lines, (int, float)) or isinstance(max_lines, bool):
        raise A2uiReverseConversionError(
            f"{component_id}: Text.maxLines must be numeric."
        )
    if max_lines == _GENERATED_TEXT_MAX_LINES:
        props.pop("maxLines")


def _collapse_design(
    component_type: str,
    component_id: str,
    props: dict[str, Any],
) -> None:
    designs = forward._COMPONENT_DESIGNS.get(component_type)
    if not designs:
        return
    for design_name, design_props in designs.items():
        resolved = forward._resolved_design_styles(component_id, design_props)
        if all(name in props and props[name] == value for name, value in resolved.items()):
            for name in resolved:
                props.pop(name)
            props["design"] = design_name
            return


def _collapse_colors(value: Any, property_name: str | None = None) -> Any:
    reverse_tokens: dict[str, str] = {}
    for token, color in forward._COLOR_TOKENS.items():
        reverse_tokens.setdefault(color, token)
    if isinstance(value, dict):
        return {
            key: _collapse_colors(child, key)
            for key, child in value.items()
        }
    if isinstance(value, list):
        if property_name == "colors":
            collapsed = []
            for stop in value:
                if isinstance(stop, list) and len(stop) == 2:
                    collapsed.append([reverse_tokens.get(stop[0], stop[0]), stop[1]])
                else:
                    collapsed.append(copy.deepcopy(stop))
            return collapsed
        return [_collapse_colors(child, property_name) for child in value]
    if property_name in forward._COLOR_PROPERTIES and isinstance(value, str):
        return reverse_tokens.get(value, value)
    return copy.deepcopy(value)


def _reverse_bindings(value: Any, context: str) -> Any:
    if isinstance(value, str):
        match = _BINDING_RE.fullmatch(value)
        if match is not None:
            path = match.group(1)
            try:
                forward._decode_json_pointer(path)
            except forward.CompactDslConversionError as exc:
                raise A2uiReverseConversionError(
                    f"{context}: invalid A2UI binding path {path}."
                ) from exc
            return {"path": path}
        expression_match = _EXPRESSION_BINDING_RE.fullmatch(value)
        if expression_match is not None:
            binding = {"expression": expression_match.group(1)}
            try:
                forward._expression_binding_paths(binding, context)
            except forward.CompactDslConversionError as exc:
                raise A2uiReverseConversionError(
                    f"{context}: unsupported A2UI binding expression {value!r}: {exc}"
                ) from exc
            return binding
        if "{{" in value or "$__dataModel" in value or "$item" in value:
            raise A2uiReverseConversionError(
                f"{context}: unsupported A2UI binding expression {value!r}."
            )
        return value
    if isinstance(value, dict):
        return {key: _reverse_bindings(child, context) for key, child in value.items()}
    if isinstance(value, list):
        return [_reverse_bindings(child, context) for child in value]
    return copy.deepcopy(value)


def _validate_compact_output(compact_dsl: str, size: str) -> None:
    try:
        rows = forward._parse_compact_rows(compact_dsl)
        components, _ = forward._validate_component_tree(rows)
        forward._validate_compact_root_dimensions(components[0], size)
        normalized = [forward._normalize_component(component) for component in components]
        data_rows = [row for row in rows if isinstance(row, forward.DataRow)]
        data_model = forward._build_data_model(data_rows)
        forward._validate_binding_paths(normalized, data_model)
    except forward.CompactDslConversionError as exc:
        raise A2uiReverseConversionError(
            f"Generated Compact DSL does not satisfy the frozen converter: {exc}"
        ) from exc


def _serialize_rows(rows: list[list[Any]]) -> str:
    return "\n".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        for row in rows
    )



