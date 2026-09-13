#!/usr/bin/env python3
"""Contract test for the identification marking visual inspection (offline)."""

import copy
import unittest

from e2008_marking_visual_inspection_logic import (
    ACCEPT,
    DEFAULT_MARKING_CRITERIA,
    MARKING_CONDITION_KINDS,
    MARKING_SURFACES,
    MARKING_TYPES,
    NOT_TOLERATED_KINDS,
    REJECT,
    REWORK,
    assess_marking,
    assess_marking_adhesion,
    assess_marking_condition,
    assess_marking_legibility,
    assess_marking_location,
    axis_location_deviation_mm,
    character_height_margin_mm,
    edge_lift_fraction,
    group_markings_by_type,
    inspect_coupon_markings,
    lifted_area_fraction,
    reconcile_marking_inventory,
    surface_tolerance_factor,
    validate_marking_criteria,
)

SOUND_MARKING = {
    "marking_id": "MK-01",
    "marking_type": "part-number-marking",
    "surface": "substrate-rear-face",
    "drawing_face": "rear",
    "observed_face": "rear",
    "nominal_position_mm": [10.0, 20.0],
    "measured_position_mm": [10.4, 20.2],
    "marking_area_mm2": 200.0,
    "lifted_area_mm2": 2.0,
    "marking_perimeter_mm": 60.0,
    "edge_lift_length_mm": 1.0,
    "character_height_mm": 2.0,
    "conditions": [],
}

SMEAR = {
    "id": "MK-01-A",
    "kind": "ink-smear",
    "surface": "substrate-rear-face",
    "area_mm2": 1.0,
}


def _marking(**overrides):
    item = copy.deepcopy(SOUND_MARKING)
    item.update(overrides)
    return item


def _moved(dx, dy, **overrides):
    item = _marking(**overrides)
    item["measured_position_mm"] = [10.0 + dx, 20.0 + dy]
    return item


def _condition(**overrides):
    item = copy.deepcopy(SMEAR)
    item.update(overrides)
    return item


def _coupon(markings, **overrides):
    coupon = {"coupon_id": "PV-COUPON-07", "markings": markings}
    coupon.update(overrides)
    return coupon


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_marking_criteria(DEFAULT_MARKING_CRITERIA),
            DEFAULT_MARKING_CRITERIA,
        )

    def test_criteria_cover_every_surface(self):
        for surface in MARKING_SURFACES:
            self.assertIn(
                surface, DEFAULT_MARKING_CRITERIA["surface_tolerance_factor"]
            )

    def test_not_tolerated_kinds_are_real_kinds(self):
        for kind in NOT_TOLERATED_KINDS:
            self.assertIn(kind, MARKING_CONDITION_KINDS)

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_marking_criteria("default")

    def test_criteria_missing_a_graded_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARKING_CRITERIA)
        del broken["rework_area_mm2"]["ink-smear"]
        with self.assertRaises(ValueError):
            validate_marking_criteria(broken)

    def test_rework_area_below_accept_area_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARKING_CRITERIA)
        broken["rework_area_mm2"]["ink-smear"] = 0.5
        with self.assertRaises(ValueError):
            validate_marking_criteria(broken)

    def test_rework_location_below_accept_location_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARKING_CRITERIA)
        broken["rework_location_deviation_mm"] = 0.2
        with self.assertRaises(ValueError):
            validate_marking_criteria(broken)

    def test_lifted_area_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARKING_CRITERIA)
        broken["accept_lifted_area_fraction"] = 1.3
        broken["rework_lifted_area_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_marking_criteria(broken)

    def test_rework_edge_lift_below_accept_edge_lift_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARKING_CRITERIA)
        broken["rework_edge_lift_fraction"] = 0.01
        with self.assertRaises(ValueError):
            validate_marking_criteria(broken)

    def test_rework_character_height_above_the_minimum_rejected(self):
        broken = copy.deepcopy(DEFAULT_MARKING_CRITERIA)
        broken["rework_character_height_mm"] = 2.0
        with self.assertRaises(ValueError):
            validate_marking_criteria(broken)

    def test_cell_stack_face_is_stricter_than_the_rear_face(self):
        self.assertLess(
            surface_tolerance_factor("cell-stack-face"),
            surface_tolerance_factor("substrate-rear-face"),
        )

    def test_unknown_surface_rejected(self):
        with self.assertRaises(ValueError):
            surface_tolerance_factor("somewhere-on-the-coupon")


class AdhesionFractionTests(unittest.TestCase):
    def test_lifted_area_fraction_is_the_lifted_share(self):
        self.assertAlmostEqual(lifted_area_fraction(20.0, 200.0), 0.1, places=9)

    def test_a_fully_adhered_marking_has_lifted_nothing(self):
        self.assertAlmostEqual(lifted_area_fraction(0.0, 200.0), 0.0, places=9)

    def test_lifted_area_above_the_footprint_rejected(self):
        with self.assertRaises(ValueError):
            lifted_area_fraction(260.0, 200.0)

    def test_zero_footprint_rejected(self):
        with self.assertRaises(ValueError):
            lifted_area_fraction(1.0, 0.0)

    def test_edge_lift_fraction_is_the_lifted_perimeter_share(self):
        self.assertAlmostEqual(edge_lift_fraction(6.0, 60.0), 0.1, places=9)

    def test_edge_lift_longer_than_the_perimeter_rejected(self):
        with self.assertRaises(ValueError):
            edge_lift_fraction(80.0, 60.0)

    def test_zero_perimeter_rejected(self):
        with self.assertRaises(ValueError):
            edge_lift_fraction(1.0, 0.0)


class LocationGeometryTests(unittest.TestCase):
    def test_governing_deviation_is_the_larger_axis_error(self):
        deviation = axis_location_deviation_mm([0.0, 0.0], [0.3, 0.9])
        self.assertAlmostEqual(deviation["x_mm"], 0.3, places=9)
        self.assertAlmostEqual(deviation["y_mm"], 0.9, places=9)
        self.assertAlmostEqual(deviation["governing_mm"], 0.9, places=9)

    def test_deviation_is_taken_as_a_magnitude_on_each_axis(self):
        deviation = axis_location_deviation_mm([0.0, 0.0], [-1.4, 0.2])
        self.assertAlmostEqual(deviation["governing_mm"], 1.4, places=9)

    def test_a_marking_on_the_spot_has_no_deviation(self):
        deviation = axis_location_deviation_mm([5.0, 6.0], [5.0, 6.0])
        self.assertAlmostEqual(deviation["governing_mm"], 0.0, places=9)

    def test_the_box_is_not_a_root_sum_square(self):
        deviation = axis_location_deviation_mm([0.0, 0.0], [0.8, 0.6])
        self.assertAlmostEqual(deviation["governing_mm"], 0.8, places=9)

    def test_non_pair_position_rejected(self):
        with self.assertRaises(ValueError):
            axis_location_deviation_mm("origin", [0.0, 0.0])

    def test_three_coordinate_position_rejected(self):
        with self.assertRaises(ValueError):
            axis_location_deviation_mm([0.0, 0.0], [1.0, 2.0, 3.0])


class LegibilityTests(unittest.TestCase):
    def test_margin_is_the_height_over_the_minimum(self):
        self.assertAlmostEqual(character_height_margin_mm(2.0), 0.5, places=9)

    def test_a_short_character_has_a_negative_margin(self):
        self.assertLess(character_height_margin_mm(1.0), 0.0)

    def test_height_on_the_minimum_is_accepted(self):
        result = assess_marking_legibility(1.5)
        self.assertAlmostEqual(
            result["measurements"]["character_height_margin_mm"], 0.0, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_height_under_the_minimum_reworks(self):
        self.assertEqual(assess_marking_legibility(1.3)["disposition"], REWORK)

    def test_height_under_the_rework_floor_rejects(self):
        self.assertEqual(assess_marking_legibility(1.0)["disposition"], REJECT)

    def test_zero_character_height_rejected(self):
        with self.assertRaises(ValueError):
            assess_marking_legibility(0.0)


class AdhesionDispositionTests(unittest.TestCase):
    def test_a_well_adhered_marking_is_accepted(self):
        result = assess_marking_adhesion(2.0, 200.0, 1.0, 60.0)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_lifted_area_exactly_on_the_accept_fraction_is_accepted(self):
        result = assess_marking_adhesion(4.0, 200.0, 1.0, 60.0)
        self.assertAlmostEqual(
            result["measurements"]["lifted_area_fraction"], 0.02, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_lifted_area_past_the_accept_fraction_reworks(self):
        result = assess_marking_adhesion(20.0, 200.0, 1.0, 60.0)
        self.assertEqual(result["disposition"], REWORK)

    def test_lifted_area_past_the_rework_fraction_rejects(self):
        result = assess_marking_adhesion(40.0, 200.0, 1.0, 60.0)
        self.assertEqual(result["disposition"], REJECT)

    def test_edge_lift_exactly_on_the_accept_fraction_is_accepted(self):
        result = assess_marking_adhesion(2.0, 200.0, 3.0, 60.0)
        self.assertAlmostEqual(
            result["measurements"]["edge_lift_fraction"], 0.05, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_a_peeled_edge_reworks_a_well_seated_footprint(self):
        result = assess_marking_adhesion(2.0, 200.0, 6.0, 60.0)
        self.assertEqual(result["disposition"], REWORK)
        self.assertAlmostEqual(
            result["measurements"]["lifted_area_fraction"], 0.01, places=9
        )

    def test_edge_lift_past_the_rework_fraction_rejects(self):
        result = assess_marking_adhesion(2.0, 200.0, 18.0, 60.0)
        self.assertEqual(result["disposition"], REJECT)

    def test_adhesion_takes_the_worse_of_the_two_figures(self):
        result = assess_marking_adhesion(40.0, 200.0, 18.0, 60.0)
        self.assertEqual(result["disposition"], REJECT)
        self.assertEqual(len(result["reasons"]), 2)


class LocationDispositionTests(unittest.TestCase):
    def test_a_marking_inside_its_box_is_accepted(self):
        result = assess_marking_location(
            [0.0, 0.0], [0.4, 0.2], "substrate-rear-face"
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_deviation_exactly_on_the_accept_box_is_accepted(self):
        result = assess_marking_location(
            [0.0, 0.0], [1.0, 0.2], "substrate-rear-face"
        )
        self.assertAlmostEqual(
            result["measurements"]["accept_location_deviation_mm"], 1.0, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_the_same_deviation_on_the_cell_stack_face_loses_its_margin(self):
        result = assess_marking_location(
            [0.0, 0.0], [1.0, 0.2], "cell-stack-face"
        )
        self.assertAlmostEqual(
            result["measurements"]["accept_location_deviation_mm"], 0.5, places=9
        )
        self.assertEqual(result["disposition"], REWORK)

    def test_deviation_past_the_rework_box_rejects(self):
        result = assess_marking_location(
            [0.0, 0.0], [5.0, 0.2], "substrate-rear-face"
        )
        self.assertEqual(result["disposition"], REJECT)


class InventoryTests(unittest.TestCase):
    def test_a_matched_inventory_is_complete(self):
        result = reconcile_marking_inventory(["MK-01", "MK-02"], ["MK-02", "MK-01"])
        self.assertTrue(result["complete"])
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["unlisted"], [])

    def test_a_drawing_marking_not_on_the_part_is_missing(self):
        result = reconcile_marking_inventory(["MK-01", "MK-02"], ["MK-01"])
        self.assertEqual(result["missing"], ["MK-02"])
        self.assertFalse(result["complete"])

    def test_a_marking_the_drawing_never_called_is_unlisted(self):
        result = reconcile_marking_inventory(["MK-01"], ["MK-01", "MK-09"])
        self.assertEqual(result["unlisted"], ["MK-09"])

    def test_a_repeated_identifier_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_marking_inventory(["MK-01", "MK-01"], ["MK-01"])

    def test_a_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_marking_inventory(["MK-01", "  "], ["MK-01"])

    def test_a_bare_string_inventory_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_marking_inventory("MK-01", ["MK-01"])


class ConditionTests(unittest.TestCase):
    def test_a_small_smear_is_accepted(self):
        result = assess_marking_condition(SMEAR)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertTrue(result["tolerated"])

    def test_smear_area_exactly_on_the_accept_limit_is_accepted(self):
        result = assess_marking_condition(_condition(area_mm2=2.0))
        self.assertAlmostEqual(
            result["measurements"]["accept_area_mm2"], 2.0, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_the_same_smear_on_the_cell_stack_face_loses_its_margin(self):
        result = assess_marking_condition(
            _condition(area_mm2=2.0, surface="cell-stack-face")
        )
        self.assertAlmostEqual(
            result["measurements"]["accept_area_mm2"], 1.0, places=9
        )
        self.assertEqual(result["disposition"], REWORK)

    def test_area_past_the_rework_limit_rejects(self):
        result = assess_marking_condition(_condition(area_mm2=20.0))
        self.assertEqual(result["disposition"], REJECT)

    def test_a_missing_marking_rejects_on_presence(self):
        result = assess_marking_condition(_condition(kind="missing-marking"))
        self.assertEqual(result["disposition"], REJECT)
        self.assertFalse(result["tolerated"])

    def test_an_unbonded_marking_rejects_on_presence(self):
        result = assess_marking_condition(_condition(kind="unbonded-marking"))
        self.assertTrue(
            any("no allowance" in reason for reason in result["reasons"])
        )

    def test_a_not_tolerated_kind_ignores_the_surface_factor(self):
        strict = assess_marking_condition(
            _condition(kind="wrong-face-marking", surface="cell-stack-face")
        )
        loose = assess_marking_condition(
            _condition(kind="wrong-face-marking", surface="substrate-rear-face")
        )
        self.assertEqual(strict["disposition"], loose["disposition"])

    def test_unknown_condition_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_marking_condition(_condition(kind="smudge"))

    def test_a_measured_leg_logged_as_a_condition_rejected(self):
        with self.assertRaises(ValueError):
            assess_marking_condition(_condition(kind="edge-lift"))

    def test_non_mapping_condition_rejected(self):
        with self.assertRaises(ValueError):
            assess_marking_condition("ink-smear")

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            assess_marking_condition(_condition(area_mm2=-1.0))


class GroupingTests(unittest.TestCase):
    def test_markings_group_by_type(self):
        result = group_markings_by_type(
            [
                _marking(),
                _marking(marking_type="serial-number-marking"),
                _marking(marking_type="serial-number-marking"),
            ]
        )
        self.assertEqual(result["counts"]["part-number-marking"], 1)
        self.assertEqual(result["counts"]["serial-number-marking"], 2)
        self.assertEqual(result["recorded"], 3)

    def test_every_type_appears_in_the_grouping(self):
        result = group_markings_by_type([])
        for marking_type in MARKING_TYPES:
            self.assertIn(marking_type, result["counts"])

    def test_grouping_an_unknown_type_rejected(self):
        with self.assertRaises(ValueError):
            group_markings_by_type([_marking(marking_type="scribble")])

    def test_grouping_a_bare_string_rejected(self):
        with self.assertRaises(ValueError):
            group_markings_by_type("MK-01")


class MarkingTests(unittest.TestCase):
    def test_a_sound_marking_is_accepted(self):
        result = assess_marking(SOUND_MARKING)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertTrue(result["well_adhered"])
        self.assertTrue(result["as_drawn"])
        self.assertTrue(result["legible"])

    def test_marking_disposition_takes_the_worst_leg(self):
        result = assess_marking(_moved(5.0, 0.2))
        self.assertEqual(result["disposition"], REJECT)
        self.assertEqual(result["adhesion_disposition"], ACCEPT)
        self.assertFalse(result["as_drawn"])

    def test_a_wrong_face_rejects_whatever_the_in_plane_deviation(self):
        result = assess_marking(_marking(observed_face="front"))
        self.assertEqual(result["disposition"], REJECT)
        self.assertFalse(result["face_correct"])
        self.assertEqual(result["location_disposition"], ACCEPT)
        self.assertTrue(
            any("wrong face" in reason for reason in result["reasons"])
        )

    def test_a_peeled_edge_is_reported_even_with_a_good_position(self):
        result = assess_marking(_marking(edge_lift_length_mm=6.0))
        self.assertEqual(result["disposition"], REWORK)
        self.assertFalse(result["well_adhered"])
        self.assertTrue(result["as_drawn"])

    def test_an_unreadable_marking_rejects(self):
        result = assess_marking(_marking(character_height_mm=1.0))
        self.assertEqual(result["disposition"], REJECT)
        self.assertFalse(result["legible"])

    def test_a_not_tolerated_condition_names_itself_on_the_marking(self):
        result = assess_marking(
            _marking(conditions=[_condition(kind="unbonded-marking")])
        )
        self.assertEqual(result["not_tolerated_ids"], ["MK-01-A"])

    def test_conditions_default_to_an_empty_survey(self):
        record = _marking()
        del record["conditions"]
        self.assertEqual(assess_marking(record)["conditions"], [])

    def test_marking_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_marking(_marking(marking_id="  "))

    def test_marking_without_a_drawing_face_rejected(self):
        with self.assertRaises(ValueError):
            assess_marking(_marking(drawing_face=""))

    def test_non_list_conditions_rejected(self):
        with self.assertRaises(ValueError):
            assess_marking(_marking(conditions="none"))

    def test_non_mapping_marking_rejected(self):
        with self.assertRaises(ValueError):
            assess_marking("MK-01")


class CouponTests(unittest.TestCase):
    def test_a_coupon_with_no_records_still_produces_a_finding(self):
        result = inspect_coupon_markings(_coupon([]))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(
            any("no marking records" in item for item in result["findings"])
        )

    def test_coupon_verdict_takes_the_worst_marking(self):
        result = inspect_coupon_markings(
            _coupon([_marking(), _moved(5.0, 0.2, marking_id="MK-02")])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["reject_count"], 1)
        self.assertEqual(result["accept_count"], 1)

    def test_duplicate_marking_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_markings(_coupon([_marking(), _marking()]))

    def test_a_drawing_marking_with_no_record_rejects_the_coupon(self):
        result = inspect_coupon_markings(
            _coupon([_marking()], drawing_marking_ids=["MK-01", "MK-02"])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["missing_marking_ids"], ["MK-02"])
        self.assertFalse(result["inventory_complete"])

    def test_an_unlisted_marking_rejects_the_coupon(self):
        result = inspect_coupon_markings(
            _coupon(
                [_marking(), _marking(marking_id="MK-09")],
                drawing_marking_ids=["MK-01"],
            )
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["unlisted_marking_ids"], ["MK-09"])

    def test_a_matched_drawing_list_leaves_the_coupon_accepted(self):
        result = inspect_coupon_markings(
            _coupon([_marking()], drawing_marking_ids=["MK-01"])
        )
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inventory_complete"])

    def test_no_drawing_list_does_not_invent_unlisted_markings(self):
        result = inspect_coupon_markings(_coupon([_marking()]))
        self.assertEqual(result["unlisted_marking_ids"], [])
        self.assertEqual(result["verdict"], ACCEPT)

    def test_a_rework_verdict_demands_reinspection(self):
        result = inspect_coupon_markings(
            _coupon([_marking(edge_lift_length_mm=6.0)])
        )
        self.assertEqual(result["verdict"], REWORK)
        self.assertTrue(result["reinspection_required"])

    def test_accepted_coupon_needs_no_reinspection(self):
        self.assertFalse(
            inspect_coupon_markings(_coupon([_marking()]))["reinspection_required"]
        )

    def test_not_tolerated_conditions_name_their_marking(self):
        result = inspect_coupon_markings(
            _coupon([_marking(conditions=[_condition(kind="unbonded-marking")])])
        )
        self.assertEqual(result["not_tolerated_marking_ids"], ["MK-01"])

    def test_type_counts_are_reported_on_the_coupon(self):
        result = inspect_coupon_markings(
            _coupon(
                [
                    _marking(),
                    _marking(
                        marking_id="MK-02", marking_type="polarity-marking"
                    ),
                ]
            )
        )
        self.assertEqual(result["type_counts"]["polarity-marking"], 1)

    def test_coupon_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_markings(_coupon([], coupon_id=" "))

    def test_non_list_markings_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_markings(_coupon("none"))

    def test_non_list_drawing_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_markings(
                _coupon([_marking()], drawing_marking_ids="MK-01")
            )

    def test_non_mapping_coupon_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_markings("PV-COUPON-07")


if __name__ == "__main__":
    unittest.main()
