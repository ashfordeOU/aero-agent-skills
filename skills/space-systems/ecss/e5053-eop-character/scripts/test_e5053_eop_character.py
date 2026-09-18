"""Contract tests for the clause 5.4.1.8 end-of-packet marker logic."""

import unittest

from e5053_eop_character_logic import (
    DELIVER,
    DISCARD,
    EEP,
    EOP,
    NO_MARKER,
    assess_transfer,
    grade_reception,
    marker_disposition,
    normalise_marker,
)


class NormaliseMarkerTests(unittest.TestCase):
    def test_canonical_token_passes_through(self):
        self.assertEqual(normalise_marker("EOP"), EOP)

    def test_lowercase_is_accepted(self):
        self.assertEqual(normalise_marker("eep"), EEP)

    def test_surrounding_whitespace_is_trimmed(self):
        self.assertEqual(normalise_marker("  EOP  "), EOP)

    def test_spelled_out_alias_is_accepted(self):
        self.assertEqual(normalise_marker("error end of packet"), EEP)

    def test_none_is_the_missing_marker(self):
        self.assertEqual(normalise_marker(None), NO_MARKER)

    def test_blank_marker_rejected(self):
        with self.assertRaises(ValueError):
            normalise_marker("   ")

    def test_unknown_marker_rejected(self):
        with self.assertRaises(ValueError):
            normalise_marker("FCT")

    def test_non_string_marker_rejected(self):
        with self.assertRaises(ValueError):
            normalise_marker(2)


class DispositionTests(unittest.TestCase):
    def test_normal_marker_delivers(self):
        self.assertEqual(marker_disposition("EOP")[0], DELIVER)

    def test_error_marker_discards(self):
        self.assertEqual(marker_disposition("EEP")[0], DISCARD)

    def test_missing_marker_discards(self):
        self.assertEqual(marker_disposition(None)[0], DISCARD)

    def test_error_and_missing_have_different_reasons(self):
        self.assertNotEqual(marker_disposition("EEP")[1], marker_disposition(None)[1])


class AssessTransferTests(unittest.TestCase):
    def test_good_transfer_is_deliverable(self):
        result = assess_transfer("EOP", 64, 64)
        self.assertTrue(result["deliverable"])
        self.assertEqual(result["findings"], [])

    def test_error_marker_transfer_is_not_deliverable(self):
        result = assess_transfer("EEP", 30, 64)
        self.assertFalse(result["deliverable"])
        self.assertEqual(result["disposition"], DISCARD)

    def test_short_transfer_with_normal_marker_points_at_the_sender(self):
        result = assess_transfer("EOP", 30, 64)
        self.assertFalse(result["deliverable"])
        self.assertTrue(any("sender" in f for f in result["findings"]))

    def test_lengths_may_be_omitted(self):
        result = assess_transfer("EOP")
        self.assertTrue(result["deliverable"])

    def test_negative_length_rejected(self):
        with self.assertRaises(ValueError):
            assess_transfer("EOP", -1, 64)

    def test_non_integer_length_rejected(self):
        with self.assertRaises(ValueError):
            assess_transfer("EOP", 12.5, 64)

    def test_boolean_length_rejected(self):
        with self.assertRaises(ValueError):
            assess_transfer("EOP", True, 64)

    def test_missing_marker_carries_its_reason(self):
        result = assess_transfer(None)
        self.assertIn("never terminated", result["reason"])


class GradeReceptionTests(unittest.TestCase):
    def test_all_normal_markers_are_within_a_zero_budget(self):
        result = grade_reception(["EOP"] * 8)
        self.assertTrue(result["within_budget"])
        self.assertEqual(result["delivered"], 8)
        self.assertAlmostEqual(result["discard_ratio"], 0.0, places=9)

    def test_discard_ratio_counts_both_bad_outcomes(self):
        result = grade_reception(["EOP", "EEP", None, "EOP"])
        self.assertEqual(result["discarded"], 2)
        self.assertAlmostEqual(result["discard_ratio"], 0.5, places=9)

    def test_counts_are_broken_out_by_marker(self):
        result = grade_reception(["EOP", "EEP", "EEP", None], max_discard_ratio=1.0)
        self.assertEqual(result["counts"][EOP], 1)
        self.assertEqual(result["counts"][EEP], 2)
        self.assertEqual(result["counts"][NO_MARKER], 1)

    def test_ratio_equal_to_the_budget_stays_within_budget(self):
        result = grade_reception(["EOP"] * 9 + ["EEP"], max_discard_ratio=0.1)
        self.assertAlmostEqual(result["discard_ratio"], 0.1, places=9)
        self.assertTrue(result["within_budget"])

    def test_ratio_above_the_budget_is_flagged(self):
        result = grade_reception(["EEP", "EEP", "EOP", "EOP"], max_discard_ratio=0.1)
        self.assertFalse(result["within_budget"])
        self.assertTrue(any("budget" in f for f in result["findings"]))

    def test_absent_terminator_is_always_reported(self):
        result = grade_reception(["EOP", None], max_discard_ratio=1.0)
        self.assertTrue(result["within_budget"])
        self.assertTrue(any("no terminator" in f for f in result["findings"]))

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            grade_reception([])

    def test_string_sequence_rejected(self):
        with self.assertRaises(ValueError):
            grade_reception("EOP")

    def test_budget_above_one_rejected(self):
        with self.assertRaises(ValueError):
            grade_reception(["EOP"], max_discard_ratio=1.5)

    def test_negative_budget_rejected(self):
        with self.assertRaises(ValueError):
            grade_reception(["EOP"], max_discard_ratio=-0.1)

    def test_unknown_marker_in_the_sequence_rejected(self):
        with self.assertRaises(ValueError):
            grade_reception(["EOP", "ESC"])


if __name__ == "__main__":
    unittest.main()
