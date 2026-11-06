"""Pytest for verifying exported dashboard corpus data.

Checks:
- 203 records
- 26 labeled: pause 8 / stop 8 / reduce 3 / continue 7
- theme counts: 63, 34, 28, 23, 19, 12, 10, 7, 7
- no stock SIP records
- no developer-reply text
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from scripts.export_dashboard_data import export_corpus_data


def test_export_corpus_data_integrity():
    corpus_file = Path("web/data/corpus.json")
    if not corpus_file.exists():
        export_corpus_data(corpus_file)

    with open(corpus_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data["records"]
    metrics = data["summary_metrics"]

    # 1. Check total records == 203
    assert len(records) == 203, f"Expected 203 records, got {len(records)}"
    assert metrics["total_records"] == 203

    # 2. Check labeled records == 26 (pause 8 / stop 8 / reduce 3 / continue 7)
    behavior_counts = {}
    for r in records:
        b = r["sip_behavior"]
        behavior_counts[b] = behavior_counts.get(b, 0) + 1

    assert behavior_counts.get("pause", 0) == 8, f"Expected 8 pause, got {behavior_counts.get('pause')}"
    assert behavior_counts.get("stop", 0) == 8, f"Expected 8 stop, got {behavior_counts.get('stop')}"
    assert behavior_counts.get("reduce", 0) == 3, f"Expected 3 reduce, got {behavior_counts.get('reduce')}"
    assert behavior_counts.get("continue", 0) == 7, f"Expected 7 continue, got {behavior_counts.get('continue')}"

    labeled_total = (
        behavior_counts.get("pause", 0)
        + behavior_counts.get("stop", 0)
        + behavior_counts.get("reduce", 0)
        + behavior_counts.get("continue", 0)
    )
    assert labeled_total == 26, f"Expected 26 labeled records, got {labeled_total}"
    assert metrics["n_labeled"] == 26
    assert behavior_counts.get("unspecified", 0) == 177

    # 3. Check theme counts: 63, 34, 28, 23, 19, 12, 10, 7, 7
    theme_counts = {}
    for r in records:
        t = r["primary_theme"]
        theme_counts[t] = theme_counts.get(t, 0) + 1

    expected_theme_counts = {
        "Uncertain / Ambiguous Feedback": 63,
        "Customer Support & Service Friction": 34,
        "Platform Trust, Technical Friction & Mandate Failures": 28,
        "Platform Usability, UI Speed & Design Ease": 23,
        "Deliberate Pausing, Stopping & Alternative Migration": 19,
        "Investment Literacy & Understanding Gaps": 12,
        "Financial Constraints & Cash-Flow Liquidity": 10,
        "Market Volatility Anxiety & Uncertainty": 7,
        "SIP Continuation & Goal Enablers": 7,
    }
    assert theme_counts == expected_theme_counts, (
        f"Theme counts differ: got {theme_counts}, expected {expected_theme_counts}"
    )

    sorted_counts = sorted(theme_counts.values(), reverse=True)
    assert sorted_counts == [63, 34, 28, 23, 19, 12, 10, 7, 7], (
        f"Expected counts [63, 34, 28, 23, 19, 12, 10, 7, 7], got {sorted_counts}"
    )

    # 4. Check no stock SIP records
    for r in records:
        assert r.get("asset_type") != "stock_sip", (
            f"Record {r.get('feedback_id')} has stock_sip asset type!"
        )
        assert r.get("source") != "reddit_stock_sip", (
            f"Record {r.get('feedback_id')} came from reddit_stock_sip!"
        )

    # 5. Check no developer-reply text leaked into records
    playstore1_path = Path("data/processed/playstore_groww_reviews_batch1_cleaned.csv")
    playstore2_path = Path("data/processed/playstore_groww_reviews_batch2_cleaned.csv")
    dev_replies = set()
    for p in [playstore1_path, playstore2_path]:
        if p.exists():
            df_ps = pd.read_csv(p)
            if "developer_reply" in df_ps.columns:
                replies = df_ps["developer_reply"].dropna().astype(str).str.strip().tolist()
                dev_replies.update(r for r in replies if len(r) > 15)

    assert len(dev_replies) > 0, "Expected to find actual developer replies in source data for checking"

    for r in records:
        text = r["text"]
        for reply in dev_replies:
            assert reply not in text, (
                f"Developer reply leaked into feedback_id {r['feedback_id']}: {reply[:40]}..."
            )

