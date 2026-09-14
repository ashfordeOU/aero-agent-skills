#!/usr/bin/env python3
"""Contract test for bare cell permanent marking (offline).

Walks the clause workflow step by step: the method-and-place pairings a
bare cell admits and the two it refuses, the survival of the mark
through the processing the cell will see, the illuminated area the mark
costs against the policy cap, the depth the coded fields and the
delivery register reach, the shortfall against the process document, the
repeated code that only the delivered set can show, and the roll-up into
one delivery verdict. This is the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_bare_cell_marking_logic import (
    DEFAULT_MARKING_POLICY,
    DEPTH_CELL,
    DEPTH_NONE,
    DEPTH_PRODUCTION_LOT,
    DEPTH_WAFER_LOT,
    MARKING_COMPLIANT,
    MARKING_INADMISSIBLE,
    MARKING_SHALLOW,
    achieved_traceability_depth,
    active_area_loss_fraction,
    assess_cell_marking,
    assess_delivery_marking,
    code_uniqueness,
    depth_shortfall,
    mark_placement_admissibility,
    mark_survives_processing,
)

SOUND_CELL = {
    "code": "BC-0001",
    "marking_method": "laser-engraved",
    "mark_location": "rear-metallisation",
    "process_exposure": "thermal-cycling",
    "mark_area_mm2": 0.4,
    "cell_active_area_mm2": 3000.0,
    "code_fields": ["production-lot-code", "cell-serial", "wafer-lot-code"],
}


def _cell(code, **overrides):
    record = copy.deepcopy(SOUND_CELL)
    record["code"] = code
    record.update(overrides)
    return record


class PlacementTests(unittest.TestCase):
    def test_engraved_rear_mark_is_admissible(self):
        result = mark_placement_admissibility(
            "laser-engraved", "rear-metallisation"
        )
        self.assertTrue(result["admissible"])
        self.assertEqual(result["findings"], [])

    def test_laser_inside_the_illuminated_area_is_refused(self):
        result = mark_placement_admissibility("laser-engraved", "front-active-area")
        self.assertFalse(result["admissible"])
        self.assertTrue(result["findings"])

    def test_adhered_label_on_the_bond_face_is_refused(self):
        result = mark_placement_admissibility("printed-label", "rear-metallisation")
        self.assertFalse(result["admissible"])

    def test_record_only_scheme_marks_nothing(self):
        result = mark_placement_admissibility("record-only", "cell-border")
        self.assertFalse(result["admissible"])

    def test_ink_in_the_illuminated_area_is_admissible_but_reported(self):
        result = mark_placement_admissibility("fired-on-ink", "front-active-area")
        self.assertTrue(result["admissible"])
        self.assertTrue(result["findings"])

    def test_unknown_marking_method_rejected(self):
        with self.assertRaises(ValueError):
            mark_placement_admissibility("chalk", "cell-border")


class PermanenceTests(unittest.TestCase):
    def test_engraved_mark_survives_the_full_campaign(self):
        result = mark_survives_processing("laser-engraved", "thermal-cycling")
        self.assertTrue(result["survives_processing"])

    def test_ink_survives_cure_and_fades_on_cycling(self):
        self.assertTrue(
            mark_survives_processing("fired-on-ink", "coverglass-bond-cure")[
                "survives_processing"
            ]
        )
        faded = mark_survives_processing("fired-on-ink", "thermal-cycling")
        self.assertFalse(faded["survives_processing"])
        self.assertTrue(faded["findings"])

    def test_label_is_lost_at_the_first_welding_step(self):
        result = mark_survives_processing("printed-label", "interconnector-welding")
        self.assertFalse(result["survives_processing"])

    def test_unknown_exposure_rejected(self):
        with self.assertRaises(ValueError):
            mark_survives_processing("laser-engraved", "launch")


class AreaLossTests(unittest.TestCase):
    def test_a_mark_outside_the_illuminated_area_costs_nothing(self):
        self.assertAlmostEqual(
            active_area_loss_fraction(25.0, 3000.0, "cell-border"), 0.0, places=12
        )

    def test_a_front_mark_costs_its_own_footprint(self):
        self.assertAlmostEqual(
            active_area_loss_fraction(6.0, 3000.0, "front-active-area"),
            0.002,
            places=12,
        )

    def test_a_mark_filling_the_illuminated_area_rejected(self):
        with self.assertRaises(ValueError):
            active_area_loss_fraction(3000.0, 3000.0, "front-active-area")

    def test_non_positive_active_area_rejected(self):
        with self.assertRaises(ValueError):
            active_area_loss_fraction(1.0, 0.0, "front-active-area")


class DepthTests(unittest.TestCase):
    def test_wafer_lot_field_reaches_the_deepest_step(self):
        self.assertEqual(
            achieved_traceability_depth(["wafer-lot-code"])["depth"], DEPTH_WAFER_LOT
        )

    def test_serial_plus_register_reaches_the_wafer_lot(self):
        reached = achieved_traceability_depth(["cell-serial"], True)
        self.assertEqual(reached["depth"], DEPTH_WAFER_LOT)

    def test_serial_alone_stops_at_the_cell(self):
        reached = achieved_traceability_depth(["cell-serial"])
        self.assertEqual(reached["depth"], DEPTH_CELL)
        self.assertTrue(reached["findings"])

    def test_lot_code_alone_cannot_tell_two_cells_apart(self):
        self.assertEqual(
            achieved_traceability_depth(["production-lot-code"])["depth"],
            DEPTH_PRODUCTION_LOT,
        )

    def test_no_coded_field_reaches_nothing(self):
        self.assertEqual(achieved_traceability_depth([])["depth"], DEPTH_NONE)

    def test_register_without_a_serial_cannot_be_entered(self):
        reached = achieved_traceability_depth(["production-lot-code"], True)
        self.assertTrue(
            any("key on" in finding for finding in reached["findings"])
        )

    def test_duplicate_coded_field_rejected(self):
        with self.assertRaises(ValueError):
            achieved_traceability_depth(["cell-serial", "cell-serial"])

    def test_shortfall_is_counted_in_steps(self):
        gap = depth_shortfall(DEPTH_WAFER_LOT, DEPTH_PRODUCTION_LOT)
        self.assertEqual(gap["steps_short"], 2)
        self.assertFalse(gap["meets_requirement"])

    def test_deeper_than_required_still_meets_the_requirement(self):
        gap = depth_shortfall(DEPTH_CELL, DEPTH_WAFER_LOT)
        self.assertEqual(gap["steps_short"], 0)
        self.assertTrue(gap["meets_requirement"])

    def test_document_requiring_no_depth_rejected(self):
        with self.assertRaises(ValueError):
            depth_shortfall(DEPTH_NONE, DEPTH_CELL)


class UniquenessTests(unittest.TestCase):
    def test_distinct_codes_are_unique(self):
        result = code_uniqueness(["BC-1", "BC-2", "BC-3"])
        self.assertEqual(result["repeated"], [])
        self.assertAlmostEqual(result["unique_share"], 1.0, places=12)

    def test_a_repeated_code_is_named(self):
        result = code_uniqueness(["BC-1", "BC-1", "BC-2"])
        self.assertEqual(result["repeated"], ["BC-1"])

    def test_empty_delivered_set_rejected(self):
        with self.assertRaises(ValueError):
            code_uniqueness([])


class CellVerdictTests(unittest.TestCase):
    def test_sound_cell_is_compliant(self):
        result = assess_cell_marking(_cell("BC-0001"))
        self.assertEqual(result["verdict"], MARKING_COMPLIANT)
        self.assertTrue(result["within_area_cap"])

    def test_shallow_scheme_is_below_the_required_depth(self):
        result = assess_cell_marking(
            _cell("BC-0002", code_fields=["production-lot-code"])
        )
        self.assertEqual(result["verdict"], MARKING_SHALLOW)
        self.assertEqual(result["shortfall"]["steps_short"], 2)

    def test_mark_lost_in_processing_is_not_established(self):
        result = assess_cell_marking(
            _cell("BC-0003", marking_method="printed-label",
                  mark_location="cell-border")
        )
        self.assertEqual(result["verdict"], MARKING_INADMISSIBLE)

    def test_mark_exactly_on_the_area_cap_is_accepted(self):
        result = assess_cell_marking(
            _cell(
                "BC-0004",
                marking_method="fired-on-ink",
                mark_location="front-active-area",
                process_exposure="coverglass-bond-cure",
                mark_area_mm2=6.0,
                cell_active_area_mm2=3000.0,
            )
        )
        self.assertTrue(result["within_area_cap"])
        self.assertAlmostEqual(
            result["active_area_loss_fraction"],
            DEFAULT_MARKING_POLICY["max_active_area_loss_fraction"],
            places=9,
        )
        self.assertEqual(result["verdict"], MARKING_COMPLIANT)

    def test_mark_over_the_area_cap_is_reported(self):
        result = assess_cell_marking(
            _cell(
                "BC-0005",
                marking_method="fired-on-ink",
                mark_location="front-active-area",
                process_exposure="coverglass-bond-cure",
                mark_area_mm2=60.0,
            )
        )
        self.assertFalse(result["within_area_cap"])
        self.assertEqual(result["verdict"], MARKING_SHALLOW)

    def test_non_mapping_cell_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_marking("the cells were all marked")


class DeliveryRollUpTests(unittest.TestCase):
    def _case(self, cells, policy=None):
        case = {"delivery_id": "LOT-77", "cells": cells}
        if policy is not None:
            case["policy"] = policy
        return case

    def test_sound_delivery_is_compliant(self):
        result = assess_delivery_marking(
            self._case([_cell("BC-1"), _cell("BC-2")])
        )
        self.assertEqual(result["verdict"], MARKING_COMPLIANT)
        self.assertTrue(result["fully_compliant"])
        self.assertAlmostEqual(result["compliant_share"], 1.0, places=12)

    def test_one_weak_cell_pulls_the_delivery_verdict_down(self):
        result = assess_delivery_marking(
            self._case(
                [_cell("BC-1"), _cell("BC-2", code_fields=["production-lot-code"])]
            )
        )
        self.assertEqual(result["verdict"], MARKING_SHALLOW)
        self.assertEqual(result["weakest_cell"], "BC-2")
        self.assertAlmostEqual(result["compliant_share"], 0.5, places=12)

    def test_a_repeated_code_fails_an_otherwise_sound_delivery(self):
        result = assess_delivery_marking(
            self._case([_cell("BC-1"), _cell("BC-1")])
        )
        self.assertEqual(result["verdict"], MARKING_INADMISSIBLE)
        self.assertFalse(result["fully_compliant"])

    def test_unmarked_cells_are_named(self):
        result = assess_delivery_marking(
            self._case(
                [_cell("BC-1"), _cell("BC-9", marking_method="record-only")]
            )
        )
        self.assertEqual(result["not_established"], ["BC-9"])

    def test_project_policy_can_relax_the_required_depth(self):
        cells = [_cell("BC-1", code_fields=["cell-serial"])]
        strict = assess_delivery_marking(self._case(cells))
        relaxed = assess_delivery_marking(
            self._case(cells, {"required_depth": DEPTH_CELL})
        )
        self.assertEqual(strict["verdict"], MARKING_SHALLOW)
        self.assertEqual(relaxed["verdict"], MARKING_COMPLIANT)

    def test_empty_delivery_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_marking(self._case([]))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_marking("every cell was engraved")


if __name__ == "__main__":
    unittest.main()
