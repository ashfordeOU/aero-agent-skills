#!/usr/bin/env python3
"""Gate 3 contract test: Markov analysis for safety and reliability.

Exercises scripts/markov_analysis_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (Markov chain state
probabilities from transition rates, two-state failure and repair
availability, non-repairable failure probability and MTTF, series
failure rates, redundant configuration reliability with k-out-of-n,
invalid inputs raise ValueError).

Anchors (computed offline, closed form):
- two_state_failure_probability(1e-4, 1e-2, 1000) = 0.009900583371
- steady_state_availability(1e-4, 1e-2) = (100/101, 1/101)
- nonrepairable_probabilities(1e-4, 10000) = (e^-1, 1 - e^-1)
- redundancy_mttf(2, 1e-4) = 15000 h; (3, 1e-4) = 18333.333333 h
- series_failure_rate([1e-5, 2e-5, 3e-5]) = 6e-5
- 2-unit active redundancy at lam*t = 1: P = (e^-2, 2(e^-1 - e^-2),
  (1 - e^-1)^2), sum 1
- k_of_n_reliability(3, 2, 0.9) = 0.972; (2, 2, 0.9) = 0.81
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import markov_analysis_logic as ma  # noqa: E402


class TwoStateModelTest(unittest.TestCase):
    def test_anchor_failure_probability(self):
        pf = ma.two_state_failure_probability(1e-4, 1e-2, 1000.0)
        self.assertAlmostEqual(pf, 0.009900583371, places=9)

    def test_availability_complements(self):
        p_ok, p_failed = ma.two_state_availability(1e-4, 1e-2, 1000.0)
        self.assertAlmostEqual(p_ok + p_failed, 1.0, places=12)
        self.assertAlmostEqual(p_failed, 0.009900583371, places=9)

    def test_steady_state_limit(self):
        a, u = ma.steady_state_availability(1e-4, 1e-2)
        self.assertAlmostEqual(a, 100.0 / 101.0, places=12)
        self.assertAlmostEqual(u, 1.0 / 101.0, places=12)
        self.assertAlmostEqual(a + u, 1.0, places=12)

    def test_small_time_linear_limit(self):
        # For (lam+mu)*t << 1 the repairable failure probability
        # approaches lam*t within the first-order error term.
        lam, mu, t = 1e-4, 1e-1, 0.1
        pf = ma.two_state_failure_probability(lam, mu, t)
        self.assertAlmostEqual(pf, lam * t, delta=0.01 * lam * t)

    def test_zero_time(self):
        p_ok, p_failed = ma.two_state_availability(1e-4, 1e-2, 0.0)
        self.assertAlmostEqual(p_ok, 1.0, places=12)
        self.assertAlmostEqual(p_failed, 0.0, places=12)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ma.two_state_failure_probability(0.0, 1e-2, 100.0)
        with self.assertRaises(ValueError):
            ma.two_state_failure_probability(1e-4, 0.0, 100.0)
        with self.assertRaises(ValueError):
            ma.two_state_failure_probability(1e-4, 1e-2, -1.0)
        with self.assertRaises(ValueError):
            ma.steady_state_availability(0.0, 1e-2)


class NonRepairableTest(unittest.TestCase):
    def test_anchor_survival(self):
        r, f = ma.nonrepairable_probabilities(1e-4, 10000.0)
        self.assertAlmostEqual(r, math.exp(-1.0), places=12)
        self.assertAlmostEqual(f, 1.0 - math.exp(-1.0), places=12)
        self.assertAlmostEqual(r + f, 1.0, places=12)

    def test_mttf_anchor(self):
        self.assertAlmostEqual(ma.mttf_exponential(1e-4), 10000.0, places=6)

    def test_mttf_inverse_rate(self):
        self.assertAlmostEqual(ma.mttf_exponential(2e-4), 5000.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ma.nonrepairable_probabilities(0.0, 100.0)
        with self.assertRaises(ValueError):
            ma.nonrepairable_probabilities(1e-4, -1.0)
        with self.assertRaises(ValueError):
            ma.mttf_exponential(0.0)


class RateCombinationTest(unittest.TestCase):
    def test_series_sum(self):
        self.assertAlmostEqual(
            ma.series_failure_rate([1e-5, 2e-5, 3e-5]), 6e-5, places=12
        )

    def test_series_single(self):
        self.assertAlmostEqual(ma.series_failure_rate([4e-5]), 4e-5, places=12)

    def test_redundancy_mttf_anchors(self):
        self.assertAlmostEqual(ma.redundancy_mttf(2, 1e-4), 15000.0, places=6)
        self.assertAlmostEqual(ma.redundancy_mttf(3, 1e-4), 18333.333333, delta=1e-3)

    def test_redundancy_mttf_improvement(self):
        # Two-unit redundancy must improve on the single unit by 1.5x.
        single = ma.mttf_exponential(1e-4)
        dual = ma.redundancy_mttf(2, 1e-4)
        self.assertAlmostEqual(dual / single, 1.5, places=12)

    def test_k_of_n_anchors(self):
        self.assertAlmostEqual(ma.k_of_n_reliability(3, 2, 0.9), 0.972, places=12)
        self.assertAlmostEqual(ma.k_of_n_reliability(2, 2, 0.9), 0.81, places=12)
        self.assertAlmostEqual(ma.k_of_n_reliability(2, 1, 0.9), 0.99, places=12)

    def test_k_of_n_all_units(self):
        self.assertAlmostEqual(ma.k_of_n_reliability(4, 4, 0.8), 0.8**4, places=12)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ma.series_failure_rate([])
        with self.assertRaises(ValueError):
            ma.series_failure_rate([-1e-5])
        with self.assertRaises(ValueError):
            ma.redundancy_mttf(0, 1e-4)
        with self.assertRaises(ValueError):
            ma.redundancy_mttf(2, 0.0)
        with self.assertRaises(ValueError):
            ma.k_of_n_reliability(2, 3, 0.9)
        with self.assertRaises(ValueError):
            ma.k_of_n_reliability(3, 2, 1.5)
        with self.assertRaises(ValueError):
            ma.k_of_n_reliability(3, 0, 0.9)


class StateProbabilityTest(unittest.TestCase):
    def test_two_unit_redundancy_closed_form(self):
        # States: 2 units up, 1 unit up, 0 units up; exit rates 2*lam, lam.
        lam = 1e-4
        rates = [[0.0, 2.0 * lam, 0.0], [0.0, 0.0, lam], [0.0, 0.0, 0.0]]
        p = ma.state_probabilities(rates, 10000.0)
        e1 = math.exp(-1.0)
        e2 = math.exp(-2.0)
        self.assertAlmostEqual(p[0], e2, places=6)
        self.assertAlmostEqual(p[1], 2.0 * (e1 - e2), places=6)
        self.assertAlmostEqual(p[2], (1.0 - e1) ** 2, places=6)
        self.assertAlmostEqual(sum(p), 1.0, places=6)

    def test_matches_two_state_closed_form(self):
        # Repairable two-state chain solved numerically matches the
        # analytic availability at the same time.
        lam, mu, t = 1e-4, 1e-2, 1000.0
        rates = [[0.0, lam], [mu, 0.0]]
        p = ma.state_probabilities(rates, t, initial=[1.0, 0.0])
        p_ok, p_failed = ma.two_state_availability(lam, mu, t)
        self.assertAlmostEqual(p[0], p_ok, places=9)
        self.assertAlmostEqual(p[1], p_failed, places=9)

    def test_no_transition_chain(self):
        # Zero rates leave the chain in the initial state.
        p = ma.state_probabilities([[0.0, 0.0], [0.0, 0.0]], 5000.0)
        self.assertAlmostEqual(p[0], 1.0, places=12)
        self.assertAlmostEqual(p[1], 0.0, places=12)

    def test_probability_conservation(self):
        lam, mu, t = 3e-5, 2e-4, 2000.0
        rates = [[0.0, lam], [mu, 0.0]]
        p = ma.state_probabilities(rates, t, initial=[0.7, 0.3])
        self.assertAlmostEqual(sum(p), 1.0, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ma.state_probabilities([], 100.0)
        with self.assertRaises(ValueError):
            ma.state_probabilities([[0.0, 1e-4]], 100.0)  # not square
        with self.assertRaises(ValueError):
            ma.state_probabilities([[0.0, 1e-4], [1e-2, 0.0]], -1.0)
        with self.assertRaises(ValueError):
            ma.state_probabilities(
                [[0.0, 1e-4], [1e-2, 0.0]], 100.0, initial=[0.5, 0.6]
            )
        with self.assertRaises(ValueError):
            ma.state_probabilities(
                [[0.0, 1e-4], [1e-2, 0.0]], 100.0, initial=[0.5]
            )
        with self.assertRaises(ValueError):
            ma.state_probabilities(
                [[0.0, -1e-4], [1e-2, 0.0]], 100.0
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
