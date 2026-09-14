"""Contract tests for the clause 6.4.3.18.3 life test acceptance criterion."""

import unittest

from e2008_long_duration_life_test_criteria_logic import (
    DEFAULT_CRITERIA_POLICY,
    DEGRADATION_EXCEEDS_LIMIT,
    DEGRADATION_WITHIN_LIMIT,
    REFERENCE_NOT_ESTABLISHED,
    assess_long_duration_life_test_criteria,
    corrected_pmax_w,
    degradation_percent,
    initial_reference_w,
    maximum_degradation_percent,
    reading_series,
    recovered_excursions,
    series_degradations,
    validate_criteria_policy,
    validate_reading,
    within_limit,
    worst_reading,
)

REFERENCE_IRRADIANCE = 1367.0
REFERENCE_TEMPERATURE = 25.0


def _policy(**overrides):
    policy = dict(DEFAULT_CRITERIA_POLICY)
    policy.update(overrides)
    return policy


def _reading(label, hours, pmax, **overrides):
    reading = {
        "label": label,
        "elapsed_hours": hours,
        "pmax_w": pmax,
        "irradiance_w_per_m2": REFERENCE_IRRADIANCE,
        "cell_temperature_c": REFERENCE_TEMPERATURE,
    }
    reading.update(overrides)
    return reading


def _readings():
    return [
        _reading("t0", 0.0, 100.0),
        _reading("t1", 2000.0, 99.6),
        _reading("t2", 4000.0, 99.2),
        _reading("t3", 6000.0, 98.9),
        _reading("t4", 8000.0, 98.7),
    ]


def _case(**overrides):
    case = {"readings": _readings()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_criteria_policy(DEFAULT_CRITERIA_POLICY),
            DEFAULT_CRITERIA_POLICY,
        )

    def test_the_default_limit_is_two_per_cent(self):
        self.assertAlmostEqual(
            DEFAULT_CRITERIA_POLICY["maximum_power_degradation_percent"],
            2.0,
            places=9,
        )

    def test_a_non_mapping_policy_is_refused(self):
        with self.assertRaises(ValueError):
            validate_criteria_policy("two per cent")

    def test_a_zero_limit_is_refused(self):
        with self.assertRaises(ValueError):
            validate_criteria_policy(
                _policy(maximum_power_degradation_percent=0.0)
            )

    def test_a_limit_of_a_hundred_per_cent_is_refused(self):
        with self.assertRaises(ValueError):
            validate_criteria_policy(
                _policy(maximum_power_degradation_percent=100.0)
            )

    def test_a_positive_temperature_coefficient_is_refused(self):
        with self.assertRaises(ValueError):
            validate_criteria_policy(
                _policy(power_temperature_coefficient_per_c=0.004)
            )

    def test_an_absurd_temperature_coefficient_is_refused(self):
        with self.assertRaises(ValueError):
            validate_criteria_policy(
                _policy(power_temperature_coefficient_per_c=-0.4)
            )

    def test_a_zero_reference_irradiance_is_refused(self):
        with self.assertRaises(ValueError):
            validate_criteria_policy(_policy(reference_irradiance_w_per_m2=0.0))


class ReadingTests(unittest.TestCase):
    def test_a_valid_reading_normalises(self):
        record = validate_reading(_reading("t0", 0.0, 100.0))
        self.assertEqual(record["label"], "t0")
        self.assertAlmostEqual(record["pmax_w"], 100.0, places=9)

    def test_a_blank_label_is_refused(self):
        with self.assertRaises(ValueError):
            validate_reading(_reading("   ", 0.0, 100.0))

    def test_a_negative_elapsed_hour_is_refused(self):
        with self.assertRaises(ValueError):
            validate_reading(_reading("t1", -10.0, 100.0))

    def test_a_zero_power_reading_is_refused(self):
        with self.assertRaises(ValueError):
            validate_reading(_reading("t1", 100.0, 0.0))

    def test_a_non_mapping_reading_is_refused(self):
        with self.assertRaises(ValueError):
            validate_reading(["t0", 0.0, 100.0])


class CorrectionTests(unittest.TestCase):
    def test_a_reading_at_reference_conditions_is_unchanged(self):
        self.assertAlmostEqual(
            corrected_pmax_w(_reading("t0", 0.0, 100.0)), 100.0, places=9
        )

    def test_low_irradiance_is_scaled_up(self):
        reading = _reading(
            "t1", 100.0, 50.0, irradiance_w_per_m2=REFERENCE_IRRADIANCE / 2.0
        )
        self.assertAlmostEqual(corrected_pmax_w(reading), 100.0, places=9)

    def test_a_warm_cell_is_corrected_upward(self):
        reading = _reading("t1", 100.0, 100.0, cell_temperature_c=55.0)
        expected = 100.0 / (1.0 + (-0.0035) * 30.0)
        self.assertAlmostEqual(corrected_pmax_w(reading), expected, places=9)

    def test_an_inverting_correction_is_refused(self):
        reading = _reading("t1", 100.0, 100.0, cell_temperature_c=500.0)
        with self.assertRaises(ValueError):
            corrected_pmax_w(reading)

    def test_weather_alone_does_not_read_as_degradation(self):
        warm = _reading("t1", 2000.0, 89.5, cell_temperature_c=55.0)
        series = reading_series([_reading("t0", 0.0, 100.0), warm])
        reference = initial_reference_w(series)
        fall = degradation_percent(reference, series[1]["corrected_pmax_w"])
        self.assertLess(abs(fall), 1.0)


class SeriesTests(unittest.TestCase):
    def test_the_series_is_ordered_in_time(self):
        shuffled = [_readings()[i] for i in (3, 0, 4, 1, 2)]
        series = reading_series(shuffled)
        self.assertEqual(
            [record["label"] for record in series], ["t0", "t1", "t2", "t3", "t4"]
        )

    def test_an_empty_series_is_refused(self):
        with self.assertRaises(ValueError):
            reading_series([])

    def test_two_readings_at_one_elapsed_hour_are_refused(self):
        with self.assertRaises(ValueError):
            reading_series([_reading("t0", 0.0, 100.0), _reading("t0b", 0.0, 99.0)])

    def test_a_repeated_label_is_refused(self):
        with self.assertRaises(ValueError):
            reading_series([_reading("t0", 0.0, 100.0), _reading("t0", 500.0, 99.0)])

    def test_a_series_that_never_starts_at_zero_has_no_reference(self):
        series = reading_series([_reading("t1", 500.0, 99.0)])
        self.assertIsNone(initial_reference_w(series))


class DegradationTests(unittest.TestCase):
    def test_no_change_is_no_degradation(self):
        self.assertAlmostEqual(degradation_percent(100.0, 100.0), 0.0, places=9)

    def test_a_two_watt_fall_from_a_hundred_is_two_per_cent(self):
        self.assertAlmostEqual(degradation_percent(100.0, 98.0), 2.0, places=9)

    def test_a_gain_reads_as_a_negative_degradation(self):
        self.assertAlmostEqual(degradation_percent(100.0, 101.0), -1.0, places=9)

    def test_a_zero_reference_is_refused(self):
        with self.assertRaises(ValueError):
            degradation_percent(0.0, 98.0)

    def test_the_maximum_is_taken_over_the_whole_series(self):
        series = reading_series(
            [
                _reading("t0", 0.0, 100.0),
                _reading("t1", 2000.0, 96.5),
                _reading("t2", 4000.0, 99.0),
            ]
        )
        degradations = series_degradations(series, initial_reference_w(series))
        self.assertAlmostEqual(
            maximum_degradation_percent(degradations), 3.5, places=9
        )

    def test_the_worst_reading_is_named(self):
        series = reading_series(
            [
                _reading("t0", 0.0, 100.0),
                _reading("t1", 2000.0, 96.5),
                _reading("t2", 4000.0, 99.0),
            ]
        )
        degradations = series_degradations(series, initial_reference_w(series))
        self.assertEqual(worst_reading(degradations)["label"], "t1")

    def test_an_empty_degradation_set_is_refused(self):
        with self.assertRaises(ValueError):
            maximum_degradation_percent([])


class LimitTests(unittest.TestCase):
    def test_a_value_inside_the_limit_holds(self):
        self.assertTrue(within_limit(1.5, 2.0))

    def test_a_value_exactly_on_the_limit_holds(self):
        self.assertTrue(within_limit(2.0, 2.0))

    def test_a_value_outside_the_limit_does_not_hold(self):
        self.assertFalse(within_limit(2.5, 2.0))

    def test_a_zero_limit_is_refused(self):
        with self.assertRaises(ValueError):
            within_limit(1.0, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_a_record_with_no_reading_closes_the_assessment(self):
        result = assess_long_duration_life_test_criteria({})
        self.assertEqual(result["verdict"], REFERENCE_NOT_ESTABLISHED)

    def test_a_series_with_no_initial_reading_closes_the_assessment(self):
        case = _case(readings=[_reading("t1", 2000.0, 99.0)])
        result = assess_long_duration_life_test_criteria(case)
        self.assertEqual(result["verdict"], REFERENCE_NOT_ESTABLISHED)

    def test_an_initial_reading_alone_closes_the_assessment(self):
        case = _case(readings=[_reading("t0", 0.0, 100.0)])
        result = assess_long_duration_life_test_criteria(case)
        self.assertEqual(result["verdict"], REFERENCE_NOT_ESTABLISHED)

    def test_a_stable_assembly_is_inside_the_limit(self):
        result = assess_long_duration_life_test_criteria(_case())
        self.assertEqual(result["verdict"], DEGRADATION_WITHIN_LIMIT)
        self.assertAlmostEqual(
            result["maximum_degradation_percent"], 1.3, places=9
        )
        self.assertEqual(result["advisories"], [])

    def test_a_reading_exactly_on_the_limit_is_admissible(self):
        case = _case(
            readings=[_reading("t0", 0.0, 100.0), _reading("t1", 8000.0, 98.0)]
        )
        result = assess_long_duration_life_test_criteria(case)
        self.assertAlmostEqual(
            result["maximum_degradation_percent"], 2.0, places=9
        )
        self.assertEqual(result["verdict"], DEGRADATION_WITHIN_LIMIT)

    def test_a_drifting_assembly_is_outside_the_limit(self):
        case = _case(
            readings=[
                _reading("t0", 0.0, 100.0),
                _reading("t1", 4000.0, 98.5),
                _reading("t2", 8000.0, 96.9),
            ]
        )
        result = assess_long_duration_life_test_criteria(case)
        self.assertEqual(result["verdict"], DEGRADATION_EXCEEDS_LIMIT)
        self.assertEqual(result["worst_reading_label"], "t2")

    def test_a_mid_test_excursion_fails_even_when_the_end_recovers(self):
        case = _case(
            readings=[
                _reading("t0", 0.0, 100.0),
                _reading("t1", 4000.0, 97.0),
                _reading("t2", 8000.0, 98.5),
            ]
        )
        result = assess_long_duration_life_test_criteria(case)
        self.assertEqual(result["verdict"], DEGRADATION_EXCEEDS_LIMIT)
        self.assertEqual(result["worst_reading_label"], "t1")
        self.assertAlmostEqual(
            result["final_degradation_percent"], 1.5, places=9
        )

    def test_the_recovered_excursion_is_reported_as_an_advisory(self):
        case = _case(
            readings=[
                _reading("t0", 0.0, 100.0),
                _reading("t1", 4000.0, 97.0),
                _reading("t2", 8000.0, 98.5),
            ]
        )
        result = assess_long_duration_life_test_criteria(case)
        self.assertEqual(len(result["advisories"]), 1)

    def test_an_excursion_with_no_recovery_raises_no_advisory(self):
        degradations = [
            {"label": "t0", "elapsed_hours": 0.0, "degradation_percent": 0.0},
            {"label": "t1", "elapsed_hours": 4000.0, "degradation_percent": 3.0},
        ]
        self.assertEqual(recovered_excursions(degradations, 2.0), ())

    def test_a_tightened_limit_moves_the_verdict(self):
        result = assess_long_duration_life_test_criteria(
            _case(), _policy(maximum_power_degradation_percent=1.0)
        )
        self.assertEqual(result["verdict"], DEGRADATION_EXCEEDS_LIMIT)

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_long_duration_life_test_criteria(["readings"])

    def test_the_reported_series_covers_every_reading(self):
        result = assess_long_duration_life_test_criteria(_case())
        self.assertEqual(len(result["degradations"]), 5)


if __name__ == "__main__":
    unittest.main()
