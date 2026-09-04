#!/usr/bin/env python3
"""Build a fixed, reviewed TaskSpec canary parquet for reward calibration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


SFT_DIR = Path(__file__).resolve().parents[2] / "sft"
if __package__:
    from ...sft.dataset import build_parquet
else:
    import sys

    sys.path.insert(0, str(SFT_DIR))
    from dataset import build_parquet


EVALUATION_DIR = Path(__file__).resolve().parent
DEFAULT_TASKSPEC = SFT_DIR / "data" / "source" / "taskspec.json"
DEFAULT_SYSTEM_PROMPT = SFT_DIR / "data" / "source" / "system_prompt.md"
DEFAULT_LABELS = EVALUATION_DIR / "fixtures" / "content_labels_canary_16_diverse.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--taskspec-file", type=Path, default=DEFAULT_TASKSPEC)
    parser.add_argument("--labels-file", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--system-prompt", type=Path, default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def load_json_array(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid {label} JSON: {path}") from exc
    if not isinstance(payload, list) or not payload:
        raise ValueError(f"{label} must be a non-empty JSON array")
    if not all(isinstance(row, dict) for row in payload):
        raise ValueError(f"every {label} row must be an object")
    return payload


def build_rows(
    *,
    task_rows: Sequence[Mapping[str, Any]],
    label_rows: Sequence[Mapping[str, Any]],
    system_prompt: str,
) -> list[dict[str, Any]]:
    tasks: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(task_rows, start=1):
        sample_id = row.get("id")
        task_spec = row.get("taskSpec")
        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError(f"TaskSpec row {index}: invalid id")
        if sample_id in tasks:
            raise ValueError(f"duplicate TaskSpec id: {sample_id}")
        if not isinstance(task_spec, Mapping):
            raise ValueError(f"{sample_id}: taskSpec must be an object")
        tasks[sample_id] = task_spec

    rows: list[dict[str, Any]] = []
    selected: set[str] = set()
    for index, label in enumerate(label_rows, start=1):
        sample_id = label.get("id")
        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError(f"label row {index}: invalid id")
        if sample_id in selected:
            raise ValueError(f"duplicate label id: {sample_id}")
        if label.get("reviewed") is not True:
            raise ValueError(f"{sample_id}: canary label is not reviewed")
        if label.get("verification_status") != "passed":
            raise ValueError(f"{sample_id}: canary label verification did not pass")
        task_spec = tasks.get(sample_id)
        if task_spec is None:
            raise ValueError(f"{sample_id}: no matching TaskSpec")
        if task_spec.get("size") not in {"2x2", "2x4"}:
            raise ValueError(f"{sample_id}: unsupported TaskSpec size")
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append(
            {
                "role": "user",
                "content": build_parquet.canonicalize_taskspec(dict(task_spec)),
            }
        )
        rows.append(
            {"id": sample_id, "messages": messages, "enable_thinking": False}
        )
        selected.add(sample_id)
    return rows


def main() -> int:
    args = parse_args()
    task_rows = load_json_array(args.taskspec_file, "TaskSpec")
    label_rows = load_json_array(args.labels_file, "content label")
    system_prompt = build_parquet.load_system_prompt(args.system_prompt)
    rows = build_rows(
        task_rows=task_rows,
        label_rows=label_rows,
        system_prompt=system_prompt,
    )
    build_parquet.write_parquet(rows, args.output)
    print(
        json.dumps(
            {
                "path": str(args.output.resolve()),
                "count": len(rows),
                "ids": [row["id"] for row in rows],
            },
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
