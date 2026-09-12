"""
Tests for drd_mass_summary_logic.py — stdlib unittest, offline, deterministic.
Run: python3 test_drd_mass_summary.py
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from drd_mass_summary_logic import (
    MATURITY_CODE_MIN_MARGINS,
    RECOGNIZED_MATURITY_CODES,
    categorize_maturity_code,
    compute_mass_with_margin,
    process_component,
    process_mass_summary_document,
)


class TestCategorizeMaturityCode(unittest.TestCase):

    def test_valid_code_a(self):
        self.assertEqual(categorize_maturity_code("A"), "A")

    def test_valid_code_e(self):
        self.assertEqual(categorize_maturity_code("E"), "E")

    def test_valid_code_lowercase_normalizes(self):
        self.assertEqual(categorize_maturity_code("b"), "B")

    def test_all_five_codes_accepted(self):
        for code in ("A", "B", "C", "D", "E"):
            with self.subTest(code=code):
                self.assertEqual(categorize_maturity_code(code), code)

    def test_unrecognized_code_raises(self):
        with self.assertRaises(ValueError):
            categorize_maturity_code("Z")

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            categorize_maturity_code(1)

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            categorize_maturity_code("")


class TestComputeMassWithMargin(unittest.TestCase):

    def test_basic_ten_percent_margin(self):
        self.assertAlmostEqual(compute_mass_with_margin(100.0, 0.10), 110.0)

    def test_zero_margin_returns_dry_mass(self):
        self.assertAlmostEqual(compute_mass_with_margin(50.0, 0.0), 50.0)

    def test_twenty_percent_margin(self):
        self.assertAlmostEqual(compute_mass_with_margin(200.0, 0.20), 240.0)

    def test_negative_dry_mass_raises(self):
        with self.assertRaises(ValueError):
            compute_mass_with_margin(-1.0, 0.05)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            compute_mass_with_margin(10.0, -0.01)


class TestProcessComponent(unittest.TestCase):

    def test_valid_component_no_findings(self):
        comp = {"id": "PANEL-01", "maturity_code": "B", "dry_mass": 10.0}
        result = process_component(comp)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["maturity_code"], "B")
        self.assertAlmostEqual(result["dry_mass"], 10.0)
        expected = 10.0 * (1 + MATURITY_CODE_MIN_MARGINS["B"])
        self.assertAlmostEqual(result["mass_with_margin"], expected)

    def test_missing_dry_mass_gives_finding(self):
        comp = {"id": "PANEL-02", "maturity_code": "A"}
        result = process_component(comp)
        self.assertTrue(len(result["findings"]) > 0)
        self.assertIsNone(result["dry_mass"])

    def test_unrecognized_maturity_code_gives_finding(self):
        comp = {"id": "PANEL-03", "maturity_code": "X", "dry_mass": 5.0}
        result = process_component(comp)
        self.assertTrue(len(result["findings"]) > 0)

    def test_missing_id_gives_finding(self):
        comp = {"maturity_code": "C", "dry_mass": 3.0}
        result = process_component(comp)
        self.assertTrue(len(result["findings"]) > 0)

    def test_margin_below_minimum_gives_finding(self):
        # Maturity C minimum is 0.10; supplying 0.01 must produce a finding
        comp = {
            "id": "PANEL-04",
            "maturity_code": "C",
            "dry_mass": 8.0,
            "margin_fraction": 0.01,
        }
        result = process_component(comp)
        self.assertTrue(len(result["findings"]) > 0)

    def test_custom_margin_above_minimum_accepted(self):
        comp = {
            "id": "PANEL-05",
            "maturity_code": "A",
            "dry_mass": 5.0,
            "margin_fraction": 0.08,
        }
        result = process_component(comp)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["mass_with_margin"], 5.0 * 1.08)

    def test_zero_dry_mass_gives_finding(self):
        comp = {"id": "PANEL-06", "maturity_code": "A", "dry_mass": 0.0}
        result = process_component(comp)
        self.assertTrue(len(result["findings"]) > 0)

    def test_maturity_e_minimum_margin_applied(self):
        comp = {"id": "PANEL-07", "maturity_code": "E", "dry_mass": 10.0}
        result = process_component(comp)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(
            result["mass_with_margin"],
            10.0 * (1 + MATURITY_CODE_MIN_MARGINS["E"]),
        )

    def test_non_numeric_dry_mass_gives_finding(self):
        comp = {"id": "PANEL-08", "maturity_code": "A", "dry_mass": "heavy"}
        result = process_component(comp)
        self.assertTrue(len(result["findings"]) > 0)


class TestProcessMassSummaryDocument(unittest.TestCase):

    def _valid_components(self):
        return [
            {"id": "COMP-01", "maturity_code": "A", "dry_mass": 10.0},
            {"id": "COMP-02", "maturity_code": "B", "dry_mass": 20.0},
            {"id": "COMP-03", "maturity_code": "C", "dry_mass": 15.0},
        ]

    def test_nominal_compliant_document(self):
        comps = self._valid_components()
        total_margin = (
            10.0 * (1 + MATURITY_CODE_MIN_MARGINS["A"])
            + 20.0 * (1 + MATURITY_CODE_MIN_MARGINS["B"])
            + 15.0 * (1 + MATURITY_CODE_MIN_MARGINS["C"])
        )
        doc = process_mass_summary_document(comps, mass_budget=total_margin + 5.0)
        self.assertTrue(doc["compliant"])
        self.assertEqual(doc["findings"], [])
        self.assertAlmostEqual(doc["total_dry_mass"], 45.0)

    def test_budget_exceedance_flagged(self):
        comps = self._valid_components()
        doc = process_mass_summary_document(comps, mass_budget=1.0)
        self.assertFalse(doc["compliant"])
        self.assertTrue(any("exceeds" in f for f in doc["findings"]))
        self.assertGreater(doc["budget_exceedance"], 0)

    def test_no_budget_gives_finding(self):
        comps = self._valid_components()
        doc = process_mass_summary_document(comps, mass_budget=None)
        self.assertFalse(doc["compliant"])
        self.assertTrue(any("budget" in f.lower() for f in doc["findings"]))

    def test_duplicate_ids_flagged(self):
        comps = [
            {"id": "COMP-01", "maturity_code": "A", "dry_mass": 5.0},
            {"id": "COMP-01", "maturity_code": "B", "dry_mass": 3.0},
        ]
        doc = process_mass_summary_document(comps, mass_budget=100.0)
        self.assertFalse(doc["compliant"])
        self.assertTrue(any("Duplicate" in f for f in doc["findings"]))

    def test_empty_document_flagged(self):
        doc = process_mass_summary_document([], mass_budget=100.0)
        self.assertFalse(doc["compliant"])
        self.assertEqual(doc["total_dry_mass"], 0.0)

    def test_total_dry_mass_sums_correctly(self):
        comps = [
            {"id": "X1", "maturity_code": "A", "dry_mass": 7.5},
            {"id": "X2", "maturity_code": "A", "dry_mass": 2.5},
        ]
        doc = process_mass_summary_document(comps, mass_budget=1000.0)
        self.assertAlmostEqual(doc["total_dry_mass"], 10.0)

    def test_total_mass_with_margin_sums_correctly(self):
        comps = [
            {"id": "Y1", "maturity_code": "D", "dry_mass": 10.0},
            {"id": "Y2", "maturity_code": "D", "dry_mass": 10.0},
        ]
        expected = 2 * 10.0 * (1 + MATURITY_CODE_MIN_MARGINS["D"])
        doc = process_mass_summary_document(comps, mass_budget=1000.0)
        self.assertAlmostEqual(doc["total_mass_with_margin"], expected)

    def test_exactly_at_budget_is_compliant(self):
        comps = [{"id": "Z1", "maturity_code": "A", "dry_mass": 10.0}]
        exact = 10.0 * (1 + MATURITY_CODE_MIN_MARGINS["A"])
        doc = process_mass_summary_document(comps, mass_budget=exact)
        self.assertTrue(doc["compliant"])

    def test_zero_budget_gives_finding(self):
        comps = self._valid_components()
        doc = process_mass_summary_document(comps, mass_budget=0.0)
        self.assertFalse(doc["compliant"])


if __name__ == "__main__":
    unittest.main()
