"""Contract tests for the clause 5.5.4.2 reserved field logic."""

import unittest

from e5053_reserved_field_zero_logic import (
    DELIVER,
    RECEIVER,
    REJECT,
    RESERVED_FIELD_OCTETS,
    RESERVED_VALUE,
    SENDER,
    assess_receiver_field,
    assess_reserved_field,
    assess_sender_field,
    audit_transfers,
    encode_reserved_field,
    validate_reserved_octet,
)


class EncodeTests(unittest.TestCase):
    def test_encoded_field_is_all_zero(self):
        self.assertEqual(encode_reserved_field(), [RESERVED_VALUE])

    def test_encoded_field_has_the_declared_width(self):
        self.assertEqual(len(encode_reserved_field()), RESERVED_FIELD_OCTETS)

    def test_encoded_field_is_a_fresh_list(self):
        first = encode_reserved_field()
        first.append(0xFF)
        self.assertEqual(len(encode_reserved_field()), RESERVED_FIELD_OCTETS)


class ValidateOctetTests(unittest.TestCase):
    def test_zero_accepted(self):
        self.assertEqual(validate_reserved_octet(0), 0)

    def test_top_of_range_accepted(self):
        self.assertEqual(validate_reserved_octet(255), 255)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_reserved_octet(-1)

    def test_above_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_reserved_octet(256)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_reserved_octet(False)

    def test_float_rejected(self):
        with self.assertRaises(ValueError):
            validate_reserved_octet(0.0)

    def test_text_rejected(self):
        with self.assertRaises(ValueError):
            validate_reserved_octet("0")


class SenderRuleTests(unittest.TestCase):
    def test_zero_is_compliant(self):
        result = assess_sender_field(0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_non_zero_is_a_sender_defect(self):
        result = assess_sender_field(0x5A)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("sender wrote" in f for f in result["findings"]))

    def test_finding_names_both_values(self):
        result = assess_sender_field(7)
        self.assertIn("7", result["findings"][0])

    def test_role_is_reported(self):
        self.assertEqual(assess_sender_field(0)["role"], SENDER)


class ReceiverRuleTests(unittest.TestCase):
    def test_zero_delivers_with_no_observation(self):
        result = assess_receiver_field(0)
        self.assertEqual(result["disposition"], DELIVER)
        self.assertEqual(result["observations"], [])

    def test_non_zero_still_delivers(self):
        result = assess_receiver_field(0xFF)
        self.assertEqual(result["disposition"], DELIVER)
        self.assertTrue(result["compliant"])

    def test_non_zero_is_recorded_as_an_observation(self):
        result = assess_receiver_field(0xFF)
        self.assertEqual(len(result["observations"]), 1)
        self.assertIn("ignored", result["observations"][0])

    def test_sender_conformance_is_reported_separately(self):
        self.assertFalse(assess_receiver_field(3)["sender_conformant"])
        self.assertTrue(assess_receiver_field(0)["sender_conformant"])

    def test_receiver_never_reports_its_own_defect_on_a_bad_field(self):
        self.assertTrue(assess_receiver_field(0x80)["compliant"])


class RoleDispatchTests(unittest.TestCase):
    def test_sender_role_dispatches_to_the_sender_rule(self):
        self.assertIn("findings", assess_reserved_field(1, SENDER))

    def test_receiver_role_dispatches_to_the_receiver_rule(self):
        self.assertIn("observations", assess_reserved_field(1, RECEIVER))

    def test_role_is_case_insensitive(self):
        self.assertEqual(assess_reserved_field(0, "RECEIVER")["role"], RECEIVER)

    def test_same_value_gets_opposite_verdicts_by_role(self):
        self.assertFalse(assess_reserved_field(9, SENDER)["compliant"])
        self.assertTrue(assess_reserved_field(9, RECEIVER)["compliant"])

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            assess_reserved_field(0, "router")

    def test_non_string_role_rejected(self):
        with self.assertRaises(ValueError):
            assess_reserved_field(0, 3)


class AuditTests(unittest.TestCase):
    def test_all_zero_run_has_no_findings(self):
        result = audit_transfers([0, 0, 0, 0])
        self.assertEqual(result["non_zero"], 0)
        self.assertEqual(result["findings"], [])

    def test_non_zero_senders_are_counted(self):
        result = audit_transfers([0, 4, 0, 4, 9])
        self.assertEqual(result["non_zero"], 3)
        self.assertEqual(result["total"], 5)

    def test_distinct_non_zero_values_are_listed(self):
        result = audit_transfers([0, 4, 4, 9])
        self.assertEqual(result["distinct_non_zero_values"], [4, 9])

    def test_tolerant_receiver_delivers(self):
        self.assertEqual(audit_transfers([0, 7])["disposition"], DELIVER)

    def test_intolerant_receiver_is_itself_a_finding(self):
        result = audit_transfers([0, 0], tolerate_non_zero=False)
        self.assertEqual(result["disposition"], REJECT)
        self.assertFalse(result["receiver_conformant"])
        self.assertTrue(any("must not refuse" in f for f in result["findings"]))

    def test_bytes_input_accepted(self):
        self.assertEqual(audit_transfers(bytes([0, 0, 5]))["non_zero"], 1)

    def test_empty_run_rejected(self):
        with self.assertRaises(ValueError):
            audit_transfers([])

    def test_text_input_rejected(self):
        with self.assertRaises(ValueError):
            audit_transfers("000")

    def test_bad_octet_rejected(self):
        with self.assertRaises(ValueError):
            audit_transfers([0, 300])

    def test_non_boolean_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            audit_transfers([0], tolerate_non_zero="yes")


if __name__ == "__main__":
    unittest.main()
