#!/usr/bin/env python3
"""Gate 3 contract test: airfoil section selection.

Exercises scripts/airfoil_selection_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - candidate
scoring by lift-to-drag ratio, thickness constraint checks, and
selection; invalid inputs raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import airfoil_selection_logic as sel  # noqa: E402


CANDIDATES = [
    {"id": "naca-0012", "cl": 0.82, "cd": 0.0079, "thickness": 0.12},
    {"id": "naca-2412", "cl": 0.95, "cd": 0.0085, "thickness": 0.12},
    {"id": "naca-23012", "cl": 1.0, "cd": 0.0090, "thickness": 0.12},
]


class LdRatioTest(unittest.TestCase):
    def test_ratio(self):
        self.assertAlmostEqual(sel.ld_ratio(0.82, 0.0079), 103.8, delta=0.5)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sel.ld_ratio(-0.1, 0.0079)
        with self.assertRaises(ValueError):
            sel.ld_ratio(0.82, 0.0)


class ThicknessTest(unittest.TestCase):
    def test_meets_requirement(self):
        self.assertTrue(sel.thickness_ok(0.12, 0.10))

    def test_fails_requirement(self):
        self.assertFalse(sel.thickness_ok(0.09, 0.10))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sel.thickness_ok(0.0, 0.10)


class SelectionTest(unittest.TestCase):
    def test_selects_best_ld_among_qualified(self):
        best = sel.select_airfoil(CANDIDATES, min_thickness=0.10)
        self.assertEqual(best, "naca-2412")

    def test_thickness_constraint_filters(self):
        thick_candidates = [
            {"id": "thin", "cl": 0.9, "cd": 0.007, "thickness": 0.06},
            {"id": "thick", "cl": 0.8, "cd": 0.008, "thickness": 0.15},
        ]
        self.assertEqual(sel.select_airfoil(thick_candidates, min_thickness=0.12),
                         "thick")

    def test_no_qualified_candidate_raises(self):
        with self.assertRaises(ValueError):
            sel.select_airfoil(CANDIDATES, min_thickness=0.20)

    def test_empty_candidates_raise(self):
        with self.assertRaises(ValueError):
            sel.select_airfoil([], min_thickness=0.10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
