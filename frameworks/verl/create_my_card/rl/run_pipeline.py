#!/usr/bin/env python3
"""Convenience entry point for ``pipeline.cli`` from any working directory."""

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from frameworks.verl.create_my_card.rl.pipeline.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
