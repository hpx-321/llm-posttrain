"""dump 侧槽位归区器（WP-AREA）—— 卡根直属子块 → title/content/bottom 三区。

设计依据：2026-08-22 B-q4 dump 实证（金标准：header(Row)=title 区、
batteryRing(Stack)=content 区、saveButton(Button)=bottom 区），供分区针对性
规则消费（L2a：GEOMETRY.AREA_TITLE_ALIGN / AREA_CONTENT_TEXT_OVERLAP /
AREA_BOTTOM_ANCHOR；L1 声明侧的 AREA.TITLE_TEXT_TIER 复用 slot_rule 工具）。

归类口径（宁缺毋滥，归不出留空列表）：
- 槽位块 = 卡根直属可见子块（有 bounds），按顶部 y 排序；
- 93 条语料（含 b-q1）形态为 root → 唯一可见子块 `root_content_contract`
  （Column，宽 134vp = 卡根 158vp 减 12vp×2 安全边距）——卡根仅一个可见
  子块且为 Column 时向下穿透（上限 3 层，同 rules/slot_rule.py 包壳口径）
  取有效容器（再往下的）直属子块作为槽位块；B 分支为 root 直接持有
  title/content/bottom 子块，无需穿透；
- title = 首块（自身或后代含非空 **Text** 节点，或为 Row）；
- bottom = 末块（自身或后代可点，或为 Button 类型）；
- content = 其余块（title 与 bottom 的并集之外）。

退化保护：
- 卡根缺失 / 无 bounds → 返回 None，调用方整体跳过；
- 卡根宽度显著异常（> 240vp，如 b-q1 渲染退化的 320vp 宽）→ 返回 None
  （宁缺毋滥，不臆报；当前语料全部为 2×2 的 158/160vp 宽，2×4 形态的
  显式支持待 layout_slots 声明接入后扩展，与 SLOT_GAP 口径一致）。

Progress 文本陷阱：dump 中 Progress 节点的 attributes.text 有值
（如 '68.000000'）——任何「文本节点」判定必须限定 node.type == 'Text'
且 text 非空（见 texts_in），含 Progress 的子树不算含文本。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .layout import DumpLayout, DumpNode

#: 卡根宽度退化阈值（vp）：正常 2×2 为 158/160vp；b-q1 渲染异常 320vp 宽
ROOT_WIDTH_MAX = 240.0
#: 单子容器穿透深度上限（同 rules/slot_rule.py PIERCE_DEPTH）
PIERCE_DEPTH = 3
#: 可穿透的容器类型：93 条语料 root 唯一可见子块均为 Column
_CONTAINERS = ("Column",)


def texts_in(node: DumpNode) -> List[DumpNode]:
    """node 子树（含自身）内可见的非空 **Text** 节点列表。

    Progress 陷阱防护：Progress 的 attributes.text 有值（如 '68.000000'），
    但 type != 'Text'，不算文本节点——判定必须同时满足
    ``node.type == 'Text'`` 且 ``text.strip()`` 非空。
    """
    out: List[DumpNode] = []
    _collect_texts(node, out)
    return out


def _collect_texts(node: DumpNode, out: List[DumpNode]) -> None:
    if node.type == "Text" and (node.text or "").strip() and node.visible:
        out.append(node)
    for c in node.children:
        _collect_texts(c, out)


def _has_clickable(node: DumpNode) -> bool:
    """node 子树（含自身）内是否存在可点击节点。"""
    if node.clickable:
        return True
    return any(_has_clickable(c) for c in node.children)


@dataclass
class SlotMap:
    """归区结果：三区节点列表 + 卡根 bounds（vp, (l,t,r,b)）。"""

    title: List[DumpNode] = field(default_factory=list)
    content: List[DumpNode] = field(default_factory=list)
    bottom: List[DumpNode] = field(default_factory=list)
    root_bounds: Optional[tuple] = None


def _slot_blocks(root: DumpNode) -> List[DumpNode]:
    """卡根直属可见子块；root 唯一可见子块为 Column 时向下穿透。"""
    blocks = [c for c in root.children if c.visible and c.bounds_vp()]
    depth = 0
    while len(blocks) == 1 and blocks[0].type in _CONTAINERS and depth < PIERCE_DEPTH:
        blocks = [c for c in blocks[0].children if c.visible and c.bounds_vp()]
        depth += 1
    return blocks


def classify(layout: DumpLayout) -> Optional[SlotMap]:
    """把 dump 布局归入 title/content/bottom 三区；退化/定位失败返回 None。"""
    root = layout.card_root()
    if root is None:
        return None
    rb = root.bounds_vp()
    if rb is None:
        return None
    width = rb[2] - rb[0]
    if width > ROOT_WIDTH_MAX:
        # b-q1 渲染退化（320vp 宽，DSL 声明 160vp）：整卡几何失真，宁缺毋滥跳过
        return None

    blocks = sorted(_slot_blocks(root), key=lambda b: b.bounds_vp()[1])  # type: ignore[arg-type]
    if not blocks:
        return SlotMap(root_bounds=rb)

    first, last = blocks[0], blocks[-1]
    title = [first] if (texts_in(first) or first.type == "Row") else []
    bottom = [last] if (last.type == "Button" or _has_clickable(last)) else []
    # 其余=content：剔除 title/bottom 块（含首块未归入 title 时归 content 的情形）
    content = [
        b for b in blocks
        if not any(b is t for t in title) and not any(b is bt for bt in bottom)
    ]
    return SlotMap(title=title, content=content, bottom=bottom, root_bounds=rb)
