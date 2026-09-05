# Wave-40 leaf spec: ins-gnss-integrated-filter (gnc-autonomy, navigation pack)

- Path: skills/gnc-autonomy/navigation/ins-gnss-integrated-filter/
- Pack: navigation. Closest siblings: kalman-filter-design (its logic
  is a scalar single-axis discrete Kalman filter: one state, one
  measurement, the classic gain/update equations; its body never
  assembles a coupled error-state vector), inertial-navigation (INS
  error growth, Schuler period, gyro drift and accelerometer bias
  propagation, alignment; its Workflow step "scope the integration"
  names INS/GNSS integration only qualitatively and its logic has no
  coupled-filter functions), gnss-pseudorange-positioning (snapshot
  pseudorange least-squares position fix, no dynamics, no filter),
  gnss-raim-fde (integrity monitoring of the GNSS fix). The gnc family
  router row for inertial-navigation currently routes "INS/GPS
  integration" to inertial-navigation; the ops manager updates the
  family router parent-side at close so this leaf owns the integration
  function. Whole-tree greps at prep: "error-state", "loosely coupled",
  "integrated filter" = 0 hits in skills/gnc-autonomy/. GENUINE GNC gap
  (fresh probe): the tree has scalar filtering and INS error growth but
  no coupled INS/GNSS integration filter.
- Standards id: arp4754a (reference-only). Ledger Standard: arp4754a.
- Family: gnc-autonomy

## Claim

Run a loosely coupled INS/GNSS integration filter in the error-state
(indirect) form: propagate a small state of position, velocity and
heading errors with the INS error model between GNSS fixes, and apply
a GNSS position measurement update that drives the estimated error
toward the measurement innovation. Produces the state-transition and
phi matrices of the error model, the predict step, the measurement
update with innovation and Kalman gain, and a corrected trajectory for
a short profile that gates the integrated navigation solution. Does
NOT do: scalar single-axis Kalman filtering (kalman-filter-design);
INS mechanization, Schuler period or gyro drift growth
(inertial-navigation); snapshot pseudorange least-squares fixes
(gnss-pseudorange-positioning); RAIM fault detection and exclusion
(gnss-raim-fde); tightly coupled pseudorange-level filtering (not
owned anywhere; explicitly out of scope).

## Model (implement exactly)

5-state horizontal-plane error-state filter. State vector
x = [dr_N, dr_E, dv_N, dv_E, dpsi]: north position error (m), east
position error (m), north velocity error (m/s), east velocity error
(m/s), heading error about the vertical (rad). The INS provides the
navigation solution; the error state is the difference between the
true error and the filter estimate. Continuous error model (psi-angle
model, level flight with horizontal specific force f_N, f_E; the
vertical channel is assumed nulled and not carried):
  dr_dot_N = dv_N, dr_dot_E = dv_E,
  dv_dot_N = f_E * dpsi, dv_dot_E = -f_N * dpsi, dpsi_dot = 0.
Functions (pure stdlib; small matrix helpers inside the module):
- mat_mul(a, b), mat_add(a, b), mat_transpose(a),
  mat_scale(c, a) -> list-of-list matrix helpers for 5x5, 2x5, 2x2 and
  5x1 operands (no numpy; document shapes; ValueError on shape
  mismatch).
- mat_inverse_2x2(m) -> float 2x2 inverse via the determinant
  (ValueError if |det| below 1e-12).
- error_state_matrix(f_north_m_s2, f_east_m_s2) -> 5x5 F per the model
  above.
- state_transition_matrix(f_north_m_s2, f_east_m_s2, dt_s) -> 5x5
  Phi = I + F * dt (first-order discrete approximation, documented);
  ValueError if dt_s <= 0.
- predict_step(x, p, phi, q) -> (x_next, p_next) with
  x_next = Phi x and p_next = Phi P Phi^T + Q (list-of-list 5x5 Q);
  ValueError if p or q are not 5x5 or x not length 5.
- measurement_update(x, p, z, h, r) -> (x_new, p_new, innovation,
  kalman_gain) implementing the standard Kalman update with
  innovation = z - H x, S = H P H^T + R, K = P H^T S^-1,
  x_new = x + K innovation, P_new = (I - K H) P (plain form,
  documented); z is length 2 (dr_N, dr_E), h is the 2x5 observation
  matrix, r the 2x2 measurement noise; ValueErrors on shape mismatch.
- run_ins_gnss_profile(dt_s, f_north_m_s2, f_east_m_s2, initial_error,
  gnss_times, p0, q, r, noise_free_innovations=True) -> dict with the
  estimated error trajectory after each GNSS update and the final
  corrected error state. Deterministic; the profile propagates the true
  error with the same Phi and feeds noise-free GNSS position
  observations z = [dr_N_true, dr_E_true] at the listed times; returns
  {"updates": [(t, innovation_N, innovation_E, est_dr_N, est_dr_E),
  ...], "final_estimate": x, "final_true": x_true}. The default
  profile constants are the worked example below.
Module constants: STATE_SIZE = 5.

Identity to test: a zero initial error and zero forcing keeps the
state at zero through predict; P stays symmetric through predict and
update (assert P[i][j] == P[j][i] within 1e-9); a perfect position
measurement (R tiny) drives the estimated position error to the
innovation; after the first GNSS update the estimated position error
is within 1 percent of the innovation magnitude; the innovation
magnitude shrinks once the filter has converged; the final estimated
position error is within 1 m of the true error after the last update
in the worked example.

## Worked example

Profile: dt = 1 s, level flight accelerating north, horizontal
specific force f_N = 2 m/s^2, f_E = 0; true initial INS error
x_true = [50, -30, 5, -2, 0.02] (m, m, m/s, m/s, rad); filter starts
at x = 0 with P0 = diag(1000, 1000, 100, 100, 0.01), process noise
Q = diag(0.01, 0.01, 0.01, 0.01, 1e-6), measurement noise
R = diag(1, 1); GNSS fixes at t = 10, 20, ..., 60 s with noise-free
innovations:
- t = 10: innovation (100.000, -51.800), estimate dr (99.991,
  -51.795).
- t = 30: innovation (-0.114, -9.900), estimate dr (200.009,
  -107.365).
- t = 60: innovation (0.0005, -0.139), estimate dr (350.000,
  -220.792); true error at t = 60 is (350.0, -220.8, 5.0, -4.4,
  0.02); final estimation error 4.3e-5 m north, 0.0081 m east.
Run your module and take the real outputs as assert targets; the
anchors above are prep-verified bounds, computed by running the prep
anchor script /tmp/w40spec/anchors_insgnss.py (prep-verified by
stdlib math).

## Validation list (contract test must include)

- error_state_matrix(2, 0): rows match the model (row 3 col 5 = 0, row
  4 col 5 = -2); error_state_matrix(0, 3): row 3 col 5 = 3.
- state_transition_matrix(2, 0, 1.0) equals I + F; ValueError at dt 0.
- predict_step on a zero state returns zero; P_next equals
  Phi P Phi^T + Q (assert against a hand-computed value within 1e-9);
  P symmetry preserved.
- measurement_update: with R = diag(1e-9, 1e-9) and z = [10, -5], the
  estimated position error after update is within 1e-3 of [10, -5]
  (perfect-measurement identity).
- Shape ValueErrors: x length != 5, p/q not 5x5, h not 2x5, r not 2x2,
  z length != 2.
- run_ins_gnss_profile on the worked example returns 6 updates; the
  t = 10 innovation is (100.000, -51.800) within 0.01; the t = 60
  innovation magnitude is below 0.2; the final estimate is within
  0.5 m of the true position error.
- Determinism: two runs return identical dicts.
- No RNG anywhere; all arithmetic deterministic.

## Corpus fragment (eval/hit1-wave40-ins-gnss-integrated-filter.yaml)

Query 1 (copy verbatim):
  "run the ins-gnss-integrated-filter error-state-filter over the level profile and apply the gnss-position measurement update to correct the ins position error and velocity error states"
  intent: "gnc-autonomy; loosely coupled INS/GNSS error-state integration filter"
  expected_skill: "gnc-autonomy/navigation/ins-gnss-integrated-filter"
Query 2 (copy verbatim):
  "propagate the ins drift error state with the psi-angle model and the state-transition matrix, then fuse the loosely-coupled-integration gnss fixes with the kalman measurement update"
  intent: "gnc-autonomy; error-state propagation and GNSS measurement fusion"
  expected_skill: "gnc-autonomy/navigation/ins-gnss-integrated-filter"
Task ids: w40-ins-gnss-integrated-filter-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must fuse INS and GNSS in a
loosely coupled error-state integration filter:" and include the
outputs in the Claim. First tag: ins-gnss-integrated-filter.
Additional tags ONLY: error-state-filter, loosely-coupled-integration,
gnss-position-update, ins-drift-correction. NEVER single generic words
(kalman, filter, ins, gnss, navigation, integration, error, state,
position, velocity). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): kalman-gain-scalar, single-axis,
innovation-variance-scalar (kalman-filter-design); schuler, gyro-drift,
accelerometer-bias, alignment, mechanization (inertial-navigation);
pseudorange, receiver-clock-bias, least-squares-fix
(gnss-pseudorange-positioning); protection-level, raim, fault-
detection (gnss-raim-fde).
