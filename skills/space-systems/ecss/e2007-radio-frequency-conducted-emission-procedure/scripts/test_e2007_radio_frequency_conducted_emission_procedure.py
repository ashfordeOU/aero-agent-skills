#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radio-frequency-conducted-emission-procedure.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radio_frequency_conducted_emission_procedure.py
"""

import unittest

from e2007_radio_frequency_conducted_emission_procedure_logic import (
    DEFAULT_CHAIN_TOLERANCE_DB,
    DEFAULT_DRIFT_TOLERANCE_DB,
    DEFAULT_WARMUP_MINUTES,
    DETECTOR_AVERAGE,
    DETECTOR_PEAK,
    DETECTORS,
    MANDATORY_PHASES,
    PHASE_AMBIENT_CHECK,
    PHASE_DATA_CAPTURE,
    PHASE_POST_VERIFICATION,
    PHASE_PRE_VERIFICATION,
    PHASE_WARMUP,
    VERDICT_REJECTED,
    VERDICT_VALID,
    assess_procedure,
    at_least,
    at_most,
    chain_drift_db,
    chain_error_db,
    expected_readback_dbuv,
    minimum_sweep_time_s,
    normalize_detector,
    normalize_phase,
    segment_coverage,
    sequence_phases,
    validate_capture_segment,
    warmup_headroom_minutes,
)

BAND = (1.0e5, 1.0e8)


def all_phases():
    return list(MANDATORY_PHASES)


def good_verification(**over):
    record = {
        "injected_dbua": 40.0,
        "transfer_impedance_dbohm": 14.0,
        "insertion_loss_db": 2.0,
        "pre_read_back_dbuv": 52.5,
        "post_read_back_dbuv": 53.0,
    }
    record.update(over)
    return record


def good_segments():
    return [
        {
            "low_hz": 1.0e5,
            "high_hz": 1.0e6,
            "bandwidth_hz": 1.0e3,
            "sweep_time_s": 5.0,
            "detector": DETECTOR_PEAK,
        },
        {
            "low_hz": 1.0e6,
            "high_hz": 1.0e8,
            "bandwidth_hz": 1.0e4,
            "sweep_time_s": 10.0,
            "detector": DETECTOR_PEAK,
        },
    ]


class TestPhaseNormalization(unittest.TestCase):
    def test_every_mandatory_phase_normalizes(self):
        for phase in MANDATORY_PHASES:
            self.assertEqual(normalize_phase(phase.upper()), phase)

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(normalize_phase("  data-capture "), PHASE_DATA_CAPTURE)

    def test_unrecognized_phase_rejected(self):
        with self.assertRaises(ValueError):
            normalize_phase("tea-break")

    def test_non_string_phase_rejected(self):
        with self.assertRaises(ValueError):
            normalize_phase(7)


class TestDetectorNormalization(unittest.TestCase):
    def test_every_detector_normalizes(self):
        for detector in DETECTORS:
            self.assertEqual(normalize_detector(detector.upper()), detector)

    def test_unrecognized_detector_rejected(self):
        with self.assertRaises(ValueError):
            normalize_detector("root-mean-square")


class TestSequencing(unittest.TestCase):
    def test_full_sequence_is_complete_and_ordered(self):
        report = sequence_phases(all_phases())
        self.assertEqual(report["missing"], [])
        self.assertFalse(report["out_of_order"])

    def test_verification_after_capture_is_out_of_order(self):
        swapped = [
            PHASE_WARMUP,
            PHASE_AMBIENT_CHECK,
            PHASE_DATA_CAPTURE,
            PHASE_PRE_VERIFICATION,
            PHASE_POST_VERIFICATION,
        ]
        self.assertTrue(sequence_phases(swapped)["out_of_order"])

    def test_absent_phase_is_reported(self):
        report = sequence_phases([p for p in MANDATORY_PHASES if p != PHASE_AMBIENT_CHECK])
        self.assertEqual(report["missing"], [PHASE_AMBIENT_CHECK])
        self.assertFalse(report["out_of_order"])

    def test_repeated_phase_rejected(self):
        with self.assertRaises(ValueError):
            sequence_phases([PHASE_WARMUP, PHASE_WARMUP])

    def test_empty_phase_list_rejected(self):
        with self.assertRaises(ValueError):
            sequence_phases([])


class TestWarmup(unittest.TestCase):
    def test_headroom_is_the_excess_soak(self):
        self.assertAlmostEqual(warmup_headroom_minutes(45.0, 30.0), 15.0, places=9)

    def test_exactly_met_soak_gives_zero_headroom(self):
        self.assertAlmostEqual(
            warmup_headroom_minutes(DEFAULT_WARMUP_MINUTES), 0.0, places=9
        )

    def test_short_soak_is_negative(self):
        self.assertLess(warmup_headroom_minutes(10.0, 30.0), 0.0)

    def test_negative_elapsed_rejected(self):
        with self.assertRaises(ValueError):
            warmup_headroom_minutes(-1.0)

    def test_non_positive_requirement_rejected(self):
        with self.assertRaises(ValueError):
            warmup_headroom_minutes(30.0, 0.0)


class TestChainVerification(unittest.TestCase):
    def test_expected_level_adds_current_and_transfer_impedance(self):
        self.assertAlmostEqual(expected_readback_dbuv(40.0, 14.0), 54.0, places=9)

    def test_insertion_loss_is_subtracted(self):
        self.assertAlmostEqual(expected_readback_dbuv(40.0, 14.0, 2.0), 52.0, places=9)

    def test_negative_insertion_loss_rejected(self):
        with self.assertRaises(ValueError):
            expected_readback_dbuv(40.0, 14.0, -1.0)

    def test_error_is_a_magnitude_so_reading_high_counts(self):
        high = chain_error_db(55.0, 40.0, 14.0, 2.0)
        low = chain_error_db(49.0, 40.0, 14.0, 2.0)
        self.assertAlmostEqual(high, 3.0, places=9)
        self.assertAlmostEqual(low, 3.0, places=9)

    def test_drift_is_a_magnitude(self):
        self.assertAlmostEqual(chain_drift_db(52.0, 50.5), 1.5, places=9)
        self.assertAlmostEqual(chain_drift_db(50.5, 52.0), 1.5, places=9)

    def test_non_numeric_read_back_rejected(self):
        with self.assertRaises(ValueError):
            chain_error_db("52 dBuV", 40.0, 14.0)


class TestSweepTime(unittest.TestCase):
    def test_floor_scales_with_span_over_bandwidth_squared(self):
        self.assertAlmostEqual(minimum_sweep_time_s(1.0e6, 1.0e3), 1.0, places=9)

    def test_halving_the_bandwidth_quadruples_the_floor(self):
        wide = minimum_sweep_time_s(1.0e6, 1.0e3)
        narrow = minimum_sweep_time_s(1.0e6, 5.0e2)
        self.assertAlmostEqual(narrow, 4.0 * wide, places=9)

    def test_non_positive_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            minimum_sweep_time_s(1.0e6, 0.0)

    def test_non_positive_span_rejected(self):
        with self.assertRaises(ValueError):
            minimum_sweep_time_s(0.0, 1.0e3)


class TestCaptureSegment(unittest.TestCase):
    def test_good_segment_is_accepted(self):
        graded = validate_capture_segment(good_segments()[0])
        self.assertTrue(graded["sweep_ok"])
        self.assertTrue(graded["detector_ok"])
        self.assertAlmostEqual(graded["span_hz"], 9.0e5, places=9)

    def test_sweep_exactly_on_the_floor_is_accepted(self):
        segment = {
            "low_hz": 1.0e5,
            "high_hz": 1.1e6,
            "bandwidth_hz": 1.0e3,
            "sweep_time_s": minimum_sweep_time_s(1.0e6, 1.0e3),
        }
        graded = validate_capture_segment(segment)
        self.assertTrue(graded["sweep_ok"])
        self.assertAlmostEqual(
            graded["sweep_time_s"], graded["sweep_floor_s"], places=9
        )

    def test_sweep_far_below_the_floor_is_rejected(self):
        segment = dict(good_segments()[0], sweep_time_s=0.01)
        self.assertFalse(validate_capture_segment(segment)["sweep_ok"])

    def test_wrong_detector_is_flagged(self):
        segment = dict(good_segments()[0], detector=DETECTOR_AVERAGE)
        self.assertFalse(validate_capture_segment(segment)["detector_ok"])

    def test_inverted_segment_rejected(self):
        segment = dict(good_segments()[0], high_hz=1.0e4)
        with self.assertRaises(ValueError):
            validate_capture_segment(segment)

    def test_missing_bandwidth_rejected(self):
        segment = dict(good_segments()[0])
        del segment["bandwidth_hz"]
        with self.assertRaises(ValueError):
            validate_capture_segment(segment)

    def test_non_mapping_segment_rejected(self):
        with self.assertRaises(ValueError):
            validate_capture_segment(["1e5", "1e6"])


class TestCoverage(unittest.TestCase):
    def test_tiled_segments_cover_the_band(self):
        graded = [validate_capture_segment(s) for s in good_segments()]
        report = segment_coverage(graded, BAND[0], BAND[1])
        self.assertTrue(report["covered"])
        self.assertEqual(report["gaps_hz"], [])
        self.assertEqual(report["overlaps_hz"], [])

    def test_gap_between_segments_is_found(self):
        segments = good_segments()
        segments[1]["low_hz"] = 2.0e6
        graded = [validate_capture_segment(s) for s in segments]
        report = segment_coverage(graded, BAND[0], BAND[1])
        self.assertFalse(report["covered"])
        self.assertEqual(len(report["gaps_hz"]), 1)

    def test_band_top_left_uncaptured_is_a_gap(self):
        segments = good_segments()
        segments[1]["high_hz"] = 5.0e7
        graded = [validate_capture_segment(s) for s in segments]
        self.assertFalse(segment_coverage(graded, BAND[0], BAND[1])["covered"])

    def test_overlap_is_reported_without_losing_coverage(self):
        segments = good_segments()
        segments[1]["low_hz"] = 5.0e5
        graded = [validate_capture_segment(s) for s in segments]
        report = segment_coverage(graded, BAND[0], BAND[1])
        self.assertTrue(report["covered"])
        self.assertEqual(len(report["overlaps_hz"]), 1)

    def test_segments_out_of_order_are_sorted_before_grading(self):
        graded = [validate_capture_segment(s) for s in reversed(good_segments())]
        self.assertTrue(segment_coverage(graded, BAND[0], BAND[1])["covered"])

    def test_empty_segment_set_rejected(self):
        with self.assertRaises(ValueError):
            segment_coverage([], BAND[0], BAND[1])


class TestTolerantComparisons(unittest.TestCase):
    def test_at_most_accepts_an_exact_bound(self):
        self.assertTrue(at_most(3.0, 3.0))

    def test_at_least_accepts_an_exact_requirement(self):
        self.assertTrue(at_least(3.0, 3.0))

    def test_at_most_still_rejects_a_real_excess(self):
        self.assertFalse(at_most(3.5, 3.0))


class TestAssessProcedure(unittest.TestCase):
    def test_clean_run_is_valid(self):
        report = assess_procedure(
            all_phases(), 45.0, good_verification(), good_segments(), BAND
        )
        self.assertEqual(report["verdict"], VERDICT_VALID)
        self.assertEqual(report["findings"], [])

    def test_thin_warmup_margin_is_a_limitation_not_a_finding(self):
        report = assess_procedure(
            all_phases(), 31.0, good_verification(), good_segments(), BAND
        )
        self.assertEqual(report["verdict"], VERDICT_VALID)
        self.assertEqual(len(report["limitations"]), 1)

    def test_short_warmup_is_a_finding(self):
        report = assess_procedure(
            all_phases(), 5.0, good_verification(), good_segments(), BAND
        )
        self.assertEqual(report["verdict"], VERDICT_REJECTED)

    def test_chain_error_past_tolerance_is_a_finding(self):
        report = assess_procedure(
            all_phases(),
            45.0,
            good_verification(pre_read_back_dbuv=60.0, post_read_back_dbuv=60.2),
            good_segments(),
            BAND,
        )
        self.assertEqual(report["verdict"], VERDICT_REJECTED)
        self.assertGreater(report["pre_error_db"], DEFAULT_CHAIN_TOLERANCE_DB)

    def test_drift_past_tolerance_is_a_finding(self):
        report = assess_procedure(
            all_phases(),
            45.0,
            good_verification(pre_read_back_dbuv=52.0, post_read_back_dbuv=49.0),
            good_segments(),
            BAND,
        )
        self.assertEqual(report["verdict"], VERDICT_REJECTED)
        self.assertGreater(report["drift_db"], DEFAULT_DRIFT_TOLERANCE_DB)

    def test_coverage_gap_is_a_finding(self):
        segments = good_segments()
        segments[1]["low_hz"] = 2.0e6
        report = assess_procedure(
            all_phases(), 45.0, good_verification(), segments, BAND
        )
        self.assertEqual(report["verdict"], VERDICT_REJECTED)

    def test_overlap_alone_keeps_the_run_valid(self):
        segments = good_segments()
        segments[1]["low_hz"] = 5.0e5
        report = assess_procedure(
            all_phases(), 45.0, good_verification(), segments, BAND
        )
        self.assertEqual(report["verdict"], VERDICT_VALID)
        self.assertEqual(len(report["limitations"]), 1)

    def test_missing_phase_rejects_the_run(self):
        report = assess_procedure(
            [p for p in MANDATORY_PHASES if p != PHASE_PRE_VERIFICATION],
            45.0,
            good_verification(),
            good_segments(),
            BAND,
        )
        self.assertEqual(report["verdict"], VERDICT_REJECTED)

    def test_total_sweep_time_is_the_sum_of_the_segments(self):
        report = assess_procedure(
            all_phases(), 45.0, good_verification(), good_segments(), BAND
        )
        self.assertAlmostEqual(report["total_sweep_time_s"], 15.0, places=9)

    def test_non_mapping_verification_rejected(self):
        with self.assertRaises(ValueError):
            assess_procedure(all_phases(), 45.0, ["40 dBuA"], good_segments(), BAND)

    def test_non_positive_chain_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            assess_procedure(
                all_phases(),
                45.0,
                good_verification(),
                good_segments(),
                BAND,
                chain_tolerance_db=0.0,
            )

    def test_malformed_method_band_rejected(self):
        with self.assertRaises(ValueError):
            assess_procedure(
                all_phases(), 45.0, good_verification(), good_segments(), (1.0e5,)
            )

    def test_report_carries_the_expected_read_back_level(self):
        report = assess_procedure(
            all_phases(), 45.0, good_verification(), good_segments(), BAND
        )
        self.assertAlmostEqual(report["expected_readback_dbuv"], 52.0, places=9)


if __name__ == "__main__":
    unittest.main()
