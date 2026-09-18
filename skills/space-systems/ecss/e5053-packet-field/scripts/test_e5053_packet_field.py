#!/usr/bin/env python3
"""Contract test for the packet field (offline)."""

import copy
import unittest

from e5053_packet_field_logic import (
    COMPLETE,
    OVERRUN,
    OVER_LIMIT,
    PRIMARY_HEADER_OCTETS,
    TRUNCATED,
    assess_packet_field,
    decode_primary_header,
    encode_primary_header,
    packet_field_offset,
    space_packet_length,
    split_packet_field,
    validate_packet_field,
)

HEADER = encode_primary_header(0x2AB, 17, 4)
PACKET = list(HEADER) + [1, 2, 3, 4]
PREFIX = [3, 7, 40, 2, 0, 5]

BASE_CASE = {"octets": PREFIX + PACKET, "path_length": 2}


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


class OffsetTests(unittest.TestCase):
    def test_pathless_unit_starts_the_packet_fifth(self):
        self.assertEqual(packet_field_offset(0), 4)

    def test_each_path_byte_pushes_the_packet_along(self):
        self.assertEqual(packet_field_offset(2), 6)
        self.assertEqual(packet_field_offset(5), 9)

    def test_negative_path_length_rejected(self):
        with self.assertRaises(ValueError):
            packet_field_offset(-3)

    def test_non_integer_path_length_rejected(self):
        with self.assertRaises(ValueError):
            packet_field_offset("four")


class HeaderTests(unittest.TestCase):
    def test_encoded_header_is_six_octets(self):
        self.assertEqual(len(HEADER), PRIMARY_HEADER_OCTETS)

    def test_decode_recovers_the_process_identifier(self):
        self.assertEqual(
            decode_primary_header(HEADER)["application_process_id"], 0x2AB
        )

    def test_decode_recovers_the_sequence_count(self):
        self.assertEqual(decode_primary_header(HEADER)["sequence_count"], 17)

    def test_length_field_is_one_less_than_the_data_octets(self):
        header = decode_primary_header(HEADER)
        self.assertEqual(header["data_octets"], 4)
        self.assertEqual(header["data_length_field"], 3)

    def test_flags_round_trip(self):
        encoded = encode_primary_header(
            5, 1, 2, packet_type=1, secondary_header_flag=1, version=0,
            sequence_flags=1,
        )
        header = decode_primary_header(encoded)
        self.assertEqual(header["packet_type"], 1)
        self.assertEqual(header["secondary_header_flag"], 1)
        self.assertEqual(header["sequence_flags"], 1)

    def test_short_header_rejected(self):
        with self.assertRaises(ValueError):
            decode_primary_header(HEADER[:5])

    def test_header_octet_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            decode_primary_header([0, 0, 0, 0, 0, 300])

    def test_process_identifier_wider_than_its_field_rejected(self):
        with self.assertRaises(ValueError):
            encode_primary_header(0x800, 0, 1)

    def test_zero_data_octets_rejected(self):
        with self.assertRaises(ValueError):
            encode_primary_header(5, 0, 0)

    def test_payload_overflowing_the_length_field_rejected(self):
        with self.assertRaises(ValueError):
            encode_primary_header(5, 0, 0x10001)

    def test_non_integer_payload_size_rejected(self):
        with self.assertRaises(ValueError):
            encode_primary_header(5, 0, 4.0)


class LengthTests(unittest.TestCase):
    def test_declared_length_is_header_plus_payload(self):
        self.assertEqual(space_packet_length(PACKET), PRIMARY_HEADER_OCTETS + 4)

    def test_smallest_packet_carries_one_data_octet(self):
        smallest = list(encode_primary_header(5, 0, 1)) + [0]
        self.assertEqual(space_packet_length(smallest), PRIMARY_HEADER_OCTETS + 1)

    def test_declared_length_ignores_what_actually_follows(self):
        self.assertEqual(space_packet_length(PACKET + [9, 9, 9]), len(PACKET))


class ValidateTests(unittest.TestCase):
    def test_exact_field_is_complete(self):
        graded = validate_packet_field(PACKET)
        self.assertEqual(graded["verdict"], COMPLETE)
        self.assertEqual(graded["trailing_octets"], 0)
        self.assertEqual(graded["shortfall"], 0)
        self.assertEqual(graded["findings"], [])

    def test_short_field_is_truncated(self):
        graded = validate_packet_field(PACKET[:-2])
        self.assertEqual(graded["verdict"], TRUNCATED)
        self.assertEqual(graded["shortfall"], 2)
        self.assertTrue(any("cut short" in f for f in graded["findings"]))

    def test_field_without_a_full_header_is_truncated(self):
        graded = validate_packet_field(PACKET[:4])
        self.assertEqual(graded["verdict"], TRUNCATED)
        self.assertIsNone(graded["declared_octets"])
        self.assertTrue(any("primary header" in f for f in graded["findings"]))

    def test_second_packet_in_the_field_is_an_overrun(self):
        graded = validate_packet_field(PACKET + PACKET)
        self.assertEqual(graded["verdict"], OVERRUN)
        self.assertEqual(graded["trailing_octets"], len(PACKET))

    def test_field_over_the_link_limit_is_reported(self):
        graded = validate_packet_field(PACKET, max_field_octets=8)
        self.assertEqual(graded["verdict"], OVER_LIMIT)
        self.assertTrue(any("link limit" in f for f in graded["findings"]))

    def test_field_inside_the_link_limit_stays_complete(self):
        graded = validate_packet_field(PACKET, max_field_octets=64)
        self.assertEqual(graded["verdict"], COMPLETE)

    def test_limit_below_the_header_rejected(self):
        with self.assertRaises(ValueError):
            validate_packet_field(PACKET, max_field_octets=4)

    def test_non_integer_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_packet_field(PACKET, max_field_octets=64.0)

    def test_non_sequence_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_packet_field(10)

    def test_field_octet_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_packet_field(PACKET[:-1] + [999])


class SplitTests(unittest.TestCase):
    def test_exact_field_splits_into_one_packet_and_nothing(self):
        split = split_packet_field(PACKET)
        self.assertEqual(list(split["packet"]), PACKET)
        self.assertEqual(split["trailing"], ())

    def test_overrun_field_separates_the_trailing_octets(self):
        split = split_packet_field(PACKET + [9, 9])
        self.assertEqual(list(split["packet"]), PACKET)
        self.assertEqual(split["trailing"], (9, 9))

    def test_split_reports_the_header_of_the_packet_it_kept(self):
        split = split_packet_field(PACKET + [9, 9])
        self.assertEqual(split["header"]["application_process_id"], 0x2AB)

    def test_truncated_field_cannot_be_split(self):
        with self.assertRaises(ValueError):
            split_packet_field(PACKET[:-1])


class AssessTests(unittest.TestCase):
    def test_complete_unit_is_deliverable(self):
        result = assess_packet_field(_case())
        self.assertEqual(result["verdict"], COMPLETE)
        self.assertTrue(result["deliverable"])
        self.assertEqual(result["packet_field_offset"], 6)
        self.assertEqual(result["application_process_id"], 0x2AB)

    def test_truncated_unit_is_not_deliverable(self):
        result = assess_packet_field(_case(octets=PREFIX + PACKET[:-3]))
        self.assertEqual(result["verdict"], TRUNCATED)
        self.assertFalse(result["deliverable"])
        self.assertEqual(result["shortfall"], 3)

    def test_unit_with_trailing_octets_is_an_overrun(self):
        result = assess_packet_field(_case(octets=PREFIX + PACKET + [0, 0]))
        self.assertEqual(result["verdict"], OVERRUN)
        self.assertEqual(result["trailing_octets"], 2)

    def test_unit_over_the_link_limit_is_reported(self):
        result = assess_packet_field(_case(max_field_octets=8))
        self.assertEqual(result["verdict"], OVER_LIMIT)

    def test_unit_with_no_packet_field_rejected(self):
        with self.assertRaises(ValueError):
            assess_packet_field(_case(octets=PREFIX))

    def test_case_without_octets_rejected(self):
        case = _case()
        del case["octets"]
        with self.assertRaises(ValueError):
            assess_packet_field(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_packet_field(PACKET)

    def test_wrong_declared_path_length_shifts_the_field(self):
        result = assess_packet_field(_case(path_length=0))
        self.assertEqual(result["packet_field_offset"], 4)
        self.assertNotEqual(result["verdict"], COMPLETE)


if __name__ == "__main__":
    unittest.main()
