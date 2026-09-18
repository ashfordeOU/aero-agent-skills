#!/usr/bin/env python3
"""Contract test for the hybrid circuit type approval routes (offline)."""

import copy
import unittest

from q6005_circuit_type_approval_routes_logic import (
    ADMINISTRATIVE_ROUTE,
    CHANGE_CATEGORIES,
    DEFAULT_ROUTE_POLICY,
    DELTA_ROUTE,
    EXTENSION_ROUTE,
    NEW_DESIGN_ROUTE,
    PREDECESSOR_STATES,
    ROUTE_RANK,
    departure_score,
    envelope_critical_departures,
    evidence_obligations,
    lightest_route_reachable,
    plan_type_approval,
    route_for_score,
    route_without_change,
    select_approval_route,
    validate_change,
    validate_changes,
    validate_route_policy,
)

TRIM_ONLY = [{"category": "passive-trim-value"}]
LAYOUT_AND_TRIM = [
    {"category": "layout-topology"},
    {"category": "passive-trim-value"},
]
PACKAGE_AND_SUPPLIER = [
    {"category": "package-or-sealing"},
    {"category": "die-supplier"},
]
DIE_TECHNOLOGY = [{"category": "die-technology"}]

EXTENSION_CASE = {
    "predecessor_state": "approved-current",
    "changes": PACKAGE_AND_SUPPLIER,
}
NEW_DESIGN_CASE = {
    "predecessor_state": "none",
    "changes": [],
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_route_policy(DEFAULT_ROUTE_POLICY), DEFAULT_ROUTE_POLICY
        )

    def test_route_rank_orders_the_four_routes(self):
        self.assertEqual(
            sorted(ROUTE_RANK, key=ROUTE_RANK.get),
            [ADMINISTRATIVE_ROUTE, DELTA_ROUTE, EXTENSION_ROUTE, NEW_DESIGN_ROUTE],
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_route_policy("default")

    def test_policy_with_decreasing_thresholds_rejected(self):
        broken = dict(DEFAULT_ROUTE_POLICY, delta_max_score=20)
        with self.assertRaises(ValueError):
            validate_route_policy(broken)

    def test_policy_with_negative_threshold_rejected(self):
        broken = dict(DEFAULT_ROUTE_POLICY, delta_max_score=-1)
        with self.assertRaises(ValueError):
            validate_route_policy(broken)

    def test_policy_with_a_missing_threshold_rejected(self):
        broken = dict(DEFAULT_ROUTE_POLICY)
        del broken["extension_max_score"]
        with self.assertRaises(ValueError):
            validate_route_policy(broken)


class ChangeValidationTests(unittest.TestCase):
    def test_every_category_carries_a_weight_and_a_criticality_flag(self):
        for name, spec in CHANGE_CATEGORIES.items():
            self.assertIn("weight", spec, name)
            self.assertIn("envelope_critical", spec, name)

    def test_a_declared_change_is_normalized_with_its_weight(self):
        change = validate_change({"category": "die-supplier"})
        self.assertEqual(change["weight"], CHANGE_CATEGORIES["die-supplier"]["weight"])
        self.assertFalse(change["covered_by_predecessor"])

    def test_unknown_change_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_change({"category": "repainted-lid"})

    def test_non_mapping_change_rejected(self):
        with self.assertRaises(ValueError):
            validate_change("die-technology")

    def test_non_boolean_coverage_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_change({"category": "die-supplier", "covered_by_predecessor": "yes"})

    def test_coverage_claim_without_a_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_change(
                {"category": "die-supplier", "covered_by_predecessor": True}
            )

    def test_coverage_claim_with_a_reference_accepted(self):
        change = validate_change(
            {
                "category": "die-supplier",
                "covered_by_predecessor": True,
                "reference": "qualification report section 4",
            }
        )
        self.assertTrue(change["covered_by_predecessor"])

    def test_duplicate_declared_change_rejected(self):
        with self.assertRaises(ValueError):
            validate_changes(
                [{"category": "layout-topology"}, {"category": "layout-topology"}]
            )

    def test_non_list_change_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_changes({"category": "layout-topology"})


class DepartureScoreTests(unittest.TestCase):
    def test_empty_change_set_scores_zero(self):
        self.assertEqual(departure_score([]), 0)

    def test_score_sums_the_category_weights(self):
        self.assertEqual(
            departure_score(PACKAGE_AND_SUPPLIER),
            CHANGE_CATEGORIES["package-or-sealing"]["weight"]
            + CHANGE_CATEGORIES["die-supplier"]["weight"],
        )

    def test_a_covered_departure_contributes_nothing(self):
        covered = [
            {"category": "package-or-sealing"},
            {
                "category": "die-supplier",
                "covered_by_predecessor": True,
                "reference": "predecessor lot acceptance data",
            },
        ]
        self.assertEqual(
            departure_score(covered),
            CHANGE_CATEGORIES["package-or-sealing"]["weight"],
        )

    def test_documentation_only_change_scores_zero(self):
        self.assertEqual(departure_score([{"category": "documentation-only"}]), 0)

    def test_envelope_critical_departures_are_named(self):
        self.assertEqual(envelope_critical_departures(DIE_TECHNOLOGY), ["die-technology"])

    def test_a_covered_critical_departure_is_not_reported(self):
        covered = [
            {
                "category": "die-technology",
                "covered_by_predecessor": True,
                "reference": "extension qualification report",
            }
        ]
        self.assertEqual(envelope_critical_departures(covered), [])


class RouteForScoreTests(unittest.TestCase):
    def test_zero_score_takes_the_administrative_route(self):
        self.assertEqual(route_for_score(0), ADMINISTRATIVE_ROUTE)

    def test_small_score_takes_the_delta_route(self):
        self.assertEqual(route_for_score(4), DELTA_ROUTE)

    def test_moderate_score_takes_the_extension_route(self):
        self.assertEqual(route_for_score(14), EXTENSION_ROUTE)

    def test_large_score_takes_the_new_design_route(self):
        self.assertEqual(route_for_score(15), NEW_DESIGN_ROUTE)

    def test_negative_score_rejected(self):
        with self.assertRaises(ValueError):
            route_for_score(-1)

    def test_non_integer_score_rejected(self):
        with self.assertRaises(ValueError):
            route_for_score(4.5)


class RouteSelectionTests(unittest.TestCase):
    def test_no_predecessor_forces_the_new_design_route(self):
        result = select_approval_route("none", [])
        self.assertEqual(result["route"], NEW_DESIGN_ROUTE)
        self.assertTrue(any("no approved predecessor" in d for d in result["drivers"]))

    def test_lapsed_predecessor_forces_the_new_design_route(self):
        result = select_approval_route("approved-lapsed", TRIM_ONLY)
        self.assertEqual(result["route"], NEW_DESIGN_ROUTE)

    def test_superseded_predecessor_forces_the_new_design_route(self):
        result = select_approval_route("approved-superseded", TRIM_ONLY)
        self.assertEqual(result["route"], NEW_DESIGN_ROUTE)

    def test_trim_change_on_a_current_approval_is_a_delta(self):
        self.assertEqual(
            select_approval_route("approved-current", TRIM_ONLY)["route"], DELTA_ROUTE
        )

    def test_layout_and_trim_together_still_fit_the_delta_ceiling(self):
        result = select_approval_route("approved-current", LAYOUT_AND_TRIM)
        self.assertEqual(result["departure_score"], 6)
        self.assertEqual(result["route"], EXTENSION_ROUTE)

    def test_package_and_supplier_take_the_extension_route(self):
        self.assertEqual(
            select_approval_route("approved-current", PACKAGE_AND_SUPPLIER)["route"],
            EXTENSION_ROUTE,
        )

    def test_a_critical_departure_outranks_a_small_score(self):
        result = select_approval_route("approved-current", DIE_TECHNOLOGY)
        self.assertEqual(result["route"], NEW_DESIGN_ROUTE)
        self.assertEqual(result["envelope_critical"], ["die-technology"])

    def test_documentation_only_change_stays_administrative(self):
        result = select_approval_route(
            "approved-current", [{"category": "documentation-only"}]
        )
        self.assertEqual(result["route"], ADMINISTRATIVE_ROUTE)

    def test_score_above_the_extension_ceiling_escalates(self):
        heavy = [
            {"category": "package-or-sealing"},
            {"category": "assembly-process"},
            {"category": "layout-topology"},
        ]
        result = select_approval_route("approved-current", heavy)
        self.assertEqual(result["departure_score"], 18)
        self.assertEqual(result["route"], NEW_DESIGN_ROUTE)

    def test_unknown_predecessor_state_rejected(self):
        with self.assertRaises(ValueError):
            select_approval_route("probably-fine", [])

    def test_every_predecessor_state_selects_a_known_route(self):
        for state in PREDECESSOR_STATES:
            route = select_approval_route(state, TRIM_ONLY)["route"]
            self.assertIn(route, ROUTE_RANK)


class EvidenceTests(unittest.TestCase):
    def test_every_route_owes_evidence(self):
        for route in ROUTE_RANK:
            self.assertTrue(evidence_obligations(route))

    def test_the_delta_family_routes_nest(self):
        # Administrative, delta and extension are the same ladder: each rung
        # keeps everything the rung below owes and adds to it.
        ladder = [ADMINISTRATIVE_ROUTE, DELTA_ROUTE, EXTENSION_ROUTE]
        for lighter, heavier in zip(ladder, ladder[1:]):
            below = evidence_obligations(lighter)
            above = evidence_obligations(heavier)
            self.assertEqual(above[: len(below)], below)
            self.assertGreater(len(above), len(below))

    def test_the_new_design_route_owes_a_different_set(self):
        # It is not the top of the delta ladder; there is no predecessor
        # evidence to add to, so the whole sequence is owed from scratch.
        extension = set(evidence_obligations(EXTENSION_ROUTE))
        new_design = set(evidence_obligations(NEW_DESIGN_ROUTE))
        self.assertEqual(extension & new_design, set())

    def test_new_design_route_owes_the_qualification_sequence(self):
        obligations = evidence_obligations(NEW_DESIGN_ROUTE)
        self.assertTrue(any("qualification lot" in o for o in obligations))

    def test_unknown_route_rejected(self):
        with self.assertRaises(ValueError):
            evidence_obligations("hope-route")


class WithdrawalTests(unittest.TestCase):
    def test_withdrawing_the_critical_departure_lowers_the_route(self):
        changes = DIE_TECHNOLOGY + [{"category": "passive-trim-value"}]
        with_it = select_approval_route("approved-current", changes)
        without = route_without_change("approved-current", changes, "die-technology")
        self.assertEqual(with_it["route"], NEW_DESIGN_ROUTE)
        self.assertEqual(without["route"], DELTA_ROUTE)
        self.assertLess(without["rank"], with_it["rank"])

    def test_withdrawing_a_category_not_declared_rejected(self):
        with self.assertRaises(ValueError):
            route_without_change("approved-current", TRIM_ONLY, "die-technology")

    def test_withdrawing_an_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            route_without_change("approved-current", TRIM_ONLY, "vibes")

    def test_lightest_route_on_a_current_approval_is_administrative(self):
        self.assertEqual(
            lightest_route_reachable("approved-current", PACKAGE_AND_SUPPLIER),
            ADMINISTRATIVE_ROUTE,
        )

    def test_lightest_route_without_a_predecessor_is_still_new_design(self):
        self.assertEqual(lightest_route_reachable("none", []), NEW_DESIGN_ROUTE)


class PlanTests(unittest.TestCase):
    def test_extension_case_plan(self):
        result = plan_type_approval(EXTENSION_CASE)
        self.assertEqual(result["route"], EXTENSION_ROUTE)
        self.assertEqual(result["departure_score"], 13)
        self.assertEqual(result["heaviest_uncovered_departure"], "package-or-sealing")
        self.assertTrue(result["evidence_obligations"])

    def test_new_design_case_plan(self):
        result = plan_type_approval(NEW_DESIGN_CASE)
        self.assertEqual(result["route"], NEW_DESIGN_ROUTE)
        self.assertEqual(result["departure_score"], 0)
        self.assertIsNone(result["heaviest_uncovered_departure"])
        self.assertTrue(any("no approved predecessor" in f for f in result["findings"]))

    def test_plan_reports_covered_departures(self):
        case = _case(
            EXTENSION_CASE,
            changes=[
                {"category": "package-or-sealing"},
                {
                    "category": "die-supplier",
                    "covered_by_predecessor": True,
                    "reference": "predecessor lot data",
                },
            ],
        )
        result = plan_type_approval(case)
        self.assertEqual(result["departure_score"], 8)
        self.assertTrue(any("inside the predecessor envelope" in f for f in result["findings"]))

    def test_plan_flags_an_undeclared_change_set(self):
        result = plan_type_approval(
            {"predecessor_state": "approved-current", "changes": []}
        )
        self.assertEqual(result["route"], ADMINISTRATIVE_ROUTE)
        self.assertTrue(any("no departure declared" in f for f in result["findings"]))

    def test_plan_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            plan_type_approval("approved-current")

    def test_plan_rejects_a_missing_predecessor_state(self):
        case = _case(EXTENSION_CASE)
        del case["predecessor_state"]
        with self.assertRaises(ValueError):
            plan_type_approval(case)

    def test_plan_rejects_a_bad_change_set(self):
        with self.assertRaises(ValueError):
            plan_type_approval(
                {"predecessor_state": "approved-current", "changes": [{"category": "x"}]}
            )

    def test_a_weaker_predecessor_never_lightens_the_route(self):
        current = plan_type_approval(
            {"predecessor_state": "approved-current", "changes": TRIM_ONLY}
        )
        lapsed = plan_type_approval(
            {"predecessor_state": "approved-lapsed", "changes": TRIM_ONLY}
        )
        self.assertGreaterEqual(lapsed["rank"], current["rank"])

    def test_plan_under_a_tighter_policy_escalates(self):
        tight = {
            "administrative_max_score": 0,
            "delta_max_score": 1,
            "extension_max_score": 2,
        }
        result = plan_type_approval(EXTENSION_CASE, tight)
        self.assertEqual(result["route"], NEW_DESIGN_ROUTE)
        self.assertTrue(any("exceeds the extension ceiling" in d for d in result["drivers"]))


if __name__ == "__main__":
    unittest.main()
