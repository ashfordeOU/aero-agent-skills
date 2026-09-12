# test_bonded_joint_analysis.py
# stdlib unittest; offline; deterministic. Run: python3 test_bonded_joint_analysis.py

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from bonded_joint_analysis_logic import (
    compute_average_shear_stress,
    compute_margin_of_safety,
    compute_peak_shear_stress,
    compute_peel_stress,
    compute_shear_lag_parameter,
    evaluate_bonded_joint,
    validate_inputs,
)

# ── shared fixture values ────────────────────────────────────────────────────
E_AL = 70e9       # Pa  aluminium adherend Young's modulus
T_AD = 2e-3       # m   adherend thickness (2 mm)
G_ADH = 1.5e9     # Pa  adhesive shear modulus
E_ADH = 3.5e9     # Pa  adhesive tensile modulus
T_ADH = 0.2e-3    # m   adhesive thickness (0.2 mm)
L = 25e-3         # m   overlap length (25 mm)
B = 20e-3         # m   bond width (20 mm)
P = 5000.0        # N   applied axial load
ALLOW_SHR = 50e6  # Pa  generous shear allowable (covers ~40.9 MPa peak)
ALLOW_PEL = 10e6  # Pa  generous peel allowable  (covers ~5.3 MPa peak)
# ────────────────────────────────────────────────────────────────────────────


class TestShearLagParameter(unittest.TestCase):
    def test_identical_adherends_positive(self):
        omega = compute_shear_lag_parameter(G_ADH, T_ADH, E_AL, T_AD, E_AL, T_AD)
        self.assertGreater(omega, 0.0)

    def test_identical_adherends_order_invariant(self):
        omega_a = compute_shear_lag_parameter(G_ADH, T_ADH, E_AL, T_AD, E_AL, T_AD)
        omega_b = compute_shear_lag_parameter(G_ADH, T_ADH, E_AL, T_AD, E_AL, T_AD)
        self.assertAlmostEqual(omega_a, omega_b)

    def test_stiffer_adherend_reduces_omega(self):
        omega_soft = compute_shear_lag_parameter(G_ADH, T_ADH, 35e9, T_AD, 35e9, T_AD)
        omega_stiff = compute_shear_lag_parameter(G_ADH, T_ADH, 70e9, T_AD, 70e9, T_AD)
        self.assertGreater(omega_soft, omega_stiff)

    def test_thicker_adhesive_reduces_omega(self):
        omega_thin = compute_shear_lag_parameter(G_ADH, 0.1e-3, E_AL, T_AD, E_AL, T_AD)
        omega_thick = compute_shear_lag_parameter(G_ADH, 0.4e-3, E_AL, T_AD, E_AL, T_AD)
        self.assertGreater(omega_thin, omega_thick)

    def test_numerical_value_within_expected_range(self):
        # omega² = (1.5e9/2e-4)*(2/(70e9*2e-3)) = 7.5e12 * 1.4286e-8 ≈ 1.0714e5
        omega = compute_shear_lag_parameter(G_ADH, T_ADH, E_AL, T_AD, E_AL, T_AD)
        self.assertAlmostEqual(omega, math.sqrt(1.07143e5), delta=5.0)


class TestPeakShearStress(unittest.TestCase):
    def test_peak_exceeds_average(self):
        omega = compute_shear_lag_parameter(G_ADH, T_ADH, E_AL, T_AD, E_AL, T_AD)
        tau_peak = compute_peak_shear_stress(P, B, L, omega)
        tau_avg = compute_average_shear_stress(P, B, L)
        self.assertGreater(tau_peak, tau_avg)

    def test_zero_load_gives_zero_peak(self):
        omega = compute_shear_lag_parameter(G_ADH, T_ADH, E_AL, T_AD, E_AL, T_AD)
        self.assertAlmostEqual(compute_peak_shear_stress(0.0, B, L, omega), 0.0)

    def test_longer_overlap_reduces_peak_stress(self):
        omega = compute_shear_lag_parameter(G_ADH, T_ADH, E_AL, T_AD, E_AL, T_AD)
        tau_short = compute_peak_shear_stress(P, B, 10e-3, omega)
        tau_long = compute_peak_shear_stress(P, B, 50e-3, omega)
        self.assertGreater(tau_short, tau_long)

    def test_wider_bond_reduces_peak_stress(self):
        omega = compute_shear_lag_parameter(G_ADH, T_ADH, E_AL, T_AD, E_AL, T_AD)
        tau_narrow = compute_peak_shear_stress(P, 10e-3, L, omega)
        tau_wide = compute_peak_shear_stress(P, 40e-3, L, omega)
        self.assertGreater(tau_narrow, tau_wide)

    def test_degenerate_tiny_omega_equals_average(self):
        # omega -> 0 should recover uniform shear (average)
        tau_peak = compute_peak_shear_stress(P, B, L, 1e-15)
        tau_avg = compute_average_shear_stress(P, B, L)
        self.assertAlmostEqual(tau_peak, tau_avg, places=2)


class TestAverageShearStress(unittest.TestCase):
    def test_average_stress_formula(self):
        # tau_avg = P / (b*l)
        expected = 5000.0 / (0.02 * 0.025)
        self.assertAlmostEqual(compute_average_shear_stress(P, B, L), expected)

    def test_proportional_to_load(self):
        tau1 = compute_average_shear_stress(1000.0, B, L)
        tau2 = compute_average_shear_stress(2000.0, B, L)
        self.assertAlmostEqual(tau2 / tau1, 2.0)


class TestPeelStress(unittest.TestCase):
    def test_single_lap_positive(self):
        sigma = compute_peel_stress(P, B, L, T_AD, T_AD, T_ADH, "single_lap")
        self.assertGreater(sigma, 0.0)

    def test_double_lap_zero_peel(self):
        sigma = compute_peel_stress(P, B, L, T_AD, T_AD, T_ADH, "double_lap")
        self.assertAlmostEqual(sigma, 0.0)

    def test_scarf_treated_conservatively(self):
        sigma_sl = compute_peel_stress(P, B, L, T_AD, T_AD, T_ADH, "single_lap")
        sigma_sc = compute_peel_stress(P, B, L, T_AD, T_AD, T_ADH, "scarf")
        self.assertAlmostEqual(sigma_sl, sigma_sc)

    def test_longer_overlap_reduces_peel(self):
        sigma_short = compute_peel_stress(P, B, 10e-3, T_AD, T_AD, T_ADH, "single_lap")
        sigma_long = compute_peel_stress(P, B, 50e-3, T_AD, T_AD, T_ADH, "single_lap")
        self.assertGreater(sigma_short, sigma_long)

    def test_thicker_adherends_increase_peel(self):
        sigma_thin = compute_peel_stress(P, B, L, 1e-3, 1e-3, T_ADH, "single_lap")
        sigma_thick = compute_peel_stress(P, B, L, 4e-3, 4e-3, T_ADH, "single_lap")
        self.assertGreater(sigma_thick, sigma_thin)


class TestMarginOfSafety(unittest.TestCase):
    def test_positive_margin(self):
        ms = compute_margin_of_safety(100.0, 80.0)
        self.assertAlmostEqual(ms, 0.25)

    def test_negative_margin(self):
        ms = compute_margin_of_safety(80.0, 100.0)
        self.assertLess(ms, 0.0)

    def test_zero_margin_at_equality(self):
        self.assertAlmostEqual(compute_margin_of_safety(50.0, 50.0), 0.0)

    def test_infinite_margin_at_zero_load(self):
        self.assertEqual(compute_margin_of_safety(50.0, 0.0), float("inf"))


class TestValidation(unittest.TestCase):
    def _base_call(self, **overrides):
        kwargs = dict(
            E1=E_AL, t1=T_AD, E2=E_AL, t2=T_AD,
            G_a=G_ADH, E_a=E_ADH, t_a=T_ADH,
            allow_shear=ALLOW_SHR, allow_peel=ALLOW_PEL,
            overlap_length=L, bond_width=B,
            applied_load=P, joint_type="single_lap",
        )
        kwargs.update(overrides)
        validate_inputs(**kwargs)

    def test_raises_on_negative_modulus(self):
        with self.assertRaises(ValueError):
            self._base_call(E1=-70e9)

    def test_raises_on_zero_overlap(self):
        with self.assertRaises(ValueError):
            self._base_call(overlap_length=0.0)

    def test_raises_on_invalid_joint_type(self):
        with self.assertRaises(ValueError):
            self._base_call(joint_type="riveted")

    def test_raises_on_negative_load_is_allowed_but_below_raises(self):
        with self.assertRaises(ValueError):
            self._base_call(applied_load=-1.0)

    def test_zero_load_is_valid(self):
        self._base_call(applied_load=0.0)  # must not raise


class TestEvaluateBondedJoint(unittest.TestCase):
    def _run(self, allow_shear=ALLOW_SHR, allow_peel=ALLOW_PEL,
             load=P, joint_type="single_lap"):
        return evaluate_bonded_joint(
            E_AL, T_AD, E_AL, T_AD,
            G_ADH, E_ADH, T_ADH,
            allow_shear, allow_peel,
            L, B, load, joint_type,
        )

    def test_pass_with_generous_allowables(self):
        result = self._run()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(len(result["findings"]), 0)

    def test_shear_fail_low_shear_allowable(self):
        result = self._run(allow_shear=20e6)  # peak ~40.9 MPa > 20 MPa
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("SHEAR FAIL" in f for f in result["findings"]))

    def test_peel_fail_low_peel_allowable(self):
        result = self._run(allow_peel=1e6)  # peak ~5.3 MPa > 1 MPa
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("PEEL FAIL" in f for f in result["findings"]))

    def test_both_fail_produces_two_findings(self):
        result = self._run(allow_shear=20e6, allow_peel=1e6)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(len(result["findings"]), 2)

    def test_double_lap_peel_margin_infinite(self):
        result = self._run(allow_peel=1e6, joint_type="double_lap")
        self.assertEqual(result["ms_peel"], float("inf"))

    def test_scf_greater_than_one_for_compliant_short_bond(self):
        result = self._run()
        self.assertGreater(result["stress_concentration_factor"], 1.0)

    def test_zero_load_gives_pass(self):
        result = self._run(load=0.0)
        self.assertEqual(result["status"], "PASS")

    def test_result_contains_all_required_keys(self):
        result = self._run()
        required = {
            "status", "omega_per_m", "tau_max_Pa", "tau_avg_Pa",
            "sigma_peel_Pa", "ms_shear", "ms_peel",
            "stress_concentration_factor", "findings",
        }
        self.assertTrue(required.issubset(result.keys()))

    def test_ms_shear_consistent_with_stresses(self):
        result = self._run()
        expected_ms = ALLOW_SHR / result["tau_max_Pa"] - 1.0
        self.assertAlmostEqual(result["ms_shear"], expected_ms, places=10)

    def test_ms_peel_consistent_with_stresses(self):
        result = self._run()
        expected_ms = ALLOW_PEL / result["sigma_peel_Pa"] - 1.0
        self.assertAlmostEqual(result["ms_peel"], expected_ms, places=10)


if __name__ == "__main__":
    unittest.main()
