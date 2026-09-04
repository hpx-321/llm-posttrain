"""DESIGN.md 规范加载器。

把 DESIGN.md 拆成两部分：
- front-matter（``---`` 之间）：token 系统（colors / background_gradients / typography /
  spacing / rounded / components / component_contracts …），解析成嵌套 dict；
- Markdown 正文：视觉、布局、间距、组件等规则，按标题建索引。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import design_spec_path

FRONT_MATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")

_SCALAR_LITERALS = {"true": True, "false": False, "null": None}


def _parse_scalar(value: str) -> Any:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    s = value.strip().rstrip(",")
    if s in _SCALAR_LITERALS:
        return _SCALAR_LITERALS[s]
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    return s


def parse_inline_map(text: str) -> Dict[str, Any]:
    """解析 ``{ key: value, key2: "value2" }`` 形式行内映射。"""
    text = text.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return {}
    body = text[1:-1]
    out: Dict[str, Any] = {}
    depth = 0
    start = 0
    pairs: List[str] = []
    for i, ch in enumerate(body):
        if ch in "{[":
            depth += 1
        elif ch in "}]":
            depth -= 1
        elif ch == "," and depth == 0:
            pairs.append(body[start:i])
            start = i + 1
    pairs.append(body[start:])
    for pair in pairs:
        if ":" not in pair:
            continue
        key, _, value = pair.partition(":")
        key = key.strip()
        if key:
            out[key] = _parse_scalar(value)
    return out


def parse_front_matter(fm_text: str) -> Dict[str, Any]:
    """缩进式 YAML 子集解析：嵌套映射、行内 ``{...}``、注释与标量。"""
    root: Dict[str, Any] = {}
    stack: List[tuple[int, Dict[str, Any]]] = [(-1, root)]
    for raw in fm_text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        content = raw.strip()
        if content.startswith("- "):
            key = f"__item_{len(stack[-1][1])}__"
            stack[-1][1][key] = _parse_scalar(content[2:])
            continue
        while stack and indent <= stack[-1][0]:
            stack.pop()
        key, sep, remainder = content.partition(":")
        key = key.strip()
        parent = stack[-1][1]
        if not sep:
            continue
        if remainder.strip() == "":
            child: Dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            value = remainder.strip()
            if value.startswith("{"):
                parent[key] = parse_inline_map(value)
            else:
                parent[key] = _parse_scalar(value)
    return root


def split_design_spec(text: str) -> tuple[Optional[str], str]:
    m = FRONT_MATTER_RE.match(text)
    if m:
        return m.group(1), text[m.end():]
    return None, text


@dataclass
class SpecSection:
    level: int
    title: str
    body: str
    line_start: int


@dataclass
class DesignSpec:
    raw: str = field(repr=False)
    front_matter: Dict[str, Any] = field(default_factory=dict)
    sections: List[SpecSection] = field(default_factory=list)
    spec_path: Optional[Path] = None

    @property
    def tokens(self) -> Dict[str, Any]:
        return self.front_matter

    def section(self, title: str) -> Optional[SpecSection]:
        for s in self.sections:
            if s.title == title:
                return s
        return None

    def token(self, dotted_path: str, default: Any = None) -> Any:
        cur: Any = self.front_matter
        for part in dotted_path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur


def load_design_spec(path: Optional[Path] = None) -> DesignSpec:
    path = path or design_spec_path()
    raw = Path(path).read_text(encoding="utf-8")
    fm_text, body = split_design_spec(raw)
    sections: List[SpecSection] = []
    current: Optional[SpecSection] = None
    for i, line in enumerate(body.splitlines(), start=1):
        m = HEADING_RE.match(line)
        if m:
            if current is not None:
                sections.append(current)
            current = SpecSection(level=len(m.group(1)), title=m.group(2).strip(), body="", line_start=i)
        elif current is not None:
            current.body += line + "\n"
    if current is not None:
        sections.append(current)
    front = parse_front_matter(fm_text) if fm_text else {}
    return DesignSpec(raw=raw, front_matter=front, sections=sections, spec_path=Path(path))
