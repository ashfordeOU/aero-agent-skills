"""Contract tests for the clause 4.2 device verification method logic."""

import unittest

from e2040_device_verification_method_concepts_logic import (
    CANONICAL_METHODS,
    REQUIREMENT_KINDS,
    SEVERITY_TOLERANCE,
    admissible_methods,
    assess_allocation,
    assess_verification_methods,
    coverage_by_method,
    evidence_rank,
    normalize_kind,
    normalize_method,
    similarity_admissible,
    validate_requirement,
)

HERITAGE = {
    "item": "PCU-A3",
    "qualified_severity": 20.0,
    "design_unchanged": True,
}


def base_requirements():
    return [
        {"id": "DEV-001", "kind": "functional", "method": "test"},
        {"id": "DEV-002", "kind": "performance", "numeric_limit": True, "method": "test"},
        {"id": "DEV-003", "kind": "environmental", "numeric_limit": True,
         "method": "analysis"},
        {"id": "DEV-004", "kind": "interface", "method": "review-of-design"},
        {"id": "DEV-005", "kind": "workmanship", "method": "inspection"},
        {"id": "DEV-006", "kind": "construction", "method": "review-of-design"},
    ]


class MethodFoldingTests(unittest.TestCase):
    def test_canonical_method_passes_through(self):
        self.assertEqual(normalize_method("inspection"), "inspection")

    def test_spaced_review_of_design_is_folded(self):
        self.assertEqual(normalize_method("Review of Design"), "review-of-design")

    def test_heritage_folds_to_similarity(self):
        self.assertEqual(normalize_method("heritage"), "similarity")

    def test_simulation_folds_to_analysis(self):
        self.assertEqual(normalize_method("simulation"), "analysis")

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            normalize_method("gut-feel")

    def test_blank_method_rejected(self):
        with self.assertRaises(ValueError):
            normalize_method("  ")

    def test_every_canonical_method_has_a_rank(self):
        for method in CANONICAL_METHODS:
            self.assertGreaterEqual(evidence_rank(method), 1)

    def test_test_outranks_review_of_design(self):
        self.assertGreater(evidence_rank("test"), evidence_rank("review-of-design"))


class KindFoldingTests(unittest.TestCase):
    def test_canonical_kind_passes_through(self):
        self.assertEqual(normalize_kind("environmental"), "environmental")

    def test_defect_freedom_folds_to_workmanship(self):
        self.assertEqual(normalize_kind("defect-freedom"), "workmanship")

    def test_materials_folds_to_construction(self):
        self.assertEqual(normalize_kind("materials"), "construction")

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_kind("nice-to-have")

    def test_every_kind_has_an_admissible_set(self):
        for kind in REQUIREMENT_KINDS:
            allowed = admissible_methods({"id": "R", "kind": kind})
            self.assertTrue(allowed)


class RequirementValidationTests(unittest.TestCase):
    def test_requirement_is_folded(self):
        record = validate_requirement({"id": " R1 ", "kind": "perf", "method": "T"})
        self.assertEqual(record["id"], "R1")
        self.assertEqual(record["kind"], "performance")
        self.assertEqual(record["method"], "test")

    def test_method_may_be_absent(self):
        self.assertIsNone(validate_requirement({"id": "R1", "kind": "functional"})["method"])

    def test_missing_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "R1"})

    def test_blank_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": " ", "kind": "functional"})

    def test_non_boolean_numeric_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "R1", "kind": "functional", "numeric_limit": "yes"})

    def test_non_mapping_heritage_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement({"id": "R1", "kind": "functional", "heritage": "PCU-A3"})


class AdmissibilityTests(unittest.TestCase):
    def test_numeric_requirement_excludes_review_of_design(self):
        allowed = admissible_methods(
            {"id": "R1", "kind": "functional", "numeric_limit": True}
        )
        self.assertNotIn("review-of-design", allowed)

    def test_non_numeric_functional_allows_review_of_design(self):
        allowed = admissible_methods({"id": "R1", "kind": "functional"})
        self.assertIn("review-of-design", allowed)

    def test_workmanship_is_seen_not_computed(self):
        allowed = admissible_methods({"id": "R1", "kind": "workmanship"})
        self.assertIn("inspection", allowed)
        self.assertNotIn("analysis", allowed)

    def test_environmental_excludes_inspection(self):
        allowed = admissible_methods({"id": "R1", "kind": "environmental"})
        self.assertNotIn("inspection", allowed)

    def test_performance_never_settled_by_looking(self):
        allowed = admissible_methods({"id": "R1", "kind": "performance"})
        self.assertNotIn("inspection", allowed)
        self.assertNotIn("review-of-design", allowed)

    def test_construction_allows_inspection(self):
        allowed = admissible_methods({"id": "R1", "kind": "construction"})
        self.assertIn("inspection", allowed)


class SimilarityTests(unittest.TestCase):
    def test_more_severe_heritage_is_admissible(self):
        verdict = similarity_admissible(HERITAGE, 14.0)
        self.assertTrue(verdict["admissible"])

    def test_equal_severity_is_admissible(self):
        verdict = similarity_admissible(HERITAGE, 20.0)
        self.assertTrue(verdict["admissible"])

    def test_equal_severity_within_tolerance_is_admissible(self):
        nudged = 20.0 * (1.0 + SEVERITY_TOLERANCE / 10.0)
        self.assertTrue(similarity_admissible(HERITAGE, nudged)["admissible"])

    def test_less_severe_heritage_is_refused(self):
        verdict = similarity_admissible(HERITAGE, 30.0)
        self.assertFalse(verdict["admissible"])
        self.assertIn("less severe", verdict["reason"])

    def test_changed_design_is_refused(self):
        heritage = dict(HERITAGE)
        heritage["design_unchanged"] = False
        self.assertFalse(similarity_admissible(heritage, 14.0)["admissible"])

    def test_missing_heritage_is_refused(self):
        self.assertFalse(similarity_admissible(None, 14.0)["admissible"])

    def test_unnamed_heritage_item_is_refused(self):
        heritage = dict(HERITAGE)
        heritage["item"] = "  "
        self.assertFalse(similarity_admissible(heritage, 14.0)["admissible"])

    def test_zero_severity_rejected(self):
        with self.assertRaises(ValueError):
            similarity_admissible(HERITAGE, 0.0)

    def test_non_numeric_severity_rejected(self):
        with self.assertRaises(ValueError):
            similarity_admissible(HERITAGE, "high")


class AllocationTests(unittest.TestCase):
    def test_adequate_allocation_is_reported_adequate(self):
        verdict = assess_allocation({"id": "R1", "kind": "performance",
                                     "numeric_limit": True, "method": "test"})
        self.assertTrue(verdict["adequate"])

    def test_review_of_design_on_a_number_is_inadequate(self):
        verdict = assess_allocation({"id": "R1", "kind": "performance",
                                     "numeric_limit": True,
                                     "method": "review-of-design"})
        self.assertFalse(verdict["adequate"])
        self.assertIn("numeric limit", verdict["reason"])

    def test_no_method_is_inadequate(self):
        verdict = assess_allocation({"id": "R1", "kind": "functional"})
        self.assertFalse(verdict["adequate"])
        self.assertIn("no verification method", verdict["reason"])

    def test_similarity_with_good_heritage_is_adequate(self):
        verdict = assess_allocation(
            {"id": "R1", "kind": "environmental", "method": "similarity",
             "heritage": dict(HERITAGE, claimed_severity=14.0)}
        )
        self.assertTrue(verdict["adequate"])

    def test_similarity_without_severity_is_inadequate(self):
        verdict = assess_allocation(
            {"id": "R1", "kind": "environmental", "method": "similarity",
             "heritage": dict(HERITAGE)}
        )
        self.assertFalse(verdict["adequate"])

    def test_verdict_lists_the_admissible_methods(self):
        verdict = assess_allocation({"id": "R1", "kind": "workmanship",
                                     "method": "inspection"})
        self.assertEqual(verdict["admissible_methods"], ["inspection", "test"])


class CoverageTests(unittest.TestCase):
    def test_counts_cover_every_method(self):
        coverage = coverage_by_method(base_requirements())
        self.assertEqual(set(coverage["counts"]), set(CANONICAL_METHODS))

    def test_test_count_is_two(self):
        self.assertEqual(coverage_by_method(base_requirements())["counts"]["test"], 2)

    def test_unallocated_requirement_is_named(self):
        requirements = base_requirements()
        del requirements[0]["method"]
        self.assertEqual(coverage_by_method(requirements)["unallocated"], ["DEV-001"])

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            coverage_by_method({"id": "R1"})


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {"requirements": base_requirements()}
        spec.update(overrides)
        return spec

    def test_well_formed_allocation_is_compliant(self):
        result = assess_verification_methods(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_inadequate_allocation_is_named(self):
        requirements = base_requirements()
        requirements[1]["method"] = "review-of-design"
        result = assess_verification_methods(self._spec(requirements=requirements))
        self.assertEqual(result["inadequate"], ["DEV-002"])
        self.assertFalse(result["compliant"])

    def test_specification_without_workmanship_is_flagged(self):
        requirements = [r for r in base_requirements() if r["kind"] != "workmanship"]
        result = assess_verification_methods(self._spec(requirements=requirements))
        self.assertTrue(any("built-in defects" in f for f in result["findings"]))

    def test_shared_claimed_severity_is_applied(self):
        requirements = base_requirements()
        requirements.append(
            {"id": "DEV-007", "kind": "environmental", "method": "similarity",
             "heritage": dict(HERITAGE)}
        )
        result = assess_verification_methods(
            self._spec(requirements=requirements, claimed_severity=14.0)
        )
        self.assertTrue(result["compliant"])

    def test_evidence_rank_is_reported_per_requirement(self):
        result = assess_verification_methods(self._spec())
        self.assertEqual(result["evidence_rank"]["DEV-002"], evidence_rank("test"))

    def test_duplicate_requirement_id_rejected(self):
        requirements = base_requirements()
        requirements.append(dict(requirements[0]))
        with self.assertRaises(ValueError):
            assess_verification_methods(self._spec(requirements=requirements))

    def test_empty_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_verification_methods({"requirements": []})

    def test_missing_requirements_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_verification_methods({})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_verification_methods(["requirements"])


if __name__ == "__main__":
    unittest.main()
