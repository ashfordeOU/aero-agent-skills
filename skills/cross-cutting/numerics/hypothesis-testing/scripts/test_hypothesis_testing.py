"""Contract test for the hypothesis-testing leaf (stdlib unittest, offline).

Asserts the worked-example anchors of the wave-26 leaf spec directly
against the real module outputs: config A/B drag count comparison with
the pooled t test (df 8, p < 0.01, reject at 0.05), the Welch variant
(df below 8), the paired test on constant +0.1 differences, the
t-stat squared equals ANOVA F identity, the F test on identical data
(stat 1, p 1), the chi-square independence anchors, the centered
one-sample anchor, special-function values, boundary cases, degenerate
verdicts, and ValueError rejection of invalid inputs.

Run offline: python3 scripts/test_hypothesis_testing.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hypothesis_testing_logic as ht

A = [267.0, 261.0, 263.0, 258.0, 262.0]  # drag counts, config A
B = [273.0, 271.0, 268.0, 275.0, 270.0]  # drag counts, config B
S = [100.0, 200.0, 300.0, 400.0, 500.0]


class SpecialFunctionTests(unittest.TestCase):
    def test_t_cdf_zero_two_sided_is_one(self):
        # t_cdf(0, 10) = 1.0 per the worked-example cross-check.
        self.assertEqual(ht.t_cdf(0.0, 10.0), 1.0)

    def test_t_cdf_huge_t_is_zero(self):
        # t_cdf(1e6, 10) ~ 0.0 per the worked-example cross-check.
        self.assertAlmostEqual(ht.t_cdf(1e6, 10.0), 0.0, places=12)

    def test_t_cdf_one_sided_halves_two_sided(self):
        self.assertAlmostEqual(
            ht.t_cdf(1.8, 10.0, tails="one-sided"),
            ht.t_cdf(1.8, 10.0) / 2.0, places=12)
        self.assertAlmostEqual(
            ht.t_cdf(-1.8, 10.0, tails="one-sided"),
            ht.t_cdf(1.8, 10.0, tails="one-sided"), places=12)

    def test_t_cdf_known_five_percent_critical_value(self):
        # Two-sided 5% critical t for df 8 is 2.306.
        p = ht.t_cdf(2.306, 8.0)
        self.assertAlmostEqual(p, 0.05, places=3)
        self.assertTrue(0.049 < p < 0.051)

    def test_chi2_cdf_zero_and_critical_value(self):
        # chi2_cdf(0, 5) = 0.0 per the worked-example cross-check, and the
        # 95th percentile of chi2 with df 1 is 3.841.
        self.assertEqual(ht.chi2_cdf(0.0, 5.0), 0.0)
        p = ht.chi2_cdf(3.841, 1.0)
        self.assertTrue(0.949 < p < 0.951)

    def test_incomplete_beta_half_point_symmetric_value(self):
        # I_0.5(2, 2) = 0.5 from the symmetric beta(2, 2) CDF.
        self.assertAlmostEqual(ht.regularized_incomplete_beta(2.0, 2.0, 0.5),
                               0.5, places=10)

    def test_incomplete_beta_symmetry_identity(self):
        # I_x(a, b) = 1 - I_(1-x)(b, a).
        direct = ht.regularized_incomplete_beta(3.0, 2.0, 0.4)
        swapped = 1.0 - ht.regularized_incomplete_beta(2.0, 3.0, 0.6)
        self.assertAlmostEqual(direct, swapped, places=10)

    def test_incomplete_gamma_matches_erf_identity(self):
        # P(0.5, x) = erf(sqrt(x)); exercise both the series and the
        # continued-fraction branches (x below and above a + 1).
        self.assertAlmostEqual(ht.regularized_lower_incomplete_gamma(0.5, 0.25),
                               math.erf(0.5), places=10)
        self.assertAlmostEqual(ht.regularized_lower_incomplete_gamma(0.5, 4.0),
                               math.erf(2.0), places=10)

    def test_incomplete_gamma_known_exponential_value(self):
        # P(1, 1) = 1 - e^-1.
        self.assertAlmostEqual(ht.regularized_lower_incomplete_gamma(1.0, 1.0),
                               1.0 - math.exp(-1.0), places=12)

    def test_special_function_invalid_args_raise(self):
        with self.assertRaises(ValueError):
            ht.regularized_incomplete_beta(0.0, 2.0, 0.5)
        with self.assertRaises(ValueError):
            ht.regularized_incomplete_beta(2.0, -1.0, 0.5)
        with self.assertRaises(ValueError):
            ht.regularized_incomplete_beta(2.0, 2.0, 1.5)
        with self.assertRaises(ValueError):
            ht.regularized_lower_incomplete_gamma(0.0, 1.0)
        with self.assertRaises(ValueError):
            ht.regularized_lower_incomplete_gamma(1.0, -0.5)
        with self.assertRaises(ValueError):
            ht.t_cdf(1.0, 0.0)


class OneSampleTTests(unittest.TestCase):
    def test_t_test_1samp_centered_anchor_zero_stat(self):
        # S against mu0 300 (its own mean): stat 0, p 1, fail-to-reject.
        res = ht.t_test_1samp(S, 300.0)
        self.assertEqual(res["stat"], 0.0)
        self.assertEqual(res["p"], 1.0)
        self.assertEqual(res["verdict"], "fail-to-reject")
        self.assertEqual(res["df"], 4)

    def test_t_test_1samp_offset_mean_rejects(self):
        # S against mu0 100: module stat 2.828, p 0.0474, reject at 0.05.
        res = ht.t_test_1samp(S, 100.0)
        self.assertAlmostEqual(res["stat"], 2.82842712474619, places=9)
        self.assertAlmostEqual(res["p"], 0.04742065558431939, places=9)
        self.assertEqual(res["verdict"], "reject-null")

    def test_t_test_1samp_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ht.t_test_1samp([5.0, 5.0, 5.0], 5.0)  # zero variance
        with self.assertRaises(ValueError):
            ht.t_test_1samp([1.0], 0.0)  # too small
        with self.assertRaises(ValueError):
            ht.t_test_1samp([float("nan"), 2.0, 3.0], 2.0)  # non-finite
        with self.assertRaises(ValueError):
            ht.t_test_1samp(S, 300.0, alpha=1.5)  # alpha out of range


class TwoSampleTTests(unittest.TestCase):
    def test_t_test_2samp_drag_counts_anchor(self):
        # Config A vs B drag counts: df 8, p < 0.01, reject at 0.05.
        res = ht.t_test_2samp(A, B)
        self.assertEqual(res["df"], 8)
        self.assertAlmostEqual(res["stat"], -4.848825745591509, places=9)
        self.assertAlmostEqual(res["p"], 0.0012737537423696313, places=9)
        self.assertLess(res["p"], 0.01)
        self.assertLess(res["p"], 0.05)
        self.assertEqual(res["verdict"], "reject-null")
        self.assertLess(sum(A) / len(A), sum(B) / len(B))

    def test_t_test_2samp_welch_lower_df_rejects(self):
        # Welch on the same drag counts: Satterthwaite df below 8.
        res = ht.t_test_2samp(A, B, equal_var=False)
        self.assertLess(res["df"], 8)
        self.assertAlmostEqual(res["df"], 7.72440100131124, places=9)
        self.assertAlmostEqual(res["p"], 0.0014072534411103507, places=9)
        self.assertLess(res["p"], 0.05)
        self.assertEqual(res["verdict"], "reject-null")

    def test_t_test_2samp_identical_data_pass(self):
        res = ht.t_test_2samp(A, A)
        self.assertAlmostEqual(res["stat"], 0.0, places=10)
        self.assertAlmostEqual(res["p"], 1.0, places=10)
        self.assertEqual(res["verdict"], "fail-to-reject")

    def test_t_test_2samp_constant_groups_degenerate(self):
        # Both variances zero: degenerate verdict from the means alone.
        same = ht.t_test_2samp([5.0, 5.0, 5.0], [5.0, 5.0, 5.0])
        self.assertEqual(same["stat"], 0.0)
        self.assertEqual(same["p"], 1.0)
        self.assertEqual(same["verdict"], "fail-to-reject")
        diff = ht.t_test_2samp([5.0, 5.0, 5.0], [9.0, 9.0, 9.0])
        self.assertEqual(diff["stat"], float("inf"))
        self.assertEqual(diff["p"], 0.0)
        self.assertEqual(diff["verdict"], "reject-null")

    def test_t_test_2samp_stat_squared_equals_anova_f(self):
        # Identity: pooled two-sample t on two groups vs one-way ANOVA.
        t_res = ht.t_test_2samp(A, B)
        an_res = ht.anova_oneway([A, B])
        self.assertAlmostEqual(t_res["stat"] ** 2, an_res["stat"], places=9)
        self.assertAlmostEqual(t_res["p"], an_res["p"], delta=1e-9)


class PairedTTests(unittest.TestCase):
    def test_t_test_paired_constant_shift_rejects(self):
        # All differences +0.1: large |t|, reject-null at 0.05.
        c = [1.0, 2.0, 1.5, 2.0, 1.8]
        d = [1.1, 2.1, 1.6, 2.2, 1.9]
        res = ht.t_test_paired(c, d)
        self.assertLess(res["p"], 0.05)
        self.assertAlmostEqual(res["stat"], -5.999999999999995, places=9)
        self.assertAlmostEqual(res["p"], 0.0038825370469605207, places=9)
        self.assertEqual(res["verdict"], "reject-null")
        self.assertEqual(res["df"], 4)

    def test_t_test_paired_identical_pass(self):
        res = ht.t_test_paired([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        self.assertEqual(res["stat"], 0.0)
        self.assertEqual(res["p"], 1.0)
        self.assertEqual(res["verdict"], "fail-to-reject")

    def test_t_test_paired_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ht.t_test_paired([1.0, 2.0, 3.0], [1.0, 2.0])  # length mismatch
        with self.assertRaises(ValueError):
            ht.t_test_paired([1.0], [2.0])  # too few pairs
        with self.assertRaises(ValueError):
            ht.t_test_paired([1.0, float("inf")], [2.0, 3.0])  # non-finite


class FVarianceTests(unittest.TestCase):
    def test_f_test_variances_identical_data_one(self):
        # F test on identical data: stat 1.0 and p 1.0.
        res = ht.f_test_variances(A, A)
        self.assertEqual(res["stat"], 1.0)
        self.assertAlmostEqual(res["p"], 1.0, places=10)
        self.assertEqual(res["verdict"], "fail-to-reject")

    def test_f_test_variances_rejects_different_spread(self):
        # A vs a much wider spread: module stat 51.4, p 0.00216, reject.
        w = [250.0, 260.0, 300.0, 240.0, 275.0]
        res = ht.f_test_variances(A, w)
        self.assertGreaterEqual(res["stat"], 1.0)
        self.assertAlmostEqual(res["stat"], 51.401869158878505, places=9)
        self.assertAlmostEqual(res["p"], 0.0021572330654282125, places=9)
        self.assertLess(res["p"], 0.05)
        self.assertEqual(res["verdict"], "reject-null")

    def test_f_test_variances_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ht.f_test_variances(A, [5.0, 5.0, 5.0, 5.0, 5.0])  # zero variance
        with self.assertRaises(ValueError):
            ht.f_test_variances([1.0, 2.0], [3.0, 4.0, 5.0])  # too small
        with self.assertRaises(ValueError):
            ht.f_test_variances([float("nan"), 2.0, 3.0], A)  # non-finite


class ChiSquareTests(unittest.TestCase):
    def test_chi2_independence_independent_table_pass(self):
        # Perfectly independent 2x2 table: stat 0, p 1, fail-to-reject.
        res = ht.chi2_independence([[10.0, 20.0], [30.0, 60.0]])
        self.assertEqual(res["stat"], 0.0)
        self.assertEqual(res["p"], 1.0)
        self.assertEqual(res["verdict"], "fail-to-reject")
        self.assertEqual(res["df"], 1)

    def test_chi2_independence_dependent_table_rejects(self):
        # Module p 0.00617, below 0.05: reject-null.
        res = ht.chi2_independence([[15.0, 15.0], [5.0, 25.0]])
        self.assertEqual(res["stat"], 7.5)
        self.assertAlmostEqual(res["p"], 0.006169899320537686, places=9)
        self.assertLess(res["p"], 0.05)
        self.assertEqual(res["verdict"], "reject-null")

    def test_chi2_independence_expected_counts_checked(self):
        # Expected table matches observed for the independent table, and
        # expected row totals match the observed row totals.
        res = ht.chi2_independence([[10.0, 20.0], [30.0, 60.0]])
        exp = res["expected"]
        for i in range(2):
            for j in range(2):
                self.assertAlmostEqual(exp[i][j], [[10.0, 20.0], [30.0, 60.0]][i][j],
                                       places=9)
        self.assertAlmostEqual(sum(exp[0]), 30.0, places=9)
        self.assertAlmostEqual(sum(exp[1]), 90.0, places=9)

    def test_chi2_independence_invalid_tables_raise(self):
        with self.assertRaises(ValueError):
            ht.chi2_independence([[0.0, 0.0], [5.0, 5.0]])  # zero row total
        with self.assertRaises(ValueError):
            ht.chi2_independence([[1.0, 0.0], [0.0, 100000.0]])  # expected < 1
        with self.assertRaises(ValueError):
            ht.chi2_independence([[1.0, 2.0, 3.0], [4.0, 5.0]])  # ragged
        with self.assertRaises(ValueError):
            ht.chi2_independence([[1.0, -2.0], [3.0, 4.0]])  # negative entry


class AnovaTests(unittest.TestCase):
    def test_anova_three_groups_rejects(self):
        # Well separated batches: df 2/12, p 5.05e-11, reject-null.
        g1 = [10.0, 12.0, 11.0, 13.0, 12.0]
        g2 = [20.0, 22.0, 21.0, 23.0, 22.0]
        g3 = [31.0, 33.0, 32.0, 30.0, 34.0]
        res = ht.anova_oneway([g1, g2, g3])
        self.assertEqual(res["df_between"], 2)
        self.assertEqual(res["df_within"], 12)
        self.assertAlmostEqual(res["stat"], 306.03921568627453, places=9)
        self.assertAlmostEqual(res["p"], 5.054200152763838e-11, places=15)
        self.assertEqual(res["verdict"], "reject-null")

    def test_anova_similar_groups_fail_to_reject(self):
        # Overlapping batches: p 0.98, fail-to-reject.
        c1 = [10.0, 12.0, 11.0, 13.0, 12.0]
        c2 = [10.5, 11.5, 12.5, 11.0, 12.0]
        c3 = [11.0, 12.5, 10.5, 12.0, 11.5]
        res = ht.anova_oneway([c1, c2, c3])
        self.assertAlmostEqual(res["stat"], 0.019607843137254763, places=9)
        self.assertGreater(res["p"], 0.95)
        self.assertEqual(res["verdict"], "fail-to-reject")

    def test_anova_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ht.anova_oneway([[1.0, 2.0], [3.0, 4.0, 5.0]])  # group too small
        with self.assertRaises(ValueError):
            ht.anova_oneway([[1.0, 2.0, 3.0]])  # single group
        with self.assertRaises(ValueError):
            ht.anova_oneway([[1.0, 2.0, float("inf")], [3.0, 4.0, 5.0]])


class ValidationAndSummaryTests(unittest.TestCase):
    def test_t_test_2samp_nonfinite_raises(self):
        with self.assertRaises(ValueError):
            ht.t_test_2samp([float("inf"), 2.0, 3.0], [1.0, 2.0, 3.0])
        with self.assertRaises(ValueError):
            ht.t_test_2samp(A, [1.0, float("nan"), 3.0])

    def test_alpha_out_of_range_raises(self):
        for bad in (0.0, 1.0, -0.1, 1.5):
            with self.assertRaises(ValueError):
                ht.t_test_2samp(A, B, alpha=bad)
            with self.assertRaises(ValueError):
                ht.chi2_independence([[10.0, 20.0], [30.0, 60.0]], alpha=bad)

    def test_summarize_rows_and_note(self):
        res = ht.summarize({"t2": ht.t_test_2samp(A, B),
                            "chi2": ht.chi2_independence([[10.0, 20.0],
                                                          [30.0, 60.0]])})
        self.assertEqual(len(res["rows"]), 2)
        self.assertEqual(res["rejecting"], ["t2"])
        self.assertIn("t2", res["note"])
        self.assertNotIn("chi2", res["note"])
        self.assertEqual(res["rows"][0]["verdict"], "reject-null")

    def test_summarize_no_rejection_note(self):
        res = ht.summarize({"chi2": ht.chi2_independence([[10.0, 20.0],
                                                          [30.0, 60.0]])})
        self.assertEqual(res["rejecting"], [])
        self.assertIn("no test rejects", res["note"])


if __name__ == "__main__":
    unittest.main()
