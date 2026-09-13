"""Contract test for the clause 6.3 multipactor temperature logic (stdlib only)."""

import math
import unittest

import e2001_multipactor_test_temperature_logic as L


def _good_campaign():
    return {
        "predicted_min_c": -20.0,
        "predicted_max_c": 70.0,
        "qualification_margin_k": 10.0,
        "gap_reference_mm": 1.0,
        "expansion_per_k": 2.3e-5,
        "reference_c": 22.0,
        "frequency_ghz": 12.0,
        "applied_power_w": 300.0,
        "required_margin_db": 6.0,
        "tested_points_c": [-30.0, 22.0, 80.0],
        "setpoint_tolerance_k": 3.0,
        "soak_minutes": 90.0,
        "required_soak_minutes": 60.0,
        "measured_drift_k": 1.5,
        "allowed_drift_k": 2.0,
    }


def _extreme(temperature_c, power_w=300.0, required_db=6.0):
    return L.evaluate_extreme(temperature_c, 1.0, 2.3e-5, 22.0, 12.0, power_w, required_db)


class ExtremeLabelTests(unittest.TestCase):
    def test_cold_alias_is_recognised(self):
        self.assertEqual(L.categorize_extreme("Cold Extreme"), "cold")

    def test_maximum_maps_onto_hot(self):
        self.assertEqual(L.categorize_extreme("maximum"), "hot")

    def test_underscored_label_is_recognised(self):
        self.assertEqual(L.categorize_extreme("low_temperature"), "cold")

    def test_uncategorized_label_is_rejected(self):
        with self.assertRaises(ValueError):
            L.categorize_extreme("ambient")

    def test_non_string_label_is_rejected(self):
        with self.assertRaises(ValueError):
            L.categorize_extreme(-40)

    def test_empty_label_is_rejected(self):
        with self.assertRaises(ValueError):
            L.categorize_extreme("  ")


class QualificationExtremeTests(unittest.TestCase):
    def test_margin_widens_the_predicted_range_both_ways(self):
        extremes = L.qualification_extremes(-20.0, 70.0, 10.0)
        self.assertAlmostEqual(extremes["cold_c"], -30.0, places=9)
        self.assertAlmostEqual(extremes["hot_c"], 80.0, places=9)
        self.assertAlmostEqual(extremes["span_k"], 110.0, places=9)

    def test_zero_margin_returns_the_predictions(self):
        extremes = L.qualification_extremes(-20.0, 70.0, 0.0)
        self.assertAlmostEqual(extremes["cold_c"], -20.0, places=9)
        self.assertAlmostEqual(extremes["hot_c"], 70.0, places=9)

    def test_equal_predictions_collapse_to_one_point_plus_margin(self):
        extremes = L.qualification_extremes(25.0, 25.0, 5.0)
        self.assertAlmostEqual(extremes["span_k"], 10.0, places=9)

    def test_inverted_predictions_are_rejected(self):
        with self.assertRaises(ValueError):
            L.qualification_extremes(70.0, -20.0, 10.0)

    def test_negative_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            L.qualification_extremes(-20.0, 70.0, -5.0)

    def test_cold_extreme_below_absolute_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            L.qualification_extremes(-270.0, 70.0, 10.0)


class GapExpansionTests(unittest.TestCase):
    def test_gap_at_the_reference_temperature_is_the_reference_gap(self):
        self.assertAlmostEqual(L.gap_at_temperature(1.0, 2.3e-5, 22.0, 22.0), 1.0, places=12)

    def test_heating_opens_a_positive_expansion_gap(self):
        self.assertGreater(L.gap_at_temperature(1.0, 2.3e-5, 22.0, 80.0), 1.0)

    def test_cooling_closes_a_positive_expansion_gap(self):
        self.assertLess(L.gap_at_temperature(1.0, 2.3e-5, 22.0, -30.0), 1.0)

    def test_gap_matches_the_linear_hand_computation(self):
        expected = 1.0 * (1.0 + 2.3e-5 * (80.0 - 22.0))
        self.assertAlmostEqual(L.gap_at_temperature(1.0, 2.3e-5, 22.0, 80.0), expected, places=12)

    def test_negative_expansion_coefficient_reverses_the_trend(self):
        self.assertGreater(L.gap_at_temperature(1.0, -2.3e-5, 22.0, -30.0), 1.0)

    def test_expansion_that_closes_the_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            L.gap_at_temperature(1.0, 0.5, 22.0, -30.0)

    def test_zero_reference_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            L.gap_at_temperature(0.0, 2.3e-5, 22.0, 22.0)

    def test_temperature_below_absolute_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            L.gap_at_temperature(1.0, 2.3e-5, 22.0, -300.0)


class FrequencyGapTests(unittest.TestCase):
    def test_product_is_frequency_times_gap(self):
        self.assertAlmostEqual(L.frequency_gap_product(12.0, 1.5), 18.0, places=12)

    def test_zero_frequency_is_rejected(self):
        with self.assertRaises(ValueError):
            L.frequency_gap_product(0.0, 1.5)

    def test_negative_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            L.frequency_gap_product(12.0, -1.5)


class SusceptibilityTests(unittest.TestCase):
    def test_threshold_at_the_low_trend_anchor(self):
        self.assertAlmostEqual(L.breakdown_threshold_v(0.1), 30.0, places=9)

    def test_threshold_at_an_interior_trend_point(self):
        self.assertAlmostEqual(L.breakdown_threshold_v(1.0), 200.0, places=6)

    def test_threshold_at_the_high_trend_anchor(self):
        self.assertAlmostEqual(L.breakdown_threshold_v(100.0), 30000.0, places=3)

    def test_log_log_midpoint_is_the_geometric_mean(self):
        midpoint = math.sqrt(1.0 * 3.0)
        self.assertAlmostEqual(
            L.breakdown_threshold_v(midpoint), math.sqrt(200.0 * 600.0), places=6
        )

    def test_threshold_rises_with_the_frequency_gap_product(self):
        self.assertGreater(L.breakdown_threshold_v(20.0), L.breakdown_threshold_v(5.0))

    def test_product_below_the_trend_is_rejected(self):
        with self.assertRaises(ValueError):
            L.breakdown_threshold_v(0.05)

    def test_product_above_the_trend_is_rejected(self):
        with self.assertRaises(ValueError):
            L.breakdown_threshold_v(150.0)

    def test_zero_product_is_rejected(self):
        with self.assertRaises(ValueError):
            L.breakdown_threshold_v(0.0)


class VoltageTests(unittest.TestCase):
    def test_peak_voltage_matches_the_travelling_wave_relation(self):
        self.assertAlmostEqual(L.peak_voltage_from_power(50.0, 50.0), math.sqrt(5000.0), places=9)

    def test_voltage_scales_with_the_square_root_of_power(self):
        low = L.peak_voltage_from_power(100.0)
        high = L.peak_voltage_from_power(400.0)
        self.assertAlmostEqual(high / low, 2.0, places=9)

    def test_zero_power_is_rejected(self):
        with self.assertRaises(ValueError):
            L.peak_voltage_from_power(0.0)

    def test_zero_impedance_is_rejected(self):
        with self.assertRaises(ValueError):
            L.peak_voltage_from_power(100.0, 0.0)


class ExtremeEvaluationTests(unittest.TestCase):
    def test_nominal_extreme_holds_its_margin(self):
        result = _extreme(-30.0)
        self.assertTrue(result["compliant"])
        self.assertGreater(result["margin_db"], 6.0)

    def test_cold_extreme_has_the_smaller_gap(self):
        self.assertLess(_extreme(-30.0)["gap_mm"], _extreme(80.0)["gap_mm"])

    def test_cold_extreme_has_the_lower_breakdown_threshold(self):
        self.assertLess(_extreme(-30.0)["threshold_v"], _extreme(80.0)["threshold_v"])

    def test_margin_exactly_on_the_requirement_is_compliant(self):
        achieved = _extreme(80.0)["margin_db"]
        result = _extreme(80.0, required_db=achieved)
        self.assertTrue(result["compliant"])
        self.assertTrue(result["at_requirement"])

    def test_excessive_power_breaks_the_margin(self):
        result = _extreme(-30.0, power_w=500000.0)
        self.assertFalse(result["compliant"])
        self.assertLess(result["margin_db"], 0.0)

    def test_negative_required_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            _extreme(-30.0, required_db=-6.0)

    def test_zero_applied_power_is_rejected(self):
        with self.assertRaises(ValueError):
            _extreme(-30.0, power_w=0.0)


class WorstCaseTests(unittest.TestCase):
    def test_cold_extreme_is_the_worst_case_for_positive_expansion(self):
        worst = L.worst_case_extreme({"cold": _extreme(-30.0), "hot": _extreme(80.0)})
        self.assertEqual(worst["extreme"], "cold")

    def test_worst_case_reports_the_lower_margin(self):
        cold = _extreme(-30.0)
        hot = _extreme(80.0)
        worst = L.worst_case_extreme({"cold": cold, "hot": hot})
        self.assertAlmostEqual(worst["margin_db"], min(cold["margin_db"], hot["margin_db"]), places=12)

    def test_empty_evaluation_set_is_rejected(self):
        with self.assertRaises(ValueError):
            L.worst_case_extreme({})

    def test_duplicate_extreme_under_two_aliases_is_rejected(self):
        with self.assertRaises(ValueError):
            L.worst_case_extreme({"cold": _extreme(-30.0), "minimum": _extreme(-30.0)})

    def test_non_evaluation_payload_is_rejected(self):
        with self.assertRaises(ValueError):
            L.worst_case_extreme({"cold": 12.0})

    def test_uncategorized_extreme_label_is_rejected(self):
        with self.assertRaises(ValueError):
            L.worst_case_extreme({"ambient": _extreme(22.0)})


class SoakTests(unittest.TestCase):
    def test_long_soak_with_small_drift_is_stabilised(self):
        soak = L.evaluate_soak(90.0, 60.0, 1.5, 2.0)
        self.assertTrue(soak["stabilised"])

    def test_soak_exactly_on_the_requirement_is_sufficient(self):
        soak = L.evaluate_soak(60.0, 60.0, 1.0, 2.0)
        self.assertTrue(soak["soak_sufficient"])

    def test_drift_exactly_on_the_tolerance_is_within(self):
        soak = L.evaluate_soak(90.0, 60.0, 2.0, 2.0)
        self.assertTrue(soak["drift_within_tolerance"])

    def test_drift_carrying_representation_error_is_within(self):
        drift = 0.0
        for _ in range(20):
            drift += 0.1
        self.assertNotEqual(drift, 2.0)
        self.assertGreater(drift, 2.0)
        soak = L.evaluate_soak(90.0, 60.0, drift, 2.0)
        self.assertTrue(soak["drift_within_tolerance"])

    def test_short_soak_is_reported(self):
        soak = L.evaluate_soak(10.0, 60.0, 1.0, 2.0)
        self.assertFalse(soak["soak_sufficient"])
        self.assertFalse(soak["stabilised"])

    def test_excess_drift_is_reported(self):
        soak = L.evaluate_soak(90.0, 60.0, 8.0, 2.0)
        self.assertFalse(soak["drift_within_tolerance"])

    def test_negative_soak_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_soak(-1.0, 60.0, 1.0, 2.0)

    def test_zero_required_soak_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_soak(90.0, 0.0, 1.0, 2.0)

    def test_negative_drift_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_soak(90.0, 60.0, -1.0, 2.0)

    def test_zero_drift_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_soak(90.0, 60.0, 1.0, 0.0)


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.extremes = L.qualification_extremes(-20.0, 70.0, 10.0)

    def test_points_on_both_extremes_are_complete_coverage(self):
        result = L.evaluate_temperature_coverage([-30.0, 22.0, 80.0], self.extremes, 3.0)
        self.assertTrue(result["complete"])
        self.assertEqual(result["uncovered"], [])

    def test_deviation_exactly_on_the_tolerance_still_covers(self):
        result = L.evaluate_temperature_coverage([-33.0, 83.0], self.extremes, 3.0)
        self.assertTrue(result["complete"])

    def test_deviation_carrying_representation_error_still_covers(self):
        offset = 0.0
        for _ in range(30):
            offset += 0.1
        self.assertGreater(offset, 3.0)
        result = L.evaluate_temperature_coverage(
            [-30.0 - offset, 80.0 + offset], self.extremes, 3.0
        )
        self.assertTrue(result["complete"])

    def test_missing_hot_point_is_reported(self):
        result = L.evaluate_temperature_coverage([-30.0, 22.0], self.extremes, 3.0)
        self.assertEqual(result["uncovered"], ["hot"])
        self.assertFalse(result["complete"])

    def test_ambient_only_campaign_covers_neither_extreme(self):
        result = L.evaluate_temperature_coverage([22.0], self.extremes, 3.0)
        self.assertEqual(result["uncovered"], ["cold", "hot"])

    def test_string_instead_of_point_list_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_temperature_coverage("-30", self.extremes, 3.0)

    def test_none_point_list_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_temperature_coverage(None, self.extremes, 3.0)

    def test_empty_point_list_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_temperature_coverage([], self.extremes, 3.0)

    def test_zero_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_temperature_coverage([-30.0, 80.0], self.extremes, 0.0)

    def test_extremes_missing_a_key_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_temperature_coverage([-30.0], {"cold_c": -30.0}, 3.0)

    def test_extremes_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            L.evaluate_temperature_coverage([-30.0], [-30.0, 80.0], 3.0)


class CampaignTests(unittest.TestCase):
    def test_clean_campaign_reports_no_findings(self):
        result = L.assess_temperature_campaign(_good_campaign())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["compliant"])

    def test_clean_campaign_names_the_cold_extreme_as_worst_case(self):
        result = L.assess_temperature_campaign(_good_campaign())
        self.assertEqual(result["worst_case"]["extreme"], "cold")

    def test_excessive_power_breaks_both_extremes(self):
        campaign = _good_campaign()
        campaign["applied_power_w"] = 500000.0
        result = L.assess_temperature_campaign(campaign)
        self.assertTrue(any("cold extreme" in f for f in result["findings"]))
        self.assertTrue(any("hot extreme" in f for f in result["findings"]))

    def test_uncovered_extreme_is_a_finding(self):
        campaign = _good_campaign()
        campaign["tested_points_c"] = [22.0, 80.0]
        result = L.assess_temperature_campaign(campaign)
        self.assertIn("no tested point covers the cold extreme", result["findings"])

    def test_short_soak_is_a_finding(self):
        campaign = _good_campaign()
        campaign["soak_minutes"] = 5.0
        result = L.assess_temperature_campaign(campaign)
        self.assertTrue(any("soak duration" in f for f in result["findings"]))

    def test_excess_drift_is_a_finding(self):
        campaign = _good_campaign()
        campaign["measured_drift_k"] = 9.0
        result = L.assess_temperature_campaign(campaign)
        self.assertTrue(any("drift" in f for f in result["findings"]))

    def test_campaign_records_both_extreme_evaluations(self):
        result = L.assess_temperature_campaign(_good_campaign())
        self.assertEqual(sorted(result["evaluations"]), ["cold", "hot"])

    def test_missing_required_key_is_rejected(self):
        campaign = _good_campaign()
        campaign.pop("frequency_ghz")
        with self.assertRaises(ValueError):
            L.assess_temperature_campaign(campaign)

    def test_non_mapping_campaign_is_rejected(self):
        with self.assertRaises(ValueError):
            L.assess_temperature_campaign(["predicted_min_c", -20.0])

    def test_findings_are_sorted_and_stable(self):
        campaign = _good_campaign()
        campaign["soak_minutes"] = 5.0
        campaign["measured_drift_k"] = 9.0
        first = L.assess_temperature_campaign(campaign)["findings"]
        second = L.assess_temperature_campaign(campaign)["findings"]
        self.assertEqual(first, second)
        self.assertEqual(first, sorted(first))


if __name__ == "__main__":
    unittest.main()
