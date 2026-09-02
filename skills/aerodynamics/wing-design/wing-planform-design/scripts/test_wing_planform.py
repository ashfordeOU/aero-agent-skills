#!/usr/bin/env python3
"""Gate 3 contract test: wing planform design.

Exercises scripts/wing_planform_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3. Hand-computed analytic
anchors, all for the worked example b = 35 m, S = 125 m^2, lambda = 0.3:
- AR = 35^2/125 = 9.8.
- cr = 2*125/(35*1.3) = 5.4945055, ct = 0.3*cr = 1.6483516,
  cbar = 125/35 = 3.5714286.
- MAC = (2/3)*5.4945055*(1.39/1.3) = 3.916596.
- y_MAC = (35/6)*(1.6/1.3) = 7.179487.
- Sweep conversion from LE = 30 deg:
  tan(c/4) = tan(30) - 0.7/(9.8*1.3) -> 27.582801 deg,
  tan(c/2) = tan(30) - 2*0.7/12.74 -> 25.054216 deg,
  tan(TE) = tan(30) - 4*0.7/12.74 -> 19.675529 deg.
- Schrenk at CL = 0.5: root cl = 0.456901, cl(0.25) = 0.492826,
  cl(0.5) = 0.525664, tip cl = 0.25; loading integrates to CL*S = 62.5.
- Rectangular wing b = 10, S = 20 (c = 2): MAC = 2, y_MAC = 2.5,
  Schrenk root cl = 0.568310, tip cl = 0.25.
- Washout: (1.15 - 1.0)/5.0265482 rad = 1.709795 deg.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import wing_planform_logic as wp  # noqa: E402

B = 35.0
S = 125.0
LAM = 0.3


class AspectRatioTest(unittest.TestCase):
    def test_analytic_worked_example(self):
        # 35^2 / 125 = 9.8.
        self.assertAlmostEqual(wp.aspect_ratio(B, S), 9.8, places=6)

    def test_rectangle(self):
        self.assertAlmostEqual(wp.aspect_ratio(10.0, 20.0), 5.0, places=6)

    def test_invalid_raises(self):
        for span, area in ((0.0, 20.0), (-5.0, 20.0), (10.0, 0.0), (10.0, -1.0)):
            with self.assertRaises(ValueError):
                wp.aspect_ratio(span, area)


class TaperRatioTest(unittest.TestCase):
    def test_analytic(self):
        self.assertAlmostEqual(wp.taper_ratio(1.6483516, 5.4945055), 0.3, places=6)

    def test_rectangular_wing(self):
        self.assertAlmostEqual(wp.taper_ratio(2.0, 2.0), 1.0, places=6)

    def test_invalid_raises(self):
        # Tip chord larger than root chord is a negative-taper violation.
        with self.assertRaises(ValueError):
            wp.taper_ratio(3.0, 2.0)
        for tip, root in ((0.0, 2.0), (1.0, 0.0), (-1.0, 2.0)):
            with self.assertRaises(ValueError):
                wp.taper_ratio(tip, root)


class TrapezoidalChordsTest(unittest.TestCase):
    def test_analytic_worked_example(self):
        cr, ct, mgc = wp.trapezoidal_chords(B, S, LAM)
        self.assertAlmostEqual(cr, 5.4945055, places=6)
        self.assertAlmostEqual(ct, 1.6483516, places=6)
        self.assertAlmostEqual(mgc, 3.5714286, places=6)

    def test_rectangle(self):
        cr, ct, mgc = wp.trapezoidal_chords(10.0, 20.0, 1.0)
        self.assertEqual((cr, ct, mgc), (2.0, 2.0, 2.0))

    def test_area_consistency(self):
        cr, ct, mgc = wp.trapezoidal_chords(B, S, LAM)
        # S = b * (cr + ct) / 2 for a trapezoid.
        self.assertAlmostEqual(B * (cr + ct) / 2.0, S, places=6)
        self.assertAlmostEqual(B * mgc, S, places=6)

    def test_invalid_raises(self):
        for taper in (0.0, -0.2, 1.5):
            with self.assertRaises(ValueError):
                wp.trapezoidal_chords(B, S, taper)
        with self.assertRaises(ValueError):
            wp.trapezoidal_chords(0.0, S, LAM)
        with self.assertRaises(ValueError):
            wp.trapezoidal_chords(B, 0.0, LAM)


class ChordAtStationTest(unittest.TestCase):
    def test_analytic_stations(self):
        # c(0) = cr, c(1) = ct, c(0.25) = cr*(1 - 0.7*0.25).
        self.assertAlmostEqual(wp.chord_at_station(B, S, LAM, 0.0), 5.4945055, places=6)
        self.assertAlmostEqual(wp.chord_at_station(B, S, LAM, 1.0), 1.6483516, places=6)
        self.assertAlmostEqual(
            wp.chord_at_station(B, S, LAM, 0.25), 4.5329670, places=6
        )

    def test_linear_in_eta(self):
        # c(0.5) = (c(0) + c(1)) / 2 for a linear taper.
        mid = wp.chord_at_station(B, S, LAM, 0.5)
        self.assertAlmostEqual(mid, (5.4945055 + 1.6483516) / 2.0, places=6)

    def test_invalid_eta_raises(self):
        for eta in (-0.1, 1.1, 2.0):
            with self.assertRaises(ValueError):
                wp.chord_at_station(B, S, LAM, eta)


class MeanAerodynamicChordTest(unittest.TestCase):
    def test_analytic_worked_example(self):
        # (2/3)*5.4945055*(1.39/1.3) = 3.916596.
        self.assertAlmostEqual(
            wp.mean_aerodynamic_chord(5.4945055, LAM), 3.916596, places=5
        )

    def test_rectangular_wing(self):
        # lambda = 1 -> MAC = cr.
        self.assertAlmostEqual(wp.mean_aerodynamic_chord(2.0, 1.0), 2.0, places=6)

    def test_triangle_wing(self):
        # lambda -> 0 -> MAC = (2/3) cr.
        self.assertAlmostEqual(
            wp.mean_aerodynamic_chord(3.0, 0.0 + 1e-9), 2.0, places=4
        )

    def test_invalid_raises(self):
        for root, taper in ((0.0, LAM), (-2.0, LAM), (5.0, 0.0), (5.0, 1.5)):
            with self.assertRaises(ValueError):
                wp.mean_aerodynamic_chord(root, taper)


class MacSpanStationTest(unittest.TestCase):
    def test_analytic_worked_example(self):
        # (35/6)*(1.6/1.3) = 7.179487.
        self.assertAlmostEqual(wp.mac_span_station(B, LAM), 7.179487, places=5)

    def test_rectangular_wing(self):
        # lambda = 1 -> y_MAC = b/4.
        self.assertAlmostEqual(wp.mac_span_station(10.0, 1.0), 2.5, places=6)

    def test_triangle_wing(self):
        # lambda -> 0 -> y_MAC = b/6.
        self.assertAlmostEqual(
            wp.mac_span_station(12.0, 0.0 + 1e-9), 2.0, places=4
        )

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            wp.mac_span_station(0.0, LAM)
        with self.assertRaises(ValueError):
            wp.mac_span_station(B, 1.5)


class SweepConvertTest(unittest.TestCase):
    def test_analytic_worked_example(self):
        # LE = 30 deg, lambda = 0.3, AR = 9.8.
        self.assertAlmostEqual(
            wp.sweep_convert(30.0, 0.0, 0.25, B, S, LAM), 27.582801, places=4
        )
        self.assertAlmostEqual(
            wp.sweep_convert(30.0, 0.0, 0.5, B, S, LAM), 25.054216, places=4
        )
        self.assertAlmostEqual(
            wp.sweep_convert(30.0, 0.0, 1.0, B, S, LAM), 19.675529, places=4
        )

    def test_round_trip(self):
        c4 = wp.sweep_convert(30.0, 0.0, 0.25, B, S, LAM)
        back = wp.sweep_convert(c4, 0.25, 0.0, B, S, LAM)
        self.assertAlmostEqual(back, 30.0, places=6)

    def test_rectangular_wing_sweep_unchanged(self):
        # lambda = 1 -> all reference lines share the sweep angle.
        self.assertAlmostEqual(
            wp.sweep_convert(25.0, 0.0, 0.25, 10.0, 20.0, 1.0), 25.0, places=6
        )

    def test_straight_trailing_edge(self):
        # tan(LE) = 4*(1-lambda)/(AR*(1+lambda)) -> TE sweep = 0.
        le = math.degrees(math.atan(4.0 * 0.7 / (9.8 * 1.3)))
        self.assertAlmostEqual(le, 12.395407, places=5)
        self.assertAlmostEqual(
            wp.sweep_convert(le, 0.0, 1.0, B, S, LAM), 0.0, places=6
        )

    def test_invalid_raises(self):
        for sweep in (-90.0, 90.0, 120.0):
            with self.assertRaises(ValueError):
                wp.sweep_convert(sweep, 0.0, 0.25, B, S, LAM)
        for ref in (-0.1, 1.1):
            with self.assertRaises(ValueError):
                wp.sweep_convert(30.0, ref, 0.25, B, S, LAM)
        with self.assertRaises(ValueError):
            wp.sweep_convert(30.0, 0.0, 0.0, B, S, LAM)


class SchrenkLoadingTest(unittest.TestCase):
    def test_analytic_worked_example(self):
        # CL = 0.5 at eta = 0.25: l = 0.5*[2*125/(pi*35)*sqrt(0.9375) + 4.532967/2].
        l, cl = wp.schrenk_loading(B, S, LAM, 0.5, 0.25)
        self.assertAlmostEqual(l, 2.233964, places=5)
        self.assertAlmostEqual(cl, 0.492826, places=5)

    def test_analytic_root_and_tip(self):
        l0, cl0 = wp.schrenk_loading(B, S, LAM, 0.5, 0.0)
        self.assertAlmostEqual(l0, 2.510447, places=5)
        self.assertAlmostEqual(cl0, 0.456901, places=5)
        lt, clt = wp.schrenk_loading(B, S, LAM, 0.5, 1.0)
        self.assertAlmostEqual(lt, 0.412088, places=5)
        self.assertAlmostEqual(clt, 0.25, places=6)

    def test_tip_cl_is_half_cl_wing(self):
        # At eta = 1 the elliptic term vanishes and l = CL*c/2, so
        # cl_tip = CL/2 for any taper.
        for lam in (0.2, 0.5, 1.0):
            _l, cl = wp.schrenk_loading(20.0, 60.0, lam, 0.8, 1.0)
            self.assertAlmostEqual(cl, 0.4, places=6)

    def test_rectangular_wing(self):
        l0, cl0 = wp.schrenk_loading(10.0, 20.0, 1.0, 0.5, 0.0)
        self.assertAlmostEqual(l0, 1.136620, places=5)
        self.assertAlmostEqual(cl0, 0.568310, places=5)
        lt, clt = wp.schrenk_loading(10.0, 20.0, 1.0, 0.5, 1.0)
        self.assertAlmostEqual(lt, 0.5, places=6)
        self.assertAlmostEqual(clt, 0.25, places=6)

    def test_loading_integrates_to_total_lift(self):
        # Full-span integral of the loading equals CL*S (trapezoid rule).
        cl_wing = 0.5
        n = 4001
        h = 1.0 / (n - 1)
        acc = 0.0
        for i in range(n):
            eta = i * h
            lv = wp.schrenk_loading(B, S, LAM, cl_wing, eta)[0]
            wgt = 1.0 if (i == 0 or i == n - 1) else 2.0
            acc += wgt * lv
        integral = acc * h / 2.0  # int_0^1 l d_eta
        self.assertAlmostEqual(B * integral, cl_wing * S, places=3)

    def test_scales_linearly_with_cl(self):
        l_half, _ = wp.schrenk_loading(B, S, LAM, 0.5, 0.25)
        l_full, _ = wp.schrenk_loading(B, S, LAM, 1.0, 0.25)
        self.assertAlmostEqual(l_full, 2.0 * l_half, places=6)

    def test_invalid_raises(self):
        for eta in (-0.1, 1.2):
            with self.assertRaises(ValueError):
                wp.schrenk_loading(B, S, LAM, 0.5, eta)
        with self.assertRaises(ValueError):
            wp.schrenk_loading(0.0, S, LAM, 0.5, 0.25)
        with self.assertRaises(ValueError):
            wp.schrenk_loading(B, 0.0, LAM, 0.5, 0.25)
        with self.assertRaises(ValueError):
            wp.schrenk_loading(B, S, 0.0, 0.5, 0.25)


class WashoutTest(unittest.TestCase):
    def test_analytic_required(self):
        # (1.15 - 1.0)/5.0265482 rad = 1.709795 deg.
        self.assertAlmostEqual(
            wp.washout_required(1.5, 1.0, 1.30, 1.15, 5.0265482),
            1.709795,
            places=5,
        )

    def test_no_washout_when_tip_inside_clmax(self):
        # Tip local cl below tip clmax: no washout needed.
        self.assertEqual(
            wp.washout_required(1.5, 1.0, 1.30, 0.9, 5.0265482), 0.0
        )

    def test_exact_margin_gives_zero(self):
        self.assertEqual(
            wp.washout_required(1.5, 1.0, 1.30, 1.0, 5.0265482), 0.0
        )

    def test_linear_washout_angle(self):
        # alpha_root 6 deg, washout 2 deg at tip: alpha_eff(0.5) = 5 deg.
        self.assertAlmostEqual(
            wp.linear_washout_angle(6.0, 2.0, 0.5), 5.0, places=6
        )
        self.assertAlmostEqual(
            wp.linear_washout_angle(6.0, 2.0, 0.0), 6.0, places=6
        )
        self.assertAlmostEqual(
            wp.linear_washout_angle(6.0, 2.0, 1.0), 4.0, places=6
        )

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            wp.washout_required(0.0, 1.0, 1.3, 1.15, 5.0265482)
        with self.assertRaises(ValueError):
            wp.washout_required(1.5, -1.0, 1.3, 1.15, 5.0265482)
        with self.assertRaises(ValueError):
            wp.washout_required(1.5, 1.0, 1.3, 1.15, 0.0)
        for eta in (-0.1, 1.5):
            with self.assertRaises(ValueError):
                wp.linear_washout_angle(6.0, 2.0, eta)


if __name__ == "__main__":
    unittest.main(verbosity=2)
