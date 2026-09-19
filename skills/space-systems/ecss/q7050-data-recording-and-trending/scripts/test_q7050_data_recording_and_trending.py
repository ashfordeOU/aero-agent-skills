"""Contract tests for the monitoring data recording and trending logic."""

import math
import unittest

from q7050_data_recording_and_trending_logic import (
    DEFAULT_ALERT_FRACTION,
    MIN_TREND_POINTS,
    alert_level,
    assess_trend,
    categorize_point,
    least_squares_fit,
    longest_rising_run,
    projected_days_to_limit,
    recording_gaps,
    series_statistics,
    trailing_run_above,
    validate_series,
)

# A slowly rising surface-particulate record, four monthly samples.
RISING = [(0.0, 10.0), (30.0, 12.0), (60.0, 14.0), (90.0, 16.0)]
FLAT = [(0.0, 10.0), (10.0, 10.0), (20.0, 10.0)]
FALLING = [(0.0, 30.0), (10.0, 20.0), (20.0, 10.0)]
STEEP = [(0.0, 40.0), (10.0, 60.0), (20.0, 80.0)]


class SeriesValidationTests(unittest.TestCase):
    def test_pairs_returned_as_floats(self):
        points = validate_series([(0, 1), (1, 2)])
        self.assertAlmostEqual(points[0][0], 0.0, places=12)
        self.assertAlmostEqual(points[1][1], 2.0, places=12)

    def test_single_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([(0.0, 1.0)])

    def test_unordered_days_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([(10.0, 1.0), (5.0, 2.0)])

    def test_repeated_day_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([(10.0, 1.0), (10.0, 2.0)])

    def test_negative_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([(0.0, 1.0), (1.0, -2.0)])

    def test_malformed_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([(0.0, 1.0), (1.0,)])

    def test_boolean_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([(0.0, 1.0), (1.0, True)])


class StatisticsTests(unittest.TestCase):
    def test_mean_of_the_record(self):
        self.assertAlmostEqual(series_statistics(RISING)["mean"], 13.0, places=12)

    def test_sample_spread_uses_n_minus_one(self):
        self.assertAlmostEqual(
            series_statistics(RISING)["stdev"], math.sqrt(20.0 / 3.0), places=12
        )

    def test_flat_record_has_no_spread(self):
        self.assertAlmostEqual(series_statistics(FLAT)["stdev"], 0.0, places=12)

    def test_extremes_are_reported(self):
        statistics = series_statistics(RISING)
        self.assertAlmostEqual(statistics["minimum"], 10.0, places=12)
        self.assertAlmostEqual(statistics["maximum"], 16.0, places=12)

    def test_span_is_the_elapsed_time(self):
        self.assertAlmostEqual(series_statistics(RISING)["span_days"], 90.0, places=12)

    def test_count_is_the_number_of_points(self):
        self.assertEqual(series_statistics(RISING)["count"], 4)


class AlertLevelTests(unittest.TestCase):
    def test_default_fraction_halves_the_action_limit(self):
        self.assertAlmostEqual(alert_level(100.0), 50.0, places=12)

    def test_stated_fraction_is_used(self):
        self.assertAlmostEqual(alert_level(100.0, 0.75), 75.0, places=12)

    def test_default_fraction_is_exposed(self):
        self.assertAlmostEqual(
            alert_level(200.0), 200.0 * DEFAULT_ALERT_FRACTION, places=12
        )

    def test_fraction_of_one_rejected(self):
        with self.assertRaises(ValueError):
            alert_level(100.0, 1.0)

    def test_zero_action_limit_rejected(self):
        with self.assertRaises(ValueError):
            alert_level(0.0)


class TrendTests(unittest.TestCase):
    def test_slope_of_the_rising_record(self):
        self.assertAlmostEqual(
            least_squares_fit(RISING)["slope_per_day"], 2.0 / 30.0, places=12
        )

    def test_flat_record_has_zero_slope(self):
        self.assertAlmostEqual(
            least_squares_fit(FLAT)["slope_per_day"], 0.0, places=12
        )

    def test_falling_record_has_a_negative_slope(self):
        self.assertAlmostEqual(
            least_squares_fit(FALLING)["slope_per_day"], -1.0, places=12
        )

    def test_fit_passes_through_the_centroid(self):
        fit = least_squares_fit(RISING)
        predicted = fit["intercept"] + fit["slope_per_day"] * fit["mean_day"]
        self.assertAlmostEqual(predicted, fit["mean_value"], places=9)

    def test_collinear_record_has_no_residual(self):
        self.assertAlmostEqual(least_squares_fit(RISING)["residual_rms"], 0.0,
                               places=9)

    def test_scattered_record_has_a_residual(self):
        fit = least_squares_fit([(0.0, 10.0), (10.0, 30.0), (20.0, 10.0)])
        self.assertGreater(fit["residual_rms"], 1.0)

    def test_two_points_are_too_few_to_trend(self):
        with self.assertRaises(ValueError):
            least_squares_fit(RISING[:2])

    def test_minimum_trend_points_is_exposed(self):
        self.assertGreaterEqual(MIN_TREND_POINTS, 3)


class ProjectionTests(unittest.TestCase):
    def test_projection_from_the_last_observation(self):
        self.assertAlmostEqual(
            projected_days_to_limit(STEEP, 100.0), 10.0, places=9
        )

    def test_flat_record_never_reaches_the_limit(self):
        self.assertIsNone(projected_days_to_limit(FLAT, 100.0))

    def test_falling_record_never_reaches_the_limit(self):
        self.assertIsNone(projected_days_to_limit(FALLING, 100.0))

    def test_already_past_the_limit_projects_zero(self):
        self.assertAlmostEqual(
            projected_days_to_limit(STEEP, 50.0), 0.0, places=12
        )

    def test_a_higher_limit_is_further_away(self):
        near = projected_days_to_limit(STEEP, 100.0)
        far = projected_days_to_limit(STEEP, 200.0)
        self.assertGreater(far, near * 2.0)

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            projected_days_to_limit(STEEP, 0.0)


class RunAndGapTests(unittest.TestCase):
    def test_trailing_run_counts_only_the_recent_points(self):
        self.assertEqual(trailing_run_above(STEEP, 50.0), 2)

    def test_a_point_exactly_at_the_threshold_ends_the_run(self):
        self.assertEqual(trailing_run_above([(0.0, 80.0), (1.0, 50.0)], 50.0), 0)

    def test_whole_record_above_the_threshold(self):
        self.assertEqual(trailing_run_above(STEEP, 10.0), 3)

    def test_longest_rising_run(self):
        record = [(0.0, 5.0), (1.0, 6.0), (2.0, 7.0), (3.0, 4.0), (4.0, 5.0)]
        self.assertEqual(longest_rising_run(record), 3)

    def test_flat_record_has_a_rising_run_of_one(self):
        self.assertEqual(longest_rising_run(FLAT), 1)

    def test_gap_wider_than_the_interval_is_listed(self):
        gaps = recording_gaps([(0.0, 1.0), (30.0, 1.0), (90.0, 1.0)], 45.0)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["interval_days"], 60.0, places=12)

    def test_gap_exactly_at_the_interval_is_not_listed(self):
        self.assertEqual(recording_gaps([(0.0, 1.0), (45.0, 1.0)], 45.0), [])

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            recording_gaps(FLAT, 0.0)


class CategorizeTests(unittest.TestCase):
    def test_low_result_conforms(self):
        self.assertEqual(categorize_point(10.0, 100.0), "conforming")

    def test_result_exactly_at_the_alert_level_still_conforms(self):
        self.assertEqual(categorize_point(50.0, 100.0, 0.5), "conforming")

    def test_result_above_the_alert_level_is_an_alert(self):
        self.assertEqual(categorize_point(60.0, 100.0, 0.5), "alert")

    def test_result_exactly_at_the_action_limit_is_not_an_exceedance(self):
        self.assertEqual(categorize_point(100.0, 100.0, 0.5), "alert")

    def test_result_above_the_action_limit_is_an_action(self):
        self.assertEqual(categorize_point(140.0, 100.0, 0.5), "action")

    def test_negative_result_rejected(self):
        with self.assertRaises(ValueError):
            categorize_point(-1.0, 100.0)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {"series": RISING, "action_limit": 100.0}
        spec.update(overrides)
        return spec

    def test_quiet_record_is_in_control(self):
        result = assess_trend(self._spec())
        self.assertTrue(result["in_control"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["latest_status"], "conforming")

    def test_steep_record_is_flagged_inside_the_horizon(self):
        result = assess_trend(self._spec(series=STEEP, horizon_days=90.0))
        self.assertFalse(result["in_control"])
        self.assertTrue(any("action limit in" in f for f in result["findings"]))

    def test_a_short_horizon_clears_the_projection_finding(self):
        result = assess_trend(self._spec(series=STEEP, horizon_days=5.0))
        self.assertTrue(all("action limit in" not in f for f in result["findings"]))

    def test_alert_run_is_its_own_trigger(self):
        result = assess_trend(self._spec(series=STEEP, action_limit=100.0,
                                         max_alert_run=2))
        self.assertTrue(any("consecutive results" in f for f in result["findings"]))

    def test_latest_exceedance_is_reported(self):
        series = [(0.0, 10.0), (10.0, 20.0), (20.0, 150.0)]
        result = assess_trend(self._spec(series=series))
        self.assertEqual(result["latest_status"], "action")
        self.assertTrue(any("exceeds the action limit" in f for f in result["findings"]))

    def test_sampling_gap_is_reported_when_an_interval_is_stated(self):
        series = [(0.0, 10.0), (30.0, 11.0), (200.0, 12.0)]
        result = assess_trend(self._spec(series=series, max_interval_days=45.0))
        self.assertTrue(any("sampling gap" in f for f in result["findings"]))

    def test_no_interval_stated_means_no_gap_findings(self):
        series = [(0.0, 10.0), (30.0, 11.0), (200.0, 12.0)]
        result = assess_trend(self._spec(series=series))
        self.assertEqual(result["gaps"], [])

    def test_two_point_record_reports_the_sparsity_finding(self):
        result = assess_trend(self._spec(series=RISING[:2]))
        self.assertIsNone(result["trend"])
        self.assertTrue(any("at least" in f for f in result["findings"]))

    def test_statuses_are_reported_per_point(self):
        result = assess_trend(self._spec(series=STEEP))
        self.assertEqual(len(result["statuses"]), len(STEEP))

    def test_alert_level_is_reported(self):
        result = assess_trend(self._spec(alert_fraction=0.75))
        self.assertAlmostEqual(result["alert_level"], 75.0, places=12)

    def test_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_trend({"series": RISING})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_trend(["series"])

    def test_zero_max_alert_run_rejected(self):
        with self.assertRaises(ValueError):
            assess_trend(self._spec(max_alert_run=0))


if __name__ == "__main__":
    unittest.main()
