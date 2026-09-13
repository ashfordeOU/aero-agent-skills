#!/usr/bin/env python3
"""Contract test for the clause 8.3 plasma power-loss validation leaf."""

import math
import unittest

from e2006_plasma_power_loss_validation_logic import (
    BIAS_ELECTRON,
    BIAS_ION,
    BIAS_NONE,
    DEFAULT_ALLOWABLE_FRACTION,
    GEOMETRY_KEYS,
    SNAPOVER_AREA_MULTIPLIER,
    SNAPOVER_ONSET_V,
    categorize_element_bias,
    collection_enhancement,
    electron_thermal_current_density,
    element_leakage_current,
    element_parasitic_power,
    ion_thermal_current_density,
    rank_leakage_contributors,
    validate_plasma_environment,
    validate_power_loss_budget,
)

LEO = {
    "electron_density_m3": 1.0e12,
    "electron_temperature_ev": 0.1,
    "ion_temperature_ev": 0.1,
    "ion_mass_amu": 16.0,
}


def element(**over):
    base = {
        "element_id": "IC-1",
        "geometry": "planar-exposed-conductor",
        "exposed_area_m2": 1.0e-4,
        "potential_v": 50.0,
        "dielectric_adjacent": False,
        "encapsulated": False,
    }
    base.update(over)
    return base


class TestValidatePlasmaEnvironment(unittest.TestCase):
    def test_full_record_is_normalized(self):
        env = validate_plasma_environment(LEO)
        self.assertAlmostEqual(env["electron_density_m3"], 1.0e12)
        self.assertAlmostEqual(env["ion_mass_amu"], 16.0)

    def test_ion_temperature_defaults_to_the_electron_temperature(self):
        env = validate_plasma_environment(
            {"electron_density_m3": 1e11, "electron_temperature_ev": 0.2}
        )
        self.assertAlmostEqual(env["ion_temperature_ev"], 0.2)

    def test_ion_mass_defaults_to_atomic_oxygen(self):
        env = validate_plasma_environment(
            {"electron_density_m3": 1e11, "electron_temperature_ev": 0.2}
        )
        self.assertAlmostEqual(env["ion_mass_amu"], 16.0)

    def test_integer_inputs_are_promoted_to_float(self):
        env = validate_plasma_environment(
            {"electron_density_m3": 1000000000000, "electron_temperature_ev": 1}
        )
        self.assertIsInstance(env["electron_temperature_ev"], float)

    def test_non_mapping_environment_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_plasma_environment([1e12, 0.1])

    def test_zero_density_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_plasma_environment(
                {"electron_density_m3": 0.0, "electron_temperature_ev": 0.1}
            )

    def test_negative_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_plasma_environment(
                {"electron_density_m3": 1e12, "electron_temperature_ev": -0.1}
            )

    def test_missing_density_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_plasma_environment({"electron_temperature_ev": 0.1})

    def test_non_finite_density_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_plasma_environment(
                {"electron_density_m3": float("nan"), "electron_temperature_ev": 0.1}
            )

    def test_zero_ion_mass_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_plasma_environment(
                {
                    "electron_density_m3": 1e12,
                    "electron_temperature_ev": 0.1,
                    "ion_mass_amu": 0.0,
                }
            )


class TestThermalCurrentDensities(unittest.TestCase):
    def test_electron_flux_matches_the_closed_form(self):
        got = electron_thermal_current_density(1.0e12, 0.1)
        q = 1.602176634e-19
        me = 9.1093837015e-31
        want = q * 1.0e12 * math.sqrt(q * 0.1 / (2.0 * math.pi * me))
        self.assertAlmostEqual(got, want, places=12)

    def test_electron_flux_scales_linearly_with_density(self):
        one = electron_thermal_current_density(1.0e12, 0.1)
        two = electron_thermal_current_density(2.0e12, 0.1)
        self.assertAlmostEqual(two, 2.0 * one, places=12)

    def test_electron_flux_grows_with_temperature(self):
        self.assertGreater(
            electron_thermal_current_density(1e12, 0.4),
            electron_thermal_current_density(1e12, 0.1),
        )

    def test_ion_flux_is_far_below_the_electron_flux(self):
        electrons = electron_thermal_current_density(1e12, 0.1)
        ions = ion_thermal_current_density(1e12, 0.1, 16.0)
        self.assertLess(ions, electrons / 100.0)

    def test_heavier_ions_arrive_more_slowly(self):
        light = ion_thermal_current_density(1e12, 0.1, 1.0)
        heavy = ion_thermal_current_density(1e12, 0.1, 16.0)
        self.assertAlmostEqual(heavy, light / 4.0, places=12)

    def test_electron_flux_rejects_zero_density(self):
        with self.assertRaises(ValueError):
            electron_thermal_current_density(0.0, 0.1)

    def test_electron_flux_rejects_negative_temperature(self):
        with self.assertRaises(ValueError):
            electron_thermal_current_density(1e12, -1.0)

    def test_ion_flux_rejects_negative_mass(self):
        with self.assertRaises(ValueError):
            ion_thermal_current_density(1e12, 0.1, -16.0)

    def test_ion_flux_rejects_non_numeric_temperature(self):
        with self.assertRaises(ValueError):
            ion_thermal_current_density(1e12, "hot", 16.0)


class TestCategorizeElementBias(unittest.TestCase):
    def test_positive_bias_collects_electrons(self):
        self.assertEqual(categorize_element_bias(element())["bias"], BIAS_ELECTRON)

    def test_negative_bias_collects_ions(self):
        rec = categorize_element_bias(element(potential_v=-60.0))
        self.assertEqual(rec["bias"], BIAS_ION)

    def test_encapsulated_element_collects_nothing(self):
        rec = categorize_element_bias(element(encapsulated=True))
        self.assertEqual(rec["bias"], BIAS_NONE)

    def test_element_at_plasma_potential_collects_nothing(self):
        rec = categorize_element_bias(element(potential_v=0.0))
        self.assertEqual(rec["bias"], BIAS_NONE)

    def test_every_known_geometry_is_accepted(self):
        for geometry in GEOMETRY_KEYS:
            rec = categorize_element_bias(element(geometry=geometry))
            self.assertEqual(rec["geometry"], geometry)

    def test_uncategorized_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_element_bias(element(geometry="toroidal-whatsit"))

    def test_missing_element_id_is_rejected(self):
        bad = element()
        del bad["element_id"]
        with self.assertRaises(ValueError):
            categorize_element_bias(bad)

    def test_zero_area_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_element_bias(element(exposed_area_m2=0.0))

    def test_negative_area_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_element_bias(element(exposed_area_m2=-1e-4))

    def test_non_boolean_encapsulated_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_element_bias(element(encapsulated="yes"))

    def test_non_boolean_dielectric_adjacent_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_element_bias(element(dielectric_adjacent=1))

    def test_non_numeric_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_element_bias(element(potential_v="50 V"))

    def test_non_mapping_element_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_element_bias("IC-1")


class TestCollectionEnhancement(unittest.TestCase):
    def test_planar_hardware_collects_through_its_own_area(self):
        self.assertAlmostEqual(
            collection_enhancement(500.0, 0.1, "planar-exposed-conductor"), 1.0
        )

    def test_spherical_node_follows_the_linear_law(self):
        self.assertAlmostEqual(
            collection_enhancement(1.0, 0.1, "spherical-node"), 11.0
        )

    def test_cylindrical_interconnect_follows_the_square_root_law(self):
        want = (2.0 / math.sqrt(math.pi)) * math.sqrt(1.0 + 10.0)
        self.assertAlmostEqual(
            collection_enhancement(1.0, 0.1, "cylindrical-interconnect"), want
        )

    def test_enhancement_uses_the_magnitude_of_the_bias(self):
        positive = collection_enhancement(80.0, 0.2, "spherical-node")
        negative = collection_enhancement(-80.0, 0.2, "spherical-node")
        self.assertAlmostEqual(positive, negative)

    def test_enhancement_grows_with_bias(self):
        self.assertGreater(
            collection_enhancement(200.0, 0.1, "spherical-node"),
            collection_enhancement(20.0, 0.1, "spherical-node"),
        )

    def test_zero_bias_gives_unit_enhancement_on_a_node(self):
        self.assertAlmostEqual(
            collection_enhancement(0.0, 0.1, "spherical-node"), 1.0
        )

    def test_uncategorized_geometry_is_rejected(self):
        with self.assertRaises(ValueError):
            collection_enhancement(50.0, 0.1, "fractal")

    def test_zero_temperature_is_rejected(self):
        with self.assertRaises(ValueError):
            collection_enhancement(50.0, 0.0, "spherical-node")


class TestElementLeakageCurrent(unittest.TestCase):
    def test_planar_electron_collection_is_area_times_flux(self):
        rec = element_leakage_current(element(), LEO)
        want = electron_thermal_current_density(1e12, 0.1) * 1e-4
        self.assertAlmostEqual(rec["leakage_current_a"], want, places=15)

    def test_non_collecting_element_draws_nothing(self):
        rec = element_leakage_current(element(encapsulated=True), LEO)
        self.assertAlmostEqual(rec["leakage_current_a"], 0.0)
        self.assertFalse(rec["snapover_active"])

    def test_ion_collection_is_much_weaker_than_electron_collection(self):
        positive = element_leakage_current(element(potential_v=60.0), LEO)
        negative = element_leakage_current(element(potential_v=-60.0), LEO)
        self.assertLess(negative["leakage_current_a"], positive["leakage_current_a"])

    def test_snapover_multiplies_the_collected_current(self):
        below = element_leakage_current(
            element(potential_v=SNAPOVER_ONSET_V - 1.0, dielectric_adjacent=True), LEO
        )
        above = element_leakage_current(
            element(potential_v=SNAPOVER_ONSET_V, dielectric_adjacent=True), LEO
        )
        self.assertTrue(above["snapover_active"])
        self.assertFalse(below["snapover_active"])
        self.assertGreater(
            above["leakage_current_a"], below["leakage_current_a"] * SNAPOVER_AREA_MULTIPLIER * 0.9
        )

    def test_snapover_needs_an_adjacent_dielectric(self):
        rec = element_leakage_current(element(potential_v=400.0), LEO)
        self.assertFalse(rec["snapover_active"])

    def test_snapover_does_not_apply_to_ion_collection(self):
        rec = element_leakage_current(
            element(potential_v=-400.0, dielectric_adjacent=True), LEO
        )
        self.assertFalse(rec["snapover_active"])

    def test_cylindrical_geometry_collects_more_than_planar(self):
        planar = element_leakage_current(element(), LEO)
        cyl = element_leakage_current(
            element(geometry="cylindrical-interconnect"), LEO
        )
        self.assertGreater(cyl["leakage_current_a"], planar["leakage_current_a"])

    def test_bad_environment_propagates_the_value_error(self):
        with self.assertRaises(ValueError):
            element_leakage_current(element(), {"electron_temperature_ev": 0.1})


class TestElementParasiticPower(unittest.TestCase):
    def test_power_is_bias_magnitude_times_current(self):
        rec = element_parasitic_power(element(), LEO)
        self.assertAlmostEqual(
            rec["parasitic_power_w"], 50.0 * rec["leakage_current_a"], places=15
        )

    def test_negative_bias_still_yields_a_positive_loss(self):
        rec = element_parasitic_power(element(potential_v=-60.0), LEO)
        self.assertGreater(rec["parasitic_power_w"], 0.0)

    def test_non_collecting_element_loses_nothing(self):
        rec = element_parasitic_power(element(potential_v=0.0), LEO)
        self.assertAlmostEqual(rec["parasitic_power_w"], 0.0)


class TestRankLeakageContributors(unittest.TestCase):
    def test_worst_contributor_comes_first(self):
        small = element_parasitic_power(element(element_id="A"), LEO)
        big = element_parasitic_power(
            element(element_id="B", exposed_area_m2=1e-2), LEO
        )
        ranked = rank_leakage_contributors([small, big])
        self.assertEqual(ranked[0]["element_id"], "B")

    def test_ties_break_on_element_id(self):
        first = element_parasitic_power(element(element_id="Z"), LEO)
        second = element_parasitic_power(element(element_id="A"), LEO)
        ranked = rank_leakage_contributors([first, second])
        self.assertEqual(ranked[0]["element_id"], "A")

    def test_unevaluated_record_is_rejected(self):
        with self.assertRaises(ValueError):
            rank_leakage_contributors([element()])

    def test_non_list_input_is_rejected(self):
        with self.assertRaises(ValueError):
            rank_leakage_contributors(element_parasitic_power(element(), LEO))


class TestValidatePowerLossBudget(unittest.TestCase):
    def test_small_loss_against_a_large_array_is_compliant(self):
        out = validate_power_loss_budget([element()], LEO, 500.0)
        self.assertTrue(out["clause_8_3_met"])
        self.assertGreater(out["margin_w"], 0.0)

    def test_loss_fraction_is_reported(self):
        out = validate_power_loss_budget([element()], LEO, 500.0)
        self.assertAlmostEqual(
            out["loss_fraction"], out["total_parasitic_power_w"] / 500.0
        )

    def test_a_large_exposed_area_breaks_the_budget(self):
        out = validate_power_loss_budget(
            [element(exposed_area_m2=4.0, geometry="spherical-node", potential_v=300.0)],
            LEO,
            50.0,
        )
        self.assertFalse(out["clause_8_3_met"])
        self.assertTrue(any("above the" in f for f in out["findings"]))

    def test_total_exactly_at_the_allowance_is_compliant(self):
        probe = element_parasitic_power(element(), LEO)
        total = probe["parasitic_power_w"]
        generated = total / DEFAULT_ALLOWABLE_FRACTION
        out = validate_power_loss_budget([element()], LEO, generated)
        self.assertTrue(out["clause_8_3_met"])

    def test_summed_total_exactly_at_the_allowance_is_compliant(self):
        parts = [
            element(element_id="A"),
            element(element_id="B", exposed_area_m2=3.0e-4),
            element(element_id="C", exposed_area_m2=7.0e-4),
        ]
        total = math.fsum(
            element_parasitic_power(p, LEO)["parasitic_power_w"] for p in parts
        )
        generated = total / DEFAULT_ALLOWABLE_FRACTION
        out = validate_power_loss_budget(parts, LEO, generated)
        self.assertTrue(out["clause_8_3_met"])

    def test_total_is_the_sum_over_elements(self):
        parts = [element(element_id="A"), element(element_id="B")]
        out = validate_power_loss_budget(parts, LEO, 500.0)
        self.assertAlmostEqual(
            out["total_parasitic_power_w"],
            2.0 * element_parasitic_power(element(), LEO)["parasitic_power_w"],
            places=15,
        )

    def test_a_dominant_contributor_is_flagged(self):
        parts = [
            element(element_id="A"),
            element(element_id="B", exposed_area_m2=1.0e-1),
        ]
        out = validate_power_loss_budget(parts, LEO, 5000.0)
        self.assertTrue(any("more than half" in f for f in out["findings"]))

    def test_a_single_element_set_is_not_flagged_for_dominance(self):
        out = validate_power_loss_budget([element()], LEO, 500.0)
        self.assertFalse(any("more than half" in f for f in out["findings"]))

    def test_snapover_is_reported_even_when_the_budget_holds(self):
        out = validate_power_loss_budget(
            [element(potential_v=250.0, dielectric_adjacent=True)], LEO, 5000.0
        )
        self.assertTrue(out["clause_8_3_met"])
        self.assertTrue(any("snapover" in f for f in out["findings"]))

    def test_tighter_allowable_fraction_can_fail_the_same_hardware(self):
        loose = validate_power_loss_budget([element()], LEO, 500.0, 0.01)
        tight = validate_power_loss_budget([element()], LEO, 500.0, 1e-9)
        self.assertTrue(loose["clause_8_3_met"])
        self.assertFalse(tight["clause_8_3_met"])

    def test_empty_element_list_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_loss_budget([], LEO, 500.0)

    def test_zero_generated_output_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_loss_budget([element()], LEO, 0.0)

    def test_zero_allowable_fraction_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_loss_budget([element()], LEO, 500.0, 0.0)

    def test_allowable_fraction_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_loss_budget([element()], LEO, 500.0, 1.5)

    def test_non_list_element_input_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_loss_budget(element(), LEO, 500.0)


if __name__ == "__main__":
    unittest.main()
