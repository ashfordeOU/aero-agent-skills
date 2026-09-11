"""
test_e1006_char_singularity.py

Offline deterministic unit tests for e1006_char_singularity_logic.
Run: python3 test_e1006_char_singularity.py
Expected output: OK
"""

import sys
import os
import unittest

# Allow running from the scripts/ directory or from the repo root.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1006_char_singularity_logic import (
    check_singularity,
    check_requirement_set,
    summary,
    SingularityResult,
    SingularityViolation,
)


class TestSingleStatementCompliant(unittest.TestCase):

    def test_single_shall_no_conjunction_is_compliant(self):
        result = check_singularity("The system shall measure inlet pressure.")
        self.assertTrue(result.compliant)
        self.assertEqual(result.violations, [])
        self.assertEqual(result.shall_count, 1)

    def test_no_shall_statement_is_compliant(self):
        result = check_singularity("All actuators must operate within thermal limits.")
        self.assertTrue(result.compliant)
        self.assertEqual(result.shall_count, 0)

    def test_shall_with_simple_object_list_is_compliant(self):
        # Listing values (5V and 12V) is not a compound requirement
        result = check_singularity(
            "The power unit shall supply 5 V and 12 V to the payload bus."
        )
        # compound-predicate does not fire because 'and' is followed by '12'
        # which is not an action verb in the pattern list.
        self.assertTrue(result.compliant)

    def test_whitespace_stripped_before_check(self):
        result = check_singularity("  The system shall log all telemetry frames.  ")
        self.assertTrue(result.compliant)
        self.assertEqual(result.statement, "The system shall log all telemetry frames.")


class TestMultipleShallViolation(unittest.TestCase):

    def test_two_shall_clauses_fires_multiple_shall(self):
        stmt = (
            "The system shall measure pressure and "
            "the system shall report it to the ground station."
        )
        result = check_singularity(stmt)
        self.assertFalse(result.compliant)
        ids = [v.pattern_id for v in result.violations]
        self.assertIn("multiple-shall", ids)

    def test_shall_count_reflects_actual_occurrences(self):
        stmt = "The unit shall store data and the unit shall transmit data."
        result = check_singularity(stmt)
        self.assertEqual(result.shall_count, 2)

    def test_multiple_shall_suppresses_compound_predicate(self):
        stmt = (
            "The system shall receive the command and shall process it "
            "and report the result."
        )
        result = check_singularity(stmt)
        ids = [v.pattern_id for v in result.violations]
        self.assertIn("multiple-shall", ids)
        self.assertNotIn("compound-predicate", ids)


class TestAndShallViolation(unittest.TestCase):

    def test_and_shall_fires(self):
        stmt = "The system shall store data and shall retrieve it on demand."
        result = check_singularity(stmt)
        self.assertFalse(result.compliant)
        ids = [v.pattern_id for v in result.violations]
        self.assertIn("and-shall", ids)
        self.assertIn("multiple-shall", ids)

    def test_case_insensitive_and_shall(self):
        stmt = "The device SHALL transmit packets AND SHALL log each event."
        result = check_singularity(stmt)
        ids = [v.pattern_id for v in result.violations]
        self.assertIn("and-shall", ids)


class TestAsWellAsViolation(unittest.TestCase):

    def test_as_well_as_fires(self):
        stmt = (
            "The system shall measure temperature as well as "
            "atmospheric pressure."
        )
        result = check_singularity(stmt)
        self.assertFalse(result.compliant)
        ids = [v.pattern_id for v in result.violations]
        self.assertIn("as-well-as", ids)

    def test_violation_carries_recommendation(self):
        stmt = "The unit shall record events as well as forward them."
        result = check_singularity(stmt)
        self.assertTrue(len(result.violations) > 0)
        for v in result.violations:
            self.assertIsInstance(v.recommendation, str)
            self.assertTrue(len(v.recommendation) > 0)


class TestInAdditionToViolation(unittest.TestCase):

    def test_in_addition_to_fires(self):
        stmt = (
            "The system shall transmit telemetry in addition to "
            "storing a local backup."
        )
        result = check_singularity(stmt)
        self.assertFalse(result.compliant)
        ids = [v.pattern_id for v in result.violations]
        self.assertIn("in-addition-to", ids)


class TestShallListViolation(unittest.TestCase):

    def test_shall_colon_list_fires(self):
        stmt = (
            "The system shall: measure pressure; report altitude; "
            "log temperature."
        )
        result = check_singularity(stmt)
        self.assertFalse(result.compliant)
        ids = [v.pattern_id for v in result.violations]
        self.assertIn("shall-list", ids)

    def test_shall_colon_with_space_fires(self):
        stmt = "The subsystem shall : perform self-test; report status."
        result = check_singularity(stmt)
        ids = [v.pattern_id for v in result.violations]
        self.assertIn("shall-list", ids)


class TestCompoundPredicateViolation(unittest.TestCase):

    def test_shall_and_action_verb_fires(self):
        stmt = "The system shall receive the uplink command and process it."
        result = check_singularity(stmt)
        self.assertFalse(result.compliant)
        ids = [v.pattern_id for v in result.violations]
        self.assertIn("compound-predicate", ids)

    def test_shall_and_provide_fires(self):
        stmt = "The software shall monitor the queue and provide status updates."
        result = check_singularity(stmt)
        ids = [v.pattern_id for v in result.violations]
        self.assertIn("compound-predicate", ids)


class TestInputValidation(unittest.TestCase):

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_singularity("")

    def test_whitespace_only_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_singularity("   ")

    def test_integer_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_singularity(42)

    def test_none_input_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_singularity(None)


class TestCheckRequirementSet(unittest.TestCase):

    def test_mixed_set_returns_correct_counts(self):
        statements = [
            "The system shall measure pressure.",
            "The system shall store data and shall transmit it.",
            "The unit shall log events.",
        ]
        results = check_requirement_set(statements)
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0].compliant)
        self.assertFalse(results[1].compliant)
        self.assertTrue(results[2].compliant)

    def test_empty_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_requirement_set([])

    def test_non_list_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            check_requirement_set("The system shall measure pressure.")

    def test_preserves_input_order(self):
        statements = [
            "The system shall control attitude.",
            "The unit shall store data and shall transmit it.",
        ]
        results = check_requirement_set(statements)
        self.assertEqual(results[0].statement, "The system shall control attitude.")
        self.assertFalse(results[1].compliant)


class TestSummary(unittest.TestCase):

    def test_all_compliant_summary(self):
        statements = [
            "The system shall measure pressure.",
            "The unit shall log telemetry.",
        ]
        results = check_requirement_set(statements)
        s = summary(results)
        self.assertEqual(s["total"], 2)
        self.assertEqual(s["compliant_count"], 2)
        self.assertEqual(s["non_compliant_count"], 0)
        self.assertEqual(s["non_compliant_indices"], [])

    def test_mixed_summary_indices(self):
        statements = [
            "The system shall measure pressure.",
            "The system shall store and transmit data.",
            "The unit shall log telemetry.",
            "The device shall record events as well as forward them.",
        ]
        results = check_requirement_set(statements)
        s = summary(results)
        self.assertEqual(s["total"], 4)
        self.assertEqual(s["non_compliant_count"], 2)
        self.assertIn(1, s["non_compliant_indices"])
        self.assertIn(3, s["non_compliant_indices"])

    def test_summary_non_list_raises_type_error(self):
        with self.assertRaises(TypeError):
            summary("not a list")


if __name__ == "__main__":
    unittest.main()
