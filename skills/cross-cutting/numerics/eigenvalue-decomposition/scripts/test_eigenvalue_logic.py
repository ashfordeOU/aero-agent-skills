#!/usr/bin/env python3
"""Gate 3 contract test: eigenvalue decomposition logic.

Exercises scripts/eigenvalue_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - power iteration returns
the dominant eigenvalue-eigenvector pair of a general square matrix
with unit 2-norm normalization and a Rayleigh quotient convergence
check, deflation exposes the next dominant eigenvalue, and the Jacobi
eigenvalue algorithm returns the full spectrum of a real symmetric
matrix with a sweep convergence tolerance on the off-diagonal sum of
squares. Every returned pair must satisfy the residual check
||A v - lambda v||_inf at machine-epsilon scale.

Analytic anchors:
- A = [[2, 1], [1, 2]] has eigenvalues 3.0 and 1.0 with unit
  eigenvectors [0.707, 0.707] and [0.707, -0.707] (residual 0).
- A = [[2, 0], [0, 1]] has dominant eigenvalue 2.0 with eigenvector
  [1, 0]; after deflation the second eigenvalue is 1.0.
- A = [[4, 1, 1], [1, 4, 1], [1, 1, 4]] has eigenvalues 6.0, 3.0, 3.0.
Trend properties: Jacobi eigenvectors are orthonormal, eigenvalues
sort descending, and residual_norm is 0.0 for an exact pair.
ValueError on non-square, ragged, non-numeric, or bool input, and on
non-symmetric input to the Jacobi routine.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import eigenvalue_logic as ev  # noqa: E402

A_SYM2 = [[2, 1], [1, 2]]
A_DIAG2 = [[2, 0], [0, 1]]
A_SYM3 = [[4, 1, 1], [1, 4, 1], [1, 1, 4]]


def dot(u, v):
    return sum(a * b for a, b in zip(u, v))


class JacobiTest(unittest.TestCase):
    def test_2x2_anchor_eigenvalues(self):
        # [[2, 1], [1, 2]] has eigenvalues 3.0 and 1.0, descending.
        vals, vecs = ev.jacobi_eigen(A_SYM2)
        self.assertAlmostEqual(vals[0], 3.0, places=8)
        self.assertAlmostEqual(vals[1], 1.0, places=8)

    def test_2x2_anchor_eigenvectors_unit_norm(self):
        vals, vecs = ev.jacobi_eigen(A_SYM2)
        for v in vecs:
            self.assertAlmostEqual(ev._norm2(v), 1.0, places=8)

    def test_2x2_anchor_eigenvectors_satisfy_residual(self):
        vals, vecs = ev.jacobi_eigen(A_SYM2)
        for lam, v in zip(vals, vecs):
            self.assertLess(ev.residual_norm(A_SYM2, v, lam), 1e-8)

    def test_2x2_anchor_eigenvectors_are_orthonormal(self):
        vals, vecs = ev.jacobi_eigen(A_SYM2)
        self.assertAlmostEqual(abs(dot(vecs[0], vecs[1])), 0.0, places=8)

    def test_3x3_anchor(self):
        # [[4, 1, 1], [1, 4, 1], [1, 1, 4]]: 6.0 for the all-ones
        # vector, 3.0 with multiplicity two.
        vals, vecs = ev.jacobi_eigen(A_SYM3)
        self.assertAlmostEqual(vals[0], 6.0, places=8)
        self.assertAlmostEqual(vals[1], 3.0, places=8)
        self.assertAlmostEqual(vals[2], 3.0, places=8)
        for lam, v in zip(vals, vecs):
            self.assertLess(ev.residual_norm(A_SYM3, v, lam), 1e-8)

    def test_diagonal_matrix_spectrum(self):
        vals, vecs = ev.jacobi_eigen([[1, 0, 0], [0, 2, 0], [0, 0, 3]])
        self.assertAlmostEqual(vals[0], 3.0, places=8)
        self.assertAlmostEqual(vals[1], 2.0, places=8)
        self.assertAlmostEqual(vals[2], 1.0, places=8)

    def test_one_by_one(self):
        vals, vecs = ev.jacobi_eigen([[5]])
        self.assertAlmostEqual(vals[0], 5.0, places=8)
        self.assertAlmostEqual(vecs[0][0], 1.0, places=8)

    def test_non_symmetric_raises_value_error(self):
        with self.assertRaises(ValueError):
            ev.jacobi_eigen([[1, 2], [3, 4]])


class PowerIterationTest(unittest.TestCase):
    def test_diagonal_dominant_anchor(self):
        # [[2, 0], [0, 1]]: dominant eigenvalue 2.0, eigenvector [1, 0].
        lam, v = ev.power_iteration(A_DIAG2)
        self.assertAlmostEqual(lam, 2.0, places=8)
        self.assertAlmostEqual(abs(v[0]), 1.0, places=8)
        self.assertAlmostEqual(v[1], 0.0, places=8)

    def test_offdiag_2x2_dominant(self):
        # [[2, 1], [1, 2]]: dominant eigenvalue 3.0.
        lam, v = ev.power_iteration(A_SYM2)
        self.assertAlmostEqual(lam, 3.0, places=8)
        self.assertLess(ev.residual_norm(A_SYM2, v, lam), 1e-8)

    def test_start_in_other_eigenspace_returns_that_pair(self):
        # v0 = [0, 1] lies exactly in the eigenvalue-1 eigenspace of
        # [[2, 0], [0, 1]]; power iteration cannot leave the
        # eigenspace, so it returns (1.0, [0, 1]) exactly.
        lam, v = ev.power_iteration(A_DIAG2, v0=[0.0, 1.0])
        self.assertAlmostEqual(lam, 1.0, places=8)
        self.assertAlmostEqual(v[0], 0.0, places=8)
        self.assertAlmostEqual(abs(v[1]), 1.0, places=8)

    def test_perturbed_start_finds_dominant(self):
        # A start with a component along the dominant eigenvector
        # converges to the dominant pair (2.0, [1, 0]).
        lam, v = ev.power_iteration(A_DIAG2, v0=[1.0, 0.5])
        self.assertAlmostEqual(lam, 2.0, places=8)
        self.assertAlmostEqual(abs(v[0]), 1.0, places=8)

    def test_deflation_exposes_second_eigenvalue(self):
        # Deflate the dominant pair out of [[2, 0], [0, 1]]: the
        # remaining dominant eigenvalue is 1.0, the second of A.
        lam1, v1 = ev.power_iteration(A_DIAG2)
        work = ev.deflate(A_DIAG2, lam1, v1)
        lam2, v2 = ev.power_iteration(work)
        self.assertAlmostEqual(lam2, 1.0, places=8)
        self.assertAlmostEqual(abs(v2[1]), 1.0, places=8)

    def test_power_spectrum_two_pairs(self):
        pairs = ev.power_spectrum(A_DIAG2, count=2)
        self.assertAlmostEqual(pairs[0][0], 2.0, places=8)
        self.assertAlmostEqual(pairs[1][0], 1.0, places=8)
        for lam, v in pairs:
            self.assertLess(ev.residual_norm(A_DIAG2, v, lam), 1e-8)

    def test_power_spectrum_matches_jacobi(self):
        # Both methods agree on the 2x2 symmetric anchor.
        power = sorted(lam for lam, _ in ev.power_spectrum(A_SYM2, count=2))
        jac = sorted(ev.jacobi_eigen(A_SYM2)[0])
        for a, b in zip(power, jac):
            self.assertAlmostEqual(a, b, places=8)

    def test_count_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            ev.power_spectrum(A_DIAG2, count=3)
        with self.assertRaises(ValueError):
            ev.power_spectrum(A_DIAG2, count=0)


class ResidualTest(unittest.TestCase):
    def test_exact_pair_zero_residual(self):
        self.assertAlmostEqual(ev.residual_norm(A_DIAG2, [1, 0], 2.0), 0.0, places=10)

    def test_wrong_eigenvalue_positive_residual(self):
        # lam = 1.0 against the [1, 0] eigenvector of [[2, 0], [0, 1]]:
        # the first row residual is |2 - 1| = 1.0.
        self.assertAlmostEqual(ev.residual_norm(A_DIAG2, [1, 0], 1.0), 1.0, places=10)

    def test_unit_norm_required_for_scale_meaning(self):
        # Scaling v scales the residual: 2*[1, 0] with lam 2.0 gives
        # |2*2 - 2*2| = 0, but 2*[1, 0] with lam 1.0 gives 2.0.
        self.assertAlmostEqual(ev.residual_norm(A_DIAG2, [2, 0], 1.0), 2.0, places=10)


class ValidationTest(unittest.TestCase):
    def test_non_square_raises(self):
        with self.assertRaises(ValueError):
            ev.power_iteration([[1, 2, 3], [4, 5, 6]])
        with self.assertRaises(ValueError):
            ev.jacobi_eigen([[1, 2, 3], [4, 5, 6]])

    def test_ragged_rows_raise(self):
        with self.assertRaises(ValueError):
            ev.power_iteration([[1, 2], [3]])

    def test_non_numeric_entries_raise(self):
        with self.assertRaises(ValueError):
            ev.power_iteration([[1, "a"], [3, 4]])
        with self.assertRaises(ValueError):
            ev.jacobi_eigen([[1, "a"], [3, 4]])

    def test_bool_entries_raise(self):
        # bool is an int subclass but is not a valid matrix entry.
        with self.assertRaises(ValueError):
            ev.power_iteration([[True, 2], [3, 4]])

    def test_empty_matrix_raises(self):
        with self.assertRaises(ValueError):
            ev.power_iteration([])

    def test_wrong_length_vector_raises(self):
        with self.assertRaises(ValueError):
            ev.power_iteration(A_DIAG2, v0=[1, 2, 3])

    def test_invalid_tolerance_raises(self):
        with self.assertRaises(ValueError):
            ev.power_iteration(A_DIAG2, tol=0)
        with self.assertRaises(ValueError):
            ev.jacobi_eigen(A_SYM2, tol=-1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
