#!/usr/bin/env python3
"""对比度计算器（goal docs/goal-contrast-operator.md P1 / 验收 B2）。

供评审模型 / 人工复核调用的确定性算子：大模型不心算对比度，一律调本工具。

用法：
    # 任意 hex 栈（默认 DSL 序 #AARRGGBB；--order rgba 切规范序 #RRGGBBAA）
    python3 scripts/contrast_calc.py --fg "#FFFFFFFF" --bg "#FF317AF7"
    python3 scripts/contrast_calc.py --fg "#E5000000" --bg "#FFFFFFFF" --bg "#190A59F7" --order rgba

    # 从 DSL 求某文字组件的背景栈（含渐变包络三态）
    python3 scripts/contrast_calc.py --card <三件套目录> --comp text2
    python3 scripts/contrast_calc.py --dsl <card.genui.jsonl> --comp text2

输出：JSON（机器可读）+ 一行人读结论。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validators.contrast_calc import envelope_evaluate, evaluate, text_background_stack  # noqa: E402
from validators.dsl import CardParseError, load_case, load_genui, load_task_spec  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="对比度计算器（WCAG，支持多层 alpha 背景栈）")
    parser.add_argument("--fg", default=None, help="前景色 hex（可多次出现则取第一个）")
    parser.add_argument("--bg", action="append", default=None, help="背景层 hex，自底向上，可多次")
    parser.add_argument("--order", choices=["argb", "rgba"], default="argb",
                        help="字节序：argb=DSL #AARRGGBB（默认），rgba=规范 #RRGGBBAA")
    parser.add_argument("--card", default=None, help="三件套目录（与 --comp 连用）")
    parser.add_argument("--dsl", default=None, help="裸 DSL jsonl（与 --comp 连用）")
    parser.add_argument("--comp", default=None, help="文字组件 id（求其背景栈与包络三态）")
    args = parser.parse_args(argv)

    try:
        if args.comp:
            if args.card:
                d = Path(args.card)
                if not d.is_dir():
                    print(f"错误: 输入目录不存在: {d}", file=sys.stderr)
                    return 2
                card = load_case(d)
            elif args.dsl:
                p = Path(args.dsl)
                if not p.is_file():
                    print(f"错误: DSL 文件不存在: {p}", file=sys.stderr)
                    return 2
                card = load_genui(p, p.stem)
                card.query_text = ""
                card.task_spec = {}
            else:
                print("错误: --comp 需要 --card 或 --dsl 之一", file=sys.stderr)
                return 2
            comp = card.find_component(args.comp)
            if comp is None:
                print(f"错误: 组件不存在: {args.comp}", file=sys.stderr)
                return 2
            fg = (comp.get("styles") or {}).get("fontColor")
            if not isinstance(fg, str):
                print(f"错误: 组件 {args.comp} 无 fontColor", file=sys.stderr)
                return 2
            info = text_background_stack(card, args.comp)
            result = envelope_evaluate(fg, info)
            result["component"] = args.comp
            result["background_stack"] = info
        elif args.fg and args.bg:
            result = evaluate(args.fg, args.bg, byteorder=args.order)
        else:
            print("错误: 需要 (--fg + --bg) 或 (--card/--dsl + --comp)", file=sys.stderr)
            return 2
    except (CardParseError, ValueError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if "verdict" in result and result["verdict"] in ("pass", "pass-suggest", "fail", "uncertain"):
        v = result["verdict"]
        human = {
            "pass": "通过（最不利位置也 ≥3:1）",
            "pass-suggest": "通过 3:1 强制档，但 <4.5:1（建议级，DESIGN.md 正文建议 ≥4.5:1）",
            "fail": "不达标（所有位置均 <3:1，P1 硬性违规）",
            "uncertain": "无法确定（跨 3:1 门槛，取决于文字实际位置，需端侧确认）",
        }[v]
        print(f"结论: {v} —— {human}（ratio {result['ratio_min']}~{result['ratio_max']})", file=sys.stderr)
    else:
        print(f"结论: {result['verdict']}（ratio {result['ratio']}）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
