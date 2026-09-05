"""Contract test for the ins-gnss-integrated-filter leaf (wave-40).

Exercises the numbered SKILL.md workflow for running the loosely
coupled INS/GNSS error-state integration filter: step 1 fixes the
5-state error-state vector ordering and module constants, step 2
assembles the continuous error-state matrix from the horizontal
specific forces, step 3 discretizes the error model into the state
transition matrix, step 4 predicts the error state and covariance
between GNSS fixes, step 5 sets up the observation model of the GNSS
position fix, step 6 applies the GNSS position measurement update with
the innovation and the Kalman gain, step 7 runs the full corrected
error trajectory profile over the worked example, and step 8 confirms
the deterministic checks with this contract test. All methods are
offline, stdlib only, deterministic, and assert the prep-verified
worked-example anchors of the leaf spec.
"""

import math
import unittest

from ins_gnss_integrated_filter_logic import (
    STATE_SIZE,
    error_state_matrix,
    mat_inverse_2x2,
    mat_mul,
    measurement_update,
    predict_step,
    run_ins_gnss_profile,
    state_transition_matrix,
    worked_example_profile,
)

# Worked-example profile from the spec (SKILL.md worked example): dt = 1 s,
# level flight accelerating north with f_N = 2 m/s^2 and f_E = 0.
F_NORTH = 2.0
F_EAST = 0.0
DT = 1.0
X_TRUE_0 = [50.0, -30.0, 5.0, -2.0, 0.02]
GNSS_TIMES = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]

H = [[1.0, 0.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0, 0.0]]


def _diag(values):
    """Diagonal matrix from a flat list, mirroring the module usage."""
    n = len(values)
    return [[values[i] if i == j else 0.0 for j in range(n)] for i in range(n)]


def _p0():
    """P0 = diag(1000, 1000, 100, 100, 0.01) of the worked example."""
    return _diag([1000.0, 1000.0, 100.0, 100.0, 0.01])


def _q():
    """Q = diag(0.01, 0.01, 0.01, 0.01, 1e-6) of the worked example."""
    return _diag([0.01, 0.01, 0.01, 0.01, 1e-6])


def _r():
    """R = diag(1, 1) measurement noise of the worked example."""
    return _diag([1.0, 1.0])


class ModuleSetupTest(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: the error-state vector ordering
    and the module constants of the integration setup."""

    def test_state_size_constant_is_five(self):
        """The error-state vector carries the five states dr_N, dr_E,
        dv_N, dv_E and dpsi fixed in step 1 of the SKILL.md
        workflow."""
        self.assertEqual(STATE_SIZE, 5)


class ErrorStateMatrixTest(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: assembling the continuous
    error-state matrix of the psi-angle model from the horizontal
    specific forces."""

    def test_error_state_matrix_north_and_east_couplings(self):
        """With f_N = 2 m/s^2 and f_E = 0 the error-state matrix keeps
        the dpsi coupling of the dv_E row at -2 and the dv_N row at 0,
        the exact rows of the psi-angle model in step 2."""
        f = error_state_matrix(2.0, 0.0)
        self.assertEqual(f[2][4], 0.0)
        self.assertEqual(f[3][4], -2.0)
        f_east = error_state_matrix(0.0, 3.0)
        self.assertEqual(f_east[2][4], 3.0)

    def test_error_state_matrix_position_velocity_rows(self):
        """Position error rates equal the velocity errors, so the
        dr_N and dr_E rows of the step 2 error-state matrix carry the
        unit dv couplings."""
        f = error_state_matrix(2.0, 0.0)
        self.assertEqual(f[0][2], 1.0)
        self.assertEqual(f[1][3], 1.0)
        self.assertEqual(f[0][4], 0.0)
        self.assertEqual(f[1][4], 0.0)


class StateTransitionMatrixTest(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: discretizing the error model
    into the state transition matrix Phi = I + F*dt."""

    def test_phi_equals_identity_plus_f(self):
        """At dt = 1 s the state transition matrix is exactly the
        identity plus the step 2 error-state matrix."""
        f = error_state_matrix(F_NORTH, F_EAST)
        phi = state_transition_matrix(F_NORTH, F_EAST, 1.0)
        for i in range(5):
            for j in range(5):
                want = (1.0 if i == j else 0.0) + f[i][j]
                self.assertAlmostEqual(phi[i][j], want, places=12)

    def test_phi_scales_with_half_step(self):
        """Halving dt halves the off-diagonal F contribution of the
        state transition matrix while the identity stays."""
        f = error_state_matrix(F_NORTH, F_EAST)
        phi = state_transition_matrix(F_NORTH, F_EAST, 0.5)
        self.assertAlmostEqual(phi[3][4], f[3][4] * 0.5, places=12)
        self.assertEqual(phi[0][0], 1.0)

    def test_phi_rejects_nonpositive_dt(self):
        """A zero or negative step raises ValueError, since the
        first-order discretization of step 3 needs a positive dt."""
        with self.assertRaises(ValueError):
            state_transition_matrix(F_NORTH, F_EAST, 0.0)
        with self.assertRaises(ValueError):
            state_transition_matrix(F_NORTH, F_EAST, -1.0)


class PredictStepTest(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: predicting the error state and
    its covariance between GNSS fixes."""

    def test_zero_state_predict_stays_zero(self):
        """A zero initial error state with zero forcing keeps the
        error state at zero through the predict step."""
        x, _ = predict_step([0.0] * 5, _p0(), state_transition_matrix(
            F_NORTH, F_EAST, DT), _q())
        self.assertEqual(x, [0.0] * 5)

    def test_predict_covariance_hand_computed_value(self):
        """P_next equals Phi P Phi^T + Q: with f_N = f_E = 0 the
        velocity error is constant and adds into the position
        covariance, so P_next[0][0] = 1100.01 and the dv-dr
        cross terms sit at 100 within 1e-9."""
        p0 = _p0()
        q = _q()
        phi = state_transition_matrix(0.0, 0.0, DT)
        _, pn = predict_step([0.0] * 5, p0, phi, q)
        want = [[0.0] * 5 for _ in range(5)]
        for i, v in enumerate([1100.01, 1100.01, 100.01, 100.01, 0.010001]):
            want[i][i] = v
        want[0][2] = want[2][0] = 100.0
        want[1][3] = want[3][1] = 100.0
        for i in range(5):
            for j in range(5):
                self.assertAlmostEqual(pn[i][j], want[i][j], delta=1e-9)

    def test_p_symmetry_preserved_after_predict(self):
        """The error covariance stays symmetric through the predict
        step of the integration filter."""
        phi = state_transition_matrix(F_NORTH, F_EAST, DT)
        _, pn = predict_step([0.0] * 5, _p0(), phi, _q())
        for i in range(5):
            for j in range(5):
                self.assertAlmostEqual(pn[i][j], pn[j][i], delta=1e-9)

    def test_predict_rejects_bad_state_length(self):
        """An error state that is not length 5 is rejected by the
        predict step."""
        with self.assertRaises(ValueError):
            predict_step([0.0] * 4, _p0(), state_transition_matrix(
                F_NORTH, F_EAST, DT), _q())

    def test_predict_rejects_bad_covariance_shape(self):
        """Covariances that are not 5x5 raise ValueError in the
        predict step."""
        phi = state_transition_matrix(F_NORTH, F_EAST, DT)
        with self.assertRaises(ValueError):
            predict_step([0.0] * 5, [[0.0] * 4 for _ in range(4)], phi, _q())
        with self.assertRaises(ValueError):
            predict_step([0.0] * 5, _p0(), phi, [[0.01] * 5])


class MeasurementUpdateTest(unittest.TestCase):
    """Steps 5 and 6 of the SKILL.md workflow: the observation model
    and the GNSS position measurement update with the innovation and
    the Kalman gain."""

    def test_observation_matrix_reads_position_channels(self):
        """The 2x5 observation matrix of step 5 senses the north and
        east position error channels only."""
        for i in range(2):
            for j in range(5):
                self.assertEqual(H[i][j], 1.0 if i == j else 0.0)

    def test_perfect_measurement_position_identity(self):
        """With a tiny measurement noise the GNSS position update of
        step 6 drives the estimated position error onto the
        measurement innovation within 1e-3."""
        r_tiny = _diag([1e-9, 1e-9])
        x_new, _, innov, _ = measurement_update(
            [0.0] * 5, _p0(), [10.0, -5.0], H, r_tiny)
        self.assertAlmostEqual(x_new[0], 10.0, delta=1e-3)
        self.assertAlmostEqual(x_new[1], -5.0, delta=1e-3)
        self.assertEqual(innov, [10.0, -5.0])

    def test_innovation_is_measurement_residual(self):
        """The innovation returned by step 6 is the residual of the
        GNSS position measurement against the predicted error state,
        z minus H x."""
        x = [3.0, -1.0, 0.0, 0.0, 0.0]
        _, _, innov, _ = measurement_update(x, _p0(), [10.0, -5.0], H, _r())
        self.assertAlmostEqual(innov[0], 7.0, delta=1e-9)
        self.assertAlmostEqual(innov[1], -4.0, delta=1e-9)

    def test_kalman_gain_matrix_shape(self):
        """The Kalman gain of the step 6 update is the 5x2 matrix
        that maps the 2-channel innovation onto the 5 error states."""
        _, _, _, kg = measurement_update(
            [0.0] * 5, _p0(), [10.0, -5.0], H, _r())
        self.assertEqual(len(kg), 5)
        for row in kg:
            self.assertEqual(len(row), 2)

    def test_covariance_shrinks_on_trusted_measurement(self):
        """A very trusted GNSS position fix collapses the position
        error covariance in the step 6 update."""
        x_new, p_new, _, _ = measurement_update(
            [0.0] * 5, _p0(), [10.0, -5.0], H, _diag([1e-9, 1e-9]))
        self.assertAlmostEqual(x_new[0], 10.0, delta=1e-3)
        self.assertLess(p_new[0][0], 1.0)

    def test_covariance_symmetric_after_update(self):
        """The error covariance stays symmetric through the GNSS
        position measurement update."""
        _, p_new, _, _ = measurement_update(
            [0.0] * 5, _p0(), [10.0, -5.0], H, _r())
        for i in range(5):
            for j in range(5):
                self.assertAlmostEqual(p_new[i][j], p_new[j][i], delta=1e-9)

    def test_update_rejects_bad_measurement_length(self):
        """A GNSS position measurement that is not length 2 raises
        ValueError in the measurement update."""
        with self.assertRaises(ValueError):
            measurement_update([0.0] * 5, _p0(), [10.0], H, _r())

    def test_update_rejects_bad_observation_shape(self):
        """An observation matrix that is not 2x5 raises ValueError in
        the measurement update."""
        with self.assertRaises(ValueError):
            measurement_update([0.0] * 5, _p0(), [10.0, -5.0],
                               [[1.0, 0.0]], _r())

    def test_update_rejects_bad_noise_shape(self):
        """A measurement noise matrix that is not 2x2 raises
        ValueError in the measurement update."""
        with self.assertRaises(ValueError):
            measurement_update([0.0] * 5, _p0(), [10.0, -5.0], H,
                               [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])

    def test_update_rejects_bad_state_or_covariance_shape(self):
        """State and covariance shape guards of the measurement
        update reject a short error state and a non-5x5 covariance."""
        with self.assertRaises(ValueError):
            measurement_update([0.0] * 3, _p0(), [10.0, -5.0], H, _r())
        with self.assertRaises(ValueError):
            measurement_update([0.0] * 5, [[0.0] * 5 for _ in range(4)],
                               [10.0, -5.0], H, _r())


class RunProfileTest(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: running the full corrected
    error trajectory profile and gating the integrated solution on
    the worked example."""

    def setUp(self):
        """Run the worked example profile once per test method."""
        self.res = worked_example_profile()

    def test_profile_returns_six_updates(self):
        """The worked example fixes GNSS at t = 10, 20, ..., 60 s, so
        the profile returns one update per fix, six in total."""
        self.assertEqual(len(self.res["updates"]), 6)

    def test_profile_t10_innovation_anchor(self):
        """The t = 10 innovation of the worked example sits at
        (100.000, -51.800) within 0.01, the first position-error
        residual of the corrected trajectory."""
        t10 = self.res["updates"][0]
        self.assertEqual(t10[0], 10.0)
        self.assertAlmostEqual(t10[1], 100.000, delta=0.01)
        self.assertAlmostEqual(t10[2], -51.800, delta=0.01)

    def test_profile_t10_estimate_anchor(self):
        """After the first GNSS fix the estimated north and east
        position errors read 99.991 m and -51.795 m within 0.01."""
        t10 = self.res["updates"][0]
        self.assertAlmostEqual(t10[3], 99.991, delta=0.01)
        self.assertAlmostEqual(t10[4], -51.795, delta=0.01)

    def test_profile_t30_innovation_and_estimate_anchors(self):
        """At t = 30 the innovation is (-0.114, -9.900) and the
        estimated position error is (200.009, -107.365), each within
        0.01 of the prep-verified anchors."""
        t30 = self.res["updates"][2]
        self.assertAlmostEqual(t30[1], -0.114, delta=0.01)
        self.assertAlmostEqual(t30[2], -9.900, delta=0.01)
        self.assertAlmostEqual(t30[3], 200.009, delta=0.01)
        self.assertAlmostEqual(t30[4], -107.365, delta=0.01)

    def test_profile_t60_innovation_magnitude_below_two_decimetres(self):
        """Once the integration filter has converged the t = 60
        innovation magnitude falls below 0.2 m."""
        t60 = self.res["updates"][5]
        self.assertLess(math.hypot(t60[1], t60[2]), 0.2)

    def test_profile_final_estimate_within_half_metre_of_true(self):
        """The final estimated position error of the worked example is
        within 0.5 m of the true position error after the last GNSS
        update."""
        fe = self.res["final_estimate"]
        ft = self.res["final_true"]
        self.assertLess(math.hypot(fe[0] - ft[0], fe[1] - ft[1]), 0.5)

    def test_profile_final_true_error_matches_spec(self):
        """The propagated true INS error at t = 60 matches the spec
        state (350.0, -220.8, 5.0, -4.4, 0.02) within 1e-6."""
        ft = self.res["final_true"]
        for got, want in zip(ft, [350.0, -220.8, 5.0, -4.4, 0.02]):
            self.assertAlmostEqual(got, want, delta=1e-6)

    def test_profile_final_estimation_error_anchors(self):
        """The final estimation error of the corrected trajectory is
        4.3e-5 m north and 0.0081 m east within tolerance."""
        fe = self.res["final_estimate"]
        ft = self.res["final_true"]
        n_err = abs(fe[0] - ft[0])
        e_err = abs(fe[1] - ft[1])
        self.assertAlmostEqual(n_err, 4.33e-5, delta=1e-6)
        self.assertAlmostEqual(e_err, 0.0081, delta=1e-4)

    def test_profile_innovation_magnitude_shrinks_after_convergence(self):
        """The innovation magnitude at t = 60 is far below the t = 30
        level once the error-state filter has converged."""
        mag30 = math.hypot(self.res["updates"][2][1], self.res["updates"][2][2])
        mag60 = math.hypot(self.res["updates"][5][1], self.res["updates"][5][2])
        self.assertLess(mag60, mag30)

    def test_profile_deterministic_two_runs_identical(self):
        """Two profile runs return identical dicts, so the corrected
        trajectory of the integrated solution is deterministic."""
        again = run_ins_gnss_profile(
            DT, F_NORTH, F_EAST, X_TRUE_0, GNSS_TIMES, _p0(), _q(), _r())
        self.assertEqual(again, self.res)

    def test_profile_rejects_stochastic_innovations(self):
        """The profile is deterministic by design, so requesting
        noisy measurement draws raises ValueError."""
        with self.assertRaises(ValueError):
            run_ins_gnss_profile(
                DT, F_NORTH, F_EAST, X_TRUE_0, GNSS_TIMES, _p0(), _q(),
                _r(), noise_free_innovations=False)


class MatrixHelpersTest(unittest.TestCase):
    """Small matrix helpers shared by the error-state matrix, the
    predict step and the measurement update of the workflow."""

    def test_mat_mul_shape_mismatch_raises(self):
        """Matrix multiplication with mismatched inner dimensions
        raises ValueError."""
        with self.assertRaises(ValueError):
            mat_mul([[1.0, 2.0]], [[1.0], [2.0], [3.0]])

    def test_mat_inverse_2x2_known_inverse(self):
        """The 2x2 inverse used by the gain computation of step 6
        recovers the textbook inverse of a 2x2 matrix."""
        m = [[4.0, 7.0], [2.0, 6.0]]
        inv = mat_inverse_2x2(m)
        self.assertAlmostEqual(inv[0][0], 0.6, delta=1e-12)
        self.assertAlmostEqual(inv[0][1], -0.7, delta=1e-12)
        self.assertAlmostEqual(inv[1][0], -0.2, delta=1e-12)
        self.assertAlmostEqual(inv[1][1], 0.4, delta=1e-12)

    def test_mat_inverse_2x2_singular_raises(self):
        """A singular 2x2 matrix raises ValueError from the inverse
        helper."""
        with self.assertRaises(ValueError):
            mat_inverse_2x2([[1.0, 2.0], [2.0, 4.0]])


if __name__ == "__main__":
    unittest.main()
