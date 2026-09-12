"""
Gate 3 contract tests for material_fatigue_properties_logic.
stdlib unittest only — deterministic, offline. 10+ tests.
Run: python3 test_material_fatigue_properties.py
"""

import math
import sys
import os
import unittest

# Allow running from the scripts/ directory directly
sys.path.insert(0, os.path.dirname(__file__))

from material_fatigue_properties_logic import (
    FatigueDataError,
    assess_material_fatigue,
    apply_scatter_factor,
    categorize_dataset,
    check_record_completeness,
    compute_fatigue_ratio,
    compute_stress_parameters,
    evaluate_sn_life,
    gerber_equivalent_amplitude,
    goodman_equivalent_amplitude,
)


class TestComputeStressParameters(unittest.TestCase):

    def test_basic_tensile_cycle(self):
        sigma_a, sigma_m, R = compute_stress_parameters(200.0, 100.0)
        self.assertAlmostEqual(sigma_a, 50.0)
        self.assertAlmostEqual(sigma_m, 150.0)
        self.assertAlmostEqual(R, 0.5)

    def test_fully_reversed_cycle(self):
        sigma_a, sigma_m, R = compute_stress_parameters(100.0, -100.0)
        self.assertAlmostEqual(sigma_a, 100.0)
        self.assertAlmostEqual(sigma_m, 0.0)
        self.assertAlmostEqual(R, -1.0)

    def test_zero_amplitude_cycle(self):
        sigma_a, sigma_m, R = compute_stress_parameters(150.0, 150.0)
        self.assertAlmostEqual(sigma_a, 0.0)
        self.assertAlmostEqual(sigma_m, 150.0)
        self.assertAlmostEqual(R, 1.0)

    def test_inverted_inputs_raise_error(self):
        with self.assertRaises(FatigueDataError):
            compute_stress_parameters(50.0, 100.0)

    def test_zero_max_stress_gives_unit_r_ratio(self):
        sigma_a, sigma_m, R = compute_stress_parameters(0.0, 0.0)
        self.assertAlmostEqual(R, 1.0)


class TestGoodmanCorrection(unittest.TestCase):

    def test_zero_mean_returns_amplitude_unchanged(self):
        result = goodman_equivalent_amplitude(100.0, 0.0, 500.0)
        self.assertAlmostEqual(result, 100.0)

    def test_positive_mean_increases_equivalent_amplitude(self):
        # sigma_a=100, sigma_m=50, sigma_ult=500 → 100/(1-0.1) = 111.11
        result = goodman_equivalent_amplitude(100.0, 50.0, 500.0)
        self.assertAlmostEqual(result, 100.0 / 0.9, places=6)

    def test_mean_equals_ult_raises_error(self):
        with self.assertRaises(FatigueDataError):
            goodman_equivalent_amplitude(100.0, 500.0, 500.0)

    def test_mean_exceeds_ult_raises_error(self):
        with self.assertRaises(FatigueDataError):
            goodman_equivalent_amplitude(50.0, 600.0, 500.0)

    def test_nonpositive_ult_raises_error(self):
        with self.assertRaises(FatigueDataError):
            goodman_equivalent_amplitude(100.0, 50.0, 0.0)


class TestGerberCorrection(unittest.TestCase):

    def test_zero_mean_returns_amplitude_unchanged(self):
        result = gerber_equivalent_amplitude(100.0, 0.0, 500.0)
        self.assertAlmostEqual(result, 100.0)

    def test_positive_mean_less_conservative_than_goodman(self):
        sigma_a, sigma_m, sigma_ult = 100.0, 50.0, 500.0
        goodman = goodman_equivalent_amplitude(sigma_a, sigma_m, sigma_ult)
        gerber = gerber_equivalent_amplitude(sigma_a, sigma_m, sigma_ult)
        # Gerber is less conservative → smaller equivalent amplitude
        self.assertLess(gerber, goodman)

    def test_gerber_value_exact(self):
        # sigma_a=100, sigma_m=50, sigma_ult=500
        # 100 / (1 - (50/500)^2) = 100 / (1 - 0.01) = 100/0.99
        result = gerber_equivalent_amplitude(100.0, 50.0, 500.0)
        self.assertAlmostEqual(result, 100.0 / 0.99, places=6)

    def test_mean_equals_ult_raises_error(self):
        with self.assertRaises(FatigueDataError):
            gerber_equivalent_amplitude(100.0, 500.0, 500.0)


class TestEvaluateSnLife(unittest.TestCase):

    SN = [(200.0, 1e4), (100.0, 1e6)]  # simple two-point S-N curve

    def test_interpolation_at_boundary_high(self):
        n = evaluate_sn_life(200.0, self.SN)
        self.assertAlmostEqual(n, 1e4, delta=1.0)

    def test_interpolation_at_boundary_low(self):
        n = evaluate_sn_life(100.0, self.SN)
        self.assertAlmostEqual(n, 1e6, delta=1.0)

    def test_interpolation_midpoint_log_scale(self):
        # At the log-mean stress the log-life should be the log-mean life
        s_mid = 10 ** ((math.log10(200) + math.log10(100)) / 2)  # ~141.4
        n = evaluate_sn_life(s_mid, self.SN)
        expected_log_n = (math.log10(1e4) + math.log10(1e6)) / 2  # 5.0
        self.assertAlmostEqual(math.log10(n), expected_log_n, places=5)

    def test_extrapolation_below_min_stress(self):
        # S=50: one segment below S=100, extrapolate from (200,1e4)-(100,1e6)
        # slope in log-log: (6-4)/(log10(100)-log10(200)) = 2/(-0.301) = -6.644
        # log10(N) at S=50: 6 + slope*(log10(50)-log10(100))
        #   = 6 + (-6.644)*(-0.301) ≈ 6 + 2.0 = 8.0 → N = 1e8
        n = evaluate_sn_life(50.0, self.SN)
        self.assertAlmostEqual(math.log10(n), 8.0, places=2)

    def test_too_few_points_raises_error(self):
        with self.assertRaises(FatigueDataError):
            evaluate_sn_life(150.0, [(200.0, 1e4)])

    def test_nonpositive_stress_raises_error(self):
        with self.assertRaises(FatigueDataError):
            evaluate_sn_life(0.0, self.SN)

    def test_nonpositive_sn_value_raises_error(self):
        with self.assertRaises(FatigueDataError):
            evaluate_sn_life(150.0, [(200.0, 1e4), (-50.0, 1e6)])


class TestApplyScatterFactor(unittest.TestCase):

    def test_scatter_factor_divides_mean_life(self):
        result = apply_scatter_factor(1e6, 4.0)
        self.assertAlmostEqual(result, 2.5e5)

    def test_scatter_factor_of_one_returns_mean_life(self):
        result = apply_scatter_factor(1e6, 1.0)
        self.assertAlmostEqual(result, 1e6)

    def test_negative_scatter_factor_raises_error(self):
        with self.assertRaises(FatigueDataError):
            apply_scatter_factor(1e6, -1.0)

    def test_zero_scatter_factor_raises_error(self):
        with self.assertRaises(FatigueDataError):
            apply_scatter_factor(1e6, 0.0)

    def test_nonpositive_mean_life_raises_error(self):
        with self.assertRaises(FatigueDataError):
            apply_scatter_factor(0.0, 3.0)


class TestCategorizeDataset(unittest.TestCase):

    def test_qualified_dataset(self):
        category, findings = categorize_dataset(8, 3, True)
        self.assertEqual(category, "qualified")
        self.assertEqual(findings, [])

    def test_provisional_few_points(self):
        category, findings = categorize_dataset(4, 3, True)
        self.assertEqual(category, "provisional")
        self.assertTrue(len(findings) >= 1)

    def test_provisional_single_r_ratio(self):
        category, findings = categorize_dataset(8, 1, True)
        self.assertEqual(category, "provisional")
        self.assertTrue(any("stress-ratio" in f for f in findings))

    def test_provisional_no_runout(self):
        category, findings = categorize_dataset(8, 3, False)
        self.assertEqual(category, "provisional")
        self.assertTrue(any("run-out" in f for f in findings))

    def test_insufficient_below_three_points(self):
        category, findings = categorize_dataset(2, 2, True)
        self.assertEqual(category, "insufficient")
        self.assertTrue(len(findings) >= 1)

    def test_insufficient_zero_points(self):
        category, _ = categorize_dataset(0, 2, True)
        self.assertEqual(category, "insufficient")


class TestCheckRecordCompleteness(unittest.TestCase):

    def _complete_record(self):
        return {
            "material": "Al-7075-T651",
            "sigma_ult": 503.0,
            "endurance_limit": 159.0,
            "scatter_factor": 3.0,
            "sn_data": [(200.0, 1e5), (150.0, 5e5), (100.0, 2e6)],
            "r_ratio_variants": 2,
        }

    def test_complete_record_passes(self):
        complete, missing = check_record_completeness(self._complete_record())
        self.assertTrue(complete)
        self.assertEqual(missing, [])

    def test_missing_scatter_factor_flagged(self):
        rec = self._complete_record()
        del rec["scatter_factor"]
        complete, missing = check_record_completeness(rec)
        self.assertFalse(complete)
        self.assertIn("scatter_factor", missing)

    def test_none_value_treated_as_missing(self):
        rec = self._complete_record()
        rec["sigma_ult"] = None
        complete, missing = check_record_completeness(rec)
        self.assertFalse(complete)
        self.assertIn("sigma_ult", missing)

    def test_multiple_missing_fields(self):
        complete, missing = check_record_completeness({})
        self.assertFalse(complete)
        self.assertEqual(len(missing), 6)


class TestComputeFatigueRatio(unittest.TestCase):

    def test_typical_aluminium_alloy(self):
        ratio = compute_fatigue_ratio(159.0, 503.0)
        self.assertAlmostEqual(ratio, 159.0 / 503.0, places=8)

    def test_ratio_in_expected_band(self):
        ratio = compute_fatigue_ratio(200.0, 500.0)
        self.assertAlmostEqual(ratio, 0.4)

    def test_zero_ult_raises_error(self):
        with self.assertRaises(FatigueDataError):
            compute_fatigue_ratio(150.0, 0.0)

    def test_negative_endurance_limit_raises_error(self):
        with self.assertRaises(FatigueDataError):
            compute_fatigue_ratio(-10.0, 500.0)


class TestAssessMaterialFatigue(unittest.TestCase):

    def _qualified_record(self):
        return {
            "material": "Ti-6Al-4V",
            "sigma_ult": 900.0,
            "endurance_limit": 400.0,
            "scatter_factor": 3.0,
            "sn_data": [
                (500.0, 1e4),
                (400.0, 5e4),
                (300.0, 2e5),
                (250.0, 5e5),
                (200.0, 2e6),
                (180.0, 1e7),
            ],
            "r_ratio_variants": 3,
            "has_runout_data": True,
        }

    def test_complete_qualified_record_no_fatal_findings(self):
        result = assess_material_fatigue(self._qualified_record())
        self.assertTrue(result["complete"])
        self.assertEqual(result["category"], "qualified")
        # fatigue ratio = 400/900 ≈ 0.444, within band — no fatigue-ratio finding
        self.assertEqual(result["missing_fields"], [])

    def test_fatigue_ratio_computed_correctly(self):
        result = assess_material_fatigue(self._qualified_record())
        self.assertAlmostEqual(result["fatigue_ratio"], 400.0 / 900.0, places=8)

    def test_incomplete_record_flagged(self):
        rec = self._qualified_record()
        del rec["endurance_limit"]
        result = assess_material_fatigue(rec)
        self.assertFalse(result["complete"])
        self.assertIn("endurance_limit", result["missing_fields"])
        self.assertIsNone(result["category"])

    def test_provisional_dataset_category_returned(self):
        rec = self._qualified_record()
        rec["r_ratio_variants"] = 1
        rec["has_runout_data"] = False
        result = assess_material_fatigue(rec)
        self.assertEqual(result["category"], "provisional")
        self.assertTrue(len(result["findings"]) >= 1)

    def test_out_of_band_fatigue_ratio_flagged(self):
        rec = self._qualified_record()
        rec["endurance_limit"] = 50.0  # ratio = 50/900 ≈ 0.056, below 0.35
        result = assess_material_fatigue(rec)
        self.assertTrue(
            any("fatigue ratio" in f.lower() for f in result["findings"]),
            "Expected a fatigue-ratio finding but got: " + str(result["findings"]),
        )

    def test_zero_sigma_ult_returns_error_finding(self):
        rec = self._qualified_record()
        rec["sigma_ult"] = 0.0
        result = assess_material_fatigue(rec)
        self.assertTrue(len(result["findings"]) >= 1)


if __name__ == "__main__":
    unittest.main()
