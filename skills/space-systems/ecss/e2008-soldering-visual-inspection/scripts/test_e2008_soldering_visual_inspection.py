#!/usr/bin/env python3
"""Contract test for the string-termination soldering inspection (offline)."""

import copy
import unittest

from e2008_soldering_visual_inspection_logic import (
    ACCEPT,
    DEFAULT_SOLDER_CRITERIA,
    NOT_TOLERATED_ATTRIBUTES,
    REJECT,
    REWORK,
    TERMINATION_TYPES,
    assess_solder_joint,
    fillet_coverage_fraction,
    group_joints_by_termination,
    inspect_string_terminations,
    validate_solder_criteria,
    validate_workmanship_agreement,
    void_area_fraction,
)

AGREEMENT = {
    "reference": "WMS-SA-014",
    "issue": "C",
    "customer_approved": True,
    "effective_date": "2026-01-15",
}

GOOD_JOINT = {
    "id": "J-1",
    "termination_type": "string-positive-termination",
    "wetting_angle_deg": 18.0,
    "wetted_length_mm": 9.0,
    "joint_length_mm": 10.0,
    "void_area_mm2": 0.2,
    "joint_area_mm2": 10.0,
    "attributes": [],
}

CLEAN_RECORD = {
    "string_id": "SA-STRING-01",
    "inspection_date": "2026-06-02",
    "workmanship_agreement": copy.deepcopy(AGREEMENT),
    "joints": [copy.deepcopy(GOOD_JOINT)],
}


def _agreement(**overrides):
    item = copy.deepcopy(AGREEMENT)
    item.update(overrides)
    return item


def _joint(**overrides):
    item = copy.deepcopy(GOOD_JOINT)
    item.update(overrides)
    return item


def _record(joints, **overrides):
    record = copy.deepcopy(CLEAN_RECORD)
    record["joints"] = joints
    record.update(overrides)
    return record


class AgreementTests(unittest.TestCase):
    def test_a_complete_agreement_is_accepted(self):
        approved = validate_workmanship_agreement(AGREEMENT)
        self.assertEqual(approved["reference"], "WMS-SA-014")
        self.assertEqual(approved["issue"], "C")
        self.assertTrue(approved["customer_approved"])

    def test_an_unnamed_agreement_is_refused(self):
        with self.assertRaises(ValueError):
            validate_workmanship_agreement(_agreement(reference="   "))

    def test_an_agreement_without_an_issue_is_refused(self):
        broken = _agreement()
        del broken["issue"]
        with self.assertRaises(ValueError):
            validate_workmanship_agreement(broken)

    def test_an_unapproved_agreement_is_refused(self):
        with self.assertRaises(ValueError):
            validate_workmanship_agreement(_agreement(customer_approved=False))

    def test_approval_must_be_explicit_rather_than_truthy(self):
        with self.assertRaises(ValueError):
            validate_workmanship_agreement(_agreement(customer_approved="yes"))

    def test_a_missing_effective_date_is_refused(self):
        broken = _agreement()
        del broken["effective_date"]
        with self.assertRaises(ValueError):
            validate_workmanship_agreement(broken)

    def test_a_malformed_effective_date_is_refused(self):
        with self.assertRaises(ValueError):
            validate_workmanship_agreement(_agreement(effective_date="15 Jan 2026"))

    def test_an_impossible_calendar_month_is_refused(self):
        with self.assertRaises(ValueError):
            validate_workmanship_agreement(_agreement(effective_date="2026-13-01"))

    def test_an_agreement_in_force_on_the_inspection_date_is_accepted(self):
        approved = validate_workmanship_agreement(AGREEMENT, "2026-01-15")
        self.assertEqual(approved["issue"], "C")

    def test_an_agreement_taking_effect_after_the_inspection_is_refused(self):
        with self.assertRaises(ValueError):
            validate_workmanship_agreement(AGREEMENT, "2025-12-20")

    def test_a_non_mapping_agreement_is_refused(self):
        with self.assertRaises(ValueError):
            validate_workmanship_agreement("WMS-SA-014")


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_solder_criteria(DEFAULT_SOLDER_CRITERIA),
            DEFAULT_SOLDER_CRITERIA,
        )

    def test_four_not_tolerated_attributes_are_defined(self):
        self.assertEqual(len(NOT_TOLERATED_ATTRIBUTES), 4)
        self.assertIn("cold-joint", NOT_TOLERATED_ATTRIBUTES)

    def test_four_termination_types_are_defined(self):
        self.assertEqual(len(TERMINATION_TYPES), 4)

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_solder_criteria("default")

    def test_rework_angle_below_accept_angle_rejected(self):
        broken = copy.deepcopy(DEFAULT_SOLDER_CRITERIA)
        broken["rework_wetting_angle_deg"] = 10.0
        with self.assertRaises(ValueError):
            validate_solder_criteria(broken)

    def test_wetting_angle_beyond_a_half_turn_rejected(self):
        broken = copy.deepcopy(DEFAULT_SOLDER_CRITERIA)
        broken["rework_wetting_angle_deg"] = 240.0
        with self.assertRaises(ValueError):
            validate_solder_criteria(broken)

    def test_coverage_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_SOLDER_CRITERIA)
        broken["accept_fillet_coverage_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_solder_criteria(broken)

    def test_coverage_limits_running_the_wrong_way_rejected(self):
        broken = copy.deepcopy(DEFAULT_SOLDER_CRITERIA)
        broken["rework_fillet_coverage_fraction"] = 0.90
        with self.assertRaises(ValueError):
            validate_solder_criteria(broken)

    def test_rework_void_fraction_below_accept_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_SOLDER_CRITERIA)
        broken["rework_void_area_fraction"] = 0.01
        with self.assertRaises(ValueError):
            validate_solder_criteria(broken)

    def test_fractional_rework_cycle_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_SOLDER_CRITERIA)
        broken["max_rework_cycles"] = 1.5
        with self.assertRaises(ValueError):
            validate_solder_criteria(broken)


class GeometryTests(unittest.TestCase):
    def test_coverage_is_wetted_length_over_joint_length(self):
        self.assertAlmostEqual(fillet_coverage_fraction(8.0, 10.0), 0.80, places=9)

    def test_a_fully_wetted_joint_has_full_coverage(self):
        self.assertAlmostEqual(fillet_coverage_fraction(10.0, 10.0), 1.0, places=9)

    def test_wetted_length_beyond_the_joint_rejected(self):
        with self.assertRaises(ValueError):
            fillet_coverage_fraction(14.0, 10.0)

    def test_zero_joint_length_rejected(self):
        with self.assertRaises(ValueError):
            fillet_coverage_fraction(4.0, 0.0)

    def test_void_fraction_is_void_area_over_joint_area(self):
        self.assertAlmostEqual(void_area_fraction(1.0, 10.0), 0.10, places=9)

    def test_a_sound_joint_has_no_voids(self):
        self.assertAlmostEqual(void_area_fraction(0.0, 10.0), 0.0, places=9)

    def test_void_area_beyond_the_joint_rejected(self):
        with self.assertRaises(ValueError):
            void_area_fraction(12.0, 10.0)

    def test_negative_void_area_rejected(self):
        with self.assertRaises(ValueError):
            void_area_fraction(-1.0, 10.0)


class JointTests(unittest.TestCase):
    def test_a_sound_joint_is_accepted(self):
        result = assess_solder_joint(GOOD_JOINT, AGREEMENT)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_the_record_names_the_standard_it_was_graded_against(self):
        result = assess_solder_joint(GOOD_JOINT, AGREEMENT)
        self.assertEqual(result["workmanship_standard"], "WMS-SA-014 issue C")

    def test_a_joint_cannot_be_graded_without_an_agreed_standard(self):
        with self.assertRaises(ValueError):
            assess_solder_joint(GOOD_JOINT, _agreement(customer_approved=False))

    def test_wetting_angle_exactly_on_the_accept_limit_is_accepted(self):
        result = assess_solder_joint(_joint(wetting_angle_deg=30.0), AGREEMENT)
        self.assertAlmostEqual(result["wetting_angle_deg"], 30.0, places=9)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_standing_off_angle_calls_a_rework(self):
        result = assess_solder_joint(_joint(wetting_angle_deg=45.0), AGREEMENT)
        self.assertEqual(result["disposition"], REWORK)

    def test_an_angle_beyond_the_rework_limit_rejects(self):
        result = assess_solder_joint(_joint(wetting_angle_deg=90.0), AGREEMENT)
        self.assertEqual(result["disposition"], REJECT)

    def test_an_angle_beyond_a_half_turn_rejected_as_input(self):
        with self.assertRaises(ValueError):
            assess_solder_joint(_joint(wetting_angle_deg=200.0), AGREEMENT)

    def test_coverage_exactly_on_the_accept_fraction_is_accepted(self):
        result = assess_solder_joint(_joint(wetted_length_mm=7.5), AGREEMENT)
        self.assertAlmostEqual(result["fillet_coverage_fraction"], 0.75, places=9)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_thin_coverage_calls_a_rework(self):
        result = assess_solder_joint(_joint(wetted_length_mm=6.0), AGREEMENT)
        self.assertEqual(result["disposition"], REWORK)

    def test_coverage_exactly_on_the_rework_fraction_stays_reworkable(self):
        result = assess_solder_joint(_joint(wetted_length_mm=5.0), AGREEMENT)
        self.assertAlmostEqual(result["fillet_coverage_fraction"], 0.50, places=9)
        self.assertEqual(result["disposition"], REWORK)

    def test_coverage_under_the_rework_fraction_rejects(self):
        result = assess_solder_joint(_joint(wetted_length_mm=3.0), AGREEMENT)
        self.assertEqual(result["disposition"], REJECT)

    def test_void_fraction_exactly_on_the_accept_limit_is_accepted(self):
        result = assess_solder_joint(_joint(void_area_mm2=0.5), AGREEMENT)
        self.assertAlmostEqual(result["void_area_fraction"], 0.05, places=9)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_voided_joint_calls_a_rework(self):
        result = assess_solder_joint(_joint(void_area_mm2=1.5), AGREEMENT)
        self.assertEqual(result["disposition"], REWORK)

    def test_void_fraction_beyond_the_rework_limit_rejects(self):
        result = assess_solder_joint(_joint(void_area_mm2=4.0), AGREEMENT)
        self.assertEqual(result["disposition"], REJECT)

    def test_the_worst_of_the_three_measurements_governs(self):
        result = assess_solder_joint(
            _joint(wetting_angle_deg=20.0, wetted_length_mm=9.5, void_area_mm2=4.0),
            AGREEMENT,
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_a_cracked_joint_rejects_whatever_the_geometry_measures(self):
        result = assess_solder_joint(
            _joint(attributes=["cracked-joint"]), AGREEMENT
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertEqual(result["not_tolerated_attributes"], ["cracked-joint"])

    def test_a_cold_joint_rejects_on_the_attribute(self):
        result = assess_solder_joint(_joint(attributes=["cold-joint"]), AGREEMENT)
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(
            any("no acceptance figure" in reason for reason in result["reasons"])
        )

    def test_an_unknown_attribute_rejected(self):
        with self.assertRaises(ValueError):
            assess_solder_joint(_joint(attributes=["untidy"]), AGREEMENT)

    def test_a_reworkable_joint_at_its_cycle_limit_rejects_instead(self):
        result = assess_solder_joint(
            _joint(wetted_length_mm=6.0, rework_cycles=2), AGREEMENT
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(
            any("heat cycle" in reason for reason in result["reasons"])
        )

    def test_a_reworkable_joint_below_its_cycle_limit_stays_reworkable(self):
        result = assess_solder_joint(
            _joint(wetted_length_mm=6.0, rework_cycles=1), AGREEMENT
        )
        self.assertEqual(result["disposition"], REWORK)

    def test_a_negative_rework_cycle_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_solder_joint(_joint(rework_cycles=-1), AGREEMENT)

    def test_an_unknown_termination_type_rejected(self):
        with self.assertRaises(ValueError):
            assess_solder_joint(_joint(termination_type="panel-hinge"), AGREEMENT)

    def test_a_joint_without_a_joint_length_rejected(self):
        broken = _joint()
        del broken["joint_length_mm"]
        with self.assertRaises(ValueError):
            assess_solder_joint(broken, AGREEMENT)

    def test_a_non_mapping_joint_rejected(self):
        with self.assertRaises(ValueError):
            assess_solder_joint("J-1", AGREEMENT)


class GroupingTests(unittest.TestCase):
    def test_joints_group_by_termination_type(self):
        counts = group_joints_by_termination(
            [
                _joint(),
                _joint(termination_type="string-negative-termination"),
                _joint(termination_type="string-negative-termination"),
            ]
        )
        self.assertEqual(counts["string-positive-termination"], 1)
        self.assertEqual(counts["string-negative-termination"], 2)
        self.assertEqual(counts["string-to-harness-termination"], 0)

    def test_grouping_an_unknown_termination_rejected(self):
        with self.assertRaises(ValueError):
            group_joints_by_termination([_joint(termination_type="panel-hinge")])

    def test_grouping_a_non_list_rejected(self):
        with self.assertRaises(ValueError):
            group_joints_by_termination("none")


class StringInspectionTests(unittest.TestCase):
    def test_a_sound_string_is_accepted(self):
        result = inspect_string_terminations(CLEAN_RECORD)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["accept_count"], 1)
        self.assertEqual(result["workmanship_standard"], "WMS-SA-014 issue C")

    def test_string_verdict_takes_the_worst_joint(self):
        result = inspect_string_terminations(
            _record([_joint(id="A"), _joint(id="B", wetting_angle_deg=90.0)])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["reject_count"], 1)
        self.assertEqual(result["accept_count"], 1)

    def test_an_attribute_refusal_is_reported_apart_from_the_verdict(self):
        result = inspect_string_terminations(
            _record([_joint(id="A"), _joint(id="B", attributes=["dewetting"])])
        )
        self.assertEqual(result["attribute_refused_ids"], ["B"])
        self.assertTrue(
            any("attribute" in finding for finding in result["findings"])
        )

    def test_a_rework_verdict_demands_reinspection(self):
        result = inspect_string_terminations(
            _record([_joint(id="A", wetted_length_mm=6.0)])
        )
        self.assertEqual(result["verdict"], REWORK)
        self.assertTrue(result["reinspection_required"])

    def test_an_empty_survey_is_not_an_inspection(self):
        result = inspect_string_terminations(_record([]))
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(
            any("not an inspection" in finding for finding in result["findings"])
        )

    def test_a_string_graded_before_the_standard_took_effect_is_refused(self):
        with self.assertRaises(ValueError):
            inspect_string_terminations(
                _record([_joint(id="A")], inspection_date="2025-11-01")
            )

    def test_a_string_with_no_agreed_standard_is_refused(self):
        record = _record([_joint(id="A")])
        del record["workmanship_agreement"]
        with self.assertRaises(ValueError):
            inspect_string_terminations(record)

    def test_duplicate_joint_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_string_terminations(_record([_joint(id="A"), _joint(id="A")]))

    def test_string_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            inspect_string_terminations(_record([_joint(id="A")], string_id="  "))

    def test_string_with_a_non_list_survey_rejected(self):
        record = _record([])
        record["joints"] = "none"
        with self.assertRaises(ValueError):
            inspect_string_terminations(record)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            inspect_string_terminations("SA-STRING-01")

    def test_termination_counts_are_returned_with_the_verdict(self):
        result = inspect_string_terminations(
            _record(
                [
                    _joint(id="A"),
                    _joint(id="B", termination_type="string-negative-termination"),
                ]
            )
        )
        self.assertEqual(result["termination_counts"]["string-positive-termination"], 1)
        self.assertEqual(result["termination_counts"]["string-negative-termination"], 1)


if __name__ == "__main__":
    unittest.main()
