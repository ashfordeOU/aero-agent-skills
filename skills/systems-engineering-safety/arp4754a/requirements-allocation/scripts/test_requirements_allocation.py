#!/usr/bin/env python3
"""Gate 3 contract test: ARP4754A requirements allocation.

Exercises scripts/requirements_allocation_logic.py (stdlib unittest,
offline). Contract: allocate maps a requirement to one item and raises
AllocationConflictError on a second allocation to a different item;
coverage returns the allocated and unallocated lists with the ratio;
unallocated_requirements lists the missing ids; requirements_by_item
and group_by_item group the register per item; validate_items rejects
items outside the design breakdown.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requirements_allocation_logic as alloc  # noqa: E402

REQUIREMENT_IDS = ["R-100", "R-101", "R-102", "R-103"]


class AllocateTest(unittest.TestCase):
    def test_allocate_records_mapping(self):
        reg = {}
        alloc.allocate(reg, "R-100", "LRU-1")
        self.assertEqual(reg, {"R-100": "LRU-1"})

    def test_same_item_reallocation_is_idempotent(self):
        reg = {}
        alloc.allocate(reg, "R-100", "LRU-1")
        alloc.allocate(reg, "R-100", "LRU-1")
        self.assertEqual(reg, {"R-100": "LRU-1"})

    def test_second_allocation_to_different_item_raises(self):
        reg = {}
        alloc.allocate(reg, "R-100", "LRU-1")
        with self.assertRaises(alloc.AllocationConflictError):
            alloc.allocate(reg, "R-100", "LRU-2")


class CoverageTest(unittest.TestCase):
    def setUp(self):
        self.reg = {}
        alloc.allocate(self.reg, "R-100", "LRU-1")
        alloc.allocate(self.reg, "R-102", "LRU-2")

    def test_partial_coverage_lists_both_sides(self):
        allocated, unallocated, ratio = alloc.coverage(self.reg, REQUIREMENT_IDS)
        self.assertEqual(allocated, ["R-100", "R-102"])
        self.assertEqual(unallocated, ["R-101", "R-103"])
        self.assertAlmostEqual(ratio, 0.5)

    def test_full_coverage_ratio_is_one(self):
        reg = dict(self.reg)
        alloc.allocate(reg, "R-101", "LRU-1")
        alloc.allocate(reg, "R-103", "LRU-2")
        allocated, unallocated, ratio = alloc.coverage(reg, REQUIREMENT_IDS)
        self.assertEqual(unallocated, [])
        self.assertEqual(ratio, 1.0)

    def test_empty_requirement_set_is_full_coverage(self):
        _, unallocated, ratio = alloc.coverage({}, [])
        self.assertEqual(unallocated, [])
        self.assertEqual(ratio, 1.0)

    def test_unallocated_requirements_list_is_sorted(self):
        self.assertEqual(
            alloc.unallocated_requirements(self.reg, REQUIREMENT_IDS),
            ["R-101", "R-103"],
        )


class GroupingTest(unittest.TestCase):
    def setUp(self):
        self.reg = {}
        alloc.allocate(self.reg, "R-103", "LRU-2")
        alloc.allocate(self.reg, "R-100", "LRU-1")
        alloc.allocate(self.reg, "R-102", "LRU-2")

    def test_requirements_by_item_sorted(self):
        self.assertEqual(alloc.requirements_by_item(self.reg, "LRU-2"),
                         ["R-102", "R-103"])
        self.assertEqual(alloc.requirements_by_item(self.reg, "LRU-1"),
                         ["R-100"])

    def test_group_by_item_builds_item_sets(self):
        grouped = alloc.group_by_item(self.reg)
        self.assertEqual(grouped, {"LRU-1": ["R-100"],
                                   "LRU-2": ["R-102", "R-103"]})

    def test_validate_items_accepts_known_items(self):
        self.assertTrue(
            alloc.validate_items(self.reg, ["LRU-1", "LRU-2"])
        )

    def test_validate_items_rejects_unknown_item(self):
        with self.assertRaises(ValueError):
            alloc.validate_items(self.reg, ["LRU-1"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
