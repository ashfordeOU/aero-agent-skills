#!/usr/bin/env python3
"""Gate 3 contract test for e2007-power-lead-transient-purpose.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_power_lead_transient_purpose.py
"""

import unittest

from e2007_power_lead_transient_purpose_logic import (
    PERFORMANCE_NO_EFFECT,
    PERFORMANCE_OPERATOR_RECOVERABLE,
    PERFORMANCE_ORDER,
    PERFORMANCE_PERMANENT,
    PERFORMANCE_SELF_RECOVERING,
    POLARITIES,
    POLARITY_NEGATIVE,
    POLARITY_POSITIVE,
    RESPONSE_ACCEPTED,
    RESPONSE_AT_CATEGORY,
    RESPONSE_REJECTED,
    STRESS_APPLIED,
    STRESS_AT_LEVEL,
    STRESS_SHORT,
    VERDICT_DEMONSTRATED,
    VERDICT_NOT_DEMONSTRATED,
    applied_stress_margin_db,
    applied_stress_ratio,
    assess_power_lead_transient_purpose,
    assess_transient_event,
    at_least,
    grade_response,
    grade_stress,
    half_amplitude_width_s,
    normalize_lead,
    normalize_performance,
    normalize_polarity,
    peak_amplitude_v,
    pulse_polarity,
    validate_pulse,
    volt_second_area,
)

EDGE_S = 1.0e-6
BODY_S = 50.0e-6


def trapezoid(peak=250.0, body_s=BODY_S, edge_s=EDGE_S):
    """A flat-topped transient with straight edges, easy to reason about."""
    return [
        (0.0, 0.0),
        (edge_s, peak),
        (edge_s + body_s, peak),
        (2.0 * edge_s + body_s, 0.0),
        (2.0 * edge_s + body_s + 10.0e-6, 0.0),
    ]


def spec(**over):
    record = {
        "specified_peak_v": 200.0,
        "specified_width_s": 40.0e-6,
        "allowed_performance": PERFORMANCE_SELF_RECOVERING,
    }
    record.update(over)
    return record


def campaign(observed=PERFORMANCE_NO_EFFECT):
    events = []
    for lead in ("primary-positive", "primary-return"):
        for polarity in POLARITIES:
            sign = 1.0 if polarity == POLARITY_POSITIVE else -1.0
            events.append(
                {
                    "lead": lead,
                    "polarity": polarity,
                    "samples": trapezoid(250.0 * sign),
                    "observed": observed,
                }
            )
    return events


class TestNormalization(unittest.TestCase):
    def test_lead_is_lowercased_and_trimmed(self):
        self.assertEqual(normalize_lead("  Primary-Return "), "primary-return")

    def test_empty_lead_rejected(self):
        with self.assertRaises(ValueError):
            normalize_lead("  ")

    def test_non_string_lead_rejected(self):
        with self.assertRaises(ValueError):
            normalize_lead(None)

    def test_both_polarities_normalize(self):
        for polarity in POLARITIES:
            self.assertEqual(normalize_polarity(polarity.upper()), polarity)

    def test_unrecognized_polarity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_polarity("bipolar")

    def test_every_performance_category_normalizes(self):
        for category in PERFORMANCE_ORDER:
            self.assertEqual(normalize_performance(category.upper()), category)

    def test_unrecognized_performance_category_rejected(self):
        with self.assertRaises(ValueError):
            normalize_performance("degraded-a-bit")


class TestPulseValidation(unittest.TestCase):
    def test_good_pulse_is_returned_as_float_pairs(self):
        pulse = validate_pulse(trapezoid())
        self.assertEqual(len(pulse), 5)
        self.assertAlmostEqual(pulse[1][1], 250.0, places=9)

    def test_single_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_pulse([(0.0, 1.0)])

    def test_repeated_sample_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_pulse([(0.0, 1.0), (0.0, 2.0)])

    def test_time_going_backwards_rejected(self):
        with self.assertRaises(ValueError):
            validate_pulse([(0.0, 1.0), (2.0, 2.0), (1.0, 3.0)])

    def test_malformed_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_pulse([(0.0, 1.0), (1.0,)])

    def test_non_numeric_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_pulse([(0.0, 1.0), (1.0, "high")])


class TestPulseMeasurements(unittest.TestCase):
    def test_peak_keeps_the_sign_of_a_negative_transient(self):
        self.assertAlmostEqual(peak_amplitude_v(trapezoid(-250.0)), -250.0, places=9)

    def test_peak_of_a_positive_transient(self):
        self.assertAlmostEqual(peak_amplitude_v(trapezoid(250.0)), 250.0, places=9)

    def test_polarity_follows_the_largest_excursion(self):
        self.assertEqual(pulse_polarity(trapezoid(250.0)), POLARITY_POSITIVE)
        self.assertEqual(pulse_polarity(trapezoid(-250.0)), POLARITY_NEGATIVE)

    def test_flat_zero_record_has_no_polarity(self):
        with self.assertRaises(ValueError):
            pulse_polarity([(0.0, 0.0), (1.0e-6, 0.0)])

    def test_half_amplitude_width_interpolates_both_crossings(self):
        width = half_amplitude_width_s(trapezoid())
        self.assertAlmostEqual(width, BODY_S + EDGE_S, places=12)

    def test_half_amplitude_width_is_polarity_independent(self):
        self.assertAlmostEqual(
            half_amplitude_width_s(trapezoid(250.0)),
            half_amplitude_width_s(trapezoid(-250.0)),
            places=12,
        )

    def test_truncated_capture_cannot_give_a_width(self):
        with self.assertRaises(ValueError):
            half_amplitude_width_s([(0.0, 0.0), (1.0e-6, 250.0)])

    def test_volt_second_area_is_the_trapezoidal_integral(self):
        area = volt_second_area(trapezoid(200.0, 50.0e-6, 1.0e-6))
        expected = 200.0 * 50.0e-6 + 200.0 * 1.0e-6
        self.assertAlmostEqual(area, expected, places=12)

    def test_volt_second_area_is_taken_on_the_magnitude(self):
        self.assertAlmostEqual(
            volt_second_area(trapezoid(250.0)),
            volt_second_area(trapezoid(-250.0)),
            places=12,
        )


class TestStressGrading(unittest.TestCase):
    def test_ratio_of_an_exactly_met_level_is_one(self):
        self.assertAlmostEqual(applied_stress_ratio(200.0, 200.0), 1.0, places=12)

    def test_ratio_ignores_polarity(self):
        self.assertAlmostEqual(applied_stress_ratio(-300.0, 200.0), 1.5, places=12)

    def test_margin_of_an_exactly_met_level_is_zero_db(self):
        self.assertAlmostEqual(applied_stress_margin_db(200.0, 200.0), 0.0, places=9)

    def test_double_amplitude_is_about_six_db(self):
        self.assertAlmostEqual(
            applied_stress_margin_db(400.0, 200.0), 6.0205999132, places=8
        )

    def test_zero_specified_level_rejected(self):
        with self.assertRaises(ValueError):
            applied_stress_ratio(200.0, 0.0)

    def test_generous_pulse_is_graded_applied(self):
        self.assertEqual(grade_stress(250.0, 200.0), STRESS_APPLIED)

    def test_pulse_on_the_specified_level_is_carried_as_such(self):
        self.assertEqual(grade_stress(200.0, 200.0), STRESS_AT_LEVEL)

    def test_under_driven_pulse_is_graded_short(self):
        self.assertEqual(grade_stress(150.0, 200.0), STRESS_SHORT)

    def test_at_level_fraction_outside_its_range_rejected(self):
        with self.assertRaises(ValueError):
            grade_stress(200.0, 200.0, at_level_fraction=1.2)


class TestResponseGrading(unittest.TestCase):
    def test_benign_outcome_inside_the_allowance_is_accepted(self):
        self.assertEqual(
            grade_response(PERFORMANCE_NO_EFFECT, PERFORMANCE_SELF_RECOVERING),
            RESPONSE_ACCEPTED,
        )

    def test_outcome_equal_to_the_allowance_is_carried_as_at_category(self):
        self.assertEqual(
            grade_response(PERFORMANCE_SELF_RECOVERING, PERFORMANCE_SELF_RECOVERING),
            RESPONSE_AT_CATEGORY,
        )

    def test_outcome_past_the_allowance_is_rejected(self):
        self.assertEqual(
            grade_response(PERFORMANCE_PERMANENT, PERFORMANCE_SELF_RECOVERING),
            RESPONSE_REJECTED,
        )

    def test_operator_recovery_is_worse_than_self_recovery(self):
        self.assertEqual(
            grade_response(
                PERFORMANCE_OPERATOR_RECOVERABLE, PERFORMANCE_SELF_RECOVERING
            ),
            RESPONSE_REJECTED,
        )


class TestAtLeast(unittest.TestCase):
    def test_value_on_the_floor_reaches_it(self):
        self.assertTrue(at_least(200.0, 200.0))

    def test_value_a_hair_under_is_absorbed(self):
        self.assertTrue(at_least(200.0 - 1e-12, 200.0))

    def test_value_clearly_under_does_not_reach_it(self):
        self.assertFalse(at_least(199.0, 200.0))


class TestEventAssessment(unittest.TestCase):
    def test_event_record_carries_every_measured_quantity(self):
        record = assess_transient_event(campaign()[0], spec())
        self.assertEqual(record["lead"], "primary-positive")
        self.assertEqual(record["polarity"], POLARITY_POSITIVE)
        self.assertAlmostEqual(record["peak_v"], 250.0, places=9)
        self.assertAlmostEqual(record["stress_ratio"], 1.25, places=12)
        self.assertEqual(record["stress_grade"], STRESS_APPLIED)
        self.assertEqual(record["response_grade"], RESPONSE_ACCEPTED)

    def test_declared_polarity_must_match_the_record(self):
        event = dict(campaign()[0])
        event["polarity"] = POLARITY_NEGATIVE
        with self.assertRaises(ValueError):
            assess_transient_event(event, spec())

    def test_width_short_of_the_specified_width_is_flagged(self):
        event = dict(campaign()[0])
        event["samples"] = trapezoid(250.0, 5.0e-6)
        record = assess_transient_event(event, spec())
        self.assertFalse(record["width_ok"])

    def test_width_is_ungraded_when_none_is_specified(self):
        record = assess_transient_event(campaign()[0], spec(specified_width_s=None))
        self.assertIsNone(record["specified_width_s"])
        self.assertTrue(record["width_ok"])

    def test_missing_event_field_rejected(self):
        event = dict(campaign()[0])
        del event["observed"]
        with self.assertRaises(ValueError):
            assess_transient_event(event, spec())

    def test_non_mapping_event_rejected(self):
        with self.assertRaises(ValueError):
            assess_transient_event(["primary-positive"], spec())


class TestCampaignAssessment(unittest.TestCase):
    def test_complete_campaign_demonstrates_the_purpose(self):
        report = assess_power_lead_transient_purpose(campaign(), spec())
        self.assertEqual(report["verdict"], VERDICT_DEMONSTRATED)
        self.assertEqual(report["findings"], [])

    def test_missing_polarity_is_a_finding(self):
        events = [e for e in campaign() if e["polarity"] == POLARITY_POSITIVE]
        report = assess_power_lead_transient_purpose(events, spec())
        self.assertEqual(report["verdict"], VERDICT_NOT_DEMONSTRATED)
        self.assertTrue(any("never saw a negative" in f for f in report["findings"]))

    def test_too_few_repeats_is_a_finding(self):
        report = assess_power_lead_transient_purpose(
            campaign(), spec(), required_repeats=3
        )
        self.assertTrue(any("short of the 3 required" in f for f in report["findings"]))

    def test_under_driven_pulse_demonstrates_nothing(self):
        events = campaign()
        events[0]["samples"] = trapezoid(150.0)
        report = assess_power_lead_transient_purpose(events, spec())
        self.assertEqual(report["verdict"], VERDICT_NOT_DEMONSTRATED)
        self.assertTrue(any("demonstrates nothing" in f for f in report["findings"]))

    def test_permanent_degradation_is_a_finding(self):
        report = assess_power_lead_transient_purpose(
            campaign(PERFORMANCE_PERMANENT), spec()
        )
        self.assertEqual(report["verdict"], VERDICT_NOT_DEMONSTRATED)
        self.assertTrue(any("past the allowed" in f for f in report["findings"]))

    def test_outcome_on_the_allowance_is_a_limitation_not_a_finding(self):
        report = assess_power_lead_transient_purpose(
            campaign(PERFORMANCE_SELF_RECOVERING), spec()
        )
        self.assertEqual(report["verdict"], VERDICT_DEMONSTRATED)
        self.assertTrue(any("nothing in hand" in l for l in report["limitations"]))

    def test_worst_event_per_lead_is_kept(self):
        events = campaign()
        events[1]["observed"] = PERFORMANCE_PERMANENT
        report = assess_power_lead_transient_purpose(events, spec())
        self.assertEqual(
            report["worst_per_lead"]["primary-positive"]["observed"],
            PERFORMANCE_PERMANENT,
        )

    def test_governing_lead_is_the_worst_lead(self):
        events = campaign()
        events[2]["observed"] = PERFORMANCE_PERMANENT
        report = assess_power_lead_transient_purpose(events, spec())
        self.assertEqual(report["governing_lead"], "primary-return")

    def test_applied_counts_cover_every_lead_and_polarity(self):
        report = assess_power_lead_transient_purpose(campaign(), spec())
        self.assertEqual(report["applied_counts"][("primary-return", POLARITY_NEGATIVE)], 1)

    def test_empty_campaign_rejected(self):
        with self.assertRaises(ValueError):
            assess_power_lead_transient_purpose([], spec())

    def test_fractional_repeat_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_power_lead_transient_purpose(campaign(), spec(), required_repeats=2.5)

    def test_empty_required_polarities_rejected(self):
        with self.assertRaises(ValueError):
            assess_power_lead_transient_purpose(campaign(), spec(), required_polarities=[])

    def test_single_polarity_requirement_is_honoured(self):
        events = [e for e in campaign() if e["polarity"] == POLARITY_POSITIVE]
        report = assess_power_lead_transient_purpose(
            events, spec(), required_polarities=[POLARITY_POSITIVE]
        )
        self.assertEqual(report["verdict"], VERDICT_DEMONSTRATED)


if __name__ == "__main__":
    unittest.main()
