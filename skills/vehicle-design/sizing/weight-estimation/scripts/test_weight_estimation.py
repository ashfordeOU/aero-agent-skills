#!/usr/bin/env python3
"""Gate 3 contract test: vehicle weight estimation logic.

Exercises scripts/weight_estimation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - moments,
center of gravity from matching weight/arm lists, CG envelope
boundary checks, empty-weight fraction band membership per
category, and ValueError on invalid inputs (mismatch, empty,
zero total weight, reversed limits, unknown category).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import weight_estimation_logic as we  # noqa: E402


class MomentTest(unittest.TestCase):
    def test_known_moment(self):
        self.assertEqual(we.moment(100.0, 10.0), 1000.0)
        self.assertEqual(we.moment(0.0, 10.0), 0.0)

    def test_negative_weight_raises(self):
        with self.assertRaises(ValueError):
            we.moment(-5.0, 10.0)


class CgTest(unittest.TestCase):
    def test_known_two_weight_case(self):
        cg = we.cg_from_moments([100.0, 200.0], [10.0, 20.0])
        self.assertAlmostEqual(cg, 16.666666666666668)

    def test_single_weight_cg_is_its_arm(self):
        self.assertAlmostEqual(we.cg_from_moments([50.0], [7.0]), 7.0)

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            we.cg_from_moments([100.0, 200.0], [10.0])

    def test_empty_lists_raise(self):
        with self.assertRaises(ValueError):
            we.cg_from_moments([], [])

    def test_zero_total_weight_raises(self):
        with self.assertRaises(ValueError):
            we.cg_from_moments([0.0, 0.0], [10.0, 20.0])


class EnvelopeTest(unittest.TestCase):
    def test_boundaries_pass(self):
        self.assertTrue(we.cg_within_envelope(16.0, 16.0, 20.0))
        self.assertTrue(we.cg_within_envelope(20.0, 16.0, 20.0))
        self.assertTrue(we.cg_within_envelope(18.0, 16.0, 20.0))

    def test_just_outside_fails(self):
        self.assertFalse(we.cg_within_envelope(15.99, 16.0, 20.0))
        self.assertFalse(we.cg_within_envelope(20.01, 16.0, 20.0))

    def test_reversed_limits_raise(self):
        with self.assertRaises(ValueError):
            we.cg_within_envelope(18.0, 20.0, 16.0)


class EmptyWeightFractionTest(unittest.TestCase):
    def test_known_bands(self):
        self.assertEqual(we.empty_weight_fraction_band("transport"), (0.42, 0.55))
        self.assertEqual(
            we.empty_weight_fraction_band("general-aviation"), (0.55, 0.68)
        )
        self.assertEqual(we.empty_weight_fraction_band("turboprop"), (0.50, 0.62))

    def test_band_membership(self):
        in_band, band, fraction = we.check_empty_weight_fraction(
            5000.0, 10000.0, "transport"
        )
        self.assertTrue(in_band)
        self.assertAlmostEqual(fraction, 0.5)
        self.assertEqual(band, (0.42, 0.55))

        in_band, _, fraction = we.check_empty_weight_fraction(
            6000.0, 10000.0, "transport"
        )
        self.assertFalse(in_band)
        self.assertAlmostEqual(fraction, 0.6)

    def test_turboprop_band_membership(self):
        in_band, _, _ = we.check_empty_weight_fraction(5600.0, 10000.0, "turboprop")
        self.assertTrue(in_band)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            we.empty_weight_fraction_band("fighter")
        with self.assertRaises(ValueError):
            we.check_empty_weight_fraction(5000.0, 10000.0, "fighter")

    def test_nonpositive_mtow_raises(self):
        with self.assertRaises(ValueError):
            we.check_empty_weight_fraction(5000.0, 0.0, "transport")
        with self.assertRaises(ValueError):
            we.check_empty_weight_fraction(5000.0, -1000.0, "transport")

    def test_negative_empty_weight_raises(self):
        with self.assertRaises(ValueError):
            we.check_empty_weight_fraction(-1.0, 10000.0, "transport")


if __name__ == "__main__":
    unittest.main(verbosity=2)
