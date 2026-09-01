#!/usr/bin/env python3
"""Gate 3 contract test: CMH-17 composite allowables logic.

Exercises scripts/cmh17_allowables_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3. Covers the
one-sided normal tolerance k-factor approximation (Owen/Odeh),
minimum sample counts, A-/B-basis allowables below the sample mean,
coupon pooling across batches (larger effective sample shrinks the
k-factor and the pooled standard deviation stays within the batch
spreads), Weibull content quantiles, laminate knockdown application,
the allowable table builder, and invalid-input edge cases.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cmh17_allowables_logic as cmh17  # noqa: E402


class KFactorTest(unittest.TestCase):
    def test_k_in_known_band_for_ten_a_basis(self):
        k = cmh17.k_factor_one_sided(10, "A")
        self.assertTrue(3.5 <= k <= 4.3, k)

    def test_k_in_known_band_for_ten_b_basis(self):
        k = cmh17.k_factor_one_sided(10, "B")
        self.assertTrue(2.0 <= k <= 2.8, k)

    def test_k_decreases_as_sample_grows(self):
        k10 = cmh17.k_factor_one_sided(10, "A")
        k20 = cmh17.k_factor_one_sided(20, "A")
        k50 = cmh17.k_factor_one_sided(50, "A")
        self.assertTrue(k10 > k20 > k50)

    def test_a_basis_k_exceeds_b_basis_k(self):
        self.assertGreater(
            cmh17.k_factor_one_sided(10, "A"),
            cmh17.k_factor_one_sided(10, "B"),
        )

    def test_invalid_basis_raises(self):
        with self.assertRaises(ValueError):
            cmh17.k_factor_one_sided(10, "C")

    def test_invalid_confidence_raises(self):
        with self.assertRaises(ValueError):
            cmh17.k_factor_one_sided(10, "A", conf=0.90)

    def test_sample_count_below_two_raises(self):
        with self.assertRaises(ValueError):
            cmh17.k_factor_one_sided(1, "A")
        with self.assertRaises(ValueError):
            cmh17.k_factor_one_sided(10.5, "A")


class MinSamplesTest(unittest.TestCase):
    def test_known_minimums(self):
        self.assertEqual(cmh17.min_samples("A"), 10)
        self.assertEqual(cmh17.min_samples("B"), 6)

    def test_unknown_basis_raises(self):
        with self.assertRaises(ValueError):
            cmh17.min_samples("C")

    def test_check_sample_count(self):
        ok, required = cmh17.check_sample_count(12, "A")
        self.assertTrue(ok)
        self.assertEqual(required, 10)
        ok, required = cmh17.check_sample_count(5, "B")
        self.assertFalse(ok)
        self.assertEqual(required, 6)


class AllowableFromSampleTest(unittest.TestCase):
    SAMPLE = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0]

    def test_allowable_below_mean_and_positive(self):
        allowable = cmh17.allowable_from_sample(self.SAMPLE, "B")
        mean = sum(self.SAMPLE) / len(self.SAMPLE)
        self.assertGreater(allowable, 0.0)
        self.assertLess(allowable, mean)

    def test_b_basis_minimum_count_works(self):
        allowable = cmh17.allowable_from_sample(self.SAMPLE, "B")
        self.assertGreater(allowable, 0.0)

    def test_a_basis_allowable_below_b_basis_allowable(self):
        samples = self.SAMPLE * 2  # 12 values: above both minimums
        a = cmh17.allowable_from_sample(samples, "A")
        b = cmh17.allowable_from_sample(samples, "B")
        self.assertLess(a, b)

    def test_sample_below_minimum_raises(self):
        with self.assertRaises(ValueError):
            cmh17.allowable_from_sample(self.SAMPLE[:5], "A")
        with self.assertRaises(ValueError):
            cmh17.allowable_from_sample(self.SAMPLE[:5], "B")

    def test_zero_standard_deviation_raises(self):
        with self.assertRaises(ValueError):
            cmh17.allowable_from_sample([100.0] * 10, "A")

    def test_unknown_basis_raises(self):
        with self.assertRaises(ValueError):
            cmh17.allowable_from_sample(self.SAMPLE, "C")


class PoolingTest(unittest.TestCase):
    BATCH1 = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0]
    BATCH2 = [99.0, 101.0, 103.0, 105.0, 107.0, 109.0]

    def test_pooling_shrinks_k_and_effective_n_is_total(self):
        pooled = cmh17.pooled_allowable([self.BATCH1, self.BATCH2], "B")
        self.assertEqual(pooled["n"], 12)
        self.assertEqual(pooled["batches"], [6, 6])
        single_k = cmh17.k_factor_one_sided(6, "B")
        self.assertLess(pooled["k"], single_k)

    def test_pooled_sd_stays_within_batch_spreads(self):
        pooled = cmh17.pooled_allowable([self.BATCH1, self.BATCH2], "B")
        sds = [cmh17.statistics.stdev(b) for b in (self.BATCH1, self.BATCH2)]
        self.assertLessEqual(pooled["sd"], max(sds))
        self.assertGreaterEqual(pooled["sd"], min(sds))

    def test_pooled_allowable_below_pooled_mean(self):
        pooled = cmh17.pooled_allowable([self.BATCH1, self.BATCH2], "B")
        self.assertLess(pooled["allowable"], pooled["mean"])
        self.assertGreater(pooled["allowable"], 0.0)

    def test_pooling_raises_on_empty_or_short_batches(self):
        with self.assertRaises(ValueError):
            cmh17.pooled_allowable([], "B")
        with self.assertRaises(ValueError):
            cmh17.pooled_allowable([[100.0]], "B")

    def test_pooling_raises_below_minimum_total(self):
        with self.assertRaises(ValueError):
            cmh17.pooled_allowable([self.BATCH1[:3], self.BATCH2[:2]], "B")

    def test_pooling_unknown_basis_raises(self):
        with self.assertRaises(ValueError):
            cmh17.pooled_allowable([self.BATCH1], "C")


class WeibullTest(unittest.TestCase):
    VALUES = [110.0, 112.0, 115.0, 118.0, 122.0, 125.0, 129.0, 133.0, 138.0, 144.0]

    def test_content_value_b_basis_above_a_basis(self):
        b_val = cmh17.weibull_content_value(self.VALUES, 0.90)
        a_val = cmh17.weibull_content_value(self.VALUES, 0.99)
        self.assertGreater(b_val, a_val)

    def test_weibull_basis_below_content_value_and_mean(self):
        content = cmh17.weibull_content_value(self.VALUES, 0.90)
        basis = cmh17.weibull_basis(self.VALUES, "B")
        mean = sum(self.VALUES) / len(self.VALUES)
        self.assertLess(basis, content)
        self.assertLess(basis, mean)
        self.assertGreater(basis, 0.0)

    def test_weibull_requires_positive_values(self):
        with self.assertRaises(ValueError):
            cmh17.weibull_mle([0.0, 1.0, 2.0])
        with self.assertRaises(ValueError):
            cmh17.weibull_mle([100.0])

    def test_content_value_p_bounds(self):
        with self.assertRaises(ValueError):
            cmh17.weibull_content_value(self.VALUES, 0.0)
        with self.assertRaises(ValueError):
            cmh17.weibull_content_value(self.VALUES, 1.0)

    def test_weibull_basis_unknown_basis_raises(self):
        with self.assertRaises(ValueError):
            cmh17.weibull_basis(self.VALUES, "C")


class KnockdownTest(unittest.TestCase):
    def test_unit_factors_leave_allowable_unchanged(self):
        value, combined = cmh17.knockdown(100.0, 1.0, 1.0, 1.0)
        self.assertEqual(combined, 1.0)
        self.assertAlmostEqual(value, 100.0)

    def test_knockdown_reduces_allowable(self):
        value, combined = cmh17.knockdown(100.0, 0.9, 0.85, 0.95)
        self.assertAlmostEqual(combined, 0.9 * 0.85 * 0.95)
        self.assertLess(value, 100.0)
        self.assertAlmostEqual(value, 100.0 * combined)

    def test_invalid_factors_raise(self):
        with self.assertRaises(ValueError):
            cmh17.knockdown(100.0, 0.0, 1.0, 1.0)
        with self.assertRaises(ValueError):
            cmh17.knockdown(100.0, 1.2, 1.0, 1.0)
        with self.assertRaises(ValueError):
            cmh17.knockdown(100.0, 1.0, -0.5, 1.0)


class BasisStatementTest(unittest.TestCase):
    def test_statements(self):
        self.assertEqual(
            cmh17.basis_statement("A"), "A-basis: 95% confidence, 99% content"
        )
        self.assertEqual(
            cmh17.basis_statement("B"), "B-basis: 95% confidence, 90% content"
        )

    def test_unknown_basis_raises(self):
        with self.assertRaises(ValueError):
            cmh17.basis_statement("C")


class AllowableTableTest(unittest.TestCase):
    TENSION = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0]
    COMPRESSION = [80.0, 82.0, 84.0, 86.0, 88.0, 90.0, 92.0]

    def test_table_rows_and_knockdown_ordering(self):
        props = [("tension", self.TENSION), ("compression", self.COMPRESSION)]
        rows = cmh17.build_allowable_table(
            props, "B", env_factor=0.9, bvid_factor=0.85, hole_factor=0.95
        )
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertIn(row["property"], ("tension", "compression"))
            self.assertEqual(row["basis"], "B")
            self.assertLess(row["laminate_allowable"], row["lamina_allowable"])
            self.assertEqual(
                row["statement"], "B-basis: 95% confidence, 90% content"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
