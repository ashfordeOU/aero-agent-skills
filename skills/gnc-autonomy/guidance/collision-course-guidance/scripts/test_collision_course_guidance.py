"""Contract test for constant-bearing collision course guidance logic.

Deterministic stdlib unittest, offline. Run:
    python3 scripts/test_collision_course_guidance.py
"""

import math
import unittest

import collision_course_guidance_logic as ccg

# Worked example (leaf spec): pursuer 600 m/s, target 250 m/s at beta = 60 deg
# off the line of sight, range 10 000 m.  Module frame: los 0 deg, target
# heading 60 deg (target velocity 60 deg off the LOS).
VP, VT = 600.0, 250.0
LOS_EX, H_EX = 0.0, 60.0
R_EX = 10000.0

# Real module outputs on the worked inputs (taken from the running module):
LA_EX = ccg.lead_angle(VP, VT, LOS_EX, H_EX)          # 21.152032974 deg
VC_EX = ccg.collision_closing_speed(VP, VT, LOS_EX, H_EX)  # 684.575732 m/s
TGO_EX = ccg.time_to_go(R_EX, VC_EX)                  # 14.607588 s


class LeadAngleTest(unittest.TestCase):
    def test_lead_angle_worked_anchor(self):
        # Real module value on the worked inputs, inside the 18-24 deg band.
        self.assertAlmostEqual(LA_EX, 21.1520, delta=0.01)
        self.assertTrue(18.0 <= LA_EX <= 24.0)
        # Sine law check: sin(LA) = (Vt/Vp) * sin(beta) with beta = 60 deg.
        beta = math.radians(H_EX - LOS_EX)
        expected = math.degrees(math.asin((VT / VP) * math.sin(beta)))
        self.assertAlmostEqual(LA_EX, expected, places=9)

    def test_lead_angle_positive_toward_target_flight_side(self):
        # beta = +60 (target velocity above the LOS) gives a positive lead.
        self.assertGreater(LA_EX, 0.0)

    def test_mirror_beta_gives_opposite_sign_lead(self):
        # beta = -60 deg gives the opposite-sign lead angle of beta = +60 deg.
        la_plus = ccg.lead_angle(VP, VT, LOS_EX, H_EX)
        la_minus = ccg.lead_angle(VP, VT, LOS_EX, -H_EX)
        self.assertAlmostEqual(la_minus, -la_plus, places=9)

    def test_heading_angle_periodicity(self):
        # Angles wrap: headings 720/780 are the same geometry as 0/60.
        la_wrapped = ccg.lead_angle(VP, VT, 720.0, 780.0)
        self.assertAlmostEqual(la_wrapped, LA_EX, places=9)

    def test_degenerate_head_on_lead_zero(self):
        # A target flying straight at the pursuer (beta = 0) needs no lead.
        self.assertEqual(ccg.lead_angle(VP, VT, 30.0, 30.0), 0.0)
        self.assertEqual(ccg.lead_angle(VP, VT, 0.0, 0.0), 0.0)

    def test_stationary_target_zero_lead(self):
        # target_speed 0: no cross-range motion, lead angle 0.
        self.assertEqual(ccg.lead_angle(VP, 0.0, LOS_EX, H_EX), 0.0)

    def test_asin_argument_out_of_range_raises(self):
        # Target too fast for the geometry: (Vt/Vp) sin(beta) exceeds 1.
        with self.assertRaises(ValueError):
            ccg.lead_angle(100.0, 400.0, LOS_EX, 90.0)
        with self.assertRaises(ValueError):
            ccg.lead_angle(VP, 700.0, LOS_EX, 90.0)

    def test_asin_argument_boundary_exact_one_no_raise(self):
        # Equal speeds at beta = 90 deg: arg exactly 1, lead 90 deg, valid.
        self.assertAlmostEqual(ccg.lead_angle(600.0, 600.0, LOS_EX, 90.0),
                               90.0, places=9)

    def test_faster_target_shallow_geometry_valid(self):
        # Vt > Vp is allowed when the asin argument stays within [-1, 1].
        la = ccg.lead_angle(VP, 700.0, LOS_EX, 30.0)
        self.assertAlmostEqual(
            la, math.degrees(math.asin((700.0 / VP) * math.sin(math.radians(30.0)))),
            places=9,
        )

    def test_pursuer_speed_nonpositive_raises(self):
        with self.assertRaises(ValueError):
            ccg.lead_angle(0.0, VT, LOS_EX, H_EX)
        with self.assertRaises(ValueError):
            ccg.lead_angle(-5.0, VT, LOS_EX, H_EX)

    def test_target_speed_negative_raises(self):
        with self.assertRaises(ValueError):
            ccg.lead_angle(VP, -1.0, LOS_EX, H_EX)


class ClosingSpeedTest(unittest.TestCase):
    def test_closing_speed_worked_anchor(self):
        # Real module value on the worked inputs, inside the 650-720 m/s band.
        self.assertAlmostEqual(VC_EX, 684.5757, delta=0.01)
        self.assertTrue(650.0 <= VC_EX <= 720.0)

    def test_closing_speed_formula(self):
        # Vc = Vp * cos(LA) + Vt * cos(beta).
        beta = math.radians(H_EX - LOS_EX)
        expected = VP * math.cos(math.radians(LA_EX)) + VT * math.cos(beta)
        self.assertAlmostEqual(VC_EX, expected, places=9)

    def test_degenerate_head_on_closing_speed_sum(self):
        # beta = 0: closing speed = pursuer_speed + target_speed.
        vc = ccg.collision_closing_speed(VP, VT, 30.0, 30.0)
        self.assertAlmostEqual(vc, VP + VT, places=9)

    def test_mirror_beta_closing_speed_unchanged(self):
        # Mirror geometry keeps the closing speed (cos is even).
        vc_minus = ccg.collision_closing_speed(VP, VT, LOS_EX, -H_EX)
        self.assertAlmostEqual(vc_minus, VC_EX, places=9)

    def test_no_closing_intercept_raises(self):
        # Faster target flying straight away (beta = +-180): Vc <= 0.
        with self.assertRaises(ValueError):
            ccg.collision_closing_speed(600.0, 900.0, LOS_EX, 180.0)
        with self.assertRaises(ValueError):
            ccg.collision_closing_speed(600.0, 900.0, LOS_EX, -180.0)

    def test_zero_target_speed_closing_is_pursuer_speed(self):
        # Stationary target: closing speed equals the pursuer speed.
        vc = ccg.collision_closing_speed(VP, 0.0, LOS_EX, H_EX)
        self.assertAlmostEqual(vc, VP, places=9)


class TimeToGoTest(unittest.TestCase):
    def test_time_to_go_worked_anchor(self):
        # Real module value at 10 000 m, inside the 13-16 s band.
        self.assertAlmostEqual(TGO_EX, 14.6076, delta=0.01)
        self.assertTrue(13.0 <= TGO_EX <= 16.0)
        self.assertAlmostEqual(TGO_EX, R_EX / VC_EX, places=9)

    def test_time_to_go_negative_range_raises(self):
        with self.assertRaises(ValueError):
            ccg.time_to_go(-1.0, VC_EX)

    def test_time_to_go_nonpositive_closing_raises(self):
        with self.assertRaises(ValueError):
            ccg.time_to_go(R_EX, 0.0)
        with self.assertRaises(ValueError):
            ccg.time_to_go(R_EX, -10.0)

    def test_time_to_go_zero_range_is_zero(self):
        self.assertEqual(ccg.time_to_go(0.0, VC_EX), 0.0)


class InterceptPointTest(unittest.TestCase):
    def test_intercept_point_extrapolates_target(self):
        # Target at origin moving +x at 250 m/s: intercept is x = Vt * t_go.
        ix, iy = ccg.intercept_point(-5000.0, 8660.0, 0.0, 0.0, VT, 0.0, TGO_EX)
        self.assertAlmostEqual(ix, VT * TGO_EX, places=6)
        self.assertAlmostEqual(iy, 0.0, places=6)

    def test_intercept_point_zero_tgo_returns_target_position(self):
        ix, iy = ccg.intercept_point(-5000.0, 8660.0, 100.0, 200.0, VT, 50.0, 0.0)
        self.assertEqual((ix, iy), (100.0, 200.0))

    def test_worked_intercept_target_travel_anchor(self):
        # After t_go the target has moved about 3650 m along its velocity.
        ix, iy = ccg.intercept_point(0.0, 0.0, 0.0, 0.0, VT, 0.0, TGO_EX)
        self.assertAlmostEqual(ix, 3651.9, delta=1.0)
        self.assertAlmostEqual(iy, 0.0, places=6)


class HeadingErrorTest(unittest.TestCase):
    def test_heading_error_on_required_heading_is_zero(self):
        required = LOS_EX + LA_EX
        self.assertAlmostEqual(
            ccg.heading_error_deg(required, LOS_EX, LA_EX), 0.0, places=9
        )

    def test_heading_error_signed_difference(self):
        # Required heading 21.152 deg, current 10 deg: error +11.152 deg.
        err = ccg.heading_error_deg(10.0, LOS_EX, LA_EX)
        self.assertAlmostEqual(err, 11.1520, delta=0.01)

    def test_heading_error_wrap_positive_crossing_zero(self):
        # Required 20 deg vs heading 350 deg: wrapped error +30 deg.
        self.assertAlmostEqual(ccg.heading_error_deg(350.0, 0.0, 20.0), 30.0)

    def test_heading_error_wrap_negative(self):
        # Required -20 deg vs heading 10 deg: wrapped error -30 deg.
        self.assertAlmostEqual(ccg.heading_error_deg(10.0, 0.0, -20.0), -30.0)

    def test_heading_error_stays_within_bounds(self):
        for heading in (-540.0, -180.0, -91.0, 0.0, 91.0, 179.0, 540.0):
            err = ccg.heading_error_deg(heading, LOS_EX, LA_EX)
            self.assertTrue(-180.0 <= err <= 180.0)


class AssessmentTest(unittest.TestCase):
    def test_assessment_keys_exactly_documented(self):
        a = ccg.collision_course_assessment(
            -5000.0, 8660.254037844386, 0.0, 0.0, VT, 0.0, VP, VT
        )
        self.assertEqual(
            set(a.keys()),
            {"range_m", "los_angle_deg", "lead_angle_deg",
             "closing_speed_m_s", "time_to_go_s", "intercept_x",
             "intercept_y"},
        )

    def test_assessment_worked_geometry(self):
        # Spec illustrative geometry: target at origin moving +x, pursuer at
        # (-5000, 5000*sqrt(3)) so the range is exactly 10 000 m and the LOS
        # is at -60 deg (8660.25 is the rounded form of 5000*sqrt(3)).
        a = ccg.collision_course_assessment(
            -5000.0, 5000.0 * math.sqrt(3.0), 0.0, 0.0, VT, 0.0, VP, VT
        )
        self.assertAlmostEqual(a["range_m"], 10000.0, places=6)
        self.assertAlmostEqual(a["los_angle_deg"], -60.0, places=6)
        self.assertAlmostEqual(a["lead_angle_deg"], LA_EX, places=6)
        self.assertAlmostEqual(a["closing_speed_m_s"], VC_EX, places=6)
        self.assertAlmostEqual(a["time_to_go_s"], TGO_EX, places=6)
        # Intercept point lies ahead of the target along its velocity.
        self.assertAlmostEqual(a["intercept_x"], VT * TGO_EX, places=3)
        self.assertAlmostEqual(a["intercept_y"], 0.0, places=6)


class ConsistencyTest(unittest.TestCase):
    def test_meeting_point_identity_within_one_percent_of_range(self):
        # Collision triangle completion: the pursuer velocity at the lead
        # angle and the target velocity meet at the intercept point at t_go.
        # Lay the closing-side triangle out: pursuer at the origin, target at
        # range 10 000 m along the LOS (los 0 deg), target velocity beta off
        # the LOS line back toward the pursuer (compass heading los + 180 -
        # beta, i.e. the target closes the range at Vt * cos(beta)).
        beta = H_EX - LOS_EX  # 60 deg
        target_heading_compass = LOS_EX + 180.0 - beta  # 120 deg
        tvx = VT * math.cos(math.radians(target_heading_compass))
        tvy = VT * math.sin(math.radians(target_heading_compass))
        pursuer_heading = math.radians(LOS_EX + LA_EX)
        pax = VP * TGO_EX * math.cos(pursuer_heading)
        pay = VP * TGO_EX * math.sin(pursuer_heading)
        ix, iy = ccg.intercept_point(0.0, 0.0, R_EX, 0.0, tvx, tvy, TGO_EX)
        mismatch = math.hypot(pax - ix, pay - iy)
        self.assertLess(mismatch, 0.01 * R_EX)


class DeterminismTest(unittest.TestCase):
    def test_run_to_run_identical_floats(self):
        a = ccg.lead_angle(VP, VT, LOS_EX, H_EX)
        b = ccg.lead_angle(VP, VT, LOS_EX, H_EX)
        self.assertEqual(a, b)
        v1 = ccg.collision_course_assessment(
            -5000.0, 5000.0 * math.sqrt(3.0), 0.0, 0.0, VT, 0.0, VP, VT
        )
        v2 = ccg.collision_course_assessment(
            -5000.0, 5000.0 * math.sqrt(3.0), 0.0, 0.0, VT, 0.0, VP, VT
        )
        self.assertEqual(v1, v2)

    def test_no_random_import_in_logic(self):
        with open(ccg.__file__, "r", encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn("import random", source)
        self.assertNotIn("from random", source)


class WrapTest(unittest.TestCase):
    def test_wrap_180_property(self):
        for angle in range(-720, 721, 37):
            wrapped = ccg._wrap_180(float(angle))
            self.assertTrue(-180.0 <= wrapped <= 180.0)


if __name__ == "__main__":
    unittest.main()
