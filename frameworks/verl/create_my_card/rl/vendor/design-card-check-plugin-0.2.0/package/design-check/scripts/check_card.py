#!/usr/bin/env python3
"""单卡设计检查 CLI（L1 + 可选 L2a/L2b）。

输入形态（goal docs/goal-dsh-design-check-plugin.md §2.2，检查对象 = 任意新输入产物）：
    --qdir q010            数据集内 case id（向后兼容）
    --dir <path>           任意三件套目录（query.txt/task-spec.json/card.genui.jsonl）
    --dsl <path>           裸 DSL jsonl（createSurface/updateComponents[/updateDataModel]）

用法：
    python3 scripts/check_card.py --qdir q010 --format json
    python3 scripts/check_card.py --dir /path/to/case --layout dump.json
    python3 scripts/check_card.py --dsl /path/to/card.genui.jsonl
    python3 scripts/check_card.py --qdir q010 --with-layout     # 用数据集 dump 真值跑 L2a/L2b
    python3 scripts/check_card.py --dsl x.jsonl --layout d.json --include-delegated

输出：统一 finding schema（开发计划 §3.1）。

退出码契约（Idea6-WP-E3，调用方据以区分「检出违规」与「检查器自身故障」）：
    0 = 检查完成且无 P0 findings；
    1 = 检查完成且有 P0 findings（正常检出结果，JSON 照常输出到 stdout）；
    2 = 检查器自身故障（输入缺失/非法、解析失败、未预期异常——stderr 输出
        异常类型与可定位路径/卡号，stdout 不产出 findings，不生成伪违规）。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validators.config import card_data_dir, design_spec_path  # noqa: E402
from validators.design_contract import (  # noqa: E402
    attach_card_size_contracts, load_design_contract,)
from validators.dsl import CardParseError, load_case, load_genui  # noqa: E402
from validators.layout import DumpLayout  # noqa: E402
from validators.rules import run_l1  # noqa: E402


def build_case_output(case_id, findings, meta=None):
    return {
        "qid": case_id,
        "findings": [f.to_dict() for f in findings],
        "summary": {
            "total": len(findings),
            "p0": sum(1 for f in findings if f.severity == "P0"),
            "p1": sum(1 for f in findings if f.severity == "P1"),
            "p2": sum(1 for f in findings if f.severity == "P2"),
        },
        "meta": meta or {},
    }


def load_input_card(args) -> "object":
    """按输入形态加载卡片；路径缺失/结构非法显式报错（含可定位路径）。"""
    if args.dir:
        case_dir = Path(args.dir)
        if not case_dir.is_dir():
            print(f"错误: 输入目录不存在: {case_dir}", file=sys.stderr)
            raise SystemExit(2)
        try:
            return load_case(case_dir)  # 三件套缺失时抛 CardParseError（含路径）
        except CardParseError as exc:  # 定位补全：解析失败信息附上 case 目录路径
            raise CardParseError(f"{exc}（case 目录: {case_dir}）") from exc
    if args.dsl:
        dsl_path = Path(args.dsl)
        if not dsl_path.is_file():
            print(f"错误: DSL 文件不存在: {dsl_path}", file=sys.stderr)
            raise SystemExit(2)
        if dsl_path.stat().st_size == 0:
            print(f"错误: DSL 文件为空: {dsl_path}", file=sys.stderr)
            raise SystemExit(2)
        # 分支前缀目录提示：check_case 管线 trio 目录形如 review/pipeline/A-q20 →
        # case_id 带分支前缀，人工指认表（_MANUAL_VERDICTS）可解析分支；
        # 其余目录（裸分支文件 dsl/ 等）不匹配，维持 stem 行为不变
        case_id = dsl_path.stem
        m = re.match(r"^([ABCMS])-q\d+$", dsl_path.parent.name)
        if m:
            case_id = dsl_path.parent.name
        card = load_genui(dsl_path, case_id)
        card.query_text = ""
        card.task_spec = {}
        return card
    case_dir = card_data_dir() / args.qdir
    if not (case_dir / "card.genui.jsonl").is_file():
        print(f"错误: case 目录不存在或缺少 DSL: {case_dir}", file=sys.stderr)
        raise SystemExit(2)
    return load_case(case_dir)


def layout_placement_meta(card) -> dict:
    """2×4 卡归位模板信息（meta 传递，报告层「标准模板」视口用）。

    委托 validators/rules/layout_2x4.placement_meta 公开接口
    （Idea2-WP-A 2026-08-26 私有函数引用收口，行为零变化）。
    """
    from validators.rules import layout_2x4 as L

    return L.placement_meta(card)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="单卡设计检查（L1+可选 L2a/L2b，任意输入产物）")
    inputs = parser.add_mutually_exclusive_group()
    inputs.add_argument("--qdir", default=None, help="数据集内 case id（如 q010）")
    inputs.add_argument("--dir", default=None, help="任意三件套目录路径")
    inputs.add_argument("--dsl", default=None, help="裸 DSL jsonl 文件路径")
    parser.add_argument("--format", choices=["json", "text"], default="json")
    parser.add_argument("--with-layout", action="store_true",
                        help="自动用数据集 render-evidence 的 dump 真值跑 L2a/L2b（仅 --qdir 形态）")
    parser.add_argument("--layout", default=None, help="显式 dump layout JSON 路径")
    parser.add_argument("--include-delegated", action="store_true",
                        help="恢复输出已移交同事侧的三条几何规则（GEOMETRY.OVERLAP /"
                             " BASELINE_MISMATCH / AREA_CONTENT_TEXT_OVERLAP；默认静默，Idea6-WP-E2）")
    args = parser.parse_args(argv)
    if args.qdir is None and not args.dir and not args.dsl:
        args.qdir = "q001"  # 向后兼容：无参数时默认 q001
    # 退出码契约见模块 docstring：0=无 P0 / 1=有 P0 / 2=自身故障。
    target_desc = args.dir or args.dsl or f"qdir={args.qdir}"

    try:
        card = load_input_card(args)
        contract = load_design_contract(design_spec_path())
        # 双契约接线收口（Idea2-WP-B）：2×4 卡挂 2×4 布局契约（校验失败即抛错，
        # 防规范误改后静默错检）；其余维持现状不挂。
        attach_card_size_contracts(contract, card)
    except (CardParseError, FileNotFoundError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2
    except SystemExit:
        raise  # load_input_card 的显式参数校验失败已带路径打印并退出 2
    except Exception as exc:  # 未预期异常：定位 + exit 2，不再生成伪 finding（Idea6-WP-E3）
        _report_internal_error(exc, target=target_desc)
        return 2

    try:
        return _check(card, contract, args)
    except SystemExit:
        raise
    except Exception as exc:  # 同上：检查阶段故障也按「检查器自身故障」口径暴露
        _report_internal_error(exc, target=f"{target_desc}（qid={getattr(card, 'case_id', '?')}）")
        return 2


def _report_internal_error(exc: Exception, target: str) -> None:
    """顶层异常统一出口：stderr 输出异常类型 + 检查对象定位 + 堆栈（可复核）。"""
    print(f"错误[检查器自身故障，exit 2]: {type(exc).__name__}: {exc}\n"
          f"  检查对象: {target}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)


def _check(card, contract, args) -> int:
    """加载后的检查主体（成功路径与可判定的输入校验分离，供 WP-E3 故障兜底包裹）。"""
    findings = run_l1(card, contract, card.query_text)

    layout_path = Path(args.layout) if args.layout else None
    if layout_path is None and args.with_layout and args.qdir:
        from validators.dataset import render_evidence_layout_path

        lp = render_evidence_layout_path(args.qdir)
        if lp.is_file():
            layout_path = lp
    if layout_path is not None:
        if not layout_path.is_file():
            print(f"错误: 找不到 dump {layout_path}", file=sys.stderr)
            return 2
        from validators.geometry import run_geometry
        from validators.reconcile_lib import reconcile

        layout = DumpLayout.from_file(layout_path)
        if any(n.attributes.get("bundleName") == "com.example.myapplication"
               for n in layout.iter_nodes()):
            findings += run_geometry(card, layout,
                                     include_delegated=args.include_delegated)
            findings += reconcile(card, layout)
        else:
            # 2026-08-22 试跑问题 3：b-q1 首版 dump 截到桌面（应用退后台）无人发现。
            # dump 中无渲染应用节点时 L2a/L2b 无真值可判，显式告警而非静默跳过；
            # 退出码不变（仍按 L1 判定），由调用方决定是否重采。
            print(f"警告: dump 中未找到渲染应用（{layout_path}），L2a/L2b 跳过"
                  f"——dump 可能截到桌面，建议重采", file=sys.stderr)

    from validators.packages_loader import packages_meta

    out = build_case_output(card.case_id, findings, meta={
        "design_spec": str(design_spec_path()),
        "card_size": card.card_size,
        "card_size_source": card.card_size_source,
        "packages": packages_meta(),
    })
    out["meta"].update(layout_placement_meta(card))
    if args.format == "json":
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"{out['qid']} findings={out['summary']['total']} "
              f"(P0={out['summary']['p0']} P1={out['summary']['p1']} P2={out['summary']['p2']})")
        for f in findings:
            el = f.element.dsl_id if f.element else None
            loc = f" @{el}" if el else ""
            print(f"  [{f.layer}] {f.severity} {f.rule_id}: {f.message}{loc}")
            if f.fix_hint:
                print(f"      fix: {f.fix_hint}")
    return 0 if out["summary"]["p0"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
