#!/usr/bin/env python3
"""Gate 3 contract test: nozzle design (isentropic rocket nozzle flow).

Exercises scripts/nozzle_design_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - exit Mach number from the
area ratio on the supersonic branch, choked throat mass flow, isentropic
exit velocity, ideal thrust with the pressure term, and the expansion
verdict against ambient pressure; invalid inputs raise ValueError.
All pressures in Pa, temperatures in K, areas in m^2, mass flow in
kg/s, velocity in m/s, thrust in N.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nozzle_design_logic as ndl  # noqa: E402


class ExitMachFromAreaRatioTest(unittest.TestCase):
    def test_textbook_air_mach_2(self):
        # Compressible flow tables: gamma = 1.4, M = 2 gives A/A* = 1.6875.
        self.assertAlmostEqual(
            ndl.exit_mach_from_area_ratio(1.6875, 1.4), 2.0, delta=1e-6
        )

    def test_gamma_1_2_area_ratio_4(self):
        # gamma = 1.2, A/A* = 4 converges cleanly to M = 2.6194.
        self.assertAlmostEqual(
            ndl.exit_mach_from_area_ratio(4.0, 1.2), 2.61945, delta=1e-3
        )

    def test_larger_area_ratio_higher_mach(self):
        m1 = ndl.exit_mach_from_area_ratio(5.0, 1.4)
        m2 = ndl.exit_mach_from_area_ratio(10.0, 1.4)
        self.assertGreater(m2, m1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ndl.exit_mach_from_area_ratio(1.0, 1.4)  # sonic, not supersonic
        with self.assertRaises(ValueError):
            ndl.exit_mach_from_area_ratio(0.5, 1.4)  # subsonic area ratio
        with self.assertRaises(ValueError):
            ndl.exit_mach_from_area_ratio(4.0, 1.0)  # gamma <= 1
        with self.assertRaises(ValueError):
            ndl.exit_mach_from_area_ratio(4.0, 0.8)


class MassFlowTest(unittest.TestCase):
    def test_anchor_choked_mass_flow(self):
        # Air (gamma = 1.4, R = 287), P0 = 1 MPa, T0 = 300 K, At = 0.01 m^2.
        self.assertAlmostEqual(
            ndl.mass_flow(1e6, 300, 0.01, 1.4, 287.0), 23.3356, delta=1e-3
        )

    def test_higher_chamber_pressure_more_flow(self):
        m1 = ndl.mass_flow(1e6, 300, 0.01)
        m2 = ndl.mass_flow(2e6, 300, 0.01)
        self.assertGreater(m2, m1)

    def test_higher_temperature_less_flow(self):
        m1 = ndl.mass_flow(1e6, 300, 0.01)
        m2 = ndl.mass_flow(1e6, 600, 0.01)
        self.assertGreater(m1, m2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ndl.mass_flow(0.0, 300, 0.01)  # P0 <= 0
        with self.assertRaises(ValueError):
            ndl.mass_flow(1e6, 0.0, 0.01)  # T0 <= 0
        with self.assertRaises(ValueError):
            ndl.mass_flow(1e6, 300, 0.0)  # At <= 0
        with self.assertRaises(ValueError):
            ndl.mass_flow(1e6, 300, 0.01, gamma=1.0)
        with self.assertRaises(ValueError):
            ndl.mass_flow(1e6, 300, 0.01, r_j_kgk=0.0)


class ExitVelocityTest(unittest.TestCase):
    def test_anchor_exit_velocity(self):
        # Air from P0 = 1 MPa, T0 = 300 K expanded to Pe = 0.1 MPa.
        self.assertAlmostEqual(
            ndl.exit_velocity(1e6, 300, 1e5, 1.4, 287.0), 539.0, delta=0.1
        )

    def test_no_expansion_zero_velocity(self):
        # Pe == P0 means no expansion: exit velocity must be zero.
        self.assertAlmostEqual(ndl.exit_velocity(1e6, 300, 1e6), 0.0, delta=1e-9)

    def test_lower_exit_pressure_higher_velocity(self):
        v1 = ndl.exit_velocity(1e6, 300, 5e5)
        v2 = ndl.exit_velocity(1e6, 300, 1e5)
        self.assertGreater(v2, v1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ndl.exit_velocity(1e6, 300, 0.0)  # Pe <= 0
        with self.assertRaises(ValueError):
            ndl.exit_velocity(0.0, 300, 1e5)  # P0 <= 0
        with self.assertRaises(ValueError):
            ndl.exit_velocity(1e6, 0.0, 1e5)  # T0 <= 0
        with self.assertRaises(ValueError):
            ndl.exit_velocity(1e6, 300, 1.2e6)  # Pe > P0


class IdealThrustTest(unittest.TestCase):
    def test_anchor_thrust_with_pressure_term(self):
        # mdot*ve = 25000 N plus (101325 - 100000) * 2 = 2650 N.
        self.assertAlmostEqual(
            ndl.ideal_thrust(10, 2500, 101325, 100000, 2), 27650.0, delta=1e-6
        )

    def test_matched_expansion_momentum_only(self):
        # Pe == Pa: the pressure term vanishes, F = mdot*ve.
        self.assertAlmostEqual(ndl.ideal_thrust(10, 2500, 1e5, 1e5, 2), 25000.0)

    def test_overexpanded_pressure_term_subtracts(self):
        # Pe < Pa: the pressure term (8e4 - 1e5) * 0.5 = -10000 N.
        self.assertAlmostEqual(ndl.ideal_thrust(10, 2500, 8e4, 1e5, 0.5), 15000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ndl.ideal_thrust(-1, 2500, 1e5, 1e5, 2)  # mdot < 0
        with self.assertRaises(ValueError):
            ndl.ideal_thrust(10, -2500, 1e5, 1e5, 2)  # ve < 0
        with self.assertRaises(ValueError):
            ndl.ideal_thrust(10, 2500, 0.0, 1e5, 2)  # Pe <= 0
        with self.assertRaises(ValueError):
            ndl.ideal_thrust(10, 2500, 1e5, 0.0, 2)  # Pa <= 0
        with self.assertRaises(ValueError):
            ndl.ideal_thrust(10, 2500, 1e5, 1e5, -1)  # Ae < 0


class OptimumExpansionTest(unittest.TestCase):
    def test_matched_is_optimum(self):
        self.assertEqual(ndl.optimum_expansion(1e6, 1e5, 1e5), "optimum")

    def test_underexpanded(self):
        # Pe > Pa: flow has not expanded enough, pressure term positive.
        self.assertEqual(ndl.optimum_expansion(1e6, 1.2e5, 1e5), "under")

    def test_overexpanded(self):
        # Pe < Pa: flow has expanded too far, pressure term negative.
        self.assertEqual(ndl.optimum_expansion(1e6, 8e4, 1e5), "over")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ndl.optimum_expansion(0.0, 1e5, 1e5)  # P0 <= 0
        with self.assertRaises(ValueError):
            ndl.optimum_expansion(1e6, 0.0, 1e5)  # Pe <= 0
        with self.assertRaises(ValueError):
            ndl.optimum_expansion(1e6, 1e5, 0.0)  # Pa <= 0
        with self.assertRaises(ValueError):
            ndl.optimum_expansion(1e6, 1.2e6, 1e5)  # Pe > P0


if __name__ == "__main__":
    unittest.main(verbosity=2)
