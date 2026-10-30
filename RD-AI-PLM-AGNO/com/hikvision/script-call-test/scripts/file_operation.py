"""Safe text-file operations constrained to a workspace directory."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from common import run_script


def get_workspace(payload: dict[str, Any]) -> Path:
    raw_workspace = payload.get("workspace") or os.environ.get(
        "SCRIPT_CALL_TEST_WORKSPACE", "./script-call-test-workspace"
    )
    if not isinstance(raw_workspace, str) or not raw_workspace.strip():
        raise ValueError("'workspace' must be a non-empty path string.")

    workspace = Path(raw_workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    if not workspace.is_dir():
        raise NotADirectoryError("Workspace path is not a directory.")
    return workspace


def safe_target(workspace: Path, relative_path: Any) -> Path:
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise ValueError("A non-empty relative path is required.")

    supplied = Path(relative_path)
    if supplied.is_absolute():
        raise ValueError("Absolute paths are not allowed.")

    root = workspace.resolve()
    target = (root / supplied).resolve()

    try:
        target.relative_to(root)
    except ValueError as exc:
        raise ValueError("Path escapes the workspace; operation rejected.") from exc

    return target


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    action = payload.get("action")
    if action not in {"write", "read", "list"}:
        raise ValueError("'action' must be one of: write, read, list.")

    workspace = get_workspace(payload)

    if action == "write":
        filename = payload.get("filename")
        content = payload.get("content")
        if not isinstance(content, str):
            raise ValueError("'content' must be a string.")

        target = safe_target(workspace, filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        # Resolve again after creating parent directories.
        target = safe_target(workspace, filename)
        target.write_text(content, encoding="utf-8")
        return {
            "action": "write",
            "relative_path": target.relative_to(workspace).as_posix(),
            "bytes_written": len(content.encode("utf-8")),
        }

    if action == "read":
        target = safe_target(workspace, payload.get("filename"))
        if not target.exists() or not target.is_file():
            raise FileNotFoundError("The requested file does not exist in the workspace.")
        content = target.read_text(encoding="utf-8")
        return {
            "action": "read",
            "relative_path": target.relative_to(workspace).as_posix(),
            "content": content,
            "characters_read": len(content),
        }

    directory = payload.get("directory", ".")
    target_dir = safe_target(workspace, directory)
    if not target_dir.exists() or not target_dir.is_dir():
        raise NotADirectoryError("The requested directory does not exist in the workspace.")

    entries = []
    for item in sorted(target_dir.iterdir(), key=lambda path: path.name.lower()):
        if item.is_symlink():
            kind = "symlink"
            size_bytes = None
        elif item.is_dir():
            kind = "directory"
            size_bytes = None
        elif item.is_file():
            kind = "file"
            size_bytes = item.stat().st_size
        else:
            kind = "other"
            size_bytes = None

        entries.append({
            "name": item.name,
            "type": kind,
            "size_bytes": size_bytes,
        })

    return {
        "action": "list",
        "relative_directory": target_dir.relative_to(workspace).as_posix() or ".",
        "entries": entries,
        "entry_count": len(entries),
    }


if __name__ == "__main__":
    raise SystemExit(run_script("file_operation", handle))
