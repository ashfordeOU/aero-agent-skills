#!/usr/bin/env python3
"""Gate 3 contract test: extended Kalman filter logic.

Exercises scripts/extended_kalman_filter_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3. Covers the
central-difference Jacobians (linear functions recovered exactly), the
predict/update recursion against the hand-computed linear Kalman
filter for linear models, the zero-innovation case (state unchanged,
covariance reduced), the singular innovation covariance edge case,
convergence of a nonlinear range/bearing tracking run on a
constant-velocity target, the stateful EKFFilter, the batch runner,
and determinism.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import extended_kalman_filter_logic as ekf  # noqa: E402


def mat_vec(m, v):
    return [sum(mi[j] * v[j] for j in range(len(v))) for mi in m]


def mat_transpose(m):
    return [[m[i][j] for i in range(len(m))] for j in range(len(m[0]))]


def mat_mul(a, b):
    return [[sum(ai[k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for ai in a]


def mat_add(a, b):
    return [[ai + bi for ai, bi in zip(ra, rb)] for ra, rb in zip(a, b)]


def mat_sub(a, b):
    return [[ai - bi for ai, bi in zip(ra, rb)] for ra, rb in zip(a, b)]


def vec_sub(a, b):
    return [ai - bi for ai, bi in zip(a, b)]


def trace(m):
    return sum(m[i][i] for i in range(len(m)))


class JacobianTest(unittest.TestCase):
    def test_linear_vector_function_jacobian_exact(self):
        def f(x):
            return [2.0 * x[0] + 3.0 * x[1], x[0] - x[1]]

        J = ekf.jacobian(f, [1.0, 2.0])
        for i in range(2):
            for j in range(2):
                self.assertAlmostEqual(J[i][j], [[2.0, 3.0], [1.0, -1.0]][i][j], places=5)

    def test_scalar_quadratic_jacobian(self):
        J = ekf.jacobian(lambda x: x[0] * x[0], [3.0])
        self.assertAlmostEqual(J[0][0], 6.0, places=5)

    def test_jacobian_f_and_h_aliases(self):
        def f(x):
            return [x[0] + 0.1 * math.sin(x[0])]

        x = [2.0]
        self.assertEqual(ekf.jacobian_f(f, x), ekf.jacobian(f, x))
        self.assertEqual(ekf.jacobian_h(f, x), ekf.jacobian(f, x))
        self.assertAlmostEqual(ekf.jacobian_f(f, x)[0][0], 1.0 + 0.1 * math.cos(2.0), places=5)

    def test_sin_derivative(self):
        J = ekf.jacobian(lambda x: [math.sin(x[0])], [0.5])
        self.assertAlmostEqual(J[0][0], math.cos(0.5), places=5)


class LinearAgreementTest(unittest.TestCase):
    """EKF must reproduce the linear Kalman filter exactly for linear models."""

    F = [[1.0, 0.1], [0.0, 1.0]]  # position/velocity with dt = 0.1
    H = [[1.0, 0.0]]  # position measurement
    Q = [[0.01, 0.0], [0.0, 0.02]]
    R = [[0.25]]

    def test_predict_matches_closed_form(self):
        x = [2.0, 1.0]
        P = [[1.0, 0.1], [0.1, 0.5]]
        out = ekf.ekf_predict(x, P, lambda s: mat_vec(self.F, s), self.Q)
        x_pred = mat_vec(self.F, x)
        P_pred = mat_add(mat_mul(mat_mul(self.F, P), mat_transpose(self.F)), self.Q)
        for i in range(2):
            self.assertAlmostEqual(out["x"][i], x_pred[i], places=8)
            for j in range(2):
                self.assertAlmostEqual(out["P"][i][j], P_pred[i][j], places=8)
        # F is numeric (finite differences), so it matches the exact
        # matrix to finite-difference tolerance.
        for i in range(2):
            for j in range(2):
                self.assertAlmostEqual(out["F"][i][j], self.F[i][j], places=6)

    def test_update_matches_closed_form(self):
        x = [2.09, 1.0]
        P = [[0.93, 0.09], [0.09, 0.52]]
        z = [2.1]
        out = ekf.ekf_update(x, P, z, lambda s: mat_vec(self.H, s), self.R)
        hx = mat_vec(self.H, x)
        y = vec_sub(z, hx)
        S = mat_add(mat_mul(mat_mul(self.H, P), mat_transpose(self.H)), self.R)
        s = S[0][0]
        # Scalar measurement: K = P H^T / S, x_new = x + K y, P_new = P - K S K^T
        KH = [[P[i][0] / s for _ in range(1)] for i in range(2)]
        K = [[P[i][0] / s] for i in range(2)]
        x_new = [x[i] + K[i][0] * y[0] for i in range(2)]
        P_new = mat_sub(P, mat_mul(mat_mul(K, S), mat_transpose(K)))
        for i in range(2):
            self.assertAlmostEqual(out["x"][i], x_new[i], places=8)
            for j in range(2):
                self.assertAlmostEqual(out["P"][i][j], P_new[i][j], places=8)
        self.assertAlmostEqual(out["S"][0][0], s, places=8)
        self.assertAlmostEqual(out["y"][0], y[0], places=8)

    def test_innovation_is_z_minus_predicted_measurement(self):
        x = [1.5, 0.0]
        P = [[1.0, 0.0], [0.0, 1.0]]
        out = ekf.ekf_update(x, P, [1.7], lambda s: mat_vec(self.H, s), self.R)
        self.assertAlmostEqual(out["y"][0], 1.7 - 1.5, places=8)


class ZeroInnovationTest(unittest.TestCase):
    def test_zero_innovation_leaves_state_unchanged(self):
        x = [2.0]
        P = [[1.0]]
        z = ekf.scalar_nonlinear_measurement([2.0])  # exact predicted measurement
        out = ekf.ekf_update(x, P, z, ekf.scalar_nonlinear_measurement, [[0.25]])
        self.assertEqual(out["y"], [0.0])
        self.assertEqual(out["x"], [2.0])
        # Covariance still shrinks: P_new = P - K S K^T < P.
        self.assertLess(trace(out["P"]), trace(P))

    def test_zero_innovation_through_filter_step(self):
        filt = ekf.EKFFilter(
            [2.0], [[1.0]],
            ekf.scalar_nonlinear_dynamics,
            ekf.scalar_nonlinear_measurement,
            [[0.01]], [[0.25]],
        )
        # Feed the measurement of the *predicted* state so the
        # innovation is exactly zero after the predict step.
        pred = ekf.ekf_predict(
            filt.x, filt.P, ekf.scalar_nonlinear_dynamics, [[0.01]]
        )
        filt.step(ekf.scalar_nonlinear_measurement(pred["x"]))
        self.assertEqual(filt.innovation, [0.0])


class SingularSTest(unittest.TestCase):
    def test_singular_innovation_covariance_raises(self):
        # h(x) = x^2 has H = 0 at x = 0; with R = 0, S = 0 -> singular.
        with self.assertRaises(ValueError):
            ekf.ekf_update([0.0], [[1.0]], [1.0], lambda s: [s[0] * s[0]], [[0.0]])

    def test_mat_inverse_singular_raises(self):
        with self.assertRaises(ValueError):
            ekf.mat_inverse([[0.0]])
        with self.assertRaises(ValueError):
            ekf.mat_inverse([[1.0, 2.0], [2.0, 4.0]])

    def test_mat_inverse_nonsquare_raises(self):
        with self.assertRaises(ValueError):
            ekf.mat_inverse([[1.0, 2.0]])

    def test_mat_inverse_known_result(self):
        inv = ekf.mat_inverse([[4.0, 7.0], [2.0, 6.0]])
        self.assertAlmostEqual(inv[0][0], 0.6, places=8)
        self.assertAlmostEqual(inv[0][1], -0.7, places=8)
        self.assertAlmostEqual(inv[1][0], -0.2, places=8)
        self.assertAlmostEqual(inv[1][1], 0.4, places=8)


class ConvergenceTest(unittest.TestCase):
    DT = 0.1
    N = 40
    TRUE0 = [10.0, 5.0, 2.0, 0.5]
    P0 = [[1.0, 0.0, 0.0, 0.0],
          [0.0, 1.0, 0.0, 0.0],
          [0.0, 0.0, 0.5, 0.0],
          [0.0, 0.0, 0.0, 0.5]]
    Q = [[1e-4, 0.0, 0.0, 0.0],
         [0.0, 1e-4, 0.0, 0.0],
         [0.0, 0.0, 1e-4, 0.0],
         [0.0, 0.0, 0.0, 1e-4]]
    R = [[1e-3, 0.0], [0.0, 1e-4]]

    def _true_trajectory(self):
        states = [self.TRUE0]
        for _ in range(self.N):
            states.append(ekf.constant_velocity_dynamics(states[-1], self.DT))
        return states

    def test_bearing_range_tracking_converges(self):
        states = self._true_trajectory()
        zs = [ekf.bearing_range_measurement(s) for s in states[1:]]
        x0 = [9.5, 5.5, 1.8, 0.4]
        out = ekf.run_ekf(
            zs, x0, self.P0,
            lambda s: ekf.constant_velocity_dynamics(s, self.DT),
            ekf.bearing_range_measurement,
            self.Q, self.R,
        )
        final = out[-1]["x"]
        true_final = states[-1]
        pos_err = math.hypot(final[0] - true_final[0], final[1] - true_final[1])
        self.assertLess(pos_err, 0.05)
        self.assertLess(trace(out[-1]["P"]), trace(self.P0))
        self.assertLess(final[2], 3.0)
        self.assertGreater(final[2], 1.0)

    def test_innovation_magnitude_decreases(self):
        states = self._true_trajectory()
        zs = [ekf.bearing_range_measurement(s) for s in states[1:]]
        x0 = [9.5, 5.5, 1.8, 0.4]
        out = ekf.run_ekf(
            zs, x0, self.P0,
            lambda s: ekf.constant_velocity_dynamics(s, self.DT),
            ekf.bearing_range_measurement,
            self.Q, self.R,
        )
        norms = [math.sqrt(sum(vi * vi for vi in step["y"])) for step in out]
        first_half = sum(norms[: self.N // 2]) / (self.N // 2)
        second_half = sum(norms[self.N // 2:]) / (self.N // 2)
        self.assertLess(second_half, first_half)


class FilterStatefulTest(unittest.TestCase):
    def test_step_populates_inspection_fields(self):
        filt = ekf.EKFFilter(
            [2.0], [[1.0]],
            ekf.scalar_nonlinear_dynamics,
            ekf.scalar_nonlinear_measurement,
            [[0.01]], [[0.25]],
        )
        filt.step([1.1])
        self.assertIsNotNone(filt.innovation)
        self.assertIsNotNone(filt.S)
        self.assertIsNotNone(filt.K)
        self.assertEqual(len(filt.K), 1)
        self.assertEqual(len(filt.K[0]), 1)

    def test_deterministic_across_runs(self):
        def run_once():
            return ekf.run_ekf(
                [[1.1], [1.15], [1.2], [1.25]],
                [2.0], [[1.0]],
                ekf.scalar_nonlinear_dynamics,
                ekf.scalar_nonlinear_measurement,
                [[0.01]], [[0.25]],
            )

        a = run_once()
        b = run_once()
        self.assertEqual(len(a), 4)
        for sa, sb in zip(a, b):
            self.assertEqual(sa["x"], sb["x"])
            self.assertEqual(sa["P"], sb["P"])
            self.assertEqual(sa["y"], sb["y"])

    def test_run_ekf_returns_one_entry_per_measurement(self):
        out = ekf.run_ekf(
            [[1.0], [1.1], [1.2]],
            [2.0], [[1.0]],
            ekf.scalar_nonlinear_dynamics,
            ekf.scalar_nonlinear_measurement,
            [[0.01]], [[0.25]],
        )
        self.assertEqual(len(out), 3)

    def test_scalar_measurement_accepts_bare_number(self):
        filt = ekf.EKFFilter(
            [2.0], [[1.0]],
            ekf.scalar_nonlinear_dynamics,
            ekf.scalar_nonlinear_measurement,
            [[0.01]], [[0.25]],
        )
        x = filt.step(1.1)
        self.assertEqual(len(x), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
