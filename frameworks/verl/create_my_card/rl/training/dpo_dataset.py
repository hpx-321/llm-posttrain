"""TaskSpec-to-DSL preference data for the veRL 0.7.1 DPO adapter.

The pair-preservation contract follows veRL's offline-DPO RFC and public
``dpo-dataset-pipeline`` branch.  This project keeps its message-based input
contract and uses veRL 0.7.1's ``force_group_size=2`` at the engine boundary
instead of patching veRL's newer packed-pair expansion into site-packages.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import Dataset

from frameworks.verl.create_my_card.sft.dataset.qwen36_sft_dataset import (
    apply_template,
)


class DPODataError(ValueError):
    """Raised when a preference row cannot satisfy the DPO contract."""


def _validate_messages(value: Any, *, label: str, roles: tuple[str, ...]) -> list[dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise DPODataError(f"{label} must be a non-empty message list")
    result: list[dict[str, str]] = []
    for index, message in enumerate(value):
        if not isinstance(message, dict):
            raise DPODataError(f"{label}[{index}] must be an object")
        role = message.get("role")
        content = message.get("content")
        if role not in roles:
            raise DPODataError(f"{label}[{index}] has unsupported role: {role!r}")
        if not isinstance(content, str) or not content.strip():
            raise DPODataError(f"{label}[{index}] content is empty")
        result.append({"role": role, "content": content})
    return result


def _validate_prompt(value: Any, *, sample_id: str) -> list[dict[str, str]]:
    prompt = _validate_messages(
        value,
        label=f"{sample_id}/prompt",
        roles=("system", "user"),
    )
    role_order = [message["role"] for message in prompt]
    if role_order not in (["user"], ["system", "user"]):
        raise DPODataError(
            f"{sample_id}/prompt roles must be user or system/user, got {role_order}"
        )
    return prompt


def encode_preference_sequence(
    tokenizer: Any,
    prompt: list[dict[str, str]],
    completion: list[dict[str, str]],
    *,
    sample_id: str,
    label: str,
    max_prompt_length: int,
    max_length: int,
) -> dict[str, torch.Tensor]:
    """Encode one prompt/completion while preserving the exact chat-template boundary."""
    prompt_ids = apply_template(tokenizer, prompt, generation=True)
    full_ids = apply_template(tokenizer, [*prompt, *completion], generation=False)
    if len(prompt_ids) > max_prompt_length:
        raise DPODataError(
            f"{sample_id}/{label}: prompt_length={len(prompt_ids)} exceeds "
            f"max_prompt_length={max_prompt_length}"
        )
    if full_ids[: len(prompt_ids)] != prompt_ids:
        raise DPODataError(
            f"{sample_id}/{label}: sequence does not start with the non-thinking prompt"
        )
    if len(full_ids) > max_length:
        raise DPODataError(
            f"{sample_id}/{label}: sequence_length={len(full_ids)} exceeds "
            f"max_length={max_length}"
        )
    if len(full_ids) == len(prompt_ids):
        raise DPODataError(f"{sample_id}/{label}: completion has no trainable tokens")

    input_ids = torch.tensor(full_ids, dtype=torch.long)
    loss_mask = torch.zeros(len(full_ids), dtype=torch.long)
    loss_mask[len(prompt_ids) :] = 1
    return {
        "input_ids": input_ids,
        "position_ids": torch.arange(len(full_ids), dtype=torch.long),
        "loss_mask": loss_mask,
    }


class DPOPairDataset(Dataset):
    """JSONL preference pairs with mutable, in-memory reference log-prob storage."""

    def __init__(
        self,
        jsonl_files: str | Sequence[str],
        tokenizer: Any,
        *,
        max_length: int,
        max_prompt_length: int,
        max_samples: int = -1,
        repeat_to_size: int = 0,
    ) -> None:
        paths = [jsonl_files] if isinstance(jsonl_files, str) else list(jsonl_files)
        if not paths:
            raise DPODataError("at least one DPO JSONL file is required")
        if max_length <= 0 or max_prompt_length <= 0:
            raise DPODataError("max lengths must be positive")
        if max_prompt_length > max_length:
            raise DPODataError("max_prompt_length cannot exceed max_length")

        self.tokenizer = tokenizer
        self.max_length = max_length
        self.max_prompt_length = max_prompt_length
        self.rows = self._read_rows([Path(path) for path in paths])
        if 0 < max_samples < len(self.rows):
            self.rows = self.rows[:max_samples]
        if not self.rows:
            raise DPODataError("DPO dataset is empty")
        if repeat_to_size > len(self.rows):
            source = self.rows
            self.rows = [source[index % len(source)] for index in range(repeat_to_size)]
        self.reference_logps: list[tuple[float, float] | None] = [None] * len(self.rows)
        print(f"DPOPairDataset len: {len(self.rows)}")

    @staticmethod
    def _read_rows(paths: list[Path]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in paths:
            if not path.is_file():
                raise FileNotFoundError(f"DPO JSONL file does not exist: {path}")
            with path.open("r", encoding="utf-8-sig") as stream:
                for line_number, line in enumerate(stream, start=1):
                    if not line.strip():
                        continue
                    try:
                        row = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise DPODataError(f"{path}:{line_number}: invalid JSON") from exc
                    if not isinstance(row, dict):
                        raise DPODataError(f"{path}:{line_number}: row must be an object")
                    rows.append(row)
        return rows

    def __len__(self) -> int:
        return len(self.rows)

    def set_reference_logps(self, index: int, chosen: float, rejected: float) -> None:
        values = torch.tensor([chosen, rejected], dtype=torch.float64)
        if not torch.isfinite(values).all():
            raise DPODataError(f"row {index}: reference log-probs must be finite")
        self.reference_logps[index] = (float(chosen), float(rejected))

    def require_complete_reference(self) -> None:
        missing = [index for index, value in enumerate(self.reference_logps) if value is None]
        if missing:
            raise RuntimeError(f"reference log-probs are missing for {len(missing)} DPO rows")

    def __getitem__(self, item: int) -> dict[str, Any]:
        row = self.rows[item]
        sample_id = row.get("id")
        if not isinstance(sample_id, str) or not sample_id:
            raise DPODataError(f"row {item}: id must be a non-empty string")
        template_kwargs = row.get("chat_template_kwargs")
        if template_kwargs != {"enable_thinking": False}:
            raise DPODataError(
                f"{sample_id}: chat_template_kwargs must disable thinking"
            )
        prompt = _validate_prompt(row.get("prompt"), sample_id=sample_id)
        chosen = _validate_messages(
            row.get("chosen"), label=f"{sample_id}/chosen", roles=("assistant",)
        )
        rejected = _validate_messages(
            row.get("rejected"), label=f"{sample_id}/rejected", roles=("assistant",)
        )
        if len(chosen) != 1 or len(rejected) != 1:
            raise DPODataError(f"{sample_id}: chosen and rejected must contain one message")
        if chosen[0]["content"].strip() == rejected[0]["content"].strip():
            raise DPODataError(f"{sample_id}: chosen and rejected must differ")
        for label, messages in (("chosen", chosen), ("rejected", rejected)):
            content = messages[0]["content"].lower()
            if "<think>" in content or "</think>" in content:
                raise DPODataError(f"{sample_id}/{label}: completion contains think tags")

        result: dict[str, Any] = {
            "sample_index": item,
            "chosen": encode_preference_sequence(
                self.tokenizer,
                prompt,
                chosen,
                sample_id=sample_id,
                label="chosen",
                max_prompt_length=self.max_prompt_length,
                max_length=self.max_length,
            ),
            "rejected": encode_preference_sequence(
                self.tokenizer,
                prompt,
                rejected,
                sample_id=sample_id,
                label="rejected",
                max_prompt_length=self.max_prompt_length,
                max_length=self.max_length,
            ),
        }
        reference = self.reference_logps[item]
        if reference is not None:
            result["reference_logps"] = reference
        return result


class DPOPairCollator:
    """Flatten each pair as adjacent chosen/rejected sequences for one model forward."""

    def __call__(self, batch: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
        sequences: list[dict[str, torch.Tensor]] = []
        pair_indices: list[int] = []
        is_chosen: list[bool] = []
        reference_logps: list[float] = []
        has_reference = all("reference_logps" in item for item in batch)
        if not has_reference and any("reference_logps" in item for item in batch):
            raise DPODataError("DPO batch mixes rows with and without reference log-probs")
        for item in batch:
            pair_index = int(item["sample_index"])
            chosen_ref, rejected_ref = item.get("reference_logps", (0.0, 0.0))
            for sequence, selected, reference in (
                (item["chosen"], True, chosen_ref),
                (item["rejected"], False, rejected_ref),
            ):
                sequences.append(sequence)
                pair_indices.append(pair_index)
                is_chosen.append(selected)
                reference_logps.append(float(reference))

        output = {
            key: torch.nested.as_nested_tensor(
                [sequence[key] for sequence in sequences], layout=torch.jagged
            )
            for key in ("input_ids", "position_ids", "loss_mask")
        }
        output["pair_index"] = torch.tensor(pair_indices, dtype=torch.long)
        output["is_chosen"] = torch.tensor(is_chosen, dtype=torch.bool)
        if has_reference:
            output["reference_logps"] = torch.tensor(reference_logps, dtype=torch.float32)
        return output
