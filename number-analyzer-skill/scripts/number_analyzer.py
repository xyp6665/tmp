#!/usr/bin/env python3
"""Descriptive statistics and IQR outlier detection for a list of numbers."""
from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import Counter
from typing import Any


def _clean_number(value: int | float, index: int) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"numbers[{index}] must be an integer or float.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"numbers[{index}] must be finite; NaN and infinity are not allowed.")
    return number


def _round_number(value: float | int | None) -> int | float | None:
    if value is None:
        return None
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("Calculation produced a non-finite result.")
    if abs(value) < 0.0000005:
        value = 0.0
    rounded = round(value, 6)
    if rounded.is_integer():
        return int(rounded)
    return rounded


def _quantile(sorted_values: list[float], probability: float) -> float:
    """Linear interpolation quantile using position (n - 1) * p."""
    if not sorted_values:
        raise ValueError("Cannot calculate a quantile from an empty list.")
    if not 0 <= probability <= 1:
        raise ValueError("probability must be between 0 and 1.")
    position = (len(sorted_values) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return sorted_values[lower_index]
    weight = position - lower_index
    return (
        sorted_values[lower_index] * (1 - weight)
        + sorted_values[upper_index] * weight
    )


def analyze_numbers(numbers: list[int | float]) -> dict[str, Any]:
    """Analyze a non-empty list of finite numbers and return JSON-ready data."""
    if not isinstance(numbers, list) or not numbers:
        raise ValueError("numbers must be a non-empty list.")

    values = [_clean_number(value, index) for index, value in enumerate(numbers)]
    ordered = sorted(values)
    count = len(values)

    total = math.fsum(values)
    mean_value = statistics.fmean(values)
    median_value = statistics.median(ordered)
    minimum = ordered[0]
    maximum = ordered[-1]
    population_variance = statistics.pvariance(values)
    population_std_dev = math.sqrt(population_variance)

    if count >= 2:
        sample_variance = statistics.variance(values)
        sample_std_dev = math.sqrt(sample_variance)
    else:
        sample_variance = None
        sample_std_dev = None

    q1 = _quantile(ordered, 0.25)
    q2 = _quantile(ordered, 0.50)
    q3 = _quantile(ordered, 0.75)
    iqr = q3 - q1

    if count >= 4:
        lower_fence = q1 - 1.5 * iqr
        upper_fence = q3 + 1.5 * iqr
        outliers = [value for value in values if value < lower_fence or value > upper_fence]
        outlier_detection = {
            "method": "IQR",
            "status": "completed",
            "lower_fence": _round_number(lower_fence),
            "upper_fence": _round_number(upper_fence),
            "outlier_count": len(outliers),
            "outliers": [_round_number(value) for value in outliers],
            "interpretation": "Potential statistical outliers; review context before treating them as errors."
        }
    else:
        outlier_detection = {
            "method": "IQR",
            "status": "insufficient_data",
            "lower_fence": None,
            "upper_fence": None,
            "outlier_count": 0,
            "outliers": [],
            "interpretation": "At least 4 values are required for this tool's IQR screening."
        }

    counts = Counter(values)
    duplicates = [
        {"value": _round_number(value), "count": frequency}
        for value, frequency in sorted(counts.items())
        if frequency > 1
    ]

    data = {
        "input_numbers": numbers,
        "count": count,
        "sum": _round_number(total),
        "mean": _round_number(mean_value),
        "median": _round_number(median_value),
        "min": _round_number(minimum),
        "max": _round_number(maximum),
        "range": _round_number(maximum - minimum),
        "dispersion": {
            "variance_population": _round_number(population_variance),
            "std_dev_population": _round_number(population_std_dev),
            "variance_sample": _round_number(sample_variance),
            "std_dev_sample": _round_number(sample_std_dev)
        },
        "quartiles": {
            "method": "linear_interpolation",
            "q1": _round_number(q1),
            "q2": _round_number(q2),
            "q3": _round_number(q3),
            "iqr": _round_number(iqr)
        },
        "outlier_detection": outlier_detection,
        "number_categories": {
            "positive_count": sum(1 for value in values if value > 0),
            "negative_count": sum(1 for value in values if value < 0),
            "zero_count": sum(1 for value in values if value == 0),
            "integer_count": sum(1 for value in values if value.is_integer())
        },
        "duplicates": duplicates
    }

    return {"status": "success", "data": data, "error": None}


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze a list of numbers and output JSON.")
    parser.add_argument("--input-json", help='JSON object, e.g. {"numbers":[1,2,3]}')
    parser.add_argument("--input-file", help="Path to a UTF-8 JSON input file.")
    args = parser.parse_args()

    try:
        if args.input_json is not None:
            payload = json.loads(args.input_json)
        elif args.input_file:
            with open(args.input_file, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        else:
            raw = sys.stdin.read()
            payload = json.loads(raw) if raw.strip() else {}

        if not isinstance(payload, dict):
            raise ValueError("Input must be a JSON object.")
        result = analyze_numbers(payload.get("numbers"))
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except Exception as exc:
        error_result = {
            "status": "error",
            "data": None,
            "error": {
                "type": type(exc).__name__,
                "message": str(exc)
            }
        }
        print(json.dumps(error_result, ensure_ascii=False, indent=2, allow_nan=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
