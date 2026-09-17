#!/usr/bin/env python3
"""Contract test for class 2 programmable logic device maintenance (offline)."""

import copy
import unittest

from q60_class_2_programmable_logic_devices_logic import (
    ARCHIVE_ARTEFACTS,
    ARCHIVE_INCOMPLETE,
    CONFIGURATION_TECHNOLOGIES,
    DEFAULT_MAINTENANCE_POLICY,
    DELTA_VERIFICATION,
    DESIGN_BASELINES,
    DUTY_REVIEW_INTERVAL_MONTHS,
    FIELD_RECONFIGURATION_DUTY,
    FIELD_RECONFIGURATION_ON_ONE_TIME_DEVICE,
    FULL_DEVELOPMENT,
    IN_SERVICE_DUTIES,
    REPROGRAMMABLE_TECHNOLOGIES,
    REVIEWED_REUSE,
    TOOLCHAIN_NOT_REPRODUCIBLE,
    archive_completeness,
    archive_gaps,
    assess_pld_case,
    duty_review_count,
    in_service_duties,
    maintenance_schedule,
    required_artefacts,
    route_pld_design,
    toolchain_is_reproducible,
    validate_archive,
    validate_maintenance_policy,
    validate_toolchain_record,
)

TOOLCHAIN = {
    "tool_name": "SYNTH-SUITE",
    "tool_version": "12.4",
    "installer_archived": True,
    "licence_available": True,
    "supported_for_months": 36,
}


def _toolchain(**overrides):
    record = copy.deepcopy(TOOLCHAIN)
    record.update(overrides)
    return record


def _case(**overrides):
    case = {
        "technology": "flash-reprogrammable",
        "baseline": "modified-reuse",
        "archive": list(ARCHIVE_ARTEFACTS),
        "toolchain": _toolchain(),
        "mission_duration_months": 60,
        "field_reconfiguration_permitted": False,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_is_returned_when_omitted(self):
        self.assertEqual(validate_maintenance_policy(), DEFAULT_MAINTENANCE_POLICY)

    def test_unknown_policy_key_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_maintenance_policy({"archive_depth": 3})

    def test_negative_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_maintenance_policy({"toolchain_support_margin_months": -2})


class ArchiveTests(unittest.TestCase):
    def test_new_design_requires_every_artefact(self):
        self.assertEqual(required_artefacts("new-design"), ARCHIVE_ARTEFACTS)

    def test_unchanged_reuse_requires_fewer_artefacts(self):
        self.assertLess(
            len(required_artefacts("unchanged-reuse")), len(ARCHIVE_ARTEFACTS)
        )

    def test_unknown_baseline_is_rejected(self):
        with self.assertRaises(ValueError):
            required_artefacts("borrowed-bitstream")

    def test_baselines_are_the_three_declared_ones(self):
        self.assertEqual(
            DESIGN_BASELINES, ("new-design", "modified-reuse", "unchanged-reuse")
        )

    def test_unknown_artefact_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_archive(["design-source-archive", "lab-notebook"])

    def test_duplicate_artefact_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_archive(["post-route-netlist", "post-route-netlist"])

    def test_archive_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_archive("design-source-archive")

    def test_complete_archive_has_no_gaps(self):
        self.assertEqual(archive_gaps("new-design", ARCHIVE_ARTEFACTS), ())

    def test_missing_artefact_is_named_as_a_gap(self):
        held = [item for item in ARCHIVE_ARTEFACTS if item != "post-route-netlist"]
        self.assertEqual(archive_gaps("new-design", held), ("post-route-netlist",))

    def test_change_log_is_not_required_for_an_unchanged_reuse(self):
        held = [item for item in ARCHIVE_ARTEFACTS if item != "design-change-log"]
        self.assertEqual(archive_gaps("unchanged-reuse", held), ())

    def test_full_archive_is_fully_complete(self):
        self.assertAlmostEqual(
            archive_completeness("new-design", ARCHIVE_ARTEFACTS), 1.0, places=9
        )

    def test_partial_archive_is_the_plain_share(self):
        held = list(ARCHIVE_ARTEFACTS)[:6]
        self.assertAlmostEqual(
            archive_completeness("new-design", held), 6 / 8, places=9
        )

    def test_empty_archive_is_zero_complete(self):
        self.assertAlmostEqual(
            archive_completeness("new-design", []), 0.0, places=9
        )


class ToolchainTests(unittest.TestCase):
    def test_complete_record_validates(self):
        self.assertEqual(
            validate_toolchain_record(TOOLCHAIN)["tool_version"], "12.4"
        )

    def test_missing_version_is_rejected(self):
        record = _toolchain()
        del record["tool_version"]
        with self.assertRaises(ValueError):
            validate_toolchain_record(record)

    def test_non_boolean_installer_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_toolchain_record(_toolchain(installer_archived="yes"))

    def test_negative_support_window_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_toolchain_record(_toolchain(supported_for_months=-1))

    def test_archived_and_licensed_toolchain_is_reproducible(self):
        self.assertTrue(toolchain_is_reproducible(TOOLCHAIN))

    def test_unarchived_installer_is_not_reproducible(self):
        self.assertFalse(
            toolchain_is_reproducible(_toolchain(installer_archived=False))
        )

    def test_missing_licence_is_not_reproducible(self):
        self.assertFalse(
            toolchain_is_reproducible(_toolchain(licence_available=False))
        )

    def test_support_exactly_at_the_margin_is_reproducible(self):
        self.assertTrue(
            toolchain_is_reproducible(
                _toolchain(
                    supported_for_months=DEFAULT_MAINTENANCE_POLICY[
                        "toolchain_support_margin_months"
                    ]
                )
            )
        )

    def test_support_below_the_margin_is_not_reproducible(self):
        self.assertFalse(toolchain_is_reproducible(_toolchain(supported_for_months=6)))


class DutyTests(unittest.TestCase):
    def test_every_technology_carries_duties(self):
        for technology in CONFIGURATION_TECHNOLOGIES:
            self.assertGreaterEqual(len(in_service_duties(technology)), 2)

    def test_volatile_device_carries_a_reload_provision(self):
        duties = in_service_duties("sram-volatile-configuration")
        self.assertIn("configuration-reload-or-scrub-provision", duties)

    def test_one_time_device_carries_a_no_reconfiguration_control(self):
        duties = in_service_duties("antifuse-one-time-programmable")
        self.assertIn("no-field-reconfiguration-control", duties)

    def test_permitted_reconfiguration_adds_a_duty_on_a_flash_device(self):
        duties = in_service_duties("flash-reprogrammable", True)
        self.assertIn(FIELD_RECONFIGURATION_DUTY, duties)

    def test_permitted_reconfiguration_adds_nothing_to_a_one_time_device(self):
        duties = in_service_duties("antifuse-one-time-programmable", True)
        self.assertNotIn(FIELD_RECONFIGURATION_DUTY, duties)

    def test_unknown_technology_has_no_duties(self):
        with self.assertRaises(ValueError):
            in_service_duties("optical-configuration")

    def test_non_boolean_reconfiguration_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            in_service_duties("flash-reprogrammable", "yes")

    def test_every_declared_duty_has_an_interval(self):
        for technology in CONFIGURATION_TECHNOLOGIES:
            for duty in IN_SERVICE_DUTIES[technology]:
                self.assertIn(duty, DUTY_REVIEW_INTERVAL_MONTHS)

    def test_reprogrammable_list_excludes_the_one_time_device(self):
        self.assertNotIn("antifuse-one-time-programmable", REPROGRAMMABLE_TECHNOLOGIES)


class ScheduleTests(unittest.TestCase):
    def test_mission_matching_the_interval_gives_one_review(self):
        self.assertEqual(
            duty_review_count("configuration-write-protection-control", 12), 1
        )

    def test_mission_one_month_past_the_interval_rounds_up(self):
        self.assertEqual(
            duty_review_count("configuration-write-protection-control", 13), 2
        )

    def test_zero_mission_length_is_rejected(self):
        with self.assertRaises(ValueError):
            duty_review_count("configuration-write-protection-control", 0)

    def test_unknown_duty_has_no_interval(self):
        with self.assertRaises(ValueError):
            duty_review_count("coffee-break", 12)

    def test_schedule_covers_every_duty_of_the_technology(self):
        schedule = maintenance_schedule("sram-volatile-configuration", 60)
        self.assertEqual(
            len(schedule), len(IN_SERVICE_DUTIES["sram-volatile-configuration"])
        )

    def test_volatile_device_reviews_more_often_than_a_one_time_device(self):
        volatile = maintenance_schedule("sram-volatile-configuration", 60)
        one_time = maintenance_schedule("antifuse-one-time-programmable", 60)
        self.assertGreater(
            sum(entry["reviews"] for entry in volatile),
            sum(entry["reviews"] for entry in one_time),
        )


class RoutingTests(unittest.TestCase):
    def test_new_design_goes_to_the_full_flow(self):
        routing = route_pld_design("new-design", ARCHIVE_ARTEFACTS, TOOLCHAIN)
        self.assertEqual(routing["route"], FULL_DEVELOPMENT)

    def test_modified_reuse_goes_to_the_delta_flow(self):
        routing = route_pld_design("modified-reuse", ARCHIVE_ARTEFACTS, TOOLCHAIN)
        self.assertEqual(routing["route"], DELTA_VERIFICATION)

    def test_unchanged_reuse_on_a_live_toolchain_is_a_reviewed_reuse(self):
        routing = route_pld_design("unchanged-reuse", ARCHIVE_ARTEFACTS, TOOLCHAIN)
        self.assertEqual(routing["route"], REVIEWED_REUSE)

    def test_unchanged_reuse_on_a_dead_toolchain_falls_back_to_delta(self):
        routing = route_pld_design(
            "unchanged-reuse", ARCHIVE_ARTEFACTS, _toolchain(installer_archived=False)
        )
        self.assertEqual(routing["route"], DELTA_VERIFICATION)
        self.assertIn(TOOLCHAIN_NOT_REPRODUCIBLE, routing["findings"])

    def test_short_archive_blocks_every_route(self):
        held = [item for item in ARCHIVE_ARTEFACTS if item != "design-source-archive"]
        routing = route_pld_design("new-design", held, TOOLCHAIN)
        self.assertEqual(routing["route"], ARCHIVE_INCOMPLETE)
        self.assertEqual(routing["gaps"], ("design-source-archive",))


class AssessmentTests(unittest.TestCase):
    def test_clean_case_is_maintainable(self):
        result = assess_pld_case(_case())
        self.assertEqual(result["route"], DELTA_VERIFICATION)
        self.assertTrue(result["maintainable"])
        self.assertEqual(result["findings"], ())

    def test_short_archive_is_not_maintainable(self):
        held = [item for item in ARCHIVE_ARTEFACTS if item != "programming-image-checksum"]
        result = assess_pld_case(_case(archive=held))
        self.assertEqual(result["route"], ARCHIVE_INCOMPLETE)
        self.assertFalse(result["maintainable"])
        self.assertAlmostEqual(result["archive_completeness"], 7 / 8, places=9)

    def test_reconfiguration_on_a_one_time_device_is_a_finding(self):
        result = assess_pld_case(
            _case(
                technology="antifuse-one-time-programmable",
                field_reconfiguration_permitted=True,
            )
        )
        self.assertIn(FIELD_RECONFIGURATION_ON_ONE_TIME_DEVICE, result["findings"])
        self.assertFalse(result["maintainable"])

    def test_permitted_reconfiguration_adds_reviews_on_a_flash_device(self):
        plain = assess_pld_case(_case())
        permitted = assess_pld_case(_case(field_reconfiguration_permitted=True))
        self.assertGreater(permitted["total_reviews"], plain["total_reviews"])

    def test_volatile_device_reports_its_integrity_duty(self):
        result = assess_pld_case(_case(technology="sram-volatile-configuration"))
        self.assertIn(
            "configuration-memory-integrity-monitoring", result["in_service_duties"]
        )

    def test_unknown_technology_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_pld_case(_case(technology="optical-configuration"))

    def test_case_missing_a_key_is_rejected(self):
        case = _case()
        del case["toolchain"]
        with self.assertRaises(ValueError):
            assess_pld_case(case)

    def test_case_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_pld_case("flash-reprogrammable")

    def test_non_boolean_reconfiguration_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_pld_case(_case(field_reconfiguration_permitted="yes"))

    def test_total_reviews_add_up_the_schedule(self):
        result = assess_pld_case(_case())
        self.assertEqual(
            result["total_reviews"],
            sum(entry["reviews"] for entry in result["maintenance_schedule"]),
        )


if __name__ == "__main__":
    unittest.main(verbosity=0)
