"""Contract test for elliptical-hertz-contact (structures/fem).

Exercises the SKILL.md Workflow steps: step 1 curvature_sums (the per-plane
curvature coefficients A and B), step 2 equivalent_modulus, step 3
eccentricity (the deterministic bisection on the Hertz relation in the
complete elliptic integrals K(e), E(e) from complete_elliptic_integrals),
step 4 elliptical_patch (the major and minor semi-axes, peak pressure,
mutual approach and patch area), step 5 the circular-patch identity check
at equal curvatures, step 6 yield_limit_pressure under the point-arm and
line-arm static conventions, and step 7 yield_limit_load and yield_margin.

Stdlib unittest, offline, deterministic, no RNG. No exact-float equality
on computed sums; assertAlmostEqual and math.isclose are used throughout.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import elliptical_hertz_contact_logic as ehc


def rel_close(actual, expected, rel_tol):
    return math.isclose(actual, expected, rel_tol=rel_tol)


class TestEllipticalHertzContact(unittest.TestCase):
    """Ball-in-groove and crossed-cylinder worked examples (step 1-4)."""

    def test_worked_example_a_curvature_sums(self):
        """Step 1: curvature_sums for the ball in a conforming groove raceway."""
        a_curv, b_curv = ehc.curvature_sums(6.35e-3, 6.35e-3, 20.0e-3, -7.9375e-3, 0.0)
        self.assertTrue(rel_close(a_curv, 15.748031496062993, 1e-9))
        self.assertTrue(rel_close(b_curv, 103.74015748031496, 1e-9))
        self.assertTrue(rel_close(b_curv / a_curv, 6.5875, 1e-6))

    def test_worked_example_a_elliptical_patch(self):
        """Step 3-4: eccentricity and elliptical_patch for the groove raceway case."""
        a_curv, b_curv = ehc.curvature_sums(6.35e-3, 6.35e-3, 20.0e-3, -7.9375e-3, 0.0)
        patch = ehc.elliptical_patch(4450.0, 113736263736.26373, a_curv, b_curv)
        self.assertTrue(rel_close(patch["e"], 0.9570992179735442, 1e-9))
        self.assertTrue(rel_close(patch["a"], 0.0012666442469398249, 1e-6))
        self.assertTrue(rel_close(patch["b"], 0.0003670233382879257, 1e-6))
        self.assertTrue(rel_close(patch["ab_ratio"], 3.4511272575973266, 1e-6))
        self.assertTrue(rel_close(patch["p0"], 4570387901.1152115, 1e-6))
        self.assertTrue(rel_close(patch["delta"], 3.9240382445150205e-05, 1e-6))
        self.assertTrue(rel_close(patch["area"], 1.460488725338006e-06, 1e-6))

    def test_worked_example_a_semi_axis_identity(self):
        """Step 4: the identity b = a * sqrt(1 - e^2) holds for the groove patch."""
        a_curv, b_curv = ehc.curvature_sums(6.35e-3, 6.35e-3, 20.0e-3, -7.9375e-3, 0.0)
        patch = ehc.elliptical_patch(4450.0, 113736263736.26373, a_curv, b_curv)
        expected_b = patch["a"] * math.sqrt(1.0 - patch["e"] ** 2)
        self.assertTrue(rel_close(patch["b"], expected_b, 1e-12))

    def test_worked_example_b_curvature_sums(self):
        """Step 1: curvature_sums for crossed unequal cylinders at right angles."""
        a_curv, b_curv = ehc.curvature_sums(25.0e-3, math.inf, 40.0e-3, math.inf, math.pi / 2.0)
        self.assertTrue(rel_close(a_curv, 12.5, 1e-12))
        self.assertTrue(rel_close(b_curv, 20.0, 1e-12))

    def test_worked_example_b_elliptical_patch(self):
        """Step 3-4: eccentricity and elliptical_patch for the crossed-cylinder case."""
        a_curv, b_curv = ehc.curvature_sums(25.0e-3, math.inf, 40.0e-3, math.inf, math.pi / 2.0)
        patch = ehc.elliptical_patch(2000.0, 113736263736.26373, a_curv, b_curv)
        self.assertTrue(rel_close(patch["e"], 0.6821239264037162, 1e-9))
        self.assertTrue(rel_close(patch["a"], 0.0008710520463135454, 1e-6))
        self.assertTrue(rel_close(patch["b"], 0.0006369451271492054, 1e-6))
        self.assertTrue(rel_close(patch["ab_ratio"], 1.367546448172293, 1e-6))
        self.assertTrue(rel_close(patch["p0"], 1721175903.0748203, 1e-6))
        self.assertTrue(rel_close(patch["delta"], 1.759812774232002e-05, 1e-6))
        self.assertTrue(rel_close(patch["area"], 1.7429944229643266e-06, 1e-6))

    def test_yield_slice_anchors_point_and_line(self):
        """Step 6: yield_limit_pressure under the point-arm and line-arm conventions."""
        self.assertAlmostEqual(ehc.yield_limit_pressure(2000.0e6), 6.6e9, delta=1.0)
        self.assertAlmostEqual(ehc.yield_limit_pressure(2000.0e6, line_arm=True), 3.2e9, delta=1.0)

    def test_yield_limit_load_case_a(self):
        """Step 7: yield_limit_load reproduces the point-arm and line-arm loads (case A)."""
        a_curv, b_curv = ehc.curvature_sums(6.35e-3, 6.35e-3, 20.0e-3, -7.9375e-3, 0.0)
        patch = ehc.elliptical_patch(4450.0, 113736263736.26373, a_curv, b_curv)
        p0y_point = ehc.yield_limit_pressure(2000.0e6)
        p0y_line = ehc.yield_limit_pressure(2000.0e6, line_arm=True)
        p_y_point = ehc.yield_limit_load(p0y_point, patch["a"], patch["b"])
        p_y_line = ehc.yield_limit_load(p0y_line, patch["a"], patch["b"])
        self.assertTrue(rel_close(p_y_point, 6426.1503914872046, 1e-6))
        self.assertTrue(rel_close(p_y_line, 3115.7092807210688, 1e-6))

    def test_yield_limit_load_case_b(self):
        """Step 7: yield_limit_load reproduces the point-arm and line-arm loads (case B)."""
        a_curv, b_curv = ehc.curvature_sums(25.0e-3, math.inf, 40.0e-3, math.inf, math.pi / 2.0)
        patch = ehc.elliptical_patch(2000.0, 113736263736.26373, a_curv, b_curv)
        p0y_point = ehc.yield_limit_pressure(1200.0e6)
        p0y_line = ehc.yield_limit_pressure(1200.0e6, line_arm=True)
        p_y_point = ehc.yield_limit_load(p0y_point, patch["a"], patch["b"])
        p_y_line = ehc.yield_limit_load(p0y_line, patch["a"], patch["b"])
        self.assertTrue(rel_close(p_y_point, 4601.5052766258223, 1e-6))
        self.assertTrue(rel_close(p_y_line, 2231.0328613943379, 1e-6))

    def test_yield_margin_case_a(self):
        """Step 7: yield_margin verdicts for the groove raceway case, point and line arm."""
        a_curv, b_curv = ehc.curvature_sums(6.35e-3, 6.35e-3, 20.0e-3, -7.9375e-3, 0.0)
        patch = ehc.elliptical_patch(4450.0, 113736263736.26373, a_curv, b_curv)
        margin_point, verdict_point = ehc.yield_margin(patch["p0"], 2000.0e6)
        margin_line, verdict_line = ehc.yield_margin(patch["p0"], 2000.0e6, line_arm=True)
        self.assertTrue(rel_close(margin_point, 1.4440787396600459, 1e-6))
        self.assertEqual(verdict_point, "pass")
        self.assertTrue(rel_close(margin_line, 0.70015938892608276, 1e-6))
        self.assertEqual(verdict_line, "fail")

    def test_yield_margin_case_b(self):
        """Step 7: yield_margin verdicts for the crossed-cylinder case, point and line arm."""
        a_curv, b_curv = ehc.curvature_sums(25.0e-3, math.inf, 40.0e-3, math.inf, math.pi / 2.0)
        patch = ehc.elliptical_patch(2000.0, 113736263736.26373, a_curv, b_curv)
        margin_point, verdict_point = ehc.yield_margin(patch["p0"], 1200.0e6)
        margin_line, verdict_line = ehc.yield_margin(patch["p0"], 1200.0e6, line_arm=True)
        self.assertTrue(rel_close(margin_point, 2.3007526383129111, 1e-6))
        self.assertEqual(verdict_point, "pass")
        self.assertTrue(rel_close(margin_line, 1.115516430697169, 1e-6))
        self.assertEqual(verdict_line, "pass")

    def test_yield_load_inverse_identity(self):
        """Step 7: P_y inverts p0 = 3P/(2 pi a b) at both arm conventions."""
        a_curv, b_curv = ehc.curvature_sums(25.0e-3, math.inf, 40.0e-3, math.inf, math.pi / 2.0)
        patch = ehc.elliptical_patch(2000.0, 113736263736.26373, a_curv, b_curv)
        for line_arm in (False, True):
            p0_yield = ehc.yield_limit_pressure(1200.0e6, line_arm=line_arm)
            p_y = ehc.yield_limit_load(p0_yield, patch["a"], patch["b"])
            p0_recovered = 3.0 * p_y / (2.0 * math.pi * patch["a"] * patch["b"])
            self.assertTrue(rel_close(p0_recovered, p0_yield, 1e-9))
            margin, _ = ehc.yield_margin(patch["p0"], 1200.0e6, line_arm=line_arm)
            self.assertTrue(rel_close(margin, p0_yield / patch["p0"], 1e-12))

    def test_elliptic_integral_anchor_rows(self):
        """Step 3: complete_elliptic_integrals at the six anchor parameters."""
        rows = [
            (0.0, 1.5707963267948966, 1.5707963267948966),
            (0.04, 1.5868678474541664, 1.5549685462425293),
            (0.25, 1.685750354812596, 1.4674622093394245),
            (0.64, 1.9953027776647292, 1.2763499431699077),
            (0.81, 2.280549138422769, 1.1716970527816148),
            (0.999999998, 11.40135368089919, 1.0000000109013556),
        ]
        for m_val, k_exp, e_exp in rows:
            k_val, e_val = ehc.complete_elliptic_integrals(m_val)
            self.assertTrue(rel_close(k_val, k_exp, 1e-12))
            self.assertTrue(rel_close(e_val, e_exp, 1e-12))

    def test_elliptic_integral_at_modulus_half(self):
        """Step 3: K and E at modulus e = 0.5 (parameter m = 0.25) match the published values."""
        k_val, e_val = ehc.complete_elliptic_integrals(0.25)
        self.assertTrue(rel_close(k_val, 1.6857503548125966, 2e-15 + 1e-13))
        self.assertTrue(rel_close(e_val, 1.4674622093394273, 2e-15 + 1e-13))

    def test_elliptic_integral_ordering_and_monotonicity(self):
        """Step 3: K >= pi/2 >= E > 0 and K - E >= 0, K increasing, E decreasing on the grid."""
        prev_k, prev_e = None, None
        for i in range(1, 1000):
            e = i / 1000.0
            k_val, e_val = ehc.complete_elliptic_integrals(e * e)
            self.assertGreaterEqual(k_val, math.pi / 2.0 - 1e-9)
            self.assertGreaterEqual(math.pi / 2.0 + 1e-9, e_val)
            self.assertGreater(e_val, 0.0)
            self.assertGreaterEqual(k_val - e_val, -1e-12)
            if prev_k is not None:
                self.assertGreaterEqual(k_val, prev_k - 1e-12)
                self.assertGreaterEqual(prev_e, e_val - 1e-12)
            prev_k, prev_e = k_val, e_val

    def test_circular_degeneracy(self):
        """Step 5: equal curvatures reduce exactly to the circular closed form (10 mm ball, 25 mm socket)."""
        a_curv, b_curv = ehc.curvature_sums(10.0e-3, 10.0e-3, -25.0e-3, -25.0e-3, 0.0)
        self.assertTrue(rel_close(a_curv, 30.0, 1e-9))
        self.assertTrue(rel_close(b_curv, 30.0, 1e-9))
        e_val = ehc.eccentricity(a_curv, b_curv)
        self.assertEqual(e_val, 0.0)
        patch = ehc.elliptical_patch(700.0, 113736263736.26373, a_curv, b_curv)
        closed_form = (3.0 * 700.0 / (4.0 * 113736263736.26373 * (a_curv + b_curv))) ** (1.0 / 3.0)
        self.assertTrue(rel_close(patch["a"], closed_form, 1e-9))
        self.assertTrue(rel_close(patch["b"], closed_form, 1e-9))
        self.assertTrue(rel_close(patch["a"], 0.0004253074907842078, 1e-9))
        delta_closed = 3.0 * 700.0 / (4.0 * 113736263736.26373 * patch["a"])
        self.assertTrue(rel_close(patch["delta"], delta_closed, 1e-9))
        self.assertTrue(rel_close(patch["delta"], 1.0853187703029526e-05, 1e-9))
        p0_closed = 3.0 * 700.0 / (2.0 * math.pi * patch["a"] * patch["a"])
        self.assertTrue(rel_close(patch["p0"], p0_closed, 1e-9))

    def test_near_circular_identity(self):
        """Step 3: near-equal curvatures (B/A = 1 + 1e-10) reflect the bisection floor at the equal-radius limit."""
        a_curv = 30.0
        b_curv = a_curv * (1.0 + 1e-10)
        e_val = ehc.eccentricity(a_curv, b_curv)
        self.assertGreater(e_val, 0.0)
        self.assertLess(e_val, 1e-2)
        patch = ehc.elliptical_patch(700.0, 113736263736.26373, a_curv, b_curv)
        closed_form = (3.0 * 700.0 / (4.0 * 113736263736.26373 * (a_curv + b_curv))) ** (1.0 / 3.0)
        rel_dev = (patch["a"] - closed_form) / closed_form
        self.assertGreater(rel_dev, 1e-10)
        self.assertLess(rel_dev, 1e-7)

    def test_exact_equal_radius_zero_deviation(self):
        """Step 5: exact equality B/A = 1 gives the e = 0 branch and zero deviation to float noise."""
        a_curv = 30.0
        b_curv = 30.0
        e_val = ehc.eccentricity(a_curv, b_curv)
        self.assertEqual(e_val, 0.0)
        patch = ehc.elliptical_patch(700.0, 113736263736.26373, a_curv, b_curv)
        closed_form = (3.0 * 700.0 / (4.0 * 113736263736.26373 * (a_curv + b_curv))) ** (1.0 / 3.0)
        self.assertAlmostEqual(patch["a"], closed_form, delta=1e-15)

    def test_monotonicity_and_range_of_hertz_relation(self):
        """Step 3: the solved eccentricity increases with B/A over a ratio sweep and round-trips."""
        prev_e = None
        for ratio in (1.01, 1.5, 2.0, 5.0, 10.0, 13.93, 30.0, 60.0, 100.0):
            a_curv = 10.0
            b_curv = a_curv * ratio
            e_val = ehc.eccentricity(a_curv, b_curv)
            if prev_e is not None:
                self.assertGreater(e_val, prev_e)
            prev_e = e_val
            recovered_ratio = ehc._hertz_ratio(e_val)
            self.assertTrue(rel_close(recovered_ratio, ratio, 1e-6))

    def test_handbook_axis_ratio_point(self):
        """Step 3: the classical m/n table point B/A = 13.93 gives axis ratio b/a near 0.1805."""
        a_curv = 10.0
        b_curv = a_curv * 13.93
        e_val = ehc.eccentricity(a_curv, b_curv)
        b_over_a = math.sqrt(1.0 - e_val * e_val)
        self.assertTrue(rel_close(b_over_a, 0.1805, 2e-3))
        self.assertTrue(rel_close(e_val, 0.9836, 2e-3))

    def test_geometry_limits_equal_sphere_pair(self):
        """Step 1: equal-radius sphere pair gives A = B = 1/r, the circular arm of the sibling."""
        r = 10.0e-3
        a_curv, b_curv = ehc.curvature_sums(r, r, r, r, 0.0)
        expected = 1.0 / r
        self.assertTrue(rel_close(a_curv, expected, 1e-12))
        self.assertTrue(rel_close(b_curv, expected, 1e-12))
        self.assertTrue(rel_close(a_curv + b_curv, 2.0 / r, 1e-12))

    def test_geometry_limits_crossed_equal_cylinders(self):
        """Step 1: crossed equal cylinders at phi = pi/2 give the sibling equal-radius closed form."""
        r = 10.0e-3
        a_curv, b_curv = ehc.curvature_sums(r, math.inf, r, math.inf, math.pi / 2.0)
        expected = 1.0 / (2.0 * r)
        self.assertTrue(rel_close(a_curv, expected, 1e-12))
        self.assertTrue(rel_close(b_curv, expected, 1e-12))

    def test_geometry_limits_crossed_unequal_sum(self):
        """Step 1: crossed unequal cylinders satisfy A + B = (1/r1 + 1/r2)/2 exactly."""
        r1, r2 = 25.0e-3, 40.0e-3
        a_curv, b_curv = ehc.curvature_sums(r1, math.inf, r2, math.inf, math.pi / 2.0)
        expected_sum = 0.5 * (1.0 / r1 + 1.0 / r2)
        self.assertTrue(rel_close(a_curv + b_curv, expected_sum, 1e-9))
        self.assertTrue(rel_close(a_curv + b_curv, 32.5, 1e-9))

    def test_concave_partner_smaller_than_convex_raises(self):
        """Step 1: a concave groove tighter than the convex ball invalidates the elliptical patch."""
        with self.assertRaises(ValueError):
            ehc.curvature_sums(6.35e-3, 6.35e-3, -5.0e-3, 20.0e-3)

    def test_determinism(self):
        """Full pipeline (steps 1-7) returns identical bits across two identical runs."""
        a1, b1 = ehc.curvature_sums(6.35e-3, 6.35e-3, 20.0e-3, -7.9375e-3, 0.0)
        a2, b2 = ehc.curvature_sums(6.35e-3, 6.35e-3, 20.0e-3, -7.9375e-3, 0.0)
        self.assertEqual(a1, a2)
        self.assertEqual(b1, b2)
        p1 = ehc.elliptical_patch(4450.0, 113736263736.26373, a1, b1)
        p2 = ehc.elliptical_patch(4450.0, 113736263736.26373, a2, b2)
        self.assertEqual(p1, p2)

    def test_value_error_complete_elliptic_integrals(self):
        """Boundary rejections for step 3's elliptic integral evaluation."""
        with self.assertRaises(ValueError):
            ehc.complete_elliptic_integrals(-0.1)
        with self.assertRaises(ValueError):
            ehc.complete_elliptic_integrals(1.0)

    def test_value_error_equivalent_modulus(self):
        """Boundary rejections for step 2's equivalent elastic modulus."""
        with self.assertRaises(ValueError):
            ehc.equivalent_modulus(0.0, 0.3, 207.0e9, 0.3)
        with self.assertRaises(ValueError):
            ehc.equivalent_modulus(207.0e9, 0.0, 207.0e9, 0.3)
        with self.assertRaises(ValueError):
            ehc.equivalent_modulus(207.0e9, 0.5, 207.0e9, 0.3)
        with self.assertRaises(ValueError):
            ehc.equivalent_modulus(207.0e9, 0.3, -1.0e9, 0.3)

    def test_value_error_curvature_sums(self):
        """Boundary rejections for step 1's curvature coefficients."""
        with self.assertRaises(ValueError):
            ehc.curvature_sums(0.0, 1.0, 1.0, 1.0)
        with self.assertRaises(ValueError):
            ehc.curvature_sums(6.35e-3, 6.35e-3, 20.0e-3, -7.9375e-3, math.pi)

    def test_value_error_eccentricity(self):
        """Boundary rejections for step 3's eccentricity solve."""
        with self.assertRaises(ValueError):
            ehc.eccentricity(0.0, 10.0)
        with self.assertRaises(ValueError):
            ehc.eccentricity(10.0, 5.0)

    def test_value_error_elliptical_patch(self):
        """Boundary rejections for step 4's patch solver."""
        with self.assertRaises(ValueError):
            ehc.elliptical_patch(0.0, 113736263736.26373, 15.0, 20.0)
        with self.assertRaises(ValueError):
            ehc.elliptical_patch(4450.0, 0.0, 15.0, 20.0)
        with self.assertRaises(ValueError):
            ehc.elliptical_patch(4450.0, 113736263736.26373, 0.0, 20.0)
        with self.assertRaises(ValueError):
            ehc.elliptical_patch(4450.0, 113736263736.26373, 20.0, 15.0)

    def test_value_error_yield_functions(self):
        """Boundary rejections for step 6-7's yield-limit functions."""
        with self.assertRaises(ValueError):
            ehc.yield_limit_pressure(0.0)
        with self.assertRaises(ValueError):
            ehc.yield_limit_load(0.0, 1.0, 1.0)
        with self.assertRaises(ValueError):
            ehc.yield_limit_load(1.0, 0.0, 1.0)
        with self.assertRaises(ValueError):
            ehc.yield_limit_load(1.0, 1.0, 0.0)


if __name__ == "__main__":
    unittest.main()
