"""Framework-neutral dataset builders for RFT, DPO, and GRPO.

Candidate generation and reward evaluation are intentionally upstream inputs.
This module only performs deterministic selection, pairing, schema conversion,
and lightweight input validation.  It never calls a model or mutates a reward.
"""

from __future__ import annotations

import json
import math
import os
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from frameworks.verl.create_my_card.sft.dataset import build_parquet

from .contracts import PipelineError, TASK_NAME


RFT_DATA_SCHEMA = "create-my-card.rft-selection.v1"
DPO_DATA_SCHEMA = "create-my-card.dpo-pairs.v1"
GRPO_DATA_SCHEMA = "create-my-card.grpo-prompts.v1"
# Matches the existing SFT OOM-probe default and covers the default global
# batch (2 samples per DP rank) through 128 data-parallel ranks.
RFT_SMOKE_ROW_COUNT = 256


@dataclass(frozen=True)
class ScoredCandidate:
    candidate_id: str
    group_id: str
    solution: str
    score: float
    completion_tokens: int | None
    producer_checkpoint: str | None
    candidate: Mapping[str, Any]
    audit: Mapping[str, Any]


def read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise PipelineError(f"{label} does not exist: {path}")
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig") as stream:
        for line_number, raw_line in enumerate(stream, start=1):
            if not raw_line.strip():
                continue
            try:
                row = json.loads(raw_line)
            except json.JSONDecodeError as exc:
                raise PipelineError(
                    f"invalid {label} JSONL at line {line_number}: {path}: {exc}"
                ) from exc
            if not isinstance(row, dict):
                raise PipelineError(f"{label} line {line_number} must be an object")
            rows.append(row)
    if not rows:
        raise PipelineError(f"{label} is empty: {path}")
    return rows


def _atomic_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    count = 0
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
                count += 1
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return count


def _ensure_new_targets(paths: Sequence[Path]) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise PipelineError(f"refusing to overwrite existing dataset artifacts: {existing}")


def _index_unique(
    rows: Sequence[Mapping[str, Any]], key: str, label: str
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for index, row in enumerate(rows, start=1):
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise PipelineError(f"{label} row {index}: {key} must be a non-empty string")
        if value in result:
            raise PipelineError(f"duplicate {label} {key}: {value}")
        result[value] = row
    return result


def _audit_score(audit: Mapping[str, Any], *, allow_partial_score: bool) -> float | None:
    value = audit.get("score")
    if value is None and allow_partial_score:
        value = audit.get("partial_score")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def _gate_map(audit: Mapping[str, Any]) -> dict[str, bool | None]:
    result: dict[str, bool | None] = {}
    gates = audit.get("gates")
    if not isinstance(gates, list):
        return result
    for gate in gates:
        if not isinstance(gate, Mapping):
            continue
        name = gate.get("name")
        passed = gate.get("passed")
        if isinstance(name, str) and (passed is None or isinstance(passed, bool)):
            result[name] = passed
    return result


def _chosen_eligible(
    audit: Mapping[str, Any], *, require_policy_update_eligible: bool
) -> bool:
    if audit.get("masked") is True:
        return False
    if require_policy_update_eligible and audit.get("policy_update_eligible") is not True:
        return False
    return not any(passed is False for passed in _gate_map(audit).values())


def _rejected_eligible(audit: Mapping[str, Any]) -> bool:
    if audit.get("masked") is True:
        return False
    return _gate_map(audit).get("conversion") is True


def load_scored_candidates(
    *,
    candidates_path: Path,
    audits_path: Path,
    allow_partial_score: bool,
    expected_producer_checkpoint: str | None = None,
) -> list[ScoredCandidate]:
    candidates = read_jsonl(candidates_path, "candidate file")
    audits = read_jsonl(audits_path, "reward audit file")
    audits_by_id = _index_unique(audits, "sample_id", "reward audit")
    result: list[ScoredCandidate] = []
    seen_candidates: set[str] = set()
    for index, candidate in enumerate(candidates, start=1):
        candidate_id = candidate.get("id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise PipelineError(f"candidate row {index}: id must be a non-empty string")
        if candidate_id in seen_candidates:
            raise PipelineError(f"duplicate candidate id: {candidate_id}")
        seen_candidates.add(candidate_id)
        group_id = candidate.get("groupId", candidate_id)
        solution = candidate.get("designCompactDsl")
        if not isinstance(group_id, str) or not group_id:
            raise PipelineError(f"{candidate_id}: groupId must be a non-empty string")
        if not isinstance(solution, str) or not solution.strip():
            raise PipelineError(f"{candidate_id}: designCompactDsl must be non-empty")
        producer_checkpoint = candidate.get("producerCheckpoint")
        if producer_checkpoint is not None and not isinstance(producer_checkpoint, str):
            raise PipelineError(f"{candidate_id}: producerCheckpoint must be a string")
        if (
            expected_producer_checkpoint is not None
            and producer_checkpoint != expected_producer_checkpoint
        ):
            raise PipelineError(
                f"{candidate_id}: producer checkpoint mismatch; expected "
                f"{expected_producer_checkpoint!r}, got {producer_checkpoint!r}"
            )
        audit = audits_by_id.get(candidate_id)
        if audit is None:
            raise PipelineError(f"{candidate_id}: no matching reward audit")
        score = _audit_score(audit, allow_partial_score=allow_partial_score)
        if score is None:
            continue
        completion_tokens = candidate.get("completionTokens")
        if isinstance(completion_tokens, bool) or not isinstance(completion_tokens, int):
            completion_tokens = None
        result.append(
            ScoredCandidate(
                candidate_id=candidate_id,
                group_id=group_id,
                solution=solution.strip(),
                score=score,
                completion_tokens=completion_tokens,
                producer_checkpoint=producer_checkpoint,
                candidate=candidate,
                audit=audit,
            )
        )
    if not result:
        raise PipelineError("no candidates have a usable score")
    return result


def _taskspec_map(path: Path) -> dict[str, dict[str, Any]]:
    return {
        record.sample_id: record.task_spec
        for record in build_parquet.load_taskspec_records(path)
    }


def _prompt_messages(system_prompt: str, task_spec: Mapping[str, Any]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append(
        {
            "role": "user",
            "content": build_parquet.canonicalize_taskspec(dict(task_spec)),
        }
    )
    return messages


def _split_any(
    rows: Sequence[Mapping[str, Any]], *, validation_ratio: float, seed: int
) -> tuple[list[Mapping[str, Any]], list[Mapping[str, Any]]]:
    if not 0 <= validation_ratio < 1:
        raise PipelineError("validation_ratio must be in [0, 1)")
    values = list(rows)
    if validation_ratio == 0 or len(values) == 1:
        return values, []
    count = max(1, round(len(values) * validation_ratio))
    count = min(count, len(values) - 1)
    shuffled = list(values)
    random.Random(seed).shuffle(shuffled)
    validation_ids = {str(row["id"]) for row in shuffled[:count]}
    return (
        [row for row in values if str(row["id"]) not in validation_ids],
        [row for row in values if str(row["id"]) in validation_ids],
    )


def _build_rft_smoke_rows(
    train_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Repeat selected RFT rows for a fixed-size, checkpoint-free gradient smoke."""

    smoke_rows: list[dict[str, Any]] = []
    for index in range(RFT_SMOKE_ROW_COUNT):
        source = train_rows[index % len(train_rows)]
        row = dict(source)
        row["id"] = f"{source['id']}__rft_smoke_{index:04d}"
        smoke_rows.append(row)
    return smoke_rows


def build_rft_dataset(
    *,
    candidates_path: Path,
    audits_path: Path,
    taskspec_path: Path,
    system_prompt_path: Path,
    output_dir: Path,
    min_score: float,
    validation_ratio: float,
    seed: int,
    require_policy_update_eligible: bool,
    allow_partial_score: bool,
    expected_producer_checkpoint: str | None = None,
) -> Mapping[str, Any]:
    """Select one highest-scoring, fully gated candidate per TaskSpec."""

    targets = [
        output_dir / "train.parquet",
        output_dir / "validation.parquet",
        output_dir / "oom_probe.parquet",
        output_dir / "selection.jsonl",
    ]
    _ensure_new_targets(targets)
    tasks = _taskspec_map(taskspec_path)
    system_prompt = build_parquet.load_system_prompt(system_prompt_path)
    candidates = load_scored_candidates(
        candidates_path=candidates_path,
        audits_path=audits_path,
        allow_partial_score=allow_partial_score,
        expected_producer_checkpoint=expected_producer_checkpoint,
    )
    groups: dict[str, list[ScoredCandidate]] = {}
    for candidate in candidates:
        groups.setdefault(candidate.group_id, []).append(candidate)

    rows: list[dict[str, Any]] = []
    selections: list[dict[str, Any]] = []
    for group_id in sorted(groups):
        task_spec = tasks.get(group_id)
        if task_spec is None:
            raise PipelineError(f"candidate group has no matching TaskSpec: {group_id}")
        eligible = [
            candidate
            for candidate in groups[group_id]
            if candidate.score >= min_score
            and _chosen_eligible(
                candidate.audit,
                require_policy_update_eligible=require_policy_update_eligible,
            )
        ]
        if not eligible:
            continue
        chosen = max(
            eligible,
            key=lambda candidate: (
                candidate.score,
                -(candidate.completion_tokens or len(candidate.solution)),
                candidate.candidate_id,
            ),
        )
        messages = _prompt_messages(system_prompt, task_spec)
        messages.append({"role": "assistant", "content": chosen.solution})
        rows.append({"id": group_id, "messages": messages, "enable_thinking": False})
        selections.append(
            {
                "schema_version": RFT_DATA_SCHEMA,
                "id": group_id,
                "candidate_id": chosen.candidate_id,
                "score": chosen.score,
                "producer_checkpoint": chosen.producer_checkpoint,
            }
        )
    if not rows:
        raise PipelineError("RFT selection produced no rows")

    train_rows, validation_rows = _split_any(
        rows, validation_ratio=validation_ratio, seed=seed
    )
    smoke_rows = _build_rft_smoke_rows(train_rows)
    build_parquet.write_parquet(train_rows, output_dir / "train.parquet")
    build_parquet.write_parquet(validation_rows, output_dir / "validation.parquet")
    build_parquet.write_parquet(smoke_rows, output_dir / "oom_probe.parquet")
    _atomic_jsonl(output_dir / "selection.jsonl", selections)
    summary = {
        "schema_version": RFT_DATA_SCHEMA,
        "task": TASK_NAME,
        "train_count": len(train_rows),
        "validation_count": len(validation_rows),
        "smoke_count": len(smoke_rows),
        "source_candidate_count": len(candidates),
        "selected_count": len(rows),
        "min_score": min_score,
        "require_policy_update_eligible": require_policy_update_eligible,
        "allow_partial_score": allow_partial_score,
        "expected_producer_checkpoint": expected_producer_checkpoint,
        "seed": seed,
    }
    return summary


def build_dpo_dataset(
    *,
    candidates_path: Path,
    audits_path: Path,
    taskspec_path: Path,
    system_prompt_path: Path,
    output_dir: Path,
    chosen_min_score: float,
    min_score_margin: float,
    max_length_ratio: float,
    validation_ratio: float,
    seed: int,
    require_policy_update_eligible: bool,
    allow_partial_score: bool,
    expected_producer_checkpoint: str | None = None,
) -> Mapping[str, Any]:
    """Build same-prompt chosen/rejected pairs with score and length guards."""

    if min_score_margin <= 0:
        raise PipelineError("min_score_margin must be positive")
    if max_length_ratio < 1:
        raise PipelineError("max_length_ratio must be >= 1")
    targets = [
        output_dir / "train.jsonl",
        output_dir / "validation.jsonl",
    ]
    _ensure_new_targets(targets)
    tasks = _taskspec_map(taskspec_path)
    system_prompt = build_parquet.load_system_prompt(system_prompt_path)
    candidates = load_scored_candidates(
        candidates_path=candidates_path,
        audits_path=audits_path,
        allow_partial_score=allow_partial_score,
        expected_producer_checkpoint=expected_producer_checkpoint,
    )
    groups: dict[str, list[ScoredCandidate]] = {}
    for candidate in candidates:
        groups.setdefault(candidate.group_id, []).append(candidate)

    pairs: list[dict[str, Any]] = []
    for group_id in sorted(groups):
        task_spec = tasks.get(group_id)
        if task_spec is None:
            raise PipelineError(f"candidate group has no matching TaskSpec: {group_id}")
        chosen_pool = [
            candidate
            for candidate in groups[group_id]
            if candidate.score >= chosen_min_score
            and _chosen_eligible(
                candidate.audit,
                require_policy_update_eligible=require_policy_update_eligible,
            )
        ]
        rejected_pool = [
            candidate
            for candidate in groups[group_id]
            if _rejected_eligible(candidate.audit)
        ]
        if not chosen_pool or not rejected_pool:
            continue
        chosen = max(chosen_pool, key=lambda item: (item.score, item.candidate_id))
        candidates_for_rejection: list[ScoredCandidate] = []
        chosen_length = chosen.completion_tokens or len(chosen.solution)
        for rejected in rejected_pool:
            if rejected.candidate_id == chosen.candidate_id:
                continue
            if chosen.score - rejected.score < min_score_margin:
                continue
            rejected_length = rejected.completion_tokens or len(rejected.solution)
            ratio = max(chosen_length, rejected_length) / max(
                1, min(chosen_length, rejected_length)
            )
            if ratio <= max_length_ratio:
                candidates_for_rejection.append(rejected)
        if not candidates_for_rejection:
            continue
        rejected = min(
            candidates_for_rejection,
            key=lambda item: (
                item.score,
                abs((item.completion_tokens or len(item.solution)) - chosen_length),
                item.candidate_id,
            ),
        )
        pairs.append(
            {
                "schema_version": DPO_DATA_SCHEMA,
                "id": group_id,
                "prompt": _prompt_messages(system_prompt, task_spec),
                "chosen": [{"role": "assistant", "content": chosen.solution}],
                "rejected": [{"role": "assistant", "content": rejected.solution}],
                "chat_template_kwargs": {"enable_thinking": False},
                "extra_info": {
                    "task": TASK_NAME,
                    "chosen_candidate_id": chosen.candidate_id,
                    "rejected_candidate_id": rejected.candidate_id,
                    "chosen_score": chosen.score,
                    "rejected_score": rejected.score,
                    "score_margin": chosen.score - rejected.score,
                    "producer_checkpoint": chosen.producer_checkpoint,
                },
            }
        )
    if not pairs:
        raise PipelineError("DPO pairing produced no rows")
    train_rows, validation_rows = _split_any(
        pairs, validation_ratio=validation_ratio, seed=seed
    )
    _atomic_jsonl(output_dir / "train.jsonl", train_rows)
    _atomic_jsonl(output_dir / "validation.jsonl", validation_rows)
    summary = {
        "schema_version": DPO_DATA_SCHEMA,
        "task": TASK_NAME,
        "train_count": len(train_rows),
        "validation_count": len(validation_rows),
        "source_candidate_count": len(candidates),
        "pair_count": len(pairs),
        "chosen_min_score": chosen_min_score,
        "min_score_margin": min_score_margin,
        "max_length_ratio": max_length_ratio,
        "require_policy_update_eligible": require_policy_update_eligible,
        "allow_partial_score": allow_partial_score,
        "expected_producer_checkpoint": expected_producer_checkpoint,
        "seed": seed,
    }
    return summary


def _load_reviewed_labels(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PipelineError(f"invalid content label file: {path}: {exc}") from exc
    if not isinstance(payload, list):
        raise PipelineError("content label file must be a JSON array")
    result: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(payload, start=1):
        if not isinstance(row, dict):
            raise PipelineError(f"content label row {index} must be an object")
        sample_id = row.get("id")
        if not isinstance(sample_id, str) or not sample_id:
            raise PipelineError(f"content label row {index}: invalid id")
        if sample_id in result:
            raise PipelineError(f"duplicate content label id: {sample_id}")
        if row.get("reviewed") is True:
            result[sample_id] = row
    return result


def _write_grpo_parquet(rows: Sequence[Mapping[str, Any]], path: Path) -> None:
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise PipelineError("pyarrow is required to build GRPO parquet") from exc
    message_type = pa.struct(
        [
            pa.field("role", pa.string(), nullable=False),
            pa.field("content", pa.string(), nullable=False),
        ]
    )
    schema = pa.schema(
        [
            pa.field("id", pa.string(), nullable=False),
            pa.field("data_source", pa.string(), nullable=False),
            pa.field("prompt", pa.list_(message_type), nullable=False),
            pa.field("ability", pa.string(), nullable=False),
            pa.field(
                "reward_model",
                pa.struct(
                    [
                        pa.field("style", pa.string(), nullable=False),
                        pa.field("ground_truth", pa.string(), nullable=False),
                    ]
                ),
                nullable=False,
            ),
            pa.field(
                "extra_info",
                pa.struct(
                    [
                        pa.field("sample_id", pa.string(), nullable=False),
                        pa.field("task_spec_json", pa.string(), nullable=False),
                        pa.field("content_labels_json", pa.string(), nullable=False),
                    ]
                ),
                nullable=False,
            ),
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(list(rows), schema=schema)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False
        ) as stream:
            temporary_path = Path(stream.name)
        pq.write_table(table, temporary_path, compression="zstd")
        if pq.read_metadata(temporary_path).num_rows != len(rows):
            raise PipelineError(f"GRPO parquet row-count verification failed: {path}")
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def build_grpo_dataset(
    *,
    taskspec_path: Path,
    system_prompt_path: Path,
    labels_path: Path | None,
    output_dir: Path,
    validation_ratio: float,
    seed: int,
    require_reviewed_labels: bool,
) -> Mapping[str, Any]:
    """Build veRL prompt parquet while keeping task metadata JSON-encoded."""

    targets = [
        output_dir / "train.parquet",
        output_dir / "validation.parquet",
    ]
    _ensure_new_targets(targets)
    tasks = _taskspec_map(taskspec_path)
    labels = _load_reviewed_labels(labels_path)
    system_prompt = build_parquet.load_system_prompt(system_prompt_path)
    rows: list[dict[str, Any]] = []
    for sample_id, task_spec in tasks.items():
        label = labels.get(sample_id)
        if require_reviewed_labels and label is None:
            continue
        rows.append(
            {
                "id": sample_id,
                "data_source": "create_my_card_taskspec_to_dsl",
                "prompt": _prompt_messages(system_prompt, task_spec),
                "ability": "card_generation",
                "reward_model": {"style": "rule", "ground_truth": ""},
                "extra_info": {
                    "sample_id": sample_id,
                    "task_spec_json": json.dumps(
                        task_spec, ensure_ascii=False, separators=(",", ":"), allow_nan=False
                    ),
                    "content_labels_json": json.dumps(
                        label or {}, ensure_ascii=False, separators=(",", ":"), allow_nan=False
                    ),
                },
            }
        )
    if not rows:
        raise PipelineError("GRPO dataset produced no rows")
    train_rows, validation_rows = _split_any(
        rows, validation_ratio=validation_ratio, seed=seed
    )
    _write_grpo_parquet(train_rows, output_dir / "train.parquet")
    _write_grpo_parquet(validation_rows, output_dir / "validation.parquet")
    summary = {
        "schema_version": GRPO_DATA_SCHEMA,
        "task": TASK_NAME,
        "train_count": len(train_rows),
        "validation_count": len(validation_rows),
        "reviewed_label_count": len(labels),
        "require_reviewed_labels": require_reviewed_labels,
        "seed": seed,
    }
    return summary
