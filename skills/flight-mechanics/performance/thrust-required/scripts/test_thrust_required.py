#!/usr/bin/env python3
"""Gate 3 contract test: thrust required and power required curves for
level unaccelerated flight.

Exercises scripts/thrust_required_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the lift and drag
coefficients return the worked values, the thrust required and power
required follow the parabolic polar at the pinned speeds, the minimum
drag speed and minimum power speed are pinned with their ordering, the
minimum thrust equals the thrust required at the minimum drag speed,
the curve shape is U shaped, and invalid inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import thrust_required_logic as tr  # noqa: E402

W = 650000.0
S = 122.0
RHO = 1.225
CD0 = 0.02
K = 0.042


class LiftDragCoefficientTest(unittest.TestCase):
    def test_lift_coefficient_worked_case(self):
        # CL = 2 W / (rho V^2 S); at the minimum drag speed
        # CL* = sqrt(cd0 / k).
        self.assertAlmostEqual(
            tr.lift_coefficient(112.27, W, S, RHO),
            math.sqrt(CD0 / K), places=3)

    def test_drag_coefficient_worked_case(self):
        # At the minimum drag speed the drag coefficient is twice cd0.
        self.assertAlmostEqual(
            tr.drag_coefficient(112.27, W, S, RHO, CD0, K),
            2.0 * CD0, places=3)

    def test_invalid_inputs_raise(self):
        for bad in (0.0, -1.0, "fast", True, None):
            with self.assertRaises(ValueError):
                tr.lift_coefficient(bad, W, S, RHO)
            with self.assertRaises(ValueError):
                tr.lift_coefficient(112.27, bad, S, RHO)
            with self.assertRaises(ValueError):
                tr.lift_coefficient(112.27, W, bad, RHO)
            with self.assertRaises(ValueError):
                tr.lift_coefficient(112.27, W, S, bad)
        with self.assertRaises(ValueError):
            tr.drag_coefficient(112.27, W, S, RHO, 0.0, K)
        with self.assertRaises(ValueError):
            tr.drag_coefficient(112.27, W, S, RHO, CD0, 0.0)
        with self.assertRaises(ValueError):
            tr.drag_coefficient(112.27, W, S, RHO, CD0, -0.1)


class ThrustPowerCurveTest(unittest.TestCase):
    def test_thrust_required_at_minimum_drag_speed(self):
        # The worked curve minimum is about 37678 N at V_md.
        self.assertAlmostEqual(
            tr.thrust_required(112.27, W, S, RHO, CD0, K),
            37678.0, delta=10.0)

    def test_thrust_required_at_minimum_power_speed(self):
        # At V_mp the thrust is about 43506 N (three quarters induced).
        self.assertAlmostEqual(
            tr.thrust_required(85.31, W, S, RHO, CD0, K),
            43506.0, delta=20.0)

    def test_power_required_worked_case(self):
        # P_req = T_req V at the minimum drag speed.
        self.assertAlmostEqual(
            tr.power_required(112.27, W, S, RHO, CD0, K),
            4.23e6, delta=1.0e4)

    def test_thrust_curve_is_u_shaped(self):
        # Both the slow (induced dominated) and fast (parasite
        # dominated) sides sit above the minimum at V_md.
        t_min = tr.thrust_required(112.27, W, S, RHO, CD0, K)
        self.assertGreater(
            tr.thrust_required(60.0, W, S, RHO, CD0, K), t_min)
        self.assertGreater(
            tr.thrust_required(140.0, W, S, RHO, CD0, K), t_min)

    def test_power_curve_minimum_at_minimum_power_speed(self):
        # P(V_mp) is below P(V_md) and below P at the slow side.
        p_mp = tr.power_required(85.31, W, S, RHO, CD0, K)
        self.assertLess(
            p_mp, tr.power_required(112.27, W, S, RHO, CD0, K))
        self.assertLess(
            p_mp, tr.power_required(60.0, W, S, RHO, CD0, K))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tr.thrust_required(0.0, W, S, RHO, CD0, K)
        with self.assertRaises(ValueError):
            tr.thrust_required(112.27, -W, S, RHO, CD0, K)
        with self.assertRaises(ValueError):
            tr.thrust_required(112.27, W, S, 0.0, CD0, K)
        with self.assertRaises(ValueError):
            tr.thrust_required(112.27, W, S, RHO, CD0, True)
        with self.assertRaises(ValueError):
            tr.power_required(112.27, W, S, RHO, 0.0, K)
        with self.assertRaises(ValueError):
            tr.power_required("fast", W, S, RHO, CD0, K)


class CharacteristicPointsTest(unittest.TestCase):
    def test_minimum_drag_speed_worked_case(self):
        self.assertAlmostEqual(
            tr.minimum_drag_speed(W, S, RHO, CD0, K), 112.27, places=1)

    def test_minimum_power_speed_worked_case(self):
        self.assertAlmostEqual(
            tr.minimum_power_speed(W, S, RHO, CD0, K), 85.31, places=1)

    def test_power_speed_below_drag_speed(self):
        self.assertLess(
            tr.minimum_power_speed(W, S, RHO, CD0, K),
            tr.minimum_drag_speed(W, S, RHO, CD0, K))

    def test_power_speed_relation(self):
        # V_mp = V_md / 3^(1/4) for the parabolic polar.
        self.assertAlmostEqual(
            tr.minimum_drag_speed(W, S, RHO, CD0, K)
            / tr.minimum_power_speed(W, S, RHO, CD0, K),
            3.0 ** 0.25, places=3)

    def test_maximum_lift_to_drag_worked_case(self):
        self.assertAlmostEqual(
            tr.maximum_lift_to_drag(CD0, K), 17.25, places=2)

    def test_minimum_thrust_worked_case(self):
        self.assertAlmostEqual(
            tr.minimum_thrust(W, CD0, K), 37677.0, delta=10.0)

    def test_minimum_thrust_equals_curve_minimum(self):
        # T_min matches the thrust required at the minimum drag speed.
        v_md = tr.minimum_drag_speed(W, S, RHO, CD0, K)
        self.assertAlmostEqual(
            tr.minimum_thrust(W, CD0, K),
            tr.thrust_required(v_md, W, S, RHO, CD0, K), delta=10.0)

    def test_minimum_thrust_times_ldmax_is_weight(self):
        ld = tr.maximum_lift_to_drag(CD0, K)
        self.assertAlmostEqual(
            tr.minimum_thrust(W, CD0, K) * ld, W, delta=10.0)

    def test_invalid_inputs_raise(self):
        for fn in (tr.minimum_drag_speed, tr.minimum_power_speed):
            with self.assertRaises(ValueError):
                fn(W, S, RHO, 0.0, K)
            with self.assertRaises(ValueError):
                fn(W, S, RHO, CD0, 0.0)
            with self.assertRaises(ValueError):
                fn(0.0, S, RHO, CD0, K)
            with self.assertRaises(ValueError):
                fn(W, S, RHO, CD0, None)
        with self.assertRaises(ValueError):
            tr.maximum_lift_to_drag(0.0, K)
        with self.assertRaises(ValueError):
            tr.maximum_lift_to_drag(CD0, -1.0)
        with self.assertRaises(ValueError):
            tr.minimum_thrust(-W, CD0, K)
        with self.assertRaises(ValueError):
            tr.minimum_thrust(W, CD0, True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
