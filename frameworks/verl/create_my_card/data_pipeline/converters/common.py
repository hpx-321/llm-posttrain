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
