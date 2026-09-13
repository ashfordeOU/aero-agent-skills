#!/usr/bin/env python3
"""Contract test for the harness resistance measurement (offline).

Walks the clause workflow step by step: the check that the two joined
redundant conductors really are the same wire, the resistance the
declared geometry predicts, the reduction of a series loop reading to
one leg by removing the far-end joint and halving, the referral to the
reference temperature, the band that separates a sound run from a
resisting one, the flight configuration that decides what the array
current sees, the interface voltage drop, and the verdict that has to
stop a campaign read two-wire or halved across mismatched legs. This is
the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_harness_resistance_measurement_logic import (
    ABOVE_BAND,
    BELOW_BAND,
    DEFAULT_HARNESS_POLICY,
    HARNESS_RESISTANCE_ACCEPTED,
    HARNESS_RESISTANCE_CATEGORIES,
    HARNESS_RESISTANCE_NOT_EVALUATED,
    HARNESS_RESISTANCE_REJECTED,
    LEG_ATTRIBUTES,
    PARALLEL_REDUNDANT,
    SINGLE_ACTIVE,
    WITHIN_BAND,
    categorize_harness_resistance,
    conductor_resistance_ohm,
    evaluate_harness_measurement,
    evaluate_harness_resistance_campaign,
    expected_loop_resistance_ohm,
    flight_resistance_ohm,
    interface_voltage_drop_v,
    single_leg_resistance_ohm,
    temperature_corrected_resistance_ohm,
    validate_harness_policy,
    validate_redundant_pair,
)

LEG = {
    "conductor-material": "copper",
    "conductor-gauge": "awg20",
    "routed-length-m": 2.4,
    "cross-section-mm2": 0.52,
}

RESISTIVITY = DEFAULT_HARNESS_POLICY["resistivity_ohm_mm2_per_m"]
ALPHA = DEFAULT_HARNESS_POLICY["temperature_coefficient_per_k"]
REFERENCE_C = DEFAULT_HARNESS_POLICY["reference_temperature_c"]
TOLERANCE = DEFAULT_HARNESS_POLICY["resistance_tolerance_fraction"]
EXPECTED_LEG_OHM = RESISTIVITY * 2.4 / 0.52
MAX_ARRAY_CURRENT_A = 3.2


def _legs(**second_leg_overrides):
    first = copy.deepcopy(LEG)
    second = copy.deepcopy(LEG)
    second.update(second_leg_overrides)
    return [first, second]


def _measurement(
    identifier="run-a",
    factor=1.0,
    temperature_c=22.0,
    joint_ohm=0.002,
    four_wire=True,
    configuration=PARALLEL_REDUNDANT,
    legs=None,
):
    """Synthesise a loop reading that reduces to factor x the prediction."""
    warm = 1.0 + ALPHA * (temperature_c - REFERENCE_C)
    loop = EXPECTED_LEG_OHM * factor * warm * 2.0 + joint_ohm
    return {
        "id": identifier,
        "legs": legs if legs is not None else _legs(),
        "loop_resistance_ohm": loop,
        "joint_resistance_ohm": joint_ohm,
        "measurement_temperature_c": temperature_c,
        "four_wire": four_wire,
        "flight_configuration": configuration,
    }


def _campaign(measurements, current_a=MAX_ARRAY_CURRENT_A):
    return {
        "max_array_current_a": current_a,
        "measurements": list(measurements),
    }


SOUND_CAMPAIGN = _campaign(
    [_measurement("run-a"), _measurement("run-b"), _measurement("run-c")]
)


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_harness_policy(DEFAULT_HARNESS_POLICY), DEFAULT_HARNESS_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_harness_policy("default")

    def test_zero_resistivity_rejected(self):
        broken = copy.deepcopy(DEFAULT_HARNESS_POLICY)
        broken["resistivity_ohm_mm2_per_m"] = 0.0
        with self.assertRaises(ValueError):
            validate_harness_policy(broken)

    def test_tolerance_of_one_or_more_rejected(self):
        broken = copy.deepcopy(DEFAULT_HARNESS_POLICY)
        broken["resistance_tolerance_fraction"] = 1.0
        with self.assertRaises(ValueError):
            validate_harness_policy(broken)

    def test_non_boolean_four_wire_flag_rejected(self):
        broken = copy.deepcopy(DEFAULT_HARNESS_POLICY)
        broken["require_four_wire"] = "yes"
        with self.assertRaises(ValueError):
            validate_harness_policy(broken)

    def test_zero_drop_budget_rejected(self):
        broken = copy.deepcopy(DEFAULT_HARNESS_POLICY)
        broken["max_interface_voltage_drop_v"] = 0.0
        with self.assertRaises(ValueError):
            validate_harness_policy(broken)


class RedundantPairTests(unittest.TestCase):
    def test_matched_legs_are_balanced(self):
        result = validate_redundant_pair(_legs())
        self.assertTrue(result["balanced"])
        self.assertEqual(result["mismatched_attributes"], [])
        self.assertEqual(result["findings"], [])

    def test_a_different_gauge_breaks_the_pair(self):
        result = validate_redundant_pair(_legs(**{"conductor-gauge": "awg24"}))
        self.assertFalse(result["balanced"])
        self.assertEqual(result["mismatched_attributes"], ["conductor-gauge"])

    def test_every_governing_attribute_is_compared(self):
        for attribute in LEG_ATTRIBUTES:
            legs = _legs(**{attribute: "something-else"})
            result = validate_redundant_pair(legs)
            self.assertEqual(result["mismatched_attributes"], [attribute])

    def test_mismatch_is_named_in_the_findings(self):
        result = validate_redundant_pair(_legs(**{"routed-length-m": 4.8}))
        self.assertTrue(
            any("routed-length-m" in note for note in result["findings"])
        )

    def test_missing_attribute_rejected(self):
        legs = _legs()
        del legs[1]["cross-section-mm2"]
        with self.assertRaises(ValueError):
            validate_redundant_pair(legs)

    def test_a_loop_of_three_legs_rejected(self):
        with self.assertRaises(ValueError):
            validate_redundant_pair(_legs() + [copy.deepcopy(LEG)])

    def test_non_mapping_leg_rejected(self):
        with self.assertRaises(ValueError):
            validate_redundant_pair([copy.deepcopy(LEG), "the other wire"])


class GeometryTests(unittest.TestCase):
    def test_resistance_is_resistivity_times_length_over_section(self):
        self.assertAlmostEqual(
            conductor_resistance_ohm(RESISTIVITY, 2.4, 0.52),
            RESISTIVITY * 2.4 / 0.52,
            places=12,
        )

    def test_a_longer_run_raises_the_resistance(self):
        short = conductor_resistance_ohm(RESISTIVITY, 2.4, 0.52)
        long_run = conductor_resistance_ohm(RESISTIVITY, 4.8, 0.52)
        self.assertAlmostEqual(long_run, 2.0 * short, places=12)

    def test_a_bigger_section_lowers_the_resistance(self):
        thin = conductor_resistance_ohm(RESISTIVITY, 2.4, 0.52)
        thick = conductor_resistance_ohm(RESISTIVITY, 2.4, 1.04)
        self.assertAlmostEqual(thick, thin / 2.0, places=12)

    def test_zero_cross_section_rejected(self):
        with self.assertRaises(ValueError):
            conductor_resistance_ohm(RESISTIVITY, 2.4, 0.0)

    def test_negative_length_rejected(self):
        with self.assertRaises(ValueError):
            conductor_resistance_ohm(RESISTIVITY, -2.4, 0.52)

    def test_expected_loop_is_both_legs_in_series(self):
        self.assertAlmostEqual(
            expected_loop_resistance_ohm(_legs()),
            2.0 * EXPECTED_LEG_OHM,
            places=12,
        )

    def test_empty_leg_sequence_rejected(self):
        with self.assertRaises(ValueError):
            expected_loop_resistance_ohm([])


class LegReductionTests(unittest.TestCase):
    def test_leg_is_half_the_loop_once_the_joint_is_removed(self):
        self.assertAlmostEqual(
            single_leg_resistance_ohm(0.1624, 0.002), 0.0802, places=12
        )

    def test_a_zero_joint_simply_halves_the_loop(self):
        self.assertAlmostEqual(
            single_leg_resistance_ohm(0.1600, 0.0), 0.0800, places=12
        )

    def test_a_joint_that_swallows_the_loop_rejected(self):
        with self.assertRaises(ValueError):
            single_leg_resistance_ohm(0.0020, 0.0020)

    def test_negative_joint_rejected(self):
        with self.assertRaises(ValueError):
            single_leg_resistance_ohm(0.1624, -0.001)

    def test_zero_loop_reading_rejected(self):
        with self.assertRaises(ValueError):
            single_leg_resistance_ohm(0.0, 0.002)


class TemperatureTests(unittest.TestCase):
    def test_reading_at_the_reference_is_unchanged(self):
        self.assertAlmostEqual(
            temperature_corrected_resistance_ohm(0.08, 20.0, 20.0, ALPHA),
            0.08,
            places=12,
        )

    def test_warm_reading_is_referred_downwards(self):
        referred = temperature_corrected_resistance_ohm(0.08, 45.0, 20.0, ALPHA)
        self.assertAlmostEqual(referred, 0.08 / (1.0 + ALPHA * 25.0), places=12)

    def test_cold_reading_is_referred_upwards(self):
        referred = temperature_corrected_resistance_ohm(0.08, -5.0, 20.0, ALPHA)
        self.assertAlmostEqual(referred, 0.08 / (1.0 - ALPHA * 25.0), places=12)

    def test_impossible_correction_factor_rejected(self):
        with self.assertRaises(ValueError):
            temperature_corrected_resistance_ohm(0.08, -260.0, 20.0, ALPHA)

    def test_zero_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            temperature_corrected_resistance_ohm(0.08, 45.0, 20.0, 0.0)


class BandTests(unittest.TestCase):
    def test_a_run_on_its_prediction_is_within_band(self):
        self.assertEqual(
            categorize_harness_resistance(0.0800, 0.0800, TOLERANCE), WITHIN_BAND
        )

    def test_a_resisting_run_is_above_band(self):
        self.assertEqual(
            categorize_harness_resistance(0.1200, 0.0800, TOLERANCE), ABOVE_BAND
        )

    def test_a_run_below_its_prediction_is_below_band(self):
        self.assertEqual(
            categorize_harness_resistance(0.0400, 0.0800, TOLERANCE), BELOW_BAND
        )

    def test_the_upper_edge_is_still_within_band(self):
        edge = 0.0800 * (1.0 + TOLERANCE)
        self.assertAlmostEqual(edge, 0.092, places=9)
        self.assertEqual(
            categorize_harness_resistance(edge, 0.0800, TOLERANCE), WITHIN_BAND
        )

    def test_the_lower_edge_is_still_within_band(self):
        edge = 0.0800 * (1.0 - TOLERANCE)
        self.assertAlmostEqual(edge, 0.068, places=9)
        self.assertEqual(
            categorize_harness_resistance(edge, 0.0800, TOLERANCE), WITHIN_BAND
        )

    def test_every_category_is_reachable(self):
        seen = {
            categorize_harness_resistance(value, 0.0800, TOLERANCE)
            for value in (0.0400, 0.0800, 0.1200)
        }
        self.assertEqual(seen, set(HARNESS_RESISTANCE_CATEGORIES))

    def test_zero_measured_resistance_rejected(self):
        with self.assertRaises(ValueError):
            categorize_harness_resistance(0.0, 0.0800, TOLERANCE)


class FlightConfigurationTests(unittest.TestCase):
    def test_paralleled_redundant_legs_halve_the_run(self):
        self.assertAlmostEqual(
            flight_resistance_ohm(0.0800, PARALLEL_REDUNDANT), 0.0400, places=12
        )

    def test_a_single_active_leg_keeps_its_resistance(self):
        self.assertAlmostEqual(
            flight_resistance_ohm(0.0800, SINGLE_ACTIVE), 0.0800, places=12
        )

    def test_unknown_configuration_rejected(self):
        with self.assertRaises(ValueError):
            flight_resistance_ohm(0.0800, "one-and-a-half")

    def test_drop_is_resistance_times_current(self):
        self.assertAlmostEqual(
            interface_voltage_drop_v(0.0400, 3.2), 0.128, places=12
        )

    def test_zero_array_current_rejected(self):
        with self.assertRaises(ValueError):
            interface_voltage_drop_v(0.0400, 0.0)


class MeasurementTests(unittest.TestCase):
    def test_sound_run_reduces_to_the_predicted_leg(self):
        record = evaluate_harness_measurement(
            _measurement("run-a"), MAX_ARRAY_CURRENT_A
        )
        self.assertTrue(record["evaluable"])
        self.assertAlmostEqual(
            record["leg_resistance_ohm"], EXPECTED_LEG_OHM, places=9
        )
        self.assertEqual(record["category"], WITHIN_BAND)
        self.assertTrue(record["acceptable"])

    def test_warm_reading_is_referred_before_the_band_is_applied(self):
        warm = evaluate_harness_measurement(
            _measurement("run-a", temperature_c=60.0), MAX_ARRAY_CURRENT_A
        )
        self.assertGreater(
            warm["leg_resistance_at_measurement_ohm"], warm["leg_resistance_ohm"]
        )
        self.assertAlmostEqual(
            warm["leg_resistance_ohm"], EXPECTED_LEG_OHM, places=9
        )

    def test_a_resisting_crimp_is_named(self):
        record = evaluate_harness_measurement(
            _measurement("run-d", factor=1.40), MAX_ARRAY_CURRENT_A
        )
        self.assertEqual(record["category"], ABOVE_BAND)
        self.assertFalse(record["acceptable"])
        self.assertTrue(any("cold crimp" in note for note in record["findings"]))

    def test_a_run_below_the_band_is_named_as_a_routing_finding(self):
        record = evaluate_harness_measurement(
            _measurement("run-e", factor=0.60), MAX_ARRAY_CURRENT_A
        )
        self.assertEqual(record["category"], BELOW_BAND)
        self.assertTrue(
            any("routed path" in note for note in record["findings"])
        )

    def test_two_wire_reading_is_not_evaluable(self):
        record = evaluate_harness_measurement(
            _measurement("run-f", four_wire=False), MAX_ARRAY_CURRENT_A
        )
        self.assertFalse(record["evaluable"])
        self.assertIsNone(record["leg_resistance_ohm"])
        self.assertTrue(any("two-wire" in note for note in record["findings"]))

    def test_two_wire_reading_is_evaluable_once_the_policy_allows_it(self):
        policy = copy.deepcopy(DEFAULT_HARNESS_POLICY)
        policy["require_four_wire"] = False
        record = evaluate_harness_measurement(
            _measurement("run-f", four_wire=False), MAX_ARRAY_CURRENT_A, policy
        )
        self.assertTrue(record["evaluable"])
        self.assertEqual(record["category"], WITHIN_BAND)

    def test_mismatched_legs_cannot_be_halved(self):
        record = evaluate_harness_measurement(
            _measurement("run-g", legs=_legs(**{"routed-length-m": 4.8})),
            MAX_ARRAY_CURRENT_A,
        )
        self.assertFalse(record["evaluable"])
        self.assertFalse(record["balanced_pair"])
        self.assertEqual(record["mismatched_attributes"], ["routed-length-m"])

    def test_drop_budget_can_reject_an_in_band_run(self):
        policy = copy.deepcopy(DEFAULT_HARNESS_POLICY)
        policy["max_interface_voltage_drop_v"] = 0.05
        record = evaluate_harness_measurement(
            _measurement("run-a"), MAX_ARRAY_CURRENT_A, policy
        )
        self.assertEqual(record["category"], WITHIN_BAND)
        self.assertFalse(record["acceptable"])
        self.assertTrue(
            any("at the interface" in note for note in record["findings"])
        )

    def test_non_boolean_four_wire_field_rejected(self):
        measurement = _measurement("run-h")
        measurement["four_wire"] = "yes"
        with self.assertRaises(ValueError):
            evaluate_harness_measurement(measurement, MAX_ARRAY_CURRENT_A)

    def test_single_active_configuration_doubles_the_interface_drop(self):
        parallel = evaluate_harness_measurement(
            _measurement("run-a"), MAX_ARRAY_CURRENT_A
        )
        single = evaluate_harness_measurement(
            _measurement("run-a", configuration=SINGLE_ACTIVE), MAX_ARRAY_CURRENT_A
        )
        self.assertAlmostEqual(
            single["interface_voltage_drop_v"],
            2.0 * parallel["interface_voltage_drop_v"],
            places=12,
        )


class CampaignTests(unittest.TestCase):
    def test_sound_campaign_is_accepted(self):
        result = evaluate_harness_resistance_campaign(SOUND_CAMPAIGN)
        self.assertEqual(result["verdict"], HARNESS_RESISTANCE_ACCEPTED)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["rejected_run_ids"], [])
        self.assertEqual(result["unevaluable_run_ids"], [])

    def test_a_resisting_run_rejects_the_campaign_and_is_named(self):
        campaign = _campaign(
            [_measurement("run-a"), _measurement("run-b", factor=1.40)]
        )
        result = evaluate_harness_resistance_campaign(campaign)
        self.assertEqual(result["verdict"], HARNESS_RESISTANCE_REJECTED)
        self.assertEqual(result["rejected_run_ids"], ["run-b"])

    def test_a_two_wire_run_leaves_the_campaign_not_evaluated(self):
        campaign = _campaign(
            [_measurement("run-a"), _measurement("run-b", four_wire=False)]
        )
        result = evaluate_harness_resistance_campaign(campaign)
        self.assertEqual(result["verdict"], HARNESS_RESISTANCE_NOT_EVALUATED)
        self.assertIsNone(result["compliant"])
        self.assertEqual(result["unevaluable_run_ids"], ["run-b"])

    def test_a_mismatched_pair_leaves_the_campaign_not_evaluated(self):
        campaign = _campaign(
            [
                _measurement("run-a"),
                _measurement("run-b", legs=_legs(**{"conductor-gauge": "awg24"})),
            ]
        )
        result = evaluate_harness_resistance_campaign(campaign)
        self.assertEqual(result["verdict"], HARNESS_RESISTANCE_NOT_EVALUATED)
        self.assertTrue(
            any("re-read four-wire" in note for note in result["findings"])
        )

    def test_worst_interface_drop_is_reported(self):
        campaign = _campaign(
            [
                _measurement("run-a"),
                _measurement("run-b", configuration=SINGLE_ACTIVE),
            ]
        )
        result = evaluate_harness_resistance_campaign(campaign)
        expected = max(
            record["interface_voltage_drop_v"] for record in result["measurements"]
        )
        self.assertAlmostEqual(
            result["worst_interface_voltage_drop_v"], expected, places=12
        )

    def test_drop_budget_can_reject_an_otherwise_sound_campaign(self):
        policy = copy.deepcopy(DEFAULT_HARNESS_POLICY)
        policy["max_interface_voltage_drop_v"] = 0.05
        result = evaluate_harness_resistance_campaign(SOUND_CAMPAIGN, policy)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["rejected_run_ids"]), 3)

    def test_campaign_without_measurements_rejected(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        campaign["measurements"] = []
        with self.assertRaises(ValueError):
            evaluate_harness_resistance_campaign(campaign)

    def test_campaign_without_an_array_current_rejected(self):
        campaign = copy.deepcopy(SOUND_CAMPAIGN)
        del campaign["max_array_current_a"]
        with self.assertRaises(ValueError):
            evaluate_harness_resistance_campaign(campaign)

    def test_non_mapping_campaign_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_harness_resistance_campaign("three runs, all sound")


if __name__ == "__main__":
    unittest.main()
