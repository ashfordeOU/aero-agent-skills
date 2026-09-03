"""Contract test for descriptive-statistics (cross-cutting/numerics).

Covers the spec worked-example anchors (mean 5.0, median 4.5, range 7.0,
sample variance 32/7, sample std 2.1380899353, population variance 4.0
and std 2.0, q1 4.0, q3 5.5, iqr 1.5, five-number summary {2, 4, 4.5,
5.5, 9}, coefficient of variation 0.42762, only index 7 flagged as an
outlier), the validation list (ValueError on empty samples, ddof guards,
percentile bounds, zero-mean CV guard, single-element behavior, odd and
even medians, the exact-fence boundary case), determinism, and the full
summary dict. Runs offline in well under a second.
"""

import math
import unittest

from descriptive_statistics_logic import (
    IQR_FACTOR,
    coefficient_of_variation,
    data_range,
    five_number_summary,
    interquartile_range,
    mean,
    median,
    outlier_indices_iqr,
    percentile,
    quartiles,
    std_dev,
    summary,
    variance,
)

# Worked example sample from the spec.
SAMPLE = [2, 4, 4, 4, 5, 5, 7, 9]


def assert_close(test, actual, expected, rel=1e-9):
    test.assertTrue(
        math.isclose(actual, expected, rel_tol=rel),
        "{0} not within {1} relative of {2}".format(actual, rel, expected),
    )


class TestLocationMeasures(unittest.TestCase):
    def test_mean_worked_example(self):
        assert_close(self, mean(SAMPLE), 5.0)

    def test_median_even_count_averages_middle_two(self):
        assert_close(self, median(SAMPLE), 4.5)

    def test_median_odd_count_exact_middle(self):
        self.assertEqual(median([1, 2, 3]), 2.0)

    def test_range_worked_example(self):
        assert_close(self, data_range(SAMPLE), 7.0)

    def test_single_element_sample(self):
        for fn in (mean, median):
            self.assertEqual(fn([7.5]), 7.5)
        self.assertEqual(data_range([7.5]), 0.0)

    def test_median_matches_quartile_q2(self):
        self.assertEqual(median(SAMPLE), quartiles(SAMPLE)["q2"])


class TestSpreadMeasures(unittest.TestCase):
    def test_sample_variance_worked_example(self):
        assert_close(self, variance(SAMPLE), 32.0 / 7.0)

    def test_sample_std_worked_example(self):
        assert_close(self, std_dev(SAMPLE), 2.1380899353)

    def test_population_variance_worked_example_exact(self):
        self.assertEqual(variance(SAMPLE, 0), 4.0)

    def test_population_std_worked_example_exact(self):
        self.assertEqual(std_dev(SAMPLE, 0), 2.0)

    def test_std_is_sqrt_of_variance(self):
        assert_close(self, std_dev(SAMPLE) ** 2, variance(SAMPLE))

    def test_variance_single_element_ddof1_raises(self):
        with self.assertRaises(ValueError):
            variance([5.0])
        with self.assertRaises(ValueError):
            std_dev([5.0])

    def test_variance_zero_ddof_raises(self):
        # n - ddof <= 0 guard: ddof = 2 on a 2-element sample.
        with self.assertRaises(ValueError):
            variance([1.0, 2.0], 2)


class TestQuartilesAndSummary(unittest.TestCase):
    def test_quartiles_worked_example(self):
        q = quartiles(SAMPLE)
        assert_close(self, q["q1"], 4.0)
        assert_close(self, q["q2"], 4.5)
        assert_close(self, q["q3"], 5.5)

    def test_interquartile_range_worked_example(self):
        assert_close(self, interquartile_range(SAMPLE), 1.5)

    def test_five_number_summary_worked_example(self):
        fns = five_number_summary(SAMPLE)
        self.assertEqual(fns["min"], 2.0)
        self.assertEqual(fns["max"], 9.0)
        assert_close(self, fns["q1"], 4.0)
        assert_close(self, fns["median"], 4.5)
        assert_close(self, fns["q3"], 5.5)

    def test_percentile_linear_interpolation_midpoint(self):
        # rank 0.5 * 3 = 1.5 on four values blends the two middle ones.
        assert_close(self, percentile([0.0, 10.0, 20.0, 30.0], 0.5), 15.0)

    def test_percentile_endpoints(self):
        self.assertEqual(percentile([1.0, 2.0, 3.0, 4.0], 0.0), 1.0)
        self.assertEqual(percentile([1.0, 2.0, 3.0, 4.0], 1.0), 4.0)

    def test_cv_worked_example(self):
        assert_close(self, coefficient_of_variation(SAMPLE), 0.427617987059879)

    def test_cv_is_std_over_mean_identity(self):
        assert_close(
            self,
            coefficient_of_variation(SAMPLE),
            std_dev(SAMPLE) / mean(SAMPLE),
        )

    def test_summary_dict_complete(self):
        s = summary(SAMPLE)
        expected_keys = {
            "n", "mean", "median", "min", "max", "range",
            "sample_variance", "sample_std", "q1", "q3", "iqr",
            "five_number_summary", "coefficient_of_variation",
            "outlier_indices", "outlier_values",
        }
        self.assertEqual(set(s.keys()), expected_keys)
        self.assertEqual(s["n"], 8)
        self.assertEqual(s["outlier_indices"], [7])
        self.assertEqual(s["outlier_values"], [9.0])
        self.assertEqual(s["five_number_summary"]["min"], 2.0)


class TestOutlierRule(unittest.TestCase):
    def test_outlier_indices_worked_example_only_index_seven(self):
        self.assertEqual(outlier_indices_iqr(SAMPLE), [7])

    def test_outlier_values_worked_example(self):
        self.assertEqual([SAMPLE[i] for i in outlier_indices_iqr(SAMPLE)], [9.0])

    def test_low_value_above_fence_not_flagged(self):
        # 2 is not an outlier: the lower fence is 4.0 - 1.5 * 1.5 = 1.75.
        self.assertEqual(outlier_indices_iqr([2, 4, 4, 4, 5, 5, 7, 9]), [7])

    def test_value_exactly_on_fence_not_flagged(self):
        # 7.75 sits exactly on the upper fence q3 + 1.5 * iqr = 7.75.
        fence_sample = [2, 4, 4, 4, 5, 5, 7, 7.75]
        self.assertEqual(outlier_indices_iqr(fence_sample), [])

    def test_value_just_past_fence_flagged(self):
        fence_sample = [2, 4, 4, 4, 5, 5, 7, 7.76]
        self.assertEqual(outlier_indices_iqr(fence_sample), [7])

    def test_low_side_outlier_flagged(self):
        # Lower fence at 1.75 with q1 4.0, iqr 1.5: 1.5 is below it,
        # 2 was not. Expected indices [0, 7] in original order.
        sample = [1.5, 4, 4, 4, 5, 5, 7, 9]
        self.assertEqual(outlier_indices_iqr(sample), [0, 7])

    def test_iqr_factor_constant(self):
        self.assertEqual(IQR_FACTOR, 1.5)


class TestValueErrorRejections(unittest.TestCase):
    def test_empty_sample_raises_for_all_measures(self):
        for fn in (mean, median, data_range, variance, std_dev, quartiles,
                   interquartile_range, five_number_summary,
                   coefficient_of_variation, outlier_indices_iqr, summary):
            with self.assertRaises(ValueError):
                fn([])
        with self.assertRaises(ValueError):
            percentile([], 0.5)

    def test_percentile_p_outside_unit_interval_raises(self):
        with self.assertRaises(ValueError):
            percentile([1.0, 2.0, 3.0], -0.1)
        with self.assertRaises(ValueError):
            percentile([1.0, 2.0, 3.0], 1.1)

    def test_cv_zero_mean_raises(self):
        with self.assertRaises(ValueError):
            coefficient_of_variation([0.0, 0.0, 0.0])
        with self.assertRaises(ValueError):
            coefficient_of_variation([-2.0, 0.0, 2.0])

    def test_cv_single_element_raises_via_ddof(self):
        with self.assertRaises(ValueError):
            coefficient_of_variation([5.0])

    def test_summary_propagates_value_error(self):
        with self.assertRaises(ValueError):
            summary([])


class TestDeterminism(unittest.TestCase):
    def test_repeated_calls_identical(self):
        self.assertEqual(summary(SAMPLE), summary(SAMPLE))
        self.assertEqual(outlier_indices_iqr(SAMPLE), outlier_indices_iqr(SAMPLE))

    def test_unsorted_input_same_result(self):
        # Results are order independent for the measures; outliers keep
        # the original order of the caller's list.
        shuffled = [4, 7, 2, 5, 9, 4, 5, 4]
        assert_close(self, mean(shuffled), mean(SAMPLE))
        assert_close(self, median(shuffled), median(SAMPLE))
        assert_close(self, variance(shuffled), variance(SAMPLE))


if __name__ == "__main__":
    unittest.main()
