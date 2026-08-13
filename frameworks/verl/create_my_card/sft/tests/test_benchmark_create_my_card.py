"""Tests for CreateMyCard benchmark report aggregation."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from benchmark_create_my_card import (  # noqa: E402
    BenchmarkRow,
    build_benchmark_report,
    classify_failure,
    format_markdown_report,
    write_markdown_report,
    write_report,
)


class BenchmarkCreateMyCardTests(unittest.TestCase):
    def test_build_benchmark_report_summarizes_quality_latency_and_tokens(self) -> None:
        rows = [
            BenchmarkRow(
                sample_id="ok-1",
                finish_reason="stop",
                prompt_tokens=100,
                completion_tokens=20,
                latency_ms=1000.0,
                ok=True,
            ),
            BenchmarkRow(
                sample_id="ok-2",
                finish_reason="stop",
                prompt_tokens=200,
                completion_tokens=40,
                latency_ms=2000.0,
                ok=True,
            ),
            BenchmarkRow(
                sample_id="bad-1",
                finish_reason="length",
                prompt_tokens=150,
                completion_tokens=64,
                latency_ms=3000.0,
                ok=False,
                error_type="truncated",
                error="generation reached max token length",
            ),
        ]

        report = build_benchmark_report(
            rows,
            model_path="/models/card-sft",
            input_file="/data/test.parquet",
            tensor_parallel_size=8,
            max_model_len=4096,
            max_new_tokens=1536,
            total_wall_ms=6500.0,
            model_load_ms=2500.0,
        )
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_file = Path(tmp_dir) / "benchmark_report.json"
            write_report(report, output_file)
            saved_report = json.loads(output_file.read_text(encoding="utf-8"))

        self.assertEqual(report["quality"]["total"], 3)
        self.assertEqual(report["quality"]["successRate"], 2 / 3)
        self.assertEqual(report["quality"]["failureCounts"], {"truncated": 1})
        self.assertEqual(report["latencyMs"]["p50"], 2000.0)
        self.assertEqual(report["latencyMs"]["p95"], 3000.0)
        self.assertEqual(report["tokens"]["completion"]["max"], 64)
        self.assertEqual(report["throughput"]["successfulRequestsPerSecond"], 2 / 6.5)
        self.assertEqual(report["modelLoadMs"], 2500.0)
        self.assertEqual(saved_report["modelPath"], "/models/card-sft")

    def test_format_markdown_report_includes_human_readable_units(self) -> None:
        rows = [
            BenchmarkRow(
                sample_id="ok-1",
                finish_reason="stop",
                prompt_tokens=100,
                completion_tokens=20,
                latency_ms=1000.0,
                ok=True,
            ),
            BenchmarkRow(
                sample_id="bad-1",
                finish_reason="length",
                prompt_tokens=150,
                completion_tokens=64,
                latency_ms=3000.0,
                ok=False,
                error_type="truncated",
                error="generation reached max token length",
            ),
        ]
        report = build_benchmark_report(
            rows,
            model_path="/models/card-sft",
            input_file="/data/test.parquet",
            tensor_parallel_size=8,
            max_model_len=4096,
            max_new_tokens=1536,
            total_wall_ms=4000.0,
            model_load_ms=2500.0,
        )

        markdown = format_markdown_report(report, rows)
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_file = Path(tmp_dir) / "benchmark_report.md"
            write_markdown_report(markdown, output_file)
            saved_markdown = output_file.read_text(encoding="utf-8")

        self.assertIn("# CreateMyCard Benchmark Report", markdown)
        self.assertIn("| Model load | 2500.00 ms |", markdown)
        self.assertIn("| Success rate | 50.00% |", markdown)
        self.assertIn("| Request throughput | 0.50 req/s |", markdown)
        self.assertIn("| Completion token throughput | 21.00 tok/s |", markdown)
        self.assertIn("| Prompt tokens p50 | 100.00 tokens |", markdown)
        self.assertIn("| Prompt tokens p95 | 150.00 tokens |", markdown)
        self.assertIn("| `bad-1` | FAIL | length | 150 tokens | 64 tokens | 3000.00 ms | truncated |", markdown)
        self.assertEqual(saved_markdown, markdown)

    def test_classify_failure_prefers_actionable_categories(self) -> None:
        self.assertEqual(
            classify_failure("length", "", None),
            ("truncated", "generation reached max token length"),
        )
        self.assertEqual(
            classify_failure("stop", "   ", None),
            ("empty", "model generated an empty Design Compact DSL"),
        )
        self.assertEqual(
            classify_failure("stop", "dsl", ValueError("bad binding")),
            ("conversion_error", "bad binding"),
        )


if __name__ == "__main__":
    unittest.main()
