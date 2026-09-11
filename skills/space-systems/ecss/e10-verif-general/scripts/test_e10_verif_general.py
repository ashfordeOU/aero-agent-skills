#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.5.1 system-level
product verification management.

Exercises scripts/e10_verif_general_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a verification
method and a method status each validate against a fixed vocabulary
and raise on an unrecognized value; a requirement's assigned methods
must be a non-empty, duplicate-free subset of that vocabulary; a
requirement without a System Engineering Plan verification policy
reference is flagged; an assigned method with no recorded status (or a
status recorded for a method never assigned) is flagged; a closed
method without supporting evidence is flagged; the aggregate status
across a requirement's methods is "failed" if any method failed,
otherwise "closed"/"closed_with_deviation" only once every method has
closed, else "in_progress" or "open"; and a requirement counts as
verified only when it has no violations and its aggregate status is a
closed one.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_verif_general_logic as vg  # noqa: E402


class ValidateVerificationMethodTest(unittest.TestCase):
    def test_test_is_valid(self):
        self.assertEqual(vg.validate_verification_method("test"), "test")

    def test_analysis_is_valid(self):
        self.assertEqual(vg.validate_verification_method("analysis"), "analysis")

    def test_inspection_is_valid(self):
        self.assertEqual(vg.validate_verification_method("inspection"), "inspection")

    def test_review_of_design_is_valid(self):
        self.assertEqual(
            vg.validate_verification_method("review_of_design"), "review_of_design"
        )

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            vg.validate_verification_method("wishful_thinking")


class ValidateMethodStatusTest(unittest.TestCase):
    def test_known_statuses_pass(self):
        for status in vg.METHOD_STATUSES:
            self.assertEqual(vg.validate_method_status(status), status)

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            vg.validate_method_status("categorized_pending")


class AssignVerificationMethodsTest(unittest.TestCase):
    def test_assigns_normalized_tuple(self):
        methods = vg.assign_verification_methods("REQ-1", ["test", "analysis"])
        self.assertEqual(methods, ("test", "analysis"))

    def test_missing_requirement_id_raises(self):
        with self.assertRaises(ValueError):
            vg.assign_verification_methods("", ["test"])

    def test_empty_methods_raises(self):
        with self.assertRaises(ValueError):
            vg.assign_verification_methods("REQ-1", [])

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            vg.assign_verification_methods("REQ-1", ["telepathy"])

    def test_duplicate_method_raises(self):
        with self.assertRaises(ValueError):
            vg.assign_verification_methods("REQ-1", ["test", "test"])


class VerificationPolicyLinkageViolationsTest(unittest.TestCase):
    def test_missing_ref_flagged(self):
        violations = vg.verification_policy_linkage_violations("REQ-1", None)
        self.assertEqual(
            violations,
            [{"issue": "missing_sep_verification_policy_linkage", "requirement": "REQ-1"}],
        )

    def test_present_ref_no_violation(self):
        self.assertEqual(
            vg.verification_policy_linkage_violations("REQ-1", "SEP-VER-POLICY-3"), []
        )


class MethodAssignmentViolationsTest(unittest.TestCase):
    def test_assigned_method_missing_status_flagged(self):
        violations = vg.method_assignment_violations("REQ-1", ("test",), {})
        self.assertEqual(
            violations,
            [{"issue": "assigned_method_missing_status", "requirement": "REQ-1", "method": "test"}],
        )

    def test_status_for_unassigned_method_flagged(self):
        violations = vg.method_assignment_violations(
            "REQ-1", ("test",), {"test": "closed", "analysis": "open"}
        )
        self.assertEqual(
            violations,
            [{"issue": "status_for_unassigned_method", "requirement": "REQ-1", "method": "analysis"}],
        )

    def test_fully_tracked_no_violation(self):
        violations = vg.method_assignment_violations(
            "REQ-1", ("test", "analysis"), {"test": "closed", "analysis": "open"}
        )
        self.assertEqual(violations, [])


class ClosureEvidenceViolationsTest(unittest.TestCase):
    def test_closed_with_evidence_no_violation(self):
        violations = vg.closure_evidence_violations(
            "REQ-1", {"test": "closed"}, {"test": "TR-004"}
        )
        self.assertEqual(violations, [])

    def test_closed_without_evidence_flagged(self):
        violations = vg.closure_evidence_violations(
            "REQ-1", {"test": "closed"}, {}
        )
        self.assertEqual(
            violations,
            [{"issue": "closed_method_missing_evidence", "requirement": "REQ-1", "method": "test"}],
        )

    def test_open_without_evidence_not_flagged(self):
        violations = vg.closure_evidence_violations(
            "REQ-1", {"test": "open"}, {}
        )
        self.assertEqual(violations, [])

    def test_closed_with_deviation_needs_evidence_too(self):
        violations = vg.closure_evidence_violations(
            "REQ-1", {"test": "closed_with_deviation"}, {}
        )
        self.assertEqual(len(violations), 1)

    def test_unrecognized_status_raises(self):
        with self.assertRaises(ValueError):
            vg.closure_evidence_violations("REQ-1", {"test": "pending_review"}, {})


class RequirementVerificationStatusTest(unittest.TestCase):
    def test_empty_map_raises(self):
        with self.assertRaises(ValueError):
            vg.requirement_verification_status({})

    def test_all_closed_is_closed(self):
        status = vg.requirement_verification_status(
            {"test": "closed", "analysis": "closed"}
        )
        self.assertEqual(status, "closed")

    def test_any_deviation_is_closed_with_deviation(self):
        status = vg.requirement_verification_status(
            {"test": "closed", "analysis": "closed_with_deviation"}
        )
        self.assertEqual(status, "closed_with_deviation")

    def test_any_failed_wins_over_closed(self):
        status = vg.requirement_verification_status(
            {"test": "closed", "analysis": "failed"}
        )
        self.assertEqual(status, "failed")

    def test_in_progress_beats_open_when_mixed(self):
        status = vg.requirement_verification_status(
            {"test": "open", "analysis": "in_progress"}
        )
        self.assertEqual(status, "in_progress")

    def test_all_open_is_open(self):
        status = vg.requirement_verification_status({"test": "open"})
        self.assertEqual(status, "open")

    def test_unrecognized_status_raises(self):
        with self.assertRaises(ValueError):
            vg.requirement_verification_status({"test": "vibes"})


class VerificationReviewTest(unittest.TestCase):
    def test_fully_compliant_review_is_verified(self):
        requirement = {
            "requirement_id": "REQ-100",
            "methods": ["test", "analysis"],
            "method_status": {"test": "closed", "analysis": "closed_with_deviation"},
            "evidence": {"test": "TR-100", "analysis": "AR-100"},
            "sep_policy_ref": "SEP-VER-POLICY-3",
        }
        review = vg.verification_review(requirement)
        self.assertEqual(review["violations"], [])
        self.assertEqual(review["status"], "closed_with_deviation")
        self.assertTrue(vg.is_requirement_verified(review))

    def test_missing_policy_linkage_still_reports_status(self):
        requirement = {
            "requirement_id": "REQ-101",
            "methods": ["inspection"],
            "method_status": {"inspection": "closed"},
            "evidence": {"inspection": "IR-101"},
            "sep_policy_ref": None,
        }
        review = vg.verification_review(requirement)
        self.assertEqual(len(review["violations"]), 1)
        self.assertEqual(
            review["violations"][0]["issue"], "missing_sep_verification_policy_linkage"
        )
        self.assertFalse(vg.is_requirement_verified(review))

    def test_missing_status_leaves_status_none_and_not_verified(self):
        requirement = {
            "requirement_id": "REQ-102",
            "methods": ["test", "analysis"],
            "method_status": {"test": "closed"},
            "evidence": {"test": "TR-102"},
            "sep_policy_ref": "SEP-VER-POLICY-3",
        }
        review = vg.verification_review(requirement)
        self.assertIsNone(review["status"])
        issues = {v["issue"] for v in review["violations"]}
        self.assertIn("assigned_method_missing_status", issues)
        self.assertFalse(vg.is_requirement_verified(review))

    def test_failed_method_is_not_verified(self):
        requirement = {
            "requirement_id": "REQ-103",
            "methods": ["review_of_design"],
            "method_status": {"review_of_design": "failed"},
            "evidence": {},
            "sep_policy_ref": "SEP-VER-POLICY-3",
        }
        review = vg.verification_review(requirement)
        self.assertEqual(review["status"], "failed")
        self.assertFalse(vg.is_requirement_verified(review))

    def test_review_raises_on_empty_methods(self):
        requirement = {
            "requirement_id": "REQ-104",
            "methods": [],
            "method_status": {},
            "evidence": {},
            "sep_policy_ref": "SEP-VER-POLICY-3",
        }
        with self.assertRaises(ValueError):
            vg.verification_review(requirement)


if __name__ == "__main__":
    unittest.main(verbosity=2)
