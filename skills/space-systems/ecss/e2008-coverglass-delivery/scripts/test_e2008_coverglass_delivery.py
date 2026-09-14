#!/usr/bin/env python3
"""Contract test for the coverglass dispatch check, clause 8.10 (offline)."""

import unittest

from e2008_coverglass_delivery_logic import (
    BATCH_HELD,
    BATCH_RELEASABLE,
    DELIVERY_HELD,
    DELIVERY_RELEASABLE,
    DOCUMENT_KINDS,
    DOC_ACCEPTED,
    DOC_ISSUE_SUPERSEDED,
    DOC_MISSING,
    DOC_UNSIGNED,
    FILL_TOLERANCE,
    LINE_COMPLETE,
    LINE_PARTIAL,
    LINE_REFUSED,
    allocate_batches_to_lines,
    assess_batch,
    assess_batches,
    document_state_for_batch,
    evaluate_delivery,
    normalize_document_kind,
    normalize_type,
    validate_document,
    validate_documents,
    validate_order,
    validate_order_line,
)

AGREED = ("certificate-of-conformity", "acceptance-test-report")


def _doc(document_id, kind, covers, issue=3, governing=3, signed=True):
    return {
        "document_id": document_id,
        "kind": kind,
        "issue": issue,
        "governing_issue": governing,
        "signed": signed,
        "covers_batch_ids": list(covers),
    }


def _docs(covers=("bt-1",)):
    return [
        _doc("coc-1", "certificate-of-conformity", covers),
        _doc("atr-1", "acceptance-test-report", covers),
    ]


def _batch(batch_id="bt-1", coverglass_type="cmx-100", pieces=40):
    return {
        "batch_id": batch_id,
        "coverglass_type": coverglass_type,
        "piece_count": pieces,
    }


def _order(lines=None, floor=0.8, agreed=AGREED, order_id="ord-2026-08"):
    return {
        "order_id": order_id,
        "agreed_document_kinds": list(agreed),
        "partial_delivery_floor": floor,
        "lines": lines
        if lines is not None
        else [{"line_id": "ln-1", "coverglass_type": "cmx-100", "ordered_count": 40}],
    }


def _spec(**overrides):
    spec = {
        "shipment_id": "shp-0101",
        "order": _order(),
        "documents": _docs(),
        "batches": [_batch()],
    }
    spec.update(overrides)
    return spec


class VocabularyTests(unittest.TestCase):
    def test_agreed_kinds_come_from_a_named_set(self):
        self.assertIn("certificate-of-conformity", DOCUMENT_KINDS)
        self.assertIn("batch-traceability-record", DOCUMENT_KINDS)

    def test_document_kind_is_trimmed_and_lowercased(self):
        self.assertEqual(
            normalize_document_kind("  Certificate-Of-Conformity "),
            "certificate-of-conformity",
        )

    def test_unknown_document_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_document_kind("delivery-note")

    def test_coverglass_type_is_trimmed_and_lowercased(self):
        self.assertEqual(normalize_type(" CMX-100 "), "cmx-100")

    def test_empty_coverglass_type_rejected(self):
        with self.assertRaises(ValueError):
            normalize_type("   ")

    def test_document_states_are_told_apart(self):
        self.assertEqual(
            len({DOC_ACCEPTED, DOC_MISSING, DOC_ISSUE_SUPERSEDED, DOC_UNSIGNED}), 4
        )


class OrderValidationTests(unittest.TestCase):
    def test_line_defaults_to_no_permitted_substitution(self):
        line = validate_order_line(
            {"line_id": "ln-1", "coverglass_type": "CMX-100", "ordered_count": 10}
        )
        self.assertEqual(line["permitted_substitute_types"], ())

    def test_line_may_not_name_its_own_type_as_a_substitution(self):
        with self.assertRaises(ValueError):
            validate_order_line(
                {
                    "line_id": "ln-1",
                    "coverglass_type": "cmx-100",
                    "ordered_count": 10,
                    "permitted_substitute_types": ["cmx-100"],
                }
            )

    def test_zero_ordered_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_order_line(
                {"line_id": "ln-1", "coverglass_type": "cmx-100", "ordered_count": 0}
            )

    def test_repeated_line_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(
                _order(
                    lines=[
                        {"line_id": "ln-1", "coverglass_type": "cmx-100",
                         "ordered_count": 4},
                        {"line_id": "ln-1", "coverglass_type": "cmx-200",
                         "ordered_count": 4},
                    ]
                )
            )

    def test_order_with_no_agreed_document_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(_order(agreed=()))

    def test_floor_outside_the_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(_order(floor=1.4))

    def test_repeated_agreed_kind_rejected(self):
        with self.assertRaises(ValueError):
            validate_order(
                _order(agreed=("packing-list", "packing-list"))
            )


class DocumentTests(unittest.TestCase):
    def test_document_missing_key_rejected(self):
        record = _doc("coc-1", "certificate-of-conformity", ("bt-1",))
        del record["signed"]
        with self.assertRaises(ValueError):
            validate_document(record)

    def test_repeated_document_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_documents(
                [
                    _doc("coc-1", "certificate-of-conformity", ("bt-1",)),
                    _doc("coc-1", "packing-list", ("bt-1",)),
                ]
            )

    def test_document_covering_another_batch_is_missing_for_this_one(self):
        documents = validate_documents(_docs(covers=("bt-9",)))
        state = document_state_for_batch(
            "certificate-of-conformity", "bt-1", documents
        )
        self.assertEqual(state["state"], DOC_MISSING)

    def test_superseded_issue_is_reported_as_such(self):
        documents = validate_documents(
            [_doc("coc-1", "certificate-of-conformity", ("bt-1",), issue=2,
                  governing=4)]
        )
        state = document_state_for_batch(
            "certificate-of-conformity", "bt-1", documents
        )
        self.assertEqual(state["state"], DOC_ISSUE_SUPERSEDED)

    def test_unsigned_record_is_reported_as_such(self):
        documents = validate_documents(
            [_doc("coc-1", "certificate-of-conformity", ("bt-1",), signed=False)]
        )
        state = document_state_for_batch(
            "certificate-of-conformity", "bt-1", documents
        )
        self.assertEqual(state["state"], DOC_UNSIGNED)

    def test_a_standing_record_beats_a_superseded_duplicate(self):
        documents = validate_documents(
            [
                _doc("coc-old", "certificate-of-conformity", ("bt-1",), issue=1,
                     governing=4),
                _doc("coc-new", "certificate-of-conformity", ("bt-1",), issue=4,
                     governing=4),
            ]
        )
        state = document_state_for_batch(
            "certificate-of-conformity", "bt-1", documents
        )
        self.assertEqual(state["state"], DOC_ACCEPTED)
        self.assertEqual(state["document_id"], "coc-new")


class BatchDispositionTests(unittest.TestCase):
    def test_fully_documented_batch_is_releasable(self):
        documents = validate_documents(_docs())
        result = assess_batch(_batch(), documents, AGREED)
        self.assertEqual(result["disposition"], BATCH_RELEASABLE)
        self.assertAlmostEqual(result["documentation_fraction"], 1.0, places=9)

    def test_batch_missing_one_agreed_document_is_held(self):
        documents = validate_documents(
            [_doc("coc-1", "certificate-of-conformity", ("bt-1",))]
        )
        result = assess_batch(_batch(), documents, AGREED)
        self.assertEqual(result["disposition"], BATCH_HELD)
        self.assertAlmostEqual(result["documentation_fraction"], 0.5, places=9)
        self.assertTrue(result["reasons"])

    def test_repeated_batch_id_rejected(self):
        documents = validate_documents(_docs(covers=("bt-1",)))
        with self.assertRaises(ValueError):
            assess_batches([_batch(), _batch()], documents, AGREED)

    def test_empty_batch_list_rejected(self):
        documents = validate_documents(_docs())
        with self.assertRaises(ValueError):
            assess_batches([], documents, AGREED)


class AllocationTests(unittest.TestCase):
    def test_exact_type_is_spent_before_a_permitted_alternative(self):
        documents = validate_documents(_docs(covers=("bt-1", "bt-2")))
        assessed = assess_batches(
            [_batch("bt-1", "cmx-100", 6), _batch("bt-2", "cmx-200", 6)],
            documents,
            AGREED,
        )
        order = _order(
            lines=[
                {
                    "line_id": "ln-1",
                    "coverglass_type": "cmx-100",
                    "ordered_count": 4,
                    "permitted_substitute_types": ["cmx-200"],
                }
            ],
            floor=0.0,
        )
        result = allocate_batches_to_lines(assessed, order)
        line = result["lines"][0]
        self.assertEqual(line["drawn_from"][0]["batch_id"], "bt-1")
        self.assertEqual(line["substituted_from"], ())

    def test_a_type_the_line_never_named_is_never_drawn_on(self):
        documents = validate_documents(_docs(covers=("bt-2",)))
        assessed = assess_batches([_batch("bt-2", "cmx-200", 10)], documents, AGREED)
        order = _order(
            lines=[{"line_id": "ln-1", "coverglass_type": "cmx-100",
                    "ordered_count": 4}],
            floor=0.0,
        )
        result = allocate_batches_to_lines(assessed, order)
        self.assertEqual(result["lines"][0]["shipped_count"], 0)

    def test_permitted_alternative_fills_the_shortfall_and_is_named(self):
        documents = validate_documents(_docs(covers=("bt-1", "bt-2")))
        assessed = assess_batches(
            [_batch("bt-1", "cmx-100", 2), _batch("bt-2", "cmx-200", 6)],
            documents,
            AGREED,
        )
        order = _order(
            lines=[
                {
                    "line_id": "ln-1",
                    "coverglass_type": "cmx-100",
                    "ordered_count": 5,
                    "permitted_substitute_types": ["cmx-200"],
                }
            ],
            floor=0.0,
        )
        result = allocate_batches_to_lines(assessed, order)
        line = result["lines"][0]
        self.assertEqual(line["shipped_count"], 5)
        self.assertEqual(line["substituted_from"][0]["piece_count"], 3)

    def test_a_held_batch_is_not_available_to_any_line(self):
        documents = validate_documents(
            [_doc("coc-1", "certificate-of-conformity", ("bt-1",))]
        )
        assessed = assess_batches([_batch("bt-1", "cmx-100", 40)], documents, AGREED)
        order = _order(floor=0.0)
        result = allocate_batches_to_lines(assessed, order)
        self.assertEqual(result["lines"][0]["shipped_count"], 0)

    def test_line_exactly_on_its_floor_clears_it(self):
        documents = validate_documents(_docs())
        assessed = assess_batches([_batch("bt-1", "cmx-100", 4)], documents, AGREED)
        order = _order(
            lines=[{"line_id": "ln-1", "coverglass_type": "cmx-100",
                    "ordered_count": 5}],
            floor=0.8,
        )
        result = allocate_batches_to_lines(assessed, order)
        line = result["lines"][0]
        self.assertAlmostEqual(line["fill_fraction"], 0.8, places=9)
        self.assertEqual(line["state"], LINE_PARTIAL)

    def test_line_below_its_floor_is_refused(self):
        documents = validate_documents(_docs())
        assessed = assess_batches([_batch("bt-1", "cmx-100", 2)], documents, AGREED)
        order = _order(
            lines=[{"line_id": "ln-1", "coverglass_type": "cmx-100",
                    "ordered_count": 5}],
            floor=0.8,
        )
        result = allocate_batches_to_lines(assessed, order)
        self.assertEqual(result["lines"][0]["state"], LINE_REFUSED)

    def test_tolerance_is_small_and_named(self):
        self.assertGreater(FILL_TOLERANCE, 0.0)
        self.assertLess(FILL_TOLERANCE, 1e-6)


class ShipmentVerdictTests(unittest.TestCase):
    def test_clean_shipment_is_releasable(self):
        result = evaluate_delivery(_spec())
        self.assertEqual(result["verdict"], DELIVERY_RELEASABLE)
        self.assertEqual(result["findings"], ())
        self.assertEqual(result["lines"][0]["state"], LINE_COMPLETE)

    def test_count_alone_does_not_release_an_undocumented_shipment(self):
        spec = _spec(documents=_docs(covers=("bt-9",)))
        result = evaluate_delivery(spec)
        self.assertEqual(result["verdict"], DELIVERY_HELD)
        self.assertEqual(result["held_batch_ids"], ("bt-1",))
        self.assertEqual(result["shipped_total"], 0)

    def test_surplus_glass_is_reported_rather_than_loaded(self):
        spec = _spec(
            batches=[_batch("bt-1", "cmx-100", 50)],
            order=_order(
                lines=[{"line_id": "ln-1", "coverglass_type": "cmx-100",
                        "ordered_count": 40}]
            ),
        )
        result = evaluate_delivery(spec)
        self.assertEqual(result["surplus"][0]["piece_count"], 10)
        self.assertEqual(result["verdict"], DELIVERY_HELD)

    def test_shipment_fill_fraction_is_reported(self):
        spec = _spec(
            batches=[_batch("bt-1", "cmx-100", 20)],
            order=_order(
                lines=[{"line_id": "ln-1", "coverglass_type": "cmx-100",
                        "ordered_count": 40}],
                floor=0.0,
            ),
        )
        result = evaluate_delivery(spec)
        self.assertAlmostEqual(result["shipment_fill_fraction"], 0.5, places=9)
        self.assertTrue(result["partial"])

    def test_substituted_lines_are_named_in_the_dispatch(self):
        spec = _spec(
            documents=_docs(covers=("bt-1", "bt-2")),
            batches=[_batch("bt-1", "cmx-100", 2), _batch("bt-2", "cmx-200", 3)],
            order=_order(
                lines=[
                    {
                        "line_id": "ln-1",
                        "coverglass_type": "cmx-100",
                        "ordered_count": 5,
                        "permitted_substitute_types": ["cmx-200"],
                    }
                ]
            ),
        )
        result = evaluate_delivery(spec)
        self.assertEqual(result["substituted_line_ids"], ("ln-1",))
        self.assertEqual(result["verdict"], DELIVERY_RELEASABLE)

    def test_spec_missing_a_key_rejected(self):
        spec = _spec()
        del spec["documents"]
        with self.assertRaises(ValueError):
            evaluate_delivery(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_delivery("ship it")


if __name__ == "__main__":
    unittest.main()
