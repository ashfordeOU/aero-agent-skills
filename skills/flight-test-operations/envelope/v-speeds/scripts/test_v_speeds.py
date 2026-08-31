#!/usr/bin/env python3
"""Gate 3 contract test: v-speeds.

Exercises scripts/v_speeds_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - vref = 1.3 * vs0,
v2 = 1.2 * vs1, vr = 1.1 * vs1 with all speeds in m/s; v_speeds
validates positivity and the configuration ordering (vs1 >= vs,
vs0 <= vs1) and raises ValueError otherwise; vno_vne_guard returns
the exceed verdict and the margin in m/s and raises ValueError when
vne is non-positive.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import v_speeds_logic as vsl  # noqa: E402


class ReferenceLandingSpeedTest(unittest.TestCase):
    def test_analytic_check(self):
        # vs0 = 30 m/s -> vref = 1.3 * 30 = 39.0 m/s
        self.assertAlmostEqual(vsl.reference_landing_speed(30), 39.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vsl.reference_landing_speed(0)
        with self.assertRaises(ValueError):
            vsl.reference_landing_speed(-30)


class TakeoffSafetySpeedTest(unittest.TestCase):
    def test_analytic_check(self):
        # vs1 = 28 m/s -> v2 = 1.2 * 28 = 33.6 m/s
        self.assertAlmostEqual(vsl.takeoff_safety_speed(28), 33.6)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            vsl.takeoff_safety_speed(0)
        with self.assertRaises(ValueError):
            vsl.takeoff_safety_speed(-28)


class RotationSpeedTest(unittest.TestCase):
    def test_analytic_check(self):
        # vs1 = 28 m/s -> vr = 1.1 * 28 = 30.8 m/s
        self.assertAlmostEqual(vsl.rotation_speed(28), 30.8)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            vsl.rotation_speed(0)
        with self.assertRaises(ValueError):
            vsl.rotation_speed(-28)


class VSpeedSetTest(unittest.TestCase):
    def test_analytic_set(self):
        # Valid ordering: vs = 22, vs0 = 25, vs1 = 28 (vs1 >= vs,
        # vs0 <= vs1). vref = 32.5, v2 = 33.6, vr = 30.8 m/s.
        out = vsl.v_speeds(22, 25, 28)
        self.assertEqual(out["vs"], 22)
        self.assertEqual(out["vs0"], 25)
        self.assertEqual(out["vs1"], 28)
        self.assertAlmostEqual(out["vref"], 32.5)
        self.assertAlmostEqual(out["v2"], 33.6)
        self.assertAlmostEqual(out["vr"], 30.8)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            vsl.v_speeds(0, 25, 28)  # vs = 0
        with self.assertRaises(ValueError):
            vsl.v_speeds(22, 0, 28)  # vs0 = 0
        with self.assertRaises(ValueError):
            vsl.v_speeds(30, 25, 28)  # vs1 < vs
        with self.assertRaises(ValueError):
            vsl.v_speeds(22, 32, 30)  # vs0 > vs1
        with self.assertRaises(ValueError):
            vsl.v_speeds(22, -25, 28)  # negative vs0


class VnoVneGuardTest(unittest.TestCase):
    def test_within_limit(self):
        out = vsl.vno_vne_guard(60, 70)
        self.assertFalse(out["vne_exceeded"])
        self.assertAlmostEqual(out["margin_mps"], 10.0)

    def test_exceeded(self):
        out = vsl.vno_vne_guard(80, 70)
        self.assertTrue(out["vne_exceeded"])
        self.assertAlmostEqual(out["margin_mps"], -10.0)

    def test_invalid_vne_raises(self):
        with self.assertRaises(ValueError):
            vsl.vno_vne_guard(60, 0)
        with self.assertRaises(ValueError):
            vsl.vno_vne_guard(60, -70)


if __name__ == "__main__":
    unittest.main(verbosity=2)
