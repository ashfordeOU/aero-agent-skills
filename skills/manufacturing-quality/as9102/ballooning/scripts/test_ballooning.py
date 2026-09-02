#!/usr/bin/env python3
"""Gate 3 contract tests for scripts/ballooning.py (stdlib unittest, offline).

Run: python3 scripts/test_ballooning.py
"""

import unittest

from ballooning import (
    accountability_matrix_verdict,
    assign_balloon_numbers,
    balloon_count_reconciliation,
    classify_characteristic,
    verification_method_code,
)


class AssignBalloonNumbersTest(unittest.TestCase):
    def test_sequential_unique_numbers(self):
        numbers = assign_balloon_numbers(
            [{"id": "DIA-1"}, {"id": "DIA-2"}, {"id": "DIA-3"}]
        )
        self.assertEqual(numbers, {"DIA-1": 1, "DIA-2": 2, "DIA-3": 3})

    def test_plain_identifier_items(self):
        numbers = assign_balloon_numbers(["A", "B"])
        self.assertEqual(numbers["A"], 1)
        self.assertEqual(numbers["B"], 2)

    def test_empty_input_returns_empty(self):
        self.assertEqual(assign_balloon_numbers([]), {})

    def test_duplicate_characteristic_raises(self):
        with self.assertRaises(ValueError):
            assign_balloon_numbers([{"id": "X"}, {"id": "X"}])

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assign_balloon_numbers("DIA-1")


class VerificationMethodCodeTest(unittest.TestCase):
    def test_all_five_codes(self):
        self.assertEqual(verification_method_code("measuring"), 1)
        self.assertEqual(verification_method_code("attribute"), 2)
        self.assertEqual(verification_method_code("functional"), 3)
        self.assertEqual(verification_method_code("visual"), 4)
        self.assertEqual(verification_method_code("analytical"), 5)

    def test_variable_alias_is_code_one(self):
        self.assertEqual(verification_method_code("variable"), 1)

    def test_go_no_go_variants_are_code_two(self):
        self.assertEqual(verification_method_code("go-no-go"), 2)
        self.assertEqual(verification_method_code("go no go"), 2)

    def test_case_insensitive_label(self):
        self.assertEqual(verification_method_code("VISUAL"), 4)

    def test_unknown_label_raises(self):
        with self.assertRaises(ValueError):
            verification_method_code("inspection")

    def test_non_string_label_raises(self):
        with self.assertRaises(ValueError):
            verification_method_code(3)


class ClassifyCharacteristicTest(unittest.TestCase):
    def test_three_classifications(self):
        self.assertEqual(classify_characteristic("key"), "key characteristic")
        self.assertEqual(
            classify_characteristic("critical"), "critical characteristic"
        )
        self.assertEqual(classify_characteristic("standard"), "standard")

    def test_case_insensitive_kind(self):
        self.assertEqual(classify_characteristic("Key"), "key characteristic")

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            classify_characteristic("safety")


class BalloonCountReconciliationTest(unittest.TestCase):
    def test_matching_counts_are_match(self):
        verdict = balloon_count_reconciliation(24, 24)
        self.assertEqual(verdict["status"], "match")
        self.assertEqual(verdict["difference"], 0)

    def test_mismatch_reports_difference(self):
        verdict = balloon_count_reconciliation(24, 22)
        self.assertEqual(verdict["status"], "mismatch")
        self.assertEqual(verdict["difference"], 2)

    def test_zero_counts_are_match(self):
        verdict = balloon_count_reconciliation(0, 0)
        self.assertEqual(verdict["status"], "match")

    def test_negative_count_raises(self):
        with self.assertRaises(ValueError):
            balloon_count_reconciliation(-1, 5)


class AccountabilityMatrixVerdictTest(unittest.TestCase):
    def test_complete_matrix(self):
        balloons = [
            {"id": 1, "method": "visual", "classification": "standard"},
            {"id": 2, "method": "measuring", "classification": "key"},
        ]
        verdict = accountability_matrix_verdict(balloons)
        self.assertTrue(verdict["complete"])
        self.assertEqual(verdict["balloon_count"], 2)
        self.assertEqual(verdict["issues"], [])

    def test_missing_method_flags_balloon(self):
        verdict = accountability_matrix_verdict(
            [{"id": 1, "classification": "standard"}]
        )
        self.assertFalse(verdict["complete"])
        self.assertIn("missing method", verdict["issues"][0])

    def test_missing_classification_flags_balloon(self):
        verdict = accountability_matrix_verdict([{"id": 1, "method": "visual"}])
        self.assertFalse(verdict["complete"])
        self.assertIn("missing classification", verdict["issues"][0])

    def test_invalid_method_flags_balloon(self):
        verdict = accountability_matrix_verdict(
            [{"id": 1, "method": "smell", "classification": "standard"}]
        )
        self.assertFalse(verdict["complete"])
        self.assertIn("invalid method", verdict["issues"][0])

    def test_empty_matrix_is_complete(self):
        verdict = accountability_matrix_verdict([])
        self.assertTrue(verdict["complete"])
        self.assertEqual(verdict["balloon_count"], 0)

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            accountability_matrix_verdict({"id": 1})


if __name__ == "__main__":
    unittest.main()
