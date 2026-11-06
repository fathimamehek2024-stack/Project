"""Survey Privacy and PII Auditor.

Scans survey CSV files for Personally Identifiable Information (PII)
such as email addresses, phone numbers, and identifying header fields.
"""

from __future__ import annotations

import csv
from pathlib import Path
import re
from typing import Any

# Regex patterns for detecting sensitive data
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_REGEX = re.compile(r"\b(?:\+91|91|0)?[6-9]\d{9}\b")

# Keywords in column headers that indicate personal or identifying tracking
PII_HEADER_KEYWORDS = [
    "email",
    "name",
    "phone",
    "mobile",
    "contact",
    "timestamp",
    "address",
    "ip address",
    "user_id",
]


def audit_survey_pii(file_path: Path | str) -> dict[str, Any]:
    """Audit a survey CSV for potential PII exposures.

    Parameters
    ----------
    file_path : Path | str
        Path to the CSV file to audit.

    Returns
    -------
    dict[str, Any]
        Audit summary containing PII columns, found emails, and risk levels.
    """
    path = Path(file_path)

    if not path.is_file():
        return {
            "file_name": path.name,
            "exists": False,
            "risk_level": "UNKNOWN",
            "pii_columns": [],
            "found_emails": [],
            "found_phones": [],
            "summary": f"File '{path}' does not exist.",
        }

    try:
        with open(path, mode="r", encoding="utf-8-sig", newline="", errors="replace") as f:
            reader = list(csv.reader(f))

        if not reader:
            return {
                "file_name": path.name,
                "exists": True,
                "risk_level": "NONE",
                "pii_columns": [],
                "found_emails": [],
                "found_phones": [],
                "summary": "File is empty.",
            }

        headers = [h.strip() for h in reader[0]]
        rows = reader[1:]

        # 1. Identify suspicious column headers
        flagged_headers: list[str] = []
        for header in headers:
            header_lower = header.lower()
            if any(keyword in header_lower for keyword in PII_HEADER_KEYWORDS):
                flagged_headers.append(header)

        # 2. Scan cell contents for regex matches (emails and phone numbers)
        found_emails: set[str] = set()
        found_phones: set[str] = set()

        for row in rows:
            row_text = " ".join(row)
            for email in EMAIL_REGEX.findall(row_text):
                found_emails.add(email)
            for phone in PHONE_REGEX.findall(row_text):
                found_phones.add(phone)

        # 3. Assess Risk Level
        if found_emails or len(flagged_headers) > 0:
            if any("email" in h.lower() for h in flagged_headers) or found_emails:
                risk_level = "HIGH RISK (Direct PII Exposed)"
            else:
                risk_level = "MEDIUM RISK (Metadata/Identifiers present)"
        else:
            risk_level = "LOW / CLEAN (Anonymous Survey Data)"

        return {
            "file_name": path.name,
            "exists": True,
            "risk_level": risk_level,
            "pii_columns": flagged_headers,
            "found_emails": list(found_emails),
            "found_phones": list(found_phones),
            "total_rows_scanned": len(rows),
            "summary": (
                f"Scanned {len(rows)} rows. Detected {len(flagged_headers)} PII header(s), "
                f"{len(found_emails)} email(s), and {len(found_phones)} phone number(s)."
            ),
        }

    except Exception as exc:
        return {
            "file_name": path.name,
            "exists": True,
            "risk_level": "ERROR",
            "pii_columns": [],
            "found_emails": [],
            "found_phones": [],
            "summary": f"Audit error: {exc}",
        }


# Default to the Groww Mutual Fund SIP survey export
DEFAULT_SURVEY_FILE = (
    Path.home() / "Downloads" / "Untitled form (Responses) - Form Responses 1 (1).csv"
)


def print_pii_report(results: list[dict[str, Any]]) -> None:
    """Print formatted PII audit report."""
    print("=" * 80)
    print("           GROWW MUTUAL FUND SIP SURVEY - PRIVACY & PII AUDIT")
    print("=" * 80)

    for idx, res in enumerate(results, start=1):
        print(f"\n[{idx}] File: {res['file_name']}")
        print("-" * 80)
        print(f"  Risk Level       : {res['risk_level']}")
        print(f"  Summary          : {res['summary']}")

        if res["pii_columns"]:
            print(f"  Flagged Headers  : {', '.join(res['pii_columns'])}")
        else:
            print("  Flagged Headers  : None (clean - no sensitive PII headers)")

        if res["found_emails"]:
            # Display masked emails for safety
            masked_emails = [
                e.split("@")[0][:2] + "***@" + e.split("@")[1] for e in res["found_emails"]
            ]
            print(f"  Sample Emails    : {', '.join(masked_emails)}")

        if res["found_phones"]:
            print(f"  Sample Phones    : {', '.join(res['found_phones'])}")

    print("\n" + "=" * 80)


def main() -> None:
    """Audit the Groww Mutual Fund SIP survey file."""
    survey_files = [DEFAULT_SURVEY_FILE]
    results = [audit_survey_pii(f) for f in survey_files]
    print_pii_report(results)


if __name__ == "__main__":
    main()
