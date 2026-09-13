#!/usr/bin/env python3
"""Contract test for the high-voltage biased-surface leaf (offline, stdlib)."""

import math
import unittest

from e2006_high_voltage_surface_description_logic import (
    ARC_INCEPTION_MAGNITUDE_V,
    DEFAULT_RAM_VELOCITY_M_S,
    DENSE_PLASMA_DENSITY_M3,
    SNAPOVER_AREA_FACTOR,
    SNAPOVER_ONSET_V,
    assess_high_voltage_surfaces,
    categorize_biased_surface,
    categorize_interaction_regime,
    check_parasitic_budget,
    collected_current_a,
    electron_thermal_current_density,
    evaluate_surface,
    is_dense_low_orbit_plasma,
    positive_bias_fraction,
    ram_ion_current_density,
    string_potential_split,
    validate_plasma_environment,
)

# Dense low-orbit environment used throughout: 1e11 m^-3, 0.1 eV, ram default.
LEO = {"electron_density_m3": 1.0e11, "electron_temperature_ev": 0.1}

# Pinned reference values for LEO, precomputed once and held as literals so
# the expectations do not re-derive themselves from the module under test.
J_E_REF = 8.476784814470048e-04
J_I_REF = 1.249697774520000e-04
FRACTION_REF = 0.03554636537320723
GROUND_REF_V = -154.31258154028686


def interconnect(**overrides):
    surface = {
        "id": "interconnect-1",
        "kind": "array-interconnect",
        "area_m2": 0.01,
        "potential_wrt_ground_v": 0.0,
        "mitigations": ["encapsulation"],
    }
    surface.update(overrides)
    return surface


class EnvironmentTests(unittest.TestCase):
    def test_environment_normalizes_with_a_default_ram_velocity(self):
        env = validate_plasma_environment(LEO)
        self.assertAlmostEqual(env["ram_velocity_m_s"], DEFAULT_RAM_VELOCITY_M_S, places=6)
        self.assertAlmostEqual(env["electron_density_m3"], 1.0e11, places=0)

    def test_explicit_ram_velocity_is_preserved(self):
        env = validate_plasma_environment(dict(LEO, ram_velocity_m_s=7400.0))
        self.assertAlmostEqual(env["ram_velocity_m_s"], 7400.0, places=6)

    def test_missing_density_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_plasma_environment({"electron_temperature_ev": 0.1})

    def test_zero_density_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_plasma_environment(dict(LEO, electron_density_m3=0.0))

    def test_negative_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_plasma_environment(dict(LEO, electron_temperature_ev=-0.1))

    def test_boolean_density_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_plasma_environment(dict(LEO, electron_density_m3=True))

    def test_non_mapping_environment_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_plasma_environment([1.0e11, 0.1])

    def test_dense_low_orbit_plasma_is_recognized(self):
        self.assertTrue(is_dense_low_orbit_plasma(LEO))

    def test_tenuous_plasma_is_not_the_clause_case(self):
        self.assertFalse(is_dense_low_orbit_plasma(dict(LEO, electron_density_m3=1.0e8)))

    def test_density_exactly_at_the_dense_threshold_counts_as_dense(self):
        self.assertTrue(
            is_dense_low_orbit_plasma(dict(LEO, electron_density_m3=DENSE_PLASMA_DENSITY_M3))
        )


class CurrentDensityTests(unittest.TestCase):
    def test_electron_thermal_current_density_matches_the_pinned_value(self):
        self.assertAlmostEqual(electron_thermal_current_density(LEO), J_E_REF, places=12)

    def test_electron_current_density_scales_with_density(self):
        doubled = electron_thermal_current_density(dict(LEO, electron_density_m3=2.0e11))
        self.assertAlmostEqual(doubled, 2.0 * J_E_REF, places=12)

    def test_electron_current_density_scales_with_the_square_root_of_temperature(self):
        hotter = electron_thermal_current_density(dict(LEO, electron_temperature_ev=0.4))
        self.assertAlmostEqual(hotter, 2.0 * J_E_REF, places=12)

    def test_ram_ion_current_density_matches_the_pinned_value(self):
        self.assertAlmostEqual(ram_ion_current_density(LEO), J_I_REF, places=12)

    def test_ram_ion_current_density_scales_with_ram_velocity(self):
        faster = ram_ion_current_density(dict(LEO, ram_velocity_m_s=15600.0))
        self.assertAlmostEqual(faster, 2.0 * J_I_REF, places=12)

    def test_electrons_reach_the_surface_faster_than_ram_ions(self):
        self.assertGreater(electron_thermal_current_density(LEO), ram_ion_current_density(LEO))


class SurfaceCategoryTests(unittest.TestCase):
    def test_interconnect_is_an_exposed_conductor(self):
        self.assertEqual(categorize_biased_surface("array-interconnect"), "exposed-conductor")

    def test_coverglass_is_dielectric_covered(self):
        self.assertEqual(categorize_biased_surface("coverglass"), "dielectric-covered")

    def test_cell_gap_is_a_semi_exposed_junction(self):
        self.assertEqual(
            categorize_biased_surface("cell-gap-triple-junction"), "semi-exposed-junction"
        )

    def test_uncategorized_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_biased_surface("shiny-bit")

    def test_non_string_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_biased_surface(None)


class BiasSplitTests(unittest.TestCase):
    def test_positive_fraction_matches_the_pinned_balance(self):
        fraction = positive_bias_fraction(LEO, 0.4, 0.1)
        self.assertAlmostEqual(fraction, FRACTION_REF, places=12)

    def test_fraction_stays_inside_the_unit_interval(self):
        for electron_area, ion_area in ((0.001, 50.0), (50.0, 0.001)):
            fraction = positive_bias_fraction(LEO, electron_area, ion_area)
            self.assertGreaterEqual(fraction, 0.0)
            self.assertLessEqual(fraction, 1.0)

    def test_more_ion_collecting_area_lifts_the_array_toward_the_plasma(self):
        low = positive_bias_fraction(LEO, 0.4, 0.1)
        high = positive_bias_fraction(LEO, 0.4, 0.4)
        self.assertGreater(high, low)

    def test_more_electron_collecting_area_drives_ground_more_negative(self):
        few = positive_bias_fraction(LEO, 0.2, 0.1)
        many = positive_bias_fraction(LEO, 0.8, 0.1)
        self.assertLess(many, few)

    def test_zero_electron_area_is_rejected(self):
        with self.assertRaises(ValueError):
            positive_bias_fraction(LEO, 0.0, 0.1)

    def test_negative_ion_area_is_rejected(self):
        with self.assertRaises(ValueError):
            positive_bias_fraction(LEO, 0.4, -0.1)

    def test_string_split_puts_most_of_a_leo_array_negative_of_the_plasma(self):
        split = string_potential_split(160.0, FRACTION_REF)
        self.assertAlmostEqual(split["ground_potential_v"], GROUND_REF_V, places=9)
        self.assertLess(split["negative_end_v"], 0.0)
        self.assertGreater(split["positive_end_v"], 0.0)

    def test_string_split_ends_span_the_full_string_voltage(self):
        split = string_potential_split(160.0, 0.25)
        self.assertAlmostEqual(split["positive_end_v"] - split["negative_end_v"], 160.0, places=9)

    def test_fraction_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            string_potential_split(160.0, 1.5)

    def test_non_positive_string_voltage_is_rejected(self):
        with self.assertRaises(ValueError):
            string_potential_split(0.0, 0.25)


class RegimeTests(unittest.TestCase):
    def test_shallow_negative_surface_collects_ions(self):
        self.assertEqual(categorize_interaction_regime(-30.0), "ion-collection")

    def test_deep_negative_surface_is_at_arc_inception_risk(self):
        self.assertEqual(categorize_interaction_regime(-150.0), "arc-inception-risk")

    def test_small_positive_surface_collects_electrons(self):
        self.assertEqual(categorize_interaction_regime(10.0), "electron-collection")

    def test_surface_at_plasma_potential_collects_electrons(self):
        self.assertEqual(categorize_interaction_regime(0.0), "electron-collection")

    def test_strongly_positive_surface_is_in_snapover(self):
        self.assertEqual(categorize_interaction_regime(120.0), "snapover-collection")

    def test_inception_magnitude_reached_by_a_sum_of_offsets_still_counts(self):
        # -33.4 - 33.3 - 33.3 is exactly -100 V physically but lands a few ULPs
        # short of it in binary; the compliant-looking shortfall must not
        # downgrade the regime.
        potential = -33.4 + -33.3 + -33.3
        self.assertGreater(potential, -ARC_INCEPTION_MAGNITUDE_V)
        self.assertEqual(categorize_interaction_regime(potential), "arc-inception-risk")

    def test_snapover_onset_reached_by_a_sum_of_offsets_still_counts(self):
        # 0.01 + 32.05 + 7.94 is exactly 40 V physically, one ULP short in binary.
        potential = 0.01 + 32.05 + 7.94
        self.assertLess(potential, SNAPOVER_ONSET_V)
        self.assertEqual(categorize_interaction_regime(potential), "snapover-collection")

    def test_non_positive_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_interaction_regime(-150.0, arc_inception_magnitude_v=0.0)

    def test_non_numeric_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_interaction_regime("-150")


class CollectedCurrentTests(unittest.TestCase):
    def test_positive_exposed_conductor_collects_the_electron_flux(self):
        current = collected_current_a("exposed-conductor", 0.02, 10.0, LEO)
        self.assertAlmostEqual(current, J_E_REF * 0.02, places=12)

    def test_snapover_multiplies_the_effective_collecting_area(self):
        plain = collected_current_a("exposed-conductor", 0.02, 10.0, LEO)
        snapped = collected_current_a("exposed-conductor", 0.02, 120.0, LEO)
        self.assertAlmostEqual(snapped, plain * SNAPOVER_AREA_FACTOR, places=12)

    def test_dielectric_cover_collects_only_through_its_leak_fraction(self):
        bare = collected_current_a("exposed-conductor", 10.0, 10.0, LEO)
        covered = collected_current_a("dielectric-covered", 10.0, 10.0, LEO)
        self.assertLess(covered, bare)
        self.assertAlmostEqual(covered, bare * 1.0e-3, places=12)

    def test_semi_exposed_junction_collects_on_half_its_area(self):
        bare = collected_current_a("exposed-conductor", 0.04, 10.0, LEO)
        junction = collected_current_a("semi-exposed-junction", 0.04, 10.0, LEO)
        self.assertAlmostEqual(junction, bare * 0.5, places=12)

    def test_negative_surface_collects_the_smaller_ion_flux(self):
        electrons = collected_current_a("exposed-conductor", 0.02, 10.0, LEO)
        ions = collected_current_a("exposed-conductor", 0.02, -150.0, LEO)
        self.assertAlmostEqual(ions, J_I_REF * 0.02, places=12)
        self.assertLess(ions, electrons)

    def test_unknown_category_is_rejected(self):
        with self.assertRaises(ValueError):
            collected_current_a("painted-panel", 0.02, 10.0, LEO)

    def test_unknown_regime_is_rejected(self):
        with self.assertRaises(ValueError):
            collected_current_a("exposed-conductor", 0.02, 10.0, LEO, regime="sparking")

    def test_zero_area_is_rejected(self):
        with self.assertRaises(ValueError):
            collected_current_a("exposed-conductor", 0.0, 10.0, LEO)


class BudgetTests(unittest.TestCase):
    def test_total_under_the_budget_has_no_findings(self):
        result = check_parasitic_budget([1.0e-4, 2.0e-4], 1.0e-3)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["total_a"], 3.0e-4, places=12)

    def test_total_above_the_budget_is_a_finding(self):
        result = check_parasitic_budget([2.0e-3, 1.0e-3], 1.0e-3)
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("exceeds", result["findings"][0])

    def test_total_exactly_at_the_budget_passes(self):
        # 0.1 A + 0.2 A is exactly the 0.3 A budget physically; in binary the
        # sum lands one ULP above it.
        currents = [0.1, 0.2]
        self.assertGreater(math.fsum(currents), 0.3)
        self.assertEqual(check_parasitic_budget(currents, 0.3)["findings"], [])

    def test_negative_per_surface_current_is_rejected(self):
        with self.assertRaises(ValueError):
            check_parasitic_budget([1.0e-4, -2.0e-4], 1.0e-3)

    def test_non_list_currents_are_rejected(self):
        with self.assertRaises(ValueError):
            check_parasitic_budget(1.0e-4, 1.0e-3)

    def test_non_positive_budget_is_rejected(self):
        with self.assertRaises(ValueError):
            check_parasitic_budget([1.0e-4], 0.0)


class EvaluateSurfaceTests(unittest.TestCase):
    def test_deep_negative_surface_without_mitigation_is_a_finding(self):
        result = evaluate_surface(interconnect(mitigations=[]), LEO, GROUND_REF_V)
        self.assertEqual(result["regime"], "arc-inception-risk")
        self.assertFalse(result["compliant"])
        self.assertIn("arc inception", result["findings"][0])

    def test_deep_negative_surface_with_encapsulation_is_compliant(self):
        result = evaluate_surface(interconnect(), LEO, GROUND_REF_V)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["plasma_relative_potential_v"], GROUND_REF_V, places=9)

    def test_snapover_surface_without_mitigation_is_a_finding(self):
        surface = interconnect(id="tab-1", potential_wrt_ground_v=260.0, mitigations=[])
        result = evaluate_surface(surface, LEO, GROUND_REF_V)
        self.assertEqual(result["regime"], "snapover-collection")
        self.assertIn("snapover", result["findings"][0])

    def test_snapover_surface_with_a_plasma_shield_is_compliant(self):
        surface = interconnect(
            id="tab-1", potential_wrt_ground_v=260.0, mitigations=["plasma-shield"]
        )
        self.assertTrue(evaluate_surface(surface, LEO, GROUND_REF_V)["compliant"])

    def test_ground_reaching_inception_by_a_sum_of_offsets_still_flags(self):
        ground = -33.4 + -33.3 + -33.3
        result = evaluate_surface(
            interconnect(potential_wrt_ground_v=0.0, mitigations=[]), LEO, ground
        )
        self.assertEqual(result["regime"], "arc-inception-risk")

    def test_uncategorized_mitigation_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_surface(interconnect(mitigations=["hope"]), LEO, GROUND_REF_V)

    def test_mitigations_must_be_a_list(self):
        with self.assertRaises(ValueError):
            evaluate_surface(interconnect(mitigations="encapsulation"), LEO, GROUND_REF_V)

    def test_missing_identifier_is_rejected(self):
        surface = interconnect()
        del surface["id"]
        with self.assertRaises(ValueError):
            evaluate_surface(surface, LEO, GROUND_REF_V)

    def test_missing_area_is_rejected(self):
        surface = interconnect()
        del surface["area_m2"]
        with self.assertRaises(ValueError):
            evaluate_surface(surface, LEO, GROUND_REF_V)

    def test_zero_area_surface_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_surface(interconnect(area_m2=0.0), LEO, GROUND_REF_V)

    def test_non_mapping_surface_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_surface("interconnect-1", LEO, GROUND_REF_V)


class AssessmentTests(unittest.TestCase):
    def base_surfaces(self):
        return [
            interconnect(),
            {
                "id": "coverglass-1",
                "kind": "coverglass",
                "area_m2": 12.0,
                "potential_wrt_ground_v": 80.0,
                "mitigations": [],
            },
        ]

    def test_mitigated_array_passes(self):
        result = assess_high_voltage_surfaces(
            self.base_surfaces(), LEO, 160.0, 0.4, 0.1, 1.0e-3
        )
        self.assertEqual(result["verdict"], "pass")
        self.assertTrue(result["dense_plasma"])
        self.assertAlmostEqual(result["split"]["ground_potential_v"], GROUND_REF_V, places=9)
        self.assertEqual(result["regime_counts"]["arc-inception-risk"], 1)

    def test_unmitigated_interconnect_fails_the_set(self):
        surfaces = self.base_surfaces()
        surfaces[0] = interconnect(mitigations=[])
        result = assess_high_voltage_surfaces(surfaces, LEO, 160.0, 0.4, 0.1, 1.0e-3)
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(result["finding_count"], 1)

    def test_parasitic_budget_overrun_fails_the_set(self):
        surfaces = self.base_surfaces()
        surfaces.append(
            {
                "id": "electrode-1",
                "kind": "biased-electrode",
                "area_m2": 2.0,
                "potential_wrt_ground_v": 400.0,
                "mitigations": ["plasma-shield"],
            }
        )
        result = assess_high_voltage_surfaces(surfaces, LEO, 160.0, 0.4, 0.1, 1.0e-4)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any("budget" in f for f in result["findings"]))

    def test_regime_counts_cover_every_surface(self):
        result = assess_high_voltage_surfaces(
            self.base_surfaces(), LEO, 160.0, 0.4, 0.1, 1.0e-3
        )
        self.assertEqual(sum(result["regime_counts"].values()), 2)

    def test_duplicate_surface_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_high_voltage_surfaces(
                [interconnect(), interconnect()], LEO, 160.0, 0.4, 0.1, 1.0e-3
            )

    def test_empty_surface_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_high_voltage_surfaces([], LEO, 160.0, 0.4, 0.1, 1.0e-3)

    def test_non_list_surface_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_high_voltage_surfaces(interconnect(), LEO, 160.0, 0.4, 0.1, 1.0e-3)


if __name__ == "__main__":
    unittest.main()
