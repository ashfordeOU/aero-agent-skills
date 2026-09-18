"""Contract tests for the clause 5.2.1 category one hybrid manufacturer logic."""

import datetime
import unittest

from q6005_category_one_approved_line_manufacturer_logic import (
    ADMISSIBLE_APPROVAL_STATES,
    APPROVAL_STATES,
    MANDATED_PID_CONTENT,
    approval_currency,
    audit_pid_content,
    categorize_manufacturer,
    categorize_manufacturer as _categorize,
    line_identity_matches,
    normalize_line_identity,
    parse_date,
    validate_manufacturer_record,
)

ASSESS_DAY = "2026-09-18"

FULL_PID = dict((item, True) for item in MANDATED_PID_CONTENT)

APPROVED_RECORD = {
    "manufacturer": "Hybrid Microcircuits GmbH",
    "build_line": "Line-A2",
    "approved_line": "line a2",
    "approval_state": "approved",
    "approval_body": "customer",
    "approval_date": "2024-03-01",
    "approval_expiry": "2027-03-01",
}


def pid_without(*missing):
    pid = dict(FULL_PID)
    for item in missing:
        pid[item] = False
    return pid


def record_with(**overrides):
    record = dict(APPROVED_RECORD)
    record.update(overrides)
    return record


class ParseDateTests(unittest.TestCase):
    def test_iso_string_becomes_a_date(self):
        self.assertEqual(parse_date("2026-09-18"), datetime.date(2026, 9, 18))

    def test_date_instance_passes_through(self):
        day = datetime.date(2025, 1, 2)
        self.assertEqual(parse_date(day), day)

    def test_datetime_is_narrowed_to_its_day(self):
        stamp = datetime.datetime(2025, 1, 2, 13, 45)
        self.assertEqual(parse_date(stamp), datetime.date(2025, 1, 2))

    def test_blank_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("   ")

    def test_non_iso_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("01/02/2025")

    def test_impossible_day_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("2025-02-30")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date(20250102)


class LineIdentityTests(unittest.TestCase):
    def test_case_and_spacing_do_not_change_the_line(self):
        self.assertTrue(line_identity_matches("  Line A2 ", "line-a2"))

    def test_underscores_are_the_same_separator(self):
        self.assertEqual(normalize_line_identity("Line_A2"), "line-a2")

    def test_a_second_line_in_the_same_plant_is_a_different_line(self):
        self.assertFalse(line_identity_matches("Line-A2", "Line-B1"))

    def test_blank_identity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_line_identity("   ")

    def test_non_string_identity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_line_identity(7)


class ValidateRecordTests(unittest.TestCase):
    def test_normalized_record_carries_comparable_lines(self):
        normalized = validate_manufacturer_record(APPROVED_RECORD)
        self.assertEqual(normalized["build_line"], "line-a2")
        self.assertEqual(normalized["approved_line"], "line-a2")

    def test_validation_is_idempotent(self):
        once = validate_manufacturer_record(APPROVED_RECORD)
        twice = validate_manufacturer_record(once)
        self.assertEqual(once, twice)

    def test_every_state_in_the_vocabulary_is_accepted(self):
        for state in APPROVAL_STATES:
            record = record_with(approval_state=state, application_date="2026-01-05")
            self.assertEqual(validate_manufacturer_record(record)["approval_state"], state)

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_manufacturer_record(record_with(approval_state="probationary"))

    def test_missing_key_rejected(self):
        record = dict(APPROVED_RECORD)
        del record["approved_line"]
        with self.assertRaises(ValueError):
            validate_manufacturer_record(record)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_manufacturer_record(["Hybrid Microcircuits GmbH"])

    def test_empty_manufacturer_rejected(self):
        with self.assertRaises(ValueError):
            validate_manufacturer_record(record_with(manufacturer="  "))

    def test_expiry_before_grant_rejected(self):
        with self.assertRaises(ValueError):
            validate_manufacturer_record(record_with(approval_expiry="2023-01-01"))

    def test_approved_line_without_expiry_rejected(self):
        record = dict(APPROVED_RECORD)
        del record["approval_expiry"]
        with self.assertRaises(ValueError):
            validate_manufacturer_record(record)

    def test_pending_line_without_application_date_rejected(self):
        record = record_with(approval_state="pending")
        record.pop("approval_expiry", None)
        with self.assertRaises(ValueError):
            validate_manufacturer_record(record)


class PidAuditTests(unittest.TestCase):
    def test_complete_document_is_complete(self):
        audit = audit_pid_content(FULL_PID)
        self.assertTrue(audit["complete"])
        self.assertEqual(audit["missing"], [])
        self.assertAlmostEqual(audit["completeness"], 1.0, places=9)

    def test_sequence_form_is_accepted(self):
        audit = audit_pid_content(list(MANDATED_PID_CONTENT))
        self.assertTrue(audit["complete"])

    def test_missing_items_are_named_in_mandated_order(self):
        audit = audit_pid_content(pid_without("process-flow-sequence", "traceability-scheme"))
        self.assertEqual(
            audit["missing"], ["process-flow-sequence", "traceability-scheme"]
        )

    def test_completeness_is_the_present_fraction(self):
        audit = audit_pid_content(pid_without("in-process-controls", "change-control-procedure"))
        self.assertAlmostEqual(
            audit["completeness"],
            (len(MANDATED_PID_CONTENT) - 2) / float(len(MANDATED_PID_CONTENT)),
            places=9,
        )

    def test_empty_document_has_zero_completeness(self):
        audit = audit_pid_content({})
        self.assertAlmostEqual(audit["completeness"], 0.0, places=9)
        self.assertEqual(len(audit["missing"]), len(MANDATED_PID_CONTENT))

    def test_content_outside_the_mandated_set_rejected(self):
        pid = dict(FULL_PID)
        pid["marketing-brochure"] = True
        with self.assertRaises(ValueError):
            audit_pid_content(pid)

    def test_absent_document_rejected(self):
        with self.assertRaises(ValueError):
            audit_pid_content(None)

    def test_non_mapping_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            audit_pid_content("line-identification")


class ApprovalCurrencyTests(unittest.TestCase):
    def test_live_approval_is_current(self):
        currency = approval_currency(APPROVED_RECORD, ASSESS_DAY)
        self.assertTrue(currency["current"])
        self.assertEqual(
            currency["days_remaining"],
            (datetime.date(2027, 3, 1) - datetime.date(2026, 9, 18)).days,
        )

    def test_approval_expiring_on_the_assessment_day_is_still_current(self):
        currency = approval_currency(record_with(approval_expiry=ASSESS_DAY), ASSESS_DAY)
        self.assertTrue(currency["current"])
        self.assertEqual(currency["days_remaining"], 0)

    def test_lapsed_approval_is_not_current(self):
        currency = approval_currency(record_with(approval_expiry="2026-09-17"), ASSESS_DAY)
        self.assertFalse(currency["current"])
        self.assertEqual(currency["days_remaining"], -1)

    def test_open_application_is_current(self):
        record = record_with(approval_state="pending", application_date="2026-05-04")
        self.assertTrue(approval_currency(record, ASSESS_DAY)["current"])

    def test_application_dated_after_the_assessment_is_not_current(self):
        record = record_with(approval_state="pending", application_date="2026-12-01")
        self.assertFalse(approval_currency(record, ASSESS_DAY)["current"])

    def test_withdrawn_state_is_outside_the_preferred_case(self):
        record = record_with(approval_state="withdrawn")
        self.assertFalse(approval_currency(record, ASSESS_DAY)["current"])

    def test_bad_assessment_date_rejected(self):
        with self.assertRaises(ValueError):
            approval_currency(APPROVED_RECORD, "next Tuesday")


class CategorizeTests(unittest.TestCase):
    def test_approved_line_with_complete_document_is_category_one(self):
        result = categorize_manufacturer(APPROVED_RECORD, FULL_PID, ASSESS_DAY)
        self.assertEqual(result["category"], "category-1")
        self.assertTrue(result["preferred"])
        self.assertEqual(result["findings"], [])

    def test_pending_line_with_complete_document_is_category_one(self):
        record = record_with(approval_state="pending", application_date="2026-04-01")
        result = categorize_manufacturer(record, FULL_PID, ASSESS_DAY)
        self.assertEqual(result["category"], "category-1")

    def test_build_on_another_line_drops_the_preferred_case(self):
        result = categorize_manufacturer(
            record_with(build_line="Line-B1"), FULL_PID, ASSESS_DAY
        )
        self.assertFalse(result["line_match"])
        self.assertEqual(result["category"], "not-category-1")
        self.assertTrue(any("line-b1" in f for f in result["findings"]))

    def test_document_gap_drops_the_preferred_case(self):
        result = categorize_manufacturer(
            APPROVED_RECORD, pid_without("change-control-procedure"), ASSESS_DAY
        )
        self.assertFalse(result["preferred"])
        self.assertIn("change-control-procedure", " ".join(result["findings"]))

    def test_lapsed_approval_drops_the_preferred_case(self):
        result = categorize_manufacturer(
            record_with(approval_expiry="2025-01-01"), FULL_PID, ASSESS_DAY
        )
        self.assertEqual(result["category"], "not-category-1")

    def test_state_outside_the_admissible_pair_drops_the_preferred_case(self):
        for state in APPROVAL_STATES:
            record = record_with(approval_state=state, application_date="2026-04-01")
            result = _categorize(record, FULL_PID, ASSESS_DAY)
            expected = state in ADMISSIBLE_APPROVAL_STATES
            self.assertEqual(result["preferred"], expected, state)

    def test_findings_accumulate_rather_than_short_circuit(self):
        record = record_with(
            build_line="Line-C3",
            approval_date="2019-01-01",
            approval_expiry="2020-01-01",
        )
        result = categorize_manufacturer(record, pid_without("traceability-scheme"), ASSESS_DAY)
        self.assertEqual(len(result["findings"]), 3)

    def test_manufacturer_name_is_carried_through_trimmed(self):
        result = categorize_manufacturer(
            record_with(manufacturer="  Hybrid Microcircuits GmbH  "), FULL_PID, ASSESS_DAY
        )
        self.assertEqual(result["manufacturer"], "Hybrid Microcircuits GmbH")

    def test_bad_record_rejected_before_any_decision(self):
        with self.assertRaises(ValueError):
            categorize_manufacturer(record_with(approval_state="maybe"), FULL_PID, ASSESS_DAY)

    def test_missing_document_rejected(self):
        with self.assertRaises(ValueError):
            categorize_manufacturer(APPROVED_RECORD, None, ASSESS_DAY)


if __name__ == "__main__":
    unittest.main()
