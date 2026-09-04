"""Contract test for the delta-wing-vortex-lift Polhamus suction analogy.

Offline, deterministic, stdlib unittest. Run:

    python3 scripts/test_delta_wing_vortex_lift.py

Covers the worked-example anchors of the wave-33 spec (NASA TN D-3767
model): aspect ratio identity, Kp and Kv anchors, the potential/vortex
lift split at 15 deg AR 1, the 5-25 deg sweep, drag due to lift, the
AR 0.5 high-vortex-fraction case, crossing angles, ValueError rejection
of non-physical inputs, summary-dict shape, and determinism.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import delta_wing_vortex_lift_logic as m

AR1_KP = m.slender_delta_kp(1.0)
AR1_KV = m.delta_kv(1.0)
ARHALF_KP = m.slender_delta_kp(0.5)
ARHALF_KV = m.delta_kv(0.5)


class DeltaAspectRatioTests(unittest.TestCase):
    def test_delta_aspect_ratio_76_deg_about_one(self):
        self.assertAlmostEqual(m.delta_aspect_ratio(76), 1.0, delta=0.005)

    def test_delta_aspect_ratio_45_deg_about_four(self):
        self.assertAlmostEqual(m.delta_aspect_ratio(45), 4.0, places=6)

    def test_delta_aspect_ratio_closed_form_identity(self):
        for sweep in (55.0, 70.0, 82.9):
            self.assertAlmostEqual(
                m.delta_aspect_ratio(sweep),
                4.0 / math.tan(math.radians(sweep)),
                places=12,
            )

    def test_delta_aspect_ratio_zero_sweep_raises(self):
        with self.assertRaises(ValueError):
            m.delta_aspect_ratio(0)

    def test_delta_aspect_ratio_negative_sweep_raises(self):
        with self.assertRaises(ValueError):
            m.delta_aspect_ratio(-30)

    def test_delta_aspect_ratio_90_deg_raises(self):
        with self.assertRaises(ValueError):
            m.delta_aspect_ratio(90)


class SlenderDeltaKpTests(unittest.TestCase):
    def test_slender_delta_kp_one_is_pi_over_two(self):
        self.assertAlmostEqual(m.slender_delta_kp(1.0), math.pi / 2, places=12)
        self.assertAlmostEqual(m.slender_delta_kp(1.0), 1.570796, places=5)

    def test_slender_delta_kp_scales_linearly_with_ar(self):
        self.assertAlmostEqual(m.slender_delta_kp(2.0), math.pi, places=12)
        self.assertAlmostEqual(
            m.slender_delta_kp(0.5), math.pi / 4, places=12
        )
        self.assertAlmostEqual(
            m.slender_delta_kp(1.5), 1.5 * m.slender_delta_kp(1.0), places=12
        )

    def test_slender_delta_kp_zero_raises(self):
        with self.assertRaises(ValueError):
            m.slender_delta_kp(0)

    def test_slender_delta_kp_negative_raises(self):
        with self.assertRaises(ValueError):
            m.slender_delta_kp(-0.5)


class DeltaKvTests(unittest.TestCase):
    def test_delta_kv_zero_anchor(self):
        self.assertAlmostEqual(m.delta_kv(0.0), 3.14, places=6)

    def test_delta_kv_four_anchor(self):
        self.assertAlmostEqual(m.delta_kv(4.0), 3.45, places=6)

    def test_delta_kv_one_anchor(self):
        self.assertAlmostEqual(m.delta_kv(1.0), 3.2175, places=6)

    def test_delta_kv_linear_at_midpoint(self):
        self.assertAlmostEqual(
            m.delta_kv(2.0), 3.14 + (3.45 - 3.14) * 0.5, places=12
        )

    def test_delta_kv_clamps_above_ar_clamp(self):
        self.assertAlmostEqual(m.delta_kv(6.0), 3.45, places=12)
        self.assertAlmostEqual(m.delta_kv(100.0), 3.45, places=12)

    def test_delta_kv_negative_raises(self):
        with self.assertRaises(ValueError):
            m.delta_kv(-1.0)


class PolhamusClTests(unittest.TestCase):
    def test_ar1_alpha15_potential_vortex_split(self):
        self.assertAlmostEqual(
            m.polhamus_cl_potential(AR1_KP, 15.0), 0.3793, places=4
        )
        self.assertAlmostEqual(
            m.polhamus_cl_vortex(AR1_KV, 15.0), 0.2082, places=4
        )

    def test_ar1_alpha15_total_lift_and_vortex_fraction(self):
        cl = m.polhamus_cl(AR1_KP, AR1_KV, 15.0)
        self.assertAlmostEqual(cl, 0.5875, places=4)
        fraction = m.polhamus_cl_vortex(AR1_KV, 15.0) / cl
        self.assertAlmostEqual(fraction, 0.354, places=3)

    def test_cl_zero_alpha_is_exactly_zero(self):
        self.assertEqual(m.polhamus_cl(AR1_KP, AR1_KV, 0.0), 0.0)
        self.assertEqual(m.polhamus_cl_potential(AR1_KP, 0.0), 0.0)
        self.assertEqual(m.polhamus_cl_vortex(AR1_KV, 0.0), 0.0)

    def test_sweep_cl_values_match_expected(self):
        expected = {5: 0.160, 10: 0.360, 15: 0.588, 20: 0.828, 25: 1.066}
        for alpha, target in expected.items():
            self.assertAlmostEqual(
                m.polhamus_cl(AR1_KP, AR1_KV, alpha), target, places=3
            )

    def test_sweep_cl_increases_monotonically(self):
        values = [
            m.polhamus_cl(AR1_KP, AR1_KV, a) for a in (5, 10, 15, 20, 25)
        ]
        for lower, upper in zip(values, values[1:]):
            self.assertGreater(upper, lower)

    def test_ar_half_alpha20_total_and_vortex_fraction(self):
        cl = m.polhamus_cl(ARHALF_KP, ARHALF_KV, 20.0)
        self.assertAlmostEqual(cl, 0.5866, places=4)
        fraction = m.polhamus_cl_vortex(ARHALF_KV, 20.0) / cl
        self.assertAlmostEqual(fraction, 0.596, places=3)
        self.assertGreater(fraction, 0.59)
        self.assertLess(fraction, 0.61)

    def test_vortex_fraction_grows_as_ar_shrinks(self):
        f_ar1 = m.polhamus_cl_vortex(AR1_KV, 15.0) / m.polhamus_cl(
            AR1_KP, AR1_KV, 15.0
        )
        f_arhalf = m.polhamus_cl_vortex(ARHALF_KV, 20.0) / m.polhamus_cl(
            ARHALF_KP, ARHALF_KV, 20.0
        )
        self.assertGreater(f_arhalf, f_ar1)


class CdDueToLiftTests(unittest.TestCase):
    def test_cd_due_to_lift_at_15_deg(self):
        cl = m.polhamus_cl(AR1_KP, AR1_KV, 15.0)
        self.assertAlmostEqual(m.cd_due_to_lift(cl, 15.0), 0.157, places=3)

    def test_cd_due_to_lift_equals_cl_times_tan(self):
        cl = 0.5875
        self.assertAlmostEqual(
            m.cd_due_to_lift(cl, 15.0),
            cl * math.tan(math.radians(15.0)),
            places=12,
        )


class CrossingTests(unittest.TestCase):
    def test_crossing_ar1_about_26_deg(self):
        self.assertAlmostEqual(
            m.vortex_potential_crossing_deg(AR1_KP, AR1_KV), 26.0, places=1
        )

    def test_crossing_ar_half_about_13_9_deg(self):
        self.assertAlmostEqual(
            m.vortex_potential_crossing_deg(ARHALF_KP, ARHALF_KV),
            13.9,
            places=1,
        )

    def test_crossing_angle_shrinks_with_slenderness(self):
        crossing_ar1 = m.vortex_potential_crossing_deg(AR1_KP, AR1_KV)
        crossing_arhalf = m.vortex_potential_crossing_deg(ARHALF_KP, ARHALF_KV)
        self.assertGreater(crossing_ar1, crossing_arhalf)

    def test_crossing_potential_equals_vortex_at_crossing(self):
        alpha = m.vortex_potential_crossing_deg(AR1_KP, AR1_KV)
        pot = m.polhamus_cl_potential(AR1_KP, alpha)
        vort = m.polhamus_cl_vortex(AR1_KV, alpha)
        self.assertAlmostEqual(pot, vort, places=9)

    def test_crossing_kv_nonpositive_raises(self):
        with self.assertRaises(ValueError):
            m.vortex_potential_crossing_deg(1.0, 0.0)
        with self.assertRaises(ValueError):
            m.vortex_potential_crossing_deg(1.0, -3.14)


class DeltaLiftSummaryTests(unittest.TestCase):
    def test_delta_lift_summary_has_exact_keys(self):
        summary = m.delta_lift_summary(1.0, 15.0)
        self.assertEqual(
            set(summary.keys()),
            {
                "aspect_ratio",
                "kp",
                "kv",
                "alpha_deg",
                "cl_potential",
                "cl_vortex",
                "cl_total",
                "cd_due_to_lift",
                "vortex_fraction",
                "crossing_deg",
            },
        )

    def test_delta_lift_summary_consistency_and_determinism(self):
        summary = m.delta_lift_summary(1.0, 15.0)
        self.assertAlmostEqual(
            summary["cl_total"],
            summary["cl_potential"] + summary["cl_vortex"],
            places=12,
        )
        self.assertAlmostEqual(
            summary["cl_potential"], 0.3793, places=4
        )
        self.assertAlmostEqual(summary["cl_total"], 0.5875, places=4)
        self.assertAlmostEqual(summary["crossing_deg"], 26.0, places=1)
        again = m.delta_lift_summary(1.0, 15.0)
        self.assertEqual(summary, again)

    def test_delta_lift_summary_sweep_flag_matches_ar_input(self):
        by_sweep = m.delta_lift_summary(76.0, 15.0, sweep=True)
        by_ar = m.delta_lift_summary(by_sweep["aspect_ratio"], 15.0)
        self.assertAlmostEqual(by_sweep["cl_total"], by_ar["cl_total"], places=12)
        self.assertAlmostEqual(
            by_sweep["aspect_ratio"], m.delta_aspect_ratio(76.0), places=12
        )

    def test_delta_lift_summary_invalid_ar_raises(self):
        with self.assertRaises(ValueError):
            m.delta_lift_summary(-1.0, 15.0)
        with self.assertRaises(ValueError):
            m.delta_lift_summary(0.0, 15.0)
        with self.assertRaises(ValueError):
            m.delta_lift_summary(90.0, 15.0, sweep=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
