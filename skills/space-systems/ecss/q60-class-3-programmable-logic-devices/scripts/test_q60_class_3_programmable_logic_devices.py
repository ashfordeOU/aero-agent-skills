#!/usr/bin/env python3
"""Contract test for the class 3 programmable logic device programme (offline)."""

import copy
import unittest

from q60_class_3_programmable_logic_devices_logic import (
    BASE_OBJECTIVES,
    CONFIGURATION_TECHNOLOGIES,
    COVERAGE_BELOW_FLOOR,
    COVERAGE_FLOORS,
    CRITICALITY_EXTRA_OBJECTIVES,
    DEFAULT_VERIFICATION_POLICY,
    DELTA_VERIFICATION,
    DESIGN_DATA_RETENTION_SHORT,
    FULL_DEVELOPMENT,
    FUNCTION_CRITICALITIES,
    MITIGATION_NOT_DECLARED,
    OBJECTIVE_NOT_PERFORMED,
    PROGRAMME_ACCEPTED,
    REPROGRAMMABLE_TECHNOLOGIES,
    REPROGRAMMING_CONTROL_MISSING,
    REVIEWED_REUSE,
    TECHNOLOGY_EXTRA_OBJECTIVES,
    TIMING_MARGIN_BELOW_FLOOR,
    TIMING_MARGIN_FLOOR,
    VERIFICATION_OBJECTIVES,
    assess_pld_programme,
    coverage_findings,
    coverage_floors,
    coverage_margins,
    meets_floor,
    missing_objectives,
    mitigation_is_required,
    required_objectives,
    required_retention_months,
    retention_findings,
    route_design,
    timing_margin,
    validate_design_record,
    validate_verification_policy,
    verification_completeness,
)

RECORD = {
    "design_id": "PLD-C3-117",
    "function_criticality": "mission-important",
    "configuration_technology": "flash-reprogrammable",
    "design_origin": "unchanged-reuse",
    "objectives_performed": [
        "requirements-traceability",
        "functional-simulation",
        "statement-coverage-measurement",
        "static-timing-analysis",
        "back-annotated-simulation",
        "single-event-mitigation-analysis",
        "reprogramming-control-procedure",
    ],
    "functional_coverage": 0.92,
    "statement_coverage": 0.86,
    "required_clock_period_ns": 20.0,
    "achieved_clock_period_ns": 16.0,
    "mitigation_declared": True,
    "mission_duration_months": 36,
    "design_data_retention_months": 60,
    "reprogramming_control_reference": "PRC-09",
}


def _record(**overrides):
    record = copy.deepcopy(RECORD)
    record.update(overrides)
    return record


def _without(objective):
    return [name for name in RECORD["objectives_performed"] if name != objective]


class PolicyTests(unittest.TestCase):
    def test_default_policy_is_returned_when_omitted(self):
        self.assertEqual(validate_verification_policy(), DEFAULT_VERIFICATION_POLICY)

    def test_unknown_policy_key_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_policy({"archive_format": "tar"})

    def test_negative_retention_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_policy({"post_mission_retention_months": -6})

    def test_policy_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_policy(24)


class RecordTests(unittest.TestCase):
    def test_complete_record_validates(self):
        validated = validate_design_record(RECORD)
        self.assertEqual(validated["design_id"], "PLD-C3-117")

    def test_unknown_criticality_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_record(_record(function_criticality="nice-to-have"))

    def test_unknown_technology_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_record(_record(configuration_technology="mask-programmed"))

    def test_unknown_origin_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_record(_record(design_origin="borrowed"))

    def test_unknown_objective_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_record(_record(objectives_performed=["lunch-review"]))

    def test_coverage_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_record(_record(functional_coverage=1.4))

    def test_zero_clock_period_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_record(_record(required_clock_period_ns=0))

    def test_non_boolean_mitigation_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_record(_record(mitigation_declared="yes"))

    def test_negative_mission_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_design_record(_record(mission_duration_months=-1))

    def test_a_blank_control_reference_reads_as_absent(self):
        validated = validate_design_record(_record(reprogramming_control_reference="  "))
        self.assertIsNone(validated["reprogramming_control_reference"])


class ObjectiveTests(unittest.TestCase):
    def test_every_criticality_and_technology_pair_owes_the_base_set(self):
        for criticality in FUNCTION_CRITICALITIES:
            for technology in CONFIGURATION_TECHNOLOGIES:
                needed = required_objectives(criticality, technology)
                for name in BASE_OBJECTIVES:
                    self.assertIn(name, needed)

    def test_every_objective_named_in_a_table_is_a_known_objective(self):
        for table in (CRITICALITY_EXTRA_OBJECTIVES, TECHNOLOGY_EXTRA_OBJECTIVES):
            for extras in table.values():
                for name in extras:
                    self.assertIn(name, VERIFICATION_OBJECTIVES)

    def test_a_critical_function_owes_more_than_a_non_critical_one(self):
        self.assertGreater(
            len(required_objectives("mission-critical", "antifuse-one-time")),
            len(required_objectives("non-critical", "antifuse-one-time")),
        )

    def test_a_volatile_part_owes_the_configuration_checks(self):
        needed = required_objectives("non-critical", "volatile-sram-configured")
        self.assertIn("power-on-configuration-check", needed)
        self.assertIn("configuration-scrubbing-design", needed)

    def test_an_antifuse_part_owes_the_programming_yield_record(self):
        self.assertIn(
            "programming-yield-record",
            required_objectives("non-critical", "antifuse-one-time"),
        )

    def test_the_required_set_never_repeats_an_objective(self):
        needed = required_objectives("mission-critical", "volatile-sram-configured")
        self.assertEqual(len(needed), len(set(needed)))

    def test_unknown_criticality_is_rejected_by_the_objective_table(self):
        with self.assertRaises(ValueError):
            required_objectives("best-effort", "antifuse-one-time")

    def test_a_complete_record_misses_nothing(self):
        self.assertEqual(missing_objectives(RECORD), ())

    def test_a_dropped_objective_is_reported(self):
        record = _record(objectives_performed=_without("back-annotated-simulation"))
        self.assertEqual(missing_objectives(record), ("back-annotated-simulation",))

    def test_completeness_is_one_when_nothing_is_missing(self):
        self.assertAlmostEqual(verification_completeness(RECORD), 1.0, places=9)

    def test_completeness_is_the_plain_share_performed(self):
        record = _record(objectives_performed=_without("back-annotated-simulation"))
        needed = len(required_objectives("mission-important", "flash-reprogrammable"))
        self.assertAlmostEqual(
            verification_completeness(record), (needed - 1) / needed, places=9
        )


class CoverageTests(unittest.TestCase):
    def test_every_criticality_names_both_floors(self):
        for criticality in FUNCTION_CRITICALITIES:
            floors = coverage_floors(criticality)
            self.assertIn("functional", floors)
            self.assertIn("statement", floors)

    def test_a_critical_function_has_the_higher_floor(self):
        self.assertGreater(
            COVERAGE_FLOORS["mission-critical"]["functional"],
            COVERAGE_FLOORS["non-critical"]["functional"],
        )

    def test_floors_are_a_copy(self):
        floors = coverage_floors("non-critical")
        floors["functional"] = 0.0
        self.assertAlmostEqual(
            COVERAGE_FLOORS["non-critical"]["functional"], 0.70, places=9
        )

    def test_a_value_on_its_floor_meets_it(self):
        self.assertTrue(meets_floor(0.80, 0.80))

    def test_a_value_just_under_its_floor_does_not_meet_it(self):
        self.assertFalse(meets_floor(0.79, 0.80))

    def test_meets_floor_rejects_a_non_numeric_value(self):
        with self.assertRaises(ValueError):
            meets_floor("high", 0.8)

    def test_coverage_above_the_floors_raises_no_finding(self):
        self.assertEqual(coverage_findings(RECORD), ())

    def test_coverage_exactly_on_the_floor_raises_no_finding(self):
        record = _record(functional_coverage=0.85, statement_coverage=0.80)
        self.assertEqual(coverage_findings(record), ())

    def test_coverage_exactly_on_the_floor_has_a_zero_margin(self):
        record = _record(statement_coverage=0.80)
        self.assertAlmostEqual(coverage_margins(record)["statement"], 0.0, places=9)

    def test_functional_coverage_under_the_floor_is_a_finding(self):
        findings = coverage_findings(_record(functional_coverage=0.60))
        self.assertEqual(findings[0]["finding"], COVERAGE_BELOW_FLOOR)
        self.assertEqual(findings[0]["subject"], "functional")

    def test_both_coverages_under_their_floors_give_two_findings(self):
        findings = coverage_findings(
            _record(functional_coverage=0.40, statement_coverage=0.30)
        )
        self.assertEqual(len(findings), 2)

    def test_a_margin_is_the_signed_distance_from_the_floor(self):
        margins = coverage_margins(RECORD)
        self.assertAlmostEqual(margins["functional"], 0.92 - 0.85, places=9)


class TimingTests(unittest.TestCase):
    def test_margin_is_the_share_of_the_period_left_standing(self):
        self.assertAlmostEqual(timing_margin(RECORD), 0.20, places=9)

    def test_a_design_exactly_at_its_required_period_has_no_margin(self):
        record = _record(achieved_clock_period_ns=20.0)
        self.assertAlmostEqual(timing_margin(record), 0.0, places=9)

    def test_a_design_past_its_required_period_has_a_negative_margin(self):
        record = _record(achieved_clock_period_ns=24.0)
        self.assertLess(timing_margin(record), 0.0)

    def test_a_margin_exactly_on_the_floor_meets_it(self):
        record = _record(required_clock_period_ns=25.0, achieved_clock_period_ns=22.0)
        margin = timing_margin(record)
        self.assertAlmostEqual(margin, TIMING_MARGIN_FLOOR["mission-important"], places=9)
        self.assertTrue(meets_floor(margin, TIMING_MARGIN_FLOOR["mission-important"]))

    def test_a_critical_function_holds_the_wider_margin(self):
        self.assertGreater(
            TIMING_MARGIN_FLOOR["mission-critical"], TIMING_MARGIN_FLOOR["non-critical"]
        )


class MitigationAndRetentionTests(unittest.TestCase):
    def test_a_critical_function_owes_a_mitigation_declaration(self):
        self.assertTrue(mitigation_is_required("mission-critical", "antifuse-one-time"))

    def test_a_non_critical_antifuse_part_owes_none(self):
        self.assertFalse(mitigation_is_required("non-critical", "antifuse-one-time"))

    def test_a_volatile_part_owes_one_whatever_the_function(self):
        self.assertTrue(
            mitigation_is_required("non-critical", "volatile-sram-configured")
        )

    def test_unknown_technology_is_rejected_by_the_mitigation_test(self):
        with self.assertRaises(ValueError):
            mitigation_is_required("non-critical", "core-rope-memory")

    def test_retention_is_the_mission_plus_the_margin(self):
        self.assertEqual(
            required_retention_months(36),
            36 + DEFAULT_VERIFICATION_POLICY["post_mission_retention_months"],
        )

    def test_a_negative_mission_length_is_rejected(self):
        with self.assertRaises(ValueError):
            required_retention_months(-4)

    def test_retention_exactly_on_the_requirement_raises_no_finding(self):
        self.assertEqual(retention_findings(RECORD), ())

    def test_short_retention_is_a_finding(self):
        findings = retention_findings(_record(design_data_retention_months=30))
        self.assertEqual(findings[0]["finding"], DESIGN_DATA_RETENTION_SHORT)

    def test_a_reprogrammable_part_without_a_control_is_a_finding(self):
        findings = retention_findings(_record(reprogramming_control_reference=None))
        self.assertEqual(findings[0]["finding"], REPROGRAMMING_CONTROL_MISSING)

    def test_a_one_time_part_needs_no_reprogramming_control(self):
        record = _record(
            configuration_technology="antifuse-one-time",
            reprogramming_control_reference=None,
            objectives_performed=[
                "requirements-traceability",
                "functional-simulation",
                "statement-coverage-measurement",
                "static-timing-analysis",
                "back-annotated-simulation",
                "single-event-mitigation-analysis",
                "programming-yield-record",
            ],
        )
        self.assertEqual(retention_findings(record), ())

    def test_every_reprogrammable_technology_is_a_known_technology(self):
        for technology in REPROGRAMMABLE_TECHNOLOGIES:
            self.assertIn(technology, CONFIGURATION_TECHNOLOGIES)


class RoutingTests(unittest.TestCase):
    def test_a_new_design_enters_the_full_flow(self):
        self.assertEqual(
            route_design(_record(design_origin="new-design"))["flow"], FULL_DEVELOPMENT
        )

    def test_a_modified_reuse_enters_the_delta_flow(self):
        self.assertEqual(
            route_design(_record(design_origin="modified-reuse"))["flow"],
            DELTA_VERIFICATION,
        )

    def test_an_unchanged_reuse_with_a_complete_set_is_a_reviewed_reuse(self):
        self.assertEqual(route_design(RECORD)["flow"], REVIEWED_REUSE)

    def test_an_unchanged_reuse_with_a_gap_falls_back_to_the_delta_flow(self):
        record = _record(objectives_performed=_without("static-timing-analysis"))
        routing = route_design(record)
        self.assertEqual(routing["flow"], DELTA_VERIFICATION)
        self.assertEqual(routing["reason"], "verification-set-incomplete")


class AssessmentTests(unittest.TestCase):
    def test_a_complete_programme_is_accepted(self):
        result = assess_pld_programme(RECORD)
        self.assertEqual(result["verdict"], PROGRAMME_ACCEPTED)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_a_missing_objective_outranks_a_coverage_gap(self):
        record = _record(
            objectives_performed=_without("back-annotated-simulation"),
            functional_coverage=0.10,
        )
        result = assess_pld_programme(record)
        self.assertEqual(result["verdict"], OBJECTIVE_NOT_PERFORMED)

    def test_a_coverage_gap_outranks_a_timing_gap(self):
        record = _record(functional_coverage=0.10, achieved_clock_period_ns=19.9)
        result = assess_pld_programme(record)
        self.assertEqual(result["verdict"], COVERAGE_BELOW_FLOOR)

    def test_a_thin_timing_margin_stops_the_programme(self):
        result = assess_pld_programme(_record(achieved_clock_period_ns=19.0))
        self.assertEqual(result["verdict"], TIMING_MARGIN_BELOW_FLOOR)
        self.assertAlmostEqual(result["timing_margin"], 0.05, places=9)

    def test_an_undeclared_mitigation_stops_the_programme(self):
        result = assess_pld_programme(_record(mitigation_declared=False))
        self.assertEqual(result["verdict"], MITIGATION_NOT_DECLARED)
        self.assertTrue(result["mitigation_required"])

    def test_a_non_critical_antifuse_part_may_leave_it_undeclared(self):
        record = _record(
            function_criticality="non-critical",
            configuration_technology="antifuse-one-time",
            mitigation_declared=False,
            objectives_performed=[
                "requirements-traceability",
                "functional-simulation",
                "statement-coverage-measurement",
                "static-timing-analysis",
                "programming-yield-record",
            ],
            reprogramming_control_reference=None,
        )
        result = assess_pld_programme(record)
        self.assertEqual(result["verdict"], PROGRAMME_ACCEPTED)
        self.assertFalse(result["mitigation_required"])

    def test_a_missing_reprogramming_control_stops_a_flash_part(self):
        result = assess_pld_programme(_record(reprogramming_control_reference=None))
        self.assertEqual(result["verdict"], REPROGRAMMING_CONTROL_MISSING)

    def test_short_retention_stops_the_programme(self):
        result = assess_pld_programme(_record(design_data_retention_months=12))
        self.assertEqual(result["verdict"], DESIGN_DATA_RETENTION_SHORT)
        self.assertEqual(result["required_retention_months"], 60)

    def test_a_longer_retention_margin_can_make_a_record_short(self):
        result = assess_pld_programme(
            RECORD, {"post_mission_retention_months": 48}
        )
        self.assertEqual(result["verdict"], DESIGN_DATA_RETENTION_SHORT)

    def test_the_reported_required_set_matches_the_tables(self):
        result = assess_pld_programme(RECORD)
        self.assertEqual(
            result["required_objectives"],
            required_objectives("mission-important", "flash-reprogrammable"),
        )

    def test_a_record_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_pld_programme("PLD-C3-117")

    def test_a_record_missing_a_field_is_rejected(self):
        record = _record()
        del record["statement_coverage"]
        with self.assertRaises(ValueError):
            assess_pld_programme(record)


if __name__ == "__main__":
    unittest.main(verbosity=0)
