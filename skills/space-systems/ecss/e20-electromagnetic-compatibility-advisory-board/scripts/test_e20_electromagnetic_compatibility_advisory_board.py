#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-20C clause 6.2.3 electromagnetic
compatibility advisory board.

Exercises scripts/e20_electromagnetic_compatibility_advisory_board_logic.py
(stdlib unittest, offline). Contract: a nominated role maps to exactly
one seat category and an unrecognized role raises; a member record is
normalized or rejected; the voting membership excludes observers and
un-appointed nominees; the quorum is the stated fraction of the voting
membership rounded up, absorbing binary representation error rather
than demanding an extra seat; a sitting is quorate only with the chair
in the room; every electromagnetically relevant subsystem needs a
representative; an agenda topic outside the remit raises before it can
be voted; a carried item that moves the baseline escalates for
customer approval; and the aggregate review is compliant only when the
board is constituted, quorate and leaves nothing deferred.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e20_electromagnetic_compatibility_advisory_board_logic as ab  # noqa: E402


def _full_board():
    """A board that fills every core seat and speaks for both listed
    subsystems."""
    return [
        {"member_id": "M-CHAIR", "role": "chairperson"},
        {"member_id": "M-SE", "role": "system_engineering_representative"},
        {"member_id": "M-CUST", "role": "customer_representative"},
        {"member_id": "M-PA", "role": "product_assurance_representative"},
        {"member_id": "M-GND", "role": "grounding_and_bonding_authority"},
        {
            "member_id": "M-AOCS",
            "role": "subsystem_emc_representative",
            "subsystems": ["aocs", "power"],
        },
        {
            "member_id": "M-PLD",
            "role": "payload_emc_representative",
            "subsystems": ["payload"],
        },
        {"member_id": "M-OBS", "role": "supplier_observer"},
    ]


def _clean_sitting():
    return {
        "members": _full_board(),
        "emc_relevant_subsystems": ["aocs", "power", "payload"],
        "present_member_ids": [
            "M-CHAIR",
            "M-SE",
            "M-CUST",
            "M-PA",
            "M-GND",
            "M-AOCS",
            "M-PLD",
        ],
        "quorum_fraction": 0.6,
        "agenda": [
            {
                "item_id": "AI-01",
                "item_kind": "emc_verification_plan_endorsement",
                "votes_for": 6,
                "votes_against": 1,
            },
            {
                "item_id": "AI-02",
                "item_kind": "interference_margin_deviation",
                "votes_for": 5,
                "votes_against": 2,
            },
        ],
    }


class CategorizeBoardRoleTest(unittest.TestCase):
    def test_chairperson_is_a_core_seat(self):
        self.assertEqual(ab.categorize_board_role("chairperson"), "core")

    def test_customer_representative_is_a_core_seat(self):
        self.assertEqual(ab.categorize_board_role("customer_representative"), "core")

    def test_grounding_authority_is_a_core_seat(self):
        self.assertEqual(
            ab.categorize_board_role("grounding_and_bonding_authority"), "core"
        )

    def test_subsystem_representative_is_a_contributing_seat(self):
        self.assertEqual(
            ab.categorize_board_role("subsystem_emc_representative"), "contributing"
        )

    def test_supplier_observer_is_an_observer_seat(self):
        self.assertEqual(ab.categorize_board_role("supplier_observer"), "observer")

    def test_every_known_role_lands_in_one_category_only(self):
        core = ab.CORE_BOARD_ROLES
        contributing = ab.CONTRIBUTING_BOARD_ROLES
        observer = ab.OBSERVER_BOARD_ROLES
        self.assertEqual(core & contributing, frozenset())
        self.assertEqual(core & observer, frozenset())
        self.assertEqual(contributing & observer, frozenset())

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            ab.categorize_board_role("catering_manager")

    def test_none_role_raises(self):
        with self.assertRaises(ValueError):
            ab.categorize_board_role(None)


class ValidateMemberTest(unittest.TestCase):
    def test_defaults_appointed_to_true(self):
        record = ab.validate_member({"member_id": "M-1", "role": "chairperson"})
        self.assertTrue(record["appointed"])

    def test_subsystems_are_sorted_for_determinism(self):
        record = ab.validate_member(
            {
                "member_id": "M-1",
                "role": "subsystem_emc_representative",
                "subsystems": ["thermal", "aocs"],
            }
        )
        self.assertEqual(record["subsystems"], ("aocs", "thermal"))

    def test_non_mapping_member_raises(self):
        with self.assertRaises(ValueError):
            ab.validate_member(["M-1", "chairperson"])

    def test_empty_member_id_raises(self):
        with self.assertRaises(ValueError):
            ab.validate_member({"member_id": "   ", "role": "chairperson"})

    def test_missing_role_raises(self):
        with self.assertRaises(ValueError):
            ab.validate_member({"member_id": "M-1"})

    def test_non_boolean_appointed_raises(self):
        with self.assertRaises(ValueError):
            ab.validate_member(
                {"member_id": "M-1", "role": "chairperson", "appointed": "yes"}
            )

    def test_string_subsystems_raises(self):
        with self.assertRaises(ValueError):
            ab.validate_member(
                {"member_id": "M-1", "role": "chairperson", "subsystems": "aocs"}
            )

    def test_empty_subsystem_name_raises(self):
        with self.assertRaises(ValueError):
            ab.validate_member(
                {"member_id": "M-1", "role": "chairperson", "subsystems": [""]}
            )


class ValidateMembershipTest(unittest.TestCase):
    def test_full_board_normalizes(self):
        self.assertEqual(len(ab.validate_membership(_full_board())), 8)

    def test_empty_membership_raises(self):
        with self.assertRaises(ValueError):
            ab.validate_membership([])

    def test_mapping_membership_raises(self):
        with self.assertRaises(ValueError):
            ab.validate_membership({"member_id": "M-1", "role": "chairperson"})

    def test_duplicate_member_id_raises(self):
        members = _full_board()
        members.append({"member_id": "M-CHAIR", "role": "secretariat"})
        with self.assertRaises(ValueError):
            ab.validate_membership(members)


class VotingMembershipTest(unittest.TestCase):
    def test_observer_does_not_vote(self):
        self.assertNotIn("M-OBS", ab.voting_member_ids(_full_board()))

    def test_full_board_has_seven_voting_seats(self):
        self.assertEqual(len(ab.voting_member_ids(_full_board())), 7)

    def test_unappointed_nominee_does_not_vote(self):
        members = _full_board()
        members[5]["appointed"] = False
        self.assertNotIn("M-AOCS", ab.voting_member_ids(members))

    def test_voting_ids_are_sorted(self):
        ids = ab.voting_member_ids(_full_board())
        self.assertEqual(list(ids), sorted(ids))


class MissingCoreRolesTest(unittest.TestCase):
    def test_full_board_misses_nothing(self):
        self.assertEqual(ab.missing_core_roles(_full_board()), [])

    def test_dropping_the_grounding_authority_is_reported(self):
        members = [m for m in _full_board() if m["member_id"] != "M-GND"]
        self.assertEqual(
            ab.missing_core_roles(members), ["grounding_and_bonding_authority"]
        )

    def test_unappointed_core_seat_counts_as_missing(self):
        members = _full_board()
        members[2]["appointed"] = False
        self.assertIn("customer_representative", ab.missing_core_roles(members))


class CeilWithToleranceTest(unittest.TestCase):
    def test_exact_integer_is_unchanged(self):
        self.assertEqual(ab._ceil_with_tolerance(14.0), 14)

    def test_representation_error_above_an_integer_is_absorbed(self):
        product = 0.56 * 25
        self.assertGreater(product, 14.0)
        self.assertEqual(ab._ceil_with_tolerance(product), 14)

    def test_a_real_fraction_still_rounds_up(self):
        self.assertEqual(ab._ceil_with_tolerance(14.4), 15)

    def test_non_finite_value_raises(self):
        with self.assertRaises(ValueError):
            ab._ceil_with_tolerance(float("inf"))

    def test_non_numeric_value_raises(self):
        with self.assertRaises(ValueError):
            ab._ceil_with_tolerance("14")


class QuorumRequirementTest(unittest.TestCase):
    def test_sixty_percent_of_seven_seats_needs_five(self):
        self.assertEqual(ab.quorum_requirement(_full_board(), 0.6), 5)

    def test_full_fraction_needs_every_voting_seat(self):
        self.assertEqual(ab.quorum_requirement(_full_board(), 1.0), 7)

    def test_tiny_fraction_still_needs_one_seat(self):
        self.assertEqual(ab.quorum_requirement(_full_board(), 0.01), 1)

    def test_zero_fraction_raises(self):
        with self.assertRaises(ValueError):
            ab.quorum_requirement(_full_board(), 0.0)

    def test_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            ab.quorum_requirement(_full_board(), 1.2)

    def test_boolean_fraction_raises(self):
        with self.assertRaises(ValueError):
            ab.quorum_requirement(_full_board(), True)

    def test_board_of_observers_only_raises(self):
        with self.assertRaises(ValueError):
            ab.quorum_requirement(
                [{"member_id": "M-OBS", "role": "supplier_observer"}], 0.5
            )


class QuorumStateTest(unittest.TestCase):
    def test_clean_sitting_is_quorate(self):
        state = ab.quorum_state(
            _full_board(), _clean_sitting()["present_member_ids"], 0.6
        )
        self.assertTrue(state["quorate"])
        self.assertEqual(state["required_voting_members"], 5)

    def test_sitting_without_the_chair_is_not_quorate(self):
        present = [m for m in _clean_sitting()["present_member_ids"] if m != "M-CHAIR"]
        state = ab.quorum_state(_full_board(), present, 0.6)
        self.assertFalse(state["chair_present"])
        self.assertFalse(state["quorate"])

    def test_too_few_voting_members_is_not_quorate(self):
        state = ab.quorum_state(_full_board(), ["M-CHAIR", "M-SE"], 0.6)
        self.assertFalse(state["quorate"])

    def test_present_observer_is_not_counted_as_a_voter(self):
        state = ab.quorum_state(
            _full_board(),
            ["M-CHAIR", "M-SE", "M-CUST", "M-PA", "M-OBS"],
            0.6,
        )
        self.assertEqual(len(state["present_voting_members"]), 4)
        self.assertFalse(state["quorate"])

    def test_attendee_not_on_the_board_raises(self):
        with self.assertRaises(ValueError):
            ab.quorum_state(_full_board(), ["M-CHAIR", "M-GHOST"], 0.6)

    def test_string_attendance_raises(self):
        with self.assertRaises(ValueError):
            ab.quorum_state(_full_board(), "M-CHAIR", 0.6)


class SubsystemRepresentationTest(unittest.TestCase):
    def test_every_listed_subsystem_is_represented(self):
        self.assertEqual(
            ab.subsystem_representation_findings(
                ["aocs", "power", "payload"], _full_board()
            ),
            [],
        )

    def test_unrepresented_subsystem_is_reported(self):
        findings = ab.subsystem_representation_findings(
            ["aocs", "propulsion"], _full_board()
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("propulsion", findings[0])

    def test_unappointed_representative_does_not_cover_its_subsystem(self):
        members = _full_board()
        members[6]["appointed"] = False
        findings = ab.subsystem_representation_findings(["payload"], members)
        self.assertEqual(len(findings), 1)

    def test_string_subsystem_list_raises(self):
        with self.assertRaises(ValueError):
            ab.subsystem_representation_findings("aocs", _full_board())

    def test_empty_subsystem_name_raises(self):
        with self.assertRaises(ValueError):
            ab.subsystem_representation_findings(["aocs", ""], _full_board())


class AgendaItemCategoryTest(unittest.TestCase):
    def test_emission_limit_tailoring_is_a_requirement_item(self):
        self.assertEqual(
            ab.categorize_agenda_item("emission_limit_tailoring"), "requirement"
        )

    def test_grounding_change_is_an_architecture_item(self):
        self.assertEqual(
            ab.categorize_agenda_item("grounding_architecture_change"), "architecture"
        )

    def test_margin_deviation_is_a_deviation_item(self):
        self.assertEqual(
            ab.categorize_agenda_item("interference_margin_deviation"), "deviation"
        )

    def test_point_list_review_is_a_verification_item(self):
        self.assertEqual(
            ab.categorize_agenda_item("interference_critical_point_list_review"),
            "verification",
        )

    def test_out_of_remit_topic_raises(self):
        with self.assertRaises(ValueError):
            ab.categorize_agenda_item("propellant_budget")

    def test_unknown_topic_raises(self):
        with self.assertRaises(ValueError):
            ab.categorize_agenda_item("coffee_rota")

    def test_requirement_item_needs_customer_approval(self):
        self.assertTrue(ab.item_needs_customer_approval("emission_limit_tailoring"))

    def test_verification_item_does_not_need_customer_approval(self):
        self.assertFalse(
            ab.item_needs_customer_approval("emc_verification_plan_endorsement")
        )


class DisposeAgendaItemTest(unittest.TestCase):
    def test_carried_verification_item_is_endorsed(self):
        item = {
            "item_kind": "emc_verification_plan_endorsement",
            "votes_for": 4,
            "votes_against": 1,
        }
        self.assertEqual(ab.dispose_agenda_item(item, True), "endorsed")

    def test_carried_deviation_escalates_to_the_customer(self):
        item = {
            "item_kind": "interference_margin_deviation",
            "votes_for": 4,
            "votes_against": 1,
        }
        self.assertEqual(
            ab.dispose_agenda_item(item, True), "escalated_for_customer_approval"
        )

    def test_tied_vote_is_rejected_not_carried(self):
        item = {
            "item_kind": "emc_verification_plan_endorsement",
            "votes_for": 3,
            "votes_against": 3,
        }
        self.assertEqual(ab.dispose_agenda_item(item, True), "rejected")

    def test_abstentions_do_not_count_towards_the_majority(self):
        item = {
            "item_kind": "emc_verification_plan_endorsement",
            "votes_for": 2,
            "votes_against": 1,
            "abstentions": 4,
        }
        self.assertEqual(ab.dispose_agenda_item(item, True), "endorsed")

    def test_all_abstentions_defers_the_item(self):
        item = {
            "item_kind": "emc_verification_plan_endorsement",
            "votes_for": 0,
            "votes_against": 0,
            "abstentions": 7,
        }
        self.assertEqual(ab.dispose_agenda_item(item, True), "deferred")

    def test_inquorate_sitting_defers_every_item(self):
        item = {
            "item_kind": "emc_verification_plan_endorsement",
            "votes_for": 7,
            "votes_against": 0,
        }
        self.assertEqual(ab.dispose_agenda_item(item, False), "deferred")

    def test_out_of_remit_item_raises_before_the_vote(self):
        item = {"item_kind": "thermal_control_budget", "votes_for": 7}
        with self.assertRaises(ValueError):
            ab.dispose_agenda_item(item, True)

    def test_negative_tally_raises(self):
        item = {
            "item_kind": "emc_verification_plan_endorsement",
            "votes_for": -1,
        }
        with self.assertRaises(ValueError):
            ab.dispose_agenda_item(item, True)

    def test_fractional_tally_raises(self):
        item = {
            "item_kind": "emc_verification_plan_endorsement",
            "votes_for": 2.5,
            "votes_against": 1,
        }
        with self.assertRaises(ValueError):
            ab.dispose_agenda_item(item, True)

    def test_non_boolean_quorate_raises(self):
        item = {"item_kind": "emc_verification_plan_endorsement", "votes_for": 3}
        with self.assertRaises(ValueError):
            ab.dispose_agenda_item(item, "yes")

    def test_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            ab.dispose_agenda_item(["emc_verification_plan_endorsement"], True)


class CompositionFindingsTest(unittest.TestCase):
    def test_full_board_has_no_composition_finding(self):
        self.assertEqual(ab.composition_findings(_full_board()), [])

    def test_second_chairperson_is_reported(self):
        members = _full_board()
        members.append({"member_id": "M-CHAIR2", "role": "chairperson"})
        findings = ab.composition_findings(members)
        self.assertTrue(any("chairpersons" in f for f in findings))

    def test_unappointed_nominee_is_reported(self):
        members = _full_board()
        members[5]["appointed"] = False
        findings = ab.composition_findings(members)
        self.assertTrue(any("not appointed" in f for f in findings))

    def test_findings_are_sorted_and_deduplicated(self):
        members = [m for m in _full_board() if m["member_id"] not in ("M-GND", "M-PA")]
        findings = ab.composition_findings(members)
        self.assertEqual(findings, sorted(findings))
        self.assertEqual(len(findings), len(set(findings)))


class ReviewAdvisoryBoardTest(unittest.TestCase):
    def test_clean_sitting_is_constituted_and_compliant(self):
        review = ab.review_advisory_board(_clean_sitting())
        self.assertTrue(review["constituted"])
        self.assertTrue(review["compliant"])
        self.assertEqual(review["open_items"], [])

    def test_deviation_item_is_escalated_in_the_aggregate(self):
        review = ab.review_advisory_board(_clean_sitting())
        self.assertEqual(
            review["dispositions"]["AI-02"], "escalated_for_customer_approval"
        )

    def test_missing_core_seat_blocks_constitution(self):
        sitting = _clean_sitting()
        sitting["members"] = [
            m for m in sitting["members"] if m["member_id"] != "M-PA"
        ]
        sitting["present_member_ids"] = [
            m for m in sitting["present_member_ids"] if m != "M-PA"
        ]
        review = ab.review_advisory_board(sitting)
        self.assertFalse(review["constituted"])
        self.assertFalse(review["compliant"])

    def test_unrepresented_subsystem_blocks_constitution(self):
        sitting = _clean_sitting()
        sitting["emc_relevant_subsystems"].append("propulsion")
        review = ab.review_advisory_board(sitting)
        self.assertFalse(review["constituted"])
        self.assertEqual(len(review["representation_findings"]), 1)

    def test_inquorate_sitting_leaves_every_item_open(self):
        sitting = _clean_sitting()
        sitting["present_member_ids"] = ["M-CHAIR", "M-SE"]
        review = ab.review_advisory_board(sitting)
        self.assertFalse(review["compliant"])
        self.assertEqual(review["open_items"], ["AI-01", "AI-02"])

    def test_duplicate_item_id_raises(self):
        sitting = _clean_sitting()
        sitting["agenda"].append(dict(sitting["agenda"][0]))
        with self.assertRaises(ValueError):
            ab.review_advisory_board(sitting)

    def test_non_mapping_board_raises(self):
        with self.assertRaises(ValueError):
            ab.review_advisory_board(["members"])

    def test_mapping_agenda_raises(self):
        sitting = _clean_sitting()
        sitting["agenda"] = {"AI-01": "endorsed"}
        with self.assertRaises(ValueError):
            ab.review_advisory_board(sitting)

    def test_review_is_deterministic_across_repeated_calls(self):
        first = ab.review_advisory_board(_clean_sitting())
        second = ab.review_advisory_board(_clean_sitting())
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
