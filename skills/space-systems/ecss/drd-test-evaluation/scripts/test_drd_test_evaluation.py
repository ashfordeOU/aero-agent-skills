"""
Gate 3 contract tests for drd_test_evaluation_logic.
stdlib unittest only — offline, deterministic. Run:
    python3 test_drd_test_evaluation.py
Expected output: OK
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from drd_test_evaluation_logic import (
    evaluate_test_objective,
    assess_result_vs_prediction,
    evaluate_anomaly,
    assess_article_condition,
    determine_overall_evaluation,
    OBJECTIVE_STATUSES,
    ANOMALY_DISPOSITIONS,
    ARTICLE_CONDITIONS,
)


class TestEvaluateTestObjective(unittest.TestCase):

    def test_objective_met_returns_true(self):
        result = evaluate_test_objective("OBJ-01", "met")
        self.assertTrue(result["met"])
        self.assertEqual(result["status"], "met")
        self.assertEqual(result["objective_id"], "OBJ-01")

    def test_objective_not_met_returns_false(self):
        result = evaluate_test_objective("OBJ-02", "not_met")
        self.assertFalse(result["met"])
        self.assertEqual(result["status"], "not_met")

    def test_objective_partial_returns_false(self):
        result = evaluate_test_objective("OBJ-03", "partial")
        self.assertFalse(result["met"])
        self.assertEqual(result["status"], "partial")

    def test_invalid_objective_status_raises(self):
        with self.assertRaises(ValueError):
            evaluate_test_objective("OBJ-04", "pending")

    def test_empty_objective_id_raises(self):
        with self.assertRaises(ValueError):
            evaluate_test_objective("", "met")

    def test_all_valid_statuses_accepted(self):
        for status in OBJECTIVE_STATUSES:
            result = evaluate_test_objective(f"OBJ-{status}", status)
            self.assertEqual(result["status"], status)


class TestAssessResultVsPrediction(unittest.TestCase):

    def test_exact_match_within_prediction(self):
        result = assess_result_vs_prediction("freq_Hz", 100.0, 100.0, 0.05)
        self.assertEqual(result["assessment"], "within_prediction")
        self.assertAlmostEqual(result["relative_error"], 0.0)

    def test_outside_tolerance_outside_prediction(self):
        result = assess_result_vs_prediction("freq_Hz", 110.0, 100.0, 0.05)
        self.assertEqual(result["assessment"], "outside_prediction")

    def test_boundary_value_within_tolerance(self):
        result = assess_result_vs_prediction("stress_MPa", 105.0, 100.0, 0.05)
        self.assertEqual(result["assessment"], "within_prediction")
        self.assertAlmostEqual(result["relative_error"], 0.05)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            assess_result_vs_prediction("param", 1.0, 1.0, -0.01)

    def test_zero_predicted_zero_measured_within(self):
        result = assess_result_vs_prediction("disp_mm", 0.0, 0.0, 0.05)
        self.assertEqual(result["assessment"], "within_prediction")

    def test_zero_predicted_nonzero_measured_outside(self):
        result = assess_result_vs_prediction("disp_mm", 0.5, 0.0, 0.05)
        self.assertEqual(result["assessment"], "outside_prediction")
        self.assertEqual(result["relative_error"], float("inf"))

    def test_non_numeric_measured_raises(self):
        with self.assertRaises(ValueError):
            assess_result_vs_prediction("param", "high", 1.0, 0.05)

    def test_relative_error_calculation(self):
        result = assess_result_vs_prediction("accel_g", 9.5, 10.0, 0.10)
        self.assertAlmostEqual(result["relative_error"], 0.05)
        self.assertEqual(result["assessment"], "within_prediction")


class TestEvaluateAnomaly(unittest.TestCase):

    def test_resolved_anomaly_not_blocking(self):
        result = evaluate_anomaly("ANO-001", "resolved")
        self.assertFalse(result["blocking"])
        self.assertEqual(result["disposition"], "resolved")

    def test_open_anomaly_is_blocking(self):
        result = evaluate_anomaly("ANO-002", "open")
        self.assertTrue(result["blocking"])

    def test_waived_anomaly_not_blocking(self):
        result = evaluate_anomaly("ANO-003", "waived")
        self.assertFalse(result["blocking"])

    def test_invalid_disposition_raises(self):
        with self.assertRaises(ValueError):
            evaluate_anomaly("ANO-004", "deferred")

    def test_empty_anomaly_id_raises(self):
        with self.assertRaises(ValueError):
            evaluate_anomaly("", "resolved")

    def test_all_valid_dispositions_accepted(self):
        for disp in ANOMALY_DISPOSITIONS:
            result = evaluate_anomaly(f"ANO-{disp}", disp)
            self.assertEqual(result["disposition"], disp)


class TestAssessArticleCondition(unittest.TestCase):

    def test_acceptable_condition_is_acceptable(self):
        result = assess_article_condition("ART-01", "acceptable")
        self.assertTrue(result["acceptable"])

    def test_not_acceptable_condition_is_not_acceptable(self):
        result = assess_article_condition("ART-02", "not_acceptable")
        self.assertFalse(result["acceptable"])

    def test_conditional_condition_is_acceptable(self):
        result = assess_article_condition("ART-03", "conditional")
        self.assertTrue(result["acceptable"])

    def test_invalid_condition_raises(self):
        with self.assertRaises(ValueError):
            assess_article_condition("ART-04", "damaged")

    def test_empty_article_id_raises(self):
        with self.assertRaises(ValueError):
            assess_article_condition("", "acceptable")

    def test_all_valid_conditions_accepted(self):
        for cond in ARTICLE_CONDITIONS:
            result = assess_article_condition(f"ART-{cond}", cond)
            self.assertEqual(result["condition"], cond)


class TestDetermineOverallEvaluation(unittest.TestCase):

    def test_all_pass_yields_accepted(self):
        objectives = [evaluate_test_objective("OBJ-01", "met")]
        assessments = [assess_result_vs_prediction("freq", 100.0, 100.0, 0.05)]
        anomalies = [evaluate_anomaly("ANO-01", "resolved")]
        articles = [assess_article_condition("ART-01", "acceptable")]
        result = determine_overall_evaluation(objectives, assessments, anomalies, articles)
        self.assertEqual(result["overall_status"], "accepted")
        self.assertEqual(len(result["findings"]), 0)

    def test_open_anomaly_yields_rejected(self):
        objectives = [evaluate_test_objective("OBJ-01", "met")]
        assessments = [assess_result_vs_prediction("freq", 100.0, 100.0, 0.05)]
        anomalies = [evaluate_anomaly("ANO-01", "open")]
        articles = [assess_article_condition("ART-01", "acceptable")]
        result = determine_overall_evaluation(objectives, assessments, anomalies, articles)
        self.assertEqual(result["overall_status"], "rejected")
        self.assertEqual(result["open_anomalies_count"], 1)

    def test_objective_not_met_yields_rejected(self):
        objectives = [evaluate_test_objective("OBJ-01", "not_met")]
        result = determine_overall_evaluation(objectives, [], [], [])
        self.assertEqual(result["overall_status"], "rejected")
        self.assertIn("Objectives not met", result["findings"][0])

    def test_result_outside_prediction_yields_rejected(self):
        objectives = [evaluate_test_objective("OBJ-01", "met")]
        assessments = [assess_result_vs_prediction("freq", 120.0, 100.0, 0.05)]
        result = determine_overall_evaluation(objectives, assessments, [], [])
        self.assertEqual(result["overall_status"], "rejected")
        self.assertEqual(result["results_outside_prediction_count"], 1)

    def test_not_acceptable_article_yields_rejected(self):
        objectives = [evaluate_test_objective("OBJ-01", "met")]
        articles = [assess_article_condition("ART-01", "not_acceptable")]
        result = determine_overall_evaluation(objectives, [], [], articles)
        self.assertEqual(result["overall_status"], "rejected")
        self.assertEqual(result["articles_not_acceptable_count"], 1)

    def test_conditional_article_does_not_block(self):
        objectives = [evaluate_test_objective("OBJ-01", "met")]
        articles = [assess_article_condition("ART-01", "conditional")]
        result = determine_overall_evaluation(objectives, [], [], articles)
        self.assertEqual(result["overall_status"], "accepted")

    def test_counts_correct_with_mixed_inputs(self):
        objectives = [
            evaluate_test_objective("OBJ-01", "met"),
            evaluate_test_objective("OBJ-02", "not_met"),
        ]
        assessments = [
            assess_result_vs_prediction("f1", 100.0, 100.0, 0.05),
            assess_result_vs_prediction("f2", 120.0, 100.0, 0.05),
        ]
        anomalies = [
            evaluate_anomaly("ANO-01", "resolved"),
            evaluate_anomaly("ANO-02", "open"),
        ]
        articles = [
            assess_article_condition("ART-01", "acceptable"),
        ]
        result = determine_overall_evaluation(objectives, assessments, anomalies, articles)
        self.assertEqual(result["objectives_count"], 2)
        self.assertEqual(result["objectives_met_count"], 1)
        self.assertEqual(result["results_count"], 2)
        self.assertEqual(result["results_within_prediction_count"], 1)
        self.assertEqual(result["results_outside_prediction_count"], 1)
        self.assertEqual(result["anomalies_count"], 2)
        self.assertEqual(result["open_anomalies_count"], 1)
        self.assertEqual(result["overall_status"], "rejected")

    def test_empty_inputs_yield_accepted(self):
        result = determine_overall_evaluation([], [], [], [])
        self.assertEqual(result["overall_status"], "accepted")
        self.assertEqual(result["objectives_count"], 0)
        self.assertEqual(result["findings"], [])

    def test_multiple_findings_all_recorded(self):
        objectives = [evaluate_test_objective("OBJ-01", "not_met")]
        anomalies = [evaluate_anomaly("ANO-01", "open")]
        articles = [assess_article_condition("ART-01", "not_acceptable")]
        result = determine_overall_evaluation(objectives, [], anomalies, articles)
        self.assertEqual(result["overall_status"], "rejected")
        self.assertEqual(len(result["findings"]), 3)

    def test_waived_anomaly_does_not_block(self):
        objectives = [evaluate_test_objective("OBJ-01", "met")]
        anomalies = [evaluate_anomaly("ANO-01", "waived")]
        result = determine_overall_evaluation(objectives, [], anomalies, [])
        self.assertEqual(result["overall_status"], "accepted")
        self.assertEqual(result["open_anomalies_count"], 0)


if __name__ == "__main__":
    unittest.main()
