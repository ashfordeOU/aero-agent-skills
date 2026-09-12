"""
Gate 3 contract tests for e1012-seu-proton.

Run: python3 test_e1012_seu_proton.py
Expected output: OK
Stdlib unittest only.  Deterministic.  Offline.
"""

import math
import sys
import os
import unittest

# Allow running from any working directory.
sys.path.insert(0, os.path.dirname(__file__))

from e1012_seu_proton_logic import (
    FluxBin,
    DeviceParams,
    SEUBudget,
    weibull_sigma,
    seu_rate_one_path,
    seu_rate_combined,
    mcu_rate,
    mission_seu_count,
    check_seu_compliance,
    validate_particle_type,
    validate_flux_bins,
    validate_device_params,
    DIRECT_PATH_EFFICIENCY,
    NUCLEAR_PATH_EFFICIENCY,
)


# ── Shared fixtures ────────────────────────────────────────────────────────────

def _make_params(sigma_sat=1e-12, E_th=10.0, W=20.0, s=1.5,
                 mcu_fraction=0.05):
    return DeviceParams(sigma_sat=sigma_sat, E_th=E_th, W=W, s=s,
                        mcu_fraction=mcu_fraction)


def _make_single_bin(energy=50.0, flux=1e6, dE=1.0):
    return [FluxBin(energy_MeV=energy, flux=flux, dE=dE)]


# ── Weibull cross-section tests ────────────────────────────────────────────────

class TestWeibullSigma(unittest.TestCase):

    def test_below_threshold_returns_zero(self):
        params = _make_params(E_th=10.0)
        self.assertEqual(weibull_sigma(5.0, params), 0.0)

    def test_at_threshold_returns_zero(self):
        params = _make_params(E_th=10.0)
        self.assertEqual(weibull_sigma(10.0, params), 0.0)

    def test_just_above_threshold_positive(self):
        params = _make_params(E_th=10.0, sigma_sat=1e-12)
        result = weibull_sigma(10.001, params)
        self.assertGreater(result, 0.0)

    def test_high_energy_approaches_saturation(self):
        params = _make_params(E_th=10.0, sigma_sat=1e-12, W=20.0, s=1.5)
        result = weibull_sigma(1000.0, params)
        self.assertAlmostEqual(result, 1e-12, places=20)

    def test_monotone_increasing_above_threshold(self):
        params = _make_params(E_th=10.0)
        energies = [15.0, 30.0, 60.0, 120.0, 300.0]
        sigmas = [weibull_sigma(e, params) for e in energies]
        for i in range(len(sigmas) - 1):
            self.assertLess(sigmas[i], sigmas[i + 1])

    def test_shape_exponent_s_effect(self):
        p_sharp = _make_params(E_th=10.0, W=20.0, s=4.0, sigma_sat=1e-12)
        p_soft = _make_params(E_th=10.0, W=20.0, s=0.5, sigma_sat=1e-12)
        # At moderate excess energy, higher s = sharper rise, lower intermediate value
        # Both must be in (0, sigma_sat)
        val_sharp = weibull_sigma(15.0, p_sharp)
        val_soft = weibull_sigma(15.0, p_soft)
        self.assertGreater(val_sharp, 0.0)
        self.assertGreater(val_soft, 0.0)
        self.assertLess(val_sharp, 1e-12)
        self.assertLess(val_soft, 1e-12)


# ── SEU rate integration tests ─────────────────────────────────────────────────

class TestSEURateOnePath(unittest.TestCase):

    def test_all_flux_below_threshold_gives_zero_rate(self):
        params = _make_params(E_th=50.0)
        bins = [FluxBin(10.0, 1e6, 5.0), FluxBin(30.0, 1e6, 5.0)]
        rate = seu_rate_one_path(bins, params, DIRECT_PATH_EFFICIENCY)
        self.assertEqual(rate, 0.0)

    def test_single_bin_above_threshold_positive_rate(self):
        params = _make_params(E_th=10.0, sigma_sat=1e-12, W=20.0, s=1.0)
        bins = _make_single_bin(energy=50.0, flux=1e6, dE=1.0)
        rate = seu_rate_one_path(bins, params, DIRECT_PATH_EFFICIENCY)
        self.assertGreater(rate, 0.0)

    def test_nuclear_path_efficiency_reduces_rate(self):
        params = _make_params(E_th=10.0, sigma_sat=1e-12, W=20.0, s=1.0)
        bins = _make_single_bin(energy=100.0, flux=1e6, dE=1.0)
        rate_direct = seu_rate_one_path(bins, params, DIRECT_PATH_EFFICIENCY)
        rate_nuclear = seu_rate_one_path(bins, params, NUCLEAR_PATH_EFFICIENCY)
        self.assertLess(rate_nuclear, rate_direct)

    def test_rate_scales_linearly_with_flux(self):
        params = _make_params(E_th=10.0, sigma_sat=1e-12, W=20.0, s=1.0)
        bins_x1 = [FluxBin(100.0, 1e5, 1.0)]
        bins_x2 = [FluxBin(100.0, 2e5, 1.0)]
        r1 = seu_rate_one_path(bins_x1, params, 1.0)
        r2 = seu_rate_one_path(bins_x2, params, 1.0)
        self.assertAlmostEqual(r2 / r1, 2.0, places=10)

    def test_empty_spectrum_raises(self):
        params = _make_params()
        with self.assertRaises(ValueError):
            seu_rate_one_path([], params, 1.0)

    def test_invalid_efficiency_raises(self):
        params = _make_params()
        bins = _make_single_bin()
        with self.assertRaises(ValueError):
            seu_rate_one_path(bins, params, 1.5)


# ── Combined rate tests ────────────────────────────────────────────────────────

class TestSEURateCombined(unittest.TestCase):

    def test_combined_rate_equals_sum_of_paths(self):
        params = _make_params(E_th=10.0, sigma_sat=1e-12, W=20.0, s=1.0)
        direct = [FluxBin(100.0, 1e6, 1.0)]
        nuclear = [FluxBin(30.0, 5e5, 2.0)]
        result = seu_rate_combined(direct, nuclear, params)
        expected_total = result["rate_direct"] + result["rate_nuclear"]
        self.assertAlmostEqual(result["rate_total"], expected_total, places=20)

    def test_nuclear_rate_less_than_direct_for_same_spectrum(self):
        params = _make_params(E_th=10.0, sigma_sat=1e-12, W=20.0, s=1.0)
        spectrum = [FluxBin(200.0, 1e6, 1.0)]
        result = seu_rate_combined(spectrum, spectrum, params)
        self.assertLess(result["rate_nuclear"], result["rate_direct"])

    def test_result_keys_present(self):
        params = _make_params()
        s = _make_single_bin(energy=100.0)
        result = seu_rate_combined(s, s, params)
        self.assertIn("rate_direct", result)
        self.assertIn("rate_nuclear", result)
        self.assertIn("rate_total", result)


# ── MCU and mission count tests ────────────────────────────────────────────────

class TestMCURateAndMissionCount(unittest.TestCase):

    def test_mcu_rate_proportional_to_fraction(self):
        total = 1e-8
        self.assertAlmostEqual(mcu_rate(total, 0.10), 1e-9, places=20)

    def test_mcu_rate_zero_fraction_gives_zero(self):
        self.assertEqual(mcu_rate(5e-9, 0.0), 0.0)

    def test_mcu_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            mcu_rate(1e-8, 1.1)

    def test_mission_count_calculation(self):
        rate = 1e-10          # upsets/bit/s
        bits = 1_000_000      # 1 Mbit
        duration = 3.156e7    # ~1 year in seconds
        count = mission_seu_count(rate, bits, duration)
        self.assertAlmostEqual(count, rate * bits * duration, places=5)

    def test_mission_count_zero_duration(self):
        self.assertEqual(mission_seu_count(1e-9, 1_000_000, 0.0), 0.0)

    def test_mission_count_zero_bit_count_raises(self):
        with self.assertRaises(ValueError):
            mission_seu_count(1e-9, 0, 1e7)

    def test_mission_count_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            mission_seu_count(1e-9, 1_000_000, -1.0)


# ── Compliance check tests ─────────────────────────────────────────────────────

class TestCheckSEUCompliance(unittest.TestCase):

    def test_within_budget_returns_compliant(self):
        budget = SEUBudget(max_rate_per_bit_per_s=1e-8,
                           max_mission_count=100.0)
        result = check_seu_compliance(5e-9, 50.0, budget)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_rate_exceedance_flagged(self):
        budget = SEUBudget(max_rate_per_bit_per_s=1e-10)
        result = check_seu_compliance(1e-9, 0.0, budget)
        self.assertFalse(result["rate_pass"])
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["findings"]) > 0)

    def test_count_exceedance_flagged(self):
        budget = SEUBudget(max_mission_count=10.0)
        result = check_seu_compliance(0.0, 50.0, budget)
        self.assertFalse(result["count_pass"])
        self.assertFalse(result["compliant"])

    def test_no_budget_is_open_finding(self):
        budget = SEUBudget()
        result = check_seu_compliance(1e-10, 5.0, budget)
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["findings"]) > 0)

    def test_only_rate_limit_set_count_pass_true(self):
        budget = SEUBudget(max_rate_per_bit_per_s=1e-8)
        result = check_seu_compliance(5e-9, 9999.0, budget)
        self.assertTrue(result["rate_pass"])
        self.assertTrue(result["count_pass"])
        self.assertTrue(result["compliant"])


# ── Validation tests ───────────────────────────────────────────────────────────

class TestValidation(unittest.TestCase):

    def test_particle_type_proton_accepted(self):
        validate_particle_type("proton")  # must not raise

    def test_particle_type_neutron_accepted(self):
        validate_particle_type("neutron")  # must not raise

    def test_particle_type_unknown_raises(self):
        with self.assertRaises(ValueError):
            validate_particle_type("electron")

    def test_flux_bins_negative_energy_raises(self):
        with self.assertRaises(ValueError):
            validate_flux_bins([FluxBin(-1.0, 1e5, 1.0)])

    def test_flux_bins_negative_dE_raises(self):
        with self.assertRaises(ValueError):
            validate_flux_bins([FluxBin(10.0, 1e5, -0.5)])

    def test_flux_bins_negative_flux_raises(self):
        with self.assertRaises(ValueError):
            validate_flux_bins([FluxBin(10.0, -1.0, 1.0)])

    def test_flux_bins_zero_flux_accepted(self):
        validate_flux_bins([FluxBin(10.0, 0.0, 1.0)])  # must not raise

    def test_device_params_zero_sigma_sat_raises(self):
        with self.assertRaises(ValueError):
            validate_device_params(DeviceParams(0.0, 10.0, 20.0, 1.5))

    def test_device_params_valid_passes(self):
        validate_device_params(_make_params())  # must not raise

    def test_device_params_negative_threshold_raises(self):
        with self.assertRaises(ValueError):
            validate_device_params(DeviceParams(1e-12, -1.0, 20.0, 1.5))


if __name__ == "__main__":
    unittest.main()
