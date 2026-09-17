#!/usr/bin/env python3
"""Contract test for class 2 microwave monolithic circuit selection (offline)."""

import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q60_class_2_microwave_monolithic_circuits_logic import (  # noqa: E402
    ADMISSIBLE_AS_PROCURED,
    ADMISSIBLE_WITH_EVIDENCE,
    APPLICATION_NONCONFORMING,
    BARE_DIE_EVIDENCE,
    DEFAULT_CLASS2_MMIC_POLICY,
    DELIVERY_FORMS,
    EVIDENCE_BY_SOURCE_ROUTE,
    MMIC_TECHNOLOGIES,
    NOT_ADMISSIBLE,
    PLASTIC_ENCAPSULATED_EVIDENCE,
    SOURCE_ROUTES,
    application_findings,
    assess_class2_mmic,
    band_guard_margins_ghz,
    compensating_evidence,
    drive_utilisation,
    esd_control_level,
    junction_temperature_c,
    junction_temperature_margin_c,
    output_backoff_db,
    validate_class2_mmic_case,
    validate_class2_mmic_policy,
)

CATALOGUE_CASE = {
    "technology": "gaas-phemt",
    "source_route": "space-qualified-catalogue",
    "delivery_form": "hermetic-packaged",
    "operating_low_ghz": 8.0,
    "operating_high_ghz": 12.0,
    "characterized_low_ghz": 6.0,
    "characterized_high_ghz": 14.0,
    "baseplate_temperature_c": 55.0,
    "junction_to_case_c_per_w": 20.0,
    "case_to_baseplate_c_per_w": 5.0,
    "dissipated_power_w": 2.0,
    "applied_drive_w": 0.5,
    "rated_drive_w": 1.0,
    "compression_point_w": 2.0,
    "esd_withstand_voltage_v": 1000.0,
}


def _case(**overrides):
    case = copy.deepcopy(CATALOGUE_CASE)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_round_trips(self):
        self.assertEqual(validate_class2_mmic_policy(None), DEFAULT_CLASS2_MMIC_POLICY)

    def test_policy_override_is_merged(self):
        merged = validate_class2_mmic_policy({"max_junction_temperature_c": 110.0})
        self.assertAlmostEqual(merged["max_junction_temperature_c"], 110.0, places=9)
        self.assertAlmostEqual(
            merged["max_drive_utilisation"],
            DEFAULT_CLASS2_MMIC_POLICY["max_drive_utilisation"],
            places=9,
        )

    def test_unknown_policy_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_class2_mmic_policy({"max_junction_temp": 110.0})

    def test_drive_utilisation_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_class2_mmic_policy({"max_drive_utilisation": 1.4})

    def test_negative_band_guard_rejected(self):
        with self.assertRaises(ValueError):
            validate_class2_mmic_policy({"min_band_guard_ghz": -0.5})

    def test_non_boolean_catalogue_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_class2_mmic_policy({"allow_commercial_catalogue": "no"})

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_class2_mmic_policy("default")


class BandGuardTests(unittest.TestCase):
    def test_band_inside_characterization_has_positive_guards(self):
        guards = band_guard_margins_ghz(8.0, 12.0, 6.0, 14.0)
        self.assertAlmostEqual(guards["lower_guard_ghz"], 2.0, places=9)
        self.assertAlmostEqual(guards["upper_guard_ghz"], 2.0, places=9)

    def test_band_on_both_edges_has_zero_guard(self):
        guards = band_guard_margins_ghz(8.0, 12.0, 8.0, 12.0)
        self.assertAlmostEqual(guards["narrowest_guard_ghz"], 0.0, places=9)
        self.assertAlmostEqual(guards["uncharacterized_span_ghz"], 0.0, places=9)

    def test_band_over_the_top_edge_reports_the_uncharacterized_span(self):
        guards = band_guard_margins_ghz(8.0, 12.0, 6.0, 10.5)
        self.assertAlmostEqual(guards["upper_guard_ghz"], -1.5, places=9)
        self.assertAlmostEqual(guards["uncharacterized_span_ghz"], 1.5, places=9)

    def test_band_over_both_edges_sums_both_spans(self):
        guards = band_guard_margins_ghz(6.0, 14.0, 7.0, 13.0)
        self.assertAlmostEqual(guards["uncharacterized_span_ghz"], 2.0, places=9)

    def test_narrowest_guard_is_the_tighter_edge(self):
        guards = band_guard_margins_ghz(8.0, 12.0, 7.5, 14.0)
        self.assertAlmostEqual(guards["narrowest_guard_ghz"], 0.5, places=9)

    def test_inverted_operating_band_rejected(self):
        with self.assertRaises(ValueError):
            band_guard_margins_ghz(12.0, 8.0, 6.0, 14.0)

    def test_zero_width_characterized_band_rejected(self):
        with self.assertRaises(ValueError):
            band_guard_margins_ghz(8.0, 12.0, 10.0, 10.0)

    def test_negative_frequency_rejected(self):
        with self.assertRaises(ValueError):
            band_guard_margins_ghz(-8.0, 12.0, 6.0, 14.0)


class ThermalTests(unittest.TestCase):
    def test_junction_adds_both_resistances(self):
        self.assertAlmostEqual(
            junction_temperature_c(55.0, 20.0, 5.0, 2.0), 105.0, places=9
        )

    def test_zero_dissipation_leaves_the_baseplate_temperature(self):
        self.assertAlmostEqual(
            junction_temperature_c(55.0, 20.0, 5.0, 0.0), 55.0, places=9
        )

    def test_interface_resistance_moves_the_junction(self):
        without = junction_temperature_c(55.0, 20.0, 0.0, 2.0)
        with_interface = junction_temperature_c(55.0, 20.0, 5.0, 2.0)
        self.assertAlmostEqual(with_interface - without, 10.0, places=9)

    def test_margin_is_the_distance_to_the_limit(self):
        self.assertAlmostEqual(
            junction_temperature_margin_c(105.0, 125.0), 20.0, places=9
        )

    def test_margin_is_negative_on_a_breach(self):
        self.assertAlmostEqual(
            junction_temperature_margin_c(140.0, 125.0), -15.0, places=9
        )

    def test_baseplate_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(-300.0, 20.0, 5.0, 2.0)

    def test_negative_interface_resistance_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(55.0, 20.0, -5.0, 2.0)

    def test_negative_dissipation_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(55.0, 20.0, 5.0, -2.0)


class DriveTests(unittest.TestCase):
    def test_utilisation_is_applied_over_rated(self):
        self.assertAlmostEqual(drive_utilisation(0.5, 1.0), 0.5, places=9)

    def test_utilisation_at_rated_is_one(self):
        self.assertAlmostEqual(drive_utilisation(2.0, 2.0), 1.0, places=9)

    def test_zero_applied_drive_is_allowed(self):
        self.assertAlmostEqual(drive_utilisation(0.0, 1.0), 0.0, places=9)

    def test_zero_rated_drive_rejected(self):
        with self.assertRaises(ValueError):
            drive_utilisation(0.5, 0.0)

    def test_negative_applied_drive_rejected(self):
        with self.assertRaises(ValueError):
            drive_utilisation(-0.5, 1.0)

    def test_backoff_at_the_compression_point_is_zero(self):
        self.assertAlmostEqual(output_backoff_db(1.0, 1.0), 0.0, places=9)

    def test_a_decade_below_compression_is_ten_decibels(self):
        self.assertAlmostEqual(output_backoff_db(0.1, 1.0), 10.0, places=9)

    def test_running_above_compression_is_a_negative_backoff(self):
        self.assertAlmostEqual(output_backoff_db(10.0, 1.0), -10.0, places=9)

    def test_zero_applied_drive_has_no_backoff_defined(self):
        with self.assertRaises(ValueError):
            output_backoff_db(0.0, 1.0)

    def test_negative_compression_point_rejected(self):
        with self.assertRaises(ValueError):
            output_backoff_db(0.5, -2.0)


class SensitivityTests(unittest.TestCase):
    def test_very_sensitive_die_is_the_lowest_control_level(self):
        self.assertEqual(esd_control_level(80.0), "esd-control-level-0a")

    def test_mid_sensitivity_die_is_grouped(self):
        self.assertEqual(esd_control_level(600.0), "esd-control-level-1b")

    def test_robust_part_is_the_highest_control_level(self):
        self.assertEqual(
            esd_control_level(9000.0), "esd-control-level-3b-or-above"
        )

    def test_non_positive_withstand_voltage_rejected(self):
        with self.assertRaises(ValueError):
            esd_control_level(0.0)


class EvidenceTests(unittest.TestCase):
    def test_catalogue_part_carries_only_lot_acceptance(self):
        self.assertEqual(
            compensating_evidence("space-qualified-catalogue", "hermetic-packaged"),
            ("lot-acceptance-testing",),
        )

    def test_commercial_catalogue_route_carries_upscreening(self):
        evidence = compensating_evidence("commercial-catalogue", "hermetic-packaged")
        self.assertIn("upscreening-programme", evidence)
        self.assertIn("radiation-evaluation", evidence)

    def test_bare_die_adds_the_package_evidence(self):
        evidence = compensating_evidence("space-qualified-catalogue", "bare-die")
        for item in BARE_DIE_EVIDENCE:
            self.assertIn(item, evidence)

    def test_plastic_body_adds_moisture_evidence(self):
        evidence = compensating_evidence(
            "space-qualified-catalogue", "plastic-encapsulated"
        )
        for item in PLASTIC_ENCAPSULATED_EVIDENCE:
            self.assertIn(item, evidence)

    def test_sensitive_die_adds_reinforced_controls(self):
        evidence = compensating_evidence(
            "space-qualified-catalogue", "hermetic-packaged", 200.0
        )
        self.assertIn("reinforced-electrostatic-discharge-controls", evidence)

    def test_robust_die_adds_no_reinforced_controls(self):
        evidence = compensating_evidence(
            "space-qualified-catalogue", "hermetic-packaged", 2000.0
        )
        self.assertNotIn("reinforced-electrostatic-discharge-controls", evidence)

    def test_unknown_source_route_rejected(self):
        with self.assertRaises(ValueError):
            compensating_evidence("surplus-stock", "hermetic-packaged")

    def test_unknown_delivery_form_rejected(self):
        with self.assertRaises(ValueError):
            compensating_evidence("space-qualified-catalogue", "wafer-lot")

    def test_every_source_route_has_an_evidence_set(self):
        for route in SOURCE_ROUTES:
            self.assertTrue(EVIDENCE_BY_SOURCE_ROUTE[route])


class ApplicationTests(unittest.TestCase):
    def test_clean_case_raises_no_finding(self):
        result = application_findings(CATALOGUE_CASE)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["band_ok"])
        self.assertTrue(result["thermal_ok"])
        self.assertTrue(result["drive_ok"])
        self.assertTrue(result["backoff_ok"])

    def test_uncharacterized_use_is_a_finding(self):
        result = application_findings(_case(characterized_high_ghz=10.5))
        self.assertFalse(result["band_ok"])
        self.assertAlmostEqual(result["uncharacterized_span_ghz"], 1.5, places=9)

    def test_junction_exactly_on_the_limit_passes(self):
        result = application_findings(_case(baseplate_temperature_c=75.0))
        self.assertAlmostEqual(result["junction_temperature_c"], 125.0, places=9)
        self.assertTrue(result["thermal_ok"])

    def test_junction_over_the_limit_is_a_finding(self):
        result = application_findings(_case(dissipated_power_w=4.0))
        self.assertFalse(result["thermal_ok"])
        self.assertLess(result["junction_temperature_margin_c"], 0.0)

    def test_drive_exactly_on_the_utilisation_limit_passes(self):
        result = application_findings(_case(applied_drive_w=0.85))
        self.assertAlmostEqual(result["drive_utilisation"], 0.85, places=9)
        self.assertTrue(result["drive_ok"])

    def test_drive_over_the_utilisation_limit_is_a_finding(self):
        result = application_findings(_case(applied_drive_w=0.95))
        self.assertFalse(result["drive_ok"])

    def test_backoff_exactly_on_the_floor_passes(self):
        compression = 0.5 * 10.0 ** 0.1
        result = application_findings(_case(compression_point_w=compression))
        self.assertAlmostEqual(result["output_backoff_db"], 1.0, places=9)
        self.assertTrue(result["backoff_ok"])

    def test_stage_in_compression_is_a_finding(self):
        result = application_findings(_case(compression_point_w=0.55))
        self.assertFalse(result["backoff_ok"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            application_findings("gan-hemt")


class DispositionTests(unittest.TestCase):
    def test_clean_catalogue_part_is_admissible_as_procured(self):
        result = assess_class2_mmic(_case(esd_withstand_voltage_v=2000.0))
        self.assertEqual(result["disposition"], ADMISSIBLE_AS_PROCURED)
        self.assertTrue(result["admissible"])

    def test_bare_die_needs_compensating_evidence(self):
        result = assess_class2_mmic(
            _case(delivery_form="bare-die", esd_withstand_voltage_v=2000.0)
        )
        self.assertEqual(result["disposition"], ADMISSIBLE_WITH_EVIDENCE)
        self.assertTrue(result["evidence_beyond_catalogue"])

    def test_commercial_catalogue_part_needs_compensating_evidence(self):
        result = assess_class2_mmic(
            _case(source_route="commercial-catalogue", esd_withstand_voltage_v=2000.0)
        )
        self.assertEqual(result["disposition"], ADMISSIBLE_WITH_EVIDENCE)
        self.assertIn("upscreening-programme", result["compensating_evidence"])

    def test_policy_may_bar_the_commercial_catalogue_route(self):
        result = assess_class2_mmic(
            _case(source_route="commercial-catalogue"),
            {"allow_commercial_catalogue": False},
        )
        self.assertEqual(result["disposition"], NOT_ADMISSIBLE)
        self.assertFalse(result["admissible"])

    def test_uncharacterized_band_makes_the_application_nonconforming(self):
        result = assess_class2_mmic(_case(characterized_high_ghz=10.5))
        self.assertEqual(result["disposition"], APPLICATION_NONCONFORMING)
        self.assertFalse(result["admissible"])

    def test_overheated_die_makes_the_application_nonconforming(self):
        result = assess_class2_mmic(_case(dissipated_power_w=5.0))
        self.assertEqual(result["disposition"], APPLICATION_NONCONFORMING)
        self.assertTrue(result["findings"])

    def test_overdriven_stage_makes_the_application_nonconforming(self):
        result = assess_class2_mmic(_case(applied_drive_w=0.99))
        self.assertEqual(result["disposition"], APPLICATION_NONCONFORMING)

    def test_a_barred_route_outranks_an_application_finding(self):
        result = assess_class2_mmic(
            _case(source_route="commercial-catalogue", dissipated_power_w=5.0),
            {"allow_commercial_catalogue": False},
        )
        self.assertEqual(result["disposition"], NOT_ADMISSIBLE)

    def test_control_level_is_reported(self):
        result = assess_class2_mmic(_case(esd_withstand_voltage_v=200.0))
        self.assertEqual(result["esd_control_level"], "esd-control-level-0b")

    def test_case_missing_a_field_rejected(self):
        case = _case()
        del case["compression_point_w"]
        with self.assertRaises(ValueError):
            assess_class2_mmic(case)

    def test_unknown_technology_rejected(self):
        with self.assertRaises(ValueError):
            assess_class2_mmic(_case(technology="silicon-cmos"))

    def test_case_validation_accepts_the_reference_case(self):
        self.assertIs(validate_class2_mmic_case(CATALOGUE_CASE), CATALOGUE_CASE)

    def test_every_delivery_form_is_routable(self):
        for form in DELIVERY_FORMS:
            result = assess_class2_mmic(
                _case(delivery_form=form, esd_withstand_voltage_v=2000.0)
            )
            self.assertTrue(result["admissible"])

    def test_every_technology_is_accepted(self):
        for technology in MMIC_TECHNOLOGIES:
            result = assess_class2_mmic(
                _case(technology=technology, esd_withstand_voltage_v=2000.0)
            )
            self.assertEqual(result["technology"], technology)


if __name__ == "__main__":
    unittest.main()
