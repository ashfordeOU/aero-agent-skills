"""Offline contract test for antenna_aperture_sizing_logic (stdlib unittest).

Deterministic, no network, no RNG. Run from the repo root:

    python3 skills/space-systems/subsystems/antenna-aperture-sizing/scripts/test_antenna_aperture_sizing.py

Covers the wave-32 sizing contract: wavelength and aperture gain, aperture
from a required gain, the required-gain assembly terms, half-power beamwidth,
the pointing accuracy budget, gain-over-temperature, the end-to-end sizing
convenience dict, round trips and identities, ValueError rejection of
non-physical inputs, and run-to-run determinism.
"""

import math
import unittest

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from antenna_aperture_sizing_logic import (
    K_BOLTZ,
    wavelength,
    gain_from_aperture,
    aperture_from_gain,
    required_gain_db,
    half_power_beamwidth,
    pointing_budget,
    gain_over_temperature,
    antenna_sizing,
)

F_HZ = 2.2e9            # S-band downlink, worked example
REQ_DB = 33.5           # required gain, dBi
ETA = 0.6
T_K = 150.0

# Real module outputs for the worked example (spec magnitude bounds in parens)
LAMBDA_M = 0.1362692990909091   # about 0.13627 m
D_M = 2.6495524687863776        # 2.5-2.8 m (about 2.650)
BEAM_DEG = 3.6001743874628342   # 3.3-3.9 deg (about 3.60)
GT_DBK = 11.739087409443187     # 11-13 dB/K (about 11.74)


class TestWavelength(unittest.TestCase):
    def test_wavelength_worked_example(self):
        lam = wavelength(F_HZ)
        self.assertAlmostEqual(lam, LAMBDA_M, places=8)
        self.assertAlmostEqual(lam, 0.13627, delta=0.001)

    def test_wavelength_value_error_nonpositive_frequency(self):
        for bad in (0.0, -1.0, -2.2e9):
            with self.assertRaises(ValueError):
                wavelength(bad)


class TestGainFromAperture(unittest.TestCase):
    def test_gain_from_aperture_worked_example(self):
        gain_lin, gain_db = gain_from_aperture(D_M, LAMBDA_M, ETA)
        self.assertAlmostEqual(gain_db, REQ_DB, delta=0.01)
        self.assertAlmostEqual(gain_db, 33.500000, places=5)

    def test_gain_from_aperture_higher_eta_higher_gain(self):
        _, g_low = gain_from_aperture(D_M, LAMBDA_M, 0.55)
        _, g_high = gain_from_aperture(D_M, LAMBDA_M, 0.65)
        self.assertGreater(g_high, g_low)

    def test_gain_from_aperture_value_error_diameter(self):
        for bad in (0.0, -2.5):
            with self.assertRaises(ValueError):
                gain_from_aperture(bad, LAMBDA_M)

    def test_gain_from_aperture_value_error_wavelength(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                gain_from_aperture(2.0, bad)

    def test_gain_from_aperture_value_error_eta(self):
        for bad in (0.0, -0.5, 1.5, 2.0):
            with self.assertRaises(ValueError):
                gain_from_aperture(2.0, LAMBDA_M, bad)


class TestApertureFromGain(unittest.TestCase):
    def test_aperture_from_gain_worked_example(self):
        d = aperture_from_gain(REQ_DB, LAMBDA_M, ETA)
        self.assertGreaterEqual(d, 2.5)
        self.assertLessEqual(d, 2.8)
        self.assertAlmostEqual(d, D_M, places=6)
        self.assertAlmostEqual(d, 2.650, delta=0.01)

    def test_aperture_from_gain_requires_more_gain_more_diameter(self):
        d_low = aperture_from_gain(30.0, LAMBDA_M, ETA)
        d_high = aperture_from_gain(36.0, LAMBDA_M, ETA)
        self.assertGreater(d_high, d_low)

    def test_aperture_from_gain_value_error_gain_nonpositive(self):
        for bad in (0.0, -3.0):
            with self.assertRaises(ValueError):
                aperture_from_gain(bad, LAMBDA_M)

    def test_aperture_from_gain_value_error_eta(self):
        for bad in (0.0, 1.01):
            with self.assertRaises(ValueError):
                aperture_from_gain(REQ_DB, LAMBDA_M, bad)

    def test_round_trip_aperture_gain(self):
        d = aperture_from_gain(REQ_DB, LAMBDA_M, ETA)
        d_back = aperture_from_gain(gain_from_aperture(d, LAMBDA_M, ETA)[1],
                                    LAMBDA_M, ETA)
        self.assertAlmostEqual(d_back / d, 1.0, places=9)


class TestRequiredGain(unittest.TestCase):
    def test_required_gain_assembly_worked_values(self):
        g = required_gain_db(3.0, 200.0, 1.0, 1e6, T_K, 10.0)
        expected = (3.0 + 200.0 + 1.0
                    + 10.0 * math.log10(K_BOLTZ * T_K * 1e6) - 10.0)
        self.assertAlmostEqual(g, expected, places=9)
        self.assertAlmostEqual(g, 47.161745, delta=0.001)

    def test_required_gain_increases_with_data_rate(self):
        g1 = required_gain_db(3.0, 200.0, 1.0, 1e6, T_K, 10.0)
        g2 = required_gain_db(3.0, 200.0, 1.0, 1e7, T_K, 10.0)
        self.assertAlmostEqual(g2 - g1, 10.0, places=9)

    def test_required_gain_increases_with_noise_temp(self):
        g1 = required_gain_db(3.0, 200.0, 1.0, 1e6, 150.0, 10.0)
        g2 = required_gain_db(3.0, 200.0, 1.0, 1e6, 1500.0, 10.0)
        self.assertAlmostEqual(g2 - g1, 10.0, places=9)

    def test_required_gain_value_error_data_rate(self):
        for bad in (0.0, -100.0):
            with self.assertRaises(ValueError):
                required_gain_db(3.0, 200.0, 1.0, bad, T_K, 10.0)

    def test_required_gain_value_error_noise_temp(self):
        for bad in (0.0, -50.0):
            with self.assertRaises(ValueError):
                required_gain_db(3.0, 200.0, 1.0, 1e6, bad, 10.0)


class TestBeamwidth(unittest.TestCase):
    def test_beamwidth_worked_example(self):
        bw = half_power_beamwidth(D_M, LAMBDA_M)
        self.assertGreaterEqual(bw, 3.3)
        self.assertLessEqual(bw, 3.9)
        self.assertAlmostEqual(bw, BEAM_DEG, places=6)
        self.assertAlmostEqual(bw, 3.60, delta=0.01)

    def test_beamwidth_decreases_with_diameter(self):
        small = half_power_beamwidth(1.0, LAMBDA_M)
        large = half_power_beamwidth(5.0, LAMBDA_M)
        self.assertGreater(small, large)

    def test_beamwidth_value_error(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                half_power_beamwidth(bad, LAMBDA_M)
        with self.assertRaises(ValueError):
            half_power_beamwidth(2.0, 0.0)


class TestPointingBudget(unittest.TestCase):
    def test_pointing_budget_worked_example(self):
        pb = pointing_budget(BEAM_DEG)
        self.assertAlmostEqual(pb["allowed_error_deg"], 0.360017, places=5)
        self.assertAlmostEqual(pb["allowed_error_deg"], 0.360, delta=0.001)
        self.assertAlmostEqual(pb["pointing_loss_db"], 0.12, places=9)

    def test_pointing_budget_fraction_zero_zero_loss(self):
        pb = pointing_budget(BEAM_DEG, 0.0)
        self.assertEqual(pb["allowed_error_deg"], 0.0)
        self.assertEqual(pb["pointing_loss_db"], 0.0)

    def test_pointing_budget_value_error_theta(self):
        with self.assertRaises(ValueError):
            pointing_budget(0.0)
        with self.assertRaises(ValueError):
            pointing_budget(-3.0)

    def test_pointing_budget_value_error_negative_fraction(self):
        with self.assertRaises(ValueError):
            pointing_budget(BEAM_DEG, -0.1)


class TestGainOverTemperature(unittest.TestCase):
    def test_gain_over_temperature_worked_example(self):
        gt = gain_over_temperature(REQ_DB, T_K)
        self.assertGreaterEqual(gt, 11.0)
        self.assertLessEqual(gt, 13.0)
        self.assertAlmostEqual(gt, GT_DBK, places=9)
        self.assertAlmostEqual(gt, 11.74, delta=0.01)

    def test_gain_over_temperature_doubling_noise(self):
        gt_low = gain_over_temperature(REQ_DB, T_K)
        gt_high = gain_over_temperature(REQ_DB, 2.0 * T_K)
        self.assertAlmostEqual(gt_high - gt_low, -10.0 * math.log10(2.0),
                               places=9)
        self.assertAlmostEqual(gt_high - gt_low, -3.0103, places=3)

    def test_gain_over_temperature_value_error(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                gain_over_temperature(REQ_DB, bad)


class TestAntennaSizing(unittest.TestCase):
    EXPECTED_KEYS = {"wavelength_m", "diameter_m", "achieved_gain_db",
                     "beamwidth_deg", "pointing_allowed_deg",
                     "pointing_loss_db", "gain_over_temperature_dbK",
                     "gain_error_db"}

    def test_sizing_worked_example_values(self):
        sz = antenna_sizing(REQ_DB, F_HZ, ETA, T_K)
        self.assertAlmostEqual(sz["wavelength_m"], LAMBDA_M, places=9)
        self.assertGreaterEqual(sz["diameter_m"], 2.5)
        self.assertLessEqual(sz["diameter_m"], 2.8)
        self.assertAlmostEqual(sz["achieved_gain_db"], REQ_DB, delta=0.01)
        self.assertGreaterEqual(sz["beamwidth_deg"], 3.3)
        self.assertLessEqual(sz["beamwidth_deg"], 3.9)
        self.assertAlmostEqual(sz["pointing_allowed_deg"], 0.360, delta=0.001)
        self.assertAlmostEqual(sz["pointing_loss_db"], 0.12, places=9)
        self.assertAlmostEqual(sz["gain_over_temperature_dbK"], GT_DBK,
                               places=6)

    def test_sizing_dict_exact_keys(self):
        sz = antenna_sizing(REQ_DB, F_HZ, ETA, T_K)
        self.assertEqual(set(sz.keys()), self.EXPECTED_KEYS)

    def test_sizing_gain_error_near_zero(self):
        sz = antenna_sizing(REQ_DB, F_HZ, ETA, T_K)
        self.assertLessEqual(abs(sz["gain_error_db"]), 1e-6)

    def test_sizing_noise_temp_none_omits_gt(self):
        sz = antenna_sizing(REQ_DB, F_HZ, ETA)
        self.assertIsNone(sz["gain_over_temperature_dbK"])
        self.assertEqual(set(sz.keys()), self.EXPECTED_KEYS)

    def test_sizing_value_error_frequency(self):
        with self.assertRaises(ValueError):
            antenna_sizing(REQ_DB, 0.0)
        with self.assertRaises(ValueError):
            antenna_sizing(REQ_DB, -2.2e9)

    def test_sizing_value_error_gain_and_eta(self):
        with self.assertRaises(ValueError):
            antenna_sizing(0.0, F_HZ)
        with self.assertRaises(ValueError):
            antenna_sizing(REQ_DB, F_HZ, 0.0)

    def test_sizing_value_error_noise_temp(self):
        with self.assertRaises(ValueError):
            antenna_sizing(REQ_DB, F_HZ, ETA, 0.0)

    def test_sizing_determinism_identical_runs(self):
        a = antenna_sizing(REQ_DB, F_HZ, ETA, T_K)
        b = antenna_sizing(REQ_DB, F_HZ, ETA, T_K)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
