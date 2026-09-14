"""Contract tests for the clause 6.1.3 lowest-class approval route.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused route
policy, an undeclared usage, no approval record at all, every one of the
referral conditions taken on its own, a referral earned and taken by the
delegate, an inquorate board, an approval standing on no evidence, a
record raised after the commitment, and a delegated approval reported to
the board too late.
"""

import unittest

from q6013_class_3_parts_control_board_logic import (
    APPROVAL_EVIDENCE_MISSING,
    APPROVAL_NOT_RECORDED,
    APPROVAL_RECORDED_AFTER_COMMITMENT,
    APPROVAL_ROUTE_SOUND,
    BOARD_QUORUM_NOT_MET,
    BOARD_REFERRAL_MISSED,
    BOARD_ROUTE,
    CRITICALITY_ORDER,
    DEFAULT_BOARD_POLICY,
    DELEGATED_APPROVAL_NOT_NOTIFIED,
    DELEGATED_ROUTE,
    MISSION_CRITICAL,
    NON_CRITICAL,
    REFERRAL_TRIGGER_NAMES,
    SAFETY_CRITICAL,
    TRIGGER_CRITICAL_FUNCTION,
    TRIGGER_DERATING_WAIVER,
    TRIGGER_LOT_NOT_TRACEABLE,
    TRIGGER_OPEN_ALERT,
    TRIGGER_OUTSIDE_CATALOGUE,
    TRIGGER_QUANTITY_ABOVE_THRESHOLD,
    TRIGGER_SINGLE_POINT_FAILURE,
    USAGE_NOT_DECLARED,
    assess_part_approval_route,
    board_referral_required,
    criticality_rank,
    notification_within_cadence,
    quorum_met,
    quorum_share,
    referral_triggers,
    route_advisories,
    validate_board_policy,
    validate_decision,
    validate_usage,
)


def _policy(**overrides):
    policy = dict(DEFAULT_BOARD_POLICY)
    policy.update(overrides)
    return policy


def _usage(**overrides):
    usage = {
        "part_reference": "CAP-0603-10U",
        "function_criticality": NON_CRITICAL,
        "in_approved_catalogue": True,
        "single_point_failure": False,
        "derating_waiver_needed": False,
        "open_alert": False,
        "lot_traceable": True,
        "installed_quantity": 12,
    }
    usage.update(overrides)
    return usage


def _board_decision(**overrides):
    decision = {
        "route": BOARD_ROUTE,
        "members_eligible": 5,
        "members_present": 4,
        "evidence_reference": "PCB3-DP-014",
        "recorded_before_commitment": True,
        "notification_delay_days": 0,
    }
    decision.update(overrides)
    return decision


def _delegated_decision(**overrides):
    decision = {
        "route": DELEGATED_ROUTE,
        "members_eligible": 0,
        "members_present": 0,
        "evidence_reference": "CAT-ENTRY-0091",
        "recorded_before_commitment": True,
        "notification_delay_days": 7,
    }
    decision.update(overrides)
    return decision


def _case(**overrides):
    case = {"usage": _usage(), "decision": _delegated_decision()}
    case.update(overrides)
    return case


class BoardPolicyValidation(unittest.TestCase):
    def test_default_policy_accepted(self):
        self.assertIs(validate_board_policy(DEFAULT_BOARD_POLICY), DEFAULT_BOARD_POLICY)

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(("min_quorum_share", 0.6))

    def test_zero_quorum_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(min_quorum_share=0.0))

    def test_quorum_band_wider_than_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(
                _policy(min_quorum_share=0.5, marginal_quorum_band=0.7)
            )

    def test_unrecognised_criticality_floor_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(referral_criticality_floor="quite-important"))

    def test_quantity_margin_wider_than_threshold_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(
                _policy(delegation_quantity_threshold=10, quantity_advisory_margin=20)
            )

    def test_negative_cadence_refused(self):
        with self.assertRaises(ValueError):
            validate_board_policy(_policy(notification_cadence_days=-1))


class UsageValidation(unittest.TestCase):
    def test_blank_part_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_usage(_usage(part_reference="   "))

    def test_unrecognised_criticality_refused(self):
        with self.assertRaises(ValueError):
            validate_usage(_usage(function_criticality="fairly-critical"))

    def test_non_boolean_catalogue_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_usage(_usage(in_approved_catalogue="yes"))

    def test_negative_quantity_refused(self):
        with self.assertRaises(ValueError):
            validate_usage(_usage(installed_quantity=-3))

    def test_criticality_rank_follows_the_scale(self):
        self.assertEqual(criticality_rank(NON_CRITICAL), 0)
        self.assertEqual(criticality_rank(SAFETY_CRITICAL), len(CRITICALITY_ORDER) - 1)


class ReferralTriggers(unittest.TestCase):
    def test_routine_catalogue_usage_fires_nothing(self):
        self.assertEqual(referral_triggers(_usage(), _policy()), ())
        self.assertFalse(board_referral_required(_usage(), _policy()))

    def test_part_outside_the_catalogue_fires(self):
        triggers = referral_triggers(_usage(in_approved_catalogue=False), _policy())
        self.assertEqual(triggers, (TRIGGER_OUTSIDE_CATALOGUE,))

    def test_criticality_at_the_floor_fires(self):
        triggers = referral_triggers(
            _usage(function_criticality=MISSION_CRITICAL),
            _policy(referral_criticality_floor=MISSION_CRITICAL),
        )
        self.assertEqual(triggers, (TRIGGER_CRITICAL_FUNCTION,))

    def test_criticality_below_the_floor_does_not_fire(self):
        triggers = referral_triggers(
            _usage(function_criticality=MISSION_CRITICAL),
            _policy(referral_criticality_floor=SAFETY_CRITICAL),
        )
        self.assertEqual(triggers, ())

    def test_single_point_failure_fires(self):
        self.assertIn(
            TRIGGER_SINGLE_POINT_FAILURE,
            referral_triggers(_usage(single_point_failure=True), _policy()),
        )

    def test_derating_waiver_fires(self):
        self.assertIn(
            TRIGGER_DERATING_WAIVER,
            referral_triggers(_usage(derating_waiver_needed=True), _policy()),
        )

    def test_open_alert_fires(self):
        self.assertIn(
            TRIGGER_OPEN_ALERT, referral_triggers(_usage(open_alert=True), _policy())
        )

    def test_untraceable_lot_fires(self):
        self.assertIn(
            TRIGGER_LOT_NOT_TRACEABLE,
            referral_triggers(_usage(lot_traceable=False), _policy()),
        )

    def test_quantity_above_the_threshold_fires(self):
        triggers = referral_triggers(
            _usage(installed_quantity=51), _policy(delegation_quantity_threshold=50)
        )
        self.assertEqual(triggers, (TRIGGER_QUANTITY_ABOVE_THRESHOLD,))

    def test_quantity_exactly_on_the_threshold_does_not_fire(self):
        triggers = referral_triggers(
            _usage(installed_quantity=50), _policy(delegation_quantity_threshold=50)
        )
        self.assertEqual(triggers, ())

    def test_several_conditions_are_all_named(self):
        triggers = referral_triggers(
            _usage(in_approved_catalogue=False, open_alert=True, lot_traceable=False),
            _policy(),
        )
        self.assertEqual(len(triggers), 3)
        for name in triggers:
            self.assertIn(name, REFERRAL_TRIGGER_NAMES)


class DecisionValidation(unittest.TestCase):
    def test_unrecognised_route_refused(self):
        with self.assertRaises(ValueError):
            validate_decision(_board_decision(route="corridor"))

    def test_board_decision_with_no_eligible_members_refused(self):
        with self.assertRaises(ValueError):
            validate_decision(_board_decision(members_eligible=0, members_present=0))

    def test_attendance_above_the_membership_refused(self):
        with self.assertRaises(ValueError):
            validate_decision(_board_decision(members_eligible=4, members_present=6))

    def test_non_boolean_commitment_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_decision(_board_decision(recorded_before_commitment="later"))

    def test_quorum_share_is_none_on_the_delegated_route(self):
        self.assertIsNone(quorum_share(_delegated_decision()))

    def test_quorum_share_is_the_attending_fraction(self):
        self.assertAlmostEqual(
            quorum_share(_board_decision(members_eligible=5, members_present=4)),
            0.8,
            places=9,
        )

    def test_quorum_exactly_on_the_floor_is_met(self):
        decision = _board_decision(members_eligible=5, members_present=3)
        self.assertAlmostEqual(quorum_share(decision), 0.6, places=9)
        self.assertTrue(quorum_met(decision, _policy(min_quorum_share=0.6)))

    def test_quorum_below_the_floor_is_not_met(self):
        decision = _board_decision(members_eligible=5, members_present=2)
        self.assertFalse(quorum_met(decision, _policy(min_quorum_share=0.6)))

    def test_delegated_route_is_never_inquorate(self):
        self.assertTrue(quorum_met(_delegated_decision(), _policy()))


class NotificationCadence(unittest.TestCase):
    def test_delegated_report_inside_the_cadence(self):
        self.assertTrue(
            notification_within_cadence(
                _delegated_decision(notification_delay_days=30),
                _policy(notification_cadence_days=30),
            )
        )

    def test_delegated_report_past_the_cadence(self):
        self.assertFalse(
            notification_within_cadence(
                _delegated_decision(notification_delay_days=31),
                _policy(notification_cadence_days=30),
            )
        )

    def test_board_route_carries_no_cadence_obligation(self):
        self.assertTrue(
            notification_within_cadence(
                _board_decision(notification_delay_days=900), _policy()
            )
        )


class RouteAdvisories(unittest.TestCase):
    def test_comfortable_board_session_raises_nothing(self):
        advisories = route_advisories(
            _usage(open_alert=True),
            _board_decision(members_eligible=5, members_present=5),
            _policy(min_quorum_share=0.6, marginal_quorum_band=0.05),
        )
        self.assertEqual(advisories, ())

    def test_bare_quorum_is_advised_on(self):
        advisories = route_advisories(
            _usage(open_alert=True),
            _board_decision(members_eligible=5, members_present=3),
            _policy(min_quorum_share=0.6, marginal_quorum_band=0.05),
        )
        self.assertEqual(len(advisories), 1)

    def test_quantity_near_the_delegation_cap_is_advised_on(self):
        advisories = route_advisories(
            _usage(installed_quantity=48),
            _delegated_decision(),
            _policy(delegation_quantity_threshold=50, quantity_advisory_margin=5),
        )
        self.assertEqual(len(advisories), 1)


class RouteVerdicts(unittest.TestCase):
    def test_absent_usage_is_not_declared(self):
        result = assess_part_approval_route(_case(usage=None))
        self.assertEqual(result["verdict"], USAGE_NOT_DECLARED)

    def test_absent_decision_is_not_recorded(self):
        result = assess_part_approval_route(_case(decision=None))
        self.assertEqual(result["verdict"], APPROVAL_NOT_RECORDED)

    def test_referral_earned_and_delegated_is_a_missed_referral(self):
        result = assess_part_approval_route(
            _case(usage=_usage(open_alert=True), decision=_delegated_decision()),
            _policy(),
        )
        self.assertEqual(result["verdict"], BOARD_REFERRAL_MISSED)
        self.assertIn(TRIGGER_OPEN_ALERT, result["referral_triggers"])

    def test_inquorate_board_cannot_decide(self):
        result = assess_part_approval_route(
            _case(
                usage=_usage(open_alert=True),
                decision=_board_decision(members_eligible=5, members_present=2),
            ),
            _policy(min_quorum_share=0.6),
        )
        self.assertEqual(result["verdict"], BOARD_QUORUM_NOT_MET)

    def test_approval_on_no_evidence_is_caught(self):
        result = assess_part_approval_route(
            _case(
                usage=_usage(open_alert=True),
                decision=_board_decision(evidence_reference=""),
            ),
            _policy(),
        )
        self.assertEqual(result["verdict"], APPROVAL_EVIDENCE_MISSING)

    def test_record_after_the_commitment_is_caught(self):
        result = assess_part_approval_route(
            _case(
                usage=_usage(open_alert=True),
                decision=_board_decision(recorded_before_commitment=False),
            ),
            _policy(),
        )
        self.assertEqual(result["verdict"], APPROVAL_RECORDED_AFTER_COMMITMENT)

    def test_late_delegated_report_is_caught(self):
        result = assess_part_approval_route(
            _case(decision=_delegated_decision(notification_delay_days=45)),
            _policy(notification_cadence_days=30),
        )
        self.assertEqual(result["verdict"], DELEGATED_APPROVAL_NOT_NOTIFIED)

    def test_sound_delegated_route_passes(self):
        result = assess_part_approval_route(_case(), _policy())
        self.assertEqual(result["verdict"], APPROVAL_ROUTE_SOUND)
        self.assertFalse(result["board_referral_required"])
        self.assertIsNone(result["quorum_share"])

    def test_sound_board_route_passes_with_its_share(self):
        result = assess_part_approval_route(
            _case(
                usage=_usage(in_approved_catalogue=False),
                decision=_board_decision(members_eligible=5, members_present=5),
            ),
            _policy(),
        )
        self.assertEqual(result["verdict"], APPROVAL_ROUTE_SOUND)
        self.assertAlmostEqual(result["quorum_share"], 1.0, places=9)

    def test_advisories_travel_with_a_passing_verdict(self):
        result = assess_part_approval_route(
            _case(usage=_usage(installed_quantity=49)),
            _policy(delegation_quantity_threshold=50, quantity_advisory_margin=5),
        )
        self.assertEqual(result["verdict"], APPROVAL_ROUTE_SOUND)
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_part_approval_route("usage")


if __name__ == "__main__":
    unittest.main()
