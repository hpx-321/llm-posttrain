"""veRL custom reward bridge for TaskSpec -> Compact DSL.

This adapter is intentionally thin.  It decodes the framework's ``extra_info``,
counts completion tokens with the rollout tokenizer, and delegates all policy
semantics to :class:`RewardComputer`.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from frameworks.verl.create_my_card.rl.reward.compute_score import (
    DEFAULT_CONFIG,
    RewardComputer,
    RewardRequest,
)
from frameworks.verl.create_my_card.rl.reward.design_checker_adapter import (
    CheckerConfig,
    DesignCheckerAdapter,
    default_checker_root,
)


class OnlineRewardError(RuntimeError):
    """Raised instead of silently turning reward infrastructure errors into 0."""


def _decode_mapping(value: Any, label: str) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise OnlineRewardError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(value, Mapping):
        raise OnlineRewardError(f"{label} must be an object")
    return dict(value)


@lru_cache(maxsize=2)
def _tokenizer(path: str):
    try:
        from transformers import AutoTokenizer
    except ImportError as exc:
        raise OnlineRewardError(
            "transformers is required in the GRPO environment to count completion tokens"
        ) from exc
    return AutoTokenizer.from_pretrained(path, trust_remote_code=True)


def _count_completion_tokens(solution_str: str) -> int:
    path = os.environ.get("CMC_TOKENIZER_PATH")
    if not path:
        raise OnlineRewardError("CMC_TOKENIZER_PATH must point to the rollout tokenizer")
    encoded = _tokenizer(path)(solution_str, add_special_tokens=False)
    input_ids = encoded.get("input_ids") if isinstance(encoded, Mapping) else None
    if not isinstance(input_ids, list):
        raise OnlineRewardError("tokenizer did not return one input_ids list")
    return len(input_ids)


@lru_cache(maxsize=4)
def _computer(config_path: str, checker_root: str) -> RewardComputer:
    adapter = DesignCheckerAdapter(CheckerConfig(Path(checker_root)))
    return RewardComputer(adapter, config_path=Path(config_path))


def compute_score(
    data_source: str,
    solution_str: str,
    ground_truth: str,
    extra_info: Any = None,
) -> float:
    """veRL-compatible scalar reward entry point.

    Unvalidated rewards are rejected by default.  A two-step integration smoke
    run may opt in with ``CMC_ALLOW_UNVALIDATED_REWARD=1``; such a run is not a
    model-quality experiment and must never be selected as a checkpoint.
    """

    del ground_truth
    if data_source != "create_my_card_taskspec_to_dsl":
        raise OnlineRewardError(f"unsupported data_source: {data_source!r}")
    metadata = _decode_mapping(extra_info, "extra_info")
    task_spec = _decode_mapping(
        metadata.get("task_spec_json", metadata.get("task_spec")), "task_spec"
    )
    content_labels = _decode_mapping(
        metadata.get("content_labels_json", metadata.get("content_labels")),
        "content_labels",
    )
    sample_id = metadata.get("sample_id")
    if not isinstance(sample_id, str) or not sample_id:
        raise OnlineRewardError("extra_info.sample_id must be a non-empty string")

    config_path = str(Path(os.environ.get("CMC_REWARD_CONFIG", str(DEFAULT_CONFIG))).resolve())
    checker_root = str(
        Path(os.environ.get("DESIGN_CHECK_ROOT", str(default_checker_root()))).resolve()
    )
    audit = _computer(config_path, checker_root).compute(
        RewardRequest(
            sample_id=sample_id,
            solution_str=solution_str,
            task_spec=task_spec,
            content_labels=content_labels,
            completion_tokens=_count_completion_tokens(solution_str),
        )
    )
    if audit.masked:
        raise OnlineRewardError(
            f"reward infrastructure masked {sample_id}; retry the rollout instead of assigning 0"
        )
    if audit.score is None:
        raise OnlineRewardError(
            f"reward for {sample_id} is incomplete; all components and reviewed labels are required"
        )
    if not audit.policy_update_eligible and os.environ.get(
        "CMC_ALLOW_UNVALIDATED_REWARD"
    ) != "1":
        raise OnlineRewardError(
            "reward is not policy-update eligible; validate the reward config or set "
            "CMC_ALLOW_UNVALIDATED_REWARD=1 only for an integration smoke run"
        )
    return float(audit.score)
