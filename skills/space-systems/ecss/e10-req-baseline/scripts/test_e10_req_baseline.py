#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.2.3.9 requirements
baseline management.

Exercises scripts/e10_req_baseline_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a requirement
status categorizes as ready only when approved, and an unrecognized
status raises; a requirement's readiness violations flag a
non-approved status, missing text, and a missing verification method
independently; duplicate requirement identifiers within a CI's set are
detected; a milestone baseline review raises on an unrecognized
milestone, flags an empty requirement set, and aggregates duplicate
and per-requirement findings; a baseline is established only when the
review has zero violations and a non-empty baseline_id is given,
otherwise it raises; a proposed baseline change raises on an
unrecognized change type and is flagged without an approved change
request; change control against a baseline raises unless the baseline
is established, and the aggregate review is controlled only when every
change is authorized.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_req_baseline_logic as rb  # noqa: E402


def approved_requirement(requirement_id="REQ-1"):
    return {
        "requirement_id": requirement_id,
        "status": "approved",
        "text": "The CI shall maintain thermal margin.",
        "verification_method": "analysis",
    }


class ClassifyRequirementStatusTest(unittest.TestCase):
    def test_approved_is_ready(self):
        self.assertEqual(rb.classify_requirement_status("approved"), "ready")

    def test_draft_is_not_ready(self):
        self.assertEqual(rb.classify_requirement_status("draft"), "not_ready")

    def test_in_review_is_not_ready(self):
        self.assertEqual(rb.classify_requirement_status("in_review"), "not_ready")

    def test_withdrawn_is_not_ready(self):
        self.assertEqual(rb.classify_requirement_status("withdrawn"), "not_ready")

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            rb.classify_requirement_status("proposed")


class RequirementReadinessViolationsTest(unittest.TestCase):
    def test_complete_approved_requirement_has_no_violations(self):
        self.assertEqual(
            rb.requirement_readiness_violations(approved_requirement()), []
        )

    def test_draft_requirement_flagged_not_approved(self):
        requirement = approved_requirement()
        requirement["status"] = "draft"
        violations = rb.requirement_readiness_violations(requirement)
        self.assertEqual(
            violations,
            [
                {
                    "issue": "requirement_not_approved",
                    "requirement_id": "REQ-1",
                    "status": "draft",
                }
            ],
        )

    def test_missing_text_flagged(self):
        requirement = approved_requirement()
        requirement["text"] = "   "
        violations = rb.requirement_readiness_violations(requirement)
        self.assertIn(
            {"issue": "missing_requirement_text", "requirement_id": "REQ-1"},
            violations,
        )

    def test_missing_verification_method_flagged(self):
        requirement = approved_requirement()
        requirement["verification_method"] = None
        violations = rb.requirement_readiness_violations(requirement)
        self.assertIn(
            {"issue": "missing_verification_method", "requirement_id": "REQ-1"},
            violations,
        )

    def test_multiple_gaps_all_reported(self):
        requirement = {"requirement_id": "REQ-2", "status": "in_review"}
        violations = rb.requirement_readiness_violations(requirement)
        self.assertEqual(len(violations), 3)


class DuplicateRequirementIdsTest(unittest.TestCase):
    def test_no_duplicates(self):
        requirements = [approved_requirement("REQ-1"), approved_requirement("REQ-2")]
        self.assertEqual(rb.duplicate_requirement_ids(requirements), [])

    def test_detects_duplicate(self):
        requirements = [
            approved_requirement("REQ-1"),
            approved_requirement("REQ-2"),
            approved_requirement("REQ-1"),
        ]
        self.assertEqual(rb.duplicate_requirement_ids(requirements), ["REQ-1"])


class MilestoneBaselineReviewTest(unittest.TestCase):
    def test_unknown_milestone_raises(self):
        with self.assertRaises(ValueError):
            rb.milestone_baseline_review("CI-1", [approved_requirement()], "KO")

    def test_empty_requirements_flagged(self):
        violations = rb.milestone_baseline_review("CI-1", [], "PDR")
        self.assertEqual(
            violations, [{"issue": "no_requirements_for_baseline", "ci_id": "CI-1"}]
        )

    def test_all_approved_requirements_no_violations(self):
        requirements = [approved_requirement("REQ-1"), approved_requirement("REQ-2")]
        self.assertEqual(rb.milestone_baseline_review("CI-1", requirements, "PDR"), [])

    def test_duplicate_and_unapproved_both_flagged(self):
        draft = approved_requirement("REQ-1")
        draft["status"] = "draft"
        requirements = [draft, approved_requirement("REQ-1")]
        violations = rb.milestone_baseline_review("CI-1", requirements, "CDR")
        issues = {v["issue"] for v in violations}
        self.assertIn("duplicate_requirement_id", issues)
        self.assertIn("requirement_not_approved", issues)


class EstablishBaselineTest(unittest.TestCase):
    def test_establishes_when_eligible(self):
        requirements = [approved_requirement("REQ-1"), approved_requirement("REQ-2")]
        baseline = rb.establish_baseline("CI-1", requirements, "PDR", "BL-CI1-PDR")
        self.assertEqual(baseline["status"], "established")
        self.assertEqual(baseline["requirement_ids"], ["REQ-1", "REQ-2"])

    def test_raises_when_ineligible(self):
        draft = approved_requirement("REQ-1")
        draft["status"] = "draft"
        with self.assertRaises(ValueError):
            rb.establish_baseline("CI-1", [draft], "PDR", "BL-CI1-PDR")

    def test_raises_on_empty_baseline_id(self):
        with self.assertRaises(ValueError):
            rb.establish_baseline("CI-1", [approved_requirement()], "PDR", "")


class BaselineChangeViolationsTest(unittest.TestCase):
    def test_unknown_change_type_raises(self):
        change = {
            "requirement_id": "REQ-1",
            "change_type": "rename",
            "has_approved_change_request": True,
        }
        with self.assertRaises(ValueError):
            rb.baseline_change_violations(change)

    def test_change_without_cr_flagged(self):
        change = {
            "requirement_id": "REQ-1",
            "change_type": "modify",
            "has_approved_change_request": False,
        }
        violations = rb.baseline_change_violations(change)
        self.assertEqual(
            violations,
            [
                {
                    "issue": "baseline_change_without_approved_cr",
                    "requirement_id": "REQ-1",
                    "change_type": "modify",
                }
            ],
        )

    def test_change_with_cr_not_flagged(self):
        change = {
            "requirement_id": "REQ-1",
            "change_type": "delete",
            "has_approved_change_request": True,
        }
        self.assertEqual(rb.baseline_change_violations(change), [])


class BaselineControlReviewTest(unittest.TestCase):
    def setUp(self):
        self.baseline = {"baseline_id": "BL-CI1-PDR", "status": "established"}

    def test_raises_when_baseline_not_established(self):
        draft_baseline = {"baseline_id": "BL-CI1-PDR", "status": "draft"}
        with self.assertRaises(ValueError):
            rb.baseline_control_review(draft_baseline, [])

    def test_aggregates_violations_across_changes(self):
        changes = [
            {
                "requirement_id": "REQ-1",
                "change_type": "modify",
                "has_approved_change_request": False,
            },
            {
                "requirement_id": "REQ-2",
                "change_type": "add",
                "has_approved_change_request": False,
            },
        ]
        violations = rb.baseline_control_review(self.baseline, changes)
        self.assertEqual(len(violations), 2)

    def test_no_violations_when_all_changes_approved(self):
        changes = [
            {
                "requirement_id": "REQ-1",
                "change_type": "modify",
                "has_approved_change_request": True,
            }
        ]
        self.assertEqual(rb.baseline_control_review(self.baseline, changes), [])


class IsBaselineChangeControlledTest(unittest.TestCase):
    def test_true_when_empty(self):
        self.assertTrue(rb.is_baseline_change_controlled([]))

    def test_false_when_violations_present(self):
        self.assertFalse(
            rb.is_baseline_change_controlled(
                [{"issue": "baseline_change_without_approved_cr"}]
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
