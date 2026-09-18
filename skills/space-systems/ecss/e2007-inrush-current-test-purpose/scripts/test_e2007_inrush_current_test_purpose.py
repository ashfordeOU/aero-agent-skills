#!/usr/bin/env python3
"""Gate 3 contract test for e2007-inrush-current-test-purpose.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_inrush_current_test_purpose.py
"""

import unittest

from e2007_inrush_current_test_purpose_logic import (
    CONDITION_COLD_START,
    CONDITION_MAXIMUM_BUS,
    CONDITION_MINIMUM_BUS,
    CONDITION_WARM_RESTART,
    GRADE_AT_BOUND,
    GRADE_EXCEEDANCE,
    GRADE_WITHIN,
    SWITCH_ON_CONDITIONS,
    VERDICT_DEMONSTRATED,
    VERDICT_NOT_DEMONSTRATED,
    assess_event,
    assess_inrush_purpose,
    at_most,
    duration_above_a,
    excess_charge_c,
    grade_peak,
    normalize_condition,
    normalize_line,
    peak_current_a,
    steady_state_current_a,
    surge_ratio,
    validate_trace,
)

TRIANGLE = [(0.0, 0.0), (1.0, 10.0), (2.0, 0.0)]
PLATEAU = [(0.0, 4.0), (1.0, 4.0), (2.0, 4.0)]


def decaying_surge(peak=18.0):
    return [
        (0.0, 0.0),
        (0.001, peak),
        (0.002, peak * 0.5),
        (0.004, peak * 0.25),
        (0.010, 2.0),
        (0.050, 1.0),
        (0.100, 1.0),
    ]


def spec(**over):
    record = {
        "peak_bound_a": 25.0,
        "envelope_a": 4.0,
        "allowed_above_envelope_s": 0.010,
    }
    record.update(over)
    return record


def campaign():
    events = []
    for line in ("primary-positive", "primary-return"):
        scale = 1.0 if line == "primary-positive" else 0.8
        for condition in SWITCH_ON_CONDITIONS:
            events.append(
                {
                    "line": line,
                    "condition": condition,
                    "samples": decaying_surge(18.0 * scale),
                }
            )
    return events


class TestConditionNormalization(unittest.TestCase):
    def test_every_condition_normalizes(self):
        for condition in SWITCH_ON_CONDITIONS:
            self.assertEqual(normalize_condition(condition.upper()), condition)

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(normalize_condition("  cold-start "), CONDITION_COLD_START)

    def test_unrecognized_condition_rejected(self):
        with self.assertRaises(ValueError):
            normalize_condition("hot-swap")

    def test_non_string_condition_rejected(self):
        with self.assertRaises(ValueError):
            normalize_condition(3)


class TestLineNormalization(unittest.TestCase):
    def test_line_is_lowercased_and_trimmed(self):
        self.assertEqual(normalize_line("  Primary-Positive "), "primary-positive")

    def test_empty_line_rejected(self):
        with self.assertRaises(ValueError):
            normalize_line("   ")

    def test_non_string_line_rejected(self):
        with self.assertRaises(ValueError):
            normalize_line(None)


class TestTraceValidation(unittest.TestCase):
    def test_good_trace_is_returned_as_float_pairs(self):
        trace = validate_trace(TRIANGLE)
        self.assertEqual(len(trace), 3)
        self.assertAlmostEqual(trace[1][1], 10.0, places=9)

    def test_single_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_trace([(0.0, 1.0)])

    def test_time_must_advance(self):
        with self.assertRaises(ValueError):
            validate_trace([(0.0, 1.0), (0.0, 2.0)])

    def test_time_going_backwards_rejected(self):
        with self.assertRaises(ValueError):
            validate_trace([(0.0, 1.0), (1.0, 2.0), (0.5, 3.0)])

    def test_negative_current_rejected(self):
        with self.assertRaises(ValueError):
            validate_trace([(0.0, 1.0), (1.0, -2.0)])

    def test_malformed_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_trace([(0.0, 1.0), (1.0,)])

    def test_non_finite_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_trace([(0.0, 1.0), (1.0, float("nan"))])


class TestPeakAndSteadyState(unittest.TestCase):
    def test_peak_is_the_largest_sample(self):
        self.assertAlmostEqual(peak_current_a(TRIANGLE), 10.0, places=9)

    def test_steady_state_averages_the_settled_tail(self):
        self.assertAlmostEqual(steady_state_current_a(decaying_surge()), 1.0, places=9)

    def test_plateau_steady_state_equals_the_plateau(self):
        self.assertAlmostEqual(steady_state_current_a(PLATEAU), 4.0, places=9)

    def test_settling_fraction_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            steady_state_current_a(PLATEAU, 0.0)

    def test_full_settling_fraction_averages_the_whole_trace(self):
        self.assertAlmostEqual(steady_state_current_a(PLATEAU, 1.0), 4.0, places=9)


class TestSurgeRatio(unittest.TestCase):
    def test_ratio_is_peak_over_settled_draw(self):
        self.assertAlmostEqual(surge_ratio(18.0, 1.0), 18.0, places=9)

    def test_zero_steady_state_rejected(self):
        with self.assertRaises(ValueError):
            surge_ratio(18.0, 0.0)

    def test_negative_peak_rejected(self):
        with self.assertRaises(ValueError):
            surge_ratio(-1.0, 1.0)


class TestEnvelopeDwell(unittest.TestCase):
    def test_triangle_crossings_are_interpolated(self):
        self.assertAlmostEqual(duration_above_a(TRIANGLE, 5.0), 1.0, places=9)

    def test_excess_charge_over_the_triangle(self):
        self.assertAlmostEqual(excess_charge_c(TRIANGLE, 5.0), 2.5, places=9)

    def test_plateau_above_the_envelope_the_whole_time(self):
        self.assertAlmostEqual(duration_above_a(PLATEAU, 2.0), 2.0, places=9)
        self.assertAlmostEqual(excess_charge_c(PLATEAU, 2.0), 4.0, places=9)

    def test_envelope_above_the_peak_leaves_nothing(self):
        self.assertAlmostEqual(duration_above_a(TRIANGLE, 20.0), 0.0, places=9)
        self.assertAlmostEqual(excess_charge_c(TRIANGLE, 20.0), 0.0, places=9)

    def test_envelope_on_the_plateau_level_leaves_nothing(self):
        self.assertAlmostEqual(duration_above_a(PLATEAU, 4.0), 0.0, places=9)

    def test_negative_threshold_rejected(self):
        with self.assertRaises(ValueError):
            duration_above_a(TRIANGLE, -1.0)

    def test_negative_threshold_rejected_for_charge(self):
        with self.assertRaises(ValueError):
            excess_charge_c(TRIANGLE, -1.0)


class TestGrading(unittest.TestCase):
    def test_comfortable_peak_is_within_bound(self):
        self.assertEqual(grade_peak(10.0, 25.0), GRADE_WITHIN)

    def test_peak_exactly_on_the_bound_is_at_bound_not_an_exceedance(self):
        self.assertEqual(grade_peak(25.0, 25.0), GRADE_AT_BOUND)

    def test_peak_just_inside_the_bound_is_at_bound(self):
        self.assertEqual(grade_peak(24.8, 25.0), GRADE_AT_BOUND)

    def test_peak_past_the_bound_is_an_exceedance(self):
        self.assertEqual(grade_peak(26.0, 25.0), GRADE_EXCEEDANCE)

    def test_non_positive_bound_rejected(self):
        with self.assertRaises(ValueError):
            grade_peak(10.0, 0.0)

    def test_at_bound_fraction_outside_range_rejected(self):
        with self.assertRaises(ValueError):
            grade_peak(10.0, 25.0, 1.0)

    def test_at_most_accepts_an_exact_bound(self):
        self.assertTrue(at_most(25.0, 25.0))

    def test_at_most_rejects_a_real_excess(self):
        self.assertFalse(at_most(25.5, 25.0))


class TestAssessEvent(unittest.TestCase):
    def test_clean_event_grades_within_bound(self):
        record = assess_event(
            {
                "line": "primary-positive",
                "condition": CONDITION_COLD_START,
                "samples": decaying_surge(),
            },
            spec(),
        )
        self.assertEqual(record["grade"], GRADE_WITHIN)
        self.assertAlmostEqual(record["peak_a"], 18.0, places=9)
        self.assertAlmostEqual(record["margin_a"], 7.0, places=9)

    def test_surge_ratio_is_carried_on_the_record(self):
        record = assess_event(
            {
                "line": "primary-positive",
                "condition": CONDITION_COLD_START,
                "samples": decaying_surge(),
            },
            spec(),
        )
        self.assertAlmostEqual(record["surge_ratio"], 18.0, places=9)

    def test_surge_ratio_is_absent_when_nothing_settled(self):
        record = assess_event(
            {
                "line": "primary-positive",
                "condition": CONDITION_COLD_START,
                "samples": TRIANGLE,
            },
            spec(envelope_a=5.0, allowed_above_envelope_s=2.0),
        )
        self.assertIsNone(record["surge_ratio"])

    def test_missing_line_rejected(self):
        with self.assertRaises(ValueError):
            assess_event(
                {"condition": CONDITION_COLD_START, "samples": TRIANGLE}, spec()
            )

    def test_missing_samples_rejected(self):
        with self.assertRaises(ValueError):
            assess_event(
                {"line": "primary-positive", "condition": CONDITION_COLD_START}, spec()
            )

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_event(
                {
                    "line": "primary-positive",
                    "condition": CONDITION_COLD_START,
                    "samples": TRIANGLE,
                },
                ["25 A"],
            )

    def test_non_positive_envelope_rejected(self):
        with self.assertRaises(ValueError):
            assess_event(
                {
                    "line": "primary-positive",
                    "condition": CONDITION_COLD_START,
                    "samples": TRIANGLE,
                },
                spec(envelope_a=0.0),
            )

    def test_absent_dwell_allowance_leaves_the_duration_ungraded(self):
        record = assess_event(
            {
                "line": "primary-positive",
                "condition": CONDITION_COLD_START,
                "samples": decaying_surge(),
            },
            {"peak_bound_a": 25.0, "envelope_a": 4.0},
        )
        self.assertTrue(record["duration_ok"])
        self.assertIsNone(record["allowed_above_envelope_s"])


class TestAssessCampaign(unittest.TestCase):
    def test_full_campaign_demonstrates_the_purpose(self):
        report = assess_inrush_purpose(campaign(), spec())
        self.assertEqual(report["verdict"], VERDICT_DEMONSTRATED)
        self.assertEqual(report["findings"], [])

    def test_governing_line_is_the_worst_peak(self):
        report = assess_inrush_purpose(campaign(), spec())
        self.assertEqual(report["governing_line"], "primary-positive")
        self.assertAlmostEqual(report["governing_peak_a"], 18.0, places=9)

    def test_missing_condition_on_one_line_is_a_finding(self):
        events = [e for e in campaign() if not (
            e["line"] == "primary-return" and e["condition"] == CONDITION_MINIMUM_BUS
        )]
        report = assess_inrush_purpose(events, spec())
        self.assertEqual(report["verdict"], VERDICT_NOT_DEMONSTRATED)
        self.assertTrue(any("minimum-bus-voltage" in f for f in report["findings"]))

    def test_exceedance_stops_the_purpose_being_demonstrated(self):
        events = campaign()
        events[0]["samples"] = decaying_surge(40.0)
        report = assess_inrush_purpose(events, spec())
        self.assertEqual(report["verdict"], VERDICT_NOT_DEMONSTRATED)

    def test_event_on_the_bound_is_a_limitation_not_a_finding(self):
        events = campaign()
        events[0]["samples"] = decaying_surge(25.0)
        report = assess_inrush_purpose(events, spec())
        self.assertEqual(report["verdict"], VERDICT_DEMONSTRATED)
        self.assertEqual(len(report["limitations"]), 1)

    def test_long_dwell_above_the_envelope_is_a_finding(self):
        events = campaign()
        report = assess_inrush_purpose(
            events, spec(allowed_above_envelope_s=0.0005)
        )
        self.assertEqual(report["verdict"], VERDICT_NOT_DEMONSTRATED)

    def test_required_conditions_can_be_narrowed(self):
        events = [e for e in campaign() if e["condition"] == CONDITION_COLD_START]
        report = assess_inrush_purpose(
            events, spec(), required_conditions=[CONDITION_COLD_START]
        )
        self.assertEqual(report["verdict"], VERDICT_DEMONSTRATED)

    def test_worst_per_line_keeps_one_record_per_line(self):
        report = assess_inrush_purpose(campaign(), spec())
        self.assertEqual(sorted(report["worst_per_line"]), [
            "primary-positive",
            "primary-return",
        ])

    def test_empty_campaign_rejected(self):
        with self.assertRaises(ValueError):
            assess_inrush_purpose([], spec())

    def test_unrecognized_required_condition_rejected(self):
        with self.assertRaises(ValueError):
            assess_inrush_purpose(
                campaign(), spec(), required_conditions=["brown-out"]
            )

    def test_warm_restart_and_maximum_bus_are_both_recognized(self):
        report = assess_inrush_purpose(campaign(), spec())
        captured = {e["condition"] for e in report["events"]}
        self.assertIn(CONDITION_WARM_RESTART, captured)
        self.assertIn(CONDITION_MAXIMUM_BUS, captured)


if __name__ == "__main__":
    unittest.main()
