"""Versioned, JSON-safe schema for the Stage 0 reward audit.

The audit deliberately separates a candidate score from policy-update
eligibility.  Stage 0 weights are hypotheses until layout/content scores are
calibrated against L2 dumps and human preferences.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class ComponentScore:
    """One normalized reward component and the evidence behind it."""

    value: float | None
    weight: float
    calibrated: bool
    source: str
    evidence: Mapping[str, Any] = field(default_factory=dict)

    @property
    def contribution(self) -> float | None:
        if self.value is None:
            return None
        return self.value * self.weight

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["contribution"] = self.contribution
        payload["available"] = self.value is not None
        return payload


@dataclass(frozen=True)
class GateResult:
    """A non-compensable reward gate evaluated before weighted scoring."""

    name: str
    passed: bool | None
    action: str
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RewardAudit:
    """Complete output for one rollout.

    ``score`` is ``None`` when a required component is unavailable or the
    environment failed. ``partial_score`` never renormalizes missing weights;
    it exists for diagnostics only and must not be consumed by the optimizer.
    """

    sample_id: str
    schema_version: str
    status: str
    score: float | None = None
    partial_score: float = 0.0
    masked: bool = False
    retryable: bool = False
    policy_update_eligible: bool = False
    components: dict[str, ComponentScore] = field(default_factory=dict)
    gates: list[GateResult] = field(default_factory=list)
    findings: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "schema_version": self.schema_version,
            "status": self.status,
            "score": self.score,
            "partial_score": self.partial_score,
            "masked": self.masked,
            "retryable": self.retryable,
            "policy_update_eligible": self.policy_update_eligible,
            "components": {
                name: component.to_dict()
                for name, component in self.components.items()
            },
            "gates": [gate.to_dict() for gate in self.gates],
            "findings": self.findings,
            "diagnostics": self.diagnostics,
        }


def require_normalized(value: float, label: str) -> float:
    """Return a normalized float or fail instead of silently clipping bugs."""

    numeric = float(value)
    if not 0.0 <= numeric <= 1.0:
        raise ValueError(f"{label} must be in [0, 1], got {numeric}")
    return numeric
