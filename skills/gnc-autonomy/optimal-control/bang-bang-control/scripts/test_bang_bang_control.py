#!/usr/bin/env python3
"""Contract test: time-optimal bang-bang control of a double integrator.

Exercises scripts/bang_bang_control_logic.py (stdlib unittest, offline,
deterministic).  Contract anchors:

- Rest-to-rest d = 100 m, a = 1 m/s^2: T* = 20.0 s exactly (2*sqrt(100));
  switch_state returns (switch_time_s, switch_position, switch_velocity)
  = (10.0, 50.0, -10.0), i.e. T*/2, d/2, -sqrt(a*d).
- Slew frame: theta0 = 2 rad, alpha = 0.05 rad/s^2: T* = 2*sqrt(2/0.05)
  about 12.649111 s.
- Generic: x0 = 50 m, v0 = +5 m/s, a = 1: total about 20.810 s =
  5 + 2*sqrt(62.5) (the first leg brakes to rest at 62.5 m, then the
  profile returns); cross-checked against a stepping simulation of the
  sampled bang-bang command to within 1e-2.
- Stepping simulation from the switch state lands at the origin within
  1e-3.
- bang_bang_command polarity: -a above the switching curve, +a below,
  0.0 exactly on it (documented sign(0) = 0 convention).
- ValueError on a <= 0 everywhere and on d < 0; d = 0 returns 0.0.
- Determinism: repeated calls return identical results.
- Convenience dicts expose exactly the documented key sets.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bang_bang_control_logic as bb  # noqa: E402

# Stepping-simulation step size used for the cross-checks.
SIM_DT = 1e-4


def _simulate(x0, v0, a, t_end, dt=SIM_DT):
    """Step the double integrator x_ddot = u with u sampled per step as
    the bang-bang command bang_bang_command(x, v, a).  Symplectic Euler
    (v += u*dt then x += v*dt) from (x0, v0) for t_end seconds.
    Returns the final (x, v)."""
    x = float(x0)
    v = float(v0)
    steps = int(round(t_end / dt))
    for _ in range(steps):
        u = bb.bang_bang_command(x, v, a)
        v += u * dt
        x += v * dt
    return x, v


class TestSwitchingCurve(unittest.TestCase):
    """switch_curve: s = x + v*|v|/(2a), zero exactly on the curve."""

    def test_formula_value_checks(self):
        cases = [
            (100.0, 0.0, 1.0, 100.0),
            (50.0, 5.0, 1.0, 62.5),    # 50 + 25/2
            (0.0, -2.0, 1.0, -2.0),    # v*|v| = -4, s = -2
            (12.5, -5.0, 1.0, 0.0),    # lower branch at v = -5
            (20.0, -5.0, 1.0, 7.5),    # right of the lower branch
        ]
        for x, v, a, expected in cases:
            with self.subTest(x=x, v=v, a=a):
                self.assertAlmostEqual(bb.switch_curve(x, v, a), expected,
                                       places=12)

    def test_zero_on_curve_branches(self):
        # Lower branch x = v^2/(2a) at v = -10; upper branch
        # x = -v^2/(2a) at v = 3.
        self.assertEqual(bb.switch_curve(50.0, -10.0, 1.0), 0.0)
        self.assertEqual(bb.switch_curve(-4.5, 3.0, 1.0), 0.0)

    def test_nonpositive_a_raises(self):
        with self.assertRaises(ValueError):
            bb.switch_curve(1.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            bb.switch_curve(1.0, 1.0, -2.0)


class TestBangBangCommand(unittest.TestCase):
    """bang_bang_command: u = -a*sign(s), sign(0) = 0 documented."""

    def test_polarity_across_curve(self):
        # Above the curve (s > 0) the command is -a; below (s < 0) +a.
        cases = [
            (100.0, 0.0, 1.0, -1.0),
            (50.0, 5.0, 1.0, -1.0),
            (-1.0, 0.0, 1.0, 1.0),
            (20.0, -10.0, 2.0, 2.0),
            (20.0, -5.0, 1.0, -1.0),   # right of lower branch
            (5.0, -5.0, 1.0, 1.0),     # left of lower branch
        ]
        for x, v, a, expected in cases:
            with self.subTest(x=x, v=v, a=a):
                self.assertEqual(bb.bang_bang_command(x, v, a), expected)

    def test_zero_command_on_curve(self):
        # sign(0) = 0: a state exactly on the switching curve commands 0.
        self.assertEqual(bb.bang_bang_command(50.0, -10.0, 1.0), 0.0)
        self.assertEqual(bb.bang_bang_command(12.5, -5.0, 1.0), 0.0)
        self.assertEqual(bb.bang_bang_command(-4.5, 3.0, 1.0), 0.0)
        self.assertEqual(bb.bang_bang_command(0.0, 0.0, 1.0), 0.0)

    def test_command_is_minus_a_exactly(self):
        # The returned magnitude equals the limit: -0.05 above the curve.
        self.assertEqual(bb.bang_bang_command(2.0, 0.0, 0.05), -0.05)
        self.assertEqual(bb.bang_bang_command(30.0, 0.0, 0.5), -0.5)
        self.assertEqual(bb.bang_bang_command(-30.0, 0.0, 0.5), 0.5)

    def test_nonpositive_a_raises(self):
        with self.assertRaises(ValueError):
            bb.bang_bang_command(1.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            bb.bang_bang_command(1.0, 0.0, -1.0)


class TestRestToRest(unittest.TestCase):
    """min_time_rest_to_rest: T* = 2*sqrt(d/a)."""

    def test_anchor_100m_exact_20(self):
        # 2*sqrt(100/1) = 20.0 exactly in IEEE double arithmetic.
        self.assertEqual(bb.min_time_rest_to_rest(100.0, 1.0), 20.0)

    def test_slew_anchor_2rad(self):
        # 2*sqrt(2/0.05) about 12.649111 s.
        self.assertAlmostEqual(bb.min_time_rest_to_rest(2.0, 0.05),
                               12.649111, places=5)

    def test_scaling_and_zero_distance(self):
        # d = 25, a = 1: 10 s; d = 100, a = 4: 10 s; d = 0: 0.0.
        self.assertEqual(bb.min_time_rest_to_rest(25.0, 1.0), 10.0)
        self.assertEqual(bb.min_time_rest_to_rest(100.0, 4.0), 10.0)
        self.assertEqual(bb.min_time_rest_to_rest(0.0, 1.0), 0.0)
        self.assertEqual(bb.min_time_rest_to_rest(0.0, 5.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            bb.min_time_rest_to_rest(-5.0, 1.0)
        with self.assertRaises(ValueError):
            bb.min_time_rest_to_rest(-0.1, 2.0)
        with self.assertRaises(ValueError):
            bb.min_time_rest_to_rest(100.0, 0.0)
        with self.assertRaises(ValueError):
            bb.min_time_rest_to_rest(100.0, -1.0)


class TestSwitchState(unittest.TestCase):
    """switch_state: (sqrt(d/a), d/2, -sqrt(a*d)) with exact keys."""

    def test_anchor_100m(self):
        result = bb.switch_state(100.0, 1.0)
        self.assertEqual(result["switch_time_s"], 10.0)
        self.assertEqual(result["switch_position"], 50.0)
        self.assertEqual(result["switch_velocity"], -10.0)

    def test_keys_and_other_distances(self):
        self.assertEqual(
            set(bb.switch_state(100.0, 1.0).keys()),
            {"switch_time_s", "switch_position", "switch_velocity"})
        result = bb.switch_state(25.0, 4.0)
        self.assertEqual(result["switch_time_s"], 2.5)
        self.assertEqual(result["switch_position"], 12.5)
        self.assertEqual(result["switch_velocity"], -10.0)
        zero = bb.switch_state(0.0, 1.0)
        self.assertEqual(zero["switch_time_s"], 0.0)
        self.assertEqual(zero["switch_position"], 0.0)
        self.assertEqual(zero["switch_velocity"], 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            bb.switch_state(-1.0, 1.0)
        with self.assertRaises(ValueError):
            bb.switch_state(100.0, 0.0)


class TestMinTimeState(unittest.TestCase):
    """min_time_state: analytic two-leg minimum-time maneuver."""

    def test_generic_anchor_analytic(self):
        # x0 = 50, v0 = +5, a = 1: total = 5 + 2*sqrt(62.5) about 20.810.
        result = bb.min_time_state(50.0, 5.0, 1.0)
        expected = 5.0 + 2.0 * math.sqrt(62.5)
        self.assertAlmostEqual(result["total_time"], expected, places=10)
        self.assertAlmostEqual(result["total_time"], 20.810, places=2)
        # Brake-to-rest waypoint: 5 s to rest at 62.5 m, then the
        # rest-to-rest return from 62.5 m.
        self.assertAlmostEqual(
            result["total_time"],
            5.0 + bb.min_time_rest_to_rest(62.5, 1.0), places=9)

    def test_generic_anchor_stepping_simulation(self):
        # Stepping the sampled bang-bang command from (50, 5) for the
        # analytic total lands at rest at the origin within 1e-2.
        result = bb.min_time_state(50.0, 5.0, 1.0)
        x_f, v_f = _simulate(50.0, 5.0, 1.0, result["total_time"])
        self.assertLess(abs(x_f), 1e-2)
        self.assertLess(abs(v_f), 1e-2)

    def test_switch_fields_on_lower_branch(self):
        result = bb.min_time_state(50.0, 5.0, 1.0)
        # v_s = -sqrt(62.5), x_s = 31.25, t1 = 5 + sqrt(62.5).
        self.assertAlmostEqual(result["switch_velocity"],
                               -math.sqrt(62.5), places=10)
        self.assertAlmostEqual(result["switch_position"], 31.25, places=10)
        self.assertAlmostEqual(result["switch_time"],
                               5.0 + math.sqrt(62.5), places=10)
        self.assertEqual(result["command_phases"][0][0], -1.0)
        self.assertEqual(result["command_phases"][1][0], 1.0)
        # The switch state lies on the switching curve.
        self.assertAlmostEqual(
            bb.switch_curve(result["switch_position"],
                            result["switch_velocity"], 1.0), 0.0, places=9)

    def test_rest_to_rest_consistency(self):
        # min_time_state(d, 0, a) reproduces the rest-to-rest maneuver:
        # same total time and the same switch point as switch_state.
        m = bb.min_time_state(100.0, 0.0, 1.0)
        self.assertEqual(m["total_time"], bb.min_time_rest_to_rest(100.0, 1.0))
        self.assertEqual(m["switch_time"], 10.0)
        self.assertEqual(m["switch_position"], 50.0)
        self.assertEqual(m["switch_velocity"], -10.0)
        self.assertEqual(len(m["command_phases"]), 2)

    def test_single_leg_on_curve_and_origin(self):
        # Upper branch (v = 3): ride with -a, T = 3.0, switch_time 0.
        up = bb.min_time_state(-4.5, 3.0, 1.0)
        self.assertEqual(up["total_time"], 3.0)
        self.assertEqual(up["switch_time"], 0.0)
        self.assertEqual(up["command_phases"], [(-1.0, 3.0)])
        # Lower branch (v = -10): ride with +a, T = 10.0.
        low = bb.min_time_state(50.0, -10.0, 1.0)
        self.assertEqual(low["total_time"], 10.0)
        self.assertEqual(low["command_phases"], [(1.0, 10.0)])
        # Origin: zero-length maneuver.
        origin = bb.min_time_state(0.0, 0.0, 1.0)
        self.assertEqual(origin["total_time"], 0.0)
        self.assertEqual(origin["command_phases"], [(0.0, 0.0)])

    def test_mirror_symmetry_and_short_leg(self):
        # (-x0, -v0) mirrors (x0, v0): same total time, flipped commands.
        m1 = bb.min_time_state(50.0, 5.0, 1.0)
        m2 = bb.min_time_state(-50.0, -5.0, 1.0)
        self.assertEqual(m1["total_time"], m2["total_time"])
        self.assertEqual(m1["switch_position"], -m2["switch_position"])
        self.assertEqual(m1["command_phases"][0][0],
                         -m2["command_phases"][0][0])
        # (20, -5): s = 7.5 > 0, brief -a leg onto the lower branch:
        # total = (v0 + 2*sqrt(a*x0 + v0^2/2))/a.
        short = bb.min_time_state(20.0, -5.0, 1.0)
        self.assertGreater(short["switch_time"], 0.0)
        self.assertLess(short["switch_time"], 1.0)
        self.assertEqual(short["command_phases"][0][0], -1.0)
        self.assertEqual(short["command_phases"][1][0], 1.0)
        expected = (-5.0 + 2.0 * math.sqrt(32.5)) / 1.0
        self.assertAlmostEqual(short["total_time"], expected, places=10)

    def test_phase_durations_sum_to_total_and_keys(self):
        self.assertEqual(
            set(bb.min_time_state(50.0, 5.0, 1.0).keys()),
            {"total_time", "switch_time", "switch_position",
             "switch_velocity", "command_phases"})
        for x0, v0 in [(50.0, 5.0), (-50.0, -5.0), (100.0, 0.0),
                       (20.0, -5.0), (-4.5, 3.0)]:
            with self.subTest(x0=x0, v0=v0):
                result = bb.min_time_state(x0, v0, 1.0)
                total = sum(d for _, d in result["command_phases"])
                self.assertAlmostEqual(total, result["total_time"], places=9)
                for command, duration in result["command_phases"]:
                    self.assertIn(command, (-1.0, 0.0, 1.0))
                    self.assertGreaterEqual(duration, 0.0)

    def test_nonpositive_a_raises(self):
        with self.assertRaises(ValueError):
            bb.min_time_state(1.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            bb.min_time_state(1.0, 0.0, -1.0)


class TestSteppingSimulationCrossCheck(unittest.TestCase):
    """Stepping the sampled bang-bang command reproduces the analytics."""

    def test_switch_state_and_full_profile_land_origin(self):
        # From the switch point of the 100 m maneuver the +a leg reaches
        # rest at the origin within 1e-3; same for the full profile.
        switch = bb.switch_state(100.0, 1.0)
        x_f, v_f = _simulate(switch["switch_position"],
                             switch["switch_velocity"], 1.0, 10.0)
        self.assertLess(abs(x_f), 1e-3)
        self.assertLess(abs(v_f), 1e-3)
        x_f, v_f = _simulate(100.0, 0.0, 1.0,
                             bb.min_time_rest_to_rest(100.0, 1.0))
        self.assertLess(abs(x_f), 1e-3)
        self.assertLess(abs(v_f), 1e-3)

    def test_braking_waypoint_at_62_5m(self):
        # The first leg under -a passes through rest at x = 62.5 m at
        # t = 5 s, then the profile returns toward the origin.
        x_f, v_f = _simulate(50.0, 5.0, 1.0, 5.0)
        self.assertAlmostEqual(x_f, 62.5, places=2)
        self.assertLess(abs(v_f), 1e-3)


class TestSummaryAndDeterminism(unittest.TestCase):
    """bang_bang_summary and run-to-run determinism."""

    def test_summary_keys_and_match(self):
        self.assertEqual(
            set(bb.bang_bang_summary(50.0, 5.0, 1.0).keys()),
            {"x0", "v0", "accel_limit", "switching_function_0",
             "total_time", "switch_time", "switch_position",
             "switch_velocity", "command_phases"})
        summary = bb.bang_bang_summary(50.0, 5.0, 1.0)
        m = bb.min_time_state(50.0, 5.0, 1.0)
        self.assertEqual(summary["total_time"], m["total_time"])
        self.assertEqual(summary["switch_time"], m["switch_time"])
        self.assertEqual(summary["switch_position"], m["switch_position"])
        self.assertEqual(summary["switch_velocity"], m["switch_velocity"])
        self.assertEqual(summary["command_phases"], m["command_phases"])
        self.assertEqual(summary["switching_function_0"], 62.5)
        self.assertEqual(summary["x0"], 50.0)
        self.assertEqual(summary["v0"], 5.0)
        self.assertEqual(summary["accel_limit"], 1.0)

    def test_summary_slew_frame(self):
        # Slew frame theta0 = 2 rad, alpha = 0.05 rad/s^2.
        summary = bb.bang_bang_summary(2.0, 0.0, 0.05)
        self.assertAlmostEqual(summary["total_time"],
                               bb.min_time_rest_to_rest(2.0, 0.05), places=12)
        self.assertAlmostEqual(summary["total_time"], 12.649111, places=5)
        with self.assertRaises(ValueError):
            bb.bang_bang_summary(1.0, 0.0, 0.0)

    def test_determinism_repeated_calls(self):
        for x0, v0, a in [(50.0, 5.0, 1.0), (100.0, 0.0, 1.0),
                          (20.0, -5.0, 1.0), (-50.0, -5.0, 1.0)]:
            with self.subTest(x0=x0, v0=v0, a=a):
                self.assertEqual(bb.min_time_state(x0, v0, a),
                                 bb.min_time_state(x0, v0, a))
                self.assertEqual(bb.bang_bang_summary(x0, v0, a),
                                 bb.bang_bang_summary(x0, v0, a))


if __name__ == "__main__":
    unittest.main()
