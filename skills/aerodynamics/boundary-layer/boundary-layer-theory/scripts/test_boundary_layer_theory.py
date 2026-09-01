#!/usr/bin/env python3
"""Gate 3 contract test: boundary-layer theory.

Exercises scripts/boundary_layer_theory_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - Blasius laminar
flat-plate thicknesses (delta = 5.0 x / sqrt(Re_x), delta* = 1.7208 x /
sqrt(Re_x), theta = 0.664 x / sqrt(Re_x)) and skin friction (0.664 and
1.328 / sqrt(Re_x)), turbulent 1/7 power-law values (delta = 0.37 x /
Re_x^(1/5), delta* = delta / 8, theta = 7 delta / 72, Cf 0.0592 and
0.074 / Re_x^(1/5)), the log-law skin-friction correlation, the shape
factor H = delta* / theta (2.5916 laminar, 9/7 turbulent) with the 1/7
profile ratios verified by numerical integration, and regime
classification at the transition Reynolds number (5e5 smooth plate),
with ValueError on non-positive inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import boundary_layer_theory_logic as bl  # noqa: E402


class ReynoldsNumberTest(unittest.TestCase):
    def test_known_condition(self):
        # Sea level: rho 1.225, mu 1.81e-5, V 50 m/s, L 1 m
        self.assertAlmostEqual(
            bl.reynolds_number(1.225, 50.0, 1.0, 1.81e-5), 3.384e6, delta=1e3
        )

    def test_kinematic_viscosity(self):
        self.assertAlmostEqual(
            bl.kinematic_viscosity(1.81e-5, 1.225), 1.4776e-5, delta=1e-8
        )

    def test_reynolds_scales_linearly(self):
        re1 = bl.reynolds_number(1.225, 50.0, 2.0, 1.81e-5)
        re2 = bl.reynolds_number(1.225, 50.0, 1.0, 1.81e-5)
        self.assertAlmostEqual(re1, 2.0 * re2, delta=1e-6)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            bl.reynolds_number(0.0, 50.0, 1.0, 1.81e-5)
        with self.assertRaises(ValueError):
            bl.reynolds_number(1.225, -50.0, 1.0, 1.81e-5)
        with self.assertRaises(ValueError):
            bl.reynolds_number(1.225, 50.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            bl.kinematic_viscosity(1.81e-5, 0.0)


class BlasiusLaminarTest(unittest.TestCase):
    def test_known_station(self):
        # Re_x = 1e6, x = 1 m: delta 5e-3, delta* 1.7208e-3, theta 6.64e-4
        self.assertAlmostEqual(bl.blasius_thickness(1.0, 1e6), 5.0e-3, delta=1e-6)
        self.assertAlmostEqual(
            bl.blasius_displacement_thickness(1.0, 1e6), 1.7208e-3, delta=1e-7
        )
        self.assertAlmostEqual(
            bl.blasius_momentum_thickness(1.0, 1e6), 6.64e-4, delta=1e-7
        )

    def test_similarity_scaling(self):
        # Same x / sqrt(Re_x) gives the same thicknesses
        self.assertAlmostEqual(
            bl.blasius_thickness(2.0, 4e6), bl.blasius_thickness(1.0, 1e6), delta=1e-9
        )

    def test_skin_friction_values(self):
        # Cf local 0.664e-3, average 1.328e-3 at Re_x = 1e6; factor of two
        self.assertAlmostEqual(
            bl.blasius_skin_friction(1e6), 6.64e-4, delta=1e-7
        )
        self.assertAlmostEqual(
            bl.blasius_average_skin_friction(1e6), 1.328e-3, delta=1e-7
        )
        self.assertAlmostEqual(
            bl.blasius_average_skin_friction(1e6),
            2.0 * bl.blasius_skin_friction(1e6),
            delta=1e-9,
        )

    def test_shape_factor(self):
        dstar = bl.blasius_displacement_thickness(1.0, 1e6)
        theta = bl.blasius_momentum_thickness(1.0, 1e6)
        self.assertAlmostEqual(bl.shape_factor(dstar, theta), 2.5916, delta=1e-3)

    def test_thickness_ordering(self):
        dstar = bl.blasius_displacement_thickness(1.0, 1e6)
        theta = bl.blasius_momentum_thickness(1.0, 1e6)
        self.assertLess(theta, dstar)
        self.assertLess(dstar, bl.blasius_thickness(1.0, 1e6))

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            bl.blasius_thickness(0.0, 1e6)
        with self.assertRaises(ValueError):
            bl.blasius_thickness(1.0, 0.0)
        with self.assertRaises(ValueError):
            bl.blasius_displacement_thickness(-1.0, 1e6)
        with self.assertRaises(ValueError):
            bl.blasius_skin_friction(-1e5)


class TurbulentPowerLawTest(unittest.TestCase):
    def test_known_station(self):
        # Re_x = 1e7, x = 1 m: delta ~ 1.473e-2
        delta = bl.turb_power_thickness(1.0, 1e7)
        self.assertAlmostEqual(delta, 1.473e-2, delta=1e-4)
        self.assertAlmostEqual(
            bl.turb_power_displacement_thickness(1.0, 1e7), delta / 8.0, delta=1e-9
        )
        self.assertAlmostEqual(
            bl.turb_power_momentum_thickness(1.0, 1e7), 7.0 * delta / 72.0, delta=1e-9
        )

    def test_profile_ratios_integrated(self):
        # Numerically integrate the 1/7 profile ratios: 1/8 and 7/72
        n = 20000
        h = 1.0 / n
        s1 = 0.0
        s2 = 0.0
        for i in range(1, n):
            eta = i * h
            u = eta ** (1.0 / 7.0)
            s1 += 1.0 - u
            s2 += u * (1.0 - u)
        s1 = (s1 + 0.5 * 1.0) * h  # endpoint eta=1: 1 - 1 = 0; eta=0: 1 - 0 = 1
        s2 = s2 * h
        self.assertAlmostEqual(s1, 1.0 / 8.0, delta=2e-4)
        self.assertAlmostEqual(s2, 7.0 / 72.0, delta=2e-4)

    def test_shape_factor_nine_sevenths(self):
        dstar = bl.turb_power_displacement_thickness(1.0, 1e7)
        theta = bl.turb_power_momentum_thickness(1.0, 1e7)
        self.assertAlmostEqual(bl.shape_factor(dstar, theta), 9.0 / 7.0, delta=1e-9)

    def test_skin_friction_values(self):
        # Re_x = 1e7: local 0.0592 / 10^1.4 ~ 2.357e-3, average 0.074 / 10^1.4
        self.assertAlmostEqual(
            bl.turb_power_skin_friction(1e7), 2.357e-3, delta=1e-5
        )
        self.assertAlmostEqual(
            bl.turb_power_average_skin_friction(1e7), 2.946e-3, delta=1e-5
        )
        self.assertAlmostEqual(
            bl.turb_power_average_skin_friction(1e7),
            1.25 * bl.turb_power_skin_friction(1e7),
            delta=1e-9,
        )

    def test_turbulent_beats_laminar(self):
        # At the same Re_x the turbulent layer is thicker and draggier
        re_x = 1e6
        self.assertGreater(
            bl.turb_power_thickness(1.0, re_x), bl.blasius_thickness(1.0, re_x)
        )
        self.assertGreater(
            bl.turb_power_skin_friction(re_x), bl.blasius_skin_friction(re_x)
        )

    def test_log_law_correlation(self):
        # 0.455 / (log10 1e7)^2.58 ~ 3.002e-3, close to the power-law average
        self.assertAlmostEqual(bl.cf_turbulent_log_law(1e7), 3.002e-3, delta=1e-5)
        self.assertAlmostEqual(
            bl.cf_turbulent_log_law(1e6),
            0.455 / (math.log10(1e6) ** 2.58),
            delta=1e-9,
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            bl.turb_power_thickness(1.0, 0.0)
        with self.assertRaises(ValueError):
            bl.turb_power_skin_friction(-1.0)
        with self.assertRaises(ValueError):
            bl.cf_turbulent_log_law(1.0)
        with self.assertRaises(ValueError):
            bl.cf_turbulent_log_law(0.5)


class RegimeClassificationTest(unittest.TestCase):
    def test_default_transition(self):
        self.assertEqual(bl.classify_regime(1e5), "laminar")
        self.assertEqual(bl.classify_regime(1e6), "turbulent")
        # Default transition Reynolds number is 5e5 (smooth flat plate)
        self.assertEqual(bl.classify_regime(4.99e5), "laminar")
        self.assertEqual(bl.classify_regime(5e5), "turbulent")

    def test_custom_transition(self):
        self.assertEqual(bl.classify_regime(3e5, re_tr=3e5), "turbulent")
        self.assertEqual(bl.classify_regime(2.99e5, re_tr=3e5), "laminar")

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            bl.classify_regime(0.0)
        with self.assertRaises(ValueError):
            bl.classify_regime(1e6, re_tr=0.0)


class FlatPlateSummaryTest(unittest.TestCase):
    def test_laminar_summary(self):
        # Re_x = 1e5 is below the 5e5 default transition: laminar Blasius
        s = bl.flat_plate_thicknesses(1.0, 1e5)
        self.assertEqual(s["regime"], "laminar")
        self.assertAlmostEqual(s["delta"], 1.581e-2, delta=1e-4)
        self.assertAlmostEqual(
            s["delta"], bl.blasius_thickness(1.0, 1e5), delta=1e-9
        )
        self.assertAlmostEqual(
            s["delta_star"], bl.blasius_displacement_thickness(1.0, 1e5), delta=1e-9
        )
        self.assertAlmostEqual(
            s["theta"], bl.blasius_momentum_thickness(1.0, 1e5), delta=1e-9
        )
        self.assertAlmostEqual(
            s["cf_local"], bl.blasius_skin_friction(1e5), delta=1e-9
        )
        self.assertAlmostEqual(
            s["cf_average"], bl.blasius_average_skin_friction(1e5), delta=1e-9
        )

    def test_turbulent_summary(self):
        s = bl.flat_plate_thicknesses(1.0, 1e7)
        self.assertEqual(s["regime"], "turbulent")
        self.assertAlmostEqual(s["delta"], 1.473e-2, delta=1e-4)
        self.assertAlmostEqual(s["shape_factor"], 9.0 / 7.0, delta=1e-9)

    def test_custom_transition_in_summary(self):
        s = bl.flat_plate_thicknesses(1.0, 4e5, re_tr=2e5)
        self.assertEqual(s["regime"], "turbulent")
        s = bl.flat_plate_thicknesses(1.0, 1e5, re_tr=2e5)
        self.assertEqual(s["regime"], "laminar")

    def test_shape_factor_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            bl.shape_factor(1e-3, 0.0)
        with self.assertRaises(ValueError):
            bl.shape_factor(-1e-3, 1e-4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
