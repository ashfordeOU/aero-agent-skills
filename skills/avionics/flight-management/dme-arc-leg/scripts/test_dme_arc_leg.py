"""Contract test for the dme-arc-leg logic module.

Deterministic, offline, stdlib only. Run with:
    python3 scripts/test_dme_arc_leg.py

Covers the wave-38 spec validation list: worked-example anchors (12 nm
radius, radials 045 to 100), arc length over 360 degrees equals the
circumference 2*pi*r, chord over 180 degrees equals 2*r, bank-angle and
turn-radius inverse identity, the radial intercept sign truth table,
ValueError rejection of non-physical inputs, and determinism.
"""

import math
import unittest

import dme_arc_leg_logic as dme


class ArcLengthTests(unittest.TestCase):
    def test_worked_example_arc_length(self):
        # 12 nm radius, radials 045 to 100: 11.519 nm prep anchor.
        self.assertAlmostEqual(dme.arc_length_nm(12.0, 55.0), 11.519, delta=0.01)

    def test_full_circle_circumference(self):
        # arc_length(12, 360) equals 2*pi*r = 75.398 nm.
        self.assertAlmostEqual(dme.arc_length_nm(12.0, 360.0), 75.398, delta=0.001)

    def test_circumference_identity_and_zero_delta(self):
        # Identity: arc over 360 degrees is the circumference 2*pi*r.
        r = 8.5
        self.assertAlmostEqual(dme.arc_length_nm(r, 360.0), 2.0 * math.pi * r, places=9)
        self.assertEqual(dme.arc_length_nm(5.0, 0.0), 0.0)

    def test_nonphysical_inputs_valueerror(self):
        for bad_r in (0.0, -1.0):
            with self.assertRaises(ValueError):
                dme.arc_length_nm(bad_r, 55.0)
        for bad_d in (-1.0, 361.0, 540.0):
            with self.assertRaises(ValueError):
                dme.arc_length_nm(12.0, bad_d)

    def test_deterministic_float_output(self):
        self.assertEqual(dme.arc_length_nm(12.0, 55.0), dme.arc_length_nm(12.0, 55.0))
        self.assertIsInstance(dme.arc_length_nm(12.0, 55.0), float)


class PointOnArcTests(unittest.TestCase):
    def test_cardinal_radials(self):
        # Radial 000 is north (0, r); 090 is east (r, 0); 270 is west.
        x, y = dme.point_on_arc(12.0, 0.0)
        self.assertAlmostEqual(x, 0.0, places=9)
        self.assertAlmostEqual(y, 12.0, places=9)
        x, y = dme.point_on_arc(12.0, 90.0)
        self.assertAlmostEqual(x, 12.0, places=9)
        self.assertAlmostEqual(y, 0.0, places=9)
        x, y = dme.point_on_arc(12.0, 270.0)
        self.assertAlmostEqual(x, -12.0, places=9)
        self.assertAlmostEqual(y, 0.0, places=9)

    def test_worked_example_start_point(self):
        # Radial 045: (8.485, 8.485) nm prep anchor.
        x, y = dme.point_on_arc(12.0, 45.0)
        self.assertAlmostEqual(x, 8.485, delta=0.01)
        self.assertAlmostEqual(y, 8.485, delta=0.01)

    def test_worked_example_end_point(self):
        # Radial 100: (11.819, -2.084) nm prep anchor.
        x, y = dme.point_on_arc(12.0, 100.0)
        self.assertAlmostEqual(x, 11.819, delta=0.01)
        self.assertAlmostEqual(y, -2.084, delta=0.01)

    def test_nonphysical_inputs_valueerror(self):
        for bad_r in (0.0, -3.0):
            with self.assertRaises(ValueError):
                dme.point_on_arc(bad_r, 45.0)
        for bad_radial in (-5.0, 365.0):
            with self.assertRaises(ValueError):
                dme.point_on_arc(12.0, bad_radial)


class BankAngleTests(unittest.TestCase):
    def test_worked_example_bank_angle(self):
        # 180 kt on 12 nm radius: 2.25 deg prep anchor.
        self.assertAlmostEqual(dme.arc_bank_angle_deg(180.0, 12.0), 2.25, delta=0.01)

    def test_nonphysical_inputs_valueerror(self):
        with self.assertRaises(ValueError):
            dme.arc_bank_angle_deg(0.0, 12.0)
        with self.assertRaises(ValueError):
            dme.arc_bank_angle_deg(-120.0, 12.0)
        with self.assertRaises(ValueError):
            dme.arc_bank_angle_deg(180.0, 0.0)


class TurnRadiusTests(unittest.TestCase):
    def test_anchor_radius_at_20_deg_bank(self):
        # 180 kt at 20 deg bank: 1.297 nm prep anchor.
        self.assertAlmostEqual(dme.arc_turn_radius_nm(180.0, 20.0), 1.297, delta=0.001)

    def test_bank_inverse_identity_two_pairs(self):
        # Radius recovered from the bank angle that holds the input radius.
        bank = dme.arc_bank_angle_deg(180.0, 12.0)
        self.assertAlmostEqual(dme.arc_turn_radius_nm(180.0, bank), 12.0, delta=0.01)
        bank = dme.arc_bank_angle_deg(240.0, 8.0)
        self.assertAlmostEqual(dme.arc_turn_radius_nm(240.0, bank), 8.0, delta=0.01)

    def test_shallower_bank_larger_radius(self):
        r_small = dme.arc_turn_radius_nm(180.0, 25.0)
        r_large = dme.arc_turn_radius_nm(180.0, 15.0)
        self.assertGreater(r_large, r_small)

    def test_nonphysical_inputs_valueerror(self):
        for bad_bank in (0.0, 90.0, -20.0, 95.0):
            with self.assertRaises(ValueError):
                dme.arc_turn_radius_nm(180.0, bad_bank)
        with self.assertRaises(ValueError):
            dme.arc_turn_radius_nm(0.0, 20.0)


class ChordTests(unittest.TestCase):
    def test_worked_example_chord(self):
        # Chord across radials 045 to 100 at 12 nm: 11.082 nm prep anchor.
        self.assertAlmostEqual(dme.arc_chord_nm(12.0, 55.0), 11.082, delta=0.01)

    def test_diameter_and_quarter_identities(self):
        # Chord over 180 degrees equals 2*r; over 90 degrees, r*sqrt(2).
        self.assertAlmostEqual(dme.arc_chord_nm(12.0, 180.0), 24.0, places=9)
        self.assertAlmostEqual(dme.arc_chord_nm(12.0, 90.0), 12.0 * math.sqrt(2.0), places=9)

    def test_nonphysical_inputs_valueerror(self):
        with self.assertRaises(ValueError):
            dme.arc_chord_nm(-1.0, 55.0)
        with self.assertRaises(ValueError):
            dme.arc_chord_nm(12.0, 400.0)


class RadialInterceptTests(unittest.TestCase):
    def test_positive_clockwise_045_to_100(self):
        self.assertEqual(dme.radial_intercept_deg(45.0, 100.0), 55.0)

    def test_negative_counterclockwise_100_to_045(self):
        self.assertEqual(dme.radial_intercept_deg(100.0, 45.0), -55.0)

    def test_across_360_sign_truth_table(self):
        # 350 to 010 crosses north clockwise: +20; reverse: -20.
        self.assertEqual(dme.radial_intercept_deg(350.0, 10.0), 20.0)
        self.assertEqual(dme.radial_intercept_deg(10.0, 350.0), -20.0)

    def test_opposite_radial_and_same_radial(self):
        self.assertEqual(abs(dme.radial_intercept_deg(0.0, 180.0)), 180.0)
        self.assertEqual(dme.radial_intercept_deg(73.0, 73.0), 0.0)

    def test_radial_out_of_range_valueerror(self):
        for bad in (-10.0, 400.0):
            with self.assertRaises(ValueError):
                dme.radial_intercept_deg(bad, 45.0)


class GeometryDictTests(unittest.TestCase):
    def test_geometry_worked_example_fields(self):
        g = dme.dme_arc_geometry(12.0, 45.0, 100.0)
        for key in ("arc_length_nm", "chord_nm", "turn_angle_deg",
                    "start_point", "end_point", "midpoint_point"):
            self.assertIn(key, g)
        self.assertAlmostEqual(g["arc_length_nm"], 11.519, delta=0.01)
        self.assertAlmostEqual(g["chord_nm"], 11.082, delta=0.01)
        self.assertEqual(g["turn_angle_deg"], 55.0)
        self.assertAlmostEqual(g["start_point"][0], 8.485, delta=0.01)
        self.assertAlmostEqual(g["start_point"][1], 8.485, delta=0.01)
        self.assertAlmostEqual(g["end_point"][0], 11.819, delta=0.01)
        self.assertAlmostEqual(g["end_point"][1], -2.084, delta=0.01)

    def test_geometry_midpoint_at_half_turn(self):
        # Midpoint of the 045 to 100 arc sits at radial 072.5.
        g = dme.dme_arc_geometry(12.0, 45.0, 100.0)
        mx, my = g["midpoint_point"]
        self.assertAlmostEqual(mx, dme.point_on_arc(12.0, 72.5)[0], places=9)
        self.assertAlmostEqual(my, dme.point_on_arc(12.0, 72.5)[1], places=9)

    def test_geometry_full_circle_zero_chord(self):
        # Start and end coincide on a closed circle; chord collapses to 0.
        g = dme.dme_arc_geometry(12.0, 45.0, 45.0)
        self.assertEqual(g["turn_angle_deg"], 0.0)
        self.assertAlmostEqual(g["chord_nm"], 0.0, places=9)
        self.assertEqual(g["start_point"], g["end_point"])

    def test_geometry_deterministic(self):
        self.assertEqual(dme.dme_arc_geometry(12.0, 45.0, 100.0),
                         dme.dme_arc_geometry(12.0, 45.0, 100.0))

    def test_geometry_nonphysical_inputs_valueerror(self):
        with self.assertRaises(ValueError):
            dme.dme_arc_geometry(0.0, 45.0, 100.0)
        with self.assertRaises(ValueError):
            dme.dme_arc_geometry(12.0, -5.0, 100.0)
        with self.assertRaises(ValueError):
            dme.dme_arc_geometry(12.0, 45.0, 500.0)


if __name__ == "__main__":
    unittest.main()
