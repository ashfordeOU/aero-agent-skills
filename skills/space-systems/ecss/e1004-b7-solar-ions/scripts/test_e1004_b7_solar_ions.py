#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C Annex B.7 solar energetic ion
spectra (heavy ions, Z-dependent abundances) for SEE analysis.

Exercises scripts/e1004_b7_solar_ions_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - an event's Fe/O
ratio categorizes it as gradual at or below the gradual threshold,
impulsive at or above the impulsive threshold, mixed in between, and a
negative ratio raises; a species' abundance ratio comes from the
gradual or impulsive table for those event types, from the max of both
tables for mixed, and an unrecognized event type or a species absent
from the tables raises; a species' scaled flux is the reference flux
times its abundance ratio, and a negative reference flux raises; a
case's species coverage is checked against the iron-group minimum and
a negative species_max_z raises; a case's event type is flagged only
when gradual; the aggregated review is compliant only when both
categories are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_b7_solar_ions_logic as b7  # noqa: E402


class ClassifyEventTypeTest(unittest.TestCase):
    def test_at_gradual_threshold_is_gradual(self):
        self.assertEqual(b7.classify_event_type(0.1), "gradual")

    def test_below_gradual_threshold_is_gradual(self):
        self.assertEqual(b7.classify_event_type(0.02), "gradual")

    def test_at_impulsive_threshold_is_impulsive(self):
        self.assertEqual(b7.classify_event_type(1.0), "impulsive")

    def test_above_impulsive_threshold_is_impulsive(self):
        self.assertEqual(b7.classify_event_type(3.0), "impulsive")

    def test_between_thresholds_is_mixed(self):
        self.assertEqual(b7.classify_event_type(0.5), "mixed")

    def test_negative_ratio_raises(self):
        with self.assertRaises(ValueError):
            b7.classify_event_type(-0.1)


class AbundanceRatioTest(unittest.TestCase):
    def test_gradual_iron_ratio(self):
        self.assertAlmostEqual(b7.abundance_ratio(26, "gradual"), 0.1)

    def test_impulsive_iron_ratio(self):
        self.assertAlmostEqual(b7.abundance_ratio(26, "impulsive"), 1.0)

    def test_reference_species_ratio_is_one(self):
        self.assertAlmostEqual(
            b7.abundance_ratio(b7.REFERENCE_SPECIES_Z, "gradual"), 1.0
        )
        self.assertAlmostEqual(
            b7.abundance_ratio(b7.REFERENCE_SPECIES_Z, "impulsive"), 1.0
        )

    def test_mixed_is_envelope_max(self):
        # Fe: gradual 0.1, impulsive 1.0 -> mixed 1.0
        self.assertAlmostEqual(b7.abundance_ratio(26, "mixed"), 1.0)
        # H: gradual 50.0, impulsive 10.0 -> mixed 50.0
        self.assertAlmostEqual(b7.abundance_ratio(1, "mixed"), 50.0)

    def test_unrecognized_event_type_raises(self):
        with self.assertRaises(ValueError):
            b7.abundance_ratio(26, "quiescent")

    def test_unknown_species_raises(self):
        with self.assertRaises(ValueError):
            b7.abundance_ratio(92, "gradual")

    def test_unknown_species_raises_for_mixed(self):
        with self.assertRaises(ValueError):
            b7.abundance_ratio(92, "mixed")


class ScaleElementSpectrumTest(unittest.TestCase):
    def test_scales_by_abundance_ratio(self):
        flux = b7.scale_element_spectrum(100.0, 26, "impulsive")
        self.assertAlmostEqual(flux, 100.0)  # ratio 1.0

    def test_scales_down_for_gradual_iron(self):
        flux = b7.scale_element_spectrum(100.0, 26, "gradual")
        self.assertAlmostEqual(flux, 10.0)  # ratio 0.1

    def test_negative_reference_flux_raises(self):
        with self.assertRaises(ValueError):
            b7.scale_element_spectrum(-1.0, 26, "impulsive")


class BuildHeavyIonSpectraTest(unittest.TestCase):
    def test_builds_per_species_spectra(self):
        reference_spectrum = [10.0, 20.0]
        spectra = b7.build_heavy_ion_spectra(reference_spectrum, [8, 26], "impulsive")
        self.assertEqual(spectra[8], [10.0, 20.0])  # O ratio 1.0
        self.assertEqual(spectra[26], [10.0, 20.0])  # Fe ratio 1.0 (impulsive)

    def test_does_not_mutate_reference_spectrum(self):
        reference_spectrum = [5.0, 15.0]
        b7.build_heavy_ion_spectra(reference_spectrum, [26], "gradual")
        self.assertEqual(reference_spectrum, [5.0, 15.0])


class SpeciesCoverageViolationsTest(unittest.TestCase):
    def test_sufficient_coverage_no_violation(self):
        self.assertEqual(b7.species_coverage_violations("case-1", 28), [])

    def test_coverage_above_minimum_no_violation(self):
        self.assertEqual(b7.species_coverage_violations("case-1", 40), [])

    def test_insufficient_coverage_flagged(self):
        violations = b7.species_coverage_violations("case-1", 20)
        self.assertEqual(
            violations,
            [
                {
                    "issue": "insufficient_heavy_ion_species_coverage",
                    "case": "case-1",
                    "species_max_z": 20,
                    "required_species_max_z": 28,
                }
            ],
        )

    def test_negative_species_max_z_raises(self):
        with self.assertRaises(ValueError):
            b7.species_coverage_violations("case-1", -1)


class EventClassViolationsTest(unittest.TestCase):
    def test_gradual_flagged(self):
        violations = b7.event_class_violations("case-1", "gradual")
        self.assertEqual(
            violations,
            [
                {
                    "issue": "gradual_event_insufficient_for_see_worst_case",
                    "case": "case-1",
                    "event_type": "gradual",
                }
            ],
        )

    def test_impulsive_not_flagged(self):
        self.assertEqual(b7.event_class_violations("case-1", "impulsive"), [])

    def test_mixed_not_flagged(self):
        self.assertEqual(b7.event_class_violations("case-1", "mixed"), [])

    def test_unrecognized_event_type_raises(self):
        with self.assertRaises(ValueError):
            b7.event_class_violations("case-1", "quiescent")


class AnnexB7ReviewTest(unittest.TestCase):
    def test_fully_compliant_review(self):
        case = {"case_id": "case-1", "species_max_z": 28, "fe_o_ratio": 2.0}
        review = b7.annex_b7_review(case)
        self.assertEqual(review["species"], [])
        self.assertEqual(review["event_class"], [])
        self.assertEqual(review["event_type"], "impulsive")
        self.assertTrue(b7.is_annex_b7_compliant(review))

    def test_review_flags_insufficient_species_coverage(self):
        case = {"case_id": "case-2", "species_max_z": 18, "fe_o_ratio": 2.0}
        review = b7.annex_b7_review(case)
        self.assertTrue(review["species"])
        self.assertEqual(review["event_class"], [])
        self.assertFalse(b7.is_annex_b7_compliant(review))

    def test_review_flags_gradual_event(self):
        case = {"case_id": "case-3", "species_max_z": 28, "fe_o_ratio": 0.05}
        review = b7.annex_b7_review(case)
        self.assertEqual(review["species"], [])
        self.assertTrue(review["event_class"])
        self.assertEqual(review["event_type"], "gradual")
        self.assertFalse(b7.is_annex_b7_compliant(review))

    def test_review_surfaces_both_categories_independently(self):
        case = {"case_id": "case-4", "species_max_z": 10, "fe_o_ratio": 0.01}
        review = b7.annex_b7_review(case)
        self.assertTrue(review["species"])
        self.assertTrue(review["event_class"])
        self.assertFalse(b7.is_annex_b7_compliant(review))

    def test_review_raises_on_negative_fe_o_ratio(self):
        case = {"case_id": "case-5", "species_max_z": 28, "fe_o_ratio": -1.0}
        with self.assertRaises(ValueError):
            b7.annex_b7_review(case)


if __name__ == "__main__":
    unittest.main(verbosity=2)
