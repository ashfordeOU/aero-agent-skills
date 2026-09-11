#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C §5.4.2 Verification Control Board
(VCB) governance.

Exercises scripts/e1002_vcb_logic.py (stdlib unittest, offline). Contract:
a VCB member role is valid when it is in the recognised set and raises for
anything outside it; composition validation flags each missing required role
(customer, supplier) and raises for an unrecognised member role; quorum is
met when both customer and supplier are present and fails when either is
absent; agenda-item authority is 'elevated' for closeout/exception/waiver
items and 'routine' for status-change and action-item-review, with a raise
for unknown types; authority_sufficient requires both required roles for
elevated items and at least one for routine; validate_vcb_decision raises for
unknown item type, unknown decision outcome, or empty rationale, and returns
an authority finding when the attending roles fall short; the full meeting
review aggregates composition, quorum, and decision findings; and the meeting
is compliant only when all three finding lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_vcb_logic as vcb  # noqa: E402


class ValidateMemberRoleTest(unittest.TestCase):
    def test_customer_role_is_valid(self):
        vcb.validate_member_role("customer")

    def test_supplier_role_is_valid(self):
        vcb.validate_member_role("supplier")

    def test_technical_expert_role_is_valid(self):
        vcb.validate_member_role("technical_expert")

    def test_observer_role_is_valid(self):
        vcb.validate_member_role("observer")

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            vcb.validate_member_role("auditor")


class ValidateVcbCompositionTest(unittest.TestCase):
    def test_composition_with_both_required_roles_passes(self):
        members = [{"role": "customer"}, {"role": "supplier"}]
        self.assertEqual(vcb.validate_vcb_composition(members), [])

    def test_composition_with_all_roles_passes(self):
        members = [
            {"role": "customer"},
            {"role": "supplier"},
            {"role": "technical_expert"},
            {"role": "observer"},
        ]
        self.assertEqual(vcb.validate_vcb_composition(members), [])

    def test_composition_missing_customer_flagged(self):
        members = [{"role": "supplier"}, {"role": "technical_expert"}]
        violations = vcb.validate_vcb_composition(members)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["missing_role"], "customer")

    def test_composition_missing_supplier_flagged(self):
        members = [{"role": "customer"}, {"role": "observer"}]
        violations = vcb.validate_vcb_composition(members)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["missing_role"], "supplier")

    def test_composition_missing_both_required_roles_flags_two(self):
        members = [{"role": "technical_expert"}, {"role": "observer"}]
        violations = vcb.validate_vcb_composition(members)
        self.assertEqual(len(violations), 2)
        missing = {v["missing_role"] for v in violations}
        self.assertEqual(missing, {"customer", "supplier"})

    def test_composition_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            vcb.validate_vcb_composition([{"role": "interloper"}])


class CheckQuorumTest(unittest.TestCase):
    def test_quorum_met_with_customer_and_supplier(self):
        self.assertTrue(vcb.check_quorum(["customer", "supplier"]))

    def test_quorum_met_with_additional_roles(self):
        self.assertTrue(
            vcb.check_quorum(["customer", "supplier", "technical_expert"])
        )

    def test_quorum_fails_without_supplier(self):
        self.assertFalse(vcb.check_quorum(["customer", "technical_expert"]))

    def test_quorum_fails_without_customer(self):
        self.assertFalse(vcb.check_quorum(["supplier", "observer"]))

    def test_quorum_fails_with_empty_attendance(self):
        self.assertFalse(vcb.check_quorum([]))


class CategorizeAgendaItemTest(unittest.TestCase):
    def test_closeout_approval_is_elevated(self):
        self.assertEqual(vcb.categorize_agenda_item("closeout_approval"), "elevated")

    def test_exception_approval_is_elevated(self):
        self.assertEqual(vcb.categorize_agenda_item("exception_approval"), "elevated")

    def test_discrepancy_waiver_is_elevated(self):
        self.assertEqual(vcb.categorize_agenda_item("discrepancy_waiver"), "elevated")

    def test_verification_status_change_is_routine(self):
        self.assertEqual(
            vcb.categorize_agenda_item("verification_status_change"), "routine"
        )

    def test_action_item_review_is_routine(self):
        self.assertEqual(vcb.categorize_agenda_item("action_item_review"), "routine")

    def test_unknown_item_type_raises(self):
        with self.assertRaises(ValueError):
            vcb.categorize_agenda_item("budget_review")


class AuthoritySufficientTest(unittest.TestCase):
    def test_elevated_item_with_both_required_roles_is_sufficient(self):
        self.assertTrue(
            vcb.authority_sufficient(
                "closeout_approval", ["customer", "supplier", "technical_expert"]
            )
        )

    def test_elevated_item_with_customer_only_is_insufficient(self):
        self.assertFalse(
            vcb.authority_sufficient("closeout_approval", ["customer"])
        )

    def test_elevated_item_with_supplier_only_is_insufficient(self):
        self.assertFalse(
            vcb.authority_sufficient("exception_approval", ["supplier"])
        )

    def test_routine_item_with_customer_only_is_sufficient(self):
        self.assertTrue(
            vcb.authority_sufficient("verification_status_change", ["customer"])
        )

    def test_routine_item_with_no_required_role_is_insufficient(self):
        self.assertFalse(
            vcb.authority_sufficient(
                "action_item_review", ["technical_expert", "observer"]
            )
        )


class ValidateVcbDecisionTest(unittest.TestCase):
    def test_valid_decision_returns_no_violations(self):
        violations = vcb.validate_vcb_decision(
            "VRQ-001",
            "verification_status_change",
            "approved",
            ["customer", "supplier"],
            "Verification evidence reviewed and accepted.",
        )
        self.assertEqual(violations, [])

    def test_unknown_item_type_raises(self):
        with self.assertRaises(ValueError):
            vcb.validate_vcb_decision(
                "VRQ-002",
                "budget_review",
                "approved",
                ["customer", "supplier"],
                "Rationale text.",
            )

    def test_unknown_decision_outcome_raises(self):
        with self.assertRaises(ValueError):
            vcb.validate_vcb_decision(
                "VRQ-003",
                "closeout_approval",
                "tabled",
                ["customer", "supplier"],
                "Rationale text.",
            )

    def test_empty_rationale_raises(self):
        with self.assertRaises(ValueError):
            vcb.validate_vcb_decision(
                "VRQ-004",
                "closeout_approval",
                "approved",
                ["customer", "supplier"],
                "",
            )

    def test_whitespace_only_rationale_raises(self):
        with self.assertRaises(ValueError):
            vcb.validate_vcb_decision(
                "VRQ-005",
                "action_item_review",
                "deferred",
                ["customer", "supplier"],
                "   ",
            )

    def test_insufficient_authority_for_elevated_item_flagged(self):
        violations = vcb.validate_vcb_decision(
            "VRQ-006",
            "closeout_approval",
            "approved",
            ["customer"],
            "Closeout evidence reviewed.",
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "insufficient_decision_authority")
        self.assertEqual(violations[0]["category"], "elevated")

    def test_deferred_decision_is_valid_outcome(self):
        violations = vcb.validate_vcb_decision(
            "VRQ-007",
            "verification_status_change",
            "deferred",
            ["customer", "supplier"],
            "Awaiting updated test evidence.",
        )
        self.assertEqual(violations, [])

    def test_conditionally_approved_is_valid_outcome(self):
        violations = vcb.validate_vcb_decision(
            "VRQ-008",
            "discrepancy_waiver",
            "conditionally_approved",
            ["customer", "supplier"],
            "Waiver granted pending follow-up action.",
        )
        self.assertEqual(violations, [])


class VcbMeetingReviewTest(unittest.TestCase):
    def _compliant_meeting(self):
        return {
            "members": [
                {"role": "customer", "name": "C. Ashford"},
                {"role": "supplier", "name": "S. Bauer"},
                {"role": "technical_expert", "name": "T. Reyes"},
            ],
            "roles_present": ["customer", "supplier", "technical_expert"],
            "decisions": [
                {
                    "item_id": "VRQ-010",
                    "item_type": "verification_status_change",
                    "decision": "approved",
                    "rationale": "All verification evidence packages reviewed and accepted.",
                },
                {
                    "item_id": "VRQ-011",
                    "item_type": "closeout_approval",
                    "decision": "approved",
                    "rationale": "Closeout documentation complete and signed off.",
                },
            ],
        }

    def test_fully_compliant_meeting_has_no_findings(self):
        review = vcb.vcb_meeting_review(self._compliant_meeting())
        self.assertEqual(review["composition"], [])
        self.assertEqual(review["quorum"], [])
        self.assertEqual(review["decisions"], [])
        self.assertTrue(vcb.is_vcb_meeting_compliant(review))

    def test_missing_supplier_in_composition_flagged(self):
        meeting = self._compliant_meeting()
        meeting["members"] = [{"role": "customer"}]
        review = vcb.vcb_meeting_review(meeting)
        self.assertEqual(len(review["composition"]), 1)
        self.assertEqual(review["composition"][0]["missing_role"], "supplier")

    def test_quorum_not_met_when_supplier_absent(self):
        meeting = self._compliant_meeting()
        meeting["roles_present"] = ["customer", "technical_expert"]
        review = vcb.vcb_meeting_review(meeting)
        self.assertEqual(len(review["quorum"]), 1)
        self.assertIn("supplier", review["quorum"][0]["missing_required_roles"])

    def test_elevated_item_without_authority_flagged_in_decisions(self):
        meeting = self._compliant_meeting()
        meeting["roles_present"] = ["customer", "technical_expert"]
        review = vcb.vcb_meeting_review(meeting)
        authority_findings = [
            d for d in review["decisions"]
            if d["issue"] == "insufficient_decision_authority"
        ]
        self.assertTrue(len(authority_findings) >= 1)

    def test_is_vcb_meeting_compliant_false_when_findings_exist(self):
        meeting = self._compliant_meeting()
        meeting["members"] = [{"role": "customer"}]
        meeting["roles_present"] = ["customer"]
        review = vcb.vcb_meeting_review(meeting)
        self.assertFalse(vcb.is_vcb_meeting_compliant(review))

    def test_unknown_role_in_attendance_raises(self):
        meeting = self._compliant_meeting()
        meeting["roles_present"] = ["customer", "supplier", "spy"]
        with self.assertRaises(ValueError):
            vcb.vcb_meeting_review(meeting)

    def test_meeting_with_no_decisions_is_structurally_valid(self):
        meeting = self._compliant_meeting()
        meeting["decisions"] = []
        review = vcb.vcb_meeting_review(meeting)
        self.assertEqual(review["decisions"], [])
        self.assertTrue(vcb.is_vcb_meeting_compliant(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
