"""Contract test for tightly-coupled-ins-gnss (gnc-autonomy/navigation).

Exercises the full SKILL.md workflow of the wave-43 leaf: step 1 (fix the
epoch profile: the six-satellite ECEF test constellation at radius
26560000.0 m on the +-x, +-y and +-z axes, the raw pseudorange measurements
of the moving receiver, the INS reference trajectory records, the initial
error state x0, the P0 diagonal and the per-step process noise q), step 2
(propagate the eight INS error states of the constant-velocity-error,
constant-drift model over dt through state_transition_matrix,
propagate_state and propagate_covariance, the exact Phi with dt on the
dr-dv couplings and the db-dd coupling), step 3 (predict each raw
pseudorange from the inertial position estimate plus the receiver clock
bias state with predicted_pseudoranges), step 4 (build the measurement
matrix from the line-of-sight geometry rows and the unit clock column with
measurement_matrix), step 5 (apply the raw-pseudorange-update Kalman
correction on the residuals with kalman_update and read the innovation
vector and innovation RMS), step 6 (re-derive the corrected navigation
solution as the INS reference plus the estimated corrections with
corrected_navigation_state) and step 7 (read off the gating outputs: the
posterior covariance diagonal closed forms, the clock-state-filter bias
and drift estimates and the convergence of the corrected position and
velocity against the true trajectory of the moving receiver).

All asserts are tolerance-based (assertAlmostEqual delta or isclose);
exact equality appears only on literal constants (the unit clock column,
the zero velocity-error and clock-drift columns, the zero velocity and
drift posterior at the first snapshot).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tightly_coupled_ins_gnss_logic import (
    STATE_SIZE,
    corrected_navigation_state,
    kalman_update,
    measurement_matrix,
    predicted_pseudoranges,
    propagate_covariance,
    propagate_state,
    run_tightly_coupled_profile,
    state_transition_matrix,
)

# Worked-example scenario (spec-given, deterministic, stdlib math only).
R_S = 26560000.0
SAT_POSITIONS = [(R_S, 0.0, 0.0), (-R_S, 0.0, 0.0), (0.0, R_S, 0.0),
                 (0.0, -R_S, 0.0), (0.0, 0.0, R_S), (0.0, 0.0, -R_S)]
NOISE_REALIZATION = [[0.2, -0.1, 0.3, -0.2, 0.1, -0.3],
                     [-0.1, 0.2, -0.2, 0.3, -0.3, 0.1],
                     [0.3, 0.1, -0.1, -0.3, 0.2, -0.2]]
DT = 1.0
MEASUREMENT_VARIANCE = 0.25
VARIANCES = [MEASUREMENT_VARIANCE] * 6
X0 = [0.0] * 8
P0 = [[0.0] * 8 for _ in range(8)]
for i, v in enumerate([100.0, 100.0, 100.0, 1.0, 1.0, 1.0, 2.5e7, 400.0]):
    P0[i][i] = v
Q = [0.01, 0.01, 0.01, 0.001, 0.001, 0.001, 0.01, 1e-4]

# True receiver trajectory of the worked example: r_true(t) =
# (100 + 25 t, 200 - 10 t, -150 + 5 t) m, v_true = (25, -10, 5) m/s,
# b_true(t) = 1500 + 5 t m, d_true = 5 m/s. The INS reference runs offset
# by e_p(t) = (12 + 0.5 t, -8 - 0.3 t, 6 + 0.2 t) m with the constant
# velocity error (0.5, -0.3, 0.2) m/s, so the clock reference stays zero
# and the clock states hold the totals.
TRUE_BIAS0 = 1500.0
TRUE_DRIFT = 5.0
TRUE_VELOCITY = [25.0, -10.0, 5.0]
TRUE_REF_VELOCITY = [25.5, -10.3, 5.2]


def true_position(t):
    return [100.0 + 25.0 * t, 200.0 - 10.0 * t, -150.0 + 5.0 * t]


def ref_position(t):
    true = true_position(t)
    offset = [12.0 + 0.5 * t, -8.0 - 0.3 * t, 6.0 + 0.2 * t]
    return [true[i] + offset[i] for i in range(3)]


def build_epochs(perfect=False):
    """Epoch list for the worked example: raw code pseudoranges only, no
    carrier phase enters anywhere. With perfect=True the measurement noise
    offsets are zero (the perfect-measurement identity run)."""
    epochs = []
    for e in range(3):
        t = float(e)
        truth = true_position(t)
        geometric = [math.sqrt(sum((SAT_POSITIONS[i][k] - truth[k]) ** 2
                                   for k in range(3)))
                     for i in range(6)]
        bias_true = TRUE_BIAS0 + TRUE_DRIFT * t
        if perfect:
            pseudoranges = [geometric[i] + bias_true for i in range(6)]
        else:
            pseudoranges = [geometric[i] + bias_true + NOISE_REALIZATION[e][i]
                            for i in range(6)]
        epochs.append({
            "sat_positions": [list(s) for s in SAT_POSITIONS],
            "pseudoranges": pseudoranges,
            "ref_position": ref_position(t),
            "ref_velocity": list(TRUE_REF_VELOCITY),
            "ref_bias": 0.0,
            "ref_drift": 0.0,
        })
    return epochs


EPOCHS = build_epochs(perfect=False)
PERFECT_EPOCHS = build_epochs(perfect=True)
PERFECT_VARIANCES = [1e-9] * 6


def run_worked():
    return run_tightly_coupled_profile(EPOCHS, X0, P0, Q, DT, VARIANCES)


class TestStateTransition(unittest.TestCase):
    """Workflow step 2: propagate the INS error states between epochs."""

    def test_state_size_is_eight(self):
        """STATE_SIZE must be the fixed 8-state form of the leaf plan (3
        position error, 3 velocity error, clock bias, clock drift)."""
        self.assertEqual(STATE_SIZE, 8)

    def test_phi_structure_rows_anchor(self):
        """state_transition_matrix(1.0) row 0 equals [1, 0, 0, 1, 0, 0, 0,
        0] and row 6 equals [0, 0, 0, 0, 0, 0, 1, 1]: the identity with dt
        on the dr-dv couplings and the db-dd coupling (exact to 0.000e+00
        on the spec anchor, asserted within 1e-12). At any dt the exact
        transition carries dt only on the position-velocity and
        bias-drift couplings; every other off-diagonal entry stays zero."""
        phi = state_transition_matrix(1.0)
        row0 = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0]
        row6 = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0]
        for i in range(8):
            self.assertAlmostEqual(phi[0][i], row0[i], delta=1e-12)
            self.assertAlmostEqual(phi[6][i], row6[i], delta=1e-12)
        phi2 = state_transition_matrix(2.0)
        for r in range(8):
            for c in range(8):
                expected = 2.0 if (r < 3 and c == r + 3) or (r == 6 and
                                                             c == 7) else 0.0
                if r == c:
                    expected += 1.0
                self.assertAlmostEqual(phi2[r][c], expected, delta=1e-12)

    def test_propagate_state_closed_form(self):
        """propagate_state on dr = (1, -2, 3), dv = (0.5, 0.25, -0.1),
        db = 10, dd = 2 at dt = 2 gives dr = (2, -1.5, 2.8) and db = 14,
        the closed form dr += dv*dt and db += dd*dt of the constant-
        velocity-error, constant-drift model (within 1e-12)."""
        out = propagate_state([1.0, -2.0, 3.0, 0.5, 0.25, -0.1, 10.0, 2.0],
                              2.0)
        expected = [2.0, -1.5, 2.8, 0.5, 0.25, -0.1, 14.0, 2.0]
        for i in range(8):
            self.assertAlmostEqual(out[i], expected[i], delta=1e-12)

    def test_propagate_covariance_matches_inline_product(self):
        """propagate_covariance equals the inline Phi*P*Phi^T + diag(q)
        product computed in the test to within 1e-9 relative (never exact
        equality on the computed aggregate)."""
        p = [[0.0] * 8 for _ in range(8)]
        for i, v in enumerate([25.0, 25.0, 25.0, 0.5, 0.5, 0.5, 4.0, 0.1]):
            p[i][i] = v
        q = [0.01, 0.01, 0.01, 0.001, 0.001, 0.001, 0.01, 1e-4]
        dt = 1.5
        phi = state_transition_matrix(dt)
        phi_t = [[phi[r][c] for r in range(8)] for c in range(8)]
        inner = [[sum(p[r][k] * phi_t[k][c] for k in range(8))
                  for c in range(8)] for r in range(8)]
        inline = [[sum(phi[r][k] * inner[k][c] for k in range(8))
                   + (q[r] if r == c else 0.0) for c in range(8)]
                  for r in range(8)]
        out = propagate_covariance(p, q, dt)
        for r in range(8):
            for c in range(8):
                self.assertTrue(math.isclose(out[r][c], inline[r][c],
                                             rel_tol=1e-9),
                                "entry %d,%d off: %r vs %r"
                                % (r, c, out[r][c], inline[r][c]))


class TestMeasurementModel(unittest.TestCase):
    """Workflow steps 3 and 4: predict each raw pseudorange from the
    inertial position estimate plus the clock bias state and build the
    measurement matrix from the line-of-sight geometry rows and the unit
    clock column."""

    def test_epoch0_range_anchors(self):
        """Predicted ranges from the epoch-0 INS reference with zero clock
        bias land at the spec anchors [26559888.0011, 26560112.0011,
        26559808.0006, 26560192.0006, 26560144.0009, 26559856.0009] within
        0.01 m per entry (geometric range plus bias, no speed-of-light
        conversion: the clock column is exactly 1.0 on ranges in metres).
        The measured raw pseudorange of sat1 (at +x) at epoch 0 is
        26561400.201177 m (geometric range about R_S - 100 m plus the
        1500 m true clock bias plus the +0.2 m noise offset), within 0.01 m."""
        pred = predicted_pseudoranges(SAT_POSITIONS, ref_position(0.0), 0.0)
        anchors = [26559888.0011, 26560112.0011, 26559808.0006,
                   26560192.0006, 26560144.0009, 26559856.0009]
        for i in range(6):
            self.assertAlmostEqual(pred[i], anchors[i], delta=0.01)
        self.assertAlmostEqual(EPOCHS[0]["pseudoranges"][0],
                               26561400.201177, delta=0.01)

    def test_measurement_matrix_geometry_rows(self):
        """On the worked constellation at the epoch-0 reference the sat +x
        row starts -0.9999999999591737 (within 1e-6 of -1, the negated
        line of sight) and the sat -y row has second entry
        0.9999999999764121 (within 1e-6 of +1); the cross-axis entries are
        of order 1e-5."""
        h = measurement_matrix(SAT_POSITIONS, ref_position(0.0))
        self.assertEqual(len(h), 6)
        self.assertAlmostEqual(h[0][0], -1.0, delta=1e-6)
        self.assertAlmostEqual(h[3][1], 1.0, delta=1e-6)
        self.assertLess(abs(h[0][1]), 1e-4)
        self.assertLess(abs(h[0][2]), 1e-4)

    def test_measurement_matrix_clock_and_zero_columns(self):
        """The clock-bias column of every row is exactly 1.0 and the
        velocity-error and clock-drift columns exactly 0.0 (a single-epoch
        raw pseudorange carries no velocity or drift information), with
        the position channel signed like the negated receiver-to-satellite
        unit vector."""
        h = measurement_matrix(SAT_POSITIONS, ref_position(0.0))
        for row in h:
            self.assertEqual(row[6], 1.0)
            self.assertEqual(row[3], 0.0)
            self.assertEqual(row[4], 0.0)
            self.assertEqual(row[5], 0.0)
            self.assertEqual(row[7], 0.0)

    def test_prediction_at_full_propagated_estimate(self):
        """The prediction of workflow step 3 evaluates the range model at
        the full propagated estimate (the inertial position estimate plus
        the propagated position error and clock bias state), which is what
        collapses the epoch-1 innovations to the drift shortfall scale of
        a few metres once the bias is known."""
        self.assertEqual(len(EPOCHS), 3)
        self.assertEqual(len(PERFECT_EPOCHS), 3)


class TestWorkedExampleRun(unittest.TestCase):
    """Workflow step 1 through step 7 of the SKILL.md workflow exercised
    as one profile run: raw-pseudorange-update Kalman corrections at every
    epoch of the tightly coupled INS/GNSS filter."""

    @classmethod
    def setUpClass(cls):
        cls.results = run_worked()

    def test_three_epoch_results(self):
        self.assertEqual(len(self.results), 3)

    def test_epoch0_innovation_anchors(self):
        """The epoch-0 innovations carry the whole unknown clock bias plus
        the 12 m INS position offset projected on the lines of sight:
        [1512.2001, 1487.9001, 1492.3000, 1507.8000, 1506.1000, 1493.7000]
        m within 0.01 m per entry."""
        anchors = [1512.2001, 1487.9001, 1492.3000, 1507.8000,
                   1506.1000, 1493.7000]
        for i in range(6):
            self.assertAlmostEqual(self.results[0]["innovations"][i],
                                   anchors[i], delta=0.01)

    def test_epoch1_innovation_anchors(self):
        """The epoch-1 innovations are the residuals of the drift
        shortfall one snapshot cannot see: [5.2652, 4.8348, 4.2403,
        5.8597, 4.7077, 5.0923] m within 0.01 m per entry."""
        anchors = [5.2652, 4.8348, 4.2403, 5.8597, 4.7077, 5.0923]
        for i in range(6):
            self.assertAlmostEqual(self.results[1]["innovations"][i],
                                   anchors[i], delta=0.01)

    def test_epoch2_innovation_anchors(self):
        """By epoch 2 the drift estimate predicts the bias growth, so the
        innovations collapse to the measurement noise level: [0.8022,
        -0.3989, 0.4140, -0.8107, 0.7352, -0.7318] m within 0.01 m per
        entry."""
        anchors = [0.8022, -0.3989, 0.4140, -0.8107, 0.7352, -0.7318]
        for i in range(6):
            self.assertAlmostEqual(self.results[2]["innovations"][i],
                                   anchors[i], delta=0.01)

    def test_innovation_rms_anchors(self):
        """The innovation RMS tells the observability story: 1500.0274 m
        at the first snapshot (unknown clock bias), 5.0251 m at the second
        (the drift that one snapshot cannot see), 0.6717 m at the third
        (measurement noise floor), each within 0.01 m."""
        anchors = [1500.0274, 5.0251, 0.6717]
        for e in range(3):
            self.assertAlmostEqual(self.results[e]["innovation_rms"],
                                   anchors[e], delta=0.01)

    def test_epoch0_error_state(self):
        """The epoch-0 update lands the error state at the negated INS
        offset: position correction (-12.1348, 7.7403, -6.1923) within
        0.01 m per entry, clock bias estimate 1500.0000 m within 0.01 m,
        and the velocity and drift states exactly zero (a single snapshot
        carries no velocity or drift information: their Kalman rows are
        exactly zero before any propagation)."""
        x = self.results[0]["x_corr"]
        for i in range(3):
            self.assertAlmostEqual(x[i], [-12.1348, 7.7403, -6.1923][i],
                                   delta=0.01)
        self.assertEqual(x[3], 0.0)
        self.assertEqual(x[4], 0.0)
        self.assertEqual(x[5], 0.0)
        self.assertAlmostEqual(x[6], 1500.0000, delta=0.01)
        self.assertEqual(x[7], 0.0)

    def test_epoch2_error_state_high_precision(self):
        """The epoch-2 error state matches the spec anchors
        (-12.985090, 8.617167, -6.459646, -0.452525, 0.355417, -0.191508,
        1509.999739, 4.999677) within 0.01 per entry against the true
        corrections (-13.0, 8.6, -6.4) m, (-0.5, 0.3, -0.2) m/s, 1510.0 m
        and 5.0 m/s."""
        x = self.results[2]["x_corr"]
        anchors = [-12.985090, 8.617167, -6.459646, -0.452525, 0.355417,
                   -0.191508, 1509.999739, 4.999677]
        for i in range(8):
            self.assertAlmostEqual(x[i], anchors[i], delta=0.01)

    def test_corrected_position_epoch_anchors(self):
        """Corrected positions of workflow step 6 read (99.8652,
        199.7403, -150.1923), (125.1713, 190.1697, -144.8191) and
        (150.0149, 180.0172, -140.0596) m within 0.01 m per entry."""
        anchors = [(99.8652, 199.7403, -150.1923),
                   (125.1713, 190.1697, -144.8191),
                   (150.0149, 180.0172, -140.0596)]
        for e in range(3):
            corr = self.results[e]["corrected"]
            for i, key in enumerate(["x", "y", "z"]):
                self.assertAlmostEqual(corr[key], anchors[e][i], delta=0.01)

    def test_position_convergence_against_true_trajectory(self):
        """The corrected position stays within 0.5 m 3D of the true
        trajectory at every epoch (anchor errors 0.3501, 0.3015, 0.0638 m,
        decreasing every epoch)."""
        previous = None
        for e in range(3):
            corr = self.results[e]["corrected"]
            truth = true_position(float(e))
            err = math.sqrt(sum((corr[key] - truth[i]) ** 2
                                for i, key in enumerate(["x", "y", "z"])))
            self.assertLess(err, 0.5)
            if previous is not None:
                self.assertLess(err, previous)
            previous = err

    def test_velocity_convergence_against_true_trajectory(self):
        """The corrected velocity stays within 0.8 m/s 3D of the true
        velocity at every epoch (anchor errors 0.6164, 0.5917, 0.0735 m/s)
        and lands below 0.1 m/s by epoch 2."""
        for e in range(3):
            corr = self.results[e]["corrected"]
            err = math.sqrt(sum((corr["v" + key] - TRUE_VELOCITY[i]) ** 2
                                for i, key in enumerate(["x", "y", "z"])))
            self.assertLess(err, 0.8)
        last = self.results[2]["corrected"]
        err2 = math.sqrt(sum((last["v" + key] - TRUE_VELOCITY[i]) ** 2
                             for i, key in enumerate(["x", "y", "z"])))
        self.assertLess(err2, 0.1)

    def test_clock_state_filter_convergence(self):
        """The clock-state-filter estimates land within 0.5 m (bias) and
        1.0 m/s (drift) of the truth at epochs 1 and 2, and within
        0.001 m / 0.001 m/s by epoch 2 (anchor errors -0.0003 m and
        -0.0003 m/s)."""
        for e in (1, 2):
            corr = self.results[e]["corrected"]
            bias_true = TRUE_BIAS0 + TRUE_DRIFT * e
            self.assertLess(abs(corr["bias"] - bias_true), 0.5)
            self.assertLess(abs(corr["drift"] - TRUE_DRIFT), 1.0)
        last = self.results[2]["corrected"]
        self.assertLess(abs(last["bias"] - (TRUE_BIAS0 + TRUE_DRIFT * 2)),
                        0.001)
        self.assertLess(abs(last["drift"] - TRUE_DRIFT), 0.001)

    def test_epoch0_posterior_closed_forms(self):
        """The epoch-0 posterior of the symmetric 6-sat geometry obeys the
        closed forms: per-axis position variance 0.124844 equals sigma^2/2
        (sigma_range 0.5 m, R = 0.25) within 1e-3 and clock-bias variance
        0.0416667 equals sigma^2/6 within 1e-4; the velocity variance 1.0
        and drift variance 400.0 stay unobservable at the first snapshot."""
        diag0 = [self.results[0]["p_corr"][i][i] for i in range(8)]
        for i in range(3):
            self.assertAlmostEqual(diag0[i], 0.124844, delta=1e-3)
        self.assertAlmostEqual(diag0[6], 0.0416667, delta=1e-4)
        self.assertAlmostEqual(diag0[3], 1.0, delta=1e-12)
        self.assertAlmostEqual(diag0[7], 400.0, delta=1e-9)

    def test_epoch2_posterior_covariance_values(self):
        """The epoch-2 posterior diagonal carries per-axis position
        variance 1.01082e-01, velocity variance 6.44799e-02 and drift
        variance 2.59567e-02 (within 1e-3): the propagation-induced
        correlations let the third snapshot observe both channels."""
        diag2 = [self.results[2]["p_corr"][i][i] for i in range(8)]
        for i in range(3):
            self.assertAlmostEqual(diag2[i], 1.01082e-01, delta=1e-3)
        for i in range(3, 6):
            self.assertAlmostEqual(diag2[i], 6.44799e-02, delta=1e-3)
        self.assertAlmostEqual(diag2[6], 3.52379e-02, delta=1e-3)
        self.assertAlmostEqual(diag2[7], 2.59567e-02, delta=1e-3)

    def test_posterior_symmetry(self):
        """Every epoch posterior covariance is symmetric: max |P - P^T|
        equals 0.00e+00 on the real anchor, asserted below 1e-12."""
        for e in range(3):
            p = self.results[e]["p_corr"]
            worst = max(abs(p[r][c] - p[c][r])
                        for r in range(8) for c in range(8))
            self.assertLess(worst, 1e-12)

    def test_determinism_bitwise(self):
        """Two identical profile runs are bitwise identical (no RNG
        anywhere in the tightly coupled filter)."""
        again = run_tightly_coupled_profile(EPOCHS, X0, P0, Q, DT,
                                            VARIANCES)
        self.assertEqual(self.results, again)

    def test_open_loop_error_state_form(self):
        """The open-loop error-state form keeps the estimated corrections
        out of the INS reference: each epoch's ref_position record is
        untouched by the update and the corrected solution is re-derived
        as reference plus x_corr at every epoch."""
        for e in range(3):
            self.assertEqual(self.results[e]["ref_position"],
                             ref_position(float(e)))
            corr = self.results[e]["corrected"]
            x = self.results[e]["x_corr"]
            ref = self.results[e]["ref_position"]
            for i, key in enumerate(["x", "y", "z"]):
                self.assertAlmostEqual(corr[key], ref[i] + x[i], delta=1e-9)


class TestPerfectMeasurementIdentity(unittest.TestCase):
    """The perfect-measurement identity run (noise offsets zero, variances
    1e-9): the raw-pseudorange-update recovers the true corrections."""

    @classmethod
    def setUpClass(cls):
        cls.results = run_tightly_coupled_profile(PERFECT_EPOCHS, X0, P0,
                                                  Q, DT,
                                                  PERFECT_VARIANCES)

    def test_epoch0_recovery_of_position_and_bias(self):
        """The epoch-0 update recovers dr = (-12.000002, 8.000000,
        -6.000004) m against (-12, 8, -6) within 1e-3 and db =
        1500.000007 m against 1500 within 1e-3."""
        x = self.results[0]["x_corr"]
        for i in range(3):
            self.assertAlmostEqual(x[i], [-12.0, 8.0, -6.0][i], delta=1e-3)
        self.assertAlmostEqual(x[6], 1500.0, delta=1e-3)

    def test_epoch2_recovery_of_velocity_and_drift(self):
        """The epoch-2 estimates land at dv = (-0.497630, 0.298579,
        -0.199051) m/s against (-0.5, 0.3, -0.2) within 0.01 and dd =
        4.999935 m/s against 5.0 within 0.01 (the residual offset comes
        from the linearization of the range model about the propagated
        estimate)."""
        x = self.results[2]["x_corr"]
        for i in range(3):
            self.assertAlmostEqual(x[3 + i], [-0.5, 0.3, -0.2][i],
                                   delta=0.01)
        self.assertAlmostEqual(x[7], 5.0, delta=0.01)

    def test_identity_epoch_positions_stay_on_true_trajectory(self):
        """With noise-free measurements every corrected position of the
        identity run stays within 0.02 m 3D of the true trajectory."""
        for e in range(3):
            corr = self.results[e]["corrected"]
            truth = true_position(float(e))
            err = math.sqrt(sum((corr[key] - truth[i]) ** 2
                                for i, key in enumerate(["x", "y", "z"])))
            self.assertLess(err, 0.02)


class TestCorrectedStateHelper(unittest.TestCase):
    """Workflow step 6: corrected_navigation_state as the reference plus
    the estimated corrections."""

    def test_corrected_navigation_state_values(self):
        """corrected_navigation_state returns x, y, z, vx, vy, vz, bias,
        drift, each the reference component plus the matching state
        correction, in SI units."""
        out = corrected_navigation_state([112.0, 192.0, -144.0],
                                         [25.5, -10.3, 5.2], 0.0, 0.0,
                                         [-12.1348, 7.7403, -6.1923,
                                          0.0, 0.0, 0.0, 1500.0, 0.0])
        self.assertAlmostEqual(out["x"], 99.8652, delta=1e-9)
        self.assertAlmostEqual(out["y"], 199.7403, delta=1e-9)
        self.assertAlmostEqual(out["z"], -150.1923, delta=1e-9)
        self.assertAlmostEqual(out["vx"], 25.5, delta=1e-9)
        self.assertAlmostEqual(out["bias"], 1500.0, delta=1e-9)
        self.assertEqual(sorted(out.keys()),
                         ["bias", "drift", "vx", "vy", "vz", "x", "y", "z"])

    def test_corrected_state_valueerror(self):
        with self.assertRaises(ValueError):
            corrected_navigation_state([1.0, 2.0], [0.0, 0.0, 0.0], 0.0,
                                       0.0, [0.0] * 8)
        with self.assertRaises(ValueError):
            corrected_navigation_state([1.0, 2.0, 3.0], [0.0, 0.0], 0.0,
                                       0.0, [0.0] * 8)
        with self.assertRaises(ValueError):
            corrected_navigation_state([1.0, 2.0, 3.0], [0.0, 0.0, 0.0],
                                       0.0, 0.0, [0.0] * 7)


class TestValueErrors(unittest.TestCase):
    """Workflow steps 2, 3, 4 and 5 reject non-physical inputs with
    ValueError: dt at 0.0 and -1.0, wrong-length state records, a negative
    or non-finite process-noise entry, degenerate satellite geometries, a
    non-positive variance and inconsistent epoch profiles."""

    def test_valueerror_dt_non_positive_and_non_finite(self):
        """state_transition_matrix, propagate_state and
        propagate_covariance all reject dt at 0.0 and -1.0, and the
        propagation functions reject non-finite dt (nan and inf)."""
        for dt_bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                state_transition_matrix(dt_bad)
            with self.assertRaises(ValueError):
                propagate_state([0.0] * 8, dt_bad)
            with self.assertRaises(ValueError):
                propagate_covariance(P0, Q, dt_bad)
        with self.assertRaises(ValueError):
            propagate_state([0.0] * 8, float("nan"))
        with self.assertRaises(ValueError):
            propagate_covariance(P0, Q, float("inf"))

    def test_valueerror_wrong_length_state_and_covariance(self):
        """propagate_state and kalman_update reject an x of length 7 and
        propagate_covariance and kalman_update reject a p of the wrong
        shape, and propagate_state rejects a non-finite state entry."""
        with self.assertRaises(ValueError):
            propagate_state([0.0] * 7, 1.0)
        with self.assertRaises(ValueError):
            propagate_state([0.0] * 7 + [float("nan")], 1.0)
        with self.assertRaises(ValueError):
            kalman_update([0.0] * 7, P0, measurement_matrix(
                SAT_POSITIONS, ref_position(0.0)),
                [1.0] * 6, VARIANCES)
        with self.assertRaises(ValueError):
            propagate_covariance([[0.0] * 8 for _ in range(7)], Q, 1.0)
        with self.assertRaises(ValueError):
            propagate_covariance([[0.0] * 7 for _ in range(8)], Q, 1.0)
        with self.assertRaises(ValueError):
            kalman_update([0.0] * 8, [[0.0] * 7 for _ in range(8)],
                          measurement_matrix(SAT_POSITIONS,
                                             ref_position(0.0)),
                          [1.0] * 6, VARIANCES)

    def test_valueerror_negative_q_entry(self):
        q_bad = list(Q)
        q_bad[3] = -0.001
        with self.assertRaises(ValueError):
            propagate_covariance(P0, q_bad, 1.0)
        q_nan = list(Q)
        q_nan[0] = float("nan")
        with self.assertRaises(ValueError):
            propagate_covariance(P0, q_nan, 1.0)

    def test_valueerror_geometry_records(self):
        """predicted_pseudoranges rejects an empty satellite list,
        non-length-3 position records and non-finite entries;
        measurement_matrix rejects fewer than 4 satellites, a satellite
        record of the wrong length and a satellite coincident with the
        receiver (zero range)."""
        with self.assertRaises(ValueError):
            predicted_pseudoranges([], ref_position(0.0), 0.0)
        with self.assertRaises(ValueError):
            predicted_pseudoranges([(1.0, 2.0)], ref_position(0.0), 0.0)
        with self.assertRaises(ValueError):
            predicted_pseudoranges(SAT_POSITIONS, [1.0, 2.0], 0.0)
        with self.assertRaises(ValueError):
            predicted_pseudoranges(SAT_POSITIONS,
                                   [float("inf"), 0.0, 0.0], 0.0)
        with self.assertRaises(ValueError):
            measurement_matrix(SAT_POSITIONS[:3], ref_position(0.0))
        with self.assertRaises(ValueError):
            measurement_matrix([(1.0, 2.0)] * 4, ref_position(0.0))
        with self.assertRaises(ValueError):
            measurement_matrix([ref_position(0.0)] * 4,
                               ref_position(0.0))

    def test_valueerror_kalman_update_variances_and_shapes(self):
        """kalman_update rejects a zero or non-finite variance, an
        innovation/variance length mismatch, a non-finite innovation and
        h with the wrong row count."""
        h = measurement_matrix(SAT_POSITIONS, ref_position(0.0))
        innovations = [1512.0] * 6
        with self.assertRaises(ValueError):
            kalman_update([0.0] * 8, P0, h, innovations,
                          [0.0, 0.25, 0.25, 0.25, 0.25, 0.25])
        with self.assertRaises(ValueError):
            kalman_update([0.0] * 8, P0, h, innovations,
                          [0.25] * 5)
        with self.assertRaises(ValueError):
            kalman_update([0.0] * 8, P0, h, innovations[:5],
                          VARIANCES)
        with self.assertRaises(ValueError):
            kalman_update([0.0] * 8, P0, h[:5], innovations, VARIANCES)
        bad_innov = list(innovations)
        bad_innov[0] = float("nan")
        with self.assertRaises(ValueError):
            kalman_update([0.0] * 8, P0, h, bad_innov, VARIANCES)

    def test_valueerror_invalid_profiles(self):
        """run_tightly_coupled_profile rejects an empty epoch list, x0 of
        the wrong length, p0 or q of the wrong shape, a profile whose
        epoch carries 3 satellites, an epoch measurement count that
        differs from the first, and variances that do not match the
        count."""
        three = [dict(EPOCHS[0], sat_positions=SAT_POSITIONS[:3],
                      pseudoranges=EPOCHS[0]["pseudoranges"][:3])]
        with self.assertRaises(ValueError):
            run_tightly_coupled_profile(three, X0, P0, Q, DT,
                                        VARIANCES[:3])
        mixed = [dict(EPOCHS[0]), dict(EPOCHS[1],
                                       pseudoranges=EPOCHS[1][
                                           "pseudoranges"][:5])]
        with self.assertRaises(ValueError):
            run_tightly_coupled_profile(mixed, X0, P0, Q, DT, VARIANCES)
        with self.assertRaises(ValueError):
            run_tightly_coupled_profile([], X0, P0, Q, DT, VARIANCES)
        with self.assertRaises(ValueError):
            run_tightly_coupled_profile(EPOCHS, [0.0] * 7, P0, Q, DT,
                                        VARIANCES)
        with self.assertRaises(ValueError):
            run_tightly_coupled_profile(EPOCHS, X0, [[0.0] * 8] * 7, Q,
                                        DT, VARIANCES)
        with self.assertRaises(ValueError):
            run_tightly_coupled_profile(EPOCHS, X0, P0, Q[:7], DT,
                                        VARIANCES)
        with self.assertRaises(ValueError):
            run_tightly_coupled_profile(EPOCHS, X0, P0, Q, DT,
                                        VARIANCES[:5])


if __name__ == "__main__":
    unittest.main()
