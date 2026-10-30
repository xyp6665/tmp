"""Echo JSON parameters to verify Agent-to-script argument passing."""
from __future__ import annotations

from typing import Any

from common import run_script


def json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "received": payload,
        "top_level_fields": list(payload.keys()),
        "top_level_types": {
            key: json_type(value) for key, value in payload.items()
        },
    }


if __name__ == "__main__":
    raise SystemExit(run_script("echo_params", handle))
