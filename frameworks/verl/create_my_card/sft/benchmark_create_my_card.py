#!/usr/bin/env python3
"""Benchmark CreateMyCard SFT model quality and offline generation latency."""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import statistics
import sys
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent

from export_renderable_a2ui import (  # noqa: E402
    CompactDslConversionError,
    DEFAULT_INPUT_FILE,
    convert_to_renderable_a2ui,
    empty_accelerator_cache,
    final_compact_dsl,
    get_tensor_parallel_size,
    read_inputs,
    require_new_output_directory,
    shutdown_llm_engine,
    write_jsonl,
)


@dataclass(frozen=True)
class BenchmarkRow:
    sample_id: str
    finish_reason: str | None
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    ok: bool
    error_type: str | None = None
    error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", required=True, help="Merged Hugging Face model path.")
    parser.add_argument("--tokenizer-path", help="Tokenizer path; defaults to --model-path.")
    parser.add_argument("--input-file", type=Path, default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--tensor-parallel-size", type=int, default=8)
    parser.add_argument("--max-model-len", type=int, default=4096)
    parser.add_argument("--max-new-tokens", type=int, default=1536)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, help="Benchmark only the first N rows.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1,
        help="Number of prompts per llm.generate call. Use 1 for per-sample latency.",
    )
    return parser.parse_args()


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(len(ordered) * pct))
    return ordered[rank - 1]


def numeric_summary(values: list[float | int]) -> dict[str, float | int | None]:
    if not values:
        return {"min": None, "p50": None, "p95": None, "max": None, "avg": None}
    numeric_values = [float(value) for value in values]
    return {
        "min": min(numeric_values),
        "p50": percentile(numeric_values, 0.50),
        "p95": percentile(numeric_values, 0.95),
        "max": max(numeric_values),
        "avg": statistics.fmean(numeric_values),
    }


def classify_failure(
    finish_reason: str | None,
    design_compact_dsl: str,
    conversion_error: Exception | None,
) -> tuple[str, str]:
    if finish_reason == "length":
        return "truncated", "generation reached max token length"
    if not design_compact_dsl.strip():
        return "empty", "model generated an empty Design Compact DSL"
    if conversion_error is not None:
        return "conversion_error", str(conversion_error)
    return "unknown", "generation failed for an unknown reason"


def build_benchmark_report(
    rows: list[BenchmarkRow],
    *,
    model_path: str,
    input_file: str,
    tensor_parallel_size: int,
    max_model_len: int,
    max_new_tokens: int,
    total_wall_ms: float,
    model_load_ms: float,
) -> dict[str, Any]:
    total = len(rows)
    success_count = sum(1 for row in rows if row.ok)
    completion_tokens = [row.completion_tokens for row in rows]
    prompt_tokens = [row.prompt_tokens for row in rows]
    latency_ms = [row.latency_ms for row in rows]
    total_seconds = total_wall_ms / 1000.0
    failure_counts = Counter(row.error_type for row in rows if not row.ok and row.error_type)
    return {
        "modelPath": model_path,
        "inputFile": input_file,
        "tensorParallelSize": tensor_parallel_size,
        "maxModelLen": max_model_len,
        "maxNewTokens": max_new_tokens,
        "modelLoadMs": model_load_ms,
        "quality": {
            "total": total,
            "success": success_count,
            "failed": total - success_count,
            "successRate": success_count / total if total else 0.0,
            "failureCounts": dict(sorted(failure_counts.items())),
        },
        "latencyMs": numeric_summary(latency_ms),
        "tokens": {
            "prompt": numeric_summary(prompt_tokens),
            "completion": numeric_summary(completion_tokens),
        },
        "throughput": {
            "wallSeconds": total_seconds,
            "requestsPerSecond": total / total_seconds if total_seconds > 0 else None,
            "successfulRequestsPerSecond": success_count / total_seconds
            if total_seconds > 0
            else None,
            "completionTokensPerSecond": sum(completion_tokens) / total_seconds
            if total_seconds > 0
            else None,
        },
    }


def write_report(report: dict[str, Any], output_file: Path) -> None:
    output_file.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def batched(items: list[Any], batch_size: int) -> list[list[Any]]:
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


def main() -> None:
    args = parse_args()
    require_new_output_directory(args.output_dir)
    if args.max_model_len <= args.max_new_tokens:
        raise ValueError("--max-model-len must be larger than --max-new-tokens")
    if args.batch_size < 1:
        raise ValueError("--batch-size must be a positive integer")
    if not 0 < args.gpu_memory_utilization <= 1:
        raise ValueError("--gpu-memory-utilization must be in (0, 1]")

    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("GLOO_SOCKET_IFNAME", "lo")
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams

    inputs = read_inputs(args.input_file, args.limit)
    tokenizer_path = args.tokenizer_path or args.model_path
    tokenizer = AutoTokenizer.from_pretrained(tokenizer_path, trust_remote_code=True)
    prompts = [
        tokenizer.apply_chat_template(
            item["messages"],
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
        for item in inputs
    ]
    prompt_token_lengths = [
        len(input_ids) for input_ids in tokenizer(prompts, add_special_tokens=False)["input_ids"]
    ]
    max_prompt_tokens = max(prompt_token_lengths)
    if max_prompt_tokens + args.max_new_tokens > args.max_model_len:
        raise ValueError(
            f"longest prompt ({max_prompt_tokens}) + --max-new-tokens "
            f"({args.max_new_tokens}) exceeds --max-model-len ({args.max_model_len})"
        )

    tensor_parallel_size = get_tensor_parallel_size(args.tensor_parallel_size, args.model_path)
    llm: Any | None = None
    benchmark_rows: list[BenchmarkRow] = []
    raw_rows: list[dict[str, Any]] = []
    model_load_start = time.perf_counter()
    total_wall_ms = 0.0
    model_load_ms = 0.0
    try:
        llm = LLM(
            model=args.model_path,
            tokenizer=tokenizer_path,
            tensor_parallel_size=tensor_parallel_size,
            distributed_executor_backend="mp",
            dtype="bfloat16",
            max_model_len=args.max_model_len,
            gpu_memory_utilization=args.gpu_memory_utilization,
            seed=args.seed,
            trust_remote_code=True,
        )
        model_load_ms = (time.perf_counter() - model_load_start) * 1000.0
        benchmark_start = time.perf_counter()
        sampling_params = SamplingParams(temperature=0.0, max_tokens=args.max_new_tokens)

        for batch in batched(list(zip(inputs, prompts, prompt_token_lengths, strict=True)), args.batch_size):
            batch_inputs = [item[0] for item in batch]
            batch_prompts = [item[1] for item in batch]
            batch_prompt_tokens = [item[2] for item in batch]
            batch_start = time.perf_counter()
            outputs = llm.generate(batch_prompts, sampling_params, use_tqdm=False)
            batch_latency_ms = (time.perf_counter() - batch_start) * 1000.0
            per_sample_latency_ms = batch_latency_ms / len(batch)

            if len(outputs) != len(batch_inputs):
                raise RuntimeError("vLLM returned an unexpected number of outputs")
            for item, prompt_tokens, output in zip(
                batch_inputs, batch_prompt_tokens, outputs, strict=True
            ):
                if not output.outputs:
                    finish_reason = None
                    completion_tokens = 0
                    text = ""
                    error_type = "no_completion"
                    error = "vLLM returned no completion"
                    ok = False
                else:
                    completion = output.outputs[0]
                    finish_reason = (
                        None
                        if completion.finish_reason is None
                        else str(completion.finish_reason)
                    )
                    completion_tokens = len(completion.token_ids)
                    text = completion.text
                    conversion_error: Exception | None = None
                    ok = False
                    try:
                        compact_dsl = final_compact_dsl(item["id"], text, finish_reason)
                        convert_to_renderable_a2ui(compact_dsl, item["size"])
                        ok = True
                        error_type = None
                        error = None
                    except (CompactDslConversionError, RuntimeError) as exc:
                        conversion_error = exc
                        error_type, error = classify_failure(
                            finish_reason, text, conversion_error
                        )

                raw_rows.append(
                    {
                        "id": item["id"],
                        "size": item["size"],
                        "finishReason": finish_reason,
                        "promptTokens": prompt_tokens,
                        "completionTokens": completion_tokens,
                        "latencyMs": per_sample_latency_ms,
                        "ok": ok,
                        "errorType": error_type,
                        "error": error,
                        "designCompactDsl": text,
                    }
                )
                benchmark_rows.append(
                    BenchmarkRow(
                        sample_id=item["id"],
                        finish_reason=finish_reason,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        latency_ms=per_sample_latency_ms,
                        ok=ok,
                        error_type=error_type,
                        error=error,
                    )
                )
    finally:
        if llm is not None:
            total_wall_ms = (time.perf_counter() - benchmark_start) * 1000.0
        if llm is not None:
            shutdown_llm_engine(llm)
            llm = None
            gc.collect()
            empty_accelerator_cache()

    args.output_dir.mkdir(parents=True)
    write_jsonl(raw_rows, args.output_dir / "raw_compact_dsl.jsonl")
    write_jsonl([asdict(row) for row in benchmark_rows], args.output_dir / "samples.jsonl")
    report = build_benchmark_report(
        benchmark_rows,
        model_path=args.model_path,
        input_file=str(args.input_file),
        tensor_parallel_size=tensor_parallel_size,
        max_model_len=args.max_model_len,
        max_new_tokens=args.max_new_tokens,
        total_wall_ms=total_wall_ms,
        model_load_ms=model_load_ms,
    )
    write_report(report, args.output_dir / "benchmark_report.json")

    print(json.dumps(report["quality"], ensure_ascii=False, allow_nan=False))
    print(f"Benchmark report: {args.output_dir / 'benchmark_report.json'}")


if __name__ == "__main__":
    main()
