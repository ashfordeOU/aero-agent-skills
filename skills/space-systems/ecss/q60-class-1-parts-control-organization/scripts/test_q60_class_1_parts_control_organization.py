"""Contract tests for the clause 4.1.2.1 parts control organization.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused adequacy
policy, a unit with no name, lead or appointment, a required function
with no holder, a function held by an unqualified name, a function funded
below its effort floor, a reporting line into the constrained authority,
a unit not independent of the design authority, control concentrated on
one holder and an organization the customer never agreed.
"""

import unittest

from q60_class_1_parts_control_organization_logic import (
    ALERT_AND_NONCONFORMANCE_HANDLING,
    CONTROL_CONCENTRATED_ON_ONE_HOLDER,
    DEFAULT_ORGANIZATION_POLICY,
    DERATING_AND_APPLICATION_REVIEW,
    EVALUATION_AND_QUALIFICATION_ROUTE,
    FUNCTION_COVERAGE_SHORT,
    OBSOLESCENCE_AND_AVAILABILITY,
    ORGANIZATION_MEETS_CLASS_ONE,
    ORGANIZATION_NOT_AGREED,
    ORGANIZATION_NOT_ESTABLISHED,
    ORGANIZATION_NOT_INDEPENDENT,
    PART_SELECTION_AND_DECLARED_LISTS,
    PROCUREMENT_AND_SOURCE_SURVEILLANCE,
    PRODUCT_ASSURANCE_MANAGER,
    RADIATION_HARDNESS_ASSURANCE,
    REPORTING_LINE_NOT_ACCEPTED,
    REQUIRED_CONTROL_FUNCTIONS,
    SCREENING_AND_LOT_ACCEPTANCE,
    assess_parts_control_organization,
    effort_weighted_staffing,
    function_coverage,
    function_is_covered,
    holder_function_load,
    marginal_effort_advisories,
    peak_holder_share,
    under_resourced_functions,
    unassigned_functions,
    validate_assignment_record,
    validate_assignments,
    validate_organization_identity,
    validate_organization_policy,
    weakest_covered_function,
)

EFFORTS = {
    PART_SELECTION_AND_DECLARED_LISTS: 0.40,
    PROCUREMENT_AND_SOURCE_SURVEILLANCE: 0.30,
    EVALUATION_AND_QUALIFICATION_ROUTE: 0.35,
    SCREENING_AND_LOT_ACCEPTANCE: 0.25,
    DERATING_AND_APPLICATION_REVIEW: 0.20,
    RADIATION_HARDNESS_ASSURANCE: 0.45,
    OBSOLESCENCE_AND_AVAILABILITY: 0.18,
    ALERT_AND_NONCONFORMANCE_HANDLING: 0.30,
}

HOLDERS = {
    PART_SELECTION_AND_DECLARED_LISTS: "parts-engineer-a",
    PROCUREMENT_AND_SOURCE_SURVEILLANCE: "procurement-quality-b",
    EVALUATION_AND_QUALIFICATION_ROUTE: "evaluation-engineer-c",
    SCREENING_AND_LOT_ACCEPTANCE: "evaluation-engineer-c",
    DERATING_AND_APPLICATION_REVIEW: "reliability-engineer-d",
    RADIATION_HARDNESS_ASSURANCE: "radiation-engineer-e",
    OBSOLESCENCE_AND_AVAILABILITY: "parts-engineer-a",
    ALERT_AND_NONCONFORMANCE_HANDLING: "quality-engineer-f",
}


def _policy(**overrides):
    policy = dict(DEFAULT_ORGANIZATION_POLICY)
    policy.update(overrides)
    return policy


def _assignments(efforts=None, holders=None, qualified=None, drop=()):
    effort_map = dict(EFFORTS)
    effort_map.update(efforts or {})
    holder_map = dict(HOLDERS)
    holder_map.update(holders or {})
    qualified_map = qualified or {}
    return [
        {
            "function": name,
            "holder": holder_map[name],
            "allocated_effort": effort_map[name],
            "holder_qualified": qualified_map.get(name, True),
        }
        for name in REQUIRED_CONTROL_FUNCTIONS
        if name not in drop
    ]


def _organization(**overrides):
    organization = {
        "unit_name": "electronic-parts-control-unit",
        "accountable_lead": "parts-control-lead-g",
        "appointment_reference": "PA-APPT-0117",
        "reports_to": PRODUCT_ASSURANCE_MANAGER,
        "independent_of_design_authority": True,
        "agreed_with_customer": True,
        "assignments": _assignments(),
    }
    organization.update(overrides)
    return organization


def _case(**overrides):
    case = {"organization": _organization()}
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
            validate_organization_policy(_policy(min_function_coverage=1.4))

    def test_non_positive_effort_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(_policy(min_function_effort=0.0))

    def test_effort_floor_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(_policy(min_function_effort=1.6))

    def test_holder_share_cap_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(_policy(max_holder_function_share=1.2))

    def test_marginal_band_wider_than_the_effort_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(
                _policy(min_function_effort=0.1, marginal_effort_band=0.3)
            )

    def test_empty_reporting_line_list_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(_policy(accepted_reporting_lines=()))

    def test_non_boolean_independence_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(
                _policy(require_design_independence="sometimes")
            )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_policy(["min_function_coverage"])


class IdentityTests(unittest.TestCase):
    def test_identity_reads_back(self):
        identity = validate_organization_identity(_organization())
        self.assertEqual(identity["unit_name"], "electronic-parts-control-unit")
        self.assertEqual(identity["reports_to"], PRODUCT_ASSURANCE_MANAGER)

    def test_non_string_unit_name_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_identity(_organization(unit_name=17))

    def test_non_boolean_customer_agreement_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_identity(_organization(agreed_with_customer="yes"))

    def test_non_mapping_organization_refused(self):
        with self.assertRaises(ValueError):
            validate_organization_identity("electronic-parts-control-unit")


class AssignmentTests(unittest.TestCase):
    def test_assignment_reads_back(self):
        record = validate_assignment_record(
            {
                "function": RADIATION_HARDNESS_ASSURANCE,
                "holder": "radiation-engineer-e",
                "allocated_effort": 0.45,
                "holder_qualified": True,
            }
        )
        self.assertEqual(record["function"], RADIATION_HARDNESS_ASSURANCE)
        self.assertAlmostEqual(record["allocated_effort"], 0.45, places=9)

    def test_unrecognised_function_refused(self):
        with self.assertRaises(ValueError):
            validate_assignment_record(
                {
                    "function": "canteen-rota",
                    "holder": "parts-engineer-a",
                    "allocated_effort": 0.2,
                    "holder_qualified": True,
                }
            )

    def test_effort_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_assignment_record(
                {
                    "function": SCREENING_AND_LOT_ACCEPTANCE,
                    "holder": "parts-engineer-a",
                    "allocated_effort": 1.3,
                    "holder_qualified": True,
                }
            )

    def test_duplicate_function_refused(self):
        assignments = _assignments()
        assignments.append(dict(assignments[0]))
        with self.assertRaises(ValueError):
            validate_assignments(assignments)

    def test_non_sequence_assignments_refused(self):
        with self.assertRaises(ValueError):
            validate_assignments({"function": SCREENING_AND_LOT_ACCEPTANCE})


class CoverageTests(unittest.TestCase):
    def test_a_complete_organization_covers_every_function(self):
        self.assertAlmostEqual(function_coverage(_assignments()), 1.0, places=9)

    def test_a_blank_holder_leaves_the_function_uncovered(self):
        record = {
            "function": DERATING_AND_APPLICATION_REVIEW,
            "holder": "   ",
            "allocated_effort": 0.4,
            "holder_qualified": True,
        }
        self.assertFalse(function_is_covered(record))

    def test_an_unqualified_holder_leaves_the_function_uncovered(self):
        assignments = _assignments(qualified={RADIATION_HARDNESS_ASSURANCE: False})
        self.assertIn(
            RADIATION_HARDNESS_ASSURANCE, under_resourced_functions(assignments)
        )

    def test_effort_exactly_on_the_floor_still_covers(self):
        record = {
            "function": OBSOLESCENCE_AND_AVAILABILITY,
            "holder": "parts-engineer-a",
            "allocated_effort": 0.1,
            "holder_qualified": True,
        }
        self.assertTrue(function_is_covered(record))

    def test_a_dropped_function_is_reported_unassigned(self):
        assignments = _assignments(drop=(ALERT_AND_NONCONFORMANCE_HANDLING,))
        self.assertEqual(
            unassigned_functions(assignments), (ALERT_AND_NONCONFORMANCE_HANDLING,)
        )

    def test_deleting_a_thin_function_cannot_raise_the_staffing(self):
        full = effort_weighted_staffing(_assignments())
        trimmed = effort_weighted_staffing(
            _assignments(drop=(OBSOLESCENCE_AND_AVAILABILITY,))
        )
        self.assertLess(trimmed, full)

    def test_staffing_averages_over_the_full_required_list(self):
        expected = sum(EFFORTS.values()) / len(REQUIRED_CONTROL_FUNCTIONS)
        self.assertAlmostEqual(
            effort_weighted_staffing(_assignments()), expected, places=9
        )

    def test_the_weakest_covered_function_is_named(self):
        weakest = weakest_covered_function(_assignments())
        self.assertEqual(weakest["function"], OBSOLESCENCE_AND_AVAILABILITY)


class ConcentrationTests(unittest.TestCase):
    def test_holder_load_counts_every_function_held(self):
        load = holder_function_load(_assignments())
        self.assertEqual(load["parts-engineer-a"], 2)
        self.assertEqual(load["evaluation-engineer-c"], 2)

    def test_peak_share_is_the_most_loaded_holder(self):
        peak, share = peak_holder_share(_assignments())
        self.assertIn(peak, ("evaluation-engineer-c", "parts-engineer-a"))
        self.assertAlmostEqual(share, 0.25, places=9)

    def test_one_holder_carrying_everything_reaches_a_full_share(self):
        holders = {name: "one-engineer" for name in REQUIRED_CONTROL_FUNCTIONS}
        peak, share = peak_holder_share(_assignments(holders=holders))
        self.assertEqual(peak, "one-engineer")
        self.assertAlmostEqual(share, 1.0, places=9)

    def test_no_named_holder_gives_an_empty_peak(self):
        holders = {name: "" for name in REQUIRED_CONTROL_FUNCTIONS}
        peak, share = peak_holder_share(_assignments(holders=holders))
        self.assertIsNone(peak)
        self.assertAlmostEqual(share, 0.0, places=9)


class AdvisoryTests(unittest.TestCase):
    def test_a_function_just_over_the_floor_is_advised_on(self):
        assignments = _assignments(efforts={OBSOLESCENCE_AND_AVAILABILITY: 0.12})
        advisories = marginal_effort_advisories(
            assignments, _policy(min_function_effort=0.1, marginal_effort_band=0.05)
        )
        self.assertEqual(len(advisories), 1)
        self.assertIn(OBSOLESCENCE_AND_AVAILABILITY, advisories[0])

    def test_a_comfortable_organization_raises_no_advisory(self):
        self.assertEqual(marginal_effort_advisories(_assignments()), ())


class VerdictTests(unittest.TestCase):
    def test_a_complete_organization_meets_the_class(self):
        result = assess_parts_control_organization(_case())
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_ONE)
        self.assertAlmostEqual(result["function_coverage"], 1.0, places=9)

    def test_an_absent_organization_is_not_established(self):
        result = assess_parts_control_organization({"organization": None})
        self.assertEqual(result["verdict"], ORGANIZATION_NOT_ESTABLISHED)

    def test_a_unit_with_no_appointment_is_not_established(self):
        result = assess_parts_control_organization(
            _case(organization=_organization(appointment_reference="  "))
        )
        self.assertEqual(result["verdict"], ORGANIZATION_NOT_ESTABLISHED)

    def test_a_missing_function_shortens_the_coverage(self):
        assignments = _assignments(drop=(RADIATION_HARDNESS_ASSURANCE,))
        result = assess_parts_control_organization(
            _case(organization=_organization(assignments=assignments))
        )
        self.assertEqual(result["verdict"], FUNCTION_COVERAGE_SHORT)
        self.assertEqual(
            result["unassigned_functions"], (RADIATION_HARDNESS_ASSURANCE,)
        )

    def test_a_reporting_line_into_the_project_is_refused(self):
        result = assess_parts_control_organization(
            _case(organization=_organization(reports_to="project-manager"))
        )
        self.assertEqual(result["verdict"], REPORTING_LINE_NOT_ACCEPTED)

    def test_a_unit_inside_the_design_authority_is_refused(self):
        result = assess_parts_control_organization(
            _case(
                organization=_organization(independent_of_design_authority=False)
            )
        )
        self.assertEqual(result["verdict"], ORGANIZATION_NOT_INDEPENDENT)

    def test_control_on_one_holder_is_refused(self):
        holders = {name: "one-engineer" for name in REQUIRED_CONTROL_FUNCTIONS}
        result = assess_parts_control_organization(
            _case(organization=_organization(assignments=_assignments(holders=holders)))
        )
        self.assertEqual(result["verdict"], CONTROL_CONCENTRATED_ON_ONE_HOLDER)
        self.assertEqual(result["peak_holder"], "one-engineer")

    def test_a_share_exactly_on_the_cap_is_admissible(self):
        holders = dict(HOLDERS)
        for name in (
            PART_SELECTION_AND_DECLARED_LISTS,
            PROCUREMENT_AND_SOURCE_SURVEILLANCE,
            EVALUATION_AND_QUALIFICATION_ROUTE,
            SCREENING_AND_LOT_ACCEPTANCE,
        ):
            holders[name] = "half-loaded-engineer"
        result = assess_parts_control_organization(
            _case(organization=_organization(assignments=_assignments(holders=holders)))
        )
        self.assertAlmostEqual(result["peak_holder_share"], 0.5, places=9)
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_ONE)

    def test_an_unagreed_organization_is_refused(self):
        result = assess_parts_control_organization(
            _case(organization=_organization(agreed_with_customer=False))
        )
        self.assertEqual(result["verdict"], ORGANIZATION_NOT_AGREED)

    def test_advisories_travel_with_a_passing_verdict(self):
        assignments = _assignments(efforts={OBSOLESCENCE_AND_AVAILABILITY: 0.12})
        result = assess_parts_control_organization(
            _case(organization=_organization(assignments=assignments)),
            _policy(min_function_effort=0.1, marginal_effort_band=0.05),
        )
        self.assertEqual(result["verdict"], ORGANIZATION_MEETS_CLASS_ONE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_an_organization_with_no_assignments_sequence_refused(self):
        organization = _organization()
        del organization["assignments"]
        with self.assertRaises(ValueError):
            assess_parts_control_organization(_case(organization=organization))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_parts_control_organization(["organization"])


if __name__ == "__main__":
    unittest.main()
