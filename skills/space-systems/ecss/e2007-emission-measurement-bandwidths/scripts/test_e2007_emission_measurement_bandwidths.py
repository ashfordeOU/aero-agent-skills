#!/usr/bin/env python3
"""Contract test for the emission measurement bandwidths leaf."""

import unittest

from e2007_emission_measurement_bandwidths_logic import (
    DWELL_BANDWIDTH_PRODUCT,
    EMISSION_RANGES,
    MAX_STEP_FRACTION_OF_BANDWIDTH,
    MIN_DWELL_FLOOR_S,
    SWEEP_LOWER_HZ,
    SWEEP_UPPER_HZ,
    assess_emission_sweep,
    check_applied_bandwidth,
    check_dwell,
    check_step,
    evaluate_sweep_point,
    maximum_step_hz,
    minimum_dwell_s,
    plan_emission_sweep,
    prescribed_bandwidth_hz,
    select_emission_range,
    span_segments,
)


def good_point(**overrides):
    point = {
        "id": "P-1",
        "frequency_hz": 1.0e8,
        "applied_bandwidth_hz": 1.0e5,
        "dwell_s": 0.05,
    }
    point.update(overrides)
    return point


def sweep():
    return [
        good_point(id="P-1", frequency_hz=1.0e8),
        good_point(id="P-2", frequency_hz=1.00004e8),
        good_point(id="P-3", frequency_hz=1.00008e8),
    ]


class TestRangeSelection(unittest.TestCase):
    def test_low_frequency_selects_the_first_range(self):
        band = select_emission_range(100.0)
        self.assertAlmostEqual(band["bandwidth_hz"], 10.0, places=9)

    def test_high_frequency_selects_the_last_range(self):
        band = select_emission_range(1.0e10)
        self.assertAlmostEqual(band["bandwidth_hz"], 1.0e6, places=3)

    def test_boundary_frequency_belongs_to_the_lower_range(self):
        self.assertAlmostEqual(prescribed_bandwidth_hz(1.0e3), 10.0, places=9)

    def test_ranges_are_contiguous_and_ascending(self):
        for earlier, later in zip(EMISSION_RANGES, EMISSION_RANGES[1:]):
            self.assertAlmostEqual(earlier[1], later[0], places=6)
            self.assertLess(earlier[2], later[2])

    def test_frequency_below_the_sweep_raises(self):
        with self.assertRaises(ValueError):
            select_emission_range(SWEEP_LOWER_HZ / 2.0)

    def test_frequency_above_the_sweep_raises(self):
        with self.assertRaises(ValueError):
            select_emission_range(SWEEP_UPPER_HZ * 2.0)

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            select_emission_range(0.0)

    def test_non_numeric_frequency_raises(self):
        with self.assertRaises(ValueError):
            select_emission_range("100")

    def test_boolean_frequency_raises(self):
        with self.assertRaises(ValueError):
            select_emission_range(True)


class TestAppliedBandwidth(unittest.TestCase):
    def test_prescribed_bandwidth_is_accepted(self):
        result = check_applied_bandwidth(1.0e8, 1.0e5)
        self.assertTrue(result["as_prescribed"])
        self.assertAlmostEqual(result["ratio"], 1.0, places=12)

    def test_narrow_bandwidth_is_refused(self):
        result = check_applied_bandwidth(1.0e8, 3.0e4)
        self.assertFalse(result["as_prescribed"])
        self.assertAlmostEqual(result["ratio"], 0.3, places=9)

    def test_wide_bandwidth_is_refused(self):
        self.assertFalse(check_applied_bandwidth(1.0e8, 1.0e6)["as_prescribed"])

    def test_last_place_difference_still_counts_as_prescribed(self):
        nudged = 1.0e5 * (1.0 + 1.0e-13)
        self.assertTrue(check_applied_bandwidth(1.0e8, nudged)["as_prescribed"])

    def test_zero_bandwidth_raises(self):
        with self.assertRaises(ValueError):
            check_applied_bandwidth(1.0e8, 0.0)

    def test_negative_bandwidth_raises(self):
        with self.assertRaises(ValueError):
            check_applied_bandwidth(1.0e8, -1.0e5)


class TestStepAndDwell(unittest.TestCase):
    def test_step_is_a_fraction_of_the_bandwidth(self):
        self.assertAlmostEqual(
            maximum_step_hz(1.0e8),
            1.0e5 * MAX_STEP_FRACTION_OF_BANDWIDTH,
            places=6,
        )

    def test_step_fraction_above_one_raises(self):
        with self.assertRaises(ValueError):
            maximum_step_hz(1.0e8, fraction=1.5)

    def test_dwell_follows_the_bandwidth_in_the_low_range(self):
        self.assertAlmostEqual(
            minimum_dwell_s(100.0), DWELL_BANDWIDTH_PRODUCT / 10.0, places=9
        )

    def test_dwell_is_floored_in_the_wide_ranges(self):
        self.assertAlmostEqual(minimum_dwell_s(1.0e8), MIN_DWELL_FLOOR_S, places=9)

    def test_exact_step_limit_is_accepted(self):
        allowed = maximum_step_hz(1.0e8)
        result = check_step(1.0e8, 1.0e8 + allowed)
        self.assertAlmostEqual(result["step_hz"], result["allowed_hz"], places=6)
        self.assertTrue(result["within"])

    def test_coarse_step_is_refused(self):
        self.assertFalse(check_step(1.0e8, 1.0e8 + 5.0e5)["within"])

    def test_backward_step_raises(self):
        with self.assertRaises(ValueError):
            check_step(1.0e8, 9.0e7)

    def test_repeated_frequency_step_raises(self):
        with self.assertRaises(ValueError):
            check_step(1.0e8, 1.0e8)

    def test_exact_dwell_minimum_is_accepted(self):
        required = minimum_dwell_s(1.0e8)
        result = check_dwell(1.0e8, required)
        self.assertAlmostEqual(result["dwell_s"], result["required_s"], places=9)
        self.assertTrue(result["within"])

    def test_short_dwell_is_refused(self):
        self.assertFalse(check_dwell(100.0, 0.05)["within"])

    def test_zero_dwell_raises(self):
        with self.assertRaises(ValueError):
            check_dwell(1.0e8, 0.0)


class TestSpanSegments(unittest.TestCase):
    def test_span_inside_one_range_gives_one_segment(self):
        segments = span_segments(4.0e7, 5.0e7)
        self.assertEqual(len(segments), 1)
        self.assertAlmostEqual(segments[0]["bandwidth_hz"], 1.0e5, places=3)

    def test_span_across_a_boundary_splits(self):
        segments = span_segments(1.4e5, 1.6e5)
        self.assertEqual(len(segments), 2)
        self.assertAlmostEqual(segments[0]["bandwidth_hz"], 1.0e3, places=6)
        self.assertAlmostEqual(segments[1]["bandwidth_hz"], 1.0e4, places=6)

    def test_segments_tile_the_span_without_gaps(self):
        segments = span_segments(1.0e4, 1.0e8)
        self.assertAlmostEqual(segments[0]["lower_hz"], 1.0e4, places=3)
        self.assertAlmostEqual(segments[-1]["upper_hz"], 1.0e8, places=3)
        for earlier, later in zip(segments, segments[1:]):
            self.assertAlmostEqual(earlier["upper_hz"], later["lower_hz"], places=3)

    def test_descending_span_raises(self):
        with self.assertRaises(ValueError):
            span_segments(1.0e8, 1.0e7)

    def test_span_leaving_the_measured_range_raises(self):
        with self.assertRaises(ValueError):
            span_segments(1.0, 1.0e8)


class TestPlanEmissionSweep(unittest.TestCase):
    def test_point_count_is_intervals_plus_one(self):
        plan = plan_emission_sweep(3.0e7, 3.05e7)
        self.assertEqual(plan["segment_count"], 1)
        self.assertEqual(plan["point_count"], 11)

    def test_exact_interval_does_not_add_a_spare_point(self):
        allowed = maximum_step_hz(4.0e7)
        plan = plan_emission_sweep(4.0e7, 4.0e7 + 10.0 * allowed)
        self.assertEqual(plan["point_count"], 11)

    def test_partial_interval_adds_a_point(self):
        allowed = maximum_step_hz(4.0e7)
        plan = plan_emission_sweep(4.0e7, 4.0e7 + 10.5 * allowed)
        self.assertEqual(plan["point_count"], 12)

    def test_crossing_span_sums_both_segments(self):
        plan = plan_emission_sweep(1.4e5, 1.6e5)
        self.assertEqual(plan["segment_count"], 2)
        self.assertEqual(
            plan["point_count"],
            sum(segment["point_count"] for segment in plan["segments"]),
        )

    def test_sweep_time_is_points_times_dwell(self):
        plan = plan_emission_sweep(3.0e7, 3.05e7)
        segment = plan["segments"][0]
        self.assertAlmostEqual(
            segment["seconds"], segment["point_count"] * segment["dwell_s"], places=9
        )

    def test_narrow_bandwidth_costs_more_points(self):
        narrow = plan_emission_sweep(1.0e4, 2.0e4)
        wide = plan_emission_sweep(4.0e7, 4.001e7)
        self.assertGreater(narrow["point_count"], wide["point_count"])


class TestEvaluateSweepPoint(unittest.TestCase):
    def test_conforming_point_has_no_finding(self):
        record = evaluate_sweep_point(good_point())
        self.assertTrue(record["conforming"])
        self.assertEqual(record["findings"], [])

    def test_wrong_bandwidth_is_a_finding(self):
        record = evaluate_sweep_point(good_point(applied_bandwidth_hz=1.0e4))
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("bandwidth-not-as-prescribed", codes)

    def test_short_dwell_is_a_finding(self):
        record = evaluate_sweep_point(
            good_point(frequency_hz=100.0, applied_bandwidth_hz=10.0, dwell_s=0.02)
        )
        codes = [finding["code"] for finding in record["findings"]]
        self.assertIn("dwell-too-short", codes)

    def test_dwell_is_optional(self):
        point = good_point()
        del point["dwell_s"]
        record = evaluate_sweep_point(point)
        self.assertNotIn("dwell", record["checks"])
        self.assertTrue(record["conforming"])

    def test_unknown_key_raises(self):
        with self.assertRaises(ValueError):
            evaluate_sweep_point(good_point(detector="peak"))

    def test_missing_bandwidth_raises(self):
        point = good_point()
        del point["applied_bandwidth_hz"]
        with self.assertRaises(ValueError):
            evaluate_sweep_point(point)

    def test_blank_identifier_raises(self):
        with self.assertRaises(ValueError):
            evaluate_sweep_point(good_point(id="  "))

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            evaluate_sweep_point(["P-1"])

    def test_findings_carry_code_subject_and_detail(self):
        record = evaluate_sweep_point(good_point(applied_bandwidth_hz=1.0e4))
        for finding in record["findings"]:
            self.assertEqual(sorted(finding.keys()), ["code", "detail", "subject"])


class TestAssessEmissionSweep(unittest.TestCase):
    def test_good_sweep_is_conforming(self):
        report = assess_emission_sweep(sweep())
        self.assertEqual(report["verdict"], "conforming")
        self.assertTrue(report["accepted"])
        self.assertAlmostEqual(report["conforming_fraction"], 1.0, places=12)

    def test_step_count_is_one_less_than_the_points(self):
        report = assess_emission_sweep(sweep())
        self.assertEqual(report["step_count"], report["point_count"] - 1)

    def test_coarse_sweep_is_refused(self):
        points = [
            good_point(id="P-1", frequency_hz=1.0e8),
            good_point(id="P-2", frequency_hz=1.005e8),
        ]
        report = assess_emission_sweep(points)
        codes = [finding["code"] for finding in report["findings"]]
        self.assertIn("step-too-coarse", codes)
        self.assertIn("sweep-under-sampled", codes)
        self.assertFalse(report["accepted"])

    def test_non_ascending_sweep_is_a_finding(self):
        points = sweep()
        points[2]["frequency_hz"] = 1.00002e8
        codes = [
            finding["code"] for finding in assess_emission_sweep(points)["findings"]
        ]
        self.assertIn("sweep-not-ascending", codes)

    def test_wrong_bandwidth_lowers_the_conforming_fraction(self):
        points = sweep()
        points[1]["applied_bandwidth_hz"] = 1.0e3
        report = assess_emission_sweep(points)
        self.assertAlmostEqual(report["conforming_fraction"], 2.0 / 3.0, places=12)

    def test_single_point_sweep_has_no_required_plan(self):
        report = assess_emission_sweep([good_point()])
        self.assertIsNone(report["required_plan"])

    def test_repeated_identifier_raises(self):
        with self.assertRaises(ValueError):
            assess_emission_sweep([good_point(), good_point()])

    def test_empty_sweep_raises(self):
        with self.assertRaises(ValueError):
            assess_emission_sweep([])

    def test_string_sweep_raises(self):
        with self.assertRaises(ValueError):
            assess_emission_sweep("P-1")


if __name__ == "__main__":
    unittest.main()
