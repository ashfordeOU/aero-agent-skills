"""Contract test for the q40-02-step4-track-accept leaf (stdlib unittest)."""

import unittest

from q40_02_step4_track_accept_logic import (
    ACCEPTANCE_RECORD_FIELDS,
    NOTIFICATION_AUDIENCE,
    STATUS_STATES,
    acceptance_record_findings,
    assess_hazard_log,
    assess_hazard_report,
    authority_is_sufficient,
    minimum_authority,
    outstanding_notifications,
    replay_status_history,
    transition_is_legal,
    validate_hazard_report,
)

FULL_HISTORY = ["open", "in-work", "controlled", "verified", "accepted"]


def record(**kw):
    rec = {
        "rationale": "residual risk is inside the project floor after two verified controls",
        "evidence_reference": "HR-7-VER-002",
        "signatory": "safety review board chair",
        "date": "2026-04-18",
    }
    rec.update(kw)
    return rec


def report(rid="HR-7", **kw):
    rec = {
        "id": rid,
        "residual_severity": "critical",
        "history": list(FULL_HISTORY),
        "acceptance_authority": "project-manager",
        "acceptance_record": record(),
        "notified": list(NOTIFICATION_AUDIENCE["accepted"]),
    }
    rec.update(kw)
    return rec


class TestTransitions(unittest.TestCase):
    def test_forward_step_is_legal(self):
        self.assertTrue(transition_is_legal("open", "in-work"))
        self.assertTrue(transition_is_legal("verified", "accepted"))

    def test_skipping_a_state_is_illegal(self):
        self.assertFalse(transition_is_legal("open", "accepted"))

    def test_reopening_to_in_work_is_legal(self):
        self.assertTrue(transition_is_legal("accepted", "in-work"))
        self.assertTrue(transition_is_legal("controlled", "in-work"))

    def test_closed_is_terminal(self):
        for state in STATUS_STATES:
            self.assertFalse(transition_is_legal("closed", state))

    def test_backward_step_other_than_in_work_is_illegal(self):
        self.assertFalse(transition_is_legal("verified", "controlled"))

    def test_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            transition_is_legal("open", "pending-vibes")


class TestHistoryReplay(unittest.TestCase):
    def test_clean_history_has_no_findings(self):
        self.assertEqual(replay_status_history(FULL_HISTORY), [])

    def test_jump_is_reported(self):
        findings = replay_status_history(["open", "accepted"])
        self.assertEqual(findings, ["illegal-transition:open->accepted"])

    def test_history_not_starting_open_raises(self):
        with self.assertRaises(ValueError):
            replay_status_history(["in-work", "controlled"])

    def test_empty_history_raises(self):
        with self.assertRaises(ValueError):
            replay_status_history([])

    def test_reopened_history_is_clean(self):
        history = ["open", "in-work", "controlled", "in-work", "controlled"]
        self.assertEqual(replay_status_history(history), [])


class TestAuthority(unittest.TestCase):
    def test_catastrophic_needs_the_board(self):
        self.assertEqual(minimum_authority("catastrophic"), "customer-safety-review-board")

    def test_minor_may_be_signed_at_working_level(self):
        self.assertTrue(authority_is_sufficient("minor", "working-level-engineer"))

    def test_working_level_cannot_sign_catastrophic(self):
        self.assertFalse(
            authority_is_sufficient("catastrophic", "working-level-engineer")
        )

    def test_higher_authority_than_required_is_sufficient(self):
        self.assertTrue(
            authority_is_sufficient("minor", "customer-safety-review-board")
        )

    def test_exact_minimum_is_sufficient(self):
        self.assertTrue(authority_is_sufficient("critical", "project-manager"))

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            minimum_authority("awkward")

    def test_unknown_authority_raises(self):
        with self.assertRaises(ValueError):
            authority_is_sufficient("minor", "the-intern")


class TestAcceptanceRecord(unittest.TestCase):
    def test_complete_record_is_clean(self):
        self.assertEqual(acceptance_record_findings(record()), [])

    def test_absent_record_is_a_finding(self):
        self.assertEqual(acceptance_record_findings(None), ["acceptance-record-absent"])

    def test_each_missing_field_is_named(self):
        findings = acceptance_record_findings({})
        self.assertEqual(len(findings), len(ACCEPTANCE_RECORD_FIELDS))
        self.assertIn("acceptance-record-missing:rationale", findings)

    def test_blank_field_counts_as_missing(self):
        findings = acceptance_record_findings(record(signatory="   "))
        self.assertEqual(findings, ["acceptance-record-missing:signatory"])

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            acceptance_record_findings(["rationale"])


class TestNotifications(unittest.TestCase):
    def test_all_told_leaves_nothing_outstanding(self):
        self.assertEqual(
            outstanding_notifications("accepted", NOTIFICATION_AUDIENCE["accepted"]), []
        )

    def test_missing_audience_is_listed(self):
        self.assertEqual(
            outstanding_notifications("accepted", ["safety-engineering", "product-assurance"]),
            ["customer"],
        )

    def test_nobody_told_lists_the_whole_audience(self):
        self.assertEqual(
            outstanding_notifications("controlled", []),
            list(NOTIFICATION_AUDIENCE["controlled"]),
        )

    def test_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            outstanding_notifications("shrugged-at", [])


class TestReportAssessment(unittest.TestCase):
    def test_clean_report_is_controlled(self):
        result = assess_hazard_report(report())
        self.assertTrue(result["controlled"])
        self.assertEqual(result["findings"], [])

    def test_authority_below_minimum_is_a_finding(self):
        result = assess_hazard_report(
            report(residual_severity="catastrophic",
                   acceptance_authority="working-level-engineer")
        )
        self.assertIn(
            "acceptance-authority-below-catastrophic-minimum", result["findings"]
        )

    def test_accepted_without_authority_is_a_finding(self):
        result = assess_hazard_report(report(acceptance_authority=None))
        self.assertIn("acceptance-authority-not-recorded", result["findings"])

    def test_unaccepted_report_needs_no_acceptance_record(self):
        history = ["open", "in-work", "controlled"]
        result = assess_hazard_report(
            report(
                history=history,
                acceptance_authority=None,
                acceptance_record=None,
                notified=list(NOTIFICATION_AUDIENCE["controlled"]),
            )
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_outstanding_notification_is_a_finding(self):
        result = assess_hazard_report(report(notified=["safety-engineering"]))
        self.assertIn("notification-outstanding:customer", result["findings"])

    def test_illegal_history_reaches_the_verdict(self):
        result = assess_hazard_report(
            report(history=["open", "accepted"])
        )
        self.assertIn("illegal-transition:open->accepted", result["findings"])
        self.assertFalse(result["controlled"])

    def test_minimum_authority_is_reported(self):
        result = assess_hazard_report(report(residual_severity="major"))
        self.assertEqual(result["minimum_authority"], "product-assurance-manager")

    def test_unknown_residual_severity_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard_report(report(residual_severity="spicy"))

    def test_report_without_history_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard_report(report(history=[]))

    def test_non_mapping_report_raises(self):
        with self.assertRaises(ValueError):
            validate_hazard_report(["HR-7"])


class TestLogAssessment(unittest.TestCase):
    def test_clean_log_is_controlled(self):
        result = assess_hazard_log([report("HR-1"), report("HR-2")])
        self.assertTrue(result["controlled"])
        self.assertEqual(result["finding_ids"], [])

    def test_open_ids_exclude_accepted_reports(self):
        open_report = report(
            "HR-3",
            history=["open", "in-work"],
            acceptance_authority=None,
            acceptance_record=None,
            notified=list(NOTIFICATION_AUDIENCE["in-work"]),
        )
        result = assess_hazard_log([report("HR-1"), open_report])
        self.assertEqual(result["open_ids"], ["HR-3"])

    def test_state_distribution_counts_every_report(self):
        result = assess_hazard_log([report("HR-1"), report("HR-2")])
        self.assertEqual(sum(result["state_distribution"].values()), 2)

    def test_duplicate_report_id_raises(self):
        with self.assertRaises(ValueError):
            assess_hazard_log([report("HR-1"), report("HR-1")])

    def test_empty_log_raises(self):
        with self.assertRaises(ValueError):
            assess_hazard_log([])

    def test_finding_ids_name_the_bad_report(self):
        bad = report("HR-9", notified=[])
        result = assess_hazard_log([report("HR-1"), bad])
        self.assertEqual(result["finding_ids"], ["HR-9"])


if __name__ == "__main__":
    unittest.main()
