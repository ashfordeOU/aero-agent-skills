#!/usr/bin/env python3
"""Contract test for the Class 3 part and material restrictions (offline)."""

import copy
import math
import unittest

from q60_class_3_part_material_restrictions_logic import (
    HERMETIC_PACKAGES,
    MAX_COLLECTED_VOLATILE_PERCENT,
    MAX_TIN_MASS_FRACTION,
    MAX_TOTAL_MASS_LOSS_PERCENT,
    MOISTURE_FLOOR_LIFE_HOURS,
    PACKAGE_TYPES,
    PERMITTED,
    PERMITTED_WITH_MITIGATION,
    RATED_RELATIVE_HUMIDITY,
    RESTRICTED,
    RESTRICTED_METALS,
    TRACE_MASS_FRACTION,
    assess_moisture_control,
    assess_outgassing,
    assess_part_restrictions,
    assess_restricted_metal,
    assess_tin_finish,
    floor_life_consumption,
    humidity_acceleration,
    is_hermetic,
    rated_floor_life,
)

HERMETIC_CASE = {
    "part_reference": "voltage-reference-ceramic-8-lead",
    "package_type": "hermetic-ceramic",
    "finishes": [{"surface": "lead-finish", "tin_mass_fraction": 0.60}],
    "declared_metals": {"cadmium": 0.0},
}

PLASTIC_CASE = {
    "part_reference": "buck-converter-plastic-qfn-24",
    "package_type": "non-hermetic-plastic-moulded",
    "moisture_sensitivity_level": 3,
    "floor_exposure_hours": 24.0,
    "storage_relative_humidity": 45.0,
    "dry_packed_on_delivery": True,
    "bake_recorded": False,
    "finishes": [{"surface": "lead-finish", "tin_mass_fraction": 0.60}],
    "organics": [
        {
            "material": "epoxy-mould-compound",
            "total_mass_loss_percent": 0.42,
            "collected_volatile_percent": 0.02,
        }
    ],
    "declared_metals": {"zinc": 0.0},
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PackagingTests(unittest.TestCase):
    def test_ceramic_case_is_hermetic(self):
        self.assertTrue(is_hermetic("hermetic-ceramic"))

    def test_chip_scale_case_is_not_hermetic(self):
        self.assertFalse(is_hermetic("non-hermetic-chip-scale"))

    def test_hermetic_set_is_a_subset_of_the_package_types(self):
        self.assertTrue(HERMETIC_PACKAGES.issubset(set(PACKAGE_TYPES)))

    def test_unknown_package_type_rejected(self):
        with self.assertRaises(ValueError):
            is_hermetic("heat-shrink-sleeve")


class FloorLifeTests(unittest.TestCase):
    def test_level_one_carries_an_unlimited_floor_life(self):
        self.assertTrue(math.isinf(rated_floor_life(1)))

    def test_floor_life_shortens_as_the_level_rises(self):
        levels = sorted(key for key in MOISTURE_FLOOR_LIFE_HOURS if key > 1)
        lives = [MOISTURE_FLOOR_LIFE_HOURS[level] for level in levels]
        self.assertEqual(lives, sorted(lives, reverse=True))

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            rated_floor_life(9)

    def test_non_integer_level_rejected(self):
        with self.assertRaises(ValueError):
            rated_floor_life("3")

    def test_rated_humidity_does_not_accelerate_the_budget(self):
        self.assertAlmostEqual(
            humidity_acceleration(RATED_RELATIVE_HUMIDITY), 1.0, places=9
        )

    def test_dry_air_does_not_slow_the_budget_either(self):
        self.assertAlmostEqual(humidity_acceleration(20.0), 1.0, places=9)

    def test_damp_air_spends_the_budget_in_proportion(self):
        self.assertAlmostEqual(humidity_acceleration(90.0), 1.5, places=9)

    def test_humidity_over_one_hundred_rejected(self):
        with self.assertRaises(ValueError):
            humidity_acceleration(140.0)

    def test_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            floor_life_consumption(3, -4.0)

    def test_level_one_never_spends_a_budget(self):
        self.assertAlmostEqual(floor_life_consumption(1, 5000.0, 90.0), 0.0, places=9)

    def test_exposure_equal_to_the_floor_life_spends_it_exactly(self):
        self.assertAlmostEqual(floor_life_consumption(3, 168.0), 1.0, places=9)

    def test_damp_storage_spends_the_same_budget_sooner(self):
        self.assertAlmostEqual(floor_life_consumption(3, 112.0, 90.0), 1.0, places=9)


class MoistureControlTests(unittest.TestCase):
    def test_hermetic_case_closes_the_moisture_question(self):
        graded = assess_moisture_control(HERMETIC_CASE)
        self.assertTrue(graded["hermetic"])
        self.assertEqual(graded["verdict"], PERMITTED)
        self.assertIsNone(graded["floor_life_consumption"])

    def test_plastic_case_inside_its_budget_is_permitted_with_mitigation(self):
        graded = assess_moisture_control(PLASTIC_CASE)
        self.assertEqual(graded["verdict"], PERMITTED_WITH_MITIGATION)
        self.assertTrue(graded["acceptable"])
        self.assertAlmostEqual(graded["budget_remaining"], 1.0 - 24.0 / 168.0, places=9)

    def test_spent_budget_without_a_bake_is_restricted(self):
        graded = assess_moisture_control(
            _case(PLASTIC_CASE, floor_exposure_hours=200.0)
        )
        self.assertTrue(graded["bake_required"])
        self.assertEqual(graded["verdict"], RESTRICTED)

    def test_spent_budget_with_a_recorded_bake_is_acceptable(self):
        graded = assess_moisture_control(
            _case(PLASTIC_CASE, floor_exposure_hours=200.0, bake_recorded=True)
        )
        self.assertTrue(graded["acceptable"])
        self.assertEqual(graded["verdict"], PERMITTED_WITH_MITIGATION)

    def test_a_budget_landing_exactly_on_unity_asks_for_the_bake(self):
        graded = assess_moisture_control(
            _case(PLASTIC_CASE, floor_exposure_hours=168.0, storage_relative_humidity=60.0)
        )
        self.assertAlmostEqual(graded["floor_life_consumption"], 1.0, places=9)
        self.assertTrue(graded["bake_required"])

    def test_delivery_outside_a_dry_pack_is_a_finding(self):
        graded = assess_moisture_control(
            _case(PLASTIC_CASE, dry_packed_on_delivery=False)
        )
        self.assertFalse(graded["acceptable"])
        self.assertTrue(any("dry pack" in text for text in graded["findings"]))

    def test_missing_dry_pack_flag_rejected(self):
        case = copy.deepcopy(PLASTIC_CASE)
        del case["dry_packed_on_delivery"]
        with self.assertRaises(ValueError):
            assess_moisture_control(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_moisture_control("plastic")


class TinFinishTests(unittest.TestCase):
    def test_alloyed_finish_is_permitted(self):
        graded = assess_tin_finish({"surface": "lead-finish", "tin_mass_fraction": 0.60})
        self.assertEqual(graded["verdict"], PERMITTED)
        self.assertAlmostEqual(graded["whisker_margin"], 0.37, places=9)

    def test_finish_exactly_on_the_threshold_counts_as_near_pure(self):
        graded = assess_tin_finish(
            {"surface": "lead-finish", "tin_mass_fraction": MAX_TIN_MASS_FRACTION}
        )
        self.assertTrue(graded["near_pure_tin"])
        self.assertAlmostEqual(graded["whisker_margin"], 0.0, places=9)
        self.assertEqual(graded["verdict"], RESTRICTED)

    def test_near_pure_finish_with_a_solder_dip_is_permitted_with_mitigation(self):
        graded = assess_tin_finish(
            {
                "surface": "lead-finish",
                "tin_mass_fraction": 0.999,
                "mitigation": "hot-solder-dip",
            }
        )
        self.assertEqual(graded["verdict"], PERMITTED_WITH_MITIGATION)

    def test_unknown_mitigation_rejected(self):
        with self.assertRaises(ValueError):
            assess_tin_finish(
                {
                    "surface": "lead-finish",
                    "tin_mass_fraction": 0.999,
                    "mitigation": "hope",
                }
            )

    def test_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            assess_tin_finish({"surface": "lead-finish", "tin_mass_fraction": 1.2})


class OutgassingTests(unittest.TestCase):
    def test_a_clean_organic_passes_both_limits(self):
        graded = assess_outgassing(
            {
                "material": "silicone-conformal-coat",
                "total_mass_loss_percent": 0.30,
                "collected_volatile_percent": 0.01,
            }
        )
        self.assertTrue(graded["acceptable"])

    def test_a_material_on_both_limits_still_passes(self):
        graded = assess_outgassing(
            {
                "material": "die-attach-adhesive",
                "total_mass_loss_percent": MAX_TOTAL_MASS_LOSS_PERCENT,
                "collected_volatile_percent": MAX_COLLECTED_VOLATILE_PERCENT,
            }
        )
        self.assertTrue(graded["acceptable"])
        self.assertAlmostEqual(graded["total_mass_loss_margin"], 0.0, places=9)
        self.assertAlmostEqual(graded["collected_volatile_margin"], 0.0, places=9)

    def test_a_material_can_pass_mass_loss_and_fail_condensables(self):
        graded = assess_outgassing(
            {
                "material": "potting-compound",
                "total_mass_loss_percent": 0.40,
                "collected_volatile_percent": 0.35,
            }
        )
        self.assertFalse(graded["acceptable"])
        self.assertEqual(
            graded["binding_limit"], "collected-volatile-condensable-material"
        )

    def test_mass_loss_can_be_the_binding_limit(self):
        graded = assess_outgassing(
            {
                "material": "potting-compound",
                "total_mass_loss_percent": 0.95,
                "collected_volatile_percent": 0.01,
            }
        )
        self.assertEqual(graded["binding_limit"], "total-mass-loss")

    def test_negative_mass_loss_rejected(self):
        with self.assertRaises(ValueError):
            assess_outgassing(
                {
                    "material": "potting-compound",
                    "total_mass_loss_percent": -0.1,
                    "collected_volatile_percent": 0.01,
                }
            )

    def test_unnamed_material_rejected(self):
        with self.assertRaises(ValueError):
            assess_outgassing(
                {"total_mass_loss_percent": 0.4, "collected_volatile_percent": 0.01}
            )


class RestrictedMetalTests(unittest.TestCase):
    def test_absent_metal_is_permitted(self):
        graded = assess_restricted_metal("cadmium", 0.0)
        self.assertEqual(graded["verdict"], PERMITTED)

    def test_a_fraction_exactly_on_the_trace_is_still_a_trace(self):
        graded = assess_restricted_metal("zinc", TRACE_MASS_FRACTION)
        self.assertFalse(graded["present_above_trace"])
        self.assertEqual(graded["verdict"], PERMITTED)

    def test_metal_above_the_trace_without_a_deviation_is_restricted(self):
        graded = assess_restricted_metal("mercury", 0.004)
        self.assertEqual(graded["verdict"], RESTRICTED)

    def test_metal_above_the_trace_with_a_deviation_is_carried(self):
        graded = assess_restricted_metal("zinc", 0.004, "DEV-2026-007")
        self.assertEqual(graded["verdict"], PERMITTED_WITH_MITIGATION)

    def test_empty_deviation_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess_restricted_metal("zinc", 0.004, "   ")

    def test_unknown_metal_rejected(self):
        with self.assertRaises(ValueError):
            assess_restricted_metal("tungsten", 0.004)

    def test_every_restricted_metal_is_gradable(self):
        for metal in RESTRICTED_METALS:
            self.assertTrue(assess_restricted_metal(metal, 0.0)["acceptable"])


class PartAssessmentTests(unittest.TestCase):
    def test_clean_hermetic_part_is_permitted(self):
        result = assess_part_restrictions(HERMETIC_CASE)
        self.assertEqual(result["verdict"], PERMITTED)
        self.assertEqual(result["findings"], [])

    def test_clean_plastic_part_is_permitted_with_mitigation(self):
        result = assess_part_restrictions(PLASTIC_CASE)
        self.assertEqual(result["verdict"], PERMITTED_WITH_MITIGATION)
        self.assertTrue(result["required_mitigations"])

    def test_a_plastic_part_without_an_outgassing_entry_is_rejected(self):
        case = copy.deepcopy(PLASTIC_CASE)
        case["organics"] = []
        with self.assertRaises(ValueError):
            assess_part_restrictions(case)

    def test_a_failing_organic_blocks_the_part(self):
        case = copy.deepcopy(PLASTIC_CASE)
        case["organics"][0]["collected_volatile_percent"] = 0.6
        result = assess_part_restrictions(case)
        self.assertEqual(result["verdict"], RESTRICTED)

    def test_the_tightest_finish_is_reported(self):
        case = copy.deepcopy(PLASTIC_CASE)
        case["finishes"] = [
            {"surface": "lead-finish", "tin_mass_fraction": 0.60},
            {"surface": "lid-seal-ring", "tin_mass_fraction": 0.90},
        ]
        result = assess_part_restrictions(case)
        self.assertEqual(result["tightest_finish"], "lid-seal-ring")

    def test_a_duplicate_finish_surface_rejected(self):
        case = copy.deepcopy(PLASTIC_CASE)
        case["finishes"] = [
            {"surface": "lead-finish", "tin_mass_fraction": 0.60},
            {"surface": "lead-finish", "tin_mass_fraction": 0.90},
        ]
        with self.assertRaises(ValueError):
            assess_part_restrictions(case)

    def test_a_metal_that_is_not_restricted_cannot_be_declared(self):
        case = copy.deepcopy(HERMETIC_CASE)
        case["declared_metals"] = {"copper": 0.4}
        with self.assertRaises(ValueError):
            assess_part_restrictions(case)

    def test_missing_part_reference_rejected(self):
        case = copy.deepcopy(HERMETIC_CASE)
        del case["part_reference"]
        with self.assertRaises(ValueError):
            assess_part_restrictions(case)

    def test_every_finding_leaves_the_part_unacceptable(self):
        case = copy.deepcopy(PLASTIC_CASE)
        case["declared_metals"] = {"cadmium": 0.01}
        result = assess_part_restrictions(case)
        self.assertFalse(result["acceptable"])
        self.assertTrue(result["findings"])


if __name__ == "__main__":
    unittest.main(verbosity=0)
