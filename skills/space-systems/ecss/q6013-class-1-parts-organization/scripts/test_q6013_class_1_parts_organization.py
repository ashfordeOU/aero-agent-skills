"""Contract tests for the clause 4.1.2.1 class 1 parts organization.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused organization
policy, an organization with no contractual mandate, an anchor duty held by
nobody or by two units, an unassigned or split duty, an accountable unit
sitting inside the design authority, and a missing customer escalation
route.
"""

import unittest

from q6013_class_1_parts_organization_logic import (
    ACCOUNTABILITY_NOT_SINGULAR,
    ACCOUNTABLE_UNIT_NOT_INDEPENDENT,
    ANCHOR_ACCOUNTABILITY,
    DEFAULT_ORGANIZATION_POLICY,
    ESCALATION_ROUTE_NOT_DECLARED,
    EVALUATION_AUTHORITY,
    NONCONFORMANCE_AND_ALERT_DISPOSITION,
    OBSOLESCENCE_AND_LIFETIME_BUY_CONTROL,
    ORGANIZATION_MEETS_CLASS_ONE,
    ORGANIZATION_NOT_ESTABLISHED,
    PARTS_LIST_AND_TRACEABILITY_CUSTODY,
    PART_SELECTION_APPROVAL,
    PROCUREMENT_SOURCE_APPROVAL,
    REQUIRED_ACCOUNTABILITIES,
    SCREENING_AND_LOT_ACCEPTANCE_CONTROL,
    accountability_assignment,
    accountability_coverage,
    assess_parts_organization,
    competence_advisories,
    competence_shortfall_years,
    nominated_accountable_unit,
    organization_is_mandated,
    split_accountabilities,
    unassigned_accountabilities,
    validate_organization_policy,
    validate_unit_record,
    validate_units,
)

ROUTE = "PA-chain to the customer product assurance manager, PAP clause 6"


def _policy(**overrides):
    policy = dict(DEFAULT_ORGANIZATION_POLICY)
    policy.update(overrides)
    return policy


def _unit(identifier, duties, **overrides):
    unit = {
        "id": identifier,
        "accountabilities": list(duties),
        "competence_years": 9.0,
        "independent_of_design_authority": True,
        "mandated_in_contract": True,
    }
    unit.update(overrides)
    return unit


def _units():
    return [
        _unit(
            "component-engineering-office",
            [
                PART_SELECTION_APPROVAL,
                EVALUATION_AUTHORITY,
                SCREENING_AND_LOT_ACCEPTANCE_CONTROL,
                OBSOLESCENCE_AND_LIFETIME_BUY_CONTROL,
            ],
        ),
        _unit(
            "procurement-quality-cell",
            [PROCUREMENT_SOURCE_APPROVAL, NONCONFORMANCE_AND_ALERT_DISPOSITION],
            competence_years=7.5,
        ),
        _unit(
            "configuration-records-desk",
            [PARTS_LIST_AND_TRACEABILITY_CUSTODY],
            competence_years=6.0,
            mandated_in_contract=False,
        ),
    ]


def _case(**overrides):
    case = {"units": _units(), "customer_escalation_route": ROUTE}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_organization_policy(DEFAULT_ORGANIZATION_POLICY),
            DEFAULT_ORGANIZATION_POLICY,
        )

    def test_coverage_floor_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(_policy(min_accountability_coverage=1.4))

    def test_non_positive_competence_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(_policy(min_competence_years=0.0))

    def test_marginal_band_wider_than_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(
                _policy(min_competence_years=5.0, marginal_competence_band_years=6.0)
            )

    def test_non_boolean_escalation_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(
                _policy(require_customer_escalation_route="yes")
            )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(["min_competence_years"])


class UnitValidationTests(unittest.TestCase):
    def test_a_good_unit_reads_back_its_duties(self):
        record = validate_unit_record(_unit("u1", [EVALUATION_AUTHORITY]))
        self.assertEqual(record["accountabilities"], (EVALUATION_AUTHORITY,))

    def test_blank_unit_id_refused(self):
        with self.assertRaises(ValueError):
            validate_unit_record(_unit("   ", [EVALUATION_AUTHORITY]))

    def test_unrecognised_duty_name_refused(self):
        with self.assertRaises(ValueError):
            validate_unit_record(_unit("u1", ["parts-vibes-oversight"]))

    def test_duty_listed_twice_on_one_unit_refused(self):
        with self.assertRaises(ValueError):
            validate_unit_record(
                _unit("u1", [EVALUATION_AUTHORITY, EVALUATION_AUTHORITY])
            )

    def test_negative_competence_refused(self):
        with self.assertRaises(ValueError):
            validate_unit_record(
                _unit("u1", [EVALUATION_AUTHORITY], competence_years=-2.0)
            )

    def test_non_boolean_independence_refused(self):
        with self.assertRaises(ValueError):
            validate_unit_record(
                _unit(
                    "u1",
                    [EVALUATION_AUTHORITY],
                    independent_of_design_authority="mostly",
                )
            )

    def test_duplicate_unit_id_refused(self):
        with self.assertRaises(ValueError):
            validate_units(
                [_unit("u1", [EVALUATION_AUTHORITY]), _unit("u1", [PART_SELECTION_APPROVAL])]
            )

    def test_empty_unit_set_refused(self):
        with self.assertRaises(ValueError):
            validate_units([])


class AssignmentTests(unittest.TestCase):
    def test_every_required_duty_appears_in_the_assignment(self):
        assignment = accountability_assignment(_units())
        self.assertEqual(set(assignment), set(REQUIRED_ACCOUNTABILITIES))

    def test_a_complete_organization_covers_every_duty_once(self):
        self.assertAlmostEqual(accountability_coverage(_units()), 1.0, places=9)
        self.assertEqual(unassigned_accountabilities(_units()), ())
        self.assertEqual(split_accountabilities(_units()), ())

    def test_a_dropped_duty_is_named_and_lowers_the_coverage(self):
        units = _units()
        units[2]["accountabilities"] = []
        self.assertEqual(
            unassigned_accountabilities(units), (PARTS_LIST_AND_TRACEABILITY_CUSTODY,)
        )
        self.assertAlmostEqual(
            accountability_coverage(units),
            (len(REQUIRED_ACCOUNTABILITIES) - 1) / len(REQUIRED_ACCOUNTABILITIES),
            places=9,
        )

    def test_a_shared_duty_is_a_split_not_redundancy(self):
        units = _units()
        units[1]["accountabilities"].append(EVALUATION_AUTHORITY)
        self.assertEqual(split_accountabilities(units), (EVALUATION_AUTHORITY,))
        self.assertAlmostEqual(
            accountability_coverage(units),
            (len(REQUIRED_ACCOUNTABILITIES) - 1) / len(REQUIRED_ACCOUNTABILITIES),
            places=9,
        )

    def test_the_anchor_duty_names_the_accountable_unit(self):
        self.assertEqual(ANCHOR_ACCOUNTABILITY, PART_SELECTION_APPROVAL)
        self.assertEqual(
            nominated_accountable_unit(_units())["id"], "component-engineering-office"
        )

    def test_two_anchor_holders_name_nobody(self):
        units = _units()
        units[1]["accountabilities"].append(PART_SELECTION_APPROVAL)
        self.assertIsNone(nominated_accountable_unit(units))

    def test_mandate_is_read_across_the_whole_organization(self):
        self.assertTrue(organization_is_mandated(_units()))
        units = [_unit("u1", [PART_SELECTION_APPROVAL], mandated_in_contract=False)]
        self.assertFalse(organization_is_mandated(units))


class CompetenceTests(unittest.TestCase):
    def test_a_unit_on_the_floor_has_no_shortfall(self):
        unit = _unit("u1", [EVALUATION_AUTHORITY], competence_years=5.0)
        self.assertAlmostEqual(
            competence_shortfall_years(unit, _policy(min_competence_years=5.0)),
            0.0,
            places=9,
        )

    def test_a_thin_unit_reports_the_gap_in_years(self):
        unit = _unit("u1", [EVALUATION_AUTHORITY], competence_years=3.25)
        self.assertAlmostEqual(
            competence_shortfall_years(unit, _policy(min_competence_years=5.0)),
            1.75,
            places=9,
        )

    def test_a_unit_just_above_the_floor_raises_an_advisory(self):
        units = [
            _unit(
                "u1",
                list(REQUIRED_ACCOUNTABILITIES),
                competence_years=5.5,
            )
        ]
        advisories = competence_advisories(
            units, _policy(min_competence_years=5.0, marginal_competence_band_years=1.0)
        )
        self.assertEqual(len(advisories), 1)
        self.assertIn("u1", advisories[0])

    def test_a_comfortable_unit_raises_no_advisory(self):
        units = [_unit("u1", list(REQUIRED_ACCOUNTABILITIES), competence_years=14.0)]
        self.assertEqual(
            competence_advisories(units, _policy(min_competence_years=5.0)), ()
        )


class AssessmentTests(unittest.TestCase):
    def test_a_sound_organization_meets_the_class(self):
        result = assess_parts_organization(_case())
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_ONE)
        self.assertEqual(result["accountable_unit_id"], "component-engineering-office")
        self.assertAlmostEqual(result["accountability_coverage"], 1.0, places=9)

    def test_an_absent_organization_is_not_established(self):
        case = _case()
        del case["units"]
        result = assess_parts_organization(case)
        self.assertEqual(result["verdict"], ORGANIZATION_NOT_ESTABLISHED)
        self.assertTrue(result["findings"])

    def test_an_unmandated_organization_is_not_established(self):
        units = _units()
        for unit in units:
            unit["mandated_in_contract"] = False
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], ORGANIZATION_NOT_ESTABLISHED)

    def test_no_anchor_holder_is_not_established(self):
        units = _units()
        units[0]["accountabilities"].remove(PART_SELECTION_APPROVAL)
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], ORGANIZATION_NOT_ESTABLISHED)

    def test_two_anchor_holders_is_not_singular(self):
        units = _units()
        units[1]["accountabilities"].append(PART_SELECTION_APPROVAL)
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], ACCOUNTABILITY_NOT_SINGULAR)

    def test_every_gap_is_named_not_only_the_first(self):
        units = _units()
        units[1]["accountabilities"] = []
        units[2]["accountabilities"] = []
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], ACCOUNTABILITY_NOT_SINGULAR)
        self.assertEqual(len(result["unassigned_accountabilities"]), 3)

    def test_a_dependent_accountable_unit_fails_on_structure(self):
        units = _units()
        units[0]["independent_of_design_authority"] = False
        result = assess_parts_organization(_case(units=units))
        self.assertEqual(result["verdict"], ACCOUNTABLE_UNIT_NOT_INDEPENDENT)

    def test_a_missing_escalation_route_closes_the_assessment(self):
        result = assess_parts_organization(_case(customer_escalation_route="  "))
        self.assertEqual(result["verdict"], ESCALATION_ROUTE_NOT_DECLARED)

    def test_the_escalation_route_may_be_waived_by_policy(self):
        result = assess_parts_organization(
            _case(customer_escalation_route=""),
            _policy(require_customer_escalation_route=False),
        )
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_ONE)

    def test_advisories_travel_with_a_passing_verdict(self):
        units = _units()
        for unit in units:
            unit["competence_years"] = 5.4
        result = assess_parts_organization(
            _case(units=units),
            _policy(min_competence_years=5.0, marginal_competence_band_years=1.0),
        )
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_ONE)
        self.assertEqual(len(result["advisories"]), 3)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_parts_organization(["units"])


if __name__ == "__main__":
    unittest.main()
