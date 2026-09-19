"""Contract tests for the elevated and low temperature metallic test logic."""

import unittest

from q7045_elevated_and_low_temperature_testing_logic import (
    MAX_THERMOCOUPLES,
    MIN_SOAK_MINUTES,
    THERMOCOUPLE_LENGTH_STEP_MM,
    assess_thermal_test,
    axial_gradient_c,
    axial_gradient_limit_c,
    device_rating_ok,
    deviation_allowance_c,
    loaded_window_stability_c,
    mean_temperature_c,
    required_soak_minutes,
    required_thermocouples,
    thermal_mode,
)


def hot_series(nominal=400.0, loaded_offset=0.5):
    """A soak followed by a loaded window held close to the nominal."""
    return [
        {"time_s": 0.0, "temperature_c": nominal - 1.0, "window": "soak"},
        {"time_s": 600.0, "temperature_c": nominal, "window": "soak"},
        {"time_s": 1200.0, "temperature_c": nominal + loaded_offset, "window": "loaded"},
        {"time_s": 1260.0, "temperature_c": nominal - loaded_offset, "window": "loaded"},
    ]


def hot_spec(**overrides):
    """A 400 degC tensile run on a 10 mm section, 60 mm parallel length."""
    spec = {
        "nominal_c": 400.0,
        "section_mm": 10.0,
        "parallel_length_mm": 60.0,
        "soak_minutes": 40.0,
        "piece_readings_c": [399.5, 400.0, 400.5],
        "series": hot_series(),
        "device_rating_c": (-50.0, 700.0),
    }
    spec.update(overrides)
    return spec


class AllowanceLadderTests(unittest.TestCase):
    def test_a_moderate_furnace_gets_the_mid_allowance(self):
        self.assertAlmostEqual(deviation_allowance_c(400.0), 3.0, places=9)

    def test_a_hotter_furnace_gets_a_wider_absolute_allowance(self):
        self.assertGreater(deviation_allowance_c(1000.0), deviation_allowance_c(400.0))

    def test_a_deep_cryogenic_nominal_gets_the_tight_allowance(self):
        self.assertAlmostEqual(deviation_allowance_c(-196.0), 2.0, places=9)

    def test_a_nominal_exactly_on_a_ladder_step_takes_that_step(self):
        self.assertAlmostEqual(deviation_allowance_c(600.0), 3.0, places=9)

    def test_a_nominal_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            deviation_allowance_c(-300.0)

    def test_non_numeric_nominal_rejected(self):
        with self.assertRaises(ValueError):
            deviation_allowance_c("400")


class ModeAndSoakTests(unittest.TestCase):
    def test_a_hot_nominal_is_an_elevated_run(self):
        self.assertEqual(thermal_mode(400.0), "elevated")

    def test_a_cryogenic_nominal_is_a_low_temperature_run(self):
        self.assertEqual(thermal_mode(-196.0), "low")

    def test_a_room_temperature_nominal_is_ambient(self):
        self.assertEqual(thermal_mode(23.0), "ambient")

    def test_a_cold_soak_is_slower_than_a_hot_one_on_the_same_section(self):
        self.assertGreater(
            required_soak_minutes(20.0, -196.0), required_soak_minutes(20.0, 400.0)
        )

    def test_a_thin_section_gets_the_floor_soak(self):
        self.assertAlmostEqual(
            required_soak_minutes(2.0, 400.0), MIN_SOAK_MINUTES, places=9
        )

    def test_a_thick_section_gets_more_than_the_floor(self):
        self.assertGreater(required_soak_minutes(40.0, 400.0), MIN_SOAK_MINUTES)

    def test_an_ambient_nominal_has_no_soak_under_this_clause(self):
        with self.assertRaises(ValueError):
            required_soak_minutes(10.0, 23.0)

    def test_a_non_positive_section_rejected(self):
        with self.assertRaises(ValueError):
            required_soak_minutes(0.0, 400.0)


class ThermocoupleTests(unittest.TestCase):
    def test_a_short_parallel_length_needs_one_point(self):
        self.assertEqual(required_thermocouples(THERMOCOUPLE_LENGTH_STEP_MM), 1)

    def test_a_longer_parallel_length_needs_more_points(self):
        self.assertEqual(required_thermocouples(THERMOCOUPLE_LENGTH_STEP_MM + 1.0), 2)

    def test_the_count_is_capped(self):
        self.assertEqual(required_thermocouples(5000.0), MAX_THERMOCOUPLES)

    def test_a_zero_parallel_length_rejected(self):
        with self.assertRaises(ValueError):
            required_thermocouples(0.0)


class ReadingStatisticsTests(unittest.TestCase):
    def test_the_mean_averages_the_points(self):
        self.assertAlmostEqual(mean_temperature_c([399.0, 400.0, 401.0]), 400.0, places=9)

    def test_the_gradient_is_the_spread_across_the_points(self):
        self.assertAlmostEqual(axial_gradient_c([399.0, 400.0, 402.0]), 3.0, places=9)

    def test_one_point_has_no_gradient(self):
        self.assertAlmostEqual(axial_gradient_c([400.0]), 0.0, places=9)

    def test_empty_readings_rejected(self):
        with self.assertRaises(ValueError):
            mean_temperature_c([])

    def test_the_gradient_limit_follows_the_allowance(self):
        self.assertAlmostEqual(
            axial_gradient_limit_c(400.0), deviation_allowance_c(400.0), places=9
        )


class LoadedWindowTests(unittest.TestCase):
    def test_the_worst_loaded_departure_is_returned(self):
        stability = loaded_window_stability_c(hot_series(loaded_offset=1.5), 400.0)
        self.assertAlmostEqual(stability["max_departure_c"], 1.5, places=9)

    def test_soak_samples_do_not_enter_the_loaded_verdict(self):
        series = hot_series()
        series[0]["temperature_c"] = 300.0
        stability = loaded_window_stability_c(series, 400.0)
        self.assertAlmostEqual(stability["max_departure_c"], 0.5, places=9)
        self.assertEqual(stability["loaded_samples"], 2)

    def test_a_series_with_no_loaded_sample_rejected(self):
        series = [{"time_s": 0.0, "temperature_c": 400.0, "window": "soak"}]
        with self.assertRaises(ValueError):
            loaded_window_stability_c(series, 400.0)

    def test_an_unknown_window_rejected(self):
        series = [{"time_s": 0.0, "temperature_c": 400.0, "window": "cooldown"}]
        with self.assertRaises(ValueError):
            loaded_window_stability_c(series, 400.0)

    def test_a_sample_missing_a_key_rejected(self):
        with self.assertRaises(ValueError):
            loaded_window_stability_c([{"time_s": 0.0, "window": "loaded"}], 400.0)


class DeviceRatingTests(unittest.TestCase):
    def test_a_device_covering_the_nominal_is_rated(self):
        self.assertTrue(device_rating_ok(400.0, -50.0, 700.0))

    def test_a_device_at_exactly_its_upper_rating_is_rated(self):
        self.assertTrue(device_rating_ok(700.0, -50.0, 700.0))

    def test_an_ambient_device_on_a_hot_piece_is_not_rated(self):
        self.assertFalse(device_rating_ok(400.0, 10.0, 40.0))

    def test_the_same_device_on_a_cryogenic_piece_is_not_rated(self):
        self.assertFalse(device_rating_ok(-196.0, 10.0, 40.0))

    def test_an_inverted_rating_rejected(self):
        with self.assertRaises(ValueError):
            device_rating_ok(400.0, 700.0, -50.0)


class AssessmentTests(unittest.TestCase):
    def test_a_well_controlled_hot_run_meets_the_thermal_rules(self):
        result = assess_thermal_test(hot_spec())
        self.assertEqual(result["status"], "thermal-control-met")
        self.assertEqual(result["findings"], [])

    def test_a_short_soak_leaves_a_cold_core(self):
        result = assess_thermal_test(hot_spec(section_mm=40.0, soak_minutes=30.0))
        self.assertTrue(any("cold core" in f or "not at temperature" in f
                            for f in result["findings"]))

    def test_a_soak_exactly_at_the_owed_time_is_accepted(self):
        owed = required_soak_minutes(40.0, 400.0)
        result = assess_thermal_test(hot_spec(section_mm=40.0, soak_minutes=owed))
        self.assertAlmostEqual(result["soak_minutes_held"], owed, places=9)
        self.assertFalse(any("owes" in f for f in result["findings"]))

    def test_one_thermocouple_on_a_long_piece_is_a_finding(self):
        result = assess_thermal_test(
            hot_spec(parallel_length_mm=150.0, piece_readings_c=[400.0])
        )
        self.assertTrue(any("gradient cannot be seen" in f for f in result["findings"]))

    def test_a_compliant_mean_with_a_gradient_still_fails(self):
        result = assess_thermal_test(hot_spec(piece_readings_c=[396.0, 400.0, 404.0]))
        self.assertAlmostEqual(result["mean_deviation_c"], 0.0, places=9)
        self.assertTrue(any("axial gradient" in f for f in result["findings"]))

    def test_a_mean_deviation_exactly_at_the_allowance_is_absorbed(self):
        nominal = 400.0
        allowance = deviation_allowance_c(nominal)
        readings = [nominal + allowance] * 3
        result = assess_thermal_test(
            hot_spec(piece_readings_c=readings,
                     series=hot_series(nominal=nominal, loaded_offset=0.5))
        )
        self.assertAlmostEqual(result["mean_deviation_c"], allowance, places=9)
        self.assertFalse(any("past the" in f and "allowance" in f
                             for f in result["findings"]))

    def test_a_mean_well_past_the_allowance_is_a_finding(self):
        result = assess_thermal_test(hot_spec(piece_readings_c=[380.0, 380.0, 380.0]))
        self.assertTrue(any("mean piece temperature" in f for f in result["findings"]))

    def test_a_drift_while_loaded_is_a_finding(self):
        result = assess_thermal_test(hot_spec(series=hot_series(loaded_offset=8.0)))
        self.assertTrue(any("while the piece was" in f for f in result["findings"]))

    def test_the_same_drift_during_the_soak_is_not(self):
        series = hot_series()
        series[0]["temperature_c"] = 380.0
        result = assess_thermal_test(hot_spec(series=series))
        self.assertEqual(result["findings"], [])

    def test_an_unrated_strain_device_is_a_finding(self):
        result = assess_thermal_test(hot_spec(device_rating_c=(10.0, 40.0)))
        self.assertTrue(any("outside its rating" in f for f in result["findings"]))

    def test_a_cryogenic_run_is_graded_on_the_tight_allowance(self):
        result = assess_thermal_test(
            hot_spec(
                nominal_c=-196.0,
                soak_minutes=60.0,
                piece_readings_c=[-196.5, -196.0, -195.5],
                series=hot_series(nominal=-196.0, loaded_offset=0.5),
                device_rating_c=(-269.0, 40.0),
            )
        )
        self.assertEqual(result["mode"], "low")
        self.assertAlmostEqual(result["allowance_c"], 2.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_an_ambient_nominal_is_routed_away_from_this_clause(self):
        with self.assertRaises(ValueError):
            assess_thermal_test(hot_spec(nominal_c=23.0))

    def test_missing_spec_key_rejected(self):
        spec = hot_spec()
        del spec["piece_readings_c"]
        with self.assertRaises(ValueError):
            assess_thermal_test(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_thermal_test([400.0])

    def test_the_allowance_travels_with_the_result(self):
        result = assess_thermal_test(hot_spec())
        self.assertAlmostEqual(
            result["allowance_c"], deviation_allowance_c(400.0), places=9
        )


if __name__ == "__main__":
    unittest.main()
