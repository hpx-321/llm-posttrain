"""L1 声明层规则集（对应开发计划 §7 错误示例 E-01~E-13 的静态部分）。

规则签名：``run(card, contract, query) -> list[Finding]``
- card:      GenuiCard
- contract:  design_contract.load_design_contract() 归一化契约
- query:     用户原始 query（用于无模型时的场景-渐变启发式）
"""
from __future__ import annotations

from typing import Callable, Dict, List

from ..dsl import GenuiCard
from ..finding import Finding

RuleFn = Callable[[GenuiCard, Dict, str], List[Finding]]

_RULES: Dict[str, RuleFn] = {}


def register(rule_id: str):
    def deco(fn: RuleFn) -> RuleFn:
        _RULES[rule_id] = fn
        return fn

    return deco


def all_l1_rules() -> Dict[str, RuleFn]:
    return {k: v for k, v in _RULES.items() if not k.startswith("SEMANTIC.")}


#: L3 语义启发式（模型推断；计划中属 L3 层）
def all_l3_heuristics() -> Dict[str, RuleFn]:
    return {k: v for k, v in _RULES.items() if k.startswith("SEMANTIC.")}


def run_l1(card: GenuiCard, contract: Dict, query: str = "", include_semantic: bool = False) -> List[Finding]:
    findings: List[Finding] = []
    for rule_id, fn in _RULES.items():
        if rule_id.startswith("SEMANTIC.") and not include_semantic:
            continue
        try:
            findings.extend(fn(card, contract, query) or [])
        except Exception as exc:  # 单条规则异常不阻断整卡
            findings.append(
                Finding(
                    qid=card.case_id,
                    layer=("L3" if rule_id.startswith("SEMANTIC.") else "L1"),
                    rule_id=rule_id,
                    severity="P1",
                    evidence_type="程序已证实",
                    message=f"规则执行异常: {exc}",
                )
            )
    return findings


def run_l3_heuristics(card: GenuiCard, contract: Dict, query: str = "") -> List[Finding]:
    """运行语义启发式（L3，模型推断）。"""
    findings: List[Finding] = []
    for rule_id, fn in all_l3_heuristics().items():
        try:
            for f in fn(card, contract, query) or []:
                f.layer = "L3"
                findings.append(f)
        except Exception as exc:
            findings.append(Finding(qid=card.case_id, layer="L3", rule_id=rule_id,
                                    severity="P2", evidence_type="模型推断", message=f"规则执行异常: {exc}"))
    return findings


# ---------------------------------------------------------------------------
# 五包模块装载（Idea2-WP-B 2026-08-26）：规则模块物理迁移至 packages/ 五包，
# 注册表机制不变。导入顺序保持迁移前的字母序，确保 _RULES 插入顺序
# （即 run_l1 的 findings 顺序）与历史基线逐字节一致。
# ---------------------------------------------------------------------------
import sys as _sys

# 注：icon 需先于 area_rule/slot_rule 导入——迁移前 slot_rule 顶部 ``from .icon
# import ...`` 使 ICON.* 先于 SLOT.* 注册（slot_rule 现改依赖 core.tree）。
# 为保持 _RULES 插入顺序（run_l1 findings 顺序）与历史基线逐字节一致，
# 此处显式提前导入 icon。
from packages.pkg_elements import icon  # noqa: E402,F401
from packages.pkg_spacing import area_rule  # noqa: E402,F401
from packages.pkg_elements import asset  # noqa: E402,F401
from packages.pkg_elements import catalog_rule  # noqa: E402,F401
from packages.pkg_elements import color  # noqa: E402,F401
from packages.pkg_elements import contrast  # noqa: E402,F401
from packages.pkg_elements import copy  # noqa: E402,F401
from packages.pkg_spacing import density  # noqa: E402,F401
from packages.pkg_elements import gradient  # noqa: E402,F401
from packages.pkg_skeleton import layout_2x4  # noqa: E402,F401
from packages.pkg_protocol import protocol  # noqa: E402,F401
from packages.pkg_elements import scene  # noqa: E402,F401
from packages.pkg_elements import shape  # noqa: E402,F401
from packages.pkg_spacing import slot_rule  # noqa: E402,F401
from packages.pkg_spacing import spacing  # noqa: E402,F401
from packages.pkg_elements import type_rule  # noqa: E402,F401

# 兼容别名：validators.rules.<module> 旧路径经 sys.modules 别名指向五包内真实
# 模块（from validators.rules.icon import X 等存量调用零改动）。
for _name in ("area_rule", "asset", "catalog_rule", "color", "contrast", "copy",
              "density", "gradient", "icon", "layout_2x4", "protocol", "scene",
              "shape", "slot_rule", "spacing", "type_rule"):
    _sys.modules[f"validators.rules.{_name}"] = globals()[_name]

del _sys, _name
