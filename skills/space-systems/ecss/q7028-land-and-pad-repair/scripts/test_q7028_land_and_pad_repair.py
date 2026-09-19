"""Contract tests for the land and pad repair logic."""

import unittest

from q7028_land_and_pad_repair_logic import (
    ALLOWABLE_BOND_STRESS_MPA,
    MAX_REPAIRED_LANDS_PER_FOOTPRINT,
    MIN_ANNULAR_RING_MM,
    MIN_PULL_OFF_N,
    MIN_REBOND_FRACTION,
    annular_land_area_mm2,
    annular_ring_mm,
    footprint_findings,
    land_area_mm2,
    plan_land_repair,
    rectangular_pad_area_mm2,
    required_bond_area_mm2,
    select_build_up_method,
    surviving_fraction,
)

# A 2.0 mm land around a 0.9 mm hole; 2.505420 mm2 of copper, worked out once
# away from the module as pi * (2.0^2 - 0.9^2) / 4.
THROUGH_HOLE_GEOMETRY = {"land_diameter_mm": 2.0, "hole_diameter_mm": 0.9}
THROUGH_HOLE_AREA_MM2 = 2.50542014123786


def base_damage(fraction=0.85, **overrides):
    damage = {
        "geometry": dict(THROUGH_HOLE_GEOMETRY),
        "surviving_area_mm2": fraction * THROUGH_HOLE_AREA_MM2,
        "barrel_state": "sound",
        "repaired_lands_on_footprint": 0,
    }
    damage.update(overrides)
    return damage


class AreaTests(unittest.TestCase):
    def test_annular_land_area_is_the_hand_worked_figure(self):
        self.assertAlmostEqual(
            annular_land_area_mm2(2.0, 0.9), THROUGH_HOLE_AREA_MM2, places=9
        )

    def test_rectangular_pad_area_is_the_product(self):
        self.assertAlmostEqual(rectangular_pad_area_mm2(2.0, 1.2), 2.4, places=9)

    def test_a_hole_as_wide_as_the_land_is_rejected(self):
        with self.assertRaises(ValueError):
            annular_land_area_mm2(1.0, 1.0)

    def test_geometry_dispatch_handles_a_through_hole_land(self):
        self.assertAlmostEqual(
            land_area_mm2(THROUGH_HOLE_GEOMETRY), THROUGH_HOLE_AREA_MM2, places=9
        )

    def test_geometry_dispatch_handles_a_surface_mount_pad(self):
        self.assertAlmostEqual(
            land_area_mm2({"length_mm": 2.0, "width_mm": 1.2}), 2.4, places=9
        )

    def test_incomplete_geometry_rejected(self):
        with self.assertRaises(ValueError):
            land_area_mm2({"land_diameter_mm": 2.0})

    def test_surviving_fraction_is_the_ratio(self):
        self.assertAlmostEqual(surviving_fraction(1.2, 2.4), 0.5, places=9)

    def test_a_fully_intact_land_reports_one(self):
        self.assertAlmostEqual(surviving_fraction(2.4, 2.4), 1.0, places=9)

    def test_surviving_area_larger_than_the_design_rejected(self):
        with self.assertRaises(ValueError):
            surviving_fraction(3.0, 2.4)

    def test_negative_surviving_area_rejected(self):
        with self.assertRaises(ValueError):
            surviving_fraction(-0.1, 2.4)


class BondAreaTests(unittest.TestCase):
    def test_required_area_is_the_load_over_the_stress(self):
        self.assertAlmostEqual(
            required_bond_area_mm2(7.0, 3.5), 2.0, places=9
        )

    def test_the_default_load_and_stress_are_used(self):
        self.assertAlmostEqual(
            required_bond_area_mm2(),
            MIN_PULL_OFF_N / ALLOWABLE_BOND_STRESS_MPA,
            places=9,
        )

    def test_zero_stress_rejected(self):
        with self.assertRaises(ValueError):
            required_bond_area_mm2(4.5, 0.0)

    def test_annular_ring_is_half_the_diameter_difference(self):
        self.assertAlmostEqual(annular_ring_mm(2.0, 0.9), 0.55, places=9)


class MethodSelectionTests(unittest.TestCase):
    def test_a_mostly_intact_land_is_rebonded_in_place(self):
        self.assertEqual(
            select_build_up_method(0.90, "sound")["method"], "land-rebond-in-place"
        )

    def test_the_rebond_fraction_bound_still_rebonds(self):
        self.assertEqual(
            select_build_up_method(MIN_REBOND_FRACTION, "sound")["method"],
            "land-rebond-in-place",
        )

    def test_a_badly_torn_land_takes_a_replacement(self):
        selection = select_build_up_method(0.40, "sound")
        self.assertEqual(selection["method"], "replacement-land-epoxy-bond")
        self.assertIn("below the", selection["reason"])

    def test_almost_nothing_left_leaves_no_method(self):
        selection = select_build_up_method(0.01, "sound")
        self.assertIsNone(selection["method"])
        self.assertIn("too little sound base material", selection["reason"])

    def test_a_damaged_barrel_forces_an_eyelet(self):
        self.assertEqual(
            select_build_up_method(0.95, "damaged")["method"], "barrel-eyelet"
        )

    def test_an_absent_barrel_forces_an_eyelet(self):
        self.assertEqual(select_build_up_method(0.20, "absent")["method"], "barrel-eyelet")

    def test_unknown_barrel_state_rejected(self):
        with self.assertRaises(ValueError):
            select_build_up_method(0.9, "rusty")

    def test_a_fraction_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            select_build_up_method(1.2, "sound")


class FootprintTests(unittest.TestCase):
    def test_a_first_repaired_land_is_clean(self):
        self.assertEqual(footprint_findings(0), [])

    def test_reaching_the_footprint_limit_exactly_is_clean(self):
        self.assertEqual(footprint_findings(MAX_REPAIRED_LANDS_PER_FOOTPRINT - 1), [])

    def test_passing_the_footprint_limit_is_flagged(self):
        self.assertTrue(footprint_findings(MAX_REPAIRED_LANDS_PER_FOOTPRINT))

    def test_a_non_integer_footprint_count_rejected(self):
        with self.assertRaises(ValueError):
            footprint_findings(1.5)


class PlanTests(unittest.TestCase):
    def test_a_nominal_lifted_land_is_rebonded_and_ready(self):
        plan = plan_land_repair(base_damage())
        self.assertEqual(plan["method"], "land-rebond-in-place")
        self.assertTrue(plan["ready"])

    def test_a_rebond_carries_only_the_copper_that_survived(self):
        plan = plan_land_repair(base_damage(0.85))
        self.assertAlmostEqual(
            plan["available_bond_area_mm2"], 0.85 * THROUGH_HOLE_AREA_MM2, places=9
        )

    def test_a_replacement_land_is_built_back_to_the_designed_area(self):
        plan = plan_land_repair(base_damage(0.40))
        self.assertEqual(plan["method"], "replacement-land-epoxy-bond")
        self.assertAlmostEqual(
            plan["available_bond_area_mm2"], THROUGH_HOLE_AREA_MM2, places=9
        )

    def test_a_small_land_rebond_can_fail_the_pull_off_area(self):
        plan = plan_land_repair(
            {
                "geometry": {"land_diameter_mm": 1.2, "hole_diameter_mm": 0.6},
                "surviving_area_mm2": 0.8 * 0.8482300164692442,
            }
        )
        self.assertTrue(any("pull-off needs" in f for f in plan["findings"]))

    def test_a_damaged_barrel_reaches_the_eyelet_through_the_plan(self):
        plan = plan_land_repair(base_damage(0.95, barrel_state="damaged"))
        self.assertEqual(plan["method"], "barrel-eyelet")

    def test_a_thin_repaired_land_fails_the_annular_ring(self):
        plan = plan_land_repair(base_damage(0.85, repaired_land_diameter_mm=0.92))
        self.assertTrue(any("annular ring" in f for f in plan["findings"]))

    def test_a_ring_exactly_on_the_minimum_is_accepted(self):
        diameter = 0.9 + 2.0 * MIN_ANNULAR_RING_MM
        plan = plan_land_repair(base_damage(0.85, repaired_land_diameter_mm=diameter))
        self.assertAlmostEqual(plan["annular_ring_mm"], MIN_ANNULAR_RING_MM, places=9)
        self.assertEqual(plan["findings"], [])

    def test_a_surface_mount_pad_reports_no_annular_ring(self):
        plan = plan_land_repair(
            {"geometry": {"length_mm": 2.0, "width_mm": 1.2}, "surviving_area_mm2": 2.0}
        )
        self.assertIsNone(plan["annular_ring_mm"])
        self.assertTrue(plan["ready"])

    def test_too_many_repaired_lands_on_a_footprint_reach_the_plan(self):
        plan = plan_land_repair(
            base_damage(0.85, repaired_lands_on_footprint=MAX_REPAIRED_LANDS_PER_FOOTPRINT)
        )
        self.assertFalse(plan["ready"])
        self.assertTrue(any("on the footprint" in f for f in plan["findings"]))

    def test_a_destroyed_land_leaves_no_method(self):
        plan = plan_land_repair(base_damage(0.01))
        self.assertIsNone(plan["method"])
        self.assertFalse(plan["ready"])

    def test_a_heavier_pull_off_demands_more_bond_area(self):
        light = plan_land_repair(base_damage(0.85))
        heavy = plan_land_repair(base_damage(0.85, pull_off_n=9.0))
        self.assertGreater(
            heavy["required_bond_area_mm2"], light["required_bond_area_mm2"]
        )

    def test_missing_damage_key_rejected(self):
        damage = base_damage()
        del damage["surviving_area_mm2"]
        with self.assertRaises(ValueError):
            plan_land_repair(damage)

    def test_non_mapping_damage_rejected(self):
        with self.assertRaises(ValueError):
            plan_land_repair("land-lifted")


if __name__ == "__main__":
    unittest.main()
