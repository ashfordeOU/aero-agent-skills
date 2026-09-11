#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C §5.3 environment-driven margins.

Exercises scripts/e1012_env_margins_logic.py (stdlib unittest, offline).
Contract: margin-approach categorization accepts 'deterministic' and
'probabilistic' and rejects anything else; the AE-8 GEO worst-case exemption
applies only when orbit is GEO, model is an AE-8 variant, and the worst-case
flag is True; unrecognized orbit or model raises; compute_design_dose returns
total_dose * rdm_factor and raises when rdm_factor is below the minimum or
inputs are non-numeric; validate_probabilistic_agreement returns True when
the model confidence level meets or exceeds the agreed level and raises for
out-of-range inputs; model-uncertainty documentation is complete only when all
three required fields are present; assess_margins flags every missing or
invalid field as a distinct finding; is_margin_compliant returns True only when
findings are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1012_env_margins_logic as em  # noqa: E402


class CategorizeMarginApproachTest(unittest.TestCase):
    def test_deterministic_approach_accepted(self):
        self.assertEqual(em.categorize_margin_approach("deterministic"), "deterministic")

    def test_probabilistic_approach_accepted(self):
        self.assertEqual(em.categorize_margin_approach("probabilistic"), "probabilistic")

    def test_unknown_approach_raises(self):
        with self.assertRaises(ValueError):
            em.categorize_margin_approach("pessimistic")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            em.categorize_margin_approach("")


class CheckAe8GeoExemptionTest(unittest.TestCase):
    def test_geo_ae8_worst_case_exemption_applies(self):
        self.assertTrue(em.check_ae8_geo_exemption("geo", "ae8", True))

    def test_geo_ae8_max_worst_case_exemption_applies(self):
        self.assertTrue(em.check_ae8_geo_exemption("geo", "ae8_max", True))

    def test_geo_ae8_worst_case_false_no_exemption(self):
        self.assertFalse(em.check_ae8_geo_exemption("geo", "ae8", False))

    def test_leo_ae8_worst_case_no_exemption(self):
        self.assertFalse(em.check_ae8_geo_exemption("leo", "ae8", True))

    def test_meo_ae8_worst_case_no_exemption(self):
        self.assertFalse(em.check_ae8_geo_exemption("meo", "ae8", True))

    def test_heo_ae8_worst_case_no_exemption(self):
        self.assertFalse(em.check_ae8_geo_exemption("heo", "ae8", True))

    def test_geo_ae9_model_no_exemption(self):
        self.assertFalse(em.check_ae8_geo_exemption("geo", "ae9", True))

    def test_unknown_orbit_raises(self):
        with self.assertRaises(ValueError):
            em.check_ae8_geo_exemption("sso", "ae8", True)

    def test_unknown_model_raises(self):
        with self.assertRaises(ValueError):
            em.check_ae8_geo_exemption("geo", "ae12", True)


class ComputeDesignDoseTest(unittest.TestCase):
    def test_basic_design_dose(self):
        self.assertAlmostEqual(em.compute_design_dose(10.0, 2.0), 20.0)

    def test_rdm_at_minimum_floor_accepted(self):
        self.assertAlmostEqual(em.compute_design_dose(5.0, 2.0), 10.0)

    def test_rdm_above_minimum_accepted(self):
        self.assertAlmostEqual(em.compute_design_dose(8.0, 3.0), 24.0)

    def test_rdm_below_minimum_raises(self):
        with self.assertRaises(ValueError):
            em.compute_design_dose(10.0, 1.5)

    def test_non_numeric_total_dose_raises(self):
        with self.assertRaises(ValueError):
            em.compute_design_dose("high", 2.0)

    def test_boolean_total_dose_raises(self):
        with self.assertRaises(ValueError):
            em.compute_design_dose(True, 2.0)

    def test_non_numeric_rdm_factor_raises(self):
        with self.assertRaises(ValueError):
            em.compute_design_dose(10.0, "two")

    def test_zero_rdm_below_minimum_raises(self):
        with self.assertRaises(ValueError):
            em.compute_design_dose(10.0, 0.0)


class ValidateProbabilisticAgreementTest(unittest.TestCase):
    def test_confidence_meets_agreed_returns_true(self):
        self.assertTrue(em.validate_probabilistic_agreement(0.97, 0.95))

    def test_confidence_equals_agreed_returns_true(self):
        self.assertTrue(em.validate_probabilistic_agreement(0.95, 0.95))

    def test_confidence_below_agreed_returns_false(self):
        self.assertFalse(em.validate_probabilistic_agreement(0.90, 0.95))

    def test_confidence_level_zero_raises(self):
        with self.assertRaises(ValueError):
            em.validate_probabilistic_agreement(0.0, 0.95)

    def test_agreed_level_zero_raises(self):
        with self.assertRaises(ValueError):
            em.validate_probabilistic_agreement(0.95, 0.0)

    def test_confidence_above_one_raises(self):
        with self.assertRaises(ValueError):
            em.validate_probabilistic_agreement(1.1, 0.95)

    def test_confidence_level_one_accepted(self):
        self.assertTrue(em.validate_probabilistic_agreement(1.0, 0.95))


class CheckModelUncertaintyDocumentedTest(unittest.TestCase):
    def test_all_fields_present_returns_empty(self):
        evidence = {
            "model_name": "AE-8 MAX",
            "model_version": "2.0",
            "uncertainty_factors": {"electron_fluence": 2.0},
        }
        self.assertEqual(em.check_model_uncertainty_documented(evidence), [])

    def test_missing_model_version_flagged(self):
        evidence = {
            "model_name": "AE-8 MAX",
            "uncertainty_factors": {"electron_fluence": 2.0},
        }
        self.assertIn("model_version", em.check_model_uncertainty_documented(evidence))

    def test_missing_all_fields_returns_three(self):
        self.assertEqual(len(em.check_model_uncertainty_documented({})), 3)

    def test_non_dict_evidence_raises(self):
        with self.assertRaises(ValueError):
            em.check_model_uncertainty_documented("documented")


class AssessMarginsTest(unittest.TestCase):
    def _good_evidence(self):
        return {
            "model_name": "AE-8 MAX",
            "model_version": "2.0",
            "uncertainty_factors": {"electron_fluence": 2.0},
        }

    def test_deterministic_full_compliant_assessment(self):
        result = em.assess_margins(
            {
                "item_id": "solar-array-1",
                "orbit_type": "geo",
                "trapped_electron_model": "ae8_max",
                "use_worst_case_geo": True,
                "margin_approach": "deterministic",
                "model_uncertainty_evidence": self._good_evidence(),
                "total_dose": 15.0,
                "rdm_factor": 2.0,
            }
        )
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["design_dose"], 30.0)
        self.assertTrue(result["geo_exemption_applies"])
        self.assertTrue(em.is_margin_compliant(result))

    def test_probabilistic_full_compliant_assessment(self):
        result = em.assess_margins(
            {
                "item_id": "payload-1",
                "orbit_type": "leo",
                "trapped_electron_model": "ae9",
                "use_worst_case_geo": False,
                "margin_approach": "probabilistic",
                "model_uncertainty_evidence": self._good_evidence(),
                "confidence_level": 0.97,
                "agreed_confidence_level": 0.95,
            }
        )
        self.assertEqual(result["findings"], [])
        self.assertIsNone(result["design_dose"])
        self.assertTrue(result["probability_agreement_met"])
        self.assertTrue(em.is_margin_compliant(result))

    def test_deterministic_missing_total_dose_flagged(self):
        result = em.assess_margins(
            {
                "item_id": "battery-1",
                "orbit_type": "leo",
                "trapped_electron_model": "ae9",
                "use_worst_case_geo": False,
                "margin_approach": "deterministic",
                "model_uncertainty_evidence": self._good_evidence(),
                "rdm_factor": 2.0,
            }
        )
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("missing_total_dose", issues)
        self.assertFalse(em.is_margin_compliant(result))

    def test_deterministic_rdm_below_floor_flagged(self):
        result = em.assess_margins(
            {
                "item_id": "star-tracker-1",
                "orbit_type": "meo",
                "trapped_electron_model": "ae9",
                "use_worst_case_geo": False,
                "margin_approach": "deterministic",
                "model_uncertainty_evidence": self._good_evidence(),
                "total_dose": 20.0,
                "rdm_factor": 1.5,
            }
        )
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("rdm_error", issues)
        self.assertFalse(em.is_margin_compliant(result))

    def test_probabilistic_confidence_below_agreed_flagged(self):
        result = em.assess_margins(
            {
                "item_id": "transponder-1",
                "orbit_type": "geo",
                "trapped_electron_model": "ae8",
                "use_worst_case_geo": False,
                "margin_approach": "probabilistic",
                "model_uncertainty_evidence": self._good_evidence(),
                "confidence_level": 0.90,
                "agreed_confidence_level": 0.95,
            }
        )
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("confidence_level_below_agreed", issues)
        self.assertFalse(result["probability_agreement_met"])
        self.assertFalse(em.is_margin_compliant(result))

    def test_missing_model_uncertainty_evidence_flagged(self):
        result = em.assess_margins(
            {
                "item_id": "pcb-1",
                "orbit_type": "leo",
                "trapped_electron_model": "ae9",
                "use_worst_case_geo": False,
                "margin_approach": "deterministic",
                "model_uncertainty_evidence": {"model_name": "AE-9"},
                "total_dose": 5.0,
                "rdm_factor": 2.0,
            }
        )
        issues = [f["issue"] for f in result["findings"]]
        self.assertIn("missing_model_uncertainty_evidence", issues)
        self.assertFalse(em.is_margin_compliant(result))

    def test_unrecognized_orbit_raises(self):
        with self.assertRaises(ValueError):
            em.assess_margins(
                {
                    "item_id": "x",
                    "orbit_type": "polar_interplanetary",
                    "trapped_electron_model": "ae8",
                    "use_worst_case_geo": False,
                    "margin_approach": "deterministic",
                    "model_uncertainty_evidence": self._good_evidence(),
                    "total_dose": 10.0,
                    "rdm_factor": 2.0,
                }
            )

    def test_unrecognized_approach_raises(self):
        with self.assertRaises(ValueError):
            em.assess_margins(
                {
                    "item_id": "x",
                    "orbit_type": "geo",
                    "trapped_electron_model": "ae8",
                    "use_worst_case_geo": True,
                    "margin_approach": "optimistic",
                    "model_uncertainty_evidence": self._good_evidence(),
                    "total_dose": 10.0,
                    "rdm_factor": 2.0,
                }
            )

    def test_geo_exemption_not_applied_to_heo(self):
        result = em.assess_margins(
            {
                "item_id": "heo-payload",
                "orbit_type": "heo",
                "trapped_electron_model": "ae8_max",
                "use_worst_case_geo": True,
                "margin_approach": "deterministic",
                "model_uncertainty_evidence": self._good_evidence(),
                "total_dose": 25.0,
                "rdm_factor": 2.0,
            }
        )
        self.assertFalse(result["geo_exemption_applies"])
        self.assertEqual(result["findings"], [])

    def test_is_margin_compliant_false_when_findings_present(self):
        result = {"findings": [{"issue": "missing_total_dose", "item": "x"}]}
        self.assertFalse(em.is_margin_compliant(result))

    def test_is_margin_compliant_true_for_empty_findings(self):
        result = {"findings": []}
        self.assertTrue(em.is_margin_compliant(result))


if __name__ == "__main__":
    unittest.main(verbosity=2)
