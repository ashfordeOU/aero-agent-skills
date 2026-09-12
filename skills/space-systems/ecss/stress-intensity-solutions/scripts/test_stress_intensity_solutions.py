"""
test_stress_intensity_solutions.py

Offline, deterministic stdlib unittest for stress_intensity_solutions_logic.py.
Run with: python3 test_stress_intensity_solutions.py
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from stress_intensity_solutions_logic import (
    CRACK_GEOMETRIES,
    K_corner_at_hole,
    K_edge_through,
    K_surface_semi_elliptical,
    K_through_finite_center,
    K_through_infinite,
    categorize_crack_geometry,
    check_lefm_dominance,
    select_and_compute_K,
    shape_factor_elliptic,
    validate_geometry_type,
)


class TestShapeFactor(unittest.TestCase):

    def test_shape_factor_circular_crack(self):
        # a/c = 1 → Q = 1 + 1.464 = 2.464
        Q = shape_factor_elliptic(1.0)
        self.assertAlmostEqual(Q, 2.464, places=3)

    def test_shape_factor_shallow_crack(self):
        # a/c → 0: Q → 1.0 (near-flat ellipse)
        Q = shape_factor_elliptic(0.01)
        self.assertAlmostEqual(Q, 1.0, delta=0.01)

    def test_shape_factor_clamped_at_one(self):
        # a/c > 1 should use min(a/c, 1.0) = 1.0 internally
        Q_at_one = shape_factor_elliptic(1.0)
        Q_above_one = shape_factor_elliptic(2.0)
        self.assertAlmostEqual(Q_at_one, Q_above_one, places=6)

    def test_shape_factor_invalid_zero(self):
        with self.assertRaises(ValueError):
            shape_factor_elliptic(0.0)


class TestThroughInfinite(unittest.TestCase):

    def test_basic_value(self):
        # K = sigma * sqrt(pi * a)
        sigma, a = 100.0, 0.01
        K = K_through_infinite(sigma, a)
        expected = sigma * math.sqrt(math.pi * a)
        self.assertAlmostEqual(K, expected, places=6)

    def test_linear_in_sigma(self):
        a = 0.005
        K1 = K_through_infinite(50.0, a)
        K2 = K_through_infinite(100.0, a)
        self.assertAlmostEqual(K2 / K1, 2.0, places=6)

    def test_scales_with_sqrt_a(self):
        sigma = 200.0
        K1 = K_through_infinite(sigma, 0.01)
        K4 = K_through_infinite(sigma, 0.04)
        self.assertAlmostEqual(K4 / K1, 2.0, places=6)

    def test_invalid_negative_sigma(self):
        with self.assertRaises(ValueError):
            K_through_infinite(-10.0, 0.01)

    def test_invalid_zero_a(self):
        with self.assertRaises(ValueError):
            K_through_infinite(100.0, 0.0)


class TestThroughFiniteCenter(unittest.TestCase):

    def test_exceeds_infinite_plate(self):
        # Feddersen correction is always > 1 for a/W > 0, so K_finite > K_infinite
        sigma, a, W = 100.0, 0.01, 0.1
        K_fin = K_through_finite_center(sigma, a, W)
        K_inf = K_through_infinite(sigma, a)
        self.assertGreater(K_fin, K_inf)

    def test_approaches_infinite_for_small_a_over_W(self):
        # Very small a/W → sec(pi*a/(2W)) → 1 → K_finite ≈ K_infinite
        sigma, a = 100.0, 1e-6
        W = 1.0
        K_fin = K_through_finite_center(sigma, a, W)
        K_inf = K_through_infinite(sigma, a)
        self.assertAlmostEqual(K_fin / K_inf, 1.0, delta=1e-5)

    def test_known_value_half_width(self):
        # a/W = 0.5 → arg = pi/4 → sec = 1/cos(pi/4) = sqrt(2) ≈ 1.4142
        sigma, a, W = 1.0, 0.5, 1.0
        K = K_through_finite_center(sigma, a, W)
        expected = sigma * math.sqrt(math.pi * a * (1.0 / math.cos(math.pi / 4)))
        self.assertAlmostEqual(K, expected, places=6)

    def test_a_equals_W_raises(self):
        with self.assertRaises(ValueError):
            K_through_finite_center(100.0, 0.1, 0.1)


class TestEdgeThrough(unittest.TestCase):

    def test_small_crack_approx_1_12(self):
        # At a/W → 0, F → 1.12, so K ≈ 1.12 * sigma * sqrt(pi * a)
        sigma, a, W = 100.0, 0.001, 1.0
        K = K_edge_through(sigma, a, W)
        K_expected = 1.12 * sigma * math.sqrt(math.pi * a)
        self.assertAlmostEqual(K / K_expected, 1.0, delta=0.001)

    def test_larger_crack_higher_K(self):
        sigma, W = 100.0, 1.0
        K_small = K_edge_through(sigma, 0.1, W)
        K_large = K_edge_through(sigma, 0.3, W)
        self.assertGreater(K_large, K_small)

    def test_a_over_W_at_limit_raises(self):
        with self.assertRaises(ValueError):
            K_edge_through(100.0, 0.6, 1.0)   # a/W = 0.6 exactly triggers the check

    def test_a_exceeds_W_raises(self):
        with self.assertRaises(ValueError):
            K_edge_through(100.0, 1.1, 1.0)


class TestSurfaceSemiElliptical(unittest.TestCase):

    def test_deepest_point_positive_K(self):
        K = K_surface_semi_elliptical(100.0, a=0.002, c=0.004, t=0.01, phi_deg=90.0)
        self.assertGreater(K, 0.0)

    def test_circular_crack_deepest_point(self):
        # a/c = 1 (circular front); F ≈ 1.04 at deepest point for small a/t
        K = K_surface_semi_elliptical(100.0, a=0.001, c=0.001, t=0.02, phi_deg=90.0)
        self.assertGreater(K, 0.0)

    def test_surface_end_lower_than_deepest_point(self):
        # For an elongated crack (a/c = 0.5, crack wider than deep), f_phi at the surface
        # end drops to 0.707, making K at the deepest point exceed the surface-end K.
        K_deep = K_surface_semi_elliptical(100.0, a=0.002, c=0.004, t=0.02, phi_deg=90.0)
        K_surf = K_surface_semi_elliptical(100.0, a=0.002, c=0.004, t=0.02, phi_deg=0.0)
        self.assertGreater(K_deep, K_surf)

    def test_a_equals_t_raises(self):
        with self.assertRaises(ValueError):
            K_surface_semi_elliptical(100.0, a=0.01, c=0.005, t=0.01, phi_deg=90.0)

    def test_phi_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            K_surface_semi_elliptical(100.0, a=0.002, c=0.004, t=0.01, phi_deg=95.0)

    def test_linear_in_sigma(self):
        K1 = K_surface_semi_elliptical(100.0, a=0.002, c=0.004, t=0.01, phi_deg=90.0)
        K2 = K_surface_semi_elliptical(200.0, a=0.002, c=0.004, t=0.01, phi_deg=90.0)
        self.assertAlmostEqual(K2 / K1, 2.0, places=6)


class TestCornerAtHole(unittest.TestCase):

    def test_small_crack_near_hole_large_Kt(self):
        # Very small a relative to R → Kt_eff ≈ 3 → large K
        K_small = K_corner_at_hole(100.0, a=0.001, R=0.01, t=0.005)
        K_large = K_corner_at_hole(100.0, a=0.003, R=0.01, t=0.005)
        # K grows with crack size despite Kt decay; sqrt(a) dominates at small a
        self.assertGreater(K_small, 0.0)
        self.assertGreater(K_large, 0.0)

    def test_a_exceeds_t_raises(self):
        with self.assertRaises(ValueError):
            K_corner_at_hole(100.0, a=0.006, R=0.01, t=0.005)

    def test_positive_output(self):
        K = K_corner_at_hole(150.0, a=0.002, R=0.008, t=0.01)
        self.assertGreater(K, 0.0)


class TestGeometryCategorization(unittest.TestCase):

    def test_through_infinite_no_extra_params(self):
        result = categorize_crack_geometry(a=0.01)
        self.assertEqual(result, "through_infinite")

    def test_through_finite_with_W(self):
        result = categorize_crack_geometry(a=0.01, W=0.1)
        self.assertEqual(result, "through_finite_center")

    def test_edge_through_with_is_edge_flag(self):
        result = categorize_crack_geometry(a=0.01, W=0.1, is_edge=True)
        self.assertEqual(result, "edge_through")

    def test_surface_with_c_and_t(self):
        result = categorize_crack_geometry(a=0.002, c=0.004, t=0.01)
        self.assertEqual(result, "surface_semi_elliptical")

    def test_corner_at_hole_with_flag(self):
        result = categorize_crack_geometry(a=0.002, c=0.002, t=0.005, at_hole=True)
        self.assertEqual(result, "corner_at_hole")

    def test_a_ge_t_surface_raises(self):
        with self.assertRaises(ValueError):
            categorize_crack_geometry(a=0.01, c=0.005, t=0.01)

    def test_a_ge_W_through_finite_raises(self):
        with self.assertRaises(ValueError):
            categorize_crack_geometry(a=0.1, W=0.05)

    def test_edge_missing_W_raises(self):
        with self.assertRaises(ValueError):
            categorize_crack_geometry(a=0.01, is_edge=True)

    def test_corner_missing_t_raises(self):
        with self.assertRaises(ValueError):
            categorize_crack_geometry(a=0.002, c=0.002, at_hole=True)


class TestGeometryTypeValidation(unittest.TestCase):

    def test_all_valid_types_pass(self):
        for g in CRACK_GEOMETRIES:
            validate_geometry_type(g)   # must not raise

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            validate_geometry_type("embedded_elliptical")


class TestDispatcher(unittest.TestCase):

    def test_through_infinite_dispatch(self):
        result = select_and_compute_K("through_infinite", 100.0, {"a": 0.01})
        self.assertIn("K", result)
        self.assertGreater(result["K"], 0.0)
        self.assertEqual(result["geometry"], "through_infinite")

    def test_through_finite_dispatch(self):
        result = select_and_compute_K(
            "through_finite_center", 100.0, {"a": 0.01, "W": 0.1}
        )
        self.assertGreater(result["K"], 0.0)
        self.assertIn("Feddersen", result["solution_ref"])

    def test_edge_dispatch(self):
        result = select_and_compute_K(
            "edge_through", 100.0, {"a": 0.02, "W": 0.2}
        )
        self.assertGreater(result["K"], 0.0)

    def test_surface_dispatch_default_phi(self):
        result = select_and_compute_K(
            "surface_semi_elliptical",
            100.0,
            {"a": 0.002, "c": 0.004, "t": 0.01},
        )
        self.assertGreater(result["K"], 0.0)
        self.assertIn("Newman-Raju", result["solution_ref"])

    def test_corner_dispatch(self):
        result = select_and_compute_K(
            "corner_at_hole", 100.0, {"a": 0.002, "R": 0.01, "t": 0.005}
        )
        self.assertGreater(result["K"], 0.0)

    def test_unknown_geometry_raises(self):
        with self.assertRaises(ValueError):
            select_and_compute_K("embedded_elliptical", 100.0, {"a": 0.01})

    def test_result_contains_params_used(self):
        result = select_and_compute_K("through_infinite", 50.0, {"a": 0.005})
        self.assertIn("params_used", result)
        self.assertEqual(result["params_used"]["sigma"], 50.0)


class TestLefmDominance(unittest.TestCase):

    def test_infinite_plate_ratio_is_one(self):
        sigma, a = 100.0, 0.01
        K = K_through_infinite(sigma, a)
        result = check_lefm_dominance(K, sigma, a)
        self.assertAlmostEqual(result["ratio"], 1.0, places=6)
        self.assertEqual(result["lefm_indicator"], "within_bounds")

    def test_K_over_Kref_positive(self):
        K = K_through_infinite(100.0, 0.01)
        result = check_lefm_dominance(K, 100.0, 0.01)
        self.assertGreater(result["K_over_Kref"], 0.0)

    def test_invalid_zero_K_raises(self):
        with self.assertRaises(ValueError):
            check_lefm_dominance(0.0, 100.0, 0.01)

    def test_very_large_K_flags_check(self):
        result = check_lefm_dominance(1e6, 1.0, 0.001)
        self.assertEqual(result["lefm_indicator"], "check_required")


if __name__ == "__main__":
    unittest.main()
