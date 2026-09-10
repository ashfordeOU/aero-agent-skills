#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 7.2 neutral atmosphere
model selection and density scaling.

Exercises scripts/e1004_atmosphere_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the Earth neutral-atmosphere
density model is selected from the case's precision need (NRLMSISE-00
for "standard", JB-2006 for "precision"); a non-Earth target body is
flagged as requiring a planetary model instead of an Earth model; an
altitude within [90, 1000] km is in range and any other altitude is
out of range; an F10.7 value at or below the solar-minimum reference is
categorized "low", at or above the solar-maximum reference is
categorized "high", otherwise "moderate"; density scaling increases
with both F10.7 and Ap; a wind model is selected only when the case
needs wind data; a case is compliant only when its target body is
Earth and its altitude is in range; the assessment record covers every
case with no duplicates and is reported all-compliant only when every
case is compliant.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_atmosphere_logic as al  # noqa: E402


class SelectAtmosphereModelTest(unittest.TestCase):
    def test_standard_model(self):
        self.assertEqual(
            al.select_atmosphere_model("standard"),
            al.MODEL_BY_PRECISION["standard"],
        )

    def test_precision_model(self):
        self.assertEqual(
            al.select_atmosphere_model("precision"),
            al.MODEL_BY_PRECISION["precision"],
        )

    def test_default_is_standard(self):
        self.assertEqual(al.select_atmosphere_model(), al.MODEL_BY_PRECISION["standard"])

    def test_unknown_precision_raises(self):
        with self.assertRaises(ValueError):
            al.select_atmosphere_model("ultra")


class RequiresPlanetaryModelTest(unittest.TestCase):
    def test_earth_does_not_require_planetary_model(self):
        self.assertFalse(al.requires_planetary_model("earth"))
        self.assertFalse(al.requires_planetary_model("Earth"))
        self.assertFalse(al.requires_planetary_model("  EARTH  "))

    def test_other_body_requires_planetary_model(self):
        self.assertTrue(al.requires_planetary_model("mars"))
        self.assertTrue(al.requires_planetary_model("Venus"))


class AltitudeInValidRangeTest(unittest.TestCase):
    def test_within_range_is_valid(self):
        self.assertTrue(al.altitude_in_valid_range(90.0))
        self.assertTrue(al.altitude_in_valid_range(400.0))
        self.assertTrue(al.altitude_in_valid_range(1000.0))

    def test_below_range_is_invalid(self):
        self.assertFalse(al.altitude_in_valid_range(50.0))

    def test_above_range_is_invalid(self):
        self.assertFalse(al.altitude_in_valid_range(1500.0))

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            al.altitude_in_valid_range(-1.0)


class ClassifySolarActivityTest(unittest.TestCase):
    def test_at_or_below_low_reference_is_low(self):
        self.assertEqual(al.classify_solar_activity(70.0), "low")
        self.assertEqual(al.classify_solar_activity(65.0), "low")

    def test_at_or_above_high_reference_is_high(self):
        self.assertEqual(al.classify_solar_activity(200.0), "high")
        self.assertEqual(al.classify_solar_activity(250.0), "high")

    def test_between_references_is_moderate(self):
        self.assertEqual(al.classify_solar_activity(140.0), "moderate")

    def test_non_positive_f107_raises(self):
        with self.assertRaises(ValueError):
            al.classify_solar_activity(0.0)
        with self.assertRaises(ValueError):
            al.classify_solar_activity(-10.0)


class SelectWindModelTest(unittest.TestCase):
    def test_needs_wind_selects_model(self):
        self.assertEqual(al.select_wind_model(True), al.WIND_MODEL_NAME)

    def test_no_wind_need_selects_none(self):
        self.assertIsNone(al.select_wind_model(False))


class DensityScaleFactorTest(unittest.TestCase):
    def test_reference_conditions_give_unit_scale(self):
        self.assertEqual(al.density_scale_factor(al.SOLAR_FLUX_LOW_SFU, 0), 1.0)

    def test_higher_f107_raises_scale(self):
        self.assertGreater(al.density_scale_factor(200.0, 0), 1.0)

    def test_higher_ap_raises_scale(self):
        base = al.density_scale_factor(al.SOLAR_FLUX_LOW_SFU, 0)
        self.assertGreater(al.density_scale_factor(al.SOLAR_FLUX_LOW_SFU, 50), base)

    def test_non_positive_f107_raises(self):
        with self.assertRaises(ValueError):
            al.density_scale_factor(0.0, 0)

    def test_negative_ap_raises(self):
        with self.assertRaises(ValueError):
            al.density_scale_factor(100.0, -1)


class ApplyDensityScalingTest(unittest.TestCase):
    def test_scales_reference_density(self):
        self.assertAlmostEqual(
            al.apply_density_scaling(1.0e-12, al.SOLAR_FLUX_LOW_SFU, 0), 1.0e-12
        )
        self.assertGreater(
            al.apply_density_scaling(1.0e-12, 200.0, 30), 1.0e-12
        )

    def test_negative_reference_density_raises(self):
        with self.assertRaises(ValueError):
            al.apply_density_scaling(-1.0, 100.0, 0)


class AssessAtmosphereCaseTest(unittest.TestCase):
    def test_compliant_earth_case_in_range(self):
        case = {
            "id": "ATM-001",
            "target_body": "earth",
            "altitude_km": 400.0,
            "precision": "standard",
            "f107": 150.0,
            "ap_index": 10,
            "needs_wind": False,
            "reference_density": 1.0e-12,
        }
        result = al.assess_atmosphere_case(case)
        self.assertEqual(result["model"], al.MODEL_BY_PRECISION["standard"])
        self.assertTrue(result["altitude_in_range"])
        self.assertFalse(result["requires_planetary_model"])
        self.assertIsNone(result["wind_model"])
        self.assertIsNotNone(result["scaled_density"])
        self.assertTrue(result["compliant"])

    def test_precision_case_with_wind(self):
        case = {
            "id": "ATM-002",
            "target_body": "Earth",
            "altitude_km": 250.0,
            "precision": "precision",
            "f107": 90.0,
            "ap_index": 5,
            "needs_wind": True,
            "reference_density": 5.0e-11,
        }
        result = al.assess_atmosphere_case(case)
        self.assertEqual(result["model"], al.MODEL_BY_PRECISION["precision"])
        self.assertEqual(result["wind_model"], al.WIND_MODEL_NAME)
        self.assertTrue(result["compliant"])

    def test_non_earth_case_is_noncompliant(self):
        case = {
            "id": "ATM-003",
            "target_body": "mars",
            "altitude_km": 300.0,
            "f107": 100.0,
            "ap_index": 0,
            "reference_density": 1.0e-12,
        }
        result = al.assess_atmosphere_case(case)
        self.assertTrue(result["requires_planetary_model"])
        self.assertIsNone(result["model"])
        self.assertIsNone(result["scaled_density"])
        self.assertFalse(result["compliant"])

    def test_out_of_range_altitude_is_noncompliant(self):
        case = {
            "id": "ATM-004",
            "target_body": "earth",
            "altitude_km": 1500.0,
            "f107": 100.0,
            "ap_index": 0,
            "reference_density": 1.0e-14,
        }
        result = al.assess_atmosphere_case(case)
        self.assertFalse(result["altitude_in_range"])
        self.assertFalse(result["compliant"])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            al.assess_atmosphere_case({
                "target_body": "earth",
                "altitude_km": 400.0,
                "f107": 100.0,
                "ap_index": 0,
                "reference_density": 1.0e-12,
            })

    def test_defaults_apply_when_optional_keys_omitted(self):
        case = {
            "id": "ATM-005",
            "target_body": "earth",
            "altitude_km": 400.0,
            "f107": 100.0,
            "ap_index": 0,
            "reference_density": 1.0e-12,
        }
        result = al.assess_atmosphere_case(case)
        self.assertEqual(result["model"], al.MODEL_BY_PRECISION["standard"])
        self.assertIsNone(result["wind_model"])


class BuildAtmosphereAssessmentTest(unittest.TestCase):
    CASES = [
        {
            "id": "ATM-001",
            "target_body": "earth",
            "altitude_km": 400.0,
            "f107": 150.0,
            "ap_index": 10,
            "reference_density": 1.0e-12,
        },
        {
            "id": "ATM-002",
            "target_body": "mars",
            "altitude_km": 300.0,
            "f107": 100.0,
            "ap_index": 0,
            "reference_density": 1.0e-12,
        },
    ]

    def test_record_order_and_status(self):
        record = al.build_atmosphere_assessment(self.CASES)
        self.assertEqual(record[0]["id"], "ATM-001")
        self.assertTrue(record[0]["compliant"])
        self.assertEqual(record[1]["id"], "ATM-002")
        self.assertFalse(record[1]["compliant"])

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            al.build_atmosphere_assessment(self.CASES + [self.CASES[0]])

    def test_does_not_mutate_input(self):
        before = [dict(c) for c in self.CASES]
        al.build_atmosphere_assessment(self.CASES)
        self.assertEqual(self.CASES, before)


class RecordSummaryTest(unittest.TestCase):
    def test_noncompliant_items(self):
        record = al.build_atmosphere_assessment(BuildAtmosphereAssessmentTest.CASES)
        self.assertEqual(al.noncompliant_items(record), ["ATM-002"])

    def test_all_compliant_true_when_all_pass(self):
        record = al.build_atmosphere_assessment(
            [BuildAtmosphereAssessmentTest.CASES[0]]
        )
        self.assertTrue(al.all_compliant(record))

    def test_all_compliant_false_when_any_fail(self):
        record = al.build_atmosphere_assessment(BuildAtmosphereAssessmentTest.CASES)
        self.assertFalse(al.all_compliant(record))


if __name__ == "__main__":
    unittest.main(verbosity=2)
