"""Contract tests for the clause 4.5 radiation review reporting logic."""

import datetime
import unittest

from q6015_radiation_review_milestones_logic import (
    DEPTH_MATRIX,
    DEPTH_SEQUENCE,
    EQUIPMENT_CATEGORIES,
    LEAD_TIME_WORKING_DAYS,
    REVIEW_SEQUENCE,
    as_date,
    assess_review_reporting,
    depth_rank,
    grade_submission,
    normalize_category,
    normalize_depth,
    normalize_review,
    required_depth,
    required_lead_days,
    review_index,
    submission_deadline,
    working_days_before,
)

# A Friday, so a working-day count back crosses at least one weekend.
CDR_DATE = datetime.date(2027, 3, 12)


class TokenTests(unittest.TestCase):
    def test_review_is_normalised(self):
        self.assertEqual(
            normalize_review("Critical Design Review"), "critical-design-review"
        )

    def test_unknown_review_rejected(self):
        with self.assertRaises(ValueError):
            normalize_review("tea-review")

    def test_reviews_are_ordered(self):
        self.assertLess(
            review_index("preliminary-design-review"), review_index("critical-design-review")
        )

    def test_depth_is_normalised(self):
        self.assertEqual(normalize_depth("Detailed Analysis"), "detailed-analysis")

    def test_depth_rank_increases_with_depth(self):
        self.assertLess(depth_rank("summary"), depth_rank("full-verification-dossier"))

    def test_unknown_depth_rejected(self):
        with self.assertRaises(ValueError):
            normalize_depth("a-few-slides")

    def test_category_is_normalised(self):
        self.assertEqual(normalize_category(" Category 1 "), "category-1")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_category("category-9")


class MatrixTests(unittest.TestCase):
    def test_every_category_covers_every_review(self):
        for category in EQUIPMENT_CATEGORIES:
            for review in REVIEW_SEQUENCE:
                self.assertIn(required_depth(category, review), DEPTH_SEQUENCE)

    def test_critical_equipment_reports_deeper_at_the_design_review(self):
        self.assertGreater(
            depth_rank(required_depth("category-1", "critical-design-review")),
            depth_rank(required_depth("category-3", "critical-design-review")),
        )

    def test_depth_never_decreases_along_the_project(self):
        for category in EQUIPMENT_CATEGORIES:
            ranks = [
                depth_rank(DEPTH_MATRIX[category][review]) for review in REVIEW_SEQUENCE
            ]
            self.assertEqual(ranks, sorted(ranks), category)

    def test_every_depth_has_a_lead_time(self):
        for depth in DEPTH_SEQUENCE:
            self.assertIn(depth, LEAD_TIME_WORKING_DAYS)

    def test_deeper_reports_buy_more_reading_time(self):
        self.assertGreater(
            required_lead_days("full-verification-dossier"), required_lead_days("summary")
        )


class CalendarTests(unittest.TestCase):
    def test_iso_string_is_parsed(self):
        self.assertEqual(as_date("2027-03-12"), CDR_DATE)

    def test_date_object_passes_through(self):
        self.assertEqual(as_date(CDR_DATE), CDR_DATE)

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            as_date("12/03/2027")

    def test_non_date_rejected(self):
        with self.assertRaises(ValueError):
            as_date(20270312)

    def test_zero_working_days_returns_the_reference(self):
        self.assertEqual(working_days_before(CDR_DATE, 0), CDR_DATE)

    def test_one_working_day_back_from_a_friday_is_thursday(self):
        self.assertEqual(working_days_before(CDR_DATE, 1), datetime.date(2027, 3, 11))

    def test_five_working_days_back_skips_the_weekend(self):
        self.assertEqual(working_days_before(CDR_DATE, 5), datetime.date(2027, 3, 5))

    def test_a_working_day_count_never_lands_on_a_weekend(self):
        for days in range(1, 45):
            self.assertLess(working_days_before(CDR_DATE, days).weekday(), 5, days)

    def test_negative_day_count_rejected(self):
        with self.assertRaises(ValueError):
            working_days_before(CDR_DATE, -1)

    def test_non_integer_day_count_rejected(self):
        with self.assertRaises(ValueError):
            working_days_before(CDR_DATE, 2.5)

    def test_deadline_follows_the_required_depth(self):
        deep = submission_deadline(CDR_DATE, "category-1", "critical-design-review")
        shallow = submission_deadline(CDR_DATE, "category-3", "critical-design-review")
        self.assertLess(deep, shallow)


class SubmissionGradingTests(unittest.TestCase):
    def _submission(self, **overrides):
        record = {
            "review": "critical-design-review",
            "submitted_depth": "detailed-analysis",
            "submitted_date": "2027-02-10",
        }
        record.update(overrides)
        return record

    def test_deep_and_early_submission_passes(self):
        record = grade_submission(self._submission(), "category-1", CDR_DATE)
        self.assertTrue(record["delivered"])
        self.assertTrue(record["deep_enough"])
        self.assertTrue(record["on_time"])
        self.assertEqual(record["findings"], [])

    def test_submission_exactly_on_the_deadline_is_on_time(self):
        deadline = submission_deadline(CDR_DATE, "category-1", "critical-design-review")
        record = grade_submission(
            self._submission(submitted_date=deadline), "category-1", CDR_DATE
        )
        self.assertTrue(record["on_time"])

    def test_submission_one_day_late_is_flagged(self):
        deadline = submission_deadline(CDR_DATE, "category-1", "critical-design-review")
        record = grade_submission(
            self._submission(submitted_date=deadline + datetime.timedelta(days=1)),
            "category-1",
            CDR_DATE,
        )
        self.assertFalse(record["on_time"])
        self.assertTrue(any("after the" in f for f in record["findings"]))

    def test_shallow_submission_is_flagged(self):
        record = grade_submission(
            self._submission(submitted_depth="summary"), "category-1", CDR_DATE
        )
        self.assertFalse(record["deep_enough"])

    def test_deeper_than_required_is_accepted(self):
        record = grade_submission(
            self._submission(submitted_depth="full-verification-dossier"),
            "category-2",
            CDR_DATE,
        )
        self.assertTrue(record["deep_enough"])

    def test_absent_submission_is_reported_once(self):
        record = grade_submission(
            {"review": "critical-design-review"}, "category-1", CDR_DATE
        )
        self.assertFalse(record["delivered"])
        self.assertEqual(len(record["findings"]), 1)

    def test_half_declared_submission_rejected(self):
        with self.assertRaises(ValueError):
            grade_submission(
                {"review": "critical-design-review", "submitted_depth": "summary"},
                "category-1",
                CDR_DATE,
            )

    def test_non_mapping_submission_rejected(self):
        with self.assertRaises(ValueError):
            grade_submission(["critical-design-review"], "category-1", CDR_DATE)


class ReportingAssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "category": "category-2",
            "reviews": [
                {
                    "review": "preliminary-design-review",
                    "review_date": "2026-09-11",
                    "submitted_depth": "summary",
                    "submitted_date": "2026-08-20",
                },
                {
                    "review": "critical-design-review",
                    "review_date": "2027-03-12",
                    "submitted_depth": "assessment",
                    "submitted_date": "2027-02-10",
                },
            ],
        }
        spec.update(overrides)
        return spec

    def test_compliant_reporting_has_no_findings(self):
        result = assess_review_reporting(self._spec())
        self.assertTrue(result["reporting_compliant"])
        self.assertEqual(result["findings"], [])

    def test_reviews_are_reported_in_project_order(self):
        spec = self._spec()
        spec["reviews"] = list(reversed(spec["reviews"]))
        result = assess_review_reporting(spec)
        self.assertEqual(
            [item["review"] for item in result["reviews"]],
            ["preliminary-design-review", "critical-design-review"],
        )

    def test_shallow_report_breaks_compliance(self):
        spec = self._spec()
        spec["reviews"][1]["submitted_depth"] = "summary"
        result = assess_review_reporting(spec)
        self.assertFalse(result["reporting_compliant"])

    def test_late_report_breaks_compliance(self):
        spec = self._spec()
        spec["reviews"][1]["submitted_date"] = "2027-03-11"
        result = assess_review_reporting(spec)
        self.assertFalse(result["reporting_compliant"])

    def test_category_change_can_break_a_compliant_set(self):
        result = assess_review_reporting(self._spec(category="category-1"))
        self.assertFalse(result["reporting_compliant"])

    def test_duplicate_review_entry_rejected(self):
        spec = self._spec()
        spec["reviews"] = [spec["reviews"][0], dict(spec["reviews"][0])]
        with self.assertRaises(ValueError):
            assess_review_reporting(spec)

    def test_entry_without_review_date_rejected(self):
        spec = self._spec()
        del spec["reviews"][0]["review_date"]
        with self.assertRaises(ValueError):
            assess_review_reporting(spec)

    def test_empty_review_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_review_reporting(self._spec(reviews=[]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["category"]
        with self.assertRaises(ValueError):
            assess_review_reporting(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_review_reporting(["category-2"])


if __name__ == "__main__":
    unittest.main()
