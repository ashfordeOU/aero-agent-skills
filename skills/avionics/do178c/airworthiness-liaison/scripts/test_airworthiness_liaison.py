#!/usr/bin/env python3
"""Gate 3 contract test: DO-178C airworthiness / certification liaison.

Exercises scripts/airworthiness_liaison_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — certification-basis coverage
accounting, SOI (stage of involvement) audit readiness with level-dependent
thresholds, and open-item liaison action flags; invalid inputs raise
ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import airworthiness_liaison_logic as al  # noqa: E402


class CertBasisCoverageTest(unittest.TestCase):
    def test_partial_coverage_reports_missing(self):
        items = [
            ("FAR-25.1309", True),
            ("FAR-25.671", True),
            ("CS-25.1309", False),
            ("AC 20-174", True),
        ]
        covered, missing, coverage = al.cert_basis_coverage(items)
        self.assertEqual(covered, 3)
        self.assertEqual(missing, ["CS-25.1309"])
        self.assertAlmostEqual(coverage, 0.75)

    def test_full_coverage(self):
        covered, missing, coverage = al.cert_basis_coverage([("A", True), ("B", True)])
        self.assertEqual(covered, 2)
        self.assertEqual(missing, [])
        self.assertAlmostEqual(coverage, 1.0)

    def test_empty_basis_raises(self):
        with self.assertRaises(ValueError):
            al.cert_basis_coverage([])

    def test_malformed_item_raises(self):
        with self.assertRaises(ValueError):
            al.cert_basis_coverage([("A", True), ("B",)])


class SoiReadinessTest(unittest.TestCase):
    def test_level_a_full_evidence_ready(self):
        evidence = {"psac": True, "sdp": True, "svp": True, "trace": True}
        ready, score = al.soi_readiness("A", evidence)
        self.assertTrue(ready)
        self.assertAlmostEqual(score, 1.0)

    def test_level_a_any_gap_not_ready(self):
        evidence = {"psac": True, "sdp": False, "svp": True, "trace": True}
        ready, _ = al.soi_readiness("A", evidence)
        self.assertFalse(ready)

    def test_level_c_high_score_ready(self):
        evidence = {"a": True, "b": True, "c": True, "d": False, "e": True,
                    "f": True, "g": True, "h": True, "i": True, "j": True}
        ready, score = al.soi_readiness("C", evidence)
        self.assertTrue(ready)
        self.assertAlmostEqual(score, 0.9)

    def test_level_c_low_score_not_ready(self):
        evidence = {"a": True, "b": True, "c": False, "d": False, "e": True,
                    "f": True, "g": True, "h": True, "i": True, "j": True}
        ready, _ = al.soi_readiness("C", evidence)
        self.assertFalse(ready)

    def test_invalid_level_raises(self):
        with self.assertRaises(ValueError):
            al.soi_readiness("Z", {"a": True})

    def test_empty_evidence_not_ready(self):
        ready, score = al.soi_readiness("D", {})
        self.assertFalse(ready)
        self.assertAlmostEqual(score, 0.0)


class LiaisonActionTest(unittest.TestCase):
    def test_no_open_items_ok(self):
        self.assertEqual(al.liaison_action(0), "ok")

    def test_open_items_action_required(self):
        self.assertEqual(al.liaison_action(3), "action required")

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            al.liaison_action(-1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
