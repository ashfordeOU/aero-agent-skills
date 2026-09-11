#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.5.2 product
verification close-out.

Exercises scripts/e10_product_verification_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a verification
method must be one of test/analysis/inspection/review_of_design and an
unrecognized method raises; a method's status is failed if any of its
evidence records is a fail, verified if it has no fail and at least
one pass, otherwise open; a requirement with no assigned method is
itself a finding (no_method_assigned), and its close-out status is
failed if any assigned method failed, else open if any assigned method
is still open, else verified; a product review partitions every
requirement by close-out status and rejects a duplicate requirement
id; the product is verification-complete only when open, failed, and
no_method_assigned are all empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_product_verification_logic as pv  # noqa: E402


class ClassifyVerificationMethodTest(unittest.TestCase):
    def test_test_method_recognized(self):
        self.assertEqual(pv.classify_verification_method("test"), "test")

    def test_analysis_method_recognized(self):
        self.assertEqual(pv.classify_verification_method("analysis"), "analysis")

    def test_inspection_method_recognized(self):
        self.assertEqual(
            pv.classify_verification_method("inspection"), "inspection"
        )

    def test_review_of_design_method_recognized(self):
        self.assertEqual(
            pv.classify_verification_method("review_of_design"),
            "review_of_design",
        )

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            pv.classify_verification_method("telepathy")


class RequirementMethodStatusTest(unittest.TestCase):
    def test_pass_evidence_is_verified(self):
        evidence = [{"method": "test", "result": "pass"}]
        self.assertEqual(pv.requirement_method_status("test", evidence), "verified")

    def test_fail_evidence_is_failed(self):
        evidence = [{"method": "test", "result": "fail"}]
        self.assertEqual(pv.requirement_method_status("test", evidence), "failed")

    def test_no_evidence_is_open(self):
        self.assertEqual(pv.requirement_method_status("analysis", []), "open")

    def test_fail_wins_over_pass(self):
        evidence = [
            {"method": "test", "result": "pass"},
            {"method": "test", "result": "fail"},
        ]
        self.assertEqual(pv.requirement_method_status("test", evidence), "failed")

    def test_other_method_evidence_ignored(self):
        evidence = [{"method": "analysis", "result": "pass"}]
        self.assertEqual(pv.requirement_method_status("test", evidence), "open")

    def test_unrecognized_result_raises(self):
        evidence = [{"method": "test", "result": "maybe"}]
        with self.assertRaises(ValueError):
            pv.requirement_method_status("test", evidence)

    def test_unrecognized_method_raises(self):
        with self.assertRaises(ValueError):
            pv.requirement_method_status("telepathy", [])


class RequirementVerificationCloseoutTest(unittest.TestCase):
    def test_no_methods_assigned(self):
        requirement = {"requirement_id": "REQ-1", "verification_methods": []}
        self.assertEqual(
            pv.requirement_verification_closeout(requirement), "no_method_assigned"
        )

    def test_all_methods_verified(self):
        requirement = {
            "requirement_id": "REQ-2",
            "verification_methods": ["test", "analysis"],
            "evidence": [
                {"method": "test", "result": "pass"},
                {"method": "analysis", "result": "pass"},
            ],
        }
        self.assertEqual(pv.requirement_verification_closeout(requirement), "verified")

    def test_any_method_open(self):
        requirement = {
            "requirement_id": "REQ-3",
            "verification_methods": ["test", "inspection"],
            "evidence": [{"method": "test", "result": "pass"}],
        }
        self.assertEqual(pv.requirement_verification_closeout(requirement), "open")

    def test_any_method_failed(self):
        requirement = {
            "requirement_id": "REQ-4",
            "verification_methods": ["test", "inspection"],
            "evidence": [
                {"method": "test", "result": "pass"},
                {"method": "inspection", "result": "fail"},
            ],
        }
        self.assertEqual(pv.requirement_verification_closeout(requirement), "failed")

    def test_failed_takes_priority_over_open(self):
        requirement = {
            "requirement_id": "REQ-5",
            "verification_methods": ["test", "review_of_design"],
            "evidence": [{"method": "test", "result": "fail"}],
        }
        self.assertEqual(pv.requirement_verification_closeout(requirement), "failed")

    def test_duplicate_method_raises(self):
        requirement = {
            "requirement_id": "REQ-6",
            "verification_methods": ["test", "test"],
            "evidence": [],
        }
        with self.assertRaises(ValueError):
            pv.requirement_verification_closeout(requirement)

    def test_unrecognized_method_raises(self):
        requirement = {
            "requirement_id": "REQ-7",
            "verification_methods": ["telepathy"],
            "evidence": [],
        }
        with self.assertRaises(ValueError):
            pv.requirement_verification_closeout(requirement)


class ProductVerificationReviewTest(unittest.TestCase):
    def test_buckets_requirements_by_status(self):
        product = {
            "product_id": "sat-bus-1",
            "requirements": [
                {
                    "requirement_id": "REQ-10",
                    "verification_methods": ["test"],
                    "evidence": [{"method": "test", "result": "pass"}],
                },
                {
                    "requirement_id": "REQ-11",
                    "verification_methods": ["analysis"],
                    "evidence": [],
                },
                {
                    "requirement_id": "REQ-12",
                    "verification_methods": ["inspection"],
                    "evidence": [{"method": "inspection", "result": "fail"}],
                },
                {"requirement_id": "REQ-13", "verification_methods": []},
            ],
        }
        review = pv.product_verification_review(product)
        self.assertEqual(review["verified"], ["REQ-10"])
        self.assertEqual(review["open"], ["REQ-11"])
        self.assertEqual(review["failed"], ["REQ-12"])
        self.assertEqual(review["no_method_assigned"], ["REQ-13"])

    def test_duplicate_requirement_id_raises(self):
        product = {
            "product_id": "sat-bus-2",
            "requirements": [
                {"requirement_id": "REQ-20", "verification_methods": []},
                {"requirement_id": "REQ-20", "verification_methods": []},
            ],
        }
        with self.assertRaises(ValueError):
            pv.product_verification_review(product)

    def test_empty_product_has_empty_buckets(self):
        review = pv.product_verification_review({"product_id": "empty", "requirements": []})
        self.assertEqual(
            review,
            {"verified": [], "open": [], "failed": [], "no_method_assigned": []},
        )


class IsProductVerificationCompleteTest(unittest.TestCase):
    def test_complete_when_all_verified(self):
        review = {
            "verified": ["REQ-1", "REQ-2"],
            "open": [],
            "failed": [],
            "no_method_assigned": [],
        }
        self.assertTrue(pv.is_product_verification_complete(review))

    def test_incomplete_with_open(self):
        review = {
            "verified": [],
            "open": ["REQ-1"],
            "failed": [],
            "no_method_assigned": [],
        }
        self.assertFalse(pv.is_product_verification_complete(review))

    def test_incomplete_with_failed(self):
        review = {
            "verified": [],
            "open": [],
            "failed": ["REQ-1"],
            "no_method_assigned": [],
        }
        self.assertFalse(pv.is_product_verification_complete(review))

    def test_incomplete_with_no_method_assigned(self):
        review = {
            "verified": [],
            "open": [],
            "failed": [],
            "no_method_assigned": ["REQ-1"],
        }
        self.assertFalse(pv.is_product_verification_complete(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
