"""Unit tests for the data cleaning and standardisation pipeline."""

import csv
from pathlib import Path

from src.processing.clean_feedback import (
    clean_google_form_responses,
    clean_playstore_reviews,
    clean_reddit_discussions,
    run_all_cleaning,
)


def test_clean_google_form_responses(tmp_path: Path):
    """Verify that Google Forms responses preserve all 32 rows and report duplicates."""
    out_file = tmp_path / "survey_cleaned.csv"
    report = clean_google_form_responses(
        input_path="data/raw/google_form_sip_responses.csv",
        output_path=out_file,
    )

    assert report.original_rows == 32
    assert report.duplicate_rows == 7
    assert report.rows_removed == 0
    assert report.final_rows == 32
    assert out_file.exists()

    with open(out_file, mode="r", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
    headers = reader[0]
    rows = reader[1:]

    assert headers[0] == "response_id"
    assert headers[1] == "asset_type"
    assert len(rows) == 32
    assert rows[0][0] == "FORM_RESP_001"
    assert rows[0][1] == "mutual_fund"


def test_clean_playstore_reviews_dedup_and_anonymisation(tmp_path: Path):
    """Verify that Google Play cleaner removes 5x pagination duplicates and anonymises users."""
    out_file = tmp_path / "playstore_b1_cleaned.csv"
    report = clean_playstore_reviews(
        input_path="data/raw/playstore_groww_reviews_batch1.csv",
        output_path=out_file,
        batch_name="Test Batch 1",
        id_prefix="GROWW_REV_TEST",
    )

    assert report.original_rows == 530
    assert report.duplicate_rows == 424
    assert report.rows_removed == 424
    assert report.final_rows == 106
    assert out_file.exists()

    with open(out_file, mode="r", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
    headers = reader[0]
    rows = reader[1:]

    assert headers[0] == "review_id"
    assert headers[1] == "reviewer_id"
    assert "User Name" not in headers
    assert len(rows) == 106

    # Verify anonymised IDs
    for r in rows:
        assert r[1].startswith("ANON_PLAYSTORE_USER_")


def test_clean_reddit_discussions_asset_type_separation(tmp_path: Path):
    """Verify that Reddit cleaner removes usernames and tags asset types cleanly."""
    out_stock = tmp_path / "stock_sip_cleaned.csv"
    report_stock = clean_reddit_discussions(
        input_path="data/raw/reddit_groww_stock_sip.csv",
        output_path=out_stock,
        dataset_name="Test Stock SIP",
        asset_type="stock_sip",
        id_prefix="TEST_STOCK",
    )

    assert report_stock.original_rows == 7
    assert report_stock.final_rows == 7
    assert out_stock.exists()

    with open(out_stock, mode="r", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
    headers = reader[0]
    rows = reader[1:]

    assert headers[3] == "author_id"
    assert "author" not in headers
    assert headers[-1] == "asset_type"

    for r in rows:
        assert r[3].startswith("ANON_REDDITOR_")
        assert r[-1] == "stock_sip"  # Kept separate from mutual funds


def test_no_missing_values_invented(tmp_path: Path):
    """Verify that empty survey fields are not imputed or hallucinated."""
    out_file = tmp_path / "survey_empty_check.csv"
    clean_google_form_responses(
        input_path="data/raw/google_form_sip_responses.csv",
        output_path=out_file,
    )

    with open(out_file, mode="r", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
    rows = reader[1:]

    # For respondents who answered 'No' to Q1, questions 2-13 must remain empty strings
    non_investor_rows = [r for r in rows if r[2].strip() == "No"]
    assert len(non_investor_rows) == 8
    for r in non_investor_rows:
        # Columns index 3 to 14 are Q2 to Q13
        for cell in r[3:]:
            assert cell == ""  # Zero invented or imputed values


def test_run_all_cleaning_pipeline():
    """Verify that the full cleaning pipeline executes and writes all 5 processed files."""
    reports = run_all_cleaning()
    assert len(reports) == 5

    expected_processed_files = [
        Path("data/processed/google_form_sip_responses_cleaned.csv"),
        Path("data/processed/playstore_groww_reviews_batch1_cleaned.csv"),
        Path("data/processed/playstore_groww_reviews_batch2_cleaned.csv"),
        Path("data/processed/reddit_groww_concerns_cleaned.csv"),
        Path("data/processed/reddit_groww_stock_sip_cleaned.csv"),
    ]

    for p in expected_processed_files:
        assert p.is_file()
        assert p.stat().st_size > 0
