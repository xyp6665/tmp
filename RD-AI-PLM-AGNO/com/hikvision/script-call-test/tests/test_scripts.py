from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"


def run_script(script_name: str, payload: dict):
    completed = subprocess.run(
        [sys.executable, str(SCRIPTS / script_name)],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        cwd=PROJECT_ROOT,
        timeout=10,
    )
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Script did not return valid JSON. stdout={completed.stdout!r}, "
            f"stderr={completed.stderr!r}"
        ) from exc
    return completed, result


class ScriptCallTest(unittest.TestCase):
    def test_echo_preserves_nested_json(self):
        payload = {
            "text": "hello",
            "number": 42,
            "enabled": True,
            "items": [1, 2, 3],
            "metadata": {"source": "test"},
        }
        completed, result = run_script("echo_params.py", payload)
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["received"], payload)
        self.assertEqual(result["data"]["top_level_types"]["enabled"], "boolean")

    def test_calculate_multiply(self):
        completed, result = run_script(
            "calculate.py",
            {"operation": "multiply", "values": [128, 36]},
        )
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["result"], 4608)

    def test_calculate_divide_by_zero_returns_json_error(self):
        completed, result = run_script(
            "calculate.py",
            {"operation": "divide", "values": [10, 0]},
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["type"], "ZeroDivisionError")

    def test_file_write_read_and_list(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = str(Path(temp_dir) / "workspace")
            content = '{"hello":"world","value":123}'

            write_proc, write_result = run_script(
                "file_operation.py",
                {
                    "action": "write",
                    "workspace": workspace,
                    "filename": "nested/result.json",
                    "content": content,
                },
            )
            self.assertEqual(write_proc.returncode, 0)
            self.assertEqual(write_result["status"], "success")

            read_proc, read_result = run_script(
                "file_operation.py",
                {
                    "action": "read",
                    "workspace": workspace,
                    "filename": "nested/result.json",
                },
            )
            self.assertEqual(read_proc.returncode, 0)
            self.assertEqual(read_result["data"]["content"], content)

            list_proc, list_result = run_script(
                "file_operation.py",
                {
                    "action": "list",
                    "workspace": workspace,
                    "directory": "nested",
                },
            )
            self.assertEqual(list_proc.returncode, 0)
            self.assertEqual(list_result["data"]["entries"][0]["name"], "result.json")

    def test_file_operation_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace = str(Path(temp_dir) / "workspace")
            completed, result = run_script(
                "file_operation.py",
                {
                    "action": "read",
                    "workspace": workspace,
                    "filename": "../outside.txt",
                },
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(result["status"], "error")
            self.assertIn("Path escapes", result["error"]["message"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
