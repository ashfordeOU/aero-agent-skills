#!/usr/bin/env python3
"""Gate 3 contract test: DO-254 hardware requirements capture.

Exercises scripts/requirements_capture_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — requirement-characteristic
checks (vague terms, identifiers, traceability), derived vs allocated
classification, and capture-readiness accounting; invalid inputs raise
ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requirements_capture_logic as rc  # noqa: E402


class RequirementIssueTest(unittest.TestCase):
    def test_clean_requirement_no_issues(self):
        req = {"id": "HR-001", "text": "The monitor shall assert fail-safe "
               "when input voltage exceeds 28.5 V.", "traceable": True}
        self.assertEqual(rc.req_issues(req), [])

    def test_vague_term_flagged(self):
        req = {"id": "HR-002", "text": "The unit shall operate at a suitable "
               "temperature.", "traceable": True}
        issues = rc.req_issues(req)
        self.assertIn("vague", issues)

    def test_missing_id_and_trace_flagged(self):
        req = {"id": "", "text": "The unit shall reset approximately every "
               "hour.", "traceable": False}
        issues = rc.req_issues(req)
        self.assertIn("missing-id", issues)
        self.assertIn("vague", issues)
        self.assertIn("not-traceable", issues)

    def test_empty_text_flagged(self):
        req = {"id": "HR-003", "text": "", "traceable": True}
        issues = rc.req_issues(req)
        self.assertIn("empty-text", issues)

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            rc.req_issues(["not", "a", "dict"])


class DerivedClassificationTest(unittest.TestCase):
    def test_no_higher_level_source_derived(self):
        self.assertEqual(rc.classify_derived(False), "derived")

    def test_higher_level_source_allocated(self):
        self.assertEqual(rc.classify_derived(True), "allocated")


class CaptureReadinessTest(unittest.TestCase):
    def test_high_fraction_ready(self):
        reqs = [
            {"id": "R1", "text": "The unit shall reset within 10 ms.",
             "traceable": True},
            {"id": "R2", "text": "The unit shall store 1024 samples.",
             "traceable": True},
            {"id": "R3", "text": "The unit shall log events.", "traceable": True},
            {"id": "R4", "text": "The unit shall keep adequate records.",
             "traceable": True},
        ]
        ready, score = rc.capture_readiness(reqs)
        self.assertTrue(ready)
        self.assertAlmostEqual(score, 0.75)

    def test_low_fraction_not_ready(self):
        reqs = [
            {"id": "R1", "text": "The unit shall reset within 10 ms.",
             "traceable": True},
            {"id": "R2", "text": "The unit shall be adequate.",
             "traceable": False},
        ]
        ready, score = rc.capture_readiness(reqs)
        self.assertFalse(ready)
        self.assertAlmostEqual(score, 0.5)

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            rc.capture_readiness([])


if __name__ == "__main__":
    unittest.main(verbosity=2)
