#!/usr/bin/env python3
"""Run veRL SFT while suppressing its unconditional final checkpoint save."""

from __future__ import annotations

from verl.trainer import sft_trainer


def skip_checkpoint_save(handler: object, step: int) -> None:
    """Replace CheckpointHandler.save_checkpoint for the two-step dry run."""
    if getattr(handler, "rank", 0) == 0:
        print(f"Dry run: skipped checkpoint and weight saving at step {step}")


sft_trainer.CheckpointHandler.save_checkpoint = skip_checkpoint_save


if __name__ == "__main__":
    sft_trainer.main()
