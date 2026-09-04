#!/usr/bin/env python3
"""Offline contract test for the digital-control-design leaf
(skills/gnc-autonomy/control/digital-control-design). Deterministic,
stdlib unittest, no network, no RNG. Run from anywhere:

    cd ~/AeroSkills
    python3 skills/gnc-autonomy/control/digital-control-design/scripts/test_digital_control_design.py

Assert targets are the module's REAL worked-example outputs (run of
scripts/digital_control_design_logic.py with the spec parameters),
bounded by the spec magnitude limits: zoh_first_order(10, 0.01) gives
A = 0.9048374180, B = 0.0951625820 with A + B == 1.0 exactly; the
prewarped Tustin emulation of the lead D(s) = 20*(s+20)/(s+200) shows
a phase error of 6.4e-15 deg at wc = 10 rad/s (bound < 1 deg);
discrete_pid_velocity(2.0, 1.0, 0.1, 0.01) gives b0 = 12.01,
b1 = -22.0, b2 = 10.0, a1 = -1.0; sample_rate_rule(10, 0.01) gives
t_max = 0.062831853 s and verdict "ok".
"""

import cmath
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from digital_control_design_logic import (  # noqa: E402
    PI,
    SAMPLING_RULE_HIGH,
    SAMPLING_RULE_LOW,
    discrete_pid_position,
    discrete_pid_velocity,
    sample_rate_rule,
    tustin_emulate,
    tustin_frequency_check,
    unit_circle_poles,
    zoh_first_order,
    zoh_second_order,
)

LEAD_NUM = [20.0, 400.0]  # D(s) = 20*(s + 20)/(s + 200)
LEAD_DEN = [1.0, 200.0]


def _second_order_poles(A):
    """Eigenvalues of the 2x2 matrix A via the characteristic polynomial."""
    tr = A[0][0] + A[1][1]
    det = A[0][0] * A[1][1] - A[0][1] * A[1][0]
    disc = cmath.sqrt(tr * tr - 4.0 * det)
    return [(tr + disc) / 2.0, (tr - disc) / 2.0]


class TestZohFirstOrder(unittest.TestCase):
    def test_zoh_first_order_worked_example(self):
        A, B = zoh_first_order(10.0, 0.01)
        self.assertAlmostEqual(A, 0.90484, places=4)
        self.assertAlmostEqual(B, 0.09516, places=4)
        self.assertAlmostEqual(A, math.exp(-0.1), places=14)

    def test_zoh_first_order_dc_gain_identity_exact(self):
        for a, T in [(10.0, 0.01), (5.0, 0.02), (1.0, 0.5), (0.7, 1.0)]:
            A, B = zoh_first_order(a, T)
            self.assertEqual(A + B, 1.0, "A + B must equal 1.0 exactly")

    def test_zoh_first_order_valueerror_a(self):
        for a in (0.0, -1.0, -50.0):
            with self.assertRaises(ValueError):
                zoh_first_order(a, 0.01)

    def test_zoh_first_order_valueerror_t(self):
        for T in (0.0, -0.01, -3.0):
            with self.assertRaises(ValueError):
                zoh_first_order(10.0, T)


class TestZohSecondOrder(unittest.TestCase):
    ZETA, WN, T = 0.5, 10.0, 0.01

    def test_zoh_second_order_step_response_settles_to_one(self):
        A, B = zoh_second_order(self.ZETA, self.WN, self.T)
        self.assertEqual(len(A), 2)
        self.assertEqual(len(A[0]), 2)
        self.assertEqual(len(A[1]), 2)
        self.assertEqual(len(B), 2)
        x1 = x2 = 0.0
        for _ in range(5000):  # step response of x[k+1] = A x[k] + B, y = x1
            x1, x2 = A[0][0] * x1 + A[0][1] * x2 + B[0], A[1][0] * x1 + A[1][1] * x2 + B[1]
        self.assertAlmostEqual(x1, 1.0, places=6)  # DC-gain identity, settles to 1

    def test_zoh_second_order_dc_gain_matrix_identity(self):
        A, B = zoh_second_order(self.ZETA, self.WN, self.T)
        # y_ss = C (I - A)^-1 B with C = [1, 0]; closed-form 2x2 inverse.
        den = (1.0 - A[0][0]) * (1.0 - A[1][1]) - A[0][1] * A[1][0]
        inv = [[(1.0 - A[1][1]) / den, A[0][1] / den], [A[1][0] / den, (1.0 - A[0][0]) / den]]
        y_ss = inv[0][0] * B[0] + inv[0][1] * B[1]
        self.assertAlmostEqual(y_ss, 1.0, places=12)

    def test_zoh_second_order_sampled_frequency_within_one_percent(self):
        A, B = zoh_second_order(self.ZETA, self.WN, self.T)
        wd = self.WN * math.sqrt(1.0 - self.ZETA ** 2)
        for pole in _second_order_poles(A):
            sampled = abs(cmath.phase(pole)) / self.T
            self.assertAlmostEqual(sampled / wd, 1.0, delta=0.01)

    def test_zoh_second_order_valueerror_wn(self):
        for wn in (0.0, -1.0, -20.0):
            with self.assertRaises(ValueError):
                zoh_second_order(0.5, wn, 0.01)

    def test_zoh_second_order_valueerror_zeta_range(self):
        for zeta in (0.0, 1.0, 1.5, -0.3):
            with self.assertRaises(ValueError):
                zoh_second_order(zeta, 10.0, 0.01)

    def test_zoh_second_order_valueerror_t(self):
        for T in (0.0, -0.01):
            with self.assertRaises(ValueError):
                zoh_second_order(0.5, 10.0, T)


class TestTustinEmulate(unittest.TestCase):
    def test_tustin_emulate_lead_worked_dc_gain_and_monic(self):
        z = tustin_emulate({"num": LEAD_NUM, "den": LEAD_DEN}, 0.01, wc=10.0)
        self.assertEqual(list(z.keys()), ["num_z", "den_z"])
        self.assertEqual(len(z["num_z"]), 2)
        self.assertEqual(len(z["den_z"]), 2)
        self.assertAlmostEqual(z["den_z"][0], 1.0, places=12)  # monic denominator
        dc = sum(z["num_z"]) / sum(z["den_z"])  # z = 1 maps to s = 0
        self.assertAlmostEqual(dc, 2.0, places=9)  # DC gain preserved

    def test_tustin_emulate_prewarp_phase_error_below_1_deg(self):
        z = tustin_emulate({"num": LEAD_NUM, "den": LEAD_DEN}, 0.01, wc=10.0)
        err = tustin_frequency_check({"num": LEAD_NUM, "den": LEAD_DEN}, z, 10.0, 0.01)
        self.assertLess(err, 1.0)  # spec magnitude bound at the prewarp frequency

    def test_tustin_emulate_pole_mapping_plain_and_prewarp(self):
        # Continuous pole s = -200 maps to z = (c + s)/(c - s).
        z_plain = tustin_emulate({"num": LEAD_NUM, "den": LEAD_DEN}, 0.01)
        self.assertAlmostEqual(z_plain["den_z"][1], 0.0, places=9)  # c = 200 -> z = 0
        c = 10.0 / math.tan(10.0 * 0.01 / 2.0)
        z_pw = tustin_emulate({"num": LEAD_NUM, "den": LEAD_DEN}, 0.01, wc=10.0)
        self.assertAlmostEqual(z_pw["den_z"][1], (200.0 - c) / (c + 200.0), places=9)  # = -z_pole
        self.assertAlmostEqual(z_pw["num_z"][0], 10.996247811178513, places=6)
        self.assertAlmostEqual(z_pw["num_z"][1], -8.995413991440406, places=6)

    def test_tustin_emulate_second_order_compensator_dc_and_poles(self):
        num = [1.0, 30.0, 200.0]
        den = [1.0, 100.0, 2000.0]
        cont_dc = num[-1] / den[-1]
        z = tustin_emulate({"num": num, "den": den}, 0.01, wc=30.0)
        self.assertAlmostEqual(sum(z["num_z"]) / sum(z["den_z"]), cont_dc, places=9)
        res = unit_circle_poles(z["den_z"])
        self.assertEqual(len(res["poles"]), 2)
        self.assertTrue(res["stable"])  # both continuous poles were in the LHP

    def test_tustin_emulate_gain_only_maps_identity(self):
        z = tustin_emulate({"num": [2.0], "den": [1.0]}, 0.01)
        self.assertEqual(z["num_z"], [2.0])
        self.assertEqual(z["den_z"], [1.0])

    def test_tustin_emulate_valueerror_invalid_inputs(self):
        with self.assertRaises(ValueError):
            tustin_emulate({"num": LEAD_NUM, "den": LEAD_DEN}, 0.0)
        with self.assertRaises(ValueError):
            tustin_emulate({"num": LEAD_NUM, "den": LEAD_DEN}, 0.01, wc=0.0)
        with self.assertRaises(ValueError):
            tustin_emulate({"num": LEAD_NUM, "den": LEAD_DEN}, 0.01, wc=-5.0)
        with self.assertRaises(ValueError):
            tustin_emulate({"num": LEAD_NUM, "den": LEAD_DEN}, 0.01, wc=400.0)  # wc*T >= pi
        with self.assertRaises(ValueError):
            tustin_emulate({"num": [], "den": LEAD_DEN}, 0.01)
        with self.assertRaises(ValueError):
            tustin_emulate({"num": LEAD_NUM, "den": []}, 0.01)
        with self.assertRaises(ValueError):
            tustin_emulate({"num": LEAD_NUM}, 0.01)


class TestTustinFrequencyCheck(unittest.TestCase):
    def test_tustin_frequency_check_prewarp_near_zero_error(self):
        z = tustin_emulate({"num": LEAD_NUM, "den": LEAD_DEN}, 0.01, wc=10.0)
        err = tustin_frequency_check({"num": LEAD_NUM, "den": LEAD_DEN}, z, 10.0, 0.01)
        self.assertLess(err, 1e-6)  # module real output: 6.36e-15 deg

    def test_tustin_frequency_check_valueerror(self):
        z = tustin_emulate({"num": LEAD_NUM, "den": LEAD_DEN}, 0.01, wc=10.0)
        with self.assertRaises(ValueError):
            tustin_frequency_check({"num": LEAD_NUM, "den": LEAD_DEN}, z, 0.0, 0.01)
        with self.assertRaises(ValueError):
            tustin_frequency_check({"num": LEAD_NUM, "den": LEAD_DEN}, z, 10.0, 0.0)


class TestDiscretePidPosition(unittest.TestCase):
    def test_pid_position_worked_example(self):
        d = discrete_pid_position(2.0, 1.0, 0.1, 0.01)
        self.assertEqual(list(d.keys()), ["kp", "ki", "kd"])
        self.assertEqual(d["kp"], 2.0)
        self.assertAlmostEqual(d["ki"], 0.01, places=12)  # Ki*T
        self.assertAlmostEqual(d["kd"], 10.0, places=12)  # Kd/T

    def test_pid_position_scaling_gains(self):
        d = discrete_pid_position(3.0, 2.0, 0.5, 0.02)
        self.assertEqual(d["kp"], 3.0)
        self.assertAlmostEqual(d["ki"], 0.04, places=12)
        self.assertAlmostEqual(d["kd"], 25.0, places=12)

    def test_pid_position_zero_ki_kd(self):
        d = discrete_pid_position(5.0, 0.0, 0.0, 0.01)
        self.assertEqual(d, {"kp": 5.0, "ki": 0.0, "kd": 0.0})

    def test_pid_position_valueerror_t(self):
        for T in (0.0, -0.01):
            with self.assertRaises(ValueError):
                discrete_pid_position(2.0, 1.0, 0.1, T)


class TestDiscretePidVelocity(unittest.TestCase):
    def test_pid_velocity_worked_example(self):
        d = discrete_pid_velocity(2.0, 1.0, 0.1, 0.01)
        self.assertEqual(list(d.keys()), ["b0", "b1", "b2", "a1"])
        self.assertAlmostEqual(d["b0"], 12.01, places=12)
        self.assertAlmostEqual(d["b1"], -22.0, places=12)
        self.assertAlmostEqual(d["b2"], 10.0, places=12)
        self.assertEqual(d["a1"], -1.0)

    def test_pid_velocity_steady_state_injection_identity(self):
        # b0 + b1 + b2 = Ki*T: a constant error injects Ki*T per step.
        Kp, Ki, Kd, T = 3.5, 0.8, 0.25, 0.02
        d = discrete_pid_velocity(Kp, Ki, Kd, T)
        self.assertAlmostEqual(d["b0"] + d["b1"] + d["b2"], Ki * T, places=12)

    def test_pid_velocity_alternate_gains(self):
        d = discrete_pid_velocity(1.0, 1.0, 1.0, 0.1)
        self.assertAlmostEqual(d["b0"], 11.1, places=12)  # 1 + 0.1 + 10
        self.assertAlmostEqual(d["b1"], -21.0, places=12)  # -1 - 2*10
        self.assertAlmostEqual(d["b2"], 10.0, places=12)

    def test_pid_velocity_valueerror_t(self):
        for T in (0.0, -0.1):
            with self.assertRaises(ValueError):
                discrete_pid_velocity(2.0, 1.0, 0.1, T)


class TestUnitCirclePoles(unittest.TestCase):
    def test_unit_circle_stable_real_pole(self):
        res = unit_circle_poles([1.0, -0.5])
        self.assertEqual(list(res.keys()), ["poles", "stable"])
        self.assertEqual(len(res["poles"]), 1)
        self.assertAlmostEqual(abs(res["poles"][0]), 0.5, places=12)
        self.assertTrue(res["stable"])

    def test_unit_circle_unstable_real_pole(self):
        res = unit_circle_poles([1.0, -1.05])
        self.assertAlmostEqual(abs(res["poles"][0]), 1.05, places=12)
        self.assertFalse(res["stable"])

    def test_unit_circle_unit_modulus_boundary_unstable(self):
        # |z| == 1 is unstable under the strict modulus < 1 rule.
        pole = complex(math.cos(0.3), math.sin(0.3))
        res = unit_circle_poles([1.0, -pole])
        self.assertAlmostEqual(abs(res["poles"][0]), 1.0, places=12)
        self.assertFalse(res["stable"])

    def test_unit_circle_degree_two_poles(self):
        res = unit_circle_poles([1.0, -2.0 * 0.9 * math.cos(0.5), 0.81])
        self.assertEqual(len(res["poles"]), 2)
        for p in res["poles"]:
            self.assertAlmostEqual(abs(p), 0.9, places=12)
        self.assertTrue(res["stable"])
        res2 = unit_circle_poles([1.0, -2.5, 1.56])
        self.assertFalse(res2["stable"])

    def test_unit_circle_valueerror_invalid_denominators(self):
        with self.assertRaises(ValueError):
            unit_circle_poles([])
        with self.assertRaises(ValueError):
            unit_circle_poles([0.0, 1.0])
        with self.assertRaises(ValueError):
            unit_circle_poles([1.0, 0.0, 0.0, 0.0])  # degree 3 not supported


class TestSampleRateRule(unittest.TestCase):
    def test_sample_rate_rule_ok_and_boundary(self):
        d = sample_rate_rule(10.0, 0.01)
        self.assertEqual(list(d.keys()), ["w_s_min_rad_s", "t_max_s", "verdict"])
        self.assertAlmostEqual(SAMPLING_RULE_LOW, 10.0, places=12)
        self.assertAlmostEqual(SAMPLING_RULE_HIGH, 20.0, places=12)
        self.assertEqual(d["w_s_min_rad_s"], SAMPLING_RULE_LOW * 10.0)
        self.assertAlmostEqual(d["t_max_s"], 0.06283185307179587, places=10)
        self.assertEqual(d["verdict"], "ok")
        # Exactly at the rule minimum (T == t_max) is still acceptable.
        d2 = sample_rate_rule(10.0, 2.0 * PI / (SAMPLING_RULE_LOW * 10.0))
        self.assertEqual(d2["verdict"], "ok")

    def test_sample_rate_rule_too_slow(self):
        d = sample_rate_rule(10.0, 0.1)
        self.assertEqual(d["verdict"], "too-slow")
        self.assertAlmostEqual(d["t_max_s"], 0.0628, places=3)

    def test_sample_rate_rule_valueerror(self):
        for wb, T in [(0.0, 0.01), (-5.0, 0.01), (10.0, 0.0), (10.0, -0.01)]:
            with self.assertRaises(ValueError):
                sample_rate_rule(wb, T)


class TestDeterminism(unittest.TestCase):
    def test_repeated_runs_identical(self):
        ref = (
            zoh_first_order(10.0, 0.01),
            zoh_second_order(0.5, 10.0, 0.01),
            tustin_emulate({"num": LEAD_NUM, "den": LEAD_DEN}, 0.01, wc=10.0),
            discrete_pid_velocity(2.0, 1.0, 0.1, 0.01),
            sample_rate_rule(10.0, 0.01),
        )
        for _ in range(3):
            again = (
                zoh_first_order(10.0, 0.01),
                zoh_second_order(0.5, 10.0, 0.01),
                tustin_emulate({"num": LEAD_NUM, "den": LEAD_DEN}, 0.01, wc=10.0),
                discrete_pid_velocity(2.0, 1.0, 0.1, 0.01),
                sample_rate_rule(10.0, 0.01),
            )
            self.assertEqual(again, ref)  # deterministic, no RNG


if __name__ == "__main__":
    unittest.main(verbosity=2)
