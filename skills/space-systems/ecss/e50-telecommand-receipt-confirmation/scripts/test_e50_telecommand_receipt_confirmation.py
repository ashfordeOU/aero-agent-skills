"""Contract tests for the clause 5.6.14.8 telecommand receipt confirmation logic."""

import unittest

from e50_telecommand_receipt_confirmation_logic import (
    ACCEPTED,
    ACTION_ESCALATE,
    ACTION_NONE,
    ACTION_RETRANSMIT,
    CONFIRMED,
    CONFIRMED_LATE,
    DEADLINE_UNACHIEVABLE,
    DUPLICATE,
    ESCALATION_REQUIRED,
    HEALTHY,
    PENDING,
    RETRANSMISSION_REQUIRED,
    TIMED_OUT,
    UNSOLICITED,
    assess_confirmation_window,
    confirmation_latency_s,
    deadline_is_achievable,
    grade_command,
    grade_confirmation,
    minimum_confirmation_deadline_s,
    next_action,
    validate_attempts,
    validate_commands,
    validate_instant,
    validate_span,
)

RTLT = 2.0
PROCESSING = 0.5
MARGIN = 0.5
MINIMUM = 3.0
DEADLINE = 4.0
NOW = 12.0
LIMIT = 3

WINDOW = [
    {"id": "tc1", "sent_at_s": 0.0, "confirmed_at_s": 2.5},
    {"id": "tc2", "sent_at_s": 0.0, "confirmed_at_s": 5.0},
    {"id": "tc3", "sent_at_s": 10.0},
    {"id": "tc4", "sent_at_s": 0.0},
    {"id": "tc5", "sent_at_s": 0.0, "attempts": 4},
]


def assess(**overrides):
    args = dict(
        commands=WINDOW,
        now_s=NOW,
        round_trip_light_time_s=RTLT,
        onboard_processing_s=PROCESSING,
        margin_s=MARGIN,
        configured_deadline_s=DEADLINE,
        retransmission_limit=LIMIT,
    )
    args.update(overrides)
    return assess_confirmation_window(**args)


class ValidationTests(unittest.TestCase):
    def test_good_window_validates(self):
        self.assertEqual(len(validate_commands(WINDOW)), 5)

    def test_repeated_command_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_commands([{"id": "tc1", "sent_at_s": 0.0}, {"id": "tc1", "sent_at_s": 1.0}])

    def test_command_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_commands([{"sent_at_s": 0.0}])

    def test_confirmation_before_dispatch_rejected(self):
        with self.assertRaises(ValueError):
            validate_commands([{"id": "tc1", "sent_at_s": 5.0, "confirmed_at_s": 1.0}])

    def test_zero_attempts_rejected(self):
        with self.assertRaises(ValueError):
            validate_attempts(0)

    def test_boolean_attempts_rejected(self):
        with self.assertRaises(ValueError):
            validate_attempts(True)

    def test_negative_span_rejected(self):
        with self.assertRaises(ValueError):
            validate_span(-1.0)

    def test_infinite_instant_rejected(self):
        with self.assertRaises(ValueError):
            validate_instant(float("inf"))

    def test_non_list_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_commands({"id": "tc1", "sent_at_s": 0.0})


class DeadlineTests(unittest.TestCase):
    def test_minimum_deadline_sums_the_geometry(self):
        self.assertAlmostEqual(
            minimum_confirmation_deadline_s(RTLT, PROCESSING, MARGIN), MINIMUM, places=9
        )

    def test_a_longer_deadline_is_achievable(self):
        self.assertTrue(deadline_is_achievable(DEADLINE, MINIMUM))

    def test_a_deadline_exactly_at_the_minimum_is_achievable(self):
        self.assertTrue(deadline_is_achievable(MINIMUM, MINIMUM))

    def test_a_shorter_deadline_is_not(self):
        self.assertFalse(deadline_is_achievable(2.0, MINIMUM))

    def test_latency_is_the_gap_between_dispatch_and_confirmation(self):
        self.assertAlmostEqual(confirmation_latency_s(1.0, 3.5), 2.5, places=9)

    def test_latency_before_dispatch_rejected(self):
        with self.assertRaises(ValueError):
            confirmation_latency_s(3.5, 1.0)


class GradeCommandTests(unittest.TestCase):
    def test_prompt_confirmation_is_confirmed(self):
        record = {"sent_at_s": 0.0, "confirmed_at_s": 2.5}
        self.assertEqual(grade_command(record, NOW, DEADLINE), CONFIRMED)

    def test_confirmation_exactly_on_the_deadline_is_on_time(self):
        record = {"sent_at_s": 0.0, "confirmed_at_s": DEADLINE}
        self.assertEqual(grade_command(record, NOW, DEADLINE), CONFIRMED)

    def test_confirmation_after_the_deadline_is_late_not_successful(self):
        record = {"sent_at_s": 0.0, "confirmed_at_s": 5.0}
        self.assertEqual(grade_command(record, NOW, DEADLINE), CONFIRMED_LATE)

    def test_young_unconfirmed_command_is_pending(self):
        record = {"sent_at_s": 10.0, "confirmed_at_s": None}
        self.assertEqual(grade_command(record, NOW, DEADLINE), PENDING)

    def test_command_exactly_at_the_deadline_is_still_pending(self):
        record = {"sent_at_s": NOW - DEADLINE, "confirmed_at_s": None}
        self.assertEqual(grade_command(record, NOW, DEADLINE), PENDING)

    def test_old_unconfirmed_command_has_timed_out(self):
        record = {"sent_at_s": 0.0, "confirmed_at_s": None}
        self.assertEqual(grade_command(record, NOW, DEADLINE), TIMED_OUT)

    def test_a_command_sent_in_the_future_rejected(self):
        record = {"sent_at_s": 20.0, "confirmed_at_s": None}
        with self.assertRaises(ValueError):
            grade_command(record, NOW, DEADLINE)


class ActionTests(unittest.TestCase):
    def test_confirmed_command_needs_nothing(self):
        self.assertEqual(next_action(CONFIRMED, 1, LIMIT), ACTION_NONE)

    def test_pending_command_needs_nothing_yet(self):
        self.assertEqual(next_action(PENDING, 1, LIMIT), ACTION_NONE)

    def test_late_confirmation_needs_no_further_send(self):
        self.assertEqual(next_action(CONFIRMED_LATE, 2, LIMIT), ACTION_NONE)

    def test_timed_out_command_inside_the_budget_is_retransmitted(self):
        self.assertEqual(next_action(TIMED_OUT, 1, LIMIT), ACTION_RETRANSMIT)

    def test_timed_out_command_at_the_budget_is_escalated(self):
        self.assertEqual(next_action(TIMED_OUT, 4, LIMIT), ACTION_ESCALATE)

    def test_negative_retransmission_limit_rejected(self):
        with self.assertRaises(ValueError):
            next_action(TIMED_OUT, 1, -1)


class ConfirmationSourceTests(unittest.TestCase):
    def test_expected_confirmation_is_accepted(self):
        self.assertEqual(grade_confirmation("tc4", ["tc4", "tc5"], []), ACCEPTED)

    def test_repeated_confirmation_is_a_duplicate(self):
        self.assertEqual(grade_confirmation("tc4", ["tc4"], ["tc4"]), DUPLICATE)

    def test_confirmation_for_a_command_never_sent_is_unsolicited(self):
        self.assertEqual(grade_confirmation("tc9", ["tc4"], []), UNSOLICITED)

    def test_empty_confirmation_id_rejected(self):
        with self.assertRaises(ValueError):
            grade_confirmation("", ["tc4"], [])


class AssessTests(unittest.TestCase):
    def test_window_counts_every_state(self):
        counts = assess()["counts"]
        self.assertEqual(counts[CONFIRMED], 1)
        self.assertEqual(counts[CONFIRMED_LATE], 1)
        self.assertEqual(counts[PENDING], 1)
        self.assertEqual(counts[TIMED_OUT], 2)

    def test_escalation_outranks_retransmission(self):
        self.assertEqual(assess()["verdict"], ESCALATION_REQUIRED)

    def test_a_clean_window_is_healthy(self):
        clean = [{"id": "tc1", "sent_at_s": 0.0, "confirmed_at_s": 2.5}]
        result = assess(commands=clean)
        self.assertEqual(result["verdict"], HEALTHY)
        self.assertEqual(result["findings"], [])

    def test_a_timed_out_command_alone_asks_for_retransmission(self):
        stale = [{"id": "tc4", "sent_at_s": 0.0}]
        result = assess(commands=stale)
        self.assertEqual(result["verdict"], RETRANSMISSION_REQUIRED)
        self.assertEqual(result["retransmit_ids"], ["tc4"])

    def test_an_unachievable_deadline_outranks_every_command_state(self):
        result = assess(configured_deadline_s=1.0)
        self.assertEqual(result["verdict"], DEADLINE_UNACHIEVABLE)

    def test_unachievable_deadline_states_the_minimum(self):
        findings = assess(configured_deadline_s=1.0)["findings"]
        self.assertTrue(any("shortest this geometry can meet" in f for f in findings))

    def test_stated_minimum_deadline_is_itself_achievable(self):
        minimum = assess(configured_deadline_s=1.0)["minimum_deadline_s"]
        self.assertTrue(assess(configured_deadline_s=minimum)["deadline_achievable"])

    def test_late_confirmation_warns_about_double_execution(self):
        findings = assess()["findings"]
        self.assertTrue(any("acted on" in f and "twice" in f for f in findings))

    def test_escalation_blames_the_link_not_the_command(self):
        findings = assess()["findings"]
        self.assertTrue(any("the link rather than the" in f for f in findings))

    def test_the_deadline_defaults_to_the_geometry_minimum(self):
        result = assess(configured_deadline_s=None)
        self.assertAlmostEqual(result["deadline_s"], MINIMUM, places=9)

    def test_worst_latency_is_reported(self):
        self.assertAlmostEqual(assess()["worst_latency_s"], 5.0, places=9)

    def test_a_window_with_no_confirmations_has_no_worst_latency(self):
        self.assertIsNone(assess(commands=[{"id": "tc4", "sent_at_s": 0.0}])["worst_latency_s"])

    def test_every_command_gets_an_outcome(self):
        outcomes = assess()["outcomes"]
        self.assertEqual([o["id"] for o in outcomes], ["tc1", "tc2", "tc3", "tc4", "tc5"])

    def test_outcome_carries_the_age_of_the_command(self):
        outcomes = assess()["outcomes"]
        self.assertAlmostEqual(outcomes[2]["age_s"], 2.0, places=9)

    def test_raising_the_limit_turns_escalation_into_retransmission(self):
        self.assertEqual(assess(retransmission_limit=9)["verdict"], RETRANSMISSION_REQUIRED)

    def test_bad_now_rejected(self):
        with self.assertRaises(ValueError):
            assess(now_s="12")


if __name__ == "__main__":
    unittest.main()
