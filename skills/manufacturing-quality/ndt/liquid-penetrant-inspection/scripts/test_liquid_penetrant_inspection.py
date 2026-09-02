#!/usr/bin/env python3
"""Gate 3 contract test: liquid penetrant inspection.

Exercises scripts/liquid_penetrant_inspection_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (capillary pressure
and rise, Washburn penetration depth during the dwell time, dwell time
sizing for a crack of given width and depth, penetration rate, crack
width to capillary radius conversion, bleed-out indication sizing,
developer coverage mass, contrast ratio; invalid inputs raise
ValueError).

Anchors:
- capillary_pressure(0.032, 5, 1e-6) = 63756.5 Pa (typical penetrant
  in a 1 micron crack)
- capillary_rise_height(0.0728, 0, 1000, 2.5e-4) = 0.0594 m (water in a
  0.5 mm tube, about 5.9 cm)
- washburn_penetration_depth(0.032, 5, 0.008, 1e-6, 300) = 0.0244 m
  (24.4 mm in a 5 minute dwell)
- dwell_time_for_depth roundtrips with washburn_penetration_depth
- penetration_rate(0.032, 5, 0.008, 1e-6, 0.01) = 9.962e-5 m/s
- crack_radius_from_width(2e-6) = 1e-6 (slit radius is half the width)
- bleed_out_width(1e-5, 5.0) = 5e-5 and bleed_out_ratio(5e-5, 1e-5) = 5
- developer_coverage_mass(1.0, 0.15) = 0.15 kg
- contrast_ratio(0.8, 0.05) = 0.9375
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import liquid_penetrant_inspection_logic as pt  # noqa: E402


class CapillaryPressureTest(unittest.TestCase):
    def test_anchor_typical_penetrant_one_micron(self):
        self.assertAlmostEqual(
            pt.capillary_pressure(0.032, 5, 1e-6), 63756.46, places=2
        )

    def test_anchor_zero_contact_angle(self):
        self.assertAlmostEqual(pt.capillary_pressure(0.032, 0, 1e-6), 64000.0)

    def test_tighter_crack_higher_pressure(self):
        tight = pt.capillary_pressure(0.032, 5, 5e-7)
        wide = pt.capillary_pressure(0.032, 5, 1e-6)
        self.assertGreater(tight, wide)
        self.assertAlmostEqual(tight, 2.0 * wide, places=6)

    def test_larger_contact_angle_lower_pressure(self):
        steep = pt.capillary_pressure(0.032, 60, 1e-6)
        flat = pt.capillary_pressure(0.032, 5, 1e-6)
        self.assertLess(steep, flat)

    def test_non_wetting_angle_raises(self):
        with self.assertRaises(ValueError):
            pt.capillary_pressure(0.032, 90, 1e-6)
        with self.assertRaises(ValueError):
            pt.capillary_pressure(0.032, 120, 1e-6)
        with self.assertRaises(ValueError):
            pt.capillary_pressure(0.032, -5, 1e-6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pt.capillary_pressure(0, 5, 1e-6)
        with self.assertRaises(ValueError):
            pt.capillary_pressure(0.032, 5, 0)
        with self.assertRaises(ValueError):
            pt.capillary_pressure(-0.032, 5, 1e-6)


class CapillaryRiseHeightTest(unittest.TestCase):
    def test_anchor_water_half_mm_tube(self):
        self.assertAlmostEqual(
            pt.capillary_rise_height(0.0728, 0, 1000, 2.5e-4), 0.0594, places=4
        )

    def test_denser_fluid_lower_rise(self):
        water = pt.capillary_rise_height(0.0728, 0, 1000, 2.5e-4)
        mercury = pt.capillary_rise_height(0.0728, 0, 13546, 2.5e-4)
        self.assertLess(mercury, water)

    def test_wider_tube_lower_rise(self):
        narrow = pt.capillary_rise_height(0.0728, 0, 1000, 1e-4)
        wide = pt.capillary_rise_height(0.0728, 0, 1000, 2.5e-4)
        self.assertGreater(narrow, wide)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pt.capillary_rise_height(0, 0, 1000, 2.5e-4)
        with self.assertRaises(ValueError):
            pt.capillary_rise_height(0.0728, 0, 0, 2.5e-4)
        with self.assertRaises(ValueError):
            pt.capillary_rise_height(0.0728, 0, 1000, 0)
        with self.assertRaises(ValueError):
            pt.capillary_rise_height(0.0728, 0, 1000, 2.5e-4, gravity=0)
        with self.assertRaises(ValueError):
            pt.capillary_rise_height(0.0728, 95, 1000, 2.5e-4)


class WashburnDepthTest(unittest.TestCase):
    def test_anchor_five_minute_dwell(self):
        self.assertAlmostEqual(
            pt.washburn_penetration_depth(0.032, 5, 0.008, 1e-6, 300),
            0.0244,
            places=4,
        )

    def test_sqrt_time_scaling(self):
        one = pt.washburn_penetration_depth(0.032, 5, 0.008, 1e-6, 100)
        four = pt.washburn_penetration_depth(0.032, 5, 0.008, 1e-6, 400)
        self.assertAlmostEqual(four, 2.0 * one, places=6)

    def test_zero_time_zero_depth(self):
        self.assertAlmostEqual(
            pt.washburn_penetration_depth(0.032, 5, 0.008, 1e-6, 0), 0.0
        )

    def test_higher_viscosity_shallower(self):
        thin = pt.washburn_penetration_depth(0.032, 5, 0.008, 1e-6, 300)
        thick = pt.washburn_penetration_depth(0.032, 5, 0.016, 1e-6, 300)
        self.assertLess(thick, thin)
        self.assertAlmostEqual(thick, thin / math.sqrt(2.0), places=6)

    def test_tighter_radius_shallower(self):
        wide = pt.washburn_penetration_depth(0.032, 5, 0.008, 2e-6, 300)
        tight = pt.washburn_penetration_depth(0.032, 5, 0.008, 1e-6, 300)
        self.assertGreater(wide, tight)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pt.washburn_penetration_depth(0, 5, 0.008, 1e-6, 300)
        with self.assertRaises(ValueError):
            pt.washburn_penetration_depth(0.032, 5, 0, 1e-6, 300)
        with self.assertRaises(ValueError):
            pt.washburn_penetration_depth(0.032, 5, 0.008, 0, 300)
        with self.assertRaises(ValueError):
            pt.washburn_penetration_depth(0.032, 5, 0.008, 1e-6, -1)
        with self.assertRaises(ValueError):
            pt.washburn_penetration_depth(0.032, 100, 0.008, 1e-6, 300)


class DwellTimeTest(unittest.TestCase):
    def test_roundtrip_with_washburn(self):
        depth = pt.washburn_penetration_depth(0.032, 5, 0.008, 1e-6, 300)
        t = pt.dwell_time_for_depth(depth, 0.032, 5, 0.008, 1e-6)
        self.assertAlmostEqual(t, 300.0, places=6)

    def test_dwell_scales_with_depth_squared(self):
        one = pt.dwell_time_for_depth(1e-3, 0.032, 5, 0.008, 1e-6)
        two = pt.dwell_time_for_depth(2e-3, 0.032, 5, 0.008, 1e-6)
        self.assertAlmostEqual(two, 4.0 * one, places=6)

    def test_tighter_crack_longer_dwell(self):
        wide = pt.dwell_time_for_depth(1e-3, 0.032, 5, 0.008, 2e-6)
        tight = pt.dwell_time_for_depth(1e-3, 0.032, 5, 0.008, 1e-6)
        self.assertGreater(tight, wide)
        self.assertAlmostEqual(tight, 2.0 * wide, places=6)

    def test_thicker_penetrant_longer_dwell(self):
        thin = pt.dwell_time_for_depth(1e-3, 0.032, 5, 0.008, 1e-6)
        thick = pt.dwell_time_for_depth(1e-3, 0.032, 5, 0.016, 1e-6)
        self.assertAlmostEqual(thick, 2.0 * thin, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pt.dwell_time_for_depth(0, 0.032, 5, 0.008, 1e-6)
        with self.assertRaises(ValueError):
            pt.dwell_time_for_depth(1e-3, 0.032, 5, 0, 1e-6)
        with self.assertRaises(ValueError):
            pt.dwell_time_for_depth(1e-3, 0.032, 5, 0.008, 0)
        with self.assertRaises(ValueError):
            pt.dwell_time_for_depth(1e-3, 0.032, 90, 0.008, 1e-6)


class PenetrationRateTest(unittest.TestCase):
    def test_anchor_rate_at_ten_mm(self):
        self.assertAlmostEqual(
            pt.penetration_rate(0.032, 5, 0.008, 1e-6, 0.01),
            9.962e-5,
            places=8,
        )

    def test_deeper_front_slower(self):
        shallow = pt.penetration_rate(0.032, 5, 0.008, 1e-6, 0.01)
        deep = pt.penetration_rate(0.032, 5, 0.008, 1e-6, 0.02)
        self.assertAlmostEqual(deep, shallow / 2.0, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pt.penetration_rate(0.032, 5, 0.008, 1e-6, 0)
        with self.assertRaises(ValueError):
            pt.penetration_rate(0.032, 5, 0.008, 1e-6, -0.01)
        with self.assertRaises(ValueError):
            pt.penetration_rate(0, 5, 0.008, 1e-6, 0.01)


class CrackRadiusTest(unittest.TestCase):
    def test_anchor_slit_half_width(self):
        self.assertAlmostEqual(pt.crack_radius_from_width(2e-6), 1e-6)

    def test_linear_in_width(self):
        self.assertAlmostEqual(
            pt.crack_radius_from_width(5e-6), 2.5e-6
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pt.crack_radius_from_width(0)
        with self.assertRaises(ValueError):
            pt.crack_radius_from_width(-1e-6)


class BleedOutTest(unittest.TestCase):
    def test_anchor_bleed_out_width(self):
        self.assertAlmostEqual(pt.bleed_out_width(1e-5, 5.0), 5e-5)

    def test_anchor_bleed_out_ratio(self):
        self.assertAlmostEqual(pt.bleed_out_ratio(5e-5, 1e-5), 5.0)

    def test_ratio_unity_when_equal(self):
        self.assertAlmostEqual(pt.bleed_out_ratio(2e-5, 2e-5), 1.0)

    def test_typical_tight_crack_ratio_between_three_and_five(self):
        ind = pt.bleed_out_width(1e-5, 4.0)
        ratio = pt.bleed_out_ratio(ind, 1e-5)
        self.assertGreaterEqual(ratio, 3.0)
        self.assertLessEqual(ratio, 5.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pt.bleed_out_width(0, 5.0)
        with self.assertRaises(ValueError):
            pt.bleed_out_width(1e-5, 0)
        with self.assertRaises(ValueError):
            pt.bleed_out_ratio(0, 1e-5)
        with self.assertRaises(ValueError):
            pt.bleed_out_ratio(5e-5, 0)


class DeveloperCoverageTest(unittest.TestCase):
    def test_anchor_one_square_meter(self):
        self.assertAlmostEqual(pt.developer_coverage_mass(1.0, 0.15), 0.15)

    def test_area_scaling(self):
        small = pt.developer_coverage_mass(0.5, 0.15)
        large = pt.developer_coverage_mass(1.0, 0.15)
        self.assertAlmostEqual(large, 2.0 * small, places=9)

    def test_zero_area_zero_mass(self):
        self.assertAlmostEqual(pt.developer_coverage_mass(0.0, 0.15), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pt.developer_coverage_mass(-1.0, 0.15)
        with self.assertRaises(ValueError):
            pt.developer_coverage_mass(1.0, 0)


class ContrastRatioTest(unittest.TestCase):
    def test_anchor_fluorescent_contrast(self):
        self.assertAlmostEqual(pt.contrast_ratio(0.8, 0.05), 0.9375)

    def test_darker_indication_against_white_developer(self):
        self.assertAlmostEqual(pt.contrast_ratio(0.9, 0.1), 0.8889, places=4)

    def test_similar_reflectances_low_contrast(self):
        self.assertAlmostEqual(pt.contrast_ratio(0.5, 0.45), 0.1)

    def test_symmetric_in_argument_order(self):
        a = pt.contrast_ratio(0.8, 0.05)
        b = pt.contrast_ratio(0.05, 0.8)
        self.assertAlmostEqual(a, b, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pt.contrast_ratio(0, 0.05)
        with self.assertRaises(ValueError):
            pt.contrast_ratio(0.8, -0.1)


class PenetrantScenarioTest(unittest.TestCase):
    def test_tight_crack_needs_longer_dwell(self):
        # A fatigue crack with a 0.5 micron effective radius needs twice
        # the dwell time of a 1 micron crack at the same depth, since
        # dwell time scales inversely with the capillary radius.
        tight = pt.dwell_time_for_depth(2e-3, 0.032, 5, 0.008, 5e-7)
        open_crack = pt.dwell_time_for_depth(2e-3, 0.032, 5, 0.008, 1e-6)
        self.assertAlmostEqual(tight, 2.0 * open_crack, places=6)

    def test_five_minute_dwell_fills_two_mm_crack(self):
        # A 2 mm deep crack of 1 micron effective radius fills in under
        # 40 seconds with a low-viscosity penetrant; the 5 minute
        # standard dwell is a large margin for this geometry.
        t = pt.dwell_time_for_depth(2e-3, 0.032, 5, 0.008, 1e-6)
        self.assertLess(t, 40.0)
        depth = pt.washburn_penetration_depth(0.032, 5, 0.008, 1e-6, 300)
        self.assertGreater(depth, 2e-3)

    def test_bleed_out_sizing_from_measured_indication(self):
        # A 15 micron wide indication with a 4x bleed-out factor
        # implies a flaw opening of about 3.75 microns.
        flaw = 15e-6 / 4.0
        self.assertAlmostEqual(pt.bleed_out_width(flaw, 4.0), 15e-6)
        self.assertAlmostEqual(pt.bleed_out_ratio(15e-6, flaw), 4.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
