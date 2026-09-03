---
name: complementary-filter
description: "Use when you must run a Mahony-style explicit complementary filter attitude observer on so3 to fuse a spacecraft or air-vehicle rate gyro with sun sensor and magnetometer vector measurements into a continuous, drift-free attitude quaternion estimate with online gyro bias estimation: form the cross-product innovation from each body measurement against the reference vector rotated by the estimated attitude, drive the proportional and integral correction gains, update the bias estimate, and integrate the quaternion kinematics with RK4 and renormalization. Produces the attitude and bias time histories, the per-step innovation norm, and the steady-state convergence verdict that gate the pointing and navigation assessment. Trigger: complementary-filter, mahony, gyro-bias-estimation, vector-measurement-fusion, so3-attitude-observer, attitude-quaternion, innovation-norm, rate-gyro."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: estimation-filtering
  tags: [complementary-filter, mahony-style-filter, gyro-bias-estimation, vector-measurement-fusion, so3-attitude-observer, attitude-quaternion, innovation-norm, rate-gyro-fusion]
  version: 0.1.0
  author: Aero Agent Skills
---

# Complementary Filter (gnc-autonomy/estimation-filtering/complementary-filter)

Use when the task is an explicit (Mahony-style) complementary filter
attitude observer on the special orthogonal group SO(3): fusing the
high-rate rate-gyro angular rates (which drift) with low-rate absolute
vector measurements (sun sensor and magnetometer, which do not) into a
continuous attitude estimate with online gyro bias estimation. This leaf
implements the Mahony explicit complementary filter structure in pure
Python, stdlib only: per vector pair the cross-product innovation drives
a proportional correction and an integral bias update, and the corrected
rate propagates the unit attitude quaternion by RK4 with renormalization.
It pairs with the static two-vector attitude determination leaf in
space-systems/adcs for single-shot attitude from a vector pair, with the
stochastic estimation leaves of this pack for full navigation filters,
and with attitude-dynamics for propagation only. The frequency-domain
intuition is a high-pass gyro channel (fast but drifting) fused with a
low-pass vector channel (absolute but slow): the filter passes the gyro
through at high frequency and the vector correction through at low
frequency, so the estimate is both agile and drift-free.

## Domain quick reference

- State: the unit attitude quaternion q (scalar first, [w, x, y, z]) and
  the gyro bias vector b in rad/s. Measured rate: omega_m = omega_true +
  b + noise. Reference-frame vector r_i, body measurement
  m_i = R(q_true)^T r_i + noise.
- Convention (documented, used everywhere): R(q) is the active rotation
  matrix, so the filter predicts the body-frame direction of a reference
  vector as the inverse rotation v_i = R(q_est)^T r_i, which reproduces
  the body measurement exactly when the estimate is perfect.
- Vector innovation: e = sum_i (m_i x v_i), cross product of the body
  measurement with the predicted body vector; the small-angle attitude
  error in the body frame, summed over the pairs available at the step.
- Corrected rate: omega_c = omega_m - b_est + k_p * e, with the
  proportional gain k_p in 1/s (module default 2.0).
- Bias dynamics: b_dot = -k_i * e, explicit step
  b_new = b_est - k_i * e * dt, integral gain k_i in 1/s^2 (module
  default 0.4). The bias estimate converges to the true gyro bias, which
  removes the drift source of the gyro channel.
- Kinematics: q_dot = 0.5 * q (x) [0, omega_c], the quaternion
  multiplication form of the body-rate equation; integrated over the
  step by RK4 with the corrected rate held constant, then q is
  renormalized to unit norm.
- When no vector measurement is present at a step, e = 0 and the filter
  degrades to gyro-only propagation of the kinematics.
- The innovation norm per step is the magnitude of the total cross
  product error; the steady-state verdict compares the mean of the last
  ten steps against a tolerance.
- SI units throughout: rad, rad/s, rad/s^2, s.
- ARP4754A frames the onboard function development context; the
  relations above are standard engineering methodology, summary-only.

## Workflow

1. Initialize the unit quaternion q0 (normalized when within 1e-6 of
   unit norm) and the bias estimate b0, and fix the gains k_p, k_i and
   the step dt.
2. For each step take the gyro sample omega_m and the vector
   measurements available: each pair carries the reference-frame
   direction r_i and the body measurement m_i.
3. Predict each reference direction in the body frame with
   rotate_reference_vector and form the per-pair error with
   vector_measurement_error; sum the pair errors (zero when no
   measurement is present).
4. Form the rate correction with correction_step and the compensated
   rate with gyro_compensated_rate, then integrate one step with
   propagate_attitude: RK4 on quat_kinematics with renormalization,
   plus the explicit bias update via bias_update.
5. Loop over the whole sample sequence with run_complementary_filter,
   which returns the (q, b) estimate and the innovation norm per step.
6. Judge convergence with steady_state_verdict on the innovation norm
   sequence at the chosen tolerance.
7. Confirm the deterministic checks with the contract test
   scripts/test_complementary_filter.py.

## Worked example

Spacecraft at a constant true body rate omega_true = [0.01, 0.02,
0.005] rad/s for 100 s at dt = 0.01 s (10000 steps), true gyro bias
b_true = [0.001, -0.0008, 0.0006] rad/s (|b_true| = 1.414e-3 rad/s), so
the gyro reads omega_true + b_true. Reference vectors: sun r1 = [1, 0,
0] and a magnetometer-style reference r2 = [0.6, -0.8, 0], each with a
perfect noiseless body measurement at every step.

- Pure gyro propagation (no measurements): the attitude drifts with the
  uncompensated bias. At t = 100 s the attitude error is 0.113 rad, in
  the expected band 0.10 to 0.20 rad around the integrated bias angle
  |b_true| * 100 s = 0.141 rad; at t = 10 s the error is 0.01411 rad
  against |b_true| * 10 s = 0.01414 rad, within 0.5 percent.
- Filtered run with k_p = 2.0 1/s and k_i = 0.4 1/s^2: the innovation
  norm stays below 1e-3 rad over the whole run (measured maximum 5.1e-4
  rad at t = 2.3 s), reads 4.7e-6 rad at t = 20 s, and decays to about
  3e-14 rad at t = 100 s; the steady-state verdict on the 1e-3 rad
  tolerance passes.
- Bias convergence: the estimate reaches within 10 percent of b_true by
  t = 9.9 s and ends at [0.0010000, -0.0008000, 0.0006000], a relative
  error of about 4e-11, so the drift source is removed.
- Attitude tracking: the estimate follows the rotating truth within the
  one-step sampling lag |omega_true| * dt = 2.29e-4 rad, because the
  measurement at step k reflects the true attitude at step k.
- A single reference vector leaves rotations about the reference sun
  line unobservable, so the bias estimate cannot fully converge with one
  vector alone; two non-parallel references (as above) make the attitude
  and bias observable, which is why the fusion loop takes vector pairs.

## Verification

- Confirm quaternion normalization and multiplication identities, and
  that quat_to_rotation_matrix gives R R^T = I within 1e-9 and maps a
  90 degree rotation correctly.
- Confirm rotate_reference_vector returns R(q)^T r and that the
  predicted body direction matches the measurement when the estimate is
  perfect.
- Confirm with zero measurement error and zero bias that the corrected
  rate equals omega_m and that one propagated step matches the closed
  form axis-angle rotation quaternion within 1e-6, norm preserved.
- Confirm the drift anchors: gyro-only attitude error 0.113 rad at
  100 s (band 0.10 to 0.20) and 0.01411 rad at 10 s (within 0.5 percent
  of the integrated bias angle).
- Confirm the filter anchors: innovation norm below 1e-3 rad for the
  whole filtered run, steady-state verdict true, bias estimate within
  10 percent of b_true by about 10 s.
- Confirm every non-positive dt, negative gain, non-finite input,
  malformed vector, zero-norm quaternion, and initial quaternion outside
  the 1e-6 unit-norm tolerance raises ValueError.
- Run the contract test offline: python3
  scripts/test_complementary_filter.py (30 tests, deterministic).

## Related leaves

- gnc-autonomy/estimation-filtering/alpha-beta-filter: the discrete
  tracking-filter relative for position and velocity smoothing.
- gnc-autonomy/space/attitude-dynamics: pure quaternion kinematics
  propagation, the gyro channel without the vector correction.
- space-systems/adcs/attitude-determination-triad: static single-shot
  attitude from two vector observations, the alternative to continuous
  filtering.
- gnc-autonomy/estimation-filtering/extended-kalman-filter: the
  stochastic filtering family this pack offers for noise-covariance
  aware estimation.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_complementary_filter.py

The test covers the quaternion algebra and rotation matrix identities,
the body-frame reference-vector prediction, the cross-product
innovation, the proportional correction and integral bias update, the
compensated rate, RK4 kinematics against the closed-form axis-angle
step, the worked-example anchors (gyro-only drift of 0.113 rad over
100 s and 0.01411 rad over 10 s, filtered innovation below 1e-3 rad
throughout, bias within 10 percent of true by about 10 s, unit norm
preserved at every step, one-step sampling lag bound), measurement gaps
that fall back to gyro propagation, the pair and list measurement
formats, and ValueError rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: ARP4754A is cited as the
  development-process frame for onboard attitude functions; the
  complementary filter relations above are standard published
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
