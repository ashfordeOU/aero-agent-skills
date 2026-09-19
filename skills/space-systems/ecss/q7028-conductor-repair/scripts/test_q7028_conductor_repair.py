"""Contract tests for the conductor and track repair logic."""

import unittest

from q7028_conductor_repair_logic import (
    COPPER_THICKNESS_MM_PER_OZ,
    JUMPER_CURRENT_DENSITY_A_PER_MM2,
    JUMPER_DERATING,
    MAX_JUMPERS_PER_BOARD,
    MAX_JUMPER_LENGTH_MM,
    MAX_LAP_GAP_MM,
    MAX_UNSUPPORTED_RUN_MM,
    MIN_LAP_OVERLAP_MM,
    MIN_LAP_TRACK_WIDTH_MM,
    jumper_bond_count,
    lap_overlap_mm,
    lap_segment_length_mm,
    plan_conductor_repair,
    select_jumper_gauge,
    select_method,
    track_cross_section_mm2,
    wire_cross_section_mm2,
)


def base_damage(**overrides):
    """A 1 mm break in a 0.5 mm wide, 1 oz track carrying 0.5 A."""
    damage = {
        "gap_mm": 1.0,
        "track_width_mm": 0.5,
        "copper_weight_oz": 1.0,
        "current_a": 0.5,
    }
    damage.update(overrides)
    return damage


class CrossSectionTests(unittest.TestCase):
    def test_track_area_follows_width_and_copper_weight(self):
        self.assertAlmostEqual(
            track_cross_section_mm2(0.5, 1.0), 0.5 * COPPER_THICKNESS_MM_PER_OZ, places=9
        )

    def test_doubling_the_copper_weight_doubles_the_area(self):
        self.assertAlmostEqual(
            track_cross_section_mm2(0.5, 2.0),
            2.0 * track_cross_section_mm2(0.5, 1.0),
            places=9,
        )

    def test_wire_area_is_the_circle_area(self):
        # A 0.4 mm wire is 0.125663706 mm2, worked out once away from the module.
        self.assertAlmostEqual(wire_cross_section_mm2(0.4), 0.12566370614359174, places=9)

    def test_zero_width_rejected(self):
        with self.assertRaises(ValueError):
            track_cross_section_mm2(0.0, 1.0)

    def test_non_numeric_copper_weight_rejected(self):
        with self.assertRaises(ValueError):
            track_cross_section_mm2(0.5, "1oz")


class LapJointTests(unittest.TestCase):
    def test_overlap_scales_with_a_wide_track(self):
        self.assertAlmostEqual(lap_overlap_mm(0.5), 1.5, places=9)

    def test_overlap_has_a_floor_on_a_fine_track(self):
        self.assertAlmostEqual(lap_overlap_mm(0.2), MIN_LAP_OVERLAP_MM, places=9)

    def test_segment_length_is_the_gap_plus_both_overlaps(self):
        self.assertAlmostEqual(lap_segment_length_mm(1.0, 0.5), 1.0 + 2 * 1.5, places=9)

    def test_negative_gap_rejected(self):
        with self.assertRaises(ValueError):
            lap_segment_length_mm(-1.0, 0.5)


class MethodSelectionTests(unittest.TestCase):
    def test_a_short_gap_on_a_wide_track_is_lapped(self):
        self.assertEqual(
            select_method(1.0, 0.5)["method"], "conductor-lap-solder-splice"
        )

    def test_a_gap_exactly_on_the_lap_limit_is_still_lapped(self):
        self.assertEqual(
            select_method(MAX_LAP_GAP_MM, 0.5)["method"], "conductor-lap-solder-splice"
        )

    def test_a_track_exactly_on_the_width_floor_is_lappable(self):
        self.assertEqual(
            select_method(1.0, MIN_LAP_TRACK_WIDTH_MM)["method"],
            "conductor-lap-solder-splice",
        )

    def test_a_long_gap_takes_a_jumper(self):
        selection = select_method(20.0, 0.5)
        self.assertEqual(selection["method"], "conductor-jumper-wire")
        self.assertIn("past the", selection["reason"])

    def test_a_fine_track_takes_a_jumper_even_on_a_short_gap(self):
        selection = select_method(1.0, 0.15)
        self.assertEqual(selection["method"], "conductor-jumper-wire")
        self.assertIn("solder to", selection["reason"])

    def test_a_gap_on_the_jumper_reach_is_still_repairable(self):
        self.assertEqual(
            select_method(MAX_JUMPER_LENGTH_MM, 0.5)["method"], "conductor-jumper-wire"
        )

    def test_a_gap_beyond_the_jumper_reach_has_no_method(self):
        selection = select_method(MAX_JUMPER_LENGTH_MM + 10.0, 0.5)
        self.assertIsNone(selection["method"])
        self.assertIn("nonconformance review", selection["reason"])


class JumperSizingTests(unittest.TestCase):
    def test_a_small_current_takes_a_thin_wire(self):
        self.assertEqual(select_jumper_gauge(0.5)["gauge"], 26)

    def test_a_larger_current_takes_a_thicker_wire(self):
        self.assertEqual(select_jumper_gauge(1.2)["gauge"], 22)

    def test_a_current_exactly_on_a_gauge_capacity_takes_that_gauge(self):
        capacity = (
            wire_cross_section_mm2(0.405) * JUMPER_CURRENT_DENSITY_A_PER_MM2 * JUMPER_DERATING
        )
        self.assertEqual(select_jumper_gauge(capacity)["gauge"], 26)

    def test_the_reported_capacity_is_the_hand_worked_figure(self):
        # 0.405 mm wire: 0.128824934 mm2 at 6 A/mm2 derated to 0.8 is 0.618359682 A.
        chosen = select_jumper_gauge(0.5)
        self.assertAlmostEqual(chosen["cross_section_mm2"], 0.12882493375126647, places=9)
        self.assertAlmostEqual(chosen["derated_capacity_a"], 0.618359682006079, places=9)

    def test_a_harsher_derating_pushes_to_a_thicker_wire(self):
        self.assertGreater(
            select_jumper_gauge(0.5)["gauge"], select_jumper_gauge(0.5, derating=0.4)["gauge"]
        )

    def test_a_current_no_bench_wire_carries_is_rejected(self):
        with self.assertRaises(ValueError):
            select_jumper_gauge(12.0)

    def test_a_derating_above_one_rejected(self):
        with self.assertRaises(ValueError):
            select_jumper_gauge(0.5, derating=1.4)

    def test_zero_current_rejected(self):
        with self.assertRaises(ValueError):
            select_jumper_gauge(0.0)


class BondSpacingTests(unittest.TestCase):
    def test_a_short_jumper_is_bonded_at_both_ends(self):
        self.assertEqual(jumper_bond_count(10.0), 2)

    def test_a_run_exactly_on_the_unsupported_limit_needs_no_extra_bond(self):
        self.assertEqual(jumper_bond_count(MAX_UNSUPPORTED_RUN_MM), 2)

    def test_a_run_just_past_the_limit_gains_a_bond(self):
        self.assertEqual(jumper_bond_count(MAX_UNSUPPORTED_RUN_MM + 1.0), 3)

    def test_two_whole_spans_need_three_bonds(self):
        self.assertEqual(jumper_bond_count(2.0 * MAX_UNSUPPORTED_RUN_MM), 3)

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):
            jumper_bond_count(0.0)


class PlanTests(unittest.TestCase):
    def test_a_nominal_lap_repair_is_ready(self):
        plan = plan_conductor_repair(base_damage())
        self.assertEqual(plan["method"], "conductor-lap-solder-splice")
        self.assertTrue(plan["ready"])
        self.assertAlmostEqual(plan["lap_segment_length_mm"], 4.0, places=9)

    def test_a_lap_repair_restores_the_original_cross_section(self):
        plan = plan_conductor_repair(base_damage())
        self.assertAlmostEqual(
            plan["replacement_cross_section_mm2"],
            plan["original_cross_section_mm2"],
            places=9,
        )

    def test_a_long_break_plans_a_jumper_with_its_bonds(self):
        plan = plan_conductor_repair(base_damage(gap_mm=30.0, jumper_route_length_mm=40.0))
        self.assertEqual(plan["method"], "conductor-jumper-wire")
        self.assertEqual(plan["jumper_bonds"], 3)
        self.assertEqual(plan["jumper"]["gauge"], 26)

    def test_a_jumper_thinner_than_the_track_it_replaces_is_flagged(self):
        plan = plan_conductor_repair(
            base_damage(gap_mm=30.0, track_width_mm=3.0, copper_weight_oz=2.0, current_a=0.2)
        )
        self.assertTrue(any("weakest point" in f for f in plan["findings"]))

    def test_the_jumper_count_on_a_board_is_held(self):
        plan = plan_conductor_repair(
            base_damage(gap_mm=30.0, existing_jumpers=MAX_JUMPERS_PER_BOARD)
        )
        self.assertTrue(any("past the" in f for f in plan["findings"]))
        self.assertFalse(plan["ready"])

    def test_the_last_allowed_jumper_is_still_clean(self):
        plan = plan_conductor_repair(
            base_damage(gap_mm=30.0, existing_jumpers=MAX_JUMPERS_PER_BOARD - 1)
        )
        self.assertTrue(plan["ready"])

    def test_an_over_long_route_is_flagged(self):
        plan = plan_conductor_repair(
            base_damage(gap_mm=30.0, jumper_route_length_mm=MAX_JUMPER_LENGTH_MM + 5.0)
        )
        self.assertTrue(any("jumper route" in f for f in plan["findings"]))

    def test_an_unspannable_break_leaves_no_method(self):
        plan = plan_conductor_repair(base_damage(gap_mm=200.0))
        self.assertIsNone(plan["method"])
        self.assertFalse(plan["ready"])

    def test_missing_damage_key_rejected(self):
        damage = base_damage()
        del damage["current_a"]
        with self.assertRaises(ValueError):
            plan_conductor_repair(damage)

    def test_non_mapping_damage_rejected(self):
        with self.assertRaises(ValueError):
            plan_conductor_repair("gap")


if __name__ == "__main__":
    unittest.main()
