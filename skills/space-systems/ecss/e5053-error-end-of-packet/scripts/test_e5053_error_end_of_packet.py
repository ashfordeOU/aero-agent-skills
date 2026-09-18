"""Contract tests for the clause 5.5.4.4 error end of packet logic."""

import unittest

from e5053_error_end_of_packet_logic import (
    BURST_FAULT,
    DELIVER,
    DISCARD,
    ERROR_END,
    HARD_FAULT,
    HEALTHY,
    NORMAL_END,
    NO_END,
    SPORADIC,
    diagnose_link,
    handle_terminated_transfer,
    longest_error_run,
    normalize_terminator,
    scan_sequence,
    validate_octet_count,
)


class NormalizeTests(unittest.TestCase):
    def test_canonical_error_token(self):
        self.assertEqual(normalize_terminator("eep"), ERROR_END)

    def test_spelled_out_error_token(self):
        self.assertEqual(normalize_terminator("error-end-of-packet"), ERROR_END)

    def test_case_and_space_tolerated(self):
        self.assertEqual(normalize_terminator("  EOP "), NORMAL_END)

    def test_unterminated_token(self):
        self.assertEqual(normalize_terminator("truncated"), NO_END)

    def test_unknown_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_terminator("maybe")

    def test_non_string_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_terminator(1)


class OctetCountTests(unittest.TestCase):
    def test_zero_accepted(self):
        self.assertEqual(validate_octet_count(0), 0)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_octet_count(-1)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_octet_count(True)

    def test_float_rejected(self):
        with self.assertRaises(ValueError):
            validate_octet_count(4.0)


class DispositionTests(unittest.TestCase):
    def test_normal_termination_delivers(self):
        result = handle_terminated_transfer(NORMAL_END, 32)
        self.assertEqual(result["disposition"], DELIVER)
        self.assertEqual(result["octets_delivered"], 32)

    def test_normal_termination_reports_nothing(self):
        self.assertIsNone(handle_terminated_transfer(NORMAL_END, 32)["report"])

    def test_error_termination_discards(self):
        self.assertEqual(handle_terminated_transfer(ERROR_END, 32)["disposition"], DISCARD)

    def test_error_termination_delivers_no_octets(self):
        self.assertEqual(handle_terminated_transfer(ERROR_END, 32)["octets_delivered"], 0)

    def test_error_termination_discards_the_whole_transfer(self):
        self.assertEqual(handle_terminated_transfer(ERROR_END, 32)["octets_discarded"], 32)

    def test_error_termination_reports(self):
        report = handle_terminated_transfer(ERROR_END, 32)["report"]
        self.assertIn("error terminator", report)
        self.assertIn("32", report)

    def test_unterminated_transfer_also_discards(self):
        result = handle_terminated_transfer(NO_END, 7)
        self.assertEqual(result["disposition"], DISCARD)
        self.assertIn("extent is unknown", result["report"])

    def test_zero_octet_error_transfer_is_handled(self):
        result = handle_terminated_transfer(ERROR_END, 0)
        self.assertEqual(result["octets_discarded"], 0)
        self.assertEqual(result["disposition"], DISCARD)


class ErrorRunTests(unittest.TestCase):
    def test_no_errors_gives_zero(self):
        self.assertEqual(longest_error_run([NORMAL_END, NORMAL_END]), 0)

    def test_single_error_gives_one(self):
        self.assertEqual(longest_error_run([NORMAL_END, ERROR_END, NORMAL_END]), 1)

    def test_longest_run_is_taken_not_the_last(self):
        ends = [ERROR_END, ERROR_END, ERROR_END, NORMAL_END, ERROR_END]
        self.assertEqual(longest_error_run(ends), 3)

    def test_normal_termination_breaks_a_run(self):
        ends = [ERROR_END, NORMAL_END, ERROR_END]
        self.assertEqual(longest_error_run(ends), 1)

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            longest_error_run([])

    def test_text_sequence_rejected(self):
        with self.assertRaises(ValueError):
            longest_error_run("eep")


class ScanTests(unittest.TestCase):
    def test_counts_split_by_disposition(self):
        scan = scan_sequence([NORMAL_END, ERROR_END, NO_END, NORMAL_END])
        self.assertEqual(scan["delivered"], 2)
        self.assertEqual(scan["error_terminated"], 1)
        self.assertEqual(scan["unterminated"], 1)

    def test_discarded_is_errors_plus_unterminated(self):
        scan = scan_sequence([ERROR_END, NO_END, NORMAL_END])
        self.assertEqual(scan["discarded"], 2)

    def test_clean_sequence_has_a_zero_ratio(self):
        self.assertAlmostEqual(scan_sequence([NORMAL_END] * 4)["discard_ratio"], 0.0, places=9)

    def test_half_discarded_sequence_ratio(self):
        scan = scan_sequence([NORMAL_END, ERROR_END])
        self.assertAlmostEqual(scan["discard_ratio"], 0.5, places=9)

    def test_every_discard_produces_a_report(self):
        scan = scan_sequence([ERROR_END, ERROR_END, NORMAL_END])
        self.assertEqual(scan["reports"], scan["discarded"])


class DiagnoseTests(unittest.TestCase):
    def test_clean_link_is_healthy(self):
        result = diagnose_link([NORMAL_END] * 6)
        self.assertEqual(result["verdict"], HEALTHY)
        self.assertEqual(result["findings"], [])

    def test_isolated_errors_are_sporadic(self):
        ends = [NORMAL_END] * 8 + [ERROR_END, NORMAL_END]
        self.assertEqual(diagnose_link(ends)["verdict"], SPORADIC)

    def test_clustered_errors_are_a_burst_fault(self):
        ends = [NORMAL_END] * 7 + [ERROR_END, ERROR_END, ERROR_END]
        self.assertEqual(diagnose_link(ends)["verdict"], BURST_FAULT)

    def test_mostly_discarded_is_a_hard_fault(self):
        ends = [ERROR_END, ERROR_END, ERROR_END, NORMAL_END]
        self.assertEqual(diagnose_link(ends)["verdict"], HARD_FAULT)

    def test_burst_threshold_is_configurable(self):
        ends = [NORMAL_END] * 8 + [ERROR_END, ERROR_END]
        self.assertEqual(diagnose_link(ends, burst_threshold=2)["verdict"], BURST_FAULT)

    def test_burst_finding_names_the_run_length(self):
        ends = [NORMAL_END] * 7 + [ERROR_END] * 3
        findings = diagnose_link(ends)["findings"]
        self.assertTrue(any("3 consecutive" in f for f in findings))

    def test_hard_fault_finding_says_the_link_delivers_nothing(self):
        findings = diagnose_link([ERROR_END, ERROR_END, NORMAL_END])["findings"]
        self.assertTrue(any("delivering nothing" in f for f in findings))

    def test_zero_burst_threshold_rejected(self):
        with self.assertRaises(ValueError):
            diagnose_link([NORMAL_END], burst_threshold=0)

    def test_non_integer_burst_threshold_rejected(self):
        with self.assertRaises(ValueError):
            diagnose_link([NORMAL_END], burst_threshold=2.5)


if __name__ == "__main__":
    unittest.main()
