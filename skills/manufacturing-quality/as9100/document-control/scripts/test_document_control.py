#!/usr/bin/env python3
"""Gate 3 contract test: document control.

Exercises scripts/document_control_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3: revision
comparison (letters, integers, mixed and empty rejection), the
approval-before-issue rule (approver present and not the author),
register validity, the use verdict for a copy (current, superseded,
unreleased, future-revision), the master-list lookup, the current
revision of the master list, and the obsolete disposition; invalid
inputs raise ValueError. The physically meaningful invariants:
revision comparison is antisymmetric, obsolete entries never yield a
current verdict, and the current revision comes from issued entries
only.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import document_control_logic as dcl  # noqa: E402


class RevisionCompareTest(unittest.TestCase):
    def test_letter_revisions(self):
        self.assertEqual(dcl.revision_compare("A", "B"), -1)
        self.assertEqual(dcl.revision_compare("B", "A"), 1)
        self.assertEqual(dcl.revision_compare("C", "C"), 0)

    def test_letter_case_insensitive(self):
        self.assertEqual(dcl.revision_compare("a", "A"), 0)
        self.assertEqual(dcl.revision_compare("a", "B"), -1)

    def test_integer_revisions(self):
        self.assertEqual(dcl.revision_compare("1", "2"), -1)
        self.assertEqual(dcl.revision_compare("10", "2"), 1)
        self.assertEqual(dcl.revision_compare("3", "3"), 0)

    def test_mixed_pair_raises(self):
        with self.assertRaises(ValueError):
            dcl.revision_compare("A", "2")

    def test_empty_revision_raises(self):
        with self.assertRaises(ValueError):
            dcl.revision_compare("", "A")
        with self.assertRaises(ValueError):
            dcl.revision_compare("A", None)

    def test_antisymmetry_invariant(self):
        for a, b in (("A", "B"), ("1", "5"), ("C", "C"), ("7", "3")):
            self.assertEqual(dcl.revision_compare(a, b), -dcl.revision_compare(b, a))


class ApprovalTest(unittest.TestCase):
    def test_independent_approver_ok(self):
        entry = {"author": "jane", "approver": "omar"}
        self.assertTrue(dcl.approval_ok(entry))

    def test_same_person_rejected(self):
        entry = {"author": "jane", "approver": "jane"}
        self.assertFalse(dcl.approval_ok(entry))

    def test_same_person_case_insensitive_rejected(self):
        entry = {"author": "Jane", "approver": "jane"}
        self.assertFalse(dcl.approval_ok(entry))

    def test_missing_approver_rejected(self):
        self.assertFalse(dcl.approval_ok({"author": "jane", "approver": ""}))
        self.assertFalse(dcl.approval_ok({"author": "jane"}))

    def test_missing_author_rejected(self):
        self.assertFalse(dcl.approval_ok({"author": "", "approver": "omar"}))

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            dcl.approval_ok("jane")


class RegisterValidityTest(unittest.TestCase):
    VALID = {
        "doc_number": "OP-1042",
        "title": "final assembly work instruction",
        "revision": "C",
        "issue_date": "2026-06-01",
        "status": "issued",
        "author": "jane",
        "approver": "omar",
    }

    def test_valid_issued_entry(self):
        self.assertEqual(dcl.register_validity(self.VALID), "valid")

    def test_valid_draft_entry_needs_no_approval(self):
        entry = dict(self.VALID)
        entry["status"] = "draft"
        entry["approver"] = ""
        self.assertEqual(dcl.register_validity(entry), "valid")

    def test_missing_fields(self):
        for key in ("doc_number", "title", "revision", "issue_date"):
            entry = dict(self.VALID)
            entry[key] = ""
            self.assertEqual(
                dcl.register_validity(entry), "missing-%s" % key.replace("_", "-"), key
            )

    def test_unknown_status(self):
        entry = dict(self.VALID)
        entry["status"] = "pending"
        self.assertEqual(dcl.register_validity(entry), "unknown-status")

    def test_issued_without_approval(self):
        entry = dict(self.VALID)
        entry["approver"] = "jane"
        self.assertEqual(dcl.register_validity(entry), "missing-approval")

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            dcl.register_validity("OP-1042")


class UseVerdictTest(unittest.TestCase):
    def _entry(self, **overrides):
        entry = {
            "doc_number": "OP-1042",
            "title": "final assembly work instruction",
            "revision": "C",
            "issue_date": "2026-06-01",
            "status": "issued",
            "author": "jane",
            "approver": "omar",
        }
        entry.update(overrides)
        return entry

    def test_current_revision(self):
        self.assertEqual(dcl.use_verdict(self._entry(), "C"), "current")

    def test_older_copy_superseded(self):
        self.assertEqual(dcl.use_verdict(self._entry(), "D"), "superseded")

    def test_ahead_copy_future_revision(self):
        self.assertEqual(dcl.use_verdict(self._entry(), "B"), "future-revision")

    def test_draft_unreleased(self):
        entry = self._entry(status="draft", revision="B")
        self.assertEqual(dcl.use_verdict(entry, "C"), "unreleased")

    def test_obsolete_superseded(self):
        entry = self._entry(status="obsolete", revision="B")
        self.assertEqual(dcl.use_verdict(entry, "C"), "superseded")

    def test_invalid_entry_raises(self):
        with self.assertRaises(ValueError):
            dcl.use_verdict(self._entry(doc_number=""), "C")

    def test_incomparable_revision_raises(self):
        entry = self._entry(revision="A")
        with self.assertRaises(ValueError):
            dcl.use_verdict(entry, "3")


class MasterListTest(unittest.TestCase):
    LIST = [
        {
            "doc_number": "OP-1042",
            "title": "final assembly work instruction",
            "revision": "B",
            "issue_date": "2025-01-10",
            "status": "obsolete",
            "author": "jane",
            "approver": "omar",
        },
        {
            "doc_number": "OP-1042",
            "title": "final assembly work instruction",
            "revision": "C",
            "issue_date": "2026-06-01",
            "status": "issued",
            "author": "jane",
            "approver": "omar",
        },
        {
            "doc_number": "OP-2011",
            "title": "cable routing drawing",
            "revision": "D",
            "issue_date": "2026-03-15",
            "status": "issued",
            "author": "liam",
            "approver": "omar",
        },
    ]

    def test_current_copy_in_use(self):
        self.assertEqual(dcl.master_list_check(self.LIST, "OP-1042", "C"), "current")

    def test_obsolete_copy_in_use(self):
        self.assertEqual(dcl.master_list_check(self.LIST, "OP-1042", "B"), "superseded")

    def test_unlisted_revision(self):
        self.assertEqual(dcl.master_list_check(self.LIST, "OP-9999", "A"), "unlisted")
        self.assertEqual(dcl.master_list_check(self.LIST, "OP-1042", "E"), "unlisted")

    def test_current_revision_of_master_list(self):
        self.assertEqual(dcl.current_revision(self.LIST, "OP-1042"), "C")
        self.assertEqual(dcl.current_revision(self.LIST, "OP-2011"), "D")

    def test_current_revision_requires_issued_entry(self):
        """A document whose only entries are draft or obsolete has no
        current revision; current_revision returns None."""
        lst = [
            dict(self.LIST[0]),
            {
                "doc_number": "OP-1042",
                "title": "final assembly work instruction",
                "revision": "D",
                "issue_date": "2026-07-01",
                "status": "draft",
                "author": "jane",
                "approver": "",
            },
        ]
        self.assertIsNone(dcl.current_revision(lst, "OP-1042"))

    def test_unlisted_current_revision_is_none(self):
        self.assertIsNone(dcl.current_revision(self.LIST, "OP-9999"))

    def test_non_list_raises(self):
        with self.assertRaises(ValueError):
            dcl.master_list_check("OP-1042", "OP-1042", "C")
        with self.assertRaises(ValueError):
            dcl.current_revision({}, "OP-1042")


class ObsoleteActionTest(unittest.TestCase):
    def test_disposition_fields(self):
        entry = {
            "doc_number": "OP-1042",
            "title": "final assembly work instruction",
            "revision": "B",
            "issue_date": "2025-01-10",
            "status": "obsolete",
            "author": "jane",
            "approver": "omar",
        }
        result = dcl.obsolete_action(entry)
        self.assertEqual(result["doc_number"], "OP-1042")
        self.assertEqual(result["revision"], "B")
        self.assertEqual(result["status"], "obsolete")
        self.assertEqual(result["action"], "remove-from-active-use")
        self.assertEqual(result["retain"], "master-list-history")

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            dcl.obsolete_action("OP-1042")


class InvariantTest(unittest.TestCase):
    def test_obsolete_never_current(self):
        """Physically meaningful invariant: an obsolete revision is
        never a current-use verdict; it is superseded by design."""
        entry = {
            "doc_number": "OP-1042",
            "title": "x",
            "revision": "B",
            "issue_date": "2025-01-10",
            "status": "obsolete",
            "author": "jane",
            "approver": "omar",
        }
        for rev in ("B", "C", "Z"):
            verdict = dcl.use_verdict(entry, rev)
            self.assertNotEqual(verdict, "current", rev)

    def test_issued_current_revision_matches_master_list(self):
        """The current revision of the master list is exactly the
        revision that yields a current verdict for the doc number."""
        entries = [
            {
                "doc_number": "OP-1042",
                "title": "final assembly work instruction",
                "revision": "B",
                "issue_date": "2025-01-10",
                "status": "obsolete",
                "author": "jane",
                "approver": "omar",
            },
            {
                "doc_number": "OP-1042",
                "title": "final assembly work instruction",
                "revision": "C",
                "issue_date": "2026-06-01",
                "status": "issued",
                "author": "jane",
                "approver": "omar",
            },
        ]
        self.assertEqual(dcl.current_revision(entries, "OP-1042"), "C")
        self.assertEqual(dcl.master_list_check(entries, "OP-1042", "C"), "current")


if __name__ == "__main__":
    unittest.main(verbosity=2)
