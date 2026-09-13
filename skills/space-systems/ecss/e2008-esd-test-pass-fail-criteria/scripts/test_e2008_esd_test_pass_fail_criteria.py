"""Contract tests for the clause 5.5.1.5.2 coupon discharge pass-decision logic."""

import unittest

from e2008_esd_test_pass_fail_criteria_logic import (
    COMPARISON_ABSOLUTE_TOLERANCE,
    TERMINATION_MODES,
    assess_esd_pass_criteria,
    categorize_event,
    categorize_events,
    count_sustained,
    evaluate_condition_coverage,
    matches_bias,
    normalize_termination,
    validate_event,
)

# A coupon biased in two steps, with a supply whose transient recovery window
# is one millisecond and which can feed half an ampere into a discharge.
RECOVERY_WINDOW_S = 1.0e-3
SUSTAINING_CURRENT_A = 0.5

APPLIED = [
    {"bias_v": 100.0, "discharges": 30},
    {"bias_v": 200.0, "discharges": 30},
]

REQUIRED = [
    {"bias_v": 100.0, "min_discharges": 25},
    {"bias_v": 200.0, "min_discharges": 25},
]


def _event(event_id="d1", duration_s=2.0e-4, peak_current_a=1.2, bias_v=100.0,
           termination="self-extinguished"):
    return {
        "event_id": event_id,
        "duration_s": duration_s,
        "peak_current_a": peak_current_a,
        "bias_v": bias_v,
        "termination": termination,
    }


def _categorize(**overrides):
    return categorize_event(_event(**overrides), SUSTAINING_CURRENT_A, RECOVERY_WINDOW_S)


class TerminationTests(unittest.TestCase):
    def test_recognized_mode_is_returned(self):
        self.assertEqual(
            normalize_termination("self-extinguished"), "self-extinguished"
        )

    def test_case_and_space_are_absorbed(self):
        self.assertEqual(
            normalize_termination(" Externally-Interrupted "), "externally-interrupted"
        )

    def test_unknown_mode_rejected(self):
        with self.assertRaises(ValueError):
            normalize_termination("blew-out")

    def test_non_string_mode_rejected(self):
        with self.assertRaises(ValueError):
            normalize_termination(None)

    def test_three_termination_modes_are_recognized(self):
        self.assertEqual(len(TERMINATION_MODES), 3)


class EventValidationTests(unittest.TestCase):
    def test_valid_event_returns_floats(self):
        record = validate_event(_event())
        self.assertAlmostEqual(record["peak_current_a"], 1.2, places=9)

    def test_event_id_is_trimmed(self):
        self.assertEqual(validate_event(_event(event_id="  d7 "))["event_id"], "d7")

    def test_missing_key_rejected(self):
        event = _event()
        del event["peak_current_a"]
        with self.assertRaises(ValueError):
            validate_event(event)

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_event(_event(duration_s=-1.0e-4))

    def test_negative_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_event(_event(peak_current_a=-0.5))

    def test_blank_event_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_event(_event(event_id="   "))

    def test_non_mapping_event_rejected(self):
        with self.assertRaises(ValueError):
            validate_event(["d1"])

    def test_boolean_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_event(_event(duration_s=True))


class CategorizationTests(unittest.TestCase):
    def test_short_self_extinguished_event_is_transient(self):
        self.assertEqual(_categorize()["category"], "transient")

    def test_long_high_current_event_is_sustained(self):
        outcome = _categorize(duration_s=5.0e-3)
        self.assertEqual(outcome["category"], "sustained")
        self.assertIn("recovery window", outcome["reason"])

    def test_long_low_current_event_is_transient(self):
        outcome = _categorize(duration_s=5.0e-3, peak_current_a=0.05)
        self.assertEqual(outcome["category"], "transient")
        self.assertIn("able to feed", outcome["reason"])

    def test_externally_interrupted_event_is_sustained(self):
        outcome = _categorize(termination="externally-interrupted", duration_s=1.0e-5)
        self.assertEqual(outcome["category"], "sustained")

    def test_still_burning_event_is_sustained(self):
        outcome = _categorize(termination="still-burning-at-end", peak_current_a=0.01)
        self.assertEqual(outcome["category"], "sustained")

    def test_duration_exactly_at_the_window_is_transient(self):
        outcome = _categorize(duration_s=RECOVERY_WINDOW_S)
        self.assertAlmostEqual(outcome["duration_s"], RECOVERY_WINDOW_S, places=12)
        self.assertEqual(outcome["category"], "transient")

    def test_duration_a_tolerance_over_the_window_is_transient(self):
        outcome = _categorize(
            duration_s=RECOVERY_WINDOW_S + COMPARISON_ABSOLUTE_TOLERANCE / 2.0
        )
        self.assertEqual(outcome["category"], "transient")

    def test_current_exactly_at_the_sustaining_level_is_sustained(self):
        outcome = _categorize(duration_s=5.0e-3, peak_current_a=SUSTAINING_CURRENT_A)
        self.assertAlmostEqual(outcome["peak_current_a"], SUSTAINING_CURRENT_A, places=12)
        self.assertEqual(outcome["category"], "sustained")

    def test_zero_recovery_window_rejected(self):
        with self.assertRaises(ValueError):
            categorize_event(_event(), SUSTAINING_CURRENT_A, 0.0)

    def test_negative_sustaining_current_rejected(self):
        with self.assertRaises(ValueError):
            categorize_event(_event(), -0.5, RECOVERY_WINDOW_S)

    def test_events_are_categorized_one_for_one(self):
        outcomes = categorize_events(
            [_event("d1"), _event("d2", duration_s=5.0e-3)],
            SUSTAINING_CURRENT_A,
            RECOVERY_WINDOW_S,
        )
        self.assertEqual(len(outcomes), 2)
        self.assertEqual(count_sustained(outcomes), 1)

    def test_empty_event_list_is_allowed(self):
        self.assertEqual(
            categorize_events([], SUSTAINING_CURRENT_A, RECOVERY_WINDOW_S), []
        )

    def test_duplicate_event_id_rejected(self):
        with self.assertRaises(ValueError):
            categorize_events(
                [_event("d1"), _event("d1")], SUSTAINING_CURRENT_A, RECOVERY_WINDOW_S
            )

    def test_non_sequence_event_set_rejected(self):
        with self.assertRaises(ValueError):
            categorize_events({"event_id": "d1"}, SUSTAINING_CURRENT_A, RECOVERY_WINDOW_S)

    def test_count_sustained_rejects_a_malformed_outcome(self):
        with self.assertRaises(ValueError):
            count_sustained([{"event_id": "d1"}])


class ConditionCoverageTests(unittest.TestCase):
    def test_full_coverage_is_satisfied(self):
        records = evaluate_condition_coverage(APPLIED, REQUIRED)
        self.assertEqual(len(records), 2)
        self.assertTrue(all(record["satisfied"] for record in records))

    def test_condition_never_applied_is_unsatisfied(self):
        records = evaluate_condition_coverage([APPLIED[0]], REQUIRED)
        self.assertFalse(records[1]["applied"])
        self.assertFalse(records[1]["satisfied"])

    def test_thin_population_is_unsatisfied(self):
        applied = [{"bias_v": 100.0, "discharges": 5}, APPLIED[1]]
        records = evaluate_condition_coverage(applied, REQUIRED)
        self.assertTrue(records[0]["applied"])
        self.assertFalse(records[0]["satisfied"])

    def test_population_exactly_at_the_minimum_is_satisfied(self):
        applied = [{"bias_v": 100.0, "discharges": 25}, APPLIED[1]]
        records = evaluate_condition_coverage(applied, REQUIRED)
        self.assertEqual(records[0]["applied_discharges"], 25)
        self.assertTrue(records[0]["satisfied"])

    def test_split_runs_at_one_bias_are_summed(self):
        applied = [
            {"bias_v": 100.0, "discharges": 15},
            {"bias_v": 100.0, "discharges": 12},
            APPLIED[1],
        ]
        records = evaluate_condition_coverage(applied, REQUIRED)
        self.assertEqual(records[0]["applied_discharges"], 27)
        self.assertTrue(records[0]["satisfied"])

    def test_empty_required_set_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_condition_coverage(APPLIED, [])

    def test_missing_count_key_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_condition_coverage([{"bias_v": 100.0}], REQUIRED)

    def test_non_integer_population_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_condition_coverage([{"bias_v": 100.0, "discharges": 30.5}], REQUIRED)

    def test_boolean_population_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_condition_coverage([{"bias_v": 100.0, "discharges": True}], REQUIRED)

    def test_bias_matching_is_tolerant_of_representation_error(self):
        self.assertTrue(matches_bias(100.0, APPLIED))

    def test_bias_outside_the_applied_set_does_not_match(self):
        self.assertFalse(matches_bias(150.0, APPLIED))


class PassDecisionTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "events": [_event("d1"), _event("d2", bias_v=200.0)],
            "sustaining_current_a": SUSTAINING_CURRENT_A,
            "extinction_window_s": RECOVERY_WINDOW_S,
            "applied_conditions": [dict(condition) for condition in APPLIED],
            "required_conditions": [dict(condition) for condition in REQUIRED],
        }
        spec.update(overrides)
        return spec

    def test_transient_events_under_full_coverage_pass(self):
        result = assess_esd_pass_criteria(self._spec())
        self.assertTrue(result["passed"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["transient_count"], 2)

    def test_a_single_sustained_event_fails_the_coupon(self):
        events = [_event("d1"), _event("d2", bias_v=200.0, duration_s=8.0e-3)]
        result = assess_esd_pass_criteria(self._spec(events=events))
        self.assertFalse(result["passed"])
        self.assertEqual(result["sustained_event_ids"], ("d2",))

    def test_externally_interrupted_event_fails_the_coupon(self):
        events = [_event("d1", termination="externally-interrupted")]
        result = assess_esd_pass_criteria(self._spec(events=events))
        self.assertFalse(result["passed"])
        self.assertEqual(result["sustained_count"], 1)

    def test_no_recorded_event_still_needs_the_conditions_applied(self):
        result = assess_esd_pass_criteria(
            self._spec(events=[], applied_conditions=[{"bias_v": 100.0, "discharges": 30}])
        )
        self.assertFalse(result["passed"])
        self.assertIn("never applied", result["findings"][0])

    def test_clean_record_under_thin_coverage_is_not_a_pass(self):
        applied = [{"bias_v": 100.0, "discharges": 4}, dict(APPLIED[1])]
        result = assess_esd_pass_criteria(self._spec(applied_conditions=applied))
        self.assertFalse(result["passed"])
        self.assertEqual(result["sustained_count"], 0)

    def test_event_outside_the_applied_conditions_is_a_finding(self):
        events = [_event("d1"), _event("d9", bias_v=350.0)]
        result = assess_esd_pass_criteria(self._spec(events=events))
        self.assertFalse(result["passed"])
        self.assertIn("no applied condition", result["findings"][0])

    def test_every_sustained_event_is_reported(self):
        events = [
            _event("d1", duration_s=6.0e-3),
            _event("d2", bias_v=200.0, termination="still-burning-at-end"),
        ]
        result = assess_esd_pass_criteria(self._spec(events=events))
        self.assertEqual(result["sustained_event_ids"], ("d1", "d2"))
        self.assertEqual(len(result["findings"]), 2)

    def test_low_current_long_event_does_not_fail_the_coupon(self):
        events = [_event("d1", duration_s=6.0e-3, peak_current_a=0.02)]
        result = assess_esd_pass_criteria(self._spec(events=events))
        self.assertTrue(result["passed"])

    def test_coverage_records_travel_with_the_verdict(self):
        result = assess_esd_pass_criteria(self._spec())
        self.assertEqual(len(result["coverage"]), 2)
        self.assertAlmostEqual(result["coverage"][1]["bias_v"], 200.0, places=9)

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["extinction_window_s"]
        with self.assertRaises(ValueError):
            assess_esd_pass_criteria(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_esd_pass_criteria(["events"])

    def test_unknown_termination_in_the_record_rejected(self):
        events = [_event("d1", termination="fizzled")]
        with self.assertRaises(ValueError):
            assess_esd_pass_criteria(self._spec(events=events))


if __name__ == "__main__":
    unittest.main()
