#!/usr/bin/env python3
"""Generate Compact DSL from TaskSpec inputs and export renderable A2UI NDJSON."""

from __future__ import annotations

import argparse
import gc
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from frameworks.verl.create_my_card.data_pipeline.converters import (  # noqa: E402
    CompactDslConversionError,
    convert_compact_dsl_to_a2ui,
)


DEFAULT_INPUT_FILE = SCRIPT_DIR / "data" / "parquet" / "test.parquet"
SAFE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--model-path", help="Model used to generate Compact DSL with vLLM.")
    source.add_argument(
        "--raw-input-file",
        type=Path,
        help="Reuse a previously saved raw_compact_dsl.jsonl without loading the model.",
    )
    parser.add_argument(
        "--tokenizer-path",
        help="Tokenizer path; defaults to --model-path.",
    )
    parser.add_argument("--input-file", type=Path, default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--tensor-parallel-size",
        type=int,
        default=8,
        help="vLLM tensor parallel size; 8 divides Qwen3.6-27B's 24 attention heads.",
    )
    parser.add_argument("--max-model-len", type=int, default=4096)
    parser.add_argument("--max-new-tokens", type=int, default=1536)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.9)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--limit", type=int, help="Generate only the first N rows.")
    return parser.parse_args()


def read_inputs(input_file: Path, limit: int | None) -> list[dict[str, Any]]:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("pyarrow is required to read TaskSpec parquet inputs") from exc

    if not input_file.is_file():
        raise FileNotFoundError(f"missing TaskSpec input data: {input_file}")
    rows = pq.read_table(input_file).to_pylist()
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be a positive integer")
        rows = rows[:limit]

    inputs: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for index, row in enumerate(rows):
        sample_id = row.get("id")
        messages = row.get("messages")
        if not isinstance(sample_id, str) or not SAFE_ID_PATTERN.fullmatch(sample_id):
            raise ValueError(f"row {index}: id is not safe for an output filename")
        if sample_id in seen_ids:
            raise ValueError(f"row {index}: duplicate id {sample_id!r}")
        if row.get("enable_thinking") is not False:
            raise ValueError(f"row {index}: enable_thinking must be false")
        if not isinstance(messages, list) or len(messages) != 2:
            raise ValueError(f"row {index}: expected exactly system and user messages")
        system, user = messages
        if system.get("role") != "system" or user.get("role") != "user":
            raise ValueError(f"row {index}: expected system then user messages")
        for turn in (system, user):
            if not isinstance(turn.get("content"), str) or not turn["content"].strip():
                raise ValueError(f"row {index}: {turn.get('role')} content is empty")
        try:
            task_spec = json.loads(user["content"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"row {index}: user content is not a JSON TaskSpec") from exc
        if not isinstance(task_spec, dict) or task_spec.get("size") != "2x2":
            raise ValueError(f"row {index}: TaskSpec size must be 2x2")
        seen_ids.add(sample_id)
        inputs.append(
            {
                "id": sample_id,
                "messages": messages,
                "size": task_spec["size"],
            }
        )
    if not inputs:
        raise ValueError("TaskSpec input dataset is empty")
    return inputs


def get_tensor_parallel_size(requested: int, model_path: str) -> int:
    import torch
    import torch_npu  # noqa: F401  # registers torch.npu
    from transformers import AutoConfig

    device_count = torch.npu.device_count()
    if device_count < 1:
        raise RuntimeError("no visible NPU devices")
    if requested < 1:
        raise ValueError("--tensor-parallel-size must be a positive integer")
    if requested > device_count:
        raise ValueError(
            f"--tensor-parallel-size={requested} exceeds {device_count} visible NPU devices"
        )

    config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
    text_config = getattr(config, "text_config", config)
    attention_heads = getattr(text_config, "num_attention_heads", None)
    if attention_heads is not None and attention_heads % requested != 0:
        raise ValueError(
            f"model has {attention_heads} attention heads, which is not divisible by "
            f"--tensor-parallel-size={requested}"
        )
    return requested


def shutdown_llm_engine(llm: Any) -> bool:
    """Shut down the first vLLM engine layer that exposes a cleanup method."""
    llm_engine = getattr(llm, "llm_engine", None)
    targets = (
        llm,
        llm_engine,
        getattr(llm_engine, "engine_core", None),
        getattr(llm_engine, "model_executor", None),
    )
    seen: set[int] = set()
    for target in targets:
        if target is None or id(target) in seen:
            continue
        seen.add(id(target))
        shutdown = getattr(target, "shutdown", None)
        if not callable(shutdown):
            continue
        try:
            shutdown()
        except Exception as exc:  # vLLM cleanup must not discard saved generations.
            print(f"Warning: failed to shut down vLLM engine: {exc}", file=sys.stderr)
            return False
        return True
    print(
        "Warning: vLLM engine exposes no shutdown method; releasing Python references only.",
        file=sys.stderr,
    )
    return False


def empty_accelerator_cache() -> None:
    """Release cached allocations after the vLLM engine and outputs are dereferenced."""
    try:
        import torch
    except ImportError:
        return
    try:
        for name in ("npu", "cuda"):
            accelerator = getattr(torch, name, None)
            is_available = getattr(accelerator, "is_available", None)
            empty_cache = getattr(accelerator, "empty_cache", None)
            if not callable(is_available) or not is_available() or not callable(empty_cache):
                continue
            empty_cache()
            return
    except Exception as exc:  # Cache cleanup must not discard saved generations.
        print(f"Warning: failed to empty accelerator cache: {exc}", file=sys.stderr)


def final_compact_dsl(sample_id: str, text: str, finish_reason: str | None) -> str:
    if finish_reason == "length":
        raise RuntimeError(
            f"{sample_id}: generation reached max token length; increase --max-new-tokens "
            "and --max-model-len before exporting"
        )
    compact_dsl = text.strip()
    if not compact_dsl:
        raise RuntimeError(f"{sample_id}: model generated an empty Design Compact DSL")
    return compact_dsl


def convert_to_renderable_a2ui(compact_dsl: str, size: str) -> str:
    return convert_compact_dsl_to_a2ui(
        compact_dsl,
        size=size,
        protocol_profile={"version": "v0.9"},
    )


def require_new_output_directory(output_dir: Path) -> None:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"output directory already exists: {output_dir}")


def create_output_directory(output_dir: Path) -> None:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir()


def write_jsonl(rows: list[dict[str, Any]], output_file: Path) -> None:
    body = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
        for row in rows
    )
    output_file.write_text(body, encoding="utf-8")


def write_renderable_outputs(rows: list[dict[str, str]], output_dir: Path) -> None:
    for row in rows:
        output_file = output_dir / f"{row['id']}.card.genui.jsonl"
        output_file.write_text(row["a2ui"].rstrip() + "\n", encoding="utf-8")


def collect_raw_outputs(inputs: list[dict[str, Any]], outputs: list[Any]) -> list[dict[str, Any]]:
    if len(outputs) != len(inputs):
        raise RuntimeError("vLLM returned an unexpected number of outputs")

    rows: list[dict[str, Any]] = []
    for item, output in zip(inputs, outputs, strict=True):
        if not output.outputs:
            raise RuntimeError(f"{item['id']}: vLLM returned no completion")
        completion = output.outputs[0]
        finish_reason = completion.finish_reason
        rows.append(
            {
                "id": item["id"],
                "size": item["size"],
                "finishReason": None if finish_reason is None else str(finish_reason),
                "completionTokens": len(completion.token_ids),
                "designCompactDsl": completion.text,
            }
        )
    return rows


def read_raw_outputs(input_file: Path) -> list[dict[str, Any]]:
    if not input_file.is_file():
        raise FileNotFoundError(f"missing raw Compact DSL input: {input_file}")

    rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    with input_file.open("r", encoding="utf-8-sig") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            if not raw_line.strip():
                continue
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"raw Compact DSL JSONL is invalid at line {line_number}: {exc}"
                ) from exc
            sample_id = row.get("id") if isinstance(row, dict) else None
            if not isinstance(sample_id, str) or not SAFE_ID_PATTERN.fullmatch(sample_id):
                raise ValueError(f"raw Compact DSL line {line_number}: invalid id")
            if sample_id in seen_ids:
                raise ValueError(f"raw Compact DSL line {line_number}: duplicate id {sample_id!r}")
            if row.get("size") != "2x2":
                raise ValueError(f"{sample_id}: raw Compact DSL size must be 2x2")
            if not isinstance(row.get("designCompactDsl"), str):
                raise ValueError(f"{sample_id}: designCompactDsl must be a string")
            finish_reason = row.get("finishReason")
            if finish_reason is not None and not isinstance(finish_reason, str):
                raise ValueError(f"{sample_id}: finishReason must be a string or null")
            completion_tokens = row.get("completionTokens")
            if (
                not isinstance(completion_tokens, int)
                or isinstance(completion_tokens, bool)
                or completion_tokens < 0
            ):
                raise ValueError(f"{sample_id}: completionTokens must be a non-negative integer")
            seen_ids.add(sample_id)
            rows.append(
                {
                    "id": sample_id,
                    "size": row["size"],
                    "finishReason": finish_reason,
                    "completionTokens": completion_tokens,
                    "designCompactDsl": row["designCompactDsl"],
                }
            )
    if not rows:
        raise ValueError("raw Compact DSL input is empty")
    return rows


def main() -> None:
    args = parse_args()
    require_new_output_directory(args.output_dir)

    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("GLOO_SOCKET_IFNAME", "lo")
    os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

    max_prompt_tokens: int | None = None
    llm: Any | None = None
    outputs: list[Any] | None = None
    try:
        if args.raw_input_file is not None:
            raw_rows = read_raw_outputs(args.raw_input_file)
        else:
            if args.max_model_len <= args.max_new_tokens:
                raise ValueError("--max-model-len must be larger than --max-new-tokens")
            if not 0 < args.gpu_memory_utilization <= 1:
                raise ValueError("--gpu-memory-utilization must be in (0, 1]")

            from transformers import AutoTokenizer

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
                len(input_ids)
                for input_ids in tokenizer(prompts, add_special_tokens=False)["input_ids"]
            ]
            max_prompt_tokens = max(prompt_token_lengths)
            if max_prompt_tokens + args.max_new_tokens > args.max_model_len:
                raise ValueError(
                    f"longest prompt ({max_prompt_tokens}) + --max-new-tokens "
                    f"({args.max_new_tokens}) exceeds --max-model-len ({args.max_model_len})"
                )

            tensor_parallel_size = get_tensor_parallel_size(
                args.tensor_parallel_size, args.model_path
            )

            from vllm import LLM, SamplingParams

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
            sampling_params = SamplingParams(temperature=0.0, max_tokens=args.max_new_tokens)
            outputs = llm.generate(prompts, sampling_params, use_tqdm=True)
            raw_rows = collect_raw_outputs(inputs, outputs)

        create_output_directory(args.output_dir)
        raw_output_file = args.output_dir / "raw_compact_dsl.jsonl"
        write_jsonl(raw_rows, raw_output_file)
        print(f"Saved raw Compact DSL outputs: {raw_output_file}")
    finally:
        if llm is not None:
            shutdown_called = shutdown_llm_engine(llm)
            llm = None
            outputs = None
            gc.collect()
            empty_accelerator_cache()
            if shutdown_called:
                print("Released vLLM engine before A2UI conversion.")

    export_rows: list[dict[str, str]] = []
    conversion_errors: list[dict[str, Any]] = []
    for row in raw_rows:
        try:
            compact_dsl = final_compact_dsl(
                row["id"], row["designCompactDsl"], row["finishReason"]
            )
            export_rows.append(
                {
                    "id": row["id"],
                    "a2ui": convert_to_renderable_a2ui(compact_dsl, row["size"]),
                }
            )
        except (CompactDslConversionError, RuntimeError) as exc:
            conversion_errors.append(
                {
                    "id": row["id"],
                    "errorType": type(exc).__name__,
                    "error": str(exc),
                    "finishReason": row["finishReason"],
                    "designCompactDsl": row["designCompactDsl"],
                }
            )

    if conversion_errors:
        error_file = args.output_dir / "conversion_errors.jsonl"
        write_jsonl(conversion_errors, error_file)
        raise RuntimeError(
            f"{len(conversion_errors)} of {len(raw_rows)} Compact DSL outputs failed conversion; "
            f"raw outputs: {raw_output_file}; errors: {error_file}"
        )

    write_renderable_outputs(export_rows, args.output_dir)
    print(f"Exported {len(export_rows)} renderable A2UI files: {args.output_dir}")
    if max_prompt_tokens is not None:
        print(f"Maximum prompt tokens: {max_prompt_tokens}")
    print(f"Maximum completion tokens: {max(row['completionTokens'] for row in raw_rows)}")


if __name__ == "__main__":
    main()
