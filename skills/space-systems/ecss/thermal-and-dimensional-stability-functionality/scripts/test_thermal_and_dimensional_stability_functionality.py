"""
Offline deterministic unit tests for thermal_and_dimensional_stability_functionality_logic.

Run: python3 test_thermal_and_dimensional_stability_functionality.py
Expected output: OK
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from thermal_and_dimensional_stability_functionality_logic import (
    ThermalAssessmentError,
    categorize_regime,
    check_qualification_envelope,
    compute_thermal_stress,
    check_thermal_stress,
    compute_dimensional_change,
    check_dimensional_stability,
    aggregate_compliance,
)


class TestCategorizeRegime(unittest.TestCase):

    def test_valid_operating(self):
        self.assertEqual(categorize_regime("operating"), "operating")

    def test_valid_survival(self):
        self.assertEqual(categorize_regime("survival"), "survival")

    def test_valid_qualification(self):
        self.assertEqual(categorize_regime("qualification"), "qualification")

    def test_case_insensitive(self):
        self.assertEqual(categorize_regime("Operating"), "operating")

    def test_unrecognized_regime_raises(self):
        with self.assertRaises(ThermalAssessmentError):
            categorize_regime("extreme")

    def test_empty_string_raises(self):
        with self.assertRaises(ThermalAssessmentError):
            categorize_regime("")


class TestQualificationEnvelope(unittest.TestCase):

    def test_compliant_envelope(self):
        result = check_qualification_envelope(
            T_op_min=-20.0, T_op_max=60.0,
            T_qual_min=-30.0, T_qual_max=70.0,
            margin=5.0,
        )
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["cold_margin"], 10.0)
        self.assertAlmostEqual(result["hot_margin"], 10.0)

    def test_cold_side_fail(self):
        result = check_qualification_envelope(
            T_op_min=-20.0, T_op_max=60.0,
            T_qual_min=-22.0, T_qual_max=70.0,
            margin=5.0,
        )
        self.assertFalse(result["cold_side_ok"])
        self.assertFalse(result["compliant"])

    def test_hot_side_fail(self):
        result = check_qualification_envelope(
            T_op_min=-20.0, T_op_max=60.0,
            T_qual_min=-30.0, T_qual_max=62.0,
            margin=5.0,
        )
        self.assertFalse(result["hot_side_ok"])
        self.assertFalse(result["compliant"])

    def test_exactly_at_margin_passes(self):
        result = check_qualification_envelope(
            T_op_min=-20.0, T_op_max=60.0,
            T_qual_min=-25.0, T_qual_max=65.0,
            margin=5.0,
        )
        self.assertTrue(result["compliant"])

    def test_inverted_op_range_raises(self):
        with self.assertRaises(ThermalAssessmentError):
            check_qualification_envelope(
                T_op_min=50.0, T_op_max=10.0,
                T_qual_min=0.0, T_qual_max=60.0,
            )

    def test_negative_margin_raises(self):
        with self.assertRaises(ThermalAssessmentError):
            check_qualification_envelope(
                T_op_min=-20.0, T_op_max=60.0,
                T_qual_min=-30.0, T_qual_max=70.0,
                margin=-1.0,
            )


class TestComputeThermalStress(unittest.TestCase):

    def test_basic_stress(self):
        # sigma = 70e9 * 23e-6 * 100 * 1.0 = 161,000,000 Pa
        sigma = compute_thermal_stress(
            E=70e9, cte_effective=23e-6, delta_T=100.0, constraint_factor=1.0
        )
        self.assertAlmostEqual(sigma, 70e9 * 23e-6 * 100.0, places=0)

    def test_free_expansion_zero_stress(self):
        sigma = compute_thermal_stress(
            E=70e9, cte_effective=23e-6, delta_T=100.0, constraint_factor=0.0
        )
        self.assertEqual(sigma, 0.0)

    def test_partial_constraint(self):
        sigma_full = compute_thermal_stress(
            E=70e9, cte_effective=23e-6, delta_T=100.0, constraint_factor=1.0
        )
        sigma_half = compute_thermal_stress(
            E=70e9, cte_effective=23e-6, delta_T=100.0, constraint_factor=0.5
        )
        self.assertAlmostEqual(sigma_half, sigma_full * 0.5, places=3)

    def test_negative_delta_T_gives_positive_stress(self):
        sigma = compute_thermal_stress(
            E=70e9, cte_effective=23e-6, delta_T=-80.0, constraint_factor=1.0
        )
        self.assertGreater(sigma, 0.0)

    def test_invalid_constraint_factor_raises(self):
        with self.assertRaises(ThermalAssessmentError):
            compute_thermal_stress(
                E=70e9, cte_effective=23e-6, delta_T=100.0, constraint_factor=1.5
            )

    def test_negative_modulus_raises(self):
        with self.assertRaises(ThermalAssessmentError):
            compute_thermal_stress(
                E=-70e9, cte_effective=23e-6, delta_T=100.0, constraint_factor=1.0
            )


class TestCheckThermalStress(unittest.TestCase):

    def test_pass_with_positive_margin(self):
        result = check_thermal_stress(sigma=50e6, sigma_allowable=100e6)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_of_safety"], 1.0, places=6)

    def test_fail_with_negative_margin(self):
        result = check_thermal_stress(sigma=120e6, sigma_allowable=100e6)
        self.assertFalse(result["compliant"])
        self.assertLess(result["margin_of_safety"], 0.0)

    def test_zero_stress_is_compliant(self):
        result = check_thermal_stress(sigma=0.0, sigma_allowable=100e6)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["margin_of_safety"], float("inf"))

    def test_stress_equals_allowable(self):
        result = check_thermal_stress(sigma=100e6, sigma_allowable=100e6)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_of_safety"], 0.0, places=10)

    def test_invalid_allowable_raises(self):
        with self.assertRaises(ThermalAssessmentError):
            check_thermal_stress(sigma=50e6, sigma_allowable=0.0)

    def test_negative_sigma_raises(self):
        with self.assertRaises(ThermalAssessmentError):
            check_thermal_stress(sigma=-10e6, sigma_allowable=100e6)


class TestComputeDimensionalChange(unittest.TestCase):

    def test_pure_cte_change(self):
        # delta_L = 1e-6 * 50 * 2.0 = 1e-4 m
        delta_L = compute_dimensional_change(
            cte=1e-6, delta_T=50.0, length=2.0, irreversible_drift=0.0
        )
        self.assertAlmostEqual(delta_L, 1e-4, places=10)

    def test_with_irreversible_drift(self):
        delta_L = compute_dimensional_change(
            cte=1e-6, delta_T=50.0, length=2.0, irreversible_drift=5e-5
        )
        self.assertAlmostEqual(delta_L, 1e-4 + 5e-5, places=10)

    def test_negative_delta_T_gives_positive_change(self):
        delta_L = compute_dimensional_change(
            cte=1e-6, delta_T=-50.0, length=2.0
        )
        self.assertAlmostEqual(delta_L, 1e-4, places=10)

    def test_negative_length_raises(self):
        with self.assertRaises(ThermalAssessmentError):
            compute_dimensional_change(cte=1e-6, delta_T=50.0, length=-1.0)

    def test_negative_drift_raises(self):
        with self.assertRaises(ThermalAssessmentError):
            compute_dimensional_change(
                cte=1e-6, delta_T=50.0, length=2.0, irreversible_drift=-1e-5
            )


class TestCheckDimensionalStability(unittest.TestCase):

    def test_short_term_pass(self):
        result = check_dimensional_stability(
            delta_L=5e-5, tolerance=1e-4, time_horizon="short-term"
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["time_horizon"], "short-term")

    def test_medium_term_fail(self):
        result = check_dimensional_stability(
            delta_L=2e-4, tolerance=1e-4, time_horizon="medium-term"
        )
        self.assertFalse(result["compliant"])

    def test_long_term_exactly_at_tolerance(self):
        result = check_dimensional_stability(
            delta_L=1e-4, tolerance=1e-4, time_horizon="long-term"
        )
        self.assertTrue(result["compliant"])

    def test_unrecognized_horizon_raises(self):
        with self.assertRaises(ThermalAssessmentError):
            check_dimensional_stability(
                delta_L=5e-5, tolerance=1e-4, time_horizon="very-long-term"
            )

    def test_none_tolerance_raises(self):
        with self.assertRaises(ThermalAssessmentError):
            check_dimensional_stability(
                delta_L=5e-5, tolerance=None, time_horizon="short-term"
            )

    def test_zero_tolerance_raises(self):
        with self.assertRaises(ThermalAssessmentError):
            check_dimensional_stability(
                delta_L=5e-5, tolerance=0.0, time_horizon="short-term"
            )


class TestAggregateCompliance(unittest.TestCase):

    def _qual_pass(self):
        return check_qualification_envelope(
            T_op_min=-20.0, T_op_max=60.0,
            T_qual_min=-30.0, T_qual_max=70.0,
        )

    def _qual_fail(self):
        return check_qualification_envelope(
            T_op_min=-20.0, T_op_max=60.0,
            T_qual_min=-22.0, T_qual_max=70.0,
        )

    def test_fully_compliant(self):
        stress = [check_thermal_stress(50e6, 100e6)]
        dim = [check_dimensional_stability(5e-5, 1e-4, "short-term")]
        result = aggregate_compliance(self._qual_pass(), stress, dim)
        self.assertTrue(result["overall_compliant"])
        self.assertEqual(result["stress_failures"], [])
        self.assertEqual(result["dim_failures"], [])

    def test_qual_failure_makes_overall_fail(self):
        stress = [check_thermal_stress(50e6, 100e6)]
        dim = [check_dimensional_stability(5e-5, 1e-4, "short-term")]
        result = aggregate_compliance(self._qual_fail(), stress, dim)
        self.assertFalse(result["overall_compliant"])
        self.assertFalse(result["qual_compliant"])

    def test_stress_failure_makes_overall_fail(self):
        stress = [check_thermal_stress(200e6, 100e6)]
        dim = [check_dimensional_stability(5e-5, 1e-4, "short-term")]
        result = aggregate_compliance(self._qual_pass(), stress, dim)
        self.assertFalse(result["overall_compliant"])
        self.assertFalse(result["all_stress_compliant"])
        self.assertEqual(len(result["stress_failures"]), 1)

    def test_dim_failure_makes_overall_fail(self):
        stress = [check_thermal_stress(50e6, 100e6)]
        dim = [check_dimensional_stability(3e-4, 1e-4, "long-term")]
        result = aggregate_compliance(self._qual_pass(), stress, dim)
        self.assertFalse(result["overall_compliant"])
        self.assertFalse(result["all_dim_compliant"])
        self.assertEqual(len(result["dim_failures"]), 1)

    def test_multiple_stress_checks_all_pass(self):
        stress = [
            check_thermal_stress(50e6, 100e6),
            check_thermal_stress(30e6, 80e6),
            check_thermal_stress(0.0, 50e6),
        ]
        dim = [check_dimensional_stability(5e-5, 1e-4, "medium-term")]
        result = aggregate_compliance(self._qual_pass(), stress, dim)
        self.assertTrue(result["all_stress_compliant"])

    def test_multiple_dim_checks_one_fail(self):
        stress = [check_thermal_stress(50e6, 100e6)]
        dim = [
            check_dimensional_stability(5e-5, 1e-4, "short-term"),
            check_dimensional_stability(9e-5, 1e-4, "medium-term"),
            check_dimensional_stability(3e-4, 1e-4, "long-term"),
        ]
        result = aggregate_compliance(self._qual_pass(), stress, dim)
        self.assertFalse(result["all_dim_compliant"])
        self.assertEqual(len(result["dim_failures"]), 1)
        self.assertEqual(result["dim_failures"][0]["time_horizon"], "long-term")

    def test_empty_checks_with_qual_pass(self):
        result = aggregate_compliance(self._qual_pass(), [], [])
        self.assertTrue(result["overall_compliant"])


if __name__ == "__main__":
    unittest.main()
