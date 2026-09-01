#!/usr/bin/env python3
"""Gate 3 contract test: midcourse guidance.

Exercises scripts/midcourse_guidance_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - the midcourse
guidance shaping set for interceptors and guided vehicles: waypoint
steering psi_d = atan2(wy - py, wx - px), wrapped course error,
turn-rate-limited commanded heading psi_c = psi + clamp(e, -omega_max
* dt, +omega_max * dt), velocity-to-be-gained vgo = max(0, V_target -
V * cos(e)), zero-effort-miss of the constant-velocity closing
geometry t_go = max(0, -(rho . v_rel) / |v_rel|^2), ZEM = |rho +
v_rel * t_go|, handover range check, gravity-compensated ascent
acceleration a_c = V * gamma_dot + g * cos(gamma), and ValueError on
invalid inputs.

Analytic anchors:
  psi_d (0,0 -> 1000,500)               = 0.4636476090008061 rad
                                          (26.56505117707799 deg)
  clamped turn, 5 deg/s, dt = 1 s       = 0.08726646259971647 rad
  vgo, V = 250 m/s, e = 20 deg,
      V_target = 300 m/s                = 300 - 250*cos(20 deg)
                                        = 65.07684480352289 m/s
  ZEM, interceptor (0,0) 300 m/s +x,
      target (6000,150) stationary:     t_go = 20 s, ZEM = 150 m
  ZEM, target (9000,0) 100 m/s +x:      t_go = 45 s, ZEM = 0 m
  ascent, V = 300 m/s, gamma_dot = 0.5
      deg/s, gamma = 30 deg, g = 9.81   = 11.11370307 m/s^2
Asserted with places=4. Units: m, s, m/s, rad, rad/s, m/s^2.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import midcourse_guidance_logic as mcg  # noqa: E402

G = 9.81
DEG5 = math.radians(5.0)
DEG20 = math.radians(20.0)
DEG30 = math.radians(30.0)
DEG45 = math.radians(45.0)
PSI_D_REF = 0.4636476090008061
TURN5_REF = 0.08726646259971647
VGO_REF = 65.07684480352289
VGO_ZERO_REF = 50.0
ASCENT_REF = 11.11370307


class WaypointSteeringTest(unittest.TestCase):
    def test_desired_heading_anchor(self):
        psi_d = mcg.desired_heading((0.0, 0.0), (1000.0, 500.0))
        self.assertAlmostEqual(psi_d, PSI_D_REF, places=6)
        self.assertAlmostEqual(math.degrees(psi_d), 26.56505117707799, places=4)

    def test_desired_heading_axis_cases(self):
        self.assertAlmostEqual(
            mcg.desired_heading((0.0, 0.0), (1000.0, 0.0)), 0.0, places=6
        )
        self.assertAlmostEqual(
            mcg.desired_heading((0.0, 0.0), (0.0, 1000.0)),
            math.pi / 2.0, places=6
        )

    def test_desired_heading_offset_position(self):
        psi = mcg.desired_heading((100.0, 50.0), (1100.0, 550.0))
        self.assertAlmostEqual(psi, PSI_D_REF, places=6)

    def test_course_error_anchor_heading_zero(self):
        e = mcg.course_error((0.0, 0.0), (1000.0, 500.0), 0.0)
        self.assertAlmostEqual(e, PSI_D_REF, places=6)

    def test_course_error_short_way_wrap(self):
        e = mcg.course_error((0.0, 0.0), (1000.0, 500.0), DEG45)
        self.assertAlmostEqual(math.degrees(e), -18.43494882292201, places=4)

    def test_course_error_wraps_into_pi(self):
        # Heading 350 deg toward a waypoint at 10 deg: the error is
        # +20 deg (short way), not +340 deg.
        e = mcg.course_error((0.0, 0.0), (1000.0, 176.327), math.radians(350.0))
        self.assertLess(abs(e), math.pi)
        self.assertGreater(e, 0.0)

    def test_steering_drives_course_error_to_zero(self):
        # Stationary heading update with a 10 deg/s limit, dt = 1 s:
        # 0 -> 10 -> 20 -> 26.565 deg, then the error is zero.
        heading = 0.0
        for _ in range(10):
            heading = mcg.commanded_heading(
                (0.0, 0.0), (1000.0, 500.0), heading,
                math.radians(10.0), 1.0,
            )
        e = mcg.course_error((0.0, 0.0), (1000.0, 500.0), heading)
        self.assertAlmostEqual(e, 0.0, places=9)
        self.assertAlmostEqual(heading, PSI_D_REF, places=6)

    def test_kinematic_simulation_reaches_waypoint(self):
        # Moving vehicle, 100 m/s, 10 deg/s turn limit, dt = 0.1 s.
        # The vehicle curves onto the course and closes to the waypoint
        # (closest approach inside 15 s), then flies past and starts
        # turning back; assert the closest approach is close.
        px, py = 0.0, 0.0
        heading = 0.0
        min_dist = float("inf")
        for _ in range(200):
            heading = mcg.commanded_heading(
                (px, py), (1000.0, 500.0), heading,
                math.radians(10.0), 0.1,
            )
            px += 100.0 * 0.1 * math.cos(heading)
            py += 100.0 * 0.1 * math.sin(heading)
            min_dist = min(min_dist, math.hypot(1000.0 - px, 500.0 - py))
        self.assertLess(min_dist, 100.0)

    def test_turn_rate_limit_clamps_commanded_turn(self):
        psi_c = mcg.commanded_heading(
            (0.0, 0.0), (1000.0, 500.0), 0.0, DEG5, 1.0
        )
        self.assertAlmostEqual(psi_c, TURN5_REF, places=6)
        self.assertAlmostEqual(math.degrees(psi_c), 5.0, places=4)

    def test_high_turn_rate_passes_full_error(self):
        psi_c = mcg.commanded_heading(
            (0.0, 0.0), (1000.0, 500.0), 0.0, math.radians(30.0), 1.0
        )
        self.assertAlmostEqual(psi_c, PSI_D_REF, places=6)

    def test_turn_limit_negative_raises(self):
        with self.assertRaises(ValueError):
            mcg.commanded_heading(
                (0.0, 0.0), (1000.0, 500.0), 0.0, -1.0, 1.0
            )

    def test_dt_non_positive_raises(self):
        with self.assertRaises(ValueError):
            mcg.commanded_heading(
                (0.0, 0.0), (1000.0, 500.0), 0.0, DEG5, 0.0
            )
        with self.assertRaises(ValueError):
            mcg.commanded_heading(
                (0.0, 0.0), (1000.0, 500.0), 0.0, DEG5, -0.5
            )

    def test_non_numeric_inputs_raise(self):
        with self.assertRaises(ValueError):
            mcg.desired_heading("origin", (1000.0, 500.0))
        with self.assertRaises(ValueError):
            mcg.desired_heading((0.0, 0.0), (1000.0,))
        with self.assertRaises(ValueError):
            mcg.course_error((0.0, 0.0), (1000.0, 500.0), "east")

    def test_waypoint_at_position_raises(self):
        with self.assertRaises(ValueError):
            mcg.desired_heading((100.0, 100.0), (100.0, 100.0))


class VelocityToBeGainedTest(unittest.TestCase):
    def test_analytic_anchor_20_deg(self):
        self.assertAlmostEqual(
            mcg.velocity_to_be_gained(250.0, DEG20, 300.0), VGO_REF, places=4
        )

    def test_zero_error_gives_speed_deficit(self):
        self.assertAlmostEqual(
            mcg.velocity_to_be_gained(250.0, 0.0, 300.0), VGO_ZERO_REF, places=4
        )

    def test_heading_error_increases_deficit(self):
        # A heading error reduces the speed component along the
        # desired course, so the velocity-to-be-gained grows.
        vgo_off = mcg.velocity_to_be_gained(250.0, DEG20, 300.0)
        vgo_on = mcg.velocity_to_be_gained(250.0, 0.0, 300.0)
        self.assertGreater(vgo_off, vgo_on)

    def test_clamps_at_zero_when_faster(self):
        self.assertEqual(mcg.velocity_to_be_gained(350.0, 0.0, 300.0), 0.0)
        self.assertEqual(mcg.velocity_to_be_gained(250.0, 0.0, 200.0), 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mcg.velocity_to_be_gained(0.0, 0.0, 300.0)
        with self.assertRaises(ValueError):
            mcg.velocity_to_be_gained(-50.0, 0.0, 300.0)
        with self.assertRaises(ValueError):
            mcg.velocity_to_be_gained(250.0, 0.0, 0.0)
        with self.assertRaises(ValueError):
            mcg.velocity_to_be_gained("fast", 0.0, 300.0)


class ZeroEffortMissTest(unittest.TestCase):
    def test_analytic_anchor_stationary_target(self):
        z = mcg.zero_effort_miss(
            (0.0, 0.0), (300.0, 0.0), (6000.0, 150.0), (0.0, 0.0)
        )
        self.assertAlmostEqual(z["zem"], 150.0, places=4)
        self.assertAlmostEqual(z["time_to_go"], 20.0, places=4)
        cx, cy = z["closest_point"]
        self.assertAlmostEqual(cx, 0.0, places=4)
        self.assertAlmostEqual(cy, 150.0, places=4)

    def test_analytic_anchor_moving_target_perfect_line(self):
        z = mcg.zero_effort_miss(
            (0.0, 0.0), (300.0, 0.0), (9000.0, 0.0), (100.0, 0.0)
        )
        self.assertAlmostEqual(z["zem"], 0.0, places=4)
        self.assertAlmostEqual(z["time_to_go"], 45.0, places=4)

    def test_zem_matches_analytic_formula(self):
        ri = (100.0, 200.0)
        vi = (250.0, 40.0)
        rt = (8000.0, 300.0)
        vt = (50.0, -30.0)
        rx = rt[0] - ri[0]
        ry = rt[1] - ri[1]
        vrx = vt[0] - vi[0]
        vry = vt[1] - vi[1]
        t_go = max(0.0, -(rx * vrx + ry * vry) / (vrx * vrx + vry * vry))
        cx = rx + vrx * t_go
        cy = ry + vry * t_go
        zem_ref = math.hypot(cx, cy)
        z = mcg.zero_effort_miss(ri, vi, rt, vt)
        self.assertAlmostEqual(z["zem"], zem_ref, places=6)
        self.assertAlmostEqual(z["time_to_go"], t_go, places=6)

    def test_receding_geometry_clamps_time_to_go(self):
        # Target moving away: rho . v_rel > 0, closest approach is in
        # the past, so t_go clamps to 0 and ZEM is the current range.
        z = mcg.zero_effort_miss(
            (0.0, 0.0), (300.0, 0.0), (6000.0, 0.0), (400.0, 0.0)
        )
        self.assertEqual(z["time_to_go"], 0.0)
        self.assertAlmostEqual(z["zem"], 6000.0, places=4)

    def test_zero_relative_velocity_raises(self):
        with self.assertRaises(ValueError):
            mcg.zero_effort_miss(
                (0.0, 0.0), (300.0, 0.0), (6000.0, 0.0), (300.0, 0.0)
            )

    def test_non_numeric_inputs_raise(self):
        with self.assertRaises(ValueError):
            mcg.zero_effort_miss(
                (0.0, 0.0), (300.0, 0.0), ("far", 0.0), (0.0, 0.0)
            )


class HandoverCheckTest(unittest.TestCase):
    def test_handover_at_handoff_range(self):
        self.assertTrue(mcg.handover_check((0.0, 0.0), (8000.0, 0.0), 8000.0))

    def test_no_handover_beyond_handoff_range(self):
        self.assertFalse(mcg.handover_check((0.0, 0.0), (9000.0, 0.0), 8000.0))

    def test_handover_inside_handoff_range(self):
        self.assertTrue(mcg.handover_check((0.0, 0.0), (3000.0, 4000.0), 8000.0))

    def test_negative_handoff_range_raises(self):
        with self.assertRaises(ValueError):
            mcg.handover_check((0.0, 0.0), (8000.0, 0.0), -1.0)

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            mcg.handover_check((0.0, 0.0), ("near", 0.0), 8000.0)


class GravityCompensatedAccelTest(unittest.TestCase):
    def test_analytic_anchor(self):
        self.assertAlmostEqual(
            mcg.gravity_compensated_accel(
                300.0, math.radians(0.5), math.radians(30.0), G
            ),
            ASCENT_REF,
            places=4,
        )

    def test_decomposes_into_program_and_gravity_terms(self):
        v_term = 300.0 * math.radians(0.5)
        g_term = G * math.cos(math.radians(30.0))
        got = mcg.gravity_compensated_accel(
            300.0, math.radians(0.5), math.radians(30.0), G
        )
        self.assertAlmostEqual(got, v_term + g_term, places=6)

    def test_zero_rate_holds_against_gravity_only(self):
        self.assertAlmostEqual(
            mcg.gravity_compensated_accel(300.0, 0.0, 0.0, G), G, places=4
        )

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            mcg.gravity_compensated_accel(0.0, 0.0, 0.0, G)
        with self.assertRaises(ValueError):
            mcg.gravity_compensated_accel(300.0, 0.0, 0.0, -G)
        with self.assertRaises(ValueError):
            mcg.gravity_compensated_accel("fast", 0.0, 0.0, G)


class DemonstrateTest(unittest.TestCase):
    def test_demonstrate_runs(self):
        # The demonstration function is part of the contract; it must
        # run offline and print the worked anchors.
        mcg.demonstrate()


if __name__ == "__main__":
    unittest.main(verbosity=2)
