#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §4 TS purpose, chain position,
and content model.

Exercises scripts/e1006_purpose_logic.py (stdlib unittest, offline).
Contract: categorize_ts_section returns 'general_part' for scope/
applicability/normative_references/terms_definitions/product_definition
and 'requirements_part' for technical_requirements/
verification_requirements/interface_requirements; unknown section types
raise ValueError; ts_missing_required_sections returns an empty list
when all required sections are present and a sorted list of absent
names otherwise; determine_chain_position returns the correct ts_action
for supplier/customer/both and raises ValueError for an unknown role;
assess_ts_structure raises ValueError for an unknown section type, flags
missing required sections, and returns the chain_position when a role is
given; is_ts_complete returns True only when both missing-sections and
section-findings lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1006_purpose_logic as ts  # noqa: E402


class CategorizeTsSectionTest(unittest.TestCase):
    def test_scope_is_general_part(self):
        self.assertEqual(ts.categorize_ts_section("scope"), "general_part")

    def test_applicability_is_general_part(self):
        self.assertEqual(ts.categorize_ts_section("applicability"), "general_part")

    def test_normative_references_is_general_part(self):
        self.assertEqual(ts.categorize_ts_section("normative_references"), "general_part")

    def test_terms_definitions_is_general_part(self):
        self.assertEqual(ts.categorize_ts_section("terms_definitions"), "general_part")

    def test_product_definition_is_general_part(self):
        self.assertEqual(ts.categorize_ts_section("product_definition"), "general_part")

    def test_technical_requirements_is_requirements_part(self):
        self.assertEqual(ts.categorize_ts_section("technical_requirements"), "requirements_part")

    def test_verification_requirements_is_requirements_part(self):
        self.assertEqual(ts.categorize_ts_section("verification_requirements"), "requirements_part")

    def test_interface_requirements_is_requirements_part(self):
        self.assertEqual(ts.categorize_ts_section("interface_requirements"), "requirements_part")

    def test_design_requirements_is_requirements_part(self):
        self.assertEqual(ts.categorize_ts_section("design_requirements"), "requirements_part")

    def test_unknown_section_raises(self):
        with self.assertRaises(ValueError):
            ts.categorize_ts_section("marketing_brochure")

    def test_another_unknown_section_raises(self):
        with self.assertRaises(ValueError):
            ts.categorize_ts_section("executive_summary")


class TsMissingRequiredSectionsTest(unittest.TestCase):
    def test_all_required_present_returns_empty(self):
        all_sections = [
            "scope", "applicability", "normative_references",
            "terms_definitions", "technical_requirements",
            "verification_requirements",
        ]
        self.assertEqual(ts.ts_missing_required_sections(all_sections), [])

    def test_missing_sections_returned_sorted(self):
        missing = ts.ts_missing_required_sections(["scope"])
        self.assertIn("applicability", missing)
        self.assertIn("technical_requirements", missing)
        self.assertEqual(missing, sorted(missing))

    def test_empty_input_returns_all_required(self):
        missing = ts.ts_missing_required_sections([])
        all_required = ts.GENERAL_PART_REQUIRED | ts.REQUIREMENTS_PART_REQUIRED
        self.assertEqual(frozenset(missing), all_required)

    def test_optional_section_not_listed_as_missing(self):
        all_required = [
            "scope", "applicability", "normative_references",
            "terms_definitions", "technical_requirements",
            "verification_requirements",
        ]
        missing = ts.ts_missing_required_sections(all_required)
        self.assertNotIn("product_definition", missing)
        self.assertNotIn("interface_requirements", missing)

    def test_only_requirements_part_missing(self):
        general_only = [
            "scope", "applicability", "normative_references", "terms_definitions"
        ]
        missing = ts.ts_missing_required_sections(general_only)
        self.assertIn("technical_requirements", missing)
        self.assertIn("verification_requirements", missing)
        self.assertNotIn("scope", missing)


class DetermineChainPositionTest(unittest.TestCase):
    def test_supplier_issues_ts(self):
        pos = ts.determine_chain_position("supplier")
        self.assertEqual(pos["ts_action"], "issues")
        self.assertEqual(pos["role"], "supplier")

    def test_customer_receives_and_reviews_ts(self):
        pos = ts.determine_chain_position("customer")
        self.assertEqual(pos["ts_action"], "receives_and_reviews")
        self.assertEqual(pos["role"], "customer")

    def test_both_issues_and_receives(self):
        pos = ts.determine_chain_position("both")
        self.assertEqual(pos["ts_action"], "issues_and_receives")
        self.assertEqual(pos["role"], "both")

    def test_all_roles_have_description(self):
        for role in ("supplier", "customer", "both"):
            pos = ts.determine_chain_position(role)
            self.assertIn("description", pos)
            self.assertTrue(len(pos["description"]) > 0)

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            ts.determine_chain_position("observer")

    def test_result_is_independent_copy(self):
        pos = ts.determine_chain_position("supplier")
        pos["role"] = "mutated"
        pos2 = ts.determine_chain_position("supplier")
        self.assertEqual(pos2["role"], "supplier")


class AssessTsStructureTest(unittest.TestCase):
    def _complete_ts(self):
        return {
            "ts_id": "TS-001",
            "sections_present": [
                "scope", "applicability", "normative_references",
                "terms_definitions", "technical_requirements",
                "verification_requirements",
            ],
            "chain_role": "supplier",
        }

    def test_complete_ts_has_no_missing_sections(self):
        assessment = ts.assess_ts_structure(self._complete_ts())
        self.assertEqual(assessment["missing_required_sections"], [])

    def test_complete_ts_has_no_findings(self):
        assessment = ts.assess_ts_structure(self._complete_ts())
        self.assertEqual(assessment["section_findings"], [])

    def test_incomplete_ts_lists_missing_sections(self):
        doc = {
            "ts_id": "TS-002",
            "sections_present": ["scope"],
            "chain_role": None,
        }
        assessment = ts.assess_ts_structure(doc)
        self.assertIn("technical_requirements", assessment["missing_required_sections"])
        self.assertTrue(len(assessment["section_findings"]) > 0)

    def test_incomplete_ts_findings_name_the_missing_sections(self):
        doc = {
            "ts_id": "TS-002",
            "sections_present": ["scope"],
            "chain_role": None,
        }
        assessment = ts.assess_ts_structure(doc)
        finding = assessment["section_findings"][0]
        self.assertEqual(finding["issue"], "missing_required_sections")
        self.assertIn("technical_requirements", finding["missing"])

    def test_unknown_section_type_raises(self):
        doc = {
            "ts_id": "TS-003",
            "sections_present": ["scope", "executive_summary"],
            "chain_role": None,
        }
        with self.assertRaises(ValueError):
            ts.assess_ts_structure(doc)

    def test_chain_position_returned_when_role_given(self):
        assessment = ts.assess_ts_structure(self._complete_ts())
        self.assertIsNotNone(assessment["chain_position"])
        self.assertEqual(assessment["chain_position"]["role"], "supplier")

    def test_chain_position_none_when_role_is_none(self):
        doc = self._complete_ts()
        doc["chain_role"] = None
        assessment = ts.assess_ts_structure(doc)
        self.assertIsNone(assessment["chain_position"])

    def test_ts_id_preserved_in_assessment(self):
        assessment = ts.assess_ts_structure(self._complete_ts())
        self.assertEqual(assessment["ts_id"], "TS-001")


class IsTsCompleteTest(unittest.TestCase):
    def test_complete_assessment_returns_true(self):
        assessment = {"missing_required_sections": [], "section_findings": []}
        self.assertTrue(ts.is_ts_complete(assessment))

    def test_missing_sections_returns_false(self):
        assessment = {
            "missing_required_sections": ["scope"],
            "section_findings": [{"issue": "missing_required_sections"}],
        }
        self.assertFalse(ts.is_ts_complete(assessment))

    def test_section_findings_only_returns_false(self):
        assessment = {
            "missing_required_sections": [],
            "section_findings": [{"issue": "some_finding"}],
        }
        self.assertFalse(ts.is_ts_complete(assessment))

    def test_end_to_end_complete_ts_is_true(self):
        doc = {
            "ts_id": "TS-FULL",
            "sections_present": [
                "scope", "applicability", "normative_references",
                "terms_definitions", "technical_requirements",
                "verification_requirements", "interface_requirements",
            ],
            "chain_role": "both",
        }
        assessment = ts.assess_ts_structure(doc)
        self.assertTrue(ts.is_ts_complete(assessment))

    def test_end_to_end_incomplete_ts_is_false(self):
        doc = {
            "ts_id": "TS-PARTIAL",
            "sections_present": ["scope", "applicability"],
            "chain_role": "customer",
        }
        assessment = ts.assess_ts_structure(doc)
        self.assertFalse(ts.is_ts_complete(assessment))


if __name__ == "__main__":
    unittest.main(verbosity=2)
