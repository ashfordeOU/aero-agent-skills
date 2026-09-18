#!/usr/bin/env python3
"""Contract test for the protocol identifier field (offline)."""

import copy
import unittest

from e5053_protocol_identifier_field_logic import (
    ASSIGNED_CATEGORY,
    DELIVER,
    DISCARD_ESCAPE,
    DISCARD_UNKNOWN,
    ESCAPE_CATEGORY,
    EXTENDED_IDENTIFIER_ESCAPE,
    PACKET_TRANSFER_PROTOCOL_ID,
    UNASSIGNED_CATEGORY,
    assess_protocol_identifier_field,
    categorize_protocol_identifier,
    demultiplex_protocol,
    encode_protocol_identifier_field,
    identifier_offset,
    read_protocol_identifier,
    validate_protocol_identifier,
)

HANDLERS = {1: "remote-memory-access-protocol", 2: "packet-transfer-protocol"}

BASE_CASE = {
    "octets": [3, 7, 40, PACKET_TRANSFER_PROTOCOL_ID, 0, 1, 8],
    "path_length": 2,
    "handlers": HANDLERS,
}


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


class OffsetTests(unittest.TestCase):
    def test_pathless_unit_puts_the_identifier_second(self):
        self.assertEqual(identifier_offset(0), 1)

    def test_each_path_byte_pushes_the_identifier_along(self):
        self.assertEqual(identifier_offset(2), 3)
        self.assertEqual(identifier_offset(5), 6)

    def test_negative_path_length_rejected(self):
        with self.assertRaises(ValueError):
            identifier_offset(-1)

    def test_non_integer_path_length_rejected(self):
        with self.assertRaises(ValueError):
            identifier_offset("two")


class CategoryTests(unittest.TestCase):
    def test_escape_value_has_its_own_category(self):
        self.assertEqual(
            categorize_protocol_identifier(EXTENDED_IDENTIFIER_ESCAPE),
            ESCAPE_CATEGORY,
        )

    def test_registered_value_is_assigned(self):
        self.assertEqual(
            categorize_protocol_identifier(PACKET_TRANSFER_PROTOCOL_ID),
            ASSIGNED_CATEGORY,
        )

    def test_unclaimed_value_is_unassigned(self):
        self.assertEqual(categorize_protocol_identifier(200), UNASSIGNED_CATEGORY)

    def test_octet_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            categorize_protocol_identifier(300)

    def test_boolean_identifier_rejected(self):
        with self.assertRaises(ValueError):
            categorize_protocol_identifier(False)

    def test_non_mapping_registry_rejected(self):
        with self.assertRaises(ValueError):
            categorize_protocol_identifier(2, registry=[2])


class ReadTests(unittest.TestCase):
    def test_identifier_is_read_after_the_address_prefix(self):
        self.assertEqual(
            read_protocol_identifier([3, 7, 40, 2, 0], 2),
            PACKET_TRANSFER_PROTOCOL_ID,
        )

    def test_pathless_unit_reads_the_second_octet(self):
        self.assertEqual(read_protocol_identifier([82, 2, 0, 1], 0), 2)

    def test_short_unit_rejected(self):
        with self.assertRaises(ValueError):
            read_protocol_identifier([82], 0)

    def test_declared_path_holding_a_logical_address_rejected(self):
        with self.assertRaises(ValueError):
            read_protocol_identifier([3, 90, 40, 2, 0], 2)

    def test_non_sequence_unit_rejected(self):
        with self.assertRaises(ValueError):
            read_protocol_identifier(40, 0)

    def test_octet_out_of_range_inside_the_prefix_rejected(self):
        with self.assertRaises(ValueError):
            read_protocol_identifier([3, 700, 40, 2, 0], 2)


class ValidateTests(unittest.TestCase):
    def test_expected_identifier_is_conformant(self):
        graded = validate_protocol_identifier(PACKET_TRANSFER_PROTOCOL_ID)
        self.assertTrue(graded["conformant"])
        self.assertEqual(graded["findings"], [])

    def test_another_registered_protocol_is_not_conformant_here(self):
        graded = validate_protocol_identifier(1)
        self.assertFalse(graded["conformant"])
        self.assertTrue(any("remote-memory" in f for f in graded["findings"]))

    def test_unregistered_identifier_reports_no_registered_protocol(self):
        graded = validate_protocol_identifier(200)
        self.assertFalse(graded["conformant"])
        self.assertTrue(any("no registered protocol" in f for f in graded["findings"]))

    def test_escape_value_is_reported_as_an_escape(self):
        graded = validate_protocol_identifier(EXTENDED_IDENTIFIER_ESCAPE)
        self.assertFalse(graded["conformant"])
        self.assertEqual(graded["category"], ESCAPE_CATEGORY)
        self.assertTrue(any("wider identifier" in f for f in graded["findings"]))

    def test_expected_identifier_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_protocol_identifier(2, expected=999)


class DemultiplexTests(unittest.TestCase):
    def test_known_identifier_reaches_its_handler(self):
        routed = demultiplex_protocol(2, HANDLERS)
        self.assertEqual(routed["disposition"], DELIVER)
        self.assertEqual(routed["handler"], "packet-transfer-protocol")

    def test_unknown_identifier_is_dropped(self):
        routed = demultiplex_protocol(200, HANDLERS)
        self.assertEqual(routed["disposition"], DISCARD_UNKNOWN)
        self.assertIsNone(routed["handler"])

    def test_escape_value_is_dropped_before_any_handler(self):
        routed = demultiplex_protocol(EXTENDED_IDENTIFIER_ESCAPE, HANDLERS)
        self.assertEqual(routed["disposition"], DISCARD_ESCAPE)

    def test_non_mapping_handlers_rejected(self):
        with self.assertRaises(ValueError):
            demultiplex_protocol(2, ["packet-transfer-protocol"])

    def test_handler_keyed_outside_one_octet_rejected(self):
        with self.assertRaises(ValueError):
            demultiplex_protocol(2, {300: "somewhere"})


class EncodeTests(unittest.TestCase):
    def test_default_encoding_is_one_octet(self):
        self.assertEqual(
            encode_protocol_identifier_field(), (PACKET_TRANSFER_PROTOCOL_ID,)
        )

    def test_another_identifier_can_be_written(self):
        self.assertEqual(encode_protocol_identifier_field(1), (1,))

    def test_escape_value_cannot_be_written_alone(self):
        with self.assertRaises(ValueError):
            encode_protocol_identifier_field(EXTENDED_IDENTIFIER_ESCAPE)

    def test_identifier_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            encode_protocol_identifier_field(256)


class AssessTests(unittest.TestCase):
    def test_conformant_unit_is_accepted(self):
        result = assess_protocol_identifier_field(_case())
        self.assertEqual(result["verdict"], "identifier-accepted")
        self.assertEqual(result["identifier_offset"], 3)
        self.assertEqual(result["handler"], "packet-transfer-protocol")
        self.assertEqual(result["findings"], [])

    def test_wrong_protocol_is_rejected_even_with_a_handler(self):
        result = assess_protocol_identifier_field(
            _case(octets=[3, 7, 40, 1, 0, 1, 8])
        )
        self.assertEqual(result["verdict"], "identifier-rejected")
        self.assertFalse(result["conformant"])
        self.assertEqual(result["disposition"], DELIVER)

    def test_unhandled_identifier_is_dropped_and_reported(self):
        result = assess_protocol_identifier_field(
            _case(octets=[3, 7, 40, 200, 0, 1, 8])
        )
        self.assertEqual(result["disposition"], DISCARD_UNKNOWN)
        self.assertTrue(any("no handler" in f for f in result["findings"]))

    def test_case_without_octets_rejected(self):
        case = _case()
        del case["octets"]
        with self.assertRaises(ValueError):
            assess_protocol_identifier_field(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_protocol_identifier_field([3, 7, 40, 2])

    def test_wrong_declared_path_length_moves_the_offset(self):
        result = assess_protocol_identifier_field(_case(path_length=0))
        self.assertEqual(result["identifier_offset"], 1)
        self.assertEqual(result["identifier"], 7)
        self.assertFalse(result["conformant"])


if __name__ == "__main__":
    unittest.main()
