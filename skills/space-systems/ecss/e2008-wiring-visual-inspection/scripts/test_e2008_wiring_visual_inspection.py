#!/usr/bin/env python3
"""Contract test for the wiring visual inspection (offline)."""

import copy
import unittest

from e2008_wiring_visual_inspection_logic import (
    ACCEPT,
    CABLE_CATEGORIES,
    DEFAULT_WIRING_CRITERIA,
    INSPECTION_STAGES,
    POST_TEST_EXCLUDED_KINDS,
    REJECT,
    REWORK,
    WIRING_FAULT_KINDS,
    assess_wiring_fault,
    bend_radius_ratio,
    group_faults_by_kind,
    inspect_wiring,
    jacket_roundness_ratio,
    minimum_bend_radius_mm,
    twist_turns_per_m,
    validate_wiring_criteria,
)

AFTER = "after-acceptance-test"
BEFORE = "before-acceptance-test"

CABLE = {"cable_category": "unshielded-power", "outer_diameter_mm": 3.0}

CLEAN_HARNESS = {
    "harness_id": "SA-HARNESS-01",
    "stage": AFTER,
    "cable": copy.deepcopy(CABLE),
    "faults": [],
}


def _bend(**overrides):
    item = {"id": "W-BEND", "kind": "sharp-bend", "measured_radius_mm": 12.0}
    item.update(overrides)
    return item


def _twist(**overrides):
    item = {
        "id": "W-TWIST",
        "kind": "excess-twist",
        "turns": 3.0,
        "run_length_mm": 1000.0,
    }
    item.update(overrides)
    return item


def _crease(**overrides):
    item = {
        "id": "W-CREASE",
        "kind": "jacket-crease",
        "minor_axis_mm": 0.60,
        "major_axis_mm": 1.00,
    }
    item.update(overrides)
    return item


def _chafe(**overrides):
    item = {
        "id": "W-CHAFE",
        "kind": "jacket-chafe",
        "depth_mm": 0.05,
        "wall_thickness_mm": 1.0,
    }
    item.update(overrides)
    return item


def _harness(faults, **overrides):
    harness = copy.deepcopy(CLEAN_HARNESS)
    harness["faults"] = faults
    harness.update(overrides)
    return harness


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_wiring_criteria(DEFAULT_WIRING_CRITERIA),
            DEFAULT_WIRING_CRITERIA,
        )

    def test_criteria_cover_every_cable_category(self):
        for category in CABLE_CATEGORIES:
            self.assertIn(category, DEFAULT_WIRING_CRITERIA["min_bend_radius_factor"])
            self.assertIn(category, DEFAULT_WIRING_CRITERIA["max_twist_turns_per_m"])

    def test_excluded_kinds_are_real_fault_kinds(self):
        for kind in POST_TEST_EXCLUDED_KINDS:
            self.assertIn(kind, WIRING_FAULT_KINDS)

    def test_two_inspection_stages_are_defined(self):
        self.assertEqual(len(INSPECTION_STAGES), 2)

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_wiring_criteria("default")

    def test_criteria_missing_a_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_WIRING_CRITERIA)
        del broken["min_bend_radius_factor"]["coaxial-rf"]
        with self.assertRaises(ValueError):
            validate_wiring_criteria(broken)

    def test_roundness_ratio_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_WIRING_CRITERIA)
        broken["min_jacket_roundness_ratio"] = 1.5
        with self.assertRaises(ValueError):
            validate_wiring_criteria(broken)

    def test_rework_depth_below_accept_depth_rejected(self):
        broken = copy.deepcopy(DEFAULT_WIRING_CRITERIA)
        broken["rework_chafe_depth_fraction"] = 0.01
        with self.assertRaises(ValueError):
            validate_wiring_criteria(broken)

    def test_coax_needs_a_larger_bend_radius_than_plain_power_wire(self):
        self.assertLess(
            DEFAULT_WIRING_CRITERIA["min_bend_radius_factor"]["unshielded-power"],
            DEFAULT_WIRING_CRITERIA["min_bend_radius_factor"]["coaxial-rf"],
        )


class GeometryTests(unittest.TestCase):
    def test_minimum_bend_radius_scales_with_the_diameter(self):
        self.assertAlmostEqual(
            minimum_bend_radius_mm(3.0, "unshielded-power"), 18.0, places=9
        )

    def test_bend_radius_ratio_is_radius_in_diameters(self):
        self.assertAlmostEqual(bend_radius_ratio(18.0, 3.0), 6.0, places=9)

    def test_zero_diameter_rejected(self):
        with self.assertRaises(ValueError):
            minimum_bend_radius_mm(0.0, "unshielded-power")

    def test_unknown_cable_category_rejected(self):
        with self.assertRaises(ValueError):
            minimum_bend_radius_mm(3.0, "fibre-optic")

    def test_negative_bend_radius_rejected(self):
        with self.assertRaises(ValueError):
            bend_radius_ratio(-4.0, 3.0)

    def test_roundness_ratio_is_minor_over_major(self):
        self.assertAlmostEqual(jacket_roundness_ratio(0.8, 1.0), 0.8, places=9)

    def test_undeformed_jacket_is_fully_round(self):
        self.assertAlmostEqual(jacket_roundness_ratio(2.0, 2.0), 1.0, places=9)

    def test_swapped_jacket_axes_rejected(self):
        with self.assertRaises(ValueError):
            jacket_roundness_ratio(2.0, 1.0)

    def test_twist_rate_normalises_to_turns_per_metre(self):
        self.assertAlmostEqual(twist_turns_per_m(3.0, 1500.0), 2.0, places=9)

    def test_untwisted_run_has_a_zero_rate(self):
        self.assertAlmostEqual(twist_turns_per_m(0.0, 500.0), 0.0, places=9)

    def test_zero_run_length_rejected(self):
        with self.assertRaises(ValueError):
            twist_turns_per_m(1.0, 0.0)


class BendTests(unittest.TestCase):
    def test_a_bend_inside_the_minimum_radius_is_accepted(self):
        result = assess_wiring_fault(_bend(measured_radius_mm=24.0), CABLE, AFTER)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertFalse(result["post_test_excluded"])

    def test_a_radius_exactly_on_the_minimum_is_accepted(self):
        result = assess_wiring_fault(_bend(measured_radius_mm=18.0), CABLE, AFTER)
        self.assertAlmostEqual(
            result["measurements"]["min_bend_radius_mm"], 18.0, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_sharp_bend_after_acceptance_testing_is_excluded(self):
        result = assess_wiring_fault(_bend(), CABLE, AFTER)
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(result["post_test_excluded"])

    def test_the_same_sharp_bend_before_testing_is_reworkable(self):
        result = assess_wiring_fault(_bend(), CABLE, BEFORE)
        self.assertEqual(result["disposition"], REWORK)
        self.assertFalse(result["post_test_excluded"])

    def test_a_larger_cable_needs_a_larger_radius_for_the_same_bend(self):
        thick = {"cable_category": "unshielded-power", "outer_diameter_mm": 5.0}
        result = assess_wiring_fault(_bend(measured_radius_mm=24.0), thick, AFTER)
        self.assertAlmostEqual(
            result["measurements"]["min_bend_radius_mm"], 30.0, places=9
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_a_bend_without_a_radius_rejected(self):
        broken = _bend()
        del broken["measured_radius_mm"]
        with self.assertRaises(ValueError):
            assess_wiring_fault(broken, CABLE, AFTER)


class TwistTests(unittest.TestCase):
    def test_twist_within_the_lay_allowance_is_accepted(self):
        result = assess_wiring_fault(
            _twist(turns=1.0, run_length_mm=1000.0), CABLE, AFTER
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_twist_exactly_on_the_allowance_is_accepted(self):
        result = assess_wiring_fault(
            _twist(turns=2.0, run_length_mm=1000.0), CABLE, AFTER
        )
        self.assertAlmostEqual(
            result["measurements"]["twist_turns_per_m"], 2.0, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_twist_beyond_the_allowance_after_testing_is_excluded(self):
        result = assess_wiring_fault(_twist(), CABLE, AFTER)
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(result["post_test_excluded"])

    def test_shielded_cable_tolerates_less_twist_than_power_wire(self):
        shielded = {"cable_category": "shielded-signal", "outer_diameter_mm": 3.0}
        result = assess_wiring_fault(
            _twist(turns=1.5, run_length_mm=1000.0), shielded, AFTER
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_twist_without_a_run_length_rejected(self):
        broken = _twist()
        del broken["run_length_mm"]
        with self.assertRaises(ValueError):
            assess_wiring_fault(broken, CABLE, AFTER)


class CreaseAndKinkTests(unittest.TestCase):
    def test_a_round_jacket_is_accepted(self):
        result = assess_wiring_fault(
            _crease(minor_axis_mm=0.95, major_axis_mm=1.0), CABLE, AFTER
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_roundness_exactly_on_the_minimum_is_accepted(self):
        result = assess_wiring_fault(
            _crease(minor_axis_mm=0.85, major_axis_mm=1.0), CABLE, AFTER
        )
        self.assertAlmostEqual(
            result["measurements"]["jacket_roundness_ratio"], 0.85, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_crease_after_acceptance_testing_is_excluded(self):
        result = assess_wiring_fault(_crease(), CABLE, AFTER)
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(result["post_test_excluded"])
        self.assertTrue(
            any("permanent set" in reason for reason in result["reasons"])
        )

    def test_the_same_crease_before_testing_is_reworkable(self):
        result = assess_wiring_fault(_crease(), CABLE, BEFORE)
        self.assertEqual(result["disposition"], REWORK)

    def test_a_crease_without_both_axes_rejected(self):
        broken = _crease()
        del broken["major_axis_mm"]
        with self.assertRaises(ValueError):
            assess_wiring_fault(broken, CABLE, AFTER)

    def test_a_kink_after_testing_is_excluded_without_a_measurement(self):
        result = assess_wiring_fault(
            {"id": "W-KINK", "kind": "conductor-kink"}, CABLE, AFTER
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(result["post_test_excluded"])


class GradedFaultTests(unittest.TestCase):
    def test_a_shallow_chafe_is_accepted(self):
        result = assess_wiring_fault(_chafe(), CABLE, AFTER)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertFalse(result["post_test_excluded"])

    def test_chafe_exactly_on_the_accept_limit_is_accepted(self):
        result = assess_wiring_fault(_chafe(depth_mm=0.10), CABLE, AFTER)
        self.assertAlmostEqual(
            result["measurements"]["depth_fraction"], 0.10, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_deeper_chafe_is_reworkable(self):
        result = assess_wiring_fault(_chafe(depth_mm=0.30), CABLE, AFTER)
        self.assertEqual(result["disposition"], REWORK)

    def test_chafe_through_most_of_the_wall_rejects(self):
        result = assess_wiring_fault(_chafe(depth_mm=0.60), CABLE, AFTER)
        self.assertEqual(result["disposition"], REJECT)

    def test_a_nick_is_held_to_a_tighter_limit_than_a_chafe(self):
        result = assess_wiring_fault(
            _chafe(kind="insulation-nick", depth_mm=0.08), CABLE, AFTER
        )
        self.assertEqual(result["disposition"], REWORK)

    def test_a_supported_span_is_accepted(self):
        result = assess_wiring_fault(
            {"id": "W-SPAN", "kind": "unsupported-span", "span_mm": 120.0},
            CABLE,
            AFTER,
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_span_exactly_on_the_tie_down_limit_is_accepted(self):
        result = assess_wiring_fault(
            {"id": "W-SPAN", "kind": "unsupported-span", "span_mm": 150.0},
            CABLE,
            AFTER,
        )
        self.assertAlmostEqual(result["measurements"]["span_mm"], 150.0, places=9)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_long_span_rejects_rather_than_reworks(self):
        result = assess_wiring_fault(
            {"id": "W-SPAN", "kind": "unsupported-span", "span_mm": 500.0},
            CABLE,
            AFTER,
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_unknown_fault_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_wiring_fault({"kind": "frayed"}, CABLE, AFTER)

    def test_unknown_stage_rejected(self):
        with self.assertRaises(ValueError):
            assess_wiring_fault(_chafe(), CABLE, "after-launch")

    def test_non_mapping_fault_rejected(self):
        with self.assertRaises(ValueError):
            assess_wiring_fault("sharp-bend", CABLE, AFTER)

    def test_non_mapping_cable_rejected(self):
        with self.assertRaises(ValueError):
            assess_wiring_fault(_chafe(), "unshielded-power", AFTER)


class GroupingTests(unittest.TestCase):
    def test_faults_group_by_kind(self):
        result = group_faults_by_kind([_bend(), _bend(), _chafe()])
        self.assertEqual(result["counts"]["sharp-bend"], 2)
        self.assertEqual(result["counts"]["jacket-chafe"], 1)
        self.assertEqual(result["exclusion_candidate_count"], 2)

    def test_graded_faults_are_not_exclusion_candidates(self):
        result = group_faults_by_kind([_chafe()])
        self.assertEqual(result["exclusion_candidate_count"], 0)

    def test_grouping_an_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            group_faults_by_kind([{"kind": "frayed"}])

    def test_grouping_a_non_list_rejected(self):
        with self.assertRaises(ValueError):
            group_faults_by_kind("none")


class HarnessInspectionTests(unittest.TestCase):
    def test_clean_harness_is_accepted_with_a_record(self):
        result = inspect_wiring(CLEAN_HARNESS)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["reject_count"], 0)
        self.assertTrue(any("clean" in finding for finding in result["findings"]))

    def test_harness_verdict_takes_the_worst_fault(self):
        result = inspect_wiring(
            _harness([_chafe(id="A"), _chafe(id="B", depth_mm=0.60)])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["reject_count"], 1)
        self.assertEqual(result["accept_count"], 1)

    def test_one_sharp_bend_after_testing_condemns_the_harness(self):
        result = inspect_wiring(_harness([_chafe(id="A"), _bend(id="B")]))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["post_test_excluded_ids"], ["B"])
        self.assertTrue(
            any("excluded" in finding for finding in result["findings"])
        )

    def test_the_same_harness_before_testing_is_reworkable(self):
        result = inspect_wiring(
            _harness([_chafe(id="A"), _bend(id="B")], stage=BEFORE)
        )
        self.assertEqual(result["verdict"], REWORK)
        self.assertEqual(result["post_test_excluded_ids"], [])

    def test_a_rework_after_testing_demands_a_retest(self):
        result = inspect_wiring(_harness([_chafe(id="A", depth_mm=0.30)]))
        self.assertEqual(result["verdict"], REWORK)
        self.assertTrue(result["retest_required"])
        self.assertTrue(result["reinspection_required"])

    def test_a_rework_before_testing_needs_no_retest(self):
        result = inspect_wiring(
            _harness([_chafe(id="A", depth_mm=0.30)], stage=BEFORE)
        )
        self.assertFalse(result["retest_required"])
        self.assertTrue(result["reinspection_required"])

    def test_accepted_harness_needs_no_reinspection(self):
        self.assertFalse(inspect_wiring(CLEAN_HARNESS)["reinspection_required"])

    def test_duplicate_fault_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_wiring(_harness([_chafe(id="A"), _chafe(id="A")]))

    def test_harness_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            inspect_wiring(_harness([], harness_id="  "))

    def test_harness_without_a_stage_rejected(self):
        harness = copy.deepcopy(CLEAN_HARNESS)
        del harness["stage"]
        with self.assertRaises(ValueError):
            inspect_wiring(harness)

    def test_harness_without_a_cable_rejected(self):
        harness = copy.deepcopy(CLEAN_HARNESS)
        del harness["cable"]
        with self.assertRaises(ValueError):
            inspect_wiring(harness)

    def test_harness_with_a_non_list_survey_rejected(self):
        harness = copy.deepcopy(CLEAN_HARNESS)
        harness["faults"] = "none"
        with self.assertRaises(ValueError):
            inspect_wiring(harness)

    def test_non_mapping_harness_rejected(self):
        with self.assertRaises(ValueError):
            inspect_wiring("SA-HARNESS-01")


if __name__ == "__main__":
    unittest.main()
