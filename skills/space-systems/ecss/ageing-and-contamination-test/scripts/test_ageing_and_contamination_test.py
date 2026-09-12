#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clauses 4.6.3.16–4.6.3.17 ageing
and contamination verification testing.

Exercises scripts/ageing_and_contamination_test_logic.py (stdlib unittest,
offline). Contract: specimen type is categorized as passive_film_coating or
structural_material, and an unrecognized type raises; an ageing condition is
validated for correct type and in-range field values, and an unrecognized type
or out-of-range value raises; property retention ratio is computed as
post / pre, and a non-positive pre-value or negative post-value raises; ageing
compliance holds when retention >= threshold, fails otherwise, and an invalid
threshold raises; contamination exposure returns acceptable or exceeds_allowable
based on the allowable limit, and negative values raise; specimen acceptance
aggregates retention and contamination findings and reports accepted only when
both lists are empty; campaign acceptance requires every specimen to be accepted.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ageing_and_contamination_test_logic as ac  # noqa: E402


class CategorizeSpecimenTest(unittest.TestCase):
    def test_passive_film_coating_is_recognized(self):
        self.assertEqual(
            ac.categorize_specimen("passive_film_coating"), "passive_film_coating"
        )

    def test_structural_material_is_recognized(self):
        self.assertEqual(
            ac.categorize_specimen("structural_material"), "structural_material"
        )

    def test_unrecognized_specimen_type_raises(self):
        with self.assertRaises(ValueError):
            ac.categorize_specimen("mystery_substrate")


class ValidateAgeingConditionTest(unittest.TestCase):
    def test_valid_thermal_cycling(self):
        self.assertTrue(
            ac.validate_ageing_condition(
                {
                    "type": "thermal_cycling",
                    "cycles": 200,
                    "temp_low_c": -120,
                    "temp_high_c": 80,
                }
            )
        )

    def test_thermal_cycling_zero_cycles_raises(self):
        with self.assertRaises(ValueError):
            ac.validate_ageing_condition(
                {
                    "type": "thermal_cycling",
                    "cycles": 0,
                    "temp_low_c": -60,
                    "temp_high_c": 80,
                }
            )

    def test_thermal_cycling_inverted_temps_raises(self):
        with self.assertRaises(ValueError):
            ac.validate_ageing_condition(
                {
                    "type": "thermal_cycling",
                    "cycles": 10,
                    "temp_low_c": 80,
                    "temp_high_c": -60,
                }
            )

    def test_valid_hygrothermal_soak(self):
        self.assertTrue(
            ac.validate_ageing_condition(
                {
                    "type": "hygrothermal_soak",
                    "duration_h": 500,
                    "relative_humidity_percent": 85,
                }
            )
        )

    def test_hygrothermal_soak_zero_duration_raises(self):
        with self.assertRaises(ValueError):
            ac.validate_ageing_condition(
                {
                    "type": "hygrothermal_soak",
                    "duration_h": 0,
                    "relative_humidity_percent": 85,
                }
            )

    def test_hygrothermal_soak_rh_over_100_raises(self):
        with self.assertRaises(ValueError):
            ac.validate_ageing_condition(
                {
                    "type": "hygrothermal_soak",
                    "duration_h": 100,
                    "relative_humidity_percent": 110,
                }
            )

    def test_valid_uv_irradiation(self):
        self.assertTrue(
            ac.validate_ageing_condition({"type": "uv_irradiation", "dose_esh": 1000})
        )

    def test_uv_irradiation_zero_dose_raises(self):
        with self.assertRaises(ValueError):
            ac.validate_ageing_condition({"type": "uv_irradiation", "dose_esh": 0})

    def test_unrecognized_condition_type_raises(self):
        with self.assertRaises(ValueError):
            ac.validate_ageing_condition({"type": "cosmic_ray_soak", "dose": 42})


class ComputePropertyRetentionTest(unittest.TestCase):
    def test_full_retention(self):
        self.assertAlmostEqual(ac.compute_property_retention(100.0, 100.0), 1.0)

    def test_partial_retention(self):
        self.assertAlmostEqual(ac.compute_property_retention(200.0, 170.0), 0.85)

    def test_zero_post_value_is_valid(self):
        self.assertAlmostEqual(ac.compute_property_retention(50.0, 0.0), 0.0)

    def test_non_positive_pre_raises(self):
        with self.assertRaises(ValueError):
            ac.compute_property_retention(0.0, 50.0)

    def test_negative_pre_raises(self):
        with self.assertRaises(ValueError):
            ac.compute_property_retention(-10.0, 50.0)

    def test_negative_post_raises(self):
        with self.assertRaises(ValueError):
            ac.compute_property_retention(100.0, -1.0)


class EvaluateAgeingComplianceTest(unittest.TestCase):
    def test_retention_at_threshold_passes(self):
        self.assertTrue(ac.evaluate_ageing_compliance(0.85, 0.85))

    def test_retention_above_threshold_passes(self):
        self.assertTrue(ac.evaluate_ageing_compliance(0.95, 0.85))

    def test_retention_below_threshold_fails(self):
        self.assertFalse(ac.evaluate_ageing_compliance(0.80, 0.85))

    def test_threshold_of_one_accepted(self):
        self.assertTrue(ac.evaluate_ageing_compliance(1.0, 1.0))

    def test_invalid_zero_threshold_raises(self):
        with self.assertRaises(ValueError):
            ac.evaluate_ageing_compliance(0.90, 0.0)

    def test_invalid_over_one_threshold_raises(self):
        with self.assertRaises(ValueError):
            ac.evaluate_ageing_compliance(0.90, 1.1)


class AssessContaminationExposureTest(unittest.TestCase):
    def test_exposure_within_allowable(self):
        self.assertEqual(
            ac.assess_contamination_exposure(10.0, 20.0), "acceptable"
        )

    def test_exposure_at_allowable_boundary(self):
        self.assertEqual(
            ac.assess_contamination_exposure(20.0, 20.0), "acceptable"
        )

    def test_exposure_exceeds_allowable(self):
        self.assertEqual(
            ac.assess_contamination_exposure(25.0, 20.0), "exceeds_allowable"
        )

    def test_zero_exposure_is_acceptable(self):
        self.assertEqual(
            ac.assess_contamination_exposure(0.0, 5.0), "acceptable"
        )

    def test_negative_exposure_raises(self):
        with self.assertRaises(ValueError):
            ac.assess_contamination_exposure(-1.0, 20.0)

    def test_negative_allowable_raises(self):
        with self.assertRaises(ValueError):
            ac.assess_contamination_exposure(10.0, -5.0)


class CheckSpecimenAcceptanceTest(unittest.TestCase):
    def _make_specimen(self, **overrides):
        base = {
            "specimen_id": "PFC-001",
            "specimen_type": "passive_film_coating",
            "ageing_conditions": [
                {
                    "type": "thermal_cycling",
                    "cycles": 100,
                    "temp_low_c": -60,
                    "temp_high_c": 80,
                }
            ],
            "property_measurements": {
                "adhesion_strength_mpa": {
                    "pre": 30.0,
                    "post": 27.0,
                    "min_retention": 0.85,
                },
            },
            "contamination_exposure_mg_m2": 5.0,
            "contamination_allowable_mg_m2": 10.0,
        }
        base.update(overrides)
        return base

    def test_compliant_specimen_is_accepted(self):
        result = ac.check_specimen_acceptance(self._make_specimen())
        self.assertEqual(result["violations"], [])
        self.assertTrue(result["accepted"])

    def test_retention_failure_is_flagged(self):
        specimen = self._make_specimen(
            property_measurements={
                "adhesion_strength_mpa": {
                    "pre": 30.0,
                    "post": 20.0,
                    "min_retention": 0.85,
                },
            }
        )
        result = ac.check_specimen_acceptance(specimen)
        self.assertEqual(len(result["violations"]), 1)
        self.assertEqual(
            result["violations"][0]["issue"], "property_retention_below_threshold"
        )
        self.assertFalse(result["accepted"])

    def test_contamination_exceedance_is_flagged(self):
        specimen = self._make_specimen(
            contamination_exposure_mg_m2=15.0,
            contamination_allowable_mg_m2=10.0,
        )
        result = ac.check_specimen_acceptance(specimen)
        issues = [v["issue"] for v in result["violations"]]
        self.assertIn("contamination_exposure_exceeds_allowable", issues)
        self.assertFalse(result["accepted"])

    def test_missing_allowable_with_nonzero_exposure_is_flagged(self):
        specimen = self._make_specimen(
            contamination_exposure_mg_m2=5.0,
            contamination_allowable_mg_m2=None,
        )
        result = ac.check_specimen_acceptance(specimen)
        issues = [v["issue"] for v in result["violations"]]
        self.assertIn("missing_contamination_allowable", issues)

    def test_zero_exposure_with_no_allowable_is_not_flagged(self):
        specimen = self._make_specimen(
            contamination_exposure_mg_m2=0.0,
            contamination_allowable_mg_m2=None,
        )
        result = ac.check_specimen_acceptance(specimen)
        contamination_issues = [
            v for v in result["violations"] if "contamination" in v["issue"]
        ]
        self.assertEqual(contamination_issues, [])

    def test_both_failures_are_reported(self):
        specimen = self._make_specimen(
            property_measurements={
                "adhesion_strength_mpa": {
                    "pre": 30.0,
                    "post": 20.0,
                    "min_retention": 0.85,
                },
            },
            contamination_exposure_mg_m2=15.0,
            contamination_allowable_mg_m2=10.0,
        )
        result = ac.check_specimen_acceptance(specimen)
        self.assertEqual(len(result["violations"]), 2)
        self.assertFalse(result["accepted"])

    def test_unrecognized_specimen_type_raises(self):
        specimen = self._make_specimen(specimen_type="exotic_alloy_foam")
        with self.assertRaises(ValueError):
            ac.check_specimen_acceptance(specimen)

    def test_specimen_id_in_result(self):
        result = ac.check_specimen_acceptance(self._make_specimen())
        self.assertEqual(result["specimen_id"], "PFC-001")


class EvaluateTestCampaignTest(unittest.TestCase):
    def _make_compliant_specimen(self, specimen_id):
        return {
            "specimen_id": specimen_id,
            "specimen_type": "structural_material",
            "ageing_conditions": [{"type": "uv_irradiation", "dose_esh": 2000}],
            "property_measurements": {
                "tensile_modulus_gpa": {
                    "pre": 70.0,
                    "post": 65.0,
                    "min_retention": 0.90,
                },
            },
            "contamination_exposure_mg_m2": 3.0,
            "contamination_allowable_mg_m2": 8.0,
        }

    def test_all_compliant_campaign_is_accepted(self):
        specimens = [
            self._make_compliant_specimen("SM-001"),
            self._make_compliant_specimen("SM-002"),
        ]
        results = ac.evaluate_test_campaign(specimens)
        self.assertTrue(ac.is_campaign_accepted(results))

    def test_campaign_fails_when_one_specimen_fails(self):
        failing = {
            "specimen_id": "SM-003",
            "specimen_type": "structural_material",
            "ageing_conditions": [{"type": "uv_irradiation", "dose_esh": 2000}],
            "property_measurements": {
                "tensile_modulus_gpa": {
                    "pre": 70.0,
                    "post": 55.0,
                    "min_retention": 0.90,
                },
            },
            "contamination_exposure_mg_m2": 0.0,
            "contamination_allowable_mg_m2": 8.0,
        }
        specimens = [self._make_compliant_specimen("SM-001"), failing]
        results = ac.evaluate_test_campaign(specimens)
        self.assertFalse(ac.is_campaign_accepted(results))

    def test_empty_campaign_is_accepted(self):
        results = ac.evaluate_test_campaign([])
        self.assertTrue(ac.is_campaign_accepted(results))

    def test_campaign_result_count_matches_specimen_count(self):
        specimens = [
            self._make_compliant_specimen("SM-A"),
            self._make_compliant_specimen("SM-B"),
            self._make_compliant_specimen("SM-C"),
        ]
        results = ac.evaluate_test_campaign(specimens)
        self.assertEqual(len(results), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
