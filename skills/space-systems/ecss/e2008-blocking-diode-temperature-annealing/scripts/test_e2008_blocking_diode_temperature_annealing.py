"""Contract tests for the clause 12.6.12 anneal insertion review.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused anneal policy, a
timeline missing one of its four events, an anneal that does not sit between
the two post-irradiation readings, a first reading taken too long after the
exposure, a soak short of its dwell or above the package rating, and two
readings taken too far apart in temperature to subtract.
"""

import unittest

from e2008_blocking_diode_temperature_annealing_logic import (
    ANNEAL_INSERTION_ACCEPTED,
    ANNEAL_SEQUENCE_NOT_ESTABLISHED,
    DEFAULT_ANNEAL_POLICY,
    READING_CONDITIONS_NOT_COMPARABLE,
    SOAK_PROFILE_OUT_OF_BOUNDS,
    assess_blocking_diode_annealing,
    first_measurement_delay_h,
    readings_comparable,
    reading_temperature_gap_k,
    recovered_share,
    sequence_breaks,
    soak_dwell_hours,
    soak_profile_breaches,
    validate_anneal_policy,
    validate_measurement,
    validate_soak_profile,
)

EXPOSURE_END_HOUR = 100.0


def _policy(**overrides):
    policy = dict(DEFAULT_ANNEAL_POLICY)
    policy.update(overrides)
    return policy


def _first(**overrides):
    reading = {
        "stage": "first-post-irradiation-measurement",
        "hour": 104.0,
        "reading_temperature_c": 25.0,
        "forward_voltage_v": 0.948,
        "reverse_leakage_a": 1.8e-6,
    }
    reading.update(overrides)
    return reading


def _second(**overrides):
    reading = {
        "stage": "second-post-irradiation-measurement",
        "hour": 200.0,
        "reading_temperature_c": 25.4,
        "forward_voltage_v": 0.876,
        "reverse_leakage_a": 9.0e-7,
    }
    reading.update(overrides)
    return reading


def _baseline(**overrides):
    reading = {
        "stage": "pre-irradiation",
        "hour": 10.0,
        "reading_temperature_c": 25.1,
        "forward_voltage_v": 0.828,
        "reverse_leakage_a": 4.0e-7,
    }
    reading.update(overrides)
    return reading


def _profile(**overrides):
    profile = {
        "start_hour": 110.0,
        "end_hour": 158.0,
        "soak_temperature_c": 85.0,
    }
    profile.update(overrides)
    return profile


def _case(**overrides):
    case = {
        "exposure_end_hour": EXPOSURE_END_HOUR,
        "pre_irradiation": _baseline(),
        "first_measurement": _first(),
        "soak_profile": _profile(),
        "second_measurement": _second(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_anneal_policy(DEFAULT_ANNEAL_POLICY), DEFAULT_ANNEAL_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_anneal_policy("min_dwell_hours")

    def test_a_soak_floor_above_the_package_rating_rejected(self):
        with self.assertRaises(ValueError):
            validate_anneal_policy(
                _policy(min_soak_temperature_c=150.0, max_package_temperature_c=125.0)
            )

    def test_a_soak_floor_equal_to_the_package_rating_is_admitted(self):
        self.assertIsNotNone(
            validate_anneal_policy(
                _policy(min_soak_temperature_c=125.0, max_package_temperature_c=125.0)
            )
        )

    def test_a_zero_dwell_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_anneal_policy(_policy(min_dwell_hours=0.0))

    def test_a_recovery_advisory_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_anneal_policy(_policy(advisory_min_recovery_fraction=1.4))

    def test_a_negative_reading_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_anneal_policy(_policy(reading_temperature_tolerance_k=-1.0))


class SoakProfileTests(unittest.TestCase):
    def test_a_profile_is_read_back(self):
        checked = validate_soak_profile(_profile())
        self.assertAlmostEqual(checked["soak_temperature_c"], 85.0, places=12)

    def test_non_mapping_profile_rejected(self):
        with self.assertRaises(ValueError):
            validate_soak_profile(85.0)

    def test_a_soak_ending_before_it_starts_rejected(self):
        with self.assertRaises(ValueError):
            validate_soak_profile(_profile(end_hour=100.0))

    def test_a_zero_length_soak_rejected(self):
        with self.assertRaises(ValueError):
            validate_soak_profile(_profile(end_hour=110.0))

    def test_the_dwell_is_the_span_of_the_soak(self):
        self.assertAlmostEqual(soak_dwell_hours(_profile()), 48.0, places=12)

    def test_a_conforming_profile_breaches_nothing(self):
        self.assertEqual(soak_profile_breaches(_profile()), ())

    def test_a_cool_soak_is_named(self):
        breaches = soak_profile_breaches(_profile(soak_temperature_c=40.0))
        self.assertEqual(len(breaches), 1)

    def test_a_soak_above_the_package_rating_is_named(self):
        breaches = soak_profile_breaches(_profile(soak_temperature_c=160.0))
        self.assertEqual(len(breaches), 1)

    def test_a_short_dwell_is_named(self):
        breaches = soak_profile_breaches(_profile(end_hour=118.0))
        self.assertEqual(len(breaches), 1)

    def test_a_soak_exactly_on_both_bounds_breaches_nothing(self):
        breaches = soak_profile_breaches(
            _profile(
                soak_temperature_c=DEFAULT_ANNEAL_POLICY["min_soak_temperature_c"],
                end_hour=110.0 + DEFAULT_ANNEAL_POLICY["min_dwell_hours"],
            )
        )
        self.assertEqual(breaches, ())

    def test_a_cool_and_short_soak_names_both(self):
        breaches = soak_profile_breaches(
            _profile(soak_temperature_c=40.0, end_hour=112.0)
        )
        self.assertEqual(len(breaches), 2)


class MeasurementTests(unittest.TestCase):
    def test_a_measurement_is_read_back(self):
        checked = validate_measurement("first", _first())
        self.assertAlmostEqual(checked["forward_voltage_v"], 0.948, places=12)

    def test_non_mapping_measurement_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurement("first", 0.948)

    def test_a_missing_reading_temperature_rejected(self):
        bad = _first()
        del bad["reading_temperature_c"]
        with self.assertRaises(ValueError):
            validate_measurement("first", bad)

    def test_a_boolean_leakage_rejected(self):
        with self.assertRaises(ValueError):
            validate_measurement("first", _first(reverse_leakage_a=True))

    def test_a_sub_zero_reading_temperature_is_admitted(self):
        checked = validate_measurement("first", _first(reading_temperature_c=-25.0))
        self.assertAlmostEqual(checked["reading_temperature_c"], -25.0, places=12)


class SequenceTests(unittest.TestCase):
    def test_a_correct_timeline_breaks_nothing(self):
        self.assertEqual(
            sequence_breaks(EXPOSURE_END_HOUR, _first(), _profile(), _second()), ()
        )

    def test_a_soak_starting_before_the_first_reading_is_a_break(self):
        breaks = sequence_breaks(
            EXPOSURE_END_HOUR, _first(hour=120.0), _profile(), _second()
        )
        self.assertEqual(len(breaks), 1)

    def test_a_second_reading_inside_the_soak_is_a_break(self):
        breaks = sequence_breaks(
            EXPOSURE_END_HOUR, _first(), _profile(), _second(hour=140.0)
        )
        self.assertEqual(len(breaks), 1)

    def test_a_first_reading_before_the_exposure_ended_is_a_break(self):
        breaks = sequence_breaks(
            EXPOSURE_END_HOUR, _first(hour=90.0), _profile(), _second()
        )
        self.assertGreaterEqual(len(breaks), 1)

    def test_two_lost_orderings_are_both_named(self):
        breaks = sequence_breaks(
            EXPOSURE_END_HOUR,
            _first(hour=115.0),
            _profile(),
            _second(hour=150.0),
        )
        self.assertEqual(len(breaks), 2)

    def test_events_touching_end_to_end_are_admitted(self):
        breaks = sequence_breaks(
            EXPOSURE_END_HOUR,
            _first(hour=EXPOSURE_END_HOUR),
            _profile(start_hour=EXPOSURE_END_HOUR, end_hour=200.0),
            _second(hour=200.0),
        )
        self.assertEqual(breaks, ())

    def test_the_first_reading_delay_is_measured_from_the_exposure_end(self):
        self.assertAlmostEqual(
            first_measurement_delay_h(EXPOSURE_END_HOUR, _first()), 4.0, places=12
        )


class ReadingConditionTests(unittest.TestCase):
    def test_the_temperature_gap_is_the_absolute_difference(self):
        self.assertAlmostEqual(
            reading_temperature_gap_k(_first(), _second()), 0.4, places=9
        )

    def test_close_readings_are_comparable(self):
        self.assertTrue(readings_comparable(_first(), _second()))

    def test_readings_exactly_on_the_tolerance_are_comparable(self):
        self.assertTrue(
            readings_comparable(
                _first(reading_temperature_c=25.0),
                _second(reading_temperature_c=27.0),
                _policy(reading_temperature_tolerance_k=2.0),
            )
        )

    def test_readings_far_apart_are_not_comparable(self):
        self.assertFalse(
            readings_comparable(
                _first(reading_temperature_c=25.0),
                _second(reading_temperature_c=55.0),
            )
        )


class RecoveryTests(unittest.TestCase):
    def test_a_full_recovery_is_one(self):
        self.assertAlmostEqual(recovered_share(0.828, 0.948, 0.828), 1.0, places=9)

    def test_no_recovery_is_zero(self):
        self.assertAlmostEqual(recovered_share(0.828, 0.948, 0.948), 0.0, places=12)

    def test_a_half_recovery_is_a_half(self):
        self.assertAlmostEqual(recovered_share(0.828, 0.948, 0.888), 0.5, places=9)

    def test_continued_drift_through_the_soak_is_negative(self):
        self.assertLess(recovered_share(0.828, 0.948, 0.980), 0.0)

    def test_an_unmoved_characteristic_rejected(self):
        with self.assertRaises(ValueError):
            recovered_share(0.900, 0.900, 0.900)


class AssessmentTests(unittest.TestCase):
    def test_a_correct_timeline_is_accepted(self):
        result = assess_blocking_diode_annealing(_case())
        self.assertEqual(result["verdict"], ANNEAL_INSERTION_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_a_missing_soak_closes_the_review(self):
        case = _case()
        del case["soak_profile"]
        result = assess_blocking_diode_annealing(case)
        self.assertEqual(result["verdict"], ANNEAL_SEQUENCE_NOT_ESTABLISHED)

    def test_a_missing_second_reading_closes_the_review(self):
        case = _case()
        del case["second_measurement"]
        result = assess_blocking_diode_annealing(case)
        self.assertEqual(result["verdict"], ANNEAL_SEQUENCE_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_a_missing_exposure_end_closes_the_review(self):
        case = _case()
        del case["exposure_end_hour"]
        result = assess_blocking_diode_annealing(case)
        self.assertEqual(result["verdict"], ANNEAL_SEQUENCE_NOT_ESTABLISHED)

    def test_a_soak_outside_the_two_readings_closes_the_review(self):
        result = assess_blocking_diode_annealing(_case(first_measurement=_first(hour=120.0)))
        self.assertEqual(result["verdict"], ANNEAL_SEQUENCE_NOT_ESTABLISHED)

    def test_a_late_first_reading_closes_the_review(self):
        result = assess_blocking_diode_annealing(
            _case(first_measurement=_first(hour=180.0), soak_profile=_profile(start_hour=185.0, end_hour=240.0), second_measurement=_second(hour=250.0))
        )
        self.assertEqual(result["verdict"], ANNEAL_SEQUENCE_NOT_ESTABLISHED)

    def test_a_short_soak_is_out_of_bounds(self):
        result = assess_blocking_diode_annealing(
            _case(soak_profile=_profile(end_hour=118.0))
        )
        self.assertEqual(result["verdict"], SOAK_PROFILE_OUT_OF_BOUNDS)

    def test_a_soak_above_the_package_rating_is_out_of_bounds(self):
        result = assess_blocking_diode_annealing(
            _case(soak_profile=_profile(soak_temperature_c=170.0))
        )
        self.assertEqual(result["verdict"], SOAK_PROFILE_OUT_OF_BOUNDS)

    def test_readings_taken_at_different_temperatures_are_not_comparable(self):
        result = assess_blocking_diode_annealing(
            _case(second_measurement=_second(reading_temperature_c=60.0))
        )
        self.assertEqual(result["verdict"], READING_CONDITIONS_NOT_COMPARABLE)

    def test_the_recovered_shares_travel_with_the_verdict(self):
        result = assess_blocking_diode_annealing(_case())
        self.assertAlmostEqual(
            result["forward_recovered_share"],
            (0.948 - 0.876) / (0.948 - 0.828),
            places=9,
        )
        self.assertIsNotNone(result["leakage_recovered_share"])

    def test_a_timeline_without_a_baseline_carries_no_recovered_share(self):
        case = _case()
        del case["pre_irradiation"]
        result = assess_blocking_diode_annealing(case)
        self.assertEqual(result["verdict"], ANNEAL_INSERTION_ACCEPTED)
        self.assertIsNone(result["forward_recovered_share"])

    def test_a_small_recovery_raises_an_advisory_without_moving_the_verdict(self):
        result = assess_blocking_diode_annealing(
            _case(second_measurement=_second(forward_voltage_v=0.940))
        )
        self.assertEqual(result["verdict"], ANNEAL_INSERTION_ACCEPTED)
        self.assertEqual(len(result["advisories"]), 1)

    def test_the_dwell_and_the_delay_are_reported(self):
        result = assess_blocking_diode_annealing(_case())
        self.assertAlmostEqual(result["dwell_hours"], 48.0, places=12)
        self.assertAlmostEqual(result["first_measurement_delay_h"], 4.0, places=12)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_blocking_diode_annealing(["soak_profile"])


if __name__ == "__main__":
    unittest.main()
