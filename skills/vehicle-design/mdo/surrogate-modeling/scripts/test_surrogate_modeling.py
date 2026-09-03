"""test_surrogate_modeling.py - contract test for the surrogate-modeling leaf.

Deterministic stdlib unittest suite (offline, no network, exit 0 in
well under 20 s). Asserts the worked-example anchors of the wave-26
surrogate-modeling spec against real outputs of
surrogate_modeling_logic:

1. Exact quadratic coefficient recovery on the 9-point grid of
   f = 1 + 2 x1 + 3 x2 + 4 x1^2 - x1 x2 + 0.5 x2^2 (within 1e-6).
2. predict_quadratic at (0.5, -0.5) equals the analytic 1.875.
3. Exact RBF interpolation on the same samples (eps default 0.5).
4. RBF leave-one-out RMSE below the quadratic one on the nonlinear
   target g = f + 0.3 sin(2 x1). Note: on the 3-level grid {-1, 0, 1}
   the sine is exactly linear (sin(2 x1) = sin(2) * x1 at those three
   abscissae), so it is absorbed by the quadratic basis. The nonlinear
   demonstration therefore samples the first design variable at nine
   levels across [-1, 1] (27 deterministic DOE runs), where the sine
   is genuinely non-quadratic and the RBF wins with real module
   outputs.
5. recommend_model branches (quadratic on the pure quadratic data,
   rbf on the nonlinear data) and the tie-break rule.
6. ValueError rejection of empty, ragged, mismatched, non-finite, and
   underdetermined inputs, eps <= 0, and singular systems.
"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import surrogate_modeling_logic as sm

# Deterministic analytic target from the spec (x0 plays x1, x1 plays x2).
ANALYTIC_COEFFS = [1.0, 2.0, 3.0, 4.0, 0.5, -1.0]

GRID9 = [
    [x0, x1] for x0 in (-1.0, 0.0, 1.0) for x1 in (-1.0, 0.0, 1.0)
]

# Nonlinear demonstration set: 9 levels of the first variable across
# [-1, 1] crossed with 3 levels of the second (27 deterministic runs),
# matching the "25 aerodynamic samples from the DOE" style sample.
L9 = [2.0 * i / 8.0 - 1.0 for i in range(9)]
DEMO27 = [[a, b] for a in L9 for b in (-1.0, 0.0, 1.0)]


def f_quad(x):
    """Pure quadratic target: 1 + 2x0 + 3x1 + 4x0^2 - x0x1 + 0.5x1^2."""
    x0, x1 = x
    return (1.0 + 2.0 * x0 + 3.0 * x1 + 4.0 * x0 * x0
            - x0 * x1 + 0.5 * x1 * x1)


def g_nonlin(x):
    """Mild nonlinear target: f plus 0.3 sin(2 x0) on the first variable."""
    return f_quad(x) + 0.3 * math.sin(2.0 * x[0])


Y9 = [f_quad(x) for x in GRID9]
YG27 = [g_nonlin(x) for x in DEMO27]


class TestSolveLinear(unittest.TestCase):
    def test_solve_linear_known_2x2(self):
        x = sm.solve_linear([[2.0, 1.0], [1.0, 3.0]], [5.0, 6.0])
        self.assertAlmostEqual(x[0], 1.8, places=12)
        self.assertAlmostEqual(x[1], 1.4, places=12)

    def test_solve_linear_known_3x3(self):
        x = sm.solve_linear(
            [[2.0, 1.0, -1.0], [-3.0, -1.0, 2.0], [-2.0, 1.0, 2.0]],
            [8.0, -11.0, -3.0],
        )
        for got, want in zip(x, [2.0, 3.0, -1.0]):
            self.assertAlmostEqual(got, want, places=10)

    def test_solve_linear_roundtrip_ax_equals_b(self):
        a = [[4.0, -1.0, 0.0], [-1.0, 4.0, -1.0], [0.0, -1.0, 3.0]]
        b = [1.0, 2.0, 3.0]
        x = sm.solve_linear(a, b)
        for i in range(3):
            lhs = sum(a[i][j] * x[j] for j in range(3))
            self.assertAlmostEqual(lhs, b[i], places=10)

    def test_solve_linear_singular_raises(self):
        with self.assertRaises(ValueError):
            sm.solve_linear([[1.0, 2.0], [2.0, 4.0]], [3.0, 6.0])

    def test_solve_linear_nonsquare_and_mismatch_raise(self):
        with self.assertRaises(ValueError):
            sm.solve_linear([[1.0, 2.0], [3.0]], [1.0, 2.0])
        with self.assertRaises(ValueError):
            sm.solve_linear([[1.0, 0.0], [0.0, 1.0]], [1.0])


class TestBasis(unittest.TestCase):
    def test_basis_d2_order_and_values(self):
        # [1, x0, x1, x0^2, x1^2, x0*x1]: linear, squares, then cross.
        b = sm.poly_basis_quadratic([0.5, -0.5])
        for got, want in zip(b, [1.0, 0.5, -0.5, 0.25, 0.25, -0.25]):
            self.assertAlmostEqual(got, want, places=12)

    def test_basis_d3_length_ten(self):
        # (d+1)(d+2)/2 = 10 for d = 3.
        b = sm.poly_basis_quadratic([1.0, 2.0, 3.0])
        self.assertEqual(len(b), 10)


class TestQuadraticFit(unittest.TestCase):
    def test_quadratic_recovery_9grid_within_1e_6(self):
        # Spec anchor 1: exact coefficient recovery of the 9-point grid.
        coeffs = sm.fit_quadratic(GRID9, Y9)
        self.assertEqual(len(coeffs), 6)
        for got, want in zip(coeffs, ANALYTIC_COEFFS):
            self.assertLess(abs(got - want), 1e-6)

    def test_quadratic_coefficient_slot_ordering(self):
        # Squares occupy slots 3 and 4, the cross term slot 5 for d = 2.
        coeffs = sm.fit_quadratic(GRID9, Y9)
        self.assertAlmostEqual(coeffs[3], 4.0, places=6)   # x0^2
        self.assertAlmostEqual(coeffs[4], 0.5, places=6)   # x1^2
        self.assertAlmostEqual(coeffs[5], -1.0, places=6)  # x0*x1

    def test_predict_quadratic_interior_equals_1_875(self):
        # Spec anchor 2: analytic value at (0.5, -0.5) is 1.875.
        coeffs = sm.fit_quadratic(GRID9, Y9)
        pred = sm.predict_quadratic(coeffs, [0.5, -0.5])
        self.assertLess(abs(pred - 1.875), 1e-6)

    def test_predict_quadratic_dot_identity(self):
        coeffs = sm.fit_quadratic(GRID9, Y9)
        x = [0.25, 0.75]
        basis = sm.poly_basis_quadratic(x)
        manual = sum(c * v for c, v in zip(coeffs, basis))
        self.assertAlmostEqual(sm.predict_quadratic(coeffs, x), manual, places=12)

    def test_fit_n_equal_m_interpolates(self):
        # Six samples for six basis terms must fit exactly (general position).
        rng = random.Random(3)
        x6 = [[round(rng.uniform(-1.0, 1.0), 6),
               round(rng.uniform(-1.0, 1.0), 6)] for _ in range(6)]
        y6 = [f_quad(x) for x in x6]
        coeffs = sm.fit_quadratic(x6, y6)
        for x, y in zip(x6, y6):
            self.assertLess(abs(sm.predict_quadratic(coeffs, x) - y), 1e-6)

    def test_fit_n_less_m_raises_with_count(self):
        with self.assertRaises(ValueError) as ctx:
            sm.fit_quadratic(GRID9[:2], Y9[:2])
        self.assertIn("6", str(ctx.exception))  # 6 basis terms for d = 2


class TestRbf(unittest.TestCase):
    def test_rbf_interpolates_9grid_exact(self):
        # Spec anchor 3: RBF interpolation is exact at every sample.
        weights = sm.fit_rbf(GRID9, Y9)
        self.assertEqual(len(weights), 9)
        for x, y in zip(GRID9, Y9):
            self.assertLess(abs(sm.predict_rbf(weights, GRID9, x) - y), 1e-6)

    def test_rbf_default_eps_is_0_5(self):
        self.assertEqual(sm.RBF_EPS_DEFAULT, 0.5)
        w1 = sm.fit_rbf(GRID9, Y9)
        w2 = sm.fit_rbf(GRID9, Y9, eps=0.5)
        for a, b in zip(w1, w2):
            self.assertEqual(a, b)

    def test_rbf_predict_manual_sum_formula(self):
        x_centers = [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]
        weights = [0.1, 0.2, 0.3]
        x = [0.2, 0.3]
        manual = sum(w * math.exp(-0.5 * ((xi[0] - x[0]) ** 2
                                          + (xi[1] - x[1]) ** 2))
                     for w, xi in zip(weights, x_centers))
        pred = sm.predict_rbf(weights, x_centers, x)
        self.assertAlmostEqual(pred, manual, places=12)

    def test_rbf_kernel_symmetry_and_scale(self):
        k = sm.rbf_kernel([0.0, 0.0], [1.0, 1.0], 0.5)
        self.assertAlmostEqual(k, math.exp(-1.0), places=12)
        self.assertAlmostEqual(
            sm.rbf_kernel([1.0, 1.0], [0.0, 0.0], 0.5), k, places=12
        )
        self.assertAlmostEqual(sm.rbf_kernel([0.1, -0.2], [0.1, -0.2], 0.5),
                               1.0, places=12)


class TestCrossValidationAndQuality(unittest.TestCase):
    def test_loo_errors_structure_and_rmse_formula(self):
        loo = sm.loo_cross_validation(GRID9, Y9, sm.fit_quadratic)
        self.assertEqual(len(loo["errors"]), 9)
        manual = math.sqrt(sum(e * e for e in loo["errors"]) / 9.0)
        self.assertAlmostEqual(loo["rmse"], manual, places=12)
        self.assertEqual(loo["max_abs"], max(loo["errors"]))

    def test_loo_quadratic_tiny_on_pure_quadratic(self):
        # Exact model family: LOO error is numerical noise only.
        loo = sm.loo_cross_validation(GRID9, Y9, sm.fit_quadratic)
        self.assertLess(loo["rmse"], 1e-6)
        self.assertLess(loo["max_abs"], 1e-5)

    def test_loo_rbf_beats_quadratic_on_nonlinear(self):
        # Spec anchor 4: on genuinely non-quadratic data the RBF has the
        # lower leave-one-out RMSE (real module outputs below).
        quad = sm.loo_cross_validation(DEMO27, YG27, sm.fit_quadratic)
        rbf = sm.loo_cross_validation(DEMO27, YG27, sm.fit_rbf)
        self.assertGreater(quad["rmse"], 0.05)   # measured 0.083910
        self.assertLess(rbf["rmse"], 0.02)       # measured 0.007279
        self.assertLess(rbf["rmse"], quad["rmse"])

    def test_quality_pure_quadratic_perfect(self):
        q = sm.model_quality(GRID9, Y9, sm.fit_quadratic)
        self.assertLess(q["rmse"], 1e-6)
        self.assertLess(q["max_abs"], 1e-6)
        self.assertGreater(q["r2"], 1.0 - 1e-9)

    def test_quality_constant_y_r2_one(self):
        yc = [5.0] * len(GRID9)
        q = sm.model_quality(GRID9, yc, sm.fit_quadratic)
        self.assertLess(q["rmse"], 1e-6)
        self.assertEqual(q["r2"], 1.0)


class TestRecommendModel(unittest.TestCase):
    def test_recommend_structure_and_keys(self):
        rec = sm.recommend_model(GRID9, Y9)
        for key in ("quadratic", "rbf", "best", "table"):
            self.assertIn(key, rec)
        self.assertEqual(len(rec["table"]), 2)
        self.assertIn(rec["best"], ("quadratic", "rbf"))
        self.assertEqual(rec["table"][0]["model"], "quadratic")
        self.assertEqual(rec["table"][1]["model"], "rbf")

    def test_recommend_quadratic_on_pure_data(self):
        # Spec anchor 5a: pure quadratic data recommends quadratic.
        rec = sm.recommend_model(GRID9, Y9)
        self.assertEqual(rec["best"], "quadratic")
        self.assertLess(rec["quadratic"], rec["rbf"])

    def test_recommend_rbf_on_nonlinear_data(self):
        # Spec anchor 5b: nonlinear data recommends rbf.
        rec = sm.recommend_model(DEMO27, YG27)
        self.assertEqual(rec["best"], "rbf")
        self.assertLess(rec["rbf"], rec["quadratic"])

    def test_recommend_decision_rule_consistency(self):
        # The decision matches the documented tie-break rule on both sets.
        self.assertEqual(sm.TIE_BREAK, "quadratic")
        for x, y in ((GRID9, Y9), (DEMO27, YG27)):
            q = sm.loo_cross_validation(x, y, sm.fit_quadratic)["rmse"]
            r = sm.loo_cross_validation(x, y, sm.fit_rbf)["rmse"]
            expected = "quadratic" if q <= r else "rbf"
            self.assertEqual(sm.recommend_model(x, y)["best"], expected)


class TestSurrogateReport(unittest.TestCase):
    def test_report_structure_and_predictions(self):
        rep = sm.surrogate_report(
            DEMO27, YG27, labels=["x1", "x2"],
            new_points=[[0.5, -0.5], [0.0, 0.0], [1.0, 1.0]],
        )
        for key in ("models", "quality", "loo", "recommendation",
                    "predictions", "labels"):
            self.assertIn(key, rep)
        self.assertEqual(len(rep["models"]["quadratic"]["coeffs"]), 6)
        self.assertEqual(len(rep["models"]["rbf"]["weights"]), 27)
        self.assertEqual(rep["labels"], ["x1", "x2"])
        self.assertEqual(rep["recommendation"]["best"], "rbf")
        self.assertEqual(len(rep["predictions"]["points"]), 3)
        self.assertEqual(len(rep["predictions"]["quadratic"]), 3)
        self.assertEqual(len(rep["predictions"]["rbf"]), 3)
        # Quadratic prediction at (0.5, -0.5) on g (measured 2.05084084).
        self.assertLess(abs(rep["predictions"]["quadratic"][0] - 2.05084084),
                        1e-4)

    def test_report_without_new_points(self):
        rep = sm.surrogate_report(GRID9, Y9)
        self.assertNotIn("predictions", rep)
        self.assertEqual(rep["recommendation"]["best"], "quadratic")

    def test_report_label_mismatch_raises(self):
        with self.assertRaises(ValueError):
            sm.surrogate_report(GRID9, Y9, labels=["x1"])


class TestValueErrorRejection(unittest.TestCase):
    def test_ve_empty_X(self):
        with self.assertRaises(ValueError):
            sm.fit_quadratic([], [])
        with self.assertRaises(ValueError):
            sm.fit_rbf([], [])
        with self.assertRaises(ValueError):
            sm.loo_cross_validation([], [], sm.fit_quadratic)

    def test_ve_ragged_rows(self):
        with self.assertRaises(ValueError):
            sm.fit_quadratic([[1.0, 2.0], [3.0]], [1.0, 2.0])
        with self.assertRaises(ValueError):
            sm.fit_quadratic([[1.0, 2.0], [1.0, 2.0, 3.0]], [1.0, 2.0])

    def test_ve_len_mismatch(self):
        with self.assertRaises(ValueError):
            sm.fit_quadratic(GRID9, Y9[:8])
        with self.assertRaises(ValueError):
            sm.fit_rbf(GRID9, Y9 + [1.0])

    def test_ve_nonfinite_values(self):
        bad_x = [[float("nan"), 0.0]] + GRID9[1:]
        with self.assertRaises(ValueError):
            sm.fit_quadratic(bad_x, Y9)
        bad_y = list(Y9[:8]) + [float("inf")]
        with self.assertRaises(ValueError):
            sm.fit_quadratic(GRID9, bad_y)
        with self.assertRaises(ValueError):
            sm.solve_linear([[1.0, 0.0], [0.0, float("nan")]], [1.0, 1.0])

    def test_ve_eps_nonpositive(self):
        with self.assertRaises(ValueError):
            sm.rbf_kernel([0.0], [0.0], 0.0)
        with self.assertRaises(ValueError):
            sm.rbf_kernel([0.0], [0.0], -1.0)
        with self.assertRaises(ValueError):
            sm.fit_rbf(GRID9, Y9, eps=0.0)
        with self.assertRaises(ValueError):
            sm.loo_cross_validation(GRID9, Y9, sm.fit_rbf, eps=-0.5)

    def test_ve_predict_mismatch_and_duplicate_samples(self):
        coeffs = sm.fit_quadratic(GRID9, Y9)
        with self.assertRaises(ValueError):
            sm.predict_quadratic(coeffs, [0.1])  # d = 1 basis against d = 2
        w9 = sm.fit_rbf(GRID9, Y9)
        with self.assertRaises(ValueError):
            sm.predict_rbf(w9, GRID9, [0.1, 0.2, 0.3])  # 3 columns vs 2
        dup = GRID9[:2] + [GRID9[0]] * 3 + GRID9[3:]
        with self.assertRaises(ValueError):
            sm.fit_rbf(dup, [f_quad(x) for x in dup])  # singular kernel


if __name__ == "__main__":
    unittest.main()
