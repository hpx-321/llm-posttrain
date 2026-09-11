from pathlib import Path
import json
import subprocess
import sys
import tempfile


ROOT = Path(
    r"E:\work\RL\llm-posttrain\frameworks\verl\create_my_card\sft\data\source\20260909-gpt6astra"
)

CONVERTER = Path(
    r"E:\work\RL\llm-posttrain\frameworks\verl\create_my_card\data_pipeline\converters\reverse_and_verify.py"
)


def normalize_a2ui_jsonl(source: Path, temp_dir: Path) -> Path:
    """将 JSON 数组格式的 genui 文件转换为标准 JSONL。"""
    text = source.read_text(encoding="utf-8-sig").strip()

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{source} 不是合法 JSON：{exc}") from exc

    if isinstance(payload, dict):
        rows = [payload]
    elif isinstance(payload, list):
        rows = payload
    else:
        raise RuntimeError(f"{source} 根节点必须是 JSON object 或 array")

    if not rows or not all(isinstance(row, dict) for row in rows):
        raise RuntimeError(f"{source} 中的 A2UI 记录必须全部是 JSON object")

    normalized = temp_dir / source.name
    with normalized.open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            file.write("\n")

    return normalized


def main() -> None:
    compact_dir = ROOT / "compact"
    roundtrip_dir = ROOT / "roundtrip"
    reports_dir = ROOT / "reports"

    compact_dir.mkdir(exist_ok=True)
    roundtrip_dir.mkdir(exist_ok=True)
    reports_dir.mkdir(exist_ok=True)

    files = sorted((ROOT / "dsl").glob("*.genui.jsonl"))

    if not files:
        raise RuntimeError(f"没有找到 DSL 文件：{ROOT / 'dsl'}")

    with tempfile.TemporaryDirectory(prefix="a2ui-normalized-") as temp_name:
        temp_dir = Path(temp_name)

        for source in files:
            sample_id = source.name.removesuffix(".genui.jsonl")
            task_spec = ROOT / "taskspec" / f"{sample_id}.taskspec.json"
            card_spec = ROOT / "cardspec" / f"{sample_id}.cardspec.json"

            if not task_spec.exists():
                raise FileNotFoundError(f"缺少 TaskSpec：{task_spec}")

            if not card_spec.exists():
                raise FileNotFoundError(f"缺少 CardSpec：{card_spec}")

            normalized_source = normalize_a2ui_jsonl(source, temp_dir)

            command = [
                sys.executable,
                str(CONVERTER),
                "--source-a2ui",
                str(normalized_source),
                "--task-spec",
                str(task_spec),
                "--card-spec",
                str(card_spec),
                "--compact-out",
                str(compact_dir / f"{sample_id}.compact.genui.jsonl"),
                "--roundtrip-out",
                str(roundtrip_dir / f"{sample_id}.genui.jsonl"),
                "--report-out",
                str(reports_dir / f"{sample_id}.json"),
            ]

            print(f"Converting {sample_id} ...")
            subprocess.run(command, check=True)

    print(f"转换完成，共处理 {len(files)} 条数据。")


if __name__ == "__main__":
    main()