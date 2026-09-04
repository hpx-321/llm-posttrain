"""dumpLayout JSON 解析与真值访问。

dump 来源：
- 模拟器 ``uitest dumpLayout`` 输出（AttributesSchema: ``{attributes, children}``）；
- 数据集 render-evidence ``full-layout.json``（同构，93 张全量可用，离线可跑）。

单位：bounds 为物理 px；density 560 → 3.5 px/vp。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

PX_PER_VP = 3.5
BOUNDS_RE = re.compile(r"\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]")


def parse_bounds(s: Optional[str]) -> Optional[tuple]:
    if not s:
        return None
    m = BOUNDS_RE.match(str(s))
    if not m:
        return None
    l, t, r, b = map(int, m.groups())
    return l, t, r, b


@dataclass
class DumpNode:
    attributes: Dict[str, Any] = field(default_factory=dict)
    children: List["DumpNode"] = field(default_factory=list)
    parent: Optional["DumpNode"] = None

    @property
    def id(self) -> str:
        return str(self.attributes.get("id") or self.attributes.get("key") or "")

    @property
    def type(self) -> str:
        return str(self.attributes.get("type") or "")

    @property
    def bounds_px(self) -> Optional[tuple]:
        return parse_bounds(self.attributes.get("bounds"))

    @property
    def visible(self) -> bool:
        vis = str(self.attributes.get("visible", "true"))
        return vis.strip().lower() != "false"

    @property
    def clickable(self) -> bool:
        return str(self.attributes.get("clickable")).lower() == "true"

    @property
    def text(self) -> str:
        return str(self.attributes.get("text") or "")

    def bounds_vp(self) -> Optional[tuple]:
        b = self.bounds_px
        if b is None:
            return None
        return tuple(x / PX_PER_VP for x in b)  # (l,t,r,b) in vp


@dataclass
class DumpLayout:
    root: DumpNode
    source: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any], source: str = "") -> "DumpLayout":
        root = _build(data, None)
        return cls(root=root, source=source)

    @classmethod
    def from_file(cls, path: Path) -> "DumpLayout":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data, str(path))

    def iter_nodes(self) -> Iterator[DumpNode]:
        yield from _walk(self.root)

    def find_by_id(self, dsl_id: str) -> Optional[DumpNode]:
        for n in self.iter_nodes():
            if n.id == dsl_id:
                return n
        return None

    def card_root(self) -> Optional[DumpNode]:
        # B 卡根 id=root；MS 生成式卡根为 cardgenerated_*_root（不可点击）。
        # 与 validators/rules/protocol.py（DSL 侧）的 *_root 回退同一约定：
        # 后缀候选唯一才用，不唯一按缺根处理（上层显式降级，不臆选）。
        # 不回退则几何断言与报告线框对 MS 分支持续静默缺失。
        root = self.find_by_id("root")
        if root is not None:
            return root
        candidates = [n for n in self.iter_nodes() if n.id.endswith("_root")]
        return candidates[0] if len(candidates) == 1 else None

    def card_nodes(self) -> List["DumpNode"]:
        """返回卡片根子树内的全部节点（含根），用于几何断言。"""
        root = self.card_root()
        if root is None:
            return []
        return list(_walk(root))


def _build(data: Dict[str, Any], parent: Optional[DumpNode]) -> DumpNode:
    node = DumpNode(attributes=data.get("attributes") or {}, parent=parent)
    for child in data.get("children") or []:
        node.children.append(_build(child, node))
    return node


def _walk(node: DumpNode) -> Iterator[DumpNode]:
    yield node
    for c in node.children:
        yield from _walk(c)
