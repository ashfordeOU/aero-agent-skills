#!/usr/bin/env python3
"""Gate 3 contract test: classical root-locus design.

Exercises scripts/root_locus_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3: closed-loop pole locations
for a gain K, the gain for a target damping ratio, the damping ratio
from a gain, and the stability verdict; invalid inputs raise
ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import root_locus_logic as rl  # noqa: E402


class ClosedLoopPolesTest(unittest.TestCase):
    def test_underdamped_poles(self):
        # a=2, K=4: s^2 + 2s + 4 = 0 -> -1 +/- j*sqrt(3)
        poles = rl.closed_loop_poles(2.0, 4.0)
        self.assertEqual(len(poles), 2)
        for re, im in poles:
            self.assertAlmostEqual(re, -1.0, delta=1e-9)
        self.assertAlmostEqual(abs(poles[0][1]), math.sqrt(3.0), delta=1e-9)
        self.assertAlmostEqual(abs(poles[1][1]), math.sqrt(3.0), delta=1e-9)
        self.assertAlmostEqual(poles[0][1], -poles[1][1], delta=1e-9)

    def test_critical_double_root(self):
        # a=2, K=1: s^2 + 2s + 1 = 0 -> real double root at -1
        poles = rl.closed_loop_poles(2.0, 1.0)
        for re, im in poles:
            self.assertAlmostEqual(re, -1.0, delta=1e-9)
            self.assertEqual(im, 0.0)

    def test_overdamped_real_poles(self):
        # a=2, K=0.75: s^2 + 2s + 0.75 = 0 -> -1.5 and -0.5
        poles = rl.closed_loop_poles(2.0, 0.75)
        res = sorted(re for re, im in poles)
        self.assertAlmostEqual(res[0], -1.5, delta=1e-9)
        self.assertAlmostEqual(res[1], -0.5, delta=1e-9)
        for re, im in poles:
            self.assertEqual(im, 0.0)

    def test_poles_satisfy_characteristic_equation(self):
        # Physically meaningful: each pole is a root of s^2 + a*s + K
        for re, im in rl.closed_loop_poles(2.0, 4.0):
            val = complex(re, im) ** 2 + 2.0 * complex(re, im) + 4.0
            self.assertAlmostEqual(abs(val), 0.0, delta=1e-9)

    def test_invalid_a_raises(self):
        with self.assertRaises(ValueError):
            rl.closed_loop_poles(0.0, 1.0)
        with self.assertRaises(ValueError):
            rl.closed_loop_poles(-1.0, 1.0)

    def test_invalid_k_raises(self):
        with self.assertRaises(ValueError):
            rl.closed_loop_poles(2.0, -1.0)


class GainForDampingTest(unittest.TestCase):
    def test_gain_for_zeta_0_7(self):
        # Known value: a=2, zeta=0.7 -> K = 4/(4*0.49) = 2.0408
        self.assertAlmostEqual(rl.gain_for_damping(2.0, 0.7),
                               4.0 / (4.0 * 0.49), delta=1e-6)
        self.assertAlmostEqual(rl.gain_for_damping(2.0, 0.7),
                               2.0408163265306123, delta=1e-6)

    def test_critically_damped_gain(self):
        # zeta = 1 -> K = a^2/4
        self.assertAlmostEqual(rl.gain_for_damping(2.0, 1.0), 1.0, delta=1e-12)

    def test_gain_round_trip_places_poles_at_zeta(self):
        # The gain chosen for a target zeta reproduces that zeta
        a, zeta = 3.0, 0.5
        K = rl.gain_for_damping(a, zeta)
        self.assertAlmostEqual(rl.damping_ratio(a, K), zeta, delta=1e-9)

    def test_invalid_zeta_raises(self):
        with self.assertRaises(ValueError):
            rl.gain_for_damping(2.0, 0.0)
        with self.assertRaises(ValueError):
            rl.gain_for_damping(2.0, -0.1)
        with self.assertRaises(ValueError):
            rl.gain_for_damping(2.0, 1.5)

    def test_invalid_a_raises(self):
        with self.assertRaises(ValueError):
            rl.gain_for_damping(0.0, 0.5)


class DampingRatioTest(unittest.TestCase):
    def test_critical_from_spec(self):
        # Known value: a=2, K=1 -> critically damped, zeta = 1
        self.assertAlmostEqual(rl.damping_ratio(2.0, 1.0), 1.0, delta=1e-12)

    def test_underdamped(self):
        # a=2, K=4: zeta = 2/(2*sqrt(4)) = 0.5
        self.assertAlmostEqual(rl.damping_ratio(2.0, 4.0), 0.5, delta=1e-9)

    def test_overdamped_reports_one(self):
        # K < a^2/4: convention reports zeta = 1
        self.assertAlmostEqual(rl.damping_ratio(2.0, 0.25), 1.0, delta=1e-12)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            rl.damping_ratio(0.0, 1.0)
        with self.assertRaises(ValueError):
            rl.damping_ratio(2.0, -1.0)


class StabilityVerdictTest(unittest.TestCase):
    def test_stable_underdamped(self):
        v = rl.stability_verdict(2.0, 4.0)
        self.assertTrue(v["stable"])
        self.assertEqual(len(v["poles"]), 2)
        for re, im in v["poles"]:
            self.assertAlmostEqual(re, -1.0, delta=1e-9)

    def test_stable_overdamped(self):
        self.assertTrue(rl.stability_verdict(2.0, 0.75)["stable"])

    def test_marginal_zero_gain_not_stable(self):
        # K = 0 puts a pole at the origin (re = 0): marginal, not stable
        v = rl.stability_verdict(2.0, 0.0)
        self.assertFalse(v["stable"])
        res = [re for re, im in v["poles"]]
        self.assertAlmostEqual(min(res), -2.0, delta=1e-9)
        self.assertAlmostEqual(max(res), 0.0, delta=1e-9)

    def test_invalid_a_raises(self):
        with self.assertRaises(ValueError):
            rl.stability_verdict(0.0, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
