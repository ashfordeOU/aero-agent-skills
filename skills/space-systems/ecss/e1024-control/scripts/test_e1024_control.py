"""
Gate 3 contract tests for e1024-control (ECSS-E-ST-10C §5.5).

Covers: change categorization, ICB quorum, ICB voting, agreement
completeness, state transition validation, audit trail check,
ChangeRequest data class, and InterfaceBaseline state machine.

Run: python3 test_e1024_control.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1024_control_logic import (
    BASELINE_STATES,
    VALID_TRANSITIONS,
    categorize_change_request,
    check_icb_quorum,
    evaluate_icb_vote,
    check_agreement_completeness,
    validate_state_transition,
    check_audit_trail,
    ChangeRequest,
    InterfaceBaseline,
)


# ---------------------------------------------------------------------------
# Change categorization
# ---------------------------------------------------------------------------

class TestChangeCategorization(unittest.TestCase):

    def test_functional_change_is_major(self):
        result = categorize_change_request(True, False, False)
        self.assertEqual(result, "major")

    def test_timing_change_is_major(self):
        result = categorize_change_request(False, True, False)
        self.assertEqual(result, "major")

    def test_physical_change_is_major(self):
        result = categorize_change_request(False, False, True)
        self.assertEqual(result, "major")

    def test_all_dimensions_affected_is_major(self):
        result = categorize_change_request(True, True, True)
        self.assertEqual(result, "major")

    def test_no_dimension_affected_is_minor(self):
        result = categorize_change_request(False, False, False)
        self.assertEqual(result, "minor")


# ---------------------------------------------------------------------------
# ICB quorum
# ---------------------------------------------------------------------------

class TestICBQuorum(unittest.TestCase):

    def test_exact_quorum_met(self):
        self.assertTrue(check_icb_quorum(["A", "B", "C"], 3))

    def test_quorum_exceeded(self):
        self.assertTrue(check_icb_quorum(["A", "B", "C", "D"], 3))

    def test_quorum_not_met(self):
        self.assertFalse(check_icb_quorum(["A", "B"], 3))

    def test_empty_voter_list_fails_quorum(self):
        self.assertFalse(check_icb_quorum([], 1))

    def test_quorum_zero_raises(self):
        with self.assertRaises(ValueError):
            check_icb_quorum(["A"], 0)

    def test_quorum_negative_raises(self):
        with self.assertRaises(ValueError):
            check_icb_quorum(["A"], -1)


# ---------------------------------------------------------------------------
# ICB voting
# ---------------------------------------------------------------------------

class TestICBVoting(unittest.TestCase):

    def test_majority_yes_is_approved(self):
        votes = {"A": "yes", "B": "yes", "C": "no"}
        result = evaluate_icb_vote(votes, required_quorum=3)
        self.assertTrue(result["approved"])
        self.assertEqual(result["yes"], 2)
        self.assertEqual(result["no"], 1)
        self.assertEqual(result["reason"], "majority")

    def test_majority_no_is_rejected(self):
        votes = {"A": "no", "B": "no", "C": "yes"}
        result = evaluate_icb_vote(votes, required_quorum=3)
        self.assertFalse(result["approved"])
        self.assertEqual(result["reason"], "not_majority")

    def test_tie_is_rejected(self):
        votes = {"A": "yes", "B": "no"}
        result = evaluate_icb_vote(votes, required_quorum=2)
        self.assertFalse(result["approved"])

    def test_quorum_not_met_returns_not_approved(self):
        votes = {"A": "yes", "B": "yes"}
        result = evaluate_icb_vote(votes, required_quorum=3)
        self.assertFalse(result["approved"])
        self.assertEqual(result["reason"], "quorum_not_met")

    def test_abstain_counted_but_not_decisive(self):
        votes = {"A": "yes", "B": "abstain", "C": "abstain"}
        result = evaluate_icb_vote(votes, required_quorum=3)
        self.assertTrue(result["approved"])   # 1 yes > 0 no
        self.assertEqual(result["abstain"], 2)

    def test_case_insensitive_vote_values(self):
        # Mixed-case tokens must normalise into the correct tally buckets.
        # This board splits 1 yes vs 1 no, which is a tie, so the motion fails
        # (consistent with test_tie_is_rejected): an abstention withholds a
        # vote and can never convert a tied board vote into an approval.
        votes = {"A": "YES", "B": "No", "C": "Abstain"}
        result = evaluate_icb_vote(votes, required_quorum=3)
        self.assertEqual(result["yes"], 1)
        self.assertEqual(result["no"], 1)
        self.assertEqual(result["abstain"], 1)
        self.assertFalse(result["approved"])
        self.assertEqual(result["reason"], "not_majority")

    def test_case_insensitive_majority_is_approved(self):
        # Case-insensitive parsing must also carry a genuine yes majority
        # through to approval.
        votes = {"A": "Yes", "B": "YES", "C": "nO"}
        result = evaluate_icb_vote(votes, required_quorum=3)
        self.assertTrue(result["approved"])
        self.assertEqual(result["yes"], 2)
        self.assertEqual(result["no"], 1)
        self.assertEqual(result["reason"], "majority")

    def test_surrounding_whitespace_in_vote_values(self):
        # Values padded with whitespace are stripped before classification.
        votes = {"A": " yes ", "B": "\tyes", "C": "no\n"}
        result = evaluate_icb_vote(votes, required_quorum=3)
        self.assertEqual(result["yes"], 2)
        self.assertEqual(result["no"], 1)
        self.assertTrue(result["approved"])

    def test_invalid_vote_value_raises(self):
        votes = {"A": "yes", "B": "maybe"}
        with self.assertRaises(ValueError):
            evaluate_icb_vote(votes, required_quorum=2)

    def test_all_abstain_is_rejected(self):
        votes = {"A": "abstain", "B": "abstain"}
        result = evaluate_icb_vote(votes, required_quorum=2)
        self.assertFalse(result["approved"])  # 0 yes not > 0 no


# ---------------------------------------------------------------------------
# Agreement completeness
# ---------------------------------------------------------------------------

class TestAgreementCompleteness(unittest.TestCase):

    def test_all_signatories_agreed(self):
        result = check_agreement_completeness(
            ["eng-a", "eng-b"], {"eng-a": "agreed", "eng-b": "agreed"}
        )
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing_agreements"], [])

    def test_partial_agreement_is_incomplete(self):
        result = check_agreement_completeness(
            ["eng-a", "eng-b", "sys-eng"], {"eng-a": "agreed"}
        )
        self.assertFalse(result["complete"])
        self.assertIn("eng-b", result["missing_agreements"])
        self.assertIn("sys-eng", result["missing_agreements"])

    def test_no_agreements_recorded(self):
        result = check_agreement_completeness(["eng-a", "eng-b"], {})
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["missing_agreements"]), 2)

    def test_extra_agreements_do_not_block(self):
        result = check_agreement_completeness(
            ["eng-a"],
            {"eng-a": "agreed", "extra": "noted"},
        )
        self.assertTrue(result["complete"])


# ---------------------------------------------------------------------------
# State transition validation
# ---------------------------------------------------------------------------

class TestStateTransitionValidation(unittest.TestCase):

    def test_draft_to_proposed_is_valid(self):
        self.assertTrue(validate_state_transition("draft", "proposed"))

    def test_proposed_to_approved_is_valid(self):
        self.assertTrue(validate_state_transition("proposed", "approved"))

    def test_proposed_back_to_draft_is_valid(self):
        self.assertTrue(validate_state_transition("proposed", "draft"))

    def test_approved_to_superseded_is_valid(self):
        self.assertTrue(validate_state_transition("approved", "superseded"))

    def test_approved_back_to_proposed_is_valid(self):
        self.assertTrue(validate_state_transition("approved", "proposed"))

    def test_draft_to_approved_skip_is_invalid(self):
        self.assertFalse(validate_state_transition("draft", "approved"))

    def test_superseded_is_terminal(self):
        for state in BASELINE_STATES:
            self.assertFalse(validate_state_transition("superseded", state))

    def test_unknown_current_state_raises(self):
        with self.assertRaises(ValueError):
            validate_state_transition("unknown", "proposed")

    def test_unknown_proposed_state_raises(self):
        with self.assertRaises(ValueError):
            validate_state_transition("draft", "archived")


# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------

class TestAuditTrail(unittest.TestCase):

    def test_empty_log_fails(self):
        self.assertFalse(check_audit_trail([]))

    def test_single_entry_passes(self):
        self.assertTrue(check_audit_trail(["draft -> proposed | ICB review request"]))

    def test_min_entries_two_enforced(self):
        self.assertFalse(check_audit_trail(["entry-1"], min_entries=2))

    def test_exactly_two_entries_passes(self):
        self.assertTrue(check_audit_trail(["e1", "e2"], min_entries=2))

    def test_min_entries_zero_raises(self):
        with self.assertRaises(ValueError):
            check_audit_trail([], min_entries=0)


# ---------------------------------------------------------------------------
# ChangeRequest data class
# ---------------------------------------------------------------------------

class TestChangeRequestDataClass(unittest.TestCase):

    def test_major_cr_category(self):
        cr = ChangeRequest("CR-001", "add telemetry field", True, False, False, "if-eng")
        self.assertEqual(cr.category, "major")

    def test_minor_cr_category(self):
        cr = ChangeRequest("CR-002", "fix label typo", False, False, False, "doc-team")
        self.assertEqual(cr.category, "minor")

    def test_empty_cr_id_raises(self):
        with self.assertRaises(ValueError):
            ChangeRequest("", "desc", False, False, False, "eng")

    def test_empty_requester_raises(self):
        with self.assertRaises(ValueError):
            ChangeRequest("CR-003", "desc", False, False, False, "")


# ---------------------------------------------------------------------------
# InterfaceBaseline state machine
# ---------------------------------------------------------------------------

class TestInterfaceBaselineStateMachine(unittest.TestCase):

    def _make(self, state: str = "draft") -> InterfaceBaseline:
        return InterfaceBaseline("ICD-A-B", "1.0", state, "sys-eng")

    def test_valid_transition_updates_state(self):
        b = self._make("draft")
        b.transition_to("proposed", "lead-eng", "ICB review request")
        self.assertEqual(b.state, "proposed")

    def test_valid_transition_appends_to_log(self):
        b = self._make("draft")
        b.transition_to("proposed", "lead-eng", "ICB review")
        self.assertEqual(len(b.change_log), 1)
        self.assertIn("draft -> proposed", b.change_log[0])

    def test_skip_transition_raises(self):
        b = self._make("draft")
        with self.assertRaises(ValueError):
            b.transition_to("approved", "lead-eng", "skip review")

    def test_superseded_cannot_transition_to_any_state(self):
        b = self._make("superseded")
        for state in BASELINE_STATES:
            with self.assertRaises(ValueError):
                b.transition_to(state, "eng", "attempt reopen")

    def test_empty_interface_id_raises(self):
        with self.assertRaises(ValueError):
            InterfaceBaseline("", "1.0", "draft", "owner")

    def test_empty_version_raises(self):
        with self.assertRaises(ValueError):
            InterfaceBaseline("ICD-X", "", "draft", "owner")

    def test_empty_owner_raises(self):
        with self.assertRaises(ValueError):
            InterfaceBaseline("ICD-X", "1.0", "draft", "")

    def test_unknown_initial_state_raises(self):
        with self.assertRaises(ValueError):
            InterfaceBaseline("ICD-X", "1.0", "pending", "owner")

    def test_multiple_transitions_recorded_in_order(self):
        b = self._make("draft")
        b.transition_to("proposed", "eng-a", "submit for review")
        b.transition_to("approved", "eng-b", "ICB vote passed")
        self.assertEqual(b.state, "approved")
        self.assertEqual(len(b.change_log), 2)


if __name__ == "__main__":
    unittest.main()
