#!/usr/bin/env python3
"""Contract test for status telemetry voltage confirmation (offline)."""

import copy
import unittest

from e2020_status_telemetry_voltage_confirmation_logic import (
    CATEGORIES,
    CONFIRMING_CATEGORIES,
    DEFAULT_DE_ENERGISED_FRACTION,
    OFF_CONFIRMED,
    OFF_CONTRADICTED,
    ON_CONFIRMED,
    ON_UNCONFIRMED_OVER,
    ON_UNCONFIRMED_UNDER,
    STATES,
    VERDICT_CONFIRMS,
    VERDICT_DOES_NOT_CONFIRM,
    assess_status_confirmation,
    categorize_report,
    confirmation_margin_v,
    derive_status,
    in_band,
    nominal_voltage_band,
    validate_sense_thresholds,
)

BAND = nominal_voltage_band(28.0, 0.05, 0.05)

ON_CASE = {
    "nominal_output_v": 28.0,
    "lower_tolerance_fraction": 0.05,
    "upper_tolerance_fraction": 0.05,
    "on_threshold_v": 27.0,
    "off_threshold_v": 25.0,
    "measured_output_v": 28.0,
    "reported_state": "on",
    "previous_state": "on",
}

OFF_CASE = {
    "nominal_output_v": 28.0,
    "lower_tolerance_fraction": 0.05,
    "upper_tolerance_fraction": 0.05,
    "on_threshold_v": 27.0,
    "off_threshold_v": 25.0,
    "measured_output_v": 1.0,
    "reported_state": "off",
    "previous_state": "off",
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class BandTests(unittest.TestCase):
    def test_band_floor_follows_the_lower_tolerance(self):
        self.assertAlmostEqual(BAND["min_v"], 26.6, places=9)

    def test_band_ceiling_follows_the_upper_tolerance(self):
        self.assertAlmostEqual(BAND["max_v"], 29.4, places=9)

    def test_band_keeps_the_nominal(self):
        self.assertAlmostEqual(BAND["nominal_v"], 28.0, places=9)

    def test_asymmetric_tolerances_are_honoured(self):
        band = nominal_voltage_band(28.0, 0.10, 0.02)
        self.assertAlmostEqual(band["min_v"], 25.2, places=9)
        self.assertAlmostEqual(band["max_v"], 28.56, places=9)

    def test_zero_nominal_rejected(self):
        with self.assertRaises(ValueError):
            nominal_voltage_band(0.0, 0.05, 0.05)

    def test_lower_tolerance_of_one_rejected(self):
        with self.assertRaises(ValueError):
            nominal_voltage_band(28.0, 1.0, 0.05)

    def test_negative_upper_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            nominal_voltage_band(28.0, 0.05, -0.05)


class InBandTests(unittest.TestCase):
    def test_nominal_sits_in_band(self):
        self.assertTrue(in_band(28.0, BAND))

    def test_measurement_on_the_floor_counts_as_in_band(self):
        self.assertTrue(in_band(BAND["min_v"], BAND))

    def test_measurement_on_the_ceiling_counts_as_in_band(self):
        self.assertTrue(in_band(BAND["max_v"], BAND))

    def test_collapsed_output_is_out_of_band(self):
        self.assertFalse(in_band(20.0, BAND))

    def test_margin_is_zero_on_the_floor(self):
        self.assertAlmostEqual(confirmation_margin_v(BAND["min_v"], BAND), 0.0, places=9)

    def test_margin_goes_negative_outside_the_band(self):
        self.assertLess(confirmation_margin_v(20.0, BAND), 0.0)

    def test_margin_is_largest_at_the_nominal(self):
        self.assertAlmostEqual(confirmation_margin_v(28.0, BAND), 1.4, places=9)


class ThresholdTests(unittest.TestCase):
    def test_thresholds_inside_the_band_are_adequate(self):
        checked = validate_sense_thresholds(BAND, 27.0, 25.0)
        self.assertTrue(checked["thresholds_adequate"])
        self.assertEqual(checked["findings"], [])

    def test_hysteresis_is_the_threshold_separation(self):
        checked = validate_sense_thresholds(BAND, 27.0, 25.0)
        self.assertAlmostEqual(checked["hysteresis_v"], 2.0, places=9)

    def test_on_threshold_below_the_band_floor_is_reported(self):
        checked = validate_sense_thresholds(BAND, 24.0, 20.0)
        self.assertFalse(checked["thresholds_adequate"])
        self.assertFalse(checked["on_threshold_inside_band"])
        self.assertTrue(any("below the band floor" in f for f in checked["findings"]))

    def test_on_threshold_above_the_band_ceiling_is_reported(self):
        checked = validate_sense_thresholds(BAND, 31.0, 25.0)
        self.assertFalse(checked["thresholds_adequate"])
        self.assertTrue(
            any("above the band ceiling" in f for f in checked["findings"])
        )

    def test_on_threshold_exactly_on_the_floor_is_accepted(self):
        checked = validate_sense_thresholds(BAND, BAND["min_v"], 25.0)
        self.assertTrue(checked["on_threshold_inside_band"])
        self.assertTrue(checked["thresholds_adequate"])

    def test_thin_hysteresis_is_reported(self):
        checked = validate_sense_thresholds(BAND, 27.0, 26.9)
        self.assertFalse(checked["thresholds_adequate"])
        self.assertTrue(any("chatters" in f for f in checked["findings"]))

    def test_inverted_thresholds_rejected(self):
        with self.assertRaises(ValueError):
            validate_sense_thresholds(BAND, 25.0, 27.0)

    def test_equal_thresholds_rejected(self):
        with self.assertRaises(ValueError):
            validate_sense_thresholds(BAND, 27.0, 27.0)

    def test_non_mapping_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_sense_thresholds("28 volts", 27.0, 25.0)


class DeriveStatusTests(unittest.TestCase):
    def test_above_the_on_threshold_derives_on(self):
        self.assertEqual(derive_status(28.0, 27.0, 25.0, "off"), "on")

    def test_below_the_off_threshold_derives_off(self):
        self.assertEqual(derive_status(1.0, 27.0, 25.0, "on"), "off")

    def test_exactly_on_the_on_threshold_derives_on(self):
        self.assertEqual(derive_status(27.0, 27.0, 25.0, "off"), "on")

    def test_inside_the_hysteresis_band_holds_the_previous_state(self):
        self.assertEqual(derive_status(26.0, 27.0, 25.0, "on"), "on")
        self.assertEqual(derive_status(26.0, 27.0, 25.0, "off"), "off")

    def test_unknown_previous_state_rejected(self):
        with self.assertRaises(ValueError):
            derive_status(28.0, 27.0, 25.0, "unknown")

    def test_inverted_thresholds_rejected_in_derivation(self):
        with self.assertRaises(ValueError):
            derive_status(28.0, 25.0, 27.0, "on")


class CategoryTests(unittest.TestCase):
    def test_on_inside_the_band_is_confirmed(self):
        self.assertEqual(categorize_report("on", 28.0, BAND), ON_CONFIRMED)

    def test_on_below_the_band_is_unconfirmed_under(self):
        self.assertEqual(categorize_report("on", 20.0, BAND), ON_UNCONFIRMED_UNDER)

    def test_on_above_the_band_is_unconfirmed_over(self):
        self.assertEqual(categorize_report("on", 32.0, BAND), ON_UNCONFIRMED_OVER)

    def test_off_on_a_dead_output_is_confirmed(self):
        self.assertEqual(categorize_report("off", 1.0, BAND), OFF_CONFIRMED)

    def test_off_on_a_live_output_is_contradicted(self):
        self.assertEqual(categorize_report("off", 28.0, BAND), OFF_CONTRADICTED)

    def test_off_on_the_de_energised_level_is_confirmed(self):
        level = DEFAULT_DE_ENERGISED_FRACTION * BAND["nominal_v"]
        self.assertEqual(categorize_report("off", level, BAND), OFF_CONFIRMED)

    def test_every_confirming_category_is_a_known_category(self):
        for category in CONFIRMING_CATEGORIES:
            self.assertIn(category, CATEGORIES)

    def test_unknown_reported_state_rejected(self):
        with self.assertRaises(ValueError):
            categorize_report("standby", 28.0, BAND)


class AssessmentTests(unittest.TestCase):
    def test_healthy_on_report_confirms(self):
        result = assess_status_confirmation(ON_CASE)
        self.assertEqual(result["verdict"], VERDICT_CONFIRMS)
        self.assertEqual(result["category"], ON_CONFIRMED)
        self.assertEqual(result["findings"], [])

    def test_healthy_off_report_confirms(self):
        result = assess_status_confirmation(OFF_CASE)
        self.assertEqual(result["verdict"], VERDICT_CONFIRMS)
        self.assertEqual(result["category"], OFF_CONFIRMED)

    def test_on_bit_over_a_collapsed_output_does_not_confirm(self):
        result = assess_status_confirmation(_case(ON_CASE, measured_output_v=20.0))
        self.assertEqual(result["verdict"], VERDICT_DOES_NOT_CONFIRM)
        self.assertEqual(result["category"], ON_UNCONFIRMED_UNDER)
        self.assertTrue(
            any("believed" in f for f in result["findings"])
        )

    def test_off_bit_over_a_live_output_does_not_confirm(self):
        result = assess_status_confirmation(
            _case(OFF_CASE, measured_output_v=28.0)
        )
        self.assertEqual(result["category"], OFF_CONTRADICTED)
        self.assertFalse(result["confirms"])

    def test_measurement_on_the_band_floor_still_confirms(self):
        result = assess_status_confirmation(
            _case(
                ON_CASE,
                on_threshold_v=BAND["min_v"],
                measured_output_v=BAND["min_v"],
            )
        )
        self.assertAlmostEqual(result["confirmation_margin_v"], 0.0, places=9)
        self.assertEqual(result["verdict"], VERDICT_CONFIRMS)

    def test_a_threshold_below_the_band_floor_blocks_confirmation(self):
        result = assess_status_confirmation(
            _case(ON_CASE, on_threshold_v=24.0, off_threshold_v=20.0)
        )
        self.assertFalse(result["thresholds_adequate"])
        self.assertEqual(result["verdict"], VERDICT_DOES_NOT_CONFIRM)

    def test_reported_bit_disagreeing_with_the_sense_chain_is_named(self):
        result = assess_status_confirmation(
            _case(ON_CASE, measured_output_v=1.0)
        )
        self.assertEqual(result["derived_state"], "off")
        self.assertTrue(
            any("does not come from the output" in f for f in result["findings"])
        )

    def test_previous_state_defaults_to_the_reported_state(self):
        case = _case(ON_CASE, measured_output_v=26.0)
        del case["previous_state"]
        result = assess_status_confirmation(case)
        self.assertEqual(result["derived_state"], "on")

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_status_confirmation("on")

    def test_unknown_reported_state_rejected_in_assessment(self):
        with self.assertRaises(ValueError):
            assess_status_confirmation(_case(ON_CASE, reported_state="tripped"))

    def test_every_state_is_assessable(self):
        for state in STATES:
            self.assertIn(state, ("on", "off"))

    def test_result_is_deterministic(self):
        first = assess_status_confirmation(ON_CASE)
        second = assess_status_confirmation(ON_CASE)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=1)
