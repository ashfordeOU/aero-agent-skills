"""Contract test for radio_navigation_aids_logic.py (offline, stdlib).

Deterministic unittest run: python3 scripts/test_radio_navigation_aids.py

Covers the worked-example contract from the wave-27 spec:
- bearing 30.0 deg within 0.01 for the aircraft 10 km east and
  17.32 km north of the station,
- radial 210.0 deg within 0.01,
- DME slant range sqrt(1e8 + 17320^2 + 1e6) = 20024.5 m within 1.0
  (the spec summary figure 20022.5 m came from rounding y^2 to three
  significant digits; the exact value for the stated inputs is
  20024.5 m, documented assumption),
- localizer deviation atan(100/5000) = 1.1458 deg within 0.001,
- glideslope deviation at 300 m of 0.0002 deg within 0.001 and at
  400 m of 0.9974 deg within 0.01,
- ValueError rejection of negative altitude, zero distance to
  threshold, and zero glideslope angle,
plus cardinal bearings, normalization to [0, 360), the reciprocal
round trip, and boundary checks.
"""

import math
import os
import sys
import unittest

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from radio_navigation_aids_logic import (bearing_deg, radial_deg,
                                         dme_slant_range_m,
                                         loc_deviation_deg,
                                         gs_deviation_deg, analyze,
                                         DEFAULT_GS_ANGLE_DEG)

X_AC = 10000.0
Y_AC = 17320.0
ALT_M = 1000.0


class TestBearing(unittest.TestCase):

    def test_bearing_worked_example_30_deg(self):
        self.assertAlmostEqual(bearing_deg(X_AC, Y_AC), 30.0, delta=0.01)

    def test_bearing_due_east_is_90(self):
        self.assertAlmostEqual(bearing_deg(1000.0, 0.0), 90.0, delta=1e-9)

    def test_bearing_due_north_is_0(self):
        self.assertAlmostEqual(bearing_deg(0.0, 1000.0), 0.0, delta=1e-9)

    def test_bearing_due_south_is_180(self):
        self.assertAlmostEqual(bearing_deg(0.0, -1000.0), 180.0, delta=1e-9)

    def test_bearing_due_west_is_270(self):
        self.assertAlmostEqual(bearing_deg(-1000.0, 0.0), 270.0,
                               delta=1e-9)

    def test_bearing_normalized_to_0_360(self):
        for x, y in [(1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0), (1.0, -1.0)]:
            value = bearing_deg(x, y)
            self.assertGreaterEqual(value, 0.0)
            self.assertLess(value, 360.0)

    def test_bearing_southwest_quadrant_225(self):
        self.assertAlmostEqual(bearing_deg(-1000.0, -1000.0), 225.0,
                               delta=1e-9)

    def test_bearing_at_station_is_zero_by_convention(self):
        self.assertEqual(bearing_deg(0.0, 0.0), 0.0)

    def test_bearing_rejects_non_finite(self):
        with self.assertRaises(ValueError):
            bearing_deg(float("nan"), 1000.0)
        with self.assertRaises(ValueError):
            bearing_deg(1000.0, float("inf"))


class TestRadial(unittest.TestCase):

    def test_radial_worked_example_210_deg(self):
        self.assertAlmostEqual(radial_deg(bearing_deg(X_AC, Y_AC)),
                               210.0, delta=0.01)

    def test_radial_of_30_is_210(self):
        self.assertEqual(radial_deg(30.0), 210.0)

    def test_radial_reciprocal_round_trip(self):
        for bearing in [0.0, 30.0, 90.0, 180.0, 210.0, 270.0, 359.5]:
            self.assertAlmostEqual(radial_deg(radial_deg(bearing)),
                                   bearing, delta=1e-9)

    def test_radial_rejects_out_of_range_bearing(self):
        with self.assertRaises(ValueError):
            radial_deg(-1.0)
        with self.assertRaises(ValueError):
            radial_deg(360.0)


class TestDmeSlantRange(unittest.TestCase):

    def test_dme_slant_worked_example_exact_value(self):
        expected = math.sqrt(1e8 + Y_AC * Y_AC + ALT_M * ALT_M)
        self.assertAlmostEqual(
            dme_slant_range_m(X_AC, Y_AC, ALT_M), expected, delta=1.0)
        self.assertAlmostEqual(
            dme_slant_range_m(X_AC, Y_AC, ALT_M), 20024.5, delta=1.0)

    def test_dme_spec_summary_value_within_rounding_band(self):
        self.assertAlmostEqual(
            dme_slant_range_m(X_AC, Y_AC, ALT_M), 20022.5, delta=2.1)

    def test_dme_three_four_five_triangle_at_ground_level(self):
        self.assertAlmostEqual(dme_slant_range_m(3000.0, 4000.0, 0.0),
                               5000.0, delta=1e-9)

    def test_dme_slant_exceeds_ground_distance_with_altitude(self):
        slant = dme_slant_range_m(3000.0, 4000.0, 1200.0)
        self.assertGreater(slant, 5000.0)

    def test_dme_zero_altitude_equals_ground_distance(self):
        self.assertAlmostEqual(dme_slant_range_m(6000.0, 8000.0, 0.0),
                               10000.0, delta=1e-9)

    def test_dme_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            dme_slant_range_m(1000.0, 1000.0, -1.0)


class TestLocalizerDeviation(unittest.TestCase):

    def test_loc_deviation_worked_example(self):
        self.assertAlmostEqual(loc_deviation_deg(100.0, 5000.0),
                               1.1458, delta=0.001)

    def test_loc_centerline_zero_deviation(self):
        self.assertEqual(loc_deviation_deg(0.0, 5000.0), 0.0)

    def test_loc_left_offset_negative_deviation(self):
        self.assertAlmostEqual(loc_deviation_deg(-100.0, 5000.0),
                               -1.1458, delta=0.001)

    def test_loc_offset_scales_with_inverse_distance(self):
        near = loc_deviation_deg(100.0, 5000.0)
        far = loc_deviation_deg(100.0, 10000.0)
        self.assertGreater(near, far)
        self.assertAlmostEqual(near, 2.0 * far, delta=0.01)

    def test_loc_zero_distance_raises(self):
        with self.assertRaises(ValueError):
            loc_deviation_deg(0.0, 0.0)

    def test_loc_negative_distance_raises(self):
        with self.assertRaises(ValueError):
            loc_deviation_deg(100.0, -5000.0)


class TestGlideslopeDeviation(unittest.TestCase):

    def test_gs_deviation_300_m_worked_example(self):
        self.assertAlmostEqual(gs_deviation_deg(300.0, 5724.0),
                               0.0002, delta=0.001)

    def test_gs_deviation_400_m_worked_example(self):
        self.assertAlmostEqual(gs_deviation_deg(400.0, 5724.0),
                               0.9974, delta=0.01)

    def test_gs_default_angle_is_3_deg(self):
        self.assertEqual(DEFAULT_GS_ANGLE_DEG, 3.0)

    def test_gs_on_path_height_gives_near_zero_deviation(self):
        height_on_path = 5724.0 * math.tan(math.radians(3.0))
        deviation = gs_deviation_deg(height_on_path, 5724.0)
        self.assertAlmostEqual(deviation, 0.0, delta=1e-6)

    def test_gs_zero_height_gives_minus_nominal(self):
        self.assertAlmostEqual(gs_deviation_deg(0.0, 5724.0), -3.0,
                               delta=1e-9)

    def test_gs_custom_angle_shifts_deviation(self):
        deviation = gs_deviation_deg(400.0, 5724.0, gs_angle_deg=2.5)
        self.assertAlmostEqual(deviation, 1.4974, delta=0.01)

    def test_gs_zero_distance_raises(self):
        with self.assertRaises(ValueError):
            gs_deviation_deg(300.0, 0.0)

    def test_gs_zero_angle_raises(self):
        with self.assertRaises(ValueError):
            gs_deviation_deg(300.0, 5724.0, gs_angle_deg=0.0)

    def test_gs_shallow_or_steep_angle_raises(self):
        with self.assertRaises(ValueError):
            gs_deviation_deg(300.0, 5724.0, gs_angle_deg=-2.0)
        with self.assertRaises(ValueError):
            gs_deviation_deg(300.0, 5724.0, gs_angle_deg=90.0)

    def test_gs_negative_height_raises(self):
        with self.assertRaises(ValueError):
            gs_deviation_deg(-50.0, 5724.0)


class TestAnalyze(unittest.TestCase):

    def test_analyze_returns_all_quantities(self):
        result = analyze(X_AC, Y_AC, ALT_M, 100.0, 5000.0, 400.0, 5724.0)
        self.assertEqual(
            sorted(result.keys()),
            ["bearing_deg", "dme_slant_range_m", "gs_deviation_deg",
             "loc_deviation_deg", "radial_deg"])
        self.assertAlmostEqual(result["bearing_deg"], 30.0, delta=0.01)
        self.assertAlmostEqual(result["radial_deg"], 210.0, delta=0.01)
        self.assertAlmostEqual(result["dme_slant_range_m"], 20024.5,
                               delta=1.0)
        self.assertAlmostEqual(result["loc_deviation_deg"], 1.1458,
                               delta=0.001)
        self.assertAlmostEqual(result["gs_deviation_deg"], 0.9974,
                               delta=0.01)

    def test_analyze_matches_individual_calls(self):
        result = analyze(X_AC, Y_AC, ALT_M, 100.0, 5000.0, 300.0, 5724.0)
        self.assertAlmostEqual(result["bearing_deg"],
                               bearing_deg(X_AC, Y_AC), delta=1e-9)
        self.assertAlmostEqual(result["radial_deg"],
                               radial_deg(bearing_deg(X_AC, Y_AC)),
                               delta=1e-9)
        self.assertAlmostEqual(result["dme_slant_range_m"],
                               dme_slant_range_m(X_AC, Y_AC, ALT_M),
                               delta=1e-9)
        self.assertAlmostEqual(result["loc_deviation_deg"],
                               loc_deviation_deg(100.0, 5000.0),
                               delta=1e-9)
        self.assertAlmostEqual(result["gs_deviation_deg"],
                               gs_deviation_deg(300.0, 5724.0),
                               delta=1e-9)

    def test_analyze_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            analyze(X_AC, Y_AC, -1.0, 100.0, 5000.0, 300.0, 5724.0)


if __name__ == "__main__":
    unittest.main()
