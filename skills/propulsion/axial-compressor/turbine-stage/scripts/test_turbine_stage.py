#!/usr/bin/env python3
"""Gate 3 contract test: axial turbine stage velocity-triangle logic.

stdlib unittest, offline, deterministic. Exercises
scripts/turbine_stage_logic.py against the analytic check
(Dixon convention, angles from the axial direction, radians):

  u = 300 m/s, ca = 200 m/s, alpha1 = atan(2.0), alpha2 = atan(0.5)
  beta1 = atan(u/ca - tan(alpha1)) = atan(-0.5) = -0.46365 rad
  beta2 = atan(u/ca - tan(alpha2)) = atan(1.0) = pi/4 rad
  w  = 300*200*(2.0 - 0.5) = 90000 J/kg
  phi = 200/300 = 0.6667
  psi = 90000/90000 = 1.0
  r  = 1 - 200/(2*300)*(2.0 + 0.5) = 1/6 = 0.1667
  nozzle kinetic c1^2/2 = ca^2*(1 + tan^2(alpha1))/2 = 100000 J/kg
  rotor kinetic w2^2/2 = ca^2*(1 + tan^2(beta2))/2 = 40000 J/kg
  eta_tt = 90000/(90000 + 0.05*100000 + 0.05*40000) = 0.9278
  eta_ts (axial exit) = 90000/(90000 + 5000 + 2000 + 20000) = 0.7692

Run: python3 scripts/test_turbine_stage.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from turbine_stage_logic import (  # noqa: E402
    specific_work,
    flow_coefficient,
    stage_loading,
    degree_of_reaction,
    relative_angle,
    blade_row_loss,
    total_to_total_efficiency,
    total_to_static_efficiency,
    stage_properties,
)

U = 300.0
CA = 200.0
ALPHA1 = math.atan(2.0)
ALPHA2 = math.atan(0.5)
BETA1 = math.atan(U / CA - math.tan(ALPHA1))
BETA2 = math.atan(U / CA - math.tan(ALPHA2))


class TestTurbineStage(unittest.TestCase):
    def test_relative_angle_relation(self):
        """tan(beta) = u/ca - tan(alpha) at the same axial station."""
        self.assertAlmostEqual(math.tan(BETA1), 300.0 / 200.0 - 2.0, places=4)
        self.assertAlmostEqual(math.tan(BETA2), 300.0 / 200.0 - 0.5, places=4)
        self.assertAlmostEqual(relative_angle(U, CA, ALPHA1), BETA1, places=4)

    def test_specific_work_analytic(self):
        self.assertAlmostEqual(specific_work(U, CA, ALPHA1, ALPHA2),
                               90000.0, places=4)

    def test_flow_coefficient_analytic(self):
        self.assertAlmostEqual(flow_coefficient(CA, U), 0.6667, places=4)

    def test_stage_loading_analytic(self):
        self.assertAlmostEqual(stage_loading(U, CA, ALPHA1, ALPHA2), 1.0,
                               places=4)

    def test_degree_of_reaction_analytic(self):
        self.assertAlmostEqual(degree_of_reaction(CA, U, ALPHA1, ALPHA2),
                               1.0 / 6.0, places=4)

    def test_degree_of_reaction_fifty_percent(self):
        """Symmetric 50% reaction design: u/ca = 0.5 with tan-sum 1.0."""
        r = degree_of_reaction(200.0, 100.0, math.pi / 4.0,
                               math.atan(-0.5))
        self.assertAlmostEqual(r, 0.5, places=4)
        self.assertAlmostEqual(specific_work(100.0, 200.0, math.pi / 4.0,
                                              math.atan(-0.5)),
                               30000.0, places=4)

    def test_degree_of_reaction_impulse(self):
        """Impulse stage: the whole enthalpy drop is in the nozzle row."""
        self.assertAlmostEqual(
            degree_of_reaction(CA, U, ALPHA1, math.atan(1.0)), 0.0, places=4)

    def test_blade_row_loss_analytic(self):
        self.assertAlmostEqual(blade_row_loss(CA, ALPHA1, 0.05), 5000.0,
                               places=4)
        self.assertAlmostEqual(blade_row_loss(CA, BETA2, 0.05), 2000.0,
                               places=4)

    def test_total_to_total_efficiency_analytic(self):
        # 90000/(90000 + 5000 + 2000) = 0.9278
        self.assertAlmostEqual(total_to_total_efficiency(U, CA, ALPHA1,
                                                         ALPHA2, BETA2),
                               0.9278, places=4)

    def test_total_to_static_efficiency_analytic(self):
        # 90000/(90000 + 5000 + 2000 + 20000) = 0.7692, axial exit
        self.assertAlmostEqual(total_to_static_efficiency(U, CA, ALPHA1,
                                                          ALPHA2, BETA2),
                               0.7692, places=4)

    def test_stage_properties_dict(self):
        props = stage_properties(U, CA, ALPHA1, ALPHA2)
        self.assertEqual(
            set(props.keys()),
            {"specific_work", "phi", "psi", "reaction", "eta_tt",
             "nozzle_loss", "rotor_loss"},
        )
        self.assertAlmostEqual(props["specific_work"], 90000.0, places=4)
        self.assertAlmostEqual(props["phi"], 0.6667, places=4)
        self.assertAlmostEqual(props["psi"], 1.0, places=4)
        self.assertAlmostEqual(props["reaction"], 1.0 / 6.0, places=4)
        self.assertAlmostEqual(props["eta_tt"], 0.9278, places=4)
        self.assertAlmostEqual(props["nozzle_loss"], 5000.0, places=4)
        self.assertAlmostEqual(props["rotor_loss"], 2000.0, places=4)

    def test_negative_work_sign_convention(self):
        """alpha1 < alpha2 turns the rotor the compressor way: no output."""
        w = specific_work(U, CA, ALPHA2, ALPHA1)
        self.assertLess(w, 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            specific_work(0.0, CA, ALPHA1, ALPHA2)
        with self.assertRaises(ValueError):
            specific_work(U, 0.0, ALPHA1, ALPHA2)
        with self.assertRaises(ValueError):
            flow_coefficient(CA, 0.0)
        with self.assertRaises(ValueError):
            stage_loading(0.0, CA, ALPHA1, ALPHA2)
        with self.assertRaises(ValueError):
            degree_of_reaction(CA, 0.0, ALPHA1, ALPHA2)
        with self.assertRaises(ValueError):
            relative_angle(0.0, CA, ALPHA1)
        with self.assertRaises(ValueError):
            blade_row_loss(CA, ALPHA1, -0.1)
        with self.assertRaises(ValueError):
            blade_row_loss(0.0, ALPHA1, 0.05)
        with self.assertRaises(ValueError):
            total_to_total_efficiency(U, CA, ALPHA1, ALPHA2, BETA2,
                                      zeta_n=-0.1)
        with self.assertRaises(ValueError):
            stage_properties(U, 0.0, ALPHA1, ALPHA2)


if __name__ == "__main__":
    unittest.main()
