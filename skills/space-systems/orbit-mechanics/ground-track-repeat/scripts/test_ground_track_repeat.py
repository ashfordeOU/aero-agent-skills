#!/usr/bin/env python3
"""Gate 3 contract tests: repeating ground track logic.

Stdlib unittest only, offline, no external dependencies. Run with:
python3 scripts/test_ground_track_repeat.py

Anchors (computed against the closed formulas, circular orbit,
Earth constants Re = 6371000 m, mu = 3.986004418e14 m^3/s^2,
J2 = 1.08262668e-3, sidereal day 86164.0905 s):
- semimajor_axis(500) = 6871000.0 m
- mean_motion(6871000) = 1.10850834e-3 rad/s
- nodal_regression_rate at 500 km, i = 97.39 deg = +1.9906791197e-07
  rad/s (retrograde sun-synchronous band, precesses eastward)
- nodal_regression_rate at 400 km, i = 51.6 deg = -1.0119619236e-06
  rad/s (prograde, regresses westward)
- nodal_period at 500 km, 97.39 deg = 5667.13 s
- revolutions_per_day at 500 km, 97.39 deg = 15.20419
- repeat orbit: 888.4676 km at 97.39 deg, N = 14.0000000000,
  repeat_cycle_days = (1, 14)
- repeat orbit: 562.2007 km at 97.39 deg, N = 15.0000000000,
  repeat_cycle_days = (1, 15)
- no repeat: 400 km at 51.6 deg, N = 15.525589, no cycle in 60 days
- invalid inputs raise ValueError
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ground_track_repeat_logic as gtr  # noqa: E402

DEG = math.pi / 180.0


class TestSemimajorAxis(unittest.TestCase):
    def test_anchor_500km(self):
        self.assertAlmostEqual(gtr.semimajor_axis(500.0), 6871000.0, places=3)

    def test_anchor_ground_level(self):
        self.assertAlmostEqual(gtr.semimajor_axis(0.0), 6371000.0, places=3)

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            gtr.semimajor_axis(-1.0)


class TestMeanMotion(unittest.TestCase):
    def test_anchor_500km(self):
        # Analytic: n = sqrt(3.986004418e14 / 6871000**3) rad/s.
        n = gtr.mean_motion(6871000.0)
        self.assertAlmostEqual(n, 1.10850834e-3, places=8)

    def test_mean_motion_decreases_with_sma(self):
        self.assertGreater(gtr.mean_motion(6871000.0), gtr.mean_motion(7259000.0))

    def test_non_positive_sma_raises(self):
        with self.assertRaises(ValueError):
            gtr.mean_motion(0.0)
        with self.assertRaises(ValueError):
            gtr.mean_motion(-5.0)


class TestNodalRegressionRate(unittest.TestCase):
    def test_anchor_retrograde_500km(self):
        n = gtr.mean_motion(6871000.0)
        rate = gtr.nodal_regression_rate(n, 6871000.0, 97.39 * DEG)
        self.assertAlmostEqual(rate, 1.9906791197e-07, places=12)

    def test_anchor_prograde_400km(self):
        n = gtr.mean_motion(6771000.0)
        rate = gtr.nodal_regression_rate(n, 6771000.0, 51.6 * DEG)
        self.assertAlmostEqual(rate, -1.0119619236e-06, places=12)

    def test_zero_regression_at_polar_inclination(self):
        n = gtr.mean_motion(6871000.0)
        rate = gtr.nodal_regression_rate(n, 6871000.0, math.pi / 2.0)
        self.assertAlmostEqual(rate, 0.0, places=15)

    def test_inclination_out_of_range_raises(self):
        n = gtr.mean_motion(6871000.0)
        with self.assertRaises(ValueError):
            gtr.nodal_regression_rate(n, 6871000.0, -0.1)
        with self.assertRaises(ValueError):
            gtr.nodal_regression_rate(n, 6871000.0, math.pi + 0.1)

    def test_non_positive_inputs_raise(self):
        with self.assertRaises(ValueError):
            gtr.nodal_regression_rate(0.0, 6871000.0, 0.5)
        with self.assertRaises(ValueError):
            gtr.nodal_regression_rate(1e-3, 0.0, 0.5)


class TestNodalPeriod(unittest.TestCase):
    def test_anchor_500km(self):
        # T_n = 2 pi / (1.1085083403e-3 + 1.9906791197e-07) = 5667.13 s.
        t = gtr.nodal_period(1.1085083403e-3, 1.9906791197e-07)
        self.assertAlmostEqual(t, 5667.13, places=2)

    def test_nodal_period_longer_than_keplerian_for_retrograde(self):
        # Positive regression raises the denominator, shortening the period.
        t_kep = 2.0 * math.pi / 1.1085083403e-3
        t_node = gtr.nodal_period(1.1085083403e-3, 1.9906791197e-07)
        self.assertLess(t_node, t_kep)

    def test_regression_overtaking_mean_motion_raises(self):
        with self.assertRaises(ValueError):
            gtr.nodal_period(1.0e-3, -2.0e-3)

    def test_non_positive_mean_motion_raises(self):
        with self.assertRaises(ValueError):
            gtr.nodal_period(0.0, 1.0e-7)


class TestRevolutionsPerDay(unittest.TestCase):
    def test_anchor_500km(self):
        revs = gtr.revolutions_per_day(1.1085083403e-3, 1.9906791197e-07)
        self.assertAlmostEqual(revs, 15.20419, places=4)

    def test_14_repeat_orbit(self):
        # Exact 14-rev repeat altitude solved for i = 97.39 deg.
        props = gtr.ground_track_properties(888.46756979, 97.39 * DEG)
        self.assertAlmostEqual(props["revolutions_per_day"], 14.0, places=8)

    def test_15_repeat_orbit(self):
        # Exact 15-rev repeat altitude solved for i = 97.39 deg.
        props = gtr.ground_track_properties(562.20071998, 97.39 * DEG)
        self.assertAlmostEqual(props["revolutions_per_day"], 15.0, places=8)


class TestRepeatCycleDays(unittest.TestCase):
    def test_14_cycle(self):
        self.assertEqual(gtr.repeat_cycle_days(14.0), (1, 14))

    def test_15_cycle(self):
        self.assertEqual(gtr.repeat_cycle_days(15.0), (1, 15))

    def test_no_cycle_iss_like(self):
        # 400 km, 51.6 deg: 15.525589 revs/day, nothing in 60 days.
        self.assertIsNone(gtr.repeat_cycle_days(15.525589))

    def test_cycle_respects_max_days(self):
        # 7.1 revs/day repeats on day 10 (71 revs) but not by day 5.
        self.assertIsNone(gtr.repeat_cycle_days(7.1, max_days=5))
        self.assertEqual(gtr.repeat_cycle_days(7.1, max_days=10), (10, 71))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gtr.repeat_cycle_days(0.0)
        with self.assertRaises(ValueError):
            gtr.repeat_cycle_days(-3.0)
        with self.assertRaises(ValueError):
            gtr.repeat_cycle_days(14.0, max_days=0)
        with self.assertRaises(ValueError):
            gtr.repeat_cycle_days(14.0, max_days=2.5)
        with self.assertRaises(ValueError):
            gtr.repeat_cycle_days(14.0, tolerance=0.0)


class TestGroundTrackProperties(unittest.TestCase):
    def test_full_solution_repeat_14(self):
        props = gtr.ground_track_properties(888.46756979, 97.39 * DEG)
        self.assertAlmostEqual(props["semimajor_axis_m"], 7259467.6, places=1)
        self.assertAlmostEqual(props["nodal_period_s"], 6154.578, places=2)
        self.assertEqual(props["repeat_cycle_days"], 1)
        self.assertEqual(props["repeat_revolutions"], 14)

    def test_full_solution_no_repeat(self):
        props = gtr.ground_track_properties(400.0, 51.6 * DEG)
        self.assertAlmostEqual(props["nodal_period_s"], 5549.81, places=2)
        self.assertIsNone(props["repeat_cycle_days"])
        self.assertIsNone(props["repeat_revolutions"])

    def test_properties_keys_present(self):
        props = gtr.ground_track_properties(500.0, 97.39 * DEG)
        for key in (
            "altitude_km",
            "semimajor_axis_m",
            "mean_motion_rad_s",
            "nodal_regression_rate_rad_s",
            "nodal_period_s",
            "revolutions_per_day",
            "repeat_cycle_days",
            "repeat_revolutions",
        ):
            self.assertIn(key, props)

    def test_closed_loop_sidereal_day(self):
        # N * T_n must equal the sidereal day by construction.
        props = gtr.ground_track_properties(888.46756979, 97.39 * DEG)
        self.assertAlmostEqual(
            props["revolutions_per_day"] * props["nodal_period_s"],
            86164.0905,
            places=2,
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            gtr.ground_track_properties(-1.0, 0.5)
        with self.assertRaises(ValueError):
            gtr.ground_track_properties(500.0, -0.1)
        with self.assertRaises(ValueError):
            gtr.ground_track_properties(500.0, math.pi + 0.1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
