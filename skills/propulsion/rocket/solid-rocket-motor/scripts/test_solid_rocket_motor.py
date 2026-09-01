#!/usr/bin/env python3
"""Gate 3 contract test: solid rocket motor ballistics logic.

Exercises scripts/solid_rocket_motor_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3. Covers the Vieille/St. Robert
burn rate law, the characteristic velocity, the chamber pressure
equilibrium (burn-side mass flow equals choked throat mass flow), mass
flow, thrust from specific impulse, total impulse from thrust and from
propellant mass, tubular grain burn area, web burn time, the burn
progression verdict, and invalid-input edge cases including the n = 1
limiting case, zero burn area, and threshold checks.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import solid_rocket_motor_logic as srm  # noqa: E402


class BurnRateTest(unittest.TestCase):
    def test_known_value(self):
        # r = a * p^n with a = 2e-5, n = 0.3 at 1e7 Pa.
        r = srm.burn_rate(1.0e7, 2.0e-5, 0.3)
        self.assertAlmostEqual(r, 2.0e-5 * 1.0e7 ** 0.3, places=12)

    def test_rate_grows_with_pressure(self):
        low = srm.burn_rate(5.0e6, 2.0e-5, 0.3)
        high = srm.burn_rate(1.0e7, 2.0e-5, 0.3)
        self.assertGreater(high, low)

    def test_rate_grows_with_coefficient(self):
        small = srm.burn_rate(1.0e7, 1.0e-5, 0.3)
        large = srm.burn_rate(1.0e7, 2.0e-5, 0.3)
        self.assertEqual(large, 2.0 * small)

    def test_non_positive_pressure_raises(self):
        with self.assertRaises(ValueError):
            srm.burn_rate(0.0, 2.0e-5, 0.3)
        with self.assertRaises(ValueError):
            srm.burn_rate(-1.0e6, 2.0e-5, 0.3)

    def test_non_positive_coefficient_raises(self):
        with self.assertRaises(ValueError):
            srm.burn_rate(1.0e7, 0.0, 0.3)

    def test_exponent_thresholds_raise(self):
        # n must be strictly inside (0, 1): n = 1 is the singular limiting
        # case and n = 0 or negative are outside the physical range.
        with self.assertRaises(ValueError):
            srm.burn_rate(1.0e7, 2.0e-5, 1.0)
        with self.assertRaises(ValueError):
            srm.burn_rate(1.0e7, 2.0e-5, 0.0)
        with self.assertRaises(ValueError):
            srm.burn_rate(1.0e7, 2.0e-5, -0.2)
        with self.assertRaises(ValueError):
            srm.burn_rate(1.0e7, 2.0e-5, 1.5)


class CharacteristicVelocityTest(unittest.TestCase):
    def test_known_band(self):
        # Typical AP/HTPB combustion products: gamma 1.2, R 320 J/(kg*K),
        # T_c 3000 K give c* near 1510 m/s.
        c_star = srm.characteristic_velocity(3000.0, 1.2, 320.0)
        self.assertTrue(1500.0 <= c_star <= 1520.0, c_star)

    def test_rises_with_temperature(self):
        cold = srm.characteristic_velocity(2500.0, 1.2, 320.0)
        hot = srm.characteristic_velocity(3500.0, 1.2, 320.0)
        self.assertGreater(hot, cold)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            srm.characteristic_velocity(0.0, 1.2, 320.0)
        with self.assertRaises(ValueError):
            srm.characteristic_velocity(3000.0, 1.0, 320.0)  # gamma must be > 1
        with self.assertRaises(ValueError):
            srm.characteristic_velocity(3000.0, 1.2, 0.0)


class EquilibriumPressureTest(unittest.TestCase):
    # Worked case: AP/HTPB tubular grain, rho_p = 1800 kg/m^3, a = 2e-5,
    # n = 0.3, A_b = 0.14 m^2, A_t = 1e-4 m^2, c* = 1600 m/s.
    RHO = 1800.0
    A = 2.0e-5
    N = 0.3
    AB = 0.14
    AT = 1.0e-4
    C_STAR = 1600.0

    def test_equilibrium_band_and_consistency(self):
        p_c = srm.equilibrium_chamber_pressure(
            self.RHO, self.A, self.N, self.AB, self.AT, self.C_STAR
        )
        self.assertTrue(1.0e7 <= p_c <= 1.1e7, p_c)
        # Equilibrium identity: burn-side mass flow equals choked throat
        # mass flow at the solved pressure.
        r = srm.burn_rate(p_c, self.A, self.N)
        burn_side = srm.burn_mass_flow(self.RHO, self.AB, r)
        nozzle_side = srm.mass_flow(p_c, self.AT, self.C_STAR)
        self.assertAlmostEqual(burn_side, nozzle_side, delta=1e-3 * nozzle_side)

    def test_pressure_rises_with_burn_area(self):
        low = srm.equilibrium_chamber_pressure(
            self.RHO, self.A, self.N, self.AB / 2.0, self.AT, self.C_STAR
        )
        high = srm.equilibrium_chamber_pressure(
            self.RHO, self.A, self.N, self.AB, self.AT, self.C_STAR
        )
        self.assertGreater(high, low)

    def test_pressure_falls_with_throat_area(self):
        small_throat = srm.equilibrium_chamber_pressure(
            self.RHO, self.A, self.N, self.AB, self.AT, self.C_STAR
        )
        big_throat = srm.equilibrium_chamber_pressure(
            self.RHO, self.A, self.N, self.AB, self.AT * 2.0, self.C_STAR
        )
        self.assertLess(big_throat, small_throat)

    def test_n_equal_one_limiting_case_raises(self):
        # n = 1 makes the exponent 1/(1-n) singular: no finite equilibrium.
        with self.assertRaises(ValueError):
            srm.equilibrium_chamber_pressure(
                self.RHO, self.A, 1.0, self.AB, self.AT, self.C_STAR
            )

    def test_zero_burn_area_raises(self):
        with self.assertRaises(ValueError):
            srm.equilibrium_chamber_pressure(
                self.RHO, self.A, self.N, 0.0, self.AT, self.C_STAR
            )

    def test_zero_throat_area_raises(self):
        with self.assertRaises(ValueError):
            srm.equilibrium_chamber_pressure(
                self.RHO, self.A, self.N, self.AB, 0.0, self.C_STAR
            )

    def test_non_positive_density_raises(self):
        with self.assertRaises(ValueError):
            srm.equilibrium_chamber_pressure(
                0.0, self.A, self.N, self.AB, self.AT, self.C_STAR
            )


class MassFlowTest(unittest.TestCase):
    def test_known_value(self):
        self.assertAlmostEqual(srm.mass_flow(1.0e7, 1.0e-4, 1600.0), 0.625)

    def test_non_positive_inputs_raise(self):
        with self.assertRaises(ValueError):
            srm.mass_flow(0.0, 1.0e-4, 1600.0)
        with self.assertRaises(ValueError):
            srm.mass_flow(1.0e7, 0.0, 1600.0)
        with self.assertRaises(ValueError):
            srm.mass_flow(1.0e7, 1.0e-4, 0.0)


class ThrustAndImpulseTest(unittest.TestCase):
    def test_thrust_from_isp(self):
        # F = Isp * g0 * m_dot: 250 s, 0.6386 kg/s gives about 1.57 kN.
        F = srm.thrust_from_isp(250.0, 0.6386)
        self.assertAlmostEqual(F, 250.0 * 9.80665 * 0.6386, places=6)
        self.assertTrue(1500.0 < F < 1600.0, F)

    def test_thrust_scales_with_mass_flow(self):
        f1 = srm.thrust_from_isp(250.0, 1.0)
        f2 = srm.thrust_from_isp(250.0, 2.0)
        self.assertAlmostEqual(f2, 2.0 * f1)

    def test_total_impulse_from_thrust(self):
        self.assertAlmostEqual(srm.total_impulse(1566.0, 7.9), 1566.0 * 7.9)

    def test_total_impulse_from_propellant(self):
        # I_t = Isp * g0 * m_prop with 250 s and 5.04 kg propellant.
        I_t = srm.total_impulse_from_propellant(250.0, 5.04)
        self.assertAlmostEqual(I_t, 250.0 * 9.80665 * 5.04, places=6)
        self.assertTrue(12000.0 < I_t < 12500.0, I_t)

    def test_impulse_consistency_worked_case(self):
        # Full worked example: burn side and impulse side must agree.
        p_c = srm.equilibrium_chamber_pressure(
            1800.0, 2.0e-5, 0.3, 0.14, 1.0e-4, 1600.0
        )
        r = srm.burn_rate(p_c, 2.0e-5, 0.3)
        m_dot = srm.burn_mass_flow(1800.0, 0.14, r)
        F = srm.thrust_from_isp(250.0, m_dot)
        t_b = srm.web_burn_time(0.02, r)
        m_prop = 1800.0 * 0.14 * 0.02
        self.assertAlmostEqual(
            srm.total_impulse(F, t_b),
            srm.total_impulse_from_propellant(250.0, m_prop),
            delta=1e-2 * 250.0 * 9.80665 * m_prop,
        )

    def test_non_positive_inputs_raise(self):
        with self.assertRaises(ValueError):
            srm.thrust_from_isp(0.0, 1.0)
        with self.assertRaises(ValueError):
            srm.thrust_from_isp(250.0, 0.0)
        with self.assertRaises(ValueError):
            srm.total_impulse(0.0, 5.0)
        with self.assertRaises(ValueError):
            srm.total_impulse(100.0, 0.0)
        with self.assertRaises(ValueError):
            srm.total_impulse_from_propellant(250.0, 0.0)


class GrainGeometryTest(unittest.TestCase):
    def test_tubular_burn_area(self):
        # Inner bore of a 0.1 m diameter, 1.0 m long tubular grain.
        self.assertAlmostEqual(
            srm.tubular_grain_burn_area(0.1, 1.0), math.pi * 0.1 * 1.0, places=12
        )

    def test_zero_diameter_raises(self):
        with self.assertRaises(ValueError):
            srm.tubular_grain_burn_area(0.0, 1.0)
        with self.assertRaises(ValueError):
            srm.tubular_grain_burn_area(0.1, 0.0)

    def test_web_burn_time(self):
        # 20 mm web at 2.5 mm/s burns for 8 s.
        self.assertAlmostEqual(srm.web_burn_time(0.02, 0.0025), 8.0, places=12)

    def test_web_burn_time_raises(self):
        with self.assertRaises(ValueError):
            srm.web_burn_time(0.0, 0.0025)
        with self.assertRaises(ValueError):
            srm.web_burn_time(0.02, 0.0)


class BurnProgressionTest(unittest.TestCase):
    def test_progressive(self):
        self.assertEqual(srm.burn_area_verdict(0.10, 0.14), "progressive")

    def test_neutral_within_tolerance(self):
        self.assertEqual(srm.burn_area_verdict(0.10, 0.10), "neutral")
        self.assertEqual(
            srm.burn_area_verdict(0.10, 0.10 + 1e-10), "neutral"
        )

    def test_regressive(self):
        self.assertEqual(srm.burn_area_verdict(0.14, 0.10), "regressive")

    def test_non_positive_areas_raise(self):
        with self.assertRaises(ValueError):
            srm.burn_area_verdict(0.0, 0.1)
        with self.assertRaises(ValueError):
            srm.burn_area_verdict(0.1, -0.05)


if __name__ == "__main__":
    unittest.main(verbosity=2)
