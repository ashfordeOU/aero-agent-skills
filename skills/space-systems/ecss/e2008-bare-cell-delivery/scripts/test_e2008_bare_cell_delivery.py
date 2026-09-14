#!/usr/bin/env python3
"""Contract test for the bare-cell dispatch check, clause 7.8 (offline)."""

import unittest

from e2008_bare_cell_delivery_logic import (
    CELL_DISPOSITIONS,
    DELIVERY_HELD,
    DELIVERY_RELEASABLE,
    FILL_TOLERANCE,
    GRADE_LADDER,
    HELD,
    LINE_COMPLETE,
    LINE_PARTIAL,
    LINE_REFUSED,
    SHIPPABLE,
    SHIPPABLE_ON_CONCESSION,
    allocate_cells_to_lines,
    assess_cell,
    assess_cells,
    evaluate_delivery,
    grade_rank,
    normalize_grade,
    released_lot_ids,
    validate_order,
    validate_order_line,
)

RELEASED = ("lot-a", "lot-b")


def _cell(cell_id, grade="grade-b", lot_id="lot-a", open_ncr=False, concession=None):
    return {
        "cell_id": cell_id,
        "lot_id": lot_id,
        "grade": grade,
        "nonconformance_open": open_ncr,
        "concession": concession,
    }


def _packages(**states):
    base = {"lot-a": True, "lot-b": True}
    base.update(states)
    return [
        {"lot_id": lot, "package_released": released}
        for lot, released in sorted(base.items())
    ]


def _order(lines=None, floor=0.8, order_id="ord-2026-07"):
    return {
        "order_id": order_id,
        "partial_delivery_floor": floor,
        "lines": lines
        if lines is not None
        else [
            {"line_id": "ln-1", "grade": "grade-b", "ordered_count": 4},
        ],
    }


def _spec(**overrides):
    spec = {
        "shipment_id": "shp-0042",
        "order": _order(),
        "lot_packages": _packages(),
        "cells": [_cell("c-%03d" % n) for n in range(1, 5)],
    }
    spec.update(overrides)
    return spec


class GradeLadderTests(unittest.TestCase):
    def test_ladder_runs_lowest_grade_first(self):
        self.assertEqual(GRADE_LADDER[0], "grade-c")
        self.assertEqual(GRADE_LADDER[-1], "grade-a")

    def test_rank_orders_the_ladder(self):
        self.assertLess(grade_rank("grade-c"), grade_rank("grade-a"))

    def test_grade_is_trimmed_and_lowercased(self):
        self.assertEqual(normalize_grade("  Grade-A "), "grade-a")

    def test_unknown_grade_rejected(self):
        with self.assertRaises(ValueError):
            normalize_grade("grade-omega")

    def test_dispositions_name_the_concession_case_separately(self):
        self.assertEqual(
            set(CELL_DISPOSITIONS), {SHIPPABLE, SHIPPABLE_ON_CONCESSION, HELD}
        )


class OrderValidationTests(unittest.TestCase):
    def test_zero_ordered_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(
                {"line_id": "ln-1", "grade": "grade-b", "ordered_count": 0}
            )

    def test_boolean_ordered_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(
                {"line_id": "ln-1", "grade": "grade-b", "ordered_count": True}
            )

    def test_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(_order(floor=1.4))

    def test_floor_must_be_a_number_not_a_word(self):
        with self.assertRaises(ValueError):
            validate_order(_order(floor="most of it"))

    def test_repeated_line_id_rejected(self):
        lines = [
            {"line_id": "ln-1", "grade": "grade-b", "ordered_count": 2},
            {"line_id": "ln-1", "grade": "grade-a", "ordered_count": 2},
        ]
        with self.assertRaises(ValueError):
            validate_order(_order(lines=lines))

    def test_order_without_lines_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(_order(lines=[]))

    def test_substitution_defaults_to_refused(self):
        line = validate_order_line(
            {"line_id": "ln-1", "grade": "grade-b", "ordered_count": 2}
        )
        self.assertFalse(line["allow_upgrade_substitution"])

    def test_validating_a_validated_order_is_stable(self):
        once = validate_order(_order())
        twice = validate_order(once)
        self.assertEqual(once, twice)


class LotPackageTests(unittest.TestCase):
    def test_an_unreleased_package_is_not_a_released_lot(self):
        self.assertEqual(released_lot_ids(_packages(**{"lot-b": False})), ("lot-a",))

    def test_non_boolean_release_state_rejected(self):
        with self.assertRaises(ValueError):
            released_lot_ids([{"lot_id": "lot-a", "package_released": "yes"}])

    def test_duplicate_lot_entry_rejected(self):
        with self.assertRaises(ValueError):
            released_lot_ids(
                [
                    {"lot_id": "lot-a", "package_released": True},
                    {"lot_id": "lot-a", "package_released": False},
                ]
            )


class CellDispositionTests(unittest.TestCase):
    def test_a_clean_documented_cell_is_shippable(self):
        result = assess_cell(_cell("c-001"), RELEASED)
        self.assertEqual(result["disposition"], SHIPPABLE)
        self.assertTrue(result["documentation_released"])

    def test_a_cell_from_an_undocumented_lot_is_held(self):
        result = assess_cell(_cell("c-001", lot_id="lot-z"), RELEASED)
        self.assertEqual(result["disposition"], HELD)
        self.assertTrue(any("lot-z" in r for r in result["reasons"]))

    def test_open_nonconformance_without_a_concession_is_held(self):
        result = assess_cell(_cell("c-001", open_ncr=True), RELEASED)
        self.assertEqual(result["disposition"], HELD)

    def test_open_nonconformance_with_a_submitted_concession_is_held(self):
        cell = _cell(
            "c-001",
            open_ncr=True,
            concession={"reference": "con-9", "state": "submitted"},
        )
        self.assertEqual(assess_cell(cell, RELEASED)["disposition"], HELD)

    def test_open_nonconformance_with_an_accepted_concession_ships_named(self):
        cell = _cell(
            "c-001",
            open_ncr=True,
            concession={"reference": "con-9", "state": "accepted"},
        )
        result = assess_cell(cell, RELEASED)
        self.assertEqual(result["disposition"], SHIPPABLE_ON_CONCESSION)
        self.assertTrue(result["shippable"])

    def test_an_accepted_concession_does_not_excuse_missing_documentation(self):
        cell = _cell(
            "c-001",
            lot_id="lot-z",
            open_ncr=True,
            concession={"reference": "con-9", "state": "accepted"},
        )
        self.assertEqual(assess_cell(cell, RELEASED)["disposition"], HELD)

    def test_unknown_concession_state_rejected(self):
        cell = _cell(
            "c-001", open_ncr=True, concession={"reference": "con-9", "state": "maybe"}
        )
        with self.assertRaises(ValueError):
            assess_cell(cell, RELEASED)

    def test_non_boolean_nonconformance_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell(_cell("c-001", open_ncr="open"), RELEASED)

    def test_cell_offered_twice_rejected(self):
        with self.assertRaises(ValueError):
            assess_cells([_cell("c-001"), _cell("c-001")], RELEASED)

    def test_empty_cell_offer_rejected(self):
        with self.assertRaises(ValueError):
            assess_cells([], RELEASED)


class AllocationTests(unittest.TestCase):
    def test_exact_grade_fills_the_line(self):
        cells = assess_cells([_cell("c-%d" % n) for n in range(4)], RELEASED)
        result = allocate_cells_to_lines(cells, _order())
        line = result["lines"][0]
        self.assertEqual(line["state"], LINE_COMPLETE)
        self.assertAlmostEqual(line["fill_fraction"], 1.0, places=9)

    def test_a_lower_grade_never_fills_a_higher_line(self):
        order = _order(
            lines=[
                {
                    "line_id": "ln-1",
                    "grade": "grade-a",
                    "ordered_count": 2,
                    "allow_upgrade_substitution": True,
                }
            ],
            floor=0.0,
        )
        cells = assess_cells(
            [_cell("c-1", grade="grade-c"), _cell("c-2", grade="grade-b")], RELEASED
        )
        line = allocate_cells_to_lines(cells, order)["lines"][0]
        self.assertEqual(line["shipped_count"], 0)

    def test_a_permitted_upgrade_fills_a_lower_line_and_is_named(self):
        order = _order(
            lines=[
                {
                    "line_id": "ln-1",
                    "grade": "grade-c",
                    "ordered_count": 2,
                    "allow_upgrade_substitution": True,
                }
            ],
            floor=0.0,
        )
        cells = assess_cells(
            [_cell("c-1", grade="grade-b"), _cell("c-2", grade="grade-a")], RELEASED
        )
        line = allocate_cells_to_lines(cells, order)["lines"][0]
        self.assertEqual(line["shipped_count"], 2)
        self.assertEqual(set(line["substituted_cell_ids"]), {"c-1", "c-2"})

    def test_an_upgrade_is_refused_when_the_order_does_not_permit_it(self):
        order = _order(
            lines=[{"line_id": "ln-1", "grade": "grade-c", "ordered_count": 2}],
            floor=0.0,
        )
        cells = assess_cells(
            [_cell("c-1", grade="grade-b"), _cell("c-2", grade="grade-a")], RELEASED
        )
        line = allocate_cells_to_lines(cells, order)["lines"][0]
        self.assertEqual(line["shipped_count"], 0)
        self.assertEqual(line["short_count"], 2)

    def test_exact_grade_is_spent_before_an_upgrade_is_taken(self):
        order = _order(
            lines=[
                {
                    "line_id": "ln-low",
                    "grade": "grade-b",
                    "ordered_count": 1,
                    "allow_upgrade_substitution": True,
                },
                {"line_id": "ln-high", "grade": "grade-a", "ordered_count": 1},
            ],
            floor=0.0,
        )
        cells = assess_cells(
            [_cell("c-b", grade="grade-b"), _cell("c-a", grade="grade-a")], RELEASED
        )
        lines = allocate_cells_to_lines(cells, order)["lines"]
        self.assertEqual(lines[0]["allocated_cell_ids"], ("c-b",))
        self.assertEqual(lines[1]["allocated_cell_ids"], ("c-a",))

    def test_a_held_cell_is_never_allocated(self):
        cells = assess_cells(
            [_cell("c-1"), _cell("c-2"), _cell("c-3"), _cell("c-4", lot_id="lot-z")],
            RELEASED,
        )
        line = allocate_cells_to_lines(cells, _order())["lines"][0]
        self.assertNotIn("c-4", line["allocated_cell_ids"])
        self.assertEqual(line["shipped_count"], 3)

    def test_a_shippable_cell_no_line_wants_is_surplus(self):
        order = _order(
            lines=[{"line_id": "ln-1", "grade": "grade-b", "ordered_count": 1}],
            floor=0.0,
        )
        cells = assess_cells([_cell("c-1"), _cell("c-2")], RELEASED)
        result = allocate_cells_to_lines(cells, order)
        self.assertEqual(result["surplus_cell_ids"], ("c-2",))

    def test_a_line_exactly_on_its_floor_is_partial_not_refused(self):
        order = _order(
            lines=[{"line_id": "ln-1", "grade": "grade-b", "ordered_count": 4}],
            floor=0.75,
        )
        cells = assess_cells([_cell("c-%d" % n) for n in range(3)], RELEASED)
        line = allocate_cells_to_lines(cells, order)["lines"][0]
        self.assertAlmostEqual(line["fill_fraction"], 0.75, places=9)
        self.assertEqual(line["state"], LINE_PARTIAL)

    def test_a_line_below_its_floor_is_refused(self):
        order = _order(
            lines=[{"line_id": "ln-1", "grade": "grade-b", "ordered_count": 4}],
            floor=0.75,
        )
        cells = assess_cells([_cell("c-1"), _cell("c-2")], RELEASED)
        line = allocate_cells_to_lines(cells, order)["lines"][0]
        self.assertAlmostEqual(line["fill_fraction"], 0.5, places=9)
        self.assertEqual(line["state"], LINE_REFUSED)

    def test_fill_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(FILL_TOLERANCE, 1e-6)


class DeliveryTests(unittest.TestCase):
    def test_a_clean_shipment_is_releasable(self):
        result = evaluate_delivery(_spec())
        self.assertEqual(result["verdict"], DELIVERY_RELEASABLE)
        self.assertFalse(result["partial"])
        self.assertAlmostEqual(result["shipment_fill_fraction"], 1.0, places=9)

    def test_the_ordered_count_can_be_met_entirely_by_undocumented_cells(self):
        spec = _spec(
            cells=[_cell("c-%d" % n, lot_id="lot-z") for n in range(4)],
            lot_packages=_packages(),
        )
        result = evaluate_delivery(spec)
        self.assertEqual(len(result["held_cell_ids"]), 4)
        self.assertEqual(result["verdict"], DELIVERY_HELD)

    def test_an_unreleased_lot_package_holds_its_cells(self):
        spec = _spec(
            lot_packages=_packages(**{"lot-a": False}),
        )
        result = evaluate_delivery(spec)
        self.assertEqual(result["verdict"], DELIVERY_HELD)
        self.assertEqual(result["released_lots"], ("lot-b",))

    def test_a_concession_shipment_is_releasable_and_named(self):
        cells = [_cell("c-%d" % n) for n in range(3)]
        cells.append(
            _cell(
                "c-9",
                open_ncr=True,
                concession={"reference": "con-4", "state": "accepted"},
            )
        )
        result = evaluate_delivery(_spec(cells=cells))
        self.assertEqual(result["verdict"], DELIVERY_RELEASABLE)
        self.assertEqual(result["concession_cell_ids"], ("c-9",))

    def test_surplus_cells_are_reported_rather_than_loaded(self):
        spec = _spec(
            order=_order(
                lines=[{"line_id": "ln-1", "grade": "grade-b", "ordered_count": 2}],
                floor=0.0,
            )
        )
        result = evaluate_delivery(spec)
        self.assertEqual(len(result["surplus_cell_ids"]), 2)
        self.assertEqual(result["verdict"], DELIVERY_HELD)

    def test_a_partial_shipment_within_the_floor_is_still_flagged_partial(self):
        spec = _spec(
            order=_order(
                lines=[{"line_id": "ln-1", "grade": "grade-b", "ordered_count": 5}],
                floor=0.75,
            )
        )
        result = evaluate_delivery(spec)
        self.assertTrue(result["partial"])
        self.assertEqual(result["lines"][0]["state"], LINE_PARTIAL)
        self.assertAlmostEqual(result["shipment_fill_fraction"], 0.8, places=9)

    def test_totals_sum_across_lines(self):
        spec = _spec(
            order=_order(
                lines=[
                    {"line_id": "ln-1", "grade": "grade-b", "ordered_count": 2},
                    {"line_id": "ln-2", "grade": "grade-b", "ordered_count": 2},
                ],
                floor=0.0,
            )
        )
        result = evaluate_delivery(spec)
        self.assertEqual(result["ordered_total"], 4)
        self.assertEqual(result["shipped_total"], 4)

    def test_spec_missing_a_key_rejected(self):
        spec = _spec()
        del spec["lot_packages"]
        with self.assertRaises(ValueError):
            evaluate_delivery(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_delivery("ship it")


if __name__ == "__main__":
    unittest.main()
