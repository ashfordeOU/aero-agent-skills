#!/usr/bin/env python3
"""Gate 3 contract test: PID controller design.

Exercises scripts/pid_control_design_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - PID output from gains and
error terms, Ziegler-Nichols gains from ultimate gain/period, PI/PID
pole placement for first/second-order plants, integrator anti-windup
clamping, type-1 gain/phase margins, and the discrete backward
difference; invalid inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pid_control_design_logic as pid  # noqa: E402


class PidOutputTest(unittest.TestCase):
    def test_output_from_terms(self):
        # u = 2*3 + 1*4 + 0.5*2 = 11
        self.assertAlmostEqual(
            pid.pid_output(2.0, 1.0, 0.5, 3.0, 4.0, 2.0), 11.0, delta=1e-12)

    def test_zero_error_zero_output(self):
        self.assertEqual(pid.pid_output(2.0, 1.0, 0.5, 0.0, 0.0, 0.0), 0.0)

    def test_negative_error_sign(self):
        # Pure proportional: kp=3, e=-2 -> -6
        self.assertEqual(pid.pid_output(3.0, 0.0, 0.0, -2.0, 0.0, 0.0), -6.0)

    def test_integral_and_derivative_terms_add(self):
        # Zero error isolates the integral term: ki=4, int=1.5 -> 6
        self.assertAlmostEqual(
            pid.pid_output(1.0, 4.0, 0.0, 0.0, 1.5, 0.0), 6.0, delta=1e-12)
        # Zero error isolates the derivative term: kd=2, d=3 -> 6
        self.assertAlmostEqual(
            pid.pid_output(1.0, 0.0, 2.0, 0.0, 0.0, 3.0), 6.0, delta=1e-12)

    def test_invalid_gains_raise(self):
        with self.assertRaises(ValueError):
            pid.pid_output(-1.0, 1.0, 0.5, 1.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            pid.pid_output(2.0, -0.5, 0.5, 1.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            pid.pid_output(2.0, 1.0, -0.5, 1.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            pid.pid_output(float("nan"), 1.0, 0.5, 1.0, 0.0, 0.0)


class ZieglerNicholsTest(unittest.TestCase):
    def test_classic_pid(self):
        # ku=2, tu=1: kp=1.2, ti=0.5, ki=2.4, td=0.125, kd=0.15
        g = pid.ziegler_nichols(2.0, 1.0, "pid")
        self.assertAlmostEqual(g["kp"], 1.2, delta=1e-12)
        self.assertAlmostEqual(g["ti"], 0.5, delta=1e-12)
        self.assertAlmostEqual(g["ki"], 2.4, delta=1e-12)
        self.assertAlmostEqual(g["td"], 0.125, delta=1e-12)
        self.assertAlmostEqual(g["kd"], 0.15, delta=1e-12)

    def test_pi_rule(self):
        # ku=2, tu=1: kp=0.9, ti=1/1.2, ki=1.08, no derivative term
        g = pid.ziegler_nichols(2.0, 1.0, "pi")
        self.assertAlmostEqual(g["kp"], 0.9, delta=1e-12)
        self.assertAlmostEqual(g["ti"], 1.0 / 1.2, delta=1e-12)
        self.assertAlmostEqual(g["ki"], 1.08, delta=1e-12)
        self.assertEqual(g["kd"], 0.0)
        self.assertIsNone(g["td"])

    def test_p_rule(self):
        g = pid.ziegler_nichols(2.0, 1.0, "p")
        self.assertAlmostEqual(g["kp"], 1.0, delta=1e-12)
        self.assertEqual(g["ki"], 0.0)
        self.assertEqual(g["kd"], 0.0)

    def test_scale_with_ku_and_tu(self):
        # Doubling ku doubles kp and ki; halving tu doubles ki
        g1 = pid.ziegler_nichols(1.0, 1.0, "pid")
        g2 = pid.ziegler_nichols(2.0, 1.0, "pid")
        self.assertAlmostEqual(g2["kp"], 2.0 * g1["kp"], delta=1e-12)
        g3 = pid.ziegler_nichols(1.0, 0.5, "pid")
        self.assertAlmostEqual(g3["ki"], 2.0 * g1["ki"], delta=1e-12)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pid.ziegler_nichols(0.0, 1.0)
        with self.assertRaises(ValueError):
            pid.ziegler_nichols(2.0, -1.0)
        with self.assertRaises(ValueError):
            pid.ziegler_nichols(2.0, 1.0, "pd")


class PolePlacementFirstOrderTest(unittest.TestCase):
    def test_pi_gains_known_values(self):
        # a=2, b=1, wn=3, zeta=0.7 -> kp=2.2, ki=9
        kp, ki = pid.pole_placement_first_order(2.0, 1.0, 3.0, 0.7)
        self.assertAlmostEqual(kp, 2.2, delta=1e-12)
        self.assertAlmostEqual(ki, 9.0, delta=1e-12)

    def test_closed_loop_matches_desired(self):
        # s^2 + (a + b*kp)s + b*ki == s^2 + 2*zeta*wn*s + wn^2
        a, b, wn, zeta = 1.5, 2.0, 4.0, 0.5
        kp, ki = pid.pole_placement_first_order(a, b, wn, zeta)
        self.assertAlmostEqual(a + b * kp, 2.0 * zeta * wn, delta=1e-9)
        self.assertAlmostEqual(b * ki, wn * wn, delta=1e-9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pid.pole_placement_first_order(2.0, 0.0, 3.0, 0.7)
        with self.assertRaises(ValueError):
            pid.pole_placement_first_order(2.0, 1.0, 0.0, 0.7)
        with self.assertRaises(ValueError):
            pid.pole_placement_first_order(2.0, 1.0, 3.0, 0.0)
        with self.assertRaises(ValueError):
            pid.pole_placement_first_order(2.0, 1.0, 3.0, 1.5)


class PolePlacementSecondOrderTest(unittest.TestCase):
    def test_pid_gains_known_values(self):
        # a1=2, a0=1, b=1, wn=3, zeta=0.7, p3=4 -> kp=24.8, ki=36, kd=6.2
        kp, ki, kd = pid.pole_placement_second_order(2.0, 1.0, 1.0, 3.0, 0.7, 4.0)
        self.assertAlmostEqual(kp, 24.8, delta=1e-9)
        self.assertAlmostEqual(ki, 36.0, delta=1e-9)
        self.assertAlmostEqual(kd, 6.2, delta=1e-9)

    def test_closed_loop_polynomial_matches_desired(self):
        # s^3 + (a1 + b*kd)s^2 + (a0 + b*kp)s + b*ki
        #   == (s^2 + 2*zeta*wn*s + wn^2)(s + p3)
        a1, a0, b = 3.0, 2.0, 0.5
        wn, zeta, p3 = 2.0, 0.7071, 5.0
        kp, ki, kd = pid.pole_placement_second_order(a1, a0, b, wn, zeta, p3)
        self.assertAlmostEqual(a1 + b * kd, 2.0 * zeta * wn + p3, delta=1e-9)
        self.assertAlmostEqual(a0 + b * kp,
                               wn * wn + 2.0 * zeta * wn * p3, delta=1e-9)
        self.assertAlmostEqual(b * ki, wn * wn * p3, delta=1e-9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pid.pole_placement_second_order(2.0, 1.0, 0.0, 3.0, 0.7, 4.0)
        with self.assertRaises(ValueError):
            pid.pole_placement_second_order(2.0, 1.0, 1.0, 0.0, 0.7, 4.0)
        with self.assertRaises(ValueError):
            pid.pole_placement_second_order(2.0, 1.0, 1.0, 3.0, 0.0, 4.0)
        with self.assertRaises(ValueError):
            pid.pole_placement_second_order(2.0, 1.0, 1.0, 3.0, 0.7, 0.0)


class IntegratorClampTest(unittest.TestCase):
    def test_integrates_inside_limits(self):
        # trial = 0 + 2*1*1 = 2, inside [-5, 5]
        self.assertAlmostEqual(
            pid.integrator_clamp(0.0, 1.0, 2.0, 1.0, 5.0), 2.0, delta=1e-12)

    def test_clamps_upper_limit(self):
        # trial = 4 + 2*1*1 = 6 > 5 -> clamped to 5
        self.assertAlmostEqual(
            pid.integrator_clamp(4.0, 1.0, 2.0, 1.0, 5.0), 5.0, delta=1e-12)

    def test_clamps_lower_limit(self):
        # trial = -4 + 2*(-1)*1 = -6 < -5 -> clamped to -5
        self.assertAlmostEqual(
            pid.integrator_clamp(-4.0, -1.0, 2.0, 1.0, 5.0), -5.0, delta=1e-12)

    def test_boundary_not_exceeded(self):
        # trial lands exactly on the limit: 4.9 + 2*1*0.05 = 5.0, kept
        self.assertAlmostEqual(
            pid.integrator_clamp(4.9, 1.0, 2.0, 0.05, 5.0), 5.0, delta=1e-12)

    def test_zero_ki_holds(self):
        # No integration gain: the integral is unchanged
        self.assertAlmostEqual(
            pid.integrator_clamp(3.0, 1.0, 0.0, 1.0, 5.0), 3.0, delta=1e-12)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pid.integrator_clamp(0.0, 1.0, 2.0, 0.0, 5.0)
        with self.assertRaises(ValueError):
            pid.integrator_clamp(0.0, 1.0, 2.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            pid.integrator_clamp(0.0, 1.0, -1.0, 1.0, 5.0)


class StabilityMarginsType1Test(unittest.TestCase):
    def test_known_values(self):
        # L = 2/(s(s+2)): wc^2 = (-4 + sqrt(32))/2 = 0.8284271
        m = pid.stability_margins_type1(2.0, 2.0)
        self.assertAlmostEqual(m["crossover_rad_s"], 0.9101797, delta=1e-4)
        self.assertAlmostEqual(m["phase_margin_deg"], 65.5305, delta=1e-2)
        self.assertEqual(m["gain_margin"], float("inf"))

    def test_crossover_equation_holds(self):
        # |L(j*wc)| = 1  <=>  K^2 = wc^2 (wc^2 + a^2)
        a, K = 1.0, 3.0
        m = pid.stability_margins_type1(a, K)
        wc = m["crossover_rad_s"]
        self.assertAlmostEqual(wc * wc * (wc * wc + a * a), K * K, delta=1e-9)

    def test_more_gain_more_phase_margin(self):
        # Larger K raises the crossover frequency and lowers the PM
        m1 = pid.stability_margins_type1(2.0, 1.0)
        m2 = pid.stability_margins_type1(2.0, 4.0)
        self.assertGreater(m2["crossover_rad_s"], m1["crossover_rad_s"])
        self.assertLess(m2["phase_margin_deg"], m1["phase_margin_deg"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pid.stability_margins_type1(0.0, 2.0)
        with self.assertRaises(ValueError):
            pid.stability_margins_type1(2.0, 0.0)


class DiscreteDerivativeTest(unittest.TestCase):
    def test_backward_difference(self):
        # (5 - 3)/0.5 = 4
        self.assertAlmostEqual(
            pid.discrete_derivative(5.0, 3.0, 0.5), 4.0, delta=1e-12)

    def test_zero_change_zero_derivative(self):
        self.assertEqual(pid.discrete_derivative(3.0, 3.0, 0.1), 0.0)

    def test_invalid_dt_raises(self):
        with self.assertRaises(ValueError):
            pid.discrete_derivative(5.0, 3.0, 0.0)
        with self.assertRaises(ValueError):
            pid.discrete_derivative(5.0, 3.0, -0.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
