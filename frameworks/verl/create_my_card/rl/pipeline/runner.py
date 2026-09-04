"""Sequential, resumable RFT -> DPO -> GRPO runner."""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .backends import BACKENDS, format_template
from .contracts import (
    RUN_MANIFEST_SCHEMA_VERSION,
    STAGE_MANIFEST_SCHEMA_VERSION,
    PipelineError,
    PipelineSpec,
    StageContext,
    StageResult,
    StageSpec,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _load_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"invalid {label}: {path}: {exc}") from exc
    if not isinstance(value, Mapping):
        raise PipelineError(f"{label} must be a JSON object: {path}")
    return value


class PipelineRunner:
    def __init__(
        self,
        spec: PipelineSpec,
        *,
        run_id: str,
        backend_override: str | None = None,
        resume: bool = False,
    ) -> None:
        if (
            len(run_id) > 128
            or run_id in {".", ".."}
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", run_id) is None
        ):
            raise PipelineError(
                "run_id must be 1-128 characters, start with an ASCII letter/digit, "
                "and contain only letters, digits, '.', '_', or '-'"
            )
        if backend_override is not None and backend_override not in BACKENDS:
            raise PipelineError(f"unsupported backend override: {backend_override}")
        self.spec = spec
        self.run_id = run_id
        self.backend_override = backend_override
        self.resume = resume

        selected_backends = {
            backend_override or stage.backend for stage in spec.stages if stage.enabled
        }
        if spec.execution_mode == "scaffold" and selected_backends != {"mock"}:
            raise PipelineError(
                "scaffold mode is orchestration-only; pass --backend mock. "
                "Use smoke or train mode for command backends."
            )

        root_variables = {"repo_root": str(spec.repo_root)}
        output_root_text = format_template(
            spec.output_root, root_variables, label="run.output_root"
        )
        output_root = Path(output_root_text)
        if not output_root.is_absolute():
            output_root = spec.repo_root / output_root
        self.output_root = output_root.resolve()
        self.run_dir = self.output_root / run_id

    def _base_variables(self, stage: StageSpec, input_checkpoint: str) -> dict[str, str]:
        stage_dir = self.run_dir / "stages" / stage.name
        variables = {
            "repo_root": str(self.spec.repo_root),
            "run_dir": str(self.run_dir),
            "stage": stage.name,
            "stage_dir": str(stage_dir),
            "input_checkpoint": input_checkpoint,
            "execution_mode": self.spec.execution_mode,
        }
        dataset_text = format_template(
            stage.dataset_dir, variables, label=f"{stage.name}.dataset_dir"
        )
        dataset_dir = Path(dataset_text)
        if not dataset_dir.is_absolute():
            dataset_dir = self.spec.repo_root / dataset_dir
        variables["dataset_dir"] = str(dataset_dir.resolve())
        output_text = format_template(
            stage.output_checkpoint,
            variables,
            label=f"{stage.name}.output_checkpoint",
        )
        output_checkpoint = Path(output_text)
        if not output_checkpoint.is_absolute():
            output_checkpoint = self.spec.repo_root / output_checkpoint
        variables["output_checkpoint"] = str(output_checkpoint.resolve())
        return variables

    def _context(self, stage: StageSpec, input_checkpoint: str) -> StageContext:
        variables = self._base_variables(stage, input_checkpoint)
        stage_dir = Path(variables["stage_dir"])
        stage_dir.mkdir(parents=True, exist_ok=True)
        return StageContext(
            run_id=self.run_id,
            execution_mode=self.spec.execution_mode,
            repo_root=self.spec.repo_root,
            run_dir=self.run_dir,
            stage_dir=stage_dir,
            dataset_dir=Path(variables["dataset_dir"]),
            input_checkpoint=input_checkpoint,
            output_checkpoint=Path(variables["output_checkpoint"]),
            variables=variables,
        )

    def _resume_stage(
        self, stage: StageSpec, context: StageContext, backend_name: str
    ) -> StageResult | None:
        manifest_path = context.stage_dir / "stage-manifest.json"
        if not manifest_path.exists():
            return None
        if not self.resume:
            raise PipelineError(
                f"{stage.name}: stage manifest already exists; use --resume or a new run_id"
            )
        manifest = _load_json(manifest_path, f"{stage.name} stage manifest")
        expected_output = (
            context.input_checkpoint
            if backend_name == "command" and self.spec.execution_mode == "smoke"
            else str(context.output_checkpoint)
        )
        expected = {
            "schema_version": STAGE_MANIFEST_SCHEMA_VERSION,
            "status": "succeeded",
            "stage": stage.name,
            "backend": backend_name,
            "execution_mode": self.spec.execution_mode,
            "input_checkpoint": context.input_checkpoint,
            "output_checkpoint": expected_output,
            "dataset_dir": str(context.dataset_dir),
        }
        mismatches = {
            key: {"expected": value, "actual": manifest.get(key)}
            for key, value in expected.items()
            if manifest.get(key) != value
        }
        if mismatches:
            raise PipelineError(
                f"{stage.name}: refusing unsafe resume because manifest differs: {mismatches}"
            )
        output_checkpoint = manifest.get("output_checkpoint")
        if not isinstance(output_checkpoint, str) or not Path(output_checkpoint).exists():
            raise PipelineError(
                f"{stage.name}: resume manifest points to a missing checkpoint: "
                f"{output_checkpoint!r}"
            )
        return StageResult(
            stage=stage.name,
            backend=backend_name,
            input_checkpoint=context.input_checkpoint,
            output_checkpoint=output_checkpoint,
            manifest_path=manifest_path,
            command_logs=tuple(manifest.get("command_logs", ())),
        )

    def _execute_stage(self, stage: StageSpec, input_checkpoint: str) -> StageResult:
        backend_name = self.backend_override or stage.backend
        backend = BACKENDS[backend_name]
        context = self._context(stage, input_checkpoint)
        resumed = self._resume_stage(stage, context, backend_name)
        if resumed is not None:
            return resumed

        started_at = _now()
        try:
            result = backend.execute(stage, context)
        except Exception as exc:
            _atomic_json(
                context.stage_dir / "stage-manifest.json",
                {
                    "schema_version": STAGE_MANIFEST_SCHEMA_VERSION,
                    "status": "failed",
                    "stage": stage.name,
                    "backend": backend_name,
                    "input_checkpoint": input_checkpoint,
                    "output_checkpoint": str(context.output_checkpoint),
                    "dataset_dir": str(context.dataset_dir),
                    "started_at": started_at,
                    "finished_at": _now(),
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
            raise
        _atomic_json(
            result.manifest_path,
            {
                "schema_version": STAGE_MANIFEST_SCHEMA_VERSION,
                "status": "succeeded",
                "stage": stage.name,
                "backend": backend_name,
                "execution_mode": self.spec.execution_mode,
                "input_checkpoint": input_checkpoint,
                "output_checkpoint": result.output_checkpoint,
                "dataset_dir": str(context.dataset_dir),
                "dataset_files": list(stage.dataset_files),
                "started_at": started_at,
                "finished_at": _now(),
                "command_logs": list(result.command_logs),
            },
        )
        return result

    def run(self, *, stop_after: str | None = None) -> Mapping[str, Any]:
        enabled_stage_names = [stage.name for stage in self.spec.stages if stage.enabled]
        if stop_after is not None and stop_after not in enabled_stage_names:
            raise PipelineError(
                f"stop_after must name an enabled stage: {enabled_stage_names}"
            )
        if self.run_dir.exists() and not self.resume:
            # Datasets are prepared independently before a command-backend run.
            # Permit that subtree, but do not reuse execution state implicitly.
            unexpected = sorted(
                child.name
                for child in self.run_dir.iterdir()
                if child.name != "datasets"
            )
            if unexpected:
                raise PipelineError(
                    "run directory contains prior execution state; use --resume or "
                    f"a new run_id: {self.run_dir}: {unexpected}"
                )
        self.run_dir.mkdir(parents=True, exist_ok=True)
        input_checkpoint = format_template(
            self.spec.base_checkpoint,
            {"repo_root": str(self.spec.repo_root), "run_dir": str(self.run_dir)},
            label="run.base_checkpoint",
        )
        stage_results: list[StageResult] = []
        for stage in self.spec.stages:
            if not stage.enabled:
                continue
            result = self._execute_stage(stage, input_checkpoint)
            stage_results.append(result)
            input_checkpoint = result.output_checkpoint
            if stage.name == stop_after:
                break

        completed_names = [result.stage for result in stage_results]
        remaining_names = [
            name for name in enabled_stage_names if name not in completed_names
        ]

        manifest = {
            "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
            "status": "paused_after_stage" if remaining_names else "succeeded",
            "run_id": self.run_id,
            "task": self.spec.task,
            "execution_mode": self.spec.execution_mode,
            "config_path": str(self.spec.config_path),
            "base_checkpoint": self.spec.base_checkpoint,
            "final_checkpoint": input_checkpoint,
            "next_stage": remaining_names[0] if remaining_names else None,
            "mock_only": all(result.backend == "mock" for result in stage_results),
            "stages": [
                {
                    "name": result.stage,
                    "backend": result.backend,
                    "input_checkpoint": result.input_checkpoint,
                    "output_checkpoint": result.output_checkpoint,
                    "manifest": str(result.manifest_path),
                }
                for result in stage_results
            ],
            "finished_at": _now(),
        }
        _atomic_json(self.run_dir / "run-manifest.json", manifest)
        return manifest
