"""Contract test for the reliability-allocation leaf
(systems-engineering-safety/arp4761a/reliability-allocation).

Exercises the SKILL.md workflow end to end: step 1 fixing the
top-level reliability budget, step 2 choosing the apportionment
scheme (equal split or complexity-weighted apportionment), step 3
producing the per-item failure-rate and MTBF targets, step 4
verifying the series-sum closure, step 5 reporting the capability
margins, and step 6 recording the targets in the item development
specifications. Deterministic and offline; stdlib only.

All numeric assertions are tolerance-based (assertAlmostEqual /
math.isclose); no exact equality is asserted on computed sums or
products.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import reliability_allocation_logic as ra

SYSTEM_RATE = 1e-4
WEIGHTS = [1, 2, 1, 3, 2, 1]
CAPABILITIES = [9e-6, 1.6e-5, 1.2e-5, 2.8e-5, 1.8e-5, 1.1e-5]


class TestMtbfConversion(unittest.TestCase):
    """Step 1 of the SKILL.md workflow, fixing the top-level budget,
    and step 3, producing the MTBF targets, use mtbf_to_rate."""

    def test_mtbf_to_rate_of_10000_hour_target_is_system_rate(self):
        """Step 1: the 10000 h MTBF system target enters the flow-down
        as the system rate 1e-4 per flight hour."""
        self.assertAlmostEqual(ra.mtbf_to_rate(10000.0), 1e-4, delta=1e-15)

    def test_mtbf_rate_round_trip_product_is_one(self):
        """Step 1 round trip: rate times the original MTBF is 1.0."""
        mtbf = 10000.0
        product = ra.mtbf_to_rate(mtbf) * mtbf
        self.assertAlmostEqual(product, 1.0, delta=1e-12)

    def test_mtbf_reciprocal_of_item_rate_is_33333_hours(self):
        """Step 3: the computer item rate 3e-05 per flight hour is an
        MTBF target of 33333.3 h, the reciprocal rounding to display
        precision."""
        self.assertTrue(math.isclose(1.0 / 3e-5, 100000.0 / 3.0,
                                     rel_tol=1e-9, abs_tol=1e-9))

    def test_mtbf_to_rate_rejects_zero(self):
        """A zero MTBF is not a positive number and raises
        ValueError."""
        with self.assertRaises(ValueError):
            ra.mtbf_to_rate(0.0)

    def test_mtbf_to_rate_rejects_negative_and_non_numeric(self):
        """Negative and non-numeric MTBF inputs are rejected."""
        for bad in (-1.0, -1e4, "10000"):
            with self.assertRaises(ValueError):
                ra.mtbf_to_rate(bad)


class TestEqualSplit(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, choosing equal split as the
    apportionment scheme for the flap actuation system items."""

    def test_equal_split_six_items_share_of_flap_system_rate(self):
        """Step 2: equal split of the 1e-4 system rate across six
        items gives six identical shares near 1.6666666666666668e-05
        per flight hour."""
        shares = ra.equal_split(SYSTEM_RATE, 6)
        self.assertEqual(len(shares), 6)
        for share in shares:
            self.assertAlmostEqual(share, 1.6666666666666668e-05,
                                   delta=1e-15)
            self.assertAlmostEqual(share, SYSTEM_RATE / 6.0, delta=1e-15)

    def test_equal_split_item_mtbf_target_is_60000_hours(self):
        """Step 3: the per-item MTBF target of the equal split is
        60000 h, the reciprocal of the item share."""
        share = ra.equal_split(SYSTEM_RATE, 6)[0]
        self.assertAlmostEqual(1.0 / share, 60000.0, delta=1e-9)

    def test_equal_split_closure_relative_error_at_float_noise(self):
        """Step 4: the series-sum closure of the equal split returns a
        total at the system rate with relative error at float noise
        (0.0 to 1.4e-16 depending on the interpreter summation
        algorithm, naive vs Neumaier), and the exact flag True."""
        result = ra.closure_check(ra.equal_split(SYSTEM_RATE, 6),
                                  SYSTEM_RATE)
        self.assertLess(abs(result["relative_error"]), 1e-14)
        self.assertLess(abs(result["relative_error"]), 1e-15)
        self.assertTrue(result["exact"])
        self.assertAlmostEqual(result["total"], SYSTEM_RATE, delta=1e-18)

    def test_equal_split_single_item_returns_system_rate(self):
        """Step 2 boundary: one item takes the whole system rate."""
        self.assertAlmostEqual(ra.equal_split(SYSTEM_RATE, 1)[0],
                               SYSTEM_RATE, delta=1e-15)

    def test_equal_split_max_items_64_runs_and_closes(self):
        """Step 2 boundary: the ITEMS_MAX 64-item split runs and the
        allocated item rates still sum to the system rate."""
        shares = ra.equal_split(5e-5, 64)
        self.assertEqual(len(shares), 64)
        result = ra.closure_check(shares, 5e-5)
        self.assertTrue(result["exact"])
        self.assertAlmostEqual(result["relative_error"], 0.0, delta=1e-12)

    def test_equal_split_rejects_nonpositive_system_rate(self):
        """A non-positive system rate cannot seed an apportionment."""
        for bad in (0.0, -1e-4):
            with self.assertRaises(ValueError):
                ra.equal_split(bad, 6)

    def test_equal_split_rejects_invalid_item_counts(self):
        """Item counts of zero, above ITEMS_MAX and non-integer values
        are rejected."""
        for bad in (0, 65, 2.5):
            with self.assertRaises(ValueError):
                ra.equal_split(SYSTEM_RATE, bad)


class TestComplexityWeightedAllocation(unittest.TestCase):
    """Step 2 of the SKILL.md workflow, choosing complexity-weighted
    apportionment with design-team complexity weights, and step 3
    producing the per-item target rates."""

    def test_weighted_flap_system_target_rates(self):
        """Step 2: the weighted split of the 1e-4 system rate over the
        six flap actuation items with weights [1, 2, 1, 3, 2, 1] gives
        the target rates [1e-05, 2e-05, 1e-05, 3e-05, 2e-05, 1e-05]
        per flight hour."""
        rates = ra.complexity_weighted_alloc(SYSTEM_RATE, WEIGHTS)
        expected = [1e-5, 2e-5, 1e-5, 3e-5, 2e-5, 1e-5]
        self.assertEqual(len(rates), len(expected))
        for actual, want in zip(rates, expected):
            self.assertAlmostEqual(actual, want, delta=1e-15)

    def test_weighted_closure_is_exact_at_system_rate(self):
        """Step 4: the normalized weighted split sums to the system
        rate, relative error at float noise (within 1e-15 under any
        interpreter summation algorithm) and exact flag True."""
        result = ra.closure_check(
            ra.complexity_weighted_alloc(SYSTEM_RATE, WEIGHTS),
            SYSTEM_RATE)
        self.assertLess(abs(result["relative_error"]), 1e-15)
        self.assertTrue(result["exact"])
        self.assertAlmostEqual(result["total"], SYSTEM_RATE, delta=1e-18)

    def test_weighted_share_identity_matches_weight_ratio(self):
        """Step 2 identity: every share equals the system rate times
        its weight over the weight sum, rate_i = 1e-4 x w_i / 10."""
        rates = ra.complexity_weighted_alloc(SYSTEM_RATE, WEIGHTS)
        weight_sum = float(sum(WEIGHTS))
        for rate, w in zip(rates, WEIGHTS):
            self.assertAlmostEqual(rate,
                                   SYSTEM_RATE * w / weight_sum,
                                   delta=1e-15)

    def test_weighted_computer_carries_largest_budget(self):
        """Step 2: the dual-redundant computer, weight 3, carries the
        largest item budget, 3e-05 per flight hour, above every other
        share."""
        rates = ra.complexity_weighted_alloc(SYSTEM_RATE, WEIGHTS)
        self.assertAlmostEqual(rates[3], 3e-5, delta=1e-15)
        for i, rate in enumerate(rates):
            if i != 3:
                self.assertLess(rate, rates[3])

    def test_weighted_computer_mtbf_target_is_33333_hours(self):
        """Step 3: the computer budget 3e-05 per flight hour is an
        MTBF target of 33333.3 h, the reciprocal rounding to display
        precision."""
        rates = ra.complexity_weighted_alloc(SYSTEM_RATE, WEIGHTS)
        self.assertTrue(math.isclose(1.0 / rates[3], 100000.0 / 3.0,
                                     rel_tol=1e-9, abs_tol=1e-9))

    def test_weighted_single_item_returns_system_rate(self):
        """Step 2 boundary: a single item with any positive weight
        receives the whole system rate."""
        rate = ra.complexity_weighted_alloc(SYSTEM_RATE, [7])[0]
        self.assertAlmostEqual(rate, SYSTEM_RATE, delta=1e-15)

    def test_weighted_rejects_nonpositive_system_rate(self):
        """A non-positive system rate cannot seed a weighted
        apportionment."""
        for bad in (0.0, -1e-4):
            with self.assertRaises(ValueError):
                ra.complexity_weighted_alloc(bad, WEIGHTS)

    def test_weighted_rejects_empty_and_nonpositive_weights(self):
        """Empty weights and weights of zero or below are rejected."""
        for bad in ([], [0], [-1], [1, 2, -1]):
            with self.assertRaises(ValueError):
                ra.complexity_weighted_alloc(SYSTEM_RATE, bad)

    def test_weighted_rejects_more_than_max_weights(self):
        """More than ITEMS_MAX weights are rejected."""
        with self.assertRaises(ValueError):
            ra.complexity_weighted_alloc(SYSTEM_RATE, [1] * 65)


class TestClosureCheck(unittest.TestCase):
    """Step 4 of the SKILL.md workflow, verifying the series-sum
    closure of the allocated item budgets against the system rate."""

    def test_closure_identity_for_arbitrary_positive_weights(self):
        """Step 4 identity: for any positive weights and positive
        system rate the weighted allocation closes with exact True."""
        weight_sets = [[1], [1, 2, 1], [1, 2, 1, 3, 2, 1],
                       [7, 3, 10, 2, 4, 8, 1, 1, 5, 3]]
        for rate in (1e-4, 2e-3, 5e-6):
            for weights in weight_sets:
                result = ra.closure_check(
                    ra.complexity_weighted_alloc(rate, weights), rate)
                self.assertTrue(result["exact"])
                self.assertAlmostEqual(result["relative_error"], 0.0,
                                       delta=1e-9)
                self.assertAlmostEqual(result["total"], rate,
                                       delta=rate * 1e-9 + 1e-15)

    def test_closure_relative_error_reports_drift(self):
        """Step 4: budgets summing to 9e-05 against a 1e-4 system
        rate report a negative 10% relative error and exact False."""
        result = ra.closure_check([3e-5, 3e-5, 3e-5], SYSTEM_RATE)
        self.assertAlmostEqual(result["total"], 9e-5, delta=1e-15)
        self.assertAlmostEqual(result["relative_error"], -0.1, delta=1e-12)
        self.assertFalse(result["exact"])

    def test_closure_rejects_empty_item_rates(self):
        """An empty item rate list cannot close against anything."""
        with self.assertRaises(ValueError):
            ra.closure_check([], SYSTEM_RATE)

    def test_closure_rejects_nonpositive_item_and_system_rate(self):
        """Item rates of zero or below and a non-positive system rate
        are rejected."""
        for bad in ([0.0], [-1e-5], [1e-5, -1e-5]):
            with self.assertRaises(ValueError):
                ra.closure_check(bad, SYSTEM_RATE)
        for bad in (0.0, -1e-4):
            with self.assertRaises(ValueError):
                ra.closure_check([1e-5], bad)


class TestMarginReport(unittest.TestCase):
    """Step 5 of the SKILL.md workflow, reporting the capability
    margins of the item budgets against predicted capability rates."""

    def test_margin_report_flap_system_example(self):
        """Step 5: against the six predicted capability rates the
        weighted flap system margins are -0.1, -0.2, +0.2, -0.0667,
        -0.1, +0.1, with keys and input order preserved."""
        report = ra.margin_report(
            ra.complexity_weighted_alloc(SYSTEM_RATE, WEIGHTS),
            CAPABILITIES)
        self.assertEqual(len(report), 6)
        expected_margins = [-0.1, -0.2, 0.2, -2.0 / 30.0, -0.1, 0.1]
        for rec, want, i in zip(report, expected_margins, range(6)):
            self.assertEqual(sorted(rec.keys()),
                             ["capability", "item", "margin", "target"])
            self.assertEqual(rec["item"], i)
            self.assertAlmostEqual(rec["margin"], want, delta=1e-9)

    def test_margin_identity_is_capability_over_target_minus_one(self):
        """Step 5 identity: the margin is exactly capability / target
        minus 1.0 for every item."""
        report = ra.margin_report(
            ra.complexity_weighted_alloc(SYSTEM_RATE, WEIGHTS),
            CAPABILITIES)
        for rec, capability in zip(report, CAPABILITIES):
            self.assertTrue(math.isclose(
                rec["margin"], capability / rec["target"] - 1.0,
                rel_tol=1e-12, abs_tol=1e-15))

    def test_margin_zero_when_capability_equals_target(self):
        """Step 5: a capability rate equal to the budget gives a zero
        margin, neither slack nor deficit."""
        rates = ra.equal_split(SYSTEM_RATE, 2)
        report = ra.margin_report(rates, list(rates))
        for rec in report:
            self.assertAlmostEqual(rec["margin"], 0.0, delta=1e-15)

    def test_margin_sign_semantics_slack_and_deficit(self):
        """Step 5: a capability below the budget is negative margin,
        slack, and a capability above the budget is positive margin,
        deficit."""
        report = ra.margin_report([1e-5, 1e-5], [9e-6, 1.1e-5])
        self.assertLess(report[0]["margin"], 0.0)
        self.assertGreater(report[1]["margin"], 0.0)

    def test_margin_capability_sum_below_system_rate_holds_headroom(self):
        """Step 5: the predicted capability rates sum to 9.4e-05,
        below the 1e-4 system rate, so the item predictions still
        close at system level with headroom."""
        total_capability = float(sum(CAPABILITIES))
        self.assertAlmostEqual(total_capability, 9.4e-5, delta=1e-15)
        self.assertLess(total_capability, SYSTEM_RATE)

    def test_margin_report_rejects_invalid_inputs(self):
        """Step 5: empty lists, mismatched lengths and non-positive
        entries are rejected."""
        for rates, caps in (([], [1e-5]), ([1e-5], []),
                            ([1e-5, 2e-5], [1e-5]),
                            ([0.0], [1e-5]), ([1e-5], [-1e-5])):
            with self.assertRaises(ValueError):
                ra.margin_report(rates, caps)


class TestDevelopmentSpecificationRecord(unittest.TestCase):
    """Step 6 of the SKILL.md workflow, recording the per-item
    failure-rate and MTBF targets in the item development
    specifications."""

    def test_six_item_targets_recorded_for_development_specifications(self):
        """Step 6: the weighted flap system flow-down yields six item
        records, each with a positive failure-rate target and the
        matching MTBF target for its development specification."""
        rates = ra.complexity_weighted_alloc(SYSTEM_RATE, WEIGHTS)
        records = [{"item": i, "rate": rates[i],
                    "mtbf": ra.mtbf_to_rate(rates[i])}
                   for i in range(len(rates))]
        self.assertEqual(len(records), 6)
        for rec in records:
            self.assertGreater(rec["rate"], 0.0)
            self.assertGreater(rec["mtbf"], 0.0)
            self.assertAlmostEqual(rec["rate"] * rec["mtbf"], 1.0,
                                   delta=1e-12)


class TestDeterminism(unittest.TestCase):
    """The workflow is deterministic: repeated calls return equal
    structures with stable floats."""

    def test_repeated_calls_return_equal_structures(self):
        """Equal split and weighted apportionment calls are stable
        across repeats, so the flow-down numbers do not drift between
        runs."""
        first = ra.complexity_weighted_alloc(SYSTEM_RATE, WEIGHTS)
        second = ra.complexity_weighted_alloc(SYSTEM_RATE, WEIGHTS)
        for a, b in zip(first, second):
            self.assertTrue(math.isclose(a, b, rel_tol=0.0, abs_tol=0.0))
        equal_first = ra.equal_split(SYSTEM_RATE, 6)
        equal_second = ra.equal_split(SYSTEM_RATE, 6)
        self.assertEqual(equal_first, equal_second)


if __name__ == "__main__":
    unittest.main()
