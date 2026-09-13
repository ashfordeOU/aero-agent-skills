#!/usr/bin/env python3
"""Gate 3 contract test for e2001-detection-rise-time.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2001_detection_rise_time.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2001_detection_rise_time_logic import (  # noqa: E402
    RISE_TIME_BANDWIDTH_PRODUCT,
    bandwidth_from_rise_time,
    baseline_recovery_s,
    categorize_detection_speed,
    chain_rise_time_s,
    dominant_stage_index,
    evaluate_detection_chain,
    inter_pulse_gap_s,
    meets_speed_requirement,
    minimum_sample_rate_hz,
    observation_window_s,
    required_rise_time_s,
    rise_time_from_bandwidth,
    shortest_supported_pulse_width_s,
    window_fraction,
)


class TestBandwidthConversion(unittest.TestCase):
    def test_one_gigahertz_stage(self):
        self.assertAlmostEqual(
            rise_time_from_bandwidth(1.0e9), RISE_TIME_BANDWIDTH_PRODUCT * 1e-9, places=18
        )

    def test_round_trip(self):
        rise = rise_time_from_bandwidth(2.5e8)
        self.assertAlmostEqual(bandwidth_from_rise_time(rise) / 2.5e8, 1.0, places=12)

    def test_wider_bandwidth_is_faster(self):
        self.assertLess(rise_time_from_bandwidth(1e9), rise_time_from_bandwidth(1e8))

    def test_zero_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            rise_time_from_bandwidth(0.0)

    def test_negative_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            rise_time_from_bandwidth(1e9, coefficient=-0.35)

    def test_non_numeric_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            rise_time_from_bandwidth("1e9")

    def test_zero_rise_time_rejected(self):
        with self.assertRaises(ValueError):
            bandwidth_from_rise_time(0.0)


class TestChainCombination(unittest.TestCase):
    def test_three_four_five_stage_pair(self):
        self.assertAlmostEqual(chain_rise_time_s([3e-9, 4e-9]) / 5e-9, 1.0, places=14)

    def test_two_equal_stages_scale_by_root_two(self):
        chain = chain_rise_time_s([1e-8, 1e-8])
        self.assertAlmostEqual(chain / 1e-8, math.sqrt(2.0), places=12)

    def test_single_stage_is_itself(self):
        self.assertAlmostEqual(chain_rise_time_s([7e-9]), 7e-9, places=18)

    def test_root_sum_square_beats_arithmetic_sum(self):
        stages = [2e-9, 3e-9, 4e-9]
        self.assertLess(chain_rise_time_s(stages), sum(stages))

    def test_dominant_stage_sets_the_chain(self):
        chain = chain_rise_time_s([1e-10, 1e-10, 5e-9])
        self.assertLess(abs(chain - 5e-9) / 5e-9, 1e-3)

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            chain_rise_time_s([])

    def test_non_sequence_chain_rejected(self):
        with self.assertRaises(ValueError):
            chain_rise_time_s(5e-9)

    def test_negative_stage_rejected(self):
        with self.assertRaises(ValueError):
            chain_rise_time_s([3e-9, -1e-9])

    def test_all_zero_stages_rejected(self):
        with self.assertRaises(ValueError):
            chain_rise_time_s([0.0, 0.0])

    def test_dominant_stage_index(self):
        self.assertEqual(dominant_stage_index([1e-9, 8e-9, 2e-9]), 1)

    def test_dominant_stage_tie_takes_first(self):
        self.assertEqual(dominant_stage_index([4e-9, 4e-9]), 0)

    def test_dominant_stage_validates_input(self):
        with self.assertRaises(ValueError):
            dominant_stage_index([])


class TestSpeedRequirement(unittest.TestCase):
    def test_required_rise_time(self):
        self.assertAlmostEqual(required_rise_time_s(1e-6, 0.1), 1e-7, places=18)

    def test_speed_ratio_above_one_rejected(self):
        with self.assertRaises(ValueError):
            required_rise_time_s(1e-6, 1.5)

    def test_zero_speed_ratio_rejected(self):
        with self.assertRaises(ValueError):
            required_rise_time_s(1e-6, 0.0)

    def test_shortest_supported_pulse(self):
        self.assertAlmostEqual(
            shortest_supported_pulse_width_s(5e-9, 0.1) / 5e-8, 1.0, places=14
        )

    def test_exact_boundary_survives_root_sum_square_error(self):
        chain = chain_rise_time_s([3e-9, 4e-9])
        required = required_rise_time_s(50e-9, 0.1)
        self.assertLess(abs(chain - required), 1e-20)
        self.assertTrue(meets_speed_requirement(chain, 50e-9, 0.1))

    def test_one_percent_too_slow_fails(self):
        self.assertFalse(meets_speed_requirement(1.01e-7, 1e-6, 0.1))

    def test_comfortably_fast_passes(self):
        self.assertTrue(meets_speed_requirement(1e-8, 1e-6, 0.1))

    def test_zero_chain_rise_rejected(self):
        with self.assertRaises(ValueError):
            meets_speed_requirement(0.0, 1e-6)


class TestSpeedCategory(unittest.TestCase):
    def test_prompt_chain(self):
        self.assertEqual(categorize_detection_speed(5e-8, 1e-6), "prompt")

    def test_exactly_at_the_ratio_is_prompt(self):
        self.assertEqual(categorize_detection_speed(1e-7, 1e-6), "prompt")

    def test_marginal_chain(self):
        self.assertEqual(categorize_detection_speed(2e-7, 1e-6), "marginal")

    def test_too_slow_chain(self):
        self.assertEqual(categorize_detection_speed(5e-7, 1e-6), "too-slow")

    def test_negative_pulse_width_rejected(self):
        with self.assertRaises(ValueError):
            categorize_detection_speed(1e-7, -1e-6)


class TestObservationWindow(unittest.TestCase):
    def test_window_subtracts_blanking_and_edge(self):
        self.assertAlmostEqual(
            observation_window_s(1e-6, 5e-8, 1e-7), 8.5e-7, places=16
        )

    def test_window_floors_at_zero(self):
        self.assertAlmostEqual(observation_window_s(1e-7, 9e-8, 5e-8), 0.0, places=18)

    def test_window_fraction(self):
        self.assertAlmostEqual(window_fraction(1e-6, 5e-8, 1e-7), 0.85, places=12)

    def test_blanking_longer_than_pulse_rejected(self):
        with self.assertRaises(ValueError):
            observation_window_s(1e-6, 5e-8, 2e-6)

    def test_negative_blanking_rejected(self):
        with self.assertRaises(ValueError):
            observation_window_s(1e-6, 5e-8, -1e-9)

    def test_zero_pulse_rejected(self):
        with self.assertRaises(ValueError):
            observation_window_s(0.0, 5e-8, 0.0)


class TestSamplingAndRecovery(unittest.TestCase):
    def test_minimum_sample_rate(self):
        self.assertAlmostEqual(minimum_sample_rate_hz(5e-9, 5.0) / 1e9, 1.0, places=12)

    def test_faster_edge_needs_faster_digitiser(self):
        self.assertGreater(minimum_sample_rate_hz(1e-9), minimum_sample_rate_hz(1e-8))

    def test_fewer_than_two_samples_rejected(self):
        with self.assertRaises(ValueError):
            minimum_sample_rate_hz(5e-9, 1.0)

    def test_zero_rise_rejected_for_sample_rate(self):
        with self.assertRaises(ValueError):
            minimum_sample_rate_hz(0.0)

    def test_half_duty_gap_equals_pulse(self):
        self.assertAlmostEqual(inter_pulse_gap_s(1e-6, 0.5) / 1e-6, 1.0, places=12)

    def test_continuous_drive_leaves_no_gap(self):
        self.assertAlmostEqual(inter_pulse_gap_s(1e-6, 1.0), 0.0, places=18)

    def test_zero_duty_rejected(self):
        with self.assertRaises(ValueError):
            inter_pulse_gap_s(1e-6, 0.0)

    def test_duty_above_one_rejected(self):
        with self.assertRaises(ValueError):
            inter_pulse_gap_s(1e-6, 1.2)

    def test_baseline_recovery_scales_with_rise(self):
        self.assertAlmostEqual(baseline_recovery_s(5e-9, 3.0) / 1.5e-8, 1.0, places=12)

    def test_zero_recovery_factor_rejected(self):
        with self.assertRaises(ValueError):
            baseline_recovery_s(5e-9, 0.0)


class TestChainEvaluation(unittest.TestCase):
    def base_spec(self):
        return {
            "stage_rise_times_s": [3e-9, 4e-9],
            "pulse_width_s": 1e-6,
            "speed_ratio": 0.1,
        }

    def test_prompt_chain_is_compliant(self):
        result = evaluate_detection_chain(self.base_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["speed_category"], "prompt")
        self.assertEqual(result["dominant_stage_index"], 1)
        self.assertAlmostEqual(
            result["shortest_supported_pulse_width_s"] / 5e-8, 1.0, places=12
        )

    def test_bandwidth_stages_match_rise_time_stages(self):
        spec = {
            "stage_bandwidths_hz": [
                RISE_TIME_BANDWIDTH_PRODUCT / 3e-9,
                RISE_TIME_BANDWIDTH_PRODUCT / 4e-9,
            ],
            "pulse_width_s": 1e-6,
        }
        result = evaluate_detection_chain(spec)
        self.assertAlmostEqual(result["chain_rise_time_s"] / 5e-9, 1.0, places=12)
        self.assertTrue(result["compliant"])

    def test_exact_speed_boundary_is_compliant(self):
        spec = self.base_spec()
        spec["pulse_width_s"] = 50e-9
        result = evaluate_detection_chain(spec)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["speed_category"], "prompt")

    def test_slow_chain_flagged(self):
        spec = self.base_spec()
        spec["stage_rise_times_s"] = [4e-7]
        result = evaluate_detection_chain(spec)
        self.assertFalse(result["compliant"])
        self.assertEqual(
            [f["code"] for f in result["findings"]], ["chain-too-slow-for-pulse"]
        )
        self.assertEqual(result["speed_category"], "too-slow")

    def test_blanking_that_eats_the_window_flagged(self):
        spec = self.base_spec()
        spec["blanking_s"] = 9.9e-7
        result = evaluate_detection_chain(spec)
        self.assertIn(
            "observation-window-too-short", [f["code"] for f in result["findings"]]
        )
        self.assertLess(result["window_fraction"], 0.5)

    def test_blanking_longer_than_the_pulse_rejected_by_evaluation(self):
        spec = self.base_spec()
        spec["blanking_s"] = 2e-6
        with self.assertRaises(ValueError):
            evaluate_detection_chain(spec)

    def test_window_driven_to_zero(self):
        spec = self.base_spec()
        spec["stage_rise_times_s"] = [9e-7]
        spec["blanking_s"] = 5e-7
        result = evaluate_detection_chain(spec)
        self.assertAlmostEqual(result["observation_window_s"], 0.0, places=18)
        self.assertIn(
            "observation-window-too-short", [f["code"] for f in result["findings"]]
        )

    def test_under_sampled_edge_flagged(self):
        spec = self.base_spec()
        spec["sample_rate_hz"] = 1e7
        result = evaluate_detection_chain(spec)
        self.assertIn("sample-rate-too-low", [f["code"] for f in result["findings"]])

    def test_adequate_sample_rate_passes(self):
        spec = self.base_spec()
        spec["sample_rate_hz"] = 1e10
        self.assertTrue(evaluate_detection_chain(spec)["compliant"])

    def test_short_gap_flags_baseline_recovery(self):
        spec = self.base_spec()
        spec["stage_rise_times_s"] = [5e-8]
        spec["duty_cycle"] = 0.9
        result = evaluate_detection_chain(spec)
        self.assertEqual(
            [f["code"] for f in result["findings"]], ["baseline-not-recovered"]
        )
        self.assertIsNotNone(result["inter_pulse_gap_s"])

    def test_generous_gap_recovers(self):
        spec = self.base_spec()
        spec["duty_cycle"] = 0.1
        self.assertTrue(evaluate_detection_chain(spec)["compliant"])

    def test_both_stage_forms_rejected(self):
        spec = self.base_spec()
        spec["stage_bandwidths_hz"] = [1e9]
        with self.assertRaises(ValueError):
            evaluate_detection_chain(spec)

    def test_no_stage_form_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_detection_chain({"pulse_width_s": 1e-6})

    def test_missing_pulse_width_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_detection_chain({"stage_rise_times_s": [5e-9]})

    def test_unknown_key_rejected(self):
        spec = self.base_spec()
        spec["chamber_pressure_pa"] = 1e-5
        with self.assertRaises(ValueError):
            evaluate_detection_chain(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_detection_chain([("pulse_width_s", 1e-6)])

    def test_empty_bandwidth_list_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_detection_chain(
                {"stage_bandwidths_hz": [], "pulse_width_s": 1e-6}
            )

    def test_bad_duty_cycle_rejected(self):
        spec = self.base_spec()
        spec["duty_cycle"] = 0.0
        with self.assertRaises(ValueError):
            evaluate_detection_chain(spec)


if __name__ == "__main__":
    unittest.main()
