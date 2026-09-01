#!/usr/bin/env python3
"""Gate 3 contract test: dense matrix operations logic.

Exercises scripts/matrix_operations_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - Gaussian
elimination with partial pivoting solves the dense square system
A x = b, the determinant comes from the pivot product with the row
swap sign, the inverse comes from Gauss-Jordan on [A | I], and
singularity detection flags any pivot at or below the tolerance.
Analytic anchors: A = [[2, 1, -1], [-3, -1, 2], [-2, 1, 2]],
b = [8, -11, -3] gives x = [2, 3, -1] with zero residual;
A = [[1, 2, 3], [0, 1, 4], [5, 6, 0]] has det 1.0;
A = [[4, 7], [2, 6]] has det 10.0 and inverse
[[0.6, -0.7], [-0.2, 0.4]]. [[1, 2], [2, 4]] is singular (det 0,
no inverse, no unique solution); [[1, 2], [3, 4]] has det -2.0.
Partial pivoting rescues [[0, 1], [1, 0]] (x = [2, 1], det -1.0).
Trend properties: swapping two rows flips the determinant sign,
doubling a row doubles the determinant, and inverting the inverse
returns the original matrix. ValueError on singular systems in
solve/inverse, non-square or ragged matrices, non-numeric or bool
entries, and wrong-length vectors.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import matrix_operations_logic as mo  # noqa: E402

A3 = [[2, 1, -1], [-3, -1, 2], [-2, 1, 2]]
B3 = [8, -11, -3]
A3_DET = [[1, 2, 3], [0, 1, 4], [5, 6, 0]]
A2 = [[4, 7], [2, 6]]


class SolveTest(unittest.TestCase):
    def test_anchor_3x3(self):
        # A x = b with x = [2, 3, -1]: every row checks exactly.
        x = mo.solve(A3, B3)
        self.assertAlmostEqual(x[0], 2.0, places=10)
        self.assertAlmostEqual(x[1], 3.0, places=10)
        self.assertAlmostEqual(x[2], -1.0, places=10)

    def test_anchor_2x2(self):
        # [[4, 7], [2, 6]] * [x, y] = [1, 3] gives x = -1.5, y = 1.0.
        x = mo.solve(A2, [1, 3])
        self.assertAlmostEqual(x[0], -1.5, places=10)
        self.assertAlmostEqual(x[1], 1.0, places=10)

    def test_identity_system(self):
        x = mo.solve([[1, 0], [0, 1]], [3, 4])
        self.assertEqual(x, [3.0, 4.0])

    def test_partial_pivoting_rescues_zero_diagonal(self):
        # The zero entry [[0, 1], [1, 0]] would divide by zero without
        # the pivot search; with partial pivoting x = [2, 1].
        x = mo.solve([[0, 1], [1, 0]], [1, 2])
        self.assertAlmostEqual(x[0], 2.0, places=10)
        self.assertAlmostEqual(x[1], 1.0, places=10)

    def test_singular_raises_value_error(self):
        # Proportional rows: no unique solution, and solve must refuse.
        with self.assertRaises(ValueError):
            mo.solve([[1, 2], [2, 4]], [3, 6])

    def test_solution_has_zero_residual(self):
        x = mo.solve(A3, B3)
        self.assertAlmostEqual(mo.residual_norm(A3, B3, x), 0.0, places=10)


class DeterminantTest(unittest.TestCase):
    def test_anchor_3x3(self):
        # One row swap during elimination flips the pivot product
        # 5 * 1 * -0.2 back to det = 1.0.
        self.assertAlmostEqual(mo.determinant(A3_DET), 1.0, places=10)

    def test_anchor_2x2(self):
        # ad - bc = 4*6 - 7*2 = 10.
        self.assertAlmostEqual(mo.determinant(A2), 10.0, places=10)

    def test_singular_matrix_det_zero(self):
        # [[1, 2], [2, 4]] has proportional rows: det = 0, no raise.
        self.assertEqual(mo.determinant([[1, 2], [2, 4]]), 0.0)

    def test_row_swap_flips_sign(self):
        # Swapping rows 0 and 2 negates the determinant (1.0 to -1.0).
        self.assertAlmostEqual(
            mo.determinant([[5, 6, 0], [0, 1, 4], [1, 2, 3]]), -1.0, places=10
        )

    def test_row_scaling_scales_det(self):
        # Doubling one row doubles the determinant (1.0 to 2.0).
        self.assertAlmostEqual(
            mo.determinant([[2, 4, 6], [0, 1, 4], [5, 6, 0]]), 2.0, places=10
        )

    def test_one_by_one(self):
        self.assertAlmostEqual(mo.determinant([[5]]), 5.0, places=10)


class InverseTest(unittest.TestCase):
    def test_anchor_2x2(self):
        # (1/10) * [[6, -7], [-2, 4]] = [[0.6, -0.7], [-0.2, 0.4]].
        inv = mo.inverse(A2)
        self.assertAlmostEqual(inv[0][0], 0.6, places=10)
        self.assertAlmostEqual(inv[0][1], -0.7, places=10)
        self.assertAlmostEqual(inv[1][0], -0.2, places=10)
        self.assertAlmostEqual(inv[1][1], 0.4, places=10)

    def test_inverse_times_matrix_is_identity(self):
        inv = mo.inverse(A2)
        prod = [
            [sum(A2[i][k] * inv[k][j] for k in range(2)) for j in range(2)]
            for i in range(2)
        ]
        self.assertAlmostEqual(prod[0][0], 1.0, places=10)
        self.assertAlmostEqual(prod[0][1], 0.0, places=10)
        self.assertAlmostEqual(prod[1][0], 0.0, places=10)
        self.assertAlmostEqual(prod[1][1], 1.0, places=10)

    def test_inverse_of_inverse_returns_matrix(self):
        back = mo.inverse(mo.inverse(A2))
        for i in range(2):
            for j in range(2):
                self.assertAlmostEqual(back[i][j], A2[i][j], places=10)

    def test_singular_raises_value_error(self):
        with self.assertRaises(ValueError):
            mo.inverse([[1, 2], [2, 4]])

    def test_one_by_one(self):
        self.assertAlmostEqual(mo.inverse([[5]])[0][0], 0.2, places=10)


class SingularTest(unittest.TestCase):
    def test_proportional_rows_singular(self):
        self.assertTrue(mo.is_singular([[1, 2], [2, 4]]))

    def test_nonsingular_matrix(self):
        # det = -2.0; the system has a unique solution.
        self.assertFalse(mo.is_singular([[1, 2], [3, 4]]))

    def test_three_by_three_singular(self):
        # Row 1 is twice row 0: rank deficient.
        self.assertTrue(mo.is_singular([[1, 2, 3], [2, 4, 6], [0, 0, 1]]))

    def test_custom_tolerance(self):
        # [[1e-10, 0], [0, 1]] has a tiny but nonzero pivot: above the
        # default scale-aware tolerance (1e-12), below an explicit
        # 1e-8 tolerance, so the verdict flips with the tolerance.
        self.assertFalse(mo.is_singular([[1e-10, 0], [0, 1]]))
        self.assertTrue(mo.is_singular([[1e-10, 0], [0, 1]], tol=1e-8))

    def test_zero_matrix_singular(self):
        self.assertTrue(mo.is_singular([[0, 0], [0, 0]]))


class ResidualTest(unittest.TestCase):
    def test_exact_solve_zero_residual(self):
        x = mo.solve(A3, B3)
        self.assertAlmostEqual(mo.residual_norm(A3, B3, x), 0.0, places=10)

    def test_wrong_vector_positive_residual(self):
        # x = [0, 0, 0] against b = [8, -11, -3]: the largest row
        # residual is |-11| = 11.0.
        self.assertAlmostEqual(mo.residual_norm(A3, B3, [0, 0, 0]), 11.0, places=10)


class ValidationTest(unittest.TestCase):
    def test_non_square_raises(self):
        with self.assertRaises(ValueError):
            mo.solve([[1, 2, 3], [4, 5, 6]], [1, 2])

    def test_ragged_rows_raise(self):
        with self.assertRaises(ValueError):
            mo.determinant([[1, 2], [3]])

    def test_non_numeric_entries_raise(self):
        with self.assertRaises(ValueError):
            mo.solve([[1, "a"], [3, 4]], [1, 2])

    def test_bool_entries_raise(self):
        # bool is an int subclass but is not a valid matrix entry.
        with self.assertRaises(ValueError):
            mo.determinant([[True, 2], [3, 4]])

    def test_wrong_length_rhs_raises(self):
        with self.assertRaises(ValueError):
            mo.solve([[1, 2], [3, 4]], [1, 2, 3])

    def test_empty_matrix_raises(self):
        with self.assertRaises(ValueError):
            mo.determinant([])

    def test_invalid_tolerance_raises(self):
        with self.assertRaises(ValueError):
            mo.is_singular([[1, 2], [3, 4]], tol=0)

    def test_wrong_length_residual_vector_raises(self):
        with self.assertRaises(ValueError):
            mo.residual_norm(A3, B3, [1, 2])


if __name__ == "__main__":
    unittest.main(verbosity=2)
