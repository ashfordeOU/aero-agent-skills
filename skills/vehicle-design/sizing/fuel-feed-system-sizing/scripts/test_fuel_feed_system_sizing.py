#!/usr/bin/env python3
"""Gate 3 contract test: aircraft fuel feed system sizing.

Exercises scripts/fuel_feed_system_sizing_logic.py (stdlib unittest,
offline, deterministic). Contract: per-engine feed flow through the
feed line velocity and Reynolds number, Darcy friction factor (laminar
64/Re or turbulent Blasius), major and minor line pressure loss, static
head gain, NPSH available at the engine-driven pump inlet against the
required NPSH with the boost pump rise added, and boost pump hydraulic
power; non-physical inputs raise ValueError.

Analytic anchors (reference line, 0.45 kg/s, Jet A 800 kg/m3, D 0.05 m,
L 12 m, mu 2.4e-3 Pa s, K 3.0, tank 1.5 m above pump, vent 24.3 kPa,
vapor 1.0 kPa, required NPSH 3.0 m, boost 15 psi at 0.60 efficiency):
  velocity 0.45 / (800 * pi * 0.05^2 / 4) = 0.2865 m/s
  Re = 4775 (turbulent); f = 0.3164 Re^-0.25 = 0.0381
  major loss 299.9 Pa, minor 98.5 Pa, total 398.4 Pa
  static head 800 * 9.80665 * 1.5 = 11768.0 Pa
  NPSHa = (24300 + 11768 - 398.4 - 1000) / 7845.32 = 4.42 m -> PASS,
    margin 1.42 m; with 103421 Pa boost 17.60 m, margin 14.60 m
  boost power 5.625e-4 * 103421 / 0.60 = 96.96 W
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fuel_feed_system_sizing_logic import (
    BLASIUS_COEFF,
    GRAVITY,
    K_LAMINAR,
    LAMINAR_RE_LIMIT,
    PSI_TO_PA,
    boost_pump_power,
    feed_system_summary,
    feed_verdict,
    friction_factor,
    line_velocity,
    major_loss_pa,
    minor_loss_pa,
    npsh_available,
    reynolds_number,
    static_head_pa,
)

M_DOT = 0.45
RHO = 800.0
D = 0.05
L = 12.0
MU = 2.4e-3
K = 3.0
H_TANK = 1.5
P_SRC = 24300.0
P_VAP = 1000.0
NPSH_REQ = 3.0
RISE = 15.0 * PSI_TO_PA
ETA = 0.60

VEL = line_velocity(M_DOT, RHO, D)
V = VEL["velocity_m_s"]
RE = reynolds_number(V, D, RHO, MU)
F = friction_factor(RE)
MAJOR = major_loss_pa(F, L, D, RHO, V)
MINOR = minor_loss_pa(K, RHO, V)
TOTAL = MAJOR + MINOR
STATIC = static_head_pa(RHO, H_TANK)
NPSH = npsh_available(P_SRC, STATIC, TOTAL, P_VAP, RHO)
NPSH_BOOST = npsh_available(P_SRC + RISE, STATIC, TOTAL, P_VAP, RHO)


class TestLineVelocity(unittest.TestCase):
    def test_worked_example(self):
        self.assertAlmostEqual(V, 0.2865, delta=1e-4)
        self.assertAlmostEqual(VEL["area_m2"], 0.0019635, places=6)
        self.assertAlmostEqual(VEL["area_m2"],
                               math.pi * D ** 2 / 4.0, places=12)

    def test_flow_scaling(self):
        double = line_velocity(2.0 * M_DOT, RHO, D)
        self.assertAlmostEqual(double["velocity_m_s"], 2.0 * V, places=12)

    def test_valueerror_non_positive(self):
        for bad in (0.0, -0.45):
            with self.assertRaises(ValueError):
                line_velocity(bad, RHO, D)
        with self.assertRaises(ValueError):
            line_velocity(M_DOT, 0.0, D)
        with self.assertRaises(ValueError):
            line_velocity(M_DOT, RHO, 0.0)
        with self.assertRaises(ValueError):
            line_velocity(M_DOT, RHO, -0.05)


class TestReynoldsNumber(unittest.TestCase):
    def test_worked_example(self):
        self.assertAlmostEqual(RE, 4775.0, delta=1.0)

    def test_proportional_scaling(self):
        self.assertAlmostEqual(reynolds_number(2.0 * V, D, RHO, MU),
                               2.0 * RE, places=9)
        self.assertAlmostEqual(reynolds_number(V, 2.0 * D, RHO, MU),
                               2.0 * RE, places=9)

    def test_valueerror(self):
        with self.assertRaises(ValueError):
            reynolds_number(-1.0, D, RHO, MU)
        with self.assertRaises(ValueError):
            reynolds_number(V, 0.0, RHO, MU)
        with self.assertRaises(ValueError):
            reynolds_number(V, D, 0.0, MU)
        with self.assertRaises(ValueError):
            reynolds_number(V, D, RHO, 0.0)


class TestFrictionFactor(unittest.TestCase):
    def test_laminar_exact(self):
        self.assertEqual(friction_factor(1000.0), K_LAMINAR / 1000.0)
        self.assertEqual(friction_factor(500.0), 64.0 / 500.0)

    def test_blasius_worked_bound(self):
        self.assertAlmostEqual(friction_factor(4775.0), 0.0381, delta=1e-4)
        self.assertAlmostEqual(F, 0.0381, delta=1e-4)
        self.assertAlmostEqual(friction_factor(RE),
                               BLASIUS_COEFF * RE ** -0.25, places=12)

    def test_transition_branch(self):
        laminar_edge = LAMINAR_RE_LIMIT - 1e-9
        self.assertEqual(friction_factor(laminar_edge),
                         K_LAMINAR / laminar_edge)
        turbulent_edge = friction_factor(LAMINAR_RE_LIMIT)
        self.assertAlmostEqual(turbulent_edge,
                               BLASIUS_COEFF * LAMINAR_RE_LIMIT ** -0.25,
                               places=12)
        self.assertNotAlmostEqual(
            turbulent_edge, K_LAMINAR / LAMINAR_RE_LIMIT, places=3)

    def test_valueerror(self):
        with self.assertRaises(ValueError):
            friction_factor(0.0)
        with self.assertRaises(ValueError):
            friction_factor(-100.0)


class TestMajorLoss(unittest.TestCase):
    def test_worked_example(self):
        self.assertAlmostEqual(MAJOR, 299.9, delta=1e-1)

    def test_scaling_identity(self):
        long_run = major_loss_pa(F, 2.0 * L, D, RHO, V)
        self.assertAlmostEqual(long_run / MAJOR, 2.0, places=9)
        fast_run = major_loss_pa(F, L, D, RHO, 2.0 * V)
        self.assertAlmostEqual(fast_run / MAJOR, 4.0, places=9)

    def test_valueerror(self):
        with self.assertRaises(ValueError):
            major_loss_pa(0.0, L, D, RHO, V)
        with self.assertRaises(ValueError):
            major_loss_pa(F, 0.0, D, RHO, V)
        with self.assertRaises(ValueError):
            major_loss_pa(F, L, 0.0, RHO, V)
        with self.assertRaises(ValueError):
            major_loss_pa(F, L, D, 0.0, V)
        with self.assertRaises(ValueError):
            major_loss_pa(F, L, D, RHO, 0.0)


class TestMinorLoss(unittest.TestCase):
    def test_worked_example(self):
        self.assertAlmostEqual(MINOR, 98.5, delta=5e-2)
        self.assertAlmostEqual(MINOR, 98.4841905, places=6)

    def test_zero_k_and_scaling(self):
        self.assertEqual(minor_loss_pa(0.0, RHO, V), 0.0)
        self.assertAlmostEqual(minor_loss_pa(K, RHO, 2.0 * V),
                               4.0 * MINOR, places=9)

    def test_valueerror(self):
        with self.assertRaises(ValueError):
            minor_loss_pa(-0.5, RHO, V)
        with self.assertRaises(ValueError):
            minor_loss_pa(K, 0.0, V)
        with self.assertRaises(ValueError):
            minor_loss_pa(K, RHO, -1.0)


class TestStaticHead(unittest.TestCase):
    def test_worked_example(self):
        self.assertAlmostEqual(STATIC, 11768.0, delta=5e-2)
        self.assertEqual(STATIC, RHO * GRAVITY * H_TANK)

    def test_sign_and_npsh_reduction(self):
        negative = static_head_pa(RHO, -1.0)
        self.assertEqual(negative, -RHO * GRAVITY)
        low_npsh = npsh_available(P_SRC, negative, TOTAL, P_VAP, RHO)
        self.assertLess(low_npsh, NPSH)
        self.assertAlmostEqual(NPSH - low_npsh, 2.5, places=9)

    def test_valueerror(self):
        with self.assertRaises(ValueError):
            static_head_pa(0.0, 1.5)


class TestNpshAvailable(unittest.TestCase):
    def test_worked_example(self):
        self.assertAlmostEqual(NPSH, 4.42, delta=1e-2)

    def test_boost_worked_example(self):
        self.assertAlmostEqual(NPSH_BOOST, 17.60, delta=1e-2)
        self.assertAlmostEqual(NPSH_BOOST - NPSH_REQ, 14.60, delta=1e-2)

    def test_signed_negative_value(self):
        starved = npsh_available(10000.0, 0.0, 30000.0, 0.0, RHO)
        self.assertLess(starved, 0.0)
        self.assertEqual(feed_verdict(starved, NPSH_REQ)["verdict"], "FAIL")

    def test_valueerror(self):
        with self.assertRaises(ValueError):
            npsh_available(-1.0, STATIC, TOTAL, P_VAP, RHO)
        with self.assertRaises(ValueError):
            npsh_available(P_SRC, STATIC, -1.0, P_VAP, RHO)
        with self.assertRaises(ValueError):
            npsh_available(P_SRC, STATIC, TOTAL, -1.0, RHO)
        with self.assertRaises(ValueError):
            npsh_available(P_SRC, STATIC, TOTAL, P_VAP, 0.0)


class TestFeedVerdict(unittest.TestCase):
    def test_pass_case(self):
        result = feed_verdict(NPSH, NPSH_REQ)
        self.assertEqual(result["verdict"], "PASS")
        self.assertAlmostEqual(result["margin_m"], 1.42, delta=1e-2)

    def test_fail_case(self):
        result = feed_verdict(NPSH, 5.0)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertAlmostEqual(result["margin_m"], -0.58, delta=1e-2)

    def test_boundary_and_valueerror(self):
        boundary = feed_verdict(3.0, 3.0)
        self.assertEqual(boundary["verdict"], "PASS")
        self.assertEqual(boundary["margin_m"], 0.0)
        with self.assertRaises(ValueError):
            feed_verdict(NPSH, -1.0)


class TestBoostPumpPower(unittest.TestCase):
    def test_worked_example(self):
        flow = M_DOT / RHO
        result = boost_pump_power(flow, RISE, ETA)
        self.assertAlmostEqual(result["power_w"], 96.96, delta=1e-1)
        self.assertEqual(result["pressure_rise_pa"], RISE)

    def test_efficiency_identity(self):
        flow = M_DOT / RHO
        ideal = boost_pump_power(flow, RISE, 1.0)
        self.assertEqual(ideal["power_w"], flow * RISE)
        half = boost_pump_power(flow, RISE, 0.5)
        self.assertAlmostEqual(half["power_w"], 2.0 * ideal["power_w"],
                               places=9)

    def test_valueerror(self):
        with self.assertRaises(ValueError):
            boost_pump_power(0.0, RISE, ETA)
        with self.assertRaises(ValueError):
            boost_pump_power(M_DOT / RHO, 0.0, ETA)
        with self.assertRaises(ValueError):
            boost_pump_power(M_DOT / RHO, RISE, 0.0)
        with self.assertRaises(ValueError):
            boost_pump_power(M_DOT / RHO, RISE, 1.1)


class TestFeedSystemSummary(unittest.TestCase):
    DOC_KEYS = [
        "velocity_m_s", "area_m2", "reynolds", "friction_factor",
        "major_loss_pa", "minor_loss_pa", "total_line_loss_pa",
        "static_head_pa", "npsh_available_m", "npsh_required_m",
        "margin_m", "verdict", "npsh_with_boost_m",
        "boost_pressure_rise_pa", "boost_power_w",
    ]

    def _summary(self):
        return feed_system_summary(M_DOT, RHO, D, L, MU, K, H_TANK,
                                   P_SRC, P_VAP, NPSH_REQ, RISE, ETA)

    def test_worked_example_values(self):
        s = self._summary()
        self.assertAlmostEqual(s["velocity_m_s"], 0.2865, delta=1e-4)
        self.assertAlmostEqual(s["reynolds"], 4775.0, delta=1.0)
        self.assertAlmostEqual(s["friction_factor"], 0.0381, delta=1e-4)
        self.assertAlmostEqual(s["total_line_loss_pa"], 398.4, delta=1e-1)
        self.assertAlmostEqual(s["static_head_pa"], 11768.0, delta=5e-2)
        self.assertAlmostEqual(s["total_line_loss_pa"],
                               s["major_loss_pa"] + s["minor_loss_pa"],
                               places=9)
        self.assertAlmostEqual(s["npsh_available_m"], 4.42, delta=1e-2)
        self.assertEqual(s["verdict"], "PASS")
        self.assertAlmostEqual(s["margin_m"], 1.42, delta=1e-2)
        self.assertAlmostEqual(s["npsh_with_boost_m"], 17.60, delta=1e-2)
        self.assertAlmostEqual(s["boost_power_w"], 96.96, delta=1e-1)

    def test_keys_exactly_as_documented(self):
        self.assertEqual(sorted(self._summary().keys()),
                         sorted(self.DOC_KEYS))

    def test_boost_rise_edge_cases(self):
        s = feed_system_summary(M_DOT, RHO, D, L, MU, K, H_TANK,
                                P_SRC, P_VAP, NPSH_REQ, 0.0, ETA)
        self.assertEqual(s["npsh_with_boost_m"], s["npsh_available_m"])
        self.assertEqual(s["boost_power_w"], 0.0)
        with self.assertRaises(ValueError):
            feed_system_summary(M_DOT, RHO, D, L, MU, K, H_TANK,
                                P_SRC, P_VAP, NPSH_REQ, -1000.0, ETA)

    def test_determinism(self):
        self.assertEqual(self._summary(), self._summary())
        self.assertEqual(line_velocity(M_DOT, RHO, D),
                         line_velocity(M_DOT, RHO, D))

    def test_laminar_chain_identity(self):
        low_flow = feed_system_summary(0.02, RHO, D, L, MU, K, H_TANK,
                                       P_SRC, P_VAP, NPSH_REQ, RISE, ETA)
        self.assertLess(low_flow["reynolds"], LAMINAR_RE_LIMIT)
        self.assertAlmostEqual(
            low_flow["friction_factor"], K_LAMINAR / low_flow["reynolds"],
            places=12)


class TestConstants(unittest.TestCase):
    def test_psi_conversion(self):
        self.assertEqual(PSI_TO_PA * 15.0, 103421.355)


if __name__ == "__main__":
    unittest.main()
