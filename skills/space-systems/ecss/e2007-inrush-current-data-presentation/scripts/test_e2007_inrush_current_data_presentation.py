#!/usr/bin/env python3
"""Gate 3 contract test for e2007-inrush-current-data-presentation.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_inrush_current_data_presentation.py
"""

import unittest

from e2007_inrush_current_data_presentation_logic import (
    REQUIRED_CONDITIONS,
    VERDICT_COMPLIANT,
    VERDICT_DEFICIENT,
    assess_inrush_data_presentation,
    axis_findings,
    missing_conditions,
    normalize_condition,
    peak_is_clipped,
    peak_to_steady_ratio,
    samples_on_rising_edge,
    scale_utilisation,
    time_span_shortfalls,
    validate_graph,
)

SWITCHING_INSTANT_S = 0.0
SETTLE_TIME_S = 0.05
RISE_TIME_S = 2.0e-5


def good_graph(**over):
    record = {
        "x_quantity": "time",
        "y_quantity": "current",
        "x_unit": "ms",
        "y_unit": "a",
        "plot_start_s": -0.005,
        "plot_stop_s": 0.08,
        "full_scale_a": 20.0,
        "peak_current_a": 12.0,
        "steady_current_a": 1.5,
        "sample_interval_s": 1.0e-6,
        "stated_conditions": list(REQUIRED_CONDITIONS),
    }
    record.update(over)
    return record


def assess(**over):
    return assess_inrush_data_presentation(
        good_graph(**over), SWITCHING_INSTANT_S, SETTLE_TIME_S, RISE_TIME_S
    )


class TestGraphValidation(unittest.TestCase):
    def test_good_graph_normalizes(self):
        graph = validate_graph(good_graph())
        self.assertEqual(graph["y_quantity"], "current")
        self.assertAlmostEqual(graph["peak_current_a"], 12.0, places=9)

    def test_unit_token_is_case_normalized(self):
        graph = validate_graph(good_graph(y_unit="A"))
        self.assertEqual(graph["y_unit"], "a")

    def test_unrecognized_quantity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_graph(good_graph(y_quantity="charge"))

    def test_unrecognized_unit_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_graph(good_graph(x_unit="fortnights"))

    def test_inverted_time_span_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_graph(good_graph(plot_start_s=0.08, plot_stop_s=-0.005))

    def test_a_negative_plot_start_is_accepted_as_pre_trigger(self):
        graph = validate_graph(good_graph())
        self.assertLess(graph["plot_start_s"], 0.0)

    def test_zero_full_scale_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_graph(good_graph(full_scale_a=0.0))

    def test_a_steady_draw_above_the_peak_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_graph(good_graph(steady_current_a=30.0))

    def test_stated_conditions_as_a_bare_string_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_graph(good_graph(stated_conditions="bus-voltage"))

    def test_missing_field_is_rejected(self):
        record = good_graph()
        del record["sample_interval_s"]
        with self.assertRaises(ValueError):
            validate_graph(record)

    def test_boolean_peak_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_graph(good_graph(peak_current_a=True))


class TestStatedConditions(unittest.TestCase):
    def test_labels_are_normalized_across_spelling(self):
        self.assertEqual(normalize_condition("Bus_Voltage"), "bus-voltage")
        self.assertEqual(normalize_condition("  load configuration "), "load-configuration")

    def test_an_empty_label_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_condition("   ")

    def test_a_full_condition_set_leaves_nothing_missing(self):
        self.assertEqual(missing_conditions(REQUIRED_CONDITIONS), [])

    def test_absent_conditions_are_listed_in_the_required_order(self):
        stated = ("bus-voltage", "switching-event")
        self.assertEqual(
            missing_conditions(stated),
            ["ambient-temperature", "load-configuration", "source-impedance"],
        )

    def test_a_non_sequence_condition_set_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_conditions("bus-voltage")


class TestAxes(unittest.TestCase):
    def test_current_against_time_has_no_axis_finding(self):
        self.assertEqual(axis_findings(validate_graph(good_graph())), [])

    def test_swapped_axes_are_reported_on_both_axes(self):
        graph = validate_graph(
            good_graph(
                x_quantity="current", y_quantity="time", x_unit="a", y_unit="ms"
            )
        )
        self.assertEqual(len(axis_findings(graph)), 2)

    def test_a_time_unit_on_the_current_axis_is_reported(self):
        graph = validate_graph(good_graph(y_unit="ms"))
        self.assertEqual(len(axis_findings(graph)), 1)

    def test_axis_findings_rejects_an_incomplete_record(self):
        with self.assertRaises(ValueError):
            axis_findings({"x_quantity": "time"})


class TestTimeSpan(unittest.TestCase):
    def test_a_covering_span_has_no_shortfall(self):
        graph = validate_graph(good_graph())
        self.assertEqual(
            time_span_shortfalls(graph, SWITCHING_INSTANT_S, SETTLE_TIME_S), []
        )

    def test_a_span_closing_exactly_at_settling_has_no_shortfall(self):
        graph = validate_graph(good_graph(plot_stop_s=SETTLE_TIME_S))
        self.assertEqual(
            time_span_shortfalls(graph, SWITCHING_INSTANT_S, SETTLE_TIME_S), []
        )

    def test_a_span_opening_after_the_switching_instant_is_reported(self):
        graph = validate_graph(good_graph(plot_start_s=0.001))
        self.assertEqual(
            len(time_span_shortfalls(graph, SWITCHING_INSTANT_S, SETTLE_TIME_S)), 1
        )

    def test_a_span_closing_before_settling_is_reported(self):
        graph = validate_graph(good_graph(plot_stop_s=0.01))
        self.assertEqual(
            len(time_span_shortfalls(graph, SWITCHING_INSTANT_S, SETTLE_TIME_S)), 1
        )

    def test_a_settling_time_before_the_switching_instant_is_rejected(self):
        graph = validate_graph(good_graph())
        with self.assertRaises(ValueError):
            time_span_shortfalls(graph, 0.02, 0.01)


class TestVerticalScale(unittest.TestCase):
    def test_a_peak_inside_the_scale_is_not_clipped(self):
        self.assertFalse(peak_is_clipped(12.0, 20.0))

    def test_a_peak_landing_on_full_scale_is_not_clipped(self):
        self.assertFalse(peak_is_clipped(0.1 + 0.2, 0.3))

    def test_a_peak_past_full_scale_is_clipped(self):
        self.assertTrue(peak_is_clipped(24.0, 20.0))

    def test_scale_utilisation_is_the_share_of_the_axis_used(self):
        self.assertAlmostEqual(scale_utilisation(12.0, 20.0), 0.6, places=9)

    def test_scale_utilisation_rejects_a_zero_axis(self):
        with self.assertRaises(ValueError):
            scale_utilisation(12.0, 0.0)


class TestEdgeResolution(unittest.TestCase):
    def test_samples_on_the_edge_are_whole_samples(self):
        self.assertEqual(samples_on_rising_edge(2.0e-5, 1.0e-6), 20)

    def test_an_interval_longer_than_the_edge_resolves_nothing(self):
        self.assertEqual(samples_on_rising_edge(2.0e-5, 1.0e-4), 0)

    def test_a_zero_sample_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            samples_on_rising_edge(2.0e-5, 0.0)

    def test_peak_to_steady_ratio_reports_how_far_the_surge_rises(self):
        self.assertAlmostEqual(peak_to_steady_ratio(12.0, 1.5), 8.0, places=9)

    def test_peak_to_steady_ratio_rejects_a_zero_steady_draw(self):
        with self.assertRaises(ValueError):
            peak_to_steady_ratio(12.0, 0.0)


class TestPresentationAssessment(unittest.TestCase):
    def test_a_good_graph_is_presentation_compliant(self):
        report = assess()
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["limitations"], [])
        self.assertEqual(report["verdict"], VERDICT_COMPLIANT)

    def test_a_clipped_peak_is_a_finding(self):
        report = assess(peak_current_a=24.0)
        self.assertTrue(report["peak_is_clipped"])
        self.assertEqual(report["verdict"], VERDICT_DEFICIENT)

    def test_a_peak_low_in_the_scale_is_a_limitation_not_a_finding(self):
        report = assess(peak_current_a=2.0)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_COMPLIANT)
        self.assertEqual(len(report["limitations"]), 1)

    def test_an_unresolved_rising_edge_is_a_finding(self):
        report = assess(sample_interval_s=1.0e-5)
        self.assertEqual(report["samples_on_rising_edge"], 2)
        self.assertEqual(report["verdict"], VERDICT_DEFICIENT)

    def test_unstated_conditions_are_a_finding_naming_them(self):
        report = assess(stated_conditions=["bus-voltage", "switching-event"])
        self.assertEqual(
            report["missing_conditions"],
            ["ambient-temperature", "load-configuration", "source-impedance"],
        )
        self.assertEqual(report["verdict"], VERDICT_DEFICIENT)

    def test_a_plot_opening_after_the_switching_instant_is_a_finding(self):
        report = assess(plot_start_s=0.001)
        self.assertEqual(len(report["time_span_shortfalls"]), 1)
        self.assertEqual(report["verdict"], VERDICT_DEFICIENT)

    def test_a_surge_barely_above_the_steady_draw_is_a_limitation(self):
        report = assess(full_scale_a=2.0, peak_current_a=1.52, steady_current_a=1.5)
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["limitations"]), 1)

    def test_the_report_carries_the_measured_ratios(self):
        report = assess()
        self.assertAlmostEqual(report["scale_utilisation"], 0.6, places=9)
        self.assertAlmostEqual(report["peak_to_steady_ratio"], 8.0, places=9)

    def test_an_impossible_edge_sample_requirement_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_inrush_data_presentation(
                good_graph(), SWITCHING_INSTANT_S, SETTLE_TIME_S, RISE_TIME_S, 0
            )

    def test_assessment_propagates_a_graph_error(self):
        with self.assertRaises(ValueError):
            assess(full_scale_a=0.0)


if __name__ == "__main__":
    unittest.main()
