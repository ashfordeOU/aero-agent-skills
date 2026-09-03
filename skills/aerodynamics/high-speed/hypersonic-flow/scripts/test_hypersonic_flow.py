#!/usr/bin/env python3
"""Gate 3 contract test: hypersonic-flow (modified Newtonian theory).

Exercises scripts/hypersonic_flow_logic.py (stdlib unittest, offline,
deterministic). Contract: the Rayleigh pitot ratio p02/p1, the
finite-Mach stagnation pressure coefficient Cp_max, the modified
Newtonian sine-squared local pressure coefficient, the hypersonic
vacuum limit, and the integrated sphere drag, cone axial-force and
inclined flat-plate force coefficients at gamma 1.4. Worked anchors
(Anderson hypersonic estimates, NACA TR-824 style data): pitot 5.640
at M 2 and 32.65 at M 5, cp_stagnation 1.8275 at M 8, sphere Cd
0.9137, cone CA 0.2138 at 20 deg, flat plate CL/CD/LD at 10 deg.
Invalid inputs raise ValueError.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hypersonic_flow_logic as hfl  # noqa: E402


class RayleighPitotTest(unittest.TestCase):
    def test_pitot_at_m2(self):
        # Known pitot value at M 2, gamma 1.4: p02/p1 = 5.640.
        self.assertAlmostEqual(hfl.rayleigh_pitot_ratio(2.0), 5.640, delta=1e-3)

    def test_pitot_at_m5(self):
        # Known pitot value at M 5, gamma 1.4: p02/p1 = 32.65.
        self.assertAlmostEqual(hfl.rayleigh_pitot_ratio(5.0), 32.65, delta=0.05)

    def test_pitot_at_m8(self):
        # Spec walk-through: base 1.03087^3.5 = 1.1124, second 74.5,
        # p02/p1 = 82.87.
        self.assertAlmostEqual(hfl.rayleigh_pitot_ratio(8.0), 82.87, delta=0.1)

    def test_pitot_at_m12_exceeds_189(self):
        # Weak-shock limit p02/p1 -> 1.893 at M -> 1; M 1.2 must exceed 1.89.
        self.assertGreater(hfl.rayleigh_pitot_ratio(1.2), 1.89)

    def test_pitot_monotonic_in_mach(self):
        # p02/p1 rises monotonically with freestream Mach.
        values = [hfl.rayleigh_pitot_ratio(m) for m in (1.2, 2.0, 3.0, 5.0, 8.0)]
        for lower, upper in zip(values, values[1:]):
            self.assertGreater(upper, lower)


class StagnationCpTest(unittest.TestCase):
    def test_cp_stagnation_at_m5(self):
        # 2/(1.4*25) * (32.65 - 1) = 1.8086.
        self.assertAlmostEqual(hfl.cp_stagnation(5.0), 1.8086, delta=0.002)

    def test_cp_stagnation_at_m8(self):
        # 2/(1.4*64) * (82.87 - 1) = 1.8275.
        self.assertAlmostEqual(hfl.cp_stagnation(8.0), 1.8275, delta=0.002)

    def test_cp_stagnation_approaches_limit_from_below(self):
        # Cp_max approaches 1.839 (gamma 1.4) from below as M grows.
        self.assertAlmostEqual(hfl.CP_MAX_INF, 1.839, delta=1e-12)
        for m in (8.0, 12.0, 20.0, 40.0):
            self.assertLess(hfl.cp_stagnation(m), hfl.CP_MAX_INF)
        self.assertGreater(hfl.cp_stagnation(40.0), hfl.cp_stagnation(8.0))

    def test_cp_stagnation_consistency_with_pitot(self):
        # Cp_max = 2/(gamma M^2) * (p02/p1 - 1) identity.
        for m in (2.0, 5.0, 8.0):
            expect = 2.0 / (1.4 * m * m) * (hfl.rayleigh_pitot_ratio(m) - 1.0)
            self.assertAlmostEqual(hfl.cp_stagnation(m), expect, places=12)


class NewtonianSurfaceTest(unittest.TestCase):
    def test_newtonian_cp_zero_and_ninety(self):
        # sin(0)^2 = 0 gives zero pressure; sin(90)^2 = 1 gives Cp_max.
        self.assertAlmostEqual(hfl.newtonian_cp(0.0, 8.0), 0.0, delta=1e-9)
        self.assertAlmostEqual(hfl.newtonian_cp(90.0, 8.0),
                               hfl.cp_stagnation(8.0), places=10)

    def test_newtonian_cp_sine_squared_scaling(self):
        # Cp(30 deg) = Cp_max * sin(30)^2 = Cp_max * 0.25.
        self.assertAlmostEqual(hfl.newtonian_cp(30.0, 8.0),
                               0.25 * hfl.cp_stagnation(8.0), places=10)

    def test_newtonian_cp_theta_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            hfl.newtonian_cp(-5.0, 8.0)
        with self.assertRaises(ValueError):
            hfl.newtonian_cp(95.0, 8.0)

    def test_vacuum_limit_at_m8(self):
        # Cp_vacuum = -2/(1.4*64) = -0.02232.
        self.assertAlmostEqual(hfl.cp_vacuum(8.0), -0.02232, delta=1e-4)

    def test_vacuum_limit_scales_with_mach(self):
        for m in (2.0, 5.0, 8.0, 12.0):
            self.assertAlmostEqual(hfl.cp_vacuum(m),
                                   -2.0 / (1.4 * m * m), places=12)
            self.assertLess(hfl.cp_vacuum(m), 0.0)


class SphereTest(unittest.TestCase):
    def test_sphere_drag_at_m8(self):
        # Modified Newtonian sphere Cd = Cp_max/2 = 1.8275/2 = 0.9137.
        self.assertAlmostEqual(hfl.sphere_drag_coefficient(8.0), 0.9137,
                               delta=1e-3)

    def test_sphere_drag_at_m5(self):
        # Cd = 1.8086/2 = 0.9043 at M 5.
        self.assertAlmostEqual(hfl.sphere_drag_coefficient(5.0), 0.9043,
                               delta=1e-3)

    def test_sphere_drag_identity(self):
        # Cd = Cp_max / 2 by construction.
        for m in (2.0, 5.0, 8.0):
            self.assertAlmostEqual(hfl.sphere_drag_coefficient(m),
                                   0.5 * hfl.cp_stagnation(m), places=12)


class ConeTest(unittest.TestCase):
    def test_cone_axial_force_at_20_deg(self):
        # sin(20)^2 = 0.11698; CA = 1.8275 * 0.11698 = 0.2138.
        self.assertAlmostEqual(
            hfl.cone_axial_force_coefficient(20.0, 8.0), 0.2138, delta=5e-4)

    def test_cone_axial_force_at_40_deg(self):
        # sin(40)^2 = 0.41318; CA = 1.8275 * 0.41318 = 0.7550.
        self.assertAlmostEqual(
            hfl.cone_axial_force_coefficient(40.0, 8.0), 0.7550, delta=1e-3)

    def test_cone_axial_force_scaling(self):
        # CA grows with the sine-squared of the half angle.
        ca20 = hfl.cone_axial_force_coefficient(20.0, 8.0)
        ca40 = hfl.cone_axial_force_coefficient(40.0, 8.0)
        self.assertAlmostEqual(ca20, hfl.cp_stagnation(8.0)
                               * math.sin(math.radians(20.0)) ** 2, places=10)
        self.assertGreater(ca40, ca20)

    def test_cone_axial_force_half_angle_raises(self):
        with self.assertRaises(ValueError):
            hfl.cone_axial_force_coefficient(0.0, 8.0)
        with self.assertRaises(ValueError):
            hfl.cone_axial_force_coefficient(90.0, 8.0)
        with self.assertRaises(ValueError):
            hfl.cone_axial_force_coefficient(-5.0, 8.0)


class FlatPlateTest(unittest.TestCase):
    def test_flat_plate_at_zero_incidence(self):
        # Zero incidence: no windward pressure, no force.
        result = hfl.flat_plate_coefficients(0.0, 8.0)
        self.assertAlmostEqual(result["cp_windward"], 0.0, delta=1e-9)
        self.assertAlmostEqual(result["cl"], 0.0, delta=1e-9)
        self.assertAlmostEqual(result["cd"], 0.0, delta=1e-9)
        self.assertIsNone(result["ld_ratio"])

    def test_flat_plate_at_10_deg(self):
        # cp_w = 1.8275 * sin(10)^2 = 0.05511; cl = 0.05427;
        # cd = 0.009570; ld = 5.671.
        result = hfl.flat_plate_coefficients(10.0, 8.0)
        self.assertAlmostEqual(result["cp_windward"], 0.05511, delta=1e-3)
        self.assertAlmostEqual(result["cn"], 0.05511, delta=1e-3)
        self.assertAlmostEqual(result["cl"], 0.05427, delta=1e-3)
        self.assertAlmostEqual(result["cd"], 0.009570, delta=1e-3)
        self.assertAlmostEqual(result["ld_ratio"], 5.671, delta=1e-3)

    def test_flat_plate_at_30_deg(self):
        # cp_w = 1.8275 * 0.25 = 0.45684; cl = 0.3956; cd = 0.2284;
        # ld = cot(30) = 1.732.
        result = hfl.flat_plate_coefficients(30.0, 8.0)
        self.assertAlmostEqual(result["cp_windward"], 0.45684, delta=1e-3)
        self.assertAlmostEqual(result["cl"], 0.3956, delta=1e-3)
        self.assertAlmostEqual(result["cd"], 0.2284, delta=1e-3)
        self.assertAlmostEqual(result["ld_ratio"], 1.732, delta=1e-3)

    def test_flat_plate_ld_equals_cot_alpha(self):
        # Newtonian flat plate: CL/CD = cot(alpha) identically.
        for alpha in (5.0, 10.0, 15.0, 30.0):
            result = hfl.flat_plate_coefficients(alpha, 8.0)
            self.assertAlmostEqual(result["ld_ratio"],
                                   1.0 / math.tan(math.radians(alpha)),
                                   places=10)

    def test_flat_plate_force_decomposition(self):
        # CL = CN*cos(alpha), CD = CN*sin(alpha).
        result = hfl.flat_plate_coefficients(20.0, 8.0)
        self.assertAlmostEqual(result["cl"],
                               result["cn"] * math.cos(math.radians(20.0)),
                               places=12)
        self.assertAlmostEqual(result["cd"],
                               result["cn"] * math.sin(math.radians(20.0)),
                               places=12)

    def test_flat_plate_alpha_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            hfl.flat_plate_coefficients(60.0, 8.0)
        with self.assertRaises(ValueError):
            hfl.flat_plate_coefficients(-1.0, 8.0)


class AnalyzeBodyTest(unittest.TestCase):
    def test_analyze_body_sphere(self):
        result = hfl.analyze_body("sphere", {}, 8.0)
        self.assertAlmostEqual(result["drag_coefficient"], 0.9137, delta=1e-3)
        self.assertAlmostEqual(result["cp_stagnation"],
                               hfl.cp_stagnation(8.0), places=12)
        self.assertAlmostEqual(result["pitot_ratio"],
                               hfl.rayleigh_pitot_ratio(8.0), places=12)

    def test_analyze_body_cone(self):
        result = hfl.analyze_body("cone", {"half_angle_deg": 20.0}, 8.0)
        self.assertAlmostEqual(result["axial_force_coefficient"], 0.2138,
                               delta=5e-4)
        self.assertEqual(result["half_angle_deg"], 20.0)
        self.assertAlmostEqual(result["pitot_ratio"],
                               hfl.rayleigh_pitot_ratio(8.0), places=12)

    def test_analyze_body_flat_plate(self):
        result = hfl.analyze_body("flat_plate", {"alpha_deg": 10.0}, 8.0)
        self.assertAlmostEqual(result["cl"], 0.05427, delta=1e-3)
        self.assertAlmostEqual(result["cd"], 0.009570, delta=1e-3)
        self.assertAlmostEqual(result["ld_ratio"], 5.671, delta=1e-3)
        self.assertAlmostEqual(result["cp_stagnation"],
                               hfl.cp_stagnation(8.0), places=12)
        self.assertAlmostEqual(result["pitot_ratio"],
                               hfl.rayleigh_pitot_ratio(8.0), places=12)

    def test_analyze_body_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            hfl.analyze_body("ogive", {}, 8.0)

    def test_analyze_body_missing_geometry_raises(self):
        with self.assertRaises(ValueError):
            hfl.analyze_body("cone", {}, 8.0)
        with self.assertRaises(ValueError):
            hfl.analyze_body("cone", {"half_angle_deg": -5.0}, 8.0)
        with self.assertRaises(ValueError):
            hfl.analyze_body("flat_plate", {}, 8.0)


class InvalidInputTest(unittest.TestCase):
    def test_mach_at_or_below_one_raises(self):
        # M = 1.0 and M = 0.8 are subsonic/sonic: rejected everywhere.
        for m in (1.0, 0.8):
            with self.assertRaises(ValueError):
                hfl.rayleigh_pitot_ratio(m)
            with self.assertRaises(ValueError):
                hfl.cp_stagnation(m)
            with self.assertRaises(ValueError):
                hfl.sphere_drag_coefficient(m)
            with self.assertRaises(ValueError):
                hfl.cone_axial_force_coefficient(20.0, m)
            with self.assertRaises(ValueError):
                hfl.flat_plate_coefficients(10.0, m)
            with self.assertRaises(ValueError):
                hfl.analyze_body("sphere", {}, m)

    def test_gamma_at_or_below_one_raises(self):
        with self.assertRaises(ValueError):
            hfl.rayleigh_pitot_ratio(5.0, gamma=1.0)
        with self.assertRaises(ValueError):
            hfl.cp_stagnation(5.0, gamma=0.9)
        with self.assertRaises(ValueError):
            hfl.cp_vacuum(5.0, gamma=1.0)
        with self.assertRaises(ValueError):
            hfl.analyze_body("sphere", {}, 5.0, gamma=1.0)

    def test_high_gamma_pitot_still_physical(self):
        # Monatomic gas gamma 5/3 gives a larger pitot ratio at M 5.
        self.assertGreater(hfl.rayleigh_pitot_ratio(5.0, gamma=5.0 / 3.0),
                           hfl.rayleigh_pitot_ratio(5.0, gamma=1.4))


if __name__ == "__main__":
    unittest.main(verbosity=2)
