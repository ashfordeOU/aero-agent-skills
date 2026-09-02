#!/usr/bin/env python3
"""Gate 3 contract test: landing distance determination.

Exercises scripts/landing_distance_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - approach speed
Vref from the stall speed with the 1.23 factor, airborne flare
segment, braking ground roll, combined demonstrated total,
certification field length with the 1.67 factor, and the runway fits
verdict; invalid inputs raise ValueError.

Analytic checks (hand computed):
- Vref = 1.23 * 50 = 61.5 m/s; factor 1.3 gives 65.0 m/s.
- s_air = 61.5 * 5 = 307.5 m; default flare time 5 s gives the same.
- a_brake = 0.45 * 9.80665 = 4.4129925 m/s^2.
- s_ground = 61.5^2 / (2 * 4.4129925) = 3782.25 / 8.825985
  = 428.536 m (3 dp); with a_brake = 4.5 m/s^2 exactly 420.25 m.
- total with Vref = 60, t_air = 6, a_brake = 4.5: 360 + 400 = 760 m.
- certified = 1.67 * 760 = 1269.2 m; factor 1.5 gives 1140.0 m.
- runway verdicts: margin 230.8 (fits), 0.0 (fits), -69.2 (too short).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import landing_distance_logic as ldl  # noqa: E402


class ApproachSpeedTest(unittest.TestCase):
    def test_analytic_check_default_factor(self):
        # 1.23 * 50 = 61.5 m/s
        self.assertAlmostEqual(ldl.approach_speed(50), 61.5, places=6)

    def test_analytic_check_custom_factor(self):
        # 1.3 * 50 = 65.0 m/s
        self.assertAlmostEqual(ldl.approach_speed(50, 1.3), 65.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ldl.approach_speed(0)
        with self.assertRaises(ValueError):
            ldl.approach_speed(-50)
        with self.assertRaises(ValueError):
            ldl.approach_speed(50, 0)
        with self.assertRaises(ValueError):
            ldl.approach_speed(50, -1.23)


class AirborneDistanceTest(unittest.TestCase):
    def test_analytic_check(self):
        # 61.5 * 5 = 307.5 m
        self.assertAlmostEqual(ldl.airborne_distance(61.5, 5), 307.5, places=6)

    def test_default_flare_time(self):
        # default t_air = 5 s gives the same 307.5 m
        self.assertAlmostEqual(ldl.airborne_distance(61.5), 307.5, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ldl.airborne_distance(0, 5)
        with self.assertRaises(ValueError):
            ldl.airborne_distance(-61.5, 5)
        with self.assertRaises(ValueError):
            ldl.airborne_distance(61.5, -5)


class GroundRollTest(unittest.TestCase):
    def test_analytic_check_clean(self):
        # 61.5^2 / (2 * 4.5) = 3782.25 / 9 = 420.25 m
        self.assertAlmostEqual(ldl.ground_roll(61.5, 4.5), 420.25, places=6)

    def test_analytic_check_friction_coefficient(self):
        # a_brake = 0.45 * 9.80665 = 4.4129925; 3782.25 / 8.825985 = 428.536 m
        a_brake = ldl.brake_deceleration(0.45)
        self.assertAlmostEqual(ldl.ground_roll(61.5, a_brake), 428.536, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ldl.ground_roll(0, 4.4)
        with self.assertRaises(ValueError):
            ldl.ground_roll(-61.5, 4.4)
        with self.assertRaises(ValueError):
            ldl.ground_roll(61.5, 0)
        with self.assertRaises(ValueError):
            ldl.ground_roll(61.5, -4.4)


class BrakeDecelerationTest(unittest.TestCase):
    def test_friction_coefficient(self):
        self.assertAlmostEqual(ldl.brake_deceleration(0.45), 0.45 * 9.80665, places=6)

    def test_custom_g(self):
        self.assertAlmostEqual(ldl.brake_deceleration(0.45, 9.81), 4.4145, places=4)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ldl.brake_deceleration(0)
        with self.assertRaises(ValueError):
            ldl.brake_deceleration(-0.45)


class TotalLandingDistanceTest(unittest.TestCase):
    def test_analytic_check(self):
        # airborne 60 * 6 = 360 m, ground roll 3600 / 9 = 400 m, total 760 m
        d = ldl.total_landing_distance(60, 6, 4.5)
        self.assertAlmostEqual(d["airborne_m"], 360.0, places=6)
        self.assertAlmostEqual(d["ground_roll_m"], 400.0, places=6)
        self.assertAlmostEqual(d["total_m"], 760.0, places=6)

    def test_analytic_check_far_example(self):
        # Vref = 61.5, s_air = 307.5, s_ground = 428.536, total = 736.036
        d = ldl.total_landing_distance(61.5, 5, ldl.brake_deceleration(0.45))
        self.assertAlmostEqual(d["airborne_m"], 307.5, places=3)
        self.assertAlmostEqual(d["ground_roll_m"], 428.536, places=3)
        self.assertAlmostEqual(d["total_m"], 736.036, places=3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ldl.total_landing_distance(61.5, 5, 0)
        with self.assertRaises(ValueError):
            ldl.total_landing_distance(61.5, -5, 4.4)


class CertifiedFieldLengthTest(unittest.TestCase):
    def test_analytic_check_default_factor(self):
        # 1.67 * 760 = 1269.2 m
        c = ldl.certified_field_length(760)
        self.assertAlmostEqual(c["certified_m"], 1269.2, places=6)
        self.assertAlmostEqual(c["factor"], 1.67, places=6)

    def test_analytic_check_custom_factor(self):
        # 1.5 * 760 = 1140.0 m
        c = ldl.certified_field_length(760, 1.5)
        self.assertAlmostEqual(c["certified_m"], 1140.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ldl.certified_field_length(-760)
        with self.assertRaises(ValueError):
            ldl.certified_field_length(760, 0)


class RunwayVerdictTest(unittest.TestCase):
    def test_fits(self):
        rv = ldl.runway_verdict(1269.2, 1500)
        self.assertEqual(rv["verdict"], "fits")
        self.assertAlmostEqual(rv["margin_m"], 230.8, places=6)

    def test_exact_fit(self):
        rv = ldl.runway_verdict(1269.2, 1269.2)
        self.assertEqual(rv["verdict"], "fits")
        self.assertAlmostEqual(rv["margin_m"], 0.0, places=6)

    def test_too_short(self):
        rv = ldl.runway_verdict(1269.2, 1200)
        self.assertEqual(rv["verdict"], "too short")
        self.assertAlmostEqual(rv["margin_m"], -69.2, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
