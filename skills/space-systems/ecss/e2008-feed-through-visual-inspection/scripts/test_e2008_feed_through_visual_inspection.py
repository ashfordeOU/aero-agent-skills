#!/usr/bin/env python3
"""Contract test for the panel feed-through visual inspection (offline)."""

import copy
import unittest

from e2008_feed_through_visual_inspection_logic import (
    ACCEPT,
    DEFAULT_FEED_THROUGH_CRITERIA,
    FEED_THROUGH_CONDITION_KINDS,
    FEED_THROUGH_ZONES,
    NOT_TOLERATED_KINDS,
    REJECT,
    REWORK,
    assess_bond_state,
    assess_feed_through,
    assess_feed_through_condition,
    assess_position_offset,
    bond_coverage_fraction,
    debond_perimeter_fraction,
    group_conditions_by_kind,
    inspect_panel_feed_throughs,
    is_firmly_bonded,
    radial_position_offset_mm,
    validate_feed_through_criteria,
    zone_tolerance_factor,
)

SOUND_FEED_THROUGH = {
    "feed_through_id": "FT-01",
    "zone": "panel-rear-face",
    "nominal_position_mm": [120.0, 45.0],
    "measured_position_mm": [120.2, 45.1],
    "bonded_area_mm2": 48.0,
    "required_bond_area_mm2": 50.0,
    "debonded_perimeter_mm": 0.5,
    "bond_perimeter_mm": 25.0,
    "conditions": [],
}

VOID = {
    "id": "FT-01-A",
    "kind": "bond-fillet-void",
    "zone": "panel-rear-face",
    "area_mm2": 0.4,
}


def _record(**overrides):
    item = copy.deepcopy(SOUND_FEED_THROUGH)
    item.update(overrides)
    return item


def _shifted(dx, dy, **overrides):
    item = _record(**overrides)
    item["measured_position_mm"] = [120.0 + dx, 45.0 + dy]
    return item


def _condition(**overrides):
    item = copy.deepcopy(VOID)
    item.update(overrides)
    return item


def _panel(records, **overrides):
    panel = {"panel_id": "SA-PANEL-02", "feed_throughs": records}
    panel.update(overrides)
    return panel


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_feed_through_criteria(DEFAULT_FEED_THROUGH_CRITERIA),
            DEFAULT_FEED_THROUGH_CRITERIA,
        )

    def test_criteria_cover_every_zone(self):
        for zone in FEED_THROUGH_ZONES:
            self.assertIn(
                zone, DEFAULT_FEED_THROUGH_CRITERIA["zone_tolerance_factor"]
            )

    def test_not_tolerated_kinds_are_real_kinds(self):
        for kind in NOT_TOLERATED_KINDS:
            self.assertIn(kind, FEED_THROUGH_CONDITION_KINDS)

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_feed_through_criteria("default")

    def test_criteria_missing_a_graded_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_FEED_THROUGH_CRITERIA)
        del broken["accept_area_mm2"]["bond-fillet-void"]
        with self.assertRaises(ValueError):
            validate_feed_through_criteria(broken)

    def test_rework_area_below_accept_area_rejected(self):
        broken = copy.deepcopy(DEFAULT_FEED_THROUGH_CRITERIA)
        broken["rework_area_mm2"]["bond-fillet-void"] = 0.1
        with self.assertRaises(ValueError):
            validate_feed_through_criteria(broken)

    def test_rework_offset_below_accept_offset_rejected(self):
        broken = copy.deepcopy(DEFAULT_FEED_THROUGH_CRITERIA)
        broken["rework_offset_mm"] = 0.2
        with self.assertRaises(ValueError):
            validate_feed_through_criteria(broken)

    def test_coverage_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_FEED_THROUGH_CRITERIA)
        broken["accept_bond_coverage_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_feed_through_criteria(broken)

    def test_rework_coverage_above_accept_coverage_rejected(self):
        broken = copy.deepcopy(DEFAULT_FEED_THROUGH_CRITERIA)
        broken["rework_bond_coverage_fraction"] = 0.95
        with self.assertRaises(ValueError):
            validate_feed_through_criteria(broken)

    def test_rework_debond_below_accept_debond_rejected(self):
        broken = copy.deepcopy(DEFAULT_FEED_THROUGH_CRITERIA)
        broken["rework_debond_perimeter_fraction"] = 0.01
        with self.assertRaises(ValueError):
            validate_feed_through_criteria(broken)

    def test_core_interface_is_stricter_than_the_rear_face(self):
        self.assertLess(
            zone_tolerance_factor("substrate-core-interface"),
            zone_tolerance_factor("panel-rear-face"),
        )

    def test_unknown_zone_rejected(self):
        with self.assertRaises(ValueError):
            zone_tolerance_factor("somewhere-on-the-panel")


class OffsetTests(unittest.TestCase):
    def test_offset_is_the_root_sum_square_of_the_axis_errors(self):
        self.assertAlmostEqual(
            radial_position_offset_mm([0.0, 0.0], [0.3, 0.4]), 0.5, places=9
        )

    def test_coincident_centres_give_a_zero_offset(self):
        self.assertAlmostEqual(
            radial_position_offset_mm([12.0, -3.0], [12.0, -3.0]), 0.0, places=9
        )

    def test_a_diagonal_miss_is_larger_than_either_axis_error(self):
        offset = radial_position_offset_mm([0.0, 0.0], [0.6, 0.8])
        self.assertGreater(offset, 0.8)

    def test_non_pair_position_rejected(self):
        with self.assertRaises(ValueError):
            radial_position_offset_mm("origin", [0.0, 0.0])

    def test_three_coordinate_position_rejected(self):
        with self.assertRaises(ValueError):
            radial_position_offset_mm([0.0, 0.0], [1.0, 2.0, 3.0])

    def test_non_numeric_coordinate_rejected(self):
        with self.assertRaises(ValueError):
            radial_position_offset_mm([0.0, 0.0], [1.0, None])


class BondFractionTests(unittest.TestCase):
    def test_coverage_is_the_bonded_share(self):
        self.assertAlmostEqual(bond_coverage_fraction(40.0, 50.0), 0.8, places=9)

    def test_full_coverage_is_one(self):
        self.assertAlmostEqual(bond_coverage_fraction(50.0, 50.0), 1.0, places=9)

    def test_bonded_area_above_the_requirement_rejected(self):
        with self.assertRaises(ValueError):
            bond_coverage_fraction(70.0, 50.0)

    def test_zero_required_footprint_rejected(self):
        with self.assertRaises(ValueError):
            bond_coverage_fraction(10.0, 0.0)

    def test_debond_fraction_is_the_released_share(self):
        self.assertAlmostEqual(
            debond_perimeter_fraction(5.0, 25.0), 0.2, places=9
        )

    def test_an_intact_bond_line_has_released_nothing(self):
        self.assertAlmostEqual(
            debond_perimeter_fraction(0.0, 25.0), 0.0, places=9
        )

    def test_debond_longer_than_the_perimeter_rejected(self):
        with self.assertRaises(ValueError):
            debond_perimeter_fraction(30.0, 25.0)

    def test_zero_perimeter_rejected(self):
        with self.assertRaises(ValueError):
            debond_perimeter_fraction(1.0, 0.0)

    def test_firmly_bonded_is_true_for_a_sound_bond(self):
        self.assertTrue(is_firmly_bonded(48.0, 50.0, 0.5, 25.0))

    def test_firmly_bonded_is_false_when_coverage_is_short(self):
        self.assertFalse(is_firmly_bonded(40.0, 50.0, 0.5, 25.0))

    def test_firmly_bonded_is_false_when_the_bond_line_has_released(self):
        self.assertFalse(is_firmly_bonded(48.0, 50.0, 8.0, 25.0))


class PositionDispositionTests(unittest.TestCase):
    def test_offset_inside_tolerance_is_accepted(self):
        result = assess_position_offset(0.2, "panel-rear-face")
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_offset_exactly_on_the_accept_tolerance_is_accepted(self):
        offset = radial_position_offset_mm([0.0, 0.0], [0.3, 0.4])
        result = assess_position_offset(offset, "panel-rear-face")
        self.assertAlmostEqual(
            result["measurements"]["accept_offset_mm"], 0.5, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_the_same_offset_at_the_core_interface_loses_its_margin(self):
        offset = radial_position_offset_mm([0.0, 0.0], [0.3, 0.4])
        result = assess_position_offset(offset, "substrate-core-interface")
        self.assertAlmostEqual(
            result["measurements"]["accept_offset_mm"], 0.25, places=9
        )
        self.assertEqual(result["disposition"], REWORK)

    def test_offset_past_the_rework_tolerance_rejects(self):
        result = assess_position_offset(3.0, "panel-rear-face")
        self.assertEqual(result["disposition"], REJECT)

    def test_negative_offset_rejected(self):
        with self.assertRaises(ValueError):
            assess_position_offset(-0.1, "panel-rear-face")


class BondDispositionTests(unittest.TestCase):
    def test_sound_bond_is_accepted(self):
        result = assess_bond_state(48.0, 50.0, 0.5, 25.0)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_coverage_exactly_on_the_minimum_is_accepted(self):
        result = assess_bond_state(45.0, 50.0, 0.5, 25.0)
        self.assertAlmostEqual(
            result["measurements"]["bond_coverage_fraction"], 0.90, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_coverage_under_the_minimum_reworks(self):
        result = assess_bond_state(40.0, 50.0, 0.5, 25.0)
        self.assertEqual(result["disposition"], REWORK)

    def test_coverage_under_the_rework_floor_rejects(self):
        result = assess_bond_state(30.0, 50.0, 0.5, 25.0)
        self.assertEqual(result["disposition"], REJECT)

    def test_debond_exactly_on_the_accept_fraction_is_accepted(self):
        result = assess_bond_state(48.0, 50.0, 1.25, 25.0)
        self.assertAlmostEqual(
            result["measurements"]["debond_perimeter_fraction"], 0.05, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_debond_past_the_accept_fraction_reworks(self):
        result = assess_bond_state(48.0, 50.0, 5.0, 25.0)
        self.assertEqual(result["disposition"], REWORK)

    def test_debond_past_the_rework_fraction_rejects(self):
        result = assess_bond_state(48.0, 50.0, 10.0, 25.0)
        self.assertEqual(result["disposition"], REJECT)

    def test_bond_takes_the_worse_of_the_two_legs(self):
        result = assess_bond_state(40.0, 50.0, 10.0, 25.0)
        self.assertEqual(result["disposition"], REJECT)
        self.assertEqual(len(result["reasons"]), 2)


class ConditionTests(unittest.TestCase):
    def test_small_fillet_void_is_accepted(self):
        result = assess_feed_through_condition(VOID)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertTrue(result["tolerated"])

    def test_void_area_exactly_on_the_accept_limit_is_accepted(self):
        result = assess_feed_through_condition(_condition(area_mm2=1.0))
        self.assertAlmostEqual(
            result["measurements"]["accept_area_mm2"], 1.0, places=9
        )
        self.assertEqual(result["disposition"], ACCEPT)

    def test_void_on_the_core_interface_loses_its_margin(self):
        result = assess_feed_through_condition(
            _condition(area_mm2=1.0, zone="substrate-core-interface")
        )
        self.assertAlmostEqual(
            result["measurements"]["accept_area_mm2"], 0.5, places=9
        )
        self.assertEqual(result["disposition"], REWORK)

    def test_area_past_the_rework_limit_rejects(self):
        result = assess_feed_through_condition(_condition(area_mm2=9.0))
        self.assertEqual(result["disposition"], REJECT)

    def test_a_loose_feed_through_rejects_on_presence(self):
        result = assess_feed_through_condition(
            _condition(kind="unbonded-feed-through")
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertFalse(result["tolerated"])

    def test_a_substrate_crack_rejects_on_presence(self):
        result = assess_feed_through_condition(
            _condition(kind="substrate-crack-at-feed-through")
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(
            any("no allowance" in reason for reason in result["reasons"])
        )

    def test_a_not_tolerated_kind_ignores_the_zone_factor(self):
        strict = assess_feed_through_condition(
            _condition(
                kind="wrong-position-feed-through",
                zone="substrate-core-interface",
            )
        )
        loose = assess_feed_through_condition(
            _condition(kind="wrong-position-feed-through", zone="panel-rear-face")
        )
        self.assertEqual(strict["disposition"], loose["disposition"])

    def test_unknown_condition_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_feed_through_condition(_condition(kind="smudge"))

    def test_a_measured_leg_logged_as_a_condition_rejected(self):
        with self.assertRaises(ValueError):
            assess_feed_through_condition(_condition(kind="position-deviation"))

    def test_non_mapping_condition_rejected(self):
        with self.assertRaises(ValueError):
            assess_feed_through_condition("bond-fillet-void")

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            assess_feed_through_condition(_condition(area_mm2=-1.0))


class GroupingTests(unittest.TestCase):
    def test_conditions_group_by_kind(self):
        result = group_conditions_by_kind(
            [_condition(), _condition(), _condition(kind="adhesive-contamination")]
        )
        self.assertEqual(result["counts"]["bond-fillet-void"], 2)
        self.assertEqual(result["counts"]["adhesive-contamination"], 1)
        self.assertEqual(result["not_tolerated_count"], 0)

    def test_not_tolerated_conditions_counted_apart(self):
        result = group_conditions_by_kind(
            [_condition(), _condition(kind="unbonded-feed-through")]
        )
        self.assertEqual(result["not_tolerated_count"], 1)

    def test_grouping_an_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            group_conditions_by_kind([_condition(kind="smudge")])

    def test_grouping_a_non_list_rejected(self):
        with self.assertRaises(ValueError):
            group_conditions_by_kind("none")


class FeedThroughTests(unittest.TestCase):
    def test_a_sound_feed_through_is_accepted(self):
        result = assess_feed_through(SOUND_FEED_THROUGH)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertTrue(result["firmly_bonded"])
        self.assertTrue(result["in_position"])

    def test_item_disposition_takes_the_worst_leg(self):
        result = assess_feed_through(_shifted(3.0, 0.0))
        self.assertEqual(result["disposition"], REJECT)
        self.assertEqual(result["bond_disposition"], ACCEPT)
        self.assertFalse(result["in_position"])

    def test_a_short_bond_is_reported_even_when_the_position_is_good(self):
        result = assess_feed_through(_record(bonded_area_mm2=40.0))
        self.assertEqual(result["disposition"], REWORK)
        self.assertFalse(result["firmly_bonded"])
        self.assertTrue(result["in_position"])

    def test_a_not_tolerated_condition_names_itself_on_the_item(self):
        result = assess_feed_through(
            _record(conditions=[_condition(kind="unbonded-feed-through")])
        )
        self.assertEqual(result["disposition"], REJECT)
        self.assertEqual(result["not_tolerated_ids"], ["FT-01-A"])

    def test_conditions_default_to_an_empty_survey(self):
        record = _record()
        del record["conditions"]
        self.assertEqual(assess_feed_through(record)["conditions"], [])

    def test_feed_through_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_feed_through(_record(feed_through_id="  "))

    def test_non_list_conditions_rejected(self):
        with self.assertRaises(ValueError):
            assess_feed_through(_record(conditions="none"))

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            assess_feed_through("FT-01")


class PanelTests(unittest.TestCase):
    def test_a_panel_with_no_records_still_produces_a_finding(self):
        result = inspect_panel_feed_throughs(_panel([]))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(
            any("no feed-through records" in item for item in result["findings"])
        )

    def test_panel_verdict_takes_the_worst_feed_through(self):
        result = inspect_panel_feed_throughs(
            _panel([_record(), _shifted(3.0, 0.0, feed_through_id="FT-02")])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["reject_count"], 1)
        self.assertEqual(result["accept_count"], 1)

    def test_duplicate_feed_through_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_panel_feed_throughs(_panel([_record(), _record()]))

    def test_a_drawing_feed_through_with_no_record_rejects_the_panel(self):
        result = inspect_panel_feed_throughs(
            _panel([_record()], drawing_feed_through_ids=["FT-01", "FT-02"])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["unrecorded_ids"], ["FT-02"])

    def test_an_undrawn_feed_through_rejects_the_panel(self):
        result = inspect_panel_feed_throughs(
            _panel(
                [_record(), _record(feed_through_id="FT-09")],
                drawing_feed_through_ids=["FT-01"],
            )
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["undrawn_ids"], ["FT-09"])

    def test_a_matched_drawing_list_leaves_the_panel_accepted(self):
        result = inspect_panel_feed_throughs(
            _panel([_record()], drawing_feed_through_ids=["FT-01"])
        )
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["unrecorded_ids"], [])
        self.assertEqual(result["undrawn_ids"], [])

    def test_a_rework_verdict_demands_reinspection(self):
        result = inspect_panel_feed_throughs(
            _panel([_record(bonded_area_mm2=40.0)])
        )
        self.assertEqual(result["verdict"], REWORK)
        self.assertTrue(result["reinspection_required"])

    def test_accepted_panel_needs_no_reinspection(self):
        result = inspect_panel_feed_throughs(_panel([_record()]))
        self.assertFalse(result["reinspection_required"])

    def test_not_tolerated_conditions_name_their_feed_through(self):
        result = inspect_panel_feed_throughs(
            _panel(
                [_record(conditions=[_condition(kind="unbonded-feed-through")])]
            )
        )
        self.assertEqual(result["not_tolerated_feed_through_ids"], ["FT-01"])
        self.assertEqual(result["condition_counts"]["unbonded-feed-through"], 1)

    def test_panel_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            inspect_panel_feed_throughs(_panel([], panel_id=" "))

    def test_non_list_feed_throughs_rejected(self):
        with self.assertRaises(ValueError):
            inspect_panel_feed_throughs(_panel("none"))

    def test_non_list_drawing_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_panel_feed_throughs(
                _panel([_record()], drawing_feed_through_ids="FT-01")
            )

    def test_non_mapping_panel_rejected(self):
        with self.assertRaises(ValueError):
            inspect_panel_feed_throughs("SA-PANEL-02")


if __name__ == "__main__":
    unittest.main()
