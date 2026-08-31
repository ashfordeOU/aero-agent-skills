#!/usr/bin/env python3
"""Gate 3 contract test: proportional navigation guidance law.

Exercises scripts/proportional_navigation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the 2D planar
intercept PN law: closing velocity vc = -(rx*vx + ry*vy) / r in m/s,
line of sight rate lam_dot = (rx*vy - ry*vx) / r^2 in rad/s, commanded
acceleration a_c = N * vc * lam_dot in m/s^2 (perpendicular to the
line of sight), the bundled guidance_command dict, and ValueError on
zero range or nonpositive N.

Analytic check (rx=1000, ry=100, vx=-200, vy=0, N=4):
  r     = sqrt(1000^2 + 100^2) = sqrt(1010000)        = 1004.987562112089
  vc    = 200000 / sqrt(1010000)                       = 199.007438042
  lam_dot = 20000 / 1010000                            = 0.019801980198
  a_c   = 4 * 199.007438042 * 0.019801980198           = 15.762965390
Asserted with places=4. Units: m, m/s, rad/s, m/s^2.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import proportional_navigation_logic as pn  # noqa: E402

RANGE_REF = 1004.987562112089
VC_REF = 199.007438042
LAM_REF = 0.0198019801980198
ACC_REF = 15.762965390


class ClosingVelocityTest(unittest.TestCase):
    def test_analytic_intercept(self):
        vc = pn.closing_velocity(1000.0, 100.0, -200.0, 0.0)
        self.assertAlmostEqual(vc, VC_REF, places=4)

    def test_positive_when_closing(self):
        # Pure closing: rx > 0, vx < 0 along the LOS -> vc = 200 m/s
        vc = pn.closing_velocity(1000.0, 0.0, -200.0, 0.0)
        self.assertAlmostEqual(vc, 200.0, places=4)

    def test_negative_when_receding(self):
        # Receding target: vx = +200 m/s -> vc = -200 m/s
        vc = pn.closing_velocity(1000.0, 0.0, 200.0, 0.0)
        self.assertAlmostEqual(vc, -200.0, places=4)

    def test_side_velocity_does_not_affect_vc(self):
        # ry = 0: cross-range velocity drops out of the dot product
        vc = pn.closing_velocity(1000.0, 0.0, -200.0, 50.0)
        self.assertAlmostEqual(vc, 200.0, places=4)

    def test_zero_range_raises(self):
        with self.assertRaises(ValueError):
            pn.closing_velocity(0.0, 0.0, -200.0, 0.0)

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            pn.closing_velocity("big", 100.0, -200.0, 0.0)


class LineOfSightRateTest(unittest.TestCase):
    def test_analytic_intercept(self):
        lam = pn.line_of_sight_rate(1000.0, 100.0, -200.0, 0.0)
        self.assertAlmostEqual(lam, LAM_REF, places=4)

    def test_cross_range_velocity(self):
        # rx = 1000, ry = 0, vy = 100: lam_dot = 100000 / 1e6 = 0.1
        lam = pn.line_of_sight_rate(1000.0, 0.0, 0.0, 100.0)
        self.assertAlmostEqual(lam, 0.1, places=4)

    def test_zero_on_pure_closing(self):
        # ry = 0 and vy = 0: LOS does not rotate
        lam = pn.line_of_sight_rate(1000.0, 0.0, -200.0, 0.0)
        self.assertAlmostEqual(lam, 0.0, places=4)

    def test_sign_flips_with_side_velocity(self):
        lam = pn.line_of_sight_rate(1000.0, 0.0, 0.0, -100.0)
        self.assertAlmostEqual(lam, -0.1, places=4)

    def test_zero_range_raises(self):
        with self.assertRaises(ValueError):
            pn.line_of_sight_rate(0.0, 0.0, 0.0, 100.0)


class CommandedAccelerationTest(unittest.TestCase):
    def test_analytic_intercept(self):
        a = pn.commanded_acceleration(1000.0, 100.0, -200.0, 0.0, 4.0)
        self.assertAlmostEqual(a, ACC_REF, places=4)

    def test_linear_in_navigation_constant(self):
        # a_c = N * vc * lam_dot: N = 6 is exactly 1.5x N = 4
        a4 = pn.commanded_acceleration(1000.0, 100.0, -200.0, 0.0, 4.0)
        a6 = pn.commanded_acceleration(1000.0, 100.0, -200.0, 0.0, 6.0)
        self.assertAlmostEqual(a6 / a4, 1.5, places=4)

    def test_zero_when_los_rate_zero(self):
        # Pure closing: lam_dot = 0, so no lateral command
        a = pn.commanded_acceleration(1000.0, 0.0, -200.0, 0.0, 4.0)
        self.assertAlmostEqual(a, 0.0, places=4)

    def test_nav_constant_zero_raises(self):
        with self.assertRaises(ValueError):
            pn.commanded_acceleration(1000.0, 100.0, -200.0, 0.0, 0.0)

    def test_nav_constant_negative_raises(self):
        with self.assertRaises(ValueError):
            pn.commanded_acceleration(1000.0, 100.0, -200.0, 0.0, -2.0)

    def test_zero_range_raises(self):
        with self.assertRaises(ValueError):
            pn.commanded_acceleration(0.0, 0.0, -200.0, 0.0, 4.0)

    def test_non_numeric_nav_raises(self):
        with self.assertRaises(ValueError):
            pn.commanded_acceleration(1000.0, 100.0, -200.0, 0.0, "fast")


class GuidanceCommandTest(unittest.TestCase):
    def test_analytic_intercept_fields(self):
        cmd = pn.guidance_command(1000.0, 100.0, -200.0, 0.0, n_nav=4.0)
        self.assertEqual(
            sorted(cmd.keys()),
            ["accel_cmd", "closing_velocity", "los_rate", "n_nav", "range"],
        )
        self.assertAlmostEqual(cmd["range"], RANGE_REF, places=4)
        self.assertAlmostEqual(cmd["closing_velocity"], VC_REF, places=4)
        self.assertAlmostEqual(cmd["los_rate"], LAM_REF, places=4)
        self.assertAlmostEqual(cmd["accel_cmd"], ACC_REF, places=4)
        self.assertEqual(cmd["n_nav"], 4.0)

    def test_default_navigation_constant(self):
        cmd = pn.guidance_command(1000.0, 100.0, -200.0, 0.0)
        self.assertEqual(cmd["n_nav"], 4.0)

    def test_command_matches_individual_functions(self):
        cmd = pn.guidance_command(1000.0, 100.0, -200.0, 0.0, n_nav=3.0)
        self.assertAlmostEqual(
            cmd["accel_cmd"],
            pn.commanded_acceleration(1000.0, 100.0, -200.0, 0.0, 3.0),
            places=4,
        )
        self.assertAlmostEqual(
            cmd["closing_velocity"],
            pn.closing_velocity(1000.0, 100.0, -200.0, 0.0),
            places=4,
        )
        self.assertAlmostEqual(
            cmd["los_rate"],
            pn.line_of_sight_rate(1000.0, 100.0, -200.0, 0.0),
            places=4,
        )

    def test_zero_range_raises(self):
        with self.assertRaises(ValueError):
            pn.guidance_command(0.0, 0.0, -200.0, 0.0)

    def test_nonpositive_nav_raises(self):
        with self.assertRaises(ValueError):
            pn.guidance_command(1000.0, 100.0, -200.0, 0.0, n_nav=0.0)
        with self.assertRaises(ValueError):
            pn.guidance_command(1000.0, 100.0, -200.0, 0.0, n_nav=-5.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
