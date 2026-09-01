#!/usr/bin/env python3
"""Gate 3 contract test for orbital-decay (stdlib unittest, offline).

Asserts REAL computed values for the drag decay of circular low Earth
orbits: ballistic coefficient, exponential atmosphere density, altitude
decay rate, decay per orbit and per day, deorbit lifetime, and the
25-year disposal check. Reference anchors: 5668.144 s orbital period
and 7616.561 m/s circular velocity at 500 km; a 300 kg satellite with
1.5 m^2 drag area and drag coefficient 2.2 at 500 km decays at
1.0818e-3 m/s (93.47 m per day), loses 6.13 m per orbit, and deorbits
to 200 km in about 1.746 years under the leaf exponential atmosphere.
"""

import unittest

from orbital_decay_logic import (
    ballistic_coefficient, atmospheric_density, orbital_period_seconds,
    circular_velocity, drag_deceleration, decay_rate, decay_per_orbit,
    decay_per_day, lifetime_seconds, lifetime_years, disposal_compliant,
)


class BallisticCoefficientTest(unittest.TestCase):
    def test_worked_example(self):
        # B = 300 / (2.2 * 1.5) = 90.909 kg/m^2
        self.assertAlmostEqual(
            ballistic_coefficient(300.0, 1.5, 2.2), 90.909090909, places=6)

    def test_more_drag_area_lowers_coefficient(self):
        self.assertLess(
            ballistic_coefficient(300.0, 3.0, 2.2),
            ballistic_coefficient(300.0, 1.5, 2.2))

    def test_invalid_inputs_raise(self):
        for kwargs in ({"mass_kg": 0.0}, {"drag_area_m2": -1.0},
                       {"drag_coeff": 0.0}, {"mass_kg": -5.0}):
            with self.assertRaises(ValueError):
                ballistic_coefficient(
                    kwargs.get("mass_kg", 300.0),
                    kwargs.get("drag_area_m2", 1.5),
                    kwargs.get("drag_coeff", 2.2))


class AtmosphericDensityTest(unittest.TestCase):
    def test_density_at_reference_altitude(self):
        # exp(0) = 1, so rho(200 km) equals the reference density.
        self.assertAlmostEqual(atmospheric_density(200.0), 2.789e-10,
                               delta=1e-24)

    def test_density_500_km(self):
        # rho = 2.789e-10 * exp(-300/60) = 1.8792134e-12 kg/m^3
        self.assertAlmostEqual(atmospheric_density(500.0),
                               1.8792134180449366e-12, delta=1e-24)

    def test_density_400_km(self):
        self.assertAlmostEqual(atmospheric_density(400.0),
                               9.949476744548693e-12, delta=1e-24)

    def test_density_decreases_with_altitude(self):
        self.assertLess(atmospheric_density(600.0),
                        atmospheric_density(400.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            atmospheric_density(0.0)
        with self.assertRaises(ValueError):
            atmospheric_density(500.0, scale_height_km=-60.0)
        with self.assertRaises(ValueError):
            atmospheric_density(500.0, rho_ref=0.0)


class OrbitGeometryTest(unittest.TestCase):
    def test_period_500_km(self):
        self.assertAlmostEqual(orbital_period_seconds(500.0),
                               5668.144369, places=3)

    def test_velocity_500_km(self):
        self.assertAlmostEqual(circular_velocity(500.0),
                               7616.560806, places=3)

    def test_period_monotonic(self):
        self.assertGreater(orbital_period_seconds(800.0),
                           orbital_period_seconds(400.0))

    def test_invalid_altitude_raises(self):
        with self.assertRaises(ValueError):
            orbital_period_seconds(-10.0)


class DecayRateTest(unittest.TestCase):
    def test_worked_example_500_km(self):
        # 300 kg, 1.5 m^2, Cd 2.2 at 500 km: -1.0818e-3 m/s
        self.assertAlmostEqual(
            decay_rate(500.0, 300.0, 1.5, 2.2), -0.0010818016812,
            delta=1e-12)

    def test_rate_is_negative(self):
        self.assertLess(decay_rate(500.0, 300.0, 1.5, 2.2), 0.0)

    def test_rate_magnitude_grows_as_altitude_drops(self):
        self.assertGreater(abs(decay_rate(400.0, 300.0, 1.5, 2.2)),
                           abs(decay_rate(500.0, 300.0, 1.5, 2.2)))

    def test_lighter_heavier_bus(self):
        # Same geometry, lighter bus: higher Cd*A/m, faster decay.
        self.assertLess(decay_rate(500.0, 150.0, 1.5, 2.2),
                        decay_rate(500.0, 300.0, 1.5, 2.2))

    def test_400_km_example(self):
        # 100 kg, 0.5 m^2, Cd 2.2 at 400 km: -5.6858e-3 m/s
        self.assertAlmostEqual(
            decay_rate(400.0, 100.0, 0.5, 2.2), -0.005685756037,
            delta=1e-12)

    def test_drag_deceleration_consistency(self):
        # |dh/dt| = 2 * a_drag * a / v for a circular orbit.
        decel = drag_deceleration(500.0, 300.0, 1.5, 2.2)
        self.assertAlmostEqual(decel, 5.995930930986173e-07, delta=1e-18)
        v = circular_velocity(500.0)
        a = (6371.0 + 500.0) * 1000.0
        self.assertAlmostEqual(abs(decay_rate(500.0, 300.0, 1.5, 2.2)),
                               2.0 * decel * a / v, delta=1e-15)


class DecayPerOrbitAndDayTest(unittest.TestCase):
    def test_per_orbit_500_km(self):
        self.assertAlmostEqual(
            decay_per_orbit(500.0, 300.0, 1.5, 2.2), -6.131808108,
            delta=1e-6)

    def test_per_day_500_km(self):
        self.assertAlmostEqual(
            decay_per_day(500.0, 300.0, 1.5, 2.2), -93.467665258,
            delta=1e-4)


class LifetimeTest(unittest.TestCase):
    def test_lifetime_seconds_500_to_200(self):
        self.assertAlmostEqual(
            lifetime_seconds(500.0, 300.0, 1.5, 2.2, 200.0),
            55089323.869988, delta=1.0)

    def test_lifetime_years_500_to_200(self):
        self.assertAlmostEqual(
            lifetime_years(500.0, 300.0, 1.5, 2.2, 200.0),
            1.745675332, delta=1e-6)

    def test_lifetime_to_zero_near_scale_height_estimate(self):
        # As hf -> 0 the closed form approaches H / |dh/dt_0|.
        t0 = lifetime_seconds(500.0, 300.0, 1.5, 2.2, 0.0)
        h_over_rate = 60000.0 / abs(decay_rate(500.0, 300.0, 1.5, 2.2))
        self.assertAlmostEqual(t0 / h_over_rate, 1.0, delta=1e-3)

    def test_lifetime_shorter_for_lower_target(self):
        self.assertLess(
            lifetime_seconds(500.0, 300.0, 1.5, 2.2, 200.0),
            lifetime_seconds(500.0, 300.0, 1.5, 2.2, 0.0))

    def test_invalid_target_raises(self):
        with self.assertRaises(ValueError):
            lifetime_seconds(500.0, 300.0, 1.5, 2.2, 500.0)
        with self.assertRaises(ValueError):
            lifetime_seconds(500.0, 300.0, 1.5, 2.2, 600.0)
        with self.assertRaises(ValueError):
            lifetime_seconds(500.0, 300.0, 1.5, 2.2, -1.0)

    def test_invalid_mass_raises(self):
        with self.assertRaises(ValueError):
            lifetime_seconds(500.0, 0.0, 1.5, 2.2, 200.0)


class DisposalTest(unittest.TestCase):
    def test_compliant_short_lifetime(self):
        self.assertTrue(disposal_compliant(1.746))

    def test_non_compliant_long_lifetime(self):
        self.assertFalse(disposal_compliant(30.0))

    def test_boundary_25_years_is_compliant(self):
        self.assertTrue(disposal_compliant(25.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            disposal_compliant(-1.0)
        with self.assertRaises(ValueError):
            disposal_compliant(10.0, limit_years=0.0)


if __name__ == "__main__":
    unittest.main()
