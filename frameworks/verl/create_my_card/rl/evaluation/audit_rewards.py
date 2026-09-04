#!/usr/bin/env python3
"""Run the CreateMyCard Stage 0 reward audit over saved model outputs."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Iterable, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT))

from frameworks.verl.create_my_card.rl.reward import (  # noqa: E402
    CheckerConfig,
    DesignCheckerAdapter,
    RewardComputer,
    RewardRequest,
    default_checker_root,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Raw rollout JSONL.")
    parser.add_argument(
        "--taskspec-file",
        type=Path,
        help="Optional TaskSpec JSON/JSONL keyed by id when rows do not embed TaskSpec.",
    )
    parser.add_argument(
        "--labels-file",
        type=Path,
        help="Optional reviewed primary-label JSON/JSONL keyed by id.",
    )
    parser.add_argument(
        "--tokenizer-path",
        type=Path,
        help=(
            "Optional Hugging Face tokenizer used to count completion tokens when "
            "an input row does not provide completionTokens. Tokenization excludes "
            "special tokens, matching saved vLLM completion.token_ids."
        ),
    )
    parser.add_argument(
        "--default-finish-reason",
        choices=("stop", "length"),
        help="Explicit finish reason to use only when an input row omits it.",
    )
    parser.add_argument(
        "--checker-root",
        type=Path,
        default=default_checker_root(),
        help=(
            "Path to design-check. Defaults to the vendored 0.2.0 package; "
            "DESIGN_CHECK_ROOT may override it."
        ),
    )
    parser.add_argument("--reward-config", type=Path, help="Override reward_stage0.json.")
    parser.add_argument(
        "--layout-dir",
        type=Path,
        help="Optional directory containing <id>.layout.json L2 dumps.",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--checker-timeout", type=float, default=30.0)
    parser.add_argument("--checker-retries", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--fail-on-masked",
        action="store_true",
        help="Exit non-zero when any checker/environment failure was masked.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit is not None and args.limit < 1:
        raise SystemExit("error: --limit must be positive")
    if args.output.exists() and not args.overwrite:
        raise SystemExit(f"error: output already exists: {args.output}")

    task_specs = load_keyed_records(args.taskspec_file, payload_keys=("taskSpec", "task_spec"))
    labels = load_keyed_records(args.labels_file, payload_keys=("labels", "reward_labels"))
    tokenizer = _load_completion_tokenizer(args.tokenizer_path)
    adapter = DesignCheckerAdapter(
        CheckerConfig(
            checker_root=args.checker_root.resolve(),
            timeout_seconds=args.checker_timeout,
            max_retries=args.checker_retries,
        )
    )
    computer_kwargs: dict[str, Any] = {"checker": adapter}
    if args.reward_config is not None:
        computer_kwargs["config_path"] = args.reward_config.resolve()
    computer = RewardComputer(**computer_kwargs)

    outputs: list[dict[str, Any]] = []
    tokenized_rows = 0
    for index, row in enumerate(read_jsonl(args.input), start=1):
        if args.limit is not None and len(outputs) >= args.limit:
            break
        sample_id = _sample_id(row, index)
        group_id = _group_id(row, index, fallback=sample_id)
        task_spec = _embedded_mapping(row, ("taskSpec", "task_spec")) or task_specs.get(group_id)
        if task_spec is None:
            raise ValueError(
                f"row {index} ({sample_id}, group {group_id}): no TaskSpec was provided"
            )
        content_labels = (
            _embedded_mapping(row, ("rewardLabels", "reward_labels", "content_labels"))
            or labels.get(group_id)
        )
        layout_path = find_layout(args.layout_dir, sample_id)
        if args.layout_dir is not None and layout_path is None:
            raise FileNotFoundError(
                f"row {index} ({sample_id}): --layout-dir has no matching "
                "<id>.layout.json or <id>.json dump"
            )
        solution = _solution(row, index)
        completion_tokens = _optional_int(row, ("completionTokens", "completion_tokens"))
        if completion_tokens is None and tokenizer is not None:
            completion_tokens = _count_completion_tokens(tokenizer, solution)
            tokenized_rows += 1
        finish_reason = _optional_string(row, ("finishReason", "finish_reason"))
        if finish_reason is None:
            finish_reason = args.default_finish_reason
        request = RewardRequest(
            sample_id=sample_id,
            solution_str=solution,
            task_spec=task_spec,
            content_labels=content_labels,
            finish_reason=finish_reason,
            completion_tokens=completion_tokens,
            layout_path=layout_path,
            include_delegated=True,
        )
        result = computer.compute(request).to_dict()
        result["input_index"] = index
        result["group_id"] = group_id
        candidate_index = _optional_int(row, ("candidateIndex", "candidate_index"))
        if candidate_index is not None:
            result["candidate_index"] = candidate_index
        sampling_mode = _optional_string(row, ("samplingMode", "sampling_mode"))
        if sampling_mode is not None:
            result["sampling_mode"] = sampling_mode
        outputs.append(result)

    if not outputs:
        raise ValueError("input contains no rollout rows")
    write_jsonl_atomic(outputs, args.output, overwrite=args.overwrite)
    masked = sum(bool(row["masked"]) for row in outputs)
    scored_rows = sum(row["score"] is not None for row in outputs)
    summary = {
        "rows": len(outputs),
        "scored_rows": scored_rows,
        "masked": masked,
        "policy_update_eligible": sum(
            bool(row["policy_update_eligible"]) for row in outputs
        ),
        "tokenized_rows": tokenized_rows,
        "tokenizer": str(args.tokenizer_path.resolve()) if tokenizer is not None else None,
        "output": str(args.output.resolve()),
    }
    print(json.dumps(summary, ensure_ascii=False, allow_nan=False))
    return 2 if args.fail_on_masked and masked else 0


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            if not raw_line.strip():
                continue
            try:
                value = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid JSONL at {path}:{line_number}:{exc.colno}"
                ) from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: row must be an object")
            yield value


def load_keyed_records(
    path: Path | None,
    *,
    payload_keys: tuple[str, ...],
) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    if not path.is_file():
        raise FileNotFoundError(path)
    if path.suffix.lower() == ".jsonl":
        raw: Any = list(read_jsonl(path))
    else:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, dict):
        if all(isinstance(value, dict) for value in raw.values()):
            return {str(key): dict(value) for key, value in raw.items()}
        raise ValueError(f"keyed JSON object values must be objects: {path}")
    if not isinstance(raw, list):
        raise ValueError(f"records must be a JSON array/object or JSONL: {path}")
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"{path}: record {index} must be an object")
        sample_id = item.get("id") or item.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError(f"{path}: record {index} has no id")
        payload = _embedded_mapping(item, payload_keys)
        if payload is None:
            payload = {key: value for key, value in item.items() if key not in {"id", "sample_id"}}
        if sample_id in result:
            raise ValueError(f"{path}: duplicate id {sample_id}")
        result[sample_id] = payload
    return result


def find_layout(layout_dir: Path | None, sample_id: str) -> Path | None:
    if layout_dir is None:
        return None
    candidates = (
        layout_dir / f"{sample_id}.layout.json",
        layout_dir / f"{sample_id}.json",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def write_jsonl_atomic(
    rows: Iterable[Mapping[str, Any]],
    output: Path,
    *,
    overwrite: bool,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output.name}.",
            suffix=".tmp",
            dir=output.parent,
            delete=False,
            mode="w",
            encoding="utf-8",
            newline="\n",
        ) as stream:
            temporary_path = Path(stream.name)
            for row in rows:
                stream.write(
                    json.dumps(
                        row,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        allow_nan=False,
                    )
                    + "\n"
                )
        if output.exists() and not overwrite:
            raise FileExistsError(output)
        os.replace(temporary_path, output)
        temporary_path = None
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _sample_id(row: Mapping[str, Any], index: int) -> str:
    value = row.get("id") or row.get("sample_id")
    if not isinstance(value, str) or not value:
        raise ValueError(f"row {index}: id must be a non-empty string")
    return value


def _group_id(row: Mapping[str, Any], index: int, *, fallback: str) -> str:
    value = row.get("groupId") or row.get("group_id") or fallback
    if not isinstance(value, str) or not value:
        raise ValueError(f"row {index}: group id must be a non-empty string")
    return value


def _solution(row: Mapping[str, Any], index: int) -> str:
    for key in ("designCompactDsl", "solution_str", "solution"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise ValueError(f"row {index}: no non-empty Compact DSL solution")


def _embedded_mapping(
    row: Mapping[str, Any],
    keys: tuple[str, ...],
) -> dict[str, Any] | None:
    for key in keys:
        value = row.get(key)
        if isinstance(value, Mapping):
            return dict(value)
    return None


def _optional_string(row: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = row.get(key)
        if isinstance(value, str):
            return value
    return None


def _optional_int(row: Mapping[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        value = row.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            return value
    return None


def _load_completion_tokenizer(tokenizer_path: Path | None) -> Any | None:
    if tokenizer_path is None:
        return None
    if not tokenizer_path.exists():
        raise FileNotFoundError(f"tokenizer path does not exist: {tokenizer_path}")
    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise RuntimeError(
            "transformers is required when --tokenizer-path is provided"
        ) from exc
    return AutoTokenizer.from_pretrained(tokenizer_path, trust_remote_code=True)


def _count_completion_tokens(tokenizer: Any, solution: str) -> int:
    encoded = tokenizer(solution, add_special_tokens=False)
    if not isinstance(encoded, Mapping):
        raise TypeError("tokenizer result must be a mapping")
    input_ids = encoded.get("input_ids")
    if not isinstance(input_ids, list) or any(
        isinstance(token_id, bool) or not isinstance(token_id, int)
        for token_id in input_ids
    ):
        raise TypeError("tokenizer result must contain one integer input_ids list")
    return len(input_ids)


if __name__ == "__main__":
    raise SystemExit(main())
