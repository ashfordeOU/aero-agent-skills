#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.6.6 budget consolidation
and margin policy.

Exercises scripts/e10_budget_margin_policy_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a contribution's
predicted value is cbe * (1 + maturity_margin_pct/100); consolidation
sums predicted values across contributors; the system contingency margin
is applied on top of the consolidated predicted total before checking
against the allocated value; a category is margin-policy compliant only
when within budget AND its remaining margin percentage meets the
phase-appropriate minimum; invalid inputs (negative values, empty
strings/collections, non-positive allocation, unknown phase) raise
ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_budget_margin_policy_logic as bm  # noqa: E402


class ContributionTest(unittest.TestCase):
    def test_predicted_value(self):
        c = bm.contribution("EQUIP-1", 10.0, 20)
        self.assertEqual(c["item_id"], "EQUIP-1")
        self.assertEqual(c["cbe"], 10.0)
        self.assertEqual(c["maturity_margin_pct"], 20)
        self.assertAlmostEqual(c["predicted"], 12.0)

    def test_zero_margin(self):
        c = bm.contribution("EQUIP-2", 5.0, 0)
        self.assertAlmostEqual(c["predicted"], 5.0)

    def test_empty_item_id_raises(self):
        with self.assertRaises(ValueError):
            bm.contribution("", 1.0, 10)

    def test_negative_cbe_raises(self):
        with self.assertRaises(ValueError):
            bm.contribution("EQUIP-1", -1.0, 10)

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            bm.contribution("EQUIP-1", 1.0, -5)


class ConsolidateCategoryBudgetTest(unittest.TestCase):
    def test_sums_predicted_values(self):
        c1 = bm.contribution("EQUIP-1", 10.0, 20)
        c2 = bm.contribution("EQUIP-2", 5.0, 10)
        entry = bm.consolidate_category_budget("mass", [c1, c2])
        self.assertEqual(entry["category"], "mass")
        self.assertAlmostEqual(entry["cbe_total"], 15.0)
        self.assertAlmostEqual(entry["predicted_total"], 12.0 + 5.5)
        self.assertEqual(entry["contributions"], [c1, c2])

    def test_empty_category_raises(self):
        c1 = bm.contribution("EQUIP-1", 10.0, 20)
        with self.assertRaises(ValueError):
            bm.consolidate_category_budget("", [c1])

    def test_empty_contributions_raises(self):
        with self.assertRaises(ValueError):
            bm.consolidate_category_budget("mass", [])


class ApplySystemMarginTest(unittest.TestCase):
    def test_applies_margin_on_top_of_predicted_total(self):
        c1 = bm.contribution("EQUIP-1", 100.0, 0)
        entry = bm.consolidate_category_budget("power", [c1])
        margined = bm.apply_system_margin(entry, 10)
        self.assertAlmostEqual(margined["margined_total"], 110.0)
        self.assertEqual(margined["system_margin_pct"], 10)
        self.assertNotIn("margined_total", entry)

    def test_negative_system_margin_raises(self):
        c1 = bm.contribution("EQUIP-1", 100.0, 0)
        entry = bm.consolidate_category_budget("power", [c1])
        with self.assertRaises(ValueError):
            bm.apply_system_margin(entry, -1)


class EvaluateAgainstAllocationTest(unittest.TestCase):
    def _margined_entry(self, cbe, margin_pct, system_margin_pct):
        c1 = bm.contribution("EQUIP-1", cbe, margin_pct)
        consolidated = bm.consolidate_category_budget("mass", [c1])
        return bm.apply_system_margin(consolidated, system_margin_pct)

    def test_within_budget(self):
        entry = self._margined_entry(100.0, 0, 0)
        checked = bm.evaluate_against_allocation(entry, 150.0)
        self.assertEqual(checked["status"], "within_budget")
        self.assertAlmostEqual(checked["margin_remaining"], 50.0)
        self.assertAlmostEqual(checked["margin_pct_remaining"], 33.333333, places=5)

    def test_exceeded(self):
        entry = self._margined_entry(100.0, 0, 0)
        checked = bm.evaluate_against_allocation(entry, 80.0)
        self.assertEqual(checked["status"], "exceeded")
        self.assertAlmostEqual(checked["margin_remaining"], -20.0)

    def test_non_positive_allocation_raises(self):
        entry = self._margined_entry(100.0, 0, 0)
        with self.assertRaises(ValueError):
            bm.evaluate_against_allocation(entry, 0)
        with self.assertRaises(ValueError):
            bm.evaluate_against_allocation(entry, -10.0)


class PhaseMinimumMarginPctTest(unittest.TestCase):
    def test_known_phases(self):
        self.assertEqual(bm.phase_minimum_margin_pct("A"), 20)
        self.assertEqual(bm.phase_minimum_margin_pct("B"), 15)
        self.assertEqual(bm.phase_minimum_margin_pct("C"), 10)
        self.assertEqual(bm.phase_minimum_margin_pct("D"), 5)
        self.assertEqual(bm.phase_minimum_margin_pct("E"), 2)

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            bm.phase_minimum_margin_pct("Z")


class CheckMarginPolicyTest(unittest.TestCase):
    def _checked_entry(self, cbe, allocated):
        c1 = bm.contribution("EQUIP-1", cbe, 0)
        consolidated = bm.consolidate_category_budget("mass", [c1])
        margined = bm.apply_system_margin(consolidated, 0)
        return bm.evaluate_against_allocation(margined, allocated)

    def test_compliant_when_margin_meets_phase_minimum(self):
        entry = self._checked_entry(80.0, 100.0)  # 20% remaining
        result = bm.check_margin_policy(entry, "A")
        self.assertTrue(result["margin_policy_compliant"])
        self.assertEqual(result["phase"], "A")
        self.assertEqual(result["minimum_required_pct"], 20)

    def test_non_compliant_when_margin_below_phase_minimum(self):
        entry = self._checked_entry(90.0, 100.0)  # 10% remaining
        result = bm.check_margin_policy(entry, "A")  # requires 20%
        self.assertFalse(result["margin_policy_compliant"])

    def test_non_compliant_when_exceeded_even_if_late_phase(self):
        entry = self._checked_entry(110.0, 100.0)  # exceeded
        result = bm.check_margin_policy(entry, "E")
        self.assertEqual(entry["status"], "exceeded")
        self.assertFalse(result["margin_policy_compliant"])

    def test_unknown_phase_raises(self):
        entry = self._checked_entry(80.0, 100.0)
        with self.assertRaises(ValueError):
            bm.check_margin_policy(entry, "Z")


class SystemBudgetReportTest(unittest.TestCase):
    def _checked(self, cbe, allocated, phase):
        c1 = bm.contribution("EQUIP-1", cbe, 0)
        consolidated = bm.consolidate_category_budget("mass", [c1])
        margined = bm.apply_system_margin(consolidated, 0)
        evaluated = bm.evaluate_against_allocation(margined, allocated)
        return bm.check_margin_policy(evaluated, phase)

    def test_all_compliant(self):
        mass = self._checked(80.0, 100.0, "A")
        power = self._checked(70.0, 100.0, "A")
        ready, non_compliant = bm.system_budget_report([mass, power])
        self.assertTrue(ready)
        self.assertEqual(non_compliant, [])

    def test_lists_non_compliant_categories(self):
        mass = self._checked(80.0, 100.0, "A")
        power = self._checked(95.0, 100.0, "A")
        ready, non_compliant = bm.system_budget_report([mass, power])
        self.assertFalse(ready)
        self.assertEqual(non_compliant, [power])


if __name__ == "__main__":
    unittest.main(verbosity=2)
