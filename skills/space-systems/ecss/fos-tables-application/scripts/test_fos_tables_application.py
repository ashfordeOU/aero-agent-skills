"""
Offline deterministic tests for fos_tables_application_logic.
Run: python3 test_fos_tables_application.py
Expected output: OK
"""

import sys
import os
import unittest

# Resolve the module relative to this file's directory.
sys.path.insert(0, os.path.dirname(__file__))

from fos_tables_application_logic import (
    lookup_fos,
    apply_fos,
    compute_margin,
    infer_mission_category,
    summarise_load_cases,
    MISSION_CATEGORIES,
    FACTOR_TYPES,
)


class TestLookupFos(unittest.TestCase):
    """Verify tabulated FOS values for each combination."""

    def test_unmanned_yield(self):
        self.assertAlmostEqual(lookup_fos("unmanned", "yield"), 1.10)

    def test_unmanned_ultimate(self):
        self.assertAlmostEqual(lookup_fos("unmanned", "ultimate"), 1.25)

    def test_unmanned_proof(self):
        self.assertAlmostEqual(lookup_fos("unmanned", "proof"), 1.10)

    def test_human_spaceflight_yield(self):
        self.assertAlmostEqual(lookup_fos("human_spaceflight", "yield"), 1.25)

    def test_human_spaceflight_ultimate(self):
        self.assertAlmostEqual(lookup_fos("human_spaceflight", "ultimate"), 1.40)

    def test_human_spaceflight_proof(self):
        self.assertAlmostEqual(lookup_fos("human_spaceflight", "proof"), 1.50)

    def test_case_insensitive_mission(self):
        self.assertAlmostEqual(lookup_fos("UNMANNED", "yield"), 1.10)

    def test_case_insensitive_factor(self):
        self.assertAlmostEqual(lookup_fos("unmanned", "YIELD"), 1.10)

    def test_human_is_more_conservative_than_unmanned_yield(self):
        self.assertGreater(
            lookup_fos("human_spaceflight", "yield"),
            lookup_fos("unmanned", "yield"),
        )

    def test_human_is_more_conservative_than_unmanned_ultimate(self):
        self.assertGreater(
            lookup_fos("human_spaceflight", "ultimate"),
            lookup_fos("unmanned", "ultimate"),
        )

    def test_invalid_mission_category_raises(self):
        with self.assertRaises(ValueError):
            lookup_fos("interplanetary", "yield")

    def test_invalid_factor_type_raises(self):
        with self.assertRaises(ValueError):
            lookup_fos("unmanned", "buckling")

    def test_both_invalid_raises(self):
        with self.assertRaises(ValueError):
            lookup_fos("unknown_mission", "unknown_factor")


class TestApplyFos(unittest.TestCase):
    """Verify design-load computation via apply_fos."""

    def test_design_load_unmanned_yield(self):
        result = apply_fos("unmanned", "yield", 1000.0)
        self.assertAlmostEqual(result["design_load"], 1100.0)
        self.assertAlmostEqual(result["fos"], 1.10)
        self.assertEqual(result["mission_category"], "unmanned")
        self.assertEqual(result["factor_type"], "yield")

    def test_design_load_human_ultimate(self):
        result = apply_fos("human_spaceflight", "ultimate", 500.0)
        self.assertAlmostEqual(result["design_load"], 700.0)
        self.assertAlmostEqual(result["fos"], 1.40)

    def test_design_load_unmanned_proof(self):
        result = apply_fos("unmanned", "proof", 200.0)
        self.assertAlmostEqual(result["design_load"], 220.0)

    def test_zero_limit_load_raises(self):
        with self.assertRaises(ValueError):
            apply_fos("unmanned", "yield", 0.0)

    def test_negative_limit_load_raises(self):
        with self.assertRaises(ValueError):
            apply_fos("unmanned", "yield", -50.0)

    def test_result_keys_present(self):
        result = apply_fos("unmanned", "ultimate", 100.0)
        for key in ("mission_category", "factor_type", "fos", "limit_load", "design_load"):
            self.assertIn(key, result)


class TestComputeMargin(unittest.TestCase):
    """Verify margin-of-safety computation."""

    def test_positive_margin_passes(self):
        # allowable = 1500, design_load = 1000 * 1.25 = 1250 → MS = 0.20
        result = compute_margin("unmanned", "ultimate", 1000.0, 1500.0)
        self.assertAlmostEqual(result["margin_of_safety"], 0.20, places=6)
        self.assertTrue(result["pass"])

    def test_zero_margin_passes(self):
        # allowable exactly equals design_load → MS = 0.0
        result = compute_margin("unmanned", "yield", 1000.0, 1100.0)
        self.assertAlmostEqual(result["margin_of_safety"], 0.0, places=6)
        self.assertTrue(result["pass"])

    def test_negative_margin_fails(self):
        # allowable = 1200, design_load = 1000 * 1.40 = 1400 → MS = -0.1429
        result = compute_margin("human_spaceflight", "ultimate", 1000.0, 1200.0)
        self.assertLess(result["margin_of_safety"], 0.0)
        self.assertFalse(result["pass"])

    def test_human_proof_margin(self):
        # allowable = 750, design_load = 400 * 1.50 = 600 → MS = 0.25
        result = compute_margin("human_spaceflight", "proof", 400.0, 750.0)
        self.assertAlmostEqual(result["margin_of_safety"], 0.25, places=6)
        self.assertTrue(result["pass"])

    def test_zero_limit_load_raises(self):
        with self.assertRaises(ValueError):
            compute_margin("unmanned", "yield", 0.0, 500.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            compute_margin("unmanned", "yield", 100.0, 0.0)

    def test_result_includes_design_load(self):
        result = compute_margin("unmanned", "ultimate", 800.0, 1200.0)
        self.assertAlmostEqual(result["design_load"], 1000.0, places=6)

    def test_result_keys_present(self):
        result = compute_margin("unmanned", "yield", 100.0, 150.0)
        for key in ("mission_category", "factor_type", "fos",
                    "limit_load", "design_load", "allowable",
                    "margin_of_safety", "pass"):
            self.assertIn(key, result)


class TestInferMissionCategory(unittest.TestCase):
    """Verify free-text mission-category inference."""

    def test_satellite_is_unmanned(self):
        self.assertEqual(infer_mission_category("LEO satellite"), "unmanned")

    def test_crewed_capsule_is_human_spaceflight(self):
        self.assertEqual(infer_mission_category("crewed capsule"), "human_spaceflight")

    def test_crew_keyword(self):
        self.assertEqual(infer_mission_category("Crew Dragon mission"), "human_spaceflight")

    def test_astronaut_keyword(self):
        self.assertEqual(infer_mission_category("astronaut EVA module"), "human_spaceflight")

    def test_human_rated_keyword(self):
        self.assertEqual(infer_mission_category("human-rated launch vehicle"), "human_spaceflight")

    def test_empty_string_is_unmanned(self):
        self.assertEqual(infer_mission_category(""), "unmanned")

    def test_case_insensitive_crew(self):
        self.assertEqual(infer_mission_category("CREW module"), "human_spaceflight")


class TestSummariseLoadCases(unittest.TestCase):
    """Verify batch load-case evaluation."""

    def test_all_passing_cases(self):
        cases = [
            {"mission_category": "unmanned", "factor_type": "yield",
             "limit_load": 1000.0, "allowable": 1500.0},
            {"mission_category": "unmanned", "factor_type": "ultimate",
             "limit_load": 1000.0, "allowable": 1600.0},
        ]
        summary = summarise_load_cases(cases)
        self.assertTrue(summary["all_pass"])
        self.assertEqual(summary["failing_cases"], [])
        self.assertGreaterEqual(summary["governing_margin"], 0.0)

    def test_one_failing_case_detected(self):
        cases = [
            {"mission_category": "unmanned", "factor_type": "yield",
             "limit_load": 1000.0, "allowable": 1500.0},
            {"mission_category": "human_spaceflight", "factor_type": "ultimate",
             "limit_load": 1000.0, "allowable": 1200.0},  # design = 1400 → MS < 0
        ]
        summary = summarise_load_cases(cases)
        self.assertFalse(summary["all_pass"])
        self.assertIn(1, summary["failing_cases"])

    def test_governing_margin_is_minimum(self):
        cases = [
            {"mission_category": "unmanned", "factor_type": "yield",
             "limit_load": 1000.0, "allowable": 1210.0},   # MS ≈ 0.10
            {"mission_category": "unmanned", "factor_type": "ultimate",
             "limit_load": 1000.0, "allowable": 2000.0},   # MS = 0.60
        ]
        summary = summarise_load_cases(cases)
        self.assertAlmostEqual(summary["governing_margin"],
                               min(r["margin_of_safety"] for r in summary["results"]),
                               places=6)

    def test_empty_cases_raises(self):
        with self.assertRaises(ValueError):
            summarise_load_cases([])

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            summarise_load_cases([{"mission_category": "unmanned", "factor_type": "yield",
                                   "limit_load": 100.0}])  # missing "allowable"

    def test_result_count_matches_input(self):
        cases = [
            {"mission_category": "unmanned", "factor_type": "yield",
             "limit_load": float(i + 1) * 100, "allowable": float(i + 1) * 200}
            for i in range(4)
        ]
        summary = summarise_load_cases(cases)
        self.assertEqual(len(summary["results"]), 4)


class TestConstantIntegrity(unittest.TestCase):
    """Sanity checks on the module constants."""

    def test_mission_categories_contains_both(self):
        self.assertIn("unmanned", MISSION_CATEGORIES)
        self.assertIn("human_spaceflight", MISSION_CATEGORIES)

    def test_factor_types_contains_all_three(self):
        for ft in ("yield", "ultimate", "proof"):
            self.assertIn(ft, FACTOR_TYPES)

    def test_all_fos_table_entries_exceed_one(self):
        from fos_tables_application_logic import _FOS_TABLE
        for key, value in _FOS_TABLE.items():
            self.assertGreater(value, 1.0, msg=f"FOS for {key} should exceed 1.0")


if __name__ == "__main__":
    unittest.main()
