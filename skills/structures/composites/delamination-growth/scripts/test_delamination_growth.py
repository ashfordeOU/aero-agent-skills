"""Deterministic offline contract test for delamination_growth_logic.

Run with: python3 scripts/test_delamination_growth.py
Asserts the wave-28 spec worked example: E = 135e9 Pa, b = 0.02 m.
Anchors: dcb_g1(50, 0.05, 0.02, 0.0015, E) = 411.52,
dcb_g1(30, 0.05, 0.02, 0.0015, E) = 148.15,
enf_g2(500, 0.03, 0.02, 0.0015, E) = 694.44, the compliance-form
cross-check at h = 0.003 (51.44, both forms agree to 1e-6 with the
exact beam-theory opening), and the mixed-mode assess cases:
growth (g_c 744.1, margin -1.76, verdict delamination-growth) and
no-growth (g_c 757.98, margin +399.18, verdict no-delamination-growth).
"""

import os
import sys
import unittest

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)

import delamination_growth_logic as dgl

E = 135e9        # flexural modulus, Pa
B = 0.02         # specimen width, m
G1C = 250.0      # mode I critical rate, J/m2
G2C = 800.0      # mode II critical rate, J/m2
ETA = 1.5        # Benzeggagh-Kenane exponent

# Worked-example coupon states. The DCB and ENF coupons are separate
# specimens, so their arm half-thicknesses are independent: the growth
# and no-growth pairs use a thicker DCB coupon (h 0.003) and a thin ENF
# coupon (h 0.0015), reproducing the spec numbers exactly.
GROWTH = {
    "p_dcb": 50.0, "a_dcb": 0.05, "h_dcb": 0.003,
    "p_enf": 500.0, "a_enf": 0.03, "h_enf": 0.0015,
    "b": B, "e": E, "g1c": G1C, "g2c": G2C, "eta": ETA,
}
NO_GROWTH = {
    "p_dcb": 30.0, "a_dcb": 0.05, "h_dcb": 0.003,
    "p_enf": 350.0, "a_enf": 0.03, "h_enf": 0.0015,
    "b": B, "e": E, "g1c": G1C, "g2c": G2C, "eta": ETA,
}


class DcbTests(unittest.TestCase):
    """Mode I DCB strain energy release rate."""

    def test_dcb_spec_50_411_52(self):
        self.assertAlmostEqual(
            dgl.dcb_g1(50.0, 0.05, B, 0.0015, E), 411.52, delta=0.1)

    def test_dcb_spec_30_148_15(self):
        self.assertAlmostEqual(
            dgl.dcb_g1(30.0, 0.05, B, 0.0015, E), 148.15, delta=0.05)

    def test_dcb_thick_arm_51_44(self):
        self.assertAlmostEqual(
            dgl.dcb_g1(50.0, 0.05, B, 0.003, E), 51.44, delta=0.01)

    def test_dcb_zero_load_zero_rate(self):
        self.assertEqual(dgl.dcb_g1(0.0, 0.05, B, 0.0015, E), 0.0)

    def test_dcb_quadratic_in_load(self):
        base = dgl.dcb_g1(50.0, 0.05, B, 0.0015, E)
        doubled = dgl.dcb_g1(100.0, 0.05, B, 0.0015, E)
        self.assertAlmostEqual(doubled / base, 4.0, places=9)

    def test_dcb_inverse_cubic_in_half_thickness(self):
        thin = dgl.dcb_g1(50.0, 0.05, B, 0.0015, E)
        thick = dgl.dcb_g1(50.0, 0.05, B, 0.003, E)
        self.assertAlmostEqual(thick / thin, 0.125, places=9)


class ComplianceTests(unittest.TestCase):
    """Compliance-form DCB rate cross-checks the load-squared form."""

    def test_compliance_spec_delta_51_44(self):
        self.assertAlmostEqual(
            dgl.dcb_g1_compliance(50.0, 6.859e-4, B, 0.05), 51.44,
            delta=0.01)

    def test_compliance_matches_load_squared_rounded_delta(self):
        g_compl = dgl.dcb_g1_compliance(50.0, 6.859e-4, B, 0.05)
        g_load = dgl.dcb_g1(50.0, 0.05, B, 0.003, E)
        self.assertAlmostEqual(g_compl, g_load, delta=0.01)

    def test_compliance_exact_agreement_1e_6(self):
        # delta = 2 * w, w = P*a^3/(3*E*I), I = b*h^3/12 with h = 0.003.
        h = 0.003
        inertia = B * h ** 3 / 12.0
        delta = 2.0 * 50.0 * 0.05 ** 3 / (3.0 * E * inertia)
        g_compl = dgl.dcb_g1_compliance(50.0, delta, B, 0.05)
        g_load = dgl.dcb_g1(50.0, 0.05, B, 0.003, E)
        self.assertLess(abs(g_compl - g_load), 1e-6)

    def test_compliance_linear_in_opening(self):
        g1 = dgl.dcb_g1_compliance(50.0, 6.859e-4, B, 0.05)
        g2 = dgl.dcb_g1_compliance(50.0, 2.0 * 6.859e-4, B, 0.05)
        self.assertAlmostEqual(g2 / g1, 2.0, places=9)


class EnfTests(unittest.TestCase):
    """Mode II ENF strain energy release rate."""

    def test_enf_spec_500_694_44(self):
        self.assertAlmostEqual(
            dgl.enf_g2(500.0, 0.03, B, 0.0015, E), 694.44, delta=0.1)

    def test_enf_coupon_350_340_28(self):
        self.assertAlmostEqual(
            dgl.enf_g2(350.0, 0.03, B, 0.0015, E), 340.28, delta=0.1)

    def test_enf_quadratic_in_load(self):
        base = dgl.enf_g2(500.0, 0.03, B, 0.0015, E)
        half = dgl.enf_g2(250.0, 0.03, B, 0.0015, E)
        self.assertAlmostEqual(half / base, 0.25, places=9)


class MixedModeRatioTests(unittest.TestCase):
    """Mode II share of the total energy release rate."""

    def test_ratio_spec_0_9310(self):
        g1 = dgl.dcb_g1(50.0, 0.05, B, 0.003, E)      # 51.44
        g2 = dgl.enf_g2(500.0, 0.03, B, 0.0015, E)    # 694.44
        self.assertAlmostEqual(
            dgl.mixed_mode_ratio(g1, g2), 0.9310, delta=1e-4)

    def test_ratio_pure_mode_one_is_zero(self):
        self.assertEqual(dgl.mixed_mode_ratio(50.0, 0.0), 0.0)

    def test_ratio_pure_mode_two_is_one(self):
        self.assertEqual(dgl.mixed_mode_ratio(0.0, 50.0), 1.0)

    def test_ratio_unloaded_total_zero_returns_zero(self):
        self.assertEqual(dgl.mixed_mode_ratio(0.0, 0.0), 0.0)


class BkCriticalTests(unittest.TestCase):
    """Benzeggagh-Kenane critical total energy release rate."""

    def test_bk_growth_case_gc_744(self):
        g1 = dgl.dcb_g1(50.0, 0.05, B, 0.003, E)
        g2 = dgl.enf_g2(500.0, 0.03, B, 0.0015, E)
        self.assertAlmostEqual(
            dgl.bk_critical(g1, g2, G1C, G2C, ETA), 744.1, delta=1.0)

    def test_bk_no_growth_case_gc_758(self):
        g1 = dgl.dcb_g1(30.0, 0.05, B, 0.003, E)
        g2 = dgl.enf_g2(350.0, 0.03, B, 0.0015, E)
        self.assertAlmostEqual(
            dgl.bk_critical(g1, g2, G1C, G2C, ETA), 757.98, delta=1.0)

    def test_bk_pure_mode_i_equals_g1c(self):
        self.assertEqual(
            dgl.bk_critical(100.0, 0.0, G1C, G2C, ETA), G1C)

    def test_bk_pure_mode_ii_equals_g2c(self):
        self.assertEqual(
            dgl.bk_critical(0.0, 100.0, G1C, G2C, ETA), G2C)

    def test_bk_monotonic_in_mode_two_share(self):
        # A higher mode II share must raise G_c toward g2c.
        cases = [(90.0, 10.0), (70.0, 30.0), (50.0, 50.0),
                 (30.0, 70.0), (10.0, 90.0), (0.0, 100.0)]
        values = [dgl.bk_critical(g1, g2, G1C, G2C, ETA)
                  for g1, g2 in cases]
        for low, high in zip(values, values[1:]):
            self.assertGreater(high, low)

    def test_bk_bounded_by_g1c_and_g2c(self):
        g_c = dgl.bk_critical(51.44, 694.44, G1C, G2C, ETA)
        self.assertGreaterEqual(g_c, G1C)
        self.assertLessEqual(g_c, G2C)


class OnsetMarginTests(unittest.TestCase):
    """Onset margin G_c - G_T."""

    def test_onset_margin_growth_negative(self):
        g1 = dgl.dcb_g1(50.0, 0.05, B, 0.003, E)
        g2 = dgl.enf_g2(500.0, 0.03, B, 0.0015, E)
        margin = dgl.onset_margin(g1, g2, G1C, G2C, ETA)
        self.assertAlmostEqual(margin, -1.76, delta=0.5)
        self.assertLess(margin, 0.0)

    def test_onset_margin_no_growth_positive(self):
        g1 = dgl.dcb_g1(30.0, 0.05, B, 0.003, E)
        g2 = dgl.enf_g2(350.0, 0.03, B, 0.0015, E)
        margin = dgl.onset_margin(g1, g2, G1C, G2C, ETA)
        self.assertAlmostEqual(margin, 399.18, delta=2.0)
        self.assertGreater(margin, 0.0)


class AssessTests(unittest.TestCase):
    """Full assess() pipeline verdicts."""

    def test_assess_growth_verdict_anchors(self):
        res = dgl.assess(GROWTH)
        self.assertAlmostEqual(res["g1"], 51.44, delta=0.01)
        self.assertAlmostEqual(res["g2"], 694.44, delta=0.1)
        self.assertAlmostEqual(res["g_t"], 745.89, delta=0.02)
        self.assertAlmostEqual(res["ratio"], 0.9310, delta=1e-4)
        self.assertAlmostEqual(res["g_c"], 744.1, delta=1.0)
        self.assertAlmostEqual(res["margin"], -1.76, delta=0.5)
        self.assertLess(res["margin"], 0.0)
        self.assertTrue(res["growth"])
        self.assertEqual(res["verdict"], "delamination-growth")

    def test_assess_no_growth_verdict_anchors(self):
        res = dgl.assess(NO_GROWTH)
        self.assertAlmostEqual(res["g1"], 18.52, delta=0.01)
        self.assertAlmostEqual(res["g2"], 340.28, delta=0.01)
        self.assertAlmostEqual(res["g_t"], 358.80, delta=0.02)
        self.assertAlmostEqual(res["g_c"], 757.98, delta=1.0)
        self.assertAlmostEqual(res["margin"], 399.18, delta=2.0)
        self.assertGreater(res["margin"], 0.0)
        self.assertFalse(res["growth"])
        self.assertEqual(res["verdict"], "no-delamination-growth")

    def test_assess_report_keys(self):
        res = dgl.assess(GROWTH)
        for key in ("g1", "g2", "g_t", "ratio", "g_c", "margin",
                    "growth", "verdict"):
            self.assertIn(key, res)
        self.assertAlmostEqual(res["margin"],
                               res["g_c"] - res["g_t"], places=9)

    def test_assess_unloaded_no_growth(self):
        inputs = dict(GROWTH)
        inputs["p_dcb"] = 0.0
        inputs["p_enf"] = 0.0
        res = dgl.assess(inputs)
        self.assertEqual(res["g_t"], 0.0)
        self.assertEqual(res["g_c"], G1C)
        self.assertFalse(res["growth"])
        self.assertEqual(res["verdict"], "no-delamination-growth")

    def test_assess_negative_dcb_load_value_error(self):
        inputs = dict(GROWTH)
        inputs["p_dcb"] = -5.0
        with self.assertRaises(ValueError):
            dgl.assess(inputs)


class ValueErrorTests(unittest.TestCase):
    """Non-physical inputs are rejected with ValueError."""

    def test_dcb_non_physical_value_errors(self):
        with self.assertRaises(ValueError):
            dgl.dcb_g1(-1.0, 0.05, B, 0.0015, E)
        with self.assertRaises(ValueError):
            dgl.dcb_g1(50.0, 0.0, B, 0.0015, E)
        with self.assertRaises(ValueError):
            dgl.dcb_g1(50.0, 0.05, -0.02, 0.0015, E)
        with self.assertRaises(ValueError):
            dgl.dcb_g1(50.0, 0.05, B, 0.0, E)
        with self.assertRaises(ValueError):
            dgl.dcb_g1(50.0, 0.05, B, 0.0015, 0.0)

    def test_enf_and_compliance_value_errors(self):
        with self.assertRaises(ValueError):
            dgl.enf_g2(-500.0, 0.03, B, 0.0015, E)
        with self.assertRaises(ValueError):
            dgl.enf_g2(500.0, 0.0, B, 0.0015, E)
        with self.assertRaises(ValueError):
            dgl.enf_g2(500.0, 0.03, B, -0.0015, E)
        with self.assertRaises(ValueError):
            dgl.dcb_g1_compliance(50.0, 0.0, B, 0.05)
        with self.assertRaises(ValueError):
            dgl.dcb_g1_compliance(50.0, 6.859e-4, B, 0.0)

    def test_rate_and_toughness_value_errors(self):
        with self.assertRaises(ValueError):
            dgl.mixed_mode_ratio(-1.0, 5.0)
        with self.assertRaises(ValueError):
            dgl.bk_critical(-1.0, 10.0, G1C, G2C, ETA)
        with self.assertRaises(ValueError):
            dgl.bk_critical(10.0, -10.0, G1C, G2C, ETA)
        with self.assertRaises(ValueError):
            dgl.bk_critical(10.0, 10.0, 0.0, G2C, ETA)
        with self.assertRaises(ValueError):
            dgl.bk_critical(10.0, 10.0, G1C, 0.0, ETA)

    def test_bk_exponent_and_assess_value_errors(self):
        with self.assertRaises(ValueError):
            dgl.bk_critical(10.0, 10.0, G1C, G2C, 0.0)
        with self.assertRaises(ValueError):
            dgl.bk_critical(10.0, 10.0, G1C, G2C, -1.0)
        inputs = dict(GROWTH)
        inputs["eta"] = 0.0
        with self.assertRaises(ValueError):
            dgl.assess(inputs)
        inputs = dict(GROWTH)
        inputs["g1c"] = 0.0
        with self.assertRaises(ValueError):
            dgl.assess(inputs)
        inputs = dict(GROWTH)
        inputs["a_enf"] = 0.0
        with self.assertRaises(ValueError):
            dgl.assess(inputs)


if __name__ == "__main__":
    unittest.main()
