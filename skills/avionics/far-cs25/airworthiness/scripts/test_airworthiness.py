#!/usr/bin/env python3
"""Gate 3 contract test: FAR-25 / CS-25 transport-category airworthiness.

Exercises scripts/airworthiness_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — the certification basis
resolves to FAR-25 for FAA transport-category programs and CS-25 for
EASA programs (out-of-scope categories raise); systems whose failure
conditions are catastrophic, hazardous, or major require the 25.1309
safety assessment; means of compliance are the standard demonstration
methods; the type-certification program follows an ordered step
sequence. Unknown inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import airworthiness_logic as aw  # noqa: E402


class CertificationBasisTest(unittest.TestCase):
    def test_faa_transport_resolves_to_far_25(self):
        self.assertEqual(
            aw.certification_basis("transport", "FAA"), ["far-25"]
        )

    def test_easa_transport_resolves_to_cs_25(self):
        self.assertEqual(
            aw.certification_basis("transport", "EASA"), ["cs-25"]
        )

    def test_out_of_scope_category_raises(self):
        with self.assertRaises(ValueError):
            aw.certification_basis("general-aviation", "FAA")

    def test_unknown_jurisdiction_raises(self):
        with self.assertRaises(ValueError):
            aw.certification_basis("transport", "ICAO")


class SafetyAssessmentTest(unittest.TestCase):
    def test_safety_significant_severities_require_assessment(self):
        for severity in ("Catastrophic", "Hazardous", "Major"):
            with self.subTest(severity=severity):
                self.assertTrue(aw.safety_assessment_required(severity))

    def test_low_severities_do_not_require_assessment(self):
        for severity in ("Minor", "No safety effect"):
            with self.subTest(severity=severity):
                self.assertFalse(aw.safety_assessment_required(severity))

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            aw.safety_assessment_required("Tolerable")


class MeansOfComplianceTest(unittest.TestCase):
    def test_standard_methods_available(self):
        methods = aw.moc_methods()
        self.assertIn("analysis", methods)
        self.assertIn("test", methods)
        self.assertIn("inspection", methods)

    def test_valid_method_recognized(self):
        self.assertTrue(aw.moc_is_valid("flight test"))

    def test_invalid_method_rejected(self):
        self.assertFalse(aw.moc_is_valid("wishing"))


class TypeCertificationStepsTest(unittest.TestCase):
    def test_program_follows_ordered_steps(self):
        steps = aw.type_certification_steps()
        self.assertEqual(steps[0], "application")
        self.assertEqual(steps[-1], "issue")
        self.assertEqual(len(steps), len(set(steps)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
