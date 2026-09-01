#!/usr/bin/env python3
"""Gate 3 contract test: supersonic ramjet inlet.

Exercises scripts/ramjet_inlet_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (normal shock total pressure
recovery at the flight Mach; isentropic diffuser recovery; model
selection and diffuser exit total pressure; Kantrowitz contraction
limit CR_K(M); starting limit Mach by bisection; asymptotic maximum
contraction; start verdict; invalid inputs raise ValueError.

Anchors (computed independently, gamma = 1.4):
- normal_shock_total_pressure_ratio(2.0) = 0.720874
- normal_shock_total_pressure_ratio(3.0) = 0.328344
- normal_shock_total_pressure_ratio(1.0) = 1.0
- isentropic_pressure_recovery() = 1.0
- exit_total_pressure(100000, 2.0) = 72087.4 Pa
- kantrowitz_contraction_limit(2.0) = 1.216475
- kantrowitz_contraction_limit(3.0) = 1.390394
- kantrowitz_contraction_limit(4.0) = 1.487293
- kantrowitz_limit_mach(1.2) = 1.928050
- kantrowitz_limit_mach(1.3) = 2.410882
- kantrowitz_max_contraction() = 1.666129
- inlet_starts(2.0, 1.2) is True; inlet_starts(2.0, 1.3) is False
- Scenario M = 2.5, p0 = 26500 Pa, CR = 1.25: starts, recovery
  0.499015, exit total pressure 225942.6 Pa.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ramjet_inlet_logic as ril  # noqa: E402


class NormalShockRecoveryTest(unittest.TestCase):
    def test_anchor_recovery_mach2(self):
        self.assertAlmostEqual(
            ril.normal_shock_total_pressure_ratio(2.0), 0.720874, delta=1e-5
        )

    def test_anchor_recovery_mach3(self):
        self.assertAlmostEqual(
            ril.normal_shock_total_pressure_ratio(3.0), 0.328344, delta=1e-5
        )

    def test_recovery_mach1_unity(self):
        self.assertAlmostEqual(
            ril.normal_shock_total_pressure_ratio(1.0), 1.0, delta=1e-9
        )

    def test_recovery_closed_form(self):
        value = ril.normal_shock_total_pressure_ratio(2.0)
        self.assertAlmostEqual(
            value,
            ((2.4 * 4.0) / (0.4 * 4.0 + 2.0)) ** 3.5
            * (2.4 / (2.8 * 4.0 - 0.4)) ** 2.5,
            delta=1e-9,
        )

    def test_recovery_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ril.normal_shock_total_pressure_ratio(0.5)
        with self.assertRaises(ValueError):
            ril.normal_shock_total_pressure_ratio(-2.0)
        with self.assertRaises(ValueError):
            ril.normal_shock_total_pressure_ratio(2.0, gamma=1.0)


class PressureRecoveryTest(unittest.TestCase):
    def test_isentropic_recovery_unity(self):
        self.assertAlmostEqual(ril.isentropic_pressure_recovery(), 1.0)

    def test_default_model_is_normal_shock(self):
        self.assertAlmostEqual(
            ril.pressure_recovery(2.0), ril.normal_shock_total_pressure_ratio(2.0)
        )

    def test_isentropic_model_selection(self):
        self.assertAlmostEqual(ril.pressure_recovery(2.0, "isentropic"), 1.0)
        self.assertAlmostEqual(ril.pressure_recovery(3.0, "isentropic"), 1.0)

    def test_invalid_model_raises(self):
        with self.assertRaises(ValueError):
            ril.pressure_recovery(2.0, "oblique")
        with self.assertRaises(ValueError):
            ril.pressure_recovery(2.0, "")

    def test_invalid_mach_raises(self):
        with self.assertRaises(ValueError):
            ril.pressure_recovery(0.0, "isentropic")
        with self.assertRaises(ValueError):
            ril.pressure_recovery(0.5, "normal")
        with self.assertRaises(ValueError):
            ril.pressure_recovery(-1.0, "normal")


class ExitTotalPressureTest(unittest.TestCase):
    def test_anchor_exit_total_pressure(self):
        self.assertAlmostEqual(
            ril.exit_total_pressure(100000.0, 2.0), 72087.386, delta=0.01
        )

    def test_anchor_isentropic_exit(self):
        self.assertAlmostEqual(ril.exit_total_pressure(100000.0, 2.0, "isentropic"), 100000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ril.exit_total_pressure(0.0, 2.0)
        with self.assertRaises(ValueError):
            ril.exit_total_pressure(-100.0, 2.0)


class FreestreamTotalPressureTest(unittest.TestCase):
    def test_anchor_freestream_total_pressure(self):
        self.assertAlmostEqual(
            ril.freestream_total_pressure(26500.0, 2.5), 452777.344, delta=0.01
        )

    def test_subsonic_value(self):
        self.assertAlmostEqual(
            ril.freestream_total_pressure(101325.0, 0.0), 101325.0, delta=1e-6
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ril.freestream_total_pressure(0.0, 2.5)
        with self.assertRaises(ValueError):
            ril.freestream_total_pressure(26500.0, -1.0)


class KantrowitzContractionLimitTest(unittest.TestCase):
    def test_anchor_contraction_mach2(self):
        self.assertAlmostEqual(
            ril.kantrowitz_contraction_limit(2.0), 1.216475, delta=1e-5
        )

    def test_anchor_contraction_mach3(self):
        self.assertAlmostEqual(
            ril.kantrowitz_contraction_limit(3.0), 1.390394, delta=1e-5
        )

    def test_anchor_contraction_mach4(self):
        self.assertAlmostEqual(
            ril.kantrowitz_contraction_limit(4.0), 1.487293, delta=1e-5
        )

    def test_contraction_mach1_unity(self):
        self.assertAlmostEqual(
            ril.kantrowitz_contraction_limit(1.0), 1.0, delta=1e-9
        )

    def test_contraction_monotone_in_mach(self):
        self.assertGreater(
            ril.kantrowitz_contraction_limit(2.5),
            ril.kantrowitz_contraction_limit(2.0),
        )

    def test_contraction_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ril.kantrowitz_contraction_limit(0.5)
        with self.assertRaises(ValueError):
            ril.kantrowitz_contraction_limit(2.0, gamma=1.0)


class KantrowitzLimitMachTest(unittest.TestCase):
    def test_anchor_limit_mach_1_2(self):
        self.assertAlmostEqual(
            ril.kantrowitz_limit_mach(1.2), 1.928050, delta=1e-4
        )

    def test_anchor_limit_mach_1_3(self):
        self.assertAlmostEqual(
            ril.kantrowitz_limit_mach(1.3), 2.410882, delta=1e-4
        )

    def test_limit_mach_no_contraction(self):
        self.assertAlmostEqual(ril.kantrowitz_limit_mach(1.0), 1.0)
        self.assertAlmostEqual(ril.kantrowitz_limit_mach(0.9), 1.0)
        self.assertAlmostEqual(ril.kantrowitz_limit_mach(0.5), 1.0)

    def test_limit_mach_roundtrip(self):
        # The limit Mach of a contraction ratio restarts that ratio.
        cr = 1.25
        mach = ril.kantrowitz_limit_mach(cr)
        self.assertAlmostEqual(
            ril.kantrowitz_contraction_limit(mach), cr, delta=1e-5
        )

    def test_max_contraction_asymptote(self):
        self.assertAlmostEqual(
            ril.kantrowitz_max_contraction(), 1.666129, delta=1e-4
        )
        self.assertGreater(ril.kantrowitz_max_contraction(), 1.66)
        self.assertLess(ril.kantrowitz_max_contraction(), 1.67)

    def test_limit_mach_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ril.kantrowitz_limit_mach(-0.5)
        with self.assertRaises(ValueError):
            ril.kantrowitz_limit_mach(1.7)
        with self.assertRaises(ValueError):
            ril.kantrowitz_limit_mach(1.2, gamma=1.0)


class InletStartTest(unittest.TestCase):
    def test_starts_at_or_below_limit(self):
        self.assertTrue(ril.inlet_starts(2.0, 1.2))
        self.assertFalse(ril.inlet_starts(2.0, 1.3))
        self.assertTrue(ril.inlet_starts(3.0, 1.3))

    def test_start_boundary(self):
        # CR below the limit starts, above it does not, at M = 2.5.
        self.assertTrue(ril.inlet_starts(2.5, 1.31))
        self.assertFalse(ril.inlet_starts(2.5, 1.32))

    def test_mach1_trivial_start(self):
        self.assertTrue(ril.inlet_starts(1.0, 1.0))
        self.assertTrue(ril.inlet_starts(1.0, 0.8))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ril.inlet_starts(0.9, 1.1)
        with self.assertRaises(ValueError):
            ril.inlet_starts(2.0, 0.0)


class ScenarioTest(unittest.TestCase):
    def test_scenario_starting_check(self):
        # M = 2.5, CR = 1.25: the inlet starts (limit 1.3158).
        self.assertTrue(ril.inlet_starts(2.5, 1.25))

    def test_scenario_recovery(self):
        self.assertAlmostEqual(
            ril.pressure_recovery(2.5), 0.499015, delta=1e-5
        )

    def test_scenario_exit_total_pressure(self):
        # p0 = 26500 Pa at M = 2.5: pt0 = 452777.3 Pa,
        # pt2 = 0.499015 * 452777.3 = 225942.6 Pa.
        pt0 = ril.freestream_total_pressure(26500.0, 2.5)
        pt2 = ril.exit_total_pressure(pt0, 2.5)
        self.assertAlmostEqual(pt0, 452777.344, delta=0.01)
        self.assertAlmostEqual(pt2, 225942.6, delta=0.5)
        self.assertAlmostEqual(pt2, pt0 * 0.499014812, delta=0.5)

    def test_scenario_math_cross_check(self):
        # Recovery formula evaluated directly for M = 2.5.
        self.assertAlmostEqual(
            ril.normal_shock_total_pressure_ratio(2.5),
            ((2.4 * 6.25) / (0.4 * 6.25 + 2.0)) ** 3.5
            * (2.4 / (2.8 * 6.25 - 0.4)) ** 2.5,
            delta=1e-9,
        )
        self.assertGreater(math.sqrt(2.0), 1.0)  # sanity import


if __name__ == "__main__":
    unittest.main(verbosity=2)
