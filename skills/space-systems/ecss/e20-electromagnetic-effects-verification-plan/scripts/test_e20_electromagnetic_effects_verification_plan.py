#!/usr/bin/env python3
"""Contract test for the Annex B electromagnetic effects verification plan leaf.

Offline, deterministic, stdlib unittest. Run: python3 this_file.py
"""

import copy
import math
import unittest

from e20_electromagnetic_effects_verification_plan_logic import (
    LEVELS,
    METHODS,
    PLAN_SECTIONS,
    REQUIREMENT_KINDS,
    assess_verification_plan,
    check_level_adequacy,
    check_method_admissibility,
    check_plan_sections,
    compute_requirement_coverage,
    level_rank,
    normalize_level,
    normalize_method,
    normalize_requirement_kind,
    summarize_method_mix,
    validate_activity,
)

MEASURED_ACTIVITY = {
    "id": "act-re-01",
    "method": "test",
    "level": "system-level",
    "coverage_share": 1.0,
    "facility": "anechoic-chamber-b",
    "configuration": "flight-representative-harness",
}

RADIATED_REQUIREMENT = {
    "id": "emc-re-01",
    "kind": "radiated-emission",
    "level": "system-level",
    "activities": [MEASURED_ACTIVITY],
}

BONDING_REQUIREMENT = {
    "id": "emc-bond-01",
    "kind": "bonding",
    "level": "equipment-level",
    "activities": [{
        "id": "act-bond-01",
        "method": "inspection",
        "level": "equipment-level",
        "coverage_share": 1.0,
        "acceptance_criterion": "strap resistance under the declared class limit",
    }],
}

GROUNDING_REQUIREMENT = {
    "id": "emc-gnd-01",
    "kind": "grounding",
    "level": "system-level",
    "activities": [{
        "id": "act-gnd-01",
        "method": "rod",
        "level": "system-level",
        "coverage_share": 1.0,
        "design_document_reference": "grounding-diagram-gd-004",
    }],
}


def good_plan():
    return copy.deepcopy([RADIATED_REQUIREMENT, BONDING_REQUIREMENT,
                          GROUNDING_REQUIREMENT])


def full_sections():
    return {
        "verification-approach-narrative": "staged approach from unit to system",
        "requirement-to-activity-matrix": ["emc-re-01", "emc-bond-01"],
        "method-justification-record": "method choice argued per requirement",
        "facility-and-configuration-declaration": "anechoic-chamber-b declared",
    }


class NormalizationTests(unittest.TestCase):
    def test_method_synonyms_resolve(self):
        self.assertEqual(normalize_method("test"), "verification-by-test")
        self.assertEqual(normalize_method("A"), "verification-by-analysis")
        self.assertEqual(normalize_method("rod"),
                         "verification-by-review-of-design")
        self.assertEqual(normalize_method("Similarity"),
                         "verification-by-similarity")

    def test_every_method_round_trips(self):
        for method in METHODS:
            self.assertEqual(normalize_method(method), method)

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            normalize_method("demonstration-by-assertion")

    def test_non_string_method_rejected(self):
        with self.assertRaises(ValueError):
            normalize_method(2)

    def test_requirement_kind_synonyms_resolve(self):
        self.assertEqual(normalize_requirement_kind("re"), "radiated-emission")
        self.assertEqual(normalize_requirement_kind("ESD"),
                         "electrostatic-discharge")
        self.assertEqual(normalize_requirement_kind("bonding"),
                         "electrical-bonding-resistance")

    def test_every_requirement_kind_round_trips(self):
        for kind in REQUIREMENT_KINDS:
            self.assertEqual(normalize_requirement_kind(kind), kind)

    def test_unknown_requirement_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_requirement_kind("thermal-balance")

    def test_level_synonyms_resolve(self):
        self.assertEqual(normalize_level("unit"), "equipment-level")
        self.assertEqual(normalize_level("spacecraft"), "system-level")
        for level in LEVELS:
            self.assertEqual(normalize_level(level), level)

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            normalize_level("component-level")

    def test_level_rank_is_ordered(self):
        self.assertLess(level_rank("equipment-level"), level_rank("subsystem-level"))
        self.assertLess(level_rank("subsystem-level"), level_rank("system-level"))


class PlanSectionTests(unittest.TestCase):
    def test_full_section_set_is_complete(self):
        out = check_plan_sections(full_sections())
        self.assertTrue(out["complete"])
        self.assertEqual(out["missing"], [])
        self.assertEqual(len(out["declared"]), len(PLAN_SECTIONS))

    def test_missing_section_is_reported(self):
        sections = full_sections()
        del sections["method-justification-record"]
        out = check_plan_sections(sections)
        self.assertEqual(out["missing"], ["method-justification-record"])

    def test_empty_section_counts_as_missing(self):
        sections = full_sections()
        sections["requirement-to-activity-matrix"] = []
        self.assertIn("requirement-to-activity-matrix",
                      check_plan_sections(sections)["missing"])

    def test_section_synonyms_resolve(self):
        out = check_plan_sections({
            "approach": "narrative",
            "matrix": ["emc-re-01"],
            "method-justification": "argued",
            "facilities": "declared",
        })
        self.assertTrue(out["complete"])

    def test_unknown_section_rejected(self):
        with self.assertRaises(ValueError):
            check_plan_sections({"budget-table": "x"})

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            check_plan_sections(["approach"])


class ActivityValidationTests(unittest.TestCase):
    def test_activity_is_normalised(self):
        record = validate_activity({"id": " act-1 ", "method": "t",
                                    "level": "unit"})
        self.assertEqual(record["id"], "act-1")
        self.assertEqual(record["method"], "verification-by-test")
        self.assertEqual(record["level"], "equipment-level")
        self.assertAlmostEqual(record["coverage_share"], 1.0, places=12)

    def test_missing_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity({"method": "test", "level": "system-level"})

    def test_zero_share_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity({"id": "a", "method": "test",
                               "level": "system-level", "coverage_share": 0.0})

    def test_share_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity({"id": "a", "method": "test",
                               "level": "system-level", "coverage_share": 1.2})

    def test_non_numeric_share_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity({"id": "a", "method": "test",
                               "level": "system-level", "coverage_share": "half"})

    def test_boolean_share_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity({"id": "a", "method": "test",
                               "level": "system-level", "coverage_share": True})

    def test_non_finite_share_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity({"id": "a", "method": "test",
                               "level": "system-level",
                               "coverage_share": float("nan")})

    def test_non_mapping_activity_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity("act-re-01")


class AdmissibilityTests(unittest.TestCase):
    def test_measured_activity_closes_a_radiated_requirement(self):
        self.assertEqual(
            check_method_admissibility("radiated-emission", MEASURED_ACTIVITY), [])

    def test_design_review_cannot_close_a_radiated_requirement(self):
        activity = {"id": "act-x", "method": "rod", "level": "system-level",
                    "design_document_reference": "layout-ld-002"}
        findings = check_method_admissibility("radiated-emission", activity)
        self.assertEqual(findings[0]["finding"], "method-not-admissible-for-kind")

    def test_inspection_closes_a_bonding_requirement(self):
        activity = BONDING_REQUIREMENT["activities"][0]
        self.assertEqual(
            check_method_admissibility("bonding", activity), [])

    def test_missing_facility_is_an_evidence_finding(self):
        activity = dict(MEASURED_ACTIVITY)
        del activity["facility"]
        findings = check_method_admissibility("radiated-emission", activity)
        self.assertEqual(findings[0]["finding"], "method-evidence-undeclared")
        self.assertEqual(findings[0]["field"], "facility")

    def test_similarity_without_heritage_or_delta_is_two_findings(self):
        activity = {"id": "act-sim", "method": "similarity",
                    "level": "equipment-level"}
        findings = check_method_admissibility("conducted-emission", activity)
        self.assertEqual(len(findings), 2)
        self.assertEqual({f["field"] for f in findings},
                         {"heritage_reference", "delta_justification"})

    def test_similarity_with_full_evidence_passes(self):
        activity = {"id": "act-sim", "method": "similarity",
                    "level": "equipment-level",
                    "heritage_reference": "unit-flown-on-earlier-mission",
                    "delta_justification": "same filter, same enclosure"}
        self.assertEqual(
            check_method_admissibility("conducted-emission", activity), [])

    def test_uncorrelated_analysis_of_a_field_quantity_is_a_finding(self):
        activity = {"id": "act-an", "method": "analysis", "level": "system-level",
                    "model_reference": "field-solver-model-m7"}
        findings = check_method_admissibility("radiated-susceptibility", activity)
        self.assertEqual(findings[0]["finding"], "analysis-model-uncorrelated")

    def test_correlated_analysis_of_a_field_quantity_passes(self):
        activity = {"id": "act-an", "method": "analysis", "level": "system-level",
                    "model_reference": "field-solver-model-m7",
                    "correlation_evidence": "measured against the engineering model"}
        self.assertEqual(
            check_method_admissibility("radiated-susceptibility", activity), [])

    def test_analysis_of_a_magnetic_moment_needs_no_correlation(self):
        activity = {"id": "act-mm", "method": "analysis",
                    "level": "subsystem-level",
                    "model_reference": "dipole-summation-model"}
        self.assertEqual(
            check_method_admissibility("magnetic-moment", activity), [])

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            check_method_admissibility("thermal-balance", MEASURED_ACTIVITY)


class LevelAdequacyTests(unittest.TestCase):
    def test_same_level_is_adequate(self):
        self.assertTrue(check_level_adequacy("subsystem-level", "subsystem-level"))

    def test_higher_level_is_adequate(self):
        self.assertTrue(check_level_adequacy("equipment-level", "system-level"))

    def test_lower_level_is_not_adequate(self):
        self.assertFalse(check_level_adequacy("system-level", "equipment-level"))


class CoverageTests(unittest.TestCase):
    def test_single_full_activity_is_complete(self):
        coverage = compute_requirement_coverage(RADIATED_REQUIREMENT)
        self.assertTrue(coverage["complete"])
        self.assertAlmostEqual(coverage["declared_share"], 1.0, places=12)
        self.assertEqual(coverage["deficit"], 0.0)

    def test_split_shares_add_up(self):
        requirement = copy.deepcopy(RADIATED_REQUIREMENT)
        requirement["activities"] = [
            dict(MEASURED_ACTIVITY, id="act-a", coverage_share=0.25),
            dict(MEASURED_ACTIVITY, id="act-b", coverage_share=0.75),
        ]
        coverage = compute_requirement_coverage(requirement)
        self.assertTrue(coverage["complete"])
        self.assertAlmostEqual(coverage["declared_share"], 1.0, places=12)

    def test_full_coverage_survives_representation_error(self):
        # Ten declared tenths do not sum to exactly 1.0 in binary floating
        # point. The requirement is physically fully covered, so the logic
        # absorbs the representation error instead of demanding an eleventh
        # activity; the coverage requirement itself stays at 1.0.
        requirement = copy.deepcopy(RADIATED_REQUIREMENT)
        requirement["activities"] = [
            dict(MEASURED_ACTIVITY, id="act-%d" % i, coverage_share=0.1)
            for i in range(10)
        ]
        coverage = compute_requirement_coverage(requirement)
        self.assertLess(coverage["declared_share"], 1.0)
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["deficit"], 0.0)

    def test_short_coverage_reports_the_deficit(self):
        requirement = copy.deepcopy(RADIATED_REQUIREMENT)
        requirement["activities"] = [dict(MEASURED_ACTIVITY, coverage_share=0.6)]
        coverage = compute_requirement_coverage(requirement)
        self.assertFalse(coverage["complete"])
        self.assertAlmostEqual(coverage["deficit"], 0.4, places=12)

    def test_over_declared_coverage_is_flagged(self):
        requirement = copy.deepcopy(RADIATED_REQUIREMENT)
        requirement["activities"] = [
            dict(MEASURED_ACTIVITY, id="act-a", coverage_share=0.8),
            dict(MEASURED_ACTIVITY, id="act-b", coverage_share=0.8),
        ]
        coverage = compute_requirement_coverage(requirement)
        self.assertTrue(coverage["over_declared"])

    def test_repeated_activity_identifier_rejected(self):
        requirement = copy.deepcopy(RADIATED_REQUIREMENT)
        requirement["activities"] = [
            dict(MEASURED_ACTIVITY, coverage_share=0.5),
            dict(MEASURED_ACTIVITY, coverage_share=0.5),
        ]
        with self.assertRaises(ValueError):
            compute_requirement_coverage(requirement)

    def test_requirement_without_activities_rejected(self):
        requirement = copy.deepcopy(RADIATED_REQUIREMENT)
        requirement["activities"] = []
        with self.assertRaises(ValueError):
            compute_requirement_coverage(requirement)

    def test_activities_as_bare_string_rejected(self):
        requirement = copy.deepcopy(RADIATED_REQUIREMENT)
        requirement["activities"] = "act-re-01"
        with self.assertRaises(ValueError):
            compute_requirement_coverage(requirement)

    def test_requirement_without_identifier_rejected(self):
        requirement = copy.deepcopy(RADIATED_REQUIREMENT)
        del requirement["id"]
        with self.assertRaises(ValueError):
            compute_requirement_coverage(requirement)

    def test_non_mapping_requirement_rejected(self):
        with self.assertRaises(ValueError):
            compute_requirement_coverage("emc-re-01")


class MethodMixTests(unittest.TestCase):
    def test_counts_sum_to_activity_count(self):
        mix = summarize_method_mix(good_plan())
        self.assertEqual(sum(mix["counts"].values()), mix["activities"])
        self.assertEqual(mix["activities"], 3)
        self.assertAlmostEqual(mix["measured_share"], 1.0 / 3.0, places=12)

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            summarize_method_mix([])

    def test_bare_mapping_rejected(self):
        with self.assertRaises(ValueError):
            summarize_method_mix(RADIATED_REQUIREMENT)


class PlanAssessmentTests(unittest.TestCase):
    def test_good_plan_is_acceptable(self):
        out = assess_verification_plan(good_plan(), 1.0, full_sections())
        self.assertTrue(out["acceptable"])
        self.assertEqual(out["findings"], [])
        self.assertAlmostEqual(out["coverage_index"], 1.0, places=12)
        self.assertEqual([r["id"] for r in out["requirements"]],
                         ["emc-bond-01", "emc-gnd-01", "emc-re-01"])

    def test_inadmissible_method_reaches_the_verdict(self):
        plan = good_plan()
        plan[0]["activities"] = [{"id": "act-re-01", "method": "inspection",
                                  "level": "system-level",
                                  "acceptance_criterion": "visual check"}]
        out = assess_verification_plan(plan)
        self.assertFalse(out["acceptable"])
        self.assertEqual(out["findings"][0]["finding"],
                         "method-not-admissible-for-kind")

    def test_verification_below_the_requirement_level_is_a_finding(self):
        plan = good_plan()
        plan[0]["activities"] = [dict(MEASURED_ACTIVITY, level="equipment-level")]
        out = assess_verification_plan(plan)
        kinds = [f["finding"] for f in out["findings"]]
        self.assertIn("verification-level-too-low", kinds)

    def test_incomplete_coverage_reaches_the_verdict(self):
        plan = good_plan()
        plan[1]["activities"][0]["coverage_share"] = 0.5
        out = assess_verification_plan(plan)
        self.assertFalse(out["acceptable"])
        kinds = [f["finding"] for f in out["findings"]]
        self.assertIn("coverage-incomplete", kinds)
        self.assertIn("coverage-index-below-floor", kinds)

    def test_missing_plan_section_reaches_the_verdict(self):
        sections = full_sections()
        del sections["facility-and-configuration-declaration"]
        out = assess_verification_plan(good_plan(), 1.0, sections)
        self.assertFalse(out["acceptable"])
        self.assertEqual(out["findings"][-1]["finding"], "plan-section-undeclared")

    def test_duplicate_requirement_identifier_rejected(self):
        plan = good_plan()
        plan.append(copy.deepcopy(RADIATED_REQUIREMENT))
        with self.assertRaises(ValueError):
            assess_verification_plan(plan)

    def test_coverage_floor_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            assess_verification_plan(good_plan(), 1.5)

    def test_non_numeric_coverage_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_verification_plan(good_plan(), "all")

    def test_empty_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_verification_plan([])

    def test_lowered_floor_accepts_a_partly_covered_plan(self):
        plan = good_plan()
        plan[1]["activities"][0]["coverage_share"] = 0.5
        out = assess_verification_plan(plan, 0.5)
        kinds = [f["finding"] for f in out["findings"]]
        self.assertNotIn("coverage-index-below-floor", kinds)

    def test_coverage_index_floor_met_within_representation_error(self):
        # Two of three requirements fully covered: the index is exactly 2/3
        # and the declared floor sits one ULP above it. The floor is not
        # widened -- only the representation error is absorbed.
        plan = good_plan()
        plan[1]["activities"][0]["coverage_share"] = 0.5
        index = 2.0 / 3.0
        floor = math.nextafter(index, 1.0)
        self.assertFalse(index >= floor)
        out = assess_verification_plan(plan, floor)
        self.assertAlmostEqual(out["coverage_index"], index, places=12)
        kinds = [f["finding"] for f in out["findings"]]
        self.assertNotIn("coverage-index-below-floor", kinds)


if __name__ == "__main__":
    unittest.main()
