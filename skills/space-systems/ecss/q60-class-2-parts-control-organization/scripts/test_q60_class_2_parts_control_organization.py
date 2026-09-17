"""Contract tests for the clause 5.1.2.1 accountable parts control unit logic.

Each test class follows one step of the SKILL.md workflow: the input
validation, the per-record disposition, the coverage gate and the closing
verdict. Offline, stdlib unittest; run it as the review checklist before
the leaf is issued.
"""

import unittest

from q60_class_2_parts_control_organization_logic import (
    APPOINTMENT_FORMS,
    CONTROL_ACTIVITIES,
    COVERAGE_TOLERANCE,
    MANDATORY_ASSIGNMENT_ATTRIBUTES,
    NON_DELEGABLE_ACTIVITIES,
    REPORTING_LINES,
    activity_coverage,
    activity_ownership,
    appointment_is_recorded,
    assess_parts_control_organization,
    assignment_completeness,
    evaluate_assignment,
    holder_load,
    independence_state,
    validate_activity,
    validate_unit,
    validate_unit_id,
)

UNIT = "PA-PARTS-OFFICE"


def unit(**overrides):
    """Return one properly appointed, independent unit."""
    base = {
        "unit_id": UNIT,
        "appointment_form": "contract-annex",
        "reporting_line": "product-assurance",
        "escalation_route_declared": False,
    }
    base.update(overrides)
    return base


def assignment(activity, **overrides):
    """Return one acceptable assignment of the given activity."""
    base = {
        "assignment_id": "A-" + activity,
        "activity": activity,
        "unit_id": UNIT,
        "holder": "parts-engineer-1",
        "delegated": False,
        "holder_qualified": True,
    }
    base.update(overrides)
    return base


def index(*units):
    return {u["unit_id"]: u for u in (validate_unit(entry) for entry in units)}


def full_assignments(**per_activity):
    """Return one assignment per mandated activity, spread over four holders."""
    out = []
    for position, name in enumerate(sorted(CONTROL_ACTIVITIES)):
        out.append(
            assignment(name, holder="parts-engineer-%d" % (position % 4 + 1))
        )
    for name, overrides in per_activity.items():
        canonical = name.replace("_", "-")
        for entry in out:
            if entry["activity"] == canonical:
                entry.update(overrides)
    return out


class ValidateUnitIdTests(unittest.TestCase):
    def test_strips_surrounding_space(self):
        self.assertEqual(validate_unit_id("  PA-PARTS-OFFICE "), UNIT)

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit_id("   ")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_unit_id(7)


class ValidateActivityTests(unittest.TestCase):
    def test_canonicalizes_case(self):
        self.assertEqual(
            validate_activity("PART-SELECTION-APPROVAL"), "part-selection-approval"
        )

    def test_unknown_activity_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity("tea-rota-management")

    def test_every_mandated_activity_carries_a_positive_weight(self):
        for name, weight in CONTROL_ACTIVITIES.items():
            self.assertEqual(validate_activity(name), name)
            self.assertGreater(weight, 0)

    def test_non_delegable_set_sits_inside_the_mandated_set(self):
        for name in NON_DELEGABLE_ACTIVITIES:
            self.assertIn(name, CONTROL_ACTIVITIES)


class AppointmentTests(unittest.TestCase):
    def test_contract_annex_stands(self):
        self.assertTrue(appointment_is_recorded("contract-annex"))

    def test_verbal_appointment_does_not_stand(self):
        self.assertFalse(appointment_is_recorded("verbal"))

    def test_meeting_minute_does_not_stand(self):
        self.assertFalse(appointment_is_recorded("meeting-minute"))

    def test_lookup_is_case_insensitive(self):
        self.assertTrue(appointment_is_recorded("Quality-Manual"))

    def test_unknown_form_rejected(self):
        with self.assertRaises(ValueError):
            appointment_is_recorded("whatever-the-line-manager-said")

    def test_every_known_form_answers_a_boolean(self):
        for form in APPOINTMENT_FORMS:
            self.assertIsInstance(appointment_is_recorded(form), bool)


class IndependenceTests(unittest.TestCase):
    def test_product_assurance_line_is_independent(self):
        self.assertEqual(
            independence_state("product-assurance", False), "independent"
        )

    def test_design_authority_line_without_route_is_flagged(self):
        self.assertEqual(
            independence_state("design-authority", False),
            "embedded-without-escalation",
        )

    def test_design_authority_line_with_route_is_tolerated(self):
        self.assertEqual(
            independence_state("design-authority", True), "embedded-with-escalation"
        )

    def test_unknown_line_rejected(self):
        with self.assertRaises(ValueError):
            independence_state("the-founders-office", False)

    def test_non_boolean_route_rejected(self):
        with self.assertRaises(ValueError):
            independence_state("design-authority", "yes")

    def test_every_known_line_answers_a_known_state(self):
        for line in REPORTING_LINES:
            self.assertIn(
                independence_state(line, False),
                {"independent", "embedded-without-escalation"},
            )


class CompletenessTests(unittest.TestCase):
    def test_complete_assignment_scores_one(self):
        missing, fraction = assignment_completeness(
            assignment("part-selection-approval")
        )
        self.assertEqual(missing, ())
        self.assertAlmostEqual(fraction, 1.0, places=9)

    def test_blank_holder_counts_as_missing(self):
        missing, fraction = assignment_completeness(
            assignment("part-selection-approval", holder="  ")
        )
        self.assertIn("holder", missing)
        self.assertAlmostEqual(
            fraction,
            (len(MANDATORY_ASSIGNMENT_ATTRIBUTES) - 1)
            / len(MANDATORY_ASSIGNMENT_ATTRIBUTES),
            places=9,
        )

    def test_absent_key_counts_as_missing(self):
        record = assignment("part-selection-approval")
        del record["unit_id"]
        missing, _ = assignment_completeness(record)
        self.assertIn("unit_id", missing)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            assignment_completeness(["not", "a", "mapping"])


class EvaluateAssignmentTests(unittest.TestCase):
    def setUp(self):
        self.index = index(unit())

    def test_good_assignment_is_accepted(self):
        record = evaluate_assignment(
            assignment("part-selection-approval"), self.index
        )
        self.assertEqual(record["disposition"], "accepted")
        self.assertTrue(record["accepted"])

    def test_incomplete_assignment_stops_before_any_other_test(self):
        record = evaluate_assignment(
            assignment("part-selection-approval", holder=None), self.index
        )
        self.assertEqual(record["disposition"], "record-incomplete")

    def test_unknown_unit_is_named(self):
        record = evaluate_assignment(
            assignment("part-selection-approval", unit_id="GHOST-OFFICE"), self.index
        )
        self.assertEqual(record["disposition"], "unknown-unit")

    def test_unknown_activity_is_named(self):
        stray = dict(assignment("part-selection-approval"), activity="tea-rota")
        record = evaluate_assignment(stray, self.index)
        self.assertEqual(record["disposition"], "unknown-activity")

    def test_unappointed_unit_owns_nothing(self):
        unappointed = index(unit(appointment_form="verbal"))
        record = evaluate_assignment(
            assignment("part-selection-approval"), unappointed
        )
        self.assertEqual(record["disposition"], "unit-not-appointed")

    def test_delegating_a_non_delegable_duty_is_refused(self):
        record = evaluate_assignment(
            assignment("part-selection-approval", delegated=True), self.index
        )
        self.assertEqual(record["disposition"], "non-delegable-activity-delegated")

    def test_delegating_a_supporting_duty_is_allowed(self):
        record = evaluate_assignment(
            assignment("obsolescence-and-supply-monitoring", delegated=True),
            self.index,
        )
        self.assertEqual(record["disposition"], "accepted")

    def test_unqualified_holder_is_refused(self):
        record = evaluate_assignment(
            assignment("incoming-inspection-release", holder_qualified=False),
            self.index,
        )
        self.assertEqual(record["disposition"], "holder-not-qualified")

    def test_empty_unit_index_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_assignment(assignment("part-selection-approval"), {})


class OwnershipAndCoverageTests(unittest.TestCase):
    def setUp(self):
        self.index = index(unit(), unit(unit_id="SUPPLIER-QA"))

    def test_ownership_lists_only_accepted_records(self):
        records = [
            evaluate_assignment(assignment("part-selection-approval"), self.index),
            evaluate_assignment(
                assignment("alert-and-advisory-handling", holder_qualified=False),
                self.index,
            ),
        ]
        owners = activity_ownership(records)
        self.assertEqual(owners, {"part-selection-approval": (UNIT,)})

    def test_two_units_on_one_activity_is_contested(self):
        records = [
            evaluate_assignment(assignment("declared-components-list-issue"), self.index),
            evaluate_assignment(
                assignment(
                    "declared-components-list-issue",
                    assignment_id="A-DCL-2",
                    unit_id="SUPPLIER-QA",
                ),
                self.index,
            ),
        ]
        _, _, contested = activity_coverage(activity_ownership(records))
        self.assertEqual(contested, ("declared-components-list-issue",))

    def test_full_ownership_reaches_exactly_one(self):
        records = [
            evaluate_assignment(entry, self.index) for entry in full_assignments()
        ]
        coverage, unassigned, contested = activity_coverage(
            activity_ownership(records)
        )
        self.assertAlmostEqual(coverage, 1.0, places=9)
        self.assertEqual(unassigned, ())
        self.assertEqual(contested, ())

    def test_coverage_is_criticality_weighted(self):
        records = [
            evaluate_assignment(assignment("part-selection-approval"), self.index)
        ]
        coverage, _, _ = activity_coverage(activity_ownership(records))
        expected = CONTROL_ACTIVITIES["part-selection-approval"] / sum(
            CONTROL_ACTIVITIES.values()
        )
        self.assertAlmostEqual(coverage, expected, places=9)

    def test_ownership_rejects_a_malformed_record(self):
        with self.assertRaises(ValueError):
            activity_ownership([{"no": "disposition"}])

    def test_holder_load_counts_accepted_ownerships_only(self):
        records = [
            evaluate_assignment(assignment("part-selection-approval"), self.index),
            evaluate_assignment(
                assignment(
                    "alert-and-advisory-handling",
                    assignment_id="A-ALERT",
                    holder_qualified=False,
                ),
                self.index,
            ),
        ]
        self.assertEqual(holder_load(records), {"parts-engineer-1": 1})


class AssessmentTests(unittest.TestCase):
    def spec(self, **overrides):
        base = {
            "units": [unit()],
            "assignments": full_assignments(),
            "required_coverage": 1.0,
            "max_activities_per_holder": 4,
        }
        base.update(overrides)
        return base

    def test_well_constituted_unit_is_accountable(self):
        result = assess_parts_control_organization(self.spec())
        self.assertTrue(result["accountable"])
        self.assertEqual(result["verdict"], "unit accountable")
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["activity_coverage"], 1.0, places=9)

    def test_a_dropped_activity_is_named_and_stops_the_verdict(self):
        assignments = [
            entry
            for entry in full_assignments()
            if entry["activity"] != "alert-and-advisory-handling"
        ]
        result = assess_parts_control_organization(self.spec(assignments=assignments))
        self.assertFalse(result["accountable"])
        self.assertEqual(
            result["unassigned_activities"], ("alert-and-advisory-handling",)
        )

    def test_embedded_unit_without_a_route_is_a_finding(self):
        result = assess_parts_control_organization(
            self.spec(units=[unit(reporting_line="design-authority")])
        )
        self.assertEqual(result["units_without_escalation_route"], (UNIT,))
        self.assertFalse(result["accountable"])

    def test_embedded_unit_with_a_route_passes(self):
        result = assess_parts_control_organization(
            self.spec(
                units=[
                    unit(
                        reporting_line="design-authority",
                        escalation_route_declared=True,
                    )
                ]
            )
        )
        self.assertEqual(result["units_without_escalation_route"], ())
        self.assertTrue(result["accountable"])

    def test_one_holder_carrying_everything_is_capped(self):
        assignments = [
            dict(entry, holder="the-only-engineer") for entry in full_assignments()
        ]
        result = assess_parts_control_organization(self.spec(assignments=assignments))
        self.assertEqual(result["overloaded_holders"], ("the-only-engineer",))
        self.assertFalse(result["accountable"])

    def test_findings_are_ranked_most_severe_first(self):
        assignments = full_assignments()
        assignments[0] = dict(assignments[0], unit_id="GHOST-OFFICE")
        assignments.append(
            assignment(
                "obsolescence-and-supply-monitoring",
                assignment_id="A-OBS-2",
                holder="parts-engineer-9",
                holder_qualified=False,
            )
        )
        result = assess_parts_control_organization(self.spec(assignments=assignments))
        severities = [entry["severity"] for entry in result["findings"]]
        self.assertEqual(severities, sorted(severities))

    def test_coverage_exactly_at_a_reduced_requirement_is_met(self):
        weights = CONTROL_ACTIVITIES
        keep = ("part-selection-approval", "nonconformance-disposition")
        assignments = [
            entry for entry in full_assignments() if entry["activity"] in keep
        ]
        required = sum(weights[name] for name in keep) / sum(weights.values())
        result = assess_parts_control_organization(
            self.spec(assignments=assignments, required_coverage=required)
        )
        self.assertAlmostEqual(
            result["activity_coverage"], result["required_coverage"], places=9
        )

    def test_duplicate_assignment_identifier_rejected(self):
        assignments = full_assignments()
        assignments.append(dict(assignments[0]))
        with self.assertRaises(ValueError):
            assess_parts_control_organization(self.spec(assignments=assignments))

    def test_duplicate_unit_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_control_organization(self.spec(units=[unit(), unit()]))

    def test_empty_unit_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_control_organization(self.spec(units=[]))

    def test_missing_key_rejected(self):
        spec = self.spec()
        del spec["assignments"]
        with self.assertRaises(ValueError):
            assess_parts_control_organization(spec)

    def test_out_of_range_required_coverage_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_control_organization(self.spec(required_coverage=1.4))

    def test_non_positive_holder_cap_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_control_organization(self.spec(max_activities_per_holder=0))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_control_organization("units and assignments")

    def test_tolerance_is_small_enough_to_be_representation_error(self):
        self.assertLess(COVERAGE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=1)
