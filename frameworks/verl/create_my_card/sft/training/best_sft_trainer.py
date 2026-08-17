#!/usr/bin/env python3
"""Run veRL SFT and save only checkpoints with improved validation loss."""

from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any


BEST_TRACKER_NAME = "best_checkpointed_iteration.txt"
BEST_METRICS_NAME = "best_validation_metrics.json"
BEST_METRIC_NAME = "val/loss"


class _RuntimeState:
    validation_loss: float | None = None
    validation_step: int | None = None
    best_loss: float | None = None
    best_step: int | None = None


_STATE = _RuntimeState()


def read_min_delta() -> float:
    raw = os.environ.get("BEST_CKPT_MIN_DELTA", "0")
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"BEST_CKPT_MIN_DELTA must be a non-negative number, got: {raw}") from exc
    if not math.isfinite(value) or value < 0:
        raise RuntimeError(f"BEST_CKPT_MIN_DELTA must be a non-negative finite number, got: {raw}")
    return value


def is_improved(validation_loss: float, best_loss: float, min_delta: float) -> bool:
    return math.isfinite(validation_loss) and validation_loss < best_loss - min_delta


def load_best_state(save_path: Path) -> tuple[float, int]:
    tracker_path = save_path / BEST_TRACKER_NAME
    metrics_path = save_path / BEST_METRICS_NAME
    if not tracker_path.exists() and not metrics_path.exists():
        return math.inf, 0
    if not tracker_path.is_file() or not metrics_path.is_file():
        raise RuntimeError(
            f"best-checkpoint metadata is incomplete under {save_path}; "
            f"expected both {BEST_TRACKER_NAME} and {BEST_METRICS_NAME}"
        )

    try:
        tracker_step = int(tracker_path.read_text(encoding="utf-8").strip())
        metrics: dict[str, Any] = json.loads(metrics_path.read_text(encoding="utf-8"))
        metric_name = metrics["metric"]
        best_loss = float(metrics["bestValidationLoss"])
        metrics_step = int(metrics["globalStep"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"invalid best-checkpoint metadata under {save_path}") from exc

    if metric_name != BEST_METRIC_NAME:
        raise RuntimeError(f"unsupported best-checkpoint metric: {metric_name}")
    if tracker_step <= 0 or metrics_step != tracker_step or not math.isfinite(best_loss):
        raise RuntimeError(f"inconsistent best-checkpoint metadata under {save_path}")
    if not (save_path / f"global_step_{tracker_step}").is_dir():
        raise RuntimeError(f"best checkpoint directory does not exist: global_step_{tracker_step}")
    return best_loss, tracker_step


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            stream.write(content)
            temporary_path = Path(stream.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def write_best_state(save_path: Path, validation_loss: float, global_step: int) -> None:
    if not math.isfinite(validation_loss) or global_step <= 0:
        raise RuntimeError("best checkpoint requires a finite validation loss and positive global step")
    metrics = {
        "metric": BEST_METRIC_NAME,
        "mode": "min",
        "bestValidationLoss": validation_loss,
        "globalStep": global_step,
    }
    _write_text_atomic(
        save_path / BEST_METRICS_NAME,
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n",
    )
    # Write the tracker last so readers never select a step before its metrics are durable.
    _write_text_atomic(save_path / BEST_TRACKER_NAME, f"{global_step}\n")


def install_best_checkpoint_policy(sft_trainer: Any) -> None:
    """Wrap veRL logging and checkpoint calls without replacing its training loop."""
    original_tracking = sft_trainer.Tracking
    original_save_checkpoint = sft_trainer.CheckpointHandler.save_checkpoint
    min_delta = read_min_delta()

    class ValidationTracking(original_tracking):
        def log(self, data: dict[str, Any], step: int, backend: Any = None) -> None:
            if BEST_METRIC_NAME in data:
                _STATE.validation_loss = float(data[BEST_METRIC_NAME])
                _STATE.validation_step = int(step)
            return super().log(data=data, step=step, backend=backend)

    def save_best_checkpoint(handler: Any, step: int) -> None:
        save_path = Path(handler.default_local_dir)
        if _STATE.best_loss is None or _STATE.best_step is None:
            _STATE.best_loss, _STATE.best_step = load_best_state(save_path)
            latest_tracker = save_path / "latest_checkpointed_iteration.txt"
            if _STATE.best_step == 0 and latest_tracker.exists():
                raise RuntimeError(
                    "cannot resume best-checkpoint training from a legacy checkpoint without best metadata; "
                    "use a new SAVE_PATH or restart with RESUME_MODE=disable"
                )

        torch = sft_trainer.torch
        signal = torch.zeros(2, device=sft_trainer.get_device_name())
        if handler.rank == 0:
            if _STATE.validation_step != step or _STATE.validation_loss is None:
                signal[0] = -1
            else:
                signal[0] = float(is_improved(_STATE.validation_loss, _STATE.best_loss, min_delta))
                signal[1] = _STATE.validation_loss
        torch.distributed.broadcast(signal, src=0)

        decision = int(signal[0].item())
        validation_loss = float(signal[1].item())
        if decision < 0:
            raise RuntimeError(
                f"checkpoint step {step} has no validation loss from the same step; "
                "trainer.test_freq and trainer.save_freq must be aligned"
            )
        if decision == 0:
            if handler.rank == 0:
                print(
                    f"Skipped checkpoint at step {step}: {BEST_METRIC_NAME}={validation_loss:.8f}, "
                    f"best={_STATE.best_loss:.8f}, min_delta={min_delta}"
                )
            return

        original_save_checkpoint(handler, step)
        if handler.rank == 0:
            checkpoint_path = save_path / f"global_step_{step}"
            for pattern in ("optim_world_size_*.pt", "extra_state_world_size_*.pt", "data_*.pt"):
                for state_file in checkpoint_path.glob(pattern):
                    state_file.unlink()
            latest_tracker = save_path / "latest_checkpointed_iteration.txt"
            if latest_tracker.exists():
                latest_tracker.unlink()
            write_best_state(save_path, validation_loss, step)
            print(
                f"Saved new best checkpoint at step {step}: "
                f"{BEST_METRIC_NAME}={validation_loss:.8f}"
            )
        torch.distributed.barrier()
        _STATE.best_loss = validation_loss
        _STATE.best_step = step

    sft_trainer.Tracking = ValidationTracking
    sft_trainer.CheckpointHandler.save_checkpoint = save_best_checkpoint


def main() -> None:
    from verl.trainer import sft_trainer

    install_best_checkpoint_policy(sft_trainer)
    sft_trainer.main()
    if not _STATE.best_step:
        raise RuntimeError("training finished without a finite validation-loss checkpoint")


if __name__ == "__main__":
    main()
