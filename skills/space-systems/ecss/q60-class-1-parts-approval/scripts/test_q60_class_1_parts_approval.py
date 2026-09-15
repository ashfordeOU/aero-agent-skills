"""Contract tests for the clause 4.2.4 class 1 parts-approval logic."""

import datetime
import unittest

from q60_class_1_parts_approval_logic import (
    DISPOSITIONS,
    MANDATORY_EVIDENCE,
    RELEASING_DISPOSITIONS,
    approval_age_days,
    assess_approval_round,
    assess_submission,
    missing_evidence,
    normalize_token,
    open_conditions,
    parse_review_date,
    unsubmitted_parts,
    validate_approver,
    validate_submission,
)

REVIEW_DATE = "2026-06-30"
ROSTER = ["A. Reviewer", "B. Reviewer"]


def _context(**overrides):
    context = {
        "review_date": REVIEW_DATE,
        "authorized_approvers": list(ROSTER),
        "validity_days": 365,
    }
    context.update(overrides)
    return context


def _submission(**overrides):
    submission = {
        "part_number": "EM-7712-CL1",
        "manufacturer": "Example Microelectronics",
        "submitter_organisation": "prime-contractor",
        "evidence": list(MANDATORY_EVIDENCE),
        "disposition": "approved",
        "approver": {"name": "A. Reviewer", "organisation": "customer-agency"},
        "decision_date": "2026-05-01",
    }
    submission.update(overrides)
    return submission


def _spec(**overrides):
    spec = {
        "proposed_parts": ["EM-7712-CL1"],
        "submissions": [_submission()],
        "review_date": REVIEW_DATE,
        "authorized_approvers": list(ROSTER),
        "validity_days": 365,
    }
    spec.update(overrides)
    return spec


class SubmissionValidationTests(unittest.TestCase):
    def test_valid_submission_returned(self):
        record = validate_submission(_submission())
        self.assertEqual(record["part_number"], "EM-7712-CL1")
        self.assertEqual(record["disposition"], "approved")

    def test_disposition_normalized(self):
        record = validate_submission(_submission(disposition="Approved With Conditions",
                                                 conditions=[{"reference": "ncr-11"}]))
        self.assertEqual(record["disposition"], "approved-with-conditions")

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            validate_submission(_submission(disposition="noted"))

    def test_blank_part_number_rejected(self):
        with self.assertRaises(ValueError):
            validate_submission(_submission(part_number="   "))

    def test_missing_manufacturer_rejected(self):
        bad = _submission()
        del bad["manufacturer"]
        with self.assertRaises(ValueError):
            validate_submission(bad)

    def test_evidence_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_submission(_submission(evidence="part-identity"))

    def test_duplicate_evidence_item_rejected(self):
        with self.assertRaises(ValueError):
            validate_submission(_submission(evidence=["part-identity", "part_identity"]))

    def test_duplicate_condition_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_submission(_submission(
                disposition="approved-with-conditions",
                conditions=[{"reference": "ncr-11"}, {"reference": "NCR 11"}]))

    def test_non_boolean_closure_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_submission(_submission(
                disposition="approved-with-conditions",
                conditions=[{"reference": "ncr-11", "closed": "yes"}]))

    def test_non_mapping_submission_rejected(self):
        with self.assertRaises(ValueError):
            validate_submission(["EM-7712-CL1"])

    def test_token_normalization_is_hyphenated_lower_case(self):
        self.assertEqual(normalize_token("Procurement_Specification"),
                         "procurement-specification")


class ApproverAndDateTests(unittest.TestCase):
    def test_approver_organisation_normalized(self):
        approver = validate_approver({"name": "A. Reviewer",
                                      "organisation": "Customer Agency"})
        self.assertEqual(approver["organisation"], "customer-agency")

    def test_approver_without_organisation_rejected(self):
        with self.assertRaises(ValueError):
            validate_approver({"name": "A. Reviewer"})

    def test_iso_day_parsed(self):
        self.assertEqual(parse_review_date("2026-05-01"), datetime.date(2026, 5, 1))

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_review_date("01/05/2026")

    def test_age_in_whole_days(self):
        self.assertEqual(approval_age_days("2026-05-01", "2026-05-31"), 30)

    def test_same_day_sign_off_is_zero_days_old(self):
        self.assertEqual(approval_age_days("2026-06-30", REVIEW_DATE), 0)

    def test_future_dated_sign_off_rejected(self):
        with self.assertRaises(ValueError):
            approval_age_days("2026-07-01", REVIEW_DATE)


class EvidenceAndConditionTests(unittest.TestCase):
    def test_complete_evidence_package_has_no_gap(self):
        self.assertEqual(missing_evidence(_submission()), [])

    def test_absent_evidence_item_reported(self):
        evidence = [i for i in MANDATORY_EVIDENCE if i != "evaluation-record"]
        self.assertEqual(missing_evidence(_submission(evidence=evidence)),
                         ["evaluation-record"])

    def test_missing_evidence_preserves_mandatory_order(self):
        self.assertEqual(missing_evidence(_submission(evidence=[])),
                         list(MANDATORY_EVIDENCE))

    def test_open_condition_reported(self):
        submission = _submission(disposition="approved-with-conditions",
                                 conditions=[{"reference": "ncr-11", "closed": True},
                                             {"reference": "ncr-12"}])
        self.assertEqual(open_conditions(submission), ["ncr-12"])

    def test_all_conditions_closed_leaves_nothing_open(self):
        submission = _submission(disposition="approved-with-conditions",
                                 conditions=[{"reference": "ncr-11", "closed": True}])
        self.assertEqual(open_conditions(submission), [])

    def test_releasing_dispositions_are_a_subset_of_all_dispositions(self):
        for name in RELEASING_DISPOSITIONS:
            self.assertIn(name, DISPOSITIONS)


class SubmissionVerdictTests(unittest.TestCase):
    def test_complete_submission_releases_the_part(self):
        record = assess_submission(_submission(), _context())
        self.assertTrue(record["released"])
        self.assertEqual(record["findings"], [])

    def test_absent_evidence_blocks_release(self):
        evidence = [i for i in MANDATORY_EVIDENCE if i != "application-data"]
        record = assess_submission(_submission(evidence=evidence), _context())
        self.assertFalse(record["released"])
        self.assertIn("application-data", record["missing_evidence"])

    def test_unsigned_submission_blocks_release(self):
        submission = _submission()
        del submission["approver"]
        record = assess_submission(submission, _context())
        self.assertFalse(record["released"])

    def test_signatory_off_the_roster_blocks_release(self):
        record = assess_submission(
            _submission(approver={"name": "C. Outsider",
                                  "organisation": "customer-agency"}), _context())
        self.assertFalse(record["released"])

    def test_signatory_inside_the_submitting_organisation_blocks_release(self):
        record = assess_submission(
            _submission(approver={"name": "A. Reviewer",
                                  "organisation": "Prime Contractor"}), _context())
        self.assertFalse(record["released"])

    def test_undated_sign_off_blocks_release(self):
        submission = _submission()
        del submission["decision_date"]
        record = assess_submission(submission, _context())
        self.assertFalse(record["released"])
        self.assertIsNone(record["age_days"])

    def test_sign_off_exactly_at_the_validity_limit_still_releases(self):
        record = assess_submission(_submission(decision_date="2026-05-01"),
                                   _context(validity_days=60))
        self.assertEqual(record["age_days"], 60)
        self.assertTrue(record["released"])

    def test_sign_off_past_the_validity_window_blocks_release(self):
        record = assess_submission(_submission(decision_date="2026-05-01"),
                                   _context(validity_days=30))
        self.assertFalse(record["released"])

    def test_rejected_disposition_blocks_release(self):
        record = assess_submission(_submission(disposition="rejected"), _context())
        self.assertFalse(record["released"])

    def test_pending_disposition_blocks_release(self):
        record = assess_submission(_submission(disposition="pending"), _context())
        self.assertFalse(record["released"])

    def test_conditional_approval_with_open_condition_blocks_release(self):
        record = assess_submission(
            _submission(disposition="approved-with-conditions",
                        conditions=[{"reference": "ncr-11"}]), _context())
        self.assertFalse(record["released"])
        self.assertEqual(record["open_conditions"], ["ncr-11"])

    def test_conditional_approval_with_closed_conditions_releases(self):
        record = assess_submission(
            _submission(disposition="approved-with-conditions",
                        conditions=[{"reference": "ncr-11", "closed": True}]), _context())
        self.assertTrue(record["released"])

    def test_conditional_approval_listing_no_conditions_rejected(self):
        with self.assertRaises(ValueError):
            assess_submission(_submission(disposition="approved-with-conditions"),
                              _context())

    def test_empty_approver_roster_rejected(self):
        with self.assertRaises(ValueError):
            assess_submission(_submission(), _context(authorized_approvers=[]))

    def test_zero_validity_window_rejected(self):
        with self.assertRaises(ValueError):
            assess_submission(_submission(), _context(validity_days=0))

    def test_every_shortfall_is_named_not_only_the_first(self):
        record = assess_submission(
            _submission(evidence=[], disposition="pending",
                        approver={"name": "C. Outsider",
                                  "organisation": "prime-contractor"}), _context())
        self.assertGreaterEqual(len(record["findings"]), 6)


class ApprovalRoundTests(unittest.TestCase):
    def test_clean_round_releases_every_proposed_part(self):
        result = assess_approval_round(_spec())
        self.assertTrue(result["round_clean"])
        self.assertEqual(result["released_count"], 1)

    def test_proposed_part_never_submitted_is_a_finding(self):
        result = assess_approval_round(_spec(proposed_parts=["EM-7712-CL1", "EM-9004-CL1"]))
        self.assertEqual(result["unsubmitted_parts"], ["EM-9004-CL1"])
        self.assertFalse(result["round_clean"])

    def test_unsubmitted_parts_reports_each_name_once(self):
        records = [{"part_number": "EM-7712-CL1"}]
        self.assertEqual(
            unsubmitted_parts(["EM-9004-CL1", "EM-9004-CL1", "EM-7712-CL1"], records),
            ["EM-9004-CL1"])

    def test_unsubmitted_parts_rejects_malformed_record(self):
        with self.assertRaises(ValueError):
            unsubmitted_parts(["EM-7712-CL1"], [{"manufacturer": "Example"}])

    def test_duplicate_submission_rejected(self):
        result_spec = _spec(submissions=[_submission(), _submission()])
        with self.assertRaises(ValueError):
            assess_approval_round(result_spec)

    def test_empty_proposed_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_approval_round(_spec(proposed_parts=[]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["validity_days"]
        with self.assertRaises(ValueError):
            assess_approval_round(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_approval_round(["proposed_parts"])

    def test_blocked_part_is_not_counted_as_released(self):
        result = assess_approval_round(
            _spec(submissions=[_submission(disposition="rejected")]))
        self.assertEqual(result["released_count"], 0)
        self.assertEqual(result["released_parts"], [])

    def test_round_reports_the_proposed_count(self):
        result = assess_approval_round(_spec(proposed_parts=["EM-7712-CL1",
                                                             "EM-9004-CL1"]))
        self.assertEqual(result["proposed_count"], 2)


if __name__ == "__main__":
    unittest.main()
