#!/usr/bin/env python3
"""Gate 3 contract test: gust and maneuver loads (FAR 25.341, 25.337).

Exercises scripts/gust_load_logic.py (stdlib unittest, offline,
deterministic). Contract: discrete 1-cosine gust load factor
n = 1 + (rho0*V_e*a*K_g*U_de)/(2*W/S), gust alleviation factor
K_g = 0.88*mu_g/(5.3+mu_g) with mass ratio
mu_g = 2*(W/S)/(rho*cbar*a*g), limit maneuvering load factor 2.5
(normal) or 3.8 (commuter/transport) at VA with linear variation to 0
at VD, negative limit -1.0, V-n diagram construction with the corner
at VA and gust lines at VB/VC/VD, envelope verdicts and margin checks.

Reference values are hand-computed analytic results; invalid inputs
raise ValueError. Contract case: a typical transport at VB with
U_de = 50 fps, W/S = 100 psf, a = 5.7/rad, cbar = 12.5 ft,
rho = rho0 = 0.002378 slugs/ft^3, V_e = 300 KEAS = 506.34 ft/s.

Hand calc:
  mu_g = 2*100/(0.002378*12.5*5.7*32.174) = 36.69
  K_g  = 0.88*36.69/(5.3 + 36.69) = 0.769
  n    = 1 + 0.002378*506.34*5.7*0.769*50/(2*100) = 2.319
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gust_load_logic as gl  # noqa: E402

# Contract-case constants (typical transport at VB).
WS = 100.0          # wing loading, lb/ft^2
CBAR = 12.5         # mean geometric chord, ft
A = 5.7             # lift-curve slope, 1/rad
RHO = 0.002378      # density, slugs/ft^3 (sea level)
VE_VB = 300.0 * 1.68781  # 300 KEAS in ft/s = 506.34
U_DE = 50.0         # design gust velocity, fps EAS
MU_G_REF = 36.69    # hand-calc mass ratio
KG_REF = 0.769      # hand-calc alleviation factor
N_VB_REF = 2.319    # hand-calc gust load factor at VB


class GustAlleviationFactorTest(unittest.TestCase):
    def test_mass_ratio_matches_hand_calc(self):
        mu_g = gl.gust_mass_ratio(WS, CBAR, A, RHO)
        self.assertLess(abs(mu_g - MU_G_REF) / MU_G_REF, 0.01)

    def test_alleviation_factor_matches_hand_calc(self):
        kg = gl.gust_alleviation_factor(WS, CBAR, A, RHO)
        self.assertLess(abs(kg - KG_REF) / KG_REF, 0.01)

    def test_alleviation_factor_is_between_zero_and_one(self):
        kg = gl.gust_alleviation_factor(WS, CBAR, A, RHO)
        self.assertGreater(kg, 0.0)
        self.assertLess(kg, 1.0)

    def test_heavier_airplane_has_higher_alleviation(self):
        # A larger mass ratio (heavier wing loading) raises K_g toward
        # the 0.88 asymptote.
        light = gl.gust_alleviation_factor(50.0, CBAR, A, RHO)
        heavy = gl.gust_alleviation_factor(200.0, CBAR, A, RHO)
        self.assertLess(light, heavy)
        self.assertLess(heavy, 0.88)

    def test_invalid_inputs_raise_value_error(self):
        for kwargs in ({"ws": 0.0}, {"cbar": -1.0}, {"a": 0.0},
                       {"rho": None}, {"g": 0.0}):
            with self.assertRaises(ValueError):
                gl.gust_alleviation_factor(ws=kwargs.get("ws", WS),
                                           cbar=kwargs.get("cbar", CBAR),
                                           a=kwargs.get("a", A),
                                           rho=kwargs.get("rho", RHO),
                                           g=kwargs.get("g", gl.G))


class GustLoadFactorTest(unittest.TestCase):
    def test_transport_at_vb_is_in_two_to_three_range(self):
        n = gl.gust_load_factor(VE_VB, WS, A, U_DE, cbar=CBAR, rho=RHO)
        self.assertGreaterEqual(n, 2.0)
        self.assertLessEqual(n, 3.0)

    def test_transport_at_vb_matches_hand_calc_within_one_percent(self):
        n = gl.gust_load_factor(VE_VB, WS, A, U_DE, cbar=CBAR, rho=RHO)
        self.assertLess(abs(n - N_VB_REF) / N_VB_REF, 0.01)

    def test_gust_load_factor_scales_linearly_with_gust_velocity(self):
        # n = 1 + slope * U_de, so doubling U_de (25 to 50 fps, both
        # within the FAR 25.341 66 fps maximum) doubles the increment.
        n1 = gl.gust_load_factor(VE_VB, WS, A, 25.0, cbar=CBAR, rho=RHO)
        n2 = gl.gust_load_factor(VE_VB, WS, A, 50.0, cbar=CBAR, rho=RHO)
        self.assertAlmostEqual(n2, 1.0 + 2.0 * (n1 - 1.0), places=10)

    def test_down_gust_reduces_load_factor(self):
        n = gl.gust_load_factor(VE_VB, WS, A, -U_DE, cbar=CBAR, rho=RHO)
        self.assertLess(n, 1.0)
        self.assertGreater(n, -1.0)

    def test_kg_may_be_passed_directly(self):
        kg = gl.gust_alleviation_factor(WS, CBAR, A, RHO)
        n1 = gl.gust_load_factor(VE_VB, WS, A, U_DE, kg=kg)
        n2 = gl.gust_load_factor(VE_VB, WS, A, U_DE, cbar=CBAR, rho=RHO)
        self.assertAlmostEqual(n1, n2, places=10)

    def test_invalid_gust_velocity_raises_value_error(self):
        for u_de in (0.0, 100.0, -100.0, "gusty", None):
            with self.assertRaises(ValueError):
                gl.gust_load_factor(VE_VB, WS, A, u_de, cbar=CBAR, rho=RHO)

    def test_missing_alleviation_inputs_raise_value_error(self):
        with self.assertRaises(ValueError):
            gl.gust_load_factor(VE_VB, WS, A, U_DE)

    def test_invalid_speeds_raise_value_error(self):
        for kwargs in ({"ve": 0.0}, {"ve": -1.0}, {"ws": 0.0},
                       {"a": None}, {"rho0": -0.002378}):
            with self.assertRaises(ValueError):
                gl.gust_load_factor(ve=kwargs.get("ve", VE_VB),
                                    ws=kwargs.get("ws", WS),
                                    a=kwargs.get("a", A),
                                    u_de=U_DE,
                                    cbar=CBAR, rho=RHO,
                                    rho0=kwargs.get("rho0", gl.RHO0))


class ManeuverLimitTest(unittest.TestCase):
    def test_normal_category_limit_at_va(self):
        self.assertEqual(gl.maneuver_limit_load_factor("normal"), 2.5)

    def test_commuter_category_limit_at_va(self):
        self.assertEqual(gl.maneuver_limit_load_factor("commuter"), 3.8)

    def test_transport_category_limit_at_va(self):
        self.assertEqual(gl.maneuver_limit_load_factor("transport"), 3.8)

    def test_negative_limit(self):
        self.assertEqual(gl.maneuver_limit_load_factor(negative=True), -1.0)

    def test_linear_variation_to_zero_at_vd(self):
        va, vd = 363.7, 621.0
        # Midway between VA and VD the positive limit is n_VA/2.
        mid = 0.5 * (va + vd)
        self.assertAlmostEqual(
            gl.maneuver_limit_load_factor("normal", speed=mid, va=va, vd=vd),
            1.25, places=3)
        # At VD the limit is exactly zero.
        self.assertEqual(
            gl.maneuver_limit_load_factor("normal", speed=vd, va=va, vd=vd),
            0.0)
        # At and below VA the plateau value applies.
        self.assertEqual(
            gl.maneuver_limit_load_factor("normal", speed=va, va=va, vd=vd),
            2.5)
        self.assertEqual(
            gl.maneuver_limit_load_factor("normal", speed=200.0, va=va, vd=vd),
            2.5)

    def test_invalid_category_raises_value_error(self):
        with self.assertRaises(ValueError):
            gl.maneuver_limit_load_factor("acrobatic")

    def test_linear_variation_requires_va_and_vd(self):
        with self.assertRaises(ValueError):
            gl.maneuver_limit_load_factor("normal", speed=400.0)
        with self.assertRaises(ValueError):
            gl.maneuver_limit_load_factor("normal", speed=400.0, va=300.0)
        with self.assertRaises(ValueError):
            gl.maneuver_limit_load_factor("normal", speed=400.0, va=500.0,
                                          vd=400.0)


class VnDiagramTest(unittest.TestCase):
    def setUp(self):
        # Typical transport: VS = 230 ft/s, VD = 2.7 * VS.
        self.vn = gl.vn_diagram(ws=WS, vs=230.0, vd=621.0, a=A, cbar=CBAR)

    def test_corner_point_at_va(self):
        # VA = VS * sqrt(n_VA) = 230 * sqrt(2.5) = 363.66 ft/s.
        self.assertAlmostEqual(self.vn["va"], 230.0 * math.sqrt(2.5),
                               places=2)
        self.assertEqual(self.vn["n_positive"], 2.5)
        self.assertEqual(self.vn["n_negative"], -1.0)

    def test_default_speeds_and_ordering(self):
        self.assertEqual(self.vn["vb"], 1.8 * 230.0)
        self.assertEqual(self.vn["vc"], 2.0 * 230.0)
        self.assertTrue(self.vn["vs"] < self.vn["va"] < self.vn["vb"]
                        < self.vn["vc"] < self.vn["vd"])

    def test_gust_point_at_vb_matches_hand_calc(self):
        p = self.vn["gust_points"][0]
        self.assertEqual(p["speed"], "VB")
        self.assertAlmostEqual(p["u_de_pos"], 66.0)
        # FAR 25.341(a)(6) design gust at VB is 66 fps EAS; hand calc
        # n = 1 + 0.002378*414*5.7*0.769*66/(2*100) = 2.424.
        self.assertLess(abs(p["n_pos"] - 2.424) / 2.424, 0.01)
        # Same airplane in the -66 fps down gust at VB: n = -0.424.
        self.assertLess(abs(p["n_neg"] + 0.424) / 0.424, 0.01)

    def test_gust_velocities_follow_far_25_341(self):
        self.assertEqual(self.vn["gust_velocities"]["vb-vc"], 66.0)
        self.assertEqual(self.vn["gust_velocities"]["vc"], 50.0)
        self.assertEqual(self.vn["gust_velocities"]["vd"], 25.0)

    def test_commuter_category_raises_the_corner(self):
        vn = gl.vn_diagram(ws=WS, vs=230.0, vd=800.0, a=A, cbar=CBAR,
                           category="commuter")
        self.assertEqual(vn["n_positive"], 3.8)
        self.assertAlmostEqual(vn["va"], 230.0 * math.sqrt(3.8), places=2)

    def test_altitude_reduces_design_gust_velocity(self):
        vn = gl.vn_diagram(ws=WS, vs=230.0, vd=621.0, a=A, cbar=CBAR,
                           altitude_ft=15000.0)
        self.assertEqual(vn["gust_velocities"]["vb-vc"], 38.0)
        self.assertEqual(vn["gust_velocities"]["vc"], 25.0)

    def test_invalid_category_raises_value_error(self):
        with self.assertRaises(ValueError):
            gl.vn_diagram(ws=WS, vs=230.0, vd=621.0, a=A, cbar=CBAR,
                          category="bogus")

    def test_speed_ordering_violation_raises_value_error(self):
        with self.assertRaises(ValueError):
            gl.vn_diagram(ws=WS, vs=230.0, vd=400.0, a=A, cbar=CBAR)


class EnvelopeVerdictTest(unittest.TestCase):
    def setUp(self):
        self.vn = gl.vn_diagram(ws=WS, vs=230.0, vd=621.0, a=A, cbar=CBAR)

    def test_point_inside_envelope_passes(self):
        # At v = 400 ft/s the positive limit is
        # 2.5 * (621 - 400) / (621 - 363.66) = 2.147, so n = 1.8 passes
        # with a positive margin.
        r = gl.envelope_verdict(self.vn, 400.0, 1.8)
        self.assertEqual(r["verdict"], "PASS")
        self.assertTrue(r["inside"])
        self.assertAlmostEqual(r["n_limit_pos"], 2.147, places=3)
        self.assertGreater(r["margin"], 0.0)

    def test_point_above_limit_fails(self):
        r = gl.envelope_verdict(self.vn, 400.0, 2.3)
        self.assertEqual(r["verdict"], "FAIL")
        self.assertFalse(r["inside"])
        self.assertLess(r["margin"], 0.0)

    def test_stall_boundary_limits_below_va(self):
        # Below VA the stall line n = (v/vs)^2 binds: at v = 300 ft/s
        # the limit is (300/230)^2 = 1.701.
        self.assertEqual(gl.envelope_verdict(self.vn, 300.0, 0.5)["verdict"],
                         "PASS")
        self.assertEqual(gl.envelope_verdict(self.vn, 300.0, 2.0)["verdict"],
                         "FAIL")
        self.assertAlmostEqual(
            gl.envelope_verdict(self.vn, 300.0, 0.5)["n_limit_pos"],
            (300.0 / 230.0) ** 2, places=3)

    def test_negative_side(self):
        self.assertEqual(gl.envelope_verdict(self.vn, 300.0, -0.8)["verdict"],
                         "PASS")
        self.assertEqual(gl.envelope_verdict(self.vn, 300.0, -1.5)["verdict"],
                         "FAIL")

    def test_speed_outside_envelope_fails(self):
        self.assertEqual(gl.envelope_verdict(self.vn, 100.0, 1.0)["verdict"],
                         "FAIL")
        self.assertEqual(gl.envelope_verdict(self.vn, 650.0, 0.5)["verdict"],
                         "FAIL")

    def test_invalid_inputs_raise_value_error(self):
        with self.assertRaises(ValueError):
            gl.envelope_verdict(self.vn, -5.0, 1.0)
        with self.assertRaises(ValueError):
            gl.envelope_verdict(None, 300.0, 1.0)
        with self.assertRaises(ValueError):
            gl.envelope_verdict(self.vn, 300.0, None)


class EnvelopeMarginsTest(unittest.TestCase):
    def setUp(self):
        self.vn = gl.vn_diagram(ws=WS, vs=230.0, vd=621.0, a=A, cbar=CBAR)
        self.margins = gl.envelope_margins(self.vn)

    def test_gust_critical_at_vb(self):
        # With the 66 fps design gust between VB and VC the gust line at
        # VB (n = 2.424) exceeds the maneuver envelope at VB
        # (2.5 * (621-414)/(621-363.66) = 2.011): the gust condition
        # drives the design near the corner.
        m = self.margins["VB"]
        self.assertLess(m["margin_pos"], 0.0)
        self.assertTrue(m["gust_critical_pos"])
        self.assertAlmostEqual(m["n_gust_pos"], 2.424, places=2)

    def test_negative_gust_stays_inside_envelope(self):
        # The -66 fps down gust at VB gives n = -0.424, above the -1.0
        # negative limit, so there is positive margin.
        m = self.margins["VB"]
        self.assertGreater(m["margin_neg"], 0.0)
        self.assertFalse(m["gust_critical_neg"])

    def test_gust_critical_at_vd(self):
        # At VD the maneuver envelope is zero, so any positive gust load
        # factor exceeds it.
        self.assertLess(self.margins["VD"]["margin_pos"], 0.0)
        self.assertTrue(self.margins["VD"]["gust_critical_pos"])

    def test_all_three_gust_speeds_reported(self):
        self.assertEqual(set(self.margins.keys()), {"VB", "VC", "VD"})

    def test_invalid_diagram_raises_value_error(self):
        with self.assertRaises(ValueError):
            gl.envelope_margins({"vs": 230.0})


class Far25GustVelocityTest(unittest.TestCase):
    def test_sea_level_values(self):
        self.assertEqual(gl.far25_gust_velocity("vb-vc"), 66.0)
        self.assertEqual(gl.far25_gust_velocity("vc"), 50.0)
        self.assertEqual(gl.far25_gust_velocity("vd"), 25.0)

    def test_altitude_floor_values(self):
        self.assertEqual(gl.far25_gust_velocity("vb-vc", 15000.0), 38.0)
        self.assertEqual(gl.far25_gust_velocity("vc", 15000.0), 25.0)
        self.assertEqual(gl.far25_gust_velocity("vd", 50000.0), 12.5)

    def test_linear_interpolation(self):
        # Halfway to the floor, halfway between the values.
        self.assertEqual(gl.far25_gust_velocity("vb-vc", 7500.0), 52.0)
        self.assertEqual(gl.far25_gust_velocity("vd", 25000.0), 18.75)

    def test_above_floor_uses_floor_value(self):
        self.assertEqual(gl.far25_gust_velocity("vc", 40000.0), 25.0)

    def test_invalid_region_raises_value_error(self):
        with self.assertRaises(ValueError):
            gl.far25_gust_velocity("vd-vc")


if __name__ == "__main__":
    unittest.main()
