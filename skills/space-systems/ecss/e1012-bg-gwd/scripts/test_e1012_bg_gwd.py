"""
Gate-3 contract tests for e1012-bg-gwd radiation-noise logic.
Run: python3 test_e1012_bg_gwd.py
Stdlib unittest only. Offline, deterministic.
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from e1012_bg_gwd_logic import (
    _ELEMENTARY_CHARGE,
    compute_charge_deposition_rate,
    compute_charge_force_noise_psd,
    compute_cosmic_ray_recoil_force_psd,
    compute_displacement_noise_psd,
    compute_accumulated_charge,
    check_charge_budget,
    check_noise_budget,
    assess_gwd_radiation_noise,
)

_E = _ELEMENTARY_CHARGE  # shorthand


class TestChargeDepositionRate(unittest.TestCase):

    def test_basic_product(self):
        # 1000 particles/cm²/s × 4.0 cm² × 1.0 charge/hit = 4000 charges/s
        result = compute_charge_deposition_rate(1000.0, 4.0, 1.0)
        self.assertAlmostEqual(result, 4000.0, places=10)

    def test_doubles_with_doubled_flux(self):
        rate1 = compute_charge_deposition_rate(500.0, 4.0, 2.0)
        rate2 = compute_charge_deposition_rate(1000.0, 4.0, 2.0)
        self.assertAlmostEqual(rate2 / rate1, 2.0, places=10)

    def test_invalid_negative_flux_raises(self):
        with self.assertRaises(ValueError):
            compute_charge_deposition_rate(-1.0, 4.0, 1.0)

    def test_invalid_zero_area_raises(self):
        with self.assertRaises(ValueError):
            compute_charge_deposition_rate(1000.0, 0.0, 1.0)

    def test_invalid_zero_charges_per_hit_raises(self):
        with self.assertRaises(ValueError):
            compute_charge_deposition_rate(1000.0, 4.0, 0.0)


class TestChargeForceNoisePsd(unittest.TestCase):

    def test_zero_coupling_returns_zero(self):
        result = compute_charge_force_noise_psd(4000.0, 0.0, 1e-3)
        self.assertEqual(result, 0.0)

    def test_formula_at_known_values(self):
        # charge_rate=4000, coupling=0.01 N/C, freq=1e-3 Hz
        # S_F = (0.01)^2 * 2 * e^2 * 4000 / (2*pi*1e-3)^2
        cr = 4000.0
        alpha = 0.01
        f = 1e-3
        expected = alpha ** 2 * 2.0 * _E ** 2 * cr / (2.0 * math.pi * f) ** 2
        result = compute_charge_force_noise_psd(cr, alpha, f)
        self.assertAlmostEqual(result / expected, 1.0, places=12)

    def test_scales_as_inverse_freq_squared(self):
        # S_F ∝ 1/f² — tripling f reduces S_F by factor 9
        s1 = compute_charge_force_noise_psd(1000.0, 0.005, 1e-3)
        s2 = compute_charge_force_noise_psd(1000.0, 0.005, 3e-3)
        self.assertAlmostEqual(s1 / s2, 9.0, places=10)

    def test_invalid_negative_coupling_raises(self):
        with self.assertRaises(ValueError):
            compute_charge_force_noise_psd(1000.0, -0.01, 1e-3)

    def test_invalid_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            compute_charge_force_noise_psd(1000.0, 0.01, 0.0)


class TestCosmicRayRecoilForcePsd(unittest.TestCase):

    def test_formula_at_known_values(self):
        # cr_flux=4.0 /cm²/s, area=100 cm², p=1e-19 kg·m/s
        # rate = 4*100 = 400 /s; S_F = 2*400*(1e-19)^2 = 8e-36 N²/Hz
        result = compute_cosmic_ray_recoil_force_psd(4.0, 100.0, 1e-19)
        self.assertAlmostEqual(result, 8e-36, places=48)

    def test_doubles_with_doubled_flux(self):
        s1 = compute_cosmic_ray_recoil_force_psd(2.0, 50.0, 1e-20)
        s2 = compute_cosmic_ray_recoil_force_psd(4.0, 50.0, 1e-20)
        self.assertAlmostEqual(s2 / s1, 2.0, places=10)

    def test_invalid_zero_area_raises(self):
        with self.assertRaises(ValueError):
            compute_cosmic_ray_recoil_force_psd(4.0, 0.0, 1e-19)

    def test_invalid_zero_momentum_raises(self):
        with self.assertRaises(ValueError):
            compute_cosmic_ray_recoil_force_psd(4.0, 100.0, 0.0)


class TestDisplacementNoisePsd(unittest.TestCase):

    def test_formula_at_known_values(self):
        # S_F=8e-36, m=2.0 kg, f=1e-3 Hz
        # denom = (2.0 * (2*pi*1e-3)^2)^2
        f = 1e-3
        m = 2.0
        s_f = 8e-36
        denom = (m * (2.0 * math.pi * f) ** 2) ** 2
        expected = s_f / denom
        result = compute_displacement_noise_psd(s_f, m, f)
        self.assertAlmostEqual(result / expected, 1.0, places=12)

    def test_scales_as_inverse_freq_to_fourth(self):
        # White force noise (CR recoil only) → S_x ∝ 1/f^4
        s_f = compute_cosmic_ray_recoil_force_psd(4.0, 100.0, 1e-19)
        f1, f2 = 1e-3, 2e-3
        sx1 = compute_displacement_noise_psd(s_f, 2.0, f1)
        sx2 = compute_displacement_noise_psd(s_f, 2.0, f2)
        # ratio should be (f2/f1)^4 = 2^4 = 16
        self.assertAlmostEqual(sx1 / sx2, 16.0, places=10)

    def test_invalid_zero_mass_raises(self):
        with self.assertRaises(ValueError):
            compute_displacement_noise_psd(1e-30, 0.0, 1e-3)

    def test_invalid_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            compute_displacement_noise_psd(1e-30, 2.0, 0.0)


class TestAccumulatedCharge(unittest.TestCase):

    def test_basic_formula(self):
        # Q = rate * e * duration
        rate = 4000.0
        duration = 1e6
        expected = rate * _E * duration
        result = compute_accumulated_charge(rate, duration)
        self.assertAlmostEqual(result / expected, 1.0, places=12)

    def test_proportional_to_duration(self):
        q1 = compute_accumulated_charge(1000.0, 1e4)
        q2 = compute_accumulated_charge(1000.0, 2e4)
        self.assertAlmostEqual(q2 / q1, 2.0, places=10)

    def test_invalid_zero_duration_raises(self):
        with self.assertRaises(ValueError):
            compute_accumulated_charge(1000.0, 0.0)


class TestCheckChargeBudget(unittest.TestCase):

    def test_pass_when_within_limit(self):
        result = check_charge_budget(1e-10, 1e-9)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_C"], 9e-10, places=20)
        self.assertIsNone(result["finding"])

    def test_fail_when_exceeds_limit(self):
        result = check_charge_budget(2e-9, 1e-9)
        self.assertFalse(result["compliant"])
        self.assertLess(result["margin_C"], 0.0)
        self.assertIsNotNone(result["finding"])

    def test_finding_message_mentions_limit(self):
        result = check_charge_budget(5e-9, 1e-9)
        self.assertIn("1.000e-09", result["finding"])

    def test_invalid_max_allowable_raises(self):
        with self.assertRaises(ValueError):
            check_charge_budget(1e-10, 0.0)


class TestCheckNoiseBudget(unittest.TestCase):

    def test_pass_when_within_budget(self):
        result = check_noise_budget(1e-28, 1e-27)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_ratio"], 10.0, places=10)
        self.assertIsNone(result["finding"])

    def test_fail_when_exceeds_budget(self):
        result = check_noise_budget(1e-27, 1e-28)
        self.assertFalse(result["compliant"])
        self.assertLess(result["margin_ratio"], 1.0)
        self.assertIsNotNone(result["finding"])

    def test_zero_psd_returns_inf_ratio(self):
        result = check_noise_budget(0.0, 1e-27)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["margin_ratio"], float("inf"))

    def test_invalid_budget_raises(self):
        with self.assertRaises(ValueError):
            check_noise_budget(1e-28, 0.0)


class TestAssessGwdRadiationNoise(unittest.TestCase):

    def _base_params(self):
        return {
            "particle_flux_per_cm2_s": 100.0,
            "effective_area_cm2": 4.0,
            "mean_charges_per_hit": 1.0,
            "coupling_N_per_C": 1e-3,
            "frequency_hz": 1e-3,
            "cr_flux_per_cm2_s": 2.0,
            "test_mass_area_cm2": 100.0,
            "mean_momentum_transfer_kg_m_s": 1e-20,
            "test_mass_kg": 2.0,
            "exposure_duration_s": 1e4,
            "max_allowable_charge_C": 1e-7,
            "noise_budget_m2_per_Hz": 1e-27,
        }

    def test_overall_compliant_when_all_pass(self):
        result = assess_gwd_radiation_noise(self._base_params())
        self.assertTrue(result["overall_compliant"])
        self.assertEqual(result["findings"], [])

    def test_noise_exceedance_detected(self):
        p = self._base_params()
        p["noise_budget_m2_per_Hz"] = 1e-40  # impossibly tight
        result = assess_gwd_radiation_noise(p)
        self.assertFalse(result["noise_check"]["compliant"])
        self.assertFalse(result["overall_compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_charge_exceedance_detected(self):
        p = self._base_params()
        p["max_allowable_charge_C"] = 1e-20  # far below expected accumulation
        result = assess_gwd_radiation_noise(p)
        self.assertFalse(result["charge_check"]["compliant"])
        self.assertFalse(result["overall_compliant"])
        self.assertGreaterEqual(len(result["findings"]), 1)

    def test_missing_param_raises_key_error(self):
        p = self._base_params()
        del p["test_mass_kg"]
        with self.assertRaises(KeyError):
            assess_gwd_radiation_noise(p)

    def test_output_keys_present(self):
        result = assess_gwd_radiation_noise(self._base_params())
        for key in [
            "charge_rate_per_s",
            "force_psd_charge_N2_per_Hz",
            "force_psd_recoil_N2_per_Hz",
            "total_force_psd_N2_per_Hz",
            "displacement_psd_m2_per_Hz",
            "accumulated_charge_C",
            "charge_check",
            "noise_check",
            "overall_compliant",
            "findings",
        ]:
            self.assertIn(key, result)

    def test_charge_rate_computed_correctly(self):
        p = self._base_params()
        result = assess_gwd_radiation_noise(p)
        expected_rate = 100.0 * 4.0 * 1.0
        self.assertAlmostEqual(result["charge_rate_per_s"], expected_rate, places=10)

    def test_total_force_psd_is_sum(self):
        result = assess_gwd_radiation_noise(self._base_params())
        expected_total = (
            result["force_psd_charge_N2_per_Hz"] + result["force_psd_recoil_N2_per_Hz"]
        )
        self.assertAlmostEqual(
            result["total_force_psd_N2_per_Hz"] / expected_total, 1.0, places=12
        )

    def test_both_exceedances_produce_two_findings(self):
        p = self._base_params()
        p["max_allowable_charge_C"] = 1e-20
        p["noise_budget_m2_per_Hz"] = 1e-40
        result = assess_gwd_radiation_noise(p)
        self.assertFalse(result["overall_compliant"])
        self.assertEqual(len(result["findings"]), 2)


if __name__ == "__main__":
    unittest.main()
