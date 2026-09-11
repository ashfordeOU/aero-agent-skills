#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C Annex I Technical Budget Report DRD.

Exercises scripts/e10_budget_drd_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a budget category is recognized
or raises; a design maturity level maps to a margin fraction or raises; a
budget item's current best estimate is its basic value inflated by that
margin fraction, and a negative basic value or unrecognized maturity
raises; a budget item record missing a DRD-required field is flagged and
excluded from the total; an item's current best estimate is checked
against its allocated value (an unset allocation with a nonzero estimate
is itself a finding); category totals sum correctly and raise on an
unrecognized category; the system-level reported total applies the system
margin and is checked against the overall allocated budget (an unset
system budget with a nonzero total is itself a finding, and a negative
system margin raises); the full report review is compliant only when
every item and the system list are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_budget_drd_logic as bd  # noqa: E402


class ClassifyBudgetCategoryTest(unittest.TestCase):
    def test_mass_is_recognized(self):
        self.assertEqual(bd.classify_budget_category("mass"), "mass")

    def test_power_is_recognized(self):
        self.assertEqual(bd.classify_budget_category("power"), "power")

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            bd.classify_budget_category("mystery_budget")


class MarginFractionForMaturityTest(unittest.TestCase):
    def test_off_the_shelf_margin(self):
        self.assertAlmostEqual(bd.margin_fraction_for_maturity("off_the_shelf"), 0.02)

    def test_new_design_no_heritage_margin(self):
        self.assertAlmostEqual(
            bd.margin_fraction_for_maturity("new_design_no_heritage"), 0.20
        )

    def test_unknown_maturity_raises(self):
        with self.assertRaises(ValueError):
            bd.margin_fraction_for_maturity("guesswork")


class CurrentBestEstimateTest(unittest.TestCase):
    def test_off_the_shelf_applies_small_margin(self):
        self.assertAlmostEqual(
            bd.current_best_estimate(100.0, "off_the_shelf"), 102.0
        )

    def test_new_design_no_heritage_applies_large_margin(self):
        self.assertAlmostEqual(
            bd.current_best_estimate(100.0, "new_design_no_heritage"), 120.0
        )

    def test_negative_basic_value_raises(self):
        with self.assertRaises(ValueError):
            bd.current_best_estimate(-1.0, "off_the_shelf")

    def test_unrecognized_maturity_raises(self):
        with self.assertRaises(ValueError):
            bd.current_best_estimate(10.0, "guesswork")


class ItemCompletenessViolationsTest(unittest.TestCase):
    def test_complete_item_no_violation(self):
        item = {
            "item_id": "bat-1",
            "category": "power",
            "basic_value": 10.0,
            "maturity": "off_the_shelf",
            "allocated_value": 20.0,
        }
        self.assertEqual(bd.item_completeness_violations(item), [])

    def test_missing_fields_flagged(self):
        item = {"item_id": "bat-2", "category": "power"}
        violations = bd.item_completeness_violations(item)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "incomplete_drd_item_record")
        self.assertIn("basic_value", violations[0]["missing_fields"])
        self.assertIn("maturity", violations[0]["missing_fields"])
        self.assertIn("allocated_value", violations[0]["missing_fields"])


class ItemAllocationViolationsTest(unittest.TestCase):
    def test_within_allocation_no_violation(self):
        self.assertEqual(bd.item_allocation_violations("ant-1", 10.0, 20.0), [])

    def test_exceeding_allocation_flagged(self):
        violations = bd.item_allocation_violations("ant-1", 25.0, 20.0)
        self.assertEqual(
            violations,
            [
                {
                    "issue": "item_allocation_exceeded",
                    "item_id": "ant-1",
                    "current_best_estimate": 25.0,
                    "allocated_value": 20.0,
                }
            ],
        )

    def test_missing_allocation_with_nonzero_cbe_flagged(self):
        violations = bd.item_allocation_violations("ant-1", 5.0, None)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_item_allocation")

    def test_missing_allocation_with_zero_cbe_not_flagged(self):
        self.assertEqual(bd.item_allocation_violations("ant-1", 0.0, None), [])


class CategoryTotalsTest(unittest.TestCase):
    def test_sums_same_category(self):
        items = [
            {"category": "mass", "basic_value": 10.0, "maturity": "off_the_shelf"},
            {
                "category": "mass",
                "basic_value": 5.0,
                "maturity": "new_design_no_heritage",
            },
        ]
        totals = bd.category_totals(items)
        # 10 * 1.02 + 5 * 1.20 = 10.2 + 6.0 = 16.2
        self.assertAlmostEqual(totals["mass"], 16.2)

    def test_raises_on_unknown_category(self):
        items = [
            {"category": "warp_field", "basic_value": 1.0, "maturity": "off_the_shelf"}
        ]
        with self.assertRaises(ValueError):
            bd.category_totals(items)


class SystemBudgetViolationsTest(unittest.TestCase):
    def test_within_system_budget_no_violation(self):
        self.assertEqual(bd.system_budget_violations(100.0, 0.1, 200.0), [])

    def test_exceeding_system_budget_flagged(self):
        violations = bd.system_budget_violations(100.0, 0.5, 120.0)
        self.assertEqual(
            violations,
            [
                {
                    "issue": "system_budget_exceeded",
                    "reported_total": 150.0,
                    "system_allocated_budget": 120.0,
                }
            ],
        )

    def test_missing_system_budget_with_nonzero_total_flagged(self):
        violations = bd.system_budget_violations(100.0, 0.1, None)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_system_allocated_budget")

    def test_missing_system_budget_with_zero_total_not_flagged(self):
        self.assertEqual(bd.system_budget_violations(0.0, 0.1, None), [])

    def test_negative_margin_raises(self):
        with self.assertRaises(ValueError):
            bd.system_budget_violations(100.0, -0.1, 200.0)


class BudgetReportReviewTest(unittest.TestCase):
    def test_fully_compliant_report(self):
        report = {
            "items": [
                {
                    "item_id": "bat-1",
                    "category": "power",
                    "basic_value": 10.0,
                    "maturity": "off_the_shelf",
                    "allocated_value": 20.0,
                },
                {
                    "item_id": "ant-1",
                    "category": "mass",
                    "basic_value": 5.0,
                    "maturity": "existing_design_modified",
                    "allocated_value": 10.0,
                },
            ],
            "system_margin_fraction": 0.1,
            "system_allocated_budget": 30.0,
        }
        review = bd.budget_report_review(report)
        self.assertEqual(review["items"]["bat-1"], {"completeness": [], "allocation": []})
        self.assertEqual(review["items"]["ant-1"], {"completeness": [], "allocation": []})
        self.assertEqual(review["system"], [])
        self.assertTrue(bd.is_budget_compliant(review))

    def test_report_flags_item_and_system_violations(self):
        report = {
            "items": [
                {
                    "item_id": "bat-1",
                    "category": "power",
                    "basic_value": 100.0,
                    "maturity": "new_design_no_heritage",
                    "allocated_value": 50.0,
                },
            ],
            "system_margin_fraction": 0.0,
            "system_allocated_budget": 100.0,
        }
        review = bd.budget_report_review(report)
        self.assertTrue(review["items"]["bat-1"]["allocation"])
        self.assertTrue(review["system"])
        self.assertFalse(bd.is_budget_compliant(review))

    def test_incomplete_item_skipped_from_total_and_flagged(self):
        report = {
            "items": [
                {"item_id": "bat-2", "category": "power", "basic_value": 10.0},
            ],
            "system_margin_fraction": 0.0,
            "system_allocated_budget": 0.0,
        }
        review = bd.budget_report_review(report)
        self.assertTrue(review["items"]["bat-2"]["completeness"])
        self.assertEqual(review["items"]["bat-2"]["allocation"], [])
        self.assertEqual(review["system"], [])
        self.assertFalse(bd.is_budget_compliant(review))

    def test_report_raises_on_unknown_category(self):
        report = {
            "items": [
                {
                    "item_id": "bat-3",
                    "category": "warp_field",
                    "basic_value": 1.0,
                    "maturity": "off_the_shelf",
                    "allocated_value": 5.0,
                },
            ],
            "system_margin_fraction": 0.0,
            "system_allocated_budget": None,
        }
        with self.assertRaises(ValueError):
            bd.budget_report_review(report)


if __name__ == "__main__":
    unittest.main(verbosity=2)
