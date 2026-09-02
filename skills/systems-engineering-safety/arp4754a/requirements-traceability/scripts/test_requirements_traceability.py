#!/usr/bin/env python3
"""Gate 3 contract test: ARP4754A requirements traceability.

Exercises scripts/requirements_traceability_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - closure requires
bidirectional tracing through srats/hlr/llr/code/test with every traced
pair verified; trace_gaps focuses one level; derived requirements are
flagged; the verified-closure ratio is 0..1; invalid inputs raise
ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requirements_traceability_logic as rtl  # noqa: E402

COMPLETE_LINKS = [
    {"from": "SRATS-1", "to": "HLR-1", "verified": True},
    {"from": "HLR-1", "to": "LLR-1", "verified": True},
    {"from": "LLR-1", "to": "CODE-1", "verified": True},
    {"from": "LLR-1", "to": "TEST-1", "verified": True},
]

HLR_TO_LLR_GAP = [
    {"from": "SRATS-1", "to": "HLR-1", "verified": True},
]

UNVERIFIED_LINKS = list(COMPLETE_LINKS)
UNVERIFIED_LINKS[-1] = {"from": "LLR-1", "to": "TEST-1", "verified": False}


class ClosureStatusTest(unittest.TestCase):
    def test_complete_bidirectional_closure_is_closed(self):
        status, gaps = rtl.closure_status(COMPLETE_LINKS)
        self.assertEqual(status, "closed")
        self.assertEqual(gaps, [])

    def test_missing_hlr_to_llr_is_open(self):
        status, gaps = rtl.closure_status(HLR_TO_LLR_GAP)
        self.assertEqual(status, "open")
        self.assertIn("hlr HLR-1 has no trace to any llr", gaps)

    def test_srats_without_hlr_trace_is_open(self):
        links = [
            {"from": "SRATS-1", "to": "HLR-1", "verified": True},
            {"from": "HLR-1", "to": "SRATS-2", "verified": True},
        ]
        status, gaps = rtl.closure_status(links)
        self.assertEqual(status, "open")
        self.assertIn("srats SRATS-2 has no trace to any hlr", gaps)

    def test_unverified_link_is_open(self):
        status, gaps = rtl.closure_status(UNVERIFIED_LINKS)
        self.assertEqual(status, "open")
        self.assertIn("unverified trace LLR-1 -> TEST-1", gaps)

    def test_invalid_link_missing_key_raises(self):
        links = [{"from": "SRATS-1", "to": "HLR-1"}]
        with self.assertRaises(ValueError):
            rtl.closure_status(links)

    def test_link_with_unknown_level_id_raises(self):
        links = [{"from": "REQ-1", "to": "HLR-1", "verified": True}]
        with self.assertRaises(ValueError):
            rtl.closure_status(links)


class TraceGapsTest(unittest.TestCase):
    def test_focuses_on_requested_level(self):
        self.assertEqual(
            rtl.trace_gaps(HLR_TO_LLR_GAP, "hlr"),
            ["hlr HLR-1 has no trace to any llr"],
        )
        self.assertEqual(rtl.trace_gaps(HLR_TO_LLR_GAP, "srats"), [])

    def test_includes_unverified_traces_touching_level(self):
        self.assertEqual(
            rtl.trace_gaps(UNVERIFIED_LINKS, "test"),
            ["unverified trace LLR-1 -> TEST-1"],
        )
        self.assertEqual(rtl.trace_gaps(UNVERIFIED_LINKS, "code"), [])

    def test_unknown_level_raises(self):
        with self.assertRaises(ValueError):
            rtl.trace_gaps(COMPLETE_LINKS, "bogus")


class DerivedFlagTest(unittest.TestCase):
    def test_derived_ids_flagged(self):
        self.assertTrue(rtl.derived_requirement_flag("HLR-4-derived"))
        self.assertTrue(rtl.derived_requirement_flag("HLR-4-DERIVED"))
        self.assertTrue(rtl.derived_requirement_flag("derived-LLR-2"))

    def test_non_derived_ids_not_flagged(self):
        self.assertFalse(rtl.derived_requirement_flag("LLR-9"))
        self.assertFalse(rtl.derived_requirement_flag("SRATS-1"))


class ClosureRatioTest(unittest.TestCase):
    def test_known_ratio(self):
        links = list(COMPLETE_LINKS)
        links[-1] = {"from": "LLR-1", "to": "TEST-1", "verified": False}
        self.assertAlmostEqual(rtl.closure_ratio(links), 0.75)

    def test_all_verified_ratio_is_one(self):
        self.assertAlmostEqual(rtl.closure_ratio(COMPLETE_LINKS), 1.0)

    def test_empty_links_raises(self):
        with self.assertRaises(ValueError):
            rtl.closure_ratio([])


if __name__ == "__main__":
    unittest.main(verbosity=2)
