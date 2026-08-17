#!/usr/bin/env python3
"""veRL SFT dataset adapter for the strict Qwen3.6 chat template."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import Dataset


class SFTDataError(ValueError):
    """Raised when a row cannot satisfy the CreateMyCard SFT contract."""


def normalize_input_ids(tokenized: Any) -> list[int]:
    """Normalize a tokenizer chat-template result to one list of token IDs."""
    if isinstance(tokenized, Mapping):
        tokenized = tokenized.get("input_ids")
    if hasattr(tokenized, "tolist"):
        tokenized = tokenized.tolist()
    if tokenized and isinstance(tokenized[0], list):
        if len(tokenized) != 1:
            raise SFTDataError("chat template unexpectedly returned a batch")
        tokenized = tokenized[0]
    if not isinstance(tokenized, list) or not all(isinstance(value, int) for value in tokenized):
        raise SFTDataError(
            f"chat template returned unsupported input_ids type: {type(tokenized).__name__}"
        )
    return tokenized


def validate_messages(messages: Any, sample_id: str) -> list[dict[str, str]]:
    """Validate the text-only, single-turn conversation used by this task."""
    if not isinstance(messages, list):
        raise SFTDataError(f"{sample_id}: messages must be a list")

    roles = [message.get("role") if isinstance(message, dict) else None for message in messages]
    if roles not in (["user", "assistant"], ["system", "user", "assistant"]):
        raise SFTDataError(
            f"{sample_id}: roles must be user/assistant or system/user/assistant, got {roles}"
        )

    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            raise SFTDataError(f"{sample_id}: message {index} must be an object")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise SFTDataError(f"{sample_id}: {message.get('role')} content is empty")

    assistant = messages[-1]["content"].lower()
    if "<think>" in assistant or "</think>" in assistant:
        raise SFTDataError(f"{sample_id}: assistant label contains <think> tags")
    return messages


def apply_template(tokenizer: Any, messages: list[dict[str, str]], *, generation: bool) -> list[int]:
    """Apply Qwen3.6's template to a complete conversation, never to one message."""
    tokenized = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=generation,
        enable_thinking=False,
    )
    return normalize_input_ids(tokenized)


def encode_sft_example(
    tokenizer: Any,
    messages: Any,
    *,
    sample_id: str,
    max_length: int,
) -> dict[str, torch.Tensor]:
    """Encode one full conversation and build an assistant-only loss mask."""
    validated = validate_messages(messages, sample_id)
    prompt_ids = apply_template(tokenizer, validated[:-1], generation=True)
    full_ids = apply_template(tokenizer, validated, generation=False)

    if full_ids[: len(prompt_ids)] != prompt_ids:
        raise SFTDataError(
            f"{sample_id}: training sequence does not start with the non-thinking inference prompt"
        )
    if len(full_ids) > max_length:
        raise SFTDataError(
            f"{sample_id}: sequence_length={len(full_ids)} is larger than max_length={max_length}"
        )

    assistant_length = len(full_ids) - len(prompt_ids)
    if assistant_length <= 0:
        raise SFTDataError(f"{sample_id}: assistant has no trainable tokens")

    input_ids = torch.tensor(full_ids, dtype=torch.long)
    loss_mask = torch.zeros(len(full_ids), dtype=torch.long)
    loss_mask[len(prompt_ids) :] = 1
    return {
        "input_ids": input_ids,
        "position_ids": torch.arange(len(full_ids), dtype=torch.long),
        "loss_mask": loss_mask,
    }


class CreateMyCardSFTDataset(Dataset):
    """Text-only Qwen3.6 dataset loaded through veRL's ``data.custom_cls`` hook."""

    def __init__(
        self,
        parquet_files: str | Sequence[str],
        tokenizer: Any,
        config: Any,
        processor: Any = None,
        max_samples: int = -1,
    ) -> None:
        del processor  # Qwen3.6 text conversations must use the tokenizer chat template.
        self.tokenizer = tokenizer
        self.max_length = int(config.get("max_length", 1024))
        self.messages_key = str(config.get("messages_key", "messages"))
        self.enable_thinking_key = str(config.get("enable_thinking_key", "enable_thinking"))

        pad_mode = str(config.get("pad_mode", "no_padding"))
        truncation = str(config.get("truncation", "error"))
        if pad_mode != "no_padding":
            raise SFTDataError(f"CreateMyCardSFTDataset requires pad_mode=no_padding, got {pad_mode}")
        if truncation != "error":
            raise SFTDataError(f"CreateMyCardSFTDataset requires truncation=error, got {truncation}")
        if self.max_length <= 0:
            raise SFTDataError(f"max_length must be positive, got {self.max_length}")

        paths = [parquet_files] if isinstance(parquet_files, str) else list(parquet_files)
        if not paths:
            raise SFTDataError("at least one parquet file is required")
        self.rows = self._read_rows([Path(path) for path in paths])
        if 0 < max_samples < len(self.rows):
            self.rows = self.rows[:max_samples]
        if not self.rows:
            raise SFTDataError("dataset is empty")
        print(f"CreateMyCardSFTDataset len: {len(self.rows)}")

    def _read_rows(self, paths: list[Path]) -> list[dict[str, Any]]:
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError("pyarrow is required to load the SFT dataset") from exc

        required = {"id", self.messages_key, self.enable_thinking_key}
        rows: list[dict[str, Any]] = []
        for path in paths:
            if not path.is_file():
                raise FileNotFoundError(f"parquet file does not exist: {path}")
            table = pq.read_table(path)
            missing = required - set(table.column_names)
            if missing:
                raise SFTDataError(f"{path} is missing columns: {sorted(missing)}")
            rows.extend(table.to_pylist())
        return rows

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, item: int) -> dict[str, torch.Tensor]:
        row = self.rows[item]
        sample_id = row.get("id")
        if not isinstance(sample_id, str) or not sample_id:
            raise SFTDataError(f"row {item}: id must be a non-empty string")
        if row.get(self.enable_thinking_key) is not False:
            raise SFTDataError(f"{sample_id}: {self.enable_thinking_key} must be false")
        return encode_sft_example(
            self.tokenizer,
            row.get(self.messages_key),
            sample_id=sample_id,
            max_length=self.max_length,
        )
