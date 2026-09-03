"""Offline contract test for winglet_design_logic (stdlib unittest).

Run:  python3 scripts/test_winglet_design.py
Covers the wave-27 worked example (span 30 m, area 100 m2, e_base 0.8,
cl_ref 0.5, height_frac 0.12, cant 0 deg), boundary behavior, sizing
bisection contract, and ValueError rejection of non-physical inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import winglet_design_logic as w


class EffectiveSpanExtensionTest(unittest.TestCase):
    """K_HEIGHT scaling of the winglet height fraction."""

    def test_effective_span_extension_worked_example(self):
        self.assertAlmostEqual(w.effective_span_extension(0.12), 0.096, places=12)

    def test_effective_span_extension_zero(self):
        self.assertEqual(w.effective_span_extension(0.0), 0.0)


class CantFactorTest(unittest.TestCase):
    """Cosine cant weighting: vertical keeps full effect, flat loses it."""

    def test_cant_factor_vertical_one(self):
        self.assertAlmostEqual(w.cant_factor(0.0), 1.0, places=12)

    def test_cant_factor_flat_zero(self):
        self.assertAlmostEqual(w.cant_factor(90.0), 0.0, places=12)

    def test_cant_factor_45deg(self):
        self.assertAlmostEqual(w.cant_factor(45.0), math.cos(math.pi / 4.0), places=12)

    def test_cant_factor_symmetric_negative(self):
        self.assertAlmostEqual(w.cant_factor(-30.0), w.cant_factor(30.0), places=12)


class AspectRatioTest(unittest.TestCase):
    """Effective aspect ratio from the extended span."""

    def test_ar_eff_worked_example(self):
        # 35.76^2/100 = 12.788 within 0.01
        self.assertAlmostEqual(w.ar_eff(30.0, 100.0, 0.12, 0.0), 12.788, delta=0.01)

    def test_ar_eff_ratio_form_identity(self):
        # AR_eff/AR == (1 + 2*cant_factor*K_HEIGHT*height_frac)^2
        ar_wl = w.ar_eff(30.0, 100.0, 0.12, 0.0)
        ratio = 1.0 + 2.0 * w.cant_factor(0.0) * w.K_HEIGHT * 0.12
        self.assertAlmostEqual(ar_wl / 9.0, ratio * ratio, places=12)

    def test_ar_eff_no_winglet_base_aspect(self):
        self.assertAlmostEqual(w.ar_eff(30.0, 100.0, 0.0, 0.0), 9.0, places=12)


class SpanEfficiencyTest(unittest.TestCase):
    """Improved span efficiency e_eff from the effective-AR gain."""

    def test_e_winglet_worked_example(self):
        # 1 - 0.2/(AR_eff/9) = 0.85925 within 1e-4
        self.assertAlmostEqual(w.e_winglet(0.8, 0.12, 0.0), 0.85925, delta=1e-4)

    def test_e_winglet_no_winglet_returns_base(self):
        self.assertAlmostEqual(w.e_winglet(0.8, 0.0, 0.0), 0.8, places=12)

    def test_e_winglet_ar_ratio_equivalent_form(self):
        # e_eff = 1 - (1 - e_base)/(AR_eff/AR) with the module's own ar_eff
        ar_wl = w.ar_eff(30.0, 100.0, 0.12, 0.0)
        expected = 1.0 - (1.0 - 0.8) / (ar_wl / 9.0)
        self.assertAlmostEqual(w.e_winglet(0.8, 0.12, 0.0), expected, places=12)


class DragFactorTest(unittest.TestCase):
    """Induced-drag factor k = 1/(pi*e*ar)."""

    def test_induced_drag_factor_base(self):
        # 1/(pi*0.8*9) = 0.0442097 within 1e-6
        self.assertAlmostEqual(w.induced_drag_factor(0.8, 9.0), 0.0442097, delta=1e-6)

    def test_induced_drag_factor_winglet(self):
        # Exact analytic identity against the module's own e_eff and ar_eff.
        e_wl = w.e_winglet(0.8, 0.12, 0.0)
        ar_wl = w.ar_eff(30.0, 100.0, 0.12, 0.0)
        k_wl = w.induced_drag_factor(e_wl, ar_wl)
        self.assertAlmostEqual(k_wl, 1.0 / (math.pi * e_wl * ar_wl), places=12)
        # Spec hand value 0.028987 carries about 2e-5 rounding slack (the
        # exact chain gives 0.02896946); assert within a 2e-5 band.
        self.assertAlmostEqual(k_wl, 0.028987, delta=2e-5)


class InducedDragCoefficientTest(unittest.TestCase):
    """cd_i = cl^2 * k."""

    def test_cd_i_base_worked_example(self):
        # 0.25*0.0442097 = 0.0110524 within 1e-5
        self.assertAlmostEqual(w.cd_i(0.5, 0.8, 9.0), 0.0110524, delta=1e-5)

    def test_cd_i_winglet_worked_example(self):
        e_wl = w.e_winglet(0.8, 0.12, 0.0)
        ar_wl = w.ar_eff(30.0, 100.0, 0.12, 0.0)
        cdi = w.cd_i(0.5, e_wl, ar_wl)
        # spec hand value 0.0072468 within 1e-5 (exact chain 0.00724236)
        self.assertAlmostEqual(cdi, 0.0072468, delta=1e-5)
        # and exactly cl^2 * k
        self.assertAlmostEqual(cdi, 0.25 * w.induced_drag_factor(e_wl, ar_wl),
                               places=12)


class DragReductionTest(unittest.TestCase):
    """Percent induced-drag reduction of the winglet case."""

    def test_drag_reduction_worked_example(self):
        e_wl = w.e_winglet(0.8, 0.12, 0.0)
        ar_wl = w.ar_eff(30.0, 100.0, 0.12, 0.0)
        k_base = w.induced_drag_factor(0.8, 9.0)
        k_wl = w.induced_drag_factor(e_wl, ar_wl)
        # 34.43 pct within 0.05 (exact chain gives 34.473)
        self.assertAlmostEqual(w.drag_reduction_pct(0.5, k_base, k_wl), 34.43,
                               delta=0.05)

    def test_drag_reduction_identical_factors_zero(self):
        self.assertAlmostEqual(w.drag_reduction_pct(0.5, 0.0442097, 0.0442097),
                               0.0, places=12)

    def test_drag_reduction_grows_as_factor_shrinks(self):
        base = 0.0442097
        small = 0.02
        large = 0.03
        self.assertGreater(w.drag_reduction_pct(0.5, base, small),
                           w.drag_reduction_pct(0.5, base, large))


class BendingPenaltyTest(unittest.TestCase):
    """Approximate root bending moment penalty scaling."""

    def test_root_bending_penalty_worked_example(self):
        # 1.0*0.8*0.12*100*(1+0.06) = 10.18 pct within 0.05
        self.assertAlmostEqual(w.root_bending_penalty_pct(0.12, 0.0), 10.18,
                               delta=0.05)

    def test_root_bending_penalty_flat_tip_zero(self):
        self.assertAlmostEqual(w.root_bending_penalty_pct(0.12, 90.0), 0.0,
                               places=12)

    def test_root_bending_penalty_cant_reduces_moment(self):
        self.assertGreater(w.root_bending_penalty_pct(0.12, 0.0),
                           w.root_bending_penalty_pct(0.12, 45.0))


class SizeWingletTest(unittest.TestCase):
    """Bisection sizing of the winglet height fraction."""

    def test_size_winglet_25pct_contract(self):
        s = w.size_winglet(30.0, 100.0, 0.8, 25.0, 0.5)
        self.assertEqual(set(s.keys()),
                         {"height_frac", "height_m", "ar_eff", "e_eff", "cd_i",
                          "reduction_pct", "bending_penalty_pct"})
        # height_frac in [0.05, 0.12], reduction within 0.1 of 25
        self.assertGreaterEqual(s["height_frac"], 0.05)
        self.assertLessEqual(s["height_frac"], 0.12)
        self.assertAlmostEqual(s["reduction_pct"], 25.0, delta=0.1)
        # physical height uses the semi-span local reference
        self.assertAlmostEqual(s["height_m"], s["height_frac"] * 15.0, places=12)
        # gains and penalties all present and positive
        self.assertGreater(s["ar_eff"], 9.0)
        self.assertGreater(s["e_eff"], 0.8)
        self.assertGreater(s["cd_i"], 0.0)
        self.assertGreater(s["bending_penalty_pct"], 0.0)

    def test_size_winglet_monotonic_target(self):
        hf15 = w.size_winglet(30.0, 100.0, 0.8, 15.0, 0.5)["height_frac"]
        hf25 = w.size_winglet(30.0, 100.0, 0.8, 25.0, 0.5)["height_frac"]
        hf40 = w.size_winglet(30.0, 100.0, 0.8, 40.0, 0.5)["height_frac"]
        self.assertLess(hf15, hf25)
        self.assertLess(hf25, hf40)

    def test_size_winglet_cant_needs_more_height(self):
        hf0 = w.size_winglet(30.0, 100.0, 0.8, 25.0, 0.5, cant_deg=0.0)["height_frac"]
        hf45 = w.size_winglet(30.0, 100.0, 0.8, 25.0, 0.5, cant_deg=45.0)["height_frac"]
        self.assertGreater(hf45, hf0)

    def test_size_winglet_impossible_target_raises(self):
        with self.assertRaises(ValueError):
            w.size_winglet(30.0, 100.0, 0.8, 90.0, 0.5)


class ValueErrorRejectionTest(unittest.TestCase):
    """Non-physical inputs must raise ValueError."""

    def test_valueerror_span_area(self):
        for bad in (0.0, -5.0):
            with self.assertRaises(ValueError):
                w.ar_eff(bad, 100.0, 0.12, 0.0)
            with self.assertRaises(ValueError):
                w.size_winglet(bad, 100.0, 0.8, 25.0, 0.5)
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                w.ar_eff(30.0, bad, 0.12, 0.0)

    def test_valueerror_e_base_cl(self):
        for bad in (0.0, 1.2):
            with self.assertRaises(ValueError):
                w.e_winglet(bad, 0.12, 0.0)
        for bad in (0.0, -0.5):
            with self.assertRaises(ValueError):
                w.cd_i(bad, 0.8, 9.0)
            with self.assertRaises(ValueError):
                w.drag_reduction_pct(bad, 0.04, 0.03)

    def test_valueerror_height_frac_cant(self):
        for bad in (-0.1, 0.8):
            with self.assertRaises(ValueError):
                w.effective_span_extension(bad)
            with self.assertRaises(ValueError):
                w.ar_eff(30.0, 100.0, bad, 0.0)
            with self.assertRaises(ValueError):
                w.root_bending_penalty_pct(bad, 0.0)
        for bad in (120.0, -95.0):
            with self.assertRaises(ValueError):
                w.cant_factor(bad)
            with self.assertRaises(ValueError):
                w.ar_eff(30.0, 100.0, 0.12, bad)

    def test_valueerror_taper_target(self):
        for bad in (0.0, 1.5):
            with self.assertRaises(ValueError):
                w.validate_inputs(30.0, 100.0, 0.8, 0.5, 0.12, 0.0, taper_frac=bad)
        for bad in (0.0, 100.0, -5.0, 120.0):
            with self.assertRaises(ValueError):
                w.size_winglet(30.0, 100.0, 0.8, bad, 0.5)

    def test_valueerror_factor_function_inputs(self):
        for bad in (0.0, 1.2):
            with self.assertRaises(ValueError):
                w.induced_drag_factor(bad, 9.0)
        for bad in (0.0, -3.0):
            with self.assertRaises(ValueError):
                w.induced_drag_factor(0.8, bad)
        with self.assertRaises(ValueError):
            w.validate_inputs(30.0, 100.0, 1.2, 0.5, 0.12, 0.0)
        with self.assertRaises(ValueError):
            w.validate_inputs(30.0, 100.0, 0.8, 0.5, 0.12, 95.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
