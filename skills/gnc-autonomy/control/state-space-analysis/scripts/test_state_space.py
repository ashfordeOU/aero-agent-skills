#!/usr/bin/env python3
"""Gate 3 contract test: state-space control analysis logic.

Exercises scripts/state_space_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3. Hand-checked cases:

- A = [[0, 1], [-2, -3]] has characteristic polynomial
  lambda^2 + 3 lambda + 2 = 0, eigenvalues -1 and -2: stable.
- A = [[0, 1], [-2, 2]] has eigenvalues 1 +- i (real part +1):
  unstable. A = [[0, 1], [-2, 0]] is the oscillator, eigenvalues
  +- i*sqrt(2): marginal, real parts 0, not stable.
- Controllability of (A, B): with B = [[0], [1]] the controllability
  matrix [[0, 1], [1, -3]] has determinant -1 (rank 2, controllable);
  with B = [[1], [-2]] the second column A B = [-2, 4] is -2 times
  the first, rank 1 (uncontrollable).
- Observability of (A, C): with C = [[1, 0]] the observability matrix
  [[1, 0], [0, 1]] has rank 2 (observable); with C = [[2, 1]] the
  second row C A = [-2, -1] is minus the first row, rank 1
  (unobservable).
- State transition matrix: Phi(0) = I; for the diagonal A the closed
  form Phi(t) = diag(exp(-t), exp(-2t)); for A = [[0, 1], [-2, -3]]
  at t = 1 the eigenvector identities Phi [1, -1] = exp(-1) [1, -1]
  and Phi [1, -2] = exp(-2) [1, -2] hold; the repeated-eigenvalue
  Jordan case A = [[0, 1], [-1, -2]] (eigenvalue -1 twice) matches
  exp(-t) [[1 + t, t], [-t, 1 - t]].
- Canonical forms: A = [[-1, 2], [0, -2]] has det 2 and trace -3, so
  the controller canonical pair is A_c = [[0, 1], [-2, -3]],
  B_c = [[0], [1]] and the observer canonical pair is
  A_o = [[0, -2], [1, -3]], C_o = [1, 0].
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import state_space_logic as ssl  # noqa: E402

A_STABLE = [[0.0, 1.0], [-2.0, -3.0]]  # eigenvalues -1, -2
A_UNSTABLE = [[0.0, 1.0], [-2.0, 2.0]]  # eigenvalues 1 +- i
A_MARGINAL = [[0.0, 1.0], [-2.0, 0.0]]  # eigenvalues +- i*sqrt(2)
A_JORDAN = [[0.0, 1.0], [-1.0, -2.0]]  # eigenvalue -1 repeated


class EigenvalueTest(unittest.TestCase):
    def test_eigenvalues_stable_pair(self):
        # Characteristic polynomial lambda^2 + 3 lambda + 2: roots -1, -2.
        lamb = ssl.eigenvalues_2x2(A_STABLE)
        reals = sorted(v.real for v in lamb)
        self.assertAlmostEqual(reals[0], -2.0, places=10)
        self.assertAlmostEqual(reals[1], -1.0, places=10)
        for v in lamb:
            self.assertAlmostEqual(v.imag, 0.0, places=10)

    def test_eigenvalues_unstable_pair(self):
        # lambda^2 - 2 lambda + 2: roots 1 +- i.
        lamb = ssl.eigenvalues_2x2(A_UNSTABLE)
        reals = sorted(v.real for v in lamb)
        self.assertAlmostEqual(reals[0], 1.0, places=10)
        self.assertAlmostEqual(reals[1], 1.0, places=10)
        self.assertAlmostEqual(abs(lamb[0].imag), 1.0, places=10)

    def test_eigenvalues_marginal_pair(self):
        # lambda^2 + 2: roots +- i*sqrt(2), real part zero.
        lamb = ssl.eigenvalues_2x2(A_MARGINAL)
        for v in lamb:
            self.assertAlmostEqual(v.real, 0.0, places=10)
            self.assertAlmostEqual(abs(v.imag), math.sqrt(2.0), places=10)

    def test_rejects_wrong_size(self):
        with self.assertRaises(ValueError):
            ssl.eigenvalues_2x2([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])


class StabilityTest(unittest.TestCase):
    def test_stable_verdict(self):
        self.assertTrue(ssl.is_stable(A_STABLE))
        report = ssl.stability_report(A_STABLE)
        self.assertTrue(report["stable"])
        self.assertEqual(len(report["eigenvalues"]), 2)

    def test_unstable_verdict(self):
        self.assertFalse(ssl.is_stable(A_UNSTABLE))
        self.assertFalse(ssl.stability_report(A_UNSTABLE)["stable"])

    def test_marginal_is_not_stable(self):
        # Real part exactly zero: fails the all-real-parts-below-zero rule.
        self.assertFalse(ssl.is_stable(A_MARGINAL))

    def test_rejects_wrong_size(self):
        with self.assertRaises(ValueError):
            ssl.is_stable([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])


class RankTest(unittest.TestCase):
    def test_identity_rank(self):
        self.assertEqual(
            ssl.matrix_rank([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]), 3
        )

    def test_dependent_rows_rank_one(self):
        self.assertEqual(ssl.matrix_rank([[1.0, 2.0], [2.0, 4.0]]), 1)

    def test_zero_matrix_rank_zero(self):
        self.assertEqual(ssl.matrix_rank([[0.0, 0.0], [0.0, 0.0]]), 0)

    def test_rectangular_rank(self):
        # Rows [1, 2, 3] and [4, 5, 6] are independent.
        self.assertEqual(ssl.matrix_rank([[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]]), 2)

    def test_rejects_ragged_matrix(self):
        with self.assertRaises(ValueError):
            ssl.matrix_rank([[1.0, 2.0], [3.0]])


class ControllabilityTest(unittest.TestCase):
    def test_controllable_pair(self):
        # [B AB] = [[0, 1], [1, -3]], determinant -1, full rank.
        cm = ssl.controllability_matrix(A_STABLE, [[0.0], [1.0]])
        self.assertEqual(cm, [[0.0, 1.0], [1.0, -3.0]])
        self.assertEqual(ssl.matrix_rank(cm), 2)
        self.assertTrue(ssl.is_controllable(A_STABLE, [[0.0], [1.0]]))

    def test_uncontrollable_pair(self):
        # A B = [-2, 4] = -2 * B: columns dependent, rank 1.
        cm = ssl.controllability_matrix(A_STABLE, [[1.0], [-2.0]])
        self.assertEqual(ssl.matrix_rank(cm), 1)
        self.assertFalse(ssl.is_controllable(A_STABLE, [[1.0], [-2.0]]))

    def test_wrong_b_rows_raise(self):
        with self.assertRaises(ValueError):
            ssl.controllability_matrix(A_STABLE, [[1.0], [2.0], [3.0]])


class ObservabilityTest(unittest.TestCase):
    def test_observable_pair(self):
        # [C; CA] = [[1, 0], [0, 1]], full rank.
        ob = ssl.observability_matrix(A_STABLE, [[1.0, 0.0]])
        self.assertEqual(ob, [[1.0, 0.0], [0.0, 1.0]])
        self.assertEqual(ssl.matrix_rank(ob), 2)
        self.assertTrue(ssl.is_observable(A_STABLE, [[1.0, 0.0]]))

    def test_unobservable_pair(self):
        # C A = [-2, -1] = -C: rows dependent, rank 1.
        ob = ssl.observability_matrix(A_STABLE, [[2.0, 1.0]])
        self.assertEqual(ssl.matrix_rank(ob), 1)
        self.assertFalse(ssl.is_observable(A_STABLE, [[2.0, 1.0]]))

    def test_wrong_c_columns_raise(self):
        with self.assertRaises(ValueError):
            ssl.observability_matrix(A_STABLE, [[1.0, 0.0, 0.0]])


class StateTransitionTest(unittest.TestCase):
    def test_phi_at_zero_is_identity(self):
        phi = ssl.state_transition_matrix(A_STABLE, 0.0)
        self.assertAlmostEqual(phi[0][0], 1.0, places=12)
        self.assertAlmostEqual(phi[0][1], 0.0, places=12)
        self.assertAlmostEqual(phi[1][0], 0.0, places=12)
        self.assertAlmostEqual(phi[1][1], 1.0, places=12)

    def test_phi_diagonal_closed_form(self):
        # A = diag(-1, -2): Phi(t) = diag(exp(-t), exp(-2t)).
        phi = ssl.state_transition_matrix([[-1.0, 0.0], [0.0, -2.0]], 0.5)
        self.assertAlmostEqual(phi[0][0], math.exp(-0.5), places=10)
        self.assertAlmostEqual(phi[1][1], math.exp(-1.0), places=10)
        self.assertAlmostEqual(phi[0][1], 0.0, places=12)
        self.assertAlmostEqual(phi[1][0], 0.0, places=12)

    def test_phi_eigenvector_identity(self):
        # At t = 1, Phi [1, -1] = exp(-1) [1, -1] and
        # Phi [1, -2] = exp(-2) [1, -2] for A = [[0, 1], [-2, -3]].
        phi = ssl.state_transition_matrix(A_STABLE, 1.0)
        pv1 = [phi[0][0] - phi[0][1], phi[1][0] - phi[1][1]]
        pv2 = [phi[0][0] - 2.0 * phi[0][1], phi[1][0] - 2.0 * phi[1][1]]
        for i in (0, 1):
            self.assertAlmostEqual(pv1[i], math.exp(-1.0) * (1.0 if i == 0 else -1.0), places=9)
            self.assertAlmostEqual(pv2[i], math.exp(-2.0) * (1.0 if i == 0 else -2.0), places=9)

    def test_phi_repeated_eigenvalue_jordan(self):
        # A = [[0, 1], [-1, -2]] (eigenvalue -1 twice):
        # Phi(t) = exp(-t) [[1 + t, t], [-t, 1 - t]].
        phi = ssl.state_transition_matrix(A_JORDAN, 0.5)
        e = math.exp(-0.5)
        self.assertAlmostEqual(phi[0][0], e * 1.5, places=10)
        self.assertAlmostEqual(phi[0][1], e * 0.5, places=10)
        self.assertAlmostEqual(phi[1][0], -e * 0.5, places=10)
        self.assertAlmostEqual(phi[1][1], e * 0.5, places=10)

    def test_phi_rejects_wrong_size(self):
        with self.assertRaises(ValueError):
            ssl.state_transition_matrix(
                [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]], 1.0
            )


class CanonicalFormTest(unittest.TestCase):
    def test_controller_canonical_form(self):
        # A = [[-1, 2], [0, -2]]: det 2, trace -3 -> a0 = 2, a1 = 3.
        ac, bc = ssl.controller_canonical_form([[-1.0, 2.0], [0.0, -2.0]], [[0.0], [1.0]])
        for r in range(2):
            for c in range(2):
                self.assertAlmostEqual(ac[r][c], [[0.0, 1.0], [-2.0, -3.0]][r][c], places=12)
        self.assertEqual(bc, [[0.0], [1.0]])

    def test_observer_canonical_form(self):
        ao, co = ssl.observer_canonical_form([[-1.0, 2.0], [0.0, -2.0]], [[1.0, 0.0]])
        for r in range(2):
            for c in range(2):
                self.assertAlmostEqual(ao[r][c], [[0.0, -2.0], [1.0, -3.0]][r][c], places=12)
        self.assertEqual(co, [1.0, 0.0])

    def test_uncontrollable_pair_raises(self):
        with self.assertRaises(ValueError):
            ssl.controller_canonical_form(A_STABLE, [[1.0], [-2.0]])

    def test_unobservable_pair_raises(self):
        with self.assertRaises(ValueError):
            ssl.observer_canonical_form(A_STABLE, [[2.0, 1.0]])


class ReportTest(unittest.TestCase):
    def test_analysis_report(self):
        report = ssl.analysis_report(A_STABLE, [[0.0], [1.0]], [[1.0, 0.0]], t=1.0)
        self.assertTrue(report["controllable"])
        self.assertTrue(report["observable"])
        self.assertTrue(report["stable"])
        self.assertEqual(len(report["eigenvalues"]), 2)
        self.assertEqual(len(report["state_transition_matrix"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
