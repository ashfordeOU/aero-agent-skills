"""Contract tests for the cleanliness monitoring report logic."""

import unittest

from q7050_monitoring_reports_logic import (
    DEFAULT_CONTENT_ITEMS,
    assess_monitoring_report,
    content_completeness,
    grade_location_coverage,
    grade_timeliness,
    grade_traceability,
    merge_intervals,
    overlapping_pairs,
    period_coverage,
    submission_latency_days,
    validate_interval,
    validate_intervals,
)

CONTIGUOUS = [(0.0, 30.0), (30.0, 60.0), (60.0, 90.0)]
REQUIRED_LOCATIONS = ["iso7-bay", "clean-tent"]


def results():
    return [
        {"location": "iso7-bay", "instrument_id": "opc-01", "method": "airborne-count",
         "value": 1200.0},
        {"location": "clean-tent", "instrument_id": "mic-02", "method": "tape-lift",
         "value": 40.0},
    ]


def package():
    return {item: "included" for item in DEFAULT_CONTENT_ITEMS}


def spec(**overrides):
    base = {
        "period_start": 0.0,
        "period_end": 90.0,
        "intervals": CONTIGUOUS,
        "results": results(),
        "submitted_day": 95.0,
        "turnaround_days": 10.0,
        "required_locations": REQUIRED_LOCATIONS,
        "package": package(),
    }
    base.update(overrides)
    return base


class IntervalTests(unittest.TestCase):
    def test_interval_returned_as_floats(self):
        self.assertEqual(validate_interval((0, 5)), (0.0, 5.0))

    def test_zero_length_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_interval((5.0, 5.0))

    def test_reversed_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_interval((10.0, 5.0))

    def test_malformed_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_interval((5.0,))

    def test_boolean_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_interval((True, 5.0))

    def test_intervals_are_sorted_by_start(self):
        ordered = validate_intervals([(60.0, 90.0), (0.0, 30.0)])
        self.assertAlmostEqual(ordered[0][0], 0.0, places=12)

    def test_empty_interval_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_intervals([])


class MergeTests(unittest.TestCase):
    def test_touching_intervals_merge(self):
        self.assertEqual(merge_intervals(CONTIGUOUS), [(0.0, 90.0)])

    def test_separated_intervals_stay_apart(self):
        self.assertEqual(
            merge_intervals([(0.0, 30.0), (45.0, 90.0)]), [(0.0, 30.0), (45.0, 90.0)]
        )

    def test_overlapping_intervals_merge_to_the_outer_bound(self):
        self.assertEqual(merge_intervals([(0.0, 40.0), (30.0, 90.0)]), [(0.0, 90.0)])

    def test_a_contained_interval_does_not_shorten_the_merge(self):
        self.assertEqual(merge_intervals([(0.0, 90.0), (30.0, 40.0)]), [(0.0, 90.0)])

    def test_touching_intervals_are_not_an_overlap(self):
        self.assertEqual(overlapping_pairs(CONTIGUOUS), [])

    def test_overlap_days_are_measured(self):
        overlaps = overlapping_pairs([(0.0, 40.0), (30.0, 90.0)])
        self.assertEqual(len(overlaps), 1)
        self.assertAlmostEqual(overlaps[0]["overlap_days"], 10.0, places=12)


class CoverageTests(unittest.TestCase):
    def test_contiguous_intervals_cover_the_period(self):
        coverage = period_coverage(CONTIGUOUS, 0.0, 90.0)
        self.assertAlmostEqual(coverage["coverage_fraction"], 1.0, places=12)
        self.assertTrue(coverage["complete"])

    def test_gap_is_located(self):
        coverage = period_coverage([(0.0, 30.0), (45.0, 90.0)], 0.0, 90.0)
        self.assertEqual(len(coverage["gaps"]), 1)
        self.assertAlmostEqual(coverage["gaps"][0][0], 30.0, places=12)
        self.assertAlmostEqual(coverage["gaps"][0][1], 45.0, places=12)

    def test_gap_reduces_the_coverage_fraction(self):
        coverage = period_coverage([(0.0, 30.0), (45.0, 90.0)], 0.0, 90.0)
        self.assertAlmostEqual(coverage["coverage_fraction"], 75.0 / 90.0, places=12)

    def test_a_leading_gap_is_found(self):
        coverage = period_coverage([(10.0, 90.0)], 0.0, 90.0)
        self.assertAlmostEqual(coverage["gaps"][0][0], 0.0, places=12)

    def test_a_trailing_gap_is_found(self):
        coverage = period_coverage([(0.0, 80.0)], 0.0, 90.0)
        self.assertAlmostEqual(coverage["gaps"][-1][1], 90.0, places=12)

    def test_double_counted_days_do_not_exceed_full_coverage(self):
        coverage = period_coverage([(0.0, 60.0), (30.0, 90.0)], 0.0, 90.0)
        self.assertAlmostEqual(coverage["coverage_fraction"], 1.0, places=12)
        self.assertEqual(len(coverage["overlaps"]), 1)

    def test_an_interval_spilling_outside_the_period_is_recorded(self):
        coverage = period_coverage([(-10.0, 30.0), (30.0, 90.0)], 0.0, 90.0)
        self.assertEqual(len(coverage["outside_period"]), 1)
        self.assertAlmostEqual(coverage["coverage_fraction"], 1.0, places=12)

    def test_an_interval_entirely_before_the_period_covers_nothing(self):
        coverage = period_coverage([(-30.0, -10.0), (0.0, 90.0)], 0.0, 90.0)
        self.assertAlmostEqual(coverage["covered_days"], 90.0, places=12)

    def test_reversed_period_rejected(self):
        with self.assertRaises(ValueError):
            period_coverage(CONTIGUOUS, 90.0, 0.0)


class TimelinessTests(unittest.TestCase):
    def test_latency_is_measured_from_the_period_end(self):
        self.assertAlmostEqual(submission_latency_days(90.0, 95.0), 5.0, places=12)

    def test_submission_inside_the_turnaround_is_on_time(self):
        self.assertTrue(grade_timeliness(90.0, 95.0, 10.0)["on_time"])

    def test_submission_exactly_at_the_turnaround_is_on_time(self):
        result = grade_timeliness(90.0, 100.0, 10.0)
        self.assertAlmostEqual(result["latency_days"], 10.0, places=9)
        self.assertTrue(result["on_time"])

    def test_late_submission_reports_the_overdue_days(self):
        result = grade_timeliness(90.0, 105.0, 10.0)
        self.assertFalse(result["on_time"])
        self.assertAlmostEqual(result["overdue_days"], 5.0, places=12)

    def test_on_time_submission_has_no_overdue_days(self):
        self.assertAlmostEqual(
            grade_timeliness(90.0, 95.0, 10.0)["overdue_days"], 0.0, places=12
        )

    def test_submission_before_the_period_closed_rejected(self):
        with self.assertRaises(ValueError):
            grade_timeliness(90.0, 85.0, 10.0)

    def test_zero_turnaround_rejected(self):
        with self.assertRaises(ValueError):
            grade_timeliness(90.0, 95.0, 0.0)


class TraceabilityTests(unittest.TestCase):
    def test_complete_results_are_traceable(self):
        self.assertTrue(grade_traceability(results())["traceable"])

    def test_a_result_without_an_instrument_is_untraceable(self):
        records = results()
        del records[0]["instrument_id"]
        graded = grade_traceability(records)
        self.assertFalse(graded["traceable"])
        self.assertEqual(graded["untraceable"][0]["missing"], ["instrument_id"])

    def test_a_result_with_an_empty_method_is_untraceable(self):
        records = results()
        records[1]["method"] = ""
        self.assertFalse(grade_traceability(records)["traceable"])

    def test_both_fields_missing_are_both_named(self):
        records = results()
        del records[0]["instrument_id"]
        del records[0]["method"]
        graded = grade_traceability(records)
        self.assertEqual(graded["untraceable"][0]["missing"],
                         ["instrument_id", "method"])

    def test_a_result_without_a_location_rejected(self):
        records = results()
        del records[0]["location"]
        with self.assertRaises(ValueError):
            grade_traceability(records)

    def test_empty_results_rejected(self):
        with self.assertRaises(ValueError):
            grade_traceability([])


class LocationTests(unittest.TestCase):
    def test_all_required_locations_reported(self):
        self.assertTrue(
            grade_location_coverage(results(), REQUIRED_LOCATIONS)["complete"]
        )

    def test_a_missing_location_is_named(self):
        graded = grade_location_coverage(results()[:1], REQUIRED_LOCATIONS)
        self.assertEqual(graded["missing"], ["clean-tent"])

    def test_an_unexpected_location_is_listed_without_failing(self):
        records = results()
        records.append({"location": "airlock", "instrument_id": "opc-01",
                        "method": "airborne-count"})
        graded = grade_location_coverage(records, REQUIRED_LOCATIONS)
        self.assertEqual(graded["unexpected"], ["airlock"])
        self.assertTrue(graded["complete"])

    def test_empty_required_list_rejected(self):
        with self.assertRaises(ValueError):
            grade_location_coverage(results(), [])

    def test_result_without_a_location_rejected(self):
        with self.assertRaises(ValueError):
            grade_location_coverage([{"instrument_id": "opc-01"}], REQUIRED_LOCATIONS)


class ContentTests(unittest.TestCase):
    def test_full_package_is_complete(self):
        graded = content_completeness(package())
        self.assertTrue(graded["complete"])
        self.assertAlmostEqual(graded["fraction_complete"], 1.0, places=12)

    def test_missing_item_is_named(self):
        contents = package()
        del contents["trend"]
        self.assertEqual(content_completeness(contents)["missing"], ["trend"])

    def test_fraction_reflects_what_is_present(self):
        graded = content_completeness({"period": "yes"})
        self.assertAlmostEqual(
            graded["fraction_complete"], 1.0 / len(DEFAULT_CONTENT_ITEMS), places=12
        )

    def test_a_programme_may_state_its_own_items(self):
        graded = content_completeness({"results": "yes"}, ["results"])
        self.assertTrue(graded["complete"])

    def test_non_mapping_package_rejected(self):
        with self.assertRaises(ValueError):
            content_completeness(["period"])

    def test_empty_required_items_rejected(self):
        with self.assertRaises(ValueError):
            content_completeness(package(), [])


class AssessmentTests(unittest.TestCase):
    def test_complete_report_is_acceptable(self):
        result = assess_monitoring_report(spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_unmonitored_days_are_reported(self):
        result = assess_monitoring_report(
            spec(intervals=[(0.0, 30.0), (45.0, 90.0)])
        )
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("unmonitored" in f for f in result["findings"]))

    def test_double_counted_days_are_reported(self):
        result = assess_monitoring_report(
            spec(intervals=[(0.0, 60.0), (30.0, 90.0)])
        )
        self.assertTrue(any("double count" in f for f in result["findings"]))

    def test_late_submission_is_reported(self):
        result = assess_monitoring_report(spec(submitted_day=140.0))
        self.assertTrue(any("turnaround" in f for f in result["findings"]))

    def test_untraceable_result_is_reported(self):
        records = results()
        del records[0]["method"]
        result = assess_monitoring_report(spec(results=records))
        self.assertTrue(any("does not name" in f for f in result["findings"]))

    def test_missing_location_is_reported(self):
        result = assess_monitoring_report(spec(results=results()[:1]))
        self.assertTrue(any("no results reported" in f for f in result["findings"]))

    def test_missing_content_is_reported(self):
        contents = package()
        del contents["signature"]
        result = assess_monitoring_report(spec(package=contents))
        self.assertTrue(any("content missing" in f for f in result["findings"]))

    def test_interval_outside_the_period_is_reported(self):
        result = assess_monitoring_report(
            spec(intervals=[(-10.0, 30.0), (30.0, 90.0)])
        )
        self.assertTrue(any("outside the reporting period" in f
                            for f in result["findings"]))

    def test_missing_key_rejected(self):
        payload = spec()
        del payload["turnaround_days"]
        with self.assertRaises(ValueError):
            assess_monitoring_report(payload)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_monitoring_report(["period_start"])

    def test_coverage_fraction_is_reported(self):
        result = assess_monitoring_report(spec())
        self.assertAlmostEqual(result["coverage"]["coverage_fraction"], 1.0,
                               places=12)


if __name__ == "__main__":
    unittest.main()
