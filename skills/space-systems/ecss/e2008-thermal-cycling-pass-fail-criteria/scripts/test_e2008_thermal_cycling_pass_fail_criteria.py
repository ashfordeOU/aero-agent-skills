#!/usr/bin/env python3
"""Contract test for cycled photovoltaic-coupon acceptance criteria (offline).

This is the gate 3 behaviour contract. Every workflow step of the leaf is
exercised: the reference correction that makes two readings comparable,
the continuity decision, the power-retention decision, and the combined
verdict that stops a coupon at the post-cycling review.
"""

import copy
import math
import unittest

from e2008_thermal_cycling_pass_fail_criteria_logic import (
    COUPON_ACCEPTED,
    COUPON_REJECTED,
    DEFAULT_ACCEPTANCE_CRITERIA,
    DISCONTINUITY_EVENTS,
    OPEN_CIRCUIT,
    POWER_RETENTION,
    RESISTANCE_DRIFT,
    correct_power_to_reference,
    evaluate_continuity,
    evaluate_cycling_acceptance,
    evaluate_power_retention,
    power_retention_ratio,
    resistance_drift_ratio,
    validate_acceptance_criteria,
)

ALPHA = -0.0025

REFERENCE_READING = {
    "power_w": 100.0,
    "cell_temperature_c": 25.0,
    "irradiance_w_m2": 1367.0,
}

CLEAN_CASE = {
    "before_resistance_ohm": 0.400,
    "after_resistance_ohm": 0.404,
    "discontinuity_events": 0,
    "before_reading": dict(REFERENCE_READING),
    "after_reading": dict(REFERENCE_READING, power_w=99.0),
    "power_temperature_coefficient_per_k": ALPHA,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_acceptance_criteria(DEFAULT_ACCEPTANCE_CRITERIA),
            DEFAULT_ACCEPTANCE_CRITERIA,
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_acceptance_criteria("source control drawing")

    def test_negative_drift_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_CRITERIA)
        broken["max_resistance_drift_ratio"] = -0.01
        with self.assertRaises(ValueError):
            validate_acceptance_criteria(broken)

    def test_drift_allowance_of_a_whole_doubling_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_CRITERIA)
        broken["max_resistance_drift_ratio"] = 1.5
        with self.assertRaises(ValueError):
            validate_acceptance_criteria(broken)

    def test_fractional_discontinuity_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_CRITERIA)
        broken["max_discontinuity_events"] = 0.5
        with self.assertRaises(ValueError):
            validate_acceptance_criteria(broken)

    def test_retention_threshold_above_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_CRITERIA)
        broken["min_power_retention_ratio"] = 1.02
        with self.assertRaises(ValueError):
            validate_acceptance_criteria(broken)

    def test_zero_reference_irradiance_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_CRITERIA)
        broken["reference_irradiance_w_m2"] = 0.0
        with self.assertRaises(ValueError):
            validate_acceptance_criteria(broken)

    def test_missing_retention_threshold_rejected(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_CRITERIA)
        del broken["min_power_retention_ratio"]
        with self.assertRaises(ValueError):
            validate_acceptance_criteria(broken)


class ReferenceCorrectionTests(unittest.TestCase):
    def test_reading_already_at_reference_is_unchanged(self):
        self.assertAlmostEqual(
            correct_power_to_reference(REFERENCE_READING, ALPHA), 100.0, places=9
        )

    def test_weak_illumination_is_scaled_up(self):
        reading = dict(REFERENCE_READING, power_w=90.0, irradiance_w_m2=1200.0)
        self.assertAlmostEqual(
            correct_power_to_reference(reading, ALPHA), 102.525, places=6
        )

    def test_hot_reading_is_corrected_upward(self):
        reading = dict(REFERENCE_READING, power_w=95.0, cell_temperature_c=45.0)
        self.assertAlmostEqual(
            correct_power_to_reference(reading, ALPHA), 100.0, places=6
        )

    def test_weak_and_hot_reading_takes_both_corrections(self):
        reading = dict(
            REFERENCE_READING,
            power_w=90.0,
            cell_temperature_c=35.0,
            irradiance_w_m2=1200.0,
        )
        self.assertAlmostEqual(
            correct_power_to_reference(reading, ALPHA), 105.1538461538, places=6
        )

    def test_zero_temperature_coefficient_leaves_temperature_alone(self):
        reading = dict(REFERENCE_READING, cell_temperature_c=60.0)
        self.assertAlmostEqual(
            correct_power_to_reference(reading, 0.0), 100.0, places=9
        )

    def test_non_mapping_reading_rejected(self):
        with self.assertRaises(ValueError):
            correct_power_to_reference("100 W", ALPHA)

    def test_zero_irradiance_rejected(self):
        reading = dict(REFERENCE_READING, irradiance_w_m2=0.0)
        with self.assertRaises(ValueError):
            correct_power_to_reference(reading, ALPHA)

    def test_temperature_below_absolute_zero_rejected(self):
        reading = dict(REFERENCE_READING, cell_temperature_c=-300.0)
        with self.assertRaises(ValueError):
            correct_power_to_reference(reading, ALPHA)

    def test_implausible_temperature_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            correct_power_to_reference(REFERENCE_READING, -0.5)

    def test_correction_that_inverts_the_reading_rejected(self):
        reading = dict(REFERENCE_READING, cell_temperature_c=1000.0)
        with self.assertRaises(ValueError):
            correct_power_to_reference(reading, -0.05)

    def test_negative_power_rejected(self):
        reading = dict(REFERENCE_READING, power_w=-10.0)
        with self.assertRaises(ValueError):
            correct_power_to_reference(reading, ALPHA)


class ResistanceDriftTests(unittest.TestCase):
    def test_one_percent_rise_is_one_percent_drift(self):
        self.assertAlmostEqual(resistance_drift_ratio(0.400, 0.404), 0.01, places=9)

    def test_unchanged_resistance_is_zero_drift(self):
        self.assertAlmostEqual(resistance_drift_ratio(0.400, 0.400), 0.0, places=12)

    def test_a_fallen_resistance_is_a_negative_drift(self):
        self.assertAlmostEqual(resistance_drift_ratio(0.400, 0.380), -0.05, places=9)

    def test_zero_pre_cycling_resistance_rejected(self):
        with self.assertRaises(ValueError):
            resistance_drift_ratio(0.0, 0.404)

    def test_negative_post_cycling_resistance_rejected(self):
        with self.assertRaises(ValueError):
            resistance_drift_ratio(0.400, -0.1)

    def test_non_numeric_resistance_rejected(self):
        with self.assertRaises(ValueError):
            resistance_drift_ratio("400 mohm", 0.404)


class ContinuityTests(unittest.TestCase):
    def test_small_drift_and_no_events_is_compliant(self):
        result = evaluate_continuity(0.400, 0.404, 0)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["failed_criteria"], [])
        self.assertAlmostEqual(result["drift_ratio"], 0.01, places=9)

    def test_drift_exactly_on_the_allowance_is_compliant(self):
        allowance = DEFAULT_ACCEPTANCE_CRITERIA["max_resistance_drift_ratio"]
        result = evaluate_continuity(0.400, 0.400 * (1.0 + allowance), 0)
        self.assertAlmostEqual(result["drift_ratio"], allowance, places=9)
        self.assertTrue(result["compliant"])

    def test_drift_beyond_the_allowance_fails(self):
        result = evaluate_continuity(0.400, 0.500, 0)
        self.assertFalse(result["compliant"])
        self.assertIn(RESISTANCE_DRIFT, result["failed_criteria"])

    def test_open_string_is_reported_as_an_open_circuit(self):
        result = evaluate_continuity(0.400, None, 0)
        self.assertTrue(result["open_circuit"])
        self.assertIn(OPEN_CIRCUIT, result["failed_criteria"])
        self.assertIsNone(result["drift_ratio"])

    def test_infinite_resistance_is_also_an_open_circuit(self):
        result = evaluate_continuity(0.400, math.inf, 0)
        self.assertIn(OPEN_CIRCUIT, result["failed_criteria"])

    def test_a_single_monitored_dropout_fails(self):
        result = evaluate_continuity(0.400, 0.404, 1)
        self.assertFalse(result["compliant"])
        self.assertIn(DISCONTINUITY_EVENTS, result["failed_criteria"])

    def test_drift_and_dropouts_are_reported_separately(self):
        result = evaluate_continuity(0.400, 0.600, 3)
        self.assertEqual(len(result["failed_criteria"]), 2)
        self.assertEqual(len(result["findings"]), 2)

    def test_negative_event_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_continuity(0.400, 0.404, -1)

    def test_fractional_event_count_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_continuity(0.400, 0.404, 1.5)

    def test_open_circuit_still_validates_the_pre_cycling_reading(self):
        with self.assertRaises(ValueError):
            evaluate_continuity(0.0, None, 0)


class PowerRetentionTests(unittest.TestCase):
    def test_one_percent_loss_is_compliant(self):
        after = dict(REFERENCE_READING, power_w=99.0)
        result = evaluate_power_retention(REFERENCE_READING, after, ALPHA)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["retention_ratio"], 0.99, places=9)
        self.assertAlmostEqual(result["loss_ratio"], 0.01, places=9)

    def test_retention_exactly_on_the_threshold_is_compliant(self):
        threshold = DEFAULT_ACCEPTANCE_CRITERIA["min_power_retention_ratio"]
        before = dict(REFERENCE_READING, power_w=120.0, cell_temperature_c=45.0,
                      irradiance_w_m2=1100.0)
        after = dict(before, power_w=120.0 * threshold)
        result = evaluate_power_retention(before, after, ALPHA)
        self.assertAlmostEqual(result["retention_ratio"], threshold, places=9)
        self.assertTrue(result["compliant"])

    def test_loss_beyond_the_threshold_fails(self):
        after = dict(REFERENCE_READING, power_w=95.0)
        result = evaluate_power_retention(REFERENCE_READING, after, ALPHA)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("retained" in f for f in result["findings"]))

    def test_a_hotter_after_reading_is_not_a_power_loss(self):
        # The raw ratio is 0.95 and would fail; the reference correction
        # shows the coupon lost nothing at all.
        after = dict(REFERENCE_READING, power_w=95.0, cell_temperature_c=45.0)
        result = evaluate_power_retention(REFERENCE_READING, after, ALPHA)
        self.assertAlmostEqual(result["retention_ratio"], 1.0, places=6)
        self.assertTrue(result["compliant"])

    def test_ratio_helper_matches_the_evaluation(self):
        after = dict(REFERENCE_READING, power_w=99.0)
        ratio = power_retention_ratio(REFERENCE_READING, after, ALPHA)
        result = evaluate_power_retention(REFERENCE_READING, after, ALPHA)
        self.assertAlmostEqual(ratio, result["retention_ratio"], places=12)

    def test_zero_pre_cycling_power_rejected(self):
        before = dict(REFERENCE_READING, power_w=0.0)
        with self.assertRaises(ValueError):
            power_retention_ratio(before, REFERENCE_READING, ALPHA)

    def test_missing_after_reading_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_power_retention(REFERENCE_READING, None, ALPHA)

    def test_missing_temperature_coefficient_rejected(self):
        after = dict(REFERENCE_READING, power_w=99.0)
        with self.assertRaises(ValueError):
            evaluate_power_retention(REFERENCE_READING, after, None)


class AcceptanceTests(unittest.TestCase):
    def test_clean_coupon_is_accepted(self):
        result = evaluate_cycling_acceptance(CLEAN_CASE)
        self.assertEqual(result["verdict"], COUPON_ACCEPTED)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["failed_criteria"], [])
        self.assertEqual(result["findings"], [])

    def test_power_shortfall_alone_rejects_the_coupon(self):
        case = _case(
            CLEAN_CASE, after_reading=dict(REFERENCE_READING, power_w=95.0)
        )
        result = evaluate_cycling_acceptance(case)
        self.assertEqual(result["verdict"], COUPON_REJECTED)
        self.assertEqual(result["failed_criteria"], [POWER_RETENTION])

    def test_drift_alone_rejects_the_coupon(self):
        result = evaluate_cycling_acceptance(_case(CLEAN_CASE, after_resistance_ohm=0.5))
        self.assertEqual(result["verdict"], COUPON_REJECTED)
        self.assertIn(RESISTANCE_DRIFT, result["failed_criteria"])

    def test_open_circuit_rejects_the_coupon_even_at_full_power(self):
        case = _case(CLEAN_CASE, after_resistance_ohm=None)
        result = evaluate_cycling_acceptance(case)
        self.assertTrue(result["open_circuit"])
        self.assertEqual(result["verdict"], COUPON_REJECTED)

    def test_every_failed_criterion_is_named(self):
        case = _case(
            CLEAN_CASE,
            after_resistance_ohm=0.600,
            discontinuity_events=2,
            after_reading=dict(REFERENCE_READING, power_w=90.0),
        )
        result = evaluate_cycling_acceptance(case)
        self.assertEqual(len(result["failed_criteria"]), 3)
        self.assertEqual(len(result["findings"]), 3)

    def test_acceptance_reports_the_measured_numbers(self):
        result = evaluate_cycling_acceptance(CLEAN_CASE)
        self.assertAlmostEqual(result["drift_ratio"], 0.01, places=9)
        self.assertAlmostEqual(result["retention_ratio"], 0.99, places=9)
        self.assertEqual(result["discontinuity_events"], 0)

    def test_missing_post_cycling_resistance_is_not_an_open_circuit(self):
        case = _case(CLEAN_CASE)
        del case["after_resistance_ohm"]
        with self.assertRaises(ValueError):
            evaluate_cycling_acceptance(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cycling_acceptance("coupon three")

    def test_tighter_criteria_can_reject_an_otherwise_clean_coupon(self):
        strict = copy.deepcopy(DEFAULT_ACCEPTANCE_CRITERIA)
        strict["min_power_retention_ratio"] = 0.995
        self.assertEqual(
            evaluate_cycling_acceptance(CLEAN_CASE, strict)["verdict"], COUPON_REJECTED
        )

    def test_criteria_are_validated_before_any_measurement_is_read(self):
        broken = copy.deepcopy(DEFAULT_ACCEPTANCE_CRITERIA)
        broken["max_discontinuity_events"] = -1
        with self.assertRaises(ValueError):
            evaluate_cycling_acceptance(CLEAN_CASE, broken)


if __name__ == "__main__":
    unittest.main()
