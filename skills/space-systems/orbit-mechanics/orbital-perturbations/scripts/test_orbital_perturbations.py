#!/usr/bin/env python3
"""Gate 3 contract tests: J2 secular orbital perturbation logic.

Stdlib unittest only, offline, no external dependencies. Run with:
python3 scripts/test_orbital_perturbations.py

Anchors below were verified against a J2 RK4 propagation of the
circular orbit (RAAN and argument-of-perigee drift within 1 percent,
ascending-node crossing intervals within 0.2 percent).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import orbital_perturbations_logic as opl

DEG = math.pi / 180.0
RAD2DEG = 180.0 / math.pi
A_500 = 6871000.0
A_GEO = 42164000.0
N_500 = 1.108508e-3


class TestSemimajorAxis(unittest.TestCase):
    def test_semimajor_axis_500km(self):
        self.assertAlmostEqual(opl.semimajor_axis(500.0), A_500, places=3)

    def test_semimajor_axis_negative_raises(self):
        with self.assertRaises(ValueError):
            opl.semimajor_axis(-1.0)


class TestMeanMotionAndPeriod(unittest.TestCase):
    def test_mean_motion_500km_anchor(self):
        # a = 6871000 m, n = sqrt(3.986004418e14 / 6871000**3)
        # = 1.108508e-3 rad/s.
        n = opl.mean_motion(A_500)
        self.assertAlmostEqual(n, N_500, places=9)

    def test_mean_motion_decreases_with_altitude(self):
        self.assertGreater(
            opl.mean_motion(opl.semimajor_axis(300.0)),
            opl.mean_motion(opl.semimajor_axis(900.0)),
        )

    def test_keplerian_period_500km_anchor(self):
        # T_K = 2 pi / n = 5668.14 s (94.47 min) at 500 km.
        self.assertAlmostEqual(opl.keplerian_period(A_500), 5668.14, places=2)

    def test_nonpositive_axis_raises(self):
        with self.assertRaises(ValueError):
            opl.mean_motion(0.0)
        with self.assertRaises(ValueError):
            opl.mean_motion(-5.0)
        with self.assertRaises(ValueError):
            opl.keplerian_period(0.0)


class TestRaanDriftRate(unittest.TestCase):
    def test_500km_30deg_anchor(self):
        # om_dot = -1.5 n J2 (Re/a)^2 cos(30 deg) = -1.3403e-6 rad/s
        # = -6.6352 deg/day.
        rate = opl.raan_drift_rate(N_500, A_500, 30.0 * DEG)
        self.assertAlmostEqual(rate, -1.3403397e-6, places=10)
        self.assertAlmostEqual(
            opl.rad_per_s_to_deg_per_day(rate), -6.6352, places=4
        )

    def test_prograde_negative_polar_zero_retrograde_positive(self):
        self.assertLess(opl.raan_drift_rate(N_500, A_500, 30.0 * DEG), 0.0)
        self.assertAlmostEqual(
            opl.raan_drift_rate(N_500, A_500, 90.0 * DEG), 0.0, places=15
        )
        self.assertGreater(opl.raan_drift_rate(N_500, A_500, 120.0 * DEG), 0.0)

    def test_drift_grows_as_semimajor_axis_shrinks(self):
        # |om_dot| scales as a^-3.5: lower altitude, faster drift.
        n400 = opl.mean_motion(opl.semimajor_axis(400.0))
        n800 = opl.mean_motion(opl.semimajor_axis(800.0))
        self.assertGreater(
            abs(opl.raan_drift_rate(n400, opl.semimajor_axis(400.0), 30.0 * DEG)),
            abs(opl.raan_drift_rate(n800, opl.semimajor_axis(800.0), 30.0 * DEG)),
        )

    def test_geo_drift_is_about_570x_smaller(self):
        # At GEO the RAAN drift is -0.0116 deg/day vs -6.6352 deg/day
        # at 500 km (about 572x smaller, a^-3.5 scaling).
        n_geo = opl.mean_motion(A_GEO)
        rate_geo = opl.raan_drift_rate(n_geo, A_GEO, 30.0 * DEG)
        self.assertAlmostEqual(
            opl.rad_per_s_to_deg_per_day(rate_geo), -0.0116, places=4
        )
        rate_leo = opl.raan_drift_rate(N_500, A_500, 30.0 * DEG)
        self.assertGreater(abs(rate_leo) / abs(rate_geo), 500.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            opl.raan_drift_rate(-N_500, A_500, 30.0 * DEG)
        with self.assertRaises(ValueError):
            opl.raan_drift_rate(N_500, 0.0, 30.0 * DEG)
        with self.assertRaises(ValueError):
            opl.raan_drift_rate(N_500, A_500, -0.1)
        with self.assertRaises(ValueError):
            opl.raan_drift_rate(N_500, A_500, math.pi + 0.1)


class TestArgPerigeeDrift(unittest.TestCase):
    def test_500km_30deg_anchor(self):
        # w_dot = 0.75 n J2 (Re/a)^2 (5 cos^2(30) - 1) = +2.1281e-6
        # rad/s = +10.5347 deg/day.
        rate = opl.arg_perigee_drift_rate(N_500, A_500, 30.0 * DEG)
        self.assertAlmostEqual(rate, 2.1280752e-6, places=10)
        self.assertAlmostEqual(
            opl.rad_per_s_to_deg_per_day(rate), 10.5347, places=4
        )

    def test_zero_at_critical_inclination(self):
        # 5 cos^2(i) - 1 = 0 at i = 63.435 deg.
        i_crit = opl.critical_inclination_rad()
        self.assertAlmostEqual(i_crit * RAD2DEG, 63.435, places=3)
        self.assertAlmostEqual(
            opl.arg_perigee_drift_rate(N_500, A_500, i_crit), 0.0, places=14
        )

    def test_sign_flips_around_critical_inclination(self):
        # Below 63.435 deg the perigee advances, between 63.435 and
        # 116.565 deg it regresses, above 116.565 deg it advances.
        self.assertGreater(opl.arg_perigee_drift_rate(N_500, A_500, 30.0 * DEG), 0.0)
        self.assertLess(opl.arg_perigee_drift_rate(N_500, A_500, 80.0 * DEG), 0.0)
        self.assertGreater(opl.arg_perigee_drift_rate(N_500, A_500, 120.0 * DEG), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            opl.arg_perigee_drift_rate(N_500, A_500, -0.1)
        with self.assertRaises(ValueError):
            opl.arg_perigee_drift_rate(0.0, A_500, 30.0 * DEG)
        with self.assertRaises(ValueError):
            opl.arg_perigee_drift_rate(N_500, -1.0, 30.0 * DEG)


class TestNodalPeriodChange(unittest.TestCase):
    def test_500km_30deg_anchor(self):
        # T_n = 2 pi / (n + om_dot) = 5675.01 s, T_K = 5668.14 s,
        # so dT = +6.86 s (prograde period lengthens).
        om_dot = opl.raan_drift_rate(N_500, A_500, 30.0 * DEG)
        self.assertAlmostEqual(opl.nodal_period(N_500, om_dot), 5675.01, places=2)
        self.assertAlmostEqual(
            opl.nodal_period_change(N_500, om_dot), 6.86, places=2
        )

    def test_polar_orbit_no_change(self):
        om_dot = opl.raan_drift_rate(N_500, A_500, 90.0 * DEG)
        self.assertAlmostEqual(
            opl.nodal_period_change(N_500, om_dot), 0.0, places=12
        )

    def test_retrograde_period_shortens(self):
        # Sun-synchronous 97.4 deg: om_dot > 0, dT = -1.02 s.
        om_dot = opl.raan_drift_rate(N_500, A_500, 97.4 * DEG)
        self.assertLess(opl.nodal_period_change(N_500, om_dot), 0.0)
        self.assertAlmostEqual(
            opl.nodal_period_change(N_500, om_dot), -1.02, places=2
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            opl.nodal_period(0.0, 0.0)
        with self.assertRaises(ValueError):
            opl.nodal_period(N_500, -2.0 * N_500)  # n + om_dot <= 0
        with self.assertRaises(ValueError):
            opl.nodal_period_change(N_500, -2.0 * N_500)


class TestDraconiticPeriod(unittest.TestCase):
    def test_500km_30deg_anchor(self):
        # T_d = 2 pi / (M_dot + w_dot) = 5652.36 s, about 15.8 s
        # shorter than the Keplerian period.
        t_d = opl.draconitic_period(N_500, A_500, 30.0 * DEG)
        self.assertAlmostEqual(t_d, 5652.36, places=2)
        self.assertLess(t_d, opl.keplerian_period(A_500))

    def test_polar_orbit_draconitic_longer(self):
        # At i = 90 deg the argument-of-latitude rate is below n, so
        # T_d = 5676.07 s exceeds the Keplerian period.
        t_d = opl.draconitic_period(N_500, A_500, 90.0 * DEG)
        self.assertAlmostEqual(t_d, 5676.07, places=2)
        self.assertGreater(t_d, opl.keplerian_period(A_500))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            opl.draconitic_period(N_500, 0.0, 30.0 * DEG)
        with self.assertRaises(ValueError):
            opl.draconitic_period(N_500, A_500, math.pi + 1.0)


class TestMagnitudeAndProperties(unittest.TestCase):
    def test_ratio_anchors_500km_and_geo(self):
        # (3/2) J2 (Re/a)^2 = 1.3962e-3 at 500 km and 3.7089e-5 at
        # GEO, about 38x smaller at GEO.
        r_leo = opl.perturbation_magnitude_ratio(A_500)
        r_geo = opl.perturbation_magnitude_ratio(A_GEO)
        self.assertAlmostEqual(r_leo, 1.3962e-3, places=7)
        self.assertAlmostEqual(r_geo, 3.7077e-5, places=9)
        self.assertGreater(r_leo / r_geo, 35.0)

    def test_ratio_decreases_with_altitude(self):
        self.assertLess(
            opl.perturbation_magnitude_ratio(opl.semimajor_axis(900.0)),
            opl.perturbation_magnitude_ratio(opl.semimajor_axis(400.0)),
        )

    def test_ratio_nonpositive_axis_raises(self):
        with self.assertRaises(ValueError):
            opl.perturbation_magnitude_ratio(0.0)

    def test_secular_drift_properties_pack(self):
        props = opl.secular_drift_properties(500.0, 30.0 * DEG)
        self.assertEqual(props["altitude_km"], 500.0)
        self.assertAlmostEqual(props["semimajor_axis_m"], A_500, places=3)
        self.assertAlmostEqual(props["mean_motion_rad_s"], N_500, places=9)
        self.assertAlmostEqual(props["keplerian_period_s"], 5668.14, places=2)
        self.assertAlmostEqual(props["raan_drift_deg_day"], -6.6352, places=4)
        self.assertAlmostEqual(
            props["arg_perigee_drift_deg_day"], 10.5347, places=4
        )
        self.assertAlmostEqual(props["nodal_period_change_s"], 6.86, places=2)
        self.assertAlmostEqual(
            props["raan_drift_rad_s"] * RAD2DEG * 86400.0,
            props["raan_drift_deg_day"],
            places=12,
        )
        self.assertAlmostEqual(props["critical_inclination_deg"], 63.435, places=3)

    def test_secular_drift_properties_invalid_raises(self):
        with self.assertRaises(ValueError):
            opl.secular_drift_properties(-1.0, 30.0 * DEG)
        with self.assertRaises(ValueError):
            opl.secular_drift_properties(500.0, 2.0 * math.pi)


if __name__ == "__main__":
    unittest.main(verbosity=2)
