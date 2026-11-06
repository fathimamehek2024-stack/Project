"""Feedback Theme Classification and Discovery Pipeline.

Analyzes cleaned research datasets to discover drivers of mutual fund SIP
continuation, pausing, reducing, and stopping.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
import re
import sys
from typing import Any

# Ensure terminal output handles UTF-8 characters safely
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ==============================================================================
# Theme Definitions
# ==============================================================================

THEME_PLATFORM_TRUST = "Platform Trust, Technical Friction & Mandate Failures"
THEME_CUSTOMER_SUPPORT = "Customer Support & Service Friction"
THEME_UNCERTAINTY = "Market Volatility Anxiety & Uncertainty"
THEME_FINANCIAL_CONSTRAINTS = "Financial Constraints & Cash-Flow Liquidity"
THEME_INVESTMENT_UNDERSTANDING = "Investment Literacy & Understanding Gaps"
THEME_PAUSE_STOP_REASONS = "Deliberate Pausing, Stopping & Alternative Migration"
THEME_CONTINUATION = "SIP Continuation & Goal Enablers"
THEME_USABILITY = "Platform Usability, UI Speed & Design Ease"
THEME_UNCERTAIN = "Uncertain / Ambiguous Feedback"


@dataclass
class ClassifiedFeedback:
    """Structure for each classified feedback item."""

    record_id: str
    source: str
    asset_type: str
    feedback_text: str
    primary_theme: str
    secondary_theme: str
    confidence: str  # 'high', 'medium', 'uncertain'
    supporting_evidence: str
    investor_status: str  # 'active', 'paused', 'stopped', 'reduced', 'reviewer', 'redditor'


# ==============================================================================
# Keyword Rules and Heuristics for Text Datasets (Play Store & Reddit)
# ==============================================================================

OFF_TOPIC_PATTERNS: list[str] = [
    r"\bcall\s+options?\b",
    r"\bput\s+options?\b",
    r"\bf[&/]o\b",
    r"\bfno\b",
    r"\bfutures?\s+and\s+options?\b",
    r"\bfutures?(\s+trading|\s+contract|\s+segment)?\b",
    r"\bderivatives?(\s+trading|\s+segment)?\b",
    r"\bscalp(er|ing)?\b",
    r"\bintraday(\s+trading|\s+order|\s+leverage)?\b",
    r"\bday[- ]?trad(er|ing)\b",
    r"\bexpiry(\s+day)?\b",
    r"\boption\s+trad(er|ing)\b",
    r"\boptions?\s+(chain|trading|premium|buyer|seller|scalping|strike)\b",
    r"\btrading\s+terminal\b",
    r"\b(nifty|bank\s*nifty|finnifty|sensex)\s+(50\s+)?(options?|call|put|ce|pe)\b",
    r"\b\d{4,5}\s*(ce|pe)\b",
    r"\b(ce|pe)\s+(call|put|strike|premium|option)\b",
    r"\bstop\s*loss\b",
    r"\btrading\s+chart(s)?\b",
    r"\bcandlestick\b",
    r"\boptions?\b(?=.*(trading|trader|strike|premium|nifty|bank\s*nifty|loss|scalp|ce|pe))",
]

GENERIC_NON_INFORMATIVE: set[str] = {
    "good app ok.",
    "good app ok",
    "good app",
    "good",
    "nice",
    "ok",
    "ok app",
    "nice app",
    "super",
    "bad",
    "worst",
    "very good",
    "best app",
    "thank you",
    "thanks",
}

KEYWORD_PATTERNS: dict[str, list[str]] = {
    THEME_PLATFORM_TRUST: [
        r"\bmandate\b",
        r"\bautopay\b",
        r"\bauto[- ]?debit\b",
        r"\bbank account\b",
        r"\bfailed\b",
        r"\bstuck\b",
        r"\bblocked\b",
        r"\bserver\b",
        r"\bglitch\b",
        r"\bdelayed?\b",
        r"\bredemption\b",
        r"\brefund\b",
        r"\bwithdraw(al)?\b",
        r"\b(money|amount|funds?|balance)\s+deducted.*(not credited|not invested|failed|stuck|awaiting)\b",
        r"\bdeducted.*(not credited|awaiting payment|shows awaiting)\b",
        r"\bnot credited\b",
        r"\bcredit\b",
        r"\btransaction failed\b",
        r"\border.*stuck\b",
        r"\bapp gets stuck\b",
        r"\bupi is not working\b",
        r"\bpayment delayed\b",
        r"\bawaiting payment\b",
        r"\b(to\s+)?continue\s+securely\b",
        r"\bdisconnect\s+usb\b",
        r"\busb\s+debugging\b",
        r"\bsecurity\s+alert\b",
        r"\bapp\s+(crash|crashes|crashing|freeze|freezes|freezing)\b",
    ],
    THEME_CUSTOMER_SUPPORT: [
        r"\bcustomer (care|service|support)\b",
        r"\bsupport team\b",
        r"\bticket\b",
        r"\bhelpline\b",
        r"\bhelp desk\b",
        r"\bno response\b",
        r"\bpathetic service\b",
        r"\bpoor service\b",
        r"\bworst service\b",
        r"\bmail.*support\b",
        r"\bexecutive\b",
        r"\breply\b",
    ],
    THEME_UNCERTAINTY: [
        r"\bloss(es)?\b",
        r"\bnegative returns?\b",
        r"\bmarket fall\b",
        r"\b(market|portfolio|nav|index|sensex|nifty|returns?|shares?)\s+(is\s+|are\s+)?down\b",
        r"\bdown\s+by\s+\d+%\b",
        r"\bups and downs\b",
        r"\bmarket crash\b",
        r"\bpanic\b",
        r"\bfear\b",
        r"\banxious\b",
        r"\brisk\b",
        r"\bvolatilit(y|ies)\b",
    ],
    THEME_FINANCIAL_CONSTRAINTS: [
        r"\bsalary\b",
        r"\bcash[- ]?flow\b",
        r"\bjob (change|loss|uncertainty)\b",
        r"\blost job\b",
        r"\bincome\b",
        r"\bfinancial (crisis|issues?|problems?|stress)\b",
        r"\bexpense(s)?\b",
        r"\bafford\b",
        r"\bneeded (the )?money\b",
        r"\bemergency\b",
        r"\bemergency medical\b",
        r"\bskip (one |a )?(month |installment)\b",
        r"\blower income\b",
    ],
    THEME_INVESTMENT_UNDERSTANDING: [
        r"\bexit\s+load(s)?\b",
        r"\bexit\s+fee(s)?\b",
        r"\bstamp\s+duty\b",
        r"\bcharges?\b",
        r"\bfee(s)?\b",
        r"\bhidden\s+fee(s)?\b",
        r"\bdeduction(s)?\b",
        r"\bwhy.*(deducted|charges?|tax(es)?|fee(s)?)\b",
        r"\b(charges?|fee(s)?).*(deducted|high|excessive)\b",
        r"\bhow\s+much\s+(deducted|charged)\b",
        r"\bdeducted\s+on\s+(redemption|withdrawal|exit|selling)\b",
        r"\bpool\s+account\b",
        r"\b(groww\s+)?shuts?\s+down\b",
        r"\bheld\s+in\s+amc\b",
        r"\bamc\s+or\s+groww\b",
        r"\bconfus(ing|ed|ion)\b",
        r"\b(did\s+not|don'?t|do\s+not|cannot|can'?t|unable\s+to)\s+understand\b",
        r"\bwhere.*money\s+(goes|is\s+invested)\b",
        r"\bnav\b",
        r"\bexpense\s+ratio\b",
        r"\bright\s+amount\b",
        r"\bhow\s+it\s+works\b",
        r"\bclearly\s+explained\b",
        r"\bclarification\b",
        r"\bwhat\s+(is|are)\s+(the\s+)?(exit\s+load|charges?|fee(s)?|deductions?)\b",
        r"\bcapital\s+gains?(\s+tax)?\b",
    ],
    THEME_PAUSE_STOP_REASONS: [
        r"\b(paused?|stopping|stopped|cancel(led)?)\b",
        r"\bclose(d)? account\b",
        r"\bswitch(ed|ing)?\b",
        r"\btransfer(ring)?\b",
        r"\bmove to kuvera\b",
        r"\bkuvera\b",
        r"\bzerodha\b",
        r"\banother investment\b",
        r"\blost interest\b",
        r"\bleave\b",
        r"\bshift(ed)?\b",
    ],
    THEME_CONTINUATION: [
        r"\bcontinue\s+(investing|my sip|sip|contributions?|monthly|regularly)\b",
        r"\b(to|will)\s+continue\s+investing\b",
        r"\bcontinuation\b",
        r"\bcontinuing\s+(my\s+)?sip\b",
        r"\bpersonal goal\b",
        r"\bprogress toward a (personal )?goal\b",
        r"\bdiscipline\b",
        r"\blong[- ]?term\b",
        r"\bcompounding\b",
        r"\bwealth creation\b",
        r"\bmonthly investment\b",
        r"\bregular (investment|investing|sip)\b",
        r"\bstep[- ]?up\b",
        r"\bkeep investing\b",
    ],
    THEME_USABILITY: [
        r"\buser[- ]?friendly\b",
        r"\beasy to (use|handle)\b",
        r"\bsimple\b",
        r"\bclean ui\b",
        r"\bsmooth\b",
        r"\bgood interface\b",
        r"\bprocessing speed\b",
        r"\blag\b",
        r"\bupdate\b",
        r"\bfeature\b",
        r"\bcharts?\b",
    ],
}


def classify_survey_record(row: list[str], headers: list[str]) -> ClassifiedFeedback:
    """Classify an active/past investor survey response into structured themes."""
    record_id = row[0]
    asset_type = row[1]
    sip_status = row[6].strip()  # Active, Paused, Stopped, Reduced
    tenure = row[7].strip()
    reason_choice = row[13].strip()  # Q13 reasons
    confusing_choice = row[11].strip()  # Q12 confusing
    continue_choice = row[14].strip()  # Q14 enablers

    # Build descriptive narrative text for traceability
    full_text = (
        f"Status: {sip_status} | Tenure: {tenure} | "
        f"Confusing aspects: '{confusing_choice}' | "
        f"Pause/Stop reasons: '{reason_choice or 'None'}' | "
        f"Continuation factors: '{continue_choice or 'None'}'"
    )

    primary_theme = THEME_CONTINUATION
    secondary_theme = ""
    evidence_list: list[str] = []
    confidence = "high"

    # Prioritize reasons if user stopped, paused, or reduced
    if sip_status in ("Stopped", "Paused", "Reduced the amount"):
        if "Market fall or negative returns" in reason_choice:
            primary_theme = THEME_UNCERTAINTY
            evidence_list.append("Selected: Market fall or negative returns")
        elif "Lower income or cash-flow pressure" in reason_choice or "Job change" in reason_choice:
            primary_theme = THEME_FINANCIAL_CONSTRAINTS
            evidence_list.append(f"Selected: {reason_choice}")
        elif "App experience issues" in reason_choice:
            primary_theme = THEME_PLATFORM_TRUST
            evidence_list.append("Selected: App experience issues")
        elif "Did not understand what was happening" in reason_choice:
            primary_theme = THEME_INVESTMENT_UNDERSTANDING
            evidence_list.append("Selected: Did not understand what was happening")
        elif "Found another investment option" in reason_choice or "Lost interest" in reason_choice:
            primary_theme = THEME_PAUSE_STOP_REASONS
            evidence_list.append(f"Selected: {reason_choice}")
        else:
            primary_theme = THEME_PAUSE_STOP_REASONS
            evidence_list.append(f"Status: {sip_status}")

        if continue_choice:
            secondary_theme = THEME_CONTINUATION
    else:  # Active
        primary_theme = THEME_CONTINUATION
        evidence_list.append(f"Active SIP investor; Continuation factors: {continue_choice}")
        if confusing_choice and "Nothing was confusing" not in confusing_choice:
            secondary_theme = THEME_INVESTMENT_UNDERSTANDING

    supporting_evidence = "; ".join(evidence_list) if evidence_list else "Survey response pattern"

    return ClassifiedFeedback(
        record_id=record_id,
        source="google_forms",
        asset_type=asset_type,
        feedback_text=full_text,
        primary_theme=primary_theme,
        secondary_theme=secondary_theme,
        confidence=confidence,
        supporting_evidence=supporting_evidence,
        investor_status=sip_status.lower(),
    )


def classify_text_record(
    record_id: str,
    source: str,
    text: str,
    investor_status: str,
    asset_type: str = "mutual_fund_and_platform",
) -> ClassifiedFeedback:
    """Classify unstructured user feedback from Play Store or Reddit."""
    cleaned_text = text.lower().strip()

    # 1. Screen for purely generic non-informative comments
    if cleaned_text in GENERIC_NON_INFORMATIVE:
        return ClassifiedFeedback(
            record_id=record_id,
            source=source,
            asset_type=asset_type,
            feedback_text=text,
            primary_theme=THEME_UNCERTAIN,
            secondary_theme="",
            confidence="uncertain",
            supporting_evidence="Generic non-informative feedback.",
            investor_status=investor_status,
        )

    # 2. Screen for off-topic F&O and derivative trading complaints
    is_off_topic = any(
        re.search(pat, cleaned_text, re.IGNORECASE) for pat in OFF_TOPIC_PATTERNS
    )
    has_mf_context = bool(
        re.search(r"\b(mutual[- ]?fund|sip|folio)\b", cleaned_text, re.IGNORECASE)
    )
    if is_off_topic and not has_mf_context:
        return ClassifiedFeedback(
            record_id=record_id,
            source=source,
            asset_type=asset_type,
            feedback_text=text,
            primary_theme=THEME_UNCERTAIN,
            secondary_theme="",
            confidence="uncertain",
            supporting_evidence="Off-topic F&O or derivatives trading feedback.",
            investor_status=investor_status,
        )

    # 3. Score each theme based on matched keyword regex patterns
    theme_matches: dict[str, list[str]] = {}
    for theme, patterns in KEYWORD_PATTERNS.items():
        matched = []
        for pat in patterns:
            found = re.findall(pat, cleaned_text, re.IGNORECASE)
            if found:
                matched.extend(
                    [m if isinstance(m, str) else m[0] for m in found if m]
                )
        if matched:
            theme_matches[theme] = matched

    if not theme_matches:
        # Ambiguous feedback: mark uncertain
        return ClassifiedFeedback(
            record_id=record_id,
            source=source,
            asset_type=asset_type,
            feedback_text=text,
            primary_theme=THEME_UNCERTAIN,
            secondary_theme="",
            confidence="uncertain",
            supporting_evidence="No domain-specific SIP or platform keywords detected.",
            investor_status=investor_status,
        )

    # 4. Disambiguation: Prioritize Investment Literacy when questions focus on fees, charges, deductions, or custody
    # rather than actual unprompted technical bank/mandate failures.
    has_technical_failure = bool(
        re.search(
            r"\b(not\s+credited|not\s+invested|mandate\s+failed|auto[- ]?debit\s+failed|"
            r"autopay\s+failed|awaiting\s+payment|payment\s+delayed|transaction\s+failed|"
            r"bank\s+mandate|mandate\s+approved.*delayed)\b",
            cleaned_text,
            re.IGNORECASE,
        )
    )
    is_fee_or_custody_query = bool(
        re.search(
            r"\b(exit\s+loads?|exit\s+fees?|stamp\s+duty|charges?|fees?|deductions?|"
            r"shuts?\s+down|pool\s+account|held\s+in\s+amc|expense\s+ratio|"
            r"why.*deducted|deducted\s+on\s+(redemption|withdrawal))\b",
            cleaned_text,
            re.IGNORECASE,
        )
    )
    if THEME_INVESTMENT_UNDERSTANDING in theme_matches and is_fee_or_custody_query and not has_technical_failure:
        # In fee/deduction/custody inquiries, words like 'redemption' or 'withdrawal' reflect the context of charges,
        # not a system technical failure. Prioritize Investment Literacy.
        literacy_words = theme_matches[THEME_INVESTMENT_UNDERSTANDING]
        other_themes = sorted(
            [(t, w) for t, w in theme_matches.items() if t != THEME_INVESTMENT_UNDERSTANDING],
            key=lambda item: len(item[1]),
            reverse=True,
        )
        sorted_themes = [(THEME_INVESTMENT_UNDERSTANDING, literacy_words)] + other_themes
    else:
        # Sort themes by match count
        sorted_themes = sorted(
            theme_matches.items(), key=lambda item: len(item[1]), reverse=True
        )

    primary_theme = sorted_themes[0][0]
    matched_words = sorted_themes[0][1]
    secondary_theme = sorted_themes[1][0] if len(sorted_themes) > 1 else ""

    # Assess classification confidence
    if len(matched_words) >= 2 or len(cleaned_text) > 40:
        confidence = "high"
    elif len(matched_words) == 1:
        confidence = "medium"
    else:
        confidence = "uncertain"

    evidence_str = f"Matched keywords: [{', '.join(set(matched_words[:5]))}]"

    return ClassifiedFeedback(
        record_id=record_id,
        source=source,
        asset_type=asset_type,
        feedback_text=text,
        primary_theme=primary_theme,
        secondary_theme=secondary_theme,
        confidence=confidence,
        supporting_evidence=evidence_str,
        investor_status=investor_status,
    )


# ==============================================================================
# Pipeline Execution & Reporting
# ==============================================================================


def run_theme_classification_pipeline() -> tuple[
    list[ClassifiedFeedback], list[ClassifiedFeedback], dict[str, Any]
]:
    """Execute classification pipeline across all cleaned datasets.

    Returns:
    --------
    tuple[list[ClassifiedFeedback], list[ClassifiedFeedback], dict[str, Any]]:
        - mutual_fund_results: List of classified mutual fund & platform records.
        - stock_sip_results: List of classified stock SIP records (isolated).
        - metrics: Dictionary of counts, sources, and distributions.
    """
    proc_dir = Path("data/processed")
    exports_dir = Path("data/exports")
    exports_dir.mkdir(parents=True, exist_ok=True)

    mutual_fund_records: list[ClassifiedFeedback] = []
    stock_sip_records: list[ClassifiedFeedback] = []

    source_counts: dict[str, int] = {
        "google_forms": 0,
        "playstore_batch1": 0,
        "playstore_batch2": 0,
        "reddit_concerns": 0,
        "reddit_stock_sip": 0,
    }

    # 1. Google Forms Survey (Exclude non-investors: Q1 == 'No')
    survey_path = proc_dir / "google_form_sip_responses_cleaned.csv"
    with open(survey_path, mode="r", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
    survey_headers = reader[0]
    for row in reader[1:]:
        # row[2] is Q1: "Have you started a mutual-fund SIP ?"
        if row[2].strip() == "Yes":
            classified = classify_survey_record(row, survey_headers)
            mutual_fund_records.append(classified)
            source_counts["google_forms"] += 1

    # 2. Google Play Reviews Batch 1
    ps1_path = proc_dir / "playstore_groww_reviews_batch1_cleaned.csv"
    with open(ps1_path, mode="r", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
    for row in reader[1:]:
        review_id = row[0]
        star_rating = row[2]
        text = row[4]
        classified = classify_text_record(
            record_id=review_id,
            source="google_play_b1",
            text=text,
            investor_status=f"playstore_{star_rating}star",
            asset_type="mutual_fund_and_platform",
        )
        mutual_fund_records.append(classified)
        source_counts["playstore_batch1"] += 1

    # 3. Google Play Reviews Batch 2
    ps2_path = proc_dir / "playstore_groww_reviews_batch2_cleaned.csv"
    with open(ps2_path, mode="r", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
    for row in reader[1:]:
        review_id = row[0]
        star_rating = row[2]
        text = row[4]
        classified = classify_text_record(
            record_id=review_id,
            source="google_play_b2",
            text=text,
            investor_status=f"playstore_{star_rating}star",
            asset_type="mutual_fund_and_platform",
        )
        mutual_fund_records.append(classified)
        source_counts["playstore_batch2"] += 1

    # 4. Reddit Groww Concerns (Exclude deleted comments)
    red1_path = proc_dir / "reddit_groww_concerns_cleaned.csv"
    with open(red1_path, mode="r", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
    for row in reader[1:]:
        comment_id = row[0]
        body = row[6].strip()
        if body and body not in ("[deleted]", "[removed]"):
            classified = classify_text_record(
                record_id=comment_id,
                source="reddit_concerns",
                text=body,
                investor_status="redditor",
                asset_type="mutual_fund_and_platform",
            )
            mutual_fund_records.append(classified)
            source_counts["reddit_concerns"] += 1

    # 5. Reddit Stock SIP Discussions (Kept strictly isolated)
    red2_path = proc_dir / "reddit_groww_stock_sip_cleaned.csv"
    with open(red2_path, mode="r", encoding="utf-8-sig") as f:
        reader = list(csv.reader(f))
    for row in reader[1:]:
        comment_id = row[0]
        body = row[6].strip()
        if body and body not in ("[deleted]", "[removed]"):
            classified = classify_text_record(
                record_id=comment_id,
                source="reddit_stock_sip",
                text=body,
                investor_status="stock_sip_discussant",
                asset_type="stock_sip",
            )
            stock_sip_records.append(classified)
            source_counts["reddit_stock_sip"] += 1

    # Save exports
    export_csv(
        exports_dir / "classified_mutual_fund_feedback.csv",
        mutual_fund_records,
    )
    export_csv(
        exports_dir / "classified_stock_sip_feedback.csv",
        stock_sip_records,
    )

    # Generate summary metrics
    theme_distribution: dict[str, int] = {}
    for r in mutual_fund_records:
        theme_distribution[r.primary_theme] = (
            theme_distribution.get(r.primary_theme, 0) + 1
        )

    metrics = {
        "source_counts": source_counts,
        "total_mf_analyzed": len(mutual_fund_records),
        "total_stock_sip_isolated": len(stock_sip_records),
        "theme_distribution": theme_distribution,
    }

    # Save report
    generate_markdown_report(
        Path("reports/feedback_analysis_summary.md"),
        mutual_fund_records,
        stock_sip_records,
        metrics,
    )

    return mutual_fund_records, stock_sip_records, metrics


def export_csv(output_path: Path, records: list[ClassifiedFeedback]) -> None:
    """Export classified feedback objects to a standardized CSV file."""
    if not records:
        return
    fieldnames = list(asdict(records[0]).keys())
    with open(output_path, mode="w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(asdict(r))


def generate_markdown_report(
    report_path: Path,
    mf_records: list[ClassifiedFeedback],
    stock_records: list[ClassifiedFeedback],
    metrics: dict[str, Any],
) -> None:
    """Generate a clean, structured Markdown analysis summary report."""
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # Gather top representative comments for each theme
    theme_samples: dict[str, list[ClassifiedFeedback]] = {}
    for r in mf_records:
        if r.confidence in ("high", "medium"):
            theme_samples.setdefault(r.primary_theme, []).append(r)

    md = []
    md.append("# Mutual Fund SIP Retention & Churn: Discovery Engine Analysis Summary\n")
    md.append("## 1. Scope & Analyzed Volume by Source\n")
    md.append("| Data Source | Raw Rows | Excluded Rows | Analyzed Rows | Notes |")
    md.append("| :--- | :---: | :---: | :---: | :--- |")
    md.append(
        f"| **Google Forms Survey** | 32 | 8 | **{metrics['source_counts']['google_forms']}** | Excluded 8 non-investors (`Q1 == 'No'`) to focus on investor retention |"
    )
    md.append(
        f"| **Google Play Reviews (Batch 1)** | 530 | 424 | **{metrics['source_counts']['playstore_batch1']}** | 424 pagination duplicates removed; 106 unique reviews |"
    )
    md.append(
        f"| **Google Play Reviews (Batch 2)** | 100 | 80 | **{metrics['source_counts']['playstore_batch2']}** | 80 pagination duplicates removed; 20 unique reviews |"
    )
    md.append(
        f"| **Reddit Groww Concerns** | 56 | 3 | **{metrics['source_counts']['reddit_concerns']}** | Excluded 3 `[deleted]` comments; preserved thread integrity |"
    )
    md.append(
        f"| **Total Mutual Fund & Platform** | **718** | **515** | **{metrics['total_mf_analyzed']}** | **Core discovery dataset for Mutual Fund SIP retention** |\n"
    )

    md.append("### Isolated Stock SIP Discussions (Strictly Segregated)\n")
    md.append(
        f"* **Reddit Stock SIP Thread:** **{metrics['total_stock_sip_isolated']} comments** analyzed in a separate domain. These discussions address single-equity systematic investing and are **excluded** from mutual fund retention findings.\n"
    )

    md.append("## 2. Identified Themes & Distribution\n")
    md.append("| Theme | Count | % of MF Feedback | Core Driver Type |")
    md.append("| :--- | :---: | :---: | :--- |")
    total_mf = metrics["total_mf_analyzed"]
    sorted_themes = sorted(
        metrics["theme_distribution"].items(), key=lambda x: x[1], reverse=True
    )
    for theme, count in sorted_themes:
        pct = (count / total_mf) * 100
        driver_type = (
            "Retention Enabler"
            if "Continuation" in theme or "Usability" in theme
            else "Churn / Pause Driver"
            if theme != THEME_UNCERTAIN
            else "Needs Clarification"
        )
        md.append(f"| **{theme}** | **{count}** | {pct:.1f}% | {driver_type} |")
    md.append("")

    md.append("## 3. Representative Supporting Comments by Theme\n")
    for theme, count in sorted_themes:
        md.append(f"### {theme} ({count} records)\n")
        samples = theme_samples.get(theme, [])[:3]
        if not samples:
            samples = [r for r in mf_records if r.primary_theme == theme][:2]
        for s in samples:
            clean_snippet = s.feedback_text.replace("\n", " ")[:200]
            md.append(f"- **[{s.source} - {s.record_id}]**: *\"{clean_snippet}...\"*")
            md.append(f"  - **Evidence:** `{s.supporting_evidence}`")
            md.append(f"  - **Confidence:** `{s.confidence}`\n")

    md.append("## 4. Key Limitations & Uncertain Findings\n")
    md.append(
        "1. **Self-Reported Intent vs. Actual 12-Month Bank Telemetry:** Survey responses represent respondents' stated perceptions and attitudes. They do not substitute for longitudinal transactional records of 12-month auto-debit success rates."
    )
    md.append(
        "2. **Negativity Skew in App Store Reviews:** Review platforms over-represent dissatisfied users who experienced transaction failures, KYC delays, or account blocks. Satisfied SIP investors rarely post reviews unless prompted."
    )
    md.append(
        "3. **Stock SIP vs Mutual Fund SIP Segregation:** Single-equity SIPs involve company-specific stock market volatility and trading charges; they have been kept separate to avoid distorting mutual fund findings."
    )
    md.append(
        f"4. **Ambiguous Feedback Records:** {metrics['theme_distribution'].get(THEME_UNCERTAIN, 0)} records were classified as uncertain because they referenced F&O option trading, generic one-word praise, or lacked clear mutual fund context."
    )
    md.append(
        "5. **Exploratory Survey Sample:** The 24 active survey respondents provide qualitative direction for product discovery, but quantitative generalizations should be verified against larger production cohorts.\n"
    )

    with open(report_path, mode="w", encoding="utf-8") as f:
        f.write("\n".join(md))


def main() -> None:
    """Run classification pipeline and print report."""
    mf_records, stock_records, metrics = run_theme_classification_pipeline()

    print("=" * 85)
    print("      GROWW SIP RETENTION DISCOVERY ENGINE - THEME CLASSIFICATION REPORT")
    print("=" * 85)
    print(f"Total Mutual Fund & Platform Records Analyzed : {metrics['total_mf_analyzed']}")
    print(f"Total Isolated Stock SIP Records Analyzed     : {metrics['total_stock_sip_isolated']}")
    print("-" * 85)
    print("RECORDS ANALYZED BY SOURCE:")
    for src, count in metrics["source_counts"].items():
        print(f"  * {src:25s} : {count} records")

    print("\nTHEME DISTRIBUTION (MUTUAL FUND & PLATFORM DATASET):")
    total_mf = metrics["total_mf_analyzed"]
    sorted_themes = sorted(
        metrics["theme_distribution"].items(), key=lambda x: x[1], reverse=True
    )
    for theme, count in sorted_themes:
        pct = (count / total_mf) * 100
        print(f"  * {count:3d} ({pct:5.1f}%) : {theme}")

    print("\nEXPORTS SAVED:")
    print("  * data/exports/classified_mutual_fund_feedback.csv")
    print("  * data/exports/classified_stock_sip_feedback.csv")
    print("  * reports/feedback_analysis_summary.md")
    print("=" * 85)


if __name__ == "__main__":
    main()
