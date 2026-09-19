#!/usr/bin/env python3
"""Contract test for the unsigned integer parameter type (offline)."""

import unittest

from e7041_unsigned_integer_logic import (
    MAX_FIELD_WIDTH_BITS,
    UNSIGNED_PTC,
    VERDICT_IN_RANGE,
    VERDICT_NEGATIVE,
    VERDICT_OVER_RANGE,
    assess_unsigned_field,
    decode_unsigned,
    encode_unsigned,
    fits,
    is_octet_aligned,
    minimum_width_for,
    narrowing_is_lossless,
    octet_count,
    pack_octets,
    unpack_octets,
    validate_field_width,
    value_range,
)


class FieldWidthTests(unittest.TestCase):
    def test_a_plausible_width_is_accepted(self):
        self.assertEqual(validate_field_width(12), 12)

    def test_zero_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width(0)

    def test_width_beyond_the_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width(MAX_FIELD_WIDTH_BITS + 1)

    def test_a_boolean_is_not_a_width(self):
        with self.assertRaises(ValueError):
            validate_field_width(True)


class RangeTests(unittest.TestCase):
    def test_range_starts_at_zero(self):
        self.assertEqual(value_range(8)[0], 0)

    def test_eight_bits_reach_two_hundred_and_fifty_five(self):
        self.assertEqual(value_range(8), (0, 255))

    def test_sixteen_bits_reach_sixty_five_thousand_five_hundred_and_thirty_five(self):
        self.assertEqual(value_range(16), (0, 65535))

    def test_a_single_bit_carries_only_zero_and_one(self):
        self.assertEqual(value_range(1), (0, 1))

    def test_the_top_value_fits_and_one_more_does_not(self):
        self.assertTrue(fits(255, 8))
        self.assertFalse(fits(256, 8))

    def test_a_negative_value_never_fits(self):
        self.assertFalse(fits(-1, 8))


class MinimumWidthTests(unittest.TestCase):
    def test_zero_still_needs_a_bit(self):
        self.assertEqual(minimum_width_for(0), 1)

    def test_two_hundred_and_fifty_five_needs_eight_bits(self):
        self.assertEqual(minimum_width_for(255), 8)

    def test_two_hundred_and_fifty_six_needs_nine_bits(self):
        self.assertEqual(minimum_width_for(256), 9)

    def test_a_negative_maximum_rejected(self):
        with self.assertRaises(ValueError):
            minimum_width_for(-1)


class AlignmentTests(unittest.TestCase):
    def test_sixteen_bits_are_octet_aligned(self):
        self.assertTrue(is_octet_aligned(16))

    def test_twelve_bits_are_not_octet_aligned(self):
        self.assertFalse(is_octet_aligned(12))

    def test_twelve_bits_occupy_two_octets_alone(self):
        self.assertEqual(octet_count(12), 2)

    def test_a_whole_octet_field_occupies_exactly_its_octets(self):
        self.assertEqual(octet_count(24), 3)


class EncodeDecodeTests(unittest.TestCase):
    def test_a_value_encodes_most_significant_bit_first(self):
        self.assertEqual(encode_unsigned(5, 8), "00000101")

    def test_the_top_value_encodes_to_all_ones(self):
        self.assertEqual(encode_unsigned(15, 4), "1111")

    def test_an_over_range_value_is_refused_not_wrapped(self):
        with self.assertRaises(ValueError):
            encode_unsigned(256, 8)

    def test_a_negative_value_is_refused(self):
        with self.assertRaises(ValueError):
            encode_unsigned(-1, 8)

    def test_a_pattern_decodes_back_to_its_value(self):
        self.assertEqual(decode_unsigned("00001010", 8), 10)

    def test_a_pattern_of_the_wrong_length_rejected(self):
        with self.assertRaises(ValueError):
            decode_unsigned("0101", 8)

    def test_a_pattern_with_a_stray_character_rejected(self):
        with self.assertRaises(ValueError):
            decode_unsigned("0000010x", 8)

    def test_every_value_in_a_small_field_survives_a_round_trip(self):
        for value in range(16):
            self.assertEqual(decode_unsigned(encode_unsigned(value, 4), 4), value)


class OctetPackingTests(unittest.TestCase):
    def test_a_two_octet_field_packs_big_endian(self):
        self.assertEqual(pack_octets(258, 16), b"\x01\x02")

    def test_a_packed_field_unpacks_to_the_same_value(self):
        self.assertEqual(unpack_octets(pack_octets(4660, 16)), 4660)

    def test_an_unaligned_field_cannot_be_packed_alone(self):
        with self.assertRaises(ValueError):
            pack_octets(5, 12)

    def test_an_over_range_value_cannot_be_packed(self):
        with self.assertRaises(ValueError):
            pack_octets(70000, 16)

    def test_an_empty_octet_run_rejected(self):
        with self.assertRaises(ValueError):
            unpack_octets(b"")

    def test_a_text_octet_run_rejected(self):
        with self.assertRaises(ValueError):
            unpack_octets("0102")


class NarrowingTests(unittest.TestCase):
    def test_a_narrower_field_that_still_covers_the_maximum_is_lossless(self):
        self.assertTrue(narrowing_is_lossless(16, 8, 200))

    def test_a_narrower_field_below_the_maximum_is_lossy(self):
        self.assertFalse(narrowing_is_lossless(16, 8, 300))

    def test_the_boundary_value_is_still_lossless(self):
        self.assertTrue(narrowing_is_lossless(16, 8, 255))

    def test_a_maximum_beyond_the_source_field_rejected(self):
        with self.assertRaises(ValueError):
            narrowing_is_lossless(8, 4, 300)


class AssessmentTests(unittest.TestCase):
    def test_an_in_range_value_is_reported_with_its_encoding(self):
        result = assess_unsigned_field({"width_bits": 8, "value": 7})
        self.assertEqual(result["verdict"], VERDICT_IN_RANGE)
        self.assertEqual(result["ptc"], UNSIGNED_PTC)
        self.assertEqual(result["encoded_bits"], "00000111")

    def test_an_over_range_value_names_the_width_it_needs(self):
        result = assess_unsigned_field({"width_bits": 8, "value": 300})
        self.assertEqual(result["verdict"], VERDICT_OVER_RANGE)
        self.assertIsNone(result["encoded_bits"])
        self.assertEqual(result["minimum_width_bits"], 9)

    def test_a_negative_value_asks_for_a_signed_type_not_a_wider_field(self):
        result = assess_unsigned_field({"width_bits": 8, "value": -3})
        self.assertEqual(result["verdict"], VERDICT_NEGATIVE)
        self.assertTrue(any("signed" in f for f in result["findings"]))

    def test_an_unaligned_field_is_reported_as_such(self):
        result = assess_unsigned_field({"width_bits": 12, "value": 100})
        self.assertFalse(result["octet_aligned"])
        self.assertTrue(any("octet aligned" in f for f in result["findings"]))

    def test_an_aligned_field_raises_no_alignment_finding(self):
        result = assess_unsigned_field({"width_bits": 16, "value": 100})
        self.assertTrue(result["octet_aligned"])
        self.assertEqual(result["findings"], [])

    def test_a_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_unsigned_field("8 bits")

    def test_a_spec_without_a_value_rejected(self):
        with self.assertRaises(ValueError):
            assess_unsigned_field({"width_bits": 8})


if __name__ == "__main__":
    unittest.main()
