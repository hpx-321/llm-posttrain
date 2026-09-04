"""卡片 DSL 产物解析（真实 case 三件套：query / task-spec / card.genui.jsonl）。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

GENUI_OPS = ("createSurface", "updateComponents", "updateDataModel")
CASE_FILES = ("query.txt", "task-spec.json", "card.genui.jsonl")

_OP_TO_FIELD = {
    "createSurface": "create_surface",
    "updateComponents": "update_components",
    "updateDataModel": "update_data_model",
}

#: 2×4 显式 canvas 尺寸（width × height）；158 宽为端侧实际渲染时的常见舍入值
_2X4_CANVAS = (320, 160)
_2X2_CANVASES = ((160, 160), (158, 160))
_2X4_ROOT_WIDTH = 320
_2X2_ROOT_WIDTHS = (160, 158)


def _as_int(value: Any) -> Optional[int]:
    """把 int / float / 纯数字字符串归一为 int；bool 与非数字返回 None。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            return int(s)
    return None


class CardParseError(ValueError):
    """卡片产物解析失败。"""


@dataclass
class GenuiCard:
    case_id: str
    create_surface: Dict[str, Any] = field(default_factory=dict)
    update_components: Dict[str, Any] = field(default_factory=dict)
    update_data_model: Dict[str, Any] = field(default_factory=dict)
    query_text: str = ""
    task_spec: Dict[str, Any] = field(default_factory=dict)

    @property
    def size(self) -> str:
        return str(self.task_spec.get("size", "2x2"))

    def _root_component(self) -> Optional[Dict[str, Any]]:
        """根解析口径与 rules/protocol.check_root_container 一致：优先 id=root，
        缺失时回退到唯一的 ``*_root`` 后缀组件（生成式根 id 形如 cardgenerated_*_root）。"""
        root = self.find_component("root")
        if root is None:
            roots = [c for c in self.iter_components() if str(c.get("id") or "").endswith("_root")]
            root = roots[0] if len(roots) == 1 else None
        return root

    def _detect_card_size(self) -> tuple[Optional[str], str]:
        """尺寸判定链（逐级回退，首个命中即返回；都不中 (None, "unknown")）：
        1) createSurface 显式 width/height；2) 根组件 styles.width 数字；
        3) task_spec.size 显式登记。注意：不沿用 ``size`` property 的无证据默认
        「2x2」（该默认对裸 DSL 是错的），本链只在有证据时给出结论。
        """
        # 1) createSurface 显式 width/height（320×160 → 2x4；160×160 / 158×160 → 2x2）
        surface = self.create_surface.get("createSurface") if isinstance(self.create_surface, dict) else {}
        surface_msg = surface if isinstance(surface, dict) else {}
        w = _as_int(surface_msg.get("width"))
        h = _as_int(surface_msg.get("height"))
        if w is not None and h is not None:
            if (w, h) == _2X4_CANVAS:
                return "2x4", f"createSurface({w}x{h})"
            if (w, h) in _2X2_CANVASES:
                return "2x2", f"createSurface({w}x{h})"
        # 2) 根组件 styles.width 为数字（320 → 2x4；160/158 → 2x2）
        root = self._root_component()
        styles = root.get("styles") if root is not None else None
        root_width = _as_int(styles.get("width")) if isinstance(styles, dict) else None
        if root_width is not None:
            if root_width == _2X4_ROOT_WIDTH:
                return "2x4", f"root-width({root_width})"
            if root_width in _2X2_ROOT_WIDTHS:
                return "2x2", f"root-width({root_width})"
        # 3) task_spec.size 显式存在且为合法枚举值（不猜默认）
        size = self.task_spec.get("size") if isinstance(self.task_spec, dict) else None
        if size in ("2x4", "2x2"):
            return size, f"task-spec.size({size})"
        return None, "unknown"

    @property
    def card_size(self) -> Optional[str]:
        """卡片尺寸判定："2x2" | "2x4" | None（无证据时 None，source 为 "unknown"）。"""
        return self._detect_card_size()[0]

    @property
    def card_size_source(self) -> str:
        """卡片尺寸判定来源：createSurface(WxH) / root-width(W) / task-spec.size(...) / unknown。"""
        return self._detect_card_size()[1]

    def iter_components(self) -> Iterator[Dict[str, Any]]:
        msg = self.update_components.get("updateComponents") if isinstance(self.update_components, dict) else {}
        comps = msg.get("components") or [] if isinstance(msg, dict) else []
        yield from self._walk(comps)

    def _walk(self, comps: List[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        for comp in comps:
            if not isinstance(comp, dict):
                continue
            yield comp
            children = comp.get("children")
            if isinstance(children, list):
                yield from self._walk(children)

    def find_component(self, comp_id: str) -> Optional[Dict[str, Any]]:
        for comp in self.iter_components():
            if comp.get("id") == comp_id:
                return comp
        return None


def parse_jsonl_lines(text: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise CardParseError(f"JSONL 行解析失败: {exc!r} -> {line[:80]}") from exc
    return records


def parse_dsl_records(text: str) -> List[Any]:
    """兼容两种产物形态：pretty/紧凑 JSON 数组（评测集四分支）与逐行 JSONL。"""
    stripped = text.lstrip()
    if stripped.startswith("["):
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CardParseError(f"JSON 数组解析失败: {exc!r}") from exc
        if not isinstance(data, list):
            raise CardParseError("JSON 数组形态必须是 list")
        return data
    return parse_jsonl_lines(text)


#: 需要提升到组件顶层（而非塞进 styles）的字段，便于规则按 comp.<field> 读取
_TOP_FIELDS = ("content", "src", "onClick")


def _tuple_to_component(rec: list) -> Dict[str, Any]:
    """把「可渲染最终 DSL」4 元组 [id, type, attrs, children] 转成 genui 组件字典。"""
    cid = rec[0] if rec and isinstance(rec[0], str) else f"item_{len(rec)}"
    ctype = rec[1] if len(rec) > 1 and isinstance(rec[1], str) else "Column"
    attrs = rec[2] if len(rec) > 2 and isinstance(rec[2], dict) else {}
    children = rec[3] if len(rec) > 3 and isinstance(rec[3], list) else []
    comp: Dict[str, Any] = {"id": cid, "component": ctype, "styles": attrs, "children": children}
    for field in _TOP_FIELDS:
        if field in attrs:
            comp[field] = attrs[field]
    return comp


def _tuple_records_to_update(records: List[Any]) -> Dict[str, Any]:
    components = [_tuple_to_component(r) for r in records if isinstance(r, list)]
    root = components[0]["id"] if components else "root"
    return {
        "updateComponents": {
            "surfaceId": "surface_tuple_dsl",
            "root": root,
            "components": components,
        }
    }


def load_genui(path: Path, case_id: str) -> GenuiCard:
    records = parse_dsl_records(Path(path).read_text(encoding="utf-8-sig"))
    by_op: Dict[str, Dict[str, Any]] = {}
    tuple_records: List[Any] = []
    for record in records:
        if isinstance(record, dict):
            for op in GENUI_OPS:
                if op in record:
                    by_op[op] = record
                    break
        elif isinstance(record, list):
            tuple_records.append(record)

    if tuple_records and "updateComponents" not in by_op:
        by_op["updateComponents"] = _tuple_records_to_update(tuple_records)

    if "createSurface" not in by_op:
        # 裸 tuple DSL 没有 createSurface 消息，合成最小占位，避免阻断检查
        by_op["createSurface"] = {
            "createSurface": {"surfaceId": "surface_tuple_dsl", "catalogId": "ohos.a2ui.extended.catalog.form"}
        }
    fields = {_OP_TO_FIELD[op]: record for op, record in by_op.items() if op in _OP_TO_FIELD}
    return GenuiCard(case_id=case_id, **fields)


def load_task_spec(path: Path) -> Dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise CardParseError(f"{path}: task-spec 必须是 JSON 对象")
    return data


def load_case(case_dir: Path, case_id: Optional[str] = None) -> GenuiCard:
    case_dir = Path(case_dir)
    if not case_dir.is_dir():
        raise CardParseError(f"case 目录不存在: {case_dir}")
    cid = case_id or case_dir.name
    query_path = case_dir / "query.txt"
    spec_path = case_dir / "task-spec.json"
    dsl_path = case_dir / "card.genui.jsonl"
    missing = [str(p.name) for p in (query_path, spec_path, dsl_path) if not p.exists()]
    if missing:
        raise CardParseError(f"{case_dir}: 缺少文件 {missing}")
    card = load_genui(dsl_path, cid)
    card.query_text = query_path.read_text(encoding="utf-8").strip()
    card.task_spec = load_task_spec(spec_path)
    return card
