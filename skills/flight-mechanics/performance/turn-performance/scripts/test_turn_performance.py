#!/usr/bin/env python3
"""Gate 3 contract test: sustained turn performance.

Exercises scripts/turn_performance_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - load factor
from bank angle (n = 1 / cos(phi)), bank angle from load factor
(phi = acos(1 / n)), turn rate (omega = g * sqrt(n^2 - 1) / V),
turn radius (R = V^2 / (g * sqrt(n^2 - 1))), and the sustained
verdict against the available thrust (D_turn = D_level * n);
invalid inputs raise ValueError. Angles in radians, SI units
throughout, g = 9.80665 m/s^2.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import turn_performance_logic as tpl  # noqa: E402


class LoadFactorTest(unittest.TestCase):
    def test_analytic_check(self):
        # 45 deg = pi/4 rad: n = 1 / cos(pi/4) = sqrt(2) = 1.4142136.
        self.assertAlmostEqual(tpl.load_factor_from_bank(math.pi / 4), math.sqrt(2))

    def test_level_flight(self):
        self.assertAlmostEqual(tpl.load_factor_from_bank(0.0), 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tpl.load_factor_from_bank(math.pi / 2)
        with self.assertRaises(ValueError):
            tpl.load_factor_from_bank(1.6)  # beyond pi/2


class BankAngleTest(unittest.TestCase):
    def test_analytic_check(self):
        self.assertAlmostEqual(tpl.bank_from_load_factor(math.sqrt(2)), math.pi / 4)

    def test_level_flight(self):
        self.assertAlmostEqual(tpl.bank_from_load_factor(1.0), 0.0)

    def test_round_trip(self):
        for n in (1.5, 2.0, 3.0):
            self.assertAlmostEqual(tpl.load_factor_from_bank(tpl.bank_from_load_factor(n)), n)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tpl.bank_from_load_factor(0.9)


class TurnRateTest(unittest.TestCase):
    def test_analytic_check(self):
        # n = 2, V = 100: 9.80665 * sqrt(3) / 100 = 0.169855 rad/s.
        expected = 9.80665 * math.sqrt(3.0) / 100.0
        self.assertAlmostEqual(tpl.turn_rate(2.0, 100.0), expected, places=6)

    def test_faster_speed_slower_rate(self):
        self.assertGreater(tpl.turn_rate(2.0, 50.0), tpl.turn_rate(2.0, 200.0))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tpl.turn_rate(0.9, 100.0)
        with self.assertRaises(ValueError):
            tpl.turn_rate(2.0, 0.0)
        with self.assertRaises(ValueError):
            tpl.turn_rate(2.0, -100.0)


class TurnRadiusTest(unittest.TestCase):
    def test_analytic_check(self):
        # n = 2, V = 100: 100^2 / (9.80665 * sqrt(3)) = 588.737 m.
        expected = 10000.0 / (9.80665 * math.sqrt(3.0))
        self.assertAlmostEqual(tpl.turn_radius(2.0, 100.0), expected, places=6)

    def test_consistency_with_turn_rate(self):
        # R = V / omega exactly.
        self.assertAlmostEqual(
            tpl.turn_radius(2.0, 100.0), 100.0 / tpl.turn_rate(2.0, 100.0), places=9
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tpl.turn_radius(0.9, 100.0)
        with self.assertRaises(ValueError):
            tpl.turn_radius(2.0, 0.0)


class SustainedCheckTest(unittest.TestCase):
    def test_sustained_when_thrust_covers(self):
        # D_turn = 20000 * 2 = 40000 N; 45000 N covers it.
        r = tpl.sustained_check(45000.0, 20000.0, 2.0)
        self.assertEqual(r["d_turn"], 40000.0)
        self.assertEqual(r["verdict"], "sustained")

    def test_not_sustained_when_thrust_short(self):
        r = tpl.sustained_check(35000.0, 20000.0, 2.0)
        self.assertEqual(r["verdict"], "not sustained")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            tpl.sustained_check(45000.0, 0.0, 2.0)
        with self.assertRaises(ValueError):
            tpl.sustained_check(45000.0, 20000.0, 0.9)


if __name__ == "__main__":
    unittest.main(verbosity=2)
