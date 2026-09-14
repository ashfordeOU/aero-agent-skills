"""Contract tests for the clause 4.1.3 class 1 parts control board.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused board policy, a
board missing a required voting role, a vote exceeding the members present,
a decision below quorum, a decision with no data package, no customer
concurrence or a record raised after the procurement commitment, and an
approval carried on a bare share.
"""

import unittest

from q6013_class_1_parts_control_board_logic import (
    APPROVAL_SHARE_SHORT,
    BOARD_APPROVALS_SOUND,
    BOARD_CHAIR,
    BOARD_NOT_CONSTITUTED,
    COMPONENT_ENGINEERING_MEMBER,
    CUSTOMER_REPRESENTATIVE_MEMBER,
    DECISION_NOT_QUORATE,
    DECISION_RECORD_INCOMPLETE,
    DEFAULT_BOARD_POLICY,
    DESIGN_AUTHORITY_MEMBER,
    MISSING_CUSTOMER_CONCURRENCE,
    MISSING_DATA_PACKAGE,
    PRODUCT_ASSURANCE_MEMBER,
    RECORDED_AFTER_COMMITMENT,
    REQUIRED_VOTING_ROLES,
    TECHNICAL_OBSERVER,
    approval_fraction,
    assess_parts_control_board,
    attendance_fraction,
    bare_quorum_advisories,
    board_is_constituted,
    decision_is_quorate,
    decision_record_shortfalls,
    decision_verdicts,
    missing_voting_roles,
    record_completeness,
    validate_board_policy,
    validate_decision_record,
    validate_member_record,
    validate_membership,
    voting_members,
    weakest_sound_decision,
)

ALL_PRESENT = ["m-chair", "m-comp", "m-des", "m-pa", "m-cust"]


def _policy(**overrides):
    policy = dict(DEFAULT_BOARD_POLICY)
    policy.update(overrides)
    return policy


def _members():
    return [
        {"id": "m-chair", "role": BOARD_CHAIR, "voting": True},
        {"id": "m-comp", "role": COMPONENT_ENGINEERING_MEMBER, "voting": True},
        {"id": "m-des", "role": DESIGN_AUTHORITY_MEMBER, "voting": True},
        {"id": "m-pa", "role": PRODUCT_ASSURANCE_MEMBER, "voting": True},
        {"id": "m-cust", "role": CUSTOMER_REPRESENTATIVE_MEMBER, "voting": True},
        {"id": "m-obs", "role": TECHNICAL_OBSERVER, "voting": False},
    ]


def _decision(identifier="pcb-01", **overrides):
    decision = {
        "id": identifier,
        "part_reference": "COTS-LDO-3311",
        "usage_reference": "payload processor bay B, 14 krad case",
        "members_present": list(ALL_PRESENT),
        "votes_for": 5,
        "votes_against": 0,
        "data_package_reference": "DP-3311 issue 2",
        "customer_concurrence": True,
        "recorded_before_commitment": True,
    }
    decision.update(overrides)
    return decision


def _case(**overrides):
    case = {"members": _members(), "decisions": [_decision()]}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_board_policy(DEFAULT_BOARD_POLICY), DEFAULT_BOARD_POLICY)

    def test_quorum_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(quorum_fraction=1.3))

    def test_non_positive_quorum_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(quorum_fraction=0.0))

    def test_approval_floor_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(min_approval_fraction=1.1))

    def test_marginal_band_wider_than_the_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(
                _policy(min_approval_fraction=0.6, marginal_approval_band=0.7)
            )

    def test_non_boolean_concurrence_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(require_customer_concurrence="sometimes"))


class MembershipTests(unittest.TestCase):
    def test_a_good_member_reads_back_its_role(self):
        record = validate_member_record(_members()[0])
        self.assertEqual(record["role"], BOARD_CHAIR)

    def test_unrecognised_role_refused(self):
        with self.assertRaises(ValueError):
            validate_member_record({"id": "m-x", "role": "friend-of-the-chair", "voting": True})

    def test_blank_member_id_refused(self):
        with self.assertRaises(ValueError):
            validate_member_record({"id": " ", "role": BOARD_CHAIR, "voting": True})

    def test_duplicate_member_id_refused(self):
        members = _members()
        members.append(dict(members[0]))
        with self.assertRaises(ValueError):
            validate_membership(members)

    def test_a_board_with_no_voting_member_refused(self):
        members = _members()
        for member in members:
            member["voting"] = False
        with self.assertRaises(ValueError):
            validate_membership(members)

    def test_observers_do_not_count_as_voting_members(self):
        self.assertEqual(len(voting_members(_members())), 5)

    def test_a_complete_board_is_constituted(self):
        self.assertTrue(board_is_constituted(_members()))
        self.assertEqual(missing_voting_roles(_members()), ())

    def test_a_non_voting_required_role_is_a_missing_role(self):
        members = _members()
        for member in members:
            if member["role"] == CUSTOMER_REPRESENTATIVE_MEMBER:
                member["voting"] = False
        self.assertEqual(
            missing_voting_roles(members), (CUSTOMER_REPRESENTATIVE_MEMBER,)
        )


class DecisionTests(unittest.TestCase):
    def test_a_decision_with_no_usage_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_decision_record(_decision(usage_reference="  "), _members())

    def test_an_attendee_who_is_not_a_member_refused(self):
        with self.assertRaises(ValueError):
            validate_decision_record(
                _decision(members_present=ALL_PRESENT + ["m-ghost"]), _members()
            )

    def test_votes_exceeding_the_members_present_refused(self):
        with self.assertRaises(ValueError):
            validate_decision_record(
                _decision(members_present=["m-chair", "m-comp"], votes_for=4),
                _members(),
            )

    def test_a_non_integer_vote_count_refused(self):
        with self.assertRaises(ValueError):
            validate_decision_record(_decision(votes_for=3.5), _members())

    def test_attendance_is_taken_over_the_voting_membership(self):
        self.assertAlmostEqual(attendance_fraction(_decision(), _members()), 1.0, places=9)
        thin = _decision(members_present=["m-chair", "m-comp", "m-obs"], votes_for=2)
        self.assertAlmostEqual(attendance_fraction(thin, _members()), 0.4, places=9)

    def test_a_decision_exactly_on_the_quorum_is_quorate(self):
        decision = _decision(
            members_present=["m-chair", "m-comp", "m-des"], votes_for=3, votes_against=0
        )
        self.assertTrue(
            decision_is_quorate(decision, _members(), _policy(quorum_fraction=0.6))
        )

    def test_an_inquorate_decision_is_named(self):
        decision = _decision(members_present=["m-chair", "m-comp"], votes_for=2)
        self.assertFalse(decision_is_quorate(decision, _members()))

    def test_approval_share_is_over_the_votes_cast(self):
        decision = _decision(votes_for=3, votes_against=2)
        self.assertAlmostEqual(approval_fraction(decision, _members()), 0.6, places=9)

    def test_no_vote_cast_gives_no_approval(self):
        decision = _decision(votes_for=0, votes_against=0)
        self.assertAlmostEqual(approval_fraction(decision, _members()), 0.0, places=9)

    def test_every_record_shortfall_is_named_not_only_the_first(self):
        decision = _decision(
            data_package_reference="",
            customer_concurrence=False,
            recorded_before_commitment=False,
        )
        shortfalls = decision_record_shortfalls(decision, _members())
        self.assertEqual(
            shortfalls,
            (MISSING_DATA_PACKAGE, MISSING_CUSTOMER_CONCURRENCE, RECORDED_AFTER_COMMITMENT),
        )

    def test_a_split_vote_below_the_floor_is_a_shortfall(self):
        decision = _decision(votes_for=2, votes_against=3)
        self.assertIn(
            APPROVAL_SHARE_SHORT, decision_record_shortfalls(decision, _members())
        )

    def test_concurrence_may_be_waived_by_policy(self):
        decision = _decision(customer_concurrence=False)
        self.assertEqual(
            decision_record_shortfalls(
                decision, _members(), _policy(require_customer_concurrence=False)
            ),
            (),
        )

    def test_duplicate_decision_id_refused(self):
        with self.assertRaises(ValueError):
            decision_verdicts([_decision(), _decision()], _members())

    def test_an_empty_minute_refused(self):
        with self.assertRaises(ValueError):
            decision_verdicts([], _members())


class BoardRollupTests(unittest.TestCase):
    def test_a_clean_minute_is_completely_recorded(self):
        verdicts = decision_verdicts([_decision(), _decision("pcb-02")], _members())
        self.assertAlmostEqual(record_completeness(verdicts), 1.0, places=9)

    def test_one_bad_decision_halves_the_completeness(self):
        verdicts = decision_verdicts(
            [_decision(), _decision("pcb-02", data_package_reference="")], _members()
        )
        self.assertAlmostEqual(record_completeness(verdicts), 0.5, places=9)

    def test_the_weakest_sound_decision_is_named(self):
        verdicts = decision_verdicts(
            [_decision(), _decision("pcb-02", votes_for=3, votes_against=2)], _members()
        )
        weakest = weakest_sound_decision(verdicts)
        self.assertEqual(weakest["id"], "pcb-02")
        self.assertAlmostEqual(weakest["approval_fraction"], 0.6, places=9)

    def test_no_sound_decision_names_nobody(self):
        verdicts = decision_verdicts(
            [_decision(data_package_reference="")], _members()
        )
        self.assertIsNone(weakest_sound_decision(verdicts))

    def test_a_bare_share_approval_raises_an_advisory(self):
        verdicts = decision_verdicts(
            [_decision(votes_for=3, votes_against=2)], _members()
        )
        advisories = bare_quorum_advisories(
            verdicts, _policy(min_approval_fraction=0.6, marginal_approval_band=0.05)
        )
        self.assertEqual(len(advisories), 1)
        self.assertIn("pcb-01", advisories[0])

    def test_a_unanimous_approval_raises_no_advisory(self):
        verdicts = decision_verdicts([_decision()], _members())
        self.assertEqual(bare_quorum_advisories(verdicts), ())


class AssessmentTests(unittest.TestCase):
    def test_a_sound_board_closes_on_approvals_sound(self):
        result = assess_parts_control_board(_case())
        self.assertEqual(result["verdict"], BOARD_APPROVALS_SOUND)
        self.assertEqual(result["voting_member_count"], len(REQUIRED_VOTING_ROLES))
        self.assertAlmostEqual(result["record_completeness"], 1.0, places=9)

    def test_an_absent_board_is_not_constituted(self):
        case = _case()
        del case["members"]
        result = assess_parts_control_board(case)
        self.assertEqual(result["verdict"], BOARD_NOT_CONSTITUTED)
        self.assertTrue(result["findings"])

    def test_every_missing_role_is_named_not_only_the_first(self):
        members = [
            member
            for member in _members()
            if member["role"] not in (PRODUCT_ASSURANCE_MEMBER, CUSTOMER_REPRESENTATIVE_MEMBER)
        ]
        result = assess_parts_control_board(_case(members=members))
        self.assertEqual(result["verdict"], BOARD_NOT_CONSTITUTED)
        self.assertEqual(len(result["missing_voting_roles"]), 2)

    def test_an_inquorate_decision_closes_the_assessment(self):
        decision = _decision(members_present=["m-chair", "m-comp"], votes_for=2)
        result = assess_parts_control_board(_case(decisions=[decision]))
        self.assertEqual(result["verdict"], DECISION_NOT_QUORATE)

    def test_a_decision_with_no_data_package_is_incomplete(self):
        result = assess_parts_control_board(
            _case(decisions=[_decision(data_package_reference="  ")])
        )
        self.assertEqual(result["verdict"], DECISION_RECORD_INCOMPLETE)

    def test_a_decision_minuted_after_the_order_is_incomplete(self):
        result = assess_parts_control_board(
            _case(decisions=[_decision(recorded_before_commitment=False)])
        )
        self.assertEqual(result["verdict"], DECISION_RECORD_INCOMPLETE)

    def test_a_decision_without_customer_concurrence_is_incomplete(self):
        result = assess_parts_control_board(
            _case(decisions=[_decision(customer_concurrence=False)])
        )
        self.assertEqual(result["verdict"], DECISION_RECORD_INCOMPLETE)

    def test_advisories_travel_with_a_passing_verdict(self):
        result = assess_parts_control_board(
            _case(decisions=[_decision(votes_for=3, votes_against=2)]),
            _policy(min_approval_fraction=0.6, marginal_approval_band=0.05),
        )
        self.assertEqual(result["verdict"], BOARD_APPROVALS_SOUND)
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_parts_control_board(["members"])


if __name__ == "__main__":
    unittest.main()
