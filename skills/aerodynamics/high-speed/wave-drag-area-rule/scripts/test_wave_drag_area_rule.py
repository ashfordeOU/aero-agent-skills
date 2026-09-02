#!/usr/bin/env python3
"""Gate 3 contract test: wave drag and the Whitcomb area rule.

Exercises scripts/wave_drag_area_rule_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the Sears-Haack
minimum-drag body (radius distribution, cross-sectional area, volume,
zero-lift wave drag area D/q = (9 * pi / 2) * (A_max / L)^2, wave drag
coefficient and force), the area-rule fuselage pinch and the RMS
deviation of an area distribution from its target, the
drag-divergence Mach estimate above the critical Mach, and the
parabolic wave drag rise above M_DD, with range checks raising
ValueError on invalid inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wave_drag_area_rule_logic as wd  # noqa: E402


class SearsHaackRadiusTest(unittest.TestCase):
    def test_midpoint_is_max_radius(self):
        self.assertAlmostEqual(wd.sears_haack_radius(5.0, 10.0, 1.0), 1.0, delta=1e-12)

    def test_endpoints_are_zero(self):
        self.assertAlmostEqual(wd.sears_haack_radius(0.0, 10.0, 1.0), 0.0, delta=1e-12)
        self.assertAlmostEqual(wd.sears_haack_radius(10.0, 10.0, 1.0), 0.0, delta=1e-12)

    def test_quarter_station(self):
        # 4 * 0.25 * 0.75 = 0.75; 0.75^0.75 = 0.80593
        self.assertAlmostEqual(wd.sears_haack_radius(2.5, 10.0, 1.0), 0.80593, delta=1e-4)

    def test_symmetric_about_midpoint(self):
        self.assertAlmostEqual(
            wd.sears_haack_radius(3.0, 10.0, 1.0),
            wd.sears_haack_radius(7.0, 10.0, 1.0),
            delta=1e-12,
        )

    def test_scales_with_r_max(self):
        self.assertAlmostEqual(
            wd.sears_haack_radius(2.5, 10.0, 2.0),
            2.0 * wd.sears_haack_radius(2.5, 10.0, 1.0),
            delta=1e-12,
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            wd.sears_haack_radius(-0.1, 10.0, 1.0)
        with self.assertRaises(ValueError):
            wd.sears_haack_radius(10.1, 10.0, 1.0)
        with self.assertRaises(ValueError):
            wd.sears_haack_radius(2.0, 0.0, 1.0)
        with self.assertRaises(ValueError):
            wd.sears_haack_radius(2.0, -5.0, 1.0)
        with self.assertRaises(ValueError):
            wd.sears_haack_radius(2.0, 10.0, 0.0)
        with self.assertRaises(ValueError):
            wd.sears_haack_radius(2.0, 10.0, -1.0)


class SearsHaackAreaTest(unittest.TestCase):
    def test_midpoint_area(self):
        # pi * r_max^2 with r_max = 1.5
        self.assertAlmostEqual(wd.sears_haack_area(5.0, 10.0, 1.5), math.pi * 2.25, delta=1e-9)

    def test_endpoint_area_zero(self):
        self.assertAlmostEqual(wd.sears_haack_area(0.0, 10.0, 1.0), 0.0, delta=1e-12)

    def test_consistent_with_radius(self):
        r = wd.sears_haack_radius(3.0, 12.0, 2.0)
        self.assertAlmostEqual(wd.sears_haack_area(3.0, 12.0, 2.0), math.pi * r * r, delta=1e-9)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            wd.sears_haack_area(2.0, 10.0, 0.0)
        with self.assertRaises(ValueError):
            wd.sears_haack_area(20.0, 10.0, 1.0)


class SearsHaackVolumeTest(unittest.TestCase):
    def test_known_volume(self):
        # V = (3 * pi^2 / 16) * r_max^2 * L = 18.5055 for r_max 1, L 10
        self.assertAlmostEqual(wd.sears_haack_volume(10.0, 1.0), 18.5055, delta=1e-3)

    def test_doubling_radius_quadruples_volume(self):
        self.assertAlmostEqual(
            wd.sears_haack_volume(10.0, 2.0),
            4.0 * wd.sears_haack_volume(10.0, 1.0),
            delta=1e-9,
        )

    def test_doubling_length_doubles_volume(self):
        self.assertAlmostEqual(
            wd.sears_haack_volume(20.0, 1.0),
            2.0 * wd.sears_haack_volume(10.0, 1.0),
            delta=1e-9,
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            wd.sears_haack_volume(0.0, 1.0)
        with self.assertRaises(ValueError):
            wd.sears_haack_volume(10.0, 0.0)


class SearsHaackWaveDragAreaTest(unittest.TestCase):
    def test_known_drag_area(self):
        # (9 * pi / 2) * (pi / 10)^2 = 1.39528 for r_max 1, L 10
        self.assertAlmostEqual(wd.sears_haack_wave_drag_area(10.0, 1.0), 1.39528, delta=1e-4)

    def test_fuselage_example(self):
        # L = 15 m, r_max = 0.54 m: A_max = 0.91609, D/q = 0.05274 m^2
        self.assertAlmostEqual(wd.sears_haack_wave_drag_area(15.0, 0.54), 0.05274, delta=1e-4)

    def test_volume_form_identity(self):
        # D/q = 128 * V^2 / (pi * L^4) is algebraically identical
        v = wd.sears_haack_volume(12.0, 1.3)
        volume_form = 128.0 * v * v / (math.pi * (12.0 ** 4))
        self.assertAlmostEqual(
            wd.sears_haack_wave_drag_area(12.0, 1.3), volume_form, delta=1e-9
        )

    def test_slender_body_has_lower_drag_area(self):
        self.assertLess(
            wd.sears_haack_wave_drag_area(20.0, 1.0),
            wd.sears_haack_wave_drag_area(10.0, 1.0),
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            wd.sears_haack_wave_drag_area(0.0, 1.0)
        with self.assertRaises(ValueError):
            wd.sears_haack_wave_drag_area(10.0, -1.0)


class SearsHaackWaveDragCoefTest(unittest.TestCase):
    def test_known_coefficient(self):
        # C_Dw = (9 * pi / 2) * (A_max / L^2) = 0.44416 for r_max 1, L 10
        self.assertAlmostEqual(wd.sears_haack_wave_drag_coef(10.0, 1.0), 0.44416, delta=1e-4)

    def test_fineness_ten_coefficient(self):
        # fineness ratio 10 (L = 20 * r_max): C_Dw ~ 0.11
        self.assertAlmostEqual(wd.sears_haack_wave_drag_coef(20.0, 1.0), 0.11104, delta=1e-4)

    def test_consistent_with_drag_area(self):
        a_max = math.pi * 1.3 ** 2
        self.assertAlmostEqual(
            wd.sears_haack_wave_drag_coef(12.0, 1.3) * a_max,
            wd.sears_haack_wave_drag_area(12.0, 1.3),
            delta=1e-9,
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            wd.sears_haack_wave_drag_coef(10.0, 0.0)


class WaveDragForceTest(unittest.TestCase):
    def test_force_from_dynamic_pressure(self):
        # D = q * (D/q) = 15000 * 1.39528 = 20929.24
        self.assertAlmostEqual(wd.wave_drag_force(15000.0, 10.0, 1.0), 20929.24, delta=0.1)

    def test_zero_dynamic_pressure(self):
        self.assertAlmostEqual(wd.wave_drag_force(0.0, 10.0, 1.0), 0.0, delta=1e-12)

    def test_force_scales_with_q(self):
        self.assertAlmostEqual(
            wd.wave_drag_force(30000.0, 10.0, 1.0),
            2.0 * wd.wave_drag_force(15000.0, 10.0, 1.0),
            delta=1e-9,
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            wd.wave_drag_force(-1000.0, 10.0, 1.0)
        with self.assertRaises(ValueError):
            wd.wave_drag_force(15000.0, 0.0, 1.0)


class AreaRuleFuselageAreaTest(unittest.TestCase):
    def test_pinch_keeps_total_on_target(self):
        # wing contributes 0.5 at a station, target total 2.0 -> pinch to 1.5
        self.assertAlmostEqual(wd.area_rule_fuselage_area(2.0, 0.5), 1.5, delta=1e-12)

    def test_no_wing_no_pinch(self):
        self.assertAlmostEqual(wd.area_rule_fuselage_area(2.0, 0.0), 2.0, delta=1e-12)

    def test_wing_plus_pinch_recovers_target(self):
        pinch = wd.area_rule_fuselage_area(3.0, 1.2)
        self.assertAlmostEqual(pinch + 1.2, 3.0, delta=1e-12)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            wd.area_rule_fuselage_area(2.0, 2.0)  # wing fills the whole target
        with self.assertRaises(ValueError):
            wd.area_rule_fuselage_area(2.0, 2.5)  # wing exceeds the target
        with self.assertRaises(ValueError):
            wd.area_rule_fuselage_area(2.0, -0.1)
        with self.assertRaises(ValueError):
            wd.area_rule_fuselage_area(0.0, 0.0)


class AreaRuleDeviationTest(unittest.TestCase):
    def test_exact_match_zero(self):
        self.assertAlmostEqual(wd.area_rule_deviation([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]), 0.0, delta=1e-12)

    def test_constant_offset(self):
        # RMS of [2, 2, 2] = 2
        self.assertAlmostEqual(wd.area_rule_deviation([1.0, 1.0, 1.0], [3.0, 3.0, 3.0]), 2.0, delta=1e-12)

    def test_unit_ramp(self):
        # differences [1, 1, 1] -> RMS 1
        self.assertAlmostEqual(wd.area_rule_deviation([1.0, 2.0, 3.0], [2.0, 3.0, 4.0]), 1.0, delta=1e-12)

    def test_smoother_distribution_closer(self):
        rough = wd.area_rule_deviation([0.0, 1.0, 0.0], [1.0, 1.0, 1.0])
        smooth = wd.area_rule_deviation([0.8, 1.0, 0.8], [1.0, 1.0, 1.0])
        self.assertLess(smooth, rough)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            wd.area_rule_deviation([1.0], [1.0, 2.0])  # length mismatch
        with self.assertRaises(ValueError):
            wd.area_rule_deviation([], [])
        with self.assertRaises(ValueError):
            wd.area_rule_deviation([1.0, -1.0], [1.0, 1.0])
        with self.assertRaises(ValueError):
            wd.area_rule_deviation([1.0], 1.0)  # not a sequence


class DragDivergenceMachTest(unittest.TestCase):
    def test_default_margin(self):
        # M_DD = 0.72 + 0.065 = 0.785
        self.assertAlmostEqual(wd.drag_divergence_mach(0.72), 0.785, delta=1e-12)

    def test_explicit_margin(self):
        self.assertAlmostEqual(wd.drag_divergence_mach(0.72, margin=0.08), 0.80, delta=1e-12)

    def test_zero_margin_returns_critical_mach(self):
        self.assertAlmostEqual(wd.drag_divergence_mach(0.7, margin=0.0), 0.7, delta=1e-12)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            wd.drag_divergence_mach(0.0)
        with self.assertRaises(ValueError):
            wd.drag_divergence_mach(1.0)
        with self.assertRaises(ValueError):
            wd.drag_divergence_mach(-0.5)
        with self.assertRaises(ValueError):
            wd.drag_divergence_mach(0.7, margin=-0.1)
        with self.assertRaises(ValueError):
            wd.drag_divergence_mach(0.7, margin=0.2)
        # 0.95 + 0.08 reaches 1.03: out of domain
        with self.assertRaises(ValueError):
            wd.drag_divergence_mach(0.95, margin=0.08)


class WaveDragRiseCoefTest(unittest.TestCase):
    def test_parabolic_rise(self):
        # k = 30, M - M_DD = 0.05 -> 30 * 0.0025 = 0.075
        self.assertAlmostEqual(wd.wave_drag_rise_coef(0.85, 0.80, k=30.0), 0.075, delta=1e-9)

    def test_below_divergence_zero(self):
        self.assertAlmostEqual(wd.wave_drag_rise_coef(0.78, 0.80, k=30.0), 0.0, delta=1e-12)

    def test_at_divergence_zero(self):
        self.assertAlmostEqual(wd.wave_drag_rise_coef(0.80, 0.80, k=30.0), 0.0, delta=1e-12)

    def test_default_constant(self):
        # default k = 20: 20 * (0.05)^2 = 0.05
        self.assertAlmostEqual(wd.wave_drag_rise_coef(0.85, 0.80), 0.05, delta=1e-9)

    def test_rise_increases_with_mach(self):
        self.assertGreater(
            wd.wave_drag_rise_coef(0.88, 0.80, k=30.0),
            wd.wave_drag_rise_coef(0.83, 0.80, k=30.0),
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            wd.wave_drag_rise_coef(-0.1, 0.80)
        with self.assertRaises(ValueError):
            wd.wave_drag_rise_coef(1.0, 0.80)
        with self.assertRaises(ValueError):
            wd.wave_drag_rise_coef(1.2, 0.80)
        with self.assertRaises(ValueError):
            wd.wave_drag_rise_coef(0.85, 0.0)
        with self.assertRaises(ValueError):
            wd.wave_drag_rise_coef(0.85, 1.0)
        with self.assertRaises(ValueError):
            wd.wave_drag_rise_coef(0.85, 0.80, k=0.0)
        with self.assertRaises(ValueError):
            wd.wave_drag_rise_coef(0.85, 0.80, k=-5.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
