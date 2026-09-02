#!/usr/bin/env python3
"""Gate 3 contract test: ARP4754A derived requirements.

Exercises scripts/derived_requirements_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a requirement
with no parent trace and a design-decision source classifies as derived
with full rationale required; a requirement traced to a parent and a
source document classifies as allocated; interface-resolution and
implementation-constraint cases classify correctly; missing rationale
fails validation; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import derived_requirements_logic as drl  # noqa: E402


class ClassificationTest(unittest.TestCase):
    def test_no_parent_trace_design_decision_is_derived_full_rationale(self):
        req = {
            "has_parent_trace": False,
            "has_source_doc": False,
            "derivation_source": "design_decision",
        }
        classification, rationale = drl.classify_requirement(req)
        self.assertEqual(classification, "derived")
        self.assertEqual(
            rationale,
            list(drl.DERIVATION_SOURCES) + list(drl.RATIONALE_FIELDS),
        )

    def test_parent_trace_and_source_doc_is_allocated(self):
        req = {
            "has_parent_trace": True,
            "has_source_doc": True,
            "derivation_source": None,
        }
        classification, rationale = drl.classify_requirement(req)
        self.assertEqual(classification, "allocated")
        self.assertEqual(rationale, [])

    def test_source_doc_alone_is_allocated(self):
        req = {
            "has_parent_trace": False,
            "has_source_doc": True,
            "derivation_source": None,
        }
        self.assertEqual(drl.classify_requirement(req)[0], "allocated")

    def test_interface_resolution_is_derived(self):
        req = {
            "has_parent_trace": False,
            "has_source_doc": False,
            "derivation_source": "interface_resolution",
        }
        classification, rationale = drl.classify_requirement(req)
        self.assertEqual(classification, "derived")
        self.assertEqual(rationale[0], "design_decision")

    def test_implementation_constraint_is_derived(self):
        req = {
            "has_parent_trace": False,
            "has_source_doc": False,
            "derivation_source": "implementation_constraint",
        }
        self.assertEqual(drl.classify_requirement(req)[0], "derived")

    def test_architectural_choice_and_environmental_assumption_are_derived(self):
        for source in ("architectural_choice", "environmental_assumption"):
            req = {
                "has_parent_trace": False,
                "has_source_doc": False,
                "derivation_source": source,
            }
            self.assertEqual(drl.classify_requirement(req)[0], "derived")


class RationaleTest(unittest.TestCase):
    def test_full_rationale_passes_validation(self):
        req = {
            "has_parent_trace": False,
            "has_source_doc": False,
            "derivation_source": "design_decision",
            "derivation_rationale": "backup unit must cover diversion duration",
            "impact_analysis": "electrical load analysis and verification plan",
        }
        self.assertTrue(drl.validate_requirement(req))

    def test_missing_rationale_fails_validation(self):
        req = {
            "has_parent_trace": False,
            "has_source_doc": False,
            "derivation_source": "design_decision",
            "derivation_rationale": "",
            "impact_analysis": "electrical load analysis",
        }
        self.assertFalse(drl.validate_requirement(req))
        checks = drl.validation_checklist(req)
        self.assertFalse(dict((f, ok) for f, ok, _ in checks)["derivation_rationale"])

    def test_missing_impact_analysis_fails_validation(self):
        req = {
            "has_parent_trace": False,
            "has_source_doc": False,
            "derivation_source": "interface_resolution",
            "derivation_rationale": "pin allocation resolved at design",
            "impact_analysis": "  ",
        }
        self.assertFalse(drl.validate_requirement(req))

    def test_allocated_requirement_passes_without_rationale(self):
        req = {
            "has_parent_trace": True,
            "has_source_doc": True,
            "derivation_source": None,
        }
        self.assertTrue(drl.validate_requirement(req))
        self.assertEqual(drl.required_rationale(req), [])

    def test_checklist_reports_derivation_source_and_rationale(self):
        req = {
            "has_parent_trace": False,
            "has_source_doc": False,
            "derivation_source": "design_decision",
            "derivation_rationale": "reason",
            "impact_analysis": "effect",
        }
        checks = drl.validation_checklist(req)
        ok = dict((f, ok) for f, ok, _ in checks)
        self.assertTrue(ok["derivation_source"])
        self.assertTrue(ok["derivation_rationale"])
        self.assertTrue(ok["impact_analysis"])
        self.assertEqual(len(checks), 3)

    def test_derived_without_source_fails_validation(self):
        req = {
            "has_parent_trace": False,
            "has_source_doc": False,
            "derivation_rationale": "reason",
            "impact_analysis": "effect",
        }
        self.assertFalse(drl.validate_requirement(req))


class InvalidInputTest(unittest.TestCase):
    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            drl.classify_requirement("derived requirement")

    def test_missing_traceability_key_raises(self):
        req = {"has_source_doc": False}
        with self.assertRaises(ValueError):
            drl.classify_requirement(req)

    def test_non_bool_traceability_raises(self):
        req = {"has_parent_trace": "yes", "has_source_doc": False}
        with self.assertRaises(ValueError):
            drl.classify_requirement(req)

    def test_unknown_derivation_source_raises(self):
        req = {
            "has_parent_trace": False,
            "has_source_doc": False,
            "derivation_source": "marketing_input",
        }
        with self.assertRaises(ValueError):
            drl.classify_requirement(req)

    def test_validate_raises_on_invalid_input(self):
        with self.assertRaises(ValueError):
            drl.validate_requirement([])


if __name__ == "__main__":
    unittest.main(verbosity=2)
