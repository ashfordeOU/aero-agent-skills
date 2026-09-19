#!/usr/bin/env python3
"""Contract tests for responsibility and authority, clause 5.3.3.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused
authority demand, a matrix never assigned, an item with nobody against
it, an item with two holders, a holder under the authority the item's
criticality demands, a delegation granting more than the delegator
holds, a delegation from somebody holding nothing, a reporting line that
stops short of the centre head, and a reporting loop.
"""

import unittest

from q2007_responsibility_logic import (
    AUTHORITY_CENTRE_HEAD,
    AUTHORITY_INSUFFICIENT,
    AUTHORITY_MANAGER,
    AUTHORITY_OPERATOR,
    AUTHORITY_SUPERVISOR,
    CRITICALITY_QUALITY_CRITICAL,
    CRITICALITY_ROUTINE,
    CRITICALITY_SAFETY_CRITICAL,
    DEFAULT_AUTHORITY_DEMAND,
    DELEGATION_INVALID,
    DUTY_AMBIGUOUS,
    ITEMS_UNASSIGNED,
    MATRIX_ABSENT,
    REPORTING_LINE_BROKEN,
    RESPONSIBILITIES_ASSIGNED,
    ambiguous_items,
    assess_responsibility,
    assignment_coverage,
    authority_held_by,
    authority_rank,
    authority_reaches,
    authority_shortfalls,
    delegation_defects,
    holders_of,
    reporting_defects,
    reporting_line,
    unassigned_items,
    validate_assignment,
    validate_authority_demand,
    validate_item,
    validate_matrix,
)

CENTRE_HEAD = "centre-head-person"


def _item(item_id="QS-CALIBRATION-CONTROL", criticality=CRITICALITY_QUALITY_CRITICAL):
    return {"item_id": item_id, "criticality": criticality}


def _assignment(item_id="QS-CALIBRATION-CONTROL", holder="metrology-lead", **overrides):
    row = {
        "item_id": item_id,
        "holder": holder,
        "authority": AUTHORITY_SUPERVISOR,
        "delegated_from": None,
        "reports_to": CENTRE_HEAD,
    }
    row.update(overrides)
    return row


def _matrix(**overrides):
    record = {
        "assigned": True,
        "items": [
            _item("QS-CALIBRATION-CONTROL", CRITICALITY_QUALITY_CRITICAL),
            _item("QS-PRESSURE-SAFETY", CRITICALITY_SAFETY_CRITICAL),
            _item("QS-HOUSEKEEPING", CRITICALITY_ROUTINE),
        ],
        "assignments": [
            _assignment("QS-CALIBRATION-CONTROL", "metrology-lead"),
            _assignment("QS-PRESSURE-SAFETY", "safety-manager", authority=AUTHORITY_MANAGER),
            _assignment("QS-HOUSEKEEPING", "facility-operator", authority=AUTHORITY_OPERATOR),
        ],
        "centre_head": CENTRE_HEAD,
    }
    record.update(overrides)
    return record


def _case(**overrides):
    case = {"matrix": _matrix()}
    case.update(overrides)
    return case


class AuthorityOrder(unittest.TestCase):
    def test_the_order_runs_from_operator_to_centre_head(self):
        self.assertLess(authority_rank(AUTHORITY_OPERATOR), authority_rank(AUTHORITY_MANAGER))
        self.assertLess(authority_rank(AUTHORITY_MANAGER), authority_rank(AUTHORITY_CENTRE_HEAD))

    def test_an_equal_level_reaches_the_demand(self):
        self.assertTrue(authority_reaches(AUTHORITY_MANAGER, AUTHORITY_MANAGER))

    def test_a_lower_level_does_not_reach_the_demand(self):
        self.assertFalse(authority_reaches(AUTHORITY_SUPERVISOR, AUTHORITY_MANAGER))

    def test_an_unrecognised_level_is_refused(self):
        with self.assertRaises(ValueError):
            authority_rank("chief-of-everything")

    def test_the_default_demand_round_trips(self):
        demand = validate_authority_demand(None)
        self.assertEqual(demand[CRITICALITY_SAFETY_CRITICAL], AUTHORITY_MANAGER)
        self.assertEqual(demand, DEFAULT_AUTHORITY_DEMAND)

    def test_a_demand_missing_a_criticality_is_refused(self):
        with self.assertRaises(ValueError):
            validate_authority_demand({CRITICALITY_ROUTINE: AUTHORITY_OPERATOR})

    def test_a_demand_naming_an_unknown_criticality_is_refused(self):
        with self.assertRaises(ValueError):
            validate_authority_demand(
                {
                    CRITICALITY_ROUTINE: AUTHORITY_OPERATOR,
                    CRITICALITY_QUALITY_CRITICAL: AUTHORITY_SUPERVISOR,
                    CRITICALITY_SAFETY_CRITICAL: AUTHORITY_MANAGER,
                    "cosmetic-item": AUTHORITY_OPERATOR,
                }
            )

    def test_a_demand_placing_safety_under_routine_is_refused(self):
        with self.assertRaises(ValueError):
            validate_authority_demand(
                {
                    CRITICALITY_ROUTINE: AUTHORITY_MANAGER,
                    CRITICALITY_QUALITY_CRITICAL: AUTHORITY_SUPERVISOR,
                    CRITICALITY_SAFETY_CRITICAL: AUTHORITY_OPERATOR,
                }
            )


class MatrixValidation(unittest.TestCase):
    def test_item_missing_field_refused(self):
        with self.assertRaises(ValueError):
            validate_item({"item_id": "QS-HOUSEKEEPING"})

    def test_unrecognised_criticality_refused(self):
        with self.assertRaises(ValueError):
            validate_item(_item(criticality="nice-to-have-item"))

    def test_assignment_missing_field_refused(self):
        bad = _assignment()
        del bad["reports_to"]
        with self.assertRaises(ValueError):
            validate_assignment(bad)

    def test_self_delegation_refused(self):
        with self.assertRaises(ValueError):
            validate_assignment(_assignment(delegated_from="metrology-lead"))

    def test_self_reporting_refused(self):
        with self.assertRaises(ValueError):
            validate_assignment(_assignment(reports_to="metrology-lead"))

    def test_duplicate_item_id_refused(self):
        items = _matrix()["items"] + [_item("QS-HOUSEKEEPING", CRITICALITY_ROUTINE)]
        with self.assertRaises(ValueError):
            validate_matrix(_matrix(items=items))

    def test_the_same_person_assigned_twice_to_one_item_refused(self):
        assignments = _matrix()["assignments"] + [
            _assignment("QS-CALIBRATION-CONTROL", "metrology-lead")
        ]
        with self.assertRaises(ValueError):
            validate_matrix(_matrix(assignments=assignments))

    def test_an_assignment_against_an_unheld_item_refused(self):
        assignments = _matrix()["assignments"] + [_assignment("QS-GHOST", "somebody")]
        with self.assertRaises(ValueError):
            validate_matrix(_matrix(assignments=assignments))

    def test_non_mapping_matrix_refused(self):
        with self.assertRaises(ValueError):
            validate_matrix(["assigned"])

    def test_holders_of_an_unheld_item_refused(self):
        with self.assertRaises(ValueError):
            holders_of(_matrix(), "QS-GHOST")


class AssignmentCompleteness(unittest.TestCase):
    def test_a_complete_matrix_leaves_nothing_unassigned(self):
        self.assertEqual(unassigned_items(_matrix()), [])
        self.assertEqual(ambiguous_items(_matrix()), [])

    def test_an_item_with_nobody_against_it_is_named(self):
        matrix = _matrix(assignments=[_assignment("QS-CALIBRATION-CONTROL", "metrology-lead")])
        self.assertEqual(
            unassigned_items(matrix), ["QS-PRESSURE-SAFETY", "QS-HOUSEKEEPING"]
        )

    def test_an_item_with_two_holders_is_ambiguous(self):
        assignments = _matrix()["assignments"] + [
            _assignment("QS-PRESSURE-SAFETY", "deputy-safety-manager", authority=AUTHORITY_MANAGER)
        ]
        ambiguous = ambiguous_items(_matrix(assignments=assignments))
        self.assertEqual(ambiguous[0][0], "QS-PRESSURE-SAFETY")
        self.assertEqual(len(ambiguous[0][1]), 2)

    def test_coverage_is_one_when_every_item_has_exactly_one_holder(self):
        self.assertAlmostEqual(assignment_coverage(_matrix()), 1.0, places=9)

    def test_coverage_drops_with_an_unassigned_item(self):
        matrix = _matrix(assignments=[_assignment("QS-CALIBRATION-CONTROL", "metrology-lead")])
        self.assertAlmostEqual(assignment_coverage(matrix), 1.0 / 3.0, places=9)

    def test_coverage_of_a_matrix_with_no_items_is_zero(self):
        self.assertAlmostEqual(
            assignment_coverage(_matrix(items=[], assignments=[])), 0.0, places=9
        )

    def test_holders_of_returns_the_assignment_rows(self):
        rows = holders_of(_matrix(), "QS-PRESSURE-SAFETY")
        self.assertEqual(rows[0]["holder"], "safety-manager")


class AuthorityAndDelegation(unittest.TestCase):
    def test_a_matched_matrix_has_no_authority_shortfall(self):
        self.assertEqual(authority_shortfalls(_matrix()), [])

    def test_a_supervisor_on_a_safety_critical_item_is_a_shortfall(self):
        assignments = [
            _assignment("QS-CALIBRATION-CONTROL", "metrology-lead"),
            _assignment("QS-PRESSURE-SAFETY", "shift-supervisor", authority=AUTHORITY_SUPERVISOR),
            _assignment("QS-HOUSEKEEPING", "facility-operator", authority=AUTHORITY_OPERATOR),
        ]
        shortfalls = authority_shortfalls(_matrix(assignments=assignments))
        self.assertEqual(shortfalls[0][0], "QS-PRESSURE-SAFETY")
        self.assertEqual(shortfalls[0][3], AUTHORITY_MANAGER)

    def test_a_raised_demand_creates_a_shortfall_that_the_default_allows(self):
        demand = {
            CRITICALITY_ROUTINE: AUTHORITY_SUPERVISOR,
            CRITICALITY_QUALITY_CRITICAL: AUTHORITY_SUPERVISOR,
            CRITICALITY_SAFETY_CRITICAL: AUTHORITY_MANAGER,
        }
        self.assertEqual(authority_shortfalls(_matrix()), [])
        self.assertEqual(len(authority_shortfalls(_matrix(), demand)), 1)

    def test_the_centre_head_holds_the_top_authority(self):
        self.assertEqual(authority_held_by(_matrix(), CENTRE_HEAD), AUTHORITY_CENTRE_HEAD)

    def test_a_person_with_no_assignment_holds_nothing(self):
        self.assertIsNone(authority_held_by(_matrix(), "visiting-auditor"))

    def test_a_valid_delegation_is_not_a_defect(self):
        assignments = _matrix()["assignments"]
        assignments[0] = _assignment(
            "QS-CALIBRATION-CONTROL", "metrology-lead", delegated_from=CENTRE_HEAD
        )
        self.assertEqual(delegation_defects(_matrix(assignments=assignments)), [])

    def test_a_delegation_above_the_delegator_is_a_defect(self):
        assignments = _matrix()["assignments"]
        assignments[1] = _assignment(
            "QS-PRESSURE-SAFETY",
            "safety-manager",
            authority=AUTHORITY_MANAGER,
            delegated_from="facility-operator",
        )
        defects = delegation_defects(_matrix(assignments=assignments))
        self.assertEqual(defects[0][1], "safety-manager")
        self.assertEqual(defects[0][3], AUTHORITY_OPERATOR)

    def test_a_delegation_from_somebody_holding_nothing_is_a_defect(self):
        assignments = _matrix()["assignments"]
        assignments[0] = _assignment(
            "QS-CALIBRATION-CONTROL", "metrology-lead", delegated_from="visiting-auditor"
        )
        defects = delegation_defects(_matrix(assignments=assignments))
        self.assertIsNone(defects[0][3])


class ReportingLines(unittest.TestCase):
    def test_a_direct_report_reaches_the_centre_head(self):
        self.assertEqual(
            reporting_line(_matrix(), "metrology-lead"), ["metrology-lead", CENTRE_HEAD]
        )

    def test_an_indirect_report_reaches_the_centre_head(self):
        assignments = _matrix()["assignments"]
        assignments[2] = _assignment(
            "QS-HOUSEKEEPING",
            "facility-operator",
            authority=AUTHORITY_OPERATOR,
            reports_to="safety-manager",
        )
        chain = reporting_line(_matrix(assignments=assignments), "facility-operator")
        self.assertEqual(chain, ["facility-operator", "safety-manager", CENTRE_HEAD])

    def test_a_line_stopping_short_of_the_centre_head_is_refused(self):
        assignments = _matrix()["assignments"]
        assignments[0] = _assignment(
            "QS-CALIBRATION-CONTROL", "metrology-lead", reports_to="nobody-listed"
        )
        with self.assertRaises(ValueError):
            reporting_line(_matrix(assignments=assignments), "metrology-lead")

    def test_a_holder_reporting_to_nobody_is_refused(self):
        assignments = [_assignment("QS-CALIBRATION-CONTROL", "metrology-lead", reports_to=None)]
        matrix = _matrix(items=[_item()], assignments=assignments)
        with self.assertRaises(ValueError):
            reporting_line(matrix, "metrology-lead")

    def test_a_reporting_loop_is_refused(self):
        assignments = [
            _assignment("QS-CALIBRATION-CONTROL", "alpha", reports_to="beta"),
            _assignment("QS-PRESSURE-SAFETY", "beta", authority=AUTHORITY_MANAGER,
                        reports_to="alpha"),
        ]
        matrix = _matrix(
            items=[
                _item("QS-CALIBRATION-CONTROL", CRITICALITY_QUALITY_CRITICAL),
                _item("QS-PRESSURE-SAFETY", CRITICALITY_SAFETY_CRITICAL),
            ],
            assignments=assignments,
        )
        with self.assertRaises(ValueError):
            reporting_line(matrix, "alpha")

    def test_reporting_defects_names_the_broken_holder(self):
        assignments = _matrix()["assignments"]
        assignments[0] = _assignment(
            "QS-CALIBRATION-CONTROL", "metrology-lead", reports_to="nobody-listed"
        )
        defects = reporting_defects(_matrix(assignments=assignments))
        self.assertEqual([name for name, _ in defects], ["metrology-lead"])

    def test_a_clean_matrix_has_no_reporting_defect(self):
        self.assertEqual(reporting_defects(_matrix()), [])


class Verdicts(unittest.TestCase):
    def test_a_complete_matrix_is_assigned(self):
        result = assess_responsibility(_case())
        self.assertEqual(result["verdict"], RESPONSIBILITIES_ASSIGNED)
        self.assertEqual(result["findings"], [])

    def test_a_matrix_never_assigned_short_circuits(self):
        result = assess_responsibility(_case(matrix=_matrix(assigned=False)))
        self.assertEqual(result["verdict"], MATRIX_ABSENT)

    def test_a_matrix_with_no_items_is_absent(self):
        result = assess_responsibility(_case(matrix=_matrix(items=[], assignments=[])))
        self.assertEqual(result["verdict"], MATRIX_ABSENT)

    def test_an_unassigned_item_outranks_an_ambiguous_one(self):
        assignments = [
            _assignment("QS-CALIBRATION-CONTROL", "metrology-lead"),
            _assignment("QS-CALIBRATION-CONTROL", "deputy-metrology-lead"),
        ]
        result = assess_responsibility(_case(matrix=_matrix(assignments=assignments)))
        self.assertEqual(result["verdict"], ITEMS_UNASSIGNED)

    def test_an_ambiguous_duty_outranks_an_authority_shortfall(self):
        assignments = _matrix()["assignments"] + [
            _assignment("QS-PRESSURE-SAFETY", "shift-supervisor", authority=AUTHORITY_SUPERVISOR)
        ]
        result = assess_responsibility(_case(matrix=_matrix(assignments=assignments)))
        self.assertEqual(result["verdict"], DUTY_AMBIGUOUS)

    def test_an_authority_shortfall_outranks_a_delegation_defect(self):
        assignments = [
            _assignment("QS-CALIBRATION-CONTROL", "metrology-lead"),
            _assignment(
                "QS-PRESSURE-SAFETY",
                "shift-supervisor",
                authority=AUTHORITY_SUPERVISOR,
                delegated_from="facility-operator",
            ),
            _assignment("QS-HOUSEKEEPING", "facility-operator", authority=AUTHORITY_OPERATOR),
        ]
        result = assess_responsibility(_case(matrix=_matrix(assignments=assignments)))
        self.assertEqual(result["verdict"], AUTHORITY_INSUFFICIENT)

    def test_a_delegation_defect_outranks_a_reporting_defect(self):
        assignments = _matrix()["assignments"]
        assignments[1] = _assignment(
            "QS-PRESSURE-SAFETY",
            "safety-manager",
            authority=AUTHORITY_MANAGER,
            delegated_from="facility-operator",
            reports_to="nobody-listed",
        )
        result = assess_responsibility(_case(matrix=_matrix(assignments=assignments)))
        self.assertEqual(result["verdict"], DELEGATION_INVALID)

    def test_a_reporting_defect_is_the_last_verdict_before_pass(self):
        assignments = _matrix()["assignments"]
        assignments[0] = _assignment(
            "QS-CALIBRATION-CONTROL", "metrology-lead", reports_to="nobody-listed"
        )
        result = assess_responsibility(_case(matrix=_matrix(assignments=assignments)))
        self.assertEqual(result["verdict"], REPORTING_LINE_BROKEN)

    def test_a_raised_demand_changes_the_verdict(self):
        demand = {
            CRITICALITY_ROUTINE: AUTHORITY_SUPERVISOR,
            CRITICALITY_QUALITY_CRITICAL: AUTHORITY_SUPERVISOR,
            CRITICALITY_SAFETY_CRITICAL: AUTHORITY_MANAGER,
        }
        result = assess_responsibility(_case(authority_demand=demand))
        self.assertEqual(result["verdict"], AUTHORITY_INSUFFICIENT)

    def test_a_case_without_a_matrix_is_refused(self):
        with self.assertRaises(ValueError):
            assess_responsibility({"authority_demand": None})

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_responsibility(("matrix",))


if __name__ == "__main__":
    unittest.main()
