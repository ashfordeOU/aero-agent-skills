"""Contract tests for the clause 8.7.10 coverglass boiling-water immersion."""

import unittest

from e2008_coverglass_boiling_water_test_logic import (
    BATH_NOT_BOILING,
    COATING_DAMAGE_EXCEEDS_LIMIT,
    COATING_WITHSTANDS_IMMERSION,
    DEFAULT_IMMERSION_POLICY,
    IMMERSION_TOO_SHORT,
    SAMPLE_COUNT_SHORT,
    SAMPLE_NOT_SINGLE_COATED,
    WATER_NOT_DEIONISED,
    assess_boiling_water_test,
    boil_threshold_c,
    boiling_point_c,
    coating_loss_fraction,
    hold_time_minutes,
    is_single_coated,
    peak_temperature_c,
    validate_immersion_policy,
    validate_sample,
    validate_temperature_log,
    water_is_deionised,
    worst_coating_loss_fraction,
)

SEA_LEVEL_KPA = 101.325

# Hand-worked boiling points, kept as an independent oracle rather than
# re-derived from the module: at the reference pressure the correction term
# vanishes and the boil sits at 100 C exactly; at 80 kPa the Clausius-
# Clapeyron correction moves it to roughly 93.39 C.
PLATEAU_KPA = 80.0
PLATEAU_BOIL_C = 93.39


def _policy(**overrides):
    policy = dict(DEFAULT_IMMERSION_POLICY)
    policy.update(overrides)
    return policy


def _sample(sample_id="CG-01", **overrides):
    sample = {
        "sample_id": sample_id,
        "coated_faces": 1,
        "coated_area_mm2": 1600.0,
        "affected_area_mm2": 0.0,
    }
    sample.update(overrides)
    return sample


def _batch(count=3, **overrides):
    return [_sample("CG-%02d" % number, **overrides) for number in range(1, count + 1)]


def _good_log():
    """Ramps to the boil in ten minutes, holds thirty-five, then cools."""
    return [(0.0, 20.0), (10.0, 100.0), (45.0, 100.0), (50.0, 60.0)]


def _case(**overrides):
    case = {
        "samples": _batch(),
        "water_conductivity_us_per_cm": 0.6,
        "ambient_pressure_kpa": SEA_LEVEL_KPA,
        "temperature_log": _good_log(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_immersion_policy(DEFAULT_IMMERSION_POLICY),
            DEFAULT_IMMERSION_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_immersion_policy("thirty minutes")

    def test_a_zero_duration_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_immersion_policy(_policy(min_immersion_minutes=0.0))

    def test_a_boil_margin_that_swallows_the_boil_rejected(self):
        with self.assertRaises(ValueError):
            validate_immersion_policy(_policy(boil_margin_c=25.0))

    def test_a_loss_acceptance_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_immersion_policy(_policy(max_coating_loss_fraction=1.0))

    def test_a_fractional_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_immersion_policy(_policy(min_sample_count=2.5))


class BoilingPointTests(unittest.TestCase):
    def test_the_reference_pressure_boils_at_one_hundred(self):
        self.assertAlmostEqual(boiling_point_c(SEA_LEVEL_KPA), 100.0, places=9)

    def test_a_plateau_pressure_boils_below_one_hundred(self):
        self.assertAlmostEqual(
            boiling_point_c(PLATEAU_KPA), PLATEAU_BOIL_C, places=2
        )

    def test_a_raised_pressure_boils_above_one_hundred(self):
        self.assertGreater(boiling_point_c(120.0) - 100.0, 1.0)

    def test_a_zero_pressure_rejected(self):
        with self.assertRaises(ValueError):
            boiling_point_c(0.0)

    def test_a_negative_pressure_rejected(self):
        with self.assertRaises(ValueError):
            boiling_point_c(-10.0)

    def test_the_threshold_sits_the_margin_below_the_boil(self):
        self.assertAlmostEqual(
            boil_threshold_c(SEA_LEVEL_KPA, 1.0), 99.0, places=9
        )

    def test_a_zero_margin_puts_the_threshold_on_the_boil(self):
        self.assertAlmostEqual(
            boil_threshold_c(SEA_LEVEL_KPA, 0.0), 100.0, places=9
        )

    def test_a_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            boil_threshold_c(SEA_LEVEL_KPA, -1.0)


class TemperatureLogTests(unittest.TestCase):
    def test_a_well_formed_log_validates(self):
        self.assertEqual(len(validate_temperature_log(_good_log())), 4)

    def test_mapping_readings_are_accepted(self):
        readings = validate_temperature_log(
            [
                {"elapsed_minutes": 0.0, "temperature_c": 20.0},
                {"elapsed_minutes": 5.0, "temperature_c": 99.5},
            ]
        )
        self.assertAlmostEqual(readings[1][1], 99.5, places=12)

    def test_a_single_reading_log_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_log([(0.0, 100.0)])

    def test_a_log_running_backwards_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_log([(10.0, 100.0), (5.0, 100.0)])

    def test_a_repeated_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_log([(5.0, 99.0), (5.0, 100.0)])

    def test_a_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_log([(0.0, -300.0), (5.0, 100.0)])

    def test_a_malformed_reading_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_log([(0.0, 20.0, "boil"), (5.0, 100.0)])

    def test_the_peak_is_the_hottest_reading(self):
        self.assertAlmostEqual(peak_temperature_c(_good_log()), 100.0, places=12)


class HoldTimeTests(unittest.TestCase):
    def test_the_hold_interpolates_both_crossings(self):
        """Hand-worked: 0.125 min in, 35 min flat, 0.125 min out."""
        self.assertAlmostEqual(
            hold_time_minutes(_good_log(), 99.0), 35.25, places=9
        )

    def test_a_log_wholly_above_the_threshold_holds_its_whole_span(self):
        self.assertAlmostEqual(
            hold_time_minutes([(0.0, 100.0), (40.0, 100.0)], 99.0), 40.0, places=12
        )

    def test_a_log_wholly_below_the_threshold_holds_nothing(self):
        self.assertAlmostEqual(
            hold_time_minutes([(0.0, 60.0), (40.0, 80.0)], 99.0), 0.0, places=12
        )

    def test_a_reading_exactly_on_the_threshold_counts_as_held(self):
        self.assertAlmostEqual(
            hold_time_minutes([(0.0, 99.0), (30.0, 99.0)], 99.0), 30.0, places=12
        )

    def test_a_ramp_crossing_at_the_midpoint_holds_half_the_span(self):
        self.assertAlmostEqual(
            hold_time_minutes([(0.0, 98.0), (20.0, 100.0)], 99.0), 10.0, places=12
        )

    def test_elapsed_time_is_not_hold_time(self):
        log = [(0.0, 20.0), (55.0, 99.0), (60.0, 99.0)]
        self.assertAlmostEqual(hold_time_minutes(log, 99.0), 5.0, places=9)


class WaterTests(unittest.TestCase):
    def test_pure_water_passes_the_conductivity_gate(self):
        self.assertTrue(water_is_deionised(0.3, 1.0))

    def test_water_exactly_on_the_limit_passes(self):
        self.assertTrue(water_is_deionised(1.0, 1.0))

    def test_process_water_fails_the_conductivity_gate(self):
        self.assertFalse(water_is_deionised(220.0, 1.0))

    def test_a_negative_conductivity_rejected(self):
        with self.assertRaises(ValueError):
            water_is_deionised(-1.0, 1.0)


class SampleTests(unittest.TestCase):
    def test_a_well_formed_sample_validates(self):
        sample = _sample()
        self.assertIs(validate_sample(sample), sample)

    def test_a_single_coated_sample_is_recognised(self):
        self.assertTrue(is_single_coated(_sample()))

    def test_a_two_face_sample_is_not_single_coated(self):
        self.assertFalse(is_single_coated(_sample(coated_faces=2)))

    def test_an_uncoated_sample_is_not_single_coated(self):
        self.assertFalse(is_single_coated(_sample(coated_faces=0)))

    def test_more_than_two_coated_faces_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(_sample(coated_faces=3))

    def test_a_missing_sample_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(_sample(sample_id="  "))

    def test_a_zero_coated_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(_sample(coated_area_mm2=0.0))

    def test_damage_larger_than_the_coated_face_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample(_sample(affected_area_mm2=2000.0))

    def test_the_loss_fraction_is_the_affected_share(self):
        self.assertAlmostEqual(
            coating_loss_fraction(_sample(affected_area_mm2=16.0)), 0.01, places=12
        )

    def test_the_worst_loss_in_the_batch_is_reported(self):
        batch = [_sample("CG-01"), _sample("CG-02", affected_area_mm2=32.0)]
        self.assertAlmostEqual(worst_coating_loss_fraction(batch), 0.02, places=12)

    def test_an_empty_batch_rejected(self):
        with self.assertRaises(ValueError):
            worst_coating_loss_fraction([])


class AssessmentTests(unittest.TestCase):
    def test_a_clean_run_passes(self):
        result = assess_boiling_water_test(_case())
        self.assertEqual(result["verdict"], COATING_WITHSTANDS_IMMERSION)
        self.assertEqual(result["findings"], [])

    def test_the_hold_and_threshold_travel_with_the_verdict(self):
        result = assess_boiling_water_test(_case())
        self.assertAlmostEqual(result["hold_minutes"], 35.25, places=9)
        self.assertAlmostEqual(result["boil_threshold_c"], 99.0, places=9)

    def test_a_two_face_sample_stops_the_run(self):
        batch = _batch()
        batch[1]["coated_faces"] = 2
        result = assess_boiling_water_test(_case(samples=batch))
        self.assertEqual(result["verdict"], SAMPLE_NOT_SINGLE_COATED)
        self.assertEqual(result["single_coated_samples"], 2)

    def test_a_short_batch_stops_the_run(self):
        result = assess_boiling_water_test(_case(samples=_batch(2)))
        self.assertEqual(result["verdict"], SAMPLE_COUNT_SHORT)

    def test_a_batch_exactly_on_the_minimum_passes(self):
        result = assess_boiling_water_test(_case(samples=_batch(3)))
        self.assertEqual(result["verdict"], COATING_WITHSTANDS_IMMERSION)

    def test_process_water_stops_the_run(self):
        result = assess_boiling_water_test(
            _case(water_conductivity_us_per_cm=180.0)
        )
        self.assertEqual(result["verdict"], WATER_NOT_DEIONISED)
        self.assertIsNone(result["hold_minutes"])

    def test_a_bath_that_never_boiled_stops_the_run(self):
        result = assess_boiling_water_test(
            _case(temperature_log=[(0.0, 20.0), (60.0, 90.0)])
        )
        self.assertEqual(result["verdict"], BATH_NOT_BOILING)

    def test_a_plateau_pressure_lowers_the_bar_the_bath_must_clear(self):
        result = assess_boiling_water_test(
            _case(
                ambient_pressure_kpa=PLATEAU_KPA,
                temperature_log=[(0.0, 20.0), (5.0, 93.0), (45.0, 93.0)],
            )
        )
        self.assertEqual(result["verdict"], COATING_WITHSTANDS_IMMERSION)
        self.assertAlmostEqual(result["boiling_point_c"], PLATEAU_BOIL_C, places=2)

    def test_a_short_hold_stops_the_run(self):
        result = assess_boiling_water_test(
            _case(temperature_log=[(0.0, 20.0), (10.0, 100.0), (25.0, 100.0)])
        )
        self.assertEqual(result["verdict"], IMMERSION_TOO_SHORT)

    def test_a_hold_exactly_on_the_minimum_passes(self):
        result = assess_boiling_water_test(
            _case(temperature_log=[(0.0, 100.0), (30.0, 100.0)])
        )
        self.assertAlmostEqual(result["hold_minutes"], 30.0, places=9)
        self.assertEqual(result["verdict"], COATING_WITHSTANDS_IMMERSION)

    def test_coating_loss_beyond_the_acceptance_fails(self):
        batch = _batch()
        batch[0]["affected_area_mm2"] = 64.0
        result = assess_boiling_water_test(_case(samples=batch))
        self.assertEqual(result["verdict"], COATING_DAMAGE_EXCEEDS_LIMIT)
        self.assertAlmostEqual(
            result["worst_coating_loss_fraction"], 0.04, places=12
        )

    def test_loss_exactly_on_the_acceptance_passes(self):
        batch = _batch()
        batch[0]["affected_area_mm2"] = 1.6
        result = assess_boiling_water_test(_case(samples=batch))
        self.assertAlmostEqual(
            result["worst_coating_loss_fraction"], 0.001, places=12
        )
        self.assertEqual(result["verdict"], COATING_WITHSTANDS_IMMERSION)

    def test_a_very_long_hold_raises_an_advisory(self):
        result = assess_boiling_water_test(
            _case(temperature_log=[(0.0, 100.0), (400.0, 100.0)])
        )
        self.assertEqual(result["verdict"], COATING_WITHSTANDS_IMMERSION)
        self.assertTrue(result["advisories"])

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_boiling_water_test(["samples"])

    def test_a_missing_samples_list_rejected(self):
        case = _case()
        del case["samples"]
        with self.assertRaises(ValueError):
            assess_boiling_water_test(case)

    def test_a_missing_temperature_log_rejected(self):
        case = _case()
        del case["temperature_log"]
        with self.assertRaises(ValueError):
            assess_boiling_water_test(case)

    def test_a_missing_water_reading_rejected(self):
        case = _case()
        del case["water_conductivity_us_per_cm"]
        with self.assertRaises(ValueError):
            assess_boiling_water_test(case)


if __name__ == "__main__":
    unittest.main()
