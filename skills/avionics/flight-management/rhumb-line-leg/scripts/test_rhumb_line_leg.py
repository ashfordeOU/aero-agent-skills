"""Offline deterministic contract test for the rhumb line leg module.

Runs with stdlib unittest only (no network, no external processes):

    python3 scripts/test_rhumb_line_leg.py

Covers the wave-38 spec anchors: leg 50N 000E to 55N 010E with rhumb
course 50.563 deg, rhumb distance 875.236 km, great-circle distance
874.536 km (central angle 7.865 deg), delta 0.700 km at 0.0801 percent;
parallel leg at 55N over 10 deg of longitude 637.788 km; long leg
30N 030W to 55N 010E with rhumb 4245.008 km, great-circle 4203.796 km,
delta 41.213 km at 0.98 percent; meridian-leg identity rhumb equals
great circle with course 0 or 180; parallel-leg course 90 or 270;
ValueError rejection of out-of-range latitudes and longitude spans;
and run-to-run determinism.
"""

import math
import unittest

from rhumb_line_leg_logic import (
    R_EARTH,
    great_circle_distance_m,
    isometric_latitude,
    parallel_leg_length_m,
    rhumb_course_deg,
    rhumb_distance_m,
    rhumb_vs_great_circle,
)

# Real module outputs for the wave-38 anchor leg 50N 000E to 55N 010E.
ANCHOR_COURSE_DEG = 50.563088238480475
ANCHOR_RHUMB_M = 875236.0685099779
ANCHOR_GC_M = 874535.8508722916
ANCHOR_DELTA_M = 700.2176376862917
ANCHOR_DELTA_PCT = 0.0800673450937284
PARALLEL_55_10_M = 637787.8976510199

# Real module outputs for the long leg 30N 030W to 55N 010E.
LONG_RHUMB_M = 4245008.399199998
LONG_GC_M = 4203795.84172454
LONG_DELTA_M = 41212.5574754579
LONG_DELTA_PCT = 0.9803653418751921

MERIDIAN_LAT1, MERIDIAN_LAT2 = 40.0, 60.0
MERIDIAN_LON = 20.0


class RhumbCourseTests(unittest.TestCase):
    def test_anchor_leg_course(self):
        course = rhumb_course_deg(50.0, 0.0, 55.0, 10.0)
        self.assertAlmostEqual(course, ANCHOR_COURSE_DEG, places=9)
        self.assertTrue(abs(course - 50.56) <= 0.1)

    def test_course_normalized_zero_to_360(self):
        legs = ((50.0, 0.0, 55.0, 10.0), (30.0, -30.0, 55.0, 10.0),
                (0.0, 0.0, -20.0, -45.0), (-10.0, 120.0, 10.0, -120.0))
        for leg in legs:
            course = rhumb_course_deg(*leg)
            self.assertGreaterEqual(course, 0.0)
            self.assertLess(course, 360.0)

    def test_parallel_east_course_90(self):
        self.assertAlmostEqual(
            rhumb_course_deg(55.0, 0.0, 55.0, 10.0), 90.0, places=9
        )
        self.assertAlmostEqual(
            rhumb_course_deg(0.0, 0.0, 0.0, 90.0), 90.0, places=9
        )

    def test_parallel_west_course_270(self):
        self.assertAlmostEqual(
            rhumb_course_deg(55.0, 10.0, 55.0, 0.0), 270.0, places=9
        )

    def test_meridian_north_course_0(self):
        self.assertAlmostEqual(
            rhumb_course_deg(40.0, 20.0, 60.0, 20.0), 0.0, places=9
        )

    def test_meridian_south_course_180(self):
        self.assertAlmostEqual(
            rhumb_course_deg(60.0, 20.0, 40.0, 20.0), 180.0, places=9
        )

    def test_course_rejects_bad_latitude_and_poles(self):
        for bad in (91.0, -91.0, 100.0, -100.0):
            with self.assertRaises(ValueError):
                rhumb_course_deg(bad, 0.0, 55.0, 10.0)
            with self.assertRaises(ValueError):
                rhumb_course_deg(50.0, 0.0, bad, 10.0)
        for pole in (90.0, -90.0):
            with self.assertRaises(ValueError):
                rhumb_course_deg(pole, 0.0, 55.0, 10.0)


class RhumbDistanceTests(unittest.TestCase):
    def test_anchor_leg_distance(self):
        dist = rhumb_distance_m(50.0, 0.0, 55.0, 10.0)
        self.assertAlmostEqual(dist, ANCHOR_RHUMB_M, places=6)
        self.assertTrue(abs(dist / 1000.0 - 875.24) <= 1.0)

    def test_parallel_leg_equals_parallel_length(self):
        dist = rhumb_distance_m(55.0, 0.0, 55.0, 10.0)
        self.assertAlmostEqual(dist, PARALLEL_55_10_M, places=6)
        self.assertEqual(dist, parallel_leg_length_m(55.0, 10.0))
        self.assertTrue(abs(dist / 1000.0 - 637.79) <= 1.0)

    def test_meridian_distance_equals_great_circle(self):
        rhumb = rhumb_distance_m(MERIDIAN_LAT1, MERIDIAN_LON,
                                 MERIDIAN_LAT2, MERIDIAN_LON)
        gc = great_circle_distance_m(MERIDIAN_LAT1, MERIDIAN_LON,
                                     MERIDIAN_LAT2, MERIDIAN_LON)
        self.assertAlmostEqual(rhumb, gc, delta=1.0e-6)
        self.assertAlmostEqual(rhumb, R_EARTH * math.radians(20.0), places=3)

    def test_equator_quarter_arc(self):
        dist = rhumb_distance_m(0.0, 0.0, 0.0, 90.0)
        self.assertAlmostEqual(dist, R_EARTH * math.pi / 2.0, places=3)

    def test_same_point_zero_distance(self):
        self.assertEqual(rhumb_distance_m(50.0, 10.0, 50.0, 10.0), 0.0)

    def test_rhumb_never_shorter_than_great_circle(self):
        legs = ((50.0, 0.0, 55.0, 10.0), (30.0, -30.0, 55.0, 10.0),
                (-40.0, -80.0, 20.0, 40.0), (10.0, 100.0, -30.0, 60.0),
                (0.0, 0.0, 45.0, 120.0))
        for leg in legs:
            rhumb = rhumb_distance_m(*leg)
            gc = great_circle_distance_m(*leg)
            self.assertGreaterEqual(rhumb, gc - 1.0e-6)


class ParallelLegTests(unittest.TestCase):
    def test_anchor_parallel_leg_55n(self):
        length = parallel_leg_length_m(55.0, 10.0)
        self.assertAlmostEqual(length, PARALLEL_55_10_M, places=6)
        self.assertTrue(abs(length / 1000.0 - 637.79) <= 1.0)

    def test_zero_lon_span_zero_length(self):
        self.assertEqual(parallel_leg_length_m(55.0, 0.0), 0.0)

    def test_equator_quarter_arc(self):
        length = parallel_leg_length_m(0.0, 90.0)
        self.assertAlmostEqual(length, R_EARTH * math.pi / 2.0, places=3)

    def test_parallel_half_length_at_60_degrees(self):
        at_60 = parallel_leg_length_m(60.0, 30.0)
        at_0 = parallel_leg_length_m(0.0, 30.0)
        self.assertAlmostEqual(at_60, at_0 / 2.0, places=3)

    def test_negative_span_magnitude_symmetric(self):
        self.assertAlmostEqual(
            parallel_leg_length_m(55.0, -10.0), -PARALLEL_55_10_M, places=6
        )

    def test_polar_parallel_near_zero(self):
        self.assertLess(abs(parallel_leg_length_m(90.0, 90.0)), 1.0e-3)
        self.assertLess(abs(parallel_leg_length_m(-90.0, 90.0)), 1.0e-3)

    def test_out_of_range_value_errors(self):
        for bad in (360.1, -360.1, 400.0, -500.0):
            with self.assertRaises(ValueError):
                parallel_leg_length_m(55.0, bad)
        for bad in (91.0, -91.0, 180.0):
            with self.assertRaises(ValueError):
                parallel_leg_length_m(bad, 10.0)


class GreatCircleDistanceTests(unittest.TestCase):
    def test_anchor_leg_great_circle(self):
        gc = great_circle_distance_m(50.0, 0.0, 55.0, 10.0)
        self.assertAlmostEqual(gc, ANCHOR_GC_M, places=6)
        central_deg = math.degrees(gc / R_EARTH)
        self.assertAlmostEqual(central_deg, 7.865, delta=0.01)
        self.assertTrue(abs(gc / 1000.0 - 874.54) <= 1.0)

    def test_meridian_leg_central_angle_is_lat_span(self):
        gc = great_circle_distance_m(MERIDIAN_LAT1, MERIDIAN_LON,
                                     MERIDIAN_LAT2, MERIDIAN_LON)
        self.assertAlmostEqual(gc, R_EARTH * math.radians(20.0), places=3)

    def test_same_point_zero(self):
        self.assertEqual(great_circle_distance_m(50.0, 10.0, 50.0, 10.0),
                         0.0)

    def test_antipodal_half_circumference(self):
        gc = great_circle_distance_m(0.0, 0.0, 0.0, 180.0)
        self.assertAlmostEqual(gc, R_EARTH * math.pi, places=3)

    def test_rejects_out_of_range_latitude(self):
        for bad in (91.0, -91.0):
            with self.assertRaises(ValueError):
                great_circle_distance_m(bad, 0.0, 55.0, 10.0)
            with self.assertRaises(ValueError):
                great_circle_distance_m(50.0, 0.0, bad, 10.0)


class IsometricLatitudeTests(unittest.TestCase):
    def test_equator_psi_zero(self):
        self.assertAlmostEqual(isometric_latitude(0.0), 0.0, places=9)

    def test_reference_psi_55n(self):
        psi = isometric_latitude(55.0)
        self.assertAlmostEqual(
            psi, math.log(math.tan(math.pi / 4.0 + math.radians(27.5))),
            delta=1.0e-9
        )
        self.assertGreater(psi, 0.0)
        self.assertLess(psi, 2.0)

    def test_southern_hemisphere_negative(self):
        self.assertLess(isometric_latitude(-30.0), 0.0)

    def test_pole_value_error(self):
        for bad in (90.0, -90.0):
            with self.assertRaises(ValueError):
                isometric_latitude(bad)


class RhumbVsGreatCircleTests(unittest.TestCase):
    def test_anchor_delta_dict(self):
        result = rhumb_vs_great_circle(50.0, 0.0, 55.0, 10.0)
        self.assertAlmostEqual(result["rhumb_m"], ANCHOR_RHUMB_M, places=6)
        self.assertAlmostEqual(result["great_circle_m"], ANCHOR_GC_M,
                               places=6)
        self.assertAlmostEqual(result["delta_m"], ANCHOR_DELTA_M, places=6)
        self.assertAlmostEqual(result["delta_pct"], ANCHOR_DELTA_PCT,
                               places=6)
        self.assertTrue(abs(result["delta_m"] / 1000.0 - 0.70) <= 0.01)
        self.assertTrue(abs(result["delta_pct"] - 0.08) <= 0.005)

    def test_long_leg_delta_material(self):
        result = rhumb_vs_great_circle(30.0, -30.0, 55.0, 10.0)
        self.assertAlmostEqual(result["rhumb_m"], LONG_RHUMB_M, places=6)
        self.assertAlmostEqual(result["great_circle_m"], LONG_GC_M, places=6)
        self.assertAlmostEqual(result["delta_m"], LONG_DELTA_M, places=6)
        self.assertAlmostEqual(result["delta_pct"], LONG_DELTA_PCT, places=6)
        self.assertTrue(abs(result["rhumb_m"] / 1000.0 - 4245.0) <= 2.0)
        self.assertTrue(abs(result["great_circle_m"] / 1000.0 - 4203.8) <= 2.0)
        self.assertTrue(abs(result["delta_m"] / 1000.0 - 41.2) <= 1.0)
        self.assertTrue(abs(result["delta_pct"] - 0.98) <= 0.01)

    def test_meridian_leg_zero_delta(self):
        result = rhumb_vs_great_circle(MERIDIAN_LAT1, MERIDIAN_LON,
                                       MERIDIAN_LAT2, MERIDIAN_LON)
        self.assertAlmostEqual(result["delta_m"], 0.0, delta=1.0e-6)
        self.assertAlmostEqual(result["delta_pct"], 0.0, delta=1.0e-6)

    def test_same_point_zero_dict(self):
        result = rhumb_vs_great_circle(45.0, 10.0, 45.0, 10.0)
        self.assertEqual(result["rhumb_m"], 0.0)
        self.assertEqual(result["great_circle_m"], 0.0)
        self.assertEqual(result["delta_m"], 0.0)
        self.assertEqual(result["delta_pct"], 0.0)

    def test_delta_positive_on_diagonal_legs(self):
        legs = ((50.0, 0.0, 55.0, 10.0), (30.0, -30.0, 55.0, 10.0),
                (-10.0, -20.0, 40.0, 80.0), (0.0, 0.0, 30.0, 60.0))
        for leg in legs:
            result = rhumb_vs_great_circle(*leg)
            self.assertGreater(result["delta_m"], 0.0)
            self.assertGreater(result["delta_pct"], 0.0)

    def test_determinism_repeated_calls(self):
        first = rhumb_vs_great_circle(30.0, -30.0, 55.0, 10.0)
        second = rhumb_vs_great_circle(30.0, -30.0, 55.0, 10.0)
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
