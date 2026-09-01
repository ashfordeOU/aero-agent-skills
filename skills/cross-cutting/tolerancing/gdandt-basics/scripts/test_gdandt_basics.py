#!/usr/bin/env python3
"""Gate 3 contract test: GD&T basics logic.

Exercises scripts/gdandt_basics_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3. Covers feature control
frame parsing (symbol, tolerance, diameter flag, material condition
modifier, datum references), form/orientation/location categorization,
tolerance zone types, modifier meanings, MMC and LMC bonus tolerance,
total tolerance at MMC, MMC/LMC boundary sizes from size limits, the
full frame interpreter, and invalid-input edge cases including
malformed frames, zero tolerance at MMC, and material condition
comparisons.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gdandt_basics_logic as gdandt  # noqa: E402


class ParseFeatureControlFrameTest(unittest.TestCase):
    def test_parse_position_frame_with_mmc(self):
        parsed = gdandt.parse_feature_control_frame("position|⌀0.5(M)|A|B(M)|C")
        self.assertEqual(parsed["symbol"], "position")
        self.assertAlmostEqual(parsed["tolerance"], 0.5)
        self.assertTrue(parsed["diameter"])
        self.assertEqual(parsed["modifier"], "M")
        self.assertEqual(
            parsed["datums"],
            [
                {"letter": "A", "modifier": None},
                {"letter": "B", "modifier": "M"},
                {"letter": "C", "modifier": None},
            ],
        )

    def test_parse_form_frame_without_datum(self):
        parsed = gdandt.parse_feature_control_frame("flatness|0.2")
        self.assertEqual(parsed["symbol"], "flatness")
        self.assertAlmostEqual(parsed["tolerance"], 0.2)
        self.assertFalse(parsed["diameter"])
        self.assertIsNone(parsed["modifier"])
        self.assertEqual(parsed["datums"], [])

    def test_parse_rfs_default_and_s_modifier(self):
        self.assertIsNone(gdandt.parse_feature_control_frame("position|⌀0.4|A")["modifier"])
        self.assertEqual(
            gdandt.parse_feature_control_frame("position|⌀0.4(S)|A")["modifier"], "S"
        )

    def test_parse_zero_tolerance_at_mmc(self):
        parsed = gdandt.parse_feature_control_frame("position|⌀0(M)|A|B|C")
        self.assertEqual(parsed["tolerance"], 0.0)
        self.assertEqual(parsed["modifier"], "M")

    def test_parse_lmc_modifier(self):
        self.assertEqual(
            gdandt.parse_feature_control_frame("perpendicularity|0.1(L)|A")["modifier"],
            "L",
        )

    def test_empty_frame_raises(self):
        with self.assertRaises(ValueError):
            gdandt.parse_feature_control_frame("")
        with self.assertRaises(ValueError):
            gdandt.parse_feature_control_frame("   ")

    def test_unknown_symbol_raises(self):
        with self.assertRaises(ValueError):
            gdandt.parse_feature_control_frame("wobble|0.5|A")

    def test_missing_tolerance_raises(self):
        with self.assertRaises(ValueError):
            gdandt.parse_feature_control_frame("position")

    def test_malformed_tolerance_raises(self):
        with self.assertRaises(ValueError):
            gdandt.parse_feature_control_frame("position|abc|A")
        with self.assertRaises(ValueError):
            gdandt.parse_feature_control_frame("position|⌀|A")

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            gdandt.parse_feature_control_frame("position|⌀-0.5|A")

    def test_invalid_modifier_raises(self):
        with self.assertRaises(ValueError):
            gdandt.parse_feature_control_frame("position|⌀0.5(X)|A")
        with self.assertRaises(ValueError):
            gdandt.parse_feature_control_frame("position|⌀0.5(M)|A(X)")

    def test_too_many_datums_raises(self):
        with self.assertRaises(ValueError):
            gdandt.parse_feature_control_frame("position|⌀0.5(M)|A|B|C|D")

    def test_form_tolerance_with_datum_raises(self):
        with self.assertRaises(ValueError):
            gdandt.parse_feature_control_frame("flatness|0.2|A")


class CategoryAndZoneTest(unittest.TestCase):
    def test_form_category(self):
        for symbol in ("flatness", "straightness", "circularity", "cylindricity"):
            self.assertEqual(gdandt.tolerance_category(symbol), "form")

    def test_orientation_category(self):
        for symbol in ("perpendicularity", "parallelism", "angularity"):
            self.assertEqual(gdandt.tolerance_category(symbol), "orientation")

    def test_location_profile_runout_categories(self):
        self.assertEqual(gdandt.tolerance_category("position"), "location")
        self.assertEqual(gdandt.tolerance_category("profile"), "profile")
        self.assertEqual(gdandt.tolerance_category("total-runout"), "runout")

    def test_zone_types(self):
        self.assertIn("cylindrical", gdandt.tolerance_zone_type("position"))
        self.assertIn("parallel planes", gdandt.tolerance_zone_type("flatness"))
        self.assertIn("annulus", gdandt.tolerance_zone_type("circularity"))

    def test_unknown_symbol_raises(self):
        with self.assertRaises(ValueError):
            gdandt.tolerance_category("wobble")
        with self.assertRaises(ValueError):
            gdandt.tolerance_zone_type("wobble")


class ModifierTest(unittest.TestCase):
    def test_material_condition_modifier(self):
        self.assertEqual(
            gdandt.material_condition_modifier("position|⌀0.5(M)|A"), "M"
        )
        self.assertEqual(
            gdandt.material_condition_modifier("position|⌀0.5(L)|A"), "L"
        )
        self.assertIsNone(
            gdandt.material_condition_modifier("position|⌀0.5|A")
        )

    def test_modifier_meanings(self):
        self.assertIn("maximum material condition", gdandt.modifier_meaning("M"))
        self.assertIn("least material condition", gdandt.modifier_meaning("L"))
        self.assertIn("regardless of feature size", gdandt.modifier_meaning("S"))
        self.assertIn("regardless of feature size", gdandt.modifier_meaning(None))

    def test_invalid_modifier_meaning_raises(self):
        with self.assertRaises(ValueError):
            gdandt.modifier_meaning("X")


class BonusToleranceTest(unittest.TestCase):
    def test_hole_bonus_grows_as_hole_grows(self):
        zero = gdandt.bonus_tolerance_at_mmc(10.0, 10.0, "hole")
        self.assertEqual(zero, 0.0)
        self.assertAlmostEqual(
            gdandt.bonus_tolerance_at_mmc(10.3, 10.0, "hole"), 0.3
        )

    def test_pin_bonus_grows_as_pin_shrinks(self):
        self.assertEqual(gdandt.bonus_tolerance_at_mmc(10.0, 10.0, "pin"), 0.0)
        self.assertAlmostEqual(
            gdandt.bonus_tolerance_at_mmc(9.7, 10.0, "pin"), 0.3
        )

    def test_hole_below_mmc_raises(self):
        with self.assertRaises(ValueError):
            gdandt.bonus_tolerance_at_mmc(9.9, 10.0, "hole")

    def test_pin_above_mmc_raises(self):
        with self.assertRaises(ValueError):
            gdandt.bonus_tolerance_at_mmc(10.1, 10.0, "pin")

    def test_lmc_bonus_opposite_direction(self):
        # Hole LMC is the largest hole: bonus grows as the hole shrinks.
        self.assertEqual(gdandt.bonus_tolerance_at_lmc(10.3, 10.3, "hole"), 0.0)
        self.assertAlmostEqual(
            gdandt.bonus_tolerance_at_lmc(10.0, 10.3, "hole"), 0.3
        )
        # Pin LMC is the smallest pin: bonus grows as the pin grows.
        self.assertEqual(gdandt.bonus_tolerance_at_lmc(9.7, 9.7, "pin"), 0.0)
        self.assertAlmostEqual(
            gdandt.bonus_tolerance_at_lmc(10.0, 9.7, "pin"), 0.3
        )

    def test_lmc_violations_raise(self):
        with self.assertRaises(ValueError):
            gdandt.bonus_tolerance_at_lmc(10.5, 10.3, "hole")
        with self.assertRaises(ValueError):
            gdandt.bonus_tolerance_at_lmc(9.5, 9.7, "pin")

    def test_invalid_part_type_raises(self):
        with self.assertRaises(ValueError):
            gdandt.bonus_tolerance_at_mmc(10.0, 10.0, "slot")
        with self.assertRaises(ValueError):
            gdandt.bonus_tolerance_at_lmc(10.0, 10.0, "slot")


class BoundarySizeTest(unittest.TestCase):
    LIMITS = (10.0, 10.3)

    def test_mmc_size(self):
        self.assertEqual(gdandt.mmc_size(self.LIMITS, "hole"), 10.0)
        self.assertEqual(gdandt.mmc_size(self.LIMITS, "pin"), 10.3)

    def test_lmc_size(self):
        self.assertEqual(gdandt.lmc_size(self.LIMITS, "hole"), 10.3)
        self.assertEqual(gdandt.lmc_size(self.LIMITS, "pin"), 10.0)

    def test_invalid_limits_raise(self):
        with self.assertRaises(ValueError):
            gdandt.mmc_size((10.3, 10.0), "hole")
        with self.assertRaises(ValueError):
            gdandt.mmc_size((10.0, 10.0), "hole")


class TotalToleranceTest(unittest.TestCase):
    def test_total_is_stated_plus_bonus(self):
        total = gdandt.total_tolerance_at_mmc(0.5, 10.3, 10.0, "hole")
        self.assertAlmostEqual(total, 0.8)

    def test_total_at_mmc_is_stated_only(self):
        total = gdandt.total_tolerance_at_mmc(0.5, 10.0, 10.0, "hole")
        self.assertAlmostEqual(total, 0.5)

    def test_negative_stated_raises(self):
        with self.assertRaises(ValueError):
            gdandt.total_tolerance_at_mmc(-0.1, 10.0, 10.0, "hole")


class InterpretFrameTest(unittest.TestCase):
    def test_interpret_without_sizes(self):
        result = gdandt.interpret_feature_control_frame("position|⌀0.5(M)|A|B|C")
        self.assertEqual(result["symbol"], "position")
        self.assertEqual(result["category"], "location")
        self.assertIn("cylindrical", result["zone_type"])
        self.assertEqual(result["modifier"], "M")
        self.assertEqual(len(result["datums"]), 3)
        self.assertNotIn("bonus_tolerance", result)

    def test_interpret_with_mmc_bonus(self):
        result = gdandt.interpret_feature_control_frame(
            "position|⌀0.5(M)|A|B|C", actual_size=10.3, mmc_size_value=10.0,
            part_type="hole"
        )
        self.assertAlmostEqual(result["bonus_tolerance"], 0.3)
        self.assertAlmostEqual(result["total_tolerance"], 0.8)

    def test_interpret_zero_tolerance_at_mmc(self):
        result = gdandt.interpret_feature_control_frame(
            "position|⌀0(M)|A|B|C", actual_size=10.2, mmc_size_value=10.0,
            part_type="hole"
        )
        self.assertEqual(result["tolerance"], 0.0)
        self.assertAlmostEqual(result["bonus_tolerance"], 0.2)
        self.assertAlmostEqual(result["total_tolerance"], 0.2)

    def test_interpret_rfs_ignores_sizes(self):
        result = gdandt.interpret_feature_control_frame(
            "position|⌀0.5|A|B|C", actual_size=10.3, mmc_size_value=10.0,
            part_type="hole"
        )
        self.assertNotIn("bonus_tolerance", result)

    def test_interpret_partial_sizes_raise(self):
        with self.assertRaises(ValueError):
            gdandt.interpret_feature_control_frame(
                "position|⌀0.5(M)|A", actual_size=10.3, mmc_size_value=None,
                part_type="hole"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
