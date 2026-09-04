"""Offline deterministic contract test for complex-number-algebra.

Runs with the standard library only: python3 test_complex_number_algebra.py
Exact float equality on rational results; math.isclose at 1e-12 on
transcendental identities. Exit 0 when all pass.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import complex_number_algebra_logic as cna


class TestRectAndArithmetic(unittest.TestCase):
    """Representation, modulus, argument, conjugate, + - * / ."""

    def test_rect_returns_tuple(self):
        self.assertEqual(cna.rect(3.0, 4.0), (3.0, 4.0))
        self.assertEqual(cna.rect(-2.5, 0.5), (-2.5, 0.5))
        self.assertIsInstance(cna.rect(1.0, 2.0), tuple)

    def test_modulus_345_exact(self):
        self.assertEqual(cna.modulus((3.0, 4.0)), 5.0)
        self.assertEqual(cna.modulus((0.0, 0.0)), 0.0)

    def test_modulus_overflow_safe(self):
        big = 1e200
        m = cna.modulus((big, big))
        self.assertTrue(math.isfinite(m))
        self.assertTrue(math.isclose(m, math.sqrt(2.0) * big, rel_tol=1e-15))

    def test_arg_quadrants_and_axes(self):
        self.assertEqual(cna.arg((1.0, 0.0)), 0.0)
        self.assertEqual(cna.arg((0.0, 1.0)), math.pi / 2)
        self.assertEqual(cna.arg((-1.0, 0.0)), math.pi)
        self.assertEqual(cna.arg((0.0, -1.0)), -math.pi / 2)
        self.assertEqual(cna.arg((0.0, 0.0)), 0.0)
        self.assertTrue(math.isclose(cna.arg((1.0, -1.0)), -math.pi / 4,
                                     abs_tol=1e-15))
        self.assertTrue(math.isclose(cna.arg((-1.0, -1.0)),
                                     -3 * math.pi / 4, abs_tol=1e-15))

    def test_conjugate_exact(self):
        self.assertEqual(cna.conjugate((3.0, 4.0)), (3.0, -4.0))
        self.assertEqual(cna.conjugate((-1.0, -2.0)), (-1.0, 2.0))
        self.assertEqual(cna.conjugate(cna.conjugate((3.0, 4.0))), (3.0, 4.0))

    def test_add_sub_exact(self):
        self.assertEqual(cna.complex_add((1.0, 2.0), (3.0, 4.0)), (4.0, 6.0))
        self.assertEqual(cna.complex_add((-5.0, 1.0), (2.0, -3.0)),
                         (-3.0, -2.0))
        self.assertEqual(cna.complex_add((1.0, 2.0), (0.0, 0.0)), (1.0, 2.0))
        self.assertEqual(cna.complex_sub((5.0, 6.0), (3.0, 4.0)), (2.0, 2.0))
        self.assertEqual(cna.complex_sub((1.0, 2.0), (1.0, 2.0)), (0.0, 0.0))

    def test_mul_worked_example_exact(self):
        # (3,4) * (2,-1) = (10, 5): the spec worked-example product.
        self.assertEqual(cna.complex_mul((3.0, 4.0), (2.0, -1.0)),
                         (10.0, 5.0))

    def test_mul_rational_exact(self):
        # (1+2i)(3-4i) = 11 + 2i; multiplication commutes; zero annihilates.
        self.assertEqual(cna.complex_mul((1.0, 2.0), (3.0, -4.0)),
                         (11.0, 2.0))
        self.assertEqual(cna.complex_mul((9.0, 8.0), (0.0, 0.0)), (0.0, 0.0))
        self.assertEqual(cna.complex_mul((3.0, 4.0), (2.0, -1.0)),
                         cna.complex_mul((2.0, -1.0), (3.0, 4.0)))

    def test_div_worked_example_exact(self):
        # (1+2i)/(3-4i) = (-0.2, 0.4) exactly per the spec derivation.
        self.assertEqual(cna.complex_div((1.0, 2.0), (3.0, -4.0)),
                         (-0.2, 0.4))
        # Division by a unit-modulus value: (1+2i)/i = 2-i.
        self.assertEqual(cna.complex_div((1.0, 2.0), (0.0, 1.0)), (2.0, -1.0))

    def test_div_zero_denominator_raises(self):
        with self.assertRaises(ValueError):
            cna.complex_div((1.0, 2.0), (0.0, 0.0))
        with self.assertRaises(ValueError):
            cna.complex_algebra((1.0, 2.0), (0.0, 0.0))

    def test_quotient_round_trip_by_mul(self):
        for z1, z2 in [((3.0, 4.0), (2.0, -1.0)),
                       ((-2.0, 5.0), (1.0, 1.0)),
                       ((5.0, -12.0), (-3.0, 4.0))]:
            q = cna.complex_div(z1, z2)
            back = cna.complex_mul(q, z2)
            self.assertTrue(cna.is_close(back, z1, tol=1e-12))


class TestPolarAndEuler(unittest.TestCase):
    """Polar form, Euler exponential form and round trips."""

    def test_polar_form(self):
        m, a = cna.polar((3.0, 4.0))
        self.assertEqual(m, 5.0)
        self.assertTrue(math.isclose(a, 0.9272952180016122, rel_tol=1e-14))
        m2, a2 = cna.polar((0.0, -1.0))
        self.assertEqual(m2, 1.0)
        self.assertEqual(a2, -math.pi / 2)

    def test_mag_phase_alias(self):
        for z in [(3.0, 4.0), (-2.0, -5.0), (0.0, -1.0)]:
            self.assertEqual(cna.mag_phase(z), cna.polar(z))

    def test_from_polar_axis_exact(self):
        re, im = cna.from_polar(1.0, math.pi / 2)
        self.assertTrue(math.isclose(re, 0.0, abs_tol=1e-12))
        self.assertEqual(im, 1.0)
        re2, im2 = cna.from_polar(2.0, math.pi)
        self.assertEqual(re2, -2.0)
        self.assertTrue(math.isclose(im2, 0.0, abs_tol=1e-12))

    def test_from_polar_negative_radius_raises(self):
        with self.assertRaises(ValueError):
            cna.from_polar(-1.0, 0.0)
        with self.assertRaises(ValueError):
            cna.from_polar(-0.5, math.pi)

    def test_polar_round_trip(self):
        for z in [(3.0, 4.0), (-2.0, 5.0), (0.0, -1.0), (1.0, 1.0),
                  (-3.0, -4.0), (5.0, -12.0), (0.5, -2.5)]:
            rt = cna.from_polar(*cna.polar(z))
            self.assertTrue(math.isclose(rt[0], z[0], abs_tol=1e-12))
            self.assertTrue(math.isclose(rt[1], z[1], abs_tol=1e-12))

    def test_exp_imag(self):
        self.assertEqual(cna.exp_imag(0.0), (1.0, 0.0))
        re, im = cna.exp_imag(math.pi / 2)
        self.assertTrue(math.isclose(re, 0.0, abs_tol=1e-12))
        self.assertTrue(math.isclose(im, 1.0, abs_tol=1e-12))

    def test_euler_identity(self):
        # e^(i*pi) + 1 = 0.
        total = cna.complex_add(cna.exp_imag(math.pi), (1.0, 0.0))
        self.assertTrue(math.isclose(total[0], 0.0, abs_tol=1e-12))
        self.assertTrue(math.isclose(total[1], 0.0, abs_tol=1e-12))


class TestDeMoivrePower(unittest.TestCase):
    """Integer powers via De Moivre's formula."""

    def test_pow_demoivre_worked_example_exact(self):
        # (1+i)^8 = 16 exactly (float noise on the real axis cleaned).
        self.assertEqual(cna.complex_pow((1.0, 1.0), 8), (16.0, 0.0))

    def test_pow_fourth_power_exact(self):
        # (1+i)^4 = -4 exactly.
        self.assertEqual(cna.complex_pow((1.0, 1.0), 4), (-4.0, 0.0))

    def test_pow_zero_cases(self):
        # Any nonzero base to the power 0 is 1; zero base to n > 0 is 0.
        self.assertEqual(cna.complex_pow((5.0, -3.0), 0), (1.0, 0.0))
        self.assertEqual(cna.complex_pow((0.0, 0.0), 3), (0.0, 0.0))
        self.assertEqual(cna.complex_pow((0.0, 0.0), 1), (0.0, 0.0))

    def test_pow_matches_repeated_mul(self):
        z = (3.0, 4.0)
        p2 = cna.complex_pow(z, 2)
        m2 = cna.complex_mul(z, z)
        self.assertTrue(cna.is_close(p2, m2, tol=1e-12))
        p3 = cna.complex_pow(z, 3)
        m3 = cna.complex_mul(cna.complex_mul(z, z), z)
        self.assertTrue(cna.is_close(p3, m3, tol=1e-12))

    def test_pow_negative_exponent_raises(self):
        with self.assertRaises(ValueError):
            cna.complex_pow((1.0, 1.0), -2)
        with self.assertRaises(ValueError):
            cna.complex_pow((3.0, 4.0), -1)

    def test_pow_zero_to_zero_raises(self):
        with self.assertRaises(ValueError):
            cna.complex_pow((0.0, 0.0), 0)


class TestRootsOfUnity(unittest.TestCase):
    """The n-th roots of unity and their identities."""

    def test_roots_length_and_first(self):
        for n in (1, 2, 3, 4, 5, 6, 8, 12):
            self.assertEqual(len(cna.roots_of_unity(n)), n)
        self.assertEqual(cna.roots_of_unity(1), [(1.0, 0.0)])
        self.assertEqual(cna.roots_of_unity(6)[0], (1.0, 0.0))

    def test_roots_fourth_exact(self):
        self.assertEqual(cna.roots_of_unity(4),
                         [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)])

    def test_root_raised_to_n_is_unity(self):
        for n in (2, 3, 4, 5, 6, 8):
            for k, root in enumerate(cna.roots_of_unity(n)):
                p = cna.complex_pow(root, n)
                self.assertTrue(math.isclose(p[0], 1.0, abs_tol=1e-12),
                                "n=%d k=%d re=%r" % (n, k, p[0]))
                self.assertTrue(math.isclose(p[1], 0.0, abs_tol=1e-12),
                                "n=%d k=%d im=%r" % (n, k, p[1]))

    def test_roots_sum_to_zero(self):
        for n in (2, 3, 4, 5):
            s = (0.0, 0.0)
            for r in cna.roots_of_unity(n):
                s = (s[0] + r[0], s[1] + r[1])
            self.assertTrue(math.isclose(s[0], 0.0, abs_tol=1e-12))
            self.assertTrue(math.isclose(s[1], 0.0, abs_tol=1e-12))

    def test_roots_unit_modulus(self):
        for root in cna.roots_of_unity(5):
            self.assertTrue(math.isclose(cna.modulus(root), 1.0,
                                         abs_tol=1e-12))

    def test_roots_non_positive_n_raises(self):
        with self.assertRaises(ValueError):
            cna.roots_of_unity(0)
        with self.assertRaises(ValueError):
            cna.roots_of_unity(-3)


class TestConvenienceAndDeterminism(unittest.TestCase):
    """is_close, the complex_algebra dict and determinism."""

    def test_is_close_tolerance(self):
        self.assertTrue(cna.is_close((1.0, 2.0), (1.0000000005, 2.0)))
        self.assertFalse(cna.is_close((1.0, 2.0), (1.0000000015, 2.0)))
        self.assertTrue(cna.is_close((1.0, 2.0), (1.0000000015, 2.0),
                                     tol=1e-8))
        self.assertFalse(cna.is_close((1.0, 2.0), (1.0, 2.000000001),
                                      tol=1e-10))

    def test_conjugate_identity_exact(self):
        # z * conj(z) = |z|^2: (3+4i)(3-4i) = 25 exactly.
        z = (3.0, 4.0)
        prod = cna.complex_mul(z, cna.conjugate(z))
        self.assertEqual(prod, (25.0, 0.0))
        self.assertEqual(prod[0], cna.modulus(z) ** 2)

    def test_complex_algebra_keys(self):
        d = cna.complex_algebra((3.0, 4.0), (2.0, -1.0))
        self.assertEqual(set(d.keys()),
                         {"z1", "z2", "sum", "difference", "product",
                          "quotient", "conjugate_z1", "modulus_z1",
                          "argument_z1_deg", "polar_z1"})
        self.assertNotIn("power_z1_n", d)
        self.assertNotIn("roots_n", d)
        dn = cna.complex_algebra((3.0, 4.0), (2.0, -1.0), n=4)
        self.assertIn("power_z1_n", dn)
        self.assertIn("roots_n", dn)
        # Deterministic: no RNG, run-to-run identical dicts.
        self.assertEqual(d, cna.complex_algebra((3.0, 4.0), (2.0, -1.0)))
        self.assertEqual(dn, cna.complex_algebra((3.0, 4.0), (2.0, -1.0),
                                                 n=4))

    def test_complex_algebra_values_exact(self):
        d = cna.complex_algebra((3.0, 4.0), (2.0, -1.0))
        self.assertEqual(d["sum"], (5.0, 3.0))
        self.assertEqual(d["difference"], (1.0, 5.0))
        self.assertEqual(d["product"], (10.0, 5.0))
        self.assertEqual(d["quotient"], (0.4, 2.2))
        self.assertEqual(d["conjugate_z1"], (3.0, -4.0))
        self.assertEqual(d["modulus_z1"], 5.0)
        self.assertTrue(math.isclose(d["argument_z1_deg"],
                                     53.13010235415598, rel_tol=1e-12))
        self.assertEqual(d["polar_z1"], (5.0, 0.9272952180016122))

    def test_complex_algebra_with_n_values(self):
        d = cna.complex_algebra((3.0, 4.0), (2.0, -1.0), n=4)
        self.assertEqual(d["roots_n"],
                         [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)])
        p = d["power_z1_n"]
        self.assertTrue(math.isclose(p[0], -527.0, abs_tol=1e-9))
        self.assertTrue(math.isclose(p[1], -336.0, abs_tol=1e-9))
        self.assertEqual(cna.roots_of_unity(8), cna.roots_of_unity(8))


if __name__ == "__main__":
    unittest.main(verbosity=1)
