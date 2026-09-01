#!/usr/bin/env python3
"""Gate 3 contract test: ARINC 429 word encoding and decoding (paraphrase).

Exercises scripts/arinc429_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the worked anchor word
encodes to the expected 32-bit integer with odd parity, decode
round-trips every field, BNR signed values encode and decode at a
given scale factor (123.4 at 0.1), BCD values encode and decode,
parity is odd, and invalid labels or out-of-range fields raise
ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import arinc429_logic as a429  # noqa: E402

# Worked anchor: label 010 (octal, value 8), SDI 1, BNR data field 1234,
# SSM 3 (normal operation). Payload 0x60134908 has 9 set bits, so the odd
# parity bit is 0 and the full 32-bit word keeps odd parity.
ANCHOR_WORD = 0x60134908


class LabelTest(unittest.TestCase):
    def test_octal_string_010(self):
        self.assertEqual(a429.parse_label("010"), 8)

    def test_octal_string_377(self):
        self.assertEqual(a429.parse_label("377"), 0o377)

    def test_int_label_passthrough(self):
        self.assertEqual(a429.parse_label(8), 8)

    def test_invalid_octal_digit_raises(self):
        with self.assertRaises(ValueError):
            a429.parse_label("019")

    def test_label_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            a429.parse_label(256)
        with self.assertRaises(ValueError):
            a429.parse_label(-1)


class BuildWordTest(unittest.TestCase):
    def test_anchor_word_encodes_to_expected_integer(self):
        self.assertEqual(a429.build_word(0o10, 1, 1234, 3), ANCHOR_WORD)

    def test_anchor_word_with_octal_string_label(self):
        self.assertEqual(a429.build_word("010", 1, 1234, 3), ANCHOR_WORD)

    def test_anchor_word_has_odd_parity(self):
        self.assertEqual(bin(ANCHOR_WORD).count("1") % 2, 1)

    def test_computed_parity_makes_popcount_odd(self):
        word = a429.build_word(0o10, 0, 100, 1)
        self.assertEqual(bin(word).count("1") % 2, 1)

    def test_explicit_parity_bit_is_respected(self):
        payload = a429.build_word(0o10, 1, 1234, 3, parity=0)
        self.assertEqual(payload, ANCHOR_WORD)

    def test_explicit_parity_invalid_raises(self):
        with self.assertRaises(ValueError):
            a429.build_word(0o10, 1, 1234, 3, parity=2)


class DecodeRoundTripTest(unittest.TestCase):
    def test_anchor_decode_round_trips_all_fields(self):
        fields = a429.decode_word(ANCHOR_WORD)
        self.assertEqual(fields["label"], 8)
        self.assertEqual(fields["sdi"], 1)
        self.assertEqual(fields["data"], 1234)
        self.assertEqual(fields["ssm"], 3)
        self.assertEqual(fields["parity"], 0)
        self.assertTrue(fields["parity_ok"])

    def test_random_word_round_trip(self):
        for label, sdi, data, ssm in ((0o10, 0, 1, 0), (0o377, 3, 0x7FFFF, 2),
                                      (0o12, 2, 555, 1), (0o320, 1, 999, 3)):
            word = a429.build_word(label, sdi, data, ssm)
            fields = a429.decode_word(word)
            self.assertEqual(fields["label"], label)
            self.assertEqual(fields["sdi"], sdi)
            self.assertEqual(fields["data"], data)
            self.assertEqual(fields["ssm"], ssm)
            self.assertEqual(fields["parity"], word >> 31)
            self.assertTrue(fields["parity_ok"])

    def test_word_bounds_raise(self):
        with self.assertRaises(ValueError):
            a429.decode_word(1 << 32)
        with self.assertRaises(ValueError):
            a429.decode_word(-1)


class FieldBoundsTest(unittest.TestCase):
    def test_sdi_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            a429.build_word(0o10, 4, 0, 0)

    def test_data_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            a429.build_word(0o10, 0, 0x80000, 0)

    def test_ssm_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            a429.build_word(0o10, 0, 0, 4)

    def test_label_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            a429.build_word(0o400, 0, 0, 0)

    def test_maximum_field_values_encode(self):
        word = a429.build_word(0o377, 3, 0x7FFFF, 3)
        self.assertEqual(word & 0xFFFFFFFF, word)  # fits 32 bits
        self.assertEqual(bin(word).count("1") % 2, 1)  # odd parity holds


class BnrTest(unittest.TestCase):
    def test_anchor_123_4_at_scale_0_1(self):
        self.assertEqual(a429.bnr_encode(123.4, 0.1), 1234)

    def test_anchor_decode_123_4(self):
        self.assertAlmostEqual(a429.bnr_decode(1234, 0.1), 123.4, places=6)

    def test_round_trip_positive(self):
        field = a429.bnr_encode(123.4, 0.1)
        self.assertAlmostEqual(a429.bnr_decode(field, 0.1), 123.4, places=6)

    def test_round_trip_negative(self):
        field = a429.bnr_encode(-12.3, 0.1)
        self.assertEqual(field, 524165)
        self.assertAlmostEqual(a429.bnr_decode(field, 0.1), -12.3, places=6)

    def test_zero_value(self):
        field = a429.bnr_encode(0.0, 0.1)
        self.assertEqual(field, 0)
        self.assertEqual(a429.bnr_decode(field, 0.1), 0.0)

    def test_out_of_range_value_raises(self):
        with self.assertRaises(ValueError):
            a429.bnr_encode(30000.0, 0.1)  # raw 300000 beyond 2^18 - 1

    def test_invalid_scale_raises(self):
        with self.assertRaises(ValueError):
            a429.bnr_encode(1.0, 0.0)
        with self.assertRaises(ValueError):
            a429.bnr_encode(1.0, -0.1)

    def test_invalid_field_raises(self):
        with self.assertRaises(ValueError):
            a429.bnr_decode(0x80000, 0.1)


class BcdTest(unittest.TestCase):
    def test_anchor_encode_1234(self):
        self.assertEqual(a429.bcd_encode(1234), 4660)

    def test_anchor_decode_1234(self):
        self.assertEqual(a429.bcd_decode(4660), 1234)

    def test_round_trip_four_digits(self):
        self.assertEqual(a429.bcd_decode(a429.bcd_encode(2026, digits=4), digits=4), 2026)

    def test_round_trip_five_digits(self):
        self.assertEqual(a429.bcd_decode(a429.bcd_encode(79999, digits=5), digits=5), 79999)

    def test_five_digit_capacity_raises(self):
        with self.assertRaises(ValueError):
            a429.bcd_encode(80000, digits=5)

    def test_four_digit_capacity_raises(self):
        with self.assertRaises(ValueError):
            a429.bcd_encode(10000, digits=4)

    def test_non_bcd_digit_field_raises(self):
        with self.assertRaises(ValueError):
            a429.bcd_decode(0b1010, digits=4)  # digit 10 in the low nibble

    def test_invalid_digits_count_raises(self):
        with self.assertRaises(ValueError):
            a429.bcd_encode(1, digits=6)
        with self.assertRaises(ValueError):
            a429.bcd_decode(1, digits=3)

    def test_negative_value_raises(self):
        with self.assertRaises(ValueError):
            a429.bcd_encode(-1)


class ParityConsistencyTest(unittest.TestCase):
    def test_built_words_always_odd_parity(self):
        words = [
            a429.build_word(0o10, 0, 0, 0),
            a429.build_word(0o377, 3, 0x7FFFF, 3),
            a429.build_word(0o320, 1, 555, 2),
            a429.build_word("012", 2, 999, 1),
        ]
        for word in words:
            self.assertEqual(bin(word).count("1") % 2, 1)
            self.assertTrue(a429.decode_word(word)["parity_ok"])

    def test_flipped_parity_bit_is_detected(self):
        fields = a429.decode_word(ANCHOR_WORD ^ (1 << 31))
        self.assertFalse(fields["parity_ok"])

    def test_non_integer_input_raises(self):
        with self.assertRaises(ValueError):
            a429.build_word(0o10, 1, 1234, "3")
        with self.assertRaises(ValueError):
            a429.bnr_encode("123.4", 0.1)
        with self.assertRaises(ValueError):
            a429.bcd_encode(True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
