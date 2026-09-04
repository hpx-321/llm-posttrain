"""Replaceable execution backends for post-training stages."""

from __future__ import annotations

import json
import os
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Mapping

from .contracts import CommandSpec, PipelineError, StageContext, StageResult, StageSpec


def format_template(value: str, variables: Mapping[str, str], *, label: str) -> str:
    try:
        return value.format_map(dict(variables))
    except KeyError as exc:
        raise PipelineError(f"{label} references unknown placeholder {exc.args[0]!r}") from exc
    except ValueError as exc:
        raise PipelineError(f"{label} has invalid format syntax: {exc}") from exc


class StageBackend(ABC):
    name: str

    @abstractmethod
    def execute(self, spec: StageSpec, context: StageContext) -> StageResult:
        raise NotImplementedError


class MockBackend(StageBackend):
    """Materialize contract-shaped artifacts without importing training libraries."""

    name = "mock"

    def execute(self, spec: StageSpec, context: StageContext) -> StageResult:
        context.dataset_dir.mkdir(parents=True, exist_ok=True)
        for relative_name in spec.dataset_files:
            path = context.dataset_dir / relative_name
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                path.write_text(
                    json.dumps(
                        {
                            "mock": True,
                            "stage": spec.name,
                            "task": "taskspec_to_dsl",
                            "warning": "scaffold artifact; never use for training",
                        },
                        ensure_ascii=False,
                    )
                    + "\n",
                    encoding="utf-8",
                )

        context.output_checkpoint.mkdir(parents=True, exist_ok=False)
        (context.output_checkpoint / "MOCK_CHECKPOINT.json").write_text(
            json.dumps(
                {
                    "mock": True,
                    "stage": spec.name,
                    "input_checkpoint": context.input_checkpoint,
                    "warning": "orchestration-only checkpoint; contains no model weights",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return StageResult(
            stage=spec.name,
            backend=self.name,
            input_checkpoint=context.input_checkpoint,
            output_checkpoint=str(context.output_checkpoint),
            manifest_path=context.stage_dir / "stage-manifest.json",
        )


class CommandBackend(StageBackend):
    """Run stage commands in the foreground and require a concrete checkpoint."""

    name = "command"

    @staticmethod
    def _validate_inputs(spec: StageSpec, context: StageContext) -> None:
        input_checkpoint = Path(context.input_checkpoint)
        if not input_checkpoint.exists():
            raise PipelineError(
                f"{spec.name}: input checkpoint does not exist: {input_checkpoint}"
            )
        if not context.dataset_dir.is_dir():
            raise PipelineError(
                f"{spec.name}: dataset directory does not exist: {context.dataset_dir}"
            )
        missing = [
            relative_name
            for relative_name in spec.dataset_files
            if not (context.dataset_dir / relative_name).is_file()
        ]
        if missing:
            raise PipelineError(
                f"{spec.name}: dataset directory is missing required files: {missing}"
            )
        if context.output_checkpoint.exists():
            raise PipelineError(
                f"{spec.name}: output checkpoint already exists: {context.output_checkpoint}"
            )

    @staticmethod
    def _run_command(
        command: CommandSpec,
        context: StageContext,
        *,
        index: int,
    ) -> str:
        variables = context.variables
        argv = [
            format_template(value, variables, label=f"{context.stage_dir.name}.{command.name}.argv")
            for value in command.argv
        ]
        if not argv:
            raise PipelineError(f"{context.stage_dir.name}.{command.name}: argv is empty")
        cwd = Path(
            format_template(command.cwd, variables, label=f"{command.name}.cwd")
        )
        if not cwd.is_dir():
            raise PipelineError(f"{command.name}: cwd does not exist: {cwd}")
        environment = os.environ.copy()
        for key, value in command.env.items():
            environment[key] = format_template(value, variables, label=f"{command.name}.env.{key}")

        log_path = context.stage_dir / f"command-{index:02d}-{command.name}.log"
        with log_path.open("w", encoding="utf-8") as stream:
            stream.write("argv=" + json.dumps(argv, ensure_ascii=False) + "\n")
            stream.flush()
            completed = subprocess.run(
                argv,
                cwd=cwd,
                env=environment,
                stdout=stream,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
            )
        if completed.returncode != 0:
            raise PipelineError(
                f"{command.name} failed with exit code {completed.returncode}; see {log_path}"
            )
        return str(log_path)

    def execute(self, spec: StageSpec, context: StageContext) -> StageResult:
        self._validate_inputs(spec, context)
        logs = [
            self._run_command(command, context, index=index)
            for index, command in enumerate(spec.commands, start=1)
        ]
        if context.execution_mode == "smoke":
            return StageResult(
                stage=spec.name,
                backend=self.name,
                input_checkpoint=context.input_checkpoint,
                output_checkpoint=context.input_checkpoint,
                manifest_path=context.stage_dir / "stage-manifest.json",
                command_logs=logs,
            )
        if not context.output_checkpoint.exists():
            raise PipelineError(
                f"{spec.name}: commands succeeded but checkpoint was not created: "
                f"{context.output_checkpoint}"
            )
        return StageResult(
            stage=spec.name,
            backend=self.name,
            input_checkpoint=context.input_checkpoint,
            output_checkpoint=str(context.output_checkpoint),
            manifest_path=context.stage_dir / "stage-manifest.json",
            command_logs=logs,
        )


BACKENDS: Mapping[str, StageBackend] = {
    "mock": MockBackend(),
    "command": CommandBackend(),
}
