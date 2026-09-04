"""Offline contract test for rotorcraft-blade-flapping-dynamics.

Deterministic stdlib unittest, no network, no RNG. Covers the worked
example magnitude bounds (Lock number 6-10 about 7.58, coning about
0.0979 rad = 5.61 deg inside the published 3-8 deg band, flap
frequency ratio about 1.0387 inside the published 1.02-1.08 per rev
band), the exact uniform-blade inertia value, limiting and identity
checks, ValueError rejection of every non-physical input, and run to
run determinism.
"""

import math
import unittest

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rotorcraft_blade_flapping_dynamics_logic import (  # noqa: E402
    A_LIFT_DEFAULT,
    PI,
    RHO_SL,
    blade_flap_inertia_uniform,
    blade_flapping_summary,
    flap_frequency_ratio,
    hover_coning_angle,
    lock_number,
)


class TestWorkedExample(unittest.TestCase):
    """Spec worked example: m_b = 50 kg, R = 6.0 m, c = 0.50 m, theta0 =
    0.170 rad, lambda = 0.050, e = 0.05, rho = 1.225, a = 5.73."""

    def test_worked_example_flap_inertia_exact(self):
        self.assertEqual(blade_flap_inertia_uniform(50, 6.0), 600.0)

    def test_worked_example_lock_number_magnitude(self):
        gamma = lock_number(1.225, 5.73, 0.50, 6.0,
                            blade_flap_inertia_uniform(50, 6.0))
        self.assertGreater(gamma, 6.0)
        self.assertLess(gamma, 10.0)
        self.assertAlmostEqual(gamma, 7.58, places=2)
        hand = RHO_SL * A_LIFT_DEFAULT * 0.50 * 6.0 ** 4 / 600.0
        self.assertAlmostEqual(gamma, hand, places=9)

    def test_worked_example_coning_radians_magnitude(self):
        gamma = lock_number(1.225, 5.73, 0.50, 6.0, 600.0)
        a0 = hover_coning_angle(gamma, 0.170, 0.050)
        self.assertAlmostEqual(a0, 0.0979, places=4)
        self.assertGreater(a0, math.radians(3.0))
        self.assertLess(a0, math.radians(8.0))

    def test_worked_example_coning_degrees_magnitude(self):
        gamma = lock_number(1.225, 5.73, 0.50, 6.0, 600.0)
        a0_deg = hover_coning_angle(gamma, 0.170, 0.050) * 180.0 / PI
        self.assertAlmostEqual(a0_deg, 5.61, places=2)
        self.assertGreater(a0_deg, 3.0)
        self.assertLess(a0_deg, 8.0)

    def test_worked_example_frequency_ratio_value(self):
        nu = flap_frequency_ratio(0.05)
        self.assertAlmostEqual(nu, 1.0387, places=4)
        self.assertGreater(nu, 1.02)
        self.assertLess(nu, 1.08)

    def test_worked_example_summary_values(self):
        summary = blade_flapping_summary(50, 6.0, 0.50, 0.170, 0.050, 0.05)
        self.assertAlmostEqual(summary["lock_number"], 7.58079, places=5)
        self.assertEqual(summary["flap_inertia_kg_m2"], 600.0)
        self.assertAlmostEqual(summary["coning_angle_deg"], 5.61032, places=4)
        self.assertAlmostEqual(summary["flap_frequency_ratio"], 1.03872, places=4)


class TestSummaryConvenience(unittest.TestCase):
    def test_summary_has_exact_keys(self):
        summary = blade_flapping_summary(50, 6.0, 0.50, 0.170, 0.050, 0.05)
        self.assertEqual(
            set(summary.keys()),
            {
                "lock_number",
                "flap_inertia_kg_m2",
                "coning_angle_rad",
                "coning_angle_deg",
                "flap_frequency_ratio",
                "flap_frequency_per_rev",
            },
        )

    def test_summary_matches_individual_calls(self):
        summary = blade_flapping_summary(50, 6.0, 0.50, 0.170, 0.050, 0.05)
        gamma = lock_number(1.225, 5.73, 0.50, 6.0, 600.0)
        a0 = hover_coning_angle(gamma, 0.170, 0.050)
        nu = flap_frequency_ratio(0.05)
        self.assertAlmostEqual(summary["lock_number"], gamma)
        self.assertAlmostEqual(summary["coning_angle_rad"], a0)
        self.assertAlmostEqual(summary["flap_frequency_ratio"], nu)
        self.assertAlmostEqual(
            summary["flap_frequency_per_rev"], nu, places=12)

    def test_summary_defaults_used(self):
        explicit = blade_flapping_summary(
            50, 6.0, 0.50, 0.170, 0.050, 0.05,
            lift_slope=A_LIFT_DEFAULT, rho=RHO_SL)
        defaulted = blade_flapping_summary(50, 6.0, 0.50, 0.170, 0.050, 0.05)
        self.assertEqual(explicit, defaulted)

    def test_summary_propagates_value_error(self):
        with self.assertRaises(ValueError):
            blade_flapping_summary(0, 6.0, 0.50, 0.170, 0.050, 0.05)

    def test_summary_all_outputs_finite(self):
        summary = blade_flapping_summary(50, 6.0, 0.50, 0.170, 0.050, 0.05)
        for value in summary.values():
            self.assertTrue(math.isfinite(value))


class TestConingLimitingBehaviour(unittest.TestCase):
    def test_coning_zero_at_flap_moment_balance(self):
        # theta0 / 4 == inflow / 3 exactly (0.125/4 = 0.09375/3 = 0.03125)
        self.assertEqual(hover_coning_angle(6.0, 0.125, 0.09375), 0.0)

    def test_coning_increases_with_collective(self):
        low = hover_coning_angle(6.0, 0.12, 0.05)
        high = hover_coning_angle(6.0, 0.16, 0.05)
        self.assertGreater(high, low)

    def test_coning_decreases_with_inflow(self):
        low_inflow = hover_coning_angle(6.0, 0.14, 0.04)
        high_inflow = hover_coning_angle(6.0, 0.14, 0.08)
        self.assertGreater(low_inflow, high_inflow)

    def test_coning_scales_linearly_with_lock_number(self):
        a_small = hover_coning_angle(4.0, 0.15, 0.05)
        a_large = hover_coning_angle(8.0, 0.15, 0.05)
        self.assertAlmostEqual(a_large, 2.0 * a_small, places=12)


class TestFlapFrequencyRatio(unittest.TestCase):
    def test_central_hinge_limit_exact(self):
        self.assertEqual(flap_frequency_ratio(0.0), 1.0)

    def test_half_offset_value(self):
        self.assertAlmostEqual(
            flap_frequency_ratio(0.5), math.sqrt(2.5), places=12)

    def test_equivalent_closed_form_identity(self):
        e = 0.2
        nu_sq = flap_frequency_ratio(e) ** 2
        alt = (1.0 - 1.5 * e + 0.5 * e ** 3) / (1.0 - e) ** 3
        self.assertAlmostEqual(nu_sq, alt, places=12)

    def test_frequency_ratio_monotonic_in_offset(self):
        self.assertGreater(flap_frequency_ratio(0.2), flap_frequency_ratio(0.05))
        self.assertGreater(flap_frequency_ratio(0.4), flap_frequency_ratio(0.2))

    def test_frequency_ratio_stays_above_one(self):
        for e in (0.01, 0.1, 0.25, 0.5, 0.75, 0.9):
            self.assertGreater(flap_frequency_ratio(e), 1.0)


class TestScalingRelations(unittest.TestCase):
    def test_inertia_scales_with_mass(self):
        self.assertAlmostEqual(
            blade_flap_inertia_uniform(100, 6.0),
            2.0 * blade_flap_inertia_uniform(50, 6.0),
            places=12,
        )

    def test_inertia_scales_with_radius_squared(self):
        self.assertAlmostEqual(
            blade_flap_inertia_uniform(50, 12.0),
            4.0 * blade_flap_inertia_uniform(50, 6.0),
            places=12,
        )

    def test_lock_number_scales_with_radius_fourth_power(self):
        g2 = lock_number(1.225, 5.73, 0.5, 2.0, 600.0)
        g4 = lock_number(1.225, 5.73, 0.5, 4.0, 600.0)
        self.assertAlmostEqual(g4, 16.0 * g2, places=12)

    def test_lock_number_inversely_proportional_to_inertia(self):
        g_half = lock_number(1.225, 5.73, 0.5, 6.0, 300.0)
        g_full = lock_number(1.225, 5.73, 0.5, 6.0, 600.0)
        self.assertAlmostEqual(g_half, 2.0 * g_full, places=12)

    def test_lock_number_scales_with_density(self):
        g_sl = lock_number(1.225, 5.73, 0.5, 6.0, 600.0)
        g_hi = lock_number(2.450, 5.73, 0.5, 6.0, 600.0)
        self.assertAlmostEqual(g_hi, 2.0 * g_sl, places=12)


class TestValueErrorRejection(unittest.TestCase):
    def test_inertia_nonpositive_mass_raises(self):
        for mass in (0.0, -1.0, -50.0):
            with self.subTest(mass=mass):
                with self.assertRaises(ValueError):
                    blade_flap_inertia_uniform(mass, 6.0)

    def test_inertia_nonpositive_radius_raises(self):
        for radius in (0.0, -2.0):
            with self.subTest(radius=radius):
                with self.assertRaises(ValueError):
                    blade_flap_inertia_uniform(50, radius)

    def test_lock_number_nonpositive_inputs_raise(self):
        cases = [
            dict(rho=0.0, lift_slope=5.73, chord_m=0.5, radius_m=6.0, flap_inertia=600.0),
            dict(rho=1.225, lift_slope=-5.73, chord_m=0.5, radius_m=6.0, flap_inertia=600.0),
            dict(rho=1.225, lift_slope=5.73, chord_m=0.0, radius_m=6.0, flap_inertia=600.0),
            dict(rho=1.225, lift_slope=5.73, chord_m=0.5, radius_m=-6.0, flap_inertia=600.0),
            dict(rho=1.225, lift_slope=5.73, chord_m=0.5, radius_m=6.0, flap_inertia=0.0),
        ]
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    lock_number(**case)

    def test_coning_nonpositive_gamma_raises(self):
        for gamma in (0.0, -4.0):
            with self.subTest(gamma=gamma):
                with self.assertRaises(ValueError):
                    hover_coning_angle(gamma, 0.15, 0.05)

    def test_coning_negative_collective_raises(self):
        with self.assertRaises(ValueError):
            hover_coning_angle(6.0, -0.1, 0.05)

    def test_coning_negative_inflow_raises(self):
        with self.assertRaises(ValueError):
            hover_coning_angle(6.0, 0.15, -0.02)

    def test_frequency_ratio_negative_offset_raises(self):
        for e in (-0.01, -0.5):
            with self.subTest(e=e):
                with self.assertRaises(ValueError):
                    flap_frequency_ratio(e)

    def test_frequency_ratio_offset_at_or_above_unity_raises(self):
        for e in (1.0, 1.5, 3.0):
            with self.subTest(e=e):
                with self.assertRaises(ValueError):
                    flap_frequency_ratio(e)


class TestDeterminism(unittest.TestCase):
    def test_repeatable_outputs_no_rng(self):
        first = blade_flapping_summary(50, 6.0, 0.50, 0.170, 0.050, 0.05)
        second = blade_flapping_summary(50, 6.0, 0.50, 0.170, 0.050, 0.05)
        self.assertEqual(first, second)
        self.assertEqual(lock_number(1.225, 5.73, 0.5, 6.0, 600.0),
                         lock_number(1.225, 5.73, 0.5, 6.0, 600.0))
        self.assertEqual(flap_frequency_ratio(0.05), flap_frequency_ratio(0.05))


if __name__ == "__main__":
    unittest.main()
