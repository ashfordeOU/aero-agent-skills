"""Contract tests for the clause 5.1.2.2 component control plan matrix logic.

Each test class follows one step of the SKILL.md workflow: the input
validation, the per-record disposition, the coverage gate and the closing
verdict. Offline, stdlib unittest; run it as the review checklist before
the leaf is issued.
"""

import unittest

from q60_class_2_component_control_plan_logic import (
    CLAUSE_PATTERN,
    COMPLIANCE_STATUSES,
    INDEX_TOLERANCE,
    MANDATORY_ROW_ATTRIBUTES,
    STATUS_CREDIT,
    assess_compliance_matrix,
    clause_row_coverage,
    compliance_index,
    evaluate_row,
    normalize_clause_id,
    row_completeness,
    status_credit,
    status_obligations,
    validate_applicable_clauses,
)

CLAUSES = [
    {"clause": "5.1.2.1", "weight": 3},
    {"clause": "5.1.2.2", "weight": 4},
    {"clause": "5.1.3", "weight": 2},
    {"clause": "5.1.4", "weight": 1},
]


def row(clause, status="compliant", **overrides):
    """Return one acceptable matrix row for the given clause and status."""
    base = {
        "row_id": "R-" + clause,
        "clause": clause,
        "status": status,
        "evidence_reference": "CCP-PROC-014 section 3",
        "justification": "tailored against the Class 2 procurement route",
        "approval_reference": "CUST-APPR-2026-011",
    }
    base.update(overrides)
    return base


def full_rows():
    """Return one compliant row per applicable clause."""
    return [row(entry["clause"]) for entry in CLAUSES]


def index():
    return validate_applicable_clauses(CLAUSES)


class ClauseIdTests(unittest.TestCase):
    def test_dotted_path_accepted(self):
        self.assertEqual(normalize_clause_id(" 5.1.2.2 "), "5.1.2.2")

    def test_single_number_accepted(self):
        self.assertEqual(normalize_clause_id("5"), "5")

    def test_prose_reference_rejected(self):
        with self.assertRaises(ValueError):
            normalize_clause_id("clause five point one")

    def test_trailing_dot_rejected(self):
        with self.assertRaises(ValueError):
            normalize_clause_id("5.1.")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalize_clause_id("   ")

    def test_pattern_is_anchored_both_ends(self):
        self.assertIsNone(CLAUSE_PATTERN.match("a5.1"))
        self.assertIsNone(CLAUSE_PATTERN.match("5.1b"))


class StatusTests(unittest.TestCase):
    def test_compliance_needs_evidence(self):
        self.assertTrue(status_obligations("compliant")["needs_evidence"])

    def test_compliance_needs_no_justification(self):
        self.assertFalse(status_obligations("compliant")["needs_justification"])

    def test_partial_compliance_needs_an_approval(self):
        self.assertTrue(status_obligations("partially-compliant")["needs_approval"])

    def test_non_applicability_needs_a_rationale(self):
        obligations = status_obligations("not-applicable")
        self.assertTrue(obligations["needs_justification"])
        self.assertFalse(obligations["applies"])

    def test_unknown_status_rejected(self):
        with self.assertRaises(ValueError):
            status_obligations("mostly-fine")

    def test_partial_credit_sits_between_the_ends(self):
        self.assertGreater(status_credit("partially-compliant"), 0.0)
        self.assertLess(status_credit("partially-compliant"), 1.0)

    def test_tailored_out_status_earns_no_credit_and_says_so(self):
        with self.assertRaises(ValueError):
            status_credit("not-applicable")

    def test_every_applying_status_has_a_credit(self):
        for name, obligations in COMPLIANCE_STATUSES.items():
            if obligations["applies"]:
                self.assertIn(name, STATUS_CREDIT)


class RowCompletenessTests(unittest.TestCase):
    def test_complete_row_scores_one(self):
        missing, fraction = row_completeness(row("5.1.3"))
        self.assertEqual(missing, ())
        self.assertAlmostEqual(fraction, 1.0, places=9)

    def test_blank_status_counts_as_missing(self):
        missing, fraction = row_completeness(row("5.1.3", status="  "))
        self.assertIn("status", missing)
        self.assertAlmostEqual(
            fraction,
            (len(MANDATORY_ROW_ATTRIBUTES) - 1) / len(MANDATORY_ROW_ATTRIBUTES),
            places=9,
        )

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            row_completeness("5.1.3 compliant")


class ApplicableClauseTests(unittest.TestCase):
    def test_weights_are_read_back(self):
        self.assertEqual(index()["5.1.2.2"], 4)

    def test_default_weight_is_one(self):
        built = validate_applicable_clauses([{"clause": "5.2"}])
        self.assertEqual(built["5.2"], 1)

    def test_duplicate_clause_rejected(self):
        with self.assertRaises(ValueError):
            validate_applicable_clauses(
                [{"clause": "5.1.3"}, {"clause": "5.1.3", "weight": 2}]
            )

    def test_zero_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_applicable_clauses([{"clause": "5.1.3", "weight": 0}])

    def test_empty_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_applicable_clauses([])


class EvaluateRowTests(unittest.TestCase):
    def setUp(self):
        self.index = index()

    def test_compliant_row_with_evidence_is_accepted(self):
        record = evaluate_row(row("5.1.3"), self.index)
        self.assertEqual(record["disposition"], "accepted")
        self.assertAlmostEqual(record["credit"], 1.0, places=9)

    def test_compliance_without_evidence_is_refused(self):
        record = evaluate_row(row("5.1.3", evidence_reference=""), self.index)
        self.assertEqual(record["disposition"], "evidence-absent")

    def test_deviation_without_justification_is_refused(self):
        record = evaluate_row(
            row("5.1.3", status="not-compliant", justification=None), self.index
        )
        self.assertEqual(record["disposition"], "justification-absent")

    def test_deviation_without_approval_is_refused(self):
        record = evaluate_row(
            row("5.1.3", status="partially-compliant", approval_reference="  "),
            self.index,
        )
        self.assertEqual(record["disposition"], "approval-absent")

    def test_unjustified_non_applicability_is_refused(self):
        record = evaluate_row(
            row("5.1.4", status="not-applicable", justification=""), self.index
        )
        self.assertEqual(record["disposition"], "justification-absent")

    def test_accepted_non_applicability_leaves_the_index(self):
        record = evaluate_row(row("5.1.4", status="not-applicable"), self.index)
        self.assertEqual(record["disposition"], "accepted")
        self.assertFalse(record["counts_in_index"])

    def test_row_outside_the_applicable_set_is_named(self):
        record = evaluate_row(row("9.9.9"), self.index)
        self.assertEqual(record["disposition"], "clause-outside-applicable-set")

    def test_malformed_clause_is_named(self):
        stray = dict(row("5.1.3"), clause="annex B")
        record = evaluate_row(stray, self.index)
        self.assertEqual(record["disposition"], "clause-malformed")

    def test_unrecognised_status_is_named(self):
        record = evaluate_row(row("5.1.3", status="broadly-ok"), self.index)
        self.assertEqual(record["disposition"], "status-unrecognised")

    def test_second_row_against_one_clause_is_a_duplicate(self):
        record = evaluate_row(row("5.1.3"), self.index, already_answered={"5.1.3"})
        self.assertEqual(record["disposition"], "duplicate-clause-row")

    def test_incomplete_row_stops_before_any_other_test(self):
        record = evaluate_row(row("5.1.3", row_id=None), self.index)
        self.assertEqual(record["disposition"], "record-incomplete")

    def test_empty_clause_index_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_row(row("5.1.3"), {})


class CoverageAndIndexTests(unittest.TestCase):
    def setUp(self):
        self.index = index()

    def test_full_matrix_covers_every_clause(self):
        records = [evaluate_row(entry, self.index) for entry in full_rows()]
        coverage, unanswered = clause_row_coverage(records, self.index)
        self.assertAlmostEqual(coverage, 1.0, places=9)
        self.assertEqual(unanswered, ())

    def test_coverage_is_clause_weighted(self):
        records = [evaluate_row(row("5.1.2.2"), self.index)]
        coverage, unanswered = clause_row_coverage(records, self.index)
        self.assertAlmostEqual(coverage, 4 / 10, places=9)
        self.assertEqual(unanswered, ("5.1.2.1", "5.1.3", "5.1.4"))

    def test_full_compliance_indexes_one(self):
        records = [evaluate_row(entry, self.index) for entry in full_rows()]
        self.assertAlmostEqual(compliance_index(records, self.index), 1.0, places=9)

    def test_partial_row_costs_half_its_weight(self):
        rows = full_rows()
        rows[2] = row("5.1.3", status="partially-compliant")
        records = [evaluate_row(entry, self.index) for entry in rows]
        self.assertAlmostEqual(
            compliance_index(records, self.index), (3 + 4 + 1 + 1) / 10, places=9
        )

    def test_tailored_clause_leaves_both_sides_of_the_index(self):
        rows = full_rows()
        rows[3] = row("5.1.4", status="not-applicable")
        records = [evaluate_row(entry, self.index) for entry in rows]
        self.assertAlmostEqual(compliance_index(records, self.index), 1.0, places=9)

    def test_unanswered_clause_scores_zero_without_leaving_the_denominator(self):
        records = [evaluate_row(entry, self.index) for entry in full_rows()[:3]]
        self.assertAlmostEqual(compliance_index(records, self.index), 9 / 10, places=9)

    def test_tailoring_everything_out_is_refused(self):
        rows = [row(entry["clause"], status="not-applicable") for entry in CLAUSES]
        records = [evaluate_row(entry, self.index) for entry in rows]
        with self.assertRaises(ValueError):
            compliance_index(records, self.index)

    def test_coverage_rejects_a_malformed_record(self):
        with self.assertRaises(ValueError):
            clause_row_coverage([{"no": "disposition"}], self.index)


class AssessmentTests(unittest.TestCase):
    def spec(self, **overrides):
        base = {
            "applicable_clauses": CLAUSES,
            "rows": full_rows(),
            "required_coverage": 1.0,
            "required_index": 1.0,
        }
        base.update(overrides)
        return base

    def test_complete_matrix_is_ready_for_issue(self):
        result = assess_compliance_matrix(self.spec())
        self.assertTrue(result["issuable"])
        self.assertEqual(result["verdict"], "matrix ready for issue")
        self.assertEqual(result["findings"], [])

    def test_missing_clause_row_is_reported_as_unanswered(self):
        result = assess_compliance_matrix(self.spec(rows=full_rows()[:2]))
        self.assertEqual(result["unanswered_clauses"], ("5.1.3", "5.1.4"))
        self.assertFalse(result["issuable"])

    def test_open_deviation_is_listed_by_clause(self):
        rows = full_rows()
        rows[0] = row("5.1.2.1", status="partially-compliant")
        result = assess_compliance_matrix(
            self.spec(rows=rows, required_index=0.5)
        )
        self.assertEqual(result["open_deviations"], ("5.1.2.1",))

    def test_tailored_clause_is_listed_apart_from_deviations(self):
        rows = full_rows()
        rows[3] = row("5.1.4", status="not-applicable")
        result = assess_compliance_matrix(self.spec(rows=rows))
        self.assertEqual(result["tailored_out_clauses"], ("5.1.4",))
        self.assertEqual(result["open_deviations"], ())

    def test_index_exactly_at_a_reduced_requirement_is_met(self):
        rows = full_rows()
        rows[2] = row("5.1.3", status="not-compliant")
        required = 8 / 10
        result = assess_compliance_matrix(
            self.spec(rows=rows, required_index=required)
        )
        self.assertAlmostEqual(
            result["compliance_index"], result["required_index"], places=9
        )

    def test_findings_are_ranked_most_severe_first(self):
        rows = full_rows()
        rows[1] = row("5.1.2.2", evidence_reference="")
        rows.append(row("9.9", row_id="R-STRAY"))
        result = assess_compliance_matrix(self.spec(rows=rows))
        severities = [entry["severity"] for entry in result["findings"]]
        self.assertEqual(severities, sorted(severities))

    def test_duplicate_row_identifier_rejected(self):
        rows = full_rows()
        rows.append(dict(rows[0]))
        with self.assertRaises(ValueError):
            assess_compliance_matrix(self.spec(rows=rows))

    def test_missing_key_rejected(self):
        spec = self.spec()
        del spec["rows"]
        with self.assertRaises(ValueError):
            assess_compliance_matrix(spec)

    def test_out_of_range_required_index_rejected(self):
        with self.assertRaises(ValueError):
            assess_compliance_matrix(self.spec(required_index=-0.2))

    def test_boolean_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_compliance_matrix(self.spec(required_coverage=True))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_compliance_matrix("a matrix")

    def test_tolerance_is_small_enough_to_be_representation_error(self):
        self.assertLess(INDEX_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=1)
