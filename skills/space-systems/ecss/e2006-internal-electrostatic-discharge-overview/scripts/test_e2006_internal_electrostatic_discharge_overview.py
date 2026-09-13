#!/usr/bin/env python3
"""Contract test for the clause 9.1 internal-electrostatic-discharge leaf."""

import math
import unittest

from e2006_internal_electrostatic_discharge_overview_logic import (
    BLEED_TAU_FRACTION,
    INTERNAL_FIELD_LIMIT_V_PER_M,
    ITEM_CATEGORIES,
    SCREENING_FLUX_PA_CM2,
    SHIELD_ATTENUATION_LENGTH_MM,
    STORED_ENERGY_LIMIT_J,
    VALIDATION_METHODS,
    assess_internal_esd_provisions,
    attenuated_flux_pa_cm2,
    bleed_time_constant_s,
    categorize_internal_item,
    effective_resistivity_ohm_m,
    evaluate_internal_item,
    floating_conductor_potential_v,
    is_below_screening_threshold,
    steady_state_internal_field_v_per_m,
    stored_discharge_energy_j,
    validate_deep_charging_environment,
    verify_validation_provision,
)

ENV = {"incident_flux_pa_cm2": 5.0, "exposure_duration_s": 36000.0}


def dielectric(**over):
    base = {
        "item_id": "HARNESS-INSULATION",
        "category": "bulk-dielectric",
        "shield_thickness_mm": 1.0,
        "dark_resistivity_ohm_m": 1.0e12,
        "validation": {"method": "deep-charging-analysis", "reference": "AR-1"},
    }
    base.update(over)
    return base


def floater(**over):
    base = {
        "item_id": "SPARE-PAD",
        "category": "ungrounded-conductor",
        "shield_thickness_mm": 1.0,
        "area_m2": 1.0e-4,
        "capacitance_f": 1.0e-11,
        "validation": {"method": "electron-beam-exposure-test", "reference": "TR-2"},
    }
    base.update(over)
    return base


def grounded(**over):
    base = {
        "item_id": "SHIELD-CAN",
        "category": "grounded-conductor",
        "shield_thickness_mm": 1.0,
        "area_m2": 1.0e-4,
        "capacitance_f": 1.0e-11,
        "bond_resistance_ohm": 1.0e6,
        "validation": {
            "method": "grounding-continuity-inspection",
            "reference": "IR-3",
        },
    }
    base.update(over)
    return base


class TestValidateEnvironment(unittest.TestCase):
    def test_valid_environment_is_normalized(self):
        env = validate_deep_charging_environment(ENV)
        self.assertAlmostEqual(env["incident_flux_pa_cm2"], 5.0)
        self.assertAlmostEqual(env["exposure_duration_s"], 36000.0)

    def test_integer_inputs_are_promoted_to_float(self):
        env = validate_deep_charging_environment(
            {"incident_flux_pa_cm2": 5, "exposure_duration_s": 36000}
        )
        self.assertIsInstance(env["incident_flux_pa_cm2"], float)

    def test_non_mapping_environment_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_deep_charging_environment([5.0, 36000.0])

    def test_zero_flux_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_deep_charging_environment(
                {"incident_flux_pa_cm2": 0.0, "exposure_duration_s": 36000.0}
            )

    def test_missing_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_deep_charging_environment({"incident_flux_pa_cm2": 5.0})

    def test_negative_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_deep_charging_environment(
                {"incident_flux_pa_cm2": 5.0, "exposure_duration_s": -1.0}
            )

    def test_non_finite_flux_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_deep_charging_environment(
                {"incident_flux_pa_cm2": float("inf"), "exposure_duration_s": 10.0}
            )


class TestShieldAttenuation(unittest.TestCase):
    def test_no_shield_passes_the_whole_flux(self):
        self.assertAlmostEqual(attenuated_flux_pa_cm2(5.0, 0.0), 5.0)

    def test_one_attenuation_length_leaves_one_over_e(self):
        got = attenuated_flux_pa_cm2(5.0, SHIELD_ATTENUATION_LENGTH_MM)
        self.assertAlmostEqual(got, 5.0 / math.e, places=12)

    def test_thicker_shielding_attenuates_further(self):
        self.assertLess(
            attenuated_flux_pa_cm2(5.0, 3.0), attenuated_flux_pa_cm2(5.0, 1.0)
        )

    def test_attenuation_is_never_negative(self):
        self.assertGreater(attenuated_flux_pa_cm2(5.0, 50.0), 0.0)

    def test_negative_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            attenuated_flux_pa_cm2(5.0, -1.0)

    def test_zero_incident_flux_is_rejected(self):
        with self.assertRaises(ValueError):
            attenuated_flux_pa_cm2(0.0, 1.0)


class TestScreening(unittest.TestCase):
    def test_low_flux_screens_out(self):
        self.assertTrue(is_below_screening_threshold(SCREENING_FLUX_PA_CM2 / 10.0))

    def test_high_flux_does_not_screen_out(self):
        self.assertFalse(is_below_screening_threshold(SCREENING_FLUX_PA_CM2 * 10.0))

    def test_flux_exactly_at_the_threshold_screens_out(self):
        self.assertTrue(is_below_screening_threshold(SCREENING_FLUX_PA_CM2))

    def test_attenuated_flux_landing_on_the_threshold_screens_out(self):
        # The incident flux is built so the attenuated value is mathematically
        # the screening threshold; an exp-and-multiply round trip can put it a
        # few units in the last place above it.
        thickness = 2.0
        incident = SCREENING_FLUX_PA_CM2 / math.exp(
            -thickness / SHIELD_ATTENUATION_LENGTH_MM
        )
        self.assertTrue(
            is_below_screening_threshold(attenuated_flux_pa_cm2(incident, thickness))
        )

    def test_zero_flux_screens_out(self):
        self.assertTrue(is_below_screening_threshold(0.0))

    def test_negative_flux_is_rejected(self):
        with self.assertRaises(ValueError):
            is_below_screening_threshold(-0.5)


class TestResistivityAndField(unittest.TestCase):
    def test_flux_lowers_the_effective_resistivity(self):
        self.assertLess(effective_resistivity_ohm_m(1e14, 5.0), 1e14)

    def test_zero_flux_leaves_the_dark_resistivity(self):
        self.assertAlmostEqual(effective_resistivity_ohm_m(1e14, 0.0), 1e14)

    def test_effective_resistivity_matches_the_model(self):
        self.assertAlmostEqual(
            effective_resistivity_ohm_m(1.1e12, 5.0), 1.1e12 / 11.0, places=6
        )

    def test_effective_resistivity_rejects_zero_dark_value(self):
        with self.assertRaises(ValueError):
            effective_resistivity_ohm_m(0.0, 5.0)

    def test_effective_resistivity_rejects_negative_flux(self):
        with self.assertRaises(ValueError):
            effective_resistivity_ohm_m(1e14, -1.0)

    def test_field_is_flux_times_resistivity_in_si(self):
        self.assertAlmostEqual(
            steady_state_internal_field_v_per_m(1.0, 1.0e12), 1.0e4, places=6
        )

    def test_field_grows_with_resistivity(self):
        self.assertGreater(
            steady_state_internal_field_v_per_m(1.0, 1.0e16),
            steady_state_internal_field_v_per_m(1.0, 1.0e12),
        )

    def test_field_rejects_zero_resistivity(self):
        with self.assertRaises(ValueError):
            steady_state_internal_field_v_per_m(1.0, 0.0)

    def test_field_rejects_non_numeric_flux(self):
        with self.assertRaises(ValueError):
            steady_state_internal_field_v_per_m("5 pA", 1e12)


class TestFloatingConductor(unittest.TestCase):
    def test_potential_is_accumulated_charge_over_capacitance(self):
        got = floating_conductor_potential_v(1.0, 1.0e-4, 1.0e-11, 1000.0)
        self.assertAlmostEqual(got, 1.0e-8 * 1.0e-4 * 1000.0 / 1.0e-11, places=9)

    def test_potential_grows_with_exposure(self):
        self.assertGreater(
            floating_conductor_potential_v(1.0, 1e-4, 1e-11, 2000.0),
            floating_conductor_potential_v(1.0, 1e-4, 1e-11, 1000.0),
        )

    def test_larger_capacitance_lowers_the_potential(self):
        self.assertLess(
            floating_conductor_potential_v(1.0, 1e-4, 1e-9, 1000.0),
            floating_conductor_potential_v(1.0, 1e-4, 1e-11, 1000.0),
        )

    def test_zero_exposure_leaves_no_potential(self):
        self.assertAlmostEqual(
            floating_conductor_potential_v(1.0, 1e-4, 1e-11, 0.0), 0.0
        )

    def test_zero_area_is_rejected(self):
        with self.assertRaises(ValueError):
            floating_conductor_potential_v(1.0, 0.0, 1e-11, 1000.0)

    def test_zero_capacitance_is_rejected(self):
        with self.assertRaises(ValueError):
            floating_conductor_potential_v(1.0, 1e-4, 0.0, 1000.0)

    def test_negative_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            floating_conductor_potential_v(1.0, 1e-4, 1e-11, -1.0)

    def test_stored_energy_is_half_c_v_squared(self):
        self.assertAlmostEqual(
            stored_discharge_energy_j(1.0e-11, 1000.0), 0.5e-5, places=12
        )

    def test_stored_energy_ignores_the_sign_of_the_potential(self):
        self.assertAlmostEqual(
            stored_discharge_energy_j(1e-11, -500.0),
            stored_discharge_energy_j(1e-11, 500.0),
        )

    def test_stored_energy_rejects_zero_capacitance(self):
        with self.assertRaises(ValueError):
            stored_discharge_energy_j(0.0, 500.0)

    def test_stored_energy_rejects_non_numeric_potential(self):
        with self.assertRaises(ValueError):
            stored_discharge_energy_j(1e-11, None)

    def test_bleed_time_constant_is_the_rc_product(self):
        self.assertAlmostEqual(bleed_time_constant_s(1.0e6, 1.0e-11), 1.0e-5, places=15)

    def test_bleed_time_constant_rejects_zero_resistance(self):
        with self.assertRaises(ValueError):
            bleed_time_constant_s(0.0, 1e-11)

    def test_bleed_time_constant_rejects_negative_capacitance(self):
        with self.assertRaises(ValueError):
            bleed_time_constant_s(1e6, -1e-11)


class TestCategorizeInternalItem(unittest.TestCase):
    def test_dielectric_record_keeps_its_resistivity(self):
        rec = categorize_internal_item(dielectric())
        self.assertAlmostEqual(rec["dark_resistivity_ohm_m"], 1.0e12)

    def test_floating_conductor_record_keeps_area_and_capacitance(self):
        rec = categorize_internal_item(floater())
        self.assertAlmostEqual(rec["area_m2"], 1.0e-4)
        self.assertAlmostEqual(rec["capacitance_f"], 1.0e-11)

    def test_grounded_conductor_record_keeps_the_bond_resistance(self):
        rec = categorize_internal_item(grounded())
        self.assertAlmostEqual(rec["bond_resistance_ohm"], 1.0e6)

    def test_shield_thickness_defaults_to_none_fitted(self):
        item = dielectric()
        del item["shield_thickness_mm"]
        self.assertAlmostEqual(categorize_internal_item(item)["shield_thickness_mm"], 0.0)

    def test_every_known_category_is_accepted(self):
        self.assertEqual(len(ITEM_CATEGORIES), 3)
        for builder in (dielectric, floater, grounded):
            rec = categorize_internal_item(builder())
            self.assertIn(rec["category"], ITEM_CATEGORIES)

    def test_uncategorized_category_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_internal_item(dielectric(category="mystery-part"))

    def test_missing_item_id_is_rejected(self):
        item = dielectric()
        del item["item_id"]
        with self.assertRaises(ValueError):
            categorize_internal_item(item)

    def test_dielectric_without_resistivity_is_rejected(self):
        item = dielectric()
        del item["dark_resistivity_ohm_m"]
        with self.assertRaises(ValueError):
            categorize_internal_item(item)

    def test_conductor_without_capacitance_is_rejected(self):
        item = floater()
        del item["capacitance_f"]
        with self.assertRaises(ValueError):
            categorize_internal_item(item)

    def test_grounded_conductor_without_bond_resistance_is_rejected(self):
        item = grounded()
        del item["bond_resistance_ohm"]
        with self.assertRaises(ValueError):
            categorize_internal_item(item)

    def test_negative_shield_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_internal_item(dielectric(shield_thickness_mm=-0.5))

    def test_non_mapping_item_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_internal_item("HARNESS-INSULATION")


class TestValidationProvision(unittest.TestCase):
    def test_analysis_closes_a_dielectric(self):
        self.assertEqual(verify_validation_provision(dielectric(), "bulk-dielectric"), [])

    def test_beam_exposure_closes_a_floating_conductor(self):
        self.assertEqual(
            verify_validation_provision(floater(), "ungrounded-conductor"), []
        )

    def test_continuity_inspection_closes_a_grounded_conductor(self):
        self.assertEqual(
            verify_validation_provision(grounded(), "grounded-conductor"), []
        )

    def test_inspection_does_not_close_a_dielectric(self):
        item = dielectric(
            validation={"method": "grounding-continuity-inspection", "reference": "IR-9"}
        )
        findings = verify_validation_provision(item, "bulk-dielectric")
        self.assertEqual(len(findings), 1)

    def test_analysis_alone_does_not_close_a_floating_conductor(self):
        item = floater(
            validation={"method": "deep-charging-analysis", "reference": "AR-9"}
        )
        findings = verify_validation_provision(item, "ungrounded-conductor")
        self.assertEqual(len(findings), 1)

    def test_similarity_closes_a_floating_conductor(self):
        item = floater(
            validation={
                "method": "similarity-to-qualified-design",
                "reference": "QR-4",
            }
        )
        self.assertEqual(verify_validation_provision(item, "ungrounded-conductor"), [])

    def test_missing_provision_is_a_finding(self):
        item = dielectric()
        del item["validation"]
        findings = verify_validation_provision(item, "bulk-dielectric")
        self.assertEqual(len(findings), 1)

    def test_provision_without_a_reference_is_a_finding(self):
        item = dielectric(
            validation={"method": "deep-charging-analysis", "reference": "  "}
        )
        findings = verify_validation_provision(item, "bulk-dielectric")
        self.assertEqual(len(findings), 1)

    def test_every_known_method_is_a_recognized_token(self):
        self.assertEqual(len(VALIDATION_METHODS), 4)
        for method in VALIDATION_METHODS:
            item = dielectric(validation={"method": method, "reference": "R-1"})
            verify_validation_provision(item, "bulk-dielectric")

    def test_uncategorized_method_is_rejected(self):
        item = dielectric(validation={"method": "vendor-opinion", "reference": "R-1"})
        with self.assertRaises(ValueError):
            verify_validation_provision(item, "bulk-dielectric")

    def test_uncategorized_category_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_validation_provision(dielectric(), "mystery-part")

    def test_non_mapping_provision_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_validation_provision(dielectric(validation="AR-1"), "bulk-dielectric")


class TestEvaluateInternalItem(unittest.TestCase):
    def test_thick_shielding_screens_an_item_out(self):
        rec = evaluate_internal_item(dielectric(shield_thickness_mm=5.0), ENV)
        self.assertTrue(rec["screened_out"])
        self.assertTrue(rec["compliant"])

    def test_a_screened_item_needs_no_validation_provision(self):
        item = dielectric(shield_thickness_mm=5.0)
        del item["validation"]
        rec = evaluate_internal_item(item, ENV)
        self.assertTrue(rec["compliant"])

    def test_a_bleedable_dielectric_stays_under_the_field_limit(self):
        rec = evaluate_internal_item(dielectric(), ENV)
        self.assertFalse(rec["screened_out"])
        self.assertTrue(rec["compliant"])
        self.assertLess(rec["internal_field_v_per_m"], INTERNAL_FIELD_LIMIT_V_PER_M)

    def test_a_high_resistivity_dielectric_breaks_the_field_limit(self):
        rec = evaluate_internal_item(dielectric(dark_resistivity_ohm_m=1.0e17), ENV)
        self.assertFalse(rec["compliant"])
        self.assertTrue(any("internal-field limit" in f for f in rec["findings"]))

    def test_field_exactly_at_the_limit_is_compliant(self):
        # Resistivity is built so the computed field is mathematically the
        # limit; the unit conversion and the division by the radiation-induced
        # conductivity term can put it a few units in the last place above.
        flux = attenuated_flux_pa_cm2(ENV["incident_flux_pa_cm2"], 1.0)
        dark = (INTERNAL_FIELD_LIMIT_V_PER_M / (flux * 1.0e-8)) * (1.0 + 2.0 * flux)
        rec = evaluate_internal_item(dielectric(dark_resistivity_ohm_m=dark), ENV)
        self.assertTrue(rec["compliant"])
        self.assertAlmostEqual(
            rec["internal_field_v_per_m"] / INTERNAL_FIELD_LIMIT_V_PER_M, 1.0, places=9
        )

    def test_an_ungrounded_conductor_stores_too_much_energy(self):
        rec = evaluate_internal_item(floater(), ENV)
        self.assertFalse(rec["compliant"])
        self.assertFalse(rec["bleed_path_adequate"])
        self.assertTrue(any("discharge-energy limit" in f for f in rec["findings"]))

    def test_a_tiny_ungrounded_pad_can_stay_inside_the_energy_limit(self):
        rec = evaluate_internal_item(floater(area_m2=1.0e-9), ENV)
        self.assertTrue(rec["compliant"])
        self.assertLess(rec["stored_energy_j"], STORED_ENERGY_LIMIT_J)

    def test_a_well_bonded_conductor_bleeds_and_passes(self):
        rec = evaluate_internal_item(grounded(), ENV)
        self.assertTrue(rec["bleed_path_adequate"])
        self.assertTrue(rec["compliant"])

    def test_a_high_resistance_bond_fails_the_bleed_check(self):
        rec = evaluate_internal_item(grounded(bond_resistance_ohm=1.0e15), ENV)
        self.assertFalse(rec["bleed_path_adequate"])
        self.assertTrue(any("bleeds with tau" in f for f in rec["findings"]))

    def test_bleed_time_constant_exactly_at_the_limit_is_adequate(self):
        capacitance = 1.0e-11
        tau_limit = BLEED_TAU_FRACTION * ENV["exposure_duration_s"]
        resistance = tau_limit / capacitance
        rec = evaluate_internal_item(
            grounded(bond_resistance_ohm=resistance, capacitance_f=capacitance), ENV
        )
        self.assertTrue(rec["bleed_path_adequate"])

    def test_a_grounded_conductor_still_needs_a_suitable_provision(self):
        rec = evaluate_internal_item(
            grounded(
                validation={
                    "method": "electron-beam-exposure-test",
                    "reference": "TR-8",
                }
            ),
            ENV,
        )
        self.assertFalse(rec["compliant"])

    def test_a_longer_exposure_charges_a_floating_conductor_further(self):
        short = evaluate_internal_item(
            floater(area_m2=1e-9),
            {"incident_flux_pa_cm2": 5.0, "exposure_duration_s": 3600.0},
        )
        long = evaluate_internal_item(
            floater(area_m2=1e-9),
            {"incident_flux_pa_cm2": 5.0, "exposure_duration_s": 36000.0},
        )
        self.assertGreater(long["floating_potential_v"], short["floating_potential_v"])

    def test_bad_item_propagates_the_value_error(self):
        with self.assertRaises(ValueError):
            evaluate_internal_item(dielectric(category="mystery-part"), ENV)

    def test_bad_environment_propagates_the_value_error(self):
        with self.assertRaises(ValueError):
            evaluate_internal_item(dielectric(), {"incident_flux_pa_cm2": 5.0})


class TestAssessInternalEsdProvisions(unittest.TestCase):
    def test_a_clean_set_meets_the_clause(self):
        out = assess_internal_esd_provisions([dielectric(), grounded()], ENV)
        self.assertTrue(out["clause_9_1_met"])
        self.assertEqual(out["assessed"], 2)
        self.assertEqual(out["non_compliant"], [])

    def test_one_floating_conductor_fails_the_roll_up(self):
        out = assess_internal_esd_provisions([dielectric(), floater()], ENV)
        self.assertFalse(out["clause_9_1_met"])
        self.assertEqual(out["non_compliant"], ["SPARE-PAD"])

    def test_screened_items_are_listed(self):
        out = assess_internal_esd_provisions(
            [dielectric(shield_thickness_mm=6.0), grounded()], ENV
        )
        self.assertEqual(out["screened_out"], ["HARNESS-INSULATION"])

    def test_roll_up_keeps_every_item_result(self):
        out = assess_internal_esd_provisions([dielectric(), floater(), grounded()], ENV)
        self.assertEqual(len(out["item_results"]), 3)

    def test_empty_item_list_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_internal_esd_provisions([], ENV)

    def test_non_list_item_input_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_internal_esd_provisions(dielectric(), ENV)

    def test_bad_environment_is_rejected_before_any_item(self):
        with self.assertRaises(ValueError):
            assess_internal_esd_provisions([dielectric()], {"exposure_duration_s": 10.0})


if __name__ == "__main__":
    unittest.main()
