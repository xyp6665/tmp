#!/usr/bin/env python3
"""Persistent task planning utilities. Python standard library only."""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
import uuid
from collections import Counter
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any


VALID_PRIORITIES = {"high", "medium", "low"}
VALID_STATUSES = {"todo", "in_progress", "done", "cancelled"}
ALLOWED_UPDATE_FIELDS = {
    "title", "description", "priority", "start_at", "end_at",
    "deadline", "estimated_hours", "status", "dependencies", "tags",
}


def _default_store_path(store_path: str | None = None) -> Path:
    if store_path:
        return Path(store_path).expanduser()
    env_path = os.environ.get("TASK_PLANNER_STORE")
    return Path(env_path).expanduser() if env_path else Path("./data/tasks.json")


def _parse_datetime(value: str | datetime, field_name: str = "datetime") -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty ISO 8601 string.")
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} must use ISO 8601 format, for example 2026-11-02T09:00:00."
        ) from exc


def _validate_optional_datetime(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    return _parse_datetime(value, field_name).isoformat()


def _load_tasks(store_path: str | None = None) -> tuple[Path, list[dict[str, Any]]]:
    path = _default_store_path(store_path)
    if not path.exists():
        return path, []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Task store contains invalid JSON: {path}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
        raise ValueError("Task store must be a JSON object containing a 'tasks' list.")
    return path, payload["tasks"]


def _save_tasks(path: Path, tasks: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps({"tasks": tasks}, ensure_ascii=False, indent=2)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=str(path.parent),
            prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            handle.write(content)
            temp_name = handle.name
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)


def _validate_priority(priority: str) -> str:
    if priority not in VALID_PRIORITIES:
        raise ValueError(f"priority must be one of: {', '.join(sorted(VALID_PRIORITIES))}.")
    return priority


def _validate_status(status: str) -> str:
    if status not in VALID_STATUSES:
        raise ValueError(f"status must be one of: {', '.join(sorted(VALID_STATUSES))}.")
    return status


def _validate_string_list(value: list[str] | None, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field_name} must be a list of non-empty strings.")
    return [item.strip() for item in value]


def calculate_deadline(
    start_at: str,
    duration: float,
    unit: str = "hours",
    working_days_only: bool = False,
    holidays: list[str] | None = None,
) -> dict[str, Any]:
    """Calculate an end/deadline datetime; does not create or persist a task."""
    start = _parse_datetime(start_at, "start_at")
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        raise ValueError("duration must be a positive number.")
    if not math.isfinite(float(duration)) or duration <= 0:
        raise ValueError("duration must be a positive finite number.")

    if unit == "hours":
        if working_days_only:
            raise ValueError("working_days_only is supported only with unit='calendar_days' or 'working_days'.")
        end = start + timedelta(hours=float(duration))
    elif unit == "calendar_days":
        if working_days_only:
            if not float(duration).is_integer():
                raise ValueError("Working-day duration must be a whole number.")
            holiday_set = set(holidays or [])
            for item in holiday_set:
                date.fromisoformat(item)
            end = start
            remaining = int(duration)
            while remaining:
                end += timedelta(days=1)
                if end.weekday() < 5 and end.date().isoformat() not in holiday_set:
                    remaining -= 1
        else:
            end = start + timedelta(days=float(duration))
    elif unit == "working_days":
        if not float(duration).is_integer():
            raise ValueError("Working-day duration must be a whole number.")
        holiday_set = set(holidays or [])
        for item in holiday_set:
            date.fromisoformat(item)
        end = start
        remaining = int(duration)
        while remaining:
            end += timedelta(days=1)
            if end.weekday() < 5 and end.date().isoformat() not in holiday_set:
                remaining -= 1
    else:
        raise ValueError("unit must be 'hours', 'calendar_days', or 'working_days'.")

    return {
        "status": "success",
        "start_at": start.isoformat(),
        "duration": duration,
        "unit": unit,
        "deadline": end.isoformat(),
    }


def create_task(
    title: str,
    description: str = "",
    priority: str = "medium",
    start_at: str | None = None,
    end_at: str | None = None,
    deadline: str | None = None,
    estimated_hours: float | None = None,
    status: str = "todo",
    dependencies: list[str] | None = None,
    tags: list[str] | None = None,
    store_path: str | None = None,
) -> dict[str, Any]:
    """Create and persist one task."""
    if not isinstance(title, str) or not title.strip():
        raise ValueError("title is required.")
    if not isinstance(description, str):
        raise ValueError("description must be a string.")
    priority = _validate_priority(priority)
    status = _validate_status(status)

    normalized_start = _validate_optional_datetime(start_at, "start_at")
    normalized_end = _validate_optional_datetime(end_at, "end_at")
    normalized_deadline = _validate_optional_datetime(deadline, "deadline")

    if estimated_hours is not None:
        if isinstance(estimated_hours, bool) or not isinstance(estimated_hours, (int, float)):
            raise ValueError("estimated_hours must be a positive number.")
        if not math.isfinite(float(estimated_hours)) or estimated_hours <= 0:
            raise ValueError("estimated_hours must be a positive finite number.")

    if normalized_start and normalized_end:
        if _parse_datetime(normalized_end, "end_at") <= _parse_datetime(normalized_start, "start_at"):
            raise ValueError("end_at must be later than start_at.")
    elif normalized_start and normalized_end is None and estimated_hours is not None:
        normalized_end = calculate_deadline(normalized_start, estimated_hours, "hours")["deadline"]

    dependency_ids = _validate_string_list(dependencies, "dependencies")
    tag_list = _validate_string_list(tags, "tags")

    path, tasks = _load_tasks(store_path)
    known_ids = {task.get("task_id") for task in tasks}
    unknown = [item for item in dependency_ids if item not in known_ids]
    if unknown:
        raise ValueError(f"Unknown dependency task ID(s): {unknown}. Create dependencies first.")

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    task = {
        "task_id": uuid.uuid4().hex[:10],
        "title": title.strip(),
        "description": description.strip(),
        "priority": priority,
        "start_at": normalized_start,
        "end_at": normalized_end,
        "deadline": normalized_deadline,
        "estimated_hours": float(estimated_hours) if estimated_hours is not None else None,
        "status": status,
        "dependencies": dependency_ids,
        "tags": tag_list,
        "created_at": now,
        "completed_at": now if status == "done" else None,
    }
    tasks.append(task)
    _save_tasks(path, tasks)
    return {"status": "success", "task": task, "store_path": str(path)}


def list_tasks(
    status: str | None = None,
    priority: str | None = None,
    store_path: str | None = None,
) -> dict[str, Any]:
    """List stored tasks, optionally filtered by status and/or priority."""
    if status is not None:
        _validate_status(status)
    if priority is not None:
        _validate_priority(priority)
    path, tasks = _load_tasks(store_path)
    filtered = [
        task for task in tasks
        if (status is None or task.get("status") == status)
        and (priority is None or task.get("priority") == priority)
    ]
    return {"status": "success", "count": len(filtered), "tasks": filtered, "store_path": str(path)}


def update_task(
    task_id: str,
    title: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
    deadline: str | None = None,
    estimated_hours: float | None = None,
    status: str | None = None,
    dependencies: list[str] | None = None,
    tags: list[str] | None = None,
    store_path: str | None = None,
) -> dict[str, Any]:
    """Update an existing task. Only non-None fields are changed."""
    if not task_id:
        raise ValueError("task_id is required.")
    path, tasks = _load_tasks(store_path)
    task = next((item for item in tasks if item.get("task_id") == task_id), None)
    if task is None:
        raise ValueError(f"Task not found: {task_id}")

    updates = {
        "title": title, "description": description, "priority": priority,
        "start_at": start_at, "end_at": end_at, "deadline": deadline,
        "estimated_hours": estimated_hours, "status": status,
        "dependencies": dependencies, "tags": tags,
    }
    unknown = set(updates) - ALLOWED_UPDATE_FIELDS
    if unknown:
        raise ValueError(f"Unsupported update fields: {sorted(unknown)}")

    if title is not None:
        if not title.strip():
            raise ValueError("title cannot be empty.")
        task["title"] = title.strip()
    if description is not None:
        task["description"] = description
    if priority is not None:
        task["priority"] = _validate_priority(priority)
    if status is not None:
        task["status"] = _validate_status(status)
        if status == "done":
            task["completed_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        elif status != "done":
            task["completed_at"] = None
    if start_at is not None:
        task["start_at"] = _validate_optional_datetime(start_at, "start_at")
    if end_at is not None:
        task["end_at"] = _validate_optional_datetime(end_at, "end_at")
    if deadline is not None:
        task["deadline"] = _validate_optional_datetime(deadline, "deadline")
    if estimated_hours is not None:
        if isinstance(estimated_hours, bool) or not isinstance(estimated_hours, (int, float)):
            raise ValueError("estimated_hours must be a positive number.")
        if not math.isfinite(float(estimated_hours)) or estimated_hours <= 0:
            raise ValueError("estimated_hours must be a positive finite number.")
        task["estimated_hours"] = float(estimated_hours)
    if dependencies is not None:
        deps = _validate_string_list(dependencies, "dependencies")
        known_ids = {item.get("task_id") for item in tasks if item.get("task_id") != task_id}
        unknown_deps = [item for item in deps if item not in known_ids]
        if unknown_deps:
            raise ValueError(f"Unknown dependency task ID(s): {unknown_deps}.")
        task["dependencies"] = deps
    if tags is not None:
        task["tags"] = _validate_string_list(tags, "tags")

    if task.get("start_at") and task.get("end_at"):
        if _parse_datetime(task["end_at"], "end_at") <= _parse_datetime(task["start_at"], "start_at"):
            raise ValueError("end_at must be later than start_at.")
    elif task.get("start_at") and task.get("estimated_hours") and (
        start_at is not None or estimated_hours is not None
    ):
        task["end_at"] = calculate_deadline(
            task["start_at"], task["estimated_hours"], "hours"
        )["deadline"]

    _save_tasks(path, tasks)
    return {"status": "success", "task": task, "store_path": str(path)}


def check_conflicts(
    task_id: str | None = None,
    store_path: str | None = None,
) -> dict[str, Any]:
    """Check overlapping scheduled intervals among active tasks."""
    path, tasks = _load_tasks(store_path)
    active = [
        task for task in tasks
        if task.get("status") not in {"done", "cancelled"}
        and task.get("start_at") and task.get("end_at")
    ]
    if task_id is not None:
        selected = next((task for task in active if task.get("task_id") == task_id), None)
        if selected is None:
            raise ValueError(f"Active scheduled task not found: {task_id}")
        candidates = [task for task in active if task.get("task_id") != task_id]
        pairs = [(selected, other) for other in candidates]
    else:
        pairs = [
            (active[i], active[j])
            for i in range(len(active))
            for j in range(i + 1, len(active))
        ]

    conflicts = []
    for first, second in pairs:
        first_start = _parse_datetime(first["start_at"], "start_at")
        first_end = _parse_datetime(first["end_at"], "end_at")
        second_start = _parse_datetime(second["start_at"], "start_at")
        second_end = _parse_datetime(second["end_at"], "end_at")
        try:
            overlaps = first_start < second_end and second_start < first_end
        except TypeError as exc:
            raise ValueError(
                "Cannot compare timezone-aware and timezone-naive task times. "
                "Use a consistent timezone format in the task store."
            ) from exc
        if overlaps:
            conflicts.append({
                "task_1": {"task_id": first["task_id"], "title": first["title"],
                           "start_at": first["start_at"], "end_at": first["end_at"]},
                "task_2": {"task_id": second["task_id"], "title": second["title"],
                           "start_at": second["start_at"], "end_at": second["end_at"]},
            })

    return {
        "status": "success",
        "checked_task_count": len(active),
        "conflict_count": len(conflicts),
        "conflicts": conflicts,
        "store_path": str(path),
    }


def summarize_tasks(
    store_path: str | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Summarize counts, completion rate, overdue tasks, and upcoming deadlines."""
    path, tasks = _load_tasks(store_path)
    reference = _parse_datetime(as_of, "as_of") if as_of else datetime.now().astimezone()

    status_counts = Counter(task.get("status", "todo") for task in tasks)
    priority_counts = Counter(task.get("priority", "medium") for task in tasks)
    done_count = status_counts.get("done", 0)
    total = len(tasks)

    overdue = []
    upcoming = []
    for task in tasks:
        due = task.get("deadline")
        if not due or task.get("status") in {"done", "cancelled"}:
            continue
        due_dt = _parse_datetime(due, "deadline")
        try:
            is_overdue = due_dt < reference
        except TypeError as exc:
            raise ValueError(
                "Cannot compare timezone-aware and timezone-naive task times. "
                "Use a consistent timezone format."
            ) from exc
        if is_overdue:
            overdue.append({"task_id": task["task_id"], "title": task["title"], "deadline": due})
        else:
            upcoming.append({"task_id": task["task_id"], "title": task["title"], "deadline": due})

    upcoming.sort(key=lambda item: _parse_datetime(item["deadline"], "deadline"))
    overdue.sort(key=lambda item: _parse_datetime(item["deadline"], "deadline"))

    return {
        "status": "success",
        "summary": {
            "total_tasks": total,
            "completed_tasks": done_count,
            "completion_rate": round((done_count / total * 100), 2) if total else 0.0,
            "overdue_count": len(overdue),
            "overdue_tasks": overdue,
            "status_counts": {key: status_counts.get(key, 0) for key in sorted(VALID_STATUSES)},
            "priority_counts": {key: priority_counts.get(key, 0) for key in sorted(VALID_PRIORITIES)},
            "next_deadlines": upcoming[:5],
        },
        "store_path": str(path),
    }


def _dispatch(action: str, payload: dict[str, Any], store_path: str | None = None) -> dict[str, Any]:
    if action == "create_task":
        return create_task(store_path=store_path, **payload)
    if action == "calculate_deadline":
        return calculate_deadline(**payload)
    if action == "check_conflicts":
        return check_conflicts(store_path=store_path, **payload)
    if action == "summarize_tasks":
        return summarize_tasks(store_path=store_path, **payload)
    if action == "list_tasks":
        return list_tasks(store_path=store_path, **payload)
    if action == "update_task":
        return update_task(store_path=store_path, **payload)
    raise ValueError(f"Unknown action: {action}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Smart Task Planner utility CLI.")
    parser.add_argument(
        "--action",
        required=True,
        choices=["create_task", "calculate_deadline", "check_conflicts",
                 "summarize_tasks", "list_tasks", "update_task"],
    )
    parser.add_argument("--input-json", help="JSON object passed to the selected function.")
    parser.add_argument("--input-file", help="Read JSON object from a UTF-8 file.")
    parser.add_argument("--store", help="Path to persistent task JSON store.")
    args = parser.parse_args()

    try:
        if args.input_json is not None:
            payload = json.loads(args.input_json)
        elif args.input_file:
            payload = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
        else:
            raw = sys.stdin.read()
            payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            raise ValueError("Input payload must be a JSON object.")
        result = _dispatch(args.action, payload, args.store)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            "status": "error",
            "error": {"type": type(exc).__name__, "message": str(exc)}
        }, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
