#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.2.3.6 requirement
consistency check.

Exercises scripts/e10_req_consistency_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a constraint
kind reduces to a feasible interval ("exact" a point, "maximum" an
upper-bounded interval, "minimum" a lower-bounded interval) and an
unrecognized kind raises; intersecting a group's intervals with an
empty low/high crossover means the group is infeasible, and
intersecting zero intervals raises; a value-conflict group with fewer
than two requirements is trivially consistent, a group whose
requirements disagree on unit is flagged without comparing values, a
requirement missing its unit raises, and an empty feasible
intersection is flagged; an interface attribute bound to more than one
distinct value across its requirement bindings is flagged per
attribute, independent of other attributes on the same interface; the
aggregated review is consistent only when both categories are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_req_consistency_logic as rc  # noqa: E402


class ConstraintIntervalTest(unittest.TestCase):
    def test_exact_is_a_point(self):
        self.assertEqual(rc.constraint_interval("exact", 5.0), (5.0, 5.0))

    def test_maximum_bounds_above(self):
        self.assertEqual(
            rc.constraint_interval("maximum", 10.0), (float("-inf"), 10.0)
        )

    def test_minimum_bounds_below(self):
        self.assertEqual(
            rc.constraint_interval("minimum", 2.0), (2.0, float("inf"))
        )

    def test_unrecognized_kind_raises(self):
        with self.assertRaises(ValueError):
            rc.constraint_interval("nominal", 1.0)


class IntersectIntervalsTest(unittest.TestCase):
    def test_single_interval_unchanged(self):
        self.assertEqual(rc.intersect_intervals([(1.0, 5.0)]), (1.0, 5.0))

    def test_overlapping_intervals_narrow(self):
        intervals = [(0.0, 10.0), (2.0, 8.0), (float("-inf"), 6.0)]
        self.assertEqual(rc.intersect_intervals(intervals), (2.0, 6.0))

    def test_disjoint_intervals_are_infeasible(self):
        low, high = rc.intersect_intervals([(0.0, 2.0), (5.0, 10.0)])
        self.assertGreater(low, high)

    def test_empty_intervals_raises(self):
        with self.assertRaises(ValueError):
            rc.intersect_intervals([])


class ValueConflictsTest(unittest.TestCase):
    def test_empty_group_has_no_violation(self):
        self.assertEqual(rc.value_conflicts("mass-budget", []), [])

    def test_single_requirement_has_no_violation(self):
        requirements = [
            {"req_id": "REQ-1", "kind": "maximum", "value": 100.0, "unit": "kg"}
        ]
        self.assertEqual(rc.value_conflicts("mass-budget", requirements), [])

    def test_compatible_bounds_have_no_violation(self):
        requirements = [
            {"req_id": "REQ-1", "kind": "maximum", "value": 100.0, "unit": "kg"},
            {"req_id": "REQ-2", "kind": "minimum", "value": 50.0, "unit": "kg"},
        ]
        self.assertEqual(rc.value_conflicts("mass-budget", requirements), [])

    def test_disjoint_bounds_are_flagged(self):
        requirements = [
            {"req_id": "REQ-1", "kind": "maximum", "value": 50.0, "unit": "kg"},
            {"req_id": "REQ-2", "kind": "minimum", "value": 100.0, "unit": "kg"},
        ]
        violations = rc.value_conflicts("mass-budget", requirements)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "conflicting_constraint_values")
        self.assertEqual(violations[0]["req_ids"], ["REQ-1", "REQ-2"])

    def test_conflicting_exact_values_are_flagged(self):
        requirements = [
            {"req_id": "REQ-1", "kind": "exact", "value": 28.0, "unit": "v"},
            {"req_id": "REQ-2", "kind": "exact", "value": 50.0, "unit": "v"},
        ]
        violations = rc.value_conflicts("bus-voltage", requirements)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["feasible_low"], 50.0)
        self.assertEqual(violations[0]["feasible_high"], 28.0)

    def test_mismatched_units_are_flagged_without_value_check(self):
        requirements = [
            {"req_id": "REQ-1", "kind": "maximum", "value": 50.0, "unit": "kg"},
            {"req_id": "REQ-2", "kind": "maximum", "value": 50.0, "unit": "lb"},
        ]
        violations = rc.value_conflicts("mass-budget", requirements)
        self.assertEqual(
            violations,
            [
                {
                    "issue": "incompatible_units",
                    "group": "mass-budget",
                    "req_ids": ["REQ-1", "REQ-2"],
                    "units": ["kg", "lb"],
                }
            ],
        )

    def test_missing_unit_raises(self):
        requirements = [
            {"req_id": "REQ-1", "kind": "maximum", "value": 50.0, "unit": "kg"},
            {"req_id": "REQ-2", "kind": "minimum", "value": 10.0, "unit": ""},
        ]
        with self.assertRaises(ValueError):
            rc.value_conflicts("mass-budget", requirements)

    def test_three_way_group_narrows_correctly(self):
        requirements = [
            {"req_id": "REQ-1", "kind": "maximum", "value": 100.0, "unit": "kg"},
            {"req_id": "REQ-2", "kind": "minimum", "value": 20.0, "unit": "kg"},
            {"req_id": "REQ-3", "kind": "exact", "value": 45.0, "unit": "kg"},
        ]
        self.assertEqual(rc.value_conflicts("mass-budget", requirements), [])


class InterfaceAttributeConflictsTest(unittest.TestCase):
    def test_no_bindings_no_violation(self):
        self.assertEqual(rc.interface_attribute_conflicts("PWR-1", []), [])

    def test_matching_values_no_violation(self):
        bindings = [
            {"req_id": "REQ-1", "attribute": "voltage", "value": "28V"},
            {"req_id": "REQ-2", "attribute": "voltage", "value": "28V"},
        ]
        self.assertEqual(rc.interface_attribute_conflicts("PWR-1", bindings), [])

    def test_conflicting_values_flagged(self):
        bindings = [
            {"req_id": "REQ-1", "attribute": "voltage", "value": "28V"},
            {"req_id": "REQ-2", "attribute": "voltage", "value": "50V"},
        ]
        violations = rc.interface_attribute_conflicts("PWR-1", bindings)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "interface_attribute_conflict")
        self.assertEqual(violations[0]["attribute"], "voltage")
        self.assertEqual(violations[0]["req_ids"], ["REQ-1", "REQ-2"])

    def test_conflicts_are_independent_per_attribute(self):
        bindings = [
            {"req_id": "REQ-1", "attribute": "voltage", "value": "28V"},
            {"req_id": "REQ-2", "attribute": "voltage", "value": "28V"},
            {"req_id": "REQ-1", "attribute": "connector", "value": "D38999"},
            {"req_id": "REQ-2", "attribute": "connector", "value": "MDM"},
        ]
        violations = rc.interface_attribute_conflicts("PWR-1", bindings)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["attribute"], "connector")


class RequirementSetConsistencyReviewTest(unittest.TestCase):
    def test_fully_consistent_review(self):
        value_groups = {
            "mass-budget": [
                {"req_id": "REQ-1", "kind": "maximum", "value": 100.0, "unit": "kg"},
                {"req_id": "REQ-2", "kind": "minimum", "value": 50.0, "unit": "kg"},
            ]
        }
        interface_bindings = {
            "PWR-1": [
                {"req_id": "REQ-3", "attribute": "voltage", "value": "28V"},
                {"req_id": "REQ-4", "attribute": "voltage", "value": "28V"},
            ]
        }
        review = rc.requirement_set_consistency_review(
            value_groups, interface_bindings
        )
        self.assertEqual(review, {"value_conflicts": [], "interface_conflicts": []})
        self.assertTrue(rc.is_requirement_set_consistent(review))

    def test_review_surfaces_each_category_independently(self):
        value_groups = {
            "mass-budget": [
                {"req_id": "REQ-1", "kind": "maximum", "value": 50.0, "unit": "kg"},
                {"req_id": "REQ-2", "kind": "minimum", "value": 100.0, "unit": "kg"},
            ]
        }
        interface_bindings = {
            "PWR-1": [
                {"req_id": "REQ-3", "attribute": "voltage", "value": "28V"},
                {"req_id": "REQ-4", "attribute": "voltage", "value": "50V"},
            ]
        }
        review = rc.requirement_set_consistency_review(
            value_groups, interface_bindings
        )
        self.assertTrue(review["value_conflicts"])
        self.assertTrue(review["interface_conflicts"])
        self.assertFalse(rc.is_requirement_set_consistent(review))

    def test_review_aggregates_multiple_groups(self):
        value_groups = {
            "mass-budget": [
                {"req_id": "REQ-1", "kind": "maximum", "value": 100.0, "unit": "kg"},
                {"req_id": "REQ-2", "kind": "minimum", "value": 200.0, "unit": "kg"},
            ],
            "power-budget": [
                {"req_id": "REQ-3", "kind": "maximum", "value": 500.0, "unit": "w"},
                {"req_id": "REQ-4", "kind": "minimum", "value": 600.0, "unit": "w"},
            ],
        }
        review = rc.requirement_set_consistency_review(value_groups, {})
        self.assertEqual(len(review["value_conflicts"]), 2)
        groups_flagged = {v["group"] for v in review["value_conflicts"]}
        self.assertEqual(groups_flagged, {"mass-budget", "power-budget"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
