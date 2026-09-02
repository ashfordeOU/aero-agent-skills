#!/usr/bin/env python3
"""Gate 3 contract tests: sun-synchronous inclination logic.

Stdlib unittest only, offline, no external dependencies. Run with:
python3 scripts/test_sun_synchronous.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import sun_synchronous_logic as ssl

OMEGA_DOT_SUN = 2.0 * math.pi / 365.2421897 / 86400.0


class TestOrbitalMeanMotion(unittest.TestCase):
    def test_mean_motion_500km(self):
        # Analytic: a = 6871000 m, n = sqrt(3.986004418e14 / 6871000**3)
        # = 1.10850834e-3 rad/s.
        n = ssl.orbital_mean_motion(500.0)
        self.assertAlmostEqual(n, 1.10850834e-3, places=8)
        self.assertGreater(n, 0.0)

    def test_mean_motion_decreases_with_altitude(self):
        self.assertGreater(
            ssl.orbital_mean_motion(300.0), ssl.orbital_mean_motion(900.0)
        )

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            ssl.orbital_mean_motion(-1.0)


class TestNodalRegressionRate(unittest.TestCase):
    def test_prograde_regression_is_negative(self):
        n = ssl.orbital_mean_motion(500.0)
        rate = ssl.nodal_regression_rate(n, 6871000.0, math.radians(30.0))
        self.assertLess(rate, 0.0)

    def test_zero_regression_at_pole(self):
        n = ssl.orbital_mean_motion(500.0)
        rate = ssl.nodal_regression_rate(n, 6871000.0, math.pi / 2.0)
        self.assertAlmostEqual(rate, 0.0, places=15)

    def test_inclination_out_of_range_raises(self):
        n = ssl.orbital_mean_motion(500.0)
        with self.assertRaises(ValueError):
            ssl.nodal_regression_rate(n, 6871000.0, -0.1)
        with self.assertRaises(ValueError):
            ssl.nodal_regression_rate(n, 6871000.0, math.pi + 0.1)


class TestSunSynchronousInclination(unittest.TestCase):
    def test_inclination_500km_analytic(self):
        # Analytic check: cos i = -0.12866 -> i = 97.39 deg at 500 km.
        inc_deg = ssl.sun_synchronous_inclination(500.0) * 180.0 / math.pi
        self.assertAlmostEqual(inc_deg, 97.39, places=2)
        self.assertGreater(inc_deg, 90.0)  # sun-synchronous is retrograde

    def test_properties_500km(self):
        props = ssl.sun_synchronous_properties(500.0)
        self.assertEqual(props["altitude_km"], 500.0)
        self.assertAlmostEqual(props["a_m"], 6871000.0, places=3)
        self.assertAlmostEqual(
            props["inclination_deg"], 97.39, places=2
        )
        self.assertAlmostEqual(
            props["inclination_rad"],
            props["inclination_deg"] * math.pi / 180.0,
            places=15,
        )
        self.assertAlmostEqual(props["n_rad_s"], 1.10850834e-3, places=8)

    def test_closed_loop_regression_matches_sun(self):
        # The chosen inclination must make nodal regression exactly
        # match the sun's apparent mean motion.
        props = ssl.sun_synchronous_properties(500.0)
        om_dot = ssl.nodal_regression_rate(
            props["n_rad_s"], props["a_m"], props["inclination_rad"]
        )
        self.assertAlmostEqual(om_dot, OMEGA_DOT_SUN, places=14)

    def test_inclination_increases_with_altitude(self):
        i500 = ssl.sun_synchronous_inclination(500.0)
        i800 = ssl.sun_synchronous_inclination(800.0)
        self.assertGreater(i800, i500)

    def test_zero_altitude_is_solvable(self):
        # At 0 km the required cos(i) is still inside [-1, 1]: about
        # 95.7 deg, no raise.
        inc = ssl.sun_synchronous_inclination(0.0)
        self.assertGreater(inc, math.pi / 2.0)
        self.assertLess(inc, math.pi)
        self.assertAlmostEqual(inc * 180.0 / math.pi, 95.7, places=1)

    def test_no_solution_high_altitude_raises(self):
        # Far beyond GEO the required cos(i) leaves [-1, 1].
        with self.assertRaises(ValueError):
            ssl.sun_synchronous_inclination(50000.0)
        with self.assertRaises(ValueError):
            ssl.sun_synchronous_properties(100000.0)

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            ssl.sun_synchronous_inclination(-1.0)
        with self.assertRaises(ValueError):
            ssl.sun_synchronous_properties(-5.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
