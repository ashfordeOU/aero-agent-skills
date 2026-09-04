"""Contract test for cross-cutting/numerics/singular-value-decomposition.

Offline, deterministic, stdlib unittest. Run from the repo root:

    python3 skills/cross-cutting/numerics/singular-value-decomposition/scripts/test_singular_value_decomposition.py

Covers the one-sided Jacobi SVD economy form on tall, square and wide
matrices, the worked-example anchors A1, A2, A3, condition number,
numerical rank, Moore-Penrose identities and ValueError rejection.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import singular_value_decomposition_logic as svd

A1 = [[3, 1], [1, 3]]  # symmetric 2x2, s = {2, 4}, cond 2.0
A2 = [[1, 1], [0, 0], [1, 0]]  # 3x2, s = [phi, 1/phi]
A3 = [[1, 2], [2, 4], [3, 6]]  # rank-1 3x2, s = [sqrt(70), 0]
A2T = [[1, 0, 1], [1, 0, 0]]  # 2x3 wide transpose of A2


def matmul(X, Y):
    """Matrix product of two list-of-lists matrices."""
    return [
        [sum(X[i][k] * Y[k][j] for k in range(len(Y))) for j in range(len(Y[0]))]
        for i in range(len(X))
    ]


def frobenius(M):
    """Frobenius norm of a list-of-lists matrix."""
    return math.sqrt(sum(x * x for row in M for x in row))


def matrix_difference(X, Y):
    """Elementwise difference X - Y as a list-of-lists matrix."""
    return [[X[i][j] - Y[i][j] for j in range(len(Y[0]))] for i in range(len(X))]


class TestSVDShapes(unittest.TestCase):
    """Economy form shapes and convenience dict keys."""

    def test_economy_shapes_all_forms(self):
        square = svd.svd_jacobi(A1)
        self.assertEqual((len(square["u"]), len(square["u"][0])), (2, 2))
        self.assertEqual(len(square["s"]), 2)
        self.assertEqual((len(square["vh"]), len(square["vh"][0])), (2, 2))
        tall = svd.svd_jacobi(A2)
        self.assertEqual((len(tall["u"]), len(tall["u"][0])), (3, 2))
        self.assertEqual(len(tall["s"]), 2)
        self.assertEqual((len(tall["vh"]), len(tall["vh"][0])), (2, 2))
        wide = svd.svd_jacobi(A2T)
        self.assertEqual((len(wide["u"]), len(wide["u"][0])), (2, 2))
        self.assertEqual(len(wide["s"]), 2)
        self.assertEqual((len(wide["vh"]), len(wide["vh"][0])), (2, 3))

    def test_svd_dict_keys_exact(self):
        res = svd.svd_jacobi(A1)
        self.assertEqual(
            set(res.keys()), {"u", "s", "vh", "reconstruction_residual"}
        )

    def test_svd_report_keys_and_consistency(self):
        report = svd.svd_report(A2)
        self.assertEqual(
            set(report.keys()),
            {
                "u",
                "s",
                "vh",
                "reconstruction_residual",
                "condition_number",
                "numerical_rank",
                "moore_penrose_inverse",
            },
        )
        direct = svd.svd_jacobi(A2)
        self.assertEqual(report["s"], direct["s"])
        self.assertEqual(report["u"], direct["u"])
        self.assertEqual(report["vh"], direct["vh"])
        self.assertEqual(report["condition_number"], svd.condition_number(direct["s"]))
        self.assertEqual(report["numerical_rank"], svd.numerical_rank(direct["s"]))
        self.assertEqual(
            report["moore_penrose_inverse"], svd.moore_penrose_inverse(A2)
        )

    def test_descending_order_and_nonnegative(self):
        res = svd.svd_jacobi([[2, 5, 1], [7, 3, 9], [4, 8, 6]])
        for first, second in zip(res["s"], res["s"][1:]):
            self.assertGreaterEqual(first, second)
        for sj in res["s"]:
            self.assertGreaterEqual(sj, 0.0)


class TestWorkedExampleA1(unittest.TestCase):
    """Symmetric 2x2 anchor: s = {2, 4}, cond 2.0, residual ~1.3e-15."""

    def test_singular_values_equal_abs_eigenvalues(self):
        res = svd.svd_jacobi(A1)
        self.assertAlmostEqual(res["s"][0], 4.0, delta=1e-9)
        self.assertAlmostEqual(res["s"][1], 2.0, delta=1e-9)
        # A1 is symmetric with eigenvalues 4 and 2, so |lambda| = s.
        self.assertAlmostEqual(res["s"][0], abs(4.0), delta=1e-9)
        self.assertAlmostEqual(res["s"][1], abs(2.0), delta=1e-9)

    def test_condition_number_two(self):
        res = svd.svd_jacobi(A1)
        self.assertAlmostEqual(svd.condition_number(res["s"]), 2.0, delta=1e-9)

    def test_reconstruction_residual(self):
        res = svd.svd_jacobi(A1)
        self.assertLess(res["reconstruction_residual"], 1e-12)
        # Independent rebuild A = U diag(s) Vh inside the test.
        diag = [[res["s"][0], 0.0], [0.0, res["s"][1]]]
        rebuilt = matmul(matmul(res["u"], diag), res["vh"])
        self.assertLess(frobenius(matrix_difference(rebuilt, A1)), 1e-12)

    def test_rank_two(self):
        res = svd.svd_jacobi(A1)
        self.assertEqual(svd.numerical_rank(res["s"]), 2)


class TestWorkedExampleA2(unittest.TestCase):
    """Rectangular 3x2 anchor: phi and 1/phi, cond phi^2, pinv identity."""

    def test_singular_values_phi(self):
        res = svd.svd_jacobi(A2)
        self.assertAlmostEqual(res["s"][0], 1.61803398875, delta=1e-9)
        self.assertAlmostEqual(res["s"][1], 0.61803398875, delta=1e-9)

    def test_condition_number(self):
        res = svd.svd_jacobi(A2)
        self.assertAlmostEqual(svd.condition_number(res["s"]), 2.618034, delta=1e-6)

    def test_reconstruction_and_transpose_agreement(self):
        res = svd.svd_jacobi(A2)
        self.assertLess(res["reconstruction_residual"], 1e-12)
        wide = svd.svd_jacobi(A2T)
        self.assertAlmostEqual(wide["s"][0], res["s"][0], delta=1e-12)
        self.assertAlmostEqual(wide["s"][1], res["s"][1], delta=1e-12)

    def test_pinv_identities_tall(self):
        pinv = svd.moore_penrose_inverse(A2)
        self.assertEqual((len(pinv), len(pinv[0])), (2, 3))
        err1 = frobenius(matrix_difference(matmul(matmul(A2, pinv), A2), A2))
        self.assertLess(err1, 1e-10)
        err2 = frobenius(matrix_difference(matmul(matmul(pinv, A2), pinv), pinv))
        self.assertLess(err2, 1e-10)


class TestWorkedExampleA3(unittest.TestCase):
    """Rank-1 anchor: s = [sqrt(70), 0], numerical rank 1."""

    def test_singular_values_sqrt_70(self):
        res = svd.svd_jacobi(A3)
        self.assertAlmostEqual(res["s"][0], 8.366600265341, delta=1e-9)
        self.assertAlmostEqual(res["s"][0], math.sqrt(70.0), delta=1e-9)
        self.assertAlmostEqual(res["s"][1], 0.0, delta=1e-9)

    def test_numerical_rank_one(self):
        res = svd.svd_jacobi(A3)
        self.assertEqual(svd.numerical_rank(res["s"]), 1)

    def test_condition_number_infinite(self):
        res = svd.svd_jacobi(A3)
        self.assertEqual(svd.condition_number(res["s"]), float("inf"))

    def test_reconstruction_and_pinv_identity(self):
        res = svd.svd_jacobi(A3)
        self.assertLess(res["reconstruction_residual"], 1e-12)
        pinv = svd.moore_penrose_inverse(A3)
        err = frobenius(matrix_difference(matmul(matmul(A3, pinv), A3), A3))
        self.assertLess(err, 1e-10)


class TestWidePinvAndRank(unittest.TestCase):
    """Wide 2x3 pinv case and numerical rank behavior."""

    def test_wide_pinv_shape_and_values(self):
        pinv = svd.moore_penrose_inverse(A2T)
        self.assertEqual((len(pinv), len(pinv[0])), (3, 2))
        res = svd.svd_jacobi(A2T)
        self.assertGreaterEqual(res["s"][0], res["s"][1])
        self.assertAlmostEqual(res["s"][0] * res["s"][0], 2.61803398875, delta=1e-9)

    def test_wide_pinv_identities(self):
        pinv = svd.moore_penrose_inverse(A2T)
        err1 = frobenius(matrix_difference(matmul(matmul(A2T, pinv), A2T), A2T))
        self.assertLess(err1, 1e-10)
        err2 = frobenius(matrix_difference(matmul(matmul(pinv, A2T), pinv), pinv))
        self.assertLess(err2, 1e-10)

    def test_identity_and_zero_matrix_rank(self):
        res_id = svd.svd_jacobi([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        self.assertEqual(svd.numerical_rank(res_id["s"]), 3)
        res_zero = svd.svd_jacobi([[0, 0], [0, 0]])
        self.assertEqual(svd.numerical_rank(res_zero["s"]), 0)
        self.assertEqual(svd.condition_number(res_zero["s"]), float("inf"))

    def test_rank_threshold_counting(self):
        # s_max 10, rel_tol 1e-12 -> threshold 1e-11: only 10 and 1e-9 count.
        self.assertEqual(svd.numerical_rank([10.0, 1e-9, 1e-15]), 2)
        self.assertEqual(svd.numerical_rank([1.0, 0.5], rel_tol=0.6), 1)
        self.assertEqual(svd.numerical_rank([1.0, 0.5], rel_tol=0.4), 2)


class TestDegenerateSizes(unittest.TestCase):
    """1x1 and fixed rectangular reconstruction round trips."""

    def test_1x1_nonzero_and_zero(self):
        res = svd.svd_jacobi([[5.0]])
        self.assertAlmostEqual(res["s"][0], 5.0, delta=1e-12)
        self.assertLess(res["reconstruction_residual"], 1e-12)
        res_zero = svd.svd_jacobi([[0.0]])
        self.assertAlmostEqual(res_zero["s"][0], 0.0, delta=1e-12)
        self.assertEqual(svd.numerical_rank(res_zero["s"]), 0)

    def test_fixed_3x4_wide_reconstruction(self):
        fixed = [[1, 0, 2, -1], [0, 3, 1, 2], [2, 1, 0, 4]]
        res = svd.svd_jacobi(fixed)
        self.assertLess(res["reconstruction_residual"], 1e-12)
        self.assertEqual(len(res["s"]), 3)
        self.assertEqual((len(res["vh"]), len(res["vh"][0])), (3, 4))


class TestDeterminismAndValidation(unittest.TestCase):
    """Run-to-run determinism and ValueError rejection of bad input."""

    def test_deterministic_repeat(self):
        fixed = [[2, 5, 1], [7, 3, 9], [4, 8, 6], [1, 2, 3]]
        first = svd.svd_jacobi(fixed)
        second = svd.svd_jacobi(fixed)
        self.assertEqual(first["s"], second["s"])
        self.assertEqual(first["u"], second["u"])
        self.assertEqual(first["vh"], second["vh"])

    def test_valueerror_empty_matrix(self):
        with self.assertRaises(ValueError):
            svd.svd_jacobi([])
        with self.assertRaises(ValueError):
            svd.svd_jacobi([[]])
        with self.assertRaises(ValueError):
            svd.moore_penrose_inverse([])

    def test_valueerror_ragged_rows(self):
        with self.assertRaises(ValueError):
            svd.svd_jacobi([[1, 2], [3]])
        with self.assertRaises(ValueError):
            svd.moore_penrose_inverse([[1, 2], [3, 4, 5]])

    def test_valueerror_non_numeric_entries(self):
        with self.assertRaises(ValueError):
            svd.svd_jacobi([[1, "a"], [2, 3]])
        with self.assertRaises(ValueError):
            svd.svd_jacobi([[1, 2], [None, 3]])
        with self.assertRaises(ValueError):
            svd.svd_jacobi([[1, 2], 5])

    def test_valueerror_empty_s(self):
        with self.assertRaises(ValueError):
            svd.condition_number([])
        with self.assertRaises(ValueError):
            svd.numerical_rank([])

    def test_valueerror_negative_s(self):
        with self.assertRaises(ValueError):
            svd.condition_number([1.0, -2.0])

    def test_condition_number_basic(self):
        self.assertAlmostEqual(svd.condition_number([8.0, 2.0]), 4.0, delta=1e-12)
        self.assertEqual(svd.condition_number([0.0, 5.0]), float("inf"))


if __name__ == "__main__":
    unittest.main()
