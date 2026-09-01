#!/usr/bin/env python3
"""Gate 3 contract test: vortex lattice method for straight wings.

Exercises scripts/vortex_lattice_method_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - horseshoe vortex
panel lattice construction, Biot-Savart influence coefficients,
circulation solution, spanwise lift distribution, downwash angles, and
induced drag; invalid inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import vortex_lattice_method_logic as vlm  # noqa: E402


def lifting_line_cl(span, alpha_deg, a0=2.0 * math.pi):
    """Prandtl lifting-line lift coefficient for a rectangular wing
    with section slope a0 and span efficiency 1 (reference value)."""
    ar = span * span / span  # rectangular wing, chord 1
    return a0 * math.radians(alpha_deg) / (1.0 + a0 / (math.pi * ar))


class BiotSavartTest(unittest.TestCase):
    def test_segment_known_value(self):
        # Segment (0,0,0) -> (1,0,0), gamma=1, point (0,0.3,0):
        # w = gamma / (4*pi*h) * (cos a1 + cos a2) with h=0.3, a1=90 deg,
        # cos a2 = 1/sqrt(1+0.3^2).
        v = vlm.segment_velocity((0.0, 0.3, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 1.0)
        expected = 1.0 / (4.0 * math.pi * 0.3) * (1.0 / math.sqrt(1.0 + 0.09))
        self.assertAlmostEqual(v[2], expected, places=9)
        self.assertEqual(v[0], 0.0)
        self.assertEqual(v[1], 0.0)

    def test_leg_known_value(self):
        # Semi-infinite leg from (0,0,0) along +x at point (0.7,0.4,0):
        # w = gamma/(4*pi*y) * (1 + x/sqrt(x^2+y^2)), verified by direct
        # Biot-Savart integration in the long-segment limit.
        v = vlm.trailing_leg_velocity((0.7, 0.4, 0.0), (0.0, 0.0, 0.0), 1.0)
        expected = 1.0 / (4.0 * math.pi * 0.4) * (
            1.0 + 0.7 / math.sqrt(0.7 * 0.7 + 0.4 * 0.4)
        )
        self.assertAlmostEqual(v[2], expected, places=9)

    def test_horseshoe_decomposition(self):
        point = (0.6, 0.4, 0.0)
        start = (0.0, 0.2, 0.0)
        end = (0.0, 0.8, 0.0)
        v = vlm.horseshoe_velocity(point, start, end, 1.0, root_leg=True)
        v_bound = vlm.segment_velocity(point, start, end, 1.0)
        v_tip = vlm.trailing_leg_velocity(point, end, 1.0, (1.0, 0.0, 0.0))
        v_root = vlm.trailing_leg_velocity(point, start, 1.0, (-1.0, 0.0, 0.0))
        for a, b in zip(v, (v_bound[0] + v_tip[0] + v_root[0],
                            v_bound[1] + v_tip[1] + v_root[1],
                            v_bound[2] + v_tip[2] + v_root[2])):
            self.assertAlmostEqual(a, b, places=12)

    def test_horseshoe_root_leg_off(self):
        point = (0.6, 0.4, 0.0)
        start = (0.0, 0.2, 0.0)
        end = (0.0, 0.8, 0.0)
        v = vlm.horseshoe_velocity(point, start, end, 1.0, root_leg=False)
        v_bound = vlm.segment_velocity(point, start, end, 1.0)
        v_tip = vlm.trailing_leg_velocity(point, end, 1.0, (1.0, 0.0, 0.0))
        self.assertAlmostEqual(v[2], v_bound[2] + v_tip[2], places=12)

    def test_segment_on_line_raises(self):
        with self.assertRaises(ValueError):
            vlm.segment_velocity((0.5, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 1.0)

    def test_leg_on_line_raises(self):
        with self.assertRaises(ValueError):
            vlm.trailing_leg_velocity((2.0, 0.0, 0.0), (0.0, 0.0, 0.0), 1.0)

    def test_segment_endpoint_raises(self):
        with self.assertRaises(ValueError):
            vlm.segment_velocity((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 1.0)


class WingModelTest(unittest.TestCase):
    def test_build_wing_geometry(self):
        w = vlm.build_wing(8.0, 1.0, 1.0, n_panels=4)
        self.assertEqual(len(w["panels"]), 4)
        self.assertAlmostEqual(w["area"], 8.0)
        self.assertAlmostEqual(w["aspect_ratio"], 8.0)
        self.assertEqual(w["panels"][0]["root_leg"], False)
        self.assertEqual(w["panels"][1]["root_leg"], True)
        # control points sit at the three-quarter chord (x = c/2)
        self.assertAlmostEqual(w["panels"][0]["control"][0], 0.5)
        self.assertAlmostEqual(w["panels"][2]["control"][1], 2.5)

    def test_influence_matrix_shape_and_sign(self):
        w = vlm.build_wing(8.0, 1.0, 1.0, n_panels=4)
        A = vlm.influence_matrix(w)
        self.assertEqual(len(A), 4)
        self.assertTrue(all(len(row) == 4 for row in A))
        # self influence is a downwash (negative z) for positive circulation
        self.assertLess(A[0][0], 0.0)
        self.assertLess(A[2][2], 0.0)


class CirculationSolutionTest(unittest.TestCase):
    def test_cl_positive_and_monotonic(self):
        w = vlm.build_wing(8.0, 1.0, 1.0, n_panels=4)
        cl2 = vlm.wing_coefficients(w, 50.0, 2.0)["cl"]
        cl5 = vlm.wing_coefficients(w, 50.0, 5.0)["cl"]
        cl8 = vlm.wing_coefficients(w, 50.0, 8.0)["cl"]
        self.assertGreater(cl2, 0.0)
        self.assertLess(cl2, cl5)
        self.assertLess(cl5, cl8)

    def test_zero_alpha_no_lift(self):
        w = vlm.build_wing(8.0, 1.0, 1.0, n_panels=4)
        r = vlm.wing_coefficients(w, 50.0, 0.0)
        self.assertLess(abs(r["cl"]), 1e-9)
        self.assertLess(abs(r["cdi"]), 1e-12)
        self.assertIsNone(r["span_efficiency"])

    def test_matches_lifting_line(self):
        w = vlm.build_wing(8.0, 1.0, 1.0, n_panels=4)
        cl = vlm.wing_coefficients(w, 50.0, 5.0)["cl"]
        ref = lifting_line_cl(8.0, 5.0)
        self.assertLess(abs(cl - ref) / ref, 0.12)

    def test_two_dimensional_limit(self):
        # Very high aspect ratio with square panels approaches 2*pi*a0.
        w = vlm.build_wing(200.0, 1.0, 1.0, n_panels=100)
        cl = vlm.wing_coefficients(w, 50.0, 5.0)["cl"]
        ref = 2.0 * math.pi * math.radians(5.0)
        self.assertLess(abs(cl - ref) / ref, 0.05)

    def test_span_efficiency_band(self):
        w = vlm.build_wing(8.0, 1.0, 1.0, n_panels=4)
        e = vlm.wing_coefficients(w, 50.0, 5.0)["span_efficiency"]
        self.assertIsNotNone(e)
        self.assertGreater(e, 0.5)
        self.assertLess(e, 1.0)

    def test_cdi_quadratic_scaling(self):
        w = vlm.build_wing(8.0, 1.0, 1.0, n_panels=4)
        cdi4 = vlm.wing_coefficients(w, 50.0, 4.0)["cdi"]
        cdi8 = vlm.wing_coefficients(w, 50.0, 8.0)["cdi"]
        ratio = cdi8 / cdi4
        self.assertGreater(ratio, 3.5)
        self.assertLess(ratio, 4.5)

    def test_lift_distribution_positive(self):
        w = vlm.build_wing(8.0, 1.0, 1.0, n_panels=8)
        g = vlm.solve_circulations(w, 50.0, 5.0)
        lifts = vlm.lift_distribution(w, g, 50.0)
        self.assertEqual(len(lifts), 8)
        self.assertTrue(all(l > 0.0 for l in lifts))

    def test_downwash_angles_band(self):
        # Induced downwash angles stay small in the linear range: bounded
        # by the geometric angle on the high side, mildly negative only
        # at the root panel where the mirror-image root leg is dropped.
        w = vlm.build_wing(8.0, 1.0, 1.0, n_panels=4)
        g = vlm.solve_circulations(w, 50.0, 5.0)
        angles = vlm.downwash_angles(w, g, 50.0)
        self.assertEqual(len(angles), 4)
        alpha = math.radians(5.0)
        self.assertTrue(all(a < alpha for a in angles))
        self.assertTrue(all(a > -alpha for a in angles))
        self.assertGreater(sum(angles), 0.0)

    def test_tapered_wing_sane(self):
        # A tapered wing with the same span and area lifts comparably to
        # its rectangular counterpart (coarse-model agreement band).
        w_rect = vlm.build_wing(8.0, 1.0, 1.0, n_panels=4)
        w_taper = vlm.build_wing(8.0, 1.2, 0.8, n_panels=4)
        cl_rect = vlm.wing_coefficients(w_rect, 50.0, 5.0)["cl"]
        cl_taper = vlm.wing_coefficients(w_taper, 50.0, 5.0)["cl"]
        self.assertGreater(cl_taper, 0.0)
        self.assertLess(abs(cl_taper - cl_rect) / cl_rect, 0.15)

    def test_deterministic(self):
        w = vlm.build_wing(8.0, 1.0, 1.0, n_panels=8)
        r1 = vlm.wing_coefficients(w, 50.0, 5.0)
        r2 = vlm.wing_coefficients(w, 50.0, 5.0)
        self.assertEqual(r1["cl"], r2["cl"])
        self.assertEqual(r1["cdi"], r2["cdi"])
        self.assertEqual(r1["circulations"], r2["circulations"])


class ValueErrorTest(unittest.TestCase):
    def test_build_wing_nonsense(self):
        with self.assertRaises(ValueError):
            vlm.build_wing(0.0, 1.0, 1.0)
        with self.assertRaises(ValueError):
            vlm.build_wing(8.0, -1.0, 1.0)
        with self.assertRaises(ValueError):
            vlm.build_wing(8.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            vlm.build_wing(8.0, 1.0, 1.0, n_panels=0)
        with self.assertRaises(ValueError):
            vlm.build_wing(8.0, 1.0, 1.0, n_panels=-2)

    def test_flow_nonsense(self):
        w = vlm.build_wing(8.0, 1.0, 1.0, n_panels=4)
        with self.assertRaises(ValueError):
            vlm.solve_circulations(w, 0.0, 5.0)
        with self.assertRaises(ValueError):
            vlm.solve_circulations(w, 50.0, 45.0)
        with self.assertRaises(ValueError):
            vlm.solve_circulations(w, 50.0, -60.0)
        with self.assertRaises(ValueError):
            vlm.lift_distribution(w, [1.0, 1.0], 50.0, rho=0.0)
        with self.assertRaises(ValueError):
            vlm.lift_distribution(w, [1.0], 50.0)
        with self.assertRaises(ValueError):
            vlm.wing_coefficients(w, 50.0, 5.0, rho=-1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
