"""
Gate 3 contract tests — e1006-char-identifiability

Stdlib unittest only.  Run with:
    python3 test_e1006_char_identifiability.py

Must print OK when all tests pass.  No network access required.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1006_char_identifiability_logic import (
    DEFAULT_ID_PATTERN,
    validate_identifier_format,
    find_missing_identifiers,
    find_duplicate_identifiers,
    check_format_violations,
    detect_numeric_gaps,
    assess_identifiability,
)


class TestValidateIdentifierFormat(unittest.TestCase):

    def test_standard_three_digit_format_passes(self):
        result = validate_identifier_format("REQ-SYS-001")
        self.assertTrue(result["valid"])

    def test_four_digit_numeric_suffix_passes(self):
        result = validate_identifier_format("REQ-FUN-0042")
        self.assertTrue(result["valid"])

    def test_alphanumeric_segment_passes(self):
        result = validate_identifier_format("REQ2-SYS3-001")
        self.assertTrue(result["valid"])

    def test_lowercase_identifier_fails(self):
        result = validate_identifier_format("req-sys-001")
        self.assertFalse(result["valid"])
        self.assertIn("does not match", result["message"])

    def test_missing_middle_segment_fails(self):
        result = validate_identifier_format("REQ-001")
        self.assertFalse(result["valid"])

    def test_empty_string_fails(self):
        result = validate_identifier_format("")
        self.assertFalse(result["valid"])
        self.assertIn("absent or a placeholder", result["message"])

    def test_none_value_fails(self):
        result = validate_identifier_format(None)
        self.assertFalse(result["valid"])

    def test_tbd_placeholder_fails(self):
        result = validate_identifier_format("TBD")
        self.assertFalse(result["valid"])

    def test_custom_pattern_match(self):
        result = validate_identifier_format("R-001", pattern=r'^R-\d{3}$')
        self.assertTrue(result["valid"])

    def test_custom_pattern_no_match(self):
        result = validate_identifier_format("REQ-SYS-001", pattern=r'^R-\d{3}$')
        self.assertFalse(result["valid"])

    def test_integer_input_fails_with_type_message(self):
        result = validate_identifier_format(42)
        self.assertFalse(result["valid"])
        self.assertIn("int", result["message"])


class TestFindMissingIdentifiers(unittest.TestCase):

    def test_no_missing_returns_empty_list(self):
        reqs = [{"id": "REQ-SYS-001"}, {"id": "REQ-SYS-002"}]
        self.assertEqual(find_missing_identifiers(reqs), [])

    def test_none_id_detected_as_missing(self):
        reqs = [{"id": "REQ-SYS-001"}, {"id": None}, {"id": "REQ-SYS-003"}]
        self.assertEqual(find_missing_identifiers(reqs), [1])

    def test_empty_string_id_detected_as_missing(self):
        reqs = [{"id": ""}, {"id": "REQ-SYS-001"}]
        self.assertIn(0, find_missing_identifiers(reqs))

    def test_tbd_placeholder_detected_as_missing(self):
        reqs = [{"id": "TBD"}, {"id": "REQ-SYS-001"}]
        self.assertIn(0, find_missing_identifiers(reqs))

    def test_tbc_placeholder_detected_as_missing(self):
        reqs = [{"id": "REQ-SYS-001"}, {"id": "TBC"}]
        self.assertIn(1, find_missing_identifiers(reqs))

    def test_multiple_missing_all_reported(self):
        reqs = [{"id": None}, {"id": "REQ-SYS-002"}, {"id": "TBD"}]
        missing = find_missing_identifiers(reqs)
        self.assertIn(0, missing)
        self.assertIn(2, missing)

    def test_empty_requirements_list_returns_empty(self):
        self.assertEqual(find_missing_identifiers([]), [])

    def test_invalid_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            find_missing_identifiers("not-a-list")


class TestFindDuplicateIdentifiers(unittest.TestCase):

    def test_no_duplicates_returns_empty_dict(self):
        reqs = [{"id": "REQ-SYS-001"}, {"id": "REQ-SYS-002"}]
        self.assertEqual(find_duplicate_identifiers(reqs), {})

    def test_one_duplicate_pair_detected(self):
        reqs = [
            {"id": "REQ-SYS-001"},
            {"id": "REQ-SYS-002"},
            {"id": "REQ-SYS-001"},
        ]
        dupes = find_duplicate_identifiers(reqs)
        self.assertIn("REQ-SYS-001", dupes)
        self.assertEqual(sorted(dupes["REQ-SYS-001"]), [0, 2])
        self.assertNotIn("REQ-SYS-002", dupes)

    def test_triple_occurrence_all_indices_recorded(self):
        reqs = [{"id": "REQ-SYS-001"}] * 3
        dupes = find_duplicate_identifiers(reqs)
        self.assertEqual(sorted(dupes["REQ-SYS-001"]), [0, 1, 2])

    def test_missing_ids_not_counted_as_duplicates(self):
        reqs = [{"id": None}, {"id": None}, {"id": "REQ-SYS-001"}]
        dupes = find_duplicate_identifiers(reqs)
        self.assertNotIn(None, dupes)

    def test_empty_requirements_list_returns_empty_dict(self):
        self.assertEqual(find_duplicate_identifiers([]), {})


class TestCheckFormatViolations(unittest.TestCase):

    def test_all_valid_returns_empty(self):
        reqs = [{"id": "REQ-SYS-001"}, {"id": "REQ-FUN-002"}]
        self.assertEqual(check_format_violations(reqs), [])

    def test_lowercase_id_flagged(self):
        reqs = [{"id": "req-sys-001"}]
        violations = check_format_violations(reqs)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["index"], 0)

    def test_missing_id_not_included_in_format_violations(self):
        reqs = [{"id": None}]
        violations = check_format_violations(reqs)
        self.assertEqual(violations, [])

    def test_multiple_violations_all_reported(self):
        reqs = [{"id": "req-001"}, {"id": "REQ-SYS-001"}, {"id": "bad"}]
        violations = check_format_violations(reqs)
        violated_indices = [v["index"] for v in violations]
        self.assertIn(0, violated_indices)
        self.assertIn(2, violated_indices)
        self.assertNotIn(1, violated_indices)


class TestDetectNumericGaps(unittest.TestCase):

    def test_consecutive_sequence_no_gaps(self):
        reqs = [
            {"id": "REQ-SYS-001"},
            {"id": "REQ-SYS-002"},
            {"id": "REQ-SYS-003"},
        ]
        gaps = detect_numeric_gaps(reqs, "REQ-SYS-")
        self.assertEqual(gaps, [])

    def test_single_missing_number_no_gap_reported(self):
        reqs = [{"id": "REQ-SYS-001"}, {"id": "REQ-SYS-003"}]
        gaps = detect_numeric_gaps(reqs, "REQ-SYS-")
        self.assertEqual(gaps, [])

    def test_large_gap_detected(self):
        reqs = [{"id": "REQ-SYS-001"}, {"id": "REQ-SYS-010"}]
        gaps = detect_numeric_gaps(reqs, "REQ-SYS-")
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["missing_count"], 8)
        self.assertEqual(gaps[0]["after"], 1)
        self.assertEqual(gaps[0]["before"], 10)

    def test_only_one_matching_prefix_no_gap(self):
        reqs = [{"id": "REQ-SYS-001"}]
        gaps = detect_numeric_gaps(reqs, "REQ-SYS-")
        self.assertEqual(gaps, [])

    def test_non_matching_prefix_ignored(self):
        reqs = [{"id": "REQ-FUN-001"}, {"id": "REQ-FUN-020"}]
        gaps = detect_numeric_gaps(reqs, "REQ-SYS-")
        self.assertEqual(gaps, [])


class TestAssessIdentifiability(unittest.TestCase):

    def test_fully_compliant_set_passes(self):
        reqs = [
            {"id": "REQ-SYS-001", "text": "The system shall operate at 28 V."},
            {"id": "REQ-SYS-002", "text": "The system shall survive 10 g vibration."},
        ]
        result = assess_identifiability(reqs)
        self.assertTrue(result["compliant"])
        self.assertIn("passed", result["summary"])
        self.assertEqual(result["findings"]["missing_ids"], [])
        self.assertEqual(result["findings"]["format_violations"], [])
        self.assertEqual(result["findings"]["duplicates"], {})

    def test_missing_id_makes_noncompliant(self):
        reqs = [{"id": "REQ-SYS-001"}, {"id": None}]
        result = assess_identifiability(reqs)
        self.assertFalse(result["compliant"])
        self.assertIn(1, result["findings"]["missing_ids"])
        self.assertIn("Findings", result["summary"])

    def test_duplicate_id_makes_noncompliant(self):
        reqs = [{"id": "REQ-SYS-001"}, {"id": "REQ-SYS-001"}]
        result = assess_identifiability(reqs)
        self.assertFalse(result["compliant"])
        self.assertIn("REQ-SYS-001", result["findings"]["duplicates"])

    def test_format_violation_makes_noncompliant(self):
        reqs = [{"id": "req-sys-001"}]
        result = assess_identifiability(reqs)
        self.assertFalse(result["compliant"])
        self.assertTrue(len(result["findings"]["format_violations"]) > 0)

    def test_empty_requirement_set_is_compliant(self):
        result = assess_identifiability([])
        self.assertTrue(result["compliant"])

    def test_custom_pattern_applied(self):
        reqs = [{"id": "R-001"}]
        result = assess_identifiability(reqs, id_pattern=r'^R-\d{3}$')
        self.assertTrue(result["compliant"])

    def test_custom_pattern_violation_detected(self):
        reqs = [{"id": "REQ-SYS-001"}]
        result = assess_identifiability(reqs, id_pattern=r'^R-\d{3}$')
        self.assertFalse(result["compliant"])

    def test_invalid_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            assess_identifiability("not-a-list")

    def test_summary_lists_all_finding_types(self):
        reqs = [
            {"id": None},
            {"id": "bad-format"},
            {"id": "REQ-SYS-001"},
            {"id": "REQ-SYS-001"},
        ]
        result = assess_identifiability(reqs)
        self.assertFalse(result["compliant"])
        self.assertIn("lack an identifier", result["summary"])
        self.assertIn("format violation", result["summary"])
        self.assertIn("duplicate", result["summary"])

    def test_na_placeholder_treated_as_missing(self):
        reqs = [{"id": "N/A"}]
        result = assess_identifiability(reqs)
        self.assertFalse(result["compliant"])
        self.assertIn(0, result["findings"]["missing_ids"])


if __name__ == "__main__":
    unittest.main()
