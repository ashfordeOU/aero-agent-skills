"""
Stdlib unittest for special_item_fracture_control_logic.
Offline, deterministic. Run: python3 test_special_item_fracture_control.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from special_item_fracture_control_logic import (
    validate_category,
    check_non_metallic,
    check_rotating_machinery,
    check_glass,
    check_fastener,
    check_edm_alloy,
    assess_item,
    VALID_CATEGORIES,
    NON_METALLIC_MIN_PROOF_FACTOR,
    BURST_SPEED_MARGIN,
    GLASS_MIN_PROOF_RATIO,
    EDM_MIN_REMOVAL_DEPTH_MM,
)


class TestValidateCategory(unittest.TestCase):

    def test_all_valid_categories_accepted(self):
        for cat in VALID_CATEGORIES:
            self.assertEqual(validate_category(cat), cat)

    def test_unknown_category_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_category("ceramic")

    def test_empty_string_category_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_category("")

    def test_near_miss_category_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_category("glasses")


class TestNonMetallic(unittest.TestCase):

    def test_proof_test_at_minimum_factor_compliant(self):
        result = check_non_metallic("proof_test", proof_factor=NON_METALLIC_MIN_PROOF_FACTOR)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_proof_test_above_minimum_factor_compliant(self):
        result = check_non_metallic("proof_test", proof_factor=2.0)
        self.assertTrue(result["compliant"])

    def test_proof_test_below_minimum_factor_noncompliant(self):
        result = check_non_metallic("proof_test", proof_factor=1.2)
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["findings"]), 0)

    def test_analysis_method_compliant_without_factor(self):
        result = check_non_metallic("analysis")
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_similarity_method_compliant_without_factor(self):
        result = check_non_metallic("similarity")
        self.assertTrue(result["compliant"])

    def test_invalid_method_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_non_metallic("fracture_mechanics")

    def test_proof_test_without_factor_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_non_metallic("proof_test")

    def test_proof_test_factor_just_below_threshold_noncompliant(self):
        result = check_non_metallic("proof_test", proof_factor=1.499)
        self.assertFalse(result["compliant"])


class TestRotatingMachinery(unittest.TestCase):

    def test_margin_above_threshold_compliant(self):
        result = check_rotating_machinery(1000.0, 1300.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin"], 1.3)

    def test_margin_at_exact_threshold_compliant(self):
        result = check_rotating_machinery(1000.0, 1250.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin"], BURST_SPEED_MARGIN)

    def test_margin_below_threshold_noncompliant(self):
        result = check_rotating_machinery(1000.0, 1200.0)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["margin"], 1.2)

    def test_finding_text_references_section(self):
        result = check_rotating_machinery(1000.0, 1000.0)
        self.assertFalse(result["compliant"])
        self.assertIn("§8.6", result["findings"][0])

    def test_zero_operating_speed_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_rotating_machinery(0.0, 1250.0)

    def test_zero_burst_speed_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_rotating_machinery(1000.0, 0.0)

    def test_negative_operating_speed_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_rotating_machinery(-500.0, 1250.0)


class TestGlass(unittest.TestCase):

    def test_ratio_above_threshold_compliant(self):
        result = check_glass(100.0, 140.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["ratio"], 1.4)

    def test_ratio_at_exact_threshold_compliant(self):
        result = check_glass(100.0, 130.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["ratio"], GLASS_MIN_PROOF_RATIO)

    def test_ratio_below_threshold_noncompliant(self):
        result = check_glass(100.0, 120.0)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["ratio"], 1.2)

    def test_finding_text_references_section(self):
        result = check_glass(100.0, 100.0)
        self.assertFalse(result["compliant"])
        self.assertIn("§8.7", result["findings"][0])

    def test_zero_design_stress_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_glass(0.0, 130.0)

    def test_zero_proof_stress_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_glass(100.0, 0.0)


class TestFastener(unittest.TestCase):

    def test_grade_a_torque_controlled_non_tension_critical_exempt(self):
        result = check_fastener("A", True, False)
        self.assertTrue(result["exempt"])
        self.assertEqual(result["findings"], [])

    def test_grade_b_torque_controlled_non_tension_critical_exempt(self):
        result = check_fastener("B", True, False)
        self.assertTrue(result["exempt"])

    def test_non_standard_grade_not_exempt(self):
        result = check_fastener("C", True, False)
        self.assertFalse(result["exempt"])
        self.assertGreater(len(result["findings"]), 0)

    def test_non_torque_controlled_not_exempt(self):
        result = check_fastener("A", False, False)
        self.assertFalse(result["exempt"])

    def test_tension_critical_joint_not_exempt(self):
        result = check_fastener("A", True, True)
        self.assertFalse(result["exempt"])

    def test_all_three_disqualifying_conditions_produces_three_findings(self):
        result = check_fastener("X", False, True)
        self.assertFalse(result["exempt"])
        self.assertEqual(len(result["findings"]), 3)

    def test_finding_text_references_section(self):
        result = check_fastener("Z", False, True)
        combined = " ".join(result["findings"])
        self.assertIn("§8.8", combined)


class TestEdmAlloy(unittest.TestCase):

    def test_adequate_depth_with_process_compliant(self):
        result = check_edm_alloy(0.15, "chemical_etching")
        self.assertTrue(result["compliant"])

    def test_exact_minimum_depth_with_process_compliant(self):
        result = check_edm_alloy(EDM_MIN_REMOVAL_DEPTH_MM, "grinding")
        self.assertTrue(result["compliant"])

    def test_insufficient_depth_noncompliant(self):
        result = check_edm_alloy(0.05, "grinding")
        self.assertFalse(result["compliant"])

    def test_missing_process_noncompliant(self):
        result = check_edm_alloy(0.15, None)
        self.assertFalse(result["compliant"])

    def test_empty_process_string_noncompliant(self):
        result = check_edm_alloy(0.15, "")
        self.assertFalse(result["compliant"])

    def test_zero_depth_noncompliant(self):
        result = check_edm_alloy(0.0, "etching")
        self.assertFalse(result["compliant"])

    def test_negative_depth_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_edm_alloy(-0.05, "etching")

    def test_both_depth_and_process_missing_produces_two_findings(self):
        result = check_edm_alloy(0.0, None)
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)

    def test_finding_text_references_section(self):
        result = check_edm_alloy(0.0, "etching")
        self.assertIn("§8.9", result["findings"][0])


class TestAssessItem(unittest.TestCase):

    def test_non_metallic_proof_test_compliant_item(self):
        item = {
            "name": "composite_bracket",
            "category": "non_metallic",
            "method": "proof_test",
            "proof_factor": 1.6,
        }
        result = assess_item(item)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["name"], "composite_bracket")
        self.assertEqual(result["category"], "non_metallic")

    def test_rotating_machinery_compliant_item(self):
        item = {
            "name": "turbine_wheel",
            "category": "rotating_machinery",
            "operating_speed_rpm": 5000.0,
            "burst_speed_rpm": 6500.0,
        }
        result = assess_item(item)
        self.assertTrue(result["compliant"])

    def test_glass_noncompliant_item_carries_findings(self):
        item = {
            "name": "viewport_lens",
            "category": "glass",
            "design_stress_mpa": 50.0,
            "proof_stress_mpa": 55.0,
        }
        result = assess_item(item)
        self.assertFalse(result["compliant"])
        self.assertGreater(len(result["findings"]), 0)

    def test_fastener_exempt_item_reported_compliant(self):
        item = {
            "name": "panel_bolt",
            "category": "fastener",
            "grade": "A",
            "torque_controlled": True,
            "tension_critical": False,
        }
        result = assess_item(item)
        self.assertTrue(result["compliant"])

    def test_edm_alloy_compliant_item(self):
        item = {
            "name": "edm_spar_fitting",
            "category": "edm_treated_alloy",
            "removal_depth_mm": 0.12,
            "removal_process": "electrochemical_etching",
        }
        result = assess_item(item)
        self.assertTrue(result["compliant"])

    def test_invalid_category_in_assess_raises_value_error(self):
        with self.assertRaises(ValueError):
            assess_item({"name": "unknown_part", "category": "ceramic"})

    def test_assess_result_always_has_required_keys(self):
        item = {
            "name": "test_part",
            "category": "non_metallic",
            "method": "similarity",
        }
        result = assess_item(item)
        for key in ("name", "category", "compliant", "findings"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()
