---
name: tightly-coupled-ins-gnss
description: "Use when you must run a tightly-coupled-ins-gnss integration filter: propagate the eight INS error states (3 position error, 3 velocity error, receiver clock bias in metres, clock drift in m/s) of the constant-velocity-error model between epochs, predict each raw pseudorange from the inertial position estimate plus the clock bias state, build the measurement matrix from the line-of-sight geometry rows with the unit clock column, and apply the raw-pseudorange-update Kalman correction on the residuals. Produces the corrected receiver position and velocity, the clock-state-filter estimates of bias and drift, the per-epoch innovation vector and the propagated and corrected covariance, in SI units, that gate the tightly coupled navigation solution of a moving receiver. Trigger: tightly coupled INS GNSS, raw pseudorange measurement update, ins-gnss-tight-coupling, clock-state-filter, INS error state with clock bias and drift."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: rtca-do-229
    reference-only: true
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: navigation
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [tightly-coupled-ins-gnss, raw-pseudorange-update, ins-gnss-tight-coupling, clock-state-filter, pseudorange-los-geometry, ins-error-state-ekf]
  version: 0.1.0
  author: AeroSkills
---

# Tightly Coupled INS/GNSS Integration (gnc-autonomy/navigation/tightly-coupled-ins-gnss)

Use when you must run a tightly coupled INS/GNSS integration: an INS
error-state Kalman filter updated on RAW pseudorange observables, in the
simplified fixed 8-state form of this leaf (3 position error states, 3
velocity error states, receiver clock bias in metres, receiver clock drift
in m/s, STATE_SIZE = 8), not a full 15-state INS. The dynamics model is
explicitly the constant-velocity-error, constant-drift form
dr += dv*dt and db += dd*dt between updates, with no attitude error states,
no accelerometer or gyro bias states, no gravity or Coriolis terms, no
earth-rate coupling and no INS mechanization: the INS reference trajectory
(position and velocity per epoch) is a GIVEN input, never re-mechanized.
The module is pure stdlib math, deterministic, with no RNG anywhere.

The leaf pairs with the loosely coupled position-domain filter of
ins-gnss-integrated-filter (same pack), which declares raw-observable
filtering out of scope in its own body; this leaf fills that gap by
updating on raw pseudoranges with the clock states. The snapshot position
fix of gnss-pseudorange-positioning enters only as the measurement-aiding
prior (the initial position estimate and the P0 position block); raw code
pseudoranges enter unsmoothed (gnss-carrier-smoothing owns the carrier
side); doppler observables never enter (gnss-doppler-velocity-positioning
owns the range-rate fix); the measurement set is treated as fault-free
(gnss-raim-fde owns integrity); and no scalar recursion tuning rules are
quoted (kalman-filter-design owns the single-axis recursion).

## Domain quick reference

- State vector x = [drx, dry, drz, dvx, dvy, dvz, db, dd] (indices 0-2
  position error in m, 3-5 velocity error in m/s, 6 receiver clock bias
  error in m, 7 receiver clock drift error in m/s). x is the correction
  ADDED to the INS reference: corrected position r_hat = r_ref + dr,
  corrected velocity v_hat = v_ref + dv, corrected clock bias
  b_hat = b_ref + db, corrected clock drift d_hat = d_ref + dd. The clock
  reference defaults to b_ref = d_ref = 0, so the clock states hold the
  total bias and drift. Open-loop error-state form: the corrections are
  never fed back into the reference; the corrected solution is re-derived
  as reference + x_hat at each epoch.
- Error dynamics over dt (exact under the constant-velocity-error,
  constant-drift model): dr(k+1) = dr(k) + dv(k)*dt with dv constant,
  db(k+1) = db(k) + dd(k)*dt with dd constant. The 8x8 transition Phi is
  the identity with dt on the dr-dv couplings (Phi[i][3+i] = dt for
  i = 0..2) and Phi[6][7] = dt.
- Covariance propagation: P_next = Phi*P*Phi^T + diag(q), with q the
  stated per-step diagonal (8 entries, all >= 0). Measurement noise R is
  the per-satellite variance list (diagonal, strictly positive entries).
- Measurement model in metres: measured pseudorange
  rho_i = |r_true - s_i| + b_true + n_i; predicted pseudorange
  rho_hat_i = |r_hat - s_i| + b_hat evaluated at the FULL propagated
  estimate r_hat = r_ref + dr, b_hat = b_ref + db. Innovation
  y_i = rho_meas,i - rho_hat_i. Clock states are in metres, so the clock
  column needs no speed-of-light conversion: it is exactly 1.0.
- Measurement row i (8 columns): the negated line of sight on the position
  channels, zero velocity-error and clock-drift columns, unit clock
  column: [-(sx-rx_hat)/rho_i, -(sy-ry_hat)/rho_i, -(sz-rz_hat)/rho_i,
  0, 0, 0, 1, 0] with rho_i the geometric range. A single-epoch raw
  pseudorange carries no velocity or drift information, so those states
  are observed only through the time propagation (stated assumption).
- Kalman update: S = H*P*H^T + R (m x m), K = P*H^T*S^-1 solved by
  Gaussian elimination with partial pivoting (singular S raises
  ValueError), x_new = x + K*y, P_new = (I - K*H)*P symmetrized by
  averaging P_new = (P_new + P_new^T)/2.
- Run driver: the first epoch is updated from the initial x0, p0 directly
  (no prior propagation); every later epoch first propagates the error
  state and covariance over dt from the previous epoch posterior, then
  predicts, then updates. Raw code pseudoranges only, m >= 4 satellites
  per update epoch with all epochs of one profile sharing m; fewer than
  four satellites raises ValueError (aiding through a partially
  observable set is out of scope). All units SI; the geometry-row sign
  convention matches gnss-pseudorange-positioning (negated
  receiver-to-satellite unit vector).

## Workflow

1. Fix the epoch profile and filter settings: the satellite ECEF
   positions, the measured raw pseudoranges per epoch, the INS reference
   records (position, velocity, clock bias and drift per epoch), the
   initial error state x0, the P0 diagonal (position sigma from the
   snapshot-fix measurement-aiding prior, velocity sigma, clock bias and
   drift sigma), the per-step process noise q, dt and the per-satellite
   measurement variances, and run run_tightly_coupled_profile over the
   epoch list.
2. Propagate the error state and covariance between epochs: the first
   epoch uses x0, p0 directly; every later epoch applies
   state_transition_matrix, propagate_state and propagate_covariance over
   dt from the previous epoch posterior, under the constant-velocity-
   error, constant-drift model.
3. Predict each raw pseudorange from the inertial position estimate plus
   the receiver clock bias state with predicted_pseudoranges, evaluated at
   the full propagated estimate (reference plus the propagated position
   error and clock bias state).
4. Build the measurement matrix from the line-of-sight geometry rows and
   the unit clock column with measurement_matrix, at the same full
   propagated estimate.
5. Apply the raw-pseudorange-update Kalman correction on the residuals
   with kalman_update: form the innovation vector (measured minus
   predicted pseudorange per satellite), compute the innovation RMS, solve
   for the gain through the innovation covariance and update the error
   state and covariance posterior.
6. Re-derive the corrected navigation solution as the INS reference plus
   the estimated corrections with corrected_navigation_state: corrected
   position, velocity, clock bias and clock drift.
7. Read off the gating outputs of the tightly coupled navigation
   solution: the per-epoch innovation vector and innovation RMS, the
   posterior covariance diagonal (position, velocity, bias and drift
   variances), the clock-state-filter estimates and the convergence of the
   corrected position and velocity against the true trajectory of the
   moving receiver. Confirm the deterministic checks with the contract
   test scripts/test_tightly_coupled_ins_gnss.py.

## Worked example

Scenario (the spec anchor scenario; all values below are REAL outputs of
this module, stdlib math, deterministic): dt = 1.0 s, 3 epochs at t = 0,
1, 2 s, 6 satellites fixed on the documented test constellation at radius
R_S = 26560000.0 m along the +-x, +-y and +-z ECEF axes (the same
documented-test-constellation convention as the gnss-pseudorange-
positioning worked example), receiver near the origin, satellite motion
neglected over the 2 s window. True receiver motion
r_true(t) = (100 + 25 t, 200 - 10 t, -150 + 5 t) m with v_true = (25,
-10, 5) m/s; true clock b_true(t) = 1500 + 5 t m with d_true = 5.0 m/s.
The INS reference starts offset by e_p0 = (12, -8, 6) m and runs with the
constant velocity error (0.5, -0.3, 0.2) m/s; the clock reference is
zero, so the clock states hold the totals. Raw pseudoranges are generated
from the true position plus the true clock bias plus the small fixed
noise realization (m, zero sum per epoch). Measurement variance 0.25 per
satellite (sigma_range = 0.5 m). Initial state x0 = 0, P0 =
diag(100, 100, 100, 1, 1, 1, 2.5e7, 400) (position sigma 10 m from the
snapshot-fix measurement-aiding prior), Q = diag(0.01, 0.01, 0.01,
0.001, 0.001, 0.001, 0.01, 1e-4).

- Predicted ranges from the epoch-0 INS reference (b = 0):
  [26559888.0011, 26560112.0011, 26559808.0006, 26560192.0006,
  26560144.0009, 26559856.0009] m; the measured pseudorange of sat1 (at
  +x) at epoch 0 is 26561400.201177 m.
- Epoch 0 (first snapshot, no prior propagation): innovations
  [1512.2001, 1487.9001, 1492.3000, 1507.8000, 1506.1000, 1493.7000] m,
  RMS 1500.0274 m; error state x_corr = (-12.1348, 7.7403, -6.1923,
  0, 0, 0, 1500.0000, 0): the position correction matches the negated INS
  offset, the clock bias estimate is 1500.0000 m and the velocity and
  drift states stay exactly zero (a single snapshot carries no velocity
  or drift information). Corrected position (99.8652, 199.7403,
  -150.1923) m, 3D error 0.3501 m. Posterior diagonal: per-axis position
  1.24844e-01 (the R/2 closed form of the symmetric 6-sat geometry),
  velocity 1.0 and drift 400.0 (unobservable), clock bias 4.16667e-02
  (the R/6 closed form).
- Epoch 1 (propagation over dt = 1 s, then update): innovations
  [5.2652, 4.8348, 4.2403, 5.8597, 4.7077, 5.0923] m, RMS 5.0251 m (the
  residuals of the drift growth one snapshot cannot see); x_corr =
  (-12.3287, 8.4697, -6.0191, -0.1708, 0.6427, 0.1526, 1504.9995,
  4.9988). Corrected position (125.1713, 190.1697, -144.8191) m, 3D
  error 0.3015 m. Posterior diagonal: velocity 2.07251e-01, drift
  9.34116e-02.
- Epoch 2: innovations collapse to the measurement noise floor
  [0.8022, -0.3989, 0.4140, -0.8107, 0.7352, -0.7318] m, RMS 0.6717 m;
  x_corr = (-12.9851, 8.6172, -6.4596, -0.4525, 0.3554, -0.1915,
  1509.9997, 4.9997) against the true corrections (-13.0, 8.6, -6.4) m,
  (-0.5, 0.3, -0.2) m/s, 1510.0 m and 5.0 m/s. Corrected position
  (150.0149, 180.0172, -140.0596) m, 3D error 0.0638 m; corrected
  velocity (25.0475, -9.9446, 5.0085) m/s, 3D error 0.0735 m/s; clock
  bias 1509.9997 m (error -0.0003 m); clock drift 4.9997 m/s (error
  -0.0003 m/s). Posterior diagonal: position 1.01082e-01, velocity
  6.44799e-02, bias 3.52379e-02, drift 2.59567e-02.
- Convergence read-off: 3D position error 0.3501 -> 0.3015 -> 0.0638 m
  and 3D velocity error 0.6164 -> 0.5917 -> 0.0735 m/s, decreasing every
  epoch. The innovation RMS tells the observability story: 1500.03 m at
  the first snapshot (unknown clock bias), 5.03 m at the second (the
  drift that one snapshot cannot see), 0.67 m at the third (measurement
  noise floor).
- Perfect-measurement identity run (noise offsets zero, variances 1e-9):
  the epoch-0 update recovers dr = (-12.000002, 8.000000, -6.000004) m
  and db = 1500.000007 m; the epoch-2 estimates land at
  dv = (-0.497630, 0.298579, -0.199051) m/s and dd = 4.999935 m/s.

## Verification

- state_transition_matrix(1.0) row 0 equals [1, 0, 0, 1, 0, 0, 0, 0] and
  row 6 equals [0, 0, 0, 0, 0, 0, 1, 1]; propagate_state reproduces the
  closed form dr = (2, -1.5, 2.8), db = 14 from dr = (1, -2, 3),
  dv = (0.5, 0.25, -0.1), db = 10, dd = 2 at dt = 2.
- propagate_covariance matches the inline Phi*P*Phi^T + diag(q) product
  to within 1e-9 relative.
- On the worked constellation the sat +x measurement row starts
  -0.9999999999591737 (within 1e-6 of -1, the negated line of sight) and
  the sat -y row has second entry 0.9999999999764121 (within 1e-6 of
  +1); the clock column is exactly 1.0 and the velocity-error and
  clock-drift columns exactly 0.0.
- Epoch-0 posterior closed forms of the symmetric 6-sat geometry: per-
  axis position variance 0.124844 equals sigma^2/2 (sigma_range = 0.5 m,
  R = 0.25) within 1e-3 and clock-bias variance 0.0416667 equals
  sigma^2/6 within 1e-4.
- Perfect-measurement identity: epoch-0 corrections recover
  (-12, 8, -6) m and 1500 m within 1e-3; epoch-2 velocity and drift
  recover (-0.5, 0.3, -0.2) m/s and 5.0 m/s within 0.01.
- P symmetry: max |P - P^T| below 1e-12 on every epoch posterior.
- Determinism: two identical profile runs are bitwise identical; no
  imports beyond math, no RNG anywhere.
- ValueError rejection of non-physical inputs: dt at 0.0 and -1.0, x of
  length 7, p of wrong shape, a negative q entry, an empty satellite
  list, satellite records of wrong length, fewer than 4 satellites, a
  satellite coincident with the receiver, a non-positive variance, an
  innovation or variance length mismatch, and an epoch profile with 3
  satellites.
- Run the contract test offline: python3
  scripts/test_tightly_coupled_ins_gnss.py (35 tests, deterministic,
  passes under python3 and the pyenv 3.13 hook interpreter).

## Related leaves

- gnc-autonomy/navigation/ins-gnss-integrated-filter: the loosely coupled
  position-domain error-state filter on GNSS position fixes, whose body
  declares raw-observable filtering out of scope (the gap this leaf
  fills).
- gnc-autonomy/navigation/gnss-pseudorange-positioning: the snapshot
  iterated least-squares fix that supplies the measurement-aiding prior
  (initial position estimate and P0 position block).
- gnc-autonomy/navigation/gnss-carrier-smoothing: the carrier-phase
  smoothing side of the code observable; this leaf consumes only raw
  unsmoothed code pseudoranges.
- gnc-autonomy/navigation/gnss-doppler-velocity-positioning: the
  snapshot velocity and clock-drift fix from doppler observables; this
  leaf never uses range-rate measurements.
- gnc-autonomy/navigation/gnss-raim-fde: integrity fault detection on the
  pseudorange set; this leaf treats the measurement set as fault-free.
- gnc-autonomy/navigation/kalman-filter-design: the scalar single-axis
  recursion and tuning rules; this leaf is the linear 8-state vector
  recursion on raw pseudoranges.

## Pitfalls

- Confusing this leaf with the loosely coupled position-domain filter:
  ins-gnss-integrated-filter updates on GNSS position fixes with the
  psi-angle model and heading error channels; this leaf updates on raw
  pseudorange observables with the clock states, and the measurement
  update needs m >= 4 satellites (fewer raises ValueError, since aiding
  through a partially observable set is out of scope).
- Re-mechanizing the INS or adding attitude channels: the INS reference
  trajectory is a given input and the model is the fixed 8-state
  constant-velocity-error, constant-drift form; adding attitude error,
  gyro or accelerometer bias states or gravity terms changes the
  transition and breaks the closed-form covariance anchors.
- Feeding the corrections back into the reference: the filter is the
  open-loop error-state form, so the corrected solution must be
  re-derived as reference + x_hat at every epoch; feeding x_hat back
  double-counts the correction.
- Expecting a single snapshot to observe velocity or drift: their
  measurement columns are zero, so the velocity and drift states only
  become observable through the time propagation once several epochs
  accumulate (their gain rows are exactly zero at the first update).
- Mixing clock units: the clock states are in metres and m/s (family
  convention), so the clock column is 1.0; a speed-of-light conversion
  would mis-scale the bias state against the metre-position states.
- Linearizing about the reference instead of the full propagated
  estimate: the pseudorange prediction and the measurement rows are
  evaluated at r_hat = r_ref + dr and b_hat = b_ref + db, which is what
  collapses the residuals once the bias is known.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_tightly_coupled_ins_gnss.py

The test covers the 8-state filter contract of the worked example: the
exact transition structure of state_transition_matrix, the
propagate_state closed form, propagate_covariance against the inline
product, the epoch-0 predicted-range and measured-pseudorange anchors,
the negated-line-of-sight measurement rows with the unit clock column and
zero velocity and drift columns, the per-epoch innovation anchors and
innovation RMS, the epoch-0 and epoch-2 error-state anchors, the
corrected navigation solution against the true trajectory at every epoch
with the decreasing 3D position and velocity errors, the epoch-0
covariance closed forms (sigma^2/2 and sigma^2/6), the epoch-2 velocity
and drift variances, posterior symmetry below 1e-12, the
perfect-measurement identity recovery, bitwise determinism and the
ValueError rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: RTCA DO-229 (MOPS for GPS/GNSS
  airborne equipment) and SAE ARP4754A (guidelines for development of
  civil aircraft and systems) are proprietary documents; the filter
  relations above are standard engineering methodology, name + paraphrase
  only per standards-map.yaml, with no reproduced tables or text.
- compliance: STANDARDS-REF, gated: false.
