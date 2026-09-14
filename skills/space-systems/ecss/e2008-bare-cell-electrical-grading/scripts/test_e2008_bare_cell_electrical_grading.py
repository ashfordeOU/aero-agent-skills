#!/usr/bin/env python3
"""Contract test for bare-cell electrical grading, clause 7.3.2.2.4 (offline)."""

import copy
import unittest

from e2008_bare_cell_electrical_grading_logic import (
    CELL_ABOVE_HIGHEST_BAND,
    CELL_BELOW_LOWEST_BAND,
    CELL_BOUNDARY_AMBIGUOUS,
    CELL_GRADED,
    DEFAULT_GRADING_POLICY,
    LOT_GRADING_ACCEPTED,
    LOT_GRADING_OPEN,
    assess_bare_cell_grading,
    grade_populations,
    grade_yields,
    guard_band_half_width,
    ladder_boundaries,
    place_cell,
    read_cell,
    validate_grade_bands,
    validate_grading_policy,
)


def _bands():
    return [
        {"grade": "grade-1", "min_current_a": 0.400, "max_current_a": 0.440},
        {"grade": "grade-2", "min_current_a": 0.440, "max_current_a": 0.480},
        {"grade": "grade-3", "min_current_a": 0.480, "max_current_a": 0.520},
    ]


def _tight_policy(**overrides):
    policy = copy.deepcopy(DEFAULT_GRADING_POLICY)
    policy["current_uncertainty_fraction"] = 0.0
    policy.update(overrides)
    return policy


def _cell(cell_id="cell-a", current=0.410, **overrides):
    cell = {"cell_id": cell_id, "test_current_a": current, "accepted": True}
    cell.update(overrides)
    return cell


def _case(*cells, **overrides):
    case = {
        "bands": _bands(),
        "cells": list(cells)
        or [_cell("cell-a", 0.410), _cell("cell-b", 0.455), _cell("cell-c", 0.500)],
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_grading_policy(DEFAULT_GRADING_POLICY), DEFAULT_GRADING_POLICY
        )

    def test_default_policy_holds_boundary_cells(self):
        self.assertTrue(DEFAULT_GRADING_POLICY["hold_boundary_ambiguous"])

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_grading_policy("grade everything")

    def test_negative_uncertainty_rejected(self):
        broken = copy.deepcopy(DEFAULT_GRADING_POLICY)
        broken["current_uncertainty_fraction"] = -0.01
        with self.assertRaises(ValueError):
            validate_grading_policy(broken)

    def test_non_boolean_contiguity_switch_rejected(self):
        broken = copy.deepcopy(DEFAULT_GRADING_POLICY)
        broken["require_contiguous_bands"] = "yes"
        with self.assertRaises(ValueError):
            validate_grading_policy(broken)


class LadderTests(unittest.TestCase):
    def test_ladder_is_returned_in_ascending_order(self):
        shuffled = list(reversed(_bands()))
        ladder = validate_grade_bands(shuffled)
        self.assertEqual(
            [band["grade"] for band in ladder], ["grade-1", "grade-2", "grade-3"]
        )

    def test_top_band_may_be_left_open(self):
        bands = _bands()
        bands[-1]["max_current_a"] = None
        ladder = validate_grade_bands(bands)
        self.assertIsNone(ladder[-1]["max_current_a"])

    def test_open_band_below_the_top_rejected(self):
        bands = _bands()
        bands[0]["max_current_a"] = None
        with self.assertRaises(ValueError):
            validate_grade_bands(bands)

    def test_gap_in_the_ladder_rejected(self):
        bands = _bands()
        bands[1]["min_current_a"] = 0.445
        with self.assertRaises(ValueError):
            validate_grade_bands(bands)

    def test_gap_allowed_when_policy_drops_contiguity(self):
        bands = _bands()
        bands[1]["min_current_a"] = 0.445
        policy = _tight_policy(require_contiguous_bands=False)
        ladder = validate_grade_bands(bands, policy)
        self.assertEqual(len(ladder), 3)

    def test_overlapping_bands_rejected(self):
        bands = _bands()
        bands[1]["min_current_a"] = 0.430
        policy = _tight_policy(require_contiguous_bands=False)
        with self.assertRaises(ValueError):
            validate_grade_bands(bands, policy)

    def test_repeated_grade_name_rejected(self):
        bands = _bands()
        bands[2]["grade"] = "grade-2"
        with self.assertRaises(ValueError):
            validate_grade_bands(bands)

    def test_band_closing_below_its_opening_rejected(self):
        bands = [{"grade": "grade-1", "min_current_a": 0.44, "max_current_a": 0.40}]
        with self.assertRaises(ValueError):
            validate_grade_bands(bands)

    def test_band_narrower_than_policy_allows_rejected(self):
        bands = [
            {"grade": "grade-1", "min_current_a": 0.400, "max_current_a": 0.4001},
            {"grade": "grade-2", "min_current_a": 0.4001, "max_current_a": 0.520},
        ]
        with self.assertRaises(ValueError):
            validate_grade_bands(bands)

    def test_empty_ladder_rejected(self):
        with self.assertRaises(ValueError):
            validate_grade_bands([])

    def test_non_positive_band_edge_rejected(self):
        bands = _bands()
        bands[0]["min_current_a"] = 0.0
        with self.assertRaises(ValueError):
            validate_grade_bands(bands)

    def test_interior_and_top_edges_are_reported(self):
        ladder = validate_grade_bands(_bands())
        edges = ladder_boundaries(ladder)
        self.assertEqual(len(edges), 3)
        self.assertAlmostEqual(edges[0], 0.440, places=9)
        self.assertAlmostEqual(edges[-1], 0.520, places=9)


class CellReadingTests(unittest.TestCase):
    def test_accepted_cell_reads_back(self):
        read = read_cell(_cell("cell-a", 0.41))
        self.assertEqual(read["cell_id"], "cell-a")
        self.assertAlmostEqual(read["test_current_a"], 0.41, places=9)

    def test_cell_defaults_to_accepted(self):
        read = read_cell({"cell_id": "cell-a", "test_current_a": 0.41})
        self.assertTrue(read["accepted"])

    def test_rejected_cell_is_refused(self):
        with self.assertRaises(ValueError):
            read_cell(_cell("cell-a", 0.41, accepted=False))

    def test_cell_without_identifier_rejected(self):
        with self.assertRaises(ValueError):
            read_cell({"test_current_a": 0.41})

    def test_negative_current_rejected(self):
        with self.assertRaises(ValueError):
            read_cell(_cell("cell-a", -0.41))

    def test_non_numeric_current_rejected(self):
        with self.assertRaises(ValueError):
            read_cell(_cell("cell-a", "half an amp"))

    def test_guard_band_scales_with_the_measurement(self):
        guard = guard_band_half_width(0.500, DEFAULT_GRADING_POLICY)
        self.assertAlmostEqual(guard, 0.005, places=9)


class PlacementTests(unittest.TestCase):
    def test_cell_lands_in_the_band_that_holds_it(self):
        ladder = validate_grade_bands(_bands())
        record = place_cell(_cell("cell-a", 0.455), ladder, _tight_policy())
        self.assertEqual(record["status"], CELL_GRADED)
        self.assertEqual(record["grade"], "grade-2")

    def test_cell_exactly_on_a_lower_edge_takes_the_upper_band(self):
        ladder = validate_grade_bands(_bands())
        record = place_cell(_cell("cell-a", 0.440), ladder, _tight_policy())
        self.assertEqual(record["grade"], "grade-2")

    def test_cell_on_the_ladder_floor_is_graded_not_held(self):
        ladder = validate_grade_bands(_bands())
        record = place_cell(_cell("cell-a", 0.400), ladder, _tight_policy())
        self.assertEqual(record["status"], CELL_GRADED)
        self.assertEqual(record["grade"], "grade-1")

    def test_cell_near_an_edge_is_held_as_ambiguous(self):
        ladder = validate_grade_bands(_bands())
        record = place_cell(_cell("cell-a", 0.4405), ladder, DEFAULT_GRADING_POLICY)
        self.assertEqual(record["status"], CELL_BOUNDARY_AMBIGUOUS)
        self.assertIsNone(record["grade"])
        self.assertEqual(record["boundary_candidates"], ["grade-1", "grade-2"])

    def test_ambiguous_cell_is_placed_when_policy_stops_holding(self):
        ladder = validate_grade_bands(_bands())
        policy = copy.deepcopy(DEFAULT_GRADING_POLICY)
        policy["hold_boundary_ambiguous"] = False
        record = place_cell(_cell("cell-a", 0.4405), ladder, policy)
        self.assertEqual(record["status"], CELL_GRADED)
        self.assertEqual(record["grade"], "grade-2")

    def test_cell_below_the_lowest_band_is_reported_on_its_own(self):
        ladder = validate_grade_bands(_bands())
        record = place_cell(_cell("cell-a", 0.300), ladder, _tight_policy())
        self.assertEqual(record["status"], CELL_BELOW_LOWEST_BAND)
        self.assertTrue(any("lowest grade" in f for f in record["findings"]))

    def test_cell_above_the_highest_band_is_reported_on_its_own(self):
        ladder = validate_grade_bands(_bands())
        record = place_cell(_cell("cell-a", 0.600), ladder, _tight_policy())
        self.assertEqual(record["status"], CELL_ABOVE_HIGHEST_BAND)

    def test_open_top_band_absorbs_a_high_cell(self):
        bands = _bands()
        bands[-1]["max_current_a"] = None
        ladder = validate_grade_bands(bands)
        record = place_cell(_cell("cell-a", 0.900), ladder, _tight_policy())
        self.assertEqual(record["status"], CELL_GRADED)
        self.assertEqual(record["grade"], "grade-3")

    def test_guard_band_is_reported_with_the_placement(self):
        ladder = validate_grade_bands(_bands())
        record = place_cell(_cell("cell-a", 0.500), ladder, DEFAULT_GRADING_POLICY)
        self.assertAlmostEqual(record["guard_band_a"], 0.005, places=9)


class PopulationTests(unittest.TestCase):
    def test_populations_group_by_grade(self):
        result = assess_bare_cell_grading(_case(), _tight_policy())
        self.assertEqual(result["grade_populations"]["grade-1"], ["cell-a"])
        self.assertEqual(result["grade_populations"]["grade-2"], ["cell-b"])
        self.assertEqual(result["grade_populations"]["grade-3"], ["cell-c"])

    def test_yields_sum_to_one_over_the_graded_population(self):
        result = assess_bare_cell_grading(_case(), _tight_policy())
        self.assertAlmostEqual(sum(result["grade_yields"].values()), 1.0, places=9)

    def test_yield_of_an_empty_population_is_empty(self):
        self.assertEqual(grade_yields([]), {})

    def test_held_cells_are_left_out_of_the_populations(self):
        records = [
            {"cell_id": "cell-a", "grade": "grade-1", "status": CELL_GRADED},
            {"cell_id": "cell-b", "grade": None, "status": CELL_BOUNDARY_AMBIGUOUS},
        ]
        self.assertEqual(grade_populations(records), {"grade-1": ["cell-a"]})

    def test_non_sequence_records_rejected(self):
        with self.assertRaises(ValueError):
            grade_populations("cell-a")


class LotTests(unittest.TestCase):
    def test_a_clean_lot_is_accepted(self):
        result = assess_bare_cell_grading(_case(), _tight_policy())
        self.assertEqual(result["verdict"], LOT_GRADING_ACCEPTED)
        self.assertAlmostEqual(result["graded_fraction"], 1.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_a_cell_below_the_ladder_opens_the_lot(self):
        case = _case(_cell("cell-a", 0.300), _cell("cell-b", 0.455))
        result = assess_bare_cell_grading(case, _tight_policy())
        self.assertEqual(result["verdict"], LOT_GRADING_OPEN)
        self.assertEqual(result["held_cell_ids"][CELL_BELOW_LOWEST_BAND], ["cell-a"])

    def test_too_many_held_cells_open_the_lot(self):
        case = _case(
            _cell("cell-a", 0.4405),
            _cell("cell-b", 0.4405),
            _cell("cell-c", 0.500),
        )
        result = assess_bare_cell_grading(case, DEFAULT_GRADING_POLICY)
        self.assertEqual(result["verdict"], LOT_GRADING_OPEN)
        self.assertFalse(result["graded_fraction_met"])

    def test_graded_fraction_is_the_placed_share(self):
        case = _case(
            _cell("cell-a", 0.410),
            _cell("cell-b", 0.455),
            _cell("cell-c", 0.4405),
            _cell("cell-d", 0.500),
        )
        result = assess_bare_cell_grading(case, DEFAULT_GRADING_POLICY)
        self.assertAlmostEqual(result["graded_fraction"], 0.75, places=9)

    def test_records_come_back_in_identifier_order(self):
        case = _case(_cell("cell-c", 0.500), _cell("cell-a", 0.410))
        result = assess_bare_cell_grading(case, _tight_policy())
        self.assertEqual(
            [r["cell_id"] for r in result["cell_records"]], ["cell-a", "cell-c"]
        )

    def test_repeated_cell_identifier_rejected(self):
        case = _case(_cell("cell-a", 0.410), _cell("cell-a", 0.455))
        with self.assertRaises(ValueError):
            assess_bare_cell_grading(case, _tight_policy())

    def test_empty_lot_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_grading({"bands": _bands(), "cells": []})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_grading([_cell()])

    def test_lot_carries_every_cell_finding(self):
        case = _case(_cell("cell-a", 0.300), _cell("cell-b", 0.455))
        result = assess_bare_cell_grading(case, _tight_policy())
        self.assertTrue(any("cell-a" in f for f in result["findings"]))

    def test_ladder_is_returned_with_the_verdict(self):
        result = assess_bare_cell_grading(_case(), _tight_policy())
        self.assertEqual(
            [band["grade"] for band in result["ladder"]],
            ["grade-1", "grade-2", "grade-3"],
        )


if __name__ == "__main__":
    unittest.main()
