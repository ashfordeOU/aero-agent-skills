#!/usr/bin/env python3
"""Gate 3 behavior contract for e1024-idd-drd (stdlib unittest, offline)."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e1024_idd_drd_logic import (  # noqa: E402
    FINDING_AGREED_WITHOUT_ICD_REF,
    FINDING_EMPTY_CHARACTERISTICS,
    FINDING_MISSING_MATING_ITEM,
    FINDING_SUPERSEDED_WITHOUT_SUCCESSOR,
    INTERFACE_STATUSES,
    INTERFACE_TYPES,
    STATUS_AGREED,
    STATUS_DRAFT,
    STATUS_SUPERSEDED,
    STATUS_UNDER_REVIEW,
    interface_record_findings,
    idd_review,
    is_idd_complete,
    status_tally,
    type_coverage,
    validate_interface_type,
    validate_status,
)


# Sentinel distinct from None: a caller must be able to pass characteristics=None
# explicitly and have that None survive into the record under test.
_CHARS_DEFAULT = object()


def rec(itype="electrical", mating="SAT-BUS", chars=_CHARS_DEFAULT,
        status="agreed", icd_ref="ICD-001", successor=None):
    return {
        "interface_type": itype,
        "mating_item": mating,
        "characteristics": {"voltage_v": 28.0} if chars is _CHARS_DEFAULT else chars,
        "status": status,
        "icd_reference": icd_ref,
        "successor_id": successor,
    }


def idd(interfaces, doc_id="IDD-001", prod_id="OBC"):
    return {"document_id": doc_id, "product_id": prod_id,
            "interfaces": interfaces}


def iface(iid, **kwargs):
    r = rec(**kwargs)
    r["interface_id"] = iid
    return r


class VocabularyTest(unittest.TestCase):
    def test_every_interface_type_validates(self):
        for t in INTERFACE_TYPES:
            self.assertEqual(validate_interface_type(t), t)

    def test_every_status_validates(self):
        for s in INTERFACE_STATUSES:
            self.assertEqual(validate_status(s), s)

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            validate_interface_type("acoustic")

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            validate_status("approved")


class RecordFindingsTest(unittest.TestCase):
    def test_clean_agreed_record_has_no_findings(self):
        self.assertEqual(interface_record_findings("I1", rec()), [])

    def test_missing_mating_item_is_flagged(self):
        f = interface_record_findings("I1", rec(mating=None))
        issues = [x["issue"] for x in f]
        self.assertIn(FINDING_MISSING_MATING_ITEM, issues)

    def test_empty_mating_item_string_is_flagged(self):
        f = interface_record_findings("I1", rec(mating=""))
        issues = [x["issue"] for x in f]
        self.assertIn(FINDING_MISSING_MATING_ITEM, issues)

    def test_empty_characteristics_is_flagged(self):
        f = interface_record_findings("I1", rec(chars={}))
        issues = [x["issue"] for x in f]
        self.assertIn(FINDING_EMPTY_CHARACTERISTICS, issues)

    def test_none_characteristics_is_flagged(self):
        f = interface_record_findings("I1", rec(chars=None))
        issues = [x["issue"] for x in f]
        self.assertIn(FINDING_EMPTY_CHARACTERISTICS, issues)

    def test_agreed_without_icd_reference_is_flagged(self):
        f = interface_record_findings("I1", rec(status="agreed", icd_ref=None))
        issues = [x["issue"] for x in f]
        self.assertIn(FINDING_AGREED_WITHOUT_ICD_REF, issues)

    def test_agreed_with_icd_reference_is_clean(self):
        f = interface_record_findings("I1", rec(status="agreed", icd_ref="ICD-42"))
        self.assertEqual(f, [])

    def test_superseded_without_successor_is_flagged(self):
        f = interface_record_findings(
            "I1", rec(status="superseded", icd_ref=None, successor=None))
        issues = [x["issue"] for x in f]
        self.assertIn(FINDING_SUPERSEDED_WITHOUT_SUCCESSOR, issues)

    def test_superseded_with_successor_is_clean(self):
        f = interface_record_findings(
            "I1", rec(status="superseded", icd_ref=None, successor="I2"))
        self.assertEqual(f, [])

    def test_draft_record_no_icd_ref_needed(self):
        f = interface_record_findings(
            "I1", rec(status="draft", icd_ref=None))
        self.assertEqual(f, [])

    def test_unknown_type_in_record_raises(self):
        with self.assertRaises(ValueError):
            interface_record_findings("I1", rec(itype="acoustic"))

    def test_unknown_status_in_record_raises(self):
        with self.assertRaises(ValueError):
            interface_record_findings("I1", rec(status="obsolete"))


class TypeCoverageTest(unittest.TestCase):
    def test_coverage_is_sorted_and_deduplicated(self):
        ifaces = [rec(itype="thermal"), rec(itype="electrical"),
                  rec(itype="thermal")]
        self.assertEqual(type_coverage(ifaces), ["electrical", "thermal"])

    def test_single_type_returns_single_entry(self):
        self.assertEqual(type_coverage([rec(itype="data")]), ["data"])


class StatusTallyTest(unittest.TestCase):
    def test_tally_counts_correctly(self):
        ifaces = [rec(status="agreed"), rec(status="agreed"),
                  rec(status="draft"), rec(status="under_review")]
        t = status_tally(ifaces)
        self.assertEqual(t["agreed"], 2)
        self.assertEqual(t["draft"], 1)
        self.assertEqual(t["under_review"], 1)
        self.assertEqual(t["superseded"], 0)

    def test_empty_list_returns_zero_counts(self):
        t = status_tally([])
        self.assertEqual(sum(t.values()), 0)


class ReviewTest(unittest.TestCase):
    def test_all_agreed_with_refs_is_complete(self):
        r = idd_review(idd([
            iface("I1", status="agreed", icd_ref="ICD-A"),
            iface("I2", status="agreed", icd_ref="ICD-B"),
        ]))
        self.assertEqual(sorted(r["agreed"]), ["I1", "I2"])
        self.assertTrue(is_idd_complete(r))

    def test_draft_interface_blocks_completeness(self):
        r = idd_review(idd([
            iface("I1", status="agreed", icd_ref="ICD-A"),
            iface("I2", status="draft", icd_ref=None),
        ]))
        self.assertIn("I2", r["draft"])
        self.assertFalse(is_idd_complete(r))

    def test_under_review_blocks_completeness(self):
        r = idd_review(idd([iface("I1", status="under_review", icd_ref=None)]))
        self.assertIn("I1", r["under_review"])
        self.assertFalse(is_idd_complete(r))

    def test_agreed_without_icd_ref_blocks_completeness(self):
        r = idd_review(idd([iface("I1", status="agreed", icd_ref=None)]))
        self.assertTrue(is_idd_complete(r) is False)
        self.assertTrue(any(f["issue"] == FINDING_AGREED_WITHOUT_ICD_REF
                            for f in r["findings"]))

    def test_superseded_with_successor_does_not_block_completeness(self):
        r = idd_review(idd([
            iface("I1", status="agreed", icd_ref="ICD-A"),
            iface("I2", status="superseded", icd_ref=None, successor="I3"),
        ]))
        self.assertTrue(is_idd_complete(r))

    def test_superseded_without_successor_adds_finding(self):
        r = idd_review(idd([iface("I1", status="superseded",
                                  icd_ref=None, successor=None)]))
        self.assertTrue(any(f["issue"] == FINDING_SUPERSEDED_WITHOUT_SUCCESSOR
                            for f in r["findings"]))

    def test_interfaces_partition_into_exactly_one_bucket(self):
        r = idd_review(idd([
            iface("I1", status="agreed", icd_ref="ICD-A"),
            iface("I2", status="draft", icd_ref=None),
            iface("I3", status="under_review", icd_ref=None),
            iface("I4", status="superseded", icd_ref=None, successor="I1"),
        ]))
        total = (len(r["agreed"]) + len(r["draft"])
                 + len(r["under_review"]) + len(r["superseded"]))
        self.assertEqual(total, 4)

    def test_duplicate_interface_id_raises(self):
        with self.assertRaises(ValueError):
            idd_review(idd([
                iface("I1", status="agreed", icd_ref="ICD-A"),
                iface("I1", status="draft", icd_ref=None),
            ]))

    def test_missing_interface_id_raises(self):
        with self.assertRaises(ValueError):
            idd_review(idd([rec()]))

    def test_review_does_not_mutate_input(self):
        doc = idd([iface("I1", status="agreed", icd_ref="ICD-A")])
        before = copy.deepcopy(doc)
        idd_review(doc)
        self.assertEqual(doc, before)

    def test_empty_idd_is_vacuously_complete(self):
        self.assertTrue(is_idd_complete(idd_review(idd([]))))

    def test_finding_includes_interface_id(self):
        r = idd_review(idd([iface("I1", status="agreed", icd_ref=None)]))
        self.assertTrue(all("interface_id" in f for f in r["findings"]))

    def test_document_and_product_id_propagated(self):
        r = idd_review(idd([], doc_id="IDD-X", prod_id="PAYLOAD"))
        self.assertEqual(r["document_id"], "IDD-X")
        self.assertEqual(r["product_id"], "PAYLOAD")


if __name__ == "__main__":
    unittest.main()
