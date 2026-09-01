#!/usr/bin/env python3
"""Gate 3 contract test: vehicle mass budget rollup and margin policy.

Exercises scripts/mass_budget_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - subsystem mass rollup,
phase growth allowance, growth allowance and contingency margin on the
margin-backed total, and the MTOW target verdict; invalid inputs raise
ValueError. Units: masses in kg, allowances as unitless fractions,
margin percent relative to the target mass.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mass_budget_logic as mbl  # noqa: E402


class RollupMassBudgetTest(unittest.TestCase):
    def test_analytic_rollup(self):
        # 5000 + 4000 + 3000 = 12000 kg
        self.assertEqual(
            mbl.rollup_mass_budget({"wing": 5000.0, "fuselage": 4000.0, "systems": 3000.0}),
            12000.0,
        )

    def test_single_subsystem_rollup(self):
        self.assertEqual(mbl.rollup_mass_budget({"payload": 2500.0}), 2500.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mbl.rollup_mass_budget({})
        with self.assertRaises(ValueError):
            mbl.rollup_mass_budget({"wing": 0})
        with self.assertRaises(ValueError):
            mbl.rollup_mass_budget({"wing": -5000.0})


class PhaseGrowthAllowanceTest(unittest.TestCase):
    def test_typical_phase_values(self):
        self.assertEqual(mbl.phase_growth_allowance("conceptual"), 0.10)
        self.assertEqual(mbl.phase_growth_allowance("preliminary"), 0.06)
        self.assertEqual(mbl.phase_growth_allowance("detailed"), 0.03)

    def test_case_insensitive_phase(self):
        self.assertEqual(mbl.phase_growth_allowance("CONCEPTUAL"), 0.10)

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            mbl.phase_growth_allowance("definition")


class ApplyGrowthAllowanceTest(unittest.TestCase):
    def test_analytic_growth(self):
        # 12000 * 1.10 = 13200 kg
        self.assertAlmostEqual(mbl.apply_growth_allowance(12000.0, 0.10), 13200.0, places=6)

    def test_zero_allowance_is_no_change(self):
        self.assertAlmostEqual(mbl.apply_growth_allowance(12000.0, 0.0), 12000.0, places=6)

    def test_consistency_with_phase(self):
        self.assertAlmostEqual(
            mbl.apply_growth_allowance(12000.0, mbl.phase_growth_allowance("conceptual")),
            13200.0,
            places=6,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mbl.apply_growth_allowance(0, 0.10)
        with self.assertRaises(ValueError):
            mbl.apply_growth_allowance(-12000.0, 0.10)
        with self.assertRaises(ValueError):
            mbl.apply_growth_allowance(12000.0, -0.01)


class ContingencyMassTest(unittest.TestCase):
    def test_analytic_contingency(self):
        # 13200 * 0.05 = 660 kg
        self.assertEqual(mbl.contingency_mass(13200.0, 0.05), 660.0)

    def test_zero_contingency_is_no_change(self):
        self.assertEqual(mbl.contingency_mass(13200.0, 0.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mbl.contingency_mass(0, 0.05)
        with self.assertRaises(ValueError):
            mbl.contingency_mass(13200.0, -0.05)


class MtowCheckTest(unittest.TestCase):
    def test_analytic_within_target(self):
        # 12000 * 1.10 * 1.05 = 13860; margin 15000 - 13860 = 1140;
        # margin percent 1140 / 15000 * 100 = 7.6
        result = mbl.mtow_check(12000.0, 15000.0, 0.10, 0.05)
        self.assertAlmostEqual(result["total_with_margin"], 13860.0, places=6)
        self.assertAlmostEqual(result["margin_kg"], 1140.0, places=6)
        self.assertAlmostEqual(result["margin_percent"], 7.6, places=6)
        self.assertEqual(result["status"], "within-target")

    def test_over_target_verdict(self):
        # 14000 * 1.10 * 1.05 = 16170 > 15000 -> over target
        result = mbl.mtow_check(14000.0, 15000.0, 0.10, 0.05)
        self.assertAlmostEqual(result["total_with_margin"], 16170.0, places=6)
        self.assertLess(result["margin_kg"], 0.0)
        self.assertEqual(result["status"], "over-target")

    def test_exact_target_is_within(self):
        # 12000 * 1.25 * 1.0 = 15000 exactly -> within target, zero margin
        result = mbl.mtow_check(12000.0, 15000.0, 0.25, 0.0)
        self.assertAlmostEqual(result["margin_kg"], 0.0, places=6)
        self.assertEqual(result["status"], "within-target")

    def test_consistency_with_growth_and_contingency(self):
        grown = mbl.apply_growth_allowance(12000.0, 0.10)
        cont = mbl.contingency_mass(grown, 0.05)
        result = mbl.mtow_check(12000.0, 15000.0, 0.10, 0.05)
        self.assertAlmostEqual(result["total_with_margin"], grown + cont, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mbl.mtow_check(0, 15000.0, 0.10, 0.05)
        with self.assertRaises(ValueError):
            mbl.mtow_check(12000.0, 0, 0.10, 0.05)
        with self.assertRaises(ValueError):
            mbl.mtow_check(12000.0, 15000.0, -0.10, 0.05)
        with self.assertRaises(ValueError):
            mbl.mtow_check(12000.0, 15000.0, 0.10, -0.05)


if __name__ == "__main__":
    unittest.main(verbosity=2)
