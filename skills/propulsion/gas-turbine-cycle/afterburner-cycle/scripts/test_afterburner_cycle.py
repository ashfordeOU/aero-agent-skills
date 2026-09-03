#!/usr/bin/env python3
"""Gate 3 contract test for afterburner_cycle_logic.py (stdlib unittest).

Run directly:
    python3 scripts/test_afterburner_cycle.py
No network, no third-party imports. Asserts the worked anchors of the
afterburner (reheat) cycle block: reheat fuel-air ratio and fuel flow,
fully expanded ideal nozzle exit velocities, dry and reheat gross thrust,
thrust augmentation ratio, and the SFC with and without reheat, plus
scaling trends, internal consistency identities, and non-physical input
rejection.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import afterburner_cycle_logic as ab

# Worked example inputs (FAR-33 engine context, augmented turbofan).
T04 = 900.0        # K, turbine exit total temperature
F_CORE = 0.02      # core fuel-air ratio
MDOT = 100.0       # kg/s, core air mass flow
T05 = 1700.0       # K, afterburner exit (nozzle entry) total temperature
P04 = 3.0e5        # Pa, nozzle entry total pressure
P_AMB = 1.01325e5  # Pa, ambient pressure


class TestAfterburnerFar(unittest.TestCase):
    """Reheat fuel-air ratio from the duct energy balance."""

    def test_worked_example_value(self):
        # 1.02 * 1150 * 800 / (0.97 * 43e6) = 0.022498.
        self.assertAlmostEqual(ab.afterburner_far(T04, T05, F_CORE),
                               0.022498, delta=1e-6)

    def test_scales_linearly_with_temperature_rise(self):
        base = ab.afterburner_far(T04, T05, F_CORE)
        doubled = ab.afterburner_far(T04, T04 + 2.0 * (T05 - T04), F_CORE)
        self.assertAlmostEqual(doubled, 2.0 * base, places=9)

    def test_core_far_weighting_factor(self):
        # The rise is carried by (1 + f_core) kg of gas per kg of air.
        f_high = ab.afterburner_far(T04, T05, 0.05)
        f_low = ab.afterburner_far(T04, T05, 0.01)
        self.assertAlmostEqual(f_high / f_low, 1.05 / 1.01, places=9)

    def test_raises_when_t05_equals_t04(self):
        with self.assertRaises(ValueError):
            ab.afterburner_far(T04, T04, F_CORE)

    def test_raises_when_t05_below_t04(self):
        with self.assertRaises(ValueError):
            ab.afterburner_far(T04, T04 - 100.0, F_CORE)

    def test_raises_when_t04_nonpositive(self):
        with self.assertRaises(ValueError):
            ab.afterburner_far(0.0, T05, F_CORE)
        with self.assertRaises(ValueError):
            ab.afterburner_far(-50.0, T05, F_CORE)

    def test_raises_when_f_core_negative(self):
        with self.assertRaises(ValueError):
            ab.afterburner_far(T04, T05, -0.01)


class TestAfterburnerFuelFlow(unittest.TestCase):
    """Reheat fuel mass flow for the core mass flow."""

    def test_worked_example_value(self):
        fab = ab.afterburner_far(T04, T05, F_CORE)
        self.assertAlmostEqual(ab.afterburner_fuel_flow(fab, MDOT),
                               2.2498, delta=1e-3)

    def test_scales_linearly_with_mass_flow(self):
        fab = ab.afterburner_far(T04, T05, F_CORE)
        half = ab.afterburner_fuel_flow(fab, 50.0)
        full = ab.afterburner_fuel_flow(fab, 100.0)
        self.assertAlmostEqual(half, 0.5 * full, places=9)

    def test_zero_ratio_gives_zero_flow(self):
        self.assertEqual(ab.afterburner_fuel_flow(0.0, MDOT), 0.0)

    def test_raises_on_nonpositive_mass_flow_or_ratio(self):
        fab = ab.afterburner_far(T04, T05, F_CORE)
        with self.assertRaises(ValueError):
            ab.afterburner_fuel_flow(fab, 0.0)
        with self.assertRaises(ValueError):
            ab.afterburner_fuel_flow(fab, -10.0)
        with self.assertRaises(ValueError):
            ab.afterburner_fuel_flow(-0.1, MDOT)


class TestNozzleExitVelocity(unittest.TestCase):
    """Fully expanded ideal nozzle exit velocity."""

    def test_dry_velocity_worked_example(self):
        self.assertAlmostEqual(ab.nozzle_exit_velocity(T04, P04, P_AMB),
                               699.1, delta=1.0)

    def test_reheat_velocity_worked_example(self):
        self.assertAlmostEqual(ab.nozzle_exit_velocity(T05, P04, P_AMB),
                               960.8, delta=1.0)

    def test_velocity_increases_with_temperature(self):
        hot = ab.nozzle_exit_velocity(T05, P04, P_AMB)
        cold = ab.nozzle_exit_velocity(T04, P04, P_AMB)
        self.assertGreater(hot, cold)

    def test_velocity_increases_with_pressure_ratio(self):
        low_pr = ab.nozzle_exit_velocity(T04, 2.0e5, P_AMB)
        high_pr = ab.nozzle_exit_velocity(T04, 3.0e5, P_AMB)
        self.assertGreater(high_pr, low_pr)

    def test_raises_when_p_total_leq_p_amb(self):
        with self.assertRaises(ValueError):
            ab.nozzle_exit_velocity(T04, P_AMB, P_AMB)
        with self.assertRaises(ValueError):
            ab.nozzle_exit_velocity(T04, 0.5e5, P_AMB)

    def test_raises_on_nonpositive_temperature_or_ambient(self):
        with self.assertRaises(ValueError):
            ab.nozzle_exit_velocity(0.0, P04, P_AMB)
        with self.assertRaises(ValueError):
            ab.nozzle_exit_velocity(T04, P04, 0.0)


class TestThrust(unittest.TestCase):
    """Dry and reheat gross thrust, and the augmentation ratio."""

    def test_dry_thrust_worked_example(self):
        self.assertAlmostEqual(
            ab.thrust_dry(T04, P04, P_AMB, MDOT, F_CORE), 71307.0, delta=50.0)

    def test_reheat_thrust_worked_example(self):
        fab = ab.afterburner_far(T04, T05, F_CORE)
        self.assertAlmostEqual(
            ab.thrust_reheat(T05, P04, P_AMB, MDOT, F_CORE, fab),
            100162.0, delta=50.0)

    def test_reheat_thrust_exceeds_dry_thrust(self):
        fab = ab.afterburner_far(T04, T05, F_CORE)
        fr = ab.thrust_reheat(T05, P04, P_AMB, MDOT, F_CORE, fab)
        fd = ab.thrust_dry(T04, P04, P_AMB, MDOT, F_CORE)
        self.assertGreater(fr, fd)

    def test_thrust_scales_with_mass_flow(self):
        fab = ab.afterburner_far(T04, T05, F_CORE)
        fr_full = ab.thrust_reheat(T05, P04, P_AMB, MDOT, F_CORE, fab)
        fr_half = ab.thrust_reheat(T05, P04, P_AMB, 50.0, F_CORE, fab)
        self.assertAlmostEqual(fr_half, 0.5 * fr_full, places=6)

    def test_raises_on_zero_mass_flow(self):
        with self.assertRaises(ValueError):
            ab.thrust_dry(T04, P04, P_AMB, 0.0, F_CORE)

    def test_raises_when_p04_equals_p_amb(self):
        with self.assertRaises(ValueError):
            ab.thrust_reheat(T05, P_AMB, P_AMB, MDOT, F_CORE, 0.02)

    def test_augmentation_ratio_worked_example(self):
        fab = ab.afterburner_far(T04, T05, F_CORE)
        fr = ab.thrust_reheat(T05, P04, P_AMB, MDOT, F_CORE, fab)
        fd = ab.thrust_dry(T04, P04, P_AMB, MDOT, F_CORE)
        self.assertAlmostEqual(
            ab.augmentation_ratio(fr, fd), 1.405, delta=0.005)

    def test_augmentation_identity_when_thrusts_equal(self):
        self.assertEqual(ab.augmentation_ratio(50000.0, 50000.0), 1.0)

    def test_augmentation_raises_on_nonpositive_dry_thrust(self):
        with self.assertRaises(ValueError):
            ab.augmentation_ratio(100000.0, 0.0)
        with self.assertRaises(ValueError):
            ab.augmentation_ratio(100000.0, -1.0)


class TestSfc(unittest.TestCase):
    """Specific fuel consumption with and without reheat."""

    def test_sfc_dry_worked_example(self):
        fd = ab.thrust_dry(T04, P04, P_AMB, MDOT, F_CORE)
        self.assertAlmostEqual(ab.sfc(F_CORE * MDOT, fd),
                               2.805e-5, delta=0.02 * 2.805e-5)

    def test_sfc_reheat_worked_example(self):
        fab = ab.afterburner_far(T04, T05, F_CORE)
        fr = ab.thrust_reheat(T05, P04, P_AMB, MDOT, F_CORE, fab)
        mdot_f_total = (F_CORE + fab) * MDOT
        self.assertAlmostEqual(ab.sfc(mdot_f_total, fr),
                               4.242e-5, delta=0.02 * 4.242e-5)

    def test_reheat_sfc_exceeds_dry_sfc(self):
        # Reheat adds fuel but only modestly raises thrust.
        fd = ab.thrust_dry(T04, P04, P_AMB, MDOT, F_CORE)
        fab = ab.afterburner_far(T04, T05, F_CORE)
        fr = ab.thrust_reheat(T05, P04, P_AMB, MDOT, F_CORE, fab)
        self.assertGreater(ab.sfc((F_CORE + fab) * MDOT, fr),
                           ab.sfc(F_CORE * MDOT, fd))

    def test_raises_on_nonpositive_thrust_or_negative_fuel(self):
        with self.assertRaises(ValueError):
            ab.sfc(2.0, 0.0)
        with self.assertRaises(ValueError):
            ab.sfc(2.0, -1.0)
        with self.assertRaises(ValueError):
            ab.sfc(-0.5, 70000.0)


class TestAnalyze(unittest.TestCase):
    """Complete afterburner cycle summary dict."""

    def test_analyze_worked_example_all_keys(self):
        r = ab.analyze(T04, F_CORE, MDOT, T05, P04, P_AMB)
        self.assertEqual(
            sorted(r.keys()),
            sorted(["f_ab", "mdot_f_ab", "v_dry", "v_reheat", "F_dry",
                    "F_reheat", "augmentation_ratio", "sfc_dry",
                    "sfc_reheat"]))
        self.assertAlmostEqual(r["f_ab"], 0.022498, delta=1e-6)
        self.assertAlmostEqual(r["mdot_f_ab"], 2.2498, delta=1e-3)
        self.assertAlmostEqual(r["v_dry"], 699.1, delta=1.0)
        self.assertAlmostEqual(r["v_reheat"], 960.8, delta=1.0)
        self.assertAlmostEqual(r["F_dry"], 71307.0, delta=50.0)
        self.assertAlmostEqual(r["F_reheat"], 100162.0, delta=50.0)
        self.assertAlmostEqual(r["augmentation_ratio"], 1.405, delta=0.005)
        self.assertAlmostEqual(r["sfc_dry"], 2.805e-5,
                               delta=0.02 * 2.805e-5)
        self.assertAlmostEqual(r["sfc_reheat"], 4.242e-5,
                               delta=0.02 * 4.242e-5)

    def test_analyze_internal_consistency_identity(self):
        # Summary values must equal the standalone functions; v = F / mdot_gas.
        r = ab.analyze(T04, F_CORE, MDOT, T05, P04, P_AMB)
        fd = ab.thrust_dry(T04, P04, P_AMB, MDOT, F_CORE)
        fab = ab.afterburner_far(T04, T05, F_CORE)
        fr = ab.thrust_reheat(T05, P04, P_AMB, MDOT, F_CORE, fab)
        self.assertAlmostEqual(r["F_dry"], fd, places=6)
        self.assertAlmostEqual(r["F_reheat"], fr, places=6)
        self.assertAlmostEqual(r["augmentation_ratio"], fr / fd, places=9)
        self.assertAlmostEqual(
            r["v_dry"], fd / (MDOT * (1.0 + F_CORE)), places=6)
        self.assertAlmostEqual(
            r["v_reheat"], fr / (MDOT * (1.0 + F_CORE + fab)), places=6)

    def test_analyze_raises_on_zero_mass_flow(self):
        with self.assertRaises(ValueError):
            ab.analyze(T04, F_CORE, 0.0, T05, P04, P_AMB)

    def test_analyze_raises_when_t05_equals_t04(self):
        with self.assertRaises(ValueError):
            ab.analyze(T04, F_CORE, MDOT, T04, P04, P_AMB)

    def test_analyze_raises_when_p04_equals_p_amb(self):
        with self.assertRaises(ValueError):
            ab.analyze(T04, F_CORE, MDOT, T05, P_AMB, P_AMB)


if __name__ == "__main__":
    unittest.main()
