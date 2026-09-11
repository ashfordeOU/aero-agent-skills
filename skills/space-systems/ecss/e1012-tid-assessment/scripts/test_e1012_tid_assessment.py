"""
Gate 3 contract tests for e1012-tid-assessment logic.

Run: python3 test_e1012_tid_assessment.py
Requires: stdlib only, offline, deterministic. Minimum 10 tests.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_tid_assessment_logic import (
    COMPONENT_CATEGORIES,
    ORBIT_DOSE_RATE_KRAD_YR,
    compute_tid,
    assess_component,
    categorize_component,
    assess_mission,
)


# ---------------------------------------------------------------------------
# compute_tid
# ---------------------------------------------------------------------------

class TestComputeTid(unittest.TestCase):

    def test_geo_2mm_5yr(self):
        # 10.0 krad/yr * 5 yr * 1000 = 50 000 rad
        self.assertAlmostEqual(compute_tid("GEO", 2, 5), 50_000.0)

    def test_geo_5mm_1yr(self):
        # 5.0 krad/yr * 1 yr * 1000 = 5 000 rad
        self.assertAlmostEqual(compute_tid("GEO", 5, 1), 5_000.0)

    def test_leo_10mm_10yr(self):
        # 0.1 krad/yr * 10 yr * 1000 = 1 000 rad
        self.assertAlmostEqual(compute_tid("LEO_500km", 10, 10), 1_000.0)

    def test_meo_2mm_1yr(self):
        # 50.0 krad/yr * 1 yr * 1000 = 50 000 rad
        self.assertAlmostEqual(compute_tid("MEO_20200km", 2, 1), 50_000.0)

    def test_fractional_duration(self):
        # GEO 5mm: 5.0 krad/yr * 0.5 yr * 1000 = 2 500 rad
        self.assertAlmostEqual(compute_tid("GEO", 5, 0.5), 2_500.0)

    def test_invalid_orbit_raises(self):
        with self.assertRaises(ValueError):
            compute_tid("UNKNOWN_ORBIT", 2, 1)

    def test_invalid_shield_raises(self):
        with self.assertRaises(ValueError):
            compute_tid("GEO", 3, 1)  # 3 mm not in table

    def test_zero_duration_raises(self):
        with self.assertRaises(ValueError):
            compute_tid("GEO", 2, 0)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            compute_tid("GEO", 2, -2)

    def test_result_is_float(self):
        result = compute_tid("LEO_500km", 5, 3)
        self.assertIsInstance(result, float)


# ---------------------------------------------------------------------------
# assess_component
# ---------------------------------------------------------------------------

class TestAssessComponent(unittest.TestCase):

    def test_standard_non_compliant(self):
        # required = 50 000 * 2 = 100 000 > 5 000 limit
        result = assess_component(50_000, "standard")
        self.assertFalse(result["compliant"])

    def test_standard_compliant(self):
        # required = 1 000 * 2 = 2 000 <= 5 000 limit
        result = assess_component(1_000, "standard")
        self.assertTrue(result["compliant"])

    def test_rad_hard_compliant(self):
        # required = 10 000 * 2 = 20 000 <= 300 000 limit
        result = assess_component(10_000, "rad_hard")
        self.assertTrue(result["compliant"])

    def test_rad_hardened_non_compliant(self):
        # required = 600 000 * 2 = 1 200 000 > 1 000 000 limit
        result = assess_component(600_000, "rad_hardened")
        self.assertFalse(result["compliant"])

    def test_margin_applied_to_required(self):
        result = assess_component(1_000, "standard", margin=2.0)
        self.assertAlmostEqual(result["required_rad"], 2_000.0)

    def test_custom_margin(self):
        result = assess_component(1_000, "standard", margin=3.0)
        self.assertAlmostEqual(result["required_rad"], 3_000.0)
        self.assertEqual(result["margin_factor"], 3.0)

    def test_limit_returned_correctly(self):
        result = assess_component(100, "rad_tolerant")
        self.assertEqual(result["limit_rad"], 30_000)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            assess_component(1_000, "super_hard")

    def test_negative_tid_raises(self):
        with self.assertRaises(ValueError):
            assess_component(-1, "standard")

    def test_zero_margin_raises(self):
        with self.assertRaises(ValueError):
            assess_component(1_000, "standard", margin=0)

    def test_boundary_exactly_at_limit(self):
        # required = 5 000 * 1.0 = 5 000 == 5 000 limit → compliant
        result = assess_component(5_000, "standard", margin=1.0)
        self.assertTrue(result["compliant"])


# ---------------------------------------------------------------------------
# categorize_component
# ---------------------------------------------------------------------------

class TestCategorizeComponent(unittest.TestCase):

    def test_low_tolerance_is_standard(self):
        self.assertEqual(categorize_component(3_000), "standard")

    def test_at_standard_boundary(self):
        self.assertEqual(categorize_component(5_000), "standard")

    def test_above_standard_is_rad_tolerant(self):
        self.assertEqual(categorize_component(5_001), "rad_tolerant")

    def test_mid_rad_tolerant(self):
        self.assertEqual(categorize_component(25_000), "rad_tolerant")

    def test_rad_hard_range(self):
        self.assertEqual(categorize_component(200_000), "rad_hard")

    def test_at_rad_hard_boundary(self):
        self.assertEqual(categorize_component(300_000), "rad_hard")

    def test_above_rad_hard_is_rad_hardened(self):
        self.assertEqual(categorize_component(300_001), "rad_hardened")

    def test_very_high_tolerance_is_rad_hardened(self):
        self.assertEqual(categorize_component(2_000_000), "rad_hardened")

    def test_zero_tid_raises(self):
        with self.assertRaises(ValueError):
            categorize_component(0)

    def test_negative_tid_raises(self):
        with self.assertRaises(ValueError):
            categorize_component(-1)


# ---------------------------------------------------------------------------
# assess_mission
# ---------------------------------------------------------------------------

class TestAssessMission(unittest.TestCase):

    def test_returns_one_result_per_component(self):
        components = [
            {"name": "MCU", "category": "rad_hard"},
            {"name": "OpAmp", "category": "standard"},
        ]
        results = assess_mission(components, "GEO", 2, 1)
        self.assertEqual(len(results), 2)

    def test_rad_hard_passes_at_geo(self):
        # GEO 2mm 1yr → 10 000 rad; required = 20 000 < 300 000
        components = [{"name": "MCU", "category": "rad_hard"}]
        result = assess_mission(components, "GEO", 2, 1)[0]
        self.assertTrue(result["compliant"])

    def test_standard_fails_at_geo(self):
        # GEO 2mm 1yr → 10 000 rad; required = 20 000 > 5 000
        components = [{"name": "OpAmp", "category": "standard"}]
        result = assess_mission(components, "GEO", 2, 1)[0]
        self.assertFalse(result["compliant"])

    def test_tid_attached_to_result(self):
        components = [{"name": "FPGA", "category": "rad_tolerant"}]
        result = assess_mission(components, "LEO_500km", 10, 5)[0]
        self.assertAlmostEqual(result["tid_rad"], 500.0)  # 0.1 * 5 * 1000

    def test_missing_name_key_raises(self):
        with self.assertRaises(ValueError):
            assess_mission([{"category": "standard"}], "GEO", 2, 1)

    def test_missing_category_key_raises(self):
        with self.assertRaises(ValueError):
            assess_mission([{"name": "Sensor"}], "GEO", 2, 1)

    def test_empty_component_list(self):
        results = assess_mission([], "GEO", 5, 3)
        self.assertEqual(results, [])

    def test_custom_margin_propagates(self):
        components = [{"name": "X", "category": "rad_hardened"}]
        result = assess_mission(components, "GEO", 2, 1, margin=1.0)[0]
        # required = 10 000 * 1.0 = 10 000 <= 1 000 000
        self.assertTrue(result["compliant"])
        self.assertEqual(result["margin_factor"], 1.0)


if __name__ == "__main__":
    unittest.main()
