#!/usr/bin/env python3
"""Gate 3 contract test: MMPDS metallic allowables logic.

Exercises scripts/mmpsd_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - one-sided normal
tolerance k-factor approximation (Owen/Odeh); k decreases as the
sample grows; A-basis k exceeds B-basis k at the same n; common
minimum sample counts (A: 10, B: 6); allowable = mean - k*stdev
with the result below the mean and positive; invalid inputs
(basis, confidence, sample count, zero standard deviation) raise
ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mmpsd_logic as mmpsd  # noqa: E402


class KFactorTest(unittest.TestCase):
    def test_k_in_known_band_for_ten_a_basis(self):
        k = mmpsd.k_factor_one_sided(10, "A")
        self.assertTrue(3.5 <= k <= 4.3, k)

    def test_k_decreases_as_sample_grows(self):
        k10 = mmpsd.k_factor_one_sided(10, "A")
        k20 = mmpsd.k_factor_one_sided(20, "A")
        k50 = mmpsd.k_factor_one_sided(50, "A")
        self.assertTrue(k10 > k20 > k50)

    def test_a_basis_k_exceeds_b_basis_k(self):
        self.assertGreater(
            mmpsd.k_factor_one_sided(10, "A"),
            mmpsd.k_factor_one_sided(10, "B"),
        )

    def test_invalid_basis_raises(self):
        with self.assertRaises(ValueError):
            mmpsd.k_factor_one_sided(10, "C")

    def test_invalid_confidence_raises(self):
        with self.assertRaises(ValueError):
            mmpsd.k_factor_one_sided(10, "A", conf=0.90)

    def test_sample_count_below_two_raises(self):
        with self.assertRaises(ValueError):
            mmpsd.k_factor_one_sided(1, "A")
        with self.assertRaises(ValueError):
            mmpsd.k_factor_one_sided(10.5, "A")


class MinSamplesTest(unittest.TestCase):
    def test_known_minimums(self):
        self.assertEqual(mmpsd.min_samples("A"), 10)
        self.assertEqual(mmpsd.min_samples("B"), 6)

    def test_unknown_basis_raises(self):
        with self.assertRaises(ValueError):
            mmpsd.min_samples("C")


class AllowableFromSampleTest(unittest.TestCase):
    SAMPLE = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0]

    def test_allowable_below_mean_and_positive(self):
        allowable = mmpsd.allowable_from_sample(self.SAMPLE, "B")
        mean = sum(self.SAMPLE) / len(self.SAMPLE)
        self.assertGreater(allowable, 0.0)
        self.assertLess(allowable, mean)

    def test_b_basis_minimum_count_works(self):
        allowable = mmpsd.allowable_from_sample(self.SAMPLE, "B")
        self.assertGreater(allowable, 0.0)

    def test_a_basis_allowable_below_b_basis_allowable(self):
        samples = self.SAMPLE * 2  # 12 values: above both minimums
        a = mmpsd.allowable_from_sample(samples, "A")
        b = mmpsd.allowable_from_sample(samples, "B")
        self.assertLess(a, b)

    def test_sample_below_minimum_raises(self):
        with self.assertRaises(ValueError):
            mmpsd.allowable_from_sample(self.SAMPLE[:5], "A")
        with self.assertRaises(ValueError):
            mmpsd.allowable_from_sample(self.SAMPLE[:5], "B")

    def test_zero_standard_deviation_raises(self):
        with self.assertRaises(ValueError):
            mmpsd.allowable_from_sample([100.0] * 10, "A")

    def test_unknown_basis_raises(self):
        with self.assertRaises(ValueError):
            mmpsd.allowable_from_sample(self.SAMPLE, "C")


class DesignValueSanityTest(unittest.TestCase):
    def test_sane_values(self):
        self.assertTrue(mmpsd.design_value_sanity(80.0, 100.0, "A"))
        self.assertFalse(mmpsd.design_value_sanity(100.0, 100.0, "A"))
        self.assertFalse(mmpsd.design_value_sanity(-1.0, 100.0, "A"))
        self.assertFalse(mmpsd.design_value_sanity(120.0, 100.0, "A"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
