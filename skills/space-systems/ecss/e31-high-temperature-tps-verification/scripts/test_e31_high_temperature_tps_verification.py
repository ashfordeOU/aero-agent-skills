"""Contract tests for the clause 4.5.2.3 high-temperature protection logic."""

import unittest

from e31_high_temperature_tps_verification_logic import (
    METHODS,
    TEMPERATURE_TOLERANCE_K,
    assess_tps_verification,
    bondline_margin_k,
    capability_adequate,
    capability_margin_k,
    correlation_acceptable,
    correlation_error_k,
    evaluate_tps_item,
    method_coverage_findings,
    qualification_temperature_k,
    recession_allowance_mm,
    required_thickness_mm,
    thickness_margin_mm,
    validate_method_set,
    validate_non_negative,
    validate_temperature_k,
)


def _item(**overrides):
    item = {
        "id": "TPS-NOSE",
        "predicted_peak_k": 1500.0,
        "qualification_margin_k": 100.0,
        "capability_k": 1800.0,
        "bondline_limit_k": 450.0,
        "bondline_predicted_k": 400.0,
        "recession_rate_mm_per_s": 0.01,
        "exposure_s": 120.0,
        "scatter_factor": 1.5,
        "insulation_mm": 8.0,
        "manufacturing_tolerance_mm": 0.5,
        "as_built_mm": 12.0,
        "agreed_methods": ["thermal-test", "correlated-analysis"],
        "performed_methods": ["thermal-test", "correlated-analysis"],
        "measured_peak_k": 1520.0,
        "correlation_tolerance_k": 40.0,
    }
    item.update(overrides)
    return item


class ValidationTests(unittest.TestCase):
    def test_kelvin_returned_as_float(self):
        self.assertAlmostEqual(validate_temperature_k(1500, "peak"), 1500.0)

    def test_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_k(0.0, "peak")

    def test_boolean_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_k(True, "peak")

    def test_non_finite_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_k(float("inf"), "peak")

    def test_zero_is_a_valid_non_negative(self):
        self.assertAlmostEqual(validate_non_negative(0.0, "margin"), 0.0)

    def test_negative_non_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_non_negative(-1.0, "margin")

    def test_method_set_is_normalised_and_deduplicated(self):
        self.assertEqual(
            validate_method_set(["Thermal-Test", "thermal-test"]), {"thermal-test"}
        )

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_set(["arc-jet-by-eye"])

    def test_empty_method_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_method_set([])

    def test_method_vocabulary_has_three_entries(self):
        self.assertEqual(len(METHODS), 3)


class QualificationTemperatureTests(unittest.TestCase):
    def test_margin_is_added_to_the_prediction(self):
        self.assertAlmostEqual(qualification_temperature_k(1500.0, 100.0), 1600.0, places=9)

    def test_zero_margin_allowed(self):
        self.assertAlmostEqual(qualification_temperature_k(1500.0, 0.0), 1500.0, places=9)

    def test_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            qualification_temperature_k(1500.0, -50.0)

    def test_capability_margin_is_over_the_qualification_point(self):
        self.assertAlmostEqual(capability_margin_k(1800.0, 1600.0), 200.0, places=9)

    def test_capability_exactly_at_qualification_is_adequate(self):
        self.assertTrue(capability_adequate(capability_margin_k(1600.0, 1600.0)))

    def test_capability_below_qualification_is_inadequate(self):
        self.assertFalse(capability_adequate(capability_margin_k(1550.0, 1600.0)))

    def test_capability_margin_needs_a_real_number(self):
        with self.assertRaises(ValueError):
            capability_adequate("200")


class ThicknessTests(unittest.TestCase):
    def test_recession_is_rate_times_exposure_times_scatter(self):
        self.assertAlmostEqual(recession_allowance_mm(0.01, 120.0, 1.5), 1.8, places=9)

    def test_zero_rate_gives_no_recession(self):
        self.assertAlmostEqual(recession_allowance_mm(0.0, 120.0, 1.5), 0.0, places=9)

    def test_scatter_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            recession_allowance_mm(0.01, 120.0, 0.9)

    def test_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            recession_allowance_mm(0.01, -1.0, 1.5)

    def test_required_thickness_sums_the_three_contributions(self):
        self.assertAlmostEqual(required_thickness_mm(1.8, 8.0, 0.5), 10.3, places=9)

    def test_zero_insulation_rejected(self):
        with self.assertRaises(ValueError):
            required_thickness_mm(1.8, 0.0, 0.5)

    def test_thickness_margin_is_as_built_minus_required(self):
        self.assertAlmostEqual(thickness_margin_mm(12.0, 10.3), 1.7, places=9)

    def test_thin_part_gives_a_negative_thickness_margin(self):
        self.assertAlmostEqual(thickness_margin_mm(9.0, 10.3), -1.3, places=9)

    def test_zero_required_thickness_rejected(self):
        with self.assertRaises(ValueError):
            thickness_margin_mm(12.0, 0.0)


class BondlineAndCorrelationTests(unittest.TestCase):
    def test_bondline_margin_is_limit_minus_predicted(self):
        self.assertAlmostEqual(bondline_margin_k(450.0, 400.0), 50.0, places=9)

    def test_bondline_overshoot_is_negative(self):
        self.assertAlmostEqual(bondline_margin_k(450.0, 470.0), -20.0, places=9)

    def test_correlation_error_is_absolute(self):
        self.assertAlmostEqual(correlation_error_k(1500.0, 1520.0), 20.0, places=9)
        self.assertAlmostEqual(correlation_error_k(1520.0, 1500.0), 20.0, places=9)

    def test_error_inside_tolerance_is_acceptable(self):
        self.assertTrue(correlation_acceptable(20.0, 40.0))

    def test_error_exactly_on_tolerance_is_acceptable(self):
        self.assertTrue(correlation_acceptable(40.0, 40.0))

    def test_error_above_tolerance_is_not_acceptable(self):
        self.assertFalse(correlation_acceptable(55.0, 40.0))

    def test_zero_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            correlation_acceptable(10.0, 0.0)


class MethodCoverageTests(unittest.TestCase):
    def test_matching_plan_raises_nothing(self):
        self.assertEqual(
            method_coverage_findings(["thermal-test"], ["thermal-test"], "TPS-1"), []
        )

    def test_missing_agreed_test_is_a_finding(self):
        findings = method_coverage_findings(
            ["thermal-test", "thermal-analysis"], ["thermal-analysis"], "TPS-1"
        )
        self.assertEqual(len(findings), 1)

    def test_correlated_analysis_without_a_test_is_a_finding(self):
        findings = method_coverage_findings(
            ["correlated-analysis"], ["correlated-analysis"], "TPS-1"
        )
        self.assertEqual(len(findings), 1)

    def test_extra_method_beyond_the_plan_is_not_a_finding(self):
        self.assertEqual(
            method_coverage_findings(
                ["thermal-analysis"], ["thermal-analysis", "thermal-test"], "TPS-1"
            ),
            [],
        )


class ItemEvaluationTests(unittest.TestCase):
    def test_nominal_item_verifies(self):
        record = evaluate_tps_item(_item())
        self.assertTrue(record["verified"])
        self.assertAlmostEqual(record["qualification_temperature_k"], 1600.0, places=9)
        self.assertAlmostEqual(record["required_thickness_mm"], 10.3, places=9)

    def test_capability_shortfall_fails_the_item(self):
        record = evaluate_tps_item(_item(capability_k=1550.0))
        self.assertFalse(record["verified"])
        self.assertFalse(record["capability_adequate"])

    def test_thin_as_built_fails_the_item(self):
        record = evaluate_tps_item(_item(as_built_mm=9.0))
        self.assertFalse(record["thickness_adequate"])

    def test_bondline_breach_fails_the_item(self):
        record = evaluate_tps_item(_item(bondline_predicted_k=480.0))
        self.assertFalse(record["bondline_adequate"])

    def test_poor_correlation_fails_the_item(self):
        record = evaluate_tps_item(_item(measured_peak_k=1600.0))
        self.assertFalse(record["correlation_acceptable"])
        self.assertFalse(record["verified"])

    def test_test_without_a_measured_peak_is_a_finding(self):
        item = _item()
        item["measured_peak_k"] = None
        record = evaluate_tps_item(item)
        self.assertFalse(record["verified"])

    def test_analysis_only_item_needs_no_measured_peak(self):
        item = _item(
            agreed_methods=["thermal-analysis"],
            performed_methods=["thermal-analysis"],
        )
        item["measured_peak_k"] = None
        record = evaluate_tps_item(item)
        self.assertIsNone(record["correlation_error_k"])
        self.assertTrue(record["verified"])

    def test_measured_peak_without_tolerance_rejected(self):
        item = _item()
        del item["correlation_tolerance_k"]
        with self.assertRaises(ValueError):
            evaluate_tps_item(item)

    def test_missing_key_rejected(self):
        item = _item()
        del item["insulation_mm"]
        with self.assertRaises(ValueError):
            evaluate_tps_item(item)

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_tps_item(_item(id="   "))


class AssessmentTests(unittest.TestCase):
    def test_single_clean_item_verifies(self):
        result = assess_tps_verification({"items": [_item()]})
        self.assertTrue(result["verified"])
        self.assertAlmostEqual(result["verified_fraction"], 1.0, places=9)

    def test_driving_item_is_the_lowest_capability_margin(self):
        result = assess_tps_verification(
            {"items": [_item(), _item(id="TPS-FLAP", capability_k=1650.0)]}
        )
        self.assertEqual(result["driving_item"], "TPS-FLAP")

    def test_one_failing_item_fails_the_set(self):
        result = assess_tps_verification(
            {"items": [_item(), _item(id="TPS-FLAP", as_built_mm=9.0)]}
        )
        self.assertFalse(result["verified"])
        self.assertAlmostEqual(result["verified_fraction"], 0.5, places=9)

    def test_duplicate_item_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_tps_verification({"items": [_item(), _item()]})

    def test_empty_item_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_tps_verification({"items": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_tps_verification(["items"])

    def test_tolerance_relaxes_nothing_measurable(self):
        self.assertLess(TEMPERATURE_TOLERANCE_K, 1e-6)


if __name__ == "__main__":
    unittest.main()
