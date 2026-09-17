"""Contract tests for the clause 4.3 parameter-drift evaluation logic."""

import unittest

from q6015_radiation_effect_evaluation_basis_logic import (
    DEFAULT_REQUIRED_MARGIN,
    DRIFT_DIRECTIONS,
    LIMIT_TOLERANCE,
    assess_parameter_drift,
    capability_margin,
    crossing_level,
    evaluate_sample,
    excursion,
    limit_threshold,
    margin_holds,
    normalize_token,
    recovery_findings,
    relative_drift,
    validate_direction,
    validate_parameter,
    validate_readings,
    within_limit,
)

RISING = {
    "name": "input offset current",
    "pre_value": 10.0,
    "limit": 30.0,
    "direction": "increase",
}

FALLING = {
    "name": "current transfer ratio",
    "pre_value": 100.0,
    "limit": 60.0,
    "direction": "decrease",
}

BAND = {
    "name": "reference voltage",
    "pre_value": 2.500,
    "limit": 0.050,
    "direction": "either",
}

# Excursion 10 -> 20 -> 40: the limit of 30 is crossed halfway between the
# 2000 and 3000 steps, so the crossing lands on 2500.
RISING_READINGS = [(1000.0, 15.0), (2000.0, 20.0), (3000.0, 40.0)]


def _dataset(**overrides):
    dataset = {
        "parameter": dict(RISING),
        "samples": [{"sample_id": "S1", "readings": list(RISING_READINGS)}],
        "specified_level": 1000.0,
    }
    dataset.update(overrides)
    return dataset


class ParameterTests(unittest.TestCase):
    def test_every_direction_validates(self):
        for direction in DRIFT_DIRECTIONS:
            self.assertEqual(validate_direction(direction), direction)

    def test_unknown_direction_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_direction("sideways")

    def test_normalize_token_folds_case_and_underscores(self):
        self.assertEqual(normalize_token("Either"), "either")

    def test_rising_parameter_validates(self):
        entry = validate_parameter(dict(RISING))
        self.assertAlmostEqual(entry["limit"], 30.0, places=9)

    def test_parameter_missing_a_required_key_is_rejected(self):
        bad = dict(RISING)
        del bad["limit"]
        with self.assertRaises(ValueError):
            validate_parameter(bad)

    def test_parameter_already_outside_its_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(dict(RISING, pre_value=40.0))

    def test_falling_parameter_already_below_its_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(dict(FALLING, pre_value=50.0))

    def test_non_positive_two_sided_band_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(dict(BAND, limit=0.0))

    def test_non_mapping_parameter_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter("input offset current")

    def test_blank_parameter_name_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter(dict(RISING, name="  "))


class ExcursionTests(unittest.TestCase):
    def test_rising_excursion_is_the_reading_itself(self):
        entry = validate_parameter(dict(RISING))
        self.assertAlmostEqual(excursion(22.0, entry), 22.0, places=9)
        self.assertAlmostEqual(limit_threshold(entry), 30.0, places=9)

    def test_falling_excursion_rises_as_the_reading_falls(self):
        entry = validate_parameter(dict(FALLING))
        self.assertAlmostEqual(excursion(70.0, entry), -70.0, places=9)
        self.assertAlmostEqual(limit_threshold(entry), -60.0, places=9)

    def test_two_sided_excursion_is_the_absolute_drift(self):
        entry = validate_parameter(dict(BAND))
        self.assertAlmostEqual(excursion(2.470, entry), 0.030, places=9)
        self.assertAlmostEqual(excursion(2.530, entry), 0.030, places=9)

    def test_reading_inside_its_limit_is_within(self):
        entry = validate_parameter(dict(RISING))
        self.assertTrue(within_limit(29.0, entry))

    def test_reading_beyond_its_limit_is_not_within(self):
        entry = validate_parameter(dict(RISING))
        self.assertFalse(within_limit(31.0, entry))

    def test_reading_exactly_on_its_limit_is_within(self):
        entry = validate_parameter(dict(RISING))
        self.assertTrue(within_limit(30.0, entry))

    def test_falling_reading_exactly_on_its_limit_is_within(self):
        entry = validate_parameter(dict(FALLING))
        self.assertTrue(within_limit(60.0, entry))

    def test_two_sided_reading_on_the_band_edge_is_within(self):
        entry = validate_parameter(dict(BAND))
        self.assertTrue(within_limit(2.550, entry))
        self.assertTrue(within_limit(2.450, entry))

    def test_relative_drift_is_a_fraction_of_the_starting_value(self):
        self.assertAlmostEqual(relative_drift(10.0, 15.0), 0.5, places=9)

    def test_relative_drift_against_zero_is_refused(self):
        with self.assertRaises(ValueError):
            relative_drift(0.0, 15.0)

    def test_limit_tolerance_is_small_and_positive(self):
        self.assertGreater(LIMIT_TOLERANCE, 0.0)
        self.assertLess(LIMIT_TOLERANCE, 1e-6)


class ReadingTests(unittest.TestCase):
    def test_valid_readings_are_returned_point_for_point(self):
        points = validate_readings(list(RISING_READINGS))
        self.assertEqual(len(points), 3)

    def test_empty_reading_set_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_readings([])

    def test_readings_out_of_level_order_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_readings([(2000.0, 20.0), (1000.0, 15.0)])

    def test_repeated_level_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_readings([(1000.0, 15.0), (1000.0, 16.0)])

    def test_malformed_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_readings([(1000.0, 15.0), (2000.0,)])

    def test_zero_exposure_level_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_readings([(0.0, 15.0)])

    def test_monotonic_run_reports_no_recovery(self):
        entry = validate_parameter(dict(RISING))
        self.assertEqual(recovery_findings(list(RISING_READINGS), entry), [])

    def test_recovered_reading_is_reported(self):
        entry = validate_parameter(dict(RISING))
        findings = recovery_findings(
            [(1000.0, 20.0), (2000.0, 16.0), (3000.0, 40.0)], entry
        )
        self.assertEqual(len(findings), 1)


class CrossingTests(unittest.TestCase):
    def test_crossing_is_interpolated_between_the_bracketing_steps(self):
        result = crossing_level(dict(RISING), list(RISING_READINGS))
        self.assertTrue(result["crossed"])
        self.assertAlmostEqual(result["level"], 2500.0, places=9)
        self.assertFalse(result["censored"])

    def test_reading_landing_on_the_limit_does_not_cross(self):
        result = crossing_level(
            dict(RISING), [(1000.0, 15.0), (2000.0, 30.0)]
        )
        self.assertFalse(result["crossed"])
        self.assertTrue(result["censored"])

    def test_run_that_stays_inside_is_censored_at_the_highest_level(self):
        result = crossing_level(dict(RISING), [(1000.0, 12.0), (5000.0, 18.0)])
        self.assertTrue(result["censored"])
        self.assertIsNone(result["level"])
        self.assertAlmostEqual(result["highest_level"], 5000.0, places=9)

    def test_falling_parameter_crossing_is_interpolated_too(self):
        result = crossing_level(
            dict(FALLING), [(1000.0, 90.0), (2000.0, 80.0), (3000.0, 40.0)]
        )
        self.assertTrue(result["crossed"])
        self.assertAlmostEqual(result["level"], 2500.0, places=9)

    def test_two_sided_band_crossing_is_interpolated(self):
        result = crossing_level(
            dict(BAND), [(1000.0, 2.520), (2000.0, 2.530), (3000.0, 2.570)]
        )
        self.assertTrue(result["crossed"])
        self.assertAlmostEqual(result["level"], 2500.0, places=9)

    def test_first_reading_already_outside_crosses_below_it(self):
        result = crossing_level(dict(RISING), [(1000.0, 50.0)])
        self.assertTrue(result["crossed"])
        self.assertLess(result["level"], 1000.0)

    def test_crossing_requires_readings(self):
        with self.assertRaises(ValueError):
            crossing_level(dict(RISING), [])


class SampleAndDatasetTests(unittest.TestCase):
    def test_sample_carries_its_crossing_and_drifts(self):
        evaluated = evaluate_sample(
            dict(RISING), {"sample_id": "S1", "readings": list(RISING_READINGS)}
        )
        self.assertAlmostEqual(evaluated["crossing_level"], 2500.0, places=9)
        self.assertAlmostEqual(evaluated["relative_drifts"][0], 0.5, places=9)

    def test_sample_missing_a_required_key_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample(dict(RISING), {"readings": list(RISING_READINGS)})

    def test_non_mapping_sample_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample(dict(RISING), ["S1"])

    def test_margin_is_capability_over_specified_level(self):
        self.assertAlmostEqual(capability_margin(2500.0, 1000.0), 2.5, places=9)

    def test_margin_exactly_at_the_requirement_holds(self):
        self.assertTrue(margin_holds(2.0, 2.0))

    def test_margin_below_the_requirement_does_not_hold(self):
        self.assertFalse(margin_holds(1.5, 2.0))

    def test_default_required_margin_exceeds_unity(self):
        self.assertGreater(DEFAULT_REQUIRED_MARGIN, 1.0)

    def test_dataset_with_adequate_margin_is_acceptable(self):
        result = assess_parameter_drift(_dataset())
        self.assertAlmostEqual(result["capability"], 2500.0, places=9)
        self.assertAlmostEqual(result["margin"], 2.5, places=9)
        self.assertTrue(result["acceptable"])

    def test_worst_case_sample_sets_the_capability(self):
        result = assess_parameter_drift(
            _dataset(
                samples=[
                    {"sample_id": "S1", "readings": list(RISING_READINGS)},
                    {"sample_id": "S2",
                     "readings": [(1000.0, 20.0), (2000.0, 40.0)]},
                ]
            )
        )
        self.assertEqual(result["worst_case_sample"], "S2")
        self.assertAlmostEqual(result["capability"], 1500.0, places=9)

    def test_uncrossed_samples_give_a_censored_capability(self):
        result = assess_parameter_drift(
            _dataset(
                samples=[
                    {"sample_id": "S1", "readings": [(1000.0, 12.0),
                                                     (4000.0, 18.0)]},
                    {"sample_id": "S2", "readings": [(1000.0, 11.0),
                                                     (3000.0, 14.0)]},
                ]
            )
        )
        self.assertTrue(result["capability_censored"])
        self.assertEqual(result["worst_case_sample"], "S2")
        self.assertAlmostEqual(result["capability"], 3000.0, places=9)

    def test_short_margin_becomes_a_finding(self):
        result = assess_parameter_drift(_dataset(specified_level=2000.0))
        self.assertFalse(result["margin_holds"])
        self.assertFalse(result["acceptable"])

    def test_recovery_reaches_the_dataset_findings(self):
        result = assess_parameter_drift(
            _dataset(
                samples=[
                    {"sample_id": "S1",
                     "readings": [(1000.0, 20.0), (2000.0, 16.0),
                                  (3000.0, 40.0)]}
                ]
            )
        )
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("recovered" in f for f in result["findings"]))

    def test_sample_evaluated_twice_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_parameter_drift(
                _dataset(
                    samples=[
                        {"sample_id": "S1", "readings": list(RISING_READINGS)},
                        {"sample_id": "S1", "readings": list(RISING_READINGS)},
                    ]
                )
            )

    def test_empty_sample_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_parameter_drift(_dataset(samples=[]))

    def test_dataset_missing_a_required_key_is_rejected(self):
        bad = _dataset()
        del bad["specified_level"]
        with self.assertRaises(ValueError):
            assess_parameter_drift(bad)

    def test_non_mapping_dataset_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_parameter_drift(["parameter"])

    def test_project_margin_overrides_the_default(self):
        result = assess_parameter_drift(_dataset(required_margin=2.5))
        self.assertAlmostEqual(result["required_margin"], 2.5, places=9)
        self.assertTrue(result["margin_holds"])


if __name__ == "__main__":
    unittest.main()
