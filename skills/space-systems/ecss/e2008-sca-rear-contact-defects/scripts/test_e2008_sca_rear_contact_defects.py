#!/usr/bin/env python3
"""Contract test for the rear contact deposit size screen (offline)."""

import copy
import math
import unittest

from e2008_sca_rear_contact_defects_logic import (
    ACCEPT,
    DEFAULT_REAR_DEPOSIT_LIMITS,
    OUTSIDE_WELDING_AREA,
    REAR_DEPOSIT_KINDS,
    REFER,
    REJECT,
    STRADDLING_WELDING_BOUNDARY,
    WITHIN_WELDING_AREA,
    assess_rear_deposit,
    deposit_footprint,
    inspect_rear_contact,
    locate_deposit,
    validate_rear_deposit_limits,
    welding_area_layout,
)

FACE_WIDTH = 40.0
FACE_HEIGHT = 80.0
GOVERNED_AREA = FACE_WIDTH * FACE_HEIGHT - 2 * 30.0 * 10.0


def _welding_areas():
    return [
        {"area_id": "W1", "x_mm": 5.0, "y_mm": 5.0, "width_mm": 30.0, "height_mm": 10.0},
        {"area_id": "W2", "x_mm": 5.0, "y_mm": 65.0, "width_mm": 30.0, "height_mm": 10.0},
    ]


def _rear_face(areas=None):
    return {
        "width_mm": FACE_WIDTH,
        "height_mm": FACE_HEIGHT,
        "welding_areas": _welding_areas() if areas is None else areas,
    }


def _deposit(
    deposit_id="D1",
    kind="weld-drop",
    x_mm=20.0,
    y_mm=40.0,
    diameter_mm=0.4,
    standoff_height_mm=0.05,
):
    return {
        "deposit_id": deposit_id,
        "kind": kind,
        "x_mm": x_mm,
        "y_mm": y_mm,
        "diameter_mm": diameter_mm,
        "standoff_height_mm": standoff_height_mm,
    }


def _assembly(deposits, areas=None, assembly_id="SCA-001"):
    return {
        "assembly_id": assembly_id,
        "rear_face": _rear_face(areas),
        "deposits": deposits,
    }


def _graded_areas():
    return welding_area_layout(_rear_face())["welding_areas"]


class LimitValidationTests(unittest.TestCase):
    def test_default_limits_validate(self):
        self.assertIs(
            validate_rear_deposit_limits(DEFAULT_REAR_DEPOSIT_LIMITS),
            DEFAULT_REAR_DEPOSIT_LIMITS,
        )

    def test_non_mapping_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_rear_deposit_limits("default")

    def test_missing_kind_in_diameter_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_REAR_DEPOSIT_LIMITS)
        del broken["max_diameter_mm"]["weld-spatter"]
        with self.assertRaises(ValueError):
            validate_rear_deposit_limits(broken)

    def test_negative_diameter_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_REAR_DEPOSIT_LIMITS)
        broken["max_diameter_mm"]["weld-drop"] = -0.1
        with self.assertRaises(ValueError):
            validate_rear_deposit_limits(broken)

    def test_covered_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_REAR_DEPOSIT_LIMITS)
        broken["max_covered_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_rear_deposit_limits(broken)

    def test_contradictory_size_allowances_rejected(self):
        broken = copy.deepcopy(DEFAULT_REAR_DEPOSIT_LIMITS)
        broken["max_diameter_mm"]["weld-spatter"] = 0.0
        with self.assertRaises(ValueError):
            validate_rear_deposit_limits(broken)

    def test_review_margin_factor_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_REAR_DEPOSIT_LIMITS)
        broken["review_margin_factor"] = 0.9
        with self.assertRaises(ValueError):
            validate_rear_deposit_limits(broken)

    def test_the_clause_names_two_deposit_kinds(self):
        self.assertEqual(len(REAR_DEPOSIT_KINDS), 2)


class LayoutTests(unittest.TestCase):
    def test_governed_area_is_the_rear_face_less_the_welding_areas(self):
        layout = welding_area_layout(_rear_face())
        self.assertAlmostEqual(layout["rear_area_mm2"], 3200.0, places=9)
        self.assertAlmostEqual(layout["welding_area_mm2"], 600.0, places=9)
        self.assertAlmostEqual(layout["governed_area_mm2"], GOVERNED_AREA, places=9)

    def test_welding_area_covering_the_whole_face_is_refused(self):
        whole = [
            {
                "area_id": "W1",
                "x_mm": 0.0,
                "y_mm": 0.0,
                "width_mm": FACE_WIDTH,
                "height_mm": FACE_HEIGHT,
            }
        ]
        with self.assertRaises(ValueError):
            welding_area_layout(_rear_face(whole))

    def test_overlapping_welding_areas_refused(self):
        areas = _welding_areas()
        areas[1]["y_mm"] = 10.0
        with self.assertRaises(ValueError):
            welding_area_layout(_rear_face(areas))

    def test_welding_area_past_the_rear_face_refused(self):
        areas = _welding_areas()
        areas[0]["width_mm"] = 60.0
        with self.assertRaises(ValueError):
            welding_area_layout(_rear_face(areas))

    def test_duplicate_welding_area_id_refused(self):
        areas = _welding_areas()
        areas[1]["area_id"] = "W1"
        with self.assertRaises(ValueError):
            welding_area_layout(_rear_face(areas))


class PlacementTests(unittest.TestCase):
    def test_deposit_well_inside_a_welding_area_is_within_it(self):
        footprint = deposit_footprint(_deposit(x_mm=20.0, y_mm=10.0))
        placement, area_id = locate_deposit(footprint, _graded_areas())
        self.assertEqual(placement, WITHIN_WELDING_AREA)
        self.assertEqual(area_id, "W1")

    def test_footprint_touching_the_boundary_exactly_is_still_within(self):
        footprint = deposit_footprint(
            _deposit(x_mm=5.2, y_mm=10.0, diameter_mm=0.4)
        )
        self.assertAlmostEqual(
            footprint["x_mm"] - footprint["radius_mm"], 5.0, places=9
        )
        placement, _ = locate_deposit(footprint, _graded_areas())
        self.assertEqual(placement, WITHIN_WELDING_AREA)

    def test_footprint_reaching_across_the_boundary_straddles_it(self):
        footprint = deposit_footprint(
            _deposit(x_mm=5.1, y_mm=10.0, diameter_mm=0.5)
        )
        placement, area_id = locate_deposit(footprint, _graded_areas())
        self.assertEqual(placement, STRADDLING_WELDING_BOUNDARY)
        self.assertEqual(area_id, "W1")

    def test_deposit_clear_of_every_welding_area_is_outside(self):
        footprint = deposit_footprint(_deposit(x_mm=20.0, y_mm=40.0))
        placement, area_id = locate_deposit(footprint, _graded_areas())
        self.assertEqual(placement, OUTSIDE_WELDING_AREA)
        self.assertIsNone(area_id)

    def test_footprint_area_follows_the_diameter(self):
        footprint = deposit_footprint(_deposit(diameter_mm=0.5))
        self.assertAlmostEqual(footprint["radius_mm"], 0.25, places=9)
        self.assertAlmostEqual(
            footprint["covered_area_mm2"], math.pi * 0.0625, places=9
        )

    def test_unknown_deposit_kind_rejected(self):
        with self.assertRaises(ValueError):
            deposit_footprint(_deposit(kind="paint-run"))

    def test_zero_diameter_deposit_rejected(self):
        with self.assertRaises(ValueError):
            deposit_footprint(_deposit(diameter_mm=0.0))

    def test_missing_deposit_id_rejected(self):
        record = _deposit()
        del record["deposit_id"]
        with self.assertRaises(ValueError):
            deposit_footprint(record)


class DepositSizeTests(unittest.TestCase):
    def test_deposit_on_the_size_allowance_accepts(self):
        allowed = float(DEFAULT_REAR_DEPOSIT_LIMITS["max_diameter_mm"]["weld-drop"])
        result = assess_rear_deposit(
            _deposit(diameter_mm=allowed), _graded_areas()
        )
        self.assertAlmostEqual(result["diameter_mm"], allowed, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_deposit_just_past_the_allowance_refers(self):
        result = assess_rear_deposit(
            _deposit(diameter_mm=0.6), _graded_areas()
        )
        self.assertEqual(result["verdict"], REFER)

    def test_deposit_far_past_the_allowance_rejects(self):
        result = assess_rear_deposit(
            _deposit(diameter_mm=1.2), _graded_areas()
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_a_proud_deposit_fails_on_standoff_with_diameter_in_hand(self):
        result = assess_rear_deposit(
            _deposit(diameter_mm=0.3, standoff_height_mm=0.40), _graded_areas()
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(
            any("standoff height" in finding for finding in result["findings"])
        )

    def test_spatter_is_held_tighter_than_a_drop_at_the_same_size(self):
        drop = assess_rear_deposit(
            _deposit(kind="weld-drop", diameter_mm=0.28), _graded_areas()
        )
        spatter = assess_rear_deposit(
            _deposit(kind="weld-spatter", diameter_mm=0.28, standoff_height_mm=0.02),
            _graded_areas(),
        )
        self.assertEqual(drop["verdict"], ACCEPT)
        self.assertEqual(spatter["verdict"], REFER)

    def test_an_oversize_deposit_inside_the_welding_area_is_not_governed(self):
        result = assess_rear_deposit(
            _deposit(x_mm=20.0, y_mm=10.0, diameter_mm=2.0, standoff_height_mm=0.9),
            _graded_areas(),
        )
        self.assertFalse(result["governed"])
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["placement"], WITHIN_WELDING_AREA)

    def test_a_straddling_deposit_is_graded_as_an_outside_one(self):
        result = assess_rear_deposit(
            _deposit(x_mm=5.1, y_mm=10.0, diameter_mm=0.9), _graded_areas()
        )
        self.assertTrue(result["governed"])
        self.assertEqual(result["placement"], STRADDLING_WELDING_BOUNDARY)
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(
            any("reaches across the boundary" in f for f in result["findings"])
        )


class RearContactRollupTests(unittest.TestCase):
    def test_clean_rear_contact_accepts(self):
        result = inspect_rear_contact(_assembly([_deposit()]))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["governed_deposit_count"], 1)
        self.assertEqual(result["not_accepted_ids"], [])

    def test_no_deposits_at_all_accepts(self):
        result = inspect_rear_contact(_assembly([]))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["deposit_count"], 0)
        self.assertAlmostEqual(result["covered_fraction"], 0.0, places=9)

    def test_exempt_deposits_are_named_and_left_out_of_the_covered_area(self):
        deposits = [
            _deposit("D1", x_mm=20.0, y_mm=10.0, diameter_mm=1.0),
            _deposit("D2", x_mm=20.0, y_mm=40.0, diameter_mm=0.4),
        ]
        result = inspect_rear_contact(_assembly(deposits))
        self.assertEqual(result["within_welding_area_ids"], ["D1"])
        self.assertEqual(result["governed_deposit_count"], 1)
        self.assertAlmostEqual(
            result["covered_area_mm2"], math.pi * 0.04, places=9
        )

    def test_covered_fraction_exactly_on_the_allowance_accepts(self):
        deposits = [
            _deposit("D1", x_mm=20.0, y_mm=40.0, diameter_mm=0.5),
            _deposit("D2", x_mm=25.0, y_mm=40.0, diameter_mm=0.5),
        ]
        exact = (2.0 * math.pi * 0.0625) / GOVERNED_AREA
        limits = copy.deepcopy(DEFAULT_REAR_DEPOSIT_LIMITS)
        limits["max_covered_fraction"] = exact
        result = inspect_rear_contact(_assembly(deposits), limits)
        self.assertAlmostEqual(result["covered_fraction"], exact, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_cumulative_cover_refers_with_every_deposit_in_size(self):
        deposits = [
            _deposit("D1", x_mm=20.0, y_mm=40.0, diameter_mm=0.5),
            _deposit("D2", x_mm=25.0, y_mm=40.0, diameter_mm=0.5),
        ]
        limits = copy.deepcopy(DEFAULT_REAR_DEPOSIT_LIMITS)
        limits["max_covered_fraction"] = 1.3e-4
        result = inspect_rear_contact(_assembly(deposits), limits)
        self.assertEqual(result["disposition_counts"][ACCEPT], 2)
        self.assertEqual(result["verdict"], REFER)
        self.assertTrue(
            any("no single one was oversize" in f for f in result["findings"])
        )

    def test_cumulative_cover_far_past_the_allowance_rejects(self):
        deposits = [
            _deposit("D1", x_mm=20.0, y_mm=40.0, diameter_mm=0.5),
            _deposit("D2", x_mm=25.0, y_mm=40.0, diameter_mm=0.5),
        ]
        limits = copy.deepcopy(DEFAULT_REAR_DEPOSIT_LIMITS)
        limits["max_covered_fraction"] = 5.0e-5
        result = inspect_rear_contact(_assembly(deposits), limits)
        self.assertEqual(result["verdict"], REJECT)

    def test_worst_deposit_drives_the_assembly_verdict(self):
        deposits = [
            _deposit("D1", diameter_mm=0.4),
            _deposit("D2", x_mm=25.0, diameter_mm=0.6),
            _deposit("D3", x_mm=30.0, diameter_mm=1.4),
        ]
        result = inspect_rear_contact(_assembly(deposits))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["not_accepted_ids"], ["D2", "D3"])
        self.assertEqual(result["disposition_counts"][REFER], 1)
        self.assertEqual(result["disposition_counts"][REJECT], 1)

    def test_straddling_deposits_are_listed_on_the_rollup(self):
        deposits = [_deposit("D1", x_mm=5.1, y_mm=10.0, diameter_mm=0.4)]
        result = inspect_rear_contact(_assembly(deposits))
        self.assertEqual(result["straddling_ids"], ["D1"])
        self.assertEqual(result["governed_deposit_count"], 1)

    def test_deposit_reaching_past_the_rear_face_rejected(self):
        deposits = [_deposit("D1", x_mm=39.9, y_mm=40.0, diameter_mm=0.5)]
        with self.assertRaises(ValueError):
            inspect_rear_contact(_assembly(deposits))

    def test_duplicate_deposit_ids_rejected(self):
        deposits = [_deposit("D1"), _deposit("D1", x_mm=25.0)]
        with self.assertRaises(ValueError):
            inspect_rear_contact(_assembly(deposits))

    def test_deposits_not_a_list_rejected(self):
        assembly = _assembly([])
        assembly["deposits"] = "one drop"
        with self.assertRaises(ValueError):
            inspect_rear_contact(assembly)

    def test_non_mapping_assembly_rejected(self):
        with self.assertRaises(ValueError):
            inspect_rear_contact("SCA-001")

    def test_missing_rear_face_rejected(self):
        assembly = _assembly([])
        del assembly["rear_face"]
        with self.assertRaises(ValueError):
            inspect_rear_contact(assembly)

    def test_stricter_project_limit_set_is_honoured(self):
        deposits = [_deposit("D1", diameter_mm=0.45)]
        strict = copy.deepcopy(DEFAULT_REAR_DEPOSIT_LIMITS)
        strict["max_diameter_mm"]["weld-drop"] = 0.20
        loose = inspect_rear_contact(_assembly(copy.deepcopy(deposits)))
        tight = inspect_rear_contact(_assembly(copy.deepcopy(deposits)), strict)
        self.assertEqual(loose["verdict"], ACCEPT)
        self.assertEqual(tight["verdict"], REJECT)
        self.assertEqual(tight["not_accepted_ids"], ["D1"])


if __name__ == "__main__":
    unittest.main()
