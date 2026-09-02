#!/usr/bin/env python3
"""Gate 3 contract test: ground vibration testing.

Exercises scripts/ground_vibration_testing_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - modal damping
comes from the half-power bandwidth zeta = (f2 - f1) / (2 * fn); an
FRF peak at or above the threshold is a mode candidate; the FFT
frequency resolution is df = sample_rate / n_samples; the detected
mode count must match the pre-test expectation; reciprocity requires
the relative difference between H_ij and H_ji within tolerance; a
measured FRF passes when coherence >= 0.9. Invalid inputs raise
ValueError.

Hand-computed values:
- f1 = 9.8, f2 = 10.2, fn = 10.0: zeta = 0.4 / 20 = 0.02.
- f1 = 9.5, f2 = 10.5, fn = 10.0: zeta = 1.0 / 20 = 0.05.
- f1 = 19.0, f2 = 21.0, fn = 20.0: zeta = 2.0 / 40 = 0.05.
- peak 0.45 vs threshold 0.30 -> pass; 0.25 -> fail; 0.30 -> pass
  (boundary).
- fs = 4096, N = 4096 -> df = 1.0 Hz; fs = 2048, N = 1024 -> 2.0 Hz;
  fs = 10000, N = 2000 -> 5.0 Hz.
- peaks [9.8, 21.3, 33.1] vs expected 3 -> pass; 2 peaks vs 3 -> fail.
- h12 = 2.0, h21 = 2.1: rel = 0.1 / 2.1 = 0.04762 <= 0.05 -> pass;
  h21 = 2.2: rel = 0.2 / 2.2 = 0.09091 > 0.05 -> fail.
- coherence 0.95 -> pass; 0.90 -> pass (boundary); 0.85 -> fail.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ground_vibration_testing_logic as gvt  # noqa: E402


class HalfPowerDampingTest(unittest.TestCase):
    def test_analytic_two_percent(self):
        # zeta = 0.4 / 20 = 0.02
        self.assertAlmostEqual(gvt.half_power_damping(9.8, 10.2, 10.0), 0.02)

    def test_analytic_five_percent(self):
        # zeta = 1.0 / 20 = 0.05
        self.assertAlmostEqual(gvt.half_power_damping(9.5, 10.5, 10.0), 0.05)

    def test_analytic_higher_mode(self):
        # zeta = 2.0 / 40 = 0.05
        self.assertAlmostEqual(gvt.half_power_damping(19.0, 21.0, 20.0), 0.05)

    def test_analytic_low_damping(self):
        # zeta = 0.2 / 40 = 0.005
        self.assertAlmostEqual(gvt.half_power_damping(19.9, 20.1, 20.0), 0.005)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gvt.half_power_damping(0, 10.2, 10.0)
        with self.assertRaises(ValueError):
            gvt.half_power_damping(9.8, 10.2, -10.0)
        with self.assertRaises(ValueError):
            gvt.half_power_damping(10.5, 11.0, 10.0)  # f1 not below fn
        with self.assertRaises(ValueError):
            gvt.half_power_damping(9.8, 9.9, 10.0)  # f2 not above fn


class PeakPickVerdictTest(unittest.TestCase):
    def test_analytic_peak_above_threshold(self):
        # 0.45 >= 0.30 -> pass
        out = gvt.peak_pick_verdict(0.45, 0.30)
        self.assertTrue(out["pass"])
        self.assertAlmostEqual(out["peak"], 0.45)

    def test_analytic_peak_below_threshold(self):
        # 0.25 < 0.30 -> fail (noise)
        out = gvt.peak_pick_verdict(0.25, 0.30)
        self.assertFalse(out["pass"])

    def test_analytic_boundary(self):
        # 0.30 == 0.30 -> pass (>=)
        out = gvt.peak_pick_verdict(0.30, 0.30)
        self.assertTrue(out["pass"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gvt.peak_pick_verdict(0.45, 0)
        with self.assertRaises(ValueError):
            gvt.peak_pick_verdict(0.45, -0.1)
        with self.assertRaises(ValueError):
            gvt.peak_pick_verdict(-0.2, 0.30)


class FrequencyResolutionTest(unittest.TestCase):
    def test_analytic_one_hertz(self):
        # 4096 / 4096 = 1.0 Hz
        self.assertAlmostEqual(gvt.frequency_resolution(4096, 4096), 1.0)

    def test_analytic_two_hertz(self):
        # 2048 / 1024 = 2.0 Hz
        self.assertAlmostEqual(gvt.frequency_resolution(2048, 1024), 2.0)

    def test_analytic_five_hertz(self):
        # 10000 / 2000 = 5.0 Hz
        self.assertAlmostEqual(gvt.frequency_resolution(10000, 2000), 5.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gvt.frequency_resolution(0, 1024)
        with self.assertRaises(ValueError):
            gvt.frequency_resolution(2048, 1)
        with self.assertRaises(ValueError):
            gvt.frequency_resolution(2048, 2.5)
        with self.assertRaises(ValueError):
            gvt.frequency_resolution(-1000, 1024)


class ModeCountVerdictTest(unittest.TestCase):
    def test_analytic_match(self):
        # three peaks, three modes expected -> pass
        out = gvt.mode_count_verdict([9.8, 21.3, 33.1], 3)
        self.assertTrue(out["pass"])
        self.assertEqual(out["found"], 3)
        self.assertEqual(out["verdict"], "mode count matches")

    def test_analytic_mismatch(self):
        # two peaks, three modes expected -> fail
        out = gvt.mode_count_verdict([9.8, 21.3], 3)
        self.assertFalse(out["pass"])
        self.assertEqual(out["found"], 2)
        self.assertEqual(out["verdict"], "mode count mismatch")

    def test_analytic_empty_band(self):
        # no peaks, no modes expected in the band -> pass
        out = gvt.mode_count_verdict([], 0)
        self.assertTrue(out["pass"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gvt.mode_count_verdict([9.8], -1)
        with self.assertRaises(ValueError):
            gvt.mode_count_verdict([9.8, -5.0], 2)


class ReciprocityCheckTest(unittest.TestCase):
    def test_analytic_within_tolerance(self):
        # rel = 0.1 / 2.1 = 0.04762 <= 0.05 -> pass
        out = gvt.reciprocity_check(2.0, 2.1)
        self.assertTrue(out["pass"])
        self.assertAlmostEqual(out["rel_diff"], 0.1 / 2.1, places=5)

    def test_analytic_outside_tolerance(self):
        # rel = 0.2 / 2.2 = 0.09091 > 0.05 -> fail
        out = gvt.reciprocity_check(2.0, 2.2)
        self.assertFalse(out["pass"])
        self.assertAlmostEqual(out["rel_diff"], 0.2 / 2.2, places=5)

    def test_analytic_identical(self):
        # rel = 0 -> pass
        out = gvt.reciprocity_check(0.5, 0.5)
        self.assertTrue(out["pass"])
        self.assertAlmostEqual(out["rel_diff"], 0.0)

    def test_analytic_both_zero(self):
        # no response at either location -> trivial pass
        out = gvt.reciprocity_check(0.0, 0.0)
        self.assertTrue(out["pass"])

    def test_analytic_large_mismatch(self):
        # rel = 0.5 / 1.0 = 0.5 > 0.05 -> fail
        out = gvt.reciprocity_check(0.5, 1.0)
        self.assertFalse(out["pass"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gvt.reciprocity_check(2.0, 2.1, tolerance=0)
        with self.assertRaises(ValueError):
            gvt.reciprocity_check(2.0, 2.1, tolerance=-0.05)


class CoherenceVerdictTest(unittest.TestCase):
    def test_analytic_high_coherence(self):
        # 0.95 >= 0.90 -> pass
        out = gvt.coherence_verdict(0.95)
        self.assertTrue(out["pass"])

    def test_analytic_boundary(self):
        # 0.90 == 0.90 -> pass (>=)
        out = gvt.coherence_verdict(0.90)
        self.assertTrue(out["pass"])

    def test_analytic_low_coherence(self):
        # 0.85 < 0.90 -> fail (noise or nonlinearity)
        out = gvt.coherence_verdict(0.85)
        self.assertFalse(out["pass"])

    def test_analytic_stricter_minimum(self):
        # 0.95 < 0.98 -> fail under the stricter minimum
        out = gvt.coherence_verdict(0.95, min_coherence=0.98)
        self.assertFalse(out["pass"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gvt.coherence_verdict(1.5)
        with self.assertRaises(ValueError):
            gvt.coherence_verdict(-0.2)
        with self.assertRaises(ValueError):
            gvt.coherence_verdict(0.95, min_coherence=0)
        with self.assertRaises(ValueError):
            gvt.coherence_verdict(0.95, min_coherence=1.2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
