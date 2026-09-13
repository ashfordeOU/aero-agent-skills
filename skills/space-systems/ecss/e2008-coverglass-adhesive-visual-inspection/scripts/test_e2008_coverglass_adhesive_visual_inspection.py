#!/usr/bin/env python3
"""Contract test for the coverglass adhesive inspection (offline)."""

import copy
import unittest

from e2008_coverglass_adhesive_visual_inspection_logic import (
    ACCEPT,
    ADHESIVE_INDICATION_KINDS,
    ADHESIVE_ZONES,
    DEFAULT_ADHESIVE_CRITERIA,
    DISCOLOURATION_GRADES,
    REJECT,
    REWORK,
    assess_adhesive_indication,
    countable_delamination_area,
    discolouration_transmission_loss,
    inspect_coverglass_adhesive,
    validate_adhesive_criteria,
)

WELD_FOOTPRINT_MM2 = 40.0
ACTIVE_AREA_MM2 = 1600.0

CLEAN_CELL = {
    "cell_id": "SCA-CELL-01",
    "bonded_area_mm2": 1700.0,
    "active_area_mm2": ACTIVE_AREA_MM2,
    "rear_weld_footprint_area_mm2": WELD_FOOTPRINT_MM2,
    "indications": [],
}


def _void(**overrides):
    indication = {
        "id": "V1",
        "kind": "delamination",
        "zone": "active-cell-area",
        "area_mm2": 10.0,
        "max_dimension_mm": 2.0,
    }
    indication.update(overrides)
    return indication


def _stain(**overrides):
    indication = {
        "id": "S1",
        "kind": "discolouration",
        "zone": "active-cell-area",
        "area_mm2": 80.0,
        "grade": "light",
    }
    indication.update(overrides)
    return indication


def _cell(indications=None, **overrides):
    cell = copy.deepcopy(CLEAN_CELL)
    cell["indications"] = copy.deepcopy(indications) if indications else []
    cell.update(overrides)
    return cell


class CriteriaTests(unittest.TestCase):
    def test_default_criteria_validate(self):
        self.assertIs(
            validate_adhesive_criteria(DEFAULT_ADHESIVE_CRITERIA),
            DEFAULT_ADHESIVE_CRITERIA,
        )

    def test_non_mapping_criteria_rejected(self):
        with self.assertRaises(ValueError):
            validate_adhesive_criteria("default")

    def test_allowance_larger_than_the_weld_footprint_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHESIVE_CRITERIA)
        broken["weld_area_allowance_fraction"] = 1.5
        with self.assertRaises(ValueError):
            validate_adhesive_criteria(broken)

    def test_reject_fraction_below_rework_fraction_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHESIVE_CRITERIA)
        broken["max_delamination_area_fraction"] = 0.005
        with self.assertRaises(ValueError):
            validate_adhesive_criteria(broken)

    def test_missing_discolouration_grade_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHESIVE_CRITERIA)
        del broken["transmission_loss_factor"]["dark"]
        with self.assertRaises(ValueError):
            validate_adhesive_criteria(broken)

    def test_loss_factor_falling_with_a_darker_grade_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHESIVE_CRITERIA)
        broken["transmission_loss_factor"]["dark"] = 0.05
        with self.assertRaises(ValueError):
            validate_adhesive_criteria(broken)

    def test_loss_factor_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHESIVE_CRITERIA)
        broken["transmission_loss_factor"]["dark"] = 1.4
        with self.assertRaises(ValueError):
            validate_adhesive_criteria(broken)

    def test_empty_optical_zone_list_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHESIVE_CRITERIA)
        broken["optical_zones"] = ()
        with self.assertRaises(ValueError):
            validate_adhesive_criteria(broken)

    def test_unknown_optical_zone_rejected(self):
        broken = copy.deepcopy(DEFAULT_ADHESIVE_CRITERIA)
        broken["optical_zones"] = ("under-the-cell",)
        with self.assertRaises(ValueError):
            validate_adhesive_criteria(broken)


class IndicationTests(unittest.TestCase):
    def test_both_kinds_are_recognised(self):
        self.assertEqual(ADHESIVE_INDICATION_KINDS, ("delamination", "discolouration"))

    def test_every_zone_is_named(self):
        self.assertIn("rear-weld-area", ADHESIVE_ZONES)

    def test_void_keeps_its_measurements(self):
        record = assess_adhesive_indication(_void())
        self.assertEqual(record["kind"], "delamination")
        self.assertAlmostEqual(record["max_dimension_mm"], 2.0, places=9)
        self.assertFalse(record["oversize_void"])

    def test_wide_void_outside_the_weld_area_is_flagged(self):
        record = assess_adhesive_indication(_void(max_dimension_mm=4.0))
        self.assertTrue(record["oversize_void"])

    def test_void_exactly_on_the_dimension_limit_is_not_flagged(self):
        record = assess_adhesive_indication(_void(max_dimension_mm=3.0))
        self.assertFalse(record["oversize_void"])

    def test_wide_void_over_the_weld_area_is_not_flagged(self):
        record = assess_adhesive_indication(
            _void(zone="rear-weld-area", max_dimension_mm=6.0)
        )
        self.assertFalse(record["oversize_void"])

    def test_stain_keeps_its_grade(self):
        record = assess_adhesive_indication(_stain(grade="moderate"))
        self.assertEqual(record["grade"], "moderate")
        self.assertIsNone(record["max_dimension_mm"])

    def test_void_without_a_dimension_rejected(self):
        indication = _void()
        del indication["max_dimension_mm"]
        with self.assertRaises(ValueError):
            assess_adhesive_indication(indication)

    def test_stain_without_a_grade_rejected(self):
        indication = _stain()
        del indication["grade"]
        with self.assertRaises(ValueError):
            assess_adhesive_indication(indication)

    def test_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            assess_adhesive_indication(_stain(grade="brownish"))

    def test_unknown_zone_rejected(self):
        with self.assertRaises(ValueError):
            assess_adhesive_indication(_void(zone="somewhere"))

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            assess_adhesive_indication(_void(kind="bubble"))

    def test_zero_area_indication_rejected(self):
        with self.assertRaises(ValueError):
            assess_adhesive_indication(_void(area_mm2=0.0))


class WeldAllowanceTests(unittest.TestCase):
    def test_weld_area_delamination_inside_the_allowance_costs_nothing(self):
        result = countable_delamination_area(
            [_void(zone="rear-weld-area", area_mm2=30.0)], WELD_FOOTPRINT_MM2
        )
        self.assertAlmostEqual(result["countable_area_mm2"], 0.0, places=9)
        self.assertAlmostEqual(result["allowance_used_mm2"], 30.0, places=9)
        self.assertAlmostEqual(result["allowance_remaining_mm2"], 10.0, places=9)

    def test_allowance_exactly_consumed_is_still_free(self):
        result = countable_delamination_area(
            [_void(zone="rear-weld-area", area_mm2=40.0)], WELD_FOOTPRINT_MM2
        )
        self.assertAlmostEqual(result["countable_area_mm2"], 0.0, places=9)
        self.assertAlmostEqual(result["allowance_remaining_mm2"], 0.0, places=9)
        self.assertTrue(any("fully used" in f for f in result["findings"]))

    def test_weld_area_delamination_beyond_the_allowance_spills(self):
        result = countable_delamination_area(
            [_void(zone="rear-weld-area", area_mm2=60.0)], WELD_FOOTPRINT_MM2
        )
        self.assertAlmostEqual(result["countable_area_mm2"], 20.0, places=9)
        self.assertTrue(any("outside the" in f for f in result["findings"]))

    def test_allowance_is_shared_across_weld_area_indications(self):
        result = countable_delamination_area(
            [
                _void(id="V1", zone="rear-weld-area", area_mm2=25.0),
                _void(id="V2", zone="rear-weld-area", area_mm2=25.0),
            ],
            WELD_FOOTPRINT_MM2,
        )
        self.assertAlmostEqual(result["countable_area_mm2"], 10.0, places=9)
        self.assertAlmostEqual(result["allowance_used_mm2"], 40.0, places=9)

    def test_delamination_elsewhere_never_draws_on_the_allowance(self):
        result = countable_delamination_area(
            [_void(zone="cell-edge-margin", area_mm2=12.0)], WELD_FOOTPRINT_MM2
        )
        self.assertAlmostEqual(result["countable_area_mm2"], 12.0, places=9)
        self.assertAlmostEqual(result["allowance_used_mm2"], 0.0, places=9)

    def test_discolouration_is_not_counted_as_delamination(self):
        result = countable_delamination_area([_stain()], WELD_FOOTPRINT_MM2)
        self.assertAlmostEqual(result["countable_area_mm2"], 0.0, places=9)

    def test_no_weld_footprint_means_no_allowance(self):
        result = countable_delamination_area(
            [_void(zone="rear-weld-area", area_mm2=10.0)], 0.0
        )
        self.assertAlmostEqual(result["countable_area_mm2"], 10.0, places=9)

    def test_negative_weld_footprint_rejected(self):
        with self.assertRaises(ValueError):
            countable_delamination_area([], -5.0)

    def test_non_list_survey_rejected(self):
        with self.assertRaises(ValueError):
            countable_delamination_area("none", WELD_FOOTPRINT_MM2)


class TransmissionLossTests(unittest.TestCase):
    def test_light_stain_costs_its_graded_share(self):
        result = discolouration_transmission_loss(
            [_stain(area_mm2=160.0, grade="light")], ACTIVE_AREA_MM2
        )
        self.assertAlmostEqual(result["transmission_loss"], 0.01, places=9)

    def test_darker_grade_costs_more_for_the_same_area(self):
        light = discolouration_transmission_loss(
            [_stain(grade="light")], ACTIVE_AREA_MM2
        )["transmission_loss"]
        dark = discolouration_transmission_loss(
            [_stain(grade="dark")], ACTIVE_AREA_MM2
        )["transmission_loss"]
        self.assertGreater(dark, light)

    def test_stain_outside_the_optical_path_costs_nothing(self):
        result = discolouration_transmission_loss(
            [_stain(zone="cell-edge-margin", area_mm2=200.0)], ACTIVE_AREA_MM2
        )
        self.assertAlmostEqual(result["transmission_loss"], 0.0, places=9)
        self.assertAlmostEqual(
            result["discoloured_outside_optical_area_mm2"], 200.0, places=9
        )

    def test_every_grade_has_a_loss_factor(self):
        for grade in DISCOLOURATION_GRADES:
            self.assertIn(grade, DEFAULT_ADHESIVE_CRITERIA["transmission_loss_factor"])

    def test_delamination_does_not_darken_the_adhesive(self):
        result = discolouration_transmission_loss([_void()], ACTIVE_AREA_MM2)
        self.assertAlmostEqual(result["transmission_loss"], 0.0, places=9)

    def test_stained_area_beyond_the_active_area_rejected(self):
        with self.assertRaises(ValueError):
            discolouration_transmission_loss(
                [_stain(area_mm2=2000.0)], ACTIVE_AREA_MM2
            )

    def test_zero_active_area_rejected(self):
        with self.assertRaises(ValueError):
            discolouration_transmission_loss([], 0.0)


class CellInspectionTests(unittest.TestCase):
    def test_clean_bond_line_is_accepted(self):
        result = inspect_coverglass_adhesive(CLEAN_CELL)
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(any("clean" in f for f in result["findings"]))

    def test_weld_area_delamination_alone_stays_accepted(self):
        result = inspect_coverglass_adhesive(
            _cell([_void(zone="rear-weld-area", area_mm2=40.0, max_dimension_mm=7.0)])
        )
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertAlmostEqual(result["countable_delamination_area_mm2"], 0.0, places=9)
        self.assertAlmostEqual(result["weld_allowance_used_mm2"], 40.0, places=9)

    def test_delamination_exactly_on_the_rework_fraction_is_accepted(self):
        result = inspect_coverglass_adhesive(_cell([_void(area_mm2=34.0)]))
        self.assertAlmostEqual(result["delamination_area_fraction"], 0.02, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_delamination_past_the_rework_fraction_reworks(self):
        result = inspect_coverglass_adhesive(_cell([_void(area_mm2=45.0)]))
        self.assertEqual(result["verdict"], REWORK)
        self.assertTrue(any("rework fraction" in f for f in result["findings"]))

    def test_delamination_past_the_limit_rejects(self):
        result = inspect_coverglass_adhesive(_cell([_void(area_mm2=120.0)]))
        self.assertEqual(result["verdict"], REJECT)

    def test_one_wide_void_rejects_on_its_own(self):
        result = inspect_coverglass_adhesive(
            _cell([_void(area_mm2=6.0, max_dimension_mm=5.0)])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertEqual(result["oversize_void_ids"], ["V1"])

    def test_a_wide_void_over_the_welds_does_not_reject(self):
        result = inspect_coverglass_adhesive(
            _cell([_void(zone="rear-weld-area", area_mm2=6.0, max_dimension_mm=5.0)])
        )
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["oversize_void_ids"], [])

    def test_spilled_weld_delamination_is_counted_against_the_bond(self):
        result = inspect_coverglass_adhesive(
            _cell([_void(zone="rear-weld-area", area_mm2=100.0, max_dimension_mm=2.0)])
        )
        self.assertAlmostEqual(
            result["countable_delamination_area_mm2"], 60.0, places=9
        )
        self.assertEqual(result["verdict"], REWORK)

    def test_discolouration_on_the_rework_limit_is_accepted(self):
        result = inspect_coverglass_adhesive(
            _cell([_stain(area_mm2=160.0, grade="light")])
        )
        self.assertAlmostEqual(result["transmission_loss"], 0.01, places=9)
        self.assertEqual(result["verdict"], ACCEPT)

    def test_discolouration_past_the_rework_limit_reworks(self):
        result = inspect_coverglass_adhesive(
            _cell([_stain(area_mm2=100.0, grade="moderate")])
        )
        self.assertEqual(result["verdict"], REWORK)

    def test_discolouration_past_the_limit_rejects(self):
        result = inspect_coverglass_adhesive(
            _cell([_stain(area_mm2=400.0, grade="light")])
        )
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(any("light to the cell" in f for f in result["findings"]))

    def test_stain_off_the_optical_path_leaves_the_cell_accepted(self):
        result = inspect_coverglass_adhesive(
            _cell([_stain(zone="cell-edge-margin", area_mm2=400.0, grade="dark")])
        )
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertAlmostEqual(result["transmission_loss"], 0.0, places=9)

    def test_both_mechanisms_take_the_worse_verdict(self):
        result = inspect_coverglass_adhesive(
            _cell(
                [
                    _void(id="V1", area_mm2=45.0),
                    _stain(id="S1", area_mm2=400.0, grade="light"),
                ]
            )
        )
        self.assertEqual(result["verdict"], REJECT)

    def test_duplicate_indication_ids_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive(
                _cell([_void(id="V1"), _void(id="V1", zone="cell-edge-margin")])
            )

    def test_active_area_larger_than_the_bonded_area_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive(_cell([], active_area_mm2=1800.0))

    def test_weld_footprint_larger_than_the_bonded_area_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive(
                _cell([], rear_weld_footprint_area_mm2=2000.0)
            )

    def test_indication_area_beyond_the_bonded_area_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive(_cell([_void(area_mm2=2000.0)]))

    def test_cell_without_an_identifier_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive(_cell([], cell_id="  "))

    def test_non_list_survey_rejected(self):
        cell = _cell()
        cell["indications"] = "none"
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive(cell)

    def test_non_mapping_cell_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coverglass_adhesive("SCA-CELL-01")


if __name__ == "__main__":
    unittest.main()
