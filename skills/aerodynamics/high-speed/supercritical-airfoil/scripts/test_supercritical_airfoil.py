#!/usr/bin/env python3
"""Gate 3 contract test: supercritical airfoil design and analysis.

Exercises scripts/supercritical_airfoil_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - supercritical
airfoil logic: terminating shock strength p2/p1 across the
upper-surface supersonic pocket, the wave-drag penalty index
(M - M_DD)^3 above drag divergence, the Korn drag-divergence Mach rule
0.95/0.90 - t/c - C_L/10, the inverse-Korn thickness and cruise lift
limits, and the aft-loading pitching moment, with range checks raising
ValueError on invalid inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import supercritical_airfoil_logic as sc  # noqa: E402


class TerminatingShockStrengthTest(unittest.TestCase):
    def test_conventional_peak_mach_13(self):
        # p2/p1 at M 1.3: 1 + 2.8/2.4 * (1.69 - 1) = 1.805
        self.assertAlmostEqual(sc.terminating_shock_strength(1.3), 1.805, delta=1e-3)

    def test_flat_top_mach_115(self):
        # p2/p1 at M 1.15: 1 + 2.8/2.4 * (1.3225 - 1) = 1.376
        self.assertAlmostEqual(sc.terminating_shock_strength(1.15), 1.376, delta=1e-3)

    def test_flat_top_shock_weaker_than_conventional(self):
        # the supercritical mechanism: weaker terminating shock
        self.assertLess(
            sc.terminating_shock_strength(1.15), sc.terminating_shock_strength(1.3)
        )

    def test_monotone_increasing(self):
        self.assertLess(
            sc.terminating_shock_strength(1.2), sc.terminating_shock_strength(1.4)
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sc.terminating_shock_strength(1.0)  # sonic: no shock
        with self.assertRaises(ValueError):
            sc.terminating_shock_strength(0.9)
        with self.assertRaises(ValueError):
            sc.terminating_shock_strength(2.5)
        with self.assertRaises(ValueError):
            sc.terminating_shock_strength(-1.0)


class WaveDragPenaltyTest(unittest.TestCase):
    def test_penalty_at_01_above_mdd(self):
        # (0.85 - 0.75)^3 = 0.001
        self.assertAlmostEqual(
            sc.wave_drag_penalty(0.85, 0.75), (0.85 - 0.75) ** 3, delta=1e-12
        )

    def test_zero_at_and_below_mdd(self):
        self.assertEqual(sc.wave_drag_penalty(0.75, 0.75), 0.0)
        self.assertEqual(sc.wave_drag_penalty(0.74, 0.75), 0.0)

    def test_monotone_increasing_above_mdd(self):
        self.assertGreater(sc.wave_drag_penalty(0.82, 0.75), sc.wave_drag_penalty(0.78, 0.75))

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sc.wave_drag_penalty(1.0, 0.75)
        with self.assertRaises(ValueError):
            sc.wave_drag_penalty(0.4, 0.75)
        with self.assertRaises(ValueError):
            sc.wave_drag_penalty(0.85, 0.5)
        with self.assertRaises(ValueError):
            sc.wave_drag_penalty(0.85, 1.0)
        with self.assertRaises(ValueError):
            sc.wave_drag_penalty(0.85, -0.1)


class DragDivergenceMachTest(unittest.TestCase):
    def test_supercritical_12_percent_at_cl_05(self):
        # 0.95 - 0.12 - 0.5/10 = 0.78
        self.assertAlmostEqual(sc.drag_divergence_mach(0.12, 0.5), 0.78, delta=1e-9)

    def test_conventional_12_percent_at_cl_05(self):
        # 0.90 - 0.12 - 0.5/10 = 0.73
        self.assertAlmostEqual(sc.drag_divergence_mach(0.12, 0.5, False), 0.73, delta=1e-9)

    def test_supercritical_gain_is_005(self):
        gain = sc.drag_divergence_mach(0.12, 0.5, True) - sc.drag_divergence_mach(
            0.12, 0.5, False
        )
        self.assertAlmostEqual(gain, 0.05, delta=1e-9)

    def test_thickness_reduces_mdd(self):
        self.assertGreater(
            sc.drag_divergence_mach(0.10, 0.5), sc.drag_divergence_mach(0.15, 0.5)
        )

    def test_lift_reduces_mdd(self):
        self.assertGreater(
            sc.drag_divergence_mach(0.12, 0.3), sc.drag_divergence_mach(0.12, 0.6)
        )

    def test_zero_lift_allowed(self):
        # 0.95 - 0.12 - 0 = 0.83
        self.assertAlmostEqual(sc.drag_divergence_mach(0.12, 0.0), 0.83, delta=1e-9)

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sc.drag_divergence_mach(0.01, 0.5)  # too thin
        with self.assertRaises(ValueError):
            sc.drag_divergence_mach(0.30, 0.5)  # boundary excluded
        with self.assertRaises(ValueError):
            sc.drag_divergence_mach(-0.05, 0.5)
        with self.assertRaises(ValueError):
            sc.drag_divergence_mach(0.12, -0.1)
        with self.assertRaises(ValueError):
            sc.drag_divergence_mach(0.12, 1.5)  # boundary excluded
        # conventional section pushed below the high-subsonic band
        with self.assertRaises(ValueError):
            sc.drag_divergence_mach(0.28, 1.4, False)


class MaxThicknessRatioTest(unittest.TestCase):
    def test_supercritical_at_mach_08(self):
        # 0.95 - 0.8 - 0.5/10 = 0.10
        self.assertAlmostEqual(sc.max_thickness_ratio(0.8, 0.5), 0.10, delta=1e-9)

    def test_conventional_at_mach_08(self):
        # 0.90 - 0.8 - 0.5/10 = 0.05
        self.assertAlmostEqual(sc.max_thickness_ratio(0.8, 0.5, False), 0.05, delta=1e-9)

    def test_supercritical_roughly_twice_as_thick(self):
        self.assertGreater(
            sc.max_thickness_ratio(0.8, 0.5, True),
            2.0 * sc.max_thickness_ratio(0.8, 0.5, False) - 1e-9,
        )

    def test_round_trip_with_drag_divergence_mach(self):
        tc = sc.max_thickness_ratio(0.8, 0.5)
        self.assertAlmostEqual(sc.drag_divergence_mach(tc, 0.5), 0.8, delta=1e-9)

    def test_higher_mach_means_thinner(self):
        self.assertLess(sc.max_thickness_ratio(0.82, 0.5), sc.max_thickness_ratio(0.78, 0.5))

    def test_bad_inputs_raise(self):
        # conventional section has no thickness left at M 0.85, C_L 0.5
        with self.assertRaises(ValueError):
            sc.max_thickness_ratio(0.85, 0.5, False)
        with self.assertRaises(ValueError):
            sc.max_thickness_ratio(0.85, 0.9, True)  # t/c would be 0.01
        with self.assertRaises(ValueError):
            sc.max_thickness_ratio(1.0, 0.5)
        with self.assertRaises(ValueError):
            sc.max_thickness_ratio(0.3, 0.5)
        with self.assertRaises(ValueError):
            sc.max_thickness_ratio(0.8, -0.1)
        with self.assertRaises(ValueError):
            sc.max_thickness_ratio(0.8, 1.5)


class MaxCruiseLiftCoefficientTest(unittest.TestCase):
    def test_supercritical_at_mach_08_tc_010(self):
        # 10 * (0.95 - 0.10 - 0.80) = 0.5
        self.assertAlmostEqual(sc.max_cruise_lift_coefficient(0.8, 0.10), 0.5, delta=1e-9)

    def test_conventional_cannot_cruise_at_mach_08_tc_010(self):
        # 10 * (0.90 - 0.10 - 0.80) = 0: no cruise lift left
        with self.assertRaises(ValueError):
            sc.max_cruise_lift_coefficient(0.8, 0.10, False)

    def test_round_trip_with_drag_divergence_mach(self):
        mdd = sc.drag_divergence_mach(0.10, 0.5)
        self.assertAlmostEqual(sc.max_cruise_lift_coefficient(mdd, 0.10), 0.5, delta=1e-9)

    def test_higher_mach_means_lower_cl(self):
        self.assertLess(
            sc.max_cruise_lift_coefficient(0.82, 0.10),
            sc.max_cruise_lift_coefficient(0.78, 0.10),
        )

    def test_thicker_section_means_lower_cl(self):
        self.assertGreater(
            sc.max_cruise_lift_coefficient(0.8, 0.08),
            sc.max_cruise_lift_coefficient(0.8, 0.12),
        )

    def test_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            sc.max_cruise_lift_coefficient(0.85, 0.10, True)  # C_L would be 0
        with self.assertRaises(ValueError):
            sc.max_cruise_lift_coefficient(0.9, 0.08, True)
        with self.assertRaises(ValueError):
            sc.max_cruise_lift_coefficient(1.0, 0.10)
        with self.assertRaises(ValueError):
            sc.max_cruise_lift_coefficient(0.3, 0.10)
        with self.assertRaises(ValueError):
            sc.max_cruise_lift_coefficient(0.8, 0.01)
        with self.assertRaises(ValueError):
            sc.max_cruise_lift_coefficient(0.8, 0.30)


class AftLoadingMomentTest(unittest.TestCase):
    def test_supercritical_moment(self):
        self.assertEqual(sc.aft_loading_moment(True), -0.12)

    def test_conventional_moment(self):
        self.assertEqual(sc.aft_loading_moment(False), -0.06)

    def test_aft_loading_more_negative(self):
        self.assertLess(sc.aft_loading_moment(True), sc.aft_loading_moment(False))

    def test_values_in_documented_band(self):
        # textbook representative ranges
        self.assertLessEqual(-0.14, sc.aft_loading_moment(True))
        self.assertLessEqual(sc.aft_loading_moment(True), -0.10)
        self.assertLessEqual(-0.08, sc.aft_loading_moment(False))
        self.assertLessEqual(sc.aft_loading_moment(False), -0.04)


class DesignTradeIntegrationTest(unittest.TestCase):
    def test_supercritical_delays_divergence_and_weakens_shock(self):
        # both benefits of the flat upper surface in one check
        self.assertGreater(
            sc.drag_divergence_mach(0.12, 0.5, True),
            sc.drag_divergence_mach(0.12, 0.5, False),
        )
        self.assertLess(
            sc.terminating_shock_strength(1.15), sc.terminating_shock_strength(1.3)
        )

    def test_wave_penalty_consistent_with_mdd(self):
        # at M_DD the penalty is zero; just above it, positive
        mdd = sc.drag_divergence_mach(0.12, 0.5)
        self.assertEqual(sc.wave_drag_penalty(mdd, mdd), 0.0)
        self.assertGreater(sc.wave_drag_penalty(mdd + 0.02, mdd), 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
