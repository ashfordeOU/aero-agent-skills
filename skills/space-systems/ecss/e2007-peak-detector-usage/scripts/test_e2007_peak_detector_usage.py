#!/usr/bin/env python3
"""Gate 3 contract test for e2007-peak-detector-usage.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_peak_detector_usage.py
"""

import unittest

from e2007_peak_detector_usage_logic import (
    CATEGORY_COMPLIANT,
    CATEGORY_MARGINAL,
    CATEGORY_NONCOMPLIANT,
    DEFAULT_MAX_BIN_STEP_FRACTION,
    DETECTOR_AVERAGE,
    DETECTOR_PEAK,
    DETECTOR_QUASI_PEAK,
    PURPOSE_EMISSION,
    PURPOSE_SUSCEPTIBILITY,
    RECOGNIZED_DETECTORS,
    UNDERSTATING_DETECTORS,
    assess_peak_detector_usage,
    at_least,
    at_most,
    bandwidth_response_time_s,
    bin_step_findings,
    bin_step_hz,
    detector_findings,
    dwell_findings,
    dwell_per_bin_s,
    grade_run,
    maximum_bin_step_hz,
    minimum_dwell_s,
    minimum_sweep_time_s,
    normalize_detector,
    normalize_purpose,
    pulse_repetition_interval_s,
    validate_frequency_domain_run,
)


def good_run(**over):
    record = {
        "id": "re102-sweep-1",
        "purpose": "emission",
        "detector": "peak",
        "span_hz": 1.0e6,
        "points": 1001,
        "sweep_time_s": 20.0,
        "resolution_bandwidth_hz": 10.0e3,
        "pulse_repetition_rate_hz": 1000.0,
    }
    record.update(over)
    return record


class PeakDetectorUsageTest(unittest.TestCase):
    # --- detector and purpose normalisation ----------------------------

    def test_peak_is_a_recognized_detector(self):
        self.assertIn(DETECTOR_PEAK, RECOGNIZED_DETECTORS)

    def test_understating_detectors_exclude_peak(self):
        self.assertNotIn(DETECTOR_PEAK, UNDERSTATING_DETECTORS)

    def test_detector_aliases_normalise_to_peak(self):
        self.assertEqual(normalize_detector("  Peak_Detector "), DETECTOR_PEAK)
        self.assertEqual(normalize_detector("PK"), DETECTOR_PEAK)

    def test_quasi_peak_aliases_normalise_separately(self):
        self.assertEqual(normalize_detector("quasipeak"), DETECTOR_QUASI_PEAK)

    def test_unknown_detector_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_detector("log-video")

    def test_non_string_detector_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_detector(None)

    def test_both_measurement_purposes_are_recognized(self):
        self.assertEqual(normalize_purpose("Emission"), PURPOSE_EMISSION)
        self.assertEqual(normalize_purpose("susceptibility"), PURPOSE_SUSCEPTIBILITY)

    def test_unknown_purpose_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_purpose("thermal")

    # --- setup validation ----------------------------------------------

    def test_run_requires_at_least_two_points(self):
        with self.assertRaises(ValueError):
            validate_frequency_domain_run(good_run(points=1))

    def test_run_rejects_a_non_integer_point_count(self):
        with self.assertRaises(ValueError):
            validate_frequency_domain_run(good_run(points=1000.5))

    def test_run_rejects_a_non_positive_sweep_time(self):
        with self.assertRaises(ValueError):
            validate_frequency_domain_run(good_run(sweep_time_s=0.0))

    def test_run_rejects_a_non_positive_resolution_bandwidth(self):
        with self.assertRaises(ValueError):
            validate_frequency_domain_run(good_run(resolution_bandwidth_hz=-1.0))

    def test_run_rejects_a_non_positive_pulse_repetition_rate(self):
        with self.assertRaises(ValueError):
            validate_frequency_domain_run(good_run(pulse_repetition_rate_hz=0.0))

    def test_run_requires_an_identifier(self):
        with self.assertRaises(ValueError):
            validate_frequency_domain_run(good_run(id="   "))

    def test_run_rejects_a_non_mapping_record(self):
        with self.assertRaises(ValueError):
            validate_frequency_domain_run(["re102"])

    def test_absent_pulse_rate_is_allowed_and_recorded_as_none(self):
        record = validate_frequency_domain_run(good_run(pulse_repetition_rate_hz=None))
        self.assertIsNone(record["pulse_repetition_rate_hz"])

    # --- derived sweep quantities ---------------------------------------

    def test_bin_step_spans_the_gaps_between_points(self):
        record = validate_frequency_domain_run(good_run())
        self.assertAlmostEqual(bin_step_hz(record), 1000.0, places=9)

    def test_dwell_per_bin_divides_the_sweep_across_the_points(self):
        record = validate_frequency_domain_run(good_run())
        self.assertAlmostEqual(dwell_per_bin_s(record), 20.0 / 1001.0, places=9)

    def test_bandwidth_response_time_is_the_reciprocal_bandwidth(self):
        self.assertAlmostEqual(bandwidth_response_time_s(10.0e3), 1.0e-4, places=12)

    def test_bandwidth_response_time_rejects_a_zero_bandwidth(self):
        with self.assertRaises(ValueError):
            bandwidth_response_time_s(0.0)

    def test_pulse_interval_is_the_reciprocal_repetition_rate(self):
        self.assertAlmostEqual(pulse_repetition_interval_s(1000.0), 1.0e-3, places=12)

    def test_minimum_dwell_takes_the_pulse_interval_when_it_dominates(self):
        record = validate_frequency_domain_run(good_run())
        self.assertAlmostEqual(minimum_dwell_s(record), 1.0e-3, places=12)

    def test_minimum_dwell_falls_back_to_the_bandwidth_response_time(self):
        record = validate_frequency_domain_run(
            good_run(pulse_repetition_rate_hz=None)
        )
        self.assertAlmostEqual(minimum_dwell_s(record), 1.0e-4, places=12)

    def test_minimum_sweep_time_scales_the_dwell_by_the_point_count(self):
        record = validate_frequency_domain_run(good_run())
        self.assertAlmostEqual(minimum_sweep_time_s(record), 1.001, places=9)

    def test_maximum_bin_step_is_a_fraction_of_the_resolution_bandwidth(self):
        record = validate_frequency_domain_run(good_run())
        self.assertAlmostEqual(
            maximum_bin_step_hz(record),
            10.0e3 * DEFAULT_MAX_BIN_STEP_FRACTION,
            places=9,
        )

    def test_maximum_bin_step_rejects_a_fraction_above_one(self):
        record = validate_frequency_domain_run(good_run())
        with self.assertRaises(ValueError):
            maximum_bin_step_hz(record, 1.5)

    def test_tolerance_helpers_absorb_representation_error_only(self):
        self.assertTrue(at_least(1.0, 1.0))
        self.assertTrue(at_most(1.0, 1.0))
        self.assertFalse(at_least(0.5, 1.0))
        self.assertFalse(at_most(2.0, 1.0))

    # --- findings --------------------------------------------------------

    def test_peak_detector_raises_no_detector_finding(self):
        record = validate_frequency_domain_run(good_run())
        self.assertEqual(detector_findings(record), [])

    def test_average_detector_is_reported_for_an_emission_sweep(self):
        record = validate_frequency_domain_run(good_run(detector=DETECTOR_AVERAGE))
        self.assertEqual(len(detector_findings(record)), 1)

    def test_average_detector_is_reported_for_a_susceptibility_sweep_too(self):
        record = validate_frequency_domain_run(
            good_run(purpose="susceptibility", detector=DETECTOR_AVERAGE)
        )
        self.assertEqual(len(detector_findings(record)), 1)

    def test_quasi_peak_detector_is_reported_as_understating_the_peak(self):
        record = validate_frequency_domain_run(good_run(detector="quasi-peak"))
        self.assertEqual(len(detector_findings(record)), 1)

    def test_a_sweep_exactly_at_the_dwell_bound_raises_no_finding(self):
        record = validate_frequency_domain_run(
            good_run(points=1000, sweep_time_s=1.0)
        )
        self.assertAlmostEqual(dwell_per_bin_s(record), minimum_dwell_s(record),
                               places=12)
        self.assertEqual(dwell_findings(record), [])

    def test_a_sweep_faster_than_the_dwell_bound_is_reported(self):
        record = validate_frequency_domain_run(good_run(sweep_time_s=0.1))
        self.assertEqual(len(dwell_findings(record)), 1)

    def test_a_bin_step_exactly_at_the_bound_raises_no_finding(self):
        record = validate_frequency_domain_run(
            good_run(span_hz=1.0e6, points=201, resolution_bandwidth_hz=10.0e3)
        )
        self.assertAlmostEqual(bin_step_hz(record), maximum_bin_step_hz(record),
                               places=9)
        self.assertEqual(bin_step_findings(record), [])

    def test_a_coarse_bin_step_is_reported(self):
        record = validate_frequency_domain_run(
            good_run(span_hz=1.0e6, points=11, resolution_bandwidth_hz=1.0e3)
        )
        self.assertEqual(len(bin_step_findings(record)), 1)

    # --- run and campaign grading ----------------------------------------

    def test_a_sound_run_is_compliant(self):
        graded = grade_run(good_run(points=201, sweep_time_s=20.0))
        self.assertEqual(graded["category"], CATEGORY_COMPLIANT)
        self.assertEqual(graded["findings"], [])

    def test_a_run_without_a_declared_pulse_rate_is_marginal(self):
        graded = grade_run(
            good_run(points=201, sweep_time_s=20.0, pulse_repetition_rate_hz=None)
        )
        self.assertEqual(graded["category"], CATEGORY_MARGINAL)
        self.assertTrue(graded["limitations"])

    def test_an_averaging_detector_makes_the_run_noncompliant(self):
        graded = grade_run(
            good_run(points=201, sweep_time_s=20.0, detector=DETECTOR_AVERAGE)
        )
        self.assertEqual(graded["category"], CATEGORY_NONCOMPLIANT)

    def test_campaign_rejects_an_empty_run_list(self):
        with self.assertRaises(ValueError):
            assess_peak_detector_usage([])

    def test_campaign_verdict_is_sound_when_every_run_holds(self):
        report = assess_peak_detector_usage([good_run(points=201, sweep_time_s=20.0)])
        self.assertEqual(report["verdict"], "peak-detection-sound")

    def test_campaign_verdict_turns_unsound_on_one_fast_sweep(self):
        runs = [
            good_run(points=201, sweep_time_s=20.0),
            good_run(id="rs103-sweep-2", points=201, sweep_time_s=0.05),
        ]
        report = assess_peak_detector_usage(runs)
        self.assertEqual(report["verdict"], "peak-detection-unsound")
        self.assertEqual(report["governing_run"], "rs103-sweep-2")

    def test_campaign_groups_runs_by_category(self):
        report = assess_peak_detector_usage([good_run(points=201, sweep_time_s=20.0)])
        self.assertEqual(
            set(report["counts"]),
            {CATEGORY_COMPLIANT, CATEGORY_MARGINAL, CATEGORY_NONCOMPLIANT},
        )


if __name__ == "__main__":
    unittest.main()
