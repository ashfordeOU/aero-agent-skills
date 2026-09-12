import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from drd_dimstab_analysis_logic import (
    REQUIRED_SECTIONS,
    VALID_CONTRIBUTOR_TYPES,
    assess_cte_mismatch,
    categorize_displacement_contributors,
    check_stability_requirement,
    compute_combined_displacement,
    compute_hygrothermal_displacement,
    compute_stability_margin,
    compute_thermal_displacement,
    validate_analysis_method,
    validate_material_entry,
    validate_required_sections,
)


class TestValidateRequiredSections(unittest.TestCase):
    def test_complete_report_returns_empty_list(self):
        report = {s: {} for s in REQUIRED_SECTIONS}
        self.assertEqual(validate_required_sections(report), [])

    def test_empty_report_returns_all_required(self):
        missing = validate_required_sections({})
        self.assertEqual(missing, REQUIRED_SECTIONS)

    def test_partial_report_flags_missing_keys(self):
        report = {"scope": {}, "structure_description": {}}
        missing = validate_required_sections(report)
        self.assertIn("material_properties", missing)
        self.assertNotIn("scope", missing)
        self.assertNotIn("structure_description", missing)

    def test_non_dict_raises_type_error(self):
        with self.assertRaises(TypeError):
            validate_required_sections("not a dict")

    def test_extra_keys_do_not_affect_result(self):
        report = {s: {} for s in REQUIRED_SECTIONS}
        report["extra_section"] = {}
        self.assertEqual(validate_required_sections(report), [])


class TestComputeThermalDisplacement(unittest.TestCase):
    def test_positive_delta_T_gives_positive_displacement(self):
        # alpha=2e-6 /K, L=1000 mm, dT=100 K -> 0.2 mm
        result = compute_thermal_displacement(2e-6, 1000.0, 100.0)
        self.assertAlmostEqual(result, 0.2, places=12)

    def test_negative_delta_T_gives_negative_displacement(self):
        result = compute_thermal_displacement(2e-6, 1000.0, -50.0)
        self.assertAlmostEqual(result, -0.1, places=12)

    def test_zero_alpha_gives_zero(self):
        result = compute_thermal_displacement(0.0, 500.0, 100.0)
        self.assertEqual(result, 0.0)

    def test_nan_alpha_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_thermal_displacement(float("nan"), 1000.0, 100.0)

    def test_zero_length_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_thermal_displacement(2e-6, 0.0, 100.0)

    def test_negative_length_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_thermal_displacement(2e-6, -100.0, 50.0)

    def test_inf_delta_T_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_thermal_displacement(2e-6, 1000.0, float("inf"))


class TestComputeHygrothermalDisplacement(unittest.TestCase):
    def test_basic_calculation(self):
        # beta=0.001 /%, L=500 mm, dM=2 % -> 1.0 mm
        result = compute_hygrothermal_displacement(0.001, 500.0, 2.0)
        self.assertAlmostEqual(result, 1.0, places=12)

    def test_zero_moisture_change_gives_zero(self):
        result = compute_hygrothermal_displacement(0.001, 500.0, 0.0)
        self.assertEqual(result, 0.0)

    def test_inf_beta_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_hygrothermal_displacement(float("inf"), 500.0, 1.0)

    def test_negative_moisture_change_gives_negative_displacement(self):
        result = compute_hygrothermal_displacement(0.001, 200.0, -1.0)
        self.assertAlmostEqual(result, -0.2, places=12)


class TestComputeCombinedDisplacement(unittest.TestCase):
    def test_additive_contributions(self):
        result = compute_combined_displacement(0.2, 1.0)
        self.assertAlmostEqual(result, 1.2, places=12)

    def test_opposing_contributions(self):
        result = compute_combined_displacement(0.5, -0.3)
        self.assertAlmostEqual(result, 0.2, places=12)

    def test_both_zero_gives_zero(self):
        self.assertEqual(compute_combined_displacement(0.0, 0.0), 0.0)

    def test_nan_thermal_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_combined_displacement(float("nan"), 0.1)

    def test_nan_hygro_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_combined_displacement(0.1, float("nan"))


class TestComputeStabilityMargin(unittest.TestCase):
    def test_positive_margin_when_within_allowable(self):
        # allowable=0.5, actual=0.2 -> margin=1.5
        result = compute_stability_margin(0.5, 0.2)
        self.assertAlmostEqual(result, 1.5, places=12)

    def test_zero_margin_at_allowable_limit(self):
        result = compute_stability_margin(0.3, 0.3)
        self.assertAlmostEqual(result, 0.0, places=12)

    def test_negative_margin_when_exceeding_allowable(self):
        result = compute_stability_margin(0.2, 0.5)
        self.assertLess(result, 0.0)

    def test_zero_actual_returns_inf(self):
        self.assertEqual(compute_stability_margin(0.5, 0.0), float("inf"))

    def test_zero_allowable_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_stability_margin(0.0, 0.1)

    def test_negative_actual_uses_magnitude(self):
        result = compute_stability_margin(0.5, -0.2)
        self.assertAlmostEqual(result, 1.5, places=12)

    def test_negative_allowable_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_stability_margin(-0.1, 0.1)


class TestAssessCTEMismatch(unittest.TestCase):
    def test_matching_materials_do_not_exceed(self):
        result = assess_cte_mismatch(2e-6, 2e-6, 1e-6)
        self.assertFalse(result["exceeds"])
        self.assertAlmostEqual(result["mismatch"], 0.0)

    def test_large_mismatch_exceeds_threshold(self):
        result = assess_cte_mismatch(2e-6, 5e-6, 1e-6)
        self.assertTrue(result["exceeds"])
        self.assertAlmostEqual(result["mismatch"], 3e-6)

    def test_mismatch_exactly_at_threshold_does_not_exceed(self):
        result = assess_cte_mismatch(0.0, 1e-6, 1e-6)
        self.assertFalse(result["exceeds"])

    def test_result_contains_required_keys(self):
        result = assess_cte_mismatch(1e-6, 3e-6, 2e-6)
        self.assertIn("mismatch", result)
        self.assertIn("threshold", result)
        self.assertIn("exceeds", result)

    def test_nan_alpha_raises_value_error(self):
        with self.assertRaises(ValueError):
            assess_cte_mismatch(float("nan"), 2e-6, 1e-6)

    def test_negative_threshold_raises_value_error(self):
        with self.assertRaises(ValueError):
            assess_cte_mismatch(2e-6, 3e-6, -1e-6)

    def test_order_of_materials_does_not_affect_mismatch(self):
        r1 = assess_cte_mismatch(1e-6, 4e-6, 5e-6)
        r2 = assess_cte_mismatch(4e-6, 1e-6, 5e-6)
        self.assertAlmostEqual(r1["mismatch"], r2["mismatch"])


class TestValidateMaterialEntry(unittest.TestCase):
    def test_valid_material_returns_empty_issues(self):
        material = {"name": "CFRP", "alpha_per_K": 2e-6, "beta_per_pct": 0.001, "E_GPa": 70.0}
        self.assertEqual(validate_material_entry(material), [])

    def test_missing_beta_field_flagged(self):
        material = {"name": "AL6061", "alpha_per_K": 23e-6, "E_GPa": 70.0}
        issues = validate_material_entry(material)
        self.assertTrue(any("beta_per_pct" in i for i in issues))

    def test_non_numeric_alpha_flagged(self):
        material = {"name": "Ti6Al4V", "alpha_per_K": "not-a-number", "beta_per_pct": 0.0, "E_GPa": 110.0}
        issues = validate_material_entry(material)
        self.assertTrue(any("alpha_per_K" in i for i in issues))

    def test_non_finite_E_flagged(self):
        material = {"name": "X", "alpha_per_K": 2e-6, "beta_per_pct": 0.0, "E_GPa": float("inf")}
        issues = validate_material_entry(material)
        self.assertTrue(any("E_GPa" in i for i in issues))

    def test_missing_name_flagged(self):
        material = {"alpha_per_K": 2e-6, "beta_per_pct": 0.0, "E_GPa": 70.0}
        issues = validate_material_entry(material)
        self.assertTrue(any("name" in i for i in issues))

    def test_non_dict_raises_type_error(self):
        with self.assertRaises(TypeError):
            validate_material_entry([1, 2, 3])


class TestCategorizeDisplacementContributors(unittest.TestCase):
    def test_known_types_go_to_correct_buckets(self):
        contributors = [
            {"type": "thermal", "source": "solar_flux"},
            {"type": "hygrothermal", "source": "moisture_release"},
            {"type": "mechanical", "source": "launch_preload"},
        ]
        result = categorize_displacement_contributors(contributors)
        self.assertEqual(len(result["thermal"]), 1)
        self.assertEqual(len(result["hygrothermal"]), 1)
        self.assertEqual(len(result["mechanical"]), 1)
        self.assertEqual(len(result["unknown"]), 0)

    def test_unknown_type_goes_to_unknown_bucket(self):
        contributors = [{"type": "creep", "source": "long_duration"}]
        result = categorize_displacement_contributors(contributors)
        self.assertEqual(len(result["unknown"]), 1)

    def test_empty_list_returns_empty_buckets(self):
        result = categorize_displacement_contributors([])
        for t in VALID_CONTRIBUTOR_TYPES:
            self.assertEqual(result[t], [])
        self.assertEqual(result["unknown"], [])

    def test_non_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_displacement_contributors({"type": "thermal"})

    def test_mixed_case_type_recognized(self):
        contributors = [{"type": "Thermal", "source": "eclipse_exit"}]
        result = categorize_displacement_contributors(contributors)
        self.assertEqual(len(result["thermal"]), 1)


class TestCheckStabilityRequirement(unittest.TestCase):
    def test_displacement_within_requirement_passes(self):
        self.assertEqual(check_stability_requirement(0.05, 0.1), "PASS")

    def test_displacement_exactly_at_requirement_passes(self):
        self.assertEqual(check_stability_requirement(0.1, 0.1), "PASS")

    def test_displacement_exceeding_requirement_fails(self):
        self.assertEqual(check_stability_requirement(0.2, 0.1), "FAIL")

    def test_negative_displacement_uses_magnitude(self):
        self.assertEqual(check_stability_requirement(-0.05, 0.1), "PASS")

    def test_zero_requirement_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_stability_requirement(0.05, 0.0)

    def test_nan_displacement_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_stability_requirement(float("nan"), 0.1)


class TestValidateAnalysisMethod(unittest.TestCase):
    def test_analytical_is_valid(self):
        self.assertTrue(validate_analysis_method("analytical"))

    def test_fea_is_valid(self):
        self.assertTrue(validate_analysis_method("fea"))

    def test_test_correlated_is_valid(self):
        self.assertTrue(validate_analysis_method("test_correlated"))

    def test_unknown_method_is_invalid(self):
        self.assertFalse(validate_analysis_method("guesswork"))

    def test_non_string_is_invalid(self):
        self.assertFalse(validate_analysis_method(42))

    def test_empty_string_is_invalid(self):
        self.assertFalse(validate_analysis_method(""))


if __name__ == "__main__":
    unittest.main()
