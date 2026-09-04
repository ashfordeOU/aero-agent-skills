#!/usr/bin/env python3
"""Gate 3 contract test: DO-254 verification.

Exercises scripts/do254_verification_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - complex AEH is verified
by test/analysis/review and simple AEH by reduced verification
(review); independent verification is expected at levels A/B;
requirements-based test coverage must meet the level ratio (0.98 for
A/B, 0.95 for C/D); hardware/software integration evidence is a
boolean; verification is complete only when every required method is
used; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import do254_verification_logic as vl  # noqa: E402


class MethodSetTest(unittest.TestCase):
    def test_complex_aeh_uses_full_method_set(self):
        for hdal in ("A", "B", "C", "D"):
            with self.subTest(hdal=hdal):
                self.assertEqual(
                    vl.verification_methods_for("complex", hdal),
                    {"test", "analysis", "review"},
                )

    def test_simple_aeh_uses_reduced_method_set(self):
        for hdal in ("A", "B", "C", "D"):
            with self.subTest(hdal=hdal):
                self.assertEqual(vl.verification_methods_for("simple", hdal), {"review"})

    def test_unknown_aeh_class_raises(self):
        with self.assertRaises(ValueError):
            vl.verification_methods_for("medium", "A")

    def test_unknown_hdal_raises(self):
        with self.assertRaises(ValueError):
            vl.verification_methods_for("complex", "E")


class IndependenceTest(unittest.TestCase):
    def test_independent_verification_expected_at_a_and_b(self):
        for hdal in ("A", "B"):
            with self.subTest(hdal=hdal):
                self.assertTrue(vl.independence_required(hdal))

    def test_no_independence_requirement_at_c_and_d(self):
        for hdal in ("C", "D"):
            with self.subTest(hdal=hdal):
                self.assertFalse(vl.independence_required(hdal))


class CoverageTest(unittest.TestCase):
    def test_ratio_0_98_passes_at_level_a(self):
        self.assertTrue(
            vl.requirements_based_coverage_ok(98, 100, "A", min_ratio=0.98)
        )

    def test_ratio_0_97_fails_at_level_a(self):
        self.assertFalse(
            vl.requirements_based_coverage_ok(97, 100, "A", min_ratio=0.98)
        )

    def test_default_ratio_0_95_boundary(self):
        self.assertTrue(vl.requirements_based_coverage_ok(95, 100, "D"))
        self.assertFalse(vl.requirements_based_coverage_ok(94, 100, "D"))

    def test_full_coverage_passes_at_level_b(self):
        self.assertTrue(
            vl.requirements_based_coverage_ok(100, 100, "B", min_ratio=0.98)
        )

    def test_tested_exceeds_total_raises(self):
        with self.assertRaises(ValueError):
            vl.requirements_based_coverage_ok(101, 100, "A")

    def test_zero_total_raises(self):
        with self.assertRaises(ValueError):
            vl.requirements_based_coverage_ok(0, 0, "A")

    def test_invalid_hdal_raises(self):
        with self.assertRaises(ValueError):
            vl.requirements_based_coverage_ok(50, 100, "E")


class IntegrationTest(unittest.TestCase):
    def test_evidence_present(self):
        self.assertTrue(vl.hwsw_integration_evidence(True))

    def test_evidence_absent(self):
        self.assertFalse(vl.hwsw_integration_evidence(False))


class CompletenessTest(unittest.TestCase):
    def test_all_required_methods_used(self):
        self.assertTrue(
            vl.verification_complete(
                {"test", "analysis", "review"}, {"review", "test"}
            )
        )

    def test_missing_method_fails(self):
        self.assertFalse(
            vl.verification_complete({"analysis"}, {"test", "analysis", "review"})
        )

    def test_extra_methods_do_not_fail(self):
        self.assertTrue(
            vl.verification_complete(
                {"test", "analysis", "review", "simulation"}, {"review"}
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
