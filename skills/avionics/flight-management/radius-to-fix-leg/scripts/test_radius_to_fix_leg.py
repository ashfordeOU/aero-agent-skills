"""Offline deterministic contract test for the radius-to-fix leg module.

Runs with stdlib unittest only (no network, no external processes):

    python3 scripts/test_radius_to_fix_leg.py

Covers the wave-33 spec anchors: EF (0,0), XF (15,-15), inbound track
090, RIGHT, R = 15 NM -> center (0,-15), exit True, sweep 90.000 deg,
arc 23.562 NM, exit track 180.0 deg, chord 21.213 NM; the R = 8 NM,
60 deg arc anchor 8.3776 NM; the XF (15,15) rejection at distance
33.54 NM; the LEFT-turn mirror center (0, +15); RIGHT vs LEFT
complementary sweeps; ValueError rejection of non-physical inputs; and
run-to-run determinism.
"""

import math
import unittest

from radius_to_fix_leg_logic import (
    rf_arc_angle_deg,
    rf_arc_length_nm,
    rf_chord_nm,
    rf_exit_on_arc,
    rf_exit_track_deg,
    rf_leg_construct,
    rf_turn_center,
)

EF_CASE1 = (0.0, 0.0)
XF_CASE1 = (15.0, -15.0)
CENTER_CASE1 = (0.0, -15.0)
TRACK_CASE1 = 90.0
R_CASE1 = 15.0


class TurnCenterTests(unittest.TestCase):
    def test_turn_center_case1_right(self):
        cx, cy = rf_turn_center(EF_CASE1, TRACK_CASE1, R_CASE1, "RIGHT")
        self.assertAlmostEqual(cx, 0.0, places=9)
        self.assertAlmostEqual(cy, -15.0, places=9)

    def test_turn_center_case4_left_mirror(self):
        cx, cy = rf_turn_center(EF_CASE1, TRACK_CASE1, R_CASE1, "LEFT")
        self.assertAlmostEqual(cx, 0.0, places=9)
        self.assertAlmostEqual(cy, 15.0, places=9)

    def test_turn_center_cardinal_track_directions(self):
        # Northbound travel: right is east, left is west.  Southbound
        # travel: right is west.  All at R = 10 NM.
        cx, cy = rf_turn_center((0.0, 0.0), 0.0, 10.0, "RIGHT")
        self.assertAlmostEqual(cx, 10.0, places=9)
        self.assertAlmostEqual(cy, 0.0, places=9)
        cx, cy = rf_turn_center((0.0, 0.0), 0.0, 10.0, "LEFT")
        self.assertAlmostEqual(cx, -10.0, places=9)
        self.assertAlmostEqual(cy, 0.0, places=9)
        cx, cy = rf_turn_center((0.0, 0.0), 180.0, 10.0, "RIGHT")
        self.assertAlmostEqual(cx, -10.0, places=9)
        self.assertAlmostEqual(cy, 0.0, places=9)

    def test_turn_center_nonpositive_radius_raises(self):
        with self.assertRaises(ValueError):
            rf_turn_center(EF_CASE1, TRACK_CASE1, 0.0, "RIGHT")
        with self.assertRaises(ValueError):
            rf_turn_center(EF_CASE1, TRACK_CASE1, -5.0, "RIGHT")

    def test_turn_center_invalid_turn_raises(self):
        with self.assertRaises(ValueError):
            rf_turn_center(EF_CASE1, TRACK_CASE1, R_CASE1, "CLIMB")

    def test_turn_center_nonfinite_ef_raises(self):
        with self.assertRaises(ValueError):
            rf_turn_center((float("nan"), 0.0), TRACK_CASE1, R_CASE1, "RIGHT")
        with self.assertRaises(ValueError):
            rf_turn_center((0.0, float("inf")), TRACK_CASE1, R_CASE1, "RIGHT")


class ExitOnArcTests(unittest.TestCase):
    def test_exit_on_arc_case1_true(self):
        self.assertTrue(rf_exit_on_arc(CENTER_CASE1, XF_CASE1, R_CASE1))

    def test_exit_on_arc_case3_rejected_at_33_54(self):
        # XF (15,15) against center (0,-15) sits 33.54 NM away.
        self.assertAlmostEqual(
            math.hypot(15.0, 15.0 - (-15.0)), 33.54, places=2
        )
        self.assertFalse(rf_exit_on_arc(CENTER_CASE1, (15.0, 15.0), R_CASE1))

    def test_exit_on_arc_tolerance_band(self):
        # 5e-7 NM off the circle is inside the 1e-6 default tolerance.
        self.assertTrue(rf_exit_on_arc(CENTER_CASE1, (0.0, -30.0), 15.0))
        self.assertTrue(rf_exit_on_arc(CENTER_CASE1, (0.0, -30.0 + 5e-7), 15.0))
        self.assertFalse(rf_exit_on_arc(CENTER_CASE1, (0.0, -30.0 + 1e-4), 15.0))

    def test_exit_on_arc_nonfinite_xf_raises(self):
        with self.assertRaises(ValueError):
            rf_exit_on_arc(CENTER_CASE1, (float("nan"), 0.0), R_CASE1)


class ArcAngleTests(unittest.TestCase):
    def test_arc_angle_case1_sweep_90(self):
        sweep = rf_arc_angle_deg(CENTER_CASE1, EF_CASE1, XF_CASE1, "RIGHT")
        self.assertAlmostEqual(sweep, 90.0, places=9)

    def test_arc_angle_complementary_sweeps(self):
        # One center and one point pair: LEFT and RIGHT sweeps are
        # complementary and sum to 360 deg.  East-to-north arc: 90/270.
        left = rf_arc_angle_deg((0.0, 0.0), (10.0, 0.0), (0.0, 10.0), "LEFT")
        right = rf_arc_angle_deg((0.0, 0.0), (10.0, 0.0), (0.0, 10.0), "RIGHT")
        self.assertAlmostEqual(left, 90.0, places=9)
        self.assertAlmostEqual(right, 270.0, places=9)
        self.assertAlmostEqual(left + right, 360.0, places=9)
        # Antipodal pair: both directions sweep 180, again summing 360.
        left = rf_arc_angle_deg((0.0, 0.0), (10.0, 0.0), (-10.0, 0.0), "LEFT")
        right = rf_arc_angle_deg((0.0, 0.0), (10.0, 0.0), (-10.0, 0.0), "RIGHT")
        self.assertAlmostEqual(left, 180.0, places=9)
        self.assertAlmostEqual(right, 180.0, places=9)
        self.assertAlmostEqual(left + right, 360.0, places=9)

    def test_arc_angle_identical_fixes_zero(self):
        # EF == XF on the arc is a degenerate zero-length arc, 0 deg.
        self.assertEqual(
            rf_arc_angle_deg((0.0, 0.0), (10.0, 0.0), (10.0, 0.0), "RIGHT"), 0.0
        )
        self.assertEqual(
            rf_arc_angle_deg((0.0, 0.0), (10.0, 0.0), (10.0, 0.0), "LEFT"), 0.0
        )

    def test_arc_angle_right_near_full_circle_no_wrap(self):
        # XF at radial bearing 089 deg, 1 deg counter-clockwise of EF:
        # the RIGHT sweep approaches 360 deg and must never wrap to 0.
        xf = (
            10.0 * math.sin(math.radians(89.0)),
            10.0 * math.cos(math.radians(89.0)),
        )
        sweep = rf_arc_angle_deg((0.0, 0.0), (10.0, 0.0), xf, "RIGHT")
        self.assertGreater(sweep, 358.0)
        self.assertLess(sweep, 360.0)

    def test_arc_angle_nonphysical_inputs_raise(self):
        with self.assertRaises(ValueError):
            rf_arc_angle_deg(CENTER_CASE1, EF_CASE1, XF_CASE1, "REVERSE")
        with self.assertRaises(ValueError):
            rf_arc_angle_deg((float("inf"), 0.0), EF_CASE1, XF_CASE1, "RIGHT")


class ArcLengthTests(unittest.TestCase):
    def test_arc_length_case1_quarter_circle(self):
        self.assertAlmostEqual(rf_arc_length_nm(15.0, 90.0), 23.562, places=3)

    def test_arc_length_case2_eight_nm_sixty_deg(self):
        self.assertAlmostEqual(rf_arc_length_nm(8.0, 60.0), 8.3776, places=4)

    def test_arc_length_full_circle(self):
        self.assertAlmostEqual(rf_arc_length_nm(10.0, 360.0), 62.8319, places=4)

    def test_arc_length_zero_sweep(self):
        self.assertEqual(rf_arc_length_nm(15.0, 0.0), 0.0)

    def test_arc_length_nonphysical_inputs_raise(self):
        with self.assertRaises(ValueError):
            rf_arc_length_nm(0.0, 90.0)
        with self.assertRaises(ValueError):
            rf_arc_length_nm(15.0, -10.0)


class ExitTrackTests(unittest.TestCase):
    def test_exit_track_case1_right_south_left_north(self):
        # Radial east of the case-1 center: RIGHT exits south, LEFT
        # exits north (perpendicular on the turn side of the radius).
        self.assertAlmostEqual(
            rf_exit_track_deg(CENTER_CASE1, XF_CASE1, "RIGHT"), 180.0, places=9
        )
        self.assertAlmostEqual(
            rf_exit_track_deg(CENTER_CASE1, XF_CASE1, "LEFT"), 0.0, places=9
        )

    def test_exit_track_half_circle_right_is_inbound_plus_180(self):
        # 180 deg RIGHT arc off inbound 090: XF at (0,-30) about the
        # case-1 center, exit track 270 = inbound + 180.
        track = rf_exit_track_deg(CENTER_CASE1, (0.0, -30.0), "RIGHT")
        self.assertAlmostEqual(track, 270.0, places=9)
        self.assertAlmostEqual(track, (TRACK_CASE1 + 180.0) % 360.0, places=9)

    def test_exit_track_normalization_across_zero(self):
        # Radial bearing 350 deg: RIGHT adds 90 (440 wraps to 80 deg).
        xf = (
            10.0 * math.sin(math.radians(350.0)),
            10.0 * math.cos(math.radians(350.0)),
        )
        self.assertAlmostEqual(
            rf_exit_track_deg((0.0, 0.0), xf, "RIGHT"), 80.0, places=9
        )
        self.assertAlmostEqual(
            rf_exit_track_deg((0.0, 0.0), xf, "LEFT"), 260.0, places=9
        )

    def test_exit_track_invalid_turn_raises(self):
        with self.assertRaises(ValueError):
            rf_exit_track_deg(CENTER_CASE1, XF_CASE1, "U-TURN")


class ChordTests(unittest.TestCase):
    def test_chord_case1(self):
        self.assertAlmostEqual(rf_chord_nm(EF_CASE1, XF_CASE1), 21.213, places=3)

    def test_chord_identical_fixes_zero(self):
        self.assertEqual(rf_chord_nm((5.0, 5.0), (5.0, 5.0)), 0.0)

    def test_chord_nonfinite_raises(self):
        with self.assertRaises(ValueError):
            rf_chord_nm(EF_CASE1, (15.0, float("nan")))


class LegConstructTests(unittest.TestCase):
    def test_leg_construct_case1_full_dict(self):
        leg = rf_leg_construct(EF_CASE1, XF_CASE1, TRACK_CASE1, R_CASE1, "RIGHT")
        self.assertAlmostEqual(leg["center_nm"][0], 0.0, places=9)
        self.assertAlmostEqual(leg["center_nm"][1], -15.0, places=9)
        self.assertTrue(leg["exit_on_arc"])
        self.assertAlmostEqual(leg["sweep_deg"], 90.0, places=9)
        self.assertAlmostEqual(leg["arc_length_nm"], 23.562, places=3)
        self.assertAlmostEqual(leg["exit_track_deg"], 180.0, places=9)
        self.assertAlmostEqual(leg["chord_nm"], 21.213, places=3)
        self.assertTrue(leg["valid"])

    def test_leg_construct_case3_rejected(self):
        leg = rf_leg_construct(EF_CASE1, (15.0, 15.0), TRACK_CASE1, R_CASE1, "RIGHT")
        self.assertFalse(leg["exit_on_arc"])
        self.assertFalse(leg["valid"])

    def test_leg_construct_left_valid_on_arc(self):
        # LEFT about center (0,+15): XF (15,15) lies on the circle and
        # the sweep is 90 deg counter-clockwise, exit track north.
        leg = rf_leg_construct(EF_CASE1, (15.0, 15.0), TRACK_CASE1, R_CASE1, "LEFT")
        self.assertAlmostEqual(leg["center_nm"][0], 0.0, places=9)
        self.assertAlmostEqual(leg["center_nm"][1], 15.0, places=9)
        self.assertTrue(leg["exit_on_arc"])
        self.assertAlmostEqual(leg["sweep_deg"], 90.0, places=9)
        self.assertAlmostEqual(leg["exit_track_deg"], 0.0, places=9)
        self.assertTrue(leg["valid"])

    def test_leg_construct_keys_exactly_documented(self):
        leg = rf_leg_construct(EF_CASE1, XF_CASE1, TRACK_CASE1, R_CASE1, "RIGHT")
        self.assertEqual(
            set(leg.keys()),
            {"center_nm", "exit_on_arc", "sweep_deg", "arc_length_nm",
             "exit_track_deg", "chord_nm", "valid"},
        )

    def test_leg_construct_deterministic(self):
        first = rf_leg_construct(EF_CASE1, XF_CASE1, TRACK_CASE1, R_CASE1, "RIGHT")
        second = rf_leg_construct(EF_CASE1, XF_CASE1, TRACK_CASE1, R_CASE1, "RIGHT")
        self.assertEqual(first, second)
        self.assertEqual(
            rf_arc_angle_deg(CENTER_CASE1, EF_CASE1, XF_CASE1, "RIGHT"),
            rf_arc_angle_deg(CENTER_CASE1, EF_CASE1, XF_CASE1, "RIGHT"),
        )

    def test_leg_construct_nonphysical_inputs_raise(self):
        with self.assertRaises(ValueError):
            rf_leg_construct(EF_CASE1, XF_CASE1, TRACK_CASE1, 0.0, "RIGHT")
        with self.assertRaises(ValueError):
            rf_leg_construct(EF_CASE1, XF_CASE1, TRACK_CASE1, R_CASE1, "LEFT_TURN")
        with self.assertRaises(ValueError):
            rf_leg_construct(
                EF_CASE1, (float("nan"), 0.0), TRACK_CASE1, R_CASE1, "RIGHT"
            )


if __name__ == "__main__":
    unittest.main()
