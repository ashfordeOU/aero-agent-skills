"""Contract tests for the Annex E storage/handling/transport deliverable schedule."""

import unittest
from datetime import date

from q2008_review_deliverables_logic import (
    DEFAULT_LEAD_WORKING_DAYS,
    DELIVERABLES,
    REVIEW_ORDER,
    anchor_review,
    assess_review_deliverables,
    due_day,
    grade_deliverable,
    normalise_identifier,
    parse_day,
    review_index,
    subtract_working_days,
    validate_reviews,
    validate_submissions,
)

# Every milestone falls on a Monday, so a twenty working day lead lands four
# calendar weeks earlier and the expected days can be written down by hand.
MILESTONES = {
    "prr": "2026-01-12",
    "srr": "2026-02-09",
    "pdr": "2026-03-09",
    "cdr": "2026-05-11",
    "qr": "2026-07-13",
    "ar": "2026-09-14",
    "orr": "2026-10-12",
    "frr": "2026-11-09",
}


def reviews(*names):
    chosen = names or tuple(MILESTONES)
    return [{"review": n, "day": MILESTONES[n]} for n in chosen]


def submissions(**pairs):
    return [{"deliverable": k.replace("_", "-"), "day": v} for k, v in pairs.items()]


class NormaliseTests(unittest.TestCase):
    def test_trims_and_lowercases(self):
        self.assertEqual(normalise_identifier("  CDR ", "x"), "cdr")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalise_identifier(None, "x")


class DayParsingTests(unittest.TestCase):
    def test_iso_string_parsed(self):
        self.assertEqual(parse_day("2026-03-09", "x"), date(2026, 3, 9))

    def test_date_object_passes_through(self):
        self.assertEqual(parse_day(date(2026, 3, 9), "x"), date(2026, 3, 9))

    def test_malformed_day_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("09/03/2026", "x")

    def test_non_string_day_rejected(self):
        with self.assertRaises(ValueError):
            parse_day(20260309, "x")


class ReviewOrderTests(unittest.TestCase):
    def test_indices_follow_the_declared_sequence(self):
        self.assertEqual([review_index(r) for r in REVIEW_ORDER], list(range(len(REVIEW_ORDER))))

    def test_pdr_precedes_cdr(self):
        self.assertLess(review_index("pdr"), review_index("cdr"))

    def test_unknown_review_rejected(self):
        with self.assertRaises(ValueError):
            review_index("lrr")

    def test_every_deliverable_is_anchored_to_a_known_review(self):
        for name, (listed, _expected) in DELIVERABLES.items():
            self.assertIn(listed, REVIEW_ORDER, name)


class WorkingDayTests(unittest.TestCase):
    def test_twenty_working_days_before_a_monday_is_four_weeks(self):
        self.assertEqual(subtract_working_days(date(2026, 3, 9), 20), date(2026, 2, 9))

    def test_one_working_day_before_a_monday_is_the_friday(self):
        self.assertEqual(subtract_working_days(date(2026, 3, 9), 1), date(2026, 3, 6))

    def test_zero_working_days_is_the_same_day(self):
        self.assertEqual(subtract_working_days(date(2026, 3, 9), 0), date(2026, 3, 9))

    def test_result_never_lands_on_a_weekend(self):
        for offset in range(1, 30):
            self.assertLess(subtract_working_days(date(2026, 3, 9), offset).weekday(), 5)

    def test_negative_lead_rejected(self):
        with self.assertRaises(ValueError):
            subtract_working_days(date(2026, 3, 9), -1)

    def test_non_integer_lead_rejected(self):
        with self.assertRaises(ValueError):
            subtract_working_days(date(2026, 3, 9), 2.0)

    def test_non_date_rejected(self):
        with self.assertRaises(ValueError):
            subtract_working_days("2026-03-09", 5)


class ReviewValidationTests(unittest.TestCase):
    def test_reviews_are_keyed_and_parsed(self):
        held = validate_reviews(reviews("pdr", "cdr"))
        self.assertEqual(held["pdr"], date(2026, 3, 9))

    def test_duplicate_review_rejected(self):
        with self.assertRaises(ValueError):
            validate_reviews(reviews("pdr") + reviews("pdr"))

    def test_unknown_review_rejected(self):
        with self.assertRaises(ValueError):
            validate_reviews([{"review": "lrr", "day": "2026-03-09"}])

    def test_backwards_dated_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_reviews([
                {"review": "pdr", "day": "2026-05-11"},
                {"review": "cdr", "day": "2026-03-09"},
            ])

    def test_empty_review_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_reviews([])


class SubmissionValidationTests(unittest.TestCase):
    def test_planned_day_is_parsed(self):
        planned = validate_submissions(submissions(container_design_report="2026-04-01"))
        self.assertEqual(planned["container-design-report"], date(2026, 4, 1))

    def test_unknown_deliverable_rejected(self):
        with self.assertRaises(ValueError):
            validate_submissions([{"deliverable": "launch-campaign-plan", "day": "2026-04-01"}])

    def test_duplicate_deliverable_rejected(self):
        with self.assertRaises(ValueError):
            validate_submissions(
                submissions(container_design_report="2026-04-01")
                + submissions(container_design_report="2026-04-02")
            )

    def test_absent_submissions_are_empty(self):
        self.assertEqual(validate_submissions(None), {})


class AnchoringTests(unittest.TestCase):
    def test_held_review_is_the_anchor(self):
        held = validate_reviews(reviews())
        self.assertEqual(anchor_review("container-design-report", held), ("cdr", False))

    def test_missing_review_reanchors_to_the_nearest_earlier_one(self):
        held = validate_reviews(reviews("pdr", "qr", "ar", "orr"))
        self.assertEqual(anchor_review("container-design-report", held), ("pdr", True))

    def test_no_earlier_review_leaves_the_deliverable_unanchored(self):
        held = validate_reviews(reviews("orr"))
        self.assertEqual(anchor_review("storage-handling-transport-plan", held), (None, True))

    def test_unknown_deliverable_rejected(self):
        held = validate_reviews(reviews())
        with self.assertRaises(ValueError):
            anchor_review("launch-campaign-plan", held)


class DueDayTests(unittest.TestCase):
    def test_default_lead_is_twenty_working_days(self):
        self.assertEqual(DEFAULT_LEAD_WORKING_DAYS, 20)

    def test_due_day_uses_the_lead(self):
        self.assertEqual(due_day(date(2026, 5, 11)), date(2026, 4, 13))

    def test_shorter_lead_moves_the_due_day_later(self):
        self.assertGreater(due_day(date(2026, 5, 11), 5), due_day(date(2026, 5, 11), 20))


class GradingTests(unittest.TestCase):
    def test_submission_before_the_due_day_is_on_time(self):
        held = validate_reviews(reviews())
        planned = validate_submissions(submissions(container_design_report="2026-04-01"))
        record = grade_deliverable("container-design-report", held, planned)
        self.assertEqual(record["status"], "on-time")
        self.assertEqual(record["due_day"], date(2026, 4, 13))

    def test_submission_exactly_on_the_due_day_is_on_time(self):
        held = validate_reviews(reviews())
        planned = validate_submissions(submissions(container_design_report="2026-04-13"))
        record = grade_deliverable("container-design-report", held, planned)
        self.assertEqual(record["status"], "on-time")
        self.assertEqual(record["slack_days"], 0)

    def test_submission_after_the_due_day_is_late(self):
        held = validate_reviews(reviews())
        planned = validate_submissions(submissions(container_design_report="2026-05-01"))
        record = grade_deliverable("container-design-report", held, planned)
        self.assertEqual(record["status"], "late")
        self.assertLess(record["slack_days"], 0)

    def test_unplanned_deliverable_is_reported(self):
        held = validate_reviews(reviews())
        record = grade_deliverable("container-design-report", held, {})
        self.assertEqual(record["status"], "not-planned")

    def test_unknown_deliverable_rejected(self):
        held = validate_reviews(reviews())
        with self.assertRaises(ValueError):
            grade_deliverable("launch-campaign-plan", held, {})


class AssessmentTests(unittest.TestCase):
    def all_on_time(self):
        held = validate_reviews(reviews())
        plan = []
        for name in DELIVERABLES:
            record = grade_deliverable(name, held, {})
            plan.append({"deliverable": name, "day": record["due_day"].isoformat()})
        return plan

    def test_fully_planned_schedule_is_accepted(self):
        result = assess_review_deliverables({
            "reviews": reviews(), "submissions": self.all_on_time()
        })
        self.assertEqual(result["decision"], "schedule-accepted")
        self.assertAlmostEqual(result["on_time_fraction"], 1.0, places=9)

    def test_schedule_is_ordered_by_due_day(self):
        result = assess_review_deliverables({
            "reviews": reviews(), "submissions": self.all_on_time()
        })
        days = [r["due_day"] for r in result["schedule"]]
        self.assertEqual(days, sorted(days))

    def test_unplanned_expected_deliverable_rejects_the_schedule(self):
        plan = [p for p in self.all_on_time()
                if p["deliverable"] != "transport-readiness-statement"]
        result = assess_review_deliverables({"reviews": reviews(), "submissions": plan})
        self.assertEqual(result["decision"], "schedule-rejected")
        self.assertEqual(
            [f["code"] for f in result["blocking_findings"]], ["deliverable-not-planned"]
        )

    def test_unplanned_optional_deliverable_is_advisory_only(self):
        plan = [p for p in self.all_on_time()
                if p["deliverable"] != "long-term-storage-extension-request"]
        result = assess_review_deliverables({"reviews": reviews(), "submissions": plan})
        self.assertEqual(result["decision"], "schedule-accepted")
        self.assertIn("deliverable-not-planned", [f["code"] for f in result["findings"]])

    def test_reanchoring_is_reported_when_a_review_is_not_held(self):
        result = assess_review_deliverables({"reviews": reviews("pdr", "qr", "ar", "orr")})
        codes = [f["code"] for f in result["findings"]]
        self.assertIn("deliverable-reanchored", codes)

    def test_deliverable_with_no_earlier_review_blocks(self):
        result = assess_review_deliverables({"reviews": reviews("orr")})
        codes = [f["code"] for f in result["blocking_findings"]]
        self.assertIn("deliverable-has-no-anchor-review", codes)

    def test_lead_is_carried_into_the_result(self):
        result = assess_review_deliverables({"reviews": reviews(), "lead_working_days": 10})
        self.assertEqual(result["lead_working_days"], 10)
        self.assertEqual(
            result["records"]["container-design-report"]["due_day"],
            due_day(date(2026, 5, 11), 10),
        )

    def test_negative_lead_rejected(self):
        with self.assertRaises(ValueError):
            assess_review_deliverables({"reviews": reviews(), "lead_working_days": -5})

    def test_missing_reviews_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_review_deliverables({"submissions": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_review_deliverables(["reviews"])


if __name__ == "__main__":
    unittest.main(verbosity=0)
