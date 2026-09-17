"""Contract tests for the clause 6.1.2.2 class 3 compliance matrix logic."""

import unittest

from q60_class_3_component_control_plan_logic import (
    BOUND_TOLERANCE,
    COMPLIANCE_STATES,
    DEPARTURE_SHARE_CEILING,
    DEPARTURE_STATES,
    MATRIX_COMPLETENESS_FLOOR,
    answered_clauses,
    compile_class_3_compliance_matrix,
    completeness_meets_floor,
    conflicting_clauses,
    departure_share,
    matrix_completeness,
    matrix_disposition,
    matrix_findings,
    normalise_clause,
    ordered_clauses,
    parse_clause,
    row_clause,
    row_defects,
    row_state,
    rows_by_clause,
    unaddressed_clauses,
    unagreed_non_compliances,
)

APPLICABLE = ["6.1.2.2", "6.1.3", "6.2.1", "6.3"]


def _row(**over):
    base = {
        "clause": "6.1.2.2",
        "state": "compliant",
        "implementing_reference": "CCP-6063 section 4",
    }
    base.update(over)
    return base


def _plan(**over):
    base = {
        "plan_id": "CCP-6063",
        "applicable_clauses": list(APPLICABLE),
        "rows": [
            _row(),
            _row(clause="6.1.3", implementing_reference="CCP-6063 section 5"),
            _row(clause="6.2.1", implementing_reference="CCP-6063 section 6"),
            _row(clause="6.3", implementing_reference="CCP-6063 section 7"),
        ],
    }
    base.update(over)
    return base


class ClauseIdentifierTests(unittest.TestCase):
    def test_a_clause_parses_into_level_numbers(self):
        self.assertEqual(parse_clause("6.1.2.2"), (6, 1, 2, 2))

    def test_a_single_level_clause_parses(self):
        self.assertEqual(parse_clause("6"), (6,))

    def test_surrounding_space_is_ignored(self):
        self.assertEqual(parse_clause("  6.1.3 "), (6, 1, 3))

    def test_a_malformed_clause_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_clause("6.1.a")

    def test_a_trailing_separator_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_clause("6.1.")

    def test_an_empty_clause_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_clause("   ")

    def test_a_number_is_not_a_clause_identifier(self):
        with self.assertRaises(ValueError):
            parse_clause(6.1)

    def test_a_clause_normalises_to_its_canonical_spelling(self):
        self.assertEqual(normalise_clause(" 6.01.3 "), "6.1.3")

    def test_the_tenth_subclause_sorts_after_the_ninth(self):
        ordered = ordered_clauses(["6.1.10", "6.1.9", "6.1.2"])
        self.assertEqual(ordered, ["6.1.2", "6.1.9", "6.1.10"])

    def test_clauses_come_back_in_numeric_order(self):
        self.assertEqual(ordered_clauses(["6.3", "6.1.2.2"]),
                         ["6.1.2.2", "6.3"])

    def test_a_repeated_clause_is_rejected(self):
        with self.assertRaises(ValueError):
            ordered_clauses(["6.1.3", "6.01.3"])

    def test_a_bare_string_is_not_a_sequence_of_clauses(self):
        with self.assertRaises(ValueError):
            ordered_clauses("6.1.3")


class RowReadingTests(unittest.TestCase):
    def test_a_row_names_its_clause(self):
        self.assertEqual(row_clause(_row()), "6.1.2.2")

    def test_a_row_with_a_malformed_clause_names_none(self):
        self.assertIsNone(row_clause(_row(clause="clause six")))

    def test_a_row_with_no_clause_names_none(self):
        self.assertIsNone(row_clause(_row(clause=None)))

    def test_a_row_states_its_compliance_state(self):
        self.assertEqual(row_state(_row()), "compliant")

    def test_a_state_reads_case_insensitively(self):
        self.assertEqual(row_state(_row(state="NOT-APPLICABLE")),
                         "not-applicable")

    def test_a_state_outside_the_vocabulary_reads_as_none(self):
        self.assertIsNone(row_state(_row(state="mostly fine")))

    def test_a_row_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            row_state("6.1.2.2")

    def test_every_published_state_is_readable(self):
        for state in COMPLIANCE_STATES:
            self.assertEqual(row_state(_row(state=state)), state)


class RowDefectTests(unittest.TestCase):
    def test_a_sound_row_carries_no_defects(self):
        self.assertEqual(row_defects(_row(), APPLICABLE), [])

    def test_a_row_naming_no_clause_is_a_defect(self):
        self.assertIn("clause-not-stated",
                      row_defects(_row(clause="clause six"), APPLICABLE))

    def test_a_clause_outside_the_declared_scope_is_a_defect(self):
        self.assertIn("clause-outside-declared-scope",
                      row_defects(_row(clause="9.9"), APPLICABLE))

    def test_an_unstated_state_short_circuits_the_state_tests(self):
        defects = row_defects(_row(state=None), APPLICABLE)
        self.assertEqual(defects, ["compliance-state-not-stated"])

    def test_a_stated_compliance_needs_an_implementing_reference(self):
        self.assertIn("implementing-reference-missing",
                      row_defects(_row(implementing_reference=""), APPLICABLE))

    def test_a_deviation_needs_a_justification(self):
        row = _row(state="compliant-with-deviation")
        self.assertIn("departure-without-justification",
                      row_defects(row, APPLICABLE))

    def test_a_justified_deviation_is_sound(self):
        row = _row(state="compliant-with-deviation",
                   justification="single-source part, derating held")
        self.assertEqual(row_defects(row, APPLICABLE), [])

    def test_a_non_applicable_clause_needs_a_justification(self):
        row = _row(state="not-applicable", implementing_reference=None)
        self.assertIn("departure-without-justification",
                      row_defects(row, APPLICABLE))

    def test_a_justified_non_applicable_clause_needs_no_reference(self):
        row = _row(state="not-applicable", implementing_reference=None,
                   justification="no hybrid parts in the equipment")
        self.assertEqual(row_defects(row, APPLICABLE), [])

    def test_a_non_compliance_needs_a_customer_agreement(self):
        row = _row(state="not-compliant", implementing_reference=None,
                   justification="no source can meet the lot date")
        self.assertIn("non-compliance-without-customer-agreement",
                      row_defects(row, APPLICABLE))

    def test_an_agreed_non_compliance_is_sound(self):
        row = _row(state="not-compliant", implementing_reference=None,
                   justification="no source can meet the lot date",
                   customer_agreement_reference="RFD-6063-02")
        self.assertEqual(row_defects(row, APPLICABLE), [])

    def test_defects_accumulate(self):
        row = _row(clause="9.9", state="not-compliant",
                   implementing_reference=None)
        defects = row_defects(row, APPLICABLE)
        self.assertEqual(len(defects), 3)

    def test_an_empty_applicable_list_is_rejected(self):
        with self.assertRaises(ValueError):
            row_defects(_row(), [])


class GroupingTests(unittest.TestCase):
    def test_rows_group_under_the_clause_they_answer(self):
        grouped = rows_by_clause(_plan()["rows"])
        self.assertEqual(len(grouped["6.1.2.2"]), 1)

    def test_an_unreadable_row_is_grouped_rather_than_dropped(self):
        grouped = rows_by_clause([_row(clause="clause six")])
        self.assertIn(None, grouped)

    def test_two_rows_for_one_clause_group_together(self):
        grouped = rows_by_clause([_row(), _row(state="not-applicable")])
        self.assertEqual(len(grouped["6.1.2.2"]), 2)

    def test_rows_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            rows_by_clause(_row())

    def test_a_row_inside_the_sequence_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            rows_by_clause([_row(), "6.1.3"])


class CoverageTests(unittest.TestCase):
    def test_a_complete_matrix_leaves_no_clause_unaddressed(self):
        self.assertEqual(unaddressed_clauses(APPLICABLE, _plan()["rows"]), [])

    def test_an_unanswered_clause_is_named(self):
        rows = _plan()["rows"][:3]
        self.assertEqual(unaddressed_clauses(APPLICABLE, rows), ["6.3"])

    def test_unaddressed_clauses_come_back_in_clause_order(self):
        missing = unaddressed_clauses(APPLICABLE, [])
        self.assertEqual(missing, ordered_clauses(APPLICABLE))

    def test_one_state_stated_twice_is_not_a_conflict(self):
        rows = [_row(), _row()]
        self.assertEqual(conflicting_clauses(rows), [])

    def test_two_different_states_on_one_clause_conflict(self):
        rows = [_row(), _row(state="not-applicable",
                             justification="no such parts")]
        self.assertEqual(conflicting_clauses(rows), ["6.1.2.2"])

    def test_a_conflicted_clause_is_not_answered(self):
        rows = [_row(), _row(state="not-applicable",
                             justification="no such parts")]
        self.assertEqual(answered_clauses(["6.1.2.2"], rows), [])

    def test_a_defective_row_does_not_answer_its_clause(self):
        rows = [_row(implementing_reference=None)]
        self.assertEqual(answered_clauses(["6.1.2.2"], rows), [])

    def test_one_sound_row_among_defective_ones_answers_the_clause(self):
        rows = [_row(implementing_reference=None), _row()]
        self.assertEqual(answered_clauses(["6.1.2.2"], rows), ["6.1.2.2"])

    def test_a_defective_row_is_listed_with_its_defects(self):
        findings = matrix_findings([_row(implementing_reference=None)],
                                   APPLICABLE)
        self.assertEqual(findings[0]["row"], "6.1.2.2")
        self.assertIn("implementing-reference-missing", findings[0]["defects"])

    def test_an_unreadable_row_falls_back_to_its_position(self):
        findings = matrix_findings([_row(clause="clause six")], APPLICABLE)
        self.assertEqual(findings[0]["row"], "row-0")

    def test_a_clean_matrix_reports_no_findings(self):
        self.assertEqual(matrix_findings(_plan()["rows"], APPLICABLE), [])


class CompletenessTests(unittest.TestCase):
    def test_a_full_matrix_reads_one(self):
        self.assertAlmostEqual(
            matrix_completeness(APPLICABLE, _plan()["rows"]), 1.0, places=9)

    def test_an_empty_matrix_reads_zero(self):
        self.assertAlmostEqual(matrix_completeness(APPLICABLE, []), 0.0,
                               places=9)

    def test_three_of_four_clauses_read_three_quarters(self):
        rows = _plan()["rows"][:3]
        self.assertAlmostEqual(matrix_completeness(APPLICABLE, rows), 0.75,
                               places=9)

    def test_an_empty_applicable_list_is_rejected(self):
        with self.assertRaises(ValueError):
            matrix_completeness([], [])

    def test_a_full_matrix_meets_the_floor(self):
        self.assertTrue(completeness_meets_floor(1.0))

    def test_completeness_exactly_on_the_floor_meets_it(self):
        self.assertTrue(completeness_meets_floor(MATRIX_COMPLETENESS_FLOOR))

    def test_nineteen_of_twenty_meets_the_floor(self):
        self.assertTrue(completeness_meets_floor(19.0 / 20.0))

    def test_three_quarters_does_not_meet_the_floor(self):
        self.assertFalse(completeness_meets_floor(0.75))

    def test_a_completeness_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            completeness_meets_floor(1.2)

    def test_the_floor_is_the_documented_size(self):
        self.assertAlmostEqual(MATRIX_COMPLETENESS_FLOOR, 0.95, places=9)

    def test_the_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)


class DepartureTests(unittest.TestCase):
    def test_a_fully_compliant_matrix_departs_nowhere(self):
        self.assertAlmostEqual(departure_share(_plan()["rows"]), 0.0, places=9)

    def test_one_departure_in_four_reads_a_quarter(self):
        rows = list(_plan()["rows"])
        rows[0] = _row(state="compliant-with-deviation",
                       justification="single-source part")
        self.assertAlmostEqual(departure_share(rows), 0.25, places=9)

    def test_a_stateless_row_is_not_counted(self):
        rows = [_row(), _row(clause="6.1.3", state=None)]
        self.assertAlmostEqual(departure_share(rows), 0.0, places=9)

    def test_a_matrix_stating_nothing_has_no_share(self):
        with self.assertRaises(ValueError):
            departure_share([_row(state=None)])

    def test_every_departure_state_counts_as_a_departure(self):
        rows = [_row(state=state, justification="stated",
                     customer_agreement_reference="RFD-6063-02")
                for state in DEPARTURE_STATES]
        self.assertAlmostEqual(departure_share(rows), 1.0, places=9)

    def test_the_ceiling_is_the_documented_size(self):
        self.assertAlmostEqual(DEPARTURE_SHARE_CEILING, 0.2, places=9)


class AgreementTests(unittest.TestCase):
    def test_an_agreed_matrix_has_no_unagreed_non_compliance(self):
        self.assertEqual(unagreed_non_compliances(_plan()["rows"]), [])

    def test_an_unagreed_non_compliance_is_named(self):
        rows = [_row(state="not-compliant", justification="no source")]
        self.assertEqual(unagreed_non_compliances(rows), ["6.1.2.2"])

    def test_an_agreed_non_compliance_is_not_named(self):
        rows = [_row(state="not-compliant", justification="no source",
                     customer_agreement_reference="RFD-6063-02")]
        self.assertEqual(unagreed_non_compliances(rows), [])

    def test_unagreed_clauses_come_back_in_clause_order(self):
        rows = [_row(clause="6.3", state="not-compliant", justification="x"),
                _row(clause="6.1.3", state="not-compliant", justification="x")]
        self.assertEqual(unagreed_non_compliances(rows), ["6.1.3", "6.3"])


class DispositionTests(unittest.TestCase):
    def test_a_clean_matrix_reads_as_ready(self):
        self.assertEqual(matrix_disposition([], [], [], 1.0), "matrix-ready")

    def test_an_unaddressed_clause_reads_as_incomplete(self):
        self.assertEqual(matrix_disposition(["6.3"], [], [], 1.0),
                         "matrix-incomplete")

    def test_a_conflict_reads_as_incomplete(self):
        self.assertEqual(matrix_disposition([], ["6.1.3"], [], 1.0),
                         "matrix-incomplete")

    def test_a_completeness_shortfall_reads_as_incomplete(self):
        self.assertEqual(matrix_disposition([], [], [], 0.75),
                         "matrix-incomplete")

    def test_an_unagreed_non_compliance_reads_as_not_agreeable(self):
        self.assertEqual(matrix_disposition([], [], ["6.3"], 1.0),
                         "matrix-not-agreeable")

    def test_an_unagreed_non_compliance_outranks_an_unaddressed_clause(self):
        self.assertEqual(matrix_disposition(["6.2.1"], [], ["6.3"], 0.5),
                         "matrix-not-agreeable")

    def test_the_unaddressed_list_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            matrix_disposition("6.3", [], [], 1.0)


class CompilationTests(unittest.TestCase):
    def test_a_sound_matrix_is_ready(self):
        result = compile_class_3_compliance_matrix(_plan())
        self.assertTrue(result["matrix_ready"])
        self.assertEqual(result["disposition"], "matrix-ready")

    def test_the_applicable_clauses_come_back_in_clause_order(self):
        result = compile_class_3_compliance_matrix(_plan())
        self.assertEqual(result["applicable_clauses"],
                         ordered_clauses(APPLICABLE))

    def test_an_unanswered_clause_is_named_and_blocks_the_matrix(self):
        plan = _plan()
        plan["rows"] = plan["rows"][:3]
        result = compile_class_3_compliance_matrix(plan)
        self.assertEqual(result["unaddressed_clauses"], ["6.3"])
        self.assertFalse(result["matrix_ready"])

    def test_a_defective_row_is_reported_with_its_defects(self):
        plan = _plan()
        plan["rows"][0] = _row(implementing_reference=None)
        result = compile_class_3_compliance_matrix(plan)
        self.assertIn("implementing-reference-missing",
                      result["matrix_findings"][0]["defects"])

    def test_an_unagreed_non_compliance_makes_the_matrix_not_agreeable(self):
        plan = _plan()
        plan["rows"][1] = _row(clause="6.1.3", state="not-compliant",
                               implementing_reference=None,
                               justification="no source can meet the lot date")
        result = compile_class_3_compliance_matrix(plan)
        self.assertEqual(result["disposition"], "matrix-not-agreeable")
        self.assertEqual(result["unagreed_non_compliances"], ["6.1.3"])

    def test_a_heavy_departure_share_raises_an_advisory(self):
        plan = _plan()
        for index in range(3):
            clause = APPLICABLE[index]
            plan["rows"][index] = _row(clause=clause,
                                       state="compliant-with-deviation",
                                       justification="tailored for this class")
        result = compile_class_3_compliance_matrix(plan)
        self.assertIn("departure-share-above-ceiling", result["advisories"])
        self.assertEqual(result["matrix_findings"], [])

    def test_a_light_departure_share_raises_no_advisory(self):
        result = compile_class_3_compliance_matrix(_plan())
        self.assertEqual(result["advisories"], [])

    def test_the_departure_share_is_reported(self):
        result = compile_class_3_compliance_matrix(_plan())
        self.assertAlmostEqual(result["departure_share"], 0.0, places=9)

    def test_completeness_is_reported(self):
        plan = _plan()
        plan["rows"] = plan["rows"][:3]
        result = compile_class_3_compliance_matrix(plan)
        self.assertAlmostEqual(result["matrix_completeness"], 0.75, places=9)

    def test_a_conflicted_clause_is_reported(self):
        plan = _plan()
        plan["rows"].append(_row(state="not-applicable",
                                 justification="no such parts"))
        result = compile_class_3_compliance_matrix(plan)
        self.assertEqual(result["conflicting_clauses"], ["6.1.2.2"])

    def test_a_plan_with_no_applicable_clause_is_rejected(self):
        with self.assertRaises(ValueError):
            compile_class_3_compliance_matrix(_plan(applicable_clauses=[]))

    def test_the_plan_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            compile_class_3_compliance_matrix([_plan()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
