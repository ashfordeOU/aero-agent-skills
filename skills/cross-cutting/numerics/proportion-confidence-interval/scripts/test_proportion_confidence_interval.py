"""Contract test for the proportion-confidence-interval logic module.

Deterministic, offline, stdlib only. Run with:
    python3 test_proportion_confidence_interval.py
Anchors come from the wave-38 spec worked example (cl = 0.95, z =
1.959964, prep-verified): Wilson and Clopper-Pearson bounds for 12/400,
0/30 and 30/30, plus the two-proportion difference interval for
k1 = 5, n1 = 100, k2 = 1, n2 = 100.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import proportion_confidence_interval_logic as pci


class TestNormalQuantile(unittest.TestCase):
    def test_quantile_975_is_196(self):
        # 1.959964 at six decimals, the 95% two-sided z value.
        self.assertAlmostEqual(pci.normal_quantile(0.975), 1.959964, places=6)

    def test_quantile_known_and_symmetric(self):
        self.assertEqual(pci.normal_quantile(0.5), 0.0)
        for p, q in ((0.80, 0.841621), (0.90, 1.281552), (0.99, 2.326348),
                     (0.995, 2.575829)):
            self.assertAlmostEqual(pci.normal_quantile(p), q, places=4)
        for p in (0.01, 0.05, 0.2, 0.9, 0.975):
            self.assertAlmostEqual(
                pci.normal_quantile(p), -pci.normal_quantile(1.0 - p), places=10
            )

    def test_quantile_rejects_out_of_range(self):
        for p in (0.0, 1.0, -0.1, 1.5):
            with self.assertRaises(ValueError):
                pci.normal_quantile(p)


class TestWilsonInterval(unittest.TestCase):
    def test_anchors(self):
        # Spec: 12/400 -> [0.017243, 0.051699]; 0/30 -> [0.0, 0.113513];
        # 30/30 -> [0.886487, 1.0].
        res = pci.wilson_score_interval(12, 400)
        self.assertAlmostEqual(res["lower"], 0.017243, places=6)
        self.assertAlmostEqual(res["upper"], 0.051699, places=6)
        res0 = pci.wilson_score_interval(0, 30)
        self.assertEqual(res0["lower"], 0.0)
        self.assertAlmostEqual(res0["upper"], 0.113513, places=6)
        resn = pci.wilson_score_interval(30, 30)
        self.assertAlmostEqual(resn["lower"], 0.886487, places=5)
        self.assertEqual(resn["upper"], 1.0)

    def test_contains_phat_and_unit_bounds(self):
        for k, n in ((12, 400), (5, 100), (25, 60), (0, 30), (30, 30), (3, 7),
                     (1, 1), (99, 100)):
            res = pci.wilson_score_interval(k, n)
            self.assertLessEqual(res["lower"], k / n)
            self.assertGreaterEqual(res["upper"], k / n)
            self.assertGreaterEqual(res["lower"], 0.0)
            self.assertLessEqual(res["upper"], 1.0)

    def test_width_is_span_and_shrinks_with_n(self):
        res = pci.wilson_score_interval(12, 400)
        self.assertAlmostEqual(res["width"], res["upper"] - res["lower"], places=12)
        # Fixed phat ~ 0.05: width must shrink as n grows.
        self.assertLess(
            pci.wilson_score_interval(50, 1000)["width"],
            pci.wilson_score_interval(5, 100)["width"],
        )

    def test_closed_form_center_matches(self):
        # Wilson bounds reproduce center +/- half-width at 12/400.
        k, n, cl = 12, 400, 0.95
        z = pci.normal_quantile(0.5 * (1.0 + cl))
        phat = k / n
        center = (phat + z * z / (2.0 * n)) / (1.0 + z * z / n)
        half = z * math.sqrt(phat * (1.0 - phat) / n + z * z / (4.0 * n * n)) / (
            1.0 + z * z / n
        )
        res = pci.wilson_score_interval(k, n)
        self.assertAlmostEqual(0.5 * (res["lower"] + res["upper"]), center, places=10)
        self.assertAlmostEqual(0.5 * (res["upper"] - res["lower"]), half, places=10)

    def test_higher_level_wider(self):
        res90 = pci.wilson_score_interval(30, 100, cl=0.90)
        res99 = pci.wilson_score_interval(30, 100, cl=0.99)
        self.assertLess(res99["lower"], res90["lower"])
        self.assertGreater(res99["upper"], res90["upper"])

    def test_rejects_bad_inputs(self):
        for bad in ((-1, 10), (11, 10), (5, 0), (5, -3)):
            with self.assertRaises(ValueError):
                pci.wilson_score_interval(*bad)
        for cl in (0.0, 1.0, 1.5, -0.1):
            with self.assertRaises(ValueError):
                pci.wilson_score_interval(5, 10, cl=cl)

    def test_deterministic(self):
        self.assertEqual(
            pci.wilson_score_interval(17, 200),
            pci.wilson_score_interval(17, 200),
        )


class TestWilsonCcInterval(unittest.TestCase):
    def test_endpoint_cases(self):
        res = pci.wilson_score_cc_interval(0, 30)
        self.assertEqual(res["lower"], 0.0)
        self.assertAlmostEqual(res["upper"], 0.141320, places=4)
        self.assertEqual(pci.wilson_score_cc_interval(30, 30)["upper"], 1.0)

    def test_contains_phat(self):
        for k, n in ((12, 400), (5, 100), (25, 60), (3, 7)):
            res = pci.wilson_score_cc_interval(k, n)
            self.assertLessEqual(res["lower"], k / n)
            self.assertGreaterEqual(res["upper"], k / n)

    def test_cc_wider_than_plain_wilson(self):
        # Continuity correction widens the interval at every case.
        for k, n in ((1, 10), (3, 7), (12, 400), (25, 60), (50, 100)):
            plain = pci.wilson_score_interval(k, n)
            cc = pci.wilson_score_cc_interval(k, n)
            self.assertLessEqual(cc["lower"], plain["lower"] + 1e-12)
            self.assertGreaterEqual(cc["upper"], plain["upper"] - 1e-12)

    def test_width_is_span(self):
        res = pci.wilson_score_cc_interval(7, 40)
        self.assertAlmostEqual(res["width"], res["upper"] - res["lower"], places=12)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            pci.wilson_score_cc_interval(-1, 10)
        with self.assertRaises(ValueError):
            pci.wilson_score_cc_interval(5, 0)
        with self.assertRaises(ValueError):
            pci.wilson_score_cc_interval(5, 10, cl=0.0)


class TestIncompleteBeta(unittest.TestCase):
    def test_special_and_polynomial_values(self):
        self.assertAlmostEqual(pci.regularized_incomplete_beta(2, 3, 0.0), 0.0)
        self.assertAlmostEqual(pci.regularized_incomplete_beta(2, 3, 1.0), 1.0)
        self.assertAlmostEqual(pci.regularized_incomplete_beta(1, 1, 0.3), 0.3)
        # I_x(2,3) = 12 * (x^2/2 - 2x^3/3 + x^4/4) for integer shapes.
        for x in (0.1, 0.4, 0.7):
            exact = 12.0 * (x * x / 2.0 - 2.0 * x ** 3 / 3.0 + x ** 4 / 4.0)
            self.assertAlmostEqual(
                pci.regularized_incomplete_beta(2, 3, x), exact, places=12
            )

    def test_symmetric_across_crossover(self):
        # I_x(a, b) = 1 - I_{1-x}(b, a); x above the (a+1)/(a+b+2)
        # crossover exercises the symmetry transform branch.
        for a, b, x in ((2, 3, 0.7), (5, 5, 0.9), (12, 389, 0.05), (3, 2, 0.95),
                        (4, 7, 0.95)):
            left = pci.regularized_incomplete_beta(a, b, x)
            right = 1.0 - pci.regularized_incomplete_beta(b, a, 1.0 - x)
            self.assertAlmostEqual(left, right, places=12)

    def test_monotone_in_x(self):
        vals = [pci.regularized_incomplete_beta(4, 9, x) for x in (0.1, 0.5, 0.9)]
        self.assertTrue(vals[0] < vals[1] < vals[2])

    def test_rejects_bad_inputs(self):
        for args in ((0, 1, 0.5), (1, -2, 0.5), (1, 1, 1.5), (1, 1, -0.1)):
            with self.assertRaises(ValueError):
                pci.regularized_incomplete_beta(*args)


class TestBetaQuantile(unittest.TestCase):
    def test_round_trip(self):
        for a, b, q in ((1, 30, 0.975), (30, 1, 0.025), (12, 389, 0.025),
                        (2, 3, 0.5), (5, 5, 0.9)):
            x = pci.beta_quantile(a, b, q)
            self.assertAlmostEqual(
                pci.regularized_incomplete_beta(a, b, x), q, places=9
            )

    def test_rule_of_three_bound(self):
        # k = 0, n = 30 upper bound: 1 - 0.025^(1/30) = 0.115703.
        upper = pci.beta_quantile(1, 30, 0.975)
        self.assertAlmostEqual(upper, 1.0 - 0.025 ** (1.0 / 30.0), places=9)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            pci.beta_quantile(1, 1, 0.0)
        with self.assertRaises(ValueError):
            pci.beta_quantile(1, 1, 1.0)
        with self.assertRaises(ValueError):
            pci.beta_quantile(0, 1, 0.5)


class TestClopperPearson(unittest.TestCase):
    def test_anchors(self):
        # Spec: 12/400 -> [0.015596, 0.051817]; 0/30 -> [0.0, 0.115703];
        # 30/30 -> [0.884297, 1.0].
        res = pci.clopper_pearson_interval(12, 400)
        self.assertAlmostEqual(res["lower"], 0.015596, places=6)
        self.assertAlmostEqual(res["upper"], 0.051817, places=6)
        res0 = pci.clopper_pearson_interval(0, 30)
        self.assertEqual(res0["lower"], 0.0)
        self.assertAlmostEqual(res0["upper"], 0.115703, places=6)
        resn = pci.clopper_pearson_interval(30, 30)
        self.assertAlmostEqual(resn["lower"], 0.884297, places=6)
        self.assertEqual(resn["upper"], 1.0)

    def test_contains_phat(self):
        for k, n in ((12, 400), (5, 100), (25, 60), (0, 30), (30, 30), (3, 7)):
            res = pci.clopper_pearson_interval(k, n)
            self.assertLessEqual(res["lower"], k / n)
            self.assertGreaterEqual(res["upper"], k / n)

    def test_exact_coverage_level(self):
        # Exactness: the CP bounds invert the binomial tail, so
        # I_upper(k+1, n-k) = 1 - alpha/2 and I_lower(k, n-k+1) = alpha/2.
        k, n, cl = 6, 40, 0.95
        res = pci.clopper_pearson_interval(k, n, cl)
        alpha2 = (1.0 - cl) / 2.0
        self.assertAlmostEqual(
            pci.regularized_incomplete_beta(k + 1, n - k, res["upper"]),
            1.0 - alpha2,
            places=9,
        )
        self.assertAlmostEqual(
            pci.regularized_incomplete_beta(k, n - k + 1, res["lower"]),
            alpha2,
            places=9,
        )

    def test_wider_or_equal_wilson_small_n(self):
        # Exactness: at small n the CP interval is wider than or equal to
        # the Wilson interval (lower bound lower, upper bound higher).
        for k, n in ((3, 7), (1, 10), (5, 15), (0, 30), (30, 30)):
            wil = pci.wilson_score_interval(k, n)
            cp = pci.clopper_pearson_interval(k, n)
            self.assertLessEqual(cp["lower"], wil["lower"] + 1e-9)
            self.assertGreaterEqual(cp["upper"], wil["upper"] - 1e-9)

    def test_width_is_span_and_shrinks_with_n(self):
        res = pci.clopper_pearson_interval(12, 400)
        self.assertAlmostEqual(res["width"], res["upper"] - res["lower"], places=12)
        self.assertLess(
            pci.clopper_pearson_interval(50, 1000)["width"],
            pci.clopper_pearson_interval(5, 100)["width"],
        )

    def test_agree_with_wilson_at_large_n(self):
        # At large n the exact and approximate intervals converge.
        wil = pci.wilson_score_interval(1200, 40000)
        cp = pci.clopper_pearson_interval(1200, 40000)
        self.assertAlmostEqual(wil["lower"], cp["lower"], places=4)
        self.assertAlmostEqual(wil["upper"], cp["upper"], places=4)

    def test_rejects_bad_inputs_and_deterministic(self):
        for bad in ((-1, 10), (5, 0)):
            with self.assertRaises(ValueError):
                pci.clopper_pearson_interval(*bad)
        with self.assertRaises(ValueError):
            pci.clopper_pearson_interval(5, 10, cl=1.2)
        self.assertEqual(
            pci.clopper_pearson_interval(17, 200),
            pci.clopper_pearson_interval(17, 200),
        )


class TestTwoProportionDiff(unittest.TestCase):
    def test_anchor(self):
        # k1 = 5, n1 = 100, k2 = 1, n2 = 100: diff 0.04, width 0.04696
        # (within 1e-3), interval [-0.00696, 0.08696].
        res = pci.two_proportion_diff_interval(5, 100, 1, 100)
        self.assertAlmostEqual(res["diff"], 0.04, places=10)
        self.assertAlmostEqual(res["width"], 0.04696, places=3)
        self.assertAlmostEqual(res["lower"], -0.00696, places=4)
        self.assertAlmostEqual(res["upper"], 0.08696, places=4)

    def test_matches_normal_formula(self):
        # diff +/- z * sqrt(p1(1-p1)/n1 + p2(1-p2)/n2), width = z * se.
        k1, n1, k2, n2, cl = 8, 50, 2, 60, 0.95
        p1, p2 = k1 / n1, k2 / n2
        se = math.sqrt(p1 * (1.0 - p1) / n1 + p2 * (1.0 - p2) / n2)
        z = pci.normal_quantile(0.5 * (1.0 + cl))
        res = pci.two_proportion_diff_interval(k1, n1, k2, n2, cl)
        self.assertAlmostEqual(res["width"], z * se, places=12)
        self.assertAlmostEqual(res["lower"], p1 - p2 - z * se, places=12)
        self.assertAlmostEqual(res["upper"], p1 - p2 + z * se, places=12)

    def test_zero_diff_and_zero_failures_cases(self):
        # Equal proportions give diff 0 and a symmetric interval.
        res = pci.two_proportion_diff_interval(10, 100, 10, 100)
        self.assertEqual(res["diff"], 0.0)
        self.assertAlmostEqual(res["lower"], -res["upper"], places=12)
        # k2 = 0 stays computable (the p2 variance term vanishes).
        res0 = pci.two_proportion_diff_interval(5, 100, 0, 100)
        self.assertGreater(res0["lower"], 0.0)
        self.assertLess(res0["width"], 0.12)

    def test_contains_diff(self):
        for args in ((5, 100, 1, 100), (30, 200, 40, 180), (0, 20, 3, 40)):
            res = pci.two_proportion_diff_interval(*args)
            self.assertLessEqual(res["lower"], res["diff"])
            self.assertGreaterEqual(res["upper"], res["diff"])

    def test_rejects_bad_inputs_and_deterministic(self):
        for bad in ((-1, 10, 1, 10), (11, 10, 1, 10), (1, 10, 1, 0),
                    (1, 10, -2, 10)):
            with self.assertRaises(ValueError):
                pci.two_proportion_diff_interval(*bad)
        with self.assertRaises(ValueError):
            pci.two_proportion_diff_interval(1, 10, 1, 10, cl=0.0)
        self.assertEqual(
            pci.two_proportion_diff_interval(5, 100, 1, 100),
            pci.two_proportion_diff_interval(5, 100, 1, 100),
        )


class TestDictContract(unittest.TestCase):
    def test_dict_keys_and_value_types(self):
        for fn in (pci.wilson_score_interval, pci.wilson_score_cc_interval,
                   pci.clopper_pearson_interval):
            res = fn(12, 400)
            self.assertEqual(sorted(res.keys()), ["lower", "upper", "width"])
            for key in res:
                self.assertIsInstance(res[key], float)
        res = pci.two_proportion_diff_interval(5, 100, 1, 100)
        self.assertEqual(sorted(res.keys()), ["diff", "lower", "upper", "width"])
        for key in res:
            self.assertIsInstance(res[key], float)


if __name__ == "__main__":
    unittest.main()
