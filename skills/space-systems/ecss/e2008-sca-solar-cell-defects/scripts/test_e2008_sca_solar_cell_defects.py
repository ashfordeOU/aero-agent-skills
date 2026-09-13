#!/usr/bin/env python3
"""Contract test for the cell body chip and nick screen (offline)."""

import copy
import unittest

from e2008_sca_solar_cell_defects_logic import (
    ACCEPT,
    CELL_DISPOSITIONS,
    CELL_EDGES,
    DEFAULT_CELL_BODY_CRITERIA,
    DEFECT_KINDS,
    INSPECTION_INCOMPLETE,
    REFER,
    REJECT,
    assess_cell_defect,
    cell_geometry,
    defect_footprint_mm2,
    defect_reach_mm,
    inspect_cell_body,
    is_through_thickness,
    permitted_reach_mm,
    validate_cell_body_criteria,
)

GEOMETRY = cell_geometry(40.0, 40.0, 1.0)
ROOT_HALF = 0.7071067811865475


def _chip(**overrides):
    defect = {
        "id": "C1",
        "kind": "edge-chip",
        "edge": "x-minus",
        "ingress_mm": 0.3,
        "length_mm": 2.0,
        "depth_fraction": 0.4,
    }
    defect.update(overrides)
    return defect


def _corner(**overrides):
    defect = {
        "id": "K1",
        "kind": "corner-chip",
        "edge": "x-minus",
        "ingress_mm": 0.3,
        "length_mm": 2.0,
        "depth_fraction": 0.4,
    }
    defect.update(overrides)
    return defect


def _flake(**overrides):
    defect = {
        "id": "F1",
        "kind": "surface-chip",
        "edge": "y-minus",
        "stand_off_mm": 0.2,
        "inward_extent_mm": 0.3,
        "length_mm": 1.0,
        "depth_fraction": 0.2,
    }
    defect.update(overrides)
    return defect


def _cell(defects=None, **overrides):
    record = {
        "cell_id": "SCA-CELL-01",
        "length_mm": 40.0,
        "width_mm": 40.0,
        "edge_margin_mm": 1.0,
        "examined_edges": list(CELL_EDGES),
        "defects": copy.deepcopy(defects) if defects else [],
    }
    record.update(overrides)
    return record


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_cell_body_criteria(DEFAULT_CELL_BODY_CRITERIA),
            DEFAULT_CELL_BODY_CRITERIA,
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_body_criteria("default")

    def test_missing_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_BODY_CRITERIA)
        del broken["max_total_area_fraction"]
        with self.assertRaises(ValueError):
            validate_cell_body_criteria(broken)

    def test_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_BODY_CRITERIA)
        broken["max_ingress_fraction_of_margin"] = 1.4
        with self.assertRaises(ValueError):
            validate_cell_body_criteria(broken)

    def test_review_factor_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_BODY_CRITERIA)
        broken["defect_review_factor"] = 0.5
        with self.assertRaises(ValueError):
            validate_cell_body_criteria(broken)

    def test_single_defect_allowed_more_than_the_whole_cell_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_BODY_CRITERIA)
        broken["max_defect_area_fraction"] = 0.02
        with self.assertRaises(ValueError):
            validate_cell_body_criteria(broken)

    def test_non_integer_edge_count_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_BODY_CRITERIA)
        broken["max_defects_per_edge"] = 1.5
        with self.assertRaises(ValueError):
            validate_cell_body_criteria(broken)


class GeometryTests(unittest.TestCase):
    def test_active_area_is_the_cell_less_its_inactive_border(self):
        self.assertAlmostEqual(GEOMETRY["cell_area_mm2"], 1600.0, places=9)
        self.assertAlmostEqual(GEOMETRY["active_area_mm2"], 1444.0, places=9)

    def test_a_border_that_swallows_the_cell_rejected(self):
        with self.assertRaises(ValueError):
            cell_geometry(40.0, 40.0, 20.0)

    def test_non_numeric_dimension_rejected(self):
        with self.assertRaises(ValueError):
            cell_geometry("40", 40.0, 1.0)


class ReachTests(unittest.TestCase):
    def test_an_edge_chip_reaches_exactly_its_ingress(self):
        self.assertAlmostEqual(defect_reach_mm(_chip(ingress_mm=0.4)), 0.4, places=12)

    def test_a_corner_chip_is_measured_on_the_diagonal(self):
        reach = defect_reach_mm(_corner(ingress_mm=1.0))
        self.assertAlmostEqual(reach, ROOT_HALF, places=12)

    def test_a_flake_reaches_its_far_side(self):
        reach = defect_reach_mm(_flake(stand_off_mm=0.4, inward_extent_mm=0.25))
        self.assertAlmostEqual(reach, 0.65, places=12)

    def test_edge_chip_footprint_is_half_its_bounding_box(self):
        self.assertAlmostEqual(
            defect_footprint_mm2(_chip(ingress_mm=0.4, length_mm=3.0)), 0.6, places=12
        )

    def test_flake_footprint_is_its_whole_outline(self):
        self.assertAlmostEqual(
            defect_footprint_mm2(_flake(inward_extent_mm=0.5, length_mm=2.0)),
            1.0,
            places=12,
        )

    def test_unknown_kind_has_no_reach(self):
        with self.assertRaises(ValueError):
            defect_reach_mm(_chip(kind="scratch"))


class ThroughThicknessTests(unittest.TestCase):
    def test_a_shallow_break_is_not_through(self):
        self.assertFalse(is_through_thickness(_chip(depth_fraction=0.4)))

    def test_a_break_exactly_on_the_fraction_counts_as_through(self):
        self.assertTrue(is_through_thickness(_chip(depth_fraction=0.9)))

    def test_depth_beyond_the_wafer_rejected(self):
        with self.assertRaises(ValueError):
            is_through_thickness(_chip(depth_fraction=1.4))

    def test_a_through_break_tightens_the_position_allowance(self):
        shallow = permitted_reach_mm(_chip(depth_fraction=0.4), GEOMETRY)
        through = permitted_reach_mm(_chip(depth_fraction=1.0), GEOMETRY)
        self.assertAlmostEqual(shallow, 0.5, places=12)
        self.assertAlmostEqual(through, 0.3, places=12)


class DefectDispositionTests(unittest.TestCase):
    def test_a_small_break_inside_the_border_accepts(self):
        result = assess_cell_defect(_chip(), GEOMETRY)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertFalse(result["reaches_active_area"])

    def test_a_break_exactly_on_the_permitted_reach_accepts(self):
        result = assess_cell_defect(_chip(ingress_mm=0.5), GEOMETRY)
        self.assertAlmostEqual(
            result["reach_mm"], result["permitted_reach_mm"], places=12
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_break_past_the_allowance_but_clear_of_the_cell_refers(self):
        result = assess_cell_defect(_chip(ingress_mm=0.8), GEOMETRY)
        self.assertEqual(result["disposition"], REFER)
        self.assertFalse(result["reaches_active_area"])

    def test_a_break_into_the_active_area_rejects(self):
        result = assess_cell_defect(_chip(ingress_mm=1.4), GEOMETRY)
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(result["reaches_active_area"])
        self.assertAlmostEqual(
            result["encroached_active_area_mm2"], 0.4, places=12
        )

    def test_a_corner_tolerates_a_longer_measurement_than_an_edge(self):
        corner = assess_cell_defect(
            _corner(ingress_mm=0.7, length_mm=4.0), GEOMETRY
        )
        edge = assess_cell_defect(_chip(ingress_mm=0.7, length_mm=4.0), GEOMETRY)
        self.assertEqual(corner["disposition"], ACCEPT)
        self.assertEqual(edge["disposition"], REFER)

    def test_a_through_break_refers_where_a_shallow_one_accepts(self):
        shallow = assess_cell_defect(_chip(ingress_mm=0.4), GEOMETRY)
        through = assess_cell_defect(
            _chip(ingress_mm=0.4, depth_fraction=1.0), GEOMETRY
        )
        self.assertEqual(shallow["disposition"], ACCEPT)
        self.assertEqual(through["disposition"], REFER)
        self.assertTrue(through["through_thickness"])

    def test_an_oversize_footprint_refers(self):
        result = assess_cell_defect(_chip(ingress_mm=0.5, length_mm=20.0), GEOMETRY)
        self.assertAlmostEqual(result["footprint_mm2"], 5.0, places=12)
        self.assertEqual(result["disposition"], REFER)

    def test_a_far_oversize_footprint_rejects(self):
        result = assess_cell_defect(_chip(ingress_mm=0.5, length_mm=30.0), GEOMETRY)
        self.assertEqual(result["disposition"], REJECT)

    def test_the_corner_area_allowance_is_the_tighter_one(self):
        edge = assess_cell_defect(_chip(ingress_mm=0.5, length_mm=8.0), GEOMETRY)
        corner = assess_cell_defect(_corner(ingress_mm=0.5, length_mm=8.0), GEOMETRY)
        self.assertAlmostEqual(edge["footprint_mm2"], corner["footprint_mm2"], places=12)
        self.assertEqual(edge["disposition"], ACCEPT)
        self.assertEqual(corner["disposition"], REFER)

    def test_a_flake_inside_the_border_accepts_and_one_beyond_it_rejects(self):
        inside = assess_cell_defect(_flake(), GEOMETRY)
        beyond = assess_cell_defect(
            _flake(stand_off_mm=1.2, inward_extent_mm=0.4), GEOMETRY
        )
        self.assertEqual(inside["disposition"], ACCEPT)
        self.assertEqual(beyond["disposition"], REJECT)
        self.assertAlmostEqual(
            beyond["encroached_active_area_mm2"], 0.4, places=12
        )

    def test_a_missing_required_field_rejected(self):
        defect = _chip()
        del defect["depth_fraction"]
        with self.assertRaises(ValueError):
            assess_cell_defect(defect, GEOMETRY)

    def test_an_unknown_edge_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_defect(_chip(edge="north"), GEOMETRY)

    def test_a_break_longer_than_its_edge_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_defect(_chip(length_mm=60.0), GEOMETRY)

    def test_a_break_past_the_half_span_is_a_fractured_cell(self):
        with self.assertRaises(ValueError):
            assess_cell_defect(_chip(ingress_mm=25.0, length_mm=2.0), GEOMETRY)

    def test_every_declared_kind_is_dispositioned(self):
        self.assertEqual(len(DEFECT_KINDS), 4)
        self.assertEqual(len(CELL_DISPOSITIONS), 3)

    def test_negative_ingress_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_defect(_chip(ingress_mm=-0.2), GEOMETRY)


class CellRollupTests(unittest.TestCase):
    def test_a_clean_cell_accepts(self):
        result = inspect_cell_body(_cell([_chip()]))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inspection_complete"])
        self.assertEqual(result["not_accepted_ids"], [])

    def test_an_unexamined_edge_leaves_the_cell_open(self):
        cell = _cell([_chip()], examined_edges=["x-minus", "x-plus", "y-minus"])
        result = inspect_cell_body(cell)
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["unexamined_edges"], ["y-plus"])

    def test_a_defect_on_an_unexamined_edge_rejected(self):
        cell = _cell(
            [_chip(edge="y-plus")], examined_edges=["x-minus", "x-plus", "y-minus"]
        )
        with self.assertRaises(ValueError):
            inspect_cell_body(cell)

    def test_small_breaks_together_exceed_the_cell_allowance(self):
        defects = [
            _chip(id="C1", edge="x-minus", ingress_mm=0.5, length_mm=12.0),
            _chip(id="C2", edge="x-minus", ingress_mm=0.5, length_mm=12.0),
            _chip(id="C3", edge="x-plus", ingress_mm=0.5, length_mm=12.0),
        ]
        result = inspect_cell_body(_cell(defects))
        self.assertEqual(result["disposition_counts"][ACCEPT], 3)
        self.assertAlmostEqual(result["defect_area_fraction"], 9.0 / 1600.0, places=12)
        self.assertEqual(result["verdict"], REFER)
        self.assertTrue(any("together" in finding for finding in result["findings"]))

    def test_a_crowded_edge_escalates_even_when_each_break_passes(self):
        defects = [_chip(id="C%d" % n) for n in range(3)]
        result = inspect_cell_body(_cell(defects))
        self.assertEqual(result["crowded_edges"], ["x-minus"])
        self.assertEqual(result["verdict"], REFER)

    def test_the_worst_break_drives_the_cell_verdict(self):
        defects = [_chip(id="C1"), _chip(id="C2", edge="x-plus", ingress_mm=1.4)]
        result = inspect_cell_body(_cell(defects))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["reaching_active_area_ids"], ["C2"])
        self.assertEqual(result["not_accepted_ids"], ["C2"])
        self.assertGreater(result["active_area_loss_fraction"], 0.0)

    def test_duplicate_defect_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_cell_body(_cell([_chip(), _chip()]))

    def test_an_edge_listed_twice_as_examined_rejected(self):
        cell = _cell(examined_edges=["x-minus", "x-minus", "x-plus", "y-minus"])
        with self.assertRaises(ValueError):
            inspect_cell_body(cell)

    def test_a_blank_cell_id_rejected(self):
        with self.assertRaises(ValueError):
            inspect_cell_body(_cell(cell_id="   "))

    def test_non_list_defects_rejected(self):
        with self.assertRaises(ValueError):
            inspect_cell_body(_cell(defects="none"))

    def test_non_mapping_cell_rejected(self):
        with self.assertRaises(ValueError):
            inspect_cell_body("SCA-CELL-01")

    def test_an_untouched_cell_reports_no_loss(self):
        result = inspect_cell_body(_cell())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertAlmostEqual(result["defect_area_fraction"], 0.0, places=12)
        self.assertAlmostEqual(result["active_area_loss_fraction"], 0.0, places=12)
        self.assertEqual(
            sorted(result["defects_per_edge"]), sorted(list(CELL_EDGES))
        )


if __name__ == "__main__":
    unittest.main()
