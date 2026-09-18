"""Contract tests for the Annex E logbook cover page header logic."""

import unittest
from datetime import date

from q20_logbook_example_logic import (
    COVER_FIELDS,
    DEFAULT_LINES_PER_SHEET,
    MANDATORY_FIELDS,
    assess_cover_page,
    cover_body_findings,
    normalise_identifier,
    parse_day,
    render_cover,
    sheet_count,
    validate_cover,
)


def cover(**changes):
    """Return a cover page filled the way the worked example fills it."""
    base = {
        "project": "orion-payload",
        "item_name": "star-tracker-head",
        "part_number": "sth-4100-02",
        "serial_number": "sn-0031",
        "manufacturer": "optical-systems-works",
        "logbook_number": "lb-4100-0031",
        "issue": 2,
        "period_from": "2026-01-01",
        "period_to": "2026-06-30",
        "sheet_number": 1,
        "sheet_total": 1,
        "custodian": "integration-store",
    }
    for key, value in changes.items():
        if value is None and key in base:
            del base[key]
        else:
            base[key] = value
    return base


def entries(count=3, serial="sn-0031", day="2026-02-02"):
    return [{"serial_number": serial, "entry_date": day} for _ in range(count)]


class VocabularyTests(unittest.TestCase):
    def test_cover_field_order_opens_with_the_project(self):
        self.assertEqual(COVER_FIELDS[0], "project")

    def test_serial_number_is_on_the_cover(self):
        self.assertIn("serial_number", COVER_FIELDS)

    def test_mandatory_fields_are_cover_fields(self):
        self.assertTrue(set(MANDATORY_FIELDS).issubset(set(COVER_FIELDS)))

    def test_custodian_is_optional(self):
        self.assertNotIn("custodian", MANDATORY_FIELDS)

    def test_default_ruling_is_positive(self):
        self.assertGreater(DEFAULT_LINES_PER_SHEET, 1)

    def test_identifier_normalised(self):
        self.assertEqual(normalise_identifier(" SN-0031 ", "s"), "sn-0031")

    def test_day_parsed_from_iso(self):
        self.assertEqual(parse_day("2026-06-30", "d"), date(2026, 6, 30))


class ValidationTests(unittest.TestCase):
    def test_clean_cover_validates(self):
        normalised = validate_cover(cover())
        self.assertEqual(normalised["serial_number"], "sn-0031")
        self.assertEqual(normalised["period_to"], date(2026, 6, 30))

    def test_non_mapping_cover_rejected(self):
        with self.assertRaises(ValueError):
            validate_cover(["sn-0031"])

    def test_unknown_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_cover(cover(shelf_location="rack-7"))

    def test_blank_mandatory_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_cover(cover(part_number=None))

    def test_absent_custodian_accepted(self):
        normalised = validate_cover(cover(custodian=None))
        self.assertIsNone(normalised["custodian"])

    def test_zero_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_cover(cover(issue=0))

    def test_boolean_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_cover(cover(issue=True))

    def test_backwards_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_cover(cover(period_from="2026-06-30", period_to="2026-01-01"))

    def test_same_day_period_accepted(self):
        normalised = validate_cover(cover(period_from="2026-01-01", period_to="2026-01-01"))
        self.assertEqual(normalised["period_from"], normalised["period_to"])

    def test_sheet_number_beyond_the_total_rejected(self):
        with self.assertRaises(ValueError):
            validate_cover(cover(sheet_number=3, sheet_total=2))

    def test_bad_period_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_cover(cover(period_from="01/01/2026"))


class RenderingTests(unittest.TestCase):
    def test_every_field_gets_a_line(self):
        lines = render_cover(validate_cover(cover()))
        self.assertEqual(len(lines), len(COVER_FIELDS))

    def test_labels_are_aligned_to_one_column(self):
        lines = render_cover(validate_cover(cover()))
        columns = {line.index(" : ") for line in lines}
        self.assertEqual(len(columns), 1)

    def test_dates_are_printed_as_iso_days(self):
        lines = render_cover(validate_cover(cover()))
        self.assertTrue(any(line.endswith("2026-06-30") for line in lines))

    def test_absent_optional_field_prints_a_dash(self):
        lines = render_cover(validate_cover(cover(custodian=None)))
        self.assertTrue(lines[-1].endswith(": -"))

    def test_rendering_rejects_a_raw_cover(self):
        with self.assertRaises(ValueError):
            render_cover(["project"])


class SheetCountTests(unittest.TestCase):
    def test_exactly_one_full_sheet(self):
        self.assertEqual(sheet_count(DEFAULT_LINES_PER_SHEET), 1)

    def test_one_line_past_a_sheet_needs_two(self):
        self.assertEqual(sheet_count(DEFAULT_LINES_PER_SHEET + 1), 2)

    def test_an_empty_book_still_has_a_cover_sheet(self):
        self.assertEqual(sheet_count(0), 1)

    def test_custom_ruling_is_honoured(self):
        self.assertEqual(sheet_count(25, lines_per_sheet=10), 3)

    def test_negative_entry_count_rejected(self):
        with self.assertRaises(ValueError):
            sheet_count(-1)

    def test_zero_ruling_rejected(self):
        with self.assertRaises(ValueError):
            sheet_count(10, lines_per_sheet=0)


class CoverBodyTests(unittest.TestCase):
    def test_matching_cover_and_entries_are_clean(self):
        self.assertEqual(cover_body_findings(validate_cover(cover()), entries()), [])

    def test_entry_for_another_serial_is_a_finding(self):
        book = entries(1) + entries(1, serial="sn-0032")
        findings = cover_body_findings(validate_cover(cover()), book)
        self.assertIn("while the cover reads sn-0031", findings[0])

    def test_entry_before_the_period_is_a_finding(self):
        book = entries(1, day="2025-12-31")
        findings = cover_body_findings(validate_cover(cover()), book)
        self.assertIn("before the cover period opens", findings[0])

    def test_entry_after_the_period_is_a_finding(self):
        book = entries(1, day="2026-07-01")
        findings = cover_body_findings(validate_cover(cover()), book)
        self.assertIn("after the cover period closes", findings[0])

    def test_entry_on_the_closing_day_is_accepted(self):
        book = entries(1, day="2026-06-30")
        self.assertEqual(cover_body_findings(validate_cover(cover()), book), [])

    def test_wrong_sheet_total_is_a_finding(self):
        book = entries(DEFAULT_LINES_PER_SHEET + 1)
        findings = cover_body_findings(validate_cover(cover()), book)
        self.assertIn("while %d entries need 2" % (DEFAULT_LINES_PER_SHEET + 1), findings[-1])

    def test_non_sequence_entries_rejected(self):
        with self.assertRaises(ValueError):
            cover_body_findings(validate_cover(cover()), "sn-0031")

    def test_entry_without_a_serial_rejected(self):
        with self.assertRaises(ValueError):
            cover_body_findings(validate_cover(cover()), [{"entry_date": "2026-02-02"}])


class AssessmentTests(unittest.TestCase):
    def test_clean_cover_is_conformant(self):
        result = assess_cover_page(cover(), entries())
        self.assertEqual(result["verdict"], "cover-conformant")
        self.assertEqual(result["entry_count"], 3)

    def test_period_span_is_reported_in_days(self):
        result = assess_cover_page(cover(), entries())
        self.assertEqual(result["period_days"], (date(2026, 6, 30) - date(2026, 1, 1)).days)

    def test_rendered_header_travels_with_the_result(self):
        result = assess_cover_page(cover(), entries())
        self.assertEqual(len(result["rendered"]), len(COVER_FIELDS))

    def test_sheet_shortfall_makes_it_nonconformant(self):
        result = assess_cover_page(cover(), entries(DEFAULT_LINES_PER_SHEET + 5))
        self.assertEqual(result["verdict"], "cover-nonconformant")
        self.assertEqual(result["sheets_needed"], 2)

    def test_mismatched_serial_makes_it_nonconformant(self):
        result = assess_cover_page(cover(), entries(2, serial="sn-9999"))
        self.assertEqual(result["verdict"], "cover-nonconformant")

    def test_issue_is_reported_for_evidence(self):
        self.assertEqual(assess_cover_page(cover(), entries())["issue"], 2)

    def test_blank_cover_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_cover_page(cover(logbook_number=None), entries())


if __name__ == "__main__":
    unittest.main()
