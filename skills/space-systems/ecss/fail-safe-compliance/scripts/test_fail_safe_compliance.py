"""
Gate 3 contract tests for fail_safe_compliance_logic.
stdlib unittest only — offline, deterministic. Run:
    python3 test_fail_safe_compliance.py
Expected output: OK
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from fail_safe_compliance_logic import (
    categorize_item,
    validate_damage_scenario,
    check_residual_strength,
    estimate_cycles_to_critical,
    check_inspection_detectability,
    check_inspection_interval,
    check_wfd_potential,
    check_fail_safe_compliance,
    MIN_INSPECTION_OPPORTUNITIES,
    ITEM_CATEGORIES,
    DAMAGE_SCENARIOS,
    INSPECTION_METHODS,
)


# ── categorize_item ──────────────────────────────────────────────────────────

class TestCategorizeItem(unittest.TestCase):

    def test_fail_safe_recognized(self):
        self.assertEqual(categorize_item("fail-safe"), "fail-safe")

    def test_safe_life_recognized(self):
        self.assertEqual(categorize_item("safe-life"), "safe-life")

    def test_damage_tolerant_recognized(self):
        self.assertEqual(categorize_item("damage-tolerant"), "damage-tolerant")

    def test_unrecognized_category_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_item("unknown-category")

    def test_non_string_raises_type_error(self):
        with self.assertRaises(TypeError):
            categorize_item(42)

    def test_whitespace_stripped_before_comparison(self):
        self.assertEqual(categorize_item("  fail-safe  "), "fail-safe")


# ── validate_damage_scenario ─────────────────────────────────────────────────

class TestValidateDamageScenario(unittest.TestCase):

    def test_element_loss_recognized(self):
        self.assertEqual(validate_damage_scenario("element-loss"), "element-loss")

    def test_through_crack_recognized(self):
        self.assertEqual(validate_damage_scenario("through-crack"), "through-crack")

    def test_partial_crack_recognized(self):
        self.assertEqual(validate_damage_scenario("partial-crack"), "partial-crack")

    def test_bay_failure_recognized(self):
        self.assertEqual(validate_damage_scenario("bay-failure"), "bay-failure")

    def test_unrecognized_scenario_raises(self):
        with self.assertRaises(ValueError):
            validate_damage_scenario("explosion")

    def test_non_string_raises_type_error(self):
        with self.assertRaises(TypeError):
            validate_damage_scenario(None)


# ── check_residual_strength ──────────────────────────────────────────────────

class TestCheckResidualStrength(unittest.TestCase):

    def test_compliant_when_strength_exceeds_required(self):
        result = check_residual_strength(150.0, 100.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin"], 0.5)

    def test_non_compliant_when_strength_below_required(self):
        result = check_residual_strength(80.0, 100.0)
        self.assertFalse(result["compliant"])
        self.assertLess(result["margin"], 0.0)

    def test_compliant_at_exact_limit(self):
        result = check_residual_strength(100.0, 100.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin"], 0.0)

    def test_negative_strength_raises(self):
        with self.assertRaises(ValueError):
            check_residual_strength(-10.0, 100.0)

    def test_zero_required_load_raises(self):
        with self.assertRaises(ValueError):
            check_residual_strength(100.0, 0.0)

    def test_result_contains_input_values(self):
        result = check_residual_strength(120.0, 80.0)
        self.assertEqual(result["residual_strength_kN"], 120.0)
        self.assertEqual(result["required_load_kN"], 80.0)


# ── estimate_cycles_to_critical ──────────────────────────────────────────────

class TestEstimateCyclesToCritical(unittest.TestCase):

    def test_basic_calculation(self):
        # (15 - 5) / 0.5 = 20 cycles
        self.assertEqual(estimate_cycles_to_critical(5.0, 15.0, 0.5), 20)

    def test_ceiling_applied(self):
        # (15.3 - 5.0) / 0.5 = 20.6 → ceil → 21
        self.assertEqual(estimate_cycles_to_critical(5.0, 15.3, 0.5), 21)

    def test_returns_zero_when_initial_at_critical(self):
        self.assertEqual(estimate_cycles_to_critical(15.0, 15.0, 0.5), 0)

    def test_returns_zero_when_initial_exceeds_critical(self):
        self.assertEqual(estimate_cycles_to_critical(20.0, 10.0, 0.5), 0)

    def test_zero_growth_rate_raises(self):
        with self.assertRaises(ValueError):
            estimate_cycles_to_critical(5.0, 15.0, 0.0)

    def test_negative_initial_size_raises(self):
        with self.assertRaises(ValueError):
            estimate_cycles_to_critical(-1.0, 15.0, 0.5)


# ── check_inspection_detectability ───────────────────────────────────────────

class TestCheckInspectionDetectability(unittest.TestCase):

    def test_detectable_when_damage_above_threshold(self):
        result = check_inspection_detectability(10.0, 5.0, "visual")
        self.assertTrue(result["detectable"])

    def test_not_detectable_when_damage_below_threshold(self):
        result = check_inspection_detectability(3.0, 5.0, "ultrasonic")
        self.assertFalse(result["detectable"])

    def test_detectable_at_exact_threshold(self):
        result = check_inspection_detectability(5.0, 5.0, "eddy-current")
        self.assertTrue(result["detectable"])

    def test_unrecognized_method_raises(self):
        with self.assertRaises(ValueError):
            check_inspection_detectability(10.0, 5.0, "sonar")

    def test_method_normalized_to_lowercase(self):
        result = check_inspection_detectability(10.0, 5.0, "X-Ray")
        self.assertEqual(result["inspection_method"], "x-ray")


# ── check_inspection_interval ────────────────────────────────────────────────

class TestCheckInspectionInterval(unittest.TestCase):

    def test_compliant_with_ample_opportunities(self):
        # 100 cycles / 20 interval = 5 opportunities >= 2
        result = check_inspection_interval(100, 20)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["opportunities"], 5)

    def test_not_compliant_with_one_opportunity(self):
        # 30 cycles / 20 interval = 1 opportunity < 2
        result = check_inspection_interval(30, 20)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["opportunities"], 1)

    def test_zero_cycles_gives_zero_opportunities(self):
        result = check_inspection_interval(0, 20)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["opportunities"], 0)

    def test_custom_min_opportunities_respected(self):
        # 100 / 20 = 5 opportunities; require 6 → fail
        result = check_inspection_interval(100, 20, min_opportunities=6)
        self.assertFalse(result["compliant"])

    def test_exactly_two_opportunities_is_compliant(self):
        # 40 cycles / 20 interval = 2 opportunities = minimum
        result = check_inspection_interval(40, 20)
        self.assertTrue(result["compliant"])

    def test_min_opportunities_constant_is_two(self):
        self.assertEqual(MIN_INSPECTION_OPPORTUNITIES, 2)


# ── check_wfd_potential ──────────────────────────────────────────────────────

class TestCheckWfdPotential(unittest.TestCase):

    def test_no_wfd_risk_when_fraction_below_threshold(self):
        # 100 / 1000 = 0.1 < 0.5
        result = check_wfd_potential(10, 1000, 100)
        self.assertFalse(result["wfd_risk"])
        self.assertAlmostEqual(result["consumed_fraction"], 0.1)

    def test_wfd_risk_when_fraction_at_threshold(self):
        # 500 / 1000 = 0.5 == 0.5
        result = check_wfd_potential(10, 1000, 500)
        self.assertTrue(result["wfd_risk"])
        self.assertAlmostEqual(result["consumed_fraction"], 0.5)

    def test_wfd_risk_when_fraction_above_threshold(self):
        # 700 / 1000 = 0.7 > 0.5
        result = check_wfd_potential(10, 1000, 700)
        self.assertTrue(result["wfd_risk"])

    def test_custom_threshold_respected(self):
        # 100 / 1000 = 0.1 < custom threshold 0.05 → no risk; 0.1 >= 0.05 → risk
        result = check_wfd_potential(10, 1000, 100, wfd_threshold_fraction=0.05)
        self.assertTrue(result["wfd_risk"])

    def test_zero_threshold_raises(self):
        with self.assertRaises(ValueError):
            check_wfd_potential(10, 1000, 100, wfd_threshold_fraction=0.0)

    def test_result_records_element_count(self):
        result = check_wfd_potential(8, 1000, 100)
        self.assertEqual(result["element_count"], 8)


# ── check_fail_safe_compliance (aggregate) ────────────────────────────────────

class TestCheckFailSafeCompliance(unittest.TestCase):

    def _base_scenario(self):
        return {
            "item_id": "STR-101",
            "damage_scenario": "element-loss",
            "residual_strength_kN": 150.0,
            "required_load_kN": 100.0,
            "initial_damage_mm": 10.0,
            "critical_damage_mm": 60.0,
            "growth_rate_mm_per_cycle": 0.5,
            "inspection_interval_cycles": 20,
            "inspection_method": "visual",
            "detection_threshold_mm": 5.0,
            "element_count": 8,
            "element_fatigue_life_cycles": 10000,
        }

    def test_fully_compliant_scenario(self):
        result = check_fail_safe_compliance(self._base_scenario())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_item_id_preserved_in_result(self):
        result = check_fail_safe_compliance(self._base_scenario())
        self.assertEqual(result["item_id"], "STR-101")

    def test_fails_when_residual_strength_too_low(self):
        s = self._base_scenario()
        s["residual_strength_kN"] = 50.0
        result = check_fail_safe_compliance(s)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("Residual strength" in f for f in result["findings"]))

    def test_fails_when_inspection_interval_too_wide(self):
        s = self._base_scenario()
        # 50mm growth / 0.5mm/cycle = 100 cycles; interval 60 → 1 opportunity < 2
        s["inspection_interval_cycles"] = 60
        result = check_fail_safe_compliance(s)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("Inspection interval" in f for f in result["findings"]))

    def test_fails_when_initial_damage_below_detection_threshold(self):
        s = self._base_scenario()
        s["detection_threshold_mm"] = 15.0  # initial damage 10mm is below
        result = check_fail_safe_compliance(s)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("detection threshold" in f for f in result["findings"]))

    def test_fails_when_wfd_risk_present(self):
        s = self._base_scenario()
        s["element_fatigue_life_cycles"] = 30  # 20/30 = 0.667 > 0.5 threshold
        result = check_fail_safe_compliance(s)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("WFD" in f for f in result["findings"]))

    def test_missing_key_raises_value_error(self):
        s = self._base_scenario()
        del s["residual_strength_kN"]
        with self.assertRaises(ValueError):
            check_fail_safe_compliance(s)

    def test_unrecognized_damage_scenario_raises(self):
        s = self._base_scenario()
        s["damage_scenario"] = "meteor-strike"
        with self.assertRaises(ValueError):
            check_fail_safe_compliance(s)

    def test_multiple_findings_reported(self):
        s = self._base_scenario()
        s["residual_strength_kN"] = 50.0      # residual strength fail
        s["element_fatigue_life_cycles"] = 30  # WFD fail
        result = check_fail_safe_compliance(s)
        self.assertFalse(result["compliant"])
        self.assertGreaterEqual(len(result["findings"]), 2)

    def test_result_contains_all_sub_checks(self):
        result = check_fail_safe_compliance(self._base_scenario())
        for key in ("residual_strength_check", "inspection_interval_check",
                    "detectability_check", "wfd_check"):
            self.assertIn(key, result)

    def test_through_crack_scenario_accepted(self):
        s = self._base_scenario()
        s["damage_scenario"] = "through-crack"
        result = check_fail_safe_compliance(s)
        self.assertIn("compliant", result)

    def test_bay_failure_scenario_accepted(self):
        s = self._base_scenario()
        s["damage_scenario"] = "bay-failure"
        result = check_fail_safe_compliance(s)
        self.assertIn("compliant", result)


if __name__ == "__main__":
    unittest.main()
