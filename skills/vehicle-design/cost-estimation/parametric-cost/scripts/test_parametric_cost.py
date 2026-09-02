#!/usr/bin/env python3
"""Gate 3 contract test: parametric cost estimating relationships.

Exercises scripts/parametric_cost_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - learning curve exponent,
unit cost, cumulative learning factor, weight-based development cost,
and total program cost rollup; invalid inputs raise ValueError. Units:
costs in program currency units, airframe mass in kg, learning curve
lc dimensionless (0.85 typical).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import parametric_cost_logic as pcl  # noqa: E402


class LearningCurveExponentTest(unittest.TestCase):
    def test_analytic_exponent_085(self):
        # ln(0.85)/ln(2) = -0.162519/0.693147 = -0.234465
        self.assertAlmostEqual(pcl.learning_curve_exponent(0.85), -0.234465, places=6)

    def test_second_unit_is_lc_times_first(self):
        # c2 = 1000 * 2**-0.234465 = 1000 * 0.85 = 850.0 (defining property)
        self.assertAlmostEqual(pcl.unit_cost(1000.0, 2, 0.85), 850.0, places=6)

    def test_invalid_lc_raises(self):
        for bad in (0, 1, -0.5, 1.5):
            with self.assertRaises(ValueError):
                pcl.learning_curve_exponent(bad)


class UnitCostTest(unittest.TestCase):
    def test_analytic_unit_cost(self):
        # c4 = 1000 * 4**-0.234465 = 1000 * 0.85**2 = 722.5
        self.assertAlmostEqual(pcl.unit_cost(1000.0, 4, 0.85), 722.5, places=3)
        self.assertAlmostEqual(pcl.unit_cost(1000.0, 1, 0.85), 1000.0, places=6)

    def test_unit_cost_decreases_with_unit_number(self):
        self.assertLess(
            pcl.unit_cost(1000.0, 4, 0.85), pcl.unit_cost(1000.0, 2, 0.85)
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pcl.unit_cost(0, 2, 0.85)
        with self.assertRaises(ValueError):
            pcl.unit_cost(-1000.0, 2, 0.85)
        with self.assertRaises(ValueError):
            pcl.unit_cost(1000.0, 0, 0.85)
        with self.assertRaises(ValueError):
            pcl.unit_cost(1000.0, 2, 1.0)


class CumulativeLearningFactorTest(unittest.TestCase):
    def test_analytic_factor(self):
        # n=2, lc=0.85: s=-0.234465, F = 2**0.765535/0.765535 = 2.220670
        self.assertAlmostEqual(
            pcl.cumulative_learning_factor(2, 0.85), 2.220670, places=6
        )
        # n=4: F = 4**0.765535/0.765535 = 3.775139
        self.assertAlmostEqual(
            pcl.cumulative_learning_factor(4, 0.85), 3.775139, places=6
        )

    def test_factor_grows_with_n(self):
        self.assertGreater(
            pcl.cumulative_learning_factor(4, 0.85),
            pcl.cumulative_learning_factor(2, 0.85),
        )

    def test_invalid_n_raises(self):
        with self.assertRaises(ValueError):
            pcl.cumulative_learning_factor(0, 0.85)
        with self.assertRaises(ValueError):
            pcl.cumulative_learning_factor(-3, 0.85)


class DevelopmentCostTest(unittest.TestCase):
    def test_analytic_cer(self):
        # 100000 * 10000**0.6 = 100000 * 251.188643 = 25118864.315
        self.assertAlmostEqual(
            pcl.development_cost(100000.0, 10000.0, 0.6), 25118864.315, places=3
        )

    def test_larger_mass_raises_cost(self):
        self.assertGreater(
            pcl.development_cost(100000.0, 20000.0, 0.6),
            pcl.development_cost(100000.0, 10000.0, 0.6),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pcl.development_cost(0, 10000.0, 0.6)
        with self.assertRaises(ValueError):
            pcl.development_cost(100000.0, 0, 0.6)
        with self.assertRaises(ValueError):
            pcl.development_cost(100000.0, 10000.0, 0)


class TotalProgramCostTest(unittest.TestCase):
    def test_analytic_rollup(self):
        result = pcl.total_program_cost(1000.0, 4, 0.85, 25118864.315)
        self.assertAlmostEqual(result["unit_n"], 722.5, places=3)
        self.assertAlmostEqual(result["cumulative_factor"], 3.775139, places=6)
        self.assertAlmostEqual(result["production_total"], 3775.139, places=3)
        self.assertAlmostEqual(result["program_total"], 25122639.454, places=3)

    def test_program_total_adds_development(self):
        base = pcl.total_program_cost(1000.0, 2, 0.85, 0.0)
        with_dev = pcl.total_program_cost(1000.0, 2, 0.85, 50000.0)
        self.assertAlmostEqual(
            with_dev["program_total"], base["program_total"] + 50000.0, places=6
        )

    def test_consistency_with_piecewise_calls(self):
        result = pcl.total_program_cost(1000.0, 4, 0.85, 25118864.315)
        self.assertAlmostEqual(
            result["unit_n"], pcl.unit_cost(1000.0, 4, 0.85), places=9
        )
        self.assertAlmostEqual(
            result["production_total"],
            1000.0 * pcl.cumulative_learning_factor(4, 0.85),
            places=9,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pcl.total_program_cost(1000.0, 0, 0.85, 0.0)
        with self.assertRaises(ValueError):
            pcl.total_program_cost(1000.0, 2, 0.0, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
