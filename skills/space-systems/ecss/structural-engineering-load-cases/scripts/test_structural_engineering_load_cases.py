"""
Gate 3 contract tests — structural-engineering-load-cases
ECSS-E-ST-32C clause 5.2

stdlib unittest only; offline; deterministic.
Run: python3 test_structural_engineering_load_cases.py
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from structural_engineering_load_cases_logic import (
    CREEP_THRESHOLD_HOURS,
    SAFETY_FACTORS,
    apply_scatter_factor,
    categorize_design_situation,
    categorize_load_case,
    check_creep_rupture,
    check_sustained_loading,
    combine_loads,
    compute_design_load,
    validate_load_case,
)


class TestCategorizeLoadCase(unittest.TestCase):

    def test_all_valid_types_accepted(self):
        for lc_type in ("limit", "yield", "ultimate", "proof", "fatigue", "creep-rupture"):
            self.assertEqual(categorize_load_case(lc_type), lc_type)

    def test_normalization_strips_whitespace_and_lowercases(self):
        self.assertEqual(categorize_load_case("  Yield  "), "yield")
        self.assertEqual(categorize_load_case("ULTIMATE"), "ultimate")

    def test_unrecognized_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_load_case("buckling")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            categorize_load_case("")


class TestCategorizeDesignSituation(unittest.TestCase):

    def test_all_valid_situations_accepted(self):
        valid = (
            "launch", "transfer-orbit", "on-orbit", "re-entry",
            "landing", "ground-handling", "transportation", "storage",
        )
        for sit in valid:
            self.assertEqual(categorize_design_situation(sit), sit)

    def test_unrecognized_situation_raises(self):
        with self.assertRaises(ValueError):
            categorize_design_situation("ascent")

    def test_case_insensitive_normalization(self):
        self.assertEqual(categorize_design_situation("Launch"), "launch")


class TestCombineLoads(unittest.TestCase):

    def test_absolute_sum_single_load(self):
        result = combine_loads({"mechanical": 100.0}, method="absolute")
        self.assertAlmostEqual(result, 100.0)

    def test_absolute_sum_multiple_loads(self):
        result = combine_loads(
            {"mechanical": 50.0, "thermal": 30.0, "pressure": 20.0},
            method="absolute",
        )
        self.assertAlmostEqual(result, 100.0)

    def test_absolute_sum_handles_negative_components(self):
        result = combine_loads({"mechanical": -40.0, "thermal": 60.0}, method="absolute")
        self.assertAlmostEqual(result, 100.0)

    def test_srss_two_loads(self):
        result = combine_loads({"vibration": 3.0, "acoustic": 4.0}, method="srss")
        self.assertAlmostEqual(result, 5.0)

    def test_srss_single_load(self):
        result = combine_loads({"shock": 7.5}, method="srss")
        self.assertAlmostEqual(result, 7.5)

    def test_empty_mapping_raises(self):
        with self.assertRaises(ValueError):
            combine_loads({})

    def test_unrecognized_method_raises(self):
        with self.assertRaises(ValueError):
            combine_loads({"mechanical": 100.0}, method="rss")


class TestApplyScatterFactor(unittest.TestCase):

    def test_scatter_factor_one_returns_unchanged(self):
        self.assertAlmostEqual(apply_scatter_factor(200.0, 1.0), 200.0)

    def test_scatter_factor_multiplied_correctly(self):
        self.assertAlmostEqual(apply_scatter_factor(100.0, 1.25), 125.0)

    def test_scatter_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            apply_scatter_factor(100.0, 0.9)

    def test_negative_load_raises(self):
        with self.assertRaises(ValueError):
            apply_scatter_factor(-50.0, 1.1)

    def test_zero_load_returns_zero(self):
        self.assertAlmostEqual(apply_scatter_factor(0.0, 1.5), 0.0)


class TestComputeDesignLoad(unittest.TestCase):

    def test_limit_case_no_additional_safety_factor(self):
        result = compute_design_load(1000.0, "limit", scatter_factor=1.0)
        self.assertAlmostEqual(result, 1000.0)

    def test_ultimate_case_default_safety_factor(self):
        # 1000 × 1.0 scatter × 1.25 ultimate
        result = compute_design_load(1000.0, "ultimate", scatter_factor=1.0)
        self.assertAlmostEqual(result, 1250.0)

    def test_yield_case_default_safety_factor(self):
        result = compute_design_load(1000.0, "yield", scatter_factor=1.0)
        self.assertAlmostEqual(result, 1100.0)

    def test_scatter_applied_before_safety_factor(self):
        # 500 × 1.2 scatter = 600; × 1.25 ultimate = 750
        result = compute_design_load(500.0, "ultimate", scatter_factor=1.2)
        self.assertAlmostEqual(result, 750.0)

    def test_override_safety_factor_respected(self):
        result = compute_design_load(
            1000.0, "ultimate", scatter_factor=1.0, safety_factor=1.5
        )
        self.assertAlmostEqual(result, 1500.0)

    def test_unrecognized_type_raises(self):
        with self.assertRaises(ValueError):
            compute_design_load(100.0, "dynamic")


class TestCheckSustainedLoading(unittest.TestCase):

    def test_creep_sensitive_material_long_duration_triggers(self):
        result = check_sustained_loading(
            duration_hours=100.0, material="aluminium-alloy"
        )
        self.assertTrue(result["creep_required"])
        self.assertTrue(result["creep_rupture_required"])

    def test_creep_sensitive_material_short_duration_no_trigger(self):
        result = check_sustained_loading(
            duration_hours=0.5, material="composite-cfrp"
        )
        self.assertFalse(result["creep_required"])
        self.assertFalse(result["creep_rupture_required"])

    def test_non_creep_sensitive_material_no_trigger(self):
        result = check_sustained_loading(
            duration_hours=500.0, material="steel"
        )
        self.assertFalse(result["creep_required"])
        self.assertIn("not in the creep-sensitive set", result["reason"])

    def test_exactly_at_threshold_triggers(self):
        result = check_sustained_loading(
            duration_hours=CREEP_THRESHOLD_HOURS, material="polymer"
        )
        self.assertTrue(result["creep_required"])

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            check_sustained_loading(duration_hours=-1.0, material="adhesive")

    def test_reason_string_present_in_result(self):
        result = check_sustained_loading(2.0, "titanium-alloy")
        self.assertIn("reason", result)
        self.assertIsInstance(result["reason"], str)


class TestCheckCreepRupture(unittest.TestCase):

    def test_pass_when_allowable_exceeds_applied(self):
        result = check_creep_rupture(
            applied_stress=100.0,
            allowable_creep_rupture_stress=150.0,
            duration_hours=1000.0,
        )
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["ms"], 0.5)

    def test_fail_when_applied_exceeds_allowable(self):
        result = check_creep_rupture(
            applied_stress=200.0,
            allowable_creep_rupture_stress=150.0,
            duration_hours=500.0,
        )
        self.assertFalse(result["passes"])
        self.assertLess(result["ms"], 0.0)

    def test_ms_exactly_zero_passes(self):
        result = check_creep_rupture(100.0, 100.0, 1.0)
        self.assertTrue(result["passes"])
        self.assertAlmostEqual(result["ms"], 0.0)

    def test_zero_applied_stress_raises(self):
        with self.assertRaises(ValueError):
            check_creep_rupture(0.0, 100.0, 10.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            check_creep_rupture(100.0, 0.0, 10.0)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            check_creep_rupture(100.0, 120.0, -5.0)

    def test_finding_string_contains_verdict(self):
        result = check_creep_rupture(100.0, 150.0, 200.0)
        self.assertIn("PASS", result["finding"])


class TestValidateLoadCase(unittest.TestCase):

    def _valid_record(self):
        return {
            "type": "ultimate",
            "situation": "launch",
            "limit_load": 5000.0,
            "scatter_factor": 1.1,
        }

    def test_valid_record_returns_no_findings(self):
        findings = validate_load_case(self._valid_record())
        self.assertEqual(findings, [])

    def test_invalid_type_reported(self):
        rec = self._valid_record()
        rec["type"] = "dynamic"
        findings = validate_load_case(rec)
        self.assertTrue(any("type" in f.lower() or "dynamic" in f for f in findings))

    def test_invalid_situation_reported(self):
        rec = self._valid_record()
        rec["situation"] = "deep-space"
        findings = validate_load_case(rec)
        self.assertTrue(len(findings) > 0)

    def test_missing_limit_load_reported(self):
        rec = self._valid_record()
        del rec["limit_load"]
        findings = validate_load_case(rec)
        self.assertTrue(any("limit_load" in f for f in findings))

    def test_negative_limit_load_reported(self):
        rec = self._valid_record()
        rec["limit_load"] = -10.0
        findings = validate_load_case(rec)
        self.assertTrue(any("limit_load" in f for f in findings))

    def test_scatter_factor_below_one_reported(self):
        rec = self._valid_record()
        rec["scatter_factor"] = 0.8
        findings = validate_load_case(rec)
        self.assertTrue(any("scatter_factor" in f for f in findings))

    def test_negative_duration_reported(self):
        rec = self._valid_record()
        rec["duration_hours"] = -2.0
        findings = validate_load_case(rec)
        self.assertTrue(any("duration_hours" in f for f in findings))

    def test_multiple_errors_all_reported(self):
        rec = {
            "type": "bad-type",
            "situation": "bad-situation",
            "limit_load": -100.0,
            "scatter_factor": 0.5,
        }
        findings = validate_load_case(rec)
        self.assertGreaterEqual(len(findings), 4)


if __name__ == "__main__":
    unittest.main()
