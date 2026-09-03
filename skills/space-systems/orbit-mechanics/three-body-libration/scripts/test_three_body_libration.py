"""Contract test for three-body-libration logic (offline, stdlib only).

Run with: python3 scripts/test_three_body_libration.py
Covers the Earth-Moon worked example (mass ratio, collinear L1/L2/L3 roots
with the |f| < 1e-10 residual gate, L4/L5 closed-form exactness, physical
distances, Jacobi constant at L4), a second mass ratio mu = 0.1, the
bisection fallback path, determinism, and ValueError rejection of every
non-physical input in the validation list.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from three_body_libration_logic import (
    MU_EARTH_MOON_DEFAULT,
    mass_ratio,
    collinear_force_balance,
    collinear_point,
    lagrange_points,
    physical_distance_from_primary,
    jacobi_constant,
    three_body_assessment,
)

M_EARTH = 5.972e24
M_MOON = 7.348e22
A_EM_M = 3.844e8          # Earth-Moon separation, m
A_EM_KM = 384400.0
SQRT3_2 = math.sqrt(3.0) / 2.0

# Real module outputs for the Earth-Moon worked example (assert targets).
MU_EM = 0.012154535289174722
X_L1_EM = 0.8368956930433207
X_L2_EM = 1.15569735430554
X_L3_EM = -1.0050642914140742
L1_FROM_EARTH_KM = 326374.90777101123
L2_FROM_EARTH_KM = 448922.26636020833
L2_FROM_MOON_KM = 64522.266360208356
JACOBI_L4_EM = 2.987993197438921


class TestMassRatio(unittest.TestCase):
    def test_mass_ratio_earth_moon(self):
        mu = mass_ratio(M_EARTH, M_MOON)
        self.assertAlmostEqual(mu, MU_EM, places=12)
        self.assertGreaterEqual(mu, 0.0120)
        self.assertLessEqual(mu, 0.0123)

    def test_mass_ratio_nonpositive_mass_rejected(self):
        with self.assertRaises(ValueError):
            mass_ratio(0.0, M_MOON)
        with self.assertRaises(ValueError):
            mass_ratio(M_EARTH, -1.0)

    def test_mass_ratio_secondary_not_lighter_rejected(self):
        with self.assertRaises(ValueError):
            mass_ratio(M_MOON, M_EARTH)  # mu > 0.5
        with self.assertRaises(ValueError):
            mass_ratio(1.0, 1.0)  # mu = 0.5 exactly


class TestCollinearPoints(unittest.TestCase):
    def test_l1_root_and_residual(self):
        self.assertGreaterEqual(X_L1_EM, 0.79)
        self.assertLessEqual(X_L1_EM, 0.87)
        self.assertLess(abs(collinear_force_balance(X_L1_EM, MU_EM)), 1e-10)

    def test_l2_root_and_residual(self):
        self.assertGreaterEqual(X_L2_EM, 1.11)
        self.assertLessEqual(X_L2_EM, 1.19)
        self.assertLess(abs(collinear_force_balance(X_L2_EM, MU_EM)), 1e-10)

    def test_l3_root_and_residual(self):
        self.assertLess(X_L3_EM, -0.9)
        self.assertLess(abs(collinear_force_balance(X_L3_EM, MU_EM)), 1e-10)

    def test_collinear_point_returns_worked_values(self):
        self.assertAlmostEqual(collinear_point(MU_EM, "L1"), X_L1_EM, places=12)
        self.assertAlmostEqual(collinear_point(MU_EM, "L2"), X_L2_EM, places=12)
        self.assertAlmostEqual(collinear_point(MU_EM, "L3"), X_L3_EM, places=12)

    def test_residual_gate_second_mu(self):
        for branch in ("L1", "L2", "L3"):
            x = collinear_point(0.1, branch)
            self.assertLess(abs(collinear_force_balance(x, 0.1)), 1e-10,
                            msg="residual gate failed for mu=0.1 branch " + branch)

    def test_residual_gate_default_constant_mu(self):
        for branch in ("L1", "L2", "L3"):
            x = collinear_point(MU_EARTH_MOON_DEFAULT, branch)
            self.assertLess(abs(collinear_force_balance(x, MU_EARTH_MOON_DEFAULT)), 1e-10)

    def test_bisection_fallback_when_newton_leaves_bracket(self):
        x_fallback = collinear_point(MU_EM, "L2", x_guess=10.0)
        self.assertAlmostEqual(x_fallback, X_L2_EM, places=12)
        self.assertLess(abs(collinear_force_balance(x_fallback, MU_EM)), 1e-10)

    def test_bisection_fallback_outside_guess_l1(self):
        x_fallback = collinear_point(MU_EM, "L1", x_guess=-5.0)
        self.assertAlmostEqual(x_fallback, X_L1_EM, places=12)

    def test_branch_not_in_set_rejected(self):
        for bad in ("L4", "l1", "", None):
            with self.assertRaises(ValueError):
                collinear_point(MU_EM, bad)

    def test_mu_out_of_range_rejected(self):
        for mu in (0.0, -0.1, 0.5, 1.0):
            with self.assertRaises(ValueError):
                collinear_point(mu, "L1")

    def test_force_balance_mu_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            collinear_force_balance(0.5, 0.5)

    def test_force_balance_singular_on_primary_rejected(self):
        with self.assertRaises(ValueError):
            collinear_force_balance(-MU_EM, MU_EM)  # on primary 1
        with self.assertRaises(ValueError):
            collinear_force_balance(1.0 - MU_EM, MU_EM)  # on primary 2


class TestTriangularPoints(unittest.TestCase):
    def test_l4_closed_form_exact(self):
        l4 = lagrange_points(MU_EM)["L4"]
        self.assertAlmostEqual(l4[0], 0.5 - MU_EM, places=9)
        self.assertAlmostEqual(l4[1], SQRT3_2, places=12)
        self.assertEqual(l4[1], SQRT3_2)

    def test_l5_mirrors_l4(self):
        pts = lagrange_points(MU_EM)
        l4, l5 = pts["L4"], pts["L5"]
        self.assertAlmostEqual(l5[0], 0.5 - MU_EM, places=12)
        self.assertAlmostEqual(l5[1], -SQRT3_2, places=12)
        self.assertEqual(l4[0], l5[0])
        self.assertEqual(l4[1], -l5[1])

    def test_lagrange_points_contains_all_five(self):
        pts = lagrange_points(MU_EM)
        self.assertEqual(set(pts.keys()), {"L1", "L2", "L3", "L4", "L5"})
        self.assertAlmostEqual(pts["L1"], X_L1_EM, places=12)
        self.assertAlmostEqual(pts["L2"], X_L2_EM, places=12)
        self.assertAlmostEqual(pts["L3"], X_L3_EM, places=12)

    def test_lagrange_points_mu_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            lagrange_points(0.5)


class TestPhysicalDistances(unittest.TestCase):
    def test_l1_distance_from_earth_bounds(self):
        d = physical_distance_from_primary(X_L1_EM, MU_EM, A_EM_M, primary=1) / 1000.0
        self.assertAlmostEqual(d, L1_FROM_EARTH_KM, places=6)
        self.assertGreaterEqual(d, 310000.0)
        self.assertLessEqual(d, 345000.0)

    def test_l2_distance_from_earth_bounds(self):
        d = physical_distance_from_primary(X_L2_EM, MU_EM, A_EM_M, primary=1) / 1000.0
        self.assertAlmostEqual(d, L2_FROM_EARTH_KM, places=6)
        self.assertGreaterEqual(d, 425000.0)
        self.assertLessEqual(d, 465000.0)

    def test_l2_distance_from_moon_primary2(self):
        d = physical_distance_from_primary(X_L2_EM, MU_EM, A_EM_M, primary=2) / 1000.0
        self.assertAlmostEqual(d, L2_FROM_MOON_KM, places=6)
        self.assertAlmostEqual(d, abs(X_L2_EM - (1.0 - MU_EM)) * A_EM_KM, places=6)

    def test_l1_distance_from_moon_uses_abs(self):
        d = physical_distance_from_primary(X_L1_EM, MU_EM, A_EM_M, primary=2)
        self.assertAlmostEqual(d, abs(X_L1_EM - (1.0 - MU_EM)) * A_EM_M, places=3)

    def test_distance_fraction_round_trip(self):
        frac = (X_L1_EM + MU_EM)
        self.assertAlmostEqual(frac * A_EM_KM, L1_FROM_EARTH_KM, places=6)

    def test_nonpositive_separation_rejected(self):
        for sep in (0.0, -3.844e8):
            with self.assertRaises(ValueError):
                physical_distance_from_primary(X_L1_EM, MU_EM, sep, primary=1)

    def test_invalid_primary_rejected(self):
        for p in (0, 3, -1):
            with self.assertRaises(ValueError):
                physical_distance_from_primary(X_L1_EM, MU_EM, A_EM_M, primary=p)


class TestJacobiConstant(unittest.TestCase):
    def test_jacobi_closed_form_at_l4(self):
        l4 = lagrange_points(MU_EM)["L4"]
        c = jacobi_constant(MU_EM, l4[0], l4[1], 0.0, 0.0)
        self.assertAlmostEqual(c, JACOBI_L4_EM, places=12)
        closed = (0.5 - MU_EM) ** 2 + SQRT3_2 ** 2 + 2.0 * (1.0 - MU_EM) + 2.0 * MU_EM
        self.assertAlmostEqual(c, closed, places=9)
        self.assertGreaterEqual(c, 2.98)
        self.assertLessEqual(c, 3.00)

    def test_jacobi_matches_direct_evaluation(self):
        pts = lagrange_points(MU_EM)
        x, y = pts["L4"]
        c = jacobi_constant(MU_EM, x, y, 0.0, 0.0)
        r1 = math.sqrt((x + MU_EM) ** 2 + y ** 2)
        r2 = math.sqrt((x - (1.0 - MU_EM)) ** 2 + y ** 2)
        direct = (x ** 2 + y ** 2 + 2.0 * (1.0 - MU_EM) / r1
                  + 2.0 * MU_EM / r2)
        self.assertAlmostEqual(c, direct, places=12)

    def test_jacobi_on_primary_rejected(self):
        with self.assertRaises(ValueError):
            jacobi_constant(MU_EM, -MU_EM, 0.0, 0.0, 0.0)  # on Earth
        with self.assertRaises(ValueError):
            jacobi_constant(MU_EM, 1.0 - MU_EM, 0.0, 0.0, 0.0)  # on the Moon

    def test_jacobi_mu_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            jacobi_constant(0.5, 0.4, 0.4, 0.0, 0.0)


class TestAssessment(unittest.TestCase):
    def test_assessment_dict_content(self):
        state = {"x": 0.4878454647108253, "y": SQRT3_2, "vx": 0.0, "vy": 0.0}
        a = three_body_assessment(M_EARTH, M_MOON, A_EM_M, state=state)
        self.assertAlmostEqual(a["mu"], MU_EM, places=12)
        self.assertAlmostEqual(a["lagrange_points"]["L1"], X_L1_EM, places=12)
        self.assertAlmostEqual(a["lagrange_points"]["L2"], X_L2_EM, places=12)
        self.assertAlmostEqual(a["lagrange_points"]["L3"], X_L3_EM, places=12)
        self.assertAlmostEqual(a["L1_distance_from_primary_km"],
                               L1_FROM_EARTH_KM, places=6)
        self.assertAlmostEqual(a["L2_distance_from_primary_km"],
                               L2_FROM_MOON_KM, places=6)
        self.assertAlmostEqual(a["jacobi_constant"], JACOBI_L4_EM, places=12)

    def test_assessment_without_state_has_no_jacobi_key(self):
        a = three_body_assessment(M_EARTH, M_MOON, A_EM_M)
        self.assertNotIn("jacobi_constant", a)
        self.assertEqual(set(a.keys()),
                         {"mu", "lagrange_points",
                          "L1_distance_from_primary_km",
                          "L2_distance_from_primary_km"})

    def test_assessment_distances_consistent_with_primary_functions(self):
        a = three_body_assessment(M_EARTH, M_MOON, A_EM_M)
        self.assertAlmostEqual(
            a["L1_distance_from_primary_km"],
            physical_distance_from_primary(X_L1_EM, MU_EM, A_EM_M, 1) / 1000.0,
            places=9)
        self.assertAlmostEqual(
            a["L2_distance_from_primary_km"],
            physical_distance_from_primary(X_L2_EM, MU_EM, A_EM_M, 2) / 1000.0,
            places=9)

    def test_assessment_propagates_value_errors(self):
        with self.assertRaises(ValueError):
            three_body_assessment(M_MOON, M_EARTH, A_EM_M)  # mu > 0.5
        with self.assertRaises(ValueError):
            three_body_assessment(M_EARTH, M_MOON, 0.0)  # separation <= 0


class TestDeterminism(unittest.TestCase):
    def test_repeated_calls_identical(self):
        self.assertEqual(lagrange_points(MU_EM), lagrange_points(MU_EM))
        self.assertEqual(collinear_point(MU_EM, "L2"),
                         collinear_point(MU_EM, "L2"))
        self.assertEqual(jacobi_constant(MU_EM, 0.4, 0.3, 0.1, 0.05),
                         jacobi_constant(MU_EM, 0.4, 0.3, 0.1, 0.05))


if __name__ == "__main__":
    unittest.main()
