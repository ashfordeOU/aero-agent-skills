"""
Gate 3 contract tests for mathematical-model-quality logic.
stdlib unittest only — offline, deterministic. Run:
    python3 test_mathematical_model_quality.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from mathematical_model_quality_logic import (
    validate_smm_type,
    assess_mesh_quality,
    check_rigid_body_modes,
    check_mass_properties,
    check_static_correlation,
    check_modal_frequency_correlation,
    categorize_finding,
    aggregate_smm_findings,
    VALID_SMM_TYPES,
    RIGID_BODY_MODE_COUNT,
)


class TestValidateSmmType(unittest.TestCase):

    def test_linear_static_accepted(self):
        result = validate_smm_type("linear-static")
        self.assertTrue(result["ok"])
        self.assertIsNone(result["finding"])
        self.assertEqual(result["smm_type"], "linear-static")

    def test_normal_modes_accepted(self):
        result = validate_smm_type("normal-modes")
        self.assertTrue(result["ok"])
        self.assertIsNone(result["finding"])

    def test_buckling_accepted(self):
        result = validate_smm_type("buckling")
        self.assertTrue(result["ok"])

    def test_all_valid_types_accepted(self):
        for smm_type in VALID_SMM_TYPES:
            with self.subTest(smm_type=smm_type):
                result = validate_smm_type(smm_type)
                self.assertTrue(result["ok"])

    def test_unknown_type_rejected(self):
        result = validate_smm_type("thermal-elastic")
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["finding"])
        self.assertIn("thermal-elastic", result["finding"])

    def test_empty_string_rejected(self):
        result = validate_smm_type("")
        self.assertFalse(result["ok"])

    def test_non_string_rejected(self):
        result = validate_smm_type(42)
        self.assertFalse(result["ok"])
        self.assertIn("int", result["finding"])


class TestAssessMeshQuality(unittest.TestCase):

    def test_good_mesh_passes(self):
        result = assess_mesh_quality(
            aspect_ratio=5.0, max_angle_deg=120.0, min_angle_deg=60.0
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["findings"], [])

    def test_aspect_ratio_at_limit_passes(self):
        result = assess_mesh_quality(
            aspect_ratio=10.0, max_angle_deg=90.0, min_angle_deg=90.0
        )
        self.assertTrue(result["ok"])

    def test_aspect_ratio_exceeds_limit_fails(self):
        result = assess_mesh_quality(
            aspect_ratio=15.0, max_angle_deg=90.0, min_angle_deg=90.0
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("aspect ratio" in f for f in result["findings"]))

    def test_zero_aspect_ratio_fails(self):
        result = assess_mesh_quality(
            aspect_ratio=0.0, max_angle_deg=90.0, min_angle_deg=90.0
        )
        self.assertFalse(result["ok"])

    def test_max_angle_exceeds_limit_fails(self):
        result = assess_mesh_quality(
            aspect_ratio=3.0, max_angle_deg=150.0, min_angle_deg=60.0
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("Maximum element angle" in f for f in result["findings"]))

    def test_min_angle_below_limit_fails(self):
        result = assess_mesh_quality(
            aspect_ratio=3.0, max_angle_deg=90.0, min_angle_deg=20.0
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("Minimum element angle" in f for f in result["findings"]))

    def test_multiple_violations_all_reported(self):
        result = assess_mesh_quality(
            aspect_ratio=20.0, max_angle_deg=160.0, min_angle_deg=10.0
        )
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["findings"]), 3)

    def test_custom_limits_respected(self):
        result = assess_mesh_quality(
            aspect_ratio=4.0,
            max_angle_deg=100.0,
            min_angle_deg=80.0,
            aspect_ratio_limit=3.0,
        )
        self.assertFalse(result["ok"])


class TestCheckRigidBodyModes(unittest.TestCase):

    def test_six_near_zero_modes_pass(self):
        freqs = [1e-6, 2e-6, 3e-6, -1e-7, 5e-8, 9e-9]
        result = check_rigid_body_modes(freqs)
        self.assertTrue(result["ok"])
        self.assertEqual(result["findings"], [])

    def test_mode_above_tolerance_fails(self):
        freqs = [1e-6, 1e-6, 1e-6, 1e-6, 1e-6, 0.5]
        result = check_rigid_body_modes(freqs)
        self.assertFalse(result["ok"])
        self.assertTrue(any("mode 6" in f for f in result["findings"]))

    def test_insufficient_mode_count_fails(self):
        freqs = [1e-8, 2e-8, 3e-8]
        result = check_rigid_body_modes(freqs)
        self.assertFalse(result["ok"])
        self.assertTrue(any("at least" in f for f in result["findings"]))

    def test_empty_frequency_list_fails(self):
        result = check_rigid_body_modes([])
        self.assertFalse(result["ok"])

    def test_extra_elastic_modes_ignored_for_rbm_check(self):
        freqs = [1e-8, 2e-8, 3e-8, 4e-8, 5e-8, 6e-8, 50.0, 75.0]
        result = check_rigid_body_modes(freqs)
        self.assertTrue(result["ok"])

    def test_custom_tolerance_tight_fails(self):
        freqs = [0.01, 0.01, 0.01, 0.01, 0.01, 0.01]
        result = check_rigid_body_modes(freqs, tolerance_hz=0.001)
        self.assertFalse(result["ok"])

    def test_custom_tolerance_loose_passes(self):
        freqs = [0.01, 0.01, 0.01, 0.01, 0.01, 0.01]
        result = check_rigid_body_modes(freqs, tolerance_hz=0.1)
        self.assertTrue(result["ok"])

    def test_multiple_bad_modes_each_reported(self):
        freqs = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        result = check_rigid_body_modes(freqs)
        self.assertFalse(result["ok"])
        self.assertEqual(len(result["findings"]), RIGID_BODY_MODE_COUNT)


class TestCheckMassProperties(unittest.TestCase):

    def test_mass_within_tolerance_passes(self):
        result = check_mass_properties(
            smm_mass_kg=100.5, reference_mass_kg=100.0
        )
        self.assertTrue(result["ok"])
        self.assertIsNone(result["finding"])
        self.assertAlmostEqual(result["error_fraction"], 0.005)

    def test_mass_outside_tolerance_fails(self):
        result = check_mass_properties(
            smm_mass_kg=110.0, reference_mass_kg=100.0
        )
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["finding"])
        self.assertIn("110.0000 kg", result["finding"])

    def test_zero_reference_mass_fails(self):
        result = check_mass_properties(smm_mass_kg=50.0, reference_mass_kg=0.0)
        self.assertFalse(result["ok"])
        self.assertIn("positive", result["finding"])

    def test_negative_reference_mass_fails(self):
        result = check_mass_properties(
            smm_mass_kg=50.0, reference_mass_kg=-10.0
        )
        self.assertFalse(result["ok"])

    def test_negative_smm_mass_fails(self):
        result = check_mass_properties(
            smm_mass_kg=-5.0, reference_mass_kg=100.0
        )
        self.assertFalse(result["ok"])
        self.assertIn("non-negative", result["finding"])

    def test_exact_match_passes(self):
        result = check_mass_properties(
            smm_mass_kg=250.0, reference_mass_kg=250.0
        )
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["error_fraction"], 0.0)

    def test_custom_tolerance_tight_fails(self):
        result = check_mass_properties(
            smm_mass_kg=101.0,
            reference_mass_kg=100.0,
            tolerance_fraction=0.005,
        )
        self.assertFalse(result["ok"])

    def test_custom_tolerance_loose_passes(self):
        result = check_mass_properties(
            smm_mass_kg=101.0,
            reference_mass_kg=100.0,
            tolerance_fraction=0.02,
        )
        self.assertTrue(result["ok"])


class TestCheckStaticCorrelation(unittest.TestCase):

    def test_displacement_within_tolerance_passes(self):
        result = check_static_correlation(
            smm_displacement_mm=10.5, test_displacement_mm=10.0
        )
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["error_fraction"], 0.05)

    def test_displacement_outside_tolerance_fails(self):
        result = check_static_correlation(
            smm_displacement_mm=12.0, test_displacement_mm=10.0
        )
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["finding"])
        self.assertIn("20.00%", result["finding"])

    def test_zero_test_displacement_fails(self):
        result = check_static_correlation(
            smm_displacement_mm=5.0, test_displacement_mm=0.0
        )
        self.assertFalse(result["ok"])
        self.assertIn("zero", result["finding"])

    def test_exact_match_passes(self):
        result = check_static_correlation(
            smm_displacement_mm=7.5, test_displacement_mm=7.5
        )
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["error_fraction"], 0.0)

    def test_negative_displacements_compared_by_magnitude(self):
        result = check_static_correlation(
            smm_displacement_mm=-10.5, test_displacement_mm=-10.0
        )
        self.assertTrue(result["ok"])


class TestCheckModalFrequencyCorrelation(unittest.TestCase):

    def test_frequency_within_tolerance_passes(self):
        result = check_modal_frequency_correlation(
            smm_frequency_hz=102.0, test_frequency_hz=100.0
        )
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["error_fraction"], 0.02)

    def test_frequency_outside_tolerance_fails(self):
        result = check_modal_frequency_correlation(
            smm_frequency_hz=115.0, test_frequency_hz=100.0
        )
        self.assertFalse(result["ok"])
        self.assertIsNotNone(result["finding"])
        self.assertIn("15.00%", result["finding"])

    def test_zero_test_frequency_fails(self):
        result = check_modal_frequency_correlation(
            smm_frequency_hz=100.0, test_frequency_hz=0.0
        )
        self.assertFalse(result["ok"])
        self.assertIn("positive", result["finding"])

    def test_negative_smm_frequency_fails(self):
        result = check_modal_frequency_correlation(
            smm_frequency_hz=-10.0, test_frequency_hz=100.0
        )
        self.assertFalse(result["ok"])
        self.assertIn("positive", result["finding"])

    def test_exact_match_passes(self):
        result = check_modal_frequency_correlation(
            smm_frequency_hz=50.0, test_frequency_hz=50.0
        )
        self.assertTrue(result["ok"])
        self.assertAlmostEqual(result["error_fraction"], 0.0)


class TestCategorizeFinding(unittest.TestCase):

    def test_critical_accepted(self):
        self.assertEqual(categorize_finding("critical"), "critical")

    def test_warning_accepted(self):
        self.assertEqual(categorize_finding("warning"), "warning")

    def test_info_accepted(self):
        self.assertEqual(categorize_finding("info"), "info")

    def test_case_insensitive_upper(self):
        self.assertEqual(categorize_finding("CRITICAL"), "critical")

    def test_case_insensitive_mixed(self):
        self.assertEqual(categorize_finding("Warning"), "warning")

    def test_unknown_severity_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            categorize_finding("severe")
        self.assertIn("severe", str(ctx.exception))

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_finding("")


class TestAggregateSmmFindings(unittest.TestCase):

    def test_all_pass_returns_adequate(self):
        results = [
            {"ok": True, "finding": None},
            {"ok": True, "findings": []},
            {"ok": True},
        ]
        agg = aggregate_smm_findings(results)
        self.assertTrue(agg["adequate"])
        self.assertEqual(agg["pass_count"], 3)
        self.assertEqual(agg["fail_count"], 0)
        self.assertEqual(agg["all_findings"], [])

    def test_one_failure_returns_not_adequate(self):
        results = [
            {"ok": True},
            {"ok": False, "finding": "Mass mismatch 5%."},
            {"ok": True},
        ]
        agg = aggregate_smm_findings(results)
        self.assertFalse(agg["adequate"])
        self.assertEqual(agg["fail_count"], 1)
        self.assertIn("Mass mismatch 5%.", agg["all_findings"])

    def test_findings_list_collected(self):
        results = [
            {
                "ok": False,
                "findings": [
                    "Aspect ratio 12.0 exceeds 10.0.",
                    "Min angle 30° below 45°.",
                ],
            }
        ]
        agg = aggregate_smm_findings(results)
        self.assertFalse(agg["adequate"])
        self.assertEqual(len(agg["all_findings"]), 2)

    def test_empty_results_returns_adequate(self):
        agg = aggregate_smm_findings([])
        self.assertTrue(agg["adequate"])
        self.assertEqual(agg["pass_count"], 0)
        self.assertEqual(agg["fail_count"], 0)

    def test_mixed_finding_keys_combined(self):
        results = [
            {"ok": False, "finding": "Single finding."},
            {"ok": False, "findings": ["Finding A.", "Finding B."]},
        ]
        agg = aggregate_smm_findings(results)
        self.assertFalse(agg["adequate"])
        self.assertEqual(len(agg["all_findings"]), 3)
        self.assertEqual(agg["fail_count"], 2)

    def test_end_to_end_full_pass_scenario(self):
        results = [
            validate_smm_type("normal-modes"),
            assess_mesh_quality(5.0, 110.0, 70.0),
            check_rigid_body_modes([1e-7, 2e-7, 3e-7, 4e-7, 5e-7, 6e-7]),
            check_mass_properties(98.0, 100.0),
            check_static_correlation(9.95, 10.0),
            check_modal_frequency_correlation(52.0, 51.5),
        ]
        agg = aggregate_smm_findings(results)
        self.assertTrue(agg["adequate"])
        self.assertEqual(agg["fail_count"], 0)

    def test_end_to_end_multiple_failures_scenario(self):
        results = [
            validate_smm_type("unknown-type"),
            assess_mesh_quality(20.0, 90.0, 90.0),
            check_rigid_body_modes([0.0, 0.0, 0.0, 0.0, 0.0, 2.0]),
            check_mass_properties(120.0, 100.0),
            check_static_correlation(13.0, 10.0),
            check_modal_frequency_correlation(60.0, 50.0),
        ]
        agg = aggregate_smm_findings(results)
        self.assertFalse(agg["adequate"])
        self.assertGreaterEqual(agg["fail_count"], 4)


if __name__ == "__main__":
    unittest.main()
