#!/usr/bin/env python3
"""Contract test for re-brazing and repair limits (offline)."""

import copy
import unittest

from q7040_rebrazing_and_repair_logic import (
    DEFECT_BASE_METAL_EROSION,
    DEFECT_FILLER_DEPLETION,
    DEFECT_INSUFFICIENT_FILLET,
    DEFECT_PARENT_CRACK,
    DEFECT_POROSITY,
    DISPOSITION_BOARD,
    DISPOSITION_REBRAZE,
    DISPOSITION_SCRAP,
    INSPECTION_METALLOGRAPHY,
    INSPECTION_PROOF,
    INSPECTION_RADIOGRAPHY,
    assess_repair,
    cumulative_dwell,
    cycle_limit,
    is_reflow_curable,
    reinspection_set,
    remaining_cycles,
    remaining_dwell_budget,
)


def _cycle(dwell, peak=1050.0, liquidus=1000.0):
    return {
        "dwell_minutes": dwell,
        "peak_temperature_c": peak,
        "liquidus_temperature_c": liquidus,
    }


GOOD_CASE = {
    "joint_id": "BRZ-014",
    "joint_category": "major",
    "defect": DEFECT_INSUFFICIENT_FILLET,
    "material_pair": "stainless-steel-nickel-filler",
    "thermal_history": [_cycle(6.0)],
    "planned_dwell_minutes": 6.0,
    "repair_procedure_qualified": True,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class DefectCurabilityTests(unittest.TestCase):
    def test_a_short_fillet_is_a_flow_defect_a_reflow_can_cure(self):
        self.assertTrue(is_reflow_curable(DEFECT_INSUFFICIENT_FILLET))

    def test_base_metal_erosion_is_not_curable_by_another_heating(self):
        self.assertFalse(is_reflow_curable(DEFECT_BASE_METAL_EROSION))

    def test_filler_depletion_and_a_parent_crack_are_not_curable(self):
        self.assertFalse(is_reflow_curable(DEFECT_FILLER_DEPLETION))
        self.assertFalse(is_reflow_curable(DEFECT_PARENT_CRACK))

    def test_an_unknown_defect_name_is_rejected(self):
        with self.assertRaises(ValueError):
            is_reflow_curable("it looked a bit rough")


class CycleBudgetTests(unittest.TestCase):
    def test_a_critical_joint_gets_the_fewest_repair_cycles(self):
        self.assertLess(cycle_limit("critical"), cycle_limit("major"))
        self.assertLess(cycle_limit("major"), cycle_limit("minor"))

    def test_remaining_cycles_falls_to_zero_and_never_below(self):
        self.assertEqual(remaining_cycles("minor", 0), 3)
        self.assertEqual(remaining_cycles("minor", 3), 0)
        self.assertEqual(remaining_cycles("minor", 9), 0)

    def test_a_negative_cycle_count_is_rejected(self):
        with self.assertRaises(ValueError):
            remaining_cycles("major", -1)

    def test_a_non_integer_cycle_count_is_rejected(self):
        with self.assertRaises(ValueError):
            remaining_cycles("major", 1.5)


class ThermalBudgetTests(unittest.TestCase):
    def test_cumulative_dwell_adds_every_excursion(self):
        self.assertAlmostEqual(
            cumulative_dwell([_cycle(5.0), _cycle(7.5)]), 12.5, places=9
        )

    def test_an_empty_history_has_spent_nothing(self):
        self.assertAlmostEqual(cumulative_dwell([]), 0.0, places=9)

    def test_a_cycle_that_never_reached_liquidus_is_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_dwell([_cycle(5.0, peak=980.0, liquidus=1000.0)])

    def test_a_negative_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_dwell([_cycle(-1.0)])

    def test_a_history_that_is_not_a_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            cumulative_dwell("two runs through the furnace")

    def test_aluminium_has_the_tightest_dwell_budget(self):
        empty = []
        self.assertLess(
            remaining_dwell_budget("aluminium-alloy-aluminium-filler", empty),
            remaining_dwell_budget("nickel-alloy-nickel-filler", empty),
        )

    def test_remaining_budget_is_the_budget_less_what_was_spent(self):
        self.assertAlmostEqual(
            remaining_dwell_budget(
                "stainless-steel-nickel-filler", [_cycle(10.0), _cycle(5.0)]
            ),
            15.0,
            places=9,
        )

    def test_an_unknown_material_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            remaining_dwell_budget("some-alloy-and-some-filler", [])


class ReinspectionTests(unittest.TestCase):
    def test_a_critical_repair_owes_radiography_and_a_proof_test(self):
        required = reinspection_set("critical", 1)
        self.assertIn(INSPECTION_RADIOGRAPHY, required)
        self.assertIn(INSPECTION_PROOF, required)

    def test_a_minor_repair_owes_neither_radiography_nor_a_proof_test(self):
        required = reinspection_set("minor", 1)
        self.assertNotIn(INSPECTION_RADIOGRAPHY, required)
        self.assertNotIn(INSPECTION_PROOF, required)

    def test_the_last_permitted_cycle_adds_a_destructive_check(self):
        self.assertIn(INSPECTION_METALLOGRAPHY, reinspection_set("major", 2))
        self.assertNotIn(INSPECTION_METALLOGRAPHY, reinspection_set("major", 1))

    def test_a_zero_cycle_repair_is_a_contradiction_and_is_rejected(self):
        with self.assertRaises(ValueError):
            reinspection_set("major", 0)


class DispositionTests(unittest.TestCase):
    def test_a_curable_defect_inside_both_budgets_is_repaired(self):
        result = assess_repair(_case())
        self.assertEqual(result["disposition"], DISPOSITION_REBRAZE)
        self.assertEqual(result["findings"], [])

    def test_a_repaired_joint_is_handed_back_with_its_reinspection_set(self):
        result = assess_repair(_case())
        self.assertIn(INSPECTION_RADIOGRAPHY, result["reinspection_required"])

    def test_erosion_sends_the_part_to_remake_not_to_the_board(self):
        result = assess_repair(_case(defect=DEFECT_BASE_METAL_EROSION))
        self.assertEqual(result["disposition"], DISPOSITION_SCRAP)

    def test_an_exhausted_cycle_count_goes_to_the_board(self):
        result = assess_repair(
            _case(
                joint_category="critical",
                thermal_history=[_cycle(4.0), _cycle(4.0)],
            )
        )
        self.assertEqual(result["disposition"], DISPOSITION_BOARD)
        self.assertEqual(result["remaining_cycles"], 0)

    def test_an_unqualified_repair_procedure_goes_to_the_board(self):
        result = assess_repair(_case(repair_procedure_qualified=False))
        self.assertEqual(result["disposition"], DISPOSITION_BOARD)

    def test_a_dwell_overshoot_outranks_the_cycle_count_and_scraps(self):
        result = assess_repair(
            _case(
                material_pair="aluminium-alloy-aluminium-filler",
                planned_dwell_minutes=9.0,
                thermal_history=[_cycle(5.0)],
            )
        )
        self.assertTrue(result["dwell_budget_exceeded"])
        self.assertEqual(result["disposition"], DISPOSITION_SCRAP)

    def test_landing_exactly_on_the_dwell_budget_is_not_an_overshoot(self):
        result = assess_repair(
            _case(
                material_pair="aluminium-alloy-aluminium-filler",
                planned_dwell_minutes=7.0,
                thermal_history=[_cycle(5.0)],
            )
        )
        self.assertAlmostEqual(
            result["projected_dwell_minutes"],
            result["dwell_budget_minutes"],
            places=9,
        )
        self.assertFalse(result["dwell_budget_exceeded"])
        self.assertEqual(result["disposition"], DISPOSITION_REBRAZE)

    def test_a_first_braze_history_counts_as_zero_repair_cycles(self):
        result = assess_repair(_case(thermal_history=[_cycle(6.0)]))
        self.assertEqual(result["cycles_used"], 0)

    def test_every_finding_is_reported_not_just_the_deciding_one(self):
        result = assess_repair(
            _case(
                defect=DEFECT_PARENT_CRACK,
                repair_procedure_qualified=False,
                joint_category="critical",
                thermal_history=[_cycle(4.0), _cycle(4.0)],
            )
        )
        self.assertEqual(len(result["findings"]), 3)
        self.assertEqual(result["disposition"], DISPOSITION_SCRAP)

    def test_a_scrapped_joint_is_given_no_reinspection_set(self):
        result = assess_repair(_case(defect=DEFECT_FILLER_DEPLETION))
        self.assertEqual(result["reinspection_required"], [])

    def test_porosity_on_a_minor_joint_is_repairable_three_times(self):
        result = assess_repair(
            _case(
                joint_category="minor",
                defect=DEFECT_POROSITY,
                thermal_history=[_cycle(2.0), _cycle(2.0), _cycle(2.0)],
            )
        )
        self.assertEqual(result["disposition"], DISPOSITION_REBRAZE)
        self.assertEqual(result["remaining_cycles"], 1)

    def test_a_case_without_a_joint_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_repair(_case(joint_id="  "))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_repair("re-run it through the furnace")

    def test_a_non_boolean_qualification_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_repair(_case(repair_procedure_qualified="yes"))


if __name__ == "__main__":
    unittest.main()
