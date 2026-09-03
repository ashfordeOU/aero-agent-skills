#!/usr/bin/env python3
"""Contract test for the reaction wheel control logic (stdlib unittest).

Deterministic, offline, runs in well under 20 s. Covers the spec worked
example (10 deg z slew, kp 0.05, kd 0.2, dt 0.01, 20 s), saturation
flags, the momentum desaturation dipole, the PD identities, the
quaternion error identities, and the ValueError rejections.
"""

import math
import unittest

import reaction_wheel_control_logic as rwc

IDENTITY = (1.0, 0.0, 0.0, 0.0)
ZERO3 = (0.0, 0.0, 0.0)
# q_ref rotates the spacecraft 10 deg about the body z axis.
Q_REF = (math.cos(math.radians(5.0)), 0.0, 0.0, math.sin(math.radians(5.0)))
KP = 0.05
KD = 0.2
J_W = 0.01
DT = 0.01
N_STEPS = 2000  # 20 s


def _slew_run(tau_max=0.1, h_max=0.5, samples=None):
    return rwc.run_wheel_control(IDENTITY, ZERO3, Q_REF, KP, KD, J_W, ZERO3,
                                 samples, tau_max, h_max, DT, N_STEPS)


class TestQuaternionError(unittest.TestCase):
    def test_identity_at_target_and_unit_norm(self):
        q_err = rwc.quaternion_error(Q_REF, Q_REF)
        for a, b in zip(q_err, IDENTITY):
            self.assertAlmostEqual(a, b, places=12)
        q_err2 = rwc.quaternion_error((0.9, 0.1, 0.1, 0.1), Q_REF)
        norm = math.sqrt(sum(c * c for c in q_err2))
        self.assertAlmostEqual(norm, 1.0, places=12)

    def test_start_value_matches_worked_example(self):
        # From identity, q_err = q0 (x) q_ref^-1 = conj(q_ref), so the
        # vector part is -sin(5 deg) about z.
        q_err = rwc.quaternion_error(IDENTITY, Q_REF)
        self.assertAlmostEqual(q_err[0], math.cos(math.radians(5.0)), places=12)
        self.assertAlmostEqual(q_err[1], 0.0, places=12)
        self.assertAlmostEqual(q_err[2], 0.0, places=12)
        self.assertAlmostEqual(q_err[3], -math.sin(math.radians(5.0)), places=12)

    def test_valueerror_nonfinite_or_wrong_length(self):
        with self.assertRaises(ValueError):
            rwc.quaternion_error((float("nan"), 0.0, 0.0, 1.0), Q_REF)
        with self.assertRaises(ValueError):
            rwc.quaternion_error(IDENTITY, (1.0, 0.0, 0.0, float("inf")))
        with self.assertRaises(ValueError):
            rwc.quaternion_error((1.0, 0.0, 0.0), Q_REF)


class TestAttitudeErrorVector(unittest.TestCase):
    def test_worked_example_angle_and_sign(self):
        # 2 * |q_err_vec| = 2 * sin(5 deg) ~= 10 deg in radians, with
        # the body short of the target by a negative z component.
        theta = rwc.attitude_error_vector(rwc.quaternion_error(IDENTITY, Q_REF))
        mag = math.sqrt(theta[0] ** 2 + theta[1] ** 2 + theta[2] ** 2)
        self.assertAlmostEqual(mag, 2.0 * math.sin(math.radians(5.0)), places=12)
        self.assertLess(abs(mag - math.radians(10.0)), 0.001)
        self.assertLess(theta[2], 0.0)
        self.assertEqual(rwc.attitude_error_vector(IDENTITY), ZERO3)

    def test_valueerror_nonfinite(self):
        with self.assertRaises(ValueError):
            rwc.attitude_error_vector((1.0, 0.0, float("nan"), 0.0))


class TestPdWheelTorque(unittest.TestCase):
    def test_zero_torque_at_zero_error_and_scaling(self):
        tau = rwc.pd_wheel_torque(KP, KD, ZERO3, ZERO3)
        for c in tau:
            self.assertAlmostEqual(c, 0.0, places=15)
        theta = rwc.attitude_error_vector(rwc.quaternion_error(IDENTITY, Q_REF))
        t1 = rwc.pd_wheel_torque(KP, KD, theta, ZERO3)
        t2 = rwc.pd_wheel_torque(2.0 * KP, KD, theta, ZERO3)
        for a, b in zip(t2, t1):
            self.assertAlmostEqual(a, 2.0 * b, places=12)

    def test_worked_example_initial_command_and_rate_term(self):
        # tau = -kp * theta_err = -0.05 * (0, 0, -0.17431) = +0.0087 z.
        theta = rwc.attitude_error_vector(rwc.quaternion_error(IDENTITY, Q_REF))
        tau = rwc.pd_wheel_torque(KP, KD, theta, ZERO3)
        self.assertAlmostEqual(tau[2], KP * 2.0 * math.sin(math.radians(5.0)),
                               places=12)
        self.assertAlmostEqual(tau[0], 0.0, places=12)
        self.assertAlmostEqual(tau[1], 0.0, places=12)
        tau_rate = rwc.pd_wheel_torque(KP, KD, ZERO3, (0.0, 0.0, 0.1))
        self.assertLess(tau_rate[2], 0.0)  # rate term opposes the rate

    def test_valueerror_nonpositive_gains(self):
        theta = rwc.attitude_error_vector(rwc.quaternion_error(IDENTITY, Q_REF))
        for kp, kd in ((0.0, KD), (-0.05, KD), (KP, 0.0), (KP, -0.2)):
            with self.assertRaises(ValueError):
                rwc.pd_wheel_torque(kp, kd, theta, ZERO3)

    def test_valueerror_nonfinite_vectors(self):
        theta = rwc.attitude_error_vector(rwc.quaternion_error(IDENTITY, Q_REF))
        with self.assertRaises(ValueError):
            rwc.pd_wheel_torque(KP, KD, (theta[0], float("nan"), theta[2]), ZERO3)
        with self.assertRaises(ValueError):
            rwc.pd_wheel_torque(KP, KD, theta, (0.0, float("inf"), 0.0))


class TestWheelMomentumUpdate(unittest.TestCase):
    def test_integrates_command_constant_without_it(self):
        h_new = rwc.wheel_momentum_update((0.1, -0.2, 0.3), ZERO3, ZERO3, DT)
        for a, b in zip(h_new, (0.1, -0.2, 0.3)):
            self.assertAlmostEqual(a, b, places=15)
        h_cmd = rwc.wheel_momentum_update(ZERO3, (0.01, 0.0, 0.0), ZERO3, DT)
        self.assertAlmostEqual(h_cmd[0], 0.01 * DT, places=15)

    def test_transport_term_cross_coupling(self):
        # omega x h_w for omega = z and h_w = x is +y, so the transport
        # term removes momentum along -y each step.
        h_new = rwc.wheel_momentum_update((1.0, 0.0, 0.0), ZERO3,
                                          (0.0, 0.0, 1.0), DT)
        self.assertAlmostEqual(h_new[0], 1.0, places=15)
        self.assertAlmostEqual(h_new[1], -DT, places=15)
        self.assertAlmostEqual(h_new[2], 0.0, places=15)

    def test_valueerror_dt_or_nonfinite(self):
        with self.assertRaises(ValueError):
            rwc.wheel_momentum_update(ZERO3, ZERO3, ZERO3, 0.0)
        with self.assertRaises(ValueError):
            rwc.wheel_momentum_update(ZERO3, ZERO3, ZERO3, -0.01)
        with self.assertRaises(ValueError):
            rwc.wheel_momentum_update((0.0, float("nan"), 0.0), ZERO3, ZERO3, DT)


class TestTorqueSaturation(unittest.TestCase):
    def test_clip_flag_and_vector_limits(self):
        clipped, flag = rwc.torque_saturation((0.2, -0.05, 0.0), 0.1)
        self.assertTrue(flag)
        self.assertAlmostEqual(clipped[0], 0.1, places=15)
        self.assertAlmostEqual(clipped[1], -0.05, places=15)
        clipped2, flag2 = rwc.torque_saturation((0.2, -0.05, 0.0),
                                                (0.05, 0.1, 0.2))
        self.assertTrue(flag2)
        self.assertAlmostEqual(clipped2[0], 0.05, places=15)

    def test_no_clip_no_flag(self):
        clipped, flag = rwc.torque_saturation((0.02, -0.05, 0.0), 0.1)
        self.assertFalse(flag)
        self.assertEqual(clipped, (0.02, -0.05, 0.0))

    def test_valueerror_nonpositive_limit(self):
        with self.assertRaises(ValueError):
            rwc.torque_saturation(ZERO3, 0.0)
        with self.assertRaises(ValueError):
            rwc.torque_saturation(ZERO3, (0.1, -0.1, 0.1))


class TestMomentumSaturation(unittest.TestCase):
    def test_excess_flag_and_within_limit(self):
        excess, flag = rwc.momentum_saturation((0.2, 0.0, 0.0),
                                               (0.1, 0.1, 0.1))
        self.assertTrue(flag)
        self.assertAlmostEqual(excess[0], 0.1, places=15)
        self.assertEqual(excess[1:], (0.0, 0.0))
        excess2, flag2 = rwc.momentum_saturation((0.05, -0.1, 0.0), 0.1)
        self.assertFalse(flag2)
        self.assertEqual(excess2, (0.0, 0.0, 0.0))

    def test_valueerror_nonpositive_limit(self):
        with self.assertRaises(ValueError):
            rwc.momentum_saturation(ZERO3, 0.0)
        with self.assertRaises(ValueError):
            rwc.momentum_saturation(ZERO3, (0.1, 0.0, 0.1))


class TestDesaturation(unittest.TestCase):
    def test_worked_example_torque_and_scaling(self):
        # h_w = 0.2 z excess over h_target, horizon 100 s.
        tau = rwc.desaturation_torque((0.0, 0.0, 0.2), ZERO3, 100.0)
        self.assertAlmostEqual(tau[2], -0.002, places=15)
        self.assertEqual(tau[:2], (-0.0, -0.0))
        tau200 = rwc.desaturation_torque((0.0, 0.0, 0.2), ZERO3, 200.0)
        self.assertAlmostEqual(tau200[2], -0.001, places=15)

    def test_partial_target_and_valueerrors(self):
        tau = rwc.desaturation_torque((0.0, 0.0, 0.2), (0.0, 0.0, 0.05), 100.0)
        self.assertAlmostEqual(tau[2], -0.0015, places=15)
        with self.assertRaises(ValueError):
            rwc.desaturation_torque((0.0, 0.0, 0.2), ZERO3, 0.0)
        with self.assertRaises(ValueError):
            rwc.desaturation_torque((0.0, 0.0, 0.2), ZERO3, -100.0)
        with self.assertRaises(ValueError):
            rwc.desaturation_torque((0.0, float("nan"), 0.2), ZERO3, 100.0)


class TestDipoleFromTorque(unittest.TestCase):
    def test_worked_example_dipole(self):
        # B = 2e-5 x, tau_desat = -0.002 z: m = (B x tau)/|B|^2 = +100 y.
        m, warn = rwc.dipole_from_torque((0.0, 0.0, -0.002), (2e-5, 0.0, 0.0))
        self.assertAlmostEqual(m[0], 0.0, places=12)
        self.assertAlmostEqual(m[1], 100.0, places=9)
        self.assertAlmostEqual(m[2], 0.0, places=12)
        self.assertFalse(warn)

    def test_torque_reconstruction_perpendicular(self):
        # For perpendicular geometry m x B equals tau_desat to 1e-12.
        tau = (0.0, 0.0, -0.002)
        b = (2e-5, 0.0, 0.0)
        m, _ = rwc.dipole_from_torque(tau, b)
        mxb = rwc._cross(m, b)
        for a, c in zip(mxb, tau):
            self.assertLess(abs(a - c), 1e-12)

    def test_alignment_warning(self):
        # Torque along the field gives a near zero dipole and a warning.
        m, warn = rwc.dipole_from_torque((0.0, 0.0, 2e-3), (0.0, 0.0, 1e-4))
        self.assertTrue(warn)
        self.assertAlmostEqual(m[2], 0.0, places=15)
        _, warn2 = rwc.dipole_from_torque((1e-3, 0.0, 0.0), (0.0, 1e-4, 0.0))
        self.assertFalse(warn2)

    def test_zero_torque_no_warning(self):
        m, warn = rwc.dipole_from_torque(ZERO3, (2e-5, 0.0, 0.0))
        self.assertFalse(warn)
        self.assertEqual(m, ZERO3)

    def test_valueerror_weak_or_nonfinite_field(self):
        with self.assertRaises(ValueError):
            rwc.dipole_from_torque((0.0, 0.0, -0.002), (0.0, 0.0, 0.0))
        with self.assertRaises(ValueError):
            rwc.dipole_from_torque((0.0, 0.0, -0.002), (1e-13, 0.0, 0.0))
        with self.assertRaises(ValueError):
            rwc.dipole_from_torque((0.0, 0.0, float("inf")), (2e-5, 0.0, 0.0))


class TestRunWheelControl(unittest.TestCase):
    def test_history_and_verdicts_structure(self):
        hist, ver = _slew_run()
        self.assertEqual(len(hist), N_STEPS)
        self.assertAlmostEqual(hist[-1]["t"], 20.0 - DT, places=12)
        for key in ("q", "omega_body", "h_w", "wheel_speed_rad_s", "tau_cmd"):
            self.assertIn(key, hist[0])
        for key in ("torque_saturated", "momentum_saturated",
                    "final_attitude_error_deg"):
            self.assertIn(key, ver)

    def test_converges_below_one_deg_at_20_s(self):
        _, ver = _slew_run()
        # Measured on this implementation: 0.11 deg at 20 s.
        self.assertLess(ver["final_attitude_error_deg"], 1.0)

    def test_small_overshoot(self):
        hist, _ = _slew_run()
        # Once the error first drops below 1 deg it stays bounded well
        # below the 10 deg maneuver (measured peak ~0.76 deg).
        crossed = None
        for i, h in enumerate(hist):
            if h["attitude_error_deg"] < 1.0:
                crossed = i
                break
        self.assertIsNotNone(crossed)
        late = [h["attitude_error_deg"] for h in hist[crossed:]]
        self.assertLess(max(late), 1.5)

    def test_initial_command_and_acceleration_direction(self):
        hist, _ = _slew_run()
        tau0 = hist[0]["tau_cmd"]
        self.assertAlmostEqual(tau0[2], KP * 2.0 * math.sin(math.radians(5.0)),
                               places=12)
        # The cluster pushes the bus toward the target: +z rate builds
        # and the wheel momentum accumulates along the +z command.
        self.assertGreater(hist[5]["omega_body"][2], 0.0)
        self.assertGreater(hist[5]["h_w"][2], 0.0)

    def test_wheel_momentum_tracks_impulse_integral(self):
        hist, _ = _slew_run()
        # For the z slew omega is parallel to h_w, so the transport term
        # vanishes and h_w equals the signed torque impulse integral.
        impulse = 0.0
        peak_mag = 0.0
        impulse_at_peak = None
        for h in hist:
            impulse += h["tau_cmd"][2] * DT
            mag = math.sqrt(sum(c * c for c in h["h_w"]))
            if mag > peak_mag:
                peak_mag = mag
                impulse_at_peak = impulse
        self.assertAlmostEqual(peak_mag, impulse_at_peak, places=6)
        self.assertGreater(peak_mag, 0.005)
        self.assertLess(peak_mag, 0.05)

    def test_no_saturation_generous_limits_and_speed(self):
        hist, ver = _slew_run()
        self.assertFalse(ver["torque_saturated"])
        self.assertFalse(ver["momentum_saturated"])
        peak = max(max(abs(s) for s in h["wheel_speed_rad_s"]) for h in hist)
        self.assertLess(abs(peak - 0.01338379 / J_W), 0.001)
        hw = ver["final_wheel_momentum"]
        self.assertLess(abs(hw[2]), 0.01)
        self.assertLess(abs(hw[0]), 1e-9)
        self.assertLess(abs(hw[1]), 1e-9)

    def test_torque_saturation_flag_and_slower_settling(self):
        hist, ver = _slew_run(tau_max=1e-4)
        self.assertTrue(ver["torque_saturated"])
        self.assertTrue(hist[0]["torque_saturated"])
        _, ver_free = _slew_run()
        self.assertGreater(ver["final_attitude_error_deg"],
                           ver_free["final_attitude_error_deg"])

    def test_momentum_saturation_flag_tight_limit(self):
        _, ver = _slew_run(h_max=0.004)
        self.assertTrue(ver["momentum_saturated"])

    def test_scalar_and_vector_limits_agree(self):
        r1 = _slew_run(tau_max=0.1, h_max=(0.5, 0.5, 0.5))
        r2 = _slew_run(tau_max=(0.1, 0.1, 0.1), h_max=0.5)
        self.assertEqual(r1[1]["final_attitude_error_deg"],
                         r2[1]["final_attitude_error_deg"])

    def test_rate_profile_mode_holds_attitude(self):
        # Given a zero rate profile the attitude holds and the command
        # stays at the PD value for the initial error.
        hist, ver = _slew_run(samples=[ZERO3] * N_STEPS)
        self.assertAlmostEqual(hist[-1]["q"][0], 1.0, places=12)
        self.assertAlmostEqual(hist[-1]["tau_cmd"][2],
                               hist[0]["tau_cmd"][2], places=12)
        self.assertFalse(ver["torque_saturated"])
        with self.assertRaises(ValueError):
            _slew_run(samples=[ZERO3] * 10)

    def test_valueerror_bad_inputs(self):
        args = (IDENTITY, ZERO3, Q_REF, KP, KD, J_W, ZERO3, None,
                0.1, 0.5, DT, N_STEPS)
        bad_q = (1.0, 0.0, float("nan"), 0.0)
        with self.assertRaises(ValueError):
            rwc.run_wheel_control(bad_q, *args[1:])
        for kp, kd, j_w in ((0.0, KD, J_W), (KP, -0.2, J_W), (KP, KD, 0.0)):
            with self.assertRaises(ValueError):
                rwc.run_wheel_control(IDENTITY, ZERO3, Q_REF, kp, kd, j_w,
                                      ZERO3, None, 0.1, 0.5, DT, N_STEPS)
        with self.assertRaises(ValueError):
            rwc.run_wheel_control(IDENTITY, ZERO3, Q_REF, KP, KD, J_W, ZERO3,
                                  None, 0.1, 0.5, 0.0, N_STEPS)
        with self.assertRaises(ValueError):
            rwc.run_wheel_control(IDENTITY, ZERO3, Q_REF, KP, KD, J_W, ZERO3,
                                  None, 0.0, 0.5, DT, N_STEPS)
        with self.assertRaises(ValueError):
            rwc.run_wheel_control(IDENTITY, ZERO3, Q_REF, KP, KD, J_W, ZERO3,
                                  None, 0.1, 0.0, DT, N_STEPS)
        with self.assertRaises(ValueError):
            rwc.run_wheel_control(IDENTITY, ZERO3, Q_REF, KP, KD, J_W, ZERO3,
                                  None, 0.1, 0.5, DT, 0)


if __name__ == "__main__":
    unittest.main()
