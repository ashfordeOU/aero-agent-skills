#!/usr/bin/env python3
"""Gate 3 contract test: uncertainty propagation logic.

Exercises scripts/uncertainty_propagation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - combined
standard uncertainty u_c = sqrt(sum((s_i * u_i)**2)), expanded
uncertainty U = k * u_c, variance contribution (s_i * u_i)**2 with
percent share, dominant contribution, and ValueError on empty lists,
length mismatch, negative uncertainties, or non-positive coverage
factor. Analytic check on sensitivities [2.0, 3.0], uncertainties
[0.1, 0.05]: contributions 0.04 and 0.0225, u_c = sqrt(0.0625) = 0.25,
U = 0.5 with k = 2.0, shares 64% and 36%.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uncertainty_propagation_logic as up  # noqa: E402


class CombinedStandardUncertaintyTest(unittest.TestCase):
    def test_analytic_two_inputs(self):
        # u_c = sqrt((2*0.1)^2 + (3*0.05)^2) = sqrt(0.04 + 0.0225) = 0.25
        self.assertAlmostEqual(
            up.combined_standard_uncertainty([2.0, 3.0], [0.1, 0.05]),
            0.25,
            places=12,
        )

    def test_single_input(self):
        self.assertAlmostEqual(
            up.combined_standard_uncertainty([1.0], [0.5]), 0.5, places=12
        )

    def test_zero_contributions(self):
        self.assertAlmostEqual(
            up.combined_standard_uncertainty([0.0], [0.0]), 0.0, places=12
        )

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            up.combined_standard_uncertainty([], [])

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            up.combined_standard_uncertainty([1.0, 2.0], [1.0])

    def test_negative_uncertainty_raises(self):
        with self.assertRaises(ValueError):
            up.combined_standard_uncertainty([1.0], [-0.5])


class ExpandedUncertaintyTest(unittest.TestCase):
    def test_default_coverage_factor(self):
        self.assertAlmostEqual(up.expanded_uncertainty(0.25), 0.5, places=12)

    def test_custom_coverage_factor(self):
        self.assertAlmostEqual(
            up.expanded_uncertainty(0.25, 1.96), 0.49, places=12
        )

    def test_nonpositive_k_raises(self):
        with self.assertRaises(ValueError):
            up.expanded_uncertainty(0.25, 0.0)
        with self.assertRaises(ValueError):
            up.expanded_uncertainty(0.25, -1.0)


class UncertaintyContributionsTest(unittest.TestCase):
    def test_analytic_contributions_sorted(self):
        contribs = up.uncertainty_contributions([2.0, 3.0], [0.1, 0.05])
        self.assertEqual(len(contribs), 2)
        # Sorted by contribution descending: index 0 first.
        self.assertEqual(contribs[0]["index"], 0)
        self.assertAlmostEqual(contribs[0]["contribution"], 0.04, places=12)
        self.assertAlmostEqual(contribs[0]["percent"], 64.0, places=10)
        self.assertEqual(contribs[1]["index"], 1)
        self.assertAlmostEqual(contribs[1]["contribution"], 0.0225, places=12)
        self.assertAlmostEqual(contribs[1]["percent"], 36.0, places=10)
        total_percent = sum(c["percent"] for c in contribs)
        self.assertAlmostEqual(total_percent, 100.0, places=10)

    def test_zero_total_percents_are_zero(self):
        contribs = up.uncertainty_contributions([0.0], [0.0])
        self.assertEqual(len(contribs), 1)
        self.assertAlmostEqual(contribs[0]["percent"], 0.0)

    def test_negative_uncertainty_raises(self):
        with self.assertRaises(ValueError):
            up.uncertainty_contributions([1.0, 1.0], [0.1, -0.2])


class DominantContributionTest(unittest.TestCase):
    def test_analytic_dominant(self):
        dom = up.dominant_contribution([2.0, 3.0], [0.1, 0.05])
        self.assertEqual(dom["index"], 0)
        self.assertAlmostEqual(dom["percent"], 64.0, places=10)

    def test_empty_returns_none(self):
        self.assertIsNone(up.dominant_contribution([], []))


if __name__ == "__main__":
    unittest.main(verbosity=2)
