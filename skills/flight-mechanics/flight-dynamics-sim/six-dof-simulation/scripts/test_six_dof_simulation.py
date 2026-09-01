#!/usr/bin/env python3
"""Gate 3 contract test: six degree of freedom rigid body simulation logic.

Exercises scripts/six_dof_simulation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - body-axis
translational and rotational equations of motion, Euler angle
kinematics, and one fourth order Runge Kutta propagation step.

Hand-computed analytic references:
- Level trimmed flight (forces cancel weight, no rates, level
  attitude) has an identically zero derivative, so RK4 leaves the
  state unchanged exactly.
- Pure pitch moment M = 2000 N m on Iyy = 5000 kg m^2 gives
  q_dot = 0.4 rad/s^2; after dt = 0.5 s with g = 0,
  q = 0.2 rad/s and theta = 0.05 rad (theta = 0.5 q_dot dt^2),
  every other component unchanged.
- Euler angle rates at phi = 30 deg, theta = 20 deg, p = 0.1,
  q = 0.2, r = 0.3: phi_dot = 0.230959264,
  theta_dot = 0.023205081, psi_dot = 0.382899273.
- Small angle check: at phi = 0.001, theta = 0.002 the Euler angle
  rates stay within 0.001 rad/s of p, q, r.
- RK4 on y' = -y from y(0) = 1 with h = 0.1 gives
  1 - h + h^2/2 - h^3/6 + h^4/24 = 0.9048375 versus
  exp(-0.1) = 0.9048374180 (error below 1e-6), and the error ratio
  between h = 0.1 and h = 0.05 is about 32 (fifth order local error).
- Energy consistency: pure translation with force X = 1000 N on
  m = 500 kg for dt = 1 s gives u = 2 m/s, kinetic energy 1000 J,
  equal to the work X * distance = 1000 J.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import six_dof_simulation_logic as sd  # noqa: E402

G = 9.80665


class EulerAngleRatesTest(unittest.TestCase):
    def test_known_values(self):
        # phi = 30 deg, theta = 20 deg, p = 0.1, q = 0.2, r = 0.3.
        phi_dot, theta_dot, psi_dot = sd.euler_angle_rates(
            0.1, 0.2, 0.3, math.radians(30.0), math.radians(20.0)
        )
        self.assertAlmostEqual(phi_dot, 0.230959264, places=6)
        self.assertAlmostEqual(theta_dot, 0.023205081, places=6)
        self.assertAlmostEqual(psi_dot, 0.382899273, places=6)

    def test_small_angle_approximation(self):
        # At phi = 0.001, theta = 0.002 the rates are within 0.001 of
        # the body angular rates p, q, r.
        phi_dot, theta_dot, psi_dot = sd.euler_angle_rates(
            0.1, 0.2, 0.3, 0.001, 0.002
        )
        self.assertAlmostEqual(phi_dot, 0.1, delta=0.001)
        self.assertAlmostEqual(theta_dot, 0.2, delta=0.001)
        self.assertAlmostEqual(psi_dot, 0.3, delta=0.001)

    def test_level_attitude_rates_are_p_q_r(self):
        # phi = theta = 0: phi_dot = p, theta_dot = q, psi_dot = r.
        self.assertEqual(
            sd.euler_angle_rates(0.1, 0.2, 0.3, 0.0, 0.0),
            (0.1, 0.2, 0.3),
        )

    def test_gimbal_lock(self):
        with self.assertRaises(ValueError):
            sd.euler_angle_rates(0.1, 0.2, 0.3, 0.0, math.pi / 2.0)


class BodyAxisDerivativeTest(unittest.TestCase):
    def test_trimmed_level_flight_derivative_is_zero(self):
        # Z = -m g cancels weight, level attitude, zero rates: the
        # full nine-component derivative is identically zero.
        state = (100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        forces = (0.0, 0.0, -50000.0 * G)
        moments = (0.0, 0.0, 0.0)
        deriv = sd.body_axis_derivative(state, forces, moments, 50000.0,
                                        (100000.0, 500000.0, 800000.0))
        for d in deriv:
            self.assertEqual(d, 0.0)

    def test_pure_pitch_moment_angular_acceleration(self):
        # M = 2000 on Iyy = 5000 gives q_dot = 0.4 rad/s^2; the other
        # rotational accelerations are zero because p = r = 0.
        state = (100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        forces = (0.0, 0.0, -50000.0 * G)
        deriv = sd.body_axis_derivative(state, forces, (0.0, 2000.0, 0.0),
                                        50000.0, (100000.0, 5000.0, 800000.0))
        self.assertAlmostEqual(deriv[4], 0.4, places=12)
        self.assertEqual(deriv[3], 0.0)
        self.assertEqual(deriv[5], 0.0)

    def test_gyroscopic_coupling_sign(self):
        # Torque-free with p = 1, q = 1, r = 0 and
        # I = (100, 200, 300): the (Ixx - Iyy) p q term gives
        # r_dot = (100 - 200) / 300 = -1/3; p_dot and q_dot are zero
        # because their gyroscopic terms use q r and r p.
        state = (0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0)
        deriv = sd.body_axis_derivative(state, (0.0, 0.0, 0.0),
                                        (0.0, 0.0, 0.0),
                                        1000.0, (100.0, 200.0, 300.0),
                                        g=0.0)
        self.assertEqual(deriv[3], 0.0)
        self.assertEqual(deriv[4], 0.0)
        self.assertAlmostEqual(deriv[5], -1.0 / 3.0, places=12)

    def test_validation(self):
        with self.assertRaises(ValueError):
            sd.body_axis_derivative((0.0,) * 9, (0.0, 0.0, 0.0),
                                    (0.0, 0.0, 0.0), -1.0,
                                    (1.0, 1.0, 1.0))
        with self.assertRaises(ValueError):
            sd.body_axis_derivative((0.0,) * 9, (0.0, 0.0, 0.0),
                                    (0.0, 0.0, 0.0), 1.0,
                                    (0.0, 1.0, 1.0))


class Rk4PropagationTest(unittest.TestCase):
    def test_trimmed_state_stays_constant(self):
        # Zero derivative: one RK4 step reproduces the state exactly.
        state = (100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        forces = (0.0, 0.0, -50000.0 * G)
        moments = (0.0, 0.0, 0.0)
        new = sd.rk4_step(state, forces, moments, 50000.0,
                          (100000.0, 500000.0, 800000.0), dt=0.1)
        for a, b in zip(new, state):
            self.assertEqual(a, b)

    def test_pure_pitch_moment_step(self):
        # g = 0 and a state at rest isolate rotation: q_dot = 0.4
        # constant, so after dt = 0.5 s exactly q = 0.2 and
        # theta = 0.5 q_dot dt^2 = 0.05; all other components
        # unchanged (u = v = w = 0 kills the q u / p v coupling).
        state = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        forces = (0.0, 0.0, 0.0)
        moments = (0.0, 2000.0, 0.0)
        new = sd.rk4_step(state, forces, moments, 50000.0,
                          (100000.0, 5000.0, 800000.0), dt=0.5, g=0.0)
        self.assertAlmostEqual(new[4], 0.2, places=12)
        self.assertAlmostEqual(new[7], 0.05, places=12)
        for i in (0, 1, 2, 3, 5, 6, 8):
            self.assertEqual(new[i], 0.0)

    def test_rk4_order_and_convergence(self):
        # y' = -y, y(0) = 1: RK4 matches exp(-h) to the Taylor series
        # through h^4, error below 1e-6 at h = 0.1, and the error
        # ratio between h = 0.1 and h = 0.05 is about 32 (fifth order
        # local error).
        y1 = sd.rk4_core(lambda y: (-y[0],), (1.0,), 0.1)[0]
        self.assertAlmostEqual(y1, 0.9048375, places=7)
        self.assertLess(abs(y1 - math.exp(-0.1)), 1e-6)
        err1 = abs(sd.rk4_core(lambda y: (-y[0],), (1.0,), 0.1)[0]
                   - math.exp(-0.1))
        err2 = abs(sd.rk4_core(lambda y: (-y[0],), (1.0,), 0.05)[0]
                   - math.exp(-0.05))
        ratio = err1 / err2
        self.assertGreater(ratio, 24.0)
        self.assertLess(ratio, 40.0)

    def test_energy_consistency_translation(self):
        # Constant force X = 1000 N on m = 500 kg, g = 0, dt = 1 s:
        # u = a dt = 2 m/s exactly, kinetic energy 0.5 m u^2 = 1000 J,
        # and the work X * distance with distance = 0.5 a dt^2 = 1 m is
        # also 1000 J.
        state = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        new = sd.rk4_step(state, (1000.0, 0.0, 0.0), (0.0, 0.0, 0.0),
                          500.0, (100.0, 200.0, 300.0), dt=1.0, g=0.0)
        self.assertAlmostEqual(new[0], 2.0, places=12)
        ke = sd.kinetic_energy(new, 500.0, (100.0, 200.0, 300.0))
        self.assertAlmostEqual(ke, 1000.0, places=6)
        self.assertEqual(ke, 1000.0 * 1.0)


class StateVectorTest(unittest.TestCase):
    def test_state_vector_documented(self):
        self.assertEqual(
            sd.STATE_NAMES,
            ("u", "v", "w", "p", "q", "r", "phi", "theta", "psi"),
        )

    def test_kinetic_energy_known_value(self):
        # u = 3, v = 4, p = 1, q = 2, r = 3 on m = 10,
        # I = (2, 3, 4): translational 0.5 * 10 * 25 = 125 J,
        # rotational 0.5 * (2 + 12 + 36) = 25 J, total 150 J.
        ke = sd.kinetic_energy((3.0, 4.0, 0.0, 1.0, 2.0, 3.0,
                                0.0, 0.0, 0.0), 10.0, (2.0, 3.0, 4.0))
        self.assertAlmostEqual(ke, 150.0, places=12)


if __name__ == "__main__":
    unittest.main()
