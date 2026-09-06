"""Contract test for the landing-gear-layout leaf (vehicle-design/sizing).

Exercises the SKILL.md workflow end to end. Step 2 of the SKILL.md
workflow, the tipback angle check at the aft CG limit about the main
gear contact (tipback_angle on the aft-CG margin over the CG height), is
exercised by the test_tipback_angle_* methods. Step 3, the tail strike
clearance angle at rotation computed with tail_strike_clearance_angle
and the comparison against the tipback angle and the ROTATION_REF_DEG
unstick reference, is exercised by the test_tail_strike_* methods. Step
4, the lateral turnover checks from the wheel track with the simplified
main gear pair lateral_turnover_angle and the nose-to-main tricycle
diagonal refinement lateral_turnover_tricycle_angle at the forward CG
limit, is exercised by the test_lateral_* and test_tricycle_* methods.
Step 5, the nose gear load fraction band across the CG travel from
nose_gear_static_load_fraction at the forward and aft CG limits with
the band verdicts against NOSE_FRACTION_MIN and NOSE_FRACTION_MAX, is
exercised by the test_nose_fraction_* methods. Step 6, the main gear
position check that closes the layout and the deterministic offline run
of this contract test, is exercised by test_main_gear_position_check_*,
test_determinism_* and test_contract_workflow_*.

All numeric asserts are order-safe: assertAlmostEqual with an explicit
delta or math.isclose, never exact float equality on computed sums or
products. Determinism asserts compare two runs of the identical
computation, which is exact by construction. Worked-example magnitudes
come from the wave-42 prep anchor: tipback_angle 28.1786 deg, tail
strike clearance angle 16.2602 deg with a 6.2602 deg rotation margin,
lateral_turnover_angle 40.7462 deg, tricycle diagonal angle 39.7567 deg
at the forward CG limit, nose gear load fraction 0.266667 at the
forward CG limit and 0.1 at the aft CG limit.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from landing_gear_layout_logic import (
    NOSE_FRACTION_MAX,
    NOSE_FRACTION_MIN,
    ROTATION_REF_DEG,
    lateral_turnover_angle,
    lateral_turnover_tricycle_angle,
    nose_gear_static_load_fraction,
    tail_strike_clearance_angle,
    tipback_angle,
)

H_CG = 2.8
X_NG = 3.0
X_MG = 18.0
X_TAIL = 30.0
H_TAIL = 3.5
TRACK = 6.5
X_CG_FWD = 14.0
X_CG_AFT = 16.5
WHEELBASE = X_MG - X_NG


class LandingGearLayoutContractTests(unittest.TestCase):
    """Contract tests for the landing-gear-layout arrangement geometry."""

    # ---- Step 2 of the SKILL.md workflow: tipback angle at the aft CG limit

    def test_tipback_angle_worked_example(self):
        """Step 2 tipback angle check: the aft-CG margin of 1.5 m over
        the 2.8 m CG height gives atan(1.5 / 2.8) = 28.1786 deg, inside
        the prep anchor band."""
        self.assertAlmostEqual(
            tipback_angle(H_CG, X_MG, X_CG_AFT), 28.17859010995917, delta=1e-4
        )
        self.assertAlmostEqual(
            tipback_angle(H_CG, X_MG, X_CG_AFT),
            math.degrees(math.atan(1.5 / H_CG)),
            delta=1e-9,
        )

    def test_tipback_angle_margin_doubling_doubles_tangent(self):
        """Step 2 tipback angle check: doubling the aft-CG margin to
        3.0 m at fixed h_cg doubles tan(theta_tip), giving
        atan(3.0 / 2.8) near 46.97 deg."""
        theta1 = tipback_angle(H_CG, X_MG, X_CG_AFT)
        theta2 = tipback_angle(H_CG, X_MG, 15.0)
        self.assertTrue(
            math.isclose(
                math.tan(math.radians(theta2)),
                2.0 * math.tan(math.radians(theta1)),
                rel_tol=1e-9,
            )
        )
        self.assertAlmostEqual(theta2, 46.97493401088198, delta=1e-4)
        self.assertAlmostEqual(
            theta2, math.degrees(math.atan(3.0 / H_CG)), delta=1e-9
        )

    def test_tipback_angle_tends_to_zero_at_contact_station(self):
        """Step 2 tipback angle check: the angle tends to 0 as the aft
        CG approaches the main gear contact station."""
        near = tipback_angle(H_CG, X_MG, 17.9999)
        self.assertTrue(math.isclose(near, 0.0, abs_tol=1e-2))
        self.assertLess(near, tipback_angle(H_CG, X_MG, 17.0))

    def test_tipback_angle_valueerror_nonpositive_cg_height(self):
        """Step 2 tipback angle check: a non-positive CG height raises
        ValueError rather than returning a plausible angle."""
        for bad in (0.0, -2.8):
            with self.assertRaises(ValueError):
                tipback_angle(bad, X_MG, X_CG_AFT)

    def test_tipback_angle_valueerror_aft_cg_not_forward_of_main(self):
        """Step 2 tipback angle check: an aft CG limit at or behind the
        main gear contact is a statically tipped arrangement and raises
        ValueError."""
        for bad in (X_MG, X_MG + 0.5, 20.0):
            with self.assertRaises(ValueError):
                tipback_angle(H_CG, X_MG, bad)

    # ---- Step 3 of the SKILL.md workflow: tail strike clearance at rotation

    def test_tail_strike_clearance_angle_worked_example(self):
        """Step 3 tail strike clearance at rotation: the tail cone arm
        of 12 m at 3.5 m contact height gives atan(3.5 / 12.0) =
        16.2602 deg, below the tipback angle so rotation is
        tail-strike limited."""
        theta_ts = tail_strike_clearance_angle(H_TAIL, X_TAIL, X_MG)
        self.assertAlmostEqual(theta_ts, 16.26020470831196, delta=1e-4)
        self.assertAlmostEqual(
            theta_ts, math.degrees(math.atan(H_TAIL / (X_TAIL - X_MG))), delta=1e-9
        )
        self.assertLess(theta_ts, tipback_angle(H_CG, X_MG, X_CG_AFT))

    def test_tail_strike_angle_height_doubling_doubles_tangent(self):
        """Step 3 tail strike clearance at rotation: doubling the tail
        contact height to 7.0 m at the fixed 12 m arm doubles
        tan(theta_ts), atan(7.0 / 12.0) near 30.26 deg."""
        theta1 = tail_strike_clearance_angle(H_TAIL, X_TAIL, X_MG)
        theta2 = tail_strike_clearance_angle(7.0, X_TAIL, X_MG)
        self.assertTrue(
            math.isclose(
                math.tan(math.radians(theta2)),
                2.0 * math.tan(math.radians(theta1)),
                rel_tol=1e-9,
            )
        )
        self.assertAlmostEqual(theta2, 30.256437163529263, delta=1e-4)

    def test_tail_strike_angle_grows_with_contact_height(self):
        """Step 3 tail strike clearance at rotation: the angle vanishes
        as the tail contact height tends to 0 and grows with
        h_tail_contact at the fixed arm."""
        tiny = tail_strike_clearance_angle(1e-6, X_TAIL, X_MG)
        self.assertTrue(math.isclose(tiny, 0.0, abs_tol=1e-3))
        self.assertLess(
            tail_strike_clearance_angle(2.0, X_TAIL, X_MG),
            tail_strike_clearance_angle(4.0, X_TAIL, X_MG),
        )

    def test_tail_strike_angle_rotation_margin_vs_reference(self):
        """Step 3 tail strike clearance at rotation: the 10.0 deg unstick
        rotation reference leaves a 6.2602 deg rotation margin before
        the tail cone touches the ground."""
        margin = tail_strike_clearance_angle(H_TAIL, X_TAIL, X_MG) - ROTATION_REF_DEG
        self.assertAlmostEqual(margin, 6.26020470831196, delta=1e-4)
        self.assertEqual(ROTATION_REF_DEG, 10.0)

    def test_tail_strike_angle_valueerror_nonpositive_contact_height(self):
        """Step 3 tail strike clearance at rotation: a non-positive tail
        contact height raises ValueError."""
        for bad in (0.0, -3.5):
            with self.assertRaises(ValueError):
                tail_strike_clearance_angle(bad, X_TAIL, X_MG)

    def test_tail_strike_angle_valueerror_tail_not_aft_of_main(self):
        """Step 3 tail strike clearance at rotation: a tail station at or
        forward of the main gear contact raises ValueError."""
        for bad in (X_MG, 17.0, 10.0):
            with self.assertRaises(ValueError):
                tail_strike_clearance_angle(H_TAIL, bad, X_MG)

    # ---- Step 4 of the SKILL.md workflow: lateral turnover from the wheel track

    def test_lateral_turnover_angle_worked_example(self):
        """Step 4 lateral turnover check: the main gear pair rolls on
        2 * h_cg / track = 0.861538, atan 40.7462 deg, inside the 40-50
        deg transport band."""
        theta_lat = lateral_turnover_angle(H_CG, TRACK)
        self.assertAlmostEqual(theta_lat, 40.74616356388081, delta=1e-4)
        self.assertAlmostEqual(
            theta_lat, math.degrees(math.atan(2.0 * H_CG / TRACK)), delta=1e-9
        )
        self.assertGreaterEqual(theta_lat, 40.0)
        self.assertLessEqual(theta_lat, 50.0)

    def test_lateral_turnover_angle_track_doubling_halves_tangent(self):
        """Step 4 lateral turnover check: doubling the wheel track to
        13.0 m halves tan(theta_lat), atan(5.6 / 13.0) near 23.30 deg."""
        theta1 = lateral_turnover_angle(H_CG, TRACK)
        theta2 = lateral_turnover_angle(H_CG, 13.0)
        self.assertTrue(
            math.isclose(
                math.tan(math.radians(theta2)),
                0.5 * math.tan(math.radians(theta1)),
                rel_tol=1e-9,
            )
        )
        self.assertAlmostEqual(theta2, 23.30489053920311, delta=1e-4)

    def test_lateral_turnover_angle_valueerror_nonpositive(self):
        """Step 4 lateral turnover check: non-positive CG height or
        wheel track raises ValueError."""
        for bad in (0.0, -2.8):
            with self.assertRaises(ValueError):
                lateral_turnover_angle(bad, TRACK)
        for bad in (0.0, -6.5):
            with self.assertRaises(ValueError):
                lateral_turnover_angle(H_CG, bad)

    def test_tricycle_turnover_angle_worked_example_forward_cg(self):
        """Step 4 tricycle diagonal refinement: at the forward CG limit
        the perpendicular diagonal arm of 2.32908 m gives atan
        39.7567 deg, marginally below the main-pair 40.7462 deg value,
        so the diagonal check binds laterally."""
        theta_diag = lateral_turnover_tricycle_angle(H_CG, X_CG_FWD, X_MG, X_NG, TRACK)
        self.assertAlmostEqual(theta_diag, 39.756669023138734, delta=1e-4)
        self.assertLess(theta_diag, lateral_turnover_angle(H_CG, TRACK))

    def test_tricycle_turnover_angle_grows_as_cg_moves_aft(self):
        """Step 4 tricycle diagonal refinement: the diagonal arm grows
        as the CG moves aft within the wheelbase, so the angle at the
        aft CG limit exceeds the forward CG value."""
        fwd = lateral_turnover_tricycle_angle(H_CG, X_CG_FWD, X_MG, X_NG, TRACK)
        aft = lateral_turnover_tricycle_angle(H_CG, X_CG_AFT, X_MG, X_NG, TRACK)
        mid = lateral_turnover_tricycle_angle(H_CG, 10.5, X_MG, X_NG, TRACK)
        self.assertLess(mid, fwd)
        self.assertLess(fwd, aft)
        self.assertAlmostEqual(aft, 45.594032414450325, delta=1e-4)

    def test_tricycle_turnover_angle_tends_to_zero_at_nose_station(self):
        """Step 4 tricycle diagonal refinement: the angle tends to 0 as
        the CG station approaches the nose gear station."""
        near = lateral_turnover_tricycle_angle(H_CG, X_NG + 0.001, X_MG, X_NG, TRACK)
        self.assertTrue(math.isclose(near, 0.0, abs_tol=1e-1))
        self.assertLess(
            near,
            lateral_turnover_tricycle_angle(H_CG, X_NG + 1.0, X_MG, X_NG, TRACK),
        )

    def test_tricycle_turnover_angle_valueerror_cg_outside_wheelbase(self):
        """Step 4 tricycle diagonal refinement: a CG station at or
        outside the nose-to-main station pair raises ValueError."""
        for bad in (X_NG, X_MG, 2.0, 19.0):
            with self.assertRaises(ValueError):
                lateral_turnover_tricycle_angle(H_CG, bad, X_MG, X_NG, TRACK)

    def test_tricycle_turnover_angle_valueerror_nonpositive(self):
        """Step 4 tricycle diagonal refinement: non-positive CG height
        or wheel track raises ValueError."""
        for bad in (0.0, -2.8):
            with self.assertRaises(ValueError):
                lateral_turnover_tricycle_angle(bad, X_CG_FWD, X_MG, X_NG, TRACK)
        for bad in (0.0, -6.5):
            with self.assertRaises(ValueError):
                lateral_turnover_tricycle_angle(H_CG, X_CG_FWD, X_MG, X_NG, bad)

    # ---- Step 5 of the SKILL.md workflow: nose gear load fraction band

    def test_nose_fraction_forward_cg_limit_worked_example(self):
        """Step 5 nose gear load fraction band: at the forward CG limit
        the moment balance about the main gear contact gives (18 - 14) /
        15 = 0.266667, above the 0.20 band top, so the forward CG limit
        fraction fails its band verdict."""
        frac_fwd = nose_gear_static_load_fraction(X_CG_FWD, X_MG, X_NG)
        self.assertAlmostEqual(frac_fwd, 0.26666666666666666, delta=1e-9)
        self.assertAlmostEqual(frac_fwd, (X_MG - X_CG_FWD) / WHEELBASE, delta=1e-12)
        self.assertGreater(frac_fwd, NOSE_FRACTION_MAX)

    def test_nose_fraction_aft_cg_limit_worked_example(self):
        """Step 5 nose gear load fraction band: at the aft CG limit the
        fraction is (18 - 16.5) / 15 = 0.1, inside the 5-20 percent
        typical band, so the aft CG limit fraction passes its verdict."""
        frac_aft = nose_gear_static_load_fraction(X_CG_AFT, X_MG, X_NG)
        self.assertAlmostEqual(frac_aft, 0.1, delta=1e-9)
        self.assertGreaterEqual(frac_aft, NOSE_FRACTION_MIN)
        self.assertLessEqual(frac_aft, NOSE_FRACTION_MAX)

    def test_nose_fraction_aft_limit_below_forward_limit(self):
        """Step 5 nose gear load fraction band: the nose gear carries
        more when the CG is forward, so the aft CG limit fraction sits
        below the forward CG limit fraction."""
        frac_fwd = nose_gear_static_load_fraction(X_CG_FWD, X_MG, X_NG)
        frac_aft = nose_gear_static_load_fraction(X_CG_AFT, X_MG, X_NG)
        self.assertLess(frac_aft, frac_fwd)

    def test_nose_fraction_complements_main_gear_share(self):
        """Step 5 nose gear load fraction band: the two fractions
        complement the main gear share to 1 at both CG limits, and the
        main gear share rises to 0.9 at the aft CG limit."""
        for x_cg in (X_CG_FWD, X_CG_AFT):
            frac = nose_gear_static_load_fraction(x_cg, X_MG, X_NG)
            main_share = (x_cg - X_NG) / WHEELBASE
            self.assertTrue(math.isclose(frac + main_share, 1.0, rel_tol=1e-12))
            self.assertTrue(math.isclose(1.0 - frac, main_share, rel_tol=1e-12))
        self.assertAlmostEqual(
            nose_gear_static_load_fraction(X_CG_AFT, X_MG, X_NG), 0.1, delta=1e-12
        )

    def test_nose_fraction_mid_wheelbase_and_aft_of_mid(self):
        """Step 5 nose gear load fraction band: a mid-wheelbase CG at
        10.5 m gives exactly 0.5, and a CG moved aft of mid-wheelbase
        keeps the fraction below 0.5."""
        self.assertTrue(
            math.isclose(
                nose_gear_static_load_fraction(10.5, X_MG, X_NG), 0.5, rel_tol=1e-12
            )
        )
        self.assertLess(nose_gear_static_load_fraction(11.0, X_MG, X_NG), 0.5)
        self.assertLess(nose_gear_static_load_fraction(14.0, X_MG, X_NG), 0.5)

    def test_nose_fraction_band_verdicts_typical_band(self):
        """Step 5 nose gear load fraction band: the band verdicts
        compare each limit fraction against the 5 to 20 percent typical
        band, so the aft CG limit passes and the over-weighted forward
        CG limit fails and flags the arrangement."""
        frac_fwd = nose_gear_static_load_fraction(X_CG_FWD, X_MG, X_NG)
        frac_aft = nose_gear_static_load_fraction(X_CG_AFT, X_MG, X_NG)
        aft_ok = NOSE_FRACTION_MIN <= frac_aft <= NOSE_FRACTION_MAX
        fwd_ok = NOSE_FRACTION_MIN <= frac_fwd <= NOSE_FRACTION_MAX
        self.assertTrue(aft_ok)
        self.assertFalse(fwd_ok)
        self.assertAlmostEqual(NOSE_FRACTION_MIN, 0.05, delta=1e-12)
        self.assertAlmostEqual(NOSE_FRACTION_MAX, 0.20, delta=1e-12)

    def test_nose_fraction_valueerror_cg_outside_wheelbase(self):
        """Step 5 nose gear load fraction band: a CG at or outside the
        nose-to-main station pair drives the fraction to zero, negative,
        one or above and raises ValueError."""
        for bad in (X_MG, X_NG, 2.0, 19.0, 100.0):
            with self.assertRaises(ValueError):
                nose_gear_static_load_fraction(bad, X_MG, X_NG)

    def test_nose_fraction_valueerror_degenerate_wheelbase(self):
        """Step 5 nose gear load fraction band: a main gear station not
        aft of the nose gear station raises ValueError."""
        with self.assertRaises(ValueError):
            nose_gear_static_load_fraction(5.0, X_NG, X_NG)
        with self.assertRaises(ValueError):
            nose_gear_static_load_fraction(5.0, 2.0, X_NG)

    # ---- Step 6 of the SKILL.md workflow: main gear position check + determinism

    def test_main_gear_position_check_stations_and_margin(self):
        """Step 6 main gear position check: both CG travel limits sit
        inside the nose-to-main station pair and the aft CG limit keeps
        a positive 1.5 m margin forward of the main gear contact."""
        self.assertGreater(X_CG_FWD, X_NG)
        self.assertLess(X_CG_AFT, X_MG)
        margin = X_MG - X_CG_AFT
        self.assertAlmostEqual(margin, 1.5, delta=1e-12)
        self.assertGreater(margin, 0.0)
        self.assertLess(X_CG_FWD, X_CG_AFT)

    def test_contract_workflow_end_to_end_worked_example(self):
        """Step 6 contract workflow close: the transport-class worked
        example runs all layout checks, with tail strike clearance below
        the tipback angle, the tricycle diagonal below the main-pair
        lateral angle, and a main gear position check that must move
        because the forward CG limit over-weights the nose gear."""
        theta_tip = tipback_angle(H_CG, X_MG, X_CG_AFT)
        theta_ts = tail_strike_clearance_angle(H_TAIL, X_TAIL, X_MG)
        theta_lat = lateral_turnover_angle(H_CG, TRACK)
        theta_diag = lateral_turnover_tricycle_angle(H_CG, X_CG_FWD, X_MG, X_NG, TRACK)
        frac_fwd = nose_gear_static_load_fraction(X_CG_FWD, X_MG, X_NG)
        frac_aft = nose_gear_static_load_fraction(X_CG_AFT, X_MG, X_NG)
        self.assertLess(theta_ts, theta_tip)
        self.assertLess(theta_diag, theta_lat)
        self.assertLess(frac_aft, NOSE_FRACTION_MAX)
        self.assertGreater(frac_fwd, NOSE_FRACTION_MAX)
        self.assertAlmostEqual(theta_tip, 28.17859010995917, delta=1e-4)
        self.assertAlmostEqual(theta_ts, 16.26020470831196, delta=1e-4)
        self.assertAlmostEqual(theta_diag, 39.756669023138734, delta=1e-4)

    def test_determinism_repeated_calls_identical(self):
        """Step 6 contract test determinism: repeated calls of every
        arrangement function return identical scalars, exact by
        construction on identical computation."""
        args_tip = (H_CG, X_MG, X_CG_AFT)
        args_ts = (H_TAIL, X_TAIL, X_MG)
        args_lat = (H_CG, TRACK)
        args_tri = (H_CG, X_CG_FWD, X_MG, X_NG, TRACK)
        args_frac = (X_CG_FWD, X_MG, X_NG)
        self.assertEqual(tipback_angle(*args_tip), tipback_angle(*args_tip))
        self.assertEqual(
            tail_strike_clearance_angle(*args_ts),
            tail_strike_clearance_angle(*args_ts),
        )
        self.assertEqual(
            lateral_turnover_angle(*args_lat), lateral_turnover_angle(*args_lat)
        )
        self.assertEqual(
            lateral_turnover_tricycle_angle(*args_tri),
            lateral_turnover_tricycle_angle(*args_tri),
        )
        self.assertEqual(
            nose_gear_static_load_fraction(*args_frac),
            nose_gear_static_load_fraction(*args_frac),
        )

    def test_angles_in_degrees_and_fractions_dimensionless(self):
        """Step 6 contract test determinism: dict-free scalar returns
        keep the model deterministic, angles are always returned in
        degrees inside the 0-90 range and fractions are dimensionless
        inside (0, 1)."""
        for angle in (
            tipback_angle(H_CG, X_MG, X_CG_AFT),
            tail_strike_clearance_angle(H_TAIL, X_TAIL, X_MG),
            lateral_turnover_angle(H_CG, TRACK),
            lateral_turnover_tricycle_angle(H_CG, X_CG_FWD, X_MG, X_NG, TRACK),
        ):
            self.assertIsInstance(angle, float)
            self.assertGreater(angle, 0.0)
            self.assertLess(angle, 90.0)
        frac_fwd = nose_gear_static_load_fraction(X_CG_FWD, X_MG, X_NG)
        frac_aft = nose_gear_static_load_fraction(X_CG_AFT, X_MG, X_NG)
        self.assertIsInstance(frac_fwd, float)
        self.assertGreater(frac_fwd, 0.0)
        self.assertLess(frac_fwd, 1.0)
        self.assertGreater(frac_aft, 0.0)
        self.assertLess(frac_aft, 1.0)


if __name__ == "__main__":
    unittest.main()
