"""Contract tests for the clause 5.4.2.1.1 turn-on rise-rate assessment.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a trace with no time base
to slope, a peak hidden inside a slow-looking mean ramp, a peak landing
exactly on the declared ceiling, a trace too coarsely sampled to show the
slope it reports, and a campaign that never reaches a declared corner.
"""

import unittest

from e2020_startup_current_slew_limit_logic import (
    EXCEEDS_SLEW_CEILING,
    NO_RISE_OBSERVED,
    SLEW_CEILING_NOT_ESTABLISHED,
    STARTUP_SLEW_ABOVE_CEILING,
    STARTUP_SLEW_CORNERS_NOT_COVERED,
    STARTUP_SLEW_WITHIN_CEILING,
    WITHIN_SLEW_CEILING,
    assess_startup_current_slew,
    largest_sample_interval,
    mean_slew_rate,
    peak_rising_slew_rate,
    segment_slew_rates,
    slew_margin_fraction,
    trace_verdict,
    trace_verdicts,
    uncovered_corners,
    validate_sample,
    validate_slew_ceiling,
    validate_trace_record,
    validate_turn_on_trace,
    worst_trace,
)

CEILING_A_PER_S = 1000.0


def _samples():
    """A turn-on reaching 2 A, steepest stretch 800 A/s between 1 and 2 ms."""
    return [
        {"time_s": 0.0, "current_a": 0.0},
        {"time_s": 0.001, "current_a": 0.2},
        {"time_s": 0.002, "current_a": 1.0},
        {"time_s": 0.004, "current_a": 1.8},
        {"time_s": 0.006, "current_a": 2.0},
    ]


def _trace(**overrides):
    trace = {"id": "ton-01", "corner": "cold-max-bus", "samples": _samples()}
    trace.update(overrides)
    return trace


def _case(**overrides):
    case = {
        "slew_ceiling_a_per_s": CEILING_A_PER_S,
        "traces": [_trace()],
    }
    case.update(overrides)
    return case


class TraceValidationTests(unittest.TestCase):
    def test_the_reference_trace_validates(self):
        points = validate_turn_on_trace(_samples())
        self.assertEqual(len(points), 5)

    def test_a_single_sample_trace_is_refused(self):
        with self.assertRaises(ValueError):
            validate_turn_on_trace(_samples()[:1])

    def test_a_trace_that_reverses_in_time_is_refused(self):
        samples = _samples()
        samples[2]["time_s"] = 0.0005
        with self.assertRaises(ValueError):
            validate_turn_on_trace(samples)

    def test_a_repeated_timestamp_is_refused(self):
        samples = _samples()
        samples[2]["time_s"] = samples[1]["time_s"]
        with self.assertRaises(ValueError):
            validate_turn_on_trace(samples)

    def test_a_negative_current_sample_is_refused(self):
        with self.assertRaises(ValueError):
            validate_sample({"time_s": 0.0, "current_a": -1.0})

    def test_a_non_numeric_sample_time_is_refused(self):
        with self.assertRaises(ValueError):
            validate_sample({"time_s": "0.0", "current_a": 1.0})

    def test_a_non_sequence_trace_is_refused(self):
        with self.assertRaises(ValueError):
            validate_turn_on_trace({"time_s": 0.0, "current_a": 1.0})

    def test_a_blank_trace_id_is_refused(self):
        with self.assertRaises(ValueError):
            validate_trace_record(_trace(id="   "))

    def test_a_blank_corner_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_trace_record(_trace(corner="  "))


class SlopeTests(unittest.TestCase):
    def test_every_segment_gets_a_slope(self):
        self.assertEqual(len(segment_slew_rates(_samples())), 4)

    def test_the_peak_is_the_steepest_segment_not_the_last(self):
        self.assertAlmostEqual(peak_rising_slew_rate(_samples()), 800.0, places=9)

    def test_the_mean_ramp_understates_the_peak(self):
        mean = mean_slew_rate(_samples())
        self.assertAlmostEqual(mean, 2.0 / 0.006, places=9)
        self.assertLess(mean, peak_rising_slew_rate(_samples()))

    def test_the_largest_sample_interval_is_reported(self):
        self.assertAlmostEqual(largest_sample_interval(_samples()), 0.002, places=12)

    def test_a_flat_trace_has_no_rising_slope(self):
        flat = [
            {"time_s": 0.0, "current_a": 1.0},
            {"time_s": 0.001, "current_a": 1.0},
        ]
        self.assertAlmostEqual(peak_rising_slew_rate(flat), 0.0, places=12)

    def test_the_margin_is_the_headroom_as_a_fraction_of_the_ceiling(self):
        self.assertAlmostEqual(
            slew_margin_fraction(800.0, CEILING_A_PER_S), 0.2, places=9
        )

    def test_the_margin_goes_negative_when_the_ceiling_is_passed(self):
        self.assertAlmostEqual(
            slew_margin_fraction(1500.0, CEILING_A_PER_S), -0.5, places=9
        )

    def test_a_zero_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            validate_slew_ceiling(0.0)


class TraceVerdictTests(unittest.TestCase):
    def test_a_trace_under_the_ceiling_is_compliant(self):
        verdict = trace_verdict(_trace(), CEILING_A_PER_S)
        self.assertEqual(verdict["outcome"], WITHIN_SLEW_CEILING)
        self.assertTrue(verdict["compliant"])

    def test_a_peak_exactly_on_the_ceiling_is_compliant(self):
        verdict = trace_verdict(_trace(), 800.0)
        self.assertEqual(verdict["outcome"], WITHIN_SLEW_CEILING)
        self.assertAlmostEqual(verdict["margin_fraction"], 0.0, places=12)

    def test_a_peak_above_the_ceiling_is_not_compliant(self):
        verdict = trace_verdict(_trace(), 500.0)
        self.assertEqual(verdict["outcome"], EXCEEDS_SLEW_CEILING)
        self.assertFalse(verdict["compliant"])

    def test_a_trace_that_never_rises_is_not_a_turn_on(self):
        flat = _trace(
            samples=[
                {"time_s": 0.0, "current_a": 2.0},
                {"time_s": 0.001, "current_a": 2.0},
            ]
        )
        verdict = trace_verdict(flat, CEILING_A_PER_S)
        self.assertEqual(verdict["outcome"], NO_RISE_OBSERVED)
        self.assertFalse(verdict["compliant"])

    def test_a_duplicate_trace_id_is_refused(self):
        with self.assertRaises(ValueError):
            trace_verdicts([_trace(), _trace()], CEILING_A_PER_S)

    def test_an_empty_campaign_is_refused(self):
        with self.assertRaises(ValueError):
            trace_verdicts([], CEILING_A_PER_S)

    def test_the_worst_trace_is_the_one_with_least_headroom(self):
        steep = _trace(
            id="ton-02",
            samples=[
                {"time_s": 0.0, "current_a": 0.0},
                {"time_s": 0.001, "current_a": 0.95},
            ],
        )
        verdicts = trace_verdicts([_trace(), steep], CEILING_A_PER_S)
        self.assertEqual(worst_trace(verdicts)["id"], "ton-02")

    def test_the_worst_trace_helper_refuses_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_trace([])


class CornerTests(unittest.TestCase):
    def test_a_covered_corner_is_not_reported_missing(self):
        verdicts = trace_verdicts([_trace()], CEILING_A_PER_S)
        self.assertEqual(uncovered_corners(verdicts, ["cold-max-bus"]), ())

    def test_an_uncovered_corner_is_named(self):
        verdicts = trace_verdicts([_trace()], CEILING_A_PER_S)
        self.assertEqual(
            uncovered_corners(verdicts, ["cold-max-bus", "hot-max-load-capacitance"]),
            ("hot-max-load-capacitance",),
        )

    def test_no_declared_corner_list_demands_nothing(self):
        verdicts = trace_verdicts([_trace()], CEILING_A_PER_S)
        self.assertEqual(uncovered_corners(verdicts, None), ())

    def test_a_blank_required_corner_is_refused(self):
        verdicts = trace_verdicts([_trace()], CEILING_A_PER_S)
        with self.assertRaises(ValueError):
            uncovered_corners(verdicts, ["  "])


class AssessmentTests(unittest.TestCase):
    def test_the_nominal_campaign_is_within_the_ceiling(self):
        result = assess_startup_current_slew(_case())
        self.assertEqual(result["verdict"], STARTUP_SLEW_WITHIN_CEILING)
        self.assertEqual(result["findings"], [])

    def test_a_missing_ceiling_closes_the_assessment(self):
        case = _case()
        del case["slew_ceiling_a_per_s"]
        result = assess_startup_current_slew(case)
        self.assertEqual(result["verdict"], SLEW_CEILING_NOT_ESTABLISHED)

    def test_a_trace_over_the_ceiling_is_reported(self):
        result = assess_startup_current_slew(_case(slew_ceiling_a_per_s=500.0))
        self.assertEqual(result["verdict"], STARTUP_SLEW_ABOVE_CEILING)
        self.assertIn("ton-01", result["findings"][0])

    def test_an_uncovered_corner_blocks_the_pass(self):
        result = assess_startup_current_slew(
            _case(required_corners=["cold-max-bus", "hot-max-load-capacitance"])
        )
        self.assertEqual(result["verdict"], STARTUP_SLEW_CORNERS_NOT_COVERED)
        self.assertEqual(result["uncovered_corners"], ("hot-max-load-capacitance",))

    def test_a_coarse_time_base_is_advised(self):
        result = assess_startup_current_slew(
            _case(sampling_interval_limit_s=0.0005)
        )
        self.assertTrue(
            any("may be smoothed" in note for note in result["advisories"])
        )

    def test_a_fine_enough_time_base_raises_no_advisory(self):
        result = assess_startup_current_slew(_case(sampling_interval_limit_s=0.01))
        self.assertFalse(
            any("may be smoothed" in note for note in result["advisories"])
        )

    def test_a_peak_far_above_the_mean_is_advised(self):
        result = assess_startup_current_slew(_case())
        self.assertTrue(
            any("would understate it" in note for note in result["advisories"])
        )

    def test_the_worst_margin_is_carried_on_the_result(self):
        result = assess_startup_current_slew(_case())
        self.assertEqual(result["worst_trace_id"], "ton-01")
        self.assertAlmostEqual(result["worst_margin_fraction"], 0.2, places=9)

    def test_a_flat_trace_is_reported_as_no_turn_on(self):
        result = assess_startup_current_slew(
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
        self.assertEqual(result["verdict"], STARTUP_SLEW_ABOVE_CEILING)
        self.assertIn("never rises", result["findings"][0])

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_startup_current_slew(["slew_ceiling_a_per_s"])


if __name__ == "__main__":
    unittest.main()
