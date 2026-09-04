"""Environment-backed configuration for the Windows rendering host."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path


EXPECTED_BUNDLE = "com.example.myapplication"
EXPECTED_ABILITY = "EntryAbility"
EXPECTED_MODULE = "entry"


class RenderServiceConfigError(RuntimeError):
    """The rendering host is not configured safely or completely."""


def _required_path(name: str) -> Path:
    value = os.environ.get(name)
    if not value:
        raise RenderServiceConfigError(f"{name} is required")
    return Path(value).expanduser()


def _positive_float(name: str, default: str) -> float:
    raw = os.environ.get(name, default)
    try:
        value = float(raw)
    except ValueError as exc:
        raise RenderServiceConfigError(f"{name} must be a number, got {raw!r}") from exc
    if value <= 0:
        raise RenderServiceConfigError(f"{name} must be positive")
    return value


def _port(name: str, default: str) -> int:
    raw = os.environ.get(name, default)
    try:
        value = int(raw)
    except ValueError as exc:
        raise RenderServiceConfigError(f"{name} must be an integer, got {raw!r}") from exc
    if not 1 <= value <= 65535:
        raise RenderServiceConfigError(f"{name} must be between 1 and 65535")
    return value


@dataclass(frozen=True)
class RenderServiceConfig:
    project_root: Path
    hdc: Path
    hvigor: Path
    node: Path
    deveco_home: Path
    artifact_root: Path
    bind: str = "127.0.0.1"
    port: int = 8000
    device_sn: str | None = None
    timeout_seconds: float = 300.0
    start_wait_seconds: float = 8.0
    screenshot_min_bytes: int = 1000
    bundle: str = EXPECTED_BUNDLE
    ability: str = EXPECTED_ABILITY
    module: str = EXPECTED_MODULE

    @classmethod
    def from_env(cls) -> "RenderServiceConfig":
        bind = os.environ.get("A2UI_RENDER_BIND", "127.0.0.1")
        if bind not in {"127.0.0.1", "::1", "localhost"}:
            raise RenderServiceConfigError(
                "A2UI_RENDER_BIND must be loopback-only; use an SSH reverse tunnel"
            )
        raw_sn = os.environ.get("A2UI_RENDER_DEVICE_SN", "").strip()
        return cls(
            project_root=_required_path("A2UI_RENDER_PROJECT_ROOT"),
            hdc=_required_path("A2UI_RENDER_HDC"),
            hvigor=_required_path("A2UI_RENDER_HVIGOR"),
            node=_required_path("A2UI_RENDER_NODE"),
            deveco_home=_required_path("A2UI_RENDER_DEVECO_HOME"),
            artifact_root=_required_path("A2UI_RENDER_ARTIFACT_ROOT"),
            bind=bind,
            port=_port("A2UI_RENDER_PORT", "8000"),
            device_sn=raw_sn or None,
            timeout_seconds=_positive_float("A2UI_RENDER_TIMEOUT_SECONDS", "300"),
            start_wait_seconds=_positive_float(
                "A2UI_RENDER_START_WAIT_SECONDS", "8"
            ),
        )

    @property
    def app_json(self) -> Path:
        return self.project_root / "AppScope" / "app.json5"

    @property
    def rawfile_target(self) -> Path:
        return (
            self.project_root
            / "entry"
            / "src"
            / "main"
            / "resources"
            / "rawfile"
            / "test.json"
        )

    @property
    def hap_output_dir(self) -> Path:
        return self.project_root / "entry" / "build" / "default" / "outputs" / "default"

    @property
    def sdk_home(self) -> Path:
        return self.deveco_home / "sdk"

    @property
    def java_home(self) -> Path:
        return self.deveco_home / "jbr"

    def validate(self, *, require_dependencies: bool = True) -> None:
        problems: list[str] = []
        required_dirs = {
            "A2UI_RENDER_PROJECT_ROOT": self.project_root,
            "A2UI_RENDER_DEVECO_HOME": self.deveco_home,
            "DevEco SDK": self.sdk_home,
            "DevEco JBR": self.java_home,
        }
        for label, path in required_dirs.items():
            if not path.is_dir():
                problems.append(f"{label} directory does not exist: {path}")
        required_files = {
            "A2UI_RENDER_HDC": self.hdc,
            "A2UI_RENDER_HVIGOR": self.hvigor,
            "A2UI_RENDER_NODE": self.node,
            "AppScope/app.json5": self.app_json,
            "rawfile test.json": self.rawfile_target,
            "DevEco Java": self.java_home / "bin" / "java.exe",
        }
        for label, path in required_files.items():
            if not path.is_file():
                problems.append(f"{label} file does not exist: {path}")
        if require_dependencies and not (self.project_root / "oh_modules").is_dir():
            problems.append(
                f"HarmonyOS dependencies are missing: {self.project_root / 'oh_modules'}; "
                "open/sync the project in DevEco Studio or run ohpm install first"
            )
        if self.app_json.is_file():
            content = self.app_json.read_text(encoding="utf-8-sig")
            bundle_match = re.search(
                r'["\']bundleName["\']\s*:\s*["\']([^"\']+)["\']',
                content,
            )
            if bundle_match is None or bundle_match.group(1) != self.bundle:
                problems.append(
                    f"render project bundle must be {self.bundle}: {self.app_json}"
                )
        if problems:
            raise RenderServiceConfigError("render host preflight failed:\n- " + "\n- ".join(problems))
        self.artifact_root.mkdir(parents=True, exist_ok=True)
