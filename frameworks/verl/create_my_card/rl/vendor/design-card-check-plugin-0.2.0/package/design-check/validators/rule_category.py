"""规则 ID → 报告类别映射（WP-REPORT-CATEGORY）。

口径来源：能力清单三分组（review/EVAL299-capability-* ：①元素合法性 ②间距 ③布局骨架）
+ 用户四类要求（颜色 / 布局 / 尺寸 / 元素）。

匹配策略：精确 ID 优先（覆盖前缀兜底的例外，如 ``ICON.SIZE_CONTRACT``→尺寸、
``GEOMETRY.BUTTON_SIZE``→尺寸），其次前缀兜底；未识别规则返回 ``"其他"``，
不抛异常（新增规则忘配类别时兜底可见，但存量规则必须显式归位——见模块级断言）。

归类表（67 条存量规则全量，按用户定稿口径）：
- 颜色：``COLOR.*``（4）、``GRADIENT.*``（3）、``SCENE.*``（1）、``VISUAL.CONTRAST``、
  ``RECONCILE.COLOR_DRIFT`` / ``RECONCILE.OPACITY_DRIFT``（L2b 色值/透明度漂移）
- 布局：``LAYOUT2X4.*``（5）、``STRUCT.*``（3）、``SPACING.*``（2）、``DENSITY.*``（3）、
  ``SLOT.*``（3）、``AREA.*``（1）、``PROTOCOL.*``（4）、``GEOMETRY.*`` 除尺寸类外的
  全部 11 条（对齐/锚点/重叠/裁切/基线/安全区越界/槽位间距等）
- 尺寸：``ICON.SIZE_CONTRACT``、``GEOMETRY.BUTTON_SIZE``（geometry.py 中唯一含
  SIZE 的规则，已 grep 确认无 ``GEOMETRY.PROBE_SIZE``）、``SHAPE.*``（圆角半径档位 4）、
  ``TYPE.*``（字号档位/字重矩阵 3）、``RECONCILE.DIMENSION_DRIFT``（L2b 声明↔实测尺寸）
- 元素：``ICON.*`` 除 SIZE_CONTRACT 外（资源引用/扩展名/重复/多色染色 4）、
  ``ASSET.*``（4）、``CATALOG.*``（2）、``COPY.*``（文案字数 2）
- 其他：``SEMANTIC.*``（L3 语义层）与未识别规则

全量覆盖断言：映射表逐条对照实际注册规则集（``rules._RULES`` + geometry 静态列表
L2a + reconcile 静态列表 L2b），存量规则无一条落入「其他」（SEMANTIC.* 除外）；
新增未识别规则落「其他」是允许的兜底，但防存量漏配。
"""
from __future__ import annotations

from typing import Dict, Set

# ---------------------------------------------------------------------------
# 精确 ID 映射（优先于前缀兜底；覆盖会误判的例外）
# ---------------------------------------------------------------------------
_EXACT: Dict[str, str] = {
    "VISUAL.CONTRAST": "颜色",          # 对比度不足（颜色类）
    "ICON.SIZE_CONTRACT": "尺寸",        # 图标尺寸契约（前缀 ICON. 本应归元素）
    "GEOMETRY.BUTTON_SIZE": "尺寸",      # 按钮实测尺寸（前缀 GEOMETRY. 本应归布局）
    "RECONCILE.COLOR_DRIFT": "颜色",     # L2b 声明↔实测色值漂移
    "RECONCILE.OPACITY_DRIFT": "颜色",   # L2b 声明↔实测透明度漂移
    "RECONCILE.DIMENSION_DRIFT": "尺寸",  # L2b 声明↔实测尺寸漂移
}

# ---------------------------------------------------------------------------
# 前缀兜底映射（按注册前缀分组）
# ---------------------------------------------------------------------------
_PREFIX: Dict[str, str] = {
    # 颜色
    "COLOR.": "颜色",
    "GRADIENT.": "颜色",
    "SCENE.": "颜色",
    # 布局
    "LAYOUT2X4.": "布局",
    "STRUCT.": "布局",
    "SPACING.": "布局",
    "DENSITY.": "布局",
    "SLOT.": "布局",
    "AREA.": "布局",
    "PROTOCOL.": "布局",
    "GEOMETRY.": "布局",   # 尺寸例外（BUTTON_SIZE 等）已精确覆盖
    # 尺寸
    "SHAPE.": "尺寸",
    "TYPE.": "尺寸",
    # 元素
    "ICON.": "元素",       # 尺寸例外（SIZE_CONTRACT）已精确覆盖
    "ASSET.": "元素",
    "CATALOG.": "元素",
    "COPY.": "元素",
    # 其他（L3 语义层）
    "SEMANTIC.": "其他",
}

# ---------------------------------------------------------------------------
# 注册规则全集（模块级断言用）
# ---------------------------------------------------------------------------
#: L2a 几何规则静态列表（geometry.py 不注册进 rules._RULES，按 grep 实证 ID 落表）
GEOMETRY_RULES: Set[str] = {
    "GEOMETRY.SAFE_AREA_OVERFLOW", "GEOMETRY.OVERLAP", "GEOMETRY.BUTTON_SIZE",
    "GEOMETRY.SLOT_GAP", "GEOMETRY.LABEL_GAP", "GEOMETRY.CONTENT_ALIGN_ANCHOR",
    "GEOMETRY.BASELINE_MISMATCH", "GEOMETRY.AREA_TITLE_ALIGN",
    "GEOMETRY.AREA_CONTENT_TEXT_OVERLAP", "GEOMETRY.AREA_BOTTOM_ANCHOR",
    "GEOMETRY.AREA_TITLE_ICON_ANCHOR", "GEOMETRY.TEXT_SQUASH",
}
#: L2b 对账规则静态列表（reconcile_lib.py 同理不注册进 _RULES）
RECONCILE_RULES: Set[str] = {
    "RECONCILE.COLOR_DRIFT", "RECONCILE.OPACITY_DRIFT", "RECONCILE.DIMENSION_DRIFT",
}


def category_for(rule_id: str) -> str:
    """规则 ID → 类别：精确匹配优先，前缀兜底；未识别返回 "其他"（不抛异常）。"""
    if rule_id in _EXACT:
        return _EXACT[rule_id]
    for prefix, cat in _PREFIX.items():
        if rule_id.startswith(prefix):
            return cat
    return "其他"


def _registered_rule_ids() -> Set[str]:
    """规则注册全集：rules._RULES（L1/L3）+ geometry（L2a）+ reconcile（L2b）。"""
    from .rules import _RULES  # 同包内引用注册表（rules/__init__ 不反向 import 本模块）

    ids = set(_RULES)
    ids |= GEOMETRY_RULES
    ids |= RECONCILE_RULES
    return ids


def assert_full_coverage() -> None:
    """存量规则全量显式归位断言：无一条落入「其他」（SEMANTIC.* 除外）。

    同时反向核对：映射表条目必须都能对上注册规则集（防写错 ID 静默失效）。
    """
    registered = _registered_rule_ids()
    mapped_exact = set(_EXACT)
    unknown_in_map = sorted(mapped_exact - registered)
    if unknown_in_map:
        raise RuntimeError(
            f"rule_category 精确映射含未注册规则 ID: {unknown_in_map}——请核对规则名")
    uncovered = sorted(
        rid for rid in registered
        if not rid.startswith("SEMANTIC.") and category_for(rid) == "其他")
    if uncovered:
        raise RuntimeError(
            f"rule_category 存量规则未显式归位（落入「其他」）: {uncovered}——"
            f"新增规则请补映射表（精确或前缀），防报告类别列漏配")


assert_full_coverage()  # 模块级执行一次：防新规则加了忘配类别
