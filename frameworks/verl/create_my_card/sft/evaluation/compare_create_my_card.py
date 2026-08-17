#!/usr/bin/env python3
"""Run paired CreateMyCard benchmarks for a base model and an SFT model."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


if __package__:
    from .export_renderable_a2ui import (
        DEFAULT_INPUT_FILE,
        DEFAULT_MAX_MODEL_LEN,
        require_new_output_directory,
    )
else:
    from export_renderable_a2ui import (
        DEFAULT_INPUT_FILE,
        DEFAULT_MAX_MODEL_LEN,
        require_new_output_directory,
    )


DEFAULT_BASE_MODEL_PATH = Path("/mnt/model/Qwen3.6-27B")
SCRIPT_DIR = Path(__file__).resolve().parent
BENCHMARK_SCRIPT = SCRIPT_DIR / "benchmark_create_my_card.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-model-path",
        type=Path,
        default=DEFAULT_BASE_MODEL_PATH,
        help=f"Base model path; defaults to {DEFAULT_BASE_MODEL_PATH}.",
    )
    parser.add_argument("--sft-model-path", type=Path, required=True)
    parser.add_argument(
        "--tokenizer-path",
        type=Path,
        help="Tokenizer shared by both runs; defaults to --base-model-path.",
    )
    parser.add_argument("--input-file", type=Path, default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tensor-parallel-size", type=int, default=8)
    parser.add_argument("--max-model-len", type=int, default=DEFAULT_MAX_MODEL_LEN)
    parser.add_argument("--max-new-tokens", type=int, default=1536)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Batch size shared by both runs; defaults to 16 for throughput comparison.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> Path:
    for label, path in (
        ("--base-model-path", args.base_model_path),
        ("--sft-model-path", args.sft_model_path),
        ("--input-file", args.input_file),
    ):
        expected = path.is_file() if label == "--input-file" else path.is_dir()
        if not expected:
            kind = "file" if label == "--input-file" else "directory"
            raise FileNotFoundError(f"{label} {kind} does not exist: {path}")

    tokenizer_path = args.tokenizer_path or args.base_model_path
    if not tokenizer_path.is_dir():
        raise FileNotFoundError(f"--tokenizer-path directory does not exist: {tokenizer_path}")
    if args.base_model_path.resolve() == args.sft_model_path.resolve():
        raise ValueError("base and SFT model paths must be different")
    if args.tensor_parallel_size < 1:
        raise ValueError("--tensor-parallel-size must be positive")
    if args.max_model_len <= args.max_new_tokens:
        raise ValueError("--max-model-len must be larger than --max-new-tokens")
    if args.batch_size < 1:
        raise ValueError("--batch-size must be positive")
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be positive")
    if not 0 < args.gpu_memory_utilization <= 1:
        raise ValueError("--gpu-memory-utilization must be in (0, 1]")
    return tokenizer_path


def benchmark_command(
    args: argparse.Namespace,
    *,
    model_path: Path,
    tokenizer_path: Path,
    output_dir: Path,
) -> list[str]:
    command = [
        sys.executable,
        "-B",
        str(BENCHMARK_SCRIPT),
        "--model-path",
        str(model_path),
        "--tokenizer-path",
        str(tokenizer_path),
        "--input-file",
        str(args.input_file),
        "--output-dir",
        str(output_dir),
        "--tensor-parallel-size",
        str(args.tensor_parallel_size),
        "--max-model-len",
        str(args.max_model_len),
        "--max-new-tokens",
        str(args.max_new_tokens),
        "--gpu-memory-utilization",
        str(args.gpu_memory_utilization),
        "--seed",
        str(args.seed),
        "--batch-size",
        str(args.batch_size),
    ]
    if args.limit is not None:
        command.extend(("--limit", str(args.limit)))
    return command


def run_benchmark(
    label: str,
    args: argparse.Namespace,
    *,
    model_path: Path,
    tokenizer_path: Path,
    output_dir: Path,
) -> None:
    print(f"Running {label} benchmark: {model_path}", flush=True)
    subprocess.run(
        benchmark_command(
            args,
            model_path=model_path,
            tokenizer_path=tokenizer_path,
            output_dir=output_dir,
        ),
        check=True,
    )


def read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing benchmark artifact: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return payload


def read_samples(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"missing benchmark samples: {path}")
    rows: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            sample_id = row.get("sample_id") if isinstance(row, dict) else None
            if not isinstance(sample_id, str) or not sample_id:
                raise ValueError(f"{path}:{line_number}: invalid sample_id")
            if sample_id in rows:
                raise ValueError(f"{path}:{line_number}: duplicate sample_id {sample_id!r}")
            rows[sample_id] = row
    if not rows:
        raise ValueError(f"benchmark samples are empty: {path}")
    return rows


def metric_pair(base_value: float | int | None, sft_value: float | int | None) -> dict[str, Any]:
    delta = None
    if base_value is not None and sft_value is not None:
        delta = float(sft_value) - float(base_value)
    return {"base": base_value, "sft": sft_value, "delta": delta}


def build_sample_comparison(
    base_samples: dict[str, dict[str, Any]],
    sft_samples: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int], list[str], list[str]]:
    if base_samples.keys() != sft_samples.keys():
        missing_from_sft = sorted(base_samples.keys() - sft_samples.keys())
        missing_from_base = sorted(sft_samples.keys() - base_samples.keys())
        raise ValueError(
            "benchmark sample sets differ: "
            f"missing from SFT={missing_from_sft}, missing from base={missing_from_base}"
        )

    rows: list[dict[str, Any]] = []
    transitions: Counter[str] = Counter()
    improved_ids: list[str] = []
    regressed_ids: list[str] = []
    for sample_id in sorted(base_samples):
        base = base_samples[sample_id]
        sft = sft_samples[sample_id]
        if base.get("prompt_tokens") != sft.get("prompt_tokens"):
            raise ValueError(f"{sample_id}: prompt token count differs between runs")

        base_ok = bool(base.get("ok"))
        sft_ok = bool(sft.get("ok"))
        if not base_ok and sft_ok:
            transition = "improved"
            improved_ids.append(sample_id)
        elif base_ok and not sft_ok:
            transition = "regressed"
            regressed_ids.append(sample_id)
        elif base_ok:
            transition = "both_success"
        else:
            transition = "both_failed"
        transitions[transition] += 1

        rows.append(
            {
                "id": sample_id,
                "transition": transition,
                "baseOk": base_ok,
                "sftOk": sft_ok,
                "baseErrorType": base.get("error_type"),
                "sftErrorType": sft.get("error_type"),
                "promptTokens": base.get("prompt_tokens"),
                "baseCompletionTokens": base.get("completion_tokens"),
                "sftCompletionTokens": sft.get("completion_tokens"),
                "completionTokenDelta": (
                    int(sft.get("completion_tokens", 0))
                    - int(base.get("completion_tokens", 0))
                ),
                "baseLatencyMs": base.get("latency_ms"),
                "sftLatencyMs": sft.get("latency_ms"),
                "latencyMsDelta": (
                    float(sft.get("latency_ms", 0.0))
                    - float(base.get("latency_ms", 0.0))
                ),
            }
        )
    return rows, dict(sorted(transitions.items())), improved_ids, regressed_ids


def build_comparison_report(
    args: argparse.Namespace,
    *,
    tokenizer_path: Path,
    base_report: dict[str, Any],
    sft_report: dict[str, Any],
    sample_rows: list[dict[str, Any]],
    transitions: dict[str, int],
    improved_ids: list[str],
    regressed_ids: list[str],
) -> dict[str, Any]:
    for field in ("inputFile", "tensorParallelSize", "maxModelLen", "maxNewTokens"):
        if base_report.get(field) != sft_report.get(field):
            raise ValueError(f"benchmark setting differs between runs: {field}")

    base_quality = base_report["quality"]
    sft_quality = sft_report["quality"]
    if base_quality["total"] != sft_quality["total"] or base_quality["total"] != len(sample_rows):
        raise ValueError("benchmark report sample counts do not match paired samples")

    return {
        "baseModelPath": str(args.base_model_path),
        "sftModelPath": str(args.sft_model_path),
        "tokenizerPath": str(tokenizer_path),
        "inputFile": str(args.input_file),
        "configuration": {
            "tensorParallelSize": args.tensor_parallel_size,
            "maxModelLen": args.max_model_len,
            "maxNewTokens": args.max_new_tokens,
            "gpuMemoryUtilization": args.gpu_memory_utilization,
            "seed": args.seed,
            "batchSize": args.batch_size,
            "limit": args.limit,
        },
        "quality": {
            "total": len(sample_rows),
            "baseSuccess": base_quality["success"],
            "sftSuccess": sft_quality["success"],
            "successDelta": sft_quality["success"] - base_quality["success"],
            "baseSuccessRate": base_quality["successRate"],
            "sftSuccessRate": sft_quality["successRate"],
            "successRateDelta": sft_quality["successRate"] - base_quality["successRate"],
            "baseFailureCounts": base_quality["failureCounts"],
            "sftFailureCounts": sft_quality["failureCounts"],
            "transitions": transitions,
            "improvedIds": improved_ids,
            "regressedIds": regressed_ids,
        },
        "modelLoadMs": metric_pair(base_report["modelLoadMs"], sft_report["modelLoadMs"]),
        "latencyMs": {
            name: metric_pair(base_report["latencyMs"][name], sft_report["latencyMs"][name])
            for name in ("avg", "p50", "p95", "max")
        },
        "throughput": {
            name: metric_pair(
                base_report["throughput"][name],
                sft_report["throughput"][name],
            )
            for name in (
                "requestsPerSecond",
                "successfulRequestsPerSecond",
                "completionTokensPerSecond",
            )
        },
        "completionTokens": {
            name: metric_pair(
                base_report["tokens"]["completion"][name],
                sft_report["tokens"]["completion"][name],
            )
            for name in ("avg", "p50", "p95", "max")
        },
        "artifacts": {
            "base": str(args.output_dir / "base"),
            "sft": str(args.output_dir / "sft"),
            "sampleComparison": str(args.output_dir / "comparison_samples.jsonl"),
        },
    }


def format_number(value: Any, *, signed: bool = False, digits: int = 2) -> str:
    if value is None:
        return "n/a"
    prefix = "+" if signed and float(value) > 0 else ""
    return f"{prefix}{float(value):.{digits}f}"


def format_comparison_markdown(report: dict[str, Any], sample_rows: list[dict[str, Any]]) -> str:
    quality = report["quality"]
    lines = [
        "# CreateMyCard Base vs SFT Comparison",
        "",
        "## Configuration",
        "",
        f"- Base model: `{report['baseModelPath']}`",
        f"- SFT model: `{report['sftModelPath']}`",
        f"- Shared tokenizer: `{report['tokenizerPath']}`",
        f"- Input: `{report['inputFile']}`",
        f"- TP / batch size: {report['configuration']['tensorParallelSize']} / {report['configuration']['batchSize']}",
        "",
        "## Quality",
        "",
        "| Metric | Base | SFT | Delta (SFT - Base) |",
        "| --- | ---: | ---: | ---: |",
        f"| Successful samples | {quality['baseSuccess']} | {quality['sftSuccess']} | {quality['successDelta']:+d} |",
        f"| Success rate | {quality['baseSuccessRate'] * 100:.2f}% | {quality['sftSuccessRate'] * 100:.2f}% | {quality['successRateDelta'] * 100:+.2f} pp |",
        "",
        "| Transition | Count |",
        "| --- | ---: |",
        f"| Failed → successful | {quality['transitions'].get('improved', 0)} |",
        f"| Successful → failed | {quality['transitions'].get('regressed', 0)} |",
        f"| Both successful | {quality['transitions'].get('both_success', 0)} |",
        f"| Both failed | {quality['transitions'].get('both_failed', 0)} |",
        "",
        "## Latency And Throughput",
        "",
        "| Metric | Base | SFT | Delta (SFT - Base) |",
        "| --- | ---: | ---: | ---: |",
    ]

    for label, section, key, unit in (
        ("Model load", "modelLoadMs", None, "ms"),
        ("Latency avg", "latencyMs", "avg", "ms"),
        ("Latency p50", "latencyMs", "p50", "ms"),
        ("Latency p95", "latencyMs", "p95", "ms"),
        ("Requests", "throughput", "requestsPerSecond", "req/s"),
        ("Successful requests", "throughput", "successfulRequestsPerSecond", "req/s"),
        ("Completion tokens", "throughput", "completionTokensPerSecond", "tok/s"),
    ):
        values = report[section] if key is None else report[section][key]
        lines.append(
            f"| {label} | {format_number(values['base'])} {unit} | "
            f"{format_number(values['sft'])} {unit} | "
            f"{format_number(values['delta'], signed=True)} {unit} |"
        )

    changed = [row for row in sample_rows if row["transition"] in {"improved", "regressed"}]
    lines.extend(
        [
            "",
            "## Changed Samples",
            "",
        ]
    )
    if not changed:
        lines.append("No pass/fail transitions.")
    else:
        lines.extend(
            [
                "| ID | Transition | Base failure | SFT failure | Completion delta | Latency delta |",
                "| --- | --- | --- | --- | ---: | ---: |",
            ]
        )
        for row in changed:
            lines.append(
                f"| `{row['id']}` | {row['transition']} | {row['baseErrorType'] or ''} | "
                f"{row['sftErrorType'] or ''} | {row['completionTokenDelta']:+d} tokens | "
                f"{row['latencyMsDelta']:+.2f} ms |"
            )
    return "\n".join(lines) + "\n"


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_jsonl(rows: list[dict[str, Any]], path: Path) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    tokenizer_path = validate_args(args)
    require_new_output_directory(args.output_dir)
    args.output_dir.parent.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir()

    base_output = args.output_dir / "base"
    sft_output = args.output_dir / "sft"
    run_benchmark(
        "base",
        args,
        model_path=args.base_model_path,
        tokenizer_path=tokenizer_path,
        output_dir=base_output,
    )
    run_benchmark(
        "SFT",
        args,
        model_path=args.sft_model_path,
        tokenizer_path=tokenizer_path,
        output_dir=sft_output,
    )

    base_report = read_json(base_output / "benchmark_report.json")
    sft_report = read_json(sft_output / "benchmark_report.json")
    base_samples = read_samples(base_output / "samples.jsonl")
    sft_samples = read_samples(sft_output / "samples.jsonl")
    sample_rows, transitions, improved_ids, regressed_ids = build_sample_comparison(
        base_samples,
        sft_samples,
    )
    report = build_comparison_report(
        args,
        tokenizer_path=tokenizer_path,
        base_report=base_report,
        sft_report=sft_report,
        sample_rows=sample_rows,
        transitions=transitions,
        improved_ids=improved_ids,
        regressed_ids=regressed_ids,
    )

    comparison_json = args.output_dir / "comparison_report.json"
    comparison_markdown = args.output_dir / "comparison_report.md"
    write_jsonl(sample_rows, args.output_dir / "comparison_samples.jsonl")
    write_json(report, comparison_json)
    comparison_markdown.write_text(
        format_comparison_markdown(report, sample_rows),
        encoding="utf-8",
    )
    print(json.dumps(report["quality"], ensure_ascii=False, indent=2, allow_nan=False))
    print(f"Comparison report: {comparison_json}")
    print(f"Human-readable comparison: {comparison_markdown}")


if __name__ == "__main__":
    main()
