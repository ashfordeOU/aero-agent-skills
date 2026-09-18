#!/usr/bin/env python3
"""Contract test for anodize stripping and re-anodizing rules (offline)."""

import copy
import unittest

from q7003_stripping_and_re_anodizing_logic import (
    ALLOY_CLASSES,
    BINDING_CLADDING,
    BINDING_DIMENSION,
    BINDING_POLICY,
    DEFAULT_REWORK_POLICY,
    REWORK_CONCESSION,
    REWORK_FINAL_CYCLE,
    REWORK_PERMITTED,
    REWORK_SCRAP,
    assess_rework,
    cycles_remaining_by_cladding,
    cycles_remaining_by_dimension,
    cycles_remaining_by_policy,
    dimension_after_cycles,
    metal_loss_per_cycle_mm,
    validate_rework_policy,
)

GOOD_CASE = {
    "alloy_class": "bare-standard",
    "current_mm": 5.000,
    "minimum_mm": 4.900,
    "loss_per_surface_um": 10.0,
    "treated_surfaces": 2,
    "cycles_completed": 0,
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_rework_policy(DEFAULT_REWORK_POLICY), DEFAULT_REWORK_POLICY
        )

    def test_policy_covers_every_alloy_class(self):
        for alloy in ALLOY_CLASSES:
            self.assertIn(alloy, DEFAULT_REWORK_POLICY["max_cycles"])

    def test_high_strength_alloy_gets_the_tightest_ceiling(self):
        table = DEFAULT_REWORK_POLICY["max_cycles"]
        self.assertLess(table["high-strength"], table["bare-standard"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_rework_policy("default")

    def test_policy_missing_an_alloy_rejected(self):
        broken = copy.deepcopy(DEFAULT_REWORK_POLICY)
        del broken["max_cycles"]["clad-sheet"]
        with self.assertRaises(ValueError):
            validate_rework_policy(broken)

    def test_policy_with_a_non_integer_ceiling_rejected(self):
        broken = copy.deepcopy(DEFAULT_REWORK_POLICY)
        broken["max_cycles"]["bare-standard"] = 2.5
        with self.assertRaises(ValueError):
            validate_rework_policy(broken)


class MetalLossTests(unittest.TestCase):
    def test_two_surfaces_cost_twice_one(self):
        self.assertAlmostEqual(
            metal_loss_per_cycle_mm(10.0, 2),
            2.0 * metal_loss_per_cycle_mm(10.0, 1),
            places=12,
        )

    def test_loss_converts_micrometres_to_millimetres(self):
        self.assertAlmostEqual(metal_loss_per_cycle_mm(10.0, 1), 0.010, places=12)

    def test_more_than_two_surfaces_rejected(self):
        with self.assertRaises(ValueError):
            metal_loss_per_cycle_mm(10.0, 3)

    def test_zero_surfaces_rejected(self):
        with self.assertRaises(ValueError):
            metal_loss_per_cycle_mm(10.0, 0)

    def test_zero_loss_rejected(self):
        with self.assertRaises(ValueError):
            metal_loss_per_cycle_mm(0.0, 1)

    def test_dimension_shrinks_with_each_cycle(self):
        self.assertAlmostEqual(
            dimension_after_cycles(5.0, 3, 10.0, 2), 5.0 - 0.06, places=12
        )

    def test_zero_cycles_leave_the_dimension_alone(self):
        self.assertAlmostEqual(
            dimension_after_cycles(5.0, 0, 10.0, 2), 5.0, places=12
        )


class DimensionLimitTests(unittest.TestCase):
    def test_budget_divides_into_whole_cycles(self):
        self.assertEqual(cycles_remaining_by_dimension(5.0, 4.90, 10.0, 2), 5)

    def test_a_budget_landing_exactly_on_a_cycle_keeps_that_cycle(self):
        # 0.1 mm of allowance at 0.02 mm per cycle is exactly five cycles,
        # and the division lands one unit in the last place below it.
        budget = 4.90 + 0.10
        self.assertEqual(cycles_remaining_by_dimension(budget, 4.90, 10.0, 2), 5)

    def test_a_part_on_its_minimum_has_no_cycles_left(self):
        self.assertEqual(cycles_remaining_by_dimension(4.90, 4.90, 10.0, 2), 0)

    def test_a_deeper_cut_leaves_fewer_cycles(self):
        shallow = cycles_remaining_by_dimension(5.0, 4.90, 10.0, 1)
        deep = cycles_remaining_by_dimension(5.0, 4.90, 10.0, 2)
        self.assertGreater(shallow, deep)

    def test_a_part_already_undersize_rejected(self):
        with self.assertRaises(ValueError):
            cycles_remaining_by_dimension(4.80, 4.90, 10.0, 2)

    def test_non_numeric_dimension_rejected(self):
        with self.assertRaises(ValueError):
            cycles_remaining_by_dimension("5 mm", 4.90, 10.0, 2)


class PolicyLimitTests(unittest.TestCase):
    def test_a_fresh_part_has_the_full_ceiling(self):
        self.assertEqual(cycles_remaining_by_policy(0, "bare-standard"), 3)

    def test_each_completed_cycle_consumes_one(self):
        self.assertEqual(cycles_remaining_by_policy(2, "bare-standard"), 1)

    def test_the_ceiling_never_goes_negative(self):
        self.assertEqual(cycles_remaining_by_policy(9, "high-strength"), 0)

    def test_unknown_alloy_class_rejected(self):
        with self.assertRaises(ValueError):
            cycles_remaining_by_policy(0, "titanium")

    def test_negative_completed_cycles_rejected(self):
        with self.assertRaises(ValueError):
            cycles_remaining_by_policy(-1, "bare-standard")


class CladdingLimitTests(unittest.TestCase):
    def test_a_bare_alloy_carries_no_cladding_limit(self):
        self.assertIsNone(
            cycles_remaining_by_cladding("bare-standard", None, 10.0, 1)
        )

    def test_clad_thickness_divides_into_cycles(self):
        self.assertEqual(
            cycles_remaining_by_cladding("clad-sheet", 45.0, 10.0, 1), 4
        )

    def test_clad_thickness_exactly_on_a_cycle_keeps_that_cycle(self):
        self.assertEqual(
            cycles_remaining_by_cladding("clad-sheet", 40.0, 10.0, 1), 4
        )

    def test_a_consumed_cladding_leaves_no_cycles(self):
        self.assertEqual(
            cycles_remaining_by_cladding("clad-sheet", 0.0, 10.0, 1), 0
        )

    def test_a_clad_part_without_a_clad_thickness_rejected(self):
        with self.assertRaises(ValueError):
            cycles_remaining_by_cladding("clad-sheet", None, 10.0, 1)

    def test_negative_clad_thickness_rejected(self):
        with self.assertRaises(ValueError):
            cycles_remaining_by_cladding("clad-sheet", -5.0, 10.0, 1)


class AssessReworkTests(unittest.TestCase):
    def test_a_fresh_part_with_room_is_permitted(self):
        result = assess_rework(GOOD_CASE)
        self.assertEqual(result["disposition"], REWORK_PERMITTED)
        self.assertEqual(result["cycles_remaining"], 3)
        self.assertEqual(result["binding_limits"], [BINDING_POLICY])

    def test_the_tightest_limit_governs(self):
        result = assess_rework(_case(current_mm=4.92))
        self.assertEqual(result["cycles_remaining"], 1)
        self.assertEqual(result["binding_limits"], [BINDING_DIMENSION])
        self.assertEqual(result["disposition"], REWORK_FINAL_CYCLE)

    def test_a_part_out_of_metal_is_scrap_not_a_concession(self):
        result = assess_rework(_case(current_mm=4.90))
        self.assertEqual(result["disposition"], REWORK_SCRAP)
        self.assertTrue(any("cannot restore metal" in f for f in result["findings"]))

    def test_a_part_out_of_cycles_with_metal_left_needs_a_concession(self):
        result = assess_rework(_case(cycles_completed=3))
        self.assertEqual(result["disposition"], REWORK_CONCESSION)
        self.assertEqual(result["binding_limits"], [BINDING_POLICY])

    def test_cladding_can_be_the_binding_limit(self):
        result = assess_rework(
            _case(
                alloy_class="clad-sheet",
                clad_remaining_um=5.0,
                treated_surfaces=1,
                cycles_completed=0,
            )
        )
        self.assertEqual(result["binding_limits"], [BINDING_CLADDING])
        self.assertEqual(result["disposition"], REWORK_CONCESSION)

    def test_two_limits_can_bind_together(self):
        result = assess_rework(_case(current_mm=4.94, cycles_completed=1))
        self.assertEqual(result["cycles_remaining"], 2)
        self.assertEqual(
            result["binding_limits"], sorted([BINDING_DIMENSION, BINDING_POLICY])
        )

    def test_a_high_strength_part_is_held_to_one_cycle(self):
        result = assess_rework(_case(alloy_class="high-strength"))
        self.assertEqual(result["disposition"], REWORK_FINAL_CYCLE)
        self.assertEqual(result["cycles_remaining"], 1)

    def test_the_next_dimension_is_reported(self):
        result = assess_rework(GOOD_CASE)
        self.assertAlmostEqual(
            result["dimension_after_next_cycle_mm"], 4.980, places=9
        )
        self.assertAlmostEqual(result["loss_per_cycle_mm"], 0.020, places=12)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_rework("strip it and run it again")

    def test_missing_loss_rate_rejected(self):
        case = _case()
        del case["loss_per_surface_um"]
        with self.assertRaises(ValueError):
            assess_rework(case)

    def test_missing_alloy_class_rejected(self):
        case = _case()
        del case["alloy_class"]
        with self.assertRaises(ValueError):
            assess_rework(case)

    def test_a_clad_case_without_the_clad_thickness_rejected(self):
        with self.assertRaises(ValueError):
            assess_rework(_case(alloy_class="clad-sheet"))


if __name__ == "__main__":
    unittest.main()
