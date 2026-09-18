"""Contract tests for the clause 5.8.4.2 GSE acceptance logic."""

import unittest

from q20_gse_acceptance_logic import (
    ACCEPTANCE_METHODS,
    CRITICALITIES,
    DEMONSTRATIVE_METHODS,
    acceptance_coverage,
    assess_gse_acceptance,
    evaluate_measurement,
    grade_results,
    method_adequacy_findings,
    normalize_token,
    release_verdict,
    validate_requirements,
    validate_results,
)

REQUIREMENTS = [
    {
        "id": "GSE-R-01",
        "criticality": "safety-critical",
        "planned_method": "test",
        "limit": 2.0,
        "limit_sense": "min",
    },
    {"id": "GSE-R-02", "criticality": "operational", "planned_method": "inspection"},
    {
        "id": "GSE-R-03",
        "criticality": "operational",
        "planned_method": "test",
        "limit": 0.5,
        "limit_sense": "max",
    },
    {"id": "GSE-R-04", "criticality": "convenience", "planned_method": "review-of-design"},
]

RESULTS = [
    {"requirement_id": "GSE-R-01", "method": "test", "outcome": "pass", "measured": 2.4},
    {"requirement_id": "GSE-R-02", "method": "inspection", "outcome": "pass"},
    {"requirement_id": "GSE-R-03", "method": "test", "outcome": "pass", "measured": 0.31},
    {"requirement_id": "GSE-R-04", "method": "review-of-design", "outcome": "pass"},
]


def _spec(**overrides):
    spec = {
        "requirements": [dict(r) for r in REQUIREMENTS],
        "results": [dict(r) for r in RESULTS],
        "required_coverage": 1.0,
    }
    spec.update(overrides)
    return spec


class NormalizeTokenTests(unittest.TestCase):
    def test_case_and_separator_folded(self):
        self.assertEqual(normalize_token("Review_Of Design"), "review-of-design")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("")


class ValidateRequirementTests(unittest.TestCase):
    def test_valid_set_is_keyed_by_identifier(self):
        agreed = validate_requirements(REQUIREMENTS)
        self.assertEqual(sorted(agreed), ["gse-r-01", "gse-r-02", "gse-r-03", "gse-r-04"])

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements([REQUIREMENTS[0], dict(REQUIREMENTS[0])])

    def test_unknown_criticality_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements([dict(REQUIREMENTS[1], criticality="nice-to-have")])

    def test_unknown_method_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements([dict(REQUIREMENTS[1], planned_method="opinion")])

    def test_limit_without_sense_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements([dict(REQUIREMENTS[1], limit=4.0)])

    def test_sense_without_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements([dict(REQUIREMENTS[1], limit_sense="max")])

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements([])

    def test_vocabularies_are_closed(self):
        self.assertIn("safety-critical", CRITICALITIES)
        self.assertEqual(len(ACCEPTANCE_METHODS), 4)
        self.assertEqual(set(DEMONSTRATIVE_METHODS), {"test", "inspection"})


class ValidateResultTests(unittest.TestCase):
    def test_result_against_an_unagreed_requirement_rejected(self):
        results = RESULTS + [
            {"requirement_id": "GSE-R-99", "method": "test", "outcome": "pass"}
        ]
        with self.assertRaises(ValueError):
            validate_results(results, REQUIREMENTS)

    def test_unknown_outcome_rejected(self):
        results = [dict(RESULTS[1], outcome="probably")]
        with self.assertRaises(ValueError):
            validate_results(results, REQUIREMENTS)

    def test_non_boolean_waiver_rejected(self):
        results = [dict(RESULTS[1], waiver_approved="yes")]
        with self.assertRaises(ValueError):
            validate_results(results, REQUIREMENTS)

    def test_waiver_defaults_to_absent(self):
        graded = validate_results([dict(RESULTS[1])], REQUIREMENTS)
        self.assertFalse(graded[0]["waiver_approved"])


class MeasurementTests(unittest.TestCase):
    def test_value_above_a_minimum_passes_with_positive_margin(self):
        verdict = evaluate_measurement(2.4, 2.0, "min")
        self.assertTrue(verdict["pass"])
        self.assertAlmostEqual(verdict["margin"], 0.4, places=9)

    def test_value_exactly_on_a_minimum_passes(self):
        verdict = evaluate_measurement(2.0, 2.0, "min")
        self.assertTrue(verdict["pass"])
        self.assertAlmostEqual(verdict["margin"], 0.0, places=9)

    def test_value_exactly_on_a_maximum_passes(self):
        verdict = evaluate_measurement(0.5, 0.5, "max")
        self.assertTrue(verdict["pass"])
        self.assertAlmostEqual(verdict["margin"], 0.0, places=9)

    def test_value_over_a_maximum_fails_with_negative_margin(self):
        verdict = evaluate_measurement(0.8, 0.5, "max")
        self.assertFalse(verdict["pass"])
        self.assertAlmostEqual(verdict["margin"], -0.3, places=9)

    def test_unknown_sense_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_measurement(1.0, 1.0, "about")

    def test_non_numeric_measurement_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_measurement("2.4", 2.0, "min")


class GradeResultTests(unittest.TestCase):
    def test_clean_acceptance_raises_no_finding(self):
        graded = grade_results(RESULTS, REQUIREMENTS)
        self.assertEqual(graded["findings"], [])

    def test_pass_contradicted_by_its_measurement_is_a_finding(self):
        results = [dict(RESULTS[0], measured=1.2)]
        graded = grade_results(results, REQUIREMENTS)
        self.assertTrue(any("misses the bound" in f for f in graded["findings"]))

    def test_failure_without_a_waiver_is_a_finding(self):
        results = [dict(RESULTS[1], outcome="fail")]
        graded = grade_results(results, REQUIREMENTS)
        self.assertTrue(any("no approved waiver" in f for f in graded["findings"]))

    def test_failure_with_a_waiver_raises_no_finding(self):
        results = [dict(RESULTS[1], outcome="fail", waiver_approved=True)]
        graded = grade_results(results, REQUIREMENTS)
        self.assertEqual(graded["findings"], [])

    def test_method_substitution_is_a_finding(self):
        results = [dict(RESULTS[2], method="analysis", measured=0.31)]
        graded = grade_results(results, REQUIREMENTS)
        self.assertTrue(any("where test was planned" in f for f in graded["findings"]))

    def test_quantitative_outcome_without_a_measurement_rejected(self):
        results = [{"requirement_id": "GSE-R-03", "method": "test", "outcome": "pass"}]
        with self.assertRaises(ValueError):
            grade_results(results, REQUIREMENTS)

    def test_margin_is_kept_alongside_the_verdict(self):
        graded = grade_results(RESULTS, REQUIREMENTS)
        by_id = {e["requirement_id"]: e for e in graded["graded"]}
        self.assertAlmostEqual(by_id["gse-r-03"]["margin"], 0.19, places=9)


class MethodAdequacyTests(unittest.TestCase):
    def test_safety_critical_requirement_shown_by_test_is_clean(self):
        self.assertEqual(method_adequacy_findings(RESULTS, REQUIREMENTS), [])

    def test_safety_critical_requirement_argued_on_paper_is_a_finding(self):
        results = [dict(RESULTS[0], method="analysis")]
        findings = method_adequacy_findings(results, REQUIREMENTS)
        self.assertEqual(len(findings), 1)
        self.assertIn("gse-r-01", findings[0])

    def test_convenience_requirement_on_paper_is_not_a_finding(self):
        self.assertEqual(method_adequacy_findings([dict(RESULTS[3])], REQUIREMENTS), [])


class CoverageTests(unittest.TestCase):
    def test_full_acceptance_is_unity(self):
        self.assertAlmostEqual(acceptance_coverage(RESULTS, REQUIREMENTS), 1.0, places=9)

    def test_half_the_set_is_one_half(self):
        self.assertAlmostEqual(acceptance_coverage(RESULTS[:2], REQUIREMENTS), 0.5, places=9)

    def test_a_later_not_run_reopens_a_requirement(self):
        results = RESULTS + [dict(RESULTS[0], outcome="not-run", measured=None)]
        self.assertAlmostEqual(acceptance_coverage(results, REQUIREMENTS), 0.75, places=9)

    def test_empty_result_set_is_zero_coverage(self):
        self.assertAlmostEqual(acceptance_coverage([], REQUIREMENTS), 0.0, places=9)


class ReleaseVerdictTests(unittest.TestCase):
    def test_clean_acceptance_releases(self):
        self.assertEqual(release_verdict([], []), "released")

    def test_waivered_failure_limits_the_equipment(self):
        self.assertEqual(release_verdict([], ["gse-r-02"]), "released-with-limitations")

    def test_any_finding_stops_the_release(self):
        self.assertEqual(release_verdict(["finding"], ["gse-r-02"]), "not-released")

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            release_verdict("finding", [])


class AssessGseAcceptanceTests(unittest.TestCase):
    def test_clean_acceptance_releases_the_equipment(self):
        result = assess_gse_acceptance(_spec())
        self.assertEqual(result["verdict"], "released")
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)

    def test_coverage_shortfall_stops_the_release(self):
        result = assess_gse_acceptance(_spec(results=[dict(r) for r in RESULTS[:2]]))
        self.assertEqual(result["verdict"], "not-released")
        self.assertTrue(any("covered" in f for f in result["findings"]))

    def test_waivered_failure_yields_a_limited_release(self):
        results = [dict(r) for r in RESULTS]
        results[1] = dict(results[1], outcome="fail", waiver_approved=True)
        result = assess_gse_acceptance(_spec(results=results))
        self.assertEqual(result["verdict"], "released-with-limitations")
        self.assertEqual(len(result["limitations"]), 1)

    def test_coverage_target_met_exactly_is_not_a_shortfall(self):
        result = assess_gse_acceptance(
            _spec(results=[dict(r) for r in RESULTS[:2]], required_coverage=0.5)
        )
        self.assertEqual(result["verdict"], "released")

    def test_out_of_range_coverage_target_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_acceptance(_spec(required_coverage=1.5))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["results"]
        with self.assertRaises(ValueError):
            assess_gse_acceptance(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_acceptance(["requirements"])

    def test_findings_accumulate_across_every_check(self):
        results = [
            dict(RESULTS[0], method="analysis", measured=1.0),
            dict(RESULTS[1], outcome="fail"),
        ]
        result = assess_gse_acceptance(_spec(results=results))
        self.assertEqual(result["verdict"], "not-released")
        self.assertGreaterEqual(len(result["findings"]), 5)


if __name__ == "__main__":
    unittest.main()
