#!/usr/bin/env python3
"""Gate 3 contract test: two-body orbital mechanics.

Exercises scripts/orbit_dynamics_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - vis-viva speed (circular
case r == a gives sqrt(mu/r); LEO at 6878 km about 7.6-7.7 km/s);
Hohmann transfer delta-v and transfer time between coplanar circular
orbits, LEO-to-GEO total in the 3500-4300 m/s sanity band; J2 drift
flag both branches; invalid inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import orbit_dynamics_logic as od  # noqa: E402

R_LEO = 6.878e6  # m, LEO at 500 km altitude
R_GEO = 4.2164e7  # m, GEO radius


class VisVivaTest(unittest.TestCase):
    def test_circular_orbit_speed(self):
        expected = math.sqrt(od.MU_EARTH / R_LEO)
        self.assertAlmostEqual(od.vis_viva_velocity(R_LEO, R_LEO), expected, places=3)

    def test_leo_speed_band(self):
        v = od.vis_viva_velocity(R_LEO, R_LEO)
        self.assertTrue(7.5e3 <= v <= 7.8e3, "v = %r m/s" % v)

    def test_elliptical_perigee_above_circular(self):
        a = 1.2 * R_LEO
        self.assertGreater(od.vis_viva_velocity(R_LEO, a), math.sqrt(od.MU_EARTH / R_LEO))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            od.vis_viva_velocity(0.0, 7.0e6)
        with self.assertRaises(ValueError):
            od.vis_viva_velocity(7.0e6, 0.0)
        with self.assertRaises(ValueError):
            od.vis_viva_velocity(-1.0, 7.0e6)


class HohmannDeltaVTest(unittest.TestCase):
    def test_leo_to_geo_total_in_band(self):
        dv1, dv2, total = od.hohmann_delta_v(R_LEO, R_GEO)
        self.assertTrue(od.leo_to_geo_sanity(total), "total %r m/s" % total)
        self.assertGreater(dv1, 0)
        self.assertGreater(dv2, 0)

    def test_dv_total_is_sum(self):
        dv1, dv2, _ = od.hohmann_delta_v(R_LEO, R_GEO)
        _, _, total = od.hohmann_delta_v(R_LEO, R_GEO)
        self.assertAlmostEqual(total, dv1 + dv2, places=6)

    def test_transfer_is_reversible_in_magnitude(self):
        _, _, up = od.hohmann_delta_v(R_LEO, R_GEO)
        _, _, down = od.hohmann_delta_v(R_GEO, R_LEO)
        self.assertAlmostEqual(abs(up), abs(down), places=6)

    def test_sanity_band_edges(self):
        self.assertTrue(od.leo_to_geo_sanity(3500.0))
        self.assertTrue(od.leo_to_geo_sanity(4300.0))
        self.assertFalse(od.leo_to_geo_sanity(3499.0))
        self.assertFalse(od.leo_to_geo_sanity(4301.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            od.hohmann_delta_v(R_LEO, R_LEO)
        with self.assertRaises(ValueError):
            od.hohmann_delta_v(0.0, R_GEO)
        with self.assertRaises(ValueError):
            od.hohmann_delta_v(R_LEO, -1.0)


class HohmannTransferTimeTest(unittest.TestCase):
    def test_leo_to_geo_time_sane(self):
        t = od.hohmann_transfer_time(R_LEO, R_GEO)
        self.assertGreater(t, 15000.0)
        self.assertLess(t, 25000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            od.hohmann_transfer_time(0.0, R_GEO)
        with self.assertRaises(ValueError):
            od.hohmann_transfer_time(R_LEO, -2.0)


class J2DriftFlagTest(unittest.TestCase):
    def test_within_allowed_is_ok(self):
        self.assertEqual(od.j2_drift_flag(0.03), "ok")
        self.assertEqual(od.j2_drift_flag(-0.03), "ok")
        self.assertEqual(od.j2_drift_flag(0.05), "ok")

    def test_exceeding_allowed_flags(self):
        self.assertEqual(od.j2_drift_flag(0.051), "j2-drift check")
        self.assertEqual(od.j2_drift_flag(-0.1), "j2-drift check")


if __name__ == "__main__":
    unittest.main(verbosity=2)
