#!/usr/bin/env python3
"""Gate 3 contract test: navigation coordinate frame conversions.

Exercises scripts/navigation_frames_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — WGS-84 geodetic to ECEF
(textbook values: X = a = 6378137.0 m at (0, 0, 0); Z = polar semi-axis
b = 6356752.314 m at the north pole; altitude adds radially at the
equator); ECEF to NED rotation (equator reference matrix, orthonormality,
determinant +1); NED velocity (a pure +Z ECEF velocity at the equator
reference is due north, magnitude preserved); GMST Earth rotation angle
(J2000.0 value 280.460618375 deg per Meeus, ~360.9856 deg per day
sidereal drift, result in [0, 2*pi)); invalid inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import navigation_frames_logic as nf  # noqa: E402

WGS84_A = 6378137.0
WGS84_B = 6356752.314245179  # m, WGS-84 polar semi-axis


class GeodeticToEcefTest(unittest.TestCase):
    def test_equator_origin_is_semi_major_axis(self):
        x, y, z = nf.geodetic_to_ecef(0.0, 0.0, 0.0)
        self.assertAlmostEqual(x, WGS84_A, places=3)
        self.assertAlmostEqual(y, 0.0, places=3)
        self.assertAlmostEqual(z, 0.0, places=3)

    def test_equator_90_deg_east(self):
        x, y, z = nf.geodetic_to_ecef(0.0, math.pi / 2.0, 0.0)
        self.assertAlmostEqual(x, 0.0, places=3)
        self.assertAlmostEqual(y, WGS84_A, places=3)
        self.assertAlmostEqual(z, 0.0, places=3)

    def test_north_pole_is_polar_semi_axis(self):
        x, y, z = nf.geodetic_to_ecef(math.pi / 2.0, 0.0, 0.0)
        self.assertAlmostEqual(x, 0.0, places=3)
        self.assertAlmostEqual(y, 0.0, places=3)
        self.assertAlmostEqual(z, WGS84_B, places=3)

    def test_altitude_adds_radially_at_equator(self):
        x, y, z = nf.geodetic_to_ecef(0.0, 0.0, 1000.0)
        self.assertAlmostEqual(x, WGS84_A + 1000.0, places=3)
        self.assertAlmostEqual(y, 0.0, places=3)
        self.assertAlmostEqual(z, 0.0, places=3)

    def test_boundary_angles_and_minimum_altitude_ok(self):
        nf.geodetic_to_ecef(-math.pi / 2.0, math.pi, -1.0e6)
        nf.geodetic_to_ecef(math.pi / 2.0, -math.pi, -1.0e6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nf.geodetic_to_ecef(math.pi / 2.0 + 0.1, 0.0, 0.0)
        with self.assertRaises(ValueError):
            nf.geodetic_to_ecef(0.0, math.pi + 0.1, 0.0)
        with self.assertRaises(ValueError):
            nf.geodetic_to_ecef(0.0, 0.0, -1.0e6 - 1.0)


class EcefToNedTest(unittest.TestCase):
    def test_equator_reference_matrix(self):
        r = nf.ecef_to_ned(0.0, 0.0)
        expected = [[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]]
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(r[i][j], expected[i][j], places=12)

    def test_rotation_is_orthonormal(self):
        r = nf.ecef_to_ned(0.5, 1.2)
        for i in range(3):
            for j in range(3):
                dot = sum(r[i][k] * r[j][k] for k in range(3))
                self.assertAlmostEqual(dot, 1.0 if i == j else 0.0, places=12)

    def test_rotation_determinant_is_one(self):
        r = nf.ecef_to_ned(-0.3, 0.7)
        det = (
            r[0][0] * (r[1][1] * r[2][2] - r[1][2] * r[2][1])
            - r[0][1] * (r[1][0] * r[2][2] - r[1][2] * r[2][0])
            + r[0][2] * (r[1][0] * r[2][1] - r[1][1] * r[2][0])
        )
        self.assertAlmostEqual(det, 1.0, places=12)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nf.ecef_to_ned(math.pi / 2.0 + 0.1, 0.0)
        with self.assertRaises(ValueError):
            nf.ecef_to_ned(0.0, math.pi + 0.1)


class NedVelocityTest(unittest.TestCase):
    def test_upward_ecef_velocity_is_due_north_at_equator(self):
        r = nf.ecef_to_ned(0.0, 0.0)
        vn, ve, vd = nf.ned_velocity([0.0, 0.0, 1.0], r)
        self.assertAlmostEqual(vn, 1.0, places=12)
        self.assertAlmostEqual(ve, 0.0, places=12)
        self.assertAlmostEqual(vd, 0.0, places=12)

    def test_magnitude_is_preserved(self):
        v = [120.0, -45.0, 30.0]
        vn, ve, vd = nf.ned_velocity(v, nf.ecef_to_ned(0.6, -1.4))
        speed = math.sqrt(vn * vn + ve * ve + vd * vd)
        self.assertAlmostEqual(
            speed, math.sqrt(120.0 ** 2 + 45.0 ** 2 + 30.0 ** 2), places=9
        )

    def test_zero_velocity_maps_to_zero(self):
        vn, ve, vd = nf.ned_velocity([0.0, 0.0, 0.0], nf.ecef_to_ned(0.3, 0.9))
        self.assertEqual((vn, ve, vd), (0.0, 0.0, 0.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nf.ned_velocity([1.0, 2.0], nf.ecef_to_ned(0.0, 0.0))
        with self.assertRaises(ValueError):
            nf.ned_velocity([1.0, 2.0, 3.0], [[1.0, 0.0], [0.0, 1.0]])


class GmstRotationAngleTest(unittest.TestCase):
    def test_j2000_known_value(self):
        # Meeus (Astronomical Algorithms): GMST at J2000.0 (JD 2451545.0)
        # is 280.460618375 deg. Self-consistent with the IAU 1982 series
        # constant 67310.54841 s of time (67310.54841 / 240 deg).
        angle = nf.gmst_rotation_angle(2451545.0)
        self.assertAlmostEqual(angle, math.radians(280.460618375), places=6)

    def test_sidereal_day_drift(self):
        # Earth rotates about 360.9856 deg per mean solar day.
        a0 = nf.gmst_rotation_angle(2460000.5)
        a1 = nf.gmst_rotation_angle(2460001.5)
        drift = (a1 - a0) % (2.0 * math.pi)
        expected = math.radians(360.98564736629) % (2.0 * math.pi)
        self.assertAlmostEqual(drift, expected, places=3)

    def test_result_in_range(self):
        for jd in (2440587.5, 2451545.0, 2469807.5):
            angle = nf.gmst_rotation_angle(jd)
            self.assertGreaterEqual(angle, 0.0)
            self.assertLess(angle, 2.0 * math.pi)

    def test_zero_julian_centuries_is_series_constant(self):
        t0 = nf.gmst_rotation_angle(2451545.0)
        self.assertAlmostEqual(
            t0, (67310.54841 * math.pi / 43200.0) % (2.0 * math.pi), places=9
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
