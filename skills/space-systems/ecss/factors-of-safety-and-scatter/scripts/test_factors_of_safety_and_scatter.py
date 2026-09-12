"""
Gate 3 contract tests for factors_of_safety_and_scatter_logic.
Run: python3 test_factors_of_safety_and_scatter.py
stdlib unittest only — offline, deterministic.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from factors_of_safety_and_scatter_logic import (
    MATERIAL_CATEGORIES,
    SCATTER_FACTOR_INSPECTABLE,
    SCATTER_FACTOR_UNINSPECTABLE,
    apply_fos,
    apply_scatter_factor,
    check_fatigue_compliance,
    compute_margin_of_safety,
)


class TestApplyFosUltimateLoads(unittest.TestCase):

    def test_metallic_ductile_ultimate_load(self):
        r = apply_fos(100.0, "metallic_ductile")
        self.assertFalse(r.errors)
        self.assertAlmostEqual(r.design_ultimate_load, 125.0)

    def test_metallic_ductile_yield_load(self):
        r = apply_fos(100.0, "metallic_ductile")
        self.assertAlmostEqual(r.design_yield_load, 100.0)

    def test_metallic_brittle_ultimate_load(self):
        r = apply_fos(100.0, "metallic_brittle")
        self.assertFalse(r.errors)
        self.assertAlmostEqual(r.design_ultimate_load, 150.0)

    def test_metallic_brittle_yield_load(self):
        r = apply_fos(100.0, "metallic_brittle")
        self.assertAlmostEqual(r.design_yield_load, 110.0)

    def test_composite_ultimate_load(self):
        r = apply_fos(200.0, "composite")
        self.assertFalse(r.errors)
        self.assertAlmostEqual(r.design_ultimate_load, 280.0)

    def test_composite_yield_load(self):
        r = apply_fos(200.0, "composite")
        self.assertAlmostEqual(r.design_yield_load, 220.0)

    def test_bonded_ultimate_load(self):
        r = apply_fos(100.0, "bonded")
        self.assertFalse(r.errors)
        self.assertAlmostEqual(r.design_ultimate_load, 150.0)

    def test_fos_values_stored_on_result(self):
        r = apply_fos(100.0, "composite")
        self.assertAlmostEqual(r.fos_ultimate, 1.40)
        self.assertAlmostEqual(r.fos_yield, 1.10)

    def test_all_material_categories_produce_no_errors(self):
        for cat in MATERIAL_CATEGORIES:
            r = apply_fos(500.0, cat)
            self.assertFalse(r.errors, f"Category '{cat}' raised errors: {r.errors}")

    def test_unknown_category_returns_error(self):
        r = apply_fos(100.0, "unobtainium")
        self.assertTrue(r.errors)
        self.assertIn("unobtainium", r.errors[0])

    def test_negative_dll_returns_error(self):
        r = apply_fos(-50.0, "metallic_ductile")
        self.assertTrue(r.errors)

    def test_zero_dll_returns_error(self):
        r = apply_fos(0.0, "composite")
        self.assertTrue(r.errors)


class TestApplyScatterFactor(unittest.TestCase):

    def test_inspectable_scatter_factor_value(self):
        r = apply_scatter_factor(1000.0, inspectable=True)
        self.assertFalse(r.errors)
        self.assertAlmostEqual(r.scatter_factor, SCATTER_FACTOR_INSPECTABLE)

    def test_uninspectable_scatter_factor_value(self):
        r = apply_scatter_factor(1000.0, inspectable=False)
        self.assertFalse(r.errors)
        self.assertAlmostEqual(r.scatter_factor, SCATTER_FACTOR_UNINSPECTABLE)

    def test_inspectable_allowable_life(self):
        r = apply_scatter_factor(1000.0, inspectable=True)
        self.assertAlmostEqual(r.allowable_life, 500.0)

    def test_uninspectable_allowable_life(self):
        r = apply_scatter_factor(1000.0, inspectable=False)
        self.assertAlmostEqual(r.allowable_life, 250.0)

    def test_uninspectable_allowable_is_half_inspectable(self):
        r_insp = apply_scatter_factor(800.0, inspectable=True)
        r_uninsp = apply_scatter_factor(800.0, inspectable=False)
        self.assertAlmostEqual(r_uninsp.allowable_life * 2.0, r_insp.allowable_life)

    def test_negative_analysis_life_returns_error(self):
        r = apply_scatter_factor(-100.0, inspectable=True)
        self.assertTrue(r.errors)

    def test_zero_analysis_life_returns_error(self):
        r = apply_scatter_factor(0.0, inspectable=False)
        self.assertTrue(r.errors)


class TestComputeMarginOfSafety(unittest.TestCase):

    def test_positive_margin_passes(self):
        r = compute_margin_of_safety(allowable=150.0, applied=100.0)
        self.assertFalse(r.errors)
        self.assertAlmostEqual(r.margin_of_safety, 0.50)
        self.assertTrue(r.passes)

    def test_zero_margin_is_a_pass(self):
        r = compute_margin_of_safety(allowable=100.0, applied=100.0)
        self.assertAlmostEqual(r.margin_of_safety, 0.0)
        self.assertTrue(r.passes)

    def test_negative_margin_is_a_finding(self):
        r = compute_margin_of_safety(allowable=80.0, applied=100.0)
        self.assertFalse(r.errors)
        self.assertLess(r.margin_of_safety, 0.0)
        self.assertFalse(r.passes)

    def test_zero_applied_returns_error(self):
        r = compute_margin_of_safety(allowable=100.0, applied=0.0)
        self.assertTrue(r.errors)

    def test_negative_allowable_returns_error(self):
        r = compute_margin_of_safety(allowable=-50.0, applied=100.0)
        self.assertTrue(r.errors)

    def test_negative_applied_returns_error(self):
        r = compute_margin_of_safety(allowable=100.0, applied=-10.0)
        self.assertTrue(r.errors)

    def test_ms_formula_correctness(self):
        r = compute_margin_of_safety(allowable=187.5, applied=150.0)
        self.assertAlmostEqual(r.margin_of_safety, 0.25)


class TestCheckFatigueCompliance(unittest.TestCase):

    def test_passes_when_allowable_exceeds_mission_life(self):
        r = check_fatigue_compliance(
            analysis_life=1000.0, mission_life=400.0, inspectable=True
        )
        self.assertFalse(r["errors"])
        self.assertTrue(r["passes"])
        self.assertAlmostEqual(r["deficit"], 0.0)

    def test_fails_when_allowable_below_mission_life(self):
        r = check_fatigue_compliance(
            analysis_life=1000.0, mission_life=600.0, inspectable=True
        )
        self.assertFalse(r["errors"])
        self.assertFalse(r["passes"])
        self.assertGreater(r["deficit"], 0.0)

    def test_uninspectable_location_uses_scatter_4(self):
        r = check_fatigue_compliance(
            analysis_life=1000.0, mission_life=200.0, inspectable=False
        )
        self.assertAlmostEqual(r["allowable_life"], 250.0)
        self.assertTrue(r["passes"])

    def test_zero_mission_life_returns_error(self):
        r = check_fatigue_compliance(
            analysis_life=1000.0, mission_life=0.0, inspectable=True
        )
        self.assertTrue(r["errors"])

    def test_zero_analysis_life_returns_error(self):
        r = check_fatigue_compliance(
            analysis_life=0.0, mission_life=200.0, inspectable=False
        )
        self.assertTrue(r["errors"])


if __name__ == "__main__":
    unittest.main()
