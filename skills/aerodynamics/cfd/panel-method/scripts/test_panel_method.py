#!/usr/bin/env python3
"""Behavior contract tests for panel-method logic (gate 3).

Stdlib unittest, offline, deterministic. Run:
python3 skills/aerodynamics/cfd/panel-method/scripts/test_panel_method.py
"""

import math
import unittest

from panel_method_logic import (
    build_panels,
    cl_from_circulation,
    dirichlet_doublet_matrix,
    dirichlet_doublet_solution,
    flat_plate_circulation,
    force_coefficients,
    kutta_condition_check,
    neumann_source_solution,
    quad_panel_properties,
    solve_linear_system,
    source_influence_matrix,
    sphere_potential_flow_cp,
    sphere_source_strength,
    surface_velocity_and_cp,
    surface_velocity_from_doublets,
    tangent_influence_matrix,
)


def circle_points(n, radius=1.0):
    """Closed counter-clockwise polygon of n equal panels on a circle."""
    pts = [
        (radius * math.cos(2 * math.pi * k / n),
         radius * math.sin(2 * math.pi * k / n))
        for k in range(n)
    ]
    pts.append(pts[0])
    return pts


class TestBuildPanels(unittest.TestCase):
    def test_panel_geometry_numeric(self):
        panels = build_panels(circle_points(4))
        # Four points on the unit circle form a diamond (area 2.0).
        self.assertEqual(panels["signed_area"], 2.0)
        self.assertEqual(len(panels["panels"]), 4)
        for p in panels["panels"]:
            self.assertAlmostEqual(p["length"], math.sqrt(2.0), places=12)
        # Panel 0 runs (1,0)->(0,1): tangent (-1,1)/sqrt2, outward
        # normal (1,1)/sqrt2.
        bottom = panels["panels"][0]
        self.assertAlmostEqual(bottom["mid_x"], 0.5, places=12)
        self.assertAlmostEqual(bottom["mid_y"], 0.5, places=12)
        self.assertAlmostEqual(bottom["tx"], -1.0 / math.sqrt(2.0), places=12)
        self.assertAlmostEqual(bottom["ty"], 1.0 / math.sqrt(2.0), places=12)
        self.assertAlmostEqual(bottom["nx"], 1.0 / math.sqrt(2.0), places=12)
        self.assertAlmostEqual(bottom["ny"], 1.0 / math.sqrt(2.0), places=12)

    def test_build_panels_edge_invalid(self):
        with self.assertRaises(ValueError):
            build_panels([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])  # not closed
        with self.assertRaises(ValueError):
            build_panels([(0.0, 0.0), (1.0, 0.0), (0.0, 0.0)])  # 2 panels
        with self.assertRaises(ValueError):
            build_panels([(0.0, 0.0), (0.0, 0.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)])
        # Clockwise ordering (signed area negative).
        cw = circle_points(8)[::-1]
        with self.assertRaises(ValueError):
            build_panels(cw)


class TestSourceInfluence(unittest.TestCase):
    def test_diagonal_self_influence(self):
        panels = build_panels(circle_points(16))
        a = source_influence_matrix(panels)
        for i in range(16):
            self.assertAlmostEqual(a[i][i], 0.5, places=12)

    def test_off_diagonal_numeric(self):
        # Unit square (0,0)->(1,0)->(1,1)->(0,1), CCW. Panel 1 runs
        # (1,0)->(1,1): t=(0,1), n=(1,0). Control point 0 at (0.5, 0):
        # s = (P-A).t = 0, n = (P-A).n = -0.5, l = 1.
        # V_s = (1/4pi) ln((s^2+n^2)/((s-l)^2+n^2)) = (1/4pi) ln(0.2)
        #     ~ -0.128075
        # V_n = (1/2pi)(atan2(-0.5,-1) - atan2(-0.5,0)) ~ -0.1762125
        # Global velocity = V_s t + V_n n = (-0.1762125, -0.128075).
        # Control point 0's outward normal is (0,-1), so the normal
        # velocity at control point 0 from panel 1 is -V_s ~ +0.128075.
        pts = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0)]
        panels = build_panels(pts)
        a = source_influence_matrix(panels)
        self.assertAlmostEqual(a[0][1], 0.128075, places=5)

    def test_tangent_diagonal_zero(self):
        panels = build_panels(circle_points(16))
        b = tangent_influence_matrix(panels)
        for i in range(16):
            self.assertAlmostEqual(b[i][i], 0.0, places=12)


class TestLinearSystem(unittest.TestCase):
    def test_solve_numeric(self):
        # 2x2: 3x + 2y = 7, x - y = -1 -> x = 1, y = 2.
        sol = solve_linear_system([[3.0, 2.0], [1.0, -1.0]], [7.0, -1.0])
        self.assertAlmostEqual(sol[0], 1.0, places=12)
        self.assertAlmostEqual(sol[1], 2.0, places=12)

    def test_solve_edge_singular(self):
        with self.assertRaises(ValueError):
            solve_linear_system([[1.0, 2.0], [2.0, 4.0]], [1.0, 2.0])
        with self.assertRaises(ValueError):
            solve_linear_system([[1.0, 0.0]], [1.0, 0.0])  # rhs mismatch
        with self.assertRaises(ValueError):
            solve_linear_system([], [])


class TestNeumannSourceMethod(unittest.TestCase):
    def test_circle_matches_analytic_cylinder(self):
        # Potential flow over a cylinder: Cp = 1 - 4 sin^2(theta). The
        # constant-source panel method reproduces this to machine
        # precision for an inscribed polygon (verified: ~1e-14 at n=128).
        panels = build_panels(circle_points(128))
        sigma = neumann_source_solution(panels, 1.0, 0.0)
        res = surface_velocity_and_cp(panels, sigma, 1.0, 0.0)
        max_err = 0.0
        for i, p in enumerate(panels["panels"]):
            theta = math.atan2(p["mid_y"], p["mid_x"])
            cp_an = 1.0 - 4.0 * math.sin(theta) ** 2
            max_err = max(max_err, abs(res[i]["cp"] - cp_an))
        self.assertLess(max_err, 1e-9)

    def test_circle_stagnation_and_force(self):
        panels = build_panels(circle_points(128))
        sigma = neumann_source_solution(panels, 1.0, 0.0)
        res = surface_velocity_and_cp(panels, sigma, 1.0, 0.0)
        # Front stagnation panel: near-zero velocity, Cp near 1.
        self.assertGreater(res[0]["cp"], 0.99)
        fc = force_coefficients(panels, [r["cp"] for r in res], 2.0)
        # d'Alembert: no lift or drag in potential flow (symmetric body).
        self.assertAlmostEqual(fc["cl"], 0.0, places=10)
        self.assertLess(abs(fc["cd"]), 0.005)

    def test_symmetric_ellipse_zero_lift(self):
        n = 128
        pts = [
            (2.0 * math.cos(2 * math.pi * k / n),
             0.5 * math.sin(2 * math.pi * k / n))
            for k in range(n)
        ]
        pts.append(pts[0])
        panels = build_panels(pts)
        sigma = neumann_source_solution(panels, 1.0, 0.0)
        res = surface_velocity_and_cp(panels, sigma, 1.0, 0.0)
        fc = force_coefficients(panels, [r["cp"] for r in res], 4.0)
        self.assertAlmostEqual(fc["cl"], 0.0, places=9)

    def test_neumann_edge_invalid(self):
        panels = build_panels(circle_points(8))
        with self.assertRaises(ValueError):
            neumann_source_solution(panels, 0.0, 0.0)
        with self.assertRaises(ValueError):
            surface_velocity_and_cp(panels, [1.0], 1.0, 0.0)
        with self.assertRaises(ValueError):
            surface_velocity_and_cp(panels, [1.0] * 8, 0.0, 0.0)
        with self.assertRaises(ValueError):
            force_coefficients(panels, [1.0] * 8, 0.0)
        with self.assertRaises(ValueError):
            force_coefficients(panels, [1.0], 1.0)


class TestDirichletDoubletMethod(unittest.TestCase):
    def test_diagonal_self_influence(self):
        panels = build_panels(circle_points(16))
        d = dirichlet_doublet_matrix(panels)
        for i in range(16):
            self.assertAlmostEqual(d[i][i], 0.5, places=12)
        # Control points sit inside the polygon, so each row sums to 1.
        for row in d:
            self.assertAlmostEqual(sum(row), 1.0, places=9)

    def test_circle_matches_analytic_cylinder(self):
        # Doublet-only Dirichlet formulation: V_t = -d(mu)/ds converges
        # to the cylinder surface velocity -2 sin(theta) at O(delta^2).
        panels = build_panels(circle_points(128))
        mu = dirichlet_doublet_solution(panels, 1.0, 0.0)
        vt = surface_velocity_from_doublets(panels, mu)
        max_err = 0.0
        for i, p in enumerate(panels["panels"]):
            theta = math.atan2(p["mid_y"], p["mid_x"])
            max_err = max(max_err, abs(vt[i] - (-2.0 * math.sin(theta))))
        self.assertLess(max_err, 0.01)

    def test_solve_residual_exact(self):
        # The solved doublet strengths satisfy the Dirichlet condition
        # sum_j D_ij mu_j = -phi_inf_i to machine precision.
        panels = build_panels(circle_points(8))
        mu = dirichlet_doublet_solution(panels, 1.0, 0.0)
        d = dirichlet_doublet_matrix(panels)
        resid = 0.0
        for i, p in enumerate(panels["panels"]):
            s = sum(d[i][j] * mu[j] for j in range(8)) + p["mid_x"]
            resid = max(resid, abs(s))
        self.assertLess(resid, 1e-12)

    def test_dirichlet_edge_invalid(self):
        panels = build_panels(circle_points(8))
        with self.assertRaises(ValueError):
            dirichlet_doublet_solution(panels, 0.0, 0.0)
        with self.assertRaises(ValueError):
            surface_velocity_from_doublets(panels, [1.0])


class TestKuttaCondition(unittest.TestCase):
    def test_flat_plate_circulation_and_cl(self):
        # Thin-airfoil result: Gamma = pi c V sin(alpha), cl = 2 pi
        # sin(alpha). At 5 degrees: cl = 2 pi sin(5 deg).
        v_inf = 10.0
        chord = 1.0
        alpha = math.radians(5.0)
        gamma = flat_plate_circulation(alpha, chord, v_inf)
        self.assertAlmostEqual(
            gamma, math.pi * chord * v_inf * math.sin(alpha), places=12
        )
        cl = cl_from_circulation(gamma, chord, v_inf)
        self.assertAlmostEqual(cl, 2.0 * math.pi * math.sin(alpha), places=12)

    def test_kutta_check(self):
        # Equal trailing-edge velocities satisfy the Kutta condition.
        ok = kutta_condition_check(2.0, 2.0)
        self.assertTrue(ok["satisfied"])
        self.assertEqual(ok["velocity_jump"], 0.0)
        self.assertEqual(ok["equalized_velocity"], 2.0)
        # A jump of 2 needs equalization to the mean velocity.
        bad = kutta_condition_check(1.0, 3.0)
        self.assertFalse(bad["satisfied"])
        self.assertEqual(bad["velocity_jump"], 2.0)
        self.assertEqual(bad["equalized_velocity"], 2.0)
        # Tolerant check passes for a small residual jump.
        self.assertTrue(kutta_condition_check(1.0, 1.0005, tol=0.001)["satisfied"])

    def test_kutta_edge_invalid(self):
        with self.assertRaises(ValueError):
            kutta_condition_check(1.0, 2.0, tol=-1.0)
        with self.assertRaises(ValueError):
            flat_plate_circulation(0.1, 0.0, 10.0)
        with self.assertRaises(ValueError):
            flat_plate_circulation(0.1, 1.0, 0.0)
        with self.assertRaises(ValueError):
            cl_from_circulation(1.0, 0.0, 10.0)


class TestSphere3D(unittest.TestCase):
    def test_sphere_cp_values(self):
        # Analytic potential-flow sphere: Cp = 1 - (9/4) sin^2(theta).
        self.assertAlmostEqual(sphere_potential_flow_cp(0.0), 1.0, places=12)
        self.assertAlmostEqual(sphere_potential_flow_cp(90.0), -1.25, places=12)
        self.assertAlmostEqual(sphere_potential_flow_cp(180.0), 1.0, places=12)
        self.assertAlmostEqual(sphere_potential_flow_cp(30.0), 1.0 - 2.25 * 0.25, places=12)

    def test_sphere_source_strength(self):
        self.assertAlmostEqual(sphere_source_strength(0.0, 10.0), 20.0, places=12)
        self.assertAlmostEqual(sphere_source_strength(90.0, 10.0), 0.0, places=12)
        self.assertAlmostEqual(sphere_source_strength(180.0, 10.0), -20.0, places=12)

    def test_sphere_edge_invalid(self):
        with self.assertRaises(ValueError):
            sphere_potential_flow_cp(-1.0)
        with self.assertRaises(ValueError):
            sphere_potential_flow_cp(181.0)
        with self.assertRaises(ValueError):
            sphere_source_strength(90.0, 0.0)


class TestQuadPanel3D(unittest.TestCase):
    def test_square_panel(self):
        q = quad_panel_properties([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)])
        self.assertAlmostEqual(q["area"], 1.0, places=12)
        self.assertAlmostEqual(q["normal"][2], 1.0, places=12)
        self.assertAlmostEqual(q["centroid"][0], 0.5, places=12)
        self.assertAlmostEqual(q["centroid"][1], 0.5, places=12)

    def test_tilted_panel_unit_normal(self):
        # Diamond in the y-z plane ordered counter-clockwise when viewed
        # from +x: normal points along +x.
        q = quad_panel_properties([(0, 0, 1), (0, -1, 0), (0, 0, -1), (0, 1, 0)])
        self.assertAlmostEqual(q["area"], 2.0, places=12)
        self.assertAlmostEqual(q["normal"][0], 1.0, places=12)
        self.assertAlmostEqual(
            math.sqrt(sum(c * c for c in q["normal"])), 1.0, places=12
        )

    def test_quad_edge_invalid(self):
        with self.assertRaises(ValueError):
            quad_panel_properties([(0, 0, 0), (1, 0, 0), (1, 1, 0)])
        with self.assertRaises(ValueError):
            # Collinear vertices: zero area.
            quad_panel_properties(
                [(0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)]
            )


if __name__ == "__main__":
    unittest.main()
