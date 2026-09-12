"""
Gate 3 contract tests for margin_of_safety_calculation_logic.py.
Stdlib unittest only — offline, deterministic.
Run: python3 test_margin_of_safety_calculation.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from margin_of_safety_calculation_logic import (
    compute_mos,
    is_adequate,
    assess_failure_mode,
    govern_assessments,
    assess_element,
    compute_design_loads,
    full_assessment,
    FAILURE_MODES,
)


class TestComputeMos(unittest.TestCase):

    def test_positive_margin(self):
        mos = compute_mos(allowable=1000.0, applied_load=800.0)
        self.assertAlmostEqual(mos, 0.25)

    def test_zero_margin_boundary(self):
        mos = compute_mos(allowable=500.0, applied_load=500.0)
        self.assertAlmostEqual(mos, 0.0)

    def test_negative_margin(self):
        mos = compute_mos(allowable=400.0, applied_load=500.0)
        self.assertAlmostEqual(mos, -0.20)

    def test_zero_applied_load_raises(self):
        with self.assertRaises(ValueError):
            compute_mos(allowable=1000.0, applied_load=0.0)

    def test_negative_applied_load_raises(self):
        with self.assertRaises(ValueError):
            compute_mos(allowable=1000.0, applied_load=-100.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            compute_mos(allowable=0.0, applied_load=500.0)


class TestIsAdequate(unittest.TestCase):

    def test_positive_mos_is_adequate(self):
        self.assertTrue(is_adequate(0.1))

    def test_zero_mos_is_adequate(self):
        self.assertTrue(is_adequate(0.0))

    def test_negative_mos_is_not_adequate(self):
        self.assertFalse(is_adequate(-0.01))


class TestAssessFailureMode(unittest.TestCase):

    def test_yield_mode_adequate(self):
        result = assess_failure_mode("yield", applied_load=800.0, allowable=1000.0)
        self.assertEqual(result["mode"], "yield")
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["mos"], 0.25)

    def test_ultimate_mode_inadequate(self):
        result = assess_failure_mode("ultimate", applied_load=1200.0, allowable=1000.0)
        self.assertEqual(result["mode"], "ultimate")
        self.assertFalse(result["adequate"])
        self.assertLess(result["mos"], 0.0)

    def test_buckling_mode_adequate(self):
        result = assess_failure_mode("buckling", applied_load=500.0, allowable=600.0)
        self.assertEqual(result["mode"], "buckling")
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["mos"], 0.20)

    def test_fatigue_mode_recognized(self):
        result = assess_failure_mode("fatigue", applied_load=300.0, allowable=450.0)
        self.assertEqual(result["mode"], "fatigue")
        self.assertTrue(result["adequate"])
        self.assertAlmostEqual(result["mos"], 0.5)

    def test_unrecognized_mode_raises(self):
        with self.assertRaises(ValueError):
            assess_failure_mode("shear_tear", applied_load=100.0, allowable=200.0)

    def test_result_contains_required_keys(self):
        result = assess_failure_mode("yield", applied_load=100.0, allowable=150.0)
        for key in ("mode", "applied_load", "allowable", "mos", "adequate"):
            self.assertIn(key, result)


class TestGoverAssessments(unittest.TestCase):

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            govern_assessments([])

    def test_single_item_is_governing(self):
        a = assess_failure_mode("yield", 100.0, 200.0)
        self.assertEqual(govern_assessments([a])["mode"], "yield")

    def test_minimum_mos_selected(self):
        a1 = assess_failure_mode("yield", 800.0, 1000.0)     # MOS = 0.25
        a2 = assess_failure_mode("ultimate", 1100.0, 1250.0)  # MOS ≈ 0.136
        a3 = assess_failure_mode("buckling", 900.0, 950.0)    # MOS ≈ 0.056
        governing = govern_assessments([a1, a2, a3])
        self.assertEqual(governing["mode"], "buckling")


class TestAssessElement(unittest.TestCase):

    def test_all_modes_adequate(self):
        modes = [
            assess_failure_mode("yield", 800.0, 1000.0),
            assess_failure_mode("ultimate", 1000.0, 1250.0),
        ]
        result = assess_element("bracket_A", modes)
        self.assertTrue(result["all_adequate"])
        self.assertEqual(result["failed_modes"], [])

    def test_one_mode_fails(self):
        modes = [
            assess_failure_mode("yield", 800.0, 1000.0),
            assess_failure_mode("ultimate", 1400.0, 1250.0),
        ]
        result = assess_element("bracket_B", modes)
        self.assertFalse(result["all_adequate"])
        self.assertIn("ultimate", result["failed_modes"])

    def test_governing_mode_is_minimum_mos(self):
        modes = [
            assess_failure_mode("yield", 800.0, 1000.0),     # MOS = 0.25
            assess_failure_mode("ultimate", 1100.0, 1250.0),  # MOS ≈ 0.136
            assess_failure_mode("buckling", 900.0, 950.0),    # MOS ≈ 0.056
        ]
        result = assess_element("strut_C", modes)
        self.assertEqual(result["governing_mode"], "buckling")
        self.assertAlmostEqual(result["governing_mos"], 950.0 / 900.0 - 1.0)

    def test_empty_element_id_raises(self):
        modes = [assess_failure_mode("yield", 100.0, 200.0)]
        with self.assertRaises(ValueError):
            assess_element("", modes)

    def test_empty_assessments_raises(self):
        with self.assertRaises(ValueError):
            assess_element("elem_X", [])

    def test_result_has_element_id(self):
        modes = [assess_failure_mode("yield", 100.0, 200.0)]
        result = assess_element("panel_Z", modes)
        self.assertEqual(result["element_id"], "panel_Z")


class TestComputeDesignLoads(unittest.TestCase):

    def test_standard_factors(self):
        result = compute_design_loads(1000.0, yield_factor=1.0, ultimate_factor=1.25)
        self.assertAlmostEqual(result["design_yield_load"], 1000.0)
        self.assertAlmostEqual(result["design_ultimate_load"], 1250.0)

    def test_limit_load_preserved(self):
        result = compute_design_loads(2000.0, 1.1, 1.5)
        self.assertAlmostEqual(result["limit_load"], 2000.0)
        self.assertAlmostEqual(result["design_yield_load"], 2200.0)
        self.assertAlmostEqual(result["design_ultimate_load"], 3000.0)

    def test_zero_limit_load_raises(self):
        with self.assertRaises(ValueError):
            compute_design_loads(0.0, 1.0, 1.25)

    def test_negative_yield_factor_raises(self):
        with self.assertRaises(ValueError):
            compute_design_loads(1000.0, -1.0, 1.25)

    def test_zero_ultimate_factor_raises(self):
        with self.assertRaises(ValueError):
            compute_design_loads(1000.0, 1.0, 0.0)


class TestFullAssessment(unittest.TestCase):

    def test_all_adequate_without_buckling(self):
        result = full_assessment(
            element_id="panel_D",
            limit_load=1000.0,
            yield_factor=1.0,
            ultimate_factor=1.25,
            yield_allowable=1200.0,
            ultimate_allowable=1600.0,
        )
        self.assertTrue(result["all_adequate"])
        self.assertEqual(len(result["mode_assessments"]), 2)

    def test_with_buckling_all_adequate(self):
        result = full_assessment(
            element_id="strut_E",
            limit_load=800.0,
            yield_factor=1.0,
            ultimate_factor=1.25,
            yield_allowable=900.0,
            ultimate_allowable=1100.0,
            buckling_applied=700.0,
            buckling_allowable=750.0,
        )
        self.assertTrue(result["all_adequate"])
        self.assertEqual(len(result["mode_assessments"]), 3)

    def test_ultimate_exceedance_detected(self):
        # DUL = 1000 * 1.25 = 1250; allowable = 1200 → MOS < 0
        result = full_assessment(
            element_id="lug_F",
            limit_load=1000.0,
            yield_factor=1.0,
            ultimate_factor=1.25,
            yield_allowable=1100.0,
            ultimate_allowable=1200.0,
        )
        self.assertFalse(result["all_adequate"])
        self.assertIn("ultimate", result["failed_modes"])

    def test_buckling_exceedance_detected(self):
        result = full_assessment(
            element_id="column_G",
            limit_load=500.0,
            yield_factor=1.0,
            ultimate_factor=1.25,
            yield_allowable=600.0,
            ultimate_allowable=800.0,
            buckling_applied=900.0,
            buckling_allowable=850.0,
        )
        self.assertFalse(result["all_adequate"])
        self.assertIn("buckling", result["failed_modes"])


if __name__ == "__main__":
    unittest.main()
