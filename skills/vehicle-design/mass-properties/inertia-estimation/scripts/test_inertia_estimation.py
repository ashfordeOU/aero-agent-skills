#!/usr/bin/env python3
"""Gate 3 contract test: vehicle mass properties (inertia estimation).

Exercises scripts/inertia_estimation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 — moment of
inertia from radius of gyration, parallel-axis theorem, and
gyration-radius sanity; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import inertia_estimation_logic as ie  # noqa: E402


class MomentOfInertiaTest(unittest.TestCase):
    def test_gyration_formula(self):
        self.assertAlmostEqual(ie.moi_gyration(1000.0, 2.0), 4000.0)

    def test_zero_mass_zero_inertia(self):
        self.assertAlmostEqual(ie.moi_gyration(0.0, 2.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ie.moi_gyration(-1.0, 2.0)
        with self.assertRaises(ValueError):
            ie.moi_gyration(1000.0, 0.0)
        with self.assertRaises(ValueError):
            ie.moi_gyration(1000.0, -1.0)


class ParallelAxisTest(unittest.TestCase):
    def test_parallel_axis_theorem(self):
        self.assertAlmostEqual(ie.parallel_axis(100.0, 10.0, 3.0), 190.0)

    def test_zero_offset_no_change(self):
        self.assertAlmostEqual(ie.parallel_axis(100.0, 10.0, 0.0), 100.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ie.parallel_axis(-1.0, 10.0, 3.0)
        with self.assertRaises(ValueError):
            ie.parallel_axis(100.0, -1.0, 3.0)
        with self.assertRaises(ValueError):
            ie.parallel_axis(100.0, 10.0, -0.5)


class GyrationSanityTest(unittest.TestCase):
    def test_within_dimension(self):
        self.assertTrue(ie.gyration_sane(2.0, 10.0))

    def test_exceeding_dimension(self):
        self.assertFalse(ie.gyration_sane(12.0, 10.0))

    def test_zero_or_negative_raises(self):
        with self.assertRaises(ValueError):
            ie.gyration_sane(0.0, 10.0)
        with self.assertRaises(ValueError):
            ie.gyration_sane(-1.0, 10.0)
        with self.assertRaises(ValueError):
            ie.gyration_sane(2.0, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
