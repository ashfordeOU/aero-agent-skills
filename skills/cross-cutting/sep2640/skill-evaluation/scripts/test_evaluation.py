#!/usr/bin/env python3
"""Gate 3 contract test: SEP-2640-style skill evaluation.

Exercises scripts/evaluation_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a delivered skill is
accepted when its conformance checks all pass (frontmatter present,
kebab-case name matching the folder, description with a Trigger
clause, Apache-2.0 license, standards referenced, SKILL.md at the
package root), its contract test exercises the core logic, its
weighted quality score clears the accept threshold, and coverage of
tested behavior is reported. Unknown or invalid inputs raise
ValueError.

Analytic hand-computed expectations:
- weighted_score({"offline": 1.0, "deterministic": 0.5,
  "network_free": 0.0}, {"offline": 0.5, "deterministic": 0.25,
  "network_free": 0.25}) == 1.0*0.5 + 0.5*0.25 + 0.0*0.25 == 0.625
- coverage_ratio(7, 10) == 0.7; coverage_ratio(3, 4) == 0.75
- acceptance_verdict(0.9, (0.85, 0.6)) == "accept"
- acceptance_verdict(0.7, (0.85, 0.6)) == "rework"
- acceptance_verdict(0.5, (0.85, 0.6)) == "reject"
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import evaluation_logic as el  # noqa: E402

GOOD_PACKAGE = {
    "folder_name": "analysis",
    "name": "analysis",
    "description": "Use when analyzing. Trigger: analysis, metrics.",
    "license": "Apache-2.0",
    "standards": ["sep-2640"],
    "files": ["SKILL.md", "scripts/tool.py"],
}


class ConformanceTest(unittest.TestCase):
    def test_all_checks_pass_for_good_package(self):
        checks = el.run_conformance_checks(GOOD_PACKAGE)
        self.assertTrue(all(checks.values()))
        verdict = el.conformance_verdict(checks)
        self.assertTrue(verdict["conformant"])
        self.assertEqual(verdict["failed"], [])

    def test_name_mismatch_fails_package(self):
        pkg = dict(GOOD_PACKAGE, name="compute")
        checks = el.run_conformance_checks(pkg)
        self.assertFalse(checks["name_matches_folder"])
        verdict = el.conformance_verdict(checks)
        self.assertFalse(verdict["conformant"])
        self.assertIn("name_matches_folder", verdict["failed"])

    def test_missing_trigger_fails(self):
        pkg = dict(GOOD_PACKAGE, description="Use when analyzing.")
        checks = el.run_conformance_checks(pkg)
        self.assertFalse(checks["description_has_trigger"])

    def test_wrong_license_fails(self):
        pkg = dict(GOOD_PACKAGE, license="MIT")
        checks = el.run_conformance_checks(pkg)
        self.assertFalse(checks["license_apache"])

    def test_missing_skill_md_fails(self):
        pkg = dict(GOOD_PACKAGE, files=["scripts/tool.py"])
        checks = el.run_conformance_checks(pkg)
        self.assertFalse(checks["skill_md_present"])

    def test_non_kebab_name_fails(self):
        pkg = dict(GOOD_PACKAGE, name="Analysis Tool")
        checks = el.run_conformance_checks(pkg)
        self.assertFalse(checks["name_kebab_case"])

    def test_verdict_rejects_non_bool_check(self):
        with self.assertRaises(ValueError):
            el.conformance_verdict({"a": 1})

    def test_verdict_rejects_empty_checks(self):
        with self.assertRaises(ValueError):
            el.conformance_verdict({})


class ScoringTest(unittest.TestCase):
    def test_weighted_score_analytic(self):
        scores = {"offline": 1.0, "deterministic": 0.5, "network_free": 0.0}
        weights = {"offline": 0.5, "deterministic": 0.25, "network_free": 0.25}
        self.assertAlmostEqual(el.weighted_score(scores, weights), 0.625)

    def test_weighted_score_full_marks(self):
        scores = {"a": 1.0, "b": 1.0}
        weights = {"a": 0.5, "b": 0.5}
        self.assertAlmostEqual(el.weighted_score(scores, weights), 1.0)

    def test_weights_must_sum_to_one(self):
        with self.assertRaises(ValueError):
            el.weighted_score({"a": 1.0}, {"a": 0.5})

    def test_key_mismatch_raises(self):
        with self.assertRaises(ValueError):
            el.weighted_score({"a": 1.0}, {"b": 1.0})

    def test_stdlib_only_scores(self):
        self.assertEqual(el.stdlib_only(["math", "re"]), 1.0)
        self.assertEqual(el.stdlib_only(["numpy"]), 0.0)

    def test_contract_score(self):
        self.assertEqual(el.contract_score(True), 1.0)
        self.assertEqual(el.contract_score(False), 0.0)
        with self.assertRaises(ValueError):
            el.contract_score("yes")


class VerdictTest(unittest.TestCase):
    def test_accept_above_threshold(self):
        self.assertEqual(el.acceptance_verdict(0.9, (0.85, 0.6)), "accept")

    def test_rework_between_thresholds(self):
        self.assertEqual(el.acceptance_verdict(0.7, (0.85, 0.6)), "rework")

    def test_reject_below_rework_threshold(self):
        self.assertEqual(el.acceptance_verdict(0.5, (0.85, 0.6)), "reject")

    def test_boundary_equal_to_accept_is_accept(self):
        self.assertEqual(el.acceptance_verdict(0.85, (0.85, 0.6)), "accept")

    def test_boundary_equal_to_rework_is_rework(self):
        self.assertEqual(el.acceptance_verdict(0.6, (0.85, 0.6)), "rework")

    def test_inverted_thresholds_raise(self):
        with self.assertRaises(ValueError):
            el.acceptance_verdict(0.9, (0.6, 0.85))

    def test_score_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            el.acceptance_verdict(1.2, (0.85, 0.6))


class CoverageTest(unittest.TestCase):
    def test_coverage_7_of_10(self):
        self.assertEqual(el.coverage_ratio(7, 10), 0.7)

    def test_coverage_3_of_4(self):
        self.assertEqual(el.coverage_ratio(3, 4), 0.75)

    def test_full_coverage(self):
        self.assertEqual(el.coverage_ratio(6, 6), 1.0)

    def test_tested_exceeding_total_raises(self):
        with self.assertRaises(ValueError):
            el.coverage_ratio(5, 4)

    def test_zero_total_raises(self):
        with self.assertRaises(ValueError):
            el.coverage_ratio(0, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
