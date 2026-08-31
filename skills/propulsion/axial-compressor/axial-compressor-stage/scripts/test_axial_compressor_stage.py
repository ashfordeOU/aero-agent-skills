#!/usr/bin/env python3
"""Gate 3 contract test: axial compressor stage velocity-triangle logic.

stdlib unittest, offline, deterministic. Exercises
scripts/axial_compressor_stage_logic.py against the analytic check
(Dixon convention, angles from the axial direction, radians):

  u = 250 m/s, ca = 150 m/s, alpha1 = 0, alpha2 = pi/4, t01 = 288 K
  beta1 = atan(u/ca - tan(alpha1)) = atan(1.66667) = 1.03038 rad
  beta2 = atan(u/ca - tan(alpha2)) = atan(0.66667) = 0.58800 rad
  w  = 250*150*(tan(pi/4) - tan(0)) = 37500 J/kg
  phi = 150/250 = 0.6
  psi = 37500/62500 = 0.6
  r  = 150/(2*250)*(tan(beta1) - tan(beta2)) = 0.3
  pi = (1 + 0.9*37500/(1005*288))**3.5 = 1.4711 (places=4)

Run: python3 scripts/test_axial_compressor_stage.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from axial_compressor_stage_logic import (  # noqa: E402
    specific_work,
    flow_coefficient,
    work_coefficient,
    degree_of_reaction,
    stage_pressure_ratio,
    stage_properties,
)

U = 250.0
CA = 150.0
ALPHA1 = 0.0
ALPHA2 = math.pi / 4.0
T01 = 288.0
BETA1 = math.atan(U / CA - math.tan(ALPHA1))
BETA2 = math.atan(U / CA - math.tan(ALPHA2))


class TestAxialCompressorStage(unittest.TestCase):
    def test_relative_angle_relation(self):
        """tan(beta) = u/ca - tan(alpha) at the same axial station."""
        self.assertAlmostEqual(math.tan(BETA1), 250.0 / 150.0, places=4)
        self.assertAlmostEqual(math.tan(BETA2), 250.0 / 150.0 - 1.0, places=4)

    def test_specific_work_analytic(self):
        self.assertAlmostEqual(specific_work(U, CA, ALPHA1, ALPHA2),
                               37500.0, places=4)

    def test_flow_coefficient_analytic(self):
        self.assertAlmostEqual(flow_coefficient(CA, U), 0.6, places=4)

    def test_work_coefficient_analytic(self):
        self.assertAlmostEqual(work_coefficient(U, CA, ALPHA1, ALPHA2),
                               0.6, places=4)

    def test_degree_of_reaction_analytic(self):
        self.assertAlmostEqual(degree_of_reaction(CA, U, BETA1, BETA2),
                               0.3, places=4)

    def test_stage_pressure_ratio_analytic(self):
        # (1 + 0.9*37500/(1005*288))**3.5 = 1.4711
        self.assertAlmostEqual(stage_pressure_ratio(U, CA, ALPHA1, ALPHA2,
                                                    T01), 1.4711, places=4)

    def test_stage_properties_dict(self):
        props = stage_properties(U, CA, ALPHA1, ALPHA2, BETA1, BETA2, T01)
        self.assertEqual(
            set(props.keys()),
            {"specific_work", "phi", "psi", "reaction", "pressure_ratio"},
        )
        self.assertAlmostEqual(props["specific_work"], 37500.0, places=4)
        self.assertAlmostEqual(props["phi"], 0.6, places=4)
        self.assertAlmostEqual(props["psi"], 0.6, places=4)
        self.assertAlmostEqual(props["reaction"], 0.3, places=4)
        self.assertAlmostEqual(props["pressure_ratio"], 1.4711, places=4)

    def test_negative_work_sign_convention(self):
        """alpha2 < alpha1 turns the rotor the other way: work is extracted."""
        w = specific_work(U, CA, ALPHA1, -ALPHA2)
        self.assertLess(w, 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            specific_work(0.0, CA, ALPHA1, ALPHA2)
        with self.assertRaises(ValueError):
            specific_work(U, 0.0, ALPHA1, ALPHA2)
        with self.assertRaises(ValueError):
            flow_coefficient(CA, 0.0)
        with self.assertRaises(ValueError):
            work_coefficient(0.0, CA, ALPHA1, ALPHA2)
        with self.assertRaises(ValueError):
            degree_of_reaction(CA, 0.0, BETA1, BETA2)
        with self.assertRaises(ValueError):
            stage_pressure_ratio(U, CA, ALPHA1, ALPHA2, 0.0)
        with self.assertRaises(ValueError):
            stage_properties(U, CA, ALPHA1, ALPHA2, BETA1, BETA2, 0.0)


if __name__ == "__main__":
    unittest.main()
