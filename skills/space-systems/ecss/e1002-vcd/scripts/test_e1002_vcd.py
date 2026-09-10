#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.8.2 / Annex B
Verification Control Document (VCD) logic.

Exercises scripts/e1002_vcd_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a recorded method must be
one of the four verification methods and must be permitted for the
requirement's category; a requirement marked not applicable must carry
a rationale and its status must agree with its applicability flag; a
"closed" status must carry closure evidence; the program-level
roll-up counts every status and computes percent complete against the
applicable total; and the full program review is compliant only when
every entry is issue-free and every applicable entry has closed.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_vcd_logic as vcd  # noqa: E402


def _entry(**overrides):
    base = {
        "requirement_id": "REQ-001",
        "category": "functional",
        "method": "test",
        "applicable": True,
        "status": "closed",
        "rationale": None,
        "closure_evidence_ref": "TRR-report-12",
    }
    base.update(overrides)
    return base


class ValidateVerificationMethodTest(unittest.TestCase):
    def test_test_is_valid(self):
        self.assertEqual(vcd.validate_verification_method("test"), "test")

    def test_review_of_design_is_valid(self):
        self.assertEqual(
            vcd.validate_verification_method("review_of_design"), "review_of_design"
        )

    def test_unrecognized_method_raises(self):
        with self.assertRaises(ValueError):
            vcd.validate_verification_method("telepathy")


class ValidateVerificationStatusTest(unittest.TestCase):
    def test_closed_is_valid(self):
        self.assertEqual(vcd.validate_verification_status("closed"), "closed")

    def test_unrecognized_status_raises(self):
        with self.assertRaises(ValueError):
            vcd.validate_verification_status("abandoned")


class AllowedMethodsForCategoryTest(unittest.TestCase):
    def test_functional_allows_test_and_analysis_only(self):
        self.assertEqual(
            vcd.allowed_methods_for_category("functional"),
            frozenset({"test", "analysis"}),
        )

    def test_design_constraint_allows_review_of_design(self):
        allowed = vcd.allowed_methods_for_category("design_constraint")
        self.assertIn("review_of_design", allowed)

    def test_unrecognized_category_raises(self):
        with self.assertRaises(ValueError):
            vcd.allowed_methods_for_category("aesthetic")


class MethodSelectionIssuesTest(unittest.TestCase):
    def test_permitted_method_has_no_issue(self):
        self.assertEqual(
            vcd.method_selection_issues("REQ-001", "functional", "test"), []
        )

    def test_review_of_design_not_permitted_for_safety(self):
        issues = vcd.method_selection_issues("REQ-002", "safety", "review_of_design")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["issue"], "method_not_permitted_for_category")
        self.assertEqual(issues[0]["allowed_methods"], ["analysis", "test"])

    def test_inspection_permitted_for_interface(self):
        self.assertEqual(
            vcd.method_selection_issues("REQ-003", "interface", "inspection"), []
        )

    def test_unrecognized_method_raises(self):
        with self.assertRaises(ValueError):
            vcd.method_selection_issues("REQ-004", "functional", "vibes")


class ApplicabilityIssuesTest(unittest.TestCase):
    def test_applicable_and_open_is_consistent(self):
        self.assertEqual(
            vcd.applicability_issues("REQ-001", True, "open", None), []
        )

    def test_not_applicable_with_rationale_is_consistent(self):
        issues = vcd.applicability_issues(
            "REQ-005", False, "not_applicable", "product has no propulsion subsystem"
        )
        self.assertEqual(issues, [])

    def test_not_applicable_without_rationale_flagged(self):
        issues = vcd.applicability_issues("REQ-005", False, "not_applicable", None)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["issue"], "missing_applicability_rationale")

    def test_applicable_true_with_not_applicable_status_mismatch(self):
        issues = vcd.applicability_issues("REQ-006", True, "not_applicable", None)
        self.assertTrue(
            any(issue["issue"] == "applicability_status_mismatch" for issue in issues)
        )

    def test_applicable_false_with_open_status_mismatch(self):
        issues = vcd.applicability_issues(
            "REQ-007", False, "open", "not yet assessed"
        )
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["issue"], "applicability_status_mismatch")

    def test_unrecognized_status_raises(self):
        with self.assertRaises(ValueError):
            vcd.applicability_issues("REQ-008", True, "shelved", None)


class ClosureIssuesTest(unittest.TestCase):
    def test_closed_with_evidence_has_no_issue(self):
        self.assertEqual(
            vcd.closure_issues("REQ-001", "closed", "TRR-report-12"), []
        )

    def test_closed_without_evidence_flagged(self):
        issues = vcd.closure_issues("REQ-001", "closed", None)
        self.assertEqual(
            issues, [{"issue": "missing_closure_evidence", "requirement_id": "REQ-001"}]
        )

    def test_open_without_evidence_has_no_issue(self):
        self.assertEqual(vcd.closure_issues("REQ-001", "open", None), [])


class EvaluateVcdEntryTest(unittest.TestCase):
    def test_clean_entry_has_no_issues(self):
        evaluation = vcd.evaluate_vcd_entry(_entry())
        self.assertTrue(vcd.is_entry_clean(evaluation))

    def test_missing_required_field_raises(self):
        entry = _entry()
        del entry["status"]
        with self.assertRaises(ValueError):
            vcd.evaluate_vcd_entry(entry)

    def test_entry_with_disallowed_method_is_not_clean(self):
        entry = _entry(category="safety", method="review_of_design")
        evaluation = vcd.evaluate_vcd_entry(entry)
        self.assertFalse(vcd.is_entry_clean(evaluation))
        self.assertTrue(evaluation["method_selection"])

    def test_entry_closed_without_evidence_is_not_clean(self):
        entry = _entry(closure_evidence_ref=None)
        evaluation = vcd.evaluate_vcd_entry(entry)
        self.assertFalse(vcd.is_entry_clean(evaluation))
        self.assertTrue(evaluation["closure"])


class VcdStatusRollupTest(unittest.TestCase):
    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            vcd.vcd_status_rollup([])

    def test_percent_complete_excludes_not_applicable(self):
        entries = [
            _entry(requirement_id="REQ-001", status="closed"),
            _entry(requirement_id="REQ-002", status="closed"),
            _entry(
                requirement_id="REQ-003",
                applicable=False,
                status="not_applicable",
                rationale="deleted requirement",
                closure_evidence_ref=None,
            ),
        ]
        rollup = vcd.vcd_status_rollup(entries)
        self.assertEqual(rollup["total"], 3)
        self.assertEqual(rollup["applicable_total"], 2)
        self.assertEqual(rollup["closed_count"], 2)
        self.assertAlmostEqual(rollup["percent_complete"], 100.0)

    def test_percent_complete_partial(self):
        entries = [
            _entry(requirement_id="REQ-001", status="closed"),
            _entry(requirement_id="REQ-002", status="open", closure_evidence_ref=None),
        ]
        rollup = vcd.vcd_status_rollup(entries)
        self.assertAlmostEqual(rollup["percent_complete"], 50.0)

    def test_all_not_applicable_is_vacuously_complete(self):
        entries = [
            _entry(
                requirement_id="REQ-001",
                applicable=False,
                status="not_applicable",
                rationale="out of scope for this product",
                closure_evidence_ref=None,
            )
        ]
        rollup = vcd.vcd_status_rollup(entries)
        self.assertEqual(rollup["applicable_total"], 0)
        self.assertAlmostEqual(rollup["percent_complete"], 100.0)


class IsVcdCompleteTest(unittest.TestCase):
    def test_full_closure_is_complete(self):
        rollup = vcd.vcd_status_rollup([_entry(status="closed")])
        self.assertTrue(vcd.is_vcd_complete(rollup))

    def test_partial_closure_is_not_complete(self):
        entries = [
            _entry(requirement_id="REQ-001", status="closed"),
            _entry(requirement_id="REQ-002", status="in_progress", closure_evidence_ref=None),
        ]
        rollup = vcd.vcd_status_rollup(entries)
        self.assertFalse(vcd.is_vcd_complete(rollup))


class VcdProgramReviewTest(unittest.TestCase):
    def test_fully_compliant_program(self):
        entries = [
            _entry(requirement_id="REQ-001", status="closed"),
            _entry(
                requirement_id="REQ-002",
                category="interface",
                method="inspection",
                status="closed",
            ),
        ]
        review = vcd.vcd_program_review(entries)
        self.assertTrue(review["compliant"])
        self.assertEqual(review["rollup"]["applicable_total"], 2)

    def test_program_with_open_requirement_not_compliant(self):
        entries = [
            _entry(requirement_id="REQ-001", status="closed"),
            _entry(requirement_id="REQ-002", status="open", closure_evidence_ref=None),
        ]
        review = vcd.vcd_program_review(entries)
        self.assertFalse(review["compliant"])

    def test_program_with_dirty_entry_not_compliant_even_if_all_closed(self):
        entries = [
            _entry(
                requirement_id="REQ-001",
                category="safety",
                method="review_of_design",
                status="closed",
            )
        ]
        review = vcd.vcd_program_review(entries)
        self.assertTrue(vcd.is_vcd_complete(review["rollup"]))
        self.assertFalse(review["compliant"])
        self.assertTrue(review["evaluations"]["REQ-001"]["method_selection"])

    def test_empty_program_raises(self):
        with self.assertRaises(ValueError):
            vcd.vcd_program_review([])


if __name__ == "__main__":
    unittest.main(verbosity=2)
