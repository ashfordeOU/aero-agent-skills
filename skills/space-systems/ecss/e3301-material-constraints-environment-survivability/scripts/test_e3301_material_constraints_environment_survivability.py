#!/usr/bin/env python3
"""Contract test for the mechanism material constraint set (offline)."""

import copy
import unittest

from e3301_material_constraints_environment_survivability_logic import (
    CONSTRAINTS,
    CONTAINMENT_LEVELS,
    DEFAULT_CONSTRAINT_POLICY,
    assess_atomic_oxygen,
    assess_flammability,
    assess_fluid_compatibility,
    assess_fungus,
    assess_hazardous_material,
    assess_material_constraints,
    assess_radiation,
    assess_stray_light,
    atomic_oxygen_recession_m,
    oxygen_index_margin_points,
    radiation_capability_ratio,
    validate_constraint_policy,
)

GOOD_CASE = {
    "name": "hinge-liner-polymer",
    "is_fungus_nutrient": False,
    "fungus_treated": False,
    "humid_ground_storage": True,
    "limiting_oxygen_index_percent": 38.0,
    "environment_oxygen_percent": 21.0,
    "toxic": False,
    "unstable": False,
    "containment": "none",
    "habitable_volume": False,
    "in_optical_path": False,
    "reflectance": 0.6,
    "max_reflectance": 0.05,
    "degradation_threshold_krad": 200.0,
    "mission_dose_krad": 30.0,
    "erosion_yield_m3_per_atom": 3.0e-30,
    "atomic_oxygen_fluence_atoms_per_m2": 1.0e24,
    "allowable_recession_m": 1.0e-5,
    "atomic_oxygen_protected": False,
    "wetted_fluids": ["hydrazine"],
    "incompatible_fluids": ["liquid-oxygen"],
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_constraint_policy(DEFAULT_CONSTRAINT_POLICY),
            DEFAULT_CONSTRAINT_POLICY,
        )

    def test_all_seven_constraints_are_named(self):
        self.assertEqual(len(CONSTRAINTS), 7)
        self.assertIn("atomic-oxygen", CONSTRAINTS)

    def test_containment_levels_are_ordered_from_none(self):
        self.assertEqual(CONTAINMENT_LEVELS[0], "none")
        self.assertIn("sealed-containment", CONTAINMENT_LEVELS)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_constraint_policy("default")

    def test_radiation_margin_below_unity_rejected(self):
        broken = dict(DEFAULT_CONSTRAINT_POLICY)
        broken["radiation_design_margin"] = 0.5
        with self.assertRaises(ValueError):
            validate_constraint_policy(broken)

    def test_non_boolean_policy_flag_rejected(self):
        broken = dict(DEFAULT_CONSTRAINT_POLICY)
        broken["unstable_materials_prohibited"] = "yes"
        with self.assertRaises(ValueError):
            validate_constraint_policy(broken)


class FungusTests(unittest.TestCase):
    def test_a_non_nutrient_material_always_passes(self):
        self.assertTrue(assess_fungus(False, False, True)["acceptable"])

    def test_an_untreated_nutrient_in_humid_storage_fails(self):
        result = assess_fungus(True, False, True)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("untreated" in f for f in result["findings"]))

    def test_a_treated_nutrient_passes_with_the_treatment_recorded(self):
        result = assess_fungus(True, True, True)
        self.assertTrue(result["acceptable"])
        self.assertTrue(result["findings"])

    def test_a_nutrient_with_no_humid_storage_passes_conditionally(self):
        result = assess_fungus(True, False, False)
        self.assertTrue(result["acceptable"])
        self.assertTrue(any("humid" in f for f in result["findings"]))

    def test_non_boolean_nutrient_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_fungus("yes", False, True)


class FlammabilityTests(unittest.TestCase):
    def test_margin_is_the_difference_in_points(self):
        self.assertAlmostEqual(oxygen_index_margin_points(38.0, 21.0), 17.0, places=9)

    def test_a_high_index_material_passes_in_air(self):
        self.assertTrue(assess_flammability(38.0, 21.0)["acceptable"])

    def test_a_margin_exactly_on_the_requirement_passes(self):
        required = DEFAULT_CONSTRAINT_POLICY["required_oxygen_index_margin_points"]
        result = assess_flammability(21.0 + required, 21.0)
        self.assertAlmostEqual(result["margin_points"], required, places=9)
        self.assertTrue(result["acceptable"])

    def test_the_same_material_can_fail_an_enriched_atmosphere(self):
        self.assertTrue(assess_flammability(28.0, 21.0)["acceptable"])
        self.assertFalse(assess_flammability(28.0, 30.0)["acceptable"])

    def test_an_index_below_the_atmosphere_fails(self):
        result = assess_flammability(18.0, 21.0)
        self.assertFalse(result["acceptable"])
        self.assertLess(result["margin_points"], 0.0)

    def test_an_index_above_one_hundred_percent_rejected(self):
        with self.assertRaises(ValueError):
            oxygen_index_margin_points(120.0, 21.0)


class HazardTests(unittest.TestCase):
    def test_a_benign_material_passes(self):
        self.assertTrue(
            assess_hazardous_material(False, False, "none", True)["acceptable"]
        )

    def test_an_unstable_material_is_prohibited_everywhere(self):
        result = assess_hazardous_material(False, True, "sealed-containment", False)
        self.assertFalse(result["acceptable"])

    def test_a_toxic_material_in_a_habitable_volume_needs_sealing(self):
        self.assertFalse(
            assess_hazardous_material(True, False, "vented-enclosure", True)[
                "acceptable"
            ]
        )

    def test_a_sealed_toxic_material_in_a_habitable_volume_is_carried(self):
        result = assess_hazardous_material(True, False, "sealed-containment", True)
        self.assertTrue(result["acceptable"])
        self.assertTrue(any("sealed containment" in f for f in result["findings"]))

    def test_a_toxic_material_outside_a_habitable_volume_is_recorded(self):
        result = assess_hazardous_material(True, False, "none", False)
        self.assertTrue(result["acceptable"])
        self.assertTrue(result["findings"])

    def test_unknown_containment_level_rejected(self):
        with self.assertRaises(ValueError):
            assess_hazardous_material(True, False, "a-bag", True)


class StrayLightTests(unittest.TestCase):
    def test_a_surface_outside_the_optical_path_is_not_graded(self):
        self.assertTrue(assess_stray_light(False, 0.9, 0.05)["acceptable"])

    def test_a_dark_surface_in_the_path_passes(self):
        self.assertTrue(assess_stray_light(True, 0.02, 0.05)["acceptable"])

    def test_a_reflectance_exactly_on_the_limit_passes(self):
        self.assertTrue(assess_stray_light(True, 0.05, 0.05)["acceptable"])

    def test_a_bright_surface_in_the_path_fails(self):
        result = assess_stray_light(True, 0.6, 0.05)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("optical path" in f for f in result["findings"]))

    def test_a_reflectance_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            assess_stray_light(True, 1.4, 0.05)


class RadiationTests(unittest.TestCase):
    def test_ratio_folds_the_design_margin_into_the_dose(self):
        self.assertAlmostEqual(
            radiation_capability_ratio(200.0, 50.0), 2.0, places=9
        )

    def test_a_threshold_well_above_the_dose_passes(self):
        self.assertTrue(assess_radiation(200.0, 30.0)["acceptable"])

    def test_a_ratio_exactly_at_unity_passes(self):
        margin = DEFAULT_CONSTRAINT_POLICY["radiation_design_margin"]
        result = assess_radiation(30.0 * margin, 30.0)
        self.assertAlmostEqual(result["capability_ratio"], 1.0, places=9)
        self.assertTrue(result["acceptable"])

    def test_a_threshold_between_the_dose_and_the_margined_dose_fails(self):
        result = assess_radiation(40.0, 30.0)
        self.assertFalse(result["acceptable"])
        self.assertLess(result["capability_ratio"], 1.0)

    def test_zero_dose_rejected(self):
        with self.assertRaises(ValueError):
            radiation_capability_ratio(200.0, 0.0)


class AtomicOxygenTests(unittest.TestCase):
    def test_recession_is_erosion_yield_times_fluence(self):
        self.assertAlmostEqual(
            atomic_oxygen_recession_m(3.0e-30, 1.0e24), 3.0e-6, places=15
        )

    def test_a_zero_erosion_yield_loses_nothing(self):
        self.assertAlmostEqual(
            atomic_oxygen_recession_m(0.0, 1.0e24), 0.0, places=15
        )

    def test_recession_inside_the_budget_passes(self):
        self.assertTrue(
            assess_atomic_oxygen(3.0e-30, 1.0e24, 1.0e-5)["acceptable"]
        )

    def test_recession_exactly_on_the_budget_passes(self):
        result = assess_atomic_oxygen(3.0e-30, 1.0e24, 3.0e-6)
        self.assertAlmostEqual(result["recession_m"], 3.0e-6, places=15)
        self.assertTrue(result["acceptable"])

    def test_excess_recession_without_a_coating_fails(self):
        result = assess_atomic_oxygen(3.0e-30, 1.0e25, 1.0e-6)
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("no protective" in f for f in result["findings"]))

    def test_excess_recession_with_a_coating_is_carried_and_recorded(self):
        result = assess_atomic_oxygen(3.0e-30, 1.0e25, 1.0e-6, protected=True)
        self.assertTrue(result["acceptable"])
        self.assertTrue(any("protective coating" in f for f in result["findings"]))

    def test_a_negative_fluence_rejected(self):
        with self.assertRaises(ValueError):
            atomic_oxygen_recession_m(3.0e-30, -1.0)

    def test_a_zero_allowable_recession_rejected(self):
        with self.assertRaises(ValueError):
            assess_atomic_oxygen(3.0e-30, 1.0e24, 0.0)


class FluidCompatibilityTests(unittest.TestCase):
    def test_a_material_touching_nothing_it_dislikes_passes(self):
        self.assertTrue(
            assess_fluid_compatibility(["hydrazine"], ["liquid-oxygen"])["acceptable"]
        )

    def test_a_wetted_incompatible_fluid_fails(self):
        result = assess_fluid_compatibility(
            ["hydrazine", "liquid-oxygen"], ["liquid-oxygen"]
        )
        self.assertFalse(result["acceptable"])
        self.assertEqual(result["clashes"], ["liquid-oxygen"])

    def test_a_repeated_clash_is_reported_once(self):
        result = assess_fluid_compatibility(
            ["liquid-oxygen", "liquid-oxygen"], ["liquid-oxygen"]
        )
        self.assertEqual(result["clashes"], ["liquid-oxygen"])

    def test_an_unwetted_material_passes(self):
        self.assertTrue(assess_fluid_compatibility([], ["liquid-oxygen"])["acceptable"])

    def test_a_non_sequence_fluid_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_fluid_compatibility("hydrazine", ["liquid-oxygen"])

    def test_a_blank_fluid_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_fluid_compatibility(["  "], ["liquid-oxygen"])


class RollUpTests(unittest.TestCase):
    def test_a_clean_material_meets_every_constraint(self):
        result = assess_material_constraints(GOOD_CASE)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "constraints-met")
        self.assertEqual(result["violated"], [])

    def test_every_constraint_is_reported_by_name(self):
        result = assess_material_constraints(GOOD_CASE)
        self.assertEqual(set(result["constraints"]), set(CONSTRAINTS))

    def test_one_violated_constraint_names_itself(self):
        result = assess_material_constraints(
            _case(is_fungus_nutrient=True, fungus_treated=False)
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["violated"], ["fungus"])

    def test_several_violated_constraints_are_all_listed(self):
        result = assess_material_constraints(
            _case(in_optical_path=True, unstable=True)
        )
        self.assertIn("stray-light", result["violated"])
        self.assertIn("hazardous-material", result["violated"])

    def test_an_eroding_surface_is_caught_by_the_roll_up(self):
        result = assess_material_constraints(
            _case(atomic_oxygen_fluence_atoms_per_m2=1.0e26)
        )
        self.assertIn("atomic-oxygen", result["violated"])

    def test_a_wetted_clash_is_caught_by_the_roll_up(self):
        result = assess_material_constraints(
            _case(wetted_fluids=["liquid-oxygen"])
        )
        self.assertIn("fluid-compatibility", result["violated"])

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_material_constraints("polymer")

    def test_blank_material_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_material_constraints(_case(name="  "))

    def test_a_missing_dose_rejected(self):
        case = copy.deepcopy(GOOD_CASE)
        del case["mission_dose_krad"]
        with self.assertRaises(ValueError):
            assess_material_constraints(case)


if __name__ == "__main__":
    unittest.main()
