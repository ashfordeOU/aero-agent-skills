#!/usr/bin/env python3
"""Gate 3 contract test for e5053-packet-length.

stdlib unittest, offline, deterministic. Run:
    python3 test_e5053_packet_length.py
"""

import unittest

from e5053_packet_length_logic import (
    AGREES,
    CCSDS_PRIMARY_HEADER_OCTETS,
    DECLARED_LONG,
    DECLARED_SHORT,
    DEFAULT_LENGTH_FIELD_OCTETS,
    LENGTH_NOT_DECLARED,
    NOT_DECLARED,
    assess_packet_length,
    categorize_length_agreement,
    ccsds_packet_octets,
    decode_length,
    deliverable,
    encode_length,
    field_capacity,
    length_is_declared,
    received_octet_count,
    validate_declared_length,
    validate_field_width,
)


def packet(octets):
    return bytes(bytearray(i % 256 for i in range(octets)))


class TestFieldWidth(unittest.TestCase):
    def test_default_width_is_accepted(self):
        self.assertEqual(validate_field_width(), DEFAULT_LENGTH_FIELD_OCTETS)

    def test_zero_width_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width(0)

    def test_oversized_width_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_field_width(9)

    def test_boolean_width_is_not_an_integer(self):
        with self.assertRaises(ValueError):
            validate_field_width(True)

    def test_capacity_follows_the_width(self):
        self.assertEqual(field_capacity(1), 255)
        self.assertEqual(field_capacity(2), 65535)


class TestDeclaredLength(unittest.TestCase):
    def test_value_inside_capacity_is_returned(self):
        self.assertEqual(validate_declared_length(1024, 2), 1024)

    def test_value_over_capacity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_declared_length(300, 1)

    def test_negative_value_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_declared_length(-1, 2)

    def test_float_value_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_declared_length(12.0, 2)

    def test_reserved_code_is_not_a_declaration(self):
        self.assertFalse(length_is_declared(LENGTH_NOT_DECLARED))

    def test_ordinary_value_is_a_declaration(self):
        self.assertTrue(length_is_declared(7))


class TestEncoding(unittest.TestCase):
    def test_encode_is_big_endian(self):
        self.assertEqual(encode_length(0x0102, 2), (0x01, 0x02))

    def test_encode_then_decode_round_trips(self):
        self.assertEqual(decode_length(encode_length(40000, 2)), 40000)

    def test_decode_rejects_an_empty_sequence(self):
        with self.assertRaises(ValueError):
            decode_length([])

    def test_decode_rejects_an_out_of_range_octet(self):
        with self.assertRaises(ValueError):
            decode_length([256, 0])

    def test_decode_rejects_text(self):
        with self.assertRaises(ValueError):
            decode_length("0102")


class TestCarriedPacketHeader(unittest.TestCase):
    def test_header_length_adds_the_primary_header_and_one(self):
        self.assertEqual(
            ccsds_packet_octets(9), CCSDS_PRIMARY_HEADER_OCTETS + 10
        )

    def test_zero_field_still_means_one_data_octet(self):
        self.assertEqual(ccsds_packet_octets(0), CCSDS_PRIMARY_HEADER_OCTETS + 1)

    def test_header_field_over_range_is_rejected(self):
        with self.assertRaises(ValueError):
            ccsds_packet_octets(0x10000)

    def test_negative_header_field_is_rejected(self):
        with self.assertRaises(ValueError):
            ccsds_packet_octets(-1)


class TestReceivedCount(unittest.TestCase):
    def test_octets_are_counted(self):
        self.assertEqual(received_octet_count(packet(16)), 16)

    def test_a_plain_count_is_accepted(self):
        self.assertEqual(received_octet_count(16), 16)

    def test_a_bad_octet_in_a_list_is_rejected(self):
        with self.assertRaises(ValueError):
            received_octet_count([1, 2, 999])

    def test_an_unsupported_type_is_rejected(self):
        with self.assertRaises(ValueError):
            received_octet_count({"octets": 4})


class TestAgreement(unittest.TestCase):
    def test_matching_declaration_agrees(self):
        self.assertEqual(categorize_length_agreement(16, packet(16)), AGREES)

    def test_reserved_code_is_not_declared(self):
        self.assertEqual(
            categorize_length_agreement(LENGTH_NOT_DECLARED, packet(16)), NOT_DECLARED
        )

    def test_short_declaration_is_grouped_as_short(self):
        self.assertEqual(categorize_length_agreement(12, packet(16)), DECLARED_SHORT)

    def test_long_declaration_is_grouped_as_long(self):
        self.assertEqual(categorize_length_agreement(20, packet(16)), DECLARED_LONG)

    def test_deliverable_rejects_an_unknown_category(self):
        with self.assertRaises(ValueError):
            deliverable("maybe")

    def test_both_mismatch_categories_block_delivery(self):
        self.assertFalse(deliverable(DECLARED_SHORT))
        self.assertFalse(deliverable(DECLARED_LONG))


class TestAssessment(unittest.TestCase):
    def test_agreeing_transfer_is_delivered(self):
        report = assess_packet_length(22, packet(22))
        self.assertEqual(report["verdict"], "deliver")
        self.assertEqual(report["findings"], [])

    def test_undeclared_transfer_is_delivered_with_a_limitation(self):
        report = assess_packet_length(LENGTH_NOT_DECLARED, packet(22))
        self.assertEqual(report["verdict"], "deliver")
        self.assertFalse(report["declared"])
        self.assertTrue(
            any("end of packet" in note for note in report["limitations"])
        )

    def test_truncated_transfer_is_discarded(self):
        report = assess_packet_length(30, packet(22))
        self.assertEqual(report["verdict"], "discard")
        self.assertTrue(any("short of its declaration" in f for f in report["findings"]))

    def test_trailing_octets_are_a_finding(self):
        report = assess_packet_length(18, packet(22))
        self.assertEqual(report["category"], DECLARED_SHORT)
        self.assertTrue(any("no declared home" in f for f in report["findings"]))

    def test_header_disagreement_is_reported_separately(self):
        report = assess_packet_length(
            16, packet(16), packet_data_length_field=20
        )
        self.assertEqual(report["category"], AGREES)
        self.assertEqual(report["verdict"], "discard")
        self.assertEqual(len(report["findings"]), 2)

    def test_header_agreement_leaves_the_transfer_deliverable(self):
        octets = CCSDS_PRIMARY_HEADER_OCTETS + 10
        report = assess_packet_length(
            octets, packet(octets), packet_data_length_field=9
        )
        self.assertEqual(report["verdict"], "deliver")
        self.assertEqual(report["header_octets"], octets)

    def test_report_carries_the_field_capacity(self):
        report = assess_packet_length(5, packet(5), field_octets=1)
        self.assertEqual(report["field_capacity"], 255)

    def test_assessment_propagates_a_capacity_error(self):
        with self.assertRaises(ValueError):
            assess_packet_length(300, packet(300), field_octets=1)


if __name__ == "__main__":
    unittest.main()
