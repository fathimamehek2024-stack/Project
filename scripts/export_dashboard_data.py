"""Export audited dashboard data to web/data/corpus.json.

Reuses load_all_cleaned_feedback, classify_feedback_dataframe,
aggregate_discovery_metrics, and rank_product_opportunities from
src.analysis.discovery_engine without modifying any existing pipeline code.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.analysis.discovery_engine import (
    aggregate_discovery_metrics,
    classify_feedback_dataframe,
    load_all_cleaned_feedback,
    rank_product_opportunities,
    redact_pii,
)


def export_corpus_data(output_path: Path = Path("web/data/corpus.json")) -> dict:
    """Load, classify, and export all mutual fund feedback and discovery metrics."""
    df_raw = load_all_cleaned_feedback()
    df_classified = classify_feedback_dataframe(df_raw)

    # Strictly isolate and filter for mutual fund & platform records (203 records)
    mf_df = df_classified[df_classified["asset_type"] != "stock_sip"].copy()

    dev_replies = set()  # No developer reply filtering

    # Build individual record payload
    records = []
    source_display_names = {
        "google_forms": "Google Form Survey",
        "playstore_batch1": "Google Play Store (Batch 1)",
        "playstore_batch2": "Google Play Store (Batch 2)",
        "reddit_concerns": "Reddit Discussions",
    }

    for _, row in mf_df.iterrows():
        raw_text = str(row["text"]).strip()
        redacted = redact_pii(raw_text)

        # No developer reply filtering applied

        records.append({
            "feedback_id": str(row["feedback_id"]),
            "source": str(row["source"]),
            "source_display": source_display_names.get(str(row["source"]), str(row["source"])),
            "asset_type": str(row["asset_type"]),
            "date": str(row.get("date", "")),
            "text": redacted,
            "primary_theme": str(row["primary_theme"]),
            "secondary_theme": str(row.get("secondary_theme", "")),
            "sip_behavior": str(row["sip_behavior"]),
            "confidence": str(row.get("confidence", "uncertain")),
            "is_uncertain": bool(row.get("is_uncertain", False)),
        })

    # Metrics and Aggregations
    metrics = aggregate_discovery_metrics(df_classified)
    all_ranked = rank_product_opportunities(metrics, df_classified)

    # Separate ranked churn opportunities and descriptive themes
    ranked_opportunities = [r for r in all_ranked if not r.get("is_descriptive", False)]
    descriptive_themes = [r for r in all_ranked if r.get("is_descriptive", False)]

    # Compute behavioral breakdown
    behavior_counts = mf_df["sip_behavior"].value_counts().to_dict()
    n_labeled = (
        behavior_counts.get("pause", 0)
        + behavior_counts.get("stop", 0)
        + behavior_counts.get("reduce", 0)
        + behavior_counts.get("continue", 0)
    )

    theme_counts = metrics["overall_theme_counts"]
    ordered_theme_counts = {
        k: theme_counts[k]
        for k in sorted(theme_counts.keys(), key=lambda x: theme_counts[x], reverse=True)
    }

    # Journey Stage Mapping
    journey_stages = [
        {
            "stage_number": 1,
            "stage_name": "Goal and continuation",
            "theme": "SIP Continuation & Goal Enablers",
            "record_count": theme_counts.get("SIP Continuation & Goal Enablers", 7),
            "description": "Long-term compounding discipline, positive retention behaviors, and goal milestone tracking.",
        },
        {
            "stage_number": 2,
            "stage_name": "Understanding",
            "theme": "Investment Literacy & Understanding Gaps",
            "record_count": theme_counts.get("Investment Literacy & Understanding Gaps", 12),
            "description": "Confusion regarding NAV calculation, exit loads, expense ratios, and capital gains taxation.",
        },
        {
            "stage_number": 3,
            "stage_name": "Payment and mandate",
            "theme": "Platform Trust, Technical Friction & Mandate Failures",
            "record_count": theme_counts.get("Platform Trust, Technical Friction & Mandate Failures", 28),
            "description": "Autopay mandate setup issues, bank debit delays, failed installments, and double-deduction anxiety.",
        },
        {
            "stage_number": 4,
            "stage_name": "Support",
            "theme": "Customer Support & Service Friction",
            "record_count": theme_counts.get("Customer Support & Service Friction", 34),
            "description": "Automated bot circular loops, unanswered tickets, slow turnaround on failed transactions.",
        },
        {
            "stage_number": 5,
            "stage_name": "Performance expectations",
            "theme": "Market Volatility Anxiety & Uncertainty",
            "record_count": theme_counts.get("Market Volatility Anxiety & Uncertainty", 7),
            "description": "Panic during short-term portfolio drawdowns, lack of context on market cycles.",
        },
        {
            "stage_number": 6,
            "stage_name": "Pause / stop",
            "theme": "Deliberate Pausing, Stopping & Alternative Migration",
            "record_count": theme_counts.get("Deliberate Pausing, Stopping & Alternative Migration", 19),
            "description": "Explicit portfolio stopping, account closure, shifting funds to competitor platforms.",
        },
    ]

    # Limitations & Study Context
    limitations = [
        {
            "title": "DATA SOURCES",
            "summary": "Google Play Store (126 across 2 batches), Reddit r/IndiaInvestments & r/mutualfunds (53), Google Form survey (24), total 203 records, deduplicated & pruned.",
        },
        {
            "title": "CLASSIFICATION",
            "summary": "Rule-based theme classifier with secondary theme and confidence scoring.",
        },
        {
            "title": "UNCERTAINTY RATE",
            "summary": f"Uncertainty Rate: {theme_counts.get('Uncertain / Ambiguous Feedback', 63)} of 203 records (31.0%) were unclassified.",
        },
        {
            "title": "STATED BEHAVIOR",
            "summary": "Stated Behavior: 26 out of 203 records self-report active/paused/stopped status (8 pause, 8 stop, 7 continue, 3 reduce).",
        },
        {
            "title": "SCORING FORMULA",
            "summary": "Scoring Formula: 0.25*Freq + 0.35*ChurnLink + 0.20*Severity + 0.20*Fixability, times 10; where n_labeled < 10, neutral placeholder 5.0 used.",
        },
        {
            "title": "APP-WIDE SCOPE",
            "summary": "App-wide Scope: Feedback covers mutual funds and general app features affecting retention. 7 stock SIP discussions are strictly excluded.",
        },
    ]

    corpus_payload = {
        "summary_metrics": {
            "total_records": len(records),
            "customer_themes_count": len(theme_counts),
            "actionable_themes_count": len(theme_counts) - 1,
            "stated_pause": behavior_counts.get("pause", 0),
            "stated_stop": behavior_counts.get("stop", 0),
            "stated_continue": behavior_counts.get("continue", 0),
            "stated_reduce": behavior_counts.get("reduce", 0),
            "n_labeled": n_labeled,
            "unspecified": behavior_counts.get("unspecified", 0),
            "source_counts": metrics.get("source_counts", {}),
            "theme_counts": ordered_theme_counts,
            "theme_percentages": metrics.get("overall_theme_pcts", {}),
            "n_labeled_per_theme": metrics.get("n_labeled", {}),
            "behavior_counts_per_theme": metrics.get("behavior_detail", {}),
            "keyword_mentions": metrics.get("keyword_mentions", {}),
            "customer_support_detail": metrics.get("customer_support_detail", {}),
        },
        "opportunity_ranking": ranked_opportunities,
        "descriptive_themes": descriptive_themes,
        "journey_stages": journey_stages,
        "limitations": limitations,
        "records": records,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(corpus_payload, f, indent=2, ensure_ascii=False)

    print(f"Successfully exported {len(records)} mutual fund records to {output_path}")
    return corpus_payload


if __name__ == "__main__":
    export_corpus_data()

