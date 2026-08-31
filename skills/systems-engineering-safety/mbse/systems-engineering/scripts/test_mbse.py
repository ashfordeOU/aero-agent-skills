#!/usr/bin/env python3
"""Gate 3 contract test: model-based systems engineering (MBSE).

Exercises scripts/mbse_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the MBSE workflow follows
an ordered stage sequence (requirements modeling through traceability);
every function must be allocated to a design element before closure;
traceability must be complete for safety-critical items; modeling
tasks map to open-source toolchains. Unknown inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mbse_logic as mb  # noqa: E402


class WorkflowTest(unittest.TestCase):
    def test_stages_are_ordered_and_unique(self):
        stages = mb.workflow_stages()
        self.assertEqual(stages[0], "requirements-modeling")
        self.assertEqual(stages[-1], "traceability")
        self.assertEqual(len(stages), len(set(stages)))


class AllocationTest(unittest.TestCase):
    def test_all_functions_allocated_closes(self):
        closed, unallocated = mb.allocation_closure(
            ["compute-position", "steer"], ["compute-position", "steer"]
        )
        self.assertTrue(closed)
        self.assertEqual(unallocated, [])

    def test_missing_allocation_stays_open(self):
        closed, unallocated = mb.allocation_closure(
            ["compute-position", "steer"], ["compute-position"]
        )
        self.assertFalse(closed)
        self.assertEqual(unallocated, ["steer"])


class TraceabilityTest(unittest.TestCase):
    def test_full_coverage_closes(self):
        self.assertEqual(mb.traceability_status(10, 10), "closed")
        self.assertEqual(mb.traceability_status(10, 10, critical=True), "closed")

    def test_critical_item_requires_full_closure(self):
        self.assertEqual(mb.traceability_status(9, 10, critical=True), "open")

    def test_non_critical_allows_small_gap(self):
        self.assertEqual(mb.traceability_status(9, 10, critical=False), "closed")

    def test_linked_exceeding_total_raises(self):
        with self.assertRaises(ValueError):
            mb.traceability_status(11, 10)


class ToolchainTest(unittest.TestCase):
    def test_modeling_task_maps_to_tool(self):
        self.assertEqual(mb.tool_for_task("functional-architecture"), "capella")
        self.assertEqual(mb.tool_for_task("architecture-analysis"), "osate")

    def test_unknown_task_raises(self):
        with self.assertRaises(ValueError):
            mb.tool_for_task("cooking")


if __name__ == "__main__":
    unittest.main(verbosity=2)
