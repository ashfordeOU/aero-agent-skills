#!/usr/bin/env python3
"""Contract test for the ECSS-E-ST-20-06C clause 11.2.1 neutralization leaf."""

import math
import unittest

from e2006_thruster_spacecraft_neutralization_logic import (
    DEFAULT_PHOTOEMISSION_DENSITY_A_M2,
    ELECTRON_MASS_KG,
    ELEMENTARY_CHARGE_C,
    ambient_electron_current,
    ambient_ion_current,
    assess_neutralization,
    environment_current_balance,
    photoemission_current,
    required_emission_capacity,
    secondary_electron_current,
    species_ion_mass_kg,
    thermal_flux_current_density,
    validate_environment,
    verify_emission_capacity,
    worst_case_environment,
)


def geo_env(**over):
    env = {
        "name": "geo-substorm",
        "electron_density_m3": 1.0e6,
        "electron_temperature_ev": 10000.0,
        "collecting_area_m2": 20.0,
        "sunlit_area_m2": 8.0,
        "secondary_emission_yield": 0.4,
    }
    env.update(over)
    return env


def leo_env(**over):
    env = {
        "name": "leo-ram",
        "electron_density_m3": 1.0e11,
        "electron_temperature_ev": 0.2,
        "collecting_area_m2": 20.0,
        "sunlit_area_m2": 8.0,
    }
    env.update(over)
    return env


class FluxDensityTests(unittest.TestCase):
    def test_flux_matches_the_closed_form(self):
        expected = (ELEMENTARY_CHARGE_C * 1.0e6
                    * math.sqrt(10000.0 * ELEMENTARY_CHARGE_C
                                / (2.0 * math.pi * ELECTRON_MASS_KG)))
        self.assertAlmostEqual(
            thermal_flux_current_density(1.0e6, 10000.0, ELECTRON_MASS_KG),
            expected, places=12)

    def test_flux_scales_linearly_with_density(self):
        one = thermal_flux_current_density(1.0e6, 10.0, ELECTRON_MASS_KG)
        two = thermal_flux_current_density(2.0e6, 10.0, ELECTRON_MASS_KG)
        self.assertAlmostEqual(two, 2.0 * one, places=15)

    def test_flux_scales_with_root_temperature(self):
        one = thermal_flux_current_density(1.0e6, 10.0, ELECTRON_MASS_KG)
        four = thermal_flux_current_density(1.0e6, 40.0, ELECTRON_MASS_KG)
        self.assertAlmostEqual(four, 2.0 * one, places=12)

    def test_heavier_particle_carries_less_flux(self):
        light = thermal_flux_current_density(1.0e6, 10.0, ELECTRON_MASS_KG)
        heavy = thermal_flux_current_density(1.0e6, 10.0,
                                             species_ion_mass_kg("xenon"))
        self.assertLess(heavy, light)

    def test_double_charge_state_doubles_the_flux(self):
        single = thermal_flux_current_density(1.0e6, 10.0, ELECTRON_MASS_KG, 1)
        double = thermal_flux_current_density(1.0e6, 10.0, ELECTRON_MASS_KG, 2)
        self.assertAlmostEqual(double, 2.0 * single, places=15)

    def test_zero_density_rejected(self):
        with self.assertRaises(ValueError):
            thermal_flux_current_density(0.0, 10.0, ELECTRON_MASS_KG)

    def test_zero_temperature_rejected(self):
        with self.assertRaises(ValueError):
            thermal_flux_current_density(1.0e6, 0.0, ELECTRON_MASS_KG)

    def test_negative_mass_rejected(self):
        with self.assertRaises(ValueError):
            thermal_flux_current_density(1.0e6, 10.0, -1.0)

    def test_zero_charge_state_rejected(self):
        with self.assertRaises(ValueError):
            thermal_flux_current_density(1.0e6, 10.0, ELECTRON_MASS_KG, 0)

    def test_non_integer_charge_state_rejected(self):
        with self.assertRaises(ValueError):
            thermal_flux_current_density(1.0e6, 10.0, ELECTRON_MASS_KG, 1.5)


class SpeciesTests(unittest.TestCase):
    def test_atomic_oxygen_mass(self):
        self.assertAlmostEqual(species_ion_mass_kg("atomic-oxygen"),
                               2.6567e-26, delta=1.0e-29)

    def test_species_lookup_is_case_insensitive(self):
        self.assertAlmostEqual(species_ion_mass_kg(" Xenon "),
                               species_ion_mass_kg("xenon"), places=32)

    def test_ion_is_far_heavier_than_an_electron(self):
        self.assertGreater(species_ion_mass_kg("hydrogen"),
                           1000.0 * ELECTRON_MASS_KG)

    def test_uncategorized_species_rejected(self):
        with self.assertRaises(ValueError):
            species_ion_mass_kg("neon")

    def test_blank_species_rejected(self):
        with self.assertRaises(ValueError):
            species_ion_mass_kg("  ")


class CollectionCurrentTests(unittest.TestCase):
    def test_electron_current_scales_with_area(self):
        small = ambient_electron_current(1.0, 1.0e6, 10.0)
        large = ambient_electron_current(4.0, 1.0e6, 10.0)
        self.assertAlmostEqual(large, 4.0 * small, places=15)

    def test_ion_current_is_far_below_the_electron_current(self):
        electrons = ambient_electron_current(20.0, 1.0e6, 10.0)
        ions = ambient_ion_current(20.0, 1.0e6, 10.0, "atomic-oxygen")
        self.assertLess(ions, electrons / 100.0)

    def test_ion_current_accepts_a_charge_state(self):
        single = ambient_ion_current(20.0, 1.0e6, 10.0, "helium", 1)
        double = ambient_ion_current(20.0, 1.0e6, 10.0, "helium", 2)
        self.assertAlmostEqual(double, 2.0 * single, places=15)

    def test_zero_collecting_area_rejected_for_electrons(self):
        with self.assertRaises(ValueError):
            ambient_electron_current(0.0, 1.0e6, 10.0)

    def test_negative_collecting_area_rejected_for_ions(self):
        with self.assertRaises(ValueError):
            ambient_ion_current(-2.0, 1.0e6, 10.0)

    def test_unknown_ion_species_rejected(self):
        with self.assertRaises(ValueError):
            ambient_ion_current(20.0, 1.0e6, 10.0, "argon")


class EmissionCurrentTests(unittest.TestCase):
    def test_photoemission_uses_the_default_density(self):
        self.assertAlmostEqual(photoemission_current(8.0),
                               8.0 * DEFAULT_PHOTOEMISSION_DENSITY_A_M2,
                               places=15)

    def test_photoemission_honours_an_override(self):
        self.assertAlmostEqual(photoemission_current(8.0, 4.0e-5),
                               3.2e-4, places=15)

    def test_eclipse_gives_no_photoemission(self):
        self.assertAlmostEqual(photoemission_current(0.0), 0.0, places=18)

    def test_negative_sunlit_area_rejected(self):
        with self.assertRaises(ValueError):
            photoemission_current(-1.0)

    def test_zero_photoemission_density_rejected(self):
        with self.assertRaises(ValueError):
            photoemission_current(8.0, 0.0)

    def test_secondary_current_scales_with_yield(self):
        self.assertAlmostEqual(secondary_electron_current(1.0e-3, 0.4),
                               4.0e-4, places=15)

    def test_zero_yield_gives_no_secondary_current(self):
        self.assertAlmostEqual(secondary_electron_current(1.0e-3, 0.0),
                               0.0, places=18)

    def test_negative_incident_current_rejected(self):
        with self.assertRaises(ValueError):
            secondary_electron_current(-1.0e-3, 0.4)

    def test_negative_yield_rejected(self):
        with self.assertRaises(ValueError):
            secondary_electron_current(1.0e-3, -0.1)

    def test_unphysical_yield_rejected(self):
        with self.assertRaises(ValueError):
            secondary_electron_current(1.0e-3, 12.0)


class EnvironmentValidationTests(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        checked = validate_environment(geo_env())
        self.assertEqual(checked["ion_species"], "atomic-oxygen")
        self.assertEqual(checked["ion_charge_state"], 1)
        self.assertAlmostEqual(checked["backscatter_current_a"], 0.0, places=18)

    def test_name_is_normalised(self):
        checked = validate_environment(geo_env(name="  GEO-Substorm "))
        self.assertEqual(checked["name"], "geo-substorm")

    def test_ion_population_defaults_to_the_electron_population(self):
        checked = validate_environment(geo_env())
        self.assertAlmostEqual(checked["ion_density_m3"], 1.0e6, places=6)
        self.assertAlmostEqual(checked["ion_temperature_ev"], 10000.0, places=6)

    def test_non_mapping_environment_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(["geo-substorm"])

    def test_missing_key_rejected(self):
        env = geo_env()
        del env["collecting_area_m2"]
        with self.assertRaises(ValueError):
            validate_environment(env)

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(geo_env(name="  "))

    def test_sunlit_area_above_collecting_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(geo_env(sunlit_area_m2=25.0))

    def test_negative_sunlit_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(geo_env(sunlit_area_m2=-1.0))

    def test_negative_backscatter_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(geo_env(backscatter_current_a=-1.0e-6))


class BalanceTests(unittest.TestCase):
    def test_positive_driving_is_the_sum_of_its_terms(self):
        balance = environment_current_balance(geo_env())
        total = (balance["photoemission_a"] + balance["secondary_emission_a"]
                 + balance["backscatter_a"] + balance["ion_collection_a"])
        self.assertAlmostEqual(balance["positive_driving_a"], total, places=15)

    def test_net_natural_current_subtracts_electron_collection(self):
        balance = environment_current_balance(geo_env())
        self.assertAlmostEqual(
            balance["net_natural_current_a"],
            balance["positive_driving_a"] - balance["electron_collection_a"],
            places=15)

    def test_hot_tenuous_plasma_drives_the_body_positive(self):
        balance = environment_current_balance(geo_env())
        self.assertGreater(balance["net_natural_current_a"], 0.0)

    def test_dense_cold_plasma_over_supplies_electrons(self):
        balance = environment_current_balance(leo_env())
        self.assertLess(balance["net_natural_current_a"], 0.0)

    def test_backscatter_raises_the_natural_current(self):
        plain = environment_current_balance(geo_env())
        with_backscatter = environment_current_balance(
            geo_env(backscatter_current_a=5.0e-5))
        self.assertAlmostEqual(
            with_backscatter["net_natural_current_a"]
            - plain["net_natural_current_a"], 5.0e-5, places=12)

    def test_secondary_emission_uses_the_collected_electron_current(self):
        balance = environment_current_balance(geo_env(secondary_emission_yield=0.5))
        self.assertAlmostEqual(balance["secondary_emission_a"],
                               0.5 * balance["electron_collection_a"],
                               places=15)


class RequiredCapacityTests(unittest.TestCase):
    def test_margin_is_applied_to_beam_plus_natural(self):
        balance = environment_current_balance(geo_env())
        expected = 1.2 * (4.2 + balance["net_natural_current_a"])
        self.assertAlmostEqual(required_emission_capacity(4.2, geo_env(), 1.2),
                               expected, places=12)

    def test_unit_margin_is_accepted(self):
        balance = environment_current_balance(geo_env())
        self.assertAlmostEqual(required_emission_capacity(4.2, geo_env(), 1.0),
                               4.2 + balance["net_natural_current_a"],
                               places=12)

    def test_electron_rich_plasma_earns_no_credit_against_the_beam(self):
        self.assertAlmostEqual(required_emission_capacity(4.2, leo_env(), 1.2),
                               1.2 * 4.2, places=12)

    def test_natural_current_raises_the_requirement_above_the_beam(self):
        self.assertGreater(required_emission_capacity(4.2, geo_env(), 1.0), 4.2)

    def test_zero_beam_current_rejected(self):
        with self.assertRaises(ValueError):
            required_emission_capacity(0.0, geo_env())

    def test_negative_beam_current_rejected(self):
        with self.assertRaises(ValueError):
            required_emission_capacity(-1.0, geo_env())

    def test_margin_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            required_emission_capacity(4.2, geo_env(), 0.9)


class WorstCaseTests(unittest.TestCase):
    def test_hot_plasma_environment_is_the_worst_case(self):
        worst = worst_case_environment(4.2, [leo_env(), geo_env()])
        self.assertEqual(worst["name"], "geo-substorm")

    def test_worst_case_carries_its_balance(self):
        worst = worst_case_environment(4.2, [leo_env(), geo_env()])
        self.assertGreater(worst["balance"]["photoemission_a"], 0.0)

    def test_equal_environments_break_the_tie_by_name(self):
        worst = worst_case_environment(
            4.2, [geo_env(name="beta-case"), geo_env(name="alpha-case")])
        self.assertEqual(worst["name"], "alpha-case")

    def test_duplicate_environment_name_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_environment(4.2, [geo_env(), geo_env()])

    def test_empty_environment_list_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_environment(4.2, [])

    def test_non_list_environment_set_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_environment(4.2, geo_env())


class VerdictTests(unittest.TestCase):
    def test_capability_above_requirement_is_compliant(self):
        verdict = verify_emission_capacity(6.0, 5.04)
        self.assertTrue(verdict["compliant"])
        self.assertAlmostEqual(verdict["shortfall_a"], 0.0, places=15)

    def test_utilisation_is_the_demand_over_the_capability(self):
        verdict = verify_emission_capacity(6.0, 3.0)
        self.assertAlmostEqual(verdict["utilisation"], 0.5, places=12)

    def test_exact_equality_is_compliant(self):
        verdict = verify_emission_capacity(5.04, 5.04)
        self.assertTrue(verdict["compliant"])

    def test_representation_shortfall_is_absorbed(self):
        # The requirement is a sum of floats that lands a few units in the
        # last place above the identical declared capability.
        required = 0.1 + 0.2
        capability = 0.3
        self.assertLess(capability, required)
        self.assertTrue(verify_emission_capacity(capability, required)["compliant"])

    def test_real_shortfall_is_reported(self):
        verdict = verify_emission_capacity(5.0, 5.04)
        self.assertFalse(verdict["compliant"])
        self.assertAlmostEqual(verdict["shortfall_a"], 0.04, places=9)

    def test_zero_capability_rejected(self):
        with self.assertRaises(ValueError):
            verify_emission_capacity(0.0, 5.04)

    def test_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            verify_emission_capacity(6.0, 0.0)


class AssessmentTests(unittest.TestCase):
    def test_sized_neutralizer_is_compliant(self):
        out = assess_neutralization({
            "beam_current_a": 4.2,
            "neutralizer_capability_a": 6.0,
            "environments": [geo_env(), leo_env()],
        })
        self.assertTrue(out["neutralization_compliant"])
        self.assertEqual(out["worst_case_environment"], "geo-substorm")
        self.assertEqual(out["findings"], [])

    def test_undersized_neutralizer_raises_a_shortfall_finding(self):
        out = assess_neutralization({
            "beam_current_a": 4.2,
            "neutralizer_capability_a": 4.3,
            "environments": [geo_env()],
        })
        self.assertFalse(out["neutralization_compliant"])
        self.assertTrue(any("emission-capacity-shortfall" in f
                            for f in out["findings"]))

    def test_natural_current_above_beam_current_is_a_finding(self):
        out = assess_neutralization({
            "beam_current_a": 1.0e-5,
            "neutralizer_capability_a": 1.0,
            "environments": [geo_env()],
        })
        self.assertTrue(any("natural-current-exceeds-beam-current" in f
                            for f in out["findings"]))
        self.assertFalse(out["neutralization_compliant"])

    def test_default_margin_is_applied(self):
        out = assess_neutralization({
            "beam_current_a": 4.2,
            "neutralizer_capability_a": 6.0,
            "environments": [leo_env()],
        })
        self.assertAlmostEqual(out["margin"], 1.2, places=12)
        self.assertAlmostEqual(out["required_capacity_a"], 5.04, places=9)

    def test_margin_override_raises_the_requirement(self):
        out = assess_neutralization({
            "beam_current_a": 4.2,
            "neutralizer_capability_a": 6.0,
            "environments": [leo_env()],
            "margin": 1.4,
        })
        self.assertAlmostEqual(out["required_capacity_a"], 5.88, places=9)

    def test_assessment_is_deterministic(self):
        config = {
            "beam_current_a": 4.2,
            "neutralizer_capability_a": 6.0,
            "environments": [geo_env(), leo_env()],
        }
        first = assess_neutralization(config)
        second = assess_neutralization(config)
        self.assertEqual(first["required_capacity_a"],
                         second["required_capacity_a"])
        self.assertEqual(first["worst_case_environment"],
                         second["worst_case_environment"])

    def test_non_mapping_configuration_rejected(self):
        with self.assertRaises(ValueError):
            assess_neutralization([geo_env()])

    def test_missing_configuration_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_neutralization({"beam_current_a": 4.2,
                                   "environments": [geo_env()]})

    def test_invalid_margin_in_configuration_rejected(self):
        with self.assertRaises(ValueError):
            assess_neutralization({
                "beam_current_a": 4.2,
                "neutralizer_capability_a": 6.0,
                "environments": [geo_env()],
                "margin": 0.5,
            })


if __name__ == "__main__":
    unittest.main()
