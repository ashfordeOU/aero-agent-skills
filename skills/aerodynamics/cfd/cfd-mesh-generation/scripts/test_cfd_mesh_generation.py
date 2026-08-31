#!/usr/bin/env python3
"""Behavior contract tests for cfd-mesh-generation logic (gate 3).

Stdlib unittest, offline, deterministic. Run:
python3 skills/aerodynamics/cfd/cfd-mesh-generation/scripts/test_cfd_mesh_generation.py
"""

import math
import unittest

from cfd_mesh_generation_logic import (
    achieved_y_plus,
    estimate_cell_count,
    first_cell_height,
    first_cell_height_from_cf,
    grid_type_recommendation,
    prism_layer_count,
    quality_flags,
    refinement_sizes,
)


class TestFirstCellHeight(unittest.TestCase):
    def test_first_cell_height_numeric(self):
        # y+ = 1, u_tau = 1 m/s, nu = 1e-5 m^2/s -> y = 1e-5 m.
        self.assertAlmostEqual(first_cell_height(1.0, 1.0, 1e-5), 1e-5, places=12)
        # y+ = 30, u_tau = 0.5 m/s, nu = 1.5e-5 -> y = 9e-4 m.
        self.assertAlmostEqual(
            first_cell_height(30.0, 0.5, 1.5e-5), 9e-4, places=12
        )

    def test_first_cell_height_from_cf_numeric(self):
        # cf = 0.003, v_inf = 100 m/s -> u_tau = 100*sqrt(0.0015) = sqrt(15).
        # y+ = 1, nu = 1.5e-5 -> y = 1.5e-5/sqrt(15) ~ 3.87298e-6 m.
        expected = 1.5e-5 / math.sqrt(15.0)
        self.assertAlmostEqual(
            first_cell_height_from_cf(1.0, 0.003, 100.0, 1.5e-5),
            expected,
            places=12,
        )

    def test_first_cell_height_round_trip_through_y_plus(self):
        y = first_cell_height_from_cf(1.0, 0.003, 100.0, 1.5e-5)
        u_tau = 100.0 * math.sqrt(0.003 / 2.0)
        self.assertAlmostEqual(achieved_y_plus(y, u_tau, 1.5e-5), 1.0, places=9)

    def test_first_cell_height_edge_non_positive(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                first_cell_height(bad, 1.0, 1e-5)
            with self.assertRaises(ValueError):
                first_cell_height(1.0, bad, 1e-5)
            with self.assertRaises(ValueError):
                first_cell_height(1.0, 1.0, bad)


class TestPrismLayers(unittest.TestCase):
    def test_prism_layer_count_numeric(self):
        # h1 = 1e-5, H = 1e-2, r = 1.2:
        # n = log(1 + 0.2*1e-2/1e-5)/log(1.2) = log(201)/log(1.2) ~ 29.09 -> 30.
        self.assertEqual(prism_layer_count(1e-5, 1e-2, 1.2), 30)

    def test_prism_layer_count_edge_thin_layer(self):
        # Boundary layer no thicker than the first cell needs one layer.
        self.assertEqual(prism_layer_count(1e-5, 1e-5, 1.2), 1)
        self.assertEqual(prism_layer_count(1e-5, 9e-6, 1.2), 1)

    def test_prism_layer_count_edge_bad_growth(self):
        with self.assertRaises(ValueError):
            prism_layer_count(1e-5, 1e-2, 1.0)
        with self.assertRaises(ValueError):
            prism_layer_count(1e-5, 1e-2, 0.8)
        with self.assertRaises(ValueError):
            prism_layer_count(0.0, 1e-2, 1.2)


class TestGridType(unittest.TestCase):
    def test_grid_type_mapping(self):
        self.assertEqual(grid_type_recommendation("simple", True), "structured")
        self.assertEqual(grid_type_recommendation("simple", False), "structured")
        self.assertEqual(grid_type_recommendation("moderate", True), "hybrid")
        self.assertEqual(grid_type_recommendation("moderate", False), "unstructured")
        self.assertEqual(grid_type_recommendation("complex", True), "hybrid")
        self.assertEqual(grid_type_recommendation("complex", False), "unstructured")

    def test_grid_type_edge_invalid(self):
        with self.assertRaises(ValueError):
            grid_type_recommendation("bogus", False)
        with self.assertRaises(ValueError):
            grid_type_recommendation("complex", "yes")


class TestQualityFlags(unittest.TestCase):
    def test_quality_flags_pass(self):
        f = quality_flags(0.5, 45.0, 2.0)
        self.assertTrue(f["pass"])
        self.assertTrue(f["skewness_ok"])
        self.assertTrue(f["orthogonality_ok"])
        self.assertTrue(f["aspect_ratio_ok"])

    def test_quality_flags_each_metric_fails_independently(self):
        f = quality_flags(0.95, 45.0, 2.0)
        self.assertFalse(f["skewness_ok"])
        self.assertFalse(f["pass"])
        f = quality_flags(0.3, 5.0, 2.0)
        self.assertFalse(f["orthogonality_ok"])
        self.assertFalse(f["pass"])
        f = quality_flags(0.3, 45.0, 100.0)
        self.assertFalse(f["aspect_ratio_ok"])
        self.assertFalse(f["pass"])

    def test_quality_flags_boundary_layer_exempts_aspect_ratio(self):
        # High-aspect cells are legitimate in the boundary layer.
        f = quality_flags(0.3, 45.0, 100.0, boundary_layer_cell=True)
        self.assertTrue(f["aspect_ratio_ok"])
        self.assertTrue(f["pass"])

    def test_quality_flags_edge_invalid(self):
        with self.assertRaises(ValueError):
            quality_flags(1.5, 45.0, 2.0)
        with self.assertRaises(ValueError):
            quality_flags(-0.1, 45.0, 2.0)
        with self.assertRaises(ValueError):
            quality_flags(0.3, -5.0, 2.0)
        with self.assertRaises(ValueError):
            quality_flags(0.3, 45.0, 0.0)
        with self.assertRaises(ValueError):
            quality_flags(0.3, 45.0, 2.0, boundary_layer_cell="yes")


class TestDomainSizing(unittest.TestCase):
    def test_estimate_cell_count_numeric(self):
        self.assertEqual(estimate_cell_count(1.0, 1.0, 1.0, 0.1, 0.1, 0.1), 1000)
        self.assertEqual(estimate_cell_count(0.4, 1.0, 1.0, 0.1, 0.1, 0.1), 400)
        # Partial cells round up: 0.35/0.1 -> 4 cells per direction.
        self.assertEqual(estimate_cell_count(0.35, 0.35, 0.35, 0.1, 0.1, 0.1), 64)

    def test_estimate_cell_count_edge_invalid(self):
        with self.assertRaises(ValueError):
            estimate_cell_count(0.0, 1.0, 1.0, 0.1, 0.1, 0.1)
        with self.assertRaises(ValueError):
            estimate_cell_count(1.0, 1.0, 1.0, 0.0, 0.1, 0.1)


class TestRefinement(unittest.TestCase):
    def test_refinement_sizes_numeric(self):
        self.assertEqual(
            refinement_sizes(0.01, 3), [0.01, 0.005, 0.0025, 0.00125]
        )
        self.assertEqual(refinement_sizes(0.01, 0), [0.01])
        self.assertEqual(
            refinement_sizes(0.01, 2, ratio=3.0),
            [0.01, 0.01 / 3.0, 0.01 / 9.0],
        )

    def test_refinement_sizes_edge_invalid(self):
        with self.assertRaises(ValueError):
            refinement_sizes(0.01, 3, ratio=1.0)
        with self.assertRaises(ValueError):
            refinement_sizes(0.01, -1)
        with self.assertRaises(ValueError):
            refinement_sizes(0.0, 3)


if __name__ == "__main__":
    unittest.main()
