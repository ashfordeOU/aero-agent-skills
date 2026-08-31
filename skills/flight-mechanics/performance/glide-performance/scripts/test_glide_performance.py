#!/usr/bin/env python3
"""Gate 3 contract test: unpowered glide performance.

Exercises scripts/glide_performance_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - glide ratio
from lift and drag, descent angle from the glide ratio, sink rate
from the airspeed and the descent angle, best glide speed from a
reference condition and the maximum lift to drag ratio, and time
to descend from the altitude loss and the sink rate; invalid
inputs raise ValueError. Units are SI: forces in N, speeds in m/s,
angles in degrees, altitude in m, time in s.

Analytic check (hand-computed): L/D = 15 gives
gamma = atan(1/15) = 3.8140748 deg (3.8141 to 4 places); the sink
rate at 60 m/s is V * sin(gamma) = 60 * sin(atan(1/15)) =
60 / sqrt(226) = 3.9911406 m/s (3.9911 to 4 places); the time to
descend 1000 m at that sink rate is 1000 / 3.9911406 = 250.5549 s
(250.55 to 2 places). Best glide speed: v_ref = 50 m/s at
L/D = 10 with (L/D)_max = 15 gives 50 * sqrt(15/10) =
50 * sqrt(1.5) = 61.2372 m/s.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import glide_performance_logic as gpl  # noqa: E402


class GlideRatioTest(unittest.TestCase):
    def test_analytic_check(self):
        # 15 / 1 = 15.0
        self.assertEqual(gpl.glide_ratio(15, 1), 15.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gpl.glide_ratio(0, 1)
        with self.assertRaises(ValueError):
            gpl.glide_ratio(-15, 1)
        with self.assertRaises(ValueError):
            gpl.glide_ratio(15, 0)
        with self.assertRaises(ValueError):
            gpl.glide_ratio(15, -1)


class DescentAngleTest(unittest.TestCase):
    def test_analytic_check(self):
        # atan(1/15) = 3.8140748 deg
        self.assertAlmostEqual(gpl.descent_angle(15.0), 3.8141, places=4)

    def test_identity_tan_gamma(self):
        # tan(gamma) = 1 / (L/D) exactly, so gamma recovers the
        # lift to drag ratio. The asin small-angle form is only an
        # approximation, so the atan identity is the exact check.
        import math

        gamma_rad = math.radians(gpl.descent_angle(15.0))
        self.assertAlmostEqual(math.tan(gamma_rad), 1.0 / 15.0, places=12)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gpl.descent_angle(0)
        with self.assertRaises(ValueError):
            gpl.descent_angle(-15)


class SinkRateTest(unittest.TestCase):
    def test_analytic_check(self):
        # 60 * sin(atan(1/15)) = 60 / sqrt(226) = 3.9911406 m/s
        self.assertAlmostEqual(
            gpl.sink_rate(60.0, gpl.descent_angle(15.0)), 3.9911, places=4
        )

    def test_units_check(self):
        # Chain: glide ratio 15, angle, then sink rate at 60 m/s.
        self.assertAlmostEqual(
            gpl.sink_rate(60.0, gpl.descent_angle(15.0)),
            60.0 / (226.0 ** 0.5),
            places=6,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gpl.sink_rate(0, 3.8141)
        with self.assertRaises(ValueError):
            gpl.sink_rate(-60, 3.8141)
        with self.assertRaises(ValueError):
            gpl.sink_rate(60, 0)
        with self.assertRaises(ValueError):
            gpl.sink_rate(60, -3.8141)


class BestGlideSpeedTest(unittest.TestCase):
    def test_analytic_check(self):
        # 50 * sqrt(15/10) = 50 * 1.2247449 = 61.2372 m/s
        self.assertAlmostEqual(gpl.best_glide_speed(50.0, 10.0, 15.0), 61.2372, places=4)

    def test_at_max_ratio(self):
        # At (L/D)_max itself the best glide speed equals v_ref.
        self.assertEqual(gpl.best_glide_speed(50.0, 15.0, 15.0), 50.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gpl.best_glide_speed(0, 10.0, 15.0)
        with self.assertRaises(ValueError):
            gpl.best_glide_speed(-50, 10.0, 15.0)
        with self.assertRaises(ValueError):
            gpl.best_glide_speed(50, 0, 15.0)
        with self.assertRaises(ValueError):
            gpl.best_glide_speed(50, -10, 15.0)
        with self.assertRaises(ValueError):
            gpl.best_glide_speed(50, 10.0, 0)
        with self.assertRaises(ValueError):
            gpl.best_glide_speed(50, 10.0, -15.0)


class TimeToDescendTest(unittest.TestCase):
    def test_analytic_check(self):
        # 1000 / 3.9911406 = 250.5549 s
        self.assertAlmostEqual(
            gpl.time_to_descend(1000.0, gpl.sink_rate(60.0, gpl.descent_angle(15.0))),
            250.55,
            places=2,
        )

    def test_units_check(self):
        # 500 m at 5 m/s sink rate is exactly 100 s.
        self.assertEqual(gpl.time_to_descend(500.0, 5.0), 100.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gpl.time_to_descend(0, 3.9911)
        with self.assertRaises(ValueError):
            gpl.time_to_descend(-1000, 3.9911)
        with self.assertRaises(ValueError):
            gpl.time_to_descend(1000, 0)
        with self.assertRaises(ValueError):
            gpl.time_to_descend(1000, -3.9911)


if __name__ == "__main__":
    unittest.main(verbosity=2)
