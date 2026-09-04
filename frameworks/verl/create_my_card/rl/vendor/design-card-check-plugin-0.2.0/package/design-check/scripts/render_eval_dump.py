#!/usr/bin/env python3
"""L2 真值层工序——对任意裸 DSL（如第一次评测分支卡）逐卡「渲染 + dumpLayout」。

背景：scripts/render_dump.py 的通道 B 骨架按 93 条集 manifest 设计，其
invoke_render_batch 与外层 render_batch_trio.py 的批次目录接口不对齐（端到端
一直是「待端侧验证」）。本脚本走正牌链路完成端到端：

    三件套转换（render_batch_trio.py，产出带 __viewport__ 的 dsl）
    → Automation arkts.render（rawfile 注入 → hvigor 构建 → 安装 → 启动 → 截图）
    → 紧接 hdc.dump_layout（uitest dumpLayout → recv）
    → review/dumps/<qid>.layout.json + 全屏截图路径

为什么逐卡重建：应用从 rawfile 读 DSL，一次构建只显示一张卡；dump 必须紧跟
该卡的 render（与 few_shot A 系管线同口径）。

前置：DevEco 模拟器已启动、hdc 可连设备、Automation-screenshot 仓库完整
（环境路径读 Automation/config/automation.json，不硬编码）。

用法：
    python3 scripts/render_eval_dump.py \
        --items b-q1=review/renders/b-eval-work/dsl/beval_q001.jsonl,b-q4=...,b-q7=... \
        [--sn 127.0.0.1:5555] [--automation-root ~/Downloads/Automation-screenshot]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from device_utils import load_hdc_path, read_automation_json  # noqa: E402
from validators.config import review_dir  # noqa: E402

DUMP_OUT = review_dir() / "dumps"


def load_automation_config(automation_root: Path, sn: str | None):
    """按 Automation/config/automation.json 构造 AutomationConfig（剥离 // 注释）。

    hdc 绝对路径读取抽到 device_utils.load_hdc_path（本模块与 check_case 共用）。
    """
    sys.path.insert(0, str(automation_root / "Automation"))
    from automation.config import AutomationConfig

    cfg = read_automation_json(automation_root)

    def p(key: str) -> Path | None:
        v = cfg.get(key)
        return Path(v) if v else None

    return AutomationConfig(
        project_root=automation_root,
        sn=sn,
        artifact_namespace="design-check",
        hdc=load_hdc_path(automation_root),
        deveco_sdk_home=p("deveco_sdk_home"),
        java_home=p("java_home"),
        hvigor_executable=p("hvigor_executable"),
    )


def render_and_dump(items: list[tuple[str, Path]], sn: str | None,
                    automation_root: Path) -> list[dict]:
    """逐卡「render + dumpLayout」，返回 results 列表（每项含 qid/rendered/dumped…）。

    items: (qid, 转换后 dsl 路径) 列表（dsl 须带 __viewport__ 元数据）。
    前置校验失败 → 抛 RuntimeError（含逐条问题）；单卡 dump 失败不终止整批
    （results 内标注 error）。dump 质量守卫不在本层（由调用方在返回后核验）。
    """
    automation_root = Path(automation_root)
    # 环境路径先于校验加载：hdc 绝对路径来自 automation.json（PATH 里通常没有 hdc）
    config = load_automation_config(automation_root, sn)

    # 前置校验复用 render_dump.preflight（hdc/设备/仓库结构，显式报错）
    from render_dump import preflight  # noqa: E402

    problems = preflight(automation_root, config.hdc, sn)
    if problems:
        raise RuntimeError("前置校验未通过:\n  - " + "\n  - ".join(problems))

    from automation.pipeline import AutomationPipeline  # noqa: E402

    pipeline = AutomationPipeline(config, None)
    DUMP_OUT.mkdir(parents=True, exist_ok=True)
    results = []
    for qid, dsl_path in items:
        print(f"=== {qid}: render（构建+安装+启动+截图）…", flush=True)
        try:
            screenshot = pipeline.arkts.render(qid, dsl_path)
        except Exception as exc:
            print(f"  render 失败 {qid}: {exc!r}", file=sys.stderr)
            results.append({"qid": qid, "rendered": False, "error": repr(exc)})
            continue
        try:
            local = DUMP_OUT / f"{qid}.layout.json"
            dump_path = pipeline.hdc.dump_layout(local, f"/data/local/tmp/{qid}.layout.json")
            print(f"  dump: {dump_path}")
            print(f"  截图: {screenshot}")
            results.append({"qid": qid, "rendered": True, "dumped": True,
                            "dump_path": str(dump_path), "screenshot": str(screenshot)})
        except Exception as exc:
            results.append({"qid": qid, "rendered": True, "dumped": False, "error": repr(exc)})
            print(f"  dump 失败 {qid}: {exc!r}", file=sys.stderr)
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="逐卡渲染 + dumpLayout（任意裸 DSL）")
    parser.add_argument("--items", required=True,
                        help="逗号分隔的 qid=转换后dsl路径 列表（dsl 须带 __viewport__ 元数据）")
    parser.add_argument("--sn", default=None, help="设备 SN（缺省取第一台）")
    parser.add_argument("--automation-root", default=None,
                        help="Automation-screenshot 根目录（默认 ~/Downloads/Automation-screenshot）")
    args = parser.parse_args(argv)

    automation_root = Path(args.automation_root or Path.home() / "Downloads" / "Automation-screenshot")
    items: list[tuple[str, Path]] = []
    for chunk in args.items.split(","):
        qid, _, path = chunk.partition("=")
        if not qid or not path:
            print(f"错误: --items 格式应为 qid=path，收到 {chunk!r}", file=sys.stderr)
            return 2
        p = Path(path)
        if not p.is_file():
            print(f"错误: DSL 文件不存在 {p.resolve()}", file=sys.stderr)
            return 2
        items.append((qid.strip(), p))

    # 环境路径先于校验加载：hdc 绝对路径来自 automation.json（PATH 里通常没有 hdc）
    try:
        results = render_and_dump(items, args.sn, automation_root)
    except RuntimeError as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2

    manifest = review_dir() / "renders" / "eval-dump-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"渲染状态写入: {manifest}")
    return 0 if all(r.get("dumped") for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
