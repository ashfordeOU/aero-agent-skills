#!/usr/bin/env python3
"""Gate 3 contract test: FMS lateral navigation (LNAV) guidance logic.

Exercises scripts/lateral_navigation_logic.py (stdlib unittest, offline,
deterministic). Contract: docs/harness-contract.md gate 3. Covers the
great-circle track and distance between waypoints, the worked parallel
leg (50N, 0E) to (50N, 10E), the cross-track error sign and magnitude at
(51N, 5E) and its mirror point, the along-track distance to go, the
track angle error wrapping, the fixed-angle intercept heading capture,
the turn anticipation distance at 90 m/s with a 30 deg track change at
25 deg bank, the fly-by versus fly-over transition verdict, the combined
lnav_guidance summary, and ValueError rejection of non-physical inputs
(out-of-range latitude, non-finite values, zero speed, out-of-range
bank, turn reversal deltas, identical leg endpoints).
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import lateral_navigation_logic as ln  # noqa: E402

R = ln.EARTH_RADIUS_M
d2r = math.radians
r2d = math.degrees

# Worked example geometry: A (50N, 0E), B (50N, 10E), P (51N, 5E).
LAT_A, LON_A = d2r(50.0), d2r(0.0)
LAT_B, LON_B = d2r(50.0), d2r(10.0)
LAT_P, LON_P = d2r(51.0), d2r(5.0)
# Module real outputs (see SKILL.md worked example).
TRACK_AB_RAD = 1.5038761977559925          # 86.165759 deg
LEG_DISTANCE_M = 714214.3017783572         # 714.2 km
XTK_LEFT_M = 99238.51006183824             # +99.2 km, sign +1
XTK_RIGHT_M = -123151.34307391857          # -123.2 km, sign -1
TO_GO_M = 357107.1508891881                # 357.1 km to the waypoint
D_ANT_WORKED_M = 474.61804692318674        # 90 m/s, 30 deg, 25 deg bank


class GreatCircleTrackTest(unittest.TestCase):
    def test_equator_east_track_ninety(self):
        # Due east along the equator: initial track exactly 90 deg.
        t = ln.great_circle_track(d2r(0.0), d2r(0.0), d2r(0.0), d2r(10.0))
        self.assertAlmostEqual(r2d(t), 90.0, places=9)

    def test_meridian_north_and_equator_west(self):
        t_n = ln.great_circle_track(d2r(0.0), d2r(0.0), d2r(10.0), d2r(0.0))
        self.assertAlmostEqual(r2d(t_n), 0.0, places=9)
        t_w = ln.great_circle_track(d2r(0.0), d2r(0.0), d2r(0.0), d2r(-10.0))
        self.assertAlmostEqual(r2d(t_w), 270.0, places=9)

    def test_parallel_leg_worked_track(self):
        # (50N, 0E) to (50N, 10E): great circle starts 3.83 deg north of
        # east because the arc bulges toward the pole.
        t = ln.great_circle_track(LAT_A, LON_A, LAT_B, LON_B)
        self.assertAlmostEqual(t, TRACK_AB_RAD, places=12)
        self.assertAlmostEqual(r2d(t), 86.165759, places=4)

    def test_track_normalized_to_standard_range(self):
        for lon_b_deg in (-150.0, -90.0, -10.0, 5.0, 45.0, 170.0):
            t = ln.great_circle_track(LAT_A, LON_A, d2r(50.0), d2r(lon_b_deg))
            self.assertGreaterEqual(t, 0.0)
            self.assertLess(t, 2.0 * math.pi)

    def test_reverse_track_on_symmetric_legs(self):
        # On a meridian the outbound and return tracks are antiparallel.
        t_ab = ln.great_circle_track(d2r(0.0), d2r(0.0), d2r(10.0), d2r(0.0))
        t_ba = ln.great_circle_track(d2r(10.0), d2r(0.0), d2r(0.0), d2r(0.0))
        self.assertAlmostEqual(t_ba, math.pi, places=9)
        self.assertAlmostEqual(abs(ln.wrap_angle(t_ba - t_ab)), math.pi, places=9)

    def test_identical_positions_raise(self):
        with self.assertRaises(ValueError):
            ln.great_circle_track(LAT_A, LON_A, LAT_A, LON_A)

    def test_invalid_positions_raise(self):
        with self.assertRaises(ValueError):
            ln.great_circle_track(d2r(95.0), LON_A, LAT_B, LON_B)
        with self.assertRaises(ValueError):
            ln.great_circle_track(LAT_A, LON_A, d2r(-91.0), LON_B)
        with self.assertRaises(ValueError):
            ln.great_circle_track(float("nan"), LON_A, LAT_B, LON_B)
        with self.assertRaises(ValueError):
            ln.great_circle_track(LAT_A, float("inf"), LAT_B, LON_B)


class GreatCircleDistanceTest(unittest.TestCase):
    def test_parallel_leg_worked_distance(self):
        # Real great-circle distance: 714.2 km, close to the parallel
        # shortcut 10 deg * cos(50) * R = 714.7 km.
        d = ln.great_circle_distance(LAT_A, LON_A, LAT_B, LON_B)
        self.assertAlmostEqual(d, LEG_DISTANCE_M, delta=0.5)
        approx = d2r(10.0) * math.cos(LAT_A) * R
        self.assertAlmostEqual(d / approx, 0.99926, places=4)

    def test_distance_symmetric(self):
        d_ab = ln.great_circle_distance(LAT_A, LON_A, LAT_B, LON_B)
        d_ba = ln.great_circle_distance(LAT_B, LON_B, LAT_A, LON_A)
        self.assertAlmostEqual(d_ab, d_ba, places=6)

    def test_known_distances(self):
        q = ln.great_circle_distance(d2r(0.0), d2r(0.0), d2r(0.0), d2r(90.0))
        self.assertAlmostEqual(q, 0.5 * math.pi * R, delta=0.5)
        h = ln.great_circle_distance(d2r(0.0), d2r(0.0), d2r(0.0), d2r(180.0))
        self.assertAlmostEqual(h, math.pi * R, delta=0.5)
        m = ln.great_circle_distance(d2r(0.0), d2r(0.0), d2r(10.0), d2r(0.0))
        self.assertAlmostEqual(m, 1111949.266, delta=0.5)

    def test_identical_points_zero(self):
        self.assertEqual(ln.great_circle_distance(LAT_A, LON_A, LAT_A, LON_A), 0.0)
        with self.assertRaises(ValueError):
            ln.great_circle_distance(LAT_A, LON_A, d2r(90.5), LON_B)


class CrossTrackErrorTest(unittest.TestCase):
    def test_worked_point_left_of_track_positive(self):
        # P (51N, 5E) sits left of the eastbound leg; the specified
        # equation returns a positive value there.
        xtk_m, sign = ln.cross_track_error(LAT_A, LON_A, LAT_B, LON_B, LAT_P, LON_P)
        self.assertAlmostEqual(xtk_m, XTK_LEFT_M, delta=0.5)
        self.assertEqual(sign, 1)

    def test_mirror_point_right_of_track_negative(self):
        # P (49N, 5E), the mirror across the track, gives the opposite
        # sign at its own (larger) magnitude.
        lat_m, lon_m = d2r(49.0), d2r(5.0)
        xtk_m, sign = ln.cross_track_error(LAT_A, LON_A, LAT_B, LON_B, lat_m, lon_m)
        self.assertAlmostEqual(xtk_m, XTK_RIGHT_M, delta=0.5)
        self.assertEqual(sign, -1)

    def test_on_track_positions_zero(self):
        # The far endpoint B lies on the leg.
        xtk_b, sign_b = ln.cross_track_error(LAT_A, LON_A, LAT_B, LON_B, LAT_B, LON_B)
        self.assertAlmostEqual(xtk_b, 0.0, places=9)
        self.assertEqual(sign_b, 1)
        # A point on the same meridian great circle is on track.
        xtk_m, _ = ln.cross_track_error(
            d2r(0.0), d2r(0.0), d2r(10.0), d2r(0.0), d2r(5.0), d2r(0.0)
        )
        self.assertAlmostEqual(xtk_m, 0.0, places=9)
        # The leg start itself has no cross-track deviation.
        xtk_a, sign_a = ln.cross_track_error(LAT_A, LON_A, LAT_B, LON_B, LAT_A, LON_A)
        self.assertAlmostEqual(xtk_a, 0.0, places=9)
        self.assertEqual(sign_a, 1)

    def test_out_of_range_latitude_raises(self):
        with self.assertRaises(ValueError):
            ln.cross_track_error(LAT_A, LON_A, LAT_B, LON_B, d2r(120.0), LON_P)


class AlongTrackDistanceTest(unittest.TestCase):
    def test_worked_distance_to_go(self):
        to_go = ln.along_track_distance(LAT_A, LON_A, LAT_B, LON_B, LAT_P, LON_P)
        self.assertAlmostEqual(to_go, TO_GO_M, delta=0.5)

    def test_endpoint_and_beyond_values(self):
        # At B there is nothing left of the leg; at A the whole leg lies
        # ahead.
        at_b = ln.along_track_distance(LAT_A, LON_A, LAT_B, LON_B, LAT_B, LON_B)
        self.assertAlmostEqual(at_b, 0.0, places=6)
        at_a = ln.along_track_distance(LAT_A, LON_A, LAT_B, LON_B, LAT_A, LON_A)
        self.assertAlmostEqual(at_a, LEG_DISTANCE_M, delta=0.5)
        # Eastbound equator leg A (0, 0) to B (0N, 10E); P at 15E lies
        # past the waypoint on the same great circle.
        past = ln.along_track_distance(
            d2r(0.0), d2r(0.0), d2r(0.0), d2r(10.0), d2r(0.0), d2r(15.0)
        )
        self.assertEqual(past, 0.0)

    def test_midpoint_of_meridian_leg(self):
        to_go = ln.along_track_distance(
            d2r(0.0), d2r(0.0), d2r(10.0), d2r(0.0), d2r(5.0), d2r(0.0)
        )
        self.assertAlmostEqual(to_go, 555974.633, delta=0.5)


class TrackAngleErrorTest(unittest.TestCase):
    def test_worked_signs(self):
        # Track 350 deg with current 10 deg: 20 deg right turn needed.
        t1 = ln.track_angle_error(d2r(10.0), d2r(350.0))
        self.assertAlmostEqual(r2d(t1), -20.0, places=9)
        # Track 10 deg with current 350 deg: 20 deg left turn.
        t2 = ln.track_angle_error(d2r(350.0), d2r(10.0))
        self.assertAlmostEqual(r2d(t2), 20.0, places=9)

    def test_antisymmetry(self):
        t1 = ln.track_angle_error(d2r(40.0), TRACK_AB_RAD)
        t2 = ln.track_angle_error(TRACK_AB_RAD, d2r(40.0))
        self.assertAlmostEqual(t1, -t2, places=12)

    def test_wrapping_behavior(self):
        for cur_deg, des_deg in ((10.0, 350.0), (200.0, 30.0), (355.0, 5.0)):
            tke = ln.track_angle_error(d2r(cur_deg), d2r(des_deg))
            self.assertGreaterEqual(tke, -math.pi)
            self.assertLess(tke, math.pi)
        # Desired 180 from current 350 is a 170 deg left turn, not a
        # 190 deg right turn.
        tke = ln.track_angle_error(d2r(350.0), d2r(180.0))
        self.assertAlmostEqual(r2d(tke), -170.0, places=9)


class InterceptHeadingTest(unittest.TestCase):
    def test_beyond_limit_steers_toward_desired(self):
        # Current 40 deg against the 86.17 deg leg track: capture at
        # track minus the 30 deg intercept angle.
        h = ln.intercept_heading(TRACK_AB_RAD, d2r(40.0))
        self.assertAlmostEqual(r2d(h), 56.165759, places=4)
        # Current 140 deg: capture at track plus the intercept angle.
        h2 = ln.intercept_heading(TRACK_AB_RAD, d2r(140.0))
        self.assertAlmostEqual(r2d(h2), 116.165759, places=4)

    def test_within_limit_holds_desired_track(self):
        h = ln.intercept_heading(TRACK_AB_RAD, d2r(70.0))
        self.assertAlmostEqual(h, TRACK_AB_RAD, places=12)

    def test_wraparound_and_normalized_capture(self):
        h = ln.intercept_heading(d2r(10.0), d2r(355.0))
        self.assertAlmostEqual(r2d(h), 10.0, places=9)
        h2 = ln.intercept_heading(d2r(350.0), d2r(300.0))
        self.assertAlmostEqual(r2d(h2), 320.0, places=9)
        h3 = ln.intercept_heading(d2r(350.0), d2r(40.0))
        self.assertAlmostEqual(r2d(h3), 20.0, places=9)
        for cur_deg in (5.0, 175.0, 350.0):
            hh = ln.intercept_heading(d2r(10.0), d2r(cur_deg))
            self.assertGreaterEqual(hh, 0.0)
            self.assertLess(hh, 2.0 * math.pi)


class TurnAnticipationTest(unittest.TestCase):
    def test_worked_anticipation_distance(self):
        d = ln.turn_anticipation_distance(90.0, d2r(30.0), 25.0)
        self.assertAlmostEqual(d, D_ANT_WORKED_M, places=6)
        # Consistent with R_turn = v^2 / (g tan(bank)) = 1771.3 m.
        r_turn = 90.0 * 90.0 / (ln.GRAVITY_M_S2 * math.tan(d2r(25.0)))
        self.assertAlmostEqual(r_turn, 1771.30, delta=0.05)
        self.assertAlmostEqual(d, r_turn * math.tan(d2r(15.0)), places=6)

    def test_speed_quadratic_and_bank_inverse(self):
        d90 = ln.turn_anticipation_distance(90.0, d2r(30.0), 25.0)
        d180 = ln.turn_anticipation_distance(180.0, d2r(30.0), 25.0)
        self.assertAlmostEqual(d180, 4.0 * d90, places=6)
        d_steep = ln.turn_anticipation_distance(90.0, d2r(30.0), 35.0)
        self.assertLess(d_steep, d90)

    def test_left_turn_and_straight_ahead(self):
        d_left = ln.turn_anticipation_distance(90.0, d2r(-30.0), 25.0)
        self.assertAlmostEqual(d_left, D_ANT_WORKED_M, places=6)
        d_straight = ln.turn_anticipation_distance(90.0, 0.0, 25.0)
        self.assertEqual(d_straight, 0.0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            ln.turn_anticipation_distance(0.0, d2r(30.0), 25.0)
        with self.assertRaises(ValueError):
            ln.turn_anticipation_distance(-90.0, d2r(30.0), 25.0)
        for bad_bank in (0.0, 90.0, 95.0, -25.0):
            with self.assertRaises(ValueError):
                ln.turn_anticipation_distance(90.0, d2r(30.0), bad_bank)
        for bad_delta in (math.pi, 2.0 * math.pi, -math.pi):
            with self.assertRaises(ValueError):
                ln.turn_anticipation_distance(90.0, bad_delta, 25.0)
        with self.assertRaises(ValueError):
            ln.turn_anticipation_distance(float("nan"), d2r(30.0), 25.0)


class WaypointTransitionTest(unittest.TestCase):
    def test_fly_by_classification(self):
        tr = ln.waypoint_transition(90.0, d2r(30.0), 25.0)
        self.assertEqual(tr["turn_type"], "fly_by")
        self.assertAlmostEqual(tr["anticipation_distance_m"], D_ANT_WORKED_M, places=6)
        self.assertAlmostEqual(tr["turn_start_distance_m"], D_ANT_WORKED_M, places=6)

    def test_fly_over_classification(self):
        tr = ln.waypoint_transition(90.0, 0.0, 25.0)
        self.assertEqual(tr["turn_type"], "fly_over")
        self.assertEqual(tr["anticipation_distance_m"], 0.0)
        self.assertEqual(tr["turn_start_distance_m"], 0.0)

    def test_dict_keys_and_default_bank(self):
        tr = ln.waypoint_transition(90.0, d2r(30.0))
        self.assertEqual(
            set(tr.keys()),
            {"turn_type", "anticipation_distance_m", "turn_start_distance_m"},
        )
        self.assertEqual(tr["turn_type"], "fly_by")


class LnavGuidanceTest(unittest.TestCase):
    def test_guidance_summary_consistency(self):
        g = ln.lnav_guidance(
            LAT_A, LON_A, LAT_B, LON_B, LAT_P, LON_P, d2r(40.0), 90.0, d2r(30.0), 25.0
        )
        self.assertEqual(
            set(g.keys()),
            {
                "leg_track_rad",
                "leg_distance_m",
                "cross_track_m",
                "cross_track_sign",
                "along_track_remaining_m",
                "track_angle_error_rad",
                "intercept_heading_rad",
                "turn_anticipation_distance_m",
                "waypoint_transition",
            },
        )
        self.assertAlmostEqual(g["leg_track_rad"], TRACK_AB_RAD, places=12)
        self.assertAlmostEqual(g["leg_distance_m"], LEG_DISTANCE_M, delta=0.5)
        self.assertAlmostEqual(g["cross_track_m"], XTK_LEFT_M, delta=0.5)
        self.assertEqual(g["cross_track_sign"], 1)
        self.assertAlmostEqual(g["along_track_remaining_m"], TO_GO_M, delta=0.5)
        self.assertAlmostEqual(
            g["intercept_heading_rad"],
            ln.intercept_heading(TRACK_AB_RAD, d2r(40.0)),
            places=12,
        )
        self.assertEqual(g["waypoint_transition"]["turn_type"], "fly_by")
        self.assertAlmostEqual(
            g["turn_anticipation_distance_m"], D_ANT_WORKED_M, places=6
        )
        # The summary cross-track equals the standalone function output.
        xtk, sign = ln.cross_track_error(LAT_A, LON_A, LAT_B, LON_B, LAT_P, LON_P)
        self.assertAlmostEqual(g["cross_track_m"], xtk, places=9)
        self.assertEqual(g["cross_track_sign"], sign)

    def test_guidance_rejects_nonphysical(self):
        with self.assertRaises(ValueError):
            ln.lnav_guidance(
                LAT_A, LON_A, LAT_B, LON_B, LAT_P, LON_P, d2r(40.0), 0.0, d2r(30.0)
            )
        with self.assertRaises(ValueError):
            ln.lnav_guidance(
                LAT_A, LON_A, LAT_A, LON_A, LAT_P, LON_P, d2r(40.0), 90.0, d2r(30.0)
            )
        with self.assertRaises(ValueError):
            ln.lnav_guidance(
                LAT_A, LON_A, LAT_B, LON_B, LAT_P, LON_P, d2r(40.0), 90.0, d2r(30.0), 90.0
            )


if __name__ == "__main__":
    unittest.main()
