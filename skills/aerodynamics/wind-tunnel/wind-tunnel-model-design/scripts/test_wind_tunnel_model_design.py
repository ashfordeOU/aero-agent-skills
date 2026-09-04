#!/usr/bin/env python3
"""Behavior contract tests for wind-tunnel-model-design logic.

Stdlib unittest, offline, deterministic. Run:
python3 skills/aerodynamics/wind-tunnel/wind-tunnel-model-design/scripts/test_wind_tunnel_model_design.py

Contract: (a) the documented worked example reproduces the reference
values: test section 2.44 m square (area 5.9536 m2), full-scale
transport span 34.0 m, wing area 122.6 m2, MAC 4.2 m, full Reynolds
3.0e7, tunnel max speed 80 m/s, max_test_cl 1.4, balance capacity
5000 N, sting arm 0.35 m, sting allowable 800 MPa, giving scale
0.04927, model area 0.29761 m2, model MAC 0.20693 m, model span
1.6752 m, blockage ratio 0.04999, model Reynolds 1.1337e6, Reynolds
ratio 0.03779 (reynolds-mismatch), q 3920 Pa, load 1633.3 N
(balance-ok), sting diameter 19.38 mm; (b) scale selection takes the
smaller of the blockage and span limits and round-trips the model
dimensions against the scale; (c) ValueError on non-positive inputs
and on a missing test section area; (d) the balance overload verdict.

Anchor tolerances follow the spec: scale, area, MAC, blockage ratio
within 1e-4, Reynolds within 1e3, load within 1 N, sting diameter
within 0.01 mm. The model span and MAC anchors are computed in the
spec from the scale truncated to five decimals (34*0.04927), while the
code carries the full-precision scale, so the span anchor is asserted
within 2e-4 (0.01% relative) and the scale identity is asserted
exactly.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wind_tunnel_model_design_logic import (  # noqa: E402
    BLOCKAGE_MAX,
    RHO_SL,
    analyze,
    balance_verdict,
    choose_scale,
    model_load_N,
    reynolds_model,
    reynolds_ratio,
    scale_from_blockage,
    scale_from_span,
    sting_diameter_m,
    section_area,
)

# Worked example inputs from the spec.
EXAMPLE = {
    "test_section_width_m": 2.44,
    "test_section_height_m": 2.44,
    "full_span_m": 34.0,
    "full_wing_area_m2": 122.6,
    "full_mac_m": 4.2,
    "full_reynolds": 3.0e7,
    "tunnel_max_speed_m_s": 80.0,
    "max_test_cl": 1.4,
    "balance_capacity_N": 5000.0,
    "sting_arm_m": 0.35,
    "sting_allowable_stress_pa": 800.0e6,
    "blockage_max": 0.05,
}


class TestSectionAreaTests(unittest.TestCase):
    def test_test_section_area_square(self):
        # 2.44 m square section.
        self.assertAlmostEqual(section_area(2.44, 2.44), 5.9536, places=4)

    def test_test_section_area_rectangular(self):
        self.assertAlmostEqual(section_area(3.0, 2.0), 6.0, places=9)

    def test_test_section_area_zero_width_raises(self):
        with self.assertRaises(ValueError):
            section_area(0.0, 2.44)

    def test_test_section_area_negative_height_raises(self):
        with self.assertRaises(ValueError):
            section_area(2.44, -1.0)


class ScaleSelectionTests(unittest.TestCase):
    def test_scale_from_blockage_anchor(self):
        # sqrt(0.05 * 5.9536 / 122.6) = sqrt(0.002428) = 0.04927.
        self.assertAlmostEqual(
            scale_from_blockage(5.9536, 122.6), 0.04927, delta=1e-4
        )

    def test_scale_from_span_anchor(self):
        # (2.44 * 0.8) / 34.0 = 1.952 / 34 = 0.05741.
        self.assertAlmostEqual(
            scale_from_span(2.44, 34.0), 0.05741, delta=1e-4
        )

    def test_choose_scale_takes_minimum_of_limits(self):
        chosen = choose_scale(5.9536, 122.6, 2.44, 34.0, 4.2)
        self.assertAlmostEqual(chosen["scale"], 0.04927, delta=1e-4)
        self.assertAlmostEqual(
            chosen["scale"], min(chosen["lambda_blockage"], chosen["lambda_span"]),
            places=12,
        )
        self.assertLess(chosen["scale"], chosen["lambda_span"])

    def test_choose_scale_model_dimension_anchors(self):
        chosen = choose_scale(5.9536, 122.6, 2.44, 34.0, 4.2)
        # Model wing area 122.6 * 0.0024275 = 0.29761 m2 (within 1e-4).
        self.assertAlmostEqual(chosen["model_wing_area"], 0.29761, delta=1e-4)
        # Model MAC 4.2 * 0.04927 = 0.20693 m (within 1e-4).
        self.assertAlmostEqual(chosen["model_mac"], 0.20693, delta=1e-4)
        # Model span 34 * 0.04927 = 1.6752 m; the anchor uses the scale
        # truncated to five decimals, so assert within 2e-4.
        self.assertAlmostEqual(chosen["model_span"], 1.6752, delta=2e-4)

    def test_choose_scale_blockage_ratio_anchor(self):
        chosen = choose_scale(5.9536, 122.6, 2.44, 34.0, 4.2)
        # 0.29761 / 5.9536 = 0.04999, within 1e-4 of the exact ratio.
        self.assertAlmostEqual(chosen["blockage_ratio"], 0.04999, delta=1e-4)
        self.assertTrue(chosen["blocked_ok"])

    def test_choose_scale_dimension_round_trip(self):
        # Model area scales with scale squared, span and MAC with scale.
        chosen = choose_scale(5.9536, 122.6, 2.44, 34.0, 4.2)
        scale = chosen["scale"]
        self.assertAlmostEqual(chosen["model_wing_area"], 122.6 * scale * scale, places=9)
        self.assertAlmostEqual(chosen["model_span"], 34.0 * scale, places=9)
        self.assertAlmostEqual(chosen["model_mac"], 4.2 * scale, places=9)
        self.assertAlmostEqual(
            chosen["model_wing_area"] / chosen["model_span"], 122.6 / 34.0 * scale,
            places=6,
        )

    def test_choose_scale_span_limited_case(self):
        # Narrow 1.0 m section on a 40 m span aircraft: span clearance
        # binds, scale = 0.8 / 40 = 0.02 and the model still fits the
        # blockage limit.
        chosen = choose_scale(1.0, 100.0, 1.0, 40.0, 5.0)
        self.assertAlmostEqual(chosen["lambda_span"], 0.02, places=6)
        self.assertAlmostEqual(chosen["scale"], 0.02, places=6)
        self.assertAlmostEqual(chosen["scale"], chosen["lambda_span"], places=12)
        self.assertTrue(chosen["blocked_ok"])
        self.assertAlmostEqual(chosen["model_wing_area"], 100.0 * 0.02 * 0.02, places=9)

    def test_choose_scale_nonpositive_raises(self):
        with self.assertRaises(ValueError):
            choose_scale(0.0, 122.6, 2.44, 34.0, 4.2)
        with self.assertRaises(ValueError):
            choose_scale(5.9536, -122.6, 2.44, 34.0, 4.2)
        with self.assertRaises(ValueError):
            choose_scale(5.9536, 122.6, 2.44, 0.0, 4.2)
        with self.assertRaises(ValueError):
            choose_scale(5.9536, 122.6, 2.44, 34.0, 0.0)
        with self.assertRaises(ValueError):
            choose_scale(5.9536, 122.6, 2.44, 34.0, 4.2, blockage_max=0.0)


class ReynoldsTests(unittest.TestCase):
    def test_reynolds_model_anchor(self):
        # rho * V * MAC / mu = 1.225 * 80 * 0.20693 / 1.789e-5 = 1.1337e6.
        chosen = choose_scale(5.9536, 122.6, 2.44, 34.0, 4.2)
        re_model = reynolds_model(80.0, chosen["model_mac"])
        self.assertAlmostEqual(re_model, 1.1337e6, delta=1e3)
        # Reynolds scales linearly with speed.
        self.assertAlmostEqual(
            reynolds_model(40.0, chosen["model_mac"]), 0.5 * re_model, places=6
        )

    def test_reynolds_model_zero_speed_raises(self):
        with self.assertRaises(ValueError):
            reynolds_model(0.0, 0.20693)

    def test_reynolds_ratio_anchor(self):
        # 1.1337e6 / 3.0e7 = 0.03779.
        self.assertAlmostEqual(
            reynolds_ratio(1.1337e6, 3.0e7), 0.03779, delta=1e-4
        )

    def test_reynolds_ratio_zero_full_re_raises(self):
        with self.assertRaises(ValueError):
            reynolds_ratio(1.1337e6, 0.0)


class LoadAndBalanceTests(unittest.TestCase):
    def test_model_load_anchor(self):
        # q = 0.5 * 1.225 * 80^2 = 3920 Pa; load = 3920 * 0.29761 * 1.4
        # = 1633.3 N (within 1 N).
        chosen = choose_scale(5.9536, 122.6, 2.44, 34.0, 4.2)
        q = 0.5 * RHO_SL * 80.0 * 80.0
        self.assertAlmostEqual(q, 3920.0, places=6)
        load = model_load_N(q, chosen["model_wing_area"], 1.4)
        self.assertAlmostEqual(load, 1633.3, delta=1.0)

    def test_model_load_scales_with_cl(self):
        load_1_4 = model_load_N(3920.0, 0.29761, 1.4)
        load_1_0 = model_load_N(3920.0, 0.29761, 1.0)
        self.assertAlmostEqual(load_1_4, 1.4 * load_1_0, places=6)

    def test_model_load_nonpositive_cl_raises(self):
        with self.assertRaises(ValueError):
            model_load_N(3920.0, 0.29761, 0.0)

    def test_balance_verdict_ok(self):
        self.assertEqual(balance_verdict(1633.3, 5000.0), "balance-ok")
        # A load exactly at capacity is still within rating.
        self.assertEqual(balance_verdict(5000.0, 5000.0), "balance-ok")

    def test_balance_verdict_overload(self):
        # Balance capacity 1000 N against a 1633 N load.
        self.assertEqual(balance_verdict(1633.3, 1000.0), "balance-overload")

    def test_balance_verdict_zero_capacity_raises(self):
        with self.assertRaises(ValueError):
            balance_verdict(1633.3, 0.0)


class StingSizingTests(unittest.TestCase):
    def test_sting_diameter_anchor(self):
        # M = 1633.3 * 0.35 = 571.7 N m; d = (32*M/(pi*800e6))^(1/3)
        # = 0.01938 m = 19.38 mm (within 0.01 mm).
        diameter = sting_diameter_m(571.7, 800.0e6)
        self.assertAlmostEqual(diameter, 0.01938, delta=1e-5)
        self.assertAlmostEqual(diameter * 1000.0, 19.38, delta=0.01)

    def test_sting_diameter_scales_with_moment(self):
        d1 = sting_diameter_m(571.7, 800.0e6)
        d2 = sting_diameter_m(571.7 * 8.0, 800.0e6)
        # Diameter grows with the cube root of the moment.
        self.assertAlmostEqual(d2, 2.0 * d1, places=6)

    def test_sting_diameter_zero_moment_raises(self):
        with self.assertRaises(ValueError):
            sting_diameter_m(0.0, 800.0e6)

    def test_sting_diameter_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            sting_diameter_m(571.7, 0.0)


class AnalyzeTests(unittest.TestCase):
    def test_analyze_full_summary_anchors(self):
        result = analyze(dict(EXAMPLE))
        self.assertAlmostEqual(result["scale"], 0.04927, delta=1e-4)
        self.assertAlmostEqual(result["model_wing_area"], 0.29761, delta=1e-4)
        self.assertAlmostEqual(result["blockage_ratio"], 0.04999, delta=1e-4)
        self.assertTrue(result["blocked_ok"])
        self.assertAlmostEqual(result["model_reynolds"], 1.1337e6, delta=1e3)
        self.assertAlmostEqual(result["reynolds_ratio"], 0.03779, delta=1e-4)
        self.assertEqual(result["reynolds_limitation"], "reynolds-mismatch")
        self.assertAlmostEqual(result["dynamic_pressure_pa"], 3920.0, places=6)
        self.assertAlmostEqual(result["model_load_N"], 1633.3, delta=1.0)
        self.assertEqual(result["balance_verdict"], "balance-ok")
        self.assertAlmostEqual(result["sting_diameter_m"], 0.01938, delta=1e-5)

    def test_analyze_bending_moment_identity(self):
        result = analyze(dict(EXAMPLE))
        self.assertAlmostEqual(
            result["sting_bending_moment_Nm"],
            result["model_load_N"] * EXAMPLE["sting_arm_m"],
            places=9,
        )

    def test_analyze_default_max_test_cl(self):
        # Omitting max_test_cl uses the 1.4 default.
        inputs = dict(EXAMPLE)
        del inputs["max_test_cl"]
        result = analyze(inputs)
        self.assertAlmostEqual(result["model_load_N"], 1633.3, delta=1.0)
        self.assertEqual(result["balance_verdict"], "balance-ok")

    def test_analyze_area_given_directly(self):
        # Height may be omitted when the test section area is given.
        inputs = dict(EXAMPLE)
        del inputs["test_section_height_m"]
        inputs["test_section_area_m2"] = 2.44 * 2.44
        result = analyze(inputs)
        self.assertAlmostEqual(result["scale"], 0.04927, delta=1e-4)
        self.assertAlmostEqual(result["model_reynolds"], 1.1337e6, delta=1e3)

    def test_analyze_overload_inputs_give_overload(self):
        inputs = dict(EXAMPLE)
        inputs["balance_capacity_N"] = 1000.0
        result = analyze(inputs)
        self.assertEqual(result["balance_verdict"], "balance-overload")
        self.assertAlmostEqual(result["model_load_N"], 1633.3, delta=1.0)

    def test_analyze_reynolds_matched_case(self):
        # A full-scale Reynolds of 2e6 puts the ratio above 0.5.
        inputs = dict(EXAMPLE)
        inputs["full_reynolds"] = 2.0e6
        result = analyze(inputs)
        self.assertGreaterEqual(result["reynolds_ratio"], 0.5)
        self.assertEqual(result["reynolds_limitation"], "reynolds-matched")

    def test_analyze_deterministic(self):
        self.assertEqual(analyze(dict(EXAMPLE)), analyze(dict(EXAMPLE)))

    def test_analyze_valueerrors(self):
        cases = [
            {"test_section_width_m": 0.0},   # zero section width
            {"balance_capacity_N": 0.0},     # zero balance capacity
            {"full_reynolds": 0.0},          # zero full-scale Reynolds
            {"tunnel_max_speed_m_s": -5.0},  # non-positive tunnel speed
            {"sting_arm_m": 0.0},            # zero sting arm
            {"max_test_cl": -1.0},           # non-positive lift coefficient
            {"full_span_m": 0.0},            # zero full-scale span
        ]
        for override in cases:
            inputs = dict(EXAMPLE)
            inputs.update(override)
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    analyze(inputs)

    def test_analyze_missing_area_and_height_raises(self):
        inputs = dict(EXAMPLE)
        del inputs["test_section_height_m"]
        with self.assertRaises(ValueError):
            analyze(inputs)


if __name__ == "__main__":
    unittest.main()
