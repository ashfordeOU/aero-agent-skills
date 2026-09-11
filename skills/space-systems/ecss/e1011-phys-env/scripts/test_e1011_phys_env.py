#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C §4.2.1.6 physical and
psycho-physiological environment characterisation for human performance.

Exercises scripts/e1011_phys_env_logic.py (stdlib unittest, offline).
Contract: a parameter name maps to exactly "physical" or
"psychophysiological", and an unrecognized name raises; check_bounds
returns an in_bounds flag that is True when the value is within
[lower, upper] and False otherwise, default bounds are used when none
are supplied, inverted bounds raise, and an unknown parameter with no
explicit bounds raises; assess_coverage returns a sorted list of
required parameters missing from the assessed set and returns empty when
all required parameters are present; environment_review aggregates
out-of-bounds findings and coverage gaps, raises on an unknown parameter,
and returns empty lists when the environment is fully acceptable;
is_environment_acceptable is True only when both lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_phys_env_logic as pe  # noqa: E402

_ALL_IN_BOUNDS = {
    "temperature_c": 22.0,
    "relative_humidity_pct": 50.0,
    "noise_level_dba": 55.0,
    "rms_vibration_ms2": 0.1,
    "illuminance_lux": 500.0,
    "o2_partial_pressure_kpa": 21.0,
    "co2_partial_pressure_kpa": 0.1,
    "workload_index": 5.0,
    "stress_index": 4.0,
    "sleep_hours_per_day": 8.0,
}


class CategorizeParameterTest(unittest.TestCase):
    def test_temperature_is_physical(self):
        self.assertEqual(pe.categorize_parameter("temperature_c"), "physical")

    def test_noise_is_physical(self):
        self.assertEqual(pe.categorize_parameter("noise_level_dba"), "physical")

    def test_illuminance_is_physical(self):
        self.assertEqual(pe.categorize_parameter("illuminance_lux"), "physical")

    def test_workload_is_psychophysiological(self):
        self.assertEqual(
            pe.categorize_parameter("workload_index"), "psychophysiological"
        )

    def test_sleep_hours_is_psychophysiological(self):
        self.assertEqual(
            pe.categorize_parameter("sleep_hours_per_day"), "psychophysiological"
        )

    def test_stress_index_is_psychophysiological(self):
        self.assertEqual(
            pe.categorize_parameter("stress_index"), "psychophysiological"
        )

    def test_unknown_parameter_raises(self):
        with self.assertRaises(ValueError):
            pe.categorize_parameter("ionizing_radiation_gy")


class CheckBoundsTest(unittest.TestCase):
    def test_temperature_within_bounds(self):
        result = pe.check_bounds("temperature_c", 22.0)
        self.assertTrue(result["in_bounds"])

    def test_temperature_above_upper_bound(self):
        result = pe.check_bounds("temperature_c", 30.0)
        self.assertFalse(result["in_bounds"])

    def test_temperature_below_lower_bound(self):
        result = pe.check_bounds("temperature_c", 10.0)
        self.assertFalse(result["in_bounds"])

    def test_noise_at_upper_limit_is_in_bounds(self):
        result = pe.check_bounds("noise_level_dba", 68.0)
        self.assertTrue(result["in_bounds"])

    def test_noise_above_upper_limit_out_of_bounds(self):
        result = pe.check_bounds("noise_level_dba", 75.0)
        self.assertFalse(result["in_bounds"])

    def test_illuminance_below_lower_limit(self):
        result = pe.check_bounds("illuminance_lux", 100.0)
        self.assertFalse(result["in_bounds"])

    def test_co2_above_limit_out_of_bounds(self):
        result = pe.check_bounds("co2_partial_pressure_kpa", 0.8)
        self.assertFalse(result["in_bounds"])

    def test_custom_bounds_override_default(self):
        result = pe.check_bounds("temperature_c", 28.0, (18.0, 30.0))
        self.assertTrue(result["in_bounds"])

    def test_result_dict_has_expected_keys(self):
        result = pe.check_bounds("temperature_c", 22.0)
        for key in ("param", "value", "lower", "upper", "in_bounds"):
            self.assertIn(key, result)

    def test_inverted_bounds_raises(self):
        with self.assertRaises(ValueError):
            pe.check_bounds("temperature_c", 22.0, (30.0, 18.0))

    def test_unknown_param_without_bounds_raises(self):
        with self.assertRaises(ValueError):
            pe.check_bounds("ionizing_radiation_gy", 0.5)


class AssessCoverageTest(unittest.TestCase):
    def test_all_required_params_present_returns_empty(self):
        self.assertEqual(pe.assess_coverage(pe.ALL_REQUIRED_PARAMS), [])

    def test_missing_params_returned_sorted(self):
        missing = pe.assess_coverage(["temperature_c"])
        self.assertEqual(missing, sorted(missing))
        self.assertIn("co2_partial_pressure_kpa", missing)
        self.assertNotIn("temperature_c", missing)

    def test_empty_assessed_returns_all_required(self):
        missing = pe.assess_coverage([])
        self.assertEqual(len(missing), len(pe.ALL_REQUIRED_PARAMS))

    def test_custom_required_params_respected(self):
        missing = pe.assess_coverage(
            ["temperature_c"],
            required_params={"temperature_c", "noise_level_dba"},
        )
        self.assertEqual(missing, ["noise_level_dba"])


class EnvironmentReviewTest(unittest.TestCase):
    def test_fully_acceptable_review(self):
        review = pe.environment_review(_ALL_IN_BOUNDS)
        self.assertEqual(review["out_of_bounds"], [])
        self.assertEqual(review["missing_params"], [])
        self.assertTrue(pe.is_environment_acceptable(review))

    def test_out_of_bounds_param_flagged(self):
        params = dict(_ALL_IN_BOUNDS)
        params["temperature_c"] = 32.0
        review = pe.environment_review(params)
        self.assertEqual(len(review["out_of_bounds"]), 1)
        self.assertEqual(review["out_of_bounds"][0]["param"], "temperature_c")

    def test_missing_params_flagged(self):
        review = pe.environment_review({"temperature_c": 22.0})
        self.assertIn("noise_level_dba", review["missing_params"])
        self.assertNotIn("temperature_c", review["missing_params"])

    def test_unknown_param_raises(self):
        with self.assertRaises(ValueError):
            pe.environment_review({"ionizing_radiation_gy": 0.5})

    def test_custom_bounds_map_applied(self):
        params = dict(_ALL_IN_BOUNDS)
        params["co2_partial_pressure_kpa"] = 0.7
        review_default = pe.environment_review(params)
        self.assertEqual(len(review_default["out_of_bounds"]), 1)
        review_override = pe.environment_review(
            params, bounds_map={"co2_partial_pressure_kpa": (0.0, 1.0)}
        )
        self.assertEqual(review_override["out_of_bounds"], [])

    def test_is_not_acceptable_with_exceedance(self):
        params = dict(_ALL_IN_BOUNDS)
        params["stress_index"] = 9.0
        review = pe.environment_review(params)
        self.assertFalse(pe.is_environment_acceptable(review))

    def test_is_not_acceptable_with_missing_params(self):
        review = pe.environment_review({"temperature_c": 22.0})
        self.assertFalse(pe.is_environment_acceptable(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
