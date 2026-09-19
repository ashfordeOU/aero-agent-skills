#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-verification-plan-completion.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_verification_plan_completion.py
"""

import datetime
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_verification_plan_completion_logic import (  # noqa: E402
    APPROVAL_STATES,
    ENTRY_FIELDS,
    approval_rank,
    assess_plan_completion,
    completeness,
    entry_is_complete,
    is_placeholder,
    meets_completeness_threshold,
    missing_fields,
    normalize_approval,
    parse_date,
    validate_entries,
    validate_facilities,
)


def full_entry(requirement, facility="EMC chamber"):
    return {
        "requirement": requirement,
        "method": "test",
        "level": "device",
        "facility": facility,
        "success_criterion": "margin of at least 6 dB across the band",
        "schedule_slot": "2026-11 week 2",
    }


def base_plan():
    return {
        "requirements": ["R-1", "R-2"],
        "entries": [full_entry("R-1"), full_entry("R-2", "thermal bench")],
        "approval_state": "approved",
        "phase_start": "2026-09-01",
        "facilities": [
            {"name": "EMC chamber", "available_from": "2026-08-01"},
            {"name": "thermal bench", "available_from": "2026-07-15"},
        ],
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestPlaceholders(unittest.TestCase):
    def test_tbd_is_a_placeholder(self):
        self.assertTrue(is_placeholder("TBD"))

    def test_tbc_with_trailing_stop_is_a_placeholder(self):
        self.assertTrue(is_placeholder("tbc."))

    def test_to_be_defined_is_a_placeholder(self):
        self.assertTrue(is_placeholder("To Be Defined"))

    def test_a_dash_is_a_placeholder(self):
        self.assertTrue(is_placeholder(" - "))

    def test_an_empty_field_is_not_a_placeholder(self):
        self.assertFalse(is_placeholder("   "))

    def test_real_content_is_not_a_placeholder(self):
        self.assertFalse(is_placeholder("EMC chamber"))

    def test_a_non_string_field_rejected(self):
        with self.assertRaises(ValueError):
            is_placeholder(7)


class TestApproval(unittest.TestCase):
    def test_released_folds_to_approved(self):
        self.assertEqual(normalize_approval("Released"), "approved")

    def test_in_review_folds_to_under_review(self):
        self.assertEqual(normalize_approval("in review"), "under-review")

    def test_unknown_approval_rejected(self):
        with self.assertRaises(ValueError):
            normalize_approval("nearly signed")

    def test_approved_outranks_draft(self):
        self.assertGreater(approval_rank("approved"), approval_rank("draft"))

    def test_three_approval_states_are_the_whole_scale(self):
        self.assertEqual(len(APPROVAL_STATES), 3)


class TestEntryCompleteness(unittest.TestCase):
    def test_five_fields_make_an_executable_entry(self):
        self.assertEqual(len(ENTRY_FIELDS), 5)

    def test_a_full_entry_is_complete(self):
        self.assertTrue(entry_is_complete(full_entry("R-1")))

    def test_a_missing_field_is_reported(self):
        entry = full_entry("R-1")
        entry["facility"] = ""
        self.assertEqual(missing_fields(entry), ["facility"])

    def test_a_placeholder_counts_as_missing(self):
        entry = full_entry("R-1")
        entry["success_criterion"] = "TBD"
        self.assertEqual(missing_fields(entry), ["success_criterion"])
        self.assertFalse(entry_is_complete(entry))

    def test_several_gaps_are_all_reported(self):
        entry = full_entry("R-1")
        entry["level"] = ""
        entry["schedule_slot"] = "TBC"
        self.assertEqual(missing_fields(entry), ["level", "schedule_slot"])

    def test_a_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            entry_is_complete(["method"])


class TestValidation(unittest.TestCase):
    def test_entries_resolve_by_requirement(self):
        entries = validate_entries(base_plan()["entries"])
        self.assertEqual(sorted(entries), ["R-1", "R-2"])

    def test_two_entries_for_one_requirement_rejected(self):
        entries = base_plan()["entries"]
        entries.append(full_entry("R-1"))
        with self.assertRaises(ValueError):
            validate_entries(entries)

    def test_unknown_entry_key_rejected(self):
        entries = base_plan()["entries"]
        entries[0]["owner"] = "someone"
        with self.assertRaises(ValueError):
            validate_entries(entries)

    def test_entry_without_a_requirement_rejected(self):
        with self.assertRaises(ValueError):
            validate_entries([{"method": "test"}])

    def test_duplicate_facility_rejected(self):
        with self.assertRaises(ValueError):
            validate_facilities([{"name": "EMC chamber"}, {"name": "EMC chamber"}])

    def test_facility_availability_parses(self):
        facilities = validate_facilities([{"name": "bench", "available_from": "2026-08-01"}])
        self.assertEqual(facilities["bench"], datetime.date(2026, 8, 1))

    def test_a_non_date_availability_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("available_from", "summer")


class TestCompletenessArithmetic(unittest.TestCase):
    def test_a_full_plan_is_fully_complete(self):
        plan = base_plan()
        self.assertAlmostEqual(
            completeness(plan["requirements"], validate_entries(plan["entries"])), 1.0, places=9
        )

    def test_a_requirement_with_no_entry_stays_in_the_denominator(self):
        plan = base_plan()
        entries = validate_entries([full_entry("R-1")])
        self.assertAlmostEqual(completeness(plan["requirements"], entries), 0.5, places=9)

    def test_one_of_three_complete_is_a_third(self):
        entries = validate_entries([full_entry("R-1")])
        self.assertAlmostEqual(completeness(["R-1", "R-2", "R-3"], entries), 1 / 3, places=9)

    def test_completeness_needs_a_requirement(self):
        with self.assertRaises(ValueError):
            completeness([], {})

    def test_a_threshold_met_exactly_is_met(self):
        self.assertTrue(meets_completeness_threshold(2 / 4, 0.5))

    def test_a_threshold_met_by_a_third_landing_is_met(self):
        self.assertTrue(meets_completeness_threshold(1 / 3, 1 / 3))

    def test_a_threshold_missed_is_missed(self):
        self.assertFalse(meets_completeness_threshold(0.9, 1.0))

    def test_a_threshold_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            meets_completeness_threshold(0.5, 3.0)


class TestAssessPlanCompletion(unittest.TestCase):
    def test_a_complete_approved_plan_is_ready(self):
        result = assess_plan_completion(base_plan())
        self.assertEqual(result["verdict"], "ready")
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["design_phase_may_open"])

    def test_completeness_reaches_the_result(self):
        result = assess_plan_completion(base_plan())
        self.assertAlmostEqual(result["completeness"], 1.0, places=9)

    def test_a_draft_plan_is_not_ready(self):
        plan = base_plan()
        plan["approval_state"] = "draft"
        result = assess_plan_completion(plan)
        self.assertIn("plan-not-approved-at-phase-start", codes(result))
        self.assertEqual(result["verdict"], "not-ready")

    def test_a_plan_under_review_is_not_ready(self):
        plan = base_plan()
        plan["approval_state"] = "in review"
        result = assess_plan_completion(plan)
        self.assertFalse(result["design_phase_may_open"])

    def test_a_requirement_with_no_entry_is_reported(self):
        plan = base_plan()
        plan["requirements"].append("R-3")
        result = assess_plan_completion(plan)
        self.assertIn("requirement-without-entry", codes(result))
        self.assertEqual(result["incomplete_requirements"], ["R-3"])

    def test_an_incomplete_entry_is_reported_with_its_fields(self):
        plan = base_plan()
        plan["entries"][0]["schedule_slot"] = ""
        result = assess_plan_completion(plan)
        self.assertIn("entry-incomplete", codes(result))
        gap = [f for f in result["findings"] if f["code"] == "entry-incomplete"][0]
        self.assertEqual(gap["fields"], ["schedule_slot"])

    def test_a_placeholder_field_is_named(self):
        plan = base_plan()
        plan["entries"][1]["success_criterion"] = "TBD"
        result = assess_plan_completion(plan)
        self.assertIn("entry-field-carries-placeholder", codes(result))
        self.assertAlmostEqual(result["completeness"], 0.5, places=9)

    def test_an_entry_naming_an_undeclared_facility_is_reported(self):
        plan = base_plan()
        plan["entries"][0]["facility"] = "vibration rig"
        result = assess_plan_completion(plan)
        self.assertIn("entry-names-unknown-facility", codes(result))

    def test_a_facility_arriving_after_the_phase_start_is_reported(self):
        plan = base_plan()
        plan["facilities"][0]["available_from"] = "2026-10-01"
        result = assess_plan_completion(plan)
        self.assertIn("facility-not-available-at-phase-start", codes(result))

    def test_a_facility_available_on_the_phase_start_is_accepted(self):
        plan = base_plan()
        plan["facilities"][0]["available_from"] = "2026-09-01"
        result = assess_plan_completion(plan)
        self.assertNotIn("facility-not-available-at-phase-start", codes(result))

    def test_an_entry_for_an_unknown_requirement_is_reported(self):
        plan = base_plan()
        plan["entries"].append(full_entry("R-9"))
        result = assess_plan_completion(plan)
        self.assertIn("entry-for-unknown-requirement", codes(result))

    def test_a_completeness_threshold_met_exactly_does_not_fail(self):
        plan = base_plan()
        plan["completeness_threshold"] = 2 / 2
        result = assess_plan_completion(plan)
        self.assertNotIn("completeness-threshold-missed", codes(result))

    def test_a_completeness_threshold_missed_is_reported(self):
        plan = base_plan()
        plan["entries"][0]["level"] = ""
        plan["completeness_threshold"] = 0.9
        result = assess_plan_completion(plan)
        self.assertIn("completeness-threshold-missed", codes(result))

    def test_duplicate_requirement_rejected(self):
        plan = base_plan()
        plan["requirements"].append("R-1")
        with self.assertRaises(ValueError):
            assess_plan_completion(plan)

    def test_unknown_plan_key_rejected(self):
        plan = base_plan()
        plan["owner"] = "someone"
        with self.assertRaises(ValueError):
            assess_plan_completion(plan)

    def test_missing_phase_start_rejected(self):
        plan = base_plan()
        del plan["phase_start"]
        with self.assertRaises(ValueError):
            assess_plan_completion(plan)

    def test_an_empty_requirement_set_rejected(self):
        plan = base_plan()
        plan["requirements"] = []
        with self.assertRaises(ValueError):
            assess_plan_completion(plan)

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            assess_plan_completion([("entries", [])])


if __name__ == "__main__":
    unittest.main()
