#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.4.1.4 / Annex G Design
Definition File (DDF) assembly and review.

Exercises scripts/e10_ddf_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a DDF content item type
categorizes into exactly one of design description, budget, or
interface data, and an unrecognized type raises; a budget item's
margin is (maximum - predicted) / maximum * 100, may be negative, and
a negative predicted value or a non-positive maximum raises; a budget
item's margin is checked against the minimum required at its review
milestone, and an unrecognized milestone or budget item type raises;
an interface data item must declare a mating product distinct from
its own product, else it is flagged, and an unrecognized interface
item type raises; a product's DDF is section-complete only when all
three sections have at least one item on record; and the aggregated
per-product review is baseline-ready only when completeness, budget,
and interface findings are all empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_ddf_logic as ddf  # noqa: E402


class ClassifyDdfItemTest(unittest.TestCase):
    def test_functional_description_is_design_description(self):
        self.assertEqual(
            ddf.classify_ddf_item("functional_description"), "design_description"
        )

    def test_design_solution_is_design_description(self):
        self.assertEqual(
            ddf.classify_ddf_item("design_solution"), "design_description"
        )

    def test_mass_budget_is_budget(self):
        self.assertEqual(ddf.classify_ddf_item("mass_budget"), "budget")

    def test_link_budget_is_budget(self):
        self.assertEqual(ddf.classify_ddf_item("link_budget"), "budget")

    def test_physical_interface_is_interface_data(self):
        self.assertEqual(
            ddf.classify_ddf_item("physical_interface"), "interface_data"
        )

    def test_thermal_interface_is_interface_data(self):
        self.assertEqual(
            ddf.classify_ddf_item("thermal_interface"), "interface_data"
        )

    def test_unknown_item_type_raises(self):
        with self.assertRaises(ValueError):
            ddf.classify_ddf_item("mystery_annex")


class BudgetMarginPercentTest(unittest.TestCase):
    def test_partial_margin(self):
        self.assertAlmostEqual(ddf.budget_margin_percent(80.0, 100.0), 20.0)

    def test_zero_predicted_is_full_margin(self):
        self.assertAlmostEqual(ddf.budget_margin_percent(0.0, 100.0), 100.0)

    def test_predicted_at_maximum_is_zero_margin(self):
        self.assertAlmostEqual(ddf.budget_margin_percent(100.0, 100.0), 0.0)

    def test_predicted_exceeds_maximum_is_negative_margin(self):
        self.assertAlmostEqual(ddf.budget_margin_percent(120.0, 100.0), -20.0)

    def test_negative_predicted_raises(self):
        with self.assertRaises(ValueError):
            ddf.budget_margin_percent(-1.0, 100.0)

    def test_zero_maximum_raises(self):
        with self.assertRaises(ValueError):
            ddf.budget_margin_percent(10.0, 0.0)

    def test_negative_maximum_raises(self):
        with self.assertRaises(ValueError):
            ddf.budget_margin_percent(10.0, -50.0)


class BudgetMarginViolationsTest(unittest.TestCase):
    def test_margin_meets_minimum_no_violation(self):
        item = {
            "item_type": "mass_budget",
            "predicted_value": 70.0,
            "maximum_value": 100.0,
        }
        self.assertEqual(ddf.budget_margin_violations("bus-1", item, "PDR"), [])

    def test_margin_below_minimum_flagged(self):
        item = {
            "item_type": "mass_budget",
            "predicted_value": 90.0,
            "maximum_value": 100.0,
        }
        violations = ddf.budget_margin_violations("bus-1", item, "PDR")
        self.assertEqual(
            violations,
            [
                {
                    "issue": "budget_margin_below_minimum",
                    "product": "bus-1",
                    "item_type": "mass_budget",
                    "margin_percent": 10.0,
                    "required_percent": 20.0,
                }
            ],
        )

    def test_same_margin_passes_early_milestone_fails_late(self):
        item = {
            "item_type": "power_budget",
            "predicted_value": 85.0,
            "maximum_value": 100.0,
        }
        self.assertEqual(ddf.budget_margin_violations("bus-1", item, "QR"), [])
        violations = ddf.budget_margin_violations("bus-1", item, "SRR")
        self.assertEqual(len(violations), 1)

    def test_unrecognized_milestone_raises(self):
        item = {
            "item_type": "mass_budget",
            "predicted_value": 10.0,
            "maximum_value": 100.0,
        }
        with self.assertRaises(ValueError):
            ddf.budget_margin_violations("bus-1", item, "FRR")

    def test_unrecognized_budget_item_type_raises(self):
        item = {
            "item_type": "functional_description",
            "predicted_value": 10.0,
            "maximum_value": 100.0,
        }
        with self.assertRaises(ValueError):
            ddf.budget_margin_violations("bus-1", item, "PDR")


class InterfaceLinkageViolationsTest(unittest.TestCase):
    def test_valid_mating_product_no_violation(self):
        item = {"item_type": "electrical_interface", "mating_product": "payload-1"}
        self.assertEqual(ddf.interface_linkage_violations("bus-1", item), [])

    def test_missing_mating_product_flagged(self):
        item = {"item_type": "electrical_interface"}
        violations = ddf.interface_linkage_violations("bus-1", item)
        self.assertEqual(
            violations,
            [
                {
                    "issue": "interface_missing_mating_product",
                    "product": "bus-1",
                    "item_type": "electrical_interface",
                }
            ],
        )

    def test_self_referential_mating_product_flagged(self):
        item = {"item_type": "physical_interface", "mating_product": "bus-1"}
        violations = ddf.interface_linkage_violations("bus-1", item)
        self.assertEqual(violations[0]["issue"], "interface_self_referential")

    def test_unrecognized_interface_item_type_raises(self):
        item = {"item_type": "mass_budget", "mating_product": "payload-1"}
        with self.assertRaises(ValueError):
            ddf.interface_linkage_violations("bus-1", item)


class DdfCompletenessViolationsTest(unittest.TestCase):
    def test_all_sections_present_no_violation(self):
        items = [
            {"item_type": "functional_description"},
            {"item_type": "mass_budget"},
            {"item_type": "physical_interface"},
        ]
        self.assertEqual(ddf.ddf_completeness_violations("bus-1", items), [])

    def test_missing_one_section_flagged(self):
        items = [
            {"item_type": "functional_description"},
            {"item_type": "mass_budget"},
        ]
        violations = ddf.ddf_completeness_violations("bus-1", items)
        self.assertEqual(
            violations,
            [{"issue": "missing_ddf_section", "product": "bus-1", "section": "interface_data"}],
        )

    def test_empty_items_flags_all_sections(self):
        violations = ddf.ddf_completeness_violations("bus-1", [])
        self.assertEqual(len(violations), 3)

    def test_unrecognized_item_type_raises(self):
        with self.assertRaises(ValueError):
            ddf.ddf_completeness_violations("bus-1", [{"item_type": "unobtainium_panel"}])


class DdfReviewTest(unittest.TestCase):
    def _compliant_items(self):
        return [
            {"item_type": "functional_description"},
            {
                "item_type": "mass_budget",
                "predicted_value": 50.0,
                "maximum_value": 100.0,
            },
            {"item_type": "physical_interface", "mating_product": "payload-1"},
        ]

    def test_fully_compliant_review_is_baseline_ready(self):
        product = {
            "product_id": "bus-1",
            "milestone": "PDR",
            "items": self._compliant_items(),
        }
        review = ddf.ddf_review(product)
        self.assertEqual(review, {"completeness": [], "budgets": [], "interfaces": []})
        self.assertTrue(ddf.is_ddf_baseline_ready(review))

    def test_review_surfaces_each_category_independently(self):
        product = {
            "product_id": "bus-2",
            "milestone": "CDR",
            "items": [
                {"item_type": "functional_description"},
                {
                    "item_type": "mass_budget",
                    "predicted_value": 98.0,
                    "maximum_value": 100.0,
                },
                {"item_type": "physical_interface"},
            ],
        }
        review = ddf.ddf_review(product)
        self.assertEqual(review["completeness"], [])
        self.assertTrue(review["budgets"])
        self.assertTrue(review["interfaces"])
        self.assertFalse(ddf.is_ddf_baseline_ready(review))

    def test_missing_section_alone_blocks_baseline_ready(self):
        product = {
            "product_id": "bus-3",
            "milestone": "SRR",
            "items": [
                {"item_type": "functional_description"},
                {
                    "item_type": "mass_budget",
                    "predicted_value": 10.0,
                    "maximum_value": 100.0,
                },
            ],
        }
        review = ddf.ddf_review(product)
        self.assertTrue(review["completeness"])
        self.assertEqual(review["budgets"], [])
        self.assertFalse(ddf.is_ddf_baseline_ready(review))

    def test_review_raises_on_unrecognized_milestone(self):
        product = {"product_id": "bus-1", "milestone": "FRR", "items": []}
        with self.assertRaises(ValueError):
            ddf.ddf_review(product)

    def test_review_raises_on_unrecognized_item_type(self):
        product = {
            "product_id": "bus-1",
            "milestone": "PDR",
            "items": [{"item_type": "unobtainium_panel"}],
        }
        with self.assertRaises(ValueError):
            ddf.ddf_review(product)


class IsDdfBaselineReadyTest(unittest.TestCase):
    def test_all_empty_categories_is_ready(self):
        self.assertTrue(
            ddf.is_ddf_baseline_ready(
                {"completeness": [], "budgets": [], "interfaces": []}
            )
        )

    def test_any_nonempty_category_is_not_ready(self):
        self.assertFalse(
            ddf.is_ddf_baseline_ready(
                {"completeness": [], "budgets": [{"issue": "x"}], "interfaces": []}
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
