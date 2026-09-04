#!/usr/bin/env python3
"""Gate 3 contract test: pointing error budget logic.

Exercises scripts/pointing_error_budget_logic.py (stdlib unittest,
offline, deterministic). Contract: docs/harness-contract.md gate 3 -
RSS combination of independent 1-sigma error contributors, 3-sigma
conversion and requirement verdict, allocation of the remaining budget
to one not-yet-sized contributor, and dominant source ranking by
variance share.

Known values (independently verified at wave-34 prep): the reference
ADCS chain [3, 2, 25, 8, 5] arcsec 1-sigma (star tracker determination
noise, gyro propagation, control deadband, jitter, thermal distortion)
gives rss = sqrt(727) = 26.962938 arcsec, 3-sigma = 80.888813 arcsec,
verdict True against a 90 arcsec 3-sigma requirement, allocation
sqrt(798) = 28.248894 arcsec for the control deadband with the other
four fixed, and the control deadband dominant with variance share
625/727 = 86.0%. The [1, 100] case returns index 1 with share 99.99%.
"""

import math
import unittest

from pointing_error_budget_logic import (
    rss_pointing_error,
    three_sigma_error,
    three_sigma_verdict,
    allocate_error_budget,
    dominant_error_source,
    pointing_error_budget,
)

CHAIN = [3, 2, 25, 8, 5]  # reference ADCS 1-sigma chain, arcsec
REQUIREMENT = 90.0        # 3-sigma pointing requirement, arcsec


class TestRssPointingError(unittest.TestCase):
    def test_worked_example_rss(self):
        value = rss_pointing_error(CHAIN)
        self.assertAlmostEqual(value, 26.962938, delta=1e-6)
        self.assertAlmostEqual(value, math.sqrt(727.0), delta=1e-12)

    def test_single_component_returns_itself(self):
        self.assertEqual(rss_pointing_error([7.0]), 7.0)

    def test_zero_component_does_not_change_rss(self):
        base = rss_pointing_error(CHAIN)
        self.assertAlmostEqual(rss_pointing_error(CHAIN + [0.0]), base, delta=1e-12)
        self.assertAlmostEqual(rss_pointing_error([0.0] + CHAIN), base, delta=1e-12)

    def test_rss_order_invariance(self):
        shuffled = [5, 3, 25, 2, 8]
        self.assertAlmostEqual(
            rss_pointing_error(shuffled), rss_pointing_error(CHAIN), delta=1e-12
        )

    def test_rss_identity_equal_component_raises_total_by_sqrt2(self):
        others = [3.0, 4.0]  # rss = 5.0
        total = rss_pointing_error(others + [5.0])
        self.assertAlmostEqual(total, 5.0 * math.sqrt(2.0), delta=1e-12)

    def test_empty_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            rss_pointing_error([])

    def test_negative_component_raises_value_error(self):
        with self.assertRaises(ValueError):
            rss_pointing_error([3.0, -1.0, 25.0])
        with self.assertRaises(ValueError):
            rss_pointing_error({"gyro": 2.0, "deadband": -0.5})

class TestThreeSigma(unittest.TestCase):
    def test_three_sigma_worked_example(self):
        value = three_sigma_error(CHAIN)
        self.assertAlmostEqual(value, 80.888813, delta=1e-6)

    def test_three_sigma_is_exactly_three_times_rss(self):
        self.assertEqual(three_sigma_error(CHAIN), 3.0 * rss_pointing_error(CHAIN))

    def test_three_sigma_empty_raises(self):
        with self.assertRaises(ValueError):
            three_sigma_error([])


class TestThreeSigmaVerdict(unittest.TestCase):
    def test_worked_example_requirement_met(self):
        self.assertTrue(three_sigma_verdict(CHAIN, REQUIREMENT))

    def test_verdict_boundary_equal_requirement_is_true(self):
        # [3, 4] rss 5, 3-sigma 15; requirement exactly 15 passes.
        self.assertTrue(three_sigma_verdict([3.0, 4.0], 15.0))

    def test_verdict_fails_when_requirement_strictly_below(self):
        self.assertFalse(three_sigma_verdict(CHAIN, 80.0))

    def test_verdict_rejects_zero_requirement(self):
        with self.assertRaises(ValueError):
            three_sigma_verdict(CHAIN, 0.0)

    def test_verdict_rejects_negative_requirement(self):
        with self.assertRaises(ValueError):
            three_sigma_verdict(CHAIN, -10.0)


class TestAllocateErrorBudget(unittest.TestCase):
    def test_worked_example_control_deadband_budget(self):
        value = allocate_error_budget(90.0, [3.0, 2.0, 8.0, 5.0])
        self.assertAlmostEqual(value, 28.248894, delta=1e-6)
        self.assertGreater(value, 25.0)  # exceeds the 25 arcsec actual deadband

    def test_empty_fixed_returns_full_one_sigma_budget(self):
        self.assertAlmostEqual(allocate_error_budget(90.0, []), 30.0, delta=1e-12)

    def test_allocation_boundary_zero_radicand(self):
        # Fixed [3, 4] rss 5 equals 15/3, radicand zero, budget zero.
        value = allocate_error_budget(15.0, [3.0, 4.0])
        self.assertAlmostEqual(value, 0.0, delta=1e-12)

    def test_negative_radicand_raises(self):
        with self.assertRaises(ValueError):
            allocate_error_budget(6.0, [3.0, 4.0])  # 1-sigma budget 2 < 5

    def test_full_chain_fixed_against_tight_requirement_raises(self):
        with self.assertRaises(ValueError):
            allocate_error_budget(30.0, CHAIN)  # 1-sigma budget 10 < 26.96

    def test_allocation_monotonic_in_requirement(self):
        fixed = [3.0, 2.0, 8.0, 5.0]
        high = allocate_error_budget(120.0, fixed)
        mid = allocate_error_budget(90.0, fixed)
        low = allocate_error_budget(45.0, fixed)
        self.assertGreater(high, mid)
        self.assertGreater(mid, low)
        self.assertGreater(low, 0.0)

    def test_allocation_rejects_nonpositive_requirement(self):
        with self.assertRaises(ValueError):
            allocate_error_budget(0.0, [3.0, 4.0])
        with self.assertRaises(ValueError):
            allocate_error_budget(-5.0, [3.0, 4.0])


class TestDominantErrorSource(unittest.TestCase):
    def test_worked_example_control_deadband_dominant(self):
        index, name, share = dominant_error_source(CHAIN)
        self.assertEqual(index, 2)
        self.assertIsNone(name)
        self.assertAlmostEqual(share, 625.0 / 727.0, delta=1e-9)
        self.assertEqual(round(share * 100.0, 1), 86.0)

    def test_two_component_large_second_dominant(self):
        index, name, share = dominant_error_source([1.0, 100.0])
        self.assertEqual(index, 1)
        self.assertIsNone(name)
        self.assertAlmostEqual(share, 10000.0 / 10001.0, delta=1e-9)
        self.assertEqual(round(share * 100.0, 2), 99.99)

    def test_dict_input_returns_name(self):
        named = {"determination": 3, "gyro": 2, "deadband": 25, "jitter": 8, "thermal": 5}
        index, name, share = dominant_error_source(named)
        self.assertEqual(index, 2)
        self.assertEqual(name, "deadband")
        self.assertAlmostEqual(share, 625.0 / 727.0, delta=1e-9)

    def test_variance_tie_returns_first_in_order(self):
        index, name, share = dominant_error_source([2.0, 2.0])
        self.assertEqual(index, 0)
        self.assertAlmostEqual(share, 0.5, delta=1e-12)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            dominant_error_source([])

    def test_all_zero_raises(self):
        with self.assertRaises(ValueError):
            dominant_error_source([0.0, 0.0])


class TestPointingErrorBudgetConvenience(unittest.TestCase):
    def test_budget_dict_worked_example(self):
        budget = pointing_error_budget(CHAIN, REQUIREMENT)
        self.assertAlmostEqual(budget["rss_1sigma"], 26.962938, delta=1e-6)
        self.assertAlmostEqual(budget["rss_3sigma"], 80.888813, delta=1e-6)
        self.assertTrue(budget["requirement_met"])
        self.assertEqual(budget["dominant_index"], 2)
        self.assertAlmostEqual(
            budget["dominant_variance_share"], 625.0 / 727.0, delta=1e-9
        )

    def test_budget_dict_keys_exactly_as_documented(self):
        budget = pointing_error_budget(CHAIN, REQUIREMENT)
        self.assertEqual(
            set(budget.keys()),
            {
                "rss_1sigma",
                "rss_3sigma",
                "requirement_met",
                "dominant_index",
                "dominant_variance_share",
                "component_variance_shares",
            },
        )

    def test_dominant_share_matches_shares_list_entry(self):
        budget = pointing_error_budget(CHAIN, REQUIREMENT)
        shares = budget["component_variance_shares"]
        self.assertAlmostEqual(
            budget["dominant_variance_share"], shares[budget["dominant_index"]],
            delta=1e-12,
        )

    def test_component_variance_shares_sum_to_one(self):
        budget = pointing_error_budget(CHAIN, REQUIREMENT)
        self.assertAlmostEqual(sum(budget["component_variance_shares"]), 1.0, delta=1e-9)
        # [3, 4] case: shares 9/25 and 16/25 in input order.
        small = pointing_error_budget([3.0, 4.0], 15.0)
        self.assertAlmostEqual(small["component_variance_shares"][0], 9.0 / 25.0)
        self.assertAlmostEqual(small["component_variance_shares"][1], 16.0 / 25.0)

    def test_budget_rejects_nonphysical_inputs(self):
        with self.assertRaises(ValueError):
            pointing_error_budget([], REQUIREMENT)
        with self.assertRaises(ValueError):
            pointing_error_budget([3.0, -2.0], REQUIREMENT)
        with self.assertRaises(ValueError):
            pointing_error_budget(CHAIN, 0.0)

    def test_determinism_run_to_run(self):
        first = pointing_error_budget(CHAIN, REQUIREMENT)
        second = pointing_error_budget(CHAIN, REQUIREMENT)
        self.assertEqual(first, second)
        self.assertEqual(first["component_variance_shares"], second["component_variance_shares"])


if __name__ == "__main__":
    unittest.main()
