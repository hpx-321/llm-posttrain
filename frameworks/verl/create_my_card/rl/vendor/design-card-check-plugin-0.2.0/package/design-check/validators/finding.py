"""统一诊断模型（开发计划 §3.1 finding schema）。

所有层（L1/L2a/L2b/L2c/L3）输出统一结构；报告、画廊与回归都消费它。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

#: 严重度
P0 = "P0"  # 阻塞（协议/结构错误、不可渲染、非法引用、内容溢出画布）
P1 = "P1"  # 规范硬性违规（token 档位外、密度/copyLimits 超限、渐变非法、几何违例、对比度不达标）
P2 = "P2"  # 建议级（对齐偏好、留白、视觉优化）

SEVERITY_ORDER = {P0: 0, P1: 1, P2: 2}

#: 证据类型
PROGRAM = "程序已证实"
MODEL = "模型推断"
DEVICE = "需端侧确认"

#: 层标识
L1 = "L1"
L2A = "L2a"
L2B = "L2b"
L2C = "L2c"
L3 = "L3"


@dataclass
class Element:
    dsl_id: Optional[str] = None
    json_pointer: str = ""
    dump_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"dsl_id": self.dsl_id, "json_pointer": self.json_pointer, "dump_id": self.dump_id}


@dataclass
class Finding:
    qid: str
    layer: str
    rule_id: str
    severity: str
    evidence_type: str
    element: Optional[Element] = None
    expected: str = ""
    actual: str = ""
    fix_hint: str = ""
    evidence_file: str = ""
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "qid": self.qid,
            "layer": self.layer,
            "rule_id": self.rule_id,
            "severity": self.severity,
            "evidence_type": self.evidence_type,
            "element": self.element.to_dict() if self.element else None,
            "expected": self.expected,
            "actual": self.actual,
            "fix_hint": self.fix_hint,
            "evidence_file": self.evidence_file,
            "message": self.message,
        }


def findings_to_dict(findings: List[Finding]) -> List[Dict[str, Any]]:
    return [f.to_dict() for f in findings]


def sort_findings(findings: List[Finding]) -> List[Finding]:
    return sorted(findings, key=lambda f: (SEVERITY_ORDER.get(f.severity, 9), f.rule_id))
