"""Contract tests for the ECSS-Q-ST-70-04C rate-control and hold-criteria logic."""

import unittest

from q7004_rate_and_hold_requirements_logic import (
    COMPARISON_TOLERANCE,
    assess_rate_and_hold,
    hold_duration_s,
    rate_band_excursions,
    rate_ceiling_excursions,
    segment_rates,
    stabilization_point,
    transition_bounds,
    validate_series,
    window_drift_rate,
)

# A cold transition from ambient at 2 K/min sampled every 300 s, followed by a
# dwell at the cold set point with a small residual wobble inside the band.
RAMP = [
    (0.0, 20.0),
    (300.0, 10.0),
    (600.0, 0.0),
    (900.0, -10.0),
    (1200.0, -20.0),
    (1500.0, -30.0),
    (1800.0, -40.0),
]

DWELL = [
    (2100.0, -40.2),
    (2400.0, -39.9),
    (2700.0, -40.1),
    (3000.0, -40.0),
    (3300.0, -39.95),
    (3600.0, -40.05),
    (3900.0, -40.0),
    (4200.0, -40.0),
    (4500.0, -40.0),
    (4800.0, -40.0),
    (5100.0, -40.0),
    (5400.0, -40.0),
]

RUN = RAMP + DWELL


def spec(**overrides):
    base = {
        "samples": list(RUN),
        "set_point_c": -40.0,
        "band_k": 2.0,
        "drift_limit_k_per_min": 0.5,
        "stabilization_window_s": 900.0,
        "required_hold_s": 3000.0,
        "rate_ceiling_k_per_min": 3.0,
        "requested_rate_k_per_min": 2.0,
        "rate_tolerance_fraction": 0.2,
        "transition_window_s": (0.0, 1800.0),
    }
    base.update(overrides)
    return base


class SeriesValidationTests(unittest.TestCase):
    def test_valid_series_is_returned_as_floats(self):
        series = validate_series([(0, 20), (60, 18)])
        self.assertEqual(series, [(0.0, 20.0), (60.0, 18.0)])

    def test_single_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([(0.0, 20.0)])

    def test_non_increasing_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([(0.0, 20.0), (0.0, 19.0)])

    def test_backwards_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([(120.0, 20.0), (60.0, 19.0)])

    def test_negative_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([(-10.0, 20.0), (60.0, 19.0)])

    def test_malformed_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([(0.0, 20.0), (60.0,)])

    def test_non_numeric_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([(0.0, 20.0), (60.0, "19")])


class RateTests(unittest.TestCase):
    def test_ramp_rate_is_kelvin_per_minute(self):
        rates = segment_rates(RAMP)
        self.assertAlmostEqual(rates[0]["rate_k_per_min"], -2.0, places=9)

    def test_one_rate_per_interval(self):
        self.assertEqual(len(segment_rates(RAMP)), len(RAMP) - 1)

    def test_cooling_rate_is_signed_negative(self):
        self.assertLess(segment_rates(RAMP)[3]["rate_k_per_min"], 0.0)

    def test_ceiling_is_met_by_the_nominal_ramp(self):
        result = rate_ceiling_excursions(RUN, 3.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["worst_abs_rate_k_per_min"], 2.0, places=9)

    def test_rate_exactly_on_the_ceiling_is_not_an_excursion(self):
        result = rate_ceiling_excursions(RAMP, 2.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["worst_abs_rate_k_per_min"], 2.0, places=9)

    def test_overspeed_interval_is_reported(self):
        fast = list(RAMP)
        fast[1] = (300.0, -10.0)
        result = rate_ceiling_excursions(fast, 3.0)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["excursions"]), 1)
        self.assertAlmostEqual(result["excursions"][0]["rate_k_per_min"], -6.0, places=9)
        self.assertAlmostEqual(
            result["excursions"][0]["exceeded_by_k_per_min"], 3.0, places=9
        )

    def test_zero_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            rate_ceiling_excursions(RAMP, 0.0)

    def test_requested_band_is_met_over_the_transition(self):
        result = rate_band_excursions(RUN, 2.0, 0.2, (0.0, 1800.0))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["graded_intervals"], 6)

    def test_dwell_intervals_are_not_graded_against_the_transition_band(self):
        graded = rate_band_excursions(RUN, 2.0, 0.2, (0.0, 1800.0))["graded_intervals"]
        self.assertLess(graded, len(segment_rates(RUN)))

    def test_slow_transition_falls_outside_the_band(self):
        slow = [(0.0, 20.0), (600.0, 10.0)]
        result = rate_band_excursions(slow, 2.0, 0.2)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["excursions"][0]["deviation_k_per_min"], 1.0, places=9)

    def test_band_half_width_is_the_fraction_of_the_requested_rate(self):
        result = rate_band_excursions(RAMP, 2.0, 0.25)
        self.assertAlmostEqual(result["half_width_k_per_min"], 0.5, places=9)

    def test_tolerance_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            rate_band_excursions(RAMP, 2.0, 1.5)

    def test_empty_transition_window_rejected(self):
        with self.assertRaises(ValueError):
            rate_band_excursions(RUN, 2.0, 0.2, (10.0, 20.0))

    def test_inverted_transition_window_rejected(self):
        with self.assertRaises(ValueError):
            transition_bounds((1800.0, 0.0))

    def test_absent_transition_window_grades_everything(self):
        self.assertIsNone(transition_bounds(None))


class StabilizationTests(unittest.TestCase):
    def test_window_drift_is_kelvin_per_minute(self):
        series = validate_series([(0.0, -40.0), (600.0, -39.0)])
        self.assertAlmostEqual(window_drift_rate(series, 0, 600.0), 0.1, places=9)

    def test_window_drift_is_none_when_no_sample_covers_it(self):
        series = validate_series([(0.0, -40.0), (6000.0, -39.0)])
        self.assertIsNone(window_drift_rate(series, 0, 600.0))

    def test_start_index_outside_the_series_rejected(self):
        series = validate_series(RAMP)
        with self.assertRaises(ValueError):
            window_drift_rate(series, 99, 600.0)

    def test_stabilization_is_found_at_the_end_of_the_ramp(self):
        point = stabilization_point(RUN, -40.0, 2.0, 0.5, 900.0)
        self.assertTrue(point["confirmed"])
        self.assertAlmostEqual(point["time_s"], 1800.0, places=9)

    def test_stabilization_needs_the_whole_window_inside_the_band(self):
        broken = list(RUN)
        broken[8] = (2400.0, -30.0)
        point = stabilization_point(broken, -40.0, 2.0, 0.5, 900.0)
        self.assertTrue(point["confirmed"])
        self.assertGreater(point["time_s"], 1800.0)

    def test_a_run_that_never_settles_is_not_confirmed(self):
        wandering = [(float(i * 300), -40.0 + 6.0 * (i % 2)) for i in range(12)]
        point = stabilization_point(wandering, -40.0, 2.0, 0.5, 900.0)
        self.assertFalse(point["confirmed"])

    def test_drift_limit_can_refuse_a_slowly_creeping_item(self):
        creep = [(float(i * 300), -41.5 + 0.3 * i) for i in range(12)]
        point = stabilization_point(creep, -40.0, 2.0, 0.001, 900.0)
        self.assertFalse(point["confirmed"])

    def test_zero_band_rejected(self):
        with self.assertRaises(ValueError):
            stabilization_point(RUN, -40.0, 0.0, 0.5, 900.0)

    def test_negative_drift_limit_rejected(self):
        with self.assertRaises(ValueError):
            stabilization_point(RUN, -40.0, 2.0, -0.5, 900.0)


class HoldTests(unittest.TestCase):
    def test_hold_runs_to_the_end_of_the_record(self):
        self.assertAlmostEqual(hold_duration_s(RUN, -40.0, 2.0, 1800.0), 3600.0, places=9)

    def test_hold_stops_where_the_band_is_left(self):
        broken = list(RUN)
        broken[10] = (3000.0, -20.0)
        self.assertAlmostEqual(hold_duration_s(broken, -40.0, 2.0, 1800.0), 900.0, places=9)

    def test_hold_is_zero_when_the_start_is_outside_the_band(self):
        self.assertAlmostEqual(hold_duration_s(RUN, -40.0, 2.0, 0.0), 0.0, places=12)

    def test_negative_start_time_rejected(self):
        with self.assertRaises(ValueError):
            hold_duration_s(RUN, -40.0, 2.0, -1.0)


class AssessmentTests(unittest.TestCase):
    def test_nominal_run_is_compliant_with_no_findings(self):
        result = assess_rate_and_hold(spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_credited_hold_is_measured_from_stabilization(self):
        result = assess_rate_and_hold(spec())
        self.assertAlmostEqual(result["achieved_hold_s"], 3600.0, places=9)

    def test_hold_exactly_on_the_requirement_is_met(self):
        result = assess_rate_and_hold(spec(required_hold_s=3600.0))
        self.assertTrue(result["hold_met"])
        self.assertLessEqual(
            abs(result["achieved_hold_s"] - result["required_hold_s"]),
            COMPARISON_TOLERANCE,
        )

    def test_short_hold_is_flagged(self):
        result = assess_rate_and_hold(spec(required_hold_s=7200.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("short of the required" in f for f in result["findings"]))

    def test_overspeed_transition_is_flagged(self):
        fast = list(RUN)
        fast[1] = (300.0, -10.0)
        result = assess_rate_and_hold(spec(samples=fast, rate_ceiling_k_per_min=3.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("exceeds the ceiling" in f for f in result["findings"]))

    def test_band_check_is_skipped_when_no_rate_was_requested(self):
        result = assess_rate_and_hold(spec(requested_rate_k_per_min=None))
        self.assertIsNone(result["rate_band"])
        self.assertTrue(result["compliant"])

    def test_unsettled_run_reports_no_hold_at_all(self):
        wandering = [(float(i * 300), -40.0 + 6.0 * (i % 2)) for i in range(12)]
        result = assess_rate_and_hold(
            spec(samples=wandering, transition_window_s=None,
                 requested_rate_k_per_min=None, rate_ceiling_k_per_min=10.0)
        )
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["achieved_hold_s"], 0.0, places=12)

    def test_missing_spec_key_rejected(self):
        bad = spec()
        del bad["band_k"]
        with self.assertRaises(ValueError):
            assess_rate_and_hold(bad)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_rate_and_hold([RUN])

    def test_negative_required_hold_rejected(self):
        with self.assertRaises(ValueError):
            assess_rate_and_hold(spec(required_hold_s=-1.0))


if __name__ == "__main__":
    unittest.main()
