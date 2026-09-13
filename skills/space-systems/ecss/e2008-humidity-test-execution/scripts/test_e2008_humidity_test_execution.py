"""Contract tests for the clause 5.5.1.4.4 humidity-test execution logic."""

import unittest

from e2008_humidity_test_execution_logic import (
    AMBIENT_PRESSURE_BAND_KPA,
    accumulate_dwell,
    assess_execution,
    sample_at_ambient_pressure,
    sample_conditioned,
    validate_band,
    validate_log,
    validate_sample,
    value_in_band,
)

# Control bands of a representative damp-heat run: 85 % relative humidity at
# 40 degC, chamber vented to the laboratory.
HUMIDITY_BAND = (83.0, 87.0)
TEMPERATURE_BAND = (38.0, 42.0)

NOMINAL = {"relative_humidity_pct": 85.0, "air_temperature_c": 40.0, "pressure_kpa": 101.3}


def _log(step=4.0, end=96.0, overrides=None):
    """Build a chamber log at a fixed sampling step, applying per-time overrides."""
    overrides = overrides or {}
    samples = []
    count = int(round(end / step)) + 1
    for i in range(count):
        time_h = i * step
        sample = dict(NOMINAL)
        sample["time_h"] = time_h
        sample.update(overrides.get(time_h, {}))
        samples.append(sample)
    return samples


def _spec(**overrides):
    spec = {
        "chamber_log": _log(),
        "humidity_band": HUMIDITY_BAND,
        "temperature_band": TEMPERATURE_BAND,
        "required_duration_h": 96.0,
    }
    spec.update(overrides)
    return spec


class BandValidationTests(unittest.TestCase):
    def test_band_returned_as_floats(self):
        self.assertEqual(validate_band((83, 87), "humidity"), (83.0, 87.0))

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band((87.0, 83.0), "humidity")

    def test_non_pair_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band((83.0,), "humidity")

    def test_non_numeric_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_band(("83", 87.0), "humidity")


class SampleValidationTests(unittest.TestCase):
    def test_sample_is_normalized_to_floats(self):
        sample = validate_sample(dict(NOMINAL, time_h=8), 2)
        self.assertAlmostEqual(sample["time_h"], 8.0)
        self.assertEqual(sample["index"], 2)

    def test_missing_field_rejected(self):
        broken = dict(NOMINAL, time_h=0.0)
        del broken["pressure_kpa"]
        with self.assertRaises(ValueError):
            validate_sample(broken, 0)

    def test_non_numeric_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(dict(NOMINAL, time_h=0.0, air_temperature_c="40"), 0)

    def test_negative_time_stamp_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(dict(NOMINAL, time_h=-1.0), 0)

    def test_humidity_above_saturation_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(dict(NOMINAL, time_h=0.0, relative_humidity_pct=120.0), 0)

    def test_negative_humidity_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(dict(NOMINAL, time_h=0.0, relative_humidity_pct=-5.0), 0)

    def test_zero_pressure_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(dict(NOMINAL, time_h=0.0, pressure_kpa=0.0), 0)

    def test_non_mapping_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample([0.0, 85.0], 0)


class LogValidationTests(unittest.TestCase):
    def test_ordered_log_is_accepted(self):
        self.assertEqual(len(validate_log(_log())), 25)

    def test_single_sample_log_rejected(self):
        with self.assertRaises(ValueError):
            validate_log([dict(NOMINAL, time_h=0.0)])

    def test_repeated_time_stamp_rejected(self):
        samples = _log(step=4.0, end=8.0)
        samples[2]["time_h"] = 4.0
        with self.assertRaises(ValueError):
            validate_log(samples)

    def test_out_of_order_log_rejected(self):
        samples = _log(step=4.0, end=8.0)
        samples[1]["time_h"] = 20.0
        with self.assertRaises(ValueError):
            validate_log(samples)


class BandMembershipTests(unittest.TestCase):
    def test_interior_value_is_in_band(self):
        self.assertTrue(value_in_band(85.0, HUMIDITY_BAND))

    def test_lower_edge_counts_as_in_band(self):
        self.assertAlmostEqual(83.0, HUMIDITY_BAND[0], places=9)
        self.assertTrue(value_in_band(83.0, HUMIDITY_BAND))

    def test_upper_edge_counts_as_in_band(self):
        self.assertAlmostEqual(87.0, HUMIDITY_BAND[1], places=9)
        self.assertTrue(value_in_band(87.0, HUMIDITY_BAND))

    def test_value_outside_the_band_is_refused(self):
        self.assertFalse(value_in_band(70.0, HUMIDITY_BAND))

    def test_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            value_in_band("85", HUMIDITY_BAND)


class SampleStateTests(unittest.TestCase):
    def test_nominal_sample_is_conditioned(self):
        self.assertTrue(sample_conditioned(NOMINAL, HUMIDITY_BAND, TEMPERATURE_BAND))

    def test_dry_sample_is_not_conditioned(self):
        dry = dict(NOMINAL, relative_humidity_pct=60.0)
        self.assertFalse(sample_conditioned(dry, HUMIDITY_BAND, TEMPERATURE_BAND))

    def test_cold_sample_is_not_conditioned(self):
        cold = dict(NOMINAL, air_temperature_c=20.0)
        self.assertFalse(sample_conditioned(cold, HUMIDITY_BAND, TEMPERATURE_BAND))

    def test_laboratory_pressure_is_ambient(self):
        self.assertTrue(sample_at_ambient_pressure(NOMINAL))

    def test_partially_evacuated_chamber_is_not_ambient(self):
        self.assertFalse(sample_at_ambient_pressure(dict(NOMINAL, pressure_kpa=50.0)))

    def test_missing_pressure_rejected(self):
        broken = dict(NOMINAL)
        del broken["pressure_kpa"]
        with self.assertRaises(ValueError):
            sample_at_ambient_pressure(broken)

    def test_wider_pressure_band_admits_a_mountain_laboratory(self):
        self.assertTrue(sample_at_ambient_pressure(dict(NOMINAL, pressure_kpa=80.0),
                                                   (78.0, 106.0)))


class DwellAccountingTests(unittest.TestCase):
    def test_clean_run_dwells_for_the_whole_span(self):
        accounting = accumulate_dwell(_log(), HUMIDITY_BAND, TEMPERATURE_BAND)
        self.assertAlmostEqual(accounting["conditioned_dwell_h"], 96.0, places=9)
        self.assertAlmostEqual(accounting["log_span_h"], 96.0, places=9)

    def test_clean_run_records_no_excursion(self):
        accounting = accumulate_dwell(_log(), HUMIDITY_BAND, TEMPERATURE_BAND)
        self.assertAlmostEqual(accounting["excursion_h"], 0.0, places=9)
        self.assertEqual(accounting["excursion_count"], 0)

    def test_one_dry_sample_voids_both_adjacent_intervals(self):
        log = _log(overrides={40.0: {"relative_humidity_pct": 60.0}})
        accounting = accumulate_dwell(log, HUMIDITY_BAND, TEMPERATURE_BAND)
        self.assertAlmostEqual(accounting["conditioned_dwell_h"], 88.0, places=9)
        self.assertAlmostEqual(accounting["longest_excursion_h"], 8.0, places=9)

    def test_separate_dips_are_counted_as_separate_excursions(self):
        log = _log(overrides={20.0: {"air_temperature_c": 20.0},
                              60.0: {"air_temperature_c": 20.0}})
        accounting = accumulate_dwell(log, HUMIDITY_BAND, TEMPERATURE_BAND)
        self.assertEqual(accounting["excursion_count"], 2)
        self.assertAlmostEqual(accounting["excursion_h"], 16.0, places=9)

    def test_pressure_loss_is_accounted_separately(self):
        log = _log(overrides={40.0: {"pressure_kpa": 40.0}})
        accounting = accumulate_dwell(log, HUMIDITY_BAND, TEMPERATURE_BAND)
        self.assertAlmostEqual(accounting["pressure_excursion_h"], 8.0, places=9)
        self.assertAlmostEqual(accounting["conditioned_dwell_h"], 88.0, places=9)

    def test_sample_count_is_reported(self):
        accounting = accumulate_dwell(_log(), HUMIDITY_BAND, TEMPERATURE_BAND)
        self.assertEqual(accounting["sample_count"], 25)

    def test_excursion_at_the_end_of_the_run_is_closed_out(self):
        log = _log(overrides={96.0: {"relative_humidity_pct": 60.0}})
        accounting = accumulate_dwell(log, HUMIDITY_BAND, TEMPERATURE_BAND)
        self.assertEqual(accounting["excursion_count"], 1)
        self.assertAlmostEqual(accounting["longest_excursion_h"], 4.0, places=9)

    def test_inverted_temperature_band_rejected(self):
        with self.assertRaises(ValueError):
            accumulate_dwell(_log(), HUMIDITY_BAND, (42.0, 38.0))


class ExecutionAssessmentTests(unittest.TestCase):
    def test_nominal_run_meets_the_defined_duration(self):
        result = assess_execution(_spec())
        self.assertAlmostEqual(result["conditioned_dwell_h"],
                               result["required_duration_h"], places=9)
        self.assertTrue(result["duration_satisfied"])
        self.assertEqual(result["findings"], [])

    def test_short_run_is_a_dwell_shortfall(self):
        result = assess_execution(_spec(required_duration_h=120.0))
        self.assertFalse(result["duration_satisfied"])
        self.assertIn("falls short", result["findings"][0])

    def test_long_single_excursion_is_flagged(self):
        log = _log(overrides={40.0: {"relative_humidity_pct": 60.0}})
        result = assess_execution(_spec(chamber_log=log, required_duration_h=80.0))
        self.assertEqual(
            len([f for f in result["findings"] if "single control excursion" in f]), 1
        )

    def test_cumulative_excursion_is_flagged_on_its_own(self):
        # One-hour sampling, three separate one-sample dips: each excursion is
        # two hours and stays inside the per-excursion limit, while the six
        # hours together break the cumulative limit.
        log = _log(step=1.0, overrides={20.0: {"relative_humidity_pct": 60.0},
                                        50.0: {"relative_humidity_pct": 60.0},
                                        80.0: {"relative_humidity_pct": 60.0}})
        result = assess_execution(
            _spec(chamber_log=log, required_duration_h=88.0,
                  max_single_excursion_h=2.0, max_cumulative_excursion_h=4.0)
        )
        self.assertAlmostEqual(result["longest_excursion_h"], 2.0, places=9)
        self.assertEqual(
            len([f for f in result["findings"] if "single control excursion" in f]), 0
        )
        self.assertEqual(
            len([f for f in result["findings"] if "cumulative control excursion" in f]), 1
        )

    def test_departure_from_ambient_pressure_is_flagged(self):
        log = _log(overrides={40.0: {"pressure_kpa": 40.0}})
        result = assess_execution(_spec(chamber_log=log, required_duration_h=80.0,
                                        max_single_excursion_h=12.0))
        self.assertEqual(
            len([f for f in result["findings"] if "ambient pressure band" in f]), 1
        )

    def test_declared_pressure_band_is_honoured(self):
        log = _log(overrides={40.0: {"pressure_kpa": 80.0}})
        result = assess_execution(_spec(chamber_log=log, pressure_band=(78.0, 106.0)))
        self.assertTrue(result["duration_satisfied"])

    def test_default_pressure_band_is_the_laboratory_band(self):
        self.assertAlmostEqual(AMBIENT_PRESSURE_BAND_KPA[1], 106.0, places=9)

    def test_limits_are_echoed_back(self):
        result = assess_execution(_spec(max_single_excursion_h=3.0))
        self.assertAlmostEqual(result["max_single_excursion_h"], 3.0, places=9)

    def test_zero_required_duration_rejected(self):
        with self.assertRaises(ValueError):
            assess_execution(_spec(required_duration_h=0.0))

    def test_negative_excursion_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_execution(_spec(max_cumulative_excursion_h=-1.0))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["humidity_band"]
        with self.assertRaises(ValueError):
            assess_execution(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_execution(["chamber_log"])


if __name__ == "__main__":
    unittest.main()
