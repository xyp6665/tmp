"""Shared JSON input/output helpers for script-call-test."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable


def load_payload() -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Read a JSON object from stdin or a file.")
    parser.add_argument(
        "--input-file",
        help="Path to a UTF-8 JSON input file. If omitted, JSON is read from stdin.",
    )
    args = parser.parse_args()

    if args.input_file:
        raw = Path(args.input_file).read_text(encoding="utf-8")
    else:
        raw = sys.stdin.read()

    if not raw.strip():
        raise ValueError("No JSON input received. Provide stdin JSON or --input-file.")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON input at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(payload, dict):
        raise ValueError("Input must be a JSON object.")
    return payload


def emit_result(
    *,
    status: str,
    script: str,
    data: Any = None,
    error: dict[str, str] | None = None,
) -> None:
    result = {
        "status": status,
        "script": script,
        "data": data,
        "error": error,
    }
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


def run_script(script: str, handler: Callable[[dict[str, Any]], Any]) -> int:
    try:
        payload = load_payload()
        data = handler(payload)
        emit_result(status="success", script=script, data=data, error=None)
        return 0
    except Exception as exc:  # Return a structured error rather than a traceback.
        emit_result(
            status="error",
            script=script,
            data=None,
            error={
                "type": type(exc).__name__,
                "message": str(exc),
            },
        )
        return 1
