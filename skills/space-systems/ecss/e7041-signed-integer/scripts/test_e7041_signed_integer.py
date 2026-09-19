#!/usr/bin/env python3
"""Contract test for the signed integer parameter type (offline)."""

import unittest

from e7041_signed_integer_logic import (
    MAX_FIELD_WIDTH_BITS,
    SIGNED_PTC,
    VERDICT_ABOVE_RANGE,
    VERDICT_BELOW_RANGE,
    VERDICT_IN_RANGE,
    assess_signed_field,
    decode_signed,
    encode_bits,
    encode_signed,
    fits,
    minimum_width_for_range,
    misread_at_width,
    most_negative_value,
    range_is_asymmetric,
    sign_bit,
    validate_field_width,
    value_range,
)


class FieldWidthTests(unittest.TestCase):
    def test_a_plausible_width_is_accepted(self):
        self.assertEqual(validate_field_width(16), 16)

    def test_a_single_bit_signed_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width(1)

    def test_width_beyond_the_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width(MAX_FIELD_WIDTH_BITS + 1)

    def test_a_boolean_is_not_a_width(self):
        with self.assertRaises(ValueError):
            validate_field_width(True)


class RangeTests(unittest.TestCase):
    def test_eight_bits_span_minus_one_hundred_and_twenty_eight_to_one_hundred_and_twenty_seven(self):
        self.assertEqual(value_range(8), (-128, 127))

    def test_sixteen_bits_span_the_expected_range(self):
        self.assertEqual(value_range(16), (-32768, 32767))

    def test_two_bits_span_minus_two_to_one(self):
        self.assertEqual(value_range(2), (-2, 1))

    def test_every_width_is_asymmetric(self):
        for width in (2, 4, 8, 16, 32):
            self.assertTrue(range_is_asymmetric(width))

    def test_the_floor_is_one_past_the_negated_ceiling(self):
        low, high = value_range(8)
        self.assertEqual(low, -(high + 1))

    def test_the_most_negative_value_is_the_floor(self):
        self.assertEqual(most_negative_value(8), -128)

    def test_the_boundary_values_fit_and_their_neighbours_do_not(self):
        self.assertTrue(fits(-128, 8))
        self.assertTrue(fits(127, 8))
        self.assertFalse(fits(-129, 8))
        self.assertFalse(fits(128, 8))


class MinimumWidthTests(unittest.TestCase):
    def test_a_small_symmetric_range_needs_few_bits(self):
        self.assertEqual(minimum_width_for_range(-2, 1), 2)

    def test_the_asymmetric_floor_does_not_force_an_extra_bit(self):
        self.assertEqual(minimum_width_for_range(-128, 127), 8)

    def test_one_past_the_ceiling_forces_the_next_width(self):
        self.assertEqual(minimum_width_for_range(-128, 128), 9)

    def test_a_positive_only_range_still_pays_for_the_sign(self):
        self.assertEqual(minimum_width_for_range(0, 127), 8)

    def test_an_inverted_range_rejected(self):
        with self.assertRaises(ValueError):
            minimum_width_for_range(10, -10)

    def test_a_range_beyond_every_width_rejected(self):
        with self.assertRaises(ValueError):
            minimum_width_for_range(0, 1 << 70)


class EncodeDecodeTests(unittest.TestCase):
    def test_a_positive_value_encodes_to_itself(self):
        self.assertEqual(encode_signed(5, 8), 5)

    def test_minus_one_encodes_to_all_ones(self):
        self.assertEqual(encode_bits(-1, 8), "11111111")

    def test_the_floor_encodes_to_the_sign_bit_alone(self):
        self.assertEqual(encode_bits(-128, 8), "10000000")

    def test_an_over_range_value_is_refused(self):
        with self.assertRaises(ValueError):
            encode_signed(128, 8)

    def test_an_under_range_value_is_refused(self):
        with self.assertRaises(ValueError):
            encode_signed(-129, 8)

    def test_a_code_above_half_decodes_negative(self):
        self.assertEqual(decode_signed(255, 8), -1)

    def test_a_code_below_half_decodes_positive(self):
        self.assertEqual(decode_signed(5, 8), 5)

    def test_a_code_outside_the_pattern_rejected(self):
        with self.assertRaises(ValueError):
            decode_signed(256, 8)

    def test_every_value_in_a_small_field_survives_a_round_trip(self):
        for value in range(-8, 8):
            self.assertEqual(decode_signed(encode_signed(value, 4), 4), value)

    def test_the_sign_bit_is_set_only_for_negatives(self):
        self.assertEqual(sign_bit(-1, 8), 1)
        self.assertEqual(sign_bit(0, 8), 0)
        self.assertEqual(sign_bit(127, 8), 0)


class MisreadTests(unittest.TestCase):
    def test_a_small_negative_read_wide_becomes_a_large_positive(self):
        self.assertEqual(misread_at_width(-1, 8, 16), 255)

    def test_the_floor_read_wide_becomes_a_large_positive(self):
        self.assertEqual(misread_at_width(-128, 8, 16), 128)

    def test_a_positive_value_is_unharmed_by_the_wider_read(self):
        self.assertEqual(misread_at_width(42, 8, 16), 42)

    def test_reading_narrower_than_the_field_rejected(self):
        with self.assertRaises(ValueError):
            misread_at_width(-1, 16, 8)


class AssessmentTests(unittest.TestCase):
    def test_an_in_range_value_is_reported_with_its_encoding(self):
        result = assess_signed_field({"width_bits": 8, "value": -3})
        self.assertEqual(result["verdict"], VERDICT_IN_RANGE)
        self.assertEqual(result["ptc"], SIGNED_PTC)
        self.assertEqual(result["encoded_bits"], "11111101")

    def test_a_value_above_the_ceiling_is_reported(self):
        result = assess_signed_field({"width_bits": 8, "value": 200})
        self.assertEqual(result["verdict"], VERDICT_ABOVE_RANGE)
        self.assertIsNone(result["encoded_bits"])
        self.assertEqual(result["minimum_width_bits"], 9)

    def test_a_value_below_the_floor_is_reported(self):
        result = assess_signed_field({"width_bits": 8, "value": -200})
        self.assertEqual(result["verdict"], VERDICT_BELOW_RANGE)
        self.assertTrue(any("floor" in f for f in result["findings"]))

    def test_the_floor_value_is_flagged_as_having_no_counterpart(self):
        result = assess_signed_field({"width_bits": 8, "value": -128})
        self.assertEqual(result["verdict"], VERDICT_IN_RANGE)
        self.assertTrue(any("no positive" in f for f in result["findings"]))

    def test_an_unaligned_width_is_flagged_for_sign_extension(self):
        result = assess_signed_field({"width_bits": 12, "value": -5})
        self.assertTrue(any("sign extension" in f for f in result["findings"]))

    def test_an_aligned_mid_range_value_raises_no_findings(self):
        result = assess_signed_field({"width_bits": 16, "value": 100})
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["asymmetric"])

    def test_a_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_signed_field("-3")

    def test_a_spec_without_a_value_rejected(self):
        with self.assertRaises(ValueError):
            assess_signed_field({"width_bits": 8})


if __name__ == "__main__":
    unittest.main()
