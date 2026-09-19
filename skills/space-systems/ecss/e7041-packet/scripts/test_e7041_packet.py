"""Contract tests for the clause 7.3.13 packet data-type logic."""

import unittest

from e7041_packet_logic import (
    LENGTH_FIELD_OFFSET,
    MAX_PACKET_OCTETS,
    MIN_PACKET_OCTETS,
    PRIMARY_HEADER_OCTETS,
    assess_packet_parameter,
    contained_packet_octets,
    extract_contained_packet,
    reconcile_declared_length,
    split_packet_sequence,
    stated_data_length,
    validate_octets,
)


def build_packet(apid, data_octets):
    """Build a well-formed contained packet with a truthful length field."""
    stated = len(data_octets) - 1
    header = [
        0x08,
        apid & 0xFF,
        0xC0,
        0x01,
        (stated >> 8) & 0xFF,
        stated & 0xFF,
    ]
    return header + list(data_octets)


PKT_A = build_packet(10, [0x01, 0x02, 0x03])
PKT_B = build_packet(11, [0x09])
PKT_C = build_packet(12, list(range(16)))


class ConstantTests(unittest.TestCase):
    def test_the_primary_header_is_six_octets(self):
        self.assertEqual(PRIMARY_HEADER_OCTETS, 6)

    def test_the_length_field_sits_in_the_last_two_header_octets(self):
        self.assertEqual(LENGTH_FIELD_OFFSET + 2, PRIMARY_HEADER_OCTETS)

    def test_the_smallest_packet_is_a_header_and_one_data_octet(self):
        self.assertEqual(MIN_PACKET_OCTETS, 7)

    def test_the_largest_packet_follows_the_sixteen_bit_length_field(self):
        self.assertEqual(MAX_PACKET_OCTETS, PRIMARY_HEADER_OCTETS + 65536)


class BufferTests(unittest.TestCase):
    def test_a_list_of_octets_is_accepted(self):
        self.assertEqual(validate_octets([0, 255]), [0, 255])

    def test_bytes_are_accepted(self):
        self.assertEqual(validate_octets(b"\x01\x02"), [1, 2])

    def test_a_value_outside_an_octet_refused(self):
        with self.assertRaises(ValueError):
            validate_octets([0, 256])

    def test_a_boolean_is_not_an_octet(self):
        with self.assertRaises(ValueError):
            validate_octets([True])

    def test_a_non_sequence_refused(self):
        with self.assertRaises(ValueError):
            validate_octets(42)


class LengthDerivationTests(unittest.TestCase):
    def test_the_length_field_states_one_less_than_the_data_field(self):
        self.assertEqual(stated_data_length(PKT_A), 2)

    def test_a_single_data_octet_states_zero(self):
        self.assertEqual(stated_data_length(PKT_B), 0)

    def test_the_total_is_seven_more_than_the_stated_value(self):
        self.assertEqual(contained_packet_octets(PKT_A), 9)

    def test_the_derived_total_matches_the_buffer(self):
        self.assertEqual(contained_packet_octets(PKT_C), len(PKT_C))

    def test_the_length_field_is_big_endian(self):
        packet = build_packet(13, [0] * 300)
        self.assertEqual(stated_data_length(packet), 299)

    def test_a_buffer_too_short_for_a_header_refused(self):
        with self.assertRaises(ValueError):
            stated_data_length(PKT_A[:5])

    def test_a_negative_offset_refused(self):
        with self.assertRaises(ValueError):
            stated_data_length(PKT_A, -1)

    def test_an_offset_past_the_buffer_refused(self):
        with self.assertRaises(ValueError):
            stated_data_length(PKT_A, 20)


class ExtractionTests(unittest.TestCase):
    def test_the_whole_packet_including_its_header_is_returned(self):
        out = extract_contained_packet(PKT_A)
        self.assertEqual(out["packet"], PKT_A)
        self.assertEqual(out["packet"][:PRIMARY_HEADER_OCTETS], PKT_A[:PRIMARY_HEADER_OCTETS])

    def test_the_data_field_size_is_reported(self):
        out = extract_contained_packet(PKT_A)
        self.assertEqual(out["data_field_octets"], 3)

    def test_the_next_offset_lands_on_the_following_packet(self):
        out = extract_contained_packet(PKT_A + PKT_B)
        self.assertEqual(out["next_offset"], len(PKT_A))

    def test_a_packet_can_be_extracted_at_an_offset(self):
        out = extract_contained_packet(PKT_A + PKT_B, len(PKT_A))
        self.assertEqual(out["packet"], PKT_B)

    def test_a_truncated_contained_packet_refused(self):
        with self.assertRaises(ValueError):
            extract_contained_packet(PKT_A[:-1])


class SequenceTests(unittest.TestCase):
    def test_back_to_back_packets_are_split_by_their_own_lengths(self):
        packets = split_packet_sequence(PKT_A + PKT_B + PKT_C)
        self.assertEqual([p["octets"] for p in packets],
                         [len(PKT_A), len(PKT_B), len(PKT_C)])

    def test_an_empty_container_holds_no_packets(self):
        self.assertEqual(split_packet_sequence([]), [])

    def test_a_declared_count_that_matches_is_accepted(self):
        self.assertEqual(len(split_packet_sequence(PKT_A + PKT_B, 2)), 2)

    def test_a_declared_count_too_low_refused(self):
        with self.assertRaises(ValueError):
            split_packet_sequence(PKT_A + PKT_B, 1)

    def test_a_declared_count_too_high_refused(self):
        with self.assertRaises(ValueError):
            split_packet_sequence(PKT_A + PKT_B, 3)

    def test_trailing_octets_short_of_a_header_refused(self):
        with self.assertRaises(ValueError):
            split_packet_sequence(PKT_A + PKT_B[:3])

    def test_a_lying_length_desynchronises_and_is_refused(self):
        corrupt = list(PKT_A)
        corrupt[LENGTH_FIELD_OFFSET + 1] = 0xF0
        with self.assertRaises(ValueError):
            split_packet_sequence(corrupt + PKT_B)

    def test_a_negative_expected_count_refused(self):
        with self.assertRaises(ValueError):
            split_packet_sequence(PKT_A, -1)


class ReconciliationTests(unittest.TestCase):
    def test_an_agreeing_declared_length_returns_the_derived_one(self):
        self.assertEqual(reconcile_declared_length(PKT_A, len(PKT_A)), len(PKT_A))

    def test_a_declared_length_one_octet_short_refused(self):
        with self.assertRaises(ValueError):
            reconcile_declared_length(PKT_A, len(PKT_A) - 1)

    def test_a_declared_length_one_octet_long_refused(self):
        with self.assertRaises(ValueError):
            reconcile_declared_length(PKT_A, len(PKT_A) + 1)

    def test_a_non_integer_declared_length_refused(self):
        with self.assertRaises(ValueError):
            reconcile_declared_length(PKT_A, "9")


class AssessmentTests(unittest.TestCase):
    def test_a_clean_container_reports_no_findings(self):
        report = assess_packet_parameter(PKT_A + PKT_B, expected_count=2)
        self.assertEqual(report["findings"], [])
        self.assertTrue(report["readable"])

    def test_the_recovered_count_and_total_are_reported(self):
        report = assess_packet_parameter(PKT_A + PKT_B + PKT_C)
        self.assertEqual(report["count"], 3)
        self.assertEqual(report["total_octets"], len(PKT_A) + len(PKT_B) + len(PKT_C))

    def test_an_empty_parameter_is_a_finding(self):
        report = assess_packet_parameter([])
        self.assertTrue(any("no packet at all" in f for f in report["findings"]))

    def test_trailing_octets_are_a_finding(self):
        report = assess_packet_parameter(PKT_A + PKT_B[:3])
        self.assertTrue(report["truncated"])
        self.assertTrue(any("packet boundary" in f for f in report["findings"]))

    def test_a_lying_length_loses_everything_after_it(self):
        corrupt = list(PKT_A)
        corrupt[LENGTH_FIELD_OFFSET + 1] = 0xF0
        report = assess_packet_parameter(corrupt + PKT_B)
        self.assertEqual(report["count"], 0)
        self.assertTrue(any("lost as well" in f for f in report["findings"]))

    def test_a_count_mismatch_is_a_finding(self):
        report = assess_packet_parameter(PKT_A + PKT_B, expected_count=3)
        self.assertTrue(any("against the 3 declared" in f for f in report["findings"]))

    def test_a_declared_field_length_disagreeing_is_a_finding(self):
        report = assess_packet_parameter(PKT_A, declared_octets=len(PKT_A) + 2)
        self.assertTrue(any("derives" in f for f in report["findings"]))

    def test_an_agreeing_declared_field_length_reports_nothing(self):
        report = assess_packet_parameter(PKT_A, declared_octets=len(PKT_A))
        self.assertEqual(report["findings"], [])

    def test_consumed_and_trailing_octets_account_for_the_buffer(self):
        buffer = PKT_A + PKT_B
        report = assess_packet_parameter(buffer)
        self.assertEqual(report["consumed_octets"] + report["trailing_octets"], len(buffer))

    def test_a_non_buffer_parameter_refused(self):
        with self.assertRaises(ValueError):
            assess_packet_parameter("not octets")

    def test_a_negative_expected_count_refused(self):
        with self.assertRaises(ValueError):
            assess_packet_parameter(PKT_A, expected_count=-2)


if __name__ == "__main__":
    unittest.main()
