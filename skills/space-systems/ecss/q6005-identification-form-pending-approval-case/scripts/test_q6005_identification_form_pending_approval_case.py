"""Contract tests for the clause 6.2.3 pending-approval form-handling logic."""

import datetime
import unittest

from q6005_identification_form_pending_approval_case_logic import (
    APPROVAL_MILESTONES,
    DECISION_MILESTONE,
    FORM_LAPSE_DAYS,
    PROVISIONAL_RATIO,
    REQUIRED_EVIDENCE,
    REVALIDATION_INTERVAL_DAYS,
    approval_pending,
    assess_pending_approval_form,
    closed_milestones,
    completion_ratio,
    days_between,
    failed_milestones,
    form_disposition,
    lapse_date,
    missing_evidence,
    open_milestones,
    parse_date,
    revalidation_due,
    schedule_margin_days,
    validate_milestones,
    waived_milestones,
)


def record(**overrides):
    """A pending line with four of six milestones closed, unless overridden."""
    base = {
        "quality-system-audit": "closed",
        "process-capability-audit": "closed",
        "technology-flow-review": "closed",
        "operator-certification": "closed",
        "line-qualification-lot": "open",
        "approval-decision": "open",
    }
    base.update(overrides)
    return base


class ParseDateTests(unittest.TestCase):
    def test_iso_string_parsed(self):
        self.assertEqual(parse_date("2026-03-04"), datetime.date(2026, 3, 4))

    def test_date_passes_through(self):
        day = datetime.date(2026, 1, 9)
        self.assertEqual(parse_date(day), day)

    def test_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            parse_date(datetime.datetime(2026, 3, 4, 10, 0))

    def test_malformed_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("04/03/2026", "form_issue_date")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date(20260304)


class ValidateMilestoneTests(unittest.TestCase):
    def test_full_record_accepted(self):
        self.assertEqual(len(validate_milestones(record())), len(APPROVAL_MILESTONES))

    def test_status_case_normalised(self):
        validated = validate_milestones(record(**{"approval-decision": "OPEN"}))
        self.assertEqual(validated[DECISION_MILESTONE], "open")

    def test_unknown_milestone_rejected(self):
        bad = record()
        bad["marketing-review"] = "closed"
        with self.assertRaises(ValueError):
            validate_milestones(bad)

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_milestones(record(**{"line-qualification-lot": "nearly"}))

    def test_omitted_milestone_rejected(self):
        partial = record()
        del partial["operator-certification"]
        with self.assertRaises(ValueError):
            validate_milestones(partial)

    def test_empty_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_milestones({})

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_milestones(list(APPROVAL_MILESTONES))


class MilestoneGroupingTests(unittest.TestCase):
    def test_closed_group_is_registry_ordered(self):
        closed = closed_milestones(record())
        self.assertEqual(closed[0], "quality-system-audit")
        self.assertEqual(len(closed), 4)

    def test_waiver_counts_as_closed_but_is_reported(self):
        state = record(**{"line-qualification-lot": "waived"})
        self.assertIn("line-qualification-lot", closed_milestones(state))
        self.assertEqual(waived_milestones(state), ("line-qualification-lot",))

    def test_open_group_lists_only_open_steps(self):
        self.assertEqual(
            open_milestones(record()), ("line-qualification-lot", "approval-decision")
        )

    def test_failed_group_picks_up_a_failure(self):
        state = record(**{"process-capability-audit": "failed"})
        self.assertEqual(failed_milestones(state), ("process-capability-audit",))

    def test_completion_ratio_is_the_closed_share(self):
        self.assertAlmostEqual(completion_ratio(record()), 4.0 / 6.0, places=9)

    def test_completion_ratio_lands_on_the_threshold(self):
        state = record(**{"operator-certification": "open"})
        self.assertAlmostEqual(completion_ratio(state), PROVISIONAL_RATIO, places=9)


class ApprovalPendingTests(unittest.TestCase):
    def test_open_decision_is_pending(self):
        self.assertTrue(approval_pending(record()))

    def test_closed_decision_is_not_pending(self):
        self.assertFalse(approval_pending(record(**{"approval-decision": "closed"})))

    def test_waived_decision_is_not_pending(self):
        self.assertFalse(approval_pending(record(**{"approval-decision": "waived"})))

    def test_a_failure_anywhere_ends_the_pending_state(self):
        self.assertFalse(approval_pending(record(**{"technology-flow-review": "failed"})))


class FormDatingTests(unittest.TestCase):
    def test_revalidation_is_the_declared_interval(self):
        due = revalidation_due("2026-01-01")
        self.assertEqual(days_between("2026-01-01", due), REVALIDATION_INTERVAL_DAYS)

    def test_lapse_is_the_longer_interval(self):
        lapses = lapse_date("2026-01-01")
        self.assertEqual(days_between("2026-01-01", lapses), FORM_LAPSE_DAYS)

    def test_days_between_is_signed(self):
        self.assertEqual(days_between("2026-05-10", "2026-05-01"), -9)

    def test_schedule_margin_positive_when_approval_precedes_need(self):
        self.assertEqual(schedule_margin_days("2026-04-01", "2026-06-01"), 61)

    def test_schedule_margin_negative_when_approval_lands_late(self):
        self.assertEqual(schedule_margin_days("2026-06-01", "2026-04-01"), -61)


class EvidenceTests(unittest.TestCase):
    def test_complete_evidence_leaves_nothing_missing(self):
        self.assertEqual(missing_evidence(list(REQUIRED_EVIDENCE)), ())

    def test_absent_evidence_reported_in_registry_order(self):
        self.assertEqual(
            missing_evidence(["line-approval-schedule"]), REQUIRED_EVIDENCE[1:]
        )

    def test_none_means_nothing_supplied(self):
        self.assertEqual(missing_evidence(None), REQUIRED_EVIDENCE)

    def test_blank_evidence_token_rejected(self):
        with self.assertRaises(ValueError):
            missing_evidence(["   "])

    def test_non_string_evidence_rejected(self):
        with self.assertRaises(ValueError):
            missing_evidence([7])

    def test_non_sequence_evidence_rejected(self):
        with self.assertRaises(ValueError):
            missing_evidence("line-approval-schedule")


class DispositionTests(unittest.TestCase):
    def test_healthy_pending_line_accepted_provisionally(self):
        self.assertEqual(form_disposition(record(), 30, True, False), "accept-provisionally")

    def test_threshold_case_still_accepted(self):
        state = record(**{"operator-certification": "open"})
        self.assertEqual(form_disposition(state, 0, True, False), "accept-provisionally")

    def test_early_line_held(self):
        state = record(**{"technology-flow-review": "open", "operator-certification": "open"})
        self.assertEqual(form_disposition(state, 30, True, False), "hold")

    def test_missing_evidence_holds_the_form(self):
        self.assertEqual(form_disposition(record(), 30, False, False), "hold")

    def test_lapsed_form_held(self):
        self.assertEqual(form_disposition(record(), 30, True, True), "hold")

    def test_negative_margin_holds_the_form(self):
        self.assertEqual(form_disposition(record(), -1, True, False), "hold")

    def test_failed_milestone_rejects(self):
        state = record(**{"line-qualification-lot": "failed"})
        self.assertEqual(form_disposition(state, 30, True, False), "reject")

    def test_approved_line_is_out_of_scope(self):
        state = record(**{"line-qualification-lot": "closed", "approval-decision": "closed"})
        self.assertEqual(form_disposition(state, 30, True, False), "out-of-scope-line-approved")

    def test_boolean_margin_rejected(self):
        with self.assertRaises(ValueError):
            form_disposition(record(), True, True, False)

    def test_non_boolean_evidence_flag_rejected(self):
        with self.assertRaises(ValueError):
            form_disposition(record(), 30, "yes", False)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "milestones": record(),
            "form_issue_date": "2026-01-15",
            "approval_target_date": "2026-05-15",
            "hardware_need_date": "2026-07-15",
            "as_of_date": "2026-03-15",
            "evidence_items": list(REQUIRED_EVIDENCE),
        }
        spec.update(overrides)
        return spec

    def test_nominal_case_is_provisionally_acceptable(self):
        out = assess_pending_approval_form(self._spec())
        self.assertEqual(out["disposition"], "accept-provisionally")
        self.assertEqual(out["findings"], [])

    def test_ratio_and_pending_flag_reported(self):
        out = assess_pending_approval_form(self._spec())
        self.assertAlmostEqual(out["completion_ratio"], 4.0 / 6.0, places=9)
        self.assertTrue(out["approval_pending"])

    def test_overdue_reconfirmation_is_a_finding(self):
        out = assess_pending_approval_form(self._spec(as_of_date="2026-09-15"))
        self.assertTrue(out["revalidation_overdue"])
        self.assertFalse(out["form_expired"])
        self.assertTrue(any("re-confirmation" in f for f in out["findings"]))

    def test_lapsed_form_holds_and_is_not_merely_overdue(self):
        out = assess_pending_approval_form(self._spec(as_of_date="2027-06-15"))
        self.assertTrue(out["form_expired"])
        self.assertFalse(out["revalidation_overdue"])
        self.assertEqual(out["disposition"], "hold")

    def test_missing_evidence_surfaces_in_findings(self):
        out = assess_pending_approval_form(self._spec(evidence_items=[]))
        self.assertEqual(out["missing_evidence"], REQUIRED_EVIDENCE)
        self.assertEqual(out["disposition"], "hold")

    def test_waiver_is_reported_even_when_accepted(self):
        state = record(**{"operator-certification": "waived"})
        out = assess_pending_approval_form(self._spec(milestones=state))
        self.assertEqual(out["waived_milestones"], ("operator-certification",))
        self.assertTrue(any("waiver" in f for f in out["findings"]))

    def test_late_approval_target_reported_with_day_count(self):
        out = assess_pending_approval_form(self._spec(hardware_need_date="2026-04-15"))
        self.assertEqual(out["schedule_margin_days"], -30)
        self.assertTrue(any("30 day(s) after" in f for f in out["findings"]))

    def test_settled_approval_routed_out_of_the_clause(self):
        state = record(**{"line-qualification-lot": "closed", "approval-decision": "closed"})
        out = assess_pending_approval_form(self._spec(milestones=state))
        self.assertEqual(out["disposition"], "out-of-scope-line-approved")

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["as_of_date"]
        with self.assertRaises(ValueError):
            assess_pending_approval_form(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_pending_approval_form(["milestones"])

    def test_target_before_issue_rejected(self):
        with self.assertRaises(ValueError):
            assess_pending_approval_form(self._spec(approval_target_date="2025-12-01"))

    def test_as_of_before_issue_rejected(self):
        with self.assertRaises(ValueError):
            assess_pending_approval_form(self._spec(as_of_date="2025-12-01"))


if __name__ == "__main__":
    unittest.main()
