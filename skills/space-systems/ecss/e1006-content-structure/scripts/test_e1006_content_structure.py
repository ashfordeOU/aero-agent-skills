#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §7.2 Technical Specification
content-structure assessment.

Exercises scripts/e1006_content_structure_logic.py (stdlib unittest,
offline). Contract: every mandatory section key must be present and appear
in the required order; each section must have a named owner; every
applicable-document reference must carry a document identifier; CM tagging
requires doc_number, issue, and revision; body section numbers must follow
hierarchical numeric format; annexes must carry single uppercase-letter
identifiers; a document marked restricted must declare its restriction
statement. The full_ts_structure_review aggregation returns compliant only
when all seven dimensions have empty violation lists.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1006_content_structure_logic as cs  # noqa: E402

COMPLETE_SECTION_KEYS = [
    "scope",
    "applicable_documents",
    "terms_and_definitions",
    "requirements",
    "verification",
]


class ValidateOrganisationTest(unittest.TestCase):
    def test_all_mandatory_sections_in_order_passes(self):
        self.assertEqual(cs.validate_organisation(COMPLETE_SECTION_KEYS), [])

    def test_extra_sections_between_mandatory_pass(self):
        keys = [
            "scope",
            "applicable_documents",
            "acronyms",
            "terms_and_definitions",
            "requirements",
            "icd_notes",
            "verification",
        ]
        self.assertEqual(cs.validate_organisation(keys), [])

    def test_missing_scope_flagged(self):
        keys = [k for k in COMPLETE_SECTION_KEYS if k != "scope"]
        violations = cs.validate_organisation(keys)
        issues = [v["issue"] for v in violations]
        self.assertIn("missing_mandatory_section", issues)
        sections = [v["section"] for v in violations if v["issue"] == "missing_mandatory_section"]
        self.assertIn("scope", sections)

    def test_missing_verification_flagged(self):
        keys = [k for k in COMPLETE_SECTION_KEYS if k != "verification"]
        violations = cs.validate_organisation(keys)
        sections = [v["section"] for v in violations if v["issue"] == "missing_mandatory_section"]
        self.assertIn("verification", sections)

    def test_missing_requirements_flagged(self):
        keys = [k for k in COMPLETE_SECTION_KEYS if k != "requirements"]
        violations = cs.validate_organisation(keys)
        sections = [v["section"] for v in violations if v["issue"] == "missing_mandatory_section"]
        self.assertIn("requirements", sections)

    def test_order_violation_flagged(self):
        keys = [
            "applicable_documents",
            "scope",
            "terms_and_definitions",
            "requirements",
            "verification",
        ]
        violations = cs.validate_organisation(keys)
        order_issues = [v for v in violations if v["issue"] == "section_order_violation"]
        self.assertTrue(
            len(order_issues) > 0,
            "expected an order violation when scope appears after applicable_documents",
        )

    def test_non_string_key_raises(self):
        with self.assertRaises(TypeError):
            cs.validate_organisation(["scope", 42, "requirements"])


class CheckResponsibilityTest(unittest.TestCase):
    def test_all_sections_with_owners_passes(self):
        sections = [
            {"key": "scope", "owner": "Systems Engineering"},
            {"key": "requirements", "owner": "Product Assurance"},
        ]
        self.assertEqual(cs.check_responsibility(sections), [])

    def test_section_with_none_owner_flagged(self):
        sections = [{"key": "scope", "owner": None}]
        violations = cs.check_responsibility(sections)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_section_owner")
        self.assertEqual(violations[0]["section"], "scope")

    def test_section_with_empty_string_owner_flagged(self):
        sections = [{"key": "verification", "owner": ""}]
        violations = cs.check_responsibility(sections)
        self.assertEqual(violations[0]["issue"], "missing_section_owner")

    def test_empty_sections_list_passes(self):
        self.assertEqual(cs.check_responsibility([]), [])


class CheckTechnicalReferencesTest(unittest.TestCase):
    def test_references_with_doc_ids_pass(self):
        refs = [
            {"title": "ECSS-E-ST-10C", "doc_id": "ECSS-E-ST-10C Rev.1"},
            {"title": "Project ICD", "doc_id": "PRJ-ICD-001"},
        ]
        self.assertEqual(cs.check_technical_references(refs), [])

    def test_reference_without_doc_id_flagged(self):
        refs = [{"title": "Some Standard", "doc_id": None}]
        violations = cs.check_technical_references(refs)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_reference_doc_id")
        self.assertEqual(violations[0]["title"], "Some Standard")

    def test_reference_with_missing_doc_id_key_flagged(self):
        refs = [{"title": "Another Doc"}]
        violations = cs.check_technical_references(refs)
        self.assertEqual(violations[0]["issue"], "missing_reference_doc_id")

    def test_empty_references_list_passes(self):
        self.assertEqual(cs.check_technical_references([]), [])


class CheckCmTaggingTest(unittest.TestCase):
    def test_complete_cm_tagging_passes(self):
        meta = {"doc_number": "PRJ-TS-001", "issue": "1", "revision": "A"}
        self.assertEqual(cs.check_cm_tagging(meta), [])

    def test_missing_doc_number_flagged(self):
        meta = {"issue": "1", "revision": "A"}
        violations = cs.check_cm_tagging(meta)
        fields = [v["field"] for v in violations]
        self.assertIn("doc_number", fields)

    def test_missing_issue_flagged(self):
        meta = {"doc_number": "PRJ-TS-001", "revision": "A"}
        violations = cs.check_cm_tagging(meta)
        fields = [v["field"] for v in violations]
        self.assertIn("issue", fields)

    def test_missing_revision_flagged(self):
        meta = {"doc_number": "PRJ-TS-001", "issue": "1"}
        violations = cs.check_cm_tagging(meta)
        fields = [v["field"] for v in violations]
        self.assertIn("revision", fields)

    def test_all_cm_fields_missing_flags_all_three(self):
        violations = cs.check_cm_tagging({})
        self.assertEqual(len(violations), 3)


class ValidateSectionNumberingTest(unittest.TestCase):
    def test_single_digit_numbers_pass(self):
        self.assertEqual(cs.validate_section_numbering(["1", "2", "3"]), [])

    def test_multi_level_numbers_pass(self):
        self.assertEqual(
            cs.validate_section_numbering(["1", "1.1", "1.2", "1.2.1", "2"]), []
        )

    def test_letter_annex_identifier_flagged(self):
        violations = cs.validate_section_numbering(["A"])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "invalid_section_number_format")
        self.assertEqual(violations[0]["number"], "A")

    def test_mixed_alpha_numeric_flagged(self):
        violations = cs.validate_section_numbering(["1A", "2.3b"])
        self.assertEqual(len(violations), 2)

    def test_non_string_raises(self):
        with self.assertRaises(ValueError):
            cs.validate_section_numbering([1, 2])

    def test_empty_list_passes(self):
        self.assertEqual(cs.validate_section_numbering([]), [])


class CheckSupplementaryInfoTest(unittest.TestCase):
    def test_valid_single_letter_annexes_pass(self):
        annexes = [
            {"key": "acronyms_annex", "letter": "A"},
            {"key": "data_tables", "letter": "B"},
        ]
        self.assertEqual(cs.check_supplementary_info(annexes), [])

    def test_numeric_annex_identifier_flagged(self):
        annexes = [{"key": "extra_info", "letter": "1"}]
        violations = cs.check_supplementary_info(annexes)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "invalid_annex_letter")

    def test_missing_annex_letter_flagged(self):
        annexes = [{"key": "notes", "letter": None}]
        violations = cs.check_supplementary_info(annexes)
        self.assertEqual(violations[0]["issue"], "invalid_annex_letter")

    def test_lowercase_letter_flagged(self):
        annexes = [{"key": "appendix", "letter": "a"}]
        violations = cs.check_supplementary_info(annexes)
        self.assertEqual(violations[0]["issue"], "invalid_annex_letter")

    def test_empty_annexes_list_passes(self):
        self.assertEqual(cs.check_supplementary_info([]), [])


class CheckRestrictionsTest(unittest.TestCase):
    def test_unrestricted_document_passes(self):
        meta = {"has_restriction": False}
        self.assertEqual(cs.check_restrictions(meta), [])

    def test_restricted_with_statement_passes(self):
        meta = {
            "has_restriction": True,
            "restriction_statement": "Distribution limited to ESA and prime contractor.",
        }
        self.assertEqual(cs.check_restrictions(meta), [])

    def test_restricted_without_statement_flagged(self):
        meta = {"has_restriction": True, "restriction_statement": None}
        violations = cs.check_restrictions(meta)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "undeclared_restriction")

    def test_restricted_with_empty_statement_flagged(self):
        meta = {"has_restriction": True, "restriction_statement": ""}
        violations = cs.check_restrictions(meta)
        self.assertEqual(violations[0]["issue"], "undeclared_restriction")


class FullTsStructureReviewTest(unittest.TestCase):
    def _compliant_ts(self):
        return {
            "section_keys": COMPLETE_SECTION_KEYS,
            "sections": [
                {"key": "scope", "owner": "Systems Engineering"},
                {"key": "applicable_documents", "owner": "Systems Engineering"},
                {"key": "terms_and_definitions", "owner": "Systems Engineering"},
                {"key": "requirements", "owner": "Product Assurance"},
                {"key": "verification", "owner": "AIV Team"},
            ],
            "technical_references": [
                {"title": "ECSS-E-ST-10C", "doc_id": "ECSS-E-ST-10C Rev.1"},
            ],
            "doc_meta": {
                "doc_number": "PRJ-TS-001",
                "issue": "1",
                "revision": "A",
                "has_restriction": False,
            },
            "section_numbers": ["1", "2", "3", "4", "5"],
            "annexes": [{"key": "acronyms", "letter": "A"}],
        }

    def test_fully_compliant_ts_passes(self):
        review = cs.full_ts_structure_review(self._compliant_ts())
        self.assertTrue(cs.is_ts_structure_compliant(review))
        for dimension, violations in review.items():
            self.assertEqual(violations, [], "unexpected violations in %r" % dimension)

    def test_missing_section_key_makes_noncompliant(self):
        ts = self._compliant_ts()
        ts["section_keys"] = [k for k in COMPLETE_SECTION_KEYS if k != "verification"]
        review = cs.full_ts_structure_review(ts)
        self.assertFalse(cs.is_ts_structure_compliant(review))
        self.assertTrue(len(review["organisation"]) > 0)

    def test_missing_cm_field_makes_noncompliant(self):
        ts = self._compliant_ts()
        ts["doc_meta"] = {"issue": "1", "revision": "A", "has_restriction": False}
        review = cs.full_ts_structure_review(ts)
        self.assertFalse(cs.is_ts_structure_compliant(review))
        self.assertTrue(len(review["cm_tagging"]) > 0)

    def test_restricted_without_statement_makes_noncompliant(self):
        ts = self._compliant_ts()
        ts["doc_meta"]["has_restriction"] = True
        ts["doc_meta"]["restriction_statement"] = None
        review = cs.full_ts_structure_review(ts)
        self.assertFalse(cs.is_ts_structure_compliant(review))
        self.assertTrue(len(review["restrictions"]) > 0)

    def test_review_with_all_dimensions_returns_seven_keys(self):
        review = cs.full_ts_structure_review(self._compliant_ts())
        self.assertEqual(
            set(review.keys()),
            {
                "organisation",
                "responsibility",
                "technical_references",
                "cm_tagging",
                "format",
                "supplementary_info",
                "restrictions",
            },
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
