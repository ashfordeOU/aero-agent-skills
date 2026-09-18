"""Contract tests for the clause 5.5.4.3 non-zero reserved field logic."""

import unittest

from e5053_reserved_field_not_zero_logic import (
    CONFORMANT,
    CORRUPTION,
    DELIVER,
    DISCARD,
    PEER_REVISION,
    RESERVED_VALUE,
    SPORADIC,
    audit_run,
    handle_reserved_field,
    is_version_conformant,
    receive_transfer,
    validate_octet_sequence,
    validate_reserved_octet,
)


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
            validate_reserved_octet(True)

    def test_float_rejected(self):
        with self.assertRaises(ValueError):
            validate_reserved_octet(1.0)


class SequenceValidationTests(unittest.TestCase):
    def test_bytes_accepted(self):
        self.assertEqual(validate_octet_sequence(bytes([0, 1])), [0, 1])

    def test_text_rejected(self):
        with self.assertRaises(ValueError):
            validate_octet_sequence("00")

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            validate_octet_sequence([])

    def test_out_of_range_member_rejected(self):
        with self.assertRaises(ValueError):
            validate_octet_sequence([0, 999])

    def test_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_octet_sequence({"a": 1})


class ConformanceTests(unittest.TestCase):
    def test_zero_is_version_conformant(self):
        self.assertTrue(is_version_conformant(RESERVED_VALUE))

    def test_non_zero_is_not_version_conformant(self):
        self.assertFalse(is_version_conformant(0x01))


class DispositionTests(unittest.TestCase):
    def test_zero_field_delivers(self):
        verdict = handle_reserved_field(0)
        self.assertEqual(verdict["disposition"], DELIVER)
        self.assertIsNone(verdict["report"])

    def test_non_zero_field_discards(self):
        verdict = handle_reserved_field(0x2A)
        self.assertEqual(verdict["disposition"], DISCARD)

    def test_non_zero_field_is_not_parsed(self):
        self.assertFalse(handle_reserved_field(0x2A)["payload_parsed"])

    def test_report_names_the_value_seen(self):
        self.assertIn("42", handle_reserved_field(42)["report"])

    def test_report_names_the_defined_value(self):
        self.assertIn("rather than 0", handle_reserved_field(9)["report"])

    def test_top_of_range_still_discards(self):
        self.assertEqual(handle_reserved_field(255)["disposition"], DISCARD)


class ReceiveTransferTests(unittest.TestCase):
    def test_conformant_transfer_hands_the_packet_up(self):
        result = receive_transfer(0, [8, 0, 0, 0, 0, 1, 7])
        self.assertEqual(result["disposition"], DELIVER)
        self.assertEqual(result["packet"], [8, 0, 0, 0, 0, 1, 7])

    def test_delivered_packet_is_a_copy(self):
        payload = [1, 2, 3]
        result = receive_transfer(0, payload)
        result["packet"].append(4)
        self.assertEqual(payload, [1, 2, 3])

    def test_non_zero_field_withholds_the_packet(self):
        result = receive_transfer(5, [1, 2, 3, 4])
        self.assertIsNone(result["packet"])
        self.assertEqual(result["disposition"], DISCARD)

    def test_withheld_octets_are_counted(self):
        self.assertEqual(receive_transfer(5, [1, 2, 3, 4])["octets_withheld"], 4)

    def test_conformant_transfer_withholds_nothing(self):
        self.assertEqual(receive_transfer(0, [1])["octets_withheld"], 0)

    def test_empty_payload_rejected(self):
        with self.assertRaises(ValueError):
            receive_transfer(0, [])


class AuditRunTests(unittest.TestCase):
    def test_clean_run_is_conformant(self):
        result = audit_run([0, 0, 0, 0])
        self.assertEqual(result["diagnosis"], CONFORMANT)
        self.assertEqual(result["findings"], [])

    def test_clean_run_discards_nothing(self):
        self.assertEqual(audit_run([0, 0])["discarded"], 0)

    def test_repeated_value_reads_as_a_peer_revision(self):
        result = audit_run([3, 3, 3, 0])
        self.assertEqual(result["diagnosis"], PEER_REVISION)

    def test_scattered_values_read_as_corruption(self):
        result = audit_run([0, 3, 9, 0, 17])
        self.assertEqual(result["diagnosis"], CORRUPTION)

    def test_rare_single_value_is_only_sporadic(self):
        self.assertEqual(audit_run([0, 0, 0, 0, 0, 0, 0, 4])["diagnosis"], SPORADIC)

    def test_half_non_zero_reaches_the_revision_threshold(self):
        result = audit_run([0, 0, 6, 6])
        self.assertAlmostEqual(result["discard_share"], 0.5, places=9)
        self.assertEqual(result["diagnosis"], PEER_REVISION)

    def test_distinct_values_are_listed_in_order(self):
        self.assertEqual(audit_run([0, 9, 3, 9])["distinct_non_zero_values"], [3, 9])

    def test_delivered_and_discarded_sum_to_the_total(self):
        result = audit_run([0, 1, 0, 2])
        self.assertEqual(result["delivered"] + result["discarded"], result["total"])

    def test_discard_share_is_exact_for_a_clean_run(self):
        self.assertAlmostEqual(audit_run([0, 0, 0])["discard_share"], 0.0, places=9)

    def test_all_non_zero_run_reports_a_full_share(self):
        self.assertAlmostEqual(audit_run([7, 7])["discard_share"], 1.0, places=9)

    def test_finding_counts_the_discards(self):
        self.assertIn("2 of 4", audit_run([0, 5, 0, 5])["findings"][0])

    def test_empty_run_rejected(self):
        with self.assertRaises(ValueError):
            audit_run([])

    def test_text_run_rejected(self):
        with self.assertRaises(ValueError):
            audit_run("000")


if __name__ == "__main__":
    unittest.main()
