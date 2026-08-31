#!/usr/bin/env python3
"""Gate 3 contract test: CFD convergence checks.

Exercises scripts/cfd_convergence_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - residual convergence
detection, CFL sanity, and mesh refinement convergence flags;
invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cfd_convergence_logic as cfd  # noqa: E402


class ResidualConvergenceTest(unittest.TestCase):
    def test_monotone_decrease_converged(self):
        history = [1e-1, 1e-2, 1e-3, 1e-4, 1e-5]
        self.assertTrue(cfd.residual_converged(history, tol=1e-4))

    def test_flat_residual_not_converged(self):
        history = [1e-3, 1e-3, 1e-3, 1e-3]
        self.assertFalse(cfd.residual_converged(history, tol=1e-4))

    def test_oscillating_not_converged(self):
        history = [1e-2, 1e-5, 1e-2, 1e-5]
        self.assertFalse(cfd.residual_converged(history, tol=1e-4))

    def test_short_history_raises(self):
        with self.assertRaises(ValueError):
            cfd.residual_converged([1e-1], tol=1e-4)

    def test_negative_residual_raises(self):
        with self.assertRaises(ValueError):
            cfd.residual_converged([1e-1, -1e-2, 1e-3], tol=1e-4)


class CflTest(unittest.TestCase):
    def test_explicit_cfl_ok(self):
        self.assertTrue(cfd.cfl_ok(0.8, explicit=True))
        self.assertFalse(cfd.cfl_ok(1.2, explicit=True))

    def test_implicit_cfl_ok(self):
        self.assertTrue(cfd.cfl_ok(1.5, explicit=False))
        self.assertFalse(cfd.cfl_ok(2.5, explicit=False))

    def test_invalid_cfl_raises(self):
        with self.assertRaises(ValueError):
            cfd.cfl_ok(0.0, explicit=True)
        with self.assertRaises(ValueError):
            cfd.cfl_ok(-1.0, explicit=True)


class MeshRefinementTest(unittest.TestCase):
    def test_small_change_converged(self):
        self.assertTrue(cfd.mesh_refinement_ok(0.02, threshold=0.05))

    def test_large_change_not_converged(self):
        self.assertFalse(cfd.mesh_refinement_ok(0.10, threshold=0.05))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cfd.mesh_refinement_ok(-0.01, threshold=0.05)
        with self.assertRaises(ValueError):
            cfd.mesh_refinement_ok(0.02, threshold=0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
