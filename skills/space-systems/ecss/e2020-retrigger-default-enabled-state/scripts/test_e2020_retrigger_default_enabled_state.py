"""Contract tests for the clause 5.2.6.3.1 retrigger power-up default state.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: an undeclared default, a
declared default that is not the active one, a restart the evidence never
covered, a restart that carries the pre-event state across instead of
defaulting, and a default that only comes into force after a load could
already have been enabled.
"""

import unittest

from e2020_retrigger_default_enabled_state_logic import (
    DEFAULT_ESTABLISHED_TOO_LATE,
    DEFAULT_RESET_POLICY,
    DEFAULT_STATE_ENABLED_EVERYWHERE,
    DEFAULT_STATE_NOT_DECLARED,
    DEFAULT_STATE_NOT_ENABLED,
    RESET_COVERAGE_INCOMPLETE,
    RETRIGGER_DISABLED,
    RETRIGGER_ENABLED,
    assess_retrigger_default_state,
    default_state_advisories,
    establishment_in_time,
    establishment_margin_ms,
    events_not_defaulting_enabled,
    events_retaining_commanded_state,
    missing_required_events,
    restart_event_records,
    slowest_establishment,
    validate_reset_policy,
    validate_restart_event,
)


def _policy(**overrides):
    policy = dict(DEFAULT_RESET_POLICY)
    policy.update(overrides)
    return policy


def _event(name, **overrides):
    event = {
        "name": name,
        "retrigger_state_after": RETRIGGER_ENABLED,
        "commanded_state_before": RETRIGGER_DISABLED,
        "state_retained_from_before": False,
        "time_to_default_ms": 18.0,
    }
    event.update(overrides)
    return event


def _events():
    return [
        _event("cold-power-up", time_to_default_ms=30.0),
        _event("warm-reset", time_to_default_ms=12.0),
        _event("watchdog-reset", time_to_default_ms=18.0),
        _event(
            "undervoltage-recovery",
            commanded_state_before=RETRIGGER_ENABLED,
            time_to_default_ms=18.0,
        ),
    ]


def _case(**overrides):
    case = {
        "limiter_id": "rcl-b7",
        "declared_default_state": RETRIGGER_ENABLED,
        "restart_events": _events(),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_reset_policy(DEFAULT_RESET_POLICY), DEFAULT_RESET_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_reset_policy("required_events")

    def test_empty_required_event_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_reset_policy(_policy(required_events=()))

    def test_repeated_required_event_rejected(self):
        with self.assertRaises(ValueError):
            validate_reset_policy(
                _policy(required_events=("warm-reset", "warm-reset"))
            )

    def test_non_positive_load_enable_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_reset_policy(_policy(earliest_load_enable_ms=0.0))

    def test_advisory_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_reset_policy(_policy(establishment_advisory_fraction=1.2))


class EventValidationTests(unittest.TestCase):
    def test_good_event_validates(self):
        record = validate_restart_event(_event("warm-reset"))
        self.assertEqual(record["name"], "warm-reset")
        self.assertEqual(record["retrigger_state_after"], RETRIGGER_ENABLED)

    def test_non_mapping_event_rejected(self):
        with self.assertRaises(ValueError):
            validate_restart_event(["warm-reset"])

    def test_blank_event_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_restart_event(_event("   "))

    def test_unknown_retrigger_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_restart_event(_event("warm-reset", retrigger_state_after="armed"))

    def test_non_boolean_retention_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_restart_event(
                _event("warm-reset", state_retained_from_before="no")
            )

    def test_negative_establishment_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_restart_event(_event("warm-reset", time_to_default_ms=-1.0))

    def test_absent_pre_event_state_is_allowed(self):
        record = validate_restart_event(
            _event("warm-reset", commanded_state_before=None)
        )
        self.assertIsNone(record["commanded_state_before"])

    def test_empty_event_set_rejected(self):
        with self.assertRaises(ValueError):
            restart_event_records([])

    def test_duplicate_event_name_rejected(self):
        with self.assertRaises(ValueError):
            restart_event_records([_event("warm-reset"), _event("warm-reset")])

    def test_records_keep_record_order(self):
        records = restart_event_records(_events())
        self.assertEqual(records[0]["name"], "cold-power-up")
        self.assertEqual(len(records), 4)


class CoverageTests(unittest.TestCase):
    def test_full_coverage_reports_nothing_missing(self):
        self.assertEqual(missing_required_events(restart_event_records(_events())), ())

    def test_cold_power_up_only_leaves_three_restarts_uncovered(self):
        records = restart_event_records([_event("cold-power-up")])
        self.assertEqual(len(missing_required_events(records)), 3)

    def test_extra_event_beyond_the_required_set_is_not_a_finding(self):
        records = restart_event_records(_events() + [_event("ground-commanded-reset")])
        self.assertEqual(missing_required_events(records), ())


class StateTests(unittest.TestCase):
    def test_all_events_default_enabled(self):
        self.assertEqual(
            events_not_defaulting_enabled(restart_event_records(_events())), ()
        )

    def test_a_disabled_restart_is_named(self):
        events = _events()
        events[2]["retrigger_state_after"] = RETRIGGER_DISABLED
        records = restart_event_records(events)
        self.assertEqual(events_not_defaulting_enabled(records), ("watchdog-reset",))

    def test_no_event_retains_the_pre_event_state(self):
        self.assertEqual(
            events_retaining_commanded_state(restart_event_records(_events())), ()
        )

    def test_a_retained_state_is_named_even_when_it_is_enabled(self):
        events = _events()
        events[1]["state_retained_from_before"] = True
        records = restart_event_records(events)
        self.assertEqual(events_retaining_commanded_state(records), ("warm-reset",))


class EstablishmentTests(unittest.TestCase):
    def test_slowest_event_is_the_cold_power_up(self):
        slowest = slowest_establishment(restart_event_records(_events()))
        self.assertEqual(slowest["name"], "cold-power-up")

    def test_margin_against_the_load_enable_window(self):
        records = restart_event_records(_events())
        self.assertAlmostEqual(establishment_margin_ms(records), 20.0, places=9)

    def test_establishment_exactly_on_the_window_is_admissible(self):
        events = _events()
        events[0]["time_to_default_ms"] = 50.0
        records = restart_event_records(events)
        self.assertAlmostEqual(establishment_margin_ms(records), 0.0, places=9)
        self.assertTrue(establishment_in_time(records))

    def test_establishment_past_the_window_is_not_admissible(self):
        events = _events()
        events[0]["time_to_default_ms"] = 64.0
        records = restart_event_records(events)
        self.assertFalse(establishment_in_time(records))

    def test_empty_records_have_no_slowest_event(self):
        with self.assertRaises(ValueError):
            slowest_establishment(())


class AdvisoryTests(unittest.TestCase):
    def test_comfortable_design_raises_no_advisory(self):
        self.assertEqual(default_state_advisories(restart_event_records(_events())), ())

    def test_establishment_inside_the_advisory_band_is_named(self):
        events = _events()
        events[0]["time_to_default_ms"] = 45.0
        advisories = default_state_advisories(restart_event_records(events))
        self.assertEqual(len(advisories), 1)
        self.assertIn("advisory band", advisories[0])

    def test_a_missing_pre_event_state_is_named(self):
        events = _events()
        events[1]["commanded_state_before"] = None
        advisories = default_state_advisories(restart_event_records(events))
        self.assertEqual(len(advisories), 1)
        self.assertIn("no pre-event commanded state", advisories[0])

    def test_never_entering_from_disabled_is_named(self):
        events = [
            _event(event["name"], commanded_state_before=RETRIGGER_ENABLED)
            for event in _events()
        ]
        advisories = default_state_advisories(restart_event_records(events))
        self.assertEqual(len(advisories), 1)
        self.assertIn("commanded off", advisories[0])


class AssessmentTests(unittest.TestCase):
    def test_compliant_design_passes(self):
        result = assess_retrigger_default_state(_case())
        self.assertEqual(result["verdict"], DEFAULT_STATE_ENABLED_EVERYWHERE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["advisories"], [])

    def test_undeclared_default_closes_the_assessment(self):
        case = _case()
        del case["declared_default_state"]
        result = assess_retrigger_default_state(case)
        self.assertEqual(result["verdict"], DEFAULT_STATE_NOT_DECLARED)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_declared_disabled_default_fails(self):
        result = assess_retrigger_default_state(
            _case(declared_default_state=RETRIGGER_DISABLED)
        )
        self.assertEqual(result["verdict"], DEFAULT_STATE_NOT_ENABLED)

    def test_partial_restart_evidence_closes_on_coverage(self):
        result = assess_retrigger_default_state(
            _case(restart_events=[_event("cold-power-up")])
        )
        self.assertEqual(result["verdict"], RESET_COVERAGE_INCOMPLETE)
        self.assertEqual(len(result["missing_events"]), 3)

    def test_a_restart_coming_up_disabled_fails(self):
        events = _events()
        events[2]["retrigger_state_after"] = RETRIGGER_DISABLED
        result = assess_retrigger_default_state(_case(restart_events=events))
        self.assertEqual(result["verdict"], DEFAULT_STATE_NOT_ENABLED)
        self.assertEqual(
            result["events_not_defaulting_enabled"], ("watchdog-reset",)
        )

    def test_a_retained_state_fails_even_when_enabled(self):
        events = _events()
        events[1]["state_retained_from_before"] = True
        result = assess_retrigger_default_state(_case(restart_events=events))
        self.assertEqual(result["verdict"], DEFAULT_STATE_NOT_ENABLED)
        self.assertIn("not a", result["findings"][0])

    def test_every_offending_restart_is_named_not_only_the_first(self):
        events = _events()
        events[1]["state_retained_from_before"] = True
        events[2]["retrigger_state_after"] = RETRIGGER_DISABLED
        result = assess_retrigger_default_state(_case(restart_events=events))
        self.assertEqual(len(result["findings"]), 2)

    def test_a_late_default_closes_on_the_window_verdict(self):
        events = _events()
        events[0]["time_to_default_ms"] = 64.0
        result = assess_retrigger_default_state(_case(restart_events=events))
        self.assertEqual(result["verdict"], DEFAULT_ESTABLISHED_TOO_LATE)
        self.assertAlmostEqual(result["establishment_margin_ms"], -14.0, places=9)

    def test_a_default_landing_on_the_window_still_passes(self):
        events = _events()
        events[0]["time_to_default_ms"] = 50.0
        result = assess_retrigger_default_state(_case(restart_events=events))
        self.assertEqual(result["verdict"], DEFAULT_STATE_ENABLED_EVERYWHERE)
        self.assertAlmostEqual(result["establishment_margin_ms"], 0.0, places=9)

    def test_advisories_do_not_move_the_verdict(self):
        events = _events()
        events[0]["time_to_default_ms"] = 45.0
        result = assess_retrigger_default_state(_case(restart_events=events))
        self.assertEqual(result["verdict"], DEFAULT_STATE_ENABLED_EVERYWHERE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_the_slowest_restart_is_reported(self):
        result = assess_retrigger_default_state(_case())
        self.assertEqual(result["slowest_event"], "cold-power-up")
        self.assertAlmostEqual(result["slowest_establishment_ms"], 30.0, places=9)

    def test_a_widened_window_can_admit_a_slower_boot(self):
        events = _events()
        events[0]["time_to_default_ms"] = 64.0
        result = assess_retrigger_default_state(
            _case(restart_events=events), _policy(earliest_load_enable_ms=90.0)
        )
        self.assertEqual(result["verdict"], DEFAULT_STATE_ENABLED_EVERYWHERE)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_retrigger_default_state(["declared_default_state"])

    def test_missing_restart_evidence_rejected(self):
        case = _case()
        del case["restart_events"]
        with self.assertRaises(ValueError):
            assess_retrigger_default_state(case)


if __name__ == "__main__":
    unittest.main()
