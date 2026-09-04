"""Small framework-neutral contracts shared by all training stages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence


PIPELINE_SCHEMA_VERSION = "create-my-card.rl-pipeline.v1"
STAGE_MANIFEST_SCHEMA_VERSION = "create-my-card.rl-stage-manifest.v1"
RUN_MANIFEST_SCHEMA_VERSION = "create-my-card.rl-run-manifest.v1"
TASK_NAME = "taskspec_to_dsl"
STAGE_ORDER = ("rft", "dpo", "grpo")


class PipelineError(RuntimeError):
    """Raised when a pipeline contract or execution invariant is violated."""


@dataclass(frozen=True)
class CommandSpec:
    """One foreground command executed without a shell."""

    name: str
    argv: tuple[str, ...]
    env: Mapping[str, str] = field(default_factory=dict)
    cwd: str = "{repo_root}"


@dataclass(frozen=True)
class StageSpec:
    name: str
    enabled: bool
    backend: str
    dataset_dir: str
    output_checkpoint: str
    dataset_files: tuple[str, ...]
    commands: tuple[CommandSpec, ...] = ()


@dataclass(frozen=True)
class PipelineSpec:
    schema_version: str
    task: str
    execution_mode: str
    output_root: str
    base_checkpoint: str
    stages: tuple[StageSpec, ...]
    config_path: Path
    repo_root: Path


@dataclass(frozen=True)
class StageContext:
    run_id: str
    execution_mode: str
    repo_root: Path
    run_dir: Path
    stage_dir: Path
    dataset_dir: Path
    input_checkpoint: str
    output_checkpoint: Path
    variables: Mapping[str, str]


@dataclass(frozen=True)
class StageResult:
    stage: str
    backend: str
    input_checkpoint: str
    output_checkpoint: str
    manifest_path: Path
    command_logs: Sequence[str] = ()
