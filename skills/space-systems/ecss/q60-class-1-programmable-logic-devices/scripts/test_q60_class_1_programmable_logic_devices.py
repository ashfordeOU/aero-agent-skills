#!/usr/bin/env python3
"""Contract test for class 1 programmable logic device routing (offline)."""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q60_class_1_programmable_logic_devices_logic import (  # noqa: E402
    ACTIVITY_SETS,
    DEFAULT_PLD_POLICY,
    DELTA_VERIFICATION,
    DESIGN_ASSURANCE_ITEMS,
    DESIGN_AXES,
    DESIGN_ORIGINS,
    DEVICE_AXES,
    EVIDENCE_INCOMPLETE,
    FULL_DEVELOPMENT,
    IMPLEMENTATION_AXES,
    LOGIC_AXES,
    MAINTENANCE_DUTIES_BY_TECHNOLOGY,
    PLD_TECHNOLOGIES,
    REQUIRED_EVIDENCE_BY_ORIGIN,
    REVIEWED_REUSE,
    activity_set_for_route,
    assess_pld_case,
    changed_design_axes,
    coverage_shortfall_pct,
    design_assurance_gaps,
    design_delta_index,
    group_changed_axes,
    maintenance_duties,
    meets_coverage,
    route_pld_design,
    validate_build_record,
    validate_pld_policy,
)

BASELINE_BUILD = {
    "device_part_number": "PLD-A1",
    "device_technology": "antifuse-one-time",
    "device_speed_grade": "std",
    "design_source_revision": "r7",
    "functional_scope": "telemetry-formatter",
    "clock_domain_set": "clk-main",
    "synthesis_tool_version": "syn-4.2",
    "place_and_route_constraints": "con-r3",
    "pin_assignment": "pin-r3",
}

FULL_EVIDENCE = {item: True for item in DESIGN_ASSURANCE_ITEMS}

REUSE_CASE = {
    "origin": "unchanged-reuse",
    "technology": "antifuse-one-time",
    "evidence_present": dict(FULL_EVIDENCE),
    "baseline": dict(BASELINE_BUILD),
    "candidate": dict(BASELINE_BUILD),
    "achieved_coverage_pct": 99.0,
    "baseline_age_months": 12,
}


def _build(**overrides):
    record = copy.deepcopy(BASELINE_BUILD)
    record.update(overrides)
    return record


def _case(**overrides):
    case = copy.deepcopy(REUSE_CASE)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_round_trips(self):
        self.assertEqual(validate_pld_policy(None), DEFAULT_PLD_POLICY)

    def test_policy_override_is_merged(self):
        merged = validate_pld_policy({"min_functional_coverage_pct": 90.0})
        self.assertAlmostEqual(merged["min_functional_coverage_pct"], 90.0, places=9)
        self.assertEqual(
            merged["max_baseline_age_months"],
            DEFAULT_PLD_POLICY["max_baseline_age_months"],
        )

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_pld_policy({"min_coverage": 90.0})

    def test_coverage_floor_above_one_hundred_rejected(self):
        with self.assertRaises(ValueError):
            validate_pld_policy({"min_functional_coverage_pct": 101.0})

    def test_non_integer_baseline_age_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_pld_policy({"max_baseline_age_months": 60.5})

    def test_non_boolean_policy_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_pld_policy({"implementation_change_forces_delta": "yes"})


class BuildRecordTests(unittest.TestCase):
    def test_complete_record_validates(self):
        self.assertIs(validate_build_record("baseline", BASELINE_BUILD), BASELINE_BUILD)

    def test_record_missing_an_axis_rejected(self):
        broken = _build()
        del broken["pin_assignment"]
        with self.assertRaises(ValueError):
            validate_build_record("candidate", broken)

    def test_record_with_a_blank_axis_rejected(self):
        with self.assertRaises(ValueError):
            validate_build_record("candidate", _build(functional_scope="   "))

    def test_record_with_an_unset_axis_rejected(self):
        with self.assertRaises(ValueError):
            validate_build_record("candidate", _build(clock_domain_set=None))

    def test_record_with_an_unknown_technology_rejected(self):
        with self.assertRaises(ValueError):
            validate_build_record("candidate", _build(device_technology="eeprom"))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_build_record("candidate", "PLD-A1")


class AxisComparisonTests(unittest.TestCase):
    def test_identical_builds_move_no_axis(self):
        self.assertEqual(changed_design_axes(BASELINE_BUILD, _build()), ())

    def test_a_moved_axis_is_reported(self):
        changed = changed_design_axes(BASELINE_BUILD, _build(pin_assignment="pin-r4"))
        self.assertEqual(changed, ("pin_assignment",))

    def test_axis_groups_partition_the_axis_set(self):
        groups = group_changed_axes(DESIGN_AXES)
        self.assertEqual(sorted(groups["device"]), sorted(DEVICE_AXES))
        self.assertEqual(sorted(groups["logic"]), sorted(LOGIC_AXES))
        self.assertEqual(sorted(groups["implementation"]), sorted(IMPLEMENTATION_AXES))

    def test_unknown_axis_name_rejected(self):
        with self.assertRaises(ValueError):
            group_changed_axes(("package_type",))

    def test_delta_index_of_no_change_is_zero(self):
        self.assertAlmostEqual(design_delta_index(()), 0.0, places=9)

    def test_delta_index_of_every_axis_is_one(self):
        self.assertAlmostEqual(design_delta_index(DESIGN_AXES), 1.0, places=9)

    def test_delta_index_of_three_axes_is_one_third(self):
        self.assertAlmostEqual(
            design_delta_index(DEVICE_AXES), 3.0 / 9.0, places=9
        )

    def test_delta_index_counts_a_one_shot_iterable(self):
        self.assertAlmostEqual(
            design_delta_index(axis for axis in DEVICE_AXES), 3.0 / 9.0, places=9
        )


class EvidenceTests(unittest.TestCase):
    def test_full_evidence_leaves_no_gap(self):
        self.assertEqual(design_assurance_gaps("new-design", FULL_EVIDENCE), ())

    def test_missing_timing_analysis_is_a_gap_for_a_new_design(self):
        evidence = dict(FULL_EVIDENCE)
        evidence["static_timing_analysis"] = False
        self.assertIn("static_timing_analysis", design_assurance_gaps("new-design", evidence))

    def test_unchanged_reuse_needs_fewer_items(self):
        self.assertLess(
            len(REQUIRED_EVIDENCE_BY_ORIGIN["unchanged-reuse"]),
            len(REQUIRED_EVIDENCE_BY_ORIGIN["new-design"]),
        )

    def test_unchanged_reuse_still_needs_post_programming_verification(self):
        evidence = dict(FULL_EVIDENCE)
        evidence["post_programming_verification"] = False
        self.assertIn(
            "post_programming_verification",
            design_assurance_gaps("unchanged-reuse", evidence),
        )

    def test_unknown_evidence_item_rejected(self):
        with self.assertRaises(ValueError):
            design_assurance_gaps("new-design", {"vendor_brochure": True})

    def test_non_boolean_evidence_flag_rejected(self):
        with self.assertRaises(ValueError):
            design_assurance_gaps("new-design", {"static_timing_analysis": "yes"})

    def test_unknown_origin_rejected(self):
        with self.assertRaises(ValueError):
            design_assurance_gaps("inherited", FULL_EVIDENCE)


class CoverageTests(unittest.TestCase):
    def test_coverage_on_the_floor_has_no_shortfall(self):
        self.assertAlmostEqual(coverage_shortfall_pct(95.0, 95.0), 0.0, places=9)

    def test_coverage_on_the_floor_counts_as_met(self):
        self.assertTrue(meets_coverage(95.0, 95.0))

    def test_coverage_below_the_floor_reports_the_gap(self):
        self.assertAlmostEqual(coverage_shortfall_pct(90.0, 95.0), 5.0, places=9)

    def test_coverage_above_the_floor_is_not_negative(self):
        self.assertAlmostEqual(coverage_shortfall_pct(99.5, 95.0), 0.0, places=9)

    def test_coverage_above_one_hundred_rejected(self):
        with self.assertRaises(ValueError):
            coverage_shortfall_pct(101.0, 95.0)

    def test_negative_coverage_rejected(self):
        with self.assertRaises(ValueError):
            coverage_shortfall_pct(-1.0, 95.0)


class MaintenanceTests(unittest.TestCase):
    def test_every_technology_has_duties(self):
        for technology in PLD_TECHNOLOGIES:
            self.assertTrue(MAINTENANCE_DUTIES_BY_TECHNOLOGY[technology])

    def test_volatile_device_owes_a_scrubbing_provision(self):
        duties = maintenance_duties("volatile-configuration")["duties"]
        self.assertIn("configuration-scrubbing-provision", duties)

    def test_one_time_device_owes_an_approved_programming_facility(self):
        duties = maintenance_duties("antifuse-one-time")["duties"]
        self.assertIn("approved-programming-facility", duties)

    def test_reprogramming_a_one_time_device_rejected(self):
        with self.assertRaises(ValueError):
            maintenance_duties("antifuse-one-time", True)

    def test_delivered_reprogramming_against_policy_is_a_finding(self):
        result = maintenance_duties("flash-reprogrammable", True)
        self.assertTrue(result["findings"])

    def test_permitted_delivered_reprogramming_adds_duties(self):
        result = maintenance_duties(
            "flash-reprogrammable",
            True,
            {"reprogramming_after_delivery_allowed": True},
        )
        self.assertIn("delivered-reprogramming-control-procedure", result["duties"])
        self.assertEqual(result["findings"], [])

    def test_unknown_technology_rejected(self):
        with self.assertRaises(ValueError):
            maintenance_duties("mask-programmed")

    def test_non_boolean_reprogramming_flag_rejected(self):
        with self.assertRaises(ValueError):
            maintenance_duties("flash-reprogrammable", "yes")


class RoutingTests(unittest.TestCase):
    def test_new_design_routes_to_full_development(self):
        self.assertEqual(route_pld_design("new-design")["route"], FULL_DEVELOPMENT)

    def test_evidence_gap_outranks_everything(self):
        routing = route_pld_design(
            "new-design", evidence_gaps=("static_timing_analysis",)
        )
        self.assertEqual(routing["route"], EVIDENCE_INCOMPLETE)
        self.assertEqual(routing["activities"], ())

    def test_a_device_change_routes_to_full_development(self):
        routing = route_pld_design(
            "modified-reuse",
            changed_groups={
                "device": ["device_part_number"],
                "logic": [],
                "implementation": [],
            },
        )
        self.assertEqual(routing["route"], FULL_DEVELOPMENT)

    def test_a_mapping_only_change_routes_to_delta_verification(self):
        routing = route_pld_design(
            "modified-reuse",
            changed_groups={
                "device": [],
                "logic": [],
                "implementation": ["pin_assignment"],
            },
        )
        self.assertEqual(routing["route"], DELTA_VERIFICATION)

    def test_an_untouched_design_routes_to_reviewed_reuse(self):
        routing = route_pld_design(
            "unchanged-reuse",
            changed_groups={"device": [], "logic": [], "implementation": []},
        )
        self.assertEqual(routing["route"], REVIEWED_REUSE)

    def test_a_lapsed_baseline_routes_to_delta_verification(self):
        routing = route_pld_design(
            "unchanged-reuse",
            changed_groups={"device": [], "logic": [], "implementation": []},
            baseline_age_months=DEFAULT_PLD_POLICY["max_baseline_age_months"] + 1,
        )
        self.assertEqual(routing["route"], DELTA_VERIFICATION)

    def test_missing_axis_group_rejected(self):
        with self.assertRaises(ValueError):
            route_pld_design("modified-reuse", changed_groups={"device": []})

    def test_negative_baseline_age_rejected(self):
        with self.assertRaises(ValueError):
            route_pld_design("new-design", baseline_age_months=-1)

    def test_every_route_has_an_activity_set(self):
        for route in ACTIVITY_SETS:
            self.assertEqual(activity_set_for_route(route), ACTIVITY_SETS[route])

    def test_unknown_route_has_no_activity_set(self):
        with self.assertRaises(ValueError):
            activity_set_for_route("pld-waiver-flow")


class AssessmentTests(unittest.TestCase):
    def test_clean_reuse_is_routable(self):
        result = assess_pld_case(REUSE_CASE)
        self.assertEqual(result["route"], REVIEWED_REUSE)
        self.assertTrue(result["routable"])
        self.assertEqual(result["design_assurance_gaps"], ())

    def test_clean_reuse_reports_a_zero_delta_index(self):
        self.assertAlmostEqual(
            assess_pld_case(REUSE_CASE)["design_delta_index"], 0.0, places=9
        )

    def test_a_moved_logic_axis_forces_full_development(self):
        case = _case(
            origin="modified-reuse",
            candidate=_build(functional_scope="telemetry-and-command-formatter"),
        )
        result = assess_pld_case(case)
        self.assertEqual(result["route"], FULL_DEVELOPMENT)
        self.assertIn("functional_scope", result["changed_axes"])

    def test_an_unchanged_reuse_that_moved_is_a_finding(self):
        case = _case(candidate=_build(pin_assignment="pin-r4"))
        result = assess_pld_case(case)
        self.assertTrue(any("unchanged reuse" in f for f in result["findings"]))

    def test_short_coverage_is_reported_and_routed(self):
        case = _case(achieved_coverage_pct=80.0)
        result = assess_pld_case(case)
        self.assertAlmostEqual(result["coverage_shortfall_pct"], 15.0, places=9)
        self.assertFalse(result["coverage_met"])
        self.assertEqual(result["route"], DELTA_VERIFICATION)

    def test_coverage_exactly_on_the_floor_is_met(self):
        case = _case(achieved_coverage_pct=95.0)
        result = assess_pld_case(case)
        self.assertTrue(result["coverage_met"])
        self.assertAlmostEqual(result["coverage_shortfall_pct"], 0.0, places=9)

    def test_missing_evidence_blocks_routing(self):
        evidence = dict(FULL_EVIDENCE)
        evidence["post_programming_verification"] = False
        result = assess_pld_case(_case(evidence_present=evidence))
        self.assertEqual(result["route"], EVIDENCE_INCOMPLETE)
        self.assertFalse(result["routable"])

    def test_volatile_case_carries_upset_duties(self):
        case = _case(
            origin="new-design",
            technology="volatile-configuration",
            evidence_present=dict(FULL_EVIDENCE),
        )
        result = assess_pld_case(case)
        self.assertIn("upset-rate-assessment", result["maintenance_duties"])

    def test_reuse_case_without_a_baseline_rejected(self):
        case = _case()
        del case["baseline"]
        with self.assertRaises(ValueError):
            assess_pld_case(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_pld_case("unchanged-reuse")

    def test_unknown_origin_in_a_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_pld_case(_case(origin="ported"))

    def test_every_origin_is_covered_by_the_evidence_table(self):
        for origin in DESIGN_ORIGINS:
            self.assertIn(origin, REQUIRED_EVIDENCE_BY_ORIGIN)


if __name__ == "__main__":
    unittest.main()
