#!/usr/bin/env python3
"""Gate 3 contract test: LQR design (Riccati gain + closed-loop stability).

Exercises scripts/lqr_design_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the algebraic Riccati
equation solved for the canonical scalar-input two-state system
(A = [[0,1],[0,-a]], B = [0,1], Q = diag(q1, q2), R = r), the gain
matrix K = R^-1 B' P, closed-loop stability of A - B K from trace and
determinant, the Q/R cost-weight trade note, and ValueError on
impossible weights. Textbook check: double integrator (a = 0) with
Q = diag(1, 0), R = 1 gives P = [[sqrt(2), 1], [1, sqrt(2)]] and
K = [1, sqrt(2)] (position-error plus control-effort weighting).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lqr_design_logic as lqr  # noqa: E402

SQRT2 = 2.0 ** 0.5
SQRT3 = 3.0 ** 0.5
SQRT7 = 7.0 ** 0.5

A_DI = [[0.0, 1.0], [0.0, 0.0]]  # double integrator, a = 0
B_SI = [0.0, 1.0]                # scalar input


class RiccatiGainTest(unittest.TestCase):
    def test_textbook_double_integrator(self):
        # a = 0, Q = diag(1, 0), R = 1 -> P = [[sqrt(2), 1], [1, sqrt(2)]]
        P = lqr.riccati_gain(A_DI, B_SI, [[1.0, 0.0], [0.0, 0.0]], 1.0)
        self.assertAlmostEqual(P[0][0], SQRT2, delta=1e-9)
        self.assertAlmostEqual(P[0][1], 1.0, delta=1e-9)
        self.assertAlmostEqual(P[1][0], 1.0, delta=1e-9)
        self.assertAlmostEqual(P[1][1], SQRT2, delta=1e-9)

    def test_identity_weights(self):
        # a = 0, Q = I, R = 1 -> P = [[sqrt(3), 1], [1, sqrt(3)]]
        P = lqr.riccati_gain(A_DI, B_SI, [[1.0, 0.0], [0.0, 1.0]], 1.0)
        self.assertAlmostEqual(P[0][0], SQRT3, delta=1e-9)
        self.assertAlmostEqual(P[0][1], 1.0, delta=1e-9)
        self.assertAlmostEqual(P[1][1], SQRT3, delta=1e-9)

    def test_damped_system(self):
        # a = 2, q1 = q2 = 1, r = 1 -> p2 = 1, p3 = -2 + sqrt(7), p1 = sqrt(7)
        P = lqr.riccati_gain([[0.0, 1.0], [0.0, -2.0]], B_SI,
                             [[1.0, 0.0], [0.0, 1.0]], 1.0)
        self.assertAlmostEqual(P[0][1], 1.0, delta=1e-9)
        self.assertAlmostEqual(P[1][1], -2.0 + SQRT7, delta=1e-9)
        self.assertAlmostEqual(P[0][0], SQRT7, delta=1e-9)

    def test_zero_position_weight(self):
        # q1 = 0, q2 = 4, r = 1, a = 0 -> p2 = 0, p3 = 2, P[0][0] = 0
        P = lqr.riccati_gain(A_DI, B_SI, [[0.0, 0.0], [0.0, 4.0]], 1.0)
        self.assertAlmostEqual(P[0][0], 0.0, delta=1e-9)
        self.assertAlmostEqual(P[0][1], 0.0, delta=1e-9)
        self.assertAlmostEqual(P[1][1], 2.0, delta=1e-9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lqr.riccati_gain(A_DI, B_SI, [[1.0, 0.0], [0.0, 0.0]], 0.0)  # R <= 0
        with self.assertRaises(ValueError):
            lqr.riccati_gain(A_DI, B_SI, [[-1.0, 0.0], [0.0, 1.0]], 1.0)  # q1 < 0
        with self.assertRaises(ValueError):
            lqr.riccati_gain([[0.0, 1.0], [0.0, 1.0]], B_SI,
                             [[1.0, 0.0], [0.0, 1.0]], 1.0)  # a < 0
        with self.assertRaises(ValueError):
            lqr.riccati_gain(A_DI, [1.0, 0.0],
                             [[1.0, 0.0], [0.0, 1.0]], 1.0)  # B != [0, 1]
        with self.assertRaises(ValueError):
            lqr.riccati_gain(A_DI, B_SI,
                             [[1.0, 2.0], [0.0, 1.0]], 1.0)  # Q not diagonal
        with self.assertRaises(ValueError):
            lqr.riccati_gain(A_DI, B_SI,
                             [[1.0, 0.0], [0.0, 1.0]], "big")  # R non-numeric


class GainMatrixTest(unittest.TestCase):
    def test_textbook_gain(self):
        P = [[SQRT2, 1.0], [1.0, SQRT2]]
        K = lqr.gain_matrix(P, B_SI, 1.0)
        self.assertAlmostEqual(K[0], 1.0, delta=1e-9)
        self.assertAlmostEqual(K[1], SQRT2, delta=1e-9)

    def test_gain_scales_with_inverse_r(self):
        # K = R^-1 B' P: with r = 2 the entries halve
        K = lqr.gain_matrix([[3.0, 1.0], [1.0, 2.0]], B_SI, 2.0)
        self.assertAlmostEqual(K[0], 0.5, delta=1e-9)
        self.assertAlmostEqual(K[1], 1.0, delta=1e-9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lqr.gain_matrix([[1.0, 2.0], [3.0, 4.0]], B_SI, 1.0)  # not symmetric
        with self.assertRaises(ValueError):
            lqr.gain_matrix([[1.0, 0.0], [0.0, 1.0]], B_SI, -1.0)  # R <= 0
        with self.assertRaises(ValueError):
            lqr.gain_matrix([[1.0, 0.0], [0.0, 1.0]], [1.0, 0.0], 1.0)  # B wrong


class ClosedLoopStableTest(unittest.TestCase):
    def test_textbook_closed_loop_stable(self):
        res = lqr.closed_loop_stable(A_DI, B_SI, [1.0, SQRT2])
        self.assertTrue(res["stable"])
        self.assertEqual(len(res["poles"]), 2)
        for re_part, _im in res["poles"]:
            self.assertLess(re_part, 0.0)

    def test_pole_pair_values(self):
        # K = [1, sqrt(2)] on the double integrator:
        # poles = -sqrt(2)/2 +- j sqrt(2)/2
        res = lqr.closed_loop_stable(A_DI, B_SI, [1.0, SQRT2])
        re_vals = sorted(p[0] for p in res["poles"])
        im_vals = sorted(abs(p[1]) for p in res["poles"])
        self.assertAlmostEqual(re_vals[0], -SQRT2 / 2.0, delta=1e-9)
        self.assertAlmostEqual(im_vals[0], SQRT2 / 2.0, delta=1e-9)

    def test_unstable_open_loop(self):
        # zero gain on the double integrator: poles at the origin
        res = lqr.closed_loop_stable(A_DI, B_SI, [0.0, 0.0])
        self.assertFalse(res["stable"])

    def test_negative_gain_destabilizes(self):
        # K = [-1, 0]: A - B K = [[0, 1], [1, 0]] has det -1
        res = lqr.closed_loop_stable(A_DI, B_SI, [-1.0, 0.0])
        self.assertFalse(res["stable"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lqr.closed_loop_stable(A_DI, B_SI, [1.0])  # K wrong length
        with self.assertRaises(ValueError):
            lqr.closed_loop_stable([[1.0, 0.0], [0.0, 1.0]], B_SI,
                                   [1.0, 1.0])  # A not canonical
        with self.assertRaises(ValueError):
            lqr.closed_loop_stable(A_DI, B_SI, ["big", 1.0])  # K non-numeric


class CostWeightGuideTest(unittest.TestCase):
    def test_note_covers_trade(self):
        note = lqr.cost_weight_guide(1.0, 1.0, 1.0)
        self.assertIn("state error", note)
        self.assertIn("control effort", note)

    def test_state_error_dominated_regime(self):
        note = lqr.cost_weight_guide(100.0, 100.0, 1.0)
        self.assertIn("state-error dominated", note)

    def test_control_effort_dominated_regime(self):
        note = lqr.cost_weight_guide(1.0, 1.0, 100.0)
        self.assertIn("control-effort dominated", note)

    def test_balanced_regime(self):
        note = lqr.cost_weight_guide(5.0, 5.0, 2.0)
        self.assertIn("balanced", note)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            lqr.cost_weight_guide(-1.0, 1.0, 1.0)
        with self.assertRaises(ValueError):
            lqr.cost_weight_guide(1.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            lqr.cost_weight_guide(1.0, 1.0, "heavy")


if __name__ == "__main__":
    unittest.main(verbosity=2)
