"""Standard-library HTTP client for the local rendering service."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class RenderServiceClientError(RuntimeError):
    """The remote rendering service failed or returned an invalid response."""


Opener = Callable[..., Any]


@dataclass(frozen=True)
class RenderServiceClient:
    base_url: str
    timeout_seconds: float = 320.0
    opener: Opener = urlopen

    def __post_init__(self) -> None:
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("render service URL must use http:// or https://")
        if self.timeout_seconds <= 0:
            raise ValueError("render service timeout must be positive")

    def health(self) -> Mapping[str, Any]:
        return self._request("GET", "/health")

    def render(
        self,
        *,
        sample_id: str,
        size: str,
        a2ui: list[dict[str, Any]] | str,
    ) -> Mapping[str, Any]:
        return self._request(
            "POST",
            "/v1/render",
            {"id": sample_id, "size": size, "a2ui": a2ui},
        )

    def _request(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(
                payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(
            self.base_url.rstrip("/") + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RenderServiceClientError(
                f"render service HTTP {exc.code}: {detail}"
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise RenderServiceClientError(f"render service request failed: {exc}") from exc
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RenderServiceClientError(
                "render service returned invalid JSON"
            ) from exc
        if not isinstance(decoded, dict):
            raise RenderServiceClientError("render service JSON root must be an object")
        return decoded
