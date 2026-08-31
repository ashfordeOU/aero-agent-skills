#!/usr/bin/env python3
"""Gate 3 contract test: oblique shock relations.

Exercises scripts/oblique_shock_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the theta-beta-M relation
theta(beta) at fixed M1, the weak/strong wave angles for a deflection
below the maximum, the maximum attached-shock deflection theta_max
(apex of the shock polar), and the downstream state (Mach number and
static ratios) on either branch; deflections above theta_max raise
ValueError (detached shock).

Analytic checks (hand-computed, gamma = 1.4):
- Mach angle: mu(2.0) = asin(0.5) = 30.0 deg exactly.
- theta-beta-M round trip at M1 = 2.0, theta = 10 deg (Anderson,
  Modern Compressible Flow, Example 4.2): weak beta = 39.3139 deg,
  strong beta = 83.7001 deg; both re-substitute to theta = 10 deg.
- Weak branch (physically realized): M2 = 1.6405 (supersonic),
  p2/p1 = 1.7066, p02/p01 = 0.9846 (far less total pressure loss than
  the 0.720875 of the normal shock at M1 = 2).
- Strong branch: M2 = 0.6037 (subsonic), p2/p1 = 4.4438, above the
  weak branch's pressure ratio.
- Limits at theta = 0: weak -> beta = mu with p2/p1 = 1 and M2 = M1
  (Mach wave, isentropic); strong -> beta = 90 deg with p2/p1 = 4.5
  and M2 = 0.5773503, the normal shock values at M1 = 2.
- Deflection limit: theta_max(2.0) = 22.9735 deg (weak and strong
  branches merge there), growing to 45.5730 deg at M1 = 100 (the
  gamma = 1.4 asymptotic limit is about 45.6 deg).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import oblique_shock_logic as osl  # noqa: E402


class MachAngleTest(unittest.TestCase):
    def test_mach_angle_at_m2(self):
        # mu = asin(1/M1): at M1 = 2.0 exactly 30.0 deg.
        self.assertAlmostEqual(osl.mach_angle(2.0), 30.0, places=6)

    def test_mach_angle_falls_with_mach(self):
        # A higher Mach number narrows the Mach cone.
        self.assertLess(osl.mach_angle(3.0), osl.mach_angle(2.0))

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            osl.mach_angle(1.0)
        with self.assertRaises(ValueError):
            osl.mach_angle(0.8)


class ThetaBetaMTest(unittest.TestCase):
    def test_weak_branch_round_trip(self):
        # theta(39.3139 deg) = 10 deg at M1 = 2: the weak wave angle
        # re-substitutes into the relation (Anderson Example 4.2).
        self.assertAlmostEqual(
            osl.theta_beta_m(2.0, 39.3139), 10.0, places=3
        )

    def test_strong_branch_round_trip(self):
        # theta(83.7001 deg) = 10 deg at M1 = 2: the strong wave angle
        # satisfies the same relation on the far side of theta_max.
        self.assertAlmostEqual(
            osl.theta_beta_m(2.0, 83.7001), 10.0, places=3
        )

    def test_zero_deflection_limits(self):
        # theta = 0 at both ends of the beta domain: the Mach angle mu
        # (weak) and 90 deg (normal shock).
        self.assertAlmostEqual(osl.theta_beta_m(2.0, 30.0), 0.0, places=6)
        self.assertAlmostEqual(osl.theta_beta_m(2.0, 90.0), 0.0, places=6)

    def test_single_interior_maximum(self):
        # theta rises from 0 at mu to theta_max, then falls to 0 at
        # 90 deg: the apex separates the weak and strong branches.
        vals = [osl.theta_beta_m(2.0, b) for b in (31.0, 40.0, 64.7, 80.0, 89.0)]
        self.assertEqual(vals.index(max(vals)), 2)

    def test_invalid_beta_raises(self):
        # beta at or below the Mach angle has no shock; above 90 deg is
        # meaningless.
        with self.assertRaises(ValueError):
            osl.theta_beta_m(2.0, 30.0 - 1e-9)
        with self.assertRaises(ValueError):
            osl.theta_beta_m(2.0, 10.0)
        with self.assertRaises(ValueError):
            osl.theta_beta_m(2.0, 90.5)
        with self.assertRaises(ValueError):
            osl.theta_beta_m(0.9, 40.0)
        with self.assertRaises(ValueError):
            osl.theta_beta_m(2.0, 40.0, 1.0)


class DeflectionLimitTest(unittest.TestCase):
    def test_limit_at_m2(self):
        # theta_max(2.0) = 22.9735 deg: above it the shock detaches.
        self.assertAlmostEqual(osl.deflection_limit(2.0), 22.9735, places=3)

    def test_limit_grows_toward_asymptote(self):
        # theta_max approaches about 45.6 deg (gamma = 1.4) as M1 grows.
        self.assertGreater(osl.deflection_limit(10.0), osl.deflection_limit(3.0))
        self.assertAlmostEqual(osl.deflection_limit(100.0), 45.573, places=3)

    def test_limit_tiny_just_above_mach_one(self):
        # Just above Mach 1 only a vanishing deflection keeps the shock
        # attached.
        self.assertAlmostEqual(osl.deflection_limit(1.01), 0.0516, places=3)

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            osl.deflection_limit(1.0)


class ShockAnglesTest(unittest.TestCase):
    def test_weak_and_strong_angles(self):
        # M1 = 2.0, theta = 10 deg (Anderson Example 4.2): weak 39.3139,
        # strong 83.7001.
        weak, strong = osl.shock_angles(2.0, 10.0)
        self.assertAlmostEqual(weak, 39.3139, places=3)
        self.assertAlmostEqual(strong, 83.7001, places=3)

    def test_zero_deflection_limits(self):
        # theta = 0 degenerates to the Mach wave and the normal shock.
        weak, strong = osl.shock_angles(2.0, 0.0)
        self.assertAlmostEqual(weak, 30.0, places=6)
        self.assertEqual(strong, 90.0)

    def test_weak_rises_with_deflection(self):
        # The weak wave angle grows monotonically with the deflection.
        prev = 0.0
        for th in (2.0, 5.0, 10.0, 20.0):
            weak, _ = osl.shock_angles(2.0, th)
            self.assertGreater(weak, prev)
            prev = weak

    def test_branches_merge_at_limit(self):
        # At theta_max the weak and strong solutions coincide: the apex
        # of the shock polar. The two bisections bracket the apex, so
        # agreement is to 1e-5, not to the last digit.
        tmax = osl.deflection_limit(2.0)
        weak, strong = osl.shock_angles(2.0, tmax)
        self.assertAlmostEqual(weak, strong, delta=1e-5)

    def test_detached_shock_raises(self):
        # theta = 25 deg exceeds theta_max(2.0) = 22.97 deg: no attached
        # oblique shock exists.
        with self.assertRaises(ValueError):
            osl.shock_angles(2.0, 25.0)
        with self.assertRaises(ValueError):
            osl.shock_angles(2.0, -1.0)


class ShockPropertiesTest(unittest.TestCase):
    def test_weak_downstream_state(self):
        # Weak branch at M1 = 2.0, theta = 10 deg: flow stays
        # supersonic, modest pressure rise, small total pressure loss.
        props = osl.shock_properties(2.0, 10.0)
        self.assertAlmostEqual(props["m2"], 1.6405, places=3)
        self.assertAlmostEqual(props["beta_deg"], 39.3139, places=3)
        self.assertAlmostEqual(props["p2_p1"], 1.7066, places=3)
        self.assertAlmostEqual(props["rho2_rho1"], 1.4584, places=3)
        self.assertAlmostEqual(props["t2_t1"], 1.1702, places=3)
        self.assertAlmostEqual(props["p02_p01"], 0.9846, places=3)
        self.assertFalse(props["strong"])

    def test_strong_downstream_state(self):
        # Strong branch: subsonic downstream flow and a higher pressure
        # ratio than the weak branch at the same deflection.
        props = osl.shock_properties(2.0, 10.0, strong=True)
        self.assertAlmostEqual(props["m2"], 0.6037, places=3)
        self.assertAlmostEqual(props["beta_deg"], 83.7001, places=3)
        self.assertAlmostEqual(props["p2_p1"], 4.4438, places=3)
        self.assertTrue(props["strong"])

    def test_strong_losses_more_total_pressure(self):
        # The strong branch loses far more stagnation pressure than the
        # weak branch; both stay below 1 (shock compression is
        # irreversible).
        weak = osl.shock_properties(2.0, 10.0)
        strong = osl.shock_properties(2.0, 10.0, strong=True)
        self.assertLess(strong["p02_p01"], weak["p02_p01"])
        self.assertLess(strong["p02_p01"], 1.0)
        self.assertLess(weak["p02_p01"], 1.0)

    def test_weak_total_pressure_loss_far_below_normal_shock(self):
        # Oblique shocks are much gentler than the normal shock: at
        # M1 = 2 the normal shock p02/p01 is 0.720875, the weak oblique
        # shock at theta = 10 deg keeps 0.9846.
        props = osl.shock_properties(2.0, 10.0)
        self.assertGreater(props["p02_p01"], 0.720875)

    def test_zero_deflection_matches_normal_shock(self):
        # Strong branch at theta = 0 is the normal shock at M1 = 2:
        # p2/p1 = 4.5, M2 = 0.5773503 (Anderson Table A.2 anchor).
        props = osl.shock_properties(2.0, 0.0, strong=True)
        self.assertAlmostEqual(props["p2_p1"], 4.5, places=6)
        self.assertAlmostEqual(props["m2"], 0.5773503, places=6)
        self.assertAlmostEqual(props["beta_deg"], 90.0, places=6)

    def test_zero_deflection_weak_is_mach_wave(self):
        # Weak branch at theta = 0 changes nothing: p2/p1 = 1, M2 = M1.
        props = osl.shock_properties(2.0, 0.0)
        self.assertAlmostEqual(props["p2_p1"], 1.0, places=6)
        self.assertAlmostEqual(props["m2"], 2.0, places=6)
        self.assertAlmostEqual(props["beta_deg"], 30.0, places=6)

    def test_temperature_ratio_from_ideal_gas(self):
        # T2/T1 = (p2/p1) / (rho2/rho1): the ideal-gas relation.
        props = osl.shock_properties(2.0, 10.0)
        self.assertAlmostEqual(
            props["t2_t1"], props["p2_p1"] / props["rho2_rho1"], places=9
        )

    def test_invalid_input_raises(self):
        with self.assertRaises(ValueError):
            osl.shock_properties(2.0, 25.0)
        with self.assertRaises(ValueError):
            osl.shock_properties(2.0, 10.0, 1.0)
        with self.assertRaises(ValueError):
            osl.shock_properties(0.9, 10.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
