#!/usr/bin/env python3
"""Gate 3 contract test: fatigue cumulative damage (Palmgren-Miner).

Exercises scripts/miner_damage_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — cumulative damage
fraction, damage limit checks, and life-consumed accounting;
invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import miner_damage_logic as md  # noqa: E402


class CumulativeDamageTest(unittest.TestCase):
    def test_two_blocks_sum(self):
        d = md.cumulative_damage([(1000, 10000), (500, 5000)])
        self.assertAlmostEqual(d, 0.2)

    def test_full_life(self):
        self.assertAlmostEqual(md.cumulative_damage([(1000, 1000)]), 1.0)

    def test_zero_cycles_no_damage(self):
        self.assertAlmostEqual(md.cumulative_damage([(0, 10000)]), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            md.cumulative_damage([])
        with self.assertRaises(ValueError):
            md.cumulative_damage([(1000, 0)])
        with self.assertRaises(ValueError):
            md.cumulative_damage([(-5, 10000)])


class DamageLimitTest(unittest.TestCase):
    def test_within_limit(self):
        self.assertTrue(md.damage_ok(0.99))
        self.assertTrue(md.damage_ok(1.0))

    def test_exceeding_limit(self):
        self.assertFalse(md.damage_ok(1.01))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            md.damage_ok(-0.1)


class LifeConsumedTest(unittest.TestCase):
    def test_percent(self):
        self.assertAlmostEqual(md.life_consumed_pct(0.2), 20.0)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            md.life_consumed_pct(-1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
