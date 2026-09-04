"""Contract test for geostationary_station_keeping_logic.

Deterministic, offline, stdlib unittest. Run from the repo root:

    python3 scripts/test_geostationary_station_keeping.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geostationary_station_keeping_logic as gk


class TestOrbitGeometry(unittest.TestCase):
    """Geosynchronous radius and speed anchors."""

    def test_radius_anchor(self):
        self.assertAlmostEqual(gk.geosynchronous_radius(), 42164.2, delta=0.5)

    def test_speed_anchor(self):
        self.assertAlmostEqual(gk.geo_speed(), 3074.7, delta=0.1)

    def test_radius_speed_kepler_identity(self):
        # v = 1000 * sqrt(MU / r) inverts exactly to r * v**2 = MU * 1e6.
        r = gk.geosynchronous_radius()
        v = gk.geo_speed()
        self.assertAlmostEqual(r * v * v / 1.0e6, gk.MU, delta=1.0e-6)

    def test_radius_positive_finite(self):
        self.assertTrue(math.isfinite(gk.geosynchronous_radius()))
        self.assertGreater(gk.geosynchronous_radius(), 40000.0)


class TestNorthSouthDeltaV(unittest.TestCase):
    """Annual and per-burn N/S delta-v from the inclination drift."""

    def test_annual_anchor(self):
        self.assertAlmostEqual(gk.ns_annual_delta_v(0.85), 45.61, delta=0.05)

    def test_per_burn_anchor(self):
        self.assertAlmostEqual(gk.ns_per_burn_delta_v(0.85), 22.81, delta=0.05)

    def test_identity_annual_is_two_per_burn(self):
        for drift in (0.5, 0.85, 1.0, 3.0):
            annual = gk.ns_annual_delta_v(drift)
            per_burn = gk.ns_per_burn_delta_v(drift)
            self.assertAlmostEqual(annual, 2.0 * per_burn, delta=1.0e-9)

    def test_zero_drift_gives_zero_delta_v(self):
        self.assertEqual(gk.ns_annual_delta_v(0.0), 0.0)
        self.assertEqual(gk.ns_per_burn_delta_v(0.0), 0.0)

    def test_small_drift_linear_approx(self):
        # 2 v sin(d/2) ~= v d (radians) for tiny drift.
        drift = 0.01
        approx = gk.geo_speed() * math.radians(drift)
        self.assertAlmostEqual(gk.ns_annual_delta_v(drift), approx,
                               delta=1.0e-4)

    def test_valueerror_negative_drift(self):
        with self.assertRaises(ValueError):
            gk.ns_annual_delta_v(-0.1)
        with self.assertRaises(ValueError):
            gk.ns_per_burn_delta_v(-0.1)


class TestBurnTime(unittest.TestCase):
    """Burn duration from delta-v, thrust and mass."""

    def test_anchor(self):
        self.assertAlmostEqual(gk.burn_time(22.81, 400.0, 2000.0), 114.0,
                               delta=0.1)

    def test_scaling_laws(self):
        # t = m * dv / F: doubling thrust halves the burn, zero dv
        # means zero burn.
        self.assertAlmostEqual(gk.burn_time(50.0, 400.0, 2000.0),
                               gk.burn_time(50.0, 200.0, 2000.0) / 2.0,
                               delta=1.0e-9)
        self.assertEqual(gk.burn_time(0.0, 400.0, 2000.0), 0.0)

    def test_valueerror_zero_thrust(self):
        with self.assertRaises(ValueError):
            gk.burn_time(22.81, 0.0, 2000.0)

    def test_valueerror_nonpositive_mass(self):
        with self.assertRaises(ValueError):
            gk.burn_time(22.81, 400.0, 0.0)
        with self.assertRaises(ValueError):
            gk.burn_time(22.81, 400.0, -2000.0)

    def test_valueerror_negative_delta_v(self):
        with self.assertRaises(ValueError):
            gk.burn_time(-1.0, 400.0, 2000.0)


class TestAnnualPropellant(unittest.TestCase):
    """Annual propellant from the rocket equation over the year."""

    def test_anchor(self):
        self.assertAlmostEqual(gk.annual_propellant(45.61, 280.0, 2000.0),
                               33.0, delta=0.2)

    def test_small_delta_v_linearization(self):
        # m * (1 - exp(-dv / (isp * g0))) ~= m * dv / (isp * g0).
        dv = 1.0
        linear = 2000.0 * dv / (280.0 * gk.G0)
        self.assertAlmostEqual(gk.annual_propellant(dv, 280.0, 2000.0),
                               linear, delta=0.01)

    def test_zero_and_monotonic(self):
        self.assertEqual(gk.annual_propellant(0.0, 280.0, 2000.0), 0.0)
        self.assertGreater(gk.annual_propellant(100.0, 280.0, 2000.0),
                           gk.annual_propellant(50.0, 280.0, 2000.0))

    def test_propellant_below_mass(self):
        self.assertLess(gk.annual_propellant(1000.0, 280.0, 2000.0), 2000.0)

    def test_valueerror_zero_isp(self):
        with self.assertRaises(ValueError):
            gk.annual_propellant(45.61, 0.0, 2000.0)

    def test_valueerror_nonpositive_mass_and_dv(self):
        with self.assertRaises(ValueError):
            gk.annual_propellant(45.61, 280.0, 0.0)
        with self.assertRaises(ValueError):
            gk.annual_propellant(-1.0, 280.0, 2000.0)


class TestEastWestCycle(unittest.TestCase):
    """E/W deadband drift cycle period and maneuver cadence."""

    def test_cycle_period_anchor(self):
        self.assertAlmostEqual(gk.ew_cycle_period(0.05, 0.0018), 14.907,
                               delta=0.05)

    def test_cadence_anchor(self):
        self.assertAlmostEqual(gk.ew_maneuvers_per_year(0.05, 0.0018), 24.5,
                               delta=0.1)

    def test_identity_period_times_cadence(self):
        for half, accel in ((0.05, 0.0018), (0.1, 0.005), (0.02, 0.001)):
            period = gk.ew_cycle_period(half, accel)
            cadence = gk.ew_maneuvers_per_year(half, accel)
            self.assertAlmostEqual(period * cadence, 365.25, delta=1.0e-9)

    def test_sqrt_scaling_laws(self):
        # T = 2 sqrt(2 h / a): doubling the box multiplies the cycle by
        # sqrt(2); quadrupling the acceleration halves it.
        t1 = gk.ew_cycle_period(0.05, 0.0018)
        self.assertAlmostEqual(gk.ew_cycle_period(0.10, 0.0018) / t1,
                               math.sqrt(2.0), delta=1.0e-9)
        self.assertAlmostEqual(gk.ew_cycle_period(0.05, 0.0072),
                               t1 / 2.0, delta=1.0e-9)

    def test_valueerror_nonpositive_half_width(self):
        with self.assertRaises(ValueError):
            gk.ew_cycle_period(0.0, 0.0018)
        with self.assertRaises(ValueError):
            gk.ew_cycle_period(-0.05, 0.0018)

    def test_valueerror_nonpositive_acceleration(self):
        with self.assertRaises(ValueError):
            gk.ew_cycle_period(0.05, 0.0)
        with self.assertRaises(ValueError):
            gk.ew_cycle_period(0.05, -0.0018)


class TestUncontrolledDrift(unittest.TestCase):
    """Uncontrolled inclination drift time to tolerance."""

    def test_anchor(self):
        self.assertAlmostEqual(gk.uncontrolled_drift_years(0.1, 0.85),
                               0.1176, delta=0.001)

    def test_scaling_laws(self):
        # t = tolerance / rate: doubling the tolerance doubles the time,
        # doubling the rate halves it.
        t1 = gk.uncontrolled_drift_years(0.1, 0.85)
        self.assertAlmostEqual(gk.uncontrolled_drift_years(0.2, 0.85),
                               2.0 * t1, delta=1.0e-9)
        self.assertAlmostEqual(gk.uncontrolled_drift_years(0.1, 1.70),
                               t1 / 2.0, delta=1.0e-9)

    def test_valueerror_nonpositive_tolerance(self):
        with self.assertRaises(ValueError):
            gk.uncontrolled_drift_years(0.0, 0.85)
        with self.assertRaises(ValueError):
            gk.uncontrolled_drift_years(-0.1, 0.85)

    def test_valueerror_nonpositive_drift_rate(self):
        with self.assertRaises(ValueError):
            gk.uncontrolled_drift_years(0.1, 0.0)
        with self.assertRaises(ValueError):
            gk.uncontrolled_drift_years(0.1, -0.85)


class TestDeterminismAndConstants(unittest.TestCase):
    """Determinism and documented module constants."""

    def test_repeat_calls_deterministic(self):
        a = (gk.geosynchronous_radius(), gk.geo_speed(),
             gk.ns_annual_delta_v(0.85), gk.ew_cycle_period(0.05, 0.0018))
        b = (gk.geosynchronous_radius(), gk.geo_speed(),
             gk.ns_annual_delta_v(0.85), gk.ew_cycle_period(0.05, 0.0018))
        self.assertEqual(a, b)

    def test_module_constants_and_float_outputs(self):
        self.assertAlmostEqual(gk.MU, 398600.4418, delta=1.0e-9)
        self.assertAlmostEqual(gk.SIDEREAL_DAY, 86164.0905, delta=1.0e-9)
        self.assertAlmostEqual(gk.G0, 9.80665, delta=1.0e-9)
        self.assertEqual(gk.PI, math.pi)
        for value in (gk.geosynchronous_radius(), gk.geo_speed(),
                      gk.ns_annual_delta_v(0.85),
                      gk.ew_maneuvers_per_year(0.05, 0.0018)):
            self.assertIsInstance(value, float)


if __name__ == "__main__":
    unittest.main()
