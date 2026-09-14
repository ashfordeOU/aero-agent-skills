#!/usr/bin/env python3
"""Contract test for the bare cell chip and nick limits (offline)."""

import copy
import math
import unittest

from e2008_bare_cell_chip_and_nick_limits_logic import (
    ACCEPT,
    CELL_ACCEPTED,
    CELL_EDGES,
    CELL_REFERRED,
    CELL_REJECTED,
    CORNER_CHIP,
    DEFAULT_CHIP_CRITERIA,
    EDGE_CHIP,
    LENGTH_EDGE_A,
    REFER,
    REJECT,
    WIDTH_EDGE_A,
    assess_bare_cell_edges,
    assess_chip,
    assess_nick,
    edge_length_mm,
    locate_chip,
    validate_cell_geometry,
    validate_chip_criteria,
)

GEOMETRY = {
    "length_mm": 40.0,
    "width_mm": 40.0,
    "thickness_um": 150.0,
    "inactive_border_mm": 1.0,
}


def _chip(**overrides):
    chip = {
        "id": "C1",
        "edge": LENGTH_EDGE_A,
        "position_mm": 10.0,
        "run_mm": 1.0,
        "reach_mm": 0.4,
    }
    chip.update(overrides)
    return chip


def _corner_chip(**overrides):
    chip = {
        "id": "C9",
        "edge": LENGTH_EDGE_A,
        "position_mm": 0.0,
        "run_mm": 1.0,
        "reach_mm": 0.6,
        "adjacent_run_mm": 0.8,
    }
    chip.update(overrides)
    return chip


def _nick(**overrides):
    nick = {
        "id": "N1",
        "depth_um": 10.0,
        "diameter_mm": 0.4,
        "contact_clearance_mm": 0.5,
    }
    nick.update(overrides)
    return nick


def _cell(chips=None, nicks=None, **overrides):
    cell = {
        "cell_id": "BC-001",
        "geometry": copy.deepcopy(GEOMETRY),
        "chips": copy.deepcopy(chips) if chips else [],
        "nicks": copy.deepcopy(nicks) if nicks else [],
    }
    cell.update(overrides)
    return cell


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_chip_criteria(DEFAULT_CHIP_CRITERIA), DEFAULT_CHIP_CRITERIA
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_chip_criteria("default")

    def test_missing_limit_rejected(self):
        broken = dict(DEFAULT_CHIP_CRITERIA)
        del broken["max_corner_leg_mm"]
        with self.assertRaises(ValueError):
            validate_chip_criteria(broken)

    def test_reach_fraction_above_one_rejected(self):
        broken = dict(DEFAULT_CHIP_CRITERIA, edge_chip_reach_fraction=1.4)
        with self.assertRaises(ValueError):
            validate_chip_criteria(broken)

    def test_review_factor_below_one_rejected(self):
        broken = dict(DEFAULT_CHIP_CRITERIA, nick_depth_review_factor=0.8)
        with self.assertRaises(ValueError):
            validate_chip_criteria(broken)

    def test_non_integer_count_allowance_rejected(self):
        broken = dict(DEFAULT_CHIP_CRITERIA, max_chips_per_edge=2.5)
        with self.assertRaises(ValueError):
            validate_chip_criteria(broken)


class GeometryTests(unittest.TestCase):
    def test_geometry_derives_perimeter_and_areas(self):
        resolved = validate_cell_geometry(GEOMETRY)
        self.assertAlmostEqual(resolved["perimeter_mm"], 160.0, places=9)
        self.assertAlmostEqual(resolved["cell_area_mm2"], 1600.0, places=9)
        self.assertAlmostEqual(resolved["active_area_mm2"], 38.0 * 38.0, places=9)

    def test_border_that_swallows_the_cell_rejected(self):
        broken = dict(GEOMETRY, inactive_border_mm=25.0)
        with self.assertRaises(ValueError):
            validate_cell_geometry(broken)

    def test_non_positive_thickness_rejected(self):
        broken = dict(GEOMETRY, thickness_um=0.0)
        with self.assertRaises(ValueError):
            validate_cell_geometry(broken)

    def test_non_mapping_geometry_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_geometry("40x40")

    def test_edge_length_follows_the_named_edge(self):
        wide = dict(GEOMETRY, width_mm=20.0)
        self.assertAlmostEqual(edge_length_mm(LENGTH_EDGE_A, wide), 40.0, places=9)
        self.assertAlmostEqual(edge_length_mm(WIDTH_EDGE_A, wide), 20.0, places=9)

    def test_unknown_edge_rejected(self):
        with self.assertRaises(ValueError):
            edge_length_mm("diagonal", GEOMETRY)

    def test_every_named_edge_resolves(self):
        for edge in CELL_EDGES:
            self.assertGreater(edge_length_mm(edge, GEOMETRY), 0.0)


class ChipPlacementTests(unittest.TestCase):
    def test_mid_edge_chip_is_an_edge_chip(self):
        placement = locate_chip(_chip(), GEOMETRY)
        self.assertEqual(placement["zone"], EDGE_CHIP)
        self.assertAlmostEqual(placement["available_reach_mm"], 1.0, places=9)

    def test_chip_starting_at_a_corner_is_a_corner_chip(self):
        placement = locate_chip(_chip(position_mm=0.0), GEOMETRY)
        self.assertEqual(placement["zone"], CORNER_CHIP)

    def test_chip_ending_at_a_corner_is_a_corner_chip(self):
        placement = locate_chip(_chip(position_mm=39.0, run_mm=1.0), GEOMETRY)
        self.assertEqual(placement["zone"], CORNER_CHIP)

    def test_corner_chip_has_the_diagonal_of_the_border_to_spend(self):
        placement = locate_chip(_chip(position_mm=0.0), GEOMETRY)
        self.assertAlmostEqual(
            placement["available_reach_mm"], math.sqrt(2.0), places=9
        )

    def test_chip_longer_than_its_edge_rejected(self):
        with self.assertRaises(ValueError):
            locate_chip(_chip(position_mm=38.0, run_mm=5.0), GEOMETRY)

    def test_chip_spanning_exactly_to_the_far_corner_is_accepted_input(self):
        placement = locate_chip(_chip(position_mm=39.0, run_mm=1.0), GEOMETRY)
        self.assertAlmostEqual(placement["distance_to_corner_mm"], 0.0, places=9)

    def test_zero_run_rejected(self):
        with self.assertRaises(ValueError):
            locate_chip(_chip(run_mm=0.0), GEOMETRY)

    def test_negative_position_rejected(self):
        with self.assertRaises(ValueError):
            locate_chip(_chip(position_mm=-1.0), GEOMETRY)


class ChipDispositionTests(unittest.TestCase):
    def test_small_mid_edge_chip_accepted(self):
        result = assess_chip(_chip(), GEOMETRY)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_reach_exactly_on_the_allowance_still_accepts(self):
        result = assess_chip(_chip(reach_mm=0.5), GEOMETRY)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_reach_inside_the_border_but_past_the_allowance_is_referred(self):
        result = assess_chip(_chip(reach_mm=0.8), GEOMETRY)
        self.assertEqual(result["disposition"], REFER)

    def test_reach_past_the_border_rejects(self):
        result = assess_chip(_chip(reach_mm=1.2), GEOMETRY)
        self.assertEqual(result["disposition"], REJECT)

    def test_same_reach_is_benign_at_a_corner_and_marginal_mid_edge(self):
        at_corner = assess_chip(_corner_chip(reach_mm=0.6), GEOMETRY)
        mid_edge = assess_chip(_chip(reach_mm=0.6), GEOMETRY)
        self.assertEqual(at_corner["disposition"], ACCEPT)
        self.assertEqual(mid_edge["disposition"], REFER)

    def test_reach_past_the_border_is_only_a_referral_at_a_corner(self):
        at_corner = assess_chip(_corner_chip(reach_mm=1.2), GEOMETRY)
        mid_edge = assess_chip(_chip(reach_mm=1.2), GEOMETRY)
        self.assertEqual(at_corner["disposition"], REFER)
        self.assertEqual(mid_edge["disposition"], REJECT)

    def test_long_run_along_the_edge_is_referred(self):
        result = assess_chip(_chip(run_mm=3.0), GEOMETRY)
        self.assertEqual(result["disposition"], REFER)

    def test_very_long_run_along_the_edge_rejects(self):
        result = assess_chip(_chip(run_mm=5.0), GEOMETRY)
        self.assertEqual(result["disposition"], REJECT)

    def test_run_allowance_scales_with_the_edge_it_sits_on(self):
        short_edge = dict(GEOMETRY, width_mm=20.0)
        on_long = assess_chip(_chip(run_mm=1.5), short_edge)
        on_short = assess_chip(
            _chip(edge=WIDTH_EDGE_A, position_mm=5.0, run_mm=1.5), short_edge
        )
        self.assertEqual(on_long["disposition"], ACCEPT)
        self.assertEqual(on_short["disposition"], REFER)

    def test_corner_leg_limit_applies_to_the_longer_leg(self):
        result = assess_chip(
            _corner_chip(run_mm=1.0, adjacent_run_mm=2.6), GEOMETRY
        )
        self.assertEqual(result["disposition"], REFER)

    def test_corner_leg_past_the_review_band_rejects(self):
        result = assess_chip(
            _corner_chip(run_mm=1.0, adjacent_run_mm=4.0), GEOMETRY
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_edge_chip_area_is_the_triangle_of_run_and_reach(self):
        result = assess_chip(_chip(run_mm=2.0, reach_mm=0.5), GEOMETRY)
        self.assertAlmostEqual(result["chip_area_mm2"], 0.5, places=9)

    def test_corner_chip_area_uses_both_legs(self):
        result = assess_chip(_corner_chip(run_mm=1.0, adjacent_run_mm=0.8), GEOMETRY)
        self.assertAlmostEqual(result["chip_area_mm2"], 0.4, places=9)
        self.assertAlmostEqual(result["perimeter_loss_mm"], 1.8, places=9)

    def test_missing_reach_rejected(self):
        chip = _chip()
        del chip["reach_mm"]
        with self.assertRaises(ValueError):
            assess_chip(chip, GEOMETRY)


class NickDispositionTests(unittest.TestCase):
    def test_shallow_clear_nick_accepted(self):
        result = assess_nick(_nick(), GEOMETRY)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_depth_exactly_on_the_allowance_still_accepts(self):
        result = assess_nick(_nick(depth_um=15.0), GEOMETRY)
        self.assertAlmostEqual(result["depth_fraction_of_thickness"], 0.1, places=9)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_depth_in_the_review_band_is_referred(self):
        result = assess_nick(_nick(depth_um=22.5), GEOMETRY)
        self.assertEqual(result["disposition"], REFER)

    def test_deep_nick_rejects_as_a_fracture_origin(self):
        result = assess_nick(_nick(depth_um=45.0), GEOMETRY)
        self.assertEqual(result["disposition"], REJECT)

    def test_depth_is_graded_against_the_actual_wafer_thickness(self):
        thin = dict(GEOMETRY, thickness_um=80.0)
        on_thick = assess_nick(_nick(depth_um=14.0), GEOMETRY)
        on_thin = assess_nick(_nick(depth_um=14.0), thin)
        self.assertEqual(on_thick["disposition"], ACCEPT)
        self.assertEqual(on_thin["disposition"], REFER)

    def test_wide_nick_is_referred(self):
        result = assess_nick(_nick(diameter_mm=0.9), GEOMETRY)
        self.assertEqual(result["disposition"], REFER)

    def test_nick_inside_the_contact_clearance_rejects(self):
        result = assess_nick(_nick(contact_clearance_mm=0.1), GEOMETRY)
        self.assertEqual(result["disposition"], REJECT)

    def test_clearance_exactly_on_the_limit_still_accepts(self):
        result = assess_nick(_nick(contact_clearance_mm=0.3), GEOMETRY)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_nick_deeper_than_the_cell_rejected(self):
        with self.assertRaises(ValueError):
            assess_nick(_nick(depth_um=200.0), GEOMETRY)

    def test_missing_clearance_rejected(self):
        nick = _nick()
        del nick["contact_clearance_mm"]
        with self.assertRaises(ValueError):
            assess_nick(nick, GEOMETRY)


class CellRollupTests(unittest.TestCase):
    def test_clean_cell_is_accepted(self):
        result = assess_bare_cell_edges(_cell([_chip()], [_nick()]))
        self.assertEqual(result["verdict"], CELL_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["not_accepted_ids"], [])

    def test_worst_defect_sets_the_cell_verdict(self):
        result = assess_bare_cell_edges(
            _cell([_chip(), _chip(id="C2", position_mm=20.0, reach_mm=1.3)])
        )
        self.assertEqual(result["verdict"], CELL_REJECTED)
        self.assertEqual(result["not_accepted_ids"], ["C2"])

    def test_cumulative_perimeter_loss_catches_individually_clean_chips(self):
        chips = []
        for index, edge in enumerate(CELL_EDGES):
            chips.append(_chip(id="C%da" % index, edge=edge, position_mm=5.0))
            chips.append(_chip(id="C%db" % index, edge=edge, position_mm=10.0))
        result = assess_bare_cell_edges(_cell(chips))
        for chip in result["chips"]:
            self.assertEqual(chip["disposition"], ACCEPT)
        self.assertAlmostEqual(result["perimeter_loss_mm"], 8.0, places=9)
        self.assertAlmostEqual(result["perimeter_loss_fraction"], 0.05, places=9)
        self.assertEqual(result["verdict"], CELL_REFERRED)

    def test_cumulative_face_area_allowance_is_enforced(self):
        criteria = dict(DEFAULT_CHIP_CRITERIA, max_cumulative_chip_area_fraction=1e-4)
        result = assess_bare_cell_edges(_cell([_chip()]), criteria)
        self.assertAlmostEqual(result["chip_area_mm2"], 0.2, places=9)
        self.assertEqual(result["verdict"], CELL_REFERRED)

    def test_too_many_chips_on_one_edge_is_referred(self):
        chips = [
            _chip(id="C1", position_mm=2.0),
            _chip(id="C2", position_mm=10.0),
            _chip(id="C3", position_mm=20.0),
        ]
        result = assess_bare_cell_edges(_cell(chips))
        self.assertEqual(result["chips_per_edge"][LENGTH_EDGE_A], 3)
        self.assertEqual(result["verdict"], CELL_REFERRED)

    def test_too_many_nicks_on_one_cell_is_referred(self):
        nicks = [_nick(id="N%d" % index) for index in range(5)]
        result = assess_bare_cell_edges(_cell(None, nicks))
        self.assertEqual(result["verdict"], CELL_REFERRED)

    def test_chips_closer_than_the_separation_are_reported_as_a_pair(self):
        chips = [
            _chip(id="C1", position_mm=5.0),
            _chip(id="C2", position_mm=6.4),
        ]
        result = assess_bare_cell_edges(_cell(chips))
        self.assertEqual(result["clustered_chip_pairs"], 1)
        self.assertEqual(result["verdict"], CELL_REFERRED)

    def test_chips_on_different_edges_are_never_a_pair(self):
        chips = [
            _chip(id="C1", edge=CELL_EDGES[0], position_mm=5.0),
            _chip(id="C2", edge=CELL_EDGES[1], position_mm=5.0),
        ]
        result = assess_bare_cell_edges(_cell(chips))
        self.assertEqual(result["clustered_chip_pairs"], 0)
        self.assertEqual(result["verdict"], CELL_ACCEPTED)

    def test_corner_chips_are_counted_separately(self):
        result = assess_bare_cell_edges(
            _cell([_chip(id="C1", position_mm=10.0), _corner_chip()])
        )
        self.assertEqual(result["corner_chip_count"], 1)

    def test_duplicate_defect_ids_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_edges(_cell([_chip(id="D")], [_nick(id="D")]))

    def test_cell_without_an_id_rejected(self):
        cell = _cell([_chip()])
        cell["cell_id"] = "  "
        with self.assertRaises(ValueError):
            assess_bare_cell_edges(cell)

    def test_non_list_chip_collection_rejected(self):
        cell = _cell()
        cell["chips"] = _chip()
        with self.assertRaises(ValueError):
            assess_bare_cell_edges(cell)

    def test_input_is_not_mutated_by_the_screen(self):
        cell = _cell([_chip(), _corner_chip()], [_nick()])
        before = copy.deepcopy(cell)
        assess_bare_cell_edges(cell)
        self.assertEqual(cell, before)


if __name__ == "__main__":
    unittest.main()
