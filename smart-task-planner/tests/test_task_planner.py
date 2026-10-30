from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from task_planner import (
    calculate_deadline,
    create_task,
    check_conflicts,
    summarize_tasks,
    list_tasks,
    update_task,
)


class SmartTaskPlannerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = str(Path(self.temp.name) / "tasks.json")

    def tearDown(self):
        self.temp.cleanup()

    def test_calculate_deadline_hours(self):
        result = calculate_deadline("2026-11-02T09:00:00", 2, "hours")
        self.assertEqual(result["deadline"], "2026-11-02T11:00:00")

    def test_calculate_working_days_skips_weekend(self):
        result = calculate_deadline("2026-11-06T09:00:00", 1, "working_days")
        self.assertEqual(result["deadline"], "2026-11-09T09:00:00")

    def test_create_task_persists_and_calculates_end(self):
        result = create_task(
            title="Collect data",
            priority="high",
            start_at="2026-11-02T09:00:00",
            estimated_hours=2,
            store_path=self.store,
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["task"]["end_at"], "2026-11-02T11:00:00")
        listed = list_tasks(store_path=self.store)
        self.assertEqual(listed["count"], 1)

    def test_dependencies_must_exist(self):
        with self.assertRaises(ValueError):
            create_task(
                title="Write report",
                dependencies=["not-a-real-id"],
                store_path=self.store,
            )

    def test_conflict_detection_and_adjacent_events(self):
        first = create_task(
            title="Task A", start_at="2026-11-02T09:00:00",
            end_at="2026-11-02T10:00:00", store_path=self.store,
        )["task"]
        create_task(
            title="Task B", start_at="2026-11-02T09:30:00",
            end_at="2026-11-02T10:30:00", store_path=self.store,
        )
        create_task(
            title="Task C", start_at="2026-11-02T10:30:00",
            end_at="2026-11-02T11:30:00", store_path=self.store,
        )
        result = check_conflicts(store_path=self.store)
        self.assertEqual(result["conflict_count"], 1)
        self.assertEqual(result["conflicts"][0]["task_1"]["task_id"], first["task_id"])

    def test_update_and_summary(self):
        task = create_task(
            title="Task done",
            status="todo",
            priority="high",
            deadline="2026-11-01T18:00:00",
            store_path=self.store,
        )["task"]
        update_task(task["task_id"], status="done", store_path=self.store)
        create_task(
            title="Task pending",
            status="todo",
            priority="medium",
            deadline="2026-11-01T18:00:00",
            store_path=self.store,
        )
        result = summarize_tasks(
            store_path=self.store,
            as_of="2026-11-02T09:00:00",
        )["summary"]
        self.assertEqual(result["total_tasks"], 2)
        self.assertEqual(result["completed_tasks"], 1)
        self.assertEqual(result["completion_rate"], 50.0)
        self.assertEqual(result["overdue_count"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
