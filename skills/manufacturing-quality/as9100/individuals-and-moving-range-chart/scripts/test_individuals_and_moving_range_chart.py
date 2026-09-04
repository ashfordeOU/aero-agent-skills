"""Offline contract test for the I-MR control chart logic (stdlib unittest).

Covers the worked-example bond-lot pull-off series, moving range and limit
identities, boundary cases, ValueError rejections, outlier flagging,
determinism, and the documented convenience dict keys. Runs offline in well
under 20 s: python3 test_individuals_and_moving_range_chart.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import individuals_and_moving_range_chart_logic as imr

# Worked example: 12 bond-lot pull-off force measurements, one destructive
# sample per lot. Real module outputs: mean 42.700, mr_bar 1.118,
# sigma_hat 0.991, UCL_X 45.674, LCL_X 39.726, UCL_MR 3.653.
WORKED = [42.1, 41.6, 43.0, 42.4, 41.2, 44.1, 43.5, 42.8, 41.9, 43.2, 44.0, 42.6]


class MovingRangesTests(unittest.TestCase):
    def test_moving_ranges_basic_sequence(self):
        self.assertEqual(imr.moving_ranges([1, 5, 2]), [4, 3])

    def test_moving_ranges_constant_series_all_zero(self):
        self.assertEqual(imr.moving_ranges([7.0] * 6), [0.0] * 5)

    def test_moving_ranges_count_n_minus_1(self):
        self.assertEqual(len(imr.moving_ranges(WORKED)), len(WORKED) - 1)

    def test_moving_ranges_two_values_single_range(self):
        self.assertEqual(imr.moving_ranges([10.0, 7.0]), [3.0])

    def test_moving_ranges_fewer_than_two_raises(self):
        for bad in ([], [42.1]):
            with self.assertRaises(ValueError):
                imr.moving_ranges(bad)

    def test_moving_ranges_magnitude_of_worked_series(self):
        mrs = imr.moving_ranges(WORKED)
        self.assertAlmostEqual(max(mrs), 2.9, delta=1e-9)
        self.assertAlmostEqual(sum(mrs), 12.3, delta=1e-9)


class IndividualsLimitsTests(unittest.TestCase):
    def test_individuals_limits_worked_example_mean(self):
        lims = imr.individuals_limits(WORKED)
        self.assertAlmostEqual(lims["mean"], 42.700, delta=1e-3)

    def test_individuals_limits_worked_example_mr_bar(self):
        lims = imr.individuals_limits(WORKED)
        self.assertAlmostEqual(lims["mr_bar"], 1.118, delta=1e-3)

    def test_individuals_limits_worked_example_sigma_hat(self):
        lims = imr.individuals_limits(WORKED)
        self.assertAlmostEqual(lims["sigma_hat"], 0.991, delta=1e-3)

    def test_individuals_limits_worked_example_x_limits(self):
        lims = imr.individuals_limits(WORKED)
        self.assertAlmostEqual(lims["UCL"], 45.674, delta=1e-3)
        self.assertAlmostEqual(lims["LCL"], 39.726, delta=1e-3)

    def test_individuals_limits_dict_keys_exact(self):
        keys = sorted(imr.individuals_limits(WORKED).keys())
        self.assertEqual(keys, ["LCL", "UCL", "mean", "mr_bar", "sigma_hat"])

    def test_individuals_limits_sigma_identity(self):
        lims = imr.individuals_limits(WORKED)
        self.assertAlmostEqual(lims["sigma_hat"], lims["mr_bar"] / imr.D2_N1,
                               delta=1e-12)

    def test_individuals_limits_constant_series_collapses(self):
        lims = imr.individuals_limits([5.0] * 8)
        self.assertEqual(lims["mean"], 5.0)
        self.assertEqual(lims["mr_bar"], 0.0)
        self.assertEqual(lims["sigma_hat"], 0.0)
        self.assertEqual(lims["UCL"], 5.0)
        self.assertEqual(lims["LCL"], 5.0)

    def test_individuals_limits_fewer_than_two_raises(self):
        for bad in ([], [42.1]):
            with self.assertRaises(ValueError):
                imr.individuals_limits(bad)

    def test_outlier_widens_individuals_limits(self):
        base = imr.individuals_limits(WORKED)
        ext = imr.individuals_limits(WORKED + [50.0])
        self.assertGreater(ext["UCL"] - ext["LCL"], base["UCL"] - base["LCL"])


class MovingRangeLimitsTests(unittest.TestCase):
    def test_moving_range_limits_worked_example(self):
        mr = imr.moving_range_limits(WORKED)
        self.assertAlmostEqual(mr["mr_bar"], 1.118, delta=1e-3)
        self.assertAlmostEqual(mr["UCL"], 3.653, delta=1e-3)

    def test_moving_range_limits_dict_keys_exact(self):
        self.assertEqual(sorted(imr.moving_range_limits(WORKED).keys()),
                         ["UCL", "mr_bar"])

    def test_moving_range_limits_ucl_factor(self):
        mr = imr.moving_range_limits(WORKED)
        self.assertAlmostEqual(mr["UCL"], imr.D3_MR_UCL * mr["mr_bar"],
                               delta=1e-12)

    def test_moving_range_limits_fewer_than_two_raises(self):
        for bad in ([], [42.1]):
            with self.assertRaises(ValueError):
                imr.moving_range_limits(bad)


class FlaggingTests(unittest.TestCase):
    def test_flag_points_flags_outside_values(self):
        flags = imr.flag_points([39.5, 42.7, 46.0], 45.674, 39.726)
        self.assertEqual(flags, [0, 2])

    def test_flag_points_value_at_limit_not_flagged(self):
        flags = imr.flag_points([45.674, 39.726, 42.7], 45.674, 39.726)
        self.assertEqual(flags, [])

    def test_flag_points_empty_raises(self):
        with self.assertRaises(ValueError):
            imr.flag_points([], 1.0, 0.0)

    def test_stability_verdict_in_control(self):
        self.assertEqual(imr.stability_verdict([], []), "in-control")

    def test_stability_verdict_out_of_control_individual(self):
        self.assertEqual(imr.stability_verdict([3], []), "out-of-control")

    def test_stability_verdict_out_of_control_moving_range(self):
        self.assertEqual(imr.stability_verdict([], [1]), "out-of-control")


class ImrSummaryTests(unittest.TestCase):
    def test_imr_summary_worked_example_fields(self):
        s = imr.imr_summary(WORKED)
        self.assertAlmostEqual(s["mean"], 42.700, delta=1e-3)
        self.assertAlmostEqual(s["mr_bar"], 1.118, delta=1e-3)
        self.assertAlmostEqual(s["sigma_hat"], 0.991, delta=1e-3)
        self.assertAlmostEqual(s["x_ucl"], 45.674, delta=1e-3)
        self.assertAlmostEqual(s["x_lcl"], 39.726, delta=1e-3)
        self.assertAlmostEqual(s["mr_ucl"], 3.653, delta=1e-3)

    def test_imr_summary_worked_example_verdict_in_control(self):
        s = imr.imr_summary(WORKED)
        self.assertEqual(s["flagged_individuals"], [])
        self.assertEqual(s["flagged_moving_ranges"], [])
        self.assertEqual(s["verdict"], "in-control")

    def test_imr_summary_dict_keys_exact(self):
        keys = list(imr.imr_summary(WORKED).keys())
        self.assertEqual(keys, ["mean", "mr_bar", "sigma_hat", "x_ucl",
                                "x_lcl", "mr_ucl", "flagged_individuals",
                                "flagged_moving_ranges", "verdict"])

    def test_outlier_individual_flagged_at_index_12(self):
        s = imr.imr_summary(WORKED + [50.0])
        self.assertEqual(s["flagged_individuals"], [12])
        self.assertEqual(s["verdict"], "out-of-control")

    def test_large_moving_range_flags_its_position(self):
        s = imr.imr_summary(WORKED + [50.0])
        self.assertEqual(s["flagged_moving_ranges"], [11])

    def test_imr_summary_fewer_than_two_raises(self):
        with self.assertRaises(ValueError):
            imr.imr_summary([42.1])

    def test_determinism_identical_inputs(self):
        self.assertEqual(imr.imr_summary(WORKED), imr.imr_summary(WORKED))


class TwoValueAndIdentityTests(unittest.TestCase):
    def test_two_value_mr_bar_equals_absolute_difference(self):
        s = imr.imr_summary([12.5, 10.0])
        self.assertAlmostEqual(s["mr_bar"], abs(12.5 - 10.0), delta=1e-12)

    def test_two_value_ucl_x_identity(self):
        s = imr.imr_summary([12.5, 10.0])
        expected = 11.25 + 2.66 * 2.5
        self.assertAlmostEqual(s["x_ucl"], expected, delta=1e-12)
        self.assertAlmostEqual(s["x_lcl"], 11.25 - 2.66 * 2.5, delta=1e-12)

    def test_two_value_sigma_hat_identity(self):
        s = imr.imr_summary([12.5, 10.0])
        self.assertAlmostEqual(s["sigma_hat"], 2.5 / imr.D2_N1, delta=1e-12)
        self.assertAlmostEqual(s["mr_ucl"], 3.267 * 2.5, delta=1e-12)


if __name__ == "__main__":
    unittest.main()
