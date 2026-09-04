"""通用组件树工具（自 rules/icon.py 上提，Idea2-WP-A 2026-08-26）。

这些是 genui 扁平组件表（children 为 id 引用）的通用遍历/解析逻辑，
不是图标域规则；原私有名经 rules/icon.py re-export 保持兼容
（density/contrast/color/type_rule/shape/slot_rule 等消费方零改动）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..dsl import GenuiCard


def _comp_index(card: GenuiCard) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for comp in card.iter_components():
        cid = comp.get("id")
        if isinstance(cid, str):
            index[cid] = comp
    return index


def _parent_map(index: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    parents: Dict[str, Dict[str, Any]] = {}
    for comp in index.values():
        for child in comp.get("children") or []:
            cid = child if isinstance(child, str) else (
                child.get("id") if isinstance(child, dict) else None)
            if isinstance(cid, str) and cid in index:
                parents[cid] = comp
    return parents


def _resolved_children(index: Dict[str, Dict[str, Any]], comp: Dict[str, Any]
                       ) -> List[Dict[str, Any]]:
    """children 的真实组件列表（id 引用与嵌套 dict 双形态）。"""
    out: List[Dict[str, Any]] = []
    for child in comp.get("children") or []:
        if isinstance(child, str):
            real = index.get(child)
            if real is not None:
                out.append(real)
        elif isinstance(child, dict):
            out.append(child)
    return out


def _numeric_vp(value: Any) -> Optional[float]:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.endswith("vp"):
        try:
            return float(value[:-2])
        except ValueError:
            return None
    return None


def _nearest_clickable_ancestor(comp: Dict[str, Any], parents: Dict[str, Dict[str, Any]]
                                ) -> Optional[Dict[str, Any]]:
    node: Optional[Dict[str, Any]] = parents.get(comp.get("id"))
    seen = set()
    while node is not None and node.get("id") not in seen:
        seen.add(node.get("id"))
        if node.get("onClick"):
            return node
        node = parents.get(node.get("id"))
    return None


def _is_card_root(comp: Dict[str, Any]) -> bool:
    """卡根特征：无父组件，或宽高为 matchParent 的顶层容器。"""
    styles = comp.get("styles") or {}
    return styles.get("width") == "matchParent" or styles.get("height") == "matchParent"


def _is_button_like(ancestor: Dict[str, Any], parents: Dict[str, Dict[str, Any]]) -> bool:
    """按钮特征：非卡根的 clickable 元素，且带底色/圆角或小高度（≤48vp）。

    整卡点击（onClick 挂在 root）不把卡内图标变成 button-icon。
    """
    if _is_card_root(ancestor) or ancestor.get("id") not in parents:
        return False
    styles = ancestor.get("styles") or {}
    if styles.get("backgroundColor") or styles.get("borderRadius"):
        return True
    h = _numeric_vp(styles.get("height"))
    return h is not None and h <= 48
