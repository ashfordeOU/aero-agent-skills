#!/usr/bin/env python3
"""Gate 3 contract test: satellite ground coverage geometry.

Exercises scripts/satellite_coverage_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the access
circle central angle, swath width, maximum off-nadir angle, access
circle radius, global and regional coverage fractions, and first-order
access time per pass return the pinned worked values for LEO and
geostationary cases, the limb relation eta + eps + theta = 90 deg
holds, and invalid inputs (negative altitude, elevation outside
[0, 90] deg, non-positive period or region area) raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import satellite_coverage_logic as scl  # noqa: E402


class AccessGeometryTest(unittest.TestCase):
    def test_leo_central_angles(self):
        # Worked anchors: ISS-like 400 km horizon access gives a
        # 19.79 deg access circle; 500 km with a 10 deg mask gives
        # 14.06 deg; 800 km with a 5 deg mask gives 22.74 deg.
        self.assertAlmostEqual(scl.central_angle(400.0, 0.0), 19.7926,
                               places=3)
        self.assertAlmostEqual(scl.central_angle(500.0, 10.0), 14.0565,
                               places=3)
        self.assertAlmostEqual(scl.central_angle(800.0, 5.0), 22.7412,
                               places=3)

    def test_geo_central_angles(self):
        # Geostationary: 81.31 deg at the horizon, 76.34 deg with a
        # 5 deg mask; a single GEO satellite sees roughly a third of
        # the globe.
        self.assertAlmostEqual(scl.central_angle(35786.0, 0.0), 81.3078,
                               places=3)
        self.assertAlmostEqual(scl.central_angle(35786.0, 5.0), 76.3412,
                               places=3)

    def test_max_off_nadir_anchors(self):
        # Off-nadir angle to the access circle edge: 70.21 deg at
        # 400 km horizon access, only 8.69 deg from GEO.
        self.assertAlmostEqual(scl.max_off_nadir(400.0, 0.0), 70.2074,
                               places=3)
        self.assertAlmostEqual(scl.max_off_nadir(35786.0, 0.0), 8.6922,
                               places=3)

    def test_limb_relation(self):
        # The triangle closes at the limb: eta + eps + theta = 90 deg.
        for alt, eps in [(400.0, 0.0), (500.0, 10.0), (800.0, 5.0),
                         (35786.0, 0.0), (35786.0, 5.0)]:
            eta = scl.central_angle(alt, eps)
            theta = scl.max_off_nadir(alt, eps)
            self.assertAlmostEqual(eta + eps + theta, 90.0, places=6)

    def test_swath_width_anchors(self):
        # Full swath across nadir: 4401.7 km at 400 km horizon access,
        # 3126.0 km at 500 km with a 10 deg mask, 16977.5 km from GEO.
        self.assertAlmostEqual(scl.swath_width(400.0, 0.0), 4401.673,
                               places=2)
        self.assertAlmostEqual(scl.swath_width(500.0, 10.0), 3126.031,
                               places=2)
        self.assertAlmostEqual(scl.swath_width(35786.0, 5.0), 16977.502,
                               places=2)

    def test_swath_is_twice_access_radius(self):
        # The full swath is twice the access circle radius on the
        # ground (arc lengths over the spherical Earth).
        for alt, eps in [(400.0, 0.0), (800.0, 5.0), (35786.0, 0.0)]:
            self.assertAlmostEqual(
                scl.swath_width(alt, eps),
                2.0 * scl.access_circle_radius_km(alt, eps), places=6)

    def test_access_radius_anchor(self):
        self.assertAlmostEqual(scl.access_circle_radius_km(400.0, 0.0),
                               2200.836, places=2)


class CoverageFractionTest(unittest.TestCase):
    def test_geo_global_fraction(self):
        # Textbook anchor: one GEO satellite at horizon access covers
        # 42.4% of the globe.
        self.assertAlmostEqual(scl.coverage_fraction_global(35786.0, 0.0),
                               0.424437, places=5)

    def test_leo_global_fraction(self):
        # A 400 km satellite at horizon access covers about 2.95% of
        # the globe at any instant.
        self.assertAlmostEqual(scl.coverage_fraction_global(400.0, 0.0),
                               0.029538, places=5)

    def test_global_fraction_bounds(self):
        # Single-access instantaneous fraction stays in (0, 0.5] for
        # valid inputs; the largest circle (GEO horizon access) is
        # just under half the globe.
        for alt, eps in [(400.0, 0.0), (500.0, 10.0), (800.0, 5.0),
                         (35786.0, 0.0), (35786.0, 5.0)]:
            f = scl.coverage_fraction_global(alt, eps)
            self.assertGreater(f, 0.0)
            self.assertLessEqual(f, 0.5)

    def test_region_fraction_clamp(self):
        # A GEO access circle (216.5e6 km2) fully covers a 1e7 km2
        # region (clamped to 1.0) and covers 43.3% of a 5e8 km2 one.
        self.assertEqual(scl.coverage_fraction_region(35786.0, 0.0, 1.0e7),
                         1.0)
        self.assertAlmostEqual(
            scl.coverage_fraction_region(35786.0, 0.0, 5.0e8),
            0.432981, places=5)

    def test_access_time_per_pass_anchor(self):
        # ISS-like 400 km horizon access with a 5556 s period keeps a
        # ground point in view about 611 s per center pass.
        self.assertAlmostEqual(
            scl.access_time_per_pass(400.0, 0.0, 5556.0), 610.931,
            places=2)


class ValidationTest(unittest.TestCase):
    def test_negative_altitude_raises(self):
        for fn in (scl.central_angle, scl.swath_width, scl.max_off_nadir,
                   scl.access_circle_radius_km, scl.coverage_fraction_global):
            with self.assertRaises(ValueError):
                fn(-1.0, 10.0)

    def test_elevation_out_of_range_raises(self):
        for eps in (-5.0, 95.0, 180.0):
            with self.assertRaises(ValueError):
                scl.central_angle(500.0, eps)
            with self.assertRaises(ValueError):
                scl.swath_width(500.0, eps)
            with self.assertRaises(ValueError):
                scl.max_off_nadir(500.0, eps)

    def test_non_numeric_inputs_raise(self):
        with self.assertRaises(ValueError):
            scl.central_angle("500", 10.0)
        with self.assertRaises(ValueError):
            scl.central_angle(500.0, "ten")
        with self.assertRaises(ValueError):
            scl.swath_width(True, 10.0)

    def test_non_positive_period_raises(self):
        with self.assertRaises(ValueError):
            scl.access_time_per_pass(400.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            scl.access_time_per_pass(400.0, 0.0, -100.0)

    def test_non_positive_region_area_raises(self):
        with self.assertRaises(ValueError):
            scl.coverage_fraction_region(35786.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            scl.coverage_fraction_region(35786.0, 0.0, -5.0e6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
