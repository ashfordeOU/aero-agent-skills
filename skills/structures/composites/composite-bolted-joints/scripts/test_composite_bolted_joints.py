#!/usr/bin/env python3
"""Gate 3 contract test: bolted joint analysis in composite laminates.

Exercises scripts/composite_bolted_joints_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - bearing stress
sigma_b = P_b / (D * t), net-tension stress sigma_nt = P / ((w - D) * t),
shear-out stress sigma_so = P / (2 * e * t), margin M = allowable /
applied - 1, bypass split P_bp = r * P with P_b = (1 - r) * P, and
joint efficiency eta = (w - D) / w.

Hand values for P = 10000 N, D = 6.35 mm, t = 4.0 mm, w = 30.0 mm,
e = 15.0 mm:
- bearing stress = 10000 / (6.35 * 4) = 10000 / 25.4 = 393.7007874015748
- net-tension stress = 10000 / ((30 - 6.35) * 4) = 10000 / 94.6
  = 105.70824524312896
- shear-out stress = 10000 / (2 * 15 * 4) = 10000 / 120 = 83.33333333333333
- margins with Fbru = 500, Fnt = 250, Fso = 120 MPa:
  bearing = 500 / 393.7007874015748 - 1 = 0.27
  net-tension = 250 / 105.70824524312896 - 1 = 1.365
  shear-out = 120 / 83.33333333333333 - 1 = 0.44
- joint efficiency = (30 - 6.35) / 30 = 0.7883333333333333
- bypass ratio 0.3: P_bp = 3000 N, P_b = 7000 N, bearing stress
  = 7000 / 25.4 = 275.5905511811024
- pitch 25.0 mm: net section per fastener (25 - 6.35) * 4 = 74.6,
  net-tension stress = 10000 / 74.6 = 134.04825737265416
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import composite_bolted_joints_logic as cj  # noqa: E402

LOAD = 10000.0
BOLT_D = 6.35
THICK = 4.0
WIDTH = 30.0
EDGE = 15.0
FBRU = 500.0
FNT = 250.0
FSO = 120.0

BEARING_STRESS = 393.7007874015748  # 10000 / 25.4
NET_TENSION_STRESS = 105.70824524312896  # 10000 / 94.6
SHEAR_OUT_STRESS = 83.33333333333333  # 10000 / 120
BEARING_MARGIN = 0.27
NET_TENSION_MARGIN = 1.365
SHEAR_OUT_MARGIN = 0.44
JOINT_EFF = 0.7883333333333333  # 23.65 / 30


class BearingStressTest(unittest.TestCase):
    def test_analytic_bearing_stress(self):
        # sigma_b = P / (D * t) = 10000 / (6.35 * 4) = 10000 / 25.4.
        got = cj.bearing_stress(LOAD, BOLT_D, THICK)
        self.assertAlmostEqual(got, BEARING_STRESS, places=10)
        self.assertAlmostEqual(got, 10000.0 / (6.35 * 4.0), places=12)

    def test_bearing_stress_scales_with_bolt_diameter(self):
        # Doubling D halves the bearing stress for the same load.
        self.assertAlmostEqual(
            cj.bearing_stress(LOAD, 2 * BOLT_D, THICK),
            BEARING_STRESS / 2.0,
            places=10,
        )

    def test_nonpositive_load_raises(self):
        with self.assertRaises(ValueError):
            cj.bearing_stress(0.0, BOLT_D, THICK)
        with self.assertRaises(ValueError):
            cj.bearing_stress(-100.0, BOLT_D, THICK)

    def test_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            cj.bearing_stress(LOAD, BOLT_D, 0.0)


class NetTensionStressTest(unittest.TestCase):
    def test_analytic_net_tension_stress(self):
        # sigma_nt = P / ((w - D) * t) = 10000 / (23.65 * 4) = 10000 / 94.6.
        got = cj.net_tension_stress(LOAD, WIDTH, BOLT_D, THICK)
        self.assertAlmostEqual(got, NET_TENSION_STRESS, places=10)
        self.assertAlmostEqual(got, 10000.0 / (23.65 * 4.0), places=12)

    def test_bolt_diameter_at_least_width_raises(self):
        # Net section (w - D) must stay positive.
        with self.assertRaises(ValueError):
            cj.net_tension_stress(LOAD, BOLT_D, BOLT_D, THICK)
        with self.assertRaises(ValueError):
            cj.net_tension_stress(LOAD, 5.0, BOLT_D, THICK)


class ShearOutStressTest(unittest.TestCase):
    def test_analytic_shear_out_stress(self):
        # sigma_so = P / (2 * e * t) = 10000 / (2 * 15 * 4) = 10000 / 120.
        got = cj.shear_out_stress(LOAD, EDGE, THICK)
        self.assertAlmostEqual(got, SHEAR_OUT_STRESS, places=10)
        self.assertAlmostEqual(got, 10000.0 / 120.0, places=12)

    def test_doubling_edge_distance_halves_stress(self):
        self.assertAlmostEqual(
            cj.shear_out_stress(LOAD, 2 * EDGE, THICK),
            SHEAR_OUT_STRESS / 2.0,
            places=10,
        )

    def test_zero_edge_distance_raises(self):
        with self.assertRaises(ValueError):
            cj.shear_out_stress(LOAD, 0.0, THICK)


class MarginTest(unittest.TestCase):
    def test_analytic_margins(self):
        self.assertAlmostEqual(
            cj.margin_of(FBRU, BEARING_STRESS), BEARING_MARGIN, places=6
        )
        self.assertAlmostEqual(
            cj.margin_of(FNT, NET_TENSION_STRESS), NET_TENSION_MARGIN, places=6
        )
        self.assertAlmostEqual(
            cj.margin_of(FSO, SHEAR_OUT_STRESS), SHEAR_OUT_MARGIN, places=6
        )

    def test_margin_zero_at_allowable(self):
        self.assertAlmostEqual(cj.margin_of(FBRU, FBRU), 0.0, places=12)

    def test_margin_negative_above_allowable(self):
        # 700 MPa applied against a 500 MPa allowable fails.
        self.assertLess(cj.margin_of(FBRU, 700.0), 0.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            cj.margin_of(0.0, BEARING_STRESS)


class BypassSplitTest(unittest.TestCase):
    def test_analytic_split(self):
        # r = 0.3: bypass 3000 N, bearing 7000 N, sum preserved.
        bypass_load, bearing_load = cj.bypass_split(LOAD, 0.3)
        self.assertAlmostEqual(bypass_load, 3000.0, places=12)
        self.assertAlmostEqual(bearing_load, 7000.0, places=12)
        self.assertAlmostEqual(bypass_load + bearing_load, LOAD, places=12)

    def test_bypass_ratio_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            cj.bypass_split(LOAD, 1.2)
        with self.assertRaises(ValueError):
            cj.bypass_split(LOAD, -0.1)

    def test_bypass_ratio_boundaries(self):
        # r = 0: all load bearing. r = 1: all load bypasses the bolt.
        self.assertAlmostEqual(cj.bypass_split(LOAD, 0.0)[1], LOAD, places=12)
        self.assertAlmostEqual(cj.bypass_split(LOAD, 1.0)[0], LOAD, places=12)


class JointEfficiencyTest(unittest.TestCase):
    def test_analytic_joint_efficiency(self):
        # eta = (w - D) / w = 23.65 / 30.
        self.assertAlmostEqual(
            cj.joint_efficiency(WIDTH, BOLT_D), JOINT_EFF, places=12
        )

    def test_bolt_diameter_at_least_width_raises(self):
        with self.assertRaises(ValueError):
            cj.joint_efficiency(5.0, BOLT_D)


class JointAnalysisTest(unittest.TestCase):
    def test_report_full_bypass_case(self):
        # Bypass ratio 0.3 with otherwise Case A geometry: bearing load
        # 7000 N gives bearing stress 7000 / 25.4 = 275.5905511811024
        # and bearing margin 500 / 275.5905511811024 - 1 = 0.8142857.
        report = cj.joint_analysis(
            LOAD,
            BOLT_D,
            THICK,
            WIDTH,
            EDGE,
            FBRU,
            FNT,
            FSO,
            bypass_ratio=0.3,
        )
        self.assertAlmostEqual(report["bypass_load"], 3000.0, places=10)
        self.assertAlmostEqual(report["bearing_load"], 7000.0, places=10)
        self.assertAlmostEqual(
            report["bearing_stress"], 275.5905511811024, places=10
        )
        self.assertAlmostEqual(
            report["net_tension_stress"], NET_TENSION_STRESS, places=10
        )
        self.assertAlmostEqual(
            report["shear_out_stress"], SHEAR_OUT_STRESS, places=10
        )
        self.assertAlmostEqual(
            report["bearing_margin"], 0.8142857142857143, places=8
        )
        self.assertAlmostEqual(
            report["net_tension_margin"], NET_TENSION_MARGIN, places=8
        )
        self.assertAlmostEqual(
            report["shear_out_margin"], SHEAR_OUT_MARGIN, places=8
        )
        self.assertEqual(report["governing_mode"], "shear-out")
        self.assertAlmostEqual(report["min_margin"], SHEAR_OUT_MARGIN, places=8)
        self.assertTrue(report["passes"])
        self.assertAlmostEqual(report["joint_efficiency"], JOINT_EFF, places=10)
        self.assertEqual(report["effective_width"], WIDTH)

    def test_report_governing_bearing_when_overloaded(self):
        # P = 30000 N: bearing stress 1181.10 (margin -0.5767), net-tension
        # 317.12 (margin -0.2117), shear-out 250 (margin -0.52); bearing is
        # the lowest margin, so the joint fails in bearing.
        report = cj.joint_analysis(
            30000.0, BOLT_D, THICK, WIDTH, EDGE, FBRU, FNT, FSO
        )
        self.assertAlmostEqual(report["bearing_stress"], 1181.1023622047244, places=8)
        self.assertAlmostEqual(report["bearing_margin"], -0.5766666666666667, places=6)
        self.assertEqual(report["governing_mode"], "bearing")
        self.assertFalse(report["passes"])

    def test_report_uses_pitch_as_tributary_width(self):
        # pitch 25.0 mm: net section per fastener (25 - 6.35) * 4 = 74.6,
        # net-tension stress = 10000 / 74.6 = 134.04825737265416.
        report = cj.joint_analysis(
            LOAD,
            BOLT_D,
            THICK,
            WIDTH,
            EDGE,
            FBRU,
            FNT,
            FSO,
            pitch=25.0,
        )
        self.assertEqual(report["effective_width"], 25.0)
        self.assertAlmostEqual(
            report["net_tension_stress"], 134.04825737265416, places=8
        )
        self.assertAlmostEqual(
            report["joint_efficiency"], 18.65 / 25.0, places=10
        )

    def test_report_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cj.joint_analysis(LOAD, BOLT_D, THICK, WIDTH, EDGE, 0.0, FNT, FSO)
        with self.assertRaises(ValueError):
            cj.joint_analysis(LOAD, BOLT_D, THICK, WIDTH, EDGE, FBRU, FNT, FSO,
                              bypass_ratio=1.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
