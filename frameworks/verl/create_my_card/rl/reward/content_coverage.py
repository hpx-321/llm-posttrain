"""Deterministic content/allowlist evidence for a converted card.

This module intentionally does not infer primary facts from the user query.
Primary labels require an offline derivation and human spot-check, as specified
by the reward plan. Missing labels therefore produce an unavailable content
score instead of a misleading pass.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from frameworks.verl.create_my_card.data_pipeline.converters.compact_dsl_a2ui_converter import (
    normalize_task_event_value,
)


_BINDING_RE = re.compile(r"\$\{(/[^{}\s]+)\}")
_HIDDEN_VISIBILITY = {"false", "gone", "hidden", "none"}
_DISPLAY_FIELDS = {"content", "label", "value", "total", "src", "select"}


@dataclass(frozen=True)
class ContentRequirements:
    required_primary_paths: tuple[str, ...] = ()
    required_primary_texts: tuple[str, ...] = ()
    required_event_calls: tuple[str, ...] = ()
    required_events: tuple[dict[str, Any], ...] = ()
    facts_min: int = 1
    facts_max: int = 3
    labels_provided: bool = False
    reviewed: bool = False

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "ContentRequirements":
        if value is None:
            return cls()
        budget = value.get("reference_content_budget")
        if not isinstance(budget, Mapping):
            budget = {}
        paths = _string_tuple(value.get("required_primary_paths"), "required_primary_paths")
        texts = _string_tuple(value.get("required_primary_texts"), "required_primary_texts")
        calls = _string_tuple(value.get("required_event_calls"), "required_event_calls")
        events = _event_tuple(value.get("required_events"), "required_events")
        facts_min = _non_negative_int(budget.get("facts_min", 1), "facts_min")
        facts_max = _non_negative_int(budget.get("facts_max", 3), "facts_max")
        if facts_max < facts_min:
            raise ValueError("reference_content_budget.facts_max must be >= facts_min")
        reviewed = value.get("reviewed") is True
        labels_provided = reviewed and any(
            key in value
            for key in (
                "required_primary_paths",
                "required_primary_texts",
                "required_event_calls",
                "required_events",
            )
        )
        return cls(
            required_primary_paths=paths,
            required_primary_texts=texts,
            required_event_calls=calls,
            required_events=events,
            facts_min=facts_min,
            facts_max=facts_max,
            labels_provided=labels_provided,
            reviewed=reviewed,
        )


@dataclass(frozen=True)
class ContentCoverage:
    score: float | None
    primary_recall: float | None
    allowed_precision: float
    content_pass: bool | None
    evidence: dict[str, Any]


def derive_card_spec(task_spec: Mapping[str, Any]) -> dict[str, Any]:
    """Build the minimum CardSpec capability roots required by context validation.

    SFT TaskSpec data does not carry CardSpec. The root is derived only from
    declared top-level ``dataModelSchema`` keys; converter schema validation
    still rejects paths outside the detailed TaskSpec schema.
    """

    schema = task_spec.get("dataModelSchema")
    if not isinstance(schema, Mapping):
        return {"dataBindings": []}
    root_children: Mapping[str, Any] = schema
    if str(schema.get("type") or "").lower() == "object" and isinstance(
        schema.get("properties"), Mapping
    ):
        root_children = schema["properties"]
    descriptor_keys = {"type", "properties", "items", "required", "description"}
    bindings = [
        {"writeResultTo": f"/{key}"}
        for key in root_children
        if isinstance(key, str) and key and key not in descriptor_keys
    ]
    return {"dataBindings": bindings}


def measure_content_coverage(
    converted_a2ui: str,
    *,
    task_spec: Mapping[str, Any],
    requirements: ContentRequirements,
) -> ContentCoverage:
    components = _load_components(converted_a2ui)
    visible_components = [component for component in components if _is_visible(component)]

    used_paths = sorted(
        {
            path
            for component in visible_components
            for field, value in component.items()
            if field in _DISPLAY_FIELDS
            for path in _binding_paths(value)
        }
    )
    used_assets = sorted(
        {
            source
            for component in visible_components
            if component.get("component") in {"Image", "ActionUnit"}
            for source in [component.get("src") or component.get("icon")]
            if isinstance(source, str) and source
        }
    )
    used_events = [
        normalize_task_event_value(handler)
        for component in visible_components
        for handler in _event_handlers(component.get("onClick"))
    ]
    used_event_calls = sorted(
        {
            handler["call"]
            for handler in used_events
            if isinstance(handler.get("call"), str)
        }
    )
    used_event_keys = {_stable_json(handler) for handler in used_events}
    visible_literal_texts = list(dict.fromkeys(_visible_literal_text(visible_components)))
    visible_text = "\n".join(visible_literal_texts)

    schema = task_spec.get("dataModelSchema")
    allowed_assets = _allowed_assets(task_spec)
    allowed_events = _allowed_events(task_spec)
    violations = {
        "paths": sorted(path for path in used_paths if not _schema_has_path(schema, path)),
        "assets": sorted(source for source in used_assets if source not in allowed_assets),
        "events": [
            handler
            for handler in used_events
            if _stable_json(handler) not in allowed_events
        ],
    }
    actual_allowlisted = len(used_paths) + len(used_assets) + len(used_events)
    violation_count = sum(len(items) for items in violations.values())
    allowed_precision = (
        1.0
        if actual_allowlisted == 0
        else (actual_allowlisted - violation_count) / actual_allowlisted
    )

    path_hits = sorted(set(requirements.required_primary_paths) & set(used_paths))
    text_hits = sorted(
        text for text in requirements.required_primary_texts if text in visible_text
    )
    event_call_hits = sorted(
        set(requirements.required_event_calls) & set(used_event_calls)
    )
    event_hits = [
        handler
        for handler in requirements.required_events
        if _stable_json(handler) in used_event_keys
    ]
    required_count = (
        len(requirements.required_primary_paths)
        + len(requirements.required_primary_texts)
        + len(requirements.required_event_calls)
        + len(requirements.required_events)
    )
    hit_count = len(path_hits) + len(text_hits) + len(event_call_hits) + len(event_hits)
    primary_recall = hit_count / required_count if required_count else None

    if not requirements.reviewed:
        score = None
        content_pass = None
        label_status = "primary_labels_not_reviewed"
    elif not requirements.labels_provided:
        score = None
        content_pass = None
        label_status = "missing_primary_labels"
    elif required_count == 0 and requirements.facts_min > 0:
        score = None
        content_pass = None
        label_status = "empty_primary_labels_with_positive_budget"
    else:
        recall_for_score = 1.0 if primary_recall is None else primary_recall
        budget_ok = requirements.facts_min <= len(used_paths) <= requirements.facts_max
        score = recall_for_score * allowed_precision * (1.0 if budget_ok else 0.0)
        # L2/text-fit visibility is not available in this first-stage module.
        if score < 1.0:
            content_pass = False
        else:
            content_pass = None
        label_status = "provided_visibility_unverified"

    return ContentCoverage(
        score=score,
        primary_recall=primary_recall,
        allowed_precision=allowed_precision,
        content_pass=content_pass,
        evidence={
            "label_status": label_status,
            "required_primary_paths": list(requirements.required_primary_paths),
            "required_primary_texts": list(requirements.required_primary_texts),
            "required_event_calls": list(requirements.required_event_calls),
            "required_events": list(requirements.required_events),
            "matched_primary_paths": path_hits,
            "matched_primary_texts": text_hits,
            "matched_event_calls": event_call_hits,
            "matched_events": event_hits,
            "used_paths": used_paths,
            "used_assets": used_assets,
            "used_event_calls": used_event_calls,
            "used_events": used_events,
            "visible_literal_texts": visible_literal_texts,
            "allowed_precision": allowed_precision,
            "violations": violations,
            "reference_content_budget": {
                "facts_min": requirements.facts_min,
                "facts_max": requirements.facts_max,
                "observed_bound_paths": len(used_paths),
            },
            "primary_text_fit": None,
            "visibility_verified_by_l2": False,
        },
    )


def _load_components(converted_a2ui: str) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(converted_a2ui.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            message = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"converted A2UI line {line_number} is invalid JSON") from exc
        update = message.get("updateComponents") if isinstance(message, dict) else None
        rows = update.get("components") if isinstance(update, dict) else None
        if isinstance(rows, list):
            components.extend(row for row in rows if isinstance(row, dict))
    return components


def _is_visible(component: Mapping[str, Any]) -> bool:
    styles = component.get("styles")
    if not isinstance(styles, Mapping):
        return True
    visibility = styles.get("visibility")
    if visibility is None:
        return True
    return str(visibility).strip().lower() not in _HIDDEN_VISIBILITY


def _binding_paths(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield from _BINDING_RE.findall(value)
    elif isinstance(value, Mapping):
        path = value.get("path")
        if isinstance(path, str) and path.startswith("/"):
            yield path
        for child in value.values():
            yield from _binding_paths(child)
    elif isinstance(value, list):
        for child in value:
            yield from _binding_paths(child)


def _visible_literal_text(components: Iterable[Mapping[str, Any]]) -> Iterable[str]:
    for component in components:
        for field in ("content", "label"):
            value = component.get(field)
            if not isinstance(value, str) or _BINDING_RE.search(value):
                continue
            if value.strip():
                yield value


def _event_handlers(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [handler for handler in value if isinstance(handler, dict)]


def _schema_has_path(schema: Any, path: str) -> bool:
    """Match the converter's concrete-list and JSON-Schema properties/items walk."""

    if not isinstance(path, str) or not path.startswith("/"):
        return False
    current = schema
    for raw_token in path.split("/")[1:]:
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, Mapping):
            schema_type = str(current.get("type") or "").lower()
            if schema_type == "array":
                items = current.get("items")
                if not token.isdigit():
                    return False
                if isinstance(items, (Mapping, list)):
                    current = items
                    continue
                return False
            if schema_type == "object":
                properties = current.get("properties")
                if isinstance(properties, Mapping) and token in properties:
                    current = properties[token]
                    continue
                return False
            if token in current:
                current = current[token]
                continue
            return False
        if isinstance(current, list):
            if not token.isdigit() or not current:
                return False
            index = int(token)
            if index >= len(current):
                return False
            current = current[index]
            continue
        return False
    return True


def _allowed_assets(task_spec: Mapping[str, Any]) -> set[str]:
    candidates = task_spec.get("assetCandidates")
    if not isinstance(candidates, list):
        return set()
    return {
        source
        for candidate in candidates
        if isinstance(candidate, Mapping)
        for source in [candidate.get("src")]
        if isinstance(source, str) and source
    }


def _allowed_events(task_spec: Mapping[str, Any]) -> set[str]:
    candidates = task_spec.get("eventCandidates")
    if not isinstance(candidates, list):
        return set()
    allowed: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            continue
        call = candidate.get("call")
        args = candidate.get("args")
        if not isinstance(call, str) or not isinstance(args, Mapping):
            action = candidate.get("action")
            if isinstance(action, Mapping):
                call = action.get("call")
                args = action.get("args")
        if isinstance(call, str) and isinstance(args, Mapping):
            allowed.add(
                _stable_json(
                    {
                        "call": call,
                        "args": normalize_task_event_value(dict(args)),
                    }
                )
            )
    return allowed


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _string_tuple(value: Any, label: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{label} must be a list of non-empty strings")
    return tuple(dict.fromkeys(item.strip() for item in value))


def _event_tuple(value: Any, label: str) -> tuple[dict[str, Any], ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list of event handler objects")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, Mapping):
            raise ValueError(f"{label}[{index}] must be an event handler object")
        call = item.get("call")
        args = item.get("args")
        if not isinstance(call, str) or not call.strip():
            raise ValueError(f"{label}[{index}].call must be a non-empty string")
        if not isinstance(args, Mapping):
            raise ValueError(f"{label}[{index}].args must be an object")
        normalized = {
            "call": call,
            "args": normalize_task_event_value(dict(args)),
        }
        key = _stable_json(normalized)
        if key not in seen:
            seen.add(key)
            result.append(normalized)
    return tuple(result)


def _non_negative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value
