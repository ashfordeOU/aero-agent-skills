#!/usr/bin/env python3
"""Gate 3 contract test: tail volume coefficient sizing.

Exercises scripts/tail_sizing_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - tail volume coefficients
V_h = S_h * L_h / (S_w * cbar) and V_v = S_v * L_v / (S_w * b), the
required tail area for a target volume coefficient, and the verdict
against the typical ranges (V_h 0.5-1.0, V_v 0.04-0.07); invalid
inputs raise ValueError. Units: areas in m^2, arms and reference
lengths in m.

Analytic anchors (hand-computed):
  V_h = 30*14/(120*3.5) = 420/420 = 1.0
  V_v = 22*13/(120*34) = 286/4080 = 0.0700980...
  S_h = 0.7*120*3.5/14 = 294/14 = 21.0 m^2
  S_v = 0.06*120*34/13 = 244.8/13 = 18.830769... m^2
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tail_sizing_logic as tsl  # noqa: E402


class TailVolumeCoefficientTest(unittest.TestCase):
    def test_analytic_horizontal(self):
        # 30*14/(120*3.5) = 420/420 = 1.0
        self.assertAlmostEqual(tsl.tail_volume_coefficient(30.0, 14.0, 120.0, 3.5), 1.0, places=6)

    def test_analytic_vertical(self):
        # 22*13/(120*34) = 286/4080 = 0.0700980...
        self.assertAlmostEqual(tsl.tail_volume_coefficient(22.0, 13.0, 120.0, 34.0), 0.0701, places=4)

    def test_transport_typical_values(self):
        # S_h = 0.7*120*3.5/14 = 21 m^2 -> V_h = 0.7
        v_h = tsl.tail_volume_coefficient(21.0, 14.0, 120.0, 3.5)
        self.assertAlmostEqual(v_h, 0.7, places=6)

    def test_larger_tail_arm_raises_coefficient(self):
        self.assertGreater(
            tsl.tail_volume_coefficient(21.0, 16.0, 120.0, 3.5),
            tsl.tail_volume_coefficient(21.0, 14.0, 120.0, 3.5),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tsl.tail_volume_coefficient(0, 14.0, 120.0, 3.5)
        with self.assertRaises(ValueError):
            tsl.tail_volume_coefficient(-30.0, 14.0, 120.0, 3.5)
        with self.assertRaises(ValueError):
            tsl.tail_volume_coefficient(30.0, 0, 120.0, 3.5)
        with self.assertRaises(ValueError):
            tsl.tail_volume_coefficient(30.0, 14.0, 0, 3.5)
        with self.assertRaises(ValueError):
            tsl.tail_volume_coefficient(30.0, 14.0, 120.0, 0)


class TailAreaRequiredTest(unittest.TestCase):
    def test_analytic_horizontal_area(self):
        # 0.7*120*3.5/14 = 294/14 = 21.0 m^2
        self.assertAlmostEqual(tsl.tail_area_required(0.7, 14.0, 120.0, 3.5), 21.0, places=6)

    def test_analytic_vertical_area(self):
        # 0.06*120*34/13 = 244.8/13 = 18.830769... m^2
        self.assertAlmostEqual(tsl.tail_area_required(0.06, 13.0, 120.0, 34.0), 18.8308, places=4)

    def test_round_trip_with_coefficient(self):
        # S_h = 30, L_h = 14, S_w = 120, cbar = 3.5 -> V_h = 1.0 ->
        # required area must come back to 30 m^2
        v_h = tsl.tail_volume_coefficient(30.0, 14.0, 120.0, 3.5)
        self.assertAlmostEqual(tsl.tail_area_required(v_h, 14.0, 120.0, 3.5), 30.0, places=6)

    def test_longer_arm_needs_less_area(self):
        self.assertLess(
            tsl.tail_area_required(0.7, 16.0, 120.0, 3.5),
            tsl.tail_area_required(0.7, 14.0, 120.0, 3.5),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tsl.tail_area_required(0, 14.0, 120.0, 3.5)
        with self.assertRaises(ValueError):
            tsl.tail_area_required(-0.7, 14.0, 120.0, 3.5)
        with self.assertRaises(ValueError):
            tsl.tail_area_required(0.7, 0, 120.0, 3.5)
        with self.assertRaises(ValueError):
            tsl.tail_area_required(0.7, 14.0, 0, 3.5)
        with self.assertRaises(ValueError):
            tsl.tail_area_required(0.7, 14.0, 120.0, 0)


class VolumeCoefficientVerdictTest(unittest.TestCase):
    def test_transport_pair_is_ok(self):
        result = tsl.volume_coefficient_verdict(0.7, 0.06)
        self.assertTrue(result["h_ok"])
        self.assertTrue(result["v_ok"])
        self.assertEqual(result["verdict"], "both tails within typical ranges")

    def test_boundaries_are_inclusive(self):
        result = tsl.volume_coefficient_verdict(0.5, 0.07)
        self.assertTrue(result["h_ok"])
        self.assertTrue(result["v_ok"])
        result2 = tsl.volume_coefficient_verdict(1.0, 0.04)
        self.assertTrue(result2["h_ok"])
        self.assertTrue(result2["v_ok"])

    def test_low_horizontal_flags_only_h(self):
        result = tsl.volume_coefficient_verdict(0.45, 0.06)
        self.assertFalse(result["h_ok"])
        self.assertTrue(result["v_ok"])
        self.assertEqual(
            result["verdict"], "horizontal tail volume coefficient outside typical range"
        )

    def test_low_vertical_flags_only_v(self):
        result = tsl.volume_coefficient_verdict(0.7, 0.03)
        self.assertTrue(result["h_ok"])
        self.assertFalse(result["v_ok"])
        self.assertEqual(
            result["verdict"], "vertical tail volume coefficient outside typical range"
        )

    def test_both_out_of_range(self):
        result = tsl.volume_coefficient_verdict(1.05, 0.08)
        self.assertFalse(result["h_ok"])
        self.assertFalse(result["v_ok"])
        self.assertEqual(
            result["verdict"], "both tail volume coefficients outside typical ranges"
        )

    def test_high_horizontal_flags_only_h(self):
        result = tsl.volume_coefficient_verdict(1.02, 0.05)
        self.assertFalse(result["h_ok"])
        self.assertTrue(result["v_ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
