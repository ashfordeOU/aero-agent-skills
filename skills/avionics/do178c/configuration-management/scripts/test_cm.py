#!/usr/bin/env python3
"""Gate 3 contract test: DO-178C configuration management change control.

Exercises scripts/cm_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - baselined items are controlled,
changes to baselined data are reviewed at every level with independent
approval at A/B, and release requires closed problem reports, a current
baseline, and an archive/recovery capability.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cm_logic as cm  # noqa: E402


class BaselineTest(unittest.TestCase):
    def test_baselined_membership(self):
        baselines = [{"C-1", "C-2"}]
        self.assertTrue(cm.is_baselined("C-1", baselines))
        self.assertFalse(cm.is_baselined("C-9", baselines))

    def test_empty_baselines(self):
        self.assertFalse(cm.is_baselined("C-1", []))


class ChangeControlTest(unittest.TestCase):
    def test_baselined_change_reviewed_every_level(self):
        for dal in "ABCDE":
            with self.subTest(dal=dal):
                self.assertTrue(cm.change_review_required(dal, baselined=True))

    def test_draft_change_needs_no_formal_review(self):
        self.assertFalse(cm.change_review_required("C", baselined=False))

    def test_independent_approval_only_ab(self):
        for dal, expected in [
            ("A", True), ("B", True), ("C", False), ("D", False), ("E", False),
        ]:
            with self.subTest(dal=dal):
                self.assertEqual(cm.change_independence_required(dal), expected)


class ReleaseGateTest(unittest.TestCase):
    def test_release_blocked_by_open_prs(self):
        ok, reason = cm.release_gate(
            open_prs=1, closed_prs=2, baseline_exists=True, archive_exists=True
        )
        self.assertFalse(ok)
        self.assertIn("open problem report", reason)

    def test_release_requires_baseline_and_archive(self):
        self.assertFalse(cm.release_gate(0, 3, False, True)[0])
        self.assertFalse(cm.release_gate(0, 3, True, False)[0])

    def test_release_clear(self):
        ok, _ = cm.release_gate(0, 3, True, True)
        self.assertTrue(ok)

    def test_unreviewed_changes_block_release(self):
        ok, _ = cm.release_gate(0, 3, True, True, unreviewed_changes=2)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main(verbosity=2)
