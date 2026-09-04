"""Contract test: gage linearity and bias study logic (stdlib unittest, offline).

Runs via `python3 scripts/test_gage_linearity_bias_study.py` from the repo
root; exit 0 on full pass. Covers the anchor worked example (masters
[2, 4, 6, 8, 10] mm, biases [0.07, 0.10, 0.16, 0.18, 0.24] mm) with the
spec magnitude bounds, ValueError rejections, the t formula identity, the
zero-dispersion convention, and the ACCEPT/REVIEW verdicts.
"""

import unittest

import gage_linearity_bias_study_logic as g

REFS = [2, 4, 6, 8, 10]
BIASES = [0.07, 0.10, 0.16, 0.18, 0.24]


class PerLevelBiasTests(unittest.TestCase):
    def test_anchor_pct_within_spec(self):
        pcts = [r["bias_pct_of_reference"]
                for r in g.per_level_bias(REFS, BIASES)]
        for val, spec in zip(pcts, [3.50, 2.50, 2.67, 2.25, 2.40]):
            self.assertAlmostEqual(val, spec, delta=1e-2)

    def test_anchor_bias_and_reference_values(self):
        rows = g.per_level_bias(REFS, BIASES)
        self.assertEqual([r["bias"] for r in rows], BIASES)
        self.assertEqual([r["reference"] for r in rows], REFS)

    def test_row_keys_and_pct_formula(self):
        rows = g.per_level_bias(REFS, BIASES)
        self.assertEqual(
            set(rows[0].keys()),
            {"reference", "bias", "bias_pct_of_reference"},
        )
        for r in rows:
            self.assertAlmostEqual(
                r["bias_pct_of_reference"],
                100.0 * r["bias"] / r["reference"],
            )

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            g.per_level_bias([2, 4, 6], [0.1, 0.2])

    def test_fewer_than_three_levels_raises(self):
        with self.assertRaises(ValueError):
            g.per_level_bias([2, 4], [0.1, 0.2])

    def test_non_increasing_references_raise(self):
        with self.assertRaises(ValueError):
            g.per_level_bias([2, 6, 4], [0.1, 0.2, 0.3])
        with self.assertRaises(ValueError):
            g.per_level_bias([2, 2, 4], [0.1, 0.2, 0.3])

    def test_non_positive_reference_raises(self):
        with self.assertRaises(ValueError):
            g.per_level_bias([0, 4, 6], [0.1, 0.2, 0.3])
        with self.assertRaises(ValueError):
            g.per_level_bias([-2, 4, 6], [0.1, 0.2, 0.3])


class MeanBiasTests(unittest.TestCase):
    def test_anchor_mean(self):
        self.assertAlmostEqual(g.mean_bias(BIASES), 0.150, delta=1e-6)

    def test_empty_raises_and_single_value(self):
        with self.assertRaises(ValueError):
            g.mean_bias([])
        self.assertEqual(g.mean_bias([0.05]), 0.05)


class LinearityRegressionTests(unittest.TestCase):
    def setUp(self):
        self.reg = g.linearity_regression(REFS, BIASES)

    def test_slope_and_intercept_within_spec(self):
        self.assertAlmostEqual(self.reg["slope"], 0.0210, delta=1e-4)
        self.assertAlmostEqual(self.reg["intercept"], 0.0240, delta=1e-3)

    def test_sse_and_r_squared_within_spec(self):
        self.assertAlmostEqual(self.reg["sse"], 0.00036, delta=1e-5)
        self.assertAlmostEqual(self.reg["r_squared"], 0.980, delta=1e-3)

    def test_keys_n_and_centroids(self):
        self.assertEqual(
            set(self.reg.keys()),
            {"slope", "intercept", "sse", "r_squared", "n", "xbar",
             "bias_bar"},
        )
        self.assertEqual(self.reg["n"], 5)
        self.assertAlmostEqual(self.reg["xbar"], 6.0)
        self.assertAlmostEqual(self.reg["bias_bar"], 0.150, delta=1e-6)

    def test_residuals_sum_zero_and_r2_identity(self):
        preds = [self.reg["intercept"] + self.reg["slope"] * x for x in REFS]
        resid_sum = sum(b - p for b, p in zip(BIASES, preds))
        self.assertLess(abs(resid_sum), 1e-9)
        bar = sum(BIASES) / len(BIASES)
        sst = sum((b - bar) ** 2 for b in BIASES)
        self.assertAlmostEqual(sst, 0.0180, delta=1e-6)
        self.assertAlmostEqual(
            self.reg["r_squared"], 1.0 - self.reg["sse"] / sst, delta=1e-9
        )

    def test_validation_mismatch_raises(self):
        with self.assertRaises(ValueError):
            g.linearity_regression([2, 4, 6], [0.1, 0.2])

    def test_zero_variation_degenerate_fit(self):
        reg = g.linearity_regression(REFS, [0.01] * 5)
        self.assertEqual(reg["slope"], 0.0)
        self.assertEqual(reg["intercept"], 0.01)
        self.assertEqual(reg["sse"], 0.0)
        self.assertEqual(reg["r_squared"], 1.0)


class BiasSignificanceTests(unittest.TestCase):
    def test_anchor_t_stat_within_spec(self):
        sig = g.bias_significance(BIASES)
        self.assertAlmostEqual(sig["t_stat"], 5.000, delta=1e-3)
        self.assertAlmostEqual(sig["t_crit"], 2.776, delta=1e-3)
        self.assertEqual(sig["df"], 4)
        self.assertTrue(sig["significant"])
        self.assertEqual(
            set(sig.keys()), {"t_stat", "t_crit", "df", "significant"}
        )

    def test_t_formula_identity(self):
        bar = sum(BIASES) / len(BIASES)
        s = (sum((b - bar) ** 2 for b in BIASES) / (len(BIASES) - 1)) ** 0.5
        t = bar / (s / len(BIASES) ** 0.5)
        self.assertAlmostEqual(
            g.bias_significance(BIASES)["t_stat"], t, delta=1e-9
        )

    def test_small_bias_not_significant(self):
        sig = g.bias_significance([0.01] * 5)
        self.assertFalse(sig["significant"])
        self.assertEqual(sig["t_stat"], 0.0)

    def test_zero_dispersion_convention(self):
        self.assertFalse(g.bias_significance([0.2] * 5)["significant"])

    def test_large_df_uses_normal_critical(self):
        sig = g.bias_significance([0.05 + 0.001 * i for i in range(22)])
        self.assertEqual(sig["df"], 21)
        self.assertAlmostEqual(sig["t_crit"], g.T_CRIT_LARGE_DF)
        self.assertTrue(sig["significant"])

    def test_fewer_than_three_raises(self):
        with self.assertRaises(ValueError):
            g.bias_significance([0.1, 0.2])

    def test_t_crit_table_and_band_constants(self):
        self.assertEqual(g.T_CRIT_95_TWOTAIL[1], 12.706)
        self.assertEqual(g.T_CRIT_95_TWOTAIL[10], 2.228)
        self.assertEqual(g.T_CRIT_95_TWOTAIL[20], 2.086)
        self.assertEqual(g.T_CRIT_LARGE_DF, 1.96)
        self.assertEqual(g.ACCEPTANCE_PCT_BAND, 10.0)


class GageBiasLinearityStudyTests(unittest.TestCase):
    def test_anchor_overall_review(self):
        study = g.gage_bias_linearity_study(REFS, BIASES)
        self.assertEqual(study["overall"], "REVIEW")
        self.assertAlmostEqual(study["mean_bias"], 0.150, delta=1e-6)
        self.assertEqual(study["regression"]["n"], 5)
        self.assertTrue(study["significance"]["significant"])

    def test_small_bias_overall_accept(self):
        study = g.gage_bias_linearity_study(REFS, [0.01] * 5)
        self.assertEqual(study["overall"], "ACCEPT")
        self.assertAlmostEqual(study["mean_bias"], 0.01)

    def test_anchor_worst_bias_and_band(self):
        study = g.gage_bias_linearity_study(REFS, BIASES)
        self.assertAlmostEqual(study["worst_bias_pct"], 3.50, delta=1e-2)
        self.assertEqual(study["worst_reference"], 2)
        self.assertTrue(study["per_level_acceptable"])

    def test_band_breach_review(self):
        study = g.gage_bias_linearity_study([2, 4, 6], [0.30, 0.05, 0.05])
        self.assertFalse(study["per_level_acceptable"])
        self.assertAlmostEqual(study["worst_bias_pct"], 15.0, delta=1e-6)
        self.assertEqual(study["overall"], "REVIEW")

    def test_keys_exact_and_levels(self):
        study = g.gage_bias_linearity_study(REFS, BIASES)
        self.assertEqual(
            set(study.keys()),
            {"per_level", "mean_bias", "regression", "significance",
             "worst_bias_pct", "worst_reference", "per_level_acceptable",
             "overall"},
        )
        self.assertEqual(len(study["per_level"]), 5)

    def test_deterministic(self):
        a = g.gage_bias_linearity_study(REFS, BIASES)
        b = g.gage_bias_linearity_study(REFS, BIASES)
        self.assertEqual(a["mean_bias"], b["mean_bias"])
        self.assertEqual(a["regression"], b["regression"])
        self.assertEqual(a["significance"], b["significance"])
        self.assertEqual(a["overall"], b["overall"])

    def test_study_validation_raises(self):
        with self.assertRaises(ValueError):
            g.gage_bias_linearity_study([2, 4, 6], [0.1, 0.2])


if __name__ == "__main__":
    unittest.main()
