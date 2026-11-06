"""Unit tests for the feedback theme classification pipeline."""

import csv
from pathlib import Path

from src.analysis.theme_classifier import (
    THEME_CONTINUATION,
    THEME_INVESTMENT_UNDERSTANDING,
    THEME_PLATFORM_TRUST,
    THEME_UNCERTAIN,
    THEME_UNCERTAINTY,
    classify_survey_record,
    classify_text_record,
    run_theme_classification_pipeline,
)


def test_classify_survey_record_mapping():
    """Verify that survey responses map properly to themes with high confidence."""
    headers = [
        "response_id", "asset_type", "Have you started a mutual-fund SIP ?",
        "Was this your first mutual-fund SIP?", "What do you do when you feel unsure about your SIP?",
        "Have you ever changed your SIP amount after starting?", "Is your SIP currently active, paused, stopped, or reduced?",
        "Approximately how long have you been investing through SIPs?", "Why did you start your first SIP?",
        "How often do you check your SIP or mutual-fund investments?", "How do you usually feel when your SIP value goes down?",
        "What did you find most confusing after starting your SIP?", "Have you ever paused, reduced, stopped, or considered stopping your SIP?",
        "If you paused, reduced, stopped, or considered stopping, what led to that decision?",
        "What would make you more likely to continue your SIP for 12+ months?",
    ]
    sample_row = [
        "FORM_RESP_TEST", "mutual_fund", "Yes", "Yes", "Search on Google",
        "No", "Paused", "3–6 months", "Wealth creation", "Weekly", "Anxious",
        "Understanding market ups and downs", "Yes, I paused it",
        "Market fall or negative returns", "Clear explanation of short-term ups and downs",
    ]

    res = classify_survey_record(sample_row, headers)
    assert res.record_id == "FORM_RESP_TEST"
    assert res.source == "google_forms"
    assert res.primary_theme == THEME_UNCERTAINTY
    assert res.confidence == "high"
    assert "Market fall or negative returns" in res.supporting_evidence


def test_classify_text_record_ambiguous_marking():
    """Verify that vague or off-topic text without SIP keywords is marked uncertain."""
    res = classify_text_record(
        record_id="REV_TEST_01",
        source="test_source",
        text="App is okay I guess.",
        investor_status="tester",
    )
    assert res.primary_theme == THEME_UNCERTAIN
    assert res.confidence == "uncertain"
    assert "No domain-specific" in res.supporting_evidence


def test_classify_text_record_platform_trust():
    """Verify detection of autopay mandate and bank debit issues."""
    text = "My autopay mandate failed and the bank account got debited twice but money is stuck."
    res = classify_text_record(
        record_id="REV_TEST_02",
        source="test_source",
        text=text,
        investor_status="tester",
    )
    assert res.primary_theme == THEME_PLATFORM_TRUST
    assert res.confidence == "high"
    assert "autopay" in res.supporting_evidence or "mandate" in res.supporting_evidence


def test_pipeline_exclusions_and_counts():
    """Verify that pipeline excludes non-investors, deleted comments, and isolates stock SIP."""
    mf_records, stock_records, metrics = run_theme_classification_pipeline()

    # 1. Non-investor exclusion (8 excluded, 24 analyzed)
    assert metrics["source_counts"]["google_forms"] == 24
    survey_ids = [r.record_id for r in mf_records if r.source == "google_forms"]
    assert len(survey_ids) == 24

    # 2. Deleted reddit exclusion (3 excluded, 53 analyzed)
    assert metrics["source_counts"]["reddit_concerns"] == 53
    for r in mf_records:
        if r.source == "reddit_concerns":
            assert r.feedback_text not in ("[deleted]", "[removed]", "")

    # 3. Stock SIP segregation (7 records isolated)
    assert len(stock_records) == 7
    assert metrics["total_stock_sip_isolated"] == 7
    for s in stock_records:
        assert s.asset_type == "stock_sip"

    # Mutual fund feedback total
    assert metrics["total_mf_analyzed"] == 203
    assert len(mf_records) == 203


def test_pipeline_exports_and_report_exist():
    """Verify export files and summary markdown report are created."""
    mf_export = Path("data/exports/classified_mutual_fund_feedback.csv")
    stock_export = Path("data/exports/classified_stock_sip_feedback.csv")
    report_file = Path("reports/feedback_analysis_summary.md")

    assert mf_export.is_file() and mf_export.stat().st_size > 0
    assert stock_export.is_file() and stock_export.stat().st_size > 0
    assert report_file.is_file() and report_file.stat().st_size > 0


def test_regression_continue_securely_not_continuation():
    """Verify 'to continue securely' does not misclassify as SIP Continuation."""
    # Case 1: Device warning with upi not working
    res1 = classify_text_record(
        record_id="REG_SEC_01",
        source="google_play",
        text="There is a problem with the app, upi is not working. It says 'To continue securely, disconnect USB'.",
        investor_status="tester",
    )
    assert res1.primary_theme == THEME_PLATFORM_TRUST
    assert res1.primary_theme != THEME_CONTINUATION

    # Case 2: Standalone USB / security warning
    res2 = classify_text_record(
        record_id="REG_SEC_02",
        source="google_play",
        text="App shows error: to continue securely disconnect USB debugging.",
        investor_status="tester",
    )
    assert res2.primary_theme == THEME_PLATFORM_TRUST
    assert res2.primary_theme != THEME_CONTINUATION


def test_regression_groww_shuts_down_and_custody():
    """Verify sponsor safety and custody questions classify as Investment Literacy."""
    res = classify_text_record(
        record_id="REG_CUSTODY_01",
        source="reddit_concerns",
        text="Is it safe to keep large sums in Groww? What happens if Groww shuts down? Are mutual fund units held in AMC or Groww pool account?",
        investor_status="tester",
    )
    assert res.primary_theme == THEME_INVESTMENT_UNDERSTANDING
    assert "shuts down" in res.supporting_evidence or "pool account" in res.supporting_evidence


def test_regression_exit_load_fee_and_deduction_questions():
    """Verify exit-load, fee, and deduction questions classify as Investment Literacy rather than Platform Trust."""
    # Fee / deduction confusion during withdrawal
    res1 = classify_text_record(
        record_id="REG_FEE_01",
        source="google_play",
        text="There was a deduction on my mutual fund withdrawal and I cannot understand the fee.",
        investor_status="tester",
    )
    assert res1.primary_theme == THEME_INVESTMENT_UNDERSTANDING

    # Percentage / amount deduction query
    res2 = classify_text_record(
        record_id="REG_FEE_02",
        source="google_play",
        text="Why was 100 rupees deducted on withdrawal?",
        investor_status="tester",
    )
    assert res2.primary_theme == THEME_INVESTMENT_UNDERSTANDING

    # Exit load charges query
    res3 = classify_text_record(
        record_id="REG_FEE_03",
        source="google_play",
        text="What are the exit load charges and withdrawal fees when redeeming my mutual fund?",
        investor_status="tester",
    )
    assert res3.primary_theme == THEME_INVESTMENT_UNDERSTANDING

    # Stamp duty deduction explanation
    res4 = classify_text_record(
        record_id="REG_FEE_04",
        source="google_play",
        text="Taxes and stamp duty deductions were not clearly explained during withdrawal.",
        investor_status="tester",
    )
    assert res4.primary_theme == THEME_INVESTMENT_UNDERSTANDING

    # Conversely, a genuine bank auto-debit/mandate payment failure must remain Platform Trust
    res_tech = classify_text_record(
        record_id="REG_TECH_01",
        source="google_play",
        text="My SIP installment amount got deducted from HDFC bank, but Groww mutual fund portfolio shows awaiting payment for 4 days.",
        investor_status="tester",
    )
    assert res_tech.primary_theme == THEME_PLATFORM_TRUST


def test_regression_unrelated_fno_and_derivatives_filtered():
    """Verify off-topic F&O and derivative comments are isolated as Uncertain / Ambiguous."""
    off_topic_samples = [
        "Lost 20k in Nifty 50 call options today, scalper terminal chart lagging.",
        "Lost money in Bank Nifty options, chart lagged badly.",
        "Banknifty options premium stopped updating during expiry.",
        "Bought 22000 CE call and Groww failed order execution.",
        "App is very laggy while trading in FNO intraday.",
        "Option chain is not loading properly on expiry day.",
    ]
    for idx, text in enumerate(off_topic_samples):
        res = classify_text_record(
            record_id=f"REG_FNO_{idx:02d}",
            source="google_play",
            text=text,
            investor_status="tester",
        )
        assert res.primary_theme == THEME_UNCERTAIN
        assert "Off-topic F&O or derivatives" in res.supporting_evidence

    # Verify that legitimate mutual fund SIP feedback mentioning index funds is NOT falsely flagged
    res_mf = classify_text_record(
        record_id="REG_MF_INDEX_01",
        source="google_play",
        text="I have a monthly mutual fund SIP in Nifty 50 index fund, but market fall is causing negative returns.",
        investor_status="tester",
    )
    assert res_mf.primary_theme == THEME_UNCERTAINTY

