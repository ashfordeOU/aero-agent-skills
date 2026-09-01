#!/usr/bin/env python3
"""Gate 3 contract test: aileron reversal.

Exercises scripts/aileron_reversal_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (reversal dynamic
pressure from the wing torsional stiffness, lift curve slope, aileron
effectiveness factor, wing area, mean chord, and elastic axis to
aerodynamic center offset; reversal true airspeed from the dynamic
pressure and air density; direct reversal speed from the stiffness
inputs; aileron effectiveness fraction at a flight dynamic pressure;
reversed verdict against the dive speed dynamic pressure; invalid
inputs raise ValueError.

Anchors:
- reversal_dynamic_pressure(5.0e6, 5.0, 0.8, 30.0, 2.0, 0.5) =
  41666.666666666664 Pa (5.0e6 / (5.0 * 0.8 * 30.0 * 2.0 * 0.5))
- reversal_speed(41666.666666666664, 1.225) = 260.8202654786505 m/s
- reversal_speed(41666.666666666664, 0.4135) = 448.9227555688767 m/s
  (10 km air density)
- reversal_speed_from_stiffness(5.0e6, 5.0, 0.8, 30.0, 2.0, 0.5,
  1.225) = 260.8202654786505 m/s
- aileron_effectiveness(19845.0, 41666.666666666664) = 0.52372
  (q = 0.5 * 1.225 * 180^2 at 180 m/s sea level)
- aileron_effectiveness(55125.0, 41666.666666666664) = -0.323
  (q = 0.5 * 1.225 * 300^2 at 300 m/s sea level)
- is_reversed(55125.0, 41666.666666666664) is True
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import aileron_reversal_logic as arl  # noqa: E402

Q_REV_ANCHOR = 5.0e6 / (5.0 * 0.8 * 30.0 * 2.0 * 0.5)


class ReversalDynamicPressureTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(arl.reversal_dynamic_pressure(5.0e6, 5.0, 0.8, 30.0, 2.0, 0.5), Q_REV_ANCHOR)

    def test_doubling_stiffness_doubles_q_rev(self):
        self.assertAlmostEqual(
            arl.reversal_dynamic_pressure(1.0e7, 5.0, 0.8, 30.0, 2.0, 0.5), 2.0 * Q_REV_ANCHOR
        )

    def test_full_effectiveness_lowers_q_rev(self):
        # eta = 1.0 (aileron as effective as the wing) twists the wing
        # harder for a given deflection, so reversal comes earlier at
        # a lower q_rev than the eta = 0.8 case.
        self.assertAlmostEqual(arl.reversal_dynamic_pressure(5.0e6, 5.0, 1.0, 30.0, 2.0, 0.5), 33333.333333333336)
        self.assertLess(
            arl.reversal_dynamic_pressure(5.0e6, 5.0, 1.0, 30.0, 2.0, 0.5),
            arl.reversal_dynamic_pressure(5.0e6, 5.0, 0.8, 30.0, 2.0, 0.5),
        )

    def test_larger_offset_lowers_q_rev(self):
        self.assertAlmostEqual(arl.reversal_dynamic_pressure(5.0e6, 5.0, 0.8, 30.0, 2.0, 1.0), 20833.333333333332)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            arl.reversal_dynamic_pressure(0, 5.0, 0.8, 30.0, 2.0, 0.5)
        with self.assertRaises(ValueError):
            arl.reversal_dynamic_pressure(-1.0, 5.0, 0.8, 30.0, 2.0, 0.5)
        with self.assertRaises(ValueError):
            arl.reversal_dynamic_pressure(5.0e6, 0, 0.8, 30.0, 2.0, 0.5)
        with self.assertRaises(ValueError):
            arl.reversal_dynamic_pressure(5.0e6, 5.0, 0, 30.0, 2.0, 0.5)
        with self.assertRaises(ValueError):
            arl.reversal_dynamic_pressure(5.0e6, 5.0, 1.1, 30.0, 2.0, 0.5)
        with self.assertRaises(ValueError):
            arl.reversal_dynamic_pressure(5.0e6, 5.0, 0.8, 0, 2.0, 0.5)
        with self.assertRaises(ValueError):
            arl.reversal_dynamic_pressure(5.0e6, 5.0, 0.8, 30.0, 0, 0.5)
        with self.assertRaises(ValueError):
            arl.reversal_dynamic_pressure(5.0e6, 5.0, 0.8, 30.0, 2.0, -0.5)


class ReversalSpeedTest(unittest.TestCase):
    def test_anchor_sea_level(self):
        self.assertAlmostEqual(arl.reversal_speed(Q_REV_ANCHOR, 1.225), 260.8202654786505)

    def test_anchor_ten_km(self):
        # Lower density at 10 km altitude raises the reversal speed.
        self.assertAlmostEqual(arl.reversal_speed(Q_REV_ANCHOR, 0.4135), 448.9227555688767)
        self.assertGreater(
            arl.reversal_speed(Q_REV_ANCHOR, 0.4135), arl.reversal_speed(Q_REV_ANCHOR, 1.225)
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            arl.reversal_speed(0, 1.225)
        with self.assertRaises(ValueError):
            arl.reversal_speed(-100.0, 1.225)
        with self.assertRaises(ValueError):
            arl.reversal_speed(Q_REV_ANCHOR, 0)
        with self.assertRaises(ValueError):
            arl.reversal_speed(Q_REV_ANCHOR, -1.225)


class ReversalSpeedFromStiffnessTest(unittest.TestCase):
    def test_anchor_matches_two_step(self):
        self.assertAlmostEqual(
            arl.reversal_speed_from_stiffness(5.0e6, 5.0, 0.8, 30.0, 2.0, 0.5, 1.225),
            arl.reversal_speed(Q_REV_ANCHOR, 1.225),
        )

    def test_stiffer_wing_reverses_later(self):
        slow = arl.reversal_speed_from_stiffness(5.0e6, 5.0, 0.8, 30.0, 2.0, 0.5, 1.225)
        fast = arl.reversal_speed_from_stiffness(1.0e7, 5.0, 0.8, 30.0, 2.0, 0.5, 1.225)
        self.assertGreater(fast, slow)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            arl.reversal_speed_from_stiffness(5.0e6, 5.0, 0.8, 30.0, 2.0, 0.5, 0)
        with self.assertRaises(ValueError):
            arl.reversal_speed_from_stiffness(5.0e6, 5.0, 0.8, 0, 2.0, 0.5, 1.225)


class AileronEffectivenessTest(unittest.TestCase):
    def test_anchor_below_reversal(self):
        # q = 0.5 * 1.225 * 180^2 = 19845.0 Pa at 180 m/s sea level.
        self.assertAlmostEqual(arl.aileron_effectiveness(19845.0, Q_REV_ANCHOR), 0.52372)

    def test_anchor_above_reversal(self):
        # q = 0.5 * 1.225 * 300^2 = 55125.0 Pa at 300 m/s sea level.
        self.assertAlmostEqual(arl.aileron_effectiveness(55125.0, Q_REV_ANCHOR), -0.323)

    def test_unity_at_zero_speed(self):
        self.assertAlmostEqual(arl.aileron_effectiveness(0.0, Q_REV_ANCHOR), 1.0)

    def test_zero_at_reversal_point(self):
        self.assertAlmostEqual(arl.aileron_effectiveness(Q_REV_ANCHOR, Q_REV_ANCHOR), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            arl.aileron_effectiveness(-1.0, Q_REV_ANCHOR)
        with self.assertRaises(ValueError):
            arl.aileron_effectiveness(19845.0, 0)
        with self.assertRaises(ValueError):
            arl.aileron_effectiveness(19845.0, -Q_REV_ANCHOR)


class IsReversedTest(unittest.TestCase):
    def test_reversed_above_reversal(self):
        self.assertTrue(arl.is_reversed(55125.0, Q_REV_ANCHOR))

    def test_not_reversed_below_reversal(self):
        self.assertFalse(arl.is_reversed(19845.0, Q_REV_ANCHOR))

    def test_boundary_not_reversed(self):
        # Strict comparison: q == q_rev is effectiveness zero, not yet
        # a reversal.
        self.assertFalse(arl.is_reversed(Q_REV_ANCHOR, Q_REV_ANCHOR))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            arl.is_reversed(-1.0, Q_REV_ANCHOR)
        with self.assertRaises(ValueError):
            arl.is_reversed(19845.0, 0)


class DiveSpeedScenarioTest(unittest.TestCase):
    def test_dive_speed_clearance(self):
        # Light transport wing, k_t = 5.0e6 N m / rad, sea level dive
        # speed 200 m/s: q = 0.5 * 1.225 * 200^2 = 24500.0 Pa, well
        # below the 41666.7 Pa reversal point, so the ailerons stay
        # effective at the dive limit.
        q_dive = 0.5 * 1.225 * 200.0 ** 2
        self.assertAlmostEqual(q_dive, 24500.0)
        eff = arl.aileron_effectiveness(q_dive, Q_REV_ANCHOR)
        self.assertAlmostEqual(eff, 1.0 - 24500.0 / Q_REV_ANCHOR)
        self.assertFalse(arl.is_reversed(q_dive, Q_REV_ANCHOR))
        self.assertGreater(arl.reversal_speed(Q_REV_ANCHOR, 1.225), 200.0)

    def test_dive_speed_exceeded_is_reversed(self):
        # Dive speed 300 m/s exceeds the 260.8 m/s reversal speed: the
        # control is reversed at the dive limit, effectiveness negative.
        q_dive = 0.5 * 1.225 * 300.0 ** 2
        self.assertTrue(arl.is_reversed(q_dive, Q_REV_ANCHOR))
        self.assertLess(arl.aileron_effectiveness(q_dive, Q_REV_ANCHOR), 0.0)
        self.assertLess(arl.reversal_speed(Q_REV_ANCHOR, 1.225), 300.0)

    def test_stiffened_wing_cures_reversal(self):
        # Doubling the torsional stiffness moves the reversal speed to
        # 368.9 m/s (260.8 * sqrt(2)), clearing the 300 m/s dive limit.
        q_dive = 0.5 * 1.225 * 300.0 ** 2
        stiff = arl.reversal_dynamic_pressure(1.0e7, 5.0, 0.8, 30.0, 2.0, 0.5)
        self.assertFalse(arl.is_reversed(q_dive, stiff))
        self.assertGreater(arl.reversal_speed(stiff, 1.225), 300.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
