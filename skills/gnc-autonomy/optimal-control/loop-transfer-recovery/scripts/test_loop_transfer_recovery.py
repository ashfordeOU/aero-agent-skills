#!/usr/bin/env python3
"""Contract test for the loop-transfer-recovery leaf (gnc-autonomy pack).

Covers the SKILL.md workflow end to end, step by step. Step 1 of the
workflow (fix the plant and the weights, build the log-spaced frequency
grid) is exercised by the frequency_grid checks; step 2 (solve the
regulator Riccati equation for the full-state target ingredient K) by
the regulator_riccati checks; step 3 (form the full-state target loop
samples and read the grid-max target magnitude) by the target_loop
checks; step 4 (solve the nominal filter Riccati equation and measure
the nominal LQG loop mismatch at q = 0) by the filter and loop_mismatch
checks; step 5 (run the recovery gain sweep: inflate the filter process
noise weight on the driven input channel, re-solve the filter Riccati
equation, evaluate the recovered output loop against the target) by the
sweep and recovered_loop checks; step 6 (read off the recovery gain q*
with the recovered filter covariance and estimator gain, the recovery
verdict and the improvement ratio) by the recovery_result checks; step 7
(confirm determinism and the stdlib-only rule) closes the file.

Every numeric assertion is tolerance based (isclose or absolute delta):
no exact float equality is asserted on any computed aggregate, so the
suite holds under both /usr/bin/python3 (3.9.6) and the pyenv 3.13.12
hook interpreter. All worked-example anchors are the real outputs of
scripts/loop_transfer_recovery_logic.py (bitwise identical under both
interpreters) and sit inside the magnitude bounds of the wave-45 spec.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import loop_transfer_recovery_logic as ltr  # noqa: E402

SQRT3 = math.sqrt(3.0)


def _mat_mul(A, B):
    """Multiply two 2x2 matrices given as lists of lists."""
    return [[A[0][0] * B[0][0] + A[0][1] * B[1][0],
             A[0][0] * B[0][1] + A[0][1] * B[1][1]],
            [A[1][0] * B[0][0] + A[1][1] * B[1][0],
             A[1][0] * B[0][1] + A[1][1] * B[1][1]]]


def _mat_t(A):
    """Transpose a 2x2 matrix."""
    return [[A[0][0], A[1][0]], [A[0][1], A[1][1]]]


def _mat_sub(A, B):
    """Subtract two 2x2 matrices."""
    return [[A[i][j] - B[i][j] for j in range(2)] for i in range(2)]


def _mat_add(A, B):
    """Add two 2x2 matrices."""
    return [[A[i][j] + B[i][j] for j in range(2)] for i in range(2)]


def _outer(v, w):
    """Outer product of two length-2 vectors."""
    return [[v[0] * w[0], v[0] * w[1]], [v[1] * w[0], v[1] * w[1]]]


def _max_entry(A):
    """Maximum absolute entry of a 2x2 matrix."""
    return max(abs(A[i][j]) for i in range(2) for j in range(2))


def _regulator_residual(a, P, K, q1, q2, r):
    """Max-entry residual of A'P + PA - P B R^-1 B' P + Q = 0."""
    A = [[0.0, 1.0], [0.0, -a]]
    pb = [P[0][1], P[1][1]]          # P B with B = [0, 1]
    btp = [P[1][0], P[1][1]]         # B' P with B = [0, 1]
    q = [[q1, 0.0], [0.0, q2]]
    res = _mat_add(_mat_mul(_mat_t(A), P), _mat_mul(P, A))
    res = _mat_sub(res, _mat_scale(1.0 / r, _outer(pb, btp)))
    res = _mat_add(res, q)
    # consistency: the closed-form gain must be K = [p2 / r, p3 / r]
    assert abs(K[0] - P[0][1] / r) < 1e-12 and abs(K[1] - P[1][1] / r) < 1e-12
    return _max_entry(res)


def _mat_scale(c, A):
    """Scale a 2x2 matrix by the scalar c."""
    return [[c * A[i][j] for j in range(2)] for i in range(2)]


def _filter_residual(a, S, w1, w2, rv):
    """Max-entry residual of A S + S A' - S C' Rw^-1 C S + Qw = 0."""
    A = [[0.0, 1.0], [0.0, -a]]
    sc = [S[0][0], S[1][0]]          # S C' with C = [1, 0]
    cs = [S[0][0], S[0][1]]          # C S with C = [1, 0]
    qw = [[w1, 0.0], [0.0, w2]]
    res = _mat_add(_mat_mul(A, S), _mat_mul(S, _mat_t(A)))
    res = _mat_sub(res, _mat_scale(1.0 / rv, _outer(sc, cs)))
    res = _mat_add(res, qw)
    return _max_entry(res)


def _worked():
    """Full worked-scenario recovery result (a = 0, matched weights)."""
    return ltr.recovery_result()


class TestFrequencyGrid(unittest.TestCase):
    """Step 1 of the SKILL.md workflow: the log-spaced frequency grid."""

    def test_grid_has_41_log_spaced_points_over_band(self):
        """Step 1: the frequency grid over [0.1, 20] rad/s with 41 points."""
        grid = ltr.frequency_grid()
        self.assertEqual(len(grid), ltr.N_FREQ)
        self.assertEqual(len(grid), 41)
        self.assertTrue(math.isclose(grid[0], 0.1, rel_tol=1e-12, abs_tol=1e-12))
        self.assertTrue(math.isclose(grid[-1], 20.0, rel_tol=1e-12,
                                     abs_tol=1e-12))
        expected_ratio = (20.0 / 0.1) ** (1.0 / 40.0)
        for k in range(len(grid) - 1):
            self.assertTrue(math.isclose(grid[k + 1] / grid[k],
                                         expected_ratio, rel_tol=1e-12,
                                         abs_tol=1e-12))

    def test_grid_value_errors(self):
        """Step 1: non-physical bands and point counts raise ValueError."""
        with self.assertRaises(ValueError):
            ltr.frequency_grid(omega_min=0.0)
        with self.assertRaises(ValueError):
            ltr.frequency_grid(n_freq=1)
        with self.assertRaises(ValueError):
            ltr.frequency_grid(omega_min=0.1, omega_max=0.05)
        with self.assertRaises(ValueError):
            ltr.frequency_grid(omega_min=float("inf"))
        with self.assertRaises(ValueError):
            ltr.frequency_grid(omega_min=-0.1)


class TestRegulatorRiccati(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the full-state target ingredient."""

    def test_regulator_worked_scenario_anchor(self):
        """Step 2: P = [[sqrt(3), 1], [1, sqrt(3)]] and K = [1, sqrt(3)]."""
        P, K = ltr.regulator_riccati(0.0, 1.0, 1.0, 1.0)
        self.assertTrue(math.isclose(P[0][0], SQRT3, rel_tol=1e-9))
        self.assertTrue(math.isclose(P[0][1], 1.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(P[1][0], 1.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(P[1][1], SQRT3, rel_tol=1e-9))
        self.assertTrue(math.isclose(K[0], 1.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(K[1], SQRT3, rel_tol=1e-9))
        res = _regulator_residual(0.0, P, K, 1.0, 1.0, 1.0)
        self.assertLess(res, 1e-8)   # real anchor 4.441e-16

    def test_regulator_damped_plant_anchor(self):
        """Step 2: damped a = 0.5 target gain K = [1, 1.3027756377319946]."""
        P, K = ltr.regulator_riccati(0.5, 1.0, 1.0, 1.0)
        self.assertTrue(math.isclose(K[1], 1.3027756377319946, rel_tol=1e-9))
        res = _regulator_residual(0.5, P, K, 1.0, 1.0, 1.0)
        self.assertLess(res, 1e-8)

    def test_regulator_value_errors(self):
        """Step 2: negative damping or nonpositive weights raise ValueError."""
        with self.assertRaises(ValueError):
            ltr.regulator_riccati(a=-0.1, q1=1.0, q2=1.0, r=1.0)
        with self.assertRaises(ValueError):
            ltr.regulator_riccati(a=0.0, q1=1.0, q2=1.0, r=0.0)
        with self.assertRaises(ValueError):
            ltr.regulator_riccati(a=0.0, q1=-1.0, q2=1.0, r=1.0)
        with self.assertRaises(ValueError):
            ltr.regulator_riccati(a=0.0, q1=1.0, q2=-1.0, r=1.0)


class TestFilterRiccati(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the filter Riccati equation solve."""

    def test_filter_worked_scenario_anchor(self):
        """Step 4: nominal filter S0 = P and L0 = [sqrt(3), 1] at q = 0."""
        S, L = ltr.filter_riccati(0.0, 1.0, 1.0, 1.0)
        for i in range(2):
            for j in range(2):
                self.assertTrue(math.isclose(S[i][j], SQRT3 if i == j else 1.0,
                                             rel_tol=1e-9))
        self.assertTrue(math.isclose(L[0], SQRT3, rel_tol=1e-9))
        self.assertTrue(math.isclose(L[1], 1.0, rel_tol=1e-9))
        res = _filter_residual(0.0, S, 1.0, 1.0, 1.0)
        self.assertLess(res, 1e-8)   # real anchor 4.441e-16

    def test_filter_damped_cross_sibling_identity(self):
        """Step 4: filter_riccati(0.5, 1.0, 4.0, 1.0) matches the lqg-design
        Example B solution through the a > 0 bisection branch."""
        S, L = ltr.filter_riccati(0.5, 1.0, 4.0, 1.0)
        self.assertTrue(math.isclose(S[0][0], 1.8179960365836825,
                                     rel_tol=1e-12))
        self.assertTrue(math.isclose(S[0][1], 1.1525547945169889,
                                     rel_tol=1e-12))
        self.assertTrue(math.isclose(S[1][1], 2.671617445635901,
                                     rel_tol=1e-12))
        self.assertTrue(math.isclose(L[0], 1.8179960365836825, rel_tol=1e-12))
        self.assertTrue(math.isclose(L[1], 1.1525547945169889, rel_tol=1e-12))
        res = _filter_residual(0.5, S, 1.0, 4.0, 1.0)
        self.assertLess(res, 1e-8)

    def test_filter_value_errors(self):
        """Step 4: negative weights or a nonpositive driven-state noise w2
        raise ValueError (w2 = 0 leaves the double integrator unstabilizable)."""
        with self.assertRaises(ValueError):
            ltr.filter_riccati(0.0, w1=-1.0, w2=1.0, rv=1.0)
        with self.assertRaises(ValueError):
            ltr.filter_riccati(0.0, w1=1.0, w2=0.0, rv=1.0)
        with self.assertRaises(ValueError):
            ltr.filter_riccati(0.0, w1=1.0, w2=1.0, rv=-1.0)
        with self.assertRaises(ValueError):
            ltr.filter_riccati(-0.1, w1=1.0, w2=1.0, rv=1.0)

    def test_s2_root_closed_form_and_bisection_branch(self):
        """Step 4: s2 is sqrt(rv w2) at a = 0 and the bisection root of the
        monotone scalar equation on (0, sqrt(rv w2)] at a > 0."""
        self.assertEqual(ltr.s2_root(0.0, 1.0, 1.0, 1.0), 1.0)
        s2 = ltr.s2_root(0.5, 1.0, 4.0, 1.0)
        hi = math.sqrt(4.0)
        self.assertGreater(s2, 0.0)
        self.assertLessEqual(s2, hi)
        f = (s2 * s2 + 2.0 * 0.25 * s2
             + 2.0 * 0.5 * s2 * math.sqrt(2.0 * s2 + 1.0) - 4.0)
        self.assertLess(abs(f), 1e-9)


class TestRecoveryInflation(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the driven-channel noise inflation."""

    def test_inflation_quadratic_law(self):
        """Step 5: the filter process noise weight on the driven input
        channel grows with the square of the recovery gain q."""
        for q in (0.0, 10.0, 100.0, 1e7):
            self.assertTrue(math.isclose(ltr.inflated_noise_covariance(q),
                                         1.0 + q * q, rel_tol=1e-15,
                                         abs_tol=1e-12))
        self.assertTrue(math.isclose(ltr.inflated_noise_covariance(1e7),
                                     1.0 + 1e14, rel_tol=1e-15, abs_tol=1e-9))

    def test_inflation_value_errors(self):
        """Step 5: a negative or non-finite recovery gain raises ValueError."""
        with self.assertRaises(ValueError):
            ltr.inflated_noise_covariance(-1.0)
        with self.assertRaises(ValueError):
            ltr.inflated_noise_covariance(float("nan"))


class TestTargetLoop(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the full-state target loop samples."""

    def test_target_loop_matrix_path_matches_closed_form(self):
        """Step 3: the 2x2 matrix path L_t(j w) = -(1/w^2) - j sqrt(3)/w at
        every grid point of the worked scenario."""
        grid = ltr.frequency_grid()
        K = [1.0, SQRT3]
        worst = 0.0
        for w in grid:
            t = ltr.target_loop(complex(0.0, w), 0.0, K)
            closed = -(1.0 / (w * w)) - 1j * SQRT3 / w
            worst = max(worst, abs(t - closed))
        self.assertLess(worst, 1e-12)   # real anchor max abs diff 3.553e-15

    def test_target_loop_grid_max_and_unity_crossing(self):
        """Step 3: the grid-max target magnitude 101.48891565092218 at w =
        0.1 rad/s and the unity-magnitude crossing at w_c = 1.8173540210239707
        rad/s, the band context of the frequency grid."""
        res = _worked()
        self.assertTrue(math.isclose(res["max_target"],
                                     101.48891565092218, rel_tol=1e-6))
        wc = math.sqrt((3.0 + math.sqrt(13.0)) / 2.0)
        self.assertTrue(math.isclose(wc, 1.8173540210239707, rel_tol=1e-12))
        mag = abs(ltr.target_loop(complex(0.0, wc), 0.0, [1.0, SQRT3]))
        self.assertTrue(math.isclose(mag, 1.0, rel_tol=1e-9))
        self.assertEqual(len(res["target_samples"]), ltr.N_FREQ)
        w0, t0 = res["target_samples"][0]
        self.assertTrue(math.isclose(w0, 0.1, rel_tol=1e-12))
        self.assertTrue(math.isclose(t0.real, -100.0, rel_tol=1e-9))
        self.assertTrue(math.isclose(t0.imag, -SQRT3 / 0.1, rel_tol=1e-9))


class TestRecoveredLoop(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the recovered output loop samples."""

    def test_recovered_loop_matches_rational_closed_form_q1000(self):
        """Step 5: at q = 1000 the 2x2 matrix loop equals num / (s^2 den)
        with num and den as pinned, at every grid point of the worked
        scenario."""
        grid = ltr.frequency_grid()
        K = [1.0, SQRT3]
        _, L = ltr.filter_riccati(0.0, 1.0,
                                  ltr.inflated_noise_covariance(1000.0), 1.0)
        k1, k2 = K
        l1, l2 = L
        worst = 0.0
        for w in grid:
            sw = complex(0.0, w)
            rec = ltr.recovered_loop(sw, 0.0, K, L)
            num = (k1 * l1 + k2 * l2) * sw + k1 * (0.0 * l1 + l2)
            den = (sw * sw + (l1 + 0.0 + k2) * sw
                   + (0.0 + k2) * l1 + k1 + l2)
            worst = max(worst, abs(rec - num / (sw * sw * den)))
        self.assertLess(worst, 1e-9)    # real anchor max abs diff 9.379e-13

    def test_recovered_loop_multiplication_orders_bitwise(self):
        """Step 5: the SISO loop equals G(s) times the matrix loop scalar in
        either multiplication order; complex scalars commute, so the two
        orders agree bitwise (max abs diff 0.0)."""
        grid = ltr.frequency_grid()
        K = [1.0, SQRT3]
        _, L = ltr.filter_riccati(0.0, 1.0,
                                  ltr.inflated_noise_covariance(1000.0), 1.0)
        worst = 0.0
        for w in grid:
            sw = complex(0.0, w)
            g = 1.0 / (sw * sw)
            u = ltr._matrix_loop_scalar(sw, 0.0, K, L)
            worst = max(worst, abs(ltr.recovered_loop(sw, 0.0, K, L) - u * g))
        self.assertEqual(worst, 0.0)

    def test_nominal_loop_transfer_closed_form_q0(self):
        """Step 4: the nominal (q = 0) output loop matches
        (1 + 2 sqrt(3) s) / (s^2 (s^2 + 2 sqrt(3) s + 5)) at every grid
        point, the estimator lag and roll-off that recovery reshapes."""
        grid = ltr.frequency_grid()
        K = [1.0, SQRT3]
        _, L0 = ltr.filter_riccati(0.0, 1.0, 1.0, 1.0)
        worst = 0.0
        for w in grid:
            sw = complex(0.0, w)
            rec = ltr.recovered_loop(sw, 0.0, K, L0)
            closed = ((1.0 + 2.0 * SQRT3 * sw)
                      / (sw * sw * (sw * sw + 2.0 * SQRT3 * sw + 5.0)))
            worst = max(worst, abs(rec - closed))
        self.assertLess(worst, 1e-9)    # real anchor max abs diff 1.42e-14


class TestLoopMismatch(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the nominal LQG loop mismatch."""

    def test_nominal_mismatch_anchor(self):
        """Step 4: at q = 0 the output loop sits up to 79% of the target peak
        magnitude off the full-state loop: M(0) = 0.79265793913710081 and
        Mmag(0) = 0.79152889018535089."""
        res = _worked()
        self.assertTrue(math.isclose(res["mismatch_nominal"],
                                     0.79265793913710081, rel_tol=1e-6))
        M, Mmag, L, S, max_t = ltr.loop_mismatch(0.0, 0.0, res["K"],
                                                 res["grid"])
        self.assertTrue(math.isclose(M, 0.79265793913710081, rel_tol=1e-6))
        self.assertTrue(math.isclose(Mmag, 0.79152889018535089,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(max_t, 101.48891565092218,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(L[0], SQRT3, rel_tol=1e-6))
        self.assertTrue(math.isclose(L[1], 1.0, rel_tol=1e-6))

    def test_loop_mismatch_invalid_q(self):
        """Step 4: a negative recovery gain q is rejected with ValueError."""
        grid = ltr.frequency_grid()
        with self.assertRaises(ValueError):
            ltr.loop_mismatch(-1.0, 0.0, [1.0, SQRT3], grid)


class TestRecoverySweep(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the recovery gain sweep over q."""

    def test_sweep_trace_anchors(self):
        """Step 5: the 8 trace entries (q, M(q), Mmag(q)) of the geometric
        sweep q = 10 .. 1e8 match the worked-example table within 1e-6
        relative per entry."""
        grid = ltr.frequency_grid()
        trace, q_star = ltr.recovery_sweep(0.0, [1.0, SQRT3], grid)
        anchors = [
            (10.0, 0.46672494862660469, 0.46665926627057602,
             4.5934465537591462, 10.04987562112089),
            (100.0, 0.20156746815359272, 0.20156524575736853,
             14.177799538363226, 100.00499987500625),
            (1000.0, 0.072062021956610434, 0.072062015642601701,
             44.732549670231741, 1000.000499999875),
            (10000.0, 0.023772073268366271, 0.023772060968471405,
             141.42489208056693, 10000.000050000001),
            (100000.0, 0.0076215835906494403, 0.0076215752257677788,
             447.21471354372943, 100000.00000499999),
            (1000000.0, 0.0024207706165423701, 0.0024207674026657765,
             1414.2139159267949, 1000000.0000005),
            (10000000.0, 0.00076658259948715081, 0.0007665815223384054,
             4472.1360668029884, 10000000.00000005),
            (100000000.0, 0.0002425216736106494, 0.00024252132677611768,
             14142.135659086289, 100000000.0),
        ]
        self.assertEqual(len(trace), len(anchors))
        for entry, (aq, aM, aMm, al1, al2) in zip(trace, anchors):
            q, M, Mmag, l1, l2 = entry
            self.assertTrue(math.isclose(q, aq, rel_tol=1e-12))
            self.assertTrue(math.isclose(M, aM, rel_tol=1e-6))
            self.assertTrue(math.isclose(Mmag, aMm, rel_tol=1e-6))
            self.assertTrue(math.isclose(l1, al1, rel_tol=1e-6))
            self.assertTrue(math.isclose(l2, al2, rel_tol=1e-6))

    def test_sweep_mismatch_strictly_decreasing(self):
        """Step 5: M(q) strictly decreases over the sweep, the minimum-phase
        recovery law of the canonical family."""
        grid = ltr.frequency_grid()
        trace, _ = ltr.recovery_sweep(0.0, [1.0, SQRT3], grid)
        Ms = [entry[1] for entry in trace]
        self.assertTrue(all(Ms[i] > Ms[i + 1] for i in range(len(Ms) - 1)))

    def test_sweep_late_decay_law(self):
        """Step 5: the late-decay ratio M(1e8) / M(1e7) = 0.316367 sits
        within 0.02 of 1/sqrt(10) = 0.316228, the M ~ c / sqrt(q) law of the
        recovery error, and M(q) sqrt(q) trends toward the constant 2.425."""
        grid = ltr.frequency_grid()
        trace, _ = ltr.recovery_sweep(0.0, [1.0, SQRT3], grid)
        ratio = trace[-1][1] / trace[-2][1]
        self.assertTrue(math.isclose(ratio, 1.0 / math.sqrt(10.0),
                                     rel_tol=0.02))
        last = trace[-1][1] * math.sqrt(trace[-1][0])
        self.assertTrue(math.isclose(last, 2.425217, rel_tol=0.02))

    def test_sweep_value_errors(self):
        """Step 5: non-physical sweep bounds (q_min = 0, q_max < q_min,
        step <= 1, tol <= 0) raise ValueError before any evaluation."""
        grid = ltr.frequency_grid()
        K = [1.0, SQRT3]
        with self.assertRaises(ValueError):
            ltr.recovery_sweep(0.0, K, grid, q_min=0.0)
        with self.assertRaises(ValueError):
            ltr.recovery_sweep(0.0, K, grid, q_min=100.0, q_max=10.0)
        with self.assertRaises(ValueError):
            ltr.recovery_sweep(0.0, K, grid, step=1.0)
        with self.assertRaises(ValueError):
            ltr.recovery_sweep(0.0, K, grid, tol=0.0)


class TestRecoveryResult(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the recovery verdict and q*."""

    def test_recovery_verdict_anchor(self):
        """Step 6: q* = 1e7 is the first sweep q with M(q) <= 1e-3, the
        recovered output loop matches the full-state target loop to better
        than 7.7e-4 of the peak, and the improvement over the nominal LQG
        loop is M(0) / M(q*) = 1034.02."""
        res = _worked()
        self.assertTrue(math.isclose(res["q_star"], 1e7, rel_tol=1e-12))
        self.assertTrue(res["verdict"])
        self.assertTrue(math.isclose(res["m_star"],
                                     0.00076658259948715081, rel_tol=1e-6))
        self.assertTrue(math.isclose(res["mmag_star"],
                                     0.0007665815223384054, rel_tol=1e-6))
        self.assertTrue(math.isclose(res["improvement_ratio"], 1034.02,
                                     rel_tol=1e-3))
        self.assertLess(res["m_star"], ltr.RECOVERY_TOL)
        self.assertGreater(res["trace"][-3][1], ltr.RECOVERY_TOL)

    def test_recovery_star_solution_anchor(self):
        """Step 6: at q* the recovered filter covariance and estimator gain
        read S(q*) = [[4472.1360668029884, 10000000.00000005],
        [10000000.00000005, 44721360668.030106]] and
        L(q*) = [4472.1360668029884, 10000000.00000005]."""
        res = _worked()
        S = res["S_star"]
        L = res["L_star"]
        self.assertTrue(math.isclose(S[0][0], 4472.1360668029884,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(S[0][1], 10000000.00000005,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(S[1][0], 10000000.00000005,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(S[1][1], 44721360668.030106,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(L[0], 4472.1360668029884, rel_tol=1e-6))
        self.assertTrue(math.isclose(L[1], 10000000.00000005, rel_tol=1e-6))
        # inflation law closed form: l2(q) = sqrt(1 + q^2), l1(q) = sqrt(2
        # l2(q) + 1) for the undamped matched scenario
        self.assertTrue(math.isclose(L[1], math.sqrt(1.0 + 1e14),
                                     rel_tol=1e-9))
        self.assertTrue(math.isclose(L[0], math.sqrt(2.0 * L[1] + 1.0),
                                     rel_tol=1e-9))

    def test_are_residuals_below_gate(self):
        """Step 6: the regulator ARE residual at the worked weights and the
        filter ARE residual at q = 0 are 4.441e-16 and the filter residual
        at q* = 1e7 is 3.725e-09, all below the 1e-8 max-entry gate."""
        res = _worked()
        P, K = res["P"], res["K"]
        S0, L0 = res["S0"], res["L0"]
        r_reg = _regulator_residual(0.0, P, K, 1.0, 1.0, 1.0)
        self.assertLess(r_reg, 1e-8)
        r_f0 = _filter_residual(0.0, S0, 1.0, 1.0, 1.0)
        self.assertLess(r_f0, 1e-8)
        r_fs = _filter_residual(0.0, res["S_star"], 1.0,
                                1.0 + res["q_star"] ** 2, 1.0)
        self.assertLess(r_fs, 1e-8)
        # entries of S(q*) are order q^2 = 1e14, so the residual is tiny
        # relative to the solution entries
        self.assertLess(r_fs, 1e-6 * res["S_star"][0][0])

    def test_recovered_loop_samples_at_q_star(self):
        """Step 6: the recovered loop complex samples at w = 0.1, 1.0, 1.8
        and the magnitudes at w = 0.1, 1.0, 1.8, 10, 20 track the target
        loop samples across the whole band at q*."""
        res = _worked()
        K = res["K"]
        L = res["L_star"]
        complex_anchors = {
            0.1: -99.923364097491799 - 17.30710203489846j,
            1.0: -0.99999970038576613 - 1.7307100322379296j,
            1.8: -0.30917685386734922 - 0.96150535819929006j,
        }
        for w in (0.1, 1.0, 1.8):
            s = ltr.recovered_loop(complex(0.0, w), 0.0, K, L)
            anchor = complex_anchors[w]
            self.assertTrue(math.isclose(s.real, anchor.real, rel_tol=1e-6))
            self.assertTrue(math.isclose(s.imag, anchor.imag, rel_tol=1e-6))
        mag_anchors = {0.1: 101.41111612, 1.0: 1.9988388170,
                       1.8: 1.0099915251, 10.0: 0.17340382738,
                       20.0: 0.086593884562}
        for w, mag_a in mag_anchors.items():
            s = ltr.recovered_loop(complex(0.0, w), 0.0, K, L)
            self.assertTrue(math.isclose(abs(s), mag_a, rel_tol=1e-6))

    def test_result_value_errors(self):
        """Step 6: the driver validates sweep parameters before sweeping
        (q_min > q_max) and propagates weight ValueErrors."""
        with self.assertRaises(ValueError):
            ltr.recovery_result(q_min=1e9, q_max=1e8)
        with self.assertRaises(ValueError):
            ltr.recovery_result(q_min=0.0)
        with self.assertRaises(ValueError):
            ltr.recovery_result(w2=0.0)


class TestDampedRecovery(unittest.TestCase):
    """Step 5 and 6 of the SKILL.md workflow on the damped plant a = 0.5."""

    def test_damped_recovery_through_bisection(self):
        """Step 5: on the damped minimum-phase plant a = 0.5 the nominal
        mismatch M(0) = 7.1197214039e-01 drops to M(1e5) = 5.7834333689e-03
        through the bisection branch of the filter Riccati equation solve."""
        grid = ltr.frequency_grid()
        res = ltr.recovery_result(a=0.5)
        K = res["K"]
        self.assertTrue(math.isclose(K[1], 1.3027756377319946, rel_tol=1e-9))
        M0 = ltr.loop_mismatch(0.0, 0.5, K, grid)[0]
        self.assertTrue(math.isclose(M0, 7.1197214039e-01, rel_tol=1e-3))
        M5 = None
        for entry in res["trace"]:
            if entry[0] == 100000.0:
                M5 = entry[1]
        self.assertIsNotNone(M5)
        self.assertTrue(math.isclose(M5, 5.7834333689e-03, rel_tol=1e-3))
        self.assertTrue(math.isclose(M5 / M0, 8.123118e-03, rel_tol=1e-3))


class TestDeterminismAndPurity(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: deterministic, stdlib-only checks."""

    def test_determinism_bitwise(self):
        """Step 7: two identical recovery_result runs are bitwise identical
        in the trace, q_star, S_star and L_star (no RNG anywhere)."""
        r1 = _worked()
        r2 = _worked()
        self.assertEqual(r1["trace"], r2["trace"])
        self.assertEqual(r1["q_star"], r2["q_star"])
        self.assertEqual(r1["S_star"], r2["S_star"])
        self.assertEqual(r1["L_star"], r2["L_star"])
        self.assertEqual(r1["mismatch_nominal"], r2["mismatch_nominal"])

    def test_module_stdlib_only_no_rng(self):
        """Step 7: the logic module imports only math and never touches a
        random number generator."""
        source = open(ltr.__file__).read()
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                self.assertTrue("math" in stripped,
                                "non-stdlib import: %s" % stripped)
        self.assertNotIn("random", source)
        self.assertNotIn("__import__", source)

    def test_public_api_surface(self):
        """Step 7: the ten documented public functions exist and the module
        constants pin the worked scenario."""
        for name in ("frequency_grid", "regulator_riccati", "s2_root",
                     "filter_riccati", "inflated_noise_covariance",
                     "target_loop", "recovered_loop", "loop_mismatch",
                     "recovery_sweep", "recovery_result"):
            self.assertTrue(callable(getattr(ltr, name, None)), name)
        self.assertEqual(ltr.N_FREQ, 41)
        self.assertEqual(ltr.OMEGA_MIN, 0.1)
        self.assertEqual(ltr.OMEGA_MAX, 20.0)
        self.assertEqual(ltr.B, [0.0, 1.0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
