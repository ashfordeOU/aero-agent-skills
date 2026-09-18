"""Contract tests for the clause 5.4.2.2.1 switch-off rate-of-fall assessment.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a trace with no usable
time base, an abrupt let-go hidden inside a leisurely mean decay, a rate
landing exactly on the ceiling, a compliant rate that still overruns the
bus transient allowance across an inductive harness, and a half-declared
transient check that silently tests nothing.
"""

import unittest

from e2020_switch_off_current_slew_limit_logic import (
    EXCEEDS_FALL_CEILING,
    EXCEEDS_TRANSIENT_ALLOWANCE,
    FALL_CEILING_NOT_ESTABLISHED,
    NO_FALL_OBSERVED,
    SWITCH_OFF_SLEW_ABOVE_LIMITS,
    SWITCH_OFF_SLEW_WITHIN_LIMITS,
    WITHIN_FALL_CEILING,
    assess_switch_off_current_slew,
    fall_margin_fraction,
    induced_transient_volt,
    mean_fall_rate,
    peak_falling_rate,
    segment_fall_rates,
    trace_verdict,
    trace_verdicts,
    transient_margin_fraction,
    validate_fall_slew_ceiling,
    validate_sample,
    validate_switch_off_trace,
    validate_trace_record,
    worst_trace,
)

CEILING_A_PER_S = 1000.0
SMALL_INDUCTANCE_H = 1.0e-4
LARGE_INDUCTANCE_H = 1.0e-3


def _samples():
    """A switch-off from 2 A, steepest collapse 800 A/s between 1 and 2 ms."""
    return [
        {"time_s": 0.0, "current_a": 2.0},
        {"time_s": 0.001, "current_a": 1.8},
        {"time_s": 0.002, "current_a": 1.0},
        {"time_s": 0.004, "current_a": 0.2},
        {"time_s": 0.006, "current_a": 0.0},
    ]


def _trace(**overrides):
    trace = {"id": "toff-01", "corner": "hot-max-load-current", "samples": _samples()}
    trace.update(overrides)
    return trace


def _case(**overrides):
    case = {
        "fall_slew_ceiling_a_per_s": CEILING_A_PER_S,
        "harness_inductance_h": SMALL_INDUCTANCE_H,
        "transient_allowance_v": 1.0,
        "traces": [_trace()],
    }
    case.update(overrides)
    return case


class TraceValidationTests(unittest.TestCase):
    def test_the_reference_trace_validates(self):
        points = validate_switch_off_trace(_samples())
        self.assertEqual(len(points), 5)

    def test_a_single_sample_trace_is_refused(self):
        with self.assertRaises(ValueError):
            validate_switch_off_trace(_samples()[:1])

    def test_a_trace_that_reverses_in_time_is_refused(self):
        samples = _samples()
        samples[3]["time_s"] = 0.0015
        with self.assertRaises(ValueError):
            validate_switch_off_trace(samples)

    def test_a_repeated_timestamp_is_refused(self):
        samples = _samples()
        samples[3]["time_s"] = samples[2]["time_s"]
        with self.assertRaises(ValueError):
            validate_switch_off_trace(samples)

    def test_a_negative_current_sample_is_refused(self):
        with self.assertRaises(ValueError):
            validate_sample({"time_s": 0.001, "current_a": -0.5})

    def test_a_non_sequence_trace_is_refused(self):
        with self.assertRaises(ValueError):
            validate_switch_off_trace("2.0 A falling")

    def test_a_blank_trace_id_is_refused(self):
        with self.assertRaises(ValueError):
            validate_trace_record(_trace(id=" "))

    def test_a_blank_corner_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_trace_record(_trace(corner=" "))


class RateTests(unittest.TestCase):
    def test_every_segment_gets_a_rate_of_fall(self):
        self.assertEqual(len(segment_fall_rates(_samples())), 4)

    def test_a_rising_segment_reports_a_negative_rate_of_fall(self):
        rising = [
            {"time_s": 0.0, "current_a": 0.0},
            {"time_s": 0.001, "current_a": 0.5},
        ]
        self.assertAlmostEqual(
            segment_fall_rates(rising)[0]["fall_rate_a_per_s"], -500.0, places=9
        )

    def test_the_peak_is_the_steepest_collapse_not_the_last_segment(self):
        self.assertAlmostEqual(peak_falling_rate(_samples()), 800.0, places=9)

    def test_the_mean_decay_understates_the_collapse(self):
        mean = mean_fall_rate(_samples())
        self.assertAlmostEqual(mean, 2.0 / 0.006, places=9)
        self.assertLess(mean, peak_falling_rate(_samples()))

    def test_a_flat_trace_has_no_rate_of_fall(self):
        flat = [
            {"time_s": 0.0, "current_a": 2.0},
            {"time_s": 0.001, "current_a": 2.0},
        ]
        self.assertAlmostEqual(peak_falling_rate(flat), 0.0, places=12)

    def test_the_margin_is_the_headroom_as_a_fraction_of_the_ceiling(self):
        self.assertAlmostEqual(
            fall_margin_fraction(800.0, CEILING_A_PER_S), 0.2, places=9
        )

    def test_a_zero_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            validate_fall_slew_ceiling(0.0)


class TransientTests(unittest.TestCase):
    def test_the_transient_is_the_inductance_times_the_rate(self):
        self.assertAlmostEqual(
            induced_transient_volt(800.0, LARGE_INDUCTANCE_H), 0.8, places=9
        )

    def test_a_rising_current_develops_no_switch_off_transient(self):
        self.assertAlmostEqual(
            induced_transient_volt(-500.0, LARGE_INDUCTANCE_H), 0.0, places=12
        )

    def test_a_zero_inductance_is_refused(self):
        with self.assertRaises(ValueError):
            induced_transient_volt(800.0, 0.0)

    def test_the_transient_margin_is_relative_to_the_allowance(self):
        self.assertAlmostEqual(transient_margin_fraction(0.8, 1.0), 0.2, places=9)

    def test_a_zero_transient_allowance_is_refused(self):
        with self.assertRaises(ValueError):
            transient_margin_fraction(0.8, 0.0)


class TraceVerdictTests(unittest.TestCase):
    def test_a_trace_under_both_limits_is_compliant(self):
        verdict = trace_verdict(
            _trace(), CEILING_A_PER_S, SMALL_INDUCTANCE_H, 1.0
        )
        self.assertEqual(verdict["outcome"], WITHIN_FALL_CEILING)
        self.assertTrue(verdict["compliant"])

    def test_a_rate_exactly_on_the_ceiling_is_compliant(self):
        verdict = trace_verdict(_trace(), 800.0)
        self.assertEqual(verdict["outcome"], WITHIN_FALL_CEILING)
        self.assertAlmostEqual(verdict["fall_margin_fraction"], 0.0, places=12)

    def test_a_rate_above_the_ceiling_is_not_compliant(self):
        verdict = trace_verdict(_trace(), 500.0)
        self.assertEqual(verdict["outcome"], EXCEEDS_FALL_CEILING)
        self.assertFalse(verdict["compliant"])

    def test_a_compliant_rate_can_still_overrun_the_harness_allowance(self):
        verdict = trace_verdict(
            _trace(), CEILING_A_PER_S, LARGE_INDUCTANCE_H, 0.5
        )
        self.assertEqual(verdict["outcome"], EXCEEDS_TRANSIENT_ALLOWANCE)
        self.assertFalse(verdict["compliant"])
        self.assertAlmostEqual(verdict["induced_transient_v"], 0.8, places=9)

    def test_a_transient_exactly_on_the_allowance_is_compliant(self):
        verdict = trace_verdict(
            _trace(), CEILING_A_PER_S, LARGE_INDUCTANCE_H, 0.8
        )
        self.assertEqual(verdict["outcome"], WITHIN_FALL_CEILING)

    def test_the_transient_is_left_unmeasured_when_no_harness_is_declared(self):
        verdict = trace_verdict(_trace(), CEILING_A_PER_S)
        self.assertIsNone(verdict["induced_transient_v"])
        self.assertIsNone(verdict["transient_margin_fraction"])

    def test_a_trace_that_never_falls_is_not_a_switch_off(self):
        flat = _trace(
            samples=[
                {"time_s": 0.0, "current_a": 2.0},
                {"time_s": 0.001, "current_a": 2.0},
            ]
        )
        verdict = trace_verdict(flat, CEILING_A_PER_S)
        self.assertEqual(verdict["outcome"], NO_FALL_OBSERVED)
        self.assertFalse(verdict["compliant"])

    def test_the_binding_margin_is_the_lower_of_the_two(self):
        verdict = trace_verdict(
            _trace(), CEILING_A_PER_S, LARGE_INDUCTANCE_H, 0.9
        )
        self.assertAlmostEqual(
            verdict["binding_margin_fraction"], 0.1 / 0.9, places=9
        )

    def test_a_duplicate_trace_id_is_refused(self):
        with self.assertRaises(ValueError):
            trace_verdicts([_trace(), _trace()], CEILING_A_PER_S)

    def test_an_empty_campaign_is_refused(self):
        with self.assertRaises(ValueError):
            trace_verdicts([], CEILING_A_PER_S)

    def test_the_worst_trace_is_the_one_with_least_headroom(self):
        abrupt = _trace(
            id="toff-02",
            samples=[
                {"time_s": 0.0, "current_a": 2.0},
                {"time_s": 0.001, "current_a": 1.05},
            ],
        )
        verdicts = trace_verdicts([_trace(), abrupt], CEILING_A_PER_S)
        self.assertEqual(worst_trace(verdicts)["id"], "toff-02")

    def test_the_worst_trace_helper_refuses_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_trace([])


class AssessmentTests(unittest.TestCase):
    def test_the_nominal_campaign_is_within_both_limits(self):
        result = assess_switch_off_current_slew(_case())
        self.assertEqual(result["verdict"], SWITCH_OFF_SLEW_WITHIN_LIMITS)
        self.assertEqual(result["findings"], [])

    def test_a_missing_ceiling_closes_the_assessment(self):
        case = _case()
        del case["fall_slew_ceiling_a_per_s"]
        result = assess_switch_off_current_slew(case)
        self.assertEqual(result["verdict"], FALL_CEILING_NOT_ESTABLISHED)

    def test_a_rate_over_the_ceiling_is_reported(self):
        result = assess_switch_off_current_slew(
            _case(fall_slew_ceiling_a_per_s=500.0)
        )
        self.assertEqual(result["verdict"], SWITCH_OFF_SLEW_ABOVE_LIMITS)
        self.assertIn("toff-01", result["findings"][0])

    def test_an_inductive_harness_can_fail_a_compliant_rate(self):
        result = assess_switch_off_current_slew(
            _case(harness_inductance_h=LARGE_INDUCTANCE_H, transient_allowance_v=0.5)
        )
        self.assertEqual(result["verdict"], SWITCH_OFF_SLEW_ABOVE_LIMITS)
        self.assertIn("across the harness", result["findings"][0])

    def test_a_half_declared_transient_check_is_advised(self):
        case = _case()
        del case["transient_allowance_v"]
        result = assess_switch_off_current_slew(case)
        self.assertEqual(result["verdict"], SWITCH_OFF_SLEW_WITHIN_LIMITS)
        self.assertTrue(
            any("left unchecked" in note for note in result["advisories"])
        )

    def test_a_transient_bound_trace_is_advised(self):
        result = assess_switch_off_current_slew(
            _case(harness_inductance_h=LARGE_INDUCTANCE_H, transient_allowance_v=0.9)
        )
        self.assertTrue(
            any("bound by the harness transient" in note for note in result["advisories"])
        )

    def test_an_abrupt_let_go_inside_a_slow_decay_is_advised(self):
        result = assess_switch_off_current_slew(_case())
        self.assertTrue(
            any("would understate it" in note for note in result["advisories"])
        )

    def test_the_worst_margin_is_carried_on_the_result(self):
        result = assess_switch_off_current_slew(_case())
        self.assertEqual(result["worst_trace_id"], "toff-01")
        self.assertAlmostEqual(result["worst_margin_fraction"], 0.2, places=9)

    def test_a_flat_trace_is_reported_as_no_switch_off(self):
        result = assess_switch_off_current_slew(
            _case(
                traces=[
                    _trace(
                        samples=[
                            {"time_s": 0.0, "current_a": 2.0},
                            {"time_s": 0.001, "current_a": 2.0},
                        ]
                    )
                ]
            )
        )
        self.assertEqual(result["verdict"], SWITCH_OFF_SLEW_ABOVE_LIMITS)
        self.assertIn("never falls", result["findings"][0])

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_switch_off_current_slew(["fall_slew_ceiling_a_per_s"])


if __name__ == "__main__":
    unittest.main()
