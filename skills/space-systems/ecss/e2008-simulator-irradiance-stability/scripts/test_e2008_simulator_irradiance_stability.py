"""Contract tests for the clause 10.1.3 simulator irradiance stability check.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused policy, a run
with no declared acquisition window, a window the monitor barely watched,
a window with a long unsampled stretch, and a window that moved further
than the acquisition allows while its neighbours held.
"""

import unittest

from e2008_simulator_irradiance_stability_logic import (
    DEFAULT_STABILITY_POLICY,
    INSTABILITY_OUT_OF_LIMIT,
    INSTABILITY_WITHIN_LIMIT,
    INTERVALS_NOT_DECLARED,
    INTERVAL_SAMPLING_INSUFFICIENT,
    acquisition_intervals,
    assess_irradiance_stability,
    interval_assessment,
    interval_assessments,
    largest_unsampled_gap_s,
    mean_irradiance_w_m2,
    monitor_series,
    run_drift_percent,
    samples_in_interval,
    temporal_instability_percent,
    validate_acquisition_interval,
    validate_monitor_sample,
    validate_stability_policy,
    worst_interval,
)

BASE_W_M2 = 1367.0
RUN_END_S = 30


def _policy(**overrides):
    policy = dict(DEFAULT_STABILITY_POLICY)
    policy.update(overrides)
    return policy


def _reading(time_s):
    return BASE_W_M2 + float((time_s % 3) - 1)


def _samples(overrides=None, times=None):
    overrides = overrides or {}
    times = times if times is not None else range(RUN_END_S + 1)
    return [
        {
            "time_s": float(time_s),
            "irradiance_w_m2": float(overrides.get(time_s, _reading(time_s))),
        }
        for time_s in times
    ]


def _intervals():
    return [
        {"id": "acq-1", "start_s": 2.0, "end_s": 8.0},
        {"id": "acq-2", "start_s": 12.0, "end_s": 18.0},
        {"id": "acq-3", "start_s": 22.0, "end_s": 28.0},
    ]


def _case(**overrides):
    case = {"acquisition_intervals": _intervals(), "monitor_samples": _samples()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_stability_policy(DEFAULT_STABILITY_POLICY),
            DEFAULT_STABILITY_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_stability_policy("max_instability_percent")

    def test_a_hundred_per_cent_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_stability_policy(_policy(max_instability_percent=110.0))

    def test_a_single_sample_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_stability_policy(_policy(min_samples_per_interval=1))

    def test_a_boolean_sample_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_stability_policy(_policy(min_samples_per_interval=True))

    def test_a_gap_allowance_above_the_whole_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_stability_policy(_policy(max_gap_fraction=1.5))

    def test_a_negative_drift_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_stability_policy(_policy(max_run_drift_percent=-1.0))


class MonitorSampleTests(unittest.TestCase):
    def test_a_reading_is_read_back(self):
        checked = validate_monitor_sample({"time_s": 4.0, "irradiance_w_m2": 1368.0})
        self.assertAlmostEqual(checked["time_s"], 4.0, places=9)
        self.assertAlmostEqual(checked["irradiance_w_m2"], 1368.0, places=9)

    def test_a_negative_timestamp_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitor_sample({"time_s": -1.0, "irradiance_w_m2": 1367.0})

    def test_a_zero_reading_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitor_sample({"time_s": 4.0, "irradiance_w_m2": 0.0})

    def test_a_boolean_reading_rejected(self):
        with self.assertRaises(ValueError):
            validate_monitor_sample({"time_s": 4.0, "irradiance_w_m2": True})

    def test_an_empty_trace_rejected(self):
        with self.assertRaises(ValueError):
            monitor_series([])

    def test_two_readings_at_one_timestamp_rejected(self):
        samples = _samples()
        samples.append({"time_s": 4.0, "irradiance_w_m2": 1370.0})
        with self.assertRaises(ValueError):
            monitor_series(samples)

    def test_the_trace_comes_back_in_time_order(self):
        series = monitor_series(list(reversed(_samples())))
        times = [sample["time_s"] for sample in series]
        self.assertEqual(times, sorted(times))


class IntervalTests(unittest.TestCase):
    def test_a_window_is_read_back(self):
        checked = validate_acquisition_interval(_intervals()[0])
        self.assertEqual(checked["id"], "acq-1")
        self.assertAlmostEqual(checked["end_s"], 8.0, places=9)

    def test_a_blank_window_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_acquisition_interval(
                {"id": "  ", "start_s": 2.0, "end_s": 8.0}
            )

    def test_a_window_with_no_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_acquisition_interval(
                {"id": "acq-0", "start_s": 8.0, "end_s": 8.0}
            )

    def test_a_backwards_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_acquisition_interval(
                {"id": "acq-0", "start_s": 9.0, "end_s": 8.0}
            )

    def test_a_duplicate_window_id_rejected(self):
        intervals = _intervals()
        intervals[2]["id"] = "acq-1"
        with self.assertRaises(ValueError):
            acquisition_intervals(intervals)

    def test_an_empty_window_set_rejected(self):
        with self.assertRaises(ValueError):
            acquisition_intervals([])

    def test_the_window_endpoints_are_included_in_its_samples(self):
        series = monitor_series(_samples())
        inside = samples_in_interval(series, _intervals()[0])
        self.assertEqual(len(inside), 7)
        self.assertAlmostEqual(inside[0]["time_s"], 2.0, places=9)
        self.assertAlmostEqual(inside[-1]["time_s"], 8.0, places=9)


class FigureTests(unittest.TestCase):
    def test_the_instability_is_taken_extreme_to_extreme(self):
        samples = [
            {"time_s": 0.0, "irradiance_w_m2": 990.0},
            {"time_s": 1.0, "irradiance_w_m2": 1000.0},
            {"time_s": 2.0, "irradiance_w_m2": 1010.0},
        ]
        self.assertAlmostEqual(
            temporal_instability_percent(samples), 1.0, places=9
        )

    def test_a_perfectly_steady_window_moves_nothing(self):
        samples = [
            {"time_s": float(index), "irradiance_w_m2": 1367.0}
            for index in range(5)
        ]
        self.assertAlmostEqual(
            temporal_instability_percent(samples), 0.0, places=12
        )

    def test_one_bad_sample_sets_the_whole_window_figure(self):
        samples = [
            {"time_s": float(index), "irradiance_w_m2": 1367.0}
            for index in range(9)
        ]
        samples[4]["irradiance_w_m2"] = 1200.0
        self.assertGreater(temporal_instability_percent(samples), 6.0)

    def test_the_window_mean_is_reported(self):
        samples = [
            {"time_s": 0.0, "irradiance_w_m2": 990.0},
            {"time_s": 1.0, "irradiance_w_m2": 1010.0},
        ]
        self.assertAlmostEqual(mean_irradiance_w_m2(samples), 1000.0, places=9)

    def test_an_empty_window_has_no_figure_to_take(self):
        with self.assertRaises(ValueError):
            temporal_instability_percent([])

    def test_a_regular_cadence_leaves_a_one_second_gap(self):
        series = monitor_series(_samples())
        inside = samples_in_interval(series, _intervals()[0])
        self.assertAlmostEqual(
            largest_unsampled_gap_s(inside, _intervals()[0]), 1.0, places=9
        )

    def test_a_monitor_that_woke_late_leaves_a_leading_gap(self):
        series = monitor_series(_samples(times=[5, 6, 7, 8]))
        self.assertAlmostEqual(
            largest_unsampled_gap_s(
                samples_in_interval(series, _intervals()[0]), _intervals()[0]
            ),
            3.0,
            places=9,
        )

    def test_an_unwatched_window_reports_its_whole_duration(self):
        self.assertAlmostEqual(
            largest_unsampled_gap_s([], _intervals()[0]), 6.0, places=9
        )


class IntervalAssessmentTests(unittest.TestCase):
    def test_a_well_watched_window_is_adequate_and_within_limit(self):
        series = monitor_series(_samples())
        assessment = interval_assessment(_intervals()[0], series)
        self.assertTrue(assessment["sampling_adequate"])
        self.assertTrue(assessment["within_limit"])
        self.assertEqual(assessment["sample_count"], 7)

    def test_a_thinly_watched_window_names_the_sample_count(self):
        series = monitor_series(_samples(times=[2, 4, 8]))
        assessment = interval_assessment(_intervals()[0], series)
        self.assertIn("sample-count", assessment["sampling_shortfalls"])

    def test_a_stalled_monitor_names_the_unsampled_gap(self):
        series = monitor_series(_samples(times=[2, 3, 7, 8]))
        assessment = interval_assessment(
            _intervals()[0], series, _policy(min_samples_per_interval=4)
        )
        self.assertIn("unsampled-gap", assessment["sampling_shortfalls"])

    def test_a_window_exactly_on_the_gap_allowance_is_adequate(self):
        interval = {"id": "acq-g", "start_s": 0.0, "end_s": 4.0}
        series = monitor_series(_samples(times=[0, 1, 2, 3, 4]))
        assessment = interval_assessment(interval, series)
        self.assertAlmostEqual(assessment["gap_fraction"], 0.25, places=9)
        self.assertTrue(assessment["sampling_adequate"])

    def test_an_unwatched_window_carries_no_instability_figure(self):
        series = monitor_series(_samples(times=[12, 13, 14]))
        assessment = interval_assessment(_intervals()[0], series)
        self.assertEqual(assessment["sample_count"], 0)
        self.assertIsNone(assessment["instability_percent"])

    def test_a_window_exactly_on_the_instability_limit_is_within_limit(self):
        interval = {"id": "acq-t", "start_s": 0.0, "end_s": 4.0}
        series = monitor_series(
            [
                {"time_s": 0.0, "irradiance_w_m2": 990.0},
                {"time_s": 1.0, "irradiance_w_m2": 1000.0},
                {"time_s": 2.0, "irradiance_w_m2": 1000.0},
                {"time_s": 3.0, "irradiance_w_m2": 1000.0},
                {"time_s": 4.0, "irradiance_w_m2": 1010.0},
            ]
        )
        assessment = interval_assessment(interval, series)
        self.assertAlmostEqual(
            assessment["instability_percent"], 1.0, places=9
        )
        self.assertTrue(assessment["within_limit"])

    def test_every_declared_window_is_judged_separately(self):
        series = monitor_series(_samples())
        assessments = interval_assessments(_intervals(), series)
        self.assertEqual(len(assessments), 3)
        self.assertEqual(
            [entry["id"] for entry in assessments], ["acq-1", "acq-2", "acq-3"]
        )


class RunTests(unittest.TestCase):
    def test_the_worst_window_is_the_one_that_moved_most(self):
        series = monitor_series(_samples(overrides={14: 1300.0}))
        assessments = interval_assessments(_intervals(), series)
        self.assertEqual(worst_interval(assessments)["id"], "acq-2")

    def test_a_run_with_no_measured_window_has_no_worst_window(self):
        series = monitor_series(_samples(times=[0, 1]))
        assessments = interval_assessments(_intervals(), series)
        with self.assertRaises(ValueError):
            worst_interval(assessments)

    def test_run_drift_is_taken_between_the_window_means(self):
        series = monitor_series(_samples())
        assessments = interval_assessments(_intervals(), series)
        self.assertLess(run_drift_percent(assessments), 0.1)

    def test_a_fading_lamp_drifts_the_run_while_each_window_holds(self):
        overrides = {}
        for time_s in range(RUN_END_S + 1):
            overrides[time_s] = 1450.0 - 3.5 * time_s
        series = monitor_series(_samples(overrides=overrides))
        assessments = interval_assessments(_intervals(), series)
        for assessment in assessments:
            self.assertTrue(assessment["within_limit"])
        self.assertGreater(run_drift_percent(assessments), 2.0)

    def test_an_empty_assessment_set_rejected(self):
        with self.assertRaises(ValueError):
            run_drift_percent([])


class AssessmentTests(unittest.TestCase):
    def test_a_steady_run_is_within_limit(self):
        result = assess_irradiance_stability(_case())
        self.assertEqual(result["verdict"], INSTABILITY_WITHIN_LIMIT)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["interval_count"], 3)

    def test_an_undeclared_window_set_closes_the_assessment(self):
        case = _case()
        del case["acquisition_intervals"]
        result = assess_irradiance_stability(case)
        self.assertEqual(result["verdict"], INTERVALS_NOT_DECLARED)
        self.assertTrue(result["findings"])

    def test_an_empty_window_set_closes_the_assessment(self):
        result = assess_irradiance_stability(_case(acquisition_intervals=[]))
        self.assertEqual(result["verdict"], INTERVALS_NOT_DECLARED)

    def test_a_barely_watched_run_stops_before_a_figure_is_quoted(self):
        result = assess_irradiance_stability(
            _case(monitor_samples=_samples(times=[2, 5, 8, 12, 15, 18, 22, 25, 28]))
        )
        self.assertEqual(result["verdict"], INTERVAL_SAMPLING_INSUFFICIENT)
        self.assertIsNone(result["worst_instability_percent"])

    def test_every_unwatched_window_is_named_not_only_the_first(self):
        result = assess_irradiance_stability(
            _case(monitor_samples=_samples(times=[2, 3, 4, 5, 6, 7, 8]))
        )
        self.assertEqual(result["verdict"], INTERVAL_SAMPLING_INSUFFICIENT)
        self.assertEqual(len(result["findings"]), 2)

    def test_one_bad_window_fails_the_run_though_the_others_hold(self):
        result = assess_irradiance_stability(
            _case(monitor_samples=_samples(overrides={14: 1300.0}))
        )
        self.assertEqual(result["verdict"], INSTABILITY_OUT_OF_LIMIT)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("acq-2", result["findings"][0])

    def test_the_worst_window_travels_with_the_verdict(self):
        result = assess_irradiance_stability(_case())
        self.assertEqual(result["worst_interval_id"], "acq-1")
        self.assertGreater(result["worst_instability_percent"], 0.0)

    def test_a_fading_lamp_passes_every_window_and_raises_a_drift_advisory(self):
        overrides = {}
        for time_s in range(RUN_END_S + 1):
            overrides[time_s] = 1450.0 - 3.5 * time_s
        result = assess_irradiance_stability(_case(monitor_samples=_samples(overrides=overrides)))
        self.assertEqual(result["verdict"], INSTABILITY_WITHIN_LIMIT)
        self.assertTrue(
            any("drift allowance" in advisory for advisory in result["advisories"])
        )

    def test_a_window_grazing_the_limit_raises_a_marginal_advisory(self):
        overrides = {13: 1380.0, 16: 1354.0}
        result = assess_irradiance_stability(
            _case(monitor_samples=_samples(overrides=overrides))
        )
        self.assertEqual(result["verdict"], INSTABILITY_WITHIN_LIMIT)
        self.assertTrue(
            any("almost nothing left" in advisory for advisory in result["advisories"])
        )

    def test_a_comfortable_run_raises_no_advisory(self):
        result = assess_irradiance_stability(_case())
        self.assertEqual(result["advisories"], [])

    def test_the_run_drift_is_reported_beside_the_verdict(self):
        result = assess_irradiance_stability(_case())
        self.assertIsNotNone(result["run_drift_percent"])

    def test_a_missing_monitor_trace_rejected(self):
        case = _case()
        del case["monitor_samples"]
        with self.assertRaises(ValueError):
            assess_irradiance_stability(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_irradiance_stability(["acquisition_intervals"])


if __name__ == "__main__":
    unittest.main()
