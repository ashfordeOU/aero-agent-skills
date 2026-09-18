#!/usr/bin/env python3
"""Gate 3 contract test for e2007-susceptibility-frequency-stepping.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_susceptibility_frequency_stepping.py
"""

import unittest

from e2007_susceptibility_frequency_stepping_logic import (
    DEFAULT_MAX_STEP_FRACTION,
    DEFAULT_MIN_DWELL_S,
    SCAN_MODE_CONTINUOUS,
    SCAN_MODE_STEPPED,
    SCAN_MODE_SWEPT,
    assess_susceptibility_frequency_stepping,
    at_least_time,
    at_most_fraction,
    generate_step_plan,
    oversized_steps,
    range_coverage_gaps,
    required_dwell_s,
    scan_duration_s,
    short_dwells,
    step_fraction,
    validate_range,
    validate_scan_mode,
    validate_steps,
)

RANGE_START = 2.0e6
RANGE_STOP = 2.08e6
RESPONSE_S = 2.0


def plan_steps(dwell=RESPONSE_S):
    return generate_step_plan(
        RANGE_START, RANGE_STOP, DEFAULT_MAX_STEP_FRACTION, dwell
    )


class TestScanMode(unittest.TestCase):
    def test_stepped_mode_normalizes(self):
        self.assertEqual(validate_scan_mode("  Stepped "), SCAN_MODE_STEPPED)

    def test_continuous_mode_is_recognized_but_distinct(self):
        self.assertEqual(validate_scan_mode("continuous"), SCAN_MODE_CONTINUOUS)

    def test_swept_mode_is_recognized(self):
        self.assertEqual(validate_scan_mode("SWEPT"), SCAN_MODE_SWEPT)

    def test_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan_mode("hopping")

    def test_non_string_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan_mode(None)


class TestRangeAndStepValidation(unittest.TestCase):
    def test_range_normalizes(self):
        band = validate_range(RANGE_START, RANGE_STOP)
        self.assertAlmostEqual(band["stop_hz"], RANGE_STOP, places=3)

    def test_inverted_range_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_range(RANGE_STOP, RANGE_START)

    def test_single_step_is_not_a_scan(self):
        with self.assertRaises(ValueError):
            validate_steps([{"frequency_hz": RANGE_START, "dwell_time_s": 2.0}])

    def test_non_increasing_steps_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_steps(
                [
                    {"frequency_hz": 2.01e6, "dwell_time_s": 2.0},
                    {"frequency_hz": 2.0e6, "dwell_time_s": 2.0},
                ]
            )

    def test_zero_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_steps(
                [
                    {"frequency_hz": 2.0e6, "dwell_time_s": 0.0},
                    {"frequency_hz": 2.01e6, "dwell_time_s": 2.0},
                ]
            )

    def test_boolean_dwell_is_not_a_number(self):
        with self.assertRaises(ValueError):
            validate_steps(
                [
                    {"frequency_hz": 2.0e6, "dwell_time_s": True},
                    {"frequency_hz": 2.01e6, "dwell_time_s": 2.0},
                ]
            )


class TestStepSizing(unittest.TestCase):
    def test_step_fraction_is_relative_to_the_lower_frequency(self):
        self.assertAlmostEqual(step_fraction(100.0, 101.0), 0.01, places=9)

    def test_step_fraction_rejects_a_backward_step(self):
        with self.assertRaises(ValueError):
            step_fraction(101.0, 100.0)

    def test_a_step_exactly_at_the_permitted_fraction_is_allowed(self):
        fraction = step_fraction(100.0, 101.0)
        self.assertAlmostEqual(fraction, DEFAULT_MAX_STEP_FRACTION, places=9)
        self.assertTrue(at_most_fraction(fraction, DEFAULT_MAX_STEP_FRACTION))

    def test_an_oversized_jump_is_reported_with_its_fraction(self):
        oversized = oversized_steps(
            [
                {"frequency_hz": 2.0e6, "dwell_time_s": 2.0},
                {"frequency_hz": 2.4e6, "dwell_time_s": 2.0},
            ]
        )
        self.assertEqual(len(oversized), 1)
        self.assertAlmostEqual(oversized[0]["fraction"], 0.2, places=9)

    def test_a_generated_plan_has_no_oversized_step(self):
        self.assertEqual(oversized_steps(plan_steps()), [])

    def test_non_positive_max_fraction_is_rejected(self):
        with self.assertRaises(ValueError):
            oversized_steps(plan_steps(), max_step_fraction=0.0)


class TestDwell(unittest.TestCase):
    def test_required_dwell_takes_the_response_time_when_it_is_longer(self):
        self.assertAlmostEqual(required_dwell_s(3.0, 1.0), 3.0, places=9)

    def test_required_dwell_holds_the_floor_when_the_response_is_fast(self):
        self.assertAlmostEqual(
            required_dwell_s(0.2, DEFAULT_MIN_DWELL_S), DEFAULT_MIN_DWELL_S, places=9
        )

    def test_a_dwell_exactly_at_the_requirement_is_not_short(self):
        requirement = required_dwell_s(RESPONSE_S)
        self.assertAlmostEqual(requirement, RESPONSE_S, places=9)
        self.assertTrue(at_least_time(requirement, RESPONSE_S))
        self.assertEqual(short_dwells(plan_steps(RESPONSE_S), RESPONSE_S), [])

    def test_a_short_dwell_is_reported_with_its_requirement(self):
        brief = short_dwells(plan_steps(0.25), RESPONSE_S)
        self.assertTrue(brief)
        self.assertAlmostEqual(brief[0]["required_dwell_s"], RESPONSE_S, places=9)

    def test_non_positive_response_time_is_rejected(self):
        with self.assertRaises(ValueError):
            required_dwell_s(0.0)


class TestRangeCoverage(unittest.TestCase):
    def test_a_generated_plan_covers_both_ends(self):
        self.assertEqual(
            range_coverage_gaps(plan_steps(), RANGE_START, RANGE_STOP), []
        )

    def test_a_plan_starting_above_the_range_start_is_reported(self):
        steps = plan_steps()[1:]
        gaps = range_coverage_gaps(steps, RANGE_START, RANGE_STOP)
        self.assertEqual(len(gaps), 1)
        self.assertIn("range start", gaps[0])

    def test_a_plan_stopping_below_the_range_stop_is_reported(self):
        steps = plan_steps()[:-1]
        gaps = range_coverage_gaps(steps, RANGE_START, RANGE_STOP)
        self.assertEqual(len(gaps), 1)
        self.assertIn("range stop", gaps[0])


class TestStepPlan(unittest.TestCase):
    def test_plan_starts_on_the_range_start_and_ends_on_the_range_stop(self):
        plan = plan_steps()
        self.assertAlmostEqual(plan[0]["frequency_hz"], RANGE_START, places=3)
        self.assertAlmostEqual(plan[-1]["frequency_hz"], RANGE_STOP, places=3)

    def test_plan_steps_increase_strictly(self):
        plan = plan_steps()
        for index in range(1, len(plan)):
            self.assertGreater(
                plan[index]["frequency_hz"], plan[index - 1]["frequency_hz"]
            )

    def test_a_finer_fraction_produces_more_steps(self):
        coarse = generate_step_plan(RANGE_START, RANGE_STOP, 0.01, 1.0)
        fine = generate_step_plan(RANGE_START, RANGE_STOP, 0.002, 1.0)
        self.assertGreater(len(fine), len(coarse))

    def test_plan_rejects_a_non_positive_fraction(self):
        with self.assertRaises(ValueError):
            generate_step_plan(RANGE_START, RANGE_STOP, 0.0, 1.0)

    def test_scan_duration_sums_dwell_and_settling(self):
        plan = generate_step_plan(RANGE_START, RANGE_STOP, 0.01, 2.0)
        duration = scan_duration_s(plan, settling_time_s=0.5)
        self.assertAlmostEqual(duration, 2.5 * len(plan), places=9)

    def test_scan_duration_rejects_negative_settling(self):
        with self.assertRaises(ValueError):
            scan_duration_s(plan_steps(), settling_time_s=-1.0)


class TestFullAssessment(unittest.TestCase):
    def test_a_compliant_stepped_scan_is_accepted(self):
        report = assess_susceptibility_frequency_stepping(
            SCAN_MODE_STEPPED, plan_steps(), RANGE_START, RANGE_STOP, RESPONSE_S
        )
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], "range-stepped")

    def test_a_continuous_scan_is_rejected(self):
        report = assess_susceptibility_frequency_stepping(
            SCAN_MODE_CONTINUOUS, plan_steps(), RANGE_START, RANGE_STOP, RESPONSE_S
        )
        self.assertEqual(report["verdict"], "scan-rejected")
        self.assertTrue(any("stepping the stimulus" in f for f in report["findings"]))

    def test_an_uncovered_range_end_is_a_finding(self):
        report = assess_susceptibility_frequency_stepping(
            SCAN_MODE_STEPPED, plan_steps()[:-1], RANGE_START, RANGE_STOP, RESPONSE_S
        )
        self.assertTrue(any("range stop" in f for f in report["findings"]))

    def test_an_oversized_step_is_a_finding(self):
        steps = [
            {"frequency_hz": RANGE_START, "dwell_time_s": RESPONSE_S},
            {"frequency_hz": RANGE_STOP, "dwell_time_s": RESPONSE_S},
        ]
        report = assess_susceptibility_frequency_stepping(
            SCAN_MODE_STEPPED, steps, RANGE_START, RANGE_STOP, RESPONSE_S
        )
        self.assertEqual(len(report["oversized_steps"]), 1)
        self.assertEqual(report["verdict"], "scan-rejected")

    def test_a_short_dwell_is_a_finding(self):
        report = assess_susceptibility_frequency_stepping(
            SCAN_MODE_STEPPED, plan_steps(0.25), RANGE_START, RANGE_STOP, RESPONSE_S
        )
        self.assertTrue(report["short_dwells"])
        self.assertEqual(report["verdict"], "scan-rejected")

    def test_report_carries_the_step_count_and_duration(self):
        plan = plan_steps()
        report = assess_susceptibility_frequency_stepping(
            SCAN_MODE_STEPPED, plan, RANGE_START, RANGE_STOP, RESPONSE_S
        )
        self.assertEqual(report["step_count"], len(plan))
        self.assertAlmostEqual(
            report["scan_duration_s"], RESPONSE_S * len(plan), places=9
        )

    def test_assessment_propagates_a_step_error(self):
        with self.assertRaises(ValueError):
            assess_susceptibility_frequency_stepping(
                SCAN_MODE_STEPPED, [], RANGE_START, RANGE_STOP, RESPONSE_S
            )

    def test_assessment_rejects_an_unknown_mode(self):
        with self.assertRaises(ValueError):
            assess_susceptibility_frequency_stepping(
                "drifting", plan_steps(), RANGE_START, RANGE_STOP, RESPONSE_S
            )


if __name__ == "__main__":
    unittest.main()
