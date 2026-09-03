"""Contract test for the rts-smoother leaf (gnc-autonomy/estimation-filtering).

Runs offline with pure stdlib unittest:

    python3 scripts/test_rts_smoother.py

Covers the 2x2 matrix helpers, the constant-velocity forward Kalman
filter on the 10-sample worked example, the worked-example anchors at
k=9 (filtered), k=0 and k=4 (smoothed), the covariance reduction
verdicts, the boundary identity, the smoother gain anchor, the
noiseless-ramp identity, and ValueError rejection of non-physical
inputs.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rts_smoother_logic import (  # noqa: E402
    forward_kalman,
    rts_smooth,
    smoother_reduction,
    mat_mul,
    mat_add,
    mat_sub,
    mat_scale,
    transpose,
    mat_vec,
    inv_2x2,
)

DT = 1.0
Q = 0.1
R = 25.0
X0 = [0.0, 5.0]
P0 = [[100.0, 0.0], [0.0, 10.0]]
MEASUREMENTS = [2.1, 6.8, 11.9, 16.4, 21.2, 26.5, 30.9, 36.2, 41.4, 45.8]


def run_worked_example():
    """Run the spec worked example and return the three smoother lists."""
    fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
    return rts_smooth(fwd)


class TestMatrixHelpers(unittest.TestCase):
    """2x2 linear-algebra helpers used by the filter and smoother."""

    def test_mat_mul_2x2(self):
        a = [[1.0, 2.0], [3.0, 4.0]]
        b = [[5.0, 6.0], [7.0, 8.0]]
        self.assertEqual(mat_mul(a, b), [[19.0, 22.0], [43.0, 50.0]])

    def test_mat_add_and_sub(self):
        a = [[1.0, 2.0], [3.0, 4.0]]
        b = [[5.0, 6.0], [7.0, 8.0]]
        self.assertEqual(mat_add(a, b), [[6.0, 8.0], [10.0, 12.0]])
        self.assertEqual(mat_sub(b, a), [[4.0, 4.0], [4.0, 4.0]])

    def test_mat_scale(self):
        a = [[1.0, -2.0], [3.0, 4.0]]
        self.assertEqual(mat_scale(a, 0.5), [[0.5, -1.0], [1.5, 2.0]])

    def test_transpose(self):
        self.assertEqual(transpose([[1.0, 2.0], [3.0, 4.0]]),
                         [[1.0, 3.0], [2.0, 4.0]])
        self.assertEqual(transpose([[2.0], [5.0]]), [[2.0, 5.0]])

    def test_inv_2x2_roundtrip(self):
        a = [[4.0, 7.0], [2.0, 6.0]]
        eye = mat_mul(a, inv_2x2(a))
        for i in range(2):
            for j in range(2):
                want = 1.0 if i == j else 0.0
                self.assertAlmostEqual(eye[i][j], want, places=12)

    def test_inv_2x2_singular_raises(self):
        with self.assertRaises(ValueError):
            inv_2x2([[1.0, 2.0], [2.0, 4.0]])


class TestForwardKalman(unittest.TestCase):
    """Forward constant-velocity Kalman recursion on the worked example."""

    def test_forward_length_and_record_keys(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        self.assertEqual(len(fwd), 10)
        for record in fwd:
            for key in ("x_pred", "P_pred", "x_filt", "P_filt",
                        "innovation", "innovation_variance"):
                self.assertIn(key, record)

    def test_forward_state_and_covariance_shapes(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        for record in fwd:
            self.assertEqual(len(record["x_pred"]), 2)
            self.assertEqual(len(record["x_filt"]), 2)
            self.assertEqual(len(record["P_pred"]), 2)
            self.assertEqual(len(record["P_pred"][0]), 2)
            self.assertEqual(len(record["P_filt"]), 2)
            self.assertEqual(len(record["P_filt"][0]), 2)


    def test_forward_first_prediction_from_prior(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        x_pred0 = [0.0 + DT * 5.0, 5.0]
        for i in range(2):
            self.assertAlmostEqual(fwd[0]["x_pred"][i], x_pred0[i], places=12)

    def test_forward_innovation_variance_is_predicted_plus_r(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        for record in fwd:
            s = record["P_pred"][0][0] + R
            self.assertAlmostEqual(record["innovation_variance"], s, places=9)


    def test_forward_filtered_anchor_k9(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        self.assertAlmostEqual(fwd[9]["x_filt"][0], 45.8108, delta=0.01)
        self.assertAlmostEqual(fwd[9]["x_filt"][1], 4.8570, delta=0.01)

    def test_forward_covariance_anchor_k9(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        self.assertAlmostEqual(fwd[9]["P_filt"][0][0], 8.8487, delta=0.01)
        self.assertAlmostEqual(fwd[9]["P_filt"][1][1], 0.5941, delta=0.01)

    def test_forward_filtered_at_k4(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        self.assertAlmostEqual(fwd[4]["P_filt"][0][0], 12.7131, delta=0.01)
        self.assertAlmostEqual(fwd[4]["P_filt"][1][1], 1.8860, delta=0.01)

    def test_forward_final_innovation_variance_anchor(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        self.assertAlmostEqual(fwd[9]["innovation_variance"], 38.697,
                               delta=0.01)


    def test_forward_rejects_nonpositive_dt(self):
        with self.assertRaises(ValueError):
            forward_kalman(MEASUREMENTS, 0.0, Q, R, X0, P0)
        with self.assertRaises(ValueError):
            forward_kalman(MEASUREMENTS, -1.0, Q, R, X0, P0)

    def test_forward_rejects_negative_process_noise(self):
        with self.assertRaises(ValueError):
            forward_kalman(MEASUREMENTS, DT, -1.0, R, X0, P0)

    def test_forward_rejects_nonpositive_measurement_variance(self):
        with self.assertRaises(ValueError):
            forward_kalman(MEASUREMENTS, DT, Q, 0.0, X0, P0)

    def test_forward_rejects_single_measurement(self):
        with self.assertRaises(ValueError):
            forward_kalman([2.1], DT, Q, R, X0, P0)

    def test_forward_rejects_bad_x0_length(self):
        with self.assertRaises(ValueError):
            forward_kalman(MEASUREMENTS, DT, Q, R, [0.0], P0)

    def test_forward_rejects_bad_p0_shape(self):
        with self.assertRaises(ValueError):
            forward_kalman(MEASUREMENTS, DT, Q, R, X0, [[100.0, 0.0]])


class TestRtsSmooth(unittest.TestCase):
    """Fixed-interval RTS backward recursion."""

    def test_smooth_output_lengths(self):
        xs, ps, gains = run_worked_example()
        self.assertEqual(len(xs), 10)
        self.assertEqual(len(ps), 10)
        self.assertEqual(len(gains), 10)

    def test_smooth_boundary_identity_state(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        xs, _, _ = rts_smooth(fwd)
        for i in range(2):
            self.assertAlmostEqual(xs[9][i], fwd[9]["x_filt"][i], places=12)

    def test_smooth_anchor_k0(self):
        xs, _, _ = run_worked_example()
        self.assertAlmostEqual(xs[0][0], 2.2080, delta=0.01)
        self.assertAlmostEqual(xs[0][1], 4.8275, delta=0.01)

    def test_smooth_anchor_k4(self):
        xs, _, _ = run_worked_example()
        self.assertAlmostEqual(xs[4][0], 21.5444, delta=0.01)
        self.assertAlmostEqual(xs[4][1], 4.8439, delta=0.01)

    def test_smooth_covariance_anchor_k4(self):
        _, ps, _ = run_worked_example()
        self.assertAlmostEqual(ps[4][0][0], 2.7726, delta=0.01)
        self.assertAlmostEqual(ps[4][1][1], 0.3326, delta=0.01)

    def test_smooth_covariance_below_filtered_at_k4(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        _, ps, _ = rts_smooth(fwd)
        self.assertLess(ps[4][0][0], fwd[4]["P_filt"][0][0])
        self.assertLess(ps[4][1][1], fwd[4]["P_filt"][1][1])

    def test_smooth_gain_anchor_k0(self):
        _, _, gains = run_worked_example()
        self.assertAlmostEqual(gains[0][0][0], 0.9983, delta=1e-3)
        self.assertAlmostEqual(gains[0][1][0], 0.0034, delta=1e-3)

    def test_smooth_final_gain_is_placeholder(self):
        _, _, gains = run_worked_example()
        self.assertEqual(gains[9], [[0.0, 0.0], [0.0, 0.0]])

    def test_smooth_reduction_verdict(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        _, ps, _ = rts_smooth(fwd)
        verdict = smoother_reduction(fwd, ps)
        self.assertTrue(verdict["all_reduced"])
        self.assertTrue(verdict["boundary_matches"])
        self.assertGreater(verdict["max_reduction"], 0.0)
        self.assertAlmostEqual(verdict["max_reduction"], 0.7819, delta=1e-3)

    def test_smooth_rejects_single_record(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        with self.assertRaises(ValueError):
            rts_smooth(fwd[:1])

    def test_smooth_rejects_missing_record_key(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        bad = [dict(record) for record in fwd]
        del bad[3]["P_filt"]
        with self.assertRaises(ValueError):
            rts_smooth(bad)

    def test_smooth_reduction_length_mismatch_raises(self):
        fwd = forward_kalman(MEASUREMENTS, DT, Q, R, X0, P0)
        _, ps, _ = rts_smooth(fwd)
        with self.assertRaises(ValueError):
            smoother_reduction(fwd, ps[:-1])

    def test_noiseless_ramp_identity(self):
        # Exact constant-velocity model (q = 0.0); the initial state sits on
        # the ramp at the epoch before the first sample so the prior and the
        # measurements are mutually consistent and the identity is exact.
        ramp = [5.0 * k for k in range(10)]
        fwd = forward_kalman(ramp, DT, 0.0, R, [-5.0, 5.0], P0)
        xs, _, _ = rts_smooth(fwd)
        for k in range(10):
            self.assertAlmostEqual(xs[k][0], ramp[k], delta=1e-6)
            self.assertAlmostEqual(xs[k][1], 5.0, delta=1e-9)

    def test_noiseless_ramp_identity_shifted_prior(self):
        # Same identity with the worked-example prior x0 = [0, 5] placed on a
        # shifted noiseless ramp (position 5*k at the measurement epochs).
        ramp = [5.0 * k for k in range(1, 11)]
        fwd = forward_kalman(ramp, DT, 0.0, R, X0, P0)
        xs, _, _ = rts_smooth(fwd)
        for k in range(10):
            self.assertAlmostEqual(xs[k][1], 5.0, delta=1e-9)



if __name__ == "__main__":
    unittest.main()
