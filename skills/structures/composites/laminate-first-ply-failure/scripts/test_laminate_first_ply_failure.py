"""Offline contract test for laminate-first-ply-failure (stdlib unittest).

Covers the T300/5208 worked example ([0/90/45/-45]s, 0.125 mm plies,
Nx = 100 N/mm), the unidirectional [0]8 closed forms, mirror symmetry,
determinism, the result dict contract, and ValueError rejection of
non-physical inputs. Run from the repo root:

    python3 skills/structures/composites/laminate-first-ply-failure/scripts/test_laminate_first_ply_failure.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import laminate_first_ply_failure_logic as fpf

# Worked-example material and laminate (T300/5208).
Q = fpf.q_matrix_from_constants(fpf.T300_E1, fpf.T300_E2, fpf.T300_NU12,
                                fpf.T300_G12)
ALLOW = (fpf.T300_XT, fpf.T300_XC, fpf.T300_YT, fpf.T300_YC, fpf.T300_S)
PLIES = [0, 90, 45, -45, -45, 45, 90, 0]
PLY_T = 0.125
A_WORKED = fpf.a_matrix_from_plies(PLIES, Q, PLY_T)
A_INV = fpf.a_inverse_compliance(*A_WORKED)
NX = 100.0


class TestQMatrixFromConstants(unittest.TestCase):
    def test_t300_q_values(self):
        q11, q12, q22, q66 = Q
        self.assertAlmostEqual(q11, 181811.14, delta=0.5)   # about 181.8 GPa
        self.assertAlmostEqual(q12, 2896.92, delta=0.5)     # about 2.90 GPa
        self.assertAlmostEqual(q22, 10346.16, delta=0.5)    # about 10.35 GPa
        self.assertAlmostEqual(q66, 7170.0, delta=1e-9)     # q66 = G12
        self.assertAlmostEqual(q12, fpf.T300_NU12 * q22, places=9)

    def test_isotropic_reduction(self):
        # E1 = E2 = E, nu12 = nu, G12 = E / (2 (1 + nu)) reduces [Q] to
        # the isotropic plane-stress form q11 = q22 = E/(1 - nu^2),
        # q12 = nu E/(1 - nu^2), q66 = E/(2 (1 + nu)).
        e, nu = 70000.0, 0.33
        q11, q12, q22, q66 = fpf.q_matrix_from_constants(
            e, e, nu, e / (2.0 * (1.0 + nu)))
        self.assertAlmostEqual(q11, e / (1.0 - nu * nu), places=3)
        self.assertAlmostEqual(q22, e / (1.0 - nu * nu), places=3)
        self.assertAlmostEqual(q12, nu * e / (1.0 - nu * nu), places=3)
        self.assertAlmostEqual(q66, e / (2.0 * (1.0 + nu)), places=3)

    def test_valueerror_nonpositive_constants(self):
        for bad in ((0.0, 10300.0, 0.28, 7170.0),
                    (181000.0, -1.0, 0.28, 7170.0),
                    (181000.0, 10300.0, 0.0, 7170.0),
                    (181000.0, 10300.0, -0.28, 7170.0),
                    (181000.0, 10300.0, 0.28, -5.0)):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    fpf.q_matrix_from_constants(*bad)

    def test_valueerror_singular_poisson_product(self):
        # nu21 = 0.9 * 100 / 10 = 9 makes nu12 * nu21 > 1: singular.
        with self.assertRaises(ValueError):
            fpf.q_matrix_from_constants(10.0, 100.0, 0.9, 5.0)


class TestAMatrixAndInverse(unittest.TestCase):
    def test_t300_worked_laminate_a(self):
        a11_m, a12_m, a22_m, a66_m = A_WORKED
        self.assertAlmostEqual(a11_m, 76368.0, delta=1.0)   # about 76368 N/mm
        self.assertAlmostEqual(a12_m, 22607.0, delta=1.0)   # about 22607 N/mm
        self.assertAlmostEqual(a22_m, 76368.0, delta=1.0)   # about 76368 N/mm
        self.assertAlmostEqual(a66_m, 26880.0, delta=1.0)   # about 26880 N/mm

    def test_quasi_isotropic_a11_equals_a22(self):
        plies = [0, 45, -45, 90, 90, -45, 45, 0]
        a11_m, a12_m, a22_m, a66_m = fpf.a_matrix_from_plies(plies, Q, PLY_T)
        self.assertAlmostEqual(a11_m, a22_m, places=9)

    def test_unidirectional_a_values(self):
        a11_m, a12_m, a22_m, a66_m = fpf.a_matrix_from_plies(
            [0] * 8, Q, PLY_T)
        self.assertAlmostEqual(a11_m, Q[0] * 1.0, places=6)
        self.assertAlmostEqual(a22_m, Q[2] * 1.0, places=6)
        self.assertAlmostEqual(a66_m, Q[3] * 1.0, places=6)

    def test_a_matrix_valueerror_guards(self):
        with self.assertRaises(ValueError):
            fpf.a_matrix_from_plies([], Q, PLY_T)
        with self.assertRaises(ValueError):
            fpf.a_matrix_from_plies(PLIES, Q[:3], PLY_T)
        with self.assertRaises(ValueError):
            fpf.a_matrix_from_plies(PLIES, Q, 0.0)
        with self.assertRaises(ValueError):
            fpf.a_matrix_from_plies(PLIES, Q, -0.125)

    def test_a_inverse_round_trip(self):
        # Inverting the compliance recovers the original A block.
        a11, a12, a22, a66 = A_INV
        det = a11 * a22 - a12 * a12
        back = (a22 / det, -a12 / det, a11 / det, 1.0 / a66)
        for got, expected in zip(back, A_WORKED):
            self.assertAlmostEqual(got, expected, delta=abs(expected) * 1e-9)

    def test_a_inverse_valueerror_guards(self):
        with self.assertRaises(ValueError):
            fpf.a_inverse_compliance(1.0, 0.0, 1.0, 0.0)
        with self.assertRaises(ValueError):
            fpf.a_inverse_compliance(-1.0, 0.0, 1.0, 1.0)
        with self.assertRaises(ValueError):
            fpf.a_inverse_compliance(1.0, 2.0, 1.0, 1.0)  # singular block


class TestMidplaneStrains(unittest.TestCase):
    def test_worked_example_strains(self):
        ex, ey, gxy = fpf.midplane_strains(*A_INV, NX, 0.0, 0.0)
        self.assertAlmostEqual(ex, 1.435e-3, delta=1e-6)    # about 1.435e-3
        self.assertAlmostEqual(ey, -4.25e-4, delta=1e-6)    # about -4.25e-4
        self.assertAlmostEqual(gxy, 0.0, places=12)         # shear decoupled

    def test_shear_decoupling(self):
        ex, ey, gxy = fpf.midplane_strains(*A_INV, 0.0, 0.0, 50.0)
        self.assertEqual(ex, 0.0)
        self.assertEqual(ey, 0.0)
        self.assertAlmostEqual(gxy, A_INV[3] * 50.0, places=9)

    def test_negative_a12_accepted(self):
        # a12 is the Poisson cross-coupling term, negative for a real
        # laminate; it must not raise and must give the coupled ey.
        ex, ey, gxy = fpf.midplane_strains(*A_INV, NX, 0.0, 0.0)
        self.assertAlmostEqual(ey, A_INV[1] * NX, places=9)
        self.assertAlmostEqual(ex, A_INV[0] * NX, places=9)

    def test_valueerror_nonpositive_diagonal(self):
        for bad in ((0.0, 0.0, 1.0, 1.0),
                    (1.0, 0.0, -1.0, 1.0),
                    (1.0, 0.0, 1.0, 0.0)):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    fpf.midplane_strains(*bad, 100.0, 0.0, 0.0)


class TestPlyTransforms(unittest.TestCase):
    def test_zero_ply_material_strains(self):
        ex, ey, gxy = 1.0e-3, -3.0e-4, 2.0e-4
        e1, e2, g12 = fpf.ply_material_strains(ex, ey, gxy, 0.0)
        self.assertAlmostEqual(e1, ex, places=15)
        self.assertAlmostEqual(e2, ey, places=15)
        self.assertAlmostEqual(g12, gxy, places=15)

    def test_90_ply_material_strains_swap(self):
        ex, ey, gxy = 1.0e-3, -3.0e-4, 2.0e-4
        e1, e2, g12 = fpf.ply_material_strains(ex, ey, gxy, 90.0)
        self.assertAlmostEqual(e1, ey, places=12)
        self.assertAlmostEqual(e2, ex, places=12)
        self.assertAlmostEqual(g12, -gxy, places=12)

    def test_orthogonality_and_periodicity(self):
        ex, ey, gxy = 1.0e-3, -3.0e-4, 2.0e-4
        e1, e2, g12 = fpf.ply_material_strains(ex, ey, gxy, 30.0)
        s1, s2, sg = fpf.ply_material_strains(ex, ey, gxy, 120.0)
        self.assertAlmostEqual(e1, s2, places=9)
        self.assertAlmostEqual(e2, s1, places=9)
        self.assertAlmostEqual(g12, -sg, places=9)
        p1, p2, pg = fpf.ply_material_strains(ex, ey, gxy, 30.0 + 180.0)
        self.assertAlmostEqual(e1, p1, places=9)
        self.assertAlmostEqual(e2, p2, places=9)
        self.assertAlmostEqual(g12, pg, places=9)

    def test_material_stresses_simple_multiply(self):
        q11, q12, q22, q66 = Q
        s1, s2, t12 = fpf.ply_material_stresses(1.0e-3, 0.0, 0.0,
                                                q11, q12, q22, q66)
        self.assertAlmostEqual(s1, q11 * 1.0e-3, places=6)
        self.assertAlmostEqual(s2, q12 * 1.0e-3, places=6)
        self.assertEqual(t12, 0.0)
        _, _, t12 = fpf.ply_material_stresses(0.0, 0.0, 1.0e-3,
                                              q11, q12, q22, q66)
        self.assertAlmostEqual(t12, q66 * 1.0e-3, places=6)


class TestTsaiWuIndex(unittest.TestCase):
    def test_fiber_tension_failure_at_allowable(self):
        self.assertAlmostEqual(
            fpf.tsai_wu_index(1500.0, 0.0, 0.0, *ALLOW), 1.0, places=9)

    def test_transverse_compression_failure_at_allowable(self):
        self.assertAlmostEqual(
            fpf.tsai_wu_index(0.0, -246.0, 0.0, *ALLOW), 1.0, places=9)

    def test_pure_shear_failure_at_allowable(self):
        self.assertAlmostEqual(
            fpf.tsai_wu_index(0.0, 0.0, 68.0, *ALLOW), 1.0, places=9)

    def test_symmetric_equal_allowables(self):
        # Xt = Xc kills the F1 linear term: +s1 and -s1 give the same FI.
        up = fpf.tsai_wu_index(600.0, 0.0, 0.0, *ALLOW)
        down = fpf.tsai_wu_index(-600.0, 0.0, 0.0, *ALLOW)
        self.assertAlmostEqual(up, down, places=9)
        self.assertAlmostEqual(up, (600.0 / 1500.0) ** 2, places=6)

    def test_zero_stress_zero_index(self):
        self.assertEqual(fpf.tsai_wu_index(0.0, 0.0, 0.0, *ALLOW), 0.0)

    def test_valueerror_nonpositive_allowables(self):
        cases = [(0.0, 1500.0, 40.0, 246.0, 68.0),
                 (1500.0, -1500.0, 40.0, 246.0, 68.0),
                 (1500.0, 1500.0, 0.0, 246.0, 68.0),
                 (1500.0, 1500.0, 40.0, 0.0, 68.0),
                 (1500.0, 1500.0, 40.0, 246.0, -68.0)]
        for bad in cases:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    fpf.tsai_wu_index(100.0, 50.0, 10.0, *bad)


class TestLaminateFirstPlyFailure(unittest.TestCase):
    def test_worked_example_indices_max_in_90_ply(self):
        indices = fpf.ply_failure_indices(PLIES, Q, ALLOW, NX, 0.0, 0.0,
                                          A_INV)
        self.assertEqual(len(indices), 8)
        self.assertAlmostEqual(indices[1], 0.3130, delta=2e-3)
        self.assertAlmostEqual(indices[6], 0.3130, delta=2e-3)
        self.assertGreater(indices[1], max(indices[0], max(indices[2:6]),
                                           indices[7]))
        # Transverse stress in the 90-deg ply, about 13.6 MPa.
        ex, ey, gxy = fpf.midplane_strains(*A_INV, NX, 0.0, 0.0)
        s1, s2, t12 = fpf.ply_material_stresses(
            *fpf.ply_material_strains(ex, ey, gxy, 90.0), *Q)
        self.assertAlmostEqual(s2, 13.6, delta=0.1)

    def test_ply_failure_indices_valueerror_guards(self):
        with self.assertRaises(ValueError):
            fpf.ply_failure_indices([], Q, ALLOW, NX, 0.0, 0.0, A_INV)
        with self.assertRaises(ValueError):
            fpf.ply_failure_indices(PLIES, Q[:3], ALLOW, NX, 0.0, 0.0, A_INV)
        with self.assertRaises(ValueError):
            fpf.ply_failure_indices(PLIES, Q, ALLOW[:4], NX, 0.0, 0.0, A_INV)
        with self.assertRaises(ValueError):
            fpf.ply_failure_indices(PLIES, Q, ALLOW, NX, 0.0, 0.0,
                                    A_INV[:3])
        with self.assertRaises(ValueError):
            fpf.ply_failure_indices(PLIES, Q, (1500.0, 1500.0, 0.0, 246.0,
                                               68.0), NX, 0.0, 0.0, A_INV)

    def test_first_ply_failure_worked_example(self):
        result = fpf.first_ply_failure(PLIES, Q, ALLOW, NX, 0.0, 0.0, A_INV)
        self.assertAlmostEqual(result["max_fi"], 0.3130, delta=2e-3)
        self.assertEqual(result["critical_ply_index"], 1)
        self.assertEqual(result["critical_ply_deg"], 90)
        self.assertAlmostEqual(result["fpf_scale_k"], 3.195, delta=0.01)
        self.assertAlmostEqual(result["fpf_load_nx"], 319.5, delta=0.5)
        self.assertEqual(result["reserve_factor"], result["fpf_scale_k"])

    def test_fpf_load_nx_and_alias(self):
        result = fpf.first_ply_failure(PLIES, Q, ALLOW, NX, 0.0, 0.0, A_INV)
        self.assertAlmostEqual(result["fpf_load_nx"],
                               result["fpf_scale_k"] * NX, places=9)
        alias = fpf.first_ply_failure_load(PLIES, Q, ALLOW, NX, 0.0, 0.0,
                                           A_INV)
        self.assertEqual(alias, result)

    def test_unidirectional_0_8_closed_form_at_fiber_failure(self):
        # [0]8 at Nx = Xt * t (t = 1.0 mm) drives sigma1 = Xt = 1500 MPa:
        # FI = 1 and k* = Xt / sigma1 = 1, the closed-form failure check.
        a_inv = fpf.a_inverse_compliance(
            *fpf.a_matrix_from_plies([0] * 8, Q, PLY_T))
        result = fpf.first_ply_failure([0] * 8, Q, ALLOW, 1500.0, 0.0, 0.0,
                                       a_inv)
        self.assertEqual(result["critical_ply_deg"], 0)
        self.assertAlmostEqual(result["max_fi"], 1.0, delta=1e-9)
        self.assertAlmostEqual(result["fpf_scale_k"], 1.0, delta=1e-9)
        self.assertAlmostEqual(result["reserve_factor"],
                               1500.0 / 1500.0, places=9)

    def test_unidirectional_0_8_quadratic_scaling(self):
        # sigma1 = Nx / t = 100 MPa; the Tsai-Wu index is quadratic,
        # so FI = (sigma1 / Xt)^2 and k* = 1 / FI = (Xt / sigma1)^2.
        a_inv = fpf.a_inverse_compliance(
            *fpf.a_matrix_from_plies([0] * 8, Q, PLY_T))
        result = fpf.first_ply_failure([0] * 8, Q, ALLOW, 100.0, 0.0, 0.0,
                                       a_inv)
        self.assertEqual(result["critical_ply_index"], 0)
        self.assertAlmostEqual(result["max_fi"], (100.0 / 1500.0) ** 2,
                               delta=1e-12)
        self.assertAlmostEqual(result["fpf_scale_k"], 225.0, delta=1e-9)
        self.assertAlmostEqual(result["fpf_load_nx"], 22500.0, delta=1e-6)

    def test_unidirectional_0_8_stress_round_trip(self):
        # The 0-ply stress recovered from the mid-plane strain equals
        # E1 * ex for the [0]8 case (uniaxial stress state).
        a_inv = fpf.a_inverse_compliance(
            *fpf.a_matrix_from_plies([0] * 8, Q, PLY_T))
        ex, ey, gxy = fpf.midplane_strains(*a_inv, 100.0, 0.0, 0.0)
        e1, e2, g12 = fpf.ply_material_strains(ex, ey, gxy, 0.0)
        s1, s2, t12 = fpf.ply_material_stresses(e1, e2, g12, *Q)
        self.assertAlmostEqual(s1, fpf.T300_E1 * ex, delta=1e-6)
        self.assertAlmostEqual(s2, 0.0, delta=1e-6)
        self.assertAlmostEqual(s1, 100.0, delta=1e-6)  # Nx / t

    def test_mirror_reversed_order_same_fpf(self):
        # Reversing the ply list leaves the A block and the FPF result
        # unchanged; only the per-ply index positions permute.
        stack = [0, 45, -45, 90, 0, 45, -45, 90]
        a_inv = fpf.a_inverse_compliance(
            *fpf.a_matrix_from_plies(stack, Q, PLY_T))
        forward = fpf.first_ply_failure(stack, Q, ALLOW, NX, 0.0, 0.0, a_inv)
        backward = fpf.first_ply_failure(list(reversed(stack)), Q, ALLOW,
                                         NX, 0.0, 0.0, a_inv)
        self.assertEqual(forward["max_fi"], backward["max_fi"])
        self.assertEqual(forward["critical_ply_deg"],
                         backward["critical_ply_deg"])
        self.assertEqual(forward["fpf_load_nx"], backward["fpf_load_nx"])
        fi_f = fpf.ply_failure_indices(stack, Q, ALLOW, NX, 0.0, 0.0, a_inv)
        fi_b = fpf.ply_failure_indices(list(reversed(stack)), Q, ALLOW,
                                       NX, 0.0, 0.0, a_inv)
        self.assertEqual(sorted(fi_f), sorted(fi_b))

    def test_mirror_of_spec_laminate_same_fpf(self):
        result = fpf.first_ply_failure(PLIES, Q, ALLOW, NX, 0.0, 0.0, A_INV)
        mirrored = fpf.first_ply_failure(list(reversed(PLIES)), Q, ALLOW,
                                         NX, 0.0, 0.0, A_INV)
        self.assertEqual(result, mirrored)

    def test_determinism_and_dict_keys(self):
        first = fpf.first_ply_failure(PLIES, Q, ALLOW, NX, 0.0, 0.0, A_INV)
        second = fpf.first_ply_failure(PLIES, Q, ALLOW, NX, 0.0, 0.0, A_INV)
        self.assertEqual(first, second)
        self.assertEqual(set(first.keys()),
                         {"max_fi", "critical_ply_index", "critical_ply_deg",
                          "fpf_scale_k", "fpf_load_nx", "reserve_factor"})
        self.assertEqual(fpf.ply_failure_indices(PLIES, Q, ALLOW, NX, 0.0,
                                                 0.0, A_INV),
                         fpf.ply_failure_indices(PLIES, Q, ALLOW, NX, 0.0,
                                                 0.0, A_INV))


if __name__ == "__main__":
    unittest.main(verbosity=2)
