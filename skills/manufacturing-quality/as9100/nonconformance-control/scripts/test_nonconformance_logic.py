#!/usr/bin/env python3
"""Gate 3 contract test: AS9100 nonconformance control.

Exercises scripts/nonconformance_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a nonconforming part is
identified and segregated, then dispositioned (rework, repair, scrap,
use-as-is) with safety-critical parts constrained to rework or scrap;
rework of a critical characteristic requires re-verification; repair and
use-as-is require material review board (MRB) approval; a disposition
record is complete only when identification, segregation, disposition,
disposition authority, and customer notification are all recorded;
unknown inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nonconformance_logic as ncl  # noqa: E402


class DispositionDecisionTest(unittest.TestCase):
    def test_rework_when_rework_meets_spec(self):
        # Dimensional, reworkable, rework brings it back to spec.
        self.assertEqual(
            ncl.disposition_decision("dimensional", True, False, True, False),
            "rework",
        )

    def test_safety_critical_not_reworkable_is_scrap(self):
        # Material, safety-critical, no rework possible: scrap.
        self.assertEqual(
            ncl.disposition_decision("material", False, True, False, True),
            "scrap",
        )

    def test_repair_when_not_safety_critical(self):
        # Process, rework misses spec, repair restores function: repair.
        self.assertEqual(
            ncl.disposition_decision("process", True, True, False, False),
            "repair",
        )

    def test_safety_critical_repairable_still_scrap(self):
        # Finish, safety-critical: rework misses spec and repair is not
        # allowed for safety-critical parts, so scrap.
        self.assertEqual(
            ncl.disposition_decision("finish", True, True, False, True),
            "scrap",
        )

    def test_use_as_is_when_no_better_option(self):
        # Process, nothing restores conformance, not safety-critical.
        self.assertEqual(
            ncl.disposition_decision("process", False, False, False, False),
            "use-as-is",
        )

    def test_reworkable_but_not_repairable_is_scrap(self):
        # Dimensional, rework misses spec, no repair path: scrap.
        self.assertEqual(
            ncl.disposition_decision("dimensional", True, False, False, False),
            "scrap",
        )

    def test_safety_critical_rework_meeting_spec_is_rework(self):
        self.assertEqual(
            ncl.disposition_decision("material", True, False, True, True),
            "rework",
        )

    def test_unknown_nonconformance_type_raises(self):
        with self.assertRaises(ValueError):
            ncl.disposition_decision("electrical", True, False, True, False)


class ReworkReverificationTest(unittest.TestCase):
    def test_rework_of_critical_characteristic_requires_reverification(self):
        self.assertTrue(ncl.rework_requires_reverification("rework", True))

    def test_rework_of_non_critical_characteristic_does_not(self):
        self.assertFalse(ncl.rework_requires_reverification("rework", False))

    def test_scrap_never_requires_reverification(self):
        self.assertFalse(ncl.rework_requires_reverification("scrap", True))

    def test_unknown_disposition_raises(self):
        with self.assertRaises(ValueError):
            ncl.rework_requires_reverification("dispose", True)


class MrbApprovalTest(unittest.TestCase):
    def test_repair_requires_mrb_approval(self):
        self.assertTrue(ncl.mrb_approval_required("repair"))

    def test_use_as_is_requires_mrb_approval(self):
        self.assertTrue(ncl.mrb_approval_required("use-as-is"))

    def test_rework_does_not_require_mrb_approval(self):
        self.assertFalse(ncl.mrb_approval_required("rework"))

    def test_scrap_does_not_require_mrb_approval(self):
        self.assertFalse(ncl.mrb_approval_required("scrap"))

    def test_return_to_supplier_does_not_require_mrb_approval(self):
        self.assertFalse(ncl.mrb_approval_required("return-to-supplier"))

    def test_unknown_disposition_raises(self):
        with self.assertRaises(ValueError):
            ncl.mrb_approval_required("dispose")


class RecordCompletenessTest(unittest.TestCase):
    def test_full_record_is_complete(self):
        result = ncl.disposition_record_complete(True, True, True, True, True)
        self.assertTrue(result["complete"])
        self.assertEqual(result["checks"], 5)
        self.assertEqual(result["total"], 5)
        self.assertEqual(result["missing"], [])

    def test_missing_segregation_is_incomplete(self):
        result = ncl.disposition_record_complete(True, False, True, True, True)
        self.assertFalse(result["complete"])
        self.assertEqual(result["checks"], 4)
        self.assertEqual(result["missing"], ["segregated"])

    def test_missing_customer_notification_is_incomplete(self):
        result = ncl.disposition_record_complete(True, True, True, True, False)
        self.assertFalse(result["complete"])
        self.assertEqual(result["checks"], 4)
        self.assertEqual(result["missing"], ["customer_notified"])


class SummaryTest(unittest.TestCase):
    def test_summary_rework_with_critical_characteristic(self):
        summary = ncl.nonconformance_summary(
            "dimensional", True, False, True, False, characteristic_critical=True
        )
        self.assertEqual(summary["disposition"], "rework")
        self.assertTrue(summary["rework_reverification"])
        self.assertFalse(summary["mrb_required"])
        self.assertTrue(summary["record_complete"]["complete"])

    def test_summary_scrap_with_incomplete_record(self):
        summary = ncl.nonconformance_summary(
            "material",
            False,
            True,
            False,
            True,
            customer_notified=False,
        )
        self.assertEqual(summary["disposition"], "scrap")
        self.assertFalse(summary["rework_reverification"])
        self.assertFalse(summary["mrb_required"])
        self.assertFalse(summary["record_complete"]["complete"])
        self.assertEqual(summary["record_complete"]["missing"], ["customer_notified"])

    def test_summary_repair_requires_mrb(self):
        summary = ncl.nonconformance_summary("process", True, True, False, False)
        self.assertEqual(summary["disposition"], "repair")
        self.assertTrue(summary["mrb_required"])
        self.assertFalse(summary["rework_reverification"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
