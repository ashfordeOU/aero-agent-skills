"""Contract tests for the clause 4.1.3 parts control board route.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused board policy,
a board missing a required seat, a meeting without its chair, attendance
below the quorum share, a decision with no reference, dissent left out of
the minute, a part category whose concurrence never came, an abstention
withholding support and a vote share below the approval threshold.
"""

import unittest

from q60_class_1_parts_control_board_logic import (
    BOARD_NOT_CONSTITUTED,
    BOARD_QUORUM_NOT_MET,
    CONCURRENCE_MISSING,
    CUSTOMER_REPRESENTATIVE,
    DECISION_NOT_RECORDED,
    DEFAULT_BOARD_POLICY,
    DESIGN_AUTHORITY_MEMBER,
    NON_STANDARD_PART,
    PART_USE_APPROVED,
    PART_USE_REFUSED,
    PARTS_ENGINEERING_MEMBER,
    PROCUREMENT_QUALITY_MEMBER,
    PRODUCT_ASSURANCE_CHAIR,
    RELIABILITY_AND_RADIATION_MEMBER,
    REQUIRED_BOARD_ROLES,
    STANDARD_QUALIFIED_PART,
    UPGRADED_PART,
    VOTE_ABSTAIN,
    VOTE_AGAINST,
    VOTE_FOR,
    abstaining_roles,
    absent_roles,
    approval_vote_share,
    assess_parts_control_board,
    attendance_share,
    chair_is_present,
    dissenting_roles,
    marginal_vote_advisory,
    missing_concurrences,
    present_vote_weight,
    quorum_is_met,
    required_concurrences,
    unseated_roles,
    validate_board_policy,
    validate_part_request,
    validate_seat_record,
    validate_seats,
    validate_votes,
)

WEIGHTS = {
    PRODUCT_ASSURANCE_CHAIR: 2.0,
    PARTS_ENGINEERING_MEMBER: 2.0,
    DESIGN_AUTHORITY_MEMBER: 1.0,
    PROCUREMENT_QUALITY_MEMBER: 1.0,
    RELIABILITY_AND_RADIATION_MEMBER: 1.0,
    CUSTOMER_REPRESENTATIVE: 1.0,
}

MEMBERS = {
    PRODUCT_ASSURANCE_CHAIR: "assurance-chair-a",
    PARTS_ENGINEERING_MEMBER: "parts-engineer-b",
    DESIGN_AUTHORITY_MEMBER: "design-lead-c",
    PROCUREMENT_QUALITY_MEMBER: "procurement-quality-d",
    RELIABILITY_AND_RADIATION_MEMBER: "reliability-engineer-e",
    CUSTOMER_REPRESENTATIVE: "customer-delegate-f",
}


def _policy(**overrides):
    policy = dict(DEFAULT_BOARD_POLICY)
    policy.update(overrides)
    return policy


def _seats(present=None, drop=()):
    present_map = present or {}
    return [
        {
            "role": role,
            "member": MEMBERS[role],
            "vote_weight": WEIGHTS[role],
            "present": present_map.get(role, True),
        }
        for role in REQUIRED_BOARD_ROLES
        if role not in drop
    ]


def _votes(overrides=None, seats=None):
    cast = overrides or {}
    seat_records = seats if seats is not None else _seats()
    return {
        record["role"]: cast.get(record["role"], VOTE_FOR)
        for record in seat_records
        if record["present"]
    }


def _request(**overrides):
    request = {
        "part_reference": "PART-1188",
        "category": NON_STANDARD_PART,
        "decision_reference": "PCB-DEC-0042",
        "dissent_recorded": False,
        "votes": _votes(),
    }
    request.update(overrides)
    return request


def _board(**overrides):
    board = {"board_reference": "PCB-2026-11", "seats": _seats()}
    board.update(overrides)
    return board


def _case(**overrides):
    case = {"board": _board(), "part_request": _request()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_board_policy(DEFAULT_BOARD_POLICY), DEFAULT_BOARD_POLICY
        )

    def test_attendance_share_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(min_attendance_share=1.4))

    def test_approval_threshold_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(min_approval_vote_share=1.2))

    def test_non_positive_approval_threshold_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(min_approval_vote_share=0.0))

    def test_marginal_band_wider_than_the_threshold_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(
                _policy(min_approval_vote_share=0.6, marginal_vote_band=0.8)
            )

    def test_non_boolean_chair_rule_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(require_chair_present="usually"))

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(["min_attendance_share"])


class SeatTests(unittest.TestCase):
    def test_a_seat_reads_back(self):
        record = validate_seat_record(
            {
                "role": PARTS_ENGINEERING_MEMBER,
                "member": "parts-engineer-b",
                "vote_weight": 2.0,
                "present": True,
            }
        )
        self.assertEqual(record["role"], PARTS_ENGINEERING_MEMBER)
        self.assertAlmostEqual(record["vote_weight"], 2.0, places=9)

    def test_unrecognised_role_refused(self):
        with self.assertRaises(ValueError):
            validate_seat_record(
                {
                    "role": "catering-member",
                    "member": "someone",
                    "vote_weight": 1.0,
                    "present": True,
                }
            )

    def test_a_seat_with_no_member_refused(self):
        with self.assertRaises(ValueError):
            validate_seat_record(
                {
                    "role": DESIGN_AUTHORITY_MEMBER,
                    "member": "   ",
                    "vote_weight": 1.0,
                    "present": True,
                }
            )

    def test_a_seat_with_no_vote_weight_refused(self):
        with self.assertRaises(ValueError):
            validate_seat_record(
                {
                    "role": DESIGN_AUTHORITY_MEMBER,
                    "member": "design-lead-c",
                    "vote_weight": 0.0,
                    "present": True,
                }
            )

    def test_duplicate_seat_refused(self):
        seats = _seats()
        seats.append(dict(seats[0]))
        with self.assertRaises(ValueError):
            validate_seats(seats)

    def test_non_sequence_seats_refused(self):
        with self.assertRaises(ValueError):
            validate_seats({"role": PRODUCT_ASSURANCE_CHAIR})

    def test_a_dropped_seat_is_reported_unseated(self):
        self.assertEqual(
            unseated_roles(_seats(drop=(CUSTOMER_REPRESENTATIVE,))),
            (CUSTOMER_REPRESENTATIVE,),
        )


class QuorumTests(unittest.TestCase):
    def test_a_full_board_attends_in_full(self):
        self.assertAlmostEqual(attendance_share(_seats()), 1.0, places=9)
        self.assertTrue(chair_is_present(_seats()))

    def test_absent_members_are_named(self):
        seats = _seats(present={DESIGN_AUTHORITY_MEMBER: False})
        self.assertEqual(absent_roles(seats), (DESIGN_AUTHORITY_MEMBER,))

    def test_the_present_weight_is_the_weight_in_the_room(self):
        seats = _seats(present={CUSTOMER_REPRESENTATIVE: False})
        self.assertAlmostEqual(present_vote_weight(seats), 7.0, places=9)

    def test_a_meeting_without_the_chair_is_not_quorate(self):
        seats = _seats(present={PRODUCT_ASSURANCE_CHAIR: False})
        self.assertFalse(quorum_is_met(seats))

    def test_attendance_exactly_on_the_share_is_quorate(self):
        seats = _seats(
            present={
                PROCUREMENT_QUALITY_MEMBER: False,
                RELIABILITY_AND_RADIATION_MEMBER: False,
                CUSTOMER_REPRESENTATIVE: False,
            }
        )
        self.assertAlmostEqual(attendance_share(seats), 0.5, places=9)
        self.assertTrue(quorum_is_met(seats, _policy(min_attendance_share=0.5)))

    def test_attendance_below_the_share_is_not_quorate(self):
        seats = _seats(
            present={
                PROCUREMENT_QUALITY_MEMBER: False,
                RELIABILITY_AND_RADIATION_MEMBER: False,
                CUSTOMER_REPRESENTATIVE: False,
            }
        )
        self.assertFalse(quorum_is_met(seats))


class VoteTests(unittest.TestCase):
    def test_a_unanimous_room_carries_the_whole_weight(self):
        self.assertAlmostEqual(approval_vote_share(_votes(), _seats()), 1.0, places=9)

    def test_an_abstention_withholds_support(self):
        seats = _seats()
        votes = _votes({CUSTOMER_REPRESENTATIVE: VOTE_ABSTAIN}, seats)
        self.assertAlmostEqual(approval_vote_share(votes, seats), 0.875, places=9)
        self.assertEqual(abstaining_roles(votes, seats), (CUSTOMER_REPRESENTATIVE,))

    def test_two_light_seats_against_land_exactly_on_the_threshold(self):
        seats = _seats()
        votes = _votes(
            {
                DESIGN_AUTHORITY_MEMBER: VOTE_AGAINST,
                PROCUREMENT_QUALITY_MEMBER: VOTE_AGAINST,
            },
            seats,
        )
        self.assertAlmostEqual(approval_vote_share(votes, seats), 0.75, places=9)
        self.assertEqual(
            dissenting_roles(votes, seats),
            (DESIGN_AUTHORITY_MEMBER, PROCUREMENT_QUALITY_MEMBER),
        )

    def test_an_empty_room_carries_nothing(self):
        seats = _seats(present={role: False for role in REQUIRED_BOARD_ROLES})
        self.assertAlmostEqual(approval_vote_share({}, seats), 0.0, places=9)

    def test_a_vote_from_an_absent_seat_refused(self):
        seats = _seats(present={DESIGN_AUTHORITY_MEMBER: False})
        votes = _votes({}, seats)
        votes[DESIGN_AUTHORITY_MEMBER] = VOTE_FOR
        with self.assertRaises(ValueError):
            validate_votes(votes, seats)

    def test_a_vote_from_an_unseated_role_refused(self):
        seats = _seats(drop=(CUSTOMER_REPRESENTATIVE,))
        votes = _votes({}, seats)
        votes[CUSTOMER_REPRESENTATIVE] = VOTE_FOR
        with self.assertRaises(ValueError):
            validate_votes(votes, seats)

    def test_a_present_seat_casting_no_vote_refused(self):
        seats = _seats()
        votes = _votes({}, seats)
        del votes[RELIABILITY_AND_RADIATION_MEMBER]
        with self.assertRaises(ValueError):
            validate_votes(votes, seats)

    def test_an_unrecognised_vote_refused(self):
        seats = _seats()
        votes = _votes({DESIGN_AUTHORITY_MEMBER: "maybe"}, seats)
        with self.assertRaises(ValueError):
            validate_votes(votes, seats)

    def test_non_mapping_votes_refused(self):
        with self.assertRaises(ValueError):
            validate_votes([VOTE_FOR], _seats())


class ConcurrenceTests(unittest.TestCase):
    def test_a_standard_part_needs_no_extra_concurrence(self):
        self.assertEqual(required_concurrences(STANDARD_QUALIFIED_PART), ())

    def test_an_upgraded_part_needs_two_concurrences(self):
        self.assertEqual(
            required_concurrences(UPGRADED_PART),
            (PARTS_ENGINEERING_MEMBER, RELIABILITY_AND_RADIATION_MEMBER),
        )

    def test_a_non_standard_part_also_needs_the_customer(self):
        self.assertIn(
            CUSTOMER_REPRESENTATIVE, required_concurrences(NON_STANDARD_PART)
        )

    def test_unrecognised_category_refused(self):
        with self.assertRaises(ValueError):
            required_concurrences("borrowed-from-a-drawer")

    def test_an_abstaining_customer_withholds_the_concurrence(self):
        seats = _seats()
        votes = _votes({CUSTOMER_REPRESENTATIVE: VOTE_ABSTAIN}, seats)
        self.assertEqual(
            missing_concurrences(NON_STANDARD_PART, votes, seats),
            (CUSTOMER_REPRESENTATIVE,),
        )

    def test_an_absent_customer_withholds_the_concurrence(self):
        seats = _seats(present={CUSTOMER_REPRESENTATIVE: False})
        votes = _votes({}, seats)
        self.assertEqual(
            missing_concurrences(NON_STANDARD_PART, votes, seats),
            (CUSTOMER_REPRESENTATIVE,),
        )


class RequestTests(unittest.TestCase):
    def test_a_request_reads_back(self):
        request = validate_part_request(_request())
        self.assertEqual(request["part_reference"], "PART-1188")
        self.assertEqual(request["category"], NON_STANDARD_PART)

    def test_a_request_naming_no_part_refused(self):
        with self.assertRaises(ValueError):
            validate_part_request(_request(part_reference="  "))

    def test_a_request_with_an_unrecognised_category_refused(self):
        with self.assertRaises(ValueError):
            validate_part_request(_request(category="something-convenient"))

    def test_a_request_with_no_votes_refused(self):
        request = _request()
        del request["votes"]
        with self.assertRaises(ValueError):
            validate_part_request(request)

    def test_non_boolean_dissent_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_part_request(_request(dissent_recorded="noted"))


class AdvisoryTests(unittest.TestCase):
    def test_an_approval_on_the_threshold_is_advised_on(self):
        seats = _seats()
        votes = _votes(
            {
                DESIGN_AUTHORITY_MEMBER: VOTE_AGAINST,
                PROCUREMENT_QUALITY_MEMBER: VOTE_AGAINST,
            },
            seats,
        )
        self.assertEqual(len(marginal_vote_advisory(votes, seats)), 1)

    def test_a_unanimous_approval_raises_no_advisory(self):
        self.assertEqual(marginal_vote_advisory(_votes(), _seats()), ())

    def test_a_refused_part_raises_no_advisory(self):
        seats = _seats()
        votes = _votes(
            {
                PRODUCT_ASSURANCE_CHAIR: VOTE_AGAINST,
                DESIGN_AUTHORITY_MEMBER: VOTE_AGAINST,
                PROCUREMENT_QUALITY_MEMBER: VOTE_AGAINST,
            },
            seats,
        )
        self.assertEqual(marginal_vote_advisory(votes, seats), ())


class VerdictTests(unittest.TestCase):
    def test_a_quorate_unanimous_board_approves_the_part(self):
        result = assess_parts_control_board(_case())
        self.assertEqual(result["verdict"], PART_USE_APPROVED)
        self.assertAlmostEqual(result["approval_vote_share"], 1.0, places=9)

    def test_an_absent_board_is_not_constituted(self):
        result = assess_parts_control_board({"board": None})
        self.assertEqual(result["verdict"], BOARD_NOT_CONSTITUTED)

    def test_a_board_missing_a_seat_is_not_constituted(self):
        seats = _seats(drop=(RELIABILITY_AND_RADIATION_MEMBER,))
        result = assess_parts_control_board(
            _case(board=_board(seats=seats))
        )
        self.assertEqual(result["verdict"], BOARD_NOT_CONSTITUTED)
        self.assertEqual(
            result["unseated_roles"], (RELIABILITY_AND_RADIATION_MEMBER,)
        )

    def test_a_board_with_no_reference_is_not_constituted(self):
        result = assess_parts_control_board(
            _case(board=_board(board_reference="   "))
        )
        self.assertEqual(result["verdict"], BOARD_NOT_CONSTITUTED)

    def test_a_meeting_without_the_chair_is_not_quorate(self):
        seats = _seats(present={PRODUCT_ASSURANCE_CHAIR: False})
        result = assess_parts_control_board(
            _case(
                board=_board(seats=seats),
                part_request=_request(votes=_votes({}, seats)),
            )
        )
        self.assertEqual(result["verdict"], BOARD_QUORUM_NOT_MET)

    def test_a_thin_room_is_not_quorate(self):
        seats = _seats(
            present={
                PROCUREMENT_QUALITY_MEMBER: False,
                RELIABILITY_AND_RADIATION_MEMBER: False,
                CUSTOMER_REPRESENTATIVE: False,
            }
        )
        result = assess_parts_control_board(
            _case(
                board=_board(seats=seats),
                part_request=_request(votes=_votes({}, seats)),
            )
        )
        self.assertEqual(result["verdict"], BOARD_QUORUM_NOT_MET)
        self.assertAlmostEqual(result["attendance_share"], 0.5, places=9)

    def test_a_decision_with_no_reference_is_not_recorded(self):
        result = assess_parts_control_board(
            _case(part_request=_request(decision_reference=""))
        )
        self.assertEqual(result["verdict"], DECISION_NOT_RECORDED)

    def test_unrecorded_dissent_leaves_the_decision_unrecorded(self):
        seats = _seats()
        votes = _votes({DESIGN_AUTHORITY_MEMBER: VOTE_AGAINST}, seats)
        result = assess_parts_control_board(
            _case(part_request=_request(votes=votes, dissent_recorded=False))
        )
        self.assertEqual(result["verdict"], DECISION_NOT_RECORDED)

    def test_recorded_dissent_lets_the_decision_stand(self):
        seats = _seats()
        votes = _votes({DESIGN_AUTHORITY_MEMBER: VOTE_AGAINST}, seats)
        result = assess_parts_control_board(
            _case(part_request=_request(votes=votes, dissent_recorded=True))
        )
        self.assertEqual(result["verdict"], PART_USE_APPROVED)
        self.assertEqual(result["dissenting_roles"], (DESIGN_AUTHORITY_MEMBER,))

    def test_a_non_standard_part_without_the_customer_stops_at_concurrence(self):
        seats = _seats()
        votes = _votes({CUSTOMER_REPRESENTATIVE: VOTE_ABSTAIN}, seats)
        result = assess_parts_control_board(
            _case(part_request=_request(votes=votes))
        )
        self.assertEqual(result["verdict"], CONCURRENCE_MISSING)
        self.assertEqual(
            result["missing_concurrences"], (CUSTOMER_REPRESENTATIVE,)
        )

    def test_an_upgraded_part_without_reliability_stops_at_concurrence(self):
        seats = _seats()
        votes = _votes({RELIABILITY_AND_RADIATION_MEMBER: VOTE_ABSTAIN}, seats)
        result = assess_parts_control_board(
            _case(part_request=_request(category=UPGRADED_PART, votes=votes))
        )
        self.assertEqual(result["verdict"], CONCURRENCE_MISSING)

    def test_a_standard_part_needs_only_the_board(self):
        seats = _seats()
        votes = _votes({CUSTOMER_REPRESENTATIVE: VOTE_ABSTAIN}, seats)
        result = assess_parts_control_board(
            _case(
                part_request=_request(
                    category=STANDARD_QUALIFIED_PART, votes=votes
                )
            )
        )
        self.assertEqual(result["verdict"], PART_USE_APPROVED)
        self.assertAlmostEqual(result["approval_vote_share"], 0.875, places=9)

    def test_a_share_below_the_threshold_refuses_the_part(self):
        seats = _seats()
        votes = _votes(
            {
                PRODUCT_ASSURANCE_CHAIR: VOTE_AGAINST,
                DESIGN_AUTHORITY_MEMBER: VOTE_AGAINST,
                PROCUREMENT_QUALITY_MEMBER: VOTE_AGAINST,
            },
            seats,
        )
        result = assess_parts_control_board(
            _case(
                part_request=_request(
                    category=STANDARD_QUALIFIED_PART,
                    votes=votes,
                    dissent_recorded=True,
                )
            )
        )
        self.assertEqual(result["verdict"], PART_USE_REFUSED)
        self.assertAlmostEqual(result["approval_vote_share"], 0.5, places=9)

    def test_a_share_exactly_on_the_threshold_carries_with_an_advisory(self):
        seats = _seats()
        votes = _votes(
            {
                DESIGN_AUTHORITY_MEMBER: VOTE_AGAINST,
                PROCUREMENT_QUALITY_MEMBER: VOTE_AGAINST,
            },
            seats,
        )
        result = assess_parts_control_board(
            _case(part_request=_request(votes=votes, dissent_recorded=True))
        )
        self.assertEqual(result["verdict"], PART_USE_APPROVED)
        self.assertAlmostEqual(result["approval_vote_share"], 0.75, places=9)
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_case_with_no_part_request_refused(self):
        case = _case()
        del case["part_request"]
        with self.assertRaises(ValueError):
            assess_parts_control_board(case)

    def test_a_board_with_no_seats_sequence_refused(self):
        board = _board()
        del board["seats"]
        with self.assertRaises(ValueError):
            assess_parts_control_board(_case(board=board))

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_parts_control_board(["board"])

    def test_non_mapping_board_refused(self):
        with self.assertRaises(ValueError):
            assess_parts_control_board(_case(board="PCB-2026-11"))


if __name__ == "__main__":
    unittest.main()
