#!/usr/bin/env python3
"""Gate 3 contract test: nacelle sizing logic.

Exercises scripts/nacelle_sizing_logic.py (stdlib unittest, offline,
deterministic). Contract: docs/harness-contract.md gate 3. Covers fan
face area from mass flow and Mach, highlight area and lip area ratio,
capture area and A0/A1 ratio, nacelle length scaling (including an
extreme length to diameter ratio), cowl thickness, wetted area, nacelle
drag bookkeeping (friction, form, interference), drag coefficient, and
invalid-input edge cases (zero mass flow, non-positive Mach, bad
factors).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nacelle_sizing_logic as nacelle  # noqa: E402


class FanFaceAreaTest(unittest.TestCase):
    def test_known_fan_face_area(self):
        # 650 kg/s, 1.0 kg/m^3, M 0.6, 288.15 K
        a1 = nacelle.fan_face_area(650.0, 1.0, 0.6, 288.15)
        self.assertAlmostEqual(a1, 3.1838, places=4)

    def test_fan_face_diameter_round_trip(self):
        d1 = nacelle.fan_face_diameter(650.0, 1.0, 0.6, 288.15)
        a1 = nacelle.fan_face_area(650.0, 1.0, 0.6, 288.15)
        self.assertAlmostEqual(d1, math.sqrt(4.0 * a1 / math.pi), places=9)

    def test_zero_mass_flow_raises(self):
        with self.assertRaises(ValueError):
            nacelle.fan_face_area(0.0, 1.0, 0.6, 288.15)

    def test_non_positive_mach_raises(self):
        with self.assertRaises(ValueError):
            nacelle.fan_face_area(650.0, 1.0, 0.0, 288.15)
        with self.assertRaises(ValueError):
            nacelle.fan_face_area(650.0, 1.0, -0.3, 288.15)

    def test_non_positive_density_or_temperature_raises(self):
        with self.assertRaises(ValueError):
            nacelle.fan_face_area(650.0, 0.0, 0.6, 288.15)
        with self.assertRaises(ValueError):
            nacelle.fan_face_area(650.0, 1.0, 0.6, 0.0)

    def test_area_grows_as_mass_flow_grows(self):
        a_small = nacelle.fan_face_area(500.0, 1.0, 0.6, 288.15)
        a_large = nacelle.fan_face_area(900.0, 1.0, 0.6, 288.15)
        self.assertLess(a_small, a_large)

    def test_area_shrinks_as_mach_grows(self):
        a_m05 = nacelle.fan_face_area(650.0, 1.0, 0.5, 288.15)
        a_m08 = nacelle.fan_face_area(650.0, 1.0, 0.8, 288.15)
        self.assertGreater(a_m05, a_m08)

    def test_speed_of_sound_known_value(self):
        a = nacelle.speed_of_sound(288.15)
        self.assertAlmostEqual(a, math.sqrt(1.4 * 287.0 * 288.15), places=9)
        self.assertAlmostEqual(a, 340.263, places=3)


class HighlightTest(unittest.TestCase):
    def test_known_highlight_area_and_diameter(self):
        a_hi = nacelle.highlight_area_from_massflow(650.0, 1.0, 0.6, 288.15, 0.15)
        self.assertAlmostEqual(a_hi, 3.6614, places=4)
        d_hi = nacelle.highlight_diameter_from_massflow(650.0, 1.0, 0.6, 288.15, 0.15)
        self.assertAlmostEqual(d_hi, 2.1591, places=4)

    def test_zero_lip_ratio_gives_flush_lip(self):
        a1 = nacelle.fan_face_area(650.0, 1.0, 0.6, 288.15)
        a_hi = nacelle.highlight_area_from_massflow(650.0, 1.0, 0.6, 288.15, 0.0)
        self.assertAlmostEqual(a_hi, a1, places=9)

    def test_negative_lip_ratio_raises(self):
        with self.assertRaises(ValueError):
            nacelle.highlight_area_from_massflow(650.0, 1.0, 0.6, 288.15, -0.05)

    def test_lip_area_ratio_round_trip(self):
        a1 = nacelle.fan_face_area(650.0, 1.0, 0.6, 288.15)
        a_hi = nacelle.highlight_area_from_massflow(650.0, 1.0, 0.6, 288.15, 0.15)
        self.assertAlmostEqual(nacelle.lip_area_ratio(a_hi, a1), 0.15, places=9)

    def test_lip_area_ratio_requires_highlight_larger(self):
        with self.assertRaises(ValueError):
            nacelle.lip_area_ratio(2.0, 3.0)
        with self.assertRaises(ValueError):
            nacelle.lip_area_ratio(2.0, 2.0)

    def test_diameter_from_area_zero_raises(self):
        with self.assertRaises(ValueError):
            nacelle.diameter_from_area(0.0)


class CaptureTest(unittest.TestCase):
    def test_known_capture_area_and_ratio(self):
        a_inf = nacelle.speed_of_sound(218.81)
        v_inf = 0.8 * a_inf
        a0 = nacelle.capture_area(650.0, 0.3804, v_inf)
        self.assertAlmostEqual(a0, 7.2035, places=4)
        a1 = nacelle.fan_face_area(650.0, 1.0, 0.6, 288.15)
        ratio = nacelle.capture_area_ratio(650.0, 0.3804, v_inf, a1)
        self.assertAlmostEqual(ratio, 2.2625, places=4)
        self.assertGreater(ratio, 1.0)  # stream tube contracts into the inlet

    def test_capture_ratio_scale_free(self):
        # Doubling mass flow doubles both A0 and A1: ratio unchanged
        a1 = nacelle.fan_face_area(650.0, 1.0, 0.6, 288.15)
        r1 = nacelle.capture_area_ratio(650.0, 0.3804, 200.0, a1)
        a1b = nacelle.fan_face_area(1300.0, 1.0, 0.6, 288.15)
        r2 = nacelle.capture_area_ratio(1300.0, 0.3804, 200.0, a1b)
        self.assertAlmostEqual(r1, r2, places=9)

    def test_capture_zero_mass_flow_raises(self):
        with self.assertRaises(ValueError):
            nacelle.capture_area(0.0, 0.3804, 237.0)

    def test_capture_ratio_non_positive_fan_area_raises(self):
        with self.assertRaises(ValueError):
            nacelle.capture_area_ratio(650.0, 0.3804, 237.0, 0.0)


class NacelleLengthTest(unittest.TestCase):
    def test_known_length(self):
        d1 = nacelle.fan_face_diameter(650.0, 1.0, 0.6, 288.15)
        self.assertAlmostEqual(nacelle.nacelle_length(d1, 1.8), 3.6241, places=4)

    def test_default_ratio(self):
        self.assertAlmostEqual(nacelle.nacelle_length(2.0), 2.0 * 1.8, places=9)

    def test_extreme_length_ratio_stays_linear(self):
        # Very long slender nacelle: length scales linearly
        self.assertAlmostEqual(nacelle.nacelle_length(2.0, 10.0), 20.0, places=9)
        self.assertAlmostEqual(nacelle.nacelle_length(2.0, 0.5), 1.0, places=9)

    def test_non_positive_inputs_raise(self):
        with self.assertRaises(ValueError):
            nacelle.nacelle_length(0.0)
        with self.assertRaises(ValueError):
            nacelle.nacelle_length(2.0, -1.0)


class CowlThicknessTest(unittest.TestCase):
    def test_known_thickness(self):
        self.assertAlmostEqual(nacelle.cowl_thickness(3.6241, 0.10), 0.3624, places=4)

    def test_ratio_band(self):
        for ratio in (0.08, 0.10, 0.12):
            t = nacelle.cowl_thickness(3.0, ratio)
            self.assertAlmostEqual(t, 3.0 * ratio, places=9)

    def test_invalid_ratio_raises(self):
        with self.assertRaises(ValueError):
            nacelle.cowl_thickness(3.0, 0.0)
        with self.assertRaises(ValueError):
            nacelle.cowl_thickness(3.0, 0.6)

    def test_non_positive_chord_raises(self):
        with self.assertRaises(ValueError):
            nacelle.cowl_thickness(0.0, 0.10)


class WettedAreaTest(unittest.TestCase):
    def test_known_wetted_area(self):
        self.assertAlmostEqual(
            nacelle.wetted_area(2.1591, 3.6241, 0.85), 20.8950, places=3
        )

    def test_cylinder_shape_factor_one(self):
        self.assertAlmostEqual(
            nacelle.wetted_area(2.0, 3.0, 1.0), math.pi * 2.0 * 3.0, places=9
        )

    def test_invalid_shape_factor_raises(self):
        with self.assertRaises(ValueError):
            nacelle.wetted_area(2.0, 3.0, 0.0)
        with self.assertRaises(ValueError):
            nacelle.wetted_area(2.0, 3.0, 1.5)

    def test_non_positive_dimensions_raise(self):
        with self.assertRaises(ValueError):
            nacelle.wetted_area(0.0, 3.0)
        with self.assertRaises(ValueError):
            nacelle.wetted_area(2.0, 0.0)


class DragBookkeepingTest(unittest.TestCase):
    def test_known_components(self):
        b = nacelle.nacelle_drag_bookkeeping(10702.07, 20.8953, 0.0025)
        self.assertAlmostEqual(b["friction_drag"], 559.06, places=2)
        self.assertAlmostEqual(b["form_drag"], 111.81, places=2)
        self.assertAlmostEqual(b["interference_drag"], 27.95, places=2)
        self.assertAlmostEqual(b["total_drag"], 698.82, places=2)

    def test_components_sum_to_total(self):
        b = nacelle.nacelle_drag_bookkeeping(10702.07, 20.8953, 0.0025)
        self.assertAlmostEqual(
            b["total_drag"],
            b["friction_drag"] + b["form_drag"] + b["interference_drag"],
            places=9,
        )

    def test_unit_form_factor_and_zero_interference(self):
        b = nacelle.nacelle_drag_bookkeeping(
            10702.07, 20.8953, 0.0025, form_factor=1.0, interference_factor=0.0
        )
        self.assertAlmostEqual(b["form_drag"], 0.0, places=9)
        self.assertAlmostEqual(b["interference_drag"], 0.0, places=9)
        self.assertAlmostEqual(
            b["total_drag"], b["friction_drag"], places=9
        )

    def test_drag_scales_with_dynamic_pressure(self):
        b1 = nacelle.nacelle_drag_bookkeeping(1000.0, 20.0, 0.0025)
        b2 = nacelle.nacelle_drag_bookkeeping(2000.0, 20.0, 0.0025)
        self.assertAlmostEqual(b2["total_drag"], 2.0 * b1["total_drag"], places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nacelle.nacelle_drag_bookkeeping(0.0, 20.0, 0.0025)
        with self.assertRaises(ValueError):
            nacelle.nacelle_drag_bookkeeping(1000.0, 0.0, 0.0025)
        with self.assertRaises(ValueError):
            nacelle.nacelle_drag_bookkeeping(1000.0, 20.0, 0.0)
        with self.assertRaises(ValueError):
            nacelle.nacelle_drag_bookkeeping(1000.0, 20.0, 0.0025, form_factor=0.9)
        with self.assertRaises(ValueError):
            nacelle.nacelle_drag_bookkeeping(
                1000.0, 20.0, 0.0025, interference_factor=-0.1
            )

    def test_known_drag_coefficient(self):
        cd = nacelle.drag_coefficient(698.82, 10702.07, 122.6)
        self.assertAlmostEqual(cd, 0.000533, places=6)

    def test_drag_coefficient_invalid_raises(self):
        with self.assertRaises(ValueError):
            nacelle.drag_coefficient(698.82, 0.0, 122.6)
        with self.assertRaises(ValueError):
            nacelle.drag_coefficient(698.82, 10702.07, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
