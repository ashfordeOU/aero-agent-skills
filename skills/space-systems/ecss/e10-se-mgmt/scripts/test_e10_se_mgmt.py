#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.6.1 SE management
assessment.

Exercises scripts/e10_se_mgmt_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - an activity kind
categorizes into one of the recognized SE activity kinds and an
unrecognized kind raises; an activity with no owner is flagged as
unassigned and an unrecognized owner role raises; an activity's
required-interface set is checked against its recorded interfaces and
an unrecognized counterpart raises; a blocked activity without a
recorded reason is flagged, a completed activity depending on a
not-yet-complete activity is flagged, and an unrecognized status or
dangling dependency id raises; the aggregated per-activity review and
the program-wide roll-up are compliant only when every category is
empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_se_mgmt_logic as se  # noqa: E402


def make_activity(**overrides):
    activity = {
        "id": "act-1",
        "kind": "analysis",
        "owner": "se_manager",
        "interfaces": [],
        "status": "planned",
        "blocking_reason": None,
        "depends_on": [],
    }
    activity.update(overrides)
    return activity


class ClassifyActivityKindTest(unittest.TestCase):
    def test_technical_management_recognized(self):
        self.assertEqual(
            se.classify_activity_kind("technical_management"), "technical_management"
        )

    def test_verification_recognized(self):
        self.assertEqual(se.classify_activity_kind("verification"), "verification")

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            se.classify_activity_kind("mystery_activity")


class ResponsibilityFindingsTest(unittest.TestCase):
    def test_assigned_owner_no_finding(self):
        activity = make_activity(owner="lead_engineer")
        self.assertEqual(se.responsibility_findings(activity), [])

    def test_missing_owner_flagged(self):
        activity = make_activity(owner=None)
        findings = se.responsibility_findings(activity)
        self.assertEqual(
            findings, [{"issue": "unassigned_responsibility", "activity": "act-1"}]
        )

    def test_empty_string_owner_flagged(self):
        activity = make_activity(owner="")
        findings = se.responsibility_findings(activity)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "unassigned_responsibility")

    def test_unrecognized_owner_raises(self):
        activity = make_activity(owner="mascot")
        with self.assertRaises(ValueError):
            se.responsibility_findings(activity)


class InterfaceCoverageFindingsTest(unittest.TestCase):
    def test_no_required_interfaces_no_finding(self):
        activity = make_activity(kind="analysis", interfaces=[])
        self.assertEqual(se.interface_coverage_findings(activity), [])

    def test_required_interface_present_no_finding(self):
        activity = make_activity(
            kind="verification",
            interfaces=[{"counterpart": "product_assurance"}],
        )
        self.assertEqual(se.interface_coverage_findings(activity), [])

    def test_required_interface_missing_flagged(self):
        activity = make_activity(kind="verification", interfaces=[])
        findings = se.interface_coverage_findings(activity)
        self.assertEqual(
            findings,
            [
                {
                    "issue": "missing_required_interface",
                    "activity": "act-1",
                    "counterpart": "product_assurance",
                }
            ],
        )

    def test_unrecognized_counterpart_raises(self):
        activity = make_activity(
            kind="verification", interfaces=[{"counterpart": "marketing"}]
        )
        with self.assertRaises(ValueError):
            se.interface_coverage_findings(activity)

    def test_unrecognized_kind_raises(self):
        activity = make_activity(kind="mystery_activity", interfaces=[])
        with self.assertRaises(ValueError):
            se.interface_coverage_findings(activity)


class StatusFindingsTest(unittest.TestCase):
    def test_planned_status_no_finding(self):
        activity = make_activity(status="planned")
        self.assertEqual(se.status_findings(activity, {"act-1": activity}), [])

    def test_blocked_with_reason_no_finding(self):
        activity = make_activity(status="blocked", blocking_reason="awaiting review")
        self.assertEqual(se.status_findings(activity, {"act-1": activity}), [])

    def test_blocked_without_reason_flagged(self):
        activity = make_activity(status="blocked", blocking_reason=None)
        findings = se.status_findings(activity, {"act-1": activity})
        self.assertEqual(
            findings, [{"issue": "blocked_without_reason", "activity": "act-1"}]
        )

    def test_complete_with_complete_dependency_no_finding(self):
        dep = make_activity(id="act-0", status="complete")
        activity = make_activity(status="complete", depends_on=["act-0"])
        activities_by_id = {"act-0": dep, "act-1": activity}
        self.assertEqual(se.status_findings(activity, activities_by_id), [])

    def test_complete_with_incomplete_dependency_flagged(self):
        dep = make_activity(id="act-0", status="in_progress")
        activity = make_activity(status="complete", depends_on=["act-0"])
        activities_by_id = {"act-0": dep, "act-1": activity}
        findings = se.status_findings(activity, activities_by_id)
        self.assertEqual(
            findings,
            [
                {
                    "issue": "incomplete_dependency",
                    "activity": "act-1",
                    "dependency": "act-0",
                }
            ],
        )

    def test_unrecognized_status_raises(self):
        activity = make_activity(status="halted")
        with self.assertRaises(ValueError):
            se.status_findings(activity, {"act-1": activity})

    def test_dangling_dependency_raises(self):
        activity = make_activity(status="complete", depends_on=["ghost"])
        with self.assertRaises(ValueError):
            se.status_findings(activity, {"act-1": activity})


class SeManagementReviewTest(unittest.TestCase):
    def test_fully_compliant_activity(self):
        activity = make_activity(
            kind="verification",
            owner="product_assurance_engineer",
            interfaces=[{"counterpart": "product_assurance"}],
            status="planned",
        )
        review = se.se_management_review(activity, {"act-1": activity})
        self.assertEqual(
            review, {"responsibility": [], "interface": [], "status": []}
        )
        self.assertTrue(se.is_se_management_compliant(review))

    def test_review_surfaces_each_category_independently(self):
        activity = make_activity(
            kind="verification",
            owner=None,
            interfaces=[],
            status="blocked",
            blocking_reason=None,
        )
        review = se.se_management_review(activity, {"act-1": activity})
        self.assertTrue(review["responsibility"])
        self.assertTrue(review["interface"])
        self.assertTrue(review["status"])
        self.assertFalse(se.is_se_management_compliant(review))


class SeManagementProgramReviewTest(unittest.TestCase):
    def test_compliant_program(self):
        activities = [
            make_activity(
                id="act-mgmt",
                kind="technical_management",
                owner="se_manager",
                interfaces=[{"counterpart": "project_management"}],
                status="in_progress",
            ),
            make_activity(
                id="act-analysis",
                kind="analysis",
                owner="lead_engineer",
                interfaces=[],
                status="planned",
            ),
        ]
        program_review = se.se_management_program_review(activities)
        self.assertTrue(se.is_program_compliant(program_review))

    def test_noncompliant_program_flags_offending_activity_only(self):
        activities = [
            make_activity(
                id="act-mgmt",
                kind="technical_management",
                owner="se_manager",
                interfaces=[{"counterpart": "project_management"}],
                status="in_progress",
            ),
            make_activity(
                id="act-risk",
                kind="risk_management",
                owner=None,
                interfaces=[],
                status="planned",
            ),
        ]
        program_review = se.se_management_program_review(activities)
        self.assertFalse(se.is_program_compliant(program_review))
        self.assertTrue(se.is_se_management_compliant(program_review["act-mgmt"]))
        self.assertFalse(se.is_se_management_compliant(program_review["act-risk"]))

    def test_duplicate_activity_id_raises(self):
        activities = [make_activity(id="act-1"), make_activity(id="act-1")]
        with self.assertRaises(ValueError):
            se.se_management_program_review(activities)


if __name__ == "__main__":
    unittest.main(verbosity=2)
