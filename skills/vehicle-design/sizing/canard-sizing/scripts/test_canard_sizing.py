"""Contract tests for canard sizing logic (stdlib unittest, offline).

Run: python3 scripts/test_canard_sizing.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from canard_sizing_logic import (G0, canard_volume_coefficient,
                                 required_canard_area, canard_lift_share,
                                 trim_lift_coefficients, stall_precedence,
                                 size_canard)


class TestCanardVolumeCoefficient(unittest.TestCase):
    """Canard volume coefficient V_c = S_c * arm / (S * cbar)."""

    def test_anchor_round_trip_returns_target(self):
        # Worked example round-trip: 4.2 m2, 9 m arm, 30 m2 wing, 2.8 m MAC.
        self.assertAlmostEqual(
            canard_volume_coefficient(4.2, 9, 30, 2.8), 0.45, places=9)

    def test_doubling_area_doubles_coefficient(self):
        self.assertAlmostEqual(
            canard_volume_coefficient(8.4, 9, 30, 2.8),
            2 * canard_volume_coefficient(4.2, 9, 30, 2.8), places=12)

    def test_doubling_wing_area_halves_coefficient(self):
        self.assertAlmostEqual(
            canard_volume_coefficient(4.2, 9, 60, 2.8),
            0.5 * canard_volume_coefficient(4.2, 9, 30, 2.8), places=12)

    def test_doubling_arm_doubles_coefficient(self):
        self.assertAlmostEqual(
            canard_volume_coefficient(4.2, 18, 30, 2.8),
            2 * canard_volume_coefficient(4.2, 9, 30, 2.8), places=12)

    def test_non_positive_area_raises(self):
        with self.assertRaises(ValueError):
            canard_volume_coefficient(0.0, 9, 30, 2.8)
        with self.assertRaises(ValueError):
            canard_volume_coefficient(-1.0, 9, 30, 2.8)

    def test_non_positive_arm_raises(self):
        with self.assertRaises(ValueError):
            canard_volume_coefficient(4.2, 0.0, 30, 2.8)

    def test_non_positive_wing_reference_raises(self):
        with self.assertRaises(ValueError):
            canard_volume_coefficient(4.2, 9, 0.0, 2.8)
        with self.assertRaises(ValueError):
            canard_volume_coefficient(4.2, 9, 30, -2.8)


class TestRequiredCanardArea(unittest.TestCase):
    """Required canard area S_c = V_c * S * cbar / arm."""

    def test_anchor_required_area(self):
        # 0.45 * 30 * 2.8 / 9 = 4.2 m2 (within 1e-6).
        self.assertAlmostEqual(
            required_canard_area(0.45, 9, 30, 2.8), 4.2, places=6)

    def test_round_trip_area_to_coefficient(self):
        area = required_canard_area(0.45, 9, 30, 2.8)
        self.assertAlmostEqual(
            canard_volume_coefficient(area, 9, 30, 2.8), 0.45, places=9)

    def test_doubling_target_doubles_area(self):
        self.assertAlmostEqual(
            required_canard_area(0.9, 9, 30, 2.8),
            2 * required_canard_area(0.45, 9, 30, 2.8), places=12)

    def test_doubling_arm_halves_area(self):
        self.assertAlmostEqual(
            required_canard_area(0.45, 18, 30, 2.8),
            0.5 * required_canard_area(0.45, 9, 30, 2.8), places=12)

    def test_non_positive_target_raises(self):
        with self.assertRaises(ValueError):
            required_canard_area(0.0, 9, 30, 2.8)
        with self.assertRaises(ValueError):
            required_canard_area(-0.45, 9, 30, 2.8)

    def test_non_positive_geometry_raises(self):
        with self.assertRaises(ValueError):
            required_canard_area(0.45, 0.0, 30, 2.8)
        with self.assertRaises(ValueError):
            required_canard_area(0.45, 9, 0.0, 2.8)
        with self.assertRaises(ValueError):
            required_canard_area(0.45, 9, 30, 0.0)


class TestCanardLiftShare(unittest.TestCase):
    """Trim lift share f_c = (x_w - x_cg) / (x_w - x_c)."""

    def test_forward_cg_anchor(self):
        # Forward CG x_cg = -3 m on arm -9 m to 0 m: 3 / 9 = 0.3333.
        self.assertAlmostEqual(
            canard_lift_share(-3, 0, -9), 1.0 / 3.0, places=6)

    def test_aft_cg_anchor(self):
        # Aft CG x_cg = -1 m: 1 / 9 = 0.1111.
        self.assertAlmostEqual(
            canard_lift_share(-1, 0, -9), 1.0 / 9.0, places=6)

    def test_share_decreases_as_cg_moves_aft(self):
        self.assertGreater(canard_lift_share(-5, 0, -9),
                           canard_lift_share(-3, 0, -9))
        self.assertGreater(canard_lift_share(-3, 0, -9),
                           canard_lift_share(-1, 0, -9))

    def test_share_bounds_inside_geometry(self):
        share = canard_lift_share(-4.5, 0, -9)
        self.assertGreater(share, 0.0)
        self.assertLess(share, 1.0)

    def test_cg_at_canard_raises(self):
        with self.assertRaises(ValueError):
            canard_lift_share(-9, 0, -9)

    def test_cg_at_wing_raises(self):
        with self.assertRaises(ValueError):
            canard_lift_share(0, 0, -9)

    def test_cg_forward_of_canard_raises(self):
        with self.assertRaises(ValueError):
            canard_lift_share(-10, 0, -9)

    def test_cg_aft_of_wing_raises(self):
        with self.assertRaises(ValueError):
            canard_lift_share(1, 0, -9)


class TestTrimLiftCoefficients(unittest.TestCase):
    """Trim lift coefficients at the worked-example trim condition."""

    WEIGHT = 1200.0 * G0          # N
    Q = 0.5 * 1.225 * 45.0 ** 2   # Pa

    def trim(self, x_cg):
        return trim_lift_coefficients(self.WEIGHT, self.Q, 30, 4.2,
                                      x_cg, 0, -9)

    def test_forward_cg_anchor(self):
        # f_c 0.3333, L_c 3922.7 N, L_w 7845.3 N, canard_cl 0.7526,
        # wing_cl 0.2108 (spec tolerances).
        out = self.trim(-3)
        self.assertAlmostEqual(out["canard_lift_share"], 1.0 / 3.0,
                               places=4)
        self.assertAlmostEqual(out["canard_lift_N"], 3922.7, delta=1.0)
        self.assertAlmostEqual(out["wing_lift_N"], 7845.3, delta=1.0)
        self.assertAlmostEqual(out["canard_cl"], 0.7526, delta=1e-3)
        self.assertAlmostEqual(out["wing_cl"], 0.2108, delta=1e-3)

    def test_aft_cg_anchor(self):
        # f_c 0.1111, canard_cl 0.2510, wing_cl 0.2811.
        out = self.trim(-1)
        self.assertAlmostEqual(out["canard_lift_share"], 1.0 / 9.0,
                               places=4)
        self.assertAlmostEqual(out["canard_cl"], 0.2510, delta=1e-3)
        self.assertAlmostEqual(out["wing_cl"], 0.2811, delta=1e-3)

    def test_lift_split_sums_to_weight(self):
        out = self.trim(-3)
        self.assertAlmostEqual(out["canard_lift_N"] + out["wing_lift_N"],
                               self.WEIGHT, places=6)

    def test_wing_lift_equals_remainder(self):
        out = self.trim(-1)
        self.assertAlmostEqual(
            out["wing_lift_N"],
            self.WEIGHT * (1.0 - out["canard_lift_share"]), places=6)

    def test_lift_coefficient_definitions(self):
        out = self.trim(-3)
        self.assertAlmostEqual(
            out["canard_cl"],
            out["canard_lift_N"] / (self.Q * 4.2), places=9)
        self.assertAlmostEqual(
            out["wing_cl"],
            out["wing_lift_N"] / (self.Q * 30), places=9)

    def test_doubling_dynamic_pressure_halves_cl(self):
        low = trim_lift_coefficients(self.WEIGHT, self.Q, 30, 4.2,
                                     -3, 0, -9)
        high = trim_lift_coefficients(self.WEIGHT, 2.0 * self.Q, 30, 4.2,
                                      -3, 0, -9)
        self.assertAlmostEqual(high["canard_cl"], 0.5 * low["canard_cl"],
                               places=9)
        self.assertAlmostEqual(high["wing_cl"], 0.5 * low["wing_cl"],
                               places=9)

    def test_zero_weight_raises(self):
        with self.assertRaises(ValueError):
            trim_lift_coefficients(0.0, self.Q, 30, 4.2, -3, 0, -9)

    def test_negative_weight_raises(self):
        with self.assertRaises(ValueError):
            trim_lift_coefficients(-1000.0, self.Q, 30, 4.2, -3, 0, -9)

    def test_zero_dynamic_pressure_raises(self):
        with self.assertRaises(ValueError):
            trim_lift_coefficients(self.WEIGHT, 0.0, 30, 4.2, -3, 0, -9)

    def test_negative_dynamic_pressure_raises(self):
        with self.assertRaises(ValueError):
            trim_lift_coefficients(self.WEIGHT, -1.0, 30, 4.2, -3, 0, -9)

    def test_bad_geometry_raises(self):
        # x_cg forward of the canard violates x_c < x_cg < x_w.
        with self.assertRaises(ValueError):
            trim_lift_coefficients(self.WEIGHT, self.Q, 30, 4.2,
                                   -12, 0, -9)
        with self.assertRaises(ValueError):
            trim_lift_coefficients(self.WEIGHT, self.Q, 30, 4.2,
                                   5, 0, -9)

    def test_non_positive_areas_raise(self):
        with self.assertRaises(ValueError):
            trim_lift_coefficients(self.WEIGHT, self.Q, 0.0, 4.2,
                                   -3, 0, -9)
        with self.assertRaises(ValueError):
            trim_lift_coefficients(self.WEIGHT, self.Q, 30, 0.0,
                                   -3, 0, -9)


class TestStallPrecedence(unittest.TestCase):
    """Stall precedence: the smaller margin ratio stalls first."""

    def test_forward_cg_anchor(self):
        # Margin ratios 2.259 (canard) and 7.116 (wing): canard first.
        out = stall_precedence(0.7526, 1.7, 0.2108, 1.5)
        self.assertAlmostEqual(out["canard_margin_ratio"], 2.259,
                               delta=0.01)
        self.assertAlmostEqual(out["wing_margin_ratio"], 7.116,
                               delta=0.01)
        self.assertEqual(out["verdict"], "canard-stalls-first")

    def test_aft_cg_anchor(self):
        # Margin ratios 6.77 (canard) and 5.34 (wing): wing first,
        # demonstrating the pitch-up risk at the aft CG.
        out = stall_precedence(0.2510, 1.7, 0.2811, 1.5)
        self.assertAlmostEqual(out["canard_margin_ratio"], 6.77,
                               delta=0.01)
        self.assertAlmostEqual(out["wing_margin_ratio"], 5.34,
                               delta=0.01)
        self.assertEqual(out["verdict"], "wing-stalls-first")

    def test_margin_ratios_definition(self):
        out = stall_precedence(0.5, 1.6, 0.4, 1.2)
        self.assertAlmostEqual(out["canard_margin_ratio"], 1.6 / 0.5,
                               places=9)
        self.assertAlmostEqual(out["wing_margin_ratio"], 1.2 / 0.4,
                               places=9)

    def test_tie_verdict_defaults_to_wing_stalls_first(self):
        # Equal margin ratios: not canard-stalls-first, so the verdict
        # reports wing-stalls-first (unsafe for a canard layout).
        out = stall_precedence(1.0, 2.0, 1.0, 2.0)
        self.assertEqual(out["verdict"], "wing-stalls-first")

    def test_margin_ratio_verdict_consistent(self):
        out = stall_precedence(0.5, 1.6, 0.6, 1.2)
        # Canard margin 3.2 > wing margin 2.0, so the wing stalls first.
        self.assertEqual(out["verdict"], "wing-stalls-first")

    def test_zero_cl_raises(self):
        with self.assertRaises(ValueError):
            stall_precedence(0.0, 1.7, 0.2, 1.5)
        with self.assertRaises(ValueError):
            stall_precedence(0.5, 1.7, 0.0, 1.5)

    def test_negative_cl_raises(self):
        with self.assertRaises(ValueError):
            stall_precedence(-0.5, 1.7, 0.2, 1.5)
        with self.assertRaises(ValueError):
            stall_precedence(0.5, 1.7, -0.2, 1.5)

    def test_non_positive_cl_max_raises(self):
        with self.assertRaises(ValueError):
            stall_precedence(0.5, 0.0, 0.2, 1.5)
        with self.assertRaises(ValueError):
            stall_precedence(0.5, 1.7, 0.2, -1.5)


class TestSizeCanard(unittest.TestCase):
    """Convenience sizing wrapper."""

    def test_anchor_dict(self):
        out = size_canard(0.45, 9, 30, 2.8)
        self.assertAlmostEqual(out["canard_area"], 4.2, places=6)
        self.assertAlmostEqual(out["canard_volume_coefficient"], 0.45,
                               places=12)

    def test_area_matches_required_area(self):
        out = size_canard(0.45, 9, 30, 2.8)
        self.assertAlmostEqual(out["canard_area"],
                               required_canard_area(0.45, 9, 30, 2.8),
                               places=12)

    def test_invalid_target_propagates(self):
        with self.assertRaises(ValueError):
            size_canard(0.0, 9, 30, 2.8)

    def test_g0_module_constant(self):
        self.assertEqual(G0, 9.80665)


if __name__ == "__main__":
    unittest.main()
