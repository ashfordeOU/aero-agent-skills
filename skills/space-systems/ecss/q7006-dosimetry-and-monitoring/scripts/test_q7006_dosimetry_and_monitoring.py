"""Contract tests for the exposure dosimetry and monitoring logic."""

import datetime
import math
import unittest

from q7006_dosimetry_and_monitoring_logic import (
    DEFAULT_DELIVERY_TOLERANCE_PCT,
    MINIMUM_MONITORS_PER_AGENT,
    MONITOR_AGREEMENT_LIMIT_PCT,
    accumulate_exposure,
    assess_dosimetry,
    calibration_expiry,
    calibration_in_date,
    combined_uncertainty_pct,
    delivery_verdict,
    monitor_deviation_pct,
    validate_monitor,
)

RUN_DATE = "2026-06-01"


def monitor(**overrides):
    record = {
        "name": "faraday-cup-a",
        "agent": "particles",
        "calibration_date": "2026-01-15",
        "calibration_interval_days": 365,
        "traceable": True,
        "uncertainty_pct": 3.0,
    }
    record.update(overrides)
    return record


def flat_samples(flux, seconds):
    return [(0.0, flux), (seconds, flux)]


def base_spec(**overrides):
    spec = {
        "run_date": RUN_DATE,
        "monitors": [
            monitor(name="cup-a"),
            monitor(name="cup-b"),
            monitor(name="uv-cell-a", agent="ultraviolet", uncertainty_pct=6.0),
            monitor(name="uv-cell-b", agent="ultraviolet", uncertainty_pct=6.0),
        ],
        "readings": {
            "cup-a": flat_samples(1.0e8, 3600.0),
            "cup-b": flat_samples(1.02e8, 3600.0),
            "uv-cell-a": flat_samples(2.0, 3600.0),
            "uv-cell-b": flat_samples(2.0, 3600.0),
        },
        "targets": {"particles": 3.6e11, "ultraviolet": 7200.0},
    }
    spec.update(overrides)
    return spec


class ValidateMonitorTests(unittest.TestCase):
    def test_name_is_stripped(self):
        self.assertEqual(validate_monitor(monitor(name=" cup "))["name"], "cup")

    def test_iso_date_is_parsed(self):
        self.assertEqual(
            validate_monitor(monitor())["calibration_date"], datetime.date(2026, 1, 15)
        )

    def test_date_object_is_accepted(self):
        record = validate_monitor(monitor(calibration_date=datetime.date(2025, 3, 4)))
        self.assertEqual(record["calibration_date"], datetime.date(2025, 3, 4))

    def test_unknown_agent_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitor(monitor(agent="neutrons"))

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitor(monitor(calibration_date="15/01/2026"))

    def test_non_boolean_traceable_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitor(monitor(traceable="yes"))

    def test_zero_calibration_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitor(monitor(calibration_interval_days=0))

    def test_float_calibration_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitor(monitor(calibration_interval_days=365.0))

    def test_missing_key_rejected(self):
        record = monitor()
        del record["uncertainty_pct"]
        with self.assertRaises(ValueError):
            validate_monitor(record)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitor(["name"])


class CalibrationTests(unittest.TestCase):
    def test_expiry_is_the_interval_after_calibration(self):
        self.assertEqual(calibration_expiry(monitor()), datetime.date(2027, 1, 15))

    def test_in_date_run_accepted(self):
        self.assertTrue(calibration_in_date(monitor(), RUN_DATE))

    def test_run_on_the_expiry_date_is_still_in_date(self):
        self.assertTrue(calibration_in_date(monitor(), "2027-01-15"))

    def test_run_one_day_past_expiry_is_out_of_date(self):
        self.assertFalse(calibration_in_date(monitor(), "2027-01-16"))

    def test_short_interval_expires_sooner(self):
        self.assertFalse(calibration_in_date(monitor(calibration_interval_days=30), RUN_DATE))

    def test_run_before_calibration_rejected(self):
        with self.assertRaises(ValueError):
            calibration_in_date(monitor(), "2025-12-31")


class AccumulationTests(unittest.TestCase):
    def test_flat_flux_integrates_to_flux_times_time(self):
        self.assertAlmostEqual(accumulate_exposure(flat_samples(1000.0, 60.0)), 60000.0, places=6)

    def test_linear_ramp_integrates_to_the_mean(self):
        self.assertAlmostEqual(
            accumulate_exposure([(0.0, 0.0), (10.0, 100.0)]), 500.0, places=9
        )

    def test_interior_samples_are_carried(self):
        whole = accumulate_exposure([(0.0, 100.0), (10.0, 100.0)])
        split = accumulate_exposure([(0.0, 100.0), (4.0, 100.0), (10.0, 100.0)])
        self.assertAlmostEqual(whole, split, places=9)

    def test_a_beam_trip_reduces_the_delivered_exposure(self):
        with_trip = accumulate_exposure([(0.0, 100.0), (5.0, 0.0), (10.0, 100.0)])
        self.assertLess(with_trip, accumulate_exposure([(0.0, 100.0), (10.0, 100.0)]))

    def test_single_sample_rejected(self):
        with self.assertRaises(ValueError):
            accumulate_exposure([(0.0, 100.0)])

    def test_unordered_samples_rejected(self):
        with self.assertRaises(ValueError):
            accumulate_exposure([(10.0, 100.0), (0.0, 100.0)])

    def test_negative_flux_rejected(self):
        with self.assertRaises(ValueError):
            accumulate_exposure([(0.0, -1.0), (10.0, 100.0)])

    def test_malformed_sample_rejected(self):
        with self.assertRaises(ValueError):
            accumulate_exposure([(0.0, 100.0), (10.0,)])


class UncertaintyTests(unittest.TestCase):
    def test_single_component_passes_through(self):
        self.assertAlmostEqual(combined_uncertainty_pct([4.0]), 4.0, places=9)

    def test_quadrature_of_three_four(self):
        self.assertAlmostEqual(combined_uncertainty_pct([3.0, 4.0]), 5.0, places=9)

    def test_combination_exceeds_each_component(self):
        combined = combined_uncertainty_pct([2.0, 2.0, 2.0])
        self.assertAlmostEqual(combined, math.sqrt(12.0), places=9)

    def test_zero_components_contribute_nothing(self):
        self.assertAlmostEqual(combined_uncertainty_pct([5.0, 0.0]), 5.0, places=9)

    def test_empty_component_list_rejected(self):
        with self.assertRaises(ValueError):
            combined_uncertainty_pct([])

    def test_negative_component_rejected(self):
        with self.assertRaises(ValueError):
            combined_uncertainty_pct([-1.0])


class AgreementAndVerdictTests(unittest.TestCase):
    def test_identical_readings_agree_exactly(self):
        self.assertAlmostEqual(monitor_deviation_pct(100.0, 100.0), 0.0, places=9)

    def test_deviation_is_relative_to_the_mean(self):
        self.assertAlmostEqual(monitor_deviation_pct(90.0, 110.0), 20.0, places=9)

    def test_deviation_is_symmetric(self):
        self.assertAlmostEqual(
            monitor_deviation_pct(90.0, 110.0), monitor_deviation_pct(110.0, 90.0), places=9
        )

    def test_zero_reading_rejected(self):
        with self.assertRaises(ValueError):
            monitor_deviation_pct(0.0, 100.0)

    def test_exact_delivery_is_within_tolerance(self):
        self.assertEqual(delivery_verdict(100.0, 100.0), "within-tolerance")

    def test_delivery_exactly_at_the_tolerance_edge_passes(self):
        edge = 100.0 * (1.0 + DEFAULT_DELIVERY_TOLERANCE_PCT / 100.0)
        self.assertEqual(delivery_verdict(edge, 100.0), "within-tolerance")

    def test_short_delivery_is_named(self):
        self.assertEqual(delivery_verdict(50.0, 100.0), "short-delivery")

    def test_overshoot_is_named(self):
        self.assertEqual(delivery_verdict(200.0, 100.0), "overshoot")

    def test_zero_target_rejected(self):
        with self.assertRaises(ValueError):
            delivery_verdict(10.0, 0.0)


class AssessDosimetryTests(unittest.TestCase):
    def test_clean_run_is_accepted(self):
        result = assess_dosimetry(base_spec())
        self.assertTrue(result["dosimetry_accepted"])
        self.assertEqual(result["findings"], [])

    def test_delivered_exposure_is_the_monitor_mean(self):
        result = assess_dosimetry(base_spec())
        self.assertAlmostEqual(
            result["agents"]["particles"]["delivered"],
            0.5 * (1.0e8 + 1.02e8) * 3600.0,
            places=3,
        )

    def test_uncertainty_is_combined_in_quadrature(self):
        result = assess_dosimetry(base_spec())
        self.assertAlmostEqual(
            result["agents"]["ultraviolet"]["combined_uncertainty_pct"],
            math.sqrt(6.0 ** 2 + 6.0 ** 2),
            places=9,
        )

    def test_single_monitor_on_an_agent_is_a_finding(self):
        spec = base_spec()
        spec["monitors"] = [m for m in spec["monitors"] if m["name"] != "cup-b"]
        del spec["readings"]["cup-b"]
        result = assess_dosimetry(spec)
        self.assertFalse(result["dosimetry_accepted"])
        self.assertTrue(any("drift" in note for note in result["findings"]))
        self.assertEqual(result["agents"]["particles"]["monitor_count"], 1)
        self.assertLess(result["agents"]["particles"]["monitor_count"], MINIMUM_MONITORS_PER_AGENT)

    def test_drifting_monitor_pair_is_a_finding(self):
        spec = base_spec()
        spec["readings"]["cup-b"] = flat_samples(2.0e8, 3600.0)
        result = assess_dosimetry(spec)
        self.assertGreater(
            result["agents"]["particles"]["worst_deviation_pct"], MONITOR_AGREEMENT_LIMIT_PCT
        )
        self.assertTrue(any("agreement limit" in note for note in result["findings"]))

    def test_expired_calibration_is_a_finding(self):
        spec = base_spec()
        spec["monitors"][0] = monitor(name="cup-a", calibration_interval_days=30)
        result = assess_dosimetry(spec)
        self.assertTrue(any("expired" in note for note in result["findings"]))

    def test_untraceable_calibration_is_a_finding(self):
        spec = base_spec()
        spec["monitors"][0] = monitor(name="cup-a", traceable=False)
        result = assess_dosimetry(spec)
        self.assertTrue(any("traceable" in note for note in result["findings"]))

    def test_short_delivery_is_a_finding(self):
        spec = base_spec(targets={"particles": 1.0e13, "ultraviolet": 7200.0})
        result = assess_dosimetry(spec)
        self.assertEqual(result["agents"]["particles"]["verdict"], "short-delivery")
        self.assertFalse(result["dosimetry_accepted"])

    def test_missing_reading_rejected(self):
        spec = base_spec()
        del spec["readings"]["uv-cell-a"]
        with self.assertRaises(ValueError):
            assess_dosimetry(spec)

    def test_missing_target_rejected(self):
        spec = base_spec(targets={"particles": 3.6e11})
        with self.assertRaises(ValueError):
            assess_dosimetry(spec)

    def test_duplicate_monitor_names_rejected(self):
        spec = base_spec()
        spec["monitors"][1]["name"] = "cup-a"
        with self.assertRaises(ValueError):
            assess_dosimetry(spec)

    def test_empty_monitor_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_dosimetry(base_spec(monitors=[]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_dosimetry(["run_date"])

    def test_run_date_is_echoed(self):
        self.assertEqual(assess_dosimetry(base_spec())["run_date"], RUN_DATE)


if __name__ == "__main__":
    unittest.main()
