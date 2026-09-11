"""
Gate 3 contract tests — e1011-anthropometry
ECSS-E-ST-10-11C §4.5.1 Anthropometric and biomechanical design verification.

Runs with: python3 test_e1011_anthropometry.py
Must print OK. stdlib unittest only. No network access.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1011_anthropometry_logic import (
    AnthropometryError,
    REACH_FORWARD,
    REACH_SIDE,
    REACH_OVERHEAD,
    REGION_STATURE,
    REGION_SEATED_HEIGHT,
    REGION_ARM_LENGTH,
    REGION_NONE,
    interpolate_percentile,
    check_dimension_accommodation,
    check_reach_requirement,
    check_strength_requirement,
    apply_microgravity_correction,
    compute_accommodation_percentage,
)


class TestInterpolatePercentile(unittest.TestCase):

    def test_at_p5_returns_p5_value(self):
        result = interpolate_percentile(1600.0, 1900.0, 5.0)
        # At the 5th percentile anchor the result must equal p5 exactly.
        self.assertAlmostEqual(result, 1600.0, places=6)

    def test_at_p95_returns_p95_value(self):
        result = interpolate_percentile(1600.0, 1900.0, 95.0)
        self.assertAlmostEqual(result, 1900.0, places=6)

    def test_at_p50_midpoint(self):
        # p50 should be exactly halfway between p5 and p95.
        result = interpolate_percentile(1600.0, 1900.0, 50.0)
        expected = 1600.0 + (50.0 - 5.0) / (95.0 - 5.0) * (1900.0 - 1600.0)
        self.assertAlmostEqual(result, expected, places=6)

    def test_invalid_percentile_zero_raises(self):
        with self.assertRaises(AnthropometryError):
            interpolate_percentile(1600.0, 1900.0, 0.0)

    def test_invalid_percentile_100_raises(self):
        with self.assertRaises(AnthropometryError):
            interpolate_percentile(1600.0, 1900.0, 100.0)

    def test_p5_equal_to_p95_raises(self):
        with self.assertRaises(AnthropometryError):
            interpolate_percentile(1700.0, 1700.0, 50.0)

    def test_p5_greater_than_p95_raises(self):
        with self.assertRaises(AnthropometryError):
            interpolate_percentile(1900.0, 1600.0, 50.0)


class TestCheckDimensionAccommodation(unittest.TestCase):

    def test_full_accommodation(self):
        result = check_dimension_accommodation(1580.0, 1920.0, 1600.0, 1900.0)
        self.assertTrue(result["accommodated"])
        self.assertEqual(result["shortfall_low"], 0.0)
        self.assertEqual(result["shortfall_high"], 0.0)

    def test_shortfall_at_low_end(self):
        # design_min (1620) exceeds population_p5 (1600) — smallest users excluded.
        result = check_dimension_accommodation(1620.0, 1920.0, 1600.0, 1900.0)
        self.assertFalse(result["accommodated"])
        self.assertAlmostEqual(result["shortfall_low"], 20.0, places=5)
        self.assertEqual(result["shortfall_high"], 0.0)

    def test_shortfall_at_high_end(self):
        # design_max (1880) is less than population_p95 (1900) — largest users excluded.
        result = check_dimension_accommodation(1580.0, 1880.0, 1600.0, 1900.0)
        self.assertFalse(result["accommodated"])
        self.assertEqual(result["shortfall_low"], 0.0)
        self.assertAlmostEqual(result["shortfall_high"], 20.0, places=5)

    def test_shortfall_at_both_ends(self):
        result = check_dimension_accommodation(1620.0, 1880.0, 1600.0, 1900.0)
        self.assertFalse(result["accommodated"])
        self.assertGreater(result["shortfall_low"], 0.0)
        self.assertGreater(result["shortfall_high"], 0.0)

    def test_design_min_exceeds_design_max_raises(self):
        with self.assertRaises(AnthropometryError):
            check_dimension_accommodation(1900.0, 1600.0, 1600.0, 1900.0)

    def test_population_p5_equal_p95_raises(self):
        with self.assertRaises(AnthropometryError):
            check_dimension_accommodation(1580.0, 1920.0, 1750.0, 1750.0)


class TestCheckReachRequirement(unittest.TestCase):

    def test_forward_reach_compliant(self):
        result = check_reach_requirement(600.0, 650.0, 800.0, REACH_FORWARD)
        self.assertTrue(result["reachable_by_p5"])
        self.assertEqual(result["shortfall_p5"], 0.0)
        self.assertEqual(result["reach_type"], REACH_FORWARD)

    def test_forward_reach_non_compliant(self):
        # p5 reach (600 mm) is less than required reach (650 mm).
        result = check_reach_requirement(650.0, 600.0, 800.0, REACH_FORWARD)
        self.assertFalse(result["reachable_by_p5"])
        self.assertAlmostEqual(result["shortfall_p5"], 50.0, places=3)

    def test_overhead_reach_type_accepted(self):
        result = check_reach_requirement(400.0, 450.0, 600.0, REACH_OVERHEAD)
        self.assertEqual(result["reach_type"], REACH_OVERHEAD)

    def test_side_reach_type_accepted(self):
        result = check_reach_requirement(350.0, 400.0, 560.0, REACH_SIDE)
        self.assertEqual(result["reach_type"], REACH_SIDE)

    def test_invalid_reach_type_raises(self):
        with self.assertRaises(AnthropometryError):
            check_reach_requirement(500.0, 550.0, 700.0, "diagonal")

    def test_non_positive_required_reach_raises(self):
        with self.assertRaises(AnthropometryError):
            check_reach_requirement(0.0, 550.0, 700.0, REACH_FORWARD)

    def test_p50_reach_reported(self):
        result = check_reach_requirement(500.0, 600.0, 800.0, REACH_FORWARD)
        # p50 should be between p5 and p95.
        self.assertGreater(result["reach_p50"], result["reach_p5"])
        self.assertLess(result["reach_p50"], result["reach_p95"])


class TestCheckStrengthRequirement(unittest.TestCase):

    def test_compliant_with_positive_margin(self):
        result = check_strength_requirement(80.0, 100.0, 250.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_n"], 20.0, places=5)

    def test_exact_boundary_is_compliant(self):
        result = check_strength_requirement(100.0, 100.0, 250.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin_n"], 0.0, places=5)

    def test_non_compliant_exceeds_p5(self):
        result = check_strength_requirement(120.0, 100.0, 250.0)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["margin_n"], -20.0, places=5)

    def test_negative_required_force_raises(self):
        with self.assertRaises(AnthropometryError):
            check_strength_requirement(-10.0, 100.0, 250.0)

    def test_non_positive_strength_p5_raises(self):
        with self.assertRaises(AnthropometryError):
            check_strength_requirement(80.0, 0.0, 250.0)

    def test_strength_p5_equal_p95_raises(self):
        with self.assertRaises(AnthropometryError):
            check_strength_requirement(80.0, 200.0, 200.0)


class TestApplyMicrogravityCorrection(unittest.TestCase):

    def test_stature_correction_applied(self):
        result = apply_microgravity_correction(1750.0, REGION_STATURE)
        self.assertAlmostEqual(result["corrected_value_mm"], 1750.0 * 1.03, places=3)
        self.assertEqual(result["correction_factor"], 0.03)

    def test_seated_height_correction_applied(self):
        result = apply_microgravity_correction(900.0, REGION_SEATED_HEIGHT)
        self.assertAlmostEqual(result["corrected_value_mm"], 900.0 * 1.03, places=3)

    def test_arm_length_no_correction(self):
        result = apply_microgravity_correction(750.0, REGION_ARM_LENGTH)
        self.assertAlmostEqual(result["corrected_value_mm"], 750.0, places=3)
        self.assertEqual(result["correction_factor"], 0.0)

    def test_region_none_no_correction(self):
        result = apply_microgravity_correction(500.0, REGION_NONE)
        self.assertAlmostEqual(result["corrected_value_mm"], 500.0, places=3)

    def test_invalid_region_raises(self):
        with self.assertRaises(AnthropometryError):
            apply_microgravity_correction(1700.0, "torso_length")

    def test_non_positive_ground_value_raises(self):
        with self.assertRaises(AnthropometryError):
            apply_microgravity_correction(0.0, REGION_STATURE)

    def test_ground_value_preserved_in_result(self):
        result = apply_microgravity_correction(1800.0, REGION_STATURE)
        self.assertEqual(result["ground_value_mm"], 1800.0)
        self.assertEqual(result["body_region"], REGION_STATURE)


class TestComputeAccommodationPercentage(unittest.TestCase):

    def test_full_range_returns_90_percent(self):
        # Design exactly spans p5 to p95 — 90 % of population accommodated.
        result = compute_accommodation_percentage(1600.0, 1900.0, 1600.0, 1900.0)
        self.assertAlmostEqual(result, 90.0, places=3)

    def test_wider_design_still_90_percent(self):
        # Design wider than population range — still capped at 90 % (p5–p95 span).
        result = compute_accommodation_percentage(1500.0, 2000.0, 1600.0, 1900.0)
        self.assertAlmostEqual(result, 90.0, places=3)

    def test_zero_accommodation_when_design_above_population(self):
        # Design entirely above population range — nobody accommodated.
        result = compute_accommodation_percentage(1950.0, 2100.0, 1600.0, 1900.0)
        self.assertEqual(result, 0.0)

    def test_partial_accommodation(self):
        # Design starts at p5 and ends halfway to p95.
        result = compute_accommodation_percentage(1600.0, 1750.0, 1600.0, 1900.0)
        self.assertGreater(result, 0.0)
        self.assertLess(result, 90.0)

    def test_design_min_greater_than_max_raises(self):
        with self.assertRaises(AnthropometryError):
            compute_accommodation_percentage(1900.0, 1600.0, 1600.0, 1900.0)

    def test_population_p5_equal_p95_raises(self):
        with self.assertRaises(AnthropometryError):
            compute_accommodation_percentage(1600.0, 1900.0, 1750.0, 1750.0)


if __name__ == "__main__":
    unittest.main()
