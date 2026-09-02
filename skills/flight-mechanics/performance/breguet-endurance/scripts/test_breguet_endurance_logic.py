#!/usr/bin/env python3
"""Gate 3 contract test: Breguet loiter endurance performance.

Exercises scripts/breguet_endurance_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (Breguet loiter endurance
from specific fuel consumption and lift-to-drag; final weight after
an endurance segment; fuel burn; requirement check; invalid inputs
raise ValueError).

Anchors:
- jet_endurance(1.5e-5, 15, 50000, 45000) = 105360.5157 s (exact).
  The anchor 105360.51 is the rounded form; asserted at places=1.
- final_weight_after_endurance(50000, 1.5e-5, 15, 3600) = 49820.3236 N
  (exact); anchored as 49820.33 at places=1.
- ln(50000/45000) = 0.1053605157
- endurance_fuel_burn(50000, 45000) = 5000 N
- loiter_check(50000, 45000, 1.5e-5, 15, 3600) meets True
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import breguet_endurance_logic as be  # noqa: E402


class JetEnduranceTest(unittest.TestCase):
    def test_anchor_endurance(self):
        e = be.jet_endurance(1.5e-5, 15, 50000, 45000)
        self.assertAlmostEqual(e, 105360.51, places=1)

    def test_mass_ratio_log(self):
        self.assertAlmostEqual(math.log(50000 / 45000), 0.1053605157, places=8)

    def test_linear_in_ld_and_sfc(self):
        base = be.jet_endurance(1.5e-5, 15, 50000, 45000)
        better_ld = be.jet_endurance(1.5e-5, 30, 50000, 45000)
        self.assertAlmostEqual(better_ld, 2 * base)
        lower_sfc = be.jet_endurance(7.5e-6, 15, 50000, 45000)
        self.assertAlmostEqual(lower_sfc, 2 * base)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            be.jet_endurance(0, 15, 50000, 45000)
        with self.assertRaises(ValueError):
            be.jet_endurance(-1.5e-5, 15, 50000, 45000)
        with self.assertRaises(ValueError):
            be.jet_endurance(1.5e-5, 0, 50000, 45000)
        with self.assertRaises(ValueError):
            be.jet_endurance(1.5e-5, 15, 0, 45000)
        with self.assertRaises(ValueError):
            be.jet_endurance(1.5e-5, 15, 50000, 0)
        with self.assertRaises(ValueError):
            be.jet_endurance(1.5e-5, 15, 45000, 50000)
        with self.assertRaises(ValueError):
            be.jet_endurance(1.5e-5, 15, 50000, 50000)


class PropEnduranceTest(unittest.TestCase):
    def test_anchor_prop_endurance(self):
        e = be.prop_endurance(1.5e-5, 15, 50000, 45000)
        self.assertAlmostEqual(e, 105360.51, places=1)

    def test_matches_jet_form(self):
        self.assertAlmostEqual(
            be.prop_endurance(1.5e-5, 15, 50000, 45000),
            be.jet_endurance(1.5e-5, 15, 50000, 45000),
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            be.prop_endurance(0, 15, 50000, 45000)
        with self.assertRaises(ValueError):
            be.prop_endurance(1.5e-5, 15, 45000, 50000)


class FinalWeightTest(unittest.TestCase):
    def test_anchor_final_weight(self):
        w = be.final_weight_after_endurance(50000, 1.5e-5, 15, 3600)
        self.assertAlmostEqual(w, 49820.33, places=1)

    def test_zero_endurance_returns_initial(self):
        self.assertAlmostEqual(
            be.final_weight_after_endurance(50000, 1.5e-5, 15, 0), 50000.0
        )

    def test_round_trip_with_jet_endurance(self):
        e = be.jet_endurance(1.5e-5, 15, 50000, 45000)
        w = be.final_weight_after_endurance(50000, 1.5e-5, 15, e)
        self.assertAlmostEqual(w, 45000.0, places=1)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            be.final_weight_after_endurance(0, 1.5e-5, 15, 3600)
        with self.assertRaises(ValueError):
            be.final_weight_after_endurance(50000, 0, 15, 3600)
        with self.assertRaises(ValueError):
            be.final_weight_after_endurance(50000, 1.5e-5, 0, 3600)
        with self.assertRaises(ValueError):
            be.final_weight_after_endurance(50000, 1.5e-5, 15, -1)


class FuelBurnTest(unittest.TestCase):
    def test_anchor_fuel_burn(self):
        self.assertAlmostEqual(be.endurance_fuel_burn(50000, 45000), 5000.0)

    def test_zero_burn_when_weights_equal(self):
        self.assertAlmostEqual(be.endurance_fuel_burn(50000, 50000), 0.0)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            be.endurance_fuel_burn(45000, 50000)


class LoiterCheckTest(unittest.TestCase):
    def test_anchor_meets(self):
        r = be.loiter_check(50000, 45000, 1.5e-5, 15, 3600)
        self.assertAlmostEqual(r["achievable"], 105360.51, places=1)
        self.assertEqual(r["required"], 3600)
        self.assertTrue(r["meets"])
        self.assertEqual(r["verdict"], "meets")

    def test_does_not_meet(self):
        r = be.loiter_check(50000, 45000, 1.5e-5, 15, 200000)
        self.assertFalse(r["meets"])
        self.assertEqual(r["verdict"], "does not meet")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            be.loiter_check(50000, 45000, 1.5e-5, 15, -1)
        with self.assertRaises(ValueError):
            be.loiter_check(45000, 50000, 1.5e-5, 15, 3600)
        with self.assertRaises(ValueError):
            be.loiter_check(50000, 45000, 0, 15, 3600)


if __name__ == "__main__":
    unittest.main(verbosity=2)
