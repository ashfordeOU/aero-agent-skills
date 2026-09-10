#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.6.5 reference coordinate
system and SI unit consistency.

Exercises scripts/e10_coordsys_units_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a unit is
consistent when it matches the canonical SI unit for its quantity type
or carries a documented exception; a frame is consistent when it is a
member of the programme's approved (CSD) frame set; the programme audit
flags every item with a unit and/or frame violation, keyed by item id,
with no duplicate ids accepted; frames used in data but absent from the
approved set are reported as missing definitions.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_coordsys_units_logic as cu  # noqa: E402


class CanonicalUnitTest(unittest.TestCase):
    def test_known_quantity_type(self):
        self.assertEqual(cu.canonical_unit("length"), "m")
        self.assertEqual(cu.canonical_unit("angle"), "rad")

    def test_unknown_quantity_type_raises(self):
        with self.assertRaises(ValueError):
            cu.canonical_unit("luminosity")


class CheckUnitTest(unittest.TestCase):
    def test_matching_unit_is_consistent(self):
        self.assertTrue(cu.check_unit("mass", "kg"))

    def test_mismatched_unit_without_exception_is_inconsistent(self):
        self.assertFalse(cu.check_unit("mass", "lb"))

    def test_mismatched_unit_with_documented_exception_is_consistent(self):
        self.assertTrue(cu.check_unit("pressure", "bar", exception_documented=True))

    def test_unknown_quantity_type_raises(self):
        with self.assertRaises(ValueError):
            cu.check_unit("cosmetic", "m")


class CheckFrameTest(unittest.TestCase):
    def test_approved_frame_is_consistent(self):
        self.assertTrue(cu.check_frame("EME2000", {"EME2000", "ITRF"}))

    def test_unapproved_frame_is_inconsistent(self):
        self.assertFalse(cu.check_frame("MyCustomFrame", {"EME2000", "ITRF"}))


class VerifyDataItemTest(unittest.TestCase):
    APPROVED_FRAMES = {"EME2000", "ITRF"}

    def test_fully_consistent_item(self):
        item = {
            "id": "DI-001",
            "quantity_type": "length",
            "unit": "m",
            "frame": "EME2000",
        }
        self.assertEqual(cu.verify_data_item(item, self.APPROVED_FRAMES), [])

    def test_unit_violation_only(self):
        item = {
            "id": "DI-002",
            "quantity_type": "length",
            "unit": "ft",
            "frame": "EME2000",
        }
        self.assertEqual(cu.verify_data_item(item, self.APPROVED_FRAMES), ["unit"])

    def test_frame_violation_only(self):
        item = {
            "id": "DI-003",
            "quantity_type": "mass",
            "unit": "kg",
            "frame": "LocalBench",
        }
        self.assertEqual(cu.verify_data_item(item, self.APPROVED_FRAMES), ["frame"])

    def test_unit_and_frame_violation(self):
        item = {
            "id": "DI-004",
            "quantity_type": "mass",
            "unit": "lb",
            "frame": "LocalBench",
        }
        self.assertEqual(cu.verify_data_item(item, self.APPROVED_FRAMES), ["unit", "frame"])

    def test_documented_exception_clears_unit_violation(self):
        item = {
            "id": "DI-005",
            "quantity_type": "pressure",
            "unit": "bar",
            "frame": "EME2000",
            "exception_documented": True,
        }
        self.assertEqual(cu.verify_data_item(item, self.APPROVED_FRAMES), [])

    def test_missing_id_raises(self):
        with self.assertRaises(ValueError):
            cu.verify_data_item(
                {"quantity_type": "length", "unit": "m", "frame": "EME2000"},
                self.APPROVED_FRAMES,
            )


class AuditProgrammeDataTest(unittest.TestCase):
    APPROVED_FRAMES = {"EME2000", "ITRF"}
    ITEMS = [
        {"id": "DI-001", "quantity_type": "length", "unit": "m", "frame": "EME2000"},
        {"id": "DI-002", "quantity_type": "length", "unit": "ft", "frame": "EME2000"},
        {"id": "DI-003", "quantity_type": "mass", "unit": "kg", "frame": "LocalBench"},
    ]

    def test_audit_reports_only_violating_items(self):
        report = cu.audit_programme_data(self.ITEMS, self.APPROVED_FRAMES)
        self.assertEqual(report, {"DI-002": ["unit"], "DI-003": ["frame"]})

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            cu.audit_programme_data(self.ITEMS + [self.ITEMS[0]], self.APPROVED_FRAMES)

    def test_no_violations_returns_empty_report(self):
        clean_items = [
            {"id": "DI-010", "quantity_type": "time", "unit": "s", "frame": "ITRF"},
        ]
        self.assertEqual(cu.audit_programme_data(clean_items, self.APPROVED_FRAMES), {})


class MissingFrameDefinitionsTest(unittest.TestCase):
    def test_detects_frames_outside_csd(self):
        used = ["EME2000", "LocalBench", "ITRF", "PayloadFrame"]
        approved = {"EME2000", "ITRF"}
        self.assertEqual(
            cu.missing_frame_definitions(used, approved),
            ["LocalBench", "PayloadFrame"],
        )

    def test_no_gap_returns_empty_list(self):
        self.assertEqual(
            cu.missing_frame_definitions(["EME2000"], {"EME2000", "ITRF"}),
            [],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
