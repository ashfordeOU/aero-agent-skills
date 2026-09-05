#!/usr/bin/env python3
"""Gate 3 contract test: spacecraft Doppler shift on a ground link.

Exercises scripts/doppler_shift_logic.py (stdlib unittest, offline).
Contract: circular-orbit circular velocity, line-of-sight range rate
from altitude and ground elevation angle, received frequency and offset
on a downlink carrier, worst-case (horizon) Doppler, and the slant
range and Doppler rate at acquisition; non-physical inputs raise
ValueError.

Anchors (prep-verified, h = 600 km, f_tx = 2.25 GHz, elev = 30 deg):
- circular_velocity = 7561.73 m/s (within 1 m/s)
- range_rate = -6548.65 m/s (within 1 m/s); overhead (90 deg) = 0
- received frequency = 2250049148.9 Hz, delta_f = +49148.9 Hz
  (within 50 Hz of the +49.15 kHz anchor); delta_f zero overhead
- max_doppler at the horizon = 56752.3 Hz (within 100 Hz) and equal to
  the shift at elevation 0
- slant range = 1200.0 km (within 1 km); doppler_rate = 89.4 Hz/s
  (within 2 Hz/s)
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import doppler_shift_logic as dsl  # noqa: E402

H = 600.0e3     # reference altitude, m
F = 2.25e9      # reference S-band carrier, Hz
V_600 = 7561.73      # prep anchor, m/s
RR_30 = -6548.65     # prep anchor, m/s
DELTA_30 = 49148.9   # prep anchor, Hz
MAXD = 56752.3       # prep anchor, Hz


class CircularVelocityTest(unittest.TestCase):
    def test_circular_velocity_600km_anchor(self):
        self.assertAlmostEqual(dsl.circular_velocity(H), V_600, delta=1.0)

    def test_circular_velocity_matches_kepler_formula(self):
        self.assertAlmostEqual(
            dsl.circular_velocity(H),
            math.sqrt(dsl.MU / (dsl.R_EARTH + H)), places=6)
        v0 = dsl.circular_velocity(0.0)
        self.assertGreater(v0, 7500.0)
        self.assertLess(v0, 8000.0)

    def test_circular_velocity_decreases_with_altitude(self):
        self.assertGreater(dsl.circular_velocity(200.0e3),
                           dsl.circular_velocity(H))
        self.assertLess(dsl.circular_velocity(1000.0e3),
                        dsl.circular_velocity(H))

    def test_circular_velocity_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            dsl.circular_velocity(-1.0)


class RangeRateTest(unittest.TestCase):
    def test_range_rate_30deg_anchor(self):
        self.assertAlmostEqual(dsl.range_rate(H, 30.0), RR_30, delta=1.0)

    def test_range_rate_negative_while_closing(self):
        self.assertLess(dsl.range_rate(H, 30.0), 0.0)

    def test_range_rate_overhead_zero(self):
        self.assertAlmostEqual(dsl.range_rate(H, 90.0), 0.0, delta=1e-6)

    def test_range_rate_horizon_equals_minus_circular_speed(self):
        v = dsl.circular_velocity(H)
        self.assertAlmostEqual(dsl.range_rate(H, 0.0), -v, places=6)

    def test_range_rate_magnitude_grows_toward_horizon(self):
        self.assertGreater(abs(dsl.range_rate(H, 10.0)),
                           abs(dsl.range_rate(H, 45.0)))

    def test_range_rate_non_physical_inputs_raise(self):
        with self.assertRaises(ValueError):
            dsl.range_rate(-1.0, 30.0)
        with self.assertRaises(ValueError):
            dsl.range_rate(H, -5.0)
        with self.assertRaises(ValueError):
            dsl.range_rate(H, 91.0)


class DopplerShiftTest(unittest.TestCase):
    def test_doppler_shift_received_freq_anchor(self):
        ds = dsl.doppler_shift(F, H, 30.0)
        self.assertAlmostEqual(ds["received_freq"], 2250049148.9, delta=50.0)

    def test_doppler_shift_delta_f_anchor(self):
        ds = dsl.doppler_shift(F, H, 30.0)
        self.assertAlmostEqual(ds["delta_f"], DELTA_30, delta=50.0)
        self.assertAlmostEqual(ds["delta_f"], 49150.0, delta=50.0)

    def test_doppler_shift_positive_while_closing(self):
        self.assertGreater(dsl.doppler_shift(F, H, 30.0)["delta_f"], 0.0)

    def test_doppler_shift_overhead_zero(self):
        ds = dsl.doppler_shift(F, H, 90.0)
        self.assertAlmostEqual(ds["delta_f"], 0.0, delta=1e-3)
        self.assertAlmostEqual(ds["received_freq"], F, delta=1e-3)

    def test_doppler_shift_horizon_equals_max_doppler(self):
        horizon = dsl.doppler_shift(F, H, 0.0)["delta_f"]
        self.assertAlmostEqual(horizon, dsl.max_doppler(F, H), delta=0.5)

    def test_doppler_shift_received_freq_rises_approaching(self):
        self.assertGreater(dsl.doppler_shift(F, H, 30.0)["received_freq"], F)

    def test_doppler_shift_non_positive_carrier_raises(self):
        with self.assertRaises(ValueError):
            dsl.doppler_shift(0.0, H, 30.0)
        with self.assertRaises(ValueError):
            dsl.doppler_shift(-2.25e9, H, 30.0)

    def test_doppler_shift_dict_contract(self):
        ds = dsl.doppler_shift(F, H, 30.0)
        self.assertEqual(list(ds), ["range_rate", "received_freq", "delta_f"])
        self.assertEqual(ds["range_rate"], dsl.range_rate(H, 30.0))


class MaxDopplerTest(unittest.TestCase):
    def test_max_doppler_anchor(self):
        self.assertAlmostEqual(dsl.max_doppler(F, H), MAXD, delta=100.0)

    def test_max_doppler_matches_v_over_c_scaling(self):
        v = dsl.circular_velocity(H)
        self.assertAlmostEqual(dsl.max_doppler(F, H), F * v / dsl.C, places=3)

    def test_max_doppler_decreases_with_altitude(self):
        self.assertLess(dsl.max_doppler(F, 1000.0e3),
                        dsl.max_doppler(F, H))

    def test_max_doppler_scales_linearly_with_carrier(self):
        self.assertAlmostEqual(dsl.max_doppler(2.0 * F, H),
                               2.0 * dsl.max_doppler(F, H), places=3)

    def test_max_doppler_non_physical_inputs_raise(self):
        with self.assertRaises(ValueError):
            dsl.max_doppler(-1.0, H)
        with self.assertRaises(ValueError):
            dsl.max_doppler(F, -100.0)


class SlantRangeAndRateTest(unittest.TestCase):
    def test_slant_range_anchor(self):
        ss = dsl.slant_range_and_rate(H, 30.0)
        self.assertAlmostEqual(ss["rho"], 1200.0e3, delta=1000.0)

    def test_doppler_rate_anchor_and_sign(self):
        ss = dsl.slant_range_and_rate(H, 30.0)
        self.assertAlmostEqual(ss["doppler_rate"], 89.4, delta=2.0)
        self.assertGreater(ss["doppler_rate"], 0.0)

    def test_doppler_rate_scales_with_carrier(self):
        base = dsl.slant_range_and_rate(H, 30.0, f_tx=F)["doppler_rate"]
        dbl = dsl.slant_range_and_rate(H, 30.0, f_tx=2.0 * F)["doppler_rate"]
        self.assertAlmostEqual(dbl, 2.0 * base, places=3)

    def test_slant_range_rho_dot_matches_range_rate(self):
        ss = dsl.slant_range_and_rate(H, 30.0)
        self.assertEqual(ss["rho_dot"], dsl.range_rate(H, 30.0))

    def test_slant_range_overhead_equals_altitude(self):
        ss = dsl.slant_range_and_rate(H, 90.0)
        self.assertAlmostEqual(ss["rho"], H, delta=1.0)
        self.assertAlmostEqual(ss["x"], 0.0, delta=1.0)

    def test_slant_range_geometry_and_doppler_rate_formula(self):
        ss = dsl.slant_range_and_rate(H, 30.0)
        self.assertAlmostEqual(
            ss["rho"], math.sqrt(H * H + ss["x"] * ss["x"]), places=3)
        v = dsl.circular_velocity(H)
        rho_dot_dot = v * v * H * H / (ss["rho"] ** 3)
        self.assertAlmostEqual(
            ss["doppler_rate"], dsl.F_TX_REF / dsl.C * abs(rho_dot_dot),
            places=3)

    def test_slant_range_horizon_raises_valueerror(self):
        with self.assertRaises(ValueError):
            dsl.slant_range_and_rate(H, 0.0)

    def test_slant_range_non_physical_inputs_raise(self):
        with self.assertRaises(ValueError):
            dsl.slant_range_and_rate(-1.0, 30.0)
        with self.assertRaises(ValueError):
            dsl.slant_range_and_rate(H, 91.0)
        with self.assertRaises(ValueError):
            dsl.slant_range_and_rate(H, 30.0, f_tx=-1.0)

    def test_slant_range_dict_keys_exact(self):
        ss = dsl.slant_range_and_rate(H, 30.0)
        self.assertEqual(list(ss), ["x", "rho", "rho_dot", "doppler_rate"])


class DeterminismTest(unittest.TestCase):
    def test_deterministic_repeated_calls(self):
        self.assertEqual(dsl.doppler_shift(F, H, 30.0),
                         dsl.doppler_shift(F, H, 30.0))
        self.assertEqual(dsl.slant_range_and_rate(H, 30.0),
                         dsl.slant_range_and_rate(H, 30.0))

    def test_module_constants_physical_values(self):
        self.assertEqual(dsl.R_EARTH, 6371.0e3)
        self.assertEqual(dsl.MU, 3.986004418e14)
        self.assertEqual(dsl.C, 299792458.0)


if __name__ == "__main__":
    unittest.main()
