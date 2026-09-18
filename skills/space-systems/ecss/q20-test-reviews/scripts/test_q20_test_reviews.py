"""Contract tests for the clause 5.6.5 test-review logic."""

import unittest
from datetime import date

from q20_test_reviews_logic import (
    CRITERION_STATES,
    MANDATORY_PTR_CRITERIA,
    MANDATORY_TRR_CRITERIA,
    PTR_CRITERIA,
    REQUIRED_ATTENDEES,
    REVIEW_KINDS,
    TRR_CRITERIA,
    assess_review,
    assess_review_pair,
    criteria_for_kind,
    criterion_findings,
    mandatory_for_kind,
    normalise_identifier,
    parse_iso_date,
    readiness_fraction,
    record_findings,
    schedule_findings,
    validate_review,
)

TEST_START = "2026-06-01"
TEST_END = "2026-06-05"


def trr(**overrides):
    """Return a clean readiness review with overrides applied."""
    review = {
        "kind": "trr",
        "held_on": "2026-05-28",
        "criteria": [{"id": name, "state": "met"} for name in TRR_CRITERIA],
        "attendees": ["chair", "product-assurance", "test-conductor"],
        "actions": [],
        "minutes_reference": "min-trr-014",
    }
    review.update(overrides)
    return review


def ptr(**overrides):
    """Return a clean post-test review with overrides applied."""
    review = {
        "kind": "ptr",
        "held_on": "2026-06-09",
        "criteria": [{"id": name, "state": "met"} for name in PTR_CRITERIA],
        "attendees": ["chair", "product-assurance"],
        "actions": [],
        "minutes_reference": "min-ptr-014",
    }
    review.update(overrides)
    return review


class VocabularyTests(unittest.TestCase):
    def test_review_kinds(self):
        self.assertEqual(REVIEW_KINDS, ("trr", "ptr"))

    def test_criterion_states(self):
        self.assertEqual(CRITERION_STATES, ("met", "not-met", "waived"))

    def test_required_attendees(self):
        self.assertEqual(REQUIRED_ATTENDEES, ("chair", "product-assurance"))

    def test_criteria_for_kind_selects_the_right_list(self):
        self.assertEqual(criteria_for_kind("trr"), TRR_CRITERIA)
        self.assertEqual(criteria_for_kind("ptr"), PTR_CRITERIA)

    def test_mandatory_subsets_sit_inside_their_lists(self):
        self.assertTrue(set(MANDATORY_TRR_CRITERIA).issubset(set(TRR_CRITERIA)))
        self.assertTrue(set(MANDATORY_PTR_CRITERIA).issubset(set(PTR_CRITERIA)))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            criteria_for_kind("crr")

    def test_mandatory_for_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            mandatory_for_kind("crr")


class HelperTests(unittest.TestCase):
    def test_identifier_normalised(self):
        self.assertEqual(normalise_identifier(" Chair ", "role"), "chair")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(None, "role")

    def test_iso_date_parsed(self):
        self.assertEqual(parse_iso_date("2026-06-01", "d"), date(2026, 6, 1))

    def test_bad_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_iso_date("2026-06", "d")


class ValidationTests(unittest.TestCase):
    def test_clean_review_validates(self):
        record = validate_review(trr())
        self.assertEqual(record["kind"], "trr")
        self.assertEqual(len(record["criteria"]), len(TRR_CRITERIA))

    def test_foreign_criterion_rejected(self):
        bad = [{"id": "report-issued", "state": "met"}]
        with self.assertRaises(ValueError):
            validate_review(trr(criteria=bad))

    def test_duplicate_criterion_rejected(self):
        bad = [
            {"id": "procedure-approved", "state": "met"},
            {"id": "procedure-approved", "state": "not-met"},
        ]
        with self.assertRaises(ValueError):
            validate_review(trr(criteria=bad))

    def test_unknown_state_rejected(self):
        bad = [{"id": "procedure-approved", "state": "pending"}]
        with self.assertRaises(ValueError):
            validate_review(trr(criteria=bad))

    def test_empty_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_review(trr(criteria=[]))

    def test_duplicate_action_rejected(self):
        action = {"id": "a-01", "owner": "engineering", "due_date": "2026-05-30"}
        with self.assertRaises(ValueError):
            validate_review(trr(actions=[action, dict(action)]))

    def test_non_mapping_review_rejected(self):
        with self.assertRaises(ValueError):
            validate_review("trr")


class CriterionTests(unittest.TestCase):
    def test_all_met_gives_no_finding(self):
        self.assertEqual(criterion_findings(validate_review(trr())), [])

    def test_unaddressed_criterion_is_a_finding(self):
        thin = [{"id": name, "state": "met"} for name in TRR_CRITERIA[:-1]]
        findings = criterion_findings(validate_review(trr(criteria=thin)))
        self.assertIn("never addressed", findings[0])

    def test_not_met_criterion_is_a_finding(self):
        criteria = [{"id": name, "state": "met"} for name in TRR_CRITERIA]
        criteria[0] = {"id": TRR_CRITERIA[0], "state": "not-met"}
        findings = criterion_findings(validate_review(trr(criteria=criteria)))
        self.assertEqual(findings, ["criterion procedure-approved is not met"])

    def test_waiver_on_a_mandatory_criterion_is_refused(self):
        criteria = [{"id": name, "state": "met"} for name in TRR_CRITERIA]
        criteria[3] = {
            "id": "safety-clearance-granted",
            "state": "waived",
            "waiver_reference": "wvr-7",
            "waiver_approver": "product-assurance",
        }
        findings = criterion_findings(validate_review(trr(criteria=criteria)))
        self.assertIn("cannot be waived", findings[0])

    def test_waiver_on_a_non_mandatory_criterion_is_accepted(self):
        criteria = [{"id": name, "state": "met"} for name in TRR_CRITERIA]
        criteria[-1] = {
            "id": "personnel-assigned",
            "state": "waived",
            "waiver_reference": "wvr-9",
            "waiver_approver": "product-assurance",
        }
        self.assertEqual(criterion_findings(validate_review(trr(criteria=criteria))), [])

    def test_waiver_without_a_reference_is_a_finding(self):
        criteria = [{"id": name, "state": "met"} for name in TRR_CRITERIA]
        criteria[-1] = {
            "id": "personnel-assigned",
            "state": "waived",
            "waiver_approver": "product-assurance",
        }
        findings = criterion_findings(validate_review(trr(criteria=criteria)))
        self.assertEqual(findings, ["waiver on personnel-assigned carries no reference"])

    def test_waiver_without_an_approver_is_a_finding(self):
        criteria = [{"id": name, "state": "met"} for name in PTR_CRITERIA]
        criteria[-1] = {
            "id": "article-post-test-inspection",
            "state": "waived",
            "waiver_reference": "wvr-11",
        }
        findings = criterion_findings(validate_review(ptr(criteria=criteria)))
        self.assertEqual(findings, ["waiver on article-post-test-inspection carries no approver"])


class RecordTests(unittest.TestCase):
    def test_clean_record_gives_no_finding(self):
        self.assertEqual(record_findings(validate_review(trr())), [])

    def test_missing_product_assurance_is_a_finding(self):
        findings = record_findings(validate_review(trr(attendees=["chair"])))
        self.assertEqual(findings, ["review was held without product-assurance"])

    def test_missing_minutes_is_a_finding(self):
        findings = record_findings(validate_review(trr(minutes_reference=None)))
        self.assertEqual(findings, ["review records no minutes reference"])

    def test_open_blocking_action_is_a_finding(self):
        actions = [
            {"id": "a-01", "owner": "engineering", "due_date": "2026-05-30", "blocking": True}
        ]
        findings = record_findings(validate_review(trr(actions=actions)))
        self.assertIn("blocking actions still open", findings[0])

    def test_open_non_blocking_action_is_tolerated(self):
        actions = [
            {"id": "a-02", "owner": "engineering", "due_date": "2026-05-30", "blocking": False}
        ]
        self.assertEqual(record_findings(validate_review(trr(actions=actions))), [])


class ScheduleTests(unittest.TestCase):
    def test_readiness_review_before_the_test_is_clean(self):
        self.assertEqual(
            schedule_findings(validate_review(trr()), TEST_START, TEST_END), []
        )

    def test_readiness_review_after_the_start_is_a_finding(self):
        record = validate_review(trr(held_on="2026-06-03"))
        self.assertIn("after the test started", schedule_findings(record, TEST_START, TEST_END)[0])

    def test_post_test_review_after_the_end_is_clean(self):
        self.assertEqual(schedule_findings(validate_review(ptr()), TEST_START, TEST_END), [])

    def test_post_test_review_before_the_end_is_a_finding(self):
        record = validate_review(ptr(held_on="2026-06-02"))
        self.assertIn("before the test ended", schedule_findings(record, TEST_START, TEST_END)[0])

    def test_inverted_test_window_rejected(self):
        with self.assertRaises(ValueError):
            schedule_findings(validate_review(trr()), TEST_END, TEST_START)


class FractionTests(unittest.TestCase):
    def test_all_met_gives_one(self):
        self.assertAlmostEqual(readiness_fraction(validate_review(trr())), 1.0, places=9)

    def test_one_not_met_lowers_the_fraction(self):
        criteria = [{"id": name, "state": "met"} for name in TRR_CRITERIA]
        criteria[0] = {"id": TRR_CRITERIA[0], "state": "not-met"}
        value = readiness_fraction(validate_review(trr(criteria=criteria)))
        self.assertAlmostEqual(value, (len(TRR_CRITERIA) - 1) / float(len(TRR_CRITERIA)), places=9)

    def test_waived_criterion_counts_as_cleared(self):
        criteria = [{"id": name, "state": "met"} for name in TRR_CRITERIA]
        criteria[-1] = {
            "id": "personnel-assigned",
            "state": "waived",
            "waiver_reference": "wvr-9",
            "waiver_approver": "product-assurance",
        }
        self.assertAlmostEqual(readiness_fraction(validate_review(trr(criteria=criteria))), 1.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_clean_readiness_review_is_go(self):
        result = assess_review(trr(), TEST_START, TEST_END)
        self.assertEqual(result["decision"], "go")
        self.assertAlmostEqual(result["readiness_fraction"], 1.0, places=9)

    def test_readiness_review_with_a_gap_is_no_go(self):
        criteria = [{"id": name, "state": "met"} for name in TRR_CRITERIA]
        criteria[2] = {"id": "facility-and-gse-calibrated", "state": "not-met"}
        result = assess_review(trr(criteria=criteria), TEST_START, TEST_END)
        self.assertEqual(result["decision"], "no-go")

    def test_clean_post_test_review_is_closed(self):
        self.assertEqual(assess_review(ptr(), TEST_START, TEST_END)["decision"], "closed")

    def test_pair_of_clean_reviews_closes_the_test(self):
        result = assess_review_pair(trr(), ptr(), TEST_START, TEST_END)
        self.assertEqual(result["verdict"], "test-closed")
        self.assertEqual(result["findings"], [])

    def test_missing_post_test_review_leaves_the_test_open(self):
        result = assess_review_pair(trr(), None, TEST_START, TEST_END)
        self.assertEqual(result["verdict"], "test-not-closed")
        self.assertIsNone(result["post_test"])

    def test_no_go_readiness_means_the_test_never_started(self):
        result = assess_review_pair(trr(attendees=["chair"]), ptr(), TEST_START, TEST_END)
        self.assertEqual(result["verdict"], "test-not-started")

    def test_pair_refuses_a_second_readiness_review(self):
        with self.assertRaises(ValueError):
            assess_review_pair(trr(), trr(), TEST_START, TEST_END)

    def test_pair_refuses_a_post_test_review_first(self):
        with self.assertRaises(ValueError):
            assess_review_pair(ptr(), ptr(), TEST_START, TEST_END)


if __name__ == "__main__":
    unittest.main()
