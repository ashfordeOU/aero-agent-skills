#!/usr/bin/env python3
"""Contract test for the protection diode dispatch check, clause 9.9 (offline)."""

import unittest

from e2008_protection_diode_delivery_logic import (
    DIODE_DISPOSITIONS,
    DIODE_FUNCTIONS,
    DISPATCH_HELD,
    DISPATCH_RELEASABLE,
    FILL_TOLERANCE,
    HELD,
    LINE_COMPLETE,
    LINE_PARTIAL,
    LINE_REFUSED,
    RATING_LADDER,
    REQUIRED_LOT_DOCUMENTS,
    SHIPPABLE,
    SHIPPABLE_ON_CONCESSION,
    allocate_diodes_to_lines,
    assess_diode,
    assess_diodes,
    assess_lot_documents,
    evaluate_delivery,
    lot_document_index,
    normalize_function,
    normalize_rating,
    rating_rank,
    validate_order,
    validate_order_line,
)


def _documents(**states):
    base = dict((doc, "released") for doc in REQUIRED_LOT_DOCUMENTS)
    base.update(states)
    return [
        {"document_id": doc, "state": state}
        for doc, state in sorted(base.items())
        if state is not None
    ]


def _lots(**overrides):
    lots = [
        {"lot_id": "lot-a", "documents": _documents()},
        {"lot_id": "lot-b", "documents": _documents()},
    ]
    for lot in lots:
        if lot["lot_id"] in overrides:
            lot["documents"] = overrides[lot["lot_id"]]
    return lots


def _index(**overrides):
    return lot_document_index(_lots(**overrides))


def _diode(
    diode_id,
    function="bypass",
    rating="rating-band-medium",
    lot_id="lot-a",
    open_ncr=False,
    concession=None,
):
    return {
        "diode_id": diode_id,
        "lot_id": lot_id,
        "function": function,
        "rating_band": rating,
        "nonconformance_open": open_ncr,
        "concession": concession,
    }


def _order(lines=None, floor=0.8, order_id="ord-2026-11"):
    return {
        "order_id": order_id,
        "partial_delivery_floor": floor,
        "lines": lines
        if lines is not None
        else [
            {
                "line_id": "ln-1",
                "function": "bypass",
                "rating_band": "rating-band-medium",
                "ordered_count": 4,
            }
        ],
    }


def _spec(**overrides):
    spec = {
        "shipment_id": "shp-0119",
        "order": _order(),
        "lots": _lots(),
        "diodes": [_diode("d-%03d" % n) for n in range(1, 5)],
    }
    spec.update(overrides)
    return spec


class LadderAndFunctionTests(unittest.TestCase):
    def test_rating_ladder_runs_lowest_band_first(self):
        self.assertEqual(RATING_LADDER[0], "rating-band-low")
        self.assertEqual(RATING_LADDER[-1], "rating-band-high")

    def test_rank_orders_the_rating_ladder(self):
        self.assertLess(rating_rank("rating-band-low"), rating_rank("rating-band-high"))

    def test_rating_band_is_trimmed_and_lowercased(self):
        self.assertEqual(normalize_rating("  Rating-Band-High "), "rating-band-high")

    def test_unknown_rating_band_rejected(self):
        with self.assertRaises(ValueError):
            normalize_rating("rating-band-omega")

    def test_function_is_categorical_with_exactly_two_members(self):
        self.assertEqual(set(DIODE_FUNCTIONS), {"bypass", "blocking"})

    def test_unknown_function_rejected(self):
        with self.assertRaises(ValueError):
            normalize_function("clamping")

    def test_dispositions_name_the_concession_case_separately(self):
        self.assertEqual(
            set(DIODE_DISPOSITIONS), {SHIPPABLE, SHIPPABLE_ON_CONCESSION, HELD}
        )


class OrderValidationTests(unittest.TestCase):
    def test_zero_ordered_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(
                {
                    "line_id": "ln-1",
                    "function": "bypass",
                    "rating_band": "rating-band-low",
                    "ordered_count": 0,
                }
            )

    def test_boolean_ordered_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(
                {
                    "line_id": "ln-1",
                    "function": "bypass",
                    "rating_band": "rating-band-low",
                    "ordered_count": True,
                }
            )

    def test_line_without_a_function_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(
                {
                    "line_id": "ln-1",
                    "rating_band": "rating-band-low",
                    "ordered_count": 2,
                }
            )

    def test_floor_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(_order(floor=1.4))

    def test_floor_must_be_a_number_not_a_word(self):
        with self.assertRaises(ValueError):
            validate_order(_order(floor="most of them"))

    def test_repeated_line_id_rejected(self):
        lines = [
            {
                "line_id": "ln-1",
                "function": "bypass",
                "rating_band": "rating-band-low",
                "ordered_count": 2,
            },
            {
                "line_id": "ln-1",
                "function": "blocking",
                "rating_band": "rating-band-high",
                "ordered_count": 2,
            },
        ]
        with self.assertRaises(ValueError):
            validate_order(_order(lines=lines))

    def test_order_without_lines_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(_order(lines=[]))

    def test_rating_upgrade_defaults_to_refused(self):
        line = validate_order_line(
            {
                "line_id": "ln-1",
                "function": "bypass",
                "rating_band": "rating-band-low",
                "ordered_count": 2,
            }
        )
        self.assertFalse(line["allow_rating_upgrade"])

    def test_validating_a_validated_order_is_stable(self):
        once = validate_order(_order())
        twice = validate_order(once)
        self.assertEqual(once, twice)


class LotDocumentSetTests(unittest.TestCase):
    def test_a_full_released_set_is_complete(self):
        lot = assess_lot_documents({"lot_id": "lot-a", "documents": _documents()})
        self.assertTrue(lot["document_set_complete"])
        self.assertEqual(lot["missing_documents"], ())

    def test_a_draft_document_is_not_a_released_document(self):
        lot = assess_lot_documents(
            {"lot_id": "lot-a", "documents": _documents(**{"screening-test-data": "draft"})}
        )
        self.assertFalse(lot["document_set_complete"])
        self.assertEqual(lot["unreleased_documents"], ("screening-test-data",))
        self.assertEqual(lot["absent_documents"], ())

    def test_a_withdrawn_document_is_not_a_released_document(self):
        lot = assess_lot_documents(
            {
                "lot_id": "lot-a",
                "documents": _documents(
                    **{"declaration-of-conformance": "withdrawn"}
                ),
            }
        )
        self.assertFalse(lot["document_set_complete"])

    def test_an_absent_document_is_reported_separately_from_an_unreleased_one(self):
        lot = assess_lot_documents(
            {"lot_id": "lot-a", "documents": _documents(**{"lot-data-package": None})}
        )
        self.assertEqual(lot["absent_documents"], ("lot-data-package",))
        self.assertEqual(lot["unreleased_documents"], ())

    def test_two_of_three_released_still_holds_the_lot(self):
        lot = assess_lot_documents(
            {"lot_id": "lot-a", "documents": _documents(**{"screening-test-data": None})}
        )
        self.assertEqual(len(lot["released_documents"]), 2)
        self.assertFalse(lot["document_set_complete"])

    def test_unknown_document_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_documents(
                {
                    "lot_id": "lot-a",
                    "documents": [{"document_id": "packing-note", "state": "released"}],
                }
            )

    def test_unknown_document_state_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_documents(
                {
                    "lot_id": "lot-a",
                    "documents": [
                        {"document_id": "lot-data-package", "state": "nearly"}
                    ],
                }
            )

    def test_repeated_document_entry_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_documents(
                {
                    "lot_id": "lot-a",
                    "documents": [
                        {"document_id": "lot-data-package", "state": "released"},
                        {"document_id": "lot-data-package", "state": "draft"},
                    ],
                }
            )

    def test_duplicate_lot_entry_rejected(self):
        with self.assertRaises(ValueError):
            lot_document_index(
                [
                    {"lot_id": "lot-a", "documents": _documents()},
                    {"lot_id": "lot-a", "documents": _documents()},
                ]
            )


class DiodeDispositionTests(unittest.TestCase):
    def test_a_clean_documented_diode_is_shippable(self):
        result = assess_diode(_diode("d-001"), _index())
        self.assertEqual(result["disposition"], SHIPPABLE)
        self.assertTrue(result["documentation_complete"])

    def test_a_diode_from_a_lot_short_one_document_is_held(self):
        index = _index(**{"lot-a": _documents(**{"screening-test-data": "draft"})})
        result = assess_diode(_diode("d-001"), index)
        self.assertEqual(result["disposition"], HELD)
        self.assertEqual(result["missing_documents"], ("screening-test-data",))

    def test_a_diode_naming_an_unregistered_lot_is_held(self):
        result = assess_diode(_diode("d-001", lot_id="lot-z"), _index())
        self.assertEqual(result["disposition"], HELD)
        self.assertTrue(any("lot-z" in r for r in result["reasons"]))

    def test_open_nonconformance_without_a_concession_is_held(self):
        result = assess_diode(_diode("d-001", open_ncr=True), _index())
        self.assertEqual(result["disposition"], HELD)

    def test_open_nonconformance_with_a_submitted_concession_is_held(self):
        diode = _diode(
            "d-001",
            open_ncr=True,
            concession={"reference": "con-3", "state": "submitted"},
        )
        self.assertEqual(assess_diode(diode, _index())["disposition"], HELD)

    def test_open_nonconformance_with_an_accepted_concession_ships_named(self):
        diode = _diode(
            "d-001",
            open_ncr=True,
            concession={"reference": "con-3", "state": "accepted"},
        )
        result = assess_diode(diode, _index())
        self.assertEqual(result["disposition"], SHIPPABLE_ON_CONCESSION)
        self.assertTrue(result["shippable"])

    def test_an_accepted_concession_does_not_complete_a_document_set(self):
        index = _index(**{"lot-a": _documents(**{"lot-data-package": "draft"})})
        diode = _diode(
            "d-001",
            open_ncr=True,
            concession={"reference": "con-3", "state": "accepted"},
        )
        self.assertEqual(assess_diode(diode, index)["disposition"], HELD)

    def test_unknown_concession_state_rejected(self):
        diode = _diode(
            "d-001", open_ncr=True, concession={"reference": "con-3", "state": "maybe"}
        )
        with self.assertRaises(ValueError):
            assess_diode(diode, _index())

    def test_non_boolean_nonconformance_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode(_diode("d-001", open_ncr="open"), _index())

    def test_diode_offered_twice_rejected(self):
        with self.assertRaises(ValueError):
            assess_diodes([_diode("d-001"), _diode("d-001")], _index())

    def test_empty_diode_offer_rejected(self):
        with self.assertRaises(ValueError):
            assess_diodes([], _index())


class AllocationTests(unittest.TestCase):
    def test_exact_band_and_function_fill_the_line(self):
        diodes = assess_diodes([_diode("d-%d" % n) for n in range(4)], _index())
        line = allocate_diodes_to_lines(diodes, _order())["lines"][0]
        self.assertEqual(line["state"], LINE_COMPLETE)
        self.assertAlmostEqual(line["fill_fraction"], 1.0, places=9)

    def test_a_blocking_diode_never_fills_a_bypass_line(self):
        order = _order(
            lines=[
                {
                    "line_id": "ln-1",
                    "function": "bypass",
                    "rating_band": "rating-band-medium",
                    "ordered_count": 2,
                    "allow_rating_upgrade": True,
                }
            ],
            floor=0.0,
        )
        diodes = assess_diodes(
            [
                _diode("d-1", function="blocking"),
                _diode("d-2", function="blocking", rating="rating-band-high"),
            ],
            _index(),
        )
        line = allocate_diodes_to_lines(diodes, order)["lines"][0]
        self.assertEqual(line["shipped_count"], 0)
        self.assertEqual(line["short_count"], 2)

    def test_a_lower_rating_band_never_fills_a_higher_line(self):
        order = _order(
            lines=[
                {
                    "line_id": "ln-1",
                    "function": "bypass",
                    "rating_band": "rating-band-high",
                    "ordered_count": 2,
                    "allow_rating_upgrade": True,
                }
            ],
            floor=0.0,
        )
        diodes = assess_diodes(
            [
                _diode("d-1", rating="rating-band-low"),
                _diode("d-2", rating="rating-band-medium"),
            ],
            _index(),
        )
        line = allocate_diodes_to_lines(diodes, order)["lines"][0]
        self.assertEqual(line["shipped_count"], 0)

    def test_a_permitted_upgrade_fills_a_lower_line_and_is_named(self):
        order = _order(
            lines=[
                {
                    "line_id": "ln-1",
                    "function": "bypass",
                    "rating_band": "rating-band-low",
                    "ordered_count": 2,
                    "allow_rating_upgrade": True,
                }
            ],
            floor=0.0,
        )
        diodes = assess_diodes(
            [
                _diode("d-1", rating="rating-band-medium"),
                _diode("d-2", rating="rating-band-high"),
            ],
            _index(),
        )
        line = allocate_diodes_to_lines(diodes, order)["lines"][0]
        self.assertEqual(line["shipped_count"], 2)
        self.assertEqual(set(line["substituted_diode_ids"]), {"d-1", "d-2"})

    def test_an_upgrade_is_refused_when_the_order_does_not_permit_it(self):
        order = _order(
            lines=[
                {
                    "line_id": "ln-1",
                    "function": "bypass",
                    "rating_band": "rating-band-low",
                    "ordered_count": 2,
                }
            ],
            floor=0.0,
        )
        diodes = assess_diodes(
            [
                _diode("d-1", rating="rating-band-medium"),
                _diode("d-2", rating="rating-band-high"),
            ],
            _index(),
        )
        line = allocate_diodes_to_lines(diodes, order)["lines"][0]
        self.assertEqual(line["shipped_count"], 0)

    def test_exact_band_is_spent_before_an_upgrade_is_taken(self):
        order = _order(
            lines=[
                {
                    "line_id": "ln-low",
                    "function": "bypass",
                    "rating_band": "rating-band-medium",
                    "ordered_count": 1,
                    "allow_rating_upgrade": True,
                },
                {
                    "line_id": "ln-high",
                    "function": "bypass",
                    "rating_band": "rating-band-high",
                    "ordered_count": 1,
                },
            ],
            floor=0.0,
        )
        diodes = assess_diodes(
            [
                _diode("d-med", rating="rating-band-medium"),
                _diode("d-high", rating="rating-band-high"),
            ],
            _index(),
        )
        lines = allocate_diodes_to_lines(diodes, order)["lines"]
        self.assertEqual(lines[0]["allocated_diode_ids"], ("d-med",))
        self.assertEqual(lines[1]["allocated_diode_ids"], ("d-high",))

    def test_a_held_diode_is_never_allocated(self):
        diodes = assess_diodes(
            [
                _diode("d-1"),
                _diode("d-2"),
                _diode("d-3"),
                _diode("d-4", lot_id="lot-z"),
            ],
            _index(),
        )
        line = allocate_diodes_to_lines(diodes, _order())["lines"][0]
        self.assertNotIn("d-4", line["allocated_diode_ids"])
        self.assertEqual(line["shipped_count"], 3)

    def test_a_shippable_diode_no_line_wants_is_surplus(self):
        order = _order(
            lines=[
                {
                    "line_id": "ln-1",
                    "function": "bypass",
                    "rating_band": "rating-band-medium",
                    "ordered_count": 1,
                }
            ],
            floor=0.0,
        )
        diodes = assess_diodes([_diode("d-1"), _diode("d-2")], _index())
        result = allocate_diodes_to_lines(diodes, order)
        self.assertEqual(result["surplus_diode_ids"], ("d-2",))

    def test_a_line_exactly_on_its_floor_is_partial_not_refused(self):
        order = _order(
            lines=[
                {
                    "line_id": "ln-1",
                    "function": "bypass",
                    "rating_band": "rating-band-medium",
                    "ordered_count": 4,
                }
            ],
            floor=0.75,
        )
        diodes = assess_diodes([_diode("d-%d" % n) for n in range(3)], _index())
        line = allocate_diodes_to_lines(diodes, order)["lines"][0]
        self.assertAlmostEqual(line["fill_fraction"], 0.75, places=9)
        self.assertEqual(line["state"], LINE_PARTIAL)

    def test_a_line_below_its_floor_is_refused(self):
        order = _order(
            lines=[
                {
                    "line_id": "ln-1",
                    "function": "bypass",
                    "rating_band": "rating-band-medium",
                    "ordered_count": 4,
                }
            ],
            floor=0.75,
        )
        diodes = assess_diodes([_diode("d-1"), _diode("d-2")], _index())
        line = allocate_diodes_to_lines(diodes, order)["lines"][0]
        self.assertAlmostEqual(line["fill_fraction"], 0.5, places=9)
        self.assertEqual(line["state"], LINE_REFUSED)

    def test_fill_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(FILL_TOLERANCE, 1e-6)


class DispatchTests(unittest.TestCase):
    def test_a_clean_shipment_is_releasable(self):
        result = evaluate_delivery(_spec())
        self.assertEqual(result["verdict"], DISPATCH_RELEASABLE)
        self.assertFalse(result["partial"])
        self.assertAlmostEqual(result["shipment_fill_fraction"], 1.0, places=9)

    def test_the_ordered_count_can_be_met_entirely_by_undocumented_diodes(self):
        spec = _spec(
            diodes=[_diode("d-%d" % n, lot_id="lot-z") for n in range(4)],
        )
        result = evaluate_delivery(spec)
        self.assertEqual(len(result["held_diode_ids"]), 4)
        self.assertEqual(result["verdict"], DISPATCH_HELD)

    def test_one_unreleased_document_holds_every_diode_of_that_lot(self):
        spec = _spec(
            lots=_lots(**{"lot-a": _documents(**{"declaration-of-conformance": "draft"})})
        )
        result = evaluate_delivery(spec)
        self.assertEqual(result["verdict"], DISPATCH_HELD)
        self.assertEqual(result["incomplete_lot_ids"], ("lot-a",))

    def test_a_concession_shipment_is_releasable_and_named(self):
        diodes = [_diode("d-%d" % n) for n in range(3)]
        diodes.append(
            _diode(
                "d-9",
                open_ncr=True,
                concession={"reference": "con-7", "state": "accepted"},
            )
        )
        result = evaluate_delivery(_spec(diodes=diodes))
        self.assertEqual(result["verdict"], DISPATCH_RELEASABLE)
        self.assertEqual(result["concession_diode_ids"], ("d-9",))

    def test_surplus_diodes_are_reported_rather_than_loaded(self):
        spec = _spec(
            order=_order(
                lines=[
                    {
                        "line_id": "ln-1",
                        "function": "bypass",
                        "rating_band": "rating-band-medium",
                        "ordered_count": 2,
                    }
                ],
                floor=0.0,
            )
        )
        result = evaluate_delivery(spec)
        self.assertEqual(len(result["surplus_diode_ids"]), 2)
        self.assertEqual(result["verdict"], DISPATCH_HELD)

    def test_a_partial_shipment_within_the_floor_is_still_flagged_partial(self):
        spec = _spec(
            order=_order(
                lines=[
                    {
                        "line_id": "ln-1",
                        "function": "bypass",
                        "rating_band": "rating-band-medium",
                        "ordered_count": 5,
                    }
                ],
                floor=0.75,
            )
        )
        result = evaluate_delivery(spec)
        self.assertTrue(result["partial"])
        self.assertEqual(result["lines"][0]["state"], LINE_PARTIAL)
        self.assertAlmostEqual(result["shipment_fill_fraction"], 0.8, places=9)

    def test_a_function_mismatch_leaves_the_line_short_and_the_stock_surplus(self):
        spec = _spec(
            order=_order(
                lines=[
                    {
                        "line_id": "ln-1",
                        "function": "blocking",
                        "rating_band": "rating-band-medium",
                        "ordered_count": 4,
                        "allow_rating_upgrade": True,
                    }
                ],
                floor=0.0,
            )
        )
        result = evaluate_delivery(spec)
        self.assertEqual(result["lines"][0]["shipped_count"], 0)
        self.assertEqual(len(result["surplus_diode_ids"]), 4)
        self.assertEqual(result["verdict"], DISPATCH_HELD)

    def test_totals_sum_across_lines(self):
        spec = _spec(
            order=_order(
                lines=[
                    {
                        "line_id": "ln-1",
                        "function": "bypass",
                        "rating_band": "rating-band-medium",
                        "ordered_count": 2,
                    },
                    {
                        "line_id": "ln-2",
                        "function": "bypass",
                        "rating_band": "rating-band-medium",
                        "ordered_count": 2,
                    },
                ],
                floor=0.0,
            )
        )
        result = evaluate_delivery(spec)
        self.assertEqual(result["ordered_total"], 4)
        self.assertEqual(result["shipped_total"], 4)

    def test_substituted_diodes_are_named_at_shipment_level(self):
        spec = _spec(
            order=_order(
                lines=[
                    {
                        "line_id": "ln-1",
                        "function": "bypass",
                        "rating_band": "rating-band-low",
                        "ordered_count": 2,
                        "allow_rating_upgrade": True,
                    }
                ],
                floor=0.0,
            ),
            diodes=[
                _diode("d-1", rating="rating-band-high"),
                _diode("d-2", rating="rating-band-high"),
            ],
        )
        result = evaluate_delivery(spec)
        self.assertEqual(result["substituted_diode_ids"], ("d-1", "d-2"))
        self.assertEqual(result["verdict"], DISPATCH_RELEASABLE)

    def test_spec_missing_a_key_rejected(self):
        spec = _spec()
        del spec["lots"]
        with self.assertRaises(ValueError):
            evaluate_delivery(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_delivery("ship the diodes")


if __name__ == "__main__":
    unittest.main()
