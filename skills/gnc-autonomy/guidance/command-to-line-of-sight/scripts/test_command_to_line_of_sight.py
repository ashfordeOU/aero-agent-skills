#!/usr/bin/env python3
"""Gate 3 contract test: command to line of sight guidance.

Exercises scripts/command_to_line_of_sight_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (tracker to target
line of sight angle; wrapped LOS error; line of sight rotation rate;
CLOS steering command proportional to the LOS error and its rate;
cross track offset of the missile from the tracker target line; on
line verdict within tolerance; invalid inputs raise ValueError.

Anchors:
- los_angle(1000, 1000) = pi/4 (tracker to point line at 45 deg)
- los_angle(-1000, 0) = pi (tracker to point line pointing west)
- wrap_angle(3*pi/2) = -pi/2 (wrapped into [-pi, pi])
- los_error(0.8, 0.5) = 0.3 (target 0.8 rad, missile 0.5 rad)
- los_error(3.0, -3.0) = 6.0 - 2*pi (wrapped difference)
- los_rate(300, 400, -30, -40) = 0.0 rad/s (pure radial closing)
- los_rate(300, 400, -40, 30) = 0.1 rad/s (tangential motion)
- steering_command(0.05, 0.02, 10, 5) = 0.6 m/s^2 (error + rate)
- steering_command(0.1, 0.0, 12, 0) = 1.2 m/s^2 (beam riding)
- cross_track_offset(1500, 100, 3000, 0) = 100 m (missile above line)
- cross_track_offset(1800, 2600, 3000, 4000) = 120 m (rotated line)
- on_line(50, 100) is True; on_line(150, 100) is False
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import command_to_line_of_sight_logic as clos  # noqa: E402

import math  # noqa: E402


class LosAngleTest(unittest.TestCase):
    def test_anchor_45_deg(self):
        self.assertAlmostEqual(clos.los_angle(1000, 1000), math.pi / 4.0)

    def test_anchor_west(self):
        self.assertAlmostEqual(clos.los_angle(-1000, 0), math.pi)

    def test_anchor_down(self):
        self.assertAlmostEqual(clos.los_angle(0, -1000), -math.pi / 2.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            clos.los_angle(0, 0)
        with self.assertRaises(ValueError):
            clos.los_angle("a", 1)
        with self.assertRaises(ValueError):
            clos.los_angle(1, None)


class WrapAngleTest(unittest.TestCase):
    def test_anchor_three_half_pi(self):
        self.assertAlmostEqual(clos.wrap_angle(3.0 * math.pi / 2.0), -math.pi / 2.0)

    def test_anchor_negative_three_half_pi(self):
        self.assertAlmostEqual(clos.wrap_angle(-3.0 * math.pi / 2.0), math.pi / 2.0)

    def test_anchor_in_range_unchanged(self):
        self.assertAlmostEqual(clos.wrap_angle(0.4), 0.4)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            clos.wrap_angle("b")


class LosErrorTest(unittest.TestCase):
    def test_anchor_error(self):
        self.assertAlmostEqual(clos.los_error(0.8, 0.5), 0.3)

    def test_anchor_wrapped(self):
        # 3.0 - (-3.0) = 6.0 rad wraps to 6.0 - 2*pi.
        self.assertAlmostEqual(clos.los_error(3.0, -3.0), 6.0 - 2.0 * math.pi)

    def test_anchor_zero(self):
        self.assertAlmostEqual(clos.los_error(0.7, 0.7), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            clos.los_error("t", 0.5)
        with self.assertRaises(ValueError):
            clos.los_error(0.8, None)


class LosRateTest(unittest.TestCase):
    def test_anchor_radial_zero(self):
        # Pure radial closing: the line does not rotate.
        self.assertAlmostEqual(clos.los_rate(300, 400, -30, -40), 0.0)

    def test_anchor_tangential(self):
        # (300*(-30) - 400*40) / 250000 = -25000 / 250000 = -0.1.
        self.assertAlmostEqual(clos.los_rate(300, 400, 40, -30), -0.1)

    def test_anchor_positive(self):
        self.assertAlmostEqual(clos.los_rate(300, 400, -40, 30), 0.1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            clos.los_rate(0, 0, 1, 1)
        with self.assertRaises(ValueError):
            clos.los_rate(300, 400, "v", 30)


class SteeringCommandTest(unittest.TestCase):
    def test_anchor_error_and_rate(self):
        self.assertAlmostEqual(clos.steering_command(0.05, 0.02, 10, 5), 0.6)

    def test_anchor_beam_riding(self):
        self.assertAlmostEqual(clos.steering_command(0.1, 0.0, 12, 0), 1.2)

    def test_anchor_zero_error(self):
        self.assertAlmostEqual(clos.steering_command(0.0, 0.05, 10, 4), 0.2)

    def test_invalid_gains_raise(self):
        with self.assertRaises(ValueError):
            clos.steering_command(0.05, 0.02, -1, 5)
        with self.assertRaises(ValueError):
            clos.steering_command(0.05, 0.02, 10, -2)
        with self.assertRaises(ValueError):
            clos.steering_command(0.05, 0.02, "k", 5)


class CrossTrackOffsetTest(unittest.TestCase):
    def test_anchor_axis_line(self):
        # Target on the x axis at 3000 m; missile 100 m above the line.
        self.assertAlmostEqual(clos.cross_track_offset(1500, 100, 3000, 0), 100.0)

    def test_anchor_rotated_line(self):
        # Target at (3000, 4000); missile 120 m off the line.
        self.assertAlmostEqual(
            clos.cross_track_offset(1800, 2600, 3000, 4000), 120.0
        )

    def test_anchor_on_line_zero(self):
        self.assertAlmostEqual(clos.cross_track_offset(1800, 2400, 3000, 4000), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            clos.cross_track_offset(1500, 100, 0, 0)
        with self.assertRaises(ValueError):
            clos.cross_track_offset("m", 100, 3000, 0)
        with self.assertRaises(ValueError):
            clos.cross_track_offset(1500, 100, 3000, None)


class OnLineTest(unittest.TestCase):
    def test_anchor_on_line(self):
        self.assertTrue(clos.on_line(50, 100))

    def test_anchor_off_line(self):
        self.assertFalse(clos.on_line(150, 100))

    def test_anchor_boundary(self):
        self.assertFalse(clos.on_line(100, 100))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            clos.on_line(50, 0)
        with self.assertRaises(ValueError):
            clos.on_line(50, -10)
        with self.assertRaises(ValueError):
            clos.on_line("d", 100)


class ClosScenarioTest(unittest.TestCase):
    def test_tracking_scenario(self):
        # Tracker at the origin, target at (3000, 4000) closing at
        # (-30, -40) m/s, missile at (1500, 2000): the missile sits on
        # the line (offset 0), the LOS error is zero, and only the LOS
        # rate term steers the command.
        lam_t = clos.los_angle(3000, 4000)
        lam_m = clos.los_angle(1500, 2000)
        eps = clos.los_error(lam_t, lam_m)
        lam_dot = clos.los_rate(3000, 4000, -30, -40)
        a_c = clos.steering_command(eps, lam_dot, 10, 5)
        d = clos.cross_track_offset(1500, 2000, 3000, 4000)
        self.assertAlmostEqual(lam_t, math.atan2(4000, 3000))
        self.assertAlmostEqual(lam_m, math.atan2(2000, 1500))
        self.assertAlmostEqual(eps, 0.0)
        self.assertAlmostEqual(lam_dot, 0.0)
        self.assertAlmostEqual(a_c, 0.0)
        self.assertAlmostEqual(d, 0.0)
        self.assertTrue(clos.on_line(d, 100))

    def test_off_line_scenario(self):
        # Missile 100 m below the x-axis target line: the error-only
        # beam riding command pulls it back onto the line.
        lam_t = clos.los_angle(3000, 0)
        lam_m = clos.los_angle(1500, -100)
        eps = clos.los_error(lam_t, lam_m)
        a_c = clos.steering_command(eps, 0.0, 12, 0)
        d = clos.cross_track_offset(1500, -100, 3000, 0)
        self.assertGreater(eps, 0.0)
        self.assertGreater(a_c, 0.0)
        self.assertAlmostEqual(d, -100.0)
        self.assertFalse(clos.on_line(d, 50))


if __name__ == "__main__":
    unittest.main(verbosity=2)
