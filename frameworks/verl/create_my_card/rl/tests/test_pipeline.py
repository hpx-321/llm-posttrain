from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from frameworks.verl.create_my_card.rl.pipeline.cli import main as pipeline_main
from frameworks.verl.create_my_card.rl.pipeline.config import load_pipeline_spec
from frameworks.verl.create_my_card.rl.pipeline.contracts import (
    PIPELINE_SCHEMA_VERSION,
    PipelineError,
    TASK_NAME,
)
from frameworks.verl.create_my_card.rl.pipeline.data import (
    build_dpo_dataset,
    build_grpo_dataset,
    build_rft_dataset,
    load_scored_candidates,
)
from frameworks.verl.create_my_card.rl.pipeline.runner import PipelineRunner
from frameworks.verl.create_my_card.rl.reward.compute_score import _load_config


REPO_ROOT = Path(__file__).resolve().parents[5]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _pipeline_config(output_root: Path, *, mode: str = "scaffold") -> dict[str, object]:
    stages = []
    for stage in ("rft", "dpo", "grpo"):
        stages.append(
            {
                "name": stage,
                "enabled": True,
                "backend": "mock",
                "dataset_dir": f"{{run_dir}}/datasets/{stage}",
                "dataset_files": ["train.data", "validation.data"],
                "output_checkpoint": "{stage_dir}/checkpoint",
            }
        )
    return {
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "task": TASK_NAME,
        "run": {
            "execution_mode": mode,
            "output_root": str(output_root),
            "base_checkpoint": "base-sft-checkpoint",
        },
        "stages": stages,
    }


class PipelineRunnerTests(unittest.TestCase):
    def test_run_id_rejects_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "pipeline.json"
            _write_json(config_path, _pipeline_config(root / "runs"))
            spec = load_pipeline_spec(config_path, repo_root=REPO_ROOT)
            for run_id in ("..", ".", "../escape", "folder/escape", "C:escape"):
                with self.subTest(run_id=run_id), self.assertRaises(PipelineError):
                    PipelineRunner(spec, run_id=run_id, backend_override="mock")

    def test_mock_pipeline_stops_and_resumes_with_checkpoint_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "pipeline.json"
            _write_json(config_path, _pipeline_config(root / "runs"))
            spec = load_pipeline_spec(config_path, repo_root=REPO_ROOT)

            first = PipelineRunner(spec, run_id="case", backend_override="mock").run(
                stop_after="rft"
            )
            self.assertEqual(first["status"], "paused_after_stage")
            self.assertEqual(first["next_stage"], "dpo")

            second = PipelineRunner(
                spec, run_id="case", backend_override="mock", resume=True
            ).run(stop_after="dpo")
            self.assertEqual(second["status"], "paused_after_stage")
            self.assertEqual(second["next_stage"], "grpo")
            self.assertEqual(
                second["stages"][1]["input_checkpoint"],
                second["stages"][0]["output_checkpoint"],
            )

            final = PipelineRunner(
                spec, run_id="case", backend_override="mock", resume=True
            ).run()
            self.assertEqual(final["status"], "succeeded")
            self.assertIsNone(final["next_stage"])
            self.assertTrue(final["mock_only"])
            self.assertEqual(len(final["stages"]), 3)
            self.assertEqual(
                final["stages"][2]["input_checkpoint"],
                final["stages"][1]["output_checkpoint"],
            )

    def test_resume_rejects_changed_config(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "pipeline.json"
            config = _pipeline_config(root / "runs")
            _write_json(config_path, config)
            spec = load_pipeline_spec(config_path, repo_root=REPO_ROOT)
            PipelineRunner(spec, run_id="case", backend_override="mock").run(
                stop_after="rft"
            )
            config["run"]["base_checkpoint"] = "different-checkpoint"  # type: ignore[index]
            _write_json(config_path, config)
            changed = load_pipeline_spec(config_path, repo_root=REPO_ROOT)
            with self.assertRaisesRegex(PipelineError, "unsafe resume"):
                PipelineRunner(
                    changed, run_id="case", backend_override="mock", resume=True
                ).run(stop_after="rft")

    def test_train_mode_runs_without_external_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "pipeline.json"
            _write_json(config_path, _pipeline_config(root / "runs", mode="train"))
            spec = load_pipeline_spec(config_path, repo_root=REPO_ROOT)
            result = PipelineRunner(
                spec, run_id="case", backend_override="mock"
            ).run(stop_after="rft")
            self.assertEqual(result["status"], "paused_after_stage")

    def test_cli_overrides_mode_and_base_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config_path = root / "pipeline.json"
            _write_json(config_path, _pipeline_config(root / "runs"))
            argv = [
                "run_pipeline.py",
                "run",
                "--config",
                str(config_path),
                "--run-id",
                "case",
                "--backend",
                "mock",
                "--mode",
                "smoke",
                "--base-checkpoint",
                "override-checkpoint",
                "--stop-after",
                "rft",
            ]
            with patch("sys.argv", argv), redirect_stdout(io.StringIO()):
                self.assertEqual(pipeline_main(), 0)
            manifest = json.loads(
                (root / "runs/case/stages/rft/stage-manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(manifest["execution_mode"], "smoke")
            self.assertEqual(manifest["input_checkpoint"], "override-checkpoint")

    def test_command_smoke_reuses_input_without_saving_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base_checkpoint = root / "base-checkpoint"
            base_checkpoint.mkdir()
            config = _pipeline_config(root / "runs", mode="smoke")
            config["run"]["base_checkpoint"] = str(base_checkpoint)  # type: ignore[index]
            rft = config["stages"][0]  # type: ignore[index]
            rft["backend"] = "command"
            rft["commands"] = [
                {
                    "name": "smoke-step",
                    "argv": [sys.executable, "-c", "print('smoke step completed')"],
                    "cwd": str(REPO_ROOT),
                }
            ]
            config_path = root / "pipeline.json"
            _write_json(config_path, config)
            dataset_dir = root / "runs/case/datasets/rft"
            dataset_dir.mkdir(parents=True)
            for name in ("train.data", "validation.data"):
                (dataset_dir / name).write_text("row\n", encoding="utf-8")

            spec = load_pipeline_spec(config_path, repo_root=REPO_ROOT)
            result = PipelineRunner(spec, run_id="case").run(stop_after="rft")

            self.assertEqual(result["final_checkpoint"], str(base_checkpoint))
            self.assertFalse((root / "runs/case/stages/rft/checkpoint").exists())


class DatasetBuilderTests(unittest.TestCase):
    def test_builds_rft_dpo_and_grpo_native_datasets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            taskspec_path = root / "taskspec.json"
            prompt_path = root / "system.txt"
            candidates_path = root / "candidates.jsonl"
            audits_path = root / "audits.jsonl"
            labels_path = root / "labels.json"
            task_spec = {
                "size": "2x2",
                "userQuery": "生成卡片",
                "dataModelSchema": {"title": {"type": "string"}},
                "eventCandidates": [],
                "assetCandidates": [],
            }
            _write_json(
                taskspec_path,
                [
                    {"id": "task-1", "taskSpec": task_spec},
                    {"id": "task-2", "taskSpec": task_spec},
                ],
            )
            prompt_path.write_text("只输出完整 Compact DSL。", encoding="utf-8")
            candidates: list[dict[str, object]] = []
            audits: list[dict[str, object]] = []
            for group in ("task-1", "task-2"):
                for suffix, score, eligible in (("good", 0.9, True), ("bad", 0.3, False)):
                    candidate_id = f"{group}-{suffix}"
                    candidates.append(
                        {
                            "id": candidate_id,
                            "groupId": group,
                            "designCompactDsl": "Row(Text($title),Text($title))"
                            if eligible
                            else "Row(Text($title),Text('x'))",
                            "completionTokens": 20,
                            "producerCheckpoint": "checkpoint-v1",
                        }
                    )
                    audits.append(
                        {
                            "sample_id": candidate_id,
                            "score": score,
                            "masked": False,
                            "policy_update_eligible": eligible,
                            "gates": [
                                {"name": "conversion", "passed": True},
                                {"name": "checker_p0", "passed": eligible},
                            ],
                        }
                    )
            _write_jsonl(candidates_path, candidates)
            _write_jsonl(audits_path, audits)
            with self.assertRaisesRegex(PipelineError, "producer checkpoint mismatch"):
                load_scored_candidates(
                    candidates_path=candidates_path,
                    audits_path=audits_path,
                    allow_partial_score=False,
                    expected_producer_checkpoint="checkpoint-v2",
                )

            missing_lineage = root / "missing-lineage.jsonl"
            candidates_without_lineage = [dict(row) for row in candidates]
            for candidate in candidates_without_lineage:
                candidate.pop("producerCheckpoint")
            _write_jsonl(missing_lineage, candidates_without_lineage)
            with self.assertRaisesRegex(PipelineError, "producer checkpoint mismatch"):
                load_scored_candidates(
                    candidates_path=missing_lineage,
                    audits_path=audits_path,
                    allow_partial_score=False,
                    expected_producer_checkpoint="checkpoint-v1",
                )
            _write_json(
                labels_path,
                [
                    {"id": "task-1", "reviewed": True},
                    {"id": "task-2", "reviewed": True},
                ],
            )

            captured_rows: dict[str, list[dict[str, object]]] = {}

            def fake_parquet(rows: object, path: Path) -> None:
                values = list(rows)  # type: ignore[arg-type]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")
                captured_rows[str(path)] = values

            with patch(
                "frameworks.verl.create_my_card.rl.pipeline.data.build_parquet.write_parquet",
                side_effect=fake_parquet,
            ), patch(
                "frameworks.verl.create_my_card.rl.pipeline.data._write_grpo_parquet",
                side_effect=fake_parquet,
            ):
                rft = build_rft_dataset(
                    candidates_path=candidates_path,
                    audits_path=audits_path,
                    taskspec_path=taskspec_path,
                    system_prompt_path=prompt_path,
                    output_dir=root / "rft",
                    min_score=0.8,
                    validation_ratio=0.5,
                    seed=7,
                    require_policy_update_eligible=True,
                    allow_partial_score=False,
                    expected_producer_checkpoint="checkpoint-v1",
                )
                dpo = build_dpo_dataset(
                    candidates_path=candidates_path,
                    audits_path=audits_path,
                    taskspec_path=taskspec_path,
                    system_prompt_path=prompt_path,
                    output_dir=root / "dpo",
                    chosen_min_score=0.8,
                    min_score_margin=0.2,
                    max_length_ratio=1.25,
                    validation_ratio=0.5,
                    seed=7,
                    require_policy_update_eligible=True,
                    allow_partial_score=False,
                    expected_producer_checkpoint="checkpoint-v1",
                )
                grpo = build_grpo_dataset(
                    taskspec_path=taskspec_path,
                    system_prompt_path=prompt_path,
                    labels_path=labels_path,
                    output_dir=root / "grpo",
                    validation_ratio=0.5,
                    seed=7,
                    require_reviewed_labels=True,
                )

            self.assertEqual(rft["selected_count"], 2)
            self.assertEqual(rft["smoke_count"], 256)
            self.assertEqual(
                len(captured_rows[str(root / "rft" / "oom_probe.parquet")]),
                256,
            )
            self.assertFalse((root / "rft" / "dataset-manifest.json").exists())
            self.assertEqual(dpo["pair_count"], 2)
            self.assertEqual(dpo["train_count"], 1)
            self.assertEqual(dpo["validation_count"], 1)
            self.assertEqual(grpo["train_count"], 1)
            self.assertEqual(grpo["validation_count"], 1)
            self.assertEqual(
                list(captured_rows[str(root / "grpo" / "train.parquet")][0]),
                ["id", "data_source", "prompt", "ability", "reward_model", "extra_info"],
            )


class RewardConfigTransitionTests(unittest.TestCase):
    def test_future_validated_reward_can_be_enabled_without_code_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "reward.json"
            current_path = (
                REPO_ROOT
                / "frameworks/verl/create_my_card/rl/configs/reward_stage0.json"
            )
            config = json.loads(current_path.read_text(encoding="utf-8"))
            config["status"] = "validated_for_policy_update"
            config["calibrated_components"] = [
                "contract",
                "content",
                "static_layout",
                "style",
                "efficiency",
            ]
            config["policy_update_enabled"] = True
            _write_json(path, config)
            self.assertTrue(_load_config(path)["policy_update_enabled"])

            config["status"] = "candidate_unvalidated"
            _write_json(path, config)
            with self.assertRaisesRegex(ValueError, "validated_for_policy_update"):
                _load_config(path)


if __name__ == "__main__":
    unittest.main()
