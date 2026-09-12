#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clause 4.6.2.15 riveted-joint analysis.

Exercises scripts/riveted_joint_analysis_logic.py (stdlib unittest, offline).
Contract: shear distribution by centroid method; rivet shear and bearing
margins; inter-rivet buckling critical stress via plate-column formula;
outstanding-flange crippling stress as the lesser of yield and elastic
plate-buckling values; full group check returning per-rivet results and
a joint-pass flag. Invalid inputs (non-positive allowables, out-of-range
Poisson ratio, zero-Ip group with non-zero moment, empty rivet list) raise
RivetJointError. Zero applied force returns math.inf margins.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import riveted_joint_analysis_logic as rj  # noqa: E402


class TestRivetShearMargin(unittest.TestCase):
    def test_positive_margin(self):
        ms = rj.rivet_shear_margin(800.0, 1000.0)
        self.assertAlmostEqual(ms, 0.25)

    def test_negative_margin(self):
        ms = rj.rivet_shear_margin(1200.0, 1000.0)
        self.assertAlmostEqual(ms, -1.0 / 6.0, places=9)

    def test_zero_applied_force_returns_inf(self):
        self.assertEqual(rj.rivet_shear_margin(0.0, 1000.0), math.inf)

    def test_invalid_allowable_raises(self):
        with self.assertRaises(rj.RivetJointError):
            rj.rivet_shear_margin(100.0, 0.0)

    def test_negative_applied_force_raises(self):
        with self.assertRaises(rj.RivetJointError):
            rj.rivet_shear_margin(-50.0, 1000.0)


class TestBearingStressAndMargin(unittest.TestCase):
    def test_bearing_stress_value(self):
        # F=500 N, d=4 mm, t=2 mm → sigma_br = 500/(0.004*0.002) = 62.5 MPa
        sigma = rj.bearing_stress(500.0, 0.004, 0.002)
        self.assertAlmostEqual(sigma, 62.5e6)

    def test_bearing_margin_positive(self):
        # allowable = 125 MPa, applied force produces 62.5 MPa → MS = 1.0
        ms = rj.bearing_margin(500.0, 0.004, 0.002, 125e6)
        self.assertAlmostEqual(ms, 1.0)

    def test_bearing_margin_zero_force_returns_inf(self):
        self.assertEqual(rj.bearing_margin(0.0, 0.004, 0.002, 100e6), math.inf)

    def test_bearing_invalid_allowable_raises(self):
        with self.assertRaises(rj.RivetJointError):
            rj.bearing_margin(100.0, 0.004, 0.002, -10e6)

    def test_bearing_invalid_diameter_raises(self):
        with self.assertRaises(rj.RivetJointError):
            rj.bearing_stress(100.0, 0.0, 0.002)


class TestInterRivetBuckling(unittest.TestCase):
    def _sigma_cr_manual(self, E, nu, t, pitch, c):
        return c * math.pi**2 * E / (12.0 * (1.0 - nu**2)) * (t / pitch)**2

    def test_stress_formula_value(self):
        # E=70 GPa, nu=0.3, t=1 mm, pitch=30 mm, c=4.0
        expected = self._sigma_cr_manual(70e9, 0.3, 1e-3, 30e-3, 4.0)
        result = rj.inter_rivet_buckling_stress(70e9, 0.3, 1e-3, 30e-3, 4.0)
        self.assertAlmostEqual(result, expected, delta=1.0)

    def test_higher_fixity_raises_critical_stress(self):
        s_low = rj.inter_rivet_buckling_stress(70e9, 0.3, 1e-3, 25e-3, fixity_c=3.62)
        s_high = rj.inter_rivet_buckling_stress(70e9, 0.3, 1e-3, 25e-3, fixity_c=6.97)
        self.assertGreater(s_high, s_low)

    def test_buckling_margin_pass(self):
        # sigma_cr ≈ 281 MPa; apply 100 MPa → MS > 0
        ms = rj.inter_rivet_buckling_margin(100e6, 70e9, 0.3, 1e-3, 30e-3)
        self.assertGreater(ms, 0.0)

    def test_buckling_margin_fail(self):
        # apply stress far above sigma_cr → MS < 0
        ms = rj.inter_rivet_buckling_margin(2000e6, 70e9, 0.3, 1e-3, 30e-3)
        self.assertLess(ms, 0.0)

    def test_buckling_margin_zero_applied_returns_inf(self):
        self.assertEqual(
            rj.inter_rivet_buckling_margin(0.0, 70e9, 0.3, 1e-3, 25e-3),
            math.inf,
        )

    def test_invalid_nu_raises(self):
        with self.assertRaises(rj.RivetJointError):
            rj.inter_rivet_buckling_stress(70e9, 0.5, 1e-3, 25e-3)

    def test_invalid_nu_negative_raises(self):
        with self.assertRaises(rj.RivetJointError):
            rj.inter_rivet_buckling_stress(70e9, -0.1, 1e-3, 25e-3)


class TestCripplingStress(unittest.TestCase):
    def test_yield_governs_stocky_flange(self):
        # b/t = 2.5 → sigma_elastic >> Fcy; Fcc should equal Fcy
        Fcy = 300e6
        E = 70e9
        b = 5e-3
        t = 2e-3  # b/t = 2.5
        Fcc = rj.crippling_stress_fcc(Fcy, E, b, t, K_cr=0.9)
        self.assertAlmostEqual(Fcc, Fcy)

    def test_elastic_buckling_governs_thin_flange(self):
        # b/t = 50 → sigma_elastic << Fcy
        Fcy = 300e6
        E = 70e9
        b = 50e-3
        t = 1e-3  # b/t = 50
        # sigma_E = 0.9 * 70e9 * (1/50)^2 = 25.2 MPa < 300 MPa
        expected = 0.9 * E * (t / b)**2
        Fcc = rj.crippling_stress_fcc(Fcy, E, b, t, K_cr=0.9)
        self.assertAlmostEqual(Fcc, expected, delta=1.0)

    def test_crippling_stress_bounded_by_fcy(self):
        Fcc = rj.crippling_stress_fcc(200e6, 70e9, 3e-3, 3e-3)
        self.assertLessEqual(Fcc, 200e6)

    def test_crippling_margin_positive(self):
        # thin flange: Fcc << Fcy; apply stress well below Fcc → MS > 0
        Fcc = rj.crippling_stress_fcc(300e6, 70e9, 50e-3, 1e-3)
        ms = rj.crippling_margin(Fcc * 0.5, 300e6, 70e9, 50e-3, 1e-3)
        self.assertAlmostEqual(ms, 1.0)

    def test_crippling_margin_negative(self):
        # apply 2× Fcc → MS < 0
        Fcc = rj.crippling_stress_fcc(300e6, 70e9, 50e-3, 1e-3)
        ms = rj.crippling_margin(Fcc * 2.0, 300e6, 70e9, 50e-3, 1e-3)
        self.assertAlmostEqual(ms, -0.5)

    def test_crippling_margin_zero_applied_returns_inf(self):
        self.assertEqual(rj.crippling_margin(0.0, 300e6, 70e9, 20e-3, 1e-3), math.inf)

    def test_invalid_fcy_raises(self):
        with self.assertRaises(rj.RivetJointError):
            rj.crippling_stress_fcc(0.0, 70e9, 10e-3, 1e-3)


class TestDistributeShearToRivets(unittest.TestCase):
    def test_pure_shear_splits_evenly(self):
        # 4 rivets at corners; pure shear_x=100 N, no moment
        coords = [(0.05, 0.05), (-0.05, 0.05), (-0.05, -0.05), (0.05, -0.05)]
        forces = rj.distribute_shear_to_rivets(100.0, 0.0, 0.0, coords)
        for fx, fy in forces:
            self.assertAlmostEqual(fx, 25.0)
            self.assertAlmostEqual(fy, 0.0)

    def test_pure_moment_zero_net_force(self):
        # Pure moment: net force across all rivets must be zero
        coords = [(0.05, 0.05), (-0.05, 0.05), (-0.05, -0.05), (0.05, -0.05)]
        forces = rj.distribute_shear_to_rivets(0.0, 0.0, 100.0, coords)
        sum_fx = sum(f[0] for f in forces)
        sum_fy = sum(f[1] for f in forces)
        self.assertAlmostEqual(sum_fx, 0.0, places=9)
        self.assertAlmostEqual(sum_fy, 0.0, places=9)

    def test_moment_resisted_correctly(self):
        # Single rivet pair: moment must equal sum of (dx*fy - dy*fx)
        coords = [(0.1, 0.0), (-0.1, 0.0)]
        M = 200.0
        forces = rj.distribute_shear_to_rivets(0.0, 0.0, M, coords)
        cx = 0.0
        cy = 0.0
        resisted = sum(
            (coords[i][0] - cx) * forces[i][1] - (coords[i][1] - cy) * forces[i][0]
            for i in range(len(coords))
        )
        self.assertAlmostEqual(resisted, M, places=9)

    def test_empty_rivet_list_raises(self):
        with self.assertRaises(rj.RivetJointError):
            rj.distribute_shear_to_rivets(100.0, 0.0, 0.0, [])

    def test_coincident_rivets_with_moment_raises(self):
        # All rivets at same point — Ip = 0; moment cannot be distributed
        coords = [(0.0, 0.0), (0.0, 0.0)]
        with self.assertRaises(rj.RivetJointError):
            rj.distribute_shear_to_rivets(0.0, 0.0, 50.0, coords)


class TestCheckRivetGroup(unittest.TestCase):
    def test_group_passes_all_margins_positive(self):
        coords = [(0.02, 0.0), (-0.02, 0.0)]
        result = rj.check_rivet_group(
            shear_x=200.0, shear_y=0.0, moment=0.0,
            rivet_coords=coords,
            rivet_diameter=4e-3, sheet_thickness=2e-3,
            allowable_rivet_shear=1000.0, allowable_bearing=500e6,
        )
        self.assertTrue(result["joint_passes"])
        self.assertGreaterEqual(result["worst_shear_ms"], 0.0)
        self.assertGreaterEqual(result["worst_bearing_ms"], 0.0)
        self.assertEqual(len(result["per_rivet"]), 2)

    def test_group_fails_when_shear_exceeded(self):
        coords = [(0.0, 0.0), (0.05, 0.0)]
        result = rj.check_rivet_group(
            shear_x=5000.0, shear_y=0.0, moment=0.0,
            rivet_coords=coords,
            rivet_diameter=4e-3, sheet_thickness=2e-3,
            allowable_rivet_shear=100.0, allowable_bearing=500e6,
        )
        self.assertFalse(result["joint_passes"])
        self.assertLess(result["worst_shear_ms"], 0.0)

    def test_per_rivet_f_total_non_negative(self):
        coords = [(0.0, 0.0), (0.0, 0.03), (0.03, 0.015)]
        result = rj.check_rivet_group(
            shear_x=300.0, shear_y=150.0, moment=5.0,
            rivet_coords=coords,
            rivet_diameter=5e-3, sheet_thickness=2e-3,
            allowable_rivet_shear=2000.0, allowable_bearing=600e6,
        )
        for rv in result["per_rivet"]:
            self.assertGreaterEqual(rv["F_total"], 0.0)


if __name__ == "__main__":
    unittest.main()
