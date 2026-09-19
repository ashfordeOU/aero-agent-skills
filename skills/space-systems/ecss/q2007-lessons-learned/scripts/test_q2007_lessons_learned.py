"""Contract tests for the clause 5.8.3 lessons-learned review logic."""

import unittest

from q2007_lessons_learned_logic import (
    CATEGORIES,
    FRACTION_TOLERANCE,
    HIGH_BAND_MIN,
    MEDIUM_BAND_MIN,
    assess_lesson,
    assess_lessons_review,
    capture_ratio,
    feedback_route,
    overdue_days,
    priority_band,
    priority_index,
    register_metrics,
    validate_lesson,
)

BASE = {
    "id": "LL-07",
    "source_event": "thermal chamber controller reset during the hot soak",
    "category": "facility",
    "recommendation": "add an uninterruptible supply to the chamber controller",
    "owner": "facility engineer",
    "target_day": 30,
    "status": "open",
    "recurrence": 2,
    "consequence": 3,
    "detectability": 2,
}


def lesson(**overrides):
    out = dict(BASE)
    out.update(overrides)
    return out


class PriorityTests(unittest.TestCase):
    def test_index_is_the_product(self):
        self.assertEqual(priority_index(2, 3, 4), 24)

    def test_lowest_index_is_one(self):
        self.assertEqual(priority_index(1, 1, 1), 1)

    def test_highest_index_is_one_hundred_and_twenty_five(self):
        self.assertEqual(priority_index(5, 5, 5), 125)

    def test_ordinal_above_range_rejected(self):
        with self.assertRaises(ValueError):
            priority_index(6, 3, 2)

    def test_ordinal_below_range_rejected(self):
        with self.assertRaises(ValueError):
            priority_index(0, 3, 2)

    def test_float_ordinal_rejected(self):
        with self.assertRaises(ValueError):
            priority_index(2.5, 3, 2)

    def test_boolean_ordinal_rejected(self):
        with self.assertRaises(ValueError):
            priority_index(True, 3, 2)

    def test_band_boundaries_are_inclusive(self):
        self.assertEqual(priority_band(HIGH_BAND_MIN), "high")
        self.assertEqual(priority_band(HIGH_BAND_MIN - 1), "medium")
        self.assertEqual(priority_band(MEDIUM_BAND_MIN), "medium")
        self.assertEqual(priority_band(MEDIUM_BAND_MIN - 1), "low")

    def test_band_of_an_out_of_range_index_rejected(self):
        with self.assertRaises(ValueError):
            priority_band(200)

    def test_band_of_a_non_integer_rejected(self):
        with self.assertRaises(ValueError):
            priority_band(24.0)


class RouteTests(unittest.TestCase):
    def test_every_category_has_a_route(self):
        for category in CATEGORIES:
            self.assertTrue(feedback_route(category))

    def test_procedure_routes_to_the_procedure_baseline(self):
        self.assertIn("procedure", feedback_route("procedure"))

    def test_instrumentation_routes_to_the_measurement_chain(self):
        self.assertIn("measurement chain", feedback_route("instrumentation"))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            feedback_route("morale")


class ValidationTests(unittest.TestCase):
    def test_valid_entry_normalises(self):
        record = validate_lesson(lesson())
        self.assertEqual(record["priority_index"], 12)
        self.assertEqual(record["priority_band"], "low")

    def test_missing_recommendation_rejected(self):
        bad = lesson()
        del bad["recommendation"]
        with self.assertRaises(ValueError):
            validate_lesson(bad)

    def test_blank_source_event_rejected(self):
        with self.assertRaises(ValueError):
            validate_lesson(lesson(source_event="   "))

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_lesson(lesson(status="parked"))

    def test_negative_target_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_lesson(lesson(target_day=-5))

    def test_blank_owner_rejected(self):
        with self.assertRaises(ValueError):
            validate_lesson(lesson(owner=""))

    def test_absent_owner_allowed_at_validation(self):
        record = validate_lesson(lesson(owner=None))
        self.assertIsNone(record["owner"])

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_lesson(["LL-07"])


class OverdueTests(unittest.TestCase):
    def test_target_in_the_future_is_not_overdue(self):
        self.assertEqual(overdue_days(30, 10), 0)

    def test_target_on_the_review_day_is_not_overdue(self):
        self.assertEqual(overdue_days(30, 30), 0)

    def test_past_target_counts_the_days(self):
        self.assertEqual(overdue_days(30, 44), 14)

    def test_negative_day_rejected(self):
        with self.assertRaises(ValueError):
            overdue_days(-1, 10)

    def test_non_integer_day_rejected(self):
        with self.assertRaises(ValueError):
            overdue_days(30.0, 10)


class LessonAssessmentTests(unittest.TestCase):
    def test_owned_and_dated_entry_is_actionable(self):
        record = assess_lesson(lesson(), 10)
        self.assertTrue(record["actionable"])

    def test_unowned_open_entry_is_a_finding(self):
        record = assess_lesson(lesson(owner=None), 10)
        self.assertFalse(record["actionable"])

    def test_undated_open_entry_is_a_finding(self):
        record = assess_lesson(lesson(target_day=None), 10)
        self.assertFalse(record["actionable"])

    def test_closed_entry_needs_no_owner(self):
        record = assess_lesson(lesson(owner=None, target_day=None, status="closed"), 90)
        self.assertTrue(record["actionable"])

    def test_overdue_open_entry_is_a_finding(self):
        record = assess_lesson(lesson(), 60)
        self.assertEqual(record["overdue_days"], 30)
        self.assertFalse(record["actionable"])

    def test_high_band_unowned_entry_names_the_review(self):
        record = assess_lesson(
            lesson(owner=None, recurrence=4, consequence=5, detectability=4), 10
        )
        self.assertEqual(record["priority_band"], "high")
        self.assertIn("review cannot be complete", " ".join(record["findings"]))

    def test_negative_review_day_rejected(self):
        with self.assertRaises(ValueError):
            assess_lesson(lesson(), -1)


class CaptureAndMetricsTests(unittest.TestCase):
    def test_capture_ratio_is_the_quotient(self):
        self.assertAlmostEqual(capture_ratio(6, 4), 1.5)

    def test_capture_ratio_of_one_per_anomaly(self):
        self.assertAlmostEqual(capture_ratio(4, 4), 1.0, places=9)

    def test_capture_ratio_with_no_anomalies_rejected(self):
        with self.assertRaises(ValueError):
            capture_ratio(3, 0)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            capture_ratio(-1, 3)

    def test_empty_register_metrics(self):
        metrics = register_metrics([])
        self.assertEqual(metrics["total"], 0)
        self.assertAlmostEqual(metrics["closed_fraction"], 0.0)

    def test_closed_fraction(self):
        records = [
            assess_lesson(lesson(id="LL-1", status="closed"), 10),
            assess_lesson(lesson(id="LL-2"), 10),
        ]
        metrics = register_metrics(records)
        self.assertAlmostEqual(metrics["closed_fraction"], 0.5, places=9)

    def test_band_counts(self):
        records = [
            assess_lesson(
                lesson(id="LL-3", recurrence=5, consequence=5, detectability=5), 10
            ),
            assess_lesson(lesson(id="LL-4"), 10),
        ]
        metrics = register_metrics(records)
        self.assertEqual(metrics["high"], 1)
        self.assertEqual(metrics["low"], 1)


class ReviewTests(unittest.TestCase):
    def spec(self, **overrides):
        out = {
            "lessons": [lesson(), lesson(id="LL-08", category="procedure")],
            "review_day": 10,
            "anomaly_count": 2,
            "required_capture_ratio": 1.0,
        }
        out.update(overrides)
        return out

    def test_clean_review_is_complete(self):
        result = assess_lessons_review(self.spec())
        self.assertTrue(result["review_complete"])
        self.assertAlmostEqual(result["capture_ratio"], 1.0, places=9)

    def test_capture_ratio_exactly_on_the_requirement_passes(self):
        result = assess_lessons_review(self.spec(anomaly_count=2))
        self.assertAlmostEqual(
            result["capture_ratio"], result["required_capture_ratio"], places=9
        )
        self.assertTrue(result["review_complete"])

    def test_thin_capture_is_a_finding(self):
        result = assess_lessons_review(self.spec(anomaly_count=8))
        self.assertFalse(result["review_complete"])

    def test_routes_are_reported_once_each(self):
        result = assess_lessons_review(self.spec())
        self.assertEqual(len(result["routes"]), 2)

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_lessons_review(self.spec(lessons=[lesson(), lesson()]))

    def test_missing_key_rejected(self):
        bad = self.spec()
        del bad["anomaly_count"]
        with self.assertRaises(ValueError):
            assess_lessons_review(bad)

    def test_negative_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_lessons_review(self.spec(required_capture_ratio=-1.0))

    def test_tolerance_is_representation_sized(self):
        self.assertAlmostEqual(FRACTION_TOLERANCE, 1e-9, places=12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
