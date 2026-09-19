"""Contract tests for the ECSS-Q-ST-70-04C in-test monitoring logic."""

import unittest

from q7004_in_test_monitoring_logic import (
    COMPARISON_TOLERANCE,
    DEFAULT_GAP_FACTOR,
    REQUIRED_ROLES,
    assess_channel,
    assess_monitoring,
    coverage_ratio,
    limit_excursions,
    recording_gaps,
    role_coverage,
    sampling_intervals,
    validate_channel,
    validate_samples,
)

WINDOW = (0.0, 3600.0)


def steady(interval_s, value, span_s=3600.0):
    count = int(span_s / interval_s) + 1
    return [(float(i) * interval_s, value) for i in range(count)]


def temperature_channel(**overrides):
    base = {
        "id": "T1-baseplate",
        "role": "temperature",
        "required_interval_s": 60.0,
        "lower_limit": -45.0,
        "upper_limit": 80.0,
        "samples": steady(60.0, -40.0),
    }
    base.update(overrides)
    return base


def pressure_channel(**overrides):
    base = {
        "id": "P1-chamber",
        "role": "pressure",
        "required_interval_s": 300.0,
        "lower_limit": 1e-7,
        "upper_limit": 1e-3,
        "samples": steady(300.0, 5e-5),
    }
    base.update(overrides)
    return base


def functional_channel(**overrides):
    base = {
        "id": "F1-bus-voltage",
        "role": "functional",
        "required_interval_s": 600.0,
        "lower_limit": 4.5,
        "upper_limit": 5.5,
        "samples": steady(600.0, 5.0),
    }
    base.update(overrides)
    return base


def spec(**overrides):
    base = {
        "channels": [temperature_channel(), pressure_channel(), functional_channel()],
        "window_start_s": WINDOW[0],
        "window_end_s": WINDOW[1],
    }
    base.update(overrides)
    return base


class SampleValidationTests(unittest.TestCase):
    def test_valid_record_is_floats(self):
        self.assertEqual(validate_samples([(0, 1), (60, 2)]), [(0.0, 1.0), (60.0, 2.0)])

    def test_single_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_samples([(0.0, 1.0)])

    def test_repeated_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            validate_samples([(0.0, 1.0), (0.0, 2.0)])

    def test_negative_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_samples([(-1.0, 1.0), (60.0, 2.0)])

    def test_malformed_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_samples([(0.0, 1.0), (60.0, 2.0, 3.0)])


class ChannelValidationTests(unittest.TestCase):
    def test_valid_channel_normalises_identity(self):
        view = validate_channel(temperature_channel(id="  T1-baseplate "))
        self.assertEqual(view["id"], "T1-baseplate")

    def test_unknown_role_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(temperature_channel(role="vibration"))

    def test_inverted_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(temperature_channel(lower_limit=80.0, upper_limit=-45.0))

    def test_zero_required_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(temperature_channel(required_interval_s=0.0))

    def test_missing_key_rejected(self):
        bad = temperature_channel()
        del bad["samples"]
        with self.assertRaises(ValueError):
            validate_channel(bad)

    def test_non_mapping_channel_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(["T1-baseplate"])


class SamplingTests(unittest.TestCase):
    def test_intervals_are_the_successive_differences(self):
        intervals = sampling_intervals([(0.0, 1.0), (60.0, 1.0), (180.0, 1.0)])
        self.assertEqual(intervals, [60.0, 120.0])

    def test_regular_record_has_no_gap(self):
        record = validate_samples(steady(60.0, -40.0))
        self.assertEqual(recording_gaps(record, 60.0)["gaps"], [])

    def test_interval_exactly_at_the_gap_threshold_is_not_a_gap(self):
        record = validate_samples([(0.0, 1.0), (120.0, 1.0), (180.0, 1.0)])
        self.assertEqual(recording_gaps(record, 60.0, 2.0)["gaps"], [])

    def test_long_interval_is_reported_as_a_gap(self):
        record = validate_samples([(0.0, 1.0), (600.0, 1.0), (660.0, 1.0)])
        gaps = recording_gaps(record, 60.0)["gaps"]
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["span_s"], 600.0, places=9)

    def test_longest_interval_is_reported(self):
        record = validate_samples([(0.0, 1.0), (60.0, 1.0), (420.0, 1.0)])
        self.assertAlmostEqual(
            recording_gaps(record, 60.0)["longest_interval_s"], 360.0, places=9
        )

    def test_gap_factor_below_one_rejected(self):
        record = validate_samples(steady(60.0, -40.0))
        with self.assertRaises(ValueError):
            recording_gaps(record, 60.0, 0.5)

    def test_default_gap_factor_is_two(self):
        self.assertAlmostEqual(DEFAULT_GAP_FACTOR, 2.0, places=12)


class CoverageTests(unittest.TestCase):
    def test_full_record_covers_the_window(self):
        record = validate_samples(steady(60.0, -40.0))
        self.assertAlmostEqual(coverage_ratio(record, 0.0, 3600.0), 1.0, places=9)

    def test_half_record_covers_half_the_window(self):
        record = validate_samples(steady(60.0, -40.0, span_s=1800.0))
        self.assertAlmostEqual(coverage_ratio(record, 0.0, 3600.0), 0.5, places=9)

    def test_record_outside_the_window_covers_nothing(self):
        record = validate_samples([(7200.0, 1.0), (7260.0, 1.0)])
        self.assertAlmostEqual(coverage_ratio(record, 0.0, 3600.0), 0.0, places=12)

    def test_inverted_window_rejected(self):
        record = validate_samples(steady(60.0, -40.0))
        with self.assertRaises(ValueError):
            coverage_ratio(record, 3600.0, 0.0)


class ExcursionTests(unittest.TestCase):
    def test_in_limit_record_has_no_excursion(self):
        record = validate_samples(steady(60.0, -40.0))
        self.assertEqual(limit_excursions(record, -45.0, 80.0), [])

    def test_value_exactly_on_the_limit_is_not_an_excursion(self):
        record = validate_samples([(0.0, -45.0), (60.0, 80.0)])
        self.assertEqual(limit_excursions(record, -45.0, 80.0), [])

    def test_consecutive_out_of_limit_samples_merge_into_one_event(self):
        record = validate_samples(
            [(0.0, -40.0), (60.0, 90.0), (120.0, 95.0), (180.0, 92.0), (240.0, -40.0)]
        )
        events = limit_excursions(record, -45.0, 80.0)
        self.assertEqual(len(events), 1)
        self.assertAlmostEqual(events[0]["duration_s"], 120.0, places=9)
        self.assertAlmostEqual(events[0]["extreme_value"], 95.0, places=9)

    def test_two_separated_excursions_are_two_events(self):
        record = validate_samples(
            [(0.0, 90.0), (60.0, -40.0), (120.0, 90.0), (180.0, -40.0)]
        )
        self.assertEqual(len(limit_excursions(record, -45.0, 80.0)), 2)

    def test_side_is_reported(self):
        record = validate_samples([(0.0, -60.0), (60.0, -40.0)])
        self.assertEqual(limit_excursions(record, -45.0, 80.0)[0]["side"], "below")

    def test_a_side_change_splits_the_event(self):
        record = validate_samples([(0.0, -60.0), (60.0, 95.0), (120.0, -40.0)])
        events = limit_excursions(record, -45.0, 80.0)
        self.assertEqual([e["side"] for e in events], ["below", "above"])

    def test_inverted_limits_rejected(self):
        record = validate_samples(steady(60.0, -40.0))
        with self.assertRaises(ValueError):
            limit_excursions(record, 80.0, -45.0)


class ChannelAssessmentTests(unittest.TestCase):
    def test_clean_channel_is_acceptable(self):
        result = assess_channel(temperature_channel(), *WINDOW)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_coverage_exactly_at_the_minimum_is_met(self):
        result = assess_channel(temperature_channel(), *WINDOW, minimum_coverage=1.0)
        self.assertTrue(result["coverage_met"])
        self.assertLessEqual(abs(result["coverage_ratio"] - 1.0), COMPARISON_TOLERANCE)

    def test_short_record_fails_coverage(self):
        channel = temperature_channel(samples=steady(60.0, -40.0, span_s=600.0))
        result = assess_channel(channel, *WINDOW)
        self.assertFalse(result["coverage_met"])
        self.assertFalse(result["acceptable"])

    def test_gap_is_reported_as_a_finding(self):
        samples = steady(60.0, -40.0, span_s=600.0) + [(1800.0, -40.0), (1860.0, -40.0)]
        channel = temperature_channel(samples=samples)
        result = assess_channel(channel, 0.0, 1860.0)
        self.assertEqual(len(result["gaps"]), 1)
        self.assertTrue(any("no record between" in f for f in result["findings"]))

    def test_excursion_is_reported_as_a_finding(self):
        samples = steady(60.0, -40.0, span_s=1800.0)
        samples[10] = (600.0, 95.0)
        channel = temperature_channel(samples=samples + steady(60.0, -40.0)[31:])
        result = assess_channel(channel, *WINDOW)
        self.assertTrue(any("its limit" in f for f in result["findings"]))

    def test_minimum_coverage_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_channel(temperature_channel(), *WINDOW, minimum_coverage=1.5)


class RoleCoverageTests(unittest.TestCase):
    def test_all_three_roles_are_covered(self):
        result = role_coverage([temperature_channel(), pressure_channel(), functional_channel()])
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])

    def test_missing_role_is_named(self):
        result = role_coverage([temperature_channel(), pressure_channel()])
        self.assertEqual(result["missing"], ["functional"])

    def test_required_roles_are_the_three_families(self):
        self.assertEqual(set(REQUIRED_ROLES), {"temperature", "pressure", "functional"})

    def test_empty_channel_set_rejected(self):
        with self.assertRaises(ValueError):
            role_coverage([])


class MonitoringAssessmentTests(unittest.TestCase):
    def test_complete_plan_is_adequate(self):
        result = assess_monitoring(spec())
        self.assertTrue(result["adequate"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["gap_count"], 0)

    def test_missing_role_makes_the_record_inadequate(self):
        result = assess_monitoring(spec(channels=[temperature_channel(), pressure_channel()]))
        self.assertFalse(result["adequate"])
        self.assertIn("no channel monitors the functional role", result["findings"])

    def test_pressure_excursion_is_counted(self):
        samples = steady(300.0, 5e-5)
        samples[4] = (1200.0, 2e-3)
        channels = [temperature_channel(), pressure_channel(samples=samples),
                    functional_channel()]
        result = assess_monitoring(spec(channels=channels))
        self.assertEqual(result["excursion_count"], 1)
        self.assertFalse(result["adequate"])

    def test_functional_dropout_is_reported(self):
        samples = steady(600.0, 5.0)
        samples[3] = (1800.0, 3.2)
        channels = [temperature_channel(), pressure_channel(),
                    functional_channel(samples=samples)]
        result = assess_monitoring(spec(channels=channels))
        self.assertFalse(result["adequate"])
        self.assertTrue(any("F1-bus-voltage" in f for f in result["findings"]))

    def test_missing_spec_key_rejected(self):
        bad = spec()
        del bad["window_end_s"]
        with self.assertRaises(ValueError):
            assess_monitoring(bad)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_monitoring("channels")


if __name__ == "__main__":
    unittest.main()
