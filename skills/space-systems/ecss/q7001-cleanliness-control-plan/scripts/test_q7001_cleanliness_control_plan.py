"""Contract tests for the contamination and cleanliness control plan logic."""

import copy
import datetime
import unittest

from q7001_cleanliness_control_plan_logic import (
    LIFECYCLE_PHASES,
    REQUIRED_CONTENT,
    REQUIRED_TRIGGERS,
    approval_findings,
    assess_control_plan,
    completeness_fraction,
    currency_findings,
    missing_content,
    missing_phases,
    review_status,
    trigger_findings,
    validate_iso_date,
    validate_section_map,
)

AS_OF = "2026-09-19"


def full_sections():
    return {area: "section %d" % (i + 1) for i, area in enumerate(REQUIRED_CONTENT)}


def full_triggers():
    return {
        name: {"action": "re-issue the affected sections", "owner": "PA manager"}
        for name in REQUIRED_TRIGGERS
    }


def sample_plan(**overrides):
    plan = {
        "title": "Contamination and cleanliness control plan",
        "issue": "issue 3 revision 0",
        "issue_date": "2026-03-01",
        "sections": full_sections(),
        "phases": list(LIFECYCLE_PHASES),
        "approved_by": "product assurance manager",
        "recognised_authorities": ["product assurance manager", "project manager"],
        "approval_date": "2026-03-05",
        "last_configuration_change": "2026-02-10",
        "review_interval_days": 365,
        "triggers": full_triggers(),
    }
    plan.update(overrides)
    return copy.deepcopy(plan)


class DateTests(unittest.TestCase):
    def test_iso_string_parsed(self):
        self.assertEqual(
            validate_iso_date("2026-03-01", "d"), datetime.date(2026, 3, 1)
        )

    def test_date_object_passed_through(self):
        day = datetime.date(2026, 3, 1)
        self.assertEqual(validate_iso_date(day, "d"), day)

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_iso_date("01/03/2026", "d")

    def test_empty_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_iso_date("  ", "d")

    def test_non_string_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_iso_date(20260301, "d")


class ContentTests(unittest.TestCase):
    def test_complete_plan_has_no_content_gap(self):
        self.assertEqual(missing_content(full_sections()), [])

    def test_absent_area_is_a_gap(self):
        sections = full_sections()
        del sections["non-conformance-handling"]
        self.assertEqual(missing_content(sections), ["non-conformance-handling"])

    def test_named_but_empty_section_is_still_a_gap(self):
        sections = full_sections()
        sections["design-provisions"] = "   "
        self.assertEqual(missing_content(sections), ["design-provisions"])

    def test_gaps_are_reported_in_the_declared_order(self):
        sections = full_sections()
        del sections["design-provisions"]
        del sections["scope-and-applicable-documents"]
        self.assertEqual(
            missing_content(sections),
            ["scope-and-applicable-documents", "design-provisions"],
        )

    def test_unknown_content_area_rejected(self):
        sections = full_sections()
        sections["catering-arrangements"] = "section 99"
        with self.assertRaises(ValueError):
            missing_content(sections)

    def test_non_mapping_sections_rejected(self):
        with self.assertRaises(ValueError):
            validate_section_map(["design-provisions"])

    def test_non_string_reference_rejected(self):
        sections = full_sections()
        sections["design-provisions"] = 4
        with self.assertRaises(ValueError):
            validate_section_map(sections)


class PhaseTests(unittest.TestCase):
    def test_all_phases_covered(self):
        self.assertEqual(missing_phases(list(LIFECYCLE_PHASES)), [])

    def test_plan_stopping_at_delivery_leaves_two_phases(self):
        covered = ["design", "manufacturing", "assembly-integration-and-test"]
        self.assertEqual(
            missing_phases(covered), ["launch-campaign", "in-orbit-operations"]
        )

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            missing_phases(["design", "disposal"])

    def test_non_sequence_phases_rejected(self):
        with self.assertRaises(ValueError):
            missing_phases("design")

    def test_completeness_is_unity_for_a_complete_plan(self):
        self.assertAlmostEqual(
            completeness_fraction(full_sections(), list(LIFECYCLE_PHASES)),
            1.0,
            places=9,
        )

    def test_one_gap_reduces_completeness_by_one_slot(self):
        sections = full_sections()
        del sections["design-provisions"]
        total = len(REQUIRED_CONTENT) + len(LIFECYCLE_PHASES)
        self.assertAlmostEqual(
            completeness_fraction(sections, list(LIFECYCLE_PHASES)),
            (total - 1) / total,
            places=9,
        )


class ApprovalTests(unittest.TestCase):
    def test_approved_plan_has_no_approval_finding(self):
        self.assertEqual(approval_findings(sample_plan()), [])

    def test_unapproved_plan_is_a_draft(self):
        findings = approval_findings(sample_plan(approved_by=None))
        self.assertEqual(len(findings), 1)
        self.assertIn("draft", findings[0])

    def test_blank_approver_is_a_draft(self):
        self.assertEqual(len(approval_findings(sample_plan(approved_by="  "))), 1)

    def test_unrecognised_authority_is_flagged(self):
        findings = approval_findings(sample_plan(approved_by="design engineer"))
        self.assertTrue(any("not a recognised" in f for f in findings))

    def test_missing_approval_date_is_flagged(self):
        findings = approval_findings(sample_plan(approval_date=None))
        self.assertTrue(any("no date" in f for f in findings))

    def test_approval_before_issue_is_flagged(self):
        findings = approval_findings(sample_plan(approval_date="2026-02-01"))
        self.assertTrue(any("predates" in f for f in findings))

    def test_empty_authority_list_rejected(self):
        with self.assertRaises(ValueError):
            approval_findings(sample_plan(recognised_authorities=[]))


class CurrencyTests(unittest.TestCase):
    def test_plan_issued_after_the_last_change_is_current(self):
        self.assertEqual(currency_findings(sample_plan()), [])

    def test_plan_predating_a_configuration_change_is_flagged(self):
        findings = currency_findings(
            sample_plan(last_configuration_change="2026-05-01")
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("no longer reflects", findings[0])

    def test_change_on_the_issue_date_is_still_current(self):
        self.assertEqual(
            currency_findings(sample_plan(last_configuration_change="2026-03-01")), []
        )

    def test_no_declared_change_leaves_the_plan_current(self):
        self.assertEqual(
            currency_findings(sample_plan(last_configuration_change=None)), []
        )


class ReviewTests(unittest.TestCase):
    def test_elapsed_days_measured_from_the_issue(self):
        status = review_status(sample_plan(), AS_OF)
        self.assertEqual(status["elapsed_days"], 202)

    def test_review_within_the_interval_is_not_overdue(self):
        self.assertFalse(review_status(sample_plan(), AS_OF)["overdue"])

    def test_review_past_the_interval_is_overdue_by_the_excess(self):
        status = review_status(sample_plan(review_interval_days=180), AS_OF)
        self.assertTrue(status["overdue"])
        self.assertEqual(status["overdue_days"], 22)

    def test_review_exactly_at_the_interval_is_not_yet_overdue(self):
        status = review_status(sample_plan(review_interval_days=202), AS_OF)
        self.assertFalse(status["overdue"])
        self.assertEqual(status["overdue_days"], 0)

    def test_no_interval_means_no_periodic_review(self):
        status = review_status(sample_plan(review_interval_days=None), AS_OF)
        self.assertFalse(status["applicable"])
        self.assertFalse(status["overdue"])

    def test_as_of_before_the_issue_rejected(self):
        with self.assertRaises(ValueError):
            review_status(sample_plan(), "2026-01-01")

    def test_non_integer_interval_rejected(self):
        with self.assertRaises(ValueError):
            review_status(sample_plan(review_interval_days=365.5), AS_OF)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            review_status(sample_plan(review_interval_days=0), AS_OF)


class TriggerTests(unittest.TestCase):
    def test_complete_triggers_produce_no_finding(self):
        self.assertEqual(trigger_findings(full_triggers()), [])

    def test_absent_trigger_is_flagged(self):
        triggers = full_triggers()
        del triggers["cleanliness-non-conformance"]
        findings = trigger_findings(triggers)
        self.assertEqual(len(findings), 1)
        self.assertIn("cleanliness-non-conformance", findings[0])

    def test_trigger_without_an_owner_is_flagged(self):
        triggers = full_triggers()
        triggers["design-change"]["owner"] = "  "
        self.assertTrue(any("no owner" in f for f in trigger_findings(triggers)))

    def test_trigger_without_an_action_is_flagged(self):
        triggers = full_triggers()
        del triggers["design-change"]["action"]
        self.assertTrue(any("no action" in f for f in trigger_findings(triggers)))

    def test_no_triggers_at_all_flags_every_required_one(self):
        self.assertEqual(len(trigger_findings(None)), len(REQUIRED_TRIGGERS))

    def test_unknown_trigger_rejected(self):
        triggers = full_triggers()
        triggers["weather"] = {"action": "wait", "owner": "PA manager"}
        with self.assertRaises(ValueError):
            trigger_findings(triggers)

    def test_non_mapping_response_rejected(self):
        triggers = full_triggers()
        triggers["design-change"] = "re-issue"
        with self.assertRaises(ValueError):
            trigger_findings(triggers)


class AssessControlPlanTests(unittest.TestCase):
    def test_sound_plan_is_the_controlling_document(self):
        result = assess_control_plan(sample_plan(), AS_OF)
        self.assertTrue(result["controlling"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["completeness"], 1.0, places=9)

    def test_missing_section_is_reported_and_blocks_the_plan(self):
        plan = sample_plan()
        del plan["sections"]["monitoring-and-witness-samples"]
        result = assess_control_plan(plan, AS_OF)
        self.assertFalse(result["controlling"])
        self.assertEqual(result["content_gaps"], ["monitoring-and-witness-samples"])

    def test_phase_gap_is_reported(self):
        plan = sample_plan(phases=["design", "manufacturing"])
        result = assess_control_plan(plan, AS_OF)
        self.assertEqual(len(result["phase_gaps"]), 3)

    def test_draft_plan_is_not_controlling(self):
        result = assess_control_plan(sample_plan(approved_by=None), AS_OF)
        self.assertFalse(result["controlling"])

    def test_stale_plan_is_not_controlling(self):
        plan = sample_plan(last_configuration_change="2026-08-01")
        result = assess_control_plan(plan, AS_OF)
        self.assertFalse(result["controlling"])
        self.assertTrue(any("no longer reflects" in f for f in result["findings"]))

    def test_overdue_review_is_reported_in_days(self):
        plan = sample_plan(review_interval_days=100)
        result = assess_control_plan(plan, AS_OF)
        self.assertTrue(any("102 days overdue" in f for f in result["findings"]))

    def test_as_of_defaults_to_the_issue_date(self):
        result = assess_control_plan(sample_plan())
        self.assertEqual(result["review"]["elapsed_days"], 0)
        self.assertTrue(result["controlling"])

    def test_issue_label_is_carried_through(self):
        self.assertEqual(
            assess_control_plan(sample_plan(), AS_OF)["issue"], "issue 3 revision 0"
        )

    def test_blank_title_rejected(self):
        with self.assertRaises(ValueError):
            assess_control_plan(sample_plan(title="  "), AS_OF)

    def test_blank_issue_label_rejected(self):
        with self.assertRaises(ValueError):
            assess_control_plan(sample_plan(issue=""), AS_OF)

    def test_missing_plan_key_rejected(self):
        plan = sample_plan()
        del plan["sections"]
        with self.assertRaises(ValueError):
            assess_control_plan(plan, AS_OF)

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            assess_control_plan(["title"], AS_OF)

    def test_several_defects_are_all_reported(self):
        plan = sample_plan(approved_by=None, phases=["design"])
        del plan["sections"]["design-provisions"]
        result = assess_control_plan(plan, AS_OF)
        self.assertGreaterEqual(len(result["findings"]), 6)


if __name__ == "__main__":
    unittest.main()
