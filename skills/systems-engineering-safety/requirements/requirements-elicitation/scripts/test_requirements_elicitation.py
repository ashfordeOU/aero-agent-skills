#!/usr/bin/env python3
"""Gate 3 contract test: requirements elicitation.

Exercises scripts/requirements_elicitation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (shall clause
counting for atomicity, weasel word detection for unambiguity,
measurable bound checking for verifiability, single-verb structure
checking, traceability field checks, the per-statement quality
assessment with ready or fix verdict, and the elicitation completeness
checklist; invalid inputs raise ValueError.

Anchors:
- count_shall_clauses("The system shall provide X.") = 1
- find_weasel_words("approximately") = ["approximately"]
- has_measurable_bound("within 1.5 percent") = True
- check_single_verb("The system shall open the valve.") = (True, [])
- check_traceability({"id": "REQ-001", "source": "interview"})
  = complete True
- assess_requirement_statement good atomic verifiable statement
  = verdict ready, every quality check True
- elicitation_completeness_check([], [], []) = verdict complete
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requirements_elicitation_logic as rel  # noqa: E402

GOOD_TEXT = "The system shall display the fuel quantity within 1.5 percent of the measured value."


class ShallClauseTest(unittest.TestCase):
    def test_anchor_single_shall(self):
        self.assertEqual(rel.count_shall_clauses(GOOD_TEXT), 1)

    def test_two_shall_clauses(self):
        self.assertEqual(
            rel.count_shall_clauses("The system shall do A and shall do B."), 2
        )

    def test_no_shall_clause(self):
        self.assertEqual(rel.count_shall_clauses("The system provides X."), 0)

    def test_case_insensitive_shall(self):
        self.assertEqual(rel.count_shall_clauses("The System SHALL respond."), 1)

    def test_shall_not_substring(self):
        self.assertEqual(rel.count_shall_clauses("Shallows are avoided."), 0)

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            rel.count_shall_clauses(None)


class WeaselWordTest(unittest.TestCase):
    def test_anchor_approximately(self):
        self.assertEqual(
            rel.find_weasel_words("The part shall be approximately 5 kg."),
            ["approximately"],
        )

    def test_no_weasel_words(self):
        self.assertEqual(rel.find_weasel_words(GOOD_TEXT), [])

    def test_and_or_detected(self):
        self.assertEqual(rel.find_weasel_words("A or B and/or C."), ["and/or"])

    def test_suitable_and_etc(self):
        self.assertEqual(
            rel.find_weasel_words("suitable finish, etc."), ["etc", "suitable"]
        )

    def test_multiword_term(self):
        self.assertEqual(
            rel.find_weasel_words("The result as required by the plan."),
            ["as required"],
        )

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            rel.find_weasel_words(42)


class MeasurableBoundTest(unittest.TestCase):
    def test_anchor_numeric_within(self):
        self.assertTrue(rel.has_measurable_bound(GOOD_TEXT))

    def test_at_least_bound(self):
        self.assertTrue(rel.has_measurable_bound("The system shall carry at least 200 kg."))

    def test_no_numeric_value(self):
        self.assertFalse(rel.has_measurable_bound("The system shall be user friendly."))

    def test_numeric_without_bound_phrase(self):
        self.assertFalse(rel.has_measurable_bound("The system shall display 12 values."))

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            rel.has_measurable_bound(None)


class SingleVerbTest(unittest.TestCase):
    def test_anchor_single_shall(self):
        ok, extras = rel.check_single_verb("The system shall open the valve.")
        self.assertTrue(ok)
        self.assertEqual(extras, [])

    def test_must_flags(self):
        ok, extras = rel.check_single_verb("The system must open the valve.")
        self.assertFalse(ok)
        self.assertIn("must", extras)

    def test_double_shall_flags(self):
        ok, extras = rel.check_single_verb("The system shall do A and shall do B.")
        self.assertFalse(ok)
        self.assertIn("shall x2", extras)

    def test_may_and_should(self):
        ok, extras = rel.check_single_verb("The system should respond and may retry.")
        self.assertFalse(ok)
        self.assertEqual(extras, ["may", "shall x0", "should"])

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            rel.check_single_verb(None)


class TraceabilityTest(unittest.TestCase):
    def test_anchor_complete(self):
        verdict = rel.check_traceability({"id": "REQ-001", "source": "interview"})
        self.assertTrue(verdict["complete"])
        self.assertEqual(verdict["missing"], [])

    def test_missing_source(self):
        verdict = rel.check_traceability({"id": "REQ-001"})
        self.assertFalse(verdict["complete"])
        self.assertEqual(verdict["missing"], ["source"])

    def test_blank_source_is_missing(self):
        verdict = rel.check_traceability({"id": "REQ-001", "source": "  "})
        self.assertFalse(verdict["complete"])
        self.assertEqual(verdict["missing"], ["source"])

    def test_missing_id(self):
        verdict = rel.check_traceability({"source": "interview"})
        self.assertFalse(verdict["complete"])
        self.assertEqual(verdict["missing"], ["id"])

    def test_optional_parent_recorded(self):
        verdict = rel.check_traceability(
            {"id": "REQ-001", "source": "interview", "parent": "HLR-002"}
        )
        self.assertTrue(verdict["complete"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            rel.check_traceability("REQ-001")


class AssessmentTest(unittest.TestCase):
    def test_anchor_good_statement_passes(self):
        req = {
            "id": "REQ-001",
            "text": GOOD_TEXT,
            "source": "stakeholder interview",
            "method": "test",
        }
        result = rel.assess_requirement_statement(req)
        self.assertEqual(result["verdict"], "ready")
        self.assertEqual(result["issues"], [])
        self.assertTrue(all(result["quality_checks"].values()))

    def test_weasel_word_flags(self):
        req = {
            "id": "REQ-002",
            "text": "The system shall be approximately 5 kg.",
            "source": "workshop",
            "method": "test",
        }
        result = rel.assess_requirement_statement(req)
        self.assertEqual(result["verdict"], "fix")
        self.assertFalse(result["quality_checks"]["unambiguity"])
        self.assertIn("unambiguity: weasel words approximately", result["issues"])

    def test_no_bound_flags_verifiability(self):
        req = {
            "id": "REQ-004",
            "text": "The system shall be user friendly.",
            "source": "interview",
            "method": "test",
        }
        result = rel.assess_requirement_statement(req)
        self.assertEqual(result["verdict"], "fix")
        self.assertFalse(result["quality_checks"]["verifiability"])
        self.assertIn("verifiability: no measurable acceptance bound", result["issues"])

    def test_invalid_method_flags_verifiability(self):
        req = {
            "id": "REQ-005",
            "text": GOOD_TEXT,
            "source": "interview",
            "method": "simulation",
        }
        result = rel.assess_requirement_statement(req)
        self.assertFalse(result["quality_checks"]["verifiability"])
        self.assertIn(
            "verifiability: method 'simulation' not in test, analysis, demonstration, inspection",
            result["issues"],
        )

    def test_two_shall_clauses_flag_atomicity(self):
        req = {
            "id": "REQ-006",
            "text": "The system shall open the valve and shall close the latch.",
            "source": "interview",
            "method": "test",
        }
        result = rel.assess_requirement_statement(req)
        self.assertEqual(result["verdict"], "fix")
        self.assertFalse(result["quality_checks"]["atomicity"])
        self.assertIn("atomicity: 2 shall clauses, expected 1", result["issues"])

    def test_missing_key_raises(self):
        with self.assertRaises(ValueError):
            rel.assess_requirement_statement({"method": "test"})

    def test_missing_source_flags_not_raises(self):
        req = {
            "id": "REQ-003",
            "text": GOOD_TEXT,
            "method": "test",
        }
        result = rel.assess_requirement_statement(req)
        self.assertEqual(result["verdict"], "fix")
        self.assertFalse(result["quality_checks"]["traceability"])
        self.assertIn("traceability: missing source", result["issues"])

    def test_non_string_text_raises(self):
        with self.assertRaises(ValueError):
            rel.assess_requirement_statement(
                {"id": "REQ-007", "text": 42, "source": "interview", "method": "test"}
            )


class CompletenessChecklistTest(unittest.TestCase):
    def test_anchor_empty_lists_complete(self):
        result = rel.elicitation_completeness_check([], [], [])
        self.assertEqual(result["verdict"], "complete")

    def test_all_covered(self):
        log_entries = [
            {"need": "fuel awareness", "scenario": "night diversion"},
            {"need": "range margin", "scenario": "night diversion"},
        ]
        result = rel.elicitation_completeness_check(
            ["fuel awareness", "range margin"], ["night diversion"], log_entries
        )
        self.assertEqual(result["verdict"], "complete")
        self.assertEqual(result["missing_needs"], [])
        self.assertEqual(result["missing_scenarios"], [])
        self.assertEqual(result["needs_covered"], 1.0)

    def test_missing_need_gap(self):
        log_entries = [{"need": "fuel awareness", "scenario": "night diversion"}]
        result = rel.elicitation_completeness_check(
            ["fuel awareness", "range margin"], ["night diversion"], log_entries
        )
        self.assertEqual(result["verdict"], "gaps")
        self.assertEqual(result["missing_needs"], ["range margin"])
        self.assertEqual(result["needs_covered"], 0.5)

    def test_missing_scenario_gap(self):
        log_entries = [{"need": "fuel awareness", "scenario": "night diversion"}]
        result = rel.elicitation_completeness_check(
            ["fuel awareness"], ["night diversion", "engine failure"], log_entries
        )
        self.assertEqual(result["verdict"], "gaps")
        self.assertEqual(result["missing_scenarios"], ["engine failure"])

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            rel.elicitation_completeness_check("needs", [], [])


if __name__ == "__main__":
    unittest.main()
