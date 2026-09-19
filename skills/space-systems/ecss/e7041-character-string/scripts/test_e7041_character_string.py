"""Contract tests for the clause 7.3.9 character-string data-type logic."""

import unittest

from e7041_character_string_logic import (
    DEFAULT_PAD_OCTET,
    MAX_COUNT_BITS,
    REPERTOIRES,
    assess_character_string_definition,
    count_field_capacity,
    decode_character_string,
    encode_character_string,
    field_size_bits,
    minimum_count_bits,
    repertoire_octets,
    validate_spec,
)

FIXED = {"kind": "fixed", "length": 8, "repertoire": "ascii-printable", "pad_octet": 0x00}
FIXED_SPACE_PAD = {"kind": "fixed", "length": 8, "repertoire": "ascii-printable", "pad_octet": 0x20}
VARIABLE = {"kind": "variable", "max_length": 32, "count_bits": 8, "repertoire": "ascii-printable"}


class RepertoireTests(unittest.TestCase):
    def test_printable_range_excludes_control_octets(self):
        low, high = repertoire_octets("ascii-printable")
        self.assertEqual((low, high), (0x20, 0x7E))

    def test_visible_range_excludes_the_space(self):
        low, _ = repertoire_octets("ascii-visible")
        self.assertEqual(low, 0x21)

    def test_every_named_repertoire_is_an_ordered_range(self):
        for name, (low, high) in REPERTOIRES.items():
            self.assertLess(low, high, name)

    def test_unknown_repertoire_refused(self):
        with self.assertRaises(ValueError):
            repertoire_octets("latin-9")

    def test_non_string_repertoire_refused(self):
        with self.assertRaises(ValueError):
            repertoire_octets(7)


class CountFieldTests(unittest.TestCase):
    def test_capacity_is_all_ones(self):
        self.assertEqual(count_field_capacity(8), 255)

    def test_single_bit_count_reaches_one_character(self):
        self.assertEqual(count_field_capacity(1), 1)

    def test_zero_width_count_refused(self):
        with self.assertRaises(ValueError):
            count_field_capacity(0)

    def test_absurdly_wide_count_refused(self):
        with self.assertRaises(ValueError):
            count_field_capacity(MAX_COUNT_BITS + 1)

    def test_minimum_bits_for_an_exact_power_boundary(self):
        self.assertEqual(minimum_count_bits(255), 8)

    def test_minimum_bits_rolls_over_past_the_boundary(self):
        self.assertEqual(minimum_count_bits(256), 9)

    def test_negative_maximum_refused(self):
        with self.assertRaises(ValueError):
            minimum_count_bits(-1)


class ValidateSpecTests(unittest.TestCase):
    def test_fixed_definition_normalises(self):
        out = validate_spec(FIXED)
        self.assertEqual(out["length"], 8)
        self.assertEqual(out["max_length"], 8)
        self.assertEqual(out["count_bits"], 0)

    def test_variable_definition_reports_its_capacity(self):
        out = validate_spec(VARIABLE)
        self.assertEqual(out["count_capacity"], 255)

    def test_default_pad_octet_applied(self):
        out = validate_spec({"kind": "fixed", "length": 4})
        self.assertEqual(out["pad_octet"], DEFAULT_PAD_OCTET)

    def test_count_field_too_narrow_for_the_declared_maximum_refused(self):
        with self.assertRaises(ValueError):
            validate_spec({"kind": "variable", "max_length": 300, "count_bits": 8})

    def test_count_field_exactly_reaching_the_maximum_accepted(self):
        out = validate_spec({"kind": "variable", "max_length": 255, "count_bits": 8})
        self.assertEqual(out["count_capacity"], 255)

    def test_padding_a_variable_length_field_refused(self):
        bad = dict(VARIABLE)
        bad["pad_octet"] = 0x20
        with self.assertRaises(ValueError):
            validate_spec(bad)

    def test_unknown_kind_refused(self):
        with self.assertRaises(ValueError):
            validate_spec({"kind": "counted", "length": 4})

    def test_zero_length_fixed_field_refused(self):
        with self.assertRaises(ValueError):
            validate_spec({"kind": "fixed", "length": 0})

    def test_out_of_range_pad_octet_refused(self):
        with self.assertRaises(ValueError):
            validate_spec({"kind": "fixed", "length": 4, "pad_octet": 300})

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            validate_spec(["fixed", 8])


class EncodeTests(unittest.TestCase):
    def test_fixed_value_is_padded_to_the_field(self):
        out = encode_character_string("ABC", FIXED)
        self.assertEqual(out["octets"], [65, 66, 67, 0, 0, 0, 0, 0])
        self.assertEqual(out["padding_octets"], 5)

    def test_fixed_value_filling_the_field_has_no_padding(self):
        out = encode_character_string("ABCDEFGH", FIXED)
        self.assertEqual(out["padding_octets"], 0)

    def test_variable_value_carries_its_count(self):
        out = encode_character_string("TM-DUMP", VARIABLE)
        self.assertEqual(out["count"], 7)
        self.assertEqual(len(out["octets"]), 7)

    def test_one_octet_per_character(self):
        out = encode_character_string("A1-b", VARIABLE)
        self.assertEqual(out["octets"], [0x41, 0x31, 0x2D, 0x62])

    def test_value_longer_than_the_fixed_field_refused(self):
        with self.assertRaises(ValueError):
            encode_character_string("ABCDEFGHI", FIXED)

    def test_value_past_the_declared_maximum_refused(self):
        with self.assertRaises(ValueError):
            encode_character_string("X" * 33, VARIABLE)

    def test_character_outside_the_repertoire_refused(self):
        with self.assertRaises(ValueError):
            encode_character_string("line\nbreak", VARIABLE)

    def test_non_string_value_refused(self):
        with self.assertRaises(ValueError):
            encode_character_string(1234, VARIABLE)

    def test_space_refused_by_the_visible_repertoire(self):
        spec = {"kind": "variable", "max_length": 16, "count_bits": 8,
                "repertoire": "ascii-visible"}
        with self.assertRaises(ValueError):
            encode_character_string("A B", spec)


class DecodeTests(unittest.TestCase):
    def test_fixed_round_trip_drops_the_padding(self):
        out = encode_character_string("EVT", FIXED)
        back = decode_character_string(out["octets"], FIXED)
        self.assertEqual(back["value"], "EVT")
        self.assertEqual(back["padding_octets"], 5)

    def test_variable_round_trip_uses_the_count(self):
        out = encode_character_string("PKT-STORE", VARIABLE)
        back = decode_character_string(out["octets"], VARIABLE, count=out["count"])
        self.assertEqual(back["value"], "PKT-STORE")

    def test_space_padding_is_reported_as_ambiguous(self):
        out = encode_character_string("EVT", FIXED_SPACE_PAD)
        back = decode_character_string(out["octets"], FIXED_SPACE_PAD)
        self.assertTrue(back["pad_in_repertoire"])

    def test_space_padding_loses_a_trailing_space(self):
        out = encode_character_string("EVT ", FIXED_SPACE_PAD)
        back = decode_character_string(out["octets"], FIXED_SPACE_PAD)
        self.assertEqual(back["value"], "EVT")

    def test_null_padding_keeps_a_trailing_space(self):
        out = encode_character_string("EVT ", FIXED)
        back = decode_character_string(out["octets"], FIXED)
        self.assertEqual(back["value"], "EVT ")
        self.assertFalse(back["pad_in_repertoire"])

    def test_wrong_octet_count_for_a_fixed_field_refused(self):
        with self.assertRaises(ValueError):
            decode_character_string([65, 66], FIXED)

    def test_count_supplied_for_a_fixed_field_refused(self):
        with self.assertRaises(ValueError):
            decode_character_string([65] * 8, FIXED, count=3)

    def test_missing_count_for_a_variable_field_refused(self):
        with self.assertRaises(ValueError):
            decode_character_string([65, 66, 67], VARIABLE)

    def test_count_beyond_the_octets_present_refused(self):
        with self.assertRaises(ValueError):
            decode_character_string([65, 66, 67], VARIABLE, count=9)

    def test_count_beyond_the_declared_maximum_refused(self):
        with self.assertRaises(ValueError):
            decode_character_string([65] * 40, VARIABLE, count=40)

    def test_octet_outside_the_repertoire_refused(self):
        with self.assertRaises(ValueError):
            decode_character_string([0x07, 66, 67], VARIABLE, count=3)

    def test_non_octet_item_refused(self):
        with self.assertRaises(ValueError):
            decode_character_string([65, 300, 67], VARIABLE, count=3)


class FieldSizeTests(unittest.TestCase):
    def test_fixed_field_is_eight_bits_per_character(self):
        self.assertEqual(field_size_bits(FIXED), 64)

    def test_variable_envelope_reserves_the_maximum(self):
        self.assertEqual(field_size_bits(VARIABLE), 8 + 8 * 32)

    def test_packed_variable_field_sizes_the_value(self):
        self.assertEqual(field_size_bits(VARIABLE, "packed", "ABCD"), 8 + 32)

    def test_packed_without_a_value_refused(self):
        with self.assertRaises(ValueError):
            field_size_bits(VARIABLE, "packed")

    def test_unknown_packing_refused(self):
        with self.assertRaises(ValueError):
            field_size_bits(VARIABLE, "bit-aligned")


class AssessmentTests(unittest.TestCase):
    def test_a_clean_definition_reports_no_findings(self):
        report = assess_character_string_definition(VARIABLE, ["MEM-A", "MEM-B"])
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["usable"])

    def test_pad_inside_the_repertoire_is_a_finding(self):
        report = assess_character_string_definition(FIXED_SPACE_PAD, ["EVT"])
        self.assertTrue(any("cannot be told from padding" in f for f in report["findings"]))

    def test_a_refused_sample_is_grouped_as_rejected(self):
        report = assess_character_string_definition(VARIABLE, ["ok", "bad\tvalue"])
        self.assertEqual(len(report["rejected"]), 1)
        self.assertFalse(report["usable"])

    def test_a_padding_dominated_fixed_field_is_a_finding(self):
        report = assess_character_string_definition(FIXED, ["AB", "ABC"])
        self.assertTrue(any("padding on every occurrence" in f for f in report["findings"]))

    def test_an_oversized_count_field_is_a_finding(self):
        spec = {"kind": "variable", "max_length": 4, "count_bits": 16}
        report = assess_character_string_definition(spec, ["ABCD"])
        self.assertTrue(any("far wider" in f for f in report["findings"]))

    def test_envelope_bits_reported(self):
        report = assess_character_string_definition(FIXED, ["ABCDEFG"])
        self.assertEqual(report["envelope_bits"], 64)


if __name__ == "__main__":
    unittest.main()
