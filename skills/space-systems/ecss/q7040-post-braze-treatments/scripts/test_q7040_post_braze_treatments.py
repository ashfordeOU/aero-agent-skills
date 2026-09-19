#!/usr/bin/env python3
"""Contract test for post-braze cleaning, residue removal, passivation."""

import copy
import unittest

from q7040_post_braze_treatments_logic import (
    FLUX_BORAX_BORIC,
    FLUX_CHLORIDE,
    FLUX_FLUORIDE,
    FLUX_NONE,
    MATERIAL_ALUMINIUM_ALLOY,
    MATERIAL_AUSTENITIC_STAINLESS,
    MATERIAL_NICKEL_ALLOY,
    OP_CHEMICAL_REMOVAL,
    OP_DRYING,
    OP_HOT_WATER_QUENCH,
    OP_PASSIVATION,
    OP_RINSE_VERIFICATION,
    PROCESS_FURNACE_VACUUM,
    PROCESS_TORCH,
    VERDICT_INCOMPLETE,
    VERDICT_RELEASED,
    assess_final_rinse,
    assess_post_braze,
    flux_leaves_residue,
    missing_operations,
    passivation_applies,
    removal_window_hours,
    required_operations,
    residue_is_corrosive,
)

GOOD_CASE = {
    "part_id": "MAN-0042",
    "process": PROCESS_TORCH,
    "flux_type": FLUX_FLUORIDE,
    "base_material": MATERIAL_AUSTENITIC_STAINLESS,
    "operations_performed": required_operations(
        PROCESS_TORCH, FLUX_FLUORIDE, MATERIAL_AUSTENITIC_STAINLESS
    ),
    "hours_to_residue_removal": 2.0,
    "rinse_conductivity_us_per_cm": 1.2,
    "feed_conductivity_us_per_cm": 1.0,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class ResidueTests(unittest.TestCase):
    def test_a_flux_free_process_leaves_nothing_to_remove(self):
        self.assertFalse(flux_leaves_residue(FLUX_NONE))

    def test_halide_residues_are_the_corrosive_ones(self):
        self.assertTrue(residue_is_corrosive(FLUX_FLUORIDE))
        self.assertTrue(residue_is_corrosive(FLUX_CHLORIDE))
        self.assertFalse(residue_is_corrosive(FLUX_BORAX_BORIC))

    def test_a_corrosive_residue_gets_the_shortest_removal_window(self):
        self.assertLess(
            removal_window_hours(FLUX_CHLORIDE), removal_window_hours(FLUX_BORAX_BORIC)
        )

    def test_asking_a_flux_free_process_for_a_window_is_rejected(self):
        with self.assertRaises(ValueError):
            removal_window_hours(FLUX_NONE)

    def test_an_unknown_flux_name_is_rejected(self):
        with self.assertRaises(ValueError):
            flux_leaves_residue("the white paste")


class OperationSetTests(unittest.TestCase):
    def test_a_vacuum_cycle_on_nickel_owes_no_residue_removal(self):
        ops = required_operations(
            PROCESS_FURNACE_VACUUM, FLUX_NONE, MATERIAL_NICKEL_ALLOY
        )
        self.assertNotIn(OP_HOT_WATER_QUENCH, ops)
        self.assertNotIn(OP_CHEMICAL_REMOVAL, ops)
        self.assertIn(OP_DRYING, ops)

    def test_a_corrosive_residue_adds_the_chemical_removal_step(self):
        ops = required_operations(
            PROCESS_TORCH, FLUX_CHLORIDE, MATERIAL_ALUMINIUM_ALLOY
        )
        self.assertIn(OP_CHEMICAL_REMOVAL, ops)

    def test_a_borax_residue_is_lifted_without_a_chemical_step(self):
        ops = required_operations(
            PROCESS_TORCH, FLUX_BORAX_BORIC, MATERIAL_NICKEL_ALLOY
        )
        self.assertIn(OP_HOT_WATER_QUENCH, ops)
        self.assertNotIn(OP_CHEMICAL_REMOVAL, ops)

    def test_only_stainless_steel_owes_passivation(self):
        self.assertTrue(passivation_applies(MATERIAL_AUSTENITIC_STAINLESS))
        self.assertFalse(passivation_applies(MATERIAL_ALUMINIUM_ALLOY))
        self.assertIn(
            OP_PASSIVATION,
            required_operations(
                PROCESS_FURNACE_VACUUM, FLUX_NONE, MATERIAL_AUSTENITIC_STAINLESS
            ),
        )

    def test_removal_precedes_the_rinse_which_precedes_its_verification(self):
        ops = required_operations(
            PROCESS_TORCH, FLUX_FLUORIDE, MATERIAL_AUSTENITIC_STAINLESS
        )
        self.assertLess(ops.index(OP_CHEMICAL_REMOVAL), ops.index(OP_RINSE_VERIFICATION))
        self.assertLess(ops.index(OP_RINSE_VERIFICATION), ops.index(OP_PASSIVATION))

    def test_a_vacuum_cycle_declared_with_flux_is_a_contradiction(self):
        with self.assertRaises(ValueError):
            required_operations(
                PROCESS_FURNACE_VACUUM, FLUX_CHLORIDE, MATERIAL_NICKEL_ALLOY
            )

    def test_missing_operations_come_back_in_the_order_they_were_owed(self):
        ops = required_operations(
            PROCESS_TORCH, FLUX_FLUORIDE, MATERIAL_AUSTENITIC_STAINLESS
        )
        gaps = missing_operations(
            PROCESS_TORCH,
            FLUX_FLUORIDE,
            MATERIAL_AUSTENITIC_STAINLESS,
            [ops[0], ops[-1]],
        )
        self.assertEqual(gaps, ops[1:-1])

    def test_an_unknown_operation_name_in_the_record_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_operations(
                PROCESS_TORCH, FLUX_FLUORIDE, MATERIAL_NICKEL_ALLOY, ["gave it a wipe"]
            )


class RinseTests(unittest.TestCase):
    def test_a_rinse_at_the_feed_conductivity_is_acceptable(self):
        result = assess_final_rinse(1.0, 1.0)
        self.assertTrue(result["acceptable"])

    def test_a_rinse_exactly_on_the_allowance_is_acceptable(self):
        result = assess_final_rinse(1.5, 1.0)
        self.assertAlmostEqual(
            result["rinse_conductivity"], result["allowed_conductivity"], places=9
        )
        self.assertTrue(result["acceptable"])

    def test_a_rinse_well_over_the_allowance_is_rejected(self):
        result = assess_final_rinse(9.0, 1.0)
        self.assertFalse(result["acceptable"])
        self.assertGreater(result["excess_conductivity"], 7.0)

    def test_a_zero_feed_conductivity_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_final_rinse(1.0, 0.0)

    def test_a_ratio_limit_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_final_rinse(1.0, 1.0, 0.8)

    def test_a_non_numeric_rinse_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_final_rinse("clear", 1.0)


class AssessmentTests(unittest.TestCase):
    def test_a_fully_treated_part_is_released(self):
        result = assess_post_braze(_case())
        self.assertEqual(result["verdict"], VERDICT_RELEASED)
        self.assertEqual(result["findings"], [])

    def test_a_skipped_passivation_holds_the_part(self):
        ops = list(GOOD_CASE["operations_performed"])
        ops.remove(OP_PASSIVATION)
        result = assess_post_braze(_case(operations_performed=ops))
        self.assertEqual(result["verdict"], VERDICT_INCOMPLETE)
        self.assertIn(OP_PASSIVATION, result["missing_operations"])

    def test_removal_after_the_window_is_a_finding_even_when_recorded(self):
        result = assess_post_braze(_case(hours_to_residue_removal=30.0))
        self.assertFalse(result["released"])
        self.assertEqual(result["missing_operations"], [])

    def test_removal_exactly_on_the_window_is_not_late(self):
        result = assess_post_braze(_case(hours_to_residue_removal=8.0))
        self.assertAlmostEqual(
            result["hours_to_residue_removal"], result["removal_window_hours"], places=9
        )
        self.assertTrue(result["released"])

    def test_a_failing_rinse_holds_the_part(self):
        result = assess_post_braze(_case(rinse_conductivity_us_per_cm=12.0))
        self.assertEqual(result["verdict"], VERDICT_INCOMPLETE)
        self.assertFalse(result["final_rinse"]["acceptable"])

    def test_a_flux_free_vacuum_part_is_not_asked_for_a_rinse_reading(self):
        result = assess_post_braze(
            {
                "part_id": "MAN-0043",
                "process": PROCESS_FURNACE_VACUUM,
                "flux_type": FLUX_NONE,
                "base_material": MATERIAL_NICKEL_ALLOY,
                "operations_performed": required_operations(
                    PROCESS_FURNACE_VACUUM, FLUX_NONE, MATERIAL_NICKEL_ALLOY
                ),
            }
        )
        self.assertTrue(result["released"])
        self.assertIsNone(result["final_rinse"])
        self.assertIsNone(result["removal_window_hours"])

    def test_a_case_without_a_part_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_post_braze(_case(part_id=""))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_post_braze("we washed it")

    def test_a_fluxed_case_with_no_removal_timing_is_rejected(self):
        case = _case()
        del case["hours_to_residue_removal"]
        with self.assertRaises(ValueError):
            assess_post_braze(case)


if __name__ == "__main__":
    unittest.main()
