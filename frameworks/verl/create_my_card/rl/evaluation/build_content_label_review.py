#!/usr/bin/env python3
"""Build a human-review template for Stage 0 primary-content labels."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT))

from frameworks.verl.create_my_card.data_pipeline.converters.compact_dsl_a2ui_converter import (  # noqa: E402
    convert_compact_dsl_to_a2ui,
    validate_compact_dsl_context,
)
from frameworks.verl.create_my_card.rl.reward.content_coverage import (  # noqa: E402
    ContentRequirements,
    derive_card_spec,
    measure_content_coverage,
)


SFT_SOURCE = PROJECT_ROOT / "frameworks" / "verl" / "create_my_card" / "sft" / "data" / "source"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--taskspec", type=Path, default=SFT_SOURCE / "taskspec.json")
    parser.add_argument(
        "--compact-dsl",
        type=Path,
        default=SFT_SOURCE / "design_compact_dsl.jsonl",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.output.exists():
        raise SystemExit(f"error: output already exists: {args.output}")
    if args.limit is not None and args.limit < 1:
        raise SystemExit("error: --limit must be positive")
    task_specs = _load_task_specs(args.taskspec)
    compact_rows = _load_compact_rows(args.compact_dsl)
    if set(task_specs) != set(compact_rows):
        missing_gold = sorted(set(task_specs) - set(compact_rows))
        missing_task = sorted(set(compact_rows) - set(task_specs))
        raise ValueError(
            f"source ids differ; missing_gold={missing_gold[:10]}, "
            f"missing_task={missing_task[:10]}"
        )

    review_rows: list[dict[str, Any]] = []
    for sample_id, task_spec in task_specs.items():
        if args.limit is not None and len(review_rows) >= args.limit:
            break
        compact_dsl = compact_rows[sample_id]
        converted = convert_compact_dsl_to_a2ui(
            compact_dsl,
            size=str(task_spec["size"]),
            protocol_profile={"version": "v0.9"},
        )
        validate_compact_dsl_context(
            compact_dsl,
            task_spec=task_spec,
            card_spec=derive_card_spec(task_spec),
        )
        evidence = measure_content_coverage(
            converted,
            task_spec=task_spec,
            requirements=ContentRequirements(),
        ).evidence
        review_rows.append(
            {
                "id": sample_id,
                "reviewed": False,
                "user_query": task_spec.get("userQuery", ""),
                "gold_evidence": {
                    "bound_paths": evidence["used_paths"],
                    "literal_texts": evidence["visible_literal_texts"],
                    "assets": evidence["used_assets"],
                    "event_calls": evidence["used_event_calls"],
                },
                "required_primary_paths": [],
                "required_primary_texts": [],
                "required_event_calls": [],
                "required_events": [],
                "reference_content_budget": {"facts_min": 1, "facts_max": 3},
                "review_notes": "",
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(review_rows, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "rows": len(review_rows),
                "reviewed": 0,
                "output": str(args.output.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _load_task_specs(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, list):
        raise ValueError("TaskSpec source must be an array")
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"TaskSpec record {index} must be an object")
        sample_id = item.get("id")
        task_spec = item.get("taskSpec")
        if not isinstance(sample_id, str) or not isinstance(task_spec, dict):
            raise ValueError(f"TaskSpec record {index} has invalid id/taskSpec")
        if sample_id in result:
            raise ValueError(f"duplicate TaskSpec id: {sample_id}")
        result[sample_id] = task_spec
    return result


def _load_compact_rows(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    with path.open("r", encoding="utf-8-sig") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            if not raw_line.strip():
                continue
            item = json.loads(raw_line)
            sample_id = item.get("id") if isinstance(item, dict) else None
            compact_dsl = item.get("designCompactDsl") if isinstance(item, dict) else None
            if not isinstance(sample_id, str) or not isinstance(compact_dsl, str):
                raise ValueError(f"Compact DSL line {line_number} has invalid id/payload")
            if sample_id in result:
                raise ValueError(f"duplicate Compact DSL id: {sample_id}")
            result[sample_id] = compact_dsl
    return result


if __name__ == "__main__":
    raise SystemExit(main())
