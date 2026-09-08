#!/usr/bin/env python3
"""Gate 3 contract test: impact-time-control guidance (ITCG) law.

Exercises scripts/impact_time_control_guidance_logic.py (stdlib
unittest, offline, deterministic). Follows the SKILL.md Workflow steps:
step 1 (fix the engagement state), step 2 (the PN baseline via
png_baseline), step 3 (the PNG time-to-go estimate via
tgo_estimate_png), step 4 (the impact-time error), step 5 (the
time-to-go-error-feedback bias via impact_time_bias), step 6 (the total
command via itcg_command), step 7 (the natural time-to-impact via
time_to_impact_seconds), and step 8 (ValueError rejection of
non-physical inputs).

Worked example (R = 8000.0 m, Vc = 300.0 m/s, lambda_dot = 0.004 rad/s,
N = 4.0, t_go_des = 30.0 s): a_png = 4.8 m/s^2, tgo_png =
26.666666666667 s, e_t = 3.333333333333 s, a_bias = 5.625 m/s^2,
a_cmd = 10.425 m/s^2. No exact float equality is asserted on any
computed sum; all numeric checks use assertAlmostEqual or
math.isclose.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import impact_time_control_guidance_logic as itcg  # noqa: E402

RANGE_M = 8000.0
VC_MPS = 300.0
LAM_DOT = 0.004
NAV_N = 4.0
TGO_DES = 30.0

A_PNG_REF = 4.8
TGO_PNG_REF = 26.666666666666668
E_T_REF = 3.3333333333333286
A_BIAS_REF = 5.624999999999997
A_CMD_REF = 10.424999999999997


class PngBaselineTest(unittest.TestCase):
    """Step 2 of the SKILL.md workflow: the PN baseline acceleration."""

    def test_worked_example(self):
        a_png = itcg.png_baseline(NAV_N, VC_MPS, LAM_DOT)
        self.assertTrue(math.isclose(a_png, A_PNG_REF, rel_tol=1e-9))

    def test_rejects_nav_constant_at_one(self):
        with self.assertRaises(ValueError):
            itcg.png_baseline(1.0, VC_MPS, LAM_DOT)

    def test_rejects_nav_constant_below_one(self):
        with self.assertRaises(ValueError):
            itcg.png_baseline(0.5, VC_MPS, LAM_DOT)

    def test_rejects_negative_closing_speed(self):
        with self.assertRaises(ValueError):
            itcg.png_baseline(NAV_N, -1.0, LAM_DOT)

    def test_zero_closing_speed_allowed(self):
        a_png = itcg.png_baseline(NAV_N, 0.0, LAM_DOT)
        self.assertAlmostEqual(a_png, 0.0, places=12)

    def test_scales_linearly_with_los_rate(self):
        a1 = itcg.png_baseline(NAV_N, VC_MPS, LAM_DOT)
        a2 = itcg.png_baseline(NAV_N, VC_MPS, 2.0 * LAM_DOT)
        self.assertTrue(math.isclose(a2, 2.0 * a1, rel_tol=1e-12))


class TgoEstimatePngTest(unittest.TestCase):
    """Step 3 of the SKILL.md workflow: the PNG time-to-go estimate."""

    def test_worked_example_ratio(self):
        tgo = itcg.tgo_estimate_png(VC_MPS, RANGE_M)
        self.assertTrue(math.isclose(tgo, RANGE_M / VC_MPS, rel_tol=1e-15))

    def test_matches_reference_value(self):
        tgo = itcg.tgo_estimate_png(VC_MPS, RANGE_M)
        self.assertTrue(math.isclose(tgo, TGO_PNG_REF, rel_tol=1e-9))

    def test_zero_range_gives_zero_tgo(self):
        tgo = itcg.tgo_estimate_png(VC_MPS, 0.0)
        self.assertAlmostEqual(tgo, 0.0, places=12)

    def test_rejects_zero_closing_speed(self):
        with self.assertRaises(ValueError):
            itcg.tgo_estimate_png(0.0, RANGE_M)

    def test_rejects_negative_closing_speed(self):
        with self.assertRaises(ValueError):
            itcg.tgo_estimate_png(-10.0, RANGE_M)

    def test_rejects_negative_range(self):
        with self.assertRaises(ValueError):
            itcg.tgo_estimate_png(VC_MPS, -1.0)


class ImpactTimeBiasTest(unittest.TestCase):
    """Step 5 of the SKILL.md workflow: the time-to-go-error feedback."""

    def test_worked_example_bias(self):
        tgo_png = itcg.tgo_estimate_png(VC_MPS, RANGE_M)
        a_b = itcg.impact_time_bias(NAV_N, VC_MPS, TGO_DES, tgo_png)
        self.assertTrue(math.isclose(a_b, A_BIAS_REF, rel_tol=1e-9))

    def test_positive_error_gives_positive_bias(self):
        a_b = itcg.impact_time_bias(4.0, 300.0, 35.0, 26.666666666666668)
        self.assertGreater(a_b, 0.0)

    def test_negative_error_gives_negative_bias(self):
        a_b = itcg.impact_time_bias(4.0, 300.0, 20.0, 26.666666666666668)
        self.assertLess(a_b, 0.0)

    def test_linear_in_closing_speed_at_fixed_ratio(self):
        tgo_actual = 26.666666666666668
        e_t = 3.3333333333333286
        tgo_desired = tgo_actual + e_t
        a_b1 = itcg.impact_time_bias(NAV_N, 300.0, tgo_desired, tgo_actual)
        a_b2 = itcg.impact_time_bias(NAV_N, 600.0, 2.0 * tgo_desired,
                                      2.0 * tgo_actual)
        # doubling Vc and tgo (actual, desired) together keeps e_t/tgo^2
        # halved, so isolate pure Vc doubling at constant e_t/tgo^2:
        a_b3 = itcg.impact_time_bias(NAV_N, 600.0, tgo_desired, tgo_actual)
        self.assertTrue(math.isclose(a_b3, 2.0 * a_b1, rel_tol=1e-12))
        self.assertIsInstance(a_b2, float)

    def test_rejects_nonpositive_gain(self):
        with self.assertRaises(ValueError):
            itcg.impact_time_bias(0.0, VC_MPS, TGO_DES, 26.666666666666668)

    def test_rejects_nonpositive_closing_speed(self):
        with self.assertRaises(ValueError):
            itcg.impact_time_bias(NAV_N, 0.0, TGO_DES, 26.666666666666668)

    def test_rejects_nonpositive_tgo_actual(self):
        with self.assertRaises(ValueError):
            itcg.impact_time_bias(NAV_N, VC_MPS, TGO_DES, 0.0)

    def test_rejects_nonpositive_tgo_desired(self):
        with self.assertRaises(ValueError):
            itcg.impact_time_bias(NAV_N, VC_MPS, 0.0, 26.666666666666668)


class ItcgCommandTest(unittest.TestCase):
    """Step 6 of the SKILL.md workflow: the total ITCG command."""

    def test_worked_example_full_tuple(self):
        a_cmd, a_png, a_b, tgo_png, e_t = itcg.itcg_command(
            NAV_N, VC_MPS, LAM_DOT, RANGE_M, TGO_DES)
        self.assertTrue(math.isclose(a_png, A_PNG_REF, rel_tol=1e-9))
        self.assertTrue(math.isclose(tgo_png, TGO_PNG_REF, rel_tol=1e-9))
        self.assertTrue(math.isclose(e_t, E_T_REF, rel_tol=1e-9))
        self.assertTrue(math.isclose(a_b, A_BIAS_REF, rel_tol=1e-9))
        self.assertTrue(math.isclose(a_cmd, A_CMD_REF, rel_tol=1e-9))

    def test_impact_time_error_arithmetic(self):
        _, _, _, tgo_png, e_t = itcg.itcg_command(
            NAV_N, VC_MPS, LAM_DOT, RANGE_M, TGO_DES)
        self.assertTrue(math.isclose(e_t, TGO_DES - tgo_png, rel_tol=1e-15))

    def test_zero_error_identity(self):
        tgo_png = itcg.tgo_estimate_png(VC_MPS, RANGE_M)
        a_cmd, a_png, a_b, _, e_t = itcg.itcg_command(
            NAV_N, VC_MPS, LAM_DOT, RANGE_M, tgo_png)
        self.assertAlmostEqual(a_b, 0.0, delta=1e-12)
        self.assertAlmostEqual(e_t, 0.0, delta=1e-12)
        self.assertTrue(math.isclose(a_cmd, a_png, rel_tol=1e-12, abs_tol=1e-12))

    def test_command_equals_baseline_plus_bias(self):
        a_cmd, a_png, a_b, _, _ = itcg.itcg_command(
            NAV_N, VC_MPS, LAM_DOT, RANGE_M, TGO_DES)
        self.assertTrue(math.isclose(a_cmd, a_png + a_b, rel_tol=1e-12))

    def test_determinism(self):
        r1 = itcg.itcg_command(NAV_N, VC_MPS, LAM_DOT, RANGE_M, TGO_DES)
        r2 = itcg.itcg_command(NAV_N, VC_MPS, LAM_DOT, RANGE_M, TGO_DES)
        self.assertEqual(r1, r2)

    def test_custom_gain_overrides_default(self):
        a_cmd_default, _, a_b_default, _, _ = itcg.itcg_command(
            NAV_N, VC_MPS, LAM_DOT, RANGE_M, TGO_DES)
        a_cmd_custom, _, a_b_custom, _, _ = itcg.itcg_command(
            NAV_N, VC_MPS, LAM_DOT, RANGE_M, TGO_DES, gain=8.0)
        self.assertTrue(math.isclose(a_b_custom, 2.0 * a_b_default, rel_tol=1e-12))
        self.assertNotAlmostEqual(a_cmd_custom, a_cmd_default, places=6)


class TimeToImpactSecondsTest(unittest.TestCase):
    """Step 7 of the SKILL.md workflow: the natural time-to-impact."""

    def test_matches_tgo_estimate_png(self):
        t_natural = itcg.time_to_impact_seconds(RANGE_M, VC_MPS)
        tgo_png = itcg.tgo_estimate_png(VC_MPS, RANGE_M)
        self.assertTrue(math.isclose(t_natural, tgo_png, rel_tol=1e-15))

    def test_worked_example_value(self):
        t_natural = itcg.time_to_impact_seconds(RANGE_M, VC_MPS)
        self.assertTrue(math.isclose(t_natural, TGO_PNG_REF, rel_tol=1e-9))

    def test_rejects_zero_closing_speed(self):
        with self.assertRaises(ValueError):
            itcg.time_to_impact_seconds(RANGE_M, 0.0)


class EulerSignProbeTest(unittest.TestCase):
    """Step 8 of the SKILL.md workflow: ValueError rejection, plus the
    illustrative fixed-step Euler sign probe (test-side identity, not a
    leaf feature) confirming the bias lengthens the flight time.

    Planar constant-speed engagement against a stationary target at
    (R, 0): the missile starts at the origin with a small lead angle
    above the line of sight, and the guidance command (PNG baseline
    plus the impact-time bias, or the PNG baseline alone) is applied
    as a lateral acceleration perpendicular to the velocity. The
    biased run must reach the target later than the unbiased run by
    the anchor's margin (anchor /tmp/w46spec/anchor_impact_time_
    guidance.py: natural PNG impact 23.5500 s, biased 27.6500 s,
    delta 4.1000 s).
    """

    def _planar_integration(self, with_bias, dt=0.01, t_max=180.0):
        V = 340.0
        eta = math.radians(5.0)
        px, py = 0.0, 0.0
        ux, uy = V * math.cos(eta), V * math.sin(eta)
        tx, ty = RANGE_M, 0.0
        t = 0.0
        while True:
            rx, ry = tx - px, ty - py
            rr = math.hypot(rx, ry)
            vc = (ux * rx + uy * ry) / rr
            if rr < 0.5 or vc <= 5.0 or t > t_max:
                break
            lam_dot = (ry * ux - rx * uy) / (rr * rr)
            a_png_c = itcg.png_baseline(NAV_N, vc, lam_dot)
            if with_bias:
                tgo_act = rr / vc
                a_b_c = itcg.impact_time_bias(NAV_N, vc, TGO_DES - t, tgo_act)
            else:
                a_b_c = 0.0
            a_c = a_png_c + a_b_c
            sp = math.hypot(ux, uy)
            nx, ny = -uy / sp, ux / sp
            ux += a_c * nx * dt
            uy += a_c * ny * dt
            sp = math.hypot(ux, uy)
            ux *= V / sp
            uy *= V / sp
            px += ux * dt
            py += uy * dt
            t += dt
        return t

    def test_biased_arrival_later_than_unbiased(self):
        t_unbiased = self._planar_integration(with_bias=False)
        t_biased = self._planar_integration(with_bias=True)
        self.assertGreater(t_biased, t_unbiased)
        delta = t_biased - t_unbiased
        self.assertGreater(delta, 3.0)
        self.assertLess(delta, 5.5)

    def test_rejects_nav_constant_le_one(self):
        with self.assertRaises(ValueError):
            itcg.png_baseline(1.0, VC_MPS, LAM_DOT)

    def test_rejects_negative_range_in_tgo(self):
        with self.assertRaises(ValueError):
            itcg.tgo_estimate_png(VC_MPS, -100.0)

    def test_rejects_nonpositive_gain_in_bias(self):
        with self.assertRaises(ValueError):
            itcg.impact_time_bias(-1.0, VC_MPS, TGO_DES, 26.666666666666668)


if __name__ == "__main__":
    unittest.main()
