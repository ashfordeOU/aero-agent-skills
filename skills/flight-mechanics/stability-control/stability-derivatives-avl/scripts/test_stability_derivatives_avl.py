#!/usr/bin/env python3
"""Gate 3 contract test: stability derivative estimation (AVL style).

Exercises scripts/stability_derivatives_avl_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - wing and tail
lift curve slopes from planform aspect ratio, quarter-chord sweep, and
Mach; Cm_alpha, downwash, tail volume coefficients, neutral point and
static margin; lateral-directional derivatives Cn_beta, Cl_beta, Cl_p,
Cl_r, Cn_p, Cn_r; the assembled derivative table; invalid inputs raise
ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import stability_derivatives_avl_logic as sd  # noqa: E402


class ClAlphaWingTest(unittest.TestCase):
    def test_known_wing_anchor(self):
        # AR=6, no sweep, incompressible, thin-airfoil section slope:
        # CL_alpha = 2*pi*6 / (2 + sqrt(36 + 4)) = 4.5287 per radian.
        self.assertAlmostEqual(
            sd.cl_alpha_wing(6.0, 0.0, 0.0), 4.5287, delta=1e-3
        )

    def test_sweep_reduces_slope(self):
        self.assertLess(
            sd.cl_alpha_wing(6.0, 25.0, 0.0), sd.cl_alpha_wing(6.0, 0.0, 0.0)
        )

    def test_mach_increases_slope_subsonic(self):
        # Compressibility raises the lift slope below M_crit.
        self.assertGreater(
            sd.cl_alpha_wing(6.0, 0.0, 0.5), sd.cl_alpha_wing(6.0, 0.0, 0.0)
        )

    def test_low_aspect_ratio_lower_slope(self):
        self.assertLess(sd.cl_alpha_wing(4.0, 0.0, 0.0), 2.0 * math.pi)

    def test_tail_uses_same_planform_estimate(self):
        self.assertAlmostEqual(
            sd.cl_alpha_tail(6.0, 0.0, 0.0),
            sd.cl_alpha_wing(6.0, 0.0, 0.0),
            delta=1e-9,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sd.cl_alpha_wing(0.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            sd.cl_alpha_wing(-3.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            sd.cl_alpha_wing(6.0, 90.0, 0.0)
        with self.assertRaises(ValueError):
            sd.cl_alpha_wing(6.0, 0.0, 0.9)
        with self.assertRaises(ValueError):
            sd.cl_alpha_wing(6.0, 0.0, 1.2)
        with self.assertRaises(ValueError):
            sd.cl_alpha_wing(6.0, 0.0, 0.0, cl_alpha_airfoil=0.0)


class DownwashTest(unittest.TestCase):
    def test_anchor_value(self):
        # 2 * 4.5287 / (pi * 6) = 0.4805
        self.assertAlmostEqual(
            sd.downwash_gradient(4.5287, 6.0), 0.4805, delta=1e-3
        )

    def test_stronger_wing_more_downwash(self):
        self.assertGreater(
            sd.downwash_gradient(5.0, 6.0), sd.downwash_gradient(4.0, 6.0)
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sd.downwash_gradient(0.0, 6.0)
        with self.assertRaises(ValueError):
            sd.downwash_gradient(4.5, 0.0)
        # Physically invalid gradient at or above 1.0.
        with self.assertRaises(ValueError):
            sd.downwash_gradient(6.0, 0.5)


class TailVolumeTest(unittest.TestCase):
    def test_horizontal_anchor(self):
        # 3 * 2 / (0.5 * 20) = 0.6
        self.assertAlmostEqual(
            sd.tail_volume_coeff(3.0, 2.0, 0.5, 20.0), 0.6, delta=1e-9
        )

    def test_vertical_anchor(self):
        # 4 * 1.5 / (12 * 20) = 0.025
        self.assertAlmostEqual(
            sd.vertical_tail_volume_coeff(4.0, 1.5, 12.0, 20.0),
            0.025,
            delta=1e-9,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sd.tail_volume_coeff(0.0, 2.0, 0.5, 20.0)
        with self.assertRaises(ValueError):
            sd.tail_volume_coeff(3.0, -1.0, 0.5, 20.0)
        with self.assertRaises(ValueError):
            sd.vertical_tail_volume_coeff(4.0, 1.5, 0.0, 20.0)
        with self.assertRaises(ValueError):
            sd.vertical_tail_volume_coeff(4.0, 1.5, 12.0, -20.0)


class CmAlphaTest(unittest.TestCase):
    def test_anchor_value(self):
        # 4.5*0.05 - 0.6*4.0*0.6 = 0.225 - 1.44 = -1.215 (pitch stable)
        self.assertAlmostEqual(
            sd.cm_alpha(4.5, 0.3, 0.25, 0.6, 4.0, 0.4), -1.215, delta=1e-9
        )

    def test_aft_cg_reduces_stability(self):
        self.assertGreater(
            sd.cm_alpha(4.5, 0.4, 0.25, 0.6, 4.0, 0.4),
            sd.cm_alpha(4.5, 0.3, 0.25, 0.6, 4.0, 0.4),
        )

    def test_no_tail_is_unstable(self):
        # Without a tail the configuration is pitch unstable.
        self.assertGreater(sd.cm_alpha(4.5, 0.3, 0.25, 0.6, 4.0, 0.4), -1e9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sd.cm_alpha(4.5, 0.0, 0.25, 0.6, 4.0, 0.4)
        with self.assertRaises(ValueError):
            sd.cm_alpha(4.5, 0.3, 1.0, 0.6, 4.0, 0.4)
        with self.assertRaises(ValueError):
            sd.cm_alpha(4.5, 0.3, 0.25, 0.0, 4.0, 0.4)
        with self.assertRaises(ValueError):
            sd.cm_alpha(4.5, 0.3, 0.25, 0.6, 0.0, 0.4)
        with self.assertRaises(ValueError):
            sd.cm_alpha(4.5, 0.3, 0.25, 0.6, 4.0, 1.0)


class NeutralPointStaticMarginTest(unittest.TestCase):
    def test_neutral_point_anchor(self):
        # 0.25 + 0.6 * (4.0/4.5) * 0.6 = 0.57
        self.assertAlmostEqual(
            sd.neutral_point(4.5, 4.0, 0.6, 0.4, 0.25), 0.57, delta=1e-9
        )

    def test_static_margin_anchor(self):
        self.assertAlmostEqual(
            sd.static_margin(0.57, 0.3), 0.27, delta=1e-9
        )

    def test_positive_margin_is_stable(self):
        self.assertGreater(sd.static_margin(0.57, 0.3), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sd.neutral_point(0.0, 4.0, 0.6, 0.4, 0.25)
        with self.assertRaises(ValueError):
            sd.neutral_point(4.5, 0.0, 0.6, 0.4, 0.25)
        with self.assertRaises(ValueError):
            sd.neutral_point(4.5, 4.0, 0.6, 1.0, 0.25)
        with self.assertRaises(ValueError):
            sd.static_margin(0.0, 0.3)
        with self.assertRaises(ValueError):
            sd.static_margin(0.57, 1.0)


class DirectionalDerivativesTest(unittest.TestCase):
    def test_cn_beta_wing_body_anchor(self):
        # -(0.5^2 / (pi*6)) * tan(25 deg) = -0.00618
        self.assertAlmostEqual(
            sd.cn_beta_wing_body(0.5, 6.0, 25.0), -0.00618, delta=1e-4
        )

    def test_cn_beta_vertical_tail_anchor(self):
        # 0.025 * 4.0 * (1 + 0.72) = 0.172
        self.assertAlmostEqual(
            sd.cn_beta_vertical_tail(0.025, 4.0), 0.172, delta=1e-9
        )

    def test_cn_beta_total_stabilizing(self):
        total = sd.cn_beta(0.5, 6.0, 25.0, 0.025, 4.0)
        self.assertGreater(total, 0.0)

    def test_unswept_zero_lift_wing_body_zero(self):
        self.assertAlmostEqual(sd.cn_beta_wing_body(0.0, 6.0, 0.0), 0.0,
                               delta=1e-12)

    def test_cl_beta_dihedral_anchor(self):
        # -(4.5/2) * 5 deg in rad = -0.19635
        self.assertAlmostEqual(
            sd.cl_beta(4.5, 5.0), -0.19635, delta=1e-4
        )

    def test_cl_beta_zero_dihedral_zero(self):
        self.assertAlmostEqual(sd.cl_beta(4.5, 0.0), 0.0, delta=1e-12)

    def test_cl_p_anchor(self):
        # -(4.5/12) * (1 + 3*0.4)/(1 + 0.4) = -0.58929
        self.assertAlmostEqual(
            sd.cl_p(6.0, 0.4, 4.5), -0.58929, delta=1e-4
        )

    def test_cl_p_always_damping(self):
        self.assertLess(sd.cl_p(6.0, 1.0, 5.0), 0.0)

    def test_cl_r_anchor(self):
        # (0.5/4) * (1 + 3*0.4)/(1 + 0.4) = 0.19643
        self.assertAlmostEqual(sd.cl_r(0.5, 0.4), 0.19643, delta=1e-4)

    def test_cn_p_anchor(self):
        self.assertAlmostEqual(sd.cn_p(0.5), -0.0625, delta=1e-9)

    def test_cn_p_zero_lift_zero(self):
        self.assertAlmostEqual(sd.cn_p(0.0), 0.0, delta=1e-12)

    def test_cn_r_anchor(self):
        # -2 * 0.025 * 4.0 * (4/12) = -0.06667
        self.assertAlmostEqual(sd.cn_r(0.025, 4.0, 4.0, 12.0), -0.06667,
                               delta=1e-4)

    def test_cn_r_always_damping(self):
        self.assertLess(sd.cn_r(0.025, 4.0, 4.0, 12.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sd.cn_beta_wing_body(-0.5, 6.0, 25.0)
        with self.assertRaises(ValueError):
            sd.cn_beta_wing_body(0.5, 0.0, 25.0)
        with self.assertRaises(ValueError):
            sd.cn_beta_vertical_tail(0.0, 4.0)
        with self.assertRaises(ValueError):
            sd.cn_beta_vertical_tail(0.025, 0.0)
        with self.assertRaises(ValueError):
            sd.cn_beta_vertical_tail(0.025, 4.0, sidewash_factor=-1.0)
        with self.assertRaises(ValueError):
            sd.cl_beta(0.0, 5.0)
        with self.assertRaises(ValueError):
            sd.cl_beta(4.5, 50.0)
        with self.assertRaises(ValueError):
            sd.cl_p(6.0, 0.0, 4.5)
        with self.assertRaises(ValueError):
            sd.cl_p(6.0, 1.5, 4.5)
        with self.assertRaises(ValueError):
            sd.cl_r(-0.1, 0.4)
        with self.assertRaises(ValueError):
            sd.cn_r(0.025, 4.0, 0.0, 12.0)


class DerivativeTableTest(unittest.TestCase):
    CFG = dict(
        aspect_ratio=6.0,
        sweep_quarter_chord_deg=25.0,
        mach=0.4,
        taper_ratio=0.4,
        h_cg=0.3,
        h_ac_w=0.25,
        l_t=3.0,
        s_t=2.0,
        c_bar=0.5,
        s_w=20.0,
        l_v=4.0,
        s_v=1.5,
        b=12.0,
        dihedral_deg=5.0,
        c_l=0.5,
    )

    def test_table_has_all_rows(self):
        t = sd.estimate_derivative_table(**self.CFG)
        for key in [
            "cl_alpha_wing", "cl_alpha_tail", "downwash_gradient",
            "tail_volume_coeff", "vertical_tail_volume_coeff", "cm_alpha",
            "neutral_point", "static_margin", "cn_beta", "cl_beta", "cl_p",
            "cl_r", "cn_p", "cn_r", "pitch_stable", "directionally_stable",
            "statically_stable",
        ]:
            self.assertIn(key, t)

    def test_table_rows_consistent_with_functions(self):
        t = sd.estimate_derivative_table(**self.CFG)
        self.assertAlmostEqual(
            t["cl_alpha_wing"],
            sd.cl_alpha_wing(6.0, 25.0, 0.4),
            delta=1e-9,
        )
        self.assertAlmostEqual(
            t["cl_alpha_tail"], t["cl_alpha_wing"], delta=1e-9
        )
        self.assertAlmostEqual(
            t["cm_alpha"],
            sd.cm_alpha(t["cl_alpha_wing"], 0.3, 0.25, t["tail_volume_coeff"],
                        t["cl_alpha_tail"], t["downwash_gradient"]),
            delta=1e-9,
        )
        self.assertAlmostEqual(
            t["static_margin"], t["neutral_point"] - 0.3, delta=1e-9
        )
        self.assertAlmostEqual(
            t["cn_beta"],
            sd.cn_beta(0.5, 6.0, 25.0, t["vertical_tail_volume_coeff"],
                       t["cl_alpha_tail"]),
            delta=1e-9,
        )

    def test_table_verdicts(self):
        t = sd.estimate_derivative_table(**self.CFG)
        self.assertTrue(t["pitch_stable"])
        self.assertTrue(t["directionally_stable"])
        self.assertTrue(t["statically_stable"])

    def test_table_unstable_configuration(self):
        cfg = dict(self.CFG)
        cfg["h_cg"] = 0.65  # far aft of the neutral point
        t = sd.estimate_derivative_table(**cfg)
        self.assertFalse(t["pitch_stable"])
        self.assertFalse(t["statically_stable"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
