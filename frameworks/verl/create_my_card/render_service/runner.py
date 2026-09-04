"""Build, install, render, screenshot, and dump one A2UI card on Windows."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from .config import RenderServiceConfig


_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9._-]+")
_VALID_SIZES = {"2x2", "2x4"}
_EXTENDED_CATALOG = "ohos.a2ui.extended.catalog"
_FORM_CATALOG = "ohos.a2ui.extended.catalog.form"
_CAPTURE_RETRIES = 3
_CAPTURE_RETRY_WAIT_SECONDS = 1.0


class RenderInfrastructureError(RuntimeError):
    """A renderer, build tool, device, or artifact validation failure."""


class RenderBusyError(RenderInfrastructureError):
    """The single device is already rendering another request."""


@dataclass(frozen=True)
class RenderResult:
    sample_id: str
    layout: Mapping[str, Any]
    screenshot_path: Path
    layout_path: Path
    log_path: Path
    elapsed_ms: float
    device_sn: str


class DeviceRenderer:
    """A single-process, single-device renderer guarded by a mutex."""

    def __init__(self, config: RenderServiceConfig):
        config.validate()
        self.config = config
        self._lock = threading.Lock()

    @property
    def busy(self) -> bool:
        acquired = self._lock.acquire(blocking=False)
        if acquired:
            self._lock.release()
            return False
        return True

    def health(self) -> dict[str, Any]:
        targets = self.list_targets()
        selected = self._select_target(targets)
        return {
            "status": "ok",
            "bundle": self.config.bundle,
            "deviceReady": True,
            "deviceSn": selected,
            "targets": targets,
            "busy": self.busy,
        }

    def list_targets(self) -> list[str]:
        result = self._run(
            [str(self.config.hdc), "list", "targets", "-v"],
            timeout=min(self.config.timeout_seconds, 30.0),
        )
        return parse_hdc_targets(result.stdout, result.stderr)
    def render(self, sample_id: str, size: str, a2ui: Any) -> RenderResult:
        if not self._lock.acquire(blocking=False):
            raise RenderBusyError("the render device is busy")
        try:
            return self._render_locked(sample_id, size, a2ui)
        finally:
            self._lock.release()

    def _render_locked(self, sample_id: str, size: str, a2ui: Any) -> RenderResult:
        safe_id = _safe_id(sample_id)
        if size not in _VALID_SIZES:
            raise ValueError(f"size must be one of {sorted(_VALID_SIZES)}, got {size!r}")
        records = parse_a2ui_records(a2ui)
        targets = self.list_targets()
        device_sn = self._select_target(targets)

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        job_id = f"{stamp}-{safe_id}-{uuid.uuid4().hex[:8]}"
        job_dir = self.config.artifact_root / job_id
        job_dir.mkdir(parents=True, exist_ok=False)
        log_path = job_dir / "render.log"
        request_path = job_dir / "request.json"
        screenshot_path = job_dir / "screenshot.jpeg"
        layout_path = job_dir / "layout.json"
        request_path.write_text(
            json.dumps(
                {"id": sample_id, "size": size, "a2ui": records},
                ensure_ascii=False,
                indent=2,
                allow_nan=False,
            )
            + "\n",
            encoding="utf-8",
        )

        started = time.perf_counter()
        original = self.config.rawfile_target.read_bytes()
        try:
            _atomic_write_json(self.config.rawfile_target, records)
            self._build(log_path)
            hap_path = self._find_hap()
            self._install_and_start(hap_path, device_sn, log_path)
            time.sleep(self.config.start_wait_seconds)
            self._capture(device_sn, screenshot_path, layout_path, log_path, job_id)
            layout = _load_layout(layout_path)
            if not _contains_bundle(layout, self.config.bundle):
                raise RenderInfrastructureError(
                    f"dumpLayout does not contain bundleName={self.config.bundle}"
                )
        except Exception as exc:
            self._append_log(log_path, f"ERROR: {type(exc).__name__}: {exc}\n")
            raise
        finally:
            _atomic_write_bytes(self.config.rawfile_target, original)

        return RenderResult(
            sample_id=sample_id,
            layout=layout,
            screenshot_path=screenshot_path,
            layout_path=layout_path,
            log_path=log_path,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            device_sn=device_sn,
        )

    def _select_target(self, targets: list[str]) -> str:
        requested = self.config.device_sn
        if requested:
            if requested not in targets:
                raise RenderInfrastructureError(
                    f"configured device {requested!r} is not online; targets={targets}"
                )
            return requested
        if not targets:
            raise RenderInfrastructureError("hdc list targets returned no devices")
        if len(targets) != 1:
            raise RenderInfrastructureError(
                "multiple HDC devices are online; set A2UI_RENDER_DEVICE_SN explicitly: "
                f"{targets}"
            )
        return targets[0]

    def _build(self, log_path: Path) -> None:
        environment = os.environ.copy()
        java_bin = self.config.java_home / "bin"
        environment["DEVECO_SDK_HOME"] = str(self.config.sdk_home)
        environment["JAVA_HOME"] = str(self.config.java_home)
        environment["PATH"] = os.pathsep.join(
            [
                str(java_bin),
                str(self.config.node.parent),
                str(self.config.hdc.parent),
                environment.get("PATH", ""),
            ]
        )
        for action in ("clean", "assembleHap"):
            command = self._hvigor_command(action)
            result = self._run(
                command,
                cwd=self.config.project_root,
                env=environment,
                timeout=self.config.timeout_seconds,
            )
            self._log_result(log_path, result)

    def _hvigor_command(self, action: str) -> list[str]:
        suffix = self.config.hvigor.suffix.lower()
        if suffix == ".js":
            return [str(self.config.node), str(self.config.hvigor), action]
        if suffix in {".bat", ".cmd"}:
            return ["cmd", "/d", "/c", str(self.config.hvigor), action]
        return [str(self.config.hvigor), action]

    def _find_hap(self) -> Path:
        candidates = sorted(
            self.config.hap_output_dir.glob("*.hap"),
            key=lambda item: item.stat().st_mtime_ns,
            reverse=True,
        )
        if not candidates:
            raise RenderInfrastructureError(
                f"Hvigor produced no HAP under {self.config.hap_output_dir}"
            )
        signed = [path for path in candidates if "-signed" in path.name]
        return signed[0] if signed else candidates[0]

    def _install_and_start(self, hap_path: Path, sn: str, log_path: Path) -> None:
        remote_dir = f"/data/local/tmp/a2ui_render_{uuid.uuid4().hex}"
        remote_hap = f"{remote_dir}/{hap_path.name}"
        try:
            self._hdc(sn, ["shell", "mkdir", "-p", remote_dir], log_path=log_path)
            self._hdc(
                sn,
                ["file", "send", str(hap_path), remote_hap],
                timeout=self.config.timeout_seconds,
                log_path=log_path,
            )
            self._hdc(
                sn,
                ["shell", "aa", "force-stop", self.config.bundle],
                check=False,
                log_path=log_path,
            )
            self._hdc(
                sn,
                ["shell", "bm", "uninstall", "-n", self.config.bundle],
                timeout=self.config.timeout_seconds,
                check=False,
                log_path=log_path,
            )
            install = self._hdc(
                sn,
                ["shell", "bm", "install", "-p", remote_dir],
                timeout=self.config.timeout_seconds,
                check=False,
                log_path=log_path,
            )
            _validate_install(install)
        finally:
            self._hdc(
                sn,
                ["shell", "rm", "-rf", remote_dir],
                check=False,
                log_path=log_path,
            )
        self._hdc(
            sn,
            [
                "shell",
                "aa",
                "start",
                "-a",
                self.config.ability,
                "-b",
                self.config.bundle,
                "-m",
                self.config.module,
            ],
            log_path=log_path,
        )

    def _capture(
        self,
        sn: str,
        screenshot_path: Path,
        layout_path: Path,
        log_path: Path,
        job_id: str,
    ) -> None:
        remote_screenshot = f"/data/local/tmp/{job_id}.jpeg"
        remote_layout = f"/data/local/tmp/{job_id}.layout.json"
        try:
            self._capture_screenshot(
                sn, remote_screenshot, screenshot_path, log_path
            )
            self._capture_layout(sn, remote_layout, layout_path, log_path)
        finally:
            self._hdc(
                sn,
                ["shell", "rm", "-f", remote_screenshot, remote_layout],
                check=False,
                log_path=log_path,
            )

    def _capture_screenshot(
        self,
        sn: str,
        remote_path: str,
        local_path: Path,
        log_path: Path,
    ) -> None:
        last_error = "unknown screenshot failure"
        for attempt in range(1, _CAPTURE_RETRIES + 1):
            local_path.unlink(missing_ok=True)
            self._hdc(
                sn,
                ["shell", "rm", "-f", remote_path],
                check=False,
                log_path=log_path,
            )
            snapshot = self._hdc(
                sn,
                ["shell", "snapshot_display", "-f", remote_path],
                check=False,
                log_path=log_path,
            )
            if _hdc_failed(snapshot):
                snapshot = self._hdc(
                    sn,
                    ["shell", "snapshot_display", remote_path],
                    check=False,
                    log_path=log_path,
                )
            if not _hdc_failed(snapshot):
                time.sleep(_CAPTURE_RETRY_WAIT_SECONDS)
                received = self._hdc(
                    sn,
                    ["file", "recv", remote_path, str(local_path)],
                    check=False,
                    log_path=log_path,
                )
                size = local_path.stat().st_size if local_path.is_file() else 0
                if (
                    not _hdc_failed(received)
                    and size > self.config.screenshot_min_bytes
                ):
                    return
                last_error = (
                    f"recv exit={received.returncode}, local screenshot size={size}"
                )
            else:
                last_error = f"snapshot_display exit={snapshot.returncode}"
            self._append_log(
                log_path,
                f"screenshot attempt {attempt}/{_CAPTURE_RETRIES} failed: "
                f"{last_error}\n",
            )
            if attempt < _CAPTURE_RETRIES:
                time.sleep(_CAPTURE_RETRY_WAIT_SECONDS)
        raise RenderInfrastructureError(
            f"failed to capture screenshot after {_CAPTURE_RETRIES} attempts: "
            f"{last_error}; path={local_path}"
        )

    def _capture_layout(
        self,
        sn: str,
        remote_path: str,
        local_path: Path,
        log_path: Path,
    ) -> None:
        last_error = "unknown dumpLayout failure"
        for attempt in range(1, _CAPTURE_RETRIES + 1):
            local_path.unlink(missing_ok=True)
            self._hdc(
                sn,
                ["shell", "rm", "-f", remote_path],
                check=False,
                log_path=log_path,
            )
            dumped = self._hdc(
                sn,
                ["shell", "uitest", "dumpLayout", "-p", remote_path],
                check=False,
                log_path=log_path,
            )
            if not _hdc_failed(dumped):
                received = self._hdc(
                    sn,
                    ["file", "recv", remote_path, str(local_path)],
                    check=False,
                    log_path=log_path,
                )
                size = local_path.stat().st_size if local_path.is_file() else 0
                if not _hdc_failed(received) and size > 0:
                    return
                last_error = f"recv exit={received.returncode}, layout size={size}"
            else:
                last_error = f"dumpLayout exit={dumped.returncode}"
            self._append_log(
                log_path,
                f"layout attempt {attempt}/{_CAPTURE_RETRIES} failed: "
                f"{last_error}\n",
            )
            if attempt < _CAPTURE_RETRIES:
                time.sleep(_CAPTURE_RETRY_WAIT_SECONDS)
        raise RenderInfrastructureError(
            f"failed to capture layout after {_CAPTURE_RETRIES} attempts: "
            f"{last_error}; path={local_path}"
        )

    def _hdc(
        self,
        sn: str,
        args: Sequence[str],
        *,
        timeout: float | None = None,
        check: bool = True,
        log_path: Path,
    ) -> subprocess.CompletedProcess[str]:
        result = self._run(
            [str(self.config.hdc), "-t", sn, *args],
            timeout=timeout or min(self.config.timeout_seconds, 30.0),
            check=False,
        )
        self._log_result(log_path, result)
        if check and _hdc_failed(result):
            raise RenderInfrastructureError(_format_failure(result))
        return result

    @staticmethod
    def _run(
        command: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float = 30.0,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        try:
            completed = subprocess.run(
                list(command),
                cwd=str(cwd) if cwd is not None else None,
                env=dict(env) if env is not None else None,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RenderInfrastructureError(
                f"command failed to start or timed out: {' '.join(command)}: {exc}"
            ) from exc
        if check and completed.returncode != 0:
            raise RenderInfrastructureError(_format_failure(completed))
        return completed

    @staticmethod
    def _append_log(path: Path, text: str) -> None:
        with path.open("a", encoding="utf-8") as stream:
            stream.write(text)

    def _log_result(
        self, path: Path, result: subprocess.CompletedProcess[str]
    ) -> None:
        self._append_log(
            path,
            "$ "
            + " ".join(str(part) for part in result.args)
            + f"\nexit={result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}\n",
        )


def parse_hdc_targets(stdout: str, stderr: str = "") -> list[str]:
    """Parse both common HDC target formats and either output stream."""
    targets: list[str] = []
    fallback: list[str] = []
    for output in (stdout, stderr):
        for raw_line in output.splitlines():
            line = raw_line.strip()
            lower = line.lower()
            if not line or "empty" in lower or "list of" in lower or line.startswith("["):
                continue
            fields = line.split()
            # UART ``Ready`` only means that the serial port can be attempted.
            # It is not addressable with ``hdc -t`` until ``tconn`` succeeds.
            if len(fields) >= 3 and fields[2].lower() == "connected":
                if fields[0] not in targets:
                    targets.append(fields[0])
            elif len(fields) == 1 and fields[0] not in fallback:
                fallback.append(fields[0])
    return targets or fallback


def parse_a2ui_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("a2ui must not be empty")
        try:
            decoded = json.loads(text)
        except json.JSONDecodeError:
            decoded = []
            for line_number, line in enumerate(text.splitlines(), start=1):
                if not line.strip():
                    continue
                try:
                    decoded.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"a2ui JSONL line {line_number} is invalid: {exc}"
                    ) from exc
    else:
        decoded = value
    if not isinstance(decoded, list) or not decoded:
        raise ValueError("a2ui must be a non-empty JSON array or JSONL string")
    records: list[dict[str, Any]] = []
    for index, record in enumerate(decoded):
        if not isinstance(record, dict):
            raise ValueError(f"a2ui[{index}] must be an object")
        if "__viewport__" in record:
            continue
        copied = dict(record)
        create_surface = copied.get("createSurface")
        if isinstance(create_surface, dict) and create_surface.get("catalogId") == _EXTENDED_CATALOG:
            copied["createSurface"] = {
                **create_surface,
                "catalogId": _FORM_CATALOG,
            }
        records.append(copied)
    if not records:
        raise ValueError("a2ui contains no renderable records")
    return records


def _safe_id(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("id must be a non-empty string")
    cleaned = _SAFE_ID_RE.sub("-", value).strip("-.")
    if not cleaned:
        raise ValueError("id contains no safe characters")
    return cleaned[:120]


def _atomic_write_json(path: Path, value: Any) -> None:
    data = (
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    ).encode("utf-8")
    _atomic_write_bytes(path, data)


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", delete=False, dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        ) as stream:
            stream.write(data)
            temporary = Path(stream.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def _load_layout(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RenderInfrastructureError(f"dumpLayout is invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise RenderInfrastructureError("dumpLayout JSON root must be an object")
    return value


def _contains_bundle(value: Any, bundle: str) -> bool:
    if isinstance(value, dict):
        if value.get("bundleName") == bundle:
            return True
        return any(_contains_bundle(child, bundle) for child in value.values())
    if isinstance(value, list):
        return any(_contains_bundle(child, bundle) for child in value)
    return False


def _validate_install(result: subprocess.CompletedProcess[str]) -> None:
    output = "\n".join((result.stdout or "", result.stderr or "")).lower()
    markers = (
        "failed",
        "failure",
        "error",
        "exception",
        "verify signature",
        "signature verification",
        "install parse profile prop check error",
    )
    if result.returncode != 0 or any(marker in output for marker in markers):
        raise RenderInfrastructureError(_format_failure(result))


def _hdc_failed(result: subprocess.CompletedProcess[str]) -> bool:
    """Handle HDC versions that print ``[Fail]`` but still exit with code 0."""
    output = "\n".join(
        (getattr(result, "stdout", "") or "", getattr(result, "stderr", "") or "")
    ).lower()
    return result.returncode != 0 or "[fail]" in output


def _format_failure(result: subprocess.CompletedProcess[str]) -> str:
    command = " ".join(str(part) for part in result.args)
    return (
        f"command failed ({result.returncode}): {command}\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
