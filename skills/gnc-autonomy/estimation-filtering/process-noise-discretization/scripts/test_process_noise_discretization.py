"""Contract test for the process-noise-discretization leaf
(gnc-autonomy/estimation-filtering).

Runs offline with pure stdlib unittest:

    python3 scripts/test_process_noise_discretization.py

Covers the van Loan discretization of the continuous white-noise
spectral density into the discrete process-noise covariance: step 1 of
the SKILL.md workflow (continuous model setup, F and Qc validation),
step 2 (the continuous noise map W = G*Qc*G^T), step 3 (the exact state
transition matrix by the matrix exponential with scaling and squaring),
step 4 (the van Loan augmented-matrix discretization into phi_d and qd),
step 5 (the closed-form verification against the discrete white noise
acceleration, scalar random walk and INS velocity random walk models),
and the worked-example anchors, the small-dt Euler limit toward the
continuous noise strength, the 2-D planar block-diagonal case, bitwise
determinism, and ValueError rejection of non-physical inputs that would
otherwise poison the filter propagation step of a consuming leaf.
"""

import os
import sys
import unittest
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from process_noise_discretization_logic import (
    mat_exp,
    state_transition_matrix,
    continuous_noise_map,
    van_loan_discretize,
    discrete_white_noise_acceleration,
    random_walk_covariance,
    ins_velocity_random_walk_covariance,
)

DWA_F = [[0.0, 1.0], [0.0, 0.0]]
DWA_G = [[0.0], [1.0]]
DWA_QC = [[0.25]]           # (m/s^2)^2 per Hz, continuous acceleration PSD


def _max_abs_diff(a, b):
    """Maximum absolute entry difference between two equal-shape lists."""
    best = 0.0
    for i in range(len(a)):
        for j in range(len(a[i])):
            d = abs(a[i][j] - b[i][j])
            if d > best:
                best = d
    return best


def _max_rel_diff(a, b):
    """Maximum entrywise relative difference (abs diff when b entry is 0)."""
    best = 0.0
    for i in range(len(a)):
        for j in range(len(a[i])):
            d = abs(a[i][j] - b[i][j]) / max(1e-300, abs(b[i][j]))
            if d > best:
                best = d
    return best


class TestMatExp(unittest.TestCase):
    """Matrix exponential by scaling and squaring (workflow step 3)."""

    def test_zero_matrix_is_identity_exact(self):
        """The identity matrix for the zero matrix is exact (step 3 of the
        SKILL.md workflow, the exact matrix exponential)."""
        self.assertEqual(mat_exp([[0.0, 0.0], [0.0, 0.0]]),
                         [[1.0, 0.0], [0.0, 1.0]])
        self.assertEqual(mat_exp([[0.0]]), [[1.0]])

    def test_scalar_exponential_matches_e(self):
        """The scalar exponential exp(1) matches e to 1e-12 relative."""
        got = mat_exp([[1.0]])[0][0]
        self.assertTrue(math.isclose(got, math.e, rel_tol=1e-12))

    def test_nilpotent_dwa_is_exact_closed_form(self):
        """The nilpotent DWA exponential exp([[0,1],[0,0]]) is the exact
        [[1,1],[0,1]] shear to 1e-12 absolute."""
        got = mat_exp([[0.0, 1.0], [0.0, 0.0]])
        self.assertLess(_max_abs_diff(got, [[1.0, 1.0], [0.0, 1.0]]), 1e-12)

    def test_scaling_and_squaring_large_norm(self):
        """A large-norm input exercises the scaling-and-squaring path:
        exp(10) matches e^10 to 1e-9 relative."""
        got = mat_exp([[10.0]])[0][0]
        self.assertTrue(math.isclose(got, math.exp(10.0), rel_tol=1e-9))

    def test_full_matrix_matches_truncated_series(self):
        """The scaling-and-squaring result on a full 2x2 matrix matches a
        naive 40-term power series to 1e-9 relative (step 3 of the
        SKILL.md workflow, the matrix exponential algorithm)."""
        a = [[0.7, 1.2], [-0.4, 0.3]]
        got = mat_exp(a)
        cur = [row[:] for row in a]
        total = [[(1.0 if i == j else 0.0) + a[i][j] for j in range(2)]
                 for i in range(2)]
        for k in range(2, 41):
            cur = [[cur[i][0] * a[0][j] + cur[i][1] * a[1][j]
                    for j in range(2)] for i in range(2)]
            cur = [[v / k for v in row] for row in cur]
            total = [[total[i][j] + cur[i][j] for j in range(2)]
                     for i in range(2)]
        self.assertLess(_max_rel_diff(got, total), 1e-9)

    def test_non_square_and_empty_raise(self):
        """Non-square and empty inputs raise ValueError on mat_exp."""
        with self.assertRaises(ValueError):
            mat_exp([[1.0, 0.0]])
        with self.assertRaises(ValueError):
            mat_exp([])


class TestStateTransitionMatrix(unittest.TestCase):
    """Exact state transition matrix Phi_d = exp(F*dt) (workflow step 3)."""

    def test_dwa_dt1_equals_shear(self):
        """state_transition_matrix on the DWA F at dt = 1.0 equals the
        [[1, 1],[0, 1]] shear within 1e-12 absolute (workflow step 3)."""
        phi = state_transition_matrix(DWA_F, 1.0)
        self.assertLess(_max_abs_diff(phi, [[1.0, 1.0], [0.0, 1.0]]), 1e-12)

    def test_matches_van_loan_phi(self):
        """The step-3 transition matrix equals the phi_d returned by the
        step-4 van Loan discretization within 1e-12 absolute."""
        phi = state_transition_matrix(DWA_F, 1.0)
        phi_vl, _ = van_loan_discretize(DWA_F, DWA_G, DWA_QC, 1.0)
        self.assertLess(_max_abs_diff(phi, phi_vl), 1e-12)

    def test_non_square_f_raises(self):
        """A non-square F raises ValueError."""
        with self.assertRaises(ValueError):
            state_transition_matrix([[1.0, 0.0]], 0.1)

    def test_dt_zero_and_negative_raise(self):
        """dt at 0 and at -0.1 raise ValueError on the transition matrix."""
        with self.assertRaises(ValueError):
            state_transition_matrix(DWA_F, 0.0)
        with self.assertRaises(ValueError):
            state_transition_matrix(DWA_F, -0.1)


class TestContinuousNoiseMap(unittest.TestCase):
    """Continuous noise strength W = G*Qc*G^T (workflow step 2)."""

    def test_scalar_map(self):
        """For G = [[1]], Qc = [[0.01]] the map returns W = [[0.01]]
        exactly (workflow step 2, the continuous noise strength)."""
        self.assertEqual(continuous_noise_map([[1.0]], [[0.01]]), [[0.01]])

    def test_dwa_map_velocity_axis(self):
        """For the DWA model the velocity-axis strength W[1][1] equals the
        continuous PSD q = 0.25."""
        self.assertEqual(continuous_noise_map(DWA_G, DWA_QC),
                         [[0.0, 0.0], [0.0, 0.25]])

    def test_two_axis_map_is_diagonal(self):
        """Two independent axes with Qc = diag(0.25, 0.5) keep the noise
        strength block diagonal with zero cross coupling."""
        g = [[0.0, 0.0], [1.0, 0.0], [0.0, 0.0], [0.0, 1.0]]
        qc = [[0.25, 0.0], [0.0, 0.5]]
        w = continuous_noise_map(g, qc)
        self.assertLess(_max_abs_diff(
            w, [[0.0, 0.0, 0.0, 0.0], [0.0, 0.25, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.5]]), 1e-15)

    def test_empty_and_ragged_g_raise(self):
        """An empty or ragged G raises ValueError."""
        with self.assertRaises(ValueError):
            continuous_noise_map([], [[0.01]])
        with self.assertRaises(ValueError):
            continuous_noise_map([[1.0], [0.5, 1.0]], [[0.01]])

    def test_shape_mismatches_raise(self):
        """G columns not matching the Qc order, and a non-square Qc, both
        raise ValueError (step 1 of the SKILL.md workflow, the continuous
        model validation that keeps a malformed spectral density out)."""
        with self.assertRaises(ValueError):
            continuous_noise_map([[1.0, 0.0]], [[0.01]])
        with self.assertRaises(ValueError):
            continuous_noise_map([[1.0, 0.0]], [[0.01, 0.0]])

    def test_not_psd_qc_raises(self):
        """Asymmetric, negative definite [[-1.0]] and indefinite
        [[1.0, 2.0],[2.0, 1.0]] Qc all raise ValueError."""
        with self.assertRaises(ValueError):
            continuous_noise_map([[1.0, 0.0], [0.0, 1.0]],
                                 [[0.01, 0.5], [0.0, 0.02]])
        with self.assertRaises(ValueError):
            continuous_noise_map([[1.0]], [[-1.0]])
        with self.assertRaises(ValueError):
            continuous_noise_map([[1.0, 0.0], [0.0, 1.0]],
                                 [[1.0, 2.0], [2.0, 1.0]])


class TestVanLoanDiscretize(unittest.TestCase):
    """The van Loan discretization into (phi_d, qd) (workflow step 4)."""

    def test_scalar_random_walk_exact(self):
        """The F = 0 scalar random walk (q = 0.01, dt = 0.1) returns
        Phi_d = [[1]] and Qd = [[0.001]] within 1e-15, matching the
        step-5 scalar random walk closed form q*dt."""
        phi, qd = van_loan_discretize([[0.0]], [[1.0]], [[0.01]], 0.1)
        self.assertLess(_max_abs_diff(phi, [[1.0]]), 1e-15)
        self.assertLess(_max_abs_diff(qd, [[0.001]]), 1e-15)
        self.assertTrue(math.isclose(qd[0][0],
                                     random_walk_covariance(0.1, 0.01),
                                     rel_tol=1e-15, abs_tol=1e-15))

    def test_dwa_dt1_matches_closed_form(self):
        """The DWA van Loan discretization at dt = 1.0, q = 0.25 equals
        discrete_white_noise_acceleration(1.0, 0.25) within 1e-12
        relative (the real values differ by one ULP on the [0][0] entry,
        so never assert exact equality)."""
        _, qd = van_loan_discretize(DWA_F, DWA_G, DWA_QC, 1.0)
        closed = discrete_white_noise_acceleration(1.0, 0.25)
        self.assertLess(_max_rel_diff(qd, closed), 1e-12)

    def test_dwa_dt1_anchor_entries(self):
        """The dt = 1.0 DWA anchor entries q*dt^3/3 = 0.08333333333333334,
        q*dt^2/2 = 0.125 and q*dt = 0.25 appear within 1e-12 absolute."""
        _, qd = van_loan_discretize(DWA_F, DWA_G, DWA_QC, 1.0)
        self.assertTrue(math.isclose(qd[0][0], 0.08333333333333334,
                                     rel_tol=1e-12))
        self.assertTrue(math.isclose(qd[0][1], 0.125, rel_tol=1e-12))
        self.assertTrue(math.isclose(qd[1][1], 0.25, rel_tol=1e-12))

    def test_dwa_dt01_matches_closed_form(self):
        """The DWA van Loan discretization at dt = 0.1 s (a 100 ms filter
        step) equals the closed form within 1e-12 relative."""
        _, qd = van_loan_discretize(DWA_F, DWA_G, DWA_QC, 0.1)
        closed = discrete_white_noise_acceleration(0.1, 0.25)
        self.assertLess(_max_rel_diff(qd, closed), 1e-12)

    def test_small_dt_euler_limit(self):
        """The small-dt Euler limit Qd[1][1]/dt tends to the continuous
        strength q = 0.25: within 1e-6 at dt = 0.1 (workflow step 2, the
        continuous noise map entry the propagated integral approaches)."""
        _, qd = van_loan_discretize(DWA_F, DWA_G, DWA_QC, 0.1)
        self.assertTrue(math.isclose(qd[1][1] / 0.1, 0.25, rel_tol=1e-6))

    def test_qd_symmetric_and_psd(self):
        """Qd is symmetric: |Qd[0][1] - Qd[1][0]| below 1e-12, and Qd is
        positive semi-definite for PSD Qc (its eigenvalues, the diagonal
        of the DWA form, are non-negative)."""
        _, qd = van_loan_discretize(DWA_F, DWA_G, DWA_QC, 1.0)
        self.assertLess(abs(qd[0][1] - qd[1][0]), 1e-12)
        self.assertGreaterEqual(qd[0][0], 0.0)
        self.assertGreaterEqual(qd[1][1], 0.0)

    def test_2d_planar_block_diagonal(self):
        """The 2-D planar case (4 states, Qc = diag(0.25, 0.5), dt = 0.1)
        gives a Qd block diagonal with per-axis DWA blocks within 1e-12
        relative and zero cross-axis coupling (workflow step 5, the
        per-axis discrete white noise acceleration closed forms)."""
        f = [[0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0],
             [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 0.0]]
        g = [[0.0, 0.0], [1.0, 0.0], [0.0, 0.0], [0.0, 1.0]]
        qc = [[0.25, 0.0], [0.0, 0.5]]
        phi, qd = van_loan_discretize(f, g, qc, 0.1)
        block_x = discrete_white_noise_acceleration(0.1, 0.25)
        block_y = discrete_white_noise_acceleration(0.1, 0.5)
        self.assertLess(_max_abs_diff(phi, [
            [1.0, 0.1, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.1], [0.0, 0.0, 0.0, 1.0]]), 1e-12)
        for i in range(2):
            for j in range(2):
                self.assertTrue(math.isclose(
                    qd[i][j], block_x[i][j], rel_tol=1e-12, abs_tol=1e-15))
                self.assertTrue(math.isclose(
                    qd[2 + i][2 + j], block_y[i][j],
                    rel_tol=1e-12, abs_tol=1e-15))
        for i in range(4):
            for j in range(4):
                if (i < 2) != (j < 2):
                    self.assertLess(abs(qd[i][j]), 1e-12)

    def test_ins_velocity_matches_scalar(self):
        """The INS velocity random walk per axis q_accel*dt = 0.0001 at
        dt = 0.01 s, q_accel = 0.01 equals the scalar van Loan F = 0
        result to 1e-15 (workflow step 5, the INS velocity random walk
        variance an error-state filter enters per velocity axis)."""
        self.assertTrue(math.isclose(
            ins_velocity_random_walk_covariance(0.01, 0.01), 0.0001,
            rel_tol=1e-15, abs_tol=1e-15))
        _, qd = van_loan_discretize([[0.0]], [[1.0]], [[0.01]], 0.01)
        self.assertTrue(math.isclose(qd[0][0], 0.0001, rel_tol=1e-15))

    def test_determinism_bitwise(self):
        """Two identical van Loan discretizations of the 4-state planar
        model are bitwise identical (deterministic, no RNG)."""
        f = [[0.0, 1.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.0],
             [0.0, 0.0, 0.0, 1.0], [0.0, 0.0, 0.0, 0.0]]
        g = [[0.0, 0.0], [1.0, 0.0], [0.0, 0.0], [0.0, 1.0]]
        qc = [[0.25, 0.0], [0.0, 0.5]]
        _, qd1 = van_loan_discretize(f, g, qc, 0.1)
        _, qd2 = van_loan_discretize(f, g, qc, 0.1)
        self.assertEqual(qd1, qd2)

    def test_dt_zero_and_negative_raise(self):
        """dt at 0 and at -0.1 raise ValueError on the van Loan
        discretization."""
        with self.assertRaises(ValueError):
            van_loan_discretize(DWA_F, DWA_G, DWA_QC, 0.0)
        with self.assertRaises(ValueError):
            van_loan_discretize(DWA_F, DWA_G, DWA_QC, -0.1)

    def test_bad_shapes_raise(self):
        """A non-square F, G with the wrong row count for F, and a
        negative definite Qc all raise ValueError on the van Loan
        discretization (workflow step 1, the continuous model validation
        that guards the filter propagation step)."""
        with self.assertRaises(ValueError):
            van_loan_discretize([[1.0, 0.0]], DWA_G, DWA_QC, 0.1)
        with self.assertRaises(ValueError):
            van_loan_discretize(DWA_F,
                                [[1.0, 0.0], [0.0, 1.0], [0.0, 0.0]],
                                [[0.01, 0.0], [0.0, 0.01]], 0.1)
        with self.assertRaises(ValueError):
            van_loan_discretize([[0.0]], [[1.0]], [[-1.0]], 0.1)


class TestClosedForms(unittest.TestCase):
    """Closed-form models the filter leaves feed on (workflow step 5)."""

    def test_dwa_dt1_values(self):
        """discrete_white_noise_acceleration(1.0, 0.25) gives the entries
        0.08333333333333333, 0.125 and 0.25 within 1e-12."""
        qd = discrete_white_noise_acceleration(1.0, 0.25)
        self.assertTrue(math.isclose(qd[0][0], 0.25 / 3.0, rel_tol=1e-12))
        self.assertTrue(math.isclose(qd[0][1], 0.125, rel_tol=1e-12))
        self.assertTrue(math.isclose(qd[1][1], 0.25, rel_tol=1e-12))
        self.assertEqual(qd[0][1], qd[1][0])

    def test_dwa_dt01_values(self):
        """At dt = 0.1 s the DWA position variance entry is q*dt^3/3 =
        8.333e-05 and the velocity variance q*dt = 0.025."""
        qd = discrete_white_noise_acceleration(0.1, 0.25)
        self.assertTrue(math.isclose(qd[0][0], 8.333333333333334e-05,
                                     rel_tol=1e-12))
        self.assertTrue(math.isclose(qd[1][1], 0.025, rel_tol=1e-12))

    def test_random_walk_value(self):
        """random_walk_covariance(0.1, 0.01) equals 0.001 exactly."""
        self.assertEqual(random_walk_covariance(0.1, 0.01), 0.001)

    def test_ins_velocity_value(self):
        """ins_velocity_random_walk_covariance(0.01, 0.01) equals 0.0001
        exactly, the per-axis velocity-error variance at 100 Hz."""
        self.assertEqual(ins_velocity_random_walk_covariance(0.01, 0.01),
                         0.0001)

    def test_dwa_dt_zero_and_negative_q_raise(self):
        """dt at 0 and q at -0.25 or -1.0 raise ValueError on the DWA
        closed form."""
        with self.assertRaises(ValueError):
            discrete_white_noise_acceleration(0.0, 0.25)
        with self.assertRaises(ValueError):
            discrete_white_noise_acceleration(0.1, -0.25)
        with self.assertRaises(ValueError):
            discrete_white_noise_acceleration(0.1, -1.0)

    def test_random_walk_dt_zero_and_negative_q_raise(self):
        """dt at 0 and q at -0.25 or -1.0 raise ValueError on the random
        walk covariance."""
        with self.assertRaises(ValueError):
            random_walk_covariance(0.0, 0.01)
        with self.assertRaises(ValueError):
            random_walk_covariance(0.1, -0.25)
        with self.assertRaises(ValueError):
            random_walk_covariance(0.1, -1.0)

    def test_ins_velocity_dt_zero_and_negative_q_raise(self):
        """dt at 0 and a negative q_accel raise ValueError on the INS
        velocity random walk covariance."""
        with self.assertRaises(ValueError):
            ins_velocity_random_walk_covariance(0.0, 0.01)
        with self.assertRaises(ValueError):
            ins_velocity_random_walk_covariance(0.01, -1.0)


if __name__ == "__main__":
    unittest.main()
