#!/usr/bin/env python3
"""Contract test for the class 3 ASIC referral and its tailoring (offline)."""

import copy
import unittest

from q60_class_3_asic_requirements_logic import (
    ACTIVITY_WEIGHT,
    APPROVAL_AUTHORITIES,
    APPROVAL_AUTHORITY_INSUFFICIENT,
    ASIC_CATEGORIES,
    BASE_ACTIVITIES,
    CORE_ACTIVITIES,
    CRITICALITY_RISK_LIMIT,
    DEFAULT_TAILORING_POLICY,
    DELTA_DEVELOPMENT,
    FULL_DEVELOPMENT,
    FUNCTION_CRITICALITIES,
    HERITAGE_EVIDENCE_INSUFFICIENT,
    RESIDUAL_RISK_ABOVE_LIMIT,
    REVIEWED_REUSE,
    TAILORING_ACCEPTED,
    WAIVER_AUTHORITY,
    WAIVER_JUSTIFICATION_MISSING,
    WAIVER_ON_CORE_ACTIVITY,
    activity_plan,
    assess_asic_tailoring,
    authority_rank,
    environment_severity_ratio,
    granted_waivers,
    heritage_is_sufficient,
    residual_risk_index,
    route_development,
    tailored_plan,
    validate_heritage_record,
    validate_tailoring_policy,
    validate_waiver,
    validate_waivers,
    waivable_activities,
    waiver_findings,
)

HERITAGE = {
    "part_number": "ASIC-C3-441",
    "units_flown": 9,
    "cumulative_flight_hours": 14000,
    "referenced_environment_severity": 1.0,
    "candidate_environment_severity": 1.0,
    "design_modified": False,
}

WAIVERS = [
    {
        "activity": "design-rule-verification",
        "approved_by": "product-assurance-manager",
        "justification_reference": "JUS-014",
        "compensating_measure": "supplier design rule report reviewed in house",
    }
]


def _heritage(**overrides):
    record = copy.deepcopy(HERITAGE)
    record.update(overrides)
    return record


def _case(**overrides):
    case = {
        "part_number": "ASIC-C3-441",
        "category": "gate-array",
        "function_criticality": "mission-critical",
        "declared_route": "reuse",
        "heritage": _heritage(),
        "waivers": copy.deepcopy(WAIVERS),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_is_returned_when_omitted(self):
        self.assertEqual(validate_tailoring_policy(), DEFAULT_TAILORING_POLICY)

    def test_unknown_policy_key_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_tailoring_policy({"minimum_lot_size": 10})

    def test_negative_unit_floor_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_tailoring_policy({"minimum_units_flown": -1})

    def test_policy_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_tailoring_policy("default")


class AuthorityTests(unittest.TestCase):
    def test_customer_authority_is_the_highest(self):
        self.assertEqual(authority_rank("customer-authority"), 1)

    def test_project_authority_is_the_lowest(self):
        self.assertEqual(authority_rank("project-authority"), len(APPROVAL_AUTHORITIES))

    def test_unknown_authority_is_rejected(self):
        with self.assertRaises(ValueError):
            authority_rank("design-office")

    def test_every_waivable_activity_names_an_authority(self):
        for activity, authority in WAIVER_AUTHORITY.items():
            self.assertIn(activity, ACTIVITY_WEIGHT)
            self.assertIn(authority, APPROVAL_AUTHORITIES)

    def test_no_core_activity_appears_in_the_waiver_authority_table(self):
        for activity in CORE_ACTIVITIES:
            self.assertNotIn(activity, WAIVER_AUTHORITY)


class HeritageTests(unittest.TestCase):
    def test_complete_record_validates(self):
        record = validate_heritage_record(HERITAGE)
        self.assertEqual(record["units_flown"], 9)

    def test_negative_units_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_heritage_record(_heritage(units_flown=-2))

    def test_zero_environment_severity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_heritage_record(_heritage(referenced_environment_severity=0))

    def test_non_boolean_design_modified_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_heritage_record(_heritage(design_modified="no"))

    def test_equal_environments_give_a_unit_ratio(self):
        self.assertAlmostEqual(environment_severity_ratio(HERITAGE), 1.0, places=9)

    def test_harsher_candidate_environment_raises_the_ratio(self):
        ratio = environment_severity_ratio(
            _heritage(candidate_environment_severity=1.6)
        )
        self.assertAlmostEqual(ratio, 1.6, places=9)

    def test_heritage_above_both_floors_is_sufficient(self):
        self.assertTrue(heritage_is_sufficient(HERITAGE))

    def test_heritage_exactly_on_both_floors_is_sufficient(self):
        record = _heritage(
            units_flown=DEFAULT_TAILORING_POLICY["minimum_units_flown"],
            cumulative_flight_hours=DEFAULT_TAILORING_POLICY["minimum_flight_hours"],
        )
        self.assertTrue(heritage_is_sufficient(record))

    def test_too_few_units_is_not_sufficient(self):
        self.assertFalse(heritage_is_sufficient(_heritage(units_flown=1)))

    def test_too_few_hours_is_not_sufficient(self):
        self.assertFalse(
            heritage_is_sufficient(_heritage(cumulative_flight_hours=120))
        )


class PlanTests(unittest.TestCase):
    def test_every_category_extends_the_base_plan(self):
        for category in ASIC_CATEGORIES:
            plan = activity_plan(category, FULL_DEVELOPMENT)
            for activity in BASE_ACTIVITIES:
                self.assertIn(activity, plan)

    def test_mixed_signal_adds_analogue_characterisation(self):
        self.assertIn(
            "analogue-characterisation", activity_plan("mixed-signal", FULL_DEVELOPMENT)
        )

    def test_reviewed_reuse_keeps_only_the_core_activities(self):
        plan = activity_plan("gate-array", REVIEWED_REUSE)
        self.assertEqual(set(plan), set(CORE_ACTIVITIES))

    def test_unknown_category_is_rejected(self):
        with self.assertRaises(ValueError):
            activity_plan("discrete-transistor", FULL_DEVELOPMENT)

    def test_unknown_flow_is_rejected(self):
        with self.assertRaises(ValueError):
            activity_plan("gate-array", "partial-flow")

    def test_no_core_activity_is_waivable(self):
        for activity in waivable_activities("system-on-chip", FULL_DEVELOPMENT):
            self.assertNotIn(activity, CORE_ACTIVITIES)

    def test_reviewed_reuse_has_nothing_left_to_waive(self):
        self.assertEqual(waivable_activities("gate-array", REVIEWED_REUSE), ())

    def test_every_activity_carries_a_weight(self):
        for category in ASIC_CATEGORIES:
            for activity in activity_plan(category, FULL_DEVELOPMENT):
                self.assertIn(activity, ACTIVITY_WEIGHT)


class RoutingTests(unittest.TestCase):
    def test_new_development_goes_straight_to_the_full_flow(self):
        routing = route_development(
            {"declared_route": "new-development", "heritage": None}
        )
        self.assertEqual(routing["flow"], FULL_DEVELOPMENT)

    def test_unknown_declared_route_is_rejected(self):
        with self.assertRaises(ValueError):
            route_development({"declared_route": "partial-reuse"})

    def test_reuse_without_a_heritage_record_is_rejected(self):
        with self.assertRaises(ValueError):
            route_development({"declared_route": "reuse"})

    def test_thin_heritage_sends_a_reuse_claim_to_the_full_flow(self):
        routing = route_development(
            {"declared_route": "reuse", "heritage": _heritage(units_flown=1)}
        )
        self.assertEqual(routing["flow"], FULL_DEVELOPMENT)
        self.assertEqual(routing["reason"], HERITAGE_EVIDENCE_INSUFFICIENT)

    def test_a_modified_design_routes_to_the_delta_flow(self):
        routing = route_development(
            {"declared_route": "reuse", "heritage": _heritage(design_modified=True)}
        )
        self.assertEqual(routing["flow"], DELTA_DEVELOPMENT)

    def test_a_harsher_environment_routes_to_the_delta_flow(self):
        routing = route_development(
            {
                "declared_route": "reuse",
                "heritage": _heritage(candidate_environment_severity=1.4),
            }
        )
        self.assertEqual(routing["flow"], DELTA_DEVELOPMENT)

    def test_a_milder_environment_still_allows_a_reviewed_reuse(self):
        routing = route_development(
            {
                "declared_route": "reuse",
                "heritage": _heritage(candidate_environment_severity=0.7),
            }
        )
        self.assertEqual(routing["flow"], REVIEWED_REUSE)

    def test_matching_environments_allow_a_reviewed_reuse(self):
        routing = route_development({"declared_route": "reuse", "heritage": HERITAGE})
        self.assertEqual(routing["flow"], REVIEWED_REUSE)


class WaiverTests(unittest.TestCase):
    def test_unknown_activity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_waiver(
                {"activity": "coffee-break", "approved_by": "project-authority"}
            )

    def test_missing_justification_is_kept_as_none(self):
        record = validate_waiver(
            {"activity": "timing-verification", "approved_by": "project-authority"}
        )
        self.assertIsNone(record["justification_reference"])

    def test_blank_justification_is_kept_as_none(self):
        record = validate_waiver(
            {
                "activity": "timing-verification",
                "approved_by": "product-assurance-manager",
                "justification_reference": "   ",
                "compensating_measure": "none",
            }
        )
        self.assertIsNone(record["justification_reference"])

    def test_duplicate_waiver_on_one_activity_is_rejected(self):
        waivers = copy.deepcopy(WAIVERS) * 2
        with self.assertRaises(ValueError):
            validate_waivers(waivers)

    def test_waivers_of_wrong_type_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_waivers("design-rule-verification")

    def test_waiver_on_a_core_activity_is_a_finding(self):
        findings = waiver_findings(
            [
                {
                    "activity": "functional-simulation",
                    "approved_by": "customer-authority",
                    "justification_reference": "JUS-020",
                    "compensating_measure": "supplier simulation report",
                }
            ],
            "gate-array",
            FULL_DEVELOPMENT,
        )
        self.assertEqual(findings[0]["finding"], WAIVER_ON_CORE_ACTIVITY)

    def test_waiver_without_a_compensating_measure_is_a_finding(self):
        findings = waiver_findings(
            [
                {
                    "activity": "timing-verification",
                    "approved_by": "product-assurance-manager",
                    "justification_reference": "JUS-021",
                }
            ],
            "gate-array",
            FULL_DEVELOPMENT,
        )
        self.assertEqual(findings[0]["finding"], WAIVER_JUSTIFICATION_MISSING)

    def test_waiver_approved_too_low_down_is_a_finding(self):
        findings = waiver_findings(
            [
                {
                    "activity": "radiation-evaluation",
                    "approved_by": "project-authority",
                    "justification_reference": "JUS-022",
                    "compensating_measure": "similarity argument to a flown part",
                }
            ],
            "gate-array",
            FULL_DEVELOPMENT,
        )
        self.assertEqual(findings[0]["finding"], APPROVAL_AUTHORITY_INSUFFICIENT)
        self.assertEqual(findings[0]["required"], "customer-authority")

    def test_waiver_approved_above_the_needed_authority_is_accepted(self):
        findings = waiver_findings(
            [
                {
                    "activity": "timing-verification",
                    "approved_by": "customer-authority",
                    "justification_reference": "JUS-023",
                    "compensating_measure": "static timing report from the foundry",
                }
            ],
            "gate-array",
            FULL_DEVELOPMENT,
        )
        self.assertEqual(findings, ())

    def test_waiver_on_an_activity_the_plan_never_carried_is_ignored(self):
        findings = waiver_findings(
            [
                {
                    "activity": "analogue-characterisation",
                    "approved_by": "project-authority",
                    "justification_reference": "JUS-024",
                    "compensating_measure": "not applicable to a digital array",
                }
            ],
            "gate-array",
            FULL_DEVELOPMENT,
        )
        self.assertEqual(findings, ())

    def test_a_blocked_waiver_is_not_granted(self):
        waivers = [
            {
                "activity": "radiation-evaluation",
                "approved_by": "project-authority",
                "justification_reference": "JUS-025",
                "compensating_measure": "similarity argument",
            }
        ]
        self.assertEqual(granted_waivers(waivers, "gate-array", FULL_DEVELOPMENT), ())

    def test_a_clean_waiver_is_granted_and_leaves_the_plan(self):
        plan = tailored_plan(WAIVERS, "gate-array", FULL_DEVELOPMENT)
        self.assertNotIn("design-rule-verification", plan)
        self.assertIn("functional-simulation", plan)


class RiskIndexTests(unittest.TestCase):
    def test_no_waiver_leaves_a_zero_index(self):
        self.assertAlmostEqual(
            residual_risk_index([], "gate-array", FULL_DEVELOPMENT), 0.0, places=9
        )

    def test_index_is_the_weighted_share_of_the_waivable_plan(self):
        waivable = waivable_activities("gate-array", FULL_DEVELOPMENT)
        total = sum(ACTIVITY_WEIGHT[name] for name in waivable)
        expected = ACTIVITY_WEIGHT["design-rule-verification"] / total
        self.assertAlmostEqual(
            residual_risk_index(WAIVERS, "gate-array", FULL_DEVELOPMENT),
            expected,
            places=9,
        )

    def test_a_flow_with_nothing_waivable_has_a_zero_index(self):
        self.assertAlmostEqual(
            residual_risk_index([], "gate-array", REVIEWED_REUSE), 0.0, places=9
        )

    def test_every_criticality_names_a_limit_between_zero_and_one(self):
        for criticality in FUNCTION_CRITICALITIES:
            limit = CRITICALITY_RISK_LIMIT[criticality]
            self.assertGreater(limit, 0.0)
            self.assertLess(limit, 1.0)

    def test_a_critical_function_may_give_up_less_than_a_non_critical_one(self):
        self.assertLess(
            CRITICALITY_RISK_LIMIT["mission-critical"],
            CRITICALITY_RISK_LIMIT["non-critical"],
        )


class AssessmentTests(unittest.TestCase):
    def test_clean_case_is_accepted(self):
        result = assess_asic_tailoring(_case(declared_route="new-development"))
        self.assertEqual(result["verdict"], TAILORING_ACCEPTED)
        self.assertTrue(result["acceptable"])

    def test_a_reviewed_reuse_carries_only_the_core_plan(self):
        result = assess_asic_tailoring(_case(waivers=[]))
        self.assertEqual(result["flow"], REVIEWED_REUSE)
        self.assertEqual(set(result["tailored_plan"]), set(CORE_ACTIVITIES))

    def test_thin_heritage_is_reported_as_a_finding(self):
        result = assess_asic_tailoring(
            _case(heritage=_heritage(units_flown=1), waivers=[])
        )
        self.assertEqual(result["verdict"], HERITAGE_EVIDENCE_INSUFFICIENT)
        self.assertEqual(result["flow"], FULL_DEVELOPMENT)

    def test_a_core_waiver_outranks_a_risk_index_finding(self):
        waivers = [
            {
                "activity": "design-data-archiving",
                "approved_by": "customer-authority",
                "justification_reference": "JUS-030",
                "compensating_measure": "supplier holds the database",
            },
            {
                "activity": "qualification-testing",
                "approved_by": "customer-authority",
                "justification_reference": "JUS-031",
                "compensating_measure": "flight lot data",
            },
        ]
        result = assess_asic_tailoring(
            _case(declared_route="new-development", waivers=waivers)
        )
        self.assertEqual(result["verdict"], WAIVER_ON_CORE_ACTIVITY)

    def test_too_much_tailoring_on_a_critical_function_is_over_the_limit(self):
        waivers = [
            {
                "activity": "design-rule-verification",
                "approved_by": "product-assurance-manager",
                "justification_reference": "JUS-040",
                "compensating_measure": "foundry sign off",
            },
            {
                "activity": "timing-verification",
                "approved_by": "product-assurance-manager",
                "justification_reference": "JUS-041",
                "compensating_measure": "margin from the synthesis report",
            },
            {
                "activity": "prototype-manufacturing",
                "approved_by": "project-authority",
                "justification_reference": "JUS-042",
                "compensating_measure": "emulation on a programmable carrier",
            },
        ]
        result = assess_asic_tailoring(
            _case(declared_route="new-development", waivers=waivers)
        )
        self.assertEqual(result["verdict"], RESIDUAL_RISK_ABOVE_LIMIT)
        self.assertGreater(
            result["residual_risk_index"], result["residual_risk_limit"]
        )

    def test_the_same_tailoring_passes_on_a_non_critical_function(self):
        waivers = [
            {
                "activity": "design-rule-verification",
                "approved_by": "product-assurance-manager",
                "justification_reference": "JUS-040",
                "compensating_measure": "foundry sign off",
            },
            {
                "activity": "timing-verification",
                "approved_by": "product-assurance-manager",
                "justification_reference": "JUS-041",
                "compensating_measure": "margin from the synthesis report",
            },
            {
                "activity": "prototype-manufacturing",
                "approved_by": "project-authority",
                "justification_reference": "JUS-042",
                "compensating_measure": "emulation on a programmable carrier",
            },
        ]
        result = assess_asic_tailoring(
            _case(
                declared_route="new-development",
                function_criticality="non-critical",
                waivers=waivers,
            )
        )
        self.assertEqual(result["verdict"], TAILORING_ACCEPTED)

    def test_unknown_criticality_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_asic_tailoring(_case(function_criticality="nice-to-have"))

    def test_case_missing_a_key_is_rejected(self):
        case = _case()
        del case["waivers"]
        with self.assertRaises(ValueError):
            assess_asic_tailoring(case)

    def test_case_of_wrong_type_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_asic_tailoring("ASIC-C3-441")

    def test_granted_waivers_are_exactly_the_plan_difference(self):
        result = assess_asic_tailoring(_case(declared_route="new-development"))
        removed = set(result["activity_plan"]) - set(result["tailored_plan"])
        self.assertEqual(removed, set(result["granted_waivers"]))


if __name__ == "__main__":
    unittest.main(verbosity=0)
