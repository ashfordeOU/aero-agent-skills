"""Contract test for gravity-assist-swingby logic (offline, stdlib only).

Run with: python3 scripts/test_gravity_assist_swingby.py
Covers the worked examples from the leaf spec (Earth swing-bys at
3 km/s and 5 km/s excess speed), the Mars close-approach feasibility
case, boundary geometry, ValueError rejection of non-physical inputs,
and the energy-integral round-trip identity.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gravity_assist_swingby_logic import (
    MU_EARTH,
    EARTH_RADIUS_M,
    DEFAULT_MIN_ALT_M,
    periapsis_speed,
    turn_angle_rad,
    dv_gain,
    outgoing_direction_deg,
    feasibility,
    analyze,
)

EARTH_RP_M = 7000e3       # worked-example periapsis radius
MARS_RADIUS_M = 3390e3    # Mars mean radius
MARS_RP_M = 3800e3        # Mars flyby periapsis radius


class TestPeriapsisSpeed(unittest.TestCase):
    def test_earth_3000_worked_example(self):
        vp = periapsis_speed(3000.0, EARTH_RP_M, MU_EARTH)
        self.assertAlmostEqual(vp, 11085.4, delta=0.5)

    def test_earth_5000_worked_example(self):
        vp = periapsis_speed(5000.0, EARTH_RP_M, MU_EARTH)
        self.assertAlmostEqual(vp, 11785.0, delta=0.5)

    def test_default_mu_is_earth(self):
        self.assertEqual(periapsis_speed(3000.0, EARTH_RP_M),
                         periapsis_speed(3000.0, EARTH_RP_M, MU_EARTH))

    def test_zero_excess_speed_parabolic(self):
        vp = periapsis_speed(0.0, EARTH_RP_M, MU_EARTH)
        self.assertAlmostEqual(vp, math.sqrt(2.0 * MU_EARTH / EARTH_RP_M),
                               delta=1e-6)

    def test_energy_integral_round_trip(self):
        v_inf = 2500.0
        vp = periapsis_speed(v_inf, EARTH_RP_M, MU_EARTH)
        lhs = vp ** 2 - v_inf ** 2
        rhs = 2.0 * MU_EARTH / EARTH_RP_M
        self.assertAlmostEqual(lhs, rhs, delta=1e-3)

    def test_negative_v_inf_raises(self):
        with self.assertRaises(ValueError):
            periapsis_speed(-1.0, EARTH_RP_M, MU_EARTH)

    def test_nonpositive_rp_raises(self):
        with self.assertRaises(ValueError):
            periapsis_speed(3000.0, 0.0, MU_EARTH)
        with self.assertRaises(ValueError):
            periapsis_speed(3000.0, -7000e3, MU_EARTH)

    def test_nonpositive_mu_raises(self):
        with self.assertRaises(ValueError):
            periapsis_speed(3000.0, EARTH_RP_M, 0.0)
        with self.assertRaises(ValueError):
            periapsis_speed(3000.0, EARTH_RP_M, -3.986e14)


class TestTurnAngle(unittest.TestCase):
    def test_earth_3000_worked_example(self):
        delta_deg = math.degrees(turn_angle_rad(3000.0, EARTH_RP_M, MU_EARTH))
        self.assertAlmostEqual(delta_deg, 119.43, delta=0.01)

    def test_earth_5000_worked_example(self):
        delta_deg = math.degrees(turn_angle_rad(5000.0, EARTH_RP_M, MU_EARTH))
        self.assertAlmostEqual(delta_deg, 88.04, delta=0.01)

    def test_turn_angle_bounds_positive(self):
        delta = turn_angle_rad(3000.0, EARTH_RP_M, MU_EARTH)
        self.assertGreater(delta, 0.0)
        self.assertLessEqual(delta, math.pi)

    def test_turn_angle_rejects_nonphysical(self):
        with self.assertRaises(ValueError):
            turn_angle_rad(-1.0, EARTH_RP_M, MU_EARTH)
        with self.assertRaises(ValueError):
            turn_angle_rad(3000.0, 0.0, MU_EARTH)
        with self.assertRaises(ValueError):
            turn_angle_rad(3000.0, EARTH_RP_M, 0.0)


class TestDvGain(unittest.TestCase):
    def test_earth_3000_worked_example(self):
        delta = turn_angle_rad(3000.0, EARTH_RP_M, MU_EARTH)
        self.assertAlmostEqual(dv_gain(3000.0, delta), 5181.1, delta=1.0)

    def test_earth_5000_worked_example(self):
        delta = turn_angle_rad(5000.0, EARTH_RP_M, MU_EARTH)
        self.assertAlmostEqual(dv_gain(5000.0, delta), 6949.0, delta=1.0)

    def test_gain_formula_identity(self):
        v_inf = 4000.0
        delta = 1.2
        self.assertAlmostEqual(dv_gain(v_inf, delta),
                               2.0 * v_inf * math.sin(delta / 2.0),
                               delta=1e-6)

    def test_zero_excess_speed_zero_gain(self):
        self.assertEqual(dv_gain(0.0, 2.0), 0.0)

    def test_negative_v_inf_raises(self):
        with self.assertRaises(ValueError):
            dv_gain(-1.0, 1.0)


class TestOutgoingDirection(unittest.TestCase):
    def test_outside_pass_worked_example(self):
        delta = turn_angle_rad(3000.0, EARTH_RP_M, MU_EARTH)
        self.assertAlmostEqual(outgoing_direction_deg(0.0, delta, 1),
                               119.43, delta=0.01)

    def test_inside_pass_turns_negative(self):
        delta = turn_angle_rad(3000.0, EARTH_RP_M, MU_EARTH)
        self.assertAlmostEqual(outgoing_direction_deg(0.0, delta, -1),
                               -119.43, delta=0.01)

    def test_nonzero_incoming_direction(self):
        delta = 0.5
        self.assertAlmostEqual(outgoing_direction_deg(30.0, delta, 1),
                               30.0 + math.degrees(delta), delta=1e-9)

    def test_invalid_turn_sign_raises(self):
        with self.assertRaises(ValueError):
            outgoing_direction_deg(0.0, 1.0, 0)
        with self.assertRaises(ValueError):
            outgoing_direction_deg(0.0, 1.0, 2)


class TestFeasibility(unittest.TestCase):
    def test_earth_629_km_pass(self):
        verdict = feasibility(EARTH_RP_M, EARTH_RADIUS_M, DEFAULT_MIN_ALT_M)
        self.assertEqual(verdict["altitude_m"], 629e3)
        self.assertEqual(verdict["min_alt_m"], DEFAULT_MIN_ALT_M)
        self.assertTrue(verdict["pass"])

    def test_mars_410_km_pass(self):
        verdict = feasibility(MARS_RP_M, MARS_RADIUS_M, 200e3)
        self.assertEqual(verdict["altitude_m"], 410e3)
        self.assertTrue(verdict["pass"])

    def test_altitude_exactly_minimum_passes(self):
        verdict = feasibility(EARTH_RADIUS_M + 200e3, EARTH_RADIUS_M, 200e3)
        self.assertEqual(verdict["altitude_m"], 200e3)
        self.assertTrue(verdict["pass"])

    def test_below_minimum_altitude_fails(self):
        verdict = feasibility(EARTH_RADIUS_M + 100e3, EARTH_RADIUS_M, 200e3)
        self.assertFalse(verdict["pass"])

    def test_inside_body_fails(self):
        verdict = feasibility(6000e3, EARTH_RADIUS_M, DEFAULT_MIN_ALT_M)
        self.assertEqual(verdict["altitude_m"], -371e3)
        self.assertFalse(verdict["pass"])

    def test_no_body_radius_passes_open(self):
        verdict = feasibility(EARTH_RP_M)
        self.assertIsNone(verdict["altitude_m"])
        self.assertTrue(verdict["pass"])

    def test_nonpositive_rp_raises(self):
        with self.assertRaises(ValueError):
            feasibility(0.0, EARTH_RADIUS_M, 200e3)


class TestAnalyze(unittest.TestCase):
    def test_earth_full_summary(self):
        result = analyze(3000.0, EARTH_RP_M, 0.0, mu_body=MU_EARTH,
                         body_radius_m=EARTH_RADIUS_M,
                         min_alt_m=DEFAULT_MIN_ALT_M)
        self.assertAlmostEqual(result["vp"], 11085.4, delta=0.5)
        self.assertAlmostEqual(result["delta_deg"], 119.43, delta=0.01)
        self.assertAlmostEqual(result["dv"], 5181.1, delta=1.0)
        self.assertAlmostEqual(result["outgoing_deg"], 119.43, delta=0.01)
        self.assertEqual(result["altitude_m"], 629e3)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["delta_rad"],
                               math.radians(result["delta_deg"]), delta=1e-9)

    def test_analyze_without_body_radius(self):
        result = analyze(3000.0, EARTH_RP_M, 0.0)
        self.assertIsNone(result["altitude_m"])
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["vp"], 11085.4, delta=0.5)

    def test_mars_analyze_passes(self):
        result = analyze(2500.0, MARS_RP_M, 10.0, body_radius_m=MARS_RADIUS_M,
                         min_alt_m=200e3)
        self.assertEqual(result["altitude_m"], 410e3)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["outgoing_deg"], 10.0 +
                               result["delta_deg"], delta=1e-6)

    def test_flyby_inside_body_raises(self):
        with self.assertRaises(ValueError):
            analyze(3000.0, 6000e3, 0.0, body_radius_m=EARTH_RADIUS_M)

    def test_analyze_rejects_nonphysical_inputs(self):
        with self.assertRaises(ValueError):
            analyze(-1.0, EARTH_RP_M, 0.0)
        with self.assertRaises(ValueError):
            analyze(3000.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            analyze(3000.0, EARTH_RP_M, 0.0, mu_body=0.0)


if __name__ == "__main__":
    unittest.main()
