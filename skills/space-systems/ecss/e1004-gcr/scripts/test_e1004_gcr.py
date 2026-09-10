#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 9.2.3 galactic cosmic
ray (GCR) model selection and solar modulation.

Exercises scripts/e1004_gcr_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the GCR model is selected
from the analysis type (SEE vs. dose); species coverage is adequate
only when it meets the analysis type's minimum ion charge number; a
modulation potential at or below the solar-minimum reference is
categorized solar_minimum, at or above the solar-maximum reference is
categorized solar_maximum, otherwise intermediate; solar modulation
scales the solar-minimum reference flux inversely with the modulation
potential; an SEE case is compliant only when its species coverage is
adequate and its solar condition is solar_minimum; a dose case is
compliant when its species coverage is adequate; the assessment record
covers every case with no duplicates and is reported all-compliant
only when every case is compliant.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_gcr_logic as gl  # noqa: E402


class SelectGcrModelTest(unittest.TestCase):
    def test_see_model(self):
        self.assertEqual(gl.select_gcr_model("see"), gl.MODEL_BY_ANALYSIS_TYPE["see"])

    def test_dose_model(self):
        self.assertEqual(
            gl.select_gcr_model("dose"), gl.MODEL_BY_ANALYSIS_TYPE["dose"]
        )

    def test_unknown_analysis_type_raises(self):
        with self.assertRaises(ValueError):
            gl.select_gcr_model("shielding")


class RequiredMaxSpeciesZTest(unittest.TestCase):
    def test_see_requires_full_heavy_ion_set(self):
        self.assertEqual(gl.required_max_species_z("see"), 92)

    def test_dose_requires_narrower_set(self):
        self.assertEqual(gl.required_max_species_z("dose"), 28)

    def test_unknown_analysis_type_raises(self):
        with self.assertRaises(ValueError):
            gl.required_max_species_z("shielding")


class SpeciesCoverageAdequateTest(unittest.TestCase):
    def test_exact_coverage_is_adequate(self):
        self.assertTrue(gl.species_coverage_adequate("dose", 28))

    def test_wider_coverage_is_adequate(self):
        self.assertTrue(gl.species_coverage_adequate("see", 92))

    def test_narrower_coverage_is_not_adequate(self):
        self.assertFalse(gl.species_coverage_adequate("see", 26))


class WorstCaseSolarConditionTest(unittest.TestCase):
    def test_see_requires_solar_minimum(self):
        self.assertEqual(gl.worst_case_solar_condition("see"), "solar_minimum")

    def test_dose_requires_cycle_average(self):
        self.assertEqual(
            gl.worst_case_solar_condition("dose"), "mission_cycle_average"
        )

    def test_unknown_analysis_type_raises(self):
        with self.assertRaises(ValueError):
            gl.worst_case_solar_condition("shielding")


class ClassifySolarConditionTest(unittest.TestCase):
    def test_at_or_below_minimum_reference_is_solar_minimum(self):
        self.assertEqual(gl.classify_solar_condition(500.0), "solar_minimum")
        self.assertEqual(gl.classify_solar_condition(300.0), "solar_minimum")

    def test_at_or_above_maximum_reference_is_solar_maximum(self):
        self.assertEqual(gl.classify_solar_condition(1100.0), "solar_maximum")
        self.assertEqual(gl.classify_solar_condition(1400.0), "solar_maximum")

    def test_between_references_is_intermediate(self):
        self.assertEqual(gl.classify_solar_condition(800.0), "intermediate")

    def test_non_positive_potential_raises(self):
        with self.assertRaises(ValueError):
            gl.classify_solar_condition(0.0)
        with self.assertRaises(ValueError):
            gl.classify_solar_condition(-10.0)


class ModulationScaleFactorTest(unittest.TestCase):
    def test_reference_potential_gives_unit_scale(self):
        self.assertEqual(gl.modulation_scale_factor(gl.SOLAR_MIN_POTENTIAL_MV), 1.0)

    def test_higher_potential_reduces_scale(self):
        self.assertLess(gl.modulation_scale_factor(1000.0), 1.0)

    def test_lower_potential_raises_scale_above_one(self):
        self.assertGreater(gl.modulation_scale_factor(250.0), 1.0)

    def test_non_positive_potential_raises(self):
        with self.assertRaises(ValueError):
            gl.modulation_scale_factor(0.0)


class ApplySolarModulationTest(unittest.TestCase):
    def test_scales_reference_flux(self):
        self.assertAlmostEqual(
            gl.apply_solar_modulation(100.0, 500.0), 100.0
        )
        self.assertAlmostEqual(
            gl.apply_solar_modulation(100.0, 1000.0), 50.0
        )

    def test_negative_reference_flux_raises(self):
        with self.assertRaises(ValueError):
            gl.apply_solar_modulation(-1.0, 500.0)


class AssessGcrCaseTest(unittest.TestCase):
    def test_compliant_see_case_at_solar_minimum(self):
        case = {
            "id": "GCR-001",
            "analysis_type": "see",
            "species_max_z": 92,
            "modulation_potential": 400.0,
            "reference_flux": 10.0,
        }
        result = gl.assess_gcr_case(case)
        self.assertEqual(result["model"], gl.MODEL_BY_ANALYSIS_TYPE["see"])
        self.assertTrue(result["species_coverage_adequate"])
        self.assertEqual(result["solar_condition"], "solar_minimum")
        self.assertTrue(result["solar_condition_adequate"])
        self.assertTrue(result["compliant"])

    def test_noncompliant_see_case_at_solar_maximum(self):
        case = {
            "id": "GCR-002",
            "analysis_type": "see",
            "species_max_z": 92,
            "modulation_potential": 1200.0,
            "reference_flux": 10.0,
        }
        result = gl.assess_gcr_case(case)
        self.assertEqual(result["solar_condition"], "solar_maximum")
        self.assertFalse(result["solar_condition_adequate"])
        self.assertFalse(result["compliant"])

    def test_noncompliant_see_case_with_insufficient_species(self):
        case = {
            "id": "GCR-003",
            "analysis_type": "see",
            "species_max_z": 26,
            "modulation_potential": 450.0,
            "reference_flux": 10.0,
        }
        result = gl.assess_gcr_case(case)
        self.assertFalse(result["species_coverage_adequate"])
        self.assertFalse(result["compliant"])

    def test_compliant_dose_case_regardless_of_solar_condition(self):
        case = {
            "id": "GCR-004",
            "analysis_type": "dose",
            "species_max_z": 28,
            "modulation_potential": 900.0,
            "reference_flux": 5.0,
        }
        result = gl.assess_gcr_case(case)
        self.assertEqual(result["solar_condition"], "intermediate")
        self.assertTrue(result["solar_condition_adequate"])
        self.assertTrue(result["compliant"])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            gl.assess_gcr_case({
                "analysis_type": "dose",
                "species_max_z": 28,
                "modulation_potential": 500.0,
                "reference_flux": 5.0,
            })

    def test_unknown_analysis_type_raises(self):
        with self.assertRaises(ValueError):
            gl.assess_gcr_case({
                "id": "GCR-005",
                "analysis_type": "shielding",
                "species_max_z": 28,
                "modulation_potential": 500.0,
                "reference_flux": 5.0,
            })


class BuildGcrAssessmentTest(unittest.TestCase):
    CASES = [
        {
            "id": "GCR-001",
            "analysis_type": "see",
            "species_max_z": 92,
            "modulation_potential": 400.0,
            "reference_flux": 10.0,
        },
        {
            "id": "GCR-002",
            "analysis_type": "see",
            "species_max_z": 92,
            "modulation_potential": 1200.0,
            "reference_flux": 10.0,
        },
    ]

    def test_record_order_and_status(self):
        record = gl.build_gcr_assessment(self.CASES)
        self.assertEqual(record[0]["id"], "GCR-001")
        self.assertTrue(record[0]["compliant"])
        self.assertEqual(record[1]["id"], "GCR-002")
        self.assertFalse(record[1]["compliant"])

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            gl.build_gcr_assessment(self.CASES + [self.CASES[0]])

    def test_does_not_mutate_input(self):
        before = [dict(c) for c in self.CASES]
        gl.build_gcr_assessment(self.CASES)
        self.assertEqual(self.CASES, before)


class RecordSummaryTest(unittest.TestCase):
    def test_noncompliant_items(self):
        record = gl.build_gcr_assessment(BuildGcrAssessmentTest.CASES)
        self.assertEqual(gl.noncompliant_items(record), ["GCR-002"])

    def test_all_compliant_true_when_all_pass(self):
        record = gl.build_gcr_assessment([BuildGcrAssessmentTest.CASES[0]])
        self.assertTrue(gl.all_compliant(record))

    def test_all_compliant_false_when_any_fail(self):
        record = gl.build_gcr_assessment(BuildGcrAssessmentTest.CASES)
        self.assertFalse(gl.all_compliant(record))


if __name__ == "__main__":
    unittest.main(verbosity=2)
