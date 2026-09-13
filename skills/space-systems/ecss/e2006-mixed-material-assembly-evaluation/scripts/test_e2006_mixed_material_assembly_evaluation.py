#!/usr/bin/env python3
"""Contract tests for the clause 6.3.3.4 mixed-material assembly leaf."""

import math
import unittest

from e2006_mixed_material_assembly_evaluation_logic import (
    CATEGORY_EXPOSED_DIELECTRIC,
    CATEGORY_FLOATING_CONDUCTOR,
    CATEGORY_GROUNDED_CONDUCTOR,
    CONDUCTIVE_CEILING_OHM_SQ,
    DECADE_SPAN_LIMIT,
    EVIDENCE_LEVEL_CONSTITUENT,
    EVIDENCE_LEVEL_UNIT,
    categorize_assembly,
    categorize_constituent,
    evaluate_mixed_material_assembly,
    evidence_findings,
    is_mixed_material_assembly,
    pairwise_decade_span,
    required_evidence_level,
    resistivity_decades,
    ungrounded_constituents,
    validate_evidence,
)


def conductor(name, resistivity=1.0e2, grounded=True, area=0.2):
    return {
        "name": name,
        "surface_resistivity_ohm_sq": resistivity,
        "grounded": grounded,
        "exposed_area_m2": area,
    }


def dielectric(name, resistivity=1.0e12, area=0.2):
    return {
        "name": name,
        "surface_resistivity_ohm_sq": resistivity,
        "grounded": False,
        "exposed_area_m2": area,
    }


def evidence(**overrides):
    record = {
        "method": "assembly-qualification",
        "coverage": "complete-unit",
        "specimen_representative": True,
        "envelope_bounds_worst_case": True,
        "constituents_covered": ["radiator-skin", "film-overlay"],
    }
    record.update(overrides)
    return record


class CategorizeConstituentTests(unittest.TestCase):
    def test_grounded_conductor_is_categorized(self):
        out = categorize_constituent(conductor("bracket"))
        self.assertEqual(out["category"], CATEGORY_GROUNDED_CONDUCTOR)
        self.assertFalse(out["ungrounded"])

    def test_floating_conductor_is_categorized(self):
        out = categorize_constituent(conductor("shim", grounded=False))
        self.assertEqual(out["category"], CATEGORY_FLOATING_CONDUCTOR)
        self.assertTrue(out["ungrounded"])

    def test_exposed_dielectric_is_categorized(self):
        out = categorize_constituent(dielectric("film-overlay"))
        self.assertEqual(out["category"], CATEGORY_EXPOSED_DIELECTRIC)
        self.assertTrue(out["ungrounded"])

    def test_exactly_at_conductive_ceiling_stays_conductive(self):
        out = categorize_constituent(
            conductor("edge", resistivity=CONDUCTIVE_CEILING_OHM_SQ, grounded=False)
        )
        self.assertEqual(out["category"], CATEGORY_FLOATING_CONDUCTOR)

    def test_just_above_conductive_ceiling_is_dielectric(self):
        out = categorize_constituent(
            conductor("edge", resistivity=CONDUCTIVE_CEILING_OHM_SQ * 1.001,
                      grounded=False)
        )
        self.assertEqual(out["category"], CATEGORY_EXPOSED_DIELECTRIC)

    def test_exposed_area_defaults_to_internal(self):
        out = categorize_constituent(
            {"name": "inner-shim", "surface_resistivity_ohm_sq": 1.0e3,
             "grounded": False}
        )
        self.assertAlmostEqual(out["exposed_area_m2"], 0.0)
        self.assertFalse(out["externally_exposed"])

    def test_decades_field_matches_log10(self):
        out = categorize_constituent(dielectric("film-overlay", resistivity=1.0e12))
        self.assertAlmostEqual(out["decades"], 12.0)

    def test_missing_name_rejected(self):
        record = conductor("bracket")
        del record["name"]
        with self.assertRaises(ValueError):
            categorize_constituent(record)

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            categorize_constituent(conductor("   "))

    def test_non_mapping_constituent_rejected(self):
        with self.assertRaises(ValueError):
            categorize_constituent(["bracket"])

    def test_missing_resistivity_rejected(self):
        record = conductor("bracket")
        del record["surface_resistivity_ohm_sq"]
        with self.assertRaises(ValueError):
            categorize_constituent(record)

    def test_non_numeric_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            categorize_constituent(conductor("bracket", resistivity="1e5"))

    def test_boolean_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            categorize_constituent(conductor("bracket", resistivity=True))

    def test_zero_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            categorize_constituent(conductor("bracket", resistivity=0.0))

    def test_negative_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            categorize_constituent(conductor("bracket", resistivity=-1.0e3))

    def test_infinite_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            categorize_constituent(conductor("bracket", resistivity=math.inf))

    def test_missing_grounded_flag_rejected(self):
        record = conductor("bracket")
        del record["grounded"]
        with self.assertRaises(ValueError):
            categorize_constituent(record)

    def test_non_boolean_grounded_flag_rejected(self):
        with self.assertRaises(ValueError):
            categorize_constituent(conductor("bracket", grounded="yes"))

    def test_negative_exposed_area_rejected(self):
        with self.assertRaises(ValueError):
            categorize_constituent(conductor("bracket", area=-0.1))


class ResistivityDecadeTests(unittest.TestCase):
    def test_decade_of_one_kilohm_per_square(self):
        self.assertAlmostEqual(resistivity_decades(1.0e3), 3.0)

    def test_decade_of_fractional_value(self):
        self.assertAlmostEqual(resistivity_decades(3.0e7), math.log10(3.0e7))

    def test_zero_resistivity_has_no_decade(self):
        with self.assertRaises(ValueError):
            resistivity_decades(0.0)

    def test_non_numeric_resistivity_has_no_decade(self):
        with self.assertRaises(ValueError):
            resistivity_decades(None)


class AssemblyCategorizationTests(unittest.TestCase):
    def test_assembly_categorizes_every_constituent(self):
        out = categorize_assembly([conductor("skin"), dielectric("film-overlay")])
        self.assertEqual(len(out), 2)

    def test_ungrounded_members_are_selected(self):
        out = categorize_assembly(
            [conductor("skin"), dielectric("film-overlay"),
             conductor("shim", grounded=False)]
        )
        names = sorted(item["name"] for item in ungrounded_constituents(out))
        self.assertEqual(names, ["film-overlay", "shim"])

    def test_constituent_list_must_be_a_list(self):
        with self.assertRaises(ValueError):
            categorize_assembly(None)

    def test_empty_assembly_rejected(self):
        with self.assertRaises(ValueError):
            categorize_assembly([])

    def test_duplicate_constituent_names_rejected(self):
        with self.assertRaises(ValueError):
            categorize_assembly([conductor("skin"), dielectric("skin")])


class DecadeSpanTests(unittest.TestCase):
    def test_no_exposed_ungrounded_pair_yields_zero_span(self):
        out = pairwise_decade_span(categorize_assembly([conductor("skin")]))
        self.assertEqual(out["pairs"], [])
        self.assertAlmostEqual(out["max_span_decades"], 0.0)
        self.assertIsNone(out["driving_pair"])

    def test_single_pair_span_value(self):
        out = pairwise_decade_span(
            categorize_assembly(
                [conductor("shim", resistivity=1.0e3, grounded=False),
                 dielectric("film-overlay", resistivity=1.0e9)]
            )
        )
        self.assertAlmostEqual(out["max_span_decades"], 6.0)
        self.assertEqual(out["driving_pair"], ("shim", "film-overlay"))

    def test_widest_pair_leads_the_ordering(self):
        out = pairwise_decade_span(
            categorize_assembly(
                [conductor("shim", resistivity=1.0e3, grounded=False),
                 dielectric("film-overlay", resistivity=1.0e6),
                 dielectric("washer-face", resistivity=1.0e13)]
            )
        )
        self.assertEqual(out["driving_pair"], ("shim", "washer-face"))
        self.assertAlmostEqual(out["pairs"][0]["span_decades"], 10.0)

    def test_internal_constituents_do_not_pair(self):
        out = pairwise_decade_span(
            categorize_assembly(
                [dielectric("film-overlay", resistivity=1.0e12),
                 dielectric("inner-sleeve", resistivity=1.0e3, area=0.0)]
            )
        )
        self.assertEqual(out["pairs"], [])

    def test_span_exactly_at_threshold_is_not_an_exceedance(self):
        out = pairwise_decade_span(
            categorize_assembly(
                [conductor("shim", resistivity=1.0e2, grounded=False),
                 dielectric("film-overlay", resistivity=1.0e6)]
            )
        )
        self.assertAlmostEqual(out["max_span_decades"], DECADE_SPAN_LIMIT)
        self.assertFalse(out["exceeds_review_threshold"])

    def test_span_at_threshold_with_representation_drift_is_not_an_exceedance(self):
        out = pairwise_decade_span(
            categorize_assembly(
                [conductor("shim", resistivity=4.7e4, grounded=False),
                 dielectric("film-overlay", resistivity=4.7e8)]
            )
        )
        self.assertAlmostEqual(out["max_span_decades"], DECADE_SPAN_LIMIT)
        self.assertGreater(out["max_span_decades"], DECADE_SPAN_LIMIT)
        self.assertFalse(out["exceeds_review_threshold"])

    def test_span_beyond_threshold_is_an_exceedance(self):
        out = pairwise_decade_span(
            categorize_assembly(
                [conductor("shim", resistivity=1.0e2, grounded=False),
                 dielectric("film-overlay", resistivity=1.0e8)]
            )
        )
        self.assertTrue(out["exceeds_review_threshold"])

    def test_differing_categories_are_dissimilar_within_one_decade(self):
        out = pairwise_decade_span(
            categorize_assembly(
                [conductor("shim", resistivity=9.0e4, grounded=False),
                 dielectric("film-overlay", resistivity=1.1e5)]
            )
        )
        self.assertLess(out["max_span_decades"], 1.0)
        self.assertTrue(out["pairs"][0]["dissimilar"])


class MixtureDecisionTests(unittest.TestCase):
    def test_dissimilar_ungrounded_pair_is_a_mixed_material_assembly(self):
        out = categorize_assembly(
            [conductor("shim", resistivity=1.0e3, grounded=False),
             dielectric("film-overlay")]
        )
        self.assertTrue(is_mixed_material_assembly(out))
        self.assertEqual(required_evidence_level(out), EVIDENCE_LEVEL_UNIT)

    def test_single_ungrounded_constituent_is_not_a_mixture(self):
        out = categorize_assembly([conductor("skin"), dielectric("film-overlay")])
        self.assertFalse(is_mixed_material_assembly(out))
        self.assertEqual(required_evidence_level(out), EVIDENCE_LEVEL_CONSTITUENT)

    def test_identical_ungrounded_materials_are_not_a_mixture(self):
        out = categorize_assembly(
            [dielectric("film-overlay", resistivity=1.0e12),
             dielectric("film-return", resistivity=1.0e12)]
        )
        self.assertFalse(is_mixed_material_assembly(out))

    def test_all_grounded_assembly_is_not_a_mixture(self):
        out = categorize_assembly([conductor("skin"), conductor("bracket")])
        self.assertFalse(is_mixed_material_assembly(out))


class EvidenceValidationTests(unittest.TestCase):
    def test_valid_evidence_is_normalized(self):
        out = validate_evidence(evidence())
        self.assertEqual(out["coverage"], "complete-unit")
        self.assertEqual(len(out["constituents_covered"]), 2)

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(evidence(method="coupon-screening"))

    def test_unknown_coverage_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(evidence(coverage="partial"))

    def test_missing_representativeness_rejected(self):
        record = evidence()
        del record["specimen_representative"]
        with self.assertRaises(ValueError):
            validate_evidence(record)

    def test_non_boolean_envelope_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence(evidence(envelope_bounds_worst_case="true"))

    def test_covered_list_must_be_a_list(self):
        with self.assertRaises(ValueError):
            validate_evidence(evidence(constituents_covered="radiator-skin"))

    def test_covered_entries_must_be_names(self):
        with self.assertRaises(ValueError):
            validate_evidence(evidence(constituents_covered=[7]))

    def test_non_mapping_evidence_rejected(self):
        with self.assertRaises(ValueError):
            validate_evidence("assembly-qualification")


class EvidenceFindingTests(unittest.TestCase):
    def setUp(self):
        self.categorized = categorize_assembly(
            [conductor("radiator-skin", resistivity=1.0e3, grounded=False),
             dielectric("film-overlay")]
        )

    def test_absent_evidence_for_a_mixture_is_a_finding(self):
        out = evidence_findings(None, self.categorized, EVIDENCE_LEVEL_UNIT)
        self.assertEqual(len(out), 1)

    def test_per_constituent_coverage_is_a_finding(self):
        norm = validate_evidence(evidence(coverage="per-constituent"))
        out = evidence_findings(norm, self.categorized, EVIDENCE_LEVEL_UNIT)
        self.assertTrue(any("complete unit" in item for item in out))

    def test_unrepresentative_specimen_is_a_finding(self):
        norm = validate_evidence(evidence(specimen_representative=False))
        out = evidence_findings(norm, self.categorized, EVIDENCE_LEVEL_UNIT)
        self.assertTrue(any("representative" in item for item in out))

    def test_envelope_shortfall_is_a_finding(self):
        norm = validate_evidence(evidence(envelope_bounds_worst_case=False))
        out = evidence_findings(norm, self.categorized, EVIDENCE_LEVEL_UNIT)
        self.assertTrue(any("envelope" in item for item in out))

    def test_uncovered_constituent_is_a_finding(self):
        norm = validate_evidence(evidence(constituents_covered=["radiator-skin"]))
        out = evidence_findings(norm, self.categorized, EVIDENCE_LEVEL_UNIT)
        self.assertTrue(any("film-overlay" in item for item in out))

    def test_complete_evidence_leaves_no_finding(self):
        norm = validate_evidence(evidence())
        out = evidence_findings(norm, self.categorized, EVIDENCE_LEVEL_UNIT)
        self.assertEqual(out, [])

    def test_constituent_level_absent_evidence_is_a_finding(self):
        out = evidence_findings(None, self.categorized, EVIDENCE_LEVEL_CONSTITUENT)
        self.assertEqual(len(out), 1)

    def test_constituent_level_envelope_shortfall_is_a_finding(self):
        norm = validate_evidence(
            evidence(coverage="per-constituent", envelope_bounds_worst_case=False)
        )
        out = evidence_findings(norm, self.categorized, EVIDENCE_LEVEL_CONSTITUENT)
        self.assertEqual(len(out), 1)


class EndToEndEvaluationTests(unittest.TestCase):
    def build(self, **overrides):
        record = {
            "name": "antenna-standoff-stack",
            "constituents": [
                conductor("radiator-skin", resistivity=1.0e3, grounded=False),
                dielectric("film-overlay", resistivity=1.0e6),
            ],
            "evidence": evidence(),
        }
        record.update(overrides)
        return record

    def test_compliant_mixture_reports_no_finding(self):
        out = evaluate_mixed_material_assembly(self.build())
        self.assertTrue(out["mixed_material"])
        self.assertTrue(out["compliant"])
        self.assertEqual(out["findings"], [])

    def test_required_level_is_reported(self):
        out = evaluate_mixed_material_assembly(self.build())
        self.assertEqual(out["required_evidence_level"], EVIDENCE_LEVEL_UNIT)
        self.assertEqual(out["ungrounded_count"], 2)

    def test_per_constituent_evidence_fails_a_mixture(self):
        out = evaluate_mixed_material_assembly(
            self.build(evidence=evidence(coverage="per-constituent"))
        )
        self.assertFalse(out["compliant"])

    def test_wide_span_without_a_qualification_run_is_a_finding(self):
        out = evaluate_mixed_material_assembly(
            self.build(
                constituents=[
                    conductor("radiator-skin", resistivity=1.0e2, grounded=False),
                    dielectric("film-overlay", resistivity=1.0e13),
                ],
                evidence=evidence(method="assembly-assessment"),
            )
        )
        self.assertTrue(out["differential_charge_driver"]["exceeds_review_threshold"])
        self.assertTrue(any("qualification" in item for item in out["findings"]))

    def test_wide_span_with_a_qualification_run_is_accepted(self):
        out = evaluate_mixed_material_assembly(
            self.build(
                constituents=[
                    conductor("radiator-skin", resistivity=1.0e2, grounded=False),
                    dielectric("film-overlay", resistivity=1.0e13),
                ]
            )
        )
        self.assertTrue(out["compliant"])

    def test_uniform_grounded_assembly_needs_constituent_evidence_only(self):
        out = evaluate_mixed_material_assembly(
            self.build(
                constituents=[conductor("radiator-skin"), conductor("bracket")],
                evidence=evidence(coverage="per-constituent"),
            )
        )
        self.assertFalse(out["mixed_material"])
        self.assertTrue(out["compliant"])

    def test_missing_evidence_block_is_a_finding(self):
        record = self.build()
        del record["evidence"]
        out = evaluate_mixed_material_assembly(record)
        self.assertFalse(out["compliant"])

    def test_assembly_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_mixed_material_assembly(["antenna-standoff-stack"])

    def test_assembly_needs_a_name(self):
        record = self.build()
        del record["name"]
        with self.assertRaises(ValueError):
            evaluate_mixed_material_assembly(record)

    def test_assembly_needs_constituents(self):
        record = self.build()
        del record["constituents"]
        with self.assertRaises(ValueError):
            evaluate_mixed_material_assembly(record)

    def test_evaluation_is_deterministic(self):
        first = evaluate_mixed_material_assembly(self.build())
        second = evaluate_mixed_material_assembly(self.build())
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
