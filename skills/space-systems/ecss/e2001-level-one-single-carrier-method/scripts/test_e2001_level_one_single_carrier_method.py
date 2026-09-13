#!/usr/bin/env python3
"""Contract test for the level-one single-carrier multipactor method.

Offline, deterministic, stdlib unittest.
Run: python3 test_e2001_level_one_single_carrier_method.py
"""

import math
import unittest

import e2001_level_one_single_carrier_method_logic as logic


class TestStandingWave(unittest.TestCase):
    def test_matched_line_has_no_reflection(self):
        self.assertAlmostEqual(logic.reflection_magnitude(1.0), 0.0, places=12)

    def test_two_to_one_standing_wave(self):
        self.assertAlmostEqual(logic.reflection_magnitude(2.0), 1.0 / 3.0, places=12)

    def test_standing_wave_below_unity_raises(self):
        with self.assertRaises(ValueError):
            logic.reflection_magnitude(0.9)

    def test_non_numeric_standing_wave_raises(self):
        with self.assertRaises(ValueError):
            logic.reflection_magnitude("1.5")

    def test_infinite_standing_wave_raises(self):
        with self.assertRaises(ValueError):
            logic.reflection_magnitude(float("inf"))


class TestCriticalRegionVoltage(unittest.TestCase):
    def test_matched_peak_voltage(self):
        self.assertAlmostEqual(
            logic.peak_voltage_from_power(100.0, 50.0, 1.0), 100.0, places=9
        )

    def test_standing_wave_raises_the_peak(self):
        self.assertAlmostEqual(
            logic.peak_voltage_from_power(100.0, 50.0, 2.0),
            100.0 * (1.0 + 1.0 / 3.0),
            places=9,
        )

    def test_field_concentration_scales_the_gap_voltage(self):
        self.assertAlmostEqual(
            logic.critical_region_voltage(100.0, 50.0, 1.0, 2.5), 250.0, places=9
        )

    def test_zero_power_raises(self):
        with self.assertRaises(ValueError):
            logic.peak_voltage_from_power(0.0, 50.0, 1.0)

    def test_negative_impedance_raises(self):
        with self.assertRaises(ValueError):
            logic.peak_voltage_from_power(10.0, -50.0, 1.0)

    def test_zero_field_concentration_raises(self):
        with self.assertRaises(ValueError):
            logic.critical_region_voltage(100.0, 50.0, 1.0, 0.0)


class TestFrequencyGapProduct(unittest.TestCase):
    def test_product_is_frequency_times_gap(self):
        self.assertAlmostEqual(
            logic.frequency_gap_product_ghz_mm(8.0, 0.25), 2.0, places=12
        )

    def test_zero_gap_raises(self):
        with self.assertRaises(ValueError):
            logic.frequency_gap_product_ghz_mm(8.0, 0.0)

    def test_negative_frequency_raises(self):
        with self.assertRaises(ValueError):
            logic.frequency_gap_product_ghz_mm(-8.0, 1.0)


class TestSurfaceFinish(unittest.TestCase):
    def test_plating_alias_resolves(self):
        self.assertEqual(logic.normalize_material("Silver-Plated"), "silver")

    def test_spelling_alias_resolves(self):
        self.assertEqual(logic.normalize_material("aluminum"), "aluminium")

    def test_unknown_finish_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_material("anodised-titanium")

    def test_blank_finish_raises(self):
        with self.assertRaises(ValueError):
            logic.normalize_material("  ")


class TestBoundaryChart(unittest.TestCase):
    def test_charted_span(self):
        low, high = logic.chart_range("silver")
        self.assertAlmostEqual(low, 0.05, places=12)
        self.assertAlmostEqual(high, 100.0, places=12)

    def test_node_lookup_returns_the_node(self):
        self.assertAlmostEqual(logic.threshold_voltage("silver", 1.0), 210.0, places=9)

    def test_finish_factor_lowers_the_boundary(self):
        self.assertAlmostEqual(
            logic.threshold_voltage("aluminium", 1.0), 210.0 * 0.75, places=9
        )

    def test_log_log_interpolation_between_nodes(self):
        expected = 360.0 * (780.0 / 360.0) ** (math.log(2.0) / math.log(2.5))
        self.assertAlmostEqual(logic.threshold_voltage("silver", 4.0), expected, places=6)

    def test_geometric_midpoint_is_the_geometric_mean(self):
        midpoint = math.sqrt(1.0 * 2.0)
        self.assertAlmostEqual(
            logic.threshold_voltage("silver", midpoint),
            math.sqrt(210.0 * 360.0),
            places=6,
        )

    def test_product_below_the_span_raises(self):
        with self.assertRaises(ValueError):
            logic.threshold_voltage("silver", 0.01)

    def test_product_above_the_span_raises(self):
        with self.assertRaises(ValueError):
            logic.threshold_voltage("silver", 250.0)

    def test_span_endpoints_are_usable(self):
        self.assertAlmostEqual(logic.threshold_voltage("silver", 0.05), 20.0, places=9)
        self.assertAlmostEqual(logic.threshold_voltage("silver", 100.0), 11000.0, places=9)

    def test_injected_project_chart_is_used(self):
        chart = ((1.0, 500.0), (10.0, 5000.0))
        self.assertAlmostEqual(
            logic.threshold_voltage("silver", 10.0, chart=chart), 5000.0, places=9
        )

    def test_single_point_chart_raises(self):
        with self.assertRaises(ValueError):
            logic.threshold_voltage("silver", 1.0, chart=((1.0, 500.0),))

    def test_non_monotone_chart_raises(self):
        with self.assertRaises(ValueError):
            logic.threshold_voltage(
                "silver", 1.0, chart=((1.0, 500.0), (0.5, 300.0))
            )

    def test_non_positive_chart_voltage_raises(self):
        with self.assertRaises(ValueError):
            logic.threshold_voltage("silver", 1.0, chart=((1.0, 0.0), (10.0, 5000.0)))


class TestMargin(unittest.TestCase):
    def test_factor_of_two_is_six_decibels(self):
        self.assertAlmostEqual(logic.margin_db(200.0, 100.0), 20.0 * math.log10(2.0), places=12)

    def test_equal_voltages_give_zero_margin(self):
        self.assertAlmostEqual(logic.margin_db(140.0, 140.0), 0.0, places=12)

    def test_zero_applied_voltage_raises(self):
        with self.assertRaises(ValueError):
            logic.margin_db(200.0, 0.0)

    def test_route_margins_differ(self):
        self.assertAlmostEqual(logic.required_margin_db("analysis-only"), 6.0, places=12)
        self.assertAlmostEqual(logic.required_margin_db("test-supported"), 3.0, places=12)

    def test_unknown_route_raises(self):
        with self.assertRaises(ValueError):
            logic.required_margin_db("engineering-judgement")

    def test_project_override_replaces_the_route_value(self):
        self.assertAlmostEqual(
            logic.required_margin_db("analysis-only", {"analysis-only": 8.0}),
            8.0,
            places=12,
        )

    def test_non_mapping_override_raises(self):
        with self.assertRaises(ValueError):
            logic.required_margin_db("analysis-only", [("analysis-only", 8.0)])

    def test_margin_exactly_at_the_owed_value_is_compliant(self):
        applied = 100.0
        boundary = applied * 10.0 ** (6.0 / 20.0)
        achieved = logic.margin_db(boundary, applied)
        # The round trip through the decibel definition can land a few units in
        # the last place under 6 dB; a compliant design must not be failed by it.
        self.assertAlmostEqual(achieved, 6.0, places=9)
        self.assertEqual(logic.verdict_for(achieved, 6.0), logic.VERDICT_COMPLIANT)

    def test_positive_but_short_margin_is_insufficient(self):
        self.assertEqual(logic.verdict_for(3.2, 6.0), logic.VERDICT_INSUFFICIENT)

    def test_zero_margin_predicts_a_discharge(self):
        self.assertEqual(logic.verdict_for(0.0, 6.0), logic.VERDICT_PREDICTED)

    def test_negative_margin_predicts_a_discharge(self):
        self.assertEqual(logic.verdict_for(-4.0, 6.0), logic.VERDICT_PREDICTED)


class TestAssessment(unittest.TestCase):
    def test_compliant_region_reports_no_action(self):
        record = logic.assess_single_carrier(
            power_w=50.0,
            frequency_ghz=4.0,
            gap_mm=1.0,
            material="silver",
            region_id="iris-gap",
        )
        expected_boundary = 360.0 * (780.0 / 360.0) ** (math.log(2.0) / math.log(2.5))
        self.assertEqual(record["verdict"], logic.VERDICT_COMPLIANT)
        self.assertEqual(record["actions"], [])
        self.assertEqual(record["region_id"], "iris-gap")
        self.assertAlmostEqual(record["frequency_gap_product_ghz_mm"], 4.0, places=12)
        self.assertAlmostEqual(record["threshold_voltage_v"], expected_boundary, places=6)
        self.assertAlmostEqual(
            record["applied_voltage_v"], math.sqrt(2.0 * 50.0 * 50.0), places=9
        )

    def test_short_margin_region_carries_an_action(self):
        record = logic.assess_single_carrier(
            power_w=2000.0, frequency_ghz=4.0, gap_mm=1.0, material="silver"
        )
        self.assertEqual(record["verdict"], logic.VERDICT_INSUFFICIENT)
        self.assertEqual(len(record["actions"]), 1)
        self.assertLess(record["achieved_margin_db"], 6.0)
        self.assertGreater(record["achieved_margin_db"], 0.0)

    def test_over_boundary_region_is_predicted(self):
        record = logic.assess_single_carrier(
            power_w=10000.0, frequency_ghz=4.0, gap_mm=1.0, material="silver"
        )
        self.assertEqual(record["verdict"], logic.VERDICT_PREDICTED)
        self.assertLess(record["achieved_margin_db"], 0.0)

    def test_test_supported_route_accepts_a_shorter_margin(self):
        record = logic.assess_single_carrier(
            power_w=2000.0,
            frequency_ghz=4.0,
            gap_mm=1.0,
            material="silver",
            route="test-supported",
        )
        self.assertEqual(record["verdict"], logic.VERDICT_COMPLIANT)

    def test_standing_wave_and_concentration_reduce_the_margin(self):
        matched = logic.assess_single_carrier(
            power_w=50.0, frequency_ghz=4.0, gap_mm=1.0, material="silver"
        )
        stressed = logic.assess_single_carrier(
            power_w=50.0,
            frequency_ghz=4.0,
            gap_mm=1.0,
            material="silver",
            vswr=2.0,
            field_concentration=1.5,
        )
        self.assertLess(stressed["achieved_margin_db"], matched["achieved_margin_db"])

    def test_unknown_finish_stops_the_assessment(self):
        with self.assertRaises(ValueError):
            logic.assess_single_carrier(
                power_w=50.0, frequency_ghz=4.0, gap_mm=1.0, material="kapton"
            )

    def test_product_outside_the_chart_stops_the_assessment(self):
        with self.assertRaises(ValueError):
            logic.assess_single_carrier(
                power_w=50.0, frequency_ghz=0.001, gap_mm=1.0, material="silver"
            )


class TestInversionAndRanking(unittest.TestCase):
    def test_maximum_power_round_trips_to_the_owed_margin(self):
        power = logic.maximum_allowable_power_w(
            frequency_ghz=4.0, gap_mm=1.0, material="silver", route="analysis-only"
        )
        record = logic.assess_single_carrier(
            power_w=power, frequency_ghz=4.0, gap_mm=1.0, material="silver"
        )
        self.assertAlmostEqual(record["achieved_margin_db"], 6.0, places=9)
        self.assertEqual(record["verdict"], logic.VERDICT_COMPLIANT)

    def test_standing_wave_lowers_the_allowable_power(self):
        matched = logic.maximum_allowable_power_w(
            frequency_ghz=4.0, gap_mm=1.0, material="silver"
        )
        mismatched = logic.maximum_allowable_power_w(
            frequency_ghz=4.0, gap_mm=1.0, material="silver", vswr=2.0
        )
        self.assertLess(mismatched, matched)

    def test_worst_case_region_is_the_smallest_margin(self):
        records = [
            logic.assess_single_carrier(
                power_w=p, frequency_ghz=4.0, gap_mm=1.0, material="silver", region_id=name
            )
            for name, p in (("a", 50.0), ("b", 2000.0), ("c", 500.0))
        ]
        self.assertEqual(logic.worst_case_region(records)["region_id"], "b")

    def test_worst_case_region_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            logic.worst_case_region([])

    def test_worst_case_region_rejects_a_malformed_record(self):
        with self.assertRaises(ValueError):
            logic.worst_case_region([{"region_id": "a"}])


if __name__ == "__main__":
    unittest.main()
