"""Contract tests for the clause 6.1.2.1 class 3 parts organization.

Every workflow step the SKILL.md sets out is exercised here, together with the
stop conditions the gate 3 contract reviews: a refused responsibility policy,
an organization recorded nowhere in the project plan, an anchor duty nobody
holds, a coverage judged at its below-unity floor under a named tolerance, a
role carrying combined duties with no deputy named, a declared effort judged
at its floor, and a missing parts decision record location.
"""

import unittest

from q6013_class_3_parts_organization_logic import (
    ALERT_AND_NONCONFORMANCE_DISPOSITION,
    ANCHOR_RESPONSIBILITY,
    CONTINUITY_NOT_ASSURED,
    COVERAGE_BELOW_CLASS_FLOOR,
    DECISION_RECORD_NOT_LOCATED,
    DEFAULT_RESPONSIBILITY_POLICY,
    EFFORT_BELOW_FLOOR,
    INCOMING_ACCEPTANCE_CONTROL,
    ORGANIZATION_MEETS_CLASS_THREE,
    PARTS_LIST_AND_TRACEABILITY_CUSTODY,
    PART_SELECTION_AND_APPROVAL,
    PROCUREMENT_SOURCE_CONTROL,
    REQUIRED_RESPONSIBILITIES,
    RESPONSIBILITY_NOT_ASSIGNED,
    anchor_is_held,
    assess_parts_responsibility,
    concentrated_roles,
    embedded_roles,
    responsibility_assignment,
    responsibility_coverage,
    roles_outside_the_project_plan,
    total_declared_effort_fte,
    unassigned_responsibilities,
    validate_responsibility_policy,
    validate_role_record,
    validate_roles,
)

LOCATION = "parts decision log in the project configuration record, section 7"


def _policy(**overrides):
    policy = dict(DEFAULT_RESPONSIBILITY_POLICY)
    policy.update(overrides)
    return policy


def _role(identifier, duties, **overrides):
    role = {
        "id": identifier,
        "responsibilities": list(duties),
        "effort_fte": 0.3,
        "deputy_named": True,
        "recorded_in_project_plan": True,
        "inside_design_authority": False,
    }
    role.update(overrides)
    return role


def _roles():
    return [
        _role(
            "project-parts-engineer",
            [PART_SELECTION_AND_APPROVAL, PROCUREMENT_SOURCE_CONTROL],
            effort_fte=0.4,
        ),
        _role(
            "assembly-acceptance-lead",
            [INCOMING_ACCEPTANCE_CONTROL, ALERT_AND_NONCONFORMANCE_DISPOSITION],
            effort_fte=0.25,
        ),
        _role(
            "configuration-records-desk",
            [PARTS_LIST_AND_TRACEABILITY_CUSTODY],
            effort_fte=0.15,
        ),
    ]


def _case(**overrides):
    case = {"roles": _roles(), "decision_record_location": LOCATION}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_responsibility_policy(DEFAULT_RESPONSIBILITY_POLICY),
            DEFAULT_RESPONSIBILITY_POLICY,
        )

    def test_the_class_floor_sits_below_unity(self):
        self.assertLess(
            float(DEFAULT_RESPONSIBILITY_POLICY["min_responsibility_coverage"]), 1.0
        )

    def test_coverage_floor_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_responsibility_policy(_policy(min_responsibility_coverage=1.3))

    def test_effort_floor_beyond_the_duty_set_refused(self):
        with self.assertRaises(ValueError):
            validate_responsibility_policy(_policy(min_total_effort_fte=9.0))

    def test_a_concentration_ceiling_covering_every_duty_refused(self):
        with self.assertRaises(ValueError):
            validate_responsibility_policy(
                _policy(max_responsibilities_without_deputy=len(REQUIRED_RESPONSIBILITIES) + 1)
            )

    def test_fractional_concentration_ceiling_refused(self):
        with self.assertRaises(ValueError):
            validate_responsibility_policy(_policy(max_responsibilities_without_deputy=2.5))

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_responsibility_policy(["min_total_effort_fte"])


class RoleValidationTests(unittest.TestCase):
    def test_a_good_role_reads_back_its_duties(self):
        record = validate_role_record(_role("r1", [INCOMING_ACCEPTANCE_CONTROL]))
        self.assertEqual(record["responsibilities"], (INCOMING_ACCEPTANCE_CONTROL,))

    def test_blank_role_id_refused(self):
        with self.assertRaises(ValueError):
            validate_role_record(_role("   ", [INCOMING_ACCEPTANCE_CONTROL]))

    def test_unrecognised_duty_name_refused(self):
        with self.assertRaises(ValueError):
            validate_role_record(_role("r1", ["parts-vibes-oversight"]))

    def test_duty_listed_twice_on_one_role_refused(self):
        with self.assertRaises(ValueError):
            validate_role_record(
                _role("r1", [INCOMING_ACCEPTANCE_CONTROL, INCOMING_ACCEPTANCE_CONTROL])
            )

    def test_effort_beyond_one_person_refused(self):
        with self.assertRaises(ValueError):
            validate_role_record(
                _role("r1", [INCOMING_ACCEPTANCE_CONTROL], effort_fte=1.4)
            )

    def test_negative_effort_refused(self):
        with self.assertRaises(ValueError):
            validate_role_record(
                _role("r1", [INCOMING_ACCEPTANCE_CONTROL], effort_fte=-0.1)
            )

    def test_non_boolean_deputy_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_role_record(
                _role("r1", [INCOMING_ACCEPTANCE_CONTROL], deputy_named="sort of")
            )

    def test_duplicate_role_id_refused(self):
        with self.assertRaises(ValueError):
            validate_roles(
                [
                    _role("r1", [INCOMING_ACCEPTANCE_CONTROL]),
                    _role("r1", [PART_SELECTION_AND_APPROVAL]),
                ]
            )

    def test_empty_role_set_refused(self):
        with self.assertRaises(ValueError):
            validate_roles([])


class AssignmentTests(unittest.TestCase):
    def test_every_required_duty_appears_in_the_assignment(self):
        assignment = responsibility_assignment(_roles())
        self.assertEqual(set(assignment), set(REQUIRED_RESPONSIBILITIES))

    def test_a_complete_organization_covers_every_duty(self):
        self.assertAlmostEqual(responsibility_coverage(_roles()), 1.0, places=9)
        self.assertEqual(unassigned_responsibilities(_roles()), ())

    def test_a_shared_duty_still_counts_as_covered_at_this_class(self):
        roles = _roles()
        roles[1]["responsibilities"].append(PROCUREMENT_SOURCE_CONTROL)
        self.assertAlmostEqual(responsibility_coverage(roles), 1.0, places=9)
        self.assertEqual(
            responsibility_assignment(roles)[PROCUREMENT_SOURCE_CONTROL],
            ("project-parts-engineer", "assembly-acceptance-lead"),
        )

    def test_a_dropped_duty_is_named_and_lowers_the_coverage(self):
        roles = _roles()
        roles[2]["responsibilities"] = []
        self.assertEqual(
            unassigned_responsibilities(roles),
            (PARTS_LIST_AND_TRACEABILITY_CUSTODY,),
        )
        self.assertAlmostEqual(
            responsibility_coverage(roles),
            (len(REQUIRED_RESPONSIBILITIES) - 1) / len(REQUIRED_RESPONSIBILITIES),
            places=9,
        )

    def test_the_anchor_duty_is_part_selection_approval(self):
        self.assertEqual(ANCHOR_RESPONSIBILITY, PART_SELECTION_AND_APPROVAL)
        self.assertTrue(anchor_is_held(_roles()))

    def test_an_organization_with_no_anchor_holder_is_detected(self):
        roles = _roles()
        roles[0]["responsibilities"].remove(PART_SELECTION_AND_APPROVAL)
        self.assertFalse(anchor_is_held(roles))

    def test_roles_outside_the_project_plan_are_named(self):
        roles = _roles()
        roles[2]["recorded_in_project_plan"] = False
        self.assertEqual(
            roles_outside_the_project_plan(roles), ("configuration-records-desk",)
        )

    def test_embedded_roles_are_named_without_being_judged(self):
        roles = _roles()
        roles[0]["inside_design_authority"] = True
        self.assertEqual(embedded_roles(roles), ("project-parts-engineer",))


class ConcentrationAndEffortTests(unittest.TestCase):
    def test_a_role_on_the_ceiling_with_no_deputy_is_accepted(self):
        roles = [
            _role(
                "one-engineer",
                [PART_SELECTION_AND_APPROVAL, PROCUREMENT_SOURCE_CONTROL],
                deputy_named=False,
            )
        ]
        self.assertEqual(concentrated_roles(roles), ())

    def test_a_role_past_the_ceiling_with_no_deputy_is_flagged(self):
        roles = [
            _role(
                "one-engineer",
                list(REQUIRED_RESPONSIBILITIES),
                deputy_named=False,
            )
        ]
        self.assertEqual(concentrated_roles(roles), ("one-engineer",))

    def test_a_deputy_clears_the_concentration(self):
        roles = [_role("one-engineer", list(REQUIRED_RESPONSIBILITIES))]
        self.assertEqual(concentrated_roles(roles), ())

    def test_declared_effort_totals_across_the_roles(self):
        self.assertAlmostEqual(total_declared_effort_fte(_roles()), 0.8, places=9)


class AssessmentTests(unittest.TestCase):
    def test_a_sound_organization_meets_the_class(self):
        result = assess_parts_responsibility(_case())
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_THREE)
        self.assertAlmostEqual(result["responsibility_coverage"], 1.0, places=9)
        self.assertEqual(result["anchor_holders"], ("project-parts-engineer",))

    def test_an_absent_organization_assigns_nothing(self):
        case = _case()
        del case["roles"]
        result = assess_parts_responsibility(case)
        self.assertEqual(result["verdict"], RESPONSIBILITY_NOT_ASSIGNED)
        self.assertTrue(result["findings"])

    def test_an_organization_in_no_project_plan_assigns_nothing(self):
        roles = _roles()
        for role in roles:
            role["recorded_in_project_plan"] = False
        result = assess_parts_responsibility(_case(roles=roles))
        self.assertEqual(result["verdict"], RESPONSIBILITY_NOT_ASSIGNED)

    def test_one_unrecorded_role_is_an_advisory_not_a_refusal(self):
        roles = _roles()
        roles[2]["recorded_in_project_plan"] = False
        result = assess_parts_responsibility(_case(roles=roles))
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_THREE)
        self.assertTrue(
            any("configuration-records-desk" in note for note in result["advisories"])
        )

    def test_no_anchor_holder_closes_the_assessment(self):
        roles = _roles()
        roles[0]["responsibilities"].remove(PART_SELECTION_AND_APPROVAL)
        result = assess_parts_responsibility(_case(roles=roles))
        self.assertEqual(result["verdict"], RESPONSIBILITY_NOT_ASSIGNED)
        self.assertIsNone(result["responsibility_coverage"])

    def test_one_duty_gap_sits_exactly_on_the_class_floor_and_passes(self):
        roles = _roles()
        roles[2]["responsibilities"] = []
        result = assess_parts_responsibility(_case(roles=roles))
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_THREE)
        self.assertAlmostEqual(
            result["responsibility_coverage"],
            (len(REQUIRED_RESPONSIBILITIES) - 1) / len(REQUIRED_RESPONSIBILITIES),
            places=9,
        )
        self.assertEqual(len(result["advisories"]), 1)

    def test_two_duty_gaps_fall_below_the_class_floor(self):
        roles = _roles()
        roles[2]["responsibilities"] = []
        roles[1]["responsibilities"] = [INCOMING_ACCEPTANCE_CONTROL]
        result = assess_parts_responsibility(_case(roles=roles))
        self.assertEqual(result["verdict"], COVERAGE_BELOW_CLASS_FLOOR)
        self.assertEqual(len(result["unassigned_responsibilities"]), 2)

    def test_a_single_role_holding_everything_without_a_deputy_fails_continuity(self):
        roles = [
            _role(
                "one-engineer",
                list(REQUIRED_RESPONSIBILITIES),
                deputy_named=False,
                effort_fte=0.9,
            )
        ]
        result = assess_parts_responsibility(_case(roles=roles))
        self.assertEqual(result["verdict"], CONTINUITY_NOT_ASSURED)
        self.assertEqual(result["concentrated_roles"], ("one-engineer",))

    def test_the_same_role_with_a_deputy_meets_the_class(self):
        roles = [
            _role("one-engineer", list(REQUIRED_RESPONSIBILITIES), effort_fte=0.9)
        ]
        result = assess_parts_responsibility(_case(roles=roles))
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_THREE)

    def test_effort_below_the_floor_closes_the_assessment(self):
        roles = _roles()
        for role in roles:
            role["effort_fte"] = 0.05
        result = assess_parts_responsibility(_case(roles=roles))
        self.assertEqual(result["verdict"], EFFORT_BELOW_FLOOR)

    def test_effort_landing_exactly_on_the_floor_passes(self):
        roles = _roles()
        roles[0]["effort_fte"] = 0.3
        roles[1]["effort_fte"] = 0.1
        roles[2]["effort_fte"] = 0.1
        result = assess_parts_responsibility(_case(roles=roles))
        self.assertAlmostEqual(
            result["total_declared_effort_fte"],
            float(DEFAULT_RESPONSIBILITY_POLICY["min_total_effort_fte"]),
            places=9,
        )
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_THREE)

    def test_a_missing_decision_record_location_closes_the_assessment(self):
        result = assess_parts_responsibility(_case(decision_record_location="   "))
        self.assertEqual(result["verdict"], DECISION_RECORD_NOT_LOCATED)

    def test_the_decision_record_location_may_be_waived_by_policy(self):
        result = assess_parts_responsibility(
            _case(decision_record_location=""),
            _policy(require_decision_record_location=False),
        )
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_THREE)

    def test_an_embedded_role_travels_as_an_advisory_with_a_passing_verdict(self):
        roles = _roles()
        roles[0]["inside_design_authority"] = True
        result = assess_parts_responsibility(_case(roles=roles))
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_THREE)
        self.assertTrue(
            any("project-parts-engineer" in note for note in result["advisories"])
        )

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_parts_responsibility(["roles"])


if __name__ == "__main__":
    unittest.main()
