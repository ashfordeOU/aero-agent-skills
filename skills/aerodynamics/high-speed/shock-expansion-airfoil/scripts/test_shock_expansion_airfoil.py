"""Contract test for the shock-expansion-airfoil leaf logic.

Deterministic, offline, stdlib-only.  Run: python3 test_shock_expansion_airfoil.py

Anchors (exact module values, gamma = 1.4):
- eps = 5 deg, M1 = 2.0, alpha = 3 deg: cl = 0.1227, cd_wave = 0.0243,
  cm_le = 0.0552.  The thin diamond tracks linear supersonic theory,
  cl = 4*alpha/sqrt(M1**2 - 1) = 0.1209, within 1.5% (asserted within
  10% as the primary identity).  The higher cl 0.3-0.5 textbook cases
  correspond to larger Mach numbers and half-angles on this geometry.
- Flat plate: eps = 0.1 deg, M1 = 2.0, alpha = 3 deg gives cl = 0.1210,
  within 5% of 4*alpha/sqrt(M1**2 - 1) = 0.1209.
- Symmetry: alpha = 0 on the symmetric diamond gives cl ~ 0 and
  cd_wave > 0 (cd_wave = 0.0177 at eps = 5 deg).
- Mach trend: cd_wave falls monotonically from 0.0386 at M1 = 1.5 to
  0.0150 at M1 = 3.0 (fixed eps = 5 deg, alpha = 3 deg).
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shock_expansion_airfoil_logic as sea

GAMMA = 1.4
ANCHOR_CL = 0.1227
ANCHOR_CD = 0.0243
ANCHOR_CM = 0.0552


class TestThetaBetaM(unittest.TestCase):
    def test_known_chart_value_m2_theta8(self):
        beta = sea.theta_beta_m(2.0, 8.0)
        self.assertAlmostEqual(beta, 37.21, delta=0.02)  # NACA chart value

    def test_zero_deflection_tends_to_mach_angle(self):
        beta = sea.theta_beta_m(2.0, 1e-6)
        self.assertAlmostEqual(beta, math.degrees(math.asin(0.5)), delta=1e-3)

    def test_above_max_deflection_raises(self):
        with self.assertRaises(ValueError):
            sea.theta_beta_m(2.0, 23.0)  # theta_max = 22.97 deg at M1 = 2
        with self.assertRaises(ValueError):
            sea.theta_beta_m(2.0, 45.0)

    def test_subsonic_and_bad_inputs_raise(self):
        for bad in (1.0, 0.9, -2.0):
            with self.assertRaises(ValueError):
                sea.theta_beta_m(bad, 5.0)
        with self.assertRaises(ValueError):
            sea.theta_beta_m(2.0, -1.0)
        with self.assertRaises(ValueError):
            sea.theta_beta_m(float("nan"), 5.0)

    def test_weak_solution_is_lower_beta_branch(self):
        # Weak branch beta must stay below the strong-branch range:
        # beta(2.0, 8 deg) ~ 37.2 deg, well below 90 deg.
        self.assertLess(sea.theta_beta_m(2.0, 8.0), 60.0)
        self.assertGreater(sea.theta_beta_m(2.0, 8.0), 30.0)


class TestObliqueShockRatios(unittest.TestCase):
    def test_known_ratios_m2_theta8(self):
        m2, p2_p1 = sea.oblique_shock_ratios(2.0, 8.0)
        self.assertAlmostEqual(p2_p1, 1.53998, delta=1e-3)  # 1.54 tables
        self.assertAlmostEqual(m2, 1.7137, delta=1e-3)

    def test_pressure_rises_with_deflection(self):
        _, p_small = sea.oblique_shock_ratios(2.0, 2.0)
        _, p_big = sea.oblique_shock_ratios(2.0, 8.0)
        self.assertGreater(p_big, p_small)
        self.assertGreater(p_small, 1.0)

    def test_mach_number_falls_across_shock(self):
        m2, _ = sea.oblique_shock_ratios(2.0, 8.0)
        self.assertLess(m2, 2.0)
        self.assertGreater(m2, 1.0)


class TestPrandtlMeyer(unittest.TestCase):
    def test_known_angle_m2(self):
        nu = sea.prandtl_meyer_angle(2.0)
        self.assertAlmostEqual(nu, 26.3798, delta=1e-3)

    def test_angle_zero_at_mach_one(self):
        self.assertAlmostEqual(sea.prandtl_meyer_angle(1.0), 0.0, delta=1e-9)

    def test_known_turn_m2_ten_deg(self):
        m2, p2_p1 = sea.prandtl_meyer_turn(2.0, 10.0)
        self.assertAlmostEqual(m2, 2.3849, delta=1e-3)  # Anderson 2.38
        self.assertAlmostEqual(p2_p1, 0.54797, delta=1e-3)

    def test_expansion_drops_pressure_raises_mach(self):
        m2, p2_p1 = sea.prandtl_meyer_turn(2.0, 5.0)
        self.assertGreater(m2, 2.0)
        self.assertLess(p2_p1, 1.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            sea.prandtl_meyer_angle(0.5)
        with self.assertRaises(ValueError):
            sea.prandtl_meyer_turn(2.0, -3.0)
        with self.assertRaises(ValueError):
            sea.prandtl_meyer_turn(2.0, 400.0)  # beyond the limiting angle


class TestSurfacePressures(unittest.TestCase):
    def test_dict_structure(self):
        s = sea.surface_pressures(2.0, 3.0, 5.0)
        self.assertEqual(set(s.keys()), {"uf", "ur", "lf", "lr"})
        for key in s:
            for field in ("cp", "m", "p_pinf", "theta_deg"):
                self.assertIn(field, s[key])

    def test_front_sign_logic_alpha_three(self):
        # theta_uf = eps - alpha = +2 deg (weak shock), theta_lf = 8 deg
        # (shock): lower front pressure above the upper front pressure.
        s = sea.surface_pressures(2.0, 3.0, 5.0)
        self.assertGreater(s["lf"]["p_pinf"], s["uf"]["p_pinf"])
        self.assertGreater(s["uf"]["p_pinf"], 1.0)
        self.assertAlmostEqual(s["uf"]["theta_deg"], 2.0)
        self.assertAlmostEqual(s["lf"]["theta_deg"], 8.0)

    def test_upper_front_expands_when_alpha_above_eps(self):
        s = sea.surface_pressures(2.0, 8.0, 5.0)
        self.assertLess(s["uf"]["p_pinf"], 1.0)  # expansion fan, p drops
        self.assertLess(s["uf"]["cp"], 0.0)

    def test_rear_surfaces_always_expand(self):
        for alpha in (-3.0, 0.0, 3.0, 6.0):
            s = sea.surface_pressures(2.0, alpha, 5.0)
            self.assertLess(s["ur"]["p_pinf"], s["uf"]["p_pinf"])
            self.assertLess(s["lr"]["p_pinf"], s["lf"]["p_pinf"])


class TestShockExpansionAirfoil(unittest.TestCase):
    def test_worked_example_exact_values(self):
        # eps = 5 deg, M1 = 2.0, alpha = 3 deg, gamma = 1.4.
        # Exact: cl = 0.1227, cd_wave = 0.0243, cm_le = 0.0552 (nose-up).
        # Primary identity: the thin diamond must track linear supersonic
        # theory, cl = 4*alpha/sqrt(M^2-1) = 0.1209; the exact value sits
        # 1.5% above it (ratio 1.0149), well inside the 10% band.
        r = sea.shock_expansion_airfoil(2.0, 3.0, 5.0)
        self.assertAlmostEqual(r["cl"], ANCHOR_CL, delta=2e-3)
        self.assertAlmostEqual(r["cd_wave"], ANCHOR_CD, delta=2e-3)
        self.assertAlmostEqual(r["cm_le"], ANCHOR_CM, delta=2e-3)
        linear = 4.0 * math.radians(3.0) / math.sqrt(2.0 ** 2 - 1.0)
        self.assertAlmostEqual(r["cl"], linear, delta=0.10 * linear)
        self.assertGreater(r["cl"], 0.0)
        self.assertGreater(r["cd_wave"], 0.0)

    def test_flat_plate_linear_limit(self):
        # eps = 0.1 deg, M = 2, alpha = 3 deg: cl = 0.1210 against the
        # linear supersonic value 4*alpha/sqrt(M^2-1) = 0.1209 (< 5%).
        linear = 4.0 * math.radians(3.0) / math.sqrt(2.0 ** 2 - 1.0)
        r = sea.shock_expansion_airfoil(2.0, 3.0, 0.1)
        self.assertAlmostEqual(r["cl"], linear, delta=0.05 * linear)
        self.assertAlmostEqual(r["cl"], 0.1210, delta=2e-3)

    def test_alpha_zero_symmetric_diamond(self):
        r = sea.shock_expansion_airfoil(2.0, 0.0, 5.0)
        self.assertLess(abs(r["cl"]), 1e-9)
        self.assertLess(abs(r["cm_le"]), 1e-9)
        self.assertGreater(r["cd_wave"], 0.0)
        self.assertAlmostEqual(r["cd_wave"], 0.0177, delta=2e-3)

    def test_negative_alpha_mirrors_lift(self):
        rp = sea.shock_expansion_airfoil(2.0, 3.0, 5.0)
        rn = sea.shock_expansion_airfoil(2.0, -3.0, 5.0)
        self.assertAlmostEqual(rn["cl"], -rp["cl"], delta=1e-9)
        self.assertAlmostEqual(rn["cd_wave"], rp["cd_wave"], delta=1e-9)

    def test_mach_trend_wave_drag_falls(self):
        cds = [sea.shock_expansion_airfoil(m, 3.0, 5.0)["cd_wave"]
               for m in (1.5, 2.0, 2.5, 3.0)]
        self.assertAlmostEqual(cds[0], 0.0386, delta=2e-3)
        self.assertAlmostEqual(cds[-1], 0.0150, delta=2e-3)
        for hi, lo in zip(cds, cds[1:]):
            self.assertGreater(hi, lo)
        cls = [sea.shock_expansion_airfoil(m, 3.0, 5.0)["cl"]
               for m in (1.5, 2.0, 2.5, 3.0)]
        for hi, lo in zip(cls, cls[1:]):
            self.assertGreater(hi, lo)

    def test_zero_thickness_zero_alpha_identity(self):
        # eps = 0 and alpha = 0: every panel sees freestream conditions.
        r = sea.shock_expansion_airfoil(2.0, 0.0, 0.0)
        for cp in r["surface_cp"].values():
            self.assertAlmostEqual(cp, 0.0, delta=1e-12)
        self.assertAlmostEqual(r["cl"], 0.0, delta=1e-12)
        self.assertAlmostEqual(r["cd_wave"], 0.0, delta=1e-12)

    def test_m1_at_one_raises(self):
        with self.assertRaises(ValueError):
            sea.shock_expansion_airfoil(1.0, 3.0, 5.0)
        with self.assertRaises(ValueError):
            sea.shock_expansion_airfoil(1.0 + 1e-10, 3.0, 5.0)

    def test_angle_ranges_raise(self):
        for alpha in (-90.0, 90.0, 120.0):
            with self.assertRaises(ValueError):
                sea.shock_expansion_airfoil(2.0, alpha, 5.0)
        for eps in (-1.0, 45.0, 60.0):
            with self.assertRaises(ValueError):
                sea.shock_expansion_airfoil(2.0, 3.0, eps)

    def test_high_alpha_detached_shock_raises(self):
        # theta_lf = eps + alpha = 23 deg > theta_max = 22.97 at M1 = 2.
        with self.assertRaises(ValueError):
            sea.shock_expansion_airfoil(2.0, 18.0, 5.0)

    def test_nonfinite_inputs_raise(self):
        with self.assertRaises(ValueError):
            sea.shock_expansion_airfoil(float("inf"), 3.0, 5.0)
        with self.assertRaises(ValueError):
            sea.shock_expansion_airfoil(2.0, float("nan"), 5.0)
        with self.assertRaises(ValueError):
            sea.shock_expansion_airfoil(2.0, 3.0, float("inf"))


if __name__ == "__main__":
    unittest.main()
