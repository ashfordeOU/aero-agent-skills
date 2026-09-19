"""Contract tests for the clause 7.3.1 packet field type code logic."""

import unittest

from e7041_packet_field_type_code_general_logic import (
    BITS_PER_OCTET,
    DEDUCED_TYPE_CODE,
    TYPE_NAMES,
    assess_structure,
    describe_field_type,
    field_width_bits,
    is_octet_aligned,
    lay_out_fields,
    padding_bits,
    straddling_fields,
    validate_format_code,
    validate_type_code,
)


def field(name, type_code, format_code, **extra):
    entry = {"name": name, "type_code": type_code, "format_code": format_code}
    entry.update(extra)
    return entry


class TypeCodeTests(unittest.TestCase):
    def test_octet_is_eight_bits(self):
        self.assertEqual(BITS_PER_OCTET, 8)

    def test_known_type_code_accepted(self):
        self.assertEqual(validate_type_code(3), 3)

    def test_type_names_cover_the_defined_codes(self):
        self.assertEqual(TYPE_NAMES[1], "boolean")
        self.assertEqual(TYPE_NAMES[DEDUCED_TYPE_CODE], "deduced")

    def test_unknown_type_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_type_code(6)

    def test_negative_type_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_type_code(-1)

    def test_boolean_type_code_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_type_code(True)

    def test_negative_format_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_format_code(-1)

    def test_fractional_format_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_format_code(1.5)


class WidthTests(unittest.TestCase):
    def test_tabulated_unsigned_integer_widths(self):
        self.assertEqual(field_width_bits(3, 13), 16)
        self.assertEqual(field_width_bits(3, 18), 64)

    def test_signed_integer_shares_the_unsigned_table(self):
        self.assertEqual(field_width_bits(4, 16), 32)

    def test_real_formats_are_single_and_double(self):
        self.assertEqual(field_width_bits(5, 1), 32)
        self.assertEqual(field_width_bits(5, 2), 64)

    def test_enumerated_width_is_the_format_code_in_bits(self):
        self.assertEqual(field_width_bits(2, 3), 3)

    def test_octet_string_width_is_the_format_code_in_octets(self):
        self.assertEqual(field_width_bits(7, 4), 32)

    def test_character_string_width_is_the_format_code_in_characters(self):
        self.assertEqual(field_width_bits(8, 10), 80)

    def test_absolute_time_widths_are_tabulated(self):
        self.assertEqual(field_width_bits(9, 3), 48)

    def test_undefined_format_for_a_tabulated_type_rejected(self):
        with self.assertRaises(ValueError):
            field_width_bits(3, 5)

    def test_zero_length_derived_field_rejected(self):
        with self.assertRaises(ValueError):
            field_width_bits(7, 0)

    def test_oversize_enumerated_field_rejected(self):
        with self.assertRaises(ValueError):
            field_width_bits(2, 65)

    def test_deduced_type_has_no_width_of_its_own(self):
        with self.assertRaises(ValueError):
            field_width_bits(DEDUCED_TYPE_CODE, 0)


class DescribeTests(unittest.TestCase):
    def test_description_names_the_type(self):
        described = describe_field_type(5, 2)
        self.assertEqual(described["type_name"], "real")
        self.assertEqual(described["width_bits"], 64)
        self.assertFalse(described["deduced"])

    def test_deduced_description_carries_no_width(self):
        described = describe_field_type(DEDUCED_TYPE_CODE, 0)
        self.assertTrue(described["deduced"])
        self.assertIsNone(described["width_bits"])


class AlignmentTests(unittest.TestCase):
    def test_multiple_of_eight_is_aligned(self):
        self.assertTrue(is_octet_aligned(32))

    def test_zero_bits_is_aligned(self):
        self.assertTrue(is_octet_aligned(0))

    def test_thirteen_bits_is_not_aligned(self):
        self.assertFalse(is_octet_aligned(13))

    def test_padding_completes_the_octet(self):
        self.assertEqual(padding_bits(13), 3)

    def test_aligned_count_needs_no_padding(self):
        self.assertEqual(padding_bits(32), 0)

    def test_negative_bit_count_rejected(self):
        with self.assertRaises(ValueError):
            is_octet_aligned(-8)


class LayoutTests(unittest.TestCase):
    def test_offsets_accumulate_the_widths(self):
        layout = lay_out_fields(
            [field("flag", 1, 0), field("mode", 2, 3), field("count", 3, 13)]
        )
        self.assertEqual([f["bit_offset"] for f in layout["fields"]], [0, 1, 4])
        self.assertEqual(layout["total_bits"], 20)

    def test_octet_offset_is_derived_from_the_bit_offset(self):
        layout = lay_out_fields([field("a", 3, 13), field("b", 3, 8)])
        self.assertEqual(layout["fields"][1]["octet_offset"], 2)

    def test_deduced_field_needs_a_supplied_width(self):
        with self.assertRaises(ValueError):
            lay_out_fields([field("payload", DEDUCED_TYPE_CODE, 0)])

    def test_deduced_field_accepts_a_supplied_width(self):
        layout = lay_out_fields([field("payload", DEDUCED_TYPE_CODE, 0, width_bits=24)])
        self.assertEqual(layout["total_bits"], 24)

    def test_deduced_field_rejects_a_zero_supplied_width(self):
        with self.assertRaises(ValueError):
            lay_out_fields([field("payload", DEDUCED_TYPE_CODE, 0, width_bits=0)])

    def test_empty_structure_rejected(self):
        with self.assertRaises(ValueError):
            lay_out_fields([])

    def test_unnamed_field_rejected(self):
        with self.assertRaises(ValueError):
            lay_out_fields([{"type_code": 3, "format_code": 8}])

    def test_blank_field_name_rejected(self):
        with self.assertRaises(ValueError):
            lay_out_fields([field("   ", 3, 8)])


class StraddleTests(unittest.TestCase):
    def test_field_within_one_octet_does_not_straddle(self):
        layout = lay_out_fields([field("flag", 1, 0), field("mode", 2, 3)])
        self.assertEqual(straddling_fields(layout["fields"]), [])

    def test_field_crossing_a_boundary_is_named(self):
        layout = lay_out_fields([field("flag", 1, 0), field("count", 3, 13)])
        self.assertEqual(straddling_fields(layout["fields"]), ["count"])

    def test_aligned_multi_octet_field_does_not_straddle(self):
        layout = lay_out_fields([field("count", 3, 13)])
        self.assertEqual(straddling_fields(layout["fields"]), [])

    def test_field_finishing_inside_its_octet_does_not_straddle(self):
        layout = lay_out_fields([field("flag", 1, 0), field("mode", 2, 7)])
        self.assertEqual(straddling_fields(layout["fields"]), [])

    def test_malformed_laid_out_field_rejected(self):
        with self.assertRaises(ValueError):
            straddling_fields([{"name": "a"}])


class AssessmentTests(unittest.TestCase):
    def test_aligned_structure_reports_no_padding(self):
        result = assess_structure([field("count", 3, 13), field("value", 5, 1)])
        self.assertTrue(result["octet_aligned"])
        self.assertEqual(result["padding_bits"], 0)
        self.assertEqual(result["total_octets"], 6)

    def test_unaligned_structure_is_flagged(self):
        result = assess_structure([field("flag", 1, 0), field("mode", 2, 3)])
        self.assertEqual(result["total_bits"], 4)
        self.assertEqual(result["padding_bits"], 4)
        self.assertTrue(any("pad bit" in f for f in result["findings"]))

    def test_total_octets_includes_the_padding(self):
        result = assess_structure([field("flag", 1, 0)])
        self.assertEqual(result["total_octets"], 1)

    def test_straddling_field_is_reported(self):
        result = assess_structure([field("flag", 1, 0), field("count", 3, 13)])
        self.assertIn("count", result["straddling_fields"])
        self.assertTrue(any("crossing an octet boundary" in f for f in result["findings"]))

    def test_duplicate_field_names_are_flagged(self):
        result = assess_structure([field("a", 3, 8), field("a", 3, 8)])
        self.assertTrue(any("duplicate field name" in f for f in result["findings"]))

    def test_clean_aligned_structure_has_no_findings(self):
        result = assess_structure([field("value", 5, 1)])
        self.assertEqual(result["findings"], [])

    def test_bad_type_code_inside_a_structure_rejected(self):
        with self.assertRaises(ValueError):
            assess_structure([field("odd", 6, 1)])


if __name__ == "__main__":
    unittest.main()
