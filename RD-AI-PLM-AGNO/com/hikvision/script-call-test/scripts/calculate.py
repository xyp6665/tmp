"""Perform basic arithmetic from a JSON request."""
from __future__ import annotations

import math
from typing import Any

from common import run_script


SUPPORTED_OPERATIONS = {"add", "subtract", "multiply", "divide"}


def normalize_number(value: float | int) -> float | int:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return round(value, 12) if isinstance(value, float) else value


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    operation = payload.get("operation")
    values = payload.get("values")

    if operation not in SUPPORTED_OPERATIONS:
        allowed = ", ".join(sorted(SUPPORTED_OPERATIONS))
        raise ValueError(f"Unsupported operation. Choose one of: {allowed}.")

    if not isinstance(values, list) or len(values) < 2:
        raise ValueError("'values' must be a list containing at least two numbers.")

    for index, value in enumerate(values):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"values[{index}] must be a number.")
        if not math.isfinite(value):
            raise ValueError(f"values[{index}] must be finite.")

    if operation == "add":
        result = math.fsum(values)
    elif operation == "subtract":
        result = values[0]
        for value in values[1:]:
            result -= value
    elif operation == "multiply":
        result = math.prod(values)
    else:
        result = values[0]
        for value in values[1:]:
            if value == 0:
                raise ZeroDivisionError("Cannot divide by zero.")
            result /= value

    if isinstance(result, float) and not math.isfinite(result):
        raise OverflowError("The calculation produced a non-finite result.")

    return {
        "operation": operation,
        "values": values,
        "result": normalize_number(result),
    }


if __name__ == "__main__":
    raise SystemExit(run_script("calculate", handle))
