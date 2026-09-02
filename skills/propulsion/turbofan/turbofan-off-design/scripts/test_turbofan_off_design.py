#!/usr/bin/env python3
"""Gate 3 contract test: turbofan off-design performance.

Exercises scripts/turbofan_off_design.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - corrected mass flow and
corrected speed, altitude net thrust with ram drag, SFC altitude
factor, throttle-setting sanity, and the fan/core component matching
verdict; invalid inputs raise ValueError.
"""

import unittest

import turbofan_off_design as tf

T_REF = 288.15
P_REF = 101325.0
RHO0 = 1.225


class CorrectedMassFlowTest(unittest.TestCase):
    def test_reference_condition_recovers_physical(self):
        self.assertAlmostEqual(tf.corrected_mass_flow(100.0, T_REF, P_REF), 100.0)

    def test_hot_day_lowers_corrected_flow(self):
        # Hot day (T > T_ref) at the same physical flow and pressure.
        self.assertAlmostEqual(
            tf.corrected_mass_flow(100.0, 300.0, P_REF),
            100.0 * (T_REF / 300.0) ** 0.5,
        )

    def test_low_pressure_raises_corrected_flow(self):
        # Low inlet pressure raises the corrected flow at fixed mass flow.
        self.assertAlmostEqual(
            tf.corrected_mass_flow(100.0, T_REF, 80000.0),
            100.0 / (80000.0 / P_REF),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tf.corrected_mass_flow(0.0, T_REF, P_REF)
        with self.assertRaises(ValueError):
            tf.corrected_mass_flow(-5.0, T_REF, P_REF)
        with self.assertRaises(ValueError):
            tf.corrected_mass_flow(100.0, 0.0, P_REF)
        with self.assertRaises(ValueError):
            tf.corrected_mass_flow(100.0, T_REF, 0.0)
        with self.assertRaises(ValueError):
            tf.corrected_mass_flow(100.0, T_REF, P_REF, t_ref=0.0)
        with self.assertRaises(ValueError):
            tf.corrected_mass_flow(100.0, T_REF, P_REF, p_ref=-1.0)


class CorrectedSpeedTest(unittest.TestCase):
    def test_reference_condition_recovers_physical(self):
        self.assertAlmostEqual(tf.corrected_speed(15000.0, T_REF), 15000.0)

    def test_hot_day_lowers_corrected_speed(self):
        self.assertAlmostEqual(
            tf.corrected_speed(15000.0, 300.0), 15000.0 * (T_REF / 300.0) ** 0.5
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tf.corrected_speed(-1.0, T_REF)
        with self.assertRaises(ValueError):
            tf.corrected_speed(15000.0, 0.0)
        with self.assertRaises(ValueError):
            tf.corrected_speed(15000.0, T_REF, t_ref=0.0)


class NetThrustAltitudeTest(unittest.TestCase):
    def test_sea_level_static_recovers(self):
        self.assertAlmostEqual(
            tf.net_thrust_altitude(100000.0, RHO0, RHO0, 1.0), 100000.0
        )

    def test_density_ratio_scaling(self):
        self.assertAlmostEqual(
            tf.net_thrust_altitude(100000.0, 0.5 * RHO0, RHO0, 1.0), 50000.0
        )

    def test_ram_drag_penalty(self):
        self.assertAlmostEqual(
            tf.net_thrust_altitude(100000.0, RHO0, RHO0, 1.0, ram_drag=10000.0),
            90000.0,
        )

    def test_zero_density_rejected(self):
        with self.assertRaises(ValueError):
            tf.net_thrust_altitude(100000.0, 0.0, RHO0, 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tf.net_thrust_altitude(0.0, RHO0, RHO0, 1.0)
        with self.assertRaises(ValueError):
            tf.net_thrust_altitude(100000.0, RHO0, 0.0, 1.0)
        with self.assertRaises(ValueError):
            tf.net_thrust_altitude(100000.0, RHO0, RHO0, 0.0)
        with self.assertRaises(ValueError):
            tf.net_thrust_altitude(100000.0, RHO0, RHO0, 2.0)
        with self.assertRaises(ValueError):
            tf.net_thrust_altitude(100000.0, RHO0, RHO0, 1.0, ram_drag=-5.0)


class SfcAltitudeFactorTest(unittest.TestCase):
    def test_sea_level_identity(self):
        self.assertAlmostEqual(tf.sfc_altitude_factor(0.6, RHO0, RHO0), 0.6)

    def test_altitude_lowers_sfc(self):
        sfc = tf.sfc_altitude_factor(0.6, 0.5 * RHO0, RHO0)
        self.assertAlmostEqual(sfc, 0.6 * 0.5 ** 0.15)
        self.assertLess(sfc, 0.6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tf.sfc_altitude_factor(0.0, RHO0, RHO0)
        with self.assertRaises(ValueError):
            tf.sfc_altitude_factor(0.6, 0.0, RHO0)
        with self.assertRaises(ValueError):
            tf.sfc_altitude_factor(0.6, RHO0, 0.0)
        with self.assertRaises(ValueError):
            tf.sfc_altitude_factor(0.6, RHO0, RHO0, exponent=0.0)


class ThrottleVerdictTest(unittest.TestCase):
    def test_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            tf.throttle_verdict(0.0)
        with self.assertRaises(ValueError):
            tf.throttle_verdict(-0.1)
        with self.assertRaises(ValueError):
            tf.throttle_verdict(1.2)

    def test_verdict_bands(self):
        self.assertEqual(tf.throttle_verdict(0.02), "below-idle")
        self.assertEqual(tf.throttle_verdict(0.15), "idle")
        self.assertEqual(tf.throttle_verdict(0.50), "cruise")
        self.assertEqual(tf.throttle_verdict(0.80), "climb")
        self.assertEqual(tf.throttle_verdict(0.98), "max-continuous")
        self.assertEqual(tf.throttle_verdict(1.03), "over-throttle")


class ComponentMatchingVerdictTest(unittest.TestCase):
    def test_both_in_band_matched(self):
        self.assertEqual(tf.component_matching_verdict(0.05, -0.03), "matched")

    def test_band_edge_inclusive(self):
        self.assertEqual(tf.component_matching_verdict(0.10, -0.10), "matched")

    def test_fan_off_design(self):
        self.assertEqual(tf.component_matching_verdict(0.15, 0.02), "fan-off-design")

    def test_core_off_design(self):
        self.assertEqual(tf.component_matching_verdict(0.02, -0.20), "core-off-design")

    def test_both_off_design(self):
        self.assertEqual(
            tf.component_matching_verdict(0.15, -0.20), "fan-and-core-off-design"
        )

    def test_invalid_band_rejected(self):
        with self.assertRaises(ValueError):
            tf.component_matching_verdict(0.05, 0.05, band=0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
