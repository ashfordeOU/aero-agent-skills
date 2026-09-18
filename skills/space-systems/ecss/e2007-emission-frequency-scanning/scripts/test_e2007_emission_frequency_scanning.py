#!/usr/bin/env python3
"""Gate 3 contract test for e2007-emission-frequency-scanning.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_emission_frequency_scanning.py
"""

import unittest

from e2007_emission_frequency_scanning_logic import (
    COVERAGE_ABSENT,
    COVERAGE_COMPLETE,
    COVERAGE_PARTIAL,
    DEFAULT_DWELL_PER_BANDWIDTH_S,
    assess_emission_frequency_scanning,
    assess_sweep_rate,
    at_least,
    at_most,
    categorize_coverage,
    coverage_fraction,
    covered_span_hz,
    merge_segments,
    minimum_sweep_time_s,
    out_of_band_excursions,
    redundant_overlaps,
    uncovered_intervals,
    validate_band,
    validate_segments,
)

BAND_START = 30.0e6
BAND_STOP = 1000.0e6


def segment(start, stop, bandwidth=120.0e3, sweep_time=None):
    if sweep_time is None:
        cells = (stop - start) / bandwidth if bandwidth > 0.0 else 1.0
        sweep_time = max(cells, 1.0) * DEFAULT_DWELL_PER_BANDWIDTH_S
    return {
        "start_hz": start,
        "stop_hz": stop,
        "resolution_bandwidth_hz": bandwidth,
        "sweep_time_s": sweep_time,
    }


def full_scan():
    return [
        segment(30.0e6, 300.0e6),
        segment(300.0e6, 1000.0e6),
    ]


class TestBandValidation(unittest.TestCase):
    def test_band_normalizes_span(self):
        band = validate_band(BAND_START, BAND_STOP)
        self.assertAlmostEqual(band["span_hz"], 970.0e6, places=3)

    def test_band_rejects_non_positive_start(self):
        with self.assertRaises(ValueError):
            validate_band(0.0, BAND_STOP)

    def test_band_rejects_inverted_edges(self):
        with self.assertRaises(ValueError):
            validate_band(BAND_STOP, BAND_START)

    def test_band_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            validate_band("30 MHz", BAND_STOP)


class TestSegmentValidation(unittest.TestCase):
    def test_segments_are_sorted_by_start(self):
        ordered = validate_segments(list(reversed(full_scan())))
        self.assertAlmostEqual(ordered[0]["start_hz"], 30.0e6, places=3)
        self.assertAlmostEqual(ordered[1]["start_hz"], 300.0e6, places=3)

    def test_empty_segment_list_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_segments([])

    def test_zero_bandwidth_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_segments([segment(30.0e6, 300.0e6, bandwidth=0.0)])

    def test_zero_sweep_time_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_segments([segment(30.0e6, 300.0e6, sweep_time=0.0)])

    def test_boolean_field_is_not_a_number(self):
        bad = segment(30.0e6, 300.0e6)
        bad["sweep_time_s"] = True
        with self.assertRaises(ValueError):
            validate_segments([bad])

    def test_degenerate_segment_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_segments([segment(300.0e6, 300.0e6)])


class TestCoverage(unittest.TestCase):
    def test_touching_segments_merge_into_one_interval(self):
        merged = merge_segments(full_scan())
        self.assertEqual(len(merged), 1)
        self.assertAlmostEqual(merged[0]["stop_hz"], BAND_STOP, places=3)

    def test_disjoint_segments_stay_separate(self):
        merged = merge_segments([segment(30.0e6, 100.0e6), segment(200.0e6, 300.0e6)])
        self.assertEqual(len(merged), 2)

    def test_complete_scan_leaves_no_uncovered_sub_band(self):
        self.assertEqual(uncovered_intervals(full_scan(), BAND_START, BAND_STOP), [])

    def test_interior_gap_is_reported_with_its_width(self):
        gaps = uncovered_intervals(
            [segment(30.0e6, 300.0e6), segment(400.0e6, 1000.0e6)],
            BAND_START,
            BAND_STOP,
        )
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["span_hz"], 100.0e6, places=3)

    def test_missing_top_of_band_is_reported(self):
        gaps = uncovered_intervals([segment(30.0e6, 300.0e6)], BAND_START, BAND_STOP)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["stop_hz"], BAND_STOP, places=3)

    def test_missing_bottom_of_band_is_reported(self):
        gaps = uncovered_intervals([segment(50.0e6, 1000.0e6)], BAND_START, BAND_STOP)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["start_hz"], BAND_START, places=3)

    def test_covered_span_clips_to_the_declared_band(self):
        covered = covered_span_hz(
            [segment(10.0e6, 2000.0e6)], BAND_START, BAND_STOP
        )
        self.assertAlmostEqual(covered, 970.0e6, places=3)

    def test_coverage_fraction_of_a_full_scan_is_one(self):
        self.assertAlmostEqual(
            coverage_fraction(full_scan(), BAND_START, BAND_STOP), 1.0, places=9
        )

    def test_half_scan_gives_a_partial_fraction(self):
        fraction = coverage_fraction(
            [segment(30.0e6, 515.0e6)], BAND_START, BAND_STOP
        )
        self.assertAlmostEqual(fraction, 485.0e6 / 970.0e6, places=9)
        self.assertEqual(categorize_coverage(fraction), COVERAGE_PARTIAL)

    def test_coverage_categories_at_the_bounds(self):
        self.assertEqual(categorize_coverage(1.0), COVERAGE_COMPLETE)
        self.assertEqual(categorize_coverage(0.0), COVERAGE_ABSENT)

    def test_coverage_fraction_outside_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_coverage(1.5)


class TestSweepRate(unittest.TestCase):
    def test_required_sweep_time_scales_with_resolution_cells(self):
        required = minimum_sweep_time_s(segment(30.0e6, 30.12e6, bandwidth=120.0e3))
        self.assertAlmostEqual(required, 1.0 * DEFAULT_DWELL_PER_BANDWIDTH_S, places=9)

    def test_a_segment_narrower_than_one_cell_still_needs_one_dwell(self):
        required = minimum_sweep_time_s(segment(30.0e6, 30.01e6, bandwidth=120.0e3))
        self.assertAlmostEqual(required, DEFAULT_DWELL_PER_BANDWIDTH_S, places=9)

    def test_exactly_sufficient_sweep_time_is_adequate(self):
        seg = segment(30.0e6, 300.0e6)
        rate = assess_sweep_rate(seg)
        self.assertAlmostEqual(
            rate["sweep_time_s"], rate["required_sweep_time_s"], places=9
        )
        self.assertTrue(rate["adequate"])

    def test_a_scan_run_too_fast_is_not_adequate(self):
        seg = segment(30.0e6, 300.0e6, sweep_time=0.5)
        self.assertFalse(assess_sweep_rate(seg)["adequate"])

    def test_non_positive_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            minimum_sweep_time_s(segment(30.0e6, 300.0e6), dwell_per_bandwidth_s=0.0)


class TestExcursionsAndOverlaps(unittest.TestCase):
    def test_in_band_scan_reports_no_excursion(self):
        self.assertEqual(out_of_band_excursions(full_scan(), BAND_START, BAND_STOP), [])

    def test_segment_reaching_past_the_band_is_reported(self):
        excursions = out_of_band_excursions(
            [segment(30.0e6, 1200.0e6)], BAND_START, BAND_STOP
        )
        self.assertEqual(len(excursions), 1)
        self.assertAlmostEqual(excursions[0]["above_hz"], 200.0e6, places=3)

    def test_touching_segments_are_not_an_overlap(self):
        self.assertEqual(redundant_overlaps(full_scan()), [])

    def test_genuine_overlap_reports_its_width(self):
        overlaps = redundant_overlaps(
            [segment(30.0e6, 320.0e6), segment(300.0e6, 1000.0e6)]
        )
        self.assertEqual(len(overlaps), 1)
        self.assertAlmostEqual(overlaps[0]["overlap_hz"], 20.0e6, places=3)


class TestTolerantComparators(unittest.TestCase):
    def test_at_least_accepts_an_exact_match(self):
        self.assertTrue(at_least(1.0, 1.0))

    def test_at_most_accepts_an_exact_match(self):
        self.assertTrue(at_most(1.0, 1.0))

    def test_at_least_rejects_a_real_shortfall(self):
        self.assertFalse(at_least(0.5, 1.0))


class TestFullAssessment(unittest.TestCase):
    def test_complete_run_is_span_swept(self):
        report = assess_emission_frequency_scanning(BAND_START, BAND_STOP, full_scan())
        self.assertEqual(report["verdict"], "span-swept")
        self.assertEqual(report["coverage"], COVERAGE_COMPLETE)
        self.assertEqual(report["findings"], [])

    def test_gap_forces_a_rescan(self):
        report = assess_emission_frequency_scanning(
            BAND_START,
            BAND_STOP,
            [segment(30.0e6, 300.0e6), segment(400.0e6, 1000.0e6)],
        )
        self.assertEqual(report["verdict"], "rescan-required")
        self.assertEqual(report["coverage"], COVERAGE_PARTIAL)
        self.assertTrue(any("uncovered sub-band" in f for f in report["findings"]))

    def test_too_fast_segment_forces_a_rescan_even_with_full_coverage(self):
        report = assess_emission_frequency_scanning(
            BAND_START,
            BAND_STOP,
            [segment(30.0e6, 300.0e6), segment(300.0e6, 1000.0e6, sweep_time=0.1)],
        )
        self.assertEqual(report["coverage"], COVERAGE_COMPLETE)
        self.assertEqual(report["verdict"], "rescan-required")

    def test_overlap_is_a_limitation_not_a_finding(self):
        report = assess_emission_frequency_scanning(
            BAND_START,
            BAND_STOP,
            [segment(30.0e6, 320.0e6), segment(300.0e6, 1000.0e6)],
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("redundant overlap" in m for m in report["limitations"]))
        self.assertEqual(report["verdict"], "span-swept")

    def test_assessment_propagates_a_segment_error(self):
        with self.assertRaises(ValueError):
            assess_emission_frequency_scanning(BAND_START, BAND_STOP, [])

    def test_report_carries_the_merged_union(self):
        report = assess_emission_frequency_scanning(BAND_START, BAND_STOP, full_scan())
        self.assertEqual(len(report["merged"]), 1)
        self.assertAlmostEqual(report["covered_span_hz"], 970.0e6, places=3)


if __name__ == "__main__":
    unittest.main()
