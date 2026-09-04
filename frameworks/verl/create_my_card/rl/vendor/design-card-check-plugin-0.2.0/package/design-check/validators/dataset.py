"""卡片数据目录索引（拍平为 case 清单）。"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

from .config import card_data_dir, review_dir
from .dsl import CASE_FILES, CardParseError

QID_RE = re.compile(r"^q(\d{3})$")


@dataclass
class CaseEntry:
    case_id: str
    query_path: Path
    spec_path: Path
    dsl_path: Path
    size: str = "2x2"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "query": str(self.query_path),
            "task_spec": str(self.spec_path),
            "card_dsl": str(self.dsl_path),
            "size": self.size,
        }


@dataclass
class DatasetManifest:
    root: Path
    entries: List[CaseEntry] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.entries)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root": str(self.root),
            "count": self.count,
            "skipped": self.skipped,
            "cases": [e.to_dict() for e in self.entries],
        }


def discover_case_dirs(root: Path) -> List[Path]:
    dirs = [c for c in Path(root).iterdir() if c.is_dir() and QID_RE.match(c.name)]
    dirs.sort(key=lambda p: int(p.name[1:]))
    return dirs


def scan_dataset(root: Path) -> DatasetManifest:
    root = Path(root)
    if not root.is_dir():
        raise CardParseError(f"卡片数据目录不存在: {root}")
    manifest = DatasetManifest(root=root)
    for case_dir in discover_case_dirs(root):
        has = {f: (case_dir / f).is_file() for f in CASE_FILES}
        if not all(has.values()):
            missing = ", ".join(f for f, ok in has.items() if not ok)
            manifest.skipped.append(f"{case_dir.name} (缺 {missing})")
            continue
        size = "2x2"
        try:
            with open(case_dir / "task-spec.json", encoding="utf-8-sig") as fh:
                size = str(json.load(fh).get("size", "2x2"))
        except Exception:
            pass
        manifest.entries.append(
            CaseEntry(
                case_id=case_dir.name,
                query_path=case_dir / "query.txt",
                spec_path=case_dir / "task-spec.json",
                dsl_path=case_dir / "card.genui.jsonl",
                size=size,
            )
        )
    return manifest


def write_manifest(manifest: DatasetManifest, target: Path) -> Path:
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(target)
    return target


def load_manifest() -> DatasetManifest:
    """生成并落盘数据集清单（写到 review/dataset-manifest.json）。"""
    manifest = scan_dataset(card_data_dir())
    write_manifest(manifest, review_dir() / "dataset-manifest.json")
    return manifest


def render_evidence_layout_path(case_id: str) -> Path:
    """返回数据集 render-evidence 的 full-layout.json（离线 dump 真值）。"""
    return card_data_dir() / "render-run" / "output" / "render-evidence" / case_id / "full-layout.json"


def render_evidence_png_path(case_id: str) -> Path:
    """返回数据集 render-run/output 下的卡片 PNG（若存在）。"""
    return card_data_dir() / "render-run" / "output" / f"{case_id}.png"
