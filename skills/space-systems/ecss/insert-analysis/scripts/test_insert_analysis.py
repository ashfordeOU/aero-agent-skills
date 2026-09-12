"""
test_insert_analysis.py

Offline deterministic unit tests for insert_analysis_logic.py.
Reference: ECSS-E-ST-32C clause 4.6.2.16.

Run:  python3 test_insert_analysis.py
Expected output: OK
"""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import insert_analysis_logic as ia


# ---------------------------------------------------------------------------
# Honeycomb potted-insert strength functions
# ---------------------------------------------------------------------------

class TestPottedInsertPulloutStrength(unittest.TestCase):

    def test_basic_formula(self):
        # F = pi * 20 * 15 * 1.5 = 450*pi
        result = ia.potted_insert_pullout_strength(20.0, 15.0, 1.5)
        self.assertAlmostEqual(result, math.pi * 20.0 * 15.0 * 1.5, places=9)

    def test_scales_linearly_with_diameter(self):
        f1 = ia.potted_insert_pullout_strength(10.0, 20.0, 2.0)
        f2 = ia.potted_insert_pullout_strength(20.0, 20.0, 2.0)
        self.assertAlmostEqual(f2 / f1, 2.0, places=12)

    def test_scales_linearly_with_core_thickness(self):
        f1 = ia.potted_insert_pullout_strength(20.0, 10.0, 2.0)
        f2 = ia.potted_insert_pullout_strength(20.0, 30.0, 2.0)
        self.assertAlmostEqual(f2 / f1, 3.0, places=12)

    def test_raises_on_zero_diameter(self):
        with self.assertRaises(ia.InsertAnalysisError):
            ia.potted_insert_pullout_strength(0.0, 15.0, 1.5)

    def test_raises_on_negative_shear_strength(self):
        with self.assertRaises(ia.InsertAnalysisError):
            ia.potted_insert_pullout_strength(20.0, 15.0, -1.0)

    def test_raises_on_zero_core_thickness(self):
        with self.assertRaises(ia.InsertAnalysisError):
            ia.potted_insert_pullout_strength(20.0, 0.0, 1.5)


class TestPottedInsertShearStrength(unittest.TestCase):

    def test_basic_formula(self):
        # F = pi * (10)^2 * 5.0 = 500*pi
        result = ia.potted_insert_shear_strength(20.0, 5.0)
        self.assertAlmostEqual(result, math.pi * 100.0 * 5.0, places=9)

    def test_scales_with_diameter_squared(self):
        f1 = ia.potted_insert_shear_strength(10.0, 3.0)
        f2 = ia.potted_insert_shear_strength(20.0, 3.0)
        self.assertAlmostEqual(f2 / f1, 4.0, places=12)

    def test_raises_on_non_positive_strength(self):
        with self.assertRaises(ia.InsertAnalysisError):
            ia.potted_insert_shear_strength(20.0, 0.0)


# ---------------------------------------------------------------------------
# Metal threaded-insert strength functions
# ---------------------------------------------------------------------------

class TestMetalInsertStrengths(unittest.TestCase):

    def test_pullout_basic(self):
        # F = pi * 6 * 12 * 100 = 7200*pi
        result = ia.metal_insert_pullout_strength(6.0, 12.0, 100.0)
        self.assertAlmostEqual(result, math.pi * 6.0 * 12.0 * 100.0, places=6)

    def test_shear_basic(self):
        # F = pi * (3)^2 * 100 = 900*pi
        result = ia.metal_insert_shear_strength(6.0, 100.0)
        self.assertAlmostEqual(result, math.pi * 9.0 * 100.0, places=6)

    def test_pullout_raises_on_zero_engagement(self):
        with self.assertRaises(ia.InsertAnalysisError):
            ia.metal_insert_pullout_strength(6.0, 0.0, 100.0)

    def test_shear_raises_on_negative_diameter(self):
        with self.assertRaises(ia.InsertAnalysisError):
            ia.metal_insert_shear_strength(-6.0, 100.0)


# ---------------------------------------------------------------------------
# Composite insert strength functions
# ---------------------------------------------------------------------------

class TestCompositeInsertStrengths(unittest.TestCase):

    def test_bearing_strength_basic(self):
        # F = 6 * 4 * 400 = 9600 N
        result = ia.composite_insert_bearing_strength(6.0, 4.0, 400.0)
        self.assertAlmostEqual(result, 9600.0, places=9)

    def test_pullthrough_basic(self):
        # F = pi * 6 * 4 * 30 = 720*pi
        result = ia.composite_insert_pullthrough_strength(6.0, 4.0, 30.0)
        self.assertAlmostEqual(result, math.pi * 6.0 * 4.0 * 30.0, places=6)

    def test_bearing_raises_on_zero_thickness(self):
        with self.assertRaises(ia.InsertAnalysisError):
            ia.composite_insert_bearing_strength(6.0, 0.0, 400.0)

    def test_pullthrough_raises_on_zero_ils(self):
        with self.assertRaises(ia.InsertAnalysisError):
            ia.composite_insert_pullthrough_strength(6.0, 4.0, 0.0)


# ---------------------------------------------------------------------------
# Combined-load interaction ratio
# ---------------------------------------------------------------------------

class TestCombinedLoadRatio(unittest.TestCase):

    def test_pure_axial(self):
        # R = (500/1000)^2 + 0 = 0.25
        r = ia.combined_load_ratio(500.0, 0.0, 1000.0, 1000.0)
        self.assertAlmostEqual(r, 0.25, places=12)

    def test_pure_shear(self):
        # R = 0 + (500/1000)^2 = 0.25
        r = ia.combined_load_ratio(0.0, 500.0, 1000.0, 1000.0)
        self.assertAlmostEqual(r, 0.25, places=12)

    def test_at_interaction_limit(self):
        # 3-4-5 triangle: (0.6)^2 + (0.8)^2 = 1.0
        r = ia.combined_load_ratio(600.0, 800.0, 1000.0, 1000.0)
        self.assertAlmostEqual(r, 1.0, places=12)

    def test_well_below_limit(self):
        r = ia.combined_load_ratio(100.0, 100.0, 1000.0, 1000.0)
        self.assertAlmostEqual(r, 0.02, places=12)

    def test_raises_on_negative_axial(self):
        with self.assertRaises(ia.InsertAnalysisError):
            ia.combined_load_ratio(-1.0, 0.0, 1000.0, 1000.0)

    def test_raises_on_zero_pullout_strength(self):
        with self.assertRaises(ia.InsertAnalysisError):
            ia.combined_load_ratio(100.0, 100.0, 0.0, 1000.0)

    def test_raises_on_zero_shear_strength(self):
        with self.assertRaises(ia.InsertAnalysisError):
            ia.combined_load_ratio(100.0, 100.0, 1000.0, 0.0)


# ---------------------------------------------------------------------------
# Margin of safety
# ---------------------------------------------------------------------------

class TestMarginOfSafety(unittest.TestCase):

    def test_at_limit_gives_zero_ms(self):
        # R=1.0 -> MS = 1/1 - 1 = 0.0
        ms = ia.margin_of_safety_from_ratio(1.0)
        self.assertAlmostEqual(ms, 0.0, places=12)

    def test_below_limit_gives_positive_ms(self):
        # R=0.25 -> MS = 1/0.5 - 1 = 1.0
        ms = ia.margin_of_safety_from_ratio(0.25)
        self.assertAlmostEqual(ms, 1.0, places=12)

    def test_above_limit_gives_negative_ms(self):
        # R=4.0 -> MS = 1/2 - 1 = -0.5
        ms = ia.margin_of_safety_from_ratio(4.0)
        self.assertAlmostEqual(ms, -0.5, places=12)

    def test_raises_on_zero_ratio(self):
        with self.assertRaises(ia.InsertAnalysisError):
            ia.margin_of_safety_from_ratio(0.0)

    def test_raises_on_negative_ratio(self):
        with self.assertRaises(ia.InsertAnalysisError):
            ia.margin_of_safety_from_ratio(-0.1)


# ---------------------------------------------------------------------------
# assess_potted_insert
# ---------------------------------------------------------------------------

class TestAssessPottedInsert(unittest.TestCase):

    def _safe_params(self):
        return dict(
            axial_load_n=200.0,
            shear_load_n=100.0,
            potting_diameter_mm=30.0,
            core_thickness_mm=20.0,
            core_shear_strength_mpa=2.0,
            potting_shear_strength_mpa=8.0,
            factor_of_safety=1.5,
        )

    def test_safe_case_is_acceptable(self):
        result = ia.assess_potted_insert(**self._safe_params())
        self.assertTrue(result["is_acceptable"])
        self.assertEqual(result["failure_mode"], "acceptable")
        self.assertGreater(result["margin_of_safety"], 0.0)

    def test_safe_case_substrate_label(self):
        result = ia.assess_potted_insert(**self._safe_params())
        self.assertEqual(result["substrate"], ia.SUBSTRATE_HONEYCOMB)

    def test_result_contains_required_keys(self):
        result = ia.assess_potted_insert(**self._safe_params())
        required = {
            "pullout_strength_n", "shear_strength_n", "interaction_ratio",
            "margin_of_safety", "is_acceptable", "failure_mode", "substrate",
        }
        self.assertTrue(required.issubset(result.keys()))

    def test_failing_pullout_dominant(self):
        result = ia.assess_potted_insert(
            axial_load_n=5000.0,
            shear_load_n=10.0,
            potting_diameter_mm=20.0,
            core_thickness_mm=15.0,
            core_shear_strength_mpa=1.5,
            potting_shear_strength_mpa=5.0,
            factor_of_safety=1.5,
        )
        self.assertFalse(result["is_acceptable"])
        self.assertLess(result["margin_of_safety"], 0.0)
        self.assertEqual(result["failure_mode"], "pullout")

    def test_zero_load_gives_infinite_ms(self):
        result = ia.assess_potted_insert(
            axial_load_n=0.0,
            shear_load_n=0.0,
            potting_diameter_mm=20.0,
            core_thickness_mm=15.0,
            core_shear_strength_mpa=1.5,
            potting_shear_strength_mpa=5.0,
        )
        self.assertEqual(result["margin_of_safety"], float("inf"))
        self.assertTrue(result["is_acceptable"])

    def test_factor_of_safety_increases_interaction_ratio(self):
        # Higher FoS on same loads must give a higher R
        base = ia.assess_potted_insert(**{**self._safe_params(), "factor_of_safety": 1.0})
        high = ia.assess_potted_insert(**{**self._safe_params(), "factor_of_safety": 3.0})
        self.assertGreater(high["interaction_ratio"], base["interaction_ratio"])

    def test_raises_on_negative_load(self):
        params = self._safe_params()
        params["axial_load_n"] = -100.0
        with self.assertRaises(ia.InsertAnalysisError):
            ia.assess_potted_insert(**params)


# ---------------------------------------------------------------------------
# assess_metal_insert
# ---------------------------------------------------------------------------

class TestAssessMetalInsert(unittest.TestCase):

    def test_acceptable_case(self):
        result = ia.assess_metal_insert(
            axial_load_n=500.0,
            shear_load_n=200.0,
            nominal_diameter_mm=6.0,
            engagement_length_mm=15.0,
            material_shear_strength_mpa=140.0,
        )
        self.assertTrue(result["is_acceptable"])
        self.assertGreater(result["margin_of_safety"], 0.0)
        self.assertEqual(result["substrate"], ia.SUBSTRATE_METAL)

    def test_failing_case(self):
        result = ia.assess_metal_insert(
            axial_load_n=50000.0,
            shear_load_n=50000.0,
            nominal_diameter_mm=3.0,
            engagement_length_mm=5.0,
            material_shear_strength_mpa=50.0,
        )
        self.assertFalse(result["is_acceptable"])
        self.assertLess(result["margin_of_safety"], 0.0)

    def test_zero_load_infinite_ms(self):
        result = ia.assess_metal_insert(
            axial_load_n=0.0,
            shear_load_n=0.0,
            nominal_diameter_mm=6.0,
            engagement_length_mm=12.0,
            material_shear_strength_mpa=120.0,
        )
        self.assertEqual(result["margin_of_safety"], float("inf"))


# ---------------------------------------------------------------------------
# assess_composite_insert
# ---------------------------------------------------------------------------

class TestAssessCompositeInsert(unittest.TestCase):

    def test_acceptable_case(self):
        result = ia.assess_composite_insert(
            axial_load_n=100.0,
            shear_load_n=200.0,
            bolt_diameter_mm=5.0,
            laminate_thickness_mm=3.0,
            interlaminar_shear_mpa=50.0,
            bearing_strength_mpa=350.0,
        )
        self.assertTrue(result["is_acceptable"])
        self.assertEqual(result["substrate"], ia.SUBSTRATE_COMPOSITE)

    def test_bearing_dominant_failure(self):
        result = ia.assess_composite_insert(
            axial_load_n=10.0,
            shear_load_n=10000.0,
            bolt_diameter_mm=3.0,
            laminate_thickness_mm=2.0,
            interlaminar_shear_mpa=40.0,
            bearing_strength_mpa=300.0,
        )
        self.assertFalse(result["is_acceptable"])
        self.assertEqual(result["failure_mode"], "shear")

    def test_result_substrate_label(self):
        result = ia.assess_composite_insert(
            axial_load_n=50.0,
            shear_load_n=50.0,
            bolt_diameter_mm=4.0,
            laminate_thickness_mm=2.0,
            interlaminar_shear_mpa=60.0,
            bearing_strength_mpa=400.0,
        )
        self.assertEqual(result["substrate"], ia.SUBSTRATE_COMPOSITE)


if __name__ == "__main__":
    unittest.main()
