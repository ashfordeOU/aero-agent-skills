"""Contract tests for the board modification plan logic."""

import unittest

from q7028_modification_techniques_logic import (
    WIRE_AMPACITY_A,
    added_wire_budget,
    assess_added_wire,
    assess_component_change,
    assess_modification_plan,
    assess_track_cut,
    require_count,
    require_real,
    required_isolation_gap_mm,
    support_points_required,
    wire_ampacity_a,
)

GAP_TABLE = [(50.0, 0.25), (100.0, 0.40), (250.0, 0.80), (500.0, 1.50)]


class InputValidationTests(unittest.TestCase):
    def test_require_real_returns_float(self):
        self.assertAlmostEqual(require_real("x", 2), 2.0, places=9)

    def test_require_real_rejects_bool(self):
        with self.assertRaises(ValueError):
            require_real("x", True)

    def test_require_real_rejects_nan(self):
        with self.assertRaises(ValueError):
            require_real("x", float("nan"))

    def test_require_count_rejects_float(self):
        with self.assertRaises(ValueError):
            require_count("n", 1.5)


class IsolationGapTests(unittest.TestCase):
    def test_tabulated_voltage_returns_its_gap(self):
        self.assertAlmostEqual(required_isolation_gap_mm(GAP_TABLE, 100.0), 0.40,
                               places=9)

    def test_interpolated_voltage(self):
        self.assertAlmostEqual(required_isolation_gap_mm(GAP_TABLE, 75.0), 0.325,
                               places=9)

    def test_lower_edge(self):
        self.assertAlmostEqual(required_isolation_gap_mm(GAP_TABLE, 50.0), 0.25,
                               places=9)

    def test_upper_edge(self):
        self.assertAlmostEqual(required_isolation_gap_mm(GAP_TABLE, 500.0), 1.50,
                               places=9)

    def test_voltage_below_the_table_refused(self):
        with self.assertRaises(ValueError):
            required_isolation_gap_mm(GAP_TABLE, 10.0)

    def test_voltage_above_the_table_refused(self):
        with self.assertRaises(ValueError):
            required_isolation_gap_mm(GAP_TABLE, 900.0)

    def test_non_monotone_table_rejected(self):
        with self.assertRaises(ValueError):
            required_isolation_gap_mm([(100.0, 0.4), (100.0, 0.5)], 100.0)

    def test_single_point_table_rejected(self):
        with self.assertRaises(ValueError):
            required_isolation_gap_mm([(100.0, 0.4)], 100.0)


class TrackCutTests(unittest.TestCase):
    def test_clean_wide_cut_is_acceptable(self):
        self.assertTrue(assess_track_cut(1.0, 100.0, GAP_TABLE)["acceptable"])

    def test_gap_exactly_on_the_requirement_is_acceptable(self):
        result = assess_track_cut(0.40, 100.0, GAP_TABLE)
        self.assertFalse(result["gap_short"])
        self.assertTrue(result["acceptable"])

    def test_narrow_cut_is_short(self):
        result = assess_track_cut(0.20, 100.0, GAP_TABLE)
        self.assertTrue(result["gap_short"])
        self.assertFalse(result["acceptable"])

    def test_residual_copper_fails_a_wide_cut(self):
        result = assess_track_cut(2.0, 100.0, GAP_TABLE, residual_copper_mm=0.05)
        self.assertTrue(result["bridged"])
        self.assertFalse(result["acceptable"])

    def test_higher_voltage_demands_a_wider_cut(self):
        narrow = assess_track_cut(0.5, 100.0, GAP_TABLE)
        wide = assess_track_cut(0.5, 250.0, GAP_TABLE)
        self.assertTrue(narrow["acceptable"])
        self.assertFalse(wide["acceptable"])

    def test_negative_gap_rejected(self):
        with self.assertRaises(ValueError):
            assess_track_cut(-0.5, 100.0, GAP_TABLE)


class AddedWireTests(unittest.TestCase):
    def test_known_gauge_ampacity(self):
        self.assertAlmostEqual(wire_ampacity_a(24), WIRE_AMPACITY_A[24], places=9)

    def test_unknown_gauge_rejected(self):
        with self.assertRaises(ValueError):
            wire_ampacity_a(23)

    def test_non_integer_gauge_rejected(self):
        with self.assertRaises(ValueError):
            wire_ampacity_a(24.0)

    def test_short_wire_needs_no_support(self):
        self.assertEqual(support_points_required(10.0, 25.0), 0)

    def test_length_exactly_one_span_needs_no_support(self):
        self.assertEqual(support_points_required(25.0, 25.0), 0)

    def test_length_just_over_a_span_needs_one_support(self):
        self.assertEqual(support_points_required(26.0, 25.0), 1)

    def test_length_exactly_four_spans_needs_three_supports(self):
        self.assertEqual(support_points_required(100.0, 25.0), 3)

    def test_zero_span_rejected(self):
        with self.assertRaises(ValueError):
            support_points_required(100.0, 0.0)

    def test_wire_inside_its_rating_and_supported_is_acceptable(self):
        result = assess_added_wire(24, 2.0, 60.0, 25.0, 2)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["supports_required"], 2)

    def test_current_exactly_on_the_rating_is_acceptable(self):
        result = assess_added_wire(24, WIRE_AMPACITY_A[24], 10.0, 25.0, 0)
        self.assertFalse(result["over_current"])

    def test_over_current_wire_is_flagged(self):
        result = assess_added_wire(30, 3.0, 10.0, 25.0, 0)
        self.assertTrue(result["over_current"])
        self.assertFalse(result["acceptable"])

    def test_under_supported_wire_is_flagged(self):
        result = assess_added_wire(24, 1.0, 120.0, 25.0, 1)
        self.assertTrue(result["under_supported"])

    def test_extra_supports_are_not_a_finding(self):
        result = assess_added_wire(24, 1.0, 60.0, 25.0, 6)
        self.assertTrue(result["acceptable"])


class BudgetAndChangeTests(unittest.TestCase):
    def test_budget_with_room_left(self):
        state = added_wire_budget(1, 2, 6)
        self.assertFalse(state["over_budget"])
        self.assertEqual(state["total_after_plan"], 3)

    def test_budget_exactly_reached(self):
        self.assertTrue(added_wire_budget(4, 2, 6)["at_budget"])

    def test_budget_exceeded(self):
        self.assertTrue(added_wire_budget(5, 2, 6)["over_budget"])

    def test_approved_matching_change_is_acceptable(self):
        self.assertTrue(assess_component_change("R14", "ECR-4471", True)["acceptable"])

    def test_change_without_approval_is_flagged(self):
        self.assertTrue(assess_component_change("R14", None, True)["unapproved"])

    def test_blank_approval_reference_is_flagged(self):
        self.assertTrue(assess_component_change("R14", "   ", True)["unapproved"])

    def test_footprint_mismatch_is_flagged(self):
        self.assertFalse(assess_component_change("R14", "ECR-4471", False)["acceptable"])

    def test_empty_designator_rejected(self):
        with self.assertRaises(ValueError):
            assess_component_change("  ", "ECR-4471", True)

    def test_non_boolean_footprint_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_component_change("R14", "ECR-4471", "yes")


class PlanTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "gap_table": GAP_TABLE,
            "max_unsupported_span_mm": 25.0,
            "wires_already_fitted": 0,
            "max_added_wires": 6,
            "track_cuts": [
                {"reference": "CUT-1", "gap_mm": 1.0, "working_voltage_v": 100.0}
            ],
            "added_wires": [
                {"reference": "W-1", "gauge": 24, "current_a": 1.0,
                 "length_mm": 60.0, "supports_planned": 2}
            ],
            "component_changes": [
                {"reference": "R14", "approved_change_ref": "ECR-4471",
                 "footprint_matches": True}
            ],
            "recorded": True,
        }
        spec.update(overrides)
        return spec

    def test_clean_plan_is_approved(self):
        result = assess_modification_plan(self._spec())
        self.assertEqual(result["verdict"], "approve")
        self.assertEqual(result["findings"], [])

    def test_bridged_cut_rejects_the_plan(self):
        spec = self._spec()
        spec["track_cuts"][0]["residual_copper_mm"] = 0.1
        self.assertEqual(assess_modification_plan(spec)["verdict"], "reject")

    def test_over_current_wire_rejects_the_plan(self):
        spec = self._spec()
        spec["added_wires"][0]["gauge"] = 30
        spec["added_wires"][0]["current_a"] = 4.0
        self.assertEqual(assess_modification_plan(spec)["verdict"], "reject")

    def test_unapproved_change_rejects_the_plan(self):
        spec = self._spec()
        spec["component_changes"][0]["approved_change_ref"] = None
        self.assertEqual(assess_modification_plan(spec)["verdict"], "reject")

    def test_over_wire_budget_rejects_the_plan(self):
        result = assess_modification_plan(self._spec(wires_already_fitted=6))
        self.assertEqual(result["verdict"], "reject")
        self.assertTrue(result["wire_budget"]["over_budget"])

    def test_reaching_the_wire_budget_is_an_action_not_a_rejection(self):
        result = assess_modification_plan(self._spec(wires_already_fitted=5))
        self.assertEqual(result["verdict"], "plan-with-actions")

    def test_unrecorded_plan_is_rejected(self):
        self.assertEqual(assess_modification_plan(self._spec(recorded=False))["verdict"],
                         "reject")

    def test_cut_only_plan_is_accepted(self):
        result = assess_modification_plan(
            self._spec(added_wires=[], component_changes=[])
        )
        self.assertEqual(result["verdict"], "approve")
        self.assertEqual(result["added_wires"], [])

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            assess_modification_plan(
                self._spec(track_cuts=[], added_wires=[], component_changes=[])
            )

    def test_every_failing_item_is_named(self):
        spec = self._spec()
        spec["track_cuts"][0]["gap_mm"] = 0.1
        spec["component_changes"][0]["footprint_matches"] = False
        result = assess_modification_plan(spec)
        self.assertEqual(len(result["findings"]), 2)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["gap_table"]
        with self.assertRaises(ValueError):
            assess_modification_plan(spec)

    def test_malformed_wire_item_rejected(self):
        spec = self._spec()
        del spec["added_wires"][0]["gauge"]
        with self.assertRaises(ValueError):
            assess_modification_plan(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_modification_plan("plan")

    def test_non_sequence_item_group_rejected(self):
        with self.assertRaises(ValueError):
            assess_modification_plan(self._spec(track_cuts="CUT-1"))


if __name__ == "__main__":
    unittest.main()
