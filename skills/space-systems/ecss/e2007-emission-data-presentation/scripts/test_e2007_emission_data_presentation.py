#!/usr/bin/env python3
"""Gate 3 contract test for e2007-emission-data-presentation.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_emission_data_presentation.py
"""

import unittest

from e2007_emission_data_presentation_logic import (
    DEFAULT_MIN_UPDATES_PER_SWEEP,
    MODE_DEFERRED,
    MODE_LIVE,
    MODE_OPERATOR,
    assess_emission_data_presentation,
    axis_findings,
    axis_span_shortfalls,
    latency_is_current,
    max_refresh_interval_s,
    refresh_is_live,
    resolve_display_mode,
    updates_per_sweep,
    validate_presentation,
)

BAND_START = 30.0e6
BAND_STOP = 1000.0e6
SWEEP_TIME_S = 2.0


def good_presentation(**over):
    record = {
        "automatic_generation": True,
        "displayed_during_run": True,
        "limit_line_shown": True,
        "x_quantity": "frequency",
        "y_quantity": "amplitude",
        "x_unit": "mhz",
        "y_unit": "dbuv_m",
        "refresh_interval_s": 0.25,
        "display_latency_s": 0.125,
        "plot_start_hz": BAND_START,
        "plot_stop_hz": BAND_STOP,
    }
    record.update(over)
    return record


class TestPresentationValidation(unittest.TestCase):
    def test_good_presentation_normalizes(self):
        config = validate_presentation(good_presentation())
        self.assertEqual(config["x_quantity"], "frequency")
        self.assertAlmostEqual(config["refresh_interval_s"], 0.25, places=9)

    def test_unit_token_is_case_normalized(self):
        config = validate_presentation(good_presentation(y_unit="dBuV_m"))
        self.assertEqual(config["y_unit"], "dbuv_m")

    def test_unrecognized_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_presentation(good_presentation(y_quantity="loudness"))

    def test_unrecognized_unit_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_presentation(good_presentation(x_unit="furlongs"))

    def test_non_boolean_generation_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_presentation(good_presentation(automatic_generation="yes"))

    def test_zero_refresh_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_presentation(good_presentation(refresh_interval_s=0.0))

    def test_negative_latency_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_presentation(good_presentation(display_latency_s=-0.5))

    def test_inverted_plot_axis_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_presentation(
                good_presentation(plot_start_hz=BAND_STOP, plot_stop_hz=BAND_START)
            )

    def test_missing_field_is_rejected(self):
        record = good_presentation()
        del record["limit_line_shown"]
        with self.assertRaises(ValueError):
            validate_presentation(record)


class TestDisplayMode(unittest.TestCase):
    def test_automatic_and_during_run_is_live(self):
        self.assertEqual(resolve_display_mode(True, True), MODE_LIVE)

    def test_automatic_after_the_run_is_deferred(self):
        self.assertEqual(resolve_display_mode(True, False), MODE_DEFERRED)

    def test_manual_generation_is_operator_initiated_either_way(self):
        self.assertEqual(resolve_display_mode(False, True), MODE_OPERATOR)
        self.assertEqual(resolve_display_mode(False, False), MODE_OPERATOR)

    def test_non_boolean_mode_input_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_display_mode(1, True)


class TestAxes(unittest.TestCase):
    def test_amplitude_against_frequency_has_no_axis_finding(self):
        self.assertEqual(axis_findings(validate_presentation(good_presentation())), [])

    def test_swapped_axes_are_reported_on_both_axes(self):
        config = validate_presentation(
            good_presentation(
                x_quantity="amplitude",
                y_quantity="frequency",
                x_unit="dbuv_m",
                y_unit="mhz",
            )
        )
        self.assertEqual(len(axis_findings(config)), 2)

    def test_amplitude_axis_in_a_frequency_unit_is_reported(self):
        config = validate_presentation(good_presentation(y_unit="khz"))
        findings = axis_findings(config)
        self.assertEqual(len(findings), 1)
        self.assertIn("not an amplitude unit", findings[0])

    def test_time_on_the_horizontal_axis_is_reported(self):
        config = validate_presentation(good_presentation(x_quantity="time"))
        self.assertTrue(any("needs frequency" in f for f in axis_findings(config)))


class TestAxisSpan(unittest.TestCase):
    def test_axis_covering_the_band_has_no_shortfall(self):
        config = validate_presentation(good_presentation())
        self.assertEqual(axis_span_shortfalls(config, BAND_START, BAND_STOP), [])

    def test_axis_starting_too_high_is_reported(self):
        config = validate_presentation(good_presentation(plot_start_hz=50.0e6))
        shortfalls = axis_span_shortfalls(config, BAND_START, BAND_STOP)
        self.assertEqual(len(shortfalls), 1)
        self.assertIn("above the declared band start", shortfalls[0])

    def test_axis_stopping_too_low_is_reported(self):
        config = validate_presentation(good_presentation(plot_stop_hz=500.0e6))
        shortfalls = axis_span_shortfalls(config, BAND_START, BAND_STOP)
        self.assertEqual(len(shortfalls), 1)
        self.assertIn("below the declared band stop", shortfalls[0])

    def test_axis_wider_than_the_band_is_not_a_shortfall(self):
        config = validate_presentation(
            good_presentation(plot_start_hz=10.0e6, plot_stop_hz=2000.0e6)
        )
        self.assertEqual(axis_span_shortfalls(config, BAND_START, BAND_STOP), [])

    def test_inverted_band_is_rejected(self):
        config = validate_presentation(good_presentation())
        with self.assertRaises(ValueError):
            axis_span_shortfalls(config, BAND_STOP, BAND_START)


class TestRefreshAndLatency(unittest.TestCase):
    def test_allowed_refresh_is_the_sweep_split_by_the_update_count(self):
        bound = max_refresh_interval_s(SWEEP_TIME_S, DEFAULT_MIN_UPDATES_PER_SWEEP)
        self.assertAlmostEqual(bound, 0.5, places=9)

    def test_refresh_exactly_at_the_bound_still_counts_as_live(self):
        bound = max_refresh_interval_s(SWEEP_TIME_S)
        self.assertAlmostEqual(bound, 0.5, places=9)
        self.assertTrue(refresh_is_live(bound, SWEEP_TIME_S))

    def test_refresh_well_past_the_bound_is_not_live(self):
        self.assertFalse(refresh_is_live(1.5, SWEEP_TIME_S))

    def test_update_count_across_one_sweep(self):
        self.assertEqual(updates_per_sweep(SWEEP_TIME_S, 0.25), 8)

    def test_a_refresh_longer_than_the_sweep_yields_no_update(self):
        self.assertEqual(updates_per_sweep(SWEEP_TIME_S, 4.0), 0)

    def test_latency_equal_to_the_refresh_interval_is_current(self):
        self.assertTrue(latency_is_current(0.25, 0.25))

    def test_latency_past_the_refresh_interval_is_stale(self):
        self.assertFalse(latency_is_current(1.0, 0.25))

    def test_update_count_rejects_a_zero_sweep(self):
        with self.assertRaises(ValueError):
            updates_per_sweep(0.0, 0.25)

    def test_fewer_than_one_update_per_sweep_is_rejected(self):
        with self.assertRaises(ValueError):
            max_refresh_interval_s(SWEEP_TIME_S, 0.5)


class TestFullAssessment(unittest.TestCase):
    def test_live_automatic_chain_is_compliant(self):
        report = assess_emission_data_presentation(
            good_presentation(), BAND_START, BAND_STOP, SWEEP_TIME_S
        )
        self.assertEqual(report["display_mode"], MODE_LIVE)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], "presentation-compliant")

    def test_post_run_plotting_is_deficient(self):
        report = assess_emission_data_presentation(
            good_presentation(displayed_during_run=False),
            BAND_START,
            BAND_STOP,
            SWEEP_TIME_S,
        )
        self.assertEqual(report["display_mode"], MODE_DEFERRED)
        self.assertEqual(report["verdict"], "presentation-deficient")

    def test_operator_initiated_plotting_is_deficient(self):
        report = assess_emission_data_presentation(
            good_presentation(automatic_generation=False),
            BAND_START,
            BAND_STOP,
            SWEEP_TIME_S,
        )
        self.assertTrue(any("operator asks" in f for f in report["findings"]))

    def test_missing_limit_line_is_a_limitation_not_a_finding(self):
        report = assess_emission_data_presentation(
            good_presentation(limit_line_shown=False),
            BAND_START,
            BAND_STOP,
            SWEEP_TIME_S,
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("limit line" in m for m in report["limitations"]))
        self.assertEqual(report["verdict"], "presentation-compliant")

    def test_slow_refresh_is_a_finding(self):
        report = assess_emission_data_presentation(
            good_presentation(refresh_interval_s=1.5),
            BAND_START,
            BAND_STOP,
            SWEEP_TIME_S,
        )
        self.assertFalse(report["refresh_is_live"])
        self.assertEqual(report["verdict"], "presentation-deficient")

    def test_stale_latency_is_a_limitation(self):
        report = assess_emission_data_presentation(
            good_presentation(display_latency_s=0.4),
            BAND_START,
            BAND_STOP,
            SWEEP_TIME_S,
        )
        self.assertFalse(report["latency_is_current"])
        self.assertEqual(report["findings"], [])

    def test_report_carries_the_allowed_refresh_and_update_count(self):
        report = assess_emission_data_presentation(
            good_presentation(), BAND_START, BAND_STOP, SWEEP_TIME_S
        )
        self.assertAlmostEqual(report["max_refresh_interval_s"], 0.5, places=9)
        self.assertEqual(report["updates_per_sweep"], 8)

    def test_assessment_propagates_a_configuration_error(self):
        with self.assertRaises(ValueError):
            assess_emission_data_presentation(
                good_presentation(refresh_interval_s=0.0),
                BAND_START,
                BAND_STOP,
                SWEEP_TIME_S,
            )


if __name__ == "__main__":
    unittest.main()
