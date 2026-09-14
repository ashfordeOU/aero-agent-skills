"""Contract tests for the clause 5.1.2.1 class 2 parts organization.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused organization
policy, a function with no contractual mandate, a part-selection approval
duty held by nobody, by two units or under delegation, a duty lent without
a recorded delegation, a credited coverage below its floor, and a function
embedded in the design authority with no product assurance escalation
route declared.
"""

import unittest

from q6013_class_2_parts_organization_logic import (
    ACCOUNTABILITY_CONTESTED,
    ANCHOR_DUTY_DELEGATED,
    CONTESTED,
    DEFAULT_ORGANIZATION_POLICY,
    DUTY_COVERAGE_SHORT,
    ESCALATION_ROUTE_NOT_DECLARED,
    EVALUATION_AND_SCREENING_CONTROL,
    FUNCTION_NOT_ESTABLISHED,
    HELD_BY_RECORDED_DELEGATION,
    HELD_DIRECTLY,
    NONCONFORMANCE_AND_ALERT_DISPOSITION,
    NON_DELEGABLE_DUTY,
    OBSOLESCENCE_AND_LIFETIME_BUY_CONTROL,
    ORGANIZATION_MEETS_CLASS_TWO,
    PARTS_LIST_CUSTODY,
    PART_SELECTION_APPROVAL,
    PROCUREMENT_SOURCE_APPROVAL,
    REQUIRED_DUTIES,
    UNASSIGNED,
    assess_parts_organization,
    competence_advisories,
    competence_shortfall_years,
    contested_duties,
    delegated_duties,
    duty_coverage,
    duty_disposition,
    effective_duty_coverage,
    function_is_mandated,
    named_parts_function,
    unassigned_duties,
    unrecorded_delegations,
    validate_organization_policy,
    validate_unit_record,
    validate_units,
)

ROUTE = "parts function to the project product assurance manager, PAP clause 5"


def _policy(**overrides):
    policy = dict(DEFAULT_ORGANIZATION_POLICY)
    policy.update(overrides)
    return policy


def _unit(identifier, duties, **overrides):
    unit = {
        "id": identifier,
        "duties": list(duties),
        "delegated_duties": [],
        "delegation_recorded": False,
        "competence_years": 6.0,
        "embedded_in_design_authority": False,
        "mandated_in_contract": True,
    }
    unit.update(overrides)
    return unit


def _units():
    return [
        _unit(
            "component-engineering-cell",
            [
                PART_SELECTION_APPROVAL,
                EVALUATION_AND_SCREENING_CONTROL,
                OBSOLESCENCE_AND_LIFETIME_BUY_CONTROL,
            ],
        ),
        _unit(
            "procurement-quality-desk",
            [PROCUREMENT_SOURCE_APPROVAL, NONCONFORMANCE_AND_ALERT_DISPOSITION],
            competence_years=4.5,
        ),
        _unit(
            "configuration-records-desk",
            [],
            delegated_duties=[PARTS_LIST_CUSTODY],
            delegation_recorded=True,
            competence_years=3.5,
            mandated_in_contract=False,
        ),
    ]


def _case(**overrides):
    case = {"units": _units(), "product_assurance_escalation_route": ROUTE}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_organization_policy(DEFAULT_ORGANIZATION_POLICY),
            DEFAULT_ORGANIZATION_POLICY,
        )

    def test_effective_floor_above_plain_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(
                _policy(min_duty_coverage=0.8, min_effective_coverage=0.9)
            )

    def test_non_positive_competence_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(_policy(min_competence_years=0.0))

    def test_marginal_band_wider_than_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(
                _policy(min_competence_years=3.0, marginal_competence_band_years=4.0)
            )

    def test_zero_delegation_credit_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(_policy(delegated_duty_credit=0.0))

    def test_delegation_credit_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(_policy(delegated_duty_credit=1.4))

    def test_non_boolean_escalation_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(
                _policy(require_escalation_route_when_embedded="sometimes")
            )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(["min_competence_years"])


class UnitValidationTests(unittest.TestCase):
    def test_a_good_unit_reads_back_its_duties(self):
        record = validate_unit_record(_unit("u1", [EVALUATION_AND_SCREENING_CONTROL]))
        self.assertEqual(record["duties"], (EVALUATION_AND_SCREENING_CONTROL,))

    def test_blank_unit_id_refused(self):
        with self.assertRaises(ValueError):
            validate_unit_record(_unit("   ", [EVALUATION_AND_SCREENING_CONTROL]))

    def test_unrecognised_duty_name_refused(self):
        with self.assertRaises(ValueError):
            validate_unit_record(_unit("u1", ["parts-vibes-oversight"]))

    def test_duty_listed_twice_refused(self):
        with self.assertRaises(ValueError):
            validate_unit_record(
                _unit(
                    "u1",
                    [
                        EVALUATION_AND_SCREENING_CONTROL,
                        EVALUATION_AND_SCREENING_CONTROL,
                    ],
                )
            )

    def test_duty_held_directly_and_under_delegation_refused(self):
        with self.assertRaises(ValueError):
            validate_unit_record(
                _unit(
                    "u1",
                    [EVALUATION_AND_SCREENING_CONTROL],
                    delegated_duties=[EVALUATION_AND_SCREENING_CONTROL],
                    delegation_recorded=True,
                )
            )

    def test_recorded_delegation_lending_nothing_refused(self):
        with self.assertRaises(ValueError):
            validate_unit_record(
                _unit("u1", [PARTS_LIST_CUSTODY], delegation_recorded=True)
            )

    def test_negative_competence_refused(self):
        with self.assertRaises(ValueError):
            validate_unit_record(
                _unit("u1", [PARTS_LIST_CUSTODY], competence_years=-1.0)
            )

    def test_non_boolean_embedding_refused(self):
        with self.assertRaises(ValueError):
            validate_unit_record(
                _unit(
                    "u1",
                    [PARTS_LIST_CUSTODY],
                    embedded_in_design_authority="partly",
                )
            )

    def test_duplicate_unit_id_refused(self):
        with self.assertRaises(ValueError):
            validate_units(
                [
                    _unit("u1", [PARTS_LIST_CUSTODY]),
                    _unit("u1", [PART_SELECTION_APPROVAL]),
                ]
            )

    def test_empty_unit_set_refused(self):
        with self.assertRaises(ValueError):
            validate_units([])


class DispositionTests(unittest.TestCase):
    def test_every_required_duty_appears_in_the_disposition(self):
        disposition = duty_disposition(_units())
        self.assertEqual(set(disposition), set(REQUIRED_DUTIES))

    def test_a_complete_organization_disposes_every_duty(self):
        self.assertEqual(unassigned_duties(_units()), ())
        self.assertEqual(contested_duties(_units()), ())
        self.assertAlmostEqual(duty_coverage(_units()), 1.0, places=9)

    def test_a_delegated_duty_is_named_and_credited_below_one(self):
        self.assertEqual(delegated_duties(_units()), (PARTS_LIST_CUSTODY,))
        self.assertEqual(
            duty_disposition(_units())[PARTS_LIST_CUSTODY]["state"],
            HELD_BY_RECORDED_DELEGATION,
        )
        self.assertAlmostEqual(
            effective_duty_coverage(_units()),
            (5.0 + 0.75) / len(REQUIRED_DUTIES),
            places=9,
        )

    def test_a_directly_held_duty_is_credited_in_full(self):
        units = _units()
        units[2]["duties"] = [PARTS_LIST_CUSTODY]
        units[2]["delegated_duties"] = []
        units[2]["delegation_recorded"] = False
        self.assertEqual(
            duty_disposition(units)[PARTS_LIST_CUSTODY]["state"], HELD_DIRECTLY
        )
        self.assertAlmostEqual(effective_duty_coverage(units), 1.0, places=9)

    def test_an_unrecorded_delegation_leaves_the_duty_unassigned(self):
        units = _units()
        units[2]["delegation_recorded"] = False
        self.assertEqual(unassigned_duties(units), (PARTS_LIST_CUSTODY,))
        self.assertEqual(
            duty_disposition(units)[PARTS_LIST_CUSTODY]["state"], UNASSIGNED
        )
        self.assertEqual(
            unrecorded_delegations(units),
            (("configuration-records-desk", PARTS_LIST_CUSTODY),),
        )

    def test_two_direct_holders_are_contested(self):
        units = _units()
        units[1]["duties"].append(EVALUATION_AND_SCREENING_CONTROL)
        self.assertEqual(contested_duties(units), (EVALUATION_AND_SCREENING_CONTROL,))
        self.assertEqual(
            duty_disposition(units)[EVALUATION_AND_SCREENING_CONTROL]["state"],
            CONTESTED,
        )

    def test_the_non_delegable_duty_names_the_function(self):
        self.assertEqual(NON_DELEGABLE_DUTY, PART_SELECTION_APPROVAL)
        self.assertEqual(
            named_parts_function(_units())["id"], "component-engineering-cell"
        )

    def test_a_delegated_anchor_duty_names_nobody(self):
        units = _units()
        units[0]["duties"].remove(PART_SELECTION_APPROVAL)
        units[2]["delegated_duties"].append(PART_SELECTION_APPROVAL)
        self.assertIsNone(named_parts_function(units))

    def test_mandate_is_read_across_the_whole_organization(self):
        self.assertTrue(function_is_mandated(_units()))
        units = [_unit("u1", [PART_SELECTION_APPROVAL], mandated_in_contract=False)]
        self.assertFalse(function_is_mandated(units))


class CompetenceTests(unittest.TestCase):
    def test_a_unit_on_the_floor_has_no_shortfall(self):
        unit = _unit("u1", [PARTS_LIST_CUSTODY], competence_years=3.0)
        self.assertAlmostEqual(
            competence_shortfall_years(unit, _policy(min_competence_years=3.0)),
            0.0,
            places=9,
        )

    def test_a_thin_unit_reports_the_gap_in_years(self):
        unit = _unit("u1", [PARTS_LIST_CUSTODY], competence_years=1.25)
        self.assertAlmostEqual(
            competence_shortfall_years(unit, _policy(min_competence_years=3.0)),
            1.75,
            places=9,
        )

    def test_a_unit_just_above_the_floor_raises_an_advisory(self):
        units = [_unit("u1", list(REQUIRED_DUTIES), competence_years=3.5)]
        advisories = competence_advisories(
            units, _policy(min_competence_years=3.0, marginal_competence_band_years=1.0)
        )
        self.assertEqual(len(advisories), 1)
        self.assertIn("u1", advisories[0])

    def test_a_comfortable_unit_raises_no_advisory(self):
        units = [_unit("u1", list(REQUIRED_DUTIES), competence_years=12.0)]
        self.assertEqual(
            competence_advisories(units, _policy(min_competence_years=3.0)), ()
        )


class AssessmentTests(unittest.TestCase):
    def test_a_sound_organization_meets_the_class(self):
        result = assess_parts_organization(_case())
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_TWO)
        self.assertEqual(result["named_function_id"], "component-engineering-cell")
        self.assertAlmostEqual(result["duty_coverage"], 1.0, places=9)
        self.assertAlmostEqual(
            result["effective_duty_coverage"],
            (5.0 + 0.75) / len(REQUIRED_DUTIES),
            places=9,
        )

    def test_an_absent_organization_is_not_established(self):
        case = _case()
        del case["units"]
        result = assess_parts_organization(case)
        self.assertEqual(result["verdict"], FUNCTION_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_an_unmandated_organization_is_not_established(self):
        units = _units()
        for unit in units:
            unit["mandated_in_contract"] = False
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], FUNCTION_NOT_ESTABLISHED)

    def test_no_anchor_holder_is_not_established(self):
        units = _units()
        units[0]["duties"].remove(PART_SELECTION_APPROVAL)
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], FUNCTION_NOT_ESTABLISHED)

    def test_a_delegated_anchor_duty_closes_the_assessment(self):
        units = _units()
        units[0]["duties"].remove(PART_SELECTION_APPROVAL)
        units[2]["delegated_duties"].append(PART_SELECTION_APPROVAL)
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], ANCHOR_DUTY_DELEGATED)

    def test_two_anchor_holders_are_contested(self):
        units = _units()
        units[1]["duties"].append(PART_SELECTION_APPROVAL)
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], ACCOUNTABILITY_CONTESTED)

    def test_a_contested_support_duty_is_reported_by_name(self):
        units = _units()
        units[1]["duties"].append(OBSOLESCENCE_AND_LIFETIME_BUY_CONTROL)
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], ACCOUNTABILITY_CONTESTED)
        self.assertEqual(
            result["contested_duties"], (OBSOLESCENCE_AND_LIFETIME_BUY_CONTROL,)
        )

    def test_every_gap_is_named_not_only_the_first(self):
        units = _units()
        units[1]["duties"] = []
        units[2]["delegated_duties"] = []
        units[2]["delegation_recorded"] = False
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], DUTY_COVERAGE_SHORT)
        self.assertEqual(len(result["unassigned_duties"]), 3)

    def test_an_unrecorded_delegation_reaches_the_findings(self):
        units = _units()
        units[2]["delegation_recorded"] = False
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], DUTY_COVERAGE_SHORT)
        self.assertEqual(len(result["unrecorded_delegations"]), 1)
        self.assertTrue(
            any("nobody recorded" in finding for finding in result["findings"])
        )

    def test_an_organization_run_through_delegation_fails_the_credited_floor(self):
        units = [
            _unit("parts-office", [PART_SELECTION_APPROVAL]),
            _unit(
                "outsourced-parts-service",
                [],
                delegated_duties=[
                    duty for duty in REQUIRED_DUTIES if duty != PART_SELECTION_APPROVAL
                ],
                delegation_recorded=True,
            ),
        ]
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], DUTY_COVERAGE_SHORT)
        self.assertAlmostEqual(result["duty_coverage"], 1.0, places=9)
        self.assertAlmostEqual(
            result["effective_duty_coverage"],
            (1.0 + 5.0 * 0.75) / len(REQUIRED_DUTIES),
            places=9,
        )

    def test_an_embedded_function_without_a_route_closes_the_assessment(self):
        units = _units()
        units[0]["embedded_in_design_authority"] = True
        result = assess_parts_organization(
            _case(units=units, product_assurance_escalation_route="  ")
        )
        self.assertEqual(result["verdict"], ESCALATION_ROUTE_NOT_DECLARED)

    def test_an_embedded_function_with_a_route_is_accepted_at_this_class(self):
        units = _units()
        units[0]["embedded_in_design_authority"] = True
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_TWO)
        self.assertEqual(result["escalation_route"], ROUTE)

    def test_the_route_requirement_may_be_waived_by_policy(self):
        units = _units()
        units[0]["embedded_in_design_authority"] = True
        result = assess_parts_organization(
            _case(units=units, product_assurance_escalation_route=""),
            _policy(require_escalation_route_when_embedded=False),
        )
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_TWO)

    def test_advisories_travel_with_a_passing_verdict(self):
        units = _units()
        for unit in units:
            unit["competence_years"] = 3.4
        result = assess_parts_organization(
            _case(units=units),
            _policy(min_competence_years=3.0, marginal_competence_band_years=1.0),
        )
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_TWO)
        self.assertEqual(len(result["advisories"]), 3)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_parts_organization(["units"])


if __name__ == "__main__":
    unittest.main()
