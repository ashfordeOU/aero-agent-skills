#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-electric-susceptibility-reporting.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_electric_susceptibility_reporting.py
"""

import math
import unittest

from e2007_radiated_electric_susceptibility_reporting_logic import (
    CATEGORY_IRRECONCILABLE,
    CATEGORY_REPORTABLE,
    CATEGORY_UNPRESENTED,
    DECADE_RATIO,
    DEFAULT_FIELD_TOLERANCE_DB,
    REQUIRED_POINT_FIELDS,
    VERDICT_REJECTED,
    VERDICT_REPORTABLE,
    assess_report,
    axis_scale_adequate,
    categorize_point,
    field_discrepancy_db,
    net_forward_power,
    normalize_point,
    normalize_points,
    normalize_tabulated,
    predicted_field,
    validate_graph,
)

FACTOR = 10.0
FREQUENCIES = (1.0e8, 2.0e8, 3.0e8)


def a_point(frequency=1.0e8, **over):
    record = {
        "frequency_hz": frequency,
        "generator_setting_dbm": 12.0,
        "forward_power_w": 100.0,
        "reflected_power_w": 0.0,
        "achieved_field_v_per_m": 100.0,
    }
    record.update(over)
    return record


def a_run(frequencies=FREQUENCIES, **over):
    return [a_point(frequency=f, **over) for f in frequencies]


def a_graph(**over):
    record = {
        "frequency_axis_label": "frequency, hertz",
        "level_axis_label": "achieved field, volt per metre",
        "frequency_axis_scale": "linear",
        "plotted_frequencies_hz": list(FREQUENCIES),
    }
    record.update(over)
    return record


class TestPointRecords(unittest.TestCase):
    def test_a_complete_point_normalizes(self):
        point = normalize_point(a_point())
        self.assertEqual(sorted(point), sorted(REQUIRED_POINT_FIELDS))

    def test_point_missing_a_field_rejected(self):
        broken = a_point()
        del broken["generator_setting_dbm"]
        with self.assertRaises(ValueError):
            normalize_point(broken)

    def test_point_with_an_invented_field_rejected(self):
        with self.assertRaises(ValueError):
            normalize_point(a_point(operator_initials=1.0))

    def test_non_positive_frequency_rejected(self):
        with self.assertRaises(ValueError):
            normalize_point(a_point(frequency=0.0))

    def test_non_positive_forward_power_rejected(self):
        with self.assertRaises(ValueError):
            normalize_point(a_point(forward_power_w=0.0))

    def test_negative_reflected_power_rejected(self):
        with self.assertRaises(ValueError):
            normalize_point(a_point(reflected_power_w=-1.0))

    def test_non_positive_achieved_field_rejected(self):
        with self.assertRaises(ValueError):
            normalize_point(a_point(achieved_field_v_per_m=0.0))

    def test_non_numeric_field_rejected(self):
        with self.assertRaises(ValueError):
            normalize_point(a_point(forward_power_w="100"))

    def test_non_mapping_point_rejected(self):
        with self.assertRaises(ValueError):
            normalize_point(["frequency_hz"])


class TestPointSets(unittest.TestCase):
    def test_points_come_back_sorted_by_frequency(self):
        points = normalize_points(a_run((3.0e8, 1.0e8, 2.0e8)))
        self.assertAlmostEqual(points[0]["frequency_hz"], 1.0e8, places=9)
        self.assertAlmostEqual(points[-1]["frequency_hz"], 3.0e8, places=9)

    def test_empty_point_set_rejected(self):
        with self.assertRaises(ValueError):
            normalize_points([])

    def test_duplicate_frequency_rejected(self):
        with self.assertRaises(ValueError):
            normalize_points(a_run((1.0e8, 1.0e8)))

    def test_non_sequence_point_set_rejected(self):
        with self.assertRaises(ValueError):
            normalize_points({"frequency_hz": 1.0e8})


class TestNetPower(unittest.TestCase):
    def test_no_reflection_delivers_the_whole_forward_power(self):
        self.assertAlmostEqual(net_forward_power(100.0, 0.0), 100.0, places=9)

    def test_reflection_is_subtracted(self):
        self.assertAlmostEqual(net_forward_power(100.0, 25.0), 75.0, places=9)

    def test_a_fully_reflected_drive_delivers_nothing(self):
        self.assertAlmostEqual(net_forward_power(100.0, 100.0), 0.0, places=9)

    def test_reflected_above_forward_rejected(self):
        with self.assertRaises(ValueError):
            net_forward_power(100.0, 140.0)

    def test_non_positive_forward_power_rejected(self):
        with self.assertRaises(ValueError):
            net_forward_power(0.0, 0.0)


class TestPredictedField(unittest.TestCase):
    def test_field_follows_the_square_root_of_power(self):
        self.assertAlmostEqual(predicted_field(100.0, FACTOR), 100.0, places=9)

    def test_four_times_the_power_buys_twice_the_field(self):
        low = predicted_field(100.0, FACTOR)
        high = predicted_field(400.0, FACTOR)
        self.assertAlmostEqual(high, 2.0 * low, places=9)

    def test_no_power_predicts_no_field(self):
        self.assertAlmostEqual(predicted_field(0.0, FACTOR), 0.0, places=9)

    def test_negative_power_rejected(self):
        with self.assertRaises(ValueError):
            predicted_field(-1.0, FACTOR)

    def test_non_positive_chamber_factor_rejected(self):
        with self.assertRaises(ValueError):
            predicted_field(100.0, 0.0)


class TestDiscrepancy(unittest.TestCase):
    def test_a_field_on_prediction_has_no_discrepancy(self):
        self.assertAlmostEqual(field_discrepancy_db(100.0, 100.0), 0.0, places=9)

    def test_twice_the_field_is_about_six_decibels(self):
        self.assertAlmostEqual(field_discrepancy_db(200.0, 100.0), 20.0 * math.log10(2.0), places=9)

    def test_a_field_under_prediction_is_negative(self):
        self.assertAlmostEqual(field_discrepancy_db(50.0, 100.0), -20.0 * math.log10(2.0), places=9)

    def test_ten_times_the_field_is_twenty_decibels(self):
        self.assertAlmostEqual(field_discrepancy_db(1000.0, 100.0), 20.0, places=9)

    def test_non_positive_achieved_field_rejected(self):
        with self.assertRaises(ValueError):
            field_discrepancy_db(0.0, 100.0)

    def test_non_positive_predicted_field_rejected(self):
        with self.assertRaises(ValueError):
            field_discrepancy_db(100.0, 0.0)


class TestGraphExhibit(unittest.TestCase):
    def test_a_complete_graph_normalizes(self):
        graph = validate_graph(a_graph())
        self.assertEqual(graph["frequency_axis_scale"], "linear")
        self.assertEqual(len(graph["plotted_frequencies_hz"]), len(FREQUENCIES))

    def test_an_absent_graph_is_allowed(self):
        self.assertIsNone(validate_graph(None))

    def test_graph_missing_an_axis_label_rejected(self):
        broken = a_graph()
        del broken["level_axis_label"]
        with self.assertRaises(ValueError):
            validate_graph(broken)

    def test_blank_axis_label_rejected(self):
        with self.assertRaises(ValueError):
            validate_graph(a_graph(level_axis_label="   "))

    def test_unrecognized_axis_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_graph(a_graph(frequency_axis_scale="semilog"))

    def test_graph_with_an_invented_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_graph(a_graph(colour_scheme="viridis"))

    def test_non_positive_plotted_frequency_rejected(self):
        with self.assertRaises(ValueError):
            validate_graph(a_graph(plotted_frequencies_hz=[0.0]))

    def test_plotted_frequencies_come_back_sorted(self):
        graph = validate_graph(a_graph(plotted_frequencies_hz=[3.0e8, 1.0e8]))
        self.assertAlmostEqual(graph["plotted_frequencies_hz"][0], 1.0e8, places=9)


class TestAxisScale(unittest.TestCase):
    def test_a_narrow_span_may_use_a_linear_axis(self):
        self.assertTrue(axis_scale_adequate(validate_graph(a_graph()), 1.0e8, 3.0e8))

    def test_a_span_of_exactly_a_decade_needs_a_logarithmic_axis(self):
        graph = validate_graph(a_graph())
        self.assertFalse(axis_scale_adequate(graph, 1.0e8, 1.0e8 * DECADE_RATIO))

    def test_a_logarithmic_axis_carries_a_wide_span(self):
        graph = validate_graph(a_graph(frequency_axis_scale="logarithmic"))
        self.assertTrue(axis_scale_adequate(graph, 1.0e7, 1.0e9))

    def test_an_absent_graph_never_fails_the_axis_check(self):
        self.assertTrue(axis_scale_adequate(None, 1.0e7, 1.0e9))

    def test_a_stop_below_the_start_rejected(self):
        graph = validate_graph(a_graph())
        with self.assertRaises(ValueError):
            axis_scale_adequate(graph, 3.0e8, 1.0e8)


class TestTabulated(unittest.TestCase):
    def test_tabulated_frequencies_come_back_sorted(self):
        self.assertEqual(normalize_tabulated([3.0e8, 1.0e8]), (1.0e8, 3.0e8))

    def test_an_empty_table_is_allowed(self):
        self.assertEqual(normalize_tabulated([]), ())

    def test_non_positive_tabulated_frequency_rejected(self):
        with self.assertRaises(ValueError):
            normalize_tabulated([-1.0e8])

    def test_non_sequence_table_rejected(self):
        with self.assertRaises(ValueError):
            normalize_tabulated(1.0e8)


class TestCategorization(unittest.TestCase):
    def test_a_tabulated_reconcilable_point_is_reportable(self):
        self.assertEqual(
            categorize_point(a_point(), FACTOR, FREQUENCIES, DEFAULT_FIELD_TOLERANCE_DB),
            CATEGORY_REPORTABLE,
        )

    def test_a_point_on_no_exhibit_is_unpresented(self):
        self.assertEqual(
            categorize_point(a_point(), FACTOR, (), DEFAULT_FIELD_TOLERANCE_DB),
            CATEGORY_UNPRESENTED,
        )

    def test_a_field_far_from_prediction_is_irreconcilable(self):
        self.assertEqual(
            categorize_point(
                a_point(achieved_field_v_per_m=1000.0),
                FACTOR,
                FREQUENCIES,
                DEFAULT_FIELD_TOLERANCE_DB,
            ),
            CATEGORY_IRRECONCILABLE,
        )

    def test_a_field_exactly_on_the_tolerance_is_still_reportable(self):
        achieved = 100.0 * 10.0 ** (DEFAULT_FIELD_TOLERANCE_DB / 20.0)
        self.assertAlmostEqual(
            field_discrepancy_db(achieved, 100.0), DEFAULT_FIELD_TOLERANCE_DB, places=9
        )
        self.assertEqual(
            categorize_point(
                a_point(achieved_field_v_per_m=achieved),
                FACTOR,
                FREQUENCIES,
                DEFAULT_FIELD_TOLERANCE_DB,
            ),
            CATEGORY_REPORTABLE,
        )

    def test_a_fully_reflected_drive_is_irreconcilable(self):
        self.assertEqual(
            categorize_point(
                a_point(reflected_power_w=100.0),
                FACTOR,
                FREQUENCIES,
                DEFAULT_FIELD_TOLERANCE_DB,
            ),
            CATEGORY_IRRECONCILABLE,
        )


class TestReportAssessment(unittest.TestCase):
    def test_a_tabulated_run_is_presentation_complete(self):
        result = assess_report(a_run(), FACTOR, FREQUENCIES)
        self.assertEqual(result["verdict"], VERDICT_REPORTABLE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["counts"][CATEGORY_REPORTABLE], len(FREQUENCIES))

    def test_a_graphed_run_is_presentation_complete(self):
        result = assess_report(a_run(), FACTOR, (), a_graph())
        self.assertEqual(result["verdict"], VERDICT_REPORTABLE)

    def test_a_report_with_no_exhibit_at_all_is_rejected(self):
        result = assess_report(a_run(), FACTOR, (), None)
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertTrue(
            any("neither a table nor a graph" in f for f in result["findings"])
        )

    def test_a_point_on_no_exhibit_is_a_finding(self):
        result = assess_report(a_run(), FACTOR, FREQUENCIES[:2])
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["counts"][CATEGORY_UNPRESENTED], 1)

    def test_table_and_graph_together_cover_the_run(self):
        result = assess_report(
            a_run(),
            FACTOR,
            FREQUENCIES[:1],
            a_graph(plotted_frequencies_hz=list(FREQUENCIES[1:])),
        )
        self.assertEqual(result["verdict"], VERDICT_REPORTABLE)

    def test_a_wide_span_on_a_linear_axis_is_a_finding(self):
        wide = (1.0e7, 1.0e8, 1.0e9)
        result = assess_report(
            a_run(wide), FACTOR, (), a_graph(plotted_frequencies_hz=list(wide))
        )
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertTrue(any("linear scale" in f for f in result["findings"]))

    def test_the_same_wide_span_passes_on_a_logarithmic_axis(self):
        wide = (1.0e7, 1.0e8, 1.0e9)
        result = assess_report(
            a_run(wide),
            FACTOR,
            (),
            a_graph(
                frequency_axis_scale="logarithmic", plotted_frequencies_hz=list(wide)
            ),
        )
        self.assertEqual(result["verdict"], VERDICT_REPORTABLE)

    def test_an_irreconcilable_field_rejects_the_report(self):
        points = a_run()
        points[1]["achieved_field_v_per_m"] = 1000.0
        result = assess_report(points, FACTOR, FREQUENCIES)
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["counts"][CATEGORY_IRRECONCILABLE], 1)

    def test_heavy_reflection_is_carried_as_a_limitation(self):
        points = a_run()
        points[0]["reflected_power_w"] = 40.0
        points[0]["achieved_field_v_per_m"] = predicted_field(60.0, FACTOR)
        result = assess_report(points, FACTOR, FREQUENCIES)
        self.assertEqual(result["verdict"], VERDICT_REPORTABLE)
        self.assertEqual(len(result["limitations"]), 1)

    def test_every_point_is_reported_with_its_derived_figures(self):
        result = assess_report(a_run(), FACTOR, FREQUENCIES)
        self.assertEqual(len(result["points"]), len(FREQUENCIES))
        for entry in result["points"]:
            self.assertAlmostEqual(entry["net_forward_power_w"], 100.0, places=9)
            self.assertAlmostEqual(entry["predicted_field_v_per_m"], 100.0, places=9)
            self.assertAlmostEqual(entry["discrepancy_db"], 0.0, places=9)

    def test_the_reported_span_is_the_range_the_points_cover(self):
        result = assess_report(a_run(), FACTOR, FREQUENCIES)
        self.assertAlmostEqual(result["reported_span_hz"][0], FREQUENCIES[0], places=9)
        self.assertAlmostEqual(result["reported_span_hz"][1], FREQUENCIES[-1], places=9)

    def test_a_tighter_tolerance_turns_a_reportable_point_irreconcilable(self):
        achieved = 100.0 * 10.0 ** (1.5 / 20.0)
        points = a_run()
        for point in points:
            point["achieved_field_v_per_m"] = achieved
        self.assertEqual(
            assess_report(points, FACTOR, FREQUENCIES)["verdict"], VERDICT_REPORTABLE
        )
        self.assertEqual(
            assess_report(points, FACTOR, FREQUENCIES, None, 1.0)["verdict"],
            VERDICT_REJECTED,
        )

    def test_non_positive_chamber_factor_rejected(self):
        with self.assertRaises(ValueError):
            assess_report(a_run(), 0.0, FREQUENCIES)

    def test_non_positive_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            assess_report(a_run(), FACTOR, FREQUENCIES, None, 0.0)

    def test_the_graph_the_report_was_graded_against_is_returned(self):
        result = assess_report(a_run(), FACTOR, (), a_graph())
        self.assertEqual(result["graph"]["frequency_axis_label"], "frequency, hertz")


if __name__ == "__main__":
    unittest.main(verbosity=0)
