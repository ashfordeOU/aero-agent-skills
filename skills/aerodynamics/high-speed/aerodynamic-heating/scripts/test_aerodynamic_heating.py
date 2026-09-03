"""Contract test for the aerodynamic-heating leaf logic.

Deterministic, offline, stdlib only. Run with:

    python3 scripts/test_aerodynamic_heating.py
"""

import math
import sys
import unittest
import os

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__))))

from aerodynamic_heating_logic import (
    C_SG,
    SIGMA_SB,
    EPSILON_DEFAULT,
    stagnation_heat_flux,
    radiation_equilibrium_temp,
    radius_scaling,
    heating_assessment,
)

# Worked example flight point (spec: heating peak).
RHO = 0.001        # kg/m3
VELOCITY = 7200.0  # m/s
NOSE_RADIUS = 0.5  # m
EMISSIVITY = 0.85

# Real module outputs at the worked point (4 s.f. targets).
FLUX_WORKED = 3.0547e6      # W/m2, spec bound 2.5e6-4.0e6
TEMP_WORKED = 2821.5        # K, spec bound 2600-3100


class TestModuleConstants(unittest.TestCase):
    def test_sutton_graves_constant(self):
        self.assertAlmostEqual(C_SG, 1.83e-4)

    def test_stefan_boltzmann_constant(self):
        self.assertAlmostEqual(SIGMA_SB, 5.670374419e-8)

    def test_default_emissivity(self):
        self.assertEqual(EPSILON_DEFAULT, 0.85)


class TestWorkedExample(unittest.TestCase):
    def test_heat_flux_magnitude_bounds(self):
        q = stagnation_heat_flux(RHO, VELOCITY, NOSE_RADIUS)
        self.assertGreater(q, 2.5e6)
        self.assertLess(q, 4.0e6)

    def test_heat_flux_value_4sf(self):
        q = stagnation_heat_flux(RHO, VELOCITY, NOSE_RADIUS)
        self.assertAlmostEqual(q, FLUX_WORKED, delta=0.5e3)

    def test_heat_flux_hand_estimate_close(self):
        q = stagnation_heat_flux(RHO, VELOCITY, NOSE_RADIUS)
        self.assertLess(abs(q - 3.1e6) / 3.1e6, 0.05)

    def test_radiation_temp_magnitude_bounds(self):
        q = stagnation_heat_flux(RHO, VELOCITY, NOSE_RADIUS)
        t = radiation_equilibrium_temp(q, emissivity=EMISSIVITY)
        self.assertGreater(t, 2600.0)
        self.assertLess(t, 3100.0)

    def test_radiation_temp_value_4sf(self):
        q = stagnation_heat_flux(RHO, VELOCITY, NOSE_RADIUS)
        t = radiation_equilibrium_temp(q, emissivity=EMISSIVITY)
        self.assertAlmostEqual(t, TEMP_WORKED, delta=0.5)

    def test_radiation_temp_hand_estimate_close(self):
        q = stagnation_heat_flux(RHO, VELOCITY, NOSE_RADIUS)
        t = radiation_equilibrium_temp(q, emissivity=EMISSIVITY)
        self.assertLess(abs(t - 2800.0) / 2800.0, 0.03)

    def test_assessment_dict_keys(self):
        a = heating_assessment(RHO, VELOCITY, NOSE_RADIUS)
        self.assertEqual(
            set(a.keys()),
            {"heat_flux_W_m2", "radiation_temp_K",
             "flux_doubled_nose_radius", "flux_halved_nose_radius"})

    def test_assessment_consistent_with_direct_calls(self):
        a = heating_assessment(RHO, VELOCITY, NOSE_RADIUS)
        q = stagnation_heat_flux(RHO, VELOCITY, NOSE_RADIUS)
        t = radiation_equilibrium_temp(q, emissivity=EMISSIVITY)
        self.assertEqual(a["heat_flux_W_m2"], q)
        self.assertEqual(a["radiation_temp_K"], t)
        self.assertEqual(
            a["flux_doubled_nose_radius"],
            radius_scaling(q, NOSE_RADIUS, 2.0 * NOSE_RADIUS))
        self.assertEqual(
            a["flux_halved_nose_radius"],
            radius_scaling(q, NOSE_RADIUS, 0.5 * NOSE_RADIUS))


class TestRadiusScalingIdentities(unittest.TestCase):
    def setUp(self):
        self.q = stagnation_heat_flux(RHO, VELOCITY, NOSE_RADIUS)

    def test_radius_doubled_is_ref_over_sqrt2(self):
        q2 = radius_scaling(self.q, NOSE_RADIUS, 2.0 * NOSE_RADIUS)
        expected = self.q / math.sqrt(2.0)
        self.assertAlmostEqual(q2, expected, delta=1e-9 * self.q)

    def test_radius_halved_is_ref_times_sqrt2(self):
        q2 = radius_scaling(self.q, NOSE_RADIUS, 0.5 * NOSE_RADIUS)
        expected = self.q * math.sqrt(2.0)
        self.assertAlmostEqual(q2, expected, delta=1e-9 * self.q)

    def test_radius_scaling_matches_direct_sutton_graves(self):
        for r_new in (0.25, 0.75, 1.0, 2.0):
            scaled = radius_scaling(self.q, NOSE_RADIUS, r_new)
            direct = stagnation_heat_flux(RHO, VELOCITY, r_new)
            self.assertAlmostEqual(scaled, direct, delta=1e-9 * direct)

    def test_radius_scaling_no_change_returns_reference(self):
        self.assertEqual(radius_scaling(self.q, NOSE_RADIUS, NOSE_RADIUS),
                         self.q)

    def test_flux_doubled_nose_radius_in_assessment_below_reference(self):
        a = heating_assessment(RHO, VELOCITY, NOSE_RADIUS)
        self.assertLess(a["flux_doubled_nose_radius"], self.q)
        self.assertGreater(a["flux_halved_nose_radius"], self.q)


class TestScalingLaws(unittest.TestCase):
    def test_flux_scales_with_velocity_cubed(self):
        q1 = stagnation_heat_flux(RHO, 5000.0, NOSE_RADIUS)
        q2 = stagnation_heat_flux(RHO, 10000.0, NOSE_RADIUS)
        self.assertAlmostEqual(q2 / q1, 8.0, places=6)

    def test_flux_increases_with_velocity(self):
        q1 = stagnation_heat_flux(RHO, 5000.0, NOSE_RADIUS)
        q2 = stagnation_heat_flux(RHO, 7200.0, NOSE_RADIUS)
        self.assertGreater(q2, q1)

    def test_flux_increases_with_density(self):
        q1 = stagnation_heat_flux(0.0005, VELOCITY, NOSE_RADIUS)
        q2 = stagnation_heat_flux(0.001, VELOCITY, NOSE_RADIUS)
        self.assertGreater(q2, q1)

    def test_flux_scales_with_sqrt_density(self):
        q1 = stagnation_heat_flux(0.001, VELOCITY, NOSE_RADIUS)
        q2 = stagnation_heat_flux(0.002, VELOCITY, NOSE_RADIUS)
        self.assertAlmostEqual(q2 / q1, math.sqrt(2.0), places=9)

    def test_flux_increases_as_radius_decreases(self):
        q_blunt = stagnation_heat_flux(RHO, VELOCITY, 1.0)
        q_sharp = stagnation_heat_flux(RHO, VELOCITY, 0.1)
        self.assertGreater(q_sharp, q_blunt)


class TestRadiationEquilibrium(unittest.TestCase):
    def test_blackbody_round_trip(self):
        q = stagnation_heat_flux(RHO, VELOCITY, NOSE_RADIUS)
        t = radiation_equilibrium_temp(q, emissivity=EMISSIVITY)
        q_back = EMISSIVITY * SIGMA_SB * t**4
        self.assertAlmostEqual(q_back, q, delta=1e-9 * q)

    def test_zero_flux_gives_zero_temperature(self):
        self.assertEqual(radiation_equilibrium_temp(0.0), 0.0)

    def test_higher_emissivity_lowers_temperature(self):
        q = stagnation_heat_flux(RHO, VELOCITY, NOSE_RADIUS)
        t1 = radiation_equilibrium_temp(q, emissivity=0.5)
        t2 = radiation_equilibrium_temp(q, emissivity=1.0)
        self.assertGreater(t1, t2)

    def test_blackbody_emissivity_one_allowed(self):
        q = stagnation_heat_flux(RHO, VELOCITY, NOSE_RADIUS)
        t = radiation_equilibrium_temp(q, emissivity=1.0)
        self.assertAlmostEqual(t, (q / SIGMA_SB)**0.25, places=6)


class TestDeterminism(unittest.TestCase):
    def test_no_rng_repeatable_results(self):
        a1 = heating_assessment(RHO, VELOCITY, NOSE_RADIUS)
        a2 = heating_assessment(RHO, VELOCITY, NOSE_RADIUS)
        self.assertEqual(a1, a2)


class TestValueErrorRejection(unittest.TestCase):
    def test_rho_nonpositive_rejected(self):
        for bad in (0.0, -0.001):
            with self.subTest(rho=bad):
                with self.assertRaises(ValueError):
                    stagnation_heat_flux(bad, VELOCITY, NOSE_RADIUS)

    def test_velocity_nonpositive_rejected(self):
        for bad in (0.0, -7200.0):
            with self.subTest(velocity=bad):
                with self.assertRaises(ValueError):
                    stagnation_heat_flux(RHO, bad, NOSE_RADIUS)

    def test_nose_radius_nonpositive_rejected(self):
        for bad in (0.0, -0.5):
            with self.subTest(nose_radius=bad):
                with self.assertRaises(ValueError):
                    stagnation_heat_flux(RHO, VELOCITY, bad)

    def test_negative_heat_flux_rejected(self):
        with self.assertRaises(ValueError):
            radiation_equilibrium_temp(-1.0)

    def test_emissivity_out_of_range_rejected(self):
        for bad in (0.0, 1.1, -0.5):
            with self.subTest(emissivity=bad):
                with self.assertRaises(ValueError):
                    radiation_equilibrium_temp(3.0e6, emissivity=bad)

    def test_radius_scaling_nonpositive_args_rejected(self):
        for bad in ((0.0, NOSE_RADIUS, 1.0),
                    (3.0e6, 0.0, 1.0),
                    (3.0e6, NOSE_RADIUS, -1.0),
                    (-3.0e6, NOSE_RADIUS, 1.0)):
            with self.subTest(args=bad):
                with self.assertRaises(ValueError):
                    radius_scaling(*bad)

    def test_assessment_propagates_valueerror(self):
        with self.assertRaises(ValueError):
            heating_assessment(0.0, VELOCITY, NOSE_RADIUS)


if __name__ == "__main__":
    unittest.main()
