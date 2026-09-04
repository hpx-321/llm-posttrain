#!/usr/bin/env python3
"""L2 真值层工序——DumpLayout 通道 B（goal docs/goal-dsh-design-check-plugin.md §2.3 / Phase 3）。

工序序列（每 case）：
    转换 DSL（convert_genui_ops）→ CreateMyCard 渲染桥（装/启动/截图，invoke_render_batch）
    → aa start 重拉卡片 → uitest dumpLayout → file recv → review/dumps/<qid>.layout.json
产物可直接被 ``check_card.py --layout`` 消费；通道 A（外部 dump 文件直传）行为不变。

前置校验（显式报错：缺什么、怎么补，含路径与退出码）：
- Automation-screenshot 根目录（``--automation-root`` / env ``AUTOMATION_SCREENSHOT_ROOT``，
  缺省 ``~/Downloads/Automation-screenshot``）；
- ``hdc`` 可执行（PATH 或 ``--hdc``）；
- 设备 targets 非空（``--sn`` 指定或自动取第一台）。

无设备时用 ``--dry-run`` 显式降级：只转换 DSL，manifest 标注 ``degraded``，退出码 0；
不得假装已渲染。

用法：
    python3 scripts/render_dump.py --cases q010 --dry-run
    python3 scripts/render_dump.py --cases q010 --sn 127.0.0.1:5555
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validators.config import review_dir  # noqa: E402
from validators.dataset import load_manifest  # noqa: E402
from validators.dsl import load_case  # noqa: E402
from validators.render_bridge import (  # noqa: E402
    RENDER_OUT,
    convert_genui_ops,
    invoke_render_batch,
)

DUMP_OUT = review_dir() / "dumps"
REMOTE_DUMP_DIR = "/data/local/tmp"
#: 与 Automation-screenshot/automation/config.py 默认一致（A2UI_Render 工程）
DEFAULT_BUNDLE = "com.example.myapplication"
DEFAULT_ABILITY = "EntryAbility"
DEFAULT_MODULE = "entry"
RELAUNCH_WAIT_SECONDS = 2.0


def resolve_automation_root(override: str | None) -> Path:
    if override:
        return Path(override)
    env = os.environ.get("AUTOMATION_SCREENSHOT_ROOT")
    if env:
        return Path(env)
    return Path.home() / "Downloads" / "Automation-screenshot"


def preflight(automation_root: Path, hdc_exec: str, sn: str | None) -> list[str]:
    """返回阻断问题清单（空 = 可执行真工序）。"""
    problems: list[str] = []
    if not automation_root.is_dir():
        problems.append(
            f"Automation-screenshot 根目录不存在: {automation_root}\n"
            f"  补救: 用 --automation-root <path> 或设置 AUTOMATION_SCREENSHOT_ROOT"
        )
    elif not (automation_root / "Automation" / "automation" / "hdc.py").is_file():
        problems.append(
            f"Automation 包缺失: {automation_root / 'Automation' / 'automation' / 'hdc.py'}\n"
            f"  补救: 确认 Automation-screenshot 仓库结构完整"
        )
    if shutil.which(hdc_exec) is None:
        problems.append(
            f"hdc 可执行文件不在 PATH: {hdc_exec}\n"
            f"  补救: 启动 DevEco Studio 模拟器并把 toolchains/hdc 加入 PATH，或用 --hdc <path>；"
            f"无设备时可改用 --dry-run（降级）或 check_card.py --layout <外部dump>（通道 A）"
        )
        return problems  # hdc 都没有，targets 检查无意义
    try:
        proc = subprocess.run([hdc_exec, "list", "targets"], capture_output=True, text=True, timeout=15)
        targets = [l.split()[0] for l in (proc.stdout or "").splitlines()
                   if l.strip() and "empty" not in l.lower() and "list of" not in l.lower()]
    except (subprocess.SubprocessError, OSError) as exc:
        problems.append(f"hdc list targets 执行失败: {exc!r}\n  补救: 确认 hdc 可用后重试")
        return problems
    if not targets:
        problems.append(
            "hdc list targets 为空（无已连接设备/模拟器）\n"
            "  补救: 启动 DevEco 模拟器后重试；无设备可改用 --dry-run（降级）或通道 A 外部 dump"
        )
    elif sn and sn not in targets:
        problems.append(f"--sn {sn} 不在设备列表 {targets}")
    return problems


def import_hdc_client(automation_root: Path):
    """从 Automation-screenshot 导入 HdcClient（dump_layout 封装）。"""
    automation_dir = automation_root / "Automation"
    sys.path.insert(0, str(automation_dir))
    try:
        from automation.hdc import HdcClient  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            f"无法导入 Automation 的 HdcClient（搜索路径 {automation_dir}）: {exc!r}\n"
            f"  补救: 确认 Automation-screenshot 仓库完整"
        ) from exc
    return HdcClient


def dump_case(hdc, case_id: str, *, bundle: str, ability: str, module: str,
              wait: float = RELAUNCH_WAIT_SECONDS) -> Path:
    """aa start 重拉卡片 → uitest dumpLayout → file recv → review/dumps/<qid>.layout.json。"""
    hdc.shell("aa", "force-stop", bundle, timeout=30, check=False)
    hdc.shell("aa", "start", "-a", ability, "-b", bundle, "-m", module, timeout=30)
    time.sleep(wait)
    local = DUMP_OUT / f"{case_id}.layout.json"
    remote = f"{REMOTE_DUMP_DIR}/{case_id}.layout.json"
    return hdc.dump_layout(local, remote)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="L2 真值层工序（render + screenshot + dumpLayout 通道 B）")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--cases", default=None, help="逗号分隔 case 白名单")
    group.add_argument("--all", action="store_true", help="全部 case")
    parser.add_argument("--dry-run", action="store_true", help="只转换 DSL，不渲染/不 dump（无设备降级路径）")
    parser.add_argument("--sn", default=None, help="设备 SN（透传给渲染桥与 hdc）")
    parser.add_argument("--automation-root", default=None, help="Automation-screenshot 根目录（默认 ~/Downloads 或 env）")
    parser.add_argument("--hdc", default="hdc", help="hdc 可执行文件路径")
    parser.add_argument("--bundle", default=DEFAULT_BUNDLE, help="重拉的 bundle 名")
    parser.add_argument("--ability", default=DEFAULT_ABILITY, help="重拉的 ability 名")
    parser.add_argument("--module", default=DEFAULT_MODULE, help="重拉的 module 名")
    parser.add_argument("--out", default=None, help="渲染状态 JSON")
    args = parser.parse_args(argv)

    manifest = load_manifest()
    entries = manifest.entries if args.all else []
    if args.cases:
        wanted = set(args.cases.split(","))
        missing = sorted(wanted - {e.case_id for e in manifest.entries})
        if missing:
            print(f"错误: 未知 case {', '.join(missing)}", file=sys.stderr)
            return 2
        entries = [e for e in manifest.entries if e.case_id in wanted]
    if not entries:
        print("没有可渲染的 case", file=sys.stderr)
        return 1

    RENDER_OUT.mkdir(parents=True, exist_ok=True)
    DUMP_OUT.mkdir(parents=True, exist_ok=True)
    results = []

    if args.dry_run:
        print(f"--dry-run 降级：仅转换 {len(entries)} 个 case，不渲染/不 dump。")
        print("  需要真值 dump 时：启动 DevEco 模拟器 + hdc 后去掉 --dry-run，或走通道 A（check_card.py --layout <外部dump>）。")
        for e in entries:
            card = load_case(e.query_path.parent)
            converted = convert_genui_ops(card, review_dir() / "converted", stem=e.case_id)
            results.append({"case_id": e.case_id, "converted": str(converted),
                            "rendered": False, "dumped": False, "degraded": True,
                            "degraded_reason": "dry-run: no device pipeline"})
    else:
        automation_root = resolve_automation_root(args.automation_root)
        problems = preflight(automation_root, args.hdc, args.sn)
        if problems:
            print("前置校验未通过，无法执行真工序：", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 2

        exit_code = invoke_render_batch(
            [e.case_id for e in entries],
            sn=args.sn,
            automation_root=automation_root,
        )
        if exit_code != 0:
            print(f"渲染返回非零 {exit_code}；请检查模拟器/工程路径（automation_root={automation_root}）。", file=sys.stderr)
            return exit_code

        HdcClient = import_hdc_client(automation_root)
        hdc = HdcClient(sn=args.sn or None)
        for e in entries:
            try:
                dump_path = dump_case(hdc, e.case_id, bundle=args.bundle,
                                      ability=args.ability, module=args.module)
                results.append({"case_id": e.case_id, "rendered": True, "dumped": True,
                                "dump_path": str(dump_path), "degraded": False})
                print(f"dump 完成: {dump_path}")
            except Exception as exc:  # 单卡 dump 失败不终止整批
                results.append({"case_id": e.case_id, "rendered": True, "dumped": False,
                                "degraded": False, "error": repr(exc)})
                print(f"dump 失败 {e.case_id}: {exc!r}", file=sys.stderr)

    out_target = Path(args.out) if args.out else RENDER_OUT / "manifest.json"
    out_target.parent.mkdir(parents=True, exist_ok=True)
    out_target.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"渲染状态写入: {out_target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
