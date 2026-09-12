"""
Gate 3 contract tests — drd-fracture-control-analysis.
Run: python3 test_drd_fracture_control_analysis.py
stdlib unittest only; offline; deterministic.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from drd_fracture_control_analysis_logic import (
    categorize_item,
    check_damage_tolerance,
    check_fracture_toughness,
    check_leak_before_burst,
    compute_critical_flaw_size,
    compute_stress_intensity_factor,
    generate_fca_report,
    integrate_crack_growth,
    validate_ndi_capability,
)


# ---------------------------------------------------------------------------
# 1. categorize_item
# ---------------------------------------------------------------------------

class TestCategorizeItem(unittest.TestCase):

    def test_catastrophic_yields_fracture_critical(self):
        self.assertEqual(categorize_item("catastrophic"), "fracture_critical")

    def test_non_catastrophic_yields_non_fracture_critical(self):
        self.assertEqual(categorize_item("non_catastrophic"), "non_fracture_critical")

    def test_unknown_consequence_raises(self):
        with self.assertRaises(ValueError):
            categorize_item("minor")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            categorize_item("")


# ---------------------------------------------------------------------------
# 2. compute_stress_intensity_factor
# ---------------------------------------------------------------------------

class TestComputeStressIntensityFactor(unittest.TestCase):

    def test_basic_formula_unit_geometry(self):
        # K = 1.0 * 100 * sqrt(pi * 0.001 m)
        K = compute_stress_intensity_factor(100.0, 1.0, 1.0)
        expected = 100.0 * math.sqrt(math.pi * 0.001)
        self.assertAlmostEqual(K, expected, places=8)

    def test_geometry_factor_scales_linearly(self):
        K1 = compute_stress_intensity_factor(100.0, 1.0, 1.0)
        K2 = compute_stress_intensity_factor(100.0, 1.0, 2.0)
        self.assertAlmostEqual(K2, 2.0 * K1, places=8)

    def test_larger_flaw_gives_larger_K(self):
        K_small = compute_stress_intensity_factor(100.0, 1.0)
        K_large = compute_stress_intensity_factor(100.0, 4.0)
        self.assertGreater(K_large, K_small)

    def test_zero_stress_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_intensity_factor(0.0, 1.0)

    def test_negative_flaw_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_intensity_factor(100.0, -0.5)

    def test_zero_geometry_factor_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_intensity_factor(100.0, 1.0, 0.0)


# ---------------------------------------------------------------------------
# 3. compute_critical_flaw_size
# ---------------------------------------------------------------------------

class TestComputeCriticalFlawSize(unittest.TestCase):

    def test_round_trip_with_stress_intensity(self):
        stress = 200.0
        a_mm = 5.0
        Y = 1.12
        K = compute_stress_intensity_factor(stress, a_mm, Y)
        a_c = compute_critical_flaw_size(K, stress, Y)
        self.assertAlmostEqual(a_c, a_mm, places=4)

    def test_higher_toughness_gives_larger_critical_flaw(self):
        a1 = compute_critical_flaw_size(30.0, 200.0)
        a2 = compute_critical_flaw_size(60.0, 200.0)
        self.assertGreater(a2, a1)

    def test_zero_toughness_raises(self):
        with self.assertRaises(ValueError):
            compute_critical_flaw_size(0.0, 200.0)

    def test_zero_stress_raises(self):
        with self.assertRaises(ValueError):
            compute_critical_flaw_size(30.0, 0.0)


# ---------------------------------------------------------------------------
# 4. check_fracture_toughness
# ---------------------------------------------------------------------------

class TestCheckFractureToughness(unittest.TestCase):

    def test_pass_when_K_below_allowable(self):
        result = check_fracture_toughness(20.0, 30.0, 1.0)
        self.assertTrue(result["passed"])

    def test_fail_when_K_exceeds_allowable(self):
        result = check_fracture_toughness(35.0, 30.0, 1.0)
        self.assertFalse(result["passed"])

    def test_safety_factor_halves_allowable(self):
        result = check_fracture_toughness(20.0, 30.0, 2.0)
        self.assertAlmostEqual(result["allowable_mpa_sqm"], 15.0, places=8)

    def test_safety_factor_can_cause_failure(self):
        result = check_fracture_toughness(20.0, 30.0, 2.0)
        self.assertFalse(result["passed"])

    def test_margin_ratio_at_half_allowable(self):
        result = check_fracture_toughness(15.0, 30.0, 1.0)
        self.assertAlmostEqual(result["margin_ratio"], 0.5, places=8)

    def test_negative_margin_on_exceedance(self):
        result = check_fracture_toughness(40.0, 30.0, 1.0)
        self.assertLess(result["margin_ratio"], 0.0)

    def test_zero_K_IC_raises(self):
        with self.assertRaises(ValueError):
            check_fracture_toughness(20.0, 0.0)


# ---------------------------------------------------------------------------
# 5. check_leak_before_burst
# ---------------------------------------------------------------------------

class TestCheckLeakBeforeBurst(unittest.TestCase):

    def test_pass_when_critical_flaw_exceeds_wall(self):
        result = check_leak_before_burst(10.0, 8.0)
        self.assertTrue(result["passed"])

    def test_fail_when_critical_flaw_below_wall(self):
        result = check_leak_before_burst(5.0, 8.0)
        self.assertFalse(result["passed"])

    def test_exact_equality_passes(self):
        result = check_leak_before_burst(8.0, 8.0)
        self.assertTrue(result["passed"])

    def test_margin_computed_correctly(self):
        result = check_leak_before_burst(10.0, 8.0)
        self.assertAlmostEqual(result["margin_mm"], 2.0, places=8)

    def test_zero_wall_thickness_raises(self):
        with self.assertRaises(ValueError):
            check_leak_before_burst(10.0, 0.0)


# ---------------------------------------------------------------------------
# 6. check_damage_tolerance
# ---------------------------------------------------------------------------

class TestCheckDamageTolerance(unittest.TestCase):

    def test_pass_when_life_exceeds_target(self):
        result = check_damage_tolerance(200_000, 40_000, 4.0)
        self.assertTrue(result["passed"])

    def test_fail_when_life_below_target(self):
        result = check_damage_tolerance(100_000, 40_000, 4.0)
        self.assertFalse(result["passed"])

    def test_target_cycles_is_product(self):
        result = check_damage_tolerance(200_000, 40_000, 4.0)
        self.assertAlmostEqual(result["target_cycles"], 160_000.0, places=4)

    def test_margin_positive_on_pass(self):
        result = check_damage_tolerance(200_000, 40_000, 4.0)
        self.assertGreater(result["margin_cycles"], 0.0)

    def test_zero_required_life_raises(self):
        with self.assertRaises(ValueError):
            check_damage_tolerance(200_000, 0, 4.0)


# ---------------------------------------------------------------------------
# 7. integrate_crack_growth
# ---------------------------------------------------------------------------

class TestIntegrateCrackGrowth(unittest.TestCase):

    def test_returns_positive_integer_cycles(self):
        N = integrate_crack_growth(0.5, 5.0, 1e-12, 3.0, 100.0)
        self.assertIsInstance(N, int)
        self.assertGreater(N, 0)

    def test_larger_initial_flaw_gives_fewer_cycles(self):
        N1 = integrate_crack_growth(0.5, 5.0, 1e-12, 3.0, 100.0)
        N2 = integrate_crack_growth(2.0, 5.0, 1e-12, 3.0, 100.0)
        self.assertLess(N2, N1)

    def test_higher_stress_range_gives_fewer_cycles(self):
        N_low = integrate_crack_growth(0.5, 5.0, 1e-12, 3.0, 100.0)
        N_high = integrate_crack_growth(0.5, 5.0, 1e-12, 3.0, 200.0)
        self.assertLess(N_high, N_low)

    def test_initial_ge_final_raises(self):
        with self.assertRaises(ValueError):
            integrate_crack_growth(5.0, 0.5, 1e-12, 3.0, 100.0)

    def test_equal_initial_and_final_raises(self):
        with self.assertRaises(ValueError):
            integrate_crack_growth(5.0, 5.0, 1e-12, 3.0, 100.0)


# ---------------------------------------------------------------------------
# 8. validate_ndi_capability
# ---------------------------------------------------------------------------

class TestValidateNdiCapability(unittest.TestCase):

    def test_pass_when_detectable_le_assumed(self):
        result = validate_ndi_capability("ultrasonic", 0.5, 1.0)
        self.assertTrue(result["passed"])

    def test_fail_when_detectable_gt_assumed(self):
        result = validate_ndi_capability("ultrasonic", 2.0, 1.0)
        self.assertFalse(result["passed"])

    def test_exact_equality_passes(self):
        result = validate_ndi_capability("penetrant", 1.0, 1.0)
        self.assertTrue(result["passed"])

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            validate_ndi_capability("sonar", 0.5, 1.0)

    def test_all_valid_methods_accepted(self):
        for method in ("penetrant", "radiography", "ultrasonic", "eddy_current", "visual"):
            result = validate_ndi_capability(method, 0.5, 1.0)
            self.assertIn("passed", result)


# ---------------------------------------------------------------------------
# 9. generate_fca_report
# ---------------------------------------------------------------------------

class TestGenerateFcaReport(unittest.TestCase):

    def _make_item(self, name, category, tc_passed, dt_passed):
        return {
            "name": name,
            "category": category,
            "toughness_check": {"passed": tc_passed},
            "dt_check": {"passed": dt_passed},
        }

    def test_all_compliant_returns_true(self):
        items = [
            self._make_item("bracket_A", "fracture_critical", True, True),
            self._make_item("panel_B", "non_fracture_critical", True, True),
        ]
        report = generate_fca_report(items)
        self.assertTrue(report["compliant"])

    def test_totals_correct(self):
        items = [
            self._make_item("A", "fracture_critical", True, True),
            self._make_item("B", "fracture_critical", True, True),
            self._make_item("C", "non_fracture_critical", True, True),
        ]
        report = generate_fca_report(items)
        self.assertEqual(report["total_items"], 3)
        self.assertEqual(report["fracture_critical_count"], 2)
        self.assertEqual(report["non_fracture_critical_count"], 1)

    def test_toughness_failure_flagged(self):
        items = [self._make_item("spar_C", "fracture_critical", False, True)]
        report = generate_fca_report(items)
        self.assertFalse(report["compliant"])
        issues = report["non_compliant_items"][0]["issues"]
        self.assertIn("fracture_toughness_exceeded", issues)

    def test_dt_failure_flagged(self):
        items = [self._make_item("rib_D", "fracture_critical", True, False)]
        report = generate_fca_report(items)
        self.assertFalse(report["compliant"])
        issues = report["non_compliant_items"][0]["issues"]
        self.assertIn("damage_tolerance_not_met", issues)

    def test_both_failures_both_flagged(self):
        items = [self._make_item("lug_E", "fracture_critical", False, False)]
        report = generate_fca_report(items)
        issues = report["non_compliant_items"][0]["issues"]
        self.assertIn("fracture_toughness_exceeded", issues)
        self.assertIn("damage_tolerance_not_met", issues)

    def test_missing_key_raises(self):
        items = [{"name": "bad_item", "category": "fracture_critical"}]
        with self.assertRaises(ValueError):
            generate_fca_report(items)

    def test_empty_list_returns_compliant_zero_totals(self):
        report = generate_fca_report([])
        self.assertTrue(report["compliant"])
        self.assertEqual(report["total_items"], 0)
        self.assertEqual(report["fracture_critical_count"], 0)


if __name__ == "__main__":
    unittest.main()
