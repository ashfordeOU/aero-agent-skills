#!/usr/bin/env python3
"""Contract test for the enumerated parameter type (offline)."""

import unittest

from e7041_enumerated_logic import (
    ENUMERATED_PTC,
    MAX_FIELD_WIDTH_BITS,
    VERDICT_NO_HEADROOM,
    VERDICT_OVERFLOWS_FIELD,
    VERDICT_VALID,
    assess_enumerated_field,
    code_capacity,
    decode_code,
    encode_symbol,
    minimum_width_bits,
    round_trip_symbol,
    spare_codes,
    table_fits_field,
    validate_field_width,
    validate_symbol_table,
)

MODE_SYMBOLS = {0: "off", 1: "standby", 2: "nominal", 3: "safe"}
SPARSE_SYMBOLS = {0: "off", 7: "safe"}


class FieldWidthTests(unittest.TestCase):
    def test_a_plausible_width_is_accepted(self):
        self.assertEqual(validate_field_width(8), 8)

    def test_zero_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width(0)

    def test_width_beyond_the_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width(MAX_FIELD_WIDTH_BITS + 1)

    def test_non_integer_width_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width(8.0)

    def test_boolean_is_not_an_integer_width(self):
        with self.assertRaises(ValueError):
            validate_field_width(True)

    def test_capacity_doubles_with_each_bit(self):
        self.assertEqual(code_capacity(1), 2)
        self.assertEqual(code_capacity(4), 16)
        self.assertEqual(code_capacity(8), 256)


class MinimumWidthTests(unittest.TestCase):
    def test_a_single_symbol_still_needs_a_bit(self):
        self.assertEqual(minimum_width_bits(1), 1)

    def test_two_symbols_need_one_bit(self):
        self.assertEqual(minimum_width_bits(2), 1)

    def test_five_symbols_need_three_bits(self):
        self.assertEqual(minimum_width_bits(5), 3)

    def test_an_exact_power_of_two_does_not_spill_into_an_extra_bit(self):
        self.assertEqual(minimum_width_bits(256), 8)

    def test_one_past_a_power_of_two_takes_the_extra_bit(self):
        self.assertEqual(minimum_width_bits(257), 9)

    def test_zero_symbols_rejected(self):
        with self.assertRaises(ValueError):
            minimum_width_bits(0)


class SymbolTableTests(unittest.TestCase):
    def test_a_well_formed_table_is_accepted(self):
        self.assertIs(validate_symbol_table(MODE_SYMBOLS), MODE_SYMBOLS)

    def test_an_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_symbol_table({})

    def test_a_negative_code_rejected(self):
        with self.assertRaises(ValueError):
            validate_symbol_table({-1: "off"})

    def test_a_blank_symbol_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_symbol_table({0: "   "})

    def test_a_duplicated_symbol_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_symbol_table({0: "safe", 1: "safe"})

    def test_a_non_mapping_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_symbol_table([("0", "off")])

    def test_a_table_within_the_field_fits(self):
        self.assertTrue(table_fits_field(MODE_SYMBOLS, 2))

    def test_a_table_reaching_past_the_field_does_not_fit(self):
        self.assertFalse(table_fits_field(SPARSE_SYMBOLS, 2))


class EncodeDecodeTests(unittest.TestCase):
    def test_a_declared_symbol_encodes_to_its_code(self):
        self.assertEqual(encode_symbol(MODE_SYMBOLS, 2, "nominal"), 2)

    def test_an_undeclared_symbol_is_refused(self):
        with self.assertRaises(ValueError):
            encode_symbol(MODE_SYMBOLS, 2, "hibernate")

    def test_a_symbol_outside_the_field_is_refused(self):
        with self.assertRaises(ValueError):
            encode_symbol(SPARSE_SYMBOLS, 2, "safe")

    def test_a_declared_code_decodes_to_its_symbol(self):
        result = decode_code(MODE_SYMBOLS, 2, 3)
        self.assertEqual(result["symbol"], "safe")
        self.assertTrue(result["defined"])
        self.assertEqual(result["findings"], [])

    def test_an_undeclared_code_is_reported_undefined_not_defaulted(self):
        result = decode_code(SPARSE_SYMBOLS, 3, 4)
        self.assertFalse(result["defined"])
        self.assertIsNone(result["symbol"])
        self.assertTrue(any("undefined" in f for f in result["findings"]))

    def test_a_code_wider_than_the_field_is_refused(self):
        with self.assertRaises(ValueError):
            decode_code(MODE_SYMBOLS, 2, 4)

    def test_a_negative_code_is_refused(self):
        with self.assertRaises(ValueError):
            decode_code(MODE_SYMBOLS, 2, -1)

    def test_every_declared_symbol_survives_a_round_trip(self):
        for name in MODE_SYMBOLS.values():
            result = round_trip_symbol(MODE_SYMBOLS, 2, name)
            self.assertEqual(result["symbol"], name)
            self.assertTrue(result["defined"])


class SpareCodeTests(unittest.TestCase):
    def test_a_full_field_leaves_no_spare_codes(self):
        self.assertEqual(spare_codes(MODE_SYMBOLS, 2), [])

    def test_a_wider_field_leaves_the_unclaimed_codes(self):
        self.assertEqual(spare_codes(MODE_SYMBOLS, 3), [4, 5, 6, 7])

    def test_a_sparse_table_leaves_the_gaps_between_its_codes(self):
        self.assertEqual(spare_codes(SPARSE_SYMBOLS, 3), [1, 2, 3, 4, 5, 6])


class AssessmentTests(unittest.TestCase):
    def test_a_field_with_room_to_grow_is_valid(self):
        result = assess_enumerated_field({"symbols": MODE_SYMBOLS, "width_bits": 3})
        self.assertEqual(result["verdict"], VERDICT_VALID)
        self.assertEqual(result["ptc"], ENUMERATED_PTC)
        self.assertEqual(result["spare_code_count"], 4)

    def test_an_exactly_filled_field_reports_no_headroom(self):
        result = assess_enumerated_field({"symbols": MODE_SYMBOLS, "width_bits": 2})
        self.assertEqual(result["verdict"], VERDICT_NO_HEADROOM)
        self.assertEqual(result["spare_code_count"], 0)
        self.assertTrue(any("widening" in f for f in result["findings"]))

    def test_a_table_past_the_field_overflows(self):
        result = assess_enumerated_field({"symbols": SPARSE_SYMBOLS, "width_bits": 2})
        self.assertEqual(result["verdict"], VERDICT_OVERFLOWS_FIELD)
        self.assertFalse(result["fits"])
        self.assertEqual(result["minimum_width_bits"], 3)

    def test_an_oversized_field_is_reported_as_slack(self):
        result = assess_enumerated_field({"symbols": MODE_SYMBOLS, "width_bits": 8})
        self.assertEqual(result["verdict"], VERDICT_VALID)
        self.assertTrue(any("would hold" in f for f in result["findings"]))

    def test_capacity_and_symbol_count_are_reported(self):
        result = assess_enumerated_field({"symbols": MODE_SYMBOLS, "width_bits": 4})
        self.assertEqual(result["capacity"], 16)
        self.assertEqual(result["symbol_count"], 4)

    def test_a_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_enumerated_field("mode")

    def test_a_spec_without_a_width_rejected(self):
        with self.assertRaises(ValueError):
            assess_enumerated_field({"symbols": MODE_SYMBOLS})


if __name__ == "__main__":
    unittest.main()
