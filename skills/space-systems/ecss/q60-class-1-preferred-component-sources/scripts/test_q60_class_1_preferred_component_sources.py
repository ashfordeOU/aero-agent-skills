#!/usr/bin/env python3
"""Contract test for the Class 1 preferred component sources leaf (offline)."""

import copy
import unittest

from q60_class_1_preferred_component_sources_logic import (
    DEFAULT_SELECTION_POLICY,
    LIST_PREFERENCE_BROKEN,
    LIST_PREFERENCE_DEMONSTRATED,
    LIST_PREFERENCE_SHORTFALL,
    LISTING_TIERS,
    REJECT_AND_RESELECT,
    SELECT_DIRECT,
    SELECT_WITH_BOARD_APPROVAL,
    SELECT_WITH_EVALUATION,
    SELECT_WITH_JUSTIFICATION,
    SELECTION_ROUTES,
    assess_parts_list,
    part_one_share,
    preference_penalty,
    select_component,
    selection_assurance,
    selection_route,
    tier_assurance,
    validate_selection_policy,
)

PART_ONE_CASE = {
    "part_reference": "cap-eppl1-0001",
    "listing_tier": "eppl-part-one",
    "part_one_search_performed": True,
    "part_one_alternative_available": True,
    "procurement_specification_reference": "spec-cap-0001",
}

PART_TWO_CASE = {
    "part_reference": "res-eppl2-0002",
    "listing_tier": "eppl-part-two",
    "part_one_search_performed": True,
    "part_one_alternative_available": False,
    "procurement_specification_reference": "spec-res-0002",
}

CATALOGUE_CASE = {
    "part_reference": "ic-cat-0003",
    "listing_tier": "manufacturer-catalogue-unqualified",
    "part_one_search_performed": False,
    "part_one_alternative_available": True,
    "procurement_specification_reference": None,
}


def _case(base, **overrides):
    case = copy.deepcopy(dict(base))
    case.update(overrides)
    return case


def _renamed(base, reference, **overrides):
    return _case(base, part_reference=reference, **overrides)


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_selection_policy(DEFAULT_SELECTION_POLICY), DEFAULT_SELECTION_POLICY
        )

    def test_policy_covers_every_listing_tier(self):
        for tier in LISTING_TIERS:
            self.assertIn(tier, DEFAULT_SELECTION_POLICY["tier_assurance"])
            self.assertIn(tier, DEFAULT_SELECTION_POLICY["tier_route"])

    def test_every_route_is_a_known_route(self):
        for tier in LISTING_TIERS:
            self.assertIn(DEFAULT_SELECTION_POLICY["tier_route"][tier], SELECTION_ROUTES)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_selection_policy("default")

    def test_policy_missing_a_tier_rejected(self):
        broken = copy.deepcopy(DEFAULT_SELECTION_POLICY)
        del broken["tier_assurance"]["eppl-part-two"]
        with self.assertRaises(ValueError):
            validate_selection_policy(broken)

    def test_policy_assurance_above_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_SELECTION_POLICY)
        broken["tier_assurance"]["other-agency-qualified"] = 1.4
        with self.assertRaises(ValueError):
            validate_selection_policy(broken)

    def test_policy_demoting_part_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_SELECTION_POLICY)
        broken["tier_assurance"]["eppl-part-one"] = 0.9
        with self.assertRaises(ValueError):
            validate_selection_policy(broken)

    def test_policy_with_unknown_route_rejected(self):
        broken = copy.deepcopy(DEFAULT_SELECTION_POLICY)
        broken["tier_route"]["eppl-part-two"] = "buy-it-anyway"
        with self.assertRaises(ValueError):
            validate_selection_policy(broken)

    def test_policy_thresholds_out_of_order_rejected(self):
        broken = copy.deepcopy(DEFAULT_SELECTION_POLICY)
        broken["reselect_threshold"] = 0.9
        with self.assertRaises(ValueError):
            validate_selection_policy(broken)


class TierTests(unittest.TestCase):
    def test_part_one_carries_full_assurance(self):
        self.assertAlmostEqual(tier_assurance("eppl-part-one"), 1.0, places=9)

    def test_tiers_fall_away_from_part_one(self):
        values = [tier_assurance(tier) for tier in LISTING_TIERS]
        for stronger, weaker in zip(values, values[1:]):
            self.assertGreater(stronger, weaker)

    def test_unknown_tier_rejected(self):
        with self.assertRaises(ValueError):
            tier_assurance("surplus-market-listing")


class PenaltyTests(unittest.TestCase):
    def test_part_one_carries_no_penalty(self):
        self.assertAlmostEqual(preference_penalty(PART_ONE_CASE), 0.0, places=9)

    def test_unsearched_departure_is_penalised(self):
        case = _case(PART_TWO_CASE, part_one_search_performed=False)
        self.assertAlmostEqual(
            preference_penalty(case),
            DEFAULT_SELECTION_POLICY["unsearched_alternative_penalty"],
            places=9,
        )

    def test_available_alternative_is_penalised(self):
        case = _case(PART_TWO_CASE, part_one_alternative_available=True)
        self.assertAlmostEqual(
            preference_penalty(case),
            DEFAULT_SELECTION_POLICY["available_alternative_penalty"],
            places=9,
        )

    def test_missing_specification_is_penalised(self):
        case = _case(PART_TWO_CASE, procurement_specification_reference=None)
        self.assertAlmostEqual(
            preference_penalty(case),
            DEFAULT_SELECTION_POLICY["missing_specification_penalty"],
            places=9,
        )

    def test_penalty_never_exceeds_one(self):
        self.assertLessEqual(preference_penalty(CATALOGUE_CASE), 1.0)


class AssuranceTests(unittest.TestCase):
    def test_clean_part_one_selection_is_full(self):
        self.assertAlmostEqual(selection_assurance(PART_ONE_CASE), 1.0, places=9)

    def test_clean_part_two_selection_keeps_its_tier_value(self):
        self.assertAlmostEqual(selection_assurance(PART_TWO_CASE), 0.80, places=9)

    def test_assurance_is_floored_at_zero(self):
        self.assertAlmostEqual(selection_assurance(CATALOGUE_CASE), 0.0, places=9)


class RouteTests(unittest.TestCase):
    def test_part_one_routes_straight_through(self):
        self.assertEqual(selection_route(PART_ONE_CASE), SELECT_DIRECT)

    def test_clean_part_two_needs_a_recorded_justification(self):
        self.assertEqual(selection_route(PART_TWO_CASE), SELECT_WITH_JUSTIFICATION)

    def test_known_part_one_equivalent_forces_board_approval(self):
        case = _case(PART_TWO_CASE, part_one_alternative_available=True)
        self.assertEqual(selection_route(case), SELECT_WITH_BOARD_APPROVAL)

    def test_unlisted_qualified_part_needs_an_evaluation_programme(self):
        case = _case(
            PART_TWO_CASE,
            part_reference="dio-oth-0004",
            listing_tier="other-agency-qualified",
        )
        self.assertEqual(selection_route(case), SELECT_WITH_EVALUATION)

    def test_stripped_catalogue_part_is_sent_back(self):
        self.assertEqual(selection_route(CATALOGUE_CASE), REJECT_AND_RESELECT)

    def test_assurance_sitting_on_the_threshold_is_not_escalated(self):
        policy = copy.deepcopy(DEFAULT_SELECTION_POLICY)
        policy["board_approval_threshold"] = policy["tier_assurance"]["eppl-part-two"]
        self.assertEqual(
            selection_route(PART_TWO_CASE, policy), SELECT_WITH_JUSTIFICATION
        )

    def test_assurance_sitting_on_the_reselect_threshold_is_still_usable(self):
        policy = copy.deepcopy(DEFAULT_SELECTION_POLICY)
        policy["reselect_threshold"] = policy["tier_assurance"][
            "manufacturer-catalogue-unqualified"
        ]
        policy["board_approval_threshold"] = policy["reselect_threshold"]
        case = _case(
            CATALOGUE_CASE,
            part_one_search_performed=True,
            part_one_alternative_available=False,
            procurement_specification_reference="spec-ic-0003",
        )
        self.assertNotEqual(selection_route(case, policy), REJECT_AND_RESELECT)


class CaseValidationTests(unittest.TestCase):
    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            select_component("eppl-part-one")

    def test_empty_part_reference_rejected(self):
        with self.assertRaises(ValueError):
            select_component(_case(PART_TWO_CASE, part_reference="  "))

    def test_unknown_tier_in_case_rejected(self):
        with self.assertRaises(ValueError):
            select_component(_case(PART_TWO_CASE, listing_tier="grey-market"))

    def test_non_boolean_search_flag_rejected(self):
        with self.assertRaises(ValueError):
            select_component(_case(PART_TWO_CASE, part_one_search_performed="yes"))

    def test_blank_specification_reference_rejected(self):
        with self.assertRaises(ValueError):
            select_component(
                _case(PART_TWO_CASE, procurement_specification_reference="")
            )

    def test_part_one_claiming_no_part_one_item_rejected(self):
        with self.assertRaises(ValueError):
            select_component(
                _case(PART_ONE_CASE, part_one_alternative_available=False)
            )


class SelectionReportTests(unittest.TestCase):
    def test_part_one_report_raises_no_finding(self):
        report = select_component(PART_ONE_CASE)
        self.assertTrue(report["from_part_one"])
        self.assertFalse(report["justification_required"])
        self.assertEqual(report["findings"], [])

    def test_departure_report_names_every_finding(self):
        report = select_component(CATALOGUE_CASE)
        self.assertEqual(len(report["findings"]), 3)
        self.assertFalse(report["usable"])

    def test_report_carries_the_route_and_the_assurance(self):
        report = select_component(PART_TWO_CASE)
        self.assertEqual(report["route"], SELECT_WITH_JUSTIFICATION)
        self.assertAlmostEqual(report["selection_assurance"], 0.80, places=9)


class ShareTests(unittest.TestCase):
    def test_share_counts_only_part_one_entries(self):
        graded = [
            select_component(PART_ONE_CASE),
            select_component(_renamed(PART_ONE_CASE, "cap-eppl1-0005")),
            select_component(PART_TWO_CASE),
            select_component(_renamed(PART_TWO_CASE, "res-eppl2-0006")),
        ]
        self.assertAlmostEqual(part_one_share(graded), 0.5, places=9)

    def test_empty_selection_list_rejected(self):
        with self.assertRaises(ValueError):
            part_one_share([])

    def test_ungraded_entry_rejected(self):
        with self.assertRaises(ValueError):
            part_one_share([{"part_reference": "x"}])


class PartsListTests(unittest.TestCase):
    def _compliant_list(self):
        return [
            _renamed(PART_ONE_CASE, "cap-eppl1-0001"),
            _renamed(PART_ONE_CASE, "cap-eppl1-0002"),
            _renamed(PART_ONE_CASE, "cap-eppl1-0003"),
            _renamed(PART_TWO_CASE, "res-eppl2-0004"),
        ]

    def test_list_meeting_the_floor_is_demonstrated(self):
        result = assess_parts_list(self._compliant_list())
        self.assertEqual(result["verdict"], LIST_PREFERENCE_DEMONSTRATED)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["part_one_share"], 0.75, places=9)

    def test_share_landing_on_the_floor_is_accepted(self):
        result = assess_parts_list(self._compliant_list())
        self.assertTrue(result["meets_share_floor"])
        self.assertAlmostEqual(
            result["part_one_share"], result["part_one_share_floor"], places=9
        )

    def test_list_below_the_floor_is_a_shortfall(self):
        cases = [
            _renamed(PART_ONE_CASE, "cap-eppl1-0001"),
            _renamed(PART_TWO_CASE, "res-eppl2-0002"),
            _renamed(PART_TWO_CASE, "res-eppl2-0003"),
            _renamed(PART_TWO_CASE, "res-eppl2-0004"),
        ]
        result = assess_parts_list(cases)
        self.assertEqual(result["verdict"], LIST_PREFERENCE_SHORTFALL)
        self.assertFalse(result["meets_share_floor"])

    def test_any_unusable_part_breaks_the_list(self):
        cases = self._compliant_list() + [_renamed(CATALOGUE_CASE, "ic-cat-0009")]
        result = assess_parts_list(cases)
        self.assertEqual(result["verdict"], LIST_PREFERENCE_BROKEN)
        self.assertIn("ic-cat-0009", result["reselect_needed"])

    def test_weakest_part_is_named(self):
        cases = self._compliant_list() + [
            _renamed(
                PART_TWO_CASE,
                "res-eppl2-0010",
                part_one_search_performed=False,
                part_one_alternative_available=True,
            )
        ]
        result = assess_parts_list(cases)
        self.assertEqual(result["weakest_part"], "res-eppl2-0010")

    def test_departures_are_listed_by_reference(self):
        result = assess_parts_list(self._compliant_list())
        self.assertEqual(result["departures"], ["res-eppl2-0004"])

    def test_duplicate_part_reference_rejected(self):
        cases = [
            _renamed(PART_ONE_CASE, "cap-eppl1-0001"),
            _renamed(PART_ONE_CASE, "cap-eppl1-0001"),
        ]
        with self.assertRaises(ValueError):
            assess_parts_list(cases)

    def test_empty_parts_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_list([])

    def test_non_sequence_parts_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_parts_list(PART_ONE_CASE)

    def test_evaluations_needed_is_collected(self):
        cases = self._compliant_list() + [
            _renamed(
                PART_TWO_CASE,
                "dio-oth-0011",
                listing_tier="other-agency-qualified",
            )
        ]
        result = assess_parts_list(cases)
        self.assertIn("dio-oth-0011", result["evaluations_needed"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
