"""
Gate 3 contract tests for interface_verification_test_logic.py.
stdlib unittest only; deterministic and offline.
Run: python3 test_interface_verification_test.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from interface_verification_test_logic import (
    INTERFACE_TYPES,
    VERIFICATION_METHODS,
    categorize_interface,
    select_verification_method,
    check_dimensional_fit,
    validate_icd_reference,
    verify_interface,
    assess_interface_set,
)


def _make_interface(**overrides):
    base = {
        "interface_id": "IFx-001",
        "interface_type": "mechanical",
        "nominal_mm": 100.0,
        "tolerance_mm": 0.5,
        "actual_mm": 100.2,
        "icd_reference": "ICD-MECH-001 rev A",
        "verification_method": "inspection",
    }
    base.update(overrides)
    return base


class TestCategorizeInterface(unittest.TestCase):

    def test_valid_mechanical_returns_mechanical(self):
        self.assertEqual(categorize_interface("mechanical"), "mechanical")

    def test_valid_electrical_returns_electrical(self):
        self.assertEqual(categorize_interface("electrical"), "electrical")

    def test_all_valid_types_accepted(self):
        for itype in INTERFACE_TYPES:
            with self.subTest(itype=itype):
                self.assertEqual(categorize_interface(itype), itype)

    def test_unknown_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            categorize_interface("pneumatic")

    def test_non_string_raises_type_error(self):
        with self.assertRaises(TypeError):
            categorize_interface(42)

    def test_whitespace_stripping_and_case_normalization(self):
        self.assertEqual(categorize_interface("  Mechanical  "), "mechanical")


class TestSelectVerificationMethod(unittest.TestCase):

    def test_electrical_requires_test_no_facility(self):
        self.assertEqual(select_verification_method("electrical", False), "test")

    def test_optical_requires_test_no_facility(self):
        self.assertEqual(select_verification_method("optical", False), "test")

    def test_mechanical_no_facility_returns_inspection(self):
        self.assertEqual(select_verification_method("mechanical", False), "inspection")

    def test_thermal_no_facility_returns_inspection(self):
        self.assertEqual(select_verification_method("thermal", False), "inspection")

    def test_mechanical_with_facility_returns_test(self):
        self.assertEqual(select_verification_method("mechanical", True), "test")

    def test_fluid_with_facility_returns_test(self):
        self.assertEqual(select_verification_method("fluid", True), "test")

    def test_unknown_type_propagates_value_error(self):
        with self.assertRaises(ValueError):
            select_verification_method("structural", False)


class TestCheckDimensionalFit(unittest.TestCase):

    def test_within_tolerance_returns_true(self):
        result = check_dimensional_fit(100.0, 0.5, 100.3)
        self.assertTrue(result["within_tolerance"])

    def test_above_tolerance_returns_false(self):
        result = check_dimensional_fit(100.0, 0.5, 100.6)
        self.assertFalse(result["within_tolerance"])

    def test_below_tolerance_returns_false(self):
        result = check_dimensional_fit(100.0, 0.5, 99.4)
        self.assertFalse(result["within_tolerance"])

    def test_at_upper_boundary_passes(self):
        result = check_dimensional_fit(100.0, 0.5, 100.5)
        self.assertTrue(result["within_tolerance"])

    def test_at_lower_boundary_passes(self):
        result = check_dimensional_fit(100.0, 0.5, 99.5)
        self.assertTrue(result["within_tolerance"])

    def test_deviation_is_signed_positive_for_oversized(self):
        result = check_dimensional_fit(100.0, 0.5, 100.3)
        self.assertAlmostEqual(result["deviation_mm"], 0.3, places=5)

    def test_deviation_is_signed_negative_for_undersized(self):
        result = check_dimensional_fit(100.0, 0.5, 99.7)
        self.assertAlmostEqual(result["deviation_mm"], -0.3, places=5)

    def test_zero_tolerance_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_dimensional_fit(100.0, 0.0, 100.0)

    def test_negative_tolerance_raises_value_error(self):
        with self.assertRaises(ValueError):
            check_dimensional_fit(100.0, -0.1, 100.0)

    def test_bounds_reported_correctly(self):
        result = check_dimensional_fit(50.0, 0.2, 50.1)
        self.assertAlmostEqual(result["lower_bound_mm"], 49.8, places=5)
        self.assertAlmostEqual(result["upper_bound_mm"], 50.2, places=5)


class TestValidateIcdReference(unittest.TestCase):

    def test_non_empty_reference_returns_true(self):
        self.assertTrue(validate_icd_reference("ICD-STR-001 rev B"))

    def test_empty_string_returns_false(self):
        self.assertFalse(validate_icd_reference(""))

    def test_whitespace_only_returns_false(self):
        self.assertFalse(validate_icd_reference("   "))

    def test_non_string_raises_type_error(self):
        with self.assertRaises(TypeError):
            validate_icd_reference(None)


class TestVerifyInterface(unittest.TestCase):

    def test_compliant_interface(self):
        result = verify_interface(_make_interface())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_out_of_tolerance_is_non_compliant(self):
        result = verify_interface(_make_interface(actual_mm=101.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("out_of_tolerance" in f for f in result["findings"]))

    def test_missing_icd_reference_is_non_compliant(self):
        result = verify_interface(_make_interface(icd_reference=""))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("missing_icd_reference" in f for f in result["findings"]))

    def test_both_failures_produce_two_findings(self):
        result = verify_interface(_make_interface(actual_mm=101.0, icd_reference=""))
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 2)

    def test_missing_required_field_raises_value_error(self):
        iface = _make_interface()
        del iface["icd_reference"]
        with self.assertRaises(ValueError):
            verify_interface(iface)

    def test_unknown_interface_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            verify_interface(_make_interface(interface_type="unknown"))

    def test_unknown_verification_method_raises_value_error(self):
        with self.assertRaises(ValueError):
            verify_interface(_make_interface(verification_method="walk-around"))

    def test_result_contains_interface_id(self):
        result = verify_interface(_make_interface(interface_id="IFx-999"))
        self.assertEqual(result["interface_id"], "IFx-999")

    def test_fit_check_embedded_in_result(self):
        result = verify_interface(_make_interface())
        self.assertIn("fit_check", result)
        self.assertIn("within_tolerance", result["fit_check"])


class TestAssessInterfaceSet(unittest.TestCase):

    def test_all_compliant_set(self):
        interfaces = [
            _make_interface(interface_id="IF-001"),
            _make_interface(interface_id="IF-002", interface_type="thermal"),
        ]
        summary = assess_interface_set(interfaces)
        self.assertTrue(summary["all_compliant"])
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["compliant_count"], 2)
        self.assertEqual(summary["non_compliant_count"], 0)

    def test_one_non_compliant_in_set(self):
        interfaces = [
            _make_interface(interface_id="IF-001"),
            _make_interface(interface_id="IF-002", actual_mm=110.0),
        ]
        summary = assess_interface_set(interfaces)
        self.assertFalse(summary["all_compliant"])
        self.assertEqual(summary["non_compliant_count"], 1)

    def test_empty_list_raises_value_error(self):
        with self.assertRaises(ValueError):
            assess_interface_set([])

    def test_non_list_raises_type_error(self):
        with self.assertRaises(TypeError):
            assess_interface_set("not-a-list")

    def test_results_length_matches_total(self):
        interfaces = [_make_interface(interface_id=f"IF-{i:03d}") for i in range(5)]
        summary = assess_interface_set(interfaces)
        self.assertEqual(len(summary["results"]), summary["total"])

    def test_mixed_types_all_compliant(self):
        interfaces = [
            _make_interface(interface_id="IF-M", interface_type="mechanical"),
            _make_interface(interface_id="IF-E", interface_type="electrical", verification_method="test"),
            _make_interface(interface_id="IF-T", interface_type="thermal"),
            _make_interface(interface_id="IF-F", interface_type="fluid"),
            _make_interface(interface_id="IF-O", interface_type="optical", verification_method="test"),
        ]
        summary = assess_interface_set(interfaces)
        self.assertTrue(summary["all_compliant"])
        self.assertEqual(summary["total"], 5)


if __name__ == "__main__":
    unittest.main()
