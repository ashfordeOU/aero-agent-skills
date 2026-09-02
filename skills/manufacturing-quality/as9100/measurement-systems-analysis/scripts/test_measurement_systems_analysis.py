#!/usr/bin/env python3
"""Gate 3 contract test: measurement systems analysis (Gage R and R).

Exercises scripts/measurement_systems_analysis_logic.py (stdlib
unittest, offline). Contract: docs/harness-contract.md gate 3 - the
range-based Gage repeatability and reproducibility study: equipment
variation EV from the average range, appraiser variation AV from the
spread of appraiser averages (clamped to zero on a negative radicand),
combined GRR, part variation PV, total variation TV, percent GRR with
the acceptance bands (under 10 acceptable, 10 to 30 conditional, over
30 unacceptable), number of distinct categories, and ValueError on
malformed tables (empty, inconsistent dimensions, negative values).

All expected values are hand-computed (see each docstring) with the
standard published range-method constants: K1 4.56/3.05 for 2/3
trials, K2 3.65/2.70 for 2/3 appraisers, K3 3.65/2.70/2.30 for 2/3/4
parts.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import measurement_systems_analysis_logic as msa  # noqa: E402


# Three appraisers (A, B, C) x three parts x two trials. Every cell
# range is 2 so rbar = 2, EV = 4.56 * 2 = 9.12. Appraiser averages are
# 21, 23, 22 so xdiff = 2 and AV = sqrt((2.70*2)^2 - 9.12^2/6) =
# sqrt(29.16 - 13.8624) = sqrt(15.2976) = 3.911215. GRR =
# sqrt(9.12^2 + 3.911215^2) = sqrt(98.472) = 9.923306. Part averages
# 12, 22, 32 give Rp = 20 and PV = 2.70 * 20 = 54. TV =
# sqrt(98.472 + 2916) = sqrt(3014.472) = 54.904207. Percent GRR =
# 100 * 9.923306 / 54.904207 = 18.073853 (conditional). ndc =
# floor(1.41 * 54 / 9.923306) = floor(7.6728) = 7.
D1 = {
    "A": [[10, 12], [20, 22], [30, 32]],
    "B": [[12, 14], [22, 24], [32, 34]],
    "C": [[11, 13], [21, 23], [31, 33]],
}

# Two appraisers x three parts x two trials. Every cell range is 0.1
# so rbar = 0.1, EV = 4.56 * 0.1 = 0.456. Appraiser averages are both
# 20.05 so xdiff = 0 and AV = 0 (radicand negative, clamped). GRR =
# 0.456. Part averages 10.05, 20.05, 30.05 give Rp = 20, PV = 54. TV
# = sqrt(0.207936 + 2916) = 54.001925. Percent GRR = 0.844414
# (acceptable). ndc = floor(1.41 * 54 / 0.456) = floor(166.974) = 166.
D2 = {
    "A": [[10, 10.1], [20, 20.1], [30, 30.1]],
    "B": [[10.1, 10], [20.1, 20], [30.1, 30]],
}

# Three appraisers x three parts x two trials. Every cell range is 2
# so EV = 9.12. Appraiser averages 21, 27, 24 give xdiff = 6 and AV =
# sqrt((2.70*6)^2 - 9.12^2/6) = sqrt(262.44 - 13.8624) =
# sqrt(248.5776) = 15.766344. GRR = sqrt(83.1744 + 248.5776) =
# sqrt(331.752) = 18.214061. Part averages 14, 24, 34 give PV = 54.
# TV = sqrt(331.752 + 2916) = 56.989052. Percent GRR = 31.960631
# (unacceptable). ndc = floor(1.41 * 54 / 18.214061) = floor(4.1802)
# = 4.
D3 = {
    "A": [[10, 12], [20, 22], [30, 32]],
    "B": [[16, 18], [26, 28], [36, 38]],
    "C": [[13, 15], [23, 25], [33, 35]],
}

# Two appraisers with identical tables: every cell range is 1 so EV =
# 4.56, appraiser averages are both 20.5 so xdiff = 0 and the radicand
# (0 - 4.56^2/6) is negative, clamping AV to 0. GRR = 4.56. Percent
# GRR = 8.414496 (acceptable). ndc = floor(1.41 * 54 / 4.56) =
# floor(16.697) = 16.
D4 = {
    "A": [[10, 11], [20, 21], [30, 31]],
    "B": [[10, 11], [20, 21], [30, 31]],
}

# Two appraisers x two parts x two trials: K2 = 3.65, K3 = 3.65. Every
# cell range is 1 so EV = 4.56. Averages 15.5 and 17.5 give xdiff = 2
# and AV = sqrt((3.65*2)^2 - 4.56^2/4) = sqrt(53.29 - 5.1984) =
# sqrt(48.0916) = 6.934811. GRR = sqrt(20.7936 + 48.0916) =
# sqrt(68.8852) = 8.299711. Part averages 11.5, 21.5 give Rp = 10 and
# PV = 3.65 * 10 = 36.5. TV = sqrt(68.8852 + 1332.25) = 37.431741.
# Percent GRR = 22.172923 (conditional). ndc = floor(1.41 * 36.5 /
# 8.299711) = floor(6.2017) = 6.
D5 = {
    "A": [[10, 11], [20, 21]],
    "B": [[12, 13], [22, 23]],
}

# Identical readings within every cell: GRR = 0, so ndc is undefined
# (None) and percent GRR is 0 (acceptable). PV = 3.65 * 10 = 36.5 and
# TV = 36.5 because the two parts differ by 10.
D6 = {
    "A": [[10, 10], [20, 20]],
    "B": [[10, 10], [20, 20]],
}

# Every reading identical everywhere: EV = AV = GRR = PV = TV = 0, all
# percents 0, verdict acceptable, ndc None.
D7 = {
    "A": [[10, 10], [10, 10]],
    "B": [[10, 10], [10, 10]],
}

# Three trials: K1 = 3.05. Every cell range is 2 so rbar = 2, EV =
# 3.05 * 2 = 6.1. Averages 94/6 and 100/6 give xdiff = 1 and AV =
# sqrt((2.70*1)^2 - 6.1^2/6) = sqrt(7.29 - 6.201667) =
# sqrt(1.088333) = 2.668489. GRR = sqrt(37.21 + 1.088333) =
# sqrt(38.298333) = 6.658140. Part averages 67/6 and 127/6 give
# Rp = 10 and PV = 3.65 * 10 = 36.5. TV = sqrt(38.298333 + 1332.25) =
# 37.102302. Percent GRR = 17.945356 (conditional). ndc =
# floor(1.41 * 36.5 / 6.658140) = floor(7.7287) = 7.
D8 = {
    "A": [[10, 10, 12], [20, 20, 22]],
    "B": [[11, 11, 13], [21, 21, 23]],
}


class EquipmentVariationTest(unittest.TestCase):
    def test_d1_two_trials(self):
        # K1(2) = 4.56, rbar = 2: EV = 9.12.
        self.assertAlmostEqual(msa.equipment_variation(D1), 9.12, places=5)

    def test_d5_rbar_one(self):
        # K1(2) = 4.56, rbar = 1: EV = 4.56.
        self.assertAlmostEqual(msa.equipment_variation(D5), 4.56, places=5)

    def test_d8_three_trials(self):
        # K1(3) = 3.05, rbar = 2: EV = 6.1.
        self.assertAlmostEqual(msa.equipment_variation(D8), 6.1, places=5)

    def test_zero_ranges_give_zero_ev(self):
        self.assertEqual(msa.equipment_variation(D7), 0.0)


class AppraiserVariationTest(unittest.TestCase):
    def test_d1_spread(self):
        # xdiff = 2, K2(3) = 2.70, EV = 9.12, trials*parts = 6.
        self.assertAlmostEqual(msa.appraiser_variation(D1), 3.911215, places=5)

    def test_d5_two_appraisers(self):
        # xdiff = 2, K2(2) = 3.65, EV = 4.56, trials*parts = 4.
        self.assertAlmostEqual(msa.appraiser_variation(D5), 6.934811, places=5)

    def test_d8_three_trials(self):
        # xdiff = 1, K2(3) = 2.70, EV = 6.1, trials*parts = 6.
        self.assertAlmostEqual(msa.appraiser_variation(D8), 2.668489, places=5)

    def test_negative_radicand_clamps_to_zero(self):
        # Identical appraiser averages: xdiff = 0, radicand negative.
        self.assertEqual(msa.appraiser_variation(D4), 0.0)


class GrrVariationTest(unittest.TestCase):
    def test_d1_grr(self):
        # sqrt(9.12^2 + 3.911215^2) = sqrt(98.472) = 9.923306.
        self.assertAlmostEqual(msa.grr_variation(D1), 9.923306, places=5)

    def test_grr_equals_ev_when_av_zero(self):
        self.assertAlmostEqual(msa.grr_variation(D4), 4.56, places=5)

    def test_d8_grr(self):
        self.assertAlmostEqual(msa.grr_variation(D8), 6.658140, places=5)


class PartVariationTest(unittest.TestCase):
    def test_d1_pv(self):
        # Rp = 20, K3(3) = 2.70: PV = 54.
        self.assertAlmostEqual(msa.part_variation(D1), 54.0, places=5)

    def test_d5_pv(self):
        # Rp = 10, K3(2) = 3.65: PV = 36.5.
        self.assertAlmostEqual(msa.part_variation(D5), 36.5, places=5)

    def test_d7_zero_part_spread(self):
        self.assertEqual(msa.part_variation(D7), 0.0)


class TotalVariationTest(unittest.TestCase):
    def test_d1_tv(self):
        # sqrt(9.923306^2 + 54^2) = sqrt(3014.472) = 54.904207.
        self.assertAlmostEqual(msa.total_variation(D1), 54.904207, places=5)

    def test_tv_exceeds_components(self):
        tv = msa.total_variation(D1)
        self.assertGreater(tv, msa.grr_variation(D1))
        self.assertGreater(tv, msa.part_variation(D1))


class PercentGrrAndVerdictTest(unittest.TestCase):
    def test_d1_conditional(self):
        s = msa.study_summary(D1)
        self.assertAlmostEqual(s["grr_pct"], 18.073853, places=5)
        self.assertEqual(s["verdict"], "conditional")

    def test_d2_acceptable(self):
        s = msa.study_summary(D2)
        self.assertAlmostEqual(s["grr_pct"], 0.844414, places=5)
        self.assertEqual(s["verdict"], "acceptable")

    def test_d3_unacceptable(self):
        s = msa.study_summary(D3)
        self.assertAlmostEqual(s["grr_pct"], 31.960631, places=5)
        self.assertEqual(s["verdict"], "unacceptable")

    def test_d4_acceptable(self):
        s = msa.study_summary(D4)
        self.assertAlmostEqual(s["grr_pct"], 8.414496, places=5)
        self.assertEqual(s["verdict"], "acceptable")

    def test_d5_conditional(self):
        s = msa.study_summary(D5)
        self.assertAlmostEqual(s["grr_pct"], 22.172923, places=5)
        self.assertEqual(s["verdict"], "conditional")

    def test_d8_conditional(self):
        s = msa.study_summary(D8)
        self.assertAlmostEqual(s["grr_pct"], 17.945356, places=5)
        self.assertEqual(s["verdict"], "conditional")

    def test_percent_components_sum_to_tv(self):
        s = msa.study_summary(D1)
        # GRR and PV are orthogonal: grr_pct^2 + pv_pct^2 ~= 100^2.
        self.assertAlmostEqual(
            s["grr_pct"] ** 2 + s["pv_pct"] ** 2, 100.0 ** 2, places=2
        )

    def test_verdict_band_boundaries(self):
        self.assertEqual(msa.acceptance_verdict(9.99), "acceptable")
        self.assertEqual(msa.acceptance_verdict(10.0), "conditional")
        self.assertEqual(msa.acceptance_verdict(30.0), "conditional")
        self.assertEqual(msa.acceptance_verdict(30.01), "unacceptable")

    def test_negative_percent_raises(self):
        with self.assertRaises(ValueError):
            msa.acceptance_verdict(-1.0)


class DistinctCategoriesTest(unittest.TestCase):
    def test_d1_ndc(self):
        # floor(1.41 * 54 / 9.923306) = floor(7.6728) = 7.
        self.assertEqual(
            msa.number_distinct_categories(
                msa.part_variation(D1), msa.grr_variation(D1)
            ),
            7,
        )

    def test_d2_ndc(self):
        self.assertEqual(
            msa.number_distinct_categories(
                msa.part_variation(D2), msa.grr_variation(D2)
            ),
            166,
        )

    def test_d3_ndc(self):
        # floor(1.41 * 54 / 18.214061) = floor(4.1802) = 4.
        self.assertEqual(
            msa.number_distinct_categories(
                msa.part_variation(D3), msa.grr_variation(D3)
            ),
            4,
        )

    def test_zero_grr_returns_none(self):
        self.assertIsNone(msa.number_distinct_categories(36.5, 0.0))

    def test_negative_input_raises(self):
        with self.assertRaises(ValueError):
            msa.number_distinct_categories(-1.0, 2.0)
        with self.assertRaises(ValueError):
            msa.number_distinct_categories(2.0, -1.0)


class ZeroTotalVariationTest(unittest.TestCase):
    def test_d7_zero_tv_summary(self):
        s = msa.study_summary(D7)
        self.assertEqual(s["ev"], 0.0)
        self.assertEqual(s["av"], 0.0)
        self.assertEqual(s["grr"], 0.0)
        self.assertEqual(s["pv"], 0.0)
        self.assertEqual(s["tv"], 0.0)
        self.assertEqual(s["grr_pct"], 0.0)
        self.assertEqual(s["verdict"], "acceptable")
        self.assertIsNone(s["ndc"])

    def test_d6_zero_grr_but_parts_differ(self):
        s = msa.study_summary(D6)
        self.assertEqual(s["grr"], 0.0)
        self.assertAlmostEqual(s["pv"], 36.5, places=5)
        self.assertEqual(s["verdict"], "acceptable")
        self.assertIsNone(s["ndc"])


class ValidationTest(unittest.TestCase):
    def test_empty_table_raises(self):
        with self.assertRaises(ValueError):
            msa.study_summary({})

    def test_single_appraiser_raises(self):
        with self.assertRaises(ValueError):
            msa.study_summary({"A": [[10, 11], [20, 21]]})

    def test_four_appraisers_raise(self):
        with self.assertRaises(ValueError):
            msa.study_summary(
                {
                    "A": [[10, 11], [20, 21]],
                    "B": [[10, 11], [20, 21]],
                    "C": [[10, 11], [20, 21]],
                    "D": [[10, 11], [20, 21]],
                }
            )

    def test_inconsistent_part_counts_raise(self):
        with self.assertRaises(ValueError):
            msa.study_summary(
                {"A": [[10, 11], [20, 21]], "B": [[10, 11], [20, 21], [30, 31]]}
            )

    def test_inconsistent_trial_counts_raise(self):
        with self.assertRaises(ValueError):
            msa.study_summary({"A": [[10, 11], [20, 21]], "B": [[10, 11, 12], [20, 21, 22]]})

    def test_single_trial_raises(self):
        with self.assertRaises(ValueError):
            msa.study_summary({"A": [[10], [20]], "B": [[10], [20]]})

    def test_four_trials_raise(self):
        with self.assertRaises(ValueError):
            msa.study_summary(
                {"A": [[10, 11, 12, 13], [20, 21, 22, 23]],
                 "B": [[10, 11, 12, 13], [20, 21, 22, 23]]}
            )

    def test_single_part_raises(self):
        with self.assertRaises(ValueError):
            msa.study_summary({"A": [[10, 11]], "B": [[10, 11]]})

    def test_eleven_parts_raise(self):
        parts_a = [[10.0 + i, 10.0 + i + 1] for i in range(11)]
        parts_b = [[10.0 + i, 10.0 + i + 1] for i in range(11)]
        with self.assertRaises(ValueError):
            msa.study_summary({"A": parts_a, "B": parts_b})

    def test_negative_value_raises(self):
        with self.assertRaises(ValueError):
            msa.study_summary({"A": [[10, -1], [20, 21]], "B": [[10, 11], [20, 21]]})

    def test_non_numeric_value_raises(self):
        with self.assertRaises(ValueError):
            msa.study_summary({"A": [[10, "x"], [20, 21]], "B": [[10, 11], [20, 21]]})

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            msa.study_summary([[[10, 11], [20, 21]]])

    def test_empty_appraiser_raises(self):
        with self.assertRaises(ValueError):
            msa.study_summary({"A": [], "B": [[10, 11], [20, 21]]})


if __name__ == "__main__":
    unittest.main()
