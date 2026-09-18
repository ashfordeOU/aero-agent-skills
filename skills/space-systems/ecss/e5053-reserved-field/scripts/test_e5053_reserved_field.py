#!/usr/bin/env python3
"""Contract test for the reserved field (offline)."""

import unittest

from e5053_reserved_field_logic import (
    ACCEPT,
    ACCEPT_WITH_RECORD,
    DISCARD,
    RECEIVER,
    RECORD_AND_ACCEPT,
    RESERVED_PATTERN,
    SENDER,
    SENDER_DEFECT,
    SILENT_ACCEPT,
    STRICT_DISCARD,
    assess_reserved_octet,
    encode_reserved_field,
    is_reserved_pattern,
    read_reserved_field,
    reserved_field_offset,
    scan_reserved_field_log,
    validate_reserved_field,
)

UNIT = [3, 7, 40, 2, RESERVED_PATTERN, 1, 8]
DEVIANT_UNIT = [3, 7, 40, 2, 0x5A, 1, 8]


class OffsetTests(unittest.TestCase):
    def test_pathless_unit_puts_the_reserved_octet_third(self):
        self.assertEqual(reserved_field_offset(0), 2)

    def test_each_path_byte_pushes_the_reserved_octet_along(self):
        self.assertEqual(reserved_field_offset(2), 4)
        self.assertEqual(reserved_field_offset(4), 6)

    def test_negative_path_length_rejected(self):
        with self.assertRaises(ValueError):
            reserved_field_offset(-2)

    def test_non_integer_path_length_rejected(self):
        with self.assertRaises(ValueError):
            reserved_field_offset(2.0)


class EncodeTests(unittest.TestCase):
    def test_sender_writes_one_octet_of_the_held_back_pattern(self):
        self.assertEqual(encode_reserved_field(), (RESERVED_PATTERN,))

    def test_encoded_octet_is_the_reserved_pattern(self):
        self.assertTrue(is_reserved_pattern(encode_reserved_field()[0]))

    def test_any_other_octet_is_not_the_reserved_pattern(self):
        self.assertFalse(is_reserved_pattern(1))
        self.assertFalse(is_reserved_pattern(255))

    def test_octet_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            is_reserved_pattern(256)

    def test_boolean_octet_rejected(self):
        with self.assertRaises(ValueError):
            is_reserved_pattern(False)


class ValidateTests(unittest.TestCase):
    def test_reserved_pattern_is_conformant_without_a_finding(self):
        graded = validate_reserved_field(RESERVED_PATTERN)
        self.assertTrue(graded["conformant"])
        self.assertEqual(graded["findings"], [])

    def test_any_other_octet_raises_a_finding(self):
        graded = validate_reserved_field(0x5A)
        self.assertFalse(graded["conformant"])
        self.assertTrue(any("later revision" in f for f in graded["findings"]))


class SenderTests(unittest.TestCase):
    def test_conformant_sender_is_accepted(self):
        outcome = assess_reserved_octet(RESERVED_PATTERN, SENDER)
        self.assertEqual(outcome["disposition"], ACCEPT)
        self.assertTrue(outcome["conformant"])

    def test_non_conformant_sender_must_rewrite_the_field(self):
        outcome = assess_reserved_octet(0x5A, SENDER)
        self.assertEqual(outcome["disposition"], SENDER_DEFECT)
        self.assertTrue(any("no freedom" in f for f in outcome["findings"]))

    def test_sender_disposition_ignores_the_receiver_policy(self):
        for policy in (STRICT_DISCARD, RECORD_AND_ACCEPT, SILENT_ACCEPT):
            outcome = assess_reserved_octet(0x5A, SENDER, policy)
            self.assertEqual(outcome["disposition"], SENDER_DEFECT)

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            assess_reserved_octet(RESERVED_PATTERN, "router")


class ReceiverTests(unittest.TestCase):
    def test_conformant_octet_is_accepted_under_every_policy(self):
        for policy in (STRICT_DISCARD, RECORD_AND_ACCEPT, SILENT_ACCEPT):
            outcome = assess_reserved_octet(RESERVED_PATTERN, RECEIVER, policy)
            self.assertEqual(outcome["disposition"], ACCEPT)
            self.assertEqual(outcome["findings"], [])

    def test_strict_policy_discards_a_deviant_octet(self):
        outcome = assess_reserved_octet(0x5A, RECEIVER, STRICT_DISCARD)
        self.assertEqual(outcome["disposition"], DISCARD)

    def test_recording_policy_accepts_and_leaves_evidence(self):
        outcome = assess_reserved_octet(0x5A, RECEIVER, RECORD_AND_ACCEPT)
        self.assertEqual(outcome["disposition"], ACCEPT_WITH_RECORD)
        self.assertTrue(outcome["findings"])

    def test_silent_policy_accepts_but_is_itself_a_finding(self):
        outcome = assess_reserved_octet(0x5A, RECEIVER, SILENT_ACCEPT)
        self.assertEqual(outcome["disposition"], ACCEPT)
        self.assertTrue(any("no evidence" in f for f in outcome["findings"]))

    def test_unknown_policy_rejected(self):
        with self.assertRaises(ValueError):
            assess_reserved_octet(RESERVED_PATTERN, RECEIVER, "best-effort")


class ReadTests(unittest.TestCase):
    def test_reserved_octet_is_read_after_the_identifier(self):
        self.assertEqual(read_reserved_field(UNIT, 2), RESERVED_PATTERN)

    def test_deviant_unit_reads_back_its_octet(self):
        self.assertEqual(read_reserved_field(DEVIANT_UNIT, 2), 0x5A)

    def test_pathless_unit_reads_the_third_octet(self):
        self.assertEqual(read_reserved_field([82, 2, 0, 1, 8], 0), 0)

    def test_short_unit_rejected(self):
        with self.assertRaises(ValueError):
            read_reserved_field([82, 2], 0)

    def test_non_sequence_unit_rejected(self):
        with self.assertRaises(ValueError):
            read_reserved_field(40, 0)


class LogScanTests(unittest.TestCase):
    def test_clean_log_reports_no_deviation(self):
        report = scan_reserved_field_log([0, 0, 0, 0])
        self.assertEqual(report["verdict"], "log-clean")
        self.assertEqual(report["discarded"], 0)
        self.assertAlmostEqual(report["deviation_rate"], 0.0, places=9)

    def test_strict_policy_discards_every_deviation(self):
        report = scan_reserved_field_log([0, 0x5A, 0, 0x5A], STRICT_DISCARD)
        self.assertEqual(report["discarded"], 2)
        self.assertEqual(report["accepted"], 2)
        self.assertAlmostEqual(report["deviation_rate"], 0.5, places=9)

    def test_recording_policy_keeps_every_unit(self):
        report = scan_reserved_field_log([0, 0x5A, 0, 0x5A], RECORD_AND_ACCEPT)
        self.assertEqual(report["discarded"], 0)
        self.assertEqual(report["accepted"], 4)
        self.assertEqual(report["recorded"], 2)

    def test_deviations_carry_their_positions(self):
        report = scan_reserved_field_log([0, 0x5A, 0])
        self.assertEqual(report["deviations"], ((1, 0x5A),))

    def test_quarter_deviation_rate_is_exact(self):
        report = scan_reserved_field_log([0, 0, 0x01, 0])
        self.assertAlmostEqual(report["deviation_rate"], 0.25, places=9)

    def test_empty_log_rejected(self):
        with self.assertRaises(ValueError):
            scan_reserved_field_log([])

    def test_non_sequence_log_rejected(self):
        with self.assertRaises(ValueError):
            scan_reserved_field_log(0)

    def test_log_with_an_out_of_range_octet_rejected(self):
        with self.assertRaises(ValueError):
            scan_reserved_field_log([0, 300])


if __name__ == "__main__":
    unittest.main()
