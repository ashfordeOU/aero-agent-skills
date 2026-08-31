#!/usr/bin/env python3
"""Gate 3 contract test: AS9100 aerospace quality management.

Exercises scripts/quality_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — an audit focus area maps to
the aerospace clauses of AS9100 (operational risk, configuration
management, product safety, counterfeit prevention, external providers,
special processes); each clause carries the minimum evidence artifacts
for an audit; a corrective action closes only when containment, root
cause, and corrective action are all recorded; unknown inputs raise
ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import quality_logic as ql  # noqa: E402


class ClauseScopeTest(unittest.TestCase):
    def test_focus_maps_to_aerospace_clause(self):
        cases = [
            ("operational-risk", ("8.1.1", "operational risk")),
            ("configuration-management", ("8.1.2", "configuration management")),
            ("product-safety", ("8.1.3", "product safety")),
            ("counterfeit-prevention", ("8.1.4", "counterfeit prevention")),
            ("external-provider", ("8.4.1", "external providers")),
            ("special-process", ("8.5.1.3", "special processes")),
        ]
        for focus, expected in cases:
            with self.subTest(focus=focus):
                self.assertEqual(ql.scope_clause(focus), expected)

    def test_unknown_focus_raises(self):
        with self.assertRaises(ValueError):
            ql.scope_clause("marketing")


class EvidenceTest(unittest.TestCase):
    def test_every_clause_has_evidence_artifacts(self):
        for focus in (
            "operational-risk",
            "configuration-management",
            "product-safety",
            "counterfeit-prevention",
            "external-provider",
            "special-process",
        ):
            with self.subTest(focus=focus):
                self.assertGreaterEqual(len(ql.audit_evidence_required(focus)), 1)

    def test_counterfeit_evidence_is_specific(self):
        evidence = ql.audit_evidence_required("counterfeit-prevention")
        self.assertTrue(any("counterfeit" in e.lower() for e in evidence))


class CorrectiveActionTest(unittest.TestCase):
    def test_complete_record_closes(self):
        self.assertTrue(
            ql.corrective_action_closure(
                nonconformance="damaged part received",
                containment="stock quarantine",
                root_cause="handling procedure gap",
                corrective_action="revise handling procedure",
            )
        )

    def test_missing_root_cause_stays_open(self):
        self.assertFalse(
            ql.corrective_action_closure(
                nonconformance="damaged part received",
                containment="stock quarantine",
                root_cause="",
                corrective_action="revise handling procedure",
            )
        )

    def test_missing_containment_stays_open(self):
        self.assertFalse(
            ql.corrective_action_closure(
                nonconformance="damaged part received",
                containment="",
                root_cause="handling procedure gap",
                corrective_action="revise handling procedure",
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
