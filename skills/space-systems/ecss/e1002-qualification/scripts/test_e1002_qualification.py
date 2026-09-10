#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.4.2 qualification
stage.

Exercises scripts/e1002_qualification_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - heritage
classification follows Table 5-1 (new design; unmodified heritage
within envelope; modified or envelope-exceeding heritage); scope
derivation escalates a safety-critical requirement out of
closed_by_similarity/delta into full; evidence requirements match the
assigned scope; the qualification record covers every product with no
duplicates; manual overrides that leave a safety-critical requirement
closed on closed_by_similarity are flagged; the stage is only reported
complete when every product is closed.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_qualification_logic as ql  # noqa: E402


class ClassifyHeritageTest(unittest.TestCase):
    def test_new_design_wins_regardless_of_other_flags(self):
        self.assertEqual(
            ql.classify_heritage({
                "new_design": True,
                "design_modified": False,
                "within_qualified_envelope": True,
            }),
            "new_design",
        )

    def test_unmodified_within_envelope_is_heritage_full(self):
        self.assertEqual(
            ql.classify_heritage({
                "new_design": False,
                "design_modified": False,
                "within_qualified_envelope": True,
            }),
            "heritage_full",
        )

    def test_modified_is_heritage_delta(self):
        self.assertEqual(
            ql.classify_heritage({
                "new_design": False,
                "design_modified": True,
                "within_qualified_envelope": True,
            }),
            "heritage_delta",
        )

    def test_outside_envelope_is_heritage_delta(self):
        self.assertEqual(
            ql.classify_heritage({
                "new_design": False,
                "design_modified": False,
                "within_qualified_envelope": False,
            }),
            "heritage_delta",
        )


class QualificationScopeTest(unittest.TestCase):
    def test_new_design_is_full(self):
        self.assertEqual(ql.qualification_scope("new_design"), "full")

    def test_heritage_full_is_closed_by_similarity(self):
        self.assertEqual(ql.qualification_scope("heritage_full"), "closed_by_similarity")

    def test_heritage_delta_is_delta(self):
        self.assertEqual(ql.qualification_scope("heritage_delta"), "delta")

    def test_safety_critical_heritage_full_escalates_to_full(self):
        self.assertEqual(
            ql.qualification_scope("heritage_full", safety_critical=True), "full"
        )

    def test_safety_critical_heritage_delta_escalates_to_full(self):
        self.assertEqual(
            ql.qualification_scope("heritage_delta", safety_critical=True), "full"
        )

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            ql.qualification_scope("heritage_partial")


class RequiredEvidenceTest(unittest.TestCase):
    def test_full_needs_qualification_result(self):
        self.assertEqual(ql.required_evidence("full"), "qualification_result")

    def test_similarity_needs_heritage_dossier(self):
        self.assertEqual(ql.required_evidence("closed_by_similarity"), "heritage_dossier")

    def test_delta_needs_delta_result(self):
        self.assertEqual(ql.required_evidence("delta"), "delta_result")

    def test_unknown_scope_raises(self):
        with self.assertRaises(ValueError):
            ql.required_evidence("partial")


class QualifyProductTest(unittest.TestCase):
    def test_closed_when_matching_evidence_supplied(self):
        product = {
            "id": "PROD-001",
            "new_design": False,
            "design_modified": False,
            "within_qualified_envelope": True,
            "safety_critical": False,
            "evidence": ["heritage_dossier"],
        }
        result = ql.qualify_product(product)
        self.assertEqual(result["category"], "heritage_full")
        self.assertEqual(result["scope"], "closed_by_similarity")
        self.assertEqual(result["evidence_needed"], "heritage_dossier")
        self.assertEqual(result["status"], "closed")

    def test_open_when_evidence_missing(self):
        product = {
            "id": "PROD-002",
            "new_design": True,
            "design_modified": False,
            "within_qualified_envelope": True,
            "safety_critical": False,
            "evidence": [],
        }
        result = ql.qualify_product(product)
        self.assertEqual(result["scope"], "full")
        self.assertEqual(result["status"], "open")

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            ql.qualify_product({
                "new_design": True,
                "design_modified": False,
                "within_qualified_envelope": True,
                "safety_critical": False,
                "evidence": [],
            })


class BuildQualificationRecordTest(unittest.TestCase):
    PRODUCTS = [
        {
            "id": "PROD-001",
            "new_design": False,
            "design_modified": False,
            "within_qualified_envelope": True,
            "safety_critical": False,
            "evidence": ["heritage_dossier"],
        },
        {
            "id": "PROD-002",
            "new_design": False,
            "design_modified": True,
            "within_qualified_envelope": True,
            "safety_critical": True,
            "evidence": ["delta_result"],
        },
    ]

    def test_record_order_and_status(self):
        record = ql.build_qualification_record(self.PRODUCTS)
        self.assertEqual(record[0]["id"], "PROD-001")
        self.assertEqual(record[0]["status"], "closed")
        # PROD-002 is heritage_delta but safety_critical, so scope
        # escalates to full (needs qualification_result), and the
        # supplied delta_result does not satisfy it.
        self.assertEqual(record[1]["scope"], "full")
        self.assertEqual(record[1]["status"], "open")

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            ql.build_qualification_record(self.PRODUCTS + [self.PRODUCTS[0]])

    def test_does_not_mutate_input(self):
        before = [dict(p) for p in self.PRODUCTS]
        ql.build_qualification_record(self.PRODUCTS)
        self.assertEqual(self.PRODUCTS, before)


class ApplyManualOverrideTest(unittest.TestCase):
    def setUp(self):
        self.record = ql.build_qualification_record([
            {
                "id": "PROD-001",
                "new_design": False,
                "design_modified": True,
                "within_qualified_envelope": True,
                "safety_critical": True,
                "evidence": ["delta_result"],
            },
        ])

    def test_override_recomputes_evidence_and_status(self):
        overridden = ql.apply_manual_override(
            self.record, {"PROD-001": "closed_by_similarity"}
        )
        self.assertEqual(overridden[0]["scope"], "closed_by_similarity")
        self.assertEqual(overridden[0]["evidence_needed"], "heritage_dossier")
        self.assertEqual(overridden[0]["status"], "open")

    def test_override_does_not_mutate_input(self):
        before = [dict(e) for e in self.record]
        ql.apply_manual_override(self.record, {"PROD-001": "closed_by_similarity"})
        self.assertEqual(self.record, before)

    def test_unknown_override_scope_raises(self):
        with self.assertRaises(ValueError):
            ql.apply_manual_override(self.record, {"PROD-001": "partial"})


class StageCompletionTest(unittest.TestCase):
    def test_open_items_lists_open_ids(self):
        record = [
            {"id": "PROD-001", "status": "closed"},
            {"id": "PROD-002", "status": "open"},
        ]
        self.assertEqual(ql.open_items(record), ["PROD-002"])

    def test_stage_complete_true_when_all_closed(self):
        record = [{"id": "PROD-001", "status": "closed"}]
        self.assertTrue(ql.stage_complete(record))

    def test_stage_complete_false_when_any_open(self):
        record = [
            {"id": "PROD-001", "status": "closed"},
            {"id": "PROD-002", "status": "open"},
        ]
        self.assertFalse(ql.stage_complete(record))


class FindUnsafeHeritageClosuresTest(unittest.TestCase):
    def test_flags_safety_critical_closed_by_similarity(self):
        # Start from a safety-critical, non-heritage-full product so the
        # automatic scope derivation would never itself pick
        # closed_by_similarity, then simulate a human manually
        # overriding the scope and supplying the (insufficient)
        # heritage dossier -- the state the safety-critical rule guards
        # against.
        record = ql.build_qualification_record([
            {
                "id": "PROD-001",
                "new_design": False,
                "design_modified": True,
                "within_qualified_envelope": True,
                "safety_critical": True,
                "evidence": ["heritage_dossier"],
            },
        ])
        overridden = ql.apply_manual_override(
            record, {"PROD-001": "closed_by_similarity"}
        )
        self.assertEqual(overridden[0]["status"], "closed")
        products_by_id = {"PROD-001": {"safety_critical": True}}
        self.assertEqual(
            ql.find_unsafe_heritage_closures(overridden, products_by_id),
            ["PROD-001"],
        )

    def test_clean_record_has_no_unsafe_closures(self):
        record = ql.build_qualification_record([
            {
                "id": "PROD-001",
                "new_design": False,
                "design_modified": False,
                "within_qualified_envelope": True,
                "safety_critical": False,
                "evidence": ["heritage_dossier"],
            },
        ])
        products_by_id = {"PROD-001": {"safety_critical": False}}
        self.assertEqual(ql.find_unsafe_heritage_closures(record, products_by_id), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
