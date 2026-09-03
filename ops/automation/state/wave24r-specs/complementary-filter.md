# Wave-24R leaf spec: complementary-filter (gnc-autonomy)

- Path: skills/gnc-autonomy/estimation-filtering/complementary-filter/
- Pack: estimation-filtering (existing: alpha-beta-filter,
  extended-kalman-filter, unscented-kalman-filter, particle-filter)
- Standards ids: arp4754a  (Ledger Standard: arp4754a)
- Family: gnc-autonomy

## Claim

Explicit (Mahony-style) complementary filter on SO(3) for spacecraft or
aircraft attitude estimation: fuse a rate gyro (high-frequency, drifts)
with vector measurements (accelerometer + magnetometer or star vector,
low-frequency, absolute) into a continuous attitude estimate with gyro
bias estimation. Produces the estimated quaternion, the gyro bias
estimate, the innovation vector, and a convergence/steady-state verdict.

Does NOT do: static single-shot attitude determination from two vectors
(TRIAD in space-systems/adcs/attitude-determination-triad), Kalman
family stochastic filtering (extended-kalman-filter etc.), gyro
integration alone (attitude-dynamics propagation).

## Model (implement exactly)

State: quaternion q (body to reference), gyro bias vector b (rad/s).
Measured angular rate omega_m = omega_true + b + noise.
Reference vectors in the reference frame r_i; measurements in the body
frame b_i = R(q) r_i + noise.

Correction (Mahony explicit complementary filter):
- For each vector pair compute the body measurement m_i and the
  estimated body vector v_i = R(q)^T? convention: choose v_i as the
  rotation of the reference vector by the current attitude estimate,
  v_i = R(q_est) r_i (document the convention; be consistent).
- Error e = sum_i (m_i x v_i)  (cross product, small-angle attitude
  error in body frame).
- Bias correction: b_dot = -k_i * e  (integral gain, rad/s^2).
- Corrected rate: omega_c = omega_m - b_est + k_p * e.
- Kinematics: q_dot = 0.5 * Omega(omega_c) * q_est  (quaternion
  multiplication form of q_dot = 0.5 * q ⊗ [0, omega_c]).
- Integrate with a fixed dt (RK4 or first-order with normalization;
  choose RK4, then renormalize q to unit norm).

Gains: k_p (proportional, default 2.0 1/s) and k_i (integral, default
0.4 1/s^2) are module constants / inputs. If no vector measurement is
present, run the gyro-only propagation (e = 0).

## Functions

- quat_normalize(q), quat_multiply(q1, q2), quat_to_rotation_matrix(q)
- rotate_reference_vector(q, r) -> estimated body vector v
- vector_measurement_error(m, v) -> cross-product error (3-vector)
- correction_step(errors, k_p) -> rate correction
- bias_update(b_est, errors, k_i, dt) -> new b_est
- gyro_compensated_rate(omega_m, b_est, k_p, errors) -> omega_c
- quat_kinematics(q, omega_c) -> q_dot
- propagate_attitude(q, omega_m, b_est, errors, k_p, k_i, dt) ->
  (q_new, b_new) one filter step
- run_complementary_filter(q0, b0, omega_samples, measurement_samples,
  k_p, k_i, dt) -> list of (q, b) estimates, innovation norm per step
- steady_state_verdict(innovation_norms, tolerance) -> bool/str
ValueError on: dt <= 0, non-finite inputs, k_p < 0, k_i < 0,
non-unit initial quaternion (normalize instead if within 1e-6, else error).

## Worked example

Spacecraft: initial q0 = [1,0,0,0] (identity), true constant body rate
omega_true = [0.01, 0.02, 0.005] rad/s for 100 s at dt = 0.01 s, true
gyro bias b_true = [0.001, -0.0008, 0.0006] rad/s (gyro measures
omega_true + b_true + small noise; use a FIXED seed for any noise, or
prefer noiseless runs for the worked anchors), reference sun vector in
the reference frame r = [1,0,0] with a perfect body measurement each
step. Anchors:
- Without the measurement (pure gyro propagation) the attitude drifts
  linearly with the bias: at t = 100 s the attitude error is about
  |b_true| * 100 s ~ 0.14 rad (assert 0.10-0.20 for noiseless run).
- With the filter and k_p = 2.0, k_i = 0.4, the steady-state innovation
  norm drops below 1e-3 rad within ~20 s and the bias estimate converges
  to within 10% of b_true by t = 100 s (noiseless; assert tolerances
  that your real run satisfies, then quote the numbers in the SKILL).
Test identities:
- quaternion rotation is norm-preserving; quat_to_rotation_matrix gives
  R R^T = I (within 1e-9).
- With zero measurement error and zero bias, the corrected rate equals
  omega_m and propagation matches closed-form quaternion kinematics for
  a constant rate over one step (compare with the analytic axis-angle
  rotation quaternion, within 1e-6).
- With bias only (no measurement), propagated attitude error after 10 s
  equals the integrated bias angle within 0.5%.
- Noise-free bias convergence test as above.
- ValueError rejections.

## Corpus tasks (2 tasks, ids w24r-complementary-filter-1/2)

Distinctive tokens: complementary-filter, mahony, gyro-bias-estimation,
vector-measurement fusion, so3 attitude observer. Avoid: "triad",
"star tracker", "kalman", "particle filter", "quaternion kinematics
propagation only" (siblings).

1. "fuse the spacecraft rate gyro with the sun vector and magnetometer
   measurements in a Mahony complementary filter on so(3): estimate the
   attitude quaternion online and the gyro bias, with the proportional
   and integral correction gains, and report the innovation norm
   convergence over the run"
2. "run an explicit complementary filter attitude observer for the
   air vehicle: combine the high-rate gyro angular rates with the
   low-rate absolute vector measurements so the gyro bias is estimated
   and the roll pitch yaw estimate does not drift, and verify the
   steady-state innovation"

## SKILL body notes

Pair with attitude-determination-triad (static vector attitude), the
Kalman estimation leaves (stochastic filtering), attitude-dynamics
(propagation only). Describe the frequency-domain intuition briefly
(high-pass gyro + low-pass vector) and the SO(3) cross-product
correction. Worked example uses the values above.
