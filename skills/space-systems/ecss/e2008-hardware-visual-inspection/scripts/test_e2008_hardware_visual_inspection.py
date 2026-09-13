#!/usr/bin/env python3
"""Contract test for the coupon hardware visual inspection (offline)."""

import copy
import unittest

from e2008_hardware_visual_inspection_logic import (
    ACCEPT,
    DEFAULT_HARDWARE_CRITERIA,
    HARDWARE_CONDITION_KINDS,
    HARDWARE_TYPES,
    HARDWARE_ZONES,
    NOT_TOLERATED_KINDS,
    REJECT,
    REWORK,
    angular_deviation_deg,
    assess_clearance,
    assess_hardware_condition,
    assess_hardware_item,
    assess_orientation,
    assess_placement,
    assess_retention,
    clearance_margin_mm,
    group_hardware_by_type,
    inspect_coupon_hardware,
    is_interfering,
    placement_offset_mm,
    reconcile_hardware_inventory,
    retention_completeness_fraction,
    validate_hardware_criteria,
    zone_tolerance_factor,
)

SOUND_ITEM = {
    "hardware_id": "TB-01",
    "hardware_type": "terminal-board",
    "zone": "substrate-rear-face",
    "nominal_position_mm": [50.0, 80.0],
    "measured_position_mm": [50.3, 80.2],
    "nominal_orientation_deg": 0.0,
    "measured_orientation_deg": 0.4,
    "fasteners_required": 4,
    "fasteners_installed": 4,
    "measured_clearance_mm": 3.5,
    "conditions": [],
}

VOID = {
    "id": "TB-01-A",
    "kind": "adhesive-fillet-void",
    "zone": "substrate-rear-face",
    "area_mm2": 1.0,
}


def _item(**overrides):
    record = copy.deepcopy(SOUND_ITEM)
    record.update(overrides)
    return record


def _moved(dx, dy, **overrides):
    record = _item(**overrides)
    record["measured_position_mm"] = [50.0 + dx, 80.0 + dy]
    return record


def _condition(**overrides):
    record = copy.deepcopy(VOID)
    record.update(overrides)
    return record


def _coupon(items, **overrides):
    coupon = {"coupon_id": "PV-COUPON-11", "hardware": items}
    coupon.update(overrides)
    return coupon


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_hardware_criteria(DEFAULT_HARDWARE_CRITERIA),
            DEFAULT_HARDWARE_CRITERIA,
        )

    def test_criteria_cover_every_zone(self):
        for zone in HARDWARE_ZONES:
            self.assertIn(
                zone, DEFAULT_HARDWARE_CRITERIA["zone_tolerance_factor"]
            )

    def test_not_tolerated_kinds_are_real_kinds(self):
        for kind in NOT_TOLERATED_KINDS:
            self.assertIn(kind, HARDWARE_CONDITION_KINDS)

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_hardware_criteria("default")

    def test_criteria_missing_a_graded_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_HARDWARE_CRITERIA)
        del broken["accept_area_mm2"]["adhesive-fillet-void"]
        with self.assertRaises(ValueError):
            validate_hardware_criteria(broken)

    def test_rework_area_below_accept_area_rejected(self):
        broken = copy.deepcopy(DEFAULT_HARDWARE_CRITERIA)
        broken["rework_area_mm2"]["adhesive-fillet-void"] = 0.5
        with self.assertRaises(ValueError):
            validate_hardware_criteria(broken)

    def test_rework_placement_below_accept_placement_rejected(self):
        broken = copy.deepcopy(DEFAULT_HARDWARE_CRITERIA)
        broken["rework_placement_offset_mm"] = 0.5
        with self.assertRaises(ValueError):
            validate_hardware_criteria(broken)

    def test_rework_angle_below_accept_angle_rejected(self):
        broken = copy.deepcopy(DEFAULT_HARDWARE_CRITERIA)
        broken["rework_angular_deviation_deg"] = 0.5
        with self.assertRaises(ValueError):
            validate_hardware_criteria(broken)

    def test_rework_retention_above_the_accept_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_HARDWARE_CRITERIA)
        broken["rework_retention_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_hardware_criteria(broken)

    def test_accept_retention_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_HARDWARE_CRITERIA)
        broken["accept_retention_fraction"] = 1.2
        with self.assertRaises(ValueError):
            validate_hardware_criteria(broken)

    def test_rework_clearance_above_the_protected_minimum_rejected(self):
        broken = copy.deepcopy(DEFAULT_HARDWARE_CRITERIA)
        broken["rework_clearance_mm"] = 4.0
        with self.assertRaises(ValueError):
            validate_hardware_criteria(broken)

    def test_cell_field_margin_is_stricter_than_the_rear_face(self):
        self.assertLess(
            zone_tolerance_factor("cell-field-margin"),
            zone_tolerance_factor("substrate-rear-face"),
        )

    def test_unknown_zone_rejected(self):
        with self.assertRaises(ValueError):
            zone_tolerance_factor("somewhere-on-the-coupon")


class PlacementGeometryTests(unittest.TestCase):
    def test_offset_is_the_true_position_radius(self):
        self.assertAlmostEqual(
            placement_offset_mm([0.0, 0.0], [0.6, 0.8]), 1.0, places=9
        )

    def test_an_item_on_its_centre_has_no_offset(self):
        self.assertAlmostEqual(
            placement_offset_mm([4.0, 5.0], [4.0, 5.0]), 0.0, places=9
        )

    def test_non_pair_position_rejected(self):
        with self.assertRaises(ValueError):
            placement_offset_mm("origin", [0.0, 0.0])

    def test_three_coordinate_position_rejected(self):
        with self.assertRaises(ValueError):
            placement_offset_mm([0.0, 0.0], [1.0, 2.0, 3.0])

    def test_non_numeric_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            placement_offset_mm([0.0, 0.0], [1.0, None])


class AngularTests(unittest.TestCase):
    def test_rotation_is_taken_the_shorter_way_round(self):
        self.assertAlmostEqual(angular_deviation_deg(359.0, 1.0), 2.0, places=9)

    def test_rotation_is_a_magnitude(self):
        self.assertAlmostEqual(angular_deviation_deg(10.0, 7.0), 3.0, places=9)

    def test_an_item_on_its_drawing_angle_has_no_deviation(self):
        self.assertAlmostEqual(angular_deviation_deg(45.0, 45.0), 0.0, places=9)

    def test_a_full_turn_is_the_same_orientation(self):
        self.assertAlmostEqual(angular_deviation_deg(30.0, 390.0), 0.0, places=9)

    def test_a_half_turn_is_the_largest_deviation(self):
        self.assertAlmostEqual(angular_deviation_deg(0.0, 180.0), 180.0, places=9)

    def test_non_numeric_orientation_rejected(self):
        with self.assertRaises(ValueError):
            angular_deviation_deg(0.0, "north")


class RetentionTests(unittest.TestCase):
    def test_full_retention_is_one(self):
        self.assertAlmostEqual(retention_completeness_fraction(4, 4), 1.0, places=9)

    def test_a_missing_fastener_lowers_the_fraction(self):
        self.assertAlmostEqual(retention_completeness_fraction(3, 4), 0.75, places=9)

    def test_more_fasteners_than_the_drawing_rejected(self):
        with self.assertRaises(ValueError):
            retention_completeness_fraction(5, 4)

    def test_a_zero_drawing_count_rejected(self):
        with self.assertRaises(ValueError):
            retention_completeness_fraction(0, 0)

    def test_a_fractional_fastener_count_rejected(self):
        with self.assertRaises(ValueError):
            retention_completeness_fraction(2.5, 4)

    def test_a_boolean_fastener_count_rejected(self):
        with self.assertRaises(ValueError):
            retention_completeness_fraction(True, 4)

    def test_a_negative_fastener_count_rejected(self):
        with self.assertRaises(ValueError):
            retention_completeness_fraction(-1, 4)


class ClearanceTests(unittest.TestCase):
    def test_margin_is_the_gap_over_the_protected_minimum(self):
        self.assertAlmostEqual(clearance_margin_mm(3.5), 1.5, places=9)

    def test_a_tight_gap_has_a_negative_margin(self):
        self.assertLess(clearance_margin_mm(0.5), 0.0)

    def test_a_touching_item_is_interfering(self):
        self.assertTrue(is_interfering(0.0))

    def test_an_overlapping_item_is_interfering(self):
        self.assertTrue(is_interfering(-0.4))

    def test_a_tight_but_clear_item_is_not_interfering(self):
        self.assertFalse(is_interfering(0.5))

    def test_non_numeric_clearance_rejected(self):
        with self.assertRaises(ValueError):
            is_interfering("close")


class InventoryTests(unittest.TestCase):
    def test_a_matched_inventory_is_complete(self):
        result = reconcile_hardware_inventory(["TB-01", "BR-02"], ["BR-02", "TB-01"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])

    def test_a_drawing_item_not_fitted_is_missing(self):
        result = reconcile_hardware_inventory(["TB-01", "BR-02"], ["TB-01"])
        self.assertEqual(result["missing"], ["BR-02"])
        self.assertFalse(result["complete"])

    def test_an_item_the_drawing_never_called_is_undrawn(self):
        result = reconcile_hardware_inventory(["TB-01"], ["TB-01", "XX-09"])
        self.assertEqual(result["undrawn"], ["XX-09"])

    def test_a_repeated_identifier_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_hardware_inventory(["TB-01", "TB-01"], ["TB-01"])

    def test_a_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_hardware_inventory(["TB-01", " "], ["TB-01"])

    def test_a_bare_string_inventory_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_hardware_inventory("TB-01", ["TB-01"])


class PlacementDispositionTests(unittest.TestCase):
    def test_an_item_inside_tolerance_is_accepted(self):
        result = assess_placement(0.4, "substrate-rear-face")
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_offset_exactly_on_the_accept_limit_is_accepted(self):
        offset = placement_offset_mm([0.0, 0.0], [0.6, 0.8])
        result = assess_placement(offset, "substrate-rear-face")
        self.assertAlmostEqual(
            result["measurements"]["accept_placement_offset_mm"], 1.0, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_the_same_offset_in_the_cell_field_margin_loses_its_margin(self):
        offset = placement_offset_mm([0.0, 0.0], [0.6, 0.8])
        result = assess_placement(offset, "cell-field-margin")
        self.assertAlmostEqual(
            result["measurements"]["accept_placement_offset_mm"], 0.5, places=9
        )
        self.assertEqual(result["disposition"], REWORK)

    def test_offset_past_the_rework_limit_rejects(self):
        result = assess_placement(4.0, "substrate-rear-face")
        self.assertEqual(result["disposition"], REJECT)

    def test_negative_offset_rejected(self):
        with self.assertRaises(ValueError):
            assess_placement(-0.1, "substrate-rear-face")


class OrientationDispositionTests(unittest.TestCase):
    def test_a_square_item_is_accepted(self):
        result = assess_orientation(0.4, "substrate-rear-face")
        self.assertEqual(result["disposition"], ACCEPT)

    def test_rotation_exactly_on_the_accept_limit_is_accepted(self):
        result = assess_orientation(1.0, "substrate-rear-face")
        self.assertAlmostEqual(
            result["measurements"]["accept_angular_deviation_deg"], 1.0, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_rotation_past_the_accept_limit_reworks(self):
        result = assess_orientation(3.0, "substrate-rear-face")
        self.assertEqual(result["disposition"], REWORK)

    def test_rotation_past_the_rework_limit_rejects(self):
        result = assess_orientation(8.0, "substrate-rear-face")
        self.assertEqual(result["disposition"], REJECT)

    def test_the_same_rotation_in_the_cell_field_margin_loses_its_margin(self):
        result = assess_orientation(1.0, "cell-field-margin")
        self.assertAlmostEqual(
            result["measurements"]["accept_angular_deviation_deg"], 0.5, places=9
        )
        self.assertEqual(result["disposition"], REWORK)


class RetentionDispositionTests(unittest.TestCase):
    def test_every_fastener_installed_is_accepted(self):
        result = assess_retention(4, 4)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertAlmostEqual(
            result["measurements"]["retention_completeness_fraction"],
            1.0,
            places=9,
        )

    def test_retention_exactly_on_the_rework_floor_stays_reworkable(self):
        result = assess_retention(3, 4)
        self.assertAlmostEqual(
            result["measurements"]["retention_completeness_fraction"],
            0.75,
            places=9,
        )
        self.assertEqual(result["disposition"], REWORK)

    def test_retention_under_the_rework_floor_rejects(self):
        result = assess_retention(2, 4)
        self.assertEqual(result["disposition"], REJECT)

    def test_no_fastener_installed_rejects(self):
        result = assess_retention(0, 4)
        self.assertEqual(result["disposition"], REJECT)


class ClearanceDispositionTests(unittest.TestCase):
    def test_a_clear_item_is_accepted(self):
        result = assess_clearance(3.5)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertTrue(result["tolerated"])

    def test_clearance_exactly_on_the_protected_minimum_is_accepted(self):
        result = assess_clearance(2.0)
        self.assertAlmostEqual(
            result["measurements"]["clearance_margin_mm"], 0.0, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_clearance_under_the_minimum_reworks(self):
        result = assess_clearance(1.5)
        self.assertEqual(result["disposition"], REWORK)

    def test_clearance_under_the_rework_floor_rejects_but_is_tolerated(self):
        result = assess_clearance(0.5)
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(result["tolerated"])

    def test_a_touching_item_rejects_as_not_tolerated(self):
        result = assess_clearance(0.0)
        self.assertEqual(result["disposition"], REJECT)
        self.assertFalse(result["tolerated"])

    def test_an_overlapping_item_rejects_as_not_tolerated(self):
        result = assess_clearance(-1.0)
        self.assertFalse(result["tolerated"])
        self.assertTrue(
            any("no allowance" in reason for reason in result["reasons"])
        )


class ConditionTests(unittest.TestCase):
    def test_a_small_fillet_void_is_accepted(self):
        result = assess_hardware_condition(VOID)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertTrue(result["tolerated"])

    def test_void_area_exactly_on_the_accept_limit_is_accepted(self):
        result = assess_hardware_condition(_condition(area_mm2=2.0))
        self.assertAlmostEqual(
            result["measurements"]["accept_area_mm2"], 2.0, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_the_same_void_in_the_cell_field_margin_loses_its_margin(self):
        result = assess_hardware_condition(
            _condition(area_mm2=2.0, zone="cell-field-margin")
        )
        self.assertAlmostEqual(
            result["measurements"]["accept_area_mm2"], 1.0, places=9
        )
        self.assertEqual(result["disposition"], REWORK)

    def test_area_past_the_rework_limit_rejects(self):
        result = assess_hardware_condition(_condition(area_mm2=20.0))
        self.assertEqual(result["disposition"], REJECT)

    def test_a_missing_item_rejects_on_presence(self):
        result = assess_hardware_condition(
            _condition(kind="missing-hardware-item")
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertFalse(result["tolerated"])

    def test_an_unsecured_item_rejects_on_presence(self):
        result = assess_hardware_condition(
            _condition(kind="unsecured-hardware-item")
        )
        self.assertTrue(
            any("no allowance" in reason for reason in result["reasons"])
        )

    def test_a_not_tolerated_kind_ignores_the_zone_factor(self):
        strict = assess_hardware_condition(
            _condition(kind="stay-out-interference", zone="cell-field-margin")
        )
        loose = assess_hardware_condition(
            _condition(kind="stay-out-interference", zone="substrate-rear-face")
        )
        self.assertEqual(strict["disposition"], loose["disposition"])

    def test_unknown_condition_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_condition(_condition(kind="scuff"))

    def test_a_measured_leg_logged_as_a_condition_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_condition(_condition(kind="retention-shortfall"))

    def test_non_mapping_condition_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_condition("adhesive-fillet-void")

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_condition(_condition(area_mm2=-1.0))


class GroupingTests(unittest.TestCase):
    def test_items_group_by_type(self):
        result = group_hardware_by_type(
            [
                _item(),
                _item(hardware_type="standoff"),
                _item(hardware_type="standoff"),
            ]
        )
        self.assertEqual(result["counts"]["terminal-board"], 1)
        self.assertEqual(result["counts"]["standoff"], 2)
        self.assertEqual(result["recorded"], 3)

    def test_every_type_appears_in_the_grouping(self):
        result = group_hardware_by_type([])
        for hardware_type in HARDWARE_TYPES:
            self.assertIn(hardware_type, result["counts"])

    def test_grouping_an_unknown_type_rejected(self):
        with self.assertRaises(ValueError):
            group_hardware_by_type([_item(hardware_type="widget")])

    def test_grouping_a_bare_string_rejected(self):
        with self.assertRaises(ValueError):
            group_hardware_by_type("TB-01")


class HardwareItemTests(unittest.TestCase):
    def test_a_sound_item_is_accepted(self):
        result = assess_hardware_item(SOUND_ITEM)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertTrue(result["as_drawn"])
        self.assertTrue(result["fully_retained"])
        self.assertFalse(result["interfering"])

    def test_item_disposition_takes_the_worst_leg(self):
        result = assess_hardware_item(_moved(4.0, 0.0))
        self.assertEqual(result["disposition"], REJECT)
        self.assertEqual(result["retention_disposition"], ACCEPT)
        self.assertFalse(result["as_drawn"])

    def test_a_rotated_board_is_caught_with_its_centre_on_the_spot(self):
        result = assess_hardware_item(
            _item(measured_position_mm=[50.0, 80.0], measured_orientation_deg=3.0)
        )
        self.assertEqual(result["placement_disposition"], ACCEPT)
        self.assertEqual(result["orientation_disposition"], REWORK)
        self.assertEqual(result["disposition"], REWORK)

    def test_the_shorter_way_round_is_used_on_the_record(self):
        result = assess_hardware_item(
            _item(nominal_orientation_deg=359.0, measured_orientation_deg=1.0)
        )
        self.assertAlmostEqual(
            result["measurements"]["angular_deviation_deg"], 2.0, places=9
        )
        self.assertEqual(result["orientation_disposition"], REWORK)

    def test_a_short_fastener_count_reworks_a_well_placed_item(self):
        result = assess_hardware_item(_item(fasteners_installed=3))
        self.assertEqual(result["disposition"], REWORK)
        self.assertFalse(result["fully_retained"])
        self.assertTrue(result["as_drawn"])

    def test_an_interfering_item_is_flagged_on_the_record(self):
        result = assess_hardware_item(_item(measured_clearance_mm=0.0))
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(result["interfering"])

    def test_a_not_tolerated_condition_names_itself_on_the_item(self):
        result = assess_hardware_item(
            _item(conditions=[_condition(kind="unsecured-hardware-item")])
        )
        self.assertEqual(result["not_tolerated_ids"], ["TB-01-A"])

    def test_conditions_default_to_an_empty_survey(self):
        record = _item()
        del record["conditions"]
        self.assertEqual(assess_hardware_item(record)["conditions"], [])

    def test_orientation_defaults_to_the_drawing_angle(self):
        record = _item()
        del record["nominal_orientation_deg"]
        del record["measured_orientation_deg"]
        self.assertAlmostEqual(
            assess_hardware_item(record)["measurements"]["angular_deviation_deg"],
            0.0,
            places=9,
        )

    def test_item_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_item(_item(hardware_id="  "))

    def test_item_without_a_fastener_count_rejected(self):
        record = _item()
        del record["fasteners_required"]
        with self.assertRaises(ValueError):
            assess_hardware_item(record)

    def test_item_without_a_clearance_measurement_rejected(self):
        record = _item()
        del record["measured_clearance_mm"]
        with self.assertRaises(ValueError):
            assess_hardware_item(record)

    def test_unknown_hardware_type_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_item(_item(hardware_type="widget"))

    def test_non_list_conditions_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_item(_item(conditions="none"))

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            assess_hardware_item("TB-01")


class CouponTests(unittest.TestCase):
    def test_a_coupon_with_no_records_still_produces_a_finding(self):
        result = inspect_coupon_hardware(_coupon([]))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(
            any("no hardware records" in item for item in result["findings"])
        )

    def test_coupon_verdict_takes_the_worst_item(self):
        result = inspect_coupon_hardware(
            _coupon([_item(), _moved(4.0, 0.0, hardware_id="TB-02")])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["reject_count"], 1)
        self.assertEqual(result["accept_count"], 1)

    def test_duplicate_hardware_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_hardware(_coupon([_item(), _item()]))

    def test_a_drawing_item_with_no_record_rejects_the_coupon(self):
        result = inspect_coupon_hardware(
            _coupon([_item()], drawing_hardware_ids=["TB-01", "BR-02"])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["missing_hardware_ids"], ["BR-02"])
        self.assertFalse(result["inventory_complete"])

    def test_an_undrawn_item_rejects_the_coupon(self):
        result = inspect_coupon_hardware(
            _coupon(
                [_item(), _item(hardware_id="XX-09")],
                drawing_hardware_ids=["TB-01"],
            )
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["undrawn_hardware_ids"], ["XX-09"])

    def test_a_matched_drawing_list_leaves_the_coupon_accepted(self):
        result = inspect_coupon_hardware(
            _coupon([_item()], drawing_hardware_ids=["TB-01"])
        )
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inventory_complete"])

    def test_no_drawing_list_does_not_invent_undrawn_items(self):
        result = inspect_coupon_hardware(_coupon([_item()]))
        self.assertEqual(result["undrawn_hardware_ids"], [])
        self.assertEqual(result["verdict"], ACCEPT)

    def test_an_interfering_item_is_named_apart(self):
        result = inspect_coupon_hardware(
            _coupon([_item(measured_clearance_mm=-0.5)])
        )
        self.assertEqual(result["not_tolerated_hardware_ids"], ["TB-01"])
        self.assertEqual(result["verdict"], REJECT)

    def test_a_rework_verdict_demands_reinspection(self):
        result = inspect_coupon_hardware(_coupon([_item(fasteners_installed=3)]))
        self.assertEqual(result["verdict"], REWORK)
        self.assertTrue(result["reinspection_required"])

    def test_accepted_coupon_needs_no_reinspection(self):
        self.assertFalse(
            inspect_coupon_hardware(_coupon([_item()]))["reinspection_required"]
        )

    def test_type_counts_are_reported_on_the_coupon(self):
        result = inspect_coupon_hardware(
            _coupon(
                [_item(), _item(hardware_id="CL-02", hardware_type="cable-clamp")]
            )
        )
        self.assertEqual(result["type_counts"]["cable-clamp"], 1)

    def test_coupon_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_hardware(_coupon([], coupon_id=" "))

    def test_non_list_hardware_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_hardware(_coupon("none"))

    def test_non_list_drawing_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_hardware(
                _coupon([_item()], drawing_hardware_ids="TB-01")
            )

    def test_non_mapping_coupon_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_hardware("PV-COUPON-11")


if __name__ == "__main__":
    unittest.main()
