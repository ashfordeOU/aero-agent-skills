#!/usr/bin/env python3
"""Gate 3 contract tests: classical orbital elements (rv2coe) logic.

Stdlib unittest only, offline, no external dependencies. Run with:
python3 scripts/test_keplerian.py

All expected values below are analytic (mu = 1 hand cases, documented
in each docstring). Angles are radians; period in seconds; radii in km.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import keplerian_logic as kl

SQRT3 = math.sqrt(3.0)
SQRT2 = math.sqrt(2.0)
TWO_PI = 2.0 * math.pi


class TestCircularEquatorial(unittest.TestCase):
    def test_elements_mu1(self):
        # Analytic (mu = 1): r = (1,0,0), v = (0,1,0) is a circular
        # equatorial orbit with v^2 = mu/r. h = (0,0,1), |h| = 1;
        # e_vec = (v x h)/1 - r_hat = (1,0,0) - (1,0,0) = 0 so e = 0;
        # energy = 1/2 - 1 = -1/2 so a = -1/(2*(-1/2)) = 1;
        # i = acos(1) = 0; node vector k x h = 0 so equatorial
        # convention: raan = 0, argp = 0; circular equatorial:
        # nu = atan2(r_y, r_x) = 0. Period 2 pi sqrt(1) = 2 pi;
        # rp = ra = 1.
        els = kl.keplerian_elements((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), mu=1.0)
        self.assertAlmostEqual(els["a"], 1.0, places=12)
        self.assertAlmostEqual(els["e"], 0.0, places=12)
        self.assertAlmostEqual(els["i"], 0.0, places=12)
        self.assertAlmostEqual(els["raan"], 0.0, places=12)
        self.assertAlmostEqual(els["argp"], 0.0, places=12)
        self.assertAlmostEqual(els["nu"], 0.0, places=12)
        self.assertAlmostEqual(els["period"], TWO_PI, places=12)
        self.assertAlmostEqual(els["rp"], 1.0, places=12)
        self.assertAlmostEqual(els["ra"], 1.0, places=12)

    def test_h_and_energy_mu1(self):
        # Analytic: h = r x v = (0,0,1); |h| = 1. Energy = -1/2.
        h = kl.specific_angular_momentum((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        self.assertAlmostEqual(kl.norm(h), 1.0, places=12)
        self.assertAlmostEqual(h[2], 1.0, places=12)
        eps = kl.specific_energy((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), mu=1.0)
        self.assertAlmostEqual(eps, -0.5, places=12)


class TestEllipticalInclined(unittest.TestCase):
    def test_periapsis_state_mu1(self):
        # Analytic (mu = 1): r = (0.5,0,0), v = (0, sqrt(3)/2, 3/2).
        # v^2 = 3/4 + 9/4 = 3 = mu(2/0.5 - 1/a) with a = 1, so this is
        # periapsis of an ellipse a = 1, e = 0.5 inclined 60 deg with
        # the node on the x axis. e_vec = (v x h) - r_hat = (0.5,0,0),
        # e = 0.5; energy = 3/2 - 2 = -1/2 so a = 1; h = (0,-0.75,
        # sqrt(3)/4), |h| = sqrt(3)/2, i = acos(1/2) = pi/3; n = k x h
        # = (0.75,0,0) so raan = atan2(0, 0.75) = 0; argp =
        # acos(n.e/(|n|e)) = 0; nu = acos(e.r/(e|r|)) = 0 at periapsis.
        # Period 2 pi; rp = 0.5, ra = 1.5.
        els = kl.keplerian_elements(
            (0.5, 0.0, 0.0), (0.0, SQRT3 / 2.0, 1.5), mu=1.0
        )
        self.assertAlmostEqual(els["a"], 1.0, places=12)
        self.assertAlmostEqual(els["e"], 0.5, places=12)
        self.assertAlmostEqual(els["i"], math.pi / 3.0, places=12)
        self.assertAlmostEqual(els["raan"], 0.0, places=12)
        self.assertAlmostEqual(els["argp"], 0.0, places=12)
        self.assertAlmostEqual(els["nu"], 0.0, places=12)
        self.assertAlmostEqual(els["period"], TWO_PI, places=12)
        self.assertAlmostEqual(els["rp"], 0.5, places=12)
        self.assertAlmostEqual(els["ra"], 1.5, places=12)

    def test_apoapsis_branch_mu1(self):
        # Analytic (mu = 1): r = (1.5,0,0), v = (0, -sqrt(3)/6, -1/2).
        # v^2 = 1/12 + 1/4 = 1/3 = mu(2/1.5 - 1), energy = 1/6 - 2/3
        # = -1/2 so a = 1; e_vec = (v x h) - r_hat = (-0.5,0,0) so
        # e = 0.5; h = (0, 0.75, -sqrt(3)/4), |h| = sqrt(3)/2,
        # i = acos(-1/2) = 2 pi/3; n = k x h = (-0.75,0,0) so
        # raan = atan2(0, -0.75) = pi; argp = acos(1) = 0; nu =
        # acos(-1) = pi (apoapsis branch). rp = 0.5, ra = 1.5.
        els = kl.keplerian_elements(
            (1.5, 0.0, 0.0), (0.0, -SQRT3 / 6.0, -0.5), mu=1.0
        )
        self.assertAlmostEqual(els["a"], 1.0, places=12)
        self.assertAlmostEqual(els["e"], 0.5, places=12)
        self.assertAlmostEqual(els["i"], 2.0 * math.pi / 3.0, places=12)
        self.assertAlmostEqual(els["raan"], math.pi, places=12)
        self.assertAlmostEqual(els["argp"], 0.0, places=12)
        self.assertAlmostEqual(els["nu"], math.pi, places=12)
        self.assertAlmostEqual(els["period"], TWO_PI, places=12)

    def test_equatorial_eccentric_mu1(self):
        # Analytic (mu = 1): r = (0.5,0,0), v = (0, sqrt(3), 0) lies in
        # the equatorial plane. v^2 = 3, energy = 3/2 - 2 = -1/2,
        # a = 1; h = (0,0,sqrt(3)/2), i = acos(1) = 0; node vector is
        # zero so equatorial conventions: raan = 0, argp = atan2(e_y,
        # e_x) = atan2(0, 0.5) = 0; e_vec = (v x h) - r_hat = (0.5,0,0),
        # e = 0.5; nu = acos(e.r/(e|r|)) = 0 at periapsis.
        els = kl.keplerian_elements((0.5, 0.0, 0.0), (0.0, SQRT3, 0.0), mu=1.0)
        self.assertAlmostEqual(els["a"], 1.0, places=12)
        self.assertAlmostEqual(els["e"], 0.5, places=12)
        self.assertAlmostEqual(els["i"], 0.0, places=12)
        self.assertAlmostEqual(els["raan"], 0.0, places=12)
        self.assertAlmostEqual(els["argp"], 0.0, places=12)
        self.assertAlmostEqual(els["nu"], 0.0, places=12)

    def test_circular_inclined_mu1(self):
        # Analytic (mu = 1): r = (1,0,0), v = (0, sqrt(2)/2, sqrt(2)/2)
        # with v^2 = 1 is circular at 45 deg. h = (0, -sqrt(2)/2,
        # sqrt(2)/2), |h| = 1, i = acos(sqrt(2)/2) = pi/4; n = k x h =
        # (sqrt(2)/2, 0, 0) so raan = 0; circular convention argp = 0
        # and nu = acos(n.r/(|n||r|)) = 0; a = 1, e = 0.
        els = kl.keplerian_elements(
            (1.0, 0.0, 0.0), (0.0, SQRT2 / 2.0, SQRT2 / 2.0), mu=1.0
        )
        self.assertAlmostEqual(els["a"], 1.0, places=12)
        self.assertAlmostEqual(els["e"], 0.0, places=12)
        self.assertAlmostEqual(els["i"], math.pi / 4.0, places=12)
        self.assertAlmostEqual(els["raan"], 0.0, places=12)
        self.assertAlmostEqual(els["argp"], 0.0, places=12)
        self.assertAlmostEqual(els["nu"], 0.0, places=12)


class TestEarthScale(unittest.TestCase):
    def test_circular_period_7000km(self):
        # Analytic: circular orbit r = 7000 km with v = sqrt(mu/r).
        # a = 7000 km, e = 0, period T = 2 pi sqrt(7000^3/mu) with
        # mu = 398600.4418 km^3/s^2. 7000^3/mu = 860510.84, sqrt =
        # 927.6371, T = 2 pi * 927.6371 = 5828.5 s.
        v = math.sqrt(kl.MU / 7000.0)
        els = kl.keplerian_elements((7000.0, 0.0, 0.0), (0.0, v, 0.0))
        self.assertAlmostEqual(els["a"], 7000.0, places=6)
        self.assertAlmostEqual(els["e"], 0.0, places=10)
        self.assertAlmostEqual(els["i"], 0.0, places=10)
        self.assertAlmostEqual(els["period"], 5828.5, places=1)
        self.assertAlmostEqual(els["period"], TWO_PI * math.sqrt(7000.0**3 / kl.MU), places=9)
        self.assertAlmostEqual(els["rp"], 7000.0, places=6)
        self.assertAlmostEqual(els["ra"], 7000.0, places=6)

    def test_period_helper(self):
        # Analytic: T = 2 pi sqrt(a^3/mu); at a = 42164 km (GEO) with
        # mu = 398600.4418: 42164^3/mu = 188056192.1, sqrt = 13713.72,
        # T = 86163.6 s (about one sidereal day, 86164.1 s).
        t = kl.orbital_period(42164.0)
        self.assertAlmostEqual(t, 86163.6, places=1)


class TestValueErrors(unittest.TestCase):
    def test_rectilinear_raises(self):
        # Radial trajectory: r and v parallel so h = 0.
        with self.assertRaises(ValueError):
            kl.specific_angular_momentum((1.0, 0.0, 0.0), (1.0, 0.0, 0.0))
        with self.assertRaises(ValueError):
            kl.keplerian_elements((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), mu=1.0)

    def test_parabolic_raises(self):
        # Analytic (mu = 1): v = (0, sqrt(2), 0) at r = (1,0,0) gives
        # energy = 2/2 - 1 = 0: parabolic, semimajor axis undefined.
        with self.assertRaises(ValueError):
            kl.semimajor_axis((1.0, 0.0, 0.0), (0.0, SQRT2, 0.0), mu=1.0)
        with self.assertRaises(ValueError):
            kl.keplerian_elements((1.0, 0.0, 0.0), (0.0, SQRT2, 0.0), mu=1.0)

    def test_hyperbolic_raises(self):
        # Analytic (mu = 1): v = (0, 2, 0) at r = (1,0,0) gives energy
        # = 4/2 - 1 = 1 > 0: hyperbolic, a = -1/2, e = 3.
        self.assertAlmostEqual(
            kl.semimajor_axis((1.0, 0.0, 0.0), (0.0, 2.0, 0.0), mu=1.0),
            -0.5,
            places=12,
        )
        with self.assertRaises(ValueError):
            kl.keplerian_elements((1.0, 0.0, 0.0), (0.0, 2.0, 0.0), mu=1.0)
        with self.assertRaises(ValueError):
            kl.orbital_period(-0.5)
        with self.assertRaises(ValueError):
            kl.periapsis_apoapsis_radii(-0.5, 3.0)
        with self.assertRaises(ValueError):
            kl.periapsis_apoapsis_radii(1.0, 1.0)  # e >= 1

    def test_zero_radius_raises(self):
        with self.assertRaises(ValueError):
            kl.specific_energy((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), mu=1.0)
        with self.assertRaises(ValueError):
            kl.eccentricity_vector((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), mu=1.0)

    def test_bad_mu_raises(self):
        with self.assertRaises(ValueError):
            kl.keplerian_elements((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), mu=0.0)
        with self.assertRaises(ValueError):
            kl.orbital_period(7000.0, mu=-1.0)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            kl.keplerian_elements((1.0, 2.0), (0.0, 1.0, 0.0), mu=1.0)
        with self.assertRaises(ValueError):
            kl.keplerian_elements(
                (float("nan"), 0.0, 0.0), (0.0, 1.0, 0.0), mu=1.0
            )
        with self.assertRaises(ValueError):
            kl.true_anomaly(
                (0.0, 0.0, 1.0), (0.5, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 1.0, 0.0)
            )


class TestPackShape(unittest.TestCase):
    def test_dict_keys_and_conventions(self):
        els = kl.keplerian_elements((0.5, 0.0, 0.0), (0.0, SQRT3 / 2.0, 1.5), mu=1.0)
        for key in ("h", "n", "e_vec", "a", "e", "i", "raan", "argp", "nu",
                    "period", "rp", "ra"):
            self.assertIn(key, els)
        # Consistency: period matches 2 pi sqrt(a^3/mu); rp/ra match
        # a (1 - e) and a (1 + e); node vector is perpendicular to h.
        self.assertAlmostEqual(
            els["period"], TWO_PI * math.sqrt(els["a"] ** 3 / 1.0), places=12
        )
        self.assertAlmostEqual(els["rp"], els["a"] * (1.0 - els["e"]), places=12)
        self.assertAlmostEqual(els["ra"], els["a"] * (1.0 + els["e"]), places=12)
        self.assertAlmostEqual(kl.dot(els["n"], els["h"]), 0.0, places=12)
        # Angles stay in their documented ranges.
        self.assertGreaterEqual(els["i"], 0.0)
        self.assertLessEqual(els["i"], math.pi)
        self.assertGreaterEqual(els["raan"], -math.pi)
        self.assertLessEqual(els["raan"], math.pi)
        self.assertGreaterEqual(els["argp"], 0.0)
        self.assertLess(els["argp"], TWO_PI)
        self.assertGreaterEqual(els["nu"], 0.0)
        self.assertLess(els["nu"], TWO_PI)


if __name__ == "__main__":
    unittest.main(verbosity=2)
