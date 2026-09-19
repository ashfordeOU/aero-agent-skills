#!/usr/bin/env python3
"""Contract test for the bit-string parameter type (offline)."""

import unittest

from e7041_bit_string_logic import (
    BIT_STRING_PTC,
    MAX_COUNT_WIDTH_BITS,
    PAD_BIT,
    VARIABLE_FORMAT_CODE,
    VERDICT_COUNT_FIELD_TOO_NARROW,
    VERDICT_EMPTY_FIXED,
    VERDICT_LENGTH_MISMATCH,
    VERDICT_VALID,
    assess_bit_string_field,
    check_fixed_field,
    decode_variable,
    encode_variable,
    max_length_for_count_width,
    octet_count,
    pack_bit_string,
    pad_to_octet,
    padding_bits,
    patterns_are_equal,
    strip_pad,
    unpack_bit_string,
    validate_bits,
    validate_count_width,
    validate_fixed_length,
)


class ValidationTests(unittest.TestCase):
    def test_a_well_formed_pattern_is_accepted(self):
        self.assertEqual(validate_bits("10110"), "10110")

    def test_an_empty_pattern_is_accepted_at_this_level(self):
        self.assertEqual(validate_bits(""), "")

    def test_a_pattern_with_a_stray_character_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits("1012")

    def test_a_non_string_pattern_rejected(self):
        with self.assertRaises(ValueError):
            validate_bits(0b10110)

    def test_a_zero_fixed_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_fixed_length(0)

    def test_an_absurd_fixed_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_fixed_length(1 << 20)

    def test_a_count_width_beyond_the_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_count_width(MAX_COUNT_WIDTH_BITS + 1)

    def test_a_zero_count_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_count_width(0)


class CountFieldTests(unittest.TestCase):
    def test_an_eight_bit_count_field_announces_two_hundred_and_fifty_five_bits(self):
        self.assertEqual(max_length_for_count_width(8), 255)

    def test_a_four_bit_count_field_announces_fifteen_bits(self):
        self.assertEqual(max_length_for_count_width(4), 15)

    def test_a_single_bit_count_field_announces_one_bit(self):
        self.assertEqual(max_length_for_count_width(1), 1)


class PaddingTests(unittest.TestCase):
    def test_a_five_bit_pattern_needs_three_pad_bits(self):
        self.assertEqual(padding_bits(5), 3)

    def test_an_octet_multiple_needs_no_pad(self):
        self.assertEqual(padding_bits(16), 0)

    def test_a_zero_length_pattern_needs_no_pad(self):
        self.assertEqual(padding_bits(0), 0)

    def test_a_five_bit_pattern_occupies_one_octet(self):
        self.assertEqual(octet_count(5), 1)

    def test_a_nine_bit_pattern_occupies_two_octets(self):
        self.assertEqual(octet_count(9), 2)

    def test_the_pad_goes_after_the_last_declared_bit(self):
        result = pad_to_octet("10110")
        self.assertEqual(result["padded_bits"], "10110" + PAD_BIT * 3)
        self.assertEqual(result["pad_count"], 3)

    def test_the_pad_value_is_fixed_so_two_encodings_agree(self):
        self.assertEqual(
            pad_to_octet("101")["padded_bits"], pad_to_octet("101")["padded_bits"]
        )

    def test_stripping_the_pad_recovers_the_declared_pattern(self):
        self.assertEqual(strip_pad("10110000", 5), "10110")

    def test_a_declared_length_past_the_run_rejected(self):
        with self.assertRaises(ValueError):
            strip_pad("10110000", 12)

    def test_more_than_one_octet_of_trailing_bits_rejected(self):
        with self.assertRaises(ValueError):
            strip_pad("1011000000000000", 5)


class PackingTests(unittest.TestCase):
    def test_a_five_bit_pattern_packs_into_one_octet(self):
        packed = pack_bit_string("10110")
        self.assertEqual(packed["octets"], b"\xb0")
        self.assertEqual(packed["pad_count"], 3)

    def test_a_pattern_survives_a_pack_and_unpack(self):
        packed = pack_bit_string("1011010110110")
        self.assertEqual(
            unpack_bit_string(packed["octets"], packed["length_bits"]),
            "1011010110110",
        )

    def test_the_declaration_order_is_preserved_not_reversed(self):
        packed = pack_bit_string("10000000")
        self.assertEqual(packed["octets"], b"\x80")

    def test_an_empty_pattern_packs_to_no_octets(self):
        packed = pack_bit_string("")
        self.assertEqual(packed["octets"], b"")

    def test_unpacking_past_the_octet_run_rejected(self):
        with self.assertRaises(ValueError):
            unpack_bit_string(b"\xb0", 12)

    def test_unpacking_a_text_run_rejected(self):
        with self.assertRaises(ValueError):
            unpack_bit_string("b0", 5)

    def test_unpacking_zero_bits_gives_an_empty_pattern(self):
        self.assertEqual(unpack_bit_string(b"\xb0", 0), "")

    def test_every_short_pattern_survives_a_round_trip(self):
        for value in range(32):
            bits = format(value, "05b")
            packed = pack_bit_string(bits)
            self.assertEqual(unpack_bit_string(packed["octets"], 5), bits)


class FixedFieldTests(unittest.TestCase):
    def test_an_exact_pattern_passes_the_fixed_field_check(self):
        self.assertEqual(check_fixed_field("10110", 5), "10110")

    def test_a_short_pattern_is_not_padded_into_meaning(self):
        with self.assertRaises(ValueError):
            check_fixed_field("101", 5)

    def test_a_long_pattern_is_not_truncated_to_fit(self):
        with self.assertRaises(ValueError):
            check_fixed_field("1011011", 5)


class VariableFieldTests(unittest.TestCase):
    def test_a_variable_field_carries_its_length_in_the_count(self):
        result = encode_variable("10110", 8)
        self.assertEqual(result["count_bits"], "00000101")
        self.assertEqual(result["octets"], b"\xb0")

    def test_a_variable_field_round_trips(self):
        result = encode_variable("101101011", 8)
        self.assertEqual(
            decode_variable(result["count_bits"], result["octets"], 8), "101101011"
        )

    def test_an_empty_variable_field_is_legitimate(self):
        result = encode_variable("", 8)
        self.assertEqual(result["length_bits"], 0)
        self.assertEqual(decode_variable(result["count_bits"], b"", 8), "")

    def test_a_pattern_past_the_count_field_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            encode_variable("1" * 20, 4)

    def test_a_count_field_of_the_wrong_width_rejected(self):
        with self.assertRaises(ValueError):
            decode_variable("0101", b"\xb0", 8)


class EqualityTests(unittest.TestCase):
    def test_identical_patterns_match(self):
        self.assertTrue(patterns_are_equal("10110", "10110"))

    def test_a_leading_zero_is_part_of_the_pattern(self):
        self.assertFalse(patterns_are_equal("0110", "110"))

    def test_a_shorter_prefix_is_not_the_same_pattern(self):
        self.assertFalse(patterns_are_equal("1011", "10110"))


class AssessmentTests(unittest.TestCase):
    def test_a_matching_fixed_field_is_valid(self):
        result = assess_bit_string_field({"bits": "10110", "format_code": 5})
        self.assertEqual(result["verdict"], VERDICT_VALID)
        self.assertEqual(result["ptc"], BIT_STRING_PTC)
        self.assertFalse(result["variable_length"])
        self.assertEqual(result["pad_bits"], 3)

    def test_a_mismatched_fixed_field_is_reported(self):
        result = assess_bit_string_field({"bits": "101", "format_code": 5})
        self.assertEqual(result["verdict"], VERDICT_LENGTH_MISMATCH)
        self.assertTrue(any("truncated" in f for f in result["findings"]))

    def test_an_empty_fixed_field_is_reported(self):
        result = assess_bit_string_field({"bits": "", "format_code": 5})
        self.assertEqual(result["verdict"], VERDICT_EMPTY_FIXED)

    def test_a_variable_field_within_its_count_is_valid(self):
        result = assess_bit_string_field(
            {"bits": "10110", "format_code": VARIABLE_FORMAT_CODE, "count_width_bits": 8}
        )
        self.assertEqual(result["verdict"], VERDICT_VALID)
        self.assertTrue(result["variable_length"])

    def test_a_variable_field_past_its_count_is_reported(self):
        result = assess_bit_string_field(
            {"bits": "1" * 20, "format_code": VARIABLE_FORMAT_CODE, "count_width_bits": 4}
        )
        self.assertEqual(result["verdict"], VERDICT_COUNT_FIELD_TOO_NARROW)
        self.assertTrue(any("count field" in f for f in result["findings"]))

    def test_an_empty_variable_field_is_valid_and_noted(self):
        result = assess_bit_string_field(
            {"bits": "", "format_code": VARIABLE_FORMAT_CODE, "count_width_bits": 8}
        )
        self.assertEqual(result["verdict"], VERDICT_VALID)
        self.assertTrue(any("zero-length" in f for f in result["findings"]))

    def test_an_octet_aligned_pattern_raises_no_pad_finding(self):
        result = assess_bit_string_field({"bits": "10110101", "format_code": 8})
        self.assertEqual(result["pad_bits"], 0)
        self.assertEqual(result["findings"], [])

    def test_a_variable_field_without_a_count_width_rejected(self):
        with self.assertRaises(ValueError):
            assess_bit_string_field(
                {"bits": "10110", "format_code": VARIABLE_FORMAT_CODE}
            )

    def test_a_negative_format_code_rejected(self):
        with self.assertRaises(ValueError):
            assess_bit_string_field({"bits": "10110", "format_code": -1})

    def test_a_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_bit_string_field("10110")


if __name__ == "__main__":
    unittest.main()
