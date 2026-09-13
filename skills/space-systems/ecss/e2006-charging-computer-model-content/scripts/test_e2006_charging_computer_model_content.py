#!/usr/bin/env python3
"""Gate 3 contract test for e2006-charging-computer-model-content."""

import math
import unittest

import e2006_charging_computer_model_content_logic as logic


GEO_SUNLIT_DIELECTRIC = {
    "regime": "geostationary-orbit",
    "sunlit": True,
    "dielectric_present": True,
}

LEO_ECLIPSE = {
    "regime": "low-earth-orbit",
    "sunlit": False,
    "dielectric_present": False,
}


def full_geo_model_effects():
    return [
        "ambient-electron-collection",
        "ambient-ion-collection",
        "secondary-electron-emission-by-electrons",
        "electron-backscatter",
        "current-balance-solution",
        "photoemission",
        "illumination-geometry",
        "surface-conduction",
        "bulk-conduction",
    ]


def good_parameters():
    return {
        "photoemission": {"photoemission_current_density_a_per_m2": 2.0e-5},
        "secondary-electron-emission-by-electrons": {
            "see_peak_yield": 2.4,
            "see_peak_energy_ev": 300.0,
        },
        "electron-backscatter": {"backscatter_yield": 0.25},
        "surface-conduction": {"surface_resistivity_ohm_per_square": 1.0e15},
        "bulk-conduction": {
            "bulk_resistivity_ohm_m": 1.0e16,
            "relative_permittivity": 3.2,
        },
    }


class EffectCatalogueTests(unittest.TestCase):
    def test_ambient_electron_collection_is_an_environment_current(self):
        self.assertEqual(
            logic.effect_family("ambient-electron-collection"),
            "environment-current",
        )

    def test_photoemission_is_an_emission_current(self):
        self.assertEqual(logic.effect_family("photoemission"), "emission-current")

    def test_radiation_induced_conductivity_is_charge_transport(self):
        self.assertEqual(
            logic.effect_family("radiation-induced-conductivity"),
            "charge-transport",
        )

    def test_unknown_effect_id_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.effect_family("magnetic-reconnection")

    def test_non_string_effect_id_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.effect_family(17)

    def test_geometry_family_lists_both_geometry_effects(self):
        self.assertEqual(
            logic.effects_in_family("geometry"),
            ["illumination-geometry", "wake-shadowing-geometry"],
        )

    def test_unknown_family_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.effects_in_family("thermal")


class ConfigurationTests(unittest.TestCase):
    def test_flags_default_to_false(self):
        cfg = logic.validate_configuration({"regime": "interplanetary"})
        self.assertFalse(cfg["transient_analysis"])
        self.assertFalse(cfg["active_plasma_source"])

    def test_unknown_regime_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_configuration({"regime": "lunar-surface"})

    def test_non_boolean_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_configuration(
                {"regime": "geostationary-orbit", "sunlit": "yes"}
            )

    def test_unknown_configuration_key_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_configuration(
                {"regime": "geostationary-orbit", "eclipse_duration": 70.0}
            )

    def test_configuration_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.validate_configuration(["geostationary-orbit"])

    def test_radiation_without_dielectric_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.validate_configuration(
                {"regime": "medium-earth-orbit", "penetrating_radiation": True}
            )


class RequiredEffectTests(unittest.TestCase):
    def test_always_required_effects_appear_in_every_configuration(self):
        required = logic.required_effects(LEO_ECLIPSE)
        for effect in logic.ALWAYS_REQUIRED:
            self.assertIn(effect, required)

    def test_sunlit_configuration_requires_photoemission_and_geometry(self):
        required = logic.required_effects(GEO_SUNLIT_DIELECTRIC)
        self.assertIn("photoemission", required)
        self.assertIn("illumination-geometry", required)

    def test_eclipsed_configuration_does_not_require_photoemission(self):
        self.assertNotIn("photoemission", logic.required_effects(LEO_ECLIPSE))

    def test_dielectric_configuration_requires_both_conduction_effects(self):
        required = logic.required_effects(GEO_SUNLIT_DIELECTRIC)
        self.assertIn("surface-conduction", required)
        self.assertIn("bulk-conduction", required)

    def test_penetrating_radiation_requires_radiation_induced_conductivity(self):
        cfg = dict(GEO_SUNLIT_DIELECTRIC)
        cfg["penetrating_radiation"] = True
        self.assertIn("radiation-induced-conductivity", logic.required_effects(cfg))

    def test_dielectric_alone_does_not_require_radiation_induced_conductivity(self):
        self.assertNotIn(
            "radiation-induced-conductivity",
            logic.required_effects(GEO_SUNLIT_DIELECTRIC),
        )

    def test_flowing_plasma_regime_requires_wake_geometry_and_ion_emission(self):
        required = logic.required_effects(LEO_ECLIPSE)
        self.assertIn("wake-shadowing-geometry", required)
        self.assertIn("secondary-electron-emission-by-ions", required)

    def test_geostationary_regime_does_not_require_wake_geometry(self):
        self.assertNotIn(
            "wake-shadowing-geometry", logic.required_effects(GEO_SUNLIT_DIELECTRIC)
        )

    def test_active_plasma_source_adds_its_external_current(self):
        cfg = dict(GEO_SUNLIT_DIELECTRIC)
        cfg["active_plasma_source"] = True
        self.assertIn("active-plasma-source-current", logic.required_effects(cfg))

    def test_transient_analysis_requires_time_dependent_integration(self):
        cfg = dict(GEO_SUNLIT_DIELECTRIC)
        cfg["transient_analysis"] = True
        self.assertIn("time-dependent-integration", logic.required_effects(cfg))

    def test_required_effect_list_is_sorted_and_unique(self):
        required = logic.required_effects(GEO_SUNLIT_DIELECTRIC)
        self.assertEqual(required, sorted(set(required)))


class CoverageTests(unittest.TestCase):
    def test_complete_model_reports_no_missing_effect(self):
        result = logic.check_effect_coverage(
            GEO_SUNLIT_DIELECTRIC, full_geo_model_effects()
        )
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])
        self.assertAlmostEqual(result["coverage"], 1.0)

    def test_missing_effect_is_reported_and_lowers_coverage(self):
        effects = [e for e in full_geo_model_effects() if e != "bulk-conduction"]
        result = logic.check_effect_coverage(GEO_SUNLIT_DIELECTRIC, effects)
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing"], ["bulk-conduction"])
        self.assertAlmostEqual(result["coverage"], 8.0 / 9.0)

    def test_extra_effect_is_scope_not_fault(self):
        effects = full_geo_model_effects() + ["wake-shadowing-geometry"]
        result = logic.check_effect_coverage(GEO_SUNLIT_DIELECTRIC, effects)
        self.assertTrue(result["complete"])
        self.assertEqual(result["extra_scope"], ["wake-shadowing-geometry"])

    def test_unknown_declared_effect_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_effect_coverage(
                GEO_SUNLIT_DIELECTRIC, full_geo_model_effects() + ["sunspot-flux"]
            )

    def test_declared_effects_must_be_a_sequence(self):
        with self.assertRaises(ValueError):
            logic.check_effect_coverage(GEO_SUNLIT_DIELECTRIC, "photoemission")


class ParameterTests(unittest.TestCase):
    def test_valid_parameter_set_has_no_finding(self):
        self.assertEqual(
            logic.check_effect_parameters(
                "secondary-electron-emission-by-electrons",
                {"see_peak_yield": 2.1, "see_peak_energy_ev": 400.0},
            ),
            [],
        )

    def test_missing_parameter_is_reported(self):
        findings = logic.check_effect_parameters(
            "secondary-electron-emission-by-electrons", {"see_peak_yield": 2.1}
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("see_peak_energy_ev", findings[0])

    def test_out_of_range_parameter_is_reported(self):
        findings = logic.check_effect_parameters(
            "electron-backscatter", {"backscatter_yield": 1.4}
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("outside", findings[0])

    def test_parameter_exactly_on_its_upper_bound_is_accepted(self):
        self.assertEqual(
            logic.check_effect_parameters(
                "electron-backscatter", {"backscatter_yield": 0.9}
            ),
            [],
        )

    def test_parameter_a_few_ulps_over_the_bound_is_absorbed(self):
        edge = 0.9 * (1.0 + 1e-15)
        self.assertEqual(
            logic.check_effect_parameters(
                "electron-backscatter", {"backscatter_yield": edge}
            ),
            [],
        )

    def test_geometry_effect_carries_no_parameter_contract(self):
        self.assertEqual(
            logic.check_effect_parameters("illumination-geometry", {}), []
        )

    def test_non_numeric_parameter_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_effect_parameters(
                "electron-backscatter", {"backscatter_yield": "low"}
            )

    def test_non_finite_parameter_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_effect_parameters(
                "electron-backscatter", {"backscatter_yield": float("nan")}
            )

    def test_parameters_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.check_effect_parameters("electron-backscatter", [0.25])

    def test_absent_parameter_set_is_reported_for_a_declared_effect(self):
        findings = logic.check_parameter_sets(["bulk-conduction"], {})
        self.assertEqual(findings, ["bulk-conduction: no parameter set supplied"])

    def test_parameter_sets_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.check_parameter_sets(["bulk-conduction"], ["1e16"])

    def test_full_declared_model_parameters_are_clean(self):
        self.assertEqual(
            logic.check_parameter_sets(full_geo_model_effects(), good_parameters()),
            [],
        )


class CurrentBalanceTests(unittest.TestCase):
    def test_residual_sums_the_signed_currents(self):
        residual = logic.current_balance_residual(
            {"ambient_electron": -4.0e-6, "photoemission": 3.0e-6, "see": 1.0e-6}
        )
        self.assertAlmostEqual(residual, 0.0, places=15)

    def test_balanced_current_set_closes(self):
        self.assertTrue(
            logic.is_current_balance_closed(
                {"ambient_electron": -1.0e-6, "photo": 3.0e-7, "see": 7.0e-7}
            )
        )

    def test_tiny_representation_residual_is_absorbed(self):
        currents = {"a": 1.0e-6, "b": -1.0e-6 + 1.0e-13}
        self.assertTrue(logic.is_current_balance_closed(currents))

    def test_real_imbalance_is_not_closed(self):
        self.assertFalse(
            logic.is_current_balance_closed({"a": 1.0e-6, "b": -9.0e-7})
        )

    def test_all_zero_current_set_is_closed(self):
        self.assertTrue(logic.is_current_balance_closed({"a": 0.0, "b": 0.0}))

    def test_empty_current_set_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.current_balance_residual({})

    def test_non_numeric_current_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.current_balance_residual({"a": "1e-6"})

    def test_infinite_current_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.current_balance_residual({"a": float("inf")})

    def test_non_positive_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.is_current_balance_closed({"a": 1.0e-6, "b": -1.0e-6}, rel_tol=0.0)


class TimeConstantTests(unittest.TestCase):
    def test_charging_time_constant_value(self):
        tau = logic.charging_time_constant(1.0e-4, 2000.0, 1.0e-6)
        self.assertAlmostEqual(tau / 1.0e5, 2.0, places=9)

    def test_charging_time_constant_is_positive_for_negative_potential(self):
        tau = logic.charging_time_constant(1.0e-4, -2000.0, 1.0e-6)
        self.assertAlmostEqual(tau / 1.0e5, 2.0, places=9)

    def test_zero_capacitance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.charging_time_constant(0.0, 1000.0, 1.0e-6)

    def test_zero_net_current_density_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.charging_time_constant(1.0e-4, 1000.0, 0.0)

    def test_zero_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.charging_time_constant(1.0e-4, 0.0, 1.0e-6)

    def test_dielectric_relaxation_time_value(self):
        tau = logic.dielectric_relaxation_time(3.2, 1.0e16)
        self.assertAlmostEqual(tau / 1.0e5, 2.833340100096e0, places=6)

    def test_relative_permittivity_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.dielectric_relaxation_time(0.8, 1.0e16)

    def test_non_positive_resistivity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.dielectric_relaxation_time(3.2, 0.0)


class IntegrationStepTests(unittest.TestCase):
    def test_small_step_resolves_the_transient(self):
        self.assertTrue(logic.check_integration_step(1.0, 100.0))

    def test_step_exactly_at_the_permitted_fraction_is_accepted(self):
        self.assertTrue(logic.check_integration_step(10.0, 100.0))

    def test_step_a_few_ulps_over_the_limit_is_absorbed(self):
        limit = 0.1 * 100.0
        self.assertTrue(logic.check_integration_step(limit * (1.0 + 1e-15), 100.0))

    def test_step_above_the_limit_is_rejected(self):
        self.assertFalse(logic.check_integration_step(11.0, 100.0))

    def test_step_above_the_time_constant_is_rejected(self):
        self.assertFalse(logic.check_integration_step(150.0, 100.0))

    def test_non_positive_step_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_integration_step(0.0, 100.0)

    def test_non_positive_time_constant_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_integration_step(1.0, -5.0)

    def test_out_of_range_fraction_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.check_integration_step(1.0, 100.0, max_fraction=1.5)


class AcceptanceTests(unittest.TestCase):
    def complete_model(self):
        return {
            "effects": full_geo_model_effects(),
            "parameters": good_parameters(),
            "currents": {"ambient": -1.0e-6, "photo": 7.0e-7, "see": 3.0e-7},
        }

    def test_complete_model_supports_acceptance(self):
        result = logic.assess_model_acceptance(
            GEO_SUNLIT_DIELECTRIC, self.complete_model()
        )
        self.assertTrue(result["supports_acceptance"])
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["balance_closed"])

    def test_missing_effect_blocks_acceptance(self):
        model = self.complete_model()
        model["effects"] = [e for e in model["effects"] if e != "photoemission"]
        result = logic.assess_model_acceptance(GEO_SUNLIT_DIELECTRIC, model)
        self.assertFalse(result["supports_acceptance"])
        self.assertIn("missing effect: photoemission", result["findings"])

    def test_open_current_balance_blocks_acceptance(self):
        model = self.complete_model()
        model["currents"] = {"ambient": -1.0e-6, "photo": 2.0e-7}
        result = logic.assess_model_acceptance(GEO_SUNLIT_DIELECTRIC, model)
        self.assertFalse(result["supports_acceptance"])
        self.assertFalse(result["balance_closed"])

    def test_absent_current_set_is_a_finding(self):
        model = self.complete_model()
        del model["currents"]
        result = logic.assess_model_acceptance(GEO_SUNLIT_DIELECTRIC, model)
        self.assertFalse(result["supports_acceptance"])
        self.assertIsNone(result["balance_closed"])

    def test_transient_run_without_a_step_is_a_finding(self):
        cfg = dict(GEO_SUNLIT_DIELECTRIC)
        cfg["transient_analysis"] = True
        model = self.complete_model()
        model["effects"] = model["effects"] + ["time-dependent-integration"]
        result = logic.assess_model_acceptance(cfg, model)
        self.assertFalse(result["supports_acceptance"])

    def test_transient_run_with_a_resolving_step_is_accepted(self):
        cfg = dict(GEO_SUNLIT_DIELECTRIC)
        cfg["transient_analysis"] = True
        model = self.complete_model()
        model["effects"] = model["effects"] + ["time-dependent-integration"]
        model["integration_step_s"] = 5.0
        model["charging_time_constant_s"] = 200.0
        result = logic.assess_model_acceptance(cfg, model)
        self.assertTrue(result["supports_acceptance"])
        self.assertTrue(result["integration_step_ok"])

    def test_transient_run_with_a_coarse_step_is_rejected(self):
        cfg = dict(GEO_SUNLIT_DIELECTRIC)
        cfg["transient_analysis"] = True
        model = self.complete_model()
        model["effects"] = model["effects"] + ["time-dependent-integration"]
        model["integration_step_s"] = 120.0
        model["charging_time_constant_s"] = 200.0
        result = logic.assess_model_acceptance(cfg, model)
        self.assertFalse(result["integration_step_ok"])
        self.assertFalse(result["supports_acceptance"])

    def test_bad_parameter_blocks_acceptance(self):
        model = self.complete_model()
        model["parameters"]["bulk-conduction"]["relative_permittivity"] = 0.4
        result = logic.assess_model_acceptance(GEO_SUNLIT_DIELECTRIC, model)
        self.assertFalse(result["supports_acceptance"])

    def test_model_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.assess_model_acceptance(GEO_SUNLIT_DIELECTRIC, ["photoemission"])

    def test_model_without_an_effect_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_model_acceptance(GEO_SUNLIT_DIELECTRIC, {"currents": {}})


if __name__ == "__main__":
    unittest.main()
