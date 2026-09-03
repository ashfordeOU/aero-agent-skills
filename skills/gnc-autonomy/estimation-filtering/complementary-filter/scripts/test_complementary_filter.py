#!/usr/bin/env python3
"""Contract test for the Complementary Filter leaf.

Stdlib unittest only (gate 3): imports the standard library and the
sibling logic module complementary_filter_logic.py. Deterministic and
offline (all runs are noiseless, so no random seed is needed at all).
Covers the gate 3 contract:

  - quaternion helpers: normalization (including rejection of zero and
    non-finite inputs), multiplication identity and same-axis
    composition, rotation matrix orthonormality R R^T = I within 1e-9
    and its action on a known 90 degree rotation
  - the body-frame prediction: the reference vector rotated by the
    inverse of the estimated attitude reproduces the body measurement
    when the estimate is perfect, and inverse rotation round-trips
  - cross-product vector innovation: zero for aligned vectors, sine of
    the separation angle, anti-symmetry in its arguments
  - correction step (sum over vector pairs times the proportional
    gain), bias update (explicit integral), compensated gyro rate
  - quaternion kinematics q_dot = 0.5 * q (x) [0, omega_c] and RK4
    propagation matching the closed-form axis-angle one-step solution
    within 1e-6
  - the worked example: a spacecraft at constant body rate
    omega_true = [0.01, 0.02, 0.005] rad/s for 100 s at dt = 0.01 s
    with gyro bias b_true = [0.001, -0.0008, 0.0006] rad/s and perfect
    sun and magnetometer-style vector measurements each step: the
    gyro-only attitude drifts 0.113 rad over 100 s (the uncompensated
    bias rate |b| times 100 s is 0.141 rad), the filtered innovation
    norm stays below 1e-3 rad over the whole run (measured maximum
    5.1e-4 rad at 2.3 s) and the bias estimate converges to within
    10 percent of b_true by about 10 s (final relative error near
    machine precision)
  - one-step sampling lag: the filtered estimate tracks the rotating
    truth within |omega| * dt (the measurement at step k reflects the
    true attitude at step k)
  - measurement gaps fall back to gyro propagation with zero innovation
  - ValueError rejection of non-positive dt, negative gains, non-finite
    inputs, malformed vectors, and initial quaternions outside the
    unit-norm tolerance

Run standalone:
    python3 scripts/test_complementary_filter.py
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import complementary_filter_logic as cf

# Worked-example scenario (spec): constant true body rate, fixed gyro
# bias, perfect vector measurements each step, SI units.
OMEGA_TRUE = [0.01, 0.02, 0.005]
B_TRUE = [0.001, -0.0008, 0.0006]
SUN_REF = [1.0, 0.0, 0.0]
MAG_REF = [0.6, -0.8, 0.0]
DT = 0.01
N_STEPS = 10000
B_TRUE_NORM = math.sqrt(sum(c * c for c in B_TRUE))
OMEGA_NORM = math.sqrt(sum(c * c for c in OMEGA_TRUE))


def axis_angle_quat(axis, angle):
    """Unit quaternion for an active rotation of angle about axis."""
    norm = math.sqrt(sum(c * c for c in axis))
    ax = [c / norm for c in axis]
    return [math.cos(angle / 2.0),
            math.sin(angle / 2.0) * ax[0],
            math.sin(angle / 2.0) * ax[1],
            math.sin(angle / 2.0) * ax[2]]


def integrate_true(q, omega, dt, n):
    """Closed-form constant-rate attitude trajectory (exact per step)."""
    angle = math.sqrt(sum(c * c for c in omega)) * dt
    dq = axis_angle_quat(omega, angle)
    out = []
    for _ in range(n):
        q = cf.quat_normalize(cf.quat_multiply(q, dq))
        out.append(q)
    return out


def error_angle(q1, q2):
    """Rotation angle between two attitudes, coordinate free."""
    dot = abs(sum(a * b for a, b in zip(q1, q2)))
    return 2.0 * math.acos(min(1.0, dot))


def vec3_norm(v):
    return math.sqrt(sum(c * c for c in v))


def relative_bias_error(b_est, b_true=B_TRUE):
    return vec3_norm([b_est[i] - b_true[i] for i in range(3)]) / B_TRUE_NORM


def run_filter(measurements, n_steps=N_STEPS):
    """Standard worked-example filter run with the module gains."""
    omega_m = [OMEGA_TRUE[i] + B_TRUE[i] for i in range(3)]
    return cf.run_complementary_filter(
        [1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [omega_m] * n_steps,
        measurements, cf.KP_DEFAULT, cf.KI_DEFAULT, DT)


def perfect_measurements(n_steps=N_STEPS):
    """Sun and magnetometer-style reference pairs measured from the
    rotating true attitude at every step."""
    q_true = integrate_true([1.0, 0.0, 0.0, 0.0], OMEGA_TRUE, DT, n_steps)
    return q_true, [[(SUN_REF, cf.rotate_reference_vector(qt, SUN_REF)),
                     (MAG_REF, cf.rotate_reference_vector(qt, MAG_REF))]
                    for qt in q_true]


class QuaternionTests(unittest.TestCase):
    """Quaternion normalization, multiplication, and rotation matrix."""

    def test_quat_normalize_unit_and_scaled(self):
        for q in ([1.0, 0.0, 0.0, 0.0], [0.5, -0.3, 0.6, 0.55]):
            self.assertAlmostEqual(vec3_norm(cf.quat_normalize(q)), 1.0,
                                   places=12)
        base = [0.5, -0.3, 0.6, 0.55]
        scaled = cf.quat_normalize([2.0 * c for c in base])
        plain = cf.quat_normalize(base)
        for a, b in zip(scaled, plain):
            self.assertAlmostEqual(a, b, places=12)

    def test_quat_normalize_invalid_raises(self):
        with self.assertRaises(ValueError):
            cf.quat_normalize([0.0, 0.0, 0.0, 0.0])
        with self.assertRaises(ValueError):
            cf.quat_normalize([float("nan"), 0.0, 0.0, 0.0])
        with self.assertRaises(ValueError):
            cf.quat_normalize([1.0, 0.0, float("inf"), 0.0])
        with self.assertRaises(ValueError):
            cf.quat_normalize([1.0, 0.0, 0.0])

    def test_quat_multiply_identity_and_composition(self):
        ident = [1.0, 0.0, 0.0, 0.0]
        q = [0.5, -0.3, 0.6, 0.55]
        for p in (cf.quat_multiply(q, ident), cf.quat_multiply(ident, q)):
            for a, b in zip(p, q):
                self.assertAlmostEqual(a, b, places=12)
        q30 = axis_angle_quat([0.0, 0.0, 1.0], math.radians(30))
        q45 = axis_angle_quat([0.0, 0.0, 1.0], math.radians(45))
        q75 = axis_angle_quat([0.0, 0.0, 1.0], math.radians(75))
        prod = cf.quat_normalize(cf.quat_multiply(q30, q45))
        for a, b in zip(prod, q75):
            self.assertAlmostEqual(a, b, places=12)

    def test_quat_multiply_invalid_raises(self):
        with self.assertRaises(ValueError):
            cf.quat_multiply([1.0, 0.0, 0.0], [1.0, 0.0, 0.0, 0.0])
        with self.assertRaises(ValueError):
            cf.quat_multiply([1.0, 0.0, 0.0, 0.0], [float("inf"), 0, 0, 0])

    def test_quat_to_rotation_matrix_orthonormal_and_known(self):
        for q in ([1.0, 0.0, 0.0, 0.0], [0.5, -0.3, 0.6, 0.55],
                  axis_angle_quat([1.0, 2.0, -0.5], 1.3)):
            r = cf.quat_to_rotation_matrix(q)
            for i in range(3):
                for j in range(3):
                    dot = sum(r[i][k] * r[j][k] for k in range(3))
                    self.assertAlmostEqual(dot, 1.0 if i == j else 0.0,
                                           places=9)
        # 90 degrees about z maps the ref x-axis onto the ref y-axis.
        r = cf.quat_to_rotation_matrix(
            axis_angle_quat([0.0, 0.0, 1.0], math.pi / 2.0))
        out = [r[i][0] for i in range(3)]
        self.assertAlmostEqual(out[0], 0.0, places=9)
        self.assertAlmostEqual(out[1], 1.0, places=9)
        self.assertAlmostEqual(out[2], 0.0, places=9)
        with self.assertRaises(ValueError):
            cf.quat_to_rotation_matrix([0.0, 0.0, 0.0, 0.0])


class MeasurementModelTests(unittest.TestCase):
    """Reference-vector rotation and cross-product innovation."""

    def test_rotate_reference_vector_body_prediction(self):
        # Identity attitude: the reference direction is its own body
        # measurement.
        v = cf.rotate_reference_vector([1.0, 0.0, 0.0, 0.0], SUN_REF)
        for a, b in zip(v, SUN_REF):
            self.assertAlmostEqual(a, b, places=12)
        # A body rotated +90 deg about z sees the ref x-axis at -90 deg.
        q90 = axis_angle_quat([0.0, 0.0, 1.0], math.pi / 2.0)
        v = cf.rotate_reference_vector(q90, SUN_REF)
        self.assertAlmostEqual(v[0], 0.0, places=9)
        self.assertAlmostEqual(v[1], -1.0, places=9)
        self.assertAlmostEqual(v[2], 0.0, places=9)
        # Rotating by the inverse attitude recovers the reference vector.
        q = cf.quat_normalize([0.6, -0.2, 0.4, 0.65])
        back = cf.rotate_reference_vector([q[0], -q[1], -q[2], -q[3]],
                                          cf.rotate_reference_vector(q, SUN_REF))
        for a, b in zip(back, SUN_REF):
            self.assertAlmostEqual(a, b, places=9)
        # Equals the matrix transpose product R(q)^T r by construction.
        rot = cf.quat_to_rotation_matrix(q)
        rv = [0.2, 0.8, -0.4]
        manual = [sum(rot[k][i] * rv[k] for k in range(3)) for i in range(3)]
        v = cf.rotate_reference_vector(q, rv)
        for a, b in zip(v, manual):
            self.assertAlmostEqual(a, b, places=9)

    def test_rotate_reference_vector_invalid_raises(self):
        with self.assertRaises(ValueError):
            cf.rotate_reference_vector([1.0, 0.0, 0.0, 0.0], [1.0, 0.0])
        with self.assertRaises(ValueError):
            cf.rotate_reference_vector([1.0, 0.0, 0.0, 0.0],
                                       [1.0, 0.0, float("nan")])

    def test_vector_measurement_error_aligned_zero_and_antisymmetry(self):
        for v in ([0.0, 0.0, 1.0], [1.0, 0.0, 0.0]):
            self.assertEqual(cf.vector_measurement_error(v, v),
                             [0.0, 0.0, 0.0])
        m = [1.0, 0.0, 0.0]
        v = [0.0, 1.0, 0.0]
        self.assertEqual(cf.vector_measurement_error(m, v), [0.0, 0.0, 1.0])
        self.assertEqual(cf.vector_measurement_error(v, m), [0.0, 0.0, -1.0])

    def test_vector_measurement_error_magnitude_sin(self):
        m = [1.0, 0.0, 0.0]
        v = [math.cos(math.radians(30.0)), math.sin(math.radians(30.0)), 0.0]
        e = cf.vector_measurement_error(m, v)
        self.assertAlmostEqual(vec3_norm(e), math.sin(math.radians(30.0)),
                               places=12)

    def test_vector_measurement_error_invalid_raises(self):
        with self.assertRaises(ValueError):
            cf.vector_measurement_error([1.0, 0.0], [1.0, 0.0, 0.0])
        with self.assertRaises(ValueError):
            cf.vector_measurement_error([1.0, 0.0, float("nan")],
                                        [1.0, 0.0, 0.0])


class CorrectionTests(unittest.TestCase):
    """Proportional correction, integral bias update, corrected rate."""

    def test_correction_step_sums_and_scales(self):
        self.assertEqual(cf.correction_step([], 2.0), [0.0, 0.0, 0.0])
        self.assertEqual(cf.correction_step(None, 2.0), [0.0, 0.0, 0.0])
        out = cf.correction_step([1.0, 2.0, 3.0], 2.0)
        self.assertEqual(out, [2.0, 4.0, 6.0])
        errors = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        out = cf.correction_step(errors, 0.5)
        for a, b in zip(out, [0.5, 0.5, 0.5]):
            self.assertAlmostEqual(a, b, places=12)

    def test_correction_step_negative_gain_raises(self):
        with self.assertRaises(ValueError):
            cf.correction_step([[1.0, 0.0, 0.0]], -0.1)
        with self.assertRaises(ValueError):
            cf.correction_step([[1.0, 0.0, 0.0]], float("nan"))

    def test_bias_update_drift_and_zero_hold(self):
        err = [[0.0, 0.0, 0.1]]
        b = cf.bias_update([0.0, 0.0, 0.0], err, 0.4, 0.01)
        self.assertAlmostEqual(b[0], 0.0, places=12)
        self.assertAlmostEqual(b[1], 0.0, places=12)
        self.assertAlmostEqual(b[2], -4e-4, places=12)
        b = cf.bias_update([0.001, -0.0008, 0.0006], [], 0.4, 0.01)
        for a, c in zip(b, [0.001, -0.0008, 0.0006]):
            self.assertAlmostEqual(a, c, places=15)

    def test_bias_update_invalid_raises(self):
        with self.assertRaises(ValueError):
            cf.bias_update([0.0, 0.0, 0.0], [], 0.4, 0.0)
        with self.assertRaises(ValueError):
            cf.bias_update([0.0, 0.0, 0.0], [], 0.4, -0.01)
        with self.assertRaises(ValueError):
            cf.bias_update([0.0, 0.0, 0.0], [], -0.4, 0.01)
        with self.assertRaises(ValueError):
            cf.bias_update([0.0, 0.0, 0.0], [], 0.4, float("nan"))

    def test_gyro_compensated_rate_corrects_bias_and_proportional(self):
        # Zero innovation: the corrected rate is the bias-compensated rate.
        out = cf.gyro_compensated_rate([0.011, 0.0192, 0.0056], B_TRUE,
                                       2.0, [])
        for a, b in zip(out, OMEGA_TRUE):
            self.assertAlmostEqual(a, b, places=12)
        # A unit innovation adds k_p on top of the compensated rate.
        out = cf.gyro_compensated_rate([0.011, 0.0192, 0.0056], B_TRUE,
                                       2.0, [[1.0, 0.0, 0.0]])
        self.assertAlmostEqual(out[0], OMEGA_TRUE[0] + 2.0, places=12)
        self.assertAlmostEqual(out[1], OMEGA_TRUE[1], places=12)
        self.assertAlmostEqual(out[2], OMEGA_TRUE[2], places=12)
        with self.assertRaises(ValueError):
            cf.gyro_compensated_rate([0.0, 0.0, 0.0], [0.0, 0.0, 0.0],
                                     -1.0, [])


class PropagationTests(unittest.TestCase):
    """Quaternion kinematics and the RK4 filter step."""

    def test_quat_kinematics_identity_rate(self):
        ident = [1.0, 0.0, 0.0, 0.0]
        qd = cf.quat_kinematics(ident, [0.0, 0.0, 0.01])
        self.assertAlmostEqual(qd[0], 0.0, places=15)
        self.assertAlmostEqual(qd[1], 0.0, places=15)
        self.assertAlmostEqual(qd[2], 0.0, places=15)
        self.assertAlmostEqual(qd[3], 0.005, places=15)
        qd = cf.quat_kinematics(ident, OMEGA_TRUE)
        self.assertAlmostEqual(qd[0], 0.0, places=12)
        self.assertAlmostEqual(vec3_norm(qd[1:]), 0.5 * OMEGA_NORM, places=12)

    def test_propagate_matches_closed_form_one_step(self):
        q0 = cf.quat_normalize([0.6, -0.2, 0.4, 0.65])
        # Zero measurement error and zero bias: propagate by the raw rate.
        q_new, _ = cf.propagate_attitude(q0, OMEGA_TRUE, [0.0, 0.0, 0.0],
                                         [], 2.0, 0.4, DT)
        closed = cf.quat_multiply(
            q0, axis_angle_quat(OMEGA_TRUE, OMEGA_NORM * DT))
        # RK4 on the linear kinematics matches the analytic axis-angle
        # step within 1e-6, and the step preserves unit norm.
        for a, b in zip(q_new, closed):
            self.assertAlmostEqual(a, b, delta=1e-6)
        self.assertLess(error_angle(q_new, closed), 1e-6)
        self.assertAlmostEqual(vec3_norm(q_new), 1.0, places=12)

    def test_propagate_applies_bias_update(self):
        err = [[0.0, 0.0, 0.05]]
        q, b = cf.propagate_attitude(
            [1.0, 0.0, 0.0, 0.0], OMEGA_TRUE, [0.0, 0.0, 0.0], err,
            2.0, 0.4, DT)
        self.assertAlmostEqual(b[2], -0.4 * 0.05 * DT, places=15)
        self.assertAlmostEqual(b[0], 0.0, places=15)
        self.assertAlmostEqual(vec3_norm(q), 1.0, places=12)

    def test_propagate_invalid_inputs_raise(self):
        args = ([1.0, 0.0, 0.0, 0.0], OMEGA_TRUE, [0.0, 0.0, 0.0], [])
        with self.assertRaises(ValueError):
            cf.propagate_attitude(*args, 2.0, 0.4, 0.0)
        with self.assertRaises(ValueError):
            cf.propagate_attitude(*args, -2.0, 0.4, DT)
        with self.assertRaises(ValueError):
            cf.propagate_attitude(*args, 2.0, -0.4, DT)
        with self.assertRaises(ValueError):
            cf.propagate_attitude([1.0, 0.0, 0.0, float("nan")], OMEGA_TRUE,
                                  [0.0, 0.0, 0.0], [], 2.0, 0.4, DT)


class FilterRunTests(unittest.TestCase):
    """Worked-example runs and end-to-end filter behavior."""

    def test_run_gyro_only_drift_100s(self):
        est, _ = run_filter(None)
        q_true, _ = perfect_measurements()
        drift = error_angle(q_true[-1], est[-1][0])
        # Uncompensated bias |b_true| * 100 s = 0.141 rad; the noiseless
        # run drifts 0.113 rad, inside the spec band 0.10-0.20 rad.
        self.assertGreater(drift, 0.10)
        self.assertLess(drift, 0.20)

    def test_run_bias_only_ten_second_error(self):
        n10 = 1000
        est, _ = run_filter(None, n_steps=n10)
        q_true10 = integrate_true([1.0, 0.0, 0.0, 0.0], OMEGA_TRUE, DT, n10)
        drift = error_angle(q_true10[-1], est[-1][0])
        integrated = B_TRUE_NORM * 10.0
        # Within 0.5 percent of the integrated bias angle (measured
        # 0.014111 rad against 0.014142 rad).
        self.assertAlmostEqual(drift, integrated, delta=0.005 * integrated)

    def test_run_filter_innovation_and_norm_converge(self):
        q_true, meas = perfect_measurements()
        est, norms = run_filter(meas)
        self.assertEqual(len(est), N_STEPS)
        self.assertEqual(len(norms), N_STEPS)
        # The innovation norm stays below 1e-3 rad over the whole run
        # (measured maximum 5.1e-4 rad at 2.3 s), the mean of the last
        # ten steps is about 3e-14 rad, and every estimate is unit norm.
        self.assertLess(max(norms), 1e-3)
        self.assertLess(norms[1999], 1e-3)
        self.assertLess(sum(norms[-10:]) / 10.0, 1e-3)
        self.assertTrue(cf.steady_state_verdict(norms, 1e-3))
        for q, _b in est:
            self.assertAlmostEqual(vec3_norm(q), 1.0, places=9)

    def test_run_filter_bias_converges(self):
        _q_true, meas = perfect_measurements()
        est, _ = run_filter(meas)
        # Final relative bias error near machine precision (measured
        # 4e-11); already within 10 percent of b_true by 10 s.
        self.assertLess(relative_bias_error(est[-1][1]), 0.10)
        self.assertLess(relative_bias_error(est[999][1]), 0.10)

    def test_run_filter_tracks_within_one_step_lag(self):
        q_true, meas = perfect_measurements()
        est, _ = run_filter(meas)
        # The measurement at step k reflects the true attitude at step k,
        # so the estimate trails by at most one step: the residual angle
        # |omega| * dt = 2.29e-4 rad is the sampling lag.
        lag = OMEGA_NORM * DT
        for k in (1999, 4999, 9999):
            self.assertLess(error_angle(q_true[k], est[k][0]),
                            1.5 * lag + 1e-6)

    def test_run_missing_measurement_steps_gyro_only(self):
        # Measurements only every 10th step: gyro propagation fills the
        # gaps with zero innovation and the filter still converges.
        q_true, meas = perfect_measurements()
        sparse = [meas[k] if k % 10 == 0 else None for k in range(N_STEPS)]
        est, norms = run_filter(sparse)
        self.assertLess(relative_bias_error(est[-1][1]), 0.10)
        for k in range(N_STEPS):
            if k % 10 != 0:
                self.assertEqual(norms[k], 0.0)
                self.assertAlmostEqual(vec3_norm(est[k][0]), 1.0, places=9)

    def test_run_pair_and_list_formats_accepted(self):
        # A tuple of two (r, m) pairs per step is accepted like a list of
        # pairs; both converge.
        q_true, meas = perfect_measurements()
        tupled = [tuple(step) for step in meas]
        est, _ = run_filter(tupled)
        self.assertLess(relative_bias_error(est[-1][1]), 0.10)
        est, _ = run_filter(meas)
        self.assertLess(relative_bias_error(est[-1][1]), 0.10)
        # A single (r, m) pair per step is accepted too.
        single = [(SUN_REF, cf.rotate_reference_vector(qt, SUN_REF))
                  for qt in q_true]
        est, _ = run_filter(single)
        self.assertEqual(len(est), N_STEPS)

    def test_run_q0_unit_norm_handling(self):
        # Within the 1e-6 tolerance the initial quaternion is normalized.
        q0 = [1.0 + 5e-7, 0.0, 0.0, 0.0]
        est, _ = cf.run_complementary_filter(
            q0, [0.0, 0.0, 0.0], [OMEGA_TRUE] * 100,
            [[(SUN_REF, [1.0, 0.0, 0.0])]] * 100, 2.0, 0.4, DT)
        self.assertAlmostEqual(vec3_norm(est[-1][0]), 1.0, places=9)
        with self.assertRaises(ValueError):
            cf.run_complementary_filter(
                [2.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0],
                [OMEGA_TRUE] * 10, None, 2.0, 0.4, DT)

    def test_run_invalid_dt_gains_raise(self):
        args = ([1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [OMEGA_TRUE] * 10, None)
        with self.assertRaises(ValueError):
            cf.run_complementary_filter(*args, 2.0, 0.4, 0.0)
        with self.assertRaises(ValueError):
            cf.run_complementary_filter(*args, -2.0, 0.4, DT)
        with self.assertRaises(ValueError):
            cf.run_complementary_filter(*args, 2.0, -0.4, DT)
        with self.assertRaises(ValueError):
            cf.run_complementary_filter([1.0, 0.0, 0.0, 0.0],
                                        [0.0, 0.0, float("nan")],
                                        [OMEGA_TRUE] * 10, None, 2.0, 0.4, DT)

    def test_run_measurement_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            cf.run_complementary_filter(
                [1.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0],
                [OMEGA_TRUE] * 10, [[]] * 9, 2.0, 0.4, DT)

    def test_steady_state_verdict(self):
        self.assertTrue(cf.steady_state_verdict([1e-6, 2e-6, 1e-6], 1e-3))
        self.assertFalse(cf.steady_state_verdict([0.1, 0.2, 0.3], 1e-3))
        # Mean of the last ten below tolerance even with early large steps.
        norms = [1.0] * 5 + [1e-6] * 10
        self.assertTrue(cf.steady_state_verdict(norms, 1e-3))
        with self.assertRaises(ValueError):
            cf.steady_state_verdict([], 1e-3)
        with self.assertRaises(ValueError):
            cf.steady_state_verdict([1e-3], 0.0)
        with self.assertRaises(ValueError):
            cf.steady_state_verdict([float("nan")], 1e-3)


if __name__ == "__main__":
    unittest.main()
