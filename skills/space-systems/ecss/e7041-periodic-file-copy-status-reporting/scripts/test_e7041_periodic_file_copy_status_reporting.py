"""Contract tests for the clause 6.23.5.5 periodic copy status reporting logic."""

import unittest

from e7041_periodic_file_copy_status_reporting_logic import (
    MIN_INTERVAL,
    assess_reporting_window,
    build_status_report,
    disable_periodic_reporting,
    enable_periodic_reporting,
    new_reporting_state,
    operation_row,
    report_ticks,
    reports_over_window,
    validate_interval,
)


def an_operation(**overrides):
    entry = {
        "source": "mass-memory/housekeeping.dat",
        "target": "downlink-buffer/housekeeping.dat",
        "octets_total": 1000,
        "octets_copied": 400,
        "state": "running",
    }
    entry.update(overrides)
    return entry


def an_enabled_state(interval=10, at_tick=100):
    state = new_reporting_state()
    enable_periodic_reporting(state, interval, at_tick)
    return state


class IntervalTests(unittest.TestCase):
    def test_minimum_interval_is_one_time_unit(self):
        self.assertEqual(MIN_INTERVAL, 1)
        self.assertEqual(validate_interval(1), 1)

    def test_zero_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_interval(0)

    def test_negative_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_interval(-5)

    def test_fractional_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_interval(2.5)

    def test_boolean_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_interval(True)


class EnableDisableTests(unittest.TestCase):
    def test_power_on_state_is_disabled(self):
        state = new_reporting_state()
        self.assertFalse(state["enabled"])
        self.assertIsNone(state["interval"])

    def test_enable_records_the_interval_and_the_tick(self):
        state = new_reporting_state()
        outcome = enable_periodic_reporting(state, 10, 100)
        self.assertEqual(outcome["outcome"], "enabled")
        self.assertEqual(state["interval"], 10)
        self.assertEqual(state["enabled_at"], 100)

    def test_enable_at_the_same_interval_restarts_the_schedule(self):
        state = an_enabled_state(10, 100)
        outcome = enable_periodic_reporting(state, 10, 135)
        self.assertEqual(outcome["outcome"], "restarted")
        self.assertEqual(state["enabled_at"], 135)

    def test_enable_at_a_new_interval_is_reported_as_a_change(self):
        state = an_enabled_state(10, 100)
        outcome = enable_periodic_reporting(state, 25, 135)
        self.assertEqual(outcome["outcome"], "re-intervalled")
        self.assertIn("10 to 25", outcome["reason"])

    def test_disable_clears_the_interval(self):
        state = an_enabled_state()
        outcome = disable_periodic_reporting(state)
        self.assertEqual(outcome["outcome"], "disabled")
        self.assertFalse(state["enabled"])
        self.assertIsNone(state["interval"])

    def test_disable_twice_is_redundant_not_an_error(self):
        state = an_enabled_state()
        disable_periodic_reporting(state)
        self.assertEqual(disable_periodic_reporting(state)["outcome"], "redundant")

    def test_enable_with_a_bad_interval_rejected(self):
        with self.assertRaises(ValueError):
            enable_periodic_reporting(new_reporting_state(), 0, 100)

    def test_enable_at_a_negative_tick_rejected(self):
        with self.assertRaises(ValueError):
            enable_periodic_reporting(new_reporting_state(), 10, -1)

    def test_malformed_state_rejected(self):
        with self.assertRaises(ValueError):
            disable_periodic_reporting({"enabled": True})


class TickScheduleTests(unittest.TestCase):
    def test_first_report_is_one_interval_after_the_enable(self):
        self.assertEqual(report_ticks(100, 10, 135)[0], 110)

    def test_enable_tick_itself_is_not_a_report_tick(self):
        self.assertNotIn(100, report_ticks(100, 10, 135))

    def test_ticks_are_evenly_spaced(self):
        self.assertEqual(report_ticks(100, 10, 135), [110, 120, 130])

    def test_a_tick_landing_on_the_window_end_is_included(self):
        self.assertEqual(report_ticks(100, 10, 130), [110, 120, 130])

    def test_interval_longer_than_the_window_gives_no_tick(self):
        self.assertEqual(report_ticks(100, 50, 135), [])

    def test_window_ending_before_the_enable_rejected(self):
        with self.assertRaises(ValueError):
            report_ticks(100, 10, 90)

    def test_schedule_is_whole_number_arithmetic(self):
        ticks = report_ticks(0, 3, 10)
        self.assertEqual(ticks, [3, 6, 9])
        self.assertTrue(all(isinstance(t, int) for t in ticks))


class ReportContentTests(unittest.TestCase):
    def test_row_carries_the_octets_remaining(self):
        row = operation_row(an_operation())
        self.assertEqual(row["octets_remaining"], 600)

    def test_row_carries_the_state(self):
        self.assertEqual(operation_row(an_operation(state="suspended"))["state"], "suspended")

    def test_row_rejects_an_unknown_state(self):
        with self.assertRaises(ValueError):
            operation_row(an_operation(state="aborted"))

    def test_row_rejects_copied_beyond_total(self):
        with self.assertRaises(ValueError):
            operation_row(an_operation(octets_copied=2000))

    def test_row_rejects_a_zero_total(self):
        with self.assertRaises(ValueError):
            operation_row(an_operation(octets_total=0))

    def test_row_rejects_a_missing_field(self):
        entry = an_operation()
        del entry["target"]
        with self.assertRaises(ValueError):
            operation_row(entry)

    def test_report_sums_the_outstanding_octets(self):
        report = build_status_report(110, [an_operation(), an_operation(octets_copied=900)])
        self.assertEqual(report["octets_remaining"], 600 + 100)

    def test_empty_list_still_produces_a_report(self):
        report = build_status_report(110, [])
        self.assertEqual(report["entry_count"], 0)
        self.assertEqual(report["operations"], [])

    def test_report_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            build_status_report(110, an_operation())


class WindowTests(unittest.TestCase):
    def test_disabled_function_generates_nothing(self):
        state = new_reporting_state()
        self.assertEqual(reports_over_window(state, lambda t: [], 200), [])

    def test_enabled_function_generates_one_report_per_tick(self):
        state = an_enabled_state(10, 100)
        reports = reports_over_window(state, lambda t: [an_operation()], 135)
        self.assertEqual([r["tick"] for r in reports], [110, 120, 130])

    def test_report_content_follows_the_tick(self):
        state = an_enabled_state(10, 100)
        content = {110: [an_operation(octets_copied=100)], 120: [], 130: []}
        reports = reports_over_window(state, lambda t: content.get(t, []), 135)
        self.assertEqual(reports[0]["entry_count"], 1)
        self.assertEqual(reports[1]["entry_count"], 0)

    def test_non_callable_source_rejected(self):
        with self.assertRaises(ValueError):
            reports_over_window(an_enabled_state(), [an_operation()], 200)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "interval": 10,
            "enabled_at": 100,
            "window_end": 135,
            "operations": [an_operation()],
        }
        spec.update(overrides)
        return spec

    def test_assessment_counts_the_reports(self):
        result = assess_reporting_window(self._spec())
        self.assertEqual(result["report_count"], 3)
        self.assertEqual(result["ticks"], [110, 120, 130])

    def test_outstanding_octets_at_the_last_report_are_flagged(self):
        result = assess_reporting_window(self._spec())
        self.assertTrue(any("still outstanding" in f for f in result["findings"]))

    def test_disabled_function_is_flagged(self):
        result = assess_reporting_window(self._spec(enabled=False))
        self.assertEqual(result["report_count"], 0)
        self.assertTrue(any("disabled" in f for f in result["findings"]))

    def test_interval_longer_than_the_window_is_flagged(self):
        result = assess_reporting_window(self._spec(interval=100))
        self.assertTrue(any("exceeds the" in f for f in result["findings"]))

    def test_all_empty_reports_are_flagged(self):
        result = assess_reporting_window(self._spec(operations=[]))
        self.assertTrue(any("reports emptiness" in f for f in result["findings"]))

    def test_per_tick_operations_mapping_is_accepted(self):
        result = assess_reporting_window(
            self._spec(operations={110: [an_operation()], 120: [], 130: []})
        )
        self.assertEqual(result["reports"][0]["entry_count"], 1)
        self.assertEqual(result["reports"][2]["entry_count"], 0)

    def test_completed_window_raises_no_outstanding_finding(self):
        result = assess_reporting_window(
            self._spec(operations={110: [an_operation()], 120: [], 130: []})
        )
        self.assertFalse(any("still outstanding" in f for f in result["findings"]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["window_end"]
        with self.assertRaises(ValueError):
            assess_reporting_window(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_reporting_window(["interval"])

    def test_bad_operations_type_rejected(self):
        with self.assertRaises(ValueError):
            assess_reporting_window(self._spec(operations="none"))


if __name__ == "__main__":
    unittest.main()
