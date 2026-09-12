"""
Gate 3 contract tests — composite_material_characterization_logic.py
Offline, deterministic, stdlib unittest only.
Run: python3 test_composite_material_characterization.py
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from composite_material_characterization_logic import (
    validate_coupon_test_type,
    check_specimen_count,
    compute_basis_value,
    apply_knockdown_factor,
    compute_margin_of_safety,
    categorize_material,
    check_allowables_completeness,
    compute_translation_efficiency,
)


def _deterministic_specimens(n, mean=1000.0, spread=50.0):
    """Generate a deterministic sequence of n strength values around mean."""
    return [mean + spread * ((-1) ** i) * (0.5 + 0.04 * i) for i in range(n)]


# ---------------------------------------------------------------------------
# validate_coupon_test_type
# ---------------------------------------------------------------------------

class TestValidateCouponTestType(unittest.TestCase):

    def test_fiber_tensile_longitudinal_valid(self):
        r = validate_coupon_test_type("fiber_tensile_longitudinal")
        self.assertTrue(r["valid"])

    def test_interlaminar_shear_strength_valid(self):
        r = validate_coupon_test_type("interlaminar_shear_strength")
        self.assertTrue(r["valid"])

    def test_in_plane_shear_valid(self):
        r = validate_coupon_test_type("in_plane_shear")
        self.assertTrue(r["valid"])

    def test_unknown_type_not_valid(self):
        r = validate_coupon_test_type("magic_coupon_test")
        self.assertFalse(r["valid"])

    def test_normalization_dashes_to_underscores(self):
        r = validate_coupon_test_type("in-plane-shear")
        self.assertTrue(r["valid"])
        self.assertEqual(r["test_type"], "in_plane_shear")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            validate_coupon_test_type("")

    def test_whitespace_only_raises(self):
        with self.assertRaises(ValueError):
            validate_coupon_test_type("   ")


# ---------------------------------------------------------------------------
# check_specimen_count
# ---------------------------------------------------------------------------

class TestCheckSpecimenCount(unittest.TestCase):

    def test_b_basis_exactly_at_minimum(self):
        r = check_specimen_count("B", 18)
        self.assertTrue(r["sufficient"])
        self.assertEqual(r["shortfall"], 0)

    def test_b_basis_above_minimum(self):
        r = check_specimen_count("B", 25)
        self.assertTrue(r["sufficient"])

    def test_b_basis_below_minimum(self):
        r = check_specimen_count("B", 10)
        self.assertFalse(r["sufficient"])
        self.assertEqual(r["shortfall"], 8)

    def test_a_basis_at_minimum(self):
        r = check_specimen_count("A", 25)
        self.assertTrue(r["sufficient"])
        self.assertEqual(r["shortfall"], 0)

    def test_a_basis_below_minimum(self):
        r = check_specimen_count("A", 20)
        self.assertFalse(r["sufficient"])
        self.assertEqual(r["shortfall"], 5)

    def test_invalid_basis_raises(self):
        with self.assertRaises(ValueError):
            check_specimen_count("Z", 30)

    def test_negative_count_raises(self):
        with self.assertRaises(ValueError):
            check_specimen_count("B", -1)

    def test_minimum_required_field_present(self):
        r = check_specimen_count("B", 20)
        self.assertIn("minimum_required", r)
        self.assertEqual(r["minimum_required"], 18)


# ---------------------------------------------------------------------------
# compute_basis_value
# ---------------------------------------------------------------------------

class TestComputeBasisValue(unittest.TestCase):

    def test_b_basis_value_below_mean(self):
        specs = _deterministic_specimens(25)
        r = compute_basis_value(specs, "B")
        self.assertLess(r["basis_value"], r["mean"])

    def test_a_basis_lower_than_b_basis(self):
        specs = _deterministic_specimens(30)
        a = compute_basis_value(specs, "A")
        b = compute_basis_value(specs, "B")
        self.assertLess(a["basis_value"], b["basis_value"])

    def test_k_factor_present_and_positive(self):
        specs = _deterministic_specimens(25)
        r = compute_basis_value(specs, "B")
        self.assertGreater(r["k_factor"], 0)

    def test_correct_n_returned(self):
        specs = _deterministic_specimens(30)
        r = compute_basis_value(specs, "A")
        self.assertEqual(r["n"], 30)

    def test_insufficient_specimens_b_basis_raises(self):
        specs = _deterministic_specimens(10)
        with self.assertRaises(ValueError):
            compute_basis_value(specs, "B")

    def test_insufficient_specimens_a_basis_raises(self):
        specs = _deterministic_specimens(20)
        with self.assertRaises(ValueError):
            compute_basis_value(specs, "A")

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            compute_basis_value([], "B")

    def test_s_basis_raises(self):
        specs = _deterministic_specimens(25)
        with self.assertRaises(ValueError):
            compute_basis_value(specs, "S")


# ---------------------------------------------------------------------------
# apply_knockdown_factor
# ---------------------------------------------------------------------------

class TestApplyKnockdownFactor(unittest.TestCase):

    def test_15_percent_reduction(self):
        r = apply_knockdown_factor(800.0, 0.85)
        self.assertAlmostEqual(r["design_allowable"], 680.0, places=2)

    def test_unit_knockdown_unchanged(self):
        r = apply_knockdown_factor(500.0, 1.0)
        self.assertAlmostEqual(r["design_allowable"], 500.0, places=4)

    def test_statistical_allowable_echoed(self):
        r = apply_knockdown_factor(400.0, 0.9)
        self.assertAlmostEqual(r["statistical_allowable"], 400.0, places=4)

    def test_zero_knockdown_raises(self):
        with self.assertRaises(ValueError):
            apply_knockdown_factor(500.0, 0.0)

    def test_knockdown_above_one_raises(self):
        with self.assertRaises(ValueError):
            apply_knockdown_factor(500.0, 1.05)

    def test_non_positive_allowable_raises(self):
        with self.assertRaises(ValueError):
            apply_knockdown_factor(-200.0, 0.9)


# ---------------------------------------------------------------------------
# compute_margin_of_safety
# ---------------------------------------------------------------------------

class TestComputeMarginOfSafety(unittest.TestCase):

    def test_positive_margin_25_percent(self):
        r = compute_margin_of_safety(1000.0, 800.0)
        self.assertAlmostEqual(r["margin_of_safety"], 0.25, places=4)
        self.assertTrue(r["passes"])

    def test_zero_margin_passes(self):
        r = compute_margin_of_safety(800.0, 800.0)
        self.assertAlmostEqual(r["margin_of_safety"], 0.0, places=4)
        self.assertTrue(r["passes"])

    def test_negative_margin_fails(self):
        r = compute_margin_of_safety(700.0, 800.0)
        self.assertLess(r["margin_of_safety"], 0.0)
        self.assertFalse(r["passes"])

    def test_zero_applied_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(800.0, 0.0)

    def test_non_positive_allowable_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(0.0, 400.0)


# ---------------------------------------------------------------------------
# categorize_material
# ---------------------------------------------------------------------------

class TestCategorizeMaterial(unittest.TestCase):

    def test_carbon_epoxy_recognized(self):
        r = categorize_material("carbon", "epoxy")
        self.assertTrue(r["recognized"])
        self.assertEqual(r["fiber_category"], "high_modulus_fiber")
        self.assertEqual(r["matrix_category"], "thermoset")

    def test_glass_peek_recognized(self):
        r = categorize_material("glass", "peek")
        self.assertTrue(r["recognized"])
        self.assertEqual(r["matrix_category"], "thermoplastic")

    def test_composite_system_contains_slash(self):
        r = categorize_material("aramid", "bmi")
        self.assertTrue(r["recognized"])
        self.assertIn("/", r["composite_system"])

    def test_unknown_fiber_not_recognized(self):
        r = categorize_material("boron", "epoxy")
        self.assertFalse(r["recognized"])
        self.assertIsNone(r["composite_system"])

    def test_unknown_matrix_not_recognized(self):
        r = categorize_material("carbon", "polyester")
        self.assertFalse(r["recognized"])

    def test_empty_fiber_raises(self):
        with self.assertRaises(ValueError):
            categorize_material("", "epoxy")

    def test_empty_matrix_raises(self):
        with self.assertRaises(ValueError):
            categorize_material("carbon", "")


# ---------------------------------------------------------------------------
# check_allowables_completeness
# ---------------------------------------------------------------------------

FULL_MATRIX = [
    "fiber_tensile_longitudinal",
    "fiber_tensile_transverse",
    "fiber_compression_longitudinal",
    "fiber_compression_transverse",
    "in_plane_shear",
    "interlaminar_shear_strength",
]


class TestCheckAllowablesCompleteness(unittest.TestCase):

    def test_full_matrix_complete(self):
        r = check_allowables_completeness(FULL_MATRIX)
        self.assertTrue(r["complete"])
        self.assertEqual(r["missing"], [])

    def test_missing_ilss_incomplete(self):
        partial = [t for t in FULL_MATRIX if t != "interlaminar_shear_strength"]
        r = check_allowables_completeness(partial)
        self.assertFalse(r["complete"])
        self.assertIn("interlaminar_shear_strength", r["missing"])

    def test_extra_tests_not_penalized(self):
        extended = FULL_MATRIX + ["open_hole_tensile", "bearing_strength"]
        r = check_allowables_completeness(extended)
        self.assertTrue(r["complete"])
        self.assertIn("open_hole_tensile", r["extra"])

    def test_empty_list_incomplete(self):
        r = check_allowables_completeness([])
        self.assertFalse(r["complete"])
        self.assertEqual(len(r["missing"]), 6)

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            check_allowables_completeness("fiber_tensile_longitudinal")

    def test_required_count_is_six(self):
        r = check_allowables_completeness(FULL_MATRIX)
        self.assertEqual(r["required_count"], 6)


# ---------------------------------------------------------------------------
# compute_translation_efficiency
# ---------------------------------------------------------------------------

class TestComputeTranslationEfficiency(unittest.TestCase):

    def test_acceptable_high_efficiency(self):
        r = compute_translation_efficiency(2000.0, 1900.0)
        self.assertAlmostEqual(r["translation_efficiency"], 0.95, places=4)
        self.assertTrue(r["acceptable"])

    def test_exact_boundary_acceptable(self):
        r = compute_translation_efficiency(1000.0, 850.0)
        self.assertAlmostEqual(r["translation_efficiency"], 0.85, places=4)
        self.assertTrue(r["acceptable"])

    def test_below_boundary_not_acceptable(self):
        r = compute_translation_efficiency(2000.0, 1600.0)
        self.assertAlmostEqual(r["translation_efficiency"], 0.80, places=4)
        self.assertFalse(r["acceptable"])

    def test_zero_dry_fiber_raises(self):
        with self.assertRaises(ValueError):
            compute_translation_efficiency(0.0, 500.0)

    def test_zero_laminate_raises(self):
        with self.assertRaises(ValueError):
            compute_translation_efficiency(2000.0, 0.0)

    def test_fields_present(self):
        r = compute_translation_efficiency(1000.0, 900.0)
        for key in ("dry_fiber_strength", "laminate_strength",
                    "translation_efficiency", "acceptable"):
            self.assertIn(key, r)


if __name__ == "__main__":
    unittest.main()
