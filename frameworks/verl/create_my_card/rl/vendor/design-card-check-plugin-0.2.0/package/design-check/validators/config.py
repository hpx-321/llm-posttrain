"""Workspace 路径约定（支持环境变量覆盖，不硬编码用户名/绝对路径）。

- 工作区根 = ``design-check/`` 的父目录（即 Design-guide，已并入宿主仓库）；
- 规范金标准（2026-08-22 登记）固定在工作区根：``DESIGN.md``（2×2）+ ``DESIGN-2x4.md``（2×4），
  与外层宿主仓库 ``docs/system_prompt.txt`` 解耦，后者不是检查器真值；
- 渲染管线位于宿主 CreateMyCard 仓库（默认外层目录，``PIPELINE_DIR`` 可覆盖）；
- ``卡片…/`` 是外部输入。
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

#: 工程目录（含 validators/ scripts/ …）
PROJECT_DIR = Path(__file__).resolve().parent.parent
#: 工作区根目录（含 DESIGN.md / DESIGN-2x4.md 两份金标准与卡片数据集）
WORKSPACE = PROJECT_DIR.parent


def design_spec_path() -> Path:
    """2×2 卡规范金标准（front-matter token + 正文规则的机器可读源）。"""
    return Path(os.environ.get("DESIGN_SPEC", WORKSPACE / "DESIGN.md"))


def design_2x4_spec_path() -> Path:
    """2×4 卡规范金标准（front-matter 含 layout_slots 布局契约；B6 类规则消费）。"""
    return Path(os.environ.get("DESIGN_2X4_SPEC", WORKSPACE / "DESIGN-2x4.md"))


def pipeline_dir() -> Path:
    override = os.environ.get("PIPELINE_DIR")
    if override:
        return Path(override)
    local = WORKSPACE / "CreateMyCard"
    if local.is_dir():
        return local
    # 工作区并入宿主仓库后不再内置副本：默认回退到外层 CreateMyCard 仓库根。
    return WORKSPACE.parent


def render_bridge_path() -> Path:
    return pipeline_dir() / "scripts" / "preview" / "render_dsl.py"


def render_batch_path() -> Path:
    return pipeline_dir() / "scripts" / "preview" / "render_batch_trio.py"


def card_data_dir() -> Path:
    override = os.environ.get("CARD_DATA_DIR")
    if override:
        return Path(override)
    for child in sorted(WORKSPACE.iterdir()):
        if child.is_dir() and child.name.startswith("卡片"):
            return child
    raise FileNotFoundError(f"工作区 {WORKSPACE} 下找不到以「卡片」开头的卡片数据目录。")


def review_dir() -> Path:
    return PROJECT_DIR / "review"


def daily_review_dir(date_str: Optional[str] = None) -> Path:
    """带日期报告产物目录 review/<YYYYMMDD>/（缺省=当天；mkdir parents exist_ok）。

    2026-08-24 起按 AGENTS.md 汇报规范：带日期报告（文件名含 -YYYYMMDD 或
    acceptance/dsh 的 2026-08-2x 形态）统一落该目录；dump/wireframe/pipeline/
    vis-assets 等非日期真值与资产目录仍用 review_dir() 原位。
    """
    stamp = date_str or datetime.now().strftime("%Y%m%d")
    d = review_dir() / stamp
    d.mkdir(parents=True, exist_ok=True)
    return d


def eval_root() -> Path:
    """第一次评测数据根目录（四分支 DSL，只读引用）。"""
    override = os.environ.get("EVAL_DIR")
    if override:
        return Path(override)
    candidate = WORKSPACE / "第一次评测"
    if candidate.is_dir():
        return candidate
    raise FileNotFoundError(f"评测数据目录不存在: {candidate}（可用 EVAL_DIR 指定）")


def prompts_dir() -> Path:
    return PROJECT_DIR / "prompts"
