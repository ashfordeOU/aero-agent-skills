#!/usr/bin/env python3
"""Contract test for laminate-bending-stiffness (structures/composites).

Exercises the SKILL.md workflow steps against
laminate_bending_stiffness_logic.py: step 2 (ply_rotated_stiffness),
step 3 (b_coupling_matrix, the z-squared bending-extension coupling
integral), step 4 (d_bending_matrix, the z-cubed bending integral),
step 5 (abd_stiffness_matrices, the full ABD assembly for symmetric
and unsymmetric laminates), step 6 (laminate_bending_terms, the D11
D22 D12 D66 hand-off to laminate-plate-buckling), step 7
(equivalent_flexural_constants) and step 8 (laminate_bending_report,
the one-shot report). Offline, deterministic, stdlib unittest only.
No exact-float equality on computed sums; every numeric assert is
tolerant (assertAlmostEqual with delta, or math.isclose).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import laminate_bending_stiffness_logic as lbs

E1 = 181.0e9
E2 = 10.3e9
NU12 = 0.28
G12 = 7.17e9
T = 0.000125

SYM_0_90S = [(0.0, T), (90.0, T), (90.0, T), (0.0, T)]
UNSYM_0_90_2T = [(0.0, T), (90.0, T), (0.0, T), (90.0, T)]
SYM_ANGLE_PLY = [(45.0, T), (-45.0, T), (-45.0, T), (45.0, T)]


def leading_minors_positive(d6):
    """True if the symmetric 3x3 D matrix's leading principal minors
    (D11, D11*D22-D12^2, det of the full 3x3) are all positive."""
    d11, d12, d16, d22, d26, d66 = d6
    m1 = d11
    m2 = d11 * d22 - d12 * d12
    m3 = (d11 * (d22 * d66 - d26 * d26)
          - d12 * (d12 * d66 - d26 * d16)
          + d16 * (d12 * d26 - d22 * d16))
    return m1 > 0.0 and m2 > 0.0 and m3 > 0.0


class LaminateBendingStiffnessTests(unittest.TestCase):
    """Step 1: fixed ply constants (AS4/3501-6 carbon/epoxy) and the
    worked example stacks feed every test below."""

    # -- step 6: the D11, D22, D12, D66 hand-off (worked example) ----

    def test_worked_example_symmetric_bending_terms(self):
        """step 6, laminate_bending_terms on the [0/90]s stack."""
        d11, d22, d12, d66 = lbs.laminate_bending_terms(SYM_0_90S, E1, E2, NU12, G12)
        self.assertAlmostEqual(d11, 1.67060433677, delta=1e-6)
        self.assertAlmostEqual(d22, 0.331034179627, delta=1e-6)
        self.assertAlmostEqual(d12, 0.0301762962953, delta=1e-6)
        self.assertAlmostEqual(d66, 0.0746875, delta=1e-6)

    # -- step 5: the full ABD assembly --------------------------------

    def test_worked_example_symmetric_a_terms(self):
        """step 5, abd_stiffness_matrices A block on the [0/90]s stack."""
        r = lbs.abd_stiffness_matrices(SYM_0_90S, E1, E2, NU12, G12)
        a11, a12, a16, a22, a26, a66 = r["a"]
        self.assertAlmostEqual(a11, 48039324.3936, delta=1.0)
        self.assertAlmostEqual(a22, 48039324.3936, delta=1.0)
        self.assertAlmostEqual(a12, 1448462.22217, delta=1.0)
        self.assertAlmostEqual(a66, 3585000.0, delta=1.0)

    def test_worked_example_symmetric_d_block_matches_terms(self):
        """step 5, abd_stiffness_matrices D block on the [0/90]s stack."""
        r = lbs.abd_stiffness_matrices(SYM_0_90S, E1, E2, NU12, G12)
        d11, d12, _d16, d22, _d26, d66 = r["d"]
        self.assertAlmostEqual(d11, 1.67060433677, delta=1e-6)
        self.assertAlmostEqual(d22, 0.331034179627, delta=1e-6)
        self.assertAlmostEqual(d12, 0.0301762962953, delta=1e-6)
        self.assertAlmostEqual(d66, 0.0746875, delta=1e-6)

    def test_a_matrix_independent_of_stacking_order(self):
        """step 5, the A block of [0/90]s and [0/90]2T (same ply set,
        different order) agree within a relative tolerance."""
        a1 = lbs.abd_stiffness_matrices(SYM_0_90S, E1, E2, NU12, G12)["a"]
        a2 = lbs.abd_stiffness_matrices(UNSYM_0_90_2T, E1, E2, NU12, G12)["a"]
        for x, y in zip(a1, a2):
            self.assertTrue(math.isclose(x, y, rel_tol=1e-9, abs_tol=1e-6))

    def test_a_consistency_with_closed_form(self):
        """step 5, the A block equals the closed form A_ij = sum_k
        Qbar_ij,k t_k, re-derived in-test with ply_rotated_stiffness
        (step 2), never by importing the sibling leaf's module."""
        a = lbs.abd_stiffness_matrices(SYM_0_90S, E1, E2, NU12, G12)["a"]
        expected = [0.0] * 6
        for theta, t in SYM_0_90S:
            qbar = lbs.ply_rotated_stiffness(E1, E2, NU12, G12, theta)
            for k in range(6):
                expected[k] += qbar[k] * t
        for got, want in zip(a, expected):
            self.assertTrue(math.isclose(got, want, rel_tol=1e-9, abs_tol=1e-9))

    # -- step 3: the B == 0 symmetric-stack identity ------------------

    def test_symmetric_b_zero_identity_0_90s(self):
        """step 3, b_coupling_matrix vanishes for the mirror-symmetric
        [0/90]s stack (residue is machine-precision cancellation)."""
        b = lbs.b_coupling_matrix(SYM_0_90S, E1, E2, NU12, G12)
        self.assertLess(max(abs(x) for x in b), 1e-9)

    def test_symmetric_b_zero_identity_angle_ply(self):
        """step 3, b_coupling_matrix vanishes for the mirror-symmetric
        balanced angle-ply [+45/-45]s stack."""
        b = lbs.b_coupling_matrix(SYM_ANGLE_PLY, E1, E2, NU12, G12)
        self.assertLess(max(abs(x) for x in b), 1e-9)

    def test_unsymmetric_b_coupling_nonzero(self):
        """step 3, b_coupling_matrix on the unsymmetric [0/90]2T stack
        gives a real, nonzero bending-extension coupling."""
        b = lbs.b_coupling_matrix(UNSYM_0_90_2T, E1, E2, NU12, G12)
        max_abs = max(abs(x) for x in b)
        self.assertAlmostEqual(max_abs, 2679.14031429, delta=1e-3)

    def test_unsymmetric_b11_equals_negative_b22(self):
        """step 3, B11 and B22 of the unsymmetric stack are equal in
        magnitude and opposite in sign."""
        b11, _b12, _b16, b22, _b26, _b66 = lbs.b_coupling_matrix(
            UNSYM_0_90_2T, E1, E2, NU12, G12)
        self.assertTrue(math.isclose(b11, -b22, rel_tol=1e-6))

    def test_unsymmetric_d_terms(self):
        """step 6, laminate_bending_terms on the unsymmetric stack
        reports D11 = D22, softer than the symmetric [0/90]s case."""
        d11, d22, _d12, _d66 = lbs.laminate_bending_terms(
            UNSYM_0_90_2T, E1, E2, NU12, G12)
        self.assertAlmostEqual(d11, 1.0008192582, delta=1e-6)
        self.assertTrue(math.isclose(d11, d22, rel_tol=1e-6))

    # -- step 4: the D matrix and its positive-definiteness -----------

    def test_positive_definite_d_0_90s(self):
        """step 4, d_bending_matrix on [0/90]s is positive definite."""
        d = lbs.d_bending_matrix(SYM_0_90S, E1, E2, NU12, G12)
        self.assertTrue(leading_minors_positive(d))

    def test_positive_definite_d_unsymmetric(self):
        """step 4, d_bending_matrix on [0/90]2T is positive definite."""
        d = lbs.d_bending_matrix(UNSYM_0_90_2T, E1, E2, NU12, G12)
        self.assertTrue(leading_minors_positive(d))

    def test_positive_definite_d_angle_ply_nonzero_d16(self):
        """step 4, d_bending_matrix on [+45/-45]s is positive definite
        even with D16 = D26 nonzero."""
        d = lbs.d_bending_matrix(SYM_ANGLE_PLY, E1, E2, NU12, G12)
        self.assertTrue(leading_minors_positive(d))
        self.assertGreater(abs(d[2]), 1e-3)

    def test_balanced_a16_a26_zero(self):
        """step 5, the balanced symmetric [+45/-45]s stack has A16 and
        A26 exactly zero (bitwise balanced cancellation)."""
        a = lbs.abd_stiffness_matrices(SYM_ANGLE_PLY, E1, E2, NU12, G12)["a"]
        self.assertEqual(a[2], 0.0)
        self.assertEqual(a[4], 0.0)

    def test_balanced_d16_d26_nonzero(self):
        """step 4, the same balanced [+45/-45]s stack has D16 and D26
        NONZERO, the reason the z-cubed integral cannot be skipped."""
        d = lbs.d_bending_matrix(SYM_ANGLE_PLY, E1, E2, NU12, G12)
        self.assertAlmostEqual(d[2], 0.334892539286, delta=1e-6)
        self.assertAlmostEqual(d[4], 0.334892539286, delta=1e-6)

    def test_cross_ply_d16_d26_near_zero(self):
        """step 4, the cross-ply [0/90]s stack has D16 and D26 below
        the 1e-9 N m machine-precision floor."""
        d = lbs.d_bending_matrix(SYM_0_90S, E1, E2, NU12, G12)
        self.assertLess(abs(d[2]), 1e-9)
        self.assertLess(abs(d[4]), 1e-9)

    # -- step 7: isotropic reduction and equivalent flexural constants

    def test_isotropic_reduction_d11(self):
        """step 4/7, a single isotropic layer reproduces the classic
        D = E h^3 / (12 (1 - nu^2)) plate result within 1e-9 relative."""
        e, nu, h = 70.0e9, 0.3, 0.002
        g = e / (2.0 * (1.0 + nu))
        d11, _d22, _d12, _d66 = lbs.laminate_bending_terms(
            [(0.0, h)], e, e, nu, g)
        classic = e * h ** 3 / (12.0 * (1.0 - nu ** 2))
        self.assertTrue(math.isclose(d11, classic, rel_tol=1e-9))
        self.assertAlmostEqual(d11, 51.2820512821, delta=1e-6)

    def test_isotropic_equivalent_flexural_constants(self):
        """step 7, equivalent_flexural_constants recovers E, G and nu
        of the isotropic layer within 1e-9 relative."""
        e, nu, h = 70.0e9, 0.3, 0.002
        g = e / (2.0 * (1.0 + nu))
        d11, _d22, _d12, d66 = lbs.laminate_bending_terms(
            [(0.0, h)], e, e, nu, g)
        e_bx, _e_by, g_bxy, nu_bxy = lbs.equivalent_flexural_constants(
            d11, d11, nu * d11, d66, h)
        self.assertTrue(math.isclose(e_bx, e, rel_tol=1e-9))
        self.assertTrue(math.isclose(g_bxy, g, rel_tol=1e-9))
        self.assertTrue(math.isclose(nu_bxy, nu, rel_tol=1e-9))

    def test_equivalent_flexural_constants_symmetric_stack(self):
        """step 7, equivalent_flexural_constants on the [0/90]s bending
        terms gives the flexural E, G and nu of the cross-ply plate."""
        d11, d22, d12, d66 = lbs.laminate_bending_terms(
            SYM_0_90S, E1, E2, NU12, G12)
        t_total = 4.0 * T
        e_bx, e_by, g_bxy, nu_bxy = lbs.equivalent_flexural_constants(
            d11, d22, d12, d66, t_total)
        self.assertAlmostEqual(e_bx / 1e9, 160.113939519, delta=1e-3)
        self.assertAlmostEqual(e_by / 1e9, 31.7269538028, delta=1e-3)
        self.assertAlmostEqual(g_bxy / 1e9, 7.17, delta=1e-6)
        self.assertAlmostEqual(nu_bxy, 0.0911576451995, delta=1e-6)

    # -- step 8: the one-shot report ----------------------------------

    def test_report_keys_and_b_max_abs(self):
        """step 8, laminate_bending_report returns the full key set
        and the coupling magnitude b_max_abs for the [0/90]s stack."""
        rep = lbs.laminate_bending_report(SYM_0_90S, E1, E2, NU12, G12)
        expected_keys = {"a", "b", "d", "d11", "d22", "d12", "d66",
                          "t_total", "b_max_abs"}
        self.assertEqual(set(rep.keys()), expected_keys)
        self.assertAlmostEqual(rep["b_max_abs"], 8.52651282912e-14, delta=1e-9)
        self.assertAlmostEqual(rep["t_total"], 4.0 * T, delta=1e-12)

    def test_report_determinism(self):
        """step 9, two consecutive one-shot calls on the same stack
        return identical dicts (no randomness anywhere)."""
        rep1 = lbs.laminate_bending_report(UNSYM_0_90_2T, E1, E2, NU12, G12)
        rep2 = lbs.laminate_bending_report(UNSYM_0_90_2T, E1, E2, NU12, G12)
        self.assertEqual(rep1, rep2)

    # -- step 2: the rotated ply stiffness integrand -------------------

    def test_ply_rotated_stiffness_0_degree_no_shear_coupling(self):
        """step 2, ply_rotated_stiffness at theta = 0 has no shear
        coupling terms Qbar16 and Qbar26."""
        qbar = lbs.ply_rotated_stiffness(E1, E2, NU12, G12, 0.0)
        self.assertAlmostEqual(qbar[2], 0.0, delta=1e-6)
        self.assertAlmostEqual(qbar[4], 0.0, delta=1e-6)

    # -- ValueError rejections (step 1, input validation) --------------

    def test_valueerror_negative_ply_thickness(self):
        """step 1, a negative ply thickness raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            lbs.b_coupling_matrix([(0.0, -T)], E1, E2, NU12, G12)
        self.assertIn("ply thickness must be a positive number", str(ctx.exception))

    def test_valueerror_zero_ply_thickness(self):
        """step 1, a zero ply thickness raises ValueError."""
        with self.assertRaises(ValueError):
            lbs.d_bending_matrix([(0.0, 0.0)], E1, E2, NU12, G12)

    def test_valueerror_boolean_ply_thickness(self):
        """step 1, a boolean ply thickness raises ValueError."""
        with self.assertRaises(ValueError):
            lbs.abd_stiffness_matrices([(0.0, True)], E1, E2, NU12, G12)

    def test_valueerror_zero_modulus_e1(self):
        """step 1, a zero E1 raises ValueError from ply_rotated_stiffness."""
        with self.assertRaises(ValueError) as ctx:
            lbs.ply_rotated_stiffness(0.0, E2, NU12, G12, 0.0)
        self.assertIn("modulus E1 must be a positive number", str(ctx.exception))

    def test_valueerror_boolean_modulus(self):
        """step 1, a boolean modulus raises ValueError."""
        with self.assertRaises(ValueError):
            lbs.ply_rotated_stiffness(True, E2, NU12, G12, 0.0)

    def test_valueerror_nu12_out_of_range(self):
        """step 1, nu12 outside [0, 1) raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            lbs.ply_rotated_stiffness(E1, E2, 1.5, G12, 0.0)
        self.assertIn("poisson ratio nu12 must be in [0, 1)", str(ctx.exception))

    def test_valueerror_empty_stack(self):
        """step 1, an empty ply list raises ValueError."""
        with self.assertRaises(ValueError) as ctx:
            lbs.b_coupling_matrix([], E1, E2, NU12, G12)
        self.assertIn("at least one ply", str(ctx.exception))

    def test_valueerror_zero_total_thickness(self):
        """step 1/7, a zero t_total raises ValueError in
        equivalent_flexural_constants."""
        with self.assertRaises(ValueError) as ctx:
            lbs.equivalent_flexural_constants(1.0, 1.0, 0.1, 0.5, 0.0)
        self.assertIn("total thickness must be a positive number", str(ctx.exception))

    def test_valueerror_non_positive_definite_d(self):
        """step 7, a non-positive-definite D pair raises ValueError
        with the D11/D22/D12 values quoted in the message."""
        with self.assertRaises(ValueError) as ctx:
            lbs.equivalent_flexural_constants(1.0, 1.0, 2.0, 0.5, 1.0)
        self.assertIn("not positive definite", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
