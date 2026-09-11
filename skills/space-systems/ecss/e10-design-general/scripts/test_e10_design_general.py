#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.4.1.1 general design
conduct.

Exercises scripts/e10_design_general_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a design decision
is closed only once an alternative is selected from its recorded
options and a rationale is on record, an empty alternatives list or a
selected alternative outside the recorded options raises; a decision
with no requirement_ids is untraceable and one that is not closed is
open, both surfaced independently; a requirement not referenced by any
design definition item is uncovered; a design item with no
requirement_ids is unallocated and one referencing an id outside the
product's requirement set has an unknown reference; the per-product
review filters every input to that product and is complete only when
all three categories are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_design_general_logic as dg  # noqa: E402


class DecisionStatusTest(unittest.TestCase):
    def test_selected_and_rationale_is_closed(self):
        self.assertEqual(
            dg.decision_status(["a", "b"], "a", "lower mass"), "closed"
        )

    def test_missing_rationale_is_open(self):
        self.assertEqual(dg.decision_status(["a", "b"], "a", None), "open")

    def test_missing_selection_is_open(self):
        self.assertEqual(dg.decision_status(["a", "b"], None, "lower mass"), "open")

    def test_missing_both_is_open(self):
        self.assertEqual(dg.decision_status(["a", "b"], None, None), "open")

    def test_single_alternative_can_close(self):
        self.assertEqual(
            dg.decision_status(["only-option"], "only-option", "no viable alternative"),
            "closed",
        )

    def test_empty_alternatives_raises(self):
        with self.assertRaises(ValueError):
            dg.decision_status([], None, None)

    def test_selection_outside_alternatives_raises(self):
        with self.assertRaises(ValueError):
            dg.decision_status(["a", "b"], "c", "rationale")


class DesignDecisionViolationsTest(unittest.TestCase):
    def test_closed_and_traced_has_no_violations(self):
        decision = {
            "decision_id": "dd-1",
            "requirement_ids": ["req-1"],
            "alternatives": ["a", "b"],
            "selected_alternative": "a",
            "rationale": "lower mass",
        }
        self.assertEqual(dg.design_decision_violations(decision), [])

    def test_untraceable_decision_flagged(self):
        decision = {
            "decision_id": "dd-2",
            "requirement_ids": [],
            "alternatives": ["a", "b"],
            "selected_alternative": "a",
            "rationale": "lower mass",
        }
        violations = dg.design_decision_violations(decision)
        self.assertEqual(
            violations, [{"issue": "untraceable_design_decision", "decision": "dd-2"}]
        )

    def test_open_decision_flagged(self):
        decision = {
            "decision_id": "dd-3",
            "requirement_ids": ["req-1"],
            "alternatives": ["a", "b"],
            "selected_alternative": None,
            "rationale": None,
        }
        violations = dg.design_decision_violations(decision)
        self.assertEqual(
            violations, [{"issue": "open_design_decision", "decision": "dd-3"}]
        )

    def test_untraceable_and_open_both_flagged(self):
        decision = {
            "decision_id": "dd-4",
            "requirement_ids": [],
            "alternatives": ["a", "b"],
            "selected_alternative": None,
            "rationale": None,
        }
        violations = dg.design_decision_violations(decision)
        self.assertEqual(len(violations), 2)

    def test_malformed_decision_raises(self):
        decision = {
            "decision_id": "dd-5",
            "requirement_ids": ["req-1"],
            "alternatives": [],
            "selected_alternative": None,
            "rationale": None,
        }
        with self.assertRaises(ValueError):
            dg.design_decision_violations(decision)


class RequirementCoverageViolationsTest(unittest.TestCase):
    def test_covered_requirement_no_violation(self):
        requirements = [{"requirement_id": "req-1", "product_id": "p1"}]
        design_items = [{"item_id": "di-1", "requirement_ids": ["req-1"]}]
        self.assertEqual(
            dg.requirement_coverage_violations(requirements, design_items), []
        )

    def test_uncovered_requirement_flagged(self):
        requirements = [{"requirement_id": "req-1", "product_id": "p1"}]
        violations = dg.requirement_coverage_violations(requirements, [])
        self.assertEqual(
            violations, [{"issue": "uncovered_requirement", "requirement": "req-1"}]
        )


class UnallocatedDesignItemViolationsTest(unittest.TestCase):
    def test_item_with_requirement_no_violation(self):
        design_items = [{"item_id": "di-1", "requirement_ids": ["req-1"]}]
        self.assertEqual(
            dg.unallocated_design_item_violations(design_items, {"req-1"}), []
        )

    def test_item_without_requirements_flagged(self):
        design_items = [{"item_id": "di-2", "requirement_ids": []}]
        violations = dg.unallocated_design_item_violations(design_items, {"req-1"})
        self.assertEqual(
            violations, [{"issue": "unallocated_design_item", "item": "di-2"}]
        )

    def test_item_with_unknown_requirement_flagged(self):
        design_items = [{"item_id": "di-3", "requirement_ids": ["req-9"]}]
        violations = dg.unallocated_design_item_violations(design_items, {"req-1"})
        self.assertEqual(
            violations,
            [
                {
                    "issue": "unknown_requirement_reference",
                    "item": "di-3",
                    "requirement": "req-9",
                }
            ],
        )


class ProductDesignReviewTest(unittest.TestCase):
    def test_fully_compliant_review(self):
        requirements = [{"requirement_id": "req-1", "product_id": "p1"}]
        design_items = [
            {"item_id": "di-1", "product_id": "p1", "requirement_ids": ["req-1"]}
        ]
        design_decisions = [
            {
                "decision_id": "dd-1",
                "product_id": "p1",
                "requirement_ids": ["req-1"],
                "alternatives": ["a", "b"],
                "selected_alternative": "a",
                "rationale": "lower mass",
            }
        ]
        review = dg.product_design_review(
            "p1", requirements, design_items, design_decisions
        )
        self.assertEqual(
            review,
            {
                "uncovered_requirements": [],
                "unallocated_design_items": [],
                "decisions": [],
            },
        )
        self.assertTrue(dg.is_design_complete(review))

    def test_review_isolates_by_product(self):
        requirements = [
            {"requirement_id": "req-1", "product_id": "p1"},
            {"requirement_id": "req-2", "product_id": "p2"},
        ]
        design_items = [
            {"item_id": "di-1", "product_id": "p1", "requirement_ids": ["req-1"]},
        ]
        design_decisions = []
        review = dg.product_design_review(
            "p2", requirements, design_items, design_decisions
        )
        self.assertEqual(
            review["uncovered_requirements"],
            [{"issue": "uncovered_requirement", "requirement": "req-2"}],
        )
        self.assertFalse(dg.is_design_complete(review))

    def test_review_flags_uncovered_and_unallocated_and_open_decision(self):
        requirements = [{"requirement_id": "req-1", "product_id": "p1"}]
        design_items = [
            {"item_id": "di-1", "product_id": "p1", "requirement_ids": []}
        ]
        design_decisions = [
            {
                "decision_id": "dd-1",
                "product_id": "p1",
                "requirement_ids": ["req-1"],
                "alternatives": ["a", "b"],
                "selected_alternative": None,
                "rationale": None,
            }
        ]
        review = dg.product_design_review(
            "p1", requirements, design_items, design_decisions
        )
        self.assertTrue(review["uncovered_requirements"])
        self.assertTrue(review["unallocated_design_items"])
        self.assertTrue(review["decisions"])
        self.assertFalse(dg.is_design_complete(review))

    def test_review_raises_on_malformed_decision(self):
        requirements = [{"requirement_id": "req-1", "product_id": "p1"}]
        design_items = [
            {"item_id": "di-1", "product_id": "p1", "requirement_ids": ["req-1"]}
        ]
        design_decisions = [
            {
                "decision_id": "dd-1",
                "product_id": "p1",
                "requirement_ids": ["req-1"],
                "alternatives": [],
                "selected_alternative": None,
                "rationale": None,
            }
        ]
        with self.assertRaises(ValueError):
            dg.product_design_review("p1", requirements, design_items, design_decisions)


if __name__ == "__main__":
    unittest.main(verbosity=2)
