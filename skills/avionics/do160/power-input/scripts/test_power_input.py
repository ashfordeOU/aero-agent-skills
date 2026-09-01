#!/usr/bin/env python3
"""Gate 3 contract test: DO-160 Section 16 power input (paraphrase).

Exercises scripts/power_input_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - sag depth and surge height
percentages of nominal, frequency deviation and tolerance, steady-state
voltage limits and margins, transient recovery time, transient category
envelope checks, ripple percentage, and emergency range classification;
invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import power_input_logic as pi  # noqa: E402


class SagDepthTest(unittest.TestCase):
    def test_anchor_25_percent(self):
        self.assertAlmostEqual(pi.sag_depth_percent(28.0, 21.0), 25.0, places=6)

    def test_no_sag_is_zero(self):
        self.assertAlmostEqual(pi.sag_depth_percent(28.0, 28.0), 0.0, places=6)

    def test_deeper_sag_gives_larger_depth(self):
        self.assertGreater(
            pi.sag_depth_percent(28.0, 20.0), pi.sag_depth_percent(28.0, 24.0)
        )

    def test_sag_above_nominal_raises(self):
        with self.assertRaises(ValueError):
            pi.sag_depth_percent(28.0, 30.0)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            pi.sag_depth_percent("28", 21.0)
        with self.assertRaises(ValueError):
            pi.sag_depth_percent(28.0, -1.0)
        with self.assertRaises(ValueError):
            pi.sag_depth_percent(0.0, 0.0)


class SurgeHeightTest(unittest.TestCase):
    def test_anchor_15_percent(self):
        self.assertAlmostEqual(pi.surge_height_percent(28.0, 32.2), 15.0, places=6)

    def test_no_surge_is_zero(self):
        self.assertAlmostEqual(pi.surge_height_percent(28.0, 28.0), 0.0, places=6)

    def test_higher_surge_gives_larger_height(self):
        self.assertGreater(
            pi.surge_height_percent(28.0, 34.0), pi.surge_height_percent(28.0, 30.0)
        )

    def test_surge_below_nominal_raises(self):
        with self.assertRaises(ValueError):
            pi.surge_height_percent(28.0, 24.0)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            pi.surge_height_percent(28.0, None)


class FrequencyDeviationTest(unittest.TestCase):
    def test_anchor_12_hz_3_percent(self):
        dev_hz, dev_pct = pi.frequency_deviation(412.0, 400.0)
        self.assertAlmostEqual(dev_hz, 12.0, places=6)
        self.assertAlmostEqual(dev_pct, 3.0, places=6)

    def test_below_nominal_is_negative(self):
        dev_hz, dev_pct = pi.frequency_deviation(385.0, 400.0)
        self.assertAlmostEqual(dev_hz, -15.0, places=6)
        self.assertAlmostEqual(dev_pct, -3.75, places=6)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            pi.frequency_deviation(412.0, 0.0)


class FrequencyToleranceTest(unittest.TestCase):
    def test_anchor_within_tolerance(self):
        self.assertTrue(pi.frequency_within_tolerance(412.0, 400.0, 5.0))

    def test_anchor_outside_tolerance(self):
        self.assertFalse(pi.frequency_within_tolerance(422.0, 400.0, 5.0))

    def test_exact_band_edge_passes(self):
        self.assertTrue(pi.frequency_within_tolerance(420.0, 400.0, 5.0))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            pi.frequency_within_tolerance(412.0, 400.0, -1.0)


class VoltageLimitsTest(unittest.TestCase):
    def test_anchor_within_limits(self):
        self.assertTrue(pi.voltage_within_limits(27.5, 22.0, 29.0))

    def test_anchor_below_limits(self):
        self.assertFalse(pi.voltage_within_limits(21.0, 22.0, 29.0))

    def test_anchor_above_limits(self):
        self.assertFalse(pi.voltage_within_limits(30.0, 22.0, 29.0))

    def test_band_edge_is_inclusive(self):
        self.assertTrue(pi.voltage_within_limits(22.0, 22.0, 29.0))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            pi.voltage_within_limits(27.5, 29.0, 22.0)


class LimitsMarginsTest(unittest.TestCase):
    def test_anchor_margins(self):
        margin_low, margin_high = pi.limits_margins(27.5, 22.0, 29.0)
        self.assertAlmostEqual(margin_low, 5.5, places=6)
        self.assertAlmostEqual(margin_high, 1.5, places=6)

    def test_outside_band_has_negative_margin(self):
        margin_low, _ = pi.limits_margins(20.0, 22.0, 29.0)
        self.assertLess(margin_low, 0.0)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            pi.limits_margins(27.5, 22.0, 22.0)


class TransientRecoveryTest(unittest.TestCase):
    def test_anchor_within_allowable(self):
        self.assertTrue(pi.transient_recovery_ok(60.0, 100.0))

    def test_exceeding_allowable_fails(self):
        self.assertFalse(pi.transient_recovery_ok(120.0, 100.0))

    def test_exact_allowable_passes(self):
        self.assertTrue(pi.transient_recovery_ok(100.0, 100.0))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            pi.transient_recovery_ok(-5.0, 100.0)
        with self.assertRaises(ValueError):
            pi.transient_recovery_ok(60.0, -1.0)


class TransientCheckTest(unittest.TestCase):
    def test_anchor_within_envelope(self):
        ok, dur_margin, depth_margin = pi.transient_check(80.0, 20.0, 100.0, 25.0)
        self.assertTrue(ok)
        self.assertAlmostEqual(dur_margin, 20.0, places=6)
        self.assertAlmostEqual(depth_margin, 5.0, places=6)

    def test_duration_violation_fails(self):
        ok, dur_margin, _ = pi.transient_check(120.0, 20.0, 100.0, 25.0)
        self.assertFalse(ok)
        self.assertLess(dur_margin, 0.0)

    def test_depth_violation_fails(self):
        ok, _, depth_margin = pi.transient_check(80.0, 30.0, 100.0, 25.0)
        self.assertFalse(ok)
        self.assertLess(depth_margin, 0.0)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            pi.transient_check(-1.0, 20.0, 100.0, 25.0)


class RipplePercentTest(unittest.TestCase):
    def test_anchor_ripple(self):
        self.assertAlmostEqual(pi.ripple_percent(29.0, 27.0, 28.0), 3.571428571, places=6)

    def test_no_ripple_is_zero(self):
        self.assertAlmostEqual(pi.ripple_percent(28.0, 28.0, 28.0), 0.0, places=6)

    def test_larger_ripple_gives_larger_percent(self):
        self.assertGreater(
            pi.ripple_percent(30.0, 26.0, 28.0), pi.ripple_percent(29.0, 27.0, 28.0)
        )

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            pi.ripple_percent(26.0, 27.0, 28.0)
        with self.assertRaises(ValueError):
            pi.ripple_percent(29.0, 27.0, 0.0)


class EmergencyRangeTest(unittest.TestCase):
    def test_anchor_emergency_only(self):
        self.assertEqual(
            pi.emergency_range_check(20.5, 22.0, 29.0, 18.0, 32.2), "emergency-only"
        )

    def test_normal_classification(self):
        self.assertEqual(
            pi.emergency_range_check(27.0, 22.0, 29.0, 18.0, 32.2), "normal"
        )

    def test_out_of_range_classification(self):
        self.assertEqual(
            pi.emergency_range_check(15.0, 22.0, 29.0, 18.0, 32.2), "out-of-range"
        )

    def test_emergency_band_must_contain_normal(self):
        with self.assertRaises(ValueError):
            pi.emergency_range_check(27.0, 22.0, 29.0, 24.0, 30.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
