"""Offline contract test for the Davenport q-method attitude determination.

Run: python3 test_attitude_determination_quest.py  (stdlib unittest, <20 s)
"""

import math
import unittest

from attitude_determination_quest_logic import (
    JACOBI_MAX_SWEEPS,
    MIN_OBSERVATIONS,
    attitude_matrix_from_quaternion,
    attitude_profile,
    conjugate,
    davenport_k_matrix,
    jacobi_eigen_sym4,
    quat_product,
    quest_solution,
    rotate_vector,
    wahba_cost,
)

RECOVER_TOL = 1e-9
RTOL = 1e-9

Q_TRUE_90Z = (math.cos(math.pi / 4), 0.0, 0.0, math.sin(math.pi / 4))
REFS_3 = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)]
BODIES_3 = [(0.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)]
ONES_3 = [1.0, 1.0, 1.0]

AXIS_111 = (1.0 / math.sqrt(3.0), 1.0 / math.sqrt(3.0), 1.0 / math.sqrt(3.0))
Q_TRUE_45_111 = (
    math.cos(math.pi / 8),
    AXIS_111[0] * math.sin(math.pi / 8),
    AXIS_111[1] * math.sin(math.pi / 8),
    AXIS_111[2] * math.sin(math.pi / 8),
)
RAW_REFS_6 = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
              (1.0, 1.0, 0.0), (1.0, -1.0, 0.0), (0.0, 1.0, 1.0)]


def _norm3(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _unit(v):
    n = _norm3(v)
    return (v[0] / n, v[1] / n, v[2] / n)


def _quat_err(q, q_true):
    """Sign-aware quaternion comparison error: min over q and -q."""
    return min(max(abs(a - b) for a, b in zip(q, q_true)),
               max(abs(a + b) for a, b in zip(q, q_true)))


REFS_6 = [_unit(v) for v in RAW_REFS_6]
BODIES_6 = [rotate_vector(Q_TRUE_45_111, r) for r in REFS_6]


class TestQuaternionOperations(unittest.TestCase):
    def test_quat_product_identity(self):
        ident = (1.0, 0.0, 0.0, 0.0)
        q = (0.3, -0.4, 0.5, 0.6)
        for p in (quat_product(q, ident), quat_product(ident, q)):
            self.assertAlmostEqual(p[0], q[0], places=14)
            self.assertAlmostEqual(p[1], q[1], places=14)
            self.assertAlmostEqual(p[2], q[2], places=14)
            self.assertAlmostEqual(p[3], q[3], places=14)

    def test_quat_product_closed_form(self):
        # Deterministic hand value of (1,2,3,4) * (5,6,7,8) under Hamilton.
        p = quat_product((1.0, 2.0, 3.0, 4.0), (5.0, 6.0, 7.0, 8.0))
        expected = (-60.0, 12.0, 30.0, 24.0)
        for got, want in zip(p, expected):
            self.assertAlmostEqual(got, want, places=12)

    def test_quat_product_double_rotation_about_z(self):
        # Two 90 deg z rotations compose to a 180 deg rotation: (0,0,0,1).
        p = quat_product(Q_TRUE_90Z, Q_TRUE_90Z)
        self.assertAlmostEqual(p[0], 0.0, places=14)
        self.assertAlmostEqual(p[3], 1.0, places=14)

    def test_conjugate_product_is_norm_squared(self):
        q = (0.5, 0.5, -0.5, 0.5)
        p = quat_product(q, conjugate(q))
        self.assertAlmostEqual(p[1], 0.0, places=14)
        self.assertAlmostEqual(p[2], 0.0, places=14)
        self.assertAlmostEqual(p[3], 0.0, places=14)
        self.assertAlmostEqual(p[0], 1.0, places=14)

    def test_rotate_vector_90_deg_about_z(self):
        got = [rotate_vector(Q_TRUE_90Z, r) for r in REFS_3]
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(got[i][j], BODIES_3[i][j], places=12)

class TestAttitudeMatrixFromQuaternion(unittest.TestCase):
    def test_90z_rows_are_observed_axes(self):
        rows = attitude_matrix_from_quaternion(Q_TRUE_90Z)
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(rows[i][j], BODIES_3[i][j], places=12)


class TestInputValidation(unittest.TestCase):
    def test_fewer_than_two_observations(self):
        with self.assertRaises(ValueError):
            attitude_profile([(1.0, 0.0, 0.0)], [(1.0, 0.0, 0.0)])
        self.assertGreaterEqual(MIN_OBSERVATIONS, 2)

    def test_observation_reference_count_mismatch(self):
        with self.assertRaises(ValueError):
            attitude_profile(BODIES_3, REFS_3[:2])

    def test_non_unit_observation_rejected(self):
        with self.assertRaises(ValueError):
            attitude_profile([(1.1, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)],
                             REFS_3)

    def test_non_unit_reference_rejected(self):
        with self.assertRaises(ValueError):
            attitude_profile(BODIES_3,
                             [(1.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 1.0)])

    def test_non_positive_weight_rejected(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                attitude_profile(BODIES_3, REFS_3, [1.0, bad, 1.0])

    def test_weights_length_mismatch(self):
        with self.assertRaises(ValueError):
            attitude_profile(BODIES_3, REFS_3, [1.0, 1.0])

    def test_quest_solution_propagates_valueerror(self):
        with self.assertRaises(ValueError):
            quest_solution([(1.0, 0.0, 0.0)], [(1.0, 0.0, 0.0)])


class TestProfileAndKMatrix(unittest.TestCase):
    def test_attitude_profile_worked_example(self):
        b = attitude_profile(BODIES_3, REFS_3, ONES_3)
        expected = [[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(b[i][j], expected[i][j], places=12)

    def test_davenport_k_matrix_worked_example_values(self):
        b = attitude_profile(BODIES_3, REFS_3, ONES_3)
        k, sigma, z = davenport_k_matrix(b)
        self.assertAlmostEqual(sigma, 1.0, places=12)
        self.assertAlmostEqual(z[0], 0.0, places=12)
        self.assertAlmostEqual(z[1], 0.0, places=12)
        self.assertAlmostEqual(z[2], 2.0, places=12)
        self.assertAlmostEqual(k[0][0], -1.0, places=12)
        self.assertAlmostEqual(k[3][3], 1.0, places=12)
        self.assertAlmostEqual(k[2][3], 2.0, places=12)
        self.assertAlmostEqual(k[3][2], 2.0, places=12)

    def test_k_matrix_is_symmetric(self):
        b = attitude_profile(BODIES_3, REFS_3, ONES_3)
        k, _s, _z = davenport_k_matrix(b)
        for i in range(4):
            for j in range(4):
                self.assertAlmostEqual(k[i][j], k[j][i], places=12)


class TestJacobiEigenSolver(unittest.TestCase):
    def test_jacobi_diagonal_matrix(self):
        k = [[1.0, 0.0, 0.0, 0.0], [0.0, 2.0, 0.0, 0.0],
             [0.0, 0.0, 3.0, 0.0], [0.0, 0.0, 0.0, 4.0]]
        eigs, v = jacobi_eigen_sym4(k)
        for i in range(4):
            self.assertAlmostEqual(eigs[i], float(i + 1), places=12)
            self.assertAlmostEqual(v[i][i], 1.0, places=12)

    def test_jacobi_reconstruction_identity(self):
        b = attitude_profile(BODIES_3, REFS_3, ONES_3)
        k, _s, _z = davenport_k_matrix(b)
        eigs, v = jacobi_eigen_sym4(k)
        for i in range(4):
            for j in range(4):
                back = sum(v[i][m] * eigs[m] * v[j][m] for m in range(4))
                self.assertAlmostEqual(back, k[i][j], places=8)

    def test_jacobi_worked_eigenvalues(self):
        b = attitude_profile(BODIES_3, REFS_3, ONES_3)
        k, _s, _z = davenport_k_matrix(b)
        eigs, _v = jacobi_eigen_sym4(k)
        self.assertAlmostEqual(max(eigs), 3.0, places=9)
        self.assertLessEqual(JACOBI_MAX_SWEEPS, 60)


class TestWorkedExample(unittest.TestCase):
    def setUp(self):
        self.sol = quest_solution(BODIES_3, REFS_3, ONES_3)

    def test_recovers_q_true_90z(self):
        self.assertLess(_quat_err(self.sol["q_optimal"], Q_TRUE_90Z),
                        RECOVER_TOL)

    def test_lambda_max_about_three(self):
        self.assertAlmostEqual(self.sol["lambda_max"], 3.0, places=9)

    def test_identity_ok_true(self):
        self.assertTrue(self.sol["identity_ok"])

    def test_wahba_cost_near_zero(self):
        self.assertLess(self.sol["wahba_cost"], 1e-9)

    def test_attitude_matrix_rows_are_observed_axes(self):
        rows = self.sol["attitude_matrix"]
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(rows[i][j], BODIES_3[i][j], places=9)

    def test_dict_keys_exactly_documented(self):
        expected = {"q_optimal", "lambda_max", "attitude_matrix", "residuals",
                    "wahba_cost", "identity_ok"}
        self.assertEqual(set(self.sol.keys()), expected)

    def test_perturbed_quaternion_cost_strictly_larger(self):
        pert = quat_product(Q_TRUE_90Z, (math.cos(0.05), 0.0, 0.0,
                                         math.sin(0.05)))
        cost_pert = wahba_cost(pert, BODIES_3, REFS_3, ONES_3)
        self.assertGreater(cost_pert, self.sol["wahba_cost"] + 1e-9)

    def test_consistency_active_rotation_maps_refs_to_bodies(self):
        q = self.sol["q_optimal"]
        for i in range(3):
            out = rotate_vector(q, REFS_3[i])
            for j in range(3):
                self.assertAlmostEqual(out[j], BODIES_3[i][j], places=9)


class TestSecondWorkedCase(unittest.TestCase):
    def setUp(self):
        self.sol = quest_solution(BODIES_6, REFS_6)

    def test_recovers_45deg_about_111(self):
        # Non-symmetric case: catches z-vector sign slips.
        self.assertLess(_quat_err(self.sol["q_optimal"], Q_TRUE_45_111),
                        RECOVER_TOL)

    def test_second_case_identity_ok(self):
        self.assertTrue(self.sol["identity_ok"])

    def test_second_case_consistency_all_six(self):
        q = self.sol["q_optimal"]
        for i in range(6):
            out = rotate_vector(q, REFS_6[i])
            for j in range(3):
                self.assertAlmostEqual(out[j], BODIES_6[i][j], places=9)

    def test_second_case_axis_and_angle(self):
        q = self.sol["q_optimal"]
        self.assertAlmostEqual(abs(q[0]), math.cos(math.pi / 8), places=9)
        vec = (q[1], q[2], q[3])
        n = _norm3(vec)
        self.assertAlmostEqual(n, math.sin(math.pi / 8), places=9)
        dot = (vec[0] * AXIS_111[0] + vec[1] * AXIS_111[1]
               + vec[2] * AXIS_111[2]) / n
        self.assertAlmostEqual(abs(dot), 1.0, places=9)


class TestRobustness(unittest.TestCase):
    def test_determinism_two_runs_identical(self):
        s1 = quest_solution(BODIES_3, REFS_3, ONES_3)
        s2 = quest_solution(BODIES_3, REFS_3, ONES_3)
        for key in ("q_optimal", "lambda_max", "wahba_cost"):
            self.assertEqual(s1[key], s2[key])
        self.assertEqual(s1["residuals"], s2["residuals"])
        e1, v1 = jacobi_eigen_sym4(
            davenport_k_matrix(attitude_profile(BODIES_3, REFS_3, ONES_3))[0])
        e2, v2 = jacobi_eigen_sym4(
            davenport_k_matrix(attitude_profile(BODIES_3, REFS_3, ONES_3))[0])
        self.assertEqual(e1, e2)
        self.assertEqual(v1, v2)

    def test_weighted_recovery_still_exact(self):
        weights = [3.0, 1.0, 0.5]
        sol = quest_solution(BODIES_3, REFS_3, weights)
        self.assertLess(_quat_err(sol["q_optimal"], Q_TRUE_90Z), RECOVER_TOL)

    def test_quaternion_sign_invariance(self):
        neg = tuple(-c for c in Q_TRUE_90Z)
        a = attitude_matrix_from_quaternion(Q_TRUE_90Z)
        b = attitude_matrix_from_quaternion(neg)
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(a[i][j], b[i][j], places=12)


if __name__ == "__main__":
    unittest.main()
