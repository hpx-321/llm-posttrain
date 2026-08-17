#!/usr/bin/env python3
"""Convert raw CreateMyCard request files into TaskSpec evaluation cases."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


SFT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA_CATALOG = SFT_DIR / "data" / "source" / "taskspec.json"
DEFAULT_OUTPUT_FILE = SFT_DIR / "data" / "source" / "taskspec_cases.json"
TASKSPEC_FIELDS = (
    "userQuery",
    "size",
    "dataModelSchema",
    "eventCandidates",
    "assetCandidates",
)
RAW_CONTENT_FIELDS = frozenset(
    {
        "bundleName",
        "userQuery",
        "candidateDataBindings",
        "title",
        "size",
        "candidateEventCandidates",
        "description",
        "candidateAssetIds",
    }
)
RAW_FILE_PATTERN = re.compile(r"^Q(?P<number>[0-9]+)\.json$", re.IGNORECASE)


_FALLBACK_FIELD_METADATA_BY_PATH: dict[str, dict[str, Any]] = {
    "/data/appUsageStats/updatedAt": {
        "type": "string",
        "description": "应用使用时长数据的更新时间",
        "sampleValue": "2026-08-13 10:00",
    },
    "/data/calendar/events/0/description": {
        "type": "string",
        "description": "日程的补充说明",
        "sampleValue": "讨论项目进展与后续安排",
    },
    "/data/calendar/events/0/entityName": {
        "type": "string",
        "description": "日程关联的业务实体名称",
        "sampleValue": "项目周会",
    },
    "/data/calendar/events/0/importantEventType": {
        "type": "string",
        "description": "重要日程的业务类型",
        "sampleValue": "会议",
    },
    "/data/calendar/events/0/isAllDay": {
        "type": "boolean",
        "description": "日程是否为全天事件",
        "sampleValue": False,
    },
    "/data/calendar/events/0/isServiceValid": {
        "type": "boolean",
        "description": "日程的一键服务当前是否有效",
        "sampleValue": True,
    },
    "/data/calendar/events/0/oneClickServiceLink": {
        "type": "string",
        "description": "日程关联的一键服务链接",
        "sampleValue": "huawei-calendar://event/demo",
    },
    "/data/calendar/events/0/oneClickServiceType": {
        "type": "string",
        "description": "日程关联的一键服务类型",
        "sampleValue": "meeting",
    },
    "/data/calendar/events/0/remindTime": {
        "type": "string",
        "description": "日程提醒时间的展示文本",
        "sampleValue": "提前15分钟",
    },
    "/data/calendar/events/0/senderName": {
        "type": "string",
        "description": "日程邀请人的名称",
        "sampleValue": "项目负责人",
    },
    "/data/healthSport/exerciseEndTimeText": {
        "type": "string",
        "description": "最近一次运动结束时间",
        "sampleValue": "19:05",
    },
    "/data/healthSport/exerciseHeartRateMax": {
        "type": "integer",
        "description": "最近一次运动的最高心率",
        "sampleValue": 168,
    },
    "/data/healthSport/exerciseHeartRateMin": {
        "type": "integer",
        "description": "最近一次运动的最低心率",
        "sampleValue": 96,
    },
    "/data/healthSport/exerciseStartTimeText": {
        "type": "string",
        "description": "最近一次运动开始时间",
        "sampleValue": "18:30",
    },
    "/data/healthSport/fallAsleepTimeText": {
        "type": "string",
        "description": "最近一次夜间入睡时间",
        "sampleValue": "23:18",
    },
    "/data/healthSport/sleepTypeDesc": {
        "type": "string",
        "description": "睡眠记录类型的展示文本",
        "sampleValue": "夜间睡眠",
    },
    "/data/healthSport/targetDateText": {
        "type": "string",
        "description": "健康运动数据对应日期的展示文本",
        "sampleValue": "今天",
    },
    "/data/healthSport/totalNapDurationText": {
        "type": "string",
        "description": "白天小睡总时长",
        "sampleValue": "30分钟",
    },
    "/data/healthSport/updatedAt": {
        "type": "string",
        "description": "健康运动数据的更新时间",
        "sampleValue": "刚刚更新",
    },
    "/data/healthSport/wakeupTimeText": {
        "type": "string",
        "description": "最近一次夜间睡眠醒来时间",
        "sampleValue": "06:36",
    },
    "/data/phoneBattery/isBatteryPresentText": {
        "type": "string",
        "description": "手机是否检测到电池的展示文本",
        "sampleValue": "电池正常",
    },
    "/data/weather/daily/0/coldLevel": {
        "type": "string",
        "description": "对应预报日的感冒指数",
        "sampleValue": "较易感冒",
    },
    "/data/weather/daily/0/date": {
        "type": "string",
        "description": "对应预报日的日期",
        "sampleValue": "2026-08-13",
    },
    "/data/weather/daily/0/uvIndex": {
        "type": "string",
        "description": "对应预报日的紫外线指数等级",
        "sampleValue": "中等",
    },
    "/data/weather/location/cityCode": {
        "type": "string",
        "description": "天气服务使用的城市编码",
        "sampleValue": "101020100",
    },
    "/data/weather/location/districtName": {
        "type": "string",
        "description": "区县名称",
        "sampleValue": "青浦区",
    },
}

FALLBACK_FIELD_METADATA = {
    tuple(path.lstrip("/").split("/")): metadata
    for path, metadata in _FALLBACK_FIELD_METADATA_BY_PATH.items()
}

FALLBACK_ASSET_PATHS = {
    "air_open_fill": "resources/base/media/air_open_fill.svg",
    "icon_car": "resources/base/media/icon_car.svg",
    "icon_focus": "resources/base/media/icon_focus.svg",
    "thermometer_snowflake": "resources/base/media/thermometer_snowflake.svg",
    "typhoon_fill": "resources/base/media/typhoon_fill.svg",
}

PREFERRED_FIELD_TYPES = {
    ("data", "weather", "current", "feelsLikeC"): "number",
    ("data", "weather", "current", "humidityPercent"): "integer",
}


class TaskSpecImportError(ValueError):
    """Raised when raw requests cannot be mapped without ambiguity."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument(
        "--schema-catalog",
        type=Path,
        default=DEFAULT_SCHEMA_CATALOG,
        help="Project TaskSpec source used to resolve field metadata and asset paths.",
    )
    parser.add_argument(
        "--reference-file",
        type=Path,
        help="Optional normalized taskspec_cases.json whose metadata takes precedence.",
    )
    parser.add_argument("--output-file", type=Path, default=DEFAULT_OUTPUT_FILE)
    return parser.parse_args()


def read_json(path: Path, label: str) -> Any:
    if not path.is_file():
        raise TaskSpecImportError(f"{label} does not exist: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TaskSpecImportError(f"{label} is not valid UTF-8 JSON: {path}") from exc


def normalized_tokens(tokens: Iterable[str]) -> tuple[str, ...]:
    return tuple("0" if token.isdigit() else token for token in tokens)


def pointer_tokens(pointer: Any, label: str) -> tuple[str, ...]:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise TaskSpecImportError(f"{label} must be an absolute JSON Pointer")
    tokens: list[str] = []
    for raw_token in pointer[1:].split("/"):
        if not raw_token:
            raise TaskSpecImportError(f"{label} contains an empty path segment")
        token = raw_token.replace("~1", "/").replace("~0", "~")
        tokens.append(token)
    return tuple(tokens)


def schema_leaves(
    node: Any,
    tokens: tuple[str, ...] = (),
) -> Iterable[tuple[tuple[str, ...], dict[str, Any]]]:
    if isinstance(node, dict) and "type" in node and "sampleValue" in node:
        yield normalized_tokens(tokens), node
        return
    if isinstance(node, dict):
        for key, value in node.items():
            yield from schema_leaves(value, (*tokens, key))
        return
    if isinstance(node, list) and node:
        yield from schema_leaves(node[0], (*tokens, "0"))


def catalog_task_specs(payload: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or not payload:
        raise TaskSpecImportError(f"{label} must be a non-empty JSON array")
    specs: list[dict[str, Any]] = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise TaskSpecImportError(f"{label} record {index} must be an object")
        task_spec = item.get("taskSpec", item)
        if not isinstance(task_spec, dict):
            raise TaskSpecImportError(f"{label} record {index} has no TaskSpec object")
        specs.append(task_spec)
    return specs


def add_catalog_entries(
    specs: Iterable[dict[str, Any]],
    field_counts: dict[tuple[str, ...], Counter[str]],
    asset_counts: dict[str, Counter[str]],
) -> None:
    for task_spec in specs:
        schema = task_spec.get("dataModelSchema", {})
        for path, leaf in schema_leaves(schema):
            encoded = json.dumps(leaf, ensure_ascii=False, sort_keys=True, allow_nan=False)
            field_counts.setdefault(path, Counter())[encoded] += 1
        assets = task_spec.get("assetCandidates", [])
        if not isinstance(assets, list):
            continue
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            src = asset.get("src")
            if isinstance(src, str) and src:
                asset_counts.setdefault(Path(src).stem, Counter())[src] += 1


def build_catalogs(
    schema_catalog: Path,
    reference_file: Path | None,
) -> tuple[
    dict[tuple[str, ...], Counter[str]],
    dict[tuple[str, ...], dict[str, Any]],
    dict[str, Counter[str]],
]:
    field_counts: dict[tuple[str, ...], Counter[str]] = {}
    asset_counts: dict[str, Counter[str]] = {}
    catalog = catalog_task_specs(read_json(schema_catalog, "schema catalog"), "schema catalog")
    add_catalog_entries(catalog, field_counts, asset_counts)

    preferred_fields: dict[tuple[str, ...], dict[str, Any]] = {}
    if reference_file is not None:
        reference = catalog_task_specs(
            read_json(reference_file, "reference file"),
            "reference file",
        )
        for task_spec in reference:
            for path, leaf in schema_leaves(task_spec.get("dataModelSchema", {})):
                preferred_fields.setdefault(path, copy.deepcopy(leaf))
        add_catalog_entries(reference, field_counts, asset_counts)
    return field_counts, preferred_fields, asset_counts


def choose_field_metadata(
    path: tuple[str, ...],
    field_counts: dict[tuple[str, ...], Counter[str]],
    preferred_fields: dict[tuple[str, ...], dict[str, Any]],
) -> dict[str, Any]:
    preferred = preferred_fields.get(path)
    if preferred is not None:
        return copy.deepcopy(preferred)

    candidates = field_counts.get(path)
    if candidates:
        preferred_type = PREFERRED_FIELD_TYPES.get(path)
        ranked = candidates.most_common()
        if preferred_type is not None:
            ranked = [
                item
                for item in ranked
                if json.loads(item[0]).get("type") == preferred_type
            ]
        if ranked:
            return json.loads(ranked[0][0])

    fallback = FALLBACK_FIELD_METADATA.get(path)
    if fallback is not None:
        return copy.deepcopy(fallback)
    pointer = "/" + "/".join(path)
    raise TaskSpecImportError(f"no schema metadata is available for {pointer}")


def specialize_sample_value(
    path: tuple[str, ...],
    metadata: dict[str, Any],
    binding: dict[str, Any],
    raw_payload: dict[str, Any],
) -> None:
    arguments = binding.get("arguments", {})
    if not isinstance(arguments, dict):
        return
    argument_by_path = {
        ("data", "weather", "location", "prefectureName"): "prefectureName",
        ("data", "weather", "location", "districtName"): "districtName",
    }
    argument_name = argument_by_path.get(path)
    if argument_name is not None:
        value = arguments.get(argument_name)
        if isinstance(value, str) and value:
            metadata["sampleValue"] = value

    if path != ("data", "countdown", "countdownDays"):
        return
    target_date = arguments.get("targetDate")
    raw_time = raw_payload.get("deviceInfo", {}).get("time")
    if not isinstance(target_date, str) or not isinstance(raw_time, str):
        return
    try:
        start = datetime.strptime(raw_time[:8], "%Y%m%d").date()
        target = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        return
    metadata["sampleValue"] = max(0, (target - start).days)


def set_schema_leaf(
    schema: dict[str, Any],
    path: tuple[str, ...],
    metadata: dict[str, Any],
) -> None:
    current: dict[str, Any] | list[Any] = schema
    for index, token in enumerate(path):
        is_last = index == len(path) - 1
        next_is_array = not is_last and path[index + 1] == "0"
        if token == "0":
            if not isinstance(current, list):
                raise TaskSpecImportError(f"schema path has an unexpected array segment: {path}")
            if not current:
                current.append({})
            if not isinstance(current[0], dict):
                raise TaskSpecImportError(f"schema path conflicts at array segment: {path}")
            current = current[0]
            continue
        if not isinstance(current, dict):
            raise TaskSpecImportError(f"schema path conflicts at object segment: {path}")
        if is_last:
            existing = current.get(token)
            if existing is not None and existing != metadata:
                raise TaskSpecImportError(f"schema leaf conflicts at {'/'.join(path)}")
            current[token] = copy.deepcopy(metadata)
            continue
        expected: dict[str, Any] | list[Any] = [] if next_is_array else {}
        child = current.setdefault(token, expected)
        if type(child) is not type(expected):
            raise TaskSpecImportError(f"schema container conflicts at {'/'.join(path)}")
        current = child


def choose_asset(
    asset_id: Any,
    asset_counts: dict[str, Counter[str]],
    label: str,
) -> dict[str, str]:
    if not isinstance(asset_id, str) or not asset_id.startswith("asset."):
        raise TaskSpecImportError(f"{label} must use an asset.<name> identifier")
    stem = asset_id.removeprefix("asset.")
    candidates = asset_counts.get(stem)
    if candidates:
        return {"src": candidates.most_common(1)[0][0]}
    fallback = FALLBACK_ASSET_PATHS.get(stem)
    if fallback is not None:
        return {"src": fallback}
    raise TaskSpecImportError(f"{label} has no project asset mapping: {asset_id}")


def load_raw_requests(input_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    if not input_dir.is_dir():
        raise TaskSpecImportError(f"input directory does not exist: {input_dir}")
    paths: list[tuple[int, Path]] = []
    for path in input_dir.iterdir():
        if not path.is_file() or path.suffix.lower() != ".json":
            continue
        match = RAW_FILE_PATTERN.fullmatch(path.name)
        if match is None:
            raise TaskSpecImportError(f"unexpected JSON filename in input directory: {path.name}")
        paths.append((int(match.group("number")), path))
    if not paths:
        raise TaskSpecImportError(f"input directory contains no Q*.json files: {input_dir}")
    paths.sort()
    numbers = [number for number, _ in paths]
    if len(numbers) != len(set(numbers)):
        raise TaskSpecImportError("input directory contains duplicate numeric Q identifiers")

    records: list[tuple[str, dict[str, Any]]] = []
    for number, path in paths:
        payload = read_json(path, f"raw request Q{number:03d}")
        if not isinstance(payload, dict):
            raise TaskSpecImportError(f"{path.name} must contain a JSON object")
        content = payload.get("content")
        if not isinstance(content, dict) or set(content) != RAW_CONTENT_FIELDS:
            raise TaskSpecImportError(
                f"{path.name}.content fields must be exactly {sorted(RAW_CONTENT_FIELDS)}"
            )
        for field in RAW_CONTENT_FIELDS:
            if payload.get(field) != content[field]:
                raise TaskSpecImportError(
                    f"{path.name}.{field} differs from {path.name}.content.{field}"
                )
        records.append((f"Q{number:03d}", payload))
    return records


def build_data_model_schema(
    case_id: str,
    payload: dict[str, Any],
    field_counts: dict[tuple[str, ...], Counter[str]],
    preferred_fields: dict[tuple[str, ...], dict[str, Any]],
) -> dict[str, Any]:
    schema: dict[str, Any] = {}
    bindings = payload["content"]["candidateDataBindings"]
    if not isinstance(bindings, list):
        raise TaskSpecImportError(f"{case_id}.candidateDataBindings must be an array")
    for binding_index, binding in enumerate(bindings, start=1):
        label = f"{case_id}.candidateDataBindings[{binding_index}]"
        if not isinstance(binding, dict):
            raise TaskSpecImportError(f"{label} must be an object")
        root = pointer_tokens(binding.get("writeResultTo"), f"{label}.writeResultTo")
        output_fields = binding.get("candidateOutputFields")
        if not isinstance(output_fields, list) or not output_fields:
            raise TaskSpecImportError(f"{label}.candidateOutputFields must be non-empty")
        for field_index, output_field in enumerate(output_fields, start=1):
            suffix = pointer_tokens(
                output_field,
                f"{label}.candidateOutputFields[{field_index}]",
            )
            path = normalized_tokens((*root, *suffix))
            metadata = choose_field_metadata(path, field_counts, preferred_fields)
            specialize_sample_value(path, metadata, binding, payload)
            set_schema_leaf(schema, path, metadata)
    return schema


def build_event_candidates(case_id: str, content: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = content["candidateEventCandidates"]
    if not isinstance(candidates, list):
        raise TaskSpecImportError(f"{case_id}.candidateEventCandidates must be an array")
    actions: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict) or not isinstance(candidate.get("action"), dict):
            raise TaskSpecImportError(
                f"{case_id}.candidateEventCandidates[{index}] must contain an action object"
            )
        action = copy.deepcopy(candidate["action"])
        if not isinstance(action.get("call"), str) or not action["call"]:
            raise TaskSpecImportError(
                f"{case_id}.candidateEventCandidates[{index}].action.call is invalid"
            )
        if not isinstance(action.get("args"), dict):
            raise TaskSpecImportError(
                f"{case_id}.candidateEventCandidates[{index}].action.args must be an object"
            )
        actions.append(action)
    return actions


def build_asset_candidates(
    case_id: str,
    content: dict[str, Any],
    asset_counts: dict[str, Counter[str]],
) -> list[dict[str, str]]:
    asset_ids = content["candidateAssetIds"]
    if not isinstance(asset_ids, list):
        raise TaskSpecImportError(f"{case_id}.candidateAssetIds must be an array")
    if len(asset_ids) != len(set(asset_ids)):
        raise TaskSpecImportError(f"{case_id}.candidateAssetIds contains duplicates")
    return [
        choose_asset(asset_id, asset_counts, f"{case_id}.candidateAssetIds[{index}]")
        for index, asset_id in enumerate(asset_ids, start=1)
    ]


def build_task_specs(
    raw_requests: list[tuple[str, dict[str, Any]]],
    field_counts: dict[tuple[str, ...], Counter[str]],
    preferred_fields: dict[tuple[str, ...], dict[str, Any]],
    asset_counts: dict[str, Counter[str]],
) -> list[dict[str, Any]]:
    task_specs: list[dict[str, Any]] = []
    for case_id, payload in raw_requests:
        content = payload["content"]
        user_query = content["userQuery"]
        if not isinstance(user_query, str) or not user_query.strip():
            raise TaskSpecImportError(f"{case_id}.userQuery must be a non-empty string")
        size = content["size"]
        if size not in {"2x2", "2x4"}:
            raise TaskSpecImportError(f"{case_id}.size is unsupported: {size!r}")
        task_spec = {
            "userQuery": user_query,
            "size": size,
            "dataModelSchema": build_data_model_schema(
                case_id,
                payload,
                field_counts,
                preferred_fields,
            ),
            "eventCandidates": build_event_candidates(case_id, content),
            "assetCandidates": build_asset_candidates(case_id, content, asset_counts),
        }
        if tuple(task_spec) != TASKSPEC_FIELDS:
            raise AssertionError("TaskSpec field order changed unexpectedly")
        task_specs.append(task_spec)
    return task_specs


def write_json_atomic(payload: Any, output_file: Path) -> None:
    if output_file.is_symlink():
        raise TaskSpecImportError(f"refusing to replace output symlink: {output_file}")
    body = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    output_file.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=output_file.parent,
            prefix=f".{output_file.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(body)
            temporary_path = Path(stream.name)
        os.replace(temporary_path, output_file)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def main() -> None:
    args = parse_args()
    try:
        raw_requests = load_raw_requests(args.input_dir)
        field_counts, preferred_fields, asset_counts = build_catalogs(
            args.schema_catalog,
            args.reference_file,
        )
        task_specs = build_task_specs(
            raw_requests,
            field_counts,
            preferred_fields,
            asset_counts,
        )
        write_json_atomic(task_specs, args.output_file)
    except TaskSpecImportError as exc:
        raise SystemExit(f"error: {exc}") from exc

    sizes = Counter(task_spec["size"] for task_spec in task_specs)
    print(f"Saved {len(task_specs)} TaskSpec cases to: {args.output_file.resolve()}")
    print(json.dumps({"sizes": dict(sorted(sizes.items()))}, ensure_ascii=False))


if __name__ == "__main__":
    main()
