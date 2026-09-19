"""Contract tests for the ECSS-E-ST-31 temperature-range and limit logic."""

import unittest

from e31_temperature_ranges_allowable_limits_classification_logic import (
    CRYOGENIC_UPPER_K,
    HIGH_TEMPERATURE_LOWER_K,
    RANGE_CONVENTIONAL,
    RANGE_CRYOGENIC,
    RANGE_HIGH,
    TIER_SURVIVAL,
    assess_item,
    group_hardware_by_range,
    inflated_prediction,
    limit_margins,
    ranges_spanned,
    temperature_range_of,
    validate_item,
)


def item(name="avionics-box", **over):
    base = {
        "name": name,
        "predicted_min_k": 263.0,
        "predicted_max_k": 313.0,
        "uncertainty_cold_k": 5.0,
        "uncertainty_hot_k": 10.0,
        "allowable_min_k": 243.0,
        "allowable_max_k": 333.0,
    }
    base.update(over)
    return base


class RangePlacementTests(unittest.TestCase):
    def test_deep_cold_is_cryogenic(self):
        self.assertEqual(temperature_range_of(90.0), RANGE_CRYOGENIC)

    def test_room_temperature_is_conventional(self):
        self.assertEqual(temperature_range_of(293.0), RANGE_CONVENTIONAL)

    def test_very_hot_is_high_temperature(self):
        self.assertEqual(temperature_range_of(900.0), RANGE_HIGH)

    def test_cryogenic_boundary_itself_is_conventional(self):
        self.assertEqual(temperature_range_of(CRYOGENIC_UPPER_K), RANGE_CONVENTIONAL)

    def test_high_temperature_boundary_itself_is_conventional(self):
        self.assertEqual(
            temperature_range_of(HIGH_TEMPERATURE_LOWER_K), RANGE_CONVENTIONAL
        )

    def test_temperature_at_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            temperature_range_of(0.0)

    def test_boolean_temperature_rejected(self):
        with self.assertRaises(ValueError):
            temperature_range_of(True)


class RangeSpanTests(unittest.TestCase):
    def test_wholly_cold_interval_touches_one_range(self):
        self.assertEqual(ranges_spanned(120.0, 180.0), [RANGE_CRYOGENIC])

    def test_wholly_conventional_interval_touches_one_range(self):
        self.assertEqual(ranges_spanned(250.0, 320.0), [RANGE_CONVENTIONAL])

    def test_cold_survival_case_pulls_an_item_into_two_ranges(self):
        self.assertEqual(
            ranges_spanned(180.0, 300.0), [RANGE_CRYOGENIC, RANGE_CONVENTIONAL]
        )

    def test_hot_case_pulls_an_item_into_two_ranges(self):
        self.assertEqual(
            ranges_spanned(400.0, 600.0), [RANGE_CONVENTIONAL, RANGE_HIGH]
        )

    def test_full_sweep_touches_all_three_ranges(self):
        self.assertEqual(
            ranges_spanned(100.0, 900.0),
            [RANGE_CRYOGENIC, RANGE_CONVENTIONAL, RANGE_HIGH],
        )

    def test_degenerate_interval_on_the_boundary_is_conventional(self):
        self.assertEqual(
            ranges_spanned(CRYOGENIC_UPPER_K, CRYOGENIC_UPPER_K), [RANGE_CONVENTIONAL]
        )

    def test_inverted_interval_rejected(self):
        with self.assertRaises(ValueError):
            ranges_spanned(300.0, 250.0)


class ValidationTests(unittest.TestCase):
    def test_valid_item_is_normalised(self):
        checked = validate_item(item())
        self.assertEqual(checked["name"], "avionics-box")
        self.assertAlmostEqual(checked["uncertainty_hot_k"], 10.0, places=9)

    def test_uncertainties_default_to_zero(self):
        bare = item()
        del bare["uncertainty_cold_k"]
        del bare["uncertainty_hot_k"]
        checked = validate_item(bare)
        self.assertAlmostEqual(checked["uncertainty_cold_k"], 0.0, places=9)

    def test_negative_uncertainty_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(item(uncertainty_hot_k=-1.0))

    def test_inverted_prediction_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(item(predicted_min_k=320.0, predicted_max_k=300.0))

    def test_crossed_allowable_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(item(allowable_min_k=350.0, allowable_max_k=300.0))

    def test_unknown_limit_tier_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(item(limit_tier="qualification"))

    def test_unnamed_item_rejected(self):
        with self.assertRaises(ValueError):
            validate_item(item(name=""))


class InflationAndMarginTests(unittest.TestCase):
    def test_uncertainty_widens_the_prediction_in_both_directions(self):
        low, high = inflated_prediction(validate_item(item()))
        self.assertAlmostEqual(low, 258.0, places=9)
        self.assertAlmostEqual(high, 323.0, places=9)

    def test_asymmetric_uncertainty_is_kept_asymmetric(self):
        low, high = inflated_prediction(
            validate_item(item(uncertainty_cold_k=2.0, uncertainty_hot_k=20.0))
        )
        self.assertAlmostEqual(low, 261.0, places=9)
        self.assertAlmostEqual(high, 333.0, places=9)

    def test_margins_are_measured_on_the_inflated_prediction(self):
        margins = limit_margins(validate_item(item()))
        self.assertAlmostEqual(margins["cold_margin_k"], 15.0, places=9)
        self.assertAlmostEqual(margins["hot_margin_k"], 10.0, places=9)

    def test_raw_prediction_would_have_overstated_the_hot_margin(self):
        checked = validate_item(item())
        raw = checked["allowable_max_k"] - checked["predicted_max_k"]
        inflated = limit_margins(checked)["hot_margin_k"]
        self.assertAlmostEqual(raw - inflated, checked["uncertainty_hot_k"], places=9)

    def test_inflation_below_absolute_zero_rejected(self):
        checked = validate_item(
            item(predicted_min_k=4.0, predicted_max_k=6.0, uncertainty_cold_k=10.0,
                 allowable_min_k=1.0, allowable_max_k=20.0)
        )
        with self.assertRaises(ValueError):
            inflated_prediction(checked)


class AssessItemTests(unittest.TestCase):
    def test_compliant_item_reports_no_findings(self):
        record = assess_item(item())
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])
        self.assertEqual(record["ranges"], [RANGE_CONVENTIONAL])

    def test_hot_breach_is_detected_on_the_inflated_prediction(self):
        record = assess_item(item(uncertainty_hot_k=30.0))
        self.assertFalse(record["compliant"])
        self.assertAlmostEqual(record["hot_margin_k"], -10.0, places=9)

    def test_cold_breach_is_detected_on_the_inflated_prediction(self):
        record = assess_item(item(uncertainty_cold_k=30.0))
        self.assertFalse(record["compliant"])
        self.assertAlmostEqual(record["cold_margin_k"], -10.0, places=9)

    def test_exactly_zero_hot_margin_is_compliant_and_flagged(self):
        record = assess_item(item(uncertainty_hot_k=20.0))
        self.assertAlmostEqual(record["hot_margin_k"], 0.0, places=9)
        self.assertTrue(record["compliant"])
        self.assertTrue(record["margin_exhausted"])

    def test_cold_survival_case_earns_both_rule_sets(self):
        record = assess_item(
            item(predicted_min_k=190.0, uncertainty_cold_k=10.0,
                 allowable_min_k=150.0)
        )
        self.assertEqual(record["ranges"], [RANGE_CRYOGENIC, RANGE_CONVENTIONAL])
        self.assertTrue(any("both rule sets" in f for f in record["findings"]))

    def test_survival_tier_is_flagged(self):
        record = assess_item(item(limit_tier=TIER_SURVIVAL))
        self.assertTrue(any("survival limits" in f for f in record["findings"]))

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            assess_item(["name"])


class GroupingTests(unittest.TestCase):
    def _set(self):
        return [
            item("avionics-box"),
            item("cryo-detector", predicted_min_k=60.0, predicted_max_k=90.0,
                 uncertainty_cold_k=3.0, uncertainty_hot_k=3.0,
                 allowable_min_k=50.0, allowable_max_k=110.0),
            item("nozzle-skirt", predicted_min_k=300.0, predicted_max_k=900.0,
                 uncertainty_cold_k=10.0, uncertainty_hot_k=50.0,
                 allowable_min_k=250.0, allowable_max_k=1200.0),
        ]

    def test_counts_are_per_range_and_an_item_can_count_twice(self):
        result = group_hardware_by_range(self._set())
        self.assertEqual(result["counts"][RANGE_CRYOGENIC], 1)
        self.assertEqual(result["counts"][RANGE_CONVENTIONAL], 2)
        self.assertEqual(result["counts"][RANGE_HIGH], 1)

    def test_multi_range_item_is_named(self):
        result = group_hardware_by_range(self._set())
        self.assertEqual(result["multi_range"], ["nozzle-skirt"])

    def test_design_drivers_are_the_least_margin_items(self):
        result = group_hardware_by_range(self._set())
        self.assertEqual(result["hot_driver"], "avionics-box")
        self.assertAlmostEqual(result["hot_driver_margin_k"], 10.0, places=9)
        self.assertEqual(result["cold_driver"], "cryo-detector")
        self.assertAlmostEqual(result["cold_driver_margin_k"], 7.0, places=9)

    def test_a_breach_makes_the_whole_set_non_compliant(self):
        items = self._set()
        items[0]["uncertainty_hot_k"] = 40.0
        result = group_hardware_by_range(items)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["breaches"], ["avionics-box"])

    def test_clean_set_is_compliant_with_no_findings(self):
        result = group_hardware_by_range(self._set())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["exhausted"], [])

    def test_duplicate_item_name_rejected(self):
        with self.assertRaises(ValueError):
            group_hardware_by_range([item(), item()])

    def test_empty_item_list_rejected(self):
        with self.assertRaises(ValueError):
            group_hardware_by_range([])


if __name__ == "__main__":
    unittest.main()
