from .common import ParsedA2ui

def _normalize_a2ui_input(a2ui: str | list[dict],) -> list[str]:
    """统一输入格式,允许输入example 目录下两种数据格式"""

    if isinstance(a2ui, str):
        return a2ui.splitlines()

    return [json.dumps(item, ensure_ascii=False)for item in a2ui]

def _check_outer_messages(a2ui:list[str] | None) -> tuple[dict[str, dict[str, Any]], str]:
    """检查DSL 最外层字段"""
    messages: dict[str, dict[str, Any]] = {}
    versions: list[str] = []

    for line_number, raw_line in enumerate(a2ui, 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as exc:
            raise A2uiReverseConversionError(
                f"A2UI line {line_number} is invalid JSON: {exc.msg}."
            ) from exc
        if not isinstance(message, dict):
            raise A2uiReverseConversionError(
                f"A2UI line {line_number} must contain a JSON object."
            )

        version = message["version"]
        if not isinstance(version, str) or not version:
            raise A2uiReverseConversionError("A2UI version must be a non-empty string.")

        # 检查每一行DSL 最外层必须存在两个字段：version 和("createSurface", "updateComponents", "updateDataModel") 中的一个
        msg_keys = set(message)
        unknown_keys = msg_keys - {"version", *_MESSAGE_KINDS}
        if unknown_keys:
            raise A2uiReverseConversionError(
                f"A2UI line {line_number} has unsupported fields: "
                f"{_names(unknown_keys)}."
            )
        kinds = [kind for kind in _MESSAGE_KINDS if kind in message]
        if len(kinds) != 1 or msg_keys != {"version", *kinds}:
            raise A2uiReverseConversionError(
                f"A2UI line {line_number} must contain version and one message payload."
            )

        kind = kinds[0]
        # 检查三类有无重复
        if kind in messages:
            raise A2uiReverseConversionError(f"Duplicate A2UI {kind} message.")
        payload = message[kind]
        if not isinstance(payload, dict):
            raise A2uiReverseConversionError(f"A2UI {kind} payload must be an object.")
        messages[kind] = copy.deepcopy(payload)
        versions.append(version)

    # 检查三类是否有遗漏
    if set(messages) != set(_MESSAGE_KINDS):
        missing = set(_MESSAGE_KINDS) - set(messages)
        raise A2uiReverseConversionError(
            f"A2UI must contain exactly three messages; missing: {_names(missing)}."
        )

    # 检查是否使用了不同版本的A2UI
    if len(set(versions)) != 1:
        raise A2uiReverseConversionError("All A2UI messages must use the same version.")

    return messages,versions[0]


def _validate_create_surface(value: Mapping[str, Any]) -> None:
    """检查createSurface 内部字段 """
    required = {"surfaceId", "catalogId"}
    allowed = {*required, "width", "height"}
    missing = required - set(value)
    unknown = set(value) - allowed
    has_width = "width" in value
    has_height = "height" in value

    if missing or unknown or has_width != has_height:
        details = []
        if missing:
            details.append(f"missing {_names(missing)}")
        if unknown:
            details.append(f"unsupported {_names(unknown)}")
        if has_width != has_height:
            details.append("width and height must appear together")
        raise A2uiReverseConversionError(
            f"createSurface fields are invalid: {'; '.join(details)}."
        )
    if value["catalogId"] != forward._A2UI_FORM_CATALOG_ID:
        raise A2uiReverseConversionError(
            f'Unsupported A2UI catalogId "{value["catalogId"]}".'
        )
    for name in ("width", "height"):
        if name not in value:
            continue
        size = value[name]
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
            raise A2uiReverseConversionError(f"createSurface.{name} must be positive integer.")

def _require_exact_fields(
    value: Mapping[str, Any], expected: set[str], context: str
) -> None:
    """根据expected 检查字段是否缺失"""
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing {_names(missing)}")
        if unknown:
            details.append(f"unsupported {_names(unknown)}")
        raise A2uiReverseConversionError(f"{context} fields are invalid: {'; '.join(details)}.")

def _validate_update_data_model(data: Mapping[str, Any],) -> None:
    """检查updateDataModel 内部字段"""

    _require_exact_fields(
        data,
        {"surfaceId", "path", "value"},
        "updateDataModel",
    )

    if data["path"] != "/":
        raise A2uiReverseConversionError(
            'updateDataModel.path must be "/".'
        )

    if not isinstance(data["value"], dict):
        raise A2uiReverseConversionError(
            "updateDataModel.value must be an object."
        )


def _parse_components(value: Any) -> dict[str, dict[str, Any]]:
    """检查 updateComponents 的components 字段内部"""
    if not isinstance(value, list) or not value:
        raise A2uiReverseConversionError("updateComponents.components must be non-empty array.")

    components: dict[str, dict[str, Any]] = {}
    for index, component in enumerate(value):
        context = f"component[{index}]"
        if not isinstance(component, dict):
            raise A2uiReverseConversionError(f"{context} must be an object.")

        component_id = component.get("id")
        component_type = component.get("component")
        if not isinstance(component_id, str) or not component_id:
            raise A2uiReverseConversionError(f"{context}.id must be non-empty string.")
        if component_id in components:
            raise A2uiReverseConversionError(f'Duplicate A2UI component id "{component_id}".')
        if component_type not in forward._COMPONENT_TYPES - {"ActionUnit"}:
            raise A2uiReverseConversionError(
                f'{component_id}: unsupported A2UI component "{component_type}".'
            )

        allowed = {"id", "component", "children", "styles", "onClick"}

        allowed.update(forward._SEMANTIC_FIELDS.get(component_type, frozenset()))
        if component_type in {"Row", "Column"}:
            allowed.add("itemMargin")
        if component_type == "List":
            allowed.add("space")

        unknown = set(component) - allowed
        if unknown:
            raise A2uiReverseConversionError(
                f"{component_id}: unsupported A2UI fields: {_names(unknown)}."
            )

        children = component.get("children", [])
        if component_type in forward._CONTAINER_TYPES and "children" not in component:
            raise A2uiReverseConversionError(
                f"{component_id}: container must contain the children field."
            )
        if component_type == "Button" and not children and "children" in component:
            raise A2uiReverseConversionError(
                f"{component_id}: empty children is not emitted for a leaf component."
            )
        if component_type not in {*forward._CONTAINER_TYPES, "Button"} and children:
            raise A2uiReverseConversionError(
                f"{component_id}: {component_type} cannot contain children."
            )
        if not isinstance(children, list) or any(
            not isinstance(child, str) or not child for child in children
        ):
            raise A2uiReverseConversionError(
                f"{component_id}: children must be an array of non-empty strings."
            )
        if len(children) != len(set(children)):
            raise A2uiReverseConversionError(f"{component_id}: children contains duplicates.")

        styles = component.get("styles", {})
        if not isinstance(styles, dict):
            raise A2uiReverseConversionError(f"{component_id}: styles must be an object.")
        if "textOverflow" in styles:
            raise A2uiReverseConversionError(
                f"{component_id}: Text.textOverflow is forbidden."
            )
        allowed_styles = set(forward._COMMON_STYLE_PROPERTIES)
        allowed_styles.update(
            forward._COMPONENT_STYLE_PROPERTIES.get(component_type, frozenset())
        )
        # These properties are legal Compact props but are emitted outside styles.
        allowed_styles.discard("itemMargin")
        allowed_styles.discard("space")
        unsupported_styles = set(styles) - allowed_styles
        if unsupported_styles:
            raise A2uiReverseConversionError(
                f"{component_id}: unsupported A2UI styles: {_names(unsupported_styles)}."
            )

        if "onClick" in component:
            on_click = component["onClick"]
            if not isinstance(on_click, list) or not on_click or any(
                not isinstance(handler, dict) for handler in on_click
            ):
                raise A2uiReverseConversionError(
                    f"{component_id}: onClick must be a non-empty array of objects."
                )
        components[component_id] = copy.deepcopy(component)
    return components

def _validate_component_tree(
    root_id: Any,
    components: dict[str, dict[str, Any]],
) -> tuple[str, ...]:
    """DFS 验证children 组件树"""
    if root_id != "root":
        raise A2uiReverseConversionError('updateComponents.root must be "root".')

    root = components.get("root")
    if root is None or root.get("component") != "Column":
        raise A2uiReverseConversionError("The root Column component is missing.")

    parent_by_child: dict[str, str] = {}
    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(component_id: str) -> None:
        if component_id in visiting:
            raise A2uiReverseConversionError(f"Component tree contains cycle at {component_id}.")
        if component_id in visited:
            raise A2uiReverseConversionError(f"Component {component_id} has multiple parents.")
        component = components.get(component_id)
        if component is None:
            raise A2uiReverseConversionError(f"Missing child component {component_id}.")
        visiting.add(component_id)
        order.append(component_id)
        for child_id in component.get("children", []):
            existing = parent_by_child.get(child_id)
            if existing is not None:
                raise A2uiReverseConversionError(
                    f"Component {child_id} is referenced by both {existing} and {component_id}."
                )
            parent_by_child[child_id] = component_id
            visit(child_id)
        visiting.remove(component_id)
        visited.add(component_id)

    visit("root")
    unreachable = set(components) - visited
    if unreachable:
        raise A2uiReverseConversionError(
            f"A2UI contains unreachable components: {_names(unreachable)}."
        )
    return tuple(order)

def parse_a2ui(a2ui: str | list[dict]) -> ParsedA2ui:
    """Parse and strictly validate the forward converter's A2UI envelope."""

    body = _normalize_a2ui_input(a2ui)

    messages,version = _check_outer_messages(body)

    create = messages["createSurface"]
    update = messages["updateComponents"]
    data = messages["updateDataModel"]

    # 检查surface_id 是否一致
    surface_ids = [create["surfaceId"], update["surfaceId"], data["surfaceId"]]
    if any(not isinstance(value, str) or not value for value in surface_ids):
        raise A2uiReverseConversionError("surfaceId must be a non-empty string.")
    if len(set(surface_ids)) != 1:
        raise A2uiReverseConversionError("All A2UI messages must target one surfaceId.")

    _validate_create_surface(create)
    _validate_update_data_model(data)
    _require_exact_fields(
        update,
        {"surfaceId", "root", "components"},
        "updateComponents",
    )

    components_by_id = _parse_components(update["components"])

    order = _validate_component_tree(update["root"], components_by_id)
    return ParsedA2ui(
        version=version,
        surface_id=surface_ids[0],
        create_surface=create,
        update_components=update,
        update_data_model=data,
        components_by_id=components_by_id,
        component_order=order,
    )


