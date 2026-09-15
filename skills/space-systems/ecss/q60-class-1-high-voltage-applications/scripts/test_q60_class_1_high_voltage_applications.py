"""Contract tests for the clause 4.6.7 high voltage and high power microwave logic."""

import unittest

from q60_class_1_high_voltage_applications_logic import (
    BASELINE_PROVISIONS,
    BOUND_TOLERANCE,
    CORONA_PRESSURE_WINDOW_PA,
    HIGH_MICROWAVE_POWER_THRESHOLD_W,
    HIGH_VOLTAGE_THRESHOLD_V,
    MULTIPACTION_FD_LIMIT_GHZ_MM,
    PROVISIONS,
    VOLTAGE_UTILISATION_LIMIT,
    application_admissibility,
    application_disposition,
    assess_class_1_high_voltage_application,
    design_findings,
    multipaction_fd_product,
    multipaction_susceptible,
    ordered_provisions,
    outstanding_provisions,
    pressure_gap_product,
    provision_coverage,
    required_provisions,
    voltage_utilisation,
    voltage_utilisation_acceptable,
    within_corona_window,
)


def _app(**over):
    base = {
        "part_id": "HV-6047-A",
        "rated_voltage_v": 400.0,
        "working_voltage_v": 150.0,
        "electrode_gap_mm": 3.0,
        "operating_pressure_pa": 1.0e-5,
        "encapsulated": True,
        "vented": True,
        "microwave_peak_power_w": 0.0,
        "microwave_frequency_ghz": 0.0,
        "provisions_closed": [],
    }
    base.update(over)
    return base


class AdmissibilityTests(unittest.TestCase):
    def test_a_sound_application_is_admissible(self):
        self.assertEqual(application_admissibility(_app()), [])

    def test_a_part_without_an_identity_is_stopped(self):
        reasons = application_admissibility(_app(part_id="   "))
        self.assertIn("part-identity-not-traceable", reasons)

    def test_a_part_without_a_rating_is_stopped(self):
        reasons = application_admissibility(_app(rated_voltage_v=0.0))
        self.assertIn("rated-voltage-not-stated", reasons)

    def test_a_missing_electrode_gap_is_stopped(self):
        reasons = application_admissibility(_app(electrode_gap_mm=None))
        self.assertIn("electrode-gap-not-stated", reasons)

    def test_working_voltage_above_the_rating_is_stopped(self):
        reasons = application_admissibility(_app(working_voltage_v=500.0))
        self.assertIn("working-voltage-exceeds-part-rating", reasons)

    def test_working_voltage_exactly_at_the_rating_is_not_stopped(self):
        reasons = application_admissibility(_app(working_voltage_v=400.0))
        self.assertNotIn("working-voltage-exceeds-part-rating", reasons)

    def test_reasons_accumulate(self):
        reasons = application_admissibility(
            _app(part_id="", rated_voltage_v=-1.0, electrode_gap_mm=0.0))
        self.assertEqual(len(reasons), 3)

    def test_application_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            application_admissibility(["HV-6047-A"])


class StressMeasurementTests(unittest.TestCase):
    def test_utilisation_is_the_working_over_rated_ratio(self):
        self.assertAlmostEqual(voltage_utilisation(150.0, 400.0), 0.375, places=9)

    def test_utilisation_exactly_on_the_limit_is_acceptable(self):
        ratio = voltage_utilisation(200.0, 400.0)
        self.assertAlmostEqual(ratio, VOLTAGE_UTILISATION_LIMIT, places=9)
        self.assertTrue(voltage_utilisation_acceptable(ratio))

    def test_utilisation_well_past_the_limit_is_not_acceptable(self):
        self.assertFalse(voltage_utilisation_acceptable(voltage_utilisation(380.0, 400.0)))

    def test_a_zero_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            voltage_utilisation(150.0, 0.0)

    def test_a_non_numeric_working_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            voltage_utilisation("150", 400.0)

    def test_the_pressure_gap_product_converts_millimetre_to_metre(self):
        self.assertAlmostEqual(pressure_gap_product(1000.0, 2.0), 2.0, places=9)

    def test_a_negative_gap_is_rejected(self):
        with self.assertRaises(ValueError):
            pressure_gap_product(1000.0, -2.0)


class CoronaWindowTests(unittest.TestCase):
    def test_a_vacuum_ambient_sits_outside_the_window(self):
        self.assertFalse(within_corona_window(1.0e-5))

    def test_a_mid_ascent_ambient_sits_inside_the_window(self):
        self.assertTrue(within_corona_window(500.0))

    def test_both_window_bounds_belong_to_the_window(self):
        low, high = CORONA_PRESSURE_WINDOW_PA
        self.assertTrue(within_corona_window(low))
        self.assertTrue(within_corona_window(high))

    def test_sea_level_ambient_sits_above_the_window(self):
        self.assertFalse(within_corona_window(101325.0))

    def test_a_non_numeric_pressure_is_rejected(self):
        with self.assertRaises(ValueError):
            within_corona_window(None)


class MultipactionTests(unittest.TestCase):
    def test_the_fd_product_is_frequency_times_gap(self):
        self.assertAlmostEqual(multipaction_fd_product(2.0, 5.0), 10.0, places=9)

    def test_a_product_exactly_on_the_bound_is_susceptible(self):
        product = multipaction_fd_product(2.0, 5.0)
        self.assertAlmostEqual(product, MULTIPACTION_FD_LIMIT_GHZ_MM, places=9)
        self.assertTrue(multipaction_susceptible(product, 50.0))

    def test_a_product_well_above_the_bound_is_not_susceptible(self):
        self.assertFalse(multipaction_susceptible(120.0, 50.0))

    def test_a_low_power_gap_is_not_susceptible(self):
        self.assertFalse(multipaction_susceptible(4.0, 0.5))

    def test_power_exactly_on_the_threshold_still_counts(self):
        self.assertTrue(
            multipaction_susceptible(4.0, HIGH_MICROWAVE_POWER_THRESHOLD_W))

    def test_an_unpowered_direct_current_gap_is_not_susceptible(self):
        self.assertFalse(multipaction_susceptible(0.0, 50.0))

    def test_a_non_numeric_power_is_rejected(self):
        with self.assertRaises(ValueError):
            multipaction_susceptible(4.0, "50")


class FindingTests(unittest.TestCase):
    def test_a_well_derated_sealed_vented_part_raises_nothing(self):
        self.assertEqual(design_findings(_app()), [])

    def test_over_utilisation_is_reported(self):
        findings = design_findings(_app(working_voltage_v=380.0))
        self.assertIn("voltage-utilisation-above-class-1-limit", findings)

    def test_an_unencapsulated_gap_in_the_window_is_reported(self):
        findings = design_findings(_app(operating_pressure_pa=500.0,
                                        encapsulated=False, vented=False))
        self.assertIn("unencapsulated-gap-inside-corona-window", findings)

    def test_a_sealed_cavity_without_a_vent_is_reported(self):
        findings = design_findings(_app(vented=False))
        self.assertIn("sealed-cavity-without-vent-path", findings)

    def test_a_non_boolean_encapsulation_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            design_findings(_app(encapsulated="yes"))


class ProvisionTests(unittest.TestCase):
    def test_the_baseline_provisions_are_always_owed(self):
        owed = required_provisions(_app())
        self.assertTrue(set(BASELINE_PROVISIONS) <= set(owed))

    def test_a_high_working_voltage_adds_the_partial_discharge_measurement(self):
        owed = required_provisions(_app(working_voltage_v=HIGH_VOLTAGE_THRESHOLD_V))
        self.assertIn("partial-discharge-measurement", owed)

    def test_a_low_voltage_application_does_not(self):
        owed = required_provisions(_app(working_voltage_v=24.0))
        self.assertNotIn("partial-discharge-measurement", owed)

    def test_an_ambient_inside_the_window_adds_corona_verification(self):
        owed = required_provisions(_app(operating_pressure_pa=500.0))
        self.assertIn("corona-onset-verification", owed)

    def test_an_unvented_part_adds_the_venting_verification(self):
        owed = required_provisions(_app(vented=False))
        self.assertIn("encapsulation-and-venting-verification", owed)

    def test_microwave_power_adds_the_power_handling_verification(self):
        owed = required_provisions(_app(microwave_peak_power_w=200.0,
                                        microwave_frequency_ghz=30.0))
        self.assertIn("microwave-power-handling-verification", owed)

    def test_a_susceptible_powered_gap_adds_the_multipaction_analysis(self):
        owed = required_provisions(_app(microwave_peak_power_w=200.0,
                                        microwave_frequency_ghz=2.0,
                                        electrode_gap_mm=3.0))
        self.assertIn("multipaction-analysis", owed)

    def test_a_wide_powered_gap_does_not_add_it(self):
        owed = required_provisions(_app(microwave_peak_power_w=200.0,
                                        microwave_frequency_ghz=30.0,
                                        electrode_gap_mm=20.0))
        self.assertNotIn("multipaction-analysis", owed)

    def test_the_owed_provisions_come_back_in_performance_order(self):
        owed = required_provisions(_app(working_voltage_v=300.0,
                                        operating_pressure_pa=500.0))
        indexes = [PROVISIONS.index(name) for name in owed]
        self.assertEqual(indexes, sorted(indexes))

    def test_provision_names_compare_case_insensitively(self):
        self.assertEqual(ordered_provisions(["HIGH-VOLTAGE-DESIGN-REVIEW"]),
                         ["high-voltage-design-review"])

    def test_an_unknown_provision_is_rejected(self):
        with self.assertRaises(ValueError):
            ordered_provisions(["gold-plating-inspection"])

    def test_a_repeated_provision_is_rejected(self):
        with self.assertRaises(ValueError):
            ordered_provisions(["high-voltage-design-review",
                                "high-voltage-design-review"])


class CoverageTests(unittest.TestCase):
    def test_nothing_closed_leaves_everything_outstanding(self):
        owed = required_provisions(_app())
        self.assertEqual(outstanding_provisions(owed, []), owed)

    def test_closing_a_provision_removes_it(self):
        owed = required_provisions(_app())
        remaining = outstanding_provisions(owed, ["high-voltage-design-review"])
        self.assertNotIn("high-voltage-design-review", remaining)

    def test_closing_a_provision_not_owed_changes_nothing(self):
        owed = required_provisions(_app(working_voltage_v=24.0))
        remaining = outstanding_provisions(owed, ["multipaction-analysis"])
        self.assertEqual(remaining, owed)

    def test_an_untouched_plan_reads_zero_coverage(self):
        owed = required_provisions(_app())
        self.assertAlmostEqual(provision_coverage(owed, []), 0.0, places=9)

    def test_a_fully_closed_plan_reads_one(self):
        owed = required_provisions(_app())
        self.assertAlmostEqual(provision_coverage(owed, owed), 1.0, places=9)

    def test_an_empty_owed_set_is_rejected(self):
        with self.assertRaises(ValueError):
            provision_coverage([], [])

    def test_the_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)


class DispositionTests(unittest.TestCase):
    def test_inadmissibility_overrides_everything(self):
        self.assertEqual(
            application_disposition(["rated-voltage-not-stated"], [], []),
            "application-not-admissible")

    def test_a_finding_outranks_outstanding_work(self):
        self.assertEqual(
            application_disposition([], ["sealed-cavity-without-vent-path"],
                                    ["corona-onset-verification"]),
            "provisions-nonconforming")

    def test_outstanding_work_reads_as_outstanding(self):
        self.assertEqual(
            application_disposition([], [], ["corona-onset-verification"]),
            "provisions-outstanding")

    def test_a_clean_closed_application_is_satisfied(self):
        self.assertEqual(application_disposition([], [], []), "provisions-satisfied")

    def test_findings_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            application_disposition([], "sealed-cavity-without-vent-path", [])


class AssessmentTests(unittest.TestCase):
    def test_a_fresh_application_opens_with_outstanding_provisions(self):
        result = assess_class_1_high_voltage_application(_app())
        self.assertTrue(result["admissible"])
        self.assertEqual(result["disposition"], "provisions-outstanding")

    def test_a_fully_worked_clean_application_is_cleared(self):
        owed = required_provisions(_app())
        result = assess_class_1_high_voltage_application(_app(provisions_closed=owed))
        self.assertTrue(result["cleared_for_flight"])
        self.assertEqual(result["outstanding_provisions"], [])

    def test_an_inadmissible_application_derives_no_provisions(self):
        result = assess_class_1_high_voltage_application(_app(rated_voltage_v=0.0))
        self.assertEqual(result["disposition"], "application-not-admissible")
        self.assertEqual(result["provisions"], [])
        self.assertIsNone(result["voltage_utilisation"])

    def test_the_measured_stresses_are_reported(self):
        result = assess_class_1_high_voltage_application(
            _app(microwave_frequency_ghz=2.0, electrode_gap_mm=5.0))
        self.assertAlmostEqual(result["fd_product_ghz_mm"], 10.0, places=9)
        self.assertAlmostEqual(result["voltage_utilisation"], 0.375, places=9)

    def test_a_finding_keeps_a_fully_closed_application_off_the_vehicle(self):
        base = _app(working_voltage_v=380.0)
        owed = required_provisions(base)
        base["provisions_closed"] = owed
        result = assess_class_1_high_voltage_application(base)
        self.assertEqual(result["disposition"], "provisions-nonconforming")
        self.assertFalse(result["cleared_for_flight"])

    def test_coverage_is_reported(self):
        owed = required_provisions(_app())
        result = assess_class_1_high_voltage_application(
            _app(provisions_closed=owed[:2]))
        self.assertAlmostEqual(result["provision_coverage"], 2.0 / len(owed), places=9)

    def test_the_application_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_class_1_high_voltage_application([_app()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
