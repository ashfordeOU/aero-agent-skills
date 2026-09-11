"""
Stdlib unittest for e1003_test_reviews_logic.py.
Offline, deterministic. Run: python3 test_e1003_test_reviews.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1003_test_reviews_logic import (
    OUTCOME_PASS, OUTCOME_CONDITIONAL, OUTCOME_FAIL,
    CATEGORY_MANDATORY, CATEGORY_ADVISORY,
    ReviewError,
    validate_criterion,
    categorize_criteria,
    assess_readiness_review,
    check_open_anomalies,
    assess_closeout_review,
    validate_review_record,
    aggregate_review_status,
)


def _criterion(name, category, met, evidence=""):
    return {"name": name, "category": category, "met": met, "evidence": evidence}


def _anomaly(aid, disposition):
    return {"id": aid, "disposition": disposition}


class TestValidateCriterion(unittest.TestCase):

    def test_valid_mandatory_met(self):
        c = _criterion("proc_approved", CATEGORY_MANDATORY, True)
        ok, issues = validate_criterion(c)
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_valid_advisory_unmet_with_evidence(self):
        c = _criterion("crew_standby", CATEGORY_ADVISORY, False, "waiver CR-42")
        ok, issues = validate_criterion(c)
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_missing_name_returns_issue(self):
        c = {"name": "", "category": CATEGORY_MANDATORY, "met": True}
        ok, issues = validate_criterion(c)
        self.assertFalse(ok)
        self.assertTrue(any("name" in i for i in issues))

    def test_invalid_category_returns_issue(self):
        c = _criterion("x", "urgent", True)
        ok, issues = validate_criterion(c)
        self.assertFalse(ok)
        self.assertTrue(any("unknown category" in i for i in issues))

    def test_missing_met_field_returns_issue(self):
        c = {"name": "x", "category": CATEGORY_MANDATORY}
        ok, issues = validate_criterion(c)
        self.assertFalse(ok)
        self.assertTrue(any("met" in i for i in issues))

    def test_unmet_without_evidence_returns_issue(self):
        c = _criterion("calibration_current", CATEGORY_MANDATORY, False, "")
        ok, issues = validate_criterion(c)
        self.assertFalse(ok)
        self.assertTrue(any("evidence" in i or "rationale" in i for i in issues))

    def test_non_bool_met_returns_issue(self):
        c = {"name": "x", "category": CATEGORY_MANDATORY, "met": "yes"}
        ok, issues = validate_criterion(c)
        self.assertFalse(ok)
        self.assertTrue(any("boolean" in i for i in issues))

    def test_non_dict_input(self):
        ok, issues = validate_criterion("not-a-dict")
        self.assertFalse(ok)
        self.assertTrue(any("dict" in i for i in issues))


class TestCategorizeCriteria(unittest.TestCase):

    def test_splits_into_two_groups(self):
        criteria = [
            _criterion("a", CATEGORY_MANDATORY, True),
            _criterion("b", CATEGORY_ADVISORY, True),
            _criterion("c", CATEGORY_MANDATORY, True),
        ]
        grouped = categorize_criteria(criteria)
        self.assertEqual(len(grouped[CATEGORY_MANDATORY]), 2)
        self.assertEqual(len(grouped[CATEGORY_ADVISORY]), 1)

    def test_unknown_category_excluded_from_groups(self):
        criteria = [
            _criterion("a", CATEGORY_MANDATORY, True),
            {"name": "b", "category": "bogus", "met": True},
        ]
        grouped = categorize_criteria(criteria)
        self.assertEqual(len(grouped[CATEGORY_MANDATORY]), 1)
        total = len(grouped[CATEGORY_MANDATORY]) + len(grouped[CATEGORY_ADVISORY])
        self.assertEqual(total, 1)


class TestAssessReadinessReview(unittest.TestCase):

    def _all_mandatory_criteria(self):
        return [
            _criterion("proc_approved", CATEGORY_MANDATORY, True),
            _criterion("item_accepted", CATEGORY_MANDATORY, True),
            _criterion("equip_calibrated", CATEGORY_MANDATORY, True),
            _criterion("safety_complete", CATEGORY_MANDATORY, True),
            _criterion("resources_allocated", CATEGORY_MANDATORY, True),
        ]

    def test_all_met_returns_pass(self):
        result = assess_readiness_review(self._all_mandatory_criteria())
        self.assertEqual(result["outcome"], OUTCOME_PASS)
        self.assertEqual(result["open_mandatory"], [])
        self.assertEqual(result["open_advisory"], [])

    def test_unmet_mandatory_returns_fail(self):
        criteria = self._all_mandatory_criteria()
        criteria[0] = _criterion("proc_approved", CATEGORY_MANDATORY, False, "not yet signed")
        result = assess_readiness_review(criteria)
        self.assertEqual(result["outcome"], OUTCOME_FAIL)
        self.assertIn("proc_approved", result["open_mandatory"])

    def test_unmet_advisory_only_returns_conditional(self):
        criteria = self._all_mandatory_criteria()
        criteria.append(
            _criterion("backup_crew_standby", CATEGORY_ADVISORY, False, "waiver on file")
        )
        result = assess_readiness_review(criteria)
        self.assertEqual(result["outcome"], OUTCOME_CONDITIONAL)
        self.assertIn("backup_crew_standby", result["open_advisory"])
        self.assertEqual(result["open_mandatory"], [])

    def test_multiple_unmet_mandatory_all_reported(self):
        criteria = [
            _criterion("proc_approved", CATEGORY_MANDATORY, False, "draft only"),
            _criterion("item_accepted", CATEGORY_MANDATORY, False, "NCR still open"),
            _criterion("equip_calibrated", CATEGORY_MANDATORY, True),
        ]
        result = assess_readiness_review(criteria)
        self.assertEqual(result["outcome"], OUTCOME_FAIL)
        self.assertIn("proc_approved", result["open_mandatory"])
        self.assertIn("item_accepted", result["open_mandatory"])

    def test_empty_criteria_raises_error(self):
        with self.assertRaises(ReviewError):
            assess_readiness_review([])

    def test_invalid_criterion_raises_error(self):
        criteria = [{"name": "", "category": CATEGORY_MANDATORY, "met": True}]
        with self.assertRaises(ReviewError):
            assess_readiness_review(criteria)


class TestCheckOpenAnomalies(unittest.TestCase):

    def test_all_resolved_returns_empty(self):
        anomalies = [
            _anomaly("AN-001", "RESOLVED"),
            _anomaly("AN-002", "WAIVED"),
        ]
        result = check_open_anomalies(anomalies)
        self.assertEqual(result, [])

    def test_open_anomaly_is_blocking(self):
        anomalies = [
            _anomaly("AN-001", "RESOLVED"),
            _anomaly("AN-002", "OPEN"),
        ]
        result = check_open_anomalies(anomalies)
        self.assertIn("AN-002", result)
        self.assertNotIn("AN-001", result)

    def test_ncr_open_is_blocking(self):
        anomalies = [_anomaly("AN-003", "NCR_OPEN")]
        result = check_open_anomalies(anomalies)
        self.assertIn("AN-003", result)

    def test_pending_is_blocking(self):
        anomalies = [_anomaly("AN-004", "PENDING")]
        result = check_open_anomalies(anomalies)
        self.assertIn("AN-004", result)

    def test_missing_disposition_raises_error(self):
        anomalies = [{"id": "AN-005"}]
        with self.assertRaises(ReviewError):
            check_open_anomalies(anomalies)

    def test_non_dict_anomaly_raises_error(self):
        with self.assertRaises(ReviewError):
            check_open_anomalies(["not-a-dict"])

    def test_empty_anomaly_list_returns_empty(self):
        result = check_open_anomalies([])
        self.assertEqual(result, [])


class TestAssessCloseoutReview(unittest.TestCase):

    def _tcr_criteria(self):
        return [
            _criterion("objectives_complete", CATEGORY_MANDATORY, True),
            _criterion("data_archived", CATEGORY_MANDATORY, True),
            _criterion("anomalies_dispositioned", CATEGORY_MANDATORY, True),
            _criterion("summary_drafted", CATEGORY_MANDATORY, True),
        ]

    def test_all_pass_no_anomalies_returns_pass(self):
        result = assess_closeout_review(self._tcr_criteria(), [])
        self.assertEqual(result["outcome"], OUTCOME_PASS)
        self.assertEqual(result["blocking_anomalies"], [])

    def test_blocking_anomaly_forces_fail(self):
        anomalies = [_anomaly("AN-010", "OPEN")]
        result = assess_closeout_review(self._tcr_criteria(), anomalies)
        self.assertEqual(result["outcome"], OUTCOME_FAIL)
        self.assertIn("AN-010", result["blocking_anomalies"])

    def test_resolved_anomaly_does_not_block(self):
        anomalies = [_anomaly("AN-011", "RESOLVED")]
        result = assess_closeout_review(self._tcr_criteria(), anomalies)
        self.assertEqual(result["outcome"], OUTCOME_PASS)
        self.assertEqual(result["blocking_anomalies"], [])

    def test_unmet_mandatory_criterion_with_anomaly_both_reported(self):
        criteria = self._tcr_criteria()
        criteria[0] = _criterion(
            "objectives_complete", CATEGORY_MANDATORY, False, "one objective waived"
        )
        anomalies = [_anomaly("AN-012", "OPEN")]
        result = assess_closeout_review(criteria, anomalies)
        self.assertEqual(result["outcome"], OUTCOME_FAIL)
        self.assertIn("objectives_complete", result["open_mandatory"])
        self.assertIn("AN-012", result["blocking_anomalies"])


class TestValidateReviewRecord(unittest.TestCase):

    def _valid_record(self, review_type="TRR"):
        return {
            "review_type": review_type,
            "date": "2026-09-10",
            "chair": "J. Smith",
            "attendees": ["A. Jones", "B. Patel"],
            "criteria": [_criterion("x", CATEGORY_MANDATORY, True)],
            "outcome": OUTCOME_PASS,
            "action_items": [],
        }

    def test_valid_trr_record(self):
        ok, issues = validate_review_record(self._valid_record("TRR"))
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_valid_tcr_record(self):
        ok, issues = validate_review_record(self._valid_record("TCR"))
        self.assertTrue(ok)
        self.assertEqual(issues, [])

    def test_missing_field_flagged(self):
        record = self._valid_record()
        del record["chair"]
        ok, issues = validate_review_record(record)
        self.assertFalse(ok)
        self.assertTrue(any("chair" in str(i) for i in issues))

    def test_invalid_review_type_flagged(self):
        record = self._valid_record()
        record["review_type"] = "PDR"
        ok, issues = validate_review_record(record)
        self.assertFalse(ok)
        self.assertTrue(any("review_type" in i or "PDR" in i for i in issues))

    def test_empty_attendees_flagged(self):
        record = self._valid_record()
        record["attendees"] = []
        ok, issues = validate_review_record(record)
        self.assertFalse(ok)
        self.assertTrue(any("attendees" in i for i in issues))

    def test_non_dict_input(self):
        ok, issues = validate_review_record("not-a-dict")
        self.assertFalse(ok)
        self.assertTrue(any("dict" in i for i in issues))


class TestAggregateReviewStatus(unittest.TestCase):

    def test_both_pass_returns_pass(self):
        self.assertEqual(aggregate_review_status(OUTCOME_PASS, OUTCOME_PASS), OUTCOME_PASS)

    def test_trr_fail_propagates(self):
        self.assertEqual(
            aggregate_review_status(OUTCOME_FAIL, OUTCOME_PASS), OUTCOME_FAIL
        )

    def test_tcr_fail_propagates(self):
        self.assertEqual(
            aggregate_review_status(OUTCOME_PASS, OUTCOME_FAIL), OUTCOME_FAIL
        )

    def test_both_fail_returns_fail(self):
        self.assertEqual(
            aggregate_review_status(OUTCOME_FAIL, OUTCOME_FAIL), OUTCOME_FAIL
        )

    def test_conditional_with_pass_returns_conditional(self):
        self.assertEqual(
            aggregate_review_status(OUTCOME_CONDITIONAL, OUTCOME_PASS), OUTCOME_CONDITIONAL
        )

    def test_conditional_and_fail_returns_fail(self):
        self.assertEqual(
            aggregate_review_status(OUTCOME_CONDITIONAL, OUTCOME_FAIL), OUTCOME_FAIL
        )

    def test_unknown_outcome_raises_error(self):
        with self.assertRaises(ReviewError):
            aggregate_review_status("UNKNOWN", OUTCOME_PASS)

    def test_unknown_tcr_outcome_raises_error(self):
        with self.assertRaises(ReviewError):
            aggregate_review_status(OUTCOME_PASS, "maybe")


if __name__ == "__main__":
    unittest.main()
