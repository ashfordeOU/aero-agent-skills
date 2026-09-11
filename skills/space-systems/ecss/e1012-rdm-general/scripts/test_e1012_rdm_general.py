#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-12 §5.1.2/§5.2 radiation design
margin — general case (dose-effects, margin approach).

Exercises scripts/e1012_rdm_general_logic.py (stdlib unittest, offline).
Contract: a design dose is mission dose times uncertainty factor (factor
defaults to 1.0 in the general case); a non-positive mission dose or a
factor below 1.0 raises; the RDM is the ratio of lot-qualified failure
dose to design dose and both inputs must be strictly positive; a
component is compliant when its RDM meets or exceeds the required
minimum margin (2.0 default); a non-positive RDM or required minimum
raises; the full component assessment composes the above steps correctly;
assess_all processes a list without mutation; rdm_findings returns only
the non-compliant entries.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1012_rdm_general_logic as rdm  # noqa: E402


class ComputeDesignDoseTest(unittest.TestCase):
    def test_default_factor_returns_mission_dose(self):
        self.assertAlmostEqual(rdm.compute_design_dose(10.0), 10.0)

    def test_explicit_factor_scales_dose(self):
        self.assertAlmostEqual(rdm.compute_design_dose(10.0, 2.0), 20.0)

    def test_factor_one_is_identity(self):
        self.assertAlmostEqual(rdm.compute_design_dose(5.5, 1.0), 5.5)

    def test_zero_mission_dose_raises(self):
        with self.assertRaises(ValueError):
            rdm.compute_design_dose(0.0)

    def test_negative_mission_dose_raises(self):
        with self.assertRaises(ValueError):
            rdm.compute_design_dose(-3.0)

    def test_factor_below_one_raises(self):
        with self.assertRaises(ValueError):
            rdm.compute_design_dose(10.0, 0.5)


class ComputeRdmTest(unittest.TestCase):
    def test_ratio_twice_design_dose(self):
        self.assertAlmostEqual(rdm.compute_rdm(200.0, 100.0), 2.0)

    def test_ratio_exactly_one(self):
        self.assertAlmostEqual(rdm.compute_rdm(50.0, 50.0), 1.0)

    def test_fractional_rdm(self):
        self.assertAlmostEqual(rdm.compute_rdm(10.0, 40.0), 0.25)

    def test_zero_failure_dose_raises(self):
        with self.assertRaises(ValueError):
            rdm.compute_rdm(0.0, 10.0)

    def test_negative_failure_dose_raises(self):
        with self.assertRaises(ValueError):
            rdm.compute_rdm(-5.0, 10.0)

    def test_zero_design_dose_raises(self):
        with self.assertRaises(ValueError):
            rdm.compute_rdm(50.0, 0.0)

    def test_negative_design_dose_raises(self):
        with self.assertRaises(ValueError):
            rdm.compute_rdm(50.0, -1.0)


class CheckRdmComplianceTest(unittest.TestCase):
    def test_rdm_above_minimum_is_compliant(self):
        result = rdm.check_rdm_compliance("comp-A", 3.0, 2.0)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["finding"])

    def test_rdm_exactly_at_minimum_is_compliant(self):
        result = rdm.check_rdm_compliance("comp-A", 2.0, 2.0)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["finding"])

    def test_rdm_below_minimum_is_non_compliant(self):
        result = rdm.check_rdm_compliance("comp-B", 1.5, 2.0)
        self.assertFalse(result["compliant"])
        self.assertIsNotNone(result["finding"])
        self.assertEqual(result["finding"]["issue"], "rdm_below_minimum")

    def test_finding_contains_component_id(self):
        result = rdm.check_rdm_compliance("U42", 1.0, 2.0)
        self.assertEqual(result["finding"]["component"], "U42")

    def test_finding_contains_rdm_and_required(self):
        result = rdm.check_rdm_compliance("U42", 1.0, 2.0)
        self.assertAlmostEqual(result["finding"]["rdm"], 1.0)
        self.assertAlmostEqual(result["finding"]["required_rdm_min"], 2.0)

    def test_zero_rdm_raises(self):
        with self.assertRaises(ValueError):
            rdm.check_rdm_compliance("comp-C", 0.0, 2.0)

    def test_zero_required_min_raises(self):
        with self.assertRaises(ValueError):
            rdm.check_rdm_compliance("comp-C", 2.0, 0.0)


class AssessComponentTest(unittest.TestCase):
    def test_passing_component_general_case(self):
        result = rdm.assess_component("C1", 50.0, 120.0)
        self.assertAlmostEqual(result["design_dose_gy"], 50.0)
        self.assertAlmostEqual(result["rdm"], 2.4)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["finding"])

    def test_failing_component_below_margin(self):
        result = rdm.assess_component("C2", 50.0, 80.0)
        self.assertAlmostEqual(result["rdm"], 1.6)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["finding"]["issue"], "rdm_below_minimum")

    def test_uncertainty_factor_scales_design_dose(self):
        result = rdm.assess_component("C3", 50.0, 200.0, uncertainty_factor=2.0)
        self.assertAlmostEqual(result["design_dose_gy"], 100.0)
        self.assertAlmostEqual(result["rdm"], 2.0)
        self.assertTrue(result["compliant"])

    def test_custom_required_rdm_min(self):
        result = rdm.assess_component("C4", 50.0, 120.0, required_rdm_min=3.0)
        self.assertAlmostEqual(result["rdm"], 2.4)
        self.assertFalse(result["compliant"])

    def test_result_carries_all_expected_keys(self):
        result = rdm.assess_component("C5", 10.0, 30.0)
        for key in (
            "component",
            "mission_dose_gy",
            "uncertainty_factor",
            "design_dose_gy",
            "qualified_failure_dose_gy",
            "rdm",
            "required_rdm_min",
            "compliant",
            "finding",
        ):
            self.assertIn(key, result)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            rdm.assess_component("C6", -10.0, 30.0)


class AssessAllTest(unittest.TestCase):
    def test_empty_list_returns_empty(self):
        self.assertEqual(rdm.assess_all([]), [])

    def test_single_component(self):
        results = rdm.assess_all(
            [{"component_id": "D1", "mission_dose_gy": 50.0, "qualified_failure_dose_gy": 120.0}]
        )
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["compliant"])

    def test_preserves_order(self):
        specs = [
            {"component_id": "D1", "mission_dose_gy": 10.0, "qualified_failure_dose_gy": 25.0},
            {"component_id": "D2", "mission_dose_gy": 10.0, "qualified_failure_dose_gy": 15.0},
        ]
        results = rdm.assess_all(specs)
        self.assertEqual(results[0]["component"], "D1")
        self.assertEqual(results[1]["component"], "D2")

    def test_mixed_pass_fail(self):
        specs = [
            {"component_id": "P1", "mission_dose_gy": 10.0, "qualified_failure_dose_gy": 25.0},
            {"component_id": "F1", "mission_dose_gy": 10.0, "qualified_failure_dose_gy": 15.0},
        ]
        results = rdm.assess_all(specs)
        self.assertTrue(results[0]["compliant"])
        self.assertFalse(results[1]["compliant"])

    def test_optional_keys_use_defaults(self):
        results = rdm.assess_all(
            [{"component_id": "D3", "mission_dose_gy": 20.0, "qualified_failure_dose_gy": 60.0}]
        )
        self.assertAlmostEqual(results[0]["uncertainty_factor"], 1.0)
        self.assertAlmostEqual(results[0]["required_rdm_min"], rdm.DEFAULT_RDM_MIN)

    def test_does_not_mutate_input(self):
        spec = {"component_id": "D4", "mission_dose_gy": 10.0, "qualified_failure_dose_gy": 25.0}
        original_keys = set(spec.keys())
        rdm.assess_all([spec])
        self.assertEqual(set(spec.keys()), original_keys)


class RdmFindingsTest(unittest.TestCase):
    def test_all_compliant_returns_empty(self):
        specs = [
            {"component_id": "E1", "mission_dose_gy": 10.0, "qualified_failure_dose_gy": 25.0},
            {"component_id": "E2", "mission_dose_gy": 5.0, "qualified_failure_dose_gy": 15.0},
        ]
        results = rdm.assess_all(specs)
        self.assertEqual(rdm.rdm_findings(results), [])

    def test_one_failure_returned(self):
        specs = [
            {"component_id": "E3", "mission_dose_gy": 10.0, "qualified_failure_dose_gy": 25.0},
            {"component_id": "E4", "mission_dose_gy": 10.0, "qualified_failure_dose_gy": 15.0},
        ]
        results = rdm.assess_all(specs)
        findings = rdm.rdm_findings(results)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["component"], "E4")
        self.assertEqual(findings[0]["issue"], "rdm_below_minimum")

    def test_all_failing_all_returned(self):
        specs = [
            {"component_id": "E5", "mission_dose_gy": 10.0, "qualified_failure_dose_gy": 5.0},
            {"component_id": "E6", "mission_dose_gy": 10.0, "qualified_failure_dose_gy": 8.0},
        ]
        results = rdm.assess_all(specs)
        findings = rdm.rdm_findings(results)
        self.assertEqual(len(findings), 2)


if __name__ == "__main__":
    unittest.main()
