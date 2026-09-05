"""Contract test for the fisher-exact-test logic module.

Deterministic, offline, stdlib only. Run with:
    python3 test_fisher_exact_test.py
Anchors come from the wave-38 spec worked example, table [[2, 6],
[5, 1]] with margins 8/6 rows and 7/7 columns, n = 14 (prep-verified):
p_obs 0.048951, direction low (odds ratio 0.0667), p_one_tail
P(a' <= 2) = 0.051282, p_two_tail (all table probabilities <= p_obs)
0.102564, seven feasible tables with a' = 1..7, minimum expected cell
count 3.0 (bottom-row cells carry 6*7/14; the top row carries 8*7/14 =
4.0), verdict exact-test-recommended. The assert targets below are the
real module outputs, checked against the prep-verified bounds.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fisher_exact_test_logic as fet


class TestHypergeometricP(unittest.TestCase):
    def test_worked_example_p_obs(self):
        # P(2) = C(8,2) * C(6,5) / C(14,7) = 168 / 3432.
        p = fet.hypergeometric_p(2, 6, 5, 1)
        self.assertAlmostEqual(p, 0.048951, delta=1e-6)
        self.assertEqual(p, 168 / 3432)

    def test_worked_example_pmf_sums_to_one(self):
        total = sum(
            fet.hypergeometric_p(ap, bp, cp, dp)
            for ap, bp, cp, dp in fet.enumerate_tables(2, 6, 5, 1)
        )
        self.assertAlmostEqual(total, 1.0, delta=1e-12)

    def test_degenerate_margin_table_probability_is_one(self):
        # Row margin a+b = 0 forces a single table, P = C(0,0)*C(8,5)/C(8,5).
        self.assertEqual(fet.hypergeometric_p(0, 0, 5, 3), 1.0)

    def test_mirror_tables_have_equal_probability(self):
        # (6, 2, 1, 5) has the same margins as (2, 6, 5, 1) and the
        # mirrored top-left count; both numerators are 28 * 6.
        self.assertEqual(fet.hypergeometric_p(2, 6, 5, 1),
                         fet.hypergeometric_p(6, 2, 1, 5))

    def test_negative_cell_rejected(self):
        for table in ((2, -1, 5, 1), (-1, 6, 5, 1), (2, 6, -5, 1),
                      (2, 6, 5, -1)):
            with self.assertRaises(ValueError):
                fet.hypergeometric_p(*table)


class TestEnumerateTables(unittest.TestCase):
    def test_worked_example_seven_tables_a_range(self):
        tables = fet.enumerate_tables(2, 6, 5, 1)
        self.assertEqual(len(tables), 7)
        self.assertEqual([t[0] for t in tables], [1, 2, 3, 4, 5, 6, 7])

    def test_worked_example_margins_preserved(self):
        for ap, bp, cp, dp in fet.enumerate_tables(2, 6, 5, 1):
            self.assertEqual((ap + bp, cp + dp), (8, 6))
            self.assertEqual((ap + cp, bp + dp), (7, 7))

    def test_single_table_when_column_margin_zero(self):
        # a + c = 0 forces a' = 0 as the only feasible table.
        self.assertEqual(fet.enumerate_tables(0, 5, 0, 5), [(0, 5, 0, 5)])

    def test_lower_bound_reaches_zero(self):
        # a' range max(0, 7 - 8) = 0 to min(6, 7) = 6.
        tables = fet.enumerate_tables(0, 6, 7, 1)
        self.assertEqual(len(tables), 7)
        self.assertEqual(tables[0][0], 0)
        self.assertEqual(tables[-1][0], 6)

    def test_negative_cell_rejected(self):
        with self.assertRaises(ValueError):
            fet.enumerate_tables(2, -6, 5, 1)


class TestOddsRatio(unittest.TestCase):
    def test_worked_example_odds_ratio(self):
        # (2*1) / (6*5) = 0.06667, no zero cells so no correction.
        self.assertAlmostEqual(fet.odds_ratio(2, 6, 5, 1), 0.066667, delta=1e-4)
        self.assertEqual(fet.odds_ratio(2, 6, 5, 1), 2 / 30)

    def test_identity_table_odds_ratio_is_one(self):
        self.assertEqual(fet.odds_ratio(2, 2, 2, 2), 1.0)

    def test_balanced_product_odds_ratio_is_one(self):
        # a*d = 4 equals b*c = 4, so the ratio is exactly 1.0.
        self.assertEqual(fet.odds_ratio(1, 2, 2, 4), 1.0)

    def test_zero_top_left_cell_haldane_correction(self):
        # a = 0 forces +0.5 on every cell:
        # (0.5 * 1.5) / (10.5 * 5.5) = 0.75 / 57.75.
        expected = (0.5 * 1.5) / (10.5 * 5.5)
        self.assertAlmostEqual(fet.odds_ratio(0, 10, 5, 1), expected, delta=1e-9)

    def test_zero_diagonal_cells_haldane_correction(self):
        # a = d = 0: (0.5 * 0.5) / (5.5 * 5.5) = 0.25 / 30.25.
        expected = (0.5 * 0.5) / (5.5 * 5.5)
        self.assertAlmostEqual(fet.odds_ratio(0, 5, 5, 0), expected, delta=1e-9)

    def test_negative_cell_rejected(self):
        with self.assertRaises(ValueError):
            fet.odds_ratio(2, 6, 5, -1)


class TestSmallCountVerdict(unittest.TestCase):
    def test_worked_example_min_expected_recommends_exact(self):
        # Expected cells: 8*7/14 = 4.0 (top row), 6*7/14 = 3.0 (bottom
        # row); the minimum is 3.0, below 5, verdict exact-test-
        # recommended.
        result = fet.small_count_verdict(2, 6, 5, 1)
        self.assertEqual(result["min_expected"], 3.0)
        self.assertEqual(result["verdict"], "exact-test-recommended")

    def test_large_count_table_adequate(self):
        result = fet.small_count_verdict(40, 60, 60, 40)
        self.assertEqual(result["min_expected"], 50.0)
        self.assertEqual(result["verdict"], "chi-square-adequate")

    def test_balanced_small_table_recommended(self):
        result = fet.small_count_verdict(1, 1, 1, 1)
        self.assertEqual(result["min_expected"], 1.0)
        self.assertEqual(result["verdict"], "exact-test-recommended")

    def test_min_expected_matches_cellwise_formula(self):
        # min over the four cells of row_total * col_total / n.
        expected_min = min(8 * 7, 8 * 7, 6 * 7, 6 * 7) / 14
        self.assertEqual(fet.small_count_verdict(2, 6, 5, 1)["min_expected"],
                         expected_min)

    def test_nonpositive_total_rejected(self):
        with self.assertRaises(ValueError):
            fet.small_count_verdict(0, 0, 0, 0)

    def test_negative_cell_rejected(self):
        with self.assertRaises(ValueError):
            fet.small_count_verdict(2, 6, -5, 1)


class TestFisherExactPValue(unittest.TestCase):
    def test_worked_example_one_tail(self):
        # Low direction (OR < 1): P(a' <= 2) = 0.002331 + 0.048951.
        self.assertAlmostEqual(
            fet.fisher_exact_p_value(2, 6, 5, 1)["p_one_tail"],
            0.051282, delta=1e-4)

    def test_worked_example_two_tail(self):
        # All tables with probability <= p_obs: a' in {1, 2, 6, 7}.
        self.assertAlmostEqual(
            fet.fisher_exact_p_value(2, 6, 5, 1)["p_two_tail"],
            0.102564, delta=1e-4)

    def test_worked_example_direction_low(self):
        self.assertEqual(fet.fisher_exact_p_value(2, 6, 5, 1)["direction"],
                         "low")

    def test_mirror_table_direction_high(self):
        # [[6, 2], [1, 5]] has OR 15 > 1; one tail sums a' >= 6.
        result = fet.fisher_exact_p_value(6, 2, 1, 5)
        self.assertEqual(result["direction"], "high")
        self.assertAlmostEqual(result["p_one_tail"], 0.051282, delta=1e-4)
        self.assertAlmostEqual(result["p_two_tail"], 0.102564, delta=1e-4)

    def test_identity_table_symmetric(self):
        # [[2, 2], [2, 2]]: odds ratio 1.0, both tail directions give
        # the same sum 53/70 and direction is symmetric.
        result = fet.fisher_exact_p_value(2, 2, 2, 2)
        self.assertEqual(result["direction"], "symmetric")
        self.assertAlmostEqual(result["p_one_tail"], 53 / 70, delta=1e-12)
        self.assertAlmostEqual(result["p_two_tail"], 1.0, delta=1e-12)

    def test_two_tailed_at_least_one_tailed(self):
        for table in ((2, 6, 5, 1), (6, 2, 1, 5), (2, 2, 2, 2), (5, 0, 0, 5),
                      (0, 10, 10, 0), (3, 2, 1, 4), (4, 1, 2, 3),
                      (1, 9, 9, 1), (0, 6, 7, 1)):
            result = fet.fisher_exact_p_value(*table)
            self.assertGreaterEqual(result["p_two_tail"],
                                    result["p_one_tail"] - 1e-12)

    def test_extreme_table_one_tail_equals_p_obs_low(self):
        # a = 0 is the extreme of the low direction; the tail contains
        # only the observed table, so p_one_tail equals p_obs.
        result = fet.fisher_exact_p_value(0, 6, 7, 1)
        self.assertEqual(result["direction"], "low")
        self.assertAlmostEqual(result["p_one_tail"], result["p_obs"],
                               delta=1e-12)

    def test_extreme_table_one_tail_equals_p_obs_high(self):
        # a = 5 equals min(row1, col1), extreme of the high direction.
        result = fet.fisher_exact_p_value(5, 0, 0, 5)
        self.assertEqual(result["direction"], "high")
        self.assertAlmostEqual(result["p_one_tail"], result["p_obs"],
                               delta=1e-12)

    def test_two_tail_manual_selection_sum(self):
        # Worked example: only a' in {1, 2, 6, 7} have probability
        # <= p_obs; their sum is 352 / 3432.
        result = fet.fisher_exact_p_value(2, 6, 5, 1)
        self.assertAlmostEqual(result["p_two_tail"], 352 / 3432, delta=1e-12)

    def test_dict_keys_exactly_as_documented(self):
        result = fet.fisher_exact_p_value(2, 6, 5, 1)
        self.assertEqual(set(result.keys()),
                         {"p_obs", "p_one_tail", "p_two_tail", "direction"})
        for value in (result["p_obs"], result["p_one_tail"],
                      result["p_two_tail"]):
            self.assertTrue(0.0 <= value <= 1.0)

    def test_alternative_accepted_and_validated(self):
        base = fet.fisher_exact_p_value(2, 6, 5, 1)
        for alt in ("two-sided", "less", "greater"):
            self.assertEqual(fet.fisher_exact_p_value(2, 6, 5, 1,
                                                      alternative=alt), base)
        with self.assertRaises(ValueError):
            fet.fisher_exact_p_value(2, 6, 5, 1, alternative="middle")

    def test_negative_cell_rejected(self):
        with self.assertRaises(ValueError):
            fet.fisher_exact_p_value(-2, 6, 5, 1)

    def test_p_obs_matches_hypergeometric_p(self):
        result = fet.fisher_exact_p_value(2, 6, 5, 1)
        self.assertEqual(result["p_obs"], fet.hypergeometric_p(2, 6, 5, 1))


if __name__ == "__main__":
    unittest.main()
