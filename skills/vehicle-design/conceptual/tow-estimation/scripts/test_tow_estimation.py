#!/usr/bin/env python3
"""Gate 3 contract test: conceptual takeoff gross weight estimation.

Exercises scripts/tow_estimation_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — fuel-fraction TOW
estimate, iteration convergence, and weight-breakdown checks;
invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tow_estimation_logic as tow  # noqa: E402


class TowEstimateTest(unittest.TestCase):
    def test_fuel_fraction_estimate(self):
        w0 = tow.tow_estimate(20000.0, 0.5, 0.3)
        self.assertAlmostEqual(w0, 100000.0)

    def test_fractions_must_leave_margin(self):
        with self.assertRaises(ValueError):
            tow.tow_estimate(20000.0, 0.6, 0.5)
        with self.assertRaises(ValueError):
            tow.tow_estimate(20000.0, 0.5, 0.5)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tow.tow_estimate(0.0, 0.5, 0.3)
        with self.assertRaises(ValueError):
            tow.tow_estimate(-100.0, 0.5, 0.3)
        with self.assertRaises(ValueError):
            tow.tow_estimate(20000.0, -0.1, 0.3)
        with self.assertRaises(ValueError):
            tow.tow_estimate(20000.0, 0.5, -0.1)


class TowConvergenceTest(unittest.TestCase):
    def test_converged_series(self):
        self.assertTrue(tow.tow_converged([99000.0, 99800.0, 99950.0, 99990.0],
                                          tol=100.0))

    def test_not_converged_series(self):
        self.assertFalse(tow.tow_converged([90000.0, 95000.0, 99000.0],
                                           tol=100.0))

    def test_short_series_raises(self):
        with self.assertRaises(ValueError):
            tow.tow_converged([99000.0], tol=100.0)

    def test_nonpositive_values_raise(self):
        with self.assertRaises(ValueError):
            tow.tow_converged([99000.0, 0.0], tol=100.0)


class WeightBreakdownTest(unittest.TestCase):
    def test_balanced_breakdown(self):
        self.assertTrue(tow.weight_breakdown_ok(50000.0, 30000.0, 20000.0,
                                                100000.0))

    def test_unbalanced_breakdown(self):
        self.assertFalse(tow.weight_breakdown_ok(50000.0, 30000.0, 20000.0,
                                                 120000.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tow.weight_breakdown_ok(-1.0, 30000.0, 20000.0, 100000.0)
        with self.assertRaises(ValueError):
            tow.weight_breakdown_ok(50000.0, 30000.0, 20000.0, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
