#!/usr/bin/env python3
"""Contract test for nonconformance report format and fields (offline)."""

import copy
import unittest

from q1009_ncr_formats_logic import (
    ALWAYS_REQUIRED,
    DEPARTURE_DISPOSITIONS,
    DETECTION_POINTS,
    DISPOSITIONS,
    FIELD_SPEC,
    SECTIONS,
    SEVERITIES,
    STATUS_CODES,
    VERDICT_CONFORMING,
    VERDICT_NONCONFORMING,
    check_field_value,
    cross_field_findings,
    field_section,
    required_fields,
    status_sequence_ok,
    validate_ncr_form,
)

OPEN_RECORD = {
    "ncr_id": "NCR-00412",
    "originator": "inspection cell 4",
    "raised_date": "2026-02-03",
    "project": "PLATFORM-B",
    "part_number": "PN-77120",
    "serial_numbers": ["SN-014", "SN-015"],
    "quantity_affected": 2,
    "configuration_item": "CI-3020 harness assembly",
    "nonconformity_description": "backshell screws below the drawing torque value",
    "detected_at": "integration",
    "requirement_id": "REQ-EL-0440",
    "severity": "minor",
    "safety_impact": False,
    "status_code": "OPEN",
}

CLOSED_RECORD = dict(
    OPEN_RECORD,
    severity="major",
    status_code="CLOSED",
    disposition="use-as-is",
    concession_reference="CON-0091",
    corrective_action_reference="CAPA-0233",
    closure_date="2026-04-30",
)


def _record(base, **overrides):
    record = copy.deepcopy(base)
    record.update(overrides)
    return record


class FieldSpecTests(unittest.TestCase):
    def test_every_field_sits_in_a_declared_section(self):
        for name, section, _kind, _values in FIELD_SPEC:
            self.assertIn(section, SECTIONS, name)

    def test_field_section_is_reported(self):
        self.assertEqual(field_section("closure_date"), "status")

    def test_unknown_field_has_no_section(self):
        with self.assertRaises(ValueError):
            field_section("inspector_mood")

    def test_every_always_required_field_is_in_the_spec(self):
        names = {name for name, _s, _k, _v in FIELD_SPEC}
        for name in ALWAYS_REQUIRED:
            self.assertIn(name, names)


class FieldValueTests(unittest.TestCase):
    def test_report_identifier_accepted(self):
        self.assertIsNone(check_field_value("ncr_id", "NCR-00412"))

    def test_free_text_identifier_refused(self):
        self.assertIsNotNone(check_field_value("ncr_id", "the harness one"))

    def test_iso_date_accepted(self):
        self.assertIsNone(check_field_value("raised_date", "2026-02-03"))

    def test_day_first_date_refused(self):
        self.assertIsNotNone(check_field_value("raised_date", "03-02-2026"))

    def test_positive_quantity_accepted(self):
        self.assertIsNone(check_field_value("quantity_affected", 2))

    def test_zero_quantity_refused(self):
        self.assertIsNotNone(check_field_value("quantity_affected", 0))

    def test_boolean_quantity_refused(self):
        self.assertIsNotNone(check_field_value("quantity_affected", True))

    def test_flag_must_be_boolean(self):
        self.assertIsNotNone(check_field_value("safety_impact", "no"))
        self.assertIsNone(check_field_value("safety_impact", False))

    def test_serial_list_must_not_be_empty(self):
        self.assertIsNotNone(check_field_value("serial_numbers", []))

    def test_serial_list_entries_must_be_text(self):
        self.assertIsNotNone(check_field_value("serial_numbers", ["SN-014", 15]))

    def test_every_detection_point_is_accepted(self):
        for point in DETECTION_POINTS:
            self.assertIsNone(check_field_value("detected_at", point))

    def test_every_status_code_is_accepted(self):
        for code in STATUS_CODES:
            self.assertIsNone(check_field_value("status_code", code))

    def test_every_severity_is_accepted(self):
        for severity in SEVERITIES:
            self.assertIsNone(check_field_value("severity", severity))

    def test_invented_status_code_refused(self):
        self.assertIsNotNone(check_field_value("status_code", "PENDING"))

    def test_unknown_field_rejected(self):
        with self.assertRaises(ValueError):
            check_field_value("inspector_mood", "grim")


class RequiredFieldTests(unittest.TestCase):
    def test_open_minor_report_owes_the_base_set(self):
        self.assertEqual(set(required_fields(OPEN_RECORD)), set(ALWAYS_REQUIRED))

    def test_major_report_owes_an_action_reference(self):
        record = _record(OPEN_RECORD, severity="major")
        self.assertIn("corrective_action_reference", required_fields(record))

    def test_departure_disposition_owes_a_concession_reference(self):
        for disposition in DEPARTURE_DISPOSITIONS:
            record = _record(
                OPEN_RECORD, status_code="DISPOSITIONED", disposition=disposition
            )
            self.assertIn("concession_reference", required_fields(record))

    def test_rework_owes_no_concession_reference(self):
        record = _record(OPEN_RECORD, status_code="DISPOSITIONED", disposition="rework")
        self.assertNotIn("concession_reference", required_fields(record))

    def test_closed_report_owes_a_closure_date(self):
        self.assertIn("closure_date", required_fields(CLOSED_RECORD))

    def test_dispositioned_report_owes_a_disposition(self):
        record = _record(OPEN_RECORD, status_code="DISPOSITIONED")
        self.assertIn("disposition", required_fields(record))

    def test_required_fields_follow_the_form_order(self):
        required = required_fields(CLOSED_RECORD)
        order = [name for name, _s, _k, _v in FIELD_SPEC]
        self.assertEqual(list(required), [n for n in order if n in set(required)])

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            required_fields("NCR-00412")


class StatusSequenceTests(unittest.TestCase):
    def test_open_may_move_to_in_work(self):
        self.assertTrue(status_sequence_ok("OPEN", "IN-WORK"))

    def test_status_may_hold(self):
        self.assertTrue(status_sequence_ok("IN-WORK", "IN-WORK"))

    def test_closed_may_not_reopen_silently(self):
        self.assertFalse(status_sequence_ok("CLOSED", "IN-WORK"))

    def test_cancelled_is_final(self):
        self.assertFalse(status_sequence_ok("CANCELLED", "OPEN"))

    def test_a_live_report_may_be_cancelled(self):
        self.assertTrue(status_sequence_ok("IN-WORK", "CANCELLED"))

    def test_a_closed_report_may_not_be_cancelled(self):
        self.assertFalse(status_sequence_ok("CLOSED", "CANCELLED"))

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            status_sequence_ok("OPEN", "PENDING")


class CrossFieldTests(unittest.TestCase):
    def test_clean_open_record_has_no_cross_field_finding(self):
        self.assertEqual(cross_field_findings(OPEN_RECORD), ())

    def test_closure_date_on_an_open_report_is_a_finding(self):
        findings = cross_field_findings(_record(OPEN_RECORD, closure_date="2026-04-30"))
        self.assertTrue(any("not closed" in f for f in findings))

    def test_disposition_on_an_open_report_is_a_finding(self):
        findings = cross_field_findings(_record(OPEN_RECORD, disposition="rework"))
        self.assertTrue(any("still reads OPEN" in f for f in findings))

    def test_concession_against_rework_is_a_finding(self):
        record = _record(
            OPEN_RECORD,
            status_code="DISPOSITIONED",
            disposition="rework",
            concession_reference="CON-0091",
        )
        self.assertTrue(any("leaves no departure" in f for f in cross_field_findings(record)))

    def test_safety_impact_on_a_minor_report_is_a_finding(self):
        findings = cross_field_findings(_record(OPEN_RECORD, safety_impact=True))
        self.assertTrue(any("minor nonconformance" in f for f in findings))

    def test_closure_before_the_raise_date_is_a_finding(self):
        record = _record(CLOSED_RECORD, closure_date="2026-01-01")
        self.assertTrue(any("before the report was raised" in f for f in cross_field_findings(record)))

    def test_closure_on_the_raise_date_is_accepted(self):
        record = _record(CLOSED_RECORD, closure_date=CLOSED_RECORD["raised_date"])
        self.assertEqual(cross_field_findings(record), ())


class FormValidationTests(unittest.TestCase):
    def test_clean_open_record_conforms(self):
        result = validate_ncr_form(OPEN_RECORD)
        self.assertEqual(result["verdict"], VERDICT_CONFORMING)
        self.assertAlmostEqual(result["completeness"], 1.0, places=9)

    def test_clean_closed_record_conforms(self):
        self.assertTrue(validate_ncr_form(CLOSED_RECORD)["conforming"])

    def test_missing_field_is_named(self):
        record = _record(OPEN_RECORD)
        del record["requirement_id"]
        result = validate_ncr_form(record)
        self.assertIn("requirement_id", result["missing_fields"])
        self.assertEqual(result["verdict"], VERDICT_NONCONFORMING)

    def test_completeness_is_a_proportion_of_the_required_set(self):
        record = _record(OPEN_RECORD)
        del record["project"]
        result = validate_ncr_form(record)
        expected = (len(result["required_fields"]) - 1) / float(len(result["required_fields"]))
        self.assertAlmostEqual(result["completeness"], expected, places=9)

    def test_invalid_value_is_reported_without_being_missing(self):
        result = validate_ncr_form(_record(OPEN_RECORD, quantity_affected=0))
        self.assertEqual(result["missing_fields"], ())
        self.assertTrue(result["invalid_fields"])

    def test_unknown_field_is_reported(self):
        result = validate_ncr_form(_record(OPEN_RECORD, inspector_mood="grim"))
        self.assertIn("inspector_mood", result["unknown_fields"])
        self.assertFalse(result["conforming"])

    def test_optional_field_is_still_value_checked(self):
        record = _record(
            OPEN_RECORD, status_code="DISPOSITIONED", disposition="rework"
        )
        record["closure_date"] = "not-a-date"
        result = validate_ncr_form(record)
        self.assertTrue(result["invalid_fields"])

    def test_sections_report_their_own_completeness(self):
        record = _record(OPEN_RECORD)
        del record["part_number"]
        result = validate_ncr_form(record)
        self.assertFalse(result["sections"]["item-data"]["complete"])
        self.assertTrue(result["sections"]["identification"]["complete"])

    def test_every_section_appears_in_the_result(self):
        result = validate_ncr_form(OPEN_RECORD)
        for section in SECTIONS:
            self.assertIn(section, result["sections"])

    def test_closed_record_without_a_concession_is_nonconforming(self):
        record = _record(CLOSED_RECORD)
        del record["concession_reference"]
        result = validate_ncr_form(record)
        self.assertIn("concession_reference", result["missing_fields"])

    def test_every_disposition_can_appear_on_a_form(self):
        for disposition in DISPOSITIONS:
            record = _record(
                CLOSED_RECORD,
                disposition=disposition,
                concession_reference=(
                    "CON-0091" if disposition in DEPARTURE_DISPOSITIONS else None
                ),
            )
            self.assertIsInstance(validate_ncr_form(record)["conforming"], bool)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_ncr_form(["NCR-00412"])


if __name__ == "__main__":
    unittest.main()
