"""Contract test for multiple_linear_regression_logic (wave-38).

Offline, deterministic, stdlib unittest only. Run from the repo root:

    python3 skills/cross-cutting/numerics/multiple-linear-regression/scripts/test_multiple_linear_regression.py

Covers the spec worked example (x1 = 1..6, x2 = 2,3,5,7,11,13,
y = 5,7,9,13,15,19), the prep-verified anchors (coef, r2, adjusted r2,
sigma2, RSS, coefficient standard errors, t statistics, VIF, prediction),
the single-predictor closed-form identity, the adjusted-r2 and residual
bounds, VIF identities, determinism, and ValueError rejection of every
non-physical input.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import multiple_linear_regression_logic as mlr

# Worked example from the leaf spec (n = 6, p = 2).
X = [[1.0, 2.0], [2.0, 3.0], [3.0, 5.0],
     [4.0, 7.0], [5.0, 11.0], [6.0, 13.0]]
Y = [5.0, 7.0, 9.0, 13.0, 15.0, 19.0]

# Real module outputs (pins) and prep-verified anchor bounds.
COEF = [1.9141104294, 2.1042944785, 0.3006134969]
COEF_ANCHOR = [1.9141, 2.1043, 0.3006]
R2 = 0.9867026741
ADJ_R2 = 0.9778377902
SIGMA2 = 0.6175869121
RSS = 1.8527607362
COEF_SE = [0.9243331162, 1.0491275895, 0.4460000336]
COEF_SE_ANCHOR = [0.9243, 1.0491, 0.4460]
T_STATS = [2.0708015281, 2.0057564967, 0.6740212428]
T_ANCHOR = [2.0708, 2.0058, 0.6740]
P_VALUES = [0.1301422879, 0.1385512810, 0.5485847960]
F_STAT = 111.3046357616
F_P_VALUE = 0.0015333683
FITTED = [4.6196319018, 7.0245398773, 9.7300613497,
          12.4355828221, 15.7423312883, 18.4478527607]
VIF = 31.188650
PREDICT_AT = 21.153374

# Single-predictor scatter set for the closed-form reduction identity.
XS1 = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
YS1 = [5.0, 7.0, 9.5, 13.0, 14.5, 19.0]


class TestDesignMatrix(unittest.TestCase):
    """Intercept-augmented predictor layout."""

    def test_design_matrix_prepends_ones(self):
        self.assertEqual(mlr.design_matrix([[1.0, 2.0], [3.0, 4.0]]),
                         [[1.0, 1.0, 2.0], [1.0, 3.0, 4.0]])

    def test_design_matrix_leaves_input_untouched(self):
        source = [[1.0, 2.0], [3.0, 4.0]]
        mlr.design_matrix(source)
        self.assertEqual(source, [[1.0, 2.0], [3.0, 4.0]])

    def test_design_matrix_empty_raises(self):
        with self.assertRaises(ValueError):
            mlr.design_matrix([])

    def test_design_matrix_ragged_rows_raise(self):
        with self.assertRaises(ValueError):
            mlr.design_matrix([[1.0, 2.0], [3.0]])

    def test_design_matrix_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            mlr.design_matrix([[1.0, "a"], [2.0, 3.0]])


class TestWorkedExampleFit(unittest.TestCase):
    """Spec anchors on x1 = 1..6, x2 = 2,3,5,7,11,13, y = 5,7,9,13,15,19."""

    def test_coefficients_match_anchor(self):
        fit = mlr.ols_fit(X, Y)
        for real, pin, anchor in zip(fit["coef"], COEF, COEF_ANCHOR):
            self.assertAlmostEqual(real, pin, places=6)
            self.assertAlmostEqual(real, anchor, places=4)

    def test_r2_and_adjusted_r2_within_anchor_bounds(self):
        fit = mlr.ols_fit(X, Y)
        self.assertAlmostEqual(fit["r2"], R2, places=9)
        self.assertAlmostEqual(fit["r2"], 0.9867, places=4)
        self.assertAlmostEqual(fit["adjusted_r2"], ADJ_R2, places=9)
        self.assertAlmostEqual(fit["adjusted_r2"], 0.9778, places=4)
        self.assertLessEqual(fit["adjusted_r2"], fit["r2"])

    def test_sigma2_and_rss_anchors(self):
        fit = mlr.ols_fit(X, Y)
        self.assertAlmostEqual(fit["sigma2"], SIGMA2, places=9)
        self.assertAlmostEqual(fit["sigma2"], 0.61759, places=4)
        self.assertAlmostEqual(fit["rss"], RSS, places=9)
        self.assertAlmostEqual(fit["rss"], 1.8528, places=4)

    def test_coefficient_standard_errors(self):
        fit = mlr.ols_fit(X, Y)
        for real, pin, anchor in zip(fit["coef_se"], COEF_SE,
                                     COEF_SE_ANCHOR):
            self.assertAlmostEqual(real, pin, places=9)
            self.assertAlmostEqual(real, anchor, places=4)

    def test_t_statistics_within_anchor_bounds(self):
        fit = mlr.ols_fit(X, Y)
        for real, pin, anchor in zip(fit["t_stats"], T_STATS, T_ANCHOR):
            self.assertAlmostEqual(real, pin, places=9)
            self.assertAlmostEqual(real, anchor, places=3)

    def test_result_keys_and_p_values_in_unit_interval(self):
        fit = mlr.ols_fit(X, Y)
        for key in ("coef", "rss", "r2", "adjusted_r2", "sigma2",
                    "coef_se", "t_stats", "p_values", "f_stat",
                    "f_p_value", "residuals", "fitted"):
            self.assertIn(key, fit)
        self.assertEqual(len(fit["coef"]), 3)
        for value in fit["p_values"]:
            self.assertGreater(value, 0.0)
            self.assertLess(value, 1.0)

    def test_f_statistic_identity_and_pin(self):
        fit = mlr.ols_fit(X, Y)
        mean_y = sum(Y) / len(Y)
        tss = sum((v - mean_y) ** 2 for v in Y)
        expected = ((tss - fit["rss"]) / 2.0) / (fit["rss"] / 3.0)
        self.assertAlmostEqual(fit["f_stat"], expected, places=6)
        self.assertAlmostEqual(fit["f_stat"], F_STAT, places=5)

    def test_f_p_value_in_unit_interval(self):
        fit = mlr.ols_fit(X, Y)
        self.assertGreater(fit["f_p_value"], 0.0)
        self.assertLess(fit["f_p_value"], 1.0)
        self.assertAlmostEqual(fit["f_p_value"], F_P_VALUE, places=9)

    def test_residuals_sum_near_zero(self):
        fit = mlr.ols_fit(X, Y)
        self.assertLess(abs(sum(fit["residuals"])), 1e-9)

    def test_fitted_values_roundtrip_predict(self):
        fit = mlr.ols_fit(X, Y)
        for value, row in zip(fit["fitted"], X):
            self.assertAlmostEqual(value,
                                   mlr.predict(fit["coef"], row), places=9)
        for real, value in zip(fit["fitted"], FITTED):
            self.assertAlmostEqual(real, value, places=6)


class TestPredict(unittest.TestCase):
    """Prediction at a new design point."""

    def test_predict_anchor_value(self):
        fit = mlr.ols_fit(X, Y)
        prediction = mlr.predict(fit["coef"], [7.0, 15.0])
        self.assertAlmostEqual(prediction, PREDICT_AT, places=6)
        self.assertAlmostEqual(prediction, 21.153, places=3)

    def test_predict_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            mlr.predict([1.0, 2.0, 3.0], [1.0])

    def test_predict_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            mlr.predict([1.0, 2.0, 3.0], [1.0, "b"])

    def test_predict_is_linear_combination(self):
        coef = [2.0, 3.0, 4.0]
        self.assertAlmostEqual(mlr.predict(coef, [1.0, 1.0]),
                               9.0, places=12)
        self.assertAlmostEqual(mlr.predict(coef, [0.0, 0.0]),
                               2.0, places=12)


class TestVarianceInflation(unittest.TestCase):
    """Multicollinearity measure per predictor."""

    def test_vif_anchor_both_predictors(self):
        fit_vif0 = mlr.variance_inflation_factor(X, 0)
        fit_vif1 = mlr.variance_inflation_factor(X, 1)
        for value in (fit_vif0, fit_vif1):
            self.assertAlmostEqual(value, VIF, places=3)
            self.assertAlmostEqual(value, 31.19, delta=0.1)
        self.assertAlmostEqual(fit_vif0, fit_vif1, places=9)

    def test_vif_single_predictor_is_one(self):
        self.assertEqual(
            mlr.variance_inflation_factor([[1.0], [2.0], [3.0], [4.0]], 0),
            1.0)

    def test_vif_index_out_of_range_raises(self):
        for bad in (-1, 2, 0.5, "x"):
            with self.assertRaises(ValueError):
                mlr.variance_inflation_factor(X, bad)

    def test_vif_low_for_mild_collinearity(self):
        mild = [[1.0, 8.0], [2.0, -3.0], [3.0, 12.0],
                [4.0, 5.0], [5.0, -7.0], [6.0, 20.0]]
        for j in (0, 1):
            value = mlr.variance_inflation_factor(mild, j)
            self.assertGreater(value, 1.0)
            self.assertLess(value, 2.0)

    def test_vif_matches_aux_r2_identity(self):
        aux = mlr.ols_fit([[row[1]] for row in X], [row[0] for row in X])
        self.assertAlmostEqual(mlr.variance_inflation_factor(X, 0),
                               1.0 / (1.0 - aux["r2"]), places=9)


class TestSinglePredictorReduction(unittest.TestCase):
    """With one predictor the OLS fit reduces to the closed-form line."""

    def test_single_predictor_matches_closed_form(self):
        fit = mlr.ols_fit([[v] for v in XS1], YS1)
        n = len(XS1)
        xbar = sum(XS1) / n
        ybar = sum(YS1) / n
        sxx = sum((x - xbar) ** 2 for x in XS1)
        sxy = sum((x - xbar) * (y - ybar) for x, y in zip(XS1, YS1))
        slope = sxy / sxx
        intercept = ybar - slope * xbar
        self.assertAlmostEqual(fit["coef"][0], intercept, places=9)
        self.assertAlmostEqual(fit["coef"][1], slope, places=9)

    def test_single_predictor_r2_matches_product_formula(self):
        fit = mlr.ols_fit([[v] for v in XS1], YS1)
        n = len(XS1)
        xbar = sum(XS1) / n
        ybar = sum(YS1) / n
        sxx = sum((x - xbar) ** 2 for x in XS1)
        syy = sum((y - ybar) ** 2 for y in YS1)
        sxy = sum((x - xbar) * (y - ybar) for x, y in zip(XS1, YS1))
        self.assertAlmostEqual(fit["r2"], sxy * sxy / (sxx * syy),
                               places=9)


class TestValueErrorRejection(unittest.TestCase):
    """Non-physical inputs raise ValueError."""

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            mlr.ols_fit(X, Y[:-1])

    def test_too_few_rows_raises(self):
        with self.assertRaises(ValueError):
            mlr.ols_fit(X[:3], Y[:3])

    def test_non_numeric_x_entry_raises(self):
        with self.assertRaises(ValueError):
            mlr.ols_fit([[1.0, "a"], [2.0, 3.0], [3.0, 5.0],
                         [4.0, 7.0], [5.0, 11.0], [6.0, 13.0]], Y)

    def test_empty_x_raises(self):
        with self.assertRaises(ValueError):
            mlr.ols_fit([], [])

    def test_non_numeric_y_entry_raises(self):
        with self.assertRaises(ValueError):
            mlr.ols_fit(X, [5.0, 7.0, "x", 13.0, 15.0, 19.0])

    def test_ragged_x_rows_raise(self):
        with self.assertRaises(ValueError):
            mlr.ols_fit([[1.0, 2.0], [2.0], [3.0, 5.0],
                         [4.0, 7.0], [5.0, 11.0], [6.0, 13.0]], Y)

    def test_constant_response_raises(self):
        with self.assertRaises(ValueError):
            mlr.ols_fit(X, [5.0] * 6)

    def test_singular_collinear_design_raises(self):
        collinear = [[1.0, 2.0], [2.0, 4.0], [3.0, 6.0],
                     [4.0, 8.0], [5.0, 10.0], [6.0, 12.0]]
        with self.assertRaises(ValueError):
            mlr.ols_fit(collinear, Y)


class TestDeterminism(unittest.TestCase):
    """Repeated fits on identical input give identical output."""

    def test_ols_fit_is_deterministic(self):
        first = mlr.ols_fit(X, Y)
        second = mlr.ols_fit([row[:] for row in X], Y[:])
        self.assertEqual(first["coef"], second["coef"])
        self.assertEqual(first["r2"], second["r2"])
        self.assertEqual(first["p_values"], second["p_values"])
        self.assertEqual(first["f_stat"], second["f_stat"])


if __name__ == "__main__":
    unittest.main()
