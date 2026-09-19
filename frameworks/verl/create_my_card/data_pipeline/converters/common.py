from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_MESSAGE_KINDS = ("createSurface", "updateComponents", "updateDataModel")


class A2uiReverseConversionError(ValueError):
    """Raised when final A2UI is invalid or outside the reversible subset."""


@dataclass(frozen=True)
class ParsedA2ui:
    """Validated three-message A2UI document."""

    version: str
    surface_id: str
    create_surface: dict[str, Any]
    update_components: dict[str, Any]
    update_data_model: dict[str, Any]
    components_by_id: dict[str, dict[str, Any]]
    component_order: tuple[str, ...]


def _names(values: set[str] | Sequence[str]) -> str:
    return ", ".join(sorted(str(value) for value in values)) or "none"


def _read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.read()
    return Path(path).read_text(encoding="utf-8")

def _read_json_object(path: str | None, label: str) -> dict[str, Any] | None:
    if path is None:
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise A2uiReverseConversionError(f"{label} must contain a JSON object.")
    return value

def _read_json_array(path: str | None, label: str) -> list[dict[str, Any]] | None:
    if path is None:
        return None
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise A2uiReverseConversionError(f"{label} must contain a JSON array.")
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise A2uiReverseConversionError(f"{label}[{idx}] must be a JSON object.")
    return raw
