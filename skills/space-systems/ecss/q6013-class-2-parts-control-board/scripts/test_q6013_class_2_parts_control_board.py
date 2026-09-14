"""Contract tests for the clause 5.1.3 class 2 parts control board.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused board policy, a
board missing a required voting role, a session or a circulation that did
not reach its floor, a circulation that missed a voting member, votes cast
by more members than took part, an approval share under its floor, a
decision with no data package, a critical usage the customer was never
told about, and a record raised after the procurement commitment.
"""

import unittest

from q6013_class_2_parts_control_board_logic import (
    APPROVAL_SHARE_SHORT,
    BOARD_APPROVALS_SOUND,
    BOARD_CHAIR,
    BOARD_NOT_CONSTITUTED,
    BY_WRITTEN_PROCEDURE,
    CIRCULATION_INCOMPLETE,
    COMPONENT_ENGINEERING_MEMBER,
    DECISION_NOT_QUORATE,
    DECISION_RECORD_INCOMPLETE,
    DEFAULT_BOARD_POLICY,
    DESIGN_AUTHORITY_MEMBER,
    IN_SESSION,
    MISSING_CUSTOMER_NOTIFICATION,
    MISSING_DATA_PACKAGE,
    PARTICIPATION_SHORT,
    PRODUCT_ASSURANCE_MEMBER,
    RECORDED_AFTER_COMMITMENT,
    REQUIRED_VOTING_ROLES,
    TECHNICAL_OBSERVER,
    applicable_participation_floor,
    approval_advisories,
    approval_share,
    assess_parts_control_board,
    board_is_constituted,
    decision_defects,
    missing_voting_roles,
    participation_share,
    validate_board_policy,
    validate_decision_record,
    validate_decisions,
    validate_member_record,
    validate_members,
    voting_members,
    weakest_approved_decision,
)

VOTERS = ("pcb-chair", "components-engineer", "design-lead", "pa-engineer")


def _policy(**overrides):
    policy = dict(DEFAULT_BOARD_POLICY)
    policy.update(overrides)
    return policy


def _members():
    return [
        {"id": "pcb-chair", "role": BOARD_CHAIR, "voting": True},
        {
            "id": "components-engineer",
            "role": COMPONENT_ENGINEERING_MEMBER,
            "voting": True,
        },
        {"id": "design-lead", "role": DESIGN_AUTHORITY_MEMBER, "voting": True},
        {"id": "pa-engineer", "role": PRODUCT_ASSURANCE_MEMBER, "voting": True},
        {
            "id": "radiation-specialist",
            "role": TECHNICAL_OBSERVER,
            "voting": False,
        },
    ]


def _session(identifier="d1", **overrides):
    decision = {
        "id": identifier,
        "part_reference": "COTS-LDO-3V3",
        "usage_reference": "power-board-A, warm bay, 12 krad",
        "mode": IN_SESSION,
        "members_present": list(VOTERS) + ["radiation-specialist"],
        "votes_in_favour": 3,
        "votes_against": 1,
        "abstentions": 0,
        "data_package_reference": "DP-014",
        "usage_criticality": 0.4,
        "customer_informed": False,
        "recorded_before_procurement_commitment": True,
    }
    decision.update(overrides)
    return decision


def _written(identifier="d2", **overrides):
    decision = {
        "id": identifier,
        "part_reference": "COTS-ADC-16B",
        "usage_reference": "payload-board-B, hot bay, 30 krad",
        "mode": BY_WRITTEN_PROCEDURE,
        "circulated_to": list(VOTERS),
        "members_responding": list(VOTERS),
        "votes_in_favour": 4,
        "votes_against": 0,
        "abstentions": 0,
        "data_package_reference": "DP-015",
        "usage_criticality": 0.8,
        "customer_informed": True,
        "recorded_before_procurement_commitment": True,
    }
    decision.update(overrides)
    return decision


def _case(**overrides):
    case = {"members": _members(), "decisions": [_session(), _written()]}
    case.update(overrides)
    return case


def _record(decision, members=None):
    return validate_decision_record(decision, members or _members())


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_board_policy(DEFAULT_BOARD_POLICY), DEFAULT_BOARD_POLICY)

    def test_zero_quorum_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(quorum_fraction=0.0))

    def test_written_floor_below_the_quorum_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(
                _policy(quorum_fraction=0.8, written_response_fraction=0.5)
            )

    def test_zero_approval_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(min_approval_fraction=0.0))

    def test_participation_band_wider_than_the_quorum_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(
                _policy(quorum_fraction=0.6, marginal_participation_band=0.7)
            )

    def test_approval_band_wider_than_the_approval_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(
                _policy(min_approval_fraction=0.6, marginal_approval_band=0.7)
            )

    def test_notification_threshold_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(customer_notification_threshold=1.5))

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(["quorum_fraction"])


class MembershipTests(unittest.TestCase):
    def test_a_good_member_reads_back(self):
        record = validate_member_record(_members()[0])
        self.assertEqual(record["role"], BOARD_CHAIR)
        self.assertTrue(record["voting"])

    def test_blank_member_id_refused(self):
        with self.assertRaises(ValueError):
            validate_member_record({"id": "  ", "role": BOARD_CHAIR, "voting": True})

    def test_unrecognised_role_refused(self):
        with self.assertRaises(ValueError):
            validate_member_record(
                {"id": "m1", "role": "parts-enthusiast", "voting": True}
            )

    def test_a_voting_observer_refused(self):
        with self.assertRaises(ValueError):
            validate_member_record(
                {"id": "m1", "role": TECHNICAL_OBSERVER, "voting": True}
            )

    def test_duplicate_member_id_refused(self):
        members = _members()
        members.append({"id": "pcb-chair", "role": BOARD_CHAIR, "voting": True})
        with self.assertRaises(ValueError):
            validate_members(members)

    def test_empty_board_refused(self):
        with self.assertRaises(ValueError):
            validate_members([])

    def test_a_board_with_no_voting_member_refused(self):
        with self.assertRaises(ValueError):
            validate_members(
                [{"id": "m1", "role": TECHNICAL_OBSERVER, "voting": False}]
            )

    def test_voting_members_exclude_the_observer(self):
        self.assertEqual(voting_members(_members()), VOTERS)

    def test_a_complete_board_is_constituted(self):
        self.assertEqual(missing_voting_roles(_members()), ())
        self.assertTrue(board_is_constituted(_members()))

    def test_a_dropped_role_is_named(self):
        members = [m for m in _members() if m["id"] != "pa-engineer"]
        self.assertEqual(missing_voting_roles(members), (PRODUCT_ASSURANCE_MEMBER,))
        self.assertFalse(board_is_constituted(members))


class DecisionValidationTests(unittest.TestCase):
    def test_a_good_session_decision_reads_back_its_voters(self):
        record = _record(_session())
        self.assertEqual(record["participating_voting_members"], VOTERS)
        self.assertEqual(record["votes_cast"], 4)

    def test_a_decision_naming_no_part_refused(self):
        with self.assertRaises(ValueError):
            _record(_session(part_reference="  "))

    def test_a_decision_naming_no_usage_refused(self):
        with self.assertRaises(ValueError):
            _record(_session(usage_reference=""))

    def test_an_unrecognised_mode_refused(self):
        with self.assertRaises(ValueError):
            _record(_session(mode="by-corridor-agreement"))

    def test_a_participant_who_is_not_a_member_refused(self):
        with self.assertRaises(ValueError):
            _record(_session(members_present=list(VOTERS) + ["a-visitor"]))

    def test_a_session_decision_carrying_a_circulation_refused(self):
        with self.assertRaises(ValueError):
            _record(_session(circulated_to=list(VOTERS)))

    def test_a_circulated_decision_carrying_a_present_list_refused(self):
        with self.assertRaises(ValueError):
            _record(_written(members_present=list(VOTERS)))

    def test_a_response_from_outside_the_circulation_refused(self):
        with self.assertRaises(ValueError):
            _record(
                _written(
                    circulated_to=["pcb-chair", "components-engineer"],
                    members_responding=list(VOTERS),
                )
            )

    def test_votes_beyond_the_members_who_took_part_refused(self):
        with self.assertRaises(ValueError):
            _record(
                _session(
                    members_present=["pcb-chair", "components-engineer"],
                    votes_in_favour=3,
                    votes_against=1,
                )
            )

    def test_a_decision_recording_no_vote_refused(self):
        with self.assertRaises(ValueError):
            _record(_session(votes_in_favour=0, votes_against=0, abstentions=0))

    def test_a_non_integer_vote_count_refused(self):
        with self.assertRaises(ValueError):
            _record(_session(votes_in_favour=2.5))

    def test_duplicate_decision_id_refused(self):
        with self.assertRaises(ValueError):
            validate_decisions([_session("d1"), _written("d1")], _members())

    def test_an_empty_decision_set_refused(self):
        with self.assertRaises(ValueError):
            validate_decisions([], _members())

    def test_non_sequence_decisions_refused(self):
        with self.assertRaises(ValueError):
            validate_decisions({"id": "d1"}, _members())


class ShareTests(unittest.TestCase):
    def test_an_observer_does_not_inflate_the_participation(self):
        record = _record(_session())
        self.assertAlmostEqual(participation_share(record, _members()), 1.0, places=9)

    def test_the_floor_depends_on_how_the_decision_was_taken(self):
        self.assertAlmostEqual(
            applicable_participation_floor(_record(_session())), 0.6, places=9
        )
        self.assertAlmostEqual(
            applicable_participation_floor(_record(_written())), 0.75, places=9
        )

    def test_a_circulation_answered_exactly_on_the_floor_is_quorate(self):
        record = _record(
            _written(
                members_responding=["pcb-chair", "components-engineer", "design-lead"],
                votes_in_favour=2,
                votes_against=1,
                abstentions=0,
            )
        )
        self.assertAlmostEqual(participation_share(record, _members()), 0.75, places=9)
        self.assertNotIn(PARTICIPATION_SHORT, decision_defects(record, _members()))

    def test_the_approval_share_is_taken_over_the_votes_cast(self):
        record = _record(_session())
        self.assertAlmostEqual(approval_share(record), 0.75, places=9)

    def test_a_bare_participation_raises_an_advisory(self):
        record = _record(
            _written(
                members_responding=["pcb-chair", "components-engineer", "design-lead"],
                votes_in_favour=3,
                votes_against=0,
                abstentions=0,
            )
        )
        advisories = approval_advisories(record, _members())
        self.assertEqual(len(advisories), 1)
        self.assertIn("participation", advisories[0])

    def test_a_bare_approval_raises_an_advisory(self):
        record = _record(_session())
        advisories = approval_advisories(
            record, _members(), _policy(min_approval_fraction=0.7)
        )
        self.assertEqual(len(advisories), 1)
        self.assertIn("approval share", advisories[0])

    def test_a_comfortable_decision_raises_no_advisory(self):
        self.assertEqual(approval_advisories(_record(_written()), _members()), ())


class AssessmentTests(unittest.TestCase):
    def test_a_sound_board_carries_its_approvals(self):
        result = assess_parts_control_board(_case())
        self.assertEqual(result["verdict"], BOARD_APPROVALS_SOUND)
        self.assertEqual(result["voting_member_count"], len(VOTERS))
        self.assertEqual(len(result["decisions"]), 2)
        self.assertEqual(result["weakest_approved_decision"][0], "d1")
        self.assertAlmostEqual(
            result["weakest_approved_decision"][1], 0.75, places=9
        )

    def test_an_absent_board_is_not_constituted(self):
        case = _case()
        del case["members"]
        result = assess_parts_control_board(case)
        self.assertEqual(result["verdict"], BOARD_NOT_CONSTITUTED)
        self.assertTrue(result["findings"])

    def test_every_missing_role_is_named_not_only_the_first(self):
        members = [
            m for m in _members() if m["id"] not in ("pa-engineer", "design-lead")
        ]
        result = assess_parts_control_board(_case(members=members))
        self.assertEqual(result["verdict"], BOARD_NOT_CONSTITUTED)
        self.assertEqual(len(result["missing_voting_roles"]), 2)
        self.assertEqual(len(result["findings"]), 2)

    def test_every_required_role_is_a_voting_role(self):
        self.assertEqual(len(REQUIRED_VOTING_ROLES), 4)
        self.assertIn(PRODUCT_ASSURANCE_MEMBER, REQUIRED_VOTING_ROLES)

    def test_a_thin_session_is_not_quorate(self):
        decision = _session(
            members_present=["pcb-chair", "radiation-specialist"],
            votes_in_favour=1,
            votes_against=0,
            abstentions=0,
        )
        result = assess_parts_control_board(_case(decisions=[decision]))
        self.assertEqual(result["verdict"], DECISION_NOT_QUORATE)
        self.assertIn(PARTICIPATION_SHORT, result["decisions"][0]["defects"])

    def test_a_thin_circulation_is_not_quorate(self):
        decision = _written(
            members_responding=["pcb-chair", "components-engineer"],
            votes_in_favour=2,
            votes_against=0,
            abstentions=0,
        )
        result = assess_parts_control_board(_case(decisions=[decision]))
        self.assertEqual(result["verdict"], DECISION_NOT_QUORATE)

    def test_a_circulation_that_missed_a_voting_member_is_a_record_defect(self):
        decision = _written(
            circulated_to=["pcb-chair", "components-engineer", "design-lead"],
            members_responding=["pcb-chair", "components-engineer", "design-lead"],
            votes_in_favour=3,
            votes_against=0,
            abstentions=0,
        )
        result = assess_parts_control_board(_case(decisions=[decision]))
        self.assertEqual(result["verdict"], DECISION_RECORD_INCOMPLETE)
        self.assertIn(CIRCULATION_INCOMPLETE, result["decisions"][0]["defects"])

    def test_a_decision_with_no_data_package_is_a_record_defect(self):
        result = assess_parts_control_board(
            _case(decisions=[_session(data_package_reference="  ")])
        )
        self.assertEqual(result["verdict"], DECISION_RECORD_INCOMPLETE)
        self.assertIn(MISSING_DATA_PACKAGE, result["decisions"][0]["defects"])

    def test_a_critical_usage_the_customer_was_not_told_about_is_a_defect(self):
        result = assess_parts_control_board(
            _case(decisions=[_written(customer_informed=False)])
        )
        self.assertEqual(result["verdict"], DECISION_RECORD_INCOMPLETE)
        self.assertIn(
            MISSING_CUSTOMER_NOTIFICATION, result["decisions"][0]["defects"]
        )

    def test_a_benign_usage_needs_no_customer_notification(self):
        result = assess_parts_control_board(_case(decisions=[_session()]))
        self.assertEqual(result["verdict"], BOARD_APPROVALS_SOUND)

    def test_a_record_raised_after_the_commitment_is_a_defect(self):
        result = assess_parts_control_board(
            _case(decisions=[_session(recorded_before_procurement_commitment=False)])
        )
        self.assertEqual(result["verdict"], DECISION_RECORD_INCOMPLETE)
        self.assertIn(RECORDED_AFTER_COMMITMENT, result["decisions"][0]["defects"])

    def test_an_approval_under_its_floor_is_a_record_defect(self):
        result = assess_parts_control_board(
            _case(decisions=[_session(votes_in_favour=1, votes_against=3)])
        )
        self.assertEqual(result["verdict"], DECISION_RECORD_INCOMPLETE)
        self.assertIn(APPROVAL_SHARE_SHORT, result["decisions"][0]["defects"])

    def test_every_defect_on_a_decision_is_reported(self):
        decision = _session(
            data_package_reference="",
            usage_criticality=0.9,
            customer_informed=False,
            recorded_before_procurement_commitment=False,
        )
        result = assess_parts_control_board(_case(decisions=[decision]))
        self.assertEqual(result["verdict"], DECISION_RECORD_INCOMPLETE)
        self.assertEqual(len(result["decisions"][0]["defects"]), 3)

    def test_an_inquorate_decision_does_not_reach_the_approval_arithmetic(self):
        decision = _session(
            members_present=["pcb-chair"],
            votes_in_favour=0,
            votes_against=1,
            abstentions=0,
        )
        records = validate_decisions([decision], _members())
        defects = decision_defects(records[0], _members())
        self.assertIn(PARTICIPATION_SHORT, defects)
        self.assertNotIn(APPROVAL_SHARE_SHORT, defects)

    def test_a_board_with_no_sound_decision_names_no_weakest(self):
        records = validate_decisions(
            [_session(data_package_reference="")], _members()
        )
        self.assertIsNone(weakest_approved_decision(records, _members()))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_parts_control_board(["members"])


if __name__ == "__main__":
    unittest.main()
