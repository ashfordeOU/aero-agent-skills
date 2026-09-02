#!/usr/bin/env python3
"""Gate 3 contract test: rocket sizing (rocket equation, delta-v).

Exercises scripts/rocket_sizing_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - delta-v from the rocket
equation, mass ratio from a delta-v requirement, propellant mass, and
staging delta-v summation; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rocket_sizing_logic as rsl  # noqa: E402


class RocketEquationDeltaVTest(unittest.TestCase):
    def test_anchor_delta_v(self):
        # 9.80665 * 300 * ln(4) = 4078.47 m/s
        self.assertAlmostEqual(
            rsl.rocket_equation_delta_v(300, 100000, 25000), 4078.47, delta=0.1
        )

    def test_more_propellant_more_delta_v(self):
        d1 = rsl.rocket_equation_delta_v(300, 100000, 50000)
        d2 = rsl.rocket_equation_delta_v(300, 100000, 25000)
        self.assertGreater(d2, d1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.rocket_equation_delta_v(0, 100000, 25000)  # isp <= 0
        with self.assertRaises(ValueError):
            rsl.rocket_equation_delta_v(-10, 100000, 25000)
        with self.assertRaises(ValueError):
            rsl.rocket_equation_delta_v(300, 0, 25000)  # m0 <= 0
        with self.assertRaises(ValueError):
            rsl.rocket_equation_delta_v(300, 100000, 0)  # mf <= 0
        with self.assertRaises(ValueError):
            rsl.rocket_equation_delta_v(300, 100000, 100000)  # mf >= m0
        with self.assertRaises(ValueError):
            rsl.rocket_equation_delta_v(300, 100000, 150000)


class MassRatioTest(unittest.TestCase):
    def test_anchor_mass_ratio(self):
        # exp(4078.59 / (9.80665 * 300)) = 4.0
        self.assertAlmostEqual(
            rsl.mass_ratio_from_delta_v(4078.59, 300), 4.0, delta=1e-3
        )

    def test_zero_delta_v_unit_ratio(self):
        self.assertAlmostEqual(rsl.mass_ratio_from_delta_v(0.0, 300), 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.mass_ratio_from_delta_v(-1.0, 300)  # delta_v < 0
        with self.assertRaises(ValueError):
            rsl.mass_ratio_from_delta_v(1000, 0)  # isp <= 0
        with self.assertRaises(ValueError):
            rsl.mass_ratio_from_delta_v(1000, -300)


class PropellantMassTest(unittest.TestCase):
    def test_anchor_propellant(self):
        self.assertEqual(rsl.propellant_mass(100000, 25000), 75000)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.propellant_mass(0, 25000)  # m0 <= 0
        with self.assertRaises(ValueError):
            rsl.propellant_mass(100000, 0)  # mf <= 0
        with self.assertRaises(ValueError):
            rsl.propellant_mass(25000, 25000)  # mf >= m0
        with self.assertRaises(ValueError):
            rsl.propellant_mass(25000, 30000)


class TotalStageDeltaVTest(unittest.TestCase):
    def test_anchor_stage_sum(self):
        self.assertEqual(rsl.total_stage_delta_v([2000, 1500]), 3500)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rsl.total_stage_delta_v([])  # empty list
        with self.assertRaises(ValueError):
            rsl.total_stage_delta_v([2000, -100])  # negative element


if __name__ == "__main__":
    unittest.main(verbosity=2)
