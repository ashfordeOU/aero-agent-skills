#!/usr/bin/env python3
"""Gate 3 contract test: impact-angle-control guidance law.

Exercises scripts/impact_angle_control_guidance_logic.py (pure stdlib
unittest, offline, deterministic). Follows the SKILL.md Workflow steps:
step 1 (fix the engagement state), step 2 (compute the crossrange
velocity via crossrange_velocity), step 3 (estimate the time-to-go via
tgo_estimate), step 4 (form the impact-angle error via
impact_angle_error), step 5 (compute the impact-angle-error-feedback
bias via impact_angle_bias), step 6 (compute the collision-course
nulling baseline via collision_nulling_baseline), step 7 (sum the
baseline and the bias via impact_angle_guidance_command), and step 8
(confirm the deterministic checks). The SKILL.md Verification checks
exercised here are the linear-model closed-loop convergence to the
terminal crossrange velocity and the nonlinear planar engagement
identity probe against the stationary target at the worked-example
state.

Worked example (stationary target at the origin, interceptor at range
10000.0 m on a -30 deg line of sight, V = 300.0 m/s, gamma_0 = -30 deg,
commanded terminal flight path angle gamma_f = -60 deg, crossrange
offset y_0 = +5000.0 m): t_go0 = 33.333333333333 s, v0 =
-150.000000000000 m/s, v_f = -259.807621135332 m/s, e_g0 =
-0.523598775598 rad, a_base0 = 0.0 (collision course), a_bias0 =
6.588457268120 m/s^2, a_cmd0 = 6.588457268120 m/s^2. No exact float
equality is asserted on any computed sum; all numeric checks use
math.isclose or assertAlmostEqual with explicit tolerances.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import impact_angle_control_guidance_logic as iacg  # noqa: E402

V_MPS = 300.0
GAMMA0_RAD = math.radians(-30.0)
GAMMA_F_RAD = math.radians(-60.0)
RANGE_M = 10000.0
Y0_M = 5000.0
TGO0_S = RANGE_M / V_MPS

# REAL anchor outputs of the spec engagement simulation (prep anchor run).
V0_REF = -150.000000000000
VF_REF = -259.807621135332
TGO_REF = 33.333333333333
EG_REF_RAD = -0.523598775598
EG_REF_DEG = -30.000000000000
ABIAS_REF = 6.588457268120
ACMD_REF = 6.588457268120
ABIAS_DOUBLE_REF = 13.176914536240
ABIAS_SHALLOW_REF = -12.462790070115
LINEAR_Y_END_REF = 0.086606202
LINEAR_V_END_REF = -259.823007259
PLANAR_T_REF = 33.885000
PLANAR_MISS_REF = 0.096219
PLANAR_GAMMA_END_REF = -60.037102


class WorkedExampleTest(unittest.TestCase):
    """Steps 2-7 of the SKILL.md workflow at the worked-example
    engagement state: the real anchor outputs of the spec run."""

    def test_time_to_go_estimate(self):
        # Step 3: t_go = range / closing speed on the closing geometry.
        tgo = iacg.tgo_estimate(V_MPS, RANGE_M)
        self.assertTrue(math.isclose(tgo, TGO_REF, rel_tol=1e-9))

    def test_crossrange_velocities(self):
        # Step 2: v = speed * sin(gamma) for the current and the
        # commanded terminal flight path angle.
        v0 = iacg.crossrange_velocity(V_MPS, GAMMA0_RAD)
        vf = iacg.crossrange_velocity(V_MPS, GAMMA_F_RAD)
        self.assertTrue(math.isclose(v0, V0_REF, rel_tol=1e-9))
        self.assertTrue(math.isclose(vf, VF_REF, rel_tol=1e-9))

    def test_impact_angle_error_anchor(self):
        # Step 4: e_g = commanded_gamma - gamma, in radians and degrees.
        eg = iacg.impact_angle_error(GAMMA_F_RAD, GAMMA0_RAD)
        self.assertTrue(math.isclose(eg, EG_REF_RAD, rel_tol=1e-9))
        self.assertTrue(math.isclose(math.degrees(eg), EG_REF_DEG,
                                     rel_tol=1e-9))

    def test_collision_course_baseline_zero(self):
        # Step 6: on the collision course y_0 + v0 * t_go0 = 0 nulls the
        # baseline exactly.
        a_base = iacg.collision_nulling_baseline(
            TGO0_S, Y0_M, iacg.crossrange_velocity(V_MPS, GAMMA0_RAD))
        self.assertLess(abs(a_base), 1e-9)

    def test_bias_anchor(self):
        # Step 5: a_bias = 2.0 * (v - v_f) / t_go for the steeper
        # commanded terminal dive.
        a_bias = iacg.impact_angle_bias(V_MPS, TGO0_S, GAMMA0_RAD,
                                        GAMMA_F_RAD)
        self.assertTrue(math.isclose(a_bias, ABIAS_REF, rel_tol=1e-9))

    def test_total_command_anchor(self):
        # Step 7: the total lateral acceleration command is the baseline
        # plus the bias.
        a_cmd = iacg.impact_angle_guidance_command(
            TGO0_S, Y0_M, iacg.crossrange_velocity(V_MPS, GAMMA0_RAD),
            V_MPS, GAMMA0_RAD, GAMMA_F_RAD)[0]
        self.assertTrue(math.isclose(a_cmd, ACMD_REF, rel_tol=1e-9))

    def test_command_tuple_anchor(self):
        # Step 7: the full tuple (a_cmd, a_base, a_bias, t_go, e_g).
        res = iacg.impact_angle_guidance_command(
            TGO0_S, Y0_M, iacg.crossrange_velocity(V_MPS, GAMMA0_RAD),
            V_MPS, GAMMA0_RAD, GAMMA_F_RAD)
        self.assertTrue(math.isclose(res[0], ACMD_REF, rel_tol=1e-9))
        self.assertLess(abs(res[1]), 1e-9)
        self.assertTrue(math.isclose(res[2], ABIAS_REF, rel_tol=1e-9))
        self.assertTrue(math.isclose(res[3], TGO_REF, rel_tol=1e-9))
        self.assertTrue(math.isclose(res[4], EG_REF_RAD, rel_tol=1e-9))


class CrossrangeVelocityTest(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the crossrange velocity."""

    def test_horizontal_flight_zero_crossrange(self):
        v = iacg.crossrange_velocity(V_MPS, 0.0)
        self.assertAlmostEqual(v, 0.0, delta=1e-12)

    def test_vertical_flight_full_speed(self):
        v = iacg.crossrange_velocity(V_MPS, math.pi / 2.0)
        self.assertTrue(math.isclose(v, V_MPS, rel_tol=1e-12))

    def test_rejects_nonpositive_speed(self):
        with self.assertRaises(ValueError):
            iacg.crossrange_velocity(0.0, GAMMA0_RAD)
        with self.assertRaises(ValueError):
            iacg.crossrange_velocity(-1.0, GAMMA0_RAD)


class TgoEstimateTest(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the time-to-go estimate."""

    def test_zero_range_valid(self):
        tgo = iacg.tgo_estimate(V_MPS, 0.0)
        self.assertEqual(tgo, 0.0)

    def test_rejects_negative_range(self):
        with self.assertRaises(ValueError):
            iacg.tgo_estimate(V_MPS, -100.0)

    def test_rejects_nonpositive_closing_speed(self):
        with self.assertRaises(ValueError):
            iacg.tgo_estimate(0.0, RANGE_M)
        with self.assertRaises(ValueError):
            iacg.tgo_estimate(-1.0, RANGE_M)


class ImpactAngleErrorTest(unittest.TestCase):
    """Step 4 of the SKILL.md workflow: the impact-angle error."""

    def test_error_arithmetic_and_zero(self):
        eg = iacg.impact_angle_error(GAMMA_F_RAD, GAMMA0_RAD)
        self.assertTrue(math.isclose(eg, GAMMA_F_RAD - GAMMA0_RAD,
                                     rel_tol=1e-15))
        self.assertAlmostEqual(iacg.impact_angle_error(GAMMA0_RAD,
                                                       GAMMA0_RAD),
                               0.0, delta=1e-15)


class ImpactAngleBiasTest(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the impact-angle-error-feedback
    bias term."""

    def test_zero_impact_angle_error_zero_bias(self):
        a_bias = iacg.impact_angle_bias(V_MPS, TGO0_S, GAMMA_F_RAD,
                                        GAMMA_F_RAD)
        self.assertAlmostEqual(a_bias, 0.0, delta=1e-12)

    def test_command_equals_baseline_at_zero_error(self):
        vf = iacg.crossrange_velocity(V_MPS, GAMMA_F_RAD)
        a_cmd, a_base, a_bias, _, _ = iacg.impact_angle_guidance_command(
            TGO0_S, Y0_M, vf, V_MPS, GAMMA_F_RAD, GAMMA_F_RAD)
        self.assertAlmostEqual(a_bias, 0.0, delta=1e-12)
        self.assertTrue(math.isclose(a_cmd, a_base, rel_tol=1e-12,
                                     abs_tol=1e-12))

    def test_steeper_command_positive_bias(self):
        a_bias = iacg.impact_angle_bias(V_MPS, TGO0_S, GAMMA0_RAD,
                                        GAMMA_F_RAD)
        self.assertGreater(a_bias, 0.0)

    def test_shallower_command_negative_bias_anchor(self):
        a_bias = iacg.impact_angle_bias(V_MPS, TGO0_S, GAMMA_F_RAD,
                                        math.radians(-10.0))
        self.assertTrue(math.isclose(a_bias, ABIAS_SHALLOW_REF,
                                     rel_tol=1e-9))

    def test_speed_doubling_doubles_bias(self):
        a_bias = iacg.impact_angle_bias(V_MPS, TGO0_S, GAMMA0_RAD,
                                        GAMMA_F_RAD)
        a_bias_2 = iacg.impact_angle_bias(2.0 * V_MPS, TGO0_S, GAMMA0_RAD,
                                          GAMMA_F_RAD)
        self.assertTrue(math.isclose(a_bias_2, 2.0 * a_bias, rel_tol=1e-12))
        self.assertTrue(math.isclose(a_bias_2, ABIAS_DOUBLE_REF,
                                     rel_tol=1e-9))

    def test_rejects_nonpositive_speed(self):
        with self.assertRaises(ValueError):
            iacg.impact_angle_bias(0.0, TGO0_S, GAMMA0_RAD, GAMMA_F_RAD)
        with self.assertRaises(ValueError):
            iacg.impact_angle_bias(-1.0, TGO0_S, GAMMA0_RAD, GAMMA_F_RAD)

    def test_rejects_nonpositive_tgo(self):
        with self.assertRaises(ValueError):
            iacg.impact_angle_bias(V_MPS, 0.0, GAMMA0_RAD, GAMMA_F_RAD)
        with self.assertRaises(ValueError):
            iacg.impact_angle_bias(V_MPS, -1.0, GAMMA0_RAD, GAMMA_F_RAD)


class CollisionNullingBaselineTest(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the collision-course nulling
    baseline."""

    def test_collision_course_baseline_zero(self):
        v_perp = -150.0
        tgo = 33.333333333333
        a_base = iacg.collision_nulling_baseline(tgo, -v_perp * tgo,
                                                 v_perp)
        self.assertLess(abs(a_base), 1e-9)

    def test_baseline_scales_with_offset(self):
        # At zero crossrange velocity the baseline is exactly
        # -W_Y * offset / tgo^2, so doubling the offset doubles it.
        a1 = iacg.collision_nulling_baseline(33.333333333333, 100.0, 0.0)
        a2 = iacg.collision_nulling_baseline(33.333333333333, 200.0, 0.0)
        self.assertTrue(math.isclose(a2, 2.0 * a1, rel_tol=1e-12))

    def test_rejects_nonpositive_tgo(self):
        with self.assertRaises(ValueError):
            iacg.collision_nulling_baseline(0.0, 100.0, -150.0)
        with self.assertRaises(ValueError):
            iacg.collision_nulling_baseline(-1.0, 100.0, -150.0)


class TerminalStraightCourseTest(unittest.TestCase):
    """Steps 5-7 of the SKILL.md workflow: the terminal straight course
    that reaches the target at the commanded angle (v = v_f,
    crossrange_offset = -v_f * t_go) gives a zero total command."""

    def test_zero_total_command_anchor(self):
        vf = iacg.crossrange_velocity(V_MPS, GAMMA_F_RAD)
        tgo = 10.0
        a_cmd, a_base, a_bias, _, _ = iacg.impact_angle_guidance_command(
            tgo, -vf * tgo, vf, V_MPS, GAMMA_F_RAD, GAMMA_F_RAD)
        self.assertLess(abs(a_cmd), 1e-9)
        self.assertLess(abs(a_base), 1e-9)
        self.assertLess(abs(a_bias), 1e-9)

    def test_straight_course_offset_anchor(self):
        # The offset -v_f * t_go at t_go = 10 s is 2598.076211353 m.
        vf = iacg.crossrange_velocity(V_MPS, GAMMA_F_RAD)
        offset = -vf * 10.0
        self.assertTrue(math.isclose(offset, 2598.076211353, rel_tol=1e-9))


class GuidanceCommandTest(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the total lateral acceleration
    command aggregation."""

    def test_command_equals_baseline_plus_bias(self):
        v0 = iacg.crossrange_velocity(V_MPS, GAMMA0_RAD)
        a_base = iacg.collision_nulling_baseline(TGO0_S, Y0_M, v0)
        a_bias = iacg.impact_angle_bias(V_MPS, TGO0_S, GAMMA0_RAD,
                                        GAMMA_F_RAD)
        res = iacg.impact_angle_guidance_command(
            TGO0_S, Y0_M, v0, V_MPS, GAMMA0_RAD, GAMMA_F_RAD)
        self.assertTrue(math.isclose(res[0], a_base + a_bias,
                                     rel_tol=1e-12))
        self.assertTrue(math.isclose(res[1], a_base, rel_tol=1e-12))
        self.assertTrue(math.isclose(res[2], a_bias, rel_tol=1e-12))

    def test_determinism_bit_identical(self):
        r1 = iacg.impact_angle_guidance_command(
            TGO0_S, Y0_M, iacg.crossrange_velocity(V_MPS, GAMMA0_RAD),
            V_MPS, GAMMA0_RAD, GAMMA_F_RAD)
        r2 = iacg.impact_angle_guidance_command(
            TGO0_S, Y0_M, iacg.crossrange_velocity(V_MPS, GAMMA0_RAD),
            V_MPS, GAMMA0_RAD, GAMMA_F_RAD)
        self.assertEqual(r1, r2)

    def test_rejects_nonpositive_inputs(self):
        with self.assertRaises(ValueError):
            iacg.impact_angle_guidance_command(TGO0_S, Y0_M, -150.0, 0.0,
                                               GAMMA0_RAD, GAMMA_F_RAD)
        with self.assertRaises(ValueError):
            iacg.impact_angle_guidance_command(0.0, Y0_M, -150.0, V_MPS,
                                               GAMMA0_RAD, GAMMA_F_RAD)
        with self.assertRaises(ValueError):
            iacg.impact_angle_guidance_command(-1.0, Y0_M, -150.0, V_MPS,
                                               GAMMA0_RAD, GAMMA_F_RAD)


class LinearModelClosedLoopTest(unittest.TestCase):
    """SKILL.md Verification: the linear-model closed-loop check (fixed-
    step Euler of dy/dt = v, dv/dt = a_cmd with the time-to-go reduced
    by dt each step) drives the state to the terminal constraint."""

    def _linear_loop_end(self, dt=0.001):
        y = Y0_M
        v = iacg.crossrange_velocity(V_MPS, GAMMA0_RAD)
        tgo = TGO0_S
        while tgo > dt:
            gamma = math.asin(max(-1.0, min(1.0, v / V_MPS)))
            a_cmd = iacg.impact_angle_guidance_command(
                tgo, y, v, V_MPS, gamma, GAMMA_F_RAD)[0]
            y = y + v * dt
            v = v + a_cmd * dt
            tgo = tgo - dt
        return y, v

    def test_linear_loop_converges_to_terminal_constraint(self):
        # The closed loop drives the crossrange offset toward zero and
        # the crossrange velocity toward the terminal value v_f.
        vf = iacg.crossrange_velocity(V_MPS, GAMMA_F_RAD)
        y_end, v_end = self._linear_loop_end()
        self.assertLess(abs(v_end - vf), 0.05)
        self.assertLess(abs(y_end), 1.0)

    def test_linear_loop_anchor_terminals(self):
        # Anchor (spec run): y_end = 0.086606202 m, v_end =
        # -259.823007259 m/s, |v_end - v_f| = 1.539e-02 m/s.
        y_end, v_end = self._linear_loop_end()
        self.assertTrue(math.isclose(y_end, LINEAR_Y_END_REF,
                                     rel_tol=1e-3, abs_tol=1e-3))
        self.assertTrue(math.isclose(v_end, LINEAR_V_END_REF,
                                     rel_tol=1e-6, abs_tol=1e-3))


class PlanarEngagementProbeTest(unittest.TestCase):
    """SKILL.md Verification: the nonlinear planar engagement identity
    probe (fixed-step Euler of the point-mass kinematics under the law,
    stationary target at the origin, worked-example start, stop at
    range <= 0.5 m) reaches the target with the terminal flight path
    angle in the anchor band."""

    def _planar_probe(self, dt):
        px, py = -8660.254038, Y0_M
        gamma = GAMMA0_RAD
        t = 0.0
        miss = float("inf")
        cmax_traverse = 0.0
        while True:
            rx, ry = -px, -py
            rr = math.hypot(rx, ry)
            miss = min(miss, rr)
            if rr <= 0.5 or t > 60.0:
                break
            vc = V_MPS * (math.cos(gamma) * rx + math.sin(gamma) * ry) / rr
            if vc <= 1e-9:
                break
            tgo = rr / vc
            a_cmd = iacg.impact_angle_guidance_command(
                tgo, py, V_MPS * math.sin(gamma), V_MPS, gamma,
                GAMMA_F_RAD)[0]
            if rr >= 50.0:
                cmax_traverse = max(cmax_traverse, abs(a_cmd))
            gamma_new = gamma + a_cmd / V_MPS * dt
            px = px + V_MPS * math.cos(gamma) * dt
            py = py + V_MPS * math.sin(gamma) * dt
            gamma = gamma_new
            t = t + dt
        return t, rr, math.degrees(gamma), miss, cmax_traverse

    def test_dt0005_flight_time_band(self):
        t, _, _, _, _ = self._planar_probe(0.005)
        self.assertGreater(t, 33.5)
        self.assertLess(t, 34.5)

    def test_dt0005_terminal_angle_band_and_anchor(self):
        _, _, gamma_end, _, _ = self._planar_probe(0.005)
        self.assertGreater(gamma_end, -61.0)
        self.assertLess(gamma_end, -59.0)
        self.assertTrue(math.isclose(gamma_end, PLANAR_GAMMA_END_REF,
                                     abs_tol=1e-3))

    def test_dt0005_miss_and_command_bounds(self):
        t, _, _, miss, cmax_traverse = self._planar_probe(0.005)
        self.assertLess(miss, 5.0)
        self.assertTrue(math.isclose(t, PLANAR_T_REF, abs_tol=1e-3))
        self.assertLess(cmax_traverse, 60.0)

    def test_dt0001_terminal_angle_in_band(self):
        _, _, gamma_end, _, _ = self._planar_probe(0.001)
        self.assertGreater(gamma_end, -61.0)
        self.assertLess(gamma_end, -59.0)


if __name__ == "__main__":
    unittest.main()
