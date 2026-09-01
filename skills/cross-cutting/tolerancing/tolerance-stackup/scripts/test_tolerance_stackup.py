#!/usr/bin/env python3
"""Gate 3 contract test: assembly tolerance stack-up analysis.

Exercises scripts/tolerance_stackup_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (worst case and RSS stack-up
totals, signed nominal assembly, assembly limits, RSS variance shares;
invalid inputs raise ValueError.

Anchors:
- nominal_total([100, 50, 25], [1, 1, 1]) = 175.0
- nominal_total([10, 5, 2], [1, -1, 1]) = 7.0 (signed chain)
- worst_case_total([0.5, 0.25, 0.1]) = 0.85
- rss_total([0.5, 0.25, 0.1]) = sqrt(0.3225) = 0.567893 (places 5)
- stackup_limits(175.0, 0.85) = (174.15, 175.85)
- rss_shares([0.5, 0.25, 0.1]) = [77.519, 19.380, 3.101] percent
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tolerance_stackup_logic as ts  # noqa: E402


class NominalTotalTest(unittest.TestCase):
    def test_anchor_all_plus(self):
        self.assertAlmostEqual(ts.nominal_total([100, 50, 25], [1, 1, 1]), 175.0)

    def test_anchor_signed_chain(self):
        self.assertAlmostEqual(ts.nominal_total([10, 5, 2], [1, -1, 1]), 7.0)

    def test_anchor_mixed_sign(self):
        self.assertAlmostEqual(ts.nominal_total([100, 30, 20], [1, -1, -1]), 50.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ts.nominal_total([], [])
        with self.assertRaises(ValueError):
            ts.nominal_total([10, 5], [1])


class WorstCaseTotalTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(ts.worst_case_total([0.5, 0.25, 0.1]), 0.85)

    def test_single_part(self):
        self.assertAlmostEqual(ts.worst_case_total([0.3]), 0.3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ts.worst_case_total([])
        with self.assertRaises(ValueError):
            ts.worst_case_total([0.5, -0.1])


class RssTotalTest(unittest.TestCase):
    def test_anchor(self):
        expected = math.sqrt(0.5 ** 2 + 0.25 ** 2 + 0.1 ** 2)
        self.assertAlmostEqual(ts.rss_total([0.5, 0.25, 0.1]), expected, places=5)
        self.assertAlmostEqual(ts.rss_total([0.5, 0.25, 0.1]), 0.567893, places=5)

    def test_rss_never_exceeds_worst_case(self):
        tols = [0.5, 0.25, 0.1]
        self.assertLessEqual(ts.rss_total(tols), ts.worst_case_total(tols))

    def test_single_part_equals_part(self):
        self.assertAlmostEqual(ts.rss_total([0.3]), 0.3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ts.rss_total([])
        with self.assertRaises(ValueError):
            ts.rss_total([0.5, -0.2])


class StackupLimitsTest(unittest.TestCase):
    def test_anchor(self):
        self.assertEqual(ts.stackup_limits(175.0, 0.85), (174.15, 175.85))

    def test_rss_limits_tighter_than_worst_case(self):
        wc_lo, wc_hi = ts.stackup_limits(175.0, ts.worst_case_total([0.5, 0.25, 0.1]))
        rss_lo, rss_hi = ts.stackup_limits(175.0, ts.rss_total([0.5, 0.25, 0.1]))
        self.assertGreater(rss_lo, wc_lo)
        self.assertLess(rss_hi, wc_hi)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ts.stackup_limits(175.0, -0.1)


class RssSharesTest(unittest.TestCase):
    def test_anchor_shares(self):
        shares = ts.rss_shares([0.5, 0.25, 0.1])
        self.assertAlmostEqual(shares[0], 77.519, places=2)
        self.assertAlmostEqual(shares[1], 19.380, places=2)
        self.assertAlmostEqual(shares[2], 3.101, places=2)

    def test_shares_sum_to_100(self):
        self.assertAlmostEqual(sum(ts.rss_shares([0.5, 0.25, 0.1])), 100.0, places=6)

    def test_equal_tolerances_equal_shares(self):
        shares = ts.rss_shares([0.2, 0.2, 0.2, 0.2])
        for s in shares:
            self.assertAlmostEqual(s, 25.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ts.rss_shares([])
        with self.assertRaises(ValueError):
            ts.rss_shares([0.0, 0.0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
