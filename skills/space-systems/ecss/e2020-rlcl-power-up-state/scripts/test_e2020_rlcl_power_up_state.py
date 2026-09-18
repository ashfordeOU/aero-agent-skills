"""Contract tests for the clause 5.2.7.1.1 retriggerable limiter power-up logic."""

import unittest

from e2020_rlcl_power_up_state_logic import (
    BROWN_OUT_RECOVERY,
    BUS_RESET_RECOVERY,
    COLD_START,
    COMMANDED_POWER_CYCLE,
    DEFAULT_RLCL_POWER_UP_POLICY,
    EVENT_COMMAND_DEPENDENT,
    EVENT_CONDUCTING_ON_ARRIVAL,
    EVENT_LATE_TO_CONDUCT,
    EVENT_NOT_CONDUCTING,
    EVENT_STATE_UNDECLARED,
    OUTPUT_CONDUCTING,
    OUTPUT_INDETERMINATE,
    OUTPUT_OFF,
    POWER_APPLICATION_EVENTS,
    POWER_UP_COMMAND_DEPENDENT,
    POWER_UP_CONFORMING,
    POWER_UP_LATE,
    POWER_UP_NONCONFORMING,
    POWER_UP_NOT_EVALUATED,
    POWER_UP_RETRIGGER_UNBOUNDED,
    UNDERVOLTAGE_RECOVERY,
    assess_retrigger_cycle,
    assess_rlcl_power_up,
    categorize_power_application_event,
    evaluate_power_application_event,
    retrigger_duty_fraction,
    retrigger_rate_hz,
    turn_on_latency_ms,
    validate_rlcl_power_up_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_RLCL_POWER_UP_POLICY)
    policy.update(overrides)
    return policy


def _event(kind, **overrides):
    event = {
        "kind": kind,
        "declared_state": OUTPUT_CONDUCTING,
        "bus_valid_dwell_ms": 2.0,
        "driver_delay_ms": 3.0,
        "requires_enable_command": False,
    }
    event.update(overrides)
    return event


def _cycle(**overrides):
    cycle = {"on_time_ms": 5.0, "off_time_ms": 20.0, "attempts": 3}
    cycle.update(overrides)
    return cycle


def _channel(**overrides):
    channel = {
        "events": [_event(kind) for kind in POWER_APPLICATION_EVENTS],
        "retrigger_cycle": _cycle(),
    }
    channel.update(overrides)
    return channel


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_rlcl_power_up_policy(DEFAULT_RLCL_POWER_UP_POLICY),
            DEFAULT_RLCL_POWER_UP_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_rlcl_power_up_policy("conducting")

    def test_a_dwell_larger_than_the_turn_on_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_rlcl_power_up_policy(
                _policy(max_bus_valid_dwell_ms=40.0, max_turn_on_delay_ms=20.0)
            )

    def test_a_dwell_equal_to_the_turn_on_budget_accepted(self):
        policy = _policy(max_bus_valid_dwell_ms=20.0, max_turn_on_delay_ms=20.0)
        self.assertIs(validate_rlcl_power_up_policy(policy), policy)

    def test_a_zero_turn_on_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_rlcl_power_up_policy(_policy(max_turn_on_delay_ms=0.0))

    def test_a_duty_ceiling_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_rlcl_power_up_policy(
                _policy(max_retrigger_duty_fraction=1.5)
            )

    def test_a_fractional_attempt_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_rlcl_power_up_policy(_policy(min_retrigger_attempts=2.5))

    def test_a_boolean_attempt_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_rlcl_power_up_policy(_policy(min_retrigger_attempts=True))


class EventVocabularyTests(unittest.TestCase):
    def test_every_known_event_round_trips(self):
        for kind in POWER_APPLICATION_EVENTS:
            self.assertEqual(categorize_power_application_event(kind), kind)

    def test_surrounding_whitespace_is_tolerated(self):
        self.assertEqual(
            categorize_power_application_event("  cold-start  "), COLD_START
        )

    def test_an_unrecognised_event_rejected(self):
        with self.assertRaises(ValueError):
            categorize_power_application_event("solar-eclipse-exit")

    def test_an_empty_event_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_power_application_event("   ")

    def test_a_non_string_event_kind_rejected(self):
        with self.assertRaises(ValueError):
            categorize_power_application_event(7)


class LatencyTests(unittest.TestCase):
    def test_latency_is_the_sum_of_dwell_and_driver_delay(self):
        self.assertAlmostEqual(turn_on_latency_ms(2.0, 3.0), 5.0, places=9)

    def test_a_zero_dwell_is_allowed(self):
        self.assertAlmostEqual(turn_on_latency_ms(0.0, 4.5), 4.5, places=9)

    def test_a_negative_driver_delay_rejected(self):
        with self.assertRaises(ValueError):
            turn_on_latency_ms(1.0, -0.5)

    def test_a_non_numeric_dwell_rejected(self):
        with self.assertRaises(ValueError):
            turn_on_latency_ms("prompt", 1.0)


class EventEvaluationTests(unittest.TestCase):
    def test_a_prompt_unconditional_turn_on_is_conducting_on_arrival(self):
        record = evaluate_power_application_event(_event(COLD_START))
        self.assertEqual(record["category"], EVENT_CONDUCTING_ON_ARRIVAL)
        self.assertAlmostEqual(record["latency_ms"], 5.0, places=9)

    def test_a_latency_exactly_on_the_budget_still_conducts_in_time(self):
        record = evaluate_power_application_event(
            _event(COLD_START, bus_valid_dwell_ms=5.0, driver_delay_ms=15.0)
        )
        self.assertEqual(record["category"], EVENT_CONDUCTING_ON_ARRIVAL)
        self.assertAlmostEqual(
            record["latency_ms"],
            float(DEFAULT_RLCL_POWER_UP_POLICY["max_turn_on_delay_ms"]),
            places=9,
        )

    def test_a_latency_past_the_budget_is_late(self):
        record = evaluate_power_application_event(
            _event(COLD_START, driver_delay_ms=50.0)
        )
        self.assertEqual(record["category"], EVENT_LATE_TO_CONDUCT)

    def test_an_enable_command_dependency_outranks_a_prompt_latency(self):
        record = evaluate_power_application_event(
            _event(BROWN_OUT_RECOVERY, requires_enable_command=True)
        )
        self.assertEqual(record["category"], EVENT_COMMAND_DEPENDENT)

    def test_an_output_off_power_up_is_not_conducting(self):
        record = evaluate_power_application_event(
            _event(UNDERVOLTAGE_RECOVERY, declared_state=OUTPUT_OFF)
        )
        self.assertEqual(record["category"], EVENT_NOT_CONDUCTING)

    def test_an_indeterminate_state_reads_as_undeclared(self):
        record = evaluate_power_application_event(
            _event(BUS_RESET_RECOVERY, declared_state=OUTPUT_INDETERMINATE)
        )
        self.assertEqual(record["category"], EVENT_STATE_UNDECLARED)

    def test_a_missing_state_reads_as_undeclared_and_carries_no_latency(self):
        record = evaluate_power_application_event(
            {"kind": COMMANDED_POWER_CYCLE, "declared_state": None}
        )
        self.assertEqual(record["category"], EVENT_STATE_UNDECLARED)
        self.assertIsNone(record["latency_ms"])

    def test_an_unrecognised_declared_state_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_power_application_event(
                _event(COLD_START, declared_state="output-maybe")
            )

    def test_a_non_mapping_event_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_power_application_event([COLD_START])


class RetriggerCycleTests(unittest.TestCase):
    def test_duty_fraction_is_the_conducting_share_of_the_cycle(self):
        self.assertAlmostEqual(retrigger_duty_fraction(5.0, 15.0), 0.25, places=9)

    def test_rate_is_one_over_the_cycle_period(self):
        self.assertAlmostEqual(retrigger_rate_hz(5.0, 15.0), 50.0, places=9)

    def test_a_zero_off_time_rejected_by_the_duty_calculation(self):
        with self.assertRaises(ValueError):
            retrigger_duty_fraction(5.0, 0.0)

    def test_a_bounded_cycle_is_bounded(self):
        cycle = assess_retrigger_cycle(_cycle())
        self.assertTrue(cycle["bounded"])
        self.assertEqual(cycle["findings"], [])
        self.assertAlmostEqual(cycle["duty_fraction"], 0.2, places=9)

    def test_a_duty_exactly_on_the_ceiling_is_still_bounded(self):
        cycle = assess_retrigger_cycle(
            _cycle(on_time_ms=6.0, off_time_ms=4.0),
            _policy(max_retrigger_duty_fraction=0.6, max_retrigger_rate_hz=200.0),
        )
        self.assertAlmostEqual(cycle["duty_fraction"], 0.6, places=9)
        self.assertTrue(cycle["bounded"])

    def test_a_short_rest_between_attempts_is_reported(self):
        cycle = assess_retrigger_cycle(_cycle(on_time_ms=1.0, off_time_ms=0.2))
        self.assertFalse(cycle["bounded"])
        self.assertTrue(any("rests" in note for note in cycle["findings"]))

    def test_a_free_running_cycle_is_reported_as_an_oscillator(self):
        cycle = assess_retrigger_cycle(
            _cycle(on_time_ms=1.0, off_time_ms=1.5),
            _policy(min_retrigger_off_time_ms=1.0, max_retrigger_rate_hz=200.0),
        )
        self.assertFalse(cycle["bounded"])
        self.assertTrue(any("Hz" in note for note in cycle["findings"]))

    def test_a_single_attempt_is_not_retriggerable_behaviour(self):
        cycle = assess_retrigger_cycle(_cycle(attempts=1))
        self.assertFalse(cycle["bounded"])

    def test_a_zero_attempt_count_rejected(self):
        with self.assertRaises(ValueError):
            assess_retrigger_cycle(_cycle(attempts=0))

    def test_a_missing_cycle_rejected(self):
        with self.assertRaises(ValueError):
            assess_retrigger_cycle(None)


class ChannelAssessmentTests(unittest.TestCase):
    def test_a_compliant_channel_conforms(self):
        result = assess_rlcl_power_up(_channel())
        self.assertEqual(result["verdict"], POWER_UP_CONFORMING)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["uncovered_events"], [])

    def test_an_uncovered_occasion_leaves_the_channel_unevaluated(self):
        channel = _channel(
            events=[_event(kind) for kind in POWER_APPLICATION_EVENTS[:-1]]
        )
        result = assess_rlcl_power_up(channel)
        self.assertEqual(result["verdict"], POWER_UP_NOT_EVALUATED)
        self.assertEqual(
            result["uncovered_events"], [POWER_APPLICATION_EVENTS[-1]]
        )

    def test_an_undeclared_occasion_outranks_a_wrong_one(self):
        events = [_event(kind) for kind in POWER_APPLICATION_EVENTS]
        events[1]["declared_state"] = OUTPUT_INDETERMINATE
        events[2]["declared_state"] = OUTPUT_OFF
        result = assess_rlcl_power_up(_channel(events=events))
        self.assertEqual(result["verdict"], POWER_UP_NOT_EVALUATED)

    def test_a_command_dependency_outranks_a_dark_occasion(self):
        events = [_event(kind) for kind in POWER_APPLICATION_EVENTS]
        events[1]["requires_enable_command"] = True
        events[2]["declared_state"] = OUTPUT_OFF
        result = assess_rlcl_power_up(_channel(events=events))
        self.assertEqual(result["verdict"], POWER_UP_COMMAND_DEPENDENT)

    def test_a_dark_occasion_is_nonconforming(self):
        events = [_event(kind) for kind in POWER_APPLICATION_EVENTS]
        events[3]["declared_state"] = OUTPUT_OFF
        result = assess_rlcl_power_up(_channel(events=events))
        self.assertEqual(result["verdict"], POWER_UP_NONCONFORMING)

    def test_a_late_occasion_is_reported_as_late(self):
        events = [_event(kind) for kind in POWER_APPLICATION_EVENTS]
        events[0]["driver_delay_ms"] = 80.0
        result = assess_rlcl_power_up(_channel(events=events))
        self.assertEqual(result["verdict"], POWER_UP_LATE)

    def test_an_unbounded_retrigger_cycle_is_caught_on_a_clean_power_up(self):
        result = assess_rlcl_power_up(
            _channel(retrigger_cycle=_cycle(on_time_ms=1.0, off_time_ms=0.1))
        )
        self.assertEqual(result["verdict"], POWER_UP_RETRIGGER_UNBOUNDED)

    def test_a_repeated_occasion_rejected(self):
        events = [_event(kind) for kind in POWER_APPLICATION_EVENTS]
        events.append(_event(COLD_START))
        with self.assertRaises(ValueError):
            assess_rlcl_power_up(_channel(events=events))

    def test_a_channel_with_no_events_rejected(self):
        with self.assertRaises(ValueError):
            assess_rlcl_power_up(_channel(events=[]))

    def test_a_non_mapping_channel_rejected(self):
        with self.assertRaises(ValueError):
            assess_rlcl_power_up("channel-a")

    def test_every_finding_is_a_readable_sentence(self):
        events = [_event(kind) for kind in POWER_APPLICATION_EVENTS]
        events[0]["declared_state"] = OUTPUT_OFF
        result = assess_rlcl_power_up(_channel(events=events))
        self.assertTrue(result["findings"])
        for note in result["findings"]:
            self.assertIsInstance(note, str)
            self.assertGreater(len(note), 20)


if __name__ == "__main__":
    unittest.main()
