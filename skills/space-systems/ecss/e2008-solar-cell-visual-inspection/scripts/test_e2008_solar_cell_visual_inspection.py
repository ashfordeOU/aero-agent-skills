#!/usr/bin/env python3
"""Contract test for the solar cell defect quantity screen (offline)."""

import copy
import unittest

from e2008_solar_cell_visual_inspection_logic import (
    ACCEPT,
    CELL_DEFECT_KINDS,
    DEFAULT_CELL_DEFECT_LIMITS,
    INSPECTION_INCOMPLETE,
    REFER,
    REJECT,
    assess_cell,
    count_cell_defects,
    inspect_coupon_cells,
    validate_cell_defect_limits,
)


def _defects(kind, how_many, prefix="D"):
    return [
        {"id": "%s%d" % (prefix, n), "kind": kind} for n in range(1, how_many + 1)
    ]


def _cell(cell_id="C-001", defects=None):
    return {"cell_id": cell_id, "defects": copy.deepcopy(defects) if defects else []}


def _coupon(cells, declared=None, coupon_id="CPN-01"):
    return {
        "coupon_id": coupon_id,
        "declared_cell_count": declared if declared is not None else len(cells),
        "cells": cells,
    }


def _clean_coupon(how_many, declared=None):
    cells = [_cell("C-%03d" % n) for n in range(how_many)]
    return _coupon(cells, declared)


class LimitValidationTests(unittest.TestCase):
    def test_default_limits_validate(self):
        self.assertIs(
            validate_cell_defect_limits(DEFAULT_CELL_DEFECT_LIMITS),
            DEFAULT_CELL_DEFECT_LIMITS,
        )

    def test_non_mapping_limits_rejected(self):
        with self.assertRaises(ValueError):
            validate_cell_defect_limits("default")

    def test_missing_kind_in_per_cell_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_DEFECT_LIMITS)
        del broken["per_cell_kind_allowance"]["edge-chip"]
        with self.assertRaises(ValueError):
            validate_cell_defect_limits(broken)

    def test_fraction_above_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_DEFECT_LIMITS)
        broken["affected_cell_fraction"]["edge-chip"] = 1.4
        with self.assertRaises(ValueError):
            validate_cell_defect_limits(broken)

    def test_non_integer_per_cell_allowance_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_DEFECT_LIMITS)
        broken["per_cell_kind_allowance"]["edge-chip"] = 2.5
        with self.assertRaises(ValueError):
            validate_cell_defect_limits(broken)

    def test_contradictory_allowances_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_DEFECT_LIMITS)
        broken["affected_cell_fraction"]["cell-crack"] = 0.05
        with self.assertRaises(ValueError):
            validate_cell_defect_limits(broken)

    def test_review_margin_factor_below_one_rejected(self):
        broken = copy.deepcopy(DEFAULT_CELL_DEFECT_LIMITS)
        broken["review_margin_factor"] = 0.8
        with self.assertRaises(ValueError):
            validate_cell_defect_limits(broken)


class TallyTests(unittest.TestCase):
    def test_clean_cell_counts_zero_of_every_kind(self):
        tally = count_cell_defects(_cell())
        self.assertEqual(tally["total"], 0)
        self.assertEqual(set(tally["counts"]), set(CELL_DEFECT_KINDS))
        self.assertEqual(sum(tally["counts"].values()), 0)

    def test_tally_groups_occurrences_by_kind(self):
        cell = _cell(defects=_defects("edge-chip", 2) + _defects("handling-scratch", 1, "S"))
        tally = count_cell_defects(cell)
        self.assertEqual(tally["counts"]["edge-chip"], 2)
        self.assertEqual(tally["counts"]["handling-scratch"], 1)
        self.assertEqual(tally["total"], 3)

    def test_unknown_defect_kind_rejected(self):
        with self.assertRaises(ValueError):
            count_cell_defects(_cell(defects=[{"id": "D1", "kind": "sunburn"}]))

    def test_duplicate_defect_id_rejected(self):
        cell = _cell(defects=[{"id": "D1", "kind": "edge-chip"}] * 2)
        with self.assertRaises(ValueError):
            count_cell_defects(cell)

    def test_missing_cell_id_rejected(self):
        with self.assertRaises(ValueError):
            count_cell_defects({"defects": []})

    def test_defects_not_a_list_rejected(self):
        with self.assertRaises(ValueError):
            count_cell_defects({"cell_id": "C-001", "defects": "two chips"})


class PerCellAllowanceTests(unittest.TestCase):
    def test_cell_on_the_allowance_accepts(self):
        result = assess_cell(_cell(defects=_defects("edge-chip", 2)))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertEqual(result["kinds_over_allowance"], [])

    def test_one_past_the_allowance_refers(self):
        result = assess_cell(_cell(defects=_defects("edge-chip", 3)))
        self.assertEqual(result["verdict"], REFER)
        self.assertEqual(result["kinds_over_allowance"], ["edge-chip"])

    def test_far_past_the_allowance_rejects(self):
        result = assess_cell(_cell(defects=_defects("edge-chip", 5)))
        self.assertEqual(result["verdict"], REJECT)

    def test_zero_allowance_kind_rejects_on_one_occurrence(self):
        result = assess_cell(_cell(defects=_defects("cell-crack", 1)))
        self.assertEqual(result["verdict"], REJECT)
        self.assertTrue(
            any("not permitted at any quantity" in f for f in result["findings"])
        )

    def test_total_allowance_catches_a_cell_inside_every_kind(self):
        defects = (
            _defects("edge-chip", 2)
            + _defects("front-contact-void", 2, "V")
            + _defects("antireflective-coating-blemish", 1, "B")
        )
        result = assess_cell(_cell(defects=defects))
        self.assertEqual(result["defect_total"], 5)
        self.assertEqual(result["kinds_over_allowance"], [])
        self.assertEqual(result["verdict"], REFER)

    def test_worst_kind_drives_the_cell_verdict(self):
        defects = _defects("edge-chip", 3) + _defects("cell-crack", 1, "K")
        result = assess_cell(_cell(defects=defects))
        self.assertEqual(result["verdict"], REJECT)


class CouponRollupTests(unittest.TestCase):
    def test_clean_coupon_accepts(self):
        result = inspect_coupon_cells(_clean_coupon(20))
        self.assertEqual(result["verdict"], ACCEPT)
        self.assertTrue(result["inspection_complete"])
        self.assertEqual(result["not_accepted_ids"], [])
        self.assertAlmostEqual(result["affected_any_fraction"], 0.0, places=9)

    def test_affected_fraction_exactly_on_the_allowance_accepts(self):
        cells = [_cell("C-%03d" % n) for n in range(20)]
        for n in range(2):
            cells[n]["defects"] = _defects("edge-chip", 1)
        result = inspect_coupon_cells(_coupon(cells))
        self.assertAlmostEqual(
            result["affected_cell_fractions"]["edge-chip"], 0.10, places=9
        )
        self.assertEqual(result["kinds_over_coupon_allowance"], [])
        self.assertEqual(result["verdict"], ACCEPT)

    def test_one_cell_past_the_coupon_allowance_refers(self):
        cells = [_cell("C-%03d" % n) for n in range(20)]
        for n in range(3):
            cells[n]["defects"] = _defects("edge-chip", 1)
        result = inspect_coupon_cells(_coupon(cells))
        self.assertEqual(result["verdict"], REFER)
        self.assertEqual(result["kinds_over_coupon_allowance"], ["edge-chip"])
        self.assertAlmostEqual(
            result["affected_cell_fractions"]["edge-chip"], 0.15, places=9
        )

    def test_coupon_wide_spread_of_a_permitted_kind_rejects(self):
        cells = [_cell("C-%03d" % n) for n in range(20)]
        for n in range(8):
            cells[n]["defects"] = _defects("corner-chip", 1)
        result = inspect_coupon_cells(_coupon(cells))
        self.assertEqual(result["verdict"], REJECT)
        self.assertIn("corner-chip", result["kinds_over_coupon_allowance"])

    def test_occurrences_and_affected_cells_are_counted_apart(self):
        cells = [_cell("C-%03d" % n) for n in range(20)]
        cells[0]["defects"] = _defects("edge-chip", 2)
        cells[1]["defects"] = _defects("edge-chip", 1)
        result = inspect_coupon_cells(_coupon(cells))
        self.assertEqual(result["defect_occurrences"]["edge-chip"], 3)
        self.assertEqual(result["affected_cell_counts"]["edge-chip"], 2)

    def test_spread_across_kinds_trips_the_all_kinds_allowance(self):
        cells = [_cell("C-%03d" % n) for n in range(20)]
        for n in range(4):
            cells[n]["defects"] = _defects("antireflective-coating-blemish", 1)
        for n in (4, 5):
            cells[n]["defects"] = _defects("edge-chip", 1)
        for n in (6, 7):
            cells[n]["defects"] = _defects("handling-scratch", 1)
        result = inspect_coupon_cells(_coupon(cells))
        self.assertEqual(result["kinds_over_coupon_allowance"], [])
        self.assertEqual(result["verdict"], REFER)
        self.assertAlmostEqual(result["affected_any_fraction"], 0.40, places=9)
        self.assertTrue(any("across all kinds" in f for f in result["findings"]))

    def test_short_record_set_leaves_the_coupon_open(self):
        result = inspect_coupon_cells(_clean_coupon(18, declared=20))
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)
        self.assertFalse(result["inspection_complete"])
        self.assertEqual(result["missing_record_count"], 2)
        self.assertTrue(any("short set" in f for f in result["findings"]))

    def test_incompleteness_outranks_a_clean_screen(self):
        cells = [_cell("C-%03d" % n) for n in range(4)]
        result = inspect_coupon_cells(_coupon(cells, declared=5))
        self.assertEqual(result["verdict"], INSPECTION_INCOMPLETE)

    def test_bad_cell_names_itself_in_the_rollup(self):
        cells = [_cell("C-%03d" % n) for n in range(20)]
        cells[7]["defects"] = _defects("cell-crack", 1)
        result = inspect_coupon_cells(_coupon(cells))
        self.assertEqual(result["not_accepted_ids"], ["C-007"])
        self.assertEqual(result["disposition_counts"][REJECT], 1)
        self.assertEqual(result["disposition_counts"][ACCEPT], 19)

    def test_more_records_than_declared_rejected(self):
        cells = [_cell("C-%03d" % n) for n in range(5)]
        with self.assertRaises(ValueError):
            inspect_coupon_cells(_coupon(cells, declared=4))

    def test_duplicate_cell_ids_rejected(self):
        cells = [_cell("C-001"), _cell("C-001")]
        with self.assertRaises(ValueError):
            inspect_coupon_cells(_coupon(cells))

    def test_non_integer_declared_count_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_cells(_coupon([_cell()], declared="twenty"))

    def test_non_mapping_coupon_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_cells("CPN-01")

    def test_cells_not_a_list_rejected(self):
        with self.assertRaises(ValueError):
            inspect_coupon_cells(
                {"coupon_id": "CPN-01", "declared_cell_count": 3, "cells": "three"}
            )

    def test_project_limit_set_is_honoured(self):
        strict = copy.deepcopy(DEFAULT_CELL_DEFECT_LIMITS)
        strict["per_cell_kind_allowance"]["edge-chip"] = 1
        strict["affected_cell_fraction"]["edge-chip"] = 0.05
        cells = [_cell("C-%03d" % n) for n in range(20)]
        cells[0]["defects"] = _defects("edge-chip", 2)
        loose = inspect_coupon_cells(_coupon(copy.deepcopy(cells)))
        tight = inspect_coupon_cells(_coupon(copy.deepcopy(cells)), strict)
        self.assertEqual(loose["verdict"], ACCEPT)
        self.assertEqual(tight["verdict"], REJECT)
        self.assertEqual(tight["not_accepted_ids"], ["C-000"])


if __name__ == "__main__":
    unittest.main()
