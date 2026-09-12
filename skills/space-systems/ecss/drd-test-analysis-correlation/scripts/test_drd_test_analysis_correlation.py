"""
Gate 3 contract tests for drd_test_analysis_correlation_logic.
stdlib unittest only. Offline, deterministic.
Run: python3 test_drd_test_analysis_correlation.py
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from drd_test_analysis_correlation_logic import (
    assess_quantity_correlation,
    build_correlation_summary,
    categorize_quantity,
    check_drd_completeness,
    check_frequency_correlation,
    check_mac_correlation,
    compute_relative_delta,
    determine_model_update_required,
    DEFAULT_FREQUENCY_THRESHOLD,
    DEFAULT_MAC_THRESHOLD,
    DEFAULT_DAMPING_THRESHOLD,
    DEFAULT_DEFLECTION_THRESHOLD,
    DEFAULT_STRESS_THRESHOLD,
    REQUIRED_DRD_SECTIONS,
    VALID_QUANTITY_TYPES,
)


class TestCategorizeQuantity(unittest.TestCase):

    def test_frequency_accepted(self):
        self.assertEqual(categorize_quantity("frequency"), "frequency")

    def test_mode_shape_accepted(self):
        self.assertEqual(categorize_quantity("mode_shape"), "mode_shape")

    def test_static_deflection_accepted(self):
        self.assertEqual(categorize_quantity("static_deflection"), "static_deflection")

    def test_stress_accepted(self):
        self.assertEqual(categorize_quantity("stress"), "stress")

    def test_damping_accepted(self):
        self.assertEqual(categorize_quantity("damping"), "damping")

    def test_unrecognized_quantity_raises(self):
        with self.assertRaises(ValueError):
            categorize_quantity("acceleration")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            categorize_quantity("")


class TestComputeRelativeDelta(unittest.TestCase):

    def test_exact_match_gives_zero(self):
        self.assertAlmostEqual(compute_relative_delta(100.0, 100.0), 0.0)

    def test_ten_percent_over(self):
        self.assertAlmostEqual(compute_relative_delta(110.0, 100.0), 0.10)

    def test_ten_percent_under(self):
        self.assertAlmostEqual(compute_relative_delta(90.0, 100.0), 0.10)

    def test_fifty_percent_miss(self):
        self.assertAlmostEqual(compute_relative_delta(50.0, 100.0), 0.50)

    def test_zero_measured_raises(self):
        with self.assertRaises(ValueError):
            compute_relative_delta(5.0, 0.0)

    def test_zero_predicted_is_valid(self):
        # 0 predicted vs 100 measured = 100% relative delta
        self.assertAlmostEqual(compute_relative_delta(0.0, 100.0), 1.0)

    def test_negative_measured_uses_absolute(self):
        # |5 - (-100)| / |-100| = 105/100 = 1.05
        self.assertAlmostEqual(compute_relative_delta(5.0, -100.0), 1.05)


class TestCheckFrequencyCorrelation(unittest.TestCase):

    def test_pass_within_default_threshold(self):
        # 102 Hz predicted vs 100 Hz measured -> delta = 0.02 < 0.05
        result = check_frequency_correlation(102.0, 100.0)
        self.assertEqual(result["status"], "pass")
        self.assertAlmostEqual(result["delta"], 0.02)

    def test_fail_outside_default_threshold(self):
        # 108 Hz predicted vs 100 Hz measured -> delta = 0.08 > 0.05
        result = check_frequency_correlation(108.0, 100.0)
        self.assertEqual(result["status"], "fail")

    def test_exactly_at_threshold_passes(self):
        # delta = exactly 0.05 -> should pass (delta <= threshold)
        result = check_frequency_correlation(105.0, 100.0)
        self.assertEqual(result["status"], "pass")
        self.assertAlmostEqual(result["delta"], 0.05)

    def test_custom_threshold_applied(self):
        # 103 Hz vs 100 Hz, threshold 0.02 -> should fail
        result = check_frequency_correlation(103.0, 100.0, threshold=0.02)
        self.assertEqual(result["status"], "fail")

    def test_zero_predicted_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_correlation(0.0, 100.0)

    def test_negative_measured_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_correlation(100.0, -10.0)

    def test_result_contains_expected_keys(self):
        result = check_frequency_correlation(50.0, 50.0)
        for key in ("predicted", "measured", "delta", "threshold", "status"):
            self.assertIn(key, result)

    def test_default_threshold_matches_constant(self):
        result = check_frequency_correlation(100.0, 100.0)
        self.assertAlmostEqual(result["threshold"], DEFAULT_FREQUENCY_THRESHOLD)


class TestCheckMacCorrelation(unittest.TestCase):

    def test_pass_above_default_threshold(self):
        result = check_mac_correlation(0.95)
        self.assertEqual(result["status"], "pass")

    def test_fail_below_default_threshold(self):
        result = check_mac_correlation(0.80)
        self.assertEqual(result["status"], "fail")

    def test_exactly_at_threshold_passes(self):
        result = check_mac_correlation(DEFAULT_MAC_THRESHOLD)
        self.assertEqual(result["status"], "pass")

    def test_perfect_mac_passes(self):
        result = check_mac_correlation(1.0)
        self.assertEqual(result["status"], "pass")

    def test_zero_mac_fails(self):
        result = check_mac_correlation(0.0)
        self.assertEqual(result["status"], "fail")

    def test_mac_above_one_raises(self):
        with self.assertRaises(ValueError):
            check_mac_correlation(1.01)

    def test_negative_mac_raises(self):
        with self.assertRaises(ValueError):
            check_mac_correlation(-0.1)

    def test_custom_threshold_applied(self):
        # MAC 0.85 with threshold 0.80 should pass
        result = check_mac_correlation(0.85, threshold=0.80)
        self.assertEqual(result["status"], "pass")

    def test_result_contains_expected_keys(self):
        result = check_mac_correlation(0.92)
        for key in ("mac_value", "threshold", "status"):
            self.assertIn(key, result)


class TestAssessQuantityCorrelation(unittest.TestCase):

    def test_frequency_pass(self):
        result = assess_quantity_correlation("frequency", 102.0, 100.0)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["quantity_type"], "frequency")
        self.assertIsNone(result["mac_value"])

    def test_frequency_fail(self):
        result = assess_quantity_correlation("frequency", 115.0, 100.0)
        self.assertEqual(result["status"], "fail")

    def test_mode_shape_pass(self):
        # For mode_shape, predicted is the MAC value; measured is ignored
        result = assess_quantity_correlation("mode_shape", 0.95, 0.0)
        self.assertEqual(result["status"], "pass")
        self.assertIsNone(result["delta"])
        self.assertAlmostEqual(result["mac_value"], 0.95)

    def test_mode_shape_fail(self):
        result = assess_quantity_correlation("mode_shape", 0.75, 0.0)
        self.assertEqual(result["status"], "fail")

    def test_static_deflection_pass(self):
        # 5% delta < 10% default threshold
        result = assess_quantity_correlation("static_deflection", 1.05, 1.0)
        self.assertEqual(result["status"], "pass")

    def test_static_deflection_fail(self):
        # 15% delta > 10% default threshold
        result = assess_quantity_correlation("static_deflection", 1.15, 1.0)
        self.assertEqual(result["status"], "fail")

    def test_damping_uses_larger_threshold(self):
        # 15% delta: within damping default (20%) but would fail frequency (5%)
        result = assess_quantity_correlation("damping", 1.15, 1.0)
        self.assertEqual(result["status"], "pass")
        self.assertAlmostEqual(result["threshold"], DEFAULT_DAMPING_THRESHOLD)

    def test_stress_fail(self):
        # 12% delta > 10% stress threshold
        result = assess_quantity_correlation("stress", 1.12, 1.0)
        self.assertEqual(result["status"], "fail")

    def test_unrecognized_quantity_raises(self):
        with self.assertRaises(ValueError):
            assess_quantity_correlation("displacement", 1.0, 1.0)

    def test_custom_threshold_overrides_default(self):
        # Frequency 3% delta, custom threshold 0.02 -> fail
        result = assess_quantity_correlation("frequency", 103.0, 100.0, threshold=0.02)
        self.assertEqual(result["status"], "fail")

    def test_result_contains_all_keys(self):
        result = assess_quantity_correlation("stress", 100.0, 100.0)
        for key in ("quantity_type", "delta", "mac_value", "threshold", "status"):
            self.assertIn(key, result)


class TestCheckDRDCompleteness(unittest.TestCase):

    def test_all_sections_present(self):
        missing = check_drd_completeness(list(REQUIRED_DRD_SECTIONS))
        self.assertEqual(missing, [])

    def test_detects_missing_conclusions(self):
        partial = [s for s in REQUIRED_DRD_SECTIONS if s != "conclusions"]
        missing = check_drd_completeness(partial)
        self.assertIn("conclusions", missing)

    def test_detects_missing_correlation_assessment(self):
        partial = [s for s in REQUIRED_DRD_SECTIONS if s != "correlation_assessment"]
        missing = check_drd_completeness(partial)
        self.assertIn("correlation_assessment", missing)

    def test_detects_missing_model_update_justification(self):
        partial = [s for s in REQUIRED_DRD_SECTIONS if s != "model_update_justification"]
        missing = check_drd_completeness(partial)
        self.assertIn("model_update_justification", missing)

    def test_empty_list_flags_all(self):
        missing = check_drd_completeness([])
        self.assertEqual(len(missing), len(REQUIRED_DRD_SECTIONS))

    def test_extra_sections_ignored(self):
        sections = list(REQUIRED_DRD_SECTIONS) + ["appendix_a", "test_matrix"]
        missing = check_drd_completeness(sections)
        self.assertEqual(missing, [])

    def test_detects_missing_pre_test_predictions(self):
        partial = [s for s in REQUIRED_DRD_SECTIONS if s != "pre_test_predictions"]
        missing = check_drd_completeness(partial)
        self.assertIn("pre_test_predictions", missing)


class TestBuildCorrelationSummary(unittest.TestCase):

    def test_all_passing_produces_empty_failing(self):
        results = [
            assess_quantity_correlation("frequency", 101.0, 100.0),
            assess_quantity_correlation("stress", 105.0, 100.0),
        ]
        summary, failing = build_correlation_summary(results)
        self.assertEqual(failing, [])

    def test_failing_entry_in_failing_list(self):
        results = [
            assess_quantity_correlation("frequency", 101.0, 100.0),   # pass
            assess_quantity_correlation("frequency", 120.0, 100.0),   # fail
        ]
        summary, failing = build_correlation_summary(results)
        self.assertIn(1, failing)
        self.assertNotIn(0, failing)

    def test_summary_keys_include_quantity_type(self):
        results = [assess_quantity_correlation("damping", 1.0, 1.0)]
        summary, _ = build_correlation_summary(results)
        self.assertIn("damping_0", summary)

    def test_empty_results_returns_empty(self):
        summary, failing = build_correlation_summary([])
        self.assertEqual(summary, {})
        self.assertEqual(failing, [])

    def test_multiple_failing_entries(self):
        results = [
            assess_quantity_correlation("frequency", 120.0, 100.0),  # fail
            assess_quantity_correlation("stress", 125.0, 100.0),     # fail
        ]
        _, failing = build_correlation_summary(results)
        self.assertEqual(set(failing), {0, 1})


class TestDetermineModelUpdateRequired(unittest.TestCase):

    def test_no_failing_entries_returns_false(self):
        self.assertFalse(determine_model_update_required([]))

    def test_one_failing_entry_returns_true(self):
        self.assertTrue(determine_model_update_required([0]))

    def test_multiple_failing_entries_returns_true(self):
        self.assertTrue(determine_model_update_required([0, 2, 5]))

    def test_end_to_end_no_update_required(self):
        results = [
            assess_quantity_correlation("frequency", 101.0, 100.0),
            assess_quantity_correlation("mode_shape", 0.95, 0.0),
        ]
        _, failing = build_correlation_summary(results)
        self.assertFalse(determine_model_update_required(failing))

    def test_end_to_end_update_required(self):
        results = [
            assess_quantity_correlation("frequency", 101.0, 100.0),
            assess_quantity_correlation("frequency", 115.0, 100.0),  # fail
        ]
        _, failing = build_correlation_summary(results)
        self.assertTrue(determine_model_update_required(failing))


class TestConstantsIntegrity(unittest.TestCase):

    def test_default_frequency_threshold_is_five_percent(self):
        self.assertAlmostEqual(DEFAULT_FREQUENCY_THRESHOLD, 0.05)

    def test_default_mac_threshold_is_ninety_percent(self):
        self.assertAlmostEqual(DEFAULT_MAC_THRESHOLD, 0.90)

    def test_default_damping_threshold_is_twenty_percent(self):
        self.assertAlmostEqual(DEFAULT_DAMPING_THRESHOLD, 0.20)

    def test_default_deflection_threshold_is_ten_percent(self):
        self.assertAlmostEqual(DEFAULT_DEFLECTION_THRESHOLD, 0.10)

    def test_default_stress_threshold_is_ten_percent(self):
        self.assertAlmostEqual(DEFAULT_STRESS_THRESHOLD, 0.10)

    def test_required_sections_non_empty(self):
        self.assertGreater(len(REQUIRED_DRD_SECTIONS), 0)

    def test_valid_quantity_types_contains_five(self):
        self.assertEqual(len(VALID_QUANTITY_TYPES), 5)

    def test_required_sections_contains_model_update_justification(self):
        self.assertIn("model_update_justification", REQUIRED_DRD_SECTIONS)

    def test_required_sections_contains_correlation_assessment(self):
        self.assertIn("correlation_assessment", REQUIRED_DRD_SECTIONS)


if __name__ == "__main__":
    unittest.main()
