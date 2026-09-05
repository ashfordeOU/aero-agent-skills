---
name: ins-gnss-integrated-filter
description: "Use when you must fuse INS and GNSS in a loosely coupled error-state integration filter: assemble the 5-state psi-angle error model of the horizontal INS drift from the specific forces, discretize it into the state transition matrix, predict the position, velocity and heading error states and their covariance between GNSS fixes, and apply the GNSS position measurement update that drives the estimated error state toward the innovation through the Kalman gain. Produces the error-state matrix, the state transition matrix, the innovation and gain of each fix, the corrected error trajectory, and the gated integrated navigation solution of a level-flight profile. Trigger: ins-gnss-integrated-filter, error-state-filter, loosely-coupled-integration, gnss-position-update, ins-drift-correction, psi-angle-model, state-transition-matrix, horizontal-specific-force."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: gnc-autonomy
pack: navigation
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [ins-gnss-integrated-filter, error-state-filter, loosely-coupled-integration, gnss-position-update, ins-drift-correction]
  version: 0.1.0
  author: AeroSkills
---

# INS/GNSS Integrated Filter (gnc-autonomy/navigation/ins-gnss-integrated-filter)

Use when the task is running a loosely coupled INS/GNSS integration
filter in the error-state (indirect) form: propagate a small state of
position, velocity and heading errors with the INS error model between
GNSS fixes, and apply a GNSS position measurement update that drives
the estimated error toward the measurement innovation. This leaf
implements the horizontal-plane psi-angle error model in pure Python,
stdlib only. It pairs with gnc-autonomy/navigation/kalman-filter-design
(the scalar single-state filter this vector model generalizes),
gnc-autonomy/navigation/inertial-navigation (the INS error growth this
filter integrates over), and gnc-autonomy/navigation/gnss-
pseudorange-positioning (the fix source of the measurement update).

## Domain quick reference

- Error-state filter: the INS provides the navigation solution and the
  filter estimates the error of that solution. State vector
  x = [dr_N, dr_E, dv_N, dv_E, dpsi]: north position error (m), east
  position error (m), north velocity error (m/s), east velocity error
  (m/s), heading error about the vertical (rad), STATE_SIZE = 5.
- Continuous psi-angle error model, level flight with horizontal
  specific force f_N, f_E and the vertical channel nulled:
  dr_dot_N = dv_N, dr_dot_E = dv_E, dv_dot_N = f_E * dpsi,
  dv_dot_E = -f_N * dpsi, dpsi_dot = 0. Heading error is a constant
  bias in level flight; the specific force couples it into the
  velocity error rows of the error-state matrix.
- Error-state matrix F: the dv_N row couples dpsi through the east
  specific force f_E and the dv_E row couples dpsi through -f_N; the
  dr rows carry the unit dv couplings.
- State transition matrix: Phi = I + F * dt, a first-order discrete
  approximation valid when dt is small relative to the dynamics time
  scale.
- Predict step: x_next = Phi * x and P_next = Phi * P * Phi^T + Q; the
  predicted covariance grows by the process noise Q each step.
- GNSS measurement update (position domain, loosely coupled):
  innovation = z - H*x with z = [dr_N, dr_E] the position error
  measurement and H the 2x5 observation matrix on the position
  channels; S = H*P*H^T + R; K = P*H^T*S^-1;
  x_new = x + K*innovation; P_new = (I - K*H)*P (plain form).
- After the first trusted fix the estimated position error lands on
  the innovation; once the filter converges the innovation magnitude
  shrinks toward the measurement noise level.
- Units are SI throughout: m, m/s, rad, specific force m/s^2,
  covariances in the unit squared.
- ARP4754A (reference-only) frames development assurance for aircraft
  systems; the error-state integration filter is standard
  estimation-theory knowledge (Gelb; Brown and Hwang), summary-only.

## Workflow

1. Fix the integration setup: the 5-state error-state vector ordering
   [dr_N, dr_E, dv_N, dv_E, dpsi], the level-flight assumption with
   the vertical channel nulled, and the module constant STATE_SIZE.
2. Assemble the continuous error-state matrix F of the psi-angle model
   with error_state_matrix(f_north_m_s2, f_east_m_s2) from the
   horizontal specific forces.
3. Discretize the error model into the state transition matrix with
   state_transition_matrix(f_north_m_s2, f_east_m_s2, dt_s), the
   first-order Phi = I + F*dt.
4. Predict the error state and its covariance between GNSS fixes with
   predict_step(x, p, phi, q); a zero error state stays zero and P
   stays symmetric.
5. Set up the observation model of the GNSS position fix: the 2x5
   observation matrix h on the position error channels and the 2x2
   measurement noise r.
6. Apply the GNSS position measurement update with
   measurement_update(x, p, z, h, r), which returns the corrected
   error state, the corrected covariance, the innovation and the
   Kalman gain of the fix.
7. Run the full profile with run_ins_gnss_profile(dt_s, f_north_m_s2,
   f_east_m_s2, initial_error, gnss_times, p0, q, r) and gate the
   integrated navigation solution on the corrected error trajectory:
   check the innovation magnitudes shrink once the filter converges
   and that the final estimate has collapsed onto the true error.
8. Confirm the deterministic checks with the contract test
   scripts/test_ins_gnss_integrated_filter.py.

## Worked example

Level flight accelerating north: dt = 1 s, f_N = 2 m/s^2, f_E = 0.
True initial INS error x_true = [50, -30, 5, -2, 0.02] (m, m, m/s,
m/s, rad); the filter starts at zero with P0 = diag(1000, 1000, 100,
100, 0.01), Q = diag(0.01, 0.01, 0.01, 0.01, 1e-6), R = diag(1, 1),
and noise-free GNSS position fixes at t = 10, 20, ..., 60 s.

- t = 10 s: innovation (100.000, -51.800), estimated error
  dr (99.991, -51.795). The first fix drags the estimate onto the
  accumulated position error.
- t = 20 s: innovation (-40.908, 22.166), estimate dr (150.044,
  -77.616). The velocity error estimate overshoots slightly, so the
  next fix pulls back.
- t = 30 s: innovation (-0.114, -9.900), estimate dr (200.009,
  -107.365).
- t = 40 s: innovation (0.023, -0.625), estimate dr (249.998,
  -141.179).
- t = 50 s: innovation (0.013, -0.238), estimate dr (299.999,
  -178.988).
- t = 60 s: innovation (0.0005, -0.139), estimate dr (350.000,
  -220.792), innovation magnitude 0.139 m, down from 112.6 m at the
  first fix.
- True error at t = 60 s: (350.0, -220.8, 5.0, -4.4, 0.02); final
  estimate (349.99996, -220.79188, 5.00010, -4.39496, 0.01955);
  final estimation error 4.3e-5 m north and 0.0081 m east.

## Verification

- Confirm error_state_matrix(2, 0) puts -f_N = -2 at the dv_E-dpsi
  entry and error_state_matrix(0, 3) puts f_E = 3 at the dv_N-dpsi
  entry.
- Confirm state_transition_matrix(2, 0, 1.0) equals I + F and that a
  non-positive dt raises ValueError.
- Confirm predict_step on a zero state returns zero and that P_next
  equals Phi*P*Phi^T + Q against the hand-computed value
  (P_next[0][0] = 1100.01 at zero specific force), with P symmetric.
- Confirm the perfect-measurement identity: with R = diag(1e-9, 1e-9)
  and z = [10, -5] the updated position error sits within 1e-3 of the
  innovation.
- Confirm the worked example: six GNSS updates, t = 10 innovation
  (100.000, -51.800) within 0.01, t = 60 innovation magnitude below
  0.2 m, final estimate within 0.5 m of the true position error, and
  the estimation error at the spec anchors 4.3e-5 m and 0.0081 m.
- Confirm non-physical and malformed inputs raise ValueError: dt <= 0,
  error state not length 5, p, q or phi not 5x5, h not 2x5, r not 2x2,
  z not length 2, a singular 2x2 measurement covariance, and the
  stochastic-innovation request that would break determinism.
- Run the contract test offline: python3
  scripts/test_ins_gnss_integrated_filter.py (35 tests,
  deterministic).

## Related leaves

- gnc-autonomy/navigation/kalman-filter-design: the scalar one-state
  discrete Kalman filter this 5-state error-state filter generalizes.
- gnc-autonomy/navigation/inertial-navigation: INS error growth and
  drift model context for the errors this filter integrates and
  corrects.
- gnc-autonomy/navigation/gnss-pseudorange-positioning: the snapshot
  position fix that feeds the loosely coupled measurement update.
- gnc-autonomy/navigation/gnss-raim-fde: integrity monitoring of the
  GNSS fix before it enters the integration filter.

## Pitfalls

- Reading the innovation as the estimation error: the innovation is
  the measurement residual z - H*x that the Kalman gain weights, not
  the error of the filter (the t = 10 innovation is 112.6 m while the
  estimate lands 0.009 m from the true error).
- Building the error-state matrix from accelerations instead of
  specific forces: the coupling entries are f_E on the dv_N row and
  -f_N on the dv_E row, and swapping the force axes changes the sign
  of the heading-to-velocity coupling.
- Treating the discrete Phi as exact: Phi = I + F*dt is a first-order
  approximation, so dt must stay small relative to the dynamics time
  scale.
- Expecting a closed-loop reset: this profile accumulates the error
  estimate across fixes (open-loop form); a real system that feeds
  corrections back to the INS resets the estimate after each update.
- Adding measurement noise: the profile is deterministic by design,
  so run_ins_gnss_profile raises ValueError when stochastic
  innovations are requested; test with noise-free fixes and add the
  noise model outside the module.
- Confusing the loosely coupled position-domain update with
  raw-observable (tightly coupled) filtering, which is out of scope
  for this leaf.
- Forgetting the units: mixing meters and kilometers in one state
  corrupts the covariance recursion, which squares the unit.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_ins_gnss_integrated_filter.py

The test covers the worked-example integration profile (six GNSS
updates, the t = 10, 30 and 60 innovation and estimate anchors, the
sub-0.2 m converged innovation magnitude, the final estimate within
0.5 m of the true error, and the 4.3e-5 m and 0.0081 m final
estimation errors), the error-state matrix row couplings of the
psi-angle model, the I + F*dt discretization, the predict step with
its hand-computed covariance and symmetry, the GNSS position
measurement update with the perfect-measurement identity, the
innovation residual, the 5x2 Kalman gain and the covariance shrinkage,
determinism across two runs, and ValueError rejection of every
malformed or non-physical input.

## Compliance

- Standards referenced, not reproduced: ARP4754A is proprietary (SAE);
  name and paraphrase only per standards-map.yaml, reference-only:
  true. The error-state integration filter relations are standard
  engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
