#!/usr/bin/env python3
"""Contract test for the bare cell rear contact deposit limits (offline)."""

import copy
import math
import unittest

from e2008_bare_cell_rear_contact_limits_logic import (
    ACCEPT,
    DEFAULT_REAR_CONTACT_CRITERIA,
    DEPOSIT_KINDS,
    REJECT,
    REWORK,
    assess_rear_contact,
    assess_rear_deposit,
    deposit_footprint_area_mm2,
    distance_outside_welding_zone_mm,
    distance_to_cell_edge_mm,
    effective_diameter_ceilings_mm,
    group_deposits_by_kind,
    validate_cell_outline,
    validate_rear_contact_criteria,
    validate_welding_zone,
)

OUTLINE = {"length_mm": 40.0, "width_mm": 40.0}
ZONE = {"x_min": 15.0, "x_max": 25.0, "y_min": 15.0, "y_max": 25.0}

CLEAN_CELL = {
    "cell_id": "BARE-CELL-0002",
    "outline": copy.deepcopy(OUTLINE),
    "welding_zone": copy.deepcopy(ZONE),
    "deposits": [],
}

DROP = {
    "id": "RD-1",
    "kind": "solder-drop",
    "x_mm": 30.0,
    "y_mm": 20.0,
    "diameter_mm": 0.20,
    "height_mm": 0.02,
}


def _drop(**overrides):
    item = copy.deepcopy(DROP)
    item.update(overrides)
    return item


def _cell(deposits, **overrides):
    cell = copy.deepcopy(CLEAN_CELL)
    cell["deposits"] = deposits
    cell.update(overrides)
    return cell


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_rear_contact_criteria(DEFAULT_REAR_CONTACT_CRITERIA),
            DEFAULT_REAR_CONTACT_CRITERIA,
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_rear_contact_criteria("default")

    def test_rework_ceiling_below_accept_ceiling_rejected(self):
        broken = copy.deepcopy(DEFAULT_REAR_CONTACT_CRITERIA)
        broken["rework_deposit_diameter_mm"] = 0.10
        with self.assertRaises(ValueError):
            validate_rear_contact_criteria(broken)

    def test_edge_factor_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_REAR_CONTACT_CRITERIA)
        broken["edge_zone_ceiling_factor"] = 1.5
        with self.assertRaises(ValueError):
            validate_rear_contact_criteria(broken)

    def test_bond_line_below_accept_height_rejected(self):
        broken = copy.deepcopy(DEFAULT_REAR_CONTACT_CRITERIA)
        broken["bond_line_thickness_mm"] = 0.01
        with self.assertRaises(ValueError):
            validate_rear_contact_criteria(broken)

    def test_zero_deposit_count_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_REAR_CONTACT_CRITERIA)
        broken["max_deposit_count_outside_zone"] = 0
        with self.assertRaises(ValueError):
            validate_rear_contact_criteria(broken)

    def test_fractional_deposit_count_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_REAR_CONTACT_CRITERIA)
        broken["max_deposit_count_outside_zone"] = 2.5
        with self.assertRaises(ValueError):
            validate_rear_contact_criteria(broken)


class GeometryValidationTests(unittest.TestCase):
    def test_welding_zone_bounds_are_returned(self):
        bounds = validate_welding_zone(ZONE)
        self.assertAlmostEqual(bounds["x_min"], 15.0, places=9)
        self.assertAlmostEqual(bounds["y_max"], 25.0, places=9)

    def test_inverted_welding_zone_rejected(self):
        with self.assertRaises(ValueError):
            validate_welding_zone(
                {"x_min": 25.0, "x_max": 15.0, "y_min": 15.0, "y_max": 25.0}
            )

    def test_welding_zone_missing_a_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_welding_zone({"x_min": 15.0, "x_max": 25.0, "y_min": 15.0})

    def test_zero_outline_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_outline({"length_mm": 0.0, "width_mm": 40.0})

    def test_non_mapping_outline_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_outline("40x40")


class ZoneDistanceTests(unittest.TestCase):
    def test_a_point_inside_the_zone_is_at_zero_distance(self):
        self.assertAlmostEqual(
            distance_outside_welding_zone_mm(20.0, 20.0, ZONE), 0.0, places=9
        )

    def test_a_point_on_the_zone_boundary_is_at_zero_distance(self):
        self.assertAlmostEqual(
            distance_outside_welding_zone_mm(25.0, 20.0, ZONE), 0.0, places=9
        )

    def test_a_point_beside_the_zone_measures_along_one_axis(self):
        self.assertAlmostEqual(
            distance_outside_welding_zone_mm(30.0, 20.0, ZONE), 5.0, places=9
        )

    def test_a_point_past_a_corner_measures_diagonally(self):
        self.assertAlmostEqual(
            distance_outside_welding_zone_mm(28.0, 29.0, ZONE),
            math.hypot(3.0, 4.0),
            places=9,
        )

    def test_a_non_numeric_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            distance_outside_welding_zone_mm("30", 20.0, ZONE)


class EdgeDistanceTests(unittest.TestCase):
    def test_edge_distance_takes_the_nearest_side(self):
        self.assertAlmostEqual(
            distance_to_cell_edge_mm(30.0, 20.0, OUTLINE), 10.0, places=9
        )

    def test_a_point_near_the_perimeter_is_close_to_the_edge(self):
        self.assertAlmostEqual(
            distance_to_cell_edge_mm(0.3, 20.0, OUTLINE), 0.3, places=9
        )

    def test_a_point_off_the_outline_rejected(self):
        with self.assertRaises(ValueError):
            distance_to_cell_edge_mm(45.0, 20.0, OUTLINE)

    def test_a_negative_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            distance_to_cell_edge_mm(-1.0, 20.0, OUTLINE)


class FootprintTests(unittest.TestCase):
    def test_footprint_area_is_the_circle_of_that_diameter(self):
        self.assertAlmostEqual(
            deposit_footprint_area_mm2(0.30), math.pi * 0.15 * 0.15, places=12
        )

    def test_a_deposit_of_no_extent_has_no_footprint(self):
        self.assertAlmostEqual(deposit_footprint_area_mm2(0.0), 0.0, places=12)

    def test_negative_diameter_rejected(self):
        with self.assertRaises(ValueError):
            deposit_footprint_area_mm2(-0.10)


class CeilingTests(unittest.TestCase):
    def test_away_from_the_edge_the_full_ceiling_applies(self):
        ceilings = effective_diameter_ceilings_mm(10.0)
        self.assertAlmostEqual(ceilings["factor"], 1.0, places=9)
        self.assertAlmostEqual(ceilings["accept_diameter_mm"], 0.30, places=9)

    def test_inside_the_edge_band_the_ceiling_tightens(self):
        ceilings = effective_diameter_ceilings_mm(0.20)
        self.assertAlmostEqual(ceilings["accept_diameter_mm"], 0.15, places=9)
        self.assertLess(
            ceilings["accept_diameter_mm"],
            DEFAULT_REAR_CONTACT_CRITERIA["accept_deposit_diameter_mm"],
        )

    def test_exactly_on_the_edge_exclusion_keeps_the_full_ceiling(self):
        ceilings = effective_diameter_ceilings_mm(0.50)
        self.assertAlmostEqual(ceilings["factor"], 1.0, places=9)

    def test_negative_edge_distance_rejected(self):
        with self.assertRaises(ValueError):
            effective_diameter_ceilings_mm(-0.10)


class DepositTests(unittest.TestCase):
    def test_a_small_deposit_clear_of_the_zone_is_accepted(self):
        result = assess_rear_deposit(DROP, CLEAN_CELL)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertFalse(result["in_welding_zone"])
        self.assertEqual(result["reasons"], [])

    def test_a_deposit_inside_the_welding_zone_carries_no_ceiling(self):
        result = assess_rear_deposit(
            _drop(x_mm=20.0, y_mm=20.0, diameter_mm=2.0, height_mm=0.5), CLEAN_CELL
        )
        self.assertTrue(result["in_welding_zone"])
        self.assertEqual(result["disposition"], ACCEPT)

    def test_diameter_exactly_on_the_accept_ceiling_is_accepted(self):
        result = assess_rear_deposit(_drop(diameter_mm=0.30), CLEAN_CELL)
        self.assertAlmostEqual(
            result["measurements"]["accept_diameter_mm"], 0.30, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_an_oversize_deposit_can_be_dressed_back(self):
        result = assess_rear_deposit(_drop(diameter_mm=0.45), CLEAN_CELL)
        self.assertEqual(result["disposition"], REWORK)

    def test_diameter_exactly_on_the_rework_ceiling_stays_reworkable(self):
        result = assess_rear_deposit(_drop(diameter_mm=0.60), CLEAN_CELL)
        self.assertEqual(result["disposition"], REWORK)

    def test_a_deposit_past_the_rework_ceiling_rejects(self):
        result = assess_rear_deposit(_drop(diameter_mm=0.90), CLEAN_CELL)
        self.assertEqual(result["disposition"], REJECT)

    def test_the_same_deposit_near_the_cell_edge_loses_its_margin(self):
        result = assess_rear_deposit(_drop(x_mm=0.30, diameter_mm=0.20), CLEAN_CELL)
        self.assertTrue(result["in_edge_band"])
        self.assertEqual(result["disposition"], REWORK)

    def test_the_edge_band_is_named_in_the_reasons(self):
        result = assess_rear_deposit(_drop(x_mm=0.30, diameter_mm=0.20), CLEAN_CELL)
        self.assertTrue(
            any("edge exclusion" in reason for reason in result["reasons"])
        )

    def test_height_exactly_on_the_accept_limit_is_accepted(self):
        result = assess_rear_deposit(_drop(height_mm=0.04), CLEAN_CELL)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_proud_deposit_inside_the_bond_line_is_reworkable(self):
        result = assess_rear_deposit(_drop(height_mm=0.07), CLEAN_CELL)
        self.assertEqual(result["disposition"], REWORK)

    def test_a_deposit_past_the_bond_line_rejects_whatever_its_diameter(self):
        result = assess_rear_deposit(
            _drop(diameter_mm=0.05, height_mm=0.15), CLEAN_CELL
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(any("bond line" in reason for reason in result["reasons"]))

    def test_the_worse_of_the_two_axes_governs(self):
        result = assess_rear_deposit(
            _drop(diameter_mm=0.45, height_mm=0.15), CLEAN_CELL
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_unknown_deposit_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_rear_deposit(_drop(kind="smudge"), CLEAN_CELL)

    def test_deposit_without_a_diameter_rejected(self):
        broken = _drop()
        del broken["diameter_mm"]
        with self.assertRaises(ValueError):
            assess_rear_deposit(broken, CLEAN_CELL)

    def test_negative_height_rejected(self):
        with self.assertRaises(ValueError):
            assess_rear_deposit(_drop(height_mm=-0.01), CLEAN_CELL)

    def test_non_mapping_deposit_rejected(self):
        with self.assertRaises(ValueError):
            assess_rear_deposit("solder-drop", CLEAN_CELL)


class GroupingTests(unittest.TestCase):
    def test_deposits_group_by_kind(self):
        result = group_deposits_by_kind(
            [_drop(), _drop(kind="weld-spatter"), _drop(kind="weld-spatter")]
        )
        self.assertEqual(result["counts"]["solder-drop"], 1)
        self.assertEqual(result["counts"]["weld-spatter"], 2)
        self.assertEqual(result["total"], 3)

    def test_every_kind_appears_in_the_grouping(self):
        result = group_deposits_by_kind([])
        for kind in DEPOSIT_KINDS:
            self.assertIn(kind, result["counts"])

    def test_grouping_an_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            group_deposits_by_kind([_drop(kind="smudge")])

    def test_grouping_a_non_list_rejected(self):
        with self.assertRaises(ValueError):
            group_deposits_by_kind("none")


class RearContactRollupTests(unittest.TestCase):
    def test_a_clear_rear_is_accepted_with_a_record(self):
        result = assess_rear_contact(CLEAN_CELL)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["outside_zone_count"], 0)
        self.assertTrue(any("surveyed" in finding for finding in result["findings"]))

    def test_cell_verdict_takes_the_worst_deposit(self):
        result = assess_rear_contact(
            _cell([_drop(id="A"), _drop(id="B", diameter_mm=0.90)])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["accept_count"], 1)
        self.assertEqual(result["reject_count"], 1)

    def test_in_zone_deposits_are_counted_apart(self):
        result = assess_rear_contact(
            _cell([_drop(id="A"), _drop(id="B", x_mm=20.0, y_mm=20.0)])
        )
        self.assertEqual(result["in_zone_count"], 1)
        self.assertEqual(result["outside_zone_count"], 1)

    def test_in_zone_deposits_stay_out_of_the_area_budget(self):
        result = assess_rear_contact(
            _cell([_drop(id="A", x_mm=20.0, y_mm=20.0, diameter_mm=3.0)])
        )
        self.assertAlmostEqual(result["total_outside_area_mm2"], 0.0, places=12)

    def test_many_acceptable_deposits_still_break_the_area_budget(self):
        criteria = copy.deepcopy(DEFAULT_REAR_CONTACT_CRITERIA)
        criteria["max_total_deposit_area_mm2"] = 0.10
        result = assess_rear_contact(
            _cell(
                [
                    _drop(id="A", diameter_mm=0.30),
                    _drop(id="B", x_mm=32.0, diameter_mm=0.30),
                ]
            ),
            criteria,
        )
        self.assertEqual(result["verdict"], REWORK)
        self.assertTrue(any("add up" in finding for finding in result["findings"]))

    def test_too_many_deposits_break_the_count_budget(self):
        criteria = copy.deepcopy(DEFAULT_REAR_CONTACT_CRITERIA)
        criteria["max_deposit_count_outside_zone"] = 1
        result = assess_rear_contact(
            _cell([_drop(id="A"), _drop(id="B", x_mm=32.0)]), criteria
        )
        self.assertEqual(result["verdict"], REWORK)
        self.assertTrue(
            any("outside the welding zone" in finding for finding in result["findings"])
        )

    def test_edge_band_deposits_are_listed(self):
        result = assess_rear_contact(
            _cell([_drop(id="A"), _drop(id="B", x_mm=0.30, diameter_mm=0.05)])
        )
        self.assertEqual(result["edge_band_ids"], ["B"])

    def test_a_rework_verdict_demands_reinspection(self):
        result = assess_rear_contact(_cell([_drop(id="A", diameter_mm=0.45)]))
        self.assertEqual(result["verdict"], REWORK)
        self.assertTrue(result["reinspection_required"])

    def test_an_accepted_cell_needs_no_reinspection(self):
        self.assertFalse(assess_rear_contact(CLEAN_CELL)["reinspection_required"])

    def test_duplicate_deposit_ids_rejected(self):
        with self.assertRaises(ValueError):
            assess_rear_contact(_cell([_drop(id="A"), _drop(id="A", x_mm=32.0)]))

    def test_cell_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_rear_contact(_cell([], cell_id="  "))

    def test_cell_with_a_non_list_survey_rejected(self):
        cell = copy.deepcopy(CLEAN_CELL)
        cell["deposits"] = "none"
        with self.assertRaises(ValueError):
            assess_rear_contact(cell)

    def test_non_mapping_cell_rejected(self):
        with self.assertRaises(ValueError):
            assess_rear_contact("BARE-CELL-0002")


if __name__ == "__main__":
    unittest.main()
