"""Loopback HTTP server for device-backed A2UI rendering."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .config import RenderServiceConfig, RenderServiceConfigError
from .runner import DeviceRenderer, RenderBusyError, RenderInfrastructureError


MAX_REQUEST_BYTES = 2 * 1024 * 1024


class RenderHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], renderer: DeviceRenderer):
        super().__init__(address, RenderRequestHandler)
        self.renderer = renderer


class RenderRequestHandler(BaseHTTPRequestHandler):
    server: RenderHTTPServer

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        if self.path != "/health":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            payload = self.server.renderer.health()
        except (RenderServiceConfigError, RenderInfrastructureError) as exc:
            self._json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"status": "unavailable", "error": str(exc)},
            )
            return
        self._json(HTTPStatus.OK, payload)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        if self.path != "/v1/render":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            payload = self._read_json()
            result = self.server.renderer.render(
                payload.get("id"), payload.get("size"), payload.get("a2ui")
            )
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"status": "failed", "error": str(exc)})
            return
        except RenderBusyError as exc:
            self._json(HTTPStatus.CONFLICT, {"status": "busy", "error": str(exc)})
            return
        except (RenderServiceConfigError, RenderInfrastructureError) as exc:
            self._json(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"status": "failed", "error": str(exc)},
            )
            return
        except Exception as exc:  # keep device/build internals out of HTTP tracebacks
            self._json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"status": "failed", "error": f"{type(exc).__name__}: {exc}"},
            )
            return
        self._json(
            HTTPStatus.OK,
            {
                "id": result.sample_id,
                "status": "succeeded",
                "bundle": self.server.renderer.config.bundle,
                "deviceSn": result.device_sn,
                "layout": result.layout,
                "screenshotBase64": base64.b64encode(
                    result.screenshot_path.read_bytes()
                ).decode("ascii"),
                "elapsedMs": result.elapsed_ms,
            },
        )

    def _read_json(self) -> dict[str, Any]:
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length is required")
        try:
            length = int(raw_length)
        except ValueError as exc:
            raise ValueError("Content-Length must be an integer") from exc
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise ValueError(f"request body must be between 1 and {MAX_REQUEST_BYTES} bytes")
        raw = self.rfile.read(length)
        decoded = json.loads(raw.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise ValueError("request JSON root must be an object")
        return decoded

    def _json(
        self,
        status: HTTPStatus,
        payload: dict[str, Any],
    ) -> None:
        body = json.dumps(
            payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(f"{self.address_string()} - {format % args}", file=sys.stderr)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate configuration and HDC device readiness, then exit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        config = RenderServiceConfig.from_env()
        renderer = DeviceRenderer(config)
        if args.check:
            print(json.dumps(renderer.health(), ensure_ascii=False, allow_nan=False))
            return 0
    except (RenderServiceConfigError, RenderInfrastructureError) as exc:
        print(f"render service configuration error: {exc}", file=sys.stderr)
        return 2
    server = RenderHTTPServer((config.bind, config.port), renderer)
    print(
        f"A2UI render service listening on http://{config.bind}:{config.port}; "
        f"bundle={config.bundle}",
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("stopping render service", flush=True)
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
