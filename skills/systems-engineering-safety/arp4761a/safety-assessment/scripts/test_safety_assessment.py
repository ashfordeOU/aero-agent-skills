#!/usr/bin/env python3
"""Gate 3 contract test: ARP4761A safety assessment process.

Exercises scripts/safety_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — failure-condition severity maps
to a development assurance level; the assessment phase tracks design
maturity (FHA before architecture, PSSA after architecture is proposed,
SSA after implementation); the analysis set scales with the level
(FTA/FMEA at all safety-significant levels, CCA for the highest); unknown
inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import safety_logic as saf  # noqa: E402


class SeverityTest(unittest.TestCase):
    def test_severity_maps_to_assurance_level(self):
        cases = [
            ("Catastrophic", "A"),
            ("Hazardous", "B"),
            ("Major", "C"),
            ("Minor", "D"),
            ("No safety effect", "E"),
        ]
        for severity, expected in cases:
            with self.subTest(severity=severity):
                self.assertEqual(saf.level_from_severity(severity), expected)

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            saf.level_from_severity("Inconvenient")


class PhaseTest(unittest.TestCase):
    def test_phase_tracks_design_maturity(self):
        cases = [
            ("concept", "FHA"),
            ("proposed-architecture", "PSSA"),
            ("implemented", "SSA"),
        ]
        for maturity, expected in cases:
            with self.subTest(maturity=maturity):
                self.assertEqual(saf.assessment_phase(maturity), expected)

    def test_unknown_maturity_raises(self):
        with self.assertRaises(ValueError):
            saf.assessment_phase("delivered")


class AnalysesTest(unittest.TestCase):
    def test_full_analysis_set_at_high_levels(self):
        for level in ("A", "B"):
            with self.subTest(level=level):
                analyses = saf.analyses_required(level)
                self.assertIn("FTA", analyses)
                self.assertIn("FMEA", analyses)
                self.assertIn("CCA", analyses)

    def test_cca_includes_all_three_elements(self):
        self.assertEqual(
            saf.cca_elements(),
            ("ZSA", "PRA", "CMA"),
        )

    def test_reduced_set_at_low_levels(self):
        analyses = saf.analyses_required("E")
        self.assertNotIn("CCA", analyses)

    def test_invalid_level_raises(self):
        with self.assertRaises(ValueError):
            saf.analyses_required("F")


if __name__ == "__main__":
    unittest.main(verbosity=2)
