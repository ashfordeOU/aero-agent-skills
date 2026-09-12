"""
Gate 3 contract tests for microvibration_test_logic.py.
Stdlib unittest only; deterministic; offline.

Run: python3 test_microvibration_test.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from microvibration_test_logic import (
    VALID_SOURCE_TYPES,
    VALID_MEASUREMENT_TYPES,
    categorize_source,
    check_frequency_coverage,
    compute_disturbance_margin,
    evaluate_source,
    run_microvibration_test_assessment,
)


class TestCategorizeSource(unittest.TestCase):
    def test_tonal_returns_tonal(self):
        self.assertEqual(categorize_source("tonal"), "tonal")

    def test_broadband_returns_broadband(self):
        self.assertEqual(categorize_source("broadband"), "broadband")

    def test_transient_returns_transient(self):
        self.assertEqual(categorize_source("transient"), "transient")

    def test_uppercase_input_normalized_to_lowercase(self):
        self.assertEqual(categorize_source("TONAL"), "tonal")

    def test_mixed_case_broadband_normalized(self):
        self.assertEqual(categorize_source("BroadBand"), "broadband")

    def test_unrecognized_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_source("harmonic")

    def test_empty_string_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_source("")

    def test_valid_types_set_matches_expected(self):
        self.assertEqual(VALID_SOURCE_TYPES, {"tonal", "broadband", "transient"})


class TestCheckFrequencyCoverage(unittest.TestCase):
    def test_measured_wider_than_required_passes(self):
        result = check_frequency_coverage(0.5, 600.0, 1.0, 500.0)
        self.assertTrue(result["covered"])
        self.assertEqual(result["gaps"], [])

    def test_exact_match_passes(self):
        result = check_frequency_coverage(1.0, 500.0, 1.0, 500.0)
        self.assertTrue(result["covered"])
        self.assertEqual(result["gaps"], [])

    def test_lower_bound_not_covered_fails(self):
        result = check_frequency_coverage(5.0, 500.0, 1.0, 500.0)
        self.assertFalse(result["covered"])
        self.assertTrue(any("lower bound" in g for g in result["gaps"]))

    def test_upper_bound_not_covered_fails(self):
        result = check_frequency_coverage(1.0, 400.0, 1.0, 500.0)
        self.assertFalse(result["covered"])
        self.assertTrue(any("upper bound" in g for g in result["gaps"]))

    def test_both_bounds_uncovered_produces_two_gap_entries(self):
        result = check_frequency_coverage(5.0, 400.0, 1.0, 500.0)
        self.assertFalse(result["covered"])
        self.assertEqual(len(result["gaps"]), 2)

    def test_degenerate_measured_range_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_coverage(500.0, 1.0, 1.0, 500.0)

    def test_degenerate_required_range_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_coverage(1.0, 500.0, 500.0, 1.0)

    def test_equal_measured_bounds_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_coverage(100.0, 100.0, 1.0, 500.0)


class TestComputeDisturbanceMargin(unittest.TestCase):
    def test_measured_below_budget_gives_positive_margin(self):
        margin = compute_disturbance_margin(0.5, 1.0)
        self.assertAlmostEqual(margin, 0.5)

    def test_measured_above_budget_gives_negative_margin(self):
        margin = compute_disturbance_margin(1.5, 1.0)
        self.assertAlmostEqual(margin, -0.5)

    def test_measured_equal_to_budget_gives_zero_margin(self):
        margin = compute_disturbance_margin(1.0, 1.0)
        self.assertEqual(margin, 0.0)

    def test_zero_measured_amplitude_is_valid(self):
        margin = compute_disturbance_margin(0.0, 1.0)
        self.assertAlmostEqual(margin, 1.0)

    def test_negative_measured_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_disturbance_margin(-0.1, 1.0)

    def test_negative_budget_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_disturbance_margin(0.5, -1.0)


class TestEvaluateSource(unittest.TestCase):
    def _source(self, **overrides):
        base = {
            "name": "RW1",
            "type": "tonal",
            "amplitude": 0.5,
            "freq_low_hz": 1.0,
            "freq_high_hz": 500.0,
            "measurement_type": "force-platform",
        }
        base.update(overrides)
        return base

    def test_compliant_source_passes(self):
        result = evaluate_source(self._source(), {"amplitude": 1.0}, (1.0, 500.0))
        self.assertTrue(result["passed"])
        self.assertEqual(result["findings"], [])

    def test_amplitude_exceedance_fails(self):
        result = evaluate_source(
            self._source(amplitude=1.5), {"amplitude": 1.0}, (1.0, 500.0)
        )
        self.assertFalse(result["passed"])
        self.assertTrue(len(result["findings"]) > 0)

    def test_frequency_gap_at_lower_bound_fails(self):
        result = evaluate_source(
            self._source(freq_low_hz=5.0), {"amplitude": 1.0}, (1.0, 500.0)
        )
        self.assertFalse(result["passed"])

    def test_zero_margin_is_compliant(self):
        result = evaluate_source(
            self._source(amplitude=1.0), {"amplitude": 1.0}, (1.0, 500.0)
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["margin"], 0.0)

    def test_missing_budget_amplitude_raises(self):
        with self.assertRaises(ValueError):
            evaluate_source(self._source(), {}, (1.0, 500.0))

    def test_unrecognized_source_type_raises(self):
        with self.assertRaises(ValueError):
            evaluate_source(
                self._source(type="harmonic"), {"amplitude": 1.0}, (1.0, 500.0)
            )

    def test_unrecognized_measurement_type_raises(self):
        with self.assertRaises(ValueError):
            evaluate_source(
                self._source(measurement_type="gyroscope"),
                {"amplitude": 1.0},
                (1.0, 500.0),
            )

    def test_result_reports_correct_source_type(self):
        result = evaluate_source(self._source(type="broadband"), {"amplitude": 1.0}, (1.0, 500.0))
        self.assertEqual(result["type"], "broadband")

    def test_result_reports_correct_measurement_type(self):
        result = evaluate_source(
            self._source(measurement_type="load-cell"), {"amplitude": 1.0}, (1.0, 500.0)
        )
        self.assertEqual(result["measurement_type"], "load-cell")

    def test_transient_source_passes_within_budget(self):
        result = evaluate_source(
            self._source(type="transient", amplitude=0.2),
            {"amplitude": 0.5},
            (1.0, 500.0),
        )
        self.assertTrue(result["passed"])

    def test_frequency_gap_recorded_in_findings(self):
        result = evaluate_source(
            self._source(freq_high_hz=400.0), {"amplitude": 1.0}, (1.0, 500.0)
        )
        self.assertFalse(result["frequency_covered"])
        self.assertTrue(any("upper bound" in f for f in result["findings"]))


class TestRunMicrovibrationTestAssessment(unittest.TestCase):
    def _source(self, name="RW1", amplitude=0.5, freq_low=1.0, freq_high=500.0):
        return {
            "name": name,
            "type": "tonal",
            "amplitude": amplitude,
            "freq_low_hz": freq_low,
            "freq_high_hz": freq_high,
            "measurement_type": "force-platform",
        }

    def test_single_passing_source_overall_passes(self):
        sources = [self._source()]
        budgets = {"RW1": {"amplitude": 1.0}}
        result = run_microvibration_test_assessment(sources, budgets, (1.0, 500.0))
        self.assertTrue(result["overall_passed"])
        self.assertEqual(result["source_count"], 1)
        self.assertEqual(result["failing_sources"], [])

    def test_single_failing_source_overall_fails(self):
        sources = [self._source(amplitude=1.5)]
        budgets = {"RW1": {"amplitude": 1.0}}
        result = run_microvibration_test_assessment(sources, budgets, (1.0, 500.0))
        self.assertFalse(result["overall_passed"])
        self.assertIn("RW1", result["failing_sources"])

    def test_multiple_sources_all_pass(self):
        sources = [self._source("RW1", 0.3), self._source("CMG1", 0.4)]
        budgets = {"RW1": {"amplitude": 1.0}, "CMG1": {"amplitude": 1.0}}
        result = run_microvibration_test_assessment(sources, budgets, (1.0, 500.0))
        self.assertTrue(result["overall_passed"])
        self.assertEqual(result["source_count"], 2)

    def test_mixed_pass_and_fail_identifies_failing_source(self):
        sources = [self._source("RW1", 0.5), self._source("CMG1", 1.5)]
        budgets = {"RW1": {"amplitude": 1.0}, "CMG1": {"amplitude": 1.0}}
        result = run_microvibration_test_assessment(sources, budgets, (1.0, 500.0))
        self.assertFalse(result["overall_passed"])
        self.assertIn("CMG1", result["failing_sources"])
        self.assertNotIn("RW1", result["failing_sources"])

    def test_empty_sources_raises_value_error(self):
        with self.assertRaises(ValueError):
            run_microvibration_test_assessment([], {}, (1.0, 500.0))

    def test_missing_budget_for_source_raises(self):
        sources = [self._source()]
        with self.assertRaises(ValueError):
            run_microvibration_test_assessment(sources, {}, (1.0, 500.0))

    def test_result_contains_per_source_results_list(self):
        sources = [self._source()]
        budgets = {"RW1": {"amplitude": 1.0}}
        result = run_microvibration_test_assessment(sources, budgets, (1.0, 500.0))
        self.assertIsInstance(result["results"], list)
        self.assertEqual(len(result["results"]), 1)

    def test_frequency_gap_causes_overall_failure(self):
        sources = [self._source(freq_low=5.0)]
        budgets = {"RW1": {"amplitude": 1.0}}
        result = run_microvibration_test_assessment(sources, budgets, (1.0, 500.0))
        self.assertFalse(result["overall_passed"])


if __name__ == "__main__":
    unittest.main()
