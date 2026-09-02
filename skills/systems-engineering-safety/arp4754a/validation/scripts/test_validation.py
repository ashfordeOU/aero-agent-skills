#!/usr/bin/env python3
"""Gate 3 contract test: ARP4754A requirements validation.

Exercises scripts/validation_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - validation method checks,
FDAL-based independence requirements, and validation closure
accounting; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import validation_logic as vl  # noqa: E402


class ValidationMethodTest(unittest.TestCase):
    def test_known_methods_ok(self):
        for method in ("analysis", "simulation", "test", "demonstration", "inspection"):
            self.assertEqual(vl.validate_method_ok(method), True)

    def test_unknown_method_raises(self):
        with self.assertRaises(ValueError):
            vl.validate_method_ok("opinion")


class IndependenceTest(unittest.TestCase):
    def test_levels_a_b_require_independent_validation(self):
        self.assertTrue(vl.independence_required("A"))
        self.assertTrue(vl.independence_required("B"))

    def test_levels_c_d_e_do_not(self):
        for fdal in ("C", "D", "E"):
            self.assertFalse(vl.independence_required(fdal))

    def test_invalid_fdal_raises(self):
        with self.assertRaises(ValueError):
            vl.independence_required("F")


class ValidationClosureTest(unittest.TestCase):
    def test_full_closure_ready(self):
        reqs = [
            ("R1", True, "analysis"),
            ("R2", True, "test"),
            ("R3", True, "simulation"),
            ("R4", True, "analysis"),
        ]
        ready, score = vl.validation_closure(reqs)
        self.assertTrue(ready)
        self.assertAlmostEqual(score, 1.0)

    def test_partial_closure_not_ready(self):
        reqs = [
            ("R1", True, "analysis"),
            ("R2", False, "analysis"),
        ]
        ready, score = vl.validation_closure(reqs)
        self.assertFalse(ready)
        self.assertAlmostEqual(score, 0.5)

    def test_missing_method_raises(self):
        with self.assertRaises(ValueError):
            vl.validation_closure([("R1", True, "opinion")])

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            vl.validation_closure([])


if __name__ == "__main__":
    unittest.main(verbosity=2)
