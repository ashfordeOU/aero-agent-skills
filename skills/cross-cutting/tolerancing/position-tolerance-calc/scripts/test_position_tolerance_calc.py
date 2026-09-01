#!/usr/bin/env python3
"""Gate 3 contract test: position tolerance calculation.

Exercises scripts/position_tolerance_calc_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (radial deviation
of the actual feature center from the true position; required zone
diameter; MMC bonus tolerance from the actual feature size; total
tolerance; virtual condition for hole and pin; acceptance verdict;
invalid inputs raise ValueError.

Anchors:
- positional_deviation(0.3, 0.4, 0.0, 0.0) = 0.5 (3-4-5 triangle)
- positional_deviation(0.3, 0.4, 0.1, 0.2) = sqrt(0.08)
- position_zone_diameter(0.3, 0.4, 0.0, 0.0) = 1.0 (twice the deviation)
- mmc_bonus(10.2, 10.0) = 0.2; mmc_bonus(10.0, 10.0) = 0.0
- total_position_tolerance(0.5, 0.2) = 0.7
- virtual_condition('hole', 10.0, 0.5) = 9.5
- virtual_condition('pin', 10.0, 0.5) = 10.5
- max_center_offset(0.5, 0.2) = 0.35
- position_verdict(0.25, 0.5) is True; position_verdict(0.3, 0.5)
  is False; position_verdict(0.3, 0.5, 0.2) is True
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import position_tolerance_calc_logic as ptc  # noqa: E402


class PositionalDeviationTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(ptc.positional_deviation(0.3, 0.4, 0.0, 0.0), 0.5)

    def test_anchor_offset_true_position(self):
        self.assertAlmostEqual(
            ptc.positional_deviation(0.3, 0.4, 0.1, 0.2), math.sqrt(0.08)
        )

    def test_zero_when_centered(self):
        self.assertAlmostEqual(ptc.positional_deviation(1.0, 2.0, 1.0, 2.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ptc.positional_deviation(float("nan"), 0.4, 0.0, 0.0)
        with self.assertRaises(ValueError):
            ptc.positional_deviation(0.3, float("inf"), 0.0, 0.0)
        with self.assertRaises(ValueError):
            ptc.positional_deviation("a", 0.4, 0.0, 0.0)
        with self.assertRaises(ValueError):
            ptc.positional_deviation(0.3, 0.4, None, 0.0)


class PositionZoneDiameterTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(ptc.position_zone_diameter(0.3, 0.4, 0.0, 0.0), 1.0)

    def test_twice_the_deviation(self):
        d = ptc.positional_deviation(0.25, 0.0, 0.0, 0.0)
        self.assertAlmostEqual(ptc.position_zone_diameter(0.25, 0.0, 0.0, 0.0), 2.0 * d)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ptc.position_zone_diameter(0.3, float("nan"), 0.0, 0.0)


class MmcBonusTest(unittest.TestCase):
    def test_anchor_bonus(self):
        self.assertAlmostEqual(ptc.mmc_bonus(10.2, 10.0), 0.2)

    def test_zero_bonus_at_mmc(self):
        self.assertAlmostEqual(ptc.mmc_bonus(10.0, 10.0), 0.0)

    def test_bonus_grows_with_hole_size(self):
        self.assertAlmostEqual(ptc.mmc_bonus(10.5, 10.0), 0.5)

    def test_invalid_below_mmc_raises(self):
        with self.assertRaises(ValueError):
            ptc.mmc_bonus(9.9, 10.0)

    def test_invalid_nonpositive_mmc_raises(self):
        with self.assertRaises(ValueError):
            ptc.mmc_bonus(10.0, 0.0)
        with self.assertRaises(ValueError):
            ptc.mmc_bonus(10.0, -1.0)


class TotalPositionToleranceTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(ptc.total_position_tolerance(0.5, 0.2), 0.7)

    def test_no_bonus(self):
        self.assertAlmostEqual(ptc.total_position_tolerance(0.5, 0.0), 0.5)

    def test_invalid_negative_stated_raises(self):
        with self.assertRaises(ValueError):
            ptc.total_position_tolerance(-0.1, 0.2)

    def test_invalid_negative_bonus_raises(self):
        with self.assertRaises(ValueError):
            ptc.total_position_tolerance(0.5, -0.2)

    def test_invalid_nonfinite_raises(self):
        with self.assertRaises(ValueError):
            ptc.total_position_tolerance(float("inf"), 0.2)


class VirtualConditionTest(unittest.TestCase):
    def test_hole_anchor(self):
        self.assertAlmostEqual(ptc.virtual_condition("hole", 10.0, 0.5), 9.5)

    def test_pin_anchor(self):
        self.assertAlmostEqual(ptc.virtual_condition("pin", 10.0, 0.5), 10.5)

    def test_invalid_part_type_raises(self):
        with self.assertRaises(ValueError):
            ptc.virtual_condition("slot", 10.0, 0.5)

    def test_invalid_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            ptc.virtual_condition("hole", 10.0, -0.5)

    def test_invalid_nonpositive_mmc_raises(self):
        with self.assertRaises(ValueError):
            ptc.virtual_condition("pin", 0.0, 0.5)


class MaxCenterOffsetTest(unittest.TestCase):
    def test_anchor(self):
        self.assertAlmostEqual(ptc.max_center_offset(0.5, 0.2), 0.35)

    def test_no_bonus(self):
        self.assertAlmostEqual(ptc.max_center_offset(0.5, 0.0), 0.25)

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            ptc.max_center_offset(-0.5, 0.2)


class PositionVerdictTest(unittest.TestCase):
    def test_accept_inside(self):
        self.assertTrue(ptc.position_verdict(0.25, 0.5))

    def test_reject_outside(self):
        self.assertFalse(ptc.position_verdict(0.3, 0.5))

    def test_accept_at_boundary(self):
        # 2 * 0.25 equals the 0.5 diameter: the boundary accepts.
        self.assertTrue(ptc.position_verdict(0.25, 0.5))

    def test_bonus_saves_the_feature(self):
        # Deviation 0.3 fails the 0.5 zone but fits with a 0.2 bonus.
        self.assertTrue(ptc.position_verdict(0.3, 0.5, 0.2))

    def test_bonus_insufficient(self):
        # Deviation 0.4 with a 0.2 bonus: 0.8 above the 0.7 total.
        self.assertFalse(ptc.position_verdict(0.4, 0.5, 0.2))

    def test_invalid_negative_deviation_raises(self):
        with self.assertRaises(ValueError):
            ptc.position_verdict(-0.1, 0.5)


class HoleScenarioTest(unittest.TestCase):
    def test_hole_clears_with_mmc_bonus(self):
        # Hole MMC 10.0, stated position diameter 0.5, actual size
        # 10.3, actual center at (0.2, 0.1) against true position
        # (0.0, 0.0): bonus 0.3, total 0.8, deviation 0.2236,
        # zone diameter 0.4472, verdict True.
        bonus = ptc.mmc_bonus(10.3, 10.0)
        total = ptc.total_position_tolerance(0.5, bonus)
        deviation = ptc.positional_deviation(0.2, 0.1, 0.0, 0.0)
        zone = ptc.position_zone_diameter(0.2, 0.1, 0.0, 0.0)
        self.assertAlmostEqual(bonus, 0.3)
        self.assertAlmostEqual(total, 0.8)
        self.assertAlmostEqual(deviation, math.sqrt(0.05))
        self.assertAlmostEqual(zone, 2.0 * math.sqrt(0.05))
        self.assertTrue(ptc.position_verdict(deviation, 0.5, bonus))

    def test_hole_fails_without_bonus_passes_with(self):
        # Center at (0.3, 0.1): deviation 0.3162, zone 0.6324 fails
        # the 0.5 stated diameter but clears the 0.7 total with the
        # 0.2 bonus.
        deviation = ptc.positional_deviation(0.3, 0.1, 0.0, 0.0)
        self.assertFalse(ptc.position_verdict(deviation, 0.5))
        self.assertTrue(ptc.position_verdict(deviation, 0.5, 0.2))

    def test_virtual_condition_bounds_the_mating_part(self):
        # Hole MMC 10.0 with 0.5 stated: the mating pin must fit a
        # 9.5 virtual condition boundary, tighter than the hole MMC.
        self.assertAlmostEqual(ptc.virtual_condition("hole", 10.0, 0.5), 9.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
