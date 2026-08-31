#!/usr/bin/env python3
"""Gate 3 contract test: XFOIL airfoil polar analysis.

Exercises scripts/xfoil_analysis_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - angle-of-attack plausibility
band; structural polar-point validation with ValueError on nonsense
inputs; NACA 0012 (Re = 6e6) anchor bands for cl at 10 deg (0.77-0.87)
and cd0 (0.0069-0.0089) with pass/fail at the boundaries; inviscid-run
and high-drag hints.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import xfoil_analysis_logic as xf  # noqa: E402


class AlphaPlausibilityTest(unittest.TestCase):
    def test_band_edges_are_plausible(self):
        self.assertTrue(xf.plausible_alpha(-25.0))
        self.assertTrue(xf.plausible_alpha(30.0))
        self.assertTrue(xf.plausible_alpha(0.0))

    def test_outside_band_is_implausible(self):
        self.assertFalse(xf.plausible_alpha(-25.1))
        self.assertFalse(xf.plausible_alpha(30.1))


class PolarPointValidationTest(unittest.TestCase):
    def test_structurally_valid_point_passes(self):
        self.assertTrue(xf.validate_polar_point(5.0, 0.6, 0.007, 6e6))

    def test_out_of_range_cl_raises(self):
        with self.assertRaises(ValueError):
            xf.validate_polar_point(5.0, 2.6, 0.007, 6e6)
        with self.assertRaises(ValueError):
            xf.validate_polar_point(5.0, -2.6, 0.007, 6e6)

    def test_out_of_range_cd_raises(self):
        with self.assertRaises(ValueError):
            xf.validate_polar_point(5.0, 0.6, -0.001, 6e6)
        with self.assertRaises(ValueError):
            xf.validate_polar_point(5.0, 0.6, 0.21, 6e6)

    def test_nonpositive_reynolds_raises(self):
        with self.assertRaises(ValueError):
            xf.validate_polar_point(5.0, 0.6, 0.007, 0)
        with self.assertRaises(ValueError):
            xf.validate_polar_point(5.0, 0.6, 0.007, -1e6)

    def test_implausible_alpha_raises(self):
        with self.assertRaises(ValueError):
            xf.validate_polar_point(35.0, 0.6, 0.007, 6e6)


class Naca0012SanityTest(unittest.TestCase):
    def test_anchor_center_passes(self):
        res = xf.naca0012_sanity(0.82, 0.0079)
        self.assertTrue(res["cl_ok"])
        self.assertTrue(res["cd0_ok"])
        self.assertTrue(res["is_sane"])
        self.assertTrue(res["note"])

    def test_upper_boundaries_pass(self):
        res = xf.naca0012_sanity(0.87, 0.0089)
        self.assertTrue(res["is_sane"])

    def test_lower_boundaries_pass(self):
        res = xf.naca0012_sanity(0.77, 0.0069)
        self.assertTrue(res["is_sane"])

    def test_just_outside_fails(self):
        res = xf.naca0012_sanity(0.76, 0.0079)
        self.assertFalse(res["cl_ok"])
        self.assertFalse(res["is_sane"])
        self.assertFalse(xf.naca0012_sanity(0.88, 0.0079)["cl_ok"])
        self.assertFalse(xf.naca0012_sanity(0.82, 0.00891)["cd0_ok"])
        self.assertFalse(xf.naca0012_sanity(0.82, 0.00689)["cd0_ok"])


class Cd0HintTest(unittest.TestCase):
    def test_inviscid_hint(self):
        self.assertEqual(
            xf.cd0_hint(0.001),
            "likely inviscid run: XFOIL inviscid drag is meaningless; rerun viscous",
        )

    def test_high_drag_hint(self):
        self.assertEqual(xf.cd0_hint(0.025), "high drag: check transition and mesh density")

    def test_typical_cd0_no_hint(self):
        self.assertIsNone(xf.cd0_hint(0.0079))
        self.assertIsNone(xf.cd0_hint(0.005))
        self.assertIsNone(xf.cd0_hint(0.02))


if __name__ == "__main__":
    unittest.main(verbosity=2)
