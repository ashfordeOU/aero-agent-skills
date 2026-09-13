#!/usr/bin/env python3
"""Gate 3 contract test for the ECSS-E-ST-20C clause 7.2.1.2.1 antenna
terminology definitions leaf. Stdlib unittest, offline, deterministic."""

import unittest

import e20_antenna_terminology_definitions_logic as term


def nominal_project():
    """A project pinned to one recognised vocabulary and using it."""
    return {
        "declared_sources": ["ieee-std-145"],
        "documents": [
            {
                "document_id": "ANT-SPEC-001",
                "terms": [
                    "antenna-gain",
                    "half-power-beamwidth",
                    "boresight",
                    "axial-ratio",
                    "radiation-pattern",
                ],
            },
            {
                "document_id": "ANT-RPT-002",
                "terms": [
                    "directivity",
                    "side-lobe-level",
                    "radiation-efficiency",
                    "aperture-efficiency",
                ],
            },
        ],
        "glossary": {"antenna-gain": {"source": "ieee-std-145", "unit": "dBi"}},
    }


class NormalizationTests(unittest.TestCase):
    def test_spaces_become_hyphens_and_case_is_folded(self):
        self.assertEqual(term.normalize_term("  Half Power Beamwidth "), "half-power-beamwidth")

    def test_underscores_become_hyphens(self):
        self.assertEqual(term.normalize_term("axial_ratio"), "axial-ratio")

    def test_canonical_form_is_unchanged(self):
        self.assertEqual(term.normalize_term("antenna-gain"), "antenna-gain")

    def test_mixed_separators_collapse(self):
        self.assertEqual(term.normalize_term("cross polar_discrimination"), "cross-polar-discrimination")

    def test_non_string_term_is_rejected(self):
        with self.assertRaises(ValueError):
            term.normalize_term(42)

    def test_blank_term_is_rejected(self):
        with self.assertRaises(ValueError):
            term.normalize_term("   ")


class ResolutionTests(unittest.TestCase):
    def test_canonical_term_resolves_to_itself(self):
        resolution = term.resolve_term("antenna-gain")
        self.assertEqual(resolution["status"], term.STATUS_CANONICAL)
        self.assertEqual(resolution["canonical"], "antenna-gain")

    def test_canonical_term_carries_source_and_unit(self):
        resolution = term.resolve_term("axial-ratio")
        self.assertEqual(resolution["source"], "ieee-std-145")
        self.assertEqual(resolution["unit"], "dB")

    def test_deprecated_synonym_maps_onto_its_canonical_form(self):
        resolution = term.resolve_term("ellipticity-ratio")
        self.assertEqual(resolution["status"], term.STATUS_DEPRECATED_SYNONYM)
        self.assertEqual(resolution["canonical"], "axial-ratio")

    def test_synonym_written_with_spaces_still_resolves(self):
        resolution = term.resolve_term("3 dB beamwidth")
        self.assertEqual(resolution["canonical"], "half-power-beamwidth")

    def test_synonym_inherits_the_canonical_unit(self):
        resolution = term.resolve_term("eirp")
        self.assertEqual(resolution["unit"], "dBW")

    def test_unknown_term_is_uncategorized(self):
        resolution = term.resolve_term("gain-slope")
        self.assertEqual(resolution["status"], term.STATUS_UNCATEGORIZED)
        self.assertIsNone(resolution["canonical"])

    def test_every_synonym_target_exists_in_the_registry(self):
        for canonical in term.DEPRECATED_SYNONYMS.values():
            self.assertIn(canonical, term.CANONICAL_TERMS)

    def test_every_registry_entry_names_a_recognised_vocabulary(self):
        for entry in term.CANONICAL_TERMS.values():
            self.assertIn(entry["source"], term.RECOGNIZED_TERMINOLOGY_SOURCES)

    def test_no_synonym_shadows_a_canonical_term(self):
        for synonym in term.DEPRECATED_SYNONYMS:
            self.assertNotIn(synonym, term.CANONICAL_TERMS)

    def test_non_string_term_is_rejected(self):
        with self.assertRaises(ValueError):
            term.resolve_term(None)


class SourceDeclarationTests(unittest.TestCase):
    def test_single_recognised_source_is_valid(self):
        review = term.validate_terminology_source(["ieee-std-145"])
        self.assertTrue(review["valid"])
        self.assertEqual(review["source"], "ieee-std-145")

    def test_declared_name_is_normalised(self):
        review = term.validate_terminology_source([" IEEE STD 145 "])
        self.assertEqual(review["source"], "ieee-std-145")

    def test_no_declared_source_is_a_finding(self):
        review = term.validate_terminology_source([])
        self.assertFalse(review["valid"])
        self.assertIsNone(review["source"])

    def test_two_declared_sources_are_a_finding(self):
        review = term.validate_terminology_source(["ieee-std-145", "itu-r-v-573"])
        self.assertFalse(review["valid"])
        self.assertIsNone(review["source"])

    def test_unrecognised_vocabulary_is_a_finding(self):
        review = term.validate_terminology_source(["project-antenna-handbook"])
        self.assertFalse(review["valid"])
        self.assertIsNone(review["source"])

    def test_string_argument_is_rejected(self):
        with self.assertRaises(ValueError):
            term.validate_terminology_source("ieee-std-145")

    def test_non_string_member_is_rejected(self):
        with self.assertRaises(ValueError):
            term.validate_terminology_source([145])

    def test_empty_name_is_rejected(self):
        with self.assertRaises(ValueError):
            term.validate_terminology_source(["  "])


class DocumentScanTests(unittest.TestCase):
    def test_all_canonical_document_is_conformant(self):
        review = term.scan_document_terms(
            {"document_id": "D1", "terms": ["antenna-gain", "directivity"]},
            "ieee-std-145",
        )
        self.assertTrue(review["conformant"])
        self.assertEqual(review["nonconforming_count"], 0)

    def test_term_count_is_the_occurrence_count(self):
        review = term.scan_document_terms(
            {"document_id": "D1", "terms": ["antenna-gain", "antenna-gain", "directivity"]},
            "ieee-std-145",
        )
        self.assertEqual(review["term_count"], 3)
        self.assertEqual(review["conforming_count"], 3)

    def test_deprecated_synonym_is_flagged_with_its_replacement(self):
        review = term.scan_document_terms(
            {"document_id": "D1", "terms": ["aerial-gain"]}, "ieee-std-145"
        )
        self.assertFalse(review["conformant"])
        self.assertTrue(any("antenna-gain" in f for f in review["findings"]))

    def test_uncategorized_term_is_flagged(self):
        review = term.scan_document_terms(
            {"document_id": "D1", "terms": ["gain-slope"]}, "ieee-std-145"
        )
        self.assertEqual(review["nonconforming_count"], 1)
        self.assertTrue(any("uncategorized" in f for f in review["findings"]))

    def test_term_from_another_vocabulary_is_flagged(self):
        review = term.scan_document_terms(
            {"document_id": "D1", "terms": ["cross-polar-discrimination"]}, "ieee-std-145"
        )
        self.assertFalse(review["conformant"])
        self.assertTrue(any("itu-r-v-573" in f for f in review["findings"]))

    def test_without_a_declared_source_the_vocabulary_check_is_skipped(self):
        review = term.scan_document_terms(
            {"document_id": "D1", "terms": ["cross-polar-discrimination"]}, None
        )
        self.assertTrue(review["conformant"])

    def test_each_occurrence_counts_separately(self):
        review = term.scan_document_terms(
            {"document_id": "D1", "terms": ["hpbw", "hpbw", "antenna-gain"]}, "ieee-std-145"
        )
        self.assertEqual(review["nonconforming_count"], 2)
        self.assertEqual(review["conforming_count"], 1)

    def test_non_mapping_document_is_rejected(self):
        with self.assertRaises(ValueError):
            term.scan_document_terms(["antenna-gain"], "ieee-std-145")

    def test_document_without_an_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            term.scan_document_terms({"terms": ["antenna-gain"]}, "ieee-std-145")

    def test_document_with_no_terms_is_rejected(self):
        with self.assertRaises(ValueError):
            term.scan_document_terms({"document_id": "D1", "terms": []}, "ieee-std-145")

    def test_terms_given_as_a_string_are_rejected(self):
        with self.assertRaises(ValueError):
            term.scan_document_terms({"document_id": "D1", "terms": "antenna-gain"}, None)

    def test_unrecognised_declared_source_is_rejected(self):
        with self.assertRaises(ValueError):
            term.scan_document_terms(
                {"document_id": "D1", "terms": ["antenna-gain"]}, "house-vocabulary"
            )


class GlossaryTests(unittest.TestCase):
    def test_agreeing_entry_is_consistent(self):
        review = term.check_glossary_entry(
            "antenna-gain", {"source": "ieee-std-145", "unit": "dBi"}, "ieee-std-145"
        )
        self.assertTrue(review["consistent"])

    def test_contradicting_unit_is_flagged(self):
        review = term.check_glossary_entry(
            "axial-ratio", {"source": "ieee-std-145", "unit": "degree"}, "ieee-std-145"
        )
        self.assertFalse(review["consistent"])
        self.assertTrue(any("degree" in f for f in review["findings"]))

    def test_contradicting_vocabulary_is_flagged(self):
        review = term.check_glossary_entry(
            "antenna-gain", {"source": "itu-r-v-573", "unit": "dBi"}, "ieee-std-145"
        )
        self.assertFalse(review["consistent"])

    def test_entry_keyed_on_a_synonym_is_flagged(self):
        review = term.check_glossary_entry(
            "eirp", {"source": "itu-r-v-573", "unit": "dBW"}, "itu-r-v-573"
        )
        self.assertFalse(review["consistent"])
        self.assertEqual(review["canonical"], "effective-isotropic-radiated-power")

    def test_entry_for_an_unknown_term_is_flagged(self):
        review = term.check_glossary_entry(
            "gain-slope", {"source": "ieee-std-145", "unit": "dB"}, "ieee-std-145"
        )
        self.assertFalse(review["consistent"])

    def test_entry_outside_the_declared_vocabulary_is_flagged(self):
        review = term.check_glossary_entry(
            "voltage-standing-wave-ratio",
            {"source": "iec-60050-712", "unit": "ratio"},
            "ieee-std-145",
        )
        self.assertFalse(review["consistent"])
        self.assertTrue(any("declared" in f for f in review["findings"]))

    def test_non_mapping_entry_is_rejected(self):
        with self.assertRaises(ValueError):
            term.check_glossary_entry("antenna-gain", "dBi")

    def test_entry_missing_a_unit_is_rejected(self):
        with self.assertRaises(ValueError):
            term.check_glossary_entry("antenna-gain", {"source": "ieee-std-145"})

    def test_entry_with_an_empty_source_is_rejected(self):
        with self.assertRaises(ValueError):
            term.check_glossary_entry("antenna-gain", {"source": "  ", "unit": "dBi"})


class ConformanceRatioTests(unittest.TestCase):
    def test_no_deviation_gives_a_unit_ratio(self):
        self.assertAlmostEqual(term.terminology_conformance_ratio(40, 0), 1.0)

    def test_one_deviation_in_twenty(self):
        self.assertAlmostEqual(term.terminology_conformance_ratio(20, 1), 0.95)

    def test_every_occurrence_deviating_gives_zero(self):
        self.assertAlmostEqual(term.terminology_conformance_ratio(12, 12), 0.0)

    def test_zero_occurrences_is_rejected(self):
        with self.assertRaises(ValueError):
            term.terminology_conformance_ratio(0, 0)

    def test_more_deviations_than_occurrences_is_rejected(self):
        with self.assertRaises(ValueError):
            term.terminology_conformance_ratio(10, 11)

    def test_negative_count_is_rejected(self):
        with self.assertRaises(ValueError):
            term.terminology_conformance_ratio(10, -1)

    def test_non_integer_count_is_rejected(self):
        with self.assertRaises(ValueError):
            term.terminology_conformance_ratio(10.5, 1)


class ConformanceAssessmentTests(unittest.TestCase):
    def test_ratio_above_the_threshold_passes(self):
        assessment = term.assess_terminology_conformance(0.99)
        self.assertTrue(assessment["meets_threshold"])
        self.assertAlmostEqual(assessment["shortfall"], 0.0)

    def test_ratio_exactly_on_the_threshold_passes_despite_round_off(self):
        # 1 - 7/100 evaluates a few units in the last place below 0.93;
        # the threshold is not lowered, the representation error is absorbed.
        ratio = term.terminology_conformance_ratio(100, 7)
        self.assertLess(ratio, 0.93)
        assessment = term.assess_terminology_conformance(ratio, 0.93)
        self.assertTrue(assessment["meets_threshold"])
        self.assertAlmostEqual(assessment["shortfall"], 0.0)

    def test_ratio_below_the_threshold_reports_the_shortfall(self):
        assessment = term.assess_terminology_conformance(0.90, 0.95)
        self.assertFalse(assessment["meets_threshold"])
        self.assertAlmostEqual(assessment["shortfall"], 0.05)

    def test_ratio_above_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            term.assess_terminology_conformance(1.2)

    def test_zero_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            term.assess_terminology_conformance(0.99, 0.0)

    def test_non_numeric_ratio_is_rejected(self):
        with self.assertRaises(ValueError):
            term.assess_terminology_conformance("0.99")


class ProjectReviewTests(unittest.TestCase):
    def test_nominal_project_is_conformant(self):
        review = term.review_project_terminology(nominal_project())
        self.assertTrue(review["conformant"])
        self.assertEqual(review["findings"], [])

    def test_nominal_project_counts_every_occurrence(self):
        review = term.review_project_terminology(nominal_project())
        self.assertEqual(review["term_count"], 9)
        self.assertEqual(review["nonconforming_count"], 0)
        self.assertAlmostEqual(review["conformance"]["ratio"], 1.0)

    def test_a_synonym_in_one_document_breaks_conformance(self):
        project = nominal_project()
        project["documents"][0]["terms"].append("electrical-axis")
        review = term.review_project_terminology(project)
        self.assertFalse(review["conformant"])
        self.assertEqual(review["nonconforming_count"], 1)

    def test_two_declared_vocabularies_are_reported(self):
        project = nominal_project()
        project["declared_sources"] = ["ieee-std-145", "iec-60050-712"]
        review = term.review_project_terminology(project)
        self.assertFalse(review["conformant"])
        self.assertFalse(review["source"]["valid"])

    def test_glossary_contradiction_is_reported(self):
        project = nominal_project()
        project["glossary"]["antenna-gain"] = {"source": "ieee-std-145", "unit": "ratio"}
        review = term.review_project_terminology(project)
        self.assertFalse(review["conformant"])
        self.assertTrue(any("registry uses dBi" in f for f in review["findings"]))

    def test_threshold_breach_is_reported_as_its_own_finding(self):
        project = nominal_project()
        project["documents"][0]["terms"] = ["hpbw", "swr", "gain-slope", "antenna-gain"]
        review = term.review_project_terminology(project)
        self.assertFalse(review["conformance"]["meets_threshold"])
        self.assertTrue(
            any("terminology-conformance-ratio" in f for f in review["findings"])
        )

    def test_missing_required_key_is_rejected(self):
        project = nominal_project()
        del project["documents"]
        with self.assertRaises(ValueError):
            term.review_project_terminology(project)

    def test_empty_document_set_is_rejected(self):
        project = nominal_project()
        project["documents"] = []
        with self.assertRaises(ValueError):
            term.review_project_terminology(project)

    def test_non_mapping_project_is_rejected(self):
        with self.assertRaises(ValueError):
            term.review_project_terminology(["ANT-SPEC-001"])

    def test_non_mapping_glossary_is_rejected(self):
        project = nominal_project()
        project["glossary"] = ["antenna-gain"]
        with self.assertRaises(ValueError):
            term.review_project_terminology(project)

    def test_undeclared_source_still_flags_synonyms(self):
        project = nominal_project()
        project["declared_sources"] = []
        project["documents"][0]["terms"].append("beam-peak")
        review = term.review_project_terminology(project)
        self.assertFalse(review["conformant"])
        self.assertTrue(any("beam-peak" in f for f in review["findings"]))


if __name__ == "__main__":
    unittest.main()
