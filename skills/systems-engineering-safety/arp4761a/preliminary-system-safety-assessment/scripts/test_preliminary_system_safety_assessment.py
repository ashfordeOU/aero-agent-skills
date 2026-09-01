#!/usr/bin/env python3
"""Gate 3 contract test: PSSA per ARP4761A logic.

Exercises scripts/preliminary_system_safety_assessment_logic.py
(stdlib unittest, offline). Contract: docs/harness-contract.md gate
3. Covers severity-to-FDAL mapping with case and spacing tolerance,
the IDAL one-level reduction boundary, OR and AND quantitative
target allocation round-trips, the unallocatable target rejection
(AND with a target at or above 1.0), realized channel checks with
margin, the safety requirement text, the PSSA summary assembly, and
invalid-input edge cases.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import preliminary_system_safety_assessment_logic as pssa  # noqa: E402


class DalForSeverityTest(unittest.TestCase):
    def test_severity_to_fdal_mapping(self):
        cases = {
            "catastrophic": "A",
            "hazardous": "B",
            "major": "C",
            "minor": "D",
            "no-safety-effect": "E",
        }
        for severity, level in cases.items():
            result = pssa.dal_for_severity(severity)
            self.assertEqual(result["fdal"], level)
            self.assertEqual(result["idal"], level)

    def test_case_and_spacing_tolerance(self):
        result = pssa.dal_for_severity("  Catastrophic ")
        self.assertEqual(result["fdal"], "A")
        self.assertEqual(pssa.dal_for_severity("NO SAFETY EFFECT")["fdal"], "E")

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            pssa.dal_for_severity("severe")
        with self.assertRaises(ValueError):
            pssa.dal_for_severity(123)


class IdalForFdalTest(unittest.TestCase):
    def test_default_equal_to_fdal(self):
        for fdal in ("A", "B", "C", "D", "E"):
            self.assertEqual(pssa.idal_for_fdal(fdal), fdal)

    def test_one_level_reduction_when_allowed(self):
        self.assertEqual(pssa.idal_for_fdal("A", reduction_allowed=True), "B")
        self.assertEqual(pssa.idal_for_fdal("B", reduction_allowed=True), "C")
        self.assertEqual(pssa.idal_for_fdal("C", reduction_allowed=True), "D")
        self.assertEqual(pssa.idal_for_fdal("D", reduction_allowed=True), "E")

    def test_e_is_the_floor(self):
        self.assertEqual(pssa.idal_for_fdal("E", reduction_allowed=True), "E")

    def test_invalid_fdal_raises(self):
        with self.assertRaises(ValueError):
            pssa.idal_for_fdal("F")
        with self.assertRaises(ValueError):
            pssa.idal_for_fdal(None)


class AllocateSafetyTargetTest(unittest.TestCase):
    def test_or_allocates_equal_shares_by_sum(self):
        alloc = pssa.allocate_safety_target(1e-9, 3, "or")
        self.assertAlmostEqual(alloc["per_contributor"], 1e-9 / 3)
        self.assertAlmostEqual(alloc["check"], 1e-9, places=20)
        self.assertTrue(alloc["verified"])

    def test_and_allocates_equal_shares_by_product(self):
        alloc = pssa.allocate_safety_target(1e-9, 2, "and")
        self.assertAlmostEqual(alloc["per_contributor"], math.sqrt(1e-9))
        self.assertAlmostEqual(alloc["check"], 1e-9, places=20)
        self.assertTrue(alloc["verified"])

    def test_single_contributor_gets_full_target(self):
        or_alloc = pssa.allocate_safety_target(1e-9, 1, "or")
        and_alloc = pssa.allocate_safety_target(1e-9, 1, "and")
        self.assertAlmostEqual(or_alloc["per_contributor"], 1e-9)
        self.assertAlmostEqual(and_alloc["per_contributor"], 1e-9)

    def test_and_budget_exceeds_or_budget(self):
        and_alloc = pssa.allocate_safety_target(1e-9, 2, "and")
        or_alloc = pssa.allocate_safety_target(1e-9, 2, "or")
        self.assertGreater(and_alloc["per_contributor"], or_alloc["per_contributor"])

    def test_unallocatable_and_target_at_or_above_one(self):
        with self.assertRaises(ValueError):
            pssa.allocate_safety_target(1.0, 2, "and")
        with self.assertRaises(ValueError):
            pssa.allocate_safety_target(2.0, 2, "and")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pssa.allocate_safety_target(0.0, 2, "or")
        with self.assertRaises(ValueError):
            pssa.allocate_safety_target(-1e-9, 2, "or")
        with self.assertRaises(ValueError):
            pssa.allocate_safety_target(1e-9, 0, "or")
        with self.assertRaises(ValueError):
            pssa.allocate_safety_target(1e-9, 2, "xor")


class ChannelAllocationCheckTest(unittest.TestCase):
    def test_or_check_sums_rates(self):
        check = pssa.channel_allocation_check([3e-10, 4e-10], 1e-9, "or")
        self.assertAlmostEqual(check["total"], 7e-10)
        self.assertTrue(check["meets"])
        self.assertAlmostEqual(check["margin"], 1e-9 / 7e-10)

    def test_and_check_multiplies_rates(self):
        check = pssa.channel_allocation_check([1e-5, 2e-5], 1e-9, "and")
        self.assertAlmostEqual(check["total"], 2e-10)
        self.assertTrue(check["meets"])
        self.assertAlmostEqual(check["margin"], 5.0)

    def test_or_check_exceeding_target_fails(self):
        check = pssa.channel_allocation_check([8e-10, 8e-10], 1e-9, "or")
        self.assertFalse(check["meets"])
        self.assertLess(check["margin"], 1.0)

    def test_and_check_exceeding_target_fails(self):
        check = pssa.channel_allocation_check([1e-4, 1e-4], 1e-9, "and")
        self.assertFalse(check["meets"])

    def test_boundary_equal_to_target_meets(self):
        check = pssa.channel_allocation_check([5e-10, 5e-10], 1e-9, "or")
        self.assertTrue(check["meets"])
        self.assertAlmostEqual(check["margin"], 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            pssa.channel_allocation_check([], 1e-9, "or")
        with self.assertRaises(ValueError):
            pssa.channel_allocation_check([1e-9, 0.0], 1e-9, "or")
        with self.assertRaises(ValueError):
            pssa.channel_allocation_check([-1e-9], 1e-9, "or")
        with self.assertRaises(ValueError):
            pssa.channel_allocation_check([1e-9], 0.0, "or")
        with self.assertRaises(ValueError):
            pssa.channel_allocation_check([1e-9], 1e-9, "nand")


class SafetyRequirementTextTest(unittest.TestCase):
    def test_text_carries_condition_target_and_budget(self):
        text = pssa.safety_requirement_text(
            "loss of both primary flight control channels", 1e-9, 2, "and"
        )
        self.assertIn("loss of both primary flight control channels", text)
        self.assertIn("1e-09", text)
        self.assertIn("3.16e-05", text)
        self.assertIn("AND", text)

    def test_text_propagates_allocation_errors(self):
        with self.assertRaises(ValueError):
            pssa.safety_requirement_text("condition", 2.0, 2, "and")


class PssaSummaryTest(unittest.TestCase):
    OUTCOMES = [
        {
            "condition": "loss of both primary flight control channels",
            "severity": "catastrophic",
            "target": 1e-9,
            "channels": [1e-5, 2e-5],
            "gate": "and",
        },
        {
            "condition": "uncommanded full nose down pitch",
            "severity": "hazardous",
            "target": 1e-7,
            "channels": [8e-8, 8e-8],
            "gate": "or",
        },
    ]

    def test_summary_rows_are_deterministic_and_complete(self):
        rows = pssa.pssa_summary(self.OUTCOMES)
        self.assertEqual(len(rows), 2)
        first = rows[0]
        self.assertEqual(first["condition"], "loss of both primary flight control channels")
        self.assertEqual(first["fdal"], "A")
        self.assertEqual(first["idal"], "A")
        self.assertEqual(first["gate"], "and")
        self.assertTrue(first["meets"])
        self.assertAlmostEqual(first["margin"], 5.0)
        second = rows[1]
        self.assertEqual(second["fdal"], "B")
        self.assertFalse(second["meets"])
        for row in rows:
            self.assertIn("shall occur at no more than", row["requirement"])

    def test_summary_rejects_malformed_outcome(self):
        with self.assertRaises(ValueError):
            pssa.pssa_summary([{"severity": "major", "target": 1e-7,
                                "channels": [1e-8], "gate": "or"}])


if __name__ == "__main__":
    unittest.main(verbosity=2)
