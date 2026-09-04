#!/usr/bin/env python3
"""Run or validate the CreateMyCard multi-stage post-training pipeline."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from .config import load_pipeline_spec
from .contracts import PipelineError
from .runner import PipelineRunner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="Validate config contracts only.")
    validate.add_argument("--config", type=Path, required=True)

    run = subparsers.add_parser("run", help="Execute the three stages sequentially.")
    run.add_argument("--config", type=Path, required=True)
    run.add_argument("--run-id", required=True)
    run.add_argument("--backend", choices=("mock", "command"))
    run.add_argument(
        "--mode",
        choices=("scaffold", "smoke", "train"),
        help="Override run.execution_mode without editing the shared config.",
    )
    run.add_argument(
        "--base-checkpoint",
        help="Override run.base_checkpoint; use the same value when resuming.",
    )
    run.add_argument("--resume", action="store_true")
    run.add_argument(
        "--stop-after",
        choices=("rft", "dpo", "grpo"),
        help="Stop cleanly after this stage so the next stage data can be built.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        spec = load_pipeline_spec(args.config)
        if args.command == "validate":
            result = {
                "valid": True,
                "schema_version": spec.schema_version,
                "task": spec.task,
                "execution_mode": spec.execution_mode,
                "stages": [stage.name for stage in spec.stages],
            }
        else:
            if args.mode is not None:
                spec = replace(spec, execution_mode=args.mode)
            if args.base_checkpoint is not None:
                spec = replace(spec, base_checkpoint=args.base_checkpoint)
            result = PipelineRunner(
                spec,
                run_id=args.run_id,
                backend_override=args.backend,
                resume=args.resume,
            ).run(stop_after=args.stop_after)
    except PipelineError as exc:
        raise SystemExit(f"error: {exc}") from exc
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
