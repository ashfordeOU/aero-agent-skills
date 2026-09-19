"""Contract tests for the clause 7.3.2 boolean parameter field logic."""

import unittest

from e7041_boolean_logic import (
    BITS_PER_OCTET,
    BOOLEAN_FORMAT_CODE,
    BOOLEAN_TYPE_CODE,
    BOOLEAN_WIDTH_BITS,
    assess_boolean_structure,
    boolean_width_bits,
    decode_boolean,
    encode_boolean,
    pack_booleans,
    padding_bits,
    unpack_booleans,
    validate_boolean_type_pair,
)


def flag(name, value, **extra):
    entry = {"name": name, "value": value}
    entry.update(extra)
    return entry


class TypePairTests(unittest.TestCase):
    def test_boolean_pair_is_accepted(self):
        self.assertEqual(
            validate_boolean_type_pair(BOOLEAN_TYPE_CODE, BOOLEAN_FORMAT_CODE),
            (1, 0),
        )

    def test_boolean_field_is_one_bit_wide(self):
        self.assertEqual(BOOLEAN_WIDTH_BITS, 1)
        self.assertEqual(boolean_width_bits(), 1)

    def test_another_type_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_boolean_type_pair(3, 0)

    def test_another_format_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_boolean_type_pair(1, 1)

    def test_truth_value_as_a_type_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_boolean_type_pair(True, 0)

    def test_non_integer_format_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_boolean_type_pair(1, "0")


class EncodeTests(unittest.TestCase):
    def test_true_encodes_to_a_set_bit(self):
        self.assertEqual(encode_boolean(True), 1)

    def test_false_encodes_to_a_clear_bit(self):
        self.assertEqual(encode_boolean(False), 0)

    def test_integer_one_is_not_a_truth_value(self):
        with self.assertRaises(ValueError):
            encode_boolean(1)

    def test_integer_zero_is_not_a_truth_value(self):
        with self.assertRaises(ValueError):
            encode_boolean(0)

    def test_the_string_true_is_rejected(self):
        with self.assertRaises(ValueError):
            encode_boolean("true")

    def test_an_empty_string_is_rejected_rather_than_read_as_false(self):
        with self.assertRaises(ValueError):
            encode_boolean("")

    def test_none_is_rejected_rather_than_read_as_false(self):
        with self.assertRaises(ValueError):
            encode_boolean(None)


class DecodeTests(unittest.TestCase):
    def test_set_bit_decodes_to_true(self):
        self.assertIs(decode_boolean(1), True)

    def test_clear_bit_decodes_to_false(self):
        self.assertIs(decode_boolean(0), False)

    def test_a_bit_of_two_rejected(self):
        with self.assertRaises(ValueError):
            decode_boolean(2)

    def test_a_negative_bit_rejected(self):
        with self.assertRaises(ValueError):
            decode_boolean(-1)

    def test_a_truth_value_is_not_a_bit(self):
        with self.assertRaises(ValueError):
            decode_boolean(True)


class PaddingTests(unittest.TestCase):
    def test_octet_is_eight_bits(self):
        self.assertEqual(BITS_PER_OCTET, 8)

    def test_one_field_needs_seven_pad_bits(self):
        self.assertEqual(padding_bits(1), 7)

    def test_eight_fields_need_none(self):
        self.assertEqual(padding_bits(8), 0)

    def test_nine_fields_need_seven(self):
        self.assertEqual(padding_bits(9), 7)

    def test_negative_bit_count_rejected(self):
        with self.assertRaises(ValueError):
            padding_bits(-1)


class PackTests(unittest.TestCase):
    def test_first_field_is_the_most_significant_bit(self):
        packed = pack_booleans([True, False, False, False, False, False, False, False])
        self.assertEqual(packed["octets"], [0x80])

    def test_last_field_of_a_full_octet_is_the_least_significant_bit(self):
        packed = pack_booleans([False] * 7 + [True])
        self.assertEqual(packed["octets"], [0x01])

    def test_all_set_fills_the_octet(self):
        self.assertEqual(pack_booleans([True] * 8)["octets"], [0xFF])

    def test_short_run_is_padded_with_clear_bits(self):
        packed = pack_booleans([True, True])
        self.assertEqual(packed["octets"], [0xC0])
        self.assertEqual(packed["padding_bits"], 6)

    def test_nine_fields_take_two_octets(self):
        packed = pack_booleans([True] * 9)
        self.assertEqual(len(packed["octets"]), 2)
        self.assertEqual(packed["octets"], [0xFF, 0x80])

    def test_empty_structure_rejected(self):
        with self.assertRaises(ValueError):
            pack_booleans([])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            pack_booleans(True)

    def test_a_non_truth_value_in_the_run_is_rejected(self):
        with self.assertRaises(ValueError):
            pack_booleans([True, 1])


class UnpackTests(unittest.TestCase):
    def test_unpack_reverses_pack(self):
        values = [True, False, True, True, False]
        packed = pack_booleans(values)
        self.assertEqual(unpack_booleans(packed["octets"], len(values)), values)

    def test_padding_is_not_decoded_as_a_field(self):
        packed = pack_booleans([True, True])
        self.assertEqual(len(unpack_booleans(packed["octets"], 2)), 2)

    def test_count_beyond_the_octets_rejected(self):
        with self.assertRaises(ValueError):
            unpack_booleans([0xFF], 9)

    def test_zero_field_count_rejected(self):
        with self.assertRaises(ValueError):
            unpack_booleans([0xFF], 0)

    def test_octet_above_the_range_rejected(self):
        with self.assertRaises(ValueError):
            unpack_booleans([256], 1)

    def test_negative_octet_rejected(self):
        with self.assertRaises(ValueError):
            unpack_booleans([-1], 1)

    def test_non_integer_octet_rejected(self):
        with self.assertRaises(ValueError):
            unpack_booleans(["ff"], 1)

    def test_round_trip_across_two_octets(self):
        values = [True, False, False, True, True, False, True, False, True]
        packed = pack_booleans(values)
        self.assertEqual(unpack_booleans(packed["octets"], len(values)), values)


class StructureTests(unittest.TestCase):
    def test_structure_reports_the_octets(self):
        result = assess_boolean_structure(
            [flag("heater-on", True), flag("valve-open", False)]
        )
        self.assertEqual(result["octets"], [0x80])
        self.assertEqual(result["octet_count"], 1)

    def test_structure_round_trips(self):
        result = assess_boolean_structure([flag("a", True), flag("b", True), flag("c", False)])
        self.assertTrue(result["round_trip_matches"])

    def test_wasted_bits_are_flagged(self):
        result = assess_boolean_structure([flag("a", True), flag("b", False)])
        self.assertEqual(result["padding_bits"], 6)
        self.assertTrue(any("carry no field" in f for f in result["findings"]))

    def test_a_lone_boolean_is_flagged_as_a_whole_octet(self):
        result = assess_boolean_structure([flag("a", True)])
        self.assertTrue(any("whole octet" in f for f in result["findings"]))

    def test_a_full_octet_of_flags_wastes_nothing(self):
        result = assess_boolean_structure([flag("f%d" % i, i % 2 == 0) for i in range(8)])
        self.assertEqual(result["padding_bits"], 0)
        self.assertEqual(result["findings"], [])

    def test_duplicate_names_are_flagged(self):
        result = assess_boolean_structure([flag("a", True)] * 8)
        self.assertTrue(any("duplicate field name" in f for f in result["findings"]))

    def test_a_non_boolean_type_code_in_a_field_rejected(self):
        with self.assertRaises(ValueError):
            assess_boolean_structure([flag("a", True, type_code=3)])

    def test_a_non_boolean_format_code_in_a_field_rejected(self):
        with self.assertRaises(ValueError):
            assess_boolean_structure([flag("a", True, format_code=2)])

    def test_blank_field_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_boolean_structure([flag("  ", True)])

    def test_missing_value_rejected(self):
        with self.assertRaises(ValueError):
            assess_boolean_structure([{"name": "a"}])

    def test_empty_structure_rejected(self):
        with self.assertRaises(ValueError):
            assess_boolean_structure([])


if __name__ == "__main__":
    unittest.main()
