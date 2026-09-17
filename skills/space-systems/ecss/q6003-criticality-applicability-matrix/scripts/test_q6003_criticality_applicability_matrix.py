"""Contract tests for the clause 9.2 criticality applicability matrix logic."""

import unittest

from q6003_criticality_applicability_matrix_logic import (
    APPLICABILITY_VALUES,
    COVERAGE_TOLERANCE,
    CRITICALITY_CATEGORIES,
    DECLARATION_VALUES,
    RECOVERABILITY_LEVELS,
    SEVERITY_LEVELS,
    applicability_for,
    applicable_requirements,
    assess_tailoring,
    derive_category,
    mandatory_requirements,
    normalize_applicability,
    normalize_category,
    normalize_token,
    tailorable_requirements,
    tailoring_coverage,
    tailoring_findings,
    validate_declarations,
    validate_matrix,
)

ROWS = [
    {
        "requirement_id": "ar-01",
        "category-1": "applicable",
        "category-2": "applicable",
        "category-3": "applicable-with-tailoring",
        "category-4": "not-applicable",
    },
    {
        "requirement_id": "ar-02",
        "category-1": "applicable",
        "category-2": "applicable-with-tailoring",
        "category-3": "not-applicable",
        "category-4": "not-applicable",
    },
    {
        "requirement_id": "ar-03",
        "category-1": "applicable-with-tailoring",
        "category-2": "applicable-with-tailoring",
        "category-3": "applicable-with-tailoring",
        "category-4": "applicable-with-tailoring",
    },
    {
        "requirement_id": "ar-04",
        "category-1": "applicable",
        "category-2": "not-applicable",
        "category-3": "not-applicable",
        "category-4": "not-applicable",
    },
]


def declaration(req, state, justification=None):
    entry = {"requirement_id": req, "state": state}
    if justification is not None:
        entry["justification"] = justification
    return entry


def full_spec(**overrides):
    base = {
        "matrix": ROWS,
        "category": "category-2",
        "declarations": [
            declaration("ar-01", "retained"),
            declaration("ar-02", "retained"),
            declaration("ar-03", "retained"),
        ],
        "required_coverage": 1.0,
    }
    base.update(overrides)
    return base


class NormalisationTests(unittest.TestCase):
    def test_token_trimmed_and_lower_cased(self):
        self.assertEqual(normalize_token(" Category-2 ", "category"), "category-2")

    def test_blank_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("  ", "category")

    def test_category_vocabulary_is_closed(self):
        self.assertEqual(normalize_category("CATEGORY-3"), "category-3")
        with self.assertRaises(ValueError):
            normalize_category("category-9")

    def test_categories_run_most_critical_first(self):
        self.assertEqual(CRITICALITY_CATEGORIES[0], "category-1")

    def test_applicability_vocabulary_is_closed(self):
        self.assertEqual(
            normalize_applicability(" Applicable-With-Tailoring "),
            "applicable-with-tailoring",
        )
        with self.assertRaises(ValueError):
            normalize_applicability("probably")

    def test_declaration_vocabulary_is_closed(self):
        self.assertEqual(set(DECLARATION_VALUES), {"retained", "tailored", "deleted"})


class CategoryDerivationTests(unittest.TestCase):
    def test_catastrophic_effect_gives_the_top_category(self):
        self.assertEqual(
            derive_category("catastrophic", "ground-recoverable"), "category-1"
        )

    def test_recovery_never_relieves_a_catastrophic_effect(self):
        self.assertEqual(
            derive_category("catastrophic", "autonomously-recoverable"), "category-1"
        )

    def test_unrecoverable_critical_effect_stays_high(self):
        self.assertEqual(derive_category("critical", "not-recoverable"), "category-2")

    def test_recovery_relaxes_a_critical_effect_by_one_step(self):
        self.assertEqual(
            derive_category("critical", "ground-recoverable"), "category-3"
        )

    def test_non_mission_critical_function_relaxes_one_further(self):
        self.assertEqual(
            derive_category("critical", "ground-recoverable", False), "category-4"
        )

    def test_category_never_runs_past_the_bottom(self):
        self.assertEqual(
            derive_category("minor", "autonomously-recoverable", False), "category-4"
        )

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            derive_category("annoying", "not-recoverable")

    def test_unknown_recoverability_rejected(self):
        with self.assertRaises(ValueError):
            derive_category("major", "maybe-recoverable")

    def test_non_boolean_mission_flag_rejected(self):
        with self.assertRaises(ValueError):
            derive_category("major", "not-recoverable", "yes")

    def test_level_vocabularies_are_populated(self):
        self.assertIn("catastrophic", SEVERITY_LEVELS)
        self.assertIn("not-recoverable", RECOVERABILITY_LEVELS)


class MatrixTests(unittest.TestCase):
    def test_valid_matrix_indexed_by_requirement(self):
        matrix = validate_matrix(ROWS)
        self.assertEqual(sorted(matrix), ["AR-01", "AR-02", "AR-03", "AR-04"])

    def test_row_missing_a_category_rejected(self):
        broken = dict(ROWS[0])
        del broken["category-4"]
        with self.assertRaises(ValueError):
            validate_matrix([broken])

    def test_duplicate_requirement_row_rejected(self):
        with self.assertRaises(ValueError):
            validate_matrix([ROWS[0], dict(ROWS[0])])

    def test_unknown_applicability_value_rejected(self):
        broken = dict(ROWS[0])
        broken["category-2"] = "sort-of"
        with self.assertRaises(ValueError):
            validate_matrix([broken])

    def test_empty_matrix_rejected(self):
        with self.assertRaises(ValueError):
            validate_matrix([])

    def test_cell_lookup_is_case_insensitive(self):
        matrix = validate_matrix(ROWS)
        self.assertEqual(applicability_for(matrix, "AR-01", "category-3"),
                         "applicable-with-tailoring")

    def test_lookup_of_an_absent_requirement_rejected(self):
        matrix = validate_matrix(ROWS)
        with self.assertRaises(ValueError):
            applicability_for(matrix, "ar-99", "category-1")

    def test_applicability_value_list_is_complete(self):
        self.assertEqual(len(APPLICABILITY_VALUES), 3)


class RequirementSetTests(unittest.TestCase):
    def setUp(self):
        self.matrix = validate_matrix(ROWS)

    def test_applicable_set_shrinks_with_falling_criticality(self):
        one = applicable_requirements(self.matrix, "category-1")
        four = applicable_requirements(self.matrix, "category-4")
        self.assertEqual(one, ["AR-01", "AR-02", "AR-03", "AR-04"])
        self.assertEqual(four, ["AR-03"])

    def test_mandatory_set_excludes_tailorable_rows(self):
        self.assertEqual(
            mandatory_requirements(self.matrix, "category-2"), ["AR-01"]
        )

    def test_tailorable_set_named_separately(self):
        self.assertEqual(
            tailorable_requirements(self.matrix, "category-2"), ["AR-02", "AR-03"]
        )

    def test_mandatory_and_tailorable_partition_the_applicable_set(self):
        for category in CRITICALITY_CATEGORIES:
            combined = set(mandatory_requirements(self.matrix, category)) | set(
                tailorable_requirements(self.matrix, category)
            )
            self.assertEqual(combined, set(applicable_requirements(self.matrix, category)))

    def test_empty_matrix_mapping_rejected(self):
        with self.assertRaises(ValueError):
            applicable_requirements({}, "category-1")


class DeclarationTests(unittest.TestCase):
    def test_declarations_indexed_by_requirement(self):
        declared = validate_declarations([declaration("ar-01", "retained")])
        self.assertEqual(declared["AR-01"], ("retained", None))

    def test_duplicate_declaration_rejected(self):
        with self.assertRaises(ValueError):
            validate_declarations(
                [declaration("ar-01", "retained"), declaration("AR-01", "deleted")]
            )

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_declarations([declaration("ar-01", "ignored")])

    def test_declaration_missing_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_declarations([{"requirement_id": "ar-01"}])

    def test_declarations_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_declarations({"requirement_id": "ar-01"})


class FindingTests(unittest.TestCase):
    def setUp(self):
        self.matrix = validate_matrix(ROWS)

    def test_clean_declaration_has_no_findings(self):
        issues = tailoring_findings(
            self.matrix, "category-2", full_spec()["declarations"]
        )
        for key in issues:
            self.assertEqual(issues[key], [])

    def test_deletion_without_justification_is_reported(self):
        declarations = [
            declaration("ar-01", "retained"),
            declaration("ar-02", "deleted"),
            declaration("ar-03", "retained"),
        ]
        issues = tailoring_findings(self.matrix, "category-2", declarations)
        self.assertEqual(issues["unjustified_deletions"], ["AR-02"])

    def test_justified_deletion_of_a_tailorable_row_is_clean(self):
        declarations = [
            declaration("ar-01", "retained"),
            declaration("ar-02", "deleted", "covered by the lot-level screen"),
            declaration("ar-03", "retained"),
        ]
        issues = tailoring_findings(self.matrix, "category-2", declarations)
        self.assertEqual(issues["unjustified_deletions"], [])
        self.assertEqual(issues["weakened_mandatory"], [])

    def test_mandatory_row_cannot_be_deleted_even_with_a_justification(self):
        declarations = [
            declaration("ar-01", "deleted", "the programme accepted the risk"),
            declaration("ar-02", "retained"),
            declaration("ar-03", "retained"),
        ]
        issues = tailoring_findings(self.matrix, "category-2", declarations)
        self.assertEqual(issues["weakened_mandatory"], ["AR-01"])

    def test_mandatory_row_cannot_be_tailored(self):
        declarations = [
            declaration("ar-01", "tailored", "reduced sample"),
            declaration("ar-02", "retained"),
            declaration("ar-03", "retained"),
        ]
        issues = tailoring_findings(self.matrix, "category-2", declarations)
        self.assertEqual(issues["weakened_mandatory"], ["AR-01"])

    def test_declaration_outside_the_matrix_is_reported(self):
        declarations = full_spec()["declarations"] + [declaration("ar-77", "retained")]
        issues = tailoring_findings(self.matrix, "category-2", declarations)
        self.assertEqual(issues["outside_the_matrix"], ["AR-77"])

    def test_undeclared_applicable_requirement_is_reported(self):
        declarations = [declaration("ar-01", "retained")]
        issues = tailoring_findings(self.matrix, "category-2", declarations)
        self.assertEqual(issues["undeclared"], ["AR-02", "AR-03"])

    def test_declaring_a_non_applicable_row_is_not_a_finding(self):
        declarations = full_spec()["declarations"] + [declaration("ar-04", "deleted")]
        issues = tailoring_findings(self.matrix, "category-2", declarations)
        self.assertEqual(issues["unjustified_deletions"], [])


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.matrix = validate_matrix(ROWS)

    def test_full_coverage_on_a_clean_declaration(self):
        value = tailoring_coverage(
            self.matrix, "category-2", full_spec()["declarations"]
        )
        self.assertAlmostEqual(value, 1.0, places=9)

    def test_undeclared_requirement_lowers_coverage(self):
        value = tailoring_coverage(
            self.matrix, "category-2", [declaration("ar-01", "retained")]
        )
        self.assertAlmostEqual(value, 1.0 / 3.0, places=9)

    def test_justified_tailoring_of_a_tailorable_row_counts_as_sound(self):
        declarations = [
            declaration("ar-01", "retained"),
            declaration("ar-02", "tailored", "reduced sample agreed"),
            declaration("ar-03", "retained"),
        ]
        value = tailoring_coverage(self.matrix, "category-2", declarations)
        self.assertAlmostEqual(value, 1.0, places=9)

    def test_weakening_a_mandatory_row_does_not_count_as_sound(self):
        declarations = [
            declaration("ar-01", "tailored", "reduced sample"),
            declaration("ar-02", "retained"),
            declaration("ar-03", "retained"),
        ]
        value = tailoring_coverage(self.matrix, "category-2", declarations)
        self.assertAlmostEqual(value, 2.0 / 3.0, places=9)

    def test_tolerance_is_small_and_positive(self):
        self.assertGreater(COVERAGE_TOLERANCE, 0.0)
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


class AssessmentTests(unittest.TestCase):
    def test_clean_tailoring_is_acceptable(self):
        result = assess_tailoring(full_spec())
        self.assertTrue(result["tailoring_acceptable"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["mandatory_requirements"], ["AR-01"])

    def test_category_derived_when_not_declared(self):
        spec = full_spec()
        del spec["category"]
        spec["severity"] = "critical"
        spec["recoverability"] = "not-recoverable"
        result = assess_tailoring(spec)
        self.assertEqual(result["category"], "category-2")
        self.assertEqual(result["derived_category"], "category-2")

    def test_declared_category_is_used_verbatim(self):
        result = assess_tailoring(full_spec(category="category-1"))
        self.assertIsNone(result["derived_category"])
        self.assertEqual(len(result["applicable_requirements"]), 4)

    def test_spec_without_category_or_severity_rejected(self):
        spec = full_spec()
        del spec["category"]
        with self.assertRaises(ValueError):
            assess_tailoring(spec)

    def test_weakened_mandatory_row_blocks_the_tailoring(self):
        spec = full_spec(
            declarations=[
                declaration("ar-01", "deleted", "risk accepted"),
                declaration("ar-02", "retained"),
                declaration("ar-03", "retained"),
            ]
        )
        result = assess_tailoring(spec)
        self.assertFalse(result["tailoring_acceptable"])
        self.assertIn("cannot be tailored away", " ".join(result["findings"]))

    def test_exactly_met_coverage_floor_passes(self):
        spec = full_spec(
            declarations=[declaration("ar-01", "retained")],
            required_coverage=1.0 / 3.0,
        )
        result = assess_tailoring(spec)
        self.assertTrue(result["coverage_ok"])
        self.assertAlmostEqual(
            result["tailoring_coverage"], result["required_coverage"], places=9
        )

    def test_out_of_range_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_tailoring(full_spec(required_coverage=2.0))

    def test_spec_missing_matrix_rejected(self):
        spec = full_spec()
        del spec["matrix"]
        with self.assertRaises(ValueError):
            assess_tailoring(spec)

    def test_spec_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_tailoring(["matrix"])

    def test_findings_name_each_defect_kind(self):
        spec = full_spec(
            declarations=[
                declaration("ar-01", "tailored", "reduced sample"),
                declaration("ar-02", "deleted"),
                declaration("ar-77", "retained"),
            ]
        )
        result = assess_tailoring(spec)
        joined = " | ".join(result["findings"])
        self.assertIn("deleted with no justification", joined)
        self.assertIn("cannot be tailored away", joined)
        self.assertIn("the matrix does not carry", joined)
        self.assertIn("is not declared", joined)


if __name__ == "__main__":
    unittest.main()
