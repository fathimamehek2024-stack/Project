"""Unit tests for survey inspection and PII audit scripts."""

import csv
from pathlib import Path

from src.collectors.audit_survey_pii import audit_survey_pii
from src.collectors.inspect_survey_structure import inspect_survey_csv


def test_inspect_survey_csv_nonexistent(tmp_path: Path):
    """Verify that a nonexistent file returns proper error metadata."""
    res = inspect_survey_csv(tmp_path / "missing.csv")
    assert res["exists"] is False
    assert res["row_count"] == 0
    assert "File not found" in res["error"]


def test_inspect_survey_csv_valid_with_duplicates(tmp_path: Path):
    """Verify row, column, and duplicate counting."""
    csv_file = tmp_path / "survey_test.csv"
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Q1", "Q2", "Q3"])
        writer.writerow(["Yes", "Active", "Growth"])
        writer.writerow(["Yes", "Active", "Growth"])  # Duplicate
        writer.writerow(["No", "Paused", "Market drop"])

    res = inspect_survey_csv(csv_file)
    assert res["exists"] is True
    assert res["row_count"] == 3
    assert res["column_count"] == 3
    assert res["unique_count"] == 2
    assert res["duplicate_count"] == 1


def test_audit_survey_pii_clean(tmp_path: Path):
    """Verify audit on a clean anonymous dataset."""
    csv_file = tmp_path / "clean_survey.csv"
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Question 1", "Question 2"])
        writer.writerow(["I paused my SIP because of mandate failure", "Groww app was confusing"])

    res = audit_survey_pii(csv_file)
    assert res["risk_level"] == "LOW / CLEAN (Anonymous Survey Data)"
    assert res["pii_columns"] == []
    assert res["found_emails"] == []


def test_audit_survey_pii_exposed(tmp_path: Path):
    """Verify detection of emails and sensitive headers."""
    csv_file = tmp_path / "pii_survey.csv"
    with open(csv_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Email Address", "Feedback"])
        writer.writerow(["2026-10-27 10:00:00", "test.user@example.com", "Good app"])

    res = audit_survey_pii(csv_file)
    assert "HIGH RISK" in res["risk_level"]
    assert "Email Address" in res["pii_columns"]
    assert "test.user@example.com" in res["found_emails"]
