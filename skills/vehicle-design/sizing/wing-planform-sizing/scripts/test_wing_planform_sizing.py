#!/usr/bin/env python3
"""Gate 3 contract test: wing planform sizing.

Exercises scripts/wing_planform_sizing_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - wing area from
wing loading and takeoff gross weight, aspect ratio and span, taper
ratio with root and tip chord, mean aerodynamic chord with its
spanwise station, and the sweep angle from the cruise Mach; invalid
inputs raise ValueError. Units: forces in N, areas in m^2, wing
loading in N/m^2, spans and chords in m, Mach unitless, sweep in
degrees.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wing_planform_sizing_logic as wpsl  # noqa: E402


class WingAreaTest(unittest.TestCase):
    def test_analytic_wing_area(self):
        # 480000 / 6000 = 80.0 m^2
        self.assertAlmostEqual(wpsl.wing_area_from_wing_loading(480000.0, 6000.0), 80.0, places=6)

    def test_higher_wing_loading_reduces_area(self):
        self.assertGreater(
            wpsl.wing_area_from_wing_loading(480000.0, 5000.0),
            wpsl.wing_area_from_wing_loading(480000.0, 6000.0),
        )

    def test_round_trip_with_wing_loading(self):
        area = wpsl.wing_area_from_wing_loading(480000.0, 6000.0)
        self.assertAlmostEqual(wpsl.wing_loading_from_area(480000.0, area), 6000.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wpsl.wing_area_from_wing_loading(0, 6000.0)
        with self.assertRaises(ValueError):
            wpsl.wing_area_from_wing_loading(-480000.0, 6000.0)
        with self.assertRaises(ValueError):
            wpsl.wing_area_from_wing_loading(480000.0, 0)
        with self.assertRaises(ValueError):
            wpsl.wing_loading_from_area(480000.0, -80.0)


class SpanAspectRatioTest(unittest.TestCase):
    def test_analytic_span(self):
        # sqrt(9 * 80) = sqrt(720) = 26.8328 m
        self.assertAlmostEqual(wpsl.span_from_aspect_ratio(80.0, 9.0), 26.8328, places=4)

    def test_higher_aspect_ratio_increases_span(self):
        self.assertGreater(
            wpsl.span_from_aspect_ratio(80.0, 10.0),
            wpsl.span_from_aspect_ratio(80.0, 9.0),
        )

    def test_round_trip_aspect_ratio(self):
        span = wpsl.span_from_aspect_ratio(80.0, 9.0)
        self.assertAlmostEqual(wpsl.aspect_ratio_from_span(span, 80.0), 9.0, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wpsl.span_from_aspect_ratio(0, 9.0)
        with self.assertRaises(ValueError):
            wpsl.span_from_aspect_ratio(80.0, 0)
        with self.assertRaises(ValueError):
            wpsl.aspect_ratio_from_span(26.8, -80.0)


class TaperChordTest(unittest.TestCase):
    def test_analytic_taper_ratio(self):
        # 1.5 / 5.0 = 0.3
        self.assertAlmostEqual(wpsl.taper_ratio_from_chords(5.0, 1.5), 0.3, places=6)

    def test_reverse_taper_raises(self):
        with self.assertRaises(ValueError):
            wpsl.taper_ratio_from_chords(5.0, 6.0)

    def test_analytic_root_chord(self):
        # 2 * 80 / (26.8328 * 1.3) = 4.5868 m
        span = wpsl.span_from_aspect_ratio(80.0, 9.0)
        self.assertAlmostEqual(wpsl.root_chord_from_taper(80.0, span, 0.3), 4.5868, places=4)

    def test_analytic_tip_chord(self):
        # 0.3 * 4.5868 = 1.3760 m
        self.assertAlmostEqual(wpsl.tip_chord_from_taper(4.5868, 0.3), 1.3760, places=4)

    def test_rectangular_planform_equal_chords(self):
        span = wpsl.span_from_aspect_ratio(80.0, 9.0)
        root = wpsl.root_chord_from_taper(80.0, span, 1.0)
        self.assertAlmostEqual(wpsl.tip_chord_from_taper(root, 1.0), root, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wpsl.root_chord_from_taper(0, 26.8, 0.3)
        with self.assertRaises(ValueError):
            wpsl.root_chord_from_taper(80.0, 26.8, 0)
        with self.assertRaises(ValueError):
            wpsl.root_chord_from_taper(80.0, 26.8, 1.5)
        with self.assertRaises(ValueError):
            wpsl.tip_chord_from_taper(4.6, -0.3)


class MacTest(unittest.TestCase):
    def test_analytic_mac(self):
        # (4*80/(3*26.8328)) * (1.39 / 1.69) = 3.2696 m
        span = wpsl.span_from_aspect_ratio(80.0, 9.0)
        self.assertAlmostEqual(wpsl.mean_aerodynamic_chord(80.0, span, 0.3), 3.2696, places=4)

    def test_mac_is_fraction_of_root_chord(self):
        span = wpsl.span_from_aspect_ratio(80.0, 9.0)
        root = wpsl.root_chord_from_taper(80.0, span, 0.3)
        mac = wpsl.mean_aerodynamic_chord(80.0, span, 0.3)
        self.assertLess(mac, root)
        self.assertGreater(mac, 0.5 * root)

    def test_lower_taper_increases_mac(self):
        # fixed area and span: a more tapered planform has a longer MAC
        span = wpsl.span_from_aspect_ratio(80.0, 9.0)
        self.assertGreater(
            wpsl.mean_aerodynamic_chord(80.0, span, 0.3),
            wpsl.mean_aerodynamic_chord(80.0, span, 0.6),
        )

    def test_analytic_mac_station(self):
        # (26.8328 / 6) * (1.6 / 1.3) = 5.5042 m
        span = wpsl.span_from_aspect_ratio(80.0, 9.0)
        self.assertAlmostEqual(wpsl.mac_spanwise_station(span, 0.3), 5.5042, places=4)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wpsl.mean_aerodynamic_chord(0, 26.8, 0.3)
        with self.assertRaises(ValueError):
            wpsl.mean_aerodynamic_chord(80.0, 0, 0.3)
        with self.assertRaises(ValueError):
            wpsl.mac_spanwise_station(26.8, 1.2)


class SweepTest(unittest.TestCase):
    def test_analytic_sweep(self):
        # arccos(0.7 / 0.8) = arccos(0.875) = 28.955 degrees
        self.assertAlmostEqual(wpsl.sweep_angle_from_cruise_mach(0.8, 0.7), 28.955, places=3)

    def test_higher_cruise_mach_increases_sweep(self):
        self.assertGreater(
            wpsl.sweep_angle_from_cruise_mach(0.85, 0.7),
            wpsl.sweep_angle_from_cruise_mach(0.8, 0.7),
        )

    def test_no_sweep_needed_below_section_critical(self):
        self.assertEqual(wpsl.sweep_angle_from_cruise_mach(0.6, 0.7), 0.0)

    def test_normal_mach_consistency(self):
        # M * cos(Lambda) with the selected sweep returns the section critical Mach
        sweep = wpsl.sweep_angle_from_cruise_mach(0.8, 0.7)
        self.assertAlmostEqual(wpsl.mach_normal_component(0.8, sweep), 0.7, places=9)

    def test_zero_sweep_leaves_mach_unchanged(self):
        self.assertAlmostEqual(wpsl.mach_normal_component(0.8, 0.0), 0.8, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wpsl.sweep_angle_from_cruise_mach(0, 0.7)
        with self.assertRaises(ValueError):
            wpsl.sweep_angle_from_cruise_mach(1.0, 0.7)
        with self.assertRaises(ValueError):
            wpsl.sweep_angle_from_cruise_mach(0.8, 0)
        with self.assertRaises(ValueError):
            wpsl.mach_normal_component(0.8, -5.0)
        with self.assertRaises(ValueError):
            wpsl.mach_normal_component(0.8, 95.0)


class PlanformGeometryTest(unittest.TestCase):
    def test_full_summary_analytic(self):
        result = wpsl.planform_geometry(80.0, 9.0, 0.3)
        self.assertAlmostEqual(result["span"], 26.8328, places=4)
        self.assertAlmostEqual(result["root_chord"], 4.5868, places=4)
        self.assertAlmostEqual(result["tip_chord"], 1.3760, places=4)
        self.assertAlmostEqual(result["mac"], 3.2696, places=4)
        self.assertAlmostEqual(result["mac_station"], 5.5042, places=4)

    def test_consistency_with_component_functions(self):
        result = wpsl.planform_geometry(80.0, 9.0, 0.3)
        self.assertAlmostEqual(result["span"], wpsl.span_from_aspect_ratio(80.0, 9.0), places=9)
        self.assertAlmostEqual(
            result["mac"], wpsl.mean_aerodynamic_chord(80.0, result["span"], 0.3), places=9
        )
        self.assertAlmostEqual(
            result["tip_chord"], result["root_chord"] * 0.3, places=9
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wpsl.planform_geometry(0, 9.0, 0.3)
        with self.assertRaises(ValueError):
            wpsl.planform_geometry(80.0, 0, 0.3)
        with self.assertRaises(ValueError):
            wpsl.planform_geometry(80.0, 9.0, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
