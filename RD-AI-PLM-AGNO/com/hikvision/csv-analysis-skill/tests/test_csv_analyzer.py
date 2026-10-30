from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from csv_analyzer import analyze_csv


class CsvAnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "sample.csv"
        with self.csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=["order_id", "order_date", "region", "units", "sales_amount"],
            )
            writer.writeheader()
            writer.writerows([
                {"order_id": "A1", "order_date": "2026-01-01", "region": "East", "units": "2", "sales_amount": "20"},
                {"order_id": "A2", "order_date": "2026-01-02", "region": "West", "units": "3", "sales_amount": "45"},
                {"order_id": "A3", "order_date": "2026-01-03", "region": "", "units": "1", "sales_amount": "10"},
                {"order_id": "A4", "order_date": "2026-01-04", "region": "East", "units": "", "sales_amount": "30"},
                {"order_id": "A4", "order_date": "2026-01-04", "region": "East", "units": "", "sales_amount": "30"},
            ])

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_overview_and_missing_values(self):
        result = analyze_csv(str(self.csv_path))
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["data"]["overview"]["row_count"], 5)
        self.assertEqual(result["data"]["overview"]["column_count"], 5)
        missing = {item["column"]: item["missing_count"] for item in result["data"]["missing_values"]}
        self.assertEqual(missing["region"], 1)
        self.assertEqual(missing["units"], 2)

    def test_duplicate_count_and_grouped_summary(self):
        result = analyze_csv(str(self.csv_path), group_by="region", metric="sales_amount")
        self.assertEqual(result["data"]["duplicate_rows"]["duplicate_count"], 1)
        groups = result["data"]["grouped_summary"]["groups"]
        east = next(item for item in groups if item["group"] == "East")
        self.assertEqual(east["metric_sum"], 80)

    def test_invalid_group_column(self):
        with self.assertRaises(ValueError):
            analyze_csv(str(self.csv_path), group_by="unknown")

    def test_output_file_is_written(self):
        output = Path(self.temp_dir.name) / "reports" / "result.json"
        result = analyze_csv(str(self.csv_path), output_path=str(output))
        self.assertTrue(output.exists())
        self.assertEqual(result["data"]["report_saved_to"], str(output))


if __name__ == "__main__":
    unittest.main(verbosity=2)
