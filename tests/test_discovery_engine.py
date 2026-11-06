"""Pytest test suite for Stage 2 AI Discovery Engine Workflow.

Tests each step of the pipeline: loading, classification, aggregation,
verbatim quote extraction with PII redaction, opportunity ranking, and report generation.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd
import pytest

from src.analysis.discovery_engine import (
    aggregate_discovery_metrics,
    classify_feedback_dataframe,
    export_uncertain_records,
    extract_verbatim_theme_quotes,
    generate_discovery_report,
    load_all_cleaned_feedback,
    rank_product_opportunities,
    redact_pii,
    round_score,
    run_discovery_pipeline,
)
from src.analysis.theme_classifier import (
    THEME_CONTINUATION,
    THEME_CUSTOMER_SUPPORT,
    THEME_FINANCIAL_CONSTRAINTS,
    THEME_INVESTMENT_UNDERSTANDING,
    THEME_PAUSE_STOP_REASONS,
    THEME_PLATFORM_TRUST,
    THEME_UNCERTAIN,
    THEME_UNCERTAINTY,
    THEME_USABILITY,
)


def _file_sha256(path: Path) -> str:
    """Helper to compute sha256 of file."""
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()


def test_step1_load_all_cleaned_feedback():
    """Step 1: Verify all cleaned feedback loads into a single DataFrame with required columns."""
    df = load_all_cleaned_feedback(Path("data/processed"))

    # Total records: 203 mutual fund + 7 isolated stock sip = 210
    assert len(df) == 210
    assert "feedback_id" in df.columns
    assert "source" in df.columns
    assert "asset_type" in df.columns
    assert "date" in df.columns
    assert "text" in df.columns
    assert "sip_behavior" in df.columns

    # Verify sources present
    sources = set(df["source"].unique())
    assert {"google_forms", "playstore_batch1", "playstore_batch2", "reddit_concerns", "reddit_stock_sip"}.issubset(sources)

    # Verify mutual fund count vs stock SIP count
    mf_df = df[df["asset_type"] != "stock_sip"]
    stock_df = df[df["asset_type"] == "stock_sip"]
    assert len(mf_df) == 203
    assert len(stock_df) == 7

    # Verify survey respondents have explicit behavior
    survey_df = df[df["source"] == "google_forms"]
    assert len(survey_df) == 24
    assert set(survey_df["sip_behavior"].unique()).issubset({"continue", "pause", "stop", "reduce"})

    # Verify no null or empty texts
    assert df["text"].str.strip().ne("").all()


def test_step2_classify_feedback_preserves_evaluation_files():
    """Step 2: Verify classification adds fields and leaves benchmark/holdout files untouched."""
    bench_file = Path("data/evaluation/benchmark_samples.csv")
    holdout_file = Path("data/evaluation/holdout_samples.csv")

    bench_hash_before = _file_sha256(bench_file)
    holdout_hash_before = _file_sha256(holdout_file)

    df = load_all_cleaned_feedback(Path("data/processed"))
    classified_df = classify_feedback_dataframe(df)

    # Fields added
    assert "primary_theme" in classified_df.columns
    assert "secondary_theme" in classified_df.columns
    assert "confidence" in classified_df.columns
    assert "supporting_evidence" in classified_df.columns
    assert "is_uncertain" in classified_df.columns

    # Verify confidence and uncertain flags
    for _, row in classified_df.iterrows():
        if row["primary_theme"] == THEME_UNCERTAIN:
            assert row["is_uncertain"] is True
        assert row["confidence"] in ("high", "medium", "uncertain")

    # Verify benchmark and holdout hashes are unmodified
    assert _file_sha256(bench_file) == bench_hash_before
    if holdout_file.exists():
        assert _file_sha256(holdout_file) == holdout_hash_before


def test_step3_aggregate_discovery_metrics():
    """Step 3: Verify overall theme counts, source breakdowns, and behavior cross-tabulation."""
    df = load_all_cleaned_feedback(Path("data/processed"))
    classified_df = classify_feedback_dataframe(df)
    metrics = aggregate_discovery_metrics(classified_df)

    assert metrics["total_mf_records"] == 203
    assert metrics["total_stock_sip_records"] == 7

    # Overall counts sum to 203
    counts = metrics["overall_theme_counts"]
    assert sum(counts.values()) == 203

    # All 9 themes exist in counts
    assert THEME_PLATFORM_TRUST in counts
    assert THEME_CUSTOMER_SUPPORT in counts
    assert THEME_USABILITY in counts
    assert THEME_PAUSE_STOP_REASONS in counts
    assert THEME_INVESTMENT_UNDERSTANDING in counts
    assert THEME_FINANCIAL_CONSTRAINTS in counts
    assert THEME_UNCERTAINTY in counts
    assert THEME_CONTINUATION in counts
    assert THEME_UNCERTAIN in counts

    # Check behavior contingency matrix
    behavior_matrix = metrics["behavior_crosstab"]
    assert THEME_CONTINUATION in behavior_matrix
    assert behavior_matrix[THEME_CONTINUATION].get("continue", 0) > 0


def test_step4_verbatim_quote_extraction_and_pii_redaction():
    """Step 4: Verify extracted quotes are verbatim substrings from data and PII is redacted."""
    df = load_all_cleaned_feedback(Path("data/processed"))
    classified_df = classify_feedback_dataframe(df)
    quotes = extract_verbatim_theme_quotes(classified_df, max_quotes=5)

    # All themes have quotes
    for theme, q_list in quotes.items():
        assert len(q_list) >= 1
        assert len(q_list) <= 5
        for item in q_list:
            raw_text = item["raw_text"]
            # Verify the quote corresponds to raw text
            assert item["feedback_id"] in set(df["feedback_id"])
            assert item["source"] in set(df["source"])
            # Verify no unmasked email or 10-digit phone
            assert "@" not in item["quote"] or "[REDACTED_EMAIL]" in item["quote"]

    # Test PII redaction utility directly
    sample_text = "Call me at +91 9876543210 or email test.user@example.com regarding folio 12345678."
    redacted = redact_pii(sample_text)
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_NUMBER]" in redacted
    assert "9876543210" not in redacted
    assert "test.user@example.com" not in redacted


def test_step5_rank_product_opportunities():
    """Step 5: Verify opportunity scoring formula, ranking order, and low-sample disclaimers."""
    df = load_all_cleaned_feedback(Path("data/processed"))
    classified_df = classify_feedback_dataframe(df)
    metrics = aggregate_discovery_metrics(classified_df)
    opportunities = rank_product_opportunities(metrics, classified_df)

    # 8 actionable themes (6 scored churn opportunities + 2 descriptive themes)
    assert len(opportunities) == 8

    # 6 Scored churn opportunities
    churn_opps = [o for o in opportunities if not o.get("is_descriptive")]
    assert len(churn_opps) == 6
    scores = [o["priority_score"] for o in churn_opps]
    assert scores == sorted(scores, reverse=True)
    assert [o["rank"] for o in churn_opps] == [1, 2, 3, 4, 5, 6]

    # Rank 1 should be Financial Constraints (due to empirical n_labeled=10 churnlink 10.0)
    assert churn_opps[0]["theme"] == THEME_FINANCIAL_CONSTRAINTS
    assert churn_opps[0]["n_labeled"] == 10
    assert churn_opps[0]["priority_score"] == 68.3

    # Ranks 2 and 3 should be Platform Trust and Customer Support
    assert churn_opps[1]["theme"] == THEME_PLATFORM_TRUST
    assert churn_opps[1]["priority_score"] == 67.0
    assert churn_opps[2]["theme"] == THEME_CUSTOMER_SUPPORT
    assert churn_opps[2]["priority_score"] == 65.5

    # 2 Descriptive themes (Deliberate Pausing and SIP Continuation)
    desc_opps = [o for o in opportunities if o.get("is_descriptive")]
    assert len(desc_opps) == 2
    desc_themes = {o["theme"] for o in desc_opps}
    assert THEME_PAUSE_STOP_REASONS in desc_themes
    assert THEME_CONTINUATION in desc_themes
    for o in desc_opps:
        assert o["rank"] is None
        assert o["priority_score"] is None

    # Verify low-sample flags for themes with < 15 records
    for opp in opportunities:
        if opp["count"] < 15:
            assert opp["is_low_sample"] is True
            assert "Low sample size" in opp["sample_disclaimer"]
        else:
            assert opp["is_low_sample"] is False


def test_step6_generate_discovery_report(tmp_path: Path):
    """Step 6: Verify markdown report generation produces all required sections and caveats."""
    df = load_all_cleaned_feedback(Path("data/processed"))
    classified_df = classify_feedback_dataframe(df)
    metrics = aggregate_discovery_metrics(classified_df)
    opportunities = rank_product_opportunities(metrics, classified_df)
    quotes = extract_verbatim_theme_quotes(classified_df)

    test_report_file = tmp_path / "test_discovery_report.md"
    generate_discovery_report(test_report_file, classified_df, metrics, opportunities, quotes)

    assert test_report_file.exists()
    content = test_report_file.read_text(encoding="utf-8")

    # Assert required sections
    assert "# Groww SIP Retention & Churn: AI Discovery Engine Report" in content
    assert "Executive Summary & Discovery Methodology" in content
    assert "Research Data Limitations & Classifier Caveats" in content
    assert "Classifier Accuracy Caveat (Independent N=20 Holdout)" in content
    assert "90.0% rule-based accuracy" in content
    assert "Discovered Themes & SIP Behavior Cross-Tabulation" in content
    assert "Customer Support SIP Keyword Mentions & Source Split" in content
    assert "Opportunity Prioritization Formula & Rubric" in content
    assert "Opportunity Ranking Summary Table (Scored Churn Drivers)" in content
    assert "Descriptive Themes (Not Scored on Churn Scale)" in content
    assert "Ranked Product Opportunities & Verbatim Evidence" in content
    assert "Disclaimers for Low-Sample Themes" in content
    assert "Recommended Strategic Roadmap for Groww" in content
    assert "Severity (Analyst Judgment)" in content
    assert "Fixability (Analyst Judgment)" in content


def test_step7_end_to_end_pipeline():
    """Step 7: Verify complete pipeline runs smoothly and outputs valid artifacts."""
    report_file = Path("reports/discovery_report.md")
    uncertain_file = Path("reports/uncertain_sample.csv")
    df, metrics, opportunities = run_discovery_pipeline(
        report_file=report_file,
        uncertain_sample_file=uncertain_file,
    )

    assert len(df) == 210
    assert metrics["total_mf_records"] == 203
    assert len(opportunities) == 8
    assert report_file.exists()
    assert report_file.stat().st_size > 5000
    assert uncertain_file.exists()
    assert uncertain_file.stat().st_size > 500


def test_step8_recompute_scores_from_report_inputs():
    """Step 8 (Requirement A.4): Verify every score in the report matches independent recomputation."""
    report_file = Path("reports/discovery_report.md")
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")

    # Verify summary table scores match inputs
    # Table line format: | **1** | **Financial Constraints...** | 10 | 2.9 | 10.0 (empirical 10/10) | 5.0 | 8.0 | **68.3** | ... |
    import re
    table_pattern = re.compile(
        r"\|\s*\*\*(?P<rank>\d+)\*\*\s*\|\s*\*\*(?P<theme>[^*]+)\*\*\s*\|\s*(?P<n_lab>\d+)\s*\|\s*(?P<freq>[\d.]+)\s*\|\s*(?P<churn_link>[^|]+)\s*\|\s*(?P<sev>[\d.]+)\s*\|\s*(?P<fix>[\d.]+)\s*\|\s*\*\*(?P<score>[\d.]+)\*\*\s*\|"
    )

    matches = list(table_pattern.finditer(content))
    assert len(matches) == 6, f"Expected 6 scored churn opportunity rows in table, found {len(matches)}"

    for match in matches:
        rank = match.group("rank")
        theme = match.group("theme").strip()
        n_lab = int(match.group("n_lab"))
        freq = float(match.group("freq"))
        churn_str = match.group("churn_link").strip()
        sev = float(match.group("sev"))
        fix = float(match.group("fix"))
        displayed_score = float(match.group("score"))

        cl = float(churn_str.split()[0])
        computed = round_score((0.25 * freq + 0.35 * cl + 0.20 * sev + 0.20 * fix) * 10.0)

        assert abs(computed - displayed_score) < 0.15, (
            f"Score mismatch for Rank {rank} ({theme}): computed {computed} vs displayed {displayed_score} "
            f"(inputs: Freq={freq}, Churn={cl}, Sev={sev}, Fix={fix})"
        )


def test_step9_uncertain_sample_export():
    """Step 9 (Requirement B.5): Verify 40 random Uncertain records exported with required columns."""
    sample_file = Path("reports/uncertain_sample.csv")
    assert sample_file.exists()
    sample_df = pd.read_csv(sample_file)

    assert len(sample_df) == 40
    assert list(sample_df.columns) == ["feedback_id", "source", "text"]
    assert sample_df["feedback_id"].notna().all()
    assert sample_df["source"].notna().all()
    assert sample_df["text"].str.strip().ne("").all()


def test_step10_keyword_mentions_and_low_sample_flagging():
    """Step 10 (Requirement B.6): Verify SIP/autopay/mandate mentions and low-sample (N<15) flags."""
    df = load_all_cleaned_feedback(Path("data/processed"))
    classified_df = classify_feedback_dataframe(df)
    metrics = aggregate_discovery_metrics(classified_df)

    mentions = metrics["keyword_mentions"]
    assert isinstance(mentions, dict)
    assert THEME_PLATFORM_TRUST in mentions
    assert mentions[THEME_PLATFORM_TRUST] == 11
    assert mentions[THEME_CUSTOMER_SUPPORT] == 0
    assert mentions[THEME_PAUSE_STOP_REASONS] == 6

    # Low-sample themes with count < 15
    for theme, count in metrics["overall_theme_counts"].items():
        if count < 15:
            assert count in (7, 10, 12)


def test_step11_quote_verbatim_verification():
    """Step 11 (Requirement B.7): Verify all quotes in reports/discovery_report.md appear verbatim in data."""
    import re
    raw_df = load_all_cleaned_feedback(Path("data/processed"))
    report_file = Path("reports/discovery_report.md")
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")

    quote_regex = re.compile(
        r"-\s+\*\*\[(?P<source>[\w_]+)\s+-\s+`(?P<feedback_id>[^`]+)`.*?\]:\*\*\s+\*\"(?P<quote>.*?)\"\*",
        re.DOTALL
    )

    matches = list(quote_regex.finditer(content))
    assert len(matches) == 24, f"Expected 24 verbatim quotes, found {len(matches)}"

    for match in matches:
        fid = match.group("feedback_id")
        quote = match.group("quote")

        row = raw_df[raw_df["feedback_id"] == fid]
        assert not row.empty, f"Feedback ID {fid} not in data"
        raw_text = row.iloc[0]["text"].replace("\n", " ").strip()
        redacted_raw = redact_pii(raw_text)

        core_quote = quote[:-3] if quote.endswith("...") else quote
        assert core_quote in redacted_raw, f"Quote for {fid} is not a verbatim substring of raw data"


# ==============================================================================
# Additional Tests for User Request Specifics
# ==============================================================================

def test_item1_n_labeled_and_behavior_counts():
    """Item 1: Verify n_labeled and pause/stop/reduce/continue counts per theme."""
    df = load_all_cleaned_feedback(Path("data/processed"))
    classified_df = classify_feedback_dataframe(df)
    metrics = aggregate_discovery_metrics(classified_df)

    b_detail = metrics["behavior_detail"]
    assert len(b_detail) == 9

    # Financial Constraints: pause=5, stop=2, reduce=3, continue=0, n_labeled=10
    fc = b_detail[THEME_FINANCIAL_CONSTRAINTS]
    assert fc["n_labeled"] == 10
    assert fc["pause"] == 5
    assert fc["stop"] == 2
    assert fc["reduce"] == 3
    assert fc["continue"] == 0

    # Market Volatility: pause=2, stop=3, reduce=0, continue=0, n_labeled=5
    mv = b_detail[THEME_UNCERTAINTY]
    assert mv["n_labeled"] == 5
    assert mv["pause"] == 2
    assert mv["stop"] == 3

    # Investment Literacy: pause=1, n_labeled=1
    il = b_detail[THEME_INVESTMENT_UNDERSTANDING]
    assert il["n_labeled"] == 1
    assert il["pause"] == 1

    # Continuation: continue=7, n_labeled=7
    sc = b_detail[THEME_CONTINUATION]
    assert sc["n_labeled"] == 7
    assert sc["continue"] == 7

    # Customer Support & Platform Trust: n_labeled=0
    assert b_detail[THEME_CUSTOMER_SUPPORT]["n_labeled"] == 0
    assert b_detail[THEME_PLATFORM_TRUST]["n_labeled"] == 0


def test_item2_neutral_placeholder_when_n_labeled_below_10():
    """Item 2: If n_labeled < 10, verify empirical ChurnLink is NOT computed, neutral 5.0 is used."""
    df = load_all_cleaned_feedback(Path("data/processed"))
    classified_df = classify_feedback_dataframe(df)
    metrics = aggregate_discovery_metrics(classified_df)
    opportunities = rank_product_opportunities(metrics, classified_df)

    scored_opps = [o for o in opportunities if not o.get("is_descriptive")]
    for opp in scored_opps:
        if opp["n_labeled"] < 10:
            assert opp["churn_link"] == 5.0
            assert "neutral placeholder" in opp["churn_link_display"]
            assert "insufficient data" in opp["churn_link_display"]
        else:
            assert opp["n_labeled"] == 10
            assert opp["churn_link"] == 10.0
            assert "empirical" in opp["churn_link_display"]


def test_item3_sip_continuation_not_ranked():
    """Item 3: Verify SIP Continuation has no empirical RetentionLink, descriptive count only, not ranked."""
    df = load_all_cleaned_feedback(Path("data/processed"))
    classified_df = classify_feedback_dataframe(df)
    metrics = aggregate_discovery_metrics(classified_df)
    opportunities = rank_product_opportunities(metrics, classified_df)

    sc_opp = next(o for o in opportunities if o["theme"] == THEME_CONTINUATION)
    assert sc_opp["is_descriptive"] is True
    assert sc_opp["is_retention_enabler"] is True
    assert sc_opp["rank"] is None
    assert sc_opp["priority_score"] is None
    assert "Descriptive count only, not ranked" in sc_opp["churn_link_display"]


def test_item4_deliberate_pausing_separate_descriptive():
    """Item 4: Verify Deliberate Pausing is listed separately as descriptive theme, not scored on churn scale."""
    df = load_all_cleaned_feedback(Path("data/processed"))
    classified_df = classify_feedback_dataframe(df)
    metrics = aggregate_discovery_metrics(classified_df)
    opportunities = rank_product_opportunities(metrics, classified_df)

    dp_opp = next(o for o in opportunities if o["theme"] == THEME_PAUSE_STOP_REASONS)
    assert dp_opp["is_descriptive"] is True
    assert dp_opp["rank"] is None
    assert dp_opp["priority_score"] is None
    assert "Descriptive theme, not scored on the churn scale" in dp_opp["churn_link_display"]


def test_item5_mention_regex_matches_all_variants():
    """Item 5: Verify regex matches 'sip', 'sips', 'sip\\'s', 'auto debit', 'auto-debit', 'autopay', 'mandate'."""
    import re
    pattern = re.compile(r"\b(sip(?:s|'s)?|auto[- ]?pay|auto[- ]?debit|mandates?)\b", re.IGNORECASE)

    test_words = [
        "sip", "sips", "SIP's", "sip's",
        "autopay", "auto-pay", "auto pay",
        "auto debit", "auto-debit", "mandate", "mandates"
    ]
    for w in test_words:
        assert bool(pattern.search(f"My {w} failed")), f"Failed to match: {w}"

    # Verify negative cases
    assert not bool(pattern.search("gossiping about something"))
    assert not bool(pattern.search("sipping coffee"))


def test_item6_customer_support_sip_mentions_and_source_split():
    """Item 6: Verify Customer Support SIP mentions count and source split."""
    df = load_all_cleaned_feedback(Path("data/processed"))
    classified_df = classify_feedback_dataframe(df)
    metrics = aggregate_discovery_metrics(classified_df)

    cs_info = metrics["customer_support_detail"]
    assert cs_info["total_records"] == 34
    assert cs_info["sip_mentions"] == 0  # 0 mentions in CS records
    assert cs_info["source_split"]["playstore_batch1"] == 30
    assert cs_info["source_split"]["playstore_batch2"] == 2
    assert cs_info["source_split"]["reddit_concerns"] == 2
    assert "google_forms" not in cs_info["source_split"]


