#!/usr/bin/env python3
"""Gate 3 behavior contract for e10-ddp-mapping (stdlib unittest, offline)."""
import copy
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from e10_ddp_mapping_logic import (  # noqa: E402
    DISPOSITIONS, ECSS_DOCUMENTS, ddp_mapping_review, documents_covered,
    is_conversion_sound, item_violations, retired_fraction,
    uncovered_documents, validate_disposition, validate_document,
)


def mapped(iid, targets):
    return {"item_id": iid, "disposition": "mapped", "targets": list(targets),
            "retirement_reason": None}


def retired(iid, reason="superseded by the ECSS DDF structure"):
    return {"item_id": iid, "disposition": "retired", "targets": [],
            "retirement_reason": reason}


def pack():
    return [mapped("L-01", ["ddf"]), mapped("L-02", ["djf", "rjf"]),
            retired("L-03")]


class VocabularyTest(unittest.TestCase):
    def test_every_document_validates(self):
        for d in ECSS_DOCUMENTS:
            self.assertEqual(validate_document(d), d)

    def test_unknown_document_raises(self):
        with self.assertRaises(ValueError):
            validate_document("readme")

    def test_every_disposition_validates(self):
        for d in DISPOSITIONS:
            self.assertEqual(validate_disposition(d), d)

    def test_unknown_disposition_raises(self):
        with self.assertRaises(ValueError):
            validate_disposition("maybe")


class ItemTest(unittest.TestCase):
    def test_mapped_item_with_target_is_clean(self):
        self.assertEqual(item_violations(mapped("L-01", ["ddf"])), [])

    def test_mapped_item_without_target_is_reported(self):
        f = item_violations(mapped("L-01", []))
        self.assertEqual(f[0]["issue"], "mapped_without_target")

    def test_mapped_item_with_unknown_target_raises(self):
        with self.assertRaises(ValueError):
            item_violations(mapped("L-01", ["scrapbook"]))

    def test_retired_item_with_reason_is_clean(self):
        self.assertEqual(item_violations(retired("L-03")), [])

    def test_retired_item_without_reason_is_reported(self):
        f = item_violations(retired("L-03", reason="  "))
        self.assertEqual(f[0]["issue"], "retired_without_reason")

    def test_retired_item_that_also_maps_is_reported(self):
        it = retired("L-03")
        it["targets"] = ["ddf"]
        issues = [f["issue"] for f in item_violations(it)]
        self.assertIn("retired_but_mapped", issues)

    def test_item_without_id_raises(self):
        with self.assertRaises(ValueError):
            item_violations({"disposition": "mapped", "targets": ["ddf"]})


class CoverageTest(unittest.TestCase):
    def test_covered_documents_are_sorted_and_deduplicated(self):
        items = [mapped("A", ["djf", "ddf"]), mapped("B", ["ddf"])]
        self.assertEqual(documents_covered(items), ["ddf", "djf"])

    def test_retired_items_do_not_cover_anything(self):
        self.assertEqual(documents_covered([retired("L-03")]), [])

    def test_uncovered_owed_document_is_reported(self):
        self.assertEqual(uncovered_documents(pack(), ["ddf", "rtm"]), ["rtm"])

    def test_fully_covered_owed_set_reports_nothing(self):
        self.assertEqual(uncovered_documents(pack(), ["ddf", "djf"]), [])

    def test_uncovered_documents_keep_declared_order(self):
        self.assertEqual(uncovered_documents([], ["pum", "ddf"]), ["pum", "ddf"])

    def test_unknown_owed_document_raises(self):
        with self.assertRaises(ValueError):
            uncovered_documents(pack(), ["folklore"])


class FractionTest(unittest.TestCase):
    def test_retired_fraction_is_computed(self):
        self.assertAlmostEqual(retired_fraction(pack()), 1.0 / 3.0)

    def test_all_mapped_gives_zero(self):
        self.assertEqual(retired_fraction([mapped("A", ["ddf"])]), 0.0)

    def test_empty_pack_raises(self):
        with self.assertRaises(ValueError):
            retired_fraction([])


class ReviewTest(unittest.TestCase):
    def test_sound_conversion_has_no_findings(self):
        r = ddp_mapping_review(pack(), ["ddf", "djf", "rjf"])
        self.assertEqual(r["documents_covered"], ["ddf", "djf", "rjf"])
        self.assertTrue(is_conversion_sound(r))

    def test_unsourced_owed_document_blocks_soundness(self):
        r = ddp_mapping_review(pack(), ["ddf", "vcd"])
        self.assertIn("ecss_document_unsourced", [f["issue"] for f in r["findings"]])
        self.assertFalse(is_conversion_sound(r))

    def test_dropped_item_blocks_soundness(self):
        items = pack() + [retired("L-04", reason="")]
        self.assertFalse(is_conversion_sound(ddp_mapping_review(items, ["ddf"])))

    def test_duplicate_item_id_raises(self):
        with self.assertRaises(ValueError):
            ddp_mapping_review(pack() + [mapped("L-01", ["ddf"])], ["ddf"])

    def test_review_does_not_mutate_input(self):
        items = pack()
        before = copy.deepcopy(items)
        ddp_mapping_review(items, ["ddf"])
        self.assertEqual(items, before)

    def test_empty_pack_with_no_owed_documents_is_sound(self):
        self.assertTrue(is_conversion_sound(ddp_mapping_review([], [])))


if __name__ == "__main__":
    unittest.main()
