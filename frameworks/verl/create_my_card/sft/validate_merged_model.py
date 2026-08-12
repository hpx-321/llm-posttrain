#!/usr/bin/env python3
"""Validate that a merged checkpoint is a loadable non-thinking Hugging Face model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-path", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model_path = args.model_path
    if not model_path.is_dir():
        raise FileNotFoundError(f"merged model directory does not exist: {model_path}")
    if not (model_path / "config.json").is_file():
        raise FileNotFoundError(f"missing model config: {model_path / 'config.json'}")

    weights = sorted(model_path.glob("*.safetensors"))
    weights.extend(sorted(model_path.glob("pytorch_model*.bin")))
    if not weights:
        raise FileNotFoundError(f"no Hugging Face weight files found in {model_path}")

    from transformers import AutoConfig, AutoTokenizer

    config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    prompt = tokenizer.apply_chat_template(
        [
            {"role": "system", "content": "Return only the answer."},
            {"role": "user", "content": "test"},
        ],
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    empty_think = "<think>\n\n</think>\n\n"
    if empty_think not in prompt:
        raise RuntimeError("non-thinking chat template did not add the expected empty think block")

    report = {
        "modelPath": str(model_path.resolve()),
        "modelType": getattr(config, "model_type", None),
        "architectures": getattr(config, "architectures", None),
        "weightFiles": len(weights),
        "chatTemplate": True,
        "nonThinkingPrefix": True,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("Merged Hugging Face model validation passed.")


if __name__ == "__main__":
    main()
