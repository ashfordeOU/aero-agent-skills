#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.3.4 analysis tool and
model qualification/correlation.

Exercises scripts/e10_analysis_tools_models_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a tool's
qualification basis is heritage reuse only when it is heritage AND its
domain applicability is confirmed, otherwise it requires correlation;
the acceptance tolerance is set by analysis criticality and an
unrecognized criticality raises; correlation error is the relative
percent difference between a predicted value and a nonzero reference
value, and a zero reference raises; a requires_correlation tool is
qualified only when its correlation error is within tolerance, a
heritage_reuse tool is always qualified, and an unrecognized basis or
missing correlation data on a requires_correlation basis raises; the
per-tool review packages basis, status and any issue; and the
aggregated per-analysis review is valid only when every tool review is
free of issues, with a duplicate tool_id or an empty tool set raising.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_analysis_tools_models_logic as tm  # noqa: E402


class ClassifyQualificationBasisTest(unittest.TestCase):
    def test_heritage_with_confirmed_domain_is_reuse(self):
        self.assertEqual(
            tm.classify_qualification_basis(True, True), "heritage_reuse"
        )

    def test_heritage_without_confirmed_domain_requires_correlation(self):
        self.assertEqual(
            tm.classify_qualification_basis(True, False), "requires_correlation"
        )

    def test_non_heritage_requires_correlation(self):
        self.assertEqual(
            tm.classify_qualification_basis(False, True), "requires_correlation"
        )

    def test_neither_heritage_nor_confirmed_requires_correlation(self):
        self.assertEqual(
            tm.classify_qualification_basis(False, False), "requires_correlation"
        )


class AcceptanceTolerancePercentTest(unittest.TestCase):
    def test_high_criticality_tolerance(self):
        self.assertEqual(tm.acceptance_tolerance_percent("high"), 5.0)

    def test_medium_criticality_tolerance(self):
        self.assertEqual(tm.acceptance_tolerance_percent("medium"), 10.0)

    def test_low_criticality_tolerance(self):
        self.assertEqual(tm.acceptance_tolerance_percent("low"), 20.0)

    def test_unrecognized_criticality_raises(self):
        with self.assertRaises(ValueError):
            tm.acceptance_tolerance_percent("severe")


class CorrelationErrorPercentTest(unittest.TestCase):
    def test_exact_match_is_zero_error(self):
        self.assertEqual(tm.correlation_error_percent(10.0, 10.0), 0.0)

    def test_overprediction_error(self):
        self.assertAlmostEqual(tm.correlation_error_percent(11.0, 10.0), 10.0)

    def test_underprediction_error_is_positive(self):
        self.assertAlmostEqual(tm.correlation_error_percent(9.0, 10.0), 10.0)

    def test_zero_reference_raises(self):
        with self.assertRaises(ValueError):
            tm.correlation_error_percent(1.0, 0.0)


class ToolQualificationStatusTest(unittest.TestCase):
    def test_heritage_reuse_is_always_qualified(self):
        self.assertEqual(
            tm.tool_qualification_status("heritage_reuse"), tm.STATUS_QUALIFIED
        )

    def test_correlation_within_tolerance_is_qualified(self):
        self.assertEqual(
            tm.tool_qualification_status("requires_correlation", 4.0, 5.0),
            tm.STATUS_QUALIFIED,
        )

    def test_correlation_at_tolerance_boundary_is_qualified(self):
        self.assertEqual(
            tm.tool_qualification_status("requires_correlation", 5.0, 5.0),
            tm.STATUS_QUALIFIED,
        )

    def test_correlation_exceeding_tolerance_is_flagged(self):
        self.assertEqual(
            tm.tool_qualification_status("requires_correlation", 6.0, 5.0),
            tm.STATUS_CORRELATION_EXCEEDED,
        )

    def test_requires_correlation_missing_data_raises(self):
        with self.assertRaises(ValueError):
            tm.tool_qualification_status("requires_correlation")

    def test_unrecognized_basis_raises(self):
        with self.assertRaises(ValueError):
            tm.tool_qualification_status("assumed_correct")


class ToolReviewTest(unittest.TestCase):
    def test_heritage_tool_review_has_no_issues(self):
        tool = {
            "tool_id": "thermal-fem-01",
            "is_heritage": True,
            "domain_applicability_confirmed": True,
        }
        review = tm.tool_review(tool)
        self.assertEqual(review["qualification_basis"], "heritage_reuse")
        self.assertEqual(review["status"], tm.STATUS_QUALIFIED)
        self.assertIsNone(review["correlation_error_pct"])
        self.assertEqual(review["issues"], [])

    def test_new_tool_within_tolerance_qualified(self):
        tool = {
            "tool_id": "orbit-prop-02",
            "is_heritage": False,
            "domain_applicability_confirmed": False,
            "criticality": "medium",
            "predicted_value": 103.0,
            "reference_value": 100.0,
        }
        review = tm.tool_review(tool)
        self.assertEqual(review["qualification_basis"], "requires_correlation")
        self.assertEqual(review["status"], tm.STATUS_QUALIFIED)
        self.assertAlmostEqual(review["correlation_error_pct"], 3.0)
        self.assertEqual(review["issues"], [])

    def test_new_tool_exceeding_tolerance_flagged(self):
        tool = {
            "tool_id": "cfd-plume-03",
            "is_heritage": False,
            "domain_applicability_confirmed": False,
            "criticality": "high",
            "predicted_value": 120.0,
            "reference_value": 100.0,
        }
        review = tm.tool_review(tool)
        self.assertEqual(review["status"], tm.STATUS_CORRELATION_EXCEEDED)
        self.assertEqual(len(review["issues"]), 1)
        self.assertEqual(
            review["issues"][0]["issue"], "tool_correlation_exceeds_tolerance"
        )

    def test_heritage_tool_outside_domain_requires_correlation(self):
        tool = {
            "tool_id": "struct-fem-04",
            "is_heritage": True,
            "domain_applicability_confirmed": False,
            "criticality": "low",
            "predicted_value": 118.0,
            "reference_value": 100.0,
        }
        review = tm.tool_review(tool)
        self.assertEqual(review["qualification_basis"], "requires_correlation")
        self.assertEqual(review["status"], tm.STATUS_QUALIFIED)


class AnalysisQualificationReviewTest(unittest.TestCase):
    def test_all_qualified_tools_yield_valid_analysis(self):
        tools = [
            {
                "tool_id": "thermal-fem-01",
                "is_heritage": True,
                "domain_applicability_confirmed": True,
            },
            {
                "tool_id": "orbit-prop-02",
                "is_heritage": False,
                "domain_applicability_confirmed": False,
                "criticality": "medium",
                "predicted_value": 101.0,
                "reference_value": 100.0,
            },
        ]
        review = tm.analysis_qualification_review(tools)
        self.assertTrue(review["is_analysis_valid"])
        self.assertEqual(review["issues"], [])
        self.assertTrue(tm.is_analysis_valid(review))

    def test_one_unqualified_tool_invalidates_analysis(self):
        tools = [
            {
                "tool_id": "thermal-fem-01",
                "is_heritage": True,
                "domain_applicability_confirmed": True,
            },
            {
                "tool_id": "cfd-plume-03",
                "is_heritage": False,
                "domain_applicability_confirmed": False,
                "criticality": "high",
                "predicted_value": 130.0,
                "reference_value": 100.0,
            },
        ]
        review = tm.analysis_qualification_review(tools)
        self.assertFalse(review["is_analysis_valid"])
        self.assertEqual(len(review["issues"]), 1)
        self.assertFalse(tm.is_analysis_valid(review))

    def test_duplicate_tool_id_raises(self):
        tools = [
            {
                "tool_id": "thermal-fem-01",
                "is_heritage": True,
                "domain_applicability_confirmed": True,
            },
            {
                "tool_id": "thermal-fem-01",
                "is_heritage": True,
                "domain_applicability_confirmed": True,
            },
        ]
        with self.assertRaises(ValueError):
            tm.analysis_qualification_review(tools)

    def test_empty_tool_list_raises(self):
        with self.assertRaises(ValueError):
            tm.analysis_qualification_review([])


if __name__ == "__main__":
    unittest.main(verbosity=2)
