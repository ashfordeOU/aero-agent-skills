#!/usr/bin/env python3
"""Gate 3 contract test for eclipse-time (stdlib unittest, offline).

Asserts REAL computed values for the eclipse geometry of circular
Earth orbits: orbital period, beta angle, shadow fraction, eclipse
time, and daylight fraction. Reference anchors: 5668 s (94.5 min)
period and about 2142 s (35.7 min) eclipse at 500 km altitude, about
4160 s (69 min) maximum eclipse at GEO.
"""

import math
import unittest

from eclipse_time_logic import (
    MU, RE, orbital_period, beta_angle, beta_angle_deg, shadow_fraction,
    eclipse_time, daylight_fraction, eclipse_properties,
)


class OrbitalPeriodTest(unittest.TestCase):
    def test_period_500_km(self):
        self.assertAlmostEqual(orbital_period(500.0), 5668.144, places=3)

    def test_period_geo(self):
        self.assertAlmostEqual(orbital_period(35786.0), 86142.114, places=3)

    def test_period_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            orbital_period(-1.0)

    def test_period_monotonic_with_altitude(self):
        self.assertGreater(orbital_period(800.0), orbital_period(400.0))


class BetaAngleTest(unittest.TestCase):
    def test_beta_example(self):
        # i = 98 deg, RAAN = 270 deg, sun dec = 23.44 deg, sun RA = 0 deg
        self.assertAlmostEqual(beta_angle_deg(98.0, 270.0, 23.44, 0.0),
                               -74.56, places=2)

    def test_beta_equinox_dusk_dawn(self):
        # Equinox sun on the ecliptic; dusk-dawn plane beta = -(180 - i)
        self.assertAlmostEqual(beta_angle_deg(98.0, 270.0, 0.0, 0.0),
                               -82.0, places=6)

    def test_beta_radians_roundtrip(self):
        b = beta_angle(math.radians(98.0), math.radians(270.0),
                       math.radians(23.44), 0.0)
        self.assertAlmostEqual(math.degrees(b), -74.56, places=2)

    def test_beta_equatorial_equals_sun_declination(self):
        # i = 0 deg: the orbit plane is the equator, so beta equals the
        # sun declination for any RAAN and sun right ascension
        self.assertAlmostEqual(beta_angle_deg(0.0, 45.0, 10.0, 20.0),
                               10.0, places=9)


class ShadowFractionTest(unittest.TestCase):
    def test_shadow_fraction_beta_zero_500(self):
        self.assertAlmostEqual(shadow_fraction(0.0, 500.0), 0.377817, places=6)

    def test_no_eclipse_high_beta(self):
        # beta = 75 deg exceeds beta_max ~68 deg at 500 km
        self.assertEqual(shadow_fraction(math.radians(75.0), 500.0), 0.0)

    def test_shadow_fraction_beta_60_500(self):
        self.assertAlmostEqual(shadow_fraction(math.radians(60.0), 500.0),
                               0.230543, places=6)

    def test_shadow_fraction_beta_zero_geo(self):
        self.assertAlmostEqual(shadow_fraction(0.0, 35786.0), 0.048290,
                               places=6)

    def test_shadow_fraction_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            shadow_fraction(0.0, -1.0)

    def test_shadow_fraction_decreases_with_beta(self):
        f0 = shadow_fraction(0.0, 500.0)
        f45 = shadow_fraction(math.radians(45.0), 500.0)
        self.assertGreater(f0, f45)


class EclipseTimeTest(unittest.TestCase):
    def test_eclipse_time_500(self):
        self.assertAlmostEqual(eclipse_time(500.0, 0.0), 2141.523, places=3)

    def test_eclipse_time_geo(self):
        self.assertAlmostEqual(eclipse_time(35786.0, 0.0), 4159.783, places=3)

    def test_eclipse_time_400(self):
        self.assertAlmostEqual(eclipse_time(400.0, 0.0), 2162.722, places=3)

    def test_eclipse_time_no_eclipse(self):
        self.assertEqual(eclipse_time(500.0, math.radians(75.0)), 0.0)

    def test_daylight_fraction_complements_shadow(self):
        self.assertAlmostEqual(
            daylight_fraction(0.0, 500.0) + shadow_fraction(0.0, 500.0),
            1.0, places=12)


class EclipsePropertiesTest(unittest.TestCase):
    def test_properties_consistency(self):
        p = eclipse_properties(
            500.0, math.radians(98.0), math.radians(270.0),
            math.radians(23.44), 0.0,
        )
        self.assertAlmostEqual(p["period_s"], orbital_period(500.0), places=9)
        self.assertAlmostEqual(p["beta_deg"], -74.56, places=2)
        self.assertAlmostEqual(p["shadow_fraction"] * p["period_s"],
                               p["eclipse_time_s"], places=9)
        self.assertAlmostEqual(p["daylight_fraction"],
                               1.0 - p["shadow_fraction"], places=12)

    def test_properties_beta_zero(self):
        p = eclipse_properties(500.0, 0.0, 0.0, 0.0, 0.0)
        self.assertAlmostEqual(p["beta_deg"], 0.0, places=9)
        self.assertAlmostEqual(p["eclipse_time_s"], 2141.523, places=3)

    def test_constants(self):
        self.assertEqual(MU, 3.986004418e14)
        self.assertEqual(RE, 6371000.0)


if __name__ == "__main__":
    unittest.main()
