#!/usr/bin/env python3
"""CSV descriptive analysis tool. Standard-library only."""
from __future__ import annotations

import argparse
import csv
import json
import math
import io
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any


def _is_missing(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _to_number(value: Any) -> float | None:
    if _is_missing(value):
        return None
    text = str(value).strip().replace(",", "")
    if text.startswith("$"):
        text = text[1:]
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _number_for_json(value: float | None) -> int | float | None:
    if value is None:
        return None
    if float(value).is_integer():
        return int(value)
    return round(float(value), 4)


def _is_identifier(column: str) -> bool:
    normalized = column.strip().lower()
    return normalized == "id" or normalized.endswith("_id")


def _parse_date(value: Any) -> date | None:
    if _is_missing(value):
        return None
    text = str(value).strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    for fmt in ("%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _read_csv(input_path: str) -> tuple[list[str], list[dict[str, str]], str]:
    path = Path(input_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")
    if not path.is_file():
        raise ValueError(f"Input path is not a file: {path}")

    # utf-8-sig handles files saved with a BOM. Fall back to latin-1 only if needed.
    try:
        text = path.read_text(encoding="utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        text = path.read_text(encoding="latin-1")
        encoding = "latin-1"

    if not text.strip():
        raise ValueError("CSV file is empty.")

    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("CSV header row is missing.")

    headers = [str(name).strip() if name is not None else "" for name in reader.fieldnames]
    if any(not name for name in headers):
        raise ValueError("CSV contains an empty column name.")
    if len(set(headers)) != len(headers):
        raise ValueError("CSV contains duplicate column names.")

    rows: list[dict[str, str]] = []
    for row in reader:
        # Ignore completely blank physical rows.
        if row and all(_is_missing(value) for value in row.values()):
            continue
        normalized = {}
        for key, value in row.items():
            if key is not None:
                normalized[key.strip()] = value.strip() if isinstance(value, str) else value
        rows.append(normalized)

    return headers, rows, encoding


def analyze_csv(
    input_path: str,
    group_by: str | None = None,
    metric: str | None = None,
    top_n: int = 10,
    output_path: str | None = None,
) -> dict[str, Any]:
    """Analyze a CSV and return a JSON-serializable result dictionary."""
    if not isinstance(top_n, int) or isinstance(top_n, bool) or top_n < 1:
        raise ValueError("top_n must be a positive integer.")

    headers, rows, encoding = _read_csv(input_path)
    if not rows:
        raise ValueError("CSV contains headers but no data rows.")

    header_set = set(headers)
    for field_name, field_value in (("group_by", group_by), ("metric", metric)):
        if field_value is not None and field_value not in header_set:
            raise ValueError(
                f"Unknown {field_name} column '{field_value}'. Available columns: {headers}"
            )

    missing_values = []
    for column in headers:
        missing_count = sum(1 for row in rows if _is_missing(row.get(column)))
        missing_values.append({
            "column": column,
            "missing_count": missing_count,
            "missing_rate": round(missing_count / len(rows), 4),
        })

    row_signatures = [tuple(row.get(column, "") for column in headers) for row in rows]
    duplicate_count = len(row_signatures) - len(set(row_signatures))

    numeric_columns: dict[str, list[float]] = {}
    date_columns: dict[str, list[date]] = {}
    identifier_columns = [column for column in headers if _is_identifier(column)]

    for column in headers:
        if column in identifier_columns:
            continue
        non_empty = [row.get(column) for row in rows if not _is_missing(row.get(column))]
        if not non_empty:
            continue
        parsed_numbers = [_to_number(value) for value in non_empty]
        if all(value is not None for value in parsed_numbers):
            numeric_columns[column] = [float(value) for value in parsed_numbers if value is not None]
            continue

        # Date recognition is attempted for date-like names or when most values parse as dates.
        parsed_dates = [_parse_date(value) for value in non_empty]
        date_like_name = "date" in column.lower() or "time" in column.lower()
        valid_dates = [value for value in parsed_dates if value is not None]
        if valid_dates and (date_like_name or len(valid_dates) / len(non_empty) >= 0.8):
            date_columns[column] = valid_dates

    categorical_columns = [
        column for column in headers
        if column not in numeric_columns
        and column not in date_columns
        and column not in identifier_columns
    ]

    numeric_summary: dict[str, Any] = {}
    for column, values in numeric_columns.items():
        numeric_summary[column] = {
            "count": len(values),
            "missing_count": len(rows) - len(values),
            "sum": _number_for_json(math.fsum(values)),
            "mean": _number_for_json(statistics.fmean(values)),
            "median": _number_for_json(statistics.median(values)),
            "std_dev": _number_for_json(statistics.stdev(values) if len(values) > 1 else 0.0),
            "min": _number_for_json(min(values)),
            "max": _number_for_json(max(values)),
        }

    categorical_summary: dict[str, Any] = {}
    for column in categorical_columns:
        values = [str(row.get(column, "")).strip() for row in rows if not _is_missing(row.get(column))]
        counts = Counter(values)
        categorical_summary[column] = {
            "unique_count": len(counts),
            "top_values": [
                {"value": value, "count": count}
                for value, count in counts.most_common(top_n)
            ],
        }

    date_summary: dict[str, Any] = {}
    for column, values in date_columns.items():
        date_summary[column] = {
            "valid_date_count": len(values),
            "min_date": min(values).isoformat(),
            "max_date": max(values).isoformat(),
        }

    # Auto-select sensible defaults only when the caller did not specify fields.
    selected_group = group_by
    if selected_group is None:
        selected_group = "region" if "region" in categorical_columns else (
            categorical_columns[0] if categorical_columns else None
        )

    selected_metric = metric
    if selected_metric is None:
        selected_metric = "sales_amount" if "sales_amount" in numeric_columns else (
            next(iter(numeric_columns), None)
        )

    if group_by is not None and group_by not in categorical_columns:
        raise ValueError(f"group_by column '{group_by}' is not a categorical column.")
    if metric is not None and metric not in numeric_columns:
        raise ValueError(f"metric column '{metric}' is not a recognized numeric column.")

    grouped_summary: dict[str, Any] | None = None
    if selected_group is not None and selected_metric is not None:
        groups: dict[str, list[float]] = defaultdict(list)
        group_row_counts: Counter[str] = Counter()
        for row in rows:
            key_value = row.get(selected_group)
            if _is_missing(key_value):
                continue
            key = str(key_value).strip()
            group_row_counts[key] += 1
            number = _to_number(row.get(selected_metric))
            if number is not None:
                groups[key].append(number)

        group_items = []
        for key, row_count in group_row_counts.items():
            values = groups.get(key, [])
            group_items.append({
                "group": key,
                "row_count": row_count,
                "metric_count": len(values),
                "metric_sum": _number_for_json(math.fsum(values)) if values else None,
                "metric_mean": _number_for_json(statistics.fmean(values)) if values else None,
            })
        group_items.sort(
            key=lambda item: (
                item["metric_sum"] is not None,
                item["metric_sum"] if item["metric_sum"] is not None else float("-inf"),
            ),
            reverse=True,
        )
        grouped_summary = {
            "group_by": selected_group,
            "metric": selected_metric,
            "groups": group_items,
        }

    report: dict[str, Any] = {
        "status": "success",
        "data": {
            "file": Path(input_path).name,
            "encoding": encoding,
            "overview": {
                "row_count": len(rows),
                "column_count": len(headers),
                "columns": headers,
                "numeric_columns": list(numeric_columns.keys()),
                "categorical_columns": categorical_columns,
                "date_columns": list(date_columns.keys()),
                "identifier_columns": identifier_columns,
            },
            "missing_values": missing_values,
            "duplicate_rows": {
                "duplicate_count": duplicate_count,
                "unique_row_count": len(set(row_signatures)),
            },
            "numeric_summary": numeric_summary,
            "categorical_summary": categorical_summary,
            "date_summary": date_summary,
            "grouped_summary": grouped_summary,
        },
        "error": None,
    }

    if output_path:
        output = Path(output_path).expanduser()
        output.parent.mkdir(parents=True, exist_ok=True)
        report["data"]["report_saved_to"] = str(output)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze a CSV file and return a JSON report.")
    parser.add_argument("--input", required=True, help="Path to the CSV file.")
    parser.add_argument("--group-by", dest="group_by", help="Categorical column used for grouping.")
    parser.add_argument("--metric", help="Numeric column to aggregate.")
    parser.add_argument("--top-n", type=int, default=10, help="Top categories to show (default: 10).")
    parser.add_argument("--output", help="Optional path to save the JSON report.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        result = analyze_csv(
            input_path=args.input,
            group_by=args.group_by,
            metric=args.metric,
            top_n=args.top_n,
            output_path=args.output,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        error_result = {
            "status": "error",
            "data": None,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc),
            },
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
