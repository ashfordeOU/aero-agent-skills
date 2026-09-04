"""test_grubbs_outlier_test.py

Offline deterministic contract test for the grubbs-outlier-test leaf
(cross-cutting/numerics/grubbs-outlier-test). Runs with:
python3 scripts/test_grubbs_outlier_test.py

Covers the worked-example anchors (mean 10.4125, sample std 0.853,
G = 2.448 at the 12.5 reading, critical(8) = 2.032, verdict reject),
the clean-sample no-outlier case, the embedded critical-value table
spot checks with linear interpolation, the iterative removal contract
(removes exactly the 12.5 and stops), dict key contract, determinism,
and ValueError rejection of every non-physical input.
"""

import unittest

from grubbs_outlier_test_logic import (
    GRUBBS_CRIT_05,
    GRUBBS_SORTED_SIZES,
    grubbs_critical,
    grubbs_remove_outliers,
    grubbs_statistic,
    grubbs_test,
)

# Worked example: 8 resistance readings with one spurious high value.
WORKED = [10.2, 10.1, 10.3, 10.0, 9.9, 10.2, 10.1, 12.5]
# Clean control sample of the same size, no spurious reading.
CLEAN = [10.0, 10.1, 10.2, 10.1, 10.0, 10.3, 10.2, 10.1]
# Worked example after removing the flagged 12.5.
REMAINDER = [10.2, 10.1, 10.3, 10.0, 9.9, 10.2, 10.1]


class TestGrubbsStatistic(unittest.TestCase):
    """grubbs_statistic: G formation, candidate pick, input guards."""

    def test_worked_example_anchors(self):
        g, mean, std, candidate, candidate_idx = grubbs_statistic(WORKED)
        self.assertAlmostEqual(mean, 10.4125, places=4)
        self.assertAlmostEqual(std, 0.853, places=3)
        self.assertAlmostEqual(g, 2.448, places=2)
        self.assertEqual(candidate, 12.5)
        self.assertEqual(candidate_idx, 7)

    def test_candidate_is_farthest_reading(self):
        g, mean, std, candidate, candidate_idx = grubbs_statistic(WORKED)
        deviations = [abs(x - mean) for x in WORKED]
        self.assertAlmostEqual(g * std, max(deviations), places=9)
        self.assertEqual(WORKED[candidate_idx], candidate)

    def test_symmetric_sample_same_g_either_side(self):
        left = grubbs_statistic([10.0, 11.0, 12.0])
        right = grubbs_statistic([12.0, 11.0, 10.0])
        self.assertAlmostEqual(left[0], 1.0, places=9)
        self.assertAlmostEqual(left[0], right[0], places=9)
        self.assertEqual(left[3], 10.0)
        self.assertEqual(right[3], 12.0)

    def test_accepts_tuple_and_integer_inputs(self):
        g, mean, std, candidate, candidate_idx = grubbs_statistic((10, 10, 13))
        self.assertAlmostEqual(g, 1.1547, places=4)
        g2, _, _, _, _ = grubbs_statistic([10, 11, 12])
        self.assertAlmostEqual(g2, 1.0, places=9)

    def test_does_not_mutate_input(self):
        sample = list(WORKED)
        grubbs_statistic(sample)
        self.assertEqual(sample, WORKED)

    def test_rejects_short_samples(self):
        for short in ([1.0, 2.0], [5.0], [], (1.0,)):
            with self.assertRaises(ValueError):
                grubbs_statistic(short)

    def test_rejects_zero_standard_deviation(self):
        with self.assertRaises(ValueError):
            grubbs_statistic([7, 7, 7, 7])
        with self.assertRaises(ValueError):
            grubbs_statistic([10.0, 10.0, 10.0])

    def test_rejects_nonnumeric_values(self):
        with self.assertRaises(ValueError):
            grubbs_statistic([1.0, "high", 3.0])
        with self.assertRaises(ValueError):
            grubbs_statistic([None, 2.0, 3.0])


class TestGrubbsCritical(unittest.TestCase):
    """grubbs_critical: table hits, interpolation, input guards."""

    def test_exact_table_hits(self):
        for n, expected in GRUBBS_CRIT_05.items():
            self.assertAlmostEqual(grubbs_critical(n), expected, places=9)

    def test_validation_spot_checks(self):
        self.assertAlmostEqual(grubbs_critical(8), 2.032, places=3)
        self.assertAlmostEqual(grubbs_critical(5), 1.715, places=3)
        self.assertAlmostEqual(grubbs_critical(20), 2.709, places=3)

    def test_table_boundaries(self):
        self.assertAlmostEqual(grubbs_critical(3), 1.155, places=9)
        self.assertAlmostEqual(grubbs_critical(50), 3.128, places=9)

    def test_interpolation_midpoint_n11(self):
        # n = 11 sits halfway between listed n = 10 and n = 12.
        expected = (GRUBBS_CRIT_05[10] + GRUBBS_CRIT_05[12]) / 2.0
        self.assertAlmostEqual(grubbs_critical(11), expected, places=9)
        self.assertAlmostEqual(grubbs_critical(11), 2.351, places=3)

    def test_interpolation_n16(self):
        # n = 16 sits one fifth of the way from n = 15 to n = 20.
        self.assertAlmostEqual(grubbs_critical(16), 2.581, places=9)

    def test_interpolated_values_stay_between_neighbors(self):
        for n in range(3, 51):
            if n in GRUBBS_CRIT_05:
                continue
            lo = max(k for k in GRUBBS_SORTED_SIZES if k < n)
            hi = min(k for k in GRUBBS_SORTED_SIZES if k > n)
            value = grubbs_critical(n)
            self.assertGreater(value, GRUBBS_CRIT_05[lo])
            self.assertLess(value, GRUBBS_CRIT_05[hi])

    def test_critical_values_monotone_in_sample_size(self):
        values = [grubbs_critical(n) for n in range(3, 51)]
        for previous, current in zip(values, values[1:]):
            self.assertGreaterEqual(current, previous)

    def test_default_alpha_is_005(self):
        self.assertEqual(grubbs_critical(8), grubbs_critical(8, 0.05))

    def test_rejects_n_outside_range(self):
        for n in (1, 2, -4, 51, 100, 0):
            with self.assertRaises(ValueError):
                grubbs_critical(n)

    def test_rejects_fractional_sample_size(self):
        for n in (8.5, 12.3, 3.001):
            with self.assertRaises(ValueError):
                grubbs_critical(n)

    def test_rejects_unsupported_alpha(self):
        for alpha in (0.01, 0.10, 0.5, 1.0):
            with self.assertRaises(ValueError):
                grubbs_critical(8, alpha)

    def test_rejects_non_integer_types(self):
        with self.assertRaises(ValueError):
            grubbs_critical(True)
        with self.assertRaises(ValueError):
            grubbs_critical("8")


class TestGrubbsTest(unittest.TestCase):
    """grubbs_test: verdict, result dict contract, determinism."""

    def test_worked_example_verdict_reject(self):
        result = grubbs_test(WORKED)
        self.assertEqual(result["verdict"], "reject")
        self.assertAlmostEqual(result["g"], 2.448, places=2)
        self.assertAlmostEqual(result["critical"], 2.032, places=3)
        self.assertEqual(result["rejected_value"], 12.5)
        self.assertEqual(result["rejected_index"], 7)
        self.assertAlmostEqual(result["mean"], 10.4125, places=4)
        self.assertAlmostEqual(result["std"], 0.853, places=3)

    def test_clean_sample_no_outlier(self):
        result = grubbs_test(CLEAN)
        self.assertEqual(result["verdict"], "no-outlier")
        self.assertIsNone(result["rejected_value"])
        self.assertIsNone(result["rejected_index"])
        self.assertAlmostEqual(result["g"], 1.6907, places=4)

    def test_remainder_after_removal_never_flags_again(self):
        # Removing the flagged 12.5 leaves 7 values whose rerun G stays
        # below the n = 7 critical value: no further outlier.
        result = grubbs_test(REMAINDER)
        self.assertEqual(result["verdict"], "no-outlier")
        self.assertAlmostEqual(result["g"], 1.5930, places=4)
        self.assertAlmostEqual(result["critical"], 2.020, places=3)
        self.assertLess(result["g"], result["critical"])

    def test_dict_keys_exact(self):
        self.assertEqual(
            set(grubbs_test(WORKED).keys()),
            {"g", "critical", "verdict", "rejected_value",
             "rejected_index", "mean", "std"},
        )

    def test_deterministic_across_calls(self):
        self.assertEqual(grubbs_test(WORKED), grubbs_test(WORKED))

    def test_verdict_rule_consistent_with_g_comparison(self):
        for sample in (WORKED, CLEAN, REMAINDER, [1.0, 2.0, 3.0]):
            result = grubbs_test(sample)
            self.assertEqual(result["verdict"] == "reject",
                             result["g"] > result["critical"])
            if result["verdict"] == "reject":
                self.assertIsNotNone(result["rejected_value"])
            else:
                self.assertIsNone(result["rejected_value"])

    def test_rejects_non_physical_inputs(self):
        with self.assertRaises(ValueError):
            grubbs_test([1.0, 2.0])
        with self.assertRaises(ValueError):
            grubbs_test([5.0, 5.0, 5.0, 5.0])


class TestGrubbsRemoveOutliers(unittest.TestCase):
    """grubbs_remove_outliers: iterative removal contract."""

    def test_worked_example_removes_12_5_and_stops(self):
        clean, removed = grubbs_remove_outliers(WORKED)
        self.assertEqual(clean, [10.2, 10.1, 10.3, 10.0, 9.9, 10.2, 10.1])
        self.assertEqual(removed, [12.5])

    def test_clean_sample_unchanged(self):
        clean, removed = grubbs_remove_outliers(CLEAN)
        self.assertEqual(clean, CLEAN)
        self.assertEqual(removed, [])

    def test_two_pass_removal(self):
        sample = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 20.0, 50.0]
        clean, removed = grubbs_remove_outliers(sample)
        self.assertEqual(clean, [10.0, 10.0, 10.0, 10.0, 10.0, 10.0])
        self.assertEqual(removed, [50.0, 20.0])

    def test_all_identical_sample_stops_clean(self):
        clean, removed = grubbs_remove_outliers([10.0, 10.0, 10.0, 10.0])
        self.assertEqual(clean, [10.0, 10.0, 10.0, 10.0])
        self.assertEqual(removed, [])

    def test_identical_remainder_stops_after_removal(self):
        clean, removed = grubbs_remove_outliers([10.0, 10.0, 10.0, 100.0])
        self.assertEqual(clean, [10.0, 10.0, 10.0])
        self.assertEqual(removed, [100.0])

    def test_removed_values_come_from_sample(self):
        sample = [9.9, 10.2, 10.1, 12.5, 10.3]
        clean, removed = grubbs_remove_outliers(sample)
        for value in removed:
            self.assertIn(value, sample)
        for value in clean:
            self.assertIn(value, sample)

    def test_rejects_fewer_than_3_values(self):
        with self.assertRaises(ValueError):
            grubbs_remove_outliers([1.0, 2.0])

    def test_rejects_nonnumeric_values(self):
        with self.assertRaises(ValueError):
            grubbs_remove_outliers([1.0, "bad", 3.0, 4.0])


if __name__ == "__main__":
    unittest.main()
