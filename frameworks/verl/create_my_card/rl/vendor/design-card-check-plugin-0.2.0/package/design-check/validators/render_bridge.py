"""预览/渲染管线桥接（吸收 ``CreateMyCard/scripts/preview/`` 的转换与渲染）。

转换层仅标准库；调用外部渲染需要模拟器/``Automation-screenshot``，无设备时应以
``--dry-run`` 或纯 DSL 检查优雅降级。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import render_batch_path, render_bridge_path, review_dir
from .dsl import GENUI_OPS, GenuiCard, load_case

VIEWPORT_META_KEY = "__viewport__"
VALID_SIZES = ("2x2", "2x4")
RENDER_OUT = review_dir() / "renders"


def _op_of(record: Dict[str, Any]) -> Optional[str]:
    for op in GENUI_OPS:
        if op in record:
            return op
    return None


def convert_genui_ops(card: GenuiCard, out_dir: Path, stem: Optional[str] = None) -> Path:
    """抽出三条 genui message + 视口元数据，写成 ``<stem>.jsonl``。"""
    by_op: Dict[str, Dict[str, Any]] = {}
    for record in (card.create_surface, card.update_components, card.update_data_model):
        record = record or {}
        op = _op_of(record)
        if op:
            by_op[op] = record
    ordered = [by_op[op] for op in GENUI_OPS if op in by_op]
    if not ordered:
        raise ValueError(f"{card.case_id}: 没有任何 genui message 可转换")
    viewport = card.size if card.size in VALID_SIZES else "2x2"
    out_records: List[Dict[str, Any]] = [{VIEWPORT_META_KEY: viewport}, *ordered]
    target = Path(out_dir) / f"{stem or card.case_id}.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out_records, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def bridge_available() -> bool:
    return render_bridge_path().is_file()


def invoke_render_dsl(inputs, *, dry_run: bool = False, sn: Optional[str] = None,
                      automation_root: Optional[Path] = None, enable_card_crop: bool = False) -> int:
    """调用 CreateMyCard 的 ``render_dsl.py``（单文件/目录渲染桥）。"""
    bridge = render_bridge_path()
    if not bridge.is_file():
        raise FileNotFoundError(f"预览渲染桥接脚本不存在: {bridge}")
    if isinstance(inputs, (str, Path)):
        inputs = [inputs]
    cmd = [sys.executable, str(bridge), *(str(i) for i in inputs)]
    if automation_root is not None:
        cmd += ["--automation-root", str(automation_root)]
    if sn:
        cmd += ["--sn", sn]
    if enable_card_crop:
        cmd += ["--enable-card-crop"]
    if dry_run:
        cmd += ["--dry-run"]
    print("执行：", " ".join(cmd))
    return subprocess.call(cmd)


def invoke_render_batch(case_ids, *, dry_run: bool = False, sn: Optional[str] = None,
                        automation_root: Optional[Path] = None) -> int:
    """调用 CreateMyCard 的 ``render_batch_trio.py``（批量三连渲染，Phase 2 主营）。"""
    script = render_batch_path()
    if not script.is_file():
        raise FileNotFoundError(f"批量渲染脚本不存在: {script}")
    cmd = [sys.executable, str(script)]
    if case_ids:
        cmd += sorted(str(c) for c in case_ids)
    if automation_root is not None:
        cmd += ["--automation-root", str(automation_root)]
    if sn:
        cmd += ["--sn", sn]
    if dry_run:
        cmd += ["--dry-run"]
    print("执行：", " ".join(cmd))
    return subprocess.call(cmd)


def render_case(case_dir, *, dry_run: bool = False, invoke: bool = True, sn: Optional[str] = None) -> Dict[str, Any]:
    """渲染单个 case：先本地转换，再（可选）调用外部渲染。"""
    card = load_case(Path(case_dir))
    jsonl = convert_genui_ops(card, review_dir() / "converted", stem=card.case_id)
    result = {
        "case_id": card.case_id,
        "converted": str(jsonl),
        "size": card.size,
        "rendered": False,
        "exit_code": 0,
    }
    if invoke and not dry_run:
        if not bridge_available():
            raise FileNotFoundError(f"预览渲染管线不可用（{render_bridge_path()} 不存在）")
        result["exit_code"] = invoke_render_dsl(jsonl, sn=sn)
        result["rendered"] = result["exit_code"] == 0
    return result
