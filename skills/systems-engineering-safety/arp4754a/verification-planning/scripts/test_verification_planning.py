#!/usr/bin/env python3
"""Gate 3 contract test: ARP4754A system verification planning.

Exercises scripts/verification_planning_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 (method
recognition for test, analysis, demonstration, inspection; method
acceptability per development assurance level; recommended methods
per level; independence for levels A and B; coverage ratio and
closure threshold; derived requirement coverage; plan closure
summary; invalid inputs raise ValueError).

Anchors:
- verification_method_ok("Test") = "test" (canonical lowercase)
- verification_method_ok("simulation") raises ValueError
- method_allowed("test", "A") is True; method_allowed("inspection", "A") is False
- method_allowed("inspection", "E") is True
- recommended_methods("A") = ("test", "analysis")
- recommended_methods("C") = ("test", "analysis", "demonstration")
- recommended_methods("E") = all four methods
- independence_required("A") and ("B") are True; ("C") and ("E") are False
- coverage_ratio(8, 10) = 0.8
- coverage_complete(0.8) is False; coverage_complete(1.0) is True
- coverage_complete(0.95, 0.95) is True
- derived_requirement_coverage_ok(9, 10, 0.9) is True; (8, 10, 0.9) is False
- verification_plan_closure([("R1", "A", "test"), ("R2", "B", None)])
  = total 2, planned 1, ratio 0.5, complete False
- verification_plan_closure with ("R1", "A", "inspection") raises ValueError
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import verification_planning_logic as vpl  # noqa: E402


class MethodRegistryTest(unittest.TestCase):
    def test_anchor_test_canonical(self):
        self.assertEqual(vpl.verification_method_ok("Test"), "test")

    def test_anchor_analysis_canonical(self):
        self.assertEqual(vpl.verification_method_ok("analysis"), "analysis")

    def test_all_four_methods_recognized(self):
        for method in ("test", "analysis", "demonstration", "inspection"):
            self.assertEqual(vpl.verification_method_ok(method), method)

    def test_simulation_is_not_a_top_level_method(self):
        with self.assertRaises(ValueError):
            vpl.verification_method_ok("simulation")

    def test_invalid_methods_raise(self):
        with self.assertRaises(ValueError):
            vpl.verification_method_ok("flight test")
        with self.assertRaises(ValueError):
            vpl.verification_method_ok("")
        with self.assertRaises(ValueError):
            vpl.verification_method_ok(None)


class AcceptabilityTest(unittest.TestCase):
    def test_level_a_accepts_test(self):
        self.assertTrue(vpl.method_allowed("test", "A"))

    def test_level_a_rejects_inspection(self):
        self.assertFalse(vpl.method_allowed("inspection", "A"))

    def test_level_b_rejects_demonstration(self):
        self.assertFalse(vpl.method_allowed("demonstration", "B"))

    def test_level_c_accepts_demonstration(self):
        self.assertTrue(vpl.method_allowed("demonstration", "C"))

    def test_level_e_accepts_every_method(self):
        for method in ("test", "analysis", "demonstration", "inspection"):
            self.assertTrue(vpl.method_allowed(method, "E"))

    def test_invalid_level_raises(self):
        with self.assertRaises(ValueError):
            vpl.method_allowed("test", "F")
        with self.assertRaises(ValueError):
            vpl.method_allowed("test", 1)


class RecommendedMethodsTest(unittest.TestCase):
    def test_anchor_level_a(self):
        self.assertEqual(vpl.recommended_methods("A"), ("test", "analysis"))

    def test_anchor_level_c(self):
        self.assertEqual(
            vpl.recommended_methods("C"), ("test", "analysis", "demonstration")
        )

    def test_anchor_level_e(self):
        self.assertEqual(
            vpl.recommended_methods("E"),
            ("test", "analysis", "demonstration", "inspection"),
        )

    def test_invalid_level_raises(self):
        with self.assertRaises(ValueError):
            vpl.recommended_methods("a")
        with self.assertRaises(ValueError):
            vpl.recommended_methods("")


class IndependenceTest(unittest.TestCase):
    def test_anchor_level_a_requires_independence(self):
        self.assertTrue(vpl.independence_required("A"))

    def test_level_b_requires_independence(self):
        self.assertTrue(vpl.independence_required("B"))

    def test_level_c_no_independence(self):
        self.assertFalse(vpl.independence_required("C"))

    def test_level_e_no_independence(self):
        self.assertFalse(vpl.independence_required("E"))

    def test_invalid_level_raises(self):
        with self.assertRaises(ValueError):
            vpl.independence_required("DAL A")


class CoverageTest(unittest.TestCase):
    def test_anchor_ratio(self):
        self.assertAlmostEqual(vpl.coverage_ratio(8, 10), 0.8)

    def test_full_coverage_ratio(self):
        self.assertAlmostEqual(vpl.coverage_ratio(10, 10), 1.0)

    def test_ratio_verified_above_total_raises(self):
        with self.assertRaises(ValueError):
            vpl.coverage_ratio(11, 10)

    def test_ratio_invalid_counts_raise(self):
        with self.assertRaises(ValueError):
            vpl.coverage_ratio(-1, 10)
        with self.assertRaises(ValueError):
            vpl.coverage_ratio(5, 0)
        with self.assertRaises(ValueError):
            vpl.coverage_ratio(5.0, 10)

    def test_complete_default_threshold(self):
        self.assertTrue(vpl.coverage_complete(1.0))
        self.assertFalse(vpl.coverage_complete(0.8))

    def test_complete_custom_threshold(self):
        self.assertTrue(vpl.coverage_complete(0.95, 0.95))
        self.assertFalse(vpl.coverage_complete(0.9, 0.95))

    def test_complete_invalid_threshold_raises(self):
        with self.assertRaises(ValueError):
            vpl.coverage_complete(0.5, 0.0)
        with self.assertRaises(ValueError):
            vpl.coverage_complete(0.5, 1.5)
        with self.assertRaises(ValueError):
            vpl.coverage_complete(0.5, -0.1)

    def test_derived_coverage_ok(self):
        self.assertTrue(vpl.derived_requirement_coverage_ok(9, 10, 0.9))
        self.assertFalse(vpl.derived_requirement_coverage_ok(8, 10, 0.9))


class ClosureTest(unittest.TestCase):
    def test_anchor_partial_closure(self):
        summary = vpl.verification_plan_closure(
            [("R1", "A", "test"), ("R2", "B", None)]
        )
        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["planned"], 1)
        self.assertEqual(summary["unplanned"], ["R2"])
        self.assertAlmostEqual(summary["ratio"], 0.5)
        self.assertFalse(summary["complete"])

    def test_full_closure(self):
        summary = vpl.verification_plan_closure(
            [("R1", "A", "test"), ("R2", "C", "analysis"), ("R3", "E", "inspection")]
        )
        self.assertTrue(summary["complete"])
        self.assertAlmostEqual(summary["ratio"], 1.0)

    def test_unplanned_list_order(self):
        summary = vpl.verification_plan_closure(
            [("R1", "B", None), ("R2", "A", "analysis"), ("R3", "D", None)]
        )
        self.assertEqual(summary["unplanned"], ["R1", "R3"])

    def test_method_not_allowed_for_level_raises(self):
        with self.assertRaises(ValueError):
            vpl.verification_plan_closure([("R1", "A", "inspection")])

    def test_invalid_entries_raise(self):
        with self.assertRaises(ValueError):
            vpl.verification_plan_closure([("R1", "F", "test")])
        with self.assertRaises(ValueError):
            vpl.verification_plan_closure([("R1", "A")])
        with self.assertRaises(ValueError):
            vpl.verification_plan_closure("not a list")


if __name__ == "__main__":
    unittest.main(verbosity=2)
