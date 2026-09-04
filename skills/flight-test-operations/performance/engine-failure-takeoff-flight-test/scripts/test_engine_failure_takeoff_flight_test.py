#!/usr/bin/env python3
"""Contract test: engine-out takeoff flight test reduction.

Exercises scripts/engine_failure_takeoff_flight_test_logic.py (stdlib
unittest, offline, deterministic). Contract: trapezoid engine-failure
distance to the VEF crossing, V1 recognition segment, continued climb
to the 35-ft obstacle, the chained continued engine-out distance,
balanced-field V1 from the segment-linear ASD/TOD intersection,
ordering checks V1 >= VEF + a_cont * t_rec and V1 <= V_R, the runway
field verdict, and the reduction summary; invalid inputs raise
ValueError.

Worked example: ASD [1350, 1450, 1560, 1680, 1810] m at 60-80 m/s and
engine-out TOD [1620, 1600, 1590, 1605, 1630] m balance at about
71.43 m/s and about 1594.3 m; V1_min = 58 + 1.8 = 59.8 m/s passes,
V1 <= V_R (80 m/s) passes, and the 1700 m runway fits with margin
about +106 m.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine_failure_takeoff_flight_test_logic as eft  # noqa: E402

SPEEDS = [60.0, 65.0, 70.0, 75.0, 80.0]
ASD = [1350.0, 1450.0, 1560.0, 1680.0, 1810.0]
TOD = [1620.0, 1600.0, 1590.0, 1605.0, 1630.0]
V_EF = 58.0
T_REC = 1.0
A_CONT = 1.8
V_R = 80.0
RUNWAY = 1700.0


class EngineFailureDistanceTest(unittest.TestCase):
    def test_linear_ramp_mid_segment_crossing(self):
        # v(t) = 2t samples; crossing at v_ef = 25 m/s (t = 12.5 s).
        # Closed form for constant a: s = v_ef^2 / (2a) = 625 / 4.
        v = [0.0, 10.0, 20.0, 30.0, 40.0]
        t = [0.0, 5.0, 10.0, 15.0, 20.0]
        self.assertAlmostEqual(eft.engine_failure_distance(v, t, 25.0), 156.25, places=6)
        self.assertAlmostEqual(
            eft.engine_failure_distance(v, t, 25.0), 25.0 ** 2 / (2.0 * 2.0), places=6
        )

    def test_linear_ramp_crossing_at_last_sample(self):
        # v_ef = 30 m/s equals the final sample: full trapezoid integral.
        v = [0.0, 10.0, 20.0, 30.0, 40.0]
        t = [0.0, 5.0, 10.0, 15.0, 20.0]
        self.assertAlmostEqual(eft.engine_failure_distance(v, t, 30.0), 225.0, places=6)

    def test_crossing_at_interior_sample_point(self):
        # v_ef = 20 m/s sits exactly on sample index 2.
        v = [0.0, 10.0, 20.0, 30.0, 40.0]
        t = [0.0, 5.0, 10.0, 15.0, 20.0]
        self.assertAlmostEqual(eft.engine_failure_distance(v, t, 20.0), 100.0, places=6)

    def test_empty_samples_raise(self):
        with self.assertRaises(ValueError):
            eft.engine_failure_distance([], [], 25.0)
        with self.assertRaises(ValueError):
            eft.engine_failure_distance([], [0.0, 1.0], 25.0)

    def test_length_mismatch_and_single_sample_raise(self):
        with self.assertRaises(ValueError):
            eft.engine_failure_distance([0.0, 10.0], [0.0], 5.0)
        with self.assertRaises(ValueError):
            eft.engine_failure_distance([10.0], [0.0], 5.0)

    def test_non_monotone_samples_raise(self):
        v = [0.0, 10.0, 20.0, 30.0, 40.0]
        t = [0.0, 5.0, 10.0, 15.0, 20.0]
        with self.assertRaises(ValueError):
            eft.engine_failure_distance(list(reversed(v)), t, 25.0)
        with self.assertRaises(ValueError):
            eft.engine_failure_distance([0.0, 10.0, 10.0, 30.0], t, 25.0)
        with self.assertRaises(ValueError):
            eft.engine_failure_distance(v, [0.0, 5.0, 15.0, 10.0, 20.0], 25.0)

    def test_non_positive_or_unreachable_v_ef_raise(self):
        v = [0.0, 10.0, 20.0, 30.0, 40.0]
        t = [0.0, 5.0, 10.0, 15.0, 20.0]
        for bad in (0.0, -5.0):
            with self.assertRaises(ValueError):
                eft.engine_failure_distance(v, t, bad)
        with self.assertRaises(ValueError):
            eft.engine_failure_distance(v, t, 45.0)  # beyond the samples
        with self.assertRaises(ValueError):
            eft.engine_failure_distance(v, t, -1.0)
        with self.assertRaises(ValueError):
            eft.engine_failure_distance([-1.0, 10.0], [0.0, 5.0], 5.0)


class RecognitionDistanceTest(unittest.TestCase):
    def test_formula(self):
        self.assertAlmostEqual(eft.recognition_distance(70.0, 2.5), 175.0, places=6)

    def test_non_positive_inputs_raise(self):
        for v1 in (0.0, -70.0):
            with self.assertRaises(ValueError):
                eft.recognition_distance(v1, 1.0)
        for tr in (0.0, -1.0):
            with self.assertRaises(ValueError):
                eft.recognition_distance(70.0, tr)

    def test_scales_with_time(self):
        d1 = eft.recognition_distance(60.0, 1.0)
        d2 = eft.recognition_distance(60.0, 2.0)
        self.assertAlmostEqual(d2, 2.0 * d1, places=6)


class ContinuedClimbDistanceTest(unittest.TestCase):
    def test_formula(self):
        # 80 * 10.668 / 6 = 142.24 m.
        self.assertAlmostEqual(
            eft.continued_climb_distance(80.0, 6.0), 142.24, places=6
        )

    def test_default_obstacle_height(self):
        a = eft.continued_climb_distance(80.0, 6.0)
        b = eft.continued_climb_distance(80.0, 6.0, h_target_m=10.668)
        self.assertAlmostEqual(a, b, places=9)

    def test_non_positive_inputs_raise(self):
        for roc in (0.0, -6.0):
            with self.assertRaises(ValueError):
                eft.continued_climb_distance(80.0, roc)
        for h in (0.0, -10.0):
            with self.assertRaises(ValueError):
                eft.continued_climb_distance(80.0, 6.0, h_target_m=h)
        with self.assertRaises(ValueError):
            eft.continued_climb_distance(0.0, 6.0)


class EngineOutTakeoffDistanceTest(unittest.TestCase):
    def test_worked_example_style_chain(self):
        # failure 100 + recognition 70 + ground (6400-4900)/3.6 +
        # climb 80*10.668/6 = 100 + 70 + 416.6667 + 142.24.
        out = eft.engine_out_takeoff_distance(100.0, 70.0, 80.0, 1.0, 1.8, 6.0)
        self.assertAlmostEqual(out["recognition_m"], 70.0, places=6)
        self.assertAlmostEqual(out["ground_continue_m"], 416.6666666667, places=6)
        self.assertAlmostEqual(out["climb_m"], 142.24, places=6)
        self.assertAlmostEqual(out["total_m"], 728.9066666667, places=6)

    def test_v1_equal_v2_zero_ground_leg(self):
        out = eft.engine_out_takeoff_distance(100.0, 80.0, 80.0, 1.0, 1.8, 6.0)
        self.assertAlmostEqual(out["ground_continue_m"], 0.0, places=9)
        self.assertAlmostEqual(out["total_m"], 100.0 + 80.0 + 142.24, places=6)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eft.engine_out_takeoff_distance(100.0, 85.0, 80.0, 1.0, 1.8, 6.0)
        with self.assertRaises(ValueError):
            eft.engine_out_takeoff_distance(100.0, 70.0, 80.0, 1.0, 0.0, 6.0)
        with self.assertRaises(ValueError):
            eft.engine_out_takeoff_distance(-1.0, 70.0, 80.0, 1.0, 1.8, 6.0)
        with self.assertRaises(ValueError):
            eft.engine_out_takeoff_distance(100.0, 70.0, 80.0, 1.0, 1.8, 0.0)
        with self.assertRaises(ValueError):
            eft.engine_out_takeoff_distance(100.0, 0.0, 80.0, 1.0, 1.8, 6.0)


class BalancedFieldV1Test(unittest.TestCase):
    def test_worked_example_balanced_v1(self):
        v1, dist = eft.balanced_field_v1(SPEEDS, ASD, SPEEDS, TOD)
        self.assertAlmostEqual(v1, 71.43, places=2)
        self.assertAlmostEqual(dist, 1594.3, places=1)
        self.assertGreater(v1, 70.0)
        self.assertLess(v1, 75.0)

    def test_intersection_consistency(self):
        v1, dist = eft.balanced_field_v1(SPEEDS, ASD, SPEEDS, TOD)
        # Crossing inside the 70-75 segment: ASD = 1560 + 24*(v-70),
        # TOD = 1590 + 3*(v-70); both must equal the returned distance.
        self.assertAlmostEqual(dist, 1560.0 + 24.0 * (v1 - 70.0), places=6)
        self.assertAlmostEqual(dist, 1590.0 + 3.0 * (v1 - 70.0), places=6)

    def test_tod_curve_may_be_non_monotone(self):
        # Dipping TOD crossing the ASD curve exactly at the 70 m/s knot.
        tod = [1650.0, 1580.0, 1560.0, 1605.0, 1630.0]
        v1, dist = eft.balanced_field_v1(SPEEDS, ASD, SPEEDS, tod)
        self.assertAlmostEqual(v1, 70.0, places=6)
        self.assertAlmostEqual(dist, 1560.0, places=6)

    def test_no_crossing_tod_above_returns_asd_limited(self):
        # TOD everywhere above ASD: no crossing, regime asd-limited.
        tod_high = [d + 200.0 for d in ASD]
        v1, flag = eft.balanced_field_v1(SPEEDS, ASD, SPEEDS, tod_high)
        self.assertIsNone(v1)
        self.assertEqual(flag, "asd-limited")

    def test_no_crossing_asd_above_returns_tod_limited(self):
        # ASD shifted above the TOD curve at every knot: no crossing,
        # regime tod-limited (ASD max 1620 is below 1750 min).
        asd_high = [d + 400.0 for d in ASD]
        v1, flag = eft.balanced_field_v1(SPEEDS, asd_high, SPEEDS, TOD)
        self.assertIsNone(v1)
        self.assertEqual(flag, "tod-limited")

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eft.balanced_field_v1([], ASD, SPEEDS, TOD)
        with self.assertRaises(ValueError):
            eft.balanced_field_v1(SPEEDS, [1350.0, 1450.0], SPEEDS, TOD)
        with self.assertRaises(ValueError):
            eft.balanced_field_v1(SPEEDS, ASD, SPEEDS, [1620.0])
        # Descending ASD distances are non-physical.
        with self.assertRaises(ValueError):
            eft.balanced_field_v1(SPEEDS, [1810.0, 1680.0, 1560.0, 1450.0, 1350.0], SPEEDS, TOD)
        # Descending speed knots.
        with self.assertRaises(ValueError):
            eft.balanced_field_v1(list(reversed(SPEEDS)), ASD, SPEEDS, TOD)
        # Negative distance.
        with self.assertRaises(ValueError):
            eft.balanced_field_v1(SPEEDS, [-1.0, 1450.0, 1560.0, 1680.0, 1810.0], SPEEDS, TOD)
        # Disjoint speed domains.
        with self.assertRaises(ValueError):
            eft.balanced_field_v1(SPEEDS, ASD, [85.0, 90.0, 95.0], [1800.0, 1850.0, 1900.0])

    def test_deterministic(self):
        a = eft.balanced_field_v1(SPEEDS, ASD, SPEEDS, TOD)
        b = eft.balanced_field_v1(SPEEDS, ASD, SPEEDS, TOD)
        self.assertEqual(a, b)
        self.assertEqual(a[0], 71.42857142857143)


class V1OrderingVerdictTest(unittest.TestCase):
    def test_worked_example_both_pass(self):
        v1, _ = eft.balanced_field_v1(SPEEDS, ASD, SPEEDS, TOD)
        out = eft.v1_ordering_verdict(v1, V_EF, T_REC, A_CONT, V_R)
        self.assertAlmostEqual(out["v1_min_mps"], 59.8, places=6)
        self.assertTrue(out["v1_ge_v1_min"])
        self.assertTrue(out["v1_le_vr"])
        self.assertTrue(out["ordering_pass"])
        self.assertAlmostEqual(out["v1_min_margin_mps"], 11.6285714286, places=6)
        self.assertAlmostEqual(out["v_r_margin_mps"], 8.5714285714, places=6)

    def test_boundary_equalities_pass(self):
        # V1 exactly at VEF + a_cont * t_rec and exactly at V_R both pass.
        out = eft.v1_ordering_verdict(59.8, V_EF, T_REC, A_CONT, V_R)
        self.assertTrue(out["v1_ge_v1_min"])
        self.assertTrue(out["ordering_pass"])
        out = eft.v1_ordering_verdict(80.0, V_EF, T_REC, A_CONT, V_R)
        self.assertTrue(out["v1_le_vr"])
        self.assertTrue(out["ordering_pass"])

    def test_longer_recognition_tightens_ordering(self):
        v1, _ = eft.balanced_field_v1(SPEEDS, ASD, SPEEDS, TOD)
        m1 = eft.v1_ordering_verdict(v1, V_EF, 1.0, A_CONT, V_R)["v1_min_mps"]
        m2 = eft.v1_ordering_verdict(v1, V_EF, 2.0, A_CONT, V_R)["v1_min_mps"]
        m8 = eft.v1_ordering_verdict(v1, V_EF, 8.0, A_CONT, V_R)["v1_min_mps"]
        self.assertGreater(m2, m1)
        self.assertAlmostEqual(m8, 58.0 + 1.8 * 8.0, places=9)
        out8 = eft.v1_ordering_verdict(v1, V_EF, 8.0, A_CONT, V_R)
        self.assertFalse(out8["v1_ge_v1_min"])
        self.assertFalse(out8["ordering_pass"])

    def test_invalid_inputs_raise(self):
        for kwargs in (
            {"v1_mps": 0.0},
            {"v_ef_mps": 0.0},
            {"t_rec_s": 0.0},
            {"a_cont_mps2": -0.1},
            {"v_r_mps": 0.0},
        ):
            args = {"v1_mps": 71.43, "v_ef_mps": 58.0, "t_rec_s": 1.0,
                    "a_cont_mps2": 1.8, "v_r_mps": 80.0}
            args.update(kwargs)
            with self.assertRaises(ValueError):
                eft.v1_ordering_verdict(**args)


class FieldLengthVerdictTest(unittest.TestCase):
    def test_worked_example_margin(self):
        out = eft.field_length_verdict(RUNWAY, 1594.2857142857142)
        self.assertAlmostEqual(out["margin_m"], 105.7142857143, places=6)
        self.assertTrue(out["fits"])

    def test_longer_runway_raises_margin_and_short_runway_fails(self):
        m_short = eft.field_length_verdict(1500.0, 1594.2857142857142)
        m_base = eft.field_length_verdict(RUNWAY, 1594.2857142857142)
        m_long = eft.field_length_verdict(2000.0, 1594.2857142857142)
        self.assertGreater(m_long["margin_m"], m_base["margin_m"])
        self.assertAlmostEqual(m_short["margin_m"], -94.2857142857, places=6)
        self.assertFalse(m_short["fits"])  # negative margin is an outcome

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            eft.field_length_verdict(0.0, 1594.0)
        with self.assertRaises(ValueError):
            eft.field_length_verdict(-1700.0, 1594.0)
        with self.assertRaises(ValueError):
            eft.field_length_verdict(1700.0, -5.0)


class SummaryTest(unittest.TestCase):
    KEYS = {
        "regime",
        "balanced_field_v1_mps",
        "balanced_field_distance_m",
        "v1_min_mps",
        "recognition_distance_m",
        "ordering_verdict",
        "field_verdict",
    }

    def test_worked_example_summary(self):
        out = eft.engine_failure_takeoff_summary(
            SPEEDS, ASD, SPEEDS, TOD, V_EF, T_REC, A_CONT, V_R, RUNWAY
        )
        self.assertEqual(set(out.keys()), self.KEYS)
        self.assertEqual(out["regime"], "balanced")
        self.assertAlmostEqual(out["balanced_field_v1_mps"], 71.43, places=2)
        self.assertAlmostEqual(out["balanced_field_distance_m"], 1594.3, places=1)
        self.assertAlmostEqual(out["v1_min_mps"], 59.8, places=6)
        self.assertAlmostEqual(out["recognition_distance_m"], 71.4285714286, places=6)
        self.assertTrue(out["ordering_verdict"]["ordering_pass"])
        self.assertTrue(out["ordering_verdict"]["v1_ge_v1_min"])
        self.assertTrue(out["ordering_verdict"]["v1_le_vr"])
        self.assertTrue(out["field_verdict"]["fits"])
        self.assertAlmostEqual(out["field_verdict"]["margin_m"], 105.71, places=1)

    def test_no_crossing_summary_regime_and_nones(self):
        tod_high = [d + 200.0 for d in ASD]
        out = eft.engine_failure_takeoff_summary(
            SPEEDS, ASD, SPEEDS, tod_high, V_EF, T_REC, A_CONT, V_R, RUNWAY
        )
        self.assertEqual(set(out.keys()), self.KEYS)
        self.assertEqual(out["regime"], "asd-limited")
        self.assertIsNone(out["balanced_field_v1_mps"])
        self.assertIsNone(out["balanced_field_distance_m"])
        self.assertIsNone(out["recognition_distance_m"])
        self.assertIsNone(out["ordering_verdict"])
        self.assertIsNone(out["field_verdict"])

    def test_summary_validates_inputs(self):
        with self.assertRaises(ValueError):
            eft.engine_failure_takeoff_summary(
                SPEEDS, ASD, SPEEDS, TOD, V_EF, T_REC, A_CONT, V_R, 0.0
            )
        with self.assertRaises(ValueError):
            eft.engine_failure_takeoff_summary(
                SPEEDS, ASD, SPEEDS, TOD, 0.0, T_REC, A_CONT, V_R, RUNWAY
            )
        with self.assertRaises(ValueError):
            eft.engine_failure_takeoff_summary(
                SPEEDS, ASD, SPEEDS, TOD, V_EF, 0.0, A_CONT, V_R, RUNWAY
            )

    def test_summary_deterministic(self):
        a = eft.engine_failure_takeoff_summary(
            SPEEDS, ASD, SPEEDS, TOD, V_EF, T_REC, A_CONT, V_R, RUNWAY
        )
        b = eft.engine_failure_takeoff_summary(
            SPEEDS, ASD, SPEEDS, TOD, V_EF, T_REC, A_CONT, V_R, RUNWAY
        )
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
