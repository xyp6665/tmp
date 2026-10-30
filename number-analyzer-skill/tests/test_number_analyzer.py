from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from number_analyzer import analyze_numbers


class NumberAnalyzerTests(unittest.TestCase):
    def test_basic_statistics(self):
        result = analyze_numbers([1, 2, 3, 4, 5])
        data = result["data"]
        self.assertEqual(data["count"], 5)
        self.assertEqual(data["sum"], 15)
        self.assertEqual(data["mean"], 3)
        self.assertEqual(data["median"], 3)
        self.assertEqual(data["min"], 1)
        self.assertEqual(data["max"], 5)
        self.assertEqual(data["range"], 4)

    def test_outlier_and_duplicate_detection(self):
        result = analyze_numbers([12, 15, 14, 10, 18, 100, 16, 13, 15, 17])
        data = result["data"]
        self.assertEqual(data["outlier_detection"]["outliers"], [100])
        self.assertEqual(data["duplicates"], [{"value": 15, "count": 2}])

    def test_number_categories(self):
        result = analyze_numbers([-2, -1, 0, 2, 2.5])
        categories = result["data"]["number_categories"]
        self.assertEqual(categories["positive_count"], 2)
        self.assertEqual(categories["negative_count"], 2)
        self.assertEqual(categories["zero_count"], 1)
        self.assertEqual(categories["integer_count"], 4)

    def test_single_number_sample_stats_null(self):
        result = analyze_numbers([7])
        self.assertIsNone(result["data"]["dispersion"]["variance_sample"])
        self.assertEqual(result["data"]["outlier_detection"]["status"], "insufficient_data")

    def test_reject_bool_and_nan(self):
        with self.assertRaises(ValueError):
            analyze_numbers([1, True, 3])
        with self.assertRaises(ValueError):
            analyze_numbers([1, float("nan"), 3])

    def test_reject_empty_list(self):
        with self.assertRaises(ValueError):
            analyze_numbers([])


if __name__ == "__main__":
    unittest.main(verbosity=2)
