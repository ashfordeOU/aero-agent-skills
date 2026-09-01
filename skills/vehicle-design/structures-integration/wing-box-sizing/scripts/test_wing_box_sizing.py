#!/usr/bin/env python3
"""Gate 3 contract test: wing box structural sizing.

Exercises scripts/wing_box_sizing_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 (root bending moment from
the elliptical and uniform lift distributions, root shear, ultimate
moment from the 1.5 factor of safety, spar cap area, web shear flow,
web thickness, sizing verdict; invalid inputs raise ValueError.

Anchors (design case n = 2.5, W = 600000 N, b = 30 m):
- wing_root_bending_moment(2.5, 600000, 30, "elliptical") =
  (2/(3*pi)) * 2.5 * 600000 * 30 = 9549296.5855 N m
- wing_root_bending_moment(2.5, 600000, 30, "uniform") =
  2.5 * 600000 * 30 / 4 = 11250000 N m
- ultimate_moment(9549296.5855, 1.5) = 14323944.8783 N m
- wing_root_shear(2.5, 600000) = 750000 N
- spar_cap_area(14323944.8783, 400e6, 0.6) = 0.0596831 m^2
- web_shear_flow(750000, 0.6, 2) = 625000 N/m
- web_thickness(625000, 240e6) = 0.00260417 m
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wing_box_sizing_logic as wbs  # noqa: E402


class RootBendingMomentTest(unittest.TestCase):
    def test_anchor_elliptical(self):
        m = wbs.wing_root_bending_moment(2.5, 600000.0, 30.0, "elliptical")
        self.assertAlmostEqual(m, 9549296.5855, places=3)

    def test_anchor_uniform(self):
        m = wbs.wing_root_bending_moment(2.5, 600000.0, 30.0, "uniform")
        self.assertAlmostEqual(m, 11250000.0, places=3)

    def test_elliptical_below_uniform(self):
        m_ell = wbs.wing_root_bending_moment(2.5, 600000.0, 30.0, "elliptical")
        m_uni = wbs.wing_root_bending_moment(2.5, 600000.0, 30.0, "uniform")
        self.assertLess(m_ell, m_uni)

    def test_linear_in_load_factor(self):
        m1 = wbs.wing_root_bending_moment(2.5, 600000.0, 30.0, "elliptical")
        m2 = wbs.wing_root_bending_moment(5.0, 600000.0, 30.0, "elliptical")
        self.assertAlmostEqual(m2, 2 * m1)

    def test_default_distribution_is_elliptical(self):
        m_default = wbs.wing_root_bending_moment(2.5, 600000.0, 30.0)
        m_ell = wbs.wing_root_bending_moment(2.5, 600000.0, 30.0, "elliptical")
        self.assertAlmostEqual(m_default, m_ell)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wbs.wing_root_bending_moment(0, 600000.0, 30.0)
        with self.assertRaises(ValueError):
            wbs.wing_root_bending_moment(2.5, 0, 30.0)
        with self.assertRaises(ValueError):
            wbs.wing_root_bending_moment(2.5, 600000.0, 0)
        with self.assertRaises(ValueError):
            wbs.wing_root_bending_moment(2.5, 600000.0, 30.0, "triangular")


class RootShearTest(unittest.TestCase):
    def test_anchor_shear(self):
        self.assertAlmostEqual(wbs.wing_root_shear(2.5, 600000.0), 750000.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wbs.wing_root_shear(0, 600000.0)
        with self.assertRaises(ValueError):
            wbs.wing_root_shear(2.5, 0)


class UltimateMomentTest(unittest.TestCase):
    def test_anchor_ultimate(self):
        self.assertAlmostEqual(
            wbs.ultimate_moment(9549296.5855, 1.5), 14323944.8783, places=3
        )

    def test_default_safety_factor(self):
        self.assertAlmostEqual(
            wbs.ultimate_moment(1000000.0), 1500000.0, places=3
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wbs.ultimate_moment(0, 1.5)
        with self.assertRaises(ValueError):
            wbs.ultimate_moment(1000000.0, 0)


class SparCapAreaTest(unittest.TestCase):
    def test_anchor_cap_area(self):
        a = wbs.spar_cap_area(14323944.8783, 400e6, 0.6)
        self.assertAlmostEqual(a, 0.0596831, places=6)

    def test_larger_box_depth_reduces_area(self):
        a_shallow = wbs.spar_cap_area(14323944.8783, 400e6, 0.6)
        a_deep = wbs.spar_cap_area(14323944.8783, 400e6, 1.2)
        self.assertAlmostEqual(a_deep, a_shallow / 2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wbs.spar_cap_area(0, 400e6, 0.6)
        with self.assertRaises(ValueError):
            wbs.spar_cap_area(14323944.8783, 0, 0.6)
        with self.assertRaises(ValueError):
            wbs.spar_cap_area(14323944.8783, 400e6, 0)


class WebSizingTest(unittest.TestCase):
    def test_anchor_shear_flow(self):
        self.assertAlmostEqual(wbs.web_shear_flow(750000.0, 0.6, 2), 625000.0)

    def test_anchor_web_thickness(self):
        t = wbs.web_thickness(625000.0, 240e6)
        self.assertAlmostEqual(t, 0.00260417, places=7)

    def test_web_count_splits_shear(self):
        q2 = wbs.web_shear_flow(750000.0, 0.6, 2)
        q4 = wbs.web_shear_flow(750000.0, 0.6, 4)
        self.assertAlmostEqual(q4, q2 / 2)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wbs.web_shear_flow(750000.0, 0.6, 0)
        with self.assertRaises(ValueError):
            wbs.web_shear_flow(750000.0, 0, 2)
        with self.assertRaises(ValueError):
            wbs.web_thickness(625000.0, 0)


class WingBoxVerdictTest(unittest.TestCase):
    def test_anchor_verdict_sized(self):
        v = wbs.wing_box_verdict(0.0596831, 0.07, 0.00260417, 0.004)
        self.assertEqual(v, "box sized")

    def test_anchor_verdict_undersized(self):
        v = wbs.wing_box_verdict(0.0596831, 0.05, 0.00260417, 0.004)
        self.assertEqual(v, "box undersized")

    def test_web_drives_undersized(self):
        v = wbs.wing_box_verdict(0.0596831, 0.07, 0.00260417, 0.002)
        self.assertEqual(v, "box undersized")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            wbs.wing_box_verdict(-0.01, 0.07, 0.0026, 0.004)
        with self.assertRaises(ValueError):
            wbs.wing_box_verdict(0.06, 0.07, -0.001, 0.004)


if __name__ == "__main__":
    unittest.main(verbosity=2)
