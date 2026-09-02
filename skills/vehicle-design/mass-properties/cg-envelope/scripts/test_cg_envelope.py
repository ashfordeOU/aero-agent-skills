#!/usr/bin/env python3
"""Gate 3 contract test: CG envelope analysis logic.

Exercises scripts/cg_envelope_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - cg station from
component weights and arms (x and z), forward/aft limit verdicts,
static margin from the neutral point and the mean aerodynamic chord
with the minimum-margin verdict, convex envelope polygon membership
with the violated limit, cg excursion across a fuel burn, and
ValueError on invalid inputs (mismatch, empty, zero total weight,
negative weight, reversed limits, non-positive MAC, non-convex or
degenerate polygon, negative minimum margin).

Hand-computed expected values:
- cg_position([100, 200], [10, 20]) = (100*10 + 200*20) / 300
  = 5000 / 300 = 16.6666...
- cg_position_2d([100, 200], [10, 20], [5, 1]):
  x_cg = 16.6666..., z_cg = (100*5 + 200*1) / 300 = 700 / 300
  = 2.3333...
- cg_limits_verdict: cg 10 with limits 8..12 is within; cg 7.9 is
  forward; cg 12.1 is aft.
- static_margin(x_np 17.0, x_cg 15.0, mac 2.0) = (17 - 15) / 2 = 1.0
  (pass); x_cg 16.9 gives (17 - 16.9) / 2 = 0.05 (pass at the
  boundary); x_cg 17.1 gives (17 - 17.1) / 2 = -0.05 (fail).
- point_in_envelope rectangle [(10, 40000), (16, 40000),
  (16, 60000), (10, 60000)]: (13, 50000) inside; (9, 50000) is
  forward of the forward boundary at x = 10; (17, 50000) is aft of
  the aft boundary at x = 16; (13, 65000) is above the envelope, x
  extent midpoint is 13, so aft by the tiebreak rule.
- point_in_envelope trapezoid [(10, 40000), (16, 40000),
  (14, 60000), (11, 60000)]: at weight 50000 the forward boundary
  edge (11, 60000)-(10, 40000) crosses x = 11 + 0.5*(10 - 11)
  = 10.5 and the aft boundary edge (16, 40000)-(14, 60000) crosses
  x = 16 + 0.5*(14 - 16) = 15; (12, 50000) is inside,
  (10.4, 50000) is forward, (15.1, 50000) is aft.
- cg_excursion([10000, 3000, 2000], [10000, 1000, 2000],
  [14, 16, 20]): before, total 15000 and moment 10000*14 + 3000*16
  + 2000*20 = 228000, cg = 228000 / 15000 = 15.2; after, total 13000
  and moment 10000*14 + 1000*16 + 2000*20 = 196000, cg = 196000 /
  13000 = 15.07692...; shift = 15.07692... - 15.2 = -0.12307...
  (the CG moves forward as the aft fuel burns).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cg_envelope_logic as cg  # noqa: E402

RECT = [(10.0, 40000.0), (16.0, 40000.0), (16.0, 60000.0), (10.0, 60000.0)]
TRAP = [(10.0, 40000.0), (16.0, 40000.0), (14.0, 60000.0), (11.0, 60000.0)]


class CgPositionTest(unittest.TestCase):
    def test_known_two_weight_case(self):
        # (100*10 + 200*20) / 300 = 5000 / 300 = 16.6666...
        self.assertAlmostEqual(cg.cg_position([100.0, 200.0], [10.0, 20.0]), 16.666666666666668)

    def test_single_weight_cg_is_its_arm(self):
        self.assertAlmostEqual(cg.cg_position([50.0], [7.0]), 7.0)

    def test_negative_arm_is_allowed(self):
        # Station ahead of the datum: (100*-2 + 300*4) / 400 = 1000 / 400 = 2.5
        self.assertAlmostEqual(cg.cg_position([100.0, 300.0], [-2.0, 4.0]), 2.5)

    def test_2d_cg(self):
        # x_cg 16.6666..., z_cg (100*5 + 200*1) / 300 = 700 / 300 = 2.3333...
        x_cg, z_cg = cg.cg_position_2d([100.0, 200.0], [10.0, 20.0], [5.0, 1.0])
        self.assertAlmostEqual(x_cg, 16.666666666666668)
        self.assertAlmostEqual(z_cg, 2.3333333333333335)

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            cg.cg_position([100.0, 200.0], [10.0])
        with self.assertRaises(ValueError):
            cg.cg_position_2d([100.0, 200.0], [10.0], [5.0, 1.0])

    def test_empty_lists_raise(self):
        with self.assertRaises(ValueError):
            cg.cg_position([], [])

    def test_zero_total_weight_raises(self):
        with self.assertRaises(ValueError):
            cg.cg_position([0.0, 0.0], [10.0, 20.0])

    def test_negative_weight_raises(self):
        with self.assertRaises(ValueError):
            cg.cg_position([100.0, -5.0], [10.0, 20.0])


class CgLimitsVerdictTest(unittest.TestCase):
    def test_within_and_violations(self):
        self.assertEqual(cg.cg_limits_verdict(10.0, 8.0, 12.0), "within")
        self.assertEqual(cg.cg_limits_verdict(8.0, 8.0, 12.0), "within")
        self.assertEqual(cg.cg_limits_verdict(12.0, 8.0, 12.0), "within")
        self.assertEqual(cg.cg_limits_verdict(7.9, 8.0, 12.0), "forward")
        self.assertEqual(cg.cg_limits_verdict(12.1, 8.0, 12.0), "aft")

    def test_reversed_limits_raise(self):
        with self.assertRaises(ValueError):
            cg.cg_limits_verdict(10.0, 12.0, 8.0)


class StaticMarginTest(unittest.TestCase):
    def test_known_margins(self):
        # (17 - 15) / 2 = 1.0
        margin, ok = cg.static_margin_verdict(17.0, 15.0, 2.0)
        self.assertAlmostEqual(margin, 1.0)
        self.assertTrue(ok)
        # (17 - 16.9) / 2 = 0.05, boundary inclusive
        margin, ok = cg.static_margin_verdict(17.0, 16.9, 2.0)
        self.assertAlmostEqual(margin, 0.05)
        self.assertTrue(ok)
        # (17 - 17.1) / 2 = -0.05
        margin, ok = cg.static_margin_verdict(17.0, 17.1, 2.0)
        self.assertAlmostEqual(margin, -0.05)
        self.assertFalse(ok)

    def test_custom_minimum(self):
        # (17 - 15.5) / 2 = 0.75 >= 0.2 passes, >= 0.8 fails
        margin, ok = cg.static_margin_verdict(17.0, 15.5, 2.0, min_margin=0.2)
        self.assertAlmostEqual(margin, 0.75)
        self.assertTrue(ok)
        _, ok = cg.static_margin_verdict(17.0, 15.5, 2.0, min_margin=0.8)
        self.assertFalse(ok)

    def test_nonpositive_mac_raises(self):
        with self.assertRaises(ValueError):
            cg.static_margin(17.0, 15.0, 0.0)
        with self.assertRaises(ValueError):
            cg.static_margin(17.0, 15.0, -2.0)
        with self.assertRaises(ValueError):
            cg.static_margin_verdict(17.0, 15.0, 0.0)

    def test_negative_min_margin_raises(self):
        with self.assertRaises(ValueError):
            cg.static_margin_verdict(17.0, 15.0, 2.0, min_margin=-0.1)


class PointInEnvelopeTest(unittest.TestCase):
    def test_rectangle_inside(self):
        # (13, 50000) is inside the 10..16 by 40000..60000 rectangle
        self.assertEqual(cg.point_in_envelope(RECT, (13.0, 50000.0)), (True, None))

    def test_rectangle_on_boundary_inside(self):
        # On the forward boundary x = 10 is inside (limits inclusive)
        self.assertEqual(cg.point_in_envelope(RECT, (10.0, 50000.0)), (True, None))

    def test_rectangle_forward_violation(self):
        # At weight 50000 the forward boundary is x = 10; 9 is forward
        self.assertEqual(cg.point_in_envelope(RECT, (9.0, 50000.0)), (False, "forward"))

    def test_rectangle_aft_violation(self):
        # At weight 50000 the aft boundary is x = 16; 17 is aft
        self.assertEqual(cg.point_in_envelope(RECT, (17.0, 50000.0)), (False, "aft"))

    def test_rectangle_above_envelope(self):
        # (13, 65000) is above the envelope; x extent midpoint is 13,
        # the tiebreak rule reports aft
        self.assertEqual(cg.point_in_envelope(RECT, (13.0, 65000.0)), (False, "aft"))

    def test_trapezoid_inside(self):
        # At weight 50000 the forward boundary crosses x = 10.5 and
        # the aft boundary crosses x = 15; (12, 50000) is inside
        self.assertEqual(cg.point_in_envelope(TRAP, (12.0, 50000.0)), (True, None))

    def test_trapezoid_forward_violation(self):
        # (10.4, 50000) is ahead of the forward boundary at x = 10.5
        self.assertEqual(cg.point_in_envelope(TRAP, (10.4, 50000.0)), (False, "forward"))

    def test_trapezoid_aft_violation(self):
        # (15.1, 50000) is behind the aft boundary at x = 15
        self.assertEqual(cg.point_in_envelope(TRAP, (15.1, 50000.0)), (False, "aft"))

    def test_degenerate_polygons_raise(self):
        with self.assertRaises(ValueError):
            cg.point_in_envelope([], (13.0, 50000.0))
        with self.assertRaises(ValueError):
            cg.point_in_envelope([(10.0, 40000.0), (16.0, 40000.0)], (13.0, 50000.0))
        # Collinear vertices: zero area
        with self.assertRaises(ValueError):
            cg.point_in_envelope(
                [(10.0, 40000.0), (13.0, 50000.0), (16.0, 60000.0)], (13.0, 50000.0)
            )

    def test_nonconvex_polygon_raises(self):
        # Concave dart: the reflex vertex makes the cross products
        # change sign
        with self.assertRaises(ValueError):
            cg.point_in_envelope(
                [(10.0, 40000.0), (16.0, 40000.0), (10.0, 60000.0), (14.0, 60000.0)],
                (13.0, 50000.0),
            )


class CgExcursionTest(unittest.TestCase):
    def test_fuel_burn_shifts_cg_forward(self):
        # before cg 15.2, after cg 196000/13000 = 15.07692..., shift
        # -0.12307... (aft fuel burns, the cg moves forward)
        before, after, shift = cg.cg_excursion(
            [10000.0, 3000.0, 2000.0], [10000.0, 1000.0, 2000.0], [14.0, 16.0, 20.0]
        )
        self.assertAlmostEqual(before, 15.2)
        self.assertAlmostEqual(after, 15.076923076923077)
        self.assertAlmostEqual(shift, -0.12307692307692294)

    def test_no_fuel_change_no_shift(self):
        before, after, shift = cg.cg_excursion(
            [10000.0, 3000.0], [10000.0, 3000.0], [14.0, 16.0]
        )
        self.assertAlmostEqual(before, after)
        self.assertAlmostEqual(shift, 0.0)

    def test_excursion_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cg.cg_excursion([10000.0, 3000.0], [10000.0], [14.0, 16.0])
        with self.assertRaises(ValueError):
            cg.cg_excursion([0.0, 0.0], [0.0, 0.0], [14.0, 16.0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
