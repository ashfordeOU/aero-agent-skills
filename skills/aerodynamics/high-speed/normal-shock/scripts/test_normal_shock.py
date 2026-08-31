#!/usr/bin/env python3
"""Gate 3 contract test: normal shock relations.

Exercises scripts/normal_shock_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - downstream Mach number,
static pressure, density, and temperature ratios, and stagnation
pressure ratio across a normal shock from the upstream Mach number
M1 and the specific heat ratio gamma; invalid inputs raise
ValueError. All inputs and outputs are unitless; gamma defaults to
1.4 (air). Textbook anchor (Anderson, Modern Compressible Flow,
Table A.2) at M1 = 2.0, gamma = 1.4: M2 = 0.5773503, p2/p1 = 4.5,
T2/T1 = 1.6875, rho2/rho1 = 2.6666667, p02/p01 = 0.720875.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import normal_shock_logic as nsl  # noqa: E402


class DownstreamMachTest(unittest.TestCase):
    def test_analytic_check(self):
        # Anderson Table A.2: M2 = 0.5773503 at M1 = 2.0, gamma = 1.4.
        self.assertAlmostEqual(nsl.downstream_mach(2.0), 0.5773503, places=6)

    def test_subsonic_downstream(self):
        # The shock always decelerates the flow: M2 < 1 for any M1 > 1.
        for m1 in (1.2, 2.0, 3.0, 5.0):
            self.assertLess(nsl.downstream_mach(m1), 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.downstream_mach(1.0)
        with self.assertRaises(ValueError):
            nsl.downstream_mach(0.8)
        with self.assertRaises(ValueError):
            nsl.downstream_mach(2.0, 1.0)
        with self.assertRaises(ValueError):
            nsl.downstream_mach(2.0, 0.9)


class PressureRatioTest(unittest.TestCase):
    def test_analytic_check(self):
        # 1 + 2*1.4/2.4 * (4 - 1) = 1 + 3.5 = 4.5.
        self.assertAlmostEqual(nsl.pressure_ratio(2.0), 4.5, places=6)

    def test_ratio_exceeds_one(self):
        self.assertGreater(nsl.pressure_ratio(1.5), 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.pressure_ratio(1.0)


class DensityRatioTest(unittest.TestCase):
    def test_analytic_check(self):
        # 2.4*4 / (2 + 0.4*4) = 9.6 / 3.6 = 2.6666667.
        self.assertAlmostEqual(nsl.density_ratio(2.0), 2.6666667, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.density_ratio(0.5)


class TemperatureRatioTest(unittest.TestCase):
    def test_analytic_check(self):
        # 4.5 / 2.6666667 = 1.6875.
        self.assertAlmostEqual(nsl.temperature_ratio(2.0), 1.6875, places=6)

    def test_consistency_with_ratios(self):
        self.assertAlmostEqual(
            nsl.temperature_ratio(2.0),
            nsl.pressure_ratio(2.0) / nsl.density_ratio(2.0),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.temperature_ratio(1.0)


class StagnationPressureRatioTest(unittest.TestCase):
    def test_analytic_check(self):
        # Anderson Table A.2 rounds to 0.7209; exact value at M1 = 2.0,
        # gamma = 1.4 is 0.72087386...
        self.assertAlmostEqual(nsl.stagnation_pressure_ratio(2.0), 0.720874, places=6)

    def test_loss_below_one(self):
        # Stagnation pressure always falls across the shock.
        self.assertLess(nsl.stagnation_pressure_ratio(3.0), 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.stagnation_pressure_ratio(1.0)


class ShockPropertiesTest(unittest.TestCase):
    def test_all_ratios_present(self):
        props = nsl.shock_properties(2.0)
        self.assertAlmostEqual(props["m2"], 0.5773503, places=6)
        self.assertAlmostEqual(props["p2_p1"], 4.5, places=6)
        self.assertAlmostEqual(props["t2_t1"], 1.6875, places=6)
        self.assertAlmostEqual(props["rho2_rho1"], 2.6666667, places=6)
        # Exact value 0.72087386...; Anderson Table A.2 rounds to 0.7209.
        self.assertAlmostEqual(props["p02_p01"], 0.720874, places=6)

    def test_energy_consistency(self):
        # T2/T1 * rho2/rho1 must recover p2/p1 exactly.
        props = nsl.shock_properties(2.0)
        self.assertAlmostEqual(
            props["t2_t1"] * props["rho2_rho1"], props["p2_p1"], places=12
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            nsl.shock_properties(1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
