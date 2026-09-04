"""Offline deterministic contract test for the IMM filter logic.

Run: python3 test_interacting_multiple_model_filter.py  (exit 0 expected)
Pure stdlib unittest, no network, deterministic, well under 20 s.
"""

import math
import unittest

import interacting_multiple_model_filter_logic as imm


def _rms_window(combined, truth, t0, t1):
    n = t1 - t0 + 1
    return math.sqrt(sum(
        math.hypot(combined[t][0] - truth[t][0],
                   combined[t][1] - truth[t][1]) ** 2
        for t in range(t0, t1 + 1)) / n)


def _cv_only_run(track):
    """Single-model CV filter over the same track and initialization."""
    x_cv = [[track[0][0], 0.0], [track[0][1], 0.0]]
    p_cv = [[[imm.R, 0.0], [0.0, imm.INIT_VEL_VAR]],
            [[imm.R, 0.0], [0.0, imm.INIT_VEL_VAR]]]
    hist = [list(track[0])]
    for k in range(1, len(track)):
        z = [float(track[k][0]), float(track[k][1])]
        nxt = []
        nxp = []
        for a in range(2):
            xp, pp = imm.kalman_predict(x_cv[a], p_cv[a], imm.F_CV, imm.Q_CV)
            xu, pu, _, _, _ = imm.kalman_update(xp, pp, z[a], imm.H_CV,
                                                imm.R)
            nxt.append(xu)
            nxp.append(pu)
        x_cv = nxt
        p_cv = nxp
        hist.append([x_cv[0][0], x_cv[1][0]])
    return hist


class TestKalmanPredict(unittest.TestCase):
    """Prediction step on the 2x2 and 3x3 mode filters."""

    def test_cv_predict_matches_hand_calculation(self):
        x, p = imm.kalman_predict([100.0, 5.0],
                                  [[4.0, 1.0], [1.0, 2.0]],
                                  imm.F_CV, imm.Q_CV)
        self.assertEqual(x, [105.0, 5.0])
        # F P F^T = [[8, 3], [3, 2]] plus Q_CV = [[1/3, 1/2], [1/2, 1]]
        self.assertAlmostEqual(p[0][0], 8.0 + 1.0 / 3.0, places=9)
        self.assertAlmostEqual(p[0][1], 3.5, places=9)
        self.assertAlmostEqual(p[1][0], 3.5, places=9)
        self.assertAlmostEqual(p[1][1], 3.0, places=9)

    def test_ca_predict_kinematics_closed_form(self):
        x, _ = imm.kalman_predict([100.0, 10.0, 2.0], imm.P0_CA,
                                  imm.F_CA, imm.Q_CA)
        # x + v + 0.5 a, v + a, a at DT = 1 s
        self.assertAlmostEqual(x[0], 111.0, places=9)
        self.assertAlmostEqual(x[1], 12.0, places=9)
        self.assertAlmostEqual(x[2], 2.0, places=9)

    def test_ca_predict_covariance_independent_cross_check(self):
        p_in = [[2.0, 0.5, 0.0], [0.5, 3.0, 0.2], [0.0, 0.2, 4.0]]
        _, p = imm.kalman_predict([1.0, 1.0, 1.0], p_in, imm.F_CA, imm.Q_CA)
        # independent triple-loop recomputation of F P F^T + Q
        ft = [[imm.F_CA[j][i] for j in range(3)] for i in range(3)]
        fpf = [[sum(imm.F_CA[i][k] * p_in[k][l] * ft[l][j]
                    for k in range(3) for l in range(3))
                for j in range(3)] for i in range(3)]
        expect = [[fpf[i][j] + imm.Q_CA[i][j] for j in range(3)]
                  for i in range(3)]
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(p[i][j], expect[i][j], places=9)

    def test_predict_rejects_dimension_mismatch(self):
        with self.assertRaises(ValueError):
            imm.kalman_predict([1.0, 2.0, 3.0], imm.P0_CV, imm.F_CV,
                               imm.Q_CV)  # 2x2 F with a 3-state x
        with self.assertRaises(ValueError):
            imm.kalman_predict([1.0, 2.0], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
                                            [0.0, 0.0, 1.0]], imm.F_CV,
                               imm.Q_CV)  # 3x3 p with 2-state x
        with self.assertRaises(ValueError):
            imm.kalman_predict([1.0, 2.0], imm.P0_CV, [[1.0, 0.0, 0.0],
                                                       [0.0, 1.0, 0.0],
                                                       [0.0, 0.0, 1.0]],
                               imm.Q_CV)  # 3x3 f with 2-state x
        with self.assertRaises(ValueError):
            imm.kalman_predict([1.0, 2.0], imm.P0_CV, imm.F_CV,
                               [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
                                [0.0, 0.0, 1.0]])  # 3x3 q with 2-state x


class TestKalmanUpdate(unittest.TestCase):
    """Scalar-position update, likelihood and noise rejection."""

    def test_update_known_case(self):
        x_upd, p_upd, innovation, s, lik = imm.kalman_update(
            [0.0, 0.0], [[1.0, 0.0], [0.0, 1.0]], 2.0, imm.H_CV, 1.0)
        self.assertAlmostEqual(innovation, 2.0, places=12)
        self.assertAlmostEqual(s, 2.0, places=12)
        self.assertAlmostEqual(x_upd[0], 1.0, places=12)
        self.assertAlmostEqual(x_upd[1], 0.0, places=12)
        self.assertAlmostEqual(p_upd[0][0], 0.5, places=12)
        self.assertAlmostEqual(p_upd[1][1], 1.0, places=12)
        self.assertAlmostEqual(lik, math.exp(-1.0) / math.sqrt(4.0 * math.pi),
                               places=12)

    def test_update_likelihood_positive_and_covariance_reduced(self):
        x_upd, p_upd, _, s, lik = imm.kalman_update(
            [0.0, 0.0], [[10.0, 0.0], [0.0, 5.0]], 1.0, imm.H_CV, imm.R)
        self.assertGreater(lik, 0.0)
        self.assertGreater(s, 0.0)
        self.assertLess(p_upd[0][0], 10.0)
        self.assertLess(x_upd[0], 1.0)  # partial correction only
        self.assertGreater(x_upd[0], 0.0)

    def test_update_measurement_pulls_state(self):
        x_upd, _, innovation, _, _ = imm.kalman_update(
            [100.0, 10.0], imm.P0_CV, 120.0, imm.H_CV, imm.R)
        self.assertAlmostEqual(innovation, 20.0, places=9)
        self.assertGreater(x_upd[0], 100.0)
        self.assertLess(x_upd[0], 120.0)

    def test_update_rejects_nonpositive_r(self):
        for bad in (0.0, -5.0):
            with self.assertRaises(ValueError):
                imm.kalman_update([0.0, 0.0], imm.P0_CV, 1.0, imm.H_CV, bad)

    def test_update_rejects_malformed_inputs(self):
        with self.assertRaises(ValueError):
            imm.kalman_update([0.0, 0.0], imm.P0_CV, 1.0, [1.0], imm.R)
        with self.assertRaises(ValueError):
            imm.kalman_update([0.0, 0.0], [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
                                           [0.0, 0.0, 1.0]], 1.0, imm.H_CV,
                              imm.R)


class TestMixInitial(unittest.TestCase):
    """Initial mode-conditioned mixing."""

    def test_mixing_identical_priors_recover_state(self):
        mu = [0.6, 0.4]
        xs = [[5.0, 2.0], [5.0, 2.0]]
        ps = [[[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]]]
        mx, mp = imm.mix_initial(mu, xs, ps, imm.PI)
        self.assertEqual(mx, [5.0, 2.0])
        self.assertAlmostEqual(mp[0][0], 1.0, places=12)
        self.assertAlmostEqual(mp[1][1], 1.0, places=12)

    def test_mixing_plain_mixture_identity(self):
        # For row-stochastic pi the predicted-probability blend of the
        # per-mode mixed priors has mean equal to the plain mu-weighted
        # mixture (rows of pi sum to one, so the pi weights telescope).
        mu = [0.6, 0.4]
        xs = [[0.0, 0.0], [10.0, 4.0]]
        ps = [[[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]]]
        mx, mp = imm.mix_initial(mu, xs, ps, imm.PI)
        self.assertAlmostEqual(mx[0], 4.0, places=9)
        self.assertAlmostEqual(mx[1], 1.6, places=9)
        # Spread terms inflate the blended variance above the weighted mean
        # of the prior covariances (1.0), but stay below the unconditional
        # mixture variance 1 + 0.6*0.4*10^2 = 25 (per-mode mixing uses the
        # more concentrated mu_{i|j} weights).
        self.assertGreater(mp[0][0], 1.0)
        self.assertLess(mp[0][0], 25.0)
        self.assertAlmostEqual(mp[0][0], 5.712691, delta=1e-5)

    def test_mixing_ca_dimension_works(self):
        mu = [0.5, 0.5]
        xs = [[0.0, 0.0, 0.0], [3.0, 1.0, 2.0]]
        ps = [imm.P0_CA, imm.P0_CA]
        mx, mp = imm.mix_initial(mu, xs, ps, imm.PI)
        self.assertEqual(len(mx), 3)
        self.assertAlmostEqual(sum(mx), sum(mu[i] * sum(xs[i])
                                            for i in range(2)), places=9)
        self.assertEqual(len(mp), 3)
        self.assertEqual(len(mp[0]), 3)

    def test_mixing_rejects_bad_mode_probabilities(self):
        xs = [[0.0, 0.0], [1.0, 1.0]]
        ps = [imm.P0_CV, imm.P0_CV]
        with self.assertRaises(ValueError):
            imm.mix_initial([0.8, 0.1], xs, ps, imm.PI)  # sum < 1
        with self.assertRaises(ValueError):
            imm.mix_initial([1.2, -0.2], xs, ps, imm.PI)

    def test_mixing_rejects_malformed_dimensions(self):
        with self.assertRaises(ValueError):
            imm.mix_initial([0.5, 0.5], [[0.0, 0.0], [1.0, 1.0, 1.0]],
                            [imm.P0_CV, imm.P0_CV], imm.PI)
        with self.assertRaises(ValueError):
            imm.mix_initial([0.5, 0.5], [[0.0, 0.0], [1.0, 1.0]],
                            [imm.P0_CV, imm.P0_CV], [[1.0, 0.0], [0.0, 1.0],
                                                     [0.0, 0.0]])


class TestModeUpdate(unittest.TestCase):
    """Bayesian mode-probability refresh."""

    def test_formula_exact(self):
        self.assertEqual(imm.mode_update([0.5, 0.5], [0.5, 0.5],
                                         [2.0, 1.0]), [2.0 / 3.0, 1.0 / 3.0])

    def test_probabilities_stay_in_unit_interval_and_sum_to_one(self):
        mu = [0.5, 0.5]
        c = [0.5, 0.5]
        likes = [1.2, 0.4]
        for _ in range(10):
            mu = imm.mode_update(mu, c, likes)
            self.assertGreaterEqual(mu[0], 0.0)
            self.assertGreaterEqual(mu[1], 0.0)
            self.assertLessEqual(mu[0], 1.0)
            self.assertLessEqual(mu[1], 1.0)
            self.assertAlmostEqual(sum(mu), 1.0, places=12)

    def test_extreme_likelihood_ratio_saturates(self):
        mu = imm.mode_update([0.5, 0.5], [0.5, 0.5], [1e-200, 1.0])
        self.assertAlmostEqual(mu[1], 1.0, places=12)
        self.assertAlmostEqual(mu[0], 0.0, places=12)

    def test_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            imm.mode_update([0.5, 0.5], [0.5, 0.5], [1.0, -1.0])
        with self.assertRaises(ValueError):
            imm.mode_update([0.5, 0.5], [0.0, 0.5], [1.0, 1.0])
        with self.assertRaises(ValueError):
            imm.mode_update([0.5, 0.5], [0.5, 0.5], [0.0, 0.0])  # zero total
        with self.assertRaises(ValueError):
            imm.mode_update([0.7, 0.7], [0.5, 0.5], [1.0, 1.0])


class TestImmStep(unittest.TestCase):
    """One full IMM cycle over both axes."""

    def _zero_bank(self):
        mu = [0.95, 0.05]
        x_cv = [[0.0, 0.0], [0.0, 0.0]]
        p_cv = [[[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]]]
        x_ca = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
        p_ca = [[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]]
        return mu, x_cv, p_cv, x_ca, p_ca

    def test_dict_contains_exactly_documented_keys(self):
        mu, x_cv, p_cv, x_ca, p_ca = self._zero_bank()
        res = imm.imm_step(mu, x_cv, p_cv, x_ca, p_ca, [100.0, 0.0],
                           imm.PI, imm.F_CV, imm.Q_CV, imm.F_CA, imm.Q_CA,
                           imm.R)
        self.assertEqual(set(res.keys()),
                         {"mu_new", "x_cv", "p_cv", "x_ca", "p_ca",
                          "x_combined", "p_combined"})

    def test_mode_probabilities_normalized_after_step(self):
        mu, x_cv, p_cv, x_ca, p_ca = self._zero_bank()
        res = imm.imm_step(mu, x_cv, p_cv, x_ca, p_ca, [1.0, 1.0],
                           imm.PI, imm.F_CV, imm.Q_CV, imm.F_CA, imm.Q_CA,
                           imm.R)
        self.assertAlmostEqual(sum(res["mu_new"]), 1.0, places=12)
        self.assertTrue(all(0.0 <= v <= 1.0 for v in res["mu_new"]))

    def test_combined_is_mu_weighted_sum_of_per_mode_estimates(self):
        mu, x_cv, p_cv, x_ca, p_ca = self._zero_bank()
        res = imm.imm_step(mu, x_cv, p_cv, x_ca, p_ca, [100.0, 0.0],
                           imm.PI, imm.F_CV, imm.Q_CV, imm.F_CA, imm.Q_CA,
                           imm.R)
        m0, m1 = res["mu_new"]
        for a in range(2):
            cv3 = [res["x_cv"][a][0], res["x_cv"][a][1], 0.0]
            for k in range(3):
                self.assertAlmostEqual(res["x_combined"][a][k],
                                       m0 * cv3[k] + m1 * res["x_ca"][a][k],
                                       places=9)

    def test_cv_mode_stays_high_on_straight_line_step(self):
        mu, x_cv, p_cv, x_ca, p_ca = self._zero_bank()
        res = imm.imm_step(mu, x_cv, p_cv, x_ca, p_ca, [100.0, 0.0],
                           imm.PI, imm.F_CV, imm.Q_CV, imm.F_CA, imm.Q_CA,
                           imm.R)
        # A small position step with no lateral motion keeps CV dominant.
        self.assertGreater(res["mu_new"][0], res["mu_new"][1])

    def test_rejects_bad_arguments(self):
        mu, x_cv, p_cv, x_ca, p_ca = self._zero_bank()
        with self.assertRaises(ValueError):
            imm.imm_step(mu, x_cv, p_cv, x_ca, p_ca, [1.0, 1.0], imm.PI,
                         imm.F_CV, imm.Q_CV, imm.F_CA, imm.Q_CA, 0.0)
        with self.assertRaises(ValueError):
            imm.imm_step([0.5, 0.3], x_cv, p_cv, x_ca, p_ca, [1.0, 1.0],
                         imm.PI, imm.F_CV, imm.Q_CV, imm.F_CA, imm.Q_CA,
                         imm.R)
        bad_pi = [[1.0, 0.0], [1.0, 0.0]]
        with self.assertRaises(ValueError):
            imm.imm_step(mu, x_cv, p_cv, x_ca, p_ca, [1.0, 1.0], bad_pi,
                         imm.F_CV, imm.Q_CV, imm.F_CA, imm.Q_CA, imm.R)
        x3 = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
        with self.assertRaises(ValueError):
            imm.imm_step(mu, x3, p_cv, x_ca, p_ca, [1.0, 1.0], imm.PI,
                         imm.F_CV, imm.Q_CV, imm.F_CA, imm.Q_CA, imm.R)


class TestManeuveringTrack(unittest.TestCase):
    """Analytic scripted truth track."""

    def test_straight_phase_before_maneuver(self):
        track = imm.make_maneuvering_track()
        self.assertEqual(len(track), 100)
        self.assertEqual(track[0], [0.0, 0.0])
        self.assertEqual(track[49], [4900.0, 0.0])
        self.assertEqual(track[50], [5000.0, 0.0])  # onset at t = 50 s

    def test_maneuver_analytic_points(self):
        track = imm.make_maneuvering_track()
        self.assertEqual(track[51], [5100.0, 10.0])
        self.assertEqual(track[60], [6000.0, 1000.0])
        self.assertEqual(track[75], [7500.0, 6250.0])  # end of accel phase
        self.assertEqual(track[76], [7600.0, 6750.0])  # 500 m/s coast
        self.assertEqual(track[99], [9900.0, 18250.0])


class TestRunImmTrack(unittest.TestCase):
    """Full 100 s run over the scripted track (worked example)."""

    def setUp(self):
        self.track = imm.make_maneuvering_track()
        self.res = imm.run_imm_track(self.track)
        self.mu_hist = self.res["mu_hist"]
        self.comb = self.res["combined_pos_hist"]

    def test_dict_keys_and_history_shapes(self):
        self.assertEqual(set(self.res.keys()),
                         {"mu_hist", "combined_pos_hist", "cv_pos_hist",
                          "ca_pos_hist"})
        self.assertEqual(len(self.mu_hist), 100)
        for t in range(100):
            self.assertEqual(len(self.mu_hist[t]), 2)
            self.assertEqual(len(self.comb[t]), 2)

    def test_cv_mode_dominates_during_straight_flight(self):
        self.assertGreater(self.mu_hist[49][0], 0.8)  # mu_cv ~ 0.892
        self.assertLess(self.mu_hist[49][1], 0.2)

    def test_ca_probability_rises_above_08_within_3s_of_onset(self):
        mu_ca_53 = self.mu_hist[53][1]
        self.assertGreater(mu_ca_53, 0.8)
        self.assertAlmostEqual(mu_ca_53, 0.859365, delta=1e-3)

    def test_imm_rms_position_error_below_15m_in_maneuver_window(self):
        rms = _rms_window(self.comb, self.track, 50, 75)
        self.assertLess(rms, 15.0)
        self.assertAlmostEqual(rms, 4.441831, delta=1e-3)

    def test_cv_only_position_error_exceeds_60m_in_maneuver_window(self):
        cv_hist = _cv_only_run(self.track)
        worst = max(math.hypot(cv_hist[t][0] - self.track[t][0],
                               cv_hist[t][1] - self.track[t][1])
                    for t in range(50, 76))
        self.assertGreater(worst, 60.0)
        self.assertAlmostEqual(worst, 76.040373, delta=1e-2)

    def test_mode_probabilities_sum_to_one_at_every_step(self):
        for m in self.mu_hist:
            self.assertAlmostEqual(sum(m), 1.0, places=9)

    def test_combined_equals_mu_weighted_sum_at_final_step(self):
        m = self.mu_hist[-1]
        cv = self.res["cv_pos_hist"][-1]
        ca = self.res["ca_pos_hist"][-1]
        for a in range(2):
            self.assertAlmostEqual(self.comb[-1][a],
                                   m[0] * cv[a] + m[1] * ca[a], places=6)

    def test_deterministic_two_runs_identical(self):
        res2 = imm.run_imm_track(self.track)
        self.assertEqual(res2["mu_hist"], self.mu_hist)
        self.assertEqual(res2["combined_pos_hist"], self.comb)

    def test_cv_velocity_converges_within_1e3_by_t20(self):
        x = [0.0, 0.0]
        p = imm.P0_CV
        for k in range(1, 21):
            xp, pp = imm.kalman_predict(x, p, imm.F_CV, imm.Q_CV)
            x, p, _, _, _ = imm.kalman_update(xp, pp, 100.0 * k,
                                              imm.H_CV, imm.R)
        self.assertLess(abs(x[1] - 100.0), 1e-3)

    def test_rejects_empty_track(self):
        with self.assertRaises(ValueError):
            imm.run_imm_track([])


if __name__ == "__main__":
    unittest.main(verbosity=2)
