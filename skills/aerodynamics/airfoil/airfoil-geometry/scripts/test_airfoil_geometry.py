#!/usr/bin/env python3
"""Gate 3 contract test: NACA airfoil geometry.

Exercises scripts/airfoil_geometry_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - NACA 4-digit thickness and
mean-camber formulas (public domain, NACA Report 460 / TR-824) with max
half-thickness t / 2 at x = 0.3, camber-line slope zero at the camber
position, leading-edge radius 1.1019 * t^2, enclosed section area
0.68508 * t (chord^2 per unit span) cross-checked by numerical
integration, and 4-digit / 5-digit / 6-series designation decode with
ValueError on nonsense inputs.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import airfoil_geometry_logic as ag  # noqa: E402


class ThicknessDistributionTest(unittest.TestCase):
    def test_max_half_thickness_at_30_percent(self):
        # NACA 0012 (t = 0.12): y_t(0.3) == t / 2
        self.assertAlmostEqual(ag.thickness_ord(0.12, 0.3), 0.06, delta=1e-4)

    def test_leading_edge_and_known_station(self):
        self.assertAlmostEqual(ag.thickness_ord(0.12, 0.0), 0.0, delta=1e-12)
        # NACA 0012 half-thickness at x = 0.1: 0.04683
        self.assertAlmostEqual(ag.thickness_ord(0.12, 0.1), 0.04683, delta=1e-4)

    def test_thickness_peaks_at_30_percent(self):
        y30 = ag.thickness_ord(0.12, 0.3)
        self.assertLess(ag.thickness_ord(0.12, 0.2), y30)
        self.assertLess(ag.thickness_ord(0.12, 0.5), y30)
        self.assertLess(ag.thickness_ord(0.12, 0.9), y30)

    def test_trailing_edge_residual_is_small(self):
        # The polynomial leaves a small trailing-edge thickness,
        # 0.0105 * t; sections are faired to a sharp edge in practice.
        self.assertAlmostEqual(
            ag.thickness_ord(0.12, 1.0), 0.0105 * 0.12, delta=1e-6
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ag.thickness_ord(0.0, 0.3)
        with self.assertRaises(ValueError):
            ag.thickness_ord(1.2, 0.3)
        with self.assertRaises(ValueError):
            ag.thickness_ord(0.12, 1.1)
        with self.assertRaises(ValueError):
            ag.thickness_ord(0.12, -0.1)


class MeanCamberLineTest(unittest.TestCase):
    def test_max_camber_at_position(self):
        # NACA 2412: m = 0.02, p = 0.4; both branches give y_c = m at x = p
        self.assertAlmostEqual(ag.camber_ord(0.02, 0.4, 0.4), 0.02, delta=1e-9)
        self.assertAlmostEqual(
            ag.camber_ord(0.02, 0.4, 0.4 + 1e-9), 0.02, delta=1e-6
        )

    def test_known_station_ordinates(self):
        # y_c(0.1) = (m / p^2)(2 p x - x^2) = 0.00875
        self.assertAlmostEqual(ag.camber_ord(0.02, 0.4, 0.1), 0.00875, delta=1e-9)
        # y_c(0.9) = (m / (1 - p)^2)(1 - 2 p + 2 p x - x^2) = 0.006111
        self.assertAlmostEqual(
            ag.camber_ord(0.02, 0.4, 0.9), 0.0061111, delta=1e-6
        )

    def test_slope_zero_at_camber_position(self):
        self.assertAlmostEqual(ag.camber_slope(0.02, 0.4, 0.4), 0.0, delta=1e-12)
        self.assertAlmostEqual(
            ag.camber_slope(0.02, 0.4, 0.4 - 1e-9), 0.0, delta=1e-6
        )
        self.assertAlmostEqual(
            ag.camber_slope(0.02, 0.4, 0.4 + 1e-9), 0.0, delta=1e-6
        )

    def test_known_station_slopes(self):
        # dy_c/dx at x = 0.1: (2 m / p^2)(p - x) = 0.075
        self.assertAlmostEqual(ag.camber_slope(0.02, 0.4, 0.1), 0.075, delta=1e-9)
        # at x = 0.9: (2 m / (1 - p)^2)(p - x) = -0.05556
        self.assertAlmostEqual(
            ag.camber_slope(0.02, 0.4, 0.9), -0.0555556, delta=1e-6
        )

    def test_surface_ordinates(self):
        # NACA 2412 at x = 0.4: y_c = 0.02, y_t = 0.05803
        up, lo = ag.surface_ords(0.02, 0.4, 0.12, 0.4)
        self.assertAlmostEqual(up, 0.07803, delta=1e-4)
        self.assertAlmostEqual(lo, -0.03803, delta=1e-4)
        # camber cancels: (up - lo) / 2 = y_t, (up + lo) / 2 = y_c
        self.assertAlmostEqual(
            (up - lo) / 2.0, ag.thickness_ord(0.12, 0.4), delta=1e-9
        )
        self.assertAlmostEqual((up + lo) / 2.0, 0.02, delta=1e-9)

    def test_symmetric_airfoil_camber_zero(self):
        self.assertAlmostEqual(ag.camber_ord(0.0, 0.4, 0.3), 0.0, delta=1e-12)
        self.assertAlmostEqual(ag.camber_slope(0.0, 0.4, 0.3), 0.0, delta=1e-12)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            ag.camber_ord(0.02, 0.0, 0.3)
        with self.assertRaises(ValueError):
            ag.camber_ord(0.02, 1.0, 0.3)
        with self.assertRaises(ValueError):
            ag.camber_slope(-0.02, 0.4, 0.3)


class LeadingEdgeRadiusTest(unittest.TestCase):
    def test_naca_0012_radius(self):
        # r_le = 1.1019 * t^2 = 0.015867 for t = 0.12
        self.assertAlmostEqual(ag.leading_edge_radius(0.12), 0.015867, delta=1e-5)
        self.assertAlmostEqual(
            ag.leading_edge_radius(0.12), 1.1019 * 0.0144, delta=1e-9
        )

    def test_bad_input_raises(self):
        with self.assertRaises(ValueError):
            ag.leading_edge_radius(0.0)
        with self.assertRaises(ValueError):
            ag.leading_edge_radius(1.5)


class SectionAreaTest(unittest.TestCase):
    def test_naca_0012_area(self):
        # A = 0.68508 * t = 0.08221 chord^2 per unit span
        self.assertAlmostEqual(ag.section_area(0.12), 0.08221, delta=1e-4)

    def test_area_independent_of_camber(self):
        # upper minus lower = 2 * y_t, so camber does not enter the area
        self.assertAlmostEqual(ag.section_area(0.18), 0.68508 * 0.18, delta=1e-5)

    def test_area_matches_numerical_integration(self):
        # Trapezoidal integral of 2 * y_t over [0, 1], fine mesh
        n = 20000
        h = 1.0 / n
        s = 0.5 * (
            2.0 * ag.thickness_ord(0.12, 0.0) + 2.0 * ag.thickness_ord(0.12, 1.0)
        )
        for i in range(1, n):
            s += 2.0 * ag.thickness_ord(0.12, i * h)
        area = s * h
        self.assertAlmostEqual(area, ag.section_area(0.12), delta=2e-4)

    def test_bad_input_raises(self):
        with self.assertRaises(ValueError):
            ag.section_area(0.0)


class DesignationDecodeTest(unittest.TestCase):
    def test_4digit(self):
        d = ag.decode_4digit("2412")
        self.assertEqual(
            (d["camber"], d["camber_pos"], d["thickness"]), (0.02, 0.4, 0.12)
        )
        d = ag.decode_4digit("naca 0012")
        self.assertEqual(
            (d["camber"], d["camber_pos"], d["thickness"]), (0.0, 0.0, 0.12)
        )

    def test_5digit(self):
        d = ag.decode_5digit("23012")
        self.assertAlmostEqual(d["design_cl"], 0.3, delta=1e-9)
        self.assertAlmostEqual(d["camber_pos"], 0.15, delta=1e-9)
        self.assertEqual(d["thickness"], 0.12)
        self.assertAlmostEqual(d["m"], 0.15, delta=1e-9)
        self.assertAlmostEqual(d["k1"], 15.957, delta=1e-3)
        self.assertFalse(d["reflexed"])

    def test_6series(self):
        d = ag.decode_6series("65-218")
        self.assertEqual(
            (d["series"], d["min_pressure_pos"], d["design_cl"], d["thickness"]),
            (6, 0.5, 0.2, 0.18),
        )
        d = ag.decode_6series("63-412")
        self.assertEqual(
            (d["min_pressure_pos"], d["design_cl"], d["thickness"]),
            (0.3, 0.4, 0.12),
        )

    def test_bad_names_raise(self):
        with self.assertRaises(ValueError):
            ag.decode_4digit("241")
        with self.assertRaises(ValueError):
            ag.decode_4digit("2400")
        with self.assertRaises(ValueError):
            ag.decode_5digit("2412")
        with self.assertRaises(ValueError):
            ag.decode_5digit("2301X")
        with self.assertRaises(ValueError):
            ag.decode_6series("65-21")
        with self.assertRaises(ValueError):
            ag.decode_6series("23012")
        with self.assertRaises(ValueError):
            ag.decode_6series("65(3)-218")
        with self.assertRaises(ValueError):
            ag.decode_6series("64A-212")


if __name__ == "__main__":
    unittest.main(verbosity=2)
