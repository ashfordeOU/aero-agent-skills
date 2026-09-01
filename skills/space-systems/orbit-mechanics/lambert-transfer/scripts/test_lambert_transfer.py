#!/usr/bin/env python3
"""Gate 3 contract test: Lambert transfer.

Exercises scripts/lambert_transfer_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (p-iteration Lambert solver:
two position vectors and a transfer time in, orbit elements and endpoint
velocity vectors out; short-way and long-way branches; multi-revolution
extension; invalid inputs raise ValueError).

Anchors (mu = 398600.4418 km^3/s^2, distances in km):
- 180-degree transfer at 7000 km radius (r2 = -r1): the Hohmann case.
  Transfer time 2914.26 s equals half the Hohmann ellipse period and
  delta-v is zero (the Hohmann total for equal radii).
- 180-degree low-earth (6878 km) to geostationary (42164 km) transfer:
  the Hohmann transfer; time 19106.81 s, total delta-v 3.81609 km/s
  (matches the Hohmann budget within 1 percent), a = 24521 km,
  e = 0.719506.
- 90-degree transfer between two different radii (r1m = 7210.29 km,
  r2m = 10499.27 km, sweep exactly 90 degrees): the solver must recover
  the generating ellipse (a = 12000 km, e = 0.4) and endpoint speeds
  consistent with vis-viva and angular momentum.
- 120-degree short-way and 240-degree long-way arcs of the same ellipse
  (a = 20000 km, e = 0.4, nu1 = 30 deg): both branches must recover the
  ellipse and the endpoint velocities.
- Multi-revolution extension: a time of flight beyond the direct-arc
  range returns an M-revolution orbit with t_arc + M * period = tof.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lambert_transfer_logic as lt  # noqa: E402

MU = lt.MU_EARTH
R = 7000.0        # circular orbit radius, km
R1 = 6878.0       # low earth orbit radius, km
R2 = 42164.0      # geostationary orbit radius, km
HALF_DAY = 86164.0  # sidereal day, s (reference only)


def vmag(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def hmag(r, v):
    cx = r[1] * v[2] - r[2] * v[1]
    cy = r[2] * v[0] - r[0] * v[2]
    cz = r[0] * v[1] - r[1] * v[0]
    return math.sqrt(cx * cx + cy * cy + cz * cz)


class Hohmann180SameRadiusTest(unittest.TestCase):
    """180-degree transfer at equal radii: half a circular orbit coast."""

    def test_transfer_time_is_half_the_hohmann_period(self):
        tof = math.pi * math.sqrt(R ** 3 / MU)
        res = lt.lambert_solve((R, 0.0, 0.0), (-R, 0.0, 0.0), tof)
        self.assertAlmostEqual(res["t"], tof, delta=0.01)
        self.assertAlmostEqual(res["t"], 0.5 * res["period"], delta=0.01)
        self.assertAlmostEqual(res["t"], 2914.258, delta=0.05)

    def test_delta_v_matches_hohmann_total(self):
        # The Hohmann total for equal radii is zero: the coast solution.
        tof = math.pi * math.sqrt(R ** 3 / MU)
        res = lt.lambert_solve((R, 0.0, 0.0), (-R, 0.0, 0.0), tof)
        self.assertLess(abs(res["delta_v"]), 1e-9)
        self.assertAlmostEqual(res["e"], 0.0, places=9)
        self.assertAlmostEqual(res["a"], R, places=3)

    def test_endpoint_speeds_are_circular(self):
        tof = math.pi * math.sqrt(R ** 3 / MU)
        res = lt.lambert_solve((R, 0.0, 0.0), (-R, 0.0, 0.0), tof)
        self.assertAlmostEqual(vmag(res["v1"]), lt.circular_velocity(R), places=4)
        self.assertAlmostEqual(vmag(res["v2"]), lt.circular_velocity(R), places=4)


class Hohmann180LeoGeoTest(unittest.TestCase):
    """180-degree LEO-to-GEO transfer: the Hohmann reference."""

    def setUp(self):
        a = 0.5 * (R1 + R2)
        self.tof = math.pi * math.sqrt(a ** 3 / MU)
        self.res = lt.lambert_solve((R1, 0.0, 0.0), (-R2, 0.0, 0.0), self.tof)

    def test_transfer_time(self):
        self.assertAlmostEqual(self.res["t"], 19106.813, delta=1.0)
        self.assertAlmostEqual(self.res["t"], 0.5 * self.res["period"], delta=1.0)

    def test_delta_v_matches_hohmann_total_within_one_percent(self):
        a = self.res["a"]
        vc1 = lt.circular_velocity(R1)
        vc2 = lt.circular_velocity(R2)
        vp = lt.vis_viva_velocity(R1, a)
        va = lt.vis_viva_velocity(R2, a)
        hohmann_total = (vp - vc1) + (vc2 - va)
        self.assertAlmostEqual(self.res["delta_v"], 3.81609, delta=0.04)
        self.assertLess(
            abs(self.res["delta_v"] - hohmann_total) / hohmann_total, 0.01
        )

    def test_transfer_ellipse_elements(self):
        self.assertAlmostEqual(self.res["a"], 24521.0, delta=0.5)
        self.assertAlmostEqual(self.res["e"], 0.719506, places=4)
        self.assertAlmostEqual(self.res["p"], 2.0 * R1 * R2 / (R1 + R2), places=1)

    def test_endpoint_speeds_match_vis_viva(self):
        a = self.res["a"]
        self.assertAlmostEqual(vmag(self.res["v1"]), lt.vis_viva_velocity(R1, a), places=4)
        self.assertAlmostEqual(vmag(self.res["v2"]), lt.vis_viva_velocity(R2, a), places=4)


class NonDegenerate90DegreeTest(unittest.TestCase):
    """90-degree transfer between two different radii: recovery of the
    generating ellipse plus energy/vis-viva and angular momentum checks."""

    def setUp(self):
        # Generating ellipse: a = 12000 km, e = 0.4, nu1 = 0.1 rad,
        # nu2 = nu1 + pi/2 (sweep exactly 90 degrees).
        self.a = 12000.0
        self.e = 0.4
        p = self.a * (1.0 - self.e * self.e)
        self.nu1 = 0.1
        self.nu2 = self.nu1 + math.pi / 2.0
        self.r1m = p / (1.0 + self.e * math.cos(self.nu1))
        self.r2m = p / (1.0 + self.e * math.cos(self.nu2))
        r1 = (self.r1m * math.cos(self.nu1), self.r1m * math.sin(self.nu1), 0.0)
        r2 = (self.r2m * math.cos(self.nu2), self.r2m * math.sin(self.nu2), 0.0)
        self.r1 = r1
        self.r2 = r2
        self.tof = lt.analytic_time(self.a, self.e, self.nu1, self.nu2)
        self.res = lt.lambert_solve(r1, r2, self.tof, direction="short")

    def test_recovery_of_semimajor_axis(self):
        self.assertAlmostEqual(self.res["a"], self.a, delta=0.001 * self.a)

    def test_recovery_of_eccentricity(self):
        self.assertAlmostEqual(self.res["e"], self.e, delta=0.001)

    def test_recovery_of_true_anomalies(self):
        self.assertAlmostEqual(self.res["nu1"], self.nu1, delta=1e-6)
        self.assertAlmostEqual(self.res["nu2"], self.nu2, delta=1e-6)

    def test_energy_vis_viva_consistency(self):
        # |v|^2 = mu * (2 / r - 1 / a) at both endpoints.
        v1sq = vmag(self.res["v1"]) ** 2
        v2sq = vmag(self.res["v2"]) ** 2
        self.assertAlmostEqual(
            v1sq, lt.vis_viva_velocity(self.r1m, self.res["a"]) ** 2,
            delta=1e-6 * v1sq,
        )
        self.assertAlmostEqual(
            v2sq, lt.vis_viva_velocity(self.r2m, self.res["a"]) ** 2,
            delta=1e-6 * v2sq,
        )

    def test_angular_momentum_consistency(self):
        h1 = hmag(self.r1, self.res["v1"])
        h2 = hmag(self.r2, self.res["v2"])
        h_ref = math.sqrt(MU * self.res["p"])
        self.assertAlmostEqual(h1, h_ref, delta=0.01)
        self.assertAlmostEqual(h2, h_ref, delta=0.01)

    def test_time_of_flight_matches(self):
        self.assertAlmostEqual(self.res["t"], self.tof, delta=0.01)


class ShortWayRoundTripTest(unittest.TestCase):
    """120-degree short-way arc: solver must reproduce the ellipse."""

    def setUp(self):
        self.a = 20000.0
        self.e = 0.4
        p = self.a * (1.0 - self.e * self.e)
        self.nu1 = math.radians(30.0)
        self.nu2 = math.radians(150.0)
        r1m = p / (1.0 + self.e * math.cos(self.nu1))
        r2m = p / (1.0 + self.e * math.cos(self.nu2))
        self.r1 = (r1m * math.cos(self.nu1), r1m * math.sin(self.nu1), 0.0)
        self.r2 = (r2m * math.cos(self.nu2), r2m * math.sin(self.nu2), 0.0)
        self.tof = lt.analytic_time(self.a, self.e, self.nu1, self.nu2)
        self.res = lt.lambert_solve(self.r1, self.r2, self.tof, direction="short")

    def test_recovery(self):
        self.assertAlmostEqual(self.res["a"], self.a, delta=0.001 * self.a)
        self.assertAlmostEqual(self.res["e"], self.e, delta=0.001)
        self.assertAlmostEqual(self.res["t"], self.tof, delta=0.01)
        self.assertAlmostEqual(self.res["delta"], math.radians(120.0), places=9)

    def test_endpoint_velocities(self):
        # Analytic velocities: v_r = sqrt(mu/p) e sin nu, v_theta =
        # sqrt(mu/p) (1 + e cos nu), resolved on rhat and the transverse.
        p = self.res["p"]
        vp = math.sqrt(MU / p)
        vr1 = vp * self.e * math.sin(self.nu1)
        vt1 = vp * (1.0 + self.e * math.cos(self.nu1))
        vr2 = vp * self.e * math.sin(self.nu2)
        vt2 = vp * (1.0 + self.e * math.cos(self.nu2))
        v1x = vr1 * math.cos(self.nu1) - vt1 * math.sin(self.nu1)
        v1y = vr1 * math.sin(self.nu1) + vt1 * math.cos(self.nu1)
        v2x = vr2 * math.cos(self.nu2) - vt2 * math.sin(self.nu2)
        v2y = vr2 * math.sin(self.nu2) + vt2 * math.cos(self.nu2)
        for got, want in zip(self.res["v1"], (v1x, v1y, 0.0)):
            self.assertAlmostEqual(got, want, delta=0.01)
        for got, want in zip(self.res["v2"], (v2x, v2y, 0.0)):
            self.assertAlmostEqual(got, want, delta=0.01)


class LongWayRoundTripTest(unittest.TestCase):
    """240-degree long-way arc (nu1 = 30 deg to nu2 = 270 deg) of the
    same ellipse: the long-way branch must reproduce it."""

    def setUp(self):
        self.a = 20000.0
        self.e = 0.4
        p = self.a * (1.0 - self.e * self.e)
        self.nu1 = math.radians(30.0)
        self.nu2 = math.radians(270.0)
        r1m = p / (1.0 + self.e * math.cos(self.nu1))
        r2m = p / (1.0 + self.e * math.cos(self.nu2))
        self.r1 = (r1m * math.cos(self.nu1), r1m * math.sin(self.nu1), 0.0)
        self.r2 = (r2m * math.cos(self.nu2), r2m * math.sin(self.nu2), 0.0)
        self.tof = lt.analytic_time(self.a, self.e, self.nu1, self.nu2)
        self.res = lt.lambert_solve(self.r1, self.r2, self.tof, direction="long")

    def test_recovery(self):
        self.assertAlmostEqual(self.res["a"], self.a, delta=0.001 * self.a)
        self.assertAlmostEqual(self.res["e"], self.e, delta=0.001)
        self.assertAlmostEqual(self.res["t"], self.tof, delta=0.01)
        self.assertAlmostEqual(self.res["delta"], math.radians(240.0), places=9)
        self.assertAlmostEqual(self.res["nu2"], self.nu2, delta=1e-6)

    def test_vis_viva_consistency(self):
        v1sq = vmag(self.res["v1"]) ** 2
        v2sq = vmag(self.res["v2"]) ** 2
        self.assertAlmostEqual(
            v1sq, lt.vis_viva_velocity(self.res["r1m"], self.res["a"]) ** 2,
            delta=1e-6 * v1sq,
        )
        self.assertAlmostEqual(
            v2sq, lt.vis_viva_velocity(self.res["r2m"], self.res["a"]) ** 2,
            delta=1e-6 * v2sq,
        )


class MultiRevolutionTest(unittest.TestCase):
    """Multi-revolution extension: tof beyond the direct arc returns an
    M-revolution orbit with t_arc + M * period = tof."""

    def setUp(self):
        # Near-equal radii geometry with a bounded direct-arc range.
        self.r1 = (7000.0, 0.0, 0.0)
        dg = math.radians(120.0)
        self.r2 = (7100.0 * math.cos(dg), 7100.0 * math.sin(dg), 0.0)
        self.tof = 1.0e7

    def test_direct_arc_is_single_revolution(self):
        res = lt.lambert_solve(self.r1, self.r2, self.tof, max_revs=0)
        self.assertEqual(res["revs"], 0)
        self.assertAlmostEqual(res["t"], self.tof, delta=1.0)

    def test_multi_revolution_returns_m_rev_orbit(self):
        res = lt.lambert_solve(self.r1, self.r2, self.tof, max_revs=1)
        self.assertEqual(res["revs"], 1)
        # The returned orbit satisfies t_arc + M * period = tof.
        self.assertLess(
            abs(res["t"] + res["revs"] * res["period"] - self.tof) / self.tof,
            1e-9,
        )

    def test_multi_revolution_vis_viva(self):
        res = lt.lambert_solve(self.r1, self.r2, self.tof, max_revs=1)
        v1sq = vmag(res["v1"]) ** 2
        self.assertAlmostEqual(
            v1sq, lt.vis_viva_velocity(7000.0, res["a"]) ** 2,
            delta=1e-6 * v1sq,
        )


class CircularCoastTest(unittest.TestCase):
    """Equal-radii transfer with the circular arc time: the solver must
    return the circular orbit (e = 0, zero delta-v)."""

    def test_circular_arc_coast(self):
        dg = math.radians(120.0)
        t_circ = math.sqrt(R ** 3 / MU) * dg
        r2 = (R * math.cos(dg), R * math.sin(dg), 0.0)
        res = lt.lambert_solve((R, 0.0, 0.0), r2, t_circ)
        self.assertAlmostEqual(res["t"], t_circ, delta=0.01)
        self.assertAlmostEqual(res["e"], 0.0, places=9)
        self.assertAlmostEqual(res["a"], R, places=3)
        self.assertLess(abs(res["delta_v"]), 1e-9)


class BranchDirectionTest(unittest.TestCase):
    """Short-way and long-way branches differ for the same geometry."""

    def test_branches_differ(self):
        dg = math.radians(90.0)
        r1 = (7000.0, 0.0, 0.0)
        r2 = (10000.0 * math.cos(dg), 10000.0 * math.sin(dg), 0.0)
        tof = 4500.0
        short = lt.lambert_solve(r1, r2, tof, direction="short")
        long = lt.lambert_solve(r1, r2, tof, direction="long")
        self.assertAlmostEqual(short["delta"], math.radians(90.0), places=9)
        self.assertAlmostEqual(long["delta"], math.radians(270.0), places=9)
        self.assertNotAlmostEqual(short["a"], long["a"], places=1)


class InvalidInputTest(unittest.TestCase):
    """Invalid inputs raise ValueError."""

    def test_zero_position_vector(self):
        with self.assertRaises(ValueError):
            lt.lambert_solve((0.0, 0.0, 0.0), (R, 0.0, 0.0), 100.0)
        with self.assertRaises(ValueError):
            lt.lambert_solve((R, 0.0, 0.0), (0.0, 0.0, 0.0), 100.0)

    def test_collinear_positions(self):
        with self.assertRaises(ValueError):
            lt.lambert_solve((R, 0.0, 0.0), (2.0 * R, 0.0, 0.0), 100.0)

    def test_non_positive_time_of_flight(self):
        with self.assertRaises(ValueError):
            lt.lambert_solve((R, 0.0, 0.0), (-R, 0.0, 0.0), 0.0)
        with self.assertRaises(ValueError):
            lt.lambert_solve((R, 0.0, 0.0), (-R, 0.0, 0.0), -10.0)

    def test_non_positive_mu(self):
        with self.assertRaises(ValueError):
            lt.lambert_solve((R, 0.0, 0.0), (-R, 0.0, 0.0), 100.0, mu=-1.0)

    def test_invalid_direction(self):
        with self.assertRaises(ValueError):
            lt.lambert_solve((R, 0.0, 0.0), (-R, 0.0, 0.0), 100.0, direction="up")

    def test_too_small_time_of_flight(self):
        dg = 1.0  # radians
        r2 = (R * math.cos(dg), R * math.sin(dg), 0.0)
        with self.assertRaises(ValueError):
            lt.lambert_solve((R, 0.0, 0.0), r2, 1.0)

    def test_negative_max_revs(self):
        with self.assertRaises(ValueError):
            lt.lambert_solve((R, 0.0, 0.0), (-R, 0.0, 0.0), 100.0, max_revs=-1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
