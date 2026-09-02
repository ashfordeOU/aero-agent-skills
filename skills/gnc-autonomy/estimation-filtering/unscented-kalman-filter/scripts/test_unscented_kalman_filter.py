#!/usr/bin/env python3
"""Contract test for the Unscented Kalman Filter leaf.

Stdlib unittest only (gate 3): imports the standard library and the
sibling logic module unscented_kalman_filter_logic.py. Deterministic
(no network, fixed-seed noise). Covers the gate 3 contract:

  - sigma-point generation properties (weights, moment reconstruction,
    symmetry about the mean)
  - predict and update through the scaled unscented transform
  - linear-model equivalence with the closed-form Kalman filter
  - convergence of the full filter on a known nonlinear problem
    (bearing/range tracking of a constant-velocity target)
  - consistency metrics (NEES, innovation covariance)

Run standalone:
    python3 scripts/test_unscented_kalman_filter.py
"""

import math
import random
import unittest

from unscented_kalman_filter_logic import (
    UKFFilter,
    bearing_range_measurement,
    constant_velocity_dynamics,
    generate_sigma_points,
    mat_add,
    mat_mul,
    mat_sub,
    mat_transpose,
    mat_trace,
    mat_vec_mul,
    nees,
    predict,
    sigma_point_weights,
    update,
    vec_add,
    vec_dot,
    vec_sub,
    weighted_moments,
)

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

N = 4  # state dimension for the tracking problem


def linear_dynamics(x, dt=1.0):
    """Linear constant-velocity dynamics as a callable for predict()."""
    return constant_velocity_dynamics(x, dt)


def linear_measurement(x):
    """Linear measurement of the first two state components."""
    return [x[0], x[1]]


def identity_dynamics(x):
    """Identity dynamics: useful for moment-reconstruction checks."""
    return list(x)


# ---------------------------------------------------------------------------
# Sigma-point generation
# ---------------------------------------------------------------------------


class TestSigmaPoints(unittest.TestCase):
    def setUp(self):
        self.x = [2.0, -1.0, 0.5, 3.0]
        self.p = [
            [4.0, 0.5, 0.0, 0.0],
            [0.5, 2.0, 0.2, 0.0],
            [0.0, 0.2, 1.0, 0.1],
            [0.0, 0.0, 0.1, 0.5],
        ]

    def test_weight_sums_to_one(self):
        # Mean weights always sum to 1. Covariance weights sum to
        # 2 + beta - alpha^2 in the scaled transform (the beta term is
        # added only to wc[0]), so only wm is checked against 1.
        wm, wc, gamma = sigma_point_weights(N, 1e-3, 2.0, 0.0)
        self.assertAlmostEqual(sum(wm), 1.0, places=9)
        self.assertAlmostEqual(sum(wc), 2.0 + 2.0 - 1e-6, places=6)
        self.assertEqual(len(wm), 2 * N + 1)
        self.assertEqual(len(wc), 2 * N + 1)
        self.assertGreater(gamma, 0.0)

    def test_weight_consistency_scaled_transform(self):
        # wc[0] = wm[0] + (1 - alpha^2 + beta); wm[i] == wc[i] for i > 0
        alpha, beta, kappa = 0.5, 2.0, 1.0
        wm, wc, _ = sigma_point_weights(N, alpha, beta, kappa)
        expected = wm[0] + (1.0 - alpha * alpha + beta)
        self.assertAlmostEqual(wc[0], expected, places=12)
        for i in range(1, 2 * N + 1):
            self.assertAlmostEqual(wm[i], wc[i], places=12)

    def test_two_plus_one_points(self):
        points = generate_sigma_points(self.x, self.p, 1e-3, 2.0, 0.0)
        self.assertEqual(len(points), 2 * N + 1)
        for pt in points:
            self.assertEqual(len(pt), N)

    def test_central_point_is_mean(self):
        points = generate_sigma_points(self.x, self.p, 1e-3, 2.0, 0.0)
        for a, b in zip(points[0], self.x):
            self.assertAlmostEqual(a, b, places=12)

    def test_sigma_points_symmetric_about_mean(self):
        # X[i] - x == -(X[n+i] - x) for i = 1..n
        points = generate_sigma_points(self.x, self.p, 0.3, 2.0, 1.0)
        for i in range(1, N + 1):
            pos = vec_sub(points[i], self.x)
            neg = vec_sub(points[N + i], self.x)
            for a, b in zip(pos, neg):
                self.assertAlmostEqual(a, -b, places=12)

    def test_weighted_mean_reconstructs_input_mean(self):
        wm, wc, _ = sigma_point_weights(N, 0.3, 2.0, 1.0)
        points = generate_sigma_points(self.x, self.p, 0.3, 2.0, 1.0)
        mean, _ = weighted_moments(points, wm, wc)
        for a, b in zip(mean, self.x):
            self.assertAlmostEqual(a, b, places=9)

    def test_weighted_covariance_reconstructs_input_covariance(self):
        wm, wc, _ = sigma_point_weights(N, 0.3, 2.0, 1.0)
        points = generate_sigma_points(self.x, self.p, 0.3, 2.0, 1.0)
        _, cov = weighted_moments(points, wm, wc)
        for i in range(N):
            for j in range(N):
                self.assertAlmostEqual(cov[i][j], self.p[i][j], places=9)


# ---------------------------------------------------------------------------
# Predict and update
# ---------------------------------------------------------------------------


class TestPredictUpdate(unittest.TestCase):
    def setUp(self):
        self.x = [10.0, 20.0, 1.0, 0.5]
        self.p = [
            [9.0, 0.0, 0.0, 0.0],
            [0.0, 9.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        self.q = [
            [0.01, 0.0, 0.0, 0.0],
            [0.0, 0.01, 0.0, 0.0],
            [0.0, 0.0, 0.001, 0.0],
            [0.0, 0.0, 0.0, 0.001],
        ]
        self.r = [[1.0, 0.0], [0.0, 1.0]]
        self.dt = 1.0

    def test_predict_matches_linear_kalman(self):
        # For a linear model the UKF predict equals the closed-form KF:
        # x_pred = F x, P_pred = F P F^T + Q with F = [[1, dt, 0, 0],
        # [0, 1, 0, 0], [0, 0, 1, dt], [0, 0, 0, 1]].
        f_mat = [
            [1.0, 0.0, self.dt, 0.0],
            [0.0, 1.0, 0.0, self.dt],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
        x_pred_kf = mat_vec_mul(f_mat, self.x)
        p_pred_kf = mat_add(
            mat_mul(mat_mul(f_mat, self.p), mat_transpose(f_mat)), self.q
        )
        x_pred, p_pred = predict(
            self.x, self.p, linear_dynamics, self.q, alpha=1e-3, beta=2.0, kappa=0.0
        )
        for a, b in zip(x_pred, x_pred_kf):
            self.assertAlmostEqual(a, b, places=9)
        for i in range(N):
            for j in range(N):
                self.assertAlmostEqual(p_pred[i][j], p_pred_kf[i][j], places=9)

    def test_predict_covariance_grows_with_process_noise(self):
        x_pred, p_pred = predict(
            self.x, self.p, linear_dynamics, self.q, alpha=1e-3, beta=2.0, kappa=0.0
        )
        trace_pred = mat_trace(p_pred)
        trace_prev = mat_trace(self.p)
        self.assertGreater(trace_pred, trace_prev)  # Q adds uncertainty

    def test_identity_dynamics_preserve_moments(self):
        # With f = identity the predict step must reproduce x and P + Q.
        x_pred, p_pred = predict(
            self.x, self.p, identity_dynamics, self.q, alpha=0.5, beta=2.0, kappa=1.0
        )
        for a, b in zip(x_pred, self.x):
            self.assertAlmostEqual(a, b, places=9)
        expected = mat_add(self.p, self.q)
        for i in range(N):
            for j in range(N):
                self.assertAlmostEqual(p_pred[i][j], expected[i][j], places=9)

    def test_update_matches_linear_kalman(self):
        # Linear measurement H = [[1,0,0,0],[0,1,0,0]]: the UKF update
        # must equal the closed-form KF update.
        z = [12.0, 18.0]
        h_mat = [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
        ]
        s_kf = mat_add(
            mat_mul(mat_mul(h_mat, self.p), mat_transpose(h_mat)), self.r
        )
        s_inv = [[s_kf[0][0] / (s_kf[0][0] * s_kf[1][1] - s_kf[0][1] * s_kf[1][0]),
                  -s_kf[0][1] / (s_kf[0][0] * s_kf[1][1] - s_kf[0][1] * s_kf[1][0])],
                 [-s_kf[1][0] / (s_kf[0][0] * s_kf[1][1] - s_kf[0][1] * s_kf[1][0]),
                  s_kf[1][1] / (s_kf[0][0] * s_kf[1][1] - s_kf[0][1] * s_kf[1][0])]]
        k_kf = mat_mul(mat_mul(self.p, mat_transpose(h_mat)), s_inv)
        innov_kf = vec_sub(z, mat_vec_mul(h_mat, self.x))
        x_new_kf = vec_add(self.x, mat_vec_mul(k_kf, innov_kf))
        p_new_kf = mat_sub(
            self.p, mat_mul(mat_mul(k_kf, s_kf), mat_transpose(k_kf))
        )
        x_new, p_new, z_mean, s, k = update(
            self.x, self.p, z, linear_measurement, self.r,
            alpha=1e-3, beta=2.0, kappa=0.0,
        )
        for a, b in zip(x_new, x_new_kf):
            self.assertAlmostEqual(a, b, places=8)
        for i in range(N):
            for j in range(N):
                self.assertAlmostEqual(p_new[i][j], p_new_kf[i][j], places=8)
        for a, b in zip(z_mean, mat_vec_mul(h_mat, self.x)):
            self.assertAlmostEqual(a, b, places=8)

    def test_innovation_covariance_symmetric_positive(self):
        z = [12.0, 18.0]
        _, _, _, s, _ = update(
            self.x, self.p, z, linear_measurement, self.r,
            alpha=1e-3, beta=2.0, kappa=0.0,
        )
        self.assertAlmostEqual(s[0][1], s[1][0], places=12)
        det = s[0][0] * s[1][1] - s[0][1] * s[1][0]
        self.assertGreater(s[0][0], 0.0)
        self.assertGreater(s[1][1], 0.0)
        self.assertGreater(det, 0.0)

    def test_update_reduces_uncertainty(self):
        z = [12.0, 18.0]
        x_new, p_new, _, _, _ = update(
            self.x, self.p, z, linear_measurement, self.r,
            alpha=1e-3, beta=2.0, kappa=0.0,
        )
        self.assertLess(mat_trace(p_new), mat_trace(self.p))

    def test_stateful_filter_steps(self):
        filt = UKFFilter(
            self.x, self.p, linear_dynamics, linear_measurement,
            self.q, self.r, alpha=1e-3, beta=2.0, kappa=0.0,
        )
        x1, p1 = filt.predict()
        x2, p2 = filt.update([11.0, 19.0])
        self.assertEqual(len(x1), N)
        self.assertEqual(len(x2), N)
        self.assertIsNotNone(filt.innovation)
        self.assertIsNotNone(filt.s)
        self.assertIsNotNone(filt.k)


# ---------------------------------------------------------------------------
# End-to-end convergence on a nonlinear problem (bearing/range tracking)
# ---------------------------------------------------------------------------


class TestBearingRangeTracking(unittest.TestCase):
    """UKF must converge on a nonlinear measurement model (range and
    bearing from cartesian position), where a linear filter would
    struggle. Deterministic: fixed-seed measurement noise."""

    def run_tracking(self, seed=7, steps=50):
        rng = random.Random(seed)
        dt = 1.0
        # True constant-velocity target.
        x_true = [100.0, 50.0, 2.0, 1.0]
        x0 = [95.0, 55.0, 0.0, 0.0]  # deliberately offset initial guess
        p0 = [
            [100.0, 0.0, 0.0, 0.0],
            [0.0, 100.0, 0.0, 0.0],
            [0.0, 0.0, 4.0, 0.0],
            [0.0, 0.0, 0.0, 4.0],
        ]
        # Dynamics noise: small, target truly constant velocity.
        q = [
            [0.05, 0.0, 0.0, 0.0],
            [0.0, 0.05, 0.0, 0.0],
            [0.0, 0.0, 0.01, 0.0],
            [0.0, 0.0, 0.0, 0.01],
        ]
        # Sensor: range sigma 1 m, bearing sigma 0.01 rad.
        r = [[1.0, 0.0], [0.0, 0.01 * 0.01]]

        filt = UKFFilter(
            x0, p0, lambda pt: constant_velocity_dynamics(pt, dt),
            bearing_range_measurement, q, r,
            alpha=1e-3, beta=2.0, kappa=0.0,
        )

        nees_values = []
        position_errors = []
        for _ in range(steps):
            # Advance the truth.
            x_true = constant_velocity_dynamics(x_true, dt)
            # Noisy measurement: range + bearing.
            truth_meas = bearing_range_measurement(x_true)
            z = [
                truth_meas[0] + rng.gauss(0.0, 1.0),
                truth_meas[1] + rng.gauss(0.0, 0.01),
            ]
            filt.step(z)
            nees_values.append(nees(filt.x, filt.p, x_true))
            err = math.hypot(filt.x[0] - x_true[0], filt.x[1] - x_true[1])
            position_errors.append(err)
        return filt, x_true, nees_values, position_errors

    def test_filter_converges_on_nonlinear_measurement(self):
        filt, x_true, _, position_errors = self.run_tracking()
        final_err = math.hypot(filt.x[0] - x_true[0], filt.x[1] - x_true[1])
        # Final position error well below the 100 m initial offset:
        # the UKF must have pulled the estimate onto the target.
        self.assertLess(final_err, 8.0)
        # Errors must shrink over the run: last-step error below the
        # first-step error (the filter converges from the offset guess).
        self.assertLess(position_errors[-1], position_errors[0])
        # Steady-state error bounded by the sensor noise level.
        late = sum(position_errors[-10:]) / 10.0
        self.assertLess(late, 3.0)

    def test_nees_stays_bounded(self):
        # A consistent filter keeps NEES near the state dimension (4).
        # Single-run values vary, but a broken filter diverges far above.
        _, _, nees_values, _ = self.run_tracking(seed=11)
        mean_nees = sum(nees_values) / len(nees_values)
        self.assertGreater(mean_nees, 0.0)
        self.assertLess(mean_nees, 40.0)
        self.assertLess(max(nees_values), 200.0)

    def test_nees_of_perfect_estimate_is_zero(self):
        # Sanity: NEES of the true state under any PD covariance is 0
        # only if estimate == truth; a zero deviation gives zero NEES.
        p = [[1.0, 0.0], [0.0, 1.0]]
        self.assertAlmostEqual(nees([1.0, 2.0], p, [1.0, 2.0]), 0.0, places=12)
        # A one-sigma deviation in one axis gives NEES ~ 1.
        val = nees([1.0, 2.0], p, [2.0, 2.0])
        self.assertAlmostEqual(val, 1.0, places=9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
