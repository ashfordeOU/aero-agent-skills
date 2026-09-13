#!/usr/bin/env python3
"""Contract test for the clause 5.3.3.4 tabulated multipactor chart logic."""

import math
import unittest

from e2001_standard_multipactor_charts_logic import (
    assess_first_level_campaign,
    assess_gap_first_level,
    chart_validity_range,
    equivalent_gap_voltage,
    frequency_gap_product,
    lookup_threshold_voltage,
    multipactor_margin_db,
    select_chart,
    validate_chart,
)

SILVER_POINTS = [
    (0.1, 60.0),
    (1.0, 300.0),
    (10.0, 1800.0),
    (100.0, 12000.0),
]

ALODINE_POINTS = [
    (0.1, 45.0),
    (1.0, 210.0),
    (10.0, 1300.0),
]


def chart(**over):
    entry = {
        "base_material": "aluminium-alloy",
        "surface_treatment": "silver-plated",
        "points": list(SILVER_POINTS),
    }
    entry.update(over)
    return entry


CHARTS = [
    chart(),
    chart(surface_treatment="alodine-conversion-coated", points=list(ALODINE_POINTS)),
]


def gap(**over):
    entry = {
        "name": "output-filter-iris",
        "base_material": "aluminium-alloy",
        "surface_treatment": "silver-plated",
        "frequency_ghz": 4.0,
        "gap_mm": 0.25,
        "peak_power_w": 40.0,
        "impedance_ohm": 50.0,
    }
    entry.update(over)
    return entry


class FrequencyGapProductTests(unittest.TestCase):
    def test_product_is_frequency_times_gap(self):
        self.assertAlmostEqual(frequency_gap_product(12.0, 0.5), 6.0)

    def test_non_positive_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product(0.0, 0.5)

    def test_negative_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product(12.0, -0.5)

    def test_non_numeric_input_is_rejected(self):
        with self.assertRaises(ValueError):
            frequency_gap_product("12", 0.5)


class ChartValidationTests(unittest.TestCase):
    def test_valid_chart_is_normalized_with_its_range(self):
        entry = validate_chart(chart())
        self.assertAlmostEqual(entry["fd_min_ghz_mm"], 0.1)
        self.assertAlmostEqual(entry["fd_max_ghz_mm"], 100.0)

    def test_validity_range_is_reported_as_a_pair(self):
        low, high = chart_validity_range(chart())
        self.assertAlmostEqual(low, 0.1)
        self.assertAlmostEqual(high, 100.0)

    def test_non_mapping_chart_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_chart(SILVER_POINTS)

    def test_missing_surface_treatment_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_chart(chart(surface_treatment=""))

    def test_single_point_chart_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_chart(chart(points=[(1.0, 300.0)]))

    def test_malformed_point_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_chart(chart(points=[(1.0, 300.0), (10.0,)]))

    def test_non_increasing_abscissae_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_chart(chart(points=[(1.0, 300.0), (0.5, 200.0)]))

    def test_non_positive_threshold_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_chart(chart(points=[(1.0, 0.0), (10.0, 1800.0)]))

    def test_non_positive_abscissa_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_chart(chart(points=[(0.0, 300.0), (10.0, 1800.0)]))


class ChartSelectionTests(unittest.TestCase):
    def test_chart_is_selected_by_surface(self):
        entry = select_chart(CHARTS, "aluminium-alloy", "alodine-conversion-coated")
        self.assertAlmostEqual(entry["fd_max_ghz_mm"], 10.0)

    def test_selection_normalizes_case_and_spacing(self):
        entry = select_chart(CHARTS, " Aluminium-Alloy ", "SILVER-PLATED")
        self.assertAlmostEqual(entry["fd_max_ghz_mm"], 100.0)

    def test_untabulated_surface_is_rejected(self):
        with self.assertRaises(ValueError):
            select_chart(CHARTS, "titanium-alloy", "bare")

    def test_empty_chart_collection_is_rejected(self):
        with self.assertRaises(ValueError):
            select_chart([], "aluminium-alloy", "silver-plated")


class ThresholdLookupTests(unittest.TestCase):
    def test_lookup_at_a_tabulated_point_returns_that_point(self):
        self.assertAlmostEqual(lookup_threshold_voltage(chart(), 1.0), 300.0)

    def test_lookup_between_points_is_logarithmic(self):
        expected = 10.0 ** (
            math.log10(300.0)
            + (math.log10(3.0) - math.log10(1.0))
            / (math.log10(10.0) - math.log10(1.0))
            * (math.log10(1800.0) - math.log10(300.0))
        )
        self.assertAlmostEqual(lookup_threshold_voltage(chart(), 3.0), expected)

    def test_logarithmic_read_out_differs_from_the_linear_chord(self):
        # The tabulated charts follow a power law across a decade, so reading
        # them on linear paper under-reads the threshold between points.
        linear = 300.0 + (3.0 - 1.0) / (10.0 - 1.0) * (1800.0 - 300.0)
        self.assertGreater(lookup_threshold_voltage(chart(), 3.0), linear)

    def test_lookup_at_the_lower_bound_is_allowed(self):
        self.assertAlmostEqual(lookup_threshold_voltage(chart(), 0.1), 60.0)

    def test_lookup_at_the_upper_bound_is_allowed(self):
        self.assertAlmostEqual(lookup_threshold_voltage(chart(), 100.0), 12000.0)

    def test_lookup_below_the_chart_is_rejected(self):
        with self.assertRaises(ValueError):
            lookup_threshold_voltage(chart(), 0.01)

    def test_lookup_above_the_chart_is_rejected(self):
        with self.assertRaises(ValueError):
            lookup_threshold_voltage(chart(), 400.0)

    def test_non_positive_abscissa_lookup_is_rejected(self):
        with self.assertRaises(ValueError):
            lookup_threshold_voltage(chart(), 0.0)

    def test_abscissa_a_few_ulps_over_the_bound_still_reads_the_chart(self):
        narrow = chart(points=[(0.1, 60.0), (1.0, 300.0), (3.3, 800.0)])
        fd_value = frequency_gap_product(3.0, 1.1)
        self.assertGreater(fd_value, 3.3)
        self.assertAlmostEqual(lookup_threshold_voltage(narrow, fd_value), 800.0)


class VoltageAndMarginTests(unittest.TestCase):
    def test_equivalent_voltage_follows_the_matched_line_relation(self):
        self.assertAlmostEqual(equivalent_gap_voltage(40.0, 50.0), math.sqrt(4000.0))

    def test_non_positive_power_is_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_gap_voltage(0.0, 50.0)

    def test_non_positive_impedance_is_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_gap_voltage(40.0, -50.0)

    def test_margin_of_a_doubled_threshold_is_six_decibel(self):
        self.assertAlmostEqual(multipactor_margin_db(200.0, 100.0), 6.0205999132)

    def test_margin_is_negative_when_operating_exceeds_threshold(self):
        self.assertLess(multipactor_margin_db(100.0, 200.0), 0.0)

    def test_non_positive_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            multipactor_margin_db(0.0, 100.0)

    def test_non_positive_operating_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            multipactor_margin_db(100.0, 0.0)


class FirstLevelAssessmentTests(unittest.TestCase):
    def test_comfortable_gap_is_compliant(self):
        result = assess_gap_first_level(gap(), CHARTS, 6.0)
        self.assertEqual(result["verdict"], "compliant")
        self.assertAlmostEqual(result["frequency_gap_product_ghz_mm"], 1.0)
        self.assertAlmostEqual(result["threshold_voltage_v"], 300.0)

    def test_operating_voltage_may_be_given_directly(self):
        result = assess_gap_first_level(
            gap(operating_voltage_v=100.0), CHARTS, 6.0
        )
        self.assertAlmostEqual(result["operating_voltage_v"], 100.0)
        self.assertAlmostEqual(result["margin_db"], multipactor_margin_db(300.0, 100.0))

    def test_overdriven_gap_has_insufficient_margin(self):
        result = assess_gap_first_level(
            gap(operating_voltage_v=280.0), CHARTS, 6.0
        )
        self.assertEqual(result["verdict"], "insufficient-margin")
        self.assertFalse(result["escalate_to_dedicated_analysis"])

    def test_margin_exactly_on_the_requirement_is_compliant(self):
        operating = 300.0 / (10.0 ** (7.5 / 20.0))
        raw_margin = multipactor_margin_db(300.0, operating)
        self.assertLess(raw_margin, 7.5)
        result = assess_gap_first_level(
            gap(operating_voltage_v=operating), CHARTS, 7.5
        )
        self.assertEqual(result["verdict"], "compliant")

    def test_gap_beyond_the_chart_is_escalated_not_failed(self):
        result = assess_gap_first_level(
            gap(frequency_ghz=30.0, gap_mm=8.0), CHARTS, 6.0
        )
        self.assertEqual(result["verdict"], "chart-range-exceeded")
        self.assertTrue(result["escalate_to_dedicated_analysis"])
        self.assertIsNone(result["margin_db"])

    def test_gap_below_the_chart_is_escalated(self):
        result = assess_gap_first_level(
            gap(frequency_ghz=0.2, gap_mm=0.05), CHARTS, 6.0
        )
        self.assertEqual(result["verdict"], "chart-range-exceeded")

    def test_untabulated_surface_raises(self):
        with self.assertRaises(ValueError):
            assess_gap_first_level(gap(surface_treatment="gold-plated"), CHARTS, 6.0)

    def test_unnamed_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_gap_first_level(gap(name="   "), CHARTS, 6.0)

    def test_non_mapping_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_gap_first_level(["output-filter-iris"], CHARTS, 6.0)

    def test_negative_required_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_gap_first_level(gap(), CHARTS, -1.0)

    def test_non_positive_supplied_operating_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_gap_first_level(gap(operating_voltage_v=0.0), CHARTS, 6.0)


class CampaignTests(unittest.TestCase):
    def test_campaign_closes_when_every_gap_is_compliant(self):
        summary = assess_first_level_campaign(
            [gap(), gap(name="input-manifold-step", peak_power_w=20.0)], CHARTS, 6.0
        )
        self.assertTrue(summary["first_level_closed"])
        self.assertEqual(len(summary["compliant_gaps"]), 2)

    def test_campaign_lists_failing_and_escalated_gaps_apart(self):
        summary = assess_first_level_campaign(
            [
                gap(),
                gap(name="ridge-step", operating_voltage_v=280.0),
                gap(name="wide-iris", frequency_ghz=30.0, gap_mm=8.0),
            ],
            CHARTS,
            6.0,
        )
        self.assertEqual(summary["failing_gaps"], ["ridge-step"])
        self.assertEqual(summary["escalated_gaps"], ["wide-iris"])
        self.assertFalse(summary["first_level_closed"])

    def test_campaign_reports_the_worst_margin(self):
        summary = assess_first_level_campaign(
            [gap(), gap(name="ridge-step", operating_voltage_v=280.0)], CHARTS, 6.0
        )
        self.assertAlmostEqual(
            summary["worst_margin_db"], multipactor_margin_db(300.0, 280.0)
        )

    def test_duplicate_gap_names_are_rejected(self):
        with self.assertRaises(ValueError):
            assess_first_level_campaign([gap(), gap()], CHARTS, 6.0)

    def test_empty_campaign_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_first_level_campaign([], CHARTS, 6.0)


if __name__ == "__main__":
    unittest.main()
