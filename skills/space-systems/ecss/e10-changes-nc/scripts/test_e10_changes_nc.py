#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.6.9 control of
engineering changes and nonconformances.

Exercises scripts/e10_changes_nc_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - an item requires a baseline
change when it affects requirements or design, in which case it routes
to CCB (change) or NRB (nonconformance); an item may only be
implemented once it is closed, approved, and (if baseline-impacting)
the baseline has been updated; approved baseline-impacting items must
go through update_baseline, not close_item directly; invalid state
transitions and empty/invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_changes_nc_logic as cnc  # noqa: E402


class RequiredAuthorityTest(unittest.TestCase):
    def test_local_when_no_baseline_impact(self):
        self.assertEqual(cnc.required_authority("change", False), "local")
        self.assertEqual(cnc.required_authority("nonconformance", False), "local")

    def test_ccb_for_baseline_impacting_change(self):
        self.assertEqual(cnc.required_authority("change", True), "CCB")

    def test_nrb_for_baseline_impacting_nonconformance(self):
        self.assertEqual(cnc.required_authority("nonconformance", True), "NRB")

    def test_unknown_item_type_raises(self):
        with self.assertRaises(ValueError):
            cnc.required_authority("deviation", True)


class RaiseItemTest(unittest.TestCase):
    def test_raise_baseline_impacting_change(self):
        record = cnc.raise_item(
            "ECR-001", "change", "swap thruster supplier", True, False,
        )
        self.assertEqual(record["item_id"], "ECR-001")
        self.assertEqual(record["item_type"], "change")
        self.assertTrue(record["requires_baseline_change"])
        self.assertEqual(record["authority"], "CCB")
        self.assertEqual(record["status"], "raised")
        self.assertIsNone(record["disposition"])
        self.assertFalse(record["baseline_updated"])

    def test_raise_non_baseline_impacting_nonconformance(self):
        record = cnc.raise_item(
            "NCR-014", "nonconformance", "cosmetic scratch on bracket", False, False,
        )
        self.assertFalse(record["requires_baseline_change"])
        self.assertEqual(record["authority"], "local")

    def test_empty_item_id_raises(self):
        with self.assertRaises(ValueError):
            cnc.raise_item("", "change", "desc", True, False)

    def test_empty_description_raises(self):
        with self.assertRaises(ValueError):
            cnc.raise_item("ECR-002", "change", "", True, False)

    def test_invalid_item_type_raises(self):
        with self.assertRaises(ValueError):
            cnc.raise_item("ECR-003", "deviation", "desc", True, False)


class DispositionItemTest(unittest.TestCase):
    def test_disposition_approved(self):
        record = cnc.raise_item("ECR-004", "change", "desc", True, False)
        dispositioned = cnc.disposition_item(record, "approved", "CCB agreed, low risk")
        self.assertEqual(dispositioned["disposition"], "approved")
        self.assertEqual(dispositioned["disposition_rationale"], "CCB agreed, low risk")
        self.assertEqual(dispositioned["status"], "dispositioned")
        self.assertEqual(record["status"], "raised")

    def test_disposition_rejected(self):
        record = cnc.raise_item("ECR-005", "change", "desc", True, False)
        dispositioned = cnc.disposition_item(record, "rejected", "cost prohibitive")
        self.assertEqual(dispositioned["disposition"], "rejected")

    def test_disposition_non_raised_raises(self):
        record = cnc.raise_item("ECR-006", "change", "desc", True, False)
        dispositioned = cnc.disposition_item(record, "approved", "ok")
        with self.assertRaises(ValueError):
            cnc.disposition_item(dispositioned, "approved", "ok again")

    def test_invalid_decision_raises(self):
        record = cnc.raise_item("ECR-007", "change", "desc", True, False)
        with self.assertRaises(ValueError):
            cnc.disposition_item(record, "deferred", "not sure")

    def test_empty_rationale_raises(self):
        record = cnc.raise_item("ECR-008", "change", "desc", True, False)
        with self.assertRaises(ValueError):
            cnc.disposition_item(record, "approved", "")


class UpdateBaselineTest(unittest.TestCase):
    def test_update_baseline_closes_approved_baseline_item(self):
        record = cnc.raise_item("ECR-009", "change", "desc", True, False)
        dispositioned = cnc.disposition_item(record, "approved", "ok")
        closed = cnc.update_baseline(dispositioned)
        self.assertTrue(closed["baseline_updated"])
        self.assertEqual(closed["status"], "closed")
        self.assertFalse(dispositioned["baseline_updated"])

    def test_update_baseline_before_disposition_raises(self):
        record = cnc.raise_item("ECR-010", "change", "desc", True, False)
        with self.assertRaises(ValueError):
            cnc.update_baseline(record)

    def test_update_baseline_on_rejected_raises(self):
        record = cnc.raise_item("ECR-011", "change", "desc", True, False)
        dispositioned = cnc.disposition_item(record, "rejected", "no")
        with self.assertRaises(ValueError):
            cnc.update_baseline(dispositioned)

    def test_update_baseline_without_baseline_impact_raises(self):
        record = cnc.raise_item("NCR-020", "nonconformance", "desc", False, False)
        dispositioned = cnc.disposition_item(record, "approved", "use as-is")
        with self.assertRaises(ValueError):
            cnc.update_baseline(dispositioned)


class CloseItemTest(unittest.TestCase):
    def test_close_rejected_item(self):
        record = cnc.raise_item("ECR-012", "change", "desc", True, False)
        dispositioned = cnc.disposition_item(record, "rejected", "no")
        closed = cnc.close_item(dispositioned)
        self.assertEqual(closed["status"], "closed")

    def test_close_approved_non_baseline_item(self):
        record = cnc.raise_item("NCR-021", "nonconformance", "desc", False, False)
        dispositioned = cnc.disposition_item(record, "approved", "use as-is")
        closed = cnc.close_item(dispositioned)
        self.assertEqual(closed["status"], "closed")

    def test_close_approved_baseline_item_raises(self):
        record = cnc.raise_item("ECR-013", "change", "desc", True, False)
        dispositioned = cnc.disposition_item(record, "approved", "ok")
        with self.assertRaises(ValueError):
            cnc.close_item(dispositioned)

    def test_close_before_disposition_raises(self):
        record = cnc.raise_item("ECR-014", "change", "desc", True, False)
        with self.assertRaises(ValueError):
            cnc.close_item(record)


class MayImplementTest(unittest.TestCase):
    def test_true_after_baseline_update(self):
        record = cnc.raise_item("ECR-015", "change", "desc", True, False)
        dispositioned = cnc.disposition_item(record, "approved", "ok")
        closed = cnc.update_baseline(dispositioned)
        self.assertTrue(cnc.may_implement(closed))

    def test_false_while_dispositioned_but_not_baseline_updated(self):
        record = cnc.raise_item("ECR-016", "change", "desc", True, False)
        dispositioned = cnc.disposition_item(record, "approved", "ok")
        self.assertFalse(cnc.may_implement(dispositioned))

    def test_false_when_rejected(self):
        record = cnc.raise_item("ECR-017", "change", "desc", True, False)
        dispositioned = cnc.disposition_item(record, "rejected", "no")
        closed = cnc.close_item(dispositioned)
        self.assertFalse(cnc.may_implement(closed))

    def test_true_for_approved_non_baseline_item_once_closed(self):
        record = cnc.raise_item("NCR-022", "nonconformance", "desc", False, False)
        dispositioned = cnc.disposition_item(record, "approved", "use as-is")
        closed = cnc.close_item(dispositioned)
        self.assertTrue(cnc.may_implement(closed))


class RegisterStatusTest(unittest.TestCase):
    def test_ready_when_all_closed(self):
        r1 = cnc.raise_item("ECR-018", "change", "desc", True, False)
        r1 = cnc.disposition_item(r1, "approved", "ok")
        r1 = cnc.update_baseline(r1)
        r2 = cnc.raise_item("NCR-023", "nonconformance", "desc", False, False)
        r2 = cnc.disposition_item(r2, "rejected", "no")
        r2 = cnc.close_item(r2)
        ready, open_items = cnc.register_status([r1, r2])
        self.assertTrue(ready)
        self.assertEqual(open_items, [])

    def test_not_ready_lists_open_items(self):
        raised = cnc.raise_item("ECR-019", "change", "desc", True, False)
        ready, open_items = cnc.register_status([raised])
        self.assertFalse(ready)
        self.assertEqual(open_items, [raised])


class ItemsByTypeTest(unittest.TestCase):
    def test_filters_by_item_type(self):
        change = cnc.raise_item("ECR-020", "change", "desc", True, False)
        nc = cnc.raise_item("NCR-024", "nonconformance", "desc", False, False)
        result = cnc.items_by_type([change, nc], "nonconformance")
        self.assertEqual(result, [nc])


if __name__ == "__main__":
    unittest.main(verbosity=2)
