"""Contract tests for the clause 4.6.8 self-made magnetic part logic."""

import unittest

from q60_class_1_self_made_magnetics_logic import (
    BASELINE_SCREENING,
    BOUND_TOLERANCE,
    CURRENT_DENSITY_LIMIT_A_PER_MM2,
    DIELECTRIC_TRIGGER_VOLTAGE_V,
    FLUX_UTILISATION_LIMIT,
    HOT_SPOT_DERATING_K,
    SCREENING_SEQUENCE,
    assess_class_1_self_made_magnetics,
    current_density_acceptable,
    design_findings,
    dielectric_test_adequate,
    flux_utilisation,
    flux_utilisation_acceptable,
    hot_spot_margin_acceptable,
    hot_spot_margin_k,
    magnetics_admissibility,
    magnetics_disposition,
    ordered_screening,
    outstanding_screening,
    required_dielectric_test_voltage,
    required_screening,
    screening_coverage,
    winding_current_density,
)


def _part(**over):
    base = {
        "part_id": "XFMR-6048-B",
        "wire_specification": "ESCC-3901-solderable-enamelled-copper",
        "core_specification": "ferrite-toroid-qualified-batch",
        "winding_procedure_qualified": True,
        "operator_certified": True,
        "winding_current_a": 6.0,
        "conductor_area_mm2": 2.0,
        "peak_flux_density_t": 0.20,
        "saturation_flux_density_t": 0.50,
        "working_voltage_v": 100.0,
        "applied_test_voltage_v": 1500.0,
        "insulation_rating_c": 155.0,
        "hot_spot_temperature_c": 95.0,
        "vacuum_impregnated": True,
        "gapped_core": False,
        "flight_lot_size": 1,
        "screening_closed": [],
    }
    base.update(over)
    return base


class AdmissibilityTests(unittest.TestCase):
    def test_a_sound_part_is_admissible(self):
        self.assertEqual(magnetics_admissibility(_part()), [])

    def test_a_part_without_an_identity_is_stopped(self):
        self.assertIn("part-identity-not-traceable",
                      magnetics_admissibility(_part(part_id="  ")))

    def test_an_unstated_wire_specification_stops_the_part(self):
        self.assertIn("wire-specification-not-stated",
                      magnetics_admissibility(_part(wire_specification=None)))

    def test_an_unstated_core_specification_stops_the_part(self):
        self.assertIn("core-specification-not-stated",
                      magnetics_admissibility(_part(core_specification="")))

    def test_an_unqualified_winding_procedure_stops_the_part(self):
        self.assertIn("winding-procedure-not-qualified",
                      magnetics_admissibility(_part(winding_procedure_qualified=False)))

    def test_an_uncertified_operator_stops_the_part(self):
        self.assertIn("winding-operator-not-certified",
                      magnetics_admissibility(_part(operator_certified=False)))

    def test_reasons_accumulate(self):
        reasons = magnetics_admissibility(
            _part(part_id="", wire_specification="", core_specification="",
                  winding_procedure_qualified=False, operator_certified=False))
        self.assertEqual(len(reasons), 5)

    def test_a_non_boolean_qualification_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            magnetics_admissibility(_part(winding_procedure_qualified="yes"))

    def test_the_part_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            magnetics_admissibility(["XFMR-6048-B"])


class CurrentDensityTests(unittest.TestCase):
    def test_the_density_is_current_over_conductor_area(self):
        self.assertAlmostEqual(winding_current_density(6.0, 2.0), 3.0, places=9)

    def test_a_density_exactly_on_the_limit_is_acceptable(self):
        density = winding_current_density(10.0, 2.0)
        self.assertAlmostEqual(density, CURRENT_DENSITY_LIMIT_A_PER_MM2, places=9)
        self.assertTrue(current_density_acceptable(density))

    def test_a_density_well_past_the_limit_is_not_acceptable(self):
        self.assertFalse(current_density_acceptable(winding_current_density(20.0, 2.0)))

    def test_a_zero_conductor_area_is_rejected(self):
        with self.assertRaises(ValueError):
            winding_current_density(6.0, 0.0)

    def test_a_non_numeric_current_is_rejected(self):
        with self.assertRaises(ValueError):
            winding_current_density("6", 2.0)


class FluxTests(unittest.TestCase):
    def test_the_utilisation_is_peak_over_saturation(self):
        self.assertAlmostEqual(flux_utilisation(0.20, 0.50), 0.4, places=9)

    def test_a_utilisation_exactly_on_the_limit_is_acceptable(self):
        utilisation = flux_utilisation(0.35, 0.50)
        self.assertAlmostEqual(utilisation, FLUX_UTILISATION_LIMIT, places=9)
        self.assertTrue(flux_utilisation_acceptable(utilisation))

    def test_a_core_driven_near_saturation_is_not_acceptable(self):
        self.assertFalse(flux_utilisation_acceptable(flux_utilisation(0.48, 0.50)))

    def test_a_zero_saturation_flux_is_rejected(self):
        with self.assertRaises(ValueError):
            flux_utilisation(0.20, 0.0)

    def test_a_negative_peak_flux_is_rejected(self):
        with self.assertRaises(ValueError):
            flux_utilisation(-0.20, 0.50)


class DielectricTests(unittest.TestCase):
    def test_the_required_voltage_is_twice_working_plus_the_base(self):
        self.assertAlmostEqual(required_dielectric_test_voltage(100.0), 1200.0,
                               places=9)

    def test_a_test_exactly_at_the_required_voltage_is_adequate(self):
        required = required_dielectric_test_voltage(100.0)
        self.assertTrue(dielectric_test_adequate(required, 100.0))

    def test_a_test_well_below_the_required_voltage_is_not_adequate(self):
        self.assertFalse(dielectric_test_adequate(500.0, 100.0))

    def test_a_low_voltage_winding_still_owes_the_base_voltage(self):
        self.assertAlmostEqual(required_dielectric_test_voltage(0.0), 1000.0,
                               places=9)

    def test_a_non_numeric_applied_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            dielectric_test_adequate(None, 100.0)


class HotSpotTests(unittest.TestCase):
    def test_the_margin_is_the_rating_less_the_hot_spot(self):
        self.assertAlmostEqual(hot_spot_margin_k(155.0, 95.0), 60.0, places=9)

    def test_a_margin_exactly_on_the_derating_is_acceptable(self):
        margin = hot_spot_margin_k(155.0, 130.0)
        self.assertAlmostEqual(margin, HOT_SPOT_DERATING_K, places=9)
        self.assertTrue(hot_spot_margin_acceptable(margin))

    def test_a_winding_running_at_its_rating_is_not_acceptable(self):
        self.assertFalse(hot_spot_margin_acceptable(hot_spot_margin_k(155.0, 155.0)))

    def test_a_hot_spot_above_the_rating_gives_a_negative_margin(self):
        self.assertAlmostEqual(hot_spot_margin_k(155.0, 170.0), -15.0, places=9)

    def test_a_sub_zero_hot_spot_is_allowed(self):
        self.assertAlmostEqual(hot_spot_margin_k(155.0, -40.0), 195.0, places=9)

    def test_a_non_numeric_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            hot_spot_margin_k("155", 95.0)


class FindingTests(unittest.TestCase):
    def test_a_part_built_to_practice_raises_nothing(self):
        self.assertEqual(design_findings(_part()), [])

    def test_an_overloaded_conductor_is_reported(self):
        findings = design_findings(_part(winding_current_a=20.0))
        self.assertIn("winding-current-density-above-practice-limit", findings)

    def test_a_core_driven_near_saturation_is_reported(self):
        findings = design_findings(_part(peak_flux_density_t=0.48))
        self.assertIn("core-flux-utilisation-above-practice-limit", findings)

    def test_an_undertested_interwinding_barrier_is_reported(self):
        findings = design_findings(_part(applied_test_voltage_v=500.0))
        self.assertIn("interwinding-test-voltage-below-required", findings)

    def test_a_hot_winding_is_reported(self):
        findings = design_findings(_part(hot_spot_temperature_c=150.0))
        self.assertIn("hot-spot-margin-below-class-1-derating", findings)

    def test_findings_accumulate(self):
        findings = design_findings(_part(winding_current_a=20.0,
                                         peak_flux_density_t=0.48,
                                         applied_test_voltage_v=100.0,
                                         hot_spot_temperature_c=150.0))
        self.assertEqual(len(findings), 4)


class ScreeningTests(unittest.TestCase):
    def test_the_baseline_steps_are_always_owed(self):
        owed = required_screening(_part())
        self.assertTrue(set(BASELINE_SCREENING) <= set(owed))

    def test_an_unimpregnated_part_owes_the_impregnation_verification(self):
        owed = required_screening(_part(vacuum_impregnated=False))
        self.assertIn("vacuum-impregnation-verification", owed)

    def test_an_impregnated_part_does_not(self):
        self.assertNotIn("vacuum-impregnation-verification",
                         required_screening(_part()))

    def test_a_working_voltage_on_the_trigger_owes_the_dielectric_test(self):
        owed = required_screening(
            _part(working_voltage_v=DIELECTRIC_TRIGGER_VOLTAGE_V))
        self.assertIn("interwinding-dielectric-withstanding-test", owed)

    def test_a_low_voltage_winding_does_not_owe_it(self):
        owed = required_screening(_part(working_voltage_v=12.0))
        self.assertNotIn("interwinding-dielectric-withstanding-test", owed)

    def test_a_gapped_core_owes_the_gap_stability_verification(self):
        owed = required_screening(_part(gapped_core=True))
        self.assertIn("gap-stability-verification", owed)

    def test_a_flight_lot_owes_the_sampled_destructive_analysis(self):
        owed = required_screening(_part(flight_lot_size=8))
        self.assertIn("sample-destructive-physical-analysis", owed)

    def test_a_single_part_does_not_owe_it(self):
        self.assertNotIn("sample-destructive-physical-analysis",
                         required_screening(_part()))

    def test_a_zero_flight_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            required_screening(_part(flight_lot_size=0))

    def test_the_owed_steps_come_back_in_performance_order(self):
        owed = required_screening(_part(vacuum_impregnated=False, gapped_core=True,
                                        flight_lot_size=8))
        indexes = [SCREENING_SEQUENCE.index(name) for name in owed]
        self.assertEqual(indexes, sorted(indexes))

    def test_the_destructive_step_is_last_when_it_is_owed(self):
        owed = required_screening(_part(flight_lot_size=8))
        self.assertEqual(owed[-1], "sample-destructive-physical-analysis")

    def test_step_names_compare_case_insensitively(self):
        self.assertEqual(ordered_screening(["EXTERNAL-VISUAL-INSPECTION"]),
                         ["external-visual-inspection"])

    def test_an_unknown_step_is_rejected(self):
        with self.assertRaises(ValueError):
            ordered_screening(["burn-in-for-a-fortnight"])

    def test_a_repeated_step_is_rejected(self):
        with self.assertRaises(ValueError):
            ordered_screening(["external-visual-inspection",
                               "external-visual-inspection"])


class CoverageTests(unittest.TestCase):
    def test_nothing_closed_leaves_everything_outstanding(self):
        owed = required_screening(_part())
        self.assertEqual(outstanding_screening(owed, []), owed)

    def test_closing_a_step_removes_it(self):
        owed = required_screening(_part())
        remaining = outstanding_screening(owed, ["external-visual-inspection"])
        self.assertNotIn("external-visual-inspection", remaining)

    def test_closing_a_step_not_owed_changes_nothing(self):
        owed = required_screening(_part())
        remaining = outstanding_screening(owed, ["gap-stability-verification"])
        self.assertEqual(remaining, owed)

    def test_an_untouched_sequence_reads_zero_coverage(self):
        owed = required_screening(_part())
        self.assertAlmostEqual(screening_coverage(owed, []), 0.0, places=9)

    def test_a_fully_closed_sequence_reads_one(self):
        owed = required_screening(_part())
        self.assertAlmostEqual(screening_coverage(owed, owed), 1.0, places=9)

    def test_half_a_sequence_reads_a_half(self):
        owed = required_screening(_part())
        half = owed[: len(owed) // 2]
        self.assertAlmostEqual(screening_coverage(owed, half),
                               len(half) / float(len(owed)), places=9)

    def test_an_empty_owed_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            screening_coverage([], [])

    def test_the_tolerance_is_the_documented_size(self):
        self.assertAlmostEqual(BOUND_TOLERANCE, 1e-9, places=12)


class DispositionTests(unittest.TestCase):
    def test_inadmissibility_overrides_everything(self):
        self.assertEqual(
            magnetics_disposition(["winding-operator-not-certified"], [], []),
            "magnetics-not-admissible")

    def test_a_finding_outranks_outstanding_screening(self):
        self.assertEqual(
            magnetics_disposition([], ["hot-spot-margin-below-class-1-derating"],
                                  ["external-visual-inspection"]),
            "design-nonconforming")

    def test_outstanding_screening_reads_as_outstanding(self):
        self.assertEqual(
            magnetics_disposition([], [], ["external-visual-inspection"]),
            "screening-outstanding")

    def test_a_clean_closed_part_satisfies_practice(self):
        self.assertEqual(magnetics_disposition([], [], []), "practice-satisfied")

    def test_the_remaining_list_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            magnetics_disposition([], [], "external-visual-inspection")


class AssessmentTests(unittest.TestCase):
    def test_a_fresh_part_opens_with_outstanding_screening(self):
        result = assess_class_1_self_made_magnetics(_part())
        self.assertTrue(result["admissible"])
        self.assertEqual(result["disposition"], "screening-outstanding")

    def test_a_fully_screened_clean_part_is_cleared(self):
        owed = required_screening(_part())
        result = assess_class_1_self_made_magnetics(_part(screening_closed=owed))
        self.assertTrue(result["cleared_for_class_1_use"])
        self.assertEqual(result["outstanding_screening"], [])

    def test_an_inadmissible_part_derives_no_screening(self):
        result = assess_class_1_self_made_magnetics(_part(operator_certified=False))
        self.assertEqual(result["disposition"], "magnetics-not-admissible")
        self.assertEqual(result["screening_sequence"], [])
        self.assertIsNone(result["current_density_a_per_mm2"])

    def test_the_measured_design_values_are_reported(self):
        result = assess_class_1_self_made_magnetics(_part())
        self.assertAlmostEqual(result["current_density_a_per_mm2"], 3.0, places=9)
        self.assertAlmostEqual(result["flux_utilisation"], 0.4, places=9)
        self.assertAlmostEqual(result["required_test_voltage_v"], 1200.0, places=9)
        self.assertAlmostEqual(result["hot_spot_margin_k"], 60.0, places=9)

    def test_a_finding_keeps_a_fully_screened_part_out_of_class_1_use(self):
        base = _part(hot_spot_temperature_c=150.0)
        base["screening_closed"] = required_screening(base)
        result = assess_class_1_self_made_magnetics(base)
        self.assertEqual(result["disposition"], "design-nonconforming")
        self.assertFalse(result["cleared_for_class_1_use"])

    def test_coverage_is_reported(self):
        owed = required_screening(_part())
        result = assess_class_1_self_made_magnetics(_part(screening_closed=owed[:3]))
        self.assertAlmostEqual(result["screening_coverage"], 3.0 / len(owed),
                               places=9)

    def test_the_part_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            assess_class_1_self_made_magnetics([_part()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
