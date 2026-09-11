#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.4.1.2 + Annex I
technical budget and margin policy during design.

Exercises scripts/e10_design_budgets_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the minimum
required margin shrinks from phase A to phase D and an unrecognized
phase raises; per-item consumption and current margin are computed
from allocation and current best estimate, with a non-positive
allocation or negative estimate raising; an item whose estimate
exceeds its allocation is flagged regardless of phase, otherwise a
current margin short of the phase's required margin is flagged; the
sum of sub-item allocations must not exceed the system-level
allocation; the system-level margin on the summed current best
estimates is checked the same way as an item; and the aggregated
review is compliant only when every category is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_design_budgets_logic as bg  # noqa: E402


class RequiredMaturityMarginPercentTest(unittest.TestCase):
    def test_phase_a_requires_largest_margin(self):
        self.assertEqual(bg.required_maturity_margin_percent("A"), 20.0)

    def test_phase_d_requires_smallest_margin(self):
        self.assertEqual(bg.required_maturity_margin_percent("D"), 5.0)

    def test_margin_shrinks_monotonically_through_phases(self):
        phases = ["A", "B", "C", "D"]
        percents = [bg.required_maturity_margin_percent(p) for p in phases]
        self.assertEqual(percents, sorted(percents, reverse=True))

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            bg.required_maturity_margin_percent("E")


class ConsumptionPercentTest(unittest.TestCase):
    def test_half_consumed(self):
        self.assertAlmostEqual(bg.consumption_percent(100.0, 50.0), 50.0)

    def test_fully_consumed(self):
        self.assertAlmostEqual(bg.consumption_percent(100.0, 100.0), 100.0)

    def test_non_positive_allocation_raises(self):
        with self.assertRaises(ValueError):
            bg.consumption_percent(0.0, 10.0)

    def test_negative_estimate_raises(self):
        with self.assertRaises(ValueError):
            bg.consumption_percent(100.0, -1.0)


class CurrentMarginPercentTest(unittest.TestCase):
    def test_partial_margin_remaining(self):
        self.assertAlmostEqual(bg.current_margin_percent(100.0, 80.0), 20.0)

    def test_negative_margin_when_over_allocation(self):
        self.assertAlmostEqual(bg.current_margin_percent(100.0, 120.0), -20.0)

    def test_non_positive_allocation_raises(self):
        with self.assertRaises(ValueError):
            bg.current_margin_percent(-5.0, 1.0)


class ItemMarginViolationsTest(unittest.TestCase):
    def test_within_required_margin_no_violation(self):
        violations = bg.item_margin_violations("bus-mass", 100.0, 70.0, "C")
        self.assertEqual(violations, [])

    def test_below_required_margin_flagged(self):
        violations = bg.item_margin_violations("bus-mass", 100.0, 95.0, "C")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "insufficient_maturity_margin")

    def test_estimate_exceeding_allocation_flagged_regardless_of_phase(self):
        violations = bg.item_margin_violations("bus-mass", 100.0, 110.0, "A")
        self.assertEqual(
            violations,
            [
                {
                    "issue": "item_budget_exceeded",
                    "item": "bus-mass",
                    "allocated": 100.0,
                    "current_best_estimate": 110.0,
                }
            ],
        )

    def test_early_phase_needs_bigger_margin_than_late_phase(self):
        # 12% current margin: fails phase A's 20% but passes phase D's 5%.
        early = bg.item_margin_violations("payload-power", 100.0, 88.0, "A")
        late = bg.item_margin_violations("payload-power", 100.0, 88.0, "D")
        self.assertTrue(early)
        self.assertEqual(late, [])

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            bg.item_margin_violations("bus-mass", 100.0, 50.0, "Z")


class AllocationConsistencyViolationsTest(unittest.TestCase):
    def test_sub_allocations_within_system_total_no_violation(self):
        violations = bg.allocation_consistency_violations(
            "mass", 500.0, [300.0, 150.0]
        )
        self.assertEqual(violations, [])

    def test_sub_allocations_exceeding_system_total_flagged(self):
        violations = bg.allocation_consistency_violations(
            "mass", 500.0, [300.0, 250.0]
        )
        self.assertEqual(
            violations,
            [
                {
                    "issue": "system_allocation_exceeded",
                    "budget": "mass",
                    "total_allocated": 550.0,
                    "system_allocation": 500.0,
                }
            ],
        )

    def test_non_positive_system_allocation_raises(self):
        with self.assertRaises(ValueError):
            bg.allocation_consistency_violations("mass", 0.0, [10.0])


class SystemMarginViolationsTest(unittest.TestCase):
    def test_system_margin_within_requirement_no_violation(self):
        violations = bg.system_margin_violations("mass", 500.0, 400.0, "D")
        self.assertEqual(violations, [])

    def test_system_estimate_exceeding_allocation_flagged(self):
        violations = bg.system_margin_violations("mass", 500.0, 520.0, "D")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "system_budget_exceeded")

    def test_system_margin_below_requirement_flagged(self):
        violations = bg.system_margin_violations("mass", 500.0, 480.0, "A")
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "insufficient_system_margin")


class TechnicalBudgetReviewTest(unittest.TestCase):
    def test_fully_compliant_budget(self):
        budget = {
            "budget_id": "mass",
            "phase": "D",
            "system_allocation": 500.0,
            "items": [
                {"item_id": "bus", "allocated": 300.0, "current_best_estimate": 280.0},
                {"item_id": "payload", "allocated": 150.0, "current_best_estimate": 130.0},
            ],
        }
        review = bg.technical_budget_review(budget)
        self.assertEqual(review, {"items": [], "allocation": [], "system_margin": []})
        self.assertTrue(bg.is_budget_compliant(review))

    def test_review_surfaces_each_category_independently(self):
        budget = {
            "budget_id": "mass",
            "phase": "A",
            "system_allocation": 400.0,
            "items": [
                {"item_id": "bus", "allocated": 300.0, "current_best_estimate": 295.0},
                {"item_id": "payload", "allocated": 200.0, "current_best_estimate": 150.0},
            ],
        }
        review = bg.technical_budget_review(budget)
        self.assertTrue(review["items"])
        self.assertTrue(review["allocation"])
        self.assertTrue(review["system_margin"])
        self.assertFalse(bg.is_budget_compliant(review))

    def test_review_raises_on_unknown_phase(self):
        budget = {
            "budget_id": "mass",
            "phase": "Q",
            "system_allocation": 100.0,
            "items": [
                {"item_id": "bus", "allocated": 50.0, "current_best_estimate": 40.0},
            ],
        }
        with self.assertRaises(ValueError):
            bg.technical_budget_review(budget)


if __name__ == "__main__":
    unittest.main(verbosity=2)
