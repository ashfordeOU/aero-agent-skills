#!/usr/bin/env python3
"""Gate 3 contract test: alpha-beta tracking filter.

Exercises scripts/alpha_beta_filter_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (predict step,
residual, alpha-beta gain update, batch tracker trajectory,
steady-state gain selection from the smoothing factor and the
maneuverability index, tracking error metrics, stateful TrackFilter;
invalid inputs raise ValueError).

Anchors (independent hand arithmetic):
- predict(10, 2, 0.5) = (11.0, 2.0): position advances by dt * v.
- alpha = 1, beta = 1 reproduces the raw measurement: from
  (x, v) = (0, 0), dt = 1, z = 12: x_pred = 0, residual = 12,
  position = 12, velocity = 12.
- Constant-velocity track with alpha = 0.5 and beta = 1/6
  (Benedict-Bordner critical damping), dt = 1, measurements
  z = 1.0, 2.5, 3.5, 4.0, 5.0 of a target moving at 1 m/s:
  step 1: residual 1.0, position 0.5, velocity 1/6
  step 2: predicted position 2/3, residual 11/6,
          position 19/12, velocity 17/36
  step 3: predicted position 37/18, residual 13/9,
          position 25/9, velocity 77/108
  step 4: predicted position 377/108, residual 55/108,
          position 809/216, velocity 517/648
  step 5: predicted position 368/81, residual 37/81,
          position 773/162, velocity 1699/1944
  The velocity estimate rises from 0 toward the true 1 m/s.
- Steady-state gains: steady_state_gains(0.5) gives beta = 1/6;
  steady_state_gains(0.2) gives beta = 1/45; steady_state_gains(1.0)
  gives beta = 1.0.
- Kalata tracking index lambda = 2 (published reference values):
  alpha = (6 * sqrt(20) - 20) / 8 = 0.8541019662496845 and
  beta = (12 - 2 * sqrt(20)) / 4 = 0.7639320225002103; the gains
  satisfy beta = 2 * (2 - alpha) - 4 * sqrt(1 - alpha) and
  lambda = beta / sqrt(1 - alpha).
- tracking_errors([0, 1, 2], [0.1, 0.9, 2.2]): squares 0.01, 0.01,
  0.04, mean 0.02, rmse = sqrt(0.02) = 0.1414213562373095,
  max_abs = 0.2.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import alpha_beta_filter_logic as abf  # noqa: E402

# Published Kalata reference values for tracking index lambda = 2.
KALATA_ALPHA_2 = 0.8541019662496845  # (6 * sqrt(20) - 20) / 8
KALATA_BETA_2 = 0.7639320225002103  # (12 - 2 * sqrt(20)) / 4


class PredictTest(unittest.TestCase):
    def test_anchor_predict(self):
        x_pred, v_pred = abf.predict(10.0, 2.0, 0.5)
        self.assertAlmostEqual(x_pred, 11.0)
        self.assertAlmostEqual(v_pred, 2.0)

    def test_predict_zero_state(self):
        x_pred, v_pred = abf.predict(0.0, 0.0, 1.0)
        self.assertAlmostEqual(x_pred, 0.0)
        self.assertAlmostEqual(v_pred, 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            abf.predict(1.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            abf.predict(1.0, 1.0, -1.0)
        with self.assertRaises(ValueError):
            abf.predict("bad", 1.0, 1.0)


class ResidualTest(unittest.TestCase):
    def test_anchor_residual(self):
        self.assertAlmostEqual(abf.residual(12.0, 10.0), 2.0)

    def test_negative_residual(self):
        self.assertAlmostEqual(abf.residual(9.0, 11.0), -2.0)


class UpdateTest(unittest.TestCase):
    def test_alpha_beta_one_reproduces_raw_measurement(self):
        # From (0, 0) with dt = 1 and z = 12: the updated position
        # must equal the raw measurement and the velocity must equal
        # the residual per second.
        upd = abf.update(0.0, 0.0, 12.0, 1.0, 1.0, 1.0)
        self.assertAlmostEqual(upd["residual"], 12.0)
        self.assertAlmostEqual(upd["position"], 12.0)
        self.assertAlmostEqual(upd["velocity"], 12.0)

    def test_anchor_update_half_gains(self):
        # alpha = 0.5, beta = 1/6 from the hand-computed sequence.
        upd = abf.update(0.0, 0.0, 1.0, 1.0, 0.5, 1.0 / 6.0)
        self.assertAlmostEqual(upd["residual"], 1.0)
        self.assertAlmostEqual(upd["position"], 0.5)
        self.assertAlmostEqual(upd["velocity"], 1.0 / 6.0)

    def test_velocity_correction_scales_with_inverse_dt(self):
        # Same residual at dt = 0.5 doubles the velocity correction.
        upd = abf.update(0.0, 0.0, 1.0, 0.5, 0.5, 1.0 / 6.0)
        self.assertAlmostEqual(upd["velocity"], (1.0 / 6.0) / 0.5)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            abf.update(0.0, 0.0, 1.0, 1.0, 2.0, 0.5)  # alpha >= 2
        with self.assertRaises(ValueError):
            abf.update(0.0, 0.0, 1.0, 1.0, -0.5, 0.5)  # alpha < 0
        with self.assertRaises(ValueError):
            abf.update(0.0, 0.0, 1.0, 1.0, 0.5, 4.0)  # beta >= 4 - 2*alpha
        with self.assertRaises(ValueError):
            abf.update(0.0, 0.0, 1.0, 0.0, 0.5, 0.5)  # dt <= 0


class StepTest(unittest.TestCase):
    def test_anchor_step1(self):
        s = abf.step(0.0, 0.0, 1.0, 1.0, 0.5, 1.0 / 6.0)
        self.assertAlmostEqual(s["predicted_position"], 0.0)
        self.assertAlmostEqual(s["predicted_velocity"], 0.0)
        self.assertAlmostEqual(s["residual"], 1.0)
        self.assertAlmostEqual(s["position"], 0.5)
        self.assertAlmostEqual(s["velocity"], 1.0 / 6.0)

    def test_anchor_step2(self):
        s = abf.step(0.5, 1.0 / 6.0, 2.5, 1.0, 0.5, 1.0 / 6.0)
        self.assertAlmostEqual(s["predicted_position"], 2.0 / 3.0)
        self.assertAlmostEqual(s["predicted_velocity"], 1.0 / 6.0)
        self.assertAlmostEqual(s["residual"], 11.0 / 6.0)
        self.assertAlmostEqual(s["position"], 19.0 / 12.0)
        self.assertAlmostEqual(s["velocity"], 17.0 / 36.0)

    def test_anchor_step3(self):
        s = abf.step(19.0 / 12.0, 17.0 / 36.0, 3.5, 1.0, 0.5, 1.0 / 6.0)
        self.assertAlmostEqual(s["predicted_position"], 37.0 / 18.0)
        self.assertAlmostEqual(s["residual"], 13.0 / 9.0)
        self.assertAlmostEqual(s["position"], 25.0 / 9.0)
        self.assertAlmostEqual(s["velocity"], 77.0 / 108.0)


class RunTrackerTest(unittest.TestCase):
    def test_anchor_five_measurements(self):
        res = abf.run_tracker(
            [1.0, 2.5, 3.5, 4.0, 5.0], 1.0, 0.5, 1.0 / 6.0, 0.0, 0.0
        )
        self.assertEqual(len(res["positions"]), 5)
        expected_positions = [0.5, 19.0 / 12.0, 25.0 / 9.0, 809.0 / 216.0, 773.0 / 162.0]
        expected_velocities = [1.0 / 6.0, 17.0 / 36.0, 77.0 / 108.0, 517.0 / 648.0, 1699.0 / 1944.0]
        for got, exp in zip(res["positions"], expected_positions):
            self.assertAlmostEqual(got, exp)
        for got, exp in zip(res["velocities"], expected_velocities):
            self.assertAlmostEqual(got, exp)
        self.assertAlmostEqual(res["predicted_positions"][4], 368.0 / 81.0)
        self.assertAlmostEqual(res["residuals"][4], 37.0 / 81.0)

    def test_converges_to_true_velocity(self):
        # Constant-velocity target at 1 m/s, dt = 1, noiseless
        # measurements z_k = k. The velocity estimate must converge
        # to 1 m/s and the position to the true ramp.
        n = 200
        res = abf.run_tracker(
            [float(k) for k in range(1, n + 1)], 1.0, 0.5, 1.0 / 6.0, 0.0, 0.0
        )
        self.assertAlmostEqual(res["velocities"][-1], 1.0, delta=1e-6)
        self.assertAlmostEqual(res["positions"][-1], float(n), delta=1e-3)

    def test_alpha_beta_one_tracks_measurements_exactly(self):
        res = abf.run_tracker([10.0, 20.0, 30.0], 1.0, 1.0, 1.0, 0.0, 0.0)
        self.assertAlmostEqual(res["positions"][0], 10.0)
        self.assertAlmostEqual(res["positions"][1], 20.0)
        self.assertAlmostEqual(res["positions"][2], 30.0)
        self.assertAlmostEqual(res["velocities"][1], 10.0)
        self.assertAlmostEqual(res["velocities"][2], 10.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            abf.run_tracker([], 1.0, 0.5, 1.0 / 6.0)
        with self.assertRaises(ValueError):
            abf.run_tracker([1.0, "bad"], 1.0, 0.5, 1.0 / 6.0)
        with self.assertRaises(ValueError):
            abf.run_tracker([1.0], 1.0, 0.5, 5.0)  # beta out of range


class SteadyStateTest(unittest.TestCase):
    def test_smoothing_factor_benedict_bordner(self):
        g = abf.steady_state_gains(0.5)
        self.assertAlmostEqual(g["alpha"], 0.5)
        self.assertAlmostEqual(g["beta"], 1.0 / 6.0)
        g = abf.steady_state_gains(0.2)
        self.assertAlmostEqual(g["beta"], 1.0 / 45.0)
        g = abf.steady_state_gains(1.0)
        self.assertAlmostEqual(g["beta"], 1.0)

    def test_smoothing_factor_raises_outside_range(self):
        with self.assertRaises(ValueError):
            abf.steady_state_gains(0.0)
        with self.assertRaises(ValueError):
            abf.steady_state_gains(2.0)
        with self.assertRaises(ValueError):
            abf.steady_state_gains(-0.5)

    def test_tracking_index_zero_gives_zero_gains(self):
        g = abf.gains_from_tracking_index(0.0)
        self.assertAlmostEqual(g["alpha"], 0.0)
        self.assertAlmostEqual(g["beta"], 0.0)

    def test_tracking_index_two_published_values(self):
        g = abf.gains_from_tracking_index(2.0)
        self.assertAlmostEqual(g["alpha"], KALATA_ALPHA_2, places=12)
        self.assertAlmostEqual(g["beta"], KALATA_BETA_2, places=12)

    def test_critical_damping_relation_holds(self):
        # beta = 2 * (2 - alpha) - 4 * sqrt(1 - alpha) and
        # lambda = beta / sqrt(1 - alpha) for the returned gains.
        lam = 2.0
        g = abf.gains_from_tracking_index(lam)
        beta_from_alpha = 2.0 * (2.0 - g["alpha"]) - 4.0 * math.sqrt(1.0 - g["alpha"])
        self.assertAlmostEqual(g["beta"], beta_from_alpha, places=12)
        self.assertAlmostEqual(g["beta"] / math.sqrt(1.0 - g["alpha"]), lam, places=12)

    def test_tracking_index_monotone_in_maneuverability(self):
        g_small = abf.gains_from_tracking_index(0.5)
        g_large = abf.gains_from_tracking_index(10.0)
        self.assertGreater(g_large["alpha"], g_small["alpha"])
        self.assertGreater(g_large["beta"], g_small["beta"])
        self.assertLess(g_large["alpha"], 1.0)

    def test_tracking_index_negative_raises(self):
        with self.assertRaises(ValueError):
            abf.gains_from_tracking_index(-1.0)


class TrackingErrorTest(unittest.TestCase):
    def test_anchor_errors(self):
        err = abf.tracking_errors([0.0, 1.0, 2.0], [0.1, 0.9, 2.2])
        self.assertAlmostEqual(err["rmse"], math.sqrt(0.02), places=12)
        self.assertAlmostEqual(err["max_abs"], 0.2)

    def test_perfect_track_zero_error(self):
        err = abf.tracking_errors([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        self.assertAlmostEqual(err["rmse"], 0.0)
        self.assertAlmostEqual(err["max_abs"], 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            abf.tracking_errors([], [])
        with self.assertRaises(ValueError):
            abf.tracking_errors([1.0, 2.0], [1.0])


class TrackFilterTest(unittest.TestCase):
    def test_stateful_steps_match_batch(self):
        f = abf.TrackFilter(x0=0.0, v0=0.0, dt=1.0, alpha=0.5, beta=1.0 / 6.0)
        self.assertAlmostEqual(f.step(1.0)["position"], 0.5)
        self.assertAlmostEqual(f.step(2.5)["position"], 19.0 / 12.0)
        self.assertAlmostEqual(f.step(3.5)["velocity"], 77.0 / 108.0)
        self.assertAlmostEqual(f.x, 25.0 / 9.0)
        self.assertAlmostEqual(f.v, 77.0 / 108.0)

    def test_predict_advances_state(self):
        f = abf.TrackFilter(x0=10.0, v0=2.0, dt=0.5, alpha=0.5)
        x_pred, v_pred = f.predict()
        self.assertAlmostEqual(x_pred, 11.0)
        self.assertAlmostEqual(v_pred, 2.0)

    def test_default_beta_from_smoothing_factor(self):
        # beta omitted: defaults to Benedict-Bordner alpha^2 / (2 - alpha).
        f = abf.TrackFilter(x0=0.0, v0=0.0, dt=1.0, alpha=0.5)
        self.assertAlmostEqual(f.beta, 1.0 / 6.0)
        self.assertAlmostEqual(f.step(1.0)["velocity"], 1.0 / 6.0)

    def test_invalid_constructor_raises(self):
        with self.assertRaises(ValueError):
            abf.TrackFilter(x0=0.0, v0=0.0, dt=1.0, alpha=1.5, beta=2.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
