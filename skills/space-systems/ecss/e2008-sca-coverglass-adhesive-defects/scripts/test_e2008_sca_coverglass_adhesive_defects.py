#!/usr/bin/env python3
"""Contract test for the coverglass adhesive weld-zone screen (offline)."""

import copy
import math
import unittest

from e2008_sca_coverglass_adhesive_defects_logic import (
    ACCEPT,
    ADHESIVE_DISPOSITIONS,
    DEFAULT_ADHESIVE_CRITERIA,
    DISCOLOURATION_GRADES,
    INDICATION_KINDS,
    INSPECTION_INCOMPLETE,
    REFER,
    REJECT,
    assess_adhesive_indication,
    circle_intersection_area_mm2,
    exempt_area_mm2,
    inspect_coverglass_adhesive,
    validate_adhesive_criteria,
    validate_weld_zone,
)

BONDED_AREA_MM2 = 1600.0

WELD_ZONES = [
    {"id": "W1", "centre_x_mm": 0.0, "centre_y_mm": 0.0, "radius_mm": 3.0},
    {"id": "W2", "centre_x_mm": 10.0, "centre_y_mm": 0.0, "radius_mm": 3.0},
]

# Intersection of two unit circles whose centres are one radius apart,
# from the closed form 2 r^2 acos(d / 2r) - (d / 2) sqrt(4 r^2 - d^2).
HALF_OVERLAP_UNIT_CIRCLES = 1.2283696986087567


def _delamination(**overrides):
    indication = {
        "id": "A1",
        "kind": "delamination",
        "centre_x_mm": 30.0,
        "centre_y_mm": 30.0,
        "radius_mm": 0.4,
    }
    indication.update(overrides)
    return indication


def _discolouration(**overrides):
    indication = {
        "id": "D1",
        "kind": "discolouration",
        "centre_x_mm": 30.0,
        "centre_y_mm": 30.0,
        "radius_mm": 1.0,
        "grade": "light",
    }
    indication.update(overrides)
    return indication


def _item(indications=None, **overrides):
    record = {
        "assembly_id": "SCA-CG-01",
        "bonded_area_mm2": BONDED_AREA_MM2,
        "weld_zones": copy.deepcopy(WELD_ZONES),
        "declared_rear_weld_count": 2,
        "indications": copy.deepcopy(indications) if indications else [],
    }
    record.update(overrides)
    return record


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_adhesive_criteria(DEFAULT_ADHESIVE_CRITERIA),
            DEFAULT_ADHESIVE_CRITERIA,
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_adhesive_criteria("default")

    def test_missing_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHESIVE_CRITERIA)
        del broken["max_total_counted_fraction"]
        with self.assertRaises(ValueError):
            validate_adhesive_criteria(broken)

    def test_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHESIVE_CRITERIA)
        broken["delamination_limit_factor"] = 1.5
        with self.assertRaises(ValueError):
            validate_adhesive_criteria(broken)

    def test_single_indication_allowed_more_than_the_bond_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHESIVE_CRITERIA)
        broken["max_indication_area_fraction"] = 0.02
        with self.assertRaises(ValueError):
            validate_adhesive_criteria(broken)

    def test_negligible_area_must_be_positive(self):
        broken = copy.deepcopy(DEFAULT_ADHESIVE_CRITERIA)
        broken["negligible_area_mm2"] = 0.0
        with self.assertRaises(ValueError):
            validate_adhesive_criteria(broken)


class IntersectionGeometryTests(unittest.TestCase):
    def test_separated_footprints_share_nothing(self):
        self.assertAlmostEqual(
            circle_intersection_area_mm2(1.0, 1.0, 3.0), 0.0, places=12
        )

    def test_footprints_exactly_touching_share_nothing(self):
        self.assertAlmostEqual(
            circle_intersection_area_mm2(1.0, 1.0, 2.0), 0.0, places=12
        )

    def test_a_contained_footprint_shares_all_of_itself(self):
        self.assertAlmostEqual(
            circle_intersection_area_mm2(1.0, 2.0, 0.5), math.pi, places=12
        )

    def test_concentric_footprints_share_the_smaller_one(self):
        self.assertAlmostEqual(
            circle_intersection_area_mm2(1.5, 4.0, 0.0), math.pi * 2.25, places=12
        )

    def test_a_half_overlap_matches_the_closed_form(self):
        self.assertAlmostEqual(
            circle_intersection_area_mm2(1.0, 1.0, 1.0),
            HALF_OVERLAP_UNIT_CIRCLES,
            places=9,
        )

    def test_a_partial_overlap_is_between_nothing_and_everything(self):
        overlap = circle_intersection_area_mm2(1.0, 3.0, 3.5)
        self.assertGreater(overlap, 0.0)
        self.assertLess(overlap, math.pi)

    def test_a_negative_radius_rejected(self):
        with self.assertRaises(ValueError):
            circle_intersection_area_mm2(-1.0, 1.0, 0.5)

    def test_a_negative_centre_distance_rejected(self):
        with self.assertRaises(ValueError):
            circle_intersection_area_mm2(1.0, 1.0, -0.5)


class ExemptZoneTests(unittest.TestCase):
    def test_an_indication_behind_a_weld_is_credited_in_full(self):
        credit = exempt_area_mm2(
            {"centre_x_mm": 1.0, "centre_y_mm": 0.0, "radius_mm": 1.0}, WELD_ZONES
        )
        self.assertAlmostEqual(credit["exempt_area_mm2"], math.pi, places=12)
        self.assertEqual(credit["zone_id"], "W1")

    def test_an_indication_clear_of_every_weld_is_credited_nothing(self):
        credit = exempt_area_mm2(
            {"centre_x_mm": 30.0, "centre_y_mm": 30.0, "radius_mm": 1.0}, WELD_ZONES
        )
        self.assertAlmostEqual(credit["exempt_area_mm2"], 0.0, places=12)
        self.assertIsNone(credit["zone_id"])

    def test_the_nearer_weld_gives_the_credit(self):
        credit = exempt_area_mm2(
            {"centre_x_mm": 9.5, "centre_y_mm": 0.0, "radius_mm": 1.0}, WELD_ZONES
        )
        self.assertEqual(credit["zone_id"], "W2")

    def test_overlapping_zones_are_not_added_together(self):
        zones = [
            {"id": "W1", "centre_x_mm": 0.0, "centre_y_mm": 0.0, "radius_mm": 3.0},
            {"id": "W2", "centre_x_mm": 0.2, "centre_y_mm": 0.0, "radius_mm": 3.0},
        ]
        credit = exempt_area_mm2(
            {"centre_x_mm": 0.0, "centre_y_mm": 0.0, "radius_mm": 1.0}, zones
        )
        self.assertAlmostEqual(credit["exempt_area_mm2"], math.pi, places=12)

    def test_a_zone_without_an_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_weld_zone(
                {"centre_x_mm": 0.0, "centre_y_mm": 0.0, "radius_mm": 3.0}
            )

    def test_a_zone_without_a_radius_rejected(self):
        with self.assertRaises(ValueError):
            validate_weld_zone({"id": "W9", "centre_x_mm": 0.0, "centre_y_mm": 0.0})


class IndicationTests(unittest.TestCase):
    def test_delamination_behind_a_weld_accepts_whatever_its_size(self):
        result = assess_adhesive_indication(
            _delamination(centre_x_mm=0.0, centre_y_mm=0.0, radius_mm=2.0),
            WELD_ZONES,
            BONDED_AREA_MM2,
        )
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertTrue(result["wholly_behind_weld"])
        self.assertAlmostEqual(result["counted_area_mm2"], 0.0, places=12)

    def test_a_straddling_indication_is_charged_for_its_overhang(self):
        result = assess_adhesive_indication(
            _delamination(centre_x_mm=2.9, centre_y_mm=0.0, radius_mm=1.0),
            WELD_ZONES,
            BONDED_AREA_MM2,
        )
        self.assertTrue(result["straddles_weld_zone"])
        self.assertFalse(result["wholly_behind_weld"])
        self.assertGreater(result["counted_area_mm2"], 0.0)
        self.assertLess(result["counted_area_mm2"], result["footprint_mm2"])

    def test_a_tiny_delamination_outside_the_zones_accepts(self):
        result = assess_adhesive_indication(
            _delamination(radius_mm=0.2), WELD_ZONES, BONDED_AREA_MM2
        )
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertFalse(result["wholly_behind_weld"])

    def test_a_measurable_delamination_outside_the_zones_refers(self):
        result = assess_adhesive_indication(
            _delamination(), WELD_ZONES, BONDED_AREA_MM2
        )
        self.assertEqual(result["disposition"], REFER)

    def test_a_large_delamination_outside_the_zones_rejects(self):
        result = assess_adhesive_indication(
            _delamination(radius_mm=1.0), WELD_ZONES, BONDED_AREA_MM2
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_the_delamination_limit_is_the_tighter_one(self):
        peeled = assess_adhesive_indication(
            _delamination(), WELD_ZONES, BONDED_AREA_MM2
        )
        darkened = assess_adhesive_indication(
            _discolouration(), WELD_ZONES, BONDED_AREA_MM2
        )
        self.assertAlmostEqual(peeled["limit_mm2"], 0.8, places=9)
        self.assertAlmostEqual(darkened["limit_mm2"], 3.2, places=9)

    def test_the_grade_changes_the_area_a_discolouration_is_charged(self):
        light = assess_adhesive_indication(
            _discolouration(radius_mm=0.5, grade="light"),
            WELD_ZONES,
            BONDED_AREA_MM2,
        )
        dark = assess_adhesive_indication(
            _discolouration(radius_mm=0.5, grade="dark"),
            WELD_ZONES,
            BONDED_AREA_MM2,
        )
        self.assertAlmostEqual(
            light["counted_area_mm2"], dark["counted_area_mm2"], places=12
        )
        self.assertEqual(light["disposition"], ACCEPT)
        self.assertEqual(dark["disposition"], REFER)

    def test_a_dark_patch_past_the_limit_rejects(self):
        result = assess_adhesive_indication(
            _discolouration(radius_mm=1.2, grade="dark"),
            WELD_ZONES,
            BONDED_AREA_MM2,
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_a_discolouration_without_a_grade_rejected(self):
        indication = _discolouration()
        del indication["grade"]
        with self.assertRaises(ValueError):
            assess_adhesive_indication(indication, WELD_ZONES, BONDED_AREA_MM2)

    def test_an_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            assess_adhesive_indication(
                _discolouration(grade="brown"), WELD_ZONES, BONDED_AREA_MM2
            )

    def test_an_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_adhesive_indication(
                _delamination(kind="void"), WELD_ZONES, BONDED_AREA_MM2
            )

    def test_an_indication_larger_than_the_bond_line_rejected(self):
        with self.assertRaises(ValueError):
            assess_adhesive_indication(
                _delamination(radius_mm=30.0), WELD_ZONES, BONDED_AREA_MM2
            )

    def test_non_list_weld_zones_rejected(self):
        with self.assertRaises(ValueError):
            assess_adhesive_indication(_delamination(), "W1", BONDED_AREA_MM2)

    def test_every_declared_kind_and_grade_is_handled(self):
        self.assertEqual(len(INDICATION_KINDS), 2)
        self.assertEqual(len(DISCOLOURATION_GRADES), 3)
        self.assertEqual(len(ADHESIVE_DISPOSITIONS), 3)


class AdhesiveRollupTests(unittest.TestCase):
    def test_a_clean_bond_line_accepts(self):
        result = inspect_coverglass_adhesive(_item())
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["exemption_map_complete"])
        self.assertAlmostEqual(result["counted_area_fraction"], 0.0, places=12)

    def test_everything_behind_the_welds_still_accepts(self):
        indications = [
            _delamination(id="A1", centre_x_mm=0.0, centre_y_mm=0.0, radius_mm=2.0),
            _discolouration(
                id="D1",
                centre_x_mm=10.0,
                centre_y_mm=0.0,
                radius_mm=2.0,
                grade="dark",
            ),
        ]
        result = inspect_coverglass_adhesive(_item(indications))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(sorted(result["wholly_exempt_ids"]), ["A1", "D1"])
        self.assertAlmostEqual(result["counted_area_mm2"], 0.0, places=12)
        self.assertGreater(result["exempt_area_mm2"], 0.0)

    def test_an_unmapped_weld_leaves_the_screen_open(self):
        result = inspect_coverglass_adhesive(_item(declared_rear_weld_count=4))
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertEqual(result["unmapped_weld_count"], 2)
        self.assertFalse(result["exemption_map_complete"])

    def test_more_zones_than_declared_welds_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive(_item(declared_rear_weld_count=1))

    def test_small_indications_together_exceed_the_bond_allowance(self):
        indications = [
            _delamination(id="A%d" % n, centre_x_mm=20.0 + 3.0 * n, radius_mm=0.25)
            for n in range(41)
        ]
        result = inspect_coverglass_adhesive(_item(indications))
        self.assertEqual(result["disposition_counts"][ACCEPT], 41)
        self.assertEqual(result["verdict"], REFER)
        self.assertTrue(any("together" in finding for finding in result["findings"]))

    def test_graded_discolouration_trips_the_transmission_allowance(self):
        indications = [
            _discolouration(
                id="D%d" % n, centre_x_mm=20.0 + 5.0 * n, radius_mm=1.0, grade="dark"
            )
            for n in range(2)
        ]
        result = inspect_coverglass_adhesive(_item(indications))
        self.assertGreater(result["transmission_loss_fraction"], 0.003)
        self.assertTrue(
            any("transmission" in finding for finding in result["findings"])
        )
        self.assertFalse(any("together" in finding for finding in result["findings"]))

    def test_the_worst_indication_drives_the_verdict(self):
        indications = [
            _delamination(id="A1", radius_mm=0.2),
            _delamination(id="A2", centre_x_mm=40.0, radius_mm=1.0),
        ]
        result = inspect_coverglass_adhesive(_item(indications))
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["not_accepted_ids"], ["A2"])

    def test_a_straddling_indication_is_named_in_the_rollup(self):
        indications = [
            _delamination(
                id="A1", centre_x_mm=2.9, centre_y_mm=0.0, radius_mm=1.0
            )
        ]
        result = inspect_coverglass_adhesive(_item(indications))
        self.assertEqual(result["straddling_ids"], ["A1"])
        self.assertEqual(result["wholly_exempt_ids"], [])

    def test_duplicate_indication_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive(_item([_delamination(), _delamination()]))

    def test_duplicate_weld_zone_ids_rejected(self):
        zones = copy.deepcopy(WELD_ZONES)
        zones[1]["id"] = "W1"
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive(_item(weld_zones=zones))

    def test_a_blank_assembly_id_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive(_item(assembly_id="  "))

    def test_non_list_indications_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive(_item(indications="none"))

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive("SCA-CG-01")

    def test_a_bond_line_without_an_area_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive(_item(bonded_area_mm2=0.0))


if __name__ == "__main__":
    unittest.main()
