"""Unit tests for feedback_validator module."""

import csv
from pathlib import Path

from src.collectors.feedback_validator import (
    DEFAULT_CSV_PATH,
    REQUIRED_COLUMNS,
    validate_feedback_csv,
)


def test_default_template_is_valid():
    """Verify that the repository's default feedback template passes validation."""
    result = validate_feedback_csv(DEFAULT_CSV_PATH)
    assert result["file_exists"] is True
    assert result["is_valid"] is True
    assert result["missing_columns"] == []
    assert result["record_count"] == 0
    assert "Success" in result["message"]


def test_file_not_found(tmp_path: Path):
    """Verify behavior when the feedback CSV file does not exist."""
    missing_path = tmp_path / "does_not_exist.csv"
    result = validate_feedback_csv(missing_path)

    assert result["file_exists"] is False
    assert result["is_valid"] is False
    assert result["record_count"] == 0
    assert "does not exist" in result["message"]


def test_missing_required_columns(tmp_path: Path):
    """Verify that validator flags missing required columns."""
    incomplete_csv = tmp_path / "incomplete.csv"
    incomplete_headers = ["feedback_id", "source", "feedback_text"]  # Missing 5 columns

    with open(incomplete_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(incomplete_headers)

    result = validate_feedback_csv(incomplete_csv)
    assert result["file_exists"] is True
    assert result["is_valid"] is False
    assert "sip_behavior" in result["missing_columns"]
    assert "collection_method" in result["missing_columns"]
    assert len(result["missing_columns"]) == 5


def test_valid_csv_with_records(tmp_path: Path):
    """Verify that validator correctly counts valid data records."""
    sample_csv = tmp_path / "sample_feedback.csv"

    with open(sample_csv, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(REQUIRED_COLUMNS)
        writer.writerow([
            "FB001",
            "Google Play",
            "https://play.google.com/store/apps/details?id=com.nextbillion.groww",
            "2026-01-15",
            "Stopped my SIP after 3 months because mandate failed repeatedly.",
            "0-3 months",
            "stop",
            "manual_entry",
        ])
        writer.writerow([
            "FB002",
            "Reddit",
            "https://reddit.com/r/IndiaInvestments/comments/example",
            "2026-02-10",
            "Market went down so I paused my SIP for a couple of months.",
            "3-6 months",
            "pause",
            "manual_entry",
        ])

    result = validate_feedback_csv(sample_csv)
    assert result["file_exists"] is True
    assert result["is_valid"] is True
    assert result["missing_columns"] == []
    assert result["record_count"] == 2
    assert "Current records: 2" in result["message"]


def test_empty_file(tmp_path: Path):
    """Verify that a completely empty file is marked invalid."""
    empty_csv = tmp_path / "empty.csv"
    empty_csv.touch()

    result = validate_feedback_csv(empty_csv)
    assert result["file_exists"] is True
    assert result["is_valid"] is False
    assert "empty" in result["message"].lower()
