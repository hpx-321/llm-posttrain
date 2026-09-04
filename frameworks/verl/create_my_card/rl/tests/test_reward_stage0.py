"""Regression tests for the CreateMyCard Stage 0 reward audit."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

from frameworks.verl.create_my_card.data_pipeline.converters.compact_dsl_a2ui_converter import (
    CompactDslConversionError,
    convert_compact_dsl_to_a2ui,
    validate_compact_dsl_context,
)
from frameworks.verl.create_my_card.rl.reward.compute_score import (
    RewardComputer,
    RewardRequest,
    _finding_family_score,
    _l2_score,
)
from frameworks.verl.create_my_card.rl.reward.content_coverage import (
    ContentRequirements,
    _schema_has_path,
    derive_card_spec,
    measure_content_coverage,
)
from frameworks.verl.create_my_card.rl.evaluation.audit_rewards import (
    _count_completion_tokens,
)
from frameworks.verl.create_my_card.rl.evaluation.analyze_reward_groups import (
    analyze_groups,
)
from frameworks.verl.create_my_card.rl.evaluation.build_reward_canary import (
    build_rows as build_canary_rows,
)
from frameworks.verl.create_my_card.rl.reward.design_checker_adapter import (
    VENDORED_CHECKER_ROOT,
    CheckerConfig,
    CheckerExecutionError,
    CheckerResult,
    DesignCheckerAdapter,
)
from frameworks.verl.create_my_card.rl.evaluation.render_l2_sample import (
    main as render_l2_main,
    write_render_payload,
)
from frameworks.verl.create_my_card.sft.evaluation.export_renderable_a2ui import (
    collect_raw_outputs,
    filter_auditable_raw_outputs,
    main as export_candidates_main,
    read_raw_outputs,
    read_taskspec_inputs,
)


VALID_DSL = "\n".join(
    [
        '["root","Column",{"width":160,"height":160},["temp","button"]]',
        '["temp","Text",{"content":{"path":"/data/weather/temp"},"fontSize":14,"width":60,"height":20}]',
        '["button","Button",{"label":"打开","width":120,"height":30,"onClick":[{"call":"openWeather","args":{}}]}]',
        '["/data/weather/temp","26℃"]',
    ]
)


class VendoredCheckerTests(unittest.TestCase):
    def test_vendored_checker_runtime_is_complete(self) -> None:
        scripts = VENDORED_CHECKER_ROOT / "scripts"
        for name in (
            "check_card.py",
            "contrast_calc.py",
            "device_utils.py",
            "render_dump.py",
            "render_eval_dump.py",
        ):
            self.assertTrue((scripts / name).is_file())

        package_json = VENDORED_CHECKER_ROOT.parent / "package.json"
        payload = json.loads(package_json.read_text(encoding="utf-8"))
        self.assertEqual(payload["name"], "design-card-check-plugin")
        self.assertEqual(payload["version"], "0.2.0")
        self.assertTrue((VENDORED_CHECKER_ROOT.parent / "DESIGN.md").is_file())
        self.assertTrue((VENDORED_CHECKER_ROOT.parent / "DESIGN-2x4.md").is_file())

TASK_SPEC = {
    "userQuery": "显示温度并打开天气",
    "size": "2x2",
    "dataModelSchema": {
        "data": {"weather": {"temp": {"type": "string", "sampleValue": "26℃"}}}
    },
    "eventCandidates": [{"call": "openWeather", "args": {}}],
    "assetCandidates": [],
}

CONTENT_LABELS = {
    "reviewed": True,
    "required_primary_paths": ["/data/weather/temp"],
    "required_event_calls": ["openWeather"],
    "reference_content_budget": {"facts_min": 1, "facts_max": 2},
}


class _FakeChecker:
    def __init__(self, root: Path, *, findings: list[dict[str, Any]] | None = None) -> None:
        self.config = CheckerConfig(root)
        self.findings = findings or []

    def check(self, *args: Any, **kwargs: Any) -> CheckerResult:
        has_p0 = any(finding.get("severity") == "P0" for finding in self.findings)
        return CheckerResult(
            exit_code=1 if has_p0 else 0,
            findings=tuple(self.findings),
            summary={"total": len(self.findings), "p0": int(has_p0), "p1": 0, "p2": 0},
            meta={},
            stderr="",
            elapsed_ms=1.0,
            attempts=1,
            l2_requested=kwargs.get("layout_path") is not None,
            l2_evaluated=kwargs.get("layout_path") is not None,
        )


class _FailingChecker(_FakeChecker):
    def check(self, *args: Any, **kwargs: Any) -> CheckerResult:
        raise CheckerExecutionError(
            "checker unavailable",
            kind="checker_exit_2",
            retryable=True,
            attempts=2,
            stderr="boom",
        )


class RewardComputerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        package = Path(self.temporary.name) / "package"
        checker_root = package / "design-check"
        (checker_root / "scripts").mkdir(parents=True)
        (checker_root / "scripts" / "check_card.py").write_text("# fixture\n", encoding="utf-8")
        (package / "package.json").write_text(
            json.dumps({"version": "test"}), encoding="utf-8"
        )
        (package / "DESIGN.md").write_text("fixture", encoding="utf-8")
        (package / "DESIGN-2x4.md").write_text("fixture", encoding="utf-8")
        self.checker_root = checker_root

    def test_valid_candidate_is_auditable_but_not_training_eligible(self) -> None:
        computer = RewardComputer(_FakeChecker(self.checker_root))
        audit = computer.compute(
            RewardRequest(
                sample_id="sample",
                solution_str=VALID_DSL,
                task_spec=TASK_SPEC,
                content_labels=CONTENT_LABELS,
                finish_reason="stop",
                completion_tokens=100,
            )
        )
        self.assertEqual(audit.score, 1.0)
        self.assertFalse(audit.masked)
        self.assertFalse(audit.policy_update_eligible)
        self.assertEqual(audit.components["content"].value, 1.0)
        self.assertEqual(
            audit.components["content"].evidence["matched_primary_paths"],
            ["/data/weather/temp"],
        )

    def test_exact_event_requirement_distinguishes_same_call_arguments(self) -> None:
        expected_handler = {"call": "openTarget", "args": {"target": "primary"}}
        distractor_handler = {
            "call": "openTarget",
            "args": {"target": "distractor"},
        }
        task_spec = {
            **TASK_SPEC,
            "eventCandidates": [expected_handler, distractor_handler],
        }
        labels = {
            "reviewed": True,
            "required_primary_paths": ["/data/weather/temp"],
            "required_events": [expected_handler],
            "reference_content_budget": {"facts_min": 1, "facts_max": 2},
        }

        def with_handler(handler: dict[str, Any]) -> str:
            return VALID_DSL.replace(
                '{"call":"openWeather","args":{}}',
                json.dumps(handler, ensure_ascii=False, separators=(",", ":")),
            )

        computer = RewardComputer(_FakeChecker(self.checker_root))
        expected = computer.compute(
            RewardRequest(
                sample_id="expected",
                solution_str=with_handler(expected_handler),
                task_spec=task_spec,
                content_labels=labels,
                finish_reason="stop",
                completion_tokens=100,
            )
        )
        distractor = computer.compute(
            RewardRequest(
                sample_id="distractor",
                solution_str=with_handler(distractor_handler),
                task_spec=task_spec,
                content_labels=labels,
                finish_reason="stop",
                completion_tokens=100,
            )
        )

        self.assertEqual(expected.score, 1.0)
        self.assertEqual(expected.components["content"].value, 1.0)
        self.assertEqual(
            expected.components["content"].evidence["matched_events"],
            [expected_handler],
        )
        self.assertEqual(distractor.score, -0.5)
        self.assertEqual(distractor.components["content"].value, 0.5)
        self.assertEqual(
            distractor.components["content"].evidence["matched_events"], []
        )

    def test_missing_primary_labels_does_not_silently_renormalize(self) -> None:
        computer = RewardComputer(_FakeChecker(self.checker_root))
        audit = computer.compute(
            RewardRequest(
                sample_id="sample",
                solution_str=VALID_DSL,
                task_spec=TASK_SPEC,
                finish_reason="stop",
                completion_tokens=100,
            )
        )
        self.assertIsNone(audit.score)
        self.assertEqual(audit.components["content"].value, None)
        self.assertAlmostEqual(audit.partial_score, 0.8)

    def test_invalid_asset_is_a_policy_failure(self) -> None:
        dsl = VALID_DSL.replace(
            '["temp","Text",{"content":{"path":"/data/weather/temp"},"fontSize":14,"width":60,"height":20}]',
            '["temp","Image",{"src":"resources/base/media/not-allowed.svg","width":20,"height":20}]',
        )
        computer = RewardComputer(_FakeChecker(self.checker_root))
        audit = computer.compute(
            RewardRequest(
                sample_id="sample",
                solution_str=dsl,
                task_spec=TASK_SPEC,
                content_labels=CONTENT_LABELS,
                finish_reason="stop",
                completion_tokens=100,
            )
        )
        self.assertEqual(audit.score, -0.5)
        self.assertFalse(audit.masked)
        self.assertEqual(audit.components["contract"].value, 1.0)
        self.assertTrue(
            any(gate.name == "taskspec_allowlist" and gate.passed is False for gate in audit.gates)
        )

    def test_checker_failure_is_masked_instead_of_scored(self) -> None:
        computer = RewardComputer(_FailingChecker(self.checker_root))
        audit = computer.compute(
            RewardRequest(
                sample_id="sample",
                solution_str=VALID_DSL,
                task_spec=TASK_SPEC,
                content_labels=CONTENT_LABELS,
                finish_reason="stop",
                completion_tokens=100,
            )
        )
        self.assertIsNone(audit.score)
        self.assertTrue(audit.masked)
        self.assertTrue(audit.retryable)

    def test_invalid_reward_metadata_is_masked_not_charged_to_model(self) -> None:
        computer = RewardComputer(_FakeChecker(self.checker_root))
        audit = computer.compute(
            RewardRequest(
                sample_id="sample",
                solution_str=VALID_DSL,
                task_spec={**TASK_SPEC, "dataModelSchema": None},
                finish_reason="stop",
                completion_tokens=100,
            )
        )
        self.assertIsNone(audit.score)
        self.assertTrue(audit.masked)
        self.assertFalse(audit.retryable)
        self.assertEqual(audit.gates[0].action, "mask_dataset_row")

    def test_unsupported_size_and_negative_tokens_are_metadata_errors(self) -> None:
        computer = RewardComputer(_FakeChecker(self.checker_root))
        unsupported = computer.compute(
            RewardRequest(
                sample_id="sample",
                solution_str=VALID_DSL,
                task_spec={**TASK_SPEC, "size": "3x3"},
            )
        )
        negative_tokens = computer.compute(
            RewardRequest(
                sample_id="sample",
                solution_str=VALID_DSL,
                task_spec=TASK_SPEC,
                completion_tokens=-1,
            )
        )
        self.assertTrue(unsupported.masked)
        self.assertTrue(negative_tokens.masked)
        self.assertIsNone(unsupported.score)
        self.assertIsNone(negative_tokens.score)

    def test_p0_is_a_valid_negative_sample_and_caps_score(self) -> None:
        finding = {
            "qid": "sample",
            "layer": "L1",
            "rule_id": "STRUCT.ROOT",
            "severity": "P0",
            "evidence_type": "程序已证实",
            "element": {"dsl_id": "root", "json_pointer": "", "dump_id": None},
        }
        computer = RewardComputer(_FakeChecker(self.checker_root, findings=[finding]))
        audit = computer.compute(
            RewardRequest(
                sample_id="sample",
                solution_str=VALID_DSL,
                task_spec=TASK_SPEC,
                content_labels=CONTENT_LABELS,
                finish_reason="stop",
                completion_tokens=100,
            )
        )
        self.assertEqual(audit.score, 0.0)
        self.assertFalse(audit.masked)

    def test_device_confirmation_findings_do_not_add_penalty(self) -> None:
        finding = {
            "layer": "L1",
            "rule_id": "VISUAL.CONTRAST",
            "severity": "P2",
            "evidence_type": "需端侧确认",
            "element": {"dsl_id": "temp"},
        }
        score, evidence = _finding_family_score(
            [finding],
            ["VISUAL."],
            {"P0": 1.0, "P1": 0.25, "P2": 0.05},
            penalized_evidence_types={"程序已证实"},
            layers={"L1"},
        )
        self.assertEqual(score, 1.0)
        self.assertEqual(evidence["excluded_by_evidence_type"], ["VISUAL.CONTRAST"])

    def test_duplicate_rule_and_element_is_penalized_once(self) -> None:
        finding = {
            "layer": "L1",
            "rule_id": "AREA.TITLE_TEXT_TIER",
            "severity": "P1",
            "evidence_type": "程序已证实",
            "element": {"dsl_id": "temp"},
        }
        score, evidence = _finding_family_score(
            [finding, dict(finding)],
            ["AREA."],
            {"P0": 1.0, "P1": 0.25, "P2": 0.05},
            penalized_evidence_types={"程序已证实"},
            layers={"L1"},
        )
        self.assertEqual(score, 0.75)
        self.assertEqual(evidence["deduplicated_counts"]["P1"], 1)

    def test_l2_scores_size_rules_and_reports_unweighted_reconcile_rules(self) -> None:
        findings = [
            {
                "layer": "L2a",
                "rule_id": "GEOMETRY.BUTTON_SIZE",
                "severity": "P1",
                "evidence_type": "程序已证实",
                "element": {"dsl_id": "button"},
            },
            {
                "layer": "L2b",
                "rule_id": "RECONCILE.COLOR_DRIFT",
                "severity": "P2",
                "evidence_type": "程序已证实",
                "element": {"dsl_id": "root"},
            },
        ]
        score, evidence = _l2_score(
            findings,
            {"P0": 1.0, "P1": 0.25, "P2": 0.05},
            penalized_evidence_types={"程序已证实"},
        )
        self.assertLess(score, 1.0)
        self.assertEqual(
            evidence["unscored_l2_rule_ids"], ["RECONCILE.COLOR_DRIFT"]
        )

    def test_visual_candidate_blends_l2_and_gates_critical_geometry(self) -> None:
        finding = {
            "layer": "L2a",
            "rule_id": "GEOMETRY.TEXT_SQUASH",
            "severity": "P1",
            "evidence_type": "程序已证实",
            "element": {"dump_id": "title"},
        }
        config = Path(__file__).resolve().parents[1] / "configs" / "reward_visual_candidate.json"
        computer = RewardComputer(
            _FakeChecker(self.checker_root, findings=[finding]), config_path=config
        )
        audit = computer.compute(
            RewardRequest(
                sample_id="sample",
                solution_str=VALID_DSL,
                task_spec=TASK_SPEC,
                content_labels=CONTENT_LABELS,
                finish_reason="stop",
                completion_tokens=100,
                layout_path=Path("fixture.layout.json"),
            )
        )
        self.assertLess(audit.components["static_layout"].value, 1.0)
        self.assertGreater(audit.components["static_layout"].value, 0.0)
        self.assertEqual(audit.components["l2"].weight, 0.0)
        self.assertEqual(audit.score, 0.0)
        self.assertTrue(
            any(
                gate.name == "visual_integrity" and gate.passed is False
                for gate in audit.gates
            )
        )


class CheckerAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "design-check"
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "scripts" / "check_card.py").write_text("# fixture\n", encoding="utf-8")

    def test_exit_one_with_p0_is_a_successful_check(self) -> None:
        payload = {
            "findings": [{"severity": "P0", "rule_id": "STRUCT.X"}],
            "summary": {"total": 1, "p0": 1, "p1": 0, "p2": 0},
            "meta": {},
        }

        def runner(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(args[0], 1, json.dumps(payload), "")

        adapter = DesignCheckerAdapter(CheckerConfig(self.root), runner=runner)
        result = adapter.check("{}", sample_id="case", task_spec={"size": "2x2"})
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(len(result.findings), 1)

    def test_checker_receives_query_and_taskspec_via_case_directory(self) -> None:
        captured: dict[str, Any] = {}
        payload = {
            "findings": [],
            "summary": {"total": 0, "p0": 0, "p1": 0, "p2": 0},
            "meta": {},
        }

        def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            self.assertIn("--dir", command)
            self.assertNotIn("--dsl", command)
            case_dir = Path(command[command.index("--dir") + 1])
            captured["case_name"] = case_dir.name
            captured["query"] = (case_dir / "query.txt").read_text(encoding="utf-8").strip()
            captured["task_spec"] = json.loads(
                (case_dir / "task-spec.json").read_text(encoding="utf-8")
            )
            captured["dsl_exists"] = (case_dir / "card.genui.jsonl").is_file()
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

        adapter = DesignCheckerAdapter(CheckerConfig(self.root), runner=runner)
        adapter.check(
            "{}",
            sample_id="A-q8",
            task_spec={"size": "2x4", "userQuery": "检查天气场景"},
        )
        self.assertEqual(captured["query"], "检查天气场景")
        self.assertEqual(captured["task_spec"]["size"], "2x4")
        self.assertTrue(captured["dsl_exists"])
        self.assertEqual(captured["case_name"], "rl-A-q8-candidate")

    def test_namespaced_candidate_cannot_trigger_vendored_manual_verdict(self) -> None:
        sys.path.insert(0, str(VENDORED_CHECKER_ROOT))
        try:
            from packages.pkg_skeleton.layout_2x4 import _manual_verdict

            self.assertIsNotNone(_manual_verdict(types.SimpleNamespace(case_id="A-q8")))
            self.assertIsNone(
                _manual_verdict(types.SimpleNamespace(case_id="rl-A-q8-candidate"))
            )
            self.assertIsNone(
                _manual_verdict(types.SimpleNamespace(case_id="rl-q8-candidate"))
            )
        finally:
            sys.path.remove(str(VENDORED_CHECKER_ROOT))

    def test_l2_command_always_includes_delegated_rules_when_requested(self) -> None:
        payload = {
            "findings": [],
            "summary": {"total": 0, "p0": 0, "p1": 0, "p2": 0},
            "meta": {},
        }
        captured: dict[str, list[str]] = {}

        def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
            captured["command"] = command
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")

        layout = Path(self.temporary.name) / "card.layout.json"
        layout.write_text(
            json.dumps(
                {
                    "attributes": {"bundleName": "com.example.myapplication"},
                    "children": [
                        {
                            "attributes": {
                                "id": "root",
                                "type": "Column",
                                "bounds": "[0,0][560,560]",
                            },
                            "children": [
                                {
                                    "attributes": {
                                        "id": "title",
                                        "type": "Text",
                                        "bounds": "[42,42][300,100]",
                                    },
                                    "children": [],
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        adapter = DesignCheckerAdapter(CheckerConfig(self.root), runner=runner)
        adapter.check(
            "{}",
            sample_id="case",
            task_spec={"size": "2x2"},
            layout_path=layout,
            include_delegated=True,
        )
        self.assertIn("--include-delegated", captured["command"])

    def test_empty_l2_application_tree_is_rejected(self) -> None:
        layout = Path(self.temporary.name) / "empty.layout.json"
        layout.write_text(
            json.dumps(
                {
                    "attributes": {"bundleName": "com.example.myapplication"},
                    "children": [],
                }
            ),
            encoding="utf-8",
        )
        adapter = DesignCheckerAdapter(CheckerConfig(self.root))
        with self.assertRaises(CheckerExecutionError) as raised:
            adapter.check(
                "{}", sample_id="case", task_spec={"size": "2x2"}, layout_path=layout
            )
        self.assertEqual(raised.exception.kind, "incomplete_layout")
        self.assertTrue(raised.exception.retryable)

    def test_exit_two_retries_then_raises(self) -> None:
        attempts = 0

        def runner(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            nonlocal attempts
            attempts += 1
            return subprocess.CompletedProcess(args[0], 2, "", "failure")

        adapter = DesignCheckerAdapter(
            CheckerConfig(self.root, max_retries=1), runner=runner
        )
        with self.assertRaises(CheckerExecutionError) as raised:
            adapter.check("{}", sample_id="case", task_spec={"size": "2x2"})
        self.assertEqual(attempts, 2)
        self.assertEqual(raised.exception.kind, "checker_exit_2")

    def test_l2_desktop_dump_is_rejected_before_checker(self) -> None:
        layout = Path(self.temporary.name) / "desktop.layout.json"
        layout.write_text(
            json.dumps({"attributes": {"bundleName": "com.ohos.launcher"}, "children": []}),
            encoding="utf-8",
        )
        adapter = DesignCheckerAdapter(CheckerConfig(self.root))
        with self.assertRaises(CheckerExecutionError) as raised:
            adapter.check(
                "{}", sample_id="case", task_spec={"size": "2x2"}, layout_path=layout
            )
        self.assertEqual(raised.exception.kind, "wrong_layout_surface")
        self.assertTrue(raised.exception.retryable)


class L2PreparationTests(unittest.TestCase):
    def test_render_payload_has_viewport_then_three_a2ui_messages(self) -> None:
        a2ui = "\n".join(
            [
                json.dumps({"version": "v0.9", "createSurface": {}}),
                json.dumps({"version": "v0.9", "updateComponents": {}}),
                json.dumps({"version": "v0.9", "updateDataModel": {}}),
            ]
        )
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "render.json"
            write_render_payload(a2ui, size="2x2", output=output)
            payload = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(payload[0], {"__viewport__": "2x2"})
        self.assertEqual(len(payload), 4)

    def test_grouped_candidate_uses_group_taskspec_for_render_preparation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            input_file = root / "raw.jsonl"
            taskspec_file = root / "taskspec.json"
            output_dir = root / "prepared"
            input_file.write_text(
                json.dumps(
                    {
                        "id": "task--sample-000",
                        "groupId": "task",
                        "designCompactDsl": VALID_DSL,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            taskspec_file.write_text(
                json.dumps([{"id": "task", "taskSpec": TASK_SPEC}]),
                encoding="utf-8",
            )
            argv = [
                "render_l2_sample.py",
                "--input",
                str(input_file),
                "--taskspec-file",
                str(taskspec_file),
                "--output-dir",
                str(output_dir),
                "--limit",
                "1",
            ]
            with mock.patch.object(sys, "argv", argv):
                self.assertEqual(render_l2_main(), 0)
            manifest = json.loads(
                (output_dir / "render-sample-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["items"][0]["id"], "task--sample-000")
            self.assertEqual(manifest["items"][0]["group_id"], "task")


class ContentSchemaTests(unittest.TestCase):
    def test_json_schema_properties_and_array_items_match_converter_paths(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "properties": {
                        "forecast": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {"temp": {"type": "string"}},
                            },
                        }
                    },
                }
            },
        }
        self.assertTrue(_schema_has_path(schema, "/data/forecast/37/temp"))
        self.assertFalse(_schema_has_path(schema, "/data/forecast/37/unknown"))

    def test_concrete_list_schema_uses_the_requested_index(self) -> None:
        schema = {
            "data": {
                "forecast": [
                    {"temperature": {"type": "string"}},
                    {"condition": {"type": "string"}},
                ]
            }
        }
        self.assertTrue(_schema_has_path(schema, "/data/forecast/1/condition"))
        self.assertFalse(_schema_has_path(schema, "/data/forecast/0/condition"))
        self.assertFalse(_schema_has_path(schema, "/data/forecast/2/condition"))


class AuditTokenizerTests(unittest.TestCase):
    def test_counts_only_completion_without_special_tokens(self) -> None:
        class FakeTokenizer:
            def __call__(self, text: str, *, add_special_tokens: bool) -> dict[str, Any]:
                self.text = text
                self.add_special_tokens = add_special_tokens
                return {"input_ids": [7, 8, 9]}

        tokenizer = FakeTokenizer()
        self.assertEqual(_count_completion_tokens(tokenizer, "row{}"), 3)
        self.assertEqual(tokenizer.text, "row{}")
        self.assertFalse(tokenizer.add_special_tokens)


class CandidatePipelineTests(unittest.TestCase):
    def test_raw_only_cli_writes_auditable_rows_and_checks_source_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = root / "raw.jsonl"
            output = root / "output"
            raw.write_text(
                json.dumps(
                    {
                        "id": "task-1",
                        "groupId": "task-1",
                        "candidateIndex": 0,
                        "samplingMode": "legacy",
                        "sampling": {},
                        "size": "2x2",
                        "finishReason": "stop",
                        "completionTokens": 1,
                        "designCompactDsl": "dsl",
                        "producerCheckpoint": "checkpoint-v1",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                sys,
                "argv",
                [
                    "export_renderable_a2ui.py",
                    "--raw-input-file",
                    str(raw),
                    "--output-dir",
                    str(output),
                    "--raw-only",
                ],
            ):
                export_candidates_main()
            saved = json.loads(
                (output / "raw_compact_dsl.jsonl").read_text(encoding="utf-8")
            )
            self.assertEqual(saved["producerCheckpoint"], "checkpoint-v1")

            with mock.patch.object(
                sys,
                "argv",
                [
                    "export_renderable_a2ui.py",
                    "--raw-input-file",
                    str(raw),
                    "--taskspec-file",
                    str(root / "taskspec.json"),
                    "--output-dir",
                    str(root / "invalid-output"),
                    "--raw-only",
                ],
            ):
                with self.assertRaisesRegex(ValueError, "cannot be combined"):
                    export_candidates_main()

    def test_raw_only_filter_excludes_empty_and_length_truncated_candidates(self) -> None:
        def candidate(sample_id: str, text: str, finish_reason: str) -> dict[str, Any]:
            return {
                "id": sample_id,
                "designCompactDsl": text,
                "finishReason": finish_reason,
            }

        accepted, rejected = filter_auditable_raw_outputs(
            [
                candidate("valid", "  dsl  ", "stop"),
                candidate("empty", "  ", "stop"),
                candidate("truncated", "partial", "length"),
            ]
        )
        self.assertEqual([row["id"] for row in accepted], ["valid"])
        self.assertEqual(accepted[0]["designCompactDsl"], "dsl")
        self.assertEqual([row["id"] for row in rejected], ["empty", "truncated"])

    def test_collect_raw_outputs_preserves_group_and_candidate_metadata(self) -> None:
        class Completion:
            def __init__(self, text: str, token_ids: list[int]) -> None:
                self.text = text
                self.token_ids = token_ids
                self.finish_reason = "stop"

        class RequestOutput:
            outputs = [Completion("first", [1]), Completion("second", [2, 3])]

        rows = collect_raw_outputs(
            [{"id": "task-1", "size": "2x2"}],
            [RequestOutput()],
            sampling_mode="sample",
            expected_candidates=2,
            qualify_ids=True,
            sampling_metadata={"temperature": 0.7},
            producer_checkpoint="checkpoint-v1",
        )
        self.assertEqual(
            [row["id"] for row in rows],
            ["task-1--sample-000", "task-1--sample-001"],
        )
        self.assertEqual([row["groupId"] for row in rows], ["task-1", "task-1"])
        self.assertEqual([row["candidateIndex"] for row in rows], [0, 1])
        self.assertEqual([row["completionTokens"] for row in rows], [1, 2])
        self.assertEqual(
            [row["producerCheckpoint"] for row in rows],
            ["checkpoint-v1", "checkpoint-v1"],
        )
        unstamped = collect_raw_outputs(
            [{"id": "task-1", "size": "2x2"}],
            [RequestOutput()],
            sampling_mode="sample",
            expected_candidates=2,
            qualify_ids=True,
        )
        self.assertNotIn("producerCheckpoint", unstamped[0])

    def test_taskspec_rollout_inputs_and_reused_candidate_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            taskspec = root / "taskspec.json"
            prompt = root / "system.md"
            raw = root / "raw.jsonl"
            taskspec.write_text(
                json.dumps(
                    [
                        {
                            "id": "task-1",
                            "taskSpec": {
                                "size": "2x2",
                                "userQuery": "生成卡片",
                                "dataModelSchema": {},
                                "eventCandidates": [],
                                "assetCandidates": [],
                            },
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            prompt.write_text("只输出完整 DSL。", encoding="utf-8")
            inputs = read_taskspec_inputs(taskspec, prompt, None)
            self.assertEqual(inputs[0]["id"], "task-1")
            self.assertEqual(inputs[0]["messages"][0]["role"], "system")
            self.assertEqual(
                json.loads(inputs[0]["messages"][1]["content"])["size"], "2x2"
            )

            raw.write_text(
                json.dumps(
                    {
                        "id": "task-1--sample-000",
                        "groupId": "task-1",
                        "candidateIndex": 0,
                        "samplingMode": "sample",
                        "sampling": {"temperature": 0.7},
                        "size": "2x2",
                        "finishReason": "stop",
                        "completionTokens": 2,
                        "designCompactDsl": "dsl",
                        "producerCheckpoint": "checkpoint-v1",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                read_raw_outputs(raw)[0]["producerCheckpoint"], "checkpoint-v1"
            )
            with self.assertRaisesRegex(ValueError, "producerCheckpoint mismatch"):
                read_raw_outputs(raw, producer_checkpoint="checkpoint-v2")

            legacy = json.loads(raw.read_text(encoding="utf-8"))
            legacy.pop("producerCheckpoint")
            raw.write_text(json.dumps(legacy) + "\n", encoding="utf-8")
            self.assertEqual(
                read_raw_outputs(raw, producer_checkpoint="checkpoint-v1")[0][
                    "producerCheckpoint"
                ],
                "checkpoint-v1",
            )

    def test_group_analysis_checks_variance_without_enabling_training(self) -> None:
        def row(mode: str, index: int, score: float, tokens: int) -> dict[str, Any]:
            return {
                "sample_id": f"task-1--{mode}-{index:03d}",
                "group_id": "task-1",
                "sampling_mode": mode,
                "candidate_index": index,
                "score": score,
                "masked": False,
                "gates": [{"name": "conversion", "passed": True}],
                "components": {
                    "static_layout": {"value": score},
                    "efficiency": {
                        "value": 1.0,
                        "evidence": {"completion_tokens": tokens},
                    },
                },
            }

        report = analyze_groups(
            [
                row("greedy", 0, 0.7, 100),
                row("sample", 1, 0.9, 120),
                row("sample", 0, 0.5, 110),
            ],
            expected_samples=2,
        )
        self.assertTrue(report["summary"]["machine_gate_passed"])
        self.assertFalse(report["summary"]["ready_for_policy_update"])
        self.assertAlmostEqual(report["groups"][0]["score_range"], 0.4)
        self.assertAlmostEqual(
            report["groups"][0]["best_sampled_minus_greedy"], 0.2
        )

    def test_group_analysis_reports_missing_sample_structure(self) -> None:
        rows = [
            {
                "sample_id": "task-1--greedy-000",
                "group_id": "task-1",
                "sampling_mode": "greedy",
                "candidate_index": 0,
                "score": 0.8,
                "masked": False,
                "gates": [{"name": "conversion", "passed": True}],
                "components": {},
            }
        ]
        report = analyze_groups(rows, expected_samples=2)
        self.assertFalse(report["summary"]["machine_gate_passed"])
        self.assertEqual(report["summary"]["structure_error_groups"], ["task-1"])
        self.assertIn("expected 2 sampled candidates", report["groups"][0]["structure_errors"][0])

    def test_group_analysis_rejects_length_only_variance(self) -> None:
        rows = []
        for mode, index, score, tokens in (
            ("greedy", 0, 0.5, 100),
            ("sample", 0, 0.6, 110),
            ("sample", 1, 0.7, 120),
        ):
            rows.append(
                {
                    "sample_id": f"task-1--{mode}-{index:03d}",
                    "group_id": "task-1",
                    "sampling_mode": mode,
                    "candidate_index": index,
                    "score": score,
                    "masked": False,
                    "gates": [{"name": "conversion", "passed": True}],
                    "components": {
                        "static_layout": {"value": 1.0},
                        "style": {"value": 1.0},
                        "efficiency": {
                            "value": score,
                            "evidence": {"completion_tokens": tokens},
                        },
                    },
                }
            )
        report = analyze_groups(rows, expected_samples=2)
        self.assertFalse(report["summary"]["machine_gate_passed"])
        self.assertEqual(report["summary"]["visual_signal_fraction"], 0.0)
        self.assertTrue(report["summary"]["suspicious_reward_token_correlation"])

    def test_canary_rows_follow_reviewed_label_order(self) -> None:
        task_rows = [
            {
                "id": "two",
                "taskSpec": {
                    "userQuery": "two",
                    "size": "2x2",
                    "dataModelSchema": {},
                    "eventCandidates": [],
                    "assetCandidates": [],
                },
            },
            {
                "id": "one",
                "taskSpec": {
                    "userQuery": "one",
                    "size": "2x2",
                    "dataModelSchema": {},
                    "eventCandidates": [],
                    "assetCandidates": [],
                },
            },
        ]
        labels = [
            {"id": "one", "reviewed": True, "verification_status": "passed"},
            {"id": "two", "reviewed": True, "verification_status": "passed"},
        ]
        rows = build_canary_rows(
            task_rows=task_rows, label_rows=labels, system_prompt="system"
        )
        self.assertEqual([row["id"] for row in rows], ["one", "two"])
        self.assertEqual([message["role"] for message in rows[0]["messages"]], ["system", "user"])


class SourceContextRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        source = Path(__file__).resolve().parents[2] / "sft" / "data" / "source"
        task_rows = json.loads((source / "taskspec.json").read_text(encoding="utf-8"))
        cls.tasks = {row["id"]: row["taskSpec"] for row in task_rows}
        cls.compact_dsls = {
            row["id"]: row["designCompactDsl"]
            for raw_line in (source / "design_compact_dsl.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            if raw_line.strip()
            for row in [json.loads(raw_line)]
        }

    def test_known_array_and_event_cases_pass_context_validation(self) -> None:
        for sample_id in (
            "cmc-v16-q008",
            "cmc-v16-q009",
            "cmc-v16-q013",
            "cmc-v16-q014",
        ):
            with self.subTest(sample_id=sample_id):
                task_spec = self.tasks[sample_id]
                compact_dsl = self.compact_dsls[sample_id]
                card_spec = derive_card_spec(task_spec)
                validate_compact_dsl_context(
                    compact_dsl,
                    task_spec=task_spec,
                    card_spec=card_spec,
                )
                converted = convert_compact_dsl_to_a2ui(
                    compact_dsl,
                    size=task_spec["size"],
                    protocol_profile={"version": "v0.9"},
                )
                coverage = measure_content_coverage(
                    converted,
                    task_spec=task_spec,
                    requirements=ContentRequirements(),
                )
                self.assertEqual(
                    coverage.evidence["violations"],
                    {"paths": [], "assets": [], "events": []},
                )

    def test_event_normalization_does_not_allow_a_different_binding_path(self) -> None:
        sample_id = "cmc-v16-q013"
        task_spec = copy.deepcopy(self.tasks[sample_id])
        task_spec["eventCandidates"][0]["args"]["params"]["entityId"] = (
            "{{ ${/data/calendar/events/0/title} }}"
        )
        with self.assertRaisesRegex(
            CompactDslConversionError,
            "onClick is not present in TaskSpec.eventCandidates",
        ):
            validate_compact_dsl_context(
                self.compact_dsls[sample_id],
                task_spec=task_spec,
                card_spec=derive_card_spec(task_spec),
            )


if __name__ == "__main__":
    unittest.main()
