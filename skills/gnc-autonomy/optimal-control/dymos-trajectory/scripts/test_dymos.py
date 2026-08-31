#!/usr/bin/env python3
"""Gate 3 contract test: Dymos trajectory optimization.

Exercises scripts/dymos_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 — phase setup completeness
(5+ collocation nodes, initial/final bounds, objective), optimizer
convergence against iteration and tolerance limits, state continuity
across segment boundaries, total delta-v within a fraction of the
expected budget, and ValueError on invalid inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dymos_logic as dm  # noqa: E402


class PhaseSetupTest(unittest.TestCase):
    def test_complete_phase_ok(self):
        ok, reasons = dm.phase_setup_ok(15, True, True, True)
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_minimum_nodes_ok(self):
        ok, reasons = dm.phase_setup_ok(5, True, True, True)
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_below_minimum_nodes_not_ok(self):
        ok, reasons = dm.phase_setup_ok(4, True, True, True)
        self.assertFalse(ok)
        self.assertTrue(any("nodes" in r for r in reasons))

    def test_missing_objective_not_ok(self):
        ok, reasons = dm.phase_setup_ok(15, True, True, False)
        self.assertFalse(ok)
        self.assertTrue(any("objective" in r for r in reasons))

    def test_missing_bounds_not_ok(self):
        ok, reasons = dm.phase_setup_ok(15, False, False, True)
        self.assertFalse(ok)
        self.assertTrue(any("initial" in r for r in reasons))
        self.assertTrue(any("final" in r for r in reasons))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dm.phase_setup_ok("many", True, True, True)
        with self.assertRaises(ValueError):
            dm.phase_setup_ok(15, "yes", True, True)


class ConvergenceTest(unittest.TestCase):
    def test_converged_within_limits(self):
        res = dm.convergence_check(49, 1e-5)
        self.assertTrue(res["converged"])
        self.assertTrue(res["reason"])

    def test_boundary_converged(self):
        self.assertTrue(dm.convergence_check(50, 1e-4)["converged"])

    def test_iteration_limit_exceeded(self):
        res = dm.convergence_check(51, 1e-5)
        self.assertFalse(res["converged"])
        self.assertTrue("iterations" in res["reason"])

    def test_tolerance_exceeded(self):
        res = dm.convergence_check(10, 1e-3)
        self.assertFalse(res["converged"])
        self.assertTrue("tol" in res["reason"])

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            dm.convergence_check(-1, 1e-5)
        with self.assertRaises(ValueError):
            dm.convergence_check("fast", 1e-5)
        with self.assertRaises(ValueError):
            dm.convergence_check(10, -1e-5)


class StateContinuityTest(unittest.TestCase):
    def test_continuous_segments_ok(self):
        self.assertTrue(dm.state_continuity_ok(True))

    def test_discontinuous_segments_not_ok(self):
        self.assertFalse(dm.state_continuity_ok(False))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            dm.state_continuity_ok("yes")


class DeltaVSanityTest(unittest.TestCase):
    def test_within_tolerance(self):
        self.assertTrue(dm.trajectory_delta_v_sanity(9.0, 10.0, tol=0.10))
        self.assertTrue(dm.trajectory_delta_v_sanity(11.0, 10.0, tol=0.10))
        self.assertTrue(dm.trajectory_delta_v_sanity(10.0, 10.0, tol=0.10))

    def test_outside_tolerance(self):
        self.assertFalse(dm.trajectory_delta_v_sanity(8.5, 10.0, tol=0.10))
        self.assertFalse(dm.trajectory_delta_v_sanity(11.5, 10.0, tol=0.10))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            dm.trajectory_delta_v_sanity(9.0, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
