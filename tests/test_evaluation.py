"""Tests for Evaluation and Comparison Module."""

from __future__ import annotations

from pathlib import Path
import tempfile

import pytest

from src.analysis.llm_classifier import MockLLMClient
from src.evaluation.evaluate_classifier import (
    BenchmarkItem,
    generate_evaluation_markdown,
    load_benchmark,
    run_evaluation,
)


def test_load_benchmark():
    """Verify that benchmark dataset loads 25 valid records."""
    benchmark_path = Path("data/evaluation/benchmark_samples.csv")
    items = load_benchmark(benchmark_path)
    assert len(items) == 25
    first = items[0]
    assert first.record_id == "BENCH_001"
    assert first.source == "google_play"
    assert first.expected_theme != ""
    assert first.feedback_text != ""


def test_load_benchmark_missing_file_raises():
    """Verify FileNotFoundError is raised when file does not exist."""
    with pytest.raises(FileNotFoundError):
        load_benchmark(Path("non_existent_benchmark.csv"))


def test_run_evaluation_metrics():
    """Verify evaluation calculations and metric boundaries."""
    client = MockLLMClient()
    results, metrics = run_evaluation(
        benchmark_path=Path("data/evaluation/benchmark_samples.csv"),
        llm_client=client,
    )
    assert len(results) == 25
    assert metrics["total_evaluated"] == 25
    assert 0 <= metrics["rule_accuracy"] <= 100
    assert 0 <= metrics["llm_accuracy"] <= 100
    assert 0 <= metrics["agreement_rate"] <= 100
    assert metrics["uncertain_flagged"] >= 0


def test_generate_evaluation_markdown(tmp_path: Path):
    """Verify markdown report generation produces required headings and content."""
    client = MockLLMClient()
    results, metrics = run_evaluation(
        benchmark_path=Path("data/evaluation/benchmark_samples.csv"),
        llm_client=client,
    )
    report_file = tmp_path / "test_report.md"
    generate_evaluation_markdown(report_file, results, metrics)

    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "# Classifier Evaluation & Disagreement Report" in content
    assert "Executive Summary & Comparative Metrics" in content
    assert "Disagreement & Edge Case Analysis" in content
    assert "Key Takeaways for Product Management" in content


def test_holdout_dataset_loading_and_evaluation():
    """Verify that independent holdout dataset loads 20 records and evaluates properly."""
    holdout_path = Path("data/evaluation/holdout_samples.csv")
    assert holdout_path.exists()
    items = load_benchmark(holdout_path)
    assert len(items) == 20

    client = MockLLMClient()
    results, metrics = run_evaluation(holdout_path, client)
    assert len(results) == 20
    assert metrics["total_evaluated"] == 20
    # Rule-based accuracy on unseen holdout should be at least 80%
    assert metrics["rule_accuracy"] >= 80.0
    assert 0 <= metrics["llm_accuracy"] <= 100.0

