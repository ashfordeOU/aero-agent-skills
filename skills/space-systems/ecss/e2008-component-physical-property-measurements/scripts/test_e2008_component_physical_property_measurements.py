#!/usr/bin/env python3
"""Contract test for the array property determination leaf (offline)."""

import copy
import math
import unittest

from e2008_component_physical_property_measurements_logic import (
    ALL_PROPERTIES,
    COMPONENT_CATEGORIES,
    DETERMINED_VERDICT,
    MECHANICAL_PROPERTIES,
    OUTSTANDING_VERDICT,
    PROPERTY_BOUNDS,
    THERMAL_PROPERTIES,
    absorptance_to_emittance_ratio,
    assess_property_dataset,
    bonded_pair_thermal_stress,
    determination_completeness,
    missing_properties,
    property_group,
    property_unit,
    required_properties,
    specific_stiffness,
    surplus_properties,
    temperature_coverage,
    thermal_diffusivity,
    validate_dataset,
    validate_property_value,
    validate_temperature_band,
)

COVERGLASS_PROPERTIES = {
    "solar-absorptance": 0.09,
    "infrared-emittance": 0.85,
    "coefficient-of-thermal-expansion": 3.2e-6,
    "density": 2550.0,
    "youngs-modulus": 7.4e10,
    "poissons-ratio": 0.22,
}

COVERGLASS_CASE = {
    "component_category": "coverglass",
    "declared_properties": COVERGLASS_PROPERTIES,
    "determined_temperature_band_k": {"minimum_k": 100.0, "maximum_k": 420.0},
    "mission_temperature_band_k": {"minimum_k": 123.15, "maximum_k": 393.15},
}


def _case(**overrides):
    case = copy.deepcopy(COVERGLASS_CASE)
    case.update(overrides)
    return case


def _properties_without(name):
    dataset = dict(COVERGLASS_PROPERTIES)
    del dataset[name]
    return dataset


class PropertyGroupingTests(unittest.TestCase):
    def test_radiative_properties_are_grouped_as_thermal(self):
        self.assertEqual(property_group("solar-absorptance"), "thermal")
        self.assertEqual(property_group("coefficient-of-thermal-expansion"), "thermal")

    def test_structural_properties_are_grouped_as_mechanical(self):
        self.assertEqual(property_group("youngs-modulus"), "mechanical")
        self.assertEqual(property_group("tensile-strength"), "mechanical")

    def test_every_property_falls_in_exactly_one_group(self):
        self.assertEqual(
            set(THERMAL_PROPERTIES) & set(MECHANICAL_PROPERTIES), set()
        )
        for name in ALL_PROPERTIES:
            self.assertIn(property_group(name), ("thermal", "mechanical"))

    def test_unknown_property_has_no_group(self):
        with self.assertRaises(ValueError):
            property_group("bandgap")

    def test_every_property_declares_a_unit_and_a_band(self):
        for name in ALL_PROPERTIES:
            self.assertIn(name, PROPERTY_BOUNDS)
            self.assertIsInstance(property_unit(name), str)


class RequiredPropertyTests(unittest.TestCase):
    def test_an_optical_coating_needs_the_radiative_pair(self):
        required = required_properties("optical-coating")
        self.assertIn("solar-absorptance", required)
        self.assertIn("infrared-emittance", required)

    def test_a_facesheet_needs_the_full_mechanical_set(self):
        required = required_properties("substrate-facesheet")
        for name in MECHANICAL_PROPERTIES:
            self.assertIn(name, required)

    def test_every_category_requires_at_least_one_thermal_property(self):
        for category in COMPONENT_CATEGORIES:
            required = required_properties(category)
            self.assertTrue(set(required) & set(THERMAL_PROPERTIES))

    def test_every_required_property_is_a_known_property(self):
        for category in COMPONENT_CATEGORIES:
            for name in required_properties(category):
                self.assertIn(name, ALL_PROPERTIES)

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            required_properties("hinge-bracket")


class ValueValidationTests(unittest.TestCase):
    def test_a_value_on_the_upper_bound_is_accepted(self):
        self.assertAlmostEqual(
            validate_property_value("infrared-emittance", 1.0), 1.0, places=9
        )

    def test_a_value_above_the_upper_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_value("infrared-emittance", 1.2)

    def test_a_negative_absorptance_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_value("solar-absorptance", -0.05)

    def test_a_slightly_negative_expansion_coefficient_is_accepted(self):
        self.assertAlmostEqual(
            validate_property_value("coefficient-of-thermal-expansion", -2.0e-6),
            -2.0e-6,
            places=12,
        )

    def test_an_incompressible_poisson_ratio_is_the_upper_bound(self):
        self.assertAlmostEqual(
            validate_property_value("poissons-ratio", 0.5), 0.5, places=9
        )

    def test_a_poisson_ratio_above_one_half_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_value("poissons-ratio", 0.6)

    def test_a_boolean_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_value("density", True)

    def test_a_string_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_value("density", "2550 kg/m3")

    def test_a_non_finite_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_value("youngs-modulus", float("inf"))

    def test_an_unknown_property_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_property_value("fracture-toughness", 1.0)

    def test_a_dataset_with_an_unknown_property_rejected(self):
        dataset = dict(COVERGLASS_PROPERTIES)
        dataset["bandgap-ev"] = 1.1
        with self.assertRaises(ValueError):
            validate_dataset("coverglass", dataset)

    def test_a_non_mapping_dataset_rejected(self):
        with self.assertRaises(ValueError):
            validate_dataset("coverglass", [0.09, 0.85])


class CompletenessTests(unittest.TestCase):
    def test_a_full_coverglass_dataset_is_complete(self):
        self.assertEqual(missing_properties("coverglass", COVERGLASS_PROPERTIES), ())
        self.assertAlmostEqual(
            determination_completeness("coverglass", COVERGLASS_PROPERTIES),
            1.0,
            places=9,
        )

    def test_a_dropped_value_is_named_as_missing(self):
        dataset = _properties_without("poissons-ratio")
        self.assertEqual(
            missing_properties("coverglass", dataset), ("poissons-ratio",)
        )

    def test_a_dropped_value_lowers_the_completeness(self):
        dataset = _properties_without("poissons-ratio")
        self.assertAlmostEqual(
            determination_completeness("coverglass", dataset), 5.0 / 6.0, places=9
        )

    def test_a_value_not_required_is_reported_as_surplus(self):
        dataset = dict(COVERGLASS_PROPERTIES)
        dataset["specific-heat"] = 750.0
        self.assertEqual(surplus_properties("coverglass", dataset), ("specific-heat",))

    def test_a_surplus_value_does_not_raise_the_completeness(self):
        dataset = dict(COVERGLASS_PROPERTIES)
        dataset["specific-heat"] = 750.0
        self.assertAlmostEqual(
            determination_completeness("coverglass", dataset), 1.0, places=9
        )


class TemperatureBandTests(unittest.TestCase):
    def test_a_band_enveloping_the_mission_is_covered(self):
        coverage = temperature_coverage(
            {"minimum_k": 100.0, "maximum_k": 420.0},
            {"minimum_k": 123.15, "maximum_k": 393.15},
        )
        self.assertTrue(coverage["covered"])
        self.assertAlmostEqual(coverage["cold_shortfall_k"], 0.0, places=9)
        self.assertAlmostEqual(coverage["hot_shortfall_k"], 0.0, places=9)

    def test_a_band_matching_the_mission_exactly_is_covered(self):
        band = {"minimum_k": 123.15, "maximum_k": 393.15}
        coverage = temperature_coverage(dict(band), dict(band))
        self.assertTrue(coverage["covered"])
        self.assertAlmostEqual(coverage["determined_span_k"], 270.0, places=9)

    def test_a_band_stopping_short_of_the_cold_limit_is_sized(self):
        coverage = temperature_coverage(
            {"minimum_k": 173.15, "maximum_k": 420.0},
            {"minimum_k": 123.15, "maximum_k": 393.15},
        )
        self.assertFalse(coverage["covered"])
        self.assertAlmostEqual(coverage["cold_shortfall_k"], 50.0, places=9)
        self.assertAlmostEqual(coverage["hot_shortfall_k"], 0.0, places=9)

    def test_a_band_stopping_short_of_the_hot_limit_is_sized(self):
        coverage = temperature_coverage(
            {"minimum_k": 100.0, "maximum_k": 353.15},
            {"minimum_k": 123.15, "maximum_k": 393.15},
        )
        self.assertFalse(coverage["covered"])
        self.assertAlmostEqual(coverage["hot_shortfall_k"], 40.0, places=9)

    def test_an_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_band(
                "determined band", {"minimum_k": 420.0, "maximum_k": 100.0}
            )

    def test_a_band_at_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_band(
                "determined band", {"minimum_k": 0.0, "maximum_k": 300.0}
            )

    def test_a_band_missing_a_limit_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_band("determined band", {"minimum_k": 100.0})

    def test_a_non_mapping_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_band("determined band", (100.0, 420.0))


class DerivedQuantityTests(unittest.TestCase):
    def test_radiative_ratio_of_a_coverglass_is_well_below_one(self):
        ratio = absorptance_to_emittance_ratio(0.09, 0.85)
        self.assertAlmostEqual(ratio, 0.09 / 0.85, places=12)
        self.assertLess(ratio, 0.5)

    def test_a_higher_emittance_lowers_the_radiative_ratio(self):
        self.assertLess(
            absorptance_to_emittance_ratio(0.09, 0.95),
            absorptance_to_emittance_ratio(0.09, 0.75),
        )

    def test_a_zero_emittance_cannot_form_a_ratio(self):
        with self.assertRaises(ValueError):
            absorptance_to_emittance_ratio(0.09, 0.0)

    def test_thermal_diffusivity_follows_from_the_three_values(self):
        value = thermal_diffusivity(0.2, 1200.0, 1100.0)
        self.assertAlmostEqual(value, 0.2 / (1200.0 * 1100.0), places=15)

    def test_specific_stiffness_rewards_a_light_facesheet(self):
        light = specific_stiffness(7.0e10, 1600.0)
        heavy = specific_stiffness(7.0e10, 2700.0)
        self.assertGreater(light, heavy)

    def test_specific_stiffness_value_is_the_modulus_over_density(self):
        self.assertAlmostEqual(
            specific_stiffness(7.4e10, 2550.0), 7.4e10 / 2550.0, places=6
        )

    def test_a_bonded_pair_with_no_mismatch_carries_no_stress(self):
        result = bonded_pair_thermal_stress(3.2e-6, 3.2e-6, 200.0, 7.4e10, 5.0e7)
        self.assertAlmostEqual(result["mismatch_strain"], 0.0, places=15)
        self.assertAlmostEqual(result["stress_pa"], 0.0, places=9)
        self.assertTrue(math.isinf(result["margin_of_safety"]))
        self.assertTrue(result["adequate"])

    def test_a_mismatched_pair_over_a_deep_cycle_builds_stress(self):
        result = bonded_pair_thermal_stress(2.3e-5, 3.2e-6, 200.0, 7.4e10, 5.0e7)
        self.assertAlmostEqual(
            result["mismatch_strain"], (2.3e-5 - 3.2e-6) * 200.0, places=12
        )
        self.assertGreater(result["stress_pa"], 1.0e8)
        self.assertFalse(result["adequate"])

    def test_the_stress_is_unsigned_for_a_cooling_excursion(self):
        warming = bonded_pair_thermal_stress(2.3e-5, 3.2e-6, 200.0, 7.4e10)
        cooling = bonded_pair_thermal_stress(2.3e-5, 3.2e-6, -200.0, 7.4e10)
        self.assertAlmostEqual(warming["stress_pa"], cooling["stress_pa"], places=6)
        self.assertLess(cooling["mismatch_strain"], 0.0)

    def test_without_an_allowable_no_margin_is_reported(self):
        result = bonded_pair_thermal_stress(2.3e-5, 3.2e-6, 200.0, 7.4e10)
        self.assertIsNone(result["margin_of_safety"])
        self.assertIsNone(result["adequate"])

    def test_a_non_numeric_temperature_change_rejected(self):
        with self.assertRaises(ValueError):
            bonded_pair_thermal_stress(2.3e-5, 3.2e-6, "200 K", 7.4e10)


class AssessmentTests(unittest.TestCase):
    def test_a_complete_coverglass_dataset_passes(self):
        result = assess_property_dataset(COVERGLASS_CASE)
        self.assertEqual(result["verdict"], DETERMINED_VERDICT)
        self.assertTrue(result["complete"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["determination_completeness"], 1.0, places=9)

    def test_the_radiative_ratio_is_carried_into_the_result(self):
        result = assess_property_dataset(COVERGLASS_CASE)
        self.assertAlmostEqual(
            result["absorptance_to_emittance_ratio"], 0.09 / 0.85, places=12
        )
        self.assertAlmostEqual(
            result["specific_stiffness_m2_s2"], 7.4e10 / 2550.0, places=6
        )

    def test_a_missing_value_holds_the_verdict_open(self):
        result = assess_property_dataset(
            _case(declared_properties=_properties_without("youngs-modulus"))
        )
        self.assertEqual(result["verdict"], OUTSTANDING_VERDICT)
        self.assertEqual(result["missing_properties"], ("youngs-modulus",))
        self.assertTrue(any("has not been determined" in f for f in result["findings"]))
        self.assertIsNone(result["specific_stiffness_m2_s2"])

    def test_a_short_determined_band_holds_the_verdict_open(self):
        result = assess_property_dataset(
            _case(determined_temperature_band_k={"minimum_k": 200.0, "maximum_k": 420.0})
        )
        self.assertEqual(result["verdict"], OUTSTANDING_VERDICT)
        self.assertTrue(any("cold mission limit" in f for f in result["findings"]))

    def test_a_surplus_value_is_recorded_without_blocking_the_verdict(self):
        dataset = dict(COVERGLASS_PROPERTIES)
        dataset["specific-heat"] = 750.0
        result = assess_property_dataset(_case(declared_properties=dataset))
        self.assertEqual(result["verdict"], DETERMINED_VERDICT)
        self.assertEqual(result["surplus_properties"], ("specific-heat",))
        self.assertTrue(any("kept for record" in f for f in result["findings"]))

    def test_an_optical_coating_reports_no_specific_stiffness(self):
        result = assess_property_dataset(
            {
                "component_category": "optical-coating",
                "declared_properties": {
                    "solar-absorptance": 0.2,
                    "infrared-emittance": 0.8,
                    "coefficient-of-thermal-expansion": 1.1e-5,
                },
                "determined_temperature_band_k": {
                    "minimum_k": 100.0,
                    "maximum_k": 420.0,
                },
                "mission_temperature_band_k": {
                    "minimum_k": 123.15,
                    "maximum_k": 393.15,
                },
            }
        )
        self.assertEqual(result["verdict"], DETERMINED_VERDICT)
        self.assertIsNone(result["specific_stiffness_m2_s2"])
        self.assertAlmostEqual(
            result["absorptance_to_emittance_ratio"], 0.25, places=9
        )

    def test_an_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            assess_property_dataset(_case(component_category="yoke"))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_property_dataset("coverglass")

    def test_a_case_without_a_mission_band_rejected(self):
        case = _case()
        del case["mission_temperature_band_k"]
        with self.assertRaises(ValueError):
            assess_property_dataset(case)

    def test_an_out_of_band_declared_value_rejected(self):
        dataset = dict(COVERGLASS_PROPERTIES)
        dataset["infrared-emittance"] = 1.4
        with self.assertRaises(ValueError):
            assess_property_dataset(_case(declared_properties=dataset))


if __name__ == "__main__":
    unittest.main()
