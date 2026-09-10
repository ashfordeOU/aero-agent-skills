#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C requirement allocation.

Exercises scripts/e10_req_allocation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - clause 5.2.3.5
requires every requirement to be allocated to at least one function
and at least one product-tree element (CI); allocation to an unknown
function or element raises ValueError; a one-sided allocation (only a
function, or only an element) raises ValueError; coverage reporting
and function/element tracing reflect only complete allocations;
allocate_requirement never mutates the allocations mapping passed in.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_req_allocation_logic as ra  # noqa: E402


FUNCTIONS = ["attitude control", "power distribution", "thermal control"]
PRODUCT_TREE = ["ADCS unit", "PCDU", "thermal louvre"]


class AllocateRequirementTest(unittest.TestCase):
    def test_allocates_both_sides(self):
        allocations = ra.allocate_requirement(
            {}, "REQ-001", ["attitude control"], ["ADCS unit"], FUNCTIONS, PRODUCT_TREE,
        )
        self.assertEqual(
            allocations["REQ-001"],
            {"functions": ("attitude control",), "elements": ("ADCS unit",)},
        )

    def test_does_not_mutate_input_mapping(self):
        original = {}
        ra.allocate_requirement(
            original, "REQ-001", ["attitude control"], ["ADCS unit"], FUNCTIONS, PRODUCT_TREE,
        )
        self.assertEqual(original, {})

    def test_many_to_many_allocation(self):
        allocations = ra.allocate_requirement(
            {}, "REQ-002",
            ["attitude control", "power distribution"],
            ["ADCS unit", "PCDU"],
            FUNCTIONS, PRODUCT_TREE,
        )
        self.assertEqual(
            allocations["REQ-002"],
            {
                "functions": ("attitude control", "power distribution"),
                "elements": ("ADCS unit", "PCDU"),
            },
        )

    def test_unknown_function_raises(self):
        with self.assertRaises(ValueError):
            ra.allocate_requirement(
                {}, "REQ-003", ["propulsion"], ["ADCS unit"], FUNCTIONS, PRODUCT_TREE,
            )

    def test_unknown_element_raises(self):
        with self.assertRaises(ValueError):
            ra.allocate_requirement(
                {}, "REQ-004", ["attitude control"], ["battery"], FUNCTIONS, PRODUCT_TREE,
            )

    def test_function_only_raises(self):
        with self.assertRaises(ValueError):
            ra.allocate_requirement(
                {}, "REQ-005", ["attitude control"], [], FUNCTIONS, PRODUCT_TREE,
            )

    def test_element_only_raises(self):
        with self.assertRaises(ValueError):
            ra.allocate_requirement(
                {}, "REQ-006", [], ["ADCS unit"], FUNCTIONS, PRODUCT_TREE,
            )


class AllocationStatusTest(unittest.TestCase):
    def test_allocated(self):
        allocations = ra.allocate_requirement(
            {}, "REQ-001", ["attitude control"], ["ADCS unit"], FUNCTIONS, PRODUCT_TREE,
        )
        self.assertEqual(ra.allocation_status(allocations, "REQ-001"), "allocated")

    def test_unallocated(self):
        self.assertEqual(ra.allocation_status({}, "REQ-999"), "unallocated")


class CoverageReportTest(unittest.TestCase):
    def test_reports_allocated_and_unallocated_in_order(self):
        allocations = ra.allocate_requirement(
            {}, "REQ-001", ["attitude control"], ["ADCS unit"], FUNCTIONS, PRODUCT_TREE,
        )
        allocated, unallocated = ra.coverage_report(["REQ-001", "REQ-002"], allocations)
        self.assertEqual(allocated, ["REQ-001"])
        self.assertEqual(unallocated, ["REQ-002"])


class TracingTest(unittest.TestCase):
    def setUp(self):
        allocations = ra.allocate_requirement(
            {}, "REQ-001", ["attitude control"], ["ADCS unit"], FUNCTIONS, PRODUCT_TREE,
        )
        self.allocations = ra.allocate_requirement(
            allocations, "REQ-002",
            ["attitude control", "power distribution"],
            ["ADCS unit", "PCDU"],
            FUNCTIONS, PRODUCT_TREE,
        )

    def test_elements_for_function(self):
        self.assertEqual(
            ra.elements_for_function(self.allocations, "attitude control"),
            ["ADCS unit", "PCDU"],
        )

    def test_elements_for_function_with_no_requirements(self):
        self.assertEqual(ra.elements_for_function(self.allocations, "thermal control"), [])

    def test_requirements_for_element(self):
        self.assertEqual(
            ra.requirements_for_element(self.allocations, "ADCS unit"),
            ["REQ-001", "REQ-002"],
        )

    def test_requirements_for_element_with_none_allocated(self):
        self.assertEqual(ra.requirements_for_element(self.allocations, "thermal louvre"), [])

    def test_unallocated_functions(self):
        self.assertEqual(ra.unallocated_functions(FUNCTIONS, self.allocations), ["thermal control"])

    def test_unallocated_elements(self):
        self.assertEqual(ra.unallocated_elements(PRODUCT_TREE, self.allocations), ["thermal louvre"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
