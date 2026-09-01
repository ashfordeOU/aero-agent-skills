#!/usr/bin/env python3
"""Gate 3 contract test: 2D truss analysis logic.

Exercises scripts/truss_analysis_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - element stiffness
matrices from E, A, L and orientation, global stiffness assembly,
nodal displacement solve by Gaussian elimination with support
conditions, member axial forces, support reactions, and ValueError on
invalid input.

Physically meaningful anchors (verified by running the logic):
- Single bar along x, E = 200 GPa, A = 1e-3 m^2, L = 1 m, pinned at
  node 0 and axially loaded with 100 kN: u_x1 = 5e-4 m, member force
  +100 kN (tension), reaction R_0x = -100 kN.
- Symmetric three-bar truss, nodes (0,0), (4,3), (8,0) m, E = 200 GPa,
  A = 1e-3 m^2, 100 kN down at the apex, pin at node 0, vertical
  roller at node 2: displacements [0, 0, 1.3333e-3, -5.25e-3,
  2.6667e-3, 0] m, member forces [-83.333e3, -83.333e3, +66.667e3] N,
  reactions R_0y = R_2y = +50e3 N, R_0x = 0.
- A two-bar V arch with a vertical roller is a mechanism: the reduced
  system is singular and solve_displacements raises ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import truss_analysis_logic as mod  # noqa: E402

THREE_BAR_NODES = [(0.0, 0.0), (4.0, 3.0), (8.0, 0.0)]
THREE_BAR_ELEMENTS = [
    (0, 1, 200e9, 1e-3),
    (1, 2, 200e9, 1e-3),
    (0, 2, 200e9, 1e-3),
]
THREE_BAR_LOADS = {(1, "y"): -100e3}
THREE_BAR_CONSTRAINTS = [(0, "x"), (0, "y"), (2, "y")]


class ElementStiffnessMatrixTest(unittest.TestCase):
    def test_bar_along_x_axis_anchor(self):
        # theta = 0: k = EA/L * [[1,0,-1,0],[0,0,0,0],[-1,0,1,0],[0,0,0,0]].
        k = mod.element_stiffness_matrix(200e9, 1e-3, 1.0, 0.0)
        self.assertAlmostEqual(k[0][0], 2e8, delta=1e-3)
        self.assertAlmostEqual(k[0][1], 0.0, delta=1e-6)
        self.assertAlmostEqual(k[0][2], -2e8, delta=1e-3)
        self.assertAlmostEqual(k[1][1], 0.0, delta=1e-6)
        self.assertAlmostEqual(k[2][2], 2e8, delta=1e-3)

    def test_vertical_bar_stiffness(self):
        # theta = 90: only the y degrees of freedom carry stiffness.
        k = mod.element_stiffness_matrix(100e9, 2e-3, 2.0, 90.0)
        scale = 100e9 * 2e-3 / 2.0
        self.assertAlmostEqual(k[1][1], scale, delta=1e-3)
        self.assertAlmostEqual(k[1][3], -scale, delta=1e-3)
        self.assertAlmostEqual(k[0][0], 0.0, delta=1e-6)
        self.assertAlmostEqual(k[3][3], scale, delta=1e-3)

    def test_matrix_symmetric_with_zero_row_sums(self):
        k = mod.element_stiffness_matrix(70e9, 5e-4, 2.5, 36.87)
        for r in range(4):
            for c in range(4):
                self.assertAlmostEqual(k[r][c], k[c][r], delta=1e-6)
            self.assertAlmostEqual(sum(k[r]), 0.0, delta=1e-3)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mod.element_stiffness_matrix(0.0, 1e-3, 1.0, 0.0)  # E <= 0
        with self.assertRaises(ValueError):
            mod.element_stiffness_matrix(200e9, -1e-3, 1.0, 0.0)  # A <= 0
        with self.assertRaises(ValueError):
            mod.element_stiffness_matrix(200e9, 1e-3, 0.0, 0.0)  # L <= 0
        with self.assertRaises(ValueError):
            mod.element_stiffness_matrix(float("nan"), 1e-3, 1.0, 0.0)


class GaussianEliminationTest(unittest.TestCase):
    def test_known_system_anchor(self):
        x = mod.gaussian_elimination([[2, 1, 1], [1, 3, 2], [1, 0, 0]], [7, 13, 1])
        self.assertAlmostEqual(x[0], 1.0, delta=1e-9)
        self.assertAlmostEqual(x[1], 2.0, delta=1e-9)
        self.assertAlmostEqual(x[2], 3.0, delta=1e-9)

    def test_upper_triangular_system(self):
        x = mod.gaussian_elimination([[4.0, -2.0], [0.0, 3.0]], [2.0, 9.0])
        self.assertAlmostEqual(x[0], 2.0, delta=1e-9)
        self.assertAlmostEqual(x[1], 3.0, delta=1e-9)

    def test_singular_matrix_raises(self):
        with self.assertRaises(ValueError):
            mod.gaussian_elimination([[1.0, 2.0], [2.0, 4.0]], [3.0, 6.0])
        with self.assertRaises(ValueError):
            mod.gaussian_elimination([[1.0, 1.0, 0.0], [0.0, 0.0, 1.0], [2.0, 2.0, 0.0]], [1.0, 2.0, 3.0])

    def test_mismatched_sizes_raise(self):
        with self.assertRaises(ValueError):
            mod.gaussian_elimination([[1.0, 2.0], [2.0, 1.0]], [1.0, 2.0, 3.0])
        with self.assertRaises(ValueError):
            mod.gaussian_elimination([[1.0, 2.0, 3.0], [2.0, 1.0]], [1.0, 2.0])


class DisplacementSolveTest(unittest.TestCase):
    def test_single_bar_axial_displacement_anchor(self):
        # u = F L / (E A) = 1e5 * 1 / (200e9 * 1e-3) = 5e-4 m.
        u = mod.solve_displacements(
            mod.assemble_global_stiffness([(0.0, 0.0), (1.0, 0.0)], [(0, 1, 200e9, 1e-3)]),
            [0.0, 0.0, 100e3, 0.0],
            [(0, "x"), (0, "y"), (1, "y")],
        )
        self.assertAlmostEqual(u[2], 5e-4, delta=1e-12)
        self.assertAlmostEqual(u[3], 0.0, delta=1e-12)
        self.assertAlmostEqual(u[0], 0.0, delta=1e-12)

    def test_three_bar_truss_apex_displacement_anchor(self):
        r = mod.truss_analysis(
            THREE_BAR_NODES, THREE_BAR_ELEMENTS, THREE_BAR_LOADS, THREE_BAR_CONSTRAINTS
        )
        u = r["displacements"]
        self.assertAlmostEqual(u[2], 1.3333e-3, delta=1e-6)  # apex u_x
        self.assertAlmostEqual(u[3], -5.25e-3, delta=1e-6)  # apex u_y
        self.assertAlmostEqual(u[4], 2.6667e-3, delta=1e-6)  # roller u_x
        self.assertAlmostEqual(u[5], 0.0, delta=1e-12)  # roller u_y fixed

    def test_stiffer_bars_halve_displacements(self):
        # Doubling E doubles every bar stiffness: displacements halve.
        r_base = mod.truss_analysis(
            THREE_BAR_NODES, THREE_BAR_ELEMENTS, THREE_BAR_LOADS, THREE_BAR_CONSTRAINTS
        )
        r_stiff = mod.truss_analysis(
            THREE_BAR_NODES,
            [(0, 1, 400e9, 1e-3), (1, 2, 400e9, 1e-3), (0, 2, 400e9, 1e-3)],
            THREE_BAR_LOADS,
            THREE_BAR_CONSTRAINTS,
        )
        self.assertAlmostEqual(r_stiff["displacements"][3], 0.5 * r_base["displacements"][3], delta=1e-9)

    def test_zero_load_gives_zero_displacement(self):
        r = mod.truss_analysis(THREE_BAR_NODES, THREE_BAR_ELEMENTS, {}, THREE_BAR_CONSTRAINTS)
        for v in r["displacements"]:
            self.assertAlmostEqual(v, 0.0, delta=1e-12)
        for f in r["member_forces"]:
            self.assertAlmostEqual(f, 0.0, delta=1e-6)

    def test_mechanism_raises_singular(self):
        # Two-bar V arch with a vertical roller has a zero-stiffness
        # mode: the reduced system is singular.
        with self.assertRaises(ValueError):
            mod.truss_analysis(
                [(0.0, 0.0), (4.0, 3.0), (8.0, 0.0)],
                [(0, 1, 200e9, 1e-3), (1, 2, 200e9, 1e-3)],
                {(1, "y"): -100e3},
                [(0, "x"), (0, "y"), (2, "y")],
            )

    def test_all_dofs_constrained_returns_zeros(self):
        u = mod.solve_displacements(
            mod.assemble_global_stiffness([(0.0, 0.0), (1.0, 0.0)], [(0, 1, 200e9, 1e-3)]),
            [0.0, 0.0, 5e4, 5e4],
            [(0, "x"), (0, "y"), (1, "x"), (1, "y")],
        )
        self.assertEqual(u, [0.0, 0.0, 0.0, 0.0])


class MemberForcesTest(unittest.TestCase):
    def test_three_bar_truss_member_forces_anchor(self):
        r = mod.truss_analysis(
            THREE_BAR_NODES, THREE_BAR_ELEMENTS, THREE_BAR_LOADS, THREE_BAR_CONSTRAINTS
        )
        self.assertAlmostEqual(r["member_forces"][0], -83333.3333, delta=1e-2)
        self.assertAlmostEqual(r["member_forces"][1], -83333.3333, delta=1e-2)
        self.assertAlmostEqual(r["member_forces"][2], 66666.6667, delta=1e-2)

    def test_single_bar_tension_positive(self):
        r = mod.truss_analysis(
            [(0.0, 0.0), (1.0, 0.0)],
            [(0, 1, 200e9, 1e-3)],
            {(1, "x"): 100e3},
            [(0, "x"), (0, "y"), (1, "y")],
        )
        self.assertAlmostEqual(r["member_forces"][0], 100e3, delta=1e-3)

    def test_member_forces_match_equilibrium(self):
        # Vertical joint equilibrium at the apex: the signed vertical
        # components 0.6*(F0 + F1) of the two bar forces equal the
        # applied load (-100 kN), so 0.6*(F0 + F1) = -P.
        r = mod.truss_analysis(
            THREE_BAR_NODES, THREE_BAR_ELEMENTS, THREE_BAR_LOADS, THREE_BAR_CONSTRAINTS
        )
        f0, f1 = r["member_forces"][0], r["member_forces"][1]
        self.assertAlmostEqual(0.6 * (f0 + f1), -100e3, delta=1e-2)


class ReactionForcesTest(unittest.TestCase):
    def test_three_bar_truss_reactions_anchor(self):
        r = mod.truss_analysis(
            THREE_BAR_NODES, THREE_BAR_ELEMENTS, THREE_BAR_LOADS, THREE_BAR_CONSTRAINTS
        )
        self.assertAlmostEqual(r["reactions"][(0, "x")], 0.0, delta=1e-6)
        self.assertAlmostEqual(r["reactions"][(0, "y")], 50e3, delta=1e-6)
        self.assertAlmostEqual(r["reactions"][(2, "y")], 50e3, delta=1e-6)

    def test_single_bar_reaction_opposes_load(self):
        r = mod.truss_analysis(
            [(0.0, 0.0), (1.0, 0.0)],
            [(0, 1, 200e9, 1e-3)],
            {(1, "x"): 100e3},
            [(0, "x"), (0, "y"), (1, "y")],
        )
        self.assertAlmostEqual(r["reactions"][(0, "x")], -100e3, delta=1e-3)
        self.assertAlmostEqual(r["reactions"][(0, "y")], 0.0, delta=1e-6)

    def test_global_equilibrium_holds(self):
        # Sum of support reactions plus applied loads must vanish.
        r = mod.truss_analysis(
            THREE_BAR_NODES, THREE_BAR_ELEMENTS, THREE_BAR_LOADS, THREE_BAR_CONSTRAINTS
        )
        fx = sum(v for (nd, ax), v in r["reactions"].items() if ax == "x")
        fy = sum(v for (nd, ax), v in r["reactions"].items() if ax == "y")
        fy += THREE_BAR_LOADS[(1, "y")]
        self.assertAlmostEqual(fx, 0.0, delta=1e-6)
        self.assertAlmostEqual(fy, 0.0, delta=1e-6)


class ValidationTest(unittest.TestCase):
    def test_invalid_elements_raise(self):
        good = THREE_BAR_NODES
        with self.assertRaises(ValueError):
            mod.assemble_global_stiffness(good, [(0, 1, -200e9, 1e-3)])  # E <= 0
        with self.assertRaises(ValueError):
            mod.assemble_global_stiffness(good, [(0, 1, 200e9, 0.0)])  # A <= 0
        with self.assertRaises(ValueError):
            mod.assemble_global_stiffness(good, [(0, 0, 200e9, 1e-3)])  # self loop
        with self.assertRaises(ValueError):
            mod.assemble_global_stiffness(good, [(0, 5, 200e9, 1e-3)])  # out of range
        with self.assertRaises(ValueError):
            mod.assemble_global_stiffness([(0.0, 0.0), (0.0, 0.0)], [(0, 1, 200e9, 1e-3)])
        with self.assertRaises(ValueError):
            mod.assemble_global_stiffness([(0.0, 0.0)], [(0, 0, 200e9, 1e-3)])  # one node

    def test_invalid_loads_and_constraints_raise(self):
        with self.assertRaises(ValueError):
            mod.truss_analysis(
                THREE_BAR_NODES, THREE_BAR_ELEMENTS, {(1, "z"): 1.0}, THREE_BAR_CONSTRAINTS
            )
        with self.assertRaises(ValueError):
            mod.truss_analysis(
                THREE_BAR_NODES, THREE_BAR_ELEMENTS, {(9, "y"): 1.0}, THREE_BAR_CONSTRAINTS
            )
        with self.assertRaises(ValueError):
            mod.truss_analysis(
                THREE_BAR_NODES, THREE_BAR_ELEMENTS, {(1, "y"): float("inf")}, THREE_BAR_CONSTRAINTS
            )
        with self.assertRaises(ValueError):
            mod.truss_analysis(THREE_BAR_NODES, THREE_BAR_ELEMENTS, THREE_BAR_LOADS, [])
        with self.assertRaises(ValueError):
            mod.truss_analysis(
                THREE_BAR_NODES, THREE_BAR_ELEMENTS, THREE_BAR_LOADS, [(2, "z")]
            )
        with self.assertRaises(ValueError):
            mod.truss_analysis(
                THREE_BAR_NODES, THREE_BAR_ELEMENTS, THREE_BAR_LOADS, [(9, "x")]
            )

    def test_displacement_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            mod.member_forces(THREE_BAR_NODES, THREE_BAR_ELEMENTS, [0.0, 0.0, 0.0])
        with self.assertRaises(ValueError):
            mod.reaction_forces(
                THREE_BAR_NODES, THREE_BAR_ELEMENTS, [0.0, 0.0, 0.0], THREE_BAR_CONSTRAINTS
            )

    def test_invalid_force_vector_raises(self):
        K = mod.assemble_global_stiffness(
            [(0.0, 0.0), (1.0, 0.0)], [(0, 1, 200e9, 1e-3)]
        )
        with self.assertRaises(ValueError):
            mod.solve_displacements(K, [0.0, 0.0, float("nan"), 0.0], [(0, "x"), (0, "y")])
        with self.assertRaises(ValueError):
            mod.solve_displacements(K, [1.0, 2.0], [(0, "x"), (0, "y")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
