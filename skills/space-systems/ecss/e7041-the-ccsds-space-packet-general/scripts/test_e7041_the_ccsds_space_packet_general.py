"""Contract tests for the clause 7.4.2 CCSDS space packet container logic."""

import unittest

from e7041_the_ccsds_space_packet_general_logic import (
    APID_MAX,
    IDLE_APID,
    MAX_DATA_FIELD_OCTETS,
    MIN_PACKET_OCTETS,
    PRIMARY_HEADER_OCTETS,
    SEQUENCE_COUNT_MAX,
    SEQUENCE_FLAG_NAMES,
    SUPPORTED_VERSION,
    TYPE_TELECOMMAND,
    TYPE_TELEMETRY,
    assess_space_packet,
    data_field_octets,
    data_length_field,
    decode_primary_header,
    encode_primary_header,
    sequence_gap,
    total_packet_octets,
    validate_primary_header,
)


def header_fields(**overrides):
    fields = {
        "packet_type": TYPE_TELEMETRY,
        "secondary_header_flag": 1,
        "apid": 100,
        "sequence_flags": 3,
        "sequence_count": 5,
        "data_octets": 10,
    }
    fields.update(overrides)
    return fields


def build(**overrides):
    fields = header_fields(**overrides)
    return encode_primary_header(fields) + [0] * fields["data_octets"]


class ConstantTests(unittest.TestCase):
    def test_the_primary_header_is_six_octets(self):
        self.assertEqual(PRIMARY_HEADER_OCTETS, 6)

    def test_the_supported_version_is_zero(self):
        self.assertEqual(SUPPORTED_VERSION, 0)

    def test_the_apid_is_eleven_bits(self):
        self.assertEqual(APID_MAX, 2047)

    def test_the_idle_apid_is_all_ones(self):
        self.assertEqual(IDLE_APID, APID_MAX)

    def test_the_sequence_count_is_fourteen_bits(self):
        self.assertEqual(SEQUENCE_COUNT_MAX, 16383)

    def test_all_four_sequence_flag_values_are_named(self):
        self.assertEqual(sorted(SEQUENCE_FLAG_NAMES), [0, 1, 2, 3])

    def test_the_smallest_packet_is_seven_octets(self):
        self.assertEqual(MIN_PACKET_OCTETS, 7)


class LengthFieldTests(unittest.TestCase):
    def test_the_field_states_one_less_than_the_data_field(self):
        self.assertEqual(data_length_field(10), 9)

    def test_a_single_data_octet_states_zero(self):
        self.assertEqual(data_length_field(1), 0)

    def test_the_largest_data_field_states_all_ones(self):
        self.assertEqual(data_length_field(MAX_DATA_FIELD_OCTETS), 0xFFFF)

    def test_a_header_only_packet_has_no_representation(self):
        with self.assertRaises(ValueError):
            data_length_field(0)

    def test_a_data_field_past_the_field_refused(self):
        with self.assertRaises(ValueError):
            data_length_field(MAX_DATA_FIELD_OCTETS + 1)

    def test_the_inverse_adds_the_one_back(self):
        self.assertEqual(data_field_octets(9), 10)

    def test_a_length_value_past_sixteen_bits_refused(self):
        with self.assertRaises(ValueError):
            data_field_octets(0x10000)

    def test_the_total_is_the_header_plus_the_data_field(self):
        self.assertEqual(total_packet_octets(10), 16)

    def test_a_zero_length_data_field_refused_by_the_total(self):
        with self.assertRaises(ValueError):
            total_packet_octets(0)


class HeaderValidationTests(unittest.TestCase):
    def test_a_well_formed_header_normalises(self):
        header = validate_primary_header(header_fields())
        self.assertEqual(header["total_octets"], 16)
        self.assertEqual(header["length_field"], 9)

    def test_the_type_is_named(self):
        header = validate_primary_header(header_fields(packet_type=TYPE_TELECOMMAND))
        self.assertEqual(header["packet_type_name"], "telecommand")

    def test_the_sequence_flags_are_named(self):
        header = validate_primary_header(header_fields(sequence_flags=1))
        self.assertEqual(header["sequence_flags_name"], "first-segment")

    def test_the_idle_apid_is_marked(self):
        header = validate_primary_header(header_fields(apid=IDLE_APID))
        self.assertTrue(header["idle"])

    def test_an_ordinary_apid_is_not_idle(self):
        self.assertFalse(validate_primary_header(header_fields())["idle"])

    def test_a_non_zero_version_refused(self):
        with self.assertRaises(ValueError):
            validate_primary_header(header_fields(version=1))

    def test_an_apid_past_eleven_bits_refused(self):
        with self.assertRaises(ValueError):
            validate_primary_header(header_fields(apid=APID_MAX + 1))

    def test_a_sequence_count_past_fourteen_bits_refused(self):
        with self.assertRaises(ValueError):
            validate_primary_header(header_fields(sequence_count=SEQUENCE_COUNT_MAX + 1))

    def test_an_out_of_range_type_refused(self):
        with self.assertRaises(ValueError):
            validate_primary_header(header_fields(packet_type=2))

    def test_an_out_of_range_sequence_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_primary_header(header_fields(sequence_flags=4))

    def test_a_boolean_field_refused(self):
        with self.assertRaises(ValueError):
            validate_primary_header(header_fields(apid=True))

    def test_a_non_mapping_refused(self):
        with self.assertRaises(ValueError):
            validate_primary_header([0, 100])


class CodingTests(unittest.TestCase):
    def test_the_header_encodes_to_six_octets(self):
        self.assertEqual(len(encode_primary_header(header_fields())), PRIMARY_HEADER_OCTETS)

    def test_the_apid_lands_in_the_low_eleven_bits_of_the_first_word(self):
        octets = encode_primary_header(header_fields(apid=0x123))
        self.assertEqual(((octets[0] << 8) | octets[1]) & APID_MAX, 0x123)

    def test_the_length_field_is_big_endian(self):
        octets = encode_primary_header(header_fields(data_octets=300))
        self.assertEqual((octets[4] << 8) | octets[5], 299)

    def test_the_round_trip_preserves_every_field(self):
        fields = header_fields(packet_type=TYPE_TELECOMMAND, apid=0x2AB,
                               sequence_flags=2, sequence_count=1234, data_octets=7)
        header = decode_primary_header(encode_primary_header(fields))
        for key, value in fields.items():
            self.assertEqual(header[key], value, key)

    def test_a_short_buffer_refused(self):
        with self.assertRaises(ValueError):
            decode_primary_header([0] * 5)

    def test_a_non_octet_refused(self):
        with self.assertRaises(ValueError):
            decode_primary_header([0, 0, 0, 0, 0, 300])

    def test_a_non_sequence_refused(self):
        with self.assertRaises(ValueError):
            decode_primary_header("header")

    def test_bytes_decode(self):
        header = decode_primary_header(bytes(encode_primary_header(header_fields())))
        self.assertEqual(header["apid"], 100)

    def test_a_decoded_non_zero_version_refused(self):
        octets = encode_primary_header(header_fields())
        octets[0] |= 0x20
        with self.assertRaises(ValueError):
            decode_primary_header(octets)


class SequenceGapTests(unittest.TestCase):
    def test_consecutive_counts_leave_no_gap(self):
        self.assertEqual(sequence_gap(5, 6), 0)

    def test_a_skipped_count_is_reported(self):
        self.assertEqual(sequence_gap(5, 9), 3)

    def test_the_counter_wrap_is_not_a_gap(self):
        self.assertEqual(sequence_gap(SEQUENCE_COUNT_MAX, 0), 0)

    def test_a_gap_across_the_wrap_is_measured(self):
        self.assertEqual(sequence_gap(SEQUENCE_COUNT_MAX - 1, 1), 2)

    def test_a_repeated_count_reads_as_a_full_span_gap(self):
        self.assertEqual(sequence_gap(5, 5), SEQUENCE_COUNT_MAX)

    def test_an_out_of_range_count_refused(self):
        with self.assertRaises(ValueError):
            sequence_gap(0, SEQUENCE_COUNT_MAX + 1)


class AssessmentTests(unittest.TestCase):
    def test_a_conformant_telemetry_packet_reports_nothing(self):
        report = assess_space_packet(build())
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["conformant"])

    def test_the_data_field_is_returned_whole(self):
        report = assess_space_packet(build(data_octets=4))
        self.assertEqual(len(report["data_field"]), 4)

    def test_a_buffer_shorter_than_the_stated_length_is_a_finding(self):
        packet = build(data_octets=10)[:-2]
        report = assess_space_packet(packet)
        self.assertTrue(any("octets are present" in f for f in report["findings"]))

    def test_a_telemetry_packet_on_the_uplink_is_a_finding(self):
        report = assess_space_packet(build(), direction="ground-to-space")
        self.assertTrue(any("disagree" in f for f in report["findings"]))

    def test_a_telecommand_packet_on_the_uplink_is_conformant(self):
        report = assess_space_packet(
            build(packet_type=TYPE_TELECOMMAND), direction="ground-to-space"
        )
        self.assertEqual(report["findings"], [])

    def test_a_service_packet_without_a_secondary_header_is_a_finding(self):
        report = assess_space_packet(build(secondary_header_flag=0))
        self.assertTrue(any("secondary header flag clear" in f for f in report["findings"]))

    def test_an_idle_apid_carrying_a_service_is_a_finding(self):
        report = assess_space_packet(build(apid=IDLE_APID))
        self.assertTrue(any("reserved for idle packets" in f for f in report["findings"]))

    def test_an_idle_packet_carrying_no_service_is_accepted(self):
        report = assess_space_packet(
            build(apid=IDLE_APID, secondary_header_flag=0), carries_a_service=False
        )
        self.assertEqual(report["findings"], [])

    def test_a_segmented_idle_packet_is_a_finding(self):
        report = assess_space_packet(
            build(apid=IDLE_APID, secondary_header_flag=0, sequence_flags=1),
            carries_a_service=False,
        )
        self.assertTrue(any("idle packet is segmented" in f for f in report["findings"]))

    def test_a_sequence_gap_is_a_finding(self):
        report = assess_space_packet(build(sequence_count=9), previous_count=5)
        self.assertEqual(report["sequence_gap"], 3)
        self.assertTrue(any("packets are missing" in f for f in report["findings"]))

    def test_no_gap_reports_zero(self):
        report = assess_space_packet(build(sequence_count=6), previous_count=5)
        self.assertEqual(report["sequence_gap"], 0)
        self.assertEqual(report["findings"], [])

    def test_an_unknown_direction_refused(self):
        with self.assertRaises(ValueError):
            assess_space_packet(build(), direction="crosslink")


if __name__ == "__main__":
    unittest.main()
