"""Contract tests for the clause 6.6.5 lowest-class MMIC application logic."""

import unittest

from q6013_class_3_microwave_integrated_circuits_logic import (
    APPLICATION_VERDICTS,
    DEFAULT_DRIVE_DERATING,
    DEFAULT_LOT_SAMPLE_PERCENT,
    ENVELOPE_TOLERANCE,
    LOWEST_CLASS_CHANNEL_ALLOWANCE_K,
    MINIMUM_LOT_SAMPLE,
    MOISTURE_OBLIGATION,
    NON_HERMETIC_FORMS,
    PACKAGE_FORMS,
    TECHNOLOGY_CHANNEL_CEILING_C,
    allowed_baseplate,
    allowed_dissipation,
    applied_channel_ceiling,
    assess_mmic_application,
    channel_temperature,
    effective_dissipation,
    lot_sample_size,
    package_form,
    technology_ceiling,
    validate_identifier,
)


def part(**overrides):
    """Return a clean MMIC application record with overrides applied."""
    base = {
        "reference": "MMIC-1",
        "technology": "gaas-phemt",
        "package_form": "hermetic-ceramic",
        "rated_channel_c": 175.0,
        "baseplate_c": 65.0,
        "peak_dissipation_w": 5.0,
        "duty_cycle": 0.5,
        "thermal_resistance_k_per_w": 20.0,
        "rated_input_w": 2.0,
        "applied_input_w": 1.2,
        "lot_size": 100,
    }
    base.update(overrides)
    return base


class ValidateIdentifierTests(unittest.TestCase):
    def test_strips_surrounding_space(self):
        self.assertEqual(validate_identifier(" MMIC-1 ", "reference"), "MMIC-1")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("  ", "reference")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(4.2, "reference")


class ConstructionTests(unittest.TestCase):
    def test_known_technology_returns_its_ceiling(self):
        self.assertAlmostEqual(technology_ceiling("gaas-phemt"), 150.0, places=9)

    def test_technology_lookup_ignores_letter_case(self):
        self.assertAlmostEqual(technology_ceiling("GaN-HEMT"), 200.0, places=9)

    def test_unknown_technology_rejected(self):
        with self.assertRaises(ValueError):
            technology_ceiling("unobtainium-hemt")

    def test_known_package_form_is_returned(self):
        self.assertEqual(package_form("Hermetic-Metal"), "hermetic-metal")

    def test_unknown_package_form_rejected(self):
        with self.assertRaises(ValueError):
            package_form("shrinkwrap")

    def test_non_hermetic_forms_are_a_subset_of_the_recognised_forms(self):
        self.assertTrue(set(NON_HERMETIC_FORMS).issubset(set(PACKAGE_FORMS)))

    def test_every_ceiling_is_above_the_class_allowance(self):
        for value in TECHNOLOGY_CHANNEL_CEILING_C.values():
            self.assertGreater(value, LOWEST_CLASS_CHANNEL_ALLOWANCE_K)


class CeilingTests(unittest.TestCase):
    def test_technology_ceiling_governs_a_generously_rated_part(self):
        self.assertAlmostEqual(
            applied_channel_ceiling("gaas-phemt", 175.0), 130.0, places=9
        )

    def test_part_rating_governs_a_conservatively_rated_part(self):
        self.assertAlmostEqual(
            applied_channel_ceiling("gaas-phemt", 140.0), 120.0, places=9
        )

    def test_declared_allowance_overrides_the_default(self):
        self.assertAlmostEqual(
            applied_channel_ceiling("gan-hemt", 250.0, 50.0), 150.0, places=9
        )

    def test_allowance_swallowing_the_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            applied_channel_ceiling("sige-bicmos", 125.0, 130.0)

    def test_negative_allowance_rejected(self):
        with self.assertRaises(ValueError):
            applied_channel_ceiling("gaas-phemt", 175.0, -5.0)


class ThermalPathTests(unittest.TestCase):
    def test_duty_cycle_folds_the_peak_into_an_effective_dissipation(self):
        self.assertAlmostEqual(effective_dissipation(5.0, 0.5), 2.5, places=9)

    def test_continuous_operation_keeps_the_peak(self):
        self.assertAlmostEqual(effective_dissipation(5.0), 5.0, places=9)

    def test_duty_cycle_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            effective_dissipation(5.0, 1.4)

    def test_zero_duty_cycle_rejected(self):
        with self.assertRaises(ValueError):
            effective_dissipation(5.0, 0.0)

    def test_channel_rises_along_the_declared_path(self):
        self.assertAlmostEqual(channel_temperature(65.0, 2.5, 20.0), 115.0, places=9)

    def test_zero_thermal_resistance_rejected(self):
        with self.assertRaises(ValueError):
            channel_temperature(65.0, 2.5, 0.0)

    def test_allowed_dissipation_inverts_the_path(self):
        self.assertAlmostEqual(allowed_dissipation(130.0, 65.0, 20.0), 3.25, places=9)

    def test_allowed_dissipation_is_zero_above_the_ceiling(self):
        self.assertAlmostEqual(allowed_dissipation(130.0, 140.0, 20.0), 0.0, places=9)

    def test_allowed_baseplate_inverts_the_path(self):
        self.assertAlmostEqual(allowed_baseplate(130.0, 2.5, 20.0), 80.0, places=9)


class LotSampleTests(unittest.TestCase):
    def test_proportional_sample_of_a_large_lot(self):
        self.assertEqual(lot_sample_size(100), 5)

    def test_sample_rounds_up_to_the_next_whole_device(self):
        self.assertEqual(lot_sample_size(101), 6)

    def test_minimum_sample_floors_a_small_lot(self):
        self.assertEqual(lot_sample_size(20), MINIMUM_LOT_SAMPLE)

    def test_sample_never_exceeds_the_lot(self):
        self.assertEqual(lot_sample_size(2), 2)

    def test_declared_percent_overrides_the_default(self):
        self.assertEqual(lot_sample_size(100, 10), 10)

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            lot_sample_size(0)

    def test_percent_above_a_hundred_rejected(self):
        with self.assertRaises(ValueError):
            lot_sample_size(100, 140)

    def test_default_percent_is_a_sampling_share(self):
        self.assertLess(DEFAULT_LOT_SAMPLE_PERCENT, 100)


class AssessmentTests(unittest.TestCase):
    def test_clean_application_is_accepted(self):
        self.assertEqual(
            assess_mmic_application(part())["verdict"], "application-accepted"
        )

    def test_clean_application_reports_its_channel_temperature(self):
        self.assertAlmostEqual(
            assess_mmic_application(part())["channel_temperature_c"], 115.0, places=9
        )

    def test_clean_application_reports_its_channel_margin(self):
        self.assertAlmostEqual(
            assess_mmic_application(part())["channel_margin_k"], 15.0, places=9
        )

    def test_channel_landing_exactly_on_the_ceiling_stays_accepted(self):
        result = assess_mmic_application(part(thermal_resistance_k_per_w=26.0))
        self.assertAlmostEqual(result["channel_margin_k"], 0.0, places=9)

    def test_channel_landing_exactly_on_the_ceiling_is_within(self):
        result = assess_mmic_application(part(thermal_resistance_k_per_w=26.0))
        self.assertTrue(result["channel_within_ceiling"])

    def test_channel_above_the_ceiling_calls_for_less_stress(self):
        result = assess_mmic_application(part(thermal_resistance_k_per_w=40.0))
        self.assertEqual(result["verdict"], "reduce-applied-stress")

    def test_continuous_operation_can_push_the_part_over(self):
        result = assess_mmic_application(part(duty_cycle=1.0))
        self.assertEqual(result["verdict"], "reduce-applied-stress")

    def test_envelope_reports_the_dissipation_still_available(self):
        self.assertAlmostEqual(
            assess_mmic_application(part())["allowed_dissipation_w"], 3.25, places=9
        )

    def test_envelope_reports_the_baseplate_still_available(self):
        self.assertAlmostEqual(
            assess_mmic_application(part())["allowed_baseplate_c"], 80.0, places=9
        )

    def test_drive_cap_is_the_derated_rating(self):
        self.assertAlmostEqual(
            assess_mmic_application(part())["drive_cap_w"], 1.6, places=9
        )

    def test_drive_landing_exactly_on_the_cap_stays_accepted(self):
        result = assess_mmic_application(part(applied_input_w=1.6))
        self.assertTrue(result["drive_within_cap"])

    def test_drive_above_the_cap_calls_for_less_stress(self):
        result = assess_mmic_application(part(applied_input_w=1.9))
        self.assertEqual(result["verdict"], "reduce-applied-stress")

    def test_non_hermetic_package_carries_a_moisture_obligation(self):
        result = assess_mmic_application(part(package_form="plastic-overmoulded"))
        self.assertEqual(result["moisture_obligations"], (MOISTURE_OBLIGATION,))

    def test_non_hermetic_package_is_accepted_with_that_obligation(self):
        result = assess_mmic_application(part(package_form="plastic-overmoulded"))
        self.assertEqual(result["verdict"], "accepted-with-moisture-obligation")

    def test_humidity_control_already_in_place_clears_the_obligation(self):
        result = assess_mmic_application(
            part(package_form="bare-die-on-carrier", humidity_controlled=True)
        )
        self.assertEqual(result["verdict"], "application-accepted")

    def test_hermetic_package_carries_no_moisture_obligation(self):
        self.assertEqual(assess_mmic_application(part())["moisture_obligations"], ())

    def test_undeclared_technology_closes_the_assessment(self):
        result = assess_mmic_application(part(technology="unobtainium-hemt"))
        self.assertEqual(result["verdict"], "refuse-undeclared-construction")

    def test_undeclared_package_form_closes_the_assessment(self):
        result = assess_mmic_application(part(package_form="shrinkwrap"))
        self.assertEqual(result["verdict"], "refuse-undeclared-construction")

    def test_undeclared_construction_publishes_no_envelope(self):
        result = assess_mmic_application(part(technology="unobtainium-hemt"))
        self.assertIsNone(result["channel_temperature_c"])

    def test_undeclared_construction_outranks_an_overstressed_channel(self):
        result = assess_mmic_application(
            part(technology="unobtainium-hemt", thermal_resistance_k_per_w=40.0)
        )
        self.assertEqual(result["verdict"], "refuse-undeclared-construction")

    def test_overstress_outranks_a_moisture_obligation(self):
        result = assess_mmic_application(
            part(package_form="plastic-overmoulded", thermal_resistance_k_per_w=40.0)
        )
        self.assertEqual(result["verdict"], "reduce-applied-stress")

    def test_lot_sample_is_reported_with_the_verdict(self):
        self.assertEqual(assess_mmic_application(part())["lot_sample_size"], 5)

    def test_findings_are_ordered_by_severity(self):
        result = assess_mmic_application(
            part(package_form="plastic-overmoulded", applied_input_w=1.9)
        )
        severities = [item["severity"] for item in result["findings"]]
        self.assertEqual(severities, sorted(severities))

    def test_missing_lot_size_rejected(self):
        broken = part()
        del broken["lot_size"]
        with self.assertRaises(ValueError):
            assess_mmic_application(broken)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_mmic_application(["MMIC-1"])

    def test_non_numeric_rated_channel_rejected(self):
        with self.assertRaises(ValueError):
            assess_mmic_application(part(rated_channel_c="hot"))

    def test_non_boolean_humidity_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_mmic_application(
                part(package_form="plastic-overmoulded", humidity_controlled="yes")
            )

    def test_verdict_is_drawn_from_the_published_set(self):
        self.assertIn(
            assess_mmic_application(part())["verdict"], APPLICATION_VERDICTS
        )

    def test_default_drive_derating_is_a_fraction(self):
        self.assertLess(DEFAULT_DRIVE_DERATING, 1.0)

    def test_tolerance_is_representation_sized(self):
        self.assertLess(ENVELOPE_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
