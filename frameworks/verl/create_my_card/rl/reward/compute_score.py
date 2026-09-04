"""Unified no-gradient reward entry point for CreateMyCard Stage 0."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from frameworks.verl.create_my_card.data_pipeline.converters.compact_dsl_a2ui_converter import (
    CompactDslConversionError,
    convert_compact_dsl_to_a2ui,
    validate_compact_dsl_context,
)

from .content_coverage import (
    ContentRequirements,
    derive_card_spec,
    measure_content_coverage,
)
from .design_checker_adapter import (
    CheckerExecutionError,
    DesignCheckerAdapter,
)
from .schema import ComponentScore, GateResult, RewardAudit, require_normalized


DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "configs" / "reward_stage0.json"
_REQUIRED_COMPONENTS = (
    "contract",
    "content",
    "static_layout",
    "style",
    "efficiency",
)


@dataclass(frozen=True)
class RewardRequest:
    sample_id: str
    solution_str: str
    task_spec: Mapping[str, Any]
    content_labels: Mapping[str, Any] | None = None
    card_spec: Mapping[str, Any] | None = None
    finish_reason: str | None = None
    completion_tokens: int | None = None
    layout_path: Path | None = None
    include_delegated: bool = True


@dataclass
class RewardComputer:
    checker: DesignCheckerAdapter
    config_path: Path = DEFAULT_CONFIG
    config: dict[str, Any] = field(init=False)

    def __post_init__(self) -> None:
        self.config = _load_config(self.config_path)

    def compute(self, request: RewardRequest) -> RewardAudit:
        audit = RewardAudit(
            sample_id=request.sample_id,
            schema_version=self.config["schema_version"],
            status=self.config["status"],
        )
        if not isinstance(request.task_spec, Mapping):
            return self._metadata_failure(
                audit,
                reason="TaskSpec must be an object",
                error_type="invalid_task_spec",
            )
        size = request.task_spec.get("size")
        if size not in {"2x2", "2x4"}:
            return self._metadata_failure(
                audit,
                reason="TaskSpec.size must be one of: 2x2, 2x4",
                error_type="invalid_task_spec",
            )
        if not isinstance(request.task_spec.get("dataModelSchema"), Mapping):
            return self._metadata_failure(
                audit,
                reason="TaskSpec.dataModelSchema must be an object",
                error_type="invalid_task_spec",
            )
        for field_name in ("eventCandidates", "assetCandidates"):
            value = request.task_spec.get(field_name, [])
            if not isinstance(value, list):
                return self._metadata_failure(
                    audit,
                    reason=f"TaskSpec.{field_name} must be an array",
                    error_type="invalid_task_spec",
                )
        try:
            json.dumps(dict(request.task_spec), ensure_ascii=False, allow_nan=False)
            requirements = ContentRequirements.from_mapping(request.content_labels)
            if request.completion_tokens is not None and request.completion_tokens < 0:
                raise ValueError("completion_tokens must be non-negative")
            if request.card_spec is not None and not isinstance(request.card_spec, Mapping):
                raise ValueError("card_spec must be an object")
        except (TypeError, ValueError) as exc:
            return self._metadata_failure(
                audit,
                reason=str(exc),
                error_type="invalid_reward_metadata",
            )

        try:
            converted = convert_compact_dsl_to_a2ui(
                request.solution_str,
                size=size,
                protocol_profile={"version": "v0.9"},
            )
        except (CompactDslConversionError, TypeError, ValueError) as exc:
            return self._policy_failure(
                audit,
                gate="conversion",
                reason=str(exc),
                error_type=type(exc).__name__,
            )

        card_spec = (
            dict(request.card_spec)
            if request.card_spec is not None
            else derive_card_spec(request.task_spec)
        )
        context_error: str | None = None
        context_warnings: list[str] = []
        try:
            context = validate_compact_dsl_context(
                request.solution_str,
                task_spec=dict(request.task_spec),
                card_spec=card_spec,
            )
            context_warnings = list(context.warnings)
        except (CompactDslConversionError, TypeError, ValueError) as exc:
            # Conversion already succeeded. Remaining context failures are
            # illegal TaskSpec path/asset/event use and receive the plan's
            # non-compensable -0.5 cap, not the parse/conversion -1 reward.
            context_error = str(exc)

        audit.gates.append(GateResult("conversion", True, "continue"))
        content = measure_content_coverage(
            converted,
            task_spec=request.task_spec,
            requirements=requirements,
        )

        try:
            checker = self.checker.check(
                converted,
                sample_id=request.sample_id,
                task_spec=request.task_spec,
                query_text=str(request.task_spec.get("userQuery") or ""),
                layout_path=request.layout_path,
                include_delegated=(
                    request.include_delegated and request.layout_path is not None
                ),
            )
        except CheckerExecutionError as exc:
            audit.masked = True
            audit.retryable = exc.retryable
            audit.gates.append(
                GateResult("checker_environment", None, "mask_and_retry", str(exc))
            )
            audit.components = {
                "contract": self._component(
                    "contract",
                    1.0,
                    "converter gate; TaskSpec context reported separately",
                    {
                        "context_warnings": context_warnings,
                        "context_error": context_error,
                    },
                ),
                "content": self._component(
                    "content",
                    content.score,
                    "explicit primary labels+TaskSpec allowlists",
                    content.evidence,
                ),
                "static_layout": self._component(
                    "static_layout", None, "checker unavailable", {}
                ),
                "style": self._component("style", None, "checker unavailable", {}),
                "efficiency": self._efficiency_component(request),
            }
            audit.partial_score = _partial_score(audit.components)
            audit.diagnostics = {
                "checker_error": {
                    "kind": exc.kind,
                    "message": str(exc),
                    "attempts": exc.attempts,
                    "stderr": exc.stderr,
                }
            }
            return audit

        findings = list(checker.findings)
        audit.findings = findings
        contract_score, contract_evidence = _finding_family_score(
            findings,
            self.config["rule_families"]["contract"],
            self.config["severity_penalties"],
            penalized_evidence_types=set(self.config["penalized_evidence_types"]),
            layers={"L1"},
        )
        layout_score, layout_evidence = _finding_family_score(
            findings,
            self.config["rule_families"]["static_layout"],
            self.config["severity_penalties"],
            penalized_evidence_types=set(self.config["penalized_evidence_types"]),
            layers={"L1"},
        )
        style_score, style_evidence = _finding_family_score(
            findings,
            self.config["rule_families"]["style"],
            self.config["severity_penalties"],
            penalized_evidence_types=set(self.config["penalized_evidence_types"]),
            layers={"L1"},
        )

        l2_score: float | None = None
        l2_evidence: dict[str, Any] | None = None
        if checker.l2_evaluated:
            l2_score, l2_evidence = _l2_score(
                findings,
                self.config["severity_penalties"],
                penalized_evidence_types=set(self.config["penalized_evidence_types"]),
            )

        l2_blend = float(self.config.get("l2_layout_blend", 0.0))
        effective_layout_score = layout_score
        if l2_score is not None and l2_blend > 0.0:
            effective_layout_score = (
                (1.0 - l2_blend) * layout_score + l2_blend * l2_score
            )

        audit.components = {
            "contract": self._component(
                "contract",
                contract_score,
                "converter gate and checker L1 protocol/structure rules",
                {
                    **contract_evidence,
                    "context_warnings": context_warnings,
                    "context_error": context_error,
                },
            ),
            "content": self._component(
                "content",
                content.score,
                "explicit primary labels+TaskSpec allowlists",
                content.evidence,
            ),
            "static_layout": self._component(
                "static_layout",
                effective_layout_score,
                (
                    "checker L1/L2 blended visual-layout evidence"
                    if l2_score is not None and l2_blend > 0.0
                    else "checker L1 layout-family diagnostic proxy"
                ),
                {
                    **layout_evidence,
                    "l1_score": layout_score,
                    "l2_layout_blend": l2_blend if l2_score is not None else 0.0,
                    "l2_score": l2_score,
                    "limitation": (
                        "without a real card-app layout dump this remains a declared-layout "
                        "proxy; L2 occupancy is not human-calibrated"
                    ),
                },
            ),
            "style": self._component(
                "style",
                style_score,
                "checker L1 visual-token rule families",
                style_evidence,
            ),
            "efficiency": self._efficiency_component(request),
        }
        if l2_score is not None and l2_evidence is not None:
            audit.components["l2"] = ComponentScore(
                value=l2_score,
                weight=0.0,
                calibrated=False,
                source="dumpLayout L2a/L2b offline evidence",
                evidence=l2_evidence,
            )

        audit.partial_score = _partial_score(audit.components)
        if all(audit.components[name].value is not None for name in _REQUIRED_COMPONENTS):
            audit.score = sum(
                audit.components[name].contribution or 0.0
                for name in _REQUIRED_COMPONENTS
            )

        any_p0 = any(finding.get("severity") == "P0" for finding in findings)
        if any_p0:
            audit.gates.append(
                GateResult("checker_p0", False, "cap_at_0", "checker emitted P0")
            )
            if audit.score is not None:
                audit.score = min(audit.score, 0.0)
        else:
            audit.gates.append(GateResult("checker_p0", True, "continue"))

        critical_l2_rules = set(self.config.get("l2_critical_rule_ids", ()))
        critical_l2_findings = sorted(
            {
                str(finding.get("rule_id"))
                for finding in findings
                if checker.l2_evaluated
                and finding.get("layer") in {"L2a", "L2b"}
                and finding.get("rule_id") in critical_l2_rules
                and finding.get("severity") in {"P0", "P1"}
                and finding.get("evidence_type")
                in set(self.config["penalized_evidence_types"])
            }
        )
        if critical_l2_findings:
            audit.gates.append(
                GateResult(
                    "visual_integrity",
                    False,
                    "cap_at_0",
                    "critical L2 findings: " + ", ".join(critical_l2_findings),
                )
            )
            if audit.score is not None:
                audit.score = min(audit.score, 0.0)
        elif checker.l2_evaluated and critical_l2_rules:
            audit.gates.append(GateResult("visual_integrity", True, "continue"))
        elif critical_l2_rules:
            audit.gates.append(
                GateResult(
                    "visual_integrity",
                    None,
                    "audit_only",
                    "no L2 layout dump was provided",
                )
            )

        if context_error is not None:
            audit.gates.append(
                GateResult(
                    "taskspec_allowlist",
                    False,
                    "cap_at_-0.5",
                    context_error,
                )
            )
            audit.score = -0.5 if audit.score is None else min(audit.score, -0.5)
        else:
            audit.gates.append(
                GateResult("taskspec_allowlist", True, "continue")
            )

        if content.score is None:
            audit.gates.append(
                GateResult(
                    "content_labels",
                    None,
                    "audit_only",
                    content.evidence["label_status"],
                )
            )
        elif content.score < 1.0:
            audit.gates.append(
                GateResult(
                    "content_coverage",
                    False,
                    "cap_at_-0.5",
                    "primary recall, allowlist precision, or content budget failed",
                )
            )
            audit.score = -0.5 if audit.score is None else min(audit.score, -0.5)
        else:
            audit.gates.append(
                GateResult(
                    "content_visibility",
                    None,
                    "audit_only",
                    "static text-fit/L2 visibility has not been verified",
                )
            )

        audit.diagnostics = {
            "checker": checker.to_diagnostics(),
            "unmapped_findings": _unmapped_findings(
                findings,
                self.config["rule_families"],
                additional_prefixes=self.config["l2_rule_families"],
            ),
            "candidate_score_only": True,
        }
        audit.policy_update_eligible = self._policy_update_eligible(audit)
        return audit

    def _metadata_failure(
        self,
        audit: RewardAudit,
        *,
        reason: str,
        error_type: str,
    ) -> RewardAudit:
        audit.masked = True
        audit.retryable = False
        audit.gates.append(
            GateResult("reward_metadata", None, "mask_dataset_row", reason)
        )
        audit.components = {
            name: self._component(name, None, "invalid reward metadata", {})
            for name in _REQUIRED_COMPONENTS
        }
        audit.diagnostics = {
            "metadata_error": {"type": error_type, "message": reason}
        }
        return audit

    def _policy_failure(
        self,
        audit: RewardAudit,
        *,
        gate: str,
        reason: str,
        error_type: str,
    ) -> RewardAudit:
        audit.score = -1.0
        audit.gates.append(GateResult(gate, False, "hard_reward_-1", reason))
        audit.components = {
            "contract": self._component(
                "contract",
                0.0,
                "converter+TaskSpec context validation",
                {"error_type": error_type, "error": reason},
            ),
            "content": self._component("content", None, "contract gate failed", {}),
            "static_layout": self._component(
                "static_layout", None, "contract gate failed", {}
            ),
            "style": self._component("style", None, "contract gate failed", {}),
            "efficiency": self._component(
                "efficiency", None, "contract gate failed", {}
            ),
        }
        audit.partial_score = _partial_score(audit.components)
        audit.diagnostics = {"policy_error": {"type": error_type, "message": reason}}
        return audit

    def _component(
        self,
        name: str,
        value: float | None,
        source: str,
        evidence: Mapping[str, Any],
    ) -> ComponentScore:
        if value is not None:
            value = require_normalized(value, name)
        return ComponentScore(
            value=value,
            weight=float(self.config["weights"][name]),
            calibrated=name in self.config["calibrated_components"],
            source=source,
            evidence=evidence,
        )

    def _efficiency_component(self, request: RewardRequest) -> ComponentScore:
        evidence = {
            "finish_reason": request.finish_reason,
            "completion_tokens": request.completion_tokens,
        }
        if request.completion_tokens is None:
            value = None
            evidence["status"] = "missing_completion_tokens"
        elif request.completion_tokens < 0:
            raise ValueError("completion_tokens must be non-negative")
        else:
            settings = self.config["efficiency"]
            soft = int(settings["completion_tokens_soft_max"])
            hard = int(settings["completion_tokens_hard_max"])
            if request.finish_reason == "length" or request.completion_tokens >= hard:
                value = 0.0
            elif request.completion_tokens <= soft:
                value = 1.0
            else:
                value = (hard - request.completion_tokens) / (hard - soft)
            if "<think>" in request.solution_str.lower() or request.solution_str.lstrip().startswith("```"):
                value = 0.0
                evidence["unclean_output"] = True
        return self._component(
            "efficiency",
            value,
            "generation finish reason and completion-token length band",
            evidence,
        )

    def _policy_update_eligible(self, audit: RewardAudit) -> bool:
        if not self.config.get("policy_update_enabled", False):
            return False
        if audit.masked or audit.score is None:
            return False
        return all(
            audit.components[name].calibrated
            for name in _REQUIRED_COMPONENTS
        )


def _load_config(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid reward config: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("reward config root must be an object")
    weights = payload.get("weights")
    if not isinstance(weights, dict) or set(weights) != set(_REQUIRED_COMPONENTS):
        raise ValueError(f"reward weights must define exactly {_REQUIRED_COMPONENTS}")
    if abs(sum(float(value) for value in weights.values()) - 1.0) > 1e-9:
        raise ValueError("reward weights must sum to 1")
    policy_update_enabled = payload.get("policy_update_enabled")
    if not isinstance(policy_update_enabled, bool):
        raise ValueError("policy_update_enabled must be boolean")
    calibrated_components = payload.get("calibrated_components")
    if not isinstance(calibrated_components, list) or not all(
        isinstance(name, str) and name in _REQUIRED_COMPONENTS
        for name in calibrated_components
    ):
        raise ValueError(
            "calibrated_components must contain only known reward component names"
        )
    if len(set(calibrated_components)) != len(calibrated_components):
        raise ValueError("calibrated_components must not contain duplicates")
    if policy_update_enabled:
        if payload.get("status") != "validated_for_policy_update":
            raise ValueError(
                "an enabled reward must have status='validated_for_policy_update'"
            )
        if set(calibrated_components) != set(_REQUIRED_COMPONENTS):
            raise ValueError(
                "an enabled reward must calibrate every weighted component"
            )
    l2_blend = payload.get("l2_layout_blend", 0.0)
    if isinstance(l2_blend, bool) or not isinstance(l2_blend, (int, float)):
        raise ValueError("l2_layout_blend must be a number in [0, 1]")
    if not 0.0 <= float(l2_blend) <= 1.0:
        raise ValueError("l2_layout_blend must be in [0, 1]")
    critical_rules = payload.get("l2_critical_rule_ids", [])
    if not isinstance(critical_rules, list) or not all(
        isinstance(rule_id, str) and rule_id for rule_id in critical_rules
    ):
        raise ValueError("l2_critical_rule_ids must be an array of non-empty strings")
    return payload


def _finding_family_score(
    findings: Sequence[Mapping[str, Any]],
    prefixes: Sequence[str],
    penalties: Mapping[str, Any],
    *,
    penalized_evidence_types: set[str],
    layers: set[str] | None = None,
) -> tuple[float, dict[str, Any]]:
    selected = []
    excluded_evidence: list[str] = []
    seen: set[tuple[str, str]] = set()
    for finding in findings:
        rule_id = finding.get("rule_id")
        layer = finding.get("layer")
        if not isinstance(rule_id, str) or not any(
            rule_id.startswith(prefix) for prefix in prefixes
        ):
            continue
        if layers is not None and layer not in layers:
            continue
        evidence_type = finding.get("evidence_type")
        if evidence_type not in penalized_evidence_types:
            excluded_evidence.append(rule_id)
            continue
        element = finding.get("element")
        element_id = ""
        if isinstance(element, Mapping):
            element_id = str(
                element.get("dsl_id")
                or element.get("dump_id")
                or element.get("json_pointer")
                or ""
            )
        key = (rule_id, element_id)
        if key in seen:
            continue
        seen.add(key)
        selected.append(finding)

    counts = {severity: 0 for severity in penalties}
    rule_ids: list[str] = []
    penalty = 0.0
    for finding in selected:
        severity = finding.get("severity")
        if severity not in penalties:
            continue
        counts[severity] += 1
        penalty += float(penalties[severity])
        rule_ids.append(str(finding.get("rule_id")))
    return 1.0 - min(penalty, 1.0), {
        "deduplicated_counts": counts,
        "rule_ids": sorted(rule_ids),
        "excluded_by_evidence_type": sorted(excluded_evidence),
        "penalty": min(penalty, 1.0),
    }


def _l2_score(
    findings: Sequence[Mapping[str, Any]],
    penalties: Mapping[str, Any],
    *,
    penalized_evidence_types: set[str],
) -> tuple[float, dict[str, Any]]:
    dimensions = {
        "no_overlap": (0.30, ("GEOMETRY.OVERLAP", "GEOMETRY.AREA_CONTENT_TEXT_OVERLAP")),
        "no_overflow_or_text_squash": (
            0.25,
            (
                "GEOMETRY.SAFE_AREA_OVERFLOW",
                "GEOMETRY.TEXT_SQUASH",
                "GEOMETRY.BUTTON_SIZE",
                "RECONCILE.DIMENSION_DRIFT",
            ),
        ),
        "spacing": (0.15, ("GEOMETRY.SLOT_GAP", "GEOMETRY.LABEL_GAP")),
        "alignment": (
            0.15,
            (
                "GEOMETRY.AREA_TITLE_ALIGN",
                "GEOMETRY.BASELINE_MISMATCH",
                "GEOMETRY.AREA_TITLE_ICON_ANCHOR",
            ),
        ),
        "occupancy_and_bottom_anchor": (
            0.15,
            ("GEOMETRY.CONTENT_ALIGN_ANCHOR", "GEOMETRY.AREA_BOTTOM_ANCHOR"),
        ),
    }
    evidence: dict[str, Any] = {}
    scored_rule_prefixes = {
        rule_id
        for _, rule_ids in dimensions.values()
        for rule_id in rule_ids
    }
    total = 0.0
    for name, (weight, rule_ids) in dimensions.items():
        score, detail = _finding_family_score(
            findings,
            tuple(rule_ids),
            penalties,
            penalized_evidence_types=penalized_evidence_types,
            layers={"L2a", "L2b"},
        )
        total += weight * score
        evidence[name] = {"score": score, "weight": weight, **detail}
    evidence["limitation"] = (
        "occupancy uses bottom-anchor rules only; image-level occupancy and human "
        "calibration are pending"
    )
    evidence["unscored_l2_rule_ids"] = sorted(
        {
            str(finding.get("rule_id"))
            for finding in findings
            if finding.get("layer") in {"L2a", "L2b"}
            and isinstance(finding.get("rule_id"), str)
            and not any(
                str(finding.get("rule_id")).startswith(prefix)
                for prefix in scored_rule_prefixes
            )
        }
    )
    return total, evidence


def _partial_score(components: Mapping[str, ComponentScore]) -> float:
    return sum(
        component.contribution or 0.0
        for name, component in components.items()
        if name in _REQUIRED_COMPONENTS
    )


def _unmapped_findings(
    findings: Sequence[Mapping[str, Any]],
    families: Mapping[str, Sequence[str]],
    *,
    additional_prefixes: Sequence[str] = (),
) -> list[str]:
    prefixes = tuple(prefix for values in families.values() for prefix in values) + tuple(
        additional_prefixes
    )
    return sorted(
        {
            str(finding.get("rule_id"))
            for finding in findings
            if isinstance(finding.get("rule_id"), str)
            and not str(finding["rule_id"]).startswith(prefixes)
        }
    )
