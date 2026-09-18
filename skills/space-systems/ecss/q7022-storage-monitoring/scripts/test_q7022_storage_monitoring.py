"""Contract test for the storage-monitoring leaf (stdlib unittest)."""

import unittest

from q7022_storage_monitoring_logic import (
    accumulated_excursion_h,
    assess_storage_monitoring,
    excursion_events,
    is_out_of_limit,
    monitoring_coverage,
    peak_deviation,
    reading_deviation,
    validate_envelope,
    validate_readings,
)

ENV = {"temp_min_c": 15.0, "temp_max_c": 25.0, "rh_max_pct": 60.0}


def reading(elapsed_h, temp_c=20.0, rh_pct=45.0):
    return {"elapsed_h": elapsed_h, "temp_c": temp_c, "rh_pct": rh_pct}


def clean_series():
    return [reading(0.0), reading(6.0), reading(12.0), reading(18.0), reading(24.0)]


def spec(**kw):
    base = {
        "envelope": ENV,
        "readings": clean_series(),
        "period_h": 24.0,
        "required_interval_h": 6.0,
        "allowed_excursion_h": 4.0,
    }
    base.update(kw)
    return base


class TestValidateEnvelope(unittest.TestCase):
    def test_valid_envelope_is_normalised(self):
        env = validate_envelope(ENV)
        self.assertAlmostEqual(env["temp_max_c"], 25.0, places=9)

    def test_inverted_band_raises(self):
        with self.assertRaises(ValueError):
            validate_envelope({"temp_min_c": 30.0, "temp_max_c": 10.0, "rh_max_pct": 60.0})

    def test_humidity_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            validate_envelope({"temp_min_c": 15.0, "temp_max_c": 25.0, "rh_max_pct": 0.0})

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_envelope([15.0, 25.0, 60.0])


class TestValidateReadings(unittest.TestCase):
    def test_clean_series_passes(self):
        self.assertEqual(len(validate_readings(clean_series(), 24.0)), 5)

    def test_non_advancing_time_raises(self):
        with self.assertRaises(ValueError):
            validate_readings([reading(0.0), reading(6.0), reading(6.0)], 24.0)

    def test_reading_past_the_period_raises(self):
        with self.assertRaises(ValueError):
            validate_readings([reading(0.0), reading(30.0)], 24.0)

    def test_single_sample_raises(self):
        with self.assertRaises(ValueError):
            validate_readings([reading(0.0)], 24.0)

    def test_humidity_above_one_hundred_raises(self):
        with self.assertRaises(ValueError):
            validate_readings([reading(0.0), reading(6.0, rh_pct=110.0)], 24.0)

    def test_boolean_temperature_raises(self):
        with self.assertRaises(ValueError):
            validate_readings([reading(0.0), reading(6.0, temp_c=True)], 24.0)

    def test_non_positive_period_raises(self):
        with self.assertRaises(ValueError):
            validate_readings(clean_series(), 0.0)


class TestDeviation(unittest.TestCase):
    def test_in_band_reading_has_no_deviation(self):
        deviation = reading_deviation(reading(0.0), ENV)
        self.assertAlmostEqual(deviation["temperature_high_c"], 0.0, places=9)
        self.assertFalse(is_out_of_limit(reading(0.0), ENV))

    def test_exact_band_edge_is_in_limit(self):
        self.assertFalse(is_out_of_limit(reading(0.0, temp_c=25.0, rh_pct=60.0), ENV))

    def test_hot_reading_reports_the_high_axis_only(self):
        deviation = reading_deviation(reading(0.0, temp_c=28.5), ENV)
        self.assertAlmostEqual(deviation["temperature_high_c"], 3.5, places=9)
        self.assertAlmostEqual(deviation["temperature_low_c"], 0.0, places=9)

    def test_cold_reading_reports_the_low_axis(self):
        deviation = reading_deviation(reading(0.0, temp_c=11.0), ENV)
        self.assertAlmostEqual(deviation["temperature_low_c"], 4.0, places=9)

    def test_wet_reading_reports_the_humidity_axis(self):
        deviation = reading_deviation(reading(0.0, rh_pct=72.0), ENV)
        self.assertAlmostEqual(deviation["humidity_pct"], 12.0, places=9)
        self.assertTrue(is_out_of_limit(reading(0.0, rh_pct=72.0), ENV))


class TestCoverage(unittest.TestCase):
    def test_even_cadence_is_fully_monitored(self):
        cover = monitoring_coverage(clean_series(), 24.0, 6.0)
        self.assertTrue(cover["cadence_met"])
        self.assertAlmostEqual(cover["monitored_fraction"], 1.0, places=9)
        self.assertAlmostEqual(cover["widest_gap_h"], 6.0, places=9)

    def test_a_gap_wider_than_the_interval_is_unmonitored_time(self):
        cover = monitoring_coverage([reading(0.0), reading(6.0), reading(24.0)], 24.0, 6.0)
        self.assertFalse(cover["cadence_met"])
        self.assertEqual(cover["gap_breaches"], 1)
        self.assertAlmostEqual(cover["unmonitored_h"], 12.0, places=9)
        self.assertAlmostEqual(cover["monitored_fraction"], 0.5, places=9)

    def test_a_late_first_sample_is_also_a_gap(self):
        cover = monitoring_coverage([reading(20.0), reading(24.0)], 24.0, 6.0)
        self.assertEqual(cover["gap_breaches"], 1)
        self.assertAlmostEqual(cover["widest_gap_h"], 20.0, places=9)

    def test_non_positive_interval_raises(self):
        with self.assertRaises(ValueError):
            monitoring_coverage(clean_series(), 24.0, 0.0)


class TestExcursionAccounting(unittest.TestCase):
    def test_clean_series_accumulates_no_excursion(self):
        self.assertAlmostEqual(accumulated_excursion_h(clean_series(), ENV, 24.0), 0.0, places=9)

    def test_midpoint_rule_splits_the_shoulder_intervals(self):
        series = [reading(0.0), reading(6.0), reading(12.0, temp_c=30.0), reading(18.0),
                  reading(24.0)]
        self.assertAlmostEqual(accumulated_excursion_h(series, ENV, 24.0), 6.0, places=9)

    def test_two_adjacent_hot_samples_own_the_whole_interval(self):
        series = [reading(0.0), reading(6.0, temp_c=30.0), reading(12.0, temp_c=30.0),
                  reading(18.0), reading(24.0)]
        self.assertAlmostEqual(accumulated_excursion_h(series, ENV, 24.0), 12.0, places=9)

    def test_events_group_consecutive_out_of_limit_samples(self):
        series = [reading(0.0), reading(6.0, temp_c=30.0), reading(12.0, temp_c=31.0),
                  reading(18.0), reading(24.0, rh_pct=80.0)]
        events = excursion_events(series, ENV, 24.0)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["sample_count"], 2)
        self.assertEqual(events[0]["axes"], ["temperature_high_c"])
        self.assertEqual(events[1]["axes"], ["humidity_pct"])

    def test_peak_deviation_is_the_largest_single_axis_excess(self):
        series = [reading(0.0), reading(6.0, temp_c=30.0), reading(12.0, rh_pct=80.0),
                  reading(18.0), reading(24.0)]
        self.assertAlmostEqual(peak_deviation(series, ENV, 24.0), 20.0, places=9)

    def test_no_event_gives_zero_peak(self):
        self.assertAlmostEqual(peak_deviation(clean_series(), ENV, 24.0), 0.0, places=9)


class TestAssessStorageMonitoring(unittest.TestCase):
    def test_clean_record_is_no_excursion(self):
        report = assess_storage_monitoring(spec())
        self.assertEqual(report["disposition"], "no-excursion")
        self.assertTrue(report["acceptable"])
        self.assertEqual(report["findings"], [])

    def test_small_excursion_stays_within_allowance(self):
        series = [reading(0.0), reading(6.0), reading(12.0, temp_c=27.0), reading(18.0),
                  reading(24.0)]
        report = assess_storage_monitoring(spec(readings=series, allowed_excursion_h=8.0))
        self.assertEqual(report["disposition"], "exposure-within-allowance")
        self.assertTrue(report["acceptable"])

    def test_exposure_at_the_allowance_is_not_a_breach(self):
        series = [reading(0.0), reading(6.0), reading(12.0, temp_c=27.0), reading(18.0),
                  reading(24.0)]
        report = assess_storage_monitoring(spec(readings=series, allowed_excursion_h=6.0))
        self.assertAlmostEqual(report["accumulated_excursion_h"], 6.0, places=9)
        self.assertTrue(report["acceptable"])

    def test_exposure_beyond_the_allowance_is_reported(self):
        series = [reading(0.0), reading(6.0, temp_c=30.0), reading(12.0, temp_c=30.0),
                  reading(18.0), reading(24.0)]
        report = assess_storage_monitoring(spec(readings=series))
        self.assertEqual(report["disposition"], "exposure-exceeded")
        self.assertFalse(report["acceptable"])
        self.assertEqual(len(report["findings"]), 1)

    def test_peak_limit_can_fail_a_short_excursion(self):
        series = [reading(0.0), reading(6.0), reading(12.0, temp_c=45.0), reading(18.0),
                  reading(24.0)]
        report = assess_storage_monitoring(spec(readings=series, allowed_excursion_h=12.0,
                                                peak_deviation_limit=5.0))
        self.assertEqual(report["disposition"], "exposure-exceeded")
        self.assertAlmostEqual(report["peak_deviation"], 20.0, places=9)

    def test_an_inadequate_record_outranks_the_exposure_verdict(self):
        series = [reading(0.0), reading(6.0, temp_c=30.0), reading(24.0, temp_c=30.0)]
        report = assess_storage_monitoring(spec(readings=series))
        self.assertEqual(report["disposition"], "record-inadequate")
        self.assertFalse(report["acceptable"])

    def test_missing_key_raises(self):
        broken = spec()
        del broken["allowed_excursion_h"]
        with self.assertRaises(ValueError):
            assess_storage_monitoring(broken)

    def test_negative_allowance_raises(self):
        with self.assertRaises(ValueError):
            assess_storage_monitoring(spec(allowed_excursion_h=-1.0))

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_storage_monitoring(clean_series())


if __name__ == "__main__":
    unittest.main()
