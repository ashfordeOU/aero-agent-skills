#!/usr/bin/env python3
"""Contract test for the output-current telemetry provision (offline)."""

import copy
import unittest

from e2020_output_current_telemetry_provision_logic import (
    CHANNEL_ADEQUATE,
    CHANNEL_INADEQUATE,
    DEFAULT_RANGE_HEADROOM_FRACTION,
    VERDICT_ADEQUATE,
    VERDICT_INADEQUATE,
    assess_channel,
    assess_current_telemetry_provision,
    channel_error_a,
    quantisation_step_a,
    required_full_scale_a,
    telemetry_coverage,
)

GOOD_CHANNEL = {
    "limiter_id": "limiter-1",
    "full_scale_a": 10.0,
    "resolution_bits": 8,
    "limitation_current_a": 8.0,
    "operating_current_a": 4.0,
    "gain_error_fraction": 0.01,
    "offset_error_fraction": 0.005,
    "required_accuracy_a": 0.20,
    "required_resolution_a": 0.08,
    "range_headroom_fraction": 0.20,
    "limiters_served": 1,
}

GOOD_CASE = {
    "limiters": [
        {"limiter_id": "limiter-1", "channel": copy.deepcopy(GOOD_CHANNEL)},
        {
            "limiter_id": "limiter-2",
            "channel": dict(copy.deepcopy(GOOD_CHANNEL), limiter_id="limiter-2"),
        },
    ]
}


def _channel(**overrides):
    channel = copy.deepcopy(GOOD_CHANNEL)
    channel.update(overrides)
    return channel


class QuantisationTests(unittest.TestCase):
    def test_step_spans_full_scale_over_the_code_count(self):
        self.assertAlmostEqual(quantisation_step_a(10.0, 8), 10.0 / 255.0, places=12)

    def test_one_more_bit_roughly_halves_the_step(self):
        coarse = quantisation_step_a(10.0, 8)
        fine = quantisation_step_a(10.0, 9)
        self.assertLess(fine, coarse)

    def test_single_bit_channel_has_a_full_scale_step(self):
        self.assertAlmostEqual(quantisation_step_a(10.0, 1), 10.0, places=12)

    def test_fractional_bits_rejected(self):
        with self.assertRaises(ValueError):
            quantisation_step_a(10.0, 8.5)

    def test_zero_bits_rejected(self):
        with self.assertRaises(ValueError):
            quantisation_step_a(10.0, 0)

    def test_zero_full_scale_rejected(self):
        with self.assertRaises(ValueError):
            quantisation_step_a(0.0, 8)


class ErrorBudgetTests(unittest.TestCase):
    def test_offset_term_scales_with_full_scale(self):
        error = channel_error_a(4.0, 10.0, 8, 0.01, 0.005)
        self.assertAlmostEqual(error["offset_a"], 0.05, places=12)

    def test_gain_term_scales_with_the_reading(self):
        error = channel_error_a(4.0, 10.0, 8, 0.01, 0.005)
        self.assertAlmostEqual(error["gain_a"], 0.04, places=12)

    def test_quantisation_term_is_half_a_step(self):
        error = channel_error_a(4.0, 10.0, 8, 0.01, 0.005)
        self.assertAlmostEqual(error["quantisation_a"], 0.5 * 10.0 / 255.0, places=12)

    def test_total_is_the_worst_case_sum(self):
        error = channel_error_a(4.0, 10.0, 8, 0.01, 0.005)
        expected = error["offset_a"] + error["gain_a"] + error["quantisation_a"]
        self.assertAlmostEqual(error["total_a"], expected, places=12)

    def test_offset_dominates_at_a_small_reading(self):
        error = channel_error_a(0.0, 10.0, 12, 0.01, 0.005)
        self.assertAlmostEqual(error["gain_a"], 0.0, places=12)
        self.assertGreater(error["offset_a"], error["quantisation_a"])

    def test_reading_exactly_at_full_scale_is_allowed(self):
        error = channel_error_a(10.0, 10.0, 8, 0.01, 0.005)
        self.assertAlmostEqual(error["gain_a"], 0.1, places=12)

    def test_reading_above_full_scale_rejected(self):
        with self.assertRaises(ValueError):
            channel_error_a(12.0, 10.0, 8, 0.01, 0.005)

    def test_negative_gain_error_rejected(self):
        with self.assertRaises(ValueError):
            channel_error_a(4.0, 10.0, 8, -0.01, 0.005)


class RangeTests(unittest.TestCase):
    def test_required_full_scale_adds_the_headroom(self):
        self.assertAlmostEqual(required_full_scale_a(8.0, 0.20), 9.6, places=9)

    def test_default_headroom_is_applied(self):
        self.assertAlmostEqual(
            required_full_scale_a(8.0),
            8.0 * (1.0 + DEFAULT_RANGE_HEADROOM_FRACTION),
            places=12,
        )

    def test_zero_headroom_is_allowed(self):
        self.assertAlmostEqual(required_full_scale_a(8.0, 0.0), 8.0, places=12)

    def test_zero_limitation_current_rejected(self):
        with self.assertRaises(ValueError):
            required_full_scale_a(0.0, 0.20)


class ChannelGradeTests(unittest.TestCase):
    def test_healthy_channel_is_adequate(self):
        graded = assess_channel(GOOD_CHANNEL)
        self.assertEqual(graded["status"], CHANNEL_ADEQUATE)
        self.assertEqual(graded["findings"], [])

    def test_full_scale_exactly_on_the_requirement_still_passes(self):
        needed = required_full_scale_a(8.0, 0.20)
        graded = assess_channel(_channel(full_scale_a=needed))
        self.assertAlmostEqual(graded["full_scale_a"], needed, places=12)
        self.assertTrue(graded["range_adequate"])

    def test_short_range_is_reported(self):
        graded = assess_channel(_channel(full_scale_a=8.0))
        self.assertFalse(graded["range_adequate"])
        self.assertEqual(graded["status"], CHANNEL_INADEQUATE)
        self.assertTrue(any("pins before" in f for f in graded["findings"]))

    def test_coarse_converter_is_reported(self):
        graded = assess_channel(_channel(resolution_bits=5))
        self.assertFalse(graded["resolution_adequate"])
        self.assertTrue(any("quantisation step" in f for f in graded["findings"]))

    def test_resolution_exactly_on_the_requirement_still_passes(self):
        step = quantisation_step_a(10.0, 8)
        graded = assess_channel(_channel(required_resolution_a=step))
        self.assertAlmostEqual(graded["quantisation_step_a"], step, places=12)
        self.assertTrue(graded["resolution_adequate"])

    def test_accuracy_exactly_on_the_requirement_still_passes(self):
        error = channel_error_a(4.0, 10.0, 8, 0.01, 0.005)
        graded = assess_channel(_channel(required_accuracy_a=error["total_a"]))
        self.assertAlmostEqual(
            graded["error_a"]["total_a"], error["total_a"], places=12
        )
        self.assertTrue(graded["accuracy_adequate"])

    def test_loose_error_budget_is_reported(self):
        graded = assess_channel(_channel(gain_error_fraction=0.10))
        self.assertFalse(graded["accuracy_adequate"])
        self.assertTrue(any("worst-case error" in f for f in graded["findings"]))

    def test_a_summing_channel_reports_no_limiter_individually(self):
        graded = assess_channel(_channel(limiters_served=3))
        self.assertFalse(graded["dedicated"])
        self.assertEqual(graded["status"], CHANNEL_INADEQUATE)
        self.assertTrue(any("sums 3 limiters" in f for f in graded["findings"]))

    def test_zero_limiters_served_rejected(self):
        with self.assertRaises(ValueError):
            assess_channel(_channel(limiters_served=0))

    def test_non_mapping_channel_rejected(self):
        with self.assertRaises(ValueError):
            assess_channel("limiter-1")

    def test_missing_accuracy_requirement_rejected(self):
        channel = _channel()
        del channel["required_accuracy_a"]
        with self.assertRaises(ValueError):
            assess_channel(channel)


class CoverageTests(unittest.TestCase):
    def test_every_limiter_with_a_channel_is_complete(self):
        coverage = telemetry_coverage(GOOD_CASE["limiters"])
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["limiter_count"], 2)
        self.assertEqual(coverage["uncovered"], [])

    def test_a_limiter_without_a_channel_is_uncovered(self):
        limiters = copy.deepcopy(GOOD_CASE["limiters"])
        limiters[1]["channel"] = None
        coverage = telemetry_coverage(limiters)
        self.assertFalse(coverage["complete"])
        self.assertEqual(coverage["uncovered"], ["limiter-2"])

    def test_empty_limiter_list_rejected(self):
        with self.assertRaises(ValueError):
            telemetry_coverage([])

    def test_duplicate_limiter_id_rejected(self):
        limiters = copy.deepcopy(GOOD_CASE["limiters"])
        limiters[1]["limiter_id"] = "limiter-1"
        with self.assertRaises(ValueError):
            telemetry_coverage(limiters)

    def test_limiter_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            telemetry_coverage([{"channel": None}])


class ProvisionTests(unittest.TestCase):
    def test_fully_covered_bus_is_adequate(self):
        result = assess_current_telemetry_provision(GOOD_CASE)
        self.assertEqual(result["verdict"], VERDICT_ADEQUATE)
        self.assertTrue(result["adequate"])
        self.assertEqual(result["findings"], [])

    def test_uncovered_limiter_fails_the_provision(self):
        case = copy.deepcopy(GOOD_CASE)
        case["limiters"][1]["channel"] = None
        result = assess_current_telemetry_provision(case)
        self.assertEqual(result["verdict"], VERDICT_INADEQUATE)
        self.assertTrue(
            any("no channel reporting it" in f for f in result["findings"])
        )

    def test_one_weak_channel_fails_the_whole_provision(self):
        case = copy.deepcopy(GOOD_CASE)
        case["limiters"][1]["channel"]["full_scale_a"] = 8.0
        result = assess_current_telemetry_provision(case)
        self.assertEqual(result["verdict"], VERDICT_INADEQUATE)
        self.assertEqual(result["adequate_channel_count"], 1)

    def test_findings_name_the_limiter(self):
        case = copy.deepcopy(GOOD_CASE)
        case["limiters"][1]["channel"]["resolution_bits"] = 4
        result = assess_current_telemetry_provision(case)
        self.assertTrue(
            any(f.startswith("limiter limiter-2:") for f in result["findings"])
        )

    def test_channel_inherits_the_limiter_id(self):
        case = copy.deepcopy(GOOD_CASE)
        del case["limiters"][0]["channel"]["limiter_id"]
        result = assess_current_telemetry_provision(case)
        self.assertEqual(result["channels"][0]["limiter_id"], "limiter-1")

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_current_telemetry_provision("two limiters")

    def test_result_is_deterministic(self):
        first = assess_current_telemetry_provision(GOOD_CASE)
        second = assess_current_telemetry_provision(GOOD_CASE)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main(verbosity=1)
