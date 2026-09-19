"""Contract tests for the certificate of conformity sheet-format logic."""

import unittest

from q20_coc_example_logic import (
    BLOCK_ORDER,
    MANDATORY_FIELDS,
    assess_certificate_sheet,
    date_findings,
    format_certificate_number,
    normalise_identifier,
    number_findings,
    overlap_findings,
    parse_day,
    parse_serial_range,
    parse_serial_ranges,
    quantity_findings,
    render_sheet,
    serial_count,
    validate_sheet,
)


def _sheet(**overrides):
    sheet = {
        "certificate_number": "COC-4000123456-0007",
        "supplier_name": "Orbital Mechanisms Division",
        "contract_reference": "4000123456",
        "item_designation": "latch-actuator",
        "part_number": "LA-220-03",
        "serial_ranges": ["SN0007-SN0012"],
        "quantity": 6,
        "specification_reference": "SPEC-LA-220 issue 4",
        "conformity_statement": "conforms-with-listed-deviations",
        "issue_date": "2026-04-14",
        "signatory_name": "quality manager on duty",
        "signatory_function": "product-assurance",
    }
    sheet.update(overrides)
    return sheet


class NormaliseIdentifierTests(unittest.TestCase):
    def test_trims_and_lowercases(self):
        self.assertEqual(normalise_identifier(" SN0007 ", "serial"), "sn0007")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier("  ", "serial")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(7, "serial")


class ParseDayTests(unittest.TestCase):
    def test_iso_day_parsed(self):
        self.assertEqual(parse_day("2026-04-14", "issue_date"), (2026, 4, 14))

    def test_leap_day_accepted(self):
        self.assertEqual(parse_day("2024-02-29", "issue_date"), (2024, 2, 29))

    def test_non_leap_day_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("2026-02-29", "issue_date")

    def test_century_leap_rule_applied(self):
        self.assertEqual(parse_day("2000-02-29", "issue_date"), (2000, 2, 29))

    def test_month_thirteen_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("2026-13-01", "issue_date")

    def test_free_text_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("14 April 2026", "issue_date")


class ParseSerialRangeTests(unittest.TestCase):
    def test_single_serial_is_a_range_of_one(self):
        entry = parse_serial_range("SN0007")
        self.assertEqual(entry["first"], 7)
        self.assertEqual(entry["last"], 7)
        self.assertEqual(serial_count(entry), 1)

    def test_range_parsed(self):
        entry = parse_serial_range("SN0007-SN0012")
        self.assertEqual(entry["prefix"], "sn")
        self.assertEqual(serial_count(entry), 6)

    def test_spaced_range_parsed(self):
        self.assertEqual(serial_count(parse_serial_range("SN0007 - SN0012")), 6)

    def test_bare_second_serial_accepted(self):
        self.assertEqual(serial_count(parse_serial_range("sn0007-0009")), 3)

    def test_mixed_prefix_rejected(self):
        with self.assertRaises(ValueError):
            parse_serial_range("SN0007-XY0012")

    def test_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            parse_serial_range("SN0012-SN0007")

    def test_inconsistent_padding_rejected(self):
        with self.assertRaises(ValueError):
            parse_serial_range("SN0007-SN12")

    def test_unnumbered_serial_rejected(self):
        with self.assertRaises(ValueError):
            parse_serial_range("SN-SPARE")

    def test_serial_count_rejects_a_non_range(self):
        with self.assertRaises(ValueError):
            serial_count({"prefix": "sn"})

    def test_empty_range_list_rejected(self):
        with self.assertRaises(ValueError):
            parse_serial_ranges([])

    def test_range_list_keeps_printed_order(self):
        entries = parse_serial_ranges(["SN0020", "SN0007-SN0012"])
        self.assertEqual(entries[0]["first"], 20)


class OverlapTests(unittest.TestCase):
    def test_disjoint_ranges_are_silent(self):
        entries = parse_serial_ranges(["SN0007-SN0012", "SN0020-SN0021"])
        self.assertEqual(overlap_findings(entries), [])

    def test_touching_ranges_are_silent(self):
        entries = parse_serial_ranges(["SN0007-SN0012", "SN0013-SN0014"])
        self.assertEqual(overlap_findings(entries), [])

    def test_overlapping_ranges_reported(self):
        entries = parse_serial_ranges(["SN0007-SN0012", "SN0010-SN0014"])
        self.assertEqual(len(overlap_findings(entries)), 1)

    def test_same_numbers_under_different_prefixes_are_silent(self):
        entries = parse_serial_ranges(["SN0007-SN0012", "XY0007-XY0012"])
        self.assertEqual(overlap_findings(entries), [])


class QuantityTests(unittest.TestCase):
    def test_matching_quantity_is_silent(self):
        entries = parse_serial_ranges(["SN0007-SN0012"])
        self.assertEqual(quantity_findings(entries, 6), [])

    def test_quantity_summed_across_ranges(self):
        entries = parse_serial_ranges(["SN0007-SN0012", "SN0020"])
        self.assertEqual(quantity_findings(entries, 7), [])

    def test_mismatched_quantity_reported(self):
        entries = parse_serial_ranges(["SN0007-SN0012"])
        self.assertEqual(len(quantity_findings(entries, 5)), 1)

    def test_zero_quantity_rejected(self):
        entries = parse_serial_ranges(["SN0007"])
        with self.assertRaises(ValueError):
            quantity_findings(entries, 0)

    def test_float_quantity_rejected(self):
        entries = parse_serial_ranges(["SN0007"])
        with self.assertRaises(ValueError):
            quantity_findings(entries, 1.0)


class CertificateNumberTests(unittest.TestCase):
    def test_number_built_from_the_pattern(self):
        self.assertEqual(
            format_certificate_number("4000123456", 7), "coc-4000123456-0007"
        )

    def test_sequence_is_zero_padded(self):
        self.assertTrue(format_certificate_number("c1", 42).endswith("-0042"))

    def test_sequence_beyond_the_field_rejected(self):
        with self.assertRaises(ValueError):
            format_certificate_number("c1", 10000)

    def test_matching_printed_number_is_silent(self):
        self.assertEqual(number_findings("COC-4000123456-0007", "4000123456", 7), [])

    def test_wrong_printed_number_reported(self):
        self.assertEqual(
            len(number_findings("COC-4000123456-0009", "4000123456", 7)), 1
        )


class DateFindingTests(unittest.TestCase):
    def test_sheet_dated_before_presentation_is_silent(self):
        self.assertEqual(date_findings("2026-04-14", "2026-04-20"), [])

    def test_sheet_dated_on_the_day_is_silent(self):
        self.assertEqual(date_findings("2026-04-20", "2026-04-20"), [])

    def test_post_dated_sheet_reported(self):
        self.assertEqual(len(date_findings("2026-05-01", "2026-04-20")), 1)

    def test_post_dated_by_one_day_reported(self):
        self.assertEqual(len(date_findings("2026-04-21", "2026-04-20")), 1)


class ValidateSheetTests(unittest.TestCase):
    def test_full_sheet_has_no_blanks(self):
        self.assertEqual(validate_sheet(_sheet())["blanks"], [])

    def test_blank_mandatory_block_named(self):
        validated = validate_sheet(_sheet(signatory_name="   "))
        self.assertEqual(validated["blanks"], ["signatory_name"])

    def test_absent_mandatory_block_named(self):
        sheet = _sheet()
        del sheet["part_number"]
        self.assertEqual(validate_sheet(sheet)["blanks"], ["part_number"])

    def test_optional_block_may_be_absent(self):
        sheet = _sheet()
        del sheet["specification_reference"]
        self.assertEqual(validate_sheet(sheet)["blanks"], [])

    def test_every_mandatory_field_is_a_printed_block(self):
        for field in MANDATORY_FIELDS:
            self.assertIn(field, BLOCK_ORDER)

    def test_bad_issue_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_sheet(_sheet(issue_date="14/04/2026"))

    def test_non_mapping_sheet_rejected(self):
        with self.assertRaises(ValueError):
            validate_sheet(["certificate_number"])


class RenderTests(unittest.TestCase):
    def test_one_line_per_block_in_order(self):
        record = validate_sheet(_sheet())["fields"]
        lines = render_sheet(record)
        self.assertEqual(len(lines), len(BLOCK_ORDER))
        self.assertTrue(lines[0].startswith("certificate number:"))

    def test_blank_block_prints_as_blank(self):
        record = validate_sheet(_sheet(specification_reference=None))["fields"]
        self.assertTrue(any("<blank>" in line for line in render_sheet(record)))

    def test_range_printed_back_in_range_form(self):
        record = validate_sheet(_sheet())["fields"]
        lines = render_sheet(record)
        self.assertTrue(any("sn0007-sn0012" in line for line in lines))

    def test_single_serial_printed_without_a_dash(self):
        record = validate_sheet(_sheet(serial_ranges=["SN0007"], quantity=1))["fields"]
        line = [l for l in render_sheet(record) if l.startswith("serial ranges:")][0]
        self.assertEqual(line, "serial ranges: sn0007")

    def test_render_is_deterministic(self):
        record = validate_sheet(_sheet())["fields"]
        self.assertEqual(render_sheet(record), render_sheet(record))


class AssessCertificateSheetTests(unittest.TestCase):
    def test_conforming_sheet_passes(self):
        result = assess_certificate_sheet(_sheet(), 7, "2026-04-20")
        self.assertEqual(result["verdict"], "sheet-conforms-to-format")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["serials_covered"], 6)

    def test_quantity_mismatch_fails_the_sheet(self):
        result = assess_certificate_sheet(_sheet(quantity=5), 7, "2026-04-20")
        self.assertEqual(result["verdict"], "sheet-defective")
        self.assertTrue(any("quantity" in f for f in result["findings"]))

    def test_wrong_certificate_number_fails_the_sheet(self):
        result = assess_certificate_sheet(_sheet(), 9, "2026-04-20")
        self.assertTrue(any("does not match the pattern" in f
                            for f in result["findings"]))

    def test_post_dated_sheet_fails(self):
        result = assess_certificate_sheet(_sheet(), 7, "2026-04-01")
        self.assertTrue(any("presented on" in f for f in result["findings"]))

    def test_blank_block_fails_the_sheet(self):
        result = assess_certificate_sheet(_sheet(signatory_function=""), 7,
                                          "2026-04-20")
        self.assertTrue(any("blank" in f for f in result["findings"]))

    def test_quantity_without_serials_reported(self):
        result = assess_certificate_sheet(
            _sheet(serial_ranges=None), 7, "2026-04-20"
        )
        self.assertTrue(any("no serial range" in f for f in result["findings"]))

    def test_single_item_without_serials_is_tolerated(self):
        result = assess_certificate_sheet(
            _sheet(serial_ranges=None, quantity=1), 7, "2026-04-20"
        )
        self.assertEqual(result["verdict"], "sheet-conforms-to-format")

    def test_overlapping_ranges_fail_the_sheet(self):
        result = assess_certificate_sheet(
            _sheet(serial_ranges=["SN0007-SN0012", "SN0010-SN0014"], quantity=11),
            7, "2026-04-20",
        )
        self.assertTrue(any("overlap" in f for f in result["findings"]))

    def test_rendered_sheet_accompanies_the_verdict(self):
        result = assess_certificate_sheet(_sheet(), 7, "2026-04-20")
        self.assertEqual(len(result["rendered"]), len(BLOCK_ORDER))


if __name__ == "__main__":
    unittest.main()
