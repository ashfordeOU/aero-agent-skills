#!/usr/bin/env python3
"""Gate 3 contract test: DO-178C requirement-to-code traceability completeness.

Exercises scripts/development_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - traceability closure per software
level: missing links fail at every level, derived items must be identified,
and levels A/B require independent review of the trace data.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import development_logic as dev  # noqa: E402


class TraceAnalysisTest(unittest.TestCase):
    def _complete(self):
        # 2 HLR -> 3 LLR -> 4 code items, fully linked.
        return dev.analyze_traceability(
            high_level=["HLR-1", "HLR-2"],
            low_level=["LLR-1", "LLR-2", "LLR-3"],
            code=["C-1", "C-2", "C-3", "C-4"],
            links=[
                ("HLR-1", "LLR-1"),
                ("HLR-1", "LLR-2"),
                ("HLR-2", "LLR-3"),
                ("LLR-1", "C-1"),
                ("LLR-2", "C-2"),
                ("LLR-3", "C-3"),
                ("LLR-3", "C-4"),
            ],
            derived=[],
        )

    def test_complete_trace_has_no_unlinked(self):
        a = self._complete()
        self.assertEqual(a["hlr_unlinked"], set())
        self.assertEqual(a["llr_unlinked"], set())
        self.assertEqual(a["code_unlinked"], set())

    def test_completeness_ratio(self):
        a = self._complete()
        self.assertEqual(a["completeness"], 1.0)

    def test_missing_llr_link_reduces_completeness(self):
        a = dev.analyze_traceability(
            high_level=["HLR-1"],
            low_level=["LLR-1", "LLR-2"],
            code=["C-1", "C-2"],
            links=[("HLR-1", "LLR-1"), ("LLR-1", "C-1")],
            derived=[],
        )
        # LLR-2 and C-2 are unlinked: 3 of 5 artifacts linked.
        self.assertEqual(a["completeness"], 3 / 5)

    def test_orphan_code_flagged_unless_derived(self):
        a = dev.analyze_traceability(
            high_level=["HLR-1"],
            low_level=["LLR-1"],
            code=["C-1", "C-orphan"],
            links=[("HLR-1", "LLR-1"), ("LLR-1", "C-1")],
            derived=[],
        )
        self.assertIn("C-orphan", a["code_unlinked"])
        b = dev.analyze_traceability(
            high_level=["HLR-1"],
            low_level=["LLR-1"],
            code=["C-1", "C-derived"],
            links=[("HLR-1", "LLR-1"), ("LLR-1", "C-1")],
            derived=["C-derived"],
        )
        self.assertNotIn("C-derived", b["code_unlinked"])


class TraceGateTest(unittest.TestCase):
    def _minimal(self):
        return dev.analyze_traceability(
            high_level=["HLR-1"],
            low_level=["LLR-1"],
            code=["C-1"],
            links=[("HLR-1", "LLR-1"), ("LLR-1", "C-1")],
            derived=[],
        )

    def test_complete_trace_passes_every_level(self):
        a = self._minimal()
        for dal in "ABCDE":
            with self.subTest(dal=dal):
                ok, _ = dev.trace_gate(a, dal)
                self.assertTrue(ok)

    def test_missing_link_fails_every_level(self):
        a = dev.analyze_traceability(
            high_level=["HLR-1"],
            low_level=["LLR-1", "LLR-2"],
            code=["C-1"],
            links=[("HLR-1", "LLR-1"), ("LLR-1", "C-1")],
            derived=[],
        )
        for dal in "ABCDE":
            with self.subTest(dal=dal):
                ok, reason = dev.trace_gate(a, dal)
                self.assertFalse(ok)
                self.assertIn("unlinked", reason)

    def test_derived_items_pass_gate(self):
        a = dev.analyze_traceability(
            high_level=["HLR-1"],
            low_level=["LLR-1", "LLR-D"],
            code=["C-1", "C-2"],
            links=[("HLR-1", "LLR-1"), ("LLR-1", "C-1"), ("LLR-D", "C-2")],
            derived=["LLR-D"],
        )
        ok, _ = dev.trace_gate(a, "A")
        self.assertTrue(ok)

    def test_no_links_at_all_fails(self):
        a = dev.analyze_traceability(
            high_level=["HLR-1"],
            low_level=["LLR-1"],
            code=["C-1"],
            links=[],
            derived=[],
        )
        ok, _ = dev.trace_gate(a, "C")
        self.assertFalse(ok)

    def test_independence_required_only_ab(self):
        for dal, expected in [
            ("A", True), ("B", True), ("C", False), ("D", False), ("E", False),
        ]:
            with self.subTest(dal=dal):
                self.assertEqual(dev.independence_required(dal), expected)

    def test_invalid_dal_raises(self):
        with self.assertRaises(ValueError):
            dev.independence_required("X")


if __name__ == "__main__":
    unittest.main(verbosity=2)
