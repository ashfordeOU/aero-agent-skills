#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C Annex A delivery-per-review check.

Exercises scripts/e10_delivery_per_review_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a delivery
schedule maps SE documents to the review milestones each is due at
(first issue or re-baseline); a review's delivery is complete only when
every document scheduled for it was delivered (unplanned deliveries are
flagged but do not block completeness), and readiness rolls up across
the whole review sequence.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_delivery_per_review_logic as dr  # noqa: E402


SCHEDULE = {
    "MDD": ["MDR"],
    "SEP": ["MDR", "PDR", "CDR"],
    "spec-tree": ["PRR", "SRR", "PDR"],
    "TS": ["SRR", "PDR", "CDR"],
    "ICD": ["PDR", "CDR"],
    "RVM": ["PDR", "CDR", "QR"],
}


class DocumentsDueAtTest(unittest.TestCase):
    def test_documents_due_at_review_in_schedule_order(self):
        self.assertEqual(dr.documents_due_at(SCHEDULE, "PDR"), ["SEP", "spec-tree", "TS", "ICD", "RVM"])

    def test_no_documents_due_at_unscheduled_review(self):
        self.assertEqual(dr.documents_due_at(SCHEDULE, "FRR"), [])


class ReviewsForDocumentTest(unittest.TestCase):
    def test_reviews_for_known_document(self):
        self.assertEqual(dr.reviews_for_document(SCHEDULE, "SEP"), ["MDR", "PDR", "CDR"])

    def test_reviews_for_unknown_document_is_empty(self):
        self.assertEqual(dr.reviews_for_document(SCHEDULE, "not-a-doc"), [])


class MissingDeliveriesTest(unittest.TestCase):
    def test_no_missing_when_all_delivered(self):
        delivered = ["MDD", "SEP"]
        self.assertEqual(dr.missing_deliveries(SCHEDULE, "MDR", delivered), [])

    def test_missing_reported_in_schedule_order(self):
        delivered = ["SEP"]
        self.assertEqual(dr.missing_deliveries(SCHEDULE, "MDR", delivered), ["MDD"])

    def test_missing_at_review_with_several_documents(self):
        delivered = ["spec-tree", "ICD"]
        self.assertEqual(dr.missing_deliveries(SCHEDULE, "PDR", delivered), ["SEP", "TS", "RVM"])


class UnplannedDeliveriesTest(unittest.TestCase):
    def test_no_unplanned_when_only_scheduled_documents_delivered(self):
        delivered = ["MDD", "SEP"]
        self.assertEqual(dr.unplanned_deliveries(SCHEDULE, "MDR", delivered), [])

    def test_unplanned_reported_in_delivered_order(self):
        delivered = ["MDD", "TS", "SEP"]
        self.assertEqual(dr.unplanned_deliveries(SCHEDULE, "MDR", delivered), ["TS"])


class ReviewDeliveryCompleteTest(unittest.TestCase):
    def test_complete_when_nothing_missing(self):
        complete, missing = dr.review_delivery_complete(SCHEDULE, "MDR", ["MDD", "SEP"])
        self.assertTrue(complete)
        self.assertEqual(missing, [])

    def test_incomplete_when_missing_scheduled_document(self):
        complete, missing = dr.review_delivery_complete(SCHEDULE, "MDR", ["SEP"])
        self.assertFalse(complete)
        self.assertEqual(missing, ["MDD"])

    def test_unplanned_delivery_does_not_block_completeness(self):
        complete, missing = dr.review_delivery_complete(SCHEDULE, "MDR", ["MDD", "SEP", "extra-note"])
        self.assertTrue(complete)
        self.assertEqual(missing, [])


class ScheduleReadinessTest(unittest.TestCase):
    def test_all_complete_when_every_scheduled_review_fully_delivered(self):
        deliveries = {
            "MDR": ["MDD", "SEP"],
            "PRR": ["spec-tree"],
            "SRR": ["spec-tree", "TS"],
            "PDR": ["SEP", "spec-tree", "TS", "ICD", "RVM"],
            "CDR": ["SEP", "TS", "ICD", "RVM"],
            "QR": ["RVM"],
        }
        all_complete, per_review = dr.schedule_readiness(SCHEDULE, deliveries)
        self.assertTrue(all_complete)
        for review in per_review:
            self.assertEqual(per_review[review]["missing"], [])

    def test_missing_review_reported_not_complete(self):
        deliveries = {
            "MDR": ["MDD"],  # SEP missing
        }
        all_complete, per_review = dr.schedule_readiness(SCHEDULE, deliveries)
        self.assertFalse(all_complete)
        self.assertEqual(per_review["MDR"]["missing"], ["SEP"])
        # a scheduled review absent from deliveries is treated as nothing delivered
        self.assertEqual(per_review["PRR"]["missing"], ["spec-tree"])

    def test_unplanned_review_delivery_included_and_does_not_block(self):
        deliveries = {
            "MDR": ["MDD", "SEP"],
            "FRR": ["acceptance-note"],  # FRR not in SCHEDULE at all
        }
        all_complete, per_review = dr.schedule_readiness(SCHEDULE, deliveries)
        self.assertIn("FRR", per_review)
        self.assertEqual(per_review["FRR"]["missing"], [])
        self.assertEqual(per_review["FRR"]["unplanned"], ["acceptance-note"])
        # other scheduled reviews still have missing documents so overall is False
        self.assertFalse(all_complete)


if __name__ == "__main__":
    unittest.main(verbosity=2)
