"""Survey Structure and Metadata Inspector.

Inspects Google Forms CSV exports to report row counts, column counts,
cleaned column names, and exact duplicate response rates.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def inspect_survey_csv(file_path: Path | str) -> dict[str, Any]:
    """Inspect the structure, rows, columns, and duplicates of a survey CSV.

    Parameters
    ----------
    file_path : Path | str
        Path to the CSV file to inspect.

    Returns
    -------
    dict[str, Any]
        Dictionary containing structural metadata.
    """
    path = Path(file_path)

    if not path.is_file():
        return {
            "file_name": path.name,
            "file_path": str(path),
            "exists": False,
            "error": f"File not found at {path}",
            "row_count": 0,
            "column_count": 0,
            "columns": [],
            "duplicate_count": 0,
            "unique_count": 0,
        }

    # Use 'utf-8-sig' to automatically handle Byte Order Mark (\ufeff) from Google Forms / Excel
    try:
        with open(path, mode="r", encoding="utf-8-sig", newline="", errors="replace") as f:
            reader = list(csv.reader(f))

        if not reader:
            return {
                "file_name": path.name,
                "file_path": str(path),
                "exists": True,
                "error": "File is empty (0 bytes).",
                "row_count": 0,
                "column_count": 0,
                "columns": [],
                "duplicate_count": 0,
                "unique_count": 0,
            }

        # Strip whitespace from headers
        columns = [col.strip() for col in reader[0]]
        data_rows = reader[1:]

        # Filter out completely empty rows
        non_empty_rows = [row for row in data_rows if any(cell.strip() for cell in row)]
        row_count = len(non_empty_rows)

        # Count exact duplicates
        row_tuples = [tuple(cell.strip() for cell in row) for row in non_empty_rows]
        unique_count = len(set(row_tuples))
        duplicate_count = row_count - unique_count

        return {
            "file_name": path.name,
            "file_path": str(path),
            "exists": True,
            "error": None,
            "row_count": row_count,
            "column_count": len(columns),
            "columns": columns,
            "duplicate_count": duplicate_count,
            "unique_count": unique_count,
        }

    except Exception as exc:
        return {
            "file_name": path.name,
            "file_path": str(path),
            "exists": True,
            "error": f"Error reading file: {exc}",
            "row_count": 0,
            "column_count": 0,
            "columns": [],
            "duplicate_count": 0,
            "unique_count": 0,
        }


# Default to the Groww Mutual Fund SIP survey export
DEFAULT_SURVEY_FILE = (
    Path.home() / "Downloads" / "Untitled form (Responses) - Form Responses 1 (1).csv"
)


def print_inspection_report(results: list[dict[str, Any]]) -> None:
    """Print a clean, formatted terminal report."""
    print("=" * 80)
    print("       GROWW MUTUAL FUND SIP SURVEY - STRUCTURAL INSPECTION REPORT")
    print("=" * 80)

    for idx, res in enumerate(results, start=1):
        print(f"\n[{idx}] File: {res['file_name']}")
        print("-" * 80)

        if not res["exists"]:
            print(f"  Status   : ERROR - {res['error']}")
            continue

        if res["error"]:
            print(f"  Status   : WARNING - {res['error']}")
            continue

        print(f"  Path              : {res['file_path']}")
        print(f"  Data Rows (Users) : {res['row_count']}")
        print(f"  Columns (Fields)  : {res['column_count']}")
        print(f"  Unique Responses  : {res['unique_count']}")
        print(f"  Exact Duplicates  : {res['duplicate_count']}")

        print(f"\n  Survey Questions ({res['column_count']} total):")
        for col_idx, col_name in enumerate(res["columns"], start=1):
            print(f"    {col_idx:2d}. {col_name}")

    print("\n" + "=" * 80)


def main() -> None:
    """Inspect the Groww Mutual Fund SIP survey file."""
    survey_files = [DEFAULT_SURVEY_FILE]
    results = [inspect_survey_csv(f) for f in survey_files]
    print_inspection_report(results)


if __name__ == "__main__":
    main()
