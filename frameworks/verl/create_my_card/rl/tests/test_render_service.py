from __future__ import annotations

import json
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from frameworks.verl.create_my_card.render_service.client import (
    RenderServiceClient,
)
from frameworks.verl.create_my_card.render_service.config import (
    EXPECTED_BUNDLE,
    RenderServiceConfig,
    RenderServiceConfigError,
)
from frameworks.verl.create_my_card.render_service.runner import (
    DeviceRenderer,
    RenderInfrastructureError,
    RenderResult,
    parse_a2ui_records,
    parse_hdc_targets,
)
from frameworks.verl.create_my_card.render_service.server import RenderHTTPServer
from frameworks.verl.create_my_card.rl.evaluation.render_l2_sample import (
    execute_render_service,
)


def test_parse_a2ui_records_accepts_payload_and_normalizes_catalog() -> None:
    records = parse_a2ui_records(
        [
            {"__viewport__": "2x2"},
            {
                "createSurface": {
                    "surfaceId": "card",
                    "catalogId": "ohos.a2ui.extended.catalog",
                }
            },
            {"updateDataModel": {"surfaceId": "card", "path": "/", "value": {}}},
        ]
    )

    assert len(records) == 2
    assert (
        records[0]["createSurface"]["catalogId"]
        == "ohos.a2ui.extended.catalog.form"
    )


def test_parse_hdc_targets_rejects_unconnected_uart_ready_state() -> None:
    assert parse_hdc_targets(
        "",
        "COM1            UART    Ready   unknown...      hdc\n",
    ) == []


def test_parse_hdc_targets_accepts_connected_tcp_and_ignores_offline_uart() -> None:
    assert parse_hdc_targets(
        "127.0.0.1:5555 TCP Connected localhost hdc\n"
        "COM1 UART Offline unknown... hdc\n"
    ) == ["127.0.0.1:5555"]


def test_parse_hdc_targets_accepts_compact_output() -> None:
    assert parse_hdc_targets("device-serial\n") == ["device-serial"]


def test_capture_screenshot_retries_small_uart_transfer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    renderer = object.__new__(DeviceRenderer)
    renderer.config = SimpleNamespace(screenshot_min_bytes=1000)
    local_path = tmp_path / "screenshot.jpeg"
    log_path = tmp_path / "render.log"
    receives = 0

    def fake_hdc(sn, args, **kwargs):
        nonlocal receives
        if args[:2] == ["file", "recv"]:
            receives += 1
            local_path.write_bytes(b"x" * (10 if receives == 1 else 1001))
        return SimpleNamespace(returncode=0)

    renderer._hdc = fake_hdc
    monkeypatch.setattr(
        "frameworks.verl.create_my_card.render_service.runner.time.sleep",
        lambda _seconds: None,
    )

    renderer._capture_screenshot(
        "COM1", "/data/local/tmp/screenshot.jpeg", local_path, log_path
    )

    assert receives == 2
    assert local_path.stat().st_size == 1001


def test_hdc_rejects_fail_marker_even_when_exit_code_is_zero(tmp_path: Path) -> None:
    renderer = object.__new__(DeviceRenderer)
    renderer.config = SimpleNamespace(hdc=Path("hdc.exe"), timeout_seconds=30)
    renderer._run = lambda command, **_kwargs: SimpleNamespace(
        args=command,
        returncode=0,
        stdout="[Fail][E001005] Device not found or connected\n",
        stderr="",
    )

    with pytest.raises(RenderInfrastructureError, match="Device not found"):
        renderer._hdc(
            "COM1",
            ["shell", "echo", "connected"],
            log_path=tmp_path / "render.log",
        )


def test_config_requires_synced_dependencies(tmp_path: Path) -> None:
    project = tmp_path / "A2UI_Render_0716"
    (project / "AppScope").mkdir(parents=True)
    (project / "AppScope" / "app.json5").write_text(
        '{"app":{"bundleName":"com.example.myapplication"}}', encoding="utf-8"
    )
    rawfile = project / "entry/src/main/resources/rawfile/test.json"
    rawfile.parent.mkdir(parents=True)
    rawfile.write_text("[]\n", encoding="utf-8")
    deveco = tmp_path / "DevEco Studio"
    (deveco / "sdk").mkdir(parents=True)
    (deveco / "jbr/bin").mkdir(parents=True)
    (deveco / "jbr/bin/java.exe").write_bytes(b"stub")
    hdc = tmp_path / "hdc.exe"
    hvigor = tmp_path / "hvigorw.js"
    node = tmp_path / "node.exe"
    for executable in (hdc, hvigor, node):
        executable.write_bytes(b"stub")
    config = RenderServiceConfig(
        project_root=project,
        hdc=hdc,
        hvigor=hvigor,
        node=node,
        deveco_home=deveco,
        artifact_root=tmp_path / "artifacts",
    )

    with pytest.raises(RenderServiceConfigError, match="oh_modules"):
        config.validate()

    (project / "oh_modules").mkdir()
    config.validate()
    assert config.artifact_root.is_dir()


class _FakeRenderer:
    def __init__(self, screenshot: Path):
        self.config = SimpleNamespace(bundle=EXPECTED_BUNDLE)
        self.screenshot = screenshot

    def health(self):
        return {
            "status": "ok",
            "bundle": EXPECTED_BUNDLE,
            "deviceReady": True,
            "deviceSn": "device-1",
            "targets": ["device-1"],
            "busy": False,
        }

    def render(self, sample_id, size, a2ui):
        assert size == "2x2"
        assert isinstance(a2ui, list)
        return RenderResult(
            sample_id=sample_id,
            layout={"attributes": {"bundleName": EXPECTED_BUNDLE}},
            screenshot_path=self.screenshot,
            layout_path=self.screenshot.with_suffix(".json"),
            log_path=self.screenshot.with_suffix(".log"),
            elapsed_ms=12.5,
            device_sn="device-1",
        )


def test_http_server_and_client_roundtrip(tmp_path: Path) -> None:
    screenshot = tmp_path / "screenshot.jpeg"
    screenshot.write_bytes(b"jpeg-data")
    server = RenderHTTPServer(("127.0.0.1", 0), _FakeRenderer(screenshot))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{server.server_port}"
    try:
        client = RenderServiceClient(base_url, 5)
        assert client.health()["deviceReady"] is True
        result = client.render(
            sample_id="case-1",
            size="2x2",
            a2ui=[{"createSurface": {"surfaceId": "card"}}],
        )
        assert result["status"] == "succeeded"
        assert result["bundle"] == EXPECTED_BUNDLE

    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_l2_http_execution_saves_layout_screenshot_and_manifest(tmp_path: Path) -> None:
    screenshot = tmp_path / "service-screenshot.jpeg"
    screenshot.write_bytes(b"jpeg-data")
    server = RenderHTTPServer(("127.0.0.1", 0), _FakeRenderer(screenshot))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    payload_path = output_dir / "case-1.render.json"
    payload_path.write_text(
        json.dumps([{"createSurface": {"surfaceId": "card"}}]),
        encoding="utf-8",
    )
    manifest = output_dir / "render-sample-manifest.json"
    try:
        exit_code = execute_render_service(
            [
                {
                    "id": "case-1",
                    "group_id": "case-1",
                    "size": "2x2",
                    "render_payload": str(payload_path),
                }
            ],
            service_url=f"http://127.0.0.1:{server.server_port}",
            timeout_seconds=5,
            output_dir=output_dir,
            manifest=manifest,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert exit_code == 0
    assert (output_dir / "layouts/case-1.layout.json").is_file()
    assert (output_dir / "screenshots/case-1.jpeg").read_bytes() == b"jpeg-data"
    assert json.loads(manifest.read_text(encoding="utf-8"))["status"] == "succeeded"


def test_render_project_bundle_matches_checker() -> None:
    project_root = Path(__file__).resolve().parents[5] / "A2UI_Render_0716"
    app_json = (project_root / "AppScope" / "app.json5").read_text(encoding="utf-8")
    assert f'"bundleName": "{EXPECTED_BUNDLE}"' in app_json
