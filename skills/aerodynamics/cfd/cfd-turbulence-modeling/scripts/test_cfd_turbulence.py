#!/usr/bin/env python3
"""Gate 3 contract test: CFD turbulence modeling (y+, friction velocity).

Exercises scripts/cfd_turbulence_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - y plus for the first
cell height, friction velocity from wall shear stress or skin
friction coefficient, and turbulence model recommendation for the
target y+; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cfd_turbulence_logic as ctl  # noqa: E402


class YPlusTest(unittest.TestCase):
    def test_first_cell_anchor(self):
        # y = 1e-5 m, u_tau = 1.5 m/s, nu = 1.46e-5 m^2/s
        self.assertAlmostEqual(ctl.y_plus(1e-5, 1.5, 1.46e-5), 1.0274, delta=1e-3)

    def test_scales_linearly_with_y(self):
        yp = ctl.y_plus(1e-5, 1.5, 1.46e-5)
        self.assertAlmostEqual(ctl.y_plus(2e-5, 1.5, 1.46e-5), 2 * yp, delta=1e-3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ctl.y_plus(0.0, 1.5, 1.46e-5)
        with self.assertRaises(ValueError):
            ctl.y_plus(-1e-5, 1.5, 1.46e-5)
        with self.assertRaises(ValueError):
            ctl.y_plus(1e-5, 0.0, 1.46e-5)
        with self.assertRaises(ValueError):
            ctl.y_plus(1e-5, -1.5, 1.46e-5)
        with self.assertRaises(ValueError):
            ctl.y_plus(1e-5, 1.5, 0.0)
        with self.assertRaises(ValueError):
            ctl.y_plus(1e-5, 1.5, -1.46e-5)


class FrictionVelocityTest(unittest.TestCase):
    def test_wall_shear_anchor(self):
        # tau_w = 2.0 Pa, rho = 1.225 kg/m^3
        self.assertAlmostEqual(ctl.friction_velocity(2.0, 1.225), 1.2778, delta=1e-3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ctl.friction_velocity(0.0, 1.225)
        with self.assertRaises(ValueError):
            ctl.friction_velocity(-2.0, 1.225)
        with self.assertRaises(ValueError):
            ctl.friction_velocity(2.0, 0.0)
        with self.assertRaises(ValueError):
            ctl.friction_velocity(2.0, -1.225)


class FrictionVelocityFromCfTest(unittest.TestCase):
    def test_cf_anchor(self):
        # cf = 0.002, v_inf = 100 m/s
        self.assertAlmostEqual(
            ctl.friction_velocity_from_cf(0.002, 100), 3.1623, delta=1e-3
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ctl.friction_velocity_from_cf(0.0, 100)
        with self.assertRaises(ValueError):
            ctl.friction_velocity_from_cf(-0.002, 100)
        with self.assertRaises(ValueError):
            ctl.friction_velocity_from_cf(0.002, 0.0)
        with self.assertRaises(ValueError):
            ctl.friction_velocity_from_cf(0.002, -100)


class TurbulenceModelRecommendationTest(unittest.TestCase):
    def test_yplus_one_sst(self):
        self.assertEqual(ctl.turbulence_model_recommendation(1, False), "k-omega-sst")

    def test_yplus_ten_realizable(self):
        self.assertEqual(
            ctl.turbulence_model_recommendation(10, True), "k-epsilon-realizable"
        )

    def test_yplus_hundred_wall_function(self):
        self.assertEqual(
            ctl.turbulence_model_recommendation(100, False), "sa-wall-function"
        )

    def test_yplus_four_hundred_wall_model_check(self):
        self.assertEqual(
            ctl.turbulence_model_recommendation(400, False), "wall-model-check"
        )

    def test_boundaries(self):
        # <= 1 is sst; 30 sits in the realizable band; 300 in the
        # wall-function band; above 300 is wall-model-check.
        self.assertEqual(
            ctl.turbulence_model_recommendation(1.0, False), "k-omega-sst"
        )
        self.assertEqual(
            ctl.turbulence_model_recommendation(30.0, False), "k-epsilon-realizable"
        )
        self.assertEqual(
            ctl.turbulence_model_recommendation(300.0, False), "sa-wall-function"
        )
        self.assertEqual(
            ctl.turbulence_model_recommendation(300.1, False), "wall-model-check"
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ctl.turbulence_model_recommendation(0, False)
        with self.assertRaises(ValueError):
            ctl.turbulence_model_recommendation(-10, False)
        with self.assertRaises(ValueError):
            ctl.turbulence_model_recommendation(30, "yes")
        with self.assertRaises(ValueError):
            ctl.turbulence_model_recommendation(30, None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
