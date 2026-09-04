"""Offline adapter for design-card-check's documented CLI contract.

The packaged CLI is intentionally used only by the no-gradient Stage 0 audit.
Online training should replace this subprocess boundary with a long-lived
Python worker or reward service after behavior parity is proven.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9._-]+")
_DUMP_BOUNDS_RE = re.compile(r"^\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]$")
_RENDER_BUNDLE = "com.example.myapplication"
VENDORED_CHECKER_ROOT = (
    Path(__file__).resolve().parents[1]
    / "vendor"
    / "design-card-check-plugin-0.2.0"
    / "package"
    / "design-check"
)


def default_checker_root() -> Path:
    """Return an explicit override or the checker vendored with this module."""

    override = os.environ.get("DESIGN_CHECK_ROOT")
    return Path(override).expanduser() if override else VENDORED_CHECKER_ROOT


@dataclass(frozen=True)
class CheckerConfig:
    checker_root: Path = field(default_factory=default_checker_root)
    python_executable: str = sys.executable
    timeout_seconds: float = 30.0
    max_retries: int = 1

    @property
    def script_path(self) -> Path:
        return self.checker_root / "scripts" / "check_card.py"


@dataclass(frozen=True)
class CheckerResult:
    exit_code: int
    findings: tuple[dict[str, Any], ...]
    summary: Mapping[str, Any]
    meta: Mapping[str, Any]
    stderr: str
    elapsed_ms: float
    attempts: int
    l2_requested: bool
    l2_evaluated: bool

    def to_diagnostics(self) -> dict[str, Any]:
        return {
            "exit_code": self.exit_code,
            "summary": dict(self.summary),
            "meta": dict(self.meta),
            "stderr": self.stderr,
            "elapsed_ms": self.elapsed_ms,
            "attempts": self.attempts,
            "l2_requested": self.l2_requested,
            "l2_evaluated": self.l2_evaluated,
        }


class CheckerExecutionError(RuntimeError):
    """A checker/environment failure that must not become negative reward."""

    def __init__(
        self,
        message: str,
        *,
        kind: str,
        retryable: bool,
        attempts: int = 0,
        stderr: str = "",
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable
        self.attempts = attempts
        self.stderr = stderr


Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass
class DesignCheckerAdapter:
    config: CheckerConfig
    runner: Runner = field(default=subprocess.run, repr=False)

    def __post_init__(self) -> None:
        if self.config.timeout_seconds <= 0:
            raise ValueError("checker timeout_seconds must be positive")
        if self.config.max_retries < 0:
            raise ValueError("checker max_retries must be non-negative")
        if not self.config.script_path.is_file():
            raise CheckerExecutionError(
                f"design checker script is missing: {self.config.script_path}",
                kind="checker_not_found",
                retryable=False,
            )

    def check(
        self,
        a2ui_dsl: str,
        *,
        sample_id: str,
        task_spec: Mapping[str, Any],
        query_text: str | None = None,
        layout_path: Path | None = None,
        include_delegated: bool = False,
    ) -> CheckerResult:
        if not a2ui_dsl.strip():
            raise ValueError("a2ui_dsl must not be empty")
        if not isinstance(task_spec, Mapping):
            raise ValueError("task_spec must be an object")
        if layout_path is not None:
            self._validate_l2_dump(layout_path)

        # Always namespace reward cases.  The vendored 2x4 checker contains a
        # legacy owner-verdict table keyed by case ids such as ``A-q8``.  A
        # model/sample id must never be able to opt into those fixture-specific
        # verdicts merely by sharing that spelling.
        normalized_id = _SAFE_ID_RE.sub("-", sample_id).strip("-.") or "rollout"
        # The suffix also prevents the checker's legacy ``q<digits>$`` fallback
        # from extracting a manual-verdict key if that fallback is re-enabled.
        safe_id = f"rl-{normalized_id}-candidate"
        last_error: CheckerExecutionError | None = None
        with tempfile.TemporaryDirectory(prefix="cmc-reward-") as temporary:
            # The checker deliberately clears query/task_spec for --dsl input.
            # A three-file case directory is required so scene, asset and size
            # rules receive the same TaskSpec context as the model.
            case_dir = Path(temporary) / safe_id
            case_dir.mkdir()
            dsl_path = case_dir / "card.genui.jsonl"
            dsl_path.write_text(a2ui_dsl.rstrip() + "\n", encoding="utf-8")
            (case_dir / "query.txt").write_text(
                (query_text or str(task_spec.get("userQuery") or "")).strip() + "\n",
                encoding="utf-8",
            )
            (case_dir / "task-spec.json").write_text(
                json.dumps(
                    dict(task_spec),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n",
                encoding="utf-8",
            )
            command = self._command(
                case_dir,
                layout_path=layout_path,
                include_delegated=include_delegated,
            )
            for attempt in range(1, self.config.max_retries + 2):
                try:
                    return self._run_once(
                        command,
                        attempt=attempt,
                        l2_requested=layout_path is not None,
                    )
                except CheckerExecutionError as exc:
                    last_error = exc
                    if not exc.retryable or attempt > self.config.max_retries:
                        raise
        assert last_error is not None
        raise last_error

    def _command(
        self,
        case_dir: Path,
        *,
        layout_path: Path | None,
        include_delegated: bool,
    ) -> list[str]:
        command = [
            self.config.python_executable,
            str(self.config.script_path),
            "--dir",
            str(case_dir),
            "--format",
            "json",
        ]
        if layout_path is not None:
            command.extend(["--layout", str(layout_path.resolve())])
            if include_delegated:
                command.append("--include-delegated")
        return command

    def _run_once(
        self,
        command: Sequence[str],
        *,
        attempt: int,
        l2_requested: bool,
    ) -> CheckerResult:
        environment = os.environ.copy()
        environment["PYTHONUTF8"] = "1"
        environment["PYTHONIOENCODING"] = "utf-8"
        started = time.perf_counter()
        try:
            completed = self.runner(
                list(command),
                cwd=str(self.config.checker_root),
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.config.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CheckerExecutionError(
                f"design checker timed out after {self.config.timeout_seconds:g}s",
                kind="timeout",
                retryable=True,
                attempts=attempt,
                stderr=_timeout_stderr(exc),
            ) from exc
        except OSError as exc:
            raise CheckerExecutionError(
                f"failed to start design checker: {exc}",
                kind="spawn_error",
                retryable=True,
                attempts=attempt,
            ) from exc

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        if completed.returncode == 2:
            raise CheckerExecutionError(
                "design checker reported an internal/input/environment failure",
                kind="checker_exit_2",
                retryable=True,
                attempts=attempt,
                stderr=completed.stderr,
            )
        if completed.returncode not in (0, 1):
            raise CheckerExecutionError(
                f"design checker returned undocumented exit code {completed.returncode}",
                kind="unexpected_exit",
                retryable=True,
                attempts=attempt,
                stderr=completed.stderr,
            )
        payload = _parse_checker_json(completed.stdout)
        findings = payload.get("findings")
        summary = payload.get("summary")
        meta = payload.get("meta")
        if not isinstance(findings, list) or not all(
            isinstance(finding, dict) for finding in findings
        ):
            raise CheckerExecutionError(
                "design checker JSON has no valid findings list",
                kind="invalid_output",
                retryable=True,
                attempts=attempt,
                stderr=completed.stderr,
            )
        if not isinstance(summary, dict) or not isinstance(meta, dict):
            raise CheckerExecutionError(
                "design checker JSON has no valid summary/meta objects",
                kind="invalid_output",
                retryable=True,
                attempts=attempt,
                stderr=completed.stderr,
            )
        has_p0 = any(finding.get("severity") == "P0" for finding in findings)
        expected_exit = 1 if has_p0 else 0
        if completed.returncode != expected_exit:
            raise CheckerExecutionError(
                "design checker exit code contradicts its finding severities",
                kind="contract_mismatch",
                retryable=False,
                attempts=attempt,
                stderr=completed.stderr,
            )
        return CheckerResult(
            exit_code=completed.returncode,
            findings=tuple(findings),
            summary=summary,
            meta=meta,
            stderr=completed.stderr,
            elapsed_ms=elapsed_ms,
            attempts=attempt,
            l2_requested=l2_requested,
            l2_evaluated=l2_requested,
        )

    @staticmethod
    def _validate_l2_dump(layout_path: Path) -> None:
        if not layout_path.is_file():
            raise CheckerExecutionError(
                f"L2 dump is missing: {layout_path}",
                kind="layout_not_found",
                retryable=False,
            )
        try:
            payload = json.loads(layout_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise CheckerExecutionError(
                f"L2 dump is not valid JSON: {layout_path}",
                kind="invalid_layout",
                retryable=False,
            ) from exc
        if not _contains_bundle(payload, _RENDER_BUNDLE):
            raise CheckerExecutionError(
                "L2 dump does not contain the rendered card application; "
                "it may be a launcher/desktop dump",
                kind="wrong_layout_surface",
                retryable=True,
            )
        if not _contains_card_geometry(payload):
            raise CheckerExecutionError(
                "L2 dump contains the render application but no complete card geometry; "
                "expected a bounded root plus at least one bounded component",
                kind="incomplete_layout",
                retryable=True,
            )


def _parse_checker_json(stdout: str) -> dict[str, Any]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise CheckerExecutionError(
            "design checker did not emit valid JSON",
            kind="invalid_output",
            retryable=True,
        ) from exc
    if not isinstance(payload, dict):
        raise CheckerExecutionError(
            "design checker JSON root must be an object",
            kind="invalid_output",
            retryable=True,
        )
    return payload


def _contains_bundle(value: Any, bundle_name: str) -> bool:
    if isinstance(value, dict):
        if value.get("bundleName") == bundle_name:
            return True
        return any(_contains_bundle(child, bundle_name) for child in value.values())
    if isinstance(value, list):
        return any(_contains_bundle(child, bundle_name) for child in value)
    return False


def _contains_card_geometry(value: Any) -> bool:
    attributes = list(_iter_dump_attributes(value))
    bounded = [attrs for attrs in attributes if _has_positive_bounds(attrs.get("bounds"))]
    has_root = any(
        str(attrs.get("id") or attrs.get("key") or "") == "root"
        or str(attrs.get("id") or attrs.get("key") or "").endswith("_root")
        for attrs in bounded
    )
    bounded_components = [
        attrs
        for attrs in bounded
        if str(attrs.get("id") or attrs.get("key") or "")
    ]
    return has_root and len(bounded_components) >= 2


def _iter_dump_attributes(value: Any):
    if isinstance(value, dict):
        attributes = value.get("attributes")
        if isinstance(attributes, dict):
            yield attributes
        for child in value.values():
            yield from _iter_dump_attributes(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_dump_attributes(child)


def _has_positive_bounds(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    match = _DUMP_BOUNDS_RE.fullmatch(value)
    if match is None:
        return False
    left, top, right, bottom = map(int, match.groups())
    return right > left and bottom > top


def _timeout_stderr(exc: subprocess.TimeoutExpired) -> str:
    stderr = exc.stderr
    if isinstance(stderr, bytes):
        return stderr.decode("utf-8", errors="replace")
    return stderr or ""
