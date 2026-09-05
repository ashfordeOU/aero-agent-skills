"""Contract test for boundary-layer-separation (Thwaites + Stratford).

Deterministic, offline, stdlib only. Run with:

    python3 scripts/test_boundary_layer_separation.py

Covers the worked-example anchors (linear deceleration U = 30(1 - x)
with nu = 1.5e-5 m2/s over 400001 stations: separation near 0.1231 m
at U = 26.31 m/s; Stratford crossing at station 8 of the C_p = 0.4 x^2
recovery with S = 0.3505), the magnitude bounds from the engineering
spec, the closed-form Thwaites identity for a linear deceleration, the
validation list (ValueError rejections, determinism), and the
identity checks for favorable, mild and steep recoveries.

The test follows the SKILL.md workflow: step 2 (the thwaites_lambda
traverse), step 3 (the laminar separation station), step 5 (the
stratford separation station) and step 6 (the separation margin) are
each exercised with their own test methods, so the module outputs gate
the workflow handoff exactly as documented.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import boundary_layer_separation_logic as bls  # noqa: E402

NU = 1.5e-5
U0 = 30.0
L = 1.0
N_LIN = 400001
DX_LIN = L / (N_LIN - 1)  # 2.5e-6 m


def linear_decel_grid(n=N_LIN):
    xs = [i * (L / (n - 1)) for i in range(n)]
    us = [U0 * (1.0 - x / L) for x in xs]
    return xs, us


def cp_grid(a, n=10):
    xs = [i / 10.0 for i in range(n)]
    cps = [a * x * x for x in xs]
    return xs, cps


def analytic_linear_lambda(x):
    """Closed-form Thwaites lambda for U = U0(1 - x/L), theta(0) = 0."""
    t = 1.0 - x / L
    return -0.075 * (1.0 - t ** 6) / t ** 6


class LaminarThwaitesTest(unittest.TestCase):
    """Thwaites traverse and the -0.09 laminar separation criterion."""

    @classmethod
    def setUpClass(cls):
        cls.xs, cls.us = linear_decel_grid()
        cls.lam = bls.thwaites_lambda(cls.xs, cls.us, NU)
        cls.sep = bls.laminar_separation_station(cls.xs, cls.us, NU)

    def test_separation_x_within_one_percent_of_anchor(self):
        self.assertIsNotNone(self.sep)
        x = self.sep[1]
        self.assertAlmostEqual(x / 0.1231, 1.0, delta=0.01)
        # separation falls strictly inside the body
        self.assertGreater(x, 0.0)
        self.assertLess(x, L)

    def test_separation_tuple_index_matches_x(self):
        idx, x = self.sep
        self.assertEqual(x, self.xs[idx])

    def test_edge_velocity_at_separation_anchor(self):
        idx = self.sep[0]
        self.assertAlmostEqual(self.us[idx] / 26.31, 1.0, delta=0.01)

    def test_first_crossing_flag(self):
        idx = self.sep[0]
        self.assertGreater(self.lam[idx - 1], bls.THWAITES_LAMBDA_SEP)
        self.assertLessEqual(self.lam[idx], bls.THWAITES_LAMBDA_SEP)

    def test_lambda_monotone_decreasing(self):
        idx = self.sep[0]
        for i in range(1, idx + 1):
            self.assertLessEqual(self.lam[i], self.lam[i - 1])

    def test_lambda_negative_at_end(self):
        idx = int(0.9 / DX_LIN)
        self.assertLess(self.lam[idx], -100.0)

    def test_lambda_analytic_closed_form(self):
        idx = int(0.05 / DX_LIN)
        self.assertAlmostEqual(self.lam[idx],
                               analytic_linear_lambda(0.05), delta=1e-4)

    def test_lambda_list_length_matches_stations(self):
        self.assertEqual(len(self.lam), len(self.xs))

    def test_accelerating_flow_no_separation(self):
        n = 2001
        xs = [i * (L / (n - 1)) for i in range(n)]
        us = [U0 * (1.0 + 0.2 * x) for x in xs]
        lam = bls.thwaites_lambda(xs, us, NU)
        self.assertIsNone(bls.laminar_separation_station(xs, us, NU))
        for value in lam:
            self.assertGreaterEqual(value, -1e-12)

    def test_constant_velocity_lambda_zero(self):
        n = 101
        xs = [i * (L / (n - 1)) for i in range(n)]
        us = [U0] * n
        lam = bls.thwaites_lambda(xs, us, NU)
        for value in lam:
            self.assertAlmostEqual(value, 0.0, places=10)
        self.assertIsNone(bls.laminar_separation_station(xs, us, NU))

    def test_mild_deceleration_no_separation(self):
        n = 2001
        xs = [i * (L / (n - 1)) for i in range(n)]
        us = [U0 * (1.0 - 0.05 * x / L) for x in xs]
        lam = bls.thwaites_lambda(xs, us, NU)
        self.assertIsNone(bls.laminar_separation_station(xs, us, NU))
        self.assertGreater(lam[-1], bls.THWAITES_LAMBDA_SEP)

    def test_stagnation_start_accelerating_no_separation(self):
        n = 101
        xs = [i * (L / (n - 1)) for i in range(n)]
        us = [30.0 * x for x in xs]  # U = 0 at the x = 0 stagnation point
        lam = bls.thwaites_lambda(xs, us, NU)
        self.assertEqual(len(lam), n)
        self.assertIsNone(bls.laminar_separation_station(xs, us, NU))

    def test_valueerror_length_mismatch(self):
        xs = [0.0, 0.5, 1.0]
        us = [30.0, 20.0]
        with self.assertRaises(ValueError):
            bls.thwaites_lambda(xs, us, NU)

    def test_valueerror_nu_nonpositive(self):
        xs = [0.0, 1.0]
        us = [30.0, 20.0]
        for bad_nu in (0.0, -1.0):
            with self.assertRaises(ValueError):
                bls.thwaites_lambda(xs, us, bad_nu)

    def test_valueerror_negative_velocity(self):
        xs = [0.0, 1.0]
        us = [30.0, -5.0]
        with self.assertRaises(ValueError):
            bls.thwaites_lambda(xs, us, NU)

    def test_valueerror_empty_lists(self):
        with self.assertRaises(ValueError):
            bls.thwaites_lambda([], [], NU)
        with self.assertRaises(ValueError):
            bls.laminar_separation_station([0.0, 1.0], [], NU)

    def test_valueerror_all_zero_velocity(self):
        xs = [0.0, 0.5, 1.0]
        us = [0.0, 0.0, 0.0]
        with self.assertRaises(ValueError):
            bls.thwaites_lambda(xs, us, NU)

    def test_valueerror_non_increasing_stations(self):
        xs = [0.0, 0.5, 0.4, 1.0]
        us = [30.0, 25.0, 22.0, 18.0]
        with self.assertRaises(ValueError):
            bls.thwaites_lambda(xs, us, NU)

    def test_determinism(self):
        xs, us = linear_decel_grid(n=2001)
        first = bls.thwaites_lambda(xs, us, NU)
        second = bls.thwaites_lambda(xs, us, NU)
        self.assertEqual(first, second)


class StratfordTest(unittest.TestCase):
    """Stratford pressure-recovery criterion and separation margin."""

    def test_crossing_anchor_index8_x08(self):
        xs, cps = cp_grid(0.4)
        self.assertEqual(bls.stratford_separation_station(xs, cps),
                         (8, 0.8))

    def test_s_parameter_at_anchor_crossing(self):
        xs, cps = cp_grid(0.4)
        s_vals = bls.stratford_parameter(xs, cps)
        self.assertAlmostEqual(s_vals[8], 0.3505, delta=0.002)

    def test_margin_positive_before_crossing(self):
        xs, cps = cp_grid(0.4)
        margin = bls.separation_margin(xs, cps)
        self.assertGreater(margin, 0.0)
        self.assertAlmostEqual(margin, 0.35 - 0.267103, delta=2e-3)

    def test_worked_example_recovery_shape(self):
        xs, cps = cp_grid(0.4)
        s_vals = bls.stratford_parameter(xs, cps)
        for i in range(2, 9):
            self.assertLess(s_vals[i - 1], s_vals[i])

    def test_mild_recovery_no_crossing_none(self):
        xs, cps = cp_grid(0.2)
        self.assertIsNone(bls.stratford_separation_station(xs, cps))

    def test_mild_recovery_positive_margin(self):
        xs, cps = cp_grid(0.2)
        margin = bls.separation_margin(xs, cps)
        self.assertGreater(margin, 0.0)
        self.assertAlmostEqual(margin, 0.12735, delta=2e-3)

    def test_steep_recovery_crossing_exists(self):
        xs, cps = cp_grid(0.6)
        self.assertEqual(bls.stratford_separation_station(xs, cps),
                         (7, 0.7))

    def test_steep_recovery_first_crossing_flag(self):
        xs, cps = cp_grid(0.6)
        s_vals = bls.stratford_parameter(xs, cps)
        for i in range(7):
            if s_vals[i] is not None:
                self.assertLess(s_vals[i], bls.STRATFORD_SEP)

    def test_steep_recovery_pre_crossing_margin_positive(self):
        xs, cps = cp_grid(0.6)
        margin = bls.separation_margin(xs, cps)
        self.assertGreater(margin, 0.0)
        self.assertAlmostEqual(margin, 0.05753, delta=2e-3)

    def test_falling_cp_no_recovery(self):
        n = 10
        xs = [0.1 * i for i in range(n)]
        cps = [0.4 * (1.0 - x) ** 2 for x in xs]  # pressure falling
        self.assertIsNone(bls.stratford_separation_station(xs, cps))
        self.assertEqual(bls.separation_margin(xs, cps), 0.35)

    def test_negative_cp_no_crossing(self):
        xs, cps = cp_grid(-0.4)
        self.assertIsNone(bls.stratford_separation_station(xs, cps))
        self.assertEqual(bls.separation_margin(xs, cps), 0.35)

    def test_constant_cp_no_recovery(self):
        xs = [0.1 * i for i in range(10)]
        cps = [0.3] * 10
        self.assertIsNone(bls.stratford_separation_station(xs, cps))
        self.assertEqual(bls.separation_margin(xs, cps), 0.35)

    def test_single_station(self):
        self.assertIsNone(bls.stratford_separation_station([0.5], [0.2]))
        self.assertEqual(bls.separation_margin([0.5], [0.2]), 0.35)

    def test_parameter_list_length_and_types(self):
        xs, cps = cp_grid(0.4)
        s_vals = bls.stratford_parameter(xs, cps)
        self.assertEqual(len(s_vals), len(xs))
        self.assertIsNone(s_vals[0])  # C_p = 0 at x = 0: no recovery there
        for i in range(1, len(s_vals)):
            self.assertIsInstance(s_vals[i], float)

    def test_valueerror_length_mismatch_and_empty(self):
        xs = [0.0, 0.5, 1.0]
        cps = [0.1, 0.2]
        with self.assertRaises(ValueError):
            bls.stratford_separation_station(xs, cps)
        with self.assertRaises(ValueError):
            bls.stratford_separation_station([], [])
        with self.assertRaises(ValueError):
            bls.separation_margin([0.1, 0.2], [])

    def test_determinism(self):
        xs, cps = cp_grid(0.4)
        self.assertEqual(bls.stratford_parameter(xs, cps),
                         bls.stratford_parameter(xs, cps))
        self.assertEqual(bls.separation_margin(xs, cps),
                         bls.separation_margin(xs, cps))


if __name__ == "__main__":
    unittest.main()
