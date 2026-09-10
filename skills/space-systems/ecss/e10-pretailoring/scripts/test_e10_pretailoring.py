#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C pre-tailoring matrix (clause 7).

Exercises scripts/e10_pretailoring_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a pre-tailoring matrix entry
must define a status (applicable|optional|not_applicable) for every
product type in scope; applicability resolves per declared product
type; a project's carried-forward clauses are checked against the
resolved set for missing mandatory clauses, out-of-scope clauses, and
unknown clause ids; pre-tailoring is ready for project-specific
tailoring only when none of those three findings are present.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_pretailoring_logic as pt  # noqa: E402

PRODUCT_TYPES = ("space_segment", "ground_segment", "launch_service_segment")


def make_matrix():
    return {
        "5.2.1": {
            "space_segment": "applicable",
            "ground_segment": "applicable",
            "launch_service_segment": "optional",
        },
        "5.4.1.4": {
            "space_segment": "applicable",
            "ground_segment": "not_applicable",
            "launch_service_segment": "not_applicable",
        },
        "5.6.5": {
            "space_segment": "optional",
            "ground_segment": "optional",
            "launch_service_segment": "optional",
        },
    }


class ValidatePretailoringMatrixTest(unittest.TestCase):
    def test_complete_matrix_has_no_problems(self):
        report = pt.validate_pretailoring_matrix(make_matrix(), PRODUCT_TYPES)
        self.assertEqual(report, {})

    def test_missing_product_type_reported(self):
        matrix = make_matrix()
        del matrix["5.2.1"]["launch_service_segment"]
        report = pt.validate_pretailoring_matrix(matrix, PRODUCT_TYPES)
        self.assertIn("5.2.1", report)
        self.assertTrue(
            any("missing product type: launch_service_segment" in p for p in report["5.2.1"])
        )

    def test_unrecognised_product_type_reported(self):
        matrix = make_matrix()
        matrix["5.2.1"]["orbital_segment"] = "applicable"
        report = pt.validate_pretailoring_matrix(matrix, PRODUCT_TYPES)
        self.assertIn("5.2.1", report)
        self.assertTrue(any("unrecognised product type" in p for p in report["5.2.1"]))

    def test_invalid_status_reported(self):
        matrix = make_matrix()
        matrix["5.6.5"]["space_segment"] = "mandatory"
        report = pt.validate_pretailoring_matrix(matrix, PRODUCT_TYPES)
        self.assertIn("5.6.5", report)
        self.assertTrue(any("invalid status" in p for p in report["5.6.5"]))


class ResolveApplicabilityTest(unittest.TestCase):
    def test_resolves_status_per_product_type(self):
        resolved = pt.resolve_applicability(make_matrix(), "space_segment")
        self.assertEqual(
            resolved, {"5.2.1": "applicable", "5.4.1.4": "applicable", "5.6.5": "optional"}
        )

    def test_clauses_with_status_sorted(self):
        applicable = pt.clauses_with_status(make_matrix(), "ground_segment", "applicable")
        self.assertEqual(applicable, ["5.2.1"])
        not_applicable = pt.clauses_with_status(make_matrix(), "ground_segment", "not_applicable")
        self.assertEqual(not_applicable, ["5.4.1.4"])


class CheckPretailoringComplianceTest(unittest.TestCase):
    def test_fully_compliant_project_has_no_findings(self):
        report = pt.check_pretailoring_compliance(
            make_matrix(), "space_segment", ["5.2.1", "5.4.1.4"]
        )
        self.assertEqual(report["missing_mandatory"], [])
        self.assertEqual(report["out_of_scope"], [])
        self.assertEqual(report["unknown_clauses"], [])
        self.assertTrue(pt.is_ready_for_project_tailoring(report))

    def test_missing_mandatory_clause_flagged(self):
        report = pt.check_pretailoring_compliance(make_matrix(), "space_segment", ["5.2.1"])
        self.assertEqual(report["missing_mandatory"], ["5.4.1.4"])
        self.assertFalse(pt.is_ready_for_project_tailoring(report))

    def test_out_of_scope_clause_flagged(self):
        report = pt.check_pretailoring_compliance(
            make_matrix(), "ground_segment", ["5.2.1", "5.4.1.4"]
        )
        self.assertEqual(report["out_of_scope"], ["5.4.1.4"])
        self.assertFalse(pt.is_ready_for_project_tailoring(report))

    def test_unknown_clause_flagged(self):
        report = pt.check_pretailoring_compliance(
            make_matrix(), "space_segment", ["5.2.1", "5.4.1.4", "9.9.9"]
        )
        self.assertEqual(report["unknown_clauses"], ["9.9.9"])
        self.assertFalse(pt.is_ready_for_project_tailoring(report))

    def test_optional_clause_never_flagged_either_way(self):
        report_with = pt.check_pretailoring_compliance(
            make_matrix(), "space_segment", ["5.2.1", "5.4.1.4", "5.6.5"]
        )
        report_without = pt.check_pretailoring_compliance(
            make_matrix(), "space_segment", ["5.2.1", "5.4.1.4"]
        )
        for report in (report_with, report_without):
            self.assertNotIn("5.6.5", report["missing_mandatory"])
            self.assertNotIn("5.6.5", report["out_of_scope"])
        self.assertTrue(pt.is_ready_for_project_tailoring(report_with))
        self.assertTrue(pt.is_ready_for_project_tailoring(report_without))


if __name__ == "__main__":
    unittest.main(verbosity=2)
