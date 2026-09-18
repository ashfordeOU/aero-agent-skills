#!/usr/bin/env python3
"""Contract test for the zero-current telemetry readout assessment (offline)."""

import copy
import unittest

from e2020_zero_current_telemetry_readout_logic import (
    BUDGET_NOT_MET,
    FIXED_TERMS,
    FLOOR_LIMITED,
    RECOMMENDATION_MET,
    RECOMMENDATION_NOT_MET,
    ZERO_REPORTABLE,
    accuracy_floor_a,
    assess_zero_current_readout,
    budget_at_current_a,
    budget_upper_limit_a,
    dominant_fixed_term,
    error_at_current_a,
    fixed_error_terms_a,
    quantisation_step_a,
    retirement_options_a,
    validate_channel,
    zero_margin_a,
)

GOOD_CHANNEL = {
    "full_scale_a": 10.0,
    "accuracy_percent_of_reading": 1.0,
    "accuracy_percent_of_full_scale": 0.5,
    "gain_error_percent": 0.4,
    "offset_error_a": 0.010,
    "adc_bits": 10,
    "noise_a": 0.005,
}

FLOOR_CHANNEL = {
    "full_scale_a": 10.0,
    "accuracy_percent_of_reading": 1.0,
    "accuracy_percent_of_full_scale": 0.5,
    "gain_error_percent": 0.4,
    "offset_error_a": 0.040,
    "adc_bits": 12,
    "noise_a": 0.010,
}

HOPELESS_CHANNEL = {
    "full_scale_a": 10.0,
    "accuracy_percent_of_reading": 1.0,
    "accuracy_percent_of_full_scale": 0.5,
    "gain_error_percent": 0.4,
    "offset_error_a": 0.080,
    "adc_bits": 8,
    "noise_a": 0.020,
}

GAIN_LIMITED_CHANNEL = {
    "full_scale_a": 10.0,
    "accuracy_percent_of_reading": 1.0,
    "accuracy_percent_of_full_scale": 0.5,
    "gain_error_percent": 2.0,
    "offset_error_a": 0.010,
    "adc_bits": 10,
    "noise_a": 0.005,
}


def _channel(base, **overrides):
    channel = copy.deepcopy(base)
    channel.update(overrides)
    return channel


class ValidationTests(unittest.TestCase):
    def test_good_channel_validates(self):
        self.assertIs(validate_channel(GOOD_CHANNEL), GOOD_CHANNEL)

    def test_non_mapping_channel_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel("10 A shunt")

    def test_missing_term_rejected(self):
        channel = _channel(GOOD_CHANNEL)
        del channel["offset_error_a"]
        with self.assertRaises(ValueError):
            validate_channel(channel)

    def test_zero_full_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(_channel(GOOD_CHANNEL, full_scale_a=0.0))

    def test_negative_offset_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(_channel(GOOD_CHANNEL, offset_error_a=-0.01))

    def test_non_integer_resolution_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(_channel(GOOD_CHANNEL, adc_bits=10.5))

    def test_blanking_above_full_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(_channel(GOOD_CHANNEL, blanking_threshold_a=12.0))

    def test_empty_accuracy_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_channel(
                _channel(
                    GOOD_CHANNEL,
                    accuracy_percent_of_reading=0.0,
                    accuracy_percent_of_full_scale=0.0,
                )
            )


class QuantisationTests(unittest.TestCase):
    def test_ten_bit_step_over_ten_amps(self):
        self.assertAlmostEqual(quantisation_step_a(10.0, 10), 10.0 / 1024.0, places=12)

    def test_an_extra_bit_halves_the_step(self):
        self.assertAlmostEqual(
            quantisation_step_a(10.0, 11), 0.5 * quantisation_step_a(10.0, 10), places=12
        )

    def test_zero_bits_rejected(self):
        with self.assertRaises(ValueError):
            quantisation_step_a(10.0, 0)

    def test_boolean_resolution_rejected(self):
        with self.assertRaises(ValueError):
            quantisation_step_a(10.0, True)


class ErrorAndBudgetTests(unittest.TestCase):
    def test_fixed_terms_cover_every_named_term(self):
        terms = fixed_error_terms_a(GOOD_CHANNEL)
        for name in FIXED_TERMS:
            self.assertIn(name, terms)

    def test_error_at_zero_is_the_sum_of_the_fixed_terms(self):
        self.assertAlmostEqual(
            error_at_current_a(GOOD_CHANNEL, 0.0),
            sum(fixed_error_terms_a(GOOD_CHANNEL).values()),
            places=12,
        )

    def test_error_grows_with_the_reading(self):
        self.assertAlmostEqual(
            error_at_current_a(GOOD_CHANNEL, 10.0)
            - error_at_current_a(GOOD_CHANNEL, 0.0),
            0.04,
            places=12,
        )

    def test_budget_at_zero_is_the_full_scale_term_only(self):
        self.assertAlmostEqual(budget_at_current_a(GOOD_CHANNEL, 0.0), 0.05, places=12)

    def test_budget_at_full_scale_adds_the_reading_term(self):
        self.assertAlmostEqual(budget_at_current_a(GOOD_CHANNEL, 10.0), 0.15, places=12)

    def test_current_above_full_scale_rejected(self):
        with self.assertRaises(ValueError):
            error_at_current_a(GOOD_CHANNEL, 11.0)

    def test_negative_current_rejected(self):
        with self.assertRaises(ValueError):
            budget_at_current_a(GOOD_CHANNEL, -1.0)

    def test_zero_margin_is_budget_less_error(self):
        self.assertAlmostEqual(
            zero_margin_a(GOOD_CHANNEL), 0.05 - 0.0198828125, places=12
        )

    def test_dominant_term_is_the_largest_fixed_contributor(self):
        self.assertEqual(dominant_fixed_term(GOOD_CHANNEL), "telemetry-offset")

    def test_coarse_resolution_makes_quantisation_dominant(self):
        self.assertEqual(
            dominant_fixed_term(_channel(GOOD_CHANNEL, adc_bits=6)),
            "acquisition-quantisation",
        )


class AccuracyFloorTests(unittest.TestCase):
    def test_a_channel_inside_budget_at_zero_has_a_zero_floor(self):
        self.assertAlmostEqual(accuracy_floor_a(GOOD_CHANNEL), 0.0, places=12)

    def test_a_fixed_error_exactly_on_the_budget_still_reaches_zero(self):
        # offset + half a step + noise sums to the 0.05 A full-scale term, a
        # value the float sum lands on only to within representation error.
        channel = _channel(
            GOOD_CHANNEL, offset_error_a=0.04, adc_bits=10, noise_a=0.0051171875
        )
        self.assertAlmostEqual(accuracy_floor_a(channel), 0.0, places=9)
        self.assertEqual(
            assess_zero_current_readout(channel)["verdict"], ZERO_REPORTABLE
        )

    def test_an_excess_fixed_error_pushes_the_floor_up(self):
        self.assertAlmostEqual(
            accuracy_floor_a(FLOOR_CHANNEL), 0.001220703125 / 0.006, places=9
        )

    def test_a_hopeless_channel_has_no_floor_in_range(self):
        self.assertIsNone(accuracy_floor_a(HOPELESS_CHANNEL))

    def test_no_floor_when_the_gain_term_outruns_the_reading_budget(self):
        channel = _channel(GAIN_LIMITED_CHANNEL, offset_error_a=0.40, noise_a=0.10)
        self.assertIsNone(accuracy_floor_a(channel))

    def test_upper_limit_is_none_when_the_budget_holds_to_full_scale(self):
        self.assertIsNone(budget_upper_limit_a(GOOD_CHANNEL))

    def test_upper_limit_found_when_the_gain_term_outruns_the_budget(self):
        self.assertAlmostEqual(
            budget_upper_limit_a(GAIN_LIMITED_CHANNEL), 0.0301171875 / 0.01, places=9
        )


class AssessmentTests(unittest.TestCase):
    def test_good_channel_reports_to_zero(self):
        result = assess_zero_current_readout(GOOD_CHANNEL)
        self.assertEqual(result["verdict"], ZERO_REPORTABLE)
        self.assertEqual(result["recommendation_status"], RECOMMENDATION_MET)
        self.assertAlmostEqual(result["lowest_reportable_current_a"], 0.0, places=12)
        self.assertAlmostEqual(result["zero_shortfall_a"], 0.0, places=12)

    def test_floor_channel_is_floor_limited_with_a_shortfall(self):
        result = assess_zero_current_readout(FLOOR_CHANNEL)
        self.assertEqual(result["verdict"], FLOOR_LIMITED)
        self.assertEqual(result["recommendation_status"], RECOMMENDATION_NOT_MET)
        self.assertAlmostEqual(result["zero_shortfall_a"], 0.001220703125, places=12)
        self.assertTrue(any("first met at" in f for f in result["findings"]))

    def test_hopeless_channel_fails_the_budget_everywhere(self):
        result = assess_zero_current_readout(HOPELESS_CHANNEL)
        self.assertEqual(result["verdict"], BUDGET_NOT_MET)
        self.assertIsNone(result["lowest_reportable_current_a"])
        self.assertTrue(any("never absorbed" in f for f in result["findings"]))

    def test_a_blanking_deadband_raises_the_reportable_floor(self):
        channel = _channel(GOOD_CHANNEL, blanking_threshold_a=0.05)
        result = assess_zero_current_readout(channel)
        self.assertEqual(result["verdict"], FLOOR_LIMITED)
        self.assertAlmostEqual(result["lowest_reportable_current_a"], 0.05, places=12)
        self.assertTrue(any("deadband" in f for f in result["findings"]))

    def test_a_blanking_deadband_does_not_change_the_accuracy_floor(self):
        channel = _channel(GOOD_CHANNEL, blanking_threshold_a=0.05)
        self.assertAlmostEqual(accuracy_floor_a(channel), 0.0, places=12)

    def test_gain_limited_channel_reports_the_upper_shortfall(self):
        result = assess_zero_current_readout(GAIN_LIMITED_CHANNEL)
        self.assertEqual(result["verdict"], ZERO_REPORTABLE)
        self.assertIsNotNone(result["budget_upper_limit_a"])
        self.assertTrue(any("upper end" in f for f in result["findings"]))

    def test_assessment_rejects_a_broken_channel(self):
        with self.assertRaises(ValueError):
            assess_zero_current_readout(_channel(GOOD_CHANNEL, noise_a=-1.0))


class RetirementTests(unittest.TestCase):
    def test_nothing_to_retire_on_a_compliant_channel(self):
        options = retirement_options_a(GOOD_CHANNEL)
        for name in FIXED_TERMS:
            self.assertAlmostEqual(options[name], 0.0, places=12)

    def test_a_term_larger_than_the_shortfall_can_retire_it_alone(self):
        options = retirement_options_a(FLOOR_CHANNEL)
        self.assertAlmostEqual(options["telemetry-offset"], 0.001220703125, places=12)

    def test_a_term_smaller_than_the_shortfall_cannot_retire_it_alone(self):
        options = retirement_options_a(HOPELESS_CHANNEL)
        self.assertIsNone(options["readout-noise"])


if __name__ == "__main__":
    unittest.main()
