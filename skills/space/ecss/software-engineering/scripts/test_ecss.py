#!/usr/bin/env python3
"""Gate 3 contract test: ECSS space software engineering.

Exercises scripts/ecss_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — ECSS-E-ST-40C classifies
space software criticality A-D from failure consequence (loss of life
or total loss of mission = A, major mission degradation = B, minor
degradation = C, negligible = D); assurance rigor scales with the
category; lifecycle phases advance only when the phase record exists;
heritage reuse demands a heritage assessment with full verification
evidence at the highest categories. Unknown inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ecss_logic as ec  # noqa: E402


class CategoryTest(unittest.TestCase):
    def test_consequence_maps_to_category(self):
        cases = [
            ("loss-of-life", "A"),
            ("loss-of-mission", "A"),
            ("major-mission-degradation", "B"),
            ("minor-mission-degradation", "C"),
            ("negligible", "D"),
        ]
        for consequence, expected in cases:
            with self.subTest(consequence=consequence):
                self.assertEqual(ec.criticality_category(consequence), expected)

    def test_unknown_consequence_raises(self):
        with self.assertRaises(ValueError):
            ec.criticality_category("annoying")


class RigorTest(unittest.TestCase):
    def test_rigor_scales_with_category(self):
        ranks = {cat: ec.rigor_rank(ec.assurance_rigor(cat)) for cat in "ABCD"}
        self.assertGreater(ranks["A"], ranks["B"])
        self.assertGreater(ranks["B"], ranks["C"])
        self.assertGreater(ranks["C"], ranks["D"])

    def test_invalid_category_raises(self):
        with self.assertRaises(ValueError):
            ec.assurance_rigor("E")


class LifecycleGateTest(unittest.TestCase):
    def test_phase_advances_with_record(self):
        self.assertTrue(
            ec.phase_gate("software-requirements", ["requirements-review-record"])
        )

    def test_phase_blocked_without_record(self):
        self.assertFalse(
            ec.phase_gate("software-requirements", ["draft-notes"])
        )

    def test_unknown_phase_raises(self):
        with self.assertRaises(ValueError):
            ec.phase_gate("brainstorming", [])


class HeritageTest(unittest.TestCase):
    def test_high_category_demands_full_evidence(self):
        evidence = ec.heritage_evidence_required("A")
        self.assertIn("heritage-assessment", evidence)
        self.assertIn("full-verification-evidence", evidence)

    def test_low_category_keeps_baseline_assessment(self):
        evidence = ec.heritage_evidence_required("D")
        self.assertIn("heritage-assessment", evidence)
        self.assertNotIn("full-verification-evidence", evidence)


if __name__ == "__main__":
    unittest.main(verbosity=2)
