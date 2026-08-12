#!/usr/bin/env python3
"""Build CreateMyCard TaskSpec inference-input parquet files."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import build_parquet


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SYSTEM_PROMPT = BASE_DIR / "data" / "source" / "system_prompt.md"
DEFAULT_OUTPUT_DIR = BASE_DIR / "data" / "parquet"
DEFAULT_SOURCE_URL = (
    "https://raw.githubusercontent.com/InnovationTea/CreateMyCard/"
    "main/testdata/taskspec/taskspec_cases.json"
)
TASKSPEC_FIELD_ORDER = (
    "userQuery",
    "size",
    "dataModelSchema",
    "eventCandidates",
    "assetCandidates",
)
EXPECTED_FIELDS = frozenset(TASKSPEC_FIELD_ORDER)
TARGET_SIZE = "2x2"


class TestDataError(ValueError):
    """Raised when the upstream inference input violates the data contract."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--source-file",
        type=Path,
        help="Use a previously downloaded taskspec_cases.json instead of GitHub.",
    )
    source.add_argument(
        "--source-url",
        default=DEFAULT_SOURCE_URL,
        help="Raw GitHub URL used when --source-file is omitted.",
    )
    parser.add_argument("--system-prompt", type=Path, default=DEFAULT_SYSTEM_PROMPT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def read_source_bytes(source_file: Path | None, source_url: str) -> tuple[bytes, str]:
    if source_file is not None:
        if not source_file.is_file():
            raise TestDataError(f"source file does not exist: {source_file}")
        return source_file.read_bytes(), str(source_file.resolve())

    request = urllib.request.Request(
        source_url,
        headers={"User-Agent": "llm-posttrain-create-my-card-eval/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read(), source_url
    except (urllib.error.URLError, TimeoutError) as exc:
        raise TestDataError(
            "failed to download the TaskSpec test source; download it manually and "
            "pass --source-file"
        ) from exc


def decode_and_validate_source(raw: bytes) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TestDataError("TaskSpec test source is not valid UTF-8 JSON") from exc
    if not isinstance(payload, list) or not payload:
        raise TestDataError("TaskSpec test source must be a non-empty JSON array")

    records: list[dict[str, Any]] = []
    for index, item in enumerate(payload, start=1):
        label = f"TaskSpec test record {index}"
        if not isinstance(item, dict):
            raise TestDataError(f"{label} must be an object")
        if set(item) != EXPECTED_FIELDS:
            raise TestDataError(
                f"{label} fields must be exactly {sorted(EXPECTED_FIELDS)}, got {sorted(item)}"
            )
        if not isinstance(item["userQuery"], str) or not item["userQuery"].strip():
            raise TestDataError(f"{label}.userQuery must be a non-empty string")
        if item["size"] not in {"2x2", "2x4"}:
            raise TestDataError(f"{label}.size is unsupported: {item['size']!r}")
        if not isinstance(item["eventCandidates"], list):
            raise TestDataError(f"{label}.eventCandidates must be an array")
        if not isinstance(item["assetCandidates"], list):
            raise TestDataError(f"{label}.assetCandidates must be an array")
        if not isinstance(item["dataModelSchema"], dict):
            raise TestDataError(f"{label}.dataModelSchema must be an object")
        try:
            json.dumps(item, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise TestDataError(f"{label} is not strict JSON: {exc}") from exc
        records.append(item)
    return records


def build_rows(system_prompt: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, task_spec in enumerate(records, start=1):
        ordered_task_spec = {field: task_spec[field] for field in TASKSPEC_FIELD_ORDER}
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append(
            {
                "role": "user",
                "content": build_parquet.canonicalize_taskspec(ordered_task_spec),
            }
        )
        rows.append(
            {
                "id": f"taskspec-{index:03d}",
                "messages": messages,
                "enable_thinking": False,
            }
        )
    return rows


def build_test_dataset(args: argparse.Namespace) -> dict[str, Any]:
    raw, source_location = read_source_bytes(args.source_file, args.source_url)
    source_records = decode_and_validate_source(raw)
    records = [record for record in source_records if record["size"] == TARGET_SIZE]
    if not records:
        raise TestDataError(f"upstream source contains no {TARGET_SIZE} TaskSpec records")
    system_prompt = build_parquet.load_system_prompt(args.system_prompt)
    rows = build_rows(system_prompt, records)
    output_path = args.output_dir / "test.parquet"
    stale_paths = []
    for stale_name in ("test_2x2.parquet", "test_2x4.parquet"):
        stale_path = args.output_dir / stale_name
        if stale_path.is_symlink():
            raise TestDataError(f"refusing to remove stale symlink: {stale_path}")
        if stale_path.exists():
            if not stale_path.is_file():
                raise TestDataError(f"stale output is not a file: {stale_path}")
            stale_paths.append(stale_path)

    build_parquet.write_parquet(rows, output_path)
    for stale_path in stale_paths:
        stale_path.unlink()
    return {
        "path": str(output_path.resolve()),
        "count": len(rows),
        "source": source_location,
    }


def main() -> None:
    args = parse_args()
    try:
        test = build_test_dataset(args)
    except (TestDataError, build_parquet.DataValidationError, RuntimeError) as exc:
        raise SystemExit(f"error: {exc}") from exc
    print(f"Saved TaskSpec inference parquet files to: {args.output_dir.resolve()}")
    print(json.dumps(test, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
