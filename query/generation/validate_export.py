#!/usr/bin/env python3
"""Read-only audit for the frozen Natural Query release (stdlib only)."""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path


FIELDS = ["id", "category", "matched_actions", "scene_id", "persona_id", "query"]
CATEGORIES = ["日历", "天气", "备忘录", "闹钟", "电话", "电池", "运动健康", "相机", "位置", "音乐", "导航", "系统设置"]
TECHNICAL_TERMS = ("api", "json", "schema", "taskspec", "cardspec", "dsl", "datamodel", "query_plan", "request_id", "html", "字段", "数据包括", "纯数字")
BASE_ROWS = 68
ADDED_ROWS = 1000
NEAR_DUPLICATE_THRESHOLD = 0.92


def read_csv(path: Path, delimiter: str = ",") -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file, delimiter=delimiter))


def read_json(path: Path) -> list[dict[str, str]]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, str]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def atomic_counts(rows: list[dict[str, str]]) -> Counter[str]:
    return Counter(part for row in rows for part in row["category"].split("+") if part)


def normalized(text: str) -> str:
    return re.sub(r"[^\w]+", "", text.lower())


def find_catalog_root(dataset_root: Path, explicit: str | None) -> Path | None:
    candidates = []
    if explicit:
        supplied = Path(explicit)
        candidates.extend([supplied, supplied / "catalogs"])
    candidates.extend(sorted(dataset_root.parent.glob("query-balanced-*-workfiles/query_agent/catalogs"), reverse=True))
    candidates.append(dataset_root.parent / "query_agent" / "catalogs")
    for candidate in candidates:
        if (candidate / "draft" / "scenes.draft.json").is_file() and (candidate / "personas.json").is_file():
            return candidate.resolve()
    return None


def near_duplicates(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    by_scene: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_scene[row["scene_id"]].append(row)
    hits = []
    for scene_rows in by_scene.values():
        for index, left in enumerate(scene_rows):
            left_text = normalized(left["query"])
            for right in scene_rows[index + 1:]:
                score = SequenceMatcher(None, left_text, normalized(right["query"])).ratio()
                if score >= NEAR_DUPLICATE_THRESHOLD:
                    hits.append({"left": left["id"], "right": right["id"], "score": round(score, 3)})
    return hits


def audit(root: Path, catalog_root: Path | None) -> dict[str, object]:
    errors: list[str] = []
    try:
        rows = read_csv(root / "natural-queries.csv")
        json_rows = read_json(root / "natural-queries.json")
        jsonl_rows = read_jsonl(root / "natural-queries.jsonl")
    except (OSError, csv.Error, json.JSONDecodeError) as exc:
        return {"status": "fail", "errors": [f"cannot read dataset: {exc}"]}

    if rows != json_rows:
        errors.append("CSV and JSON contents differ")
    if rows != jsonl_rows:
        errors.append("CSV and JSONL contents differ")
    if len(rows) != BASE_ROWS + ADDED_ROWS:
        errors.append(f"expected {BASE_ROWS + ADDED_ROWS} rows, got {len(rows)}")

    for row_number, row in enumerate(rows, 2):
        if list(row) != FIELDS:
            errors.append(f"CSV row {row_number}: fields differ from {FIELDS}")
            break
        if any(not row[field].strip() for field in FIELDS):
            errors.append(f"CSV row {row_number}: empty required field")

    ids = [row["id"] for row in rows]
    queries = [row["query"].strip() for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate id")
    if len(queries) != len(set(queries)):
        errors.append("duplicate query")

    unknown_categories = sorted(set(atomic_counts(rows)) - set(CATEGORIES))
    if unknown_categories:
        errors.append(f"unknown categories: {unknown_categories}")
    malformed_categories = [row["id"] for row in rows if not 1 <= len(row["category"].split("+")) <= 3]
    if malformed_categories:
        errors.append(f"category must contain 1-3 atomic categories: {malformed_categories[:10]}")

    base, added = rows[:BASE_ROWS], rows[BASE_ROWS:]
    shape_counts = Counter(len(row["category"].split("+")) for row in added)
    if shape_counts != Counter({2: 988, 3: 12}):
        errors.append(f"added composite shape mismatch: {dict(shape_counts)}")

    final_counts = atomic_counts(rows)
    if set(final_counts.values()) != {174} or set(final_counts) != set(CATEGORIES):
        errors.append(f"atomic categories are not all balanced to 174: {dict(final_counts)}")

    card_missing = [row["id"] for row in rows if not any(word in row["query"] for word in ("卡片", "小组件"))]
    technical_hits = [
        {"id": row["id"], "terms": [term for term in TECHNICAL_TERMS if term in row["query"].lower()]}
        for row in rows if any(term in row["query"].lower() for term in TECHNICAL_TERMS)
    ]
    if card_missing:
        errors.append(f"missing card/widget intent: {card_missing[:10]}")
    if technical_hits:
        errors.append(f"technical/template language found: {technical_hits[:10]}")

    source_prefix_check: object = "not_checked"
    source_tsv = root / "queries.tsv"
    if source_tsv.is_file():
        source_rows = read_csv(source_tsv, "\t")
        source_prefix_check = {"rows": len(source_rows), "exact_prefix_match": rows[:len(source_rows)] == source_rows}
        if rows[:len(source_rows)] != source_rows:
            errors.append("queries.tsv is not an exact prefix of the release")

    catalog_check: object = "blocked: catalog not found; pass --catalog-root"
    frozen_matches: list[str] = []
    if catalog_root:
        scenes_doc = json.loads((catalog_root / "draft" / "scenes.draft.json").read_text(encoding="utf-8"))
        personas_doc = json.loads((catalog_root / "personas.json").read_text(encoding="utf-8"))
        scenes = {item["scene_id"]: item for item in scenes_doc["scenes"]}
        personas = {item["persona_id"] for item in personas_doc["personas"]}
        catalog_errors = []
        for row in rows:
            scene = scenes.get(row["scene_id"])
            actions = {item.strip() for item in row["matched_actions"].split("；") if item.strip()}
            if not scene:
                catalog_errors.append(f"{row['id']}: unknown scene {row['scene_id']}")
            elif not actions.issubset(set(scene["candidate_actions"])):
                outside = sorted(actions - set(scene["candidate_actions"]))
                catalog_errors.append(f"{row['id']}: action outside scene {row['scene_id']}: {outside}")
            if row["persona_id"] not in personas:
                catalog_errors.append(f"{row['id']}: unknown persona {row['persona_id']}")
        frozen_path = catalog_root / "frozen_evaluation_queries.json"
        if frozen_path.is_file():
            frozen = {item["query"].strip() for item in json.loads(frozen_path.read_text(encoding="utf-8"))["queries"]}
            frozen_matches = [row["id"] for row in rows if row["query"].strip() in frozen]
            if frozen_matches:
                catalog_errors.append(f"exact frozen-evaluation matches: {frozen_matches[:10]}")
        if catalog_errors:
            errors.append(f"{len(catalog_errors)} rows fail strict scene/action/persona or frozen-query checks; see catalog_check.examples")
        catalog_check = {"root": str(catalog_root), "error_count": len(catalog_errors), "examples": catalog_errors[:20]}
    else:
        errors.append("catalog not found; pass --catalog-root to verify scene/action/persona provenance")

    duplicate_pairs = near_duplicates(rows)
    if duplicate_pairs:
        errors.append(f"same-scene near duplicates >= {NEAR_DUPLICATE_THRESHOLD}: {duplicate_pairs[:10]}")

    openings = Counter(normalized(row["query"])[:10] for row in added)
    lengths = [len(row["query"]) for row in added]
    return {
        "status": "pass" if not errors else "fail",
        "rows": {"base": len(base), "added": len(added), "total": len(rows), "added_shapes": dict(sorted(shape_counts.items()))},
        "atomic_category_counts": {"base": dict(atomic_counts(base)), "added": dict(atomic_counts(added)), "final": dict(final_counts)},
        "coverage": {"personas": len({row["persona_id"] for row in rows}), "scenes": len({row["scene_id"] for row in rows})},
        "quality": {
            "duplicate_ids": len(ids) - len(set(ids)),
            "duplicate_queries": len(queries) - len(set(queries)),
            "near_duplicate_threshold": NEAR_DUPLICATE_THRESHOLD,
            "near_duplicate_count": len(duplicate_pairs),
            "largest_repeated_10_char_opening": max(openings.values(), default=0),
            "technical_hits": technical_hits,
            "missing_card_intent": card_missing,
            "added_query_length": {"min": min(lengths), "max": max(lengths), "average": round(sum(lengths) / len(lengths), 2)},
            "exact_frozen_matches": frozen_matches,
        },
        "source_prefix_check": source_prefix_check,
        "catalog_check": catalog_check,
        "errors": errors,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Natural Query files without modifying them.")
    parser.add_argument("--dataset-root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--catalog-root", help="Path to query_agent or its catalogs directory")
    parser.add_argument("--write-report", action="store_true", help="Replace validation-report.json with the recomputed report")
    args = parser.parse_args()
    root = Path(args.dataset_root).resolve()
    report = audit(root, find_catalog_root(root, args.catalog_root))
    output = json.dumps(report, ensure_ascii=False, indent=2)
    print(output)
    if args.write_report:
        (root / "validation-report.json").write_text(output + "\n", encoding="utf-8")
    raise SystemExit(report["status"] != "pass")


if __name__ == "__main__":
    main()
