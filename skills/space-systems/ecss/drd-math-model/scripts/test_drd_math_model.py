"""
Contract tests for drd_math_model_logic.py.
Stdlib unittest only.  Offline, deterministic.  No third-party deps.
Run: python3 test_drd_math_model.py
"""
import sys
import os
import unittest

# Allow running from the scripts/ directory or from the repo root.
sys.path.insert(0, os.path.dirname(__file__))

from drd_math_model_logic import (
    FREQ_TOLERANCE_PCT,
    MAC_THRESHOLD,
    MODEL_TYPES,
    REQUIRED_DELIVERY_ITEMS,
    REQUIRED_MMDD_FIELDS,
    assess_correlation,
    assess_mmdd_compliance,
    categorize_model_type,
    check_delivery_package,
    check_frequency_correlation,
    check_mac_value,
    validate_fidelity,
    validate_mmdd_fields,
)


# ---------------------------------------------------------------------------
# Model-type categorization
# ---------------------------------------------------------------------------

class TestCategorizeModelType(unittest.TestCase):

    def test_finite_element_accepted(self):
        result = categorize_model_type("FINITE_ELEMENT")
        self.assertEqual(result, "FINITE_ELEMENT")

    def test_analytical_accepted(self):
        result = categorize_model_type("ANALYTICAL")
        self.assertEqual(result, "ANALYTICAL")

    def test_hybrid_accepted(self):
        result = categorize_model_type("HYBRID")
        self.assertEqual(result, "HYBRID")

    def test_case_normalisation(self):
        result = categorize_model_type("finite_element")
        self.assertEqual(result, "FINITE_ELEMENT")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_model_type("EMPIRICAL")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            categorize_model_type("")


# ---------------------------------------------------------------------------
# Fidelity validation
# ---------------------------------------------------------------------------

class TestValidateFidelity(unittest.TestCase):

    def test_linear_accepted(self):
        self.assertEqual(validate_fidelity("LINEAR"), "LINEAR")

    def test_nonlinear_accepted(self):
        self.assertEqual(validate_fidelity("NONLINEAR"), "NONLINEAR")

    def test_unknown_fidelity_raises(self):
        with self.assertRaises(ValueError):
            validate_fidelity("QUASI_STATIC")


# ---------------------------------------------------------------------------
# MMDD field validation
# ---------------------------------------------------------------------------

def _complete_fields():
    return {
        "model_id": "STR-MM-001",
        "model_type": "FINITE_ELEMENT",
        "fidelity": "LINEAR",
        "coordinate_system_defined": True,
        "boundary_conditions_described": True,
        "loading_cases_listed": True,
        "element_types_listed": True,
        "material_properties_complete": True,
        "dof_count": 45600,
        "correlation_test_ref": "TST-REP-042",
    }


class TestValidateMmddFields(unittest.TestCase):

    def test_complete_fields_returns_empty_list(self):
        missing = validate_mmdd_fields(_complete_fields())
        self.assertEqual(missing, [])

    def test_missing_model_id_flagged(self):
        fields = _complete_fields()
        del fields["model_id"]
        missing = validate_mmdd_fields(fields)
        self.assertIn("model_id", missing)

    def test_empty_string_treated_as_missing(self):
        fields = _complete_fields()
        fields["correlation_test_ref"] = ""
        missing = validate_mmdd_fields(fields)
        self.assertIn("correlation_test_ref", missing)

    def test_false_boolean_treated_as_missing(self):
        fields = _complete_fields()
        fields["coordinate_system_defined"] = False
        missing = validate_mmdd_fields(fields)
        self.assertIn("coordinate_system_defined", missing)

    def test_multiple_missing_fields_all_reported(self):
        fields = _complete_fields()
        del fields["dof_count"]
        del fields["loading_cases_listed"]
        missing = validate_mmdd_fields(fields)
        self.assertIn("dof_count", missing)
        self.assertIn("loading_cases_listed", missing)
        self.assertEqual(len(missing), 2)


# ---------------------------------------------------------------------------
# Eigenfrequency correlation
# ---------------------------------------------------------------------------

class TestCheckFrequencyCorrelation(unittest.TestCase):

    def test_exact_match_zero_error(self):
        result = check_frequency_correlation(10.0, 10.0)
        self.assertAlmostEqual(result["error_pct"], 0.0)
        self.assertTrue(result["within_tolerance"])

    def test_within_tolerance_boundary(self):
        # 5 % exactly — boundary must pass
        result = check_frequency_correlation(100.0, 105.0)
        self.assertAlmostEqual(result["error_pct"], 5.0)
        self.assertTrue(result["within_tolerance"])

    def test_exceeds_tolerance_flagged(self):
        # 6 % error — must fail
        result = check_frequency_correlation(100.0, 106.0)
        self.assertAlmostEqual(result["error_pct"], 6.0)
        self.assertFalse(result["within_tolerance"])

    def test_negative_predicted_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_correlation(10.0, -5.0)

    def test_zero_measured_raises(self):
        with self.assertRaises(ValueError):
            check_frequency_correlation(0.0, 10.0)

    def test_result_contains_required_keys(self):
        result = check_frequency_correlation(50.0, 52.0)
        for key in ("measured_hz", "predicted_hz", "error_pct",
                    "within_tolerance", "tolerance_pct"):
            self.assertIn(key, result)


# ---------------------------------------------------------------------------
# MAC correlation
# ---------------------------------------------------------------------------

class TestCheckMacValue(unittest.TestCase):

    def test_high_mac_passes(self):
        result = check_mac_value(0.95)
        self.assertTrue(result["meets_threshold"])

    def test_mac_at_threshold_passes(self):
        result = check_mac_value(MAC_THRESHOLD)
        self.assertTrue(result["meets_threshold"])

    def test_mac_below_threshold_fails(self):
        result = check_mac_value(0.85)
        self.assertFalse(result["meets_threshold"])

    def test_mac_above_range_raises(self):
        with self.assertRaises(ValueError):
            check_mac_value(1.01)

    def test_mac_below_range_raises(self):
        with self.assertRaises(ValueError):
            check_mac_value(-0.1)

    def test_result_contains_required_keys(self):
        result = check_mac_value(0.92)
        for key in ("mac", "meets_threshold", "threshold"):
            self.assertIn(key, result)


# ---------------------------------------------------------------------------
# Combined correlation assessment
# ---------------------------------------------------------------------------

class TestAssessCorrelation(unittest.TestCase):

    def test_all_modes_pass(self):
        freq_pairs = [(100.0, 103.0), (200.0, 199.0)]
        mac_values = [0.95, 0.91]
        result = assess_correlation(freq_pairs, mac_values)
        self.assertTrue(result["correlated"])
        self.assertTrue(result["frequency_correlation_pass"])
        self.assertTrue(result["mac_correlation_pass"])

    def test_frequency_failure_makes_not_correlated(self):
        freq_pairs = [(100.0, 110.0)]  # 10 % error — exceeds tolerance
        mac_values = [0.95]
        result = assess_correlation(freq_pairs, mac_values)
        self.assertFalse(result["frequency_correlation_pass"])
        self.assertFalse(result["correlated"])

    def test_mac_failure_makes_not_correlated(self):
        freq_pairs = [(100.0, 102.0)]  # within tolerance
        mac_values = [0.80]            # below threshold
        result = assess_correlation(freq_pairs, mac_values)
        self.assertFalse(result["mac_correlation_pass"])
        self.assertFalse(result["correlated"])

    def test_mismatched_lengths_raises(self):
        with self.assertRaises(ValueError):
            assess_correlation([(100.0, 102.0), (200.0, 201.0)], [0.95])

    def test_empty_freq_pairs_raises(self):
        with self.assertRaises(ValueError):
            assess_correlation([], [])


# ---------------------------------------------------------------------------
# Delivery package completeness
# ---------------------------------------------------------------------------

def _complete_package():
    return {
        "mmdd_document": "MMDD-STR-001-v1.0.pdf",
        "model_file": "model_str_001.bdf",
        "correlation_report": "COR-REP-001.pdf",
        "coordinate_system_definition": "CS-DEF-001.pdf",
        "version_identifier": "v1.0",
        "interface_description": "ICD-STR-001.pdf",
    }


class TestCheckDeliveryPackage(unittest.TestCase):

    def test_complete_package_returns_empty_list(self):
        missing = check_delivery_package(_complete_package())
        self.assertEqual(missing, [])

    def test_missing_model_file_flagged(self):
        pkg = _complete_package()
        del pkg["model_file"]
        missing = check_delivery_package(pkg)
        self.assertIn("model_file", missing)

    def test_missing_correlation_report_flagged(self):
        pkg = _complete_package()
        pkg["correlation_report"] = ""
        missing = check_delivery_package(pkg)
        self.assertIn("correlation_report", missing)

    def test_multiple_missing_items_all_reported(self):
        pkg = _complete_package()
        del pkg["version_identifier"]
        del pkg["interface_description"]
        missing = check_delivery_package(pkg)
        self.assertIn("version_identifier", missing)
        self.assertIn("interface_description", missing)


# ---------------------------------------------------------------------------
# Full MMDD compliance assessment
# ---------------------------------------------------------------------------

class TestAssessMmddCompliance(unittest.TestCase):

    def test_fully_compliant_case(self):
        result = assess_mmdd_compliance(
            fields=_complete_fields(),
            freq_pairs=[(50.0, 51.5), (120.0, 118.0)],
            mac_values=[0.93, 0.96],
            delivery_package=_complete_package(),
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["missing_mmdd_fields"], [])
        self.assertEqual(result["missing_delivery_items"], [])

    def test_missing_field_makes_non_compliant(self):
        fields = _complete_fields()
        del fields["dof_count"]
        result = assess_mmdd_compliance(
            fields=fields,
            freq_pairs=[(50.0, 51.0)],
            mac_values=[0.92],
            delivery_package=_complete_package(),
        )
        self.assertFalse(result["compliant"])
        self.assertIn("dof_count", result["missing_mmdd_fields"])

    def test_failed_correlation_makes_non_compliant(self):
        result = assess_mmdd_compliance(
            fields=_complete_fields(),
            freq_pairs=[(50.0, 60.0)],  # 20 % error
            mac_values=[0.91],
            delivery_package=_complete_package(),
        )
        self.assertFalse(result["compliant"])
        self.assertFalse(result["correlation"]["correlated"])

    def test_incomplete_delivery_makes_non_compliant(self):
        pkg = _complete_package()
        del pkg["mmdd_document"]
        result = assess_mmdd_compliance(
            fields=_complete_fields(),
            freq_pairs=[(80.0, 82.0)],
            mac_values=[0.94],
            delivery_package=pkg,
        )
        self.assertFalse(result["compliant"])
        self.assertIn("mmdd_document", result["missing_delivery_items"])

    def test_result_contains_all_top_level_keys(self):
        result = assess_mmdd_compliance(
            fields=_complete_fields(),
            freq_pairs=[(100.0, 101.0)],
            mac_values=[0.95],
            delivery_package=_complete_package(),
        )
        for key in ("missing_mmdd_fields", "correlation",
                    "missing_delivery_items", "compliant"):
            self.assertIn(key, result)


if __name__ == "__main__":
    unittest.main()
