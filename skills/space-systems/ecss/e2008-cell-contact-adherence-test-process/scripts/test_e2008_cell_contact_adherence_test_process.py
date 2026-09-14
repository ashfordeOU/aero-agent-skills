#!/usr/bin/env python3
"""Contract test for the bare-cell contact adherence run (offline).

Walks the clause procedure step by step: the footprint a cell occupies
once its edge clearance is counted, the shelf area the load needs, the
packing cap that keeps the soak reaching every cell, the ambient
pressure band, the declared dwell, the completeness rule that refuses to
sentence a lot from a partial load, the per-site grouping of front
contact, rear contact and diode attachment, the weakest-site rule that
sentences a cell, and the run verdict that has to stop a campaign whose
chamber never held the stated conditions. This is the gate 3 review
evidence for the leaf.
"""

import copy
import unittest

from e2008_cell_contact_adherence_test_process_logic import (
    ADHERENCE_CATEGORIES,
    ADHERENT,
    ATTACHMENT_SITES,
    BELOW_LIMIT,
    CONTACT_ADHERENCE_RUN_FAILED,
    CONTACT_ADHERENCE_RUN_NOT_EVALUATED,
    CONTACT_ADHERENCE_RUN_PASSED,
    DEFAULT_CELL_LOADING_POLICY,
    DETACHED,
    DIODE_ATTACHMENT,
    FRONT_CONTACT,
    REAR_CONTACT,
    RUN_VERDICTS,
    assess_chamber_loading,
    categorize_attachment,
    cell_loading_footprint_mm2,
    chamber_pressure_in_band,
    evaluate_cell,
    evaluate_cell_contact_adherence_process,
    loading_completeness,
    required_shelf_area_mm2,
    shelf_packing_fraction,
    validate_cell_loading_policy,
)

LOT_SIZE = 20

LOADING = {
    "lot_size": LOT_SIZE,
    "cells_loaded": LOT_SIZE,
    "cell_length_mm": 80.0,
    "cell_width_mm": 40.0,
    "edge_clearance_mm": 2.0,
    "usable_shelf_area_mm2": 120000.0,
    "chamber_pressure_kpa": 101.3,
    "soak_dwell_h": 48.0,
}


def _cell(identifier, front=4.0, rear=3.5, diode=3.0, carries_diode=True):
    record = {
        "id": identifier,
        "front_contact_pull_load_n": front,
        "rear_contact_pull_load_n": rear,
        "carries_bypass_diode": carries_diode,
    }
    if carries_diode:
        record["diode_attachment_pull_load_n"] = diode
    return record


def _run(cells, loading=None):
    return {
        "lot_id": "lot-11",
        "loading": copy.deepcopy(loading if loading is not None else LOADING),
        "cells": list(cells),
    }


SOUND_CELLS = [_cell("c%02d" % index) for index in range(LOT_SIZE)]
SOUND_RUN = _run(SOUND_CELLS)


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_cell_loading_policy(DEFAULT_CELL_LOADING_POLICY),
            DEFAULT_CELL_LOADING_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_loading_policy("ambient")

    def test_inverted_pressure_band_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_LOADING_POLICY)
        broken["max_chamber_pressure_kpa"] = 50.0
        with self.assertRaises(ValueError):
            validate_cell_loading_policy(broken)

    def test_packing_cap_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_LOADING_POLICY)
        broken["max_shelf_packing_fraction"] = 1.4
        with self.assertRaises(ValueError):
            validate_cell_loading_policy(broken)

    def test_detached_threshold_above_the_pull_floor_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_LOADING_POLICY)
        broken["detached_load_n"] = 5.0
        with self.assertRaises(ValueError):
            validate_cell_loading_policy(broken)

    def test_reject_allowance_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_LOADING_POLICY)
        broken["max_reject_fraction"] = 2.0
        with self.assertRaises(ValueError):
            validate_cell_loading_policy(broken)


class FootprintTests(unittest.TestCase):
    def test_clearance_is_added_on_every_side(self):
        self.assertAlmostEqual(
            cell_loading_footprint_mm2(80.0, 40.0, 2.0), 84.0 * 44.0, places=9
        )

    def test_no_clearance_gives_the_bare_cell_area(self):
        self.assertAlmostEqual(
            cell_loading_footprint_mm2(80.0, 40.0, 0.0), 3200.0, places=9
        )

    def test_zero_cell_length_rejected(self):
        with self.assertRaises(ValueError):
            cell_loading_footprint_mm2(0.0, 40.0, 2.0)

    def test_negative_clearance_rejected(self):
        with self.assertRaises(ValueError):
            cell_loading_footprint_mm2(80.0, 40.0, -1.0)

    def test_required_area_scales_with_the_load(self):
        footprint = cell_loading_footprint_mm2(80.0, 40.0, 2.0)
        self.assertAlmostEqual(
            required_shelf_area_mm2(20, footprint), 20 * footprint, places=6
        )

    def test_fractional_cell_count_rejected(self):
        with self.assertRaises(ValueError):
            required_shelf_area_mm2(20.5, 3696.0)

    def test_packing_fraction_is_required_over_usable(self):
        self.assertAlmostEqual(
            shelf_packing_fraction(73920.0, 120000.0), 0.616, places=9
        )

    def test_zero_usable_shelf_rejected(self):
        with self.assertRaises(ValueError):
            shelf_packing_fraction(73920.0, 0.0)


class PressureAndCompletenessTests(unittest.TestCase):
    def test_ambient_pressure_is_in_band(self):
        self.assertTrue(chamber_pressure_in_band(101.3))

    def test_pressure_exactly_on_the_lower_edge_is_in_band(self):
        edge = float(DEFAULT_CELL_LOADING_POLICY["min_chamber_pressure_kpa"])
        self.assertTrue(chamber_pressure_in_band(edge))

    def test_pressure_exactly_on_the_upper_edge_is_in_band(self):
        edge = float(DEFAULT_CELL_LOADING_POLICY["max_chamber_pressure_kpa"])
        self.assertTrue(chamber_pressure_in_band(edge))

    def test_partial_vacuum_is_out_of_band(self):
        self.assertFalse(chamber_pressure_in_band(10.0))

    def test_full_load_is_complete(self):
        result = loading_completeness(20, 20)
        self.assertTrue(result["complete"])
        self.assertEqual(result["cells_not_loaded"], 0)
        self.assertEqual(result["findings"], [])

    def test_partial_load_names_the_cells_left_out(self):
        result = loading_completeness(25, 20)
        self.assertFalse(result["complete"])
        self.assertEqual(result["cells_not_loaded"], 5)
        self.assertTrue(
            any("never entered the chamber" in note for note in result["findings"])
        )

    def test_loading_more_cells_than_the_lot_rejected(self):
        with self.assertRaises(ValueError):
            loading_completeness(10, 12)


class ChamberLoadingTests(unittest.TestCase):
    def test_sound_load_is_valid(self):
        result = assess_chamber_loading(LOADING)
        self.assertTrue(result["valid"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["shelf_packing_fraction"], 0.616, places=9)

    def test_packing_exactly_on_the_cap_is_accepted(self):
        loading = copy.deepcopy(LOADING)
        loading["usable_shelf_area_mm2"] = 73920.0 / 0.75
        result = assess_chamber_loading(loading)
        self.assertAlmostEqual(
            result["shelf_packing_fraction"],
            float(DEFAULT_CELL_LOADING_POLICY["max_shelf_packing_fraction"]),
            places=9,
        )
        self.assertTrue(result["packing_acceptable"])

    def test_over_packed_shelf_is_called_out(self):
        loading = copy.deepcopy(LOADING)
        loading["usable_shelf_area_mm2"] = 80000.0
        result = assess_chamber_loading(loading)
        self.assertFalse(result["packing_acceptable"])
        self.assertFalse(result["valid"])
        self.assertTrue(
            any("blocks its own circulation" in note for note in result["findings"])
        )

    def test_thin_clearance_is_called_out(self):
        loading = copy.deepcopy(LOADING)
        loading["edge_clearance_mm"] = 0.5
        result = assess_chamber_loading(loading)
        self.assertFalse(result["clearance_adequate"])
        self.assertTrue(any("shadowed" in note for note in result["findings"]))

    def test_dwell_exactly_on_the_floor_is_adequate(self):
        loading = copy.deepcopy(LOADING)
        loading["soak_dwell_h"] = float(
            DEFAULT_CELL_LOADING_POLICY["min_soak_dwell_h"]
        )
        result = assess_chamber_loading(loading)
        self.assertTrue(result["dwell_adequate"])
        self.assertTrue(result["valid"])

    def test_short_dwell_invalidates_the_load(self):
        loading = copy.deepcopy(LOADING)
        loading["soak_dwell_h"] = 2.0
        result = assess_chamber_loading(loading)
        self.assertFalse(result["dwell_adequate"])
        self.assertFalse(result["valid"])

    def test_missing_pressure_rejected(self):
        loading = copy.deepcopy(LOADING)
        del loading["chamber_pressure_kpa"]
        with self.assertRaises(ValueError):
            assess_chamber_loading(loading)


class CategoryTests(unittest.TestCase):
    def test_strong_joint_is_adherent(self):
        self.assertEqual(categorize_attachment(4.0), ADHERENT)

    def test_load_exactly_on_the_floor_is_adherent(self):
        floor = float(DEFAULT_CELL_LOADING_POLICY["min_pull_load_n"])
        self.assertEqual(categorize_attachment(floor), ADHERENT)

    def test_weak_joint_is_grouped_below_limit(self):
        self.assertEqual(categorize_attachment(1.0), BELOW_LIMIT)

    def test_joint_that_came_away_is_detached(self):
        self.assertEqual(categorize_attachment(0.05), DETACHED)

    def test_every_category_is_reachable(self):
        seen = {categorize_attachment(value) for value in (4.0, 1.0, 0.05)}
        self.assertEqual(seen, set(ADHERENCE_CATEGORIES))

    def test_negative_pull_load_rejected(self):
        with self.assertRaises(ValueError):
            categorize_attachment(-1.0)


class CellTests(unittest.TestCase):
    def test_sound_cell_is_acceptable(self):
        record = evaluate_cell(_cell("c1"))
        self.assertTrue(record["acceptable"])
        self.assertEqual(record["category"], ADHERENT)
        self.assertEqual(record["weakest_site"], DIODE_ATTACHMENT)

    def test_cell_without_a_diode_carries_two_sites(self):
        record = evaluate_cell(_cell("c2", carries_diode=False))
        self.assertEqual(set(record["site_categories"]), {FRONT_CONTACT, REAR_CONTACT})
        self.assertTrue(record["acceptable"])

    def test_missing_diode_reading_on_a_diode_cell_rejected(self):
        broken = _cell("c3")
        del broken["diode_attachment_pull_load_n"]
        with self.assertRaises(ValueError):
            evaluate_cell(broken)

    def test_weakest_site_sentences_the_cell(self):
        record = evaluate_cell(_cell("c4", front=5.0, rear=5.0, diode=1.2))
        self.assertEqual(record["category"], BELOW_LIMIT)
        self.assertEqual(record["weakest_site"], DIODE_ATTACHMENT)
        self.assertFalse(record["acceptable"])

    def test_detached_rear_contact_is_named(self):
        record = evaluate_cell(_cell("c5", rear=0.0))
        self.assertEqual(record["category"], DETACHED)
        self.assertTrue(
            any("not weak" in note for note in record["findings"])
        )

    def test_every_site_name_is_known(self):
        record = evaluate_cell(_cell("c6"))
        for site in record["site_categories"]:
            self.assertIn(site, ATTACHMENT_SITES)

    def test_non_mapping_cell_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cell("four newtons")


class RunTests(unittest.TestCase):
    def test_sound_run_passes(self):
        result = evaluate_cell_contact_adherence_process(SOUND_RUN)
        self.assertEqual(result["verdict"], CONTACT_ADHERENCE_RUN_PASSED)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["rejected_cell_ids"], [])

    def test_one_weak_cell_exactly_on_the_reject_allowance_passes(self):
        cells = copy.deepcopy(SOUND_CELLS)
        cells[3]["rear_contact_pull_load_n"] = 1.0
        result = evaluate_cell_contact_adherence_process(_run(cells))
        self.assertAlmostEqual(
            result["reject_fraction"],
            float(DEFAULT_CELL_LOADING_POLICY["max_reject_fraction"]),
            places=9,
        )
        self.assertEqual(result["verdict"], CONTACT_ADHERENCE_RUN_PASSED)
        self.assertEqual(result["rejected_cell_ids"], ["c03"])

    def test_too_many_weak_cells_fail_the_run(self):
        cells = copy.deepcopy(SOUND_CELLS)
        for index in range(4):
            cells[index]["front_contact_pull_load_n"] = 1.1
        result = evaluate_cell_contact_adherence_process(_run(cells))
        self.assertEqual(result["verdict"], CONTACT_ADHERENCE_RUN_FAILED)
        self.assertTrue(
            any("rejected share" in note for note in result["findings"])
        )

    def test_one_detached_joint_fails_the_run_on_its_own(self):
        cells = copy.deepcopy(SOUND_CELLS)
        cells[7]["diode_attachment_pull_load_n"] = 0.0
        result = evaluate_cell_contact_adherence_process(_run(cells))
        self.assertEqual(result["verdict"], CONTACT_ADHERENCE_RUN_FAILED)
        self.assertEqual(result["detached_cell_ids"], ["c07"])

    def test_partial_load_is_not_evaluated(self):
        loading = copy.deepcopy(LOADING)
        loading["lot_size"] = 25
        result = evaluate_cell_contact_adherence_process(
            _run(SOUND_CELLS, loading)
        )
        self.assertEqual(result["verdict"], CONTACT_ADHERENCE_RUN_NOT_EVALUATED)
        self.assertIsNone(result["compliant"])
        self.assertTrue(
            any("unknown state" in note for note in result["findings"])
        )

    def test_out_of_band_pressure_is_not_evaluated(self):
        loading = copy.deepcopy(LOADING)
        loading["chamber_pressure_kpa"] = 12.0
        result = evaluate_cell_contact_adherence_process(
            _run(SOUND_CELLS, loading)
        )
        self.assertEqual(result["verdict"], CONTACT_ADHERENCE_RUN_NOT_EVALUATED)

    def test_every_verdict_is_reachable(self):
        weak = copy.deepcopy(SOUND_CELLS)
        weak[0]["front_contact_pull_load_n"] = 0.0
        bad_loading = copy.deepcopy(LOADING)
        bad_loading["soak_dwell_h"] = 1.0
        seen = {
            evaluate_cell_contact_adherence_process(run)["verdict"]
            for run in (
                SOUND_RUN,
                _run(weak),
                _run(SOUND_CELLS, bad_loading),
            )
        }
        self.assertEqual(seen, set(RUN_VERDICTS))

    def test_result_count_that_disagrees_with_the_load_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cell_contact_adherence_process(_run(SOUND_CELLS[:5]))

    def test_run_without_cells_rejected(self):
        run = _run(SOUND_CELLS)
        run["cells"] = []
        with self.assertRaises(ValueError):
            evaluate_cell_contact_adherence_process(run)

    def test_non_mapping_run_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_cell_contact_adherence_process("twenty cells, all soaked")


if __name__ == "__main__":
    unittest.main()
