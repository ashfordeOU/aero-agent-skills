"""Contract tests for the paint application-environment control logic."""

import math
import unittest

from q7031_environmental_conditions_logic import (
    BAND_TOLERANCE,
    assess_application_environment,
    assess_cleanliness,
    dew_point_c,
    dew_point_margin_c,
    iso14644_limit_per_m3,
    validate_band,
    validate_relative_humidity,
    validate_temperature_c,
    within_band,
)

BASE = {
    "air_temperature_c": 22.0,
    "substrate_temperature_c": 22.0,
    "relative_humidity_pct": 45.0,
    "temperature_band": (15.0, 30.0),
    "humidity_band": (30.0, 65.0),
    "min_dew_point_margin_c": 3.0,
}


def spec(**overrides):
    out = dict(BASE)
    out.update(overrides)
    return out


class TemperatureValidationTests(unittest.TestCase):
    def test_returns_float(self):
        self.assertEqual(validate_temperature_c(21), 21.0)

    def test_non_numeric_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_c("21")

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_c(True)

    def test_non_finite_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_c(float("nan"))

    def test_implausible_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_c(-273.15)


class HumidityValidationTests(unittest.TestCase):
    def test_zero_humidity_accepted_by_validator(self):
        self.assertEqual(validate_relative_humidity(0), 0.0)

    def test_above_hundred_rejected(self):
        with self.assertRaises(ValueError):
            validate_relative_humidity(100.5)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_relative_humidity(-1.0)


class BandTests(unittest.TestCase):
    def test_band_returns_float_pair(self):
        self.assertEqual(validate_band((15, 30)), (15.0, 30.0))

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band((30.0, 15.0))

    def test_band_needs_two_entries(self):
        with self.assertRaises(ValueError):
            validate_band((15.0,))

    def test_value_on_the_lower_limit_is_inside(self):
        self.assertTrue(within_band(15.0, (15.0, 30.0)))

    def test_value_on_the_upper_limit_is_inside(self):
        self.assertTrue(within_band(30.0, (15.0, 30.0)))

    def test_value_outside_is_rejected(self):
        self.assertFalse(within_band(30.5, (15.0, 30.0)))

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            within_band(20.0, (15.0, 30.0), tolerance=-1.0)


class DewPointTests(unittest.TestCase):
    def test_saturated_air_dew_point_equals_air_temperature(self):
        self.assertAlmostEqual(dew_point_c(20.0, 100.0), 20.0, places=9)

    def test_dew_point_falls_as_humidity_falls(self):
        drier = dew_point_c(20.0, 30.0)
        damper = dew_point_c(20.0, 70.0)
        self.assertTrue(drier < damper - 1.0)

    def test_known_room_condition(self):
        self.assertAlmostEqual(dew_point_c(22.0, 45.0), 9.515, places=3)

    def test_zero_humidity_has_no_dew_point(self):
        with self.assertRaises(ValueError):
            dew_point_c(20.0, 0.0)

    def test_margin_is_substrate_minus_dew_point(self):
        margin = dew_point_margin_c(15.0, 22.0, 45.0)
        self.assertAlmostEqual(margin, 15.0 - dew_point_c(22.0, 45.0), places=12)

    def test_cold_substrate_gives_negative_margin(self):
        self.assertTrue(dew_point_margin_c(5.0, 22.0, 60.0) < 0.0)


class CleanlinessTests(unittest.TestCase):
    def test_limit_at_reference_size_is_the_decade(self):
        self.assertAlmostEqual(iso14644_limit_per_m3(8.0, 0.1), 1.0e8, places=0)

    def test_larger_particles_have_a_lower_limit(self):
        small = iso14644_limit_per_m3(8.0, 0.5)
        large = iso14644_limit_per_m3(8.0, 5.0)
        self.assertTrue(large * 10.0 < small)

    def test_class_outside_one_to_nine_rejected(self):
        with self.assertRaises(ValueError):
            iso14644_limit_per_m3(0.5, 0.5)

    def test_non_positive_size_rejected(self):
        with self.assertRaises(ValueError):
            iso14644_limit_per_m3(8.0, 0.0)

    def test_counts_on_the_limit_are_accepted(self):
        limit = iso14644_limit_per_m3(8.0, 0.5)
        result = assess_cleanliness({0.5: limit}, 8.0)
        self.assertTrue(result["within_limit"])

    def test_counts_over_the_limit_raise_a_finding(self):
        limit = iso14644_limit_per_m3(8.0, 0.5)
        result = assess_cleanliness({0.5: limit * 2.0}, 8.0)
        self.assertFalse(result["within_limit"])
        self.assertEqual(len(result["findings"]), 1)

    def test_empty_counts_rejected(self):
        with self.assertRaises(ValueError):
            assess_cleanliness({}, 8.0)

    def test_negative_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_cleanliness({0.5: -1.0}, 8.0)


class ApplicationEnvironmentTests(unittest.TestCase):
    def test_nominal_run_is_released(self):
        result = assess_application_environment(spec())
        self.assertTrue(result["release_to_spray"])
        self.assertEqual(result["findings"], [])

    def test_hot_booth_is_held(self):
        result = assess_application_environment(spec(air_temperature_c=34.0))
        self.assertFalse(result["release_to_spray"])
        self.assertFalse(result["temperature_within_band"])

    def test_humid_booth_is_held(self):
        result = assess_application_environment(spec(relative_humidity_pct=80.0))
        self.assertFalse(result["humidity_within_band"])

    def test_temperature_exactly_on_the_window_edge_is_released(self):
        result = assess_application_environment(spec(air_temperature_c=15.0))
        self.assertTrue(result["temperature_within_band"])

    def test_cold_substrate_fails_the_dew_point_margin(self):
        result = assess_application_environment(
            spec(substrate_temperature_c=10.0, relative_humidity_pct=60.0)
        )
        self.assertFalse(result["dew_point_margin_met"])
        self.assertFalse(result["release_to_spray"])

    def test_margin_exactly_on_the_requirement_is_met(self):
        dew = dew_point_c(22.0, 45.0)
        result = assess_application_environment(
            spec(substrate_temperature_c=dew + 3.0)
        )
        self.assertAlmostEqual(result["dew_point_margin_c"], 3.0, places=9)
        self.assertTrue(result["dew_point_margin_met"])

    def test_in_window_air_can_still_condense_on_a_cold_part(self):
        result = assess_application_environment(spec(substrate_temperature_c=8.0))
        self.assertTrue(result["temperature_within_band"])
        self.assertTrue(result["humidity_within_band"])
        self.assertFalse(result["release_to_spray"])

    def test_cleanliness_is_folded_into_the_verdict(self):
        limit = iso14644_limit_per_m3(8.0, 0.5)
        result = assess_application_environment(
            spec(iso_class=8.0, particle_counts={0.5: limit * 5.0})
        )
        self.assertFalse(result["release_to_spray"])
        self.assertIsNotNone(result["cleanliness"])

    def test_cleanliness_omitted_when_not_declared(self):
        self.assertIsNone(assess_application_environment(spec())["cleanliness"])

    def test_missing_key_rejected(self):
        broken = spec()
        del broken["humidity_band"]
        with self.assertRaises(ValueError):
            assess_application_environment(broken)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_application_environment(["air_temperature_c", 22.0])

    def test_negative_required_margin_rejected(self):
        with self.assertRaises(ValueError):
            assess_application_environment(spec(min_dew_point_margin_c=-1.0))

    def test_band_tolerance_is_small(self):
        self.assertTrue(BAND_TOLERANCE > 0.0)
        self.assertAlmostEqual(BAND_TOLERANCE, 1e-9, places=12)

    def test_findings_name_every_breach(self):
        result = assess_application_environment(
            spec(
                air_temperature_c=34.0,
                substrate_temperature_c=36.0,
                relative_humidity_pct=85.0,
            )
        )
        self.assertFalse(result["temperature_within_band"])
        self.assertFalse(result["humidity_within_band"])
        self.assertTrue(result["dew_point_margin_met"])
        self.assertEqual(len(result["findings"]), 2)

    def test_dew_point_is_reported(self):
        result = assess_application_environment(spec())
        self.assertTrue(math.isfinite(result["dew_point_c"]))


if __name__ == "__main__":
    unittest.main(verbosity=1)
