#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C requirement traceability (5.2.2).

Exercises scripts/e10_req_traceability_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a derived
requirement without an upward trace to its parent is a gap; a
customer requirement with no downward trace (no child requirement and
no direct product allocation) is a gap; any requirement missing a
product allocation or a verification link is a gap; parent/product/
verification ids that reference a record outside the given sets are
dangling-reference gaps; a fully-traced set reports no gaps.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_req_traceability_logic as rtl  # noqa: E402


def _chain():
    """One customer requirement flowed down to one derived requirement,
    allocated to a product, closed by a verification record."""
    requirements = [
        {"id": "CUS-001", "level": "customer", "parents": [], "products": [],
         "verifications": ["VER-001"]},
        {"id": "DER-001", "level": "derived", "parents": ["CUS-001"],
         "products": ["PROD-001"], "verifications": ["VER-002"]},
    ]
    products = ["PROD-001"]
    verifications = ["VER-001", "VER-002"]
    return requirements, products, verifications


class ValidateRequirementSetTest(unittest.TestCase):
    def test_well_formed_set_has_no_problems(self):
        requirements, _, _ = _chain()
        self.assertEqual(rtl.validate_requirement_set(requirements), [])

    def test_missing_id_is_a_problem(self):
        problems = rtl.validate_requirement_set([{"level": "customer"}])
        self.assertIn("requirement record missing id", problems)

    def test_duplicate_id_is_a_problem(self):
        requirements = [
            {"id": "CUS-001", "level": "customer"},
            {"id": "CUS-001", "level": "derived"},
        ]
        problems = rtl.validate_requirement_set(requirements)
        self.assertIn("duplicate requirement id: CUS-001", problems)

    def test_unknown_level_is_a_problem(self):
        problems = rtl.validate_requirement_set([{"id": "R-1", "level": "system"}])
        self.assertEqual(
            problems, ["requirement R-1 has unknown level: 'system'"]
        )


class TraceGapsTest(unittest.TestCase):
    def test_fully_traced_chain_has_no_gaps(self):
        requirements, products, verifications = _chain()
        self.assertEqual(rtl.trace_gaps(requirements, products, verifications), {})

    def test_derived_requirement_without_parent_is_a_gap(self):
        requirements, products, verifications = _chain()
        requirements[1]["parents"] = []
        gaps = rtl.trace_gaps(requirements, products, verifications)
        self.assertIn(rtl.GAP_NO_UPWARD_TRACE, gaps["DER-001"])

    def test_customer_requirement_with_no_downstream_is_a_gap(self):
        requirements = [
            {"id": "CUS-001", "level": "customer", "parents": [], "products": [],
             "verifications": ["VER-001"]},
        ]
        gaps = rtl.trace_gaps(requirements, ["PROD-001"], ["VER-001"])
        self.assertIn(rtl.GAP_NO_DOWNWARD_TRACE, gaps["CUS-001"])

    def test_customer_requirement_allocated_directly_is_not_a_downward_gap(self):
        requirements = [
            {"id": "CUS-001", "level": "customer", "parents": [], "products": ["PROD-001"],
             "verifications": ["VER-001"]},
        ]
        gaps = rtl.trace_gaps(requirements, ["PROD-001"], ["VER-001"])
        self.assertNotIn("CUS-001", gaps)

    def test_missing_product_allocation_is_a_gap(self):
        requirements, products, verifications = _chain()
        requirements[1]["products"] = []
        gaps = rtl.trace_gaps(requirements, products, verifications)
        self.assertIn(rtl.GAP_NO_PRODUCT_ALLOCATION, gaps["DER-001"])

    def test_missing_verification_link_is_a_gap(self):
        requirements, products, verifications = _chain()
        requirements[1]["verifications"] = []
        gaps = rtl.trace_gaps(requirements, products, verifications)
        self.assertIn(rtl.GAP_NO_VERIFICATION_LINK, gaps["DER-001"])

    def test_dangling_parent_reference_is_a_gap(self):
        requirements, products, verifications = _chain()
        requirements[1]["parents"] = ["CUS-999"]
        gaps = rtl.trace_gaps(requirements, products, verifications)
        self.assertIn(rtl.GAP_DANGLING_PARENT, gaps["DER-001"])

    def test_dangling_product_reference_is_a_gap(self):
        requirements, products, verifications = _chain()
        requirements[1]["products"] = ["PROD-999"]
        gaps = rtl.trace_gaps(requirements, products, verifications)
        self.assertIn(rtl.GAP_DANGLING_PRODUCT, gaps["DER-001"])

    def test_dangling_verification_reference_is_a_gap(self):
        requirements, products, verifications = _chain()
        requirements[1]["verifications"] = ["VER-999"]
        gaps = rtl.trace_gaps(requirements, products, verifications)
        self.assertIn(rtl.GAP_DANGLING_VERIFICATION, gaps["DER-001"])


class IsFullyTracedTest(unittest.TestCase):
    def test_fully_traced_chain_reports_true(self):
        requirements, products, verifications = _chain()
        traced, gaps = rtl.is_fully_traced(requirements, products, verifications)
        self.assertTrue(traced)
        self.assertEqual(gaps, {})

    def test_broken_chain_reports_false_with_gaps(self):
        requirements, products, verifications = _chain()
        requirements[1]["parents"] = []
        traced, gaps = rtl.is_fully_traced(requirements, products, verifications)
        self.assertFalse(traced)
        self.assertIn("DER-001", gaps)


if __name__ == "__main__":
    unittest.main(verbosity=2)
