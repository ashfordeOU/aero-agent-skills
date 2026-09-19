"""Contract tests for the clause 7.4.3.2 telemetry user data field logic."""

import unittest

from e7041_telemetry_user_data_field_logic import (
    DEFAULT_ERROR_CONTROL_BITS,
    DEFAULT_MAX_PACKET_DATA_FIELD_OCTETS,
    MAX_SPARE_BITS,
    OCTET_BITS,
    PRIMARY_HEADER_OCTETS,
    assess_user_data_field,
    body_bits,
    packet_data_field_octets,
    packet_data_length_field,
    parameter_offsets,
    resolve_body_layout,
    spare_bits_for_alignment,
    total_packet_octets,
    user_data_field_bits,
    user_data_field_octets,
    validate_bit_count,
)

HK_BODY = [
    ("structure-id", 8),
    ("bus-voltage", 16),
    ("bus-current", 16),
    ("battery-temperature", 16),
]

RAGGED_BODY = [
    ("enable-flag", 1),
    ("mode-word", 4),
]


class BitCountTests(unittest.TestCase):
    def test_zero_is_allowed_by_default(self):
        self.assertEqual(validate_bit_count(0, "spare"), 0)

    def test_zero_rejected_when_positive_required(self):
        with self.assertRaises(ValueError):
            validate_bit_count(0, "width", allow_zero=False)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_bit_count(-8, "width")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_bit_count(True, "width")

    def test_float_rejected(self):
        with self.assertRaises(ValueError):
            validate_bit_count(8.0, "width")


class BodyLayoutTests(unittest.TestCase):
    def test_layout_keeps_the_declared_order(self):
        layout = resolve_body_layout(HK_BODY)
        self.assertEqual([name for name, _w in layout], [n for n, _w in HK_BODY])

    def test_body_width_is_the_sum(self):
        self.assertEqual(body_bits(HK_BODY), 56)

    def test_empty_body_is_allowed(self):
        self.assertEqual(resolve_body_layout([]), [])

    def test_duplicate_parameter_name_rejected(self):
        with self.assertRaises(ValueError):
            resolve_body_layout([("a", 8), ("a", 8)])

    def test_blank_parameter_name_rejected(self):
        with self.assertRaises(ValueError):
            resolve_body_layout([("  ", 8)])

    def test_zero_width_parameter_rejected(self):
        with self.assertRaises(ValueError):
            resolve_body_layout([("a", 0)])

    def test_malformed_parameter_rejected(self):
        with self.assertRaises(ValueError):
            resolve_body_layout([("a", 8, 1)])

    def test_string_instead_of_sequence_rejected(self):
        with self.assertRaises(ValueError):
            resolve_body_layout("structure-id")


class OffsetTests(unittest.TestCase):
    def test_first_parameter_starts_at_zero(self):
        records = parameter_offsets(HK_BODY)
        self.assertEqual(records[0]["offset_bits"], 0)
        self.assertTrue(records[0]["octet_aligned"])

    def test_offsets_accumulate(self):
        records = parameter_offsets(HK_BODY)
        self.assertEqual(records[2]["offset_bits"], 24)
        self.assertEqual(records[2]["octet"], 3)

    def test_sub_octet_parameter_is_not_aligned(self):
        records = parameter_offsets(RAGGED_BODY)
        self.assertFalse(records[1]["octet_aligned"])
        self.assertEqual(records[1]["bit_in_octet"], 1)

    def test_one_record_per_parameter(self):
        self.assertEqual(len(parameter_offsets(HK_BODY)), len(HK_BODY))


class SpareTests(unittest.TestCase):
    def test_aligned_body_needs_no_spare(self):
        self.assertEqual(spare_bits_for_alignment(56), 0)

    def test_one_bit_body_needs_seven_spare(self):
        self.assertEqual(spare_bits_for_alignment(1), 7)

    def test_five_bit_body_needs_three_spare(self):
        self.assertEqual(spare_bits_for_alignment(5), 3)

    def test_spare_never_reaches_a_whole_octet(self):
        for bits in range(0, 64):
            self.assertLessEqual(spare_bits_for_alignment(bits), MAX_SPARE_BITS)

    def test_negative_body_rejected(self):
        with self.assertRaises(ValueError):
            spare_bits_for_alignment(-1)


class UserDataFieldTests(unittest.TestCase):
    def test_aligned_body_without_error_control(self):
        total, spare = user_data_field_bits(56)
        self.assertEqual((total, spare), (56, 0))

    def test_ragged_body_is_padded_before_error_control(self):
        total, spare = user_data_field_bits(5, DEFAULT_ERROR_CONTROL_BITS)
        self.assertEqual(spare, 3)
        self.assertEqual(total, 5 + 3 + DEFAULT_ERROR_CONTROL_BITS)

    def test_octet_count_matches_the_bit_total(self):
        self.assertEqual(user_data_field_octets(56, 16), 9)

    def test_error_control_must_be_whole_octets(self):
        with self.assertRaises(ValueError):
            user_data_field_bits(56, 12)

    def test_zero_body_with_error_control_only(self):
        self.assertEqual(user_data_field_octets(0, 16), 2)


class PacketLengthTests(unittest.TestCase):
    def test_data_field_adds_the_secondary_header(self):
        self.assertEqual(packet_data_field_octets(13, 9), 22)

    def test_length_field_counts_one_less(self):
        self.assertEqual(packet_data_length_field(22), 21)

    def test_single_octet_data_field_gives_zero(self):
        self.assertEqual(packet_data_length_field(1), 0)

    def test_empty_data_field_rejected(self):
        with self.assertRaises(ValueError):
            packet_data_field_octets(0, 0)

    def test_zero_length_field_rejected(self):
        with self.assertRaises(ValueError):
            packet_data_length_field(0)

    def test_total_packet_includes_the_primary_header(self):
        self.assertEqual(total_packet_octets(22), 22 + PRIMARY_HEADER_OCTETS)

    def test_primary_header_width_is_overridable(self):
        self.assertEqual(total_packet_octets(22, 0), 22)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "parameters": list(HK_BODY),
            "secondary_header_octets": 13,
            "carries_error_control": True,
        }
        spec.update(overrides)
        return spec

    def test_well_formed_report_is_compliant(self):
        result = assess_user_data_field(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_lengths_are_consistent_with_each_other(self):
        result = assess_user_data_field(self._spec())
        self.assertEqual(result["user_data_field_octets"], 9)
        self.assertEqual(result["packet_data_field_octets"], 22)
        self.assertEqual(result["packet_data_length_field"], 21)
        self.assertEqual(
            result["total_packet_octets"], 22 + PRIMARY_HEADER_OCTETS
        )

    def test_error_control_is_dropped_when_the_mission_has_none(self):
        result = assess_user_data_field(self._spec(carries_error_control=False))
        self.assertEqual(result["error_control_bits"], 0)
        self.assertEqual(result["user_data_field_octets"], 7)

    def test_ragged_body_reports_the_spare(self):
        result = assess_user_data_field(self._spec(parameters=list(RAGGED_BODY)))
        self.assertEqual(result["spare_bits"], 3)
        self.assertTrue(any("spare" in f for f in result["findings"]))

    def test_empty_body_is_flagged(self):
        result = assess_user_data_field(self._spec(parameters=[]))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("no parameters" in f for f in result["findings"]))

    def test_oversize_packet_is_flagged(self):
        result = assess_user_data_field(
            self._spec(parameters=[("bulk-dump", 8 * 4096)],
                       max_packet_data_field_octets=1024)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("above the" in f for f in result["findings"]))

    def test_default_limit_is_the_space_packet_limit(self):
        result = assess_user_data_field(self._spec())
        self.assertLess(
            result["packet_data_field_octets"],
            DEFAULT_MAX_PACKET_DATA_FIELD_OCTETS,
        )

    def test_parameters_crossing_an_octet_boundary_are_named(self):
        result = assess_user_data_field(self._spec(parameters=list(RAGGED_BODY)))
        self.assertEqual(result["parameters_crossing_an_octet_boundary"], ["mode-word"])

    def test_error_control_width_without_the_field_rejected(self):
        with self.assertRaises(ValueError):
            assess_user_data_field(
                self._spec(carries_error_control=False, error_control_bits=16)
            )

    def test_non_boolean_error_control_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_user_data_field(self._spec(carries_error_control="yes"))

    def test_missing_secondary_header_key_rejected(self):
        spec = self._spec()
        del spec["secondary_header_octets"]
        with self.assertRaises(ValueError):
            assess_user_data_field(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_user_data_field(["parameters"])

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_user_data_field(self._spec(max_packet_data_field_octets=0))

    def test_octet_constant_is_eight(self):
        self.assertEqual(OCTET_BITS, 8)


if __name__ == "__main__":
    unittest.main()
