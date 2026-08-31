#!/usr/bin/env python3
"""Gate 3 contract test: composite laminate stiffness (CLT).

Exercises scripts/laminate_stiffness_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - ply stiffness,
rotated stiffness, and symmetric laminate A-matrix; invalid inputs
raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import laminate_stiffness_logic as clt  # noqa: E402

E1 = 135.0e9
E2 = 10.0e9
NU12 = 0.3
G12 = 5.0e9


class PlyStiffnessTest(unittest.TestCase):
    def test_unidirectional_q11(self):
        q11, q12, q22, q66 = clt.ply_stiffness(E1, E2, NU12, G12)
        expected_q11 = E1 / (1.0 - NU12 * (NU12 * E2 / E1))
        self.assertAlmostEqual(q11, expected_q11, delta=1e6)

    def test_q66_equals_g12(self):
        _, _, _, q66 = clt.ply_stiffness(E1, E2, NU12, G12)
        self.assertAlmostEqual(q66, G12)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            clt.ply_stiffness(0.0, E2, NU12, G12)
        with self.assertRaises(ValueError):
            clt.ply_stiffness(E1, E2, NU12, 0.0)


class RotatedStiffnessTest(unittest.TestCase):
    def test_zero_degrees_rotated_equals_material(self):
        q = clt.ply_stiffness(E1, E2, NU12, G12)
        r = clt.rotated_ply_stiffness(E1, E2, NU12, G12, 0.0)
        self.assertAlmostEqual(r[0], q[0], delta=1e6)
        self.assertAlmostEqual(r[3], q[2], delta=1e6)
        self.assertAlmostEqual(r[2], 0.0, places=3)  # q16 = 0
        self.assertAlmostEqual(r[4], 0.0, places=3)  # q26 = 0

    def test_ninety_degrees_swaps_directions(self):
        q = clt.ply_stiffness(E1, E2, NU12, G12)
        r = clt.rotated_ply_stiffness(E1, E2, NU12, G12, 90.0)
        self.assertAlmostEqual(r[0], q[2], delta=1e6)
        self.assertAlmostEqual(r[3], q[0], delta=1e6)

    def test_forty_five_degrees_coupling_nonzero(self):
        r = clt.rotated_ply_stiffness(E1, E2, NU12, G12, 45.0)
        self.assertNotAlmostEqual(r[2], 0.0, places=3)  # q16 nonzero


class LaminateAMatrixTest(unittest.TestCase):
    def test_unidirectional_a11(self):
        q11, _, _, _ = clt.ply_stiffness(E1, E2, NU12, G12)
        a = clt.laminate_a_matrix([(0.0, 0.001)], E1, E2, NU12, G12)
        self.assertAlmostEqual(a[0], q11 * 0.001, delta=1e4)

    def test_symmetric_cross_ply_no_coupling(self):
        plies = [(0.0, 0.0005), (90.0, 0.0005), (90.0, 0.0005), (0.0, 0.0005)]
        a = clt.laminate_a_matrix(plies, E1, E2, NU12, G12)
        self.assertAlmostEqual(a[2], 0.0, places=6)  # A16 = 0
        self.assertAlmostEqual(a[4], 0.0, places=6)  # A26 = 0
        self.assertGreater(a[0], 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            clt.laminate_a_matrix([], E1, E2, NU12, G12)
        with self.assertRaises(ValueError):
            clt.laminate_a_matrix([(0.0, -0.001)], E1, E2, NU12, G12)
        with self.assertRaises(ValueError):
            clt.laminate_a_matrix([(0.0, 0.001)], 0.0, E2, NU12, G12)


if __name__ == "__main__":
    unittest.main(verbosity=2)
