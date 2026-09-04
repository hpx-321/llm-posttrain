"""SLOT.* —— 槽模型完整性（F1，DESIGN.md §Slot Model L1410-1440）。

依据（DESIGN.md 行号，以实际 grep 为准）：
- L1412：卡片内容必须映射到 title-area / content-area / button-area 三个区域，自上而下槽序；
- L1414：title-area 是必选槽，由可选 leading-icon 与必选 title-text 组成；
  leading-icon 一卡至多两个（左上 12vp 一个 + 右上 20vp 一个）；
- L1416：content-area 是必选槽，承载主信息或主视觉；
- L1430：所有尺寸都必须保留显式 content-area 容器，不得用自定义容器替代该槽位。

槽结构静态判定口径（2026-08-22 扫 93 条语料 + 第一次评测 A/B/C 分支抽样确认）：
- 语料主流形态：root 的唯一子节点是 `*_contract` 容器（= content-area 容器），
  title 区 = 容器第一个子节点（Row 或 Text，71/93 为 icon+text 的 Row，22/93 为裸 Text），
  action 区 = 容器内含 onClick 的子树（Button，93 条中 19 条各 1 个，均为末位子节点）；
- 第一次评测形态：root 直接持有 title_area / value_row / bottom_area 命名子槽，
  仍按「容器第一个子节点 = title 区、末位 = action 区」的同一口径判定；
- 模板分支（C）形态：root → root_0(root_0_0)… 全宽（matchParent/100%）Column/Row/Stack
  包壳链（2026-08-22 实测 41/41 卡均为此形态，深 1~3 层）——槽容器定位时向下穿透
  包壳（上限 3 层）到有效容器，再套用同一口径；穿透深度超限或穿透后仍判定不了则
  按原「宁缺毋滥」跳过不报。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from validators.dsl import GenuiCard
from validators.finding import Finding, P1
from validators.rules import register
from validators.rules._common import make
from validators.core.tree import _comp_index, _parent_map, _resolved_children

_CONTAINERS = ("Column", "Row", "Stack")
#: 全宽包壳标记：width/height 为 matchParent 或 100%
_FULL = ("matchParent", "100%")
#: 包壳穿透深度上限（C 分支模板形态实测最深 3 层）
PIERCE_DEPTH = 3


def _is_wrapper(comp: Dict[str, Any]) -> bool:
    """包壳容器：Column/Row/Stack 且宽或高为 matchParent/100% 的全宽包装层。"""
    if comp.get("component") not in _CONTAINERS:
        return False
    styles = comp.get("styles") or {}
    return styles.get("width") in _FULL or styles.get("height") in _FULL


def _pierce_wrappers(container: Dict[str, Any], index: Dict[str, Dict[str, Any]],
                     depth: int = PIERCE_DEPTH) -> Dict[str, Any]:
    """沿「唯一子节点且为全宽容器」的包壳链向下穿透，返回有效槽容器。"""
    for _ in range(depth):
        kids = _resolved_children(index, container)
        if len(kids) == 1 and _is_wrapper(kids[0]):
            container = kids[0]
        else:
            break
    return container


def _find_root(index: Dict[str, Dict[str, Any]], parents: Dict[str, Dict[str, Any]]
               ) -> Optional[Dict[str, Any]]:
    if "root" in index:
        return index["root"]
    for cid, comp in index.items():
        if cid not in parents:
            return comp
    return None


def _container_of(root: Dict[str, Any], index: Dict[str, Dict[str, Any]]) -> Tuple[
        Dict[str, Any], bool]:
    """返回 (槽位有效容器, 是否 `*_contract` 显式 content-area 容器)。

    语料形态：root 唯一子节点为 *_contract（L1430 要求的显式 content-area 容器）；
    第一次评测形态：root 直接持有命名子槽，此时容器即 root 自身；
    模板分支（C）形态：root 唯一子节点是 root_0/root_0_0… 全宽包壳链，
    沿包壳向下穿透（上限 PIERCE_DEPTH 层）到有效容器再判定。
    """
    kids = _resolved_children(index, root)
    if len(kids) == 1 and str(kids[0].get("id") or "").endswith("_contract"):
        return _pierce_wrappers(kids[0], index), True
    return _pierce_wrappers(root, index), False


def _subtree_has(index: Dict[str, Dict[str, Any]], comp: Dict[str, Any],
                 pred) -> bool:
    for child in _resolved_children(index, comp):
        if pred(child):
            return True
        if _subtree_has(index, child, pred):
            return True
    return False


def _title_zone(container: Dict[str, Any], index: Dict[str, Dict[str, Any]]
                ) -> Optional[Dict[str, Any]]:
    """title 区 = 容器第一个子节点；容器无子节点返回 None（判定不了跳过）。"""
    kids = _resolved_children(index, container)
    return kids[0] if kids else None


def _action_children(container: Dict[str, Any], index: Dict[str, Dict[str, Any]],
                     root_id: str) -> List[int]:
    """返回含 onClick（非卡根）的子树在容器子节点中的下标列表。"""
    out: List[int] = []
    for i, child in enumerate(_resolved_children(index, container)):
        if child.get("id") == root_id:
            continue
        if child.get("onClick") or _subtree_has(index, child, lambda c: bool(c.get("onClick"))):
            out.append(i)
    return out


@register("SLOT.MODEL_REQUIRED")
def check_model_required(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """title-text / content-area 是必选槽（§L1414 / L1416 / L1430）。

    判定：
    - title-text 缺失：title 区（容器首子）为已知容器形态但子树无任何 Text，
      或首子为裸 Image/Button 等非文本形态（裸 Text 视为 title-text 本体）；
    - content-area 缺失：*_contract 容器（或 root 直接作容器时）只有 title 区一个子节点，
      且该子节点不是「内含多子节点的包壳容器」——后者可能是合法包装形态，跳过不报。
    """
    findings: List[Finding] = []
    index = _comp_index(card)
    parents = _parent_map(index)
    root = _find_root(index, parents)
    if root is None:
        return []
    container, is_contract = _container_of(root, index)
    kids = _resolved_children(index, container)
    if not kids:
        return []
    # --- title-text 必选 ---
    first = kids[0]
    if first.get("component") == "Text":
        pass  # 裸 Text 即 title-text
    elif first.get("component") in _CONTAINERS:
        if not _subtree_has(index, first, lambda c: c.get("component") == "Text"):
            findings.append(
                make(
                    card, "SLOT.MODEL_REQUIRED",
                    "title-area 缺必选 title-text：title 区（容器首子）内没有任何 Text",
                    first.get("id"), severity=P1,
                    expected="title 区包含 title-text（DESIGN.md §Slot Model L1414）",
                    actual=f"title 区 {first.get('id')} 无 Text",
                    fix_hint="在标题区补一个 12vp 的 title-text（body-s-regular）",
                )
            )
    elif first.get("component") in ("Image", "Button", "Progress"):
        # 首子是裸非文本节点：结构可判，按缺 title-text 报（icon-only 标题行 / 动作占位）
        findings.append(
            make(
                card, "SLOT.MODEL_REQUIRED",
                f"title-area 缺必选 title-text：容器首子是裸 {first.get('component')}，非 Text 也非含文本容器",
                first.get("id"), severity=P1,
                expected="title 区包含 title-text（DESIGN.md §Slot Model L1414）",
                actual=f"首子 {first.get('id')} [{first.get('component')}]",
                fix_hint="在标题区补一个 12vp 的 title-text（body-s-regular）",
            )
        )
    # else: 未知形态跳过（宁缺毋滥）
    # --- content-area 必选 ---
    if len(kids) < 2:
        wrapper = (
            not is_contract
            and len(kids) == 1
            and kids[0].get("component") in _CONTAINERS
            and len(_resolved_children(index, kids[0])) >= 2
        )
        if not wrapper:
            findings.append(
                make(
                    card, "SLOT.MODEL_REQUIRED",
                    "content-area 缺失：槽位容器除 title 区外没有任何内容子节点",
                    container.get("id"), severity=P1,
                    expected="content-area 必选槽存在（DESIGN.md §Slot Model L1416/L1430）",
                    actual=f"容器 {container.get('id')} 仅有 {len(kids)} 个子节点",
                    fix_hint="补 content-area 承载主信息/主视觉，并保留显式 content-area 容器",
                )
            )
    return findings


@register("SLOT.ORDER")
def check_slot_order(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """槽序合法：title → content → action（§L1412 自上而下映射）。

    判定：action 子树（含非卡根 onClick）必须位于槽位容器末位；
    action 之前出现非 action 内容、或 action 不位于末位 → 槽序错乱。
    """
    index = _comp_index(card)
    parents = _parent_map(index)
    root = _find_root(index, parents)
    if root is None:
        return []
    container, _ = _container_of(root, index)
    root_id = root.get("id")
    action_idx = _action_children(container, index, root_id)
    kids = _resolved_children(index, container)
    if not kids or not action_idx:
        return []
    last = action_idx[-1]
    if last != len(kids) - 1:
        offender = kids[last + 1]
        return [
            make(
                card, "SLOT.ORDER",
                f"槽序错乱：action 区（含 onClick 的子树）不在末位，其后还有内容节点",
                offender.get("id"), severity=P1,
                expected="槽序 title-area → content-area → button-area（§L1412）",
                actual=f"action 子树位于下标 {last}，其后仍有 {offender.get('id')}",
                fix_hint="把按钮/动作区移至槽位容器末位，保持 title → content → action 槽序",
            )
        ]
    return []


@register("SLOT.LEADING_ICON_COUNT")
def check_leading_icon_count(card: GenuiCard, contract: Dict, query: str) -> List[Finding]:
    """leading-icon 一卡至多两个（左上 12vp 一个 + 右上 20vp 一个，§L1414）。

    判定：title 区（容器首子）子树内的 Image 计数；>2 即违规。
    环中心、按钮内、hero 等非标题区图标不计入（各有独立契约）。
    """
    index = _comp_index(card)
    parents = _parent_map(index)
    root = _find_root(index, parents)
    if root is None:
        return []
    container, _ = _container_of(root, index)
    title = _title_zone(container, index)
    if title is None:
        return []
    icons: List[str] = []
    if title.get("component") == "Image":
        icons.append(title.get("id"))
    elif title.get("component") in _CONTAINERS:
        for child in _resolved_children(index, title):
            if child.get("component") == "Image":
                icons.append(child.get("id"))
            elif child.get("component") in _CONTAINERS:
                icons.extend(
                    c.get("id") for c in _resolved_children(index, child)
                    if c.get("component") == "Image"
                )
    if len(icons) > 2:
        return [
            make(
                card, "SLOT.LEADING_ICON_COUNT",
                f"title 区出现 {len(icons)} 个 leading-icon > 上限 2",
                icons[2], severity=P1,
                expected="leading-icon ≤ 2（左上 12vp 一个 + 右上 20vp 一个，§L1414）",
                actual=f"{len(icons)} 个: {', '.join(icons)}",
                fix_hint="最多保留左上前置 12vp + 右上 20vp 两个 leading-icon，其余移除",
            )
        ]
    return []
