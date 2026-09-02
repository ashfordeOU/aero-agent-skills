#!/usr/bin/env python3
"""Gate 3 contract test: static longitudinal stability.

Exercises scripts/longitudinal_stability_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - neutral point
from the wing aerodynamic center, tail volume, lift slope ratio, and
downwash gradient; static margin at the center of gravity; and the
longitudinal stability verdict; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import longitudinal_stability_logic as ls  # noqa: E402


class NeutralPointTest(unittest.TestCase):
    def test_anchor_value(self):
        # 0.25 + 0.5 * 0.8 * (1 - 0.4) = 0.49
        self.assertAlmostEqual(
            ls.neutral_point(0.25, 0.5, 0.8, 0.4), 0.49, delta=1e-9
        )

    def test_no_tail_contribution(self):
        # Zero downwash gradient leaves the full tail contribution.
        self.assertAlmostEqual(
            ls.neutral_point(0.25, 0.2, 0.9, 0.0), 0.25 + 0.2 * 0.9, delta=1e-9
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ls.neutral_point(0.0, 0.5, 0.8, 0.4)
        with self.assertRaises(ValueError):
            ls.neutral_point(1.0, 0.5, 0.8, 0.4)
        with self.assertRaises(ValueError):
            ls.neutral_point(1.5, 0.5, 0.8, 0.4)
        with self.assertRaises(ValueError):
            ls.neutral_point(0.25, 0.0, 0.8, 0.4)
        with self.assertRaises(ValueError):
            ls.neutral_point(0.25, -0.5, 0.8, 0.4)
        with self.assertRaises(ValueError):
            ls.neutral_point(0.25, 0.5, 0.0, 0.4)
        with self.assertRaises(ValueError):
            ls.neutral_point(0.25, 0.5, -0.8, 0.4)
        with self.assertRaises(ValueError):
            ls.neutral_point(0.25, 0.5, 0.8, -0.1)
        with self.assertRaises(ValueError):
            ls.neutral_point(0.25, 0.5, 0.8, 1.0)


class StaticMarginTest(unittest.TestCase):
    def test_anchor_value(self):
        self.assertAlmostEqual(ls.static_margin(0.49, 0.35), 0.14, delta=1e-9)

    def test_cg_aft_of_neutral_point(self):
        self.assertAlmostEqual(
            ls.static_margin(0.49, 0.55), -0.06, delta=1e-9
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ls.static_margin(0.0, 0.35)
        with self.assertRaises(ValueError):
            ls.static_margin(1.0, 0.35)
        with self.assertRaises(ValueError):
            ls.static_margin(0.49, 0.0)
        with self.assertRaises(ValueError):
            ls.static_margin(0.49, 1.0)
        with self.assertRaises(ValueError):
            ls.static_margin(0.49, 1.5)


class LongitudinalStabilityTest(unittest.TestCase):
    def test_stable_margin(self):
        self.assertTrue(ls.longitudinally_stable(0.14))

    def test_unstable_margin(self):
        self.assertFalse(ls.longitudinally_stable(0.03))

    def test_margin_at_minimum_is_stable(self):
        self.assertTrue(ls.longitudinally_stable(0.05))

    def test_custom_min_margin(self):
        self.assertFalse(ls.longitudinally_stable(0.14, min_margin=0.2))
        self.assertTrue(ls.longitudinally_stable(0.14, min_margin=0.1))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            ls.longitudinally_stable(0.14, min_margin=-0.05)


if __name__ == "__main__":
    unittest.main(verbosity=2)
