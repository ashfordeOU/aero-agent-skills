#!/usr/bin/env python3
"""Gate 3 contract test: visual inspection (VT).

Exercises scripts/visual_inspection_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (aperture ratio, eye
resolution limit and magnification for a target indication size,
illuminance by the inverse-square law with lux to foot-candle
conversion, borescope field of view, scan positions for surface
coverage, and acceptance verdicts against the indication acceptance
criteria; invalid inputs raise ValueError).

Anchors:
- aperture_ratio(6e-3, 100e-3) = 0.06 (6 mm objective at 100 mm)
- eye_resolvable_size(0.3) = 8.727e-5 m (1 arcmin at 300 mm)
- resolvable_size(10, 0.25) = 7.272e-6 m (10x at the 250 mm near point)
- magnification_for_resolution(25e-6, 0.25) = 2.909x
- illuminance_from_intensity(250, 0.5) = 1000 lux (inverse-square)
- intensity_for_illuminance(1000, 0.5) = 250 cd
- distance_for_illuminance(250, 1000) = 0.5 m
- foot_candles_to_lux(100) = 1076.391 lux
- field_of_view(0.05, 40) = 3.6397e-2 m (40 deg field at 50 mm)
- scan_positions(0.01, 1.6e-3, 0.2) = 8 positions
- acceptance_verdict(1.2e-3, 1e-3) = False, acceptance_verdict(0.8e-3, 1e-3) = True
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import visual_inspection_logic as vt  # noqa: E402


class ApertureRatioTest(unittest.TestCase):
    def test_anchor_six_mm_at_hundred_mm(self):
        self.assertAlmostEqual(vt.aperture_ratio(6e-3, 100e-3), 0.06)

    def test_higher_ratio_with_larger_aperture(self):
        small = vt.aperture_ratio(3e-3, 100e-3)
        large = vt.aperture_ratio(6e-3, 100e-3)
        self.assertAlmostEqual(large, 2.0 * small, places=9)

    def test_lower_ratio_with_longer_working_distance(self):
        near = vt.aperture_ratio(6e-3, 100e-3)
        far = vt.aperture_ratio(6e-3, 200e-3)
        self.assertLess(far, near)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vt.aperture_ratio(0, 100e-3)
        with self.assertRaises(ValueError):
            vt.aperture_ratio(6e-3, 0)
        with self.assertRaises(ValueError):
            vt.aperture_ratio(-6e-3, 100e-3)


class EyeResolutionTest(unittest.TestCase):
    def test_anchor_three_hundred_mm(self):
        self.assertAlmostEqual(vt.eye_resolvable_size(0.3), 8.727e-5, places=8)

    def test_anchor_near_point_250_mm(self):
        self.assertAlmostEqual(vt.eye_resolvable_size(0.25), 7.272e-5, places=8)

    def test_closer_viewing_resolves_finer(self):
        near = vt.eye_resolvable_size(0.25)
        far = vt.eye_resolvable_size(0.5)
        self.assertLess(near, far)
        self.assertAlmostEqual(far, 2.0 * near, places=9)

    def test_sharper_acuity_resolves_finer(self):
        standard = vt.eye_resolvable_size(0.3, eye_angle_arcmin=1.0)
        sharp = vt.eye_resolvable_size(0.3, eye_angle_arcmin=0.5)
        self.assertLess(sharp, standard)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vt.eye_resolvable_size(0)
        with self.assertRaises(ValueError):
            vt.eye_resolvable_size(-0.3)
        with self.assertRaises(ValueError):
            vt.eye_resolvable_size(0.3, eye_angle_arcmin=0)


class MagnifiedResolutionTest(unittest.TestCase):
    def test_anchor_ten_x_at_near_point(self):
        self.assertAlmostEqual(vt.resolvable_size(10, 0.25), 7.272e-6, places=9)

    def test_anchor_five_x_at_300_mm(self):
        self.assertAlmostEqual(vt.resolvable_size(5, 0.3), 1.74533e-5, places=8)

    def test_higher_magnification_resolves_finer(self):
        low = vt.resolvable_size(5, 0.25)
        high = vt.resolvable_size(10, 0.25)
        self.assertLess(high, low)
        self.assertAlmostEqual(high, low / 2.0, places=9)

    def test_roundtrip_with_magnification_for_resolution(self):
        size = vt.resolvable_size(10, 0.25)
        mag = vt.magnification_for_resolution(size, 0.25)
        self.assertAlmostEqual(mag, 10.0, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vt.resolvable_size(0, 0.25)
        with self.assertRaises(ValueError):
            vt.resolvable_size(10, 0)
        with self.assertRaises(ValueError):
            vt.resolvable_size(-10, 0.25)


class MagnificationForResolutionTest(unittest.TestCase):
    def test_anchor_twenty_five_micron_at_250_mm(self):
        self.assertAlmostEqual(
            vt.magnification_for_resolution(25e-6, 0.25), 2.909, places=3
        )

    def test_anchor_fifty_micron_at_300_mm(self):
        self.assertAlmostEqual(
            vt.magnification_for_resolution(50e-6, 0.3), 1.745, places=3
        )

    def test_finer_target_needs_more_magnification(self):
        fine = vt.magnification_for_resolution(25e-6, 0.25)
        coarse = vt.magnification_for_resolution(100e-6, 0.25)
        self.assertGreater(fine, coarse)
        self.assertAlmostEqual(fine, 4.0 * coarse, places=9)

    def test_farther_viewing_needs_more_magnification(self):
        near = vt.magnification_for_resolution(25e-6, 0.25)
        far = vt.magnification_for_resolution(25e-6, 0.5)
        self.assertAlmostEqual(far, 2.0 * near, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vt.magnification_for_resolution(0, 0.25)
        with self.assertRaises(ValueError):
            vt.magnification_for_resolution(25e-6, 0)
        with self.assertRaises(ValueError):
            vt.magnification_for_resolution(-25e-6, 0.25)


class IlluminanceTest(unittest.TestCase):
    def test_anchor_250_cd_at_half_meter(self):
        self.assertAlmostEqual(vt.illuminance_from_intensity(250, 0.5), 1000.0)

    def test_anchor_500_cd_at_one_meter(self):
        self.assertAlmostEqual(vt.illuminance_from_intensity(500, 1.0), 500.0)

    def test_inverse_square_falloff(self):
        near = vt.illuminance_from_intensity(250, 0.5)
        far = vt.illuminance_from_intensity(250, 1.0)
        self.assertAlmostEqual(far, near / 4.0, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vt.illuminance_from_intensity(0, 0.5)
        with self.assertRaises(ValueError):
            vt.illuminance_from_intensity(250, 0)
        with self.assertRaises(ValueError):
            vt.illuminance_from_intensity(-250, 0.5)


class IntensityForIlluminanceTest(unittest.TestCase):
    def test_anchor_thousand_lux_at_half_meter(self):
        self.assertAlmostEqual(vt.intensity_for_illuminance(1000, 0.5), 250.0)

    def test_doubling_distance_quadruples_intensity(self):
        near = vt.intensity_for_illuminance(1000, 0.5)
        far = vt.intensity_for_illuminance(1000, 1.0)
        self.assertAlmostEqual(far, 4.0 * near, places=9)

    def test_roundtrip_with_illuminance_from_intensity(self):
        i = vt.intensity_for_illuminance(1000, 0.5)
        self.assertAlmostEqual(vt.illuminance_from_intensity(i, 0.5), 1000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vt.intensity_for_illuminance(0, 0.5)
        with self.assertRaises(ValueError):
            vt.intensity_for_illuminance(1000, 0)


class DistanceForIlluminanceTest(unittest.TestCase):
    def test_anchor_250_cd_for_thousand_lux(self):
        self.assertAlmostEqual(vt.distance_for_illuminance(250, 1000), 0.5)

    def test_brighter_lamp_allows_farther_distance(self):
        dim = vt.distance_for_illuminance(250, 1000)
        bright = vt.distance_for_illuminance(1000, 1000)
        self.assertAlmostEqual(bright, 2.0 * dim, places=9)

    def test_roundtrip_with_intensity_for_illuminance(self):
        d = vt.distance_for_illuminance(250, 1000)
        self.assertAlmostEqual(vt.intensity_for_illuminance(1000, d), 250.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vt.distance_for_illuminance(0, 1000)
        with self.assertRaises(ValueError):
            vt.distance_for_illuminance(250, 0)


class UnitConversionTest(unittest.TestCase):
    def test_anchor_hundred_foot_candles(self):
        self.assertAlmostEqual(vt.foot_candles_to_lux(100), 1076.391, places=3)

    def test_anchor_thousand_lux_roundtrip(self):
        self.assertAlmostEqual(vt.lux_to_foot_candles(1076.391), 100.0, places=6)

    def test_lux_less_than_numeric_foot_candles(self):
        lux = vt.foot_candles_to_lux(100)
        self.assertGreater(lux, 100.0)

    def test_zero_is_zero(self):
        self.assertAlmostEqual(vt.foot_candles_to_lux(0), 0.0)
        self.assertAlmostEqual(vt.lux_to_foot_candles(0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vt.foot_candles_to_lux(-1)
        with self.assertRaises(ValueError):
            vt.lux_to_foot_candles(-1)


class FieldOfViewTest(unittest.TestCase):
    def test_anchor_forty_deg_at_fifty_mm(self):
        self.assertAlmostEqual(vt.field_of_view(0.05, 40), 3.6397e-2, places=6)

    def test_anchor_sixty_deg_at_hundred_mm(self):
        self.assertAlmostEqual(vt.field_of_view(0.1, 60), 1.1547e-1, places=4)

    def test_wider_angle_wider_field(self):
        narrow = vt.field_of_view(0.05, 20)
        wide = vt.field_of_view(0.05, 40)
        self.assertGreater(wide, narrow)

    def test_farther_working_distance_wider_field(self):
        near = vt.field_of_view(0.05, 40)
        far = vt.field_of_view(0.1, 40)
        self.assertAlmostEqual(far, 2.0 * near, places=9)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vt.field_of_view(0, 40)
        with self.assertRaises(ValueError):
            vt.field_of_view(0.05, 0)
        with self.assertRaises(ValueError):
            vt.field_of_view(0.05, 180)
        with self.assertRaises(ValueError):
            vt.field_of_view(0.05, -40)


class ScanPositionsTest(unittest.TestCase):
    def test_anchor_eight_positions_at_twenty_percent_overlap(self):
        self.assertEqual(vt.scan_positions(0.01, 1.6e-3, 0.2), 8)

    def test_more_overlap_more_positions(self):
        light = vt.scan_positions(0.01, 1.6e-3, 0.0)
        heavy = vt.scan_positions(0.01, 1.6e-3, 0.5)
        self.assertGreater(heavy, light)

    def test_larger_field_fewer_positions(self):
        small_field = vt.scan_positions(0.01, 1.6e-3, 0.2)
        large_field = vt.scan_positions(0.01, 3.2e-3, 0.2)
        self.assertLess(large_field, small_field)

    def test_zero_area_zero_positions(self):
        self.assertEqual(vt.scan_positions(0.0, 1.6e-3, 0.2), 0)

    def test_rounds_up_partial_fields(self):
        # 0.01 m2 with no overlap needs ceil(6.25) = 7 full fields.
        self.assertEqual(vt.scan_positions(0.01, 1.6e-3, 0.0), 7)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vt.scan_positions(-0.01, 1.6e-3, 0.2)
        with self.assertRaises(ValueError):
            vt.scan_positions(0.01, 0, 0.2)
        with self.assertRaises(ValueError):
            vt.scan_positions(0.01, 1.6e-3, 1.0)
        with self.assertRaises(ValueError):
            vt.scan_positions(0.01, 1.6e-3, -0.1)


class AcceptanceVerdictTest(unittest.TestCase):
    def test_anchor_reject_over_limit(self):
        self.assertFalse(vt.acceptance_verdict(1.2e-3, 1.0e-3))

    def test_anchor_accept_under_limit(self):
        self.assertTrue(vt.acceptance_verdict(0.8e-3, 1.0e-3))

    def test_at_limit_accepts(self):
        self.assertTrue(vt.acceptance_verdict(1.0e-3, 1.0e-3))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vt.acceptance_verdict(-1.0e-3, 1.0e-3)
        with self.assertRaises(ValueError):
            vt.acceptance_verdict(1.0e-3, 0)


class VisualInspectionScenarioTest(unittest.TestCase):
    def test_ten_x_borescope_resolves_fatigue_crack(self):
        # An 8 micrometer surface crack needs about 9.1x at the 250 mm
        # near point; a 10x borescope provides it, so the crack is in
        # the resolvable class.
        size = vt.resolvable_size(10, 0.25)
        self.assertLess(size, 8e-6)
        mag = vt.magnification_for_resolution(8e-6, 0.25)
        self.assertLessEqual(mag, 10.0)

    def test_lamp_too_far_drops_below_requirement(self):
        # A 250 cd lamp holds 1000 lux only within 0.5 m; at 0.8 m the
        # illumination falls to 390.6 lux, below the 1000 lux minimum.
        d = vt.distance_for_illuminance(250, 1000)
        self.assertAlmostEqual(d, 0.5)
        self.assertAlmostEqual(vt.illuminance_from_intensity(250, 0.8), 390.625)

    def test_hundred_foot_candle_procedure_stricter_than_lux(self):
        # 100 fc is 1076.4 lux, so a 1000 lux requirement is met but a
        # 100 fc requirement is not, on the same surface.
        lux = vt.foot_candles_to_lux(100)
        self.assertGreater(lux, 1000.0)

    def test_coverage_plan_for_fin_flange(self):
        # A 0.05 m2 flange scanned with a 40 mm square field at 25
        # percent overlap needs 42 positions.
        positions = vt.scan_positions(0.05, 1.6e-3, 0.25)
        self.assertEqual(positions, 42)

    def test_aperture_ratio_and_brightness_trend(self):
        # The same objective held closer gives a higher aperture ratio
        # and a brighter image, which is why the borescope is advanced
        # toward the surface before judging fine indications.
        near = vt.aperture_ratio(6e-3, 50e-3)
        far = vt.aperture_ratio(6e-3, 100e-3)
        self.assertAlmostEqual(near, 2.0 * far, places=9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
