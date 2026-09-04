"""Measure whether grouped SFT rollouts produce a useful reward signal.

This is an audit tool, not a training gate.  It checks mechanical properties
such as group shape and score variance, while deliberately keeping the final
"ready for RL" decision false until high/low candidates pass visual review.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize greedy+sample reward variance by TaskSpec group."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--expected-samples", type=int, default=8)
    parser.add_argument("--zero-variance-epsilon", type=float, default=1e-9)
    parser.add_argument("--minimum-visual-signal-fraction", type=float, default=0.50)
    parser.add_argument("--max-abs-reward-token-correlation", type=float, default=0.80)
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{line_number}: row must be an object")
            rows.append(row)
    if not rows:
        raise ValueError(f"audit file is empty: {path}")
    return rows


def analyze_groups(
    rows: Sequence[Mapping[str, Any]],
    *,
    expected_samples: int = 8,
    zero_variance_epsilon: float = 1e-9,
    minimum_visual_signal_fraction: float = 0.50,
    max_abs_reward_token_correlation: float = 0.80,
) -> dict[str, Any]:
    if expected_samples < 1:
        raise ValueError("expected_samples must be positive")
    if zero_variance_epsilon < 0:
        raise ValueError("zero_variance_epsilon must be non-negative")
    if not 0.0 <= minimum_visual_signal_fraction <= 1.0:
        raise ValueError("minimum_visual_signal_fraction must be in [0, 1]")
    if not 0.0 <= max_abs_reward_token_correlation <= 1.0:
        raise ValueError("max_abs_reward_token_correlation must be in [0, 1]")

    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for index, row in enumerate(rows, start=1):
        group_id = row.get("group_id") or row.get("groupId")
        if not isinstance(group_id, str) or not group_id:
            raise ValueError(f"row {index}: missing non-empty group_id")
        grouped[group_id].append(row)

    group_reports: list[dict[str, Any]] = []
    structure_error_groups: list[str] = []
    all_score_token_pairs: list[tuple[float, float]] = []
    conversion_passed = 0
    masked_count = 0
    missing_score_count = 0

    for row in rows:
        if bool(row.get("masked")):
            masked_count += 1
        if _numeric(row.get("score")) is None:
            missing_score_count += 1
        if not bool(row.get("masked")) and _gate_passed(row, "conversion"):
            conversion_passed += 1
        score = _numeric(row.get("score"))
        tokens = _completion_tokens(row)
        if score is not None and tokens is not None:
            all_score_token_pairs.append((score, float(tokens)))

    for group_id in sorted(grouped):
        candidates = grouped[group_id]
        greedy = [row for row in candidates if row.get("sampling_mode") == "greedy"]
        sampled = [row for row in candidates if row.get("sampling_mode") == "sample"]
        errors: list[str] = []
        if len(greedy) != 1:
            errors.append(f"expected 1 greedy candidate, got {len(greedy)}")
        elif greedy[0].get("candidate_index") != 0:
            errors.append("greedy candidate_index must be 0")
        if len(sampled) != expected_samples:
            errors.append(
                f"expected {expected_samples} sampled candidates, got {len(sampled)}"
            )
        candidate_indices = [row.get("candidate_index") for row in sampled]
        if not all(
            isinstance(candidate_index, int) and not isinstance(candidate_index, bool)
            for candidate_index in candidate_indices
        ):
            errors.append("sample candidate_index values must be integers")
        elif sorted(candidate_indices) != list(range(expected_samples)):
            errors.append(
                "sample candidate_index must be exactly "
                f"0..{expected_samples - 1}, got {candidate_indices}"
            )
        if errors:
            structure_error_groups.append(group_id)

        scored = [
            (str(row.get("sample_id") or ""), score)
            for row in candidates
            if (score := _numeric(row.get("score"))) is not None
        ]
        score_values = [score for _, score in scored]
        score_range = max(score_values) - min(score_values) if score_values else None
        score_std = statistics.pstdev(score_values) if score_values else None
        best = max(scored, key=lambda item: item[1]) if scored else (None, None)
        worst = min(scored, key=lambda item: item[1]) if scored else (None, None)
        greedy_score = _numeric(greedy[0].get("score")) if len(greedy) == 1 else None
        sampled_scores = [
            score
            for row in sampled
            if (score := _numeric(row.get("score"))) is not None
        ]
        best_sampled = max(sampled_scores) if sampled_scores else None

        component_ranges: dict[str, float] = {}
        component_names = sorted(
            {
                name
                for row in candidates
                for name in _component_values(row)
            }
        )
        for name in component_names:
            values = [
                value
                for row in candidates
                if (value := _component_values(row).get(name)) is not None
            ]
            if values:
                component_ranges[name] = max(values) - min(values)

        group_reports.append(
            {
                "group_id": group_id,
                "candidate_count": len(candidates),
                "structure_errors": errors,
                "scored_count": len(score_values),
                "score_min": worst[1],
                "score_max": best[1],
                "score_range": score_range,
                "score_std": score_std,
                "distinct_scores_1e-6": len({round(value, 6) for value in score_values}),
                "zero_variance": (
                    score_range is not None and score_range <= zero_variance_epsilon
                ),
                "best_candidate_id": best[0],
                "worst_candidate_id": worst[0],
                "greedy_score": greedy_score,
                "best_sampled_score": best_sampled,
                "best_sampled_minus_greedy": (
                    best_sampled - greedy_score
                    if best_sampled is not None and greedy_score is not None
                    else None
                ),
                "component_ranges": component_ranges,
            }
        )

    zero_variance_groups = [
        report["group_id"] for report in group_reports if report["zero_variance"]
    ]
    valid_std = [
        report["score_std"]
        for report in group_reports
        if report["score_std"] is not None
    ]
    group_count = len(group_reports)
    candidate_count = len(rows)
    conversion_rate = conversion_passed / candidate_count
    zero_variance_fraction = len(zero_variance_groups) / group_count
    visual_signal_groups = [
        report["group_id"]
        for report in group_reports
        if max(
            report["component_ranges"].get("static_layout", 0.0),
            report["component_ranges"].get("style", 0.0),
        )
        > zero_variance_epsilon
    ]
    visual_signal_fraction = len(visual_signal_groups) / group_count
    reward_token_pearson = _pearson(all_score_token_pairs)
    suspicious_token_correlation = (
        reward_token_pearson is not None
        and abs(reward_token_pearson) > max_abs_reward_token_correlation
    )
    machine_gate_passed = (
        not structure_error_groups
        and masked_count == 0
        and missing_score_count == 0
        and conversion_rate >= 0.95
        and zero_variance_fraction <= 0.50
        and visual_signal_fraction >= minimum_visual_signal_fraction
        and not suspicious_token_correlation
    )
    return {
        "schema_version": "create-my-card.reward-group-analysis.v1",
        "summary": {
            "group_count": group_count,
            "candidate_count": candidate_count,
            "expected_candidates_per_group": expected_samples + 1,
            "structure_error_groups": structure_error_groups,
            "masked_count": masked_count,
            "missing_score_count": missing_score_count,
            "conversion_passed": conversion_passed,
            "conversion_rate": conversion_rate,
            "zero_variance_groups": zero_variance_groups,
            "zero_variance_fraction": zero_variance_fraction,
            "mean_group_score_std": statistics.fmean(valid_std) if valid_std else None,
            "visual_signal_groups": visual_signal_groups,
            "visual_signal_fraction": visual_signal_fraction,
            "minimum_visual_signal_fraction": minimum_visual_signal_fraction,
            "reward_token_pearson": reward_token_pearson,
            "max_abs_reward_token_correlation": max_abs_reward_token_correlation,
            "suspicious_reward_token_correlation": suspicious_token_correlation,
            "machine_gate_passed": machine_gate_passed,
            "ready_for_policy_update": False,
            "readiness_reason": (
                "machine checks passed; visual high/low preference and selective L2 review "
                "are still required"
                if machine_gate_passed
                else "mechanical reward-signal checks failed; inspect group details"
            ),
        },
        "groups": group_reports,
    }


def render_markdown(report: Mapping[str, Any], *, source: Path) -> str:
    summary = report["summary"]
    lines = [
        "# Reward group audit",
        "",
        f"Source: `{source}`",
        "",
        "## Summary",
        "",
        f"- Groups: {summary['group_count']}",
        f"- Candidates: {summary['candidate_count']}",
        f"- Conversion rate: {summary['conversion_rate']:.2%}",
        f"- Zero-variance groups: {len(summary['zero_variance_groups'])} "
        f"({summary['zero_variance_fraction']:.2%})",
        f"- Mean within-group score std: {_format_number(summary['mean_group_score_std'])}",
        f"- Groups with layout/style variance: {len(summary['visual_signal_groups'])} "
        f"({summary['visual_signal_fraction']:.2%})",
        f"- Reward/token Pearson: {_format_number(summary['reward_token_pearson'])}",
        f"- Suspicious reward/token correlation: "
        f"{'YES' if summary['suspicious_reward_token_correlation'] else 'no'}",
        f"- Mechanical gate: {'PASS' if summary['machine_gate_passed'] else 'FAIL'}",
        "- Policy update: **NOT ENABLED**",
        "",
        "> Passing the mechanical gate only proves that the reward varies. It does not "
        "prove that higher-scored cards look better. Review the best/worst candidates "
        "and run selective L2 rendering before training.",
        "",
        "## Groups",
        "",
        "| Group | Range | Std | Distinct | Greedy | Best sampled | Errors |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for group in report["groups"]:
        errors = "; ".join(group["structure_errors"]) or "-"
        lines.append(
            f"| {group['group_id']} | {_format_number(group['score_range'])} | "
            f"{_format_number(group['score_std'])} | {group['distinct_scores_1e-6']} | "
            f"{_format_number(group['greedy_score'])} | "
            f"{_format_number(group['best_sampled_score'])} | {errors} |"
        )
    return "\n".join(lines) + "\n"


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _gate_passed(row: Mapping[str, Any], gate_name: str) -> bool:
    gates = row.get("gates")
    if not isinstance(gates, list):
        return False
    return any(
        isinstance(gate, Mapping)
        and gate.get("name") == gate_name
        and gate.get("passed") is True
        for gate in gates
    )


def _completion_tokens(row: Mapping[str, Any]) -> int | None:
    components = row.get("components")
    if not isinstance(components, Mapping):
        return None
    efficiency = components.get("efficiency")
    if not isinstance(efficiency, Mapping):
        return None
    evidence = efficiency.get("evidence")
    if not isinstance(evidence, Mapping):
        return None
    value = evidence.get("completion_tokens")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _component_values(row: Mapping[str, Any]) -> dict[str, float | None]:
    components = row.get("components")
    if not isinstance(components, Mapping):
        return {}
    return {
        str(name): _numeric(component.get("value"))
        for name, component in components.items()
        if isinstance(component, Mapping)
    }


def _pearson(pairs: Iterable[tuple[float, float]]) -> float | None:
    values = list(pairs)
    if len(values) < 2:
        return None
    xs = [value[0] for value in values]
    ys = [value[1] for value in values]
    x_mean = statistics.fmean(xs)
    y_mean = statistics.fmean(ys)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in values)
    x_scale = math.sqrt(sum((x - x_mean) ** 2 for x in xs))
    y_scale = math.sqrt(sum((y - y_mean) ** 2 for y in ys))
    denominator = x_scale * y_scale
    return numerator / denominator if denominator else None


def _format_number(value: Any) -> str:
    numeric = _numeric(value)
    return "-" if numeric is None else f"{numeric:.4f}"


def main() -> int:
    args = parse_args()
    report = analyze_groups(
        read_jsonl(args.input),
        expected_samples=args.expected_samples,
        zero_variance_epsilon=args.zero_variance_epsilon,
        minimum_visual_signal_fraction=args.minimum_visual_signal_fraction,
        max_abs_reward_token_correlation=args.max_abs_reward_token_correlation,
    )
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    args.output_md.write_text(
        render_markdown(report, source=args.input), encoding="utf-8"
    )
    print(json.dumps(report["summary"], ensure_ascii=False, allow_nan=False))
    return 0 if report["summary"]["machine_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
