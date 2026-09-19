# -*- coding: utf-8 -*-
"""Reverse final A2UI NDJSON to Design Compact DSL and verify roundtrips.

The reverse converter intentionally reads the frozen forward converter's private
protocol tables.  Keeping the two files together makes the token vocabulary and
normalization rules a single versioned unit instead of duplicating those rules.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # Package import.
    from . import compact_dsl_a2ui_converter as forward
    from .a2ui_to_compact import (
        _convert_parsed_a2ui_to_compact_dsl,
        _resolve_size,
        convert_a2ui_to_compact_dsl,
    )
    from .check_a2ui import parse_a2ui
    from .common import (
        A2uiReverseConversionError,
        ParsedA2ui,
        _read_json_object,
        _read_text,
    )
except ImportError:  # Direct script execution.
    import compact_dsl_a2ui_converter as forward
    from a2ui_to_compact import (
        _convert_parsed_a2ui_to_compact_dsl,
        _resolve_size,
        convert_a2ui_to_compact_dsl,
    )
    from check_a2ui import parse_a2ui
    from common import (
        A2uiReverseConversionError,
        ParsedA2ui,
        _read_json_object,
        _read_text,
    )


@dataclass(frozen=True)
class RoundtripResult:
    """Artifacts produced by one successful reverse/forward execution."""

    compact_dsl: str
    roundtrip_a2ui: str
    report: dict[str, Any]


@dataclass(frozen=True)
class _RoundtripVerification:
    """A forward-converted A2UI document and its differences from the source."""

    a2ui: str
    differences: list[dict[str, Any]]


def reverse_and_verify(
    a2ui: str,
    *,
    size: str | None = None,
    protocol_profile: dict[str, Any] | None = None,
    task_spec: dict[str, Any] | None = None,
    card_spec: dict[str, Any] | None = None,
    case_id: str | None = None,
    collapse_design_tokens: bool = True,
    collapse_color_tokens: bool = False,
    collapse_action_units: bool = True,
) -> RoundtripResult:
    """Reverse, validate, forward-convert, and compare one A2UI document."""

    parsed = parse_a2ui(a2ui)
    resolved_size = _resolve_size(parsed, size)
    compact_dsl = _convert_parsed_a2ui_to_compact_dsl(
        parsed,
        size=resolved_size,
        collapse_design_tokens=collapse_design_tokens,
        collapse_color_tokens=collapse_color_tokens,
        collapse_action_units=collapse_action_units,
    )

    context_status, warnings = _validate_compact_context(
        compact_dsl,
        task_spec=task_spec,
        card_spec=card_spec,
    )
    verification = _forward_and_compare(
        parsed,
        compact_dsl,
        size=resolved_size,
        protocol_profile=protocol_profile,
    )

    report = {
        "caseId": case_id,
        "size": resolved_size,
        "reverse": "pass",
        "compactValidation": "pass",
        "contextValidation": context_status,
        "forward": "pass",
        "roundtrip": "pass" if not verification.differences else "fail",
        "differences": verification.differences,
        "warnings": warnings,
        "sourceSha256": _sha256_text(a2ui),
        "compactSha256": _sha256_text(compact_dsl),
        "roundtripSha256": _sha256_text(verification.a2ui),
    }
    return RoundtripResult(compact_dsl, verification.a2ui, report)


def _validate_compact_context(
    compact_dsl: str,
    *,
    task_spec: dict[str, Any] | None,
    card_spec: dict[str, Any] | None,
) -> tuple[str, list[str]]:
    """Run optional TaskSpec/CardSpec validation for generated Compact DSL."""

    if task_spec is None and card_spec is None:
        return "not_run", []
    if task_spec is None or card_spec is None:
        raise A2uiReverseConversionError(
            "TaskSpec and CardSpec must be supplied together for context validation."
        )
    validation = forward.validate_compact_dsl_context(
        compact_dsl,
        task_spec=task_spec,
        card_spec=card_spec,
    )
    return "pass", list(validation.warnings)


def _forward_and_compare(
    parsed: ParsedA2ui,
    compact_dsl: str,
    *,
    size: str,
    protocol_profile: dict[str, Any] | None,
) -> _RoundtripVerification:
    """Forward-convert Compact DSL and compare canonical A2UI values."""

    profile = _roundtrip_profile(parsed, protocol_profile)
    roundtrip_a2ui = forward.convert_compact_dsl_to_a2ui(
        compact_dsl,
        size=size,
        protocol_profile=profile,
        surface_id=parsed.surface_id,
    )
    roundtrip_parsed = parse_a2ui(roundtrip_a2ui)
    source_value = _canonical_a2ui(parsed, size)
    roundtrip_value = _canonical_a2ui(roundtrip_parsed, size)
    differences: list[dict[str, Any]] = []
    _collect_differences(source_value, roundtrip_value, "$", differences)
    return _RoundtripVerification(roundtrip_a2ui, differences)


def _roundtrip_profile(
    parsed: ParsedA2ui,
    supplied: dict[str, Any] | None,
) -> dict[str, Any]:
    if supplied is not None and not isinstance(supplied, dict):
        raise A2uiReverseConversionError("protocol_profile must be an object.")
    profile = copy.deepcopy(supplied or {})
    supplied_version = profile.get("version")
    if supplied_version is not None and str(supplied_version) != parsed.version:
        raise A2uiReverseConversionError(
            "Protocol profile version does not match source A2UI version."
        )
    profile["version"] = parsed.version
    return profile


def _canonical_a2ui(parsed: ParsedA2ui, size: str) -> dict[str, Any]:
    create_surface = copy.deepcopy(parsed.create_surface)
    if "width" not in create_surface:
        create_surface.update(forward._surface_dimensions(size, {}))

    update = copy.deepcopy(parsed.update_components)
    update["components"] = [
        _canonical_component(parsed.components_by_id[component_id])
        for component_id in parsed.component_order
    ]
    return {
        "version": parsed.version,
        "createSurface": create_surface,
        "updateComponents": update,
        "updateDataModel": copy.deepcopy(parsed.update_data_model),
    }


def _canonical_component(component: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(component)
    if "onClick" in normalized:
        normalized["onClick"] = forward._convert_path_bindings(normalized["onClick"])
    return normalized


def _collect_differences(
    source: Any,
    roundtrip: Any,
    path: str,
    differences: list[dict[str, Any]],
    *,
    limit: int = 200,
) -> None:
    if len(differences) >= limit:
        return
    if isinstance(source, dict) and isinstance(roundtrip, dict):
        for key in sorted(set(source) | set(roundtrip)):
            child_path = f"{path}.{key}"
            if key not in source:
                differences.append(
                    {"path": child_path, "kind": "added", "roundtrip": roundtrip[key]}
                )
            elif key not in roundtrip:
                differences.append(
                    {"path": child_path, "kind": "removed", "source": source[key]}
                )
            else:
                _collect_differences(
                    source[key], roundtrip[key], child_path, differences, limit=limit
                )
        return
    if isinstance(source, list) and isinstance(roundtrip, list):
        for index in range(max(len(source), len(roundtrip))):
            child_path = f"{path}[{index}]"
            if index >= len(source):
                differences.append(
                    {"path": child_path, "kind": "added", "roundtrip": roundtrip[index]}
                )
            elif index >= len(roundtrip):
                differences.append(
                    {"path": child_path, "kind": "removed", "source": source[index]}
                )
            else:
                _collect_differences(
                    source[index], roundtrip[index], child_path, differences, limit=limit
                )
        return
    if source != roundtrip:
        differences.append(
            {"path": path, "kind": "changed", "source": source, "roundtrip": roundtrip}
        )


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_text(path: str | None, value: str) -> None:
    if path is None:
        return
    output = value.rstrip("\n") + "\n"
    if path == "-":
        sys.stdout.write(output)
        return
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(output, encoding="utf-8")


def _extract_size(
    explicit: str | None,
    task_spec: dict[str, Any] | None,
    card_spec: dict[str, Any] | None,
) -> str | None:
    if explicit is not None:
        return explicit
    candidates: list[str] = []
    for document in (card_spec, task_spec):
        if document is None:
            continue
        for key in ("suggestSize", "size"):
            value = document.get(key)
            if isinstance(value, str):
                candidates.append(value)
        nested = document.get("cardSpec")
        if isinstance(nested, dict):
            value = nested.get("suggestSize") or nested.get("size")
            if isinstance(value, str):
                candidates.append(value)
    unique = list(dict.fromkeys(candidates))
    if len(unique) > 1:
        raise A2uiReverseConversionError(
            f"TaskSpec/CardSpec contain conflicting sizes: {', '.join(unique)}."
        )
    return unique[0] if unique else None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reverse final A2UI to Compact DSL and verify a forward roundtrip."
    )
    parser.add_argument("--source-a2ui", required=True, help="A2UI file, or - for stdin.")
    parser.add_argument("--size", choices=tuple(forward._COMPACT_ROOT_DIMENSIONS))
    parser.add_argument("--task-spec")
    parser.add_argument("--card-spec")
    parser.add_argument("--protocol-profile")
    parser.add_argument("--case-id")
    parser.add_argument("--compact-out", default="-")
    parser.add_argument("--roundtrip-out")
    parser.add_argument("--report-out")
    parser.add_argument(
        "--collapse-color-tokens",
        action="store_true",
        help="Replace known Hex colors with deterministic semantic color tokens.",
    )
    parser.add_argument(
        "--no-design-tokens",
        action="store_true",
        help="Keep all design styles explicit.",
    )
    parser.add_argument(
        "--no-action-units",
        action="store_true",
        help="Do not collapse strict generated action structures to ActionUnit.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report: dict[str, Any] | None = None
    try:
        source = _read_text(args.source_a2ui)
        task_spec = _read_json_object(args.task_spec, "TaskSpec")
        card_spec = _read_json_object(args.card_spec, "CardSpec")
        if card_spec is None and isinstance(task_spec, dict):
            nested = task_spec.get("cardSpec")
            if isinstance(nested, dict):
                card_spec = nested
        size = _extract_size(args.size, task_spec, card_spec)
        result = reverse_and_verify(
            source,
            size=size,
            protocol_profile=_read_json_object(
                args.protocol_profile, "protocol profile"
            ),
            task_spec=task_spec if card_spec is not None else None,
            card_spec=card_spec,
            case_id=args.case_id,
            collapse_design_tokens=not args.no_design_tokens,
            collapse_color_tokens=args.collapse_color_tokens,
            collapse_action_units=not args.no_action_units,
        )
        report = result.report
        _write_text(args.compact_out, result.compact_dsl)
        _write_text(args.roundtrip_out, result.roundtrip_a2ui)
        if args.report_out:
            _write_text(
                args.report_out,
                json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
            )
        if report["roundtrip"] != "pass":
            print("roundtrip verification failed", file=sys.stderr)
            return 1
        return 0
    except (
        A2uiReverseConversionError,
        forward.CompactDslConversionError,
        json.JSONDecodeError,
        OSError,
    ) as exc:
        report = {
            "caseId": args.case_id,
            "reverse": "fail",
            "compactValidation": "not_run",
            "contextValidation": "not_run",
            "forward": "not_run",
            "roundtrip": "fail",
            "differences": [],
            "errors": [str(exc)],
        }
        if args.report_out:
            try:
                _write_text(
                    args.report_out,
                    json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
                )
            except OSError:
                pass
        print(f"reverse conversion failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
