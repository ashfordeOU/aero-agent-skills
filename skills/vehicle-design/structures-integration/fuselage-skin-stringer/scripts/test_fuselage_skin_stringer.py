#!/usr/bin/env python3
"""Gate 3 contract test: pressurized fuselage skin-stringer panel.

Exercises scripts/fuselage_skin_stringer_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (hoop and
longitudinal membrane stresses from the cabin differential pressure
and radius; skin thickness from the governing hoop stress with the
1.5 factor of safety and the minimum gauge; stringer spacing from the
flat panel buckling allowable; frame pitch from the stringer column
buckling length; effective skin width; stringer area from the
compression strip load; invalid inputs raise ValueError.

Anchors:
- hoop_stress(100000, 2.0, 0.002) = 1.0e8 Pa (100 MPa)
- longitudinal_stress(100000, 2.0, 0.002) = 5.0e7 Pa (50 MPa)
- skin_thickness(100000, 2.0, 200e6, 1.5, 0.001) = 0.0015 m
  (hoop governs; t_long term is 0.00075 m)
- skin_thickness(40000, 1.0, 300e6, 1.5, 0.0012) = 0.0012 m
  (minimum gauge governs)
- stringer_spacing(0.0015, 70e9, 150e6) = 0.0616117 m
- frame_pitch(2e-4, 2e-8, 70e9, 200e6) = 0.5877382 m
- effective_skin_width(0.0015, 70e9, 250e6) = 0.0476896 m
- stringer_area(50000, 0.0476896, 0.0015, 250e6) = 1.28466e-4 m^2
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fuselage_skin_stringer_logic as fss  # noqa: E402


class HoopStressTest(unittest.TestCase):
    def test_anchor_hoop(self):
        self.assertAlmostEqual(fss.hoop_stress(100000, 2.0, 0.002), 1.0e8)

    def test_half_thickness_doubles_stress(self):
        self.assertAlmostEqual(fss.hoop_stress(100000, 2.0, 0.001), 2.0e8)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fss.hoop_stress(0, 2.0, 0.002)
        with self.assertRaises(ValueError):
            fss.hoop_stress(-100000, 2.0, 0.002)
        with self.assertRaises(ValueError):
            fss.hoop_stress(100000, 0, 0.002)
        with self.assertRaises(ValueError):
            fss.hoop_stress(100000, 2.0, -0.002)


class LongitudinalStressTest(unittest.TestCase):
    def test_anchor_longitudinal(self):
        self.assertAlmostEqual(
            fss.longitudinal_stress(100000, 2.0, 0.002), 5.0e7
        )

    def test_half_of_hoop(self):
        hoop = fss.hoop_stress(100000, 2.0, 0.002)
        longi = fss.longitudinal_stress(100000, 2.0, 0.002)
        self.assertAlmostEqual(longi, hoop / 2.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fss.longitudinal_stress(0, 2.0, 0.002)
        with self.assertRaises(ValueError):
            fss.longitudinal_stress(100000, 0, 0.002)
        with self.assertRaises(ValueError):
            fss.longitudinal_stress(100000, 2.0, 0)


class SkinThicknessTest(unittest.TestCase):
    def test_anchor_hoop_governs(self):
        # t_hoop = 100000 * 2.0 * 1.5 / 200e6 = 0.0015 m; the
        # longitudinal term is 0.00075 m and the gauge is 0.001 m.
        self.assertAlmostEqual(
            fss.skin_thickness(100000, 2.0, 200e6, 1.5, 0.001), 0.0015
        )

    def test_minimum_gauge_governs(self):
        # t_hoop = 40000 * 1.0 * 1.5 / 300e6 = 0.0002 m, below the
        # 0.0012 m minimum gauge.
        self.assertAlmostEqual(
            fss.skin_thickness(40000, 1.0, 300e6, 1.5, 0.0012), 0.0012
        )

    def test_custom_factor_of_safety(self):
        self.assertAlmostEqual(
            fss.skin_thickness(100000, 2.0, 200e6, 2.0, 0.001), 0.002
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fss.skin_thickness(0, 2.0, 200e6)
        with self.assertRaises(ValueError):
            fss.skin_thickness(100000, 2.0, 0)
        with self.assertRaises(ValueError):
            fss.skin_thickness(100000, 2.0, 200e6, 0.9)
        with self.assertRaises(ValueError):
            fss.skin_thickness(100000, 2.0, 200e6, 1.5, 0)


class StringerSpacingTest(unittest.TestCase):
    def test_anchor_spacing(self):
        self.assertAlmostEqual(
            fss.stringer_spacing(0.0015, 70e9, 150e6), 0.0616117, places=6
        )

    def test_spacing_scales_with_thickness(self):
        self.assertAlmostEqual(
            fss.stringer_spacing(0.002, 70e9, 150e6), 0.0821489, places=6
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fss.stringer_spacing(0, 70e9, 150e6)
        with self.assertRaises(ValueError):
            fss.stringer_spacing(0.0015, 0, 150e6)
        with self.assertRaises(ValueError):
            fss.stringer_spacing(0.0015, 70e9, -150e6)
        with self.assertRaises(ValueError):
            fss.stringer_spacing(0.0015, 70e9, 150e6, k=0)
        with self.assertRaises(ValueError):
            fss.stringer_spacing(0.0015, 70e9, 150e6, poisson=0.6)
        with self.assertRaises(ValueError):
            fss.stringer_spacing(0.0015, 70e9, 150e6, poisson=0.0)


class FramePitchTest(unittest.TestCase):
    def test_anchor_frame_pitch(self):
        self.assertAlmostEqual(
            fss.frame_pitch(2e-4, 2e-8, 70e9, 200e6), 0.5877382, places=6
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fss.frame_pitch(0, 2e-8, 70e9, 200e6)
        with self.assertRaises(ValueError):
            fss.frame_pitch(2e-4, 0, 70e9, 200e6)
        with self.assertRaises(ValueError):
            fss.frame_pitch(2e-4, 2e-8, 70e9, 0)


class EffectiveSkinWidthTest(unittest.TestCase):
    def test_anchor_effective_width(self):
        self.assertAlmostEqual(
            fss.effective_skin_width(0.0015, 70e9, 250e6), 0.0476896, places=6
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fss.effective_skin_width(0, 70e9, 250e6)
        with self.assertRaises(ValueError):
            fss.effective_skin_width(0.0015, 0, 250e6)
        with self.assertRaises(ValueError):
            fss.effective_skin_width(0.0015, 70e9, 0)


class StringerAreaTest(unittest.TestCase):
    def test_anchor_stringer_area(self):
        # A = 50000 / 250e6 - 0.0476896 * 0.0015 = 1.28466e-4 m^2.
        self.assertAlmostEqual(
            fss.stringer_area(50000, 0.0476896, 0.0015, 250e6),
            1.28466e-4,
            places=9,
        )

    def test_skin_alone_raises(self):
        # 10000 N strip: the effective skin alone carries it, so no
        # stringer area is required and the sizing raises.
        with self.assertRaises(ValueError):
            fss.stringer_area(10000, 0.0476896, 0.0015, 250e6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            fss.stringer_area(0, 0.0476896, 0.0015, 250e6)
        with self.assertRaises(ValueError):
            fss.stringer_area(50000, 0, 0.0015, 250e6)
        with self.assertRaises(ValueError):
            fss.stringer_area(50000, 0.0476896, 0.0015, 0)


class PressurizedFuselageScenarioTest(unittest.TestCase):
    def test_skin_thickness_min_gauge(self):
        # 0.55 bar differential at 1.98 m radius, 250 MPa allowable:
        # t_hoop = 55000 * 1.98 * 1.5 / 250e6 = 0.0006534 m, so the
        # 1.2 mm minimum gauge governs.
        self.assertAlmostEqual(
            fss.skin_thickness(55000, 1.98, 250e6, 1.5, 0.0012), 0.0012
        )

    def test_hoop_stress_of_sized_skin(self):
        # Limit hoop stress of the 1.2 mm skin at 0.55 bar:
        # 55000 * 1.98 / 0.0012 = 90.75 MPa.
        self.assertAlmostEqual(
            fss.hoop_stress(55000, 1.98, 0.0012), 9.075e7
        )

    def test_stringer_spacing_scenario(self):
        self.assertAlmostEqual(
            fss.stringer_spacing(0.0012, 70e9, 120e6), 0.0551072, places=6
        )

    def test_frame_pitch_scenario(self):
        self.assertAlmostEqual(
            fss.frame_pitch(1.5e-4, 1.5e-8, 70e9, 250e6), 0.5256890, places=6
        )

    def test_stringer_area_scenario(self):
        width = fss.effective_skin_width(0.0012, 70e9, 250e6)
        self.assertAlmostEqual(width, 0.0381517, places=6)
        self.assertAlmostEqual(
            fss.stringer_area(60000, width, 0.0012, 250e6),
            1.94218e-4,
            places=9,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
