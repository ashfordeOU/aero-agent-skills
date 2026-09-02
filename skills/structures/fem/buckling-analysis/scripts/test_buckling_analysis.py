#!/usr/bin/env python3
"""Gate 3 contract test: Euler column buckling analysis.

Exercises scripts/buckling_analysis_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - critical
buckling load Pcr = pi^2*E*I/(K*L)^2, effective length factor K for
pinned, fixed and cantilever end conditions, slenderness ratio and
radius of gyration, the buckling stress check, the transition
slenderness classification, the full column check with margin of
safety, and ValueError on invalid input.

Physically meaningful anchors (verified by running the logic):
- Steel column E = 200 GPa, I = 1e-6 m^4, L = 3 m: Pcr = 219.325 kN
  pinned-pinned (K = 1), 877.298 kN fixed-fixed (K = 0.5),
  54.831 kN cantilever (K = 2), 447.601 kN fixed-pinned (K = 0.7).
- Same column with A = 1e-3 m^2: r = 0.03162 m, lambda = 94.868,
  buckling stress = 219.325 MPa = pi^2*E/lambda^2.
- Steel E = 200 GPa, sigma_y = 250 MPa: transition slenderness
  88.858, so lambda = 94.868 is in the slender Euler range.
- Circular column d = 0.1 m: r = 0.025 m, lambda = 120 (L = 3 m,
  K = 1), Pcr = 1.0766 MN, buckling stress = 137.078 MPa.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import buckling_analysis_logic as mod  # noqa: E402

E_STEEL = 200e9
I_ANCHOR = 1e-6
A_ANCHOR = 1e-3
L_ANCHOR = 3.0


class CriticalBucklingLoadTest(unittest.TestCase):
    def test_pinned_pinned_anchor(self):
        # Pcr = pi^2 * 200e9 * 1e-6 / 3^2 = 219.3 kN.
        pcr = mod.critical_buckling_load(E_STEEL, I_ANCHOR, L_ANCHOR, 1.0)
        self.assertAlmostEqual(pcr, 219324.54, delta=1.0)

    def test_fixed_fixed_anchor(self):
        # K = 0.5 -> Le = 1.5 m -> four times the pinned-pinned load.
        pcr = mod.critical_buckling_load(E_STEEL, I_ANCHOR, L_ANCHOR, 0.5)
        self.assertAlmostEqual(pcr, 877298.2, delta=1.0)
        self.assertAlmostEqual(
            pcr, 4.0 * mod.critical_buckling_load(E_STEEL, I_ANCHOR, L_ANCHOR, 1.0), delta=2.0
        )

    def test_cantilever_anchor(self):
        # K = 2 -> Le = 6 m -> one quarter of the pinned-pinned load.
        pcr = mod.critical_buckling_load(E_STEEL, I_ANCHOR, L_ANCHOR, 2.0)
        self.assertAlmostEqual(pcr, 54831.1, delta=1.0)
        self.assertAlmostEqual(
            pcr, 0.25 * mod.critical_buckling_load(E_STEEL, I_ANCHOR, L_ANCHOR, 1.0), delta=1.0
        )

    def test_fixed_pinned_anchor(self):
        pcr = mod.critical_buckling_load(E_STEEL, I_ANCHOR, L_ANCHOR, 0.7)
        self.assertAlmostEqual(pcr, 447601.1, delta=1.0)

    def test_longer_column_drops_critical_load(self):
        # Pcr ~ 1/L^2: doubling the length quarters the load.
        p2 = mod.critical_buckling_load(E_STEEL, I_ANCHOR, 2.0, 1.0)
        p3 = mod.critical_buckling_load(E_STEEL, I_ANCHOR, 3.0, 1.0)
        p4 = mod.critical_buckling_load(E_STEEL, I_ANCHOR, 4.0, 1.0)
        self.assertGreater(p2, p3)
        self.assertGreater(p3, p4)
        self.assertAlmostEqual(p4, 0.25 * p2, delta=1.0)

    def test_stiffer_and_heavier_sections_raise_load(self):
        base = mod.critical_buckling_load(E_STEEL, I_ANCHOR, L_ANCHOR, 1.0)
        self.assertGreater(
            mod.critical_buckling_load(2 * E_STEEL, I_ANCHOR, L_ANCHOR, 1.0), base
        )
        self.assertGreater(
            mod.critical_buckling_load(E_STEEL, 2 * I_ANCHOR, L_ANCHOR, 1.0), base
        )

    def test_invalid_inputs_raise_valueerror(self):
        for kwargs in [
            dict(E=0.0, I=I_ANCHOR, L=L_ANCHOR),
            dict(E=-200e9, I=I_ANCHOR, L=L_ANCHOR),
            dict(E=E_STEEL, I=0.0, L=L_ANCHOR),
            dict(E=E_STEEL, I=-I_ANCHOR, L=L_ANCHOR),
            dict(E=E_STEEL, I=I_ANCHOR, L=0.0),
            dict(E=E_STEEL, I=I_ANCHOR, L=-L_ANCHOR),
            dict(E=E_STEEL, I=I_ANCHOR, L=L_ANCHOR, K=0.0),
            dict(E=E_STEEL, I=I_ANCHOR, L=L_ANCHOR, K=-1.0),
            dict(E=float("nan"), I=I_ANCHOR, L=L_ANCHOR),
            dict(E=E_STEEL, I=float("inf"), L=L_ANCHOR),
            dict(E="two hundred", I=I_ANCHOR, L=L_ANCHOR),
        ]:
            with self.assertRaises(ValueError):
                mod.critical_buckling_load(**kwargs)


class EffectiveLengthFactorTest(unittest.TestCase):
    def test_standard_k_table(self):
        self.assertEqual(mod.effective_length_factor("pinned-pinned"), 1.0)
        self.assertEqual(mod.effective_length_factor("fixed-fixed"), 0.5)
        self.assertEqual(mod.effective_length_factor("fixed-pinned"), 0.7)
        self.assertEqual(mod.effective_length_factor("fixed-free"), 2.0)

    def test_aliases_resolve(self):
        self.assertEqual(mod.effective_length_factor("pinned"), 1.0)
        self.assertEqual(mod.effective_length_factor("hinged"), 1.0)
        self.assertEqual(mod.effective_length_factor("fixed"), 0.5)
        self.assertEqual(mod.effective_length_factor("clamped"), 0.5)
        self.assertEqual(mod.effective_length_factor("cantilever"), 2.0)
        self.assertEqual(mod.effective_length_factor("  Pinned-Pinned  "), 1.0)

    def test_unknown_end_condition_raises(self):
        for bad in ["free-free", "roller", "", "both-ends-elastic"]:
            with self.assertRaises(ValueError):
                mod.effective_length_factor(bad)
        with self.assertRaises(ValueError):
            mod.effective_length_factor(3.0)

    def test_effective_length_scales_with_k(self):
        self.assertAlmostEqual(mod.effective_length(L_ANCHOR, 1.0), 3.0)
        self.assertAlmostEqual(mod.effective_length(L_ANCHOR, 2.0), 6.0)
        self.assertAlmostEqual(mod.effective_length(L_ANCHOR, 0.5), 1.5)
        with self.assertRaises(ValueError):
            mod.effective_length(0.0, 1.0)


class SlendernessTest(unittest.TestCase):
    def test_radius_of_gyration_anchor(self):
        # I = 1e-6 m^4, A = 1e-3 m^2 -> r = sqrt(1e-3) = 0.03162 m.
        self.assertAlmostEqual(mod.radius_of_gyration(I_ANCHOR, A_ANCHOR), 0.0316228, delta=1e-6)

    def test_circular_column_radius_of_gyration(self):
        # Solid circular section d = 0.1 m: r = d/4 = 0.025 m.
        d = 0.1
        i = math.pi * d ** 4 / 64.0
        a = math.pi * d ** 2 / 4.0
        self.assertAlmostEqual(mod.radius_of_gyration(i, a), 0.025, delta=1e-9)

    def test_slenderness_ratio_anchor(self):
        # r = 0.03162 m, K = 1, L = 3 m -> lambda = 94.868.
        r = mod.radius_of_gyration(I_ANCHOR, A_ANCHOR)
        self.assertAlmostEqual(mod.slenderness_ratio(L_ANCHOR, 1.0, r), 94.868, delta=1e-2)
        # Cantilever: lambda doubles with K.
        self.assertAlmostEqual(
            mod.slenderness_ratio(L_ANCHOR, 2.0, r), 2.0 * mod.slenderness_ratio(L_ANCHOR, 1.0, r), delta=1e-9
        )

    def test_slenderness_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mod.slenderness_ratio(L_ANCHOR, 1.0, 0.0)
        with self.assertRaises(ValueError):
            mod.radius_of_gyration(0.0, A_ANCHOR)
        with self.assertRaises(ValueError):
            mod.radius_of_gyration(I_ANCHOR, -A_ANCHOR)


class BucklingStressTest(unittest.TestCase):
    def test_buckling_stress_equals_pcr_over_area(self):
        pcr = mod.critical_buckling_load(E_STEEL, I_ANCHOR, L_ANCHOR, 1.0)
        sig = mod.buckling_stress(E_STEEL, I_ANCHOR, A_ANCHOR, L_ANCHOR, 1.0)
        self.assertAlmostEqual(sig, pcr / A_ANCHOR, delta=1.0)
        self.assertAlmostEqual(sig / 1e6, 219.325, delta=0.01)

    def test_euler_stress_matches_sigma_cr(self):
        r = mod.radius_of_gyration(I_ANCHOR, A_ANCHOR)
        lam = mod.slenderness_ratio(L_ANCHOR, 1.0, r)
        self.assertAlmostEqual(
            mod.euler_stress(E_STEEL, lam),
            mod.buckling_stress(E_STEEL, I_ANCHOR, A_ANCHOR, L_ANCHOR, 1.0),
            delta=1.0,
        )

    def test_euler_stress_drops_with_slenderness(self):
        self.assertGreater(mod.euler_stress(E_STEEL, 50.0), mod.euler_stress(E_STEEL, 100.0))
        self.assertAlmostEqual(
            mod.euler_stress(E_STEEL, 2 * 100.0), 0.25 * mod.euler_stress(E_STEEL, 100.0), delta=1.0
        )

    def test_transition_slenderness_anchor(self):
        # Steel E = 200 GPa, sigma_y = 250 MPa -> lambda_1 = 88.858.
        lam1 = mod.transition_slenderness(E_STEEL, 250e6)
        self.assertAlmostEqual(lam1, 88.858, delta=0.01)
        # Higher yield strength moves the transition down.
        self.assertGreater(
            mod.transition_slenderness(E_STEEL, 250e6),
            mod.transition_slenderness(E_STEEL, 500e6),
        )

    def test_transition_slenderness_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mod.transition_slenderness(0.0, 250e6)
        with self.assertRaises(ValueError):
            mod.transition_slenderness(E_STEEL, -250e6)
        with self.assertRaises(ValueError):
            mod.euler_stress(E_STEEL, 0.0)


class ColumnCheckTest(unittest.TestCase):
    def test_full_check_anchor(self):
        ck = mod.column_check(E_STEEL, I_ANCHOR, A_ANCHOR, L_ANCHOR, "pinned-pinned", 100e3, 250e6)
        self.assertEqual(ck["end_condition"], "pinned-pinned")
        self.assertAlmostEqual(ck["effective_length_factor"], 1.0)
        self.assertAlmostEqual(ck["effective_length"], 3.0)
        self.assertAlmostEqual(ck["radius_of_gyration"], 0.0316228, delta=1e-6)
        self.assertAlmostEqual(ck["slenderness_ratio"], 94.868, delta=1e-2)
        self.assertAlmostEqual(ck["critical_buckling_load"], 219324.5, delta=1.0)
        self.assertAlmostEqual(ck["buckling_stress"] / 1e6, 219.325, delta=0.01)
        self.assertAlmostEqual(ck["transition_slenderness"], 88.858, delta=0.01)
        self.assertTrue(ck["euler_governs"])
        self.assertAlmostEqual(ck["margin_of_safety"], 1.1932, delta=1e-3)

    def test_check_accepts_numeric_k(self):
        ck = mod.column_check(E_STEEL, I_ANCHOR, A_ANCHOR, L_ANCHOR, 0.7, 100e3, 250e6)
        self.assertIsNone(ck["end_condition"])
        self.assertAlmostEqual(ck["critical_buckling_load"], 447601.1, delta=1.0)
        self.assertAlmostEqual(ck["margin_of_safety"], 3.4760, delta=1e-3)

    def test_stubby_column_euler_does_not_govern(self):
        # Very low slenderness: lambda < lambda_1 -> euler_governs False.
        ck = mod.column_check(E_STEEL, 1e-3, 1e-2, 0.3, "fixed-fixed", 1e6, 250e6)
        self.assertFalse(ck["euler_governs"])
        self.assertLess(ck["slenderness_ratio"], ck["transition_slenderness"])

    def test_cantilever_check_weakest(self):
        pinned = mod.column_check(E_STEEL, I_ANCHOR, A_ANCHOR, L_ANCHOR, "pinned-pinned", 100e3, 250e6)
        cant = mod.column_check(E_STEEL, I_ANCHOR, A_ANCHOR, L_ANCHOR, "cantilever", 100e3, 250e6)
        fixed = mod.column_check(E_STEEL, I_ANCHOR, A_ANCHOR, L_ANCHOR, "fixed-fixed", 100e3, 250e6)
        self.assertLess(cant["critical_buckling_load"], pinned["critical_buckling_load"])
        self.assertLess(pinned["critical_buckling_load"], fixed["critical_buckling_load"])
        self.assertLess(cant["margin_of_safety"], pinned["margin_of_safety"])
        self.assertLess(pinned["margin_of_safety"], fixed["margin_of_safety"])

    def test_check_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mod.column_check(E_STEEL, I_ANCHOR, A_ANCHOR, L_ANCHOR, "free-free", 100e3, 250e6)
        with self.assertRaises(ValueError):
            mod.column_check(E_STEEL, I_ANCHOR, A_ANCHOR, L_ANCHOR, "pinned-pinned", 0.0, 250e6)
        with self.assertRaises(ValueError):
            mod.column_check(E_STEEL, I_ANCHOR, A_ANCHOR, L_ANCHOR, "pinned-pinned", -50e3, 250e6)
        with self.assertRaises(ValueError):
            mod.column_check(E_STEEL, I_ANCHOR, A_ANCHOR, L_ANCHOR, "pinned-pinned", 100e3, -250e6)
        with self.assertRaises(ValueError):
            mod.column_check(E_STEEL, I_ANCHOR, A_ANCHOR, L_ANCHOR, [1.0], 100e3, 250e6)
        with self.assertRaises(ValueError):
            mod.column_check(E_STEEL, I_ANCHOR, 0.0, L_ANCHOR, "pinned-pinned", 100e3, 250e6)


if __name__ == "__main__":
    unittest.main()
