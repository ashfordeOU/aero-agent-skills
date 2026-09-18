"""Contract tests for the clause 5.5.4.1 protocol identifier logic."""

import unittest

from e5053_protocol_identifier_logic import (
    EXTENDED_IDENTIFIER_OCTETS,
    EXTENDED_MARKER,
    KNOWN_IDENTIFIERS,
    PROTOCOL_IDENTIFIER,
    RECEIVER,
    RESERVED_RANGE,
    SENDER,
    assess_protocol_identifier,
    categorize_identifier,
    demultiplex,
    expected_identifier,
    validate_identifier_octet,
)


class ValidateOctetTests(unittest.TestCase):
    def test_in_range_value_returned(self):
        self.assertEqual(validate_identifier_octet(2), 2)

    def test_zero_accepted(self):
        self.assertEqual(validate_identifier_octet(0), 0)

    def test_top_of_range_accepted(self):
        self.assertEqual(validate_identifier_octet(255), 255)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier_octet(-1)

    def test_above_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier_octet(256)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier_octet(True)

    def test_text_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier_octet("2")

    def test_float_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier_octet(2.0)


class CategorizeTests(unittest.TestCase):
    def test_assigned_value_is_this_protocol(self):
        self.assertEqual(
            categorize_identifier(PROTOCOL_IDENTIFIER), "assigned-to-this-protocol"
        )

    def test_zero_announces_an_extended_identifier(self):
        self.assertEqual(
            categorize_identifier(EXTENDED_MARKER), "extended-identifier-announced"
        )

    def test_other_known_identifier_is_separated(self):
        self.assertEqual(
            categorize_identifier(0x01), "assigned-to-another-protocol"
        )

    def test_reserved_low_bound_is_reserved(self):
        self.assertEqual(categorize_identifier(RESERVED_RANGE[0]), "reserved-value")

    def test_reserved_high_bound_is_reserved(self):
        self.assertEqual(categorize_identifier(RESERVED_RANGE[1]), "reserved-value")

    def test_value_below_the_reserved_range_is_unassigned(self):
        self.assertEqual(categorize_identifier(RESERVED_RANGE[0] - 1), "unassigned-value")

    def test_value_above_the_reserved_range_is_unassigned(self):
        self.assertEqual(categorize_identifier(RESERVED_RANGE[1] + 1), "unassigned-value")

    def test_expected_identifier_matches_the_constant(self):
        self.assertEqual(expected_identifier(), PROTOCOL_IDENTIFIER)


class SenderAssessmentTests(unittest.TestCase):
    def test_assigned_value_is_compliant(self):
        result = assess_protocol_identifier(PROTOCOL_IDENTIFIER)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_compliant_sender_field_names_the_protocol(self):
        result = assess_protocol_identifier(PROTOCOL_IDENTIFIER, SENDER)
        self.assertEqual(result["name"], KNOWN_IDENTIFIERS[PROTOCOL_IDENTIFIER])

    def test_another_protocols_value_is_a_sender_defect(self):
        result = assess_protocol_identifier(0x01, SENDER)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("sender wrote" in f for f in result["findings"]))

    def test_zero_is_a_sender_defect(self):
        result = assess_protocol_identifier(EXTENDED_MARKER, SENDER)
        self.assertFalse(result["compliant"])

    def test_reserved_value_is_a_sender_defect(self):
        self.assertFalse(assess_protocol_identifier(RESERVED_RANGE[0], SENDER)["compliant"])

    def test_role_is_case_insensitive(self):
        self.assertTrue(assess_protocol_identifier(PROTOCOL_IDENTIFIER, "SENDER")["compliant"])

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            assess_protocol_identifier(PROTOCOL_IDENTIFIER, "router")

    def test_non_string_role_rejected(self):
        with self.assertRaises(ValueError):
            assess_protocol_identifier(PROTOCOL_IDENTIFIER, 1)


class ReceiverAssessmentTests(unittest.TestCase):
    def test_assigned_value_is_for_this_entity(self):
        result = assess_protocol_identifier(PROTOCOL_IDENTIFIER, RECEIVER)
        self.assertTrue(result["for_this_entity"])
        self.assertTrue(result["compliant"])

    def test_another_protocol_is_not_a_finding(self):
        result = assess_protocol_identifier(0x01, RECEIVER)
        self.assertFalse(result["for_this_entity"])
        self.assertEqual(result["findings"], [])

    def test_reserved_value_is_a_receiver_finding(self):
        result = assess_protocol_identifier(RESERVED_RANGE[0], RECEIVER)
        self.assertFalse(result["compliant"])

    def test_extended_marker_reports_the_octets_still_to_read(self):
        result = assess_protocol_identifier(EXTENDED_MARKER, RECEIVER)
        self.assertEqual(result["extended_octets_to_read"], EXTENDED_IDENTIFIER_OCTETS)

    def test_assigned_value_needs_no_further_octets(self):
        result = assess_protocol_identifier(PROTOCOL_IDENTIFIER, RECEIVER)
        self.assertEqual(result["extended_octets_to_read"], 0)


class DemultiplexTests(unittest.TestCase):
    def test_assigned_value_routes_here(self):
        taken, reason = demultiplex(PROTOCOL_IDENTIFIER)
        self.assertTrue(taken)
        self.assertIn("CCSDS packet transfer", reason)

    def test_other_known_value_names_its_owner(self):
        taken, reason = demultiplex(0x01)
        self.assertFalse(taken)
        self.assertIn("remote memory access", reason)

    def test_extended_marker_asks_for_more_octets(self):
        taken, reason = demultiplex(EXTENDED_MARKER)
        self.assertFalse(taken)
        self.assertIn(str(EXTENDED_IDENTIFIER_OCTETS), reason)

    def test_reserved_value_is_named_as_held_back(self):
        taken, reason = demultiplex(RESERVED_RANGE[1])
        self.assertFalse(taken)
        self.assertIn("held back", reason)

    def test_unassigned_value_is_named_as_unassigned(self):
        taken, reason = demultiplex(0x7F)
        self.assertFalse(taken)
        self.assertIn("not assigned", reason)

    def test_bad_octet_rejected(self):
        with self.assertRaises(ValueError):
            demultiplex(999)


if __name__ == "__main__":
    unittest.main()
