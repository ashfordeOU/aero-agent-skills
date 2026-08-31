#!/usr/bin/env python3
"""Gate 3 contract test: limit cycle oscillation.

Exercises scripts/limit_cycle_oscillation.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the log
decrement is delta = (1/n) * ln(A_0 / A_n); the damping ratio is
zeta = delta / sqrt(4*pi^2 + delta^2); the amplitude growth rate is
the linear least squares slope of amplitude versus time; the LCO
amplitude margin is (A_limit - A) / A_limit; the LCO verdict combines
the airspeed band, the amplitude band, and the damping trend
(sustained LCO = amplitude stabilizes at a fixed airspeed, clearance
requires margin to the limit amplitude); freeplay risk is a
qualitative flag. Invalid inputs raise ValueError.

Hand-computed values:
- log_decrement([10.0, 8.0]) = ln(1.25) = 0.22314.
- log_decrement([10.0, 1.0]) = ln(10) = 2.302585.
- log_decrement([100, 50, 25], cycles=2) = ln(4)/2 = 0.693147.
- zeta(0) = 0; zeta(1.0) = 1/sqrt(4*pi^2 + 1) = 0.15718;
  zeta(100) = 100/sqrt(4*pi^2 + 10000) = 0.99803;
  delta = 2*pi*0.02 -> zeta ~ 0.02 (small-delta limit).
- zeta(log_decrement([10.0, 8.0])) = 0.22314/sqrt(4*pi^2 + 0.04979)
  = 0.03549.
- growth rate of the perfect lines [0,1,2,3,4] over [0,1,2,3,4] is
  1.0 m/s; [0,0.5,1,1.5,2] is 0.5; [4,3,2,1,0] is -1.0; the parabola
  (0,0),(1,1),(4,4),(9,9) is 1.0 (x = y).
- margin (4,5) = 0.2; (5,5) = 0.0; (6,5) = -0.2; (0,5) = 1.0.
- verdict: speed 90 vs limit 100, amp 4 vs limit 5, slope 0 ->
  below-limit, margin 0.2, stable, sustained_lco True, CLEAR;
  slope 0.05 (tol 0.01) -> growing, NOT-CLEAR; amp 6 -> NOT-CLEAR;
  speed 105 -> above-limit, NOT-CLEAR; amp 4.75 with required margin
  0.10 -> MARGINAL; slope -0.02 -> decaying, CLEAR.
- freeplay 1.5 deg -> high; 0.5 -> low; 1.0 -> high (boundary).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import limit_cycle_oscillation as lco  # noqa: E402


class LogDecrementTests(unittest.TestCase):
    def test_log_decrement_single_cycle(self):
        self.assertAlmostEqual(lco.log_decrement([10.0, 8.0]), 0.22314, places=5)

    def test_log_decrement_full_decay(self):
        self.assertAlmostEqual(lco.log_decrement([10.0, 1.0]), 2.302585, places=5)

    def test_log_decrement_over_two_cycles(self):
        self.assertAlmostEqual(
            lco.log_decrement([100.0, 50.0, 25.0], cycles=2), 0.693147, places=5
        )

    def test_log_decrement_uses_last_sample_when_record_short(self):
        self.assertAlmostEqual(
            lco.log_decrement([10.0, 5.0, 2.5], cycles=5),
            math.log(10.0 / 2.5) / 5.0,
            places=5,
        )

    def test_log_decrement_rejects_single_amplitude(self):
        with self.assertRaises(ValueError):
            lco.log_decrement([5.0])

    def test_log_decrement_rejects_zero_amplitude(self):
        with self.assertRaises(ValueError):
            lco.log_decrement([5.0, 0.0])

    def test_log_decrement_rejects_negative_amplitude(self):
        with self.assertRaises(ValueError):
            lco.log_decrement([5.0, -1.0])

    def test_log_decrement_rejects_zero_cycles(self):
        with self.assertRaises(ValueError):
            lco.log_decrement([10.0, 8.0], cycles=0)


class DampingRatioTests(unittest.TestCase):
    def test_zero_decrement_undamped(self):
        self.assertEqual(lco.damping_ratio_from_log_decrement(0.0), 0.0)

    def test_unit_decrement_reference_value(self):
        # zeta = 1 / sqrt(4*pi^2 + 1) = 0.15718
        self.assertAlmostEqual(
            lco.damping_ratio_from_log_decrement(1.0), 0.15718, places=5
        )

    def test_large_decrement_approaches_one(self):
        # zeta = 100 / sqrt(4*pi^2 + 10000) = 0.99803
        self.assertAlmostEqual(
            lco.damping_ratio_from_log_decrement(100.0), 0.99803, places=5
        )

    def test_small_decrement_matches_delta_over_two_pi(self):
        # delta = 2*pi*0.02 -> zeta ~ 0.02 in the small-delta limit
        delta = 2.0 * math.pi * 0.02
        self.assertAlmostEqual(
            lco.damping_ratio_from_log_decrement(delta), 0.02, places=4
        )

    def test_damping_from_decaying_record(self):
        # log decrement of 10 -> 8 mm is 0.22314, zeta = 0.03549
        delta = lco.log_decrement([10.0, 8.0])
        self.assertAlmostEqual(
            lco.damping_ratio_from_log_decrement(delta), 0.03549, places=5
        )

    def test_negative_decrement_rejected(self):
        with self.assertRaises(ValueError):
            lco.damping_ratio_from_log_decrement(-0.5)


class AmplitudeGrowthRateTests(unittest.TestCase):
    def test_linear_growth_slope_one(self):
        self.assertAlmostEqual(
            lco.amplitude_growth_rate([0, 1, 2, 3, 4], [0, 1, 2, 3, 4]), 1.0
        )

    def test_linear_growth_slope_half(self):
        self.assertAlmostEqual(
            lco.amplitude_growth_rate([0, 0.5, 1.0, 1.5, 2.0], [0, 1, 2, 3, 4]),
            0.5,
        )

    def test_decaying_trend_negative_slope(self):
        self.assertAlmostEqual(
            lco.amplitude_growth_rate([4, 3, 2, 1, 0], [0, 1, 2, 3, 4]), -1.0
        )

    def test_nonuniform_times(self):
        # x = y over non-uniform times still fits slope 1.0
        self.assertAlmostEqual(
            lco.amplitude_growth_rate([0, 1, 4, 9], [0, 1, 4, 9]), 1.0
        )

    def test_length_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            lco.amplitude_growth_rate([1.0, 2.0], [0.0, 1.0, 2.0])

    def test_single_point_rejected(self):
        with self.assertRaises(ValueError):
            lco.amplitude_growth_rate([1.0], [0.0])

    def test_constant_times_rejected(self):
        with self.assertRaises(ValueError):
            lco.amplitude_growth_rate([1.0, 2.0, 3.0], [5.0, 5.0, 5.0])


class AmplitudeMarginTests(unittest.TestCase):
    def test_margin_below_limit(self):
        self.assertAlmostEqual(lco.lco_amplitude_margin(4.0, 5.0), 0.2)

    def test_margin_at_limit_is_zero(self):
        self.assertAlmostEqual(lco.lco_amplitude_margin(5.0, 5.0), 0.0)

    def test_margin_above_limit_is_negative(self):
        self.assertAlmostEqual(lco.lco_amplitude_margin(6.0, 5.0), -0.2)

    def test_zero_amplitude_full_margin(self):
        self.assertAlmostEqual(lco.lco_amplitude_margin(0.0, 5.0), 1.0)

    def test_nonpositive_limit_rejected(self):
        with self.assertRaises(ValueError):
            lco.lco_amplitude_margin(4.0, 0.0)

    def test_negative_amplitude_rejected(self):
        with self.assertRaises(ValueError):
            lco.lco_amplitude_margin(-1.0, 5.0)


class LcoVerdictTests(unittest.TestCase):
    def test_sustained_lco_cleared_with_margin(self):
        v = lco.lco_verdict(90.0, 100.0, 4.0, 5.0, 0.0)
        self.assertEqual(v["speed_band"], "below-limit")
        self.assertAlmostEqual(v["amplitude_margin"], 0.2)
        self.assertEqual(v["trend"], "stable")
        self.assertTrue(v["sustained_lco"])
        self.assertEqual(v["clearance"], "CLEAR")

    def test_growing_trend_not_clear(self):
        v = lco.lco_verdict(90.0, 100.0, 4.0, 5.0, 0.05, slope_tolerance=0.01)
        self.assertEqual(v["trend"], "growing")
        self.assertFalse(v["sustained_lco"])
        self.assertEqual(v["clearance"], "NOT-CLEAR")

    def test_amplitude_above_limit_not_clear(self):
        v = lco.lco_verdict(90.0, 100.0, 6.0, 5.0, 0.0)
        self.assertLess(v["amplitude_margin"], 0.0)
        self.assertFalse(v["sustained_lco"])
        self.assertEqual(v["clearance"], "NOT-CLEAR")

    def test_airspeed_above_limit_not_clear(self):
        v = lco.lco_verdict(105.0, 100.0, 4.0, 5.0, -0.01)
        self.assertEqual(v["speed_band"], "above-limit")
        self.assertEqual(v["trend"], "decaying")
        self.assertEqual(v["clearance"], "NOT-CLEAR")

    def test_margin_below_required_is_marginal(self):
        v = lco.lco_verdict(90.0, 100.0, 4.75, 5.0, 0.0, required_margin=0.10)
        self.assertAlmostEqual(v["amplitude_margin"], 0.05)
        self.assertTrue(v["sustained_lco"])
        self.assertEqual(v["clearance"], "MARGINAL")

    def test_decaying_trend_cleared(self):
        v = lco.lco_verdict(90.0, 100.0, 4.0, 5.0, -0.02, slope_tolerance=0.01)
        self.assertEqual(v["trend"], "decaying")
        self.assertFalse(v["sustained_lco"])
        self.assertEqual(v["clearance"], "CLEAR")

    def test_at_limit_speed_boundary(self):
        v = lco.lco_verdict(100.0, 100.0, 4.0, 5.0, 0.0)
        self.assertEqual(v["speed_band"], "at-limit")
        self.assertEqual(v["clearance"], "CLEAR")

    def test_slope_at_tolerance_is_stable(self):
        v = lco.lco_verdict(90.0, 100.0, 4.0, 5.0, 0.01, slope_tolerance=0.01)
        self.assertEqual(v["trend"], "stable")
        self.assertTrue(v["sustained_lco"])

    def test_nonpositive_limit_speed_rejected(self):
        with self.assertRaises(ValueError):
            lco.lco_verdict(90.0, 0.0, 4.0, 5.0, 0.0)

    def test_negative_airspeed_rejected(self):
        with self.assertRaises(ValueError):
            lco.lco_verdict(-10.0, 100.0, 4.0, 5.0, 0.0)


class FreeplayTests(unittest.TestCase):
    def test_freeplay_above_threshold_high_risk(self):
        self.assertEqual(lco.freeplay_lco_onset_risk(1.5), "high")

    def test_freeplay_below_threshold_low_risk(self):
        self.assertEqual(lco.freeplay_lco_onset_risk(0.5), "low")

    def test_freeplay_at_threshold_is_high(self):
        self.assertEqual(lco.freeplay_lco_onset_risk(1.0), "high")

    def test_freeplay_negative_rejected(self):
        with self.assertRaises(ValueError):
            lco.freeplay_lco_onset_risk(-0.1)

    def test_nonpositive_threshold_rejected(self):
        with self.assertRaises(ValueError):
            lco.freeplay_lco_onset_risk(0.5, threshold_deg=0.0)


if __name__ == "__main__":
    unittest.main()
