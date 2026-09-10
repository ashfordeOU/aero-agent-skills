#!/usr/bin/env python3
"""Offline unittest contract for e1002_method_analysis_logic.py
(ECSS-E-ST-10-02C clause 5.2.2.3 verification-by-analysis method)."""

import unittest

from e1002_method_analysis_logic import (
    ANALYSIS_TECHNIQUES,
    analysis_case_rollup,
    analysis_plan_completeness,
    environment_envelope_check,
    select_analysis_technique,
    similarity_validation,
    validate_analysis_technique,
    verification_by_similarity_status,
)


class ValidateAnalysisTechniqueTests(unittest.TestCase):
    def test_accepts_every_known_technique(self):
        for technique in ANALYSIS_TECHNIQUES:
            self.assertEqual(validate_analysis_technique(technique), technique)

    def test_rejects_unrecognized_technique(self):
        with self.assertRaises(ValueError):
            validate_analysis_technique("guesswork")


class SelectAnalysisTechniqueTests(unittest.TestCase):
    def test_heritage_reference_selects_similarity(self):
        case = {"has_verified_reference_item": True}
        self.assertEqual(select_analysis_technique(case), "similarity")

    def test_similarity_takes_priority_over_other_flags(self):
        case = {
            "has_verified_reference_item": True,
            "requires_probabilistic_treatment": True,
            "requires_bounding_worst_case": True,
        }
        self.assertEqual(select_analysis_technique(case), "similarity")

    def test_probabilistic_flag_selects_statistical(self):
        case = {"requires_probabilistic_treatment": True}
        self.assertEqual(select_analysis_technique(case), "statistical")

    def test_bounding_flag_selects_worst_case(self):
        case = {"requires_bounding_worst_case": True}
        self.assertEqual(select_analysis_technique(case), "worst_case")

    def test_judgement_only_flag_selects_qualitative(self):
        case = {"requires_engineering_judgement_only": True}
        self.assertEqual(select_analysis_technique(case), "qualitative")

    def test_no_flags_defaults_to_classical_calculation(self):
        self.assertEqual(select_analysis_technique({}), "classical_calculation")

    def test_rejects_non_dict_case(self):
        with self.assertRaises(ValueError):
            select_analysis_technique(["has_verified_reference_item"])


class EnvironmentEnvelopeCheckTests(unittest.TestCase):
    def test_no_exceedance_when_new_is_bounded(self):
        new_env = {"peak_temperature_c": 60, "random_vibration_grms": 8.0}
        reference_env = {"peak_temperature_c": 70, "random_vibration_grms": 10.0}
        self.assertEqual(environment_envelope_check(new_env, reference_env), [])

    def test_equal_values_are_enveloped(self):
        new_env = {"peak_temperature_c": 70}
        reference_env = {"peak_temperature_c": 70}
        self.assertEqual(environment_envelope_check(new_env, reference_env), [])

    def test_exceeded_parameter_is_reported(self):
        new_env = {"peak_temperature_c": 90, "random_vibration_grms": 8.0}
        reference_env = {"peak_temperature_c": 70, "random_vibration_grms": 10.0}
        self.assertEqual(
            environment_envelope_check(new_env, reference_env),
            ["peak_temperature_c"],
        )

    def test_missing_reference_parameter_raises(self):
        new_env = {"shock_response_g": 500}
        reference_env = {"peak_temperature_c": 70}
        with self.assertRaises(ValueError):
            environment_envelope_check(new_env, reference_env)


class SimilarityValidationTests(unittest.TestCase):
    def _base_item(self):
        return {
            "reference_item_id": "REF-001",
            "reference_previously_verified": True,
            "design_identical": True,
            "manufacturing_process_equivalent": True,
            "new_environment": {"peak_temperature_c": 60},
            "reference_environment": {"peak_temperature_c": 70},
        }

    def test_fully_compliant_item_has_no_findings(self):
        self.assertEqual(similarity_validation(self._base_item()), [])

    def test_design_differences_assessed_substitutes_for_identical(self):
        item = self._base_item()
        item["design_identical"] = False
        item["design_differences_assessed"] = True
        self.assertEqual(similarity_validation(item), [])

    def test_missing_reference_item_is_flagged(self):
        item = self._base_item()
        item["reference_item_id"] = None
        findings = similarity_validation(item)
        self.assertEqual(
            [f["issue"] for f in findings], ["no_verified_reference_item"]
        )

    def test_unverified_reference_item_is_flagged(self):
        item = self._base_item()
        item["reference_previously_verified"] = False
        findings = similarity_validation(item)
        self.assertEqual(
            [f["issue"] for f in findings], ["no_verified_reference_item"]
        )

    def test_unassessed_design_difference_is_flagged(self):
        item = self._base_item()
        item["design_identical"] = False
        findings = similarity_validation(item)
        self.assertEqual(
            [f["issue"] for f in findings], ["design_differences_not_assessed"]
        )

    def test_non_equivalent_manufacturing_is_flagged(self):
        item = self._base_item()
        item["manufacturing_process_equivalent"] = False
        findings = similarity_validation(item)
        self.assertEqual(
            [f["issue"] for f in findings],
            ["manufacturing_process_not_equivalent"],
        )

    def test_unenveloped_environment_is_flagged_with_parameters(self):
        item = self._base_item()
        item["new_environment"] = {"peak_temperature_c": 90}
        findings = similarity_validation(item)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "environment_not_enveloped")
        self.assertEqual(findings[0]["parameters"], ["peak_temperature_c"])

    def test_multiple_unmet_conditions_all_reported(self):
        item = {
            "reference_item_id": None,
            "reference_previously_verified": False,
            "design_identical": False,
            "design_differences_assessed": False,
            "manufacturing_process_equivalent": False,
            "new_environment": {},
            "reference_environment": {},
        }
        findings = similarity_validation(item)
        issues = {f["issue"] for f in findings}
        self.assertEqual(
            issues,
            {
                "no_verified_reference_item",
                "design_differences_not_assessed",
                "manufacturing_process_not_equivalent",
            },
        )


class VerificationBySimilarityStatusTests(unittest.TestCase):
    def test_compliant_item_is_verified(self):
        item = {
            "reference_item_id": "REF-002",
            "reference_previously_verified": True,
            "design_identical": True,
            "manufacturing_process_equivalent": True,
            "new_environment": {},
            "reference_environment": {},
        }
        result = verification_by_similarity_status(item)
        self.assertEqual(result["status"], "verified_by_similarity")
        self.assertEqual(result["findings"], [])

    def test_noncompliant_item_is_not_verified(self):
        item = {
            "reference_item_id": None,
            "reference_previously_verified": False,
            "design_identical": False,
            "manufacturing_process_equivalent": False,
            "new_environment": {},
            "reference_environment": {},
        }
        result = verification_by_similarity_status(item)
        self.assertEqual(result["status"], "not_verified")
        self.assertTrue(result["findings"])


class AnalysisPlanCompletenessTests(unittest.TestCase):
    def _base_plan(self):
        return {
            "requirement_id": "REQ-100",
            "technique": "worst_case",
            "input_data_sources": ["thermal model v3"],
            "acceptance_criteria": "margin >= 0",
            "verified_by": "J. Doe",
        }

    def test_complete_plan_has_no_findings(self):
        self.assertEqual(analysis_plan_completeness(self._base_plan()), [])

    def test_missing_field_is_reported(self):
        plan = self._base_plan()
        del plan["acceptance_criteria"]
        findings = analysis_plan_completeness(plan)
        self.assertEqual(
            [f["field"] for f in findings], ["acceptance_criteria"]
        )

    def test_similarity_plan_requires_reference_item_id(self):
        plan = self._base_plan()
        plan["technique"] = "similarity"
        findings = analysis_plan_completeness(plan)
        self.assertEqual(
            [f["field"] for f in findings], ["reference_item_id"]
        )

    def test_similarity_plan_with_reference_item_id_is_complete(self):
        plan = self._base_plan()
        plan["technique"] = "similarity"
        plan["reference_item_id"] = "REF-003"
        self.assertEqual(analysis_plan_completeness(plan), [])

    def test_unrecognized_technique_raises(self):
        plan = self._base_plan()
        plan["technique"] = "guesswork"
        with self.assertRaises(ValueError):
            analysis_plan_completeness(plan)


class AnalysisCaseRollupTests(unittest.TestCase):
    def test_all_closed_cases(self):
        cases = [
            {"case_id": "C1", "findings": []},
            {"case_id": "C2", "findings": []},
        ]
        rollup = analysis_case_rollup(cases)
        self.assertEqual(
            rollup, {"total": 2, "closed": 2, "open": 0, "open_case_ids": []}
        )

    def test_mixed_open_and_closed_cases(self):
        cases = [
            {"case_id": "C1", "findings": []},
            {"case_id": "C2", "findings": [{"issue": "no_verified_reference_item"}]},
            {"case_id": "C3", "findings": [{"issue": "environment_not_enveloped"}]},
        ]
        rollup = analysis_case_rollup(cases)
        self.assertEqual(rollup["total"], 3)
        self.assertEqual(rollup["closed"], 1)
        self.assertEqual(rollup["open"], 2)
        self.assertEqual(rollup["open_case_ids"], ["C2", "C3"])

    def test_empty_cases_raises(self):
        with self.assertRaises(ValueError):
            analysis_case_rollup([])


if __name__ == "__main__":
    result = unittest.main(exit=False)
    if result.result.wasSuccessful():
        print("OK")
