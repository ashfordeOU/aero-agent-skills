#!/usr/bin/env python3
"""Contract test for the array ambient environment leaf (offline)."""

import copy
import unittest

from e2008_standard_test_environment_conditions_logic import (
    ACTIVITIES,
    CONDENSATION_VERDICT,
    DEFAULT_EXCURSION_POLICY,
    ENVIRONMENT_PARAMETERS,
    RECORD_VERDICT,
    REJECTED_VERDICT,
    WITHIN_VERDICT,
    assess_environment,
    condensation_margin_k,
    dew_point_c,
    dwell_fraction_outside,
    envelope_for,
    envelope_headroom,
    reading_excursions,
    validate_envelope,
    validate_log,
    validate_policy,
    validate_reading,
    worst_exceedance,
)

INSPECTION_ENVELOPE = envelope_for("inspection")


def _reading(pressure=100.0, temperature=22.0, humidity=45.0, duration=60.0):
    return {
        "pressure_kpa": pressure,
        "temperature_c": temperature,
        "relative_humidity_pct": humidity,
        "duration_min": duration,
    }


CLEAN_LOG = [_reading(), _reading(temperature=24.0), _reading(humidity=55.0)]

RECORDABLE_LOG = [_reading(duration=570.0), _reading(humidity=68.0, duration=30.0)]

OVERSIZE_LOG = [_reading(duration=570.0), _reading(humidity=88.0, duration=30.0)]

LONG_DWELL_LOG = [
    _reading(duration=300.0),
    _reading(humidity=68.0, duration=300.0),
]


def _case(**overrides):
    case = {"activity": "inspection", "readings": copy.deepcopy(CLEAN_LOG)}
    case.update(overrides)
    return case


class EnvelopeTests(unittest.TestCase):
    def test_inspection_and_testing_hold_the_same_band(self):
        self.assertEqual(envelope_for("inspection"), envelope_for("testing"))

    def test_short_term_storage_allows_a_drier_and_cooler_room(self):
        storage = envelope_for("short-term-storage")
        inspection = envelope_for("inspection")
        self.assertLess(
            storage["relative_humidity_pct"][0], inspection["relative_humidity_pct"][0]
        )
        self.assertLess(storage["temperature_c"][0], inspection["temperature_c"][0])

    def test_every_activity_declares_every_parameter(self):
        for activity in ACTIVITIES:
            envelope = envelope_for(activity)
            for parameter in ENVIRONMENT_PARAMETERS:
                self.assertIn(parameter, envelope)

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            envelope_for("shipping")

    def test_envelope_missing_a_parameter_rejected(self):
        broken = dict(INSPECTION_ENVELOPE)
        del broken["pressure_kpa"]
        with self.assertRaises(ValueError):
            validate_envelope(broken)

    def test_envelope_with_an_inverted_band_rejected(self):
        broken = dict(INSPECTION_ENVELOPE)
        broken["temperature_c"] = (30.0, 15.0)
        with self.assertRaises(ValueError):
            validate_envelope(broken)

    def test_envelope_band_that_is_not_a_pair_rejected(self):
        broken = dict(INSPECTION_ENVELOPE)
        broken["temperature_c"] = (15.0, 22.0, 30.0)
        with self.assertRaises(ValueError):
            validate_envelope(broken)


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_policy(DEFAULT_EXCURSION_POLICY), DEFAULT_EXCURSION_POLICY
        )

    def test_a_dwell_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_EXCURSION_POLICY)
        broken["max_dwell_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_policy(broken)

    def test_a_negative_condensation_margin_rejected(self):
        broken = copy.deepcopy(DEFAULT_EXCURSION_POLICY)
        broken["condensation_margin_k"] = -1.0
        with self.assertRaises(ValueError):
            validate_policy(broken)

    def test_a_recordable_table_missing_a_parameter_rejected(self):
        broken = copy.deepcopy(DEFAULT_EXCURSION_POLICY)
        del broken["recordable_exceedance"]["temperature_c"]
        with self.assertRaises(ValueError):
            validate_policy(broken)

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_policy("default")


class ReadingValidationTests(unittest.TestCase):
    def test_a_well_formed_reading_normalises(self):
        entry = validate_reading(_reading())
        self.assertAlmostEqual(entry["temperature_c"], 22.0, places=9)
        self.assertAlmostEqual(entry["duration_min"], 60.0, places=9)

    def test_a_reading_without_a_duration_takes_one_minute(self):
        entry = validate_reading(
            {"pressure_kpa": 100.0, "temperature_c": 22.0, "relative_humidity_pct": 45.0}
        )
        self.assertAlmostEqual(entry["duration_min"], 1.0, places=9)

    def test_a_humidity_above_saturation_rejected(self):
        with self.assertRaises(ValueError):
            validate_reading(_reading(humidity=120.0))

    def test_a_zero_humidity_reading_rejected(self):
        with self.assertRaises(ValueError):
            validate_reading(_reading(humidity=0.0))

    def test_a_temperature_at_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_reading(_reading(temperature=-273.15))

    def test_a_zero_pressure_reading_rejected(self):
        with self.assertRaises(ValueError):
            validate_reading(_reading(pressure=0.0))

    def test_a_zero_duration_reading_rejected(self):
        with self.assertRaises(ValueError):
            validate_reading(_reading(duration=0.0))

    def test_a_non_mapping_reading_rejected(self):
        with self.assertRaises(ValueError):
            validate_reading((100.0, 22.0, 45.0))

    def test_an_empty_log_rejected(self):
        with self.assertRaises(ValueError):
            validate_log([])


class DewPointTests(unittest.TestCase):
    def test_saturated_air_dews_at_its_own_temperature(self):
        self.assertAlmostEqual(dew_point_c(22.0, 100.0), 22.0, places=9)

    def test_a_half_saturated_room_dews_about_eleven_degrees_lower(self):
        self.assertAlmostEqual(dew_point_c(22.0, 50.0), 11.0946, places=4)

    def test_drier_air_lowers_the_dew_point(self):
        self.assertLess(dew_point_c(22.0, 30.0), dew_point_c(22.0, 60.0))

    def test_a_warmer_room_at_the_same_humidity_dews_higher(self):
        self.assertGreater(dew_point_c(26.0, 50.0), dew_point_c(18.0, 50.0))

    def test_a_warm_surface_holds_a_positive_condensation_margin(self):
        self.assertGreater(condensation_margin_k(22.0, 45.0, 21.0), 5.0)

    def test_a_cold_surface_sits_below_the_dew_point(self):
        self.assertLess(condensation_margin_k(22.0, 60.0, 12.0), 0.0)

    def test_a_zero_humidity_dew_point_rejected(self):
        with self.assertRaises(ValueError):
            dew_point_c(22.0, 0.0)

    def test_a_surface_at_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            condensation_margin_k(22.0, 45.0, -300.0)


class ExcursionTests(unittest.TestCase):
    def test_a_reading_inside_the_band_has_no_excursion(self):
        self.assertEqual(reading_excursions(_reading(), INSPECTION_ENVELOPE), [])

    def test_a_reading_exactly_on_the_humidity_ceiling_is_inside(self):
        self.assertEqual(
            reading_excursions(_reading(humidity=65.0), INSPECTION_ENVELOPE), []
        )
        headroom = envelope_headroom(_reading(humidity=65.0), INSPECTION_ENVELOPE)
        self.assertAlmostEqual(headroom["relative_humidity_pct"], 0.0, places=9)

    def test_a_reading_exactly_on_the_pressure_floor_is_inside(self):
        self.assertEqual(
            reading_excursions(_reading(pressure=86.0), INSPECTION_ENVELOPE), []
        )

    def test_a_humid_reading_is_sized_against_the_high_bound(self):
        excursions = reading_excursions(_reading(humidity=68.0), INSPECTION_ENVELOPE)
        self.assertEqual(len(excursions), 1)
        self.assertEqual(excursions[0]["parameter"], "relative_humidity_pct")
        self.assertEqual(excursions[0]["bound"], "high")
        self.assertAlmostEqual(excursions[0]["exceedance"], 3.0, places=9)

    def test_a_cold_reading_is_sized_against_the_low_bound(self):
        excursions = reading_excursions(_reading(temperature=11.0), INSPECTION_ENVELOPE)
        self.assertEqual(excursions[0]["bound"], "low")
        self.assertAlmostEqual(excursions[0]["exceedance"], 4.0, places=9)

    def test_two_parameters_out_at_once_are_both_reported(self):
        excursions = reading_excursions(
            _reading(temperature=11.0, humidity=75.0), INSPECTION_ENVELOPE
        )
        self.assertEqual(len(excursions), 2)
        self.assertEqual(
            sorted(e["parameter"] for e in excursions),
            ["relative_humidity_pct", "temperature_c"],
        )

    def test_headroom_goes_negative_outside_the_band(self):
        headroom = envelope_headroom(_reading(humidity=75.0), INSPECTION_ENVELOPE)
        self.assertAlmostEqual(headroom["relative_humidity_pct"], -10.0, places=9)


class DwellTests(unittest.TestCase):
    def test_a_clean_log_dwells_no_time_outside(self):
        self.assertAlmostEqual(
            dwell_fraction_outside(CLEAN_LOG, INSPECTION_ENVELOPE), 0.0, places=9
        )

    def test_dwell_is_weighted_by_time_not_by_reading_count(self):
        log = [_reading(duration=10.0), _reading(humidity=68.0, duration=90.0)]
        self.assertAlmostEqual(
            dwell_fraction_outside(log, INSPECTION_ENVELOPE), 0.9, places=9
        )

    def test_a_short_excursion_dwells_a_small_fraction(self):
        self.assertAlmostEqual(
            dwell_fraction_outside(RECORDABLE_LOG, INSPECTION_ENVELOPE), 0.05, places=9
        )

    def test_worst_exceedance_is_zero_on_a_clean_log(self):
        worst = worst_exceedance(CLEAN_LOG, INSPECTION_ENVELOPE)
        for parameter in ENVIRONMENT_PARAMETERS:
            self.assertAlmostEqual(worst[parameter], 0.0, places=9)

    def test_worst_exceedance_keeps_the_largest_per_parameter(self):
        log = [
            _reading(humidity=68.0),
            _reading(humidity=72.0),
            _reading(temperature=11.0),
        ]
        worst = worst_exceedance(log, INSPECTION_ENVELOPE)
        self.assertAlmostEqual(worst["relative_humidity_pct"], 7.0, places=9)
        self.assertAlmostEqual(worst["temperature_c"], 4.0, places=9)


class AssessmentTests(unittest.TestCase):
    def test_a_clean_inspection_log_is_within_the_envelope(self):
        result = assess_environment(_case())
        self.assertEqual(result["verdict"], WITHIN_VERDICT)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["excursion_reading_count"], 0)

    def test_a_short_small_excursion_is_accepted_against_a_record(self):
        result = assess_environment(_case(readings=RECORDABLE_LOG))
        self.assertEqual(result["verdict"], RECORD_VERDICT)
        self.assertTrue(result["accepted"])
        self.assertTrue(any("record the excursion" in f for f in result["findings"]))
        self.assertAlmostEqual(result["dwell_fraction_outside"], 0.05, places=9)

    def test_an_oversize_excursion_is_rejected(self):
        result = assess_environment(_case(readings=OVERSIZE_LOG))
        self.assertEqual(result["verdict"], REJECTED_VERDICT)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("too large" in f for f in result["findings"]))

    def test_a_long_dwell_outside_the_band_is_rejected(self):
        result = assess_environment(_case(readings=LONG_DWELL_LOG))
        self.assertEqual(result["verdict"], REJECTED_VERDICT)
        self.assertTrue(any("dwell" in f for f in result["findings"]))

    def test_a_cold_surface_is_rejected_even_with_no_excursion(self):
        result = assess_environment(
            _case(readings=[_reading(humidity=60.0)], coldest_surface_c=15.0)
        )
        self.assertEqual(result["verdict"], CONDENSATION_VERDICT)
        self.assertTrue(result["condensation_risk"])
        self.assertFalse(result["accepted"])
        self.assertLess(result["condensation_margin_k"], 3.0)

    def test_condensation_outranks_a_recordable_excursion(self):
        log = [_reading(duration=570.0), _reading(humidity=68.0, duration=30.0)]
        result = assess_environment(_case(readings=log, coldest_surface_c=14.0))
        self.assertEqual(result["verdict"], CONDENSATION_VERDICT)

    def test_a_warm_surface_leaves_no_condensation_risk(self):
        result = assess_environment(_case(coldest_surface_c=21.0))
        self.assertEqual(result["verdict"], WITHIN_VERDICT)
        self.assertFalse(result["condensation_risk"])
        self.assertGreater(result["condensation_margin_k"], 3.0)

    def test_without_a_surface_no_condensation_margin_is_reported(self):
        result = assess_environment(_case())
        self.assertIsNone(result["condensation_margin_k"])
        self.assertFalse(result["condensation_risk"])

    def test_a_dry_room_passes_storage_but_fails_inspection(self):
        log = [_reading(humidity=15.0)]
        storage = assess_environment(
            {"activity": "short-term-storage", "readings": log}
        )
        inspection = assess_environment({"activity": "inspection", "readings": log})
        self.assertEqual(storage["verdict"], WITHIN_VERDICT)
        self.assertEqual(inspection["verdict"], REJECTED_VERDICT)

    def test_a_declared_envelope_overrides_the_activity_band(self):
        envelope = dict(INSPECTION_ENVELOPE)
        envelope["relative_humidity_pct"] = (20.0, 70.0)
        result = assess_environment(
            _case(readings=[_reading(humidity=68.0)], envelope=envelope)
        )
        self.assertEqual(result["verdict"], WITHIN_VERDICT)

    def test_an_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            assess_environment(_case(activity="transport"))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_environment("inspection")

    def test_a_case_with_no_readings_rejected(self):
        with self.assertRaises(ValueError):
            assess_environment(_case(readings=[]))

    def test_a_tighter_policy_turns_a_record_into_a_rejection(self):
        policy = copy.deepcopy(DEFAULT_EXCURSION_POLICY)
        policy["recordable_exceedance"]["relative_humidity_pct"] = 1.0
        result = assess_environment(_case(readings=RECORDABLE_LOG), policy)
        self.assertEqual(result["verdict"], REJECTED_VERDICT)


if __name__ == "__main__":
    unittest.main()
