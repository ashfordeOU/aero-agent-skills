#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C §4.6.1–4.6.2 HFE requirements
process.

Exercises scripts/e1011_hfe_req_process_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 — each HFE
requirement type categorizes to exactly itself or raises for an
unrecognized type; a valid lifecycle status returns True and an
unrecognized status raises; a requirement without a source identifier
produces an upstream-trace violation; a requirement in an
allocation-required status without allocated elements produces an
allocation violation; a requirement at proposed status without elements
has no allocation violation; an allocated element of unrecognized type
is flagged; the aggregated review is compliant only when both finding
lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_hfe_req_process_logic as hfe  # noqa: E402


class CategorizeReqTest(unittest.TestCase):
    def test_functional_type_recognized(self):
        self.assertEqual(hfe.categorize_req("functional"), "functional")

    def test_performance_type_recognized(self):
        self.assertEqual(hfe.categorize_req("performance"), "performance")

    def test_environmental_type_recognized(self):
        self.assertEqual(hfe.categorize_req("environmental"), "environmental")

    def test_safety_type_recognized(self):
        self.assertEqual(hfe.categorize_req("safety"), "safety")

    def test_anthropometric_type_recognized(self):
        self.assertEqual(hfe.categorize_req("anthropometric"), "anthropometric")

    def test_unknown_req_type_raises(self):
        with self.assertRaises(ValueError):
            hfe.categorize_req("aesthetic")


class ValidateStatusTest(unittest.TestCase):
    def test_proposed_status_valid(self):
        self.assertTrue(hfe.validate_status("proposed"))

    def test_approved_status_valid(self):
        self.assertTrue(hfe.validate_status("approved"))

    def test_allocated_status_valid(self):
        self.assertTrue(hfe.validate_status("allocated"))

    def test_verified_status_valid(self):
        self.assertTrue(hfe.validate_status("verified"))

    def test_closed_status_valid(self):
        self.assertTrue(hfe.validate_status("closed"))

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            hfe.validate_status("pending_review")


class CheckTraceabilityTest(unittest.TestCase):
    def test_missing_source_id_flagged(self):
        req = {"req_id": "HFE-001", "source_id": None}
        violations = hfe.check_traceability(req)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_upstream_trace")
        self.assertEqual(violations[0]["req_id"], "HFE-001")

    def test_empty_source_id_flagged(self):
        req = {"req_id": "HFE-002", "source_id": ""}
        violations = hfe.check_traceability(req)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_upstream_trace")

    def test_present_source_id_no_violation(self):
        req = {"req_id": "HFE-003", "source_id": "OPS-CON-12"}
        self.assertEqual(hfe.check_traceability(req), [])

    def test_check_traceability_does_not_mutate_req(self):
        req = {"req_id": "HFE-004", "source_id": None}
        original_keys = set(req.keys())
        hfe.check_traceability(req)
        self.assertEqual(set(req.keys()), original_keys)


class CheckAllocationTest(unittest.TestCase):
    def test_allocated_status_no_elements_flagged(self):
        req = {"req_id": "HFE-010", "status": "allocated", "allocated_elements": []}
        violations = hfe.check_allocation(req)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "unallocated_requirement")
        self.assertEqual(violations[0]["status"], "allocated")

    def test_implemented_status_no_elements_flagged(self):
        req = {"req_id": "HFE-011", "status": "implemented", "allocated_elements": []}
        violations = hfe.check_allocation(req)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "unallocated_requirement")

    def test_proposed_status_no_elements_no_violation(self):
        req = {"req_id": "HFE-012", "status": "proposed", "allocated_elements": []}
        self.assertEqual(hfe.check_allocation(req), [])

    def test_approved_status_no_elements_no_violation(self):
        req = {"req_id": "HFE-013", "status": "approved", "allocated_elements": []}
        self.assertEqual(hfe.check_allocation(req), [])

    def test_unrecognized_element_type_flagged(self):
        req = {
            "req_id": "HFE-014",
            "status": "allocated",
            "allocated_elements": [
                {"element_id": "SW-42", "element_type": "firmware"}
            ],
        }
        violations = hfe.check_allocation(req)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "unrecognized_element_type")
        self.assertEqual(violations[0]["element_type"], "firmware")

    def test_recognized_hardware_element_no_violation(self):
        req = {
            "req_id": "HFE-015",
            "status": "allocated",
            "allocated_elements": [
                {"element_id": "HW-01", "element_type": "hardware"}
            ],
        }
        self.assertEqual(hfe.check_allocation(req), [])

    def test_multiple_recognized_element_types_no_violation(self):
        req = {
            "req_id": "HFE-016",
            "status": "verified",
            "allocated_elements": [
                {"element_id": "SW-01", "element_type": "software"},
                {"element_id": "PROC-01", "element_type": "procedure"},
            ],
        }
        self.assertEqual(hfe.check_allocation(req), [])


class HfeReqReviewTest(unittest.TestCase):
    def test_fully_compliant_review(self):
        req = {
            "req_id": "HFE-020",
            "req_type": "functional",
            "status": "allocated",
            "source_id": "OCD-3.2.1",
            "allocated_elements": [
                {"element_id": "SW-DISP-01", "element_type": "software"}
            ],
        }
        review = hfe.hfe_req_review(req)
        self.assertEqual(review, {"traceability": [], "allocation": []})
        self.assertTrue(hfe.is_req_compliant(review))

    def test_review_flags_missing_source_and_missing_element(self):
        req = {
            "req_id": "HFE-021",
            "req_type": "safety",
            "status": "allocated",
            "source_id": None,
            "allocated_elements": [],
        }
        review = hfe.hfe_req_review(req)
        self.assertEqual(len(review["traceability"]), 1)
        self.assertEqual(len(review["allocation"]), 1)
        self.assertFalse(hfe.is_req_compliant(review))

    def test_review_raises_on_unknown_req_type(self):
        req = {
            "req_id": "HFE-022",
            "req_type": "aesthetic",
            "status": "proposed",
            "source_id": "OCD-1",
            "allocated_elements": [],
        }
        with self.assertRaises(ValueError):
            hfe.hfe_req_review(req)

    def test_review_raises_on_unknown_status(self):
        req = {
            "req_id": "HFE-023",
            "req_type": "performance",
            "status": "pending_review",
            "source_id": "OCD-2",
            "allocated_elements": [],
        }
        with self.assertRaises(ValueError):
            hfe.hfe_req_review(req)

    def test_proposed_req_with_source_is_compliant(self):
        req = {
            "req_id": "HFE-024",
            "req_type": "environmental",
            "status": "proposed",
            "source_id": "REG-EVA-05",
            "allocated_elements": [],
        }
        review = hfe.hfe_req_review(req)
        self.assertTrue(hfe.is_req_compliant(review))


class IsReqCompliantTest(unittest.TestCase):
    def test_empty_finding_lists_are_compliant(self):
        self.assertTrue(hfe.is_req_compliant({"traceability": [], "allocation": []}))

    def test_traceability_finding_is_not_compliant(self):
        self.assertFalse(
            hfe.is_req_compliant(
                {
                    "traceability": [{"issue": "missing_upstream_trace", "req_id": "X"}],
                    "allocation": [],
                }
            )
        )

    def test_allocation_finding_is_not_compliant(self):
        self.assertFalse(
            hfe.is_req_compliant(
                {
                    "traceability": [],
                    "allocation": [{"issue": "unallocated_requirement", "req_id": "X"}],
                }
            )
        )


if __name__ == "__main__":
    unittest.main()
