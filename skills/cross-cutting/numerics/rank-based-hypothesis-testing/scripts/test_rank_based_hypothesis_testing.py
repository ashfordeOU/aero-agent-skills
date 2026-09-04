"""test_rank_based_hypothesis_testing.py

Offline deterministic contract test for the rank based hypothesis
testing leaf (cross-cutting/numerics/rank-based-hypothesis-testing).
Runs with: python3 scripts/test_rank_based_hypothesis_testing.py

Covers the worked-example anchors of the spec (Wilcoxon rank-sum /
Mann-Whitney U, Wilcoxon signed-rank, sign test with normal
approximation, continuity correction and verdict), the identity cases
(identical samples give U = n1 n2 / 2, z = 0, p = 1; symmetric paired
sample gives W = 0, p = 1), average-rank tie handling, dict key
contracts, determinism, the dispatch summary, and ValueError rejection
of every non-physical input.
"""

import unittest

from rank_based_hypothesis_testing_logic import (
    TEST_RANK_SUM,
    TEST_SIGN,
    TEST_SIGNED_RANK,
    rank_test_summary,
    sign_test,
    wilcoxon_rank_sum,
    wilcoxon_signed_rank,
)

# Worked example, two finish-roughness batches (spec anchor).
RANK_X = [0.82, 0.79, 0.85, 0.80, 0.83]
RANK_Y = [0.96, 1.02, 0.94, 0.98, 0.99]

# Signed-rank worked example: all six differences negative, W = -21.
SR_X = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
SR_Y = [1.1, 2.2, 3.3, 4.4, 5.5, 6.6]

# Sign test worked example: exactly 8 positive of 10 differences.
SIGN_X = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
SIGN_Y = [0.9, 1.9, 2.9, 3.9, 4.9, 5.9, 6.9, 7.9, 10.9, 11.9]
ALL_POS_Y = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5]
ALL_NEG_Y = [1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.5, 9.5, 10.5]

RANK_SUM_KEYS = {"n1", "n2", "r1", "u", "mu_u", "sd_u", "z", "p_value", "reject"}
SIGNED_RANK_KEYS = {"n", "w", "sd_w", "z", "p_value", "reject"}
SIGN_KEYS = {"n_pos", "n_neg", "n", "z", "p_value", "reject"}


class TestWilcoxonRankSum(unittest.TestCase):
    def test_worked_example_anchors(self):
        r = wilcoxon_rank_sum(RANK_X, RANK_Y)
        self.assertEqual(r["n1"], 5)
        self.assertEqual(r["n2"], 5)
        self.assertAlmostEqual(r["r1"], 15.0, places=4)
        self.assertAlmostEqual(r["u"], 0.0, places=4)
        self.assertAlmostEqual(r["mu_u"], 12.5, places=4)
        self.assertAlmostEqual(r["sd_u"], 4.787, places=3)
        self.assertAlmostEqual(r["z"], -2.5067, places=4)
        self.assertAlmostEqual(r["p_value"], 0.01219, places=5)
        self.assertIs(r["reject"], True)

    def test_worked_example_magnitude_bounds(self):
        r = wilcoxon_rank_sum(RANK_X, RANK_Y)
        self.assertTrue(-2.8 < r["z"] < -2.2)
        self.assertTrue(0.005 < r["p_value"] < 0.02)

    def test_reversed_direction_rejects_positive_z(self):
        r = wilcoxon_rank_sum(RANK_Y, RANK_X)
        self.assertAlmostEqual(r["r1"], 40.0, places=4)
        self.assertAlmostEqual(r["u"], 25.0, places=4)
        self.assertGreater(r["z"], 0.0)
        self.assertAlmostEqual(r["z"], 2.5067, places=4)
        self.assertIs(r["reject"], True)

    def test_identical_samples_p_one(self):
        r = wilcoxon_rank_sum([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
        self.assertAlmostEqual(r["u"], 3 * 3 / 2.0, places=6)
        self.assertAlmostEqual(r["z"], 0.0, places=6)
        self.assertAlmostEqual(r["p_value"], 1.0, places=6)
        self.assertIs(r["reject"], False)

    def test_identical_values_exercise_average_ranks(self):
        r = wilcoxon_rank_sum([2.5, 4.0, 7.0], [2.5, 4.0, 7.0])
        self.assertAlmostEqual(r["u"], 3 * 3 / 2.0, places=6)
        self.assertAlmostEqual(r["p_value"], 1.0, places=6)

    def test_partial_ties_average_ranks(self):
        # Merged 1(x), 2(x), 2(y), 3(x), 3(y), 4(y): tied pairs rank 2.5 and 4.5.
        r = wilcoxon_rank_sum([1.0, 2.0, 3.0], [2.0, 3.0, 4.0])
        self.assertAlmostEqual(r["r1"], 8.0, places=6)
        self.assertAlmostEqual(r["u"], 2.0, places=6)
        self.assertAlmostEqual(r["z"], -0.87287, places=4)

    def test_unequal_sample_sizes_convention(self):
        x = [1.0, 2.0, 3.0]
        y = [4.0, 5.0, 6.0, 7.0, 8.0]
        r = wilcoxon_rank_sum(x, y)
        self.assertEqual(r["n1"], 3)
        self.assertEqual(r["n2"], 5)
        self.assertAlmostEqual(r["u"], r["r1"] - 3 * 4 / 2.0, places=6)
        self.assertAlmostEqual(r["mu_u"], 7.5, places=6)
        self.assertIs(r["reject"], True)

    def test_result_keys(self):
        self.assertEqual(set(wilcoxon_rank_sum(RANK_X, RANK_Y).keys()), RANK_SUM_KEYS)

    def test_fewer_than_two_observations_raises(self):
        with self.assertRaises(ValueError):
            wilcoxon_rank_sum([1.0], [2.0, 3.0])
        with self.assertRaises(ValueError):
            wilcoxon_rank_sum([1.0, 2.0], [3.0])

    def test_alpha_out_of_range_raises(self):
        for bad in (0.0, 1.0, -0.05, 1.5):
            with self.assertRaises(ValueError):
                wilcoxon_rank_sum(RANK_X, RANK_Y, alpha=bad)


class TestWilcoxonSignedRank(unittest.TestCase):
    def test_worked_example_anchors(self):
        r = wilcoxon_signed_rank(SR_X, SR_Y)
        self.assertEqual(r["n"], 6)
        self.assertAlmostEqual(r["w"], -21.0, places=4)
        self.assertAlmostEqual(r["sd_w"], 9.539, places=3)
        self.assertAlmostEqual(r["sd_w"], (6 * 7 * 13 / 6.0) ** 0.5, places=6)
        self.assertAlmostEqual(r["z"], -2.1490, places=4)
        self.assertAlmostEqual(r["p_value"], 0.03164, places=5)
        self.assertIs(r["reject"], True)

    def test_worked_example_magnitude_bounds(self):
        r = wilcoxon_signed_rank(SR_X, SR_Y)
        self.assertTrue(-2.4 < r["z"] < -1.9)
        self.assertTrue(0.01 < r["p_value"] < 0.06)

    def test_all_positive_rejects(self):
        r = wilcoxon_signed_rank(SR_Y, SR_X)
        self.assertAlmostEqual(r["w"], 21.0, places=4)
        self.assertGreater(r["z"], 0.0)
        self.assertAlmostEqual(r["z"], 2.1490, places=4)
        self.assertIs(r["reject"], True)

    def test_symmetric_paired_sample_w_zero_p_one(self):
        # Differences +1, -1, +2, -2, +3, -3 give W = 0.
        d = [1.0, -1.0, 2.0, -2.0, 3.0, -3.0]
        zeros = [0.0] * len(d)
        r = wilcoxon_signed_rank(d, zeros)
        self.assertAlmostEqual(r["w"], 0.0, places=6)
        self.assertAlmostEqual(r["z"], 0.0, places=6)
        self.assertAlmostEqual(r["p_value"], 1.0, places=6)
        self.assertIs(r["reject"], False)

    def test_tied_magnitudes_average_ranks(self):
        # Differences +1, -1, +2, -2, +3, +3: magnitudes rank 1.5, 3.5, 5.5.
        d = [1.0, -1.0, 2.0, -2.0, 3.0, 3.0]
        zeros = [0.0] * len(d)
        r = wilcoxon_signed_rank(d, zeros)
        self.assertEqual(r["n"], 6)
        self.assertAlmostEqual(r["w"], 11.0, places=6)
        self.assertIs(r["reject"], False)

    def test_zero_differences_dropped(self):
        x = [1.0, 2.0, 3.0, 4.0, 5.0]
        y = [1.0, 3.0, 3.0, 4.5, 6.0]  # differences 0, -1, 0, -0.5, -1
        r = wilcoxon_signed_rank(x, y)
        self.assertEqual(r["n"], 3)

    def test_result_keys(self):
        self.assertEqual(set(wilcoxon_signed_rank(SR_X, SR_Y).keys()), SIGNED_RANK_KEYS)

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            wilcoxon_signed_rank([1.0, 2.0, 3.0], [1.0, 2.0])

    def test_fewer_than_two_nonzero_differences_raises(self):
        with self.assertRaises(ValueError):
            wilcoxon_signed_rank([1.0, 1.0, 1.0], [1.0, 2.0, 1.0])
        with self.assertRaises(ValueError):
            wilcoxon_signed_rank([1.0, 1.0], [1.0, 1.0])

    def test_alpha_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            wilcoxon_signed_rank(SR_X, SR_Y, alpha=0.0)


class TestSignTest(unittest.TestCase):
    def test_worked_example_anchors(self):
        r = sign_test(SIGN_X, SIGN_Y)
        self.assertEqual(r["n_pos"], 8)
        self.assertEqual(r["n_neg"], 2)
        self.assertEqual(r["n"], 10)
        self.assertAlmostEqual(r["z"], 1.5811, places=4)
        self.assertAlmostEqual(r["z"], 2.5 / (10.0 / 4.0) ** 0.5, places=6)
        self.assertAlmostEqual(r["p_value"], 0.1138, places=4)
        self.assertIs(r["reject"], False)

    def test_all_positive_rejects(self):
        r = sign_test(SIGN_X, ALL_POS_Y)
        self.assertEqual(r["n_pos"], 10)
        # Continuity-corrected z ~ 2.85 (spec hand check ~3.0), p ~ 0.0044.
        self.assertTrue(2.5 < r["z"] < 3.3)
        self.assertTrue(0.001 < r["p_value"] < 0.01)
        self.assertIs(r["reject"], True)

    def test_all_negative_rejects_negative_z(self):
        r = sign_test(SIGN_X, ALL_NEG_Y)
        self.assertEqual(r["n_pos"], 0)
        self.assertLess(r["z"], 0.0)
        self.assertTrue(0.001 < r["p_value"] < 0.01)
        self.assertIs(r["reject"], True)

    def test_balanced_no_reject(self):
        # 5 positive of 10 differences: z = 0, p = 1.
        y = [2.0, 1.0, 4.0, 3.0, 6.0, 5.0, 8.0, 7.0, 10.0, 9.0]
        r = sign_test(SIGN_X, y)
        self.assertEqual(r["n_pos"], 5)
        self.assertEqual(r["n_neg"], 5)
        self.assertAlmostEqual(r["z"], 0.0, places=6)
        self.assertAlmostEqual(r["p_value"], 1.0, places=6)
        self.assertIs(r["reject"], False)

    def test_one_sided_direction_small_sample(self):
        # 3 positive of 4 differences: corrected z = (3 - 2 - 0.5) / 1.0.
        x = [1.0, 2.0, 3.0, 4.0]
        y = [0.5, 1.5, 2.5, 5.0]
        r = sign_test(x, y)
        self.assertEqual(r["n"], 4)
        self.assertAlmostEqual(r["z"], 0.5, places=6)
        self.assertIs(r["reject"], False)

    def test_result_keys(self):
        self.assertEqual(set(sign_test(SIGN_X, SIGN_Y).keys()), SIGN_KEYS)

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            sign_test([1.0, 2.0, 3.0], [1.0, 2.0])

    def test_no_nonzero_differences_raises(self):
        with self.assertRaises(ValueError):
            sign_test([1.0, 2.0], [1.0, 2.0])

    def test_alpha_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            sign_test(SIGN_X, SIGN_Y, alpha=1.0)


class TestSummaryAndDeterminism(unittest.TestCase):
    def test_summary_dispatches_all_three(self):
        a = rank_test_summary(TEST_RANK_SUM, RANK_X, RANK_Y)
        b = rank_test_summary(TEST_SIGNED_RANK, SR_X, SR_Y)
        c = rank_test_summary(TEST_SIGN, SIGN_X, SIGN_Y)
        self.assertAlmostEqual(a["z"], wilcoxon_rank_sum(RANK_X, RANK_Y)["z"])
        self.assertAlmostEqual(b["z"], wilcoxon_signed_rank(SR_X, SR_Y)["z"])
        self.assertAlmostEqual(c["z"], sign_test(SIGN_X, SIGN_Y)["z"])

    def test_summary_unknown_test_raises(self):
        with self.assertRaises(ValueError):
            rank_test_summary("bogus-test", RANK_X, RANK_Y)

    def test_determinism_identical_float_outputs(self):
        r1 = wilcoxon_rank_sum(RANK_X, RANK_Y)
        r2 = wilcoxon_rank_sum(RANK_X, RANK_Y)
        self.assertEqual(r1["z"], r2["z"])
        self.assertEqual(r1["p_value"], r2["p_value"])
        s1 = sign_test(SIGN_X, ALL_POS_Y)
        s2 = sign_test(SIGN_X, ALL_POS_Y)
        self.assertEqual(s1["p_value"], s2["p_value"])

    def test_p_value_one_sided_symmetry(self):
        # Flipping the samples mirrors z and keeps p identical.
        fwd = wilcoxon_rank_sum(RANK_X, RANK_Y)
        rev = wilcoxon_rank_sum(RANK_Y, RANK_X)
        self.assertAlmostEqual(fwd["z"], -rev["z"], places=6)
        self.assertAlmostEqual(fwd["p_value"], rev["p_value"], places=6)


if __name__ == "__main__":
    unittest.main()
