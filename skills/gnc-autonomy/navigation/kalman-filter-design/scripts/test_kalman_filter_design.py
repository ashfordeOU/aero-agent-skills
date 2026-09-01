#!/usr/bin/env python3
"""Gate 3 contract test: discrete-time Kalman filter design.

Exercises scripts/kalman_filter_design_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (scalar
discrete-time Kalman filter: predict step, innovation and innovation
variance, Kalman gain, corrected state and covariance, batch filter
trajectory, steady-state covariance; invalid inputs raise ValueError).

Anchors (constant-position model f = 1, unit measurement h = 1,
q = 0.1, r = 1.0, starting at x0 = 0, p0 = 1.0; independent
hand arithmetic):
- predict(0, 1.0, 1, 0.1)      = (0.0, 1.1)
- update(0, 1.1, 1.0, 1, 1)    : innovation 1.0, variance 2.1,
  gain 1.1/2.1 = 11/21, state 11/21, covariance 11/21
- step 2 from (11/21, 11/21) with z = 2.0:
  predicted covariance 131/210, innovation 31/21,
  variance 341/210, gain 131/341, state 12/11,
  covariance 131/341
- steady a-priori covariance: positive root of
  P = P - P^2/(P+1) + 0.1, i.e. (0.1 + sqrt(0.41)) / 2 =
  0.3701562118716424; the a-posteriori covariance settles at
  (sqrt(0.41) - 0.1) / 2 = 0.27015621187164246 and its gain
  K = P_pred/(P_pred + 1) equals the same value at steady state.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import kalman_filter_design_logic as kf  # noqa: E402

STEADY_P = (0.1 + math.sqrt(0.41)) / 2.0  # 0.3701562118716424 (a-priori root)
POST_P = (math.sqrt(0.41) - 0.1) / 2.0  # 0.27015621187164246 (a-posteriori root)


class PredictTest(unittest.TestCase):
    def test_anchor_predict(self):
        x_pred, p_pred = kf.predict(0.0, 1.0, 1.0, 0.1)
        self.assertAlmostEqual(x_pred, 0.0)
        self.assertAlmostEqual(p_pred, 1.1)

    def test_predict_grows_covariance_with_q(self):
        x_pred, p_pred = kf.predict(2.0, 1.0, 1.0, 0.5)
        self.assertAlmostEqual(x_pred, 2.0)
        self.assertAlmostEqual(p_pred, 1.5)

    def test_predict_scales_state_by_f(self):
        x_pred, _p_pred = kf.predict(3.0, 1.0, 0.5, 0.0)
        self.assertAlmostEqual(x_pred, 1.5)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            kf.predict(0.0, -0.1, 1.0, 0.1)
        with self.assertRaises(ValueError):
            kf.predict(0.0, 1.0, 1.0, -0.1)
        with self.assertRaises(ValueError):
            kf.predict("bad", 1.0, 1.0, 0.1)


class UpdateTest(unittest.TestCase):
    def test_anchor_update_step1(self):
        upd = kf.update(0.0, 1.1, 1.0, 1.0, 1.0)
        self.assertAlmostEqual(upd["innovation"], 1.0)
        self.assertAlmostEqual(upd["innovation_variance"], 2.1)
        self.assertAlmostEqual(upd["gain"], 11.0 / 21.0)
        self.assertAlmostEqual(upd["state"], 11.0 / 21.0)
        self.assertAlmostEqual(upd["covariance"], 11.0 / 21.0)

    def test_anchor_update_step2(self):
        upd = kf.update(11.0 / 21.0, 131.0 / 210.0, 2.0, 1.0, 1.0)
        self.assertAlmostEqual(upd["innovation"], 31.0 / 21.0)
        self.assertAlmostEqual(upd["innovation_variance"], 341.0 / 210.0)
        self.assertAlmostEqual(upd["gain"], 131.0 / 341.0)
        self.assertAlmostEqual(upd["state"], 12.0 / 11.0)
        self.assertAlmostEqual(upd["covariance"], 131.0 / 341.0)

    def test_gain_bounds(self):
        # K = h * p / (h^2 p + r) lies in [0, 1/h] for h > 0.
        self.assertGreaterEqual(kf.kalman_gain(5.0, 1.0, 1.0), 0.0)
        self.assertLessEqual(kf.kalman_gain(5.0, 1.0, 1.0), 1.0)
        self.assertAlmostEqual(kf.kalman_gain(0.0, 1.0, 1.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            kf.update(0.0, -1.0, 1.0, 1.0, 1.0)
        with self.assertRaises(ValueError):
            kf.update(0.0, 1.0, 1.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            kf.update(0.0, 1.0, 1.0, 1.0, -0.5)


class KalmanStepTest(unittest.TestCase):
    def test_anchor_full_step(self):
        step = kf.kalman_step(0.0, 1.0, 1.0, 1.0, 1.0, 0.1, 1.0)
        self.assertAlmostEqual(step["predicted_state"], 0.0)
        self.assertAlmostEqual(step["predicted_covariance"], 1.1)
        self.assertAlmostEqual(step["innovation"], 1.0)
        self.assertAlmostEqual(step["innovation_variance"], 2.1)
        self.assertAlmostEqual(step["gain"], 11.0 / 21.0)
        self.assertAlmostEqual(step["state"], 11.0 / 21.0)
        self.assertAlmostEqual(step["covariance"], 11.0 / 21.0)

    def test_defaults_are_constant_position_unit_measurement(self):
        # Default f=1, h=1, q=0, r=1 must reproduce the anchor with
        # q=0: predicted covariance equals prior covariance.
        step = kf.kalman_step(0.0, 1.0, 1.0)
        self.assertAlmostEqual(step["predicted_covariance"], 1.0)
        self.assertAlmostEqual(step["gain"], 0.5)
        self.assertAlmostEqual(step["state"], 0.5)
        self.assertAlmostEqual(step["covariance"], 0.5)


class RunFilterTest(unittest.TestCase):
    def test_anchor_two_measurements(self):
        res = kf.run_filter([1.0, 2.0], 0.0, 1.0, 1.0, 1.0, 0.1, 1.0)
        self.assertEqual(len(res["states"]), 2)
        self.assertAlmostEqual(res["states"][0], 11.0 / 21.0)
        self.assertAlmostEqual(res["states"][1], 12.0 / 11.0)
        self.assertAlmostEqual(res["covariances"][0], 11.0 / 21.0)
        self.assertAlmostEqual(res["covariances"][1], 131.0 / 341.0)
        self.assertAlmostEqual(res["gains"][0], 11.0 / 21.0)
        self.assertAlmostEqual(res["gains"][1], 131.0 / 341.0)
        self.assertAlmostEqual(res["innovations"][0], 1.0)
        self.assertAlmostEqual(res["innovations"][1], 31.0 / 21.0)

    def test_converges_to_steady_state(self):
        # Constant measurements of 1.0 must drive the a-posteriori
        # covariance to the posterior root, and the predicted
        # covariance (posterior + q, f = 1) to the DARE root.
        res = kf.run_filter([1.0] * 50, 0.0, 10.0, 1.0, 1.0, 0.1, 1.0)
        self.assertAlmostEqual(res["covariances"][-1], POST_P, delta=1e-4)
        self.assertAlmostEqual(res["covariances"][-1] + 0.1, STEADY_P, delta=1e-4)
        self.assertAlmostEqual(
            res["gains"][-1], STEADY_P / (STEADY_P + 1.0), delta=1e-4
        )

    def test_high_measurement_trust_tracks_measurement(self):
        # Tiny measurement noise r against large prior p0: the
        # corrected state must sit essentially on the measurement.
        res = kf.run_filter([7.0], 0.0, 100.0, 1.0, 1.0, 0.0, 1e-6)
        self.assertAlmostEqual(res["states"][0], 7.0, places=4)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            kf.run_filter([], 0.0, 1.0)
        with self.assertRaises(ValueError):
            kf.run_filter([1.0, "bad"], 0.0, 1.0)


class SteadyStateTest(unittest.TestCase):
    def test_anchor_steady_state(self):
        self.assertAlmostEqual(
            kf.steady_state_covariance(1.0, 1.0, 0.1, 1.0), STEADY_P, places=12
        )

    def test_steady_gain_from_covariance(self):
        p = kf.steady_state_covariance(1.0, 1.0, 0.1, 1.0)
        k = kf.kalman_gain(p, 1.0, 1.0)
        self.assertAlmostEqual(k, 0.27015621187164246, places=12)

    def test_no_process_noise_converges_to_zero(self):
        # q = 0 with a non-diverging model: perfect estimation of a
        # constant state, covariance goes to zero.
        self.assertAlmostEqual(
            kf.steady_state_covariance(1.0, 1.0, 0.0, 1.0), 0.0, places=12
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            kf.steady_state_covariance(1.0, 0.0, 0.1, 1.0)
        with self.assertRaises(ValueError):
            kf.steady_state_covariance(1.0, 1.0, -0.1, 1.0)
        with self.assertRaises(ValueError):
            kf.steady_state_covariance(1.0, 1.0, 0.1, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
