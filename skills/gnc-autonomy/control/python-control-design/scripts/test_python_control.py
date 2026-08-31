#!/usr/bin/env python3
"""Gate 3 contract test: feedback control design.

Exercises scripts/python_control_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - gain-margin acceptance at
6 dB (pass at boundary, fail below), phase-margin acceptance at 45 deg
(pass at boundary, fail below), stability classification from the
margins, Ziegler-Nichols PID tuning from ultimate gain and period
(ku = 10, tu = 2 gives kp = 6, ki = 6, kd = 1.5), gain sanity, and
ValueError on invalid inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import python_control_logic as pcl  # noqa: E402


class MarginAcceptanceTest(unittest.TestCase):
    def test_gain_margin_boundary(self):
        self.assertTrue(pcl.gain_margin_ok(6.0))
        self.assertFalse(pcl.gain_margin_ok(5.9))

    def test_gain_margin_custom_minimum(self):
        self.assertTrue(pcl.gain_margin_ok(9.0, min_db=8.0))
        self.assertFalse(pcl.gain_margin_ok(7.0, min_db=8.0))

    def test_phase_margin_boundary(self):
        self.assertTrue(pcl.phase_margin_ok(45.0))
        self.assertFalse(pcl.phase_margin_ok(44.0))

    def test_phase_margin_custom_minimum(self):
        self.assertTrue(pcl.phase_margin_ok(50.0, min_deg=50.0))
        self.assertFalse(pcl.phase_margin_ok(49.0, min_deg=50.0))


class StabilityTest(unittest.TestCase):
    def test_positive_margins_stable(self):
        self.assertEqual(pcl.stability_from_margins(6.0, 45.0), "stable")

    def test_zero_margin_unstable(self):
        self.assertEqual(pcl.stability_from_margins(0.0, 45.0), "unstable")
        self.assertEqual(pcl.stability_from_margins(6.0, 0.0), "unstable")

    def test_negative_margin_unstable(self):
        self.assertEqual(pcl.stability_from_margins(-2.0, 45.0), "unstable")
        self.assertEqual(pcl.stability_from_margins(6.0, -10.0), "unstable")

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            pcl.stability_from_margins("six", 45.0)
        with self.assertRaises(ValueError):
            pcl.stability_from_margins(6.0, None)


class ZieglerNicholsTest(unittest.TestCase):
    def test_known_case(self):
        kp, ki, kd = pcl.ziegler_nichols_pid(10.0, 2.0)
        self.assertAlmostEqual(kp, 6.0)
        self.assertAlmostEqual(ki, 6.0)
        self.assertAlmostEqual(kd, 1.5)

    def test_tuned_gains_sane(self):
        self.assertTrue(pcl.controller_sanity(*pcl.ziegler_nichols_pid(10.0, 2.0)))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pcl.ziegler_nichols_pid(0.0, 2.0)
        with self.assertRaises(ValueError):
            pcl.ziegler_nichols_pid(10.0, -1.0)


class ControllerSanityTest(unittest.TestCase):
    def test_sane_gains(self):
        self.assertTrue(pcl.controller_sanity(1.0, 0.5, 0.1))

    def test_nonpositive_proportional_fails(self):
        self.assertFalse(pcl.controller_sanity(0.0, 0.5, 0.1))
        self.assertFalse(pcl.controller_sanity(-1.0, 0.5, 0.1))

    def test_negative_integral_or_derivative_fails(self):
        self.assertFalse(pcl.controller_sanity(1.0, -0.1, 0.1))
        self.assertFalse(pcl.controller_sanity(1.0, 0.5, -0.1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
