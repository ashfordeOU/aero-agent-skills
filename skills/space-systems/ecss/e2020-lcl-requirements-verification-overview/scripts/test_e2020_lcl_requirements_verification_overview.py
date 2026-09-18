"""Contract tests for the clause 4.1 compliance-method overview.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused coverage policy,
a method token outside the vocabulary, a requirement carrying no method, a
quantitative limit left to design review alone, a duplicate identifier and
a matrix that falls under its declared coverage floor.
"""

import unittest

from e2020_lcl_requirements_verification_overview_logic import (
    ADMISSIBLE_METHODS,
    COVERAGE_BELOW_POLICY_FLOOR,
    DEFAULT_VERIFICATION_POLICY,
    EVIDENCE_BEARING_METHODS,
    MATRIX_COVERS_REQUIREMENT_SET,
    METHOD_ANALYSIS,
    METHOD_INSPECTION,
    METHOD_NOT_ESTABLISHED,
    METHOD_REVIEW_OF_DESIGN,
    METHOD_TEST,
    NO_METHOD,
    QUANTITATIVE_LIMIT_WITHOUT_EVIDENCE,
    assess_verification_overview,
    covered_fraction,
    evidence_bearing_fraction,
    normalise_method,
    requirement_coverage,
    requirement_coverages,
    requirements_grouped_by_method,
    uncovered_requirements,
    validate_requirement_record,
    validate_verification_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_VERIFICATION_POLICY)
    policy.update(overrides)
    return policy


def _requirements():
    return [
        {
            "id": "R-4.1-01",
            "clause": "5.2.1",
            "methods": [METHOD_TEST],
            "states_quantitative_limit": True,
        },
        {
            "id": "R-4.1-02",
            "clause": "5.2.2",
            "methods": [METHOD_ANALYSIS, METHOD_REVIEW_OF_DESIGN],
            "states_quantitative_limit": True,
        },
        {
            "id": "R-4.1-03",
            "clause": "6.1.1",
            "methods": [METHOD_INSPECTION],
            "states_quantitative_limit": False,
        },
        {
            "id": "R-4.1-04",
            "clause": "6.1.2",
            "methods": [METHOD_REVIEW_OF_DESIGN],
            "states_quantitative_limit": False,
        },
    ]


def _case(**overrides):
    case = {
        "matrix_reference": "VCD-2020 issue B",
        "requirements": _requirements(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_verification_policy(DEFAULT_VERIFICATION_POLICY),
            DEFAULT_VERIFICATION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_policy("min_covered_fraction")

    def test_covered_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_policy(_policy(min_covered_fraction=1.4))

    def test_negative_evidence_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_policy(
                _policy(min_evidence_bearing_fraction=-0.1)
            )

    def test_evidence_floor_above_coverage_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_policy(
                _policy(min_covered_fraction=0.4, min_evidence_bearing_fraction=0.9)
            )

    def test_non_numeric_fraction_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_policy(_policy(min_covered_fraction="all"))


class MethodVocabularyTests(unittest.TestCase):
    def test_every_admissible_method_normalises(self):
        for method in ADMISSIBLE_METHODS:
            self.assertEqual(normalise_method(method.upper()), method)

    def test_evidence_bearing_methods_are_a_subset(self):
        for method in EVIDENCE_BEARING_METHODS:
            self.assertIn(method, ADMISSIBLE_METHODS)

    def test_invented_method_token_rejected(self):
        with self.assertRaises(ValueError):
            normalise_method("by-similarity")

    def test_blank_method_token_rejected(self):
        with self.assertRaises(ValueError):
            normalise_method("   ")

    def test_non_string_method_token_rejected(self):
        with self.assertRaises(ValueError):
            normalise_method(4)


class RequirementRecordTests(unittest.TestCase):
    def test_a_valid_record_reads_back(self):
        identifier, methods, quantitative, clause = validate_requirement_record(
            _requirements()[0]
        )
        self.assertEqual(identifier, "R-4.1-01")
        self.assertEqual(methods, (METHOD_TEST,))
        self.assertTrue(quantitative)
        self.assertEqual(clause, "5.2.1")

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement_record({"id": "  ", "methods": [METHOD_TEST]})

    def test_methods_given_as_a_bare_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement_record({"id": "R-9", "methods": METHOD_TEST})

    def test_non_boolean_quantitative_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirement_record(
                {
                    "id": "R-9",
                    "methods": [METHOD_TEST],
                    "states_quantitative_limit": "yes",
                }
            )

    def test_repeated_method_collapses(self):
        _, methods, _, _ = validate_requirement_record(
            {"id": "R-9", "methods": [METHOD_TEST, "TEST", METHOD_TEST]}
        )
        self.assertEqual(methods, (METHOD_TEST,))


class CoverageTests(unittest.TestCase):
    def test_a_tested_limit_is_covered(self):
        cover = requirement_coverage(_requirements()[0])
        self.assertTrue(cover["covered"])
        self.assertEqual(cover["findings"], ())

    def test_a_requirement_with_no_method_is_uncovered(self):
        cover = requirement_coverage({"id": "R-9", "methods": []})
        self.assertFalse(cover["covered"])
        self.assertIn(NO_METHOD, cover["findings"])

    def test_a_limit_left_to_design_review_is_a_finding(self):
        cover = requirement_coverage(
            {
                "id": "R-9",
                "methods": [METHOD_REVIEW_OF_DESIGN, METHOD_INSPECTION],
                "states_quantitative_limit": True,
            }
        )
        self.assertFalse(cover["covered"])
        self.assertIn(QUANTITATIVE_LIMIT_WITHOUT_EVIDENCE, cover["findings"])

    def test_a_non_quantitative_requirement_may_rest_on_review(self):
        cover = requirement_coverage(_requirements()[3])
        self.assertTrue(cover["covered"])

    def test_duplicate_requirement_identifier_rejected(self):
        requirements = _requirements()
        requirements[1]["id"] = requirements[0]["id"]
        with self.assertRaises(ValueError):
            requirement_coverages(requirements)

    def test_empty_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            requirement_coverages([])

    def test_non_sequence_requirement_set_rejected(self):
        with self.assertRaises(ValueError):
            requirement_coverages({"id": "R-9"})


class MatrixArithmeticTests(unittest.TestCase):
    def test_a_complete_matrix_is_fully_covered(self):
        coverages = requirement_coverages(_requirements())
        self.assertAlmostEqual(covered_fraction(coverages), 1.0, places=12)

    def test_evidence_bearing_share_counts_test_and_analysis_only(self):
        coverages = requirement_coverages(_requirements())
        self.assertAlmostEqual(
            evidence_bearing_fraction(coverages), 0.5, places=12
        )

    def test_one_missing_method_moves_the_covered_share(self):
        requirements = _requirements()
        requirements[2]["methods"] = []
        coverages = requirement_coverages(requirements)
        self.assertAlmostEqual(covered_fraction(coverages), 0.75, places=12)

    def test_grouping_lists_every_admissible_method_key(self):
        grouped = requirements_grouped_by_method(
            requirement_coverages(_requirements())
        )
        self.assertEqual(set(grouped), set(ADMISSIBLE_METHODS))
        self.assertEqual(grouped[METHOD_TEST], ("R-4.1-01",))
        self.assertEqual(
            grouped[METHOD_REVIEW_OF_DESIGN], ("R-4.1-02", "R-4.1-04")
        )

    def test_uncovered_requirements_are_named(self):
        requirements = _requirements()
        requirements[0]["methods"] = []
        coverages = requirement_coverages(requirements)
        self.assertEqual(uncovered_requirements(coverages), ("R-4.1-01",))

    def test_covered_fraction_refuses_an_empty_sequence(self):
        with self.assertRaises(ValueError):
            covered_fraction([])


class AssessmentTests(unittest.TestCase):
    def test_a_complete_matrix_closes_clean(self):
        result = assess_verification_overview(_case())
        self.assertEqual(result["verdict"], MATRIX_COVERS_REQUIREMENT_SET)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["requirement_count"], 4)

    def test_a_missing_matrix_reference_closes_the_assessment(self):
        result = assess_verification_overview(_case(matrix_reference="   "))
        self.assertEqual(result["verdict"], METHOD_NOT_ESTABLISHED)
        self.assertEqual(result["coverages"], ())

    def test_an_absent_matrix_reference_closes_the_assessment(self):
        case = _case()
        del case["matrix_reference"]
        result = assess_verification_overview(case)
        self.assertEqual(result["verdict"], METHOD_NOT_ESTABLISHED)

    def test_an_unmethoded_requirement_fails_the_coverage_floor(self):
        requirements = _requirements()
        requirements[3]["methods"] = []
        result = assess_verification_overview(_case(requirements=requirements))
        self.assertEqual(result["verdict"], COVERAGE_BELOW_POLICY_FLOOR)
        self.assertEqual(result["uncovered_requirements"], ("R-4.1-04",))
        self.assertTrue(
            any("declares no compliance method" in f for f in result["findings"])
        )

    def test_a_review_only_case_fails_the_evidence_floor(self):
        requirements = [
            {
                "id": "R-4.1-10",
                "methods": [METHOD_REVIEW_OF_DESIGN],
                "states_quantitative_limit": False,
            },
            {
                "id": "R-4.1-11",
                "methods": [METHOD_INSPECTION],
                "states_quantitative_limit": False,
            },
        ]
        result = assess_verification_overview(_case(requirements=requirements))
        self.assertEqual(result["verdict"], COVERAGE_BELOW_POLICY_FLOOR)
        self.assertAlmostEqual(result["covered_fraction"], 1.0, places=12)
        self.assertAlmostEqual(result["evidence_bearing_fraction"], 0.0, places=12)

    def test_an_evidence_share_exactly_on_the_floor_is_admissible(self):
        result = assess_verification_overview(
            _case(), _policy(min_evidence_bearing_fraction=0.5)
        )
        self.assertAlmostEqual(result["evidence_bearing_fraction"], 0.5, places=9)
        self.assertEqual(result["verdict"], MATRIX_COVERS_REQUIREMENT_SET)

    def test_single_method_requirements_raise_an_advisory_without_moving_the_verdict(self):
        result = assess_verification_overview(_case())
        self.assertEqual(result["verdict"], MATRIX_COVERS_REQUIREMENT_SET)
        self.assertTrue(any("single method" in a for a in result["advisories"]))

    def test_a_limit_on_review_alone_is_reported_with_its_methods(self):
        requirements = _requirements()
        requirements[0]["methods"] = [METHOD_REVIEW_OF_DESIGN]
        result = assess_verification_overview(_case(requirements=requirements))
        self.assertEqual(result["verdict"], COVERAGE_BELOW_POLICY_FLOOR)
        self.assertTrue(
            any("needs test or analysis" in f for f in result["findings"])
        )

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_verification_overview(["matrix_reference"])

    def test_an_invented_method_inside_a_case_is_refused(self):
        requirements = _requirements()
        requirements[1]["methods"] = ["heritage"]
        with self.assertRaises(ValueError):
            assess_verification_overview(_case(requirements=requirements))


if __name__ == "__main__":
    unittest.main()
