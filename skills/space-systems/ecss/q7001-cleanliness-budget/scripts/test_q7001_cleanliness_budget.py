"""Contract tests for the cleanliness budget allocation and closure logic."""

import copy
import unittest

from q7001_cleanliness_budget_logic import (
    CLOSURE_TOLERANCE,
    LEVEL_ORDER,
    allocate_by_weight,
    assess_budget,
    close_node,
    combine,
    combine_linear,
    combine_quadrature,
    hold_reserve,
    roll_up,
    validate_budget_value,
    validate_level,
    validate_node,
)


def sample_tree():
    """System/subsystem/unit allocation tree, deposition in mg/m^2."""
    return {
        "name": "observatory",
        "level": "system",
        "allocation": 75.0,
        "children": [
            {
                "name": "payload",
                "level": "subsystem",
                "allocation": 45.0,
                "children": [
                    {"name": "telescope", "level": "unit", "allocation": 30.0},
                    {"name": "detector", "level": "unit", "allocation": 15.0},
                ],
            },
            {
                "name": "platform",
                "level": "subsystem",
                "allocation": 30.0,
                "children": [
                    {"name": "propulsion", "level": "unit", "allocation": 12.0},
                    {"name": "avionics", "level": "unit", "allocation": 8.0},
                ],
            },
        ],
    }


class ValidationTests(unittest.TestCase):
    def test_budget_value_returns_float(self):
        self.assertAlmostEqual(validate_budget_value(7, "x"), 7.0, places=9)

    def test_zero_budget_allowed_by_default(self):
        self.assertAlmostEqual(validate_budget_value(0.0, "x"), 0.0, places=9)

    def test_zero_budget_rejected_when_disallowed(self):
        with self.assertRaises(ValueError):
            validate_budget_value(0.0, "x", allow_zero=False)

    def test_negative_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_budget_value(-1.0, "x")

    def test_boolean_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_budget_value(True, "x")

    def test_non_finite_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_budget_value(float("inf"), "x")

    def test_level_index_follows_the_decomposition_order(self):
        self.assertEqual(validate_level("system"), 0)
        self.assertEqual(validate_level("unit"), len(LEVEL_ORDER) - 1)

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_level("assembly")


class ReserveAndSplitTests(unittest.TestCase):
    def test_reserve_is_held_before_allocation(self):
        allocatable, reserve = hold_reserve(100.0, 0.25)
        self.assertAlmostEqual(allocatable, 75.0, places=9)
        self.assertAlmostEqual(reserve, 25.0, places=9)

    def test_zero_reserve_leaves_the_whole_budget(self):
        allocatable, reserve = hold_reserve(100.0, 0.0)
        self.assertAlmostEqual(allocatable, 100.0, places=9)
        self.assertAlmostEqual(reserve, 0.0, places=9)

    def test_full_reserve_rejected(self):
        with self.assertRaises(ValueError):
            hold_reserve(100.0, 1.0)

    def test_zero_total_rejected(self):
        with self.assertRaises(ValueError):
            hold_reserve(0.0, 0.25)

    def test_weighted_split_is_proportional(self):
        split = allocate_by_weight(75.0, {"payload": 3.0, "platform": 2.0})
        self.assertAlmostEqual(split["payload"], 45.0, places=9)
        self.assertAlmostEqual(split["platform"], 30.0, places=9)

    def test_weighted_split_conserves_the_pot(self):
        split = allocate_by_weight(75.0, {"a": 1.0, "b": 1.0, "c": 1.0})
        self.assertAlmostEqual(sum(split.values()), 75.0, places=9)

    def test_all_zero_weights_rejected(self):
        with self.assertRaises(ValueError):
            allocate_by_weight(75.0, {"a": 0.0, "b": 0.0})

    def test_empty_weight_mapping_rejected(self):
        with self.assertRaises(ValueError):
            allocate_by_weight(75.0, {})

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            allocate_by_weight(75.0, {"a": -1.0, "b": 2.0})


class CombineTests(unittest.TestCase):
    def test_deposited_masses_add_linearly(self):
        self.assertAlmostEqual(combine_linear([12.0, 8.0, 5.0]), 25.0, places=9)

    def test_empty_linear_combination_is_zero(self):
        self.assertAlmostEqual(combine_linear([]), 0.0, places=9)

    def test_uncertainties_combine_in_quadrature(self):
        self.assertAlmostEqual(combine_quadrature([3.0, 4.0]), 5.0, places=9)

    def test_quadrature_is_never_larger_than_linear(self):
        linear = combine_linear([3.0, 4.0])
        quad = combine_quadrature([3.0, 4.0])
        self.assertLess(quad, linear)

    def test_combine_dispatches_on_method(self):
        self.assertAlmostEqual(combine([3.0, 4.0], "quadrature"), 5.0, places=9)
        self.assertAlmostEqual(combine([3.0, 4.0], "linear"), 7.0, places=9)

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            combine([1.0], "worst-case")

    def test_negative_contribution_rejected(self):
        with self.assertRaises(ValueError):
            combine_linear([1.0, -2.0])


class NodeTests(unittest.TestCase):
    def test_valid_tree_accepted(self):
        self.assertEqual(validate_node(sample_tree()), 0)

    def test_missing_allocation_rejected(self):
        tree = sample_tree()
        del tree["children"][0]["allocation"]
        with self.assertRaises(ValueError):
            validate_node(tree)

    def test_child_at_the_same_level_rejected(self):
        tree = sample_tree()
        tree["children"][0]["level"] = "system"
        with self.assertRaises(ValueError):
            validate_node(tree)

    def test_subsystem_under_a_unit_rejected(self):
        tree = sample_tree()
        tree["children"][0]["children"][0]["children"] = [
            {"name": "board", "level": "subsystem", "allocation": 1.0}
        ]
        with self.assertRaises(ValueError):
            validate_node(tree)

    def test_duplicate_sibling_name_rejected(self):
        tree = sample_tree()
        tree["children"][1]["name"] = "payload"
        with self.assertRaises(ValueError):
            validate_node(tree)

    def test_blank_node_name_rejected(self):
        tree = sample_tree()
        tree["name"] = " "
        with self.assertRaises(ValueError):
            validate_node(tree)

    def test_non_mapping_node_rejected(self):
        with self.assertRaises(ValueError):
            validate_node(["observatory"])


class RollUpTests(unittest.TestCase):
    def test_leaf_demands_its_own_allocation(self):
        leaf = {"name": "telescope", "level": "unit", "allocation": 30.0}
        self.assertAlmostEqual(roll_up(leaf), 30.0, places=9)

    def test_parent_demands_the_sum_of_its_children(self):
        tree = sample_tree()
        self.assertAlmostEqual(roll_up(tree["children"][0]), 45.0, places=9)

    def test_unspent_child_allocation_propagates_as_lower_demand(self):
        tree = sample_tree()
        self.assertAlmostEqual(roll_up(tree["children"][1]), 20.0, places=9)
        self.assertAlmostEqual(roll_up(tree), 65.0, places=9)

    def test_quadrature_roll_up_is_smaller(self):
        tree = sample_tree()
        self.assertLess(roll_up(tree, "quadrature"), roll_up(tree, "linear"))

    def test_exactly_closed_node_reports_zero_headroom(self):
        record = close_node(sample_tree()["children"][0])
        self.assertAlmostEqual(record["headroom"], 0.0, places=9)
        self.assertLessEqual(abs(record["headroom"]), CLOSURE_TOLERANCE)
        self.assertTrue(record["closed"])

    def test_over_subscribed_node_is_not_closed(self):
        tree = sample_tree()
        tree["children"][0]["children"][0]["allocation"] = 40.0
        record = close_node(tree["children"][0])
        self.assertFalse(record["closed"])
        self.assertAlmostEqual(record["demand"], 55.0, places=9)


class AssessBudgetTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "total": 100.0,
            "reserve_fraction": 0.25,
            "root": sample_tree(),
        }
        spec.update(overrides)
        return copy.deepcopy(spec) if not overrides else spec

    def test_reserve_and_allocatable_are_reported(self):
        result = assess_budget(self._spec())
        self.assertAlmostEqual(result["reserve"], 25.0, places=9)
        self.assertAlmostEqual(result["allocatable"], 75.0, places=9)

    def test_sound_tree_closes_with_no_findings(self):
        result = assess_budget(self._spec())
        self.assertTrue(result["closed"])
        self.assertEqual(result["findings"], [])

    def test_one_record_per_node(self):
        result = assess_budget(self._spec())
        self.assertEqual(len(result["records"]), 7)

    def test_root_allocation_over_the_allocatable_is_flagged(self):
        spec = self._spec()
        spec["root"]["allocation"] = 90.0
        result = assess_budget(spec)
        self.assertFalse(result["closed"])
        self.assertIn("allocatable", result["findings"][0])

    def test_unit_overrun_is_flagged_at_its_parent(self):
        spec = self._spec()
        spec["root"]["children"][0]["children"][0]["allocation"] = 40.0
        result = assess_budget(spec)
        self.assertFalse(result["closed"])
        self.assertTrue(any("payload" in f for f in result["findings"]))

    def test_largely_unallocated_node_is_reported_when_asked(self):
        spec = self._spec()
        spec["headroom_warning_fraction"] = 0.2
        result = assess_budget(spec)
        self.assertTrue(any("unallocated" in f for f in result["findings"]))

    def test_no_headroom_warning_without_a_threshold(self):
        result = assess_budget(self._spec())
        self.assertFalse(any("unallocated" in f for f in result["findings"]))

    def test_quadrature_method_is_carried_through(self):
        spec = self._spec()
        spec["method"] = "quadrature"
        self.assertEqual(assess_budget(spec)["method"], "quadrature")

    def test_unknown_method_rejected(self):
        spec = self._spec()
        spec["method"] = "envelope"
        with self.assertRaises(ValueError):
            assess_budget(spec)

    def test_missing_root_rejected(self):
        spec = self._spec()
        del spec["root"]
        with self.assertRaises(ValueError):
            assess_budget(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_budget(["total"])

    def test_reserve_at_or_above_unity_rejected(self):
        spec = self._spec()
        spec["reserve_fraction"] = 1.5
        with self.assertRaises(ValueError):
            assess_budget(spec)


if __name__ == "__main__":
    unittest.main()
