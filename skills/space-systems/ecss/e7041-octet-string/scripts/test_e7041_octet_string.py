#!/usr/bin/env python3
"""Contract test for the octet-string parameter type (offline)."""

import unittest

from e7041_octet_string_logic import (
    MAX_COUNT_WIDTH_BITS,
    OCTET_STRING_PTC,
    VARIABLE_FORMAT_CODE,
    VERDICT_COUNT_FIELD_TOO_NARROW,
    VERDICT_EMPTY_FIXED,
    VERDICT_LENGTH_MISMATCH,
    VERDICT_VALID,
    assess_octet_string_field,
    check_fixed_field,
    decode_variable,
    encode_variable,
    field_size_bits,
    max_length_for_count_width,
    padding_octets,
    payloads_are_equal,
    validate_count_width,
    validate_fixed_length,
    validate_octets,
)

PAYLOAD = b"\x01\x02\x03\x04"


class ValidationTests(unittest.TestCase):
    def test_a_byte_payload_is_accepted(self):
        self.assertEqual(validate_octets(PAYLOAD), PAYLOAD)

    def test_a_bytearray_payload_is_normalised_to_bytes(self):
        self.assertEqual(validate_octets(bytearray(PAYLOAD)), PAYLOAD)

    def test_an_empty_payload_is_accepted_at_this_level(self):
        self.assertEqual(validate_octets(b""), b"")

    def test_a_text_payload_is_refused_because_there_is_no_character_set(self):
        with self.assertRaises(ValueError):
            validate_octets("0102")

    def test_an_integer_payload_rejected(self):
        with self.assertRaises(ValueError):
            validate_octets(0x01020304)

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


class AlignmentTests(unittest.TestCase):
    def test_an_octet_string_never_needs_padding(self):
        for length in (0, 1, 3, 7, 1000):
            self.assertEqual(padding_octets(length), 0)

    def test_the_payload_is_always_a_whole_number_of_bits(self):
        self.assertEqual(field_size_bits(4), 32)

    def test_an_empty_payload_occupies_no_bits(self):
        self.assertEqual(field_size_bits(0), 0)

    def test_a_negative_length_rejected(self):
        with self.assertRaises(ValueError):
            field_size_bits(-1)


class CountFieldTests(unittest.TestCase):
    def test_an_eight_bit_count_field_announces_two_hundred_and_fifty_five_octets(self):
        self.assertEqual(max_length_for_count_width(8), 255)

    def test_a_sixteen_bit_count_field_announces_sixty_five_thousand_plus(self):
        self.assertEqual(max_length_for_count_width(16), 65535)

    def test_a_four_bit_count_field_announces_fifteen_octets(self):
        self.assertEqual(max_length_for_count_width(4), 15)


class FixedFieldTests(unittest.TestCase):
    def test_an_exact_payload_passes_the_fixed_field_check(self):
        self.assertEqual(check_fixed_field(PAYLOAD, 4), PAYLOAD)

    def test_a_short_payload_is_not_padded_out(self):
        with self.assertRaises(ValueError):
            check_fixed_field(b"\x01\x02", 4)

    def test_a_long_payload_is_not_truncated_to_fit(self):
        with self.assertRaises(ValueError):
            check_fixed_field(PAYLOAD + b"\x05", 4)

    def test_a_text_payload_is_refused_by_the_fixed_field_check(self):
        with self.assertRaises(ValueError):
            check_fixed_field("abcd", 4)


class VariableFieldTests(unittest.TestCase):
    def test_a_variable_field_prefixes_its_octet_count(self):
        result = encode_variable(PAYLOAD, 8)
        self.assertEqual(result["count_octets"], b"\x04")
        self.assertEqual(result["buffer"], b"\x04" + PAYLOAD)

    def test_a_variable_field_round_trips(self):
        result = encode_variable(PAYLOAD, 16)
        decoded = decode_variable(result["buffer"], 16)
        self.assertEqual(decoded["payload"], PAYLOAD)
        self.assertEqual(decoded["length_octets"], 4)

    def test_an_empty_variable_field_is_legitimate(self):
        result = encode_variable(b"", 8)
        decoded = decode_variable(result["buffer"], 8)
        self.assertEqual(decoded["payload"], b"")
        self.assertEqual(decoded["consumed_octets"], 1)

    def test_a_payload_past_the_count_field_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            encode_variable(b"\x00" * 300, 8)

    def test_a_decode_reports_what_it_consumed_and_what_remains(self):
        buffer = encode_variable(PAYLOAD, 8)["buffer"] + b"\xaa\xbb"
        decoded = decode_variable(buffer, 8)
        self.assertEqual(decoded["consumed_octets"], 5)
        self.assertEqual(decoded["trailing_octets"], 2)

    def test_a_truncated_payload_is_refused_not_shortened(self):
        with self.assertRaises(ValueError):
            decode_variable(b"\x04\x01\x02", 8)

    def test_a_buffer_shorter_than_the_count_field_rejected(self):
        with self.assertRaises(ValueError):
            decode_variable(b"", 16)

    def test_an_unaligned_count_field_width_rejected(self):
        with self.assertRaises(ValueError):
            encode_variable(PAYLOAD, 12)

    def test_an_unaligned_count_field_width_rejected_on_decode(self):
        with self.assertRaises(ValueError):
            decode_variable(b"\x04" + PAYLOAD, 12)

    def test_every_short_payload_survives_a_round_trip(self):
        for length in range(8):
            payload = bytes(range(length))
            buffer = encode_variable(payload, 8)["buffer"]
            self.assertEqual(decode_variable(buffer, 8)["payload"], payload)


class EqualityTests(unittest.TestCase):
    def test_identical_payloads_match(self):
        self.assertTrue(payloads_are_equal(PAYLOAD, bytes(PAYLOAD)))

    def test_a_shorter_prefix_is_not_the_same_payload(self):
        self.assertFalse(payloads_are_equal(PAYLOAD, PAYLOAD[:3]))

    def test_a_trailing_zero_octet_is_part_of_the_payload(self):
        self.assertFalse(payloads_are_equal(PAYLOAD, PAYLOAD + b"\x00"))


class AssessmentTests(unittest.TestCase):
    def test_a_matching_fixed_field_is_valid(self):
        result = assess_octet_string_field({"payload": PAYLOAD, "format_code": 4})
        self.assertEqual(result["verdict"], VERDICT_VALID)
        self.assertEqual(result["ptc"], OCTET_STRING_PTC)
        self.assertFalse(result["variable_length"])
        self.assertEqual(result["pad_octets"], 0)

    def test_a_mismatched_fixed_field_is_reported(self):
        result = assess_octet_string_field({"payload": b"\x01\x02", "format_code": 4})
        self.assertEqual(result["verdict"], VERDICT_LENGTH_MISMATCH)
        self.assertTrue(any("truncated" in f for f in result["findings"]))

    def test_an_empty_fixed_field_is_reported(self):
        result = assess_octet_string_field({"payload": b"", "format_code": 4})
        self.assertEqual(result["verdict"], VERDICT_EMPTY_FIXED)

    def test_a_variable_field_within_its_count_is_valid(self):
        result = assess_octet_string_field(
            {
                "payload": PAYLOAD,
                "format_code": VARIABLE_FORMAT_CODE,
                "count_width_bits": 8,
            }
        )
        self.assertEqual(result["verdict"], VERDICT_VALID)
        self.assertTrue(result["variable_length"])
        self.assertEqual(result["field_octets"], 5)

    def test_a_variable_field_past_its_count_is_reported(self):
        result = assess_octet_string_field(
            {
                "payload": b"\x00" * 300,
                "format_code": VARIABLE_FORMAT_CODE,
                "count_width_bits": 8,
            }
        )
        self.assertEqual(result["verdict"], VERDICT_COUNT_FIELD_TOO_NARROW)

    def test_an_empty_variable_field_is_valid_and_noted(self):
        result = assess_octet_string_field(
            {
                "payload": b"",
                "format_code": VARIABLE_FORMAT_CODE,
                "count_width_bits": 8,
            }
        )
        self.assertEqual(result["verdict"], VERDICT_VALID)
        self.assertTrue(any("zero-length" in f for f in result["findings"]))

    def test_every_assessment_records_that_the_payload_is_opaque(self):
        result = assess_octet_string_field({"payload": PAYLOAD, "format_code": 4})
        self.assertTrue(any("opaque" in f for f in result["findings"]))

    def test_the_payload_bit_count_is_a_whole_number_of_octets(self):
        result = assess_octet_string_field({"payload": PAYLOAD, "format_code": 4})
        self.assertEqual(result["payload_bits"], 32)

    def test_a_variable_field_without_a_count_width_rejected(self):
        with self.assertRaises(ValueError):
            assess_octet_string_field(
                {"payload": PAYLOAD, "format_code": VARIABLE_FORMAT_CODE}
            )

    def test_a_negative_format_code_rejected(self):
        with self.assertRaises(ValueError):
            assess_octet_string_field({"payload": PAYLOAD, "format_code": -1})

    def test_a_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_octet_string_field(PAYLOAD)

    def test_a_text_payload_in_a_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_octet_string_field({"payload": "0102", "format_code": 4})


if __name__ == "__main__":
    unittest.main()
