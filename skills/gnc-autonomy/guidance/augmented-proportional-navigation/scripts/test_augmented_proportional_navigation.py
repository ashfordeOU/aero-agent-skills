"""Contract test for augmented proportional navigation (APN) guidance logic.

Deterministic stdlib unittest, offline. Run:
    python3 scripts/test_augmented_proportional_navigation.py
"""

import math
import unittest

import augmented_proportional_navigation_logic as apn

G0 = apn.G0
N_DEFAULT = apn.N_DEFAULT

# Worked example 1 (planar intercept): Vc 900 m/s, LOS rate 0.005 rad/s,
# target lateral acceleration 10 m/s2, navigation ratio 4.0.
VC_EX = 900.0
LAM_EX = 0.005
AT_EX = 10.0
N_EX = 4.0
PN_EX = N_EX * VC_EX * LAM_EX  # 18.0 m/s2, spec bound 15-21
APN_EX = N_EX * (VC_EX * LAM_EX + AT_EX / 2.0)  # 38.0 m/s2, spec bound 34-42

# Worked geometry: rel_pos = (8000, 6000) m, rel_vel = (-600, -300) m/s.
RX, RY, VX, VY = 8000.0, 6000.0, -600.0, -300.0
R_GEOM = math.hypot(RX, RY)  # 10000.0 m
VC_GEOM = -(RX * VX + RY * VY) / R_GEOM  # 660.0 m/s
# LOS rate at this geometry from the spec formula is +0.012 rad/s (the
# velocity is 10.3 deg off the head-on course); the near-head-on course
# closing at 660 m/s carries the small -1.15e-4 rad/s anchor (see
# test_los_rate_near_head_on_regime).


class LosRateTest(unittest.TestCase):
    def test_los_rate_worked_geometry_formula_value(self):
        # Exact formula value for the stated geometry; run-to-run stable.
        self.assertAlmostEqual(
            apn.los_rate(RX, RY, VX, VY), 0.012, places=12
        )

    def test_los_rate_zero_on_pure_closing(self):
        # Pure closing along the LOS: no rotation of the line of sight.
        self.assertAlmostEqual(apn.los_rate(1000.0, 0.0, -200.0, 0.0), 0.0)

    def test_los_rate_sign_mirror_rel_vel_y(self):
        # A crossing target mirrored about the LOS flips the sign.
        lam_up = apn.los_rate(8000.0, 6000.0, 0.0, 300.0)
        lam_down = apn.los_rate(8000.0, 6000.0, 0.0, -300.0)
        self.assertAlmostEqual(lam_up, -lam_down, places=12)
        self.assertGreater(lam_up, 0.0)
        self.assertLess(lam_down, 0.0)

    def test_los_rate_near_head_on_regime(self):
        # Near-head-on closing at 660 m/s: LOS rate within the spec bound
        # -2e-4..0, about -1.15e-4 rad/s; a slight cross-range drift on a
        # closing course stays in the same small regime.
        lam = apn.los_rate(8000.0, 6000.0, -527.31, -396.92)
        self.assertGreaterEqual(lam, -2e-4)
        self.assertLessEqual(lam, 0.0)
        self.assertAlmostEqual(lam, -1.15e-4, delta=1e-6)
        lam2 = apn.los_rate(10000.0, 0.0, -660.0, -1.15)
        self.assertGreaterEqual(lam2, -2e-4)
        self.assertLessEqual(lam2, 0.0)

    def test_los_rate_zero_relative_position_raises(self):
        with self.assertRaises(ValueError):
            apn.los_rate(0.0, 0.0, -200.0, 50.0)


class ClosingVelocityTest(unittest.TestCase):
    def test_closing_velocity_worked_geometry(self):
        vc = apn.closing_velocity(RX, RY, VX, VY)
        self.assertAlmostEqual(vc, 660.0, places=9)
        self.assertAlmostEqual(vc, VC_GEOM, places=12)

    def test_closing_velocity_positive_when_closing(self):
        # Velocity anti-parallel to the LOS is pure closing at the speed.
        vc = apn.closing_velocity(1000.0, 0.0, -200.0, 0.0)
        self.assertAlmostEqual(vc, 200.0)
        vc2 = apn.closing_velocity(8000.0, 6000.0, -528.0, -396.0)
        self.assertAlmostEqual(vc2, 660.0, places=9)

    def test_closing_velocity_negative_passthrough_opening(self):
        # Opening geometry: Vc negative and passed through unchanged.
        vc = apn.closing_velocity(1000.0, 0.0, 200.0, 0.0)
        self.assertAlmostEqual(vc, -200.0)

    def test_closing_velocity_zero_relative_position_raises(self):
        with self.assertRaises(ValueError):
            apn.closing_velocity(0.0, 0.0, -200.0, 0.0)


class PnCommandTest(unittest.TestCase):
    def test_pn_worked_example_within_spec_bound(self):
        a = apn.pn_command(N_EX, VC_EX, LAM_EX)
        self.assertAlmostEqual(a, PN_EX, places=12)
        self.assertGreaterEqual(a, 15.0)
        self.assertLessEqual(a, 21.0)
        self.assertAlmostEqual(a, 18.0, places=9)

    def test_pn_zero_los_rate_zero_command(self):
        self.assertAlmostEqual(apn.pn_command(4.0, 900.0, 0.0), 0.0)

    def test_pn_valueerror_nonpositive_ratio(self):
        for bad in (0.0, -1.0, -4.0):
            with self.assertRaises(ValueError):
                apn.pn_command(bad, VC_EX, LAM_EX)

    def test_pn_negative_command_for_opening_geometry(self):
        # Vc negative flips the sign of the command (target recedes).
        a = apn.pn_command(4.0, -300.0, 0.005)
        self.assertAlmostEqual(a, -6.0)


class ApnCommandTest(unittest.TestCase):
    def test_apn_worked_example_within_spec_bound(self):
        a = apn.apn_command(N_EX, VC_EX, LAM_EX, AT_EX)
        self.assertAlmostEqual(a, APN_EX, places=12)
        self.assertGreaterEqual(a, 34.0)
        self.assertLessEqual(a, 42.0)
        self.assertAlmostEqual(a, 38.0, places=9)

    def test_apn_augmentation_term_adds_n_over_2_times_at(self):
        # The augmentation term adds exactly N/2 * a_T = 20 m/s2 to PN.
        pn_cmd = apn.pn_command(N_EX, VC_EX, LAM_EX)
        apn_cmd = apn.apn_command(N_EX, VC_EX, LAM_EX, AT_EX)
        self.assertAlmostEqual(apn_cmd - pn_cmd, N_EX / 2.0 * AT_EX, places=12)
        self.assertAlmostEqual(apn_cmd - pn_cmd, 20.0, places=9)

    def test_apn_degenerate_zero_target_accel_equals_pn(self):
        a_apn = apn.apn_command(N_EX, VC_EX, LAM_EX, 0.0)
        a_pn = apn.pn_command(N_EX, VC_EX, LAM_EX)
        self.assertAlmostEqual(a_apn, a_pn, places=12)

    def test_apn_scaling_doubled_target_accel(self):
        # Doubling a_T grows the command by exactly N/2 * the increment.
        a1 = apn.apn_command(N_EX, VC_EX, LAM_EX, 10.0)
        a2 = apn.apn_command(N_EX, VC_EX, LAM_EX, 20.0)
        self.assertAlmostEqual(a2 - a1, N_EX / 2.0 * 10.0, places=12)
        self.assertAlmostEqual(a2 - a1, 20.0, places=9)

    def test_apn_negative_target_accel_allowed(self):
        # target_lateral_accel may be any sign; no ValueError.
        a = apn.apn_command(N_EX, VC_EX, LAM_EX, -10.0)
        self.assertAlmostEqual(a, N_EX * (VC_EX * LAM_EX - 5.0), places=12)

    def test_apn_valueerror_nonpositive_ratio(self):
        for bad in (0.0, -1.0, -2.0):
            with self.assertRaises(ValueError):
                apn.apn_command(bad, VC_EX, LAM_EX, AT_EX)


class CommandedAccelGTest(unittest.TestCase):
    def test_pn_worked_example_g(self):
        g = apn.commanded_accel_g(PN_EX)
        self.assertAlmostEqual(g, PN_EX / G0, places=12)
        self.assertAlmostEqual(g, 1.8355, delta=1e-3)

    def test_apn_worked_example_g(self):
        g = apn.commanded_accel_g(APN_EX)
        self.assertAlmostEqual(g, APN_EX / G0, places=12)
        self.assertAlmostEqual(g, 3.8749, delta=1e-3)

    def test_g_reference_points(self):
        # One g at standard gravity, zero command at zero.
        self.assertAlmostEqual(apn.commanded_accel_g(G0), 1.0, places=12)
        self.assertAlmostEqual(apn.commanded_accel_g(0.0), 0.0)


class TimeToGoTest(unittest.TestCase):
    def test_time_to_go_worked_example_within_spec_bound(self):
        t = apn.time_to_go(R_GEOM, VC_GEOM)
        self.assertAlmostEqual(t, R_GEOM / VC_GEOM, places=12)
        self.assertGreaterEqual(t, 13.0)
        self.assertLessEqual(t, 17.0)
        self.assertAlmostEqual(t, 15.1515, delta=1e-3)

    def test_time_to_go_zero_range_zero(self):
        self.assertAlmostEqual(apn.time_to_go(0.0, 660.0), 0.0)

    def test_time_to_go_negative_range_raises(self):
        with self.assertRaises(ValueError):
            apn.time_to_go(-100.0, 660.0)

    def test_time_to_go_valueerror_nonpositive_closing(self):
        for bad in (0.0, -660.0, -1.0):
            with self.assertRaises(ValueError):
                apn.time_to_go(10000.0, bad)


class ApnAssessmentTest(unittest.TestCase):
    DOC_KEYS = {
        "los_rate",
        "closing_velocity",
        "pn_command_m_s2",
        "apn_command_m_s2",
        "pn_command_g",
        "apn_command_g",
        "time_to_go_s",
    }

    def test_assessment_keys_exactly_documented(self):
        a = apn.apn_assessment(RX, RY, VX, VY, AT_EX, range_m=R_GEOM)
        self.assertEqual(set(a.keys()), self.DOC_KEYS)
        # Without range_m the same documented keys hold and time_to_go_s is
        # None, per the convenience chain contract.
        b = apn.apn_assessment(RX, RY, VX, VY, AT_EX)
        self.assertEqual(set(b.keys()), self.DOC_KEYS)
        self.assertIsNone(b["time_to_go_s"])

    def test_assessment_with_range_matches_direct_calls(self):
        a = apn.apn_assessment(RX, RY, VX, VY, AT_EX, range_m=R_GEOM)
        lam = apn.los_rate(RX, RY, VX, VY)
        vc = apn.closing_velocity(RX, RY, VX, VY)
        pn_cmd = apn.pn_command(N_DEFAULT, vc, lam)
        self.assertAlmostEqual(a["los_rate"], lam, places=12)
        self.assertAlmostEqual(a["closing_velocity"], vc, places=12)
        self.assertAlmostEqual(a["pn_command_m_s2"], pn_cmd, places=12)
        self.assertAlmostEqual(
            a["apn_command_m_s2"],
            apn.apn_command(N_DEFAULT, vc, lam, AT_EX),
            places=12,
        )
        self.assertAlmostEqual(
            a["pn_command_g"], apn.commanded_accel_g(pn_cmd), places=12
        )
        self.assertAlmostEqual(
            a["apn_command_g"],
            apn.commanded_accel_g(apn.apn_command(N_DEFAULT, vc, lam, AT_EX)),
            places=12,
        )
        self.assertAlmostEqual(a["time_to_go_s"], R_GEOM / vc, places=12)

    def test_assessment_explicit_ratio_overrides_default(self):
        a = apn.apn_assessment(RX, RY, VX, VY, AT_EX, navigation_ratio=3.0,
                               range_m=R_GEOM)
        self.assertAlmostEqual(a["pn_command_m_s2"], 3.0 * 660.0 * 0.012)
        self.assertAlmostEqual(
            a["apn_command_m_s2"], 3.0 * (660.0 * 0.012 + 5.0)
        )
        # Default navigation ratio N_DEFAULT = 4.0 reproduces the same chain.
        a_def = apn.apn_assessment(RX, RY, VX, VY, AT_EX, range_m=R_GEOM)
        self.assertAlmostEqual(
            a_def["pn_command_m_s2"], N_DEFAULT * 660.0 * 0.012
        )

    def test_assessment_zero_position_raises(self):
        with self.assertRaises(ValueError):
            apn.apn_assessment(0.0, 0.0, VX, VY, AT_EX)


class DeterminismTest(unittest.TestCase):
    def test_module_constants(self):
        self.assertAlmostEqual(G0, 9.80665)
        self.assertAlmostEqual(N_DEFAULT, 4.0)

    def test_run_to_run_identical_floats(self):
        first = apn.apn_assessment(RX, RY, VX, VY, AT_EX, range_m=R_GEOM)
        second = apn.apn_assessment(RX, RY, VX, VY, AT_EX, range_m=R_GEOM)
        for k in first:
            self.assertEqual(first[k], second[k])

    def test_no_randomness_in_module_source(self):
        import inspect
        import re

        import augmented_proportional_navigation_logic as mod

        src = inspect.getsource(mod)
        # No RNG import, no seeded or unseeded stochastic call, no time-based
        # or identity-based entropy source anywhere in the module.
        self.assertNotIn("import random", src)
        self.assertNotIn("from random", src)
        self.assertNotIn("numpy", src)
        self.assertNotIn("time.time", src)
        self.assertNotIn("id(", src)
        self.assertIsNone(re.search(r"\bseed\s*\(", src))


if __name__ == "__main__":
    unittest.main()
