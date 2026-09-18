"""Contract tests for the clause 5.4.3.3.1 undervoltage blanking time logic."""

import unittest

from e2020_undervoltage_event_blanking_time_logic import (
    DEFAULT_BOUND_MARGIN,
    EVENT_KINDS,
    TIME_TOLERANCE_S,
    assess_blanking_time,
    blanking_window,
    event_response,
    lower_bound_s,
    upper_bound_s,
    validate_events,
    validate_timing,
    walk_events,
)

# A twenty-eight volt bus tripping at twenty-four volts. The longest permitted
# transient is two milliseconds; the load holds up for fifty, of which the
# detection chain and the switching element take one and a half between them.
TIMING = {
    "blanking_time_s": 0.005,
    "longest_transient_s": 0.002,
    "hold_up_time_s": 0.050,
    "detection_latency_s": 0.001,
    "switching_latency_s": 0.0005,
    "trip_threshold_v": 24.0,
    "bound_margin": 0.2,
}

EVENTS = [
    {
        "name": "load-step",
        "duration_s": 0.0018,
        "minimum_voltage_v": 22.0,
        "kind": "transient",
    },
    {
        "name": "heater-inrush",
        "duration_s": 0.0009,
        "minimum_voltage_v": 23.5,
        "kind": "transient",
    },
    {
        "name": "ripple-dip",
        "duration_s": 0.010,
        "minimum_voltage_v": 24.5,
        "kind": "transient",
    },
    {
        "name": "bus-collapse",
        "duration_s": 0.030,
        "minimum_voltage_v": 15.0,
        "kind": "undervoltage",
    },
]


def base(**overrides):
    spec = dict(TIMING)
    spec.update(overrides)
    return spec


def with_events(events=None, **overrides):
    spec = base(**overrides)
    spec["events"] = [dict(e) for e in (EVENTS if events is None else events)]
    return spec


class ValidationTests(unittest.TestCase):
    def test_non_mapping_timing_rejected(self):
        with self.assertRaises(ValueError):
            validate_timing([0.005])

    def test_missing_timing_key_rejected(self):
        partial = base()
        del partial["hold_up_time_s"]
        with self.assertRaises(ValueError):
            validate_timing(partial)

    def test_zero_blanking_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_timing(base(blanking_time_s=0.0))

    def test_negative_detection_latency_rejected(self):
        with self.assertRaises(ValueError):
            validate_timing(base(detection_latency_s=-0.001))

    def test_bound_margin_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_timing(base(bound_margin=1.0))

    def test_boolean_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_timing(base(hold_up_time_s=True))

    def test_events_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            validate_events({"name": "x"}, 24.0)

    def test_event_missing_key_rejected(self):
        bad = [{"name": "x", "duration_s": 0.001, "kind": "transient"}]
        with self.assertRaises(ValueError):
            validate_events(bad, 24.0)

    def test_duplicate_event_name_rejected(self):
        bad = [dict(EVENTS[0]), dict(EVENTS[0])]
        with self.assertRaises(ValueError):
            validate_events(bad, 24.0)

    def test_unknown_event_kind_rejected(self):
        bad = [dict(EVENTS[0], kind="glitchy")]
        with self.assertRaises(ValueError):
            validate_events(bad, 24.0)

    def test_undervoltage_that_never_reaches_the_threshold_rejected(self):
        bad = [dict(EVENTS[3], minimum_voltage_v=25.0)]
        with self.assertRaises(ValueError):
            validate_events(bad, 24.0)

    def test_empty_event_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_events([], 24.0)


class WindowTests(unittest.TestCase):
    def test_lower_bound_is_the_longest_transient_with_margin(self):
        self.assertAlmostEqual(lower_bound_s(validate_timing(base())), 0.0024, places=9)

    def test_upper_bound_is_the_hold_up_less_the_latencies(self):
        self.assertAlmostEqual(upper_bound_s(validate_timing(base())), 0.0385, places=9)

    def test_nominal_budget_leaves_a_feasible_window(self):
        lower, upper, feasible = blanking_window(validate_timing(base()))
        self.assertTrue(feasible)
        self.assertAlmostEqual(lower, 0.0024, places=9)
        self.assertAlmostEqual(upper, 0.0385, places=9)

    def test_a_transient_envelope_wider_than_the_hold_up_closes_the_window(self):
        lower, upper, feasible = blanking_window(
            validate_timing(base(longest_transient_s=0.040))
        )
        self.assertFalse(feasible)
        self.assertAlmostEqual(lower, 0.048, places=9)

    def test_blanking_exactly_on_the_lower_bound_is_inside(self):
        lower = lower_bound_s(validate_timing(base()))
        result = assess_blanking_time(base(blanking_time_s=lower))
        self.assertTrue(result["inside_window"])
        self.assertAlmostEqual(result["lower_margin_s"], 0.0, places=9)

    def test_blanking_exactly_on_the_upper_bound_is_inside(self):
        upper = upper_bound_s(validate_timing(base()))
        result = assess_blanking_time(base(blanking_time_s=upper))
        self.assertTrue(result["inside_window"])
        self.assertAlmostEqual(result["upper_margin_s"], 0.0, places=9)

    def test_a_larger_margin_narrows_the_window_from_both_ends(self):
        wide = blanking_window(validate_timing(base(bound_margin=0.1)))
        tight = blanking_window(validate_timing(base(bound_margin=0.4)))
        self.assertAlmostEqual(wide[0], 0.0022, places=9)
        self.assertAlmostEqual(tight[0], 0.0028, places=9)
        self.assertAlmostEqual(tight[1], 0.0285, places=9)


class EventWalkTests(unittest.TestCase):
    def test_a_dip_that_never_reaches_the_threshold_never_arms_the_timer(self):
        events = validate_events([dict(EVENTS[2])], 24.0)
        record = event_response(events[0], 0.005)
        self.assertFalse(record["arms_timer"])
        self.assertFalse(record["tripped"])
        self.assertIn("never arms", record["reason"])

    def test_a_dip_exactly_as_long_as_the_blanking_time_is_absorbed(self):
        events = validate_events(
            [dict(EVENTS[0], name="edge-case", duration_s=0.005)], 24.0
        )
        record = event_response(events[0], 0.005)
        self.assertAlmostEqual(record["duration_s"], 0.005, places=9)
        self.assertFalse(record["tripped"])
        self.assertTrue(record["correct"])

    def test_a_transient_longer_than_the_blanking_time_trips(self):
        events = validate_events([dict(EVENTS[0], duration_s=0.008)], 24.0)
        record = event_response(events[0], 0.005)
        self.assertTrue(record["tripped"])
        self.assertFalse(record["correct"])

    def test_a_real_undervoltage_longer_than_the_blanking_time_trips(self):
        events = validate_events([dict(EVENTS[3])], 24.0)
        record = event_response(events[0], 0.005)
        self.assertTrue(record["tripped"])
        self.assertTrue(record["correct"])

    def test_the_walk_returns_one_record_per_event_with_a_reason(self):
        events = validate_events([dict(e) for e in EVENTS], 24.0)
        walk = walk_events(events, 0.005)
        self.assertEqual(len(walk), len(EVENTS))
        for record in walk:
            self.assertTrue(record["reason"])
            self.assertIn(record["kind"], EVENT_KINDS)


class AssessmentTests(unittest.TestCase):
    def test_nominal_budget_and_event_set_is_compliant(self):
        result = assess_blanking_time(with_events())
        self.assertEqual(result["verdict"], "compliant")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["mishandled_events"], [])

    def test_a_blanking_time_below_the_lower_bound_is_reported(self):
        result = assess_blanking_time(with_events(blanking_time_s=0.001))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertIn("load-step", result["mishandled_events"])
        joined = " | ".join(result["findings"])
        self.assertIn("shorter than", joined)
        self.assertIn("transient 'load-step' trips", joined)

    def test_a_blanking_time_above_the_upper_bound_is_reported(self):
        result = assess_blanking_time(with_events(blanking_time_s=0.045))
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertIn("bus-collapse", result["mishandled_events"])
        joined = " | ".join(result["findings"])
        self.assertIn("overruns", joined)
        self.assertIn("is not caught", joined)

    def test_an_infeasible_window_is_a_finding_of_its_own(self):
        result = assess_blanking_time(base(longest_transient_s=0.040))
        self.assertFalse(result["window_feasible"])
        self.assertEqual(result["verdict"], "non-compliant")
        self.assertIn("no blanking time exists", result["findings"][0])

    def test_margins_on_both_sides_are_reported(self):
        result = assess_blanking_time(base())
        self.assertAlmostEqual(result["lower_margin_s"], 0.0026, places=9)
        self.assertAlmostEqual(result["upper_margin_s"], 0.0335, places=9)

    def test_the_tripped_event_list_names_only_what_actually_tripped(self):
        result = assess_blanking_time(with_events())
        self.assertEqual(result["tripped_events"], ["bus-collapse"])
        self.assertEqual(result["event_count"], 4)

    def test_a_spec_without_events_still_grades_the_window(self):
        result = assess_blanking_time(base())
        self.assertEqual(result["event_count"], 0)
        self.assertEqual(result["verdict"], "compliant")

    def test_a_long_dip_that_stays_above_the_threshold_never_trips(self):
        result = assess_blanking_time(with_events(events=[dict(EVENTS[2])]))
        self.assertEqual(result["tripped_events"], [])
        self.assertEqual(result["verdict"], "compliant")

    def test_default_bound_margin_is_declared(self):
        self.assertAlmostEqual(DEFAULT_BOUND_MARGIN, 0.2, places=9)

    def test_time_tolerance_is_a_representation_allowance_not_a_limit(self):
        self.assertLessEqual(TIME_TOLERANCE_S, 1e-9)


if __name__ == "__main__":
    unittest.main()
