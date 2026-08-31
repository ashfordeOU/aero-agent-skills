#!/usr/bin/env python3
"""Gate 3 contract test: envelope expansion (flight-test-operations).

Exercises scripts/envelope_expansion_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - corner speed, airspeed
classification, expansion step size, and load factor limit checks;
invalid inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import envelope_expansion_logic as ee  # noqa: E402


class CornerSpeedTest(unittest.TestCase):
    def test_anchor_corner_speed(self):
        va = ee.corner_speed(60, 3.8)
        self.assertAlmostEqual(va, 116.96, delta=0.05)
        self.assertAlmostEqual(va, 60 * math.sqrt(3.8), delta=0.05)

    def test_unit_load_factor(self):
        self.assertAlmostEqual(ee.corner_speed(50, 4.0), 100.0, delta=0.01)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ee.corner_speed(0, 3.8)
        with self.assertRaises(ValueError):
            ee.corner_speed(-60, 3.8)
        with self.assertRaises(ValueError):
            ee.corner_speed(60, 1.0)
        with self.assertRaises(ValueError):
            ee.corner_speed(60, 0.5)


class ClassifyAirspeedTest(unittest.TestCase):
    B = (80, 116.96, 140, 160)  # vfe, va, vno, vne

    def test_anchor_below_vfe(self):
        self.assertEqual(ee.classify_airspeed(70, *self.B), "below-vfe")

    def test_anchor_vfe_to_va(self):
        self.assertEqual(ee.classify_airspeed(100, *self.B), "vfe-to-va")

    def test_anchor_va_to_vno(self):
        self.assertEqual(ee.classify_airspeed(130, *self.B), "va-to-vno")

    def test_anchor_vno_to_vne(self):
        self.assertEqual(ee.classify_airspeed(150, *self.B), "vno-to-vne")

    def test_anchor_at_or_above_vne(self):
        self.assertEqual(ee.classify_airspeed(165, *self.B), "at-or-above-vne")

    def test_boundaries_are_half_open(self):
        self.assertEqual(ee.classify_airspeed(80, *self.B), "vfe-to-va")
        self.assertEqual(ee.classify_airspeed(116.96, *self.B), "va-to-vno")
        self.assertEqual(ee.classify_airspeed(140, *self.B), "vno-to-vne")
        self.assertEqual(ee.classify_airspeed(160, *self.B), "at-or-above-vne")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ee.classify_airspeed(-1, *self.B)
        with self.assertRaises(ValueError):
            ee.classify_airspeed(100, 120, 110, 140, 160)  # vfe >= va
        with self.assertRaises(ValueError):
            ee.classify_airspeed(100, 80, 116.96, 160, 140)  # vno >= vne
        with self.assertRaises(ValueError):
            ee.classify_airspeed(100, 0, 116.96, 140, 160)  # vfe <= 0


class ExpansionStepSizeTest(unittest.TestCase):
    def test_anchor_step_size(self):
        self.assertEqual(ee.expansion_step_size(120, 60, 4), 15.0)

    def test_fractional_step(self):
        self.assertAlmostEqual(ee.expansion_step_size(110, 60, 4), 12.5)

    def test_zero_delta(self):
        self.assertEqual(ee.expansion_step_size(60, 60, 4), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ee.expansion_step_size(120, 60, 0)
        with self.assertRaises(ValueError):
            ee.expansion_step_size(120, 60, -2)
        with self.assertRaises(ValueError):
            ee.expansion_step_size(60, 120, 4)  # target < current


class LoadFactorLimitTest(unittest.TestCase):
    def test_within_limit(self):
        self.assertTrue(ee.load_factor_within_limit(3.5, 3.8))
        self.assertTrue(ee.load_factor_within_limit(3.8, 3.8))

    def test_exceeding_limit(self):
        self.assertFalse(ee.load_factor_within_limit(4.0, 3.8))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ee.load_factor_within_limit(-0.1, 3.8)
        with self.assertRaises(ValueError):
            ee.load_factor_within_limit(3.5, 0)
        with self.assertRaises(ValueError):
            ee.load_factor_within_limit(3.5, -1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
