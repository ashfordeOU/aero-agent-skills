#!/usr/bin/env python3
"""Contract test for the substrate visual inspection (offline)."""

import copy
import unittest

from e2008_substrate_visual_inspection_logic import (
    ACCEPT,
    DEFAULT_SUBSTRATE_CRITERIA,
    REJECT,
    REPAIR,
    SOURCE_OPERATIONS,
    SUBSTRATE_INDICATION_KINDS,
    SUBSTRATE_ZONES,
    assess_indication,
    attribute_damage_operations,
    damaged_area_fraction,
    depth_fraction,
    inspect_substrate,
    validate_substrate_criteria,
    zone_severity_factor,
)

THICKNESS_MM = 1.0

CLEAN_PANEL = {
    "substrate_id": "SA-PANEL-01",
    "panel_area_mm2": 10000.0,
    "facesheet_thickness_mm": THICKNESS_MM,
    "indications": [],
}

SCRATCH = {
    "id": "IND-1",
    "kind": "facesheet-scratch",
    "zone": "free-facesheet-area",
    "operation": "handling",
    "depth_mm": 0.05,
    "area_mm2": 30.0,
}


def _indication(**overrides):
    item = copy.deepcopy(SCRATCH)
    item.update(overrides)
    return item


def _panel(indications, **overrides):
    panel = copy.deepcopy(CLEAN_PANEL)
    panel["indications"] = indications
    panel.update(overrides)
    return panel


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_substrate_criteria(DEFAULT_SUBSTRATE_CRITERIA),
            DEFAULT_SUBSTRATE_CRITERIA,
        )

    def test_criteria_cover_every_indication_kind(self):
        for kind in SUBSTRATE_INDICATION_KINDS:
            self.assertIn(kind, DEFAULT_SUBSTRATE_CRITERIA["accept_area_mm2"])
            self.assertIn(kind, DEFAULT_SUBSTRATE_CRITERIA["repair_depth_fraction"])

    def test_criteria_cover_every_zone(self):
        for zone in SUBSTRATE_ZONES:
            self.assertIn(zone, DEFAULT_SUBSTRATE_CRITERIA["zone_severity_factor"])

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_substrate_criteria("default")

    def test_criteria_missing_a_kind_rejected(self):
        broken = copy.deepcopy(DEFAULT_SUBSTRATE_CRITERIA)
        del broken["accept_area_mm2"]["facesheet-dent"]
        with self.assertRaises(ValueError):
            validate_substrate_criteria(broken)

    def test_repair_limit_below_accept_limit_rejected(self):
        broken = copy.deepcopy(DEFAULT_SUBSTRATE_CRITERIA)
        broken["repair_area_mm2"]["facesheet-scratch"] = 10.0
        with self.assertRaises(ValueError):
            validate_substrate_criteria(broken)

    def test_zero_zone_severity_factor_rejected(self):
        broken = copy.deepcopy(DEFAULT_SUBSTRATE_CRITERIA)
        broken["zone_severity_factor"]["free-facesheet-area"] = 0.0
        with self.assertRaises(ValueError):
            validate_substrate_criteria(broken)

    def test_panel_reject_fraction_below_repair_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_SUBSTRATE_CRITERIA)
        broken["panel_reject_area_fraction"] = 0.001
        with self.assertRaises(ValueError):
            validate_substrate_criteria(broken)


class DepthTests(unittest.TestCase):
    def test_depth_fraction_is_depth_over_thickness(self):
        self.assertAlmostEqual(depth_fraction(0.15, 0.6), 0.25, places=9)

    def test_through_damage_gives_a_fraction_above_one(self):
        self.assertGreater(depth_fraction(1.2, 0.6), 1.0)

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            depth_fraction(0.1, 0.0)

    def test_negative_depth_rejected(self):
        with self.assertRaises(ValueError):
            depth_fraction(-0.1, 0.6)

    def test_cell_footprint_is_stricter_than_open_facesheet(self):
        self.assertLess(
            zone_severity_factor("cell-bonding-footprint"),
            zone_severity_factor("free-facesheet-area"),
        )

    def test_unknown_zone_rejected(self):
        with self.assertRaises(ValueError):
            zone_severity_factor("somewhere-on-the-panel")


class IndicationTests(unittest.TestCase):
    def test_shallow_small_scratch_is_accepted(self):
        result = assess_indication(SCRATCH, THICKNESS_MM)
        self.assertEqual(result["disposition"], ACCEPT)
        self.assertEqual(result["reasons"], [])

    def test_depth_exactly_on_the_accept_limit_is_accepted(self):
        result = assess_indication(_indication(depth_mm=0.10), THICKNESS_MM)
        self.assertAlmostEqual(result["depth_fraction"], 0.10, places=9)
        self.assertAlmostEqual(result["accept_depth_fraction"], 0.10, places=9)
        self.assertEqual(result["disposition"], ACCEPT)

    def test_same_scratch_under_the_cells_loses_its_margin(self):
        result = assess_indication(
            _indication(depth_mm=0.10, zone="cell-bonding-footprint"), THICKNESS_MM
        )
        self.assertAlmostEqual(result["accept_depth_fraction"], 0.05, places=9)
        self.assertEqual(result["disposition"], REPAIR)

    def test_area_beyond_the_accept_limit_calls_a_repair(self):
        result = assess_indication(_indication(area_mm2=120.0), THICKNESS_MM)
        self.assertEqual(result["disposition"], REPAIR)
        self.assertTrue(any("area" in reason for reason in result["reasons"]))

    def test_area_beyond_the_repair_limit_rejects(self):
        result = assess_indication(_indication(area_mm2=900.0), THICKNESS_MM)
        self.assertEqual(result["disposition"], REJECT)

    def test_area_exactly_on_the_repair_limit_stays_repairable(self):
        result = assess_indication(_indication(area_mm2=400.0), THICKNESS_MM)
        self.assertAlmostEqual(result["repair_area_mm2"], 400.0, places=9)
        self.assertEqual(result["disposition"], REPAIR)

    def test_worst_of_depth_and_area_governs(self):
        result = assess_indication(
            _indication(depth_mm=0.6, area_mm2=10.0), THICKNESS_MM
        )
        self.assertEqual(result["disposition"], REJECT)

    def test_puncture_under_the_cells_rejects_even_when_small(self):
        result = assess_indication(
            _indication(
                kind="facesheet-puncture",
                zone="cell-bonding-footprint",
                depth_mm=1.4,
                area_mm2=4.0,
            ),
            THICKNESS_MM,
        )
        self.assertTrue(result["through_facesheet"])
        self.assertEqual(result["disposition"], REJECT)
        self.assertTrue(
            any("dielectric" in reason for reason in result["reasons"])
        )

    def test_same_puncture_on_open_facesheet_is_repairable(self):
        result = assess_indication(
            _indication(
                kind="facesheet-puncture",
                zone="free-facesheet-area",
                depth_mm=1.4,
                area_mm2=4.0,
            ),
            THICKNESS_MM,
        )
        self.assertEqual(result["disposition"], REPAIR)

    def test_core_crush_is_never_accepted_as_found(self):
        result = assess_indication(
            _indication(
                kind="honeycomb-core-crush",
                zone="free-facesheet-area",
                depth_mm=1.5,
                area_mm2=200.0,
            ),
            THICKNESS_MM,
        )
        self.assertEqual(result["disposition"], REPAIR)

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_indication(_indication(kind="scuff"), THICKNESS_MM)

    def test_unattributed_indication_rejected(self):
        with self.assertRaises(ValueError):
            assess_indication(_indication(operation="unknown"), THICKNESS_MM)

    def test_indication_with_no_measurement_rejected(self):
        with self.assertRaises(ValueError):
            assess_indication(
                _indication(depth_mm=0.0, area_mm2=0.0), THICKNESS_MM
            )

    def test_negative_area_rejected(self):
        with self.assertRaises(ValueError):
            assess_indication(_indication(area_mm2=-5.0), THICKNESS_MM)

    def test_non_mapping_indication_rejected(self):
        with self.assertRaises(ValueError):
            assess_indication("facesheet-scratch", THICKNESS_MM)


class AttributionTests(unittest.TestCase):
    def test_counts_group_by_operation(self):
        result = attribute_damage_operations(
            [
                _indication(operation="handling"),
                _indication(operation="handling"),
                _indication(operation="test"),
            ]
        )
        self.assertEqual(result["counts"]["handling"], 2)
        self.assertEqual(result["counts"]["test"], 1)
        self.assertEqual(result["counts"]["assembly"], 0)
        self.assertEqual(result["dominant_operation"], "handling")

    def test_a_tie_names_no_dominant_operation(self):
        result = attribute_damage_operations(
            [_indication(operation="handling"), _indication(operation="test")]
        )
        self.assertIsNone(result["dominant_operation"])

    def test_empty_survey_names_no_dominant_operation(self):
        result = attribute_damage_operations([])
        self.assertIsNone(result["dominant_operation"])
        for operation in SOURCE_OPERATIONS:
            self.assertEqual(result["counts"][operation], 0)

    def test_unknown_operation_rejected(self):
        with self.assertRaises(ValueError):
            attribute_damage_operations([_indication(operation="shipping")])


class AreaFractionTests(unittest.TestCase):
    def test_fraction_is_damaged_area_over_panel_area(self):
        self.assertAlmostEqual(
            damaged_area_fraction(
                [_indication(area_mm2=40.0), _indication(area_mm2=60.0)], 10000.0
            ),
            0.01,
            places=9,
        )

    def test_clean_panel_has_zero_damaged_fraction(self):
        self.assertAlmostEqual(damaged_area_fraction([], 10000.0), 0.0, places=9)

    def test_damage_beyond_the_panel_area_rejected(self):
        with self.assertRaises(ValueError):
            damaged_area_fraction([_indication(area_mm2=20000.0)], 10000.0)

    def test_zero_panel_area_rejected(self):
        with self.assertRaises(ValueError):
            damaged_area_fraction([], 0.0)


class PanelInspectionTests(unittest.TestCase):
    def test_clean_panel_is_accepted_with_a_record(self):
        result = inspect_substrate(CLEAN_PANEL)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["reject_count"], 0)
        self.assertTrue(any("clean" in finding for finding in result["findings"]))

    def test_panel_verdict_takes_the_worst_indication(self):
        result = inspect_substrate(
            _panel([_indication(id="A"), _indication(id="B", area_mm2=900.0)])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["reject_count"], 1)
        self.assertEqual(result["accept_count"], 1)

    def test_a_repair_verdict_demands_reinspection(self):
        result = inspect_substrate(_panel([_indication(id="A", area_mm2=120.0)]))
        self.assertEqual(result["verdict"], REPAIR)
        self.assertTrue(result["reinspection_required"])

    def test_accepted_panel_needs_no_reinspection(self):
        self.assertFalse(inspect_substrate(CLEAN_PANEL)["reinspection_required"])

    def test_damaged_fraction_exactly_on_the_repair_limit_does_not_escalate(self):
        indications = [
            _indication(id="A%d" % n, area_mm2=40.0) for n in range(5)
        ]
        result = inspect_substrate(_panel(indications))
        self.assertAlmostEqual(result["damaged_area_fraction"], 0.02, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_many_small_accepted_indications_still_escalate_the_panel(self):
        indications = [
            _indication(id="A%d" % n, area_mm2=45.0) for n in range(5)
        ]
        result = inspect_substrate(_panel(indications))
        self.assertEqual(result["accept_count"], 5)
        self.assertEqual(result["verdict"], REPAIR)
        self.assertTrue(
            any("repair fraction" in finding for finding in result["findings"])
        )

    def test_corrective_action_points_at_the_dominant_operation(self):
        result = inspect_substrate(
            _panel(
                [
                    _indication(id="A", operation="test"),
                    _indication(id="B", operation="test"),
                    _indication(id="C", operation="assembly"),
                ]
            )
        )
        self.assertEqual(result["corrective_action_focus"], "test")
        self.assertTrue(
            any("corrective action" in finding for finding in result["findings"])
        )

    def test_duplicate_indication_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_substrate(_panel([_indication(id="A"), _indication(id="A")]))

    def test_panel_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            inspect_substrate(_panel([], substrate_id="  "))

    def test_panel_with_a_non_list_survey_rejected(self):
        panel = copy.deepcopy(CLEAN_PANEL)
        panel["indications"] = "none"
        with self.assertRaises(ValueError):
            inspect_substrate(panel)

    def test_panel_without_a_facesheet_thickness_rejected(self):
        panel = copy.deepcopy(CLEAN_PANEL)
        del panel["facesheet_thickness_mm"]
        with self.assertRaises(ValueError):
            inspect_substrate(panel)

    def test_non_mapping_panel_rejected(self):
        with self.assertRaises(ValueError):
            inspect_substrate("SA-PANEL-01")


if __name__ == "__main__":
    unittest.main()
