#!/usr/bin/env python3
"""Gate 3 contract test: pursuit guidance laws.

Exercises scripts/pursuit_guidance_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the planar
pursuit guidance laws: line of sight angle lam = atan2(ry, rx) in
rad, wrapped guidance error eta = wrap(lam - psi) in [-pi, pi], lead
pursuit lead angle lam_lead = asin((Vt/Vi) sin(beta)) in rad with
ValueError when no collision course exists, capture condition
Vi > Vt, tail chase intercept time t_i = r / (Vi - Vt) in s, and the
proportional navigation comparison command a_c = N * Vc * lam_dot in
m/s^2.

Analytic checks:
  lam(1000, 1000)      = atan2(1000, 1000)        = pi/4
  eta(psi=0, 1000, 1000) = pi/4 - 0               = pi/4
  eta(psi=3, -1000, -100) = wrap(-6.0419239)      = 0.2412614
  lam_lead(200, 400, pi/2) = asin(0.5)            = pi/6
  aim with lead          = pi/4 + pi/6            = 5*pi/12
  t_i(1000, 400, 200)   = 1000 / 200              = 5.0
  a_c(1000, 100, -200, 0, N=4) = 15.762965390 (PN leaf reference)
Asserted with places=4. Units: m, m/s, rad, rad/s, m/s^2.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pursuit_guidance_logic as pg  # noqa: E402

ACC_REF = 15.762965390  # PN comparison command, N=4 (PN leaf reference)


class LineOfSightAngleTest(unittest.TestCase):
    def test_analytic_diagonal(self):
        lam = pg.line_of_sight_angle(1000.0, 1000.0)
        self.assertAlmostEqual(lam, math.pi / 4.0, places=4)

    def test_pure_closing_along_x(self):
        # Target due east: lam = 0
        lam = pg.line_of_sight_angle(1000.0, 0.0)
        self.assertAlmostEqual(lam, 0.0, places=4)

    def test_target_due_north(self):
        lam = pg.line_of_sight_angle(0.0, 500.0)
        self.assertAlmostEqual(lam, math.pi / 2.0, places=4)

    def test_target_southeast(self):
        lam = pg.line_of_sight_angle(1000.0, -1000.0)
        self.assertAlmostEqual(lam, -math.pi / 4.0, places=4)

    def test_zero_range_raises(self):
        with self.assertRaises(ValueError):
            pg.line_of_sight_angle(0.0, 0.0)

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            pg.line_of_sight_angle("big", 100.0)


class HeadingErrorTest(unittest.TestCase):
    def test_analytic_diagonal(self):
        # psi = 0 (due east), target northeast: eta = pi/4
        eta = pg.heading_error(0.0, 1000.0, 1000.0)
        self.assertAlmostEqual(eta, math.pi / 4.0, places=4)

    def test_aligned_no_error(self):
        eta = pg.heading_error(math.pi / 4.0, 1000.0, 1000.0)
        self.assertAlmostEqual(eta, 0.0, places=4)

    def test_wrap_into_pi(self):
        # lam = atan2(-100, -1000) = -3.0419239; psi = 3.0;
        # raw difference -6.0419239 wraps to +0.2412614
        eta = pg.heading_error(3.0, -1000.0, -100.0)
        self.assertAlmostEqual(eta, 0.2412614, places=4)

    def test_error_inside_bounds(self):
        for psi in (-3.0, -0.5, 0.0, 1.0, 2.9):
            eta = pg.heading_error(psi, 1000.0, -100.0)
            self.assertGreaterEqual(eta, -math.pi)
            self.assertLessEqual(eta, math.pi)

    def test_zero_range_raises(self):
        with self.assertRaises(ValueError):
            pg.heading_error(0.0, 0.0, 0.0)

    def test_non_numeric_heading_raises(self):
        with self.assertRaises(ValueError):
            pg.heading_error("fast", 1000.0, 1000.0)


class LeadAngleTest(unittest.TestCase):
    def test_analytic_crossing_target(self):
        # Vt = 200, Vi = 400, beta = pi/2: asin(0.5) = pi/6
        lead = pg.lead_angle(200.0, 400.0, math.pi / 2.0)
        self.assertAlmostEqual(lead, math.pi / 6.0, places=4)

    def test_zero_when_target_along_los(self):
        # beta = 0: target flies straight along the LOS, no lead needed
        lead = pg.lead_angle(200.0, 400.0, 0.0)
        self.assertAlmostEqual(lead, 0.0, places=4)

    def test_speed_ratio_scaling(self):
        # Vt/Vi = 0.5, beta = pi/2: asin(0.5); Vt/Vi = 0.25: asin(0.25)
        lead = pg.lead_angle(100.0, 400.0, math.pi / 2.0)
        self.assertAlmostEqual(lead, math.asin(0.25), places=4)

    def test_no_collision_course_raises(self):
        # Vt/Vi = 2.0, beta = pi/2: arcsin argument 2.0, no real lead
        with self.assertRaises(ValueError):
            pg.lead_angle(400.0, 200.0, math.pi / 2.0)

    def test_negative_speed_raises(self):
        with self.assertRaises(ValueError):
            pg.lead_angle(200.0, 0.0, math.pi / 2.0)


class PursuitHeadingTest(unittest.TestCase):
    def test_pure_pursuit_is_los_angle(self):
        # Pure pursuit aims at the target's current position
        psi_cmd = pg.pursuit_heading(1000.0, 1000.0)
        self.assertAlmostEqual(psi_cmd, math.pi / 4.0, places=4)

    def test_lead_pursuit_aims_ahead(self):
        # pi/4 + pi/6 = 5*pi/12: line of sight plus lead angle
        psi_cmd = pg.pursuit_heading(1000.0, 1000.0, 200.0, 400.0,
                                     beta=math.pi / 2.0)
        self.assertAlmostEqual(psi_cmd, 5.0 * math.pi / 12.0, places=4)

    def test_lead_pursuit_impossible_raises(self):
        with self.assertRaises(ValueError):
            pg.pursuit_heading(1000.0, 1000.0, 400.0, 200.0,
                               beta=math.pi / 2.0)

    def test_zero_range_raises(self):
        with self.assertRaises(ValueError):
            pg.pursuit_heading(0.0, 0.0)


class CaptureConditionTest(unittest.TestCase):
    def test_faster_interceptor_captures(self):
        self.assertTrue(pg.capture_possible(400.0, 200.0))

    def test_slower_interceptor_never_captures(self):
        self.assertFalse(pg.capture_possible(200.0, 400.0))

    def test_equal_speeds_no_capture(self):
        # Strict inequality: Vi = Vt never closes on a receding target
        self.assertFalse(pg.capture_possible(400.0, 400.0))

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            pg.capture_possible("fast", 200.0)


class InterceptTimeTest(unittest.TestCase):
    def test_analytic_tail_chase(self):
        # r = 1000 m, Vi = 400, Vt = 200: closing at 200 m/s, t = 5 s
        t = pg.intercept_time(1000.0, 400.0, 200.0)
        self.assertAlmostEqual(t, 5.0, places=4)

    def test_high_speed_ratio_shorter_time(self):
        t = pg.intercept_time(1000.0, 500.0, 200.0)
        self.assertAlmostEqual(t, 1000.0 / 300.0, places=4)

    def test_no_closure_raises(self):
        with self.assertRaises(ValueError):
            pg.intercept_time(1000.0, 200.0, 400.0)
        with self.assertRaises(ValueError):
            pg.intercept_time(1000.0, 400.0, 400.0)

    def test_zero_range_raises(self):
        with self.assertRaises(ValueError):
            pg.intercept_time(0.0, 400.0, 200.0)


class PnComparisonTest(unittest.TestCase):
    def test_analytic_command_matches_pn_leaf(self):
        # Same reference case as the proportional-navigation leaf:
        # rx=1000, ry=100, vx=-200, vy=0, N=4 -> a_c = 15.762965390
        a = pg.pn_acceleration(1000.0, 100.0, -200.0, 0.0, 4.0)
        self.assertAlmostEqual(a, ACC_REF, places=4)

    def test_zero_command_on_pure_closing(self):
        # lam_dot = 0 on a pure closing geometry: no lateral command
        a = pg.pn_acceleration(1000.0, 0.0, -200.0, 0.0, 4.0)
        self.assertAlmostEqual(a, 0.0, places=4)

    def test_linear_in_navigation_constant(self):
        a4 = pg.pn_acceleration(1000.0, 100.0, -200.0, 0.0, 4.0)
        a8 = pg.pn_acceleration(1000.0, 100.0, -200.0, 0.0, 8.0)
        self.assertAlmostEqual(a8 / a4, 2.0, places=4)

    def test_nonpositive_nav_raises(self):
        with self.assertRaises(ValueError):
            pg.pn_acceleration(1000.0, 100.0, -200.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            pg.pn_acceleration(1000.0, 100.0, -200.0, 0.0, -3.0)

    def test_zero_range_raises(self):
        with self.assertRaises(ValueError):
            pg.pn_acceleration(0.0, 0.0, -200.0, 0.0, 4.0)


class GuidanceStateTest(unittest.TestCase):
    def test_pure_pursuit_bundle(self):
        st = pg.guidance_state(1000.0, 1000.0, 0.0, -200.0, 0.0,
                               v_target=200.0, v_interceptor=400.0)
        self.assertEqual(
            sorted(st.keys()),
            ["aim_heading", "capture_possible", "heading_error",
             "intercept_time", "lead_angle", "los_angle", "n_nav",
             "pn_accel_cmd", "range"],
        )
        self.assertAlmostEqual(st["range"], math.hypot(1000.0, 1000.0), places=4)
        self.assertAlmostEqual(st["los_angle"], math.pi / 4.0, places=4)
        self.assertAlmostEqual(st["aim_heading"], math.pi / 4.0, places=4)
        self.assertAlmostEqual(st["heading_error"], math.pi / 4.0, places=4)
        self.assertIsNone(st["lead_angle"])
        self.assertTrue(st["capture_possible"])
        # r = hypot(1000, 1000) = 1414.2136 m, closing at 200 m/s
        self.assertAlmostEqual(st["intercept_time"], 7.0710678, places=4)

    def test_lead_pursuit_bundle(self):
        st = pg.guidance_state(1000.0, 1000.0, 0.0, -200.0, 0.0,
                               v_target=200.0, v_interceptor=400.0,
                               beta=math.pi / 2.0)
        self.assertAlmostEqual(st["lead_angle"], math.pi / 6.0, places=4)
        self.assertAlmostEqual(st["aim_heading"], 5.0 * math.pi / 12.0, places=4)

    def test_slower_interceptor_bundle(self):
        st = pg.guidance_state(1000.0, 1000.0, 0.0, -200.0, 0.0,
                               v_target=400.0, v_interceptor=200.0)
        self.assertFalse(st["capture_possible"])
        self.assertIsNone(st["intercept_time"])

    def test_pn_command_in_bundle(self):
        st = pg.guidance_state(1000.0, 100.0, 0.0, -200.0, 0.0)
        self.assertAlmostEqual(st["pn_accel_cmd"], ACC_REF, places=4)
        self.assertEqual(st["n_nav"], 4.0)

    def test_zero_range_raises(self):
        with self.assertRaises(ValueError):
            pg.guidance_state(0.0, 0.0, 0.0, -200.0, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
