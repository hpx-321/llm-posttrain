"""LAYOUT2X4.* —— 2×4 标准 Layout 布局 L1 规则组（DESIGN-2x4.md ``layout_slots`` 段）。

规范依据键（DESIGN-2x4.md front-matter ``layout_slots``）：
- ``canvas``（root=Stack 320×160、borderRadius 20、linearGradient-required；
  contentRoot 为 Column|Row matchParent、padding 固定 12vp、安全区 296×136）
- ``rootStructures``（bare / titledCompact / titledRegular / titledAction 4 根结构，
  垂直闭合 17+4+115 / 20+8+108 / 20+4+72+4+36 = 136）
- ``splitRules``（rowSplitFull gap12 → 142/90.67/65；rowSplitContent gap8 →
  144/93.33/68；columnSplit gap8 → 53.5/33/50；gridG4 格 144×50）
- ``standardVariants``（18 标准变体 structure 字符串）
- ``horizontalClosure.rowRule`` / ``verticalClosure.columnRule``（逐层闭合公式）
- ``layoutRouting.forbidden``（invent-new-layouts / cross-variant-splicing /
  asymmetric-splits / add-regions-for-candidates）

5 条规则 + TEMPLATE_DELTA（2026-08-24 WP2 新增，共 6 条），severity 统一 P1 起步
（未登记形态降 P2）、evidence_type 统一「程序已证实」：
- LAYOUT2X4.ROOT_CONTRACT：root 契约（Stack + borderRadius 20 + linearGradient；
  唯一子 content_root 为 Column/Row；padding==12，14/16/18/20 明示禁止档位）
  ——2026-08-24 owner 裁决：属语法层结构写法契约，移出本插件职责（函数保留、
  静默返回 []，见 check_root_contract docstring）；ROOT_STRUCTURE / VARIANT_MATCH /
  EQUAL_SPLIT / CLOSURE / TEMPLATE_DELTA 五条几何契约保留。
- LAYOUT2X4.ROOT_STRUCTURE：content_root 直接子块序列匹配 4 根结构之一
  （高度闭合：子块高之和 + gap == 136）
- LAYOUT2X4.VARIANT_MATCH：内容树归约成结构骨架（方向 H/V + gap + 直接子块数 +
  子块声明宽高），与官方 18 + Pixso 补充 6 模板匹配（精确）；精确失败后拓扑归位
  （2026-08-24 owner 裁决 WP2：轴/层级/块数/title 家族/action 按钮数同构，title
  高度就近档 {17,20}、数值偏差不阻断）；两者都不中 → 未登记形态降 P2（原 P1 兜底降级）
- LAYOUT2X4.EQUAL_SPLIT：分栏容器子栏宽/高必须等于等分公式值（±1vp 容差）
- LAYOUT2X4.CLOSURE：逐层闭合——Row 左右 padding+子宽和+gap ≤ 父宽；
  Column 上下 padding+子高和+gap ≤ 父高
- LAYOUT2X4.TEMPLATE_DELTA（2026-08-24 WP2 新增）：命中骨架（精确/拓扑）后逐槽位
  量化数值偏差——title 高 / 槽位宽高 / action 按钮（高 36、宽 140/144 等价档）/
  垂直闭合余量（含 gap 口径，itemMargin 顶层生效，五卡 dump 实证）

首版 P1 交人审裁定真违规 vs 规范过严，升 P0 需 owner 拍板（AGENTS.md 检查项范式：
机器只检测+定位+建议，不下最终设计结论）。

口径（AGENTS.md 开发约定）：
- ``card.card_size != "2x4"`` 或契约无 ``layout_slots_2x4`` → 全部返回 []，
  不误伤 2×2 / 无证据卡；
- 组件树两种形态归一（内嵌 children dict / 扁平数组 + children id 引用）；
- matchParent / 未声明尺寸：声明层验声明，未声明跳过（交 L2），不臆造数值；
- 补充骨架（_SUPPLEMENT_TEMPLATES，Pixso 63:61 + 63:62 + 2026-08-24 终审新固化
  ta-H2-dual）仅本模块登记先行，规范侧登记由 owner 另行定夺；finding 命中补充骨架
  标注「扩展（63:xx）·待规范登记」；
- 人工指认（_MANUAL_VERDICTS，2026-08-24 终审三组映射）：owner 指认卡 → 覆写算法
  归位（VARIANT_MATCH 跳过、TEMPLATE_DELTA 按指认模板比对，含结构级 delta——
  指认模板与产物拓扑不同构时块数/嵌套不符各一条 P1）；匹配口径见 _MANUAL_VERDICTS
  注释（分支前缀精确 / 卡号唯一单键回退 / 裸 DSL 无分支信息不误覆写）。
- 规则内部异常由 rules/__init__.py 的 try/except 兜住，规则自己不整卡静默吞错。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from validators.dsl import GenuiCard
from validators.finding import Finding, P1, P2, PROGRAM
from validators.rules import register
from validators.rules._common import make

#: 尺寸比对容差（vp）。90.67/93.33/53.5 等浮点公式值允许 ±1vp 舍入差异
_TOL = 1.0

#: 容器组件集合（退化等分审计只对「子块全为容器」的分栏行判 asymmetric）
_CONTAINER_COMPONENTS = {"Row", "Column", "Stack", "Grid", "List"}


# ---------------------------------------------------------------------------
# 组件树归一层（两种 DSL 形态：内嵌 children dict / 扁平数组 + children id 引用）
# ---------------------------------------------------------------------------

@dataclass
class TNode:
    """组件树节点（两种 DSL 形态归一层）。"""
    comp: Dict[str, Any]
    children: List["TNode"] = field(default_factory=list)
    kind: str = "box"  # row | col | box
    w: Optional[float] = None
    h: Optional[float] = None
    gap: Optional[float] = None
    padding: Optional[float] = None


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _style(comp: Dict[str, Any], key: str) -> Any:
    styles = comp.get("styles")
    return styles.get(key) if isinstance(styles, dict) else None


def _gap(comp: Dict[str, Any]) -> Optional[float]:
    v = comp.get("itemMargin")
    if v is None:
        v = _style(comp, "itemMargin")
    return _num(v)


def _padding(comp: Dict[str, Any]) -> Optional[float]:
    v = _style(comp, "padding")
    if isinstance(v, (int, float)):
        return float(v)
    return None  # dict 形态的 padding（各向不同）不做声明层数值判定


def _root_component(card: GenuiCard) -> Optional[Dict[str, Any]]:
    """根解析口径与 protocol.check_root_container 一致：优先 id=root，
    回退到唯一的 ``*_root`` 后缀组件。"""
    root = card.find_component("root")
    if root is None:
        roots = [c for c in card.iter_components() if str(c.get("id") or "").endswith("_root")]
        root = roots[0] if len(roots) == 1 else None
    return root


def build_tree(card: GenuiCard) -> Optional[TNode]:
    """把卡片组件集合归一层为树；无根返回 None（缺根原由 ROOT_CONTRACT 报告，
    2026-08-24 起该规则静默，缺根不再报）。"""
    root_comp = _root_component(card)
    if root_comp is None:
        return None
    by_id: Dict[str, Dict[str, Any]] = {}
    for comp in card.iter_components():
        cid = comp.get("id")
        if cid:
            by_id[cid] = comp

    def build(comp: Dict[str, Any]) -> TNode:
        node = TNode(comp=comp)
        node.w = _num(_style(comp, "width"))
        node.h = _num(_style(comp, "height"))
        node.gap = _gap(comp)
        node.padding = _padding(comp)
        ctype = comp.get("component")
        node.kind = "row" if ctype == "Row" else ("col" if ctype == "Column" else "box")
        for child in comp.get("children") or []:
            if isinstance(child, str):
                child_comp = by_id.get(child)
                if child_comp is None:
                    continue  # 悬空引用由 PROTOCOL.DANGLING_CHILD 报告
                node.children.append(build(child_comp))
            elif isinstance(child, dict):
                node.children.append(build(child))
        return node

    return build(root_comp)


def _content_node(tree: Optional[TNode]) -> Optional[TNode]:
    """root 的唯一子（content_root）；root 缺失/多子时返回 None。"""
    if tree is None or len(tree.children) != 1:
        return None
    return tree.children[0]


def _is_title_bar(node: TNode) -> bool:
    """title bar 判定：高 17/20vp 且宽 296vp（layout_slots.titleRow.barHeight）。"""
    return node.h in (17.0, 20.0) and node.w == 296.0


def _slots(card: GenuiCard, contract: Dict) -> Optional[Dict[str, Any]]:
    """门禁：非 2×4 卡或无 2×4 布局契约 → None（规则全部静默）。"""
    if card.card_size != "2x4":
        return None
    slots = (contract or {}).get("layout_slots_2x4")
    if not isinstance(slots, dict) or not slots.get("standardVariants"):
        return None
    return slots


# ---------------------------------------------------------------------------
# 18 变体内容骨架模板（standardVariants.structure 的结构化版本；
# 加载时断言键集 == 契约 standardVariants 键集，规范变更必须同步模板）
# ---------------------------------------------------------------------------

#: 模板三元组/四元组：("box", w, h) / ("row"|"col", gap, [children]) /
#: ("vseq", [children])（vseq = content_root 垂直序列，仅 ta-S1）
_VARIANT_TEMPLATES: Dict[str, tuple] = {
    "bare-H2": ("row", 12, [("box", 142, 136), ("box", 142, 136)]),
    "bare-H3": ("row", 12, [("box", 90.67, 136), ("box", 90.67, 136), ("box", 90.67, 136)]),
    "bare-H4": ("row", 12, [("box", 65, 136), ("box", 65, 136), ("box", 65, 136), ("box", 65, 136)]),
    "tc-S1": ("box", 296, 115),
    "tc-S1-list3": ("col", 8, [("box", 296, 33), ("box", 296, 33), ("box", 296, 33)]),
    "tc-H2": ("row", 8, [("box", 144, 115), ("box", 144, 115)]),
    "tc-H2-V2": ("row", 8, [("box", 144, 115),
                            ("col", 8, [("box", 144, 53.5), ("box", 144, 53.5)])]),
    "tc-H2-H2": ("row", 8, [("box", 144, 115),
                            ("row", 8, [("box", 68, 115), ("box", 68, 115)])]),
    "tc-H2-V2H2": ("row", 8, [("box", 144, 115),
                              ("col", 8, [("box", 144, 53.5),
                                          ("row", 8, [("box", 68, 53.5), ("box", 68, 53.5)])])]),
    "tc-H2-G4": ("row", 8, [("box", 144, 115),
                            ("col", 8, [("row", 8, [("box", 68, 53.5), ("box", 68, 53.5)]),
                                        ("row", 8, [("box", 68, 53.5), ("box", 68, 53.5)])])]),
    "tr-H3": ("row", 12, [("box", 90.67, 108), ("box", 90.67, 108), ("box", 90.67, 108)]),
    "tr-H4": ("row", 12, [("box", 65, 108), ("box", 65, 108), ("box", 65, 108), ("box", 65, 108)]),
    "tr-G4": ("col", 8, [("row", 8, [("box", 144, 50), ("box", 144, 50)]),
                         ("row", 8, [("box", 144, 50), ("box", 144, 50)])]),
    "tr-V2": ("col", 8, [("box", 296, 50), ("box", 296, 50)]),
    "tr-V2-H2": ("col", 8, [("box", 296, 50),
                            ("row", 8, [("box", 144, 50), ("box", 144, 50)])]),
    "tr-V2-H3": ("col", 8, [("box", 296, 50),
                            ("row", 8, [("box", 93.33, 50), ("box", 93.33, 50), ("box", 93.33, 50)])]),
    "tr-V2-H4": ("col", 8, [("box", 296, 50),
                            ("row", 8, [("box", 68, 50), ("box", 68, 50), ("box", 68, 50), ("box", 68, 50)])]),
    "ta-S1": ("vseq", [("box", 296, 72), ("box", 140, 36)]),
}


def _templates_ok(slots: Dict[str, Any]) -> bool:
    """模板键集必须与契约 standardVariants 键集一致（防规范变更后静默错检）。"""
    return set(_VARIANT_TEMPLATES) == set((slots.get("standardVariants") or {}).keys())


# ---------------------------------------------------------------------------
# Pixso 补充骨架（2026-08-24 owner 裁决：骨架库扩充，路线 C WP2）
# 来源 = Pixso item-id 63:61「骨架补充」（63:57/63:20/63:37/63:48/63:27）+
# 本轮 63:62 新骨架（用户逐卡指认 A-q20/A-q9 时固化）+ 2026-08-24 终审 ta-H2-dual
# （owner 指认 A-q8 新固化，待 Pixso 补画登记）。与官方 18 共同参与
# VARIANT_MATCH（精确 + 拓扑归位）与 TEMPLATE_DELTA 比对；finding 命中补充骨架时
# 标注「扩展（63:xx）·待规范登记」（规范侧登记由 owner 另行定夺，本表先行）。
# 结构与官方表同构：("box", w, h) / ("row"|"col", gap, [children]) / ("vseq", [children])。
# ---------------------------------------------------------------------------

_SUPPLEMENT_TEMPLATES: Dict[str, tuple] = {
    # 63:57 bare-H2 同构重申（左右二分等分，296×136 内两个 fill 矩形）
    "63:57": ("row", 12, [("box", 142, 136), ("box", 142, 136)]),
    # 63:20 ta-S1-144：单内容 + 单按钮（等分宽 144 = (296-8)/2，官方 capsule 140 等价档差 4vp）
    "63:20": ("vseq", [("box", 296, 72), ("box", 144, 36)]),
    # 63:37 ta-H2：content 内 H 二分 144 + 单按钮 144×36
    "63:37": ("vseq", [("row", 8, [("box", 144, 72), ("box", 144, 72)]), ("box", 144, 36)]),
    # 63:48 tr-H2：title20 + content H 二分 144（官方 tc-H2 为 title17，tr 家族缺二分）
    "63:48": ("row", 8, [("box", 144, 108), ("box", 144, 108)]),
    # 63:27 ta-S1-dual：单内容 + 双按钮行 144×36×2（gap8 闭合 296；即 Q3 形态）
    "63:27": ("vseq", [("box", 296, 72), ("row", 8, [("box", 144, 36), ("box", 144, 36)])]),
    # 63:62 ta-H3-dual：content 内 H 三列等分 93.33 + 双按钮行 144×36×2（2026-08-24 新固化，
    # 用户指认 A-q20/A-q9：93.33×3+8×2=296；144×2+8=296；20+4+72+4+36=136）
    "63:62": ("vseq", [("row", 8, [("box", 93.33, 72), ("box", 93.33, 72), ("box", 93.33, 72)]),
                       ("row", 8, [("box", 144, 36), ("box", 144, 36)])]),
    # ta-H2-dual：title20 + content 内 H 二分 72 + 双按钮行 144×36×2（2026-08-24 终审
    # owner 指认 A-q8 新固化：横向二分 + 两按钮形态；来源 = owner 指认，待 Pixso 补画
    # 登记；闭合 144×2+8=296 / 72+4+36=136）
    "ta-H2-dual": ("vseq", [("row", 8, [("box", 144, 72), ("box", 144, 72)]),
                            ("row", 8, [("box", 144, 36), ("box", 144, 36)])]),
}

#: 补充骨架根结构家族（决定 title 档：bare 无 / tc 17 / tr 20 / ta 20）
_SUPPLEMENT_FAMILY: Dict[str, str] = {
    "63:57": "bare", "63:20": "ta", "63:37": "ta", "63:48": "tr",
    "63:27": "ta", "63:62": "ta", "ta-H2-dual": "ta",
}


def _tpl_family(name: str) -> str:
    """模板名（官方/补充）→ 根结构家族 bare/tc/tr/ta。"""
    if name in _SUPPLEMENT_FAMILY:
        return _SUPPLEMENT_FAMILY[name]
    for fam in ("bare", "tc", "tr", "ta"):
        if name.startswith(fam + "-"):
            return fam
    return "bare"


def _tpl_title_tier(name: str) -> Optional[float]:
    """模板家族 title 档：bare → None；tc → 17；tr/ta → 20。"""
    return {"bare": None, "tc": 17.0, "tr": 20.0, "ta": 20.0}[_tpl_family(name)]


def _all_templates() -> List[Tuple[str, tuple]]:
    """官方 18 + 补充 7 全部模板（官方先，tie-break 稳定）。"""
    return ([(n, t) for n, t in _VARIANT_TEMPLATES.items()]
            + [(n, t) for n, t in _SUPPLEMENT_TEMPLATES.items()])


def _sk(node: TNode) -> tuple:
    """组件节点 → 结构骨架：(kind, gap, w, h, [children]) / ("box", w, h)。"""
    if node.kind in ("row", "col"):
        return (node.kind, node.gap, node.w, node.h, [_sk(c) for c in node.children])
    return ("box", node.w, node.h)


def _content_sk(content: TNode) -> tuple:
    """content_root → 内容骨架（剥掉 title bar 后匹配 18 变体模板）。

    - Row（bare 系）：骨架即其子结构；
    - Column：首子为 title bar（17/20×296）时剥除，余单块 → 该块骨架，
      余多块（ta-S1）→ ("vseq", [...])；无 title 形态多块也归 vseq（匹配不上即报）。
    """
    if content.kind == "row":
        return ("row", content.gap, content.w, content.h, [_sk(c) for c in content.children])
    kids = content.children
    if len(kids) >= 2 and _is_title_bar(kids[0]):
        rest = kids[1:]
        if len(rest) == 1:
            return _sk(rest[0])
        return ("vseq", [_sk(k) for k in rest])
    if len(kids) >= 2:
        return ("vseq", [_sk(k) for k in kids])
    if len(kids) == 1:
        return _sk(kids[0])
    return ("box", None, None)


def _match_sk(node_sk: tuple, tpl: tuple, tol: float = _TOL) -> Tuple[bool, float]:
    """骨架与模板树形递归匹配；返回 (是否完全匹配, 差异评分)。"""
    kind = tpl[0]
    if kind == "box":
        w, h = tpl[1], tpl[2]
        if node_sk[0] == "box":
            nw, nh = node_sk[1], node_sk[2]
            penalty = 0.0
        elif node_sk[0] == "row":
            if len(node_sk[4]) >= 2:
                # 横向分栏（≥2 子块）不是单块槽位：防止 tc-S1 等 box 模板
                # 吞掉自创 H 分栏形态导致 VARIANT_MATCH/EQUAL_SPLIT 漏检
                return (False, 12.0)
            nw, nh = node_sk[2], node_sk[3]
            penalty = 6.0
        elif node_sk[0] == "col":
            # 纵向内容堆叠可承载单块槽位（tc-S1 内容列形态合法）
            nw, nh = node_sk[2], node_sk[3]
            penalty = 6.0
        else:  # vseq：无自身尺寸，不能承载单块槽位
            return (False, 12.0)
        dim_score = 0.0
        if nw is not None and abs(nw - w) > tol:
            dim_score += min(12.0, abs(nw - w))
        if nh is not None and abs(nh - h) > tol:
            dim_score += min(12.0, abs(nh - h))
        return (dim_score == 0, dim_score + penalty)
    if kind == "vseq":
        if node_sk[0] != "vseq":
            return (False, 10.0)
        blocks = tpl[1]
        nblocks = node_sk[1]
        if len(nblocks) != len(blocks):
            return (False, 5.0 + abs(len(nblocks) - len(blocks)) * 3.0)
        total = 0.0
        for nsk, t in zip(nblocks, blocks):
            m, s = _match_sk(nsk, t, tol)
            total += s
            if not m:
                return (False, total)
        return (total == 0, total)
    # row / col 容器
    if node_sk[0] != kind:
        return (False, 10.0)
    gap = tpl[1]
    ngap = node_sk[1]
    if ngap is None:
        gscore = 0.0  # 未声明 gap：声明层不验（交 L2）
    elif abs(ngap - gap) <= tol:
        gscore = 0.0
    elif abs(ngap - gap) <= 2:
        gscore = 2.0
    else:
        gscore = 6.0
    kids = tpl[2]
    nkids = node_sk[4]
    if len(nkids) != len(kids):
        return (False, 5.0 + abs(len(nkids) - len(kids)) * 3.0)
    total = gscore
    for nsk, t in zip(nkids, kids):
        m, s = _match_sk(nsk, t, tol)
        total += s
        if not m:
            return (False, total)
    return (total == 0, total)


def _find_variant(content_sk: tuple) -> Optional[Tuple[str, tuple]]:
    """在 ok（完全匹配）的模板中取差异评分最小者；无 ok 返回 None。

    匹配范围 = 官方 18 + 补充 6（_all_templates，官方先 → 同分取官方）。
    注意取最小评分而非首个匹配：单块槽位模板（tc-S1 等 box）也可承载容器形态
    内容（评分含容器让步分），若先命中会把 H2/V2 等分栏形态「吞掉」，导致
    EQUAL_SPLIT 模板对齐漏检——评分排序保证结构同构的分栏模板优先。
    """
    best: Optional[Tuple[str, tuple, float]] = None
    for name, tpl in _all_templates():
        m, score = _match_sk(content_sk, tpl)
        if m and (best is None or score < best[2]):
            best = (name, tpl, score)
    if best is None:
        return None
    return (best[0], best[1])


# ---------------------------------------------------------------------------
# 拓扑归位匹配（2026-08-24 owner 裁决：VARIANT_MATCH 匹配放宽，路线 C WP2）
# 精确几何匹配失败后做拓扑级匹配：轴 / 层级 / 块数 / title 家族 / action 按钮数
# 同构；title 高度按就近档 {17,20} 归位、数值偏差不阻断（由 TEMPLATE_DELTA 量化）。
# 拓扑命中任一骨架（官方 18 + 补充 6）→ 归位；全部不中 → 未登记形态降 P2。
# 依据：owner 2026-08-24 逐卡指认映射（B-q65→tc-S1-list3 / B-q44→tr-V2 / F03→tc-S1 /
# B-q20→tr-V2-H2 / A-q8→63:27 / A-q93→63:48 / A-q20、A-q9→63:62）+ 匹配过死修正。
# ---------------------------------------------------------------------------

#: 拓扑归位得分阈值（≤ 命中；超出 → 未登记形态 P2）
_TOPO_OK = 5.0


def _is_button_like(node: TNode) -> bool:
    """产物按钮块判定（onClick 或 Button 组件；与 geometry/scripts 口径一致）。"""
    return "onClick" in node.comp or node.comp.get("component") == "Button"


def _title_zone(content: TNode) -> Tuple[List[TNode], List[float]]:
    """前导近似 title 块序列（Row、高 15-28、子含 Text；含 17/20×296 标准 title bar）。

    返回 (zone 块列表, 各块就近档位 17/20)。是否剥离由调用方按前缀 k 尝试
    （k=0 不剥，k=n 剥前 n 块）——A-q8 剥 1 块（device_row 保留为内容）、
    A-q20 剥 2 块（connection_status 归入 title 区域）由对齐得分自然决定。
    """
    zone: List[TNode] = []
    tiers: List[float] = []
    for kid in content.children:
        if kid.kind == "row" and kid.h is not None and 15.0 <= kid.h <= 28.0:
            has_text = any(c.kind == "box" and c.comp.get("component") == "Text"
                           for c in kid.children)
            if has_text or kid.w == 296.0:  # 含 Text 或全宽行（构造正例 title 无 Text 子）
                zone.append(kid)
                tiers.append(20.0 if abs(kid.h - 20.0) <= abs(kid.h - 17.0) else 17.0)
            else:
                break
        else:
            break
    return zone, tiers


def _block_sig(node: TNode) -> tuple:
    """产物块拓扑签名：("btn", n) 按钮行（子全可点）| ("row"|"col", n) 容器 | ("box", 0) 叶。"""
    if node.kind in ("row", "col") and node.children \
            and all(_is_button_like(k) for k in node.children):
        return ("btn", len(node.children))
    if node.kind in ("row", "col"):
        return (node.kind, len(node.children))
    return ("box", 0)


def _tpl_kid_sig(kid: tuple) -> tuple:
    """模板子结构拓扑签名；高 36 的 box / 全 36 高子块容器 = 按钮槽位（144/140 等价档）。"""
    k = kid[0]
    if k == "box":
        w, h = kid[1], kid[2]
        return ("btn", 1) if h == 36.0 else ("box", 0)
    kids = kid[2]
    if all(kk[0] == "box" and kk[2] == 36.0 for kk in kids):
        return ("btn", len(kids))
    return (k, len(kids))


def _slot_score(tsig: tuple, bsig: tuple) -> Optional[float]:
    """槽位对齐分：None = 不兼容；分数越小越接近（拓扑层，数值偏差不参与）。

    按钮槽位（btn）只匹配按钮块（子全可点）；内容行/列槽位（row/col）可承载按钮
    行（B-q20 budsRow 子全可点 ↔ tr-V2-H2 下行槽位）；内容槽位（box）承载任意
    非按钮块（多子容器 +2）。"""
    t_kind, t_n = tsig
    b_kind, b_n = bsig
    if t_kind == "box":
        if b_kind == "btn":
            return None
        if b_kind == "box":
            return 0.0
        return 2.0 if b_n > 1 else 0.0   # 内容槽位承载多子容器 +2
    if t_kind == "btn":
        if b_kind == "btn":
            return float(abs(t_n - b_n))
        return None                       # 按钮槽位不承载内容块
    # 模板 row/col 容器槽位
    if b_kind == t_kind:
        return 2.0 * abs(t_n - b_n)       # 容器子数差 2/子（A-q20 三列 vs 二分区分）
    if b_kind == "btn":
        return 2.0 * abs(t_n - b_n)       # 内容行 ↔ 按钮行（宽松，子数差 2/子）
    return 5.0                            # 方向差 / 叶 vs 容器


def _topo_align(blocks: List[TNode], tpl_kids: List[tuple]) -> Optional[Tuple[list, float]]:
    """贪心对齐：模板槽位序列 vs 产物块序列（跳过不兼容或高代价块，每跳 +1）。

    跳过条件：槽位-块不兼容（_slot_score 返回 None）或代价 > 2（如 row↔col 方向差
    5，应跳过后找更优匹配）。返回 (对齐 [(模板子结构, 产物块), ...], 得分)；
    槽位无可用块/块不足 → None。"""
    align: list = []
    score = 0.0
    i = 0
    for t in tpl_kids:
        tsig = _tpl_kid_sig(t)
        found: Optional[Tuple[int, float]] = None
        for j in range(i, len(blocks)):
            s = _slot_score(tsig, _block_sig(blocks[j]))
            if s is None or s > 2.0:
                score += 3.0
                continue
            found = (j, s)
            break
        if found is None:
            return None
        j, s = found
        align.append((t, blocks[j]))
        score += s
        i = j + 1
    score += 3.0 * (len(blocks) - i)
    return align, score


def _find_topology(content: TNode) -> Optional[Tuple[str, tuple, list, float, Optional[float]]]:
    """拓扑归位：返回 (模板名, tpl, 对齐列表, 得分, title 就近档位|None)；无命中返回 None。

    规则：title 区域剥前缀 k=0..n 全部尝试（得分最优者胜；title 档 = 剥离的最后一
    块就近档位，与模板档差 ≤ 3 计 1 分/档）；轴（row→H / col|vseq→V）严格；形态层
    序列匹配，单块容器时**展开优先**（子块序列命中即取，形态候选不参与——B-q44
    上下二分归 tr-V2 而非形态层单块的 tc-S1、B-q65 列表归 tc-S1-list3）；得分
    ≤ _TOPO_OK 命中，官方先 tie-break。
    """
    zone, tiers = _title_zone(content)
    axis = "H" if content.kind == "row" else "V"
    best: Optional[Tuple[str, tuple, list, float, Optional[float]]] = None
    for k in range(0, len(zone) + 1):
        blocks = [b for b in content.children if b not in zone[:k]]
        tier = tiers[k - 1] if k else None
        if not blocks:
            continue
        for name, tpl in _all_templates():
            tt = _tpl_title_tier(name)
            if tt is None:
                if tier is not None:
                    continue
                tier_pen = 0.0
            else:
                if tier is None or abs(tier - tt) > 3.0:
                    continue
                tier_pen = abs(tier - tt)
            t_axis = "H" if tpl[0] == "row" else "V"
            if tpl[0] == "vseq":
                kids = tpl[1]
            elif tpl[0] in ("row", "col"):
                kids = tpl[2]
            else:
                kids = [tpl]
            # 展开候选（单块容器）：命中即取（展开优先）
            if len(blocks) == 1 and blocks[0].kind in ("row", "col") and blocks[0].children:
                sub_axis = "H" if blocks[0].kind == "row" else "V"
                if sub_axis == t_axis:
                    res = _topo_align(list(blocks[0].children), kids)
                    if res is not None:
                        align, score = res
                        total = score + tier_pen
                        if total <= _TOPO_OK:
                            if best is None or total < best[3]:
                                best = (name, tpl, align, total, tier)
                            continue
            # 形态候选
            if t_axis != axis:
                continue
            res = _topo_align(blocks, kids)
            if res is None:
                continue
            align, score = res
            total = score + tier_pen
            if total > _TOPO_OK:
                continue
            if best is None or total < best[3]:
                best = (name, tpl, align, total, tier)
    return best


def _describe_diff(content_sk: tuple, tpl: tuple) -> str:
    """顶层差异粗描述（供 fix_hint 提示最接近变体差异点）。"""
    if tpl[0] == "box":
        return "内容块尺寸与模板槽位不符"
    if tpl[0] == "vseq":
        return "子块序列/尺寸与模板不符"
    if content_sk[0] != tpl[0]:
        return f"方向不符（实际 {content_sk[0]}，模板 {tpl[0]}）"
    if len(content_sk[4]) != len(tpl[2]):
        return f"分栏数不符（实际 {len(content_sk[4])}，模板 {len(tpl[2])}）"
    return "gap 或槽位尺寸与模板不符"


# ---------------------------------------------------------------------------
# 人工指认表（2026-08-24 owner 终审三组映射，WP2b）
# ---------------------------------------------------------------------------

#: owner 人工指认（2026-08-24 终审）：(分支, 卡号) → 目标模板，覆写算法拓扑归位。
#:
#: 三组终审结论：
#: - B-q20 维持指认 tr-V2-H2：80% 电量与「未充电」是一组语义信息，产物散开
#:   150/134 大间距二分是缺陷——算法几何归位 tr-G4 覆盖不了语义分组；
#: - B-q93 接受算法 63:48（不变，不登记指认）；
#: - A-q8 双方都不对 → 新固化 ta-H2-dual（横向二分 + 双按钮；来源 = owner 指认，
#:   待 Pixso 补画登记）。
#:
#: 匹配口径（最小侵入，check_card --dsl 单卡无分支信息）：
#: 1) case_id 分支前缀（eval_loader 格式 A-q008 / B-q020 / C-Q004，或 check_eval
#:    "B/q20" 形态）→ (分支, 卡号) 精确匹配，卡号数字补零归一（q020 → q20）；
#: 2) 卡号在评测集仅单分支存在时单键回退（_MANUAL_SINGLE_KEY_OK 白名单登记；
#:    当前 q8/q20 在 A/B 双分支都存在，不满足唯一性 → 白名单空，不触发）；
#: 3) 无法唯一匹配时该表项只在能识别分支的场景生效——单卡裸 DSL（case_id=q20
#:    无分支信息）一律不覆写，防 A-q20（归 63:62）等误覆写。
#:
#: 生效路径：VARIANT_MATCH 跳过（不报未匹配/归位）；TEMPLATE_DELTA 按指认模板
#: 做槽位序列比对（数值 delta + 结构级 delta：指认模板与产物拓扑不同构时，
#: 块数/嵌套不符各一条结构差异 P1）。
_MANUAL_VERDICTS: Dict[Tuple[str, str], str] = {
    ("B", "q20"): "tr-V2-H2",
    ("A", "q8"): "ta-H2-dual",
}

#: 单键回退白名单：卡号在评测集（A/B/C/MS 四分支）仅一个分支存在时登记；
#: 当前 q8/q20 在 A/B 双分支都存在 → 空集，裸 DSL 单卡不误覆写。
_MANUAL_SINGLE_KEY_OK: frozenset = frozenset()

#: case_id 分支前缀（eval_loader A-q008 / check_eval B/q20 形态；裸 q20 不匹配）
_VERDICT_CASE_RE = re.compile(r"^(A|B|C|MS|M)[/-](?:[qQ](\d+))?$")


def _card_num(card: GenuiCard) -> Optional[str]:
    """case_id → 指认表卡号（q020 → q20 / q8 → q8）；无卡号返回 None。"""
    m = re.search(r"[qQ](\d+)$", card.case_id or "")
    return f"q{int(m.group(1))}" if m else None


def _verdict_branch(card: GenuiCard) -> Optional[str]:
    """case_id → 分支短名（eval_loader A-q008 / check_eval B/q20 形态）；
    裸 DSL（q20）无分支信息 → None（不臆断分支，防误覆写）。"""
    m = _VERDICT_CASE_RE.match(card.case_id or "")
    return m.group(1) if m else None


def _manual_verdict(card: GenuiCard) -> Optional[str]:
    """owner 人工指认查询：返回目标模板名；无指认返回 None（算法归位照常）。"""
    branch = _verdict_branch(card)
    num = _card_num(card)
    if branch is not None and num is not None:
        hit = _MANUAL_VERDICTS.get((branch, num))
        if hit is not None:
            return hit
    # 单键回退：卡号唯一（白名单登记）且指认表仅一个分支登记该卡号
    if num in _MANUAL_SINGLE_KEY_OK:
        hits = [(b, t) for (b, n), t in _MANUAL_VERDICTS.items() if n == num]
        if len(hits) == 1:
            return hits[0][1]
    return None


# ---------------------------------------------------------------------------
# 规则 1：ROOT_CONTRACT
# ---------------------------------------------------------------------------

@register("LAYOUT2X4.ROOT_CONTRACT")
def check_root_contract(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """root 契约（Stack + borderRadius 20 + linearGradient；唯一子 content_root
    为 Column|Row，padding==12，禁 14/16/18/20）——**静默**（2026-08-24 owner 裁决）。

    裁决记录：「root 必须 Stack / 唯一子 content_root」属**语法层结构写法契约**，
    移出本插件检出范围（本插件专注设计规范/设计元素合法性，如圆角/颜色/间距/
    布局骨架几何契约）；ROOT_STRUCTURE / VARIANT_MATCH / EQUAL_SPLIT / CLOSURE /
    TEMPLATE_DELTA 五条几何契约保留。
    函数保留（内部助手 _root_component / build_tree / _content_node 被其余规则
    复用，不删），仅入口静默返回 []。
    """
    return []


# ---------------------------------------------------------------------------
# 规则 2：ROOT_STRUCTURE
# ---------------------------------------------------------------------------

#: 根结构闭合描述（layout_slots.rootStructures / verticalClosure.padding12-safe-height-136）
_ROOT_CLOSURES = {
    "bare": "content 136",
    "titledCompact": "title 17 + gap 4 + content 115 = 136",
    "titledRegular": "title 20 + gap 8 + content 108 = 136",
    "titledAction": "title 20 + gap 4 + content 72 + gap 4 + capsule 36 = 136",
}


def _match_root_structure(content: TNode) -> Tuple[Optional[str], Optional[str]]:
    """content_root 直接子块序列 → 4 根结构之一；返回 (kind, 差异说明)。

    - Row（bare 全量/三分/四分）→ bare；
    - Column 单块且高 136 → bare；单块高非 136 → 不匹配（可能是缺 title 的
      titled 形态）；
    - Column 首子为 title bar（17/20×296）：2 子块 → titledCompact/titledRegular；
      3 子块 → titledAction；其余 → 不匹配；
    - 其余形态（缺 title / title 高异常）→ 不匹配，差异说明给最接近建议。
    """
    n = len(content.children)
    if content.kind == "row":
        return ("bare", None)
    if n == 1:
        only = content.children[0]
        if only.h is not None and abs(only.h - 136) > _TOL:
            return (None, f"单块高 {only.h:g}（bare 应为 136；若是 titled 形态则缺 title bar，"
                          f"需 17/20×296 title + gap 补足垂直闭合）")
        return ("bare", None)
    first = content.children[0]
    gap = content.gap
    if first.h in (17.0, 20.0) and first.w == 296.0:
        if n == 2:
            return ("titledCompact" if first.h == 17.0 else "titledRegular", None)
        if n == 3:
            return ("titledAction", None)
        return (None, f"title bar 之后应有 1-2 个子块（content[+capsule]），实际 {n - 1} 个")
    if first.h is None and gap in (4.0, 8.0) and n in (2, 3):
        # title 高未声明，按 gap 推断（声明层不臆造，仅形态归组）
        if n == 2:
            return ("titledCompact" if gap == 4.0 else "titledRegular", None)
        return ("titledAction", None)
    hint = f"首子块高 {first.h if first.h is not None else '未声明'}（应为 17/20 title bar×296）"
    return (None, hint)


@register("LAYOUT2X4.ROOT_STRUCTURE")
def check_root_structure(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """content_root 直接子块序列匹配 4 根结构之一；声明齐全时验垂直闭合
    （子块高之和 + gap == 136）。依据：layout_slots.rootStructures /
    verticalClosure.padding12-safe-height-136。"""
    slots = _slots(card, contract)
    if slots is None:
        return []
    content = _content_node(build_tree(card))
    if content is None:
        return []  # 缺根/多子：ROOT_CONTRACT 已静默（2026-08-24 裁决），此处不重复报
    kind, diff = _match_root_structure(content)
    if kind is None:
        return [make(
            card, "LAYOUT2X4.ROOT_STRUCTURE",
            f"content_root 子块序列不匹配 4 根结构之一（{diff}）",
            content.comp.get("id"), severity=P1,
            expected="bare / titledCompact / titledRegular / titledAction",
            actual=diff or "序列不符",
            fix_hint="按 4 根结构对齐：bare 无 title 纯横向分栏；titled 需 17/20×296 title bar + 对应闭合")]
    # 垂直闭合验证（声明齐全才验；gap 未声明时无法证实闭合，跳过）
    gap = content.gap
    heights = [c.h for c in content.children]
    if kind == "bare":
        if gap is not None and heights and all(h is not None for h in heights):
            actual_h = max(heights) if content.kind == "row" else heights[0]
            if abs(actual_h - 136) > _TOL:
                return [make(
                    card, "LAYOUT2X4.ROOT_STRUCTURE",
                    f"bare 垂直闭合应 136（content 全高），实际 {actual_h:g}",
                    content.comp.get("id"), severity=P1,
                    expected="136", actual=f"{actual_h:g}",
                    fix_hint="bare 内容块高度保持 136（安全区 296×136）")]
        return []
    if gap is None or any(h is None for h in heights):
        return []
    total = sum(heights) + gap * (len(heights) - 1)
    if abs(total - 136) > _TOL:
        expected_desc = _ROOT_CLOSURES[kind]
        return [make(
            card, "LAYOUT2X4.ROOT_STRUCTURE",
            f"{kind} 垂直闭合应 136，实际 {total:g}（子块高 {'+'.join(f'{h:g}' for h in heights)} + gap {gap:g}×{len(heights) - 1}）",
            content.comp.get("id"), severity=P1,
            expected=f"136（{expected_desc}）", actual=f"{total:g}",
            fix_hint=f"按 {kind} 闭合对齐：{expected_desc}")]
    return []


# ---------------------------------------------------------------------------
# 规则 3：VARIANT_MATCH
# ---------------------------------------------------------------------------

@register("LAYOUT2X4.VARIANT_MATCH")
def check_variant_match(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """内容树归约成结构骨架，与官方 18 + 补充 7 模板树形递归匹配（精确）；精确失败后
    做拓扑归位（_find_topology：轴/层级/块数/title 家族/action 按钮数同构，title 高度
    就近档 {17,20} 归位、数值偏差不阻断）；拓扑命中 → 归位（数值偏差由 TEMPLATE_DELTA
    量化）；两者都不中 → 未登记形态降 P2（2026-08-24 owner 裁定，原 P1 兜底降级）。
    owner 人工指认卡（_MANUAL_VERDICTS，2026-08-24 终审）→ 直接跳过（VARIANT_MATCH
    不报，TEMPLATE_DELTA 按指认模板比对）。
    依据：layout_slots.standardVariants + layoutRouting.forbidden（invent-new-layouts /
    cross-variant-splicing）+ owner 2026-08-24 路线 C 裁决（WP2）与终审指认（WP2b）。"""
    slots = _slots(card, contract)
    if slots is None:
        return []
    if not _templates_ok(slots):
        return [make(card, "LAYOUT2X4.VARIANT_MATCH",
                     "变体模板键集与契约 standardVariants 不一致（规范变更未同步模板），本规则跳过",
                     severity=P1, fix_hint="同步 _VARIANT_TEMPLATES 与 DESIGN-2x4.md layout_slots")]
    if _manual_verdict(card) is not None:
        return []  # owner 指认覆写（2026-08-24 终审）：跳过算法归位与未登记判定
    content = _content_node(build_tree(card))
    if content is None:
        return []
    content_sk = _content_sk(content)
    if _find_variant(content_sk) is not None:
        return []
    # 拓扑归位（2026-08-24 匹配放宽）：命中任一骨架 → 归位，不报未匹配
    if _find_topology(content) is not None:
        return []
    best_name, best_tpl, best_score = None, None, float("inf")
    for name, tpl in _all_templates():
        _, score = _match_sk(content_sk, tpl)
        if score < best_score:
            best_name, best_tpl, best_score = name, tpl, score
    diff = _describe_diff(content_sk, best_tpl) if best_tpl is not None else "无接近骨架"
    return [make(
        card, "LAYOUT2X4.VARIANT_MATCH",
        f"内容布局未匹配任何已登记骨架（18 官方 + 7 补充，精确与拓扑归位均未命中）"
        f"→ 未登记形态（最接近 {best_name}：{diff}）；owner 2026-08-24 裁定降 P2，待骨架库登记",
        content.comp.get("id"), severity=P2,
        expected="官方 18 + 补充 7 骨架之一（layout_slots.standardVariants + Pixso 63:61/63:62 + ta-H2-dual）",
        actual=f"最接近 {best_name}（差异评分 {best_score:g}）" if best_name else "无",
        fix_hint=f"改用已登记骨架 {best_name} 或按其槽位对齐；禁止 invent-new-layouts / "
                 f"cross-variant-splicing / asymmetric-splits；如需登记新骨架由 owner 指认")]


# ---------------------------------------------------------------------------
# 规则 4：EQUAL_SPLIT
# ---------------------------------------------------------------------------

def _fmt_list(values) -> str:
    return ", ".join(f"{v:g}" for v in values)


def _audit_split(node: TNode, tpl: tuple, card: GenuiCard, findings: List[Finding]) -> None:
    """按已匹配模板逐层核对分栏等分（±1vp 容差）。模板 box/vseq 不产生分栏语义。

    等分基准 = 容器内容区（声明尺寸 − padding×2）：content_root 320+padding12 →
    内容区 296，与 splitRules 公式的 296 基准一致。"""
    kind = tpl[0]
    if kind == "box" or kind == "vseq":
        return
    gap = tpl[1]
    kids = tpl[2]
    if node.kind in ("row", "col") and len(node.children) == len(kids) and len(kids) >= 2:
        if node.kind == "row" and node.w is not None:
            widths = [c.w for c in node.children]
            if all(w is not None for w in widths):
                content_w = node.w - 2 * (node.padding or 0.0)
                exp = (content_w - gap * (len(kids) - 1)) / len(kids)
                if any(abs(w - exp) > _TOL for w in widths):
                    findings.append(make(
                        card, "LAYOUT2X4.EQUAL_SPLIT",
                        f"Row 子栏宽非等分/公式不符：{_fmt_list(widths)}，等分公式值 {exp:g}（内容区 {content_w:g}，gap {gap:g}×{len(kids) - 1}）",
                        node.comp.get("id"), severity=P1,
                        expected=f"每栏 {exp:g}", actual=_fmt_list(widths),
                        fix_hint=f"子栏宽按等分公式 (W-gap×(n-1))/n = {exp:g} 对齐，禁止 asymmetric-splits"))
        elif node.kind == "col" and node.h is not None:
            heights = [c.h for c in node.children]
            if all(h is not None for h in heights):
                content_h = node.h - 2 * (node.padding or 0.0)
                exp = (content_h - gap * (len(kids) - 1)) / len(kids)
                if any(abs(h - exp) > _TOL for h in heights):
                    findings.append(make(
                        card, "LAYOUT2X4.EQUAL_SPLIT",
                        f"Column 子块高非等分/公式不符：{_fmt_list(heights)}，等分公式值 {exp:g}（内容区 {content_h:g}，gap {gap:g}×{len(kids) - 1}）",
                        node.comp.get("id"), severity=P1,
                        expected=f"每块 {exp:g}", actual=_fmt_list(heights),
                        fix_hint=f"子块高按等分公式 (H-gap×(n-1))/n = {exp:g} 对齐"))
    for child, t in zip(node.children, kids):
        _audit_split(child, t, card, findings)


def _audit_degenerate(content: TNode, card: GenuiCard, findings: List[Finding]) -> None:
    """变体未匹配时的保守退化审计：仅 Row 分栏且子块全为容器组件、
    宽度全声明且互不等分 → asymmetric-splits。Column 与内容行（Text/Image 子块）
    不判，宁缺毋滥。"""
    def walk(node: TNode) -> None:
        if node.kind == "row":
            widths = [c.w for c in node.children]
            if (len(node.children) >= 2 and node.w is not None
                    and all(w is not None for w in widths)
                    and all(c.kind in ("row", "col") or c.comp.get("component") in _CONTAINER_COMPONENTS
                            for c in node.children)
                    and max(widths) - min(widths) > _TOL):
                gap = node.gap or 0.0
                content_w = node.w - 2 * (node.padding or 0.0)
                exp = (content_w - gap * (len(node.children) - 1)) / len(node.children)
                findings.append(make(
                    card, "LAYOUT2X4.EQUAL_SPLIT",
                    f"Row 子栏宽互不等分（asymmetric-splits）：{_fmt_list(widths)}"
                    f"（若为分栏，等分公式值应每栏 {exp:g}，内容区 {content_w:g}，gap {gap:g}×{len(node.children) - 1}）",
                    node.comp.get("id"), severity=P1,
                    expected=f"每栏 {exp:g}", actual=_fmt_list(widths),
                    fix_hint="子栏按等分公式 (W-gap×(n-1))/n 对齐；内容行非分栏形态不适用"))
        for c in node.children:
            walk(c)
    # 剪枝：titled 形态首子（title bar 行）及其内部不做分栏判定
    if content.kind == "col" and len(content.children) >= 2 and _is_title_bar(content.children[0]):
        for c in content.children[1:]:
            walk(c)
    else:
        walk(content)


@register("LAYOUT2X4.EQUAL_SPLIT")
def check_equal_split(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """分栏容器子栏宽/高必须等于等分公式值（±1vp 容差；90.67/93.33/53.5 浮点比对）。
    已匹配变体 → 按模板逐层核对；未匹配 → 退化审计（仅 Row 全容器子块互不等分）。
    依据：layout_slots.splitRules（rowSplitFull gap12 / rowSplitContent gap8 /
    columnSplit / gridG4）与 layoutRouting.forbidden.asymmetric-splits。"""
    slots = _slots(card, contract)
    if slots is None:
        return []
    if not _templates_ok(slots):
        return [make(card, "LAYOUT2X4.EQUAL_SPLIT",
                     "变体模板键集与契约 standardVariants 不一致（规范变更未同步模板），本规则跳过",
                     severity=P1, fix_hint="同步 _VARIANT_TEMPLATES 与 DESIGN-2x4.md layout_slots")]
    content = _content_node(build_tree(card))
    if content is None:
        return []
    findings: List[Finding] = []
    content_sk = _content_sk(content)
    matched = _find_variant(content_sk)
    if matched is not None:
        name, tpl = matched
        # 模板顶层 box/vseq 无分栏；容器模板从「剥 title 后的内容节点」对齐：
        # titled 形态下模板容器对应 content_root 的子容器，而非 content_root 本身
        start_node = content
        if content.kind == "col" and len(content.children) >= 2 and _is_title_bar(content.children[0]):
            rest = content.children[1:]
            if len(rest) == 1:
                start_node = rest[0]
        _audit_split(start_node, tpl, card, findings)
    else:
        _audit_degenerate(content, card, findings)
    return findings


# ---------------------------------------------------------------------------
# 规则 5：CLOSURE
# ---------------------------------------------------------------------------

def _audit_closure(node: TNode, card: GenuiCard, findings: List[Finding]) -> None:
    """逐层闭合：Row 左右 padding+子宽和+gap ≤ 父宽；Column 上下 padding+子高和
    +gap ≤ 父高。声明齐全才验；gap/padding 未声明按 0 计（仅证实性报超）。
    依据：layout_slots.horizontalClosure.rowRule / verticalClosure.columnRule。"""
    if node.kind in ("row", "col"):
        kids = node.children
        n = len(kids)
        if n >= 1:
            gap = node.gap or 0.0
            pad = node.padding or 0.0
            if node.kind == "row":
                parent_dim = node.w
                child_dims = [c.w for c in kids]
                if parent_dim is not None and all(d is not None for d in child_dims):
                    total = pad * 2 + sum(child_dims) + gap * (n - 1)
                    if total > parent_dim + _TOL:
                        findings.append(make(
                            card, "LAYOUT2X4.CLOSURE",
                            f"Row 横向闭合超父宽：声明预算 {parent_dim:g}vp vs 实际之和 {total:g}vp"
                            f"（子宽 {_fmt_list(child_dims)} + gap {gap:g}×{n - 1} + padding {pad:g}×2）",
                            node.comp.get("id"), severity=P1,
                            expected=f"≤ {parent_dim:g}", actual=f"{total:g}",
                            fix_hint="缩减子项宽度/减少分栏或 gap，保证 padding×2+子宽和+gap×(n-1) ≤ 父宽"))
            else:
                parent_dim = node.h
                child_dims = [c.h for c in kids]
                if parent_dim is not None and all(d is not None for d in child_dims):
                    total = pad * 2 + sum(child_dims) + gap * (n - 1)
                    if total > parent_dim + _TOL:
                        findings.append(make(
                            card, "LAYOUT2X4.CLOSURE",
                            f"Column 纵向闭合超父高：声明预算 {parent_dim:g}vp vs 实际之和 {total:g}vp"
                            f"（子高 {_fmt_list(child_dims)} + gap {gap:g}×{n - 1} + padding {pad:g}×2）",
                            node.comp.get("id"), severity=P1,
                            expected=f"≤ {parent_dim:g}", actual=f"{total:g}",
                            fix_hint="缩减子项高度/减少分栏或 gap，保证 padding×2+子高和+gap×(n-1) ≤ 父高"))
    for child in node.children:
        _audit_closure(child, card, findings)


@register("LAYOUT2X4.CLOSURE")
def check_closure(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """逐层闭合预算：Row 左右 padding+子宽和+gap ≤ 父宽；Column 上下 padding+
    子高和+gap ≤ 父高；超出 P1，message 给「声明预算 vs 实际之和」。
    依据：layout_slots.horizontalClosure.rowRule / verticalClosure.columnRule。"""
    slots = _slots(card, contract)
    if slots is None:
        return []
    content = _content_node(build_tree(card))
    if content is None:
        return []
    findings: List[Finding] = []
    _audit_closure(content, card, findings)
    return findings


# ---------------------------------------------------------------------------
# 规则 6：TEMPLATE_DELTA（2026-08-24 owner 路线 C 裁决 + 逐卡指认，WP2）
# 卡命中骨架（精确或拓扑归位）后逐槽位量化数值偏差：title 高 / 各行·栏宽高 /
# action 按钮（高 36、宽 140/144 等价档）/ 垂直闭合余量（含 gap 口径，itemMargin
# 顶层生效——2026-08-24 五卡 dump 实证）。每处偏差独立 P1 finding，message 给
# 「产物值 vs 模板值」与 delta。未命中骨架的卡静默（未登记形态由 VARIANT_MATCH
# 降 P2 报告）。
# ---------------------------------------------------------------------------

#: 安全区（layout_slots.canvas.safeArea：padding 12 → 296×136）
_SAFE_W = 296.0
_SAFE_H = 136.0
#: 按钮宽等价档（140 = 官方 capsule 注册宽 / 144 = 补充骨架等分宽，差 4vp 内合规）
_BTN_W = (140.0, 144.0)


def _delta_msg(prod_id: str, what: str, pv: float, tv: float) -> str:
    return (f"{prod_id} {what} {pv:g} vs 模板 {tv:g}（delta {pv - tv:+.0f}）")


def _delta_slot(t_kid: tuple, node: TNode, name: str, card: GenuiCard,
                findings: List[Finding]) -> None:
    """单槽位尺寸比对（递归容器子槽）。"""
    k = t_kid[0]
    nid = str(node.comp.get("id") or "?")
    if k == "box":
        w, h = float(t_kid[1]), float(t_kid[2])
        if h == 36.0:
            # 按钮槽位：高 36 严格（±1）；宽 140/144 等价档（|差| ≤ 4 合规）。
            # 按钮容器（onClick Row/Column）取自身声明宽高，不取其内部子块。
            bw, bh = node.w, node.h
            if bw is not None and min(abs(bw - b) for b in _BTN_W) > 4.0:
                findings.append(make(
                    card, "LAYOUT2X4.TEMPLATE_DELTA",
                    _delta_msg(nid, "按钮宽", bw, w),
                    nid, severity=P1, expected=f"{w:g}（140/144 等价档）", actual=f"{bw:g}",
                    fix_hint="按钮宽对齐 capsule 140 注册宽或补充骨架等分宽 144"))
            if bh is not None and abs(bh - 36.0) > _TOL:
                findings.append(make(
                    card, "LAYOUT2X4.TEMPLATE_DELTA",
                    _delta_msg(nid, "按钮高", bh, 36.0),
                    nid, severity=P1, expected="36", actual=f"{bh:g}",
                    fix_hint="按钮高对齐 36vp 契约"))
        else:
            for label, tv, nv in (("宽", w, node.w), ("高", h, node.h)):
                if nv is not None and abs(nv - tv) > _TOL:
                    findings.append(make(
                        card, "LAYOUT2X4.TEMPLATE_DELTA",
                        _delta_msg(nid, label, nv, tv),
                        nid, severity=P1, expected=f"{tv:g}", actual=f"{nv:g}",
                        fix_hint=f"{label}对齐模板槽位 {tv:g}"))
        return
    # 容器槽位：gap 比对（itemMargin 顶层生效，2026-08-24 五卡 dump 实证）+ 子递归
    if k in ("row", "col"):
        tgap = float(t_kid[1])
        if node.gap is not None and abs(node.gap - tgap) > _TOL:
            findings.append(make(
                card, "LAYOUT2X4.TEMPLATE_DELTA",
                _delta_msg(nid, "gap", node.gap, tgap),
                nid, severity=P1, expected=f"{tgap:g}", actual=f"{node.gap:g}",
                fix_hint=f"gap 对齐档位 {tgap:g}"))
        for sub_t, sub_n in zip(t_kid[2], node.children):
            _delta_slot(sub_t, sub_n, name, card, findings)


def _align_for_delta(content: TNode, tpl: tuple, k: int = 1) -> List[Tuple[tuple, TNode]]:
    """模板结构 ↔ 产物树（剥 title 前缀 k 块后）贪心对齐（精确/拓扑共用）。"""
    zone, _ = _title_zone(content)
    blocks = [b for b in content.children if b not in zone[:k]]
    if tpl[0] == "vseq":
        kids = tpl[1]
    elif tpl[0] in ("row", "col"):
        kids = tpl[2]
    else:
        kids = [tpl]
    res = _topo_align(blocks, kids)
    return res[0] if res is not None else []


def _delta_closure(content: TNode, card: GenuiCard, findings: List[Finding]) -> None:
    """垂直闭合余量（含 gap 口径，itemMargin 顶层生效；声明齐全才验）。"""
    nid = str(content.comp.get("id") or "?")
    g = content.gap if content.gap is not None else 0.0
    if content.kind == "col":
        hs = [c.h for c in content.children]
        if all(h is not None for h in hs):
            total = sum(hs) + g * (len(hs) - 1)
            rem = _SAFE_H - total
            if abs(rem) > _TOL:
                findings.append(make(
                    card, "LAYOUT2X4.TEMPLATE_DELTA",
                    f"{nid} 垂直闭合余量 {rem:+.0f}vp（Σ子和+gap {total:g} vs 安全区 {_SAFE_H:g}）",
                    nid, severity=P1, expected=f"闭合 {_SAFE_H:g}", actual=f"余 {rem:g}vp",
                    fix_hint="按根结构闭合式对齐（bare 136 / tc 17+4+115 / tr 20+8+108 / ta 20+4+72+4+36）"))
    elif content.kind == "row":
        ws = [c.w for c in content.children]
        if all(w is not None for w in ws):
            total = sum(ws) + g * (len(ws) - 1)
            rem = _SAFE_W - total
            if abs(rem) > _TOL:
                findings.append(make(
                    card, "LAYOUT2X4.TEMPLATE_DELTA",
                    f"{nid} 横向闭合余量 {rem:+.0f}vp（Σ子和+gap {total:g} vs 安全区 {_SAFE_W:g}）",
                    nid, severity=P1, expected=f"闭合 {_SAFE_W:g}", actual=f"余 {rem:g}vp",
                    fix_hint="分栏按等分公式闭合 296"))


# ---------------------------------------------------------------------------
# 指认路径：TEMPLATE_DELTA 按 owner 指认模板比对（2026-08-24 终审，WP2b）
# 指认模板与产物拓扑不同构时 → 结构级 delta（P1，程序已证实）：按指认模板做
# 槽位序列比对，块数/嵌套不符各一条结构差异 finding（B-q20 上行散开 150/134、
# A-q8 状态行多一层 / action 行单按钮+文本等）；同构槽位照常报数值 delta。
# ---------------------------------------------------------------------------


def _verdict_tpl(name: str) -> Optional[tuple]:
    """指认模板名 → 模板结构（官方 18 + 补充 7 查找）。"""
    return _VARIANT_TEMPLATES.get(name) or _SUPPLEMENT_TEMPLATES.get(name)


def _dim_score(v: Optional[float], target: float) -> float:
    """数值适配分（≤6 封顶；未声明 0 分）。"""
    return 0.0 if v is None else min(6.0, abs(v - target))


def _verdict_slot_score(t_kid: tuple, node: TNode) -> float:
    """指认槽位 ↔ 产物块适配分（越小越适配；仅用于对齐择优，不产出 finding）。"""
    k = t_kid[0]
    if k == "box":
        w, h = float(t_kid[1]), float(t_kid[2])
        if h == 36.0:  # 按钮槽位：行/按钮块均可，成分差异由结构审计报
            if _block_sig(node)[0] == "btn":
                pen, nw, nh = 0.0, node.w, node.h
            elif node.kind == "box":
                pen, nw, nh = 2.0, node.w, node.h
            else:
                pen, nw, nh = 1.0, node.w, node.h
            return pen + _dim_score(nw, w) + _dim_score(nh, h)
        if _block_sig(node)[0] == "btn":
            return 6.0  # 内容槽位不吃按钮块
        pen = 4.0 if node.kind in ("row", "col") and len(node.children) >= 2 else 0.0
        return pen + _dim_score(node.w, w) + _dim_score(node.h, h)
    # row/col 容器槽位
    if node.kind == "box":
        return 5.0  # 模板容器槽位 ↔ 产物单块（嵌套不符，结构审计报）
    pen = 0.0 if node.kind == k else 3.0
    n, m = len(t_kid[2]), len(node.children)
    if n == m:
        num = sum(_dim_score(cn.w, ct[1]) + _dim_score(cn.h, ct[2])
                  for ct, cn in zip(t_kid[2], node.children) if ct[0] == "box")
    else:
        num = 2.0 * abs(n - m)
    return pen + num


def _verdict_align(blocks: List[TNode], kids: List[tuple]) -> Tuple[list, List[TNode]]:
    """指认槽位序列 ↔ 产物块序列贪心最佳适配（允许跳块，不跳槽）；
    返回 (配对 [(模板子结构, 产物块), ...], 跳过的多余块)。"""
    pairs: list = []
    skipped: List[TNode] = []
    i = 0
    for t in kids:
        best_j, best_s = None, None
        for j in range(i, len(blocks)):
            s = _verdict_slot_score(t, blocks[j])
            if best_s is None or s < best_s:
                best_j, best_s = j, s
        if best_j is None:
            break  # 块已耗尽：剩余槽位缺失（块数不符由调用方报）
        for j in range(i, best_j):
            skipped.append(blocks[j])
        pairs.append((t, blocks[best_j]))
        i = best_j + 1
    for j in range(i, len(blocks)):
        skipped.append(blocks[j])
    return pairs, skipped


def _fmt_dims(w: Optional[float], h: Optional[float]) -> str:
    """w×h 串（未声明显示 ?）。"""
    s = lambda v: f"{v:g}" if v is not None else "?"  # noqa: E731
    return f"{s(w)}×{s(h)}"


def _children_dims(node: TNode) -> str:
    """产物容器子块尺寸串（行宽 / 列高；含 gap，如 150/134 gap12）。"""
    vals = [c.w for c in node.children] if node.kind == "row" else [c.h for c in node.children]
    dims = "/".join(f"{v:g}" if v is not None else "?" for v in vals)
    gap = node.gap if node.gap is not None else 0.0
    return f"{dims} gap{gap:g}"


def _delta_slot_verdict(t_kid: tuple, node: TNode, slot_name: str, card: GenuiCard,
                        findings: List[Finding]) -> None:
    """指认模板槽位比对：结构不同构 → 结构差异 finding（各一条）；同构 → 数值 delta。"""
    k = t_kid[0]
    nid = str(node.comp.get("id") or "?")
    if k == "box":
        w, h = float(t_kid[1]), float(t_kid[2])
        if h == 36.0:
            # 单按钮槽位
            if node.kind == "box":
                if not _is_button_like(node):
                    findings.append(make(
                        card, "LAYOUT2X4.TEMPLATE_DELTA",
                        f"槽位{slot_name}应为按钮（144×36 档），实际为文本/内容块（{_fmt_dims(node.w, node.h)}）",
                        nid, severity=P1, expected="按钮 144×36", actual=_fmt_dims(node.w, node.h),
                        fix_hint="按指认模板按钮槽位放按钮（onClick/Button 组件）"))
                else:
                    _delta_slot(t_kid, node, slot_name, card, findings)
                return
            if node.children and _is_button_like(node):
                # 按钮容器（整行可点）：数值比对（取自身声明宽高）
                _delta_slot(t_kid, node, slot_name, card, findings)
                return
            btns = [c for c in node.children if _is_button_like(c)]
            findings.append(make(
                card, "LAYOUT2X4.TEMPLATE_DELTA",
                f"槽位{slot_name}应为 1 个按钮（144×36 档），实际 {len(btns)} 按钮 + {len(node.children) - len(btns)} 文本/内容块"
                f"（{_fmt_dims(node.w, node.h)}）",
                nid, severity=P1, expected="1 按钮",
                actual=f"{len(btns)} 按钮 + {len(node.children) - len(btns)} 文本/内容块",
                fix_hint="按指认模板按钮槽位放按钮（onClick/Button 组件）"))
            return
        # 内容 box 槽位：产物散开多块 → 结构差异（语义分组不得拆散）
        if node.kind in ("row", "col") and len(node.children) >= 2 and not _is_button_like(node):
            findings.append(make(
                card, "LAYOUT2X4.TEMPLATE_DELTA",
                f"槽位{slot_name}应为整组 1 块（{w:g}×{h:g}），实际散开 {len(node.children)} 块"
                f"（{_children_dims(node)}）",
                nid, severity=P1, expected=f"整组 1 块 {w:g}×{h:g}",
                actual=f"散开 {len(node.children)} 块（{_children_dims(node)}）",
                fix_hint="按指认模板槽位合并为整组块（语义分组不得拆散）"))
            return
        _delta_slot(t_kid, node, slot_name, card, findings)
        return
    # row/col 容器槽位
    if node.kind == "box":
        findings.append(make(
            card, "LAYOUT2X4.TEMPLATE_DELTA",
            f"槽位{slot_name}应为 {k} 容器 {len(t_kid[2])} 块（gap {t_kid[1]:g}），实际单块"
            f"（{_fmt_dims(node.w, node.h)}）",
            nid, severity=P1, expected=f"{k} {len(t_kid[2])} 块容器", actual="单块",
            fix_hint="按指认模板展开容器槽位"))
        return
    t_kids = t_kid[2]
    n, m = len(t_kids), len(node.children)
    if node.kind != k or n != m:
        findings.append(make(
            card, "LAYOUT2X4.TEMPLATE_DELTA",
            f"槽位{slot_name}应为 {k} {n} 块（gap {t_kid[1]:g}），实际 {node.kind} {m} 块"
            f"（{_children_dims(node)}）",
            nid, severity=P1, expected=f"{k} {n} 块", actual=f"{node.kind} {m} 块",
            fix_hint="按指认模板槽位序列对齐块数/方向"))
        return
    if k == "row" and t_kids and all(kt[0] == "box" and kt[2] == 36.0 for kt in t_kids):
        # 按钮行槽位：产物行按钮成分核对（单按钮+文本 vs 双按钮等）
        btns = [c for c in node.children if _is_button_like(c)]
        n_other = len(node.children) - len(btns)
        if n_other > 0:
            findings.append(make(
                card, "LAYOUT2X4.TEMPLATE_DELTA",
                f"槽位{slot_name}应为 {n} 个按钮，实际 {len(btns)} 按钮 + {n_other} 文本/内容块"
                f"（{_fmt_dims(node.w, node.h)}）",
                nid, severity=P1, expected=f"{n} 按钮",
                actual=f"{len(btns)} 按钮 + {n_other} 文本/内容块",
                fix_hint="action 行对齐指认模板按钮行（144×36×n，gap 8）"))
            return  # 成分不符：不进子槽数值（避免误导性按钮宽/高 delta）
        for sub_t, sub_n in zip(t_kids, node.children):
            _delta_slot(sub_t, sub_n, slot_name, card, findings)
        return
    tgap = float(t_kid[1])
    if node.gap is not None and abs(node.gap - tgap) > _TOL:
        findings.append(make(
            card, "LAYOUT2X4.TEMPLATE_DELTA",
            _delta_msg(nid, "gap", node.gap, tgap),
            nid, severity=P1, expected=f"{tgap:g}", actual=f"{node.gap:g}",
            fix_hint=f"gap 对齐档位 {tgap:g}"))
    for i, (sub_t, sub_n) in enumerate(zip(t_kids, node.children)):
        _delta_slot_verdict(sub_t, sub_n, f"{slot_name}内{i + 1}", card, findings)


def _check_verdict_delta(card: GenuiCard, tree: Optional[TNode], verdict: str) -> List[Finding]:
    """owner 指认卡：按指认模板做槽位序列比对（数值 + 结构级 delta）。

    - content 解析带 root 回退：root 多子且首子为 title bar（root 即 content_root，
      B-q20/B-q93 形态）时以 root 本身为 content；
    - title 剥离仅限严格 title bar（17/20×296，_is_title_bar）：非 17/20 的状态行
      不剥 → 作为「多出 1 层」结构差异如实报（A-q8 device_row）；
    - 槽位序列贪心最佳适配（_verdict_align，允许跳块）；跳过的块 = 多余层，
      块不足 = 缺槽，各一条 P1；
    - 结构不同构槽位报结构差异（各一条），同构槽位走数值 delta（_delta_slot_verdict）。
    """
    tpl = _verdict_tpl(verdict)
    if tpl is None:
        return []  # 指认模板未登记：静默（防臆造比对）
    content = _content_node(tree)
    if content is None and tree is not None and len(tree.children) >= 2:
        content = tree  # root 即 content_root（root 双子无 wrapper）
    if content is None:
        return []
    if tpl[0] == "vseq":
        kids = tpl[1]
    elif tpl[0] in ("row", "col"):
        kids = tpl[2]
    else:
        kids = [tpl]
    zone = [b for b in content.children if _is_title_bar(b)]
    best: Optional[Tuple[float, int, list, List[TNode]]] = None
    for k in range(len(zone) + 1):
        blocks = [b for b in content.children if b not in zone[:k]]
        if not blocks:
            continue
        if len(blocks) == 1 and blocks[0].kind in ("row", "col") and blocks[0].children:
            blocks = list(blocks[0].children)  # 展开单块容器（与拓扑路径口径一致）
        pairs, skipped = _verdict_align(blocks, kids)
        tier = zone[k - 1].h if k else None
        tt = _tpl_title_tier(verdict)
        if tt is not None and tier is not None:
            tier_pen = abs(tier - tt)
        elif (tt is None) != (tier is None):
            tier_pen = 3.0
        else:
            tier_pen = 0.0
        score = sum(_verdict_slot_score(t, n) for t, n in pairs) + 3.0 * len(skipped) + tier_pen
        if best is None or score < best[0]:
            best = (score, k, pairs, skipped)
    if best is None:
        return []
    _, k, pairs, skipped = best
    findings: List[Finding] = []
    # title 档
    tier = zone[k - 1].h if k else None
    tt = _tpl_title_tier(verdict)
    cid = str(content.comp.get("id") or "content_root")
    if tt is not None and tier is None:
        findings.append(make(
            card, "LAYOUT2X4.TEMPLATE_DELTA",
            f"缺 title bar（指认模板 {verdict} 为 {tt:g} 档；产物无 17/20×296 title 区域）",
            cid, severity=P1, expected=f"title {tt:g}", actual="无",
            fix_hint=f"补 {tt:g}×296 title bar（含 Text 的 Row）"))
    elif tt is not None and abs(tier - tt) > _TOL:
        findings.append(make(
            card, "LAYOUT2X4.TEMPLATE_DELTA",
            f"title 高 {tier:g} vs 模板 {tt:g}（delta {tier - tt:+.0f}）",
            cid, severity=P1, expected=f"title {tt:g}", actual=f"{tier:g}",
            fix_hint=f"title 高对齐档位 {tt:g}（就近 {{17, 20}}）"))
    elif tt is None and tier is not None:
        findings.append(make(
            card, "LAYOUT2X4.TEMPLATE_DELTA",
            f"产物有 title 高 {tier:g}，指认模板 {verdict} 为 bare（无 title）",
            cid, severity=P1, expected="无 title", actual=f"title {tier:g}",
            fix_hint="bare 形态不应带 title bar"))
    # 槽位序列比对（结构差异各一条 + 同构槽位数值 delta）
    horizontal = tpl[0] == "row"
    for i, (t_kid, node) in enumerate(pairs):
        if horizontal:
            name = ("左栏", "右栏")[i] if i < 2 else f"第{i + 1}栏"
        else:
            name = ("上行", "下行")[i] if i < 2 else f"第{i + 1}行"
        _delta_slot_verdict(t_kid, node, name, card, findings)
    # 多余层/块（块数不符）
    if skipped:
        ids = ", ".join(str(b.comp.get("id")) for b in skipped)
        findings.append(make(
            card, "LAYOUT2X4.TEMPLATE_DELTA",
            f"槽位序列应为 {len(kids)} 槽（{verdict}），产物 {len(pairs) + len(skipped)} 块，"
            f"多出 {len(skipped)} 层/块（{ids}，模板无对应槽位）",
            cid, severity=P1, expected=f"{len(kids)} 槽", actual=f"多出 {len(skipped)} 层/块",
            fix_hint="按指认模板删除多余层/块，或并入相邻槽位"))
    # 块数不足（缺槽）
    if len(pairs) < len(kids):
        n_miss = len(kids) - len(pairs)
        findings.append(make(
            card, "LAYOUT2X4.TEMPLATE_DELTA",
            f"槽位序列应为 {len(kids)} 槽（{verdict}），产物仅 {len(pairs)} 块，缺 {n_miss} 槽",
            cid, severity=P1, expected=f"{len(kids)} 槽", actual=f"缺 {n_miss} 槽",
            fix_hint="按指认模板补齐缺失槽位"))
    _delta_closure(content, card, findings)
    return findings


@register("LAYOUT2X4.TEMPLATE_DELTA")
def check_template_delta(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """骨架命中（精确或拓扑归位）后逐槽位数值偏差量化（P1，程序已证实）。

    依据：owner 2026-08-24 路线 C 裁决 + 本轮逐卡指认（B-q65 title 20 vs 17 记
    delta+3；A-q20 命中 63:62 三列宽差与按钮高 32 vs 36 等）——匹配放宽后数值偏差
    由本规则独立报告，不再混在「未匹配」里。gap 口径：itemMargin 顶层生效
    （2026-08-24 五卡 dump 实证：q18 4→4.00 / q19·20·93 2→2.00 / q93 earbud 8、
    run 6 全吻合）。
    owner 人工指认卡（_MANUAL_VERDICTS，2026-08-24 终审）→ 改走 _check_verdict_delta：
    按指认模板比对（数值 + 结构级 delta，块数/嵌套不符各一条 P1）。"""
    slots = _slots(card, contract)
    if slots is None:
        return []
    if not _templates_ok(slots):
        return []
    tree = build_tree(card)
    verdict = _manual_verdict(card)
    if verdict is not None:
        return _check_verdict_delta(card, tree, verdict)
    content = _content_node(tree)
    if content is None:
        return []
    content_sk = _content_sk(content)
    hit = _find_variant(content_sk)
    if hit is not None:
        name, tpl = hit
        zone, tiers = _title_zone(content)
        tier = tiers[0] if zone else None
        align = _align_for_delta(content, tpl, k=1 if zone else 0)
    else:
        topo = _find_topology(content)
        if topo is None:
            return []  # 未登记形态：VARIANT_MATCH P2 报告，本规则静默
        name, tpl, align, _, tier = topo
    findings: List[Finding] = []
    # title 高（产物近似 title 就近档位 vs 模板家族档位）
    tt = _tpl_title_tier(name)
    if tt is not None:
        if tier is None:
            findings.append(make(
                card, "LAYOUT2X4.TEMPLATE_DELTA",
                f"缺 title bar（模板 {name} 为 {tt:g} 档；产物无 title 区域）",
                str(content.comp.get("id") or "content_root"), severity=P1,
                expected=f"title {tt:g}", actual="无",
                fix_hint=f"补 {tt:g}×296 title bar（含 Text 的 Row）"))
        elif abs(tier - tt) > _TOL:
            findings.append(make(
                card, "LAYOUT2X4.TEMPLATE_DELTA",
                f"title 高 {tier:g} vs 模板 {tt:g}（delta {tier - tt:+.0f}）",
                str(content.comp.get("id") or "content_root"), severity=P1,
                expected=f"title {tt:g}", actual=f"{tier:g}",
                fix_hint=f"title 高对齐档位 {tt:g}（就近 {17, 20}）"))
    elif tier is not None:
        findings.append(make(
            card, "LAYOUT2X4.TEMPLATE_DELTA",
            f"产物有 title 高 {tier:g}，模板 {name} 为 bare（无 title）",
            str(content.comp.get("id") or "content_root"), severity=P1,
            expected="无 title", actual=f"title {tier:g}",
            fix_hint="bare 形态不应带 title bar"))
    # 槽位尺寸（对齐；拓扑命中的对齐直接复用 _find_topology 的贪心结果）
    for t_kid, node in align:
        _delta_slot(t_kid, node, name, card, findings)
    _delta_closure(content, card, findings)
    return findings


def placement_meta(card: GenuiCard) -> dict:
    """2×4 卡归位模板信息（供编排层 check_card / 报告层消费，Idea2-WP-A 2026-08-26 收口）。

    只读复用本模块匹配函数（build_tree / _content_node / _content_sk /
    _find_variant / _find_topology / _manual_verdict），不改其逻辑；
    解析顺序与规则侧一致：人工指认表 → 精确匹配 → 拓扑归位。
    meta 为增强信息：任何异常降级为空 dict（报告层据此隐藏模板层），
    不影响检查主流程。
    """
    if card.card_size != "2x4":
        return {}
    try:
        verdict = _manual_verdict(card)
        if verdict is not None:
            return {"layout_2x4": {"template": verdict, "source": "manual"}}
        tree = build_tree(card)
        content = _content_node(tree)
        if content is None and tree is not None and len(tree.children) >= 2:
            content = tree  # root 即 content_root（B 系形态，与规则侧口径一致）
        info = {"template": None, "source": None}
        if content is not None:
            hit = _find_variant(_content_sk(content))
            if hit is not None:
                info = {"template": hit[0], "source": "algorithm"}
            else:
                topo = _find_topology(content)
                if topo is not None:
                    info = {"template": topo[0], "source": "algorithm"}
        return {"layout_2x4": info}
    except Exception:  # noqa: BLE001
        return {}
