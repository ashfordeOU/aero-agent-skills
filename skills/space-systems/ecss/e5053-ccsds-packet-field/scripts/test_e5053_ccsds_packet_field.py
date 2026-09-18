"""Contract tests for the clause 5.4.1.7 CCSDS Packet field occupancy logic."""

import unittest

from e5053_ccsds_packet_field_logic import (
    IDLE_APID,
    MAX_SPACE_PACKET_OCTETS,
    PRIMARY_HEADER_OCTETS,
    SPACE_PACKET_VERSION_1,
    assess_ccsds_packet_field,
    declared_total_length,
    parse_primary_header,
    scan_field,
    validate_octets,
)


def build_packet(apid=0x2A, data_octets=4, version=SPACE_PACKET_VERSION_1,
                 packet_type=0, secondary_header_flag=0, sequence_flags=3,
                 sequence_count=1):
    """Build a well-formed space packet with a data field of data_octets."""
    length_field = data_octets - 1
    b0 = ((version & 0x07) << 5) | ((packet_type & 0x01) << 4) \
        | ((secondary_header_flag & 0x01) << 3) | ((apid >> 8) & 0x07)
    b1 = apid & 0xFF
    b2 = ((sequence_flags & 0x03) << 6) | ((sequence_count >> 8) & 0x3F)
    b3 = sequence_count & 0xFF
    b4 = (length_field >> 8) & 0xFF
    b5 = length_field & 0xFF
    return [b0, b1, b2, b3, b4, b5] + [0x5A] * data_octets


GOOD = build_packet()


class ValidateOctetsTests(unittest.TestCase):
    def test_list_becomes_tuple(self):
        self.assertEqual(validate_octets([0, 255, 7]), (0, 255, 7))

    def test_bytes_accepted(self):
        self.assertEqual(validate_octets(bytes([1, 2, 3])), (1, 2, 3))

    def test_text_rejected(self):
        with self.assertRaises(ValueError):
            validate_octets("010203")

    def test_out_of_range_octet_rejected(self):
        with self.assertRaises(ValueError):
            validate_octets([0, 256])

    def test_negative_octet_rejected(self):
        with self.assertRaises(ValueError):
            validate_octets([-1, 4])

    def test_boolean_octet_rejected(self):
        with self.assertRaises(ValueError):
            validate_octets([True, 4])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_octets(17)


class PrimaryHeaderTests(unittest.TestCase):
    def test_apid_spans_the_two_header_octets(self):
        header = parse_primary_header(build_packet(apid=0x2AB))
        self.assertEqual(header["apid"], 0x2AB)

    def test_version_and_flags_decoded(self):
        header = parse_primary_header(
            build_packet(packet_type=1, secondary_header_flag=1, sequence_flags=2)
        )
        self.assertEqual(header["version"], SPACE_PACKET_VERSION_1)
        self.assertEqual(header["packet_type"], 1)
        self.assertEqual(header["secondary_header_flag"], 1)
        self.assertEqual(header["sequence_flags"], 2)

    def test_sequence_count_spans_fourteen_bits(self):
        header = parse_primary_header(build_packet(sequence_count=0x3FFF))
        self.assertEqual(header["sequence_count"], 0x3FFF)

    def test_data_length_field_is_one_less_than_the_data_field(self):
        header = parse_primary_header(build_packet(data_octets=16))
        self.assertEqual(header["data_length_field"], 15)

    def test_short_field_rejected(self):
        with self.assertRaises(ValueError):
            parse_primary_header([0, 1, 2])

    def test_offset_past_the_end_rejected(self):
        with self.assertRaises(ValueError):
            parse_primary_header(GOOD, offset=len(GOOD))

    def test_negative_offset_rejected(self):
        with self.assertRaises(ValueError):
            parse_primary_header(GOOD, offset=-1)

    def test_non_integer_offset_rejected(self):
        with self.assertRaises(ValueError):
            parse_primary_header(GOOD, offset=1.5)


class DeclaredLengthTests(unittest.TestCase):
    def test_total_is_header_plus_data_field(self):
        header = parse_primary_header(build_packet(data_octets=10))
        self.assertEqual(declared_total_length(header), PRIMARY_HEADER_OCTETS + 10)

    def test_minimum_data_field_is_one_octet(self):
        self.assertEqual(
            declared_total_length({"data_length_field": 0}), PRIMARY_HEADER_OCTETS + 1
        )

    def test_maximum_data_field_matches_the_expressible_maximum(self):
        self.assertEqual(
            declared_total_length({"data_length_field": 0xFFFF}), MAX_SPACE_PACKET_OCTETS
        )

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            declared_total_length({"apid": 3})

    def test_out_of_range_length_field_rejected(self):
        with self.assertRaises(ValueError):
            declared_total_length({"data_length_field": 0x10000})

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            declared_total_length([0, 1])


class ScanFieldTests(unittest.TestCase):
    def test_single_packet_gives_one_span(self):
        spans = scan_field(GOOD)
        self.assertEqual(len(spans), 1)
        self.assertTrue(spans[0]["complete"])

    def test_two_packets_give_two_spans(self):
        spans = scan_field(GOOD + build_packet(apid=0x30, data_octets=2))
        self.assertEqual(len(spans), 2)
        self.assertEqual(spans[1]["offset"], len(GOOD))

    def test_trailing_stub_is_reported_incomplete(self):
        spans = scan_field(GOOD + [0x08, 0x2A])
        self.assertEqual(len(spans), 2)
        self.assertFalse(spans[1]["complete"])

    def test_truncated_lead_packet_is_incomplete(self):
        spans = scan_field(GOOD[:-2])
        self.assertFalse(spans[0]["complete"])


class AssessmentTests(unittest.TestCase):
    def test_one_whole_packet_is_compliant(self):
        result = assess_ccsds_packet_field(GOOD)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["packet_count"], 1)

    def test_declared_and_present_agree_on_a_good_field(self):
        result = assess_ccsds_packet_field(GOOD)
        self.assertEqual(result["declared_length"], result["present_length"])
        self.assertEqual(result["surplus_octets"], 0)

    def test_truncated_packet_is_flagged(self):
        result = assess_ccsds_packet_field(GOOD[:-1])
        self.assertFalse(result["compliant"])
        self.assertIn("truncated", result["findings"][0])

    def test_surplus_tail_is_flagged(self):
        result = assess_ccsds_packet_field(GOOD + [0x00, 0x00])
        self.assertFalse(result["compliant"])
        self.assertEqual(result["surplus_octets"], 2)

    def test_second_packet_in_the_field_is_flagged(self):
        result = assess_ccsds_packet_field(GOOD + build_packet(apid=0x31, data_octets=3))
        self.assertFalse(result["compliant"])
        self.assertEqual(result["packet_count"], 2)

    def test_empty_field_is_flagged(self):
        result = assess_ccsds_packet_field([])
        self.assertFalse(result["compliant"])
        self.assertEqual(result["present_length"], 0)

    def test_header_stub_is_flagged(self):
        result = assess_ccsds_packet_field([0x08, 0x2A, 0xC0])
        self.assertFalse(result["compliant"])
        self.assertIsNone(result["header"])

    def test_wrong_packet_version_is_flagged(self):
        result = assess_ccsds_packet_field(build_packet(version=1))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("version" in f for f in result["findings"]))

    def test_idle_apid_is_flagged_as_user_data(self):
        result = assess_ccsds_packet_field(build_packet(apid=IDLE_APID))
        self.assertFalse(result["compliant"])

    def test_idle_apid_accepted_when_fill_is_expected(self):
        result = assess_ccsds_packet_field(
            build_packet(apid=IDLE_APID), expect_user_data=False
        )
        self.assertTrue(result["compliant"])

    def test_non_boolean_expectation_rejected(self):
        with self.assertRaises(ValueError):
            assess_ccsds_packet_field(GOOD, expect_user_data="yes")

    def test_bad_octet_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_ccsds_packet_field([0x08, 0x2A, 0xC0, 0x01, 0x00, 300])


if __name__ == "__main__":
    unittest.main()
