#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §8.2.9 requirement verifiability check.

Exercises scripts/e1006_char_verifiability_logic.py (stdlib unittest, offline).
Contract: validate_method returns the method string for T/A/I/D and raises
ValueError for any other code; validate_level returns the level string for
system/subsystem/equipment/component and raises for any other identifier;
is_compound_requirement returns True when requirement text contains more than
one 'shall' and False otherwise, including for empty text; assess_verifiability
produces findings for missing text, no method assigned, no level assigned,
an unrecognized method code, an unrecognized level identifier, and compound
text, produces no findings for a fully assigned valid requirement, and never
mutates the input dict; assess_set preserves input order and returns one result
per requirement; summarize_results aggregates totals and findings-by-type
correctly; is_verifiable mirrors the verifiable flag of a result dict.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1006_char_verifiability_logic as vf  # noqa: E402


class ValidateMethodTest(unittest.TestCase):
    def test_test_method_accepted(self):
        self.assertEqual(vf.validate_method("T"), "T")

    def test_analysis_method_accepted(self):
        self.assertEqual(vf.validate_method("A"), "A")

    def test_inspection_method_accepted(self):
        self.assertEqual(vf.validate_method("I"), "I")

    def test_review_of_design_method_accepted(self):
        self.assertEqual(vf.validate_method("D"), "D")

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            vf.validate_method("X")

    def test_lowercase_method_raises(self):
        with self.assertRaises(ValueError):
            vf.validate_method("t")


class ValidateLevelTest(unittest.TestCase):
    def test_system_level_accepted(self):
        self.assertEqual(vf.validate_level("system"), "system")

    def test_subsystem_level_accepted(self):
        self.assertEqual(vf.validate_level("subsystem"), "subsystem")

    def test_equipment_level_accepted(self):
        self.assertEqual(vf.validate_level("equipment"), "equipment")

    def test_component_level_accepted(self):
        self.assertEqual(vf.validate_level("component"), "component")

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            vf.validate_level("mission")

    def test_uppercase_level_raises(self):
        with self.assertRaises(ValueError):
            vf.validate_level("System")


class IsCompoundRequirementTest(unittest.TestCase):
    def test_single_shall_is_not_compound(self):
        self.assertFalse(vf.is_compound_requirement(
            "The unit shall survive a 100 g shock load."
        ))

    def test_two_shall_is_compound(self):
        self.assertTrue(vf.is_compound_requirement(
            "The system shall maintain attitude and shall transmit telemetry."
        ))

    def test_three_shall_is_compound(self):
        self.assertTrue(vf.is_compound_requirement(
            "The system shall power on, shall self-test, and shall report status."
        ))

    def test_empty_text_is_not_compound(self):
        self.assertFalse(vf.is_compound_requirement(""))

    def test_no_shall_is_not_compound(self):
        self.assertFalse(vf.is_compound_requirement(
            "Operating temperature range: -40 to +85 degC."
        ))

    def test_shall_case_insensitive(self):
        self.assertTrue(vf.is_compound_requirement(
            "The unit SHALL operate cold and SHALL operate hot."
        ))


class AssessVerifiabilityTest(unittest.TestCase):
    def _req(self, req_id="R-001", text="The unit shall survive 100 g shock.",
             methods=None, levels=None):
        return {
            "req_id": req_id,
            "text": text,
            "methods": methods if methods is not None else ["T"],
            "levels": levels if levels is not None else ["equipment"],
        }

    def test_fully_assigned_req_is_verifiable(self):
        result = vf.assess_verifiability(self._req())
        self.assertTrue(result["verifiable"])
        self.assertEqual(result["findings"], [])

    def test_result_carries_req_id(self):
        result = vf.assess_verifiability(self._req(req_id="R-007"))
        self.assertEqual(result["req_id"], "R-007")

    def test_empty_text_produces_missing_text_finding(self):
        result = vf.assess_verifiability(self._req(text=""))
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("missing_text", issues)
        self.assertFalse(result["verifiable"])

    def test_whitespace_only_text_produces_missing_text_finding(self):
        result = vf.assess_verifiability(self._req(text="   "))
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("missing_text", issues)

    def test_no_methods_produces_no_method_assigned_finding(self):
        result = vf.assess_verifiability(self._req(methods=[]))
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("no_method_assigned", issues)

    def test_no_levels_produces_no_level_assigned_finding(self):
        result = vf.assess_verifiability(self._req(levels=[]))
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("no_level_assigned", issues)

    def test_invalid_method_code_produces_finding(self):
        result = vf.assess_verifiability(self._req(methods=["Z"]))
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("invalid_method", issues)

    def test_invalid_level_identifier_produces_finding(self):
        result = vf.assess_verifiability(self._req(levels=["mission"]))
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("invalid_level", issues)

    def test_compound_text_produces_compound_requirement_finding(self):
        compound = "The unit shall heat up and shall cool down."
        result = vf.assess_verifiability(self._req(text=compound))
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("compound_requirement", issues)

    def test_multiple_valid_methods_and_levels_accepted(self):
        result = vf.assess_verifiability(
            self._req(methods=["T", "A"], levels=["system", "subsystem"])
        )
        self.assertTrue(result["verifiable"])

    def test_multiple_findings_coexist_when_multiple_problems(self):
        result = vf.assess_verifiability(self._req(text="", methods=[], levels=[]))
        self.assertGreaterEqual(len(result["findings"]), 2)
        self.assertFalse(result["verifiable"])

    def test_input_req_dict_not_mutated(self):
        req = self._req()
        original_methods = list(req["methods"])
        original_levels = list(req["levels"])
        vf.assess_verifiability(req)
        self.assertEqual(req["methods"], original_methods)
        self.assertEqual(req["levels"], original_levels)


class AssessSetTest(unittest.TestCase):
    def test_returns_one_result_per_requirement(self):
        reqs = [
            {"req_id": "R-001", "text": "Shall survive 100 g.", "methods": ["T"], "levels": ["equipment"]},
            {"req_id": "R-002", "text": "Shall operate at minus 40 C.", "methods": [], "levels": ["system"]},
        ]
        results = vf.assess_set(reqs)
        self.assertEqual(len(results), 2)

    def test_order_preserved_across_set(self):
        reqs = [
            {"req_id": "R-A", "text": "Shall do A.", "methods": ["A"], "levels": ["system"]},
            {"req_id": "R-B", "text": "Shall do B.", "methods": ["I"], "levels": ["subsystem"]},
        ]
        results = vf.assess_set(reqs)
        self.assertEqual(results[0]["req_id"], "R-A")
        self.assertEqual(results[1]["req_id"], "R-B")

    def test_empty_set_returns_empty_list(self):
        self.assertEqual(vf.assess_set([]), [])


class SummarizeResultsTest(unittest.TestCase):
    def test_all_verifiable_summary(self):
        reqs = [
            {"req_id": "R-001", "text": "Shall survive shock.", "methods": ["T"], "levels": ["equipment"]},
        ]
        summary = vf.summarize_results(vf.assess_set(reqs))
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["verifiable_count"], 1)
        self.assertEqual(summary["unverifiable_count"], 0)
        self.assertEqual(summary["findings_by_type"], {})

    def test_unverifiable_counts_correctly(self):
        reqs = [
            {"req_id": "R-001", "text": "Shall operate.", "methods": [], "levels": ["equipment"]},
            {"req_id": "R-002", "text": "Shall transmit.", "methods": [], "levels": ["system"]},
        ]
        summary = vf.summarize_results(vf.assess_set(reqs))
        self.assertEqual(summary["unverifiable_count"], 2)
        self.assertEqual(summary["findings_by_type"].get("no_method_assigned"), 2)

    def test_mixed_set_summary(self):
        reqs = [
            {"req_id": "R-001", "text": "Shall survive shock.", "methods": ["T"], "levels": ["equipment"]},
            {"req_id": "R-002", "text": "Shall operate cold.", "methods": [], "levels": []},
        ]
        summary = vf.summarize_results(vf.assess_set(reqs))
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["verifiable_count"], 1)
        self.assertEqual(summary["unverifiable_count"], 1)

    def test_is_verifiable_helper_true_for_passing_result(self):
        req = {"req_id": "R-001", "text": "Shall survive shock.", "methods": ["T"], "levels": ["equipment"]}
        result = vf.assess_verifiability(req)
        self.assertTrue(vf.is_verifiable(result))

    def test_is_verifiable_helper_false_for_failing_result(self):
        req = {"req_id": "R-002", "text": "Shall operate.", "methods": [], "levels": []}
        result = vf.assess_verifiability(req)
        self.assertFalse(vf.is_verifiable(result))


if __name__ == "__main__":
    unittest.main()
