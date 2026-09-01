#!/usr/bin/env python3
"""Gate 3 contract test: structures/fem/plate-buckling (stdlib unittest).

Pins the worked anchors of scripts/plate_buckling_logic.py, the
coefficient boundaries (aspect ratio and edge condition dependence),
the stress-form scalings, the combined interaction check, the von
Karman effective width and the ValueError cases for non-positive,
non-finite or unknown inputs. Offline, deterministic, no network.
"""

import math
import unittest

import plate_buckling_logic as pb


class CompressionCoefficientTests(unittest.TestCase):
    def test_simply_supported_long_plate(self):
        # a/b = 2 with m = 2 gives (1 + 1)^2 = 4.0; a/b = 3 and a/b = 1
        # also minimize to 4.0 (m = 3 and m = 1 respectively).
        self.assertAlmostEqual(pb.compression_coefficient(2.0, "ssss"), 4.0, places=6)
        self.assertAlmostEqual(pb.compression_coefficient(3.0, "ssss"), 4.0, places=6)
        self.assertAlmostEqual(pb.compression_coefficient(1.0, "ssss"), 4.0, places=6)

    def test_simply_supported_short_plate(self):
        # a/b = 1.5 minimizes at m = 2: (2/1.5 + 1.5/2)^2 = 4.3403.
        self.assertAlmostEqual(
            pb.compression_coefficient(1.5, "ssss"), 4.340277777777777, places=6
        )
        # a/b = 0.5 minimizes at m = 1: (2 + 0.5)^2 = 6.25.
        self.assertAlmostEqual(pb.compression_coefficient(0.5, "ssss"), 6.25, places=6)

    def test_clamped_long_plate_approximation(self):
        self.assertAlmostEqual(pb.compression_coefficient(2.0, "cccc"), 6.97, places=6)
        self.assertAlmostEqual(
            pb.compression_coefficient(2.0, "clamped"), 6.97, places=6
        )

    def test_coefficient_monotone_under_support_restraint(self):
        # For the same long panel the clamped coefficient exceeds the
        # simply supported one.
        self.assertGreater(
            pb.compression_coefficient(2.0, "cccc"),
            pb.compression_coefficient(2.0, "ssss"),
        )

    def test_clamped_short_plate_raises(self):
        with self.assertRaises(ValueError):
            pb.compression_coefficient(0.5, "cccc")

    def test_unknown_edge_condition_raises(self):
        with self.assertRaises(ValueError):
            pb.compression_coefficient(2.0, "eeff")
        with self.assertRaises(ValueError):
            pb.compression_coefficient(2.0, 42)


class ShearCoefficientTests(unittest.TestCase):
    def test_simply_supported_formulas(self):
        # a/b >= 1: k_s = 5.34 + 4/a_r^2.
        self.assertAlmostEqual(pb.shear_coefficient(2.0, "ssss"), 6.34, places=6)
        self.assertAlmostEqual(pb.shear_coefficient(1.0, "ssss"), 9.34, places=6)
        # a/b < 1: k_s = 5.34 * a_r^2 + 4.
        self.assertAlmostEqual(pb.shear_coefficient(0.5, "ssss"), 5.335, places=6)

    def test_clamped_formulas(self):
        # a/b >= 1: k_s = 8.98 + 5.6/a_r^2.
        self.assertAlmostEqual(pb.shear_coefficient(2.0, "cccc"), 10.38, places=6)
        # a/b < 1: k_s = 8.98 * a_r^2 + 5.6.
        self.assertAlmostEqual(pb.shear_coefficient(0.5, "cccc"), 7.845, places=6)

    def test_clamped_exceeds_simply_supported(self):
        self.assertGreater(
            pb.shear_coefficient(2.0, "cccc"), pb.shear_coefficient(2.0, "ssss")
        )

    def test_alias_resolution(self):
        self.assertAlmostEqual(
            pb.shear_coefficient(2.0, "simply supported"), 6.34, places=6
        )
        self.assertAlmostEqual(pb.shear_coefficient(2.0, "fixed"), 10.38, places=6)


class CriticalStressTests(unittest.TestCase):
    def test_compression_anchor(self):
        # Aluminum skin: E = 70 GPa, nu = 0.33, t = 2 mm, b = 150 mm,
        # k = 4.0 gives sigma_cr = 45.94 MPa.
        sig = pb.compression_buckling_stress(70e9, 0.33, 0.002, 0.15, 4.0)
        self.assertAlmostEqual(sig / 1e6, 45.94386849885944, places=6)

    def test_shear_anchor(self):
        # Aluminum web: t = 1.5 mm, b = 250 mm, k_s = 6.34 gives
        # tau_cr = 14.75 MPa.
        tau = pb.shear_buckling_stress(70e9, 0.33, 0.0015, 0.25, 6.34)
        self.assertAlmostEqual(tau / 1e6, 14.746258893065168, places=6)

    def test_thickness_to_width_ratio_scaling(self):
        # The critical stress scales with (t/b)^2: doubling t/b
        # quadruples the critical stress.
        base = pb.compression_buckling_stress(70e9, 0.33, 0.002, 0.15, 4.0)
        doubled = pb.compression_buckling_stress(70e9, 0.33, 0.004, 0.15, 4.0)
        self.assertAlmostEqual(doubled / base, 4.0, places=10)

    def test_modulus_scaling(self):
        # The critical stress scales linearly with E.
        base = pb.compression_buckling_stress(70e9, 0.33, 0.002, 0.15, 4.0)
        stiffer = pb.compression_buckling_stress(105e9, 0.33, 0.002, 0.15, 4.0)
        self.assertAlmostEqual(stiffer / base, 1.5, places=10)

    def test_coefficient_scaling(self):
        # Clamped long plate (k = 6.97) vs simply supported (k = 4.0)
        # at the same geometry.
        ss = pb.compression_buckling_stress(70e9, 0.33, 0.002, 0.15, 4.0)
        cc = pb.compression_buckling_stress(70e9, 0.33, 0.002, 0.15, 6.97)
        self.assertAlmostEqual(cc / ss, 6.97 / 4.0, places=10)

    def test_poisson_effect(self):
        # A higher Poisson ratio raises the critical stress: the
        # denominator 12 * (1 - nu^2) shrinks as nu grows, so the
        # lateral restraint of the plate increases its buckling load.
        low = pb.compression_buckling_stress(70e9, 0.30, 0.002, 0.15, 4.0)
        high = pb.compression_buckling_stress(70e9, 0.40, 0.002, 0.15, 4.0)
        self.assertGreater(high, low)


class PanelCheckTests(unittest.TestCase):
    def test_compression_panel_anchor(self):
        r = pb.compression_panel_check(70e9, 0.33, 0.002, 0.3, 0.15, "ssss", 30e6)
        self.assertAlmostEqual(r["coefficient"], 4.0, places=6)
        self.assertAlmostEqual(r["critical_stress"] / 1e6, 45.94386849885944, places=6)
        self.assertAlmostEqual(r["margin_of_safety"], 0.5314622832953144, places=6)
        self.assertTrue(r["stable"])

    def test_compression_panel_ultimate_scale(self):
        # Same skin against an ultimate stress of 46 MPa is marginal:
        # the margin goes negative above the critical stress.
        r = pb.compression_panel_check(70e9, 0.33, 0.002, 0.3, 0.15, "ssss", 46e6)
        self.assertLess(r["margin_of_safety"], 0.0)
        self.assertFalse(r["stable"])

    def test_shear_panel_anchor(self):
        r = pb.shear_panel_check(70e9, 0.33, 0.0015, 0.5, 0.25, "ssss", 8e6)
        self.assertAlmostEqual(r["coefficient"], 6.34, places=6)
        self.assertAlmostEqual(r["critical_stress"] / 1e6, 14.746258893065168, places=6)
        self.assertAlmostEqual(r["margin_of_safety"], 0.843282361633146, places=6)
        self.assertTrue(r["stable"])

    def test_aspect_ratio_shortens_critical_stress(self):
        # The same web with a/b = 0.5 has k_s = 5.335 instead of 6.34.
        short = pb.shear_panel_check(70e9, 0.33, 0.0015, 0.125, 0.25, "ssss", 8e6)
        long = pb.shear_panel_check(70e9, 0.33, 0.0015, 0.5, 0.25, "ssss", 8e6)
        self.assertLess(short["critical_stress"], long["critical_stress"])


class InteractionTests(unittest.TestCase):
    def test_anchor(self):
        r = pb.interaction_index(
            30e6, 45.94386849885944e6, 8e6, 14.746258893065168e6
        )
        self.assertAlmostEqual(r["index"], 0.9472883221819679, places=6)
        self.assertTrue(r["stable"])
        self.assertAlmostEqual(r["margin_of_safety"], 0.05564480906575198, places=6)

    def test_linear_compression_quadratic_shear(self):
        # Doubling the shear stress quadruples its interaction term;
        # a negligible compression term keeps the ratio clean.
        base = pb.interaction_index(1.0, 45.94386849885944e6, 8e6, 14.746258893065168e6)
        doubled = pb.interaction_index(1.0, 45.94386849885944e6, 16e6, 14.746258893065168e6)
        self.assertAlmostEqual(doubled["index"] / base["index"], 4.0, places=3)

    def test_unstable_case(self):
        r = pb.interaction_index(40e6, 45.94e6, 10e6, 14.75e6)
        self.assertGreater(r["index"], 1.0)
        self.assertFalse(r["stable"])
        self.assertLess(r["margin_of_safety"], 0.0)


class EffectiveWidthTests(unittest.TestCase):
    def test_anchor(self):
        b_e = pb.effective_width(70e9, 200e6, 0.002)
        self.assertAlmostEqual(b_e * 1000, 71.0914903487049, places=6)

    def test_edge_stress_dependence(self):
        # A higher edge stress gives a smaller effective width.
        low = pb.effective_width(70e9, 100e6, 0.002)
        high = pb.effective_width(70e9, 400e6, 0.002)
        self.assertGreater(low, high)

    def test_thickness_dependence(self):
        # Effective width scales linearly with thickness.
        t1 = pb.effective_width(70e9, 200e6, 0.002)
        t2 = pb.effective_width(70e9, 200e6, 0.004)
        self.assertAlmostEqual(t2 / t1, 2.0, places=10)


class InvalidInputTests(unittest.TestCase):
    def test_non_positive_inputs(self):
        for fn, args in [
            (pb.compression_coefficient, (0.0, "ssss")),
            (pb.compression_coefficient, (-2.0, "ssss")),
            (pb.shear_coefficient, (0.0, "ssss")),
            (pb.shear_coefficient, (-1.0, "cccc")),
            (pb.compression_buckling_stress, (0.0, 0.33, 0.002, 0.15, 4.0)),
            (pb.compression_buckling_stress, (70e9, 0.33, 0.0, 0.15, 4.0)),
            (pb.compression_buckling_stress, (70e9, 0.33, 0.002, 0.0, 4.0)),
            (pb.compression_buckling_stress, (70e9, 0.33, 0.002, 0.15, 0.0)),
            (pb.shear_buckling_stress, (70e9, 0.33, 0.002, 0.15, -6.34)),
            (pb.compression_panel_check, (70e9, 0.33, 0.002, 0.3, 0.15, "ssss", 0.0)),
            (pb.shear_panel_check, (70e9, 0.33, 0.002, 0.3, 0.15, "ssss", -8e6)),
            (pb.interaction_index, (30e6, 0.0, 8e6, 14.75e6)),
            (pb.interaction_index, (30e6, 45.94e6, 8e6, -14.75e6)),
            (pb.effective_width, (70e9, 0.0, 0.002)),
            (pb.effective_width, (70e9, 200e6, 0.0)),
        ]:
            with self.assertRaises(ValueError, msg="args=%r" % (args,)):
                fn(*args)

    def test_invalid_poisson(self):
        for nu in (-0.1, 0.5, 0.7):
            with self.assertRaises(ValueError):
                pb.compression_buckling_stress(70e9, nu, 0.002, 0.15, 4.0)
            with self.assertRaises(ValueError):
                pb.shear_buckling_stress(70e9, nu, 0.0015, 0.25, 6.34)

    def test_non_finite_inputs(self):
        for bad in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                pb.compression_coefficient(bad, "ssss")
            with self.assertRaises(ValueError):
                pb.shear_buckling_stress(bad, 0.33, 0.002, 0.15, 6.34)
            with self.assertRaises(ValueError):
                pb.compression_buckling_stress(70e9, 0.33, bad, 0.15, 4.0)

    def test_non_numeric_inputs(self):
        with self.assertRaises(ValueError):
            pb.compression_coefficient("two", "ssss")
        with self.assertRaises(ValueError):
            pb.compression_buckling_stress(70e9, 0.33, True, 0.15, 4.0)
        with self.assertRaises(ValueError):
            pb.interaction_index(30e6, 45.94e6, "eight", 14.75e6)
        with self.assertRaises(ValueError):
            pb.effective_width(70e9, 200e6, None)


if __name__ == "__main__":
    unittest.main(verbosity=2)
