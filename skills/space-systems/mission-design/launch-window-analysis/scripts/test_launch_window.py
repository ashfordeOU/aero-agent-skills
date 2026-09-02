"""Gate 3 behavior contract test for launch-window-analysis.

Offline, deterministic, stdlib unittest. Verifies the correct
engineering answers for fixed inputs and ValueError on infeasible
inputs. Part of the mission-design launch window workflow.

Run from the repo root:
python3 skills/space-systems/mission-design/launch-window-analysis/scripts/test_launch_window.py
"""

import math
import sys
import unittest
from pathlib import Path

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parent
        / "."
    ),
)
from launch_window_logic import (
    beta_angle,
    daily_window_center_halfwidth,
    direct_injection_feasible,
    elevation_angle_at_crossing,
    launch_azimuth_for_inclination,
    plane_change_delta_v,
    sun_sync_ltan_to_raan,
    window_open_close,
)

# Fixed inputs (contract checklist): KSC at 28.5 deg N, 80.6 deg W.
KSC_LAT = 28.5
KSC_LON = -80.6


class TestLaunchAzimuth(unittest.TestCase):
    def test_due_east_at_latitude_equal_inclination(self):
        # cos(inc) = cos(lat) * sin(az) with inc = lat gives az = 90.
        az = launch_azimuth_for_inclination(28.5, 28.5)
        self.assertAlmostEqual(az, 90.0, places=6)

    def test_iss_inclination_from_ksc(self):
        # inc 51.6 from 28.5 N: az = asin(cos 51.6 / cos 28.5) = 44.98.
        az = launch_azimuth_for_inclination(51.6, KSC_LAT)
        self.assertAlmostEqual(az, 44.9751, delta=0.1)
        self.assertTrue(40.0 <= az <= 45.0)

    def test_retrograde_azimuth_westward(self):
        # inc 98 from 28.5 N: az = 180 - asin(cos 98 / cos 28.5) = 189.11.
        az = launch_azimuth_for_inclination(98.0, KSC_LAT)
        self.assertAlmostEqual(az, 189.112, delta=0.1)

    def test_polar_azimuth_due_north(self):
        az = launch_azimuth_for_inclination(90.0, KSC_LAT)
        self.assertAlmostEqual(az, 0.0, delta=1e-9)

    def test_inclination_below_latitude_raises(self):
        # Direct injection needs inc >= |lat|; below that the azimuth
        # formula has no real solution.
        with self.assertRaises(ValueError):
            launch_azimuth_for_inclination(20.0, KSC_LAT)
        with self.assertRaises(ValueError):
            launch_azimuth_for_inclination(160.0, KSC_LAT)
        self.assertFalse(direct_injection_feasible(20.0, KSC_LAT))
        self.assertTrue(direct_injection_feasible(51.6, KSC_LAT))


class TestPlaneChangeDeltaV(unittest.TestCase):
    def test_plane_change_ten_degrees(self):
        # dv = 2 * v * sin(di / 2). A 10 deg plane change at 7.8 km/s
        # costs 2 * 7.8 * sin(5 deg) = 1.360 km/s. (The 2.72 km/s figure
        # sometimes quoted for "10 deg" is 2 * 7.8 * sin(10 deg), which
        # is the value for a 20 deg plane change under the half-angle
        # formula; that case is asserted below.)
        self.assertAlmostEqual(
            plane_change_delta_v(10.0, 7.8), 1.3596, delta=0.01
        )
        # A 20 deg plane change at 7.8 km/s: 2.709 km/s, within 1% of
        # the 2.72 km/s reference.
        self.assertAlmostEqual(
            plane_change_delta_v(20.0, 7.8), 2.7089, delta=0.01
        )
        self.assertTrue(
            abs(plane_change_delta_v(20.0, 7.8) - 2.72) <= 0.0272
        )

    def test_plane_change_edges(self):
        self.assertAlmostEqual(plane_change_delta_v(0.0, 7.8), 0.0, delta=1e-9)
        # 60 deg plane change at 7.8 km/s: 2 * 7.8 * sin(30 deg) = 7.8.
        self.assertAlmostEqual(plane_change_delta_v(60.0, 7.8), 7.8, delta=1e-9)


class TestSunSyncLtanToRaan(unittest.TestCase):
    def test_ltan_conversions(self):
        # raan = sun_ra + 15 * (LTAN - 12), mod 360, at sun_ra = 0.
        self.assertAlmostEqual(sun_sync_ltan_to_raan(10.5, 0.0), 337.5, places=6)
        self.assertAlmostEqual(sun_sync_ltan_to_raan(18.0, 0.0), 90.0, places=6)
        self.assertAlmostEqual(sun_sync_ltan_to_raan(6.0, 0.0), 270.0, places=6)
        self.assertAlmostEqual(sun_sync_ltan_to_raan(12.0, 0.0), 0.0, places=6)

    def test_ltan_with_sun_ra(self):
        self.assertAlmostEqual(
            sun_sync_ltan_to_raan(10.5, 280.0), 257.5, places=6
        )
        self.assertAlmostEqual(sun_sync_ltan_to_raan(18.0, 280.0), 10.0, places=6)

    def test_ltan_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            sun_sync_ltan_to_raan(25.0, 0.0)


class TestDailyWindow(unittest.TestCase):
    def test_window_center_and_halfwidth(self):
        # KSC (28.5 N, 80.6 W), inc 51.6, raan 100, gmst 0, tol 5 deg.
        # Crossing LST = 100 + asin(tan 28.5 / tan 51.6) = 125.489 deg;
        # center = (125.489 + 80.6) / 360.9856 days = 49326 s.
        g = daily_window_center_halfwidth(
            51.6, KSC_LAT, 100.0, KSC_LON, 0.0, 5.0
        )
        self.assertAlmostEqual(g["center_seconds"], 49326.37, delta=30.0)
        self.assertAlmostEqual(g["half_width_seconds"], 1864.53, delta=30.0)
        self.assertAlmostEqual(g["center_lst_deg"], 125.4892, delta=0.1)
        self.assertAlmostEqual(g["relative_rate_deg_per_day"], 360.9856, places=6)

    def test_descending_node_crossing(self):
        # Descending-side crossing is 180 - 2 * asin(t) later in LST:
        # center = (254.511 + 80.6) / 360.9856 days = 80207 s.
        g = daily_window_center_halfwidth(
            51.6, KSC_LAT, 100.0, KSC_LON, 0.0, 5.0, node="descending"
        )
        self.assertAlmostEqual(g["center_seconds"], 80207.0, delta=30.0)

    def test_window_open_close(self):
        w = window_open_close(51.6, KSC_LAT, 100.0, KSC_LON, 0.0, 5.0)
        self.assertTrue(w["window_open_seconds"] < w["window_center_seconds"])
        self.assertTrue(w["window_center_seconds"] < w["window_close_seconds"])
        self.assertAlmostEqual(
            w["window_duration_seconds"], 3729.06, delta=30.0
        )
        # Sidereal day repeat with no node regression.
        self.assertAlmostEqual(w["window_period_days"], 0.99727, delta=1e-4)

    def test_sun_sync_window_period_is_one_day(self):
        # Node regression at +0.9856 deg/day cancels the 0.9856 deg/day
        # excess of the sidereal day: the window repeats at the same
        # local solar time every day.
        w = window_open_close(
            98.0, KSC_LAT, 337.5, KSC_LON, 45.0, 5.0,
            node_regression_deg_per_day=0.9856,
        )
        self.assertAlmostEqual(w["window_period_days"], 1.0, places=9)

    def test_sun_sync_ltan_10_30_window(self):
        # LTAN 10:30 -> raan 337.5 (sun_ra 0); crossing at
        # 337.5 + asin(-0.0763) = 333.124 deg LST; with gmst 45 the
        # center is (333.124 + 80.6 - 45) / 360.9856 days = 2088 s.
        g = daily_window_center_halfwidth(
            98.0, KSC_LAT, 337.5, KSC_LON, 45.0, 5.0
        )
        self.assertAlmostEqual(g["center_seconds"], 2087.96, delta=30.0)
        self.assertAlmostEqual(g["half_width_seconds"], 1384.50, delta=30.0)

    def test_infeasible_plane_raises(self):
        # inc 20 from 28.5 N: |tan(lat) / tan(inc)| > 1, the site never
        # crosses the plane, same limit as the azimuth feasibility gate.
        with self.assertRaises(ValueError):
            daily_window_center_halfwidth(
                20.0, KSC_LAT, 100.0, KSC_LON, 0.0, 5.0
            )


class TestElevationAtCrossing(unittest.TestCase):
    def test_overhead_at_crossing(self):
        # At the plane-crossing instant the site is on the ground track.
        self.assertAlmostEqual(
            elevation_angle_at_crossing(400.0, 0.0), 90.0, places=6
        )

    def test_elevation_profile_400km(self):
        # Zenith pass at 400 km: elevation falls from 90 deg to the
        # horizon at about 305 s on each side.
        self.assertAlmostEqual(
            elevation_angle_at_crossing(400.0, 100.0), 24.973, delta=0.5
        )
        self.assertAlmostEqual(
            elevation_angle_at_crossing(400.0, 300.0), 0.318, delta=0.5
        )
        self.assertTrue(elevation_angle_at_crossing(400.0, 500.0) < 0.0)

    def test_horizon_crossing_time(self):
        # Horizon at mu = acos(R / (R + h)): 304.85 s for 400 km.
        # Bisection-free check: elevation is negative past 305 s.
        self.assertTrue(elevation_angle_at_crossing(400.0, 304.0) > 0.0)
        self.assertTrue(elevation_angle_at_crossing(400.0, 306.0) < 0.0)


class TestLightingBetaAngle(unittest.TestCase):
    def test_dawn_dusk_sun_in_plane(self):
        # LTAN 06:00 (raan 270, sun_ra 0, dec 0, inc 98): the sun lies
        # near the orbit plane, |beta| near 90 deg.
        self.assertAlmostEqual(
            beta_angle(0.0, 0.0, 270.0, 98.0), -82.0, delta=0.5
        )

    def test_noon_midnight_sun_normal_to_plane(self):
        # LTAN 12:00 (raan 0): sun perpendicular to the plane, beta 0.
        self.assertAlmostEqual(beta_angle(0.0, 0.0, 0.0, 98.0), 0.0, delta=1e-9)

    def test_ltan_10_30_beta(self):
        self.assertAlmostEqual(
            beta_angle(0.0, 0.0, 337.5, 98.0), -22.269, delta=0.5
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
