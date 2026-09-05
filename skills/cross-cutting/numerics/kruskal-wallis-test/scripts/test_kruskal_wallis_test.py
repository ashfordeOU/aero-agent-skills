"""Contract test for the kruskal-wallis-test logic module.

Deterministic, offline, stdlib only. Run with:
    python3 test_kruskal_wallis_test.py
The spec worked example (three groups of three, x = [2.1, 2.2, 2.3],
y = [2.9, 3.0, 3.1], z = [3.7, 3.8, 3.9]) anchors the asserts:
H = 7.2 within 1e-9, df 2, p_value 0.0273 within 1e-3 (chi-square
survival P(chi2_2 > 7.2) = exp(-3.6) = 0.027323722447292528, checked
against the survival-function evaluation), verdict reject at 0.05,
per-group rank sums 6, 15, 24. The assert targets are the real module
outputs taken inside the spec magnitude bounds.

Workflow coverage: the test methods below exercise the numbered steps
of the SKILL.md Workflow section. Step 1 (group collection, at least
three samples with two or more observations each) is covered by the
validation class tests. Step 2 (rank assignment with average ranks for
ties) is covered by test_rank_data_average_ranks_for_ties and
test_rank_data_plain_ordering. Step 3 (H statistic computation) is
covered by the worked-example H tests and the rank-invariance tests.
Step 4 (ties correction via ties_correction) is covered by the tied
denominator and corrected-statistic identity tests. Step 5 (significance
conversion through the chi-square survival with k - 1 degrees of
freedom) is covered by the p-value and survival anchor tests. Step 6
(verdict report dict reading at the chosen significance level) is
covered by the verdict, report-key and determinism tests. Step 7 (the
contract test run itself) is this module.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kruskal_wallis_test_logic as kw

X = [2.1, 2.2, 2.3]
Y = [2.9, 3.0, 3.1]
Z = [3.7, 3.8, 3.9]
WORKED = [X, Y, Z]


class TestWorkedExample(unittest.TestCase):
    def test_worked_example_h_within_spec_bounds(self):
        # Step 3 of the SKILL.md workflow, the H statistic computation,
        # on the spec worked example: H = 7.2 within 1e-9.
        self.assertAlmostEqual(kw.kruskal_wallis_h(WORKED), 7.2, delta=1e-9)

    def test_worked_example_degrees_of_freedom(self):
        # Significance conversion at df = group_count - 1 = 2.
        report = kw.kruskal_wallis_test(WORKED)
        self.assertEqual(report["df"], 2)

    def test_worked_example_p_value_against_anchor(self):
        # Step 5 (significance conversion): p within 1e-3 of 0.0273 and
        # tight against the real survival evaluation.
        report = kw.kruskal_wallis_test(WORKED)
        self.assertAlmostEqual(report["p_value"], 0.0273, delta=1e-3)
        self.assertAlmostEqual(report["p_value"], 0.027323722447292528, delta=1e-9)

    def test_worked_example_p_matches_exponential_survival(self):
        # chi-square survival with df 2 is exp(-h / 2); the p-value at
        # h 7.2 must equal exp(-3.6) on the survival function path.
        p = kw.kruskal_wallis_p_value(7.2, 3)
        self.assertAlmostEqual(p, math.exp(-3.6), delta=1e-12)

    def test_worked_example_verdict_reject_at_005(self):
        # Step 6, the verdict report at significance level 0.05: p below
        # alpha, so the verdict is reject.
        report = kw.kruskal_wallis_test(WORKED)
        self.assertEqual(report["verdict"], "reject")

    def test_worked_example_group_rank_sums(self):
        # Step 2 rank assignment followed by the report dict: x sums 6,
        # y sums 15, z sums 24.
        report = kw.kruskal_wallis_test(WORKED)
        self.assertEqual(report["group_rank_sums"], [6.0, 15.0, 24.0])

    def test_worked_example_no_ties_identity(self):
        # Step 4, the ties correction step: no ties gives correction 1.0
        # and h_corrected equals the raw H statistic.
        self.assertEqual(kw.ties_correction(WORKED), 1.0)
        report = kw.kruskal_wallis_test(WORKED)
        self.assertEqual(report["h_corrected"], report["h"])


class TestRankAssignment(unittest.TestCase):
    def test_rank_data_plain_ordering(self):
        # Step 2 rank assignment on untied data returns 1..N in order.
        merged = [v for g in WORKED for v in g]
        self.assertEqual(kw.rank_data(merged), [1.0, 2.0, 3.0, 4.0, 5.0,
                                                6.0, 7.0, 8.0, 9.0])

    def test_rank_data_average_ranks_for_ties(self):
        # Step 2: tied observations share the average rank of the block,
        # so [1, 1, 2, 3] maps to [1.5, 1.5, 3.0, 4.0].
        self.assertEqual(kw.rank_data([1, 1, 2, 3]), [1.5, 1.5, 3.0, 4.0])
        self.assertEqual(kw.rank_data([1, 2, 2, 2, 3]), [1.0, 3.0, 3.0, 3.0, 5.0])

    def test_rank_data_empty(self):
        self.assertEqual(kw.rank_data([]), [])

    def test_rank_invariance_under_scaling(self):
        # Step 3 sanity: H is invariant to a monotone transform of the
        # data because only the rank assignment changes, not the ranks.
        scaled = [[10.0 * v for v in group] for group in WORKED]
        self.assertEqual(kw.kruskal_wallis_h(scaled), kw.kruskal_wallis_h(WORKED))

    def test_rank_invariance_under_affine_shift(self):
        shifted = [[10.0 * v + 5.0 for v in group] for group in WORKED]
        self.assertEqual(kw.kruskal_wallis_h(shifted), kw.kruskal_wallis_h(WORKED))


class TestIdenticalAndTiedData(unittest.TestCase):
    def test_identical_groups_h_zero_p_one(self):
        # Step 3 and step 5: all-identical groups give H = 0.0 and a
        # p-value of exactly 1.0 from the survival function.
        identical = [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]
        report = kw.kruskal_wallis_test(identical)
        self.assertEqual(report["h"], 0.0)
        self.assertEqual(report["p_value"], 1.0)

    def test_identical_groups_verdict_fail_to_reject(self):
        identical = [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]
        report = kw.kruskal_wallis_test(identical)
        self.assertEqual(report["verdict"], "fail to reject")

    def test_identical_groups_zero_denominator_handled(self):
        # Step 4: a single tie run covering all N observations makes the
        # correction denominator 0, and the corrected statistic stays 0.
        identical = [[1.0, 1.0, 1.0], [1.0, 1.0, 1.0], [1.0, 1.0, 1.0]]
        self.assertEqual(kw.ties_correction(identical), 0.0)
        self.assertEqual(kw.kruskal_wallis_test(identical)["h_corrected"], 0.0)

    def test_ties_correction_denominator_below_one(self):
        # Step 4 ties correction: the spec tied example [1, 2, 3],
        # [1.5, 2.5, 3.5], [2, 3, 4] carries tied values 2 and 3, giving
        # C = 1 - 12 / 720 = 0.9833333333333333 below 1.
        tied = [[1, 2, 3], [1.5, 2.5, 3.5], [2, 3, 4]]
        correction = kw.ties_correction(tied)
        self.assertAlmostEqual(correction, 0.9833333333333333, delta=1e-12)
        self.assertLess(correction, 1.0)

    def test_ties_corrected_statistic_identity(self):
        # Step 4: the model divides H by the correction denominator,
        # h_corrected = h / C, so the corrected statistic rises above the
        # raw H whenever ties are present (C below 1).
        tied = [[1, 2, 3], [1.5, 2.5, 3.5], [2, 3, 4]]
        report = kw.kruskal_wallis_test(tied)
        correction = kw.ties_correction(tied)
        self.assertAlmostEqual(report["h_corrected"], report["h"] / correction,
                               delta=1e-12)
        self.assertGreater(report["h_corrected"], report["h"])

    def test_tied_report_rank_sums(self):
        tied = [[1, 2, 3], [1.5, 2.5, 3.5], [2, 3, 4]]
        report = kw.kruskal_wallis_test(tied)
        self.assertEqual(report["group_rank_sums"], [11.0, 15.0, 19.0])

    def test_tied_data_p_value_direction(self):
        # The tied example is weakly separated, so the p-value stays
        # above 0.05 and the verdict is fail to reject.
        tied = [[1, 2, 3], [1.5, 2.5, 3.5], [2, 3, 4]]
        report = kw.kruskal_wallis_test(tied)
        self.assertGreater(report["p_value"], 0.05)
        self.assertEqual(report["verdict"], "fail to reject")


class TestReportContract(unittest.TestCase):
    def test_unequal_group_sizes_accepted(self):
        # Groups of 4, 3 and 2 observations run through the whole
        # workflow; df stays 2 and the verdict is reject for strong
        # separation.
        groups = [[1.0, 1.1, 1.2, 1.3], [5.0, 5.1, 5.2], [9.0, 9.1]]
        report = kw.kruskal_wallis_test(groups)
        self.assertEqual(report["df"], 2)
        self.assertEqual(report["verdict"], "reject")
        self.assertLess(report["p_value"], 0.05)

    def test_rank_sum_total_identity(self):
        # The per-group rank sums always total N (N + 1) / 2, the closed
        # form for the sum of the merged ranks, with or without ties.
        for groups in (WORKED, [[1, 2, 3], [1.5, 2.5, 3.5], [2, 3, 4]]):
            report = kw.kruskal_wallis_test(groups)
            n = sum(len(g) for g in groups)
            self.assertAlmostEqual(sum(report["group_rank_sums"]),
                                   n * (n + 1) / 2.0, delta=1e-9)

    def test_report_dict_keys_exact(self):
        report = kw.kruskal_wallis_test(WORKED)
        self.assertEqual(sorted(report.keys()),
                         ["df", "group_rank_sums", "h", "h_corrected",
                          "p_value", "verdict"])

    def test_determinism_repeat_calls_identical(self):
        first = kw.kruskal_wallis_test(WORKED)
        second = kw.kruskal_wallis_test(WORKED)
        self.assertEqual(first, second)

    def test_default_alpha_is_005(self):
        report = kw.kruskal_wallis_test(WORKED)
        self.assertEqual(report["verdict"], "reject")

    def test_zero_h_p_value_is_one(self):
        # Step 5 boundary: a zero corrected statistic is never exceeded
        # by the chi-square survival, so p is exactly 1.0.
        self.assertEqual(kw.kruskal_wallis_p_value(0.0, 3), 1.0)

    def test_alpha_half_verdict_consistent(self):
        # Same separation at alpha 0.5 still rejects; the significance
        # level only moves the verdict boundary.
        report = kw.kruskal_wallis_test(WORKED, alpha=0.5)
        self.assertEqual(report["verdict"], "reject")


class TestInputValidation(unittest.TestCase):
    def test_two_groups_raise_valueerror(self):
        with self.assertRaises(ValueError):
            kw.kruskal_wallis_h([X, Y])
        with self.assertRaises(ValueError):
            kw.kruskal_wallis_test([X, Y])

    def test_single_observation_group_raises(self):
        with self.assertRaises(ValueError):
            kw.kruskal_wallis_test([X, [3.0], Z])

    def test_nan_observation_raises(self):
        with self.assertRaises(ValueError):
            kw.kruskal_wallis_test([X + [float("nan")], Y, Z])
        with self.assertRaises(ValueError):
            kw.rank_data([1.0, float("nan")])

    def test_infinite_observation_raises(self):
        with self.assertRaises(ValueError):
            kw.kruskal_wallis_test([[1.0, float("inf")], Y, Z])

    def test_alpha_zero_raises(self):
        with self.assertRaises(ValueError):
            kw.kruskal_wallis_test(WORKED, alpha=0.0)

    def test_alpha_one_raises(self):
        with self.assertRaises(ValueError):
            kw.kruskal_wallis_test(WORKED, alpha=1.0)

    def test_alpha_outside_interval_raises(self):
        with self.assertRaises(ValueError):
            kw.kruskal_wallis_test(WORKED, alpha=1.5)
        with self.assertRaises(ValueError):
            kw.kruskal_wallis_test(WORKED, alpha=-0.1)

    def test_negative_h_corrected_raises(self):
        with self.assertRaises(ValueError):
            kw.kruskal_wallis_p_value(-1.0, 3)

    def test_p_value_group_count_below_three_raises(self):
        with self.assertRaises(ValueError):
            kw.kruskal_wallis_p_value(5.0, 2)


if __name__ == "__main__":
    unittest.main()
