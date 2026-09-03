"""Contract tests for the control-allocation logic module.

Deterministic, offline, stdlib only. Run with:
    python3 test_control_allocation.py
Exit code 0 means every contract assertion passed.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from control_allocation_logic import (  # noqa: E402
    allocation_verdict,
    clip_to_limits,
    daisy_chain_alloc,
    damped_least_squares_alloc,
    direct_alloc,
    pseudoinverse_alloc,
    rate_limit,
    redistribute_pseudoinverse,
    weighted_alloc,
)

ROLL_B = [[1.0, 1.0]]
ROLL_M = [0.8]

B3 = [
    [1.0, 0.5, 0.0, 0.0, 0.0, 0.0],
    [0.0, 0.0, 1.0, 0.5, 0.0, 0.0],
    [0.0, 0.0, 0.0, 0.0, 1.0, 0.5],
]
M3 = [0.9, -0.6, 0.3]


def matvec(b, u):
    return [sum(b[i][k] * u[k] for k in range(len(u))) for i in range(len(b))]


def norm(v):
    return math.sqrt(sum(x * x for x in v))


class TestPseudoinverse(unittest.TestCase):
    def test_pseudoinverse_two_effector_roll_round_trip(self):
        u = pseudoinverse_alloc(ROLL_B, ROLL_M)
        self.assertAlmostEqual(u[0], 0.4, places=9)
        self.assertAlmostEqual(u[1], 0.4, places=9)
        achieved = matvec(ROLL_B, u)
        self.assertAlmostEqual(achieved[0], ROLL_M[0], places=9)

    def test_pseudoinverse_two_effector_minimum_norm(self):
        u = pseudoinverse_alloc(ROLL_B, ROLL_M)
        alt = [1.0, -0.2]  # feasible: 1.0 - 0.2 = 0.8
        self.assertAlmostEqual(matvec(ROLL_B, alt)[0], ROLL_M[0], places=9)
        self.assertLess(norm(u), norm(alt))

    def test_pseudoinverse_three_axis_six_effector_split(self):
        u = pseudoinverse_alloc(B3, M3)
        expected = [0.72, 0.36, -0.48, -0.24, 0.24, 0.12]
        for got, want in zip(u, expected):
            self.assertAlmostEqual(got, want, places=9)

    def test_pseudoinverse_three_axis_round_trip(self):
        u = pseudoinverse_alloc(B3, M3)
        achieved = matvec(B3, u)
        for got, want in zip(achieved, M3):
            self.assertAlmostEqual(got, want, places=9)

    def test_pseudoinverse_three_axis_minimum_norm(self):
        u = pseudoinverse_alloc(B3, M3)
        null_dir = [0.5, -1.0, 0.0, 0.0, 0.0, 0.0]  # B nullspace direction
        alt = [a + 0.1 * d for a, d in zip(u, null_dir)]
        achieved = matvec(B3, alt)
        for got, want in zip(achieved, M3):
            self.assertAlmostEqual(got, want, places=9)
        self.assertLess(norm(u), norm(alt))

    def test_pseudoinverse_singular_gram_regularized(self):
        b = [[1.0, 1.0], [1.0, 1.0]]
        m = [0.5, 0.5]
        u = pseudoinverse_alloc(b, m)
        self.assertAlmostEqual(u[0], 0.25, places=9)
        self.assertAlmostEqual(u[1], 0.25, places=9)
        for got, want in zip(matvec(b, u), m):
            self.assertAlmostEqual(got, want, places=9)


class TestDampedLeastSquares(unittest.TestCase):
    def test_damped_value_and_zero_lambda_delegation(self):
        u = damped_least_squares_alloc(ROLL_B, ROLL_M, 0.05)
        self.assertAlmostEqual(u[0], 0.390243902439, places=9)
        self.assertAlmostEqual(u[1], 0.390243902439, places=9)
        u_zero = damped_least_squares_alloc(ROLL_B, ROLL_M, 0.0)
        self.assertAlmostEqual(u_zero[0], 0.4, places=9)
        self.assertAlmostEqual(u_zero[1], 0.4, places=9)

    def test_damped_singular_gram_stays_finite(self):
        b = [[1.0, 1.0], [1.0, 1.0]]
        u = damped_least_squares_alloc(b, [0.5, 0.5], 0.1)
        for value in u:
            self.assertTrue(math.isfinite(value))

    def test_damped_rejects_negative_lambda(self):
        with self.assertRaises(ValueError):
            damped_least_squares_alloc(ROLL_B, ROLL_M, -0.1)


class TestWeighted(unittest.TestCase):
    def test_weighted_equal_weights_match_pseudoinverse(self):
        u = weighted_alloc(ROLL_B, [1.0, 1.0], ROLL_M)
        self.assertAlmostEqual(u[0], 0.4, places=9)
        self.assertAlmostEqual(u[1], 0.4, places=9)

    def test_weighted_pushes_command_to_lower_cost_effector(self):
        u = weighted_alloc(ROLL_B, [1.0, 4.0], ROLL_M)
        self.assertAlmostEqual(u[0], 0.64, places=9)
        self.assertAlmostEqual(u[1], 0.16, places=9)
        achieved = matvec(ROLL_B, u)
        self.assertAlmostEqual(achieved[0], ROLL_M[0], places=9)
        u_mirror = weighted_alloc(ROLL_B, [4.0, 1.0], ROLL_M)
        self.assertAlmostEqual(u_mirror[0], 0.16, places=9)
        self.assertAlmostEqual(u_mirror[1], 0.64, places=9)

    def test_weighted_rejects_nonpositive_and_misaligned_weights(self):
        with self.assertRaises(ValueError):
            weighted_alloc(ROLL_B, [1.0, 0.0], ROLL_M)
        with self.assertRaises(ValueError):
            weighted_alloc(ROLL_B, [-1.0, 2.0], ROLL_M)
        with self.assertRaises(ValueError):
            weighted_alloc(ROLL_B, [1.0], ROLL_M)


class TestClipping(unittest.TestCase):
    def test_clip_unchanged_within_limits(self):
        u, mask = clip_to_limits([0.2, 0.4], [0.0, 0.0], [0.5, 0.6])
        self.assertEqual(u, [0.2, 0.4])
        self.assertEqual(mask, [False, False])

    def test_clip_upper_and_lower_saturation_masks(self):
        u, mask = clip_to_limits([0.4, 0.4], [0.0, 0.0], [0.3, 0.6])
        self.assertAlmostEqual(u[0], 0.3, places=9)
        self.assertAlmostEqual(u[1], 0.4, places=9)
        self.assertEqual(mask, [True, False])
        u_lo, mask_lo = clip_to_limits([-0.2, 0.1], [-0.1, 0.0], [0.3, 0.6])
        self.assertAlmostEqual(u_lo[0], -0.1, places=9)
        self.assertEqual(mask_lo, [True, False])

    def test_clip_rejects_inverted_limits(self):
        with self.assertRaises(ValueError):
            clip_to_limits([0.1, 0.1], [0.3, 0.0], [0.2, 0.6])


class TestRedistribute(unittest.TestCase):
    def test_redistributed_pseudoinverse_worked_example(self):
        u = redistribute_pseudoinverse(ROLL_B, ROLL_M, [0.0, 0.0], [0.3, 0.6])
        self.assertAlmostEqual(u[0], 0.3, places=9)
        self.assertAlmostEqual(u[1], 0.5, places=9)
        verdict = allocation_verdict(ROLL_B, ROLL_M, u, [0.0, 0.0], [0.3, 0.6])
        self.assertAlmostEqual(verdict["error_norm"], 0.0, places=9)
        self.assertEqual(verdict["saturated_effectors"], [0])

    def test_redistribute_no_saturation_returns_pseudoinverse(self):
        u = redistribute_pseudoinverse(ROLL_B, ROLL_M, [-1.0, -1.0], [1.0, 1.0])
        self.assertAlmostEqual(u[0], 0.4, places=9)
        self.assertAlmostEqual(u[1], 0.4, places=9)

    def test_redistribute_full_saturation_keeps_residual(self):
        u = redistribute_pseudoinverse(ROLL_B, [1.2], [0.0, 0.0], [0.5, 0.5])
        self.assertAlmostEqual(u[0], 0.5, places=9)
        self.assertAlmostEqual(u[1], 0.5, places=9)
        achieved = matvec(ROLL_B, u)[0]
        self.assertAlmostEqual(achieved, 1.0, places=9)
        self.assertAlmostEqual(1.2 - achieved, 0.2, places=9)

    def test_redistribute_respects_max_iter_bound(self):
        u = redistribute_pseudoinverse(ROLL_B, ROLL_M, [0.0, 0.0], [0.3, 0.6], 0)
        self.assertAlmostEqual(u[0], 0.3, places=9)
        self.assertAlmostEqual(u[1], 0.4, places=9)

    def test_redistribute_rejects_inverted_limits(self):
        with self.assertRaises(ValueError):
            redistribute_pseudoinverse(ROLL_B, ROLL_M, [0.3, 0.0], [0.2, 0.6])


class TestRateLimit(unittest.TestCase):
    def test_rate_limit_first_and_second_step(self):
        first = rate_limit([0.4, 0.4], [0.0, 0.0], 0.1, [2.0, 3.0])
        self.assertAlmostEqual(first[0], 0.2, places=9)
        self.assertAlmostEqual(first[1], 0.3, places=9)
        second = rate_limit([0.4, 0.4], first, 0.1, [2.0, 3.0])
        self.assertAlmostEqual(second[0], 0.4, places=9)
        self.assertAlmostEqual(second[1], 0.4, places=9)

    def test_rate_limit_unchanged_when_within_rate(self):
        out = rate_limit([0.2, 0.3], [0.0, 0.0], 0.1, 5.0)
        self.assertAlmostEqual(out[0], 0.2, places=9)
        self.assertAlmostEqual(out[1], 0.3, places=9)

    def test_rate_limit_symmetric_reversal(self):
        out = rate_limit([0.0, 0.0], [0.4, 0.4], 0.05, 2.0)
        self.assertAlmostEqual(out[0], 0.3, places=9)
        self.assertAlmostEqual(out[1], 0.3, places=9)

    def test_rate_limit_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            rate_limit([0.4, 0.4], [0.0, 0.0], 0.0, 2.0)
        with self.assertRaises(ValueError):
            rate_limit([0.4, 0.4], [0.0, 0.0], -0.1, 2.0)
        with self.assertRaises(ValueError):
            rate_limit([0.4, 0.4], [0.0, 0.0], 0.1, -2.0)
        with self.assertRaises(ValueError):
            rate_limit([0.4, 0.4], [0.0, 0.0], 0.1, [2.0, -1.0])
        with self.assertRaises(ValueError):
            rate_limit([0.4, 0.4], [0.0, 0.0], 0.1, [2.0, 3.0, 4.0])
        with self.assertRaises(ValueError):
            rate_limit([0.4, 0.4], [0.0], 0.1, 2.0)


class TestDaisyChain(unittest.TestCase):
    def test_daisy_chain_worked_example(self):
        u_p, u_s = daisy_chain_alloc(
            [[1.0, 1.0]], [[2.0]], [1.0], [0.0, 0.0], [0.3, 0.3], [-1.0], [1.0]
        )
        self.assertAlmostEqual(u_p[0], 0.3, places=9)
        self.assertAlmostEqual(u_p[1], 0.3, places=9)
        self.assertAlmostEqual(u_s[0], 0.2, places=9)
        total = sum(u_p) + 2.0 * u_s[0]
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_daisy_chain_secondary_saturation_leaves_error(self):
        u_p, u_s = daisy_chain_alloc(
            [[1.0, 1.0]], [[1.0]], [1.0], [0.0, 0.0], [0.3, 0.3], [-0.1], [0.1]
        )
        self.assertAlmostEqual(u_p[0], 0.3, places=9)
        self.assertAlmostEqual(u_s[0], 0.1, places=9)
        achieved = sum(u_p) + u_s[0]
        self.assertAlmostEqual(achieved, 0.7, places=9)

    def test_daisy_chain_primary_handles_small_command(self):
        u_p, u_s = daisy_chain_alloc(
            [[1.0, 1.0]], [[2.0]], [0.4], [0.0, 0.0], [0.3, 0.6], [-1.0], [1.0]
        )
        self.assertAlmostEqual(u_p[0], 0.2, places=9)
        self.assertAlmostEqual(u_p[1], 0.2, places=9)
        self.assertAlmostEqual(u_s[0], 0.0, places=9)


class TestDirect(unittest.TestCase):
    def test_direct_allocation_full_command_inside_box(self):
        u = direct_alloc(ROLL_B, [0.6], [0.0, 0.0], [0.5, 0.5])
        self.assertAlmostEqual(u[0], 0.3, places=9)
        self.assertAlmostEqual(u[1], 0.3, places=9)
        achieved = matvec(ROLL_B, u)[0]
        self.assertAlmostEqual(achieved, 0.6, places=9)

    def test_direct_allocation_box_bound_saturation(self):
        u = direct_alloc(ROLL_B, [0.8], [0.0, 0.0], [0.3, 0.6])
        self.assertAlmostEqual(u[0], 0.3, places=9)
        self.assertAlmostEqual(u[1], 0.3, places=9)
        verdict = allocation_verdict(ROLL_B, [0.8], u, [0.0, 0.0], [0.3, 0.6])
        self.assertAlmostEqual(verdict["error_norm"], 0.2, places=9)


class TestVerdict(unittest.TestCase):
    def test_verdict_reports_saturation_and_achieved_moment(self):
        verdict = allocation_verdict(
            ROLL_B, ROLL_M, [0.3, 0.5], [0.0, 0.0], [0.3, 0.6]
        )
        self.assertEqual(verdict["saturated_effectors"], [0])
        self.assertAlmostEqual(verdict["achieved_moment"][0], 0.8, places=9)
        self.assertAlmostEqual(verdict["error_norm"], 0.0, places=9)

    def test_verdict_no_saturation_with_wide_limits(self):
        verdict = allocation_verdict(ROLL_B, ROLL_M, [0.4, 0.4], [-1.0, -1.0], [1.0, 1.0])
        self.assertEqual(verdict["saturated_effectors"], [])
        self.assertAlmostEqual(verdict["error_norm"], 0.0, places=9)

    def test_verdict_error_norm_when_saturated(self):
        verdict = allocation_verdict(
            ROLL_B, ROLL_M, [0.3, 0.3], [0.0, 0.0], [0.3, 0.6]
        )
        self.assertAlmostEqual(verdict["error_norm"], 0.2, places=9)


class TestValidation(unittest.TestCase):
    def test_dimension_mismatch_raises(self):
        with self.assertRaises(ValueError):
            pseudoinverse_alloc(B3, [0.5, 0.5])

    def test_nonfinite_input_raises(self):
        with self.assertRaises(ValueError):
            pseudoinverse_alloc(ROLL_B, [float("nan")])
        with self.assertRaises(ValueError):
            pseudoinverse_alloc([[1.0, float("inf")]], ROLL_M)

    def test_underactuated_and_empty_systems_raise(self):
        with self.assertRaises(ValueError):
            pseudoinverse_alloc([[1.0], [1.0]], [0.5, 0.5])
        with self.assertRaises(ValueError):
            pseudoinverse_alloc([], [])
        with self.assertRaises(ValueError):
            pseudoinverse_alloc([[1.0, 1.0]], [])


if __name__ == "__main__":
    unittest.main(verbosity=1)
