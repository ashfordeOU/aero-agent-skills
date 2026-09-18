#!/usr/bin/env python3
"""Gate 3 contract test for e2007-susceptibility-monitoring-provisions.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_susceptibility_monitoring_provisions.py
"""

import unittest

from e2007_susceptibility_monitoring_provisions_logic import (
    CATEGORY_ADEQUATE,
    CATEGORY_INADEQUATE,
    CATEGORY_MARGINAL,
    DEFAULT_RESOLUTION_STEPS,
    DEFAULT_SAMPLES_PER_EVENT,
    TOL,
    acceptance_band,
    assess_susceptibility_monitoring,
    at_least,
    at_most,
    coverage_gaps,
    grade_parameter,
    grade_run,
    merge_windows,
    resolution_adequate,
    resolution_steps,
    sampling_adequate,
    uncovered_duration_s,
    validate_exposure,
    validate_monitored_parameter,
)

SHORTEST_EVENT_S = 0.020


def good_parameter(**over):
    record = {
        "name": "bus-current",
        "lower_limit": 2.7,
        "upper_limit": 3.3,
        "resolution": 0.01,
        "sample_interval_s": 0.005,
        "continuously_observable": True,
    }
    record.update(over)
    return record


def second_parameter(**over):
    record = {
        "name": "output-voltage",
        "lower_limit": 4.75,
        "upper_limit": 5.25,
        "resolution": 0.005,
        "sample_interval_s": 0.002,
        "continuously_observable": True,
    }
    record.update(over)
    return record


def good_run(**over):
    record = {
        "id": "cs101-run-1",
        "exposure": {"start_s": 0.0, "end_s": 60.0},
        "monitoring_windows": [{"start_s": 0.0, "end_s": 60.0}],
        "parameters": [good_parameter(), second_parameter()],
    }
    record.update(over)
    return record


class SusceptibilityMonitoringProvisionsTest(unittest.TestCase):
    # --- parameter declaration ----------------------------------------

    def test_parameter_requires_a_name(self):
        with self.assertRaises(ValueError):
            validate_monitored_parameter(good_parameter(name="  "))

    def test_parameter_rejects_inverted_acceptance_limits(self):
        with self.assertRaises(ValueError):
            validate_monitored_parameter(
                good_parameter(lower_limit=3.3, upper_limit=2.7)
            )

    def test_parameter_rejects_a_non_positive_resolution(self):
        with self.assertRaises(ValueError):
            validate_monitored_parameter(good_parameter(resolution=0.0))

    def test_parameter_rejects_a_non_positive_sample_interval(self):
        with self.assertRaises(ValueError):
            validate_monitored_parameter(good_parameter(sample_interval_s=-0.001))

    def test_parameter_rejects_a_non_boolean_observability_flag(self):
        with self.assertRaises(ValueError):
            validate_monitored_parameter(good_parameter(continuously_observable="yes"))

    def test_parameter_rejects_a_non_mapping_record(self):
        with self.assertRaises(ValueError):
            validate_monitored_parameter(["bus-current"])

    def test_acceptance_band_is_the_limit_separation(self):
        record = validate_monitored_parameter(good_parameter())
        self.assertAlmostEqual(acceptance_band(record), 0.6, places=9)

    # --- resolution and sampling adequacy ------------------------------

    def test_resolution_steps_counts_monitor_steps_across_the_band(self):
        record = validate_monitored_parameter(good_parameter())
        self.assertAlmostEqual(resolution_steps(record), 60.0, places=9)

    def test_resolution_exactly_meeting_the_requirement_is_adequate(self):
        record = validate_monitored_parameter(good_parameter(resolution=0.06))
        self.assertAlmostEqual(resolution_steps(record), DEFAULT_RESOLUTION_STEPS,
                               places=9)
        self.assertTrue(resolution_adequate(record))

    def test_coarse_resolution_hides_a_drift_to_the_band_edge(self):
        record = validate_monitored_parameter(good_parameter(resolution=0.3))
        self.assertFalse(resolution_adequate(record))

    def test_sampling_exactly_at_the_nyquist_style_bound_is_adequate(self):
        interval = SHORTEST_EVENT_S / DEFAULT_SAMPLES_PER_EVENT
        record = validate_monitored_parameter(
            good_parameter(sample_interval_s=interval)
        )
        self.assertTrue(sampling_adequate(record, SHORTEST_EVENT_S))

    def test_slow_sampling_can_step_over_the_shortest_upset(self):
        record = validate_monitored_parameter(good_parameter(sample_interval_s=0.05))
        self.assertFalse(sampling_adequate(record, SHORTEST_EVENT_S))

    def test_sampling_rejects_a_non_positive_event_duration(self):
        record = validate_monitored_parameter(good_parameter())
        with self.assertRaises(ValueError):
            sampling_adequate(record, 0.0)

    def test_tolerance_helpers_absorb_representation_error_only(self):
        self.assertTrue(at_most(1.0 + TOL / 2.0, 1.0))
        self.assertFalse(at_most(1.5, 1.0))
        self.assertTrue(at_least(1.0 - TOL / 2.0, 1.0))

    def test_graded_parameter_flags_a_between_runs_only_monitor(self):
        graded = grade_parameter(
            good_parameter(continuously_observable=False), SHORTEST_EVENT_S
        )
        self.assertEqual(graded["category"], CATEGORY_INADEQUATE)
        self.assertTrue(any("observable" in f for f in graded["findings"]))

    def test_graded_parameter_is_adequate_when_it_resolves_and_keeps_up(self):
        graded = grade_parameter(good_parameter(), SHORTEST_EVENT_S)
        self.assertEqual(graded["category"], CATEGORY_ADEQUATE)
        self.assertEqual(graded["findings"], [])

    # --- exposure and window coverage ----------------------------------

    def test_exposure_rejects_a_zero_length_span(self):
        with self.assertRaises(ValueError):
            validate_exposure({"start_s": 5.0, "end_s": 5.0})

    def test_exposure_rejects_a_negative_start(self):
        with self.assertRaises(ValueError):
            validate_exposure({"start_s": -1.0, "end_s": 5.0})

    def test_merge_windows_rejects_an_empty_provision(self):
        with self.assertRaises(ValueError):
            merge_windows([])

    def test_merge_windows_rejects_an_inverted_window(self):
        with self.assertRaises(ValueError):
            merge_windows([{"start_s": 10.0, "end_s": 2.0}])

    def test_merge_windows_joins_overlapping_spans(self):
        merged = merge_windows(
            [{"start_s": 0.0, "end_s": 30.0}, {"start_s": 20.0, "end_s": 60.0}]
        )
        self.assertEqual(len(merged), 1)
        self.assertAlmostEqual(merged[0][1], 60.0, places=9)

    def test_merge_windows_keeps_disjoint_spans_apart(self):
        merged = merge_windows(
            [{"start_s": 0.0, "end_s": 20.0}, {"start_s": 40.0, "end_s": 60.0}]
        )
        self.assertEqual(len(merged), 2)

    def test_abutting_windows_leave_no_gap(self):
        gaps = coverage_gaps(
            [{"start_s": 0.0, "end_s": 30.0}, {"start_s": 30.0, "end_s": 60.0}],
            {"start_s": 0.0, "end_s": 60.0},
        )
        self.assertEqual(gaps, ())

    def test_a_late_start_is_reported_as_a_leading_gap(self):
        gaps = coverage_gaps(
            [{"start_s": 5.0, "end_s": 60.0}], {"start_s": 0.0, "end_s": 60.0}
        )
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][1] - gaps[0][0], 5.0, places=9)

    def test_an_early_stop_is_reported_as_a_trailing_gap(self):
        gaps = coverage_gaps(
            [{"start_s": 0.0, "end_s": 50.0}], {"start_s": 0.0, "end_s": 60.0}
        )
        self.assertAlmostEqual(uncovered_duration_s(gaps), 10.0, places=9)

    def test_a_mid_exposure_interruption_is_reported(self):
        gaps = coverage_gaps(
            [{"start_s": 0.0, "end_s": 20.0}, {"start_s": 25.0, "end_s": 60.0}],
            {"start_s": 0.0, "end_s": 60.0},
        )
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0][0], 20.0, places=9)

    def test_windows_wider_than_the_exposure_leave_no_gap(self):
        gaps = coverage_gaps(
            [{"start_s": -5.0, "end_s": 70.0}], {"start_s": 0.0, "end_s": 60.0}
        )
        self.assertEqual(gaps, ())

    # --- run and campaign grading --------------------------------------

    def test_fully_watched_run_with_good_monitors_is_adequate(self):
        graded = grade_run(good_run(), SHORTEST_EVENT_S)
        self.assertEqual(graded["category"], CATEGORY_ADEQUATE)
        self.assertAlmostEqual(graded["uncovered_duration_s"], 0.0, places=9)

    def test_run_with_a_coverage_gap_is_inadequate(self):
        graded = grade_run(
            good_run(monitoring_windows=[{"start_s": 0.0, "end_s": 40.0}]),
            SHORTEST_EVENT_S,
        )
        self.assertEqual(graded["category"], CATEGORY_INADEQUATE)
        self.assertTrue(graded["findings"])

    def test_run_requires_at_least_one_monitored_parameter(self):
        with self.assertRaises(ValueError):
            grade_run(good_run(parameters=[]), SHORTEST_EVENT_S)

    def test_run_requires_an_identifier(self):
        with self.assertRaises(ValueError):
            grade_run(good_run(id=""), SHORTEST_EVENT_S)

    def test_campaign_rejects_an_empty_run_list(self):
        with self.assertRaises(ValueError):
            assess_susceptibility_monitoring([], SHORTEST_EVENT_S)

    def test_campaign_verdict_is_adequate_when_every_run_is_watched(self):
        report = assess_susceptibility_monitoring([good_run()], SHORTEST_EVENT_S)
        self.assertEqual(report["verdict"], "monitoring-adequate")
        self.assertEqual(report["counts"][CATEGORY_ADEQUATE], 1)

    def test_campaign_verdict_turns_deficient_on_one_bad_run(self):
        runs = [
            good_run(),
            good_run(
                id="rs103-run-2",
                monitoring_windows=[{"start_s": 10.0, "end_s": 60.0}],
            ),
        ]
        report = assess_susceptibility_monitoring(runs, SHORTEST_EVENT_S)
        self.assertEqual(report["verdict"], "monitoring-deficient")
        self.assertEqual(report["worst_covered_run"], "rs103-run-2")
        self.assertAlmostEqual(report["total_uncovered_s"], 10.0, places=9)

    def test_campaign_groups_runs_by_category(self):
        report = assess_susceptibility_monitoring([good_run()], SHORTEST_EVENT_S)
        self.assertEqual(
            set(report["counts"]),
            {CATEGORY_ADEQUATE, CATEGORY_MARGINAL, CATEGORY_INADEQUATE},
        )


if __name__ == "__main__":
    unittest.main()
