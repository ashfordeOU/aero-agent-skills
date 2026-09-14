#!/usr/bin/env python3
"""Contract test for the bare cell bus bar and grid continuity screen (offline)."""

import copy
import unittest

from e2008_bare_cell_bus_bar_grids_logic import (
    ACCEPT,
    CONTINUITY_BREAKING_KINDS,
    DEFAULT_GRID_CONTINUITY_CRITERIA,
    INDICATION_KINDS,
    LINE_KINDS,
    REJECT,
    REVIEW,
    assess_cell_front_grid,
    assess_grid_indication,
    group_indications_by_line_kind,
    local_current_density_a_per_mm2,
    orphaned_collection_fraction,
    residual_width_fraction,
    validate_grid_continuity_criteria,
)

NARROWING = {
    "id": "GL-1",
    "kind": "line-constriction",
    "line_kind": "grid-finger",
    "nominal_width_um": 100.0,
    "narrowest_width_um": 90.0,
}

CLEAN_CELL = {
    "cell_id": "BARE-CELL-0001",
    "indications": [],
}


def _narrowing(**overrides):
    item = copy.deepcopy(NARROWING)
    item.update(overrides)
    return item


def _break(**overrides):
    item = {
        "id": "GL-BR",
        "kind": "line-break",
        "line_kind": "grid-finger",
        "line_length_mm": 40.0,
        "break_position_mm": 10.0,
        "feed_ends": 1,
    }
    item.update(overrides)
    return item


def _cell(indications, **overrides):
    cell = copy.deepcopy(CLEAN_CELL)
    cell["indications"] = indications
    cell.update(overrides)
    return cell


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_grid_continuity_criteria(DEFAULT_GRID_CONTINUITY_CRITERIA),
            DEFAULT_GRID_CONTINUITY_CRITERIA,
        )

    def test_criteria_cover_every_line_kind(self):
        for line_kind in LINE_KINDS:
            self.assertIn(
                line_kind,
                DEFAULT_GRID_CONTINUITY_CRITERIA["accept_residual_width_fraction"],
            )

    def test_bus_bar_is_held_tighter_than_a_finger(self):
        table = DEFAULT_GRID_CONTINUITY_CRITERIA["accept_residual_width_fraction"]
        self.assertGreater(table["front-bus-bar"], table["grid-finger"])

    def test_continuity_breaking_kinds_are_real_kinds(self):
        for kind in CONTINUITY_BREAKING_KINDS:
            self.assertIn(kind, INDICATION_KINDS)

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_grid_continuity_criteria("default")

    def test_criteria_missing_a_line_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_GRID_CONTINUITY_CRITERIA)
        del broken["accept_residual_width_fraction"]["grid-finger"]
        with self.assertRaises(ValueError):
            validate_grid_continuity_criteria(broken)

    def test_residual_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_GRID_CONTINUITY_CRITERIA)
        broken["accept_residual_width_fraction"]["grid-finger"] = 1.4
        with self.assertRaises(ValueError):
            validate_grid_continuity_criteria(broken)

    def test_review_fraction_above_accept_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_GRID_CONTINUITY_CRITERIA)
        broken["review_residual_width_fraction"]["grid-finger"] = 0.95
        with self.assertRaises(ValueError):
            validate_grid_continuity_criteria(broken)

    def test_review_current_density_below_accept_rejected(self):
        broken = copy.deepcopy(DEFAULT_GRID_CONTINUITY_CRITERIA)
        broken["review_current_density_a_per_mm2"] = 10.0
        with self.assertRaises(ValueError):
            validate_grid_continuity_criteria(broken)

    def test_zero_current_density_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_GRID_CONTINUITY_CRITERIA)
        broken["accept_current_density_a_per_mm2"] = 0.0
        with self.assertRaises(ValueError):
            validate_grid_continuity_criteria(broken)


class ResidualWidthTests(unittest.TestCase):
    def test_residual_fraction_is_the_surviving_share(self):
        self.assertAlmostEqual(residual_width_fraction(100.0, 75.0), 0.75, places=9)

    def test_an_untouched_line_keeps_its_full_width(self):
        self.assertAlmostEqual(residual_width_fraction(120.0, 120.0), 1.0, places=9)

    def test_a_fully_eaten_line_has_nothing_left(self):
        self.assertAlmostEqual(residual_width_fraction(100.0, 0.0), 0.0, places=9)

    def test_narrowest_wider_than_nominal_rejected(self):
        with self.assertRaises(ValueError):
            residual_width_fraction(100.0, 140.0)

    def test_zero_nominal_width_rejected(self):
        with self.assertRaises(ValueError):
            residual_width_fraction(0.0, 10.0)

    def test_negative_narrowest_width_rejected(self):
        with self.assertRaises(ValueError):
            residual_width_fraction(100.0, -1.0)


class OrphanedCollectionTests(unittest.TestCase):
    def test_a_break_orphans_everything_past_it_on_a_single_fed_line(self):
        self.assertAlmostEqual(
            orphaned_collection_fraction(40.0, 10.0, 1), 0.75, places=9
        )

    def test_a_line_fed_from_both_ends_orphans_nothing(self):
        self.assertAlmostEqual(
            orphaned_collection_fraction(40.0, 10.0, 2), 0.0, places=9
        )

    def test_a_break_at_the_far_tip_orphans_nothing(self):
        self.assertAlmostEqual(
            orphaned_collection_fraction(40.0, 40.0, 1), 0.0, places=9
        )

    def test_a_break_at_the_bus_bar_orphans_the_whole_line(self):
        self.assertAlmostEqual(
            orphaned_collection_fraction(40.0, 0.0, 1), 1.0, places=9
        )

    def test_break_beyond_the_line_length_rejected(self):
        with self.assertRaises(ValueError):
            orphaned_collection_fraction(40.0, 60.0, 1)

    def test_unknown_feed_end_count_rejected(self):
        with self.assertRaises(ValueError):
            orphaned_collection_fraction(40.0, 10.0, 3)

    def test_boolean_feed_ends_rejected(self):
        with self.assertRaises(ValueError):
            orphaned_collection_fraction(40.0, 10.0, True)


class CurrentDensityTests(unittest.TestCase):
    def test_current_density_uses_the_surviving_cross_section(self):
        self.assertAlmostEqual(
            local_current_density_a_per_mm2(0.15, 100.0, 10.0), 150.0, places=6
        )

    def test_a_narrower_line_carries_a_higher_density(self):
        wide = local_current_density_a_per_mm2(0.10, 100.0, 10.0)
        narrow = local_current_density_a_per_mm2(0.10, 50.0, 10.0)
        self.assertGreater(narrow, wide)

    def test_zero_metal_thickness_rejected(self):
        with self.assertRaises(ValueError):
            local_current_density_a_per_mm2(0.10, 100.0, 0.0)

    def test_negative_line_current_rejected(self):
        with self.assertRaises(ValueError):
            local_current_density_a_per_mm2(-0.10, 100.0, 10.0)


class ContinuityBreakTests(unittest.TestCase):
    def test_a_break_rejects_whatever_it_orphans(self):
        result = assess_grid_indication(_break())
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(result["continuity_broken"])

    def test_a_break_on_a_doubly_fed_line_still_rejects(self):
        result = assess_grid_indication(_break(feed_ends=2))
        self.assertEqual(result["disposition"], REJECT)
        self.assertAlmostEqual(
            result["measurements"]["orphaned_collection_fraction"], 0.0, places=9
        )

    def test_a_crack_through_the_bus_bar_rejects(self):
        result = assess_grid_indication(
            _break(kind="line-crack-through", line_kind="front-bus-bar")
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(
            any("continuity" in reason for reason in result["reasons"])
        )

    def test_a_break_without_its_geometry_rejected(self):
        broken = _break()
        del broken["feed_ends"]
        with self.assertRaises(ValueError):
            assess_grid_indication(broken)


class NarrowingTests(unittest.TestCase):
    def test_a_shallow_narrowing_is_accepted(self):
        result = assess_grid_indication(NARROWING)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_width_exactly_on_the_accept_fraction_is_accepted(self):
        result = assess_grid_indication(_narrowing(narrowest_width_um=75.0))
        self.assertAlmostEqual(
            result["measurements"]["residual_width_fraction"], 0.75, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_the_same_narrowing_on_a_bus_bar_loses_its_margin(self):
        result = assess_grid_indication(
            _narrowing(narrowest_width_um=80.0, line_kind="front-bus-bar")
        )
        self.assertEqual(result["disposition"], REVIEW)

    def test_width_exactly_on_the_review_fraction_stays_in_review(self):
        result = assess_grid_indication(_narrowing(narrowest_width_um=55.0))
        self.assertAlmostEqual(
            result["measurements"]["residual_width_fraction"], 0.55, places=9
        )
        self.assertEqual(result["disposition"], REVIEW)

    def test_a_narrowing_past_the_review_band_rejects(self):
        result = assess_grid_indication(_narrowing(narrowest_width_um=20.0))
        self.assertEqual(result["disposition"], REJECT)
        self.assertFalse(result["continuity_broken"])

    def test_an_edge_nick_is_measured_not_refused_on_presence(self):
        result = assess_grid_indication(
            _narrowing(kind="line-edge-nick", narrowest_width_um=95.0)
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_void_inside_the_line_is_measured_the_same_way(self):
        result = assess_grid_indication(
            _narrowing(kind="line-void", narrowest_width_um=60.0)
        )
        self.assertEqual(result["disposition"], REVIEW)

    def test_an_acceptable_width_can_still_fail_on_current_density(self):
        result = assess_grid_indication(
            _narrowing(
                narrowest_width_um=90.0, line_current_a=0.30, metal_thickness_um=10.0
            )
        )
        self.assertAlmostEqual(
            result["measurements"]["local_current_density_a_per_mm2"],
            333.3333333333,
            places=6,
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_a_modest_current_leaves_the_width_call_standing(self):
        result = assess_grid_indication(
            _narrowing(
                narrowest_width_um=90.0, line_current_a=0.05, metal_thickness_um=10.0
            )
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_current_without_a_thickness_rejected(self):
        with self.assertRaises(ValueError):
            assess_grid_indication(_narrowing(line_current_a=0.05))

    def test_a_narrowing_without_width_measurements_rejected(self):
        broken = _narrowing()
        del broken["narrowest_width_um"]
        with self.assertRaises(ValueError):
            assess_grid_indication(broken)

    def test_unknown_indication_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_grid_indication(_narrowing(kind="smudge"))

    def test_unknown_line_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_grid_indication(_narrowing(line_kind="rear-contact"))

    def test_non_mapping_indication_rejected(self):
        with self.assertRaises(ValueError):
            assess_grid_indication("line-constriction")


class GroupingTests(unittest.TestCase):
    def test_indications_group_by_line_kind(self):
        result = group_indications_by_line_kind(
            [_narrowing(), _narrowing(line_kind="front-bus-bar"), _break()]
        )
        self.assertEqual(result["counts"]["grid-finger"], 2)
        self.assertEqual(result["counts"]["front-bus-bar"], 1)

    def test_continuity_breaks_are_counted_apart(self):
        result = group_indications_by_line_kind([_narrowing(), _break()])
        self.assertEqual(result["continuity_broken_total"], 1)
        self.assertEqual(result["continuity_broken_counts"]["grid-finger"], 1)

    def test_grouping_an_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            group_indications_by_line_kind([_narrowing(kind="smudge")])

    def test_grouping_a_non_list_rejected(self):
        with self.assertRaises(ValueError):
            group_indications_by_line_kind("none")


class CellFrontGridTests(unittest.TestCase):
    def test_a_clean_front_is_accepted_with_a_record(self):
        result = assess_cell_front_grid(CLEAN_CELL)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["reject_count"], 0)
        self.assertTrue(
            any("runs through" in finding for finding in result["findings"])
        )

    def test_cell_verdict_takes_the_worst_indication(self):
        result = assess_cell_front_grid(
            _cell([_narrowing(id="A"), _narrowing(id="B", narrowest_width_um=60.0)])
        )
        self.assertEqual(result["verdict"], REVIEW)
        self.assertEqual(result["accept_count"], 1)
        self.assertEqual(result["review_count"], 1)

    def test_one_break_condemns_an_otherwise_clean_front(self):
        result = assess_cell_front_grid(
            _cell([_narrowing(id="A"), _break(id="B")])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["continuity_broken_ids"], ["B"])

    def test_the_worst_orphaned_share_is_reported(self):
        result = assess_cell_front_grid(
            _cell(
                [
                    _break(id="A", break_position_mm=30.0),
                    _break(id="B", break_position_mm=4.0),
                ]
            )
        )
        self.assertAlmostEqual(
            result["worst_orphaned_collection_fraction"], 0.90, places=9
        )

    def test_a_review_verdict_raises_a_nonconformance(self):
        result = assess_cell_front_grid(
            _cell([_narrowing(id="A", narrowest_width_um=60.0)])
        )
        self.assertTrue(result["nonconformance_review_required"])

    def test_an_accepted_cell_raises_no_nonconformance(self):
        self.assertFalse(
            assess_cell_front_grid(CLEAN_CELL)["nonconformance_review_required"]
        )

    def test_duplicate_indication_ids_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_front_grid(_cell([_narrowing(id="A"), _narrowing(id="A")]))

    def test_cell_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_front_grid(_cell([], cell_id="   "))

    def test_cell_with_a_non_list_survey_rejected(self):
        cell = copy.deepcopy(CLEAN_CELL)
        cell["indications"] = "none"
        with self.assertRaises(ValueError):
            assess_cell_front_grid(cell)

    def test_non_mapping_cell_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_front_grid("BARE-CELL-0001")


if __name__ == "__main__":
    unittest.main()
