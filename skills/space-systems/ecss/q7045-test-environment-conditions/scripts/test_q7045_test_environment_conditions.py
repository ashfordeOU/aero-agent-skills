"""Contract tests for the metallic test environmental-conditions logic."""

import unittest

from q7045_test_environment_conditions_logic import (
    AMBIENT_BAND_C,
    MAX_EXCURSION_DEPTH_C,
    MIN_CONDITIONING_MINUTES,
    OXIDATION_THRESHOLD_C,
    REFERENCE_AMBIENT_C,
    assess_environment,
    band_excursions,
    condensation_risk,
    conditioning_minutes,
    dew_point_c,
    humidity_control_required,
    required_atmosphere,
    validate_series,
    within_band,
)


def sample(time_s, temperature_c=23.0, humidity_pct=45.0, window="loaded"):
    """One environmental log sample."""
    return {
        "time_s": time_s,
        "temperature_c": temperature_c,
        "humidity_pct": humidity_pct,
        "window": window,
    }


def steady_series():
    """Four minutes of a laboratory sitting comfortably inside its band."""
    return [
        sample(0.0, 22.8, 45.0, "conditioning"),
        sample(60.0, 23.0, 45.5, "conditioning"),
        sample(120.0, 23.1, 46.0, "loaded"),
        sample(180.0, 23.0, 45.0, "loaded"),
    ]


def run_spec(**overrides):
    """A room-temperature tensile run on an aluminium plate piece."""
    spec = {
        "series": steady_series(),
        "material_family": "aluminium-alloy",
        "test_type": "tensile",
        "test_temperature_c": REFERENCE_AMBIENT_C,
        "section_mm": 5.0,
        "soak_minutes": 30.0,
        "piece_temperature_c": 22.5,
        "atmosphere": "air",
    }
    spec.update(overrides)
    return spec


class SeriesValidationTests(unittest.TestCase):
    def test_a_well_formed_series_validates(self):
        self.assertEqual(len(validate_series(steady_series())), 4)

    def test_time_must_increase(self):
        series = steady_series()
        series[2]["time_s"] = 30.0
        with self.assertRaises(ValueError):
            validate_series(series)

    def test_sample_without_a_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([{"time_s": 0.0}])

    def test_humidity_outside_zero_to_hundred_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([sample(0.0, humidity_pct=140.0)])

    def test_unknown_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([sample(0.0, window="cooldown")])

    def test_window_defaults_to_loaded(self):
        series = validate_series([{"time_s": 0.0, "temperature_c": 23.0}])
        self.assertEqual(series[0]["window"], "loaded")

    def test_empty_series_rejected(self):
        with self.assertRaises(ValueError):
            validate_series([])


class BandTests(unittest.TestCase):
    def test_a_reading_inside_the_band_is_within(self):
        self.assertTrue(within_band(23.0, AMBIENT_BAND_C))

    def test_a_reading_exactly_on_the_lower_bound_is_within(self):
        self.assertAlmostEqual(AMBIENT_BAND_C[0], 18.0, places=9)
        self.assertTrue(within_band(AMBIENT_BAND_C[0], AMBIENT_BAND_C))

    def test_a_reading_exactly_on_the_upper_bound_is_within(self):
        self.assertTrue(within_band(AMBIENT_BAND_C[1], AMBIENT_BAND_C))

    def test_a_reading_well_outside_the_band_is_not(self):
        self.assertFalse(within_band(35.0, AMBIENT_BAND_C))

    def test_an_inverted_band_is_rejected(self):
        with self.assertRaises(ValueError):
            within_band(23.0, (28.0, 18.0))


class ExcursionTests(unittest.TestCase):
    def test_a_steady_series_produces_no_excursion(self):
        self.assertEqual(band_excursions(steady_series(), AMBIENT_BAND_C), [])

    def test_consecutive_out_of_band_samples_group_into_one_excursion(self):
        series = [
            sample(0.0, 23.0),
            sample(60.0, 30.0),
            sample(120.0, 31.0),
            sample(180.0, 23.0),
        ]
        excursions = band_excursions(series, AMBIENT_BAND_C)
        self.assertEqual(len(excursions), 1)
        self.assertAlmostEqual(excursions[0]["duration_s"], 60.0, places=9)
        self.assertAlmostEqual(excursions[0]["depth_c"], 3.0, places=9)

    def test_an_excursion_does_not_span_a_window_change(self):
        series = [
            sample(0.0, 30.0, window="conditioning"),
            sample(60.0, 30.0, window="loaded"),
        ]
        self.assertEqual(len(band_excursions(series, AMBIENT_BAND_C)), 2)

    def test_a_single_sample_excursion_has_zero_duration(self):
        series = [sample(0.0, 23.0), sample(60.0, 30.0), sample(120.0, 23.0)]
        self.assertAlmostEqual(
            band_excursions(series, AMBIENT_BAND_C)[0]["duration_s"], 0.0, places=9
        )

    def test_depth_is_measured_from_the_nearer_bound(self):
        series = [sample(0.0, 15.0)]
        self.assertAlmostEqual(
            band_excursions(series, AMBIENT_BAND_C)[0]["depth_c"], 3.0, places=9
        )


class HumidityAndCondensationTests(unittest.TestCase):
    def test_a_moisture_sensitive_family_owes_humidity_control(self):
        self.assertTrue(humidity_control_required("magnesium-alloy", "tensile"))

    def test_a_sustained_load_test_owes_humidity_control_on_any_material(self):
        self.assertTrue(humidity_control_required("aluminium-alloy", "sustained-load"))

    def test_a_plain_tensile_test_on_an_insensitive_alloy_does_not(self):
        self.assertFalse(humidity_control_required("aluminium-alloy", "tensile"))

    def test_dew_point_sits_below_the_room_temperature(self):
        self.assertLess(dew_point_c(23.0, 45.0), 23.0)

    def test_dew_point_at_saturation_equals_the_room_temperature(self):
        self.assertAlmostEqual(dew_point_c(23.0, 100.0), 23.0, places=9)

    def test_zero_humidity_rejected_by_the_dew_point(self):
        with self.assertRaises(ValueError):
            dew_point_c(23.0, 0.0)

    def test_a_cold_piece_in_a_humid_room_is_a_condensation_risk(self):
        self.assertTrue(condensation_risk(5.0, 23.0, 60.0)["risk"])

    def test_a_warm_piece_in_the_same_room_is_not(self):
        self.assertFalse(condensation_risk(22.0, 23.0, 45.0)["risk"])


class ConditioningAndAtmosphereTests(unittest.TestCase):
    def test_a_thin_section_gets_the_floor_conditioning_time(self):
        self.assertAlmostEqual(
            conditioning_minutes(2.0), MIN_CONDITIONING_MINUTES, places=9
        )

    def test_a_thick_section_gets_more_than_the_floor(self):
        self.assertGreater(conditioning_minutes(40.0), MIN_CONDITIONING_MINUTES)

    def test_non_positive_section_rejected(self):
        with self.assertRaises(ValueError):
            conditioning_minutes(0.0)

    def test_an_oxidising_alloy_hot_needs_an_inert_atmosphere(self):
        result = required_atmosphere("titanium-alloy", 600.0)
        self.assertEqual(result["atmosphere"], "inert-or-vacuum")

    def test_the_same_alloy_at_room_temperature_may_be_tested_in_air(self):
        self.assertEqual(required_atmosphere("titanium-alloy", 23.0)["atmosphere"], "air")

    def test_exactly_at_the_oxidation_threshold_stays_in_air(self):
        result = required_atmosphere("titanium-alloy", OXIDATION_THRESHOLD_C)
        self.assertEqual(result["atmosphere"], "air")

    def test_an_insensitive_alloy_stays_in_air_when_hot(self):
        self.assertEqual(
            required_atmosphere("stainless-steel", 600.0)["atmosphere"], "air"
        )


class AssessmentTests(unittest.TestCase):
    def test_a_steady_run_is_acceptable(self):
        result = assess_environment(run_spec())
        self.assertEqual(result["status"], "environment-acceptable")
        self.assertEqual(result["findings"], [])

    def test_an_excursion_during_loading_costs_the_result(self):
        series = steady_series()
        series[2]["temperature_c"] = 31.0
        result = assess_environment(run_spec(series=series))
        self.assertTrue(any("loaded window" in f for f in result["findings"]))

    def test_a_brief_shallow_excursion_while_conditioning_is_recoverable(self):
        series = steady_series()
        series[0]["temperature_c"] = 17.5
        result = assess_environment(run_spec(series=series))
        self.assertTrue(result["temperature_excursions"][0]["recoverable"])
        self.assertEqual(result["findings"], [])

    def test_a_deep_excursion_while_conditioning_is_not_recoverable(self):
        series = steady_series()
        series[0]["temperature_c"] = 10.0
        result = assess_environment(run_spec(series=series))
        self.assertFalse(result["temperature_excursions"][0]["recoverable"])
        self.assertTrue(any("conditioning-window" in f for f in result["findings"]))

    def test_excursion_depth_exactly_at_the_allowance_is_absorbed(self):
        series = steady_series()
        series[0]["temperature_c"] = AMBIENT_BAND_C[0] - MAX_EXCURSION_DEPTH_C
        result = assess_environment(run_spec(series=series))
        self.assertAlmostEqual(
            result["temperature_excursions"][0]["depth_c"],
            MAX_EXCURSION_DEPTH_C,
            places=9,
        )
        self.assertTrue(result["temperature_excursions"][0]["acceptable"])

    def test_an_uncontrolled_room_fails_a_moisture_sensitive_run(self):
        series = [
            {"time_s": 0.0, "temperature_c": 23.0, "window": "conditioning"},
            {"time_s": 60.0, "temperature_c": 23.0, "window": "loaded"},
        ]
        result = assess_environment(
            run_spec(series=series, material_family="magnesium-alloy",
                     piece_temperature_c=None)
        )
        self.assertTrue(any("controlled relative humidity" in f for f in result["findings"]))

    def test_a_piece_below_the_dew_point_stops_the_run(self):
        result = assess_environment(run_spec(piece_temperature_c=2.0))
        self.assertTrue(any("dew" in f for f in result["findings"]))

    def test_a_short_soak_on_a_thick_section_is_a_finding(self):
        result = assess_environment(run_spec(section_mm=40.0, soak_minutes=20.0))
        self.assertTrue(any("gradient" in f for f in result["findings"]))

    def test_a_soak_exactly_at_the_owed_time_is_accepted(self):
        owed = conditioning_minutes(40.0)
        result = assess_environment(run_spec(section_mm=40.0, soak_minutes=owed))
        self.assertAlmostEqual(result["conditioning_minutes_held"], owed, places=9)
        self.assertFalse(any("gradient" in f for f in result["findings"]))

    def test_a_hot_oxidising_alloy_declared_in_air_is_a_finding(self):
        result = assess_environment(
            run_spec(material_family="titanium-alloy", test_temperature_c=600.0,
                     atmosphere="air")
        )
        self.assertTrue(any("declared atmosphere" in f for f in result["findings"]))

    def test_the_same_run_under_argon_is_accepted(self):
        result = assess_environment(
            run_spec(material_family="titanium-alloy", test_temperature_c=600.0,
                     atmosphere="argon")
        )
        self.assertFalse(any("declared atmosphere" in f for f in result["findings"]))

    def test_missing_spec_key_rejected(self):
        spec = run_spec()
        del spec["soak_minutes"]
        with self.assertRaises(ValueError):
            assess_environment(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_environment(steady_series())

    def test_negative_soak_rejected(self):
        with self.assertRaises(ValueError):
            assess_environment(run_spec(soak_minutes=-1.0))


if __name__ == "__main__":
    unittest.main()
