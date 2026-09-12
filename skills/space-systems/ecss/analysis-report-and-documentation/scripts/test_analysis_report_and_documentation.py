"""
Gate 3 contract tests for analysis_report_and_documentation_logic.
stdlib unittest; offline; deterministic.
Run: python3 test_analysis_report_and_documentation.py
"""

import unittest

from analysis_report_and_documentation_logic import (
    STRUCTURAL_REPORT_REQUIRED_SECTIONS,
    LBB_REPORT_REQUIRED_SECTIONS,
    MARGIN_OF_SAFETY_LIMIT,
    compute_margin_of_safety,
    check_structural_report,
    check_lbb_report,
    evaluate_load_cases,
    evaluate_full_deliverable,
)


class TestComputeMarginOfSafety(unittest.TestCase):

    def test_ms_positive_allowable_greater_than_applied(self):
        ms = compute_margin_of_safety(allowable=120.0, applied=100.0)
        self.assertAlmostEqual(ms, 0.2)

    def test_ms_zero_when_allowable_equals_applied(self):
        ms = compute_margin_of_safety(allowable=50.0, applied=50.0)
        self.assertAlmostEqual(ms, 0.0)

    def test_ms_negative_when_applied_exceeds_allowable(self):
        ms = compute_margin_of_safety(allowable=80.0, applied=100.0)
        self.assertAlmostEqual(ms, -0.2)

    def test_ms_raises_on_zero_applied(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(allowable=100.0, applied=0.0)

    def test_ms_raises_on_negative_applied(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(allowable=100.0, applied=-10.0)

    def test_ms_raises_on_zero_allowable(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(allowable=0.0, applied=50.0)

    def test_ms_raises_on_negative_allowable(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(allowable=-5.0, applied=50.0)

    def test_ms_large_safety_factor(self):
        ms = compute_margin_of_safety(allowable=300.0, applied=100.0)
        self.assertAlmostEqual(ms, 2.0)


class TestCheckStructuralReport(unittest.TestCase):

    def test_all_required_sections_present_returns_compliant(self):
        result = check_structural_report(
            list(STRUCTURAL_REPORT_REQUIRED_SECTIONS)
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["missing"], [])

    def test_missing_single_section_flagged(self):
        sections = [s for s in STRUCTURAL_REPORT_REQUIRED_SECTIONS
                    if s != "margin_of_safety"]
        result = check_structural_report(sections)
        self.assertFalse(result["compliant"])
        self.assertIn("margin_of_safety", result["missing"])

    def test_empty_section_list_flags_all_missing(self):
        result = check_structural_report([])
        self.assertFalse(result["compliant"])
        self.assertEqual(
            len(result["missing"]), len(STRUCTURAL_REPORT_REQUIRED_SECTIONS)
        )

    def test_extra_sections_do_not_affect_compliance(self):
        sections = list(STRUCTURAL_REPORT_REQUIRED_SECTIONS) + [
            "appendix_a", "revision_history"
        ]
        result = check_structural_report(sections)
        self.assertTrue(result["compliant"])

    def test_section_matching_is_case_insensitive(self):
        sections = [s.upper() for s in STRUCTURAL_REPORT_REQUIRED_SECTIONS]
        result = check_structural_report(sections)
        self.assertTrue(result["compliant"])

    def test_non_list_input_raises_type_error(self):
        with self.assertRaises(TypeError):
            check_structural_report("objectives")


class TestCheckLbbReport(unittest.TestCase):

    def test_all_lbb_sections_present_returns_compliant(self):
        result = check_lbb_report(list(LBB_REPORT_REQUIRED_SECTIONS))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["missing"], [])

    def test_missing_lbb_section_flagged(self):
        sections = [s for s in LBB_REPORT_REQUIRED_SECTIONS
                    if s != "leak_detection_rationale"]
        result = check_lbb_report(sections)
        self.assertFalse(result["compliant"])
        self.assertIn("leak_detection_rationale", result["missing"])

    def test_empty_lbb_section_list_flags_all_missing(self):
        result = check_lbb_report([])
        self.assertFalse(result["compliant"])
        self.assertEqual(
            len(result["missing"]), len(LBB_REPORT_REQUIRED_SECTIONS)
        )


class TestEvaluateLoadCases(unittest.TestCase):

    def test_single_passing_load_case(self):
        lcs = [{"name": "LC1", "allowable": 200.0, "applied": 100.0}]
        result = evaluate_load_cases(lcs)
        self.assertTrue(result["all_compliant"])
        self.assertAlmostEqual(result["load_cases"][0]["margin_of_safety"], 1.0)

    def test_single_failing_load_case(self):
        lcs = [{"name": "LC2", "allowable": 80.0, "applied": 100.0}]
        result = evaluate_load_cases(lcs)
        self.assertFalse(result["all_compliant"])
        self.assertFalse(result["load_cases"][0]["compliant"])

    def test_mixed_load_cases_flags_any_failure(self):
        lcs = [
            {"name": "LC_ok", "allowable": 150.0, "applied": 100.0},
            {"name": "LC_fail", "allowable": 90.0, "applied": 100.0},
        ]
        result = evaluate_load_cases(lcs)
        self.assertFalse(result["all_compliant"])

    def test_load_case_missing_allowable_key_records_error(self):
        lcs = [{"name": "LC_bad", "applied": 100.0}]
        result = evaluate_load_cases(lcs)
        self.assertFalse(result["load_cases"][0]["compliant"])
        self.assertIsNotNone(result["load_cases"][0]["error"])

    def test_load_case_zero_applied_records_error(self):
        lcs = [{"name": "LC_zero", "allowable": 100.0, "applied": 0.0}]
        result = evaluate_load_cases(lcs)
        self.assertFalse(result["load_cases"][0]["compliant"])
        self.assertIsNotNone(result["load_cases"][0]["error"])

    def test_empty_load_case_list_is_all_compliant(self):
        result = evaluate_load_cases([])
        self.assertTrue(result["all_compliant"])
        self.assertEqual(result["load_cases"], [])

    def test_ms_at_limit_zero_is_compliant(self):
        lcs = [{"name": "LC_limit", "allowable": 100.0, "applied": 100.0}]
        result = evaluate_load_cases(lcs)
        self.assertTrue(result["load_cases"][0]["compliant"])
        self.assertAlmostEqual(result["load_cases"][0]["margin_of_safety"], 0.0)


class TestEvaluateFullDeliverable(unittest.TestCase):

    def test_full_structural_report_compliant(self):
        report = {
            "report_type": "structural",
            "sections": list(STRUCTURAL_REPORT_REQUIRED_SECTIONS),
            "load_cases": [
                {"name": "LC1", "allowable": 200.0, "applied": 100.0}
            ],
        }
        result = evaluate_full_deliverable(report)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["report_type"], "structural")

    def test_full_structural_report_noncompliant_due_to_missing_section(self):
        sections = [s for s in STRUCTURAL_REPORT_REQUIRED_SECTIONS
                    if s != "conclusions"]
        report = {
            "report_type": "structural",
            "sections": sections,
            "load_cases": [
                {"name": "LC1", "allowable": 200.0, "applied": 100.0}
            ],
        }
        result = evaluate_full_deliverable(report)
        self.assertFalse(result["compliant"])
        self.assertIn("conclusions", result["section_check"]["missing"])

    def test_full_structural_report_noncompliant_due_to_negative_ms(self):
        report = {
            "report_type": "structural",
            "sections": list(STRUCTURAL_REPORT_REQUIRED_SECTIONS),
            "load_cases": [
                {"name": "LC_fail", "allowable": 50.0, "applied": 100.0}
            ],
        }
        result = evaluate_full_deliverable(report)
        self.assertFalse(result["compliant"])
        self.assertFalse(result["load_case_check"]["all_compliant"])

    def test_full_lbb_report_compliant(self):
        report = {
            "report_type": "lbb",
            "sections": list(LBB_REPORT_REQUIRED_SECTIONS),
        }
        result = evaluate_full_deliverable(report)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["report_type"], "lbb")

    def test_full_lbb_report_noncompliant_due_to_missing_section(self):
        sections = [s for s in LBB_REPORT_REQUIRED_SECTIONS
                    if s != "inspection_intervals"]
        report = {
            "report_type": "lbb",
            "sections": sections,
        }
        result = evaluate_full_deliverable(report)
        self.assertFalse(result["compliant"])
        self.assertIn("inspection_intervals", result["section_check"]["missing"])

    def test_unknown_report_type_raises_value_error(self):
        report = {"report_type": "thermal", "sections": []}
        with self.assertRaises(ValueError):
            evaluate_full_deliverable(report)

    def test_report_type_comparison_is_case_insensitive(self):
        report = {
            "report_type": "LBB",
            "sections": list(LBB_REPORT_REQUIRED_SECTIONS),
        }
        result = evaluate_full_deliverable(report)
        self.assertTrue(result["compliant"])

    def test_margin_of_safety_limit_constant_is_zero(self):
        self.assertEqual(MARGIN_OF_SAFETY_LIMIT, 0.0)


if __name__ == "__main__":
    unittest.main()
