#!/usr/bin/env python3
"""Prepare and optionally execute a device-backed L2 render/dump sample."""

from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT))

from frameworks.verl.create_my_card.data_pipeline.converters import (  # noqa: E402
    convert_compact_dsl_to_a2ui,
)
from frameworks.verl.create_my_card.rl.evaluation.audit_rewards import (  # noqa: E402
    _embedded_mapping,
    _group_id,
    _sample_id,
    _solution,
    load_keyed_records,
    read_jsonl,
)
from frameworks.verl.create_my_card.rl.reward import default_checker_root  # noqa: E402
from frameworks.verl.create_my_card.render_service import (  # noqa: E402
    RenderServiceClient,
    RenderServiceClientError,
)
from frameworks.verl.create_my_card.render_service.config import (  # noqa: E402
    EXPECTED_BUNDLE,
)


_SAFE_SAMPLE_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Raw rollout JSONL.")
    parser.add_argument("--taskspec-file", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument(
        "--ids",
        help="Optional comma-separated sample ids; preserves the input order.",
    )
    parser.add_argument(
        "--checker-root",
        type=Path,
        default=default_checker_root(),
        help=(
            "Path to design-check. Defaults to the vendored 0.2.0 package; "
            "DESIGN_CHECK_ROOT may override it."
        ),
    )
    parser.add_argument("--automation-root", type=Path)
    parser.add_argument("--device-sn")
    parser.add_argument(
        "--render-service-url",
        default=os.environ.get("A2UI_RENDER_SERVICE_URL"),
        help=(
            "Optional HTTP render service URL. With --execute, use the service "
            "instead of the legacy local Automation-screenshot subprocess. "
            "Defaults to A2UI_RENDER_SERVICE_URL."
        ),
    )
    parser.add_argument(
        "--render-service-timeout",
        type=float,
        default=float(os.environ.get("A2UI_RENDER_REQUEST_TIMEOUT_SECONDS", "320")),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Call the checker package's device render_eval_dump.py after preparation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("error: --limit must be positive")
    if args.output_dir.exists():
        raise SystemExit(f"error: output directory already exists: {args.output_dir}")
    selected_ids = None
    if args.ids:
        selected_ids = {value.strip() for value in args.ids.split(",") if value.strip()}
        if not selected_ids:
            raise SystemExit("error: --ids contains no ids")
    task_specs = load_keyed_records(
        args.taskspec_file,
        payload_keys=("taskSpec", "task_spec"),
    )

    prepared: list[dict[str, Any]] = []
    args.output_dir.mkdir(parents=True)
    for index, row in enumerate(read_jsonl(args.input), start=1):
        sample_id = _sample_id(row, index)
        if not _SAFE_SAMPLE_ID_RE.fullmatch(sample_id):
            raise ValueError(
                f"row {index}: sample id may contain only letters, digits, '.', '_' and '-': "
                f"{sample_id!r}"
            )
        if selected_ids is not None and sample_id not in selected_ids:
            continue
        group_id = _group_id(row, index, fallback=sample_id)
        task_spec = (
            _embedded_mapping(row, ("taskSpec", "task_spec"))
            or task_specs.get(group_id)
        )
        if task_spec is None:
            raise ValueError(
                f"row {index} ({sample_id}, group {group_id}): "
                "no TaskSpec was provided"
            )
        size = task_spec.get("size")
        if size not in {"2x2", "2x4"}:
            raise ValueError(f"row {index} ({sample_id}): unsupported size {size!r}")
        converted = convert_compact_dsl_to_a2ui(
            _solution(row, index),
            size=size,
            protocol_profile={"version": "v0.9"},
        )
        output_file = args.output_dir / f"{sample_id}.render.json"
        write_render_payload(converted, size=size, output=output_file)
        prepared.append(
            {
                "id": sample_id,
                "group_id": group_id,
                "size": size,
                "render_payload": str(output_file.resolve()),
            }
        )
        if len(prepared) >= args.limit:
            break
    if not prepared:
        raise ValueError("no render samples were selected")
    if selected_ids is not None:
        missing = sorted(selected_ids - {row["id"] for row in prepared})
        if missing:
            raise ValueError(f"selected ids were not found before the limit: {missing}")

    manifest = args.output_dir / "render-sample-manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "status": "prepared_not_rendered",
                "requires_device": True,
                "items": prepared,
            },
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if not args.execute:
        print(
            json.dumps(
                {
                    "prepared": len(prepared),
                    "executed": False,
                    "manifest": str(manifest.resolve()),
                },
                ensure_ascii=False,
            )
        )
        return 0
    if args.render_service_url:
        if args.render_service_timeout <= 0:
            raise SystemExit("error: --render-service-timeout must be positive")
        return execute_render_service(
            prepared,
            service_url=args.render_service_url,
            timeout_seconds=args.render_service_timeout,
            output_dir=args.output_dir,
            manifest=manifest,
        )
    return execute_render(
        prepared,
        checker_root=args.checker_root.resolve(),
        automation_root=args.automation_root,
        device_sn=args.device_sn,
    )


def write_render_payload(a2ui: str, *, size: str, output: Path) -> None:
    messages = [
        json.loads(raw_line)
        for raw_line in a2ui.splitlines()
        if raw_line.strip()
    ]
    output.write_text(
        json.dumps(
            [{"__viewport__": size}, *messages],
            ensure_ascii=False,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def execute_render(
    items: list[Mapping[str, Any]],
    *,
    checker_root: Path,
    automation_root: Path | None,
    device_sn: str | None,
) -> int:
    script = checker_root / "scripts" / "render_eval_dump.py"
    if not script.is_file():
        raise FileNotFoundError(script)
    chunks: list[str] = []
    for item in items:
        sample_id = str(item["id"])
        payload = str(item["render_payload"])
        if any(character in sample_id + payload for character in (",", "=")):
            raise ValueError("render item ids/paths cannot contain ',' or '='")
        chunks.append(f"{sample_id}={payload}")
    command = [sys.executable, str(script), "--items", ",".join(chunks)]
    if automation_root is not None:
        command.extend(["--automation-root", str(automation_root.resolve())])
    if device_sn:
        command.extend(["--sn", device_sn])
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    environment["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        command,
        cwd=checker_root,
        env=environment,
        check=False,
    )
    return completed.returncode


def execute_render_service(
    items: list[Mapping[str, Any]],
    *,
    service_url: str,
    timeout_seconds: float,
    output_dir: Path,
    manifest: Path,
) -> int:
    client = RenderServiceClient(service_url, timeout_seconds)
    try:
        health = client.health()
    except RenderServiceClientError as exc:
        _write_service_manifest(
            manifest,
            status="service_unavailable",
            items=[dict(item) for item in items],
            error=str(exc),
        )
        print(f"render service health check failed: {exc}", file=sys.stderr)
        return 2
    if (
        health.get("status") != "ok"
        or health.get("deviceReady") is not True
        or health.get("bundle") != EXPECTED_BUNDLE
    ):
        error = f"render service is not ready or has the wrong bundle: {health}"
        _write_service_manifest(
            manifest,
            status="service_unavailable",
            items=[dict(item) for item in items],
            error=error,
        )
        print(error, file=sys.stderr)
        return 2

    layout_dir = output_dir / "layouts"
    screenshot_dir = output_dir / "screenshots"
    layout_dir.mkdir()
    screenshot_dir.mkdir()
    results: list[dict[str, Any]] = []
    failures = 0
    for item in items:
        sample_id = str(item["id"])
        result = dict(item)
        try:
            payload = json.loads(
                Path(str(item["render_payload"])).read_text(encoding="utf-8")
            )
            if not isinstance(payload, list):
                raise ValueError("prepared render payload must be a JSON array")
            response = client.render(
                sample_id=sample_id,
                size=str(item["size"]),
                a2ui=payload,
            )
            if response.get("status") != "succeeded":
                raise RenderServiceClientError(
                    f"render service did not report success: {response}"
                )
            if response.get("bundle") != EXPECTED_BUNDLE:
                raise RenderServiceClientError(
                    f"render service returned bundle {response.get('bundle')!r}, "
                    f"expected {EXPECTED_BUNDLE!r}"
                )
            layout = response.get("layout")
            screenshot_base64 = response.get("screenshotBase64")
            if not isinstance(layout, dict):
                raise RenderServiceClientError("render response has no layout object")
            if not isinstance(screenshot_base64, str):
                raise RenderServiceClientError("render response has no screenshotBase64")
            try:
                screenshot = base64.b64decode(screenshot_base64, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise RenderServiceClientError(
                    "render response screenshotBase64 is invalid"
                ) from exc
            layout_path = layout_dir / f"{sample_id}.layout.json"
            screenshot_path = screenshot_dir / f"{sample_id}.jpeg"
            layout_path.write_text(
                json.dumps(layout, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )
            screenshot_path.write_bytes(screenshot)
            result.update(
                {
                    "status": "succeeded",
                    "rendered": True,
                    "dumped": True,
                    "layout_path": str(layout_path.resolve()),
                    "screenshot": str(screenshot_path.resolve()),
                    "elapsed_ms": response.get("elapsedMs"),
                    "device_sn": response.get("deviceSn"),
                }
            )
        except (OSError, ValueError, json.JSONDecodeError, RenderServiceClientError) as exc:
            failures += 1
            result.update(
                {
                    "status": "failed",
                    "rendered": False,
                    "dumped": False,
                    "error": str(exc),
                }
            )
            print(f"render service failed for {sample_id}: {exc}", file=sys.stderr)
        results.append(result)

    _write_service_manifest(
        manifest,
        status="succeeded" if failures == 0 else "partial_failure",
        items=results,
    )
    print(
        json.dumps(
            {
                "rendered": len(results) - failures,
                "failed": failures,
                "layout_dir": str(layout_dir.resolve()),
                "manifest": str(manifest.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0 if failures == 0 else 1


def _write_service_manifest(
    path: Path,
    *,
    status: str,
    items: list[dict[str, Any]],
    error: str | None = None,
) -> None:
    payload: dict[str, Any] = {
        "status": status,
        "requires_device": True,
        "transport": "http",
        "items": items,
    }
    if error:
        payload["error"] = error
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    raise SystemExit(main())
