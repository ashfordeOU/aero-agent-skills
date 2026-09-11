#!/usr/bin/env python3
"""Stdlib unittest for e1012_rdm_see_logic — ECSS-E-ST-10-12C §5.1.3 SEE margin.
Run: python3 test_e1012_rdm_see.py
Must print OK. Offline, deterministic, no external dependencies.
"""

import math
import unittest

from e1012_rdm_see_logic import (
    DEFAULT_RDM_MIN,
    DESTRUCTIVE_EFFECTS,
    NON_DESTRUCTIVE_EFFECTS,
    SEEError,
    assess_all,
    assess_part,
    categorize_effect,
    check_see_compliance,
    compute_let_margin,
    compute_rate_margin,
    see_findings,
)


class TestCategorizeEffect(unittest.TestCase):
    def test_sel_is_destructive(self):
        self.assertEqual(categorize_effect("SEL"), "destructive")

    def test_seb_is_destructive(self):
        self.assertEqual(categorize_effect("SEB"), "destructive")

    def test_segr_is_destructive(self):
        self.assertEqual(categorize_effect("SEGR"), "destructive")

    def test_seu_is_non_destructive(self):
        self.assertEqual(categorize_effect("SEU"), "non_destructive")

    def test_sefi_is_non_destructive(self):
        self.assertEqual(categorize_effect("SEFI"), "non_destructive")

    def test_set_is_non_destructive(self):
        self.assertEqual(categorize_effect("SET"), "non_destructive")

    def test_lowercase_input_accepted(self):
        self.assertEqual(categorize_effect("sel"), "destructive")
        self.assertEqual(categorize_effect("seu"), "non_destructive")

    def test_mixed_case_input_accepted(self):
        self.assertEqual(categorize_effect("Seb"), "destructive")

    def test_unknown_effect_raises(self):
        with self.assertRaises(SEEError):
            categorize_effect("UNKNOWN")

    def test_empty_string_raises(self):
        with self.assertRaises(SEEError):
            categorize_effect("")

    def test_destructive_set_contents(self):
        self.assertIn("SEL", DESTRUCTIVE_EFFECTS)
        self.assertIn("SEB", DESTRUCTIVE_EFFECTS)
        self.assertIn("SEGR", DESTRUCTIVE_EFFECTS)

    def test_non_destructive_set_contents(self):
        self.assertIn("SEU", NON_DESTRUCTIVE_EFFECTS)
        self.assertIn("SEFI", NON_DESTRUCTIVE_EFFECTS)
        self.assertIn("SET", NON_DESTRUCTIVE_EFFECTS)


class TestComputeLetMargin(unittest.TestCase):
    def test_margin_above_rdm_passes_numerically(self):
        margin = compute_let_margin(40.0, 10.0)
        self.assertAlmostEqual(margin, 4.0)

    def test_margin_exactly_one(self):
        margin = compute_let_margin(10.0, 10.0)
        self.assertAlmostEqual(margin, 1.0)

    def test_margin_below_one_when_threshold_lower(self):
        margin = compute_let_margin(5.0, 10.0)
        self.assertAlmostEqual(margin, 0.5)

    def test_zero_threshold_raises(self):
        with self.assertRaises(SEEError):
            compute_let_margin(0.0, 10.0)

    def test_negative_threshold_raises(self):
        with self.assertRaises(SEEError):
            compute_let_margin(-5.0, 10.0)

    def test_zero_environment_raises(self):
        with self.assertRaises(SEEError):
            compute_let_margin(10.0, 0.0)

    def test_negative_environment_raises(self):
        with self.assertRaises(SEEError):
            compute_let_margin(10.0, -1.0)

    def test_large_margin_value(self):
        margin = compute_let_margin(100.0, 1.0)
        self.assertAlmostEqual(margin, 100.0)


class TestComputeRateMargin(unittest.TestCase):
    def test_passing_margin(self):
        # predicted=1, allowable=10, rdm=2 → margin=10/(1*2)=5.0
        margin = compute_rate_margin(1.0, 10.0, 2.0)
        self.assertAlmostEqual(margin, 5.0)

    def test_exact_unity_margin(self):
        # predicted=5, allowable=10, rdm=2 → margin=10/(5*2)=1.0
        margin = compute_rate_margin(5.0, 10.0, 2.0)
        self.assertAlmostEqual(margin, 1.0)

    def test_failing_margin_below_unity(self):
        # predicted=8, allowable=10, rdm=2 → margin=10/16=0.625
        margin = compute_rate_margin(8.0, 10.0, 2.0)
        self.assertAlmostEqual(margin, 0.625)

    def test_zero_predicted_rate_returns_infinity(self):
        margin = compute_rate_margin(0.0, 10.0, 2.0)
        self.assertTrue(math.isinf(margin))

    def test_negative_predicted_raises(self):
        with self.assertRaises(SEEError):
            compute_rate_margin(-1.0, 10.0, 2.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(SEEError):
            compute_rate_margin(1.0, 0.0, 2.0)

    def test_negative_allowable_raises(self):
        with self.assertRaises(SEEError):
            compute_rate_margin(1.0, -5.0, 2.0)

    def test_zero_rdm_min_raises(self):
        with self.assertRaises(SEEError):
            compute_rate_margin(1.0, 10.0, 0.0)


class TestCheckSeeCompliance(unittest.TestCase):
    def test_destructive_track_passes_above_rdm(self):
        result = check_see_compliance("U1", "destructive", 4.0, 2.0)
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["finding"])

    def test_destructive_track_fails_below_rdm(self):
        result = check_see_compliance("U2", "destructive", 1.5, 2.0)
        self.assertFalse(result["compliant"])
        self.assertIsNotNone(result["finding"])
        self.assertEqual(result["finding"]["part_id"], "U2")

    def test_destructive_track_passes_at_exact_rdm(self):
        result = check_see_compliance("U3", "destructive", 2.0, 2.0)
        self.assertTrue(result["compliant"])

    def test_non_destructive_track_passes_above_unity(self):
        result = check_see_compliance("U4", "non_destructive", 5.0, 2.0)
        self.assertTrue(result["compliant"])

    def test_non_destructive_track_fails_below_unity(self):
        result = check_see_compliance("U5", "non_destructive", 0.5, 2.0)
        self.assertFalse(result["compliant"])

    def test_non_destructive_track_passes_at_exact_unity(self):
        result = check_see_compliance("U6", "non_destructive", 1.0, 2.0)
        self.assertTrue(result["compliant"])

    def test_unknown_category_raises(self):
        with self.assertRaises(SEEError):
            check_see_compliance("U7", "unknown_category", 2.0, 2.0)

    def test_finding_contains_issue_key(self):
        result = check_see_compliance("U8", "destructive", 1.0, 2.0)
        self.assertEqual(result["finding"]["issue"], "see_margin_below_threshold")


class TestAssessPart(unittest.TestCase):
    def test_destructive_part_compliant(self):
        spec = {
            "part_id": "SEL-001",
            "effect_type": "SEL",
            "let_threshold": 40.0,
            "let_environment": 10.0,
        }
        result = assess_part(spec)
        self.assertEqual(result["part_id"], "SEL-001")
        self.assertEqual(result["category"], "destructive")
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin"], 4.0)

    def test_destructive_part_non_compliant(self):
        spec = {
            "part_id": "SEB-001",
            "effect_type": "SEB",
            "let_threshold": 15.0,
            "let_environment": 10.0,
        }
        result = assess_part(spec)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["margin"], 1.5)

    def test_non_destructive_part_compliant(self):
        spec = {
            "part_id": "SEU-001",
            "effect_type": "SEU",
            "predicted_rate": 1.0,
            "allowable_rate": 10.0,
        }
        result = assess_part(spec)
        self.assertEqual(result["category"], "non_destructive")
        self.assertTrue(result["compliant"])

    def test_non_destructive_part_non_compliant(self):
        spec = {
            "part_id": "SEFI-001",
            "effect_type": "SEFI",
            "predicted_rate": 9.0,
            "allowable_rate": 10.0,
        }
        result = assess_part(spec)
        self.assertFalse(result["compliant"])

    def test_missing_effect_type_raises(self):
        with self.assertRaises(SEEError):
            assess_part({"part_id": "X1"})

    def test_missing_let_threshold_raises(self):
        with self.assertRaises(SEEError):
            assess_part({"part_id": "X2", "effect_type": "SEL", "let_environment": 10.0})

    def test_missing_let_environment_raises(self):
        with self.assertRaises(SEEError):
            assess_part({"part_id": "X3", "effect_type": "SEGR", "let_threshold": 20.0})

    def test_missing_predicted_rate_raises(self):
        with self.assertRaises(SEEError):
            assess_part({"part_id": "X4", "effect_type": "SEU", "allowable_rate": 5.0})

    def test_missing_allowable_rate_raises(self):
        with self.assertRaises(SEEError):
            assess_part({"part_id": "X5", "effect_type": "SET", "predicted_rate": 1.0})

    def test_per_part_rdm_override(self):
        # With rdm_min=3.0, a LET margin of 2.5 must fail
        spec = {
            "part_id": "SEL-002",
            "effect_type": "SEL",
            "let_threshold": 25.0,
            "let_environment": 10.0,
            "rdm_min": 3.0,
        }
        result = assess_part(spec)
        self.assertAlmostEqual(result["margin"], 2.5)
        self.assertFalse(result["compliant"])

    def test_effect_type_normalized_to_uppercase(self):
        spec = {
            "part_id": "SEU-002",
            "effect_type": "seu",
            "predicted_rate": 0.5,
            "allowable_rate": 5.0,
        }
        result = assess_part(spec)
        self.assertEqual(result["effect_type"], "SEU")

    def test_zero_predicted_rate_is_compliant(self):
        spec = {
            "part_id": "SET-001",
            "effect_type": "SET",
            "predicted_rate": 0.0,
            "allowable_rate": 1.0,
        }
        result = assess_part(spec)
        self.assertTrue(result["compliant"])
        self.assertTrue(math.isinf(result["margin"]))

    def test_default_rdm_min_applied(self):
        spec = {
            "part_id": "SEL-003",
            "effect_type": "SEL",
            "let_threshold": 20.0,
            "let_environment": 10.0,
        }
        result = assess_part(spec)
        self.assertEqual(result["rdm_min"], DEFAULT_RDM_MIN)

    def test_result_does_not_mutate_input(self):
        spec = {
            "part_id": "SEU-003",
            "effect_type": "SEU",
            "predicted_rate": 1.0,
            "allowable_rate": 10.0,
        }
        original_keys = set(spec.keys())
        assess_part(spec)
        self.assertEqual(set(spec.keys()), original_keys)


class TestAssessAll(unittest.TestCase):
    def test_mixed_compliant_parts(self):
        parts = [
            {
                "part_id": "A",
                "effect_type": "SEL",
                "let_threshold": 40.0,
                "let_environment": 10.0,
            },
            {
                "part_id": "B",
                "effect_type": "SEU",
                "predicted_rate": 1.0,
                "allowable_rate": 10.0,
            },
        ]
        results = assess_all(parts)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["compliant"] for r in results))

    def test_empty_list_returns_empty(self):
        self.assertEqual(assess_all([]), [])

    def test_order_preserved(self):
        parts = [
            {"part_id": "first", "effect_type": "SEU", "predicted_rate": 0.1, "allowable_rate": 5.0},
            {"part_id": "second", "effect_type": "SEL", "let_threshold": 30.0, "let_environment": 10.0},
        ]
        results = assess_all(parts)
        self.assertEqual(results[0]["part_id"], "first")
        self.assertEqual(results[1]["part_id"], "second")

    def test_raises_on_invalid_part(self):
        parts = [
            {"part_id": "good", "effect_type": "SEU", "predicted_rate": 1.0, "allowable_rate": 5.0},
            {"part_id": "bad"},
        ]
        with self.assertRaises(SEEError):
            assess_all(parts)


class TestSeeFindings(unittest.TestCase):
    def test_all_compliant_returns_empty(self):
        parts = [
            {"part_id": "A", "effect_type": "SEL", "let_threshold": 40.0, "let_environment": 10.0},
            {"part_id": "B", "effect_type": "SEU", "predicted_rate": 1.0, "allowable_rate": 10.0},
        ]
        results = assess_all(parts)
        findings = see_findings(results)
        self.assertEqual(findings, [])

    def test_non_compliant_parts_appear_in_findings(self):
        parts = [
            {"part_id": "FAIL1", "effect_type": "SEL", "let_threshold": 5.0, "let_environment": 10.0},
            {"part_id": "PASS1", "effect_type": "SEU", "predicted_rate": 1.0, "allowable_rate": 10.0},
            {"part_id": "FAIL2", "effect_type": "SEFI", "predicted_rate": 9.0, "allowable_rate": 10.0},
        ]
        results = assess_all(parts)
        findings = see_findings(results)
        self.assertEqual(len(findings), 2)
        failing_ids = {f["part_id"] for f in findings}
        self.assertIn("FAIL1", failing_ids)
        self.assertIn("FAIL2", failing_ids)
        self.assertNotIn("PASS1", failing_ids)

    def test_finding_dict_has_required_keys(self):
        parts = [
            {"part_id": "X", "effect_type": "SEB", "let_threshold": 1.0, "let_environment": 10.0},
        ]
        results = assess_all(parts)
        findings = see_findings(results)
        self.assertEqual(len(findings), 1)
        f = findings[0]
        for key in ("issue", "part_id", "category", "margin", "threshold", "rdm_min"):
            self.assertIn(key, f)


if __name__ == "__main__":
    unittest.main()
