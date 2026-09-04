#!/usr/bin/env python3
"""Build framework-specific stage datasets from neutral input files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from frameworks.verl.create_my_card.sft.dataset.build_parquet import (
    DataValidationError,
)

from .contracts import PipelineError
from .data import build_dpo_dataset, build_grpo_dataset, build_rft_dataset


def _common_candidate_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--audits", type=Path, required=True)
    parser.add_argument("--taskspec", type=Path, required=True)
    parser.add_argument("--system-prompt", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--validation-ratio", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--expected-producer-checkpoint")
    parser.add_argument("--allow-partial-score", action="store_true")
    parser.add_argument("--require-policy-update-eligible", action="store_true")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    rft = subparsers.add_parser("rft", help="Select high-quality candidates for RFT.")
    _common_candidate_args(rft)
    rft.add_argument("--min-score", type=float, default=0.8)

    dpo = subparsers.add_parser("dpo", help="Build same-prompt DPO pairs.")
    _common_candidate_args(dpo)
    dpo.add_argument("--chosen-min-score", type=float, default=0.8)
    dpo.add_argument("--min-score-margin", type=float, default=0.2)
    dpo.add_argument("--max-length-ratio", type=float, default=1.25)

    grpo = subparsers.add_parser("grpo", help="Build veRL prompt parquet.")
    grpo.add_argument("--taskspec", type=Path, required=True)
    grpo.add_argument("--system-prompt", type=Path, required=True)
    grpo.add_argument("--labels", type=Path)
    grpo.add_argument("--output-dir", type=Path, required=True)
    grpo.add_argument("--validation-ratio", type=float, default=0.05)
    grpo.add_argument("--seed", type=int, default=42)
    grpo.add_argument("--require-reviewed-labels", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.command == "rft":
            result = build_rft_dataset(
                candidates_path=args.candidates,
                audits_path=args.audits,
                taskspec_path=args.taskspec,
                system_prompt_path=args.system_prompt,
                output_dir=args.output_dir,
                min_score=args.min_score,
                validation_ratio=args.validation_ratio,
                seed=args.seed,
                require_policy_update_eligible=args.require_policy_update_eligible,
                allow_partial_score=args.allow_partial_score,
                expected_producer_checkpoint=args.expected_producer_checkpoint,
            )
        elif args.command == "dpo":
            result = build_dpo_dataset(
                candidates_path=args.candidates,
                audits_path=args.audits,
                taskspec_path=args.taskspec,
                system_prompt_path=args.system_prompt,
                output_dir=args.output_dir,
                chosen_min_score=args.chosen_min_score,
                min_score_margin=args.min_score_margin,
                max_length_ratio=args.max_length_ratio,
                validation_ratio=args.validation_ratio,
                seed=args.seed,
                require_policy_update_eligible=args.require_policy_update_eligible,
                allow_partial_score=args.allow_partial_score,
                expected_producer_checkpoint=args.expected_producer_checkpoint,
            )
        else:
            result = build_grpo_dataset(
                taskspec_path=args.taskspec,
                system_prompt_path=args.system_prompt,
                labels_path=args.labels,
                output_dir=args.output_dir,
                validation_ratio=args.validation_ratio,
                seed=args.seed,
                require_reviewed_labels=args.require_reviewed_labels,
            )
    except (PipelineError, DataValidationError, RuntimeError) as exc:
        raise SystemExit(f"error: {exc}") from exc
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
