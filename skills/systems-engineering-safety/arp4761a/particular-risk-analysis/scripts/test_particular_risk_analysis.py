#!/usr/bin/env python3
"""Gate 3 contract test: ARP4761A particular risk analysis.

Exercises scripts/particular_risk_analysis_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - event and
conditional probability combination, event exposure over flight
hours, hazard zone containment verdicts, and invalid-input handling.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import particular_risk_analysis_logic as pra  # noqa: E402


class ConditionalProbabilityTest(unittest.TestCase):
    """conditional_probability: analytic product p_a * p_b_given_a.

    Hand-computed: 0.1 * 0.5 = 0.05; 1.0 * 0.25 = 0.25;
    0.0 * 0.9 = 0.0; 0.02 * 0.3 = 0.006.
    """

    def test_basic_product(self):
        self.assertAlmostEqual(pra.conditional_probability(0.1, 0.5), 0.05)

    def test_certain_event(self):
        self.assertAlmostEqual(pra.conditional_probability(1.0, 0.25), 0.25)

    def test_impossible_event(self):
        self.assertAlmostEqual(pra.conditional_probability(0.0, 0.9), 0.0)

    def test_small_probabilities(self):
        self.assertAlmostEqual(pra.conditional_probability(0.02, 0.3), 0.006)

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            pra.conditional_probability(1.1, 0.5)
        with self.assertRaises(ValueError):
            pra.conditional_probability(0.5, -0.1)


class ExposureProbabilityTest(unittest.TestCase):
    """exposure_probability: 1 - exp(-rate*hours), hand-computed.

    rate*hours = 0.1 -> 1 - exp(-0.1) = 0.09516258196404043;
    rate*hours = 0.001 -> 1 - exp(-0.001) = 0.000999500166624978;
    rate 0 -> 0.0; 1e-6 for 1 hour -> 9.999950000166673e-07.
    """

    def test_poisson_lambda_0_1(self):
        self.assertAlmostEqual(
            pra.exposure_probability(0.0001, 1000.0), 0.09516258196404043, places=9
        )

    def test_poisson_lambda_0_001(self):
        self.assertAlmostEqual(
            pra.exposure_probability(0.001, 1.0), 0.000999500166624978, places=12
        )

    def test_zero_rate(self):
        self.assertEqual(pra.exposure_probability(0.0, 1000.0), 0.0)

    def test_small_rate_approximates_rate_times_hours(self):
        p = pra.exposure_probability(1e-6, 1.0)
        self.assertAlmostEqual(p, 1e-6, places=9)

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            pra.exposure_probability(-0.001, 100.0)

    def test_negative_hours_raises(self):
        with self.assertRaises(ValueError):
            pra.exposure_probability(0.001, -5.0)


class ContainmentVerdictTest(unittest.TestCase):
    """containment_verdict: zero overlap contained, any overlap action."""

    def test_zero_overlap_ok(self):
        self.assertEqual(pra.containment_verdict(0.0), "ok")

    def test_partial_overlap_action(self):
        self.assertEqual(pra.containment_verdict(0.05), "action")

    def test_full_overlap_action(self):
        self.assertEqual(pra.containment_verdict(1.0), "action")

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            pra.containment_verdict(-0.01)
        with self.assertRaises(ValueError):
            pra.containment_verdict(1.01)


if __name__ == "__main__":
    unittest.main(verbosity=2)
