#!/usr/bin/env python3
"""Gate 3 contract test: glide flight test sink rate and L/D logic.

Exercises scripts/glide_flight_test_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - sink rate from
altitude loss and time, descent angle from L/D, L/D from airspeed and
sink rate, sink rate from airspeed and angle, weight and density
corrections, residual idle thrust correction, best glide speed, and
glide ratio from distance; invalid inputs raise ValueError. Analytic
check: 500 m lost in 100 s gives v_sink = 5.0 m/s; L/D = 10 gives
gamma = 5.7106 deg and v_sink = 4.975 m/s at V = 50 m/s; weight
10000 to 9000 gives v_sink 4.743 m/s; T/W = 0.02 raises L/D 10 to
12.5; best glide speed from (50, 12.5, 15) is 54.772 m/s.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import glide_flight_test_logic as gft  # noqa: E402


class SinkRateTest(unittest.TestCase):
    def test_analytic_check(self):
        # 500 m lost over 100 s = 5.0 m/s
        self.assertAlmostEqual(gft.sink_rate(500, 100), 5.0, places=3)

    def test_level_flight_is_zero(self):
        self.assertAlmostEqual(gft.sink_rate(0, 100), 0.0, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gft.sink_rate(500, 0)
        with self.assertRaises(ValueError):
            gft.sink_rate(500, -100)
        with self.assertRaises(ValueError):
            gft.sink_rate(-500, 100)


class DescentAngleFromLDTest(unittest.TestCase):
    def test_analytic_check(self):
        # atan(1/10) = 0.0996687 rad = 5.7106 deg
        self.assertAlmostEqual(gft.descent_angle_from_ld(10), 5.7106, places=3)

    def test_ld_one_is_45_deg(self):
        self.assertAlmostEqual(gft.descent_angle_from_ld(1), 45.0, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gft.descent_angle_from_ld(0)
        with self.assertRaises(ValueError):
            gft.descent_angle_from_ld(-10)


class LDFromSinkRateTest(unittest.TestCase):
    def test_analytic_check(self):
        self.assertAlmostEqual(gft.ld_from_sink_rate(50, 5), 10.0, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gft.ld_from_sink_rate(0, 5)
        with self.assertRaises(ValueError):
            gft.ld_from_sink_rate(-50, 5)
        with self.assertRaises(ValueError):
            gft.ld_from_sink_rate(50, 0)
        with self.assertRaises(ValueError):
            gft.ld_from_sink_rate(50, -5)


class SinkRateFromAirspeedTest(unittest.TestCase):
    def test_analytic_check(self):
        # 50 * sin(atan(1/10)) = 50 * 0.0995037 = 4.975 m/s
        gamma = gft.descent_angle_from_ld(10)
        self.assertAlmostEqual(gft.sink_rate_from_airspeed(50, gamma), 4.975, places=3)

    def test_matches_direct_sine(self):
        self.assertAlmostEqual(
            gft.sink_rate_from_airspeed(50, 10), 50 * math.sin(math.radians(10)), places=6
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gft.sink_rate_from_airspeed(0, 5)
        with self.assertRaises(ValueError):
            gft.sink_rate_from_airspeed(-50, 5)


class WeightCorrectedSinkRateTest(unittest.TestCase):
    def test_analytic_check(self):
        # 5.0 * sqrt(9000/10000) = 5.0 * 0.948683 = 4.743 m/s
        self.assertAlmostEqual(gft.weight_corrected_sink_rate(5.0, 10000, 9000), 4.743, places=3)

    def test_same_weight_unchanged(self):
        self.assertAlmostEqual(gft.weight_corrected_sink_rate(5.0, 10000, 10000), 5.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gft.weight_corrected_sink_rate(0, 10000, 9000)
        with self.assertRaises(ValueError):
            gft.weight_corrected_sink_rate(5.0, 0, 9000)
        with self.assertRaises(ValueError):
            gft.weight_corrected_sink_rate(5.0, 10000, 0)
        with self.assertRaises(ValueError):
            gft.weight_corrected_sink_rate(5.0, -10000, 9000)


class DensityCorrectedAirspeedTest(unittest.TestCase):
    def test_analytic_check(self):
        # 50 * sqrt(1.0/0.9) = 50 * 1.054093 = 52.705 m/s
        self.assertAlmostEqual(gft.density_corrected_airspeed(50, 1.0, 0.9), 52.705, places=3)

    def test_same_density_unchanged(self):
        self.assertAlmostEqual(gft.density_corrected_airspeed(50, 1.0, 1.0), 50.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gft.density_corrected_airspeed(0, 1.0, 0.9)
        with self.assertRaises(ValueError):
            gft.density_corrected_airspeed(50, 0, 0.9)
        with self.assertRaises(ValueError):
            gft.density_corrected_airspeed(50, 1.0, 0)


class IdleThrustCorrectedLDTest(unittest.TestCase):
    def test_analytic_check(self):
        # 1 / (1/10 - 0.02) = 1 / 0.08 = 12.5
        self.assertAlmostEqual(gft.idle_thrust_corrected_ld(10, 0.02), 12.5, places=3)

    def test_zero_thrust_unchanged(self):
        self.assertAlmostEqual(gft.idle_thrust_corrected_ld(10, 0.0), 10.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gft.idle_thrust_corrected_ld(0, 0.02)
        with self.assertRaises(ValueError):
            gft.idle_thrust_corrected_ld(-10, 0.02)
        with self.assertRaises(ValueError):
            gft.idle_thrust_corrected_ld(10, -0.01)

    def test_thrust_exceeding_drag_raises(self):
        # 1/10 - 0.11 < 0: residual thrust exceeds the measured drag
        with self.assertRaises(ValueError):
            gft.idle_thrust_corrected_ld(10, 0.11)


class BestGlideSpeedTest(unittest.TestCase):
    def test_analytic_check(self):
        # 50 * sqrt(15/12.5) = 50 * 1.095445 = 54.772 m/s
        self.assertAlmostEqual(gft.best_glide_speed(50, 12.5, 15), 54.772, places=3)

    def test_no_gain_unchanged(self):
        self.assertAlmostEqual(gft.best_glide_speed(50, 10, 10), 50.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gft.best_glide_speed(0, 10, 12.5)
        with self.assertRaises(ValueError):
            gft.best_glide_speed(50, 0, 12.5)
        with self.assertRaises(ValueError):
            gft.best_glide_speed(50, 10, 0)


class GlideRatioFromDistanceTest(unittest.TestCase):
    def test_analytic_check(self):
        self.assertAlmostEqual(gft.glide_ratio_from_distance(10000, 1000), 10.0, places=3)

    def test_zero_horizontal_is_zero(self):
        self.assertAlmostEqual(gft.glide_ratio_from_distance(0, 1000), 0.0, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gft.glide_ratio_from_distance(10000, 0)
        with self.assertRaises(ValueError):
            gft.glide_ratio_from_distance(10000, -1000)
        with self.assertRaises(ValueError):
            gft.glide_ratio_from_distance(-10000, 1000)


class GlideTestEndToEndTest(unittest.TestCase):
    def test_full_measurement_chain(self):
        # 500 m lost in 100 s, V_tas 50 m/s, weight 10000 to 9000,
        # T/W 0.02, then best glide speed from (50, 12.5, 15).
        v_sink = gft.sink_rate(500, 100)
        self.assertAlmostEqual(v_sink, 5.0, places=3)
        ld = gft.ld_from_sink_rate(50, v_sink)
        self.assertAlmostEqual(ld, 10.0, places=3)
        corrected = gft.weight_corrected_sink_rate(v_sink, 10000, 9000)
        self.assertAlmostEqual(corrected, 4.743, places=3)
        ld_true = gft.idle_thrust_corrected_ld(ld, 0.02)
        self.assertAlmostEqual(ld_true, 12.5, places=3)
        v_best = gft.best_glide_speed(50, ld_true, 15)
        self.assertAlmostEqual(v_best, 54.772, places=3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
