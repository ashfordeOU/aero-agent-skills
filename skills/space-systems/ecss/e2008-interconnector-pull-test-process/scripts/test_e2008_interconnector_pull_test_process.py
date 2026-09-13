"""Contract tests for the clause 6.4.3.10.2 interconnector pull-test process."""

import unittest

from e2008_interconnector_pull_test_process_logic import (
    MAX_PRELOAD_FRACTION,
    MIN_LOAD_CELL_UTILISATION,
    MIN_SAMPLES_TO_PEAK,
    RATE_TOLERANCE,
    SECONDS_PER_MINUTE,
    assess_pull_test_process,
    instrumentation_findings,
    load_cell_utilisation,
    ramp_rate_n_per_s,
    samples_to_peak,
    speed_findings,
    tab_reconciliation,
    time_to_peak_s,
    trace_findings,
    validate_speed_window,
)

RISING_TRACE = [
    (0.0, 0.0),
    (0.1, 1.0),
    (0.2, 2.0),
    (0.3, 3.0),
    (0.4, 4.0),
    (0.5, 0.2),
]
DIPPING_TRACE = [
    (0.0, 0.0),
    (0.1, 1.0),
    (0.2, 0.6),
    (0.3, 3.0),
    (0.4, 4.0),
    (0.5, 0.1),
]
PRELOADED_TRACE = [
    (0.0, 0.5),
    (0.1, 1.2),
    (0.2, 2.4),
    (0.3, 3.1),
    (0.4, 4.0),
    (0.5, 0.3),
]


def pull_record(tab, speed=30.0, peak=4.0, trace=None):
    return {
        "tab": tab,
        "speed_mm_per_min": speed,
        "peak_force_n": peak,
        "trace": list(RISING_TRACE if trace is None else trace),
    }


class SpeedWindowTests(unittest.TestCase):
    def test_window_is_returned_as_floats(self):
        self.assertEqual(validate_speed_window(20, 100), (20.0, 100.0))

    def test_equal_bounds_are_a_valid_single_speed(self):
        self.assertEqual(validate_speed_window(50.0, 50.0), (50.0, 50.0))

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_speed_window(100.0, 20.0)

    def test_zero_speed_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_speed_window(0.0, 100.0)

    def test_boolean_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_speed_window(True, 100.0)

    def test_speed_inside_the_window_gives_no_finding(self):
        self.assertEqual(
            speed_findings([pull_record("tab-1")], (20.0, 100.0)), []
        )

    def test_speed_exactly_on_the_floor_is_conformant(self):
        self.assertEqual(
            speed_findings([pull_record("tab-1", speed=20.0)], (20.0, 100.0)), []
        )

    def test_speed_exactly_on_the_ceiling_is_conformant(self):
        self.assertEqual(
            speed_findings([pull_record("tab-1", speed=100.0)], (20.0, 100.0)), []
        )

    def test_slow_pull_is_a_finding(self):
        findings = speed_findings(
            [pull_record("tab-7", speed=5.0)], (20.0, 100.0)
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("tab-7", findings[0])

    def test_fast_pull_is_a_finding(self):
        findings = speed_findings(
            [pull_record("tab-9", speed=250.0)], (20.0, 100.0)
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("ceiling", findings[0])

    def test_empty_record_list_rejected(self):
        with self.assertRaises(ValueError):
            speed_findings([], (20.0, 100.0))

    def test_record_without_speed_rejected(self):
        with self.assertRaises(ValueError):
            speed_findings([{"tab": "tab-1"}], (20.0, 100.0))


class RampTests(unittest.TestCase):
    def test_seconds_per_minute_constant(self):
        self.assertAlmostEqual(SECONDS_PER_MINUTE, 60.0, places=9)

    def test_ramp_rate_from_speed_and_stiffness(self):
        self.assertAlmostEqual(ramp_rate_n_per_s(30.0, 20.0), 10.0, places=9)

    def test_ramp_rate_scales_with_speed(self):
        slow = ramp_rate_n_per_s(30.0, 20.0)
        fast = ramp_rate_n_per_s(60.0, 20.0)
        self.assertAlmostEqual(fast, 2.0 * slow, places=9)

    def test_zero_stiffness_rejected(self):
        with self.assertRaises(ValueError):
            ramp_rate_n_per_s(30.0, 0.0)

    def test_time_to_peak_is_force_over_rate(self):
        self.assertAlmostEqual(time_to_peak_s(4.0, 10.0), 0.4, places=9)

    def test_negative_peak_force_rejected(self):
        with self.assertRaises(ValueError):
            time_to_peak_s(-4.0, 10.0)

    def test_sample_count_is_duration_times_rate(self):
        self.assertAlmostEqual(samples_to_peak(0.4, 100.0), 40.0, places=9)

    def test_zero_sample_rate_rejected(self):
        with self.assertRaises(ValueError):
            samples_to_peak(0.4, 0.0)


class InstrumentationTests(unittest.TestCase):
    def test_utilisation_is_peak_over_range(self):
        self.assertAlmostEqual(load_cell_utilisation(4.0, 20.0), 0.2, places=9)

    def test_adequate_instrumentation_gives_no_finding(self):
        self.assertEqual(
            instrumentation_findings(4.0, 10.0, 100.0, 20.0), []
        )

    def test_slow_recorder_is_a_finding(self):
        findings = instrumentation_findings(4.0, 10.0, 10.0, 20.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("samples", findings[0])

    def test_sample_count_exactly_on_the_minimum_is_adequate(self):
        self.assertEqual(instrumentation_findings(4.0, 10.0, 50.0, 20.0), [])

    def test_saturating_load_cell_is_a_finding(self):
        findings = instrumentation_findings(25.0, 10.0, 100.0, 20.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("saturates", findings[0])

    def test_oversized_load_cell_is_a_finding(self):
        findings = instrumentation_findings(4.0, 10.0, 100.0, 500.0)
        self.assertEqual(len(findings), 1)
        self.assertIn("load cell range", findings[0])

    def test_default_minimum_sample_count(self):
        self.assertEqual(MIN_SAMPLES_TO_PEAK, 20)

    def test_default_minimum_utilisation(self):
        self.assertAlmostEqual(MIN_LOAD_CELL_UTILISATION, 0.05, places=9)

    def test_min_samples_below_two_rejected(self):
        with self.assertRaises(ValueError):
            instrumentation_findings(4.0, 10.0, 100.0, 20.0, min_samples=1)

    def test_non_integer_min_samples_rejected(self):
        with self.assertRaises(ValueError):
            instrumentation_findings(4.0, 10.0, 100.0, 20.0, min_samples=20.0)

    def test_utilisation_floor_at_or_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            instrumentation_findings(
                4.0, 10.0, 100.0, 20.0, min_utilisation=1.0
            )

    def test_rate_tolerance_is_small(self):
        self.assertAlmostEqual(RATE_TOLERANCE, 1e-9, places=12)


class TraceTests(unittest.TestCase):
    def test_rising_trace_gives_no_finding(self):
        self.assertEqual(trace_findings(RISING_TRACE, "tab-1"), [])

    def test_dipping_trace_is_a_finding(self):
        findings = trace_findings(DIPPING_TRACE, "tab-4")
        self.assertEqual(len(findings), 1)
        self.assertIn("did not rise steadily", findings[0])

    def test_preloaded_trace_is_a_finding(self):
        findings = trace_findings(PRELOADED_TRACE, "tab-5")
        self.assertEqual(len(findings), 1)
        self.assertIn("pre-loaded", findings[0])

    def test_default_preload_fraction(self):
        self.assertAlmostEqual(MAX_PRELOAD_FRACTION, 0.02, places=9)

    def test_small_seating_force_within_the_fraction_is_accepted(self):
        trace = [(0.0, 0.05), (0.1, 1.0), (0.2, 2.5), (0.3, 4.0), (0.4, 0.1)]
        self.assertEqual(trace_findings(trace, "tab-6"), [])

    def test_drop_after_the_peak_is_not_a_finding(self):
        trace = [(0.0, 0.0), (0.1, 2.0), (0.2, 4.0), (0.3, 0.0), (0.4, 0.0)]
        self.assertEqual(trace_findings(trace, "tab-2"), [])

    def test_single_point_trace_rejected(self):
        with self.assertRaises(ValueError):
            trace_findings([(0.0, 4.0)], "tab-1")

    def test_non_increasing_times_rejected(self):
        trace = [(0.0, 0.0), (0.1, 1.0), (0.1, 2.0), (0.3, 4.0)]
        with self.assertRaises(ValueError):
            trace_findings(trace, "tab-1")

    def test_malformed_trace_point_rejected(self):
        with self.assertRaises(ValueError):
            trace_findings([(0.0, 0.0), (0.1,)], "tab-1")

    def test_all_zero_trace_rejected(self):
        with self.assertRaises(ValueError):
            trace_findings([(0.0, 0.0), (0.1, 0.0)], "tab-1")

    def test_negative_force_rejected(self):
        with self.assertRaises(ValueError):
            trace_findings([(0.0, 0.0), (0.1, -1.0), (0.2, 4.0)], "tab-1")


class ReconciliationTests(unittest.TestCase):
    def test_matching_run_is_clean(self):
        report = tab_reconciliation(["a", "b"], ["a", "b"])
        self.assertEqual(report["missing"], [])
        self.assertEqual(report["unplanned"], [])
        self.assertEqual(report["repeated"], [])

    def test_unpulled_tab_is_missing(self):
        report = tab_reconciliation(["a", "b", "c"], ["a", "c"])
        self.assertEqual(report["missing"], ["b"])

    def test_repeated_tab_is_reported(self):
        report = tab_reconciliation(["a", "b"], ["a", "b", "a"])
        self.assertEqual(report["repeated"], ["a"])

    def test_unplanned_tab_is_reported(self):
        report = tab_reconciliation(["a", "b"], ["a", "b", "z"])
        self.assertEqual(report["unplanned"], ["z"])

    def test_empty_plan_rejected(self):
        with self.assertRaises(ValueError):
            tab_reconciliation([], ["a"])

    def test_non_sequence_plan_rejected(self):
        with self.assertRaises(ValueError):
            tab_reconciliation("abc", ["a"])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "planned_tabs": ["tab-1", "tab-2", "tab-3"],
            "pull_records": [
                pull_record("tab-1"),
                pull_record("tab-2", speed=40.0),
                pull_record("tab-3", speed=25.0),
            ],
            "speed_window_mm_per_min": (20.0, 100.0),
            "stiffness_n_per_mm": 20.0,
            "sample_rate_hz": 100.0,
            "load_cell_range_n": 20.0,
        }
        spec.update(overrides)
        return spec

    def test_conformant_run_has_no_finding(self):
        result = assess_pull_test_process(self._spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["process_conformant"])

    def test_every_tab_is_reported(self):
        result = assess_pull_test_process(self._spec())
        self.assertEqual(len(result["tabs"]), 3)
        self.assertEqual(result["pulled_count"], 3)
        self.assertEqual(result["planned_count"], 3)

    def test_derived_rate_and_duration_are_reported(self):
        result = assess_pull_test_process(self._spec())
        first = result["tabs"][0]
        self.assertAlmostEqual(first["ramp_rate_n_per_s"], 10.0, places=9)
        self.assertAlmostEqual(first["duration_s"], 0.4, places=9)
        self.assertAlmostEqual(first["samples_to_peak"], 40.0, places=9)

    def test_unpulled_planned_tab_fails_the_run(self):
        spec = self._spec()
        spec["pull_records"] = spec["pull_records"][:2]
        result = assess_pull_test_process(spec)
        self.assertFalse(result["process_conformant"])
        self.assertTrue(
            any("never pulled" in item for item in result["findings"])
        )

    def test_out_of_window_speed_fails_the_run(self):
        spec = self._spec()
        spec["pull_records"][1]["speed_mm_per_min"] = 5.0
        result = assess_pull_test_process(spec)
        self.assertFalse(result["process_conformant"])

    def test_dipping_trace_fails_the_run(self):
        spec = self._spec()
        spec["pull_records"][2]["trace"] = list(DIPPING_TRACE)
        result = assess_pull_test_process(spec)
        self.assertFalse(result["process_conformant"])
        self.assertTrue(
            any("tab-3" in item for item in result["findings"])
        )

    def test_slow_recorder_fails_every_tab(self):
        result = assess_pull_test_process(self._spec(sample_rate_hz=5.0))
        self.assertEqual(len(result["findings"]), 3)

    def test_repeated_tab_fails_the_run(self):
        spec = self._spec()
        spec["pull_records"].append(pull_record("tab-1"))
        result = assess_pull_test_process(spec)
        self.assertTrue(
            any("ambiguous" in item for item in result["findings"])
        )

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["stiffness_n_per_mm"]
        with self.assertRaises(ValueError):
            assess_pull_test_process(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_pull_test_process(["planned_tabs"])

    def test_malformed_speed_window_rejected(self):
        with self.assertRaises(ValueError):
            assess_pull_test_process(self._spec(speed_window_mm_per_min=(20.0,)))

    def test_record_without_a_trace_rejected(self):
        spec = self._spec()
        del spec["pull_records"][0]["trace"]
        with self.assertRaises(ValueError):
            assess_pull_test_process(spec)


if __name__ == "__main__":
    unittest.main()
