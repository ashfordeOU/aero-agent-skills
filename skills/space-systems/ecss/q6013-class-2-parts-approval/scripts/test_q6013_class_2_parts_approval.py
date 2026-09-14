"""Contract tests for the clause 5.2.4 class 2 part-approval logic."""

import unittest

from q6013_class_2_parts_approval_logic import (
    APPROVAL_ROUTES,
    ESCALATION_DRIVERS,
    REQUIRED_JUSTIFICATION_ELEMENTS,
    SCORE_TOLERANCE,
    assess_parts_approval,
    dispose_justification,
    justification_scores,
    required_route,
    route_rank,
    validate_approval_policy,
    validate_approval_record,
    validate_citation,
    validate_justification_element,
    validity_state,
)

POLICY = {
    "covered_floor": 0.8,
    "completeness_floor": 0.7,
    "reference_credit": 0.6,
    "marginal_band": 0.05,
}

RECORD = {
    "reference": "PAR-6013-221",
    "issue": "issue 2",
    "approver_role": "parts-control-board",
    "declared_route": "parts-control-board-approval",
    "approval_position": 3,
    "first_commitment_position": 7,
    "validity_months": 24,
    "age_months": 9,
}


def _justification(**overrides):
    elements = {
        name: {"name": name, "rationale": "recorded at the approval review"}
        for name in REQUIRED_JUSTIFICATION_ELEMENTS
    }
    elements.update(overrides)
    return [elements[name] for name in REQUIRED_JUSTIFICATION_ELEMENTS
            if elements.get(name) is not None]


def _case(**overrides):
    case = {
        "policy": dict(POLICY),
        "record": dict(RECORD),
        "escalation_drivers": ["no-approved-equivalent-on-the-project"],
        "justification": _justification(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_valid_policy_returned_as_floats(self):
        policy = validate_approval_policy(dict(POLICY))
        self.assertAlmostEqual(policy["covered_floor"], 0.8, places=9)
        self.assertAlmostEqual(policy["reference_credit"], 0.6, places=9)

    def test_completeness_floor_above_covered_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval_policy(dict(POLICY, completeness_floor=0.9))

    def test_full_reference_credit_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval_policy(dict(POLICY, reference_credit=1.0))

    def test_zero_reference_credit_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval_policy(dict(POLICY, reference_credit=0.0))

    def test_band_wider_than_the_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval_policy(dict(POLICY, marginal_band=0.9))

    def test_floor_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval_policy(dict(POLICY, covered_floor=1.4))

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval_policy("covered_floor 0.8")


class RecordTests(unittest.TestCase):
    def test_record_returned_normalized(self):
        record = validate_approval_record(
            dict(RECORD, declared_route="Parts Control Board Approval")
        )
        self.assertEqual(record["declared_route"], "parts-control-board-approval")

    def test_blank_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval_record(dict(RECORD, reference="  "))

    def test_missing_issue_rejected(self):
        bad = dict(RECORD)
        del bad["issue"]
        with self.assertRaises(ValueError):
            validate_approval_record(bad)

    def test_approver_outside_the_permitted_roles_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval_record(dict(RECORD, approver_role="the buyer"))

    def test_unrecognized_route_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval_record(dict(RECORD, declared_route="verbal-agreement"))

    def test_zero_validity_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval_record(dict(RECORD, validity_months=0))

    def test_negative_position_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval_record(dict(RECORD, approval_position=-1))

    def test_boolean_position_rejected(self):
        with self.assertRaises(ValueError):
            validate_approval_record(dict(RECORD, approval_position=True))


class CitationTests(unittest.TestCase):
    def test_citation_returned_stripped(self):
        citation = validate_citation({"document": " PA-PLAN-2 ", "issue": "issue 4"})
        self.assertEqual(citation["document"], "PA-PLAN-2")

    def test_citation_without_issue_rejected(self):
        with self.assertRaises(ValueError):
            validate_citation({"document": "PA-PLAN-2"})

    def test_citation_with_blank_document_rejected(self):
        with self.assertRaises(ValueError):
            validate_citation({"document": "   ", "issue": "issue 4"})


class RouteTests(unittest.TestCase):
    def test_route_rank_orders_the_ladder(self):
        ranks = [route_rank(name) for name in APPROVAL_ROUTES]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(len(set(ranks)), len(APPROVAL_ROUTES))

    def test_no_driver_leaves_the_delegated_route(self):
        demanded = required_route([])
        self.assertEqual(demanded["route"], "component-engineer-approval")
        self.assertEqual(demanded["raised_by"], [])

    def test_board_driver_raises_to_the_board_route(self):
        demanded = required_route(["obsolete-at-the-order-date"])
        self.assertEqual(demanded["route"], "parts-control-board-approval")

    def test_customer_driver_wins_over_a_board_driver(self):
        demanded = required_route(
            ["obsolete-at-the-order-date", "single-point-failure-function"]
        )
        self.assertEqual(demanded["route"], "customer-agreed-approval")
        self.assertEqual(demanded["raised_by"], ["single-point-failure-function"])

    def test_repeated_driver_rejected(self):
        with self.assertRaises(ValueError):
            required_route(["no-published-radiation-data",
                            "no-published-radiation-data"])

    def test_unknown_driver_rejected(self):
        with self.assertRaises(ValueError):
            required_route(["the-buyer-liked-the-price"])

    def test_every_driver_names_a_real_route(self):
        for driver, route in ESCALATION_DRIVERS.items():
            self.assertIn(route, APPROVAL_ROUTES, driver)

    def test_unknown_route_rank_rejected(self):
        with self.assertRaises(ValueError):
            route_rank("nodded-through")


class JustificationTests(unittest.TestCase):
    def test_written_element_scores_one(self):
        dispositions = dispose_justification(_justification(), POLICY)
        self.assertTrue(all(d["state"] == "written" for d in dispositions))
        self.assertAlmostEqual(justification_scores(dispositions)["completeness"],
                               1.0, places=9)

    def test_referenced_element_is_credited_below_one(self):
        elements = _justification(**{
            "compensating-measures": {
                "name": "compensating-measures",
                "citation": {"document": "SCREEN-FLOW-9", "issue": "issue 1"},
            }
        })
        dispositions = dispose_justification(elements, POLICY)
        credited = [d for d in dispositions if d["name"] == "compensating-measures"][0]
        self.assertEqual(credited["state"], "carried-by-reference")
        self.assertAlmostEqual(credited["weight"], 0.6, places=9)
        self.assertTrue(credited["treated"])

    def test_heading_with_no_rationale_is_not_treated(self):
        elements = _justification(**{
            "residual-risk-statement": {"name": "residual-risk-statement",
                                        "rationale": "   "}
        })
        dispositions = dispose_justification(elements, POLICY)
        heading = [d for d in dispositions
                   if d["name"] == "residual-risk-statement"][0]
        self.assertEqual(heading["state"], "stated-without-a-rationale")
        self.assertFalse(heading["treated"])

    def test_absent_element_still_occupies_the_denominator(self):
        elements = _justification(**{"alternatives-examined": None})
        dispositions = dispose_justification(elements, POLICY)
        self.assertEqual(len(dispositions), len(REQUIRED_JUSTIFICATION_ELEMENTS))
        scores = justification_scores(dispositions)
        self.assertAlmostEqual(scores["covered_share"], 0.8, places=9)

    def test_element_with_both_bases_rejected(self):
        with self.assertRaises(ValueError):
            validate_justification_element({
                "name": "need-statement",
                "rationale": "needed for the receiver chain",
                "citation": {"document": "D-1", "issue": "issue 1"},
            })

    def test_unrecognized_element_rejected(self):
        with self.assertRaises(ValueError):
            validate_justification_element({"name": "price-comparison",
                                            "rationale": "cheaper"})

    def test_duplicate_element_rejected(self):
        elements = _justification()
        elements.append({"name": "need-statement", "rationale": "again"})
        with self.assertRaises(ValueError):
            dispose_justification(elements, POLICY)

    def test_non_string_rationale_rejected(self):
        with self.assertRaises(ValueError):
            validate_justification_element({"name": "need-statement", "rationale": 7})

    def test_empty_disposition_list_rejected(self):
        with self.assertRaises(ValueError):
            justification_scores([])


class ValidityTests(unittest.TestCase):
    def test_approval_inside_its_validity(self):
        state = validity_state(dict(RECORD))
        self.assertFalse(state["lapsed"])
        self.assertEqual(state["remaining_months"], 15)

    def test_approval_exactly_at_its_validity_is_not_lapsed(self):
        state = validity_state(dict(RECORD, age_months=24))
        self.assertFalse(state["lapsed"])
        self.assertEqual(state["remaining_months"], 0)

    def test_approval_past_its_validity_is_lapsed(self):
        self.assertTrue(validity_state(dict(RECORD, age_months=25))["lapsed"])

    def test_missing_age_rejected(self):
        bad = dict(RECORD)
        del bad["age_months"]
        with self.assertRaises(ValueError):
            validity_state(bad)


class AssessmentTests(unittest.TestCase):
    def test_complete_case_is_approved(self):
        result = assess_parts_approval(_case())
        self.assertEqual(result["verdict"], "part approved for class 2 use")
        self.assertTrue(result["approved"])
        self.assertEqual(result["findings"], [])

    def test_missing_record_closes_on_approval_not_established(self):
        result = assess_parts_approval(_case(record=None))
        self.assertEqual(result["verdict"], "approval not established")
        self.assertFalse(result["approved"])

    def test_route_below_the_demanded_level_is_the_verdict(self):
        result = assess_parts_approval(
            _case(escalation_drivers=["single-point-failure-function"])
        )
        self.assertEqual(result["verdict"], "approval route below the required level")
        self.assertTrue(any("demand" in f for f in result["findings"]))

    def test_route_above_the_demanded_level_is_an_advisory_not_a_finding(self):
        result = assess_parts_approval(
            _case(record=dict(RECORD, declared_route="customer-agreed-approval"))
        )
        self.assertTrue(result["approved"])
        self.assertTrue(any("above" in a for a in result["advisories"]))

    def test_lapsed_approval_closes_on_lapsed(self):
        result = assess_parts_approval(_case(record=dict(RECORD, age_months=40)))
        self.assertEqual(result["verdict"], "approval lapsed")

    def test_approval_after_the_commitment_closes_on_timing(self):
        result = assess_parts_approval(
            _case(record=dict(RECORD, approval_position=9,
                              first_commitment_position=4))
        )
        self.assertEqual(result["verdict"],
                         "approval recorded after the procurement commitment")

    def test_approval_on_the_commitment_position_is_in_time(self):
        result = assess_parts_approval(
            _case(record=dict(RECORD, approval_position=7,
                              first_commitment_position=7))
        )
        self.assertTrue(result["approved"])

    def test_absent_element_shortens_the_record(self):
        result = assess_parts_approval(
            _case(justification=_justification(**{"residual-risk-statement": None}))
        )
        self.assertEqual(result["verdict"],
                         "justification record short of the required content")
        self.assertEqual(result["absent_elements"], ["residual-risk-statement"])

    def test_record_of_pure_pointers_falls_below_the_completeness_floor(self):
        elements = [
            {"name": name, "citation": {"document": "PA-PLAN-2", "issue": "issue 4"}}
            for name in REQUIRED_JUSTIFICATION_ELEMENTS
        ]
        result = assess_parts_approval(_case(justification=elements))
        self.assertAlmostEqual(result["scores"]["covered_share"], 1.0, places=9)
        self.assertAlmostEqual(result["scores"]["completeness"], 0.6, places=9)
        self.assertEqual(result["verdict"],
                         "justification record short of the required content")

    def test_completeness_exactly_on_its_floor_passes(self):
        policy = dict(POLICY, completeness_floor=0.6, covered_floor=0.6,
                      marginal_band=0.05)
        elements = [
            {"name": name, "citation": {"document": "PA-PLAN-2", "issue": "issue 4"}}
            for name in REQUIRED_JUSTIFICATION_ELEMENTS
        ]
        result = assess_parts_approval(_case(policy=policy, justification=elements))
        self.assertAlmostEqual(result["scores"]["completeness"],
                               policy["completeness_floor"], places=9)
        self.assertTrue(result["approved"])

    def test_marginal_completeness_raises_an_advisory(self):
        policy = dict(POLICY, completeness_floor=0.58, covered_floor=0.58,
                      marginal_band=0.05)
        elements = [
            {"name": name, "citation": {"document": "PA-PLAN-2", "issue": "issue 4"}}
            for name in REQUIRED_JUSTIFICATION_ELEMENTS
        ]
        result = assess_parts_approval(_case(policy=policy, justification=elements))
        self.assertTrue(any("marginal band" in a for a in result["advisories"]))

    def test_heading_only_element_is_named_in_its_own_list(self):
        elements = _justification(**{
            "approval-validity-scope": {"name": "approval-validity-scope",
                                        "rationale": ""}
        })
        result = assess_parts_approval(_case(justification=elements))
        self.assertEqual(result["heading_only_elements"], ["approval-validity-scope"])

    def test_every_finding_is_named_not_only_the_first(self):
        elements = _justification(**{"residual-risk-statement": None,
                                     "alternatives-examined": None,
                                     "compensating-measures": None})
        result = assess_parts_approval(
            _case(justification=elements,
                  record=dict(RECORD, approval_position=9,
                              first_commitment_position=2, age_months=40))
        )
        self.assertGreaterEqual(len(result["findings"]), 6)

    def test_missing_case_key_rejected(self):
        case = _case()
        del case["justification"]
        with self.assertRaises(ValueError):
            assess_parts_approval(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_approval(["policy"])

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(SCORE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
