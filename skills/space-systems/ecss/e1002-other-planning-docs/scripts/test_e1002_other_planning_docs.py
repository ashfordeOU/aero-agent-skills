#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.8.3 other
verification planning documents.

Exercises scripts/e1002_other_planning_docs_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a requirement's
verification method maps to an other-planning-document type (test ->
AIT plan interface, analysis -> analysis plan, inspection / review of
design -> none) and an unrecognized method raises; the required
document set for a programme is the set of document types implied by
its requirements' methods; a required document is checked for its
minimum content fields and for linkage of every requirement id
assigned to its method, and a missing document is itself a finding;
each document's status must be one of draft / in_review / approved,
and the overall roll-up is the least-complete status present (or
approved when nothing is required); the review is compliant only when
the roll-up is approved and every required document has no issues.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_other_planning_docs_logic as opd  # noqa: E402


class OtherPlanningDocForMethodTest(unittest.TestCase):
    def test_test_method_maps_to_ait_plan_interface(self):
        self.assertEqual(
            opd.other_planning_doc_for_method("test"), "ait_plan_interface"
        )

    def test_analysis_method_maps_to_analysis_plan(self):
        self.assertEqual(
            opd.other_planning_doc_for_method("analysis"), "analysis_plan"
        )

    def test_inspection_method_has_no_other_document(self):
        self.assertIsNone(opd.other_planning_doc_for_method("inspection"))

    def test_review_of_design_method_has_no_other_document(self):
        self.assertIsNone(opd.other_planning_doc_for_method("review_of_design"))

    def test_unrecognized_method_raises(self):
        with self.assertRaises(ValueError):
            opd.other_planning_doc_for_method("telepathy")


class RequiredOtherPlanningDocumentsTest(unittest.TestCase):
    def test_no_requirements_needs_nothing(self):
        self.assertEqual(opd.required_other_planning_documents([]), ())

    def test_test_only_requires_ait_plan_interface(self):
        requirements = [{"id": "R1", "verification_method": "test"}]
        self.assertEqual(
            opd.required_other_planning_documents(requirements),
            ("ait_plan_interface",),
        )

    def test_analysis_only_requires_analysis_plan(self):
        requirements = [{"id": "R1", "verification_method": "analysis"}]
        self.assertEqual(
            opd.required_other_planning_documents(requirements), ("analysis_plan",)
        )

    def test_mixed_methods_require_both_sorted(self):
        requirements = [
            {"id": "R1", "verification_method": "analysis"},
            {"id": "R2", "verification_method": "test"},
        ]
        self.assertEqual(
            opd.required_other_planning_documents(requirements),
            ("ait_plan_interface", "analysis_plan"),
        )

    def test_inspection_and_review_of_design_require_nothing(self):
        requirements = [
            {"id": "R1", "verification_method": "inspection"},
            {"id": "R2", "verification_method": "review_of_design"},
        ]
        self.assertEqual(opd.required_other_planning_documents(requirements), ())

    def test_missing_method_key_raises(self):
        with self.assertRaises(ValueError):
            opd.required_other_planning_documents([{"id": "R1"}])

    def test_unrecognized_method_raises(self):
        with self.assertRaises(ValueError):
            opd.required_other_planning_documents(
                [{"id": "R1", "verification_method": "divination"}]
            )


class CheckDocumentCompletenessTest(unittest.TestCase):
    def test_complete_ait_plan_interface_has_no_issues(self):
        document = {
            "ait_plan_reference": "AIT-PLAN-001",
            "linked_requirement_ids": ["R1"],
            "interface_points": ["integration_step_3"],
        }
        self.assertEqual(opd.check_document_completeness("ait_plan_interface", document), [])

    def test_incomplete_analysis_plan_flags_each_missing_field(self):
        issues = opd.check_document_completeness("analysis_plan", {})
        fields = {issue["field"] for issue in issues}
        self.assertEqual(fields, {"analysis_methods", "linked_requirement_ids", "tools_or_models"})

    def test_unrecognized_doc_type_raises(self):
        with self.assertRaises(ValueError):
            opd.check_document_completeness("mystery_doc", {})


class CheckRequirementLinkageTest(unittest.TestCase):
    def test_fully_linked_has_no_issues(self):
        requirements = [
            {"id": "R1", "verification_method": "test"},
            {"id": "R2", "verification_method": "test"},
        ]
        document = {"linked_requirement_ids": ["R1", "R2"]}
        self.assertEqual(
            opd.check_requirement_linkage("ait_plan_interface", document, requirements), []
        )

    def test_missing_linkage_is_flagged(self):
        requirements = [
            {"id": "R1", "verification_method": "analysis"},
            {"id": "R2", "verification_method": "analysis"},
        ]
        document = {"linked_requirement_ids": ["R1"]}
        issues = opd.check_requirement_linkage("analysis_plan", document, requirements)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["missing_requirement_ids"], ["R2"])

    def test_ignores_requirements_of_other_methods(self):
        requirements = [
            {"id": "R1", "verification_method": "analysis"},
            {"id": "R2", "verification_method": "inspection"},
        ]
        document = {"linked_requirement_ids": ["R1"]}
        self.assertEqual(
            opd.check_requirement_linkage("analysis_plan", document, requirements), []
        )

    def test_unrecognized_doc_type_raises(self):
        with self.assertRaises(ValueError):
            opd.check_requirement_linkage("mystery_doc", {}, [])


class ValidateDocumentStatusTest(unittest.TestCase):
    def test_draft_rank_is_lowest(self):
        self.assertEqual(opd.validate_document_status("draft"), 0)

    def test_approved_rank_is_highest(self):
        self.assertEqual(
            opd.validate_document_status("approved"),
            len(opd.DOCUMENT_STATUSES) - 1,
        )

    def test_unrecognized_status_raises(self):
        with self.assertRaises(ValueError):
            opd.validate_document_status("finalized")


class RollUpOverallStatusTest(unittest.TestCase):
    def test_empty_is_approved(self):
        self.assertEqual(opd.roll_up_overall_status([]), "approved")

    def test_all_approved_is_approved(self):
        self.assertEqual(opd.roll_up_overall_status(["approved", "approved"]), "approved")

    def test_any_draft_dominates(self):
        self.assertEqual(
            opd.roll_up_overall_status(["approved", "draft", "in_review"]), "draft"
        )

    def test_in_review_beats_approved_without_draft(self):
        self.assertEqual(
            opd.roll_up_overall_status(["approved", "in_review"]), "in_review"
        )

    def test_unrecognized_status_raises(self):
        with self.assertRaises(ValueError):
            opd.roll_up_overall_status(["approved", "pending"])


class ReviewOtherPlanningDocumentsTest(unittest.TestCase):
    def test_fully_compliant_review(self):
        requirements = [
            {"id": "R1", "verification_method": "test"},
            {"id": "R2", "verification_method": "analysis"},
        ]
        documents = {
            "ait_plan_interface": {
                "ait_plan_reference": "AIT-PLAN-001",
                "linked_requirement_ids": ["R1"],
                "interface_points": ["integration_step_3"],
                "status": "approved",
            },
            "analysis_plan": {
                "analysis_methods": ["structural_worst_case"],
                "linked_requirement_ids": ["R2"],
                "tools_or_models": ["fem_model_v3"],
                "status": "approved",
            },
        }
        review = opd.review_other_planning_documents(requirements, documents)
        self.assertEqual(
            review["required_documents"], ("ait_plan_interface", "analysis_plan")
        )
        self.assertEqual(review["overall_status"], "approved")
        self.assertTrue(review["is_compliant"])
        self.assertTrue(opd.is_other_planning_docs_compliant(review))

    def test_missing_required_document_is_flagged_and_not_compliant(self):
        requirements = [{"id": "R1", "verification_method": "test"}]
        review = opd.review_other_planning_documents(requirements, {})
        entry = review["per_document"]["ait_plan_interface"]
        self.assertEqual(entry["issues"][0]["issue"], "missing_required_document")
        self.assertIsNone(entry["status"])
        self.assertFalse(review["is_compliant"])

    def test_incomplete_document_is_not_compliant_even_if_approved(self):
        requirements = [{"id": "R1", "verification_method": "analysis"}]
        documents = {
            "analysis_plan": {
                "analysis_methods": ["structural_worst_case"],
                "linked_requirement_ids": [],
                "tools_or_models": ["fem_model_v3"],
                "status": "approved",
            }
        }
        review = opd.review_other_planning_documents(requirements, documents)
        self.assertFalse(review["is_compliant"])
        entry = review["per_document"]["analysis_plan"]
        issue_types = {issue["issue"] for issue in entry["issues"]}
        self.assertIn("missing_field", issue_types)
        self.assertIn("requirement_not_linked", issue_types)

    def test_no_requirements_is_trivially_compliant(self):
        review = opd.review_other_planning_documents([], {})
        self.assertEqual(review["required_documents"], ())
        self.assertEqual(review["overall_status"], "approved")
        self.assertTrue(review["is_compliant"])

    def test_missing_document_pulls_overall_status_to_draft(self):
        requirements = [
            {"id": "R1", "verification_method": "test"},
            {"id": "R2", "verification_method": "analysis"},
        ]
        documents = {
            "analysis_plan": {
                "analysis_methods": ["structural_worst_case"],
                "linked_requirement_ids": ["R2"],
                "tools_or_models": ["fem_model_v3"],
                "status": "approved",
            }
        }
        review = opd.review_other_planning_documents(requirements, documents)
        self.assertEqual(review["overall_status"], "draft")
        self.assertFalse(review["is_compliant"])

    def test_invalid_document_status_raises(self):
        requirements = [{"id": "R1", "verification_method": "test"}]
        documents = {
            "ait_plan_interface": {
                "ait_plan_reference": "AIT-PLAN-001",
                "linked_requirement_ids": ["R1"],
                "interface_points": ["integration_step_3"],
                "status": "finalized",
            }
        }
        with self.assertRaises(ValueError):
            opd.review_other_planning_documents(requirements, documents)

    def test_malformed_requirement_raises(self):
        with self.assertRaises(ValueError):
            opd.review_other_planning_documents([{"id": "R1"}], {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
