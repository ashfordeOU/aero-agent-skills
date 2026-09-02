#!/usr/bin/env python3
"""Gate 3 contract test: high-lift systems estimation.

Exercises scripts/high_lift_systems_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - DATCOM-style section clmax
increment for plain, split, slotted, and Fowler flaps scaled by
deflection, flap chord ratio, and flapped span fraction; leading-edge
slat and Krueger increments by superposition; wing-level CLmax with
three-dimensional and sweep reduction; stall speed from weight, wing
area, density, and CLmax; flap drag (zero-lift plus induced) and
pitching moment increments; ValueError on nonsense inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import high_lift_systems_logic as hl  # noqa: E402


class FlapClmaxIncrementTest(unittest.TestCase):
    def test_plain_flap_at_30_deg(self):
        # 0.9 * sin(30) / sin(60) = 0.51962 (reference chord, full span)
        self.assertAlmostEqual(
            hl.flap_clmax_increment("plain", 30.0), 0.51962, delta=1e-4
        )

    def test_full_deflection_gives_reference_value(self):
        self.assertAlmostEqual(hl.flap_clmax_increment("fowler", 40.0), 1.7, delta=1e-9)
        self.assertAlmostEqual(
            hl.flap_clmax_increment("slotted", 40.0), 1.3, delta=1e-9
        )

    def test_zero_deflection_gives_zero(self):
        self.assertAlmostEqual(hl.flap_clmax_increment("plain", 0.0), 0.0, delta=1e-12)
        self.assertAlmostEqual(
            hl.flap_clmax_increment("fowler", 0.0), 0.0, delta=1e-12
        )

    def test_increment_monotonic_in_deflection(self):
        lo = hl.flap_clmax_increment("slotted", 10.0)
        mid = hl.flap_clmax_increment("slotted", 25.0)
        hi = hl.flap_clmax_increment("slotted", 40.0)
        self.assertLess(lo, mid)
        self.assertLess(mid, hi)

    def test_deflection_beyond_max_clamps(self):
        self.assertAlmostEqual(
            hl.flap_clmax_increment("plain", 90.0), 0.9, delta=1e-9
        )
        self.assertAlmostEqual(
            hl.flap_clmax_increment("fowler", 80.0), 1.7, delta=1e-9
        )

    def test_type_ordering_at_same_deflection(self):
        # fowler > slotted > split == plain at the reference chord ratios
        plain = hl.flap_clmax_increment("plain", 30.0)
        split = hl.flap_clmax_increment("split", 30.0)
        slotted = hl.flap_clmax_increment("slotted", 30.0)
        fowler = hl.flap_clmax_increment("fowler", 30.0)
        self.assertLess(slotted, fowler)
        self.assertLess(split, slotted)
        self.assertAlmostEqual(split, plain, delta=1e-9)

    def test_chord_ratio_scaling(self):
        # slotted at full deflection, chord ratio 0.30 vs reference 0.25
        self.assertAlmostEqual(
            hl.flap_clmax_increment("slotted", 40.0, chord_frac=0.30),
            1.3 * (0.30 / 0.25),
            delta=1e-9,
        )

    def test_span_fraction_scaling(self):
        self.assertAlmostEqual(
            hl.flap_clmax_increment("slotted", 40.0, span_frac=0.6),
            1.3 * 0.6,
            delta=1e-9,
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            hl.flap_clmax_increment("spoiler", 30.0)
        with self.assertRaises(ValueError):
            hl.flap_clmax_increment("plain", -5.0)
        with self.assertRaises(ValueError):
            hl.flap_clmax_increment("plain", 30.0, chord_frac=0.0)
        with self.assertRaises(ValueError):
            hl.flap_clmax_increment("plain", 30.0, chord_frac=1.5)
        with self.assertRaises(ValueError):
            hl.flap_clmax_increment("plain", 30.0, span_frac=0.0)
        with self.assertRaises(ValueError):
            hl.flap_clmax_increment("plain", 30.0, span_frac=2.0)


class FowlerChordRatioTest(unittest.TestCase):
    def test_chord_extension(self):
        self.assertAlmostEqual(hl.fowler_chord_ratio(0.25), 1.25, delta=1e-12)
        self.assertAlmostEqual(hl.fowler_chord_ratio(0.0), 1.0, delta=1e-12)

    def test_bad_extension_raises(self):
        with self.assertRaises(ValueError):
            hl.fowler_chord_ratio(-0.1)
        with self.assertRaises(ValueError):
            hl.fowler_chord_ratio(1.0)


class LeadingEdgeDeviceTest(unittest.TestCase):
    def test_full_span_slat(self):
        self.assertAlmostEqual(hl.slat_clmax_increment("slat"), 0.5, delta=1e-9)

    def test_partial_span_slat(self):
        self.assertAlmostEqual(
            hl.slat_clmax_increment("slat", span_frac=0.5), 0.25, delta=1e-9
        )

    def test_krueger(self):
        self.assertAlmostEqual(
            hl.slat_clmax_increment("krueger"), 0.4, delta=1e-9
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            hl.slat_clmax_increment("vortex-generator")
        with self.assertRaises(ValueError):
            hl.slat_clmax_increment("slat", span_frac=0.0)


class CombinedIncrementTest(unittest.TestCase):
    def test_superposition(self):
        flap = hl.flap_clmax_increment("slotted", 40.0)
        slat = hl.slat_clmax_increment("slat")
        self.assertAlmostEqual(
            hl.combined_clmax_increment(flap, slat), 1.8, delta=1e-9
        )

    def test_bad_increment_raises(self):
        with self.assertRaises(ValueError):
            hl.combined_clmax_increment(-0.1, 0.5)


class WingClmaxTest(unittest.TestCase):
    def test_unswept_wing(self):
        # 0.9 * 1.5 = 1.35
        self.assertAlmostEqual(hl.wing_clmax(1.5), 1.35, delta=1e-9)

    def test_swept_wing(self):
        # 0.9 * 1.5 * cos(30 deg) = 1.16913
        self.assertAlmostEqual(hl.wing_clmax(1.5, sweep_deg=30.0), 1.16913, delta=1e-4)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            hl.wing_clmax(0.0)
        with self.assertRaises(ValueError):
            hl.wing_clmax(1.5, sweep_deg=90.0)


class StallSpeedTest(unittest.TestCase):
    def test_known_value(self):
        # V = sqrt(2 * 10000 / (1.0 * 20 * 2.0)) = sqrt(500) = 22.3607
        self.assertAlmostEqual(
            hl.stall_speed(10000.0, 20.0, 1.0, 2.0), 22.36068, delta=1e-3
        )

    def test_identity(self):
        w, s, rho, cl = 200000.0, 50.0, 1.225, 1.5
        v = hl.stall_speed(w, s, rho, cl)
        self.assertAlmostEqual(
            v * v, 2.0 * w / (rho * s * cl), delta=1e-6
        )

    def test_higher_clmax_lowers_stall_speed(self):
        self.assertLess(
            hl.stall_speed(10000.0, 20.0, 1.0, 2.5),
            hl.stall_speed(10000.0, 20.0, 1.0, 2.0),
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            hl.stall_speed(0.0, 20.0, 1.0, 2.0)
        with self.assertRaises(ValueError):
            hl.stall_speed(10000.0, 0.0, 1.0, 2.0)
        with self.assertRaises(ValueError):
            hl.stall_speed(10000.0, 20.0, 0.0, 2.0)
        with self.assertRaises(ValueError):
            hl.stall_speed(10000.0, 20.0, 1.0, 0.0)


class FlapDragIncrementTest(unittest.TestCase):
    def test_known_value(self):
        # cd0 = 0.08 * sin(20)/sin(40) = 0.04257;
        # cdi = 0.5^2 / (pi * 9 * 0.8) = 0.01105
        cd0, cdi, total = hl.flap_drag_increment("slotted", 20.0, 0.5, 9.0)
        self.assertAlmostEqual(cd0, 0.04257, delta=1e-4)
        self.assertAlmostEqual(cdi, 0.01105, delta=1e-4)
        self.assertAlmostEqual(total, 0.05362, delta=1e-4)

    def test_zero_deflection_zero_cd0(self):
        cd0, _, _ = hl.flap_drag_increment("plain", 0.0, 0.5, 9.0)
        self.assertAlmostEqual(cd0, 0.0, delta=1e-12)

    def test_induced_drag_grows_with_delta_cl(self):
        _, cdi_lo, _ = hl.flap_drag_increment("plain", 30.0, 0.3, 9.0)
        _, cdi_hi, _ = hl.flap_drag_increment("plain", 30.0, 0.6, 9.0)
        self.assertLess(cdi_lo, cdi_hi)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            hl.flap_drag_increment("nope", 30.0, 0.5, 9.0)
        with self.assertRaises(ValueError):
            hl.flap_drag_increment("plain", -1.0, 0.5, 9.0)
        with self.assertRaises(ValueError):
            hl.flap_drag_increment("plain", 30.0, 0.0, 9.0)
        with self.assertRaises(ValueError):
            hl.flap_drag_increment("plain", 30.0, 0.5, 0.0)
        with self.assertRaises(ValueError):
            hl.flap_drag_increment("plain", 30.0, 0.5, 9.0, oswald_e=0.0)


class PitchingMomentTest(unittest.TestCase):
    def test_fowler_nose_down(self):
        # -1.2 * (0.58 - 0.25) = -0.396
        self.assertAlmostEqual(
            hl.flap_pitch_moment_increment("fowler", 1.2), -0.396, delta=1e-9
        )

    def test_plain_flap_moment(self):
        # -0.5 * (0.50 - 0.25) = -0.125
        self.assertAlmostEqual(
            hl.flap_pitch_moment_increment("plain", 0.5), -0.125, delta=1e-9
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            hl.flap_pitch_moment_increment("fowler", 0.0)
        with self.assertRaises(ValueError):
            hl.flap_pitch_moment_increment("fowler", 0.5, ac_frac=1.5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
