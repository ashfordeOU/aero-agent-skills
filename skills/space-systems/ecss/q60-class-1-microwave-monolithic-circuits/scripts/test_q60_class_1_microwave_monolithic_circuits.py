#!/usr/bin/env python3
"""Contract test for class 1 microwave monolithic circuit selection (offline)."""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q60_class_1_microwave_monolithic_circuits_logic import (  # noqa: E402
    BARE_DIE_ACTIVITIES,
    BASE_ACTIVITIES_BY_SOURCE,
    DEFAULT_MMIC_POLICY,
    DELIVERY_FORMS,
    FOUNDRY_PROCESSES,
    NOT_USABLE,
    SOURCE_CATEGORIES,
    USABLE_AS_PROCURED,
    USABLE_WITH_ACTIVITIES,
    assess_mmic_selection,
    band_coverage_fraction,
    channel_temperature_c,
    channel_temperature_margin_c,
    derating_findings,
    esd_handling_category,
    out_of_band_span_ghz,
    required_activities,
    rf_drive_ratio,
    thermal_acceleration_factor,
    validate_mmic_case,
    validate_mmic_policy,
)

CATALOGUE_CASE = {
    "foundry_process": "gaas-phemt",
    "source_category": "space-qualified-catalogue",
    "delivery_form": "hermetic-packaged",
    "operating_low_ghz": 8.0,
    "operating_high_ghz": 12.0,
    "characterized_low_ghz": 6.0,
    "characterized_high_ghz": 14.0,
    "baseplate_temperature_c": 60.0,
    "thermal_resistance_c_per_w": 20.0,
    "dissipated_power_w": 1.0,
    "applied_drive_w": 0.4,
    "rated_drive_w": 1.0,
    "esd_withstand_voltage_v": 1000.0,
}


def _case(**overrides):
    case = copy.deepcopy(CATALOGUE_CASE)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_round_trips(self):
        self.assertEqual(validate_mmic_policy(None), DEFAULT_MMIC_POLICY)

    def test_policy_override_is_merged(self):
        merged = validate_mmic_policy({"max_channel_temperature_c": 95.0})
        self.assertAlmostEqual(merged["max_channel_temperature_c"], 95.0, places=9)
        self.assertAlmostEqual(
            merged["max_rf_drive_ratio"],
            DEFAULT_MMIC_POLICY["max_rf_drive_ratio"],
            places=9,
        )

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_mmic_policy({"max_temp": 95.0})

    def test_drive_ratio_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_mmic_policy({"max_rf_drive_ratio": 1.2})

    def test_band_coverage_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_mmic_policy({"min_band_coverage": 1.5})

    def test_non_boolean_commercial_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_mmic_policy({"allow_commercial_foundry": "no"})


class BandTests(unittest.TestCase):
    def test_band_fully_inside_is_fully_covered(self):
        self.assertAlmostEqual(
            band_coverage_fraction(8.0, 12.0, 6.0, 14.0), 1.0, places=9
        )

    def test_half_covered_band_reports_one_half(self):
        self.assertAlmostEqual(
            band_coverage_fraction(8.0, 12.0, 8.0, 10.0), 0.5, places=9
        )

    def test_disjoint_band_reports_no_coverage(self):
        self.assertAlmostEqual(
            band_coverage_fraction(8.0, 12.0, 20.0, 24.0), 0.0, places=9
        )

    def test_fully_covered_band_has_no_outside_span(self):
        self.assertAlmostEqual(
            out_of_band_span_ghz(8.0, 12.0, 6.0, 14.0), 0.0, places=9
        )

    def test_partly_covered_band_reports_the_outside_span(self):
        self.assertAlmostEqual(
            out_of_band_span_ghz(8.0, 12.0, 8.0, 10.0), 2.0, places=9
        )

    def test_disjoint_band_is_wholly_outside(self):
        self.assertAlmostEqual(
            out_of_band_span_ghz(8.0, 12.0, 20.0, 24.0), 4.0, places=9
        )

    def test_inverted_operating_band_rejected(self):
        with self.assertRaises(ValueError):
            band_coverage_fraction(12.0, 8.0, 6.0, 14.0)

    def test_zero_width_characterized_band_rejected(self):
        with self.assertRaises(ValueError):
            band_coverage_fraction(8.0, 12.0, 10.0, 10.0)

    def test_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            band_coverage_fraction(-8.0, 12.0, 6.0, 14.0)


class ThermalTests(unittest.TestCase):
    def test_channel_temperature_adds_the_thermal_rise(self):
        self.assertAlmostEqual(
            channel_temperature_c(60.0, 20.0, 1.0), 80.0, places=9
        )

    def test_zero_dissipation_leaves_the_baseplate_temperature(self):
        self.assertAlmostEqual(
            channel_temperature_c(60.0, 20.0, 0.0), 60.0, places=9
        )

    def test_margin_is_the_distance_to_the_limit(self):
        self.assertAlmostEqual(
            channel_temperature_margin_c(80.0, 110.0), 30.0, places=9
        )

    def test_margin_is_negative_on_a_breach(self):
        self.assertAlmostEqual(
            channel_temperature_margin_c(120.0, 110.0), -10.0, places=9
        )

    def test_baseplate_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            channel_temperature_c(-300.0, 20.0, 1.0)

    def test_negative_thermal_resistance_rejected(self):
        with self.assertRaises(ValueError):
            channel_temperature_c(60.0, -20.0, 1.0)

    def test_negative_dissipation_rejected(self):
        with self.assertRaises(ValueError):
            channel_temperature_c(60.0, 20.0, -1.0)

    def test_acceleration_at_the_reference_is_unity(self):
        self.assertAlmostEqual(
            thermal_acceleration_factor(85.0, 85.0, 1.3), 1.0, places=9
        )

    def test_a_hotter_channel_accelerates_degradation(self):
        hot = thermal_acceleration_factor(150.0, 85.0, 1.3)
        self.assertGreater(hot, 10.0)

    def test_a_cooler_channel_decelerates_degradation(self):
        cool = thermal_acceleration_factor(40.0, 85.0, 1.3)
        self.assertLess(cool, 0.1)

    def test_non_positive_activation_energy_rejected(self):
        with self.assertRaises(ValueError):
            thermal_acceleration_factor(150.0, 85.0, 0.0)


class DriveTests(unittest.TestCase):
    def test_drive_ratio_is_applied_over_rated(self):
        self.assertAlmostEqual(rf_drive_ratio(0.4, 1.0), 0.4, places=9)

    def test_drive_ratio_at_rated_is_one(self):
        self.assertAlmostEqual(rf_drive_ratio(2.0, 2.0), 1.0, places=9)

    def test_zero_applied_drive_is_allowed(self):
        self.assertAlmostEqual(rf_drive_ratio(0.0, 1.0), 0.0, places=9)

    def test_zero_rated_drive_rejected(self):
        with self.assertRaises(ValueError):
            rf_drive_ratio(0.4, 0.0)

    def test_negative_applied_drive_rejected(self):
        with self.assertRaises(ValueError):
            rf_drive_ratio(-0.4, 1.0)


class SensitivityTests(unittest.TestCase):
    def test_very_sensitive_part_is_the_lowest_category(self):
        self.assertEqual(esd_handling_category(80.0), "esd-sensitivity-0a")

    def test_mid_sensitivity_part_is_categorized(self):
        self.assertEqual(esd_handling_category(600.0), "esd-sensitivity-1b")

    def test_robust_part_is_the_highest_category(self):
        self.assertEqual(
            esd_handling_category(9000.0), "esd-sensitivity-3b-or-above"
        )

    def test_non_positive_withstand_voltage_rejected(self):
        with self.assertRaises(ValueError):
            esd_handling_category(0.0)


class ActivityTests(unittest.TestCase):
    def test_catalogue_part_carries_only_lot_acceptance(self):
        self.assertEqual(
            required_activities("space-qualified-catalogue", "hermetic-packaged"),
            ("lot-acceptance-testing",),
        )

    def test_commercial_part_carries_radiation_evaluation(self):
        activities = required_activities("commercial-foundry", "hermetic-packaged")
        self.assertIn("radiation-evaluation", activities)

    def test_bare_die_adds_handling_and_attach_activities(self):
        activities = required_activities("space-qualified-catalogue", "bare-die")
        for activity in BARE_DIE_ACTIVITIES:
            self.assertIn(activity, activities)

    def test_sensitive_part_adds_reinforced_controls(self):
        activities = required_activities(
            "space-qualified-catalogue", "hermetic-packaged", 200.0
        )
        self.assertIn("reinforced-electrostatic-discharge-controls", activities)

    def test_robust_part_adds_no_reinforced_controls(self):
        activities = required_activities(
            "space-qualified-catalogue", "hermetic-packaged", 2000.0
        )
        self.assertNotIn("reinforced-electrostatic-discharge-controls", activities)

    def test_unknown_source_category_rejected(self):
        with self.assertRaises(ValueError):
            required_activities("surplus-stock", "hermetic-packaged")

    def test_unknown_delivery_form_rejected(self):
        with self.assertRaises(ValueError):
            required_activities("space-qualified-catalogue", "wafer-lot")

    def test_every_source_category_has_a_base_activity_set(self):
        for category in SOURCE_CATEGORIES:
            self.assertTrue(BASE_ACTIVITIES_BY_SOURCE[category])


class DeratingTests(unittest.TestCase):
    def test_clean_case_raises_no_derating_finding(self):
        result = derating_findings(CATALOGUE_CASE)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["band_ok"])
        self.assertTrue(result["thermal_ok"])
        self.assertTrue(result["drive_ok"])

    def test_out_of_band_use_is_a_finding(self):
        result = derating_findings(_case(characterized_high_ghz=10.0))
        self.assertFalse(result["band_ok"])
        self.assertAlmostEqual(result["out_of_band_span_ghz"], 2.0, places=9)

    def test_channel_exactly_on_the_limit_passes(self):
        result = derating_findings(
            _case(baseplate_temperature_c=90.0, thermal_resistance_c_per_w=20.0)
        )
        self.assertAlmostEqual(result["channel_temperature_c"], 110.0, places=9)
        self.assertTrue(result["thermal_ok"])

    def test_channel_over_the_limit_is_a_finding(self):
        result = derating_findings(_case(dissipated_power_w=3.0))
        self.assertFalse(result["thermal_ok"])
        self.assertLess(result["channel_temperature_margin_c"], 0.0)

    def test_drive_exactly_on_the_limit_passes(self):
        result = derating_findings(_case(applied_drive_w=0.8))
        self.assertAlmostEqual(result["rf_drive_ratio"], 0.8, places=9)
        self.assertTrue(result["drive_ok"])

    def test_drive_over_the_limit_is_a_finding(self):
        result = derating_findings(_case(applied_drive_w=0.95))
        self.assertFalse(result["drive_ok"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            derating_findings("gaas-phemt")


class SelectionTests(unittest.TestCase):
    def test_clean_catalogue_part_is_usable_as_procured(self):
        result = assess_mmic_selection(_case(esd_withstand_voltage_v=2000.0))
        self.assertEqual(result["verdict"], USABLE_AS_PROCURED)
        self.assertTrue(result["usable"])

    def test_bare_die_part_needs_additional_activities(self):
        result = assess_mmic_selection(
            _case(delivery_form="bare-die", esd_withstand_voltage_v=2000.0)
        )
        self.assertEqual(result["verdict"], USABLE_WITH_ACTIVITIES)
        self.assertTrue(result["activities_beyond_catalogue"])

    def test_commercial_part_needs_additional_activities(self):
        result = assess_mmic_selection(
            _case(source_category="commercial-foundry", esd_withstand_voltage_v=2000.0)
        )
        self.assertEqual(result["verdict"], USABLE_WITH_ACTIVITIES)
        self.assertIn("radiation-evaluation", result["required_activities"])

    def test_commercial_part_is_not_usable_when_policy_forbids_it(self):
        result = assess_mmic_selection(
            _case(source_category="commercial-foundry"),
            {"allow_commercial_foundry": False},
        )
        self.assertEqual(result["verdict"], NOT_USABLE)
        self.assertFalse(result["usable"])

    def test_out_of_band_application_is_not_usable(self):
        result = assess_mmic_selection(_case(characterized_high_ghz=10.0))
        self.assertEqual(result["verdict"], NOT_USABLE)

    def test_overheated_part_is_not_usable(self):
        result = assess_mmic_selection(_case(dissipated_power_w=4.0))
        self.assertEqual(result["verdict"], NOT_USABLE)
        self.assertTrue(result["findings"])

    def test_overdriven_part_is_not_usable(self):
        result = assess_mmic_selection(_case(applied_drive_w=0.99))
        self.assertEqual(result["verdict"], NOT_USABLE)

    def test_sensitivity_category_is_reported(self):
        result = assess_mmic_selection(_case(esd_withstand_voltage_v=200.0))
        self.assertEqual(result["esd_handling_category"], "esd-sensitivity-0b")

    def test_case_missing_a_field_rejected(self):
        case = _case()
        del case["rated_drive_w"]
        with self.assertRaises(ValueError):
            assess_mmic_selection(case)

    def test_unknown_foundry_process_rejected(self):
        with self.assertRaises(ValueError):
            assess_mmic_selection(_case(foundry_process="silicon-cmos"))

    def test_case_validation_accepts_the_reference_case(self):
        self.assertIs(validate_mmic_case(CATALOGUE_CASE), CATALOGUE_CASE)

    def test_every_delivery_form_is_routable(self):
        for form in DELIVERY_FORMS:
            result = assess_mmic_selection(
                _case(delivery_form=form, esd_withstand_voltage_v=2000.0)
            )
            self.assertTrue(result["usable"])

    def test_every_foundry_process_is_accepted(self):
        for process in FOUNDRY_PROCESSES:
            result = assess_mmic_selection(
                _case(foundry_process=process, esd_withstand_voltage_v=2000.0)
            )
            self.assertEqual(result["foundry_process"], process)


if __name__ == "__main__":
    unittest.main()
