#!/usr/bin/env python3
"""Contract test for the lqg-design SKILL.md workflow (gnc-autonomy).

Exercises the six numbered SKILL.md workflow steps on the canonical damped
double integrator: step 1 fixes the canonical plant family
(A = [[0, 1], [0, -a]] with damping a >= 0, B = [0, 1], C = [1, 0]) and the
quadratic cost weights Q, R together with the noise covariances Qw, Rw;
step 2 is the regulator-riccati solve
(regulator_riccati returns the symmetric P and the gain K); step 3 is the
filter-riccati solve (filter_riccati returns the error covariance S and the
Kalman estimator gain L, with the s2 root in closed form at a = 0 and by
bisection at a > 0); step 4 assembles the dynamic output-feedback
compensator state-space realization (Ac, Bc, Cc, Dc); step 5 runs the
separation-principle verdict whose Faddeev-LeVerrier closed-loop polynomial
must equal the product of the regulator and estimator polynomials so the
closed-loop eigenvalues are the union of the regulator poles and the
estimator poles; step 6 reduces the compensator to its transfer function
G_c(s) = Cc (sI - Ac)^-1 Bc. The two worked examples are the spec anchors;
all numeric asserts are tolerance based (assertAlmostEqual delta or
math.isclose), never exact equality on computed sums. Stdlib only, offline,
deterministic, runs in well under 20 s.

Run: python3 scripts/test_lqg_design.py
"""

import ast
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lqg_design_logic import (  # noqa: E402
    compensator_realization,
    compensator_transfer_function,
    filter_riccati,
    filter_s2_bisection,
    regulator_riccati,
    separation_verdict,
)

# Worked example A (spec): a = 0, Q = diag(1, 1), R = 1, Qw = diag(1, 1), Rw = 1
A0 = [[0.0, 1.0], [0.0, 0.0]]
B = [0.0, 1.0]
C = [1.0, 0.0]
QA = [[1.0, 0.0], [0.0, 1.0]]
QWA = [[1.0, 0.0], [0.0, 1.0]]

# Worked example B (spec): a = 0.5, Q = diag(2, 1), R = 1, Qw = diag(1, 4), Rw = 1
AB = [[0.0, 1.0], [0.0, -0.5]]
QB = [[2.0, 0.0], [0.0, 1.0]]
QWB = [[1.0, 0.0], [0.0, 4.0]]

SQRT3 = math.sqrt(3.0)


def _mat_mul(X, Y):
    """Multiply two 2x2 matrices given as lists of lists."""
    return [[X[i][0] * Y[0][j] + X[i][1] * Y[1][j] for j in range(2)]
            for i in range(2)]


def _mat_transpose(M):
    """Transpose of a 2x2 matrix given as a list of lists."""
    return [[M[0][0], M[1][0]], [M[0][1], M[1][1]]]


def _outer_scale(v, scale):
    """Outer product v v' scaled by scale, as a 2x2 matrix."""
    return [[v[i] * v[j] * scale for j in range(2)] for i in range(2)]


def _max_abs(matrix):
    """Max absolute entry of a matrix or vector given as nested lists."""
    return max(abs(x) for row in matrix for x in row)


def _reg_are_residual(A, P, B, Q, r):
    """Max abs entry of A'P + PA - P B R^-1 B' P + Q (2x2, R scalar).

    Generic 2x2 algebra; P B = second column of P because B = [0, 1],
    so the quadratic term is the outer product of that column over r.
    """
    at_p = _mat_mul(_mat_transpose(A), P)
    p_a = _mat_mul(P, A)
    pb = [P[0][1], P[1][1]]
    quad = _outer_scale(pb, 1.0 / r)
    res = [[0.0, 0.0], [0.0, 0.0]]
    for i in range(2):
        for j in range(2):
            res[i][j] = at_p[i][j] + p_a[i][j] - quad[i][j] + Q[i][j]
    return _max_abs(res)


def _fil_are_residual(A, S, C, Qw, rv):
    """Max abs entry of A S + S A' - S C' Rw^-1 C S + Qw (2x2).

    Generic 2x2 algebra; S C' is the first column of S because C = [1, 0],
    so the quadratic term is the outer product of that column over rv.
    """
    a_s = _mat_mul(A, S)
    s_a = _mat_mul(S, _mat_transpose(A))
    sc = [S[0][0], S[1][0]]
    quad = _outer_scale(sc, 1.0 / rv)
    res = [[0.0, 0.0], [0.0, 0.0]]
    for i in range(2):
        for j in range(2):
            res[i][j] = a_s[i][j] + s_a[i][j] - quad[i][j] + Qw[i][j]
    return _max_abs(res)


def _poles_from_char(trace, det):
    """Roots of s^2 - trace s + det as [(re, im), (re, im)] pairs."""
    disc = trace * trace - 4.0 * det
    if disc >= 0.0:
        s = math.sqrt(disc)
        return [(0.5 * (trace + s), 0.0), (0.5 * (trace - s), 0.0)]
    s = math.sqrt(-disc)
    return [(0.5 * trace, 0.5 * s), (0.5 * trace, -0.5 * s)]


def _assert_vec_close(tc, actual, expected, delta):
    """assertAlmostEqual for every entry of two equal-length lists."""
    tc.assertEqual(len(actual), len(expected))
    for got, want in zip(actual, expected):
        tc.assertAlmostEqual(got, want, delta=delta)


class TestExampleARegulator(unittest.TestCase):
    """Workflow step 2, the regulator-riccati solve on example A."""

    def test_example_a_regulator_P_solution(self):
        """Step 2 regulator-riccati solve returns P = [[sqrt3, 1], [1, sqrt3]]."""
        P, _ = regulator_riccati(A0, B, QA, 1.0)
        for got, want in zip(P[0], [SQRT3, 1.0]):
            self.assertAlmostEqual(got, want, delta=1e-9)
        for got, want in zip(P[1], [1.0, SQRT3]):
            self.assertAlmostEqual(got, want, delta=1e-9)

    def test_example_a_regulator_gain_K(self):
        """Step 2 gain K = [1, sqrt3] from the Riccati solution P and R."""
        _, K = regulator_riccati(A0, B, QA, 1.0)
        _assert_vec_close(self, K, [1.0, SQRT3], 1e-9)

    def test_example_a_regulator_are_residual(self):
        """Step 2 Riccati solution P satisfies the ARE to max abs entry 1e-9."""
        P, K = regulator_riccati(A0, B, QA, 1.0)
        self.assertAlmostEqual(P[0][1], K[0], delta=1e-12)
        self.assertLess(_reg_are_residual(A0, P, B, QA, 1.0), 1e-9)

    def test_example_a_regulator_pole_pair(self):
        """Step 5 regulator poles of det(sI - (A - B K)) sit at -0.866 +- 0.5j."""
        _, K = regulator_riccati(A0, B, QA, 1.0)
        k1, k2 = K
        poles = _poles_from_char(-(k2), k1)
        for re, im in poles:
            self.assertAlmostEqual(re, -0.866025403784, delta=1e-6)
            self.assertAlmostEqual(abs(im), 0.5, delta=1e-6)


class TestExampleAFilter(unittest.TestCase):
    """Workflow step 3, the filter-riccati solve on example A."""

    def test_example_a_filter_S_matches_P_by_dual_symmetry(self):
        """Step 3 filter Riccati solution S equals P on the undamped plant."""
        P, _ = regulator_riccati(A0, B, QA, 1.0)
        S, _ = filter_riccati(A0, C, QWA, 1.0)
        for row_got, row_want in zip(S, P):
            _assert_vec_close(self, row_got, row_want, 1e-9)

    def test_example_a_filter_gain_L(self):
        """Step 3 Kalman gain L = [sqrt3, 1] from the filter Riccati solution."""
        _, L = filter_riccati(A0, C, QWA, 1.0)
        _assert_vec_close(self, L, [SQRT3, 1.0], 1e-9)

    def test_example_a_filter_s2_closed_form_root(self):
        """Step 3 s2 root is sqrt(rv w2) = 1 in closed form at a = 0."""
        S, _ = filter_riccati(A0, C, QWA, 1.0)
        self.assertAlmostEqual(S[0][1], math.sqrt(1.0 * 1.0), delta=1e-12)
        self.assertAlmostEqual(S[0][1], 1.0, delta=1e-12)

    def test_example_a_filter_s2_bisection_branch_agreement(self):
        """Step 3 forced bisection s2 branch returns sqrt(rv w2) within 1e-12."""
        s2_bisect = filter_s2_bisection(0.0, 1.0, 1.0, 1.0)
        self.assertAlmostEqual(s2_bisect, math.sqrt(1.0), delta=1e-12)

    def test_example_a_filter_are_residual(self):
        """Step 3 covariance S satisfies the filter ARE to max abs entry 1e-9."""
        S, _ = filter_riccati(A0, C, QWA, 1.0)
        self.assertLess(_fil_are_residual(A0, S, C, QWA, 1.0), 1e-9)

    def test_example_a_estimator_pole_pair(self):
        """Step 5 estimator poles of det(sI - (A - L C)) sit at -0.866 +- 0.5j."""
        _, L = filter_riccati(A0, C, QWA, 1.0)
        l1, l2 = L
        poles = _poles_from_char(-(l1), l2)  # a = 0: trace -(a + l1), det a l1 + l2
        for re, im in poles:
            self.assertAlmostEqual(re, -0.866025403784, delta=1e-6)
            self.assertAlmostEqual(abs(im), 0.5, delta=1e-6)


class TestExampleACompensator(unittest.TestCase):
    """Workflow steps 4 to 6, compensator assembly on example A."""

    def test_example_a_compensator_state_space_realization(self):
        """Step 4 dynamic output-feedback compensator realization matrices."""
        _, K = regulator_riccati(A0, B, QA, 1.0)
        _, L = filter_riccati(A0, C, QWA, 1.0)
        Ac, Bc, Cc, Dc = compensator_realization(A0, B, C, K, L)
        _assert_vec_close(self, Ac[0], [-SQRT3, 1.0], 1e-9)
        _assert_vec_close(self, Ac[1], [-2.0, -SQRT3], 1e-9)
        _assert_vec_close(self, Bc, L, 1e-12)
        _assert_vec_close(self, Cc, [-1.0, -SQRT3], 1e-9)
        self.assertEqual(Dc, 0.0)

    def test_example_a_compensator_own_poles(self):
        """Step 4 Ac poles -1.732 +- 1.414j are NOT the closed-loop poles."""
        _, K = regulator_riccati(A0, B, QA, 1.0)
        _, L = filter_riccati(A0, C, QWA, 1.0)
        Ac, _, _, _ = compensator_realization(A0, B, C, K, L)
        trace = Ac[0][0] + Ac[1][1]
        det = Ac[0][0] * Ac[1][1] - Ac[0][1] * Ac[1][0]
        for re, im in _poles_from_char(trace, det):
            self.assertAlmostEqual(re, -SQRT3, delta=1e-6)
            self.assertAlmostEqual(abs(im), math.sqrt(2.0), delta=1e-6)

    def test_example_a_separation_verdict_polynomial_identity(self):
        """Step 5 verdict: 4x4 closed-loop polynomial equals (s^2 + sqrt3 s + 1)^2."""
        _, K = regulator_riccati(A0, B, QA, 1.0)
        _, L = filter_riccati(A0, C, QWA, 1.0)
        v = separation_verdict(A0, B, C, K, L)
        _assert_vec_close(self, v["regulator_polynomial"],
                          [1.0, SQRT3, 1.0], 1e-9)
        _assert_vec_close(self, v["estimator_polynomial"],
                          [1.0, SQRT3, 1.0], 1e-9)
        _assert_vec_close(self, v["closed_loop_polynomial"],
                          [1.0, 3.46410161514, 5.0, 3.46410161514, 1.0], 1e-6)
        _assert_vec_close(self, v["product_polynomial"],
                          [1.0, 3.46410161514, 5.0, 3.46410161514, 1.0], 1e-6)
        self.assertLess(v["max_abs_diff"], 1e-9)
        self.assertTrue(v["separated"])

    def test_example_a_compensator_transfer_function(self):
        """Step 6 transfer function G_c(s) = (-3.464 s - 1) / (s^2 + 3.464 s + 5)."""
        _, K = regulator_riccati(A0, B, QA, 1.0)
        _, L = filter_riccati(A0, C, QWA, 1.0)
        Ac, Bc, Cc, _ = compensator_realization(A0, B, C, K, L)
        num, den = compensator_transfer_function(Ac, Bc, Cc)
        _assert_vec_close(self, num, [-3.46410161514, -1.0], 1e-6)
        _assert_vec_close(self, den, [1.0, 3.46410161514, 5.0], 1e-6)


class TestExampleB(unittest.TestCase):
    """Worked example B exercises the filter bisection branch (a = 0.5)."""

    def test_example_b_regulator_P_solution(self):
        """Step 2 regulator-riccati solve on the damped plant (a = 0.5)."""
        P, _ = regulator_riccati(AB, B, QB, 1.0)
        _assert_vec_close(self, P[0], [2.85602070187, 1.41421356237], 1e-6)
        _assert_vec_close(self, P[1], [1.41421356237, 1.5195116055], 1e-6)

    def test_example_b_regulator_gain_and_poles(self):
        """Step 2 gain K and step 5 regulator poles -1.0098 +- 0.6282j."""
        _, K = regulator_riccati(AB, B, QB, 1.0)
        _assert_vec_close(self, K, [1.41421356237, 1.5195116055], 1e-6)
        k1, k2 = K
        poles = _poles_from_char(-(0.5 + k2), k1)
        for re, im in poles:
            self.assertAlmostEqual(re, -1.00975580275, delta=1e-6)
            self.assertAlmostEqual(abs(im), 0.628177348514, delta=1e-6)

    def test_example_b_regulator_are_residual(self):
        """Step 2 damped-plant Riccati solution satisfies the ARE to 1e-9."""
        P, _ = regulator_riccati(AB, B, QB, 1.0)
        self.assertLess(_reg_are_residual(AB, P, B, QB, 1.0), 1e-9)

    def test_example_b_filter_S(self):
        """Step 3 filter-riccati covariance S on the damped plant (a = 0.5)."""
        S, _ = filter_riccati(AB, C, QWB, 1.0)
        _assert_vec_close(self, S[0], [1.81799603658, 1.15255479452], 1e-6)
        _assert_vec_close(self, S[1], [1.15255479452, 2.67161744564], 1e-6)

    def test_example_b_filter_gain_L(self):
        """Step 3 Kalman gain L from the bisection s2 root at a = 0.5."""
        _, L = filter_riccati(AB, C, QWB, 1.0)
        _assert_vec_close(self, L, [1.81799603658, 1.15255479452], 1e-6)

    def test_example_b_estimator_poles_faster_than_regulator(self):
        """Step 5 estimator poles -1.159 +- 0.8475j, faster than the regulator."""
        _, K = regulator_riccati(AB, B, QB, 1.0)
        _, L = filter_riccati(AB, C, QWB, 1.0)
        k1, k2 = K
        l1, l2 = L
        reg = _poles_from_char(-(0.5 + k2), k1)
        est = _poles_from_char(-(0.5 + l1), 0.5 * l1 + l2)
        for re, im in est:
            self.assertAlmostEqual(re, -1.15899801829, delta=1e-6)
            self.assertAlmostEqual(abs(im), 0.847511891601, delta=1e-6)
        self.assertLess(est[0][0], reg[0][0])

    def test_example_b_filter_are_residual_validates_bisection(self):
        """Step 3 bisection-branch covariance satisfies the filter ARE to 1e-9."""
        S, _ = filter_riccati(AB, C, QWB, 1.0)
        self.assertLess(_fil_are_residual(AB, S, C, QWB, 1.0), 1e-9)

    def test_example_b_compensator_realization(self):
        """Step 4 damped-plant compensator state-space realization Ac."""
        _, K = regulator_riccati(AB, B, QB, 1.0)
        _, L = filter_riccati(AB, C, QWB, 1.0)
        Ac, _, _, _ = compensator_realization(AB, B, C, K, L)
        _assert_vec_close(self, Ac[0], [-1.81799603658, 1.0], 1e-6)
        _assert_vec_close(self, Ac[1], [-2.56676835689, -2.0195116055], 1e-6)

    def test_example_b_separation_verdict(self):
        """Step 5 verdict: closed-loop polynomial equals the two-factor product."""
        _, K = regulator_riccati(AB, B, QB, 1.0)
        _, L = filter_riccati(AB, C, QWB, 1.0)
        v = separation_verdict(AB, B, C, K, L)
        _assert_vec_close(self, v["closed_loop_polynomial"],
                          [1.0, 4.33750764208, 8.15698627256,
                           7.44147126328, 2.91547594742], 1e-6)
        _assert_vec_close(self, v["product_polynomial"],
                          [1.0, 4.33750764208, 8.15698627256,
                           7.44147126328, 2.91547594742], 1e-6)
        self.assertLess(v["max_abs_diff"], 1e-9)
        self.assertTrue(v["separated"])

    def test_example_b_compensator_transfer_function(self):
        """Step 6 damped-plant G_c(s) numerator and monic denominator."""
        _, K = regulator_riccati(AB, B, QB, 1.0)
        _, L = filter_riccati(AB, C, QWB, 1.0)
        Ac, Bc, Cc, _ = compensator_realization(AB, B, C, K, L)
        num, den = compensator_transfer_function(Ac, Bc, Cc)
        _assert_vec_close(self, num, [-4.32235503752, -2.91547594742], 1e-6)
        _assert_vec_close(self, den, [1.0, 3.83750764208, 6.23823245152], 1e-6)


class TestGeneralIdentities(unittest.TestCase):
    """Closed-form identities and module hygiene across the workflow."""

    def test_dual_symmetry_matched_weights(self):
        """Step 2/3: S equals P on the undamped plant for matched scalar weights.

        Matched weights that are invariant under the state-index swap
        (q1 = q2 = w1 = w2 = r = rv) make the regulator Riccati solution P
        swap-symmetric, so the filter Riccati solution S coincides with P and
        the regulator and estimator pole pairs are identical. Example A is
        the unit-weight instance of this family.
        """
        Qm = [[2.0, 0.0], [0.0, 2.0]]
        P, K = regulator_riccati(A0, B, Qm, 2.0)
        S, L = filter_riccati(A0, C, Qm, 2.0)
        for row_got, row_want in zip(S, P):
            _assert_vec_close(self, row_got, row_want, 1e-9)
        _assert_vec_close(self, K, [1.0, SQRT3], 1e-9)
        _assert_vec_close(self, L, [SQRT3, 1.0], 1e-9)
        v = separation_verdict(A0, B, C, K, L)
        _assert_vec_close(self, v["regulator_polynomial"],
                          v["estimator_polynomial"], 1e-12)

    def test_regulator_are_residual_general_weights(self):
        """Step 2 ARE identity holds for a = 0.7 with q1 = 4, q2 = 1, r = 0.5."""
        Ag = [[0.0, 1.0], [0.0, -0.7]]
        Qg = [[4.0, 0.0], [0.0, 1.0]]
        P, _ = regulator_riccati(Ag, B, Qg, 0.5)
        self.assertLess(_reg_are_residual(Ag, P, B, Qg, 0.5), 1e-9)

    def test_filter_are_residual_damped_general_weights(self):
        """Step 3 filter ARE identity holds at a = 0.4, Qw = diag(0.5, 2), Rw = 3."""
        Ag = [[0.0, 1.0], [0.0, -0.4]]
        Qwg = [[0.5, 0.0], [0.0, 2.0]]
        S, _ = filter_riccati(Ag, C, Qwg, 3.0)
        self.assertLess(_fil_are_residual(Ag, S, C, Qwg, 3.0), 1e-9)

    def test_separation_identity_general_plant(self):
        """Step 5 union identity holds off the anchors at a = 0.2."""
        Ag = [[0.0, 1.0], [0.0, -0.2]]
        Qg = [[1.5, 0.0], [0.0, 0.8]]
        Qwg = [[0.6, 0.0], [0.0, 1.2]]
        _, K = regulator_riccati(Ag, B, Qg, 2.0)
        _, L = filter_riccati(Ag, C, Qwg, 1.5)
        v = separation_verdict(Ag, B, C, K, L)
        k1, k2 = K
        l1, l2 = L
        _assert_vec_close(self, v["regulator_polynomial"],
                          [1.0, 0.2 + k2, k1], 1e-12)
        _assert_vec_close(self, v["estimator_polynomial"],
                          [1.0, 0.2 + l1, 0.2 * l1 + l2], 1e-12)
        self.assertLess(v["max_abs_diff"], 1e-9)
        self.assertTrue(v["separated"])

    def test_transfer_denominator_trace_det_identity(self):
        """Step 6 denominator equals s^2 - tr(Ac) s + det(Ac) exactly."""
        _, K = regulator_riccati(AB, B, QB, 1.0)
        _, L = filter_riccati(AB, C, QWB, 1.0)
        Ac, Bc, Cc, _ = compensator_realization(AB, B, C, K, L)
        num, den = compensator_transfer_function(Ac, Bc, Cc)
        trace = Ac[0][0] + Ac[1][1]
        det = Ac[0][0] * Ac[1][1] - Ac[0][1] * Ac[1][0]
        _assert_vec_close(self, den, [1.0, -trace, det], 1e-9)
        self.assertEqual(len(num), 2)
        self.assertEqual(len(den), 3)

    def test_module_determinism_and_stdlib_only(self):
        """All workflow steps repeat identically; logic imports math only."""
        P1, K1 = regulator_riccati(AB, B, QB, 1.0)
        P2, K2 = regulator_riccati(AB, B, QB, 1.0)
        S1, L1 = filter_riccati(AB, C, QWB, 1.0)
        S2, L2 = filter_riccati(AB, C, QWB, 1.0)
        self.assertEqual(P1, P2)
        self.assertEqual(K1, K2)
        self.assertEqual(S1, S2)
        self.assertEqual(L1, L2)
        logic_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "lqg_design_logic.py")
        with open(logic_path, "r") as handle:
            tree = ast.parse(handle.read())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertLessEqual(imported, {"math"})


class TestValueErrorContract(unittest.TestCase):
    """Shared ValueError rejection of non-physical inputs, workflow step 1."""

    def test_valueerror_plant_structure_rejected(self):
        """Step 1 canonical-plant checks reject bad A, B and C."""
        bad_a = [[0.0, 1.0], [0.0, 0.1]]       # a = -0.1
        bad_swap = [[0.0, 1.0], [1.0, 0.0]]    # not canonical
        with self.assertRaises(ValueError):
            regulator_riccati(bad_a, B, QA, 1.0)
        with self.assertRaises(ValueError):
            filter_riccati(bad_a, C, QWA, 1.0)
        with self.assertRaises(ValueError):
            regulator_riccati(bad_swap, B, QA, 1.0)
        with self.assertRaises(ValueError):
            regulator_riccati(A0, [1.0, 0.0], QA, 1.0)
        with self.assertRaises(ValueError):
            filter_riccati(A0, [0.0, 1.0], QWA, 1.0)
        with self.assertRaises(ValueError):
            compensator_realization(A0, B, [0.0, 1.0], [1.0, 1.0], [1.0, 1.0])

    def test_valueerror_cost_weights_rejected(self):
        """Step 2 weight validation rejects non-diagonal or negative Q, zero R."""
        bad_q_off = [[1.0, 0.5], [0.0, 1.0]]
        bad_q_neg = [[1.0, 0.0], [0.0, -1.0]]
        with self.assertRaises(ValueError):
            regulator_riccati(A0, B, bad_q_off, 1.0)
        with self.assertRaises(ValueError):
            regulator_riccati(A0, B, bad_q_neg, 1.0)
        with self.assertRaises(ValueError):
            regulator_riccati(A0, B, QA, 0.0)

    def test_valueerror_noise_weights_rejected(self):
        """Step 3 noise-covariance validation rejects w1 < 0, w2 = 0, Rw < 0."""
        bad_w1 = [[-1.0, 0.0], [0.0, 1.0]]
        bad_w2 = [[1.0, 0.0], [0.0, 0.0]]
        with self.assertRaises(ValueError):
            filter_riccati(A0, C, bad_w1, 1.0)
        with self.assertRaises(ValueError):
            filter_riccati(A0, C, bad_w2, 1.0)
        with self.assertRaises(ValueError):
            filter_riccati(A0, C, QWA, -1.0)

    def test_valueerror_gain_lengths_rejected(self):
        """Steps 4 and 5 reject K or L that are not length-2 gain vectors."""
        with self.assertRaises(ValueError):
            compensator_realization(A0, B, C, [1.0], [1.0, 1.0])
        with self.assertRaises(ValueError):
            separation_verdict(A0, B, C, [1.0, 1.0], [1.0, 1.0, 1.0])
        with self.assertRaises(ValueError):
            compensator_transfer_function(A0, [1.0, 1.0, 1.0], [-1.0, -1.0])


if __name__ == "__main__":
    unittest.main()
