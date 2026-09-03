#!/usr/bin/env python3
"""Gate 3 contract test: low-altitude windshear and microburst hazard logic.

Exercises scripts/windshear_analysis_logic.py (stdlib unittest,
offline, deterministic). Contract: docs/harness-contract.md gate 3.
Anchors (worked example from the SKILL body):
- Approach at v = 75 m/s, mass 55,000 kg -> W = 539,365.75 N, engines
  at the approach setting with T = D = 77,000 N (F_available = 0).
- Headwind decreasing at 8 kt/s -> a_wind = -8*463/900 = -4.11556 m/s^2.
- f_factor_from_thrust = 0.419670; plus w_d/v = 6/75 = 0.08 the total
  F-factor is 0.499670 -> severe; energy height loss rate 37.475 m/s;
  altitude loss over 20 s 749.505 m; recovery thrust increment
  269,504.8 N; downdraft out-climb verdict descend.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import windshear_analysis_logic as ws  # noqa: E402


MASS = 55000.0
W = 539365.75  # weight_from_mass(55000, 9.80665)
T_APPR = 77000.0
D_APPR = 77000.0
V = 75.0
A_WIND_HZ = -8.0 * ws.KT_TO_MS  # -4.115555555555556 m/s^2
DOWN = 6.0
TIME_S = 20.0
F_SHEAR_EX = 0.4196698725411385  # decreasing-headwind term, computed module value
F_TOTAL_EX = 0.49966987254113854  # total F-factor of the worked example
LOSS_EX = 37.47524044058539  # energy height loss rate, m/s
ALT_EX = 749.5048088117078  # altitude loss over 20 s, m
DT_EX = 269504.8155555556  # recovery thrust increment, N


class TestModuleConstants(unittest.TestCase):
    def test_module_constants(self):
        self.assertEqual(ws.G0, 9.80665)
        self.assertEqual(ws.KT_TO_MS, 463.0 / 900.0)
        self.assertAlmostEqual(ws.KT_TO_MS * 3600.0, 1852.0, places=9)
        self.assertEqual((ws.SEVERITY_LOW, ws.SEVERITY_MODERATE, ws.SEVERITY_HIGH),
                         (0.05, 0.10, 0.15))


class TestWeightFromMass(unittest.TestCase):
    def test_weight_from_mass_example(self):
        self.assertAlmostEqual(ws.weight_from_mass(MASS), W, places=6)
        self.assertAlmostEqual(ws.weight_from_mass(MASS / 2.0), W / 2.0, places=6)

    def test_weight_from_mass_rejects_non_positive_mass(self):
        for bad in (0.0, -1000.0):
            with self.assertRaises(ValueError):
                ws.weight_from_mass(bad)


class TestFFactorFromThrust(unittest.TestCase):
    def test_calm_air_zero_excess_is_zero(self):
        self.assertAlmostEqual(ws.f_factor_from_thrust(T_APPR, D_APPR, W, 0.0), 0.0)

    def test_excess_thrust_and_shear_combine(self):
        # Excess thrust ratio 0.1 in calm air, and added to the shear term.
        self.assertAlmostEqual(ws.f_factor_from_thrust(W * 0.1, 0.0, W, 0.0), 0.1, places=9)
        f = ws.f_factor_from_thrust(T_APPR + W * 0.1, D_APPR, W, A_WIND_HZ)
        self.assertAlmostEqual(f, 0.1 + F_SHEAR_EX, places=9)

    def test_decreasing_headwind_example(self):
        # 8 kt/s headwind decrease at T = D: F = -a_wind/g = 0.419670.
        self.assertAlmostEqual(ws.f_factor_from_thrust(T_APPR, D_APPR, W, A_WIND_HZ), F_SHEAR_EX)
        # 1 kt/s = 0.514444 m/s^2: F contribution per kt/s is KT_TO_MS/g.
        self.assertAlmostEqual(
            ws.f_factor_from_thrust(T_APPR, D_APPR, W, -ws.KT_TO_MS), ws.KT_TO_MS / ws.G0
        )

    def test_increasing_headwind_lowers_f(self):
        # An increasing headwind is a performance increase: F goes negative.
        f = ws.f_factor_from_thrust(T_APPR, D_APPR, W, -A_WIND_HZ)
        self.assertAlmostEqual(f, -F_SHEAR_EX)

    def test_round_trip_zero_f_identity(self):
        # a_wind = g*(t - d)/w cancels the excess thrust term exactly: F = 0.
        a = ws.G0 * (W * 0.05) / W
        self.assertAlmostEqual(ws.f_factor_from_thrust(W * 0.05, 0.0, W, a), 0.0, places=12)

    def test_rejects_non_physical_inputs(self):
        with self.assertRaises(ValueError):
            ws.f_factor_from_thrust(-1.0, D_APPR, W, 0.0)  # negative thrust
        with self.assertRaises(ValueError):
            ws.f_factor_from_thrust(T_APPR, -1.0, W, 0.0)  # negative drag
        with self.assertRaises(ValueError):
            ws.f_factor_from_thrust(T_APPR, D_APPR, 0.0, 0.0)  # zero weight
        with self.assertRaises(ValueError):
            ws.f_factor_from_thrust(T_APPR, D_APPR, -W, 0.0)  # negative weight
        with self.assertRaises(ValueError):
            ws.f_factor_from_thrust(T_APPR, D_APPR, W, 0.0, g=0.0)


class TestFFactorFromWindGradients(unittest.TestCase):
    def test_zero_gradient_downdraft_only(self):
        # t = d so dh/dt = 0, a_wind = 0: F = w_d/v = 0.08, gradient irrelevant.
        self.assertAlmostEqual(ws.f_factor_from_wind_gradients(0.0, DOWN, V, W, T_APPR, D_APPR), 0.08)
        self.assertAlmostEqual(ws.f_factor_from_wind_gradients(0.05, DOWN, V, W, T_APPR, D_APPR), 0.08)

    def test_no_gradient_excess_only(self):
        self.assertAlmostEqual(
            ws.f_factor_from_wind_gradients(0.0, 0.0, V, W, T_APPR + W * 0.05, D_APPR),
            0.05,
            places=9,
        )

    def test_climb_into_increasing_headwind_reduces_f(self):
        # Excess ratio 0.1 at v = 75: dh/dt = 7.5 m/s; gradient 0.05 1/s gives
        # a_wind = +0.375 m/s^2 -> -a_wind/g = -0.038239, F = 0.061761.
        f = ws.f_factor_from_wind_gradients(0.05, 0.0, V, W, T_APPR + W * 0.1, D_APPR)
        self.assertAlmostEqual(f, 0.0617606420133277)

    def test_descent_through_hazard_shear_raises_f(self):
        # Excess ratio -0.03 (approach descent): dh/dt = -2.25 m/s; gradient
        # 0.05 1/s gives a_wind = -0.1125 m/s^2, hazard, plus w_d/v = 0.08.
        f = ws.f_factor_from_wind_gradients(0.05, DOWN, V, W, T_APPR - W * 0.03, D_APPR)
        self.assertAlmostEqual(f, 0.06147180739600169)

    def test_rejects_non_physical_inputs(self):
        with self.assertRaises(ValueError):
            ws.f_factor_from_wind_gradients(0.05, DOWN, 0.0, W, T_APPR, D_APPR)  # v = 0
        with self.assertRaises(ValueError):
            ws.f_factor_from_wind_gradients(0.05, DOWN, V, 0.0, T_APPR, D_APPR)  # w = 0
        with self.assertRaises(ValueError):
            ws.f_factor_from_wind_gradients(0.05, DOWN, V, W, -1.0, D_APPR)  # t < 0


class TestSeverityClass(unittest.TestCase):
    def test_band_boundaries_inclusive_low_edge(self):
        self.assertEqual(ws.severity_class(0.0499), "low")
        self.assertEqual(ws.severity_class(0.05), "moderate")
        self.assertEqual(ws.severity_class(0.0999), "moderate")
        self.assertEqual(ws.severity_class(0.1), "high")
        self.assertEqual(ws.severity_class(0.1499), "high")
        self.assertEqual(ws.severity_class(0.15), "severe")
        self.assertEqual(ws.severity_class(0.3), "severe")

    def test_zero_negative_low_and_example_severe(self):
        self.assertEqual(ws.severity_class(0.0), "low")
        self.assertEqual(ws.severity_class(-0.2), "low")
        self.assertEqual(ws.severity_class(F_TOTAL_EX), "severe")


class TestEnergyHeightLoss(unittest.TestCase):
    def test_loss_rate_example_and_scaling(self):
        self.assertAlmostEqual(ws.energy_height_loss_rate(F_TOTAL_EX, V), LOSS_EX)
        self.assertAlmostEqual(ws.energy_height_loss_rate(0.1, 100.0), 10.0, places=9)
        self.assertEqual(ws.energy_height_loss_rate(0.0, V), 0.0)

    def test_altitude_loss_example(self):
        self.assertAlmostEqual(ws.altitude_loss(F_TOTAL_EX, V, TIME_S), ALT_EX)

    def test_altitude_loss_is_rate_times_time(self):
        f = 0.1
        self.assertAlmostEqual(
            ws.altitude_loss(f, V, TIME_S),
            ws.energy_height_loss_rate(f, V) * TIME_S,
            places=9,
        )
        self.assertEqual(ws.altitude_loss(F_TOTAL_EX, V, 0.0), 0.0)

    def test_rejects_bad_speed_and_time(self):
        for bad in (0.0, -10.0):
            with self.assertRaises(ValueError):
                ws.energy_height_loss_rate(0.1, bad)
        with self.assertRaises(ValueError):
            ws.altitude_loss(F_TOTAL_EX, V, -1.0)


class TestMaxClimbRateInDowndraft(unittest.TestCase):
    def test_zero_excess_descends(self):
        res = ws.max_climb_rate_in_downdraft(0.0, W, DOWN, V)
        self.assertEqual(res["max_climb_rate_mps"], 0.0)
        self.assertEqual(res["downdraft_mps"], DOWN)
        self.assertFalse(res["out_climbs"])
        self.assertEqual(res["verdict"], "descend")

    def test_excess_ratio_point_one_out_climbs(self):
        # RC = 75 * 0.1 = 7.5 m/s > 6 m/s downdraft.
        res = ws.max_climb_rate_in_downdraft(W * 0.1, W, DOWN, V)
        self.assertAlmostEqual(res["max_climb_rate_mps"], 7.5, places=9)
        self.assertTrue(res["out_climbs"])
        self.assertEqual(res["verdict"], "out-climb")

    def test_marginal_equality_and_updraft(self):
        # Excess thrust sized so RC exactly equals the downdraft: marginal.
        res = ws.max_climb_rate_in_downdraft(DOWN * W / V, W, DOWN, V)
        self.assertAlmostEqual(res["max_climb_rate_mps"], DOWN, places=9)
        self.assertFalse(res["out_climbs"])
        self.assertEqual(res["verdict"], "marginal")
        # An updraft (negative downdraft) is always out-climbable.
        up = ws.max_climb_rate_in_downdraft(0.0, W, -2.0, V)
        self.assertTrue(up["out_climbs"])
        self.assertEqual(up["verdict"], "out-climb")

    def test_rejects_negative_excess_and_bad_state(self):
        with self.assertRaises(ValueError):
            ws.max_climb_rate_in_downdraft(-1.0, W, DOWN, V)
        with self.assertRaises(ValueError):
            ws.max_climb_rate_in_downdraft(1000.0, 0.0, DOWN, V)
        with self.assertRaises(ValueError):
            ws.max_climb_rate_in_downdraft(1000.0, W, DOWN, 0.0)


class TestRequiredThrustIncrement(unittest.TestCase):
    def test_recovery_increment_example(self):
        # dT = W*(F_demand - F_available) with F_available = 0.
        self.assertAlmostEqual(ws.required_thrust_increment(F_TOTAL_EX, 0.0, W), DT_EX)

    def test_zero_when_sufficient_and_negative_when_excess(self):
        self.assertEqual(ws.required_thrust_increment(0.1, 0.1, W), 0.0)
        # Calm-air target 0 from an excess of 0.1: reduce thrust by 0.1 W.
        self.assertAlmostEqual(ws.required_thrust_increment(0.0, 0.1, W), -0.1 * W)

    def test_scales_with_weight_and_rejects_zero_weight(self):
        self.assertAlmostEqual(ws.required_thrust_increment(0.5, 0.0, 2.0 * W), 0.5 * 2.0 * W)
        with self.assertRaises(ValueError):
            ws.required_thrust_increment(0.1, 0.0, 0.0)


class TestWindshearVerdict(unittest.TestCase):
    def test_worked_example_verdict(self):
        v = ws.windshear_verdict(T_APPR, D_APPR, W, V, A_WIND_HZ, DOWN, time_s=TIME_S)
        self.assertAlmostEqual(v["f_available"], 0.0)
        self.assertAlmostEqual(v["f_demand"], F_TOTAL_EX)
        self.assertAlmostEqual(v["f_total"], F_TOTAL_EX)
        self.assertEqual(v["severity"], "severe")
        self.assertAlmostEqual(v["energy_height_loss_rate_mps"], LOSS_EX)
        self.assertAlmostEqual(v["altitude_loss_m"], ALT_EX)
        self.assertEqual(v["time_s"], TIME_S)
        self.assertEqual(v["max_climb_rate_mps"], 0.0)
        self.assertEqual(v["downdraft_mps"], DOWN)
        self.assertFalse(v["out_climbs"])
        self.assertEqual(v["climb_verdict"], "descend")
        self.assertAlmostEqual(v["required_thrust_increment_n"], DT_EX)
        self.assertAlmostEqual(v["thrust_to_weight_increment"], F_TOTAL_EX)
        self.assertEqual(v["escape_verdict"], "escape")

    def test_calm_encounter_verdict(self):
        v = ws.windshear_verdict(T_APPR, D_APPR, W, V, 0.0, 0.0, time_s=TIME_S)
        self.assertAlmostEqual(v["f_total"], 0.0)
        self.assertEqual(v["severity"], "low")
        self.assertEqual(v["energy_height_loss_rate_mps"], 0.0)
        self.assertEqual(v["altitude_loss_m"], 0.0)
        self.assertEqual(v["escape_verdict"], "monitor")

    def test_exact_loss_rate_with_excess_thrust(self):
        # With nonzero excess thrust the exact loss is v*(F_demand - F_available).
        t = T_APPR + W * 0.1
        v = ws.windshear_verdict(t, D_APPR, W, V, A_WIND_HZ, DOWN, time_s=TIME_S)
        self.assertAlmostEqual(v["f_available"], 0.1, places=9)
        self.assertAlmostEqual(v["f_demand"], F_TOTAL_EX)
        self.assertAlmostEqual(v["f_total"], 0.1 + F_TOTAL_EX, places=9)
        self.assertTrue(v["out_climbs"])
        self.assertEqual(v["climb_verdict"], "out-climb")
        self.assertAlmostEqual(v["energy_height_loss_rate_mps"], V * (F_TOTAL_EX - 0.1))
        self.assertEqual(v["escape_verdict"], "escape")

    def test_updraft_verdict_is_monitor(self):
        v = ws.windshear_verdict(T_APPR, D_APPR, W, V, 0.0, -2.0, time_s=TIME_S)
        self.assertEqual(v["severity"], "low")
        self.assertTrue(v["out_climbs"])
        self.assertEqual(v["escape_verdict"], "monitor")

    def test_rejects_bad_time_and_states(self):
        with self.assertRaises(ValueError):
            ws.windshear_verdict(T_APPR, D_APPR, W, V, A_WIND_HZ, DOWN, time_s=-1.0)
        with self.assertRaises(ValueError):
            ws.windshear_verdict(T_APPR, D_APPR, 0.0, V, A_WIND_HZ, DOWN)
        with self.assertRaises(ValueError):
            ws.windshear_verdict(T_APPR, D_APPR, W, 0.0, A_WIND_HZ, DOWN)


if __name__ == "__main__":
    unittest.main()
