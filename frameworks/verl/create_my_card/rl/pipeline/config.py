"""JSON configuration loader for the multi-stage pipeline."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .contracts import (
    PIPELINE_SCHEMA_VERSION,
    STAGE_ORDER,
    TASK_NAME,
    CommandSpec,
    PipelineError,
    PipelineSpec,
    StageSpec,
)


def _object(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PipelineError(f"{label} must be an object")
    return value


def _non_empty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PipelineError(f"{label} must be a non-empty string")
    return value


def _string_list(value: Any, label: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "an array" if allow_empty else "a non-empty array"
        raise PipelineError(f"{label} must be {qualifier} of strings")
    if not all(isinstance(item, str) and item for item in value):
        raise PipelineError(f"{label} must contain only non-empty strings")
    return tuple(value)


def _load_command(value: Any, label: str) -> CommandSpec:
    command = _object(value, label)
    env_payload = command.get("env", {})
    env = _object(env_payload, f"{label}.env")
    if not all(
        isinstance(key, str)
        and key
        and isinstance(item, (str, int, float, bool))
        for key, item in env.items()
    ):
        raise PipelineError(f"{label}.env values must be scalar strings/numbers/booleans")
    return CommandSpec(
        name=_non_empty_string(command.get("name"), f"{label}.name"),
        argv=_string_list(command.get("argv"), f"{label}.argv"),
        env={key: str(item) for key, item in env.items()},
        cwd=_non_empty_string(command.get("cwd", "{repo_root}"), f"{label}.cwd"),
    )


def _load_stage(value: Any, index: int) -> StageSpec:
    stage = _object(value, f"stages[{index}]")
    name = _non_empty_string(stage.get("name"), f"stages[{index}].name")
    enabled = stage.get("enabled", True)
    if not isinstance(enabled, bool):
        raise PipelineError(f"stages[{index}].enabled must be boolean")
    backend = _non_empty_string(stage.get("backend"), f"stages[{index}].backend")
    if backend not in {"mock", "command"}:
        raise PipelineError(f"{name}: backend must be mock or command")
    commands_payload = stage.get("commands", [])
    if not isinstance(commands_payload, list):
        raise PipelineError(f"{name}.commands must be an array")
    commands = tuple(
        _load_command(command, f"{name}.commands[{command_index}]")
        for command_index, command in enumerate(commands_payload)
    )
    if backend == "command" and enabled and not commands:
        raise PipelineError(f"{name}: command backend requires at least one command")

    return StageSpec(
        name=name,
        enabled=enabled,
        backend=backend,
        dataset_dir=_non_empty_string(stage.get("dataset_dir"), f"{name}.dataset_dir"),
        output_checkpoint=_non_empty_string(
            stage.get("output_checkpoint", f"{{stage_dir}}/checkpoint"),
            f"{name}.output_checkpoint",
        ),
        dataset_files=_string_list(
            stage.get("dataset_files"), f"{name}.dataset_files"
        ),
        commands=commands,
    )


def load_pipeline_spec(path: Path, *, repo_root: Path | None = None) -> PipelineSpec:
    """Load a pipeline config and reject ambiguous or forward-incompatible input."""

    path = path.resolve()
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PipelineError(f"invalid pipeline config: {path}: {exc}") from exc
    root = _object(payload, "pipeline config")

    schema_version = _non_empty_string(root.get("schema_version"), "schema_version")
    if schema_version != PIPELINE_SCHEMA_VERSION:
        raise PipelineError(
            f"unsupported pipeline schema {schema_version!r}; expected {PIPELINE_SCHEMA_VERSION!r}"
        )
    task = _non_empty_string(root.get("task"), "task")
    if task != TASK_NAME:
        raise PipelineError(f"this pipeline currently supports only task={TASK_NAME!r}")

    run = _object(root.get("run"), "run")
    execution_mode = _non_empty_string(run.get("execution_mode", "scaffold"), "run.execution_mode")
    if execution_mode not in {"scaffold", "smoke", "train"}:
        raise PipelineError("run.execution_mode must be scaffold, smoke, or train")

    stages_payload = root.get("stages")
    if not isinstance(stages_payload, list):
        raise PipelineError("stages must be an array")
    stages = tuple(_load_stage(value, index) for index, value in enumerate(stages_payload))
    names = tuple(stage.name for stage in stages)
    if names != STAGE_ORDER:
        raise PipelineError(f"stages must be declared exactly in order {STAGE_ORDER}, got {names}")
    if not all(stage.enabled for stage in stages):
        raise PipelineError("the initial scaffold requires rft, dpo, and grpo to all be enabled")
    resolved_repo_root = (
        repo_root.resolve()
        if repo_root is not None
        else Path(__file__).resolve().parents[5]
    )
    return PipelineSpec(
        schema_version=schema_version,
        task=task,
        execution_mode=execution_mode,
        output_root=_non_empty_string(run.get("output_root"), "run.output_root"),
        base_checkpoint=_non_empty_string(
            run.get("base_checkpoint"), "run.base_checkpoint"
        ),
        stages=stages,
        config_path=path,
        repo_root=resolved_repo_root,
    )
