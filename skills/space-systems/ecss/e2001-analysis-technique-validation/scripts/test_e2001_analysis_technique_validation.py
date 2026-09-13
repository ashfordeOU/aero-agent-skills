#!/usr/bin/env python3
"""Contract test for the multipaction analysis-technique validation (offline)."""

import copy
import unittest

from e2001_analysis_technique_validation_logic import (
    DEFAULT_AGREEMENT_CRITERION_DB,
    HERITAGE,
    MEASURED_CORRELATION,
    MIN_COMPARISON_POINTS,
    assess_correlation_evidence,
    assess_heritage_evidence,
    categorize_evidence,
    covers_analysis_case,
    frequency_gap_product_ghz_mm,
    prediction_deviation_db,
    tool_build_is_covered,
    validate_analysis_technique,
    validated_envelope,
)

TECHNIQUE = {
    "name": "multipaction-solver",
    "version": "3.2.1",
    "version_lineage": ["3.2.0", "3.1.4"],
    "theory_basis": "parallel-plate-two-surface",
}

HERITAGE_RECORD = {
    "route": HERITAGE,
    "tool_version": "3.2.1",
    "prior_application": "Ku-band output filter, flight unit",
    "geometry_family": "rectangular-waveguide-iris",
    "electrode_material": "silver-plated-aluminium",
    "frequency_hz": 12.0e9,
    "gap_m": 1.0e-3,
    "verified_by_test": True,
}

CORRELATION_RECORD = {
    "route": MEASURED_CORRELATION,
    "tool_version": "3.2.1",
    "geometry_family": "rectangular-waveguide-iris",
    "electrode_material": "silver-plated-aluminium",
    "comparison_points": [
        {
            "frequency_hz": 4.9e9,
            "gap_m": 1.0e-3,
            "predicted_breakdown_w": 104.0,
            "measured_breakdown_w": 100.0,
        },
        {
            "frequency_hz": 12.0e9,
            "gap_m": 1.0e-3,
            "predicted_breakdown_w": 480.0,
            "measured_breakdown_w": 500.0,
        },
        {
            "frequency_hz": 18.0e9,
            "gap_m": 1.5e-3,
            "predicted_breakdown_w": 1180.0,
            "measured_breakdown_w": 1200.0,
        },
    ],
}

CASE_INSIDE = {
    "frequency_hz": 14.0e9,
    "gap_m": 1.0e-3,
    "geometry_family": "rectangular-waveguide-iris",
    "electrode_material": "silver-plated-aluminium",
}


def _heritage(**overrides):
    record = copy.deepcopy(HERITAGE_RECORD)
    record.update(overrides)
    return record


def _correlation(**overrides):
    record = copy.deepcopy(CORRELATION_RECORD)
    record.update(overrides)
    return record


class DeviationTests(unittest.TestCase):
    def test_identical_levels_give_zero_deviation(self):
        self.assertAlmostEqual(prediction_deviation_db(500.0, 500.0), 0.0, places=12)

    def test_factor_of_two_over_prediction(self):
        self.assertAlmostEqual(prediction_deviation_db(200.0, 100.0), 3.0103, places=4)

    def test_under_prediction_is_negative(self):
        self.assertLess(prediction_deviation_db(90.0, 100.0), 0.0)

    def test_zero_predicted_level_rejected(self):
        with self.assertRaises(ValueError):
            prediction_deviation_db(0.0, 100.0)

    def test_negative_measured_level_rejected(self):
        with self.assertRaises(ValueError):
            prediction_deviation_db(100.0, -100.0)

    def test_non_numeric_level_rejected(self):
        with self.assertRaises(ValueError):
            prediction_deviation_db("100 W", 100.0)


class FrequencyGapProductTests(unittest.TestCase):
    def test_product_in_ghz_millimetre(self):
        self.assertAlmostEqual(
            frequency_gap_product_ghz_mm(12.0e9, 1.0e-3), 12.0, places=9
        )

    def test_product_scales_with_the_gap(self):
        self.assertAlmostEqual(
            frequency_gap_product_ghz_mm(12.0e9, 2.0e-3), 24.0, places=9
        )

    def test_zero_gap_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product_ghz_mm(12.0e9, 0.0)

    def test_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product_ghz_mm(-12.0e9, 1.0e-3)

    def test_missing_gap_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product_ghz_mm(12.0e9, None)


class EvidenceRouteTests(unittest.TestCase):
    def test_heritage_route_recognised(self):
        self.assertEqual(categorize_evidence(HERITAGE_RECORD), HERITAGE)

    def test_correlation_route_recognised(self):
        self.assertEqual(categorize_evidence(CORRELATION_RECORD), MEASURED_CORRELATION)

    def test_unknown_route_rejected(self):
        with self.assertRaises(ValueError):
            categorize_evidence({"route": "engineering-judgement"})

    def test_missing_route_rejected(self):
        with self.assertRaises(ValueError):
            categorize_evidence({"tool_version": "3.2.1"})

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            categorize_evidence(["route", HERITAGE])


class ToolBuildTests(unittest.TestCase):
    def test_same_build_is_covered(self):
        self.assertTrue(tool_build_is_covered("3.2.1", TECHNIQUE))

    def test_declared_ancestor_is_covered(self):
        self.assertTrue(tool_build_is_covered("3.1.4", TECHNIQUE))

    def test_foreign_build_is_not_covered(self):
        self.assertFalse(tool_build_is_covered("2.9.0", TECHNIQUE))

    def test_blank_build_rejected(self):
        with self.assertRaises(ValueError):
            tool_build_is_covered("   ", TECHNIQUE)

    def test_non_mapping_technique_rejected(self):
        with self.assertRaises(ValueError):
            tool_build_is_covered("3.2.1", "multipaction-solver 3.2.1")

    def test_non_sequence_lineage_rejected(self):
        broken = dict(TECHNIQUE, version_lineage="3.2.0")
        with self.assertRaises(ValueError):
            tool_build_is_covered("3.2.0", broken)


class HeritageEvidenceTests(unittest.TestCase):
    def test_complete_heritage_record_is_accepted(self):
        result = assess_heritage_evidence(HERITAGE_RECORD, TECHNIQUE)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["frequency_gap_products"][0], 12.0, places=9)

    def test_wrong_route_rejected(self):
        with self.assertRaises(ValueError):
            assess_heritage_evidence(CORRELATION_RECORD, TECHNIQUE)

    def test_missing_prior_application_is_a_finding(self):
        result = assess_heritage_evidence(_heritage(prior_application=""), TECHNIQUE)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("prior application" in f for f in result["findings"]))

    def test_untested_heritage_is_a_finding(self):
        result = assess_heritage_evidence(_heritage(verified_by_test=False), TECHNIQUE)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("multipaction-test" in f for f in result["findings"]))

    def test_foreign_build_is_a_finding(self):
        result = assess_heritage_evidence(_heritage(tool_version="1.0.0"), TECHNIQUE)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("ancestor" in f for f in result["findings"]))

    def test_missing_geometry_family_is_a_finding(self):
        result = assess_heritage_evidence(_heritage(geometry_family=None), TECHNIQUE)
        self.assertFalse(result["accepted"])

    def test_missing_electrode_material_is_a_finding(self):
        result = assess_heritage_evidence(_heritage(electrode_material=""), TECHNIQUE)
        self.assertFalse(result["accepted"])

    def test_missing_gap_rejected(self):
        with self.assertRaises(ValueError):
            assess_heritage_evidence(_heritage(gap_m=None), TECHNIQUE)

    def test_heritage_carries_no_deviation(self):
        result = assess_heritage_evidence(HERITAGE_RECORD, TECHNIQUE)
        self.assertIsNone(result["worst_deviation_db"])


class CorrelationEvidenceTests(unittest.TestCase):
    def test_default_criterion_is_one_decibel(self):
        self.assertAlmostEqual(DEFAULT_AGREEMENT_CRITERION_DB, 1.0, places=12)

    def test_minimum_comparison_points_is_three(self):
        self.assertEqual(MIN_COMPARISON_POINTS, 3)

    def test_agreeing_correlation_is_accepted(self):
        result = assess_correlation_evidence(CORRELATION_RECORD)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["frequency_gap_products"]), 3)

    def test_worst_deviation_is_the_largest_magnitude(self):
        result = assess_correlation_evidence(CORRELATION_RECORD)
        self.assertAlmostEqual(result["worst_deviation_db"], -0.1773, places=3)

    def test_mean_deviation_reported(self):
        result = assess_correlation_evidence(CORRELATION_RECORD)
        self.assertLess(abs(result["mean_deviation_db"]), 0.2)

    def test_point_outside_the_criterion_is_a_finding(self):
        record = _correlation()
        record["comparison_points"][1]["predicted_breakdown_w"] = 900.0
        result = assess_correlation_evidence(record)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("criterion" in f for f in result["findings"]))

    def test_point_exactly_on_the_criterion_is_accepted(self):
        record = _correlation()
        record["comparison_points"][0]["measured_breakdown_w"] = 100.0
        record["comparison_points"][0]["predicted_breakdown_w"] = 100.0 * (10.0 ** 0.1)
        result = assess_correlation_evidence(record, criterion_db=1.0)
        self.assertAlmostEqual(
            abs(result["worst_deviation_db"]), 1.0, places=9
        )
        self.assertTrue(result["accepted"])

    def test_widened_criterion_accepts_a_larger_deviation(self):
        record = _correlation()
        record["comparison_points"][1]["predicted_breakdown_w"] = 630.0
        self.assertFalse(assess_correlation_evidence(record)["accepted"])
        self.assertTrue(
            assess_correlation_evidence(record, criterion_db=2.0)["accepted"]
        )

    def test_too_few_points_is_a_finding(self):
        record = _correlation()
        record["comparison_points"] = record["comparison_points"][:2]
        result = assess_correlation_evidence(record)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("fewer than" in f for f in result["findings"]))

    def test_missing_geometry_family_is_a_finding(self):
        result = assess_correlation_evidence(_correlation(geometry_family=None))
        self.assertFalse(result["accepted"])

    def test_wrong_route_rejected(self):
        with self.assertRaises(ValueError):
            assess_correlation_evidence(HERITAGE_RECORD)

    def test_empty_comparison_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_correlation_evidence(_correlation(comparison_points=[]))

    def test_non_mapping_comparison_point_rejected(self):
        with self.assertRaises(ValueError):
            assess_correlation_evidence(_correlation(comparison_points=[(1, 2)]))

    def test_comparison_point_missing_key_rejected(self):
        record = _correlation()
        del record["comparison_points"][0]["measured_breakdown_w"]
        with self.assertRaises(ValueError):
            assess_correlation_evidence(record)

    def test_zero_criterion_rejected(self):
        with self.assertRaises(ValueError):
            assess_correlation_evidence(CORRELATION_RECORD, criterion_db=0.0)


class EnvelopeTests(unittest.TestCase):
    def _accepted(self):
        return [
            assess_heritage_evidence(HERITAGE_RECORD, TECHNIQUE),
            assess_correlation_evidence(CORRELATION_RECORD),
        ]

    def test_envelope_spans_the_accepted_evidence(self):
        envelope = validated_envelope(self._accepted())
        self.assertAlmostEqual(envelope["frequency_gap_product_min"], 4.9, places=9)
        self.assertAlmostEqual(envelope["frequency_gap_product_max"], 27.0, places=9)

    def test_envelope_lists_both_routes(self):
        envelope = validated_envelope(self._accepted())
        self.assertEqual(
            envelope["routes"], tuple(sorted((HERITAGE, MEASURED_CORRELATION)))
        )

    def test_envelope_collects_families_and_materials(self):
        envelope = validated_envelope(self._accepted())
        self.assertEqual(
            envelope["geometry_families"], ("rectangular-waveguide-iris",)
        )
        self.assertEqual(
            envelope["electrode_materials"], ("silver-plated-aluminium",)
        )

    def test_rejected_evidence_contributes_nothing(self):
        rejected = assess_heritage_evidence(_heritage(verified_by_test=False), TECHNIQUE)
        self.assertIsNone(validated_envelope([rejected]))

    def test_non_sequence_assessments_rejected(self):
        with self.assertRaises(ValueError):
            validated_envelope("assessments")


class CoverageTests(unittest.TestCase):
    def _envelope(self):
        return validated_envelope(
            [
                assess_heritage_evidence(HERITAGE_RECORD, TECHNIQUE),
                assess_correlation_evidence(CORRELATION_RECORD),
            ]
        )

    def test_case_inside_the_envelope_is_covered(self):
        result = covers_analysis_case(self._envelope(), CASE_INSIDE)
        self.assertTrue(result["covered"])
        self.assertEqual(result["reasons"], [])

    def test_case_below_the_envelope_is_not_covered(self):
        case = dict(CASE_INSIDE, frequency_hz=1.0e9, gap_m=1.0e-3)
        result = covers_analysis_case(self._envelope(), case)
        self.assertFalse(result["covered"])
        self.assertTrue(any("below" in r for r in result["reasons"]))

    def test_case_above_the_envelope_is_not_covered(self):
        case = dict(CASE_INSIDE, frequency_hz=30.0e9, gap_m=2.0e-3)
        result = covers_analysis_case(self._envelope(), case)
        self.assertFalse(result["covered"])
        self.assertTrue(any("above" in r for r in result["reasons"]))

    def test_case_on_the_lower_bound_is_covered(self):
        # 7.0 GHz x 0.7 mm evaluates one unit in the last place below 4.9.
        case = dict(CASE_INSIDE, frequency_hz=7.0e9, gap_m=0.7e-3)
        self.assertLess(
            frequency_gap_product_ghz_mm(7.0e9, 0.7e-3),
            self._envelope()["frequency_gap_product_min"],
        )
        self.assertTrue(covers_analysis_case(self._envelope(), case)["covered"])

    def test_unknown_geometry_family_is_not_covered(self):
        case = dict(CASE_INSIDE, geometry_family="coaxial-connector-bead")
        result = covers_analysis_case(self._envelope(), case)
        self.assertFalse(result["covered"])
        self.assertTrue(any("geometry family" in r for r in result["reasons"]))

    def test_unknown_electrode_material_is_not_covered(self):
        case = dict(CASE_INSIDE, electrode_material="alodine-treated-aluminium")
        result = covers_analysis_case(self._envelope(), case)
        self.assertFalse(result["covered"])

    def test_absent_envelope_covers_nothing(self):
        result = covers_analysis_case(None, CASE_INSIDE)
        self.assertFalse(result["covered"])
        self.assertTrue(any("no accepted evidence" in r for r in result["reasons"]))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            covers_analysis_case(self._envelope(), "14 GHz, 1 mm")

    def test_case_without_geometry_family_rejected(self):
        case = dict(CASE_INSIDE)
        del case["geometry_family"]
        with self.assertRaises(ValueError):
            covers_analysis_case(self._envelope(), case)


class TechniqueValidationTests(unittest.TestCase):
    def test_two_route_evidence_validates_the_technique(self):
        result = validate_analysis_technique(
            TECHNIQUE, [HERITAGE_RECORD, CORRELATION_RECORD], [CASE_INSIDE]
        )
        self.assertEqual(result["verdict"], "validated")
        self.assertTrue(result["usable_for_substantiation"])
        self.assertEqual(result["findings"], [])

    def test_case_outside_the_envelope_restricts_the_verdict(self):
        outside = dict(CASE_INSIDE, frequency_hz=40.0e9, gap_m=2.0e-3)
        result = validate_analysis_technique(
            TECHNIQUE, [HERITAGE_RECORD, CORRELATION_RECORD], [CASE_INSIDE, outside]
        )
        self.assertEqual(result["verdict"], "validated-restricted-envelope")
        self.assertFalse(result["usable_for_substantiation"])
        self.assertTrue(result["findings"])

    def test_all_evidence_rejected_leaves_the_technique_unvalidated(self):
        result = validate_analysis_technique(
            TECHNIQUE, [_heritage(verified_by_test=False)], [CASE_INSIDE]
        )
        self.assertEqual(result["verdict"], "not-validated")
        self.assertIsNone(result["envelope"])
        self.assertEqual(result["accepted_routes"], ())

    def test_heritage_alone_can_validate(self):
        result = validate_analysis_technique(TECHNIQUE, [HERITAGE_RECORD])
        self.assertEqual(result["verdict"], "validated")
        self.assertEqual(result["accepted_routes"], (HERITAGE,))

    def test_findings_name_the_offending_evidence_index(self):
        result = validate_analysis_technique(
            TECHNIQUE, [HERITAGE_RECORD, _heritage(verified_by_test=False)]
        )
        self.assertTrue(any(f.startswith("evidence 1") for f in result["findings"]))

    def test_unknown_theory_basis_rejected(self):
        broken = dict(TECHNIQUE, theory_basis="expert-opinion")
        with self.assertRaises(ValueError):
            validate_analysis_technique(broken, [HERITAGE_RECORD])

    def test_empty_evidence_rejected(self):
        with self.assertRaises(ValueError):
            validate_analysis_technique(TECHNIQUE, [])

    def test_missing_technique_name_rejected(self):
        broken = dict(TECHNIQUE)
        del broken["name"]
        with self.assertRaises(ValueError):
            validate_analysis_technique(broken, [HERITAGE_RECORD])

    def test_non_mapping_technique_rejected(self):
        with self.assertRaises(ValueError):
            validate_analysis_technique("multipaction-solver", [HERITAGE_RECORD])

    def test_non_sequence_analysis_cases_rejected(self):
        with self.assertRaises(ValueError):
            validate_analysis_technique(TECHNIQUE, [HERITAGE_RECORD], CASE_INSIDE)

    def test_tightened_criterion_can_reject_the_correlation(self):
        result = validate_analysis_technique(
            TECHNIQUE, [CORRELATION_RECORD], [], criterion_db=0.05
        )
        self.assertEqual(result["verdict"], "not-validated")


if __name__ == "__main__":
    unittest.main()
