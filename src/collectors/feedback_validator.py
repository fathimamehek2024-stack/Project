"""Feedback Data Validator.

This module checks that the raw investor feedback CSV dataset exists,
verifies that all required columns are present, and reports the total
count of collected feedback records.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

# The 8 mandatory columns required for the mutual fund SIP discovery dataset
REQUIRED_COLUMNS: list[str] = [
    "feedback_id",
    "source",
    "source_url",
    "date",
    "feedback_text",
    "investor_stage",
    "sip_behavior",
    "collection_method",
]

# Default location for the raw feedback file
DEFAULT_CSV_PATH = Path("data/raw/investor_feedback.csv")


def validate_feedback_csv(file_path: Path | str = DEFAULT_CSV_PATH) -> dict[str, Any]:
    """Validate existence, columns, and record count of the feedback CSV file.

    Parameters
    ----------
    file_path : Path | str
        Path to the CSV file to validate. Defaults to 'data/raw/investor_feedback.csv'.

    Returns
    -------
    dict[str, Any]
        Dictionary with validation results containing:
        - 'is_valid' (bool): True if file exists and contains all required columns.
        - 'file_exists' (bool): Whether the file was found.
        - 'file_path' (str): String representation of the path.
        - 'required_columns' (list[str]): List of expected column names.
        - 'actual_columns' (list[str]): Column names found in the CSV.
        - 'missing_columns' (list[str]): Columns that are missing.
        - 'record_count' (int): Total number of data rows (excluding header).
        - 'message' (str): Human-readable summary message.
    """
    path = Path(file_path)

    # 1. Check if the file exists
    if not path.is_file():
        return {
            "is_valid": False,
            "file_exists": False,
            "file_path": str(path),
            "required_columns": REQUIRED_COLUMNS,
            "actual_columns": [],
            "missing_columns": REQUIRED_COLUMNS,
            "record_count": 0,
            "message": f"Error: File '{path}' does not exist.",
        }

    # 2. Read headers and count records
    try:
        with open(path, mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            header_row = next(reader, None)

            if header_row is None:
                return {
                    "is_valid": False,
                    "file_exists": True,
                    "file_path": str(path),
                    "required_columns": REQUIRED_COLUMNS,
                    "actual_columns": [],
                    "missing_columns": REQUIRED_COLUMNS,
                    "record_count": 0,
                    "message": f"Error: File '{path}' is empty and has no headers.",
                }

            # Strip whitespace from column names
            actual_columns = [col.strip() for col in header_row]

            # Count rows (excluding empty lines)
            records = [row for row in reader if any(field.strip() for field in row)]
            record_count = len(records)

    except Exception as exc:
        return {
            "is_valid": False,
            "file_exists": True,
            "file_path": str(path),
            "required_columns": REQUIRED_COLUMNS,
            "actual_columns": [],
            "missing_columns": REQUIRED_COLUMNS,
            "record_count": 0,
            "message": f"Error reading '{path}': {exc}",
        }

    # 3. Check for missing columns
    actual_set = set(actual_columns)
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in actual_set]

    is_valid = len(missing_columns) == 0

    if is_valid:
        message = (
            f"Success: File '{path}' is valid with all {len(REQUIRED_COLUMNS)} required "
            f"columns present. Current records: {record_count}."
        )
    else:
        message = (
            f"Error: File '{path}' is missing {len(missing_columns)} required column(s): "
            f"{', '.join(missing_columns)}."
        )

    return {
        "is_valid": is_valid,
        "file_exists": True,
        "file_path": str(path),
        "required_columns": REQUIRED_COLUMNS,
        "actual_columns": actual_columns,
        "missing_columns": missing_columns,
        "record_count": record_count,
        "message": message,
    }


def main() -> None:
    """Run validation from the command line and display formatted report."""
    print("=" * 65)
    print("  Investor Feedback Dataset Validator")
    print("=" * 65)

    result = validate_feedback_csv()

    print(f"File Path        : {result['file_path']}")
    print(f"File Exists      : {'Yes' if result['file_exists'] else 'No'}")
    print(f"Schema Valid     : {'PASS' if result['is_valid'] else 'FAIL'}")
    print(f"Total Records    : {result['record_count']}")

    if result["missing_columns"]:
        print(f"Missing Columns  : {', '.join(result['missing_columns'])}")
    else:
        print(f"Required Columns : All {len(REQUIRED_COLUMNS)} columns present")

    print("-" * 65)
    print(f"Summary          : {result['message']}")
    print("=" * 65)


if __name__ == "__main__":
    main()
