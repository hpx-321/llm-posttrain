#!/usr/bin/env python3
"""设备前置与自恢复（WP-PIPE 单一口径，2026-08-22）。

背景（docs/plan.md 2026-08-22「L2 真值通道 B 端到端」遗留）：模拟器进程会中途退出、
``hdc list targets`` 清空，此前需手工重启（Emulator -start，~25s 起）+ ``hdc tconn
127.0.0.1:5555``。本模块把「探测 → 恢复 → 轮询」固化为 ``ensure_device``，并把
hdc 绝对路径读取（Automation/config/automation.json）抽到 ``load_hdc_path`` 供
render_eval_dump 复用。

职责边界：只做设备可达性，不渲染、不 dump。dump 质量守卫（bundle 存在性）见
``verify_dump_has_bundle``（纯函数，配单测）。

依据：AGENTS.md「调用外部渲染需要…本地模拟器；无设备时以 --dry-run / 纯 DSL 检查
降级」；开发计划 v2.1 M-A 工序序列；2026-08-22 试跑问题 2。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

#: 本机模拟器默认实例（可用环境变量覆盖，不硬编码用户名/工作区路径）
DEFAULT_EMULATOR_BIN = "/Applications/DevEco-Studio.app/Contents/tools/emulator/Emulator"
DEFAULT_EMULATOR_NAME = "Pura 90"
DEFAULT_TCONN_ADDR = "127.0.0.1:5555"
#: 模拟器启动后轮询 hdc targets 的最长等待（秒）
ENSURE_POLL_SECONDS = 150
POLL_INTERVAL_SECONDS = 3.0

#: 与 Automation-screenshot 默认渲染工程一致的 bundle（dump 守卫用）
DEFAULT_BUNDLE = "com.example.myapplication"


def emulator_bin() -> str:
    return os.environ.get("DESIGNCHECK_EMULATOR_BIN", DEFAULT_EMULATOR_BIN)


def emulator_name() -> str:
    return os.environ.get("DESIGNCHECK_EMULATOR_NAME", DEFAULT_EMULATOR_NAME)


def read_automation_json(automation_root: Path) -> dict:
    """读 Automation/config/automation.json 的 automation 节（剥离 // 注释）。

    抽自 render_eval_dump.load_automation_config 的 JSON 读取逻辑，供本模块与
    render_eval_dump 共用；路径不存在/解析失败显式报错（含可定位路径）。
    """
    cfg_path = automation_root / "Automation" / "config" / "automation.json"
    if not cfg_path.is_file():
        raise FileNotFoundError(
            f"Automation 配置文件不存在: {cfg_path}\n"
            f"  补救: 确认 Automation-screenshot 仓库完整（automation_root={automation_root}）"
        )
    raw = cfg_path.read_text(encoding="utf-8")
    clean = re.sub(r"^\s*//.*$", "", raw, flags=re.M)
    try:
        cfg = json.loads(clean)["automation"]
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RuntimeError(f"解析 Automation 配置失败 {cfg_path}: {exc!r}") from exc
    return cfg


def load_hdc_path(automation_root: Path) -> str:
    """hdc 绝对路径（automation.json 的 hdc 键；缺省回退 'hdc' 走 PATH）。"""
    return str(read_automation_json(automation_root).get("hdc") or "hdc")


def list_targets(hdc_path: str, timeout: float = 15.0) -> list[str]:
    """hdc list targets → 设备 sn 列表（空 = 无已连接设备）。"""
    proc = subprocess.run([hdc_path, "list", "targets"], capture_output=True,
                          text=True, timeout=timeout)
    out = proc.stdout or ""
    return [line.split()[0] for line in out.splitlines()
            if line.strip() and "empty" not in line.lower()
            and "list of" not in line.lower()]


def _tconn(hdc_path: str, addr: str) -> None:
    subprocess.run([hdc_path, "tconn", addr], capture_output=True,
                   text=True, timeout=30)


def _emulator_running() -> bool:
    try:
        proc = subprocess.run(["pgrep", "-f", "Emulator"], capture_output=True,
                              text=True, timeout=15)
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"  检测模拟器进程失败（pgrep）: {exc!r}，按未启动处理", file=sys.stderr)
        return False
    return proc.returncode == 0 and bool((proc.stdout or "").strip())


def _start_emulator() -> None:
    """后台启动 DevEco 模拟器（不阻塞；起 ~25s，随后由轮询确认）。"""
    cmd = [emulator_bin(), "-start", emulator_name()]
    print(f"  模拟器未运行，启动: {' '.join(cmd)}")
    try:
        # 模拟器是长驻 GUI 进程：detach，不等待退出
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except OSError as exc:
        raise RuntimeError(
            f"启动模拟器失败: {exc!r}（二进制 {emulator_bin()}）\n"
            f"  补救: 确认 DevEco Studio 已安装，或用 DESIGNCHECK_EMULATOR_BIN 指定模拟器二进制"
        ) from exc


def ensure_device(hdc_path: str, sn: str | None) -> str:
    """保证 hdc 有一台可用设备，返回其 sn。

    恢复序列（每步动作打印）：
      1. ``hdc list targets`` 已有目标 → 直接返回（sn 指定时须在列）；
      2. 空 → ``hdc tconn 127.0.0.1:5555``（本地模拟器 TCP 重连）；
      3. 仍空 → 检查模拟器进程（pgrep Emulator），不在则启动
         （DESIGNCHECK_EMULATOR_BIN + DESIGNCHECK_EMULATOR_NAME）；
      4. 轮询 ``hdc list targets`` 最长 {ENSURE_POLL_SECONDS}s。
    全部失败 → RuntimeError（含 hdc 路径与补救建议），由调用方显式报错退出。
    """
    if not Path(hdc_path).is_absolute() or not Path(hdc_path).exists():
        raise RuntimeError(
            f"hdc 可执行文件不可用: {hdc_path}\n"
            f"  补救: 在 Automation/config/automation.json 配置 hdc 绝对路径，"
            f"或把 hdc 加入 PATH 后重试"
        )

    def pick(targets: list[str]) -> str | None:
        if not targets:
            return None
        if sn and sn in targets:
            return sn
        if not sn:
            return targets[0]
        return None  # sn 指定但不在列 → 走恢复

    targets = list_targets(hdc_path)
    chosen = pick(targets)
    if chosen:
        print(f"设备就绪: {chosen}（targets={targets}）")
        return chosen
    if sn:
        print(f"hdc list targets={targets} 不含 --sn {sn}，进入恢复序列")
    else:
        print(f"hdc list targets 为空，进入恢复序列")

    # 恢复 1：TCP 重连本地模拟器端口
    print(f"  恢复: hdc tconn {DEFAULT_TCONN_ADDR}")
    try:
        _tconn(hdc_path, DEFAULT_TCONN_ADDR)
    except (subprocess.SubprocessError, OSError) as exc:
        print(f"  tconn 执行失败（继续）: {exc!r}", file=sys.stderr)
    targets = list_targets(hdc_path)
    chosen = pick(targets)
    if chosen:
        print(f"  tconn 后设备就绪: {chosen}")
        return chosen

    # 恢复 2：模拟器进程自检 + 重启
    if not _emulator_running():
        _start_emulator()
    else:
        print("  模拟器进程在运行但 hdc 未识别，等待其重新注册…")

    # 恢复 3：轮询 targets（tconn 兜底 + 重启约 25s）
    deadline = time.monotonic() + ENSURE_POLL_SECONDS
    waited = 0.0
    while time.monotonic() < deadline:
        time.sleep(POLL_INTERVAL_SECONDS)
        waited += POLL_INTERVAL_SECONDS
        try:
            _tconn(hdc_path, DEFAULT_TCONN_ADDR)  # 每轮兜底，已连则立即失败返回，开销可忽略
        except (subprocess.SubprocessError, OSError):
            pass
        targets = list_targets(hdc_path)
        chosen = pick(targets)
        if chosen:
            print(f"  轮询 {waited:.0f}s 后设备就绪: {chosen}")
            return chosen
    raise RuntimeError(
        f"等待 {ENSURE_POLL_SECONDS:.0f}s 后 hdc 仍无可用设备（hdc={hdc_path}，"
        f"sn={sn}，targets={targets}）\n"
        f"  补救: 手工执行 '{emulator_bin()} -start {emulator_name()}' 后重试；"
        f"无设备时可改用 --dry-run（纯 DSL 检查降级）"
    )


def dump_contains_bundle(dump_data: dict, bundle: str = DEFAULT_BUNDLE) -> bool:
    """dump JSON 树中是否存在 bundleName == bundle 的节点（递归）。纯函数，可单测。"""
    def walk(node):
        attrs = node.get("attributes") or {}
        if attrs.get("bundleName") == bundle:
            return True
        return any(walk(c) for c in node.get("children") or [])
    return walk(dump_data)


def verify_dump_has_bundle(dump_path: Path, bundle: str = DEFAULT_BUNDLE) -> None:
    """dump 质量守卫：dump 必须包含渲染应用节点，否则抛 RuntimeError。

    背景（2026-08-22 试跑问题 3）：b-q1 首版 dump 截到桌面（应用退后台）——
    卡根找不到且无人发现。守卫在 render 后立即核验，失败由调用方 aa start 重拉
    后再验一次，仍失败则硬失败。
    """
    dump_path = Path(dump_path)
    if not dump_path.is_file():
        raise RuntimeError(f"dump 文件不存在: {dump_path}")
    try:
        data = json.loads(dump_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"dump 解析失败 {dump_path}: {exc!r}") from exc
    if not dump_contains_bundle(data, bundle):
        raise RuntimeError(
            f"dump 未包含渲染应用（bundleName={bundle}）: {dump_path}\n"
            f"  原因: dump 可能截到桌面（应用退后台）或渲染未完成；建议 aa start 重拉后再 dump"
        )
